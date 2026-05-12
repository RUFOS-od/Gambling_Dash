"""AI Market Radar — Fiches Concurrents."""

import streamlit as st
from data.simulator import (
    generate_share_of_voice, generate_sentiment_data, generate_ad_intensity,
    generate_risk_levels, generate_social_mentions, generate_competitor_actions,
    COMPETITORS
)
from data.loader import calc_tom_all_brands, calc_notoriete_all_brands, load_raw_data
from components.styles import kpi_card, section_header, insight_box, styled_divider, alert_box
from components.charts import donut_chart, line_chart_evolution, BETCLIC_RED, OPINIONWAY_PURPLE
import plotly.graph_objects as go


def render():
    st.markdown(section_header(
        "Fiches Concurrents",
        "Profil détaillé de chaque acteur du marché"
    ), unsafe_allow_html=True)

    # Load real + simulated data
    data = load_raw_data()
    latest = data[data["Vague"] == "Vague 3"]
    tom_all = calc_tom_all_brands(latest)
    not_all = calc_notoriete_all_brands(latest)

    sov = generate_share_of_voice()
    sentiment = generate_sentiment_data()
    ad_intensity = generate_ad_intensity()
    risks = generate_risk_levels()
    mentions = generate_social_mentions()
    actions = generate_competitor_actions()

    # Competitor selector
    competitors_no_betclic = [b for b in COMPETITORS if b != "Betclic"]
    selected = st.selectbox("Sélectionner un concurrent", competitors_no_betclic, index=0)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Competitor card ──
    risk = risks.get(selected, {})
    sent = sentiment.get(selected, {})

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(kpi_card("TOM", f"{tom_all.get(selected, 0)}%"), unsafe_allow_html=True)
    with col2:
        st.markdown(kpi_card("Notoriété", f"{not_all.get(selected, 0)}%"), unsafe_allow_html=True)
    with col3:
        st.markdown(kpi_card("Share of Voice", f"{sov.get(selected, 0)}%"), unsafe_allow_html=True)
    with col4:
        st.markdown(kpi_card("Intensité Pub", f"{ad_intensity.get(selected, 0)}/100"), unsafe_allow_html=True)
    with col5:
        level = risk.get("level", "—")
        color_map = {"Élevé": "down", "Modéré": "neutral", "Faible": "up"}
        st.markdown(kpi_card("Niveau Risque", level, risk.get("trend", ""), color_map.get(level, "neutral")), unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Sentiment + Mentions ──
    col_left, col_right = st.columns(2)

    with col_left:
        fig = donut_chart(
            sent, f"Sentiment — {selected}",
            colors=["#27AE60", "#F39C12", "#E74C3C"], height=350
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        # Weekly mentions
        brand_mentions = mentions.get(selected, {})
        if brand_mentions:
            weeks = list(brand_mentions.keys())
            vals = list(brand_mentions.values())
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=weeks, y=vals,
                marker_color=OPINIONWAY_PURPLE,
                text=vals, textposition="outside",
                textfont=dict(size=13, color="#FAFAFA"),
            ))
            fig.update_layout(
                title=f"Mentions sociales hebdomadaires — {selected}",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter", color="#FAFAFA", size=12),
                margin=dict(l=40, r=40, t=50, b=40), height=350,
                yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Recent Actions ──
    st.markdown(section_header(f"Actions récentes — {selected}"), unsafe_allow_html=True)

    brand_actions = actions.get(selected, [])
    if brand_actions:
        for action in brand_actions:
            impact_color = {"Fort": "alert-box", "Moyen": "alert-box warning", "Faible": "alert-box success"}
            css_class = impact_color.get(action["impact"], "alert-box")
            st.markdown(f"""
            <div class="{css_class}">
                <strong>{action['date']}</strong> | {action['type']} | Impact: {action['impact']}<br/>
                {action['detail']}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Aucune action significative détectée récemment.")

    # ── Comparative vs Betclic ──
    st.markdown(styled_divider(), unsafe_allow_html=True)
    st.markdown(section_header(f"Comparaison {selected} vs Betclic"), unsafe_allow_html=True)

    sent_betclic = sentiment.get("Betclic", {})

    metrics = {
        "Top-of-Mind": (tom_all.get(selected, 0), tom_all.get("Betclic", 0)),
        "Notoriété Totale": (not_all.get(selected, 0), not_all.get("Betclic", 0)),
        "Share of Voice": (sov.get(selected, 0), sov.get("Betclic", 0)),
        "Sentiment Positif": (sent.get("Positif", 0), sent_betclic.get("Positif", 0)),
        "Intensité Pub": (ad_intensity.get(selected, 0), ad_intensity.get("Betclic", 0)),
    }

    fig = go.Figure()
    cats = list(metrics.keys())
    vals_comp = [m[0] for m in metrics.values()]
    vals_betclic = [m[1] for m in metrics.values()]

    fig.add_trace(go.Bar(name=selected, x=cats, y=vals_comp, marker_color=OPINIONWAY_PURPLE, text=vals_comp, textposition="outside"))
    fig.add_trace(go.Bar(name="Betclic", x=cats, y=vals_betclic, marker_color=BETCLIC_RED, text=vals_betclic, textposition="outside"))
    fig.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#FAFAFA", size=12),
        margin=dict(l=40, r=40, t=50, b=40), height=400,
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, use_container_width=True)
