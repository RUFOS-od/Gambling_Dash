"""Briques communes aux vues AI Market Radar (chargement, tonalite, barometre)."""

import pandas as pd
import streamlit as st

from data.collectors import Storage
from data.collectors.base import COMPETITORS, is_affiliate, is_non_ci, other_country_only, clean_title
from components.llm_analyst import classify_sentiment

SOURCES_NOTE = (
    "Sources : presse en ligne (Google Actualités), YouTube et recherches Google, Côte d'Ivoire, "
    "12 derniers mois. Sont retenus les contenus qui citent la marque et concernent la Côte d'Ivoire ; "
    "sont exclus les contenus d'affiliation (codes promo, avis, tutoriels), les contenus en euros "
    "(Betclic France) et les doublons."
)


def load_radar() -> dict:
    """Dernière collecte de chaque source, limitée aux marques suivies."""
    storage = Storage()
    out = {}
    for key, table in [("news", "news"), ("trends", "trends"), ("yt", "youtube_videos")]:
        df = storage.latest(table)
        col = "keyword" if key == "trends" else "brand"
        if len(df) and col in df.columns:
            df = df[df[col].isin(COMPETITORS)].copy()
        if len(df) and "title" in df.columns:
            if "source" in df.columns:
                df["title"] = [clean_title(clean_title(t, s), s) for t, s in zip(df["title"], df["source"].fillna(""))]
            # filtres réappliqués à la lecture (règles enrichies sans attendre une nouvelle collecte)
            bad = df["title"].map(lambda t: is_affiliate(t) or is_non_ci(t))
            if key == "yt":
                bad |= df["title"].map(other_country_only)
            df = df[~bad].copy()
        out[key] = df
    if len(out["trends"]):
        out["trends"]["interest"] = pd.to_numeric(out["trends"]["interest"], errors="coerce").fillna(0)
        out["trends"]["date"] = pd.to_datetime(out["trends"]["date"], errors="coerce")
    if len(out["yt"]):
        out["yt"]["views"] = pd.to_numeric(out["yt"]["views"], errors="coerce").fillna(0).astype(int)
    dates = [pd.to_datetime(df["collected_at"], errors="coerce").max()
             for df in out.values() if len(df) and "collected_at" in df.columns]
    dates = [d for d in dates if pd.notna(d)]
    out["collected_at"] = max(dates) if dates else None
    out["empty"] = all(len(out[k]) == 0 for k in ("news", "trends", "yt"))
    return out


def collected_caption(R: dict) -> str:
    d = R.get("collected_at")
    return f"Dernière collecte : {d:%d/%m/%Y à %H:%M}. {SOURCES_NOTE}" if d is not None else SOURCES_NOTE


def news_sentiment(news: pd.DataFrame) -> pd.DataFrame:
    """Tonalité de chaque titre envers sa marque (IA, mise en cache)."""
    if news is None or len(news) == 0:
        return pd.DataFrame(columns=["brand", "title", "sentiment", "rationale", "link", "published", "source"])
    s = classify_sentiment(news["title"].fillna("").tolist(), news["brand"].tolist())
    out = news[["brand", "title", "link", "published", "source"]].reset_index(drop=True).copy()
    out["sentiment"] = s["sentiment"].values[:len(out)]
    out["score"] = s["score"].values[:len(out)]
    out["rationale"] = s["rationale"].values[:len(out)]
    out.attrs["ai"] = bool(len(s)) and str(s["source"].iloc[0]).startswith("claude")
    return out


def share_of_voice(R: dict) -> dict:
    counts = {}
    for key in ("news", "yt"):
        if len(R[key]):
            for b, n in R[key]["brand"].value_counts().items():
                counts[b] = counts.get(b, 0) + int(n)
    total = sum(counts.values())
    return {b: round(n / total * 100, 1) for b, n in counts.items()} if total else {}, counts, total


def share_of_search(R: dict, weeks: int = 12) -> dict:
    """Part des recherches Google sur les dernières semaines (indice relatif, ancre Betclic)."""
    t = R["trends"]
    if not len(t):
        return {}
    last = t[t["date"] >= t["date"].max() - pd.Timedelta(weeks=weeks)]
    m = last.groupby("keyword")["interest"].mean()
    tot = m.sum()
    return {b: round(v / tot * 100, 1) for b, v in m.items() if v > 0} if tot else {}


def tracker_kpis() -> dict:
    """Repères du baromètre (dernière vague) transmis au brief : TOM, pénétration, PDM."""
    try:
        from data.loader import (sort_vagues, vague_short, calc_tom_all_brands,
                                 calc_penetration_all_brands, calc_pdm_volume_all_brands,
                                 get_main_competitors)
        data = st.session_state.get("data")
        if data is None or not len(data):
            return {}
        lv = sort_vagues(data["Vague"].dropna().unique().tolist())[-1]
        d = data[data["Vague"] == lv]
        main = get_main_competitors(d)
        tom, pen, pdm = calc_tom_all_brands(d), calc_penetration_all_brands(d), calc_pdm_volume_all_brands(d)
        return {"vague": vague_short(lv),
                "definitions": {
                    "top_of_mind": "% des répondants citant la marque EN PREMIER spontanément (Q1A)",
                    "penetration": "% de l'échantillon ayant déjà parié sur la marque (Q5)",
                    "pdm_volume": "part des essais de la marque parmi tous les essais des parieurs (Q5)",
                },
                **{b: {"top_of_mind": tom.get(b), "penetration": pen.get(b), "pdm_volume": pdm.get(b)}
                   for b in main}}
    except Exception:
        return {}
