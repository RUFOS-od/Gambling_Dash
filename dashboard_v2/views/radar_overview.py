"""AI Market Radar — Overview."""

import streamlit as st
from data.simulator import (
    generate_share_of_voice, generate_sentiment_data, generate_ad_intensity,
    generate_risk_levels, generate_positioning_data, generate_social_mentions,
    COMPETITORS
)
from data.loader import calc_tom_all_brands, calc_notoriete_all_brands, load_raw_data
from components.styles import kpi_card, section_header, insight_box, styled_divider
from components.charts import (
    bubble_chart, bar_chart_brands, donut_chart, stacked_bar,
    BETCLIC_RED, OPINIONWAY_PURPLE, COLORS_SEQ
)


def render():
    st.markdown(section_header(
        "AI Market Radar — Vue d'ensemble",
        "Veille concurrentielle augmentée par IA | 9 acteurs du marché ivoirien des paris sportifs"
    ), unsafe_allow_html=True)

    sov = generate_share_of_voice()
    sentiment = generate_sentiment_data()
    ad_intensity = generate_ad_intensity()
    risks = generate_risk_levels()

    # ── Top KPIs ──
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        betclic_sov = sov.get("Betclic", 0)
        st.markdown(kpi_card("Share of Voice", f"{betclic_sov}%", "+2.3 pt", "up"), unsafe_allow_html=True)
    with col2:
        sent_betclic = sentiment.get("Betclic", {})
        st.markdown(kpi_card("Sentiment Positif", f"{sent_betclic.get('Positif', 0)}%", "+3.1 pt", "up"), unsafe_allow_html=True)
    with col3:
        high_risk = sum(1 for b, r in risks.items() if r["level"] == "Élevé")
        st.markdown(kpi_card("Risque Élevé", str(high_risk), "concurrents", "neutral"), unsafe_allow_html=True)
    with col4:
        st.markdown(kpi_card("Alertes Actives", "6", "+2 / semaine", "up"), unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Positioning Bubble Chart ──
    pos_data = generate_positioning_data()
    fig = bubble_chart(pos_data, "Positionnement Concurrentiel — Share of Voice vs Sentiment Positif", height=500)
    fig.update_xaxes(title_text="Share of Voice (%)")
    fig.update_yaxes(title_text="Sentiment Positif (%)")
    st.plotly_chart(fig, width='stretch')

    st.markdown(insight_box(
        "<strong>Betclic domine le quadrant supérieur droit</strong> avec le meilleur ratio Share of Voice / Sentiment. "
        "<strong>1XBET</strong> maintient une forte présence vocale mais avec un sentiment plus mitigé. "
        "<strong>Sportcash</strong> régresse en visibilité mais conserve un socle fidèle."
    ), unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Share of Voice + Ad Intensity ──
    col_left, col_right = st.columns(2)

    with col_left:
        fig = bar_chart_brands(sov, "Share of Voice (%)", height=400)
        st.plotly_chart(fig, width='stretch')

    with col_right:
        fig = bar_chart_brands(ad_intensity, "Intensité Publicitaire (score /100)", height=400)
        st.plotly_chart(fig, width='stretch')

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Sentiment comparison ──
    brands_sorted = sorted(COMPETITORS, key=lambda b: sentiment.get(b, {}).get("Positif", 0), reverse=True)
    series = {
        "Positif": [sentiment[b]["Positif"] for b in brands_sorted],
        "Neutre": [sentiment[b]["Neutre"] for b in brands_sorted],
        "Négatif": [sentiment[b]["Négatif"] for b in brands_sorted],
    }
    fig = stacked_bar(brands_sorted, series, "Analyse de Sentiment par marque (%)", height=400)
    st.plotly_chart(fig, width='stretch')

    # ── Risk matrix ──
    st.markdown(styled_divider(), unsafe_allow_html=True)
    st.markdown(section_header("Matrice de Risque Concurrentiel"), unsafe_allow_html=True)

    risk_cols = st.columns(4)
    for i, (brand, risk) in enumerate(sorted(risks.items(), key=lambda x: x[1]["score"], reverse=True)):
        if brand == "Betclic":
            continue
        col_idx = i % 4
        with risk_cols[col_idx]:
            level = risk["level"]
            color_map = {"Élevé": "down", "Modéré": "neutral", "Faible": "up"}
            st.markdown(kpi_card(
                brand, level,
                f"Score: {int(risk['score'])} | {risk['trend']}",
                color_map.get(level, "neutral")
            ), unsafe_allow_html=True)
            st.markdown("", unsafe_allow_html=True)
