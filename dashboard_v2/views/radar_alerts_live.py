"""AI Market Radar — Alertes & Signaux (donnees reelles + brief executif IA)."""

import pandas as pd
import streamlit as st

from data.collectors import Storage
from data.collectors.base import COMPETITORS
from components.styles import section_header, styled_divider, alert_box
from components.llm_analyst import (
    detect_weak_signals, build_executive_brief, classify_sentiment,
)


SEVERITY_STYLES = {
    "high":   ("#C0392B", "CRITIQUE"),
    "medium": ("#D4760A", "MODEREE"),
    "low":    ("#1D8348", "FAIBLE"),
    "info":   ("#4A5568", "INFO"),
}


def _signal_card(s: dict) -> str:
    color, label = SEVERITY_STYLES.get(s["severity"], ("#4A5568", "INFO"))
    brand_txt = f" — <strong>{s['brand']}</strong>" if s.get("brand") else ""
    return (
        f'<div style="background:#FFFFFF;border-left:4px solid {color};'
        f'padding:0.8rem 1rem;margin-bottom:0.6rem;border-radius:0 8px 8px 0;'
        f'box-shadow:0 2px 6px rgba(0,0,0,0.04);">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span style="color:{color};font-weight:700;letter-spacing:0.05em;">{label}{brand_txt}</span>'
        f'<span style="color:#7B8794;font-size:0.78rem;">{s.get("detected_at","")[:16].replace("T"," ")}</span>'
        f'</div>'
        f'<div style="margin-top:0.3rem;color:#1A1D23;">{s["message"]}</div>'
        f'<div style="margin-top:0.2rem;color:#4A5568;font-size:0.82rem;font-style:italic;">{s.get("evidence","")}</div>'
        f'</div>'
    )


def render():
    st.markdown(section_header(
        "Alertes & Signaux Faibles",
        "Détection automatique : pics de recherche, mots-clés réglementaires, brief exécutif IA"
    ), unsafe_allow_html=True)

    storage = Storage()
    news_df = storage.latest("news")
    trends_df = storage.latest("trends")

    if len(news_df) == 0 and len(trends_df) == 0:
        st.warning("Aucune donnée de veille. Lancez une collecte depuis le menu latéral.")
        return

    signals = detect_weak_signals(news_df=news_df, trends_df=trends_df)

    # ── Resumes ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total signaux", len(signals))
    c2.metric("Critiques", sum(1 for s in signals if s["severity"] == "high"))
    c3.metric("Moderes", sum(1 for s in signals if s["severity"] == "medium"))
    c4.metric("Faibles", sum(1 for s in signals if s["severity"] == "low"))

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Liste des signaux ──
    st.markdown("### Signaux detectes")
    if signals:
        for s in signals[:30]:
            st.markdown(_signal_card(s), unsafe_allow_html=True)
    else:
        st.markdown(alert_box(
            "Aucun signal faible detecte sur le dernier cycle. Marche stable.",
            "success",
        ), unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Brief executif IA ──
    st.markdown("### Brief exécutif — Analyse IA")
    with st.spinner("Generation du brief..."):
        # Pre-calcul du sentiment agrege
        sent_summary = {"positif": 0, "neutre": 0, "negatif": 0}
        if len(news_df) > 0:
            sample = news_df.head(80)
            sent_df = classify_sentiment(sample["title"].fillna("").tolist())
            for k, v in sent_df["sentiment"].value_counts().items():
                sent_summary[k] = int(v)

        news_by_brand = news_df["brand"].value_counts().to_dict() if len(news_df) else {}

        trends_snapshot = pd.DataFrame()
        if len(trends_df) > 0:
            df_t = trends_df.copy()
            df_t["interest"] = pd.to_numeric(df_t["interest"], errors="coerce").fillna(0)
            trends_snapshot = df_t.groupby("keyword")["interest"].agg(["mean", "max"]).reset_index()
            trends_snapshot.columns = ["keyword", "interest_mean", "interest_max"]

        brief = build_executive_brief({
            "news_count_by_brand": news_by_brand,
            "sentiment_summary": sent_summary,
            "signals": signals,
            "trends_snapshot": trends_snapshot,
        })

    if brief.get("source", "").startswith("claude"):
        st.caption(f"Brief généré par IA · {brief.get('generated_at','')[:16].replace('T',' ')}")
    else:
        st.caption("Brief généré en mode dégradé (analyse lexicale).")

    # Rendu
    st.markdown(f"**Resume executif.** {brief.get('summary','')}")

    col_i, col_t = st.columns(2)
    with col_i:
        st.markdown("**Insights cles**")
        for it in brief.get("key_insights", []):
            st.markdown(f"- {it}")
    with col_t:
        st.markdown("**Menaces identifiees**")
        for it in brief.get("threats", []):
            st.markdown(f"- {it}")

    col_o, col_r = st.columns(2)
    with col_o:
        st.markdown("**Opportunites**")
        for it in brief.get("opportunities", []):
            st.markdown(f"- {it}")
    with col_r:
        st.markdown("**Recommandations**")
        for it in brief.get("recommendations", []):
            st.markdown(f"- {it}")
