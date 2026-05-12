"""Brand Health Tracker — Notoriété & Visibilité."""

import streamlit as st
from data.loader import (
    apply_filters, calc_tom, calc_tom_all_brands, calc_notoriete_totale,
    calc_notoriete_all_brands, calc_notoriete_aidee, calc_rappel_campagne,
    calc_ambassadeur_distribution, calc_canal_decouverte,
    calc_kpi_by_vague, calc_delta, get_latest_vague, get_previous_vague,
    COMPETITORS
)
from components.styles import kpi_card, section_header, insight_box, styled_divider
from components.charts import (
    bar_chart_brands, grouped_bar_vagues, line_chart_evolution,
    donut_chart, BETCLIC_RED, OPINIONWAY_PURPLE
)


def render():
    data = st.session_state["data"]
    vagues = st.session_state["selected_vagues"]
    villes = st.session_state["selected_villes"]
    genres = st.session_state["selected_genres"]
    segments = st.session_state["selected_segments"]

    df = apply_filters(data, vagues, villes or None, genres or None, segments or None)

    st.markdown(section_header(
        "Notoriété & Visibilité",
        "Top-of-Mind, notoriété totale, rappel campagne et ambassadeurs"
    ), unsafe_allow_html=True)

    # ── KPI Cards ──
    tom_v = calc_kpi_by_vague(df, calc_tom)
    not_v = calc_kpi_by_vague(df, calc_notoriete_totale)
    aided_v = calc_kpi_by_vague(df, calc_notoriete_aidee)
    rappel_v = calc_kpi_by_vague(df, calc_rappel_campagne)

    col1, col2, col3, col4 = st.columns(4)

    for col, label, vdata in [
        (col1, "Top-of-Mind Betclic", tom_v),
        (col2, "Notoriété Totale", not_v),
        (col3, "Notoriété Aidée", aided_v),
        (col4, "Rappel Campagne", rappel_v),
    ]:
        latest = get_latest_vague(vdata)
        prev = get_previous_vague(vdata)
        d, direction = calc_delta(latest, prev)
        with col:
            st.markdown(kpi_card(label, f"{latest}%", f"{d} pt" if d else None, direction), unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── TOM Ranking ──
    col_left, col_right = st.columns(2)

    with col_left:
        latest_vague = [v for v in ["Vague 3", "Vague 2", "Vague 1"] if v in vagues]
        if latest_vague:
            df_latest = df[df["Vague"] == latest_vague[0]]
        else:
            df_latest = df
        tom_all = calc_tom_all_brands(df_latest)
        fig = bar_chart_brands(tom_all, f"Top-of-Mind par marque ({latest_vague[0] if latest_vague else 'Total'})", height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        # TOM evolution for top 3 brands
        tom_betclic = calc_kpi_by_vague(df, calc_tom, brand="Betclic")
        tom_1xbet = calc_kpi_by_vague(df, calc_tom, brand="1XBET")
        tom_sport = calc_kpi_by_vague(df, calc_tom, brand="Sportcash")

        data_evol = {
            "Betclic": tom_betclic,
            "1XBET": tom_1xbet,
            "Sportcash": tom_sport,
        }
        from components.charts import multi_line_chart
        fig = multi_line_chart(data_evol, "Évolution TOM — Top 3 marques")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Notoriété Totale comparison ──
    col_left, col_right = st.columns(2)

    with col_left:
        not_all = calc_notoriete_all_brands(df_latest)
        fig = bar_chart_brands(not_all, "Notoriété Totale par marque", height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        # Notoriete evolution by vague for all brands
        not_by_vague = {}
        for v in ["Vague 1", "Vague 2", "Vague 3"]:
            sub = df[df["Vague"] == v]
            if len(sub) > 0:
                not_by_vague[v] = calc_notoriete_all_brands(sub)
        if not_by_vague:
            fig = grouped_bar_vagues(not_by_vague, "Notoriété Totale — Évolution par vague", height=400)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Rappel campagne & ambassadeurs ──
    st.markdown(section_header("Rappel Campagne & Ambassadeurs"), unsafe_allow_html=True)

    col_left, col_right = st.columns(2)

    with col_left:
        rappel_evol = {v: rappel_v[v] for v in ["Vague 1", "Vague 2", "Vague 3"] if rappel_v.get(v) is not None}
        fig = line_chart_evolution(rappel_evol, "Évolution Rappel Campagne Betclic", height=350)
        st.plotly_chart(fig, use_container_width=True)

        latest_rappel = get_latest_vague(rappel_v)
        first_rappel = rappel_v.get("Vague 1")
        d_rappel, _ = calc_delta(latest_rappel, first_rappel)
        st.markdown(insight_box(
            f"Le rappel campagne progresse fortement : <strong>{latest_rappel}%</strong> "
            f"({d_rappel} pt depuis V1). L'investissement média porte ses fruits avec une mémorisation "
            f"croissante des campagnes Betclic."
        ), unsafe_allow_html=True)

    with col_right:
        # Ambassador distribution
        ambass = calc_ambassadeur_distribution(df_latest)
        if ambass:
            colors_amb = [BETCLIC_RED, OPINIONWAY_PURPLE, "#2980B9", "#F39C12", "#27AE60"]
            fig = donut_chart(ambass, "Ambassadeur mémorisé (parmi ceux ayant vu la campagne)", colors=colors_amb[:len(ambass)], height=350)
            st.plotly_chart(fig, use_container_width=True)

    # ── Canal de découverte ──
    st.markdown(styled_divider(), unsafe_allow_html=True)
    canal = calc_canal_decouverte(df_latest)
    if canal:
        fig = bar_chart_brands(canal, "Canal de découverte de Betclic", highlight="", height=350)
        st.plotly_chart(fig, use_container_width=True)
