"""
Couche d'intelligence : analyse semantique des donnees collectees via Claude API.
Si ANTHROPIC_API_KEY n'est pas definie, bascule sur des heuristiques deterministes
(lexique francais de sentiment + detection de mots-cles d'alerte).

Trois fonctions publiques :
  - classify_sentiment(texts, brands) -> DataFrame avec colonnes sentiment, score, rationale
  - detect_weak_signals(news_df, trends_df) -> list of signal dicts
  - build_executive_brief(context) -> dict avec summary, key_insights, recommendations

Les resultats IA sont mis en cache en memoire : un meme lot de titres ou un meme
contexte n'est envoye qu'une fois (evite un appel a chaque interaction).
"""

import os
import re
import json
import hashlib
import unicodedata
from datetime import datetime
from typing import Optional
import pandas as pd


ANTHROPIC_MODEL = "claude-opus-4-7"
MAX_BATCH_SIZE = 30
_CACHE: dict = {}

# Contexte de marche transmis a l'IA (Cote d'Ivoire)
CI_CONTEXT = (
    "Contexte : marché ivoirien des paris sportifs. Régulateur : ARJH (Autorité de Régulation des "
    "Jeux de Hasard, loi de 2020). La LONACI est concessionnaire et délivre les agréments aux "
    "opérateurs (1XBET, Betclic, Premier Bet, etc.) ; Sportcash est la plateforme de la LONACI. "
    "Depuis le décret de décembre 2023, les paris non organisés ou agréés par la LONACI sont "
    "interdits. Monnaie : franc CFA (FCFA). Paiements surtout par mobile money (Orange Money, "
    "MTN MoMo, Moov Money, Wave). Âge légal : 18 ans. Le football (Éléphants, CAN) domine. "
    "Betclic Côte d'Ivoire est distinct de Betclic France (ignorer tout contenu français)."
)


def _cache_key(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, default=str).encode()).hexdigest()


# ────────────────────────────────────────────────────────────
# Fallback heuristique : lexique francais
# ────────────────────────────────────────────────────────────
POS_WORDS = {
    "excellent", "super", "parfait", "top", "bravo", "merci", "fiable", "rapide",
    "facile", "securise", "recommande", "genial", "bonne", "bon", "content",
    "satisfait", "efficace", "pratique", "meilleur", "qualite", "innovant",
    "performant", "gagnant", "gagne", "remporte", "sacre", "recompense", "soutien",
    "engage", "partenariat", "ambassadeur", "sensibilise", "solidarite",
}
NEG_WORDS = {
    "arnaque", "nul", "mauvais", "bug", "panne", "bloque", "escroc", "escroquerie",
    "fraude", "lent", "probleme", "erreur", "perdu", "vole", "plainte", "pourri",
    "scam", "faux", "decu", "catastrophe", "pire", "refuse", "triche", "voleur",
    "impaye", "illegal", "illegaux", "interdit", "sanction", "suspendu", "addiction",
}

# Regles d'alerte : (categorie, severite, motifs). Les motifs s'appliquent au texte
# normalise (minuscules, sans accents).
ALERT_RULES = [
    ("Réglementation", "high", [
        r"\barjh\b", r"\blonaci\b.*\b(sanction|retrait|suspen|interdi|agrement)",
        r"\bagrement", r"\blicence\b", r"\binterdi", r"\billegal", r"\bdecret\b",
        r"\bsanction", r"\bamende\b", r"\bsuspen", r"\btaxe\b", r"\bfiscal",
        r"\bmineurs?\b", r"\bblanchiment",
    ]),
    ("Réputation", "high", [
        r"\barnaque", r"\bescroq", r"\bfraude", r"\bplainte", r"\bproces\b", r"\bcondamn",
        r"\bscandale", r"\bcompte[s]? (bloque|suspendu|ferme)", r"\bretrait[s]? (impossible|bloque)",
        r"\bgains? (bloque|non paye|impaye)", r"\bpiratage", r"\bcyberattaque", r"\bpanne\b",
    ]),
    ("Jeu responsable", "medium", [
        r"\baddict", r"\bdependance", r"\bjeu responsable", r"\bsurendett",
    ]),
    ("Activité marketing concurrente", "low", [
        r"\bpartenariat", r"\bsponsor", r"\bambassadeur", r"\blancement\b", r"\blance\b",
        r"\bnouvelle offre", r"\bbonus\b", r"\bcampagne\b",
    ]),
]


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9\s']", " ", s)


def _heuristic_sentiment(text: str) -> dict:
    tokens = set(_norm(text).split())
    pos_hits = len(tokens & POS_WORDS)
    neg_hits = len(tokens & NEG_WORDS)
    score = pos_hits - neg_hits
    label = "positif" if score > 0 else ("negatif" if score < 0 else "neutre")
    return {
        "sentiment": label,
        "score": max(-1.0, min(1.0, score / 3.0)),
        "rationale": "Analyse lexicale",
    }


def _has_anthropic() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _anthropic_client():
    try:
        import anthropic
        return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    except ImportError:
        return None
    except Exception:
        return None


# ────────────────────────────────────────────────────────────
# API publique
# ────────────────────────────────────────────────────────────

def classify_sentiment(texts: list, brands: Optional[list] = None) -> pd.DataFrame:
    """
    Classifie le sentiment de titres courts envers la marque concernee.
    Colonnes retournees : text, sentiment (positif/neutre/negatif), score [-1,1], rationale, source.
    """
    if not texts:
        return pd.DataFrame(columns=["text", "sentiment", "score", "rationale", "source"])
    brands = list(brands) if brands is not None else [""] * len(texts)
    key = _cache_key("sent", list(map(str, texts)), brands)
    if key in _CACHE:
        return _CACHE[key].copy()

    client = _anthropic_client() if _has_anthropic() else None
    rows = []
    if client is None:
        for t in texts:
            res = _heuristic_sentiment(str(t))
            res.update({"text": str(t)[:300], "source": "heuristic"})
            rows.append(res)
        return pd.DataFrame(rows)

    try:
        for i in range(0, len(texts), MAX_BATCH_SIZE):
            batch = list(zip(texts[i:i + MAX_BATCH_SIZE], brands[i:i + MAX_BATCH_SIZE]))
            msg = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=2500,
                messages=[{"role": "user", "content": _build_sentiment_prompt(batch)}],
            )
            content = msg.content[0].text if msg.content else ""
            rows.extend(_parse_sentiment_json(content, [b[0] for b in batch]))
        df = pd.DataFrame(rows)
        _CACHE[key] = df
        return df.copy()
    except Exception as e:
        rows = []
        for t in texts:
            res = _heuristic_sentiment(str(t))
            res.update({"text": str(t)[:300], "source": f"heuristic_fallback:{type(e).__name__}"})
            rows.append(res)
        return pd.DataFrame(rows)


def _build_sentiment_prompt(batch: list) -> str:
    lines = "\n".join(f"{i+1}. [{b or 'marque'}] {str(t)[:280]}" for i, (t, b) in enumerate(batch))
    return (
        f"Tu es analyste de réputation pour le marché des paris sportifs en Côte d'Ivoire. {CI_CONTEXT}\n\n"
        "Pour chaque titre numéroté, évalue le sentiment envers la marque indiquée entre crochets "
        "(pas le sentiment général de l'actualité) : positif, neutre ou negatif, avec un score entre "
        "-1 et 1 et une justification en français de 10 mots maximum, sans tiret long. "
        "Un partenariat, une action sociale ou un événement sponsorisé est en général positif ; "
        "une annonce factuelle est neutre ; une plainte, une sanction ou une arnaque est négative.\n"
        "Réponds UNIQUEMENT en JSON valide de la forme :\n"
        '[{"id":1,"sentiment":"positif","score":0.7,"rationale":"..."}]\n\n'
        f"Titres :\n{lines}"
    )


def _parse_sentiment_json(content: str, batch: list) -> list:
    m = re.search(r"\[[\s\S]*\]", content)
    try:
        arr = json.loads(m.group(0)) if m else []
    except Exception:
        arr = []
    out = []
    for i, t in enumerate(batch):
        rec = next((x for x in arr if int(x.get("id", -1)) == i + 1), None) or \
            {"sentiment": "neutre", "score": 0.0, "rationale": ""}
        sent = str(rec.get("sentiment", "neutre")).lower().replace("é", "e")
        out.append({
            "text": str(t)[:300],
            "sentiment": sent if sent in ("positif", "neutre", "negatif") else "neutre",
            "score": float(rec.get("score", 0.0) or 0.0),
            "rationale": str(rec.get("rationale", "")).replace("—", ",").replace("–", ","),
            "source": "claude",
        })
    return out


def detect_weak_signals(news_df: Optional[pd.DataFrame] = None,
                        trends_df: Optional[pd.DataFrame] = None) -> list:
    """
    Detecte des signaux faibles a partir des news et des trends.
    Retourne une liste de dicts : {severity, type, brand, message, evidence, detected_at}.
    """
    signals = []
    now = datetime.now().isoformat()

    # ── Actualites : regles par categorie (la plus severe l'emporte) ──
    if news_df is not None and len(news_df) > 0:
        for _, row in news_df.iterrows():
            title = row.get("title", "") or ""
            t = _norm(title)
            for cat, sev, pats in ALERT_RULES:
                hit = next((p for p in pats if re.search(p, t)), None)
                if hit:
                    if cat.startswith("Activité marketing"):
                        cat = "Activité marketing Betclic" if row.get("brand") == "Betclic" \
                            else "Activité marketing concurrente"
                    signals.append({
                        "severity": sev,
                        "type": cat,
                        "brand": row.get("brand", ""),
                        "message": f"{cat} : {title}",
                        "evidence": f"{row.get('source', '')} · {str(row.get('published', ''))[:10]}",
                        "link": row.get("link", ""),
                        "detected_at": now,
                    })
                    break

    # ── Recherches Google : derniere semaine vs moyenne des 11 precedentes ──
    if trends_df is not None and len(trends_df) > 0:
        try:
            df = trends_df.copy()
            df["date"] = pd.to_datetime(df["date"])
            df["interest"] = pd.to_numeric(df["interest"], errors="coerce")
            df = df.dropna(subset=["interest"])
            for kw, grp in df.groupby("keyword"):
                grp = grp.sort_values("date").tail(12)
                if len(grp) < 4:
                    continue
                recent = grp.iloc[-1]["interest"]
                baseline = grp.iloc[:-1]["interest"].mean()
                if baseline < 5:      # volume trop faible pour conclure
                    continue
                ratio = recent / baseline
                if ratio >= 2.0:
                    sev = "high"
                elif ratio >= 1.4:
                    sev = "medium"
                elif ratio <= 0.5:
                    sev = "medium"
                else:
                    continue
                hausse = ratio > 1
                signals.append({
                    "severity": sev,
                    "type": "Recherches Google",
                    "brand": kw,
                    "message": (f"{'Hausse' if hausse else 'Baisse'} des recherches Google sur {kw} : "
                                f"indice {recent:.0f} la dernière semaine contre {baseline:.0f} en moyenne "
                                f"sur les 11 précédentes (× {ratio:.1f})."),
                    "evidence": f"Semaine du {grp.iloc[-1]['date']:%d/%m/%Y} · Côte d'Ivoire",
                    "detected_at": now,
                })
        except Exception:
            pass

    # ── Concentration de la couverture presse ──
    if news_df is not None and len(news_df) > 0 and "brand" in news_df.columns:
        brand_counts = news_df["brand"].value_counts()
        betclic_count = int(brand_counts.get("Betclic", 0))
        total = int(brand_counts.sum())
        for brand, n in brand_counts.items():
            if brand == "Betclic" or total < 10:
                continue
            if n >= max(2 * betclic_count, 4):
                signals.append({
                    "severity": "medium",
                    "type": "Couverture presse",
                    "brand": brand,
                    "message": (f"{brand} obtient {n} articles de presse ivoirienne sur 12 mois, "
                                f"contre {betclic_count} pour Betclic."),
                    "evidence": f"Base : {total} articles retenus",
                    "detected_at": now,
                })

    seen, deduped = set(), []
    for s in signals:
        k = (s.get("type"), s.get("brand"), s.get("message"))
        if k not in seen:
            seen.add(k)
            deduped.append(s)
    order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    deduped.sort(key=lambda s: order.get(s["severity"], 9))
    return deduped


def build_executive_brief(context: dict) -> dict:
    """
    Construit un brief executif.
    context : {
      'news_count_by_brand': dict, 'sentiment_summary': dict, 'signals': list,
      'trends_snapshot': DataFrame (keyword, interest_mean, interest_max),
      'news_titles': list, 'tracker_kpis': dict (optionnel, derniere vague du barometre)
    }
    """
    key = _cache_key("brief", context.get("news_count_by_brand"), context.get("sentiment_summary"),
                     [s.get("message") for s in context.get("signals", [])][:15],
                     context.get("news_titles", [])[:40], context.get("tracker_kpis"),
                     context["trends_snapshot"].to_dict("records")
                     if isinstance(context.get("trends_snapshot"), pd.DataFrame) else None)
    if key in _CACHE:
        return dict(_CACHE[key])

    client = _anthropic_client() if _has_anthropic() else None
    if client is None:
        return _heuristic_brief(context)

    try:
        msg = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": _build_brief_prompt(context)}],
        )
        content = msg.content[0].text if msg.content else ""
        parsed = _parse_brief_json(content)
        for k in ("summary",):
            parsed[k] = str(parsed.get(k, "")).replace("—", ",").replace("–", ",")
        for k in ("key_insights", "threats", "opportunities", "recommendations"):
            parsed[k] = [str(x).replace("—", ",").replace("–", ",") for x in parsed.get(k, [])]
        parsed["source"] = "claude"
        parsed["generated_at"] = datetime.now().isoformat()
        if parsed.get("summary") and not parsed["summary"].startswith("Erreur"):
            _CACHE[key] = parsed
        return dict(parsed)
    except Exception as e:
        brief = _heuristic_brief(context)
        brief["source"] = f"heuristic_fallback:{type(e).__name__}"
        return brief


def _build_brief_prompt(context: dict) -> str:
    news_by_brand = context.get("news_count_by_brand", {})
    sentiment = context.get("sentiment_summary", {})
    signals = [{k: s.get(k) for k in ("severity", "type", "brand", "message")}
               for s in context.get("signals", [])[:15]]
    trends = context.get("trends_snapshot")
    trends_txt = trends.head(20).to_string(index=False) if isinstance(trends, pd.DataFrame) and len(trends) else "n.d."
    titles = "\n".join(f"- {t}" for t in context.get("news_titles", [])[:40])
    kpis = context.get("tracker_kpis") or {}

    return (
        "Tu es analyste senior en veille concurrentielle pour Betclic Côte d'Ivoire, au sein "
        f"d'OpinionWay Africa. {CI_CONTEXT}\n\n"
        "Rédige un brief exécutif à partir des seules données ci-dessous (veille presse ivoirienne, "
        "YouTube et recherches Google sur 12 mois). N'invente aucun fait, chiffre, montant ou "
        "événement absent des données. Écris en français correct avec les accents, sans tiret long. "
        "Les montants éventuels sont en FCFA. Ne cite pas d'opérateur non agréé comme une "
        "opportunité. Reste factuel et actionnable. Respecte les définitions du baromètre : le Top of "
        "Mind est la première marque citée spontanément (ne l'appelle pas notoriété spontanée). "
        "L'indice Google Trends mesure l'intérêt relatif pour le nom de la marque dans les recherches "
        "Google, pas une part de marché. Format français des nombres : virgule décimale et espace "
        "avant % (ex. 51,8 %).\n"
        "Réponds UNIQUEMENT en JSON valide de la forme :\n"
        '{"summary": "...", "key_insights": ["..."], "threats": ["..."], '
        '"opportunities": ["..."], "recommendations": ["..."]}\n'
        "Maximum 4 insights, 3 menaces, 3 opportunités, 4 recommandations, une phrase chacun.\n\n"
        f"Articles de presse ivoirienne par marque (12 mois) : {json.dumps(news_by_brand, ensure_ascii=False)}\n"
        f"Sentiment des titres envers chaque marque : {json.dumps(sentiment, ensure_ascii=False)}\n"
        f"Signaux détectés : {json.dumps(signals, ensure_ascii=False)}\n"
        f"Indice d'intérêt Google en Côte d'Ivoire (0 à 100, moyenne et maximum sur 12 mois) :\n{trends_txt}\n"
        f"Titres des articles les plus récents :\n{titles}\n"
        f"Baromètre OpinionWay (dernière vague, en %) : {json.dumps(kpis, ensure_ascii=False)}\n"
    )


def _parse_brief_json(content: str) -> dict:
    empty = {"summary": "", "key_insights": [], "threats": [], "opportunities": [], "recommendations": []}
    m = re.search(r"\{[\s\S]*\}", content)
    if not m:
        return {**empty, "summary": "Erreur de lecture de la réponse."}
    try:
        return {**empty, **json.loads(m.group(0))}
    except Exception:
        return {**empty, "summary": "Erreur de lecture de la réponse."}


def _heuristic_brief(context: dict) -> dict:
    news_by_brand = context.get("news_count_by_brand", {}) or {}
    sentiment = context.get("sentiment_summary", {}) or {}
    signals = context.get("signals", []) or []

    top_brands = sorted(news_by_brand.items(), key=lambda x: x[1], reverse=True)[:3]
    top_txt = ", ".join(f"{b} ({n} articles)" for b, n in top_brands) or "aucune marque"
    high_sig = [s for s in signals if s.get("severity") == "high"]

    insights = [f"Marques les plus présentes dans la presse ivoirienne sur 12 mois : {top_txt}."]
    total = max(sum(sentiment.values()), 1) if sentiment else 0
    if total:
        insights.append(f"Tonalité des titres : {sentiment.get('positif', 0)} positifs, "
                        f"{sentiment.get('negatif', 0)} négatifs sur {total}.")
    if high_sig:
        insights.append(f"{len(high_sig)} signal(aux) prioritaire(s) à examiner.")
    spikes = [s for s in signals if s.get("type") == "Recherches Google" and s.get("brand") != "Betclic"
              and "Hausse" in s.get("message", "")]
    return {
        "summary": (f"{sum(news_by_brand.values())} articles de presse ivoirienne retenus sur 12 mois, "
                    f"{len(signals)} signaux dont {len(high_sig)} prioritaires."),
        "key_insights": insights[:4],
        "threats": [s["message"] for s in high_sig[:3]],
        "opportunities": ([f"Hausse des recherches sur {spikes[0]['brand']} : en analyser la cause."]
                          if spikes else []),
        "recommendations": [
            "Examiner chaque signal prioritaire avec l'équipe marketing Betclic Côte d'Ivoire.",
            "Suivre l'évolution des recherches Google des principaux concurrents.",
        ],
        "source": "heuristic",
        "generated_at": datetime.now().isoformat(),
    }
