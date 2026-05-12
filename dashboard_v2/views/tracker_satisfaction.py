"""Brand Health Tracker — Satisfaction & Fidélité."""

import streamlit as st
from data.loader import (
    apply_filters, calc_satisfaction, calc_nps, calc_churn_risk,
    calc_irritants, calc_intention, calc_intention_positive,
    calc_kpi_by_vague, calc_delta, get_latest_vague, get_previous_vague,
    get_utilisateurs_betclic
)
from components.styles import kpi_card, section_header, insight_box, styled_divider
from components.charts import (
    nps_gauge, line_chart_evolution, donut_chart, bar_chart_brands,
    BETCLIC_RED, OPINIONWAY_PURPLE, COLORS_SEQ
)
import plotly.graph_objects as go


def render():
    data = st.session_state["data"]
    vagues = st.session_state["selected_vagues"]
    villes = st.session_state["selected_villes"]
    genres = st.session_state["selected_genres"]
    segments = st.session_state["selected_segments"]

    df = apply_filters(data, vagues, villes or None, genres or None, segments or None)

    st.markdown(section_header(
        "Satisfaction & Fidélité",
        "NPS, satisfaction globale, risque de churn, irritants et intention de réutilisation"
    ), unsafe_allow_html=True)

    # ── KPI calculations ──
    sat_v = calc_kpi_by_vague(df, calc_satisfaction)

    def _nps_score(sub):
        return calc_nps(sub)["nps"]
    def _nps_promoteurs(sub):
        return calc_nps(sub)["promoteurs"]
    def _nps_detracteurs(sub):
        return calc_nps(sub)["detracteurs"]
    def _churn_eleve(sub):
        cr = calc_churn_risk(sub)
        return cr.get("Élevé", 0)

    nps_v = calc_kpi_by_vague(df, _nps_score)
    prom_v = calc_kpi_by_vague(df, _nps_promoteurs)
    det_v = calc_kpi_by_vague(df, _nps_detracteurs)
    churn_v = calc_kpi_by_vague(df, _churn_eleve)
    intent_v = calc_kpi_by_vague(df, calc_intention_positive)

    # ── KPI Cards ──
    col1, col2, col3, col4, col5 = st.columns(5)

    for col, label, vdata, suffix in [
        (col1, "Satisfaction", sat_v, "/5"),
        (col2, "NPS", nps_v, " pts"),
        (col3, "Promoteurs", prom_v, "%"),
        (col4, "Détracteurs", det_v, "%"),
        (col5, "Churn Élevé", churn_v, "%"),
    ]:
        latest = get_latest_vague(vdata)
        prev = get_previous_vague(vdata)
        d, direction = calc_delta(latest, prev)
        # For detractors and churn, lower is better
        if label in ["Détracteurs", "Churn Élevé"] and direction == "down":
            direction = "up"
        elif label in ["Détracteurs", "Churn Élevé"] and direction == "up":
            direction = "down"
        with col:
            st.markdown(kpi_card(label, f"{latest}{suffix}", f"{d} pt" if d else None, direction), unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── NPS Gauge + Evolution ──
    col_left, col_right = st.columns(2)

    with col_left:
        latest_nps = get_latest_vague(nps_v)
        fig = nps_gauge(latest_nps if latest_nps else 0, height=300)
        st.plotly_chart(fig, width='stretch')

        # NPS breakdown
        latest_vague = [v for v in ["Vague 3", "Vague 2", "Vague 1"] if v in vagues]
        if latest_vague:
            df_latest = df[df["Vague"] == latest_vague[0]]
            nps_data = calc_nps(df_latest)
            nps_breakdown = {
                "Promoteurs (9-10)": nps_data["promoteurs"],
                "Passifs (7-8)": nps_data["passifs"],
                "Détracteurs (0-6)": nps_data["detracteurs"],
            }
            fig = donut_chart(nps_breakdown, "Répartition NPS", colors=["#27AE60", "#F39C12", "#E74C3C"], height=300)
            st.plotly_chart(fig, width='stretch')

    with col_right:
        # NPS + Satisfaction evolution
        nps_evol = {v: nps_v[v] for v in ["Vague 1", "Vague 2", "Vague 3"] if nps_v.get(v) is not None}
        fig = line_chart_evolution(nps_evol, "Évolution NPS", suffix=" pts", height=300)
        st.plotly_chart(fig, width='stretch')

        sat_evol = {v: sat_v[v] for v in ["Vague 1", "Vague 2", "Vague 3"] if sat_v.get(v) is not None}
        fig = line_chart_evolution(sat_evol, "Évolution Satisfaction", suffix="/5", height=300)
        st.plotly_chart(fig, width='stretch')

    # Insight
    latest_sat = get_latest_vague(sat_v)
    delta_nps, _ = calc_delta(get_latest_vague(nps_v), nps_v.get("Vague 1"))
    st.markdown(insight_box(
        f"Satisfaction stable à <strong>{latest_sat}/5</strong>. Le NPS progresse de <strong>{delta_nps} pts</strong> "
        f"depuis V1, porté par la hausse des promoteurs et la baisse des détracteurs. "
        f"La base clients Betclic est de plus en plus engagée et recommandatrice."
    ), unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Churn Risk + Irritants ──
    st.markdown(section_header("Risque de Churn & Irritants"), unsafe_allow_html=True)

    col_left, col_right = st.columns(2)

    with col_left:
        if latest_vague:
            churn = calc_churn_risk(df[df["Vague"] == latest_vague[0]])
            if churn:
                fig = donut_chart(churn, "Répartition Risque de Churn", colors=["#27AE60", "#F39C12", "#E74C3C"], height=350)
                st.plotly_chart(fig, width='stretch')

        # Churn evolution
        churn_evol = {v: churn_v[v] for v in ["Vague 1", "Vague 2", "Vague 3"] if churn_v.get(v) is not None}
        fig = line_chart_evolution(churn_evol, "Évolution Churn Élevé (%)", height=300)
        st.plotly_chart(fig, width='stretch')

    with col_right:
        if latest_vague:
            irritants = calc_irritants(df[df["Vague"] == latest_vague[0]])
            if irritants:
                fig = bar_chart_brands(irritants, "Principaux Irritants", highlight="", height=380)
                st.plotly_chart(fig, width='stretch')

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Intention de réutilisation ──
    st.markdown(section_header("Intention de Réutilisation"), unsafe_allow_html=True)

    col_left, col_right = st.columns(2)

    with col_left:
        if latest_vague:
            intention = calc_intention(df[df["Vague"] == latest_vague[0]])
            if intention:
                colors_int = ["#27AE60", "#2980B9", "#F39C12", "#E74C3C"]
                fig = donut_chart(intention, "Intention de réutilisation Betclic", colors=colors_int[:len(intention)], height=350)
                st.plotly_chart(fig, width='stretch')

    with col_right:
        intent_evol = {v: intent_v[v] for v in ["Vague 1", "Vague 2", "Vague 3"] if intent_v.get(v) is not None}
        fig = line_chart_evolution(intent_evol, "Évolution Intention Positive (Certainement + Probablement)", height=350)
        st.plotly_chart(fig, width='stretch')
