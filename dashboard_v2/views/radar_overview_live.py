"""AI Market Radar — Vue d'ensemble (donnees reelles issues des collecteurs)."""

from datetime import datetime
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from data.collectors import Storage
from data.collectors.base import COMPETITORS
from components.styles import section_header, insight_box, styled_divider, kpi_card
from components.charts import BETCLIC_RED, OPINIONWAY_PURPLE, COLORS_SEQ, bar_chart_brands
from components.llm_analyst import classify_sentiment, detect_weak_signals


def _empty_state():
    st.warning(
        "Aucune donnee de veille disponible. Cliquez sur **Rafraichir la veille** "
        "dans la sidebar pour lancer la premiere collecte."
    )


def render():
    st.markdown(section_header(
        "AI Market Radar — Vue d'ensemble",
        "Veille concurrentielle sur donnees reelles : Google Trends, News, Meta Ads, YouTube"
    ), unsafe_allow_html=True)

    storage = Storage()
    news_df = storage.latest("news")
    trends_df = storage.latest("trends")
    ads_df = storage.latest("ads")
    yt_df = storage.latest("youtube_videos")

    if all(len(x) == 0 for x in [news_df, trends_df, ads_df, yt_df]):
        _empty_state()
        return

    # ── Share of Voice : basee sur la volumetrie news + videos YouTube ──
    sov_counts = {b: 0 for b in COMPETITORS}
    if len(news_df) > 0:
        for b, n in news_df["brand"].value_counts().items():
            sov_counts[b] = sov_counts.get(b, 0) + int(n)
    if len(yt_df) > 0:
        for b, n in yt_df["brand"].value_counts().items():
            sov_counts[b] = sov_counts.get(b, 0) + int(n)
    total_sov = sum(sov_counts.values()) or 1
    sov_pct = {b: round(v / total_sov * 100, 1) for b, v in sov_counts.items()}

    # ── Sentiment via LLM sur les 100 dernieres news ──
    sentiment_summary = {"positif": 0, "neutre": 0, "negatif": 0}
    sentiment_by_brand = {b: {"positif": 0, "neutre": 0, "negatif": 0} for b in COMPETITORS}
    if len(news_df) > 0:
        sample = news_df.head(100)
        sent_df = classify_sentiment(sample["title"].fillna("").tolist())
        sent_df["brand"] = sample["brand"].values[:len(sent_df)]
        for _, row in sent_df.iterrows():
            s = row["sentiment"]
            sentiment_summary[s] = sentiment_summary.get(s, 0) + 1
            if row["brand"] in sentiment_by_brand:
                sentiment_by_brand[row["brand"]][s] += 1

    # ── KPIs ──
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card(
            "Share of Voice Betclic",
            f"{sov_pct.get('Betclic', 0)}%",
            f"{sov_counts.get('Betclic', 0)} mentions",
            "up" if sov_pct.get("Betclic", 0) > 11 else "neutral",
        ), unsafe_allow_html=True)
    with c2:
        total_sent = max(sum(sentiment_summary.values()), 1)
        pos_pct = round(sentiment_summary["positif"] / total_sent * 100, 1)
        st.markdown(kpi_card(
            "Sentiment Positif",
            f"{pos_pct}%",
            f"{sentiment_summary['positif']} articles",
            "up" if pos_pct > 40 else "down",
        ), unsafe_allow_html=True)
    with c3:
        signals = detect_weak_signals(news_df=news_df, trends_df=trends_df)
        n_high = sum(1 for s in signals if s["severity"] == "high")
        st.markdown(kpi_card(
            "Alertes critiques",
            str(n_high),
            f"{len(signals)} signaux au total",
            "down" if n_high > 0 else "up",
        ), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card(
            "Volume news (7j)",
            str(len(news_df)),
            "articles collectes",
            "neutral",
        ), unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Share of Voice bar chart ──
    col_a, col_b = st.columns(2)
    with col_a:
        fig = bar_chart_brands(sov_pct, "Share of Voice (%)", height=400)
        st.plotly_chart(fig, width='stretch')

    with col_b:
        # Intensite publicitaire basee sur le nombre d'ads Meta
        ads_counts = {b: 0 for b in COMPETITORS}
        if len(ads_df) > 0:
            for b, n in ads_df["brand"].value_counts().items():
                ads_counts[b] = int(n)
        if sum(ads_counts.values()) == 0:
            st.info(
                "Meta Ad Library : aucune donnee. Definir la variable "
                "d'environnement `META_ACCESS_TOKEN` pour activer la collecte."
            )
        else:
            fig = bar_chart_brands(ads_counts, "Intensite Publicitaire (nb pubs actives)", height=400)
            st.plotly_chart(fig, width='stretch')

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Sentiment empile ──
    if sum(sum(v.values()) for v in sentiment_by_brand.values()) > 0:
        brands_sorted = sorted(COMPETITORS, key=lambda b: sentiment_by_brand[b]["positif"], reverse=True)
        fig = go.Figure()
        for label, color in [("positif", "#1D8348"), ("neutre", "#94A3B8"), ("negatif", "#C0392B")]:
            fig.add_trace(go.Bar(
                name=label.capitalize(),
                x=brands_sorted,
                y=[sentiment_by_brand[b][label] for b in brands_sorted],
                marker_color=color,
            ))
        fig.update_layout(
            barmode="stack",
            title="Sentiment par marque (articles classifies)",
            height=400,
            paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(l=20, r=20, t=50, b=40),
        )
        st.plotly_chart(fig, width='stretch')

    # ── Insight synthetique ──
    leaders = sorted(sov_pct.items(), key=lambda x: x[1], reverse=True)[:3]
    leaders_txt = ", ".join(f"<strong>{b}</strong> ({v}%)" for b, v in leaders)
    st.markdown(insight_box(
        f"Classement Share of Voice : {leaders_txt}. "
        f"Alertes critiques detectees cette vague : <strong>{n_high}</strong>."
    ), unsafe_allow_html=True)
