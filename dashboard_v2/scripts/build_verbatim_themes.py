"""
Thématise les verbatims NPS Q16 (raison de la note) en thèmes actionnables
via Claude API. À exécuter à chaque mise à jour des données.

Usage :
    python dashboard_v2/scripts/build_verbatim_themes.py [--vague 1]
    python dashboard_v2/scripts/build_verbatim_themes.py --all

Pré-requis : ANTHROPIC_API_KEY défini en variable d'environnement OU
             présent dans dashboard_v2/.streamlit/secrets.toml.

Output : dashboard_v2/data/verbatim_themes/Vague_N.json
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Make dashboard_v2 importable
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))


# ── Bridge st.secrets → os.environ (so the same secrets file works locally) ──
def _load_secrets_into_env():
    secrets_path = HERE / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        return
    try:
        import tomllib  # py 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return
    with open(secrets_path, "rb") as f:
        data = tomllib.load(f)
    for k, v in data.items():
        if k not in os.environ and isinstance(v, str) and v:
            os.environ[k] = v


_load_secrets_into_env()

# Stub streamlit for the data loader import
import types as _types
_st = _types.ModuleType("streamlit")
class _Cache:
    def __init__(self, *a, **k): pass
    def __call__(self, f): return f
_st.cache_data = _Cache
_st.cache_resource = _Cache
sys.modules["streamlit"] = _st

from data.loader import load_raw_data, get_utilisateurs_betclic  # noqa: E402


PROMPT_TEMPLATE = """Tu es un analyste senior en études de marché pour OpinionWay
qui audite la marque Betclic en Côte d'Ivoire.

Voici les verbatims (réponses ouvertes) à la question Q16 : "Pourquoi cette note ?"
posée juste après la note de recommandation NPS (Q15) aux utilisateurs principaux
de Betclic. Ces verbatims sont issus exclusivement de {nps_category} (note NPS {nps_range}).

Volume total : {n_total} verbatims.

VERBATIMS (un par ligne, numérotés) :
{verbatims_block}

TÂCHE : regroupe ces verbatims en 5 à 7 thèmes business actionnables.
- Un thème = un cluster de verbatims qui parlent du MÊME sujet (même si les mots diffèrent).
- Le label du thème doit être court (3-6 mots), spécifique et actionnable
  (ex : "Retraits difficiles / délais longs", "Cotes peu compétitives",
  "Service client réactif", "Sécurité perçue forte").
- Pour chaque thème, donne le nombre exact de verbatims qui s'y rattachent
  (la somme doit être <= {n_total}).
- Pour chaque thème, fournis 2 verbatims illustratifs VERBATIM (sans les modifier).
- Trie les thèmes par count décroissant.

Réponds UNIQUEMENT en JSON valide selon ce schéma :
{{
  "themes": [
    {{
      "label": "string",
      "count": int,
      "illustrative_quotes": ["verbatim 1", "verbatim 2"]
    }}
  ]
}}
"""


def _build_verbatims_block(verbatims: list) -> str:
    return "\n".join(f"{i+1}. {v.strip()}" for i, v in enumerate(verbatims))


def _call_claude(verbatims: list, nps_category: str, nps_range: str) -> dict:
    import anthropic

    n_total = len(verbatims)
    prompt = PROMPT_TEMPLATE.format(
        nps_category=nps_category,
        nps_range=nps_range,
        n_total=n_total,
        verbatims_block=_build_verbatims_block(verbatims),
    )
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text if msg.content else ""
    # Extract first JSON block
    import re
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise RuntimeError(f"Pas de JSON dans la réponse Claude:\n{raw[:500]}")
    return json.loads(match.group(0))


def _enrich_themes(themes: list, n_total: int) -> list:
    """Add share_pct field, sort, sanity-check counts."""
    enriched = []
    for t in themes:
        count = int(t.get("count", 0))
        enriched.append({
            "label": t["label"].strip(),
            "count": count,
            "share_pct": round(count / n_total * 100, 1) if n_total > 0 else 0.0,
            "illustrative_quotes": [q.strip() for q in t.get("illustrative_quotes", [])][:2],
        })
    enriched.sort(key=lambda x: -x["count"])
    return enriched


def process_vague(df: pd.DataFrame, vague: str) -> dict:
    """Build theme dict for one wave (detractors + promoters)."""
    df_v = df[df["Vague"] == vague]
    users = get_utilisateurs_betclic(df_v)
    out = {
        "wave": vague,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "model": "claude-opus-4-7",
    }
    for nps_cat, nps_range, key in [
        ("Détracteurs", "0-6", "detractors"),
        ("Promoteurs", "9-10", "promoters"),
    ]:
        sub = users[users["NPS_Categorie"] == nps_cat.rstrip("s")]
        verbatims = sub["Principal_Irritant"].dropna().astype(str).tolist()
        verbatims = [v for v in verbatims if v.strip() and v.strip() != "0"]
        n = len(verbatims)
        print(f"  → {nps_cat} ({nps_range}) : {n} verbatims")
        if n < 3:
            out[key] = {"n_total": n, "themes": [],
                        "note": "Base trop faible pour thématiser."}
            continue
        try:
            result = _call_claude(verbatims, nps_cat, nps_range)
            themes = _enrich_themes(result.get("themes", []), n)
            out[key] = {"n_total": n, "themes": themes}
            print(f"    ✓ {len(themes)} thèmes identifiés")
        except Exception as e:
            out[key] = {"n_total": n, "themes": [],
                        "error": f"{type(e).__name__}: {e}"}
            print(f"    ✗ Erreur: {e}")
    return out


def save_themes(themes_dict: dict, wave: str):
    target = HERE / "data" / "verbatim_themes" / f"{wave.replace(' ', '_')}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(themes_dict, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Sauvé : {target.relative_to(HERE.parent)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vague", type=int, default=None,
                        help="Numéro de vague à traiter (ex: 1). Par défaut : toutes.")
    parser.add_argument("--all", action="store_true",
                        help="Traite toutes les vagues disponibles.")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY manquante. Définir dans secrets.toml ou env.")
        sys.exit(1)

    df = load_raw_data()
    vagues = sorted(df["Vague"].dropna().unique().tolist())
    if args.vague is not None and not args.all:
        target = f"Vague {args.vague}"
        if target not in vagues:
            print(f"❌ {target} introuvable. Vagues disponibles : {vagues}")
            sys.exit(1)
        vagues = [target]

    for vague in vagues:
        print(f"\n▶ Traitement {vague}...")
        themes = process_vague(df, vague)
        save_themes(themes, vague)

    print("\n✅ Terminé.")


if __name__ == "__main__":
    main()
