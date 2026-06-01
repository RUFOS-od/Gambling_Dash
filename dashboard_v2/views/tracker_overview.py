"""Brand Health Tracker · Executive Scorecard & Overview."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.loader import (
    apply_filters, calc_tom, calc_notoriete_totale, calc_notoriete_aidee,
    calc_penetration, calc_satisfaction, calc_nps, calc_preference,
    calc_consideration, calc_wallet_share, calc_rappel_campagne,
    calc_pdm_volume, calc_pdm_volume_all_brands,
    calc_kpi_by_vague, calc_delta, get_latest_vague, get_previous_vague,
    calc_funnel, calc_marque_principale,
    calc_tom_all_brands, calc_notoriete_all_brands,
    calc_penetration_all_brands, calc_marque_principale_all,
    VAGUE_SHORT, MAIN_COMPETITORS
)
from components.styles import kpi_card, section_header, insight_box, styled_divider
from components.charts import (
    line_chart_evolution, funnel_chart, multi_line_chart,
    BETCLIC_RED, OPINIONWAY_PURPLE, COLORS_SEQ,
)


def render():
    data = st.session_state["data"]
    vagues = st.session_state["selected_vagues"]
    villes = st.session_state["selected_villes"]
    genres = st.session_state["selected_genres"]
    segments = st.session_state["selected_segments"]

    df = apply_filters(data, vagues, villes or None, genres or None, segments or None)

    st.markdown(section_header(
        "Scorecard Exécutif · Betclic Brand Pulse",
        "Vue synthétique des indicateurs clés de santé de marque | Évolution inter-vagues"
    ), unsafe_allow_html=True)

    # ── KPI calculations by vague ──
    tom_v = calc_kpi_by_vague(df, calc_tom)
    not_v = calc_kpi_by_vague(df, calc_notoriete_totale)
    pen_v = calc_kpi_by_vague(df, calc_penetration)
    sat_v = calc_kpi_by_vague(df, calc_satisfaction)
    pref_v = calc_kpi_by_vague(df, calc_preference)
    consid_v = calc_kpi_by_vague(df, calc_consideration)
    wallet_v = calc_kpi_by_vague(df, calc_wallet_share)
    rappel_v = calc_kpi_by_vague(df, calc_rappel_campagne)
    pdm_v = calc_kpi_by_vague(df, calc_pdm_volume)

    def _nps_extract(sub):
        return calc_nps(sub)["nps"]
    nps_v = calc_kpi_by_vague(df, _nps_extract)

    # ── Row 1: Main KPIs ──
    col1, col2, col3, col4, col5 = st.columns(5)

    def _fmt(value, suffix, currency=False):
        if currency:
            # Thousand separator with non-breaking space, no decimals
            return f"{int(round(float(value))):,}".replace(",", " ") + suffix
        return f"{value}{suffix}"

    def _render_kpi(col, label, vague_data, suffix="%", currency=False):
        latest = get_latest_vague(vague_data)
        prev = get_previous_vague(vague_data)
        delta_str, delta_dir = calc_delta(latest, prev)
        if delta_str:
            if currency:
                # Strip "+/-" prefix and reformat as currency delta
                try:
                    raw = float(str(delta_str).replace(",", ".").replace("+", "").strip())
                    sign = "+" if raw >= 0 else "−"
                    delta_str = f"{sign}{int(round(abs(raw))):,}".replace(",", " ") + " F CFA"
                except Exception:
                    delta_str = f"{delta_str} F CFA"
            else:
                delta_str = f"{delta_str} pt"
        with col:
            st.markdown(kpi_card(label, _fmt(latest, suffix, currency), delta_str, delta_dir), unsafe_allow_html=True)

    _render_kpi(col1, "Top-of-Mind", tom_v)
    _render_kpi(col2, "Notoriété Totale", not_v)
    _render_kpi(col3, "Pénétration", pen_v)
    _render_kpi(col4, "NPS", nps_v, suffix=" pts")
    _render_kpi(col5, "Satisfaction", sat_v, suffix="/5")

    st.markdown("", unsafe_allow_html=True)

    # ── Row 2: Secondary KPIs ──
    col1, col2, col3, col4, col5 = st.columns(5)
    _render_kpi(col1, "Considération", consid_v)
    _render_kpi(col2, "Préférence (PDM Vol.)", pref_v)
    _render_kpi(col3, "PDM Volume", pdm_v)
    _render_kpi(col4, "Wallet Share", wallet_v, suffix=" F CFA", currency=True)
    _render_kpi(col5, "Rappel Pub", rappel_v)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Insights automatiques ──
    latest_tom = get_latest_vague(tom_v)
    latest_pen = get_latest_vague(pen_v)
    latest_nps = get_latest_vague(nps_v)
    delta_tom, dir_tom = calc_delta(get_latest_vague(tom_v), tom_v.get("Vague 1"))
    delta_pen, _ = calc_delta(get_latest_vague(pen_v), pen_v.get("Vague 1"))

    st.markdown(insight_box(
        f"<strong>Betclic confirme son leadership</strong> avec un TOM de <strong>{latest_tom}%</strong> "
        f"({delta_tom} pt depuis V1). La pénétration parieurs atteint <strong>{latest_pen}%</strong> "
        f"({delta_pen} pt vs V1), portée par la hausse de la considération et du rappel campagne. "
        f"Le NPS à <strong>{latest_nps} pts</strong> signale une base clients engagée et promotrice."
    ), unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Comparatif concurrentiel ──
    st.markdown(section_header(
        "Scorecard Concurrentiel",
        "Comparaison Betclic vs principaux concurrents du marché ivoirien"
    ), unsafe_allow_html=True)

    latest_vague_name = [v for v in ["Vague 3", "Vague 2", "Vague 1"] if v in vagues]
    df_latest = df[df["Vague"] == latest_vague_name[0]] if latest_vague_name else df

    tom_all = calc_tom_all_brands(df_latest)
    not_all = calc_notoriete_all_brands(df_latest)
    pen_all = calc_penetration_all_brands(df_latest)
    mp_all = calc_marque_principale_all(df_latest)

    # Build the comparative bar chart : 4 KPIs grouped per brand
    kpi_groups = {
        "TOM": tom_all,
        "Notoriété Totale": not_all,
        "Pénétration": pen_all,
        "Marque Principale": mp_all,
    }
    brand_colors = {
        "Betclic": BETCLIC_RED,
        "1XBET": "#2980B9",
        "Sportcash": "#27AE60",
        "Melbet": "#F39C12",
        "BetMomo": "#8E44AD",
    }
    fig = go.Figure()
    for kpi_name, kpi_values in kpi_groups.items():
        vals = [kpi_values.get(b, 0) for b in MAIN_COMPETITORS]
        fig.add_trace(go.Bar(
            name=kpi_name,
            x=MAIN_COMPETITORS,
            y=vals,
            text=[f"{v:.1f}%" for v in vals],
            textposition="outside",
            textfont=dict(size=11),
        ))
    fig.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#1A1D23", size=12),
        margin=dict(l=40, r=40, t=50, b=60),
        height=440,
        title=dict(text="KPIs clés par marque", font=dict(size=15)),
        yaxis=dict(range=[0, 105], gridcolor="rgba(0,0,0,0.06)", title="%"),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.18),
    )
    st.plotly_chart(fig, width='stretch')

    # Comparative table for precise reading
    table_rows = []
    for b in MAIN_COMPETITORS:
        table_rows.append({
            "Marque": b,
            "TOM (%)": tom_all.get(b, 0),
            "Notoriété Totale (%)": not_all.get(b, 0),
            "Pénétration (%)": pen_all.get(b, 0),
            "Marque Principale (%)": mp_all.get(b, 0),
        })
    df_table = pd.DataFrame(table_rows).set_index("Marque")
    st.dataframe(df_table, width='stretch', height=240)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Charts ──
    col_left, col_right = st.columns(2)

    with col_left:
        # Evolution chart
        kpi_evol = {
            "TOM": {v: tom_v.get(v, 0) for v in ["Vague 1", "Vague 2", "Vague 3"] if tom_v.get(v) is not None},
            "Pénétration": {v: pen_v.get(v, 0) for v in ["Vague 1", "Vague 2", "Vague 3"] if pen_v.get(v) is not None},
            "Considération": {v: consid_v.get(v, 0) for v in ["Vague 1", "Vague 2", "Vague 3"] if consid_v.get(v) is not None},
            "Préférence": {v: pref_v.get(v, 0) for v in ["Vague 1", "Vague 2", "Vague 3"] if pref_v.get(v) is not None},
        }
        fig = multi_line_chart(kpi_evol, "Évolution des KPIs clés Betclic", height=420)
        st.plotly_chart(fig, width='stretch')

    with col_right:
        # Funnel chart - latest vague (df_latest already computed above)
        funnel_data = calc_funnel(df_latest)
        vague_label = VAGUE_SHORT.get(latest_vague_name[0], '') if latest_vague_name else ''
        fig = funnel_chart(funnel_data, f"Funnel de Conversion Betclic ({vague_label})", height=420)
        st.plotly_chart(fig, width='stretch')

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Évolution NPS + Satisfaction ──
    col_left, col_right = st.columns(2)
    with col_left:
        nps_evol = {v: nps_v[v] for v in ["Vague 1", "Vague 2", "Vague 3"] if nps_v.get(v) is not None}
        fig = line_chart_evolution(nps_evol, "Évolution NPS", suffix=" pts", height=320)
        st.plotly_chart(fig, width='stretch')

    with col_right:
        sat_evol = {v: sat_v[v] for v in ["Vague 1", "Vague 2", "Vague 3"] if sat_v.get(v) is not None}
        fig = line_chart_evolution(sat_evol, "Évolution Satisfaction /5", suffix="/5", height=320)
        st.plotly_chart(fig, width='stretch')
