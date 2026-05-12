"""AI Market Radar — Social & Sentiment Analysis."""

import streamlit as st
import plotly.graph_objects as go
from data.simulator import (
    generate_social_mentions, generate_sentiment_data, generate_share_of_voice,
    COMPETITORS
)
from components.styles import kpi_card, section_header, insight_box, styled_divider
from components.charts import stacked_bar, donut_chart, BETCLIC_RED, OPINIONWAY_PURPLE, COLORS_SEQ


def render():
    st.markdown(section_header(
        "Social & Sentiment Analysis",
        "Monitoring des conversations sociales et analyse de sentiment par IA"
    ), unsafe_allow_html=True)

    mentions = generate_social_mentions()
    sentiment = generate_sentiment_data()
    sov = generate_share_of_voice()

    # ── Total mentions KPI ──
    total_mentions = {brand: sum(weeks.values()) for brand, weeks in mentions.items()}
    betclic_total = total_mentions.get("Betclic", 0)
    market_total = sum(total_mentions.values())

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(kpi_card("Mentions Betclic", f"{betclic_total:,}", "+8%", "up"), unsafe_allow_html=True)
    with col2:
        st.markdown(kpi_card("Total Marché", f"{market_total:,}", None, "neutral"), unsafe_allow_html=True)
    with col3:
        sent_b = sentiment.get("Betclic", {})
        st.markdown(kpi_card("Sentiment Positif", f"{sent_b.get('Positif', 0)}%", "+3.1 pt", "up"), unsafe_allow_html=True)
    with col4:
        st.markdown(kpi_card("SOV Betclic", f"{sov.get('Betclic', 0)}%", "+2.3 pt", "up"), unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Weekly mentions evolution ──
    weeks = list(next(iter(mentions.values())).keys())
    fig = go.Figure()

    # Sort brands by total mentions
    sorted_brands = sorted(COMPETITORS, key=lambda b: total_mentions.get(b, 0), reverse=True)

    for i, brand in enumerate(sorted_brands[:5]):  # Top 5
        vals = [mentions[brand][w] for w in weeks]
        color = BETCLIC_RED if brand == "Betclic" else COLORS_SEQ[i % len(COLORS_SEQ)]
        width = 3 if brand == "Betclic" else 1.5
        fig.add_trace(go.Scatter(
            x=weeks, y=vals, name=brand,
            mode="lines+markers",
            line=dict(color=color, width=width),
            marker=dict(size=8 if brand == "Betclic" else 5),
        ))

    fig.update_layout(
        title="Évolution des mentions sociales — Top 5 marques",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#FAFAFA", size=12),
        margin=dict(l=40, r=40, t=50, b=40), height=400,
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Mentions"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Sentiment analysis ──
    st.markdown(section_header("Analyse de Sentiment par Marque"), unsafe_allow_html=True)

    brands_sorted = sorted(COMPETITORS, key=lambda b: sentiment.get(b, {}).get("Positif", 0), reverse=True)
    series = {
        "Positif": [sentiment[b]["Positif"] for b in brands_sorted],
        "Neutre": [sentiment[b]["Neutre"] for b in brands_sorted],
        "Négatif": [sentiment[b]["Négatif"] for b in brands_sorted],
    }
    fig = stacked_bar(brands_sorted, series, "Répartition du Sentiment (%)", height=420)
    st.plotly_chart(fig, use_container_width=True)

    # ── Insight ──
    best_sentiment = brands_sorted[0]
    worst_sentiment = brands_sorted[-1]
    st.markdown(insight_box(
        f"<strong>{best_sentiment}</strong> affiche le meilleur sentiment positif "
        f"({sentiment[best_sentiment]['Positif']}%). "
        f"<strong>{worst_sentiment}</strong> concentre le plus de négativité "
        f"({sentiment[worst_sentiment]['Négatif']}%). "
        f"Les irritants principaux du marché : délais de retrait, bugs applicatifs et service client."
    ), unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Share of Voice donut ──
    col_left, col_right = st.columns(2)

    with col_left:
        fig = donut_chart(sov, "Share of Voice — Mars 2026", colors=COLORS_SEQ[:len(sov)], height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        # Total mentions bar
        mentions_sorted = dict(sorted(total_mentions.items(), key=lambda x: x[1], reverse=True))
        colors = [BETCLIC_RED if b == "Betclic" else "#4A5568" for b in mentions_sorted.keys()]
        fig = go.Figure(go.Bar(
            y=list(mentions_sorted.keys()),
            x=list(mentions_sorted.values()),
            orientation="h",
            marker_color=colors,
            text=list(mentions_sorted.values()),
            textposition="outside",
            textfont=dict(size=12, color="#FAFAFA"),
        ))
        fig.update_layout(
            title="Total Mentions (4 semaines)",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color="#FAFAFA", size=12),
            margin=dict(l=40, r=40, t=50, b=40), height=400,
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
