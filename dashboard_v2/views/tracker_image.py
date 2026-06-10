"""Brand Health Tracker · Attributs Fonctionnels."""

import streamlit as st
import pandas as pd
from data.loader import (
    apply_filters, calc_image_scores, calc_image_scores_main_brands,
    calc_kpi_by_vague,
    calc_delta, get_latest_vague, get_previous_vague,
    IMAGE_ATTRIBUTES, MAIN_COMPETITORS
)
from components.styles import kpi_card, section_header, insight_box, styled_divider
from components.charts import radar_chart, bar_chart_brands, multi_line_chart, BETCLIC_RED, OPINIONWAY_PURPLE, COLORS_VAGUES, COLORS_SEQ, brand_color
import plotly.graph_objects as go


def render():
    data = st.session_state["data"]
    vagues = st.session_state["selected_vagues"]
    villes = st.session_state["selected_villes"]
    genres = st.session_state["selected_genres"]
    segments = st.session_state["selected_segments"]
    ages = st.session_state.get("selected_ages", [])

    df = apply_filters(data, vagues, villes or None, genres or None, segments or None, ages=ages or None)

    st.markdown(section_header(
        "Attributs Fonctionnels Betclic",
        "12 attributs fonctionnels mesurés sur une échelle de 1 à 5 | Évolution inter-vagues"
    ), unsafe_allow_html=True)

    # ── Radar chart by vague ──
    image_by_vague = {}
    for v in ["Vague 1", "Vague 2", "Vague 3"]:
        sub = df[df["Vague"] == v]
        if len(sub) > 0:
            image_by_vague[v] = calc_image_scores(sub)

    if image_by_vague:
        fig = radar_chart(image_by_vague, "Profil des Attributs Fonctionnels Betclic · Comparaison inter-vagues", height=520)
        st.plotly_chart(fig, width='stretch')

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Top / Bottom attributes ──
    latest_v = [v for v in ["Vague 3", "Vague 2", "Vague 1"] if v in image_by_vague]
    if latest_v:
        latest_scores = image_by_vague[latest_v[0]]
        sorted_attrs = sorted(latest_scores.items(), key=lambda x: x[1], reverse=True)

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown(section_header("Points Forts", "Top attributs fonctionnels"), unsafe_allow_html=True)
            for attr, score in sorted_attrs[:4]:
                # Get delta vs V1
                v1_score = image_by_vague.get("Vague 1", {}).get(attr, score)
                d, direction = calc_delta(score, v1_score)
                st.markdown(kpi_card(attr, f"{score}/5", f"{d} vs V1" if d else None, direction), unsafe_allow_html=True)
                st.markdown("", unsafe_allow_html=True)

        with col_right:
            st.markdown(section_header("Axes d'Amélioration", "Attributs à renforcer"), unsafe_allow_html=True)
            for attr, score in sorted_attrs[-4:]:
                v1_score = image_by_vague.get("Vague 1", {}).get(attr, score)
                d, direction = calc_delta(score, v1_score)
                st.markdown(kpi_card(attr, f"{score}/5", f"{d} vs V1" if d else None, direction), unsafe_allow_html=True)
                st.markdown("", unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Detailed evolution per attribute ──
    st.markdown(section_header("Évolution détaillée par attribut"), unsafe_allow_html=True)

    # Build evolution data
    evol_data = {}
    for attr_col, attr_label in IMAGE_ATTRIBUTES.items():
        evol_data[attr_label] = {}
        for v in ["Vague 1", "Vague 2", "Vague 3"]:
            scores = image_by_vague.get(v, {})
            if attr_label in scores:
                evol_data[attr_label][v] = scores[attr_label]

    # Show as a grouped bar chart
    if evol_data:
        attrs = list(evol_data.keys())
        fig = go.Figure()
        for v in ["Vague 1", "Vague 2", "Vague 3"]:
            vals = [evol_data[a].get(v, 0) for a in attrs]
            fig.add_trace(go.Bar(
                name=v, x=attrs, y=vals,
                marker_color=COLORS_VAGUES.get(v, "#2C3E50"),
                text=[f"{val:.2f}" for val in vals],
                textposition="outside",
                textfont=dict(size=10),
            ))
        fig.update_layout(
            barmode="group",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="#1A1D23", size=12),
            margin=dict(l=40, r=40, t=50, b=80),
            height=450,
            title=dict(text="Scores par Attribut Fonctionnel · Évolution V1→V3", font=dict(size=16)),
            yaxis=dict(range=[0, 5.2], gridcolor="rgba(0,0,0,0.06)"),
            xaxis=dict(tickangle=-45),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig, width='stretch')

    # ── Insight ──
    if latest_v and "Vague 1" in image_by_vague:
        best = sorted_attrs[0]
        worst = sorted_attrs[-1]
        st.markdown(insight_box(
            f"<strong>{best[0]}</strong> reste le point fort de Betclic ({best[1]}/5). "
            f"<strong>{worst[0]}</strong> ({worst[1]}/5) représente le principal axe d'amélioration. "
            f"Globalement, tous les attributs progressent entre V1 et V3, signe d'un renforcement "
            f"cohérent des attributs fonctionnels."
        ), unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Comparatif concurrentiel ──
    st.markdown(section_header(
        "Attributs Fonctionnels · Comparaison concurrentielle",
        "Scores par attribut pour Betclic vs principaux concurrents (parmi ceux qui connaissent chaque marque)"
    ), unsafe_allow_html=True)

    image_by_brand = calc_image_scores_main_brands(df)
    # Filter to brands that have at least some data
    image_by_brand = {b: scores for b, scores in image_by_brand.items()
                      if any(v > 0 for v in scores.values())}

    if image_by_brand:
        attrs = list(IMAGE_ATTRIBUTES.values())
        # Sort attributes by Betclic score (descending) for readability
        betclic_scores = image_by_brand.get("Betclic", {})
        attrs = sorted(attrs, key=lambda a: -betclic_scores.get(a, 0))

        fig_bar = go.Figure()
        for i, brand in enumerate(image_by_brand.keys()):
            vals = [image_by_brand[brand].get(a, 0) for a in attrs]
            fig_bar.add_trace(go.Bar(
                name=brand,
                x=attrs,
                y=vals,
                marker_color=brand_color(brand),
                text=[f"{v:.2f}" for v in vals],
                textposition="outside",
                textfont=dict(size=9),
            ))
        fig_bar.update_layout(
            barmode="group",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="#1A1D23", size=11),
            margin=dict(l=40, r=40, t=50, b=120),
            height=520,
            title=dict(text="Scores par attribut · Multi-marques (trié par score Betclic)", font=dict(size=15)),
            yaxis=dict(range=[0, 5.5], gridcolor="rgba(0,0,0,0.06)", title="Score moyen / 5"),
            xaxis=dict(tickangle=-40),
            legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.32),
        )
        st.plotly_chart(fig_bar, width='stretch')

        # Compact table for precise reading
        import pandas as pd
        table_rows = []
        for a in attrs:
            row = {"Attribut": a}
            for b in image_by_brand.keys():
                row[b] = image_by_brand[b].get(a, 0)
            table_rows.append(row)
        st.dataframe(pd.DataFrame(table_rows).set_index("Attribut"), width='stretch', height=460)
