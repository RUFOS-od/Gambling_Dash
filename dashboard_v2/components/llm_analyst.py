"""
Couche d'intelligence : analyse semantique des donnees collectees via Claude API.
Si ANTHROPIC_API_KEY n'est pas definie, bascule sur des heuristiques deterministes
(lexique francais de sentiment + detection de mots-cles d'alerte).

Trois fonctions publiques :
  - classify_sentiment(texts) -> DataFrame avec colonnes sentiment, score, rationale
  - detect_weak_signals(news_df, trends_df) -> list of signal dicts
  - build_executive_brief(context) -> dict avec summary, key_insights, recommendations
"""

import os
import re
import json
from datetime import datetime
from typing import Optional
import pandas as pd


ANTHROPIC_MODEL = "claude-opus-4-7"  # best for reasoning
MAX_BATCH_SIZE = 30


# ────────────────────────────────────────────────────────────
# Fallback heuristique : lexique francais
# ────────────────────────────────────────────────────────────
POS_WORDS = {
    "excellent", "super", "parfait", "top", "bravo", "merci", "fiable", "rapide",
    "facile", "securise", "recommande", "genial", "bonne", "bon", "content",
    "satisfait", "efficace", "pratique", "meilleur", "qualite", "innovant",
    "performant", "gagner", "gagnant", "bonus", "promo", "cadeau", "cote",
}
NEG_WORDS = {
    "arnaque", "nul", "mauvais", "bug", "panne", "retrait", "bloque", "escroc",
    "fraude", "lent", "probleme", "erreur", "deconnexion", "perdu", "vole",
    "plainte", "pourri", "scam", "faux", "decu", "catastrophe", "pire",
    "refuse", "triche", "voleur", "impayé", "impaye", "attente",
}
ALERT_PATTERNS = [
    # Réglementaire / juridique
    r"\blicence\b", r"\binterdit", r"\bregulateur", r"\bregulation",
    r"\bsuspens", r"\bsanction", r"\bamende\b", r"\benqu[eê]te",
    r"\bscandale", r"\bpolitique\b", r"\bgouvernement", r"\bjustice",
    r"\bproces", r"\bfraude", r"\bcondamn",
    # Opérationnel critique
    r"\bbloque", r"\bblocage", r"\bpanne\b", r"\bcoupure",
    r"\bpiratage", r"\bcyberatt", r"\bhack",
    r"\bretrait impossib", r"\bcompte\s+bloque", r"\bcompte\s+suspendu",
    # Marketing concurrent agressif
    r"\bbonus\s+\d+%", r"\boffre\s+exclus", r"\blancement\b",
    r"\bnouveau\s+sponsor", r"\bpartenariat",
    # Jeu responsable / addiction
    r"\baddict", r"\bdependa", r"\bjeu\s+responsable",
    # Communication crise
    r"\bcrise\b", r"\balerte\b", r"\bd[eé]non",
]


def _norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-zàâäéèêëîïôöùûüç\s]", " ", s)
    return s


def _heuristic_sentiment(text: str) -> dict:
    norm = _norm(text)
    tokens = set(norm.split())
    pos_hits = len(tokens & POS_WORDS)
    neg_hits = len(tokens & NEG_WORDS)
    score = pos_hits - neg_hits
    if score > 0:
        label = "positif"
    elif score < 0:
        label = "negatif"
    else:
        label = "neutre"
    return {
        "sentiment": label,
        "score": max(-1.0, min(1.0, score / 3.0)),
        "rationale": f"pos={pos_hits} neg={neg_hits}",
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

def classify_sentiment(texts: list) -> pd.DataFrame:
    """
    Classifie le sentiment d'une liste de textes courts.
    Colonnes retournees : text, sentiment (positif/neutre/negatif), score [-1,1], rationale, source.
    """
    rows = []
    if not texts:
        return pd.DataFrame(columns=["text", "sentiment", "score", "rationale", "source"])

    client = _anthropic_client() if _has_anthropic() else None
    if client is None:
        # Fallback heuristique
        for t in texts:
            res = _heuristic_sentiment(str(t))
            res.update({"text": str(t)[:300], "source": "heuristic"})
            rows.append(res)
        return pd.DataFrame(rows)

    # Batch appels Claude
    try:
        batches = [texts[i:i + MAX_BATCH_SIZE] for i in range(0, len(texts), MAX_BATCH_SIZE)]
        for batch in batches:
            prompt = _build_sentiment_prompt(batch)
            msg = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            content = msg.content[0].text if msg.content else ""
            parsed = _parse_sentiment_json(content, batch)
            rows.extend(parsed)
        return pd.DataFrame(rows)
    except Exception as e:
        # En cas d'echec Claude, fallback transparent
        rows = []
        for t in texts:
            res = _heuristic_sentiment(str(t))
            res.update({"text": str(t)[:300], "source": f"heuristic_fallback:{type(e).__name__}"})
            rows.append(res)
        return pd.DataFrame(rows)


def _build_sentiment_prompt(batch: list) -> str:
    lines = "\n".join(f"{i+1}. {str(t)[:280]}" for i, t in enumerate(batch))
    return (
        "Tu es un analyste de sentiment pour le marche des paris sportifs en Cote d'Ivoire. "
        "Pour chaque texte numerote, donne le sentiment (positif, neutre, negatif), un score "
        "entre -1 et 1, et une justification tres courte (max 10 mots). "
        "Reponds UNIQUEMENT en JSON valide de la forme :\n"
        '[{"id":1,"sentiment":"positif","score":0.7,"rationale":"..."}]\n\n'
        f"Textes :\n{lines}"
    )


def _parse_sentiment_json(content: str, batch: list) -> list:
    # Extraire le bloc JSON
    m = re.search(r"\[[\s\S]*\]", content)
    if not m:
        return [
            {"text": str(t)[:300], "sentiment": "neutre", "score": 0.0,
             "rationale": "parse_failed", "source": "claude_parse_failed"}
            for t in batch
        ]
    try:
        arr = json.loads(m.group(0))
    except Exception:
        return [
            {"text": str(t)[:300], "sentiment": "neutre", "score": 0.0,
             "rationale": "json_error", "source": "claude_parse_failed"}
            for t in batch
        ]

    out = []
    for i, t in enumerate(batch):
        rec = next((x for x in arr if int(x.get("id", -1)) == i + 1), None)
        if not rec:
            rec = {"sentiment": "neutre", "score": 0.0, "rationale": "missing"}
        out.append({
            "text": str(t)[:300],
            "sentiment": rec.get("sentiment", "neutre"),
            "score": float(rec.get("score", 0.0)),
            "rationale": rec.get("rationale", ""),
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

    # ── Signaux a partir des news ──
    if news_df is not None and len(news_df) > 0:
        for _, row in news_df.iterrows():
            title = (row.get("title", "") or "") + " " + (row.get("summary", "") or "")
            title_l = title.lower()
            for pat in ALERT_PATTERNS:
                if re.search(pat, title_l):
                    signals.append({
                        "severity": "high",
                        "type": "regulatory_or_reputational",
                        "brand": row.get("brand", ""),
                        "message": f"Mot-cle d'alerte detecte dans l'actualite : {pat}",
                        "evidence": row.get("title", "")[:200],
                        "detected_at": now,
                    })
                    break

    # ── Signaux a partir des trends (pic vs moyenne) ──
    # Seuils permissifs : 1.3x = pic notable, 0.7x = chute notable.
    # Minimum 3 points pour avoir une baseline.
    if trends_df is not None and len(trends_df) > 0:
        try:
            df = trends_df.copy()
            df["date"] = pd.to_datetime(df["date"])
            df["interest"] = pd.to_numeric(df["interest"], errors="coerce")
            df = df.dropna(subset=["interest"])
            for kw, grp in df.groupby("keyword"):
                grp = grp.sort_values("date").tail(12)
                if len(grp) < 3:
                    continue
                recent = grp.iloc[-1]["interest"]
                baseline = grp.iloc[:-1]["interest"].mean()
                if baseline <= 0:
                    continue
                ratio = recent / baseline
                if ratio >= 2.0:
                    sev = "high"
                elif ratio >= 1.3:
                    sev = "medium"
                elif ratio <= 0.5:
                    sev = "medium"
                elif ratio <= 0.7:
                    sev = "low"
                else:
                    continue
                direction = "Pic" if ratio > 1 else "Chute"
                signals.append({
                    "severity": sev,
                    "type": "trend_spike" if ratio > 1 else "trend_drop",
                    "brand": kw,
                    "message": f"{direction} d'intérêt de recherche : {recent:.0f} vs moyenne {baseline:.0f} ({ratio:.1f}×)",
                    "evidence": f"keyword={kw}, ratio={ratio:.2f}",
                    "detected_at": now,
                })
        except Exception as e:
            signals.append({
                "severity": "info",
                "type": "system",
                "brand": "",
                "message": f"Détection trends impossible : {e}",
                "evidence": "",
                "detected_at": now,
            })

    # ── Signaux de volume de mentions news (concentration concurrentielle) ──
    if news_df is not None and len(news_df) > 0 and "brand" in news_df.columns:
        try:
            brand_counts = news_df["brand"].value_counts()
            if len(brand_counts) >= 2:
                top_brand = brand_counts.index[0]
                top_count = int(brand_counts.iloc[0])
                betclic_count = int(brand_counts.get("Betclic", 0))
                # Si un concurrent capte > 2x le volume Betclic, c'est notable
                if top_brand != "Betclic" and betclic_count > 0 and top_count >= betclic_count * 2:
                    signals.append({
                        "severity": "high",
                        "type": "competitor_volume_dominance",
                        "brand": top_brand,
                        "message": f"{top_brand} capte {top_count} mentions presse contre {betclic_count} pour Betclic ({top_count/betclic_count:.1f}× le volume)",
                        "evidence": f"{top_brand}={top_count}, Betclic={betclic_count}",
                        "detected_at": now,
                    })
                # Si un concurrent émergent dépasse 30% du volume total
                total = brand_counts.sum()
                for brand, n in brand_counts.head(5).items():
                    if brand == "Betclic":
                        continue
                    share = n / total
                    if share >= 0.30:
                        signals.append({
                            "severity": "medium",
                            "type": "competitor_share_high",
                            "brand": brand,
                            "message": f"{brand} concentre {share*100:.0f}% des mentions presse ({n} articles)",
                            "evidence": f"{brand} share={share*100:.1f}%",
                            "detected_at": now,
                        })
        except Exception:
            pass

    # Dédoublonner par (type, brand, message)
    seen = set()
    deduped = []
    for s in signals:
        key = (s.get("type"), s.get("brand"), s.get("message"))
        if key not in seen:
            seen.add(key)
            deduped.append(s)
    signals = deduped

    # Trier par sévérité
    order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    signals.sort(key=lambda s: order.get(s["severity"], 9))
    return signals


def build_executive_brief(context: dict) -> dict:
    """
    Construit un brief hebdomadaire executif.
    context : {
      'news_count_by_brand': dict,
      'trends_snapshot': DataFrame (keyword, interest, evolution_pct),
      'signals': list,
      'sentiment_summary': {positif:n, neutre:n, negatif:n}
    }
    """
    # Construire un contexte textuel
    client = _anthropic_client() if _has_anthropic() else None
    if client is None:
        return _heuristic_brief(context)

    try:
        prompt = _build_brief_prompt(context)
        msg = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        content = msg.content[0].text if msg.content else ""
        parsed = _parse_brief_json(content)
        parsed["source"] = "claude"
        parsed["generated_at"] = datetime.now().isoformat()
        return parsed
    except Exception as e:
        brief = _heuristic_brief(context)
        brief["source"] = f"heuristic_fallback:{type(e).__name__}"
        return brief


def _build_brief_prompt(context: dict) -> str:
    news_by_brand = context.get("news_count_by_brand", {})
    sentiment = context.get("sentiment_summary", {})
    signals = context.get("signals", [])[:10]
    trends = context.get("trends_snapshot")

    trends_txt = ""
    if isinstance(trends, pd.DataFrame) and len(trends) > 0:
        trends_txt = trends.head(20).to_string(index=False)

    return (
        "Tu es un analyste senior en veille concurrentielle pour Betclic Cote d'Ivoire. "
        "Sur la base des donnees ci-dessous, redige un brief executif hebdomadaire. "
        "Reponds UNIQUEMENT en JSON valide de la forme :\n"
        '{"summary": "...", "key_insights": ["...", "..."], '
        '"threats": ["..."], "opportunities": ["..."], "recommendations": ["..."]}\n\n'
        f"Volumes de news par marque : {json.dumps(news_by_brand, ensure_ascii=False)}\n\n"
        f"Sentiment agrege : {json.dumps(sentiment, ensure_ascii=False)}\n\n"
        f"Signaux detectes : {json.dumps(signals, ensure_ascii=False, default=str)}\n\n"
        f"Tendances Google (extrait) :\n{trends_txt}\n\n"
        "Ton : professionnel, concret, actionnable. Maximum 4 insights, 3 menaces, "
        "3 opportunites, 4 recommandations. Chaque point doit tenir en une phrase."
    )


def _parse_brief_json(content: str) -> dict:
    m = re.search(r"\{[\s\S]*\}", content)
    if not m:
        return {
            "summary": "Erreur de parsing de la reponse.",
            "key_insights": [],
            "threats": [],
            "opportunities": [],
            "recommendations": [],
        }
    try:
        return json.loads(m.group(0))
    except Exception:
        return {
            "summary": "Erreur de parsing JSON.",
            "key_insights": [],
            "threats": [],
            "opportunities": [],
            "recommendations": [],
        }


def _heuristic_brief(context: dict) -> dict:
    news_by_brand = context.get("news_count_by_brand", {}) or {}
    sentiment = context.get("sentiment_summary", {}) or {}
    signals = context.get("signals", []) or []

    top_brands = sorted(news_by_brand.items(), key=lambda x: x[1], reverse=True)[:3]
    top_brands_txt = ", ".join(f"{b} ({n} articles)" for b, n in top_brands) or "aucune marque detectee"

    high_sig = [s for s in signals if s.get("severity") == "high"]

    insights = []
    if top_brands:
        insights.append(f"Marques les plus mediatisees cette semaine : {top_brands_txt}.")
    if sentiment:
        pos = sentiment.get("positif", 0)
        neg = sentiment.get("negatif", 0)
        total = max(pos + neg + sentiment.get("neutre", 0), 1)
        insights.append(
            f"Sentiment global : {pos}/{total} positif, {neg}/{total} negatif."
        )
    if high_sig:
        insights.append(f"{len(high_sig)} alerte(s) rouge(s) detectee(s) : surveillance rapprochee requise.")

    threats = [f"Alerte : {s['message']} ({s.get('brand','?')})" for s in high_sig[:3]]
    opportunities = []
    if any(s.get("type") == "trend_spike" for s in signals):
        spikes = [s for s in signals if s.get("type") == "trend_spike" and s.get("brand") != "Betclic"]
        if spikes:
            opportunities.append(
                f"Pic d'interet sur {spikes[0]['brand']} : analyser les causes pour reaction tactique."
            )

    recommendations = [
        "Maintenir la pression mediatique et la presence digitale.",
        "Surveiller les pics de recherche inhabituels sur les concurrents.",
    ]
    if high_sig:
        recommendations.insert(0, "Escalader immediatement les alertes critiques au comite de direction.")

    return {
        "summary": (
            f"Semaine sous surveillance : {sum(news_by_brand.values())} articles, "
            f"{len(signals)} signaux dont {len(high_sig)} critiques."
        ),
        "key_insights": insights[:4],
        "threats": threats[:3],
        "opportunities": opportunities[:3] or ["A determiner au prochain cycle."],
        "recommendations": recommendations[:4],
        "source": "heuristic",
        "generated_at": datetime.now().isoformat(),
    }
