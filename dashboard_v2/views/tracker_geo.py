"""Brand Health Tracker — Analyse Géographique."""

import streamlit as st
import plotly.graph_objects as go
from data.loader import (
    apply_filters, calc_tom, calc_notoriete_totale, calc_penetration,
    calc_satisfaction, calc_nps, calc_preference, calc_consideration,
    calc_kpi_by_city, CITIES, VAGUE_SHORT, MAIN_COMPETITORS
)
from components.styles import kpi_card, section_header, insight_box, styled_divider
from components.charts import heatmap_cities, BETCLIC_RED, OPINIONWAY_PURPLE, COLORS_SEQ


def render():
    data = st.session_state["data"]
    vagues = st.session_state["selected_vagues"]
    villes = st.session_state["selected_villes"]
    genres = st.session_state["selected_genres"]
    segments = st.session_state["selected_segments"]

    df = apply_filters(data, vagues, villes or None, genres or None, segments or None)

    st.markdown(section_header(
        "Analyse Géographique",
        "Performances comparées sur les 7 villes stratégiques de Côte d'Ivoire"
    ), unsafe_allow_html=True)

    # Get latest vague data
    latest_vague = [v for v in ["Vague 3", "Vague 2", "Vague 1"] if v in vagues]
    if latest_vague:
        df_latest = df[df["Vague"] == latest_vague[0]]
    else:
        df_latest = df

    vague_label = VAGUE_SHORT.get(latest_vague[0], "") if latest_vague else "Total"

    # ── City KPI heatmaps ──
    kpis_geo = {
        "Top-of-Mind (%)": calc_kpi_by_city(df_latest, calc_tom),
        "Notoriété Totale (%)": calc_kpi_by_city(df_latest, calc_notoriete_totale),
        "Pénétration (%)": calc_kpi_by_city(df_latest, calc_penetration),
        "Considération (%)": calc_kpi_by_city(df_latest, calc_consideration),
        "Préférence (%)": calc_kpi_by_city(df_latest, calc_preference),
    }

    def _sat_city(sub):
        return calc_satisfaction(sub)

    def _nps_city(sub):
        return calc_nps(sub)["nps"]

    kpis_geo["Satisfaction (/5)"] = calc_kpi_by_city(df_latest, _sat_city)
    kpis_geo["NPS (pts)"] = calc_kpi_by_city(df_latest, _nps_city)

    # ── Main bar charts ──
    col_left, col_right = st.columns(2)

    with col_left:
        fig = heatmap_cities(kpis_geo["Top-of-Mind (%)"], f"Top-of-Mind par ville ({vague_label})", height=350)
        st.plotly_chart(fig, width='stretch')

    with col_right:
        fig = heatmap_cities(kpis_geo["Pénétration (%)"], f"Pénétration par ville ({vague_label})", height=350)
        st.plotly_chart(fig, width='stretch')

    st.markdown(styled_divider(), unsafe_allow_html=True)

    col_left, col_right = st.columns(2)

    with col_left:
        fig = heatmap_cities(kpis_geo["Considération (%)"], f"Considération par ville ({vague_label})", height=350)
        st.plotly_chart(fig, width='stretch')

    with col_right:
        fig = heatmap_cities(kpis_geo["Préférence (%)"], f"Préférence par ville ({vague_label})", height=350)
        st.plotly_chart(fig, width='stretch')

    st.markdown(styled_divider(), unsafe_allow_html=True)

    col_left, col_right = st.columns(2)

    with col_left:
        fig = heatmap_cities(kpis_geo["Satisfaction (/5)"], f"Satisfaction par ville ({vague_label})", height=350)
        st.plotly_chart(fig, width='stretch')

    with col_right:
        fig = heatmap_cities(kpis_geo["NPS (pts)"], f"NPS par ville ({vague_label})", height=350)
        st.plotly_chart(fig, width='stretch')

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Comprehensive table ──
    st.markdown(section_header("Tableau Synthétique par Ville"), unsafe_allow_html=True)

    # Build a summary table
    import pandas as pd
    table_data = []
    for city in CITIES:
        row = {"Ville": city}
        for kpi_name, city_data in kpis_geo.items():
            row[kpi_name] = city_data.get(city, "—")
        table_data.append(row)

    df_table = pd.DataFrame(table_data)

    # Style the dataframe
    st.dataframe(
        df_table.set_index("Ville"),
        width='stretch',
        height=320,
    )

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Comparatif concurrentiel par ville ──
    st.markdown(section_header(
        "Comparaison concurrentielle par ville",
        "Pénétration (% a déjà parié sur la marque) — Betclic vs principaux concurrents"
    ), unsafe_allow_html=True)

    import plotly.graph_objects as go
    pen_per_brand_per_city = {}
    for b in MAIN_COMPETITORS:
        per_city = {}
        for city in CITIES:
            sub = df_latest[df_latest["Ville"] == city]
            if len(sub) > 0:
                col = f"A_Deja_Parie_{b}"
                if col in sub.columns:
                    per_city[city] = round(sub[col].sum() / len(sub) * 100, 1)
                else:
                    per_city[city] = 0
        pen_per_brand_per_city[b] = per_city

    fig_geo = go.Figure()
    for i, b in enumerate(MAIN_COMPETITORS):
        vals = [pen_per_brand_per_city[b].get(c, 0) for c in CITIES]
        fig_geo.add_trace(go.Bar(
            name=b,
            x=CITIES,
            y=vals,
            text=[f"{v:.0f}%" for v in vals],
            textposition="outside",
            textfont=dict(size=9),
            marker_color=BETCLIC_RED if b == "Betclic" else COLORS_SEQ[i % len(COLORS_SEQ)],
        ))
    fig_geo.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#1A1D23", size=11),
        margin=dict(l=40, r=40, t=50, b=80),
        height=460,
        title=dict(text=f"Pénétration par ville et par marque ({vague_label})", font=dict(size=15)),
        yaxis=dict(gridcolor="rgba(0,0,0,0.06)", title="%"),
        xaxis=dict(tickangle=-20),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.20),
    )
    st.plotly_chart(fig_geo, width='stretch')

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Insight ──
    # Find best and worst performing cities
    tom_data = kpis_geo["Top-of-Mind (%)"]
    if tom_data:
        best_city = max(tom_data, key=tom_data.get)
        worst_city = min(tom_data, key=tom_data.get)
        pen_data = kpis_geo["Pénétration (%)"]
        best_pen_city = max(pen_data, key=pen_data.get) if pen_data else "N/A"

        st.markdown(insight_box(
            f"<strong>{best_city}</strong> affiche le meilleur TOM ({tom_data[best_city]}%), "
            f"tandis que <strong>{worst_city}</strong> présente le plus faible ({tom_data[worst_city]}%). "
            f"La pénétration est maximale à <strong>{best_pen_city}</strong> "
            f"({pen_data.get(best_pen_city, 0)}%). "
            f"Les villes secondaires montrent un potentiel de croissance significatif pour Betclic."
        ), unsafe_allow_html=True)
