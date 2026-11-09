"""Brand Health Tracker · Executive Scorecard & Overview."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.loader import (
    sort_vagues, get_main_competitors, keep_brands,
    apply_filters, calc_tom, calc_notoriete_totale, calc_notoriete_aidee,
    calc_penetration, calc_satisfaction, calc_nps, calc_preference,
    calc_consideration, calc_rappel_campagne,
    calc_pdm_volume, calc_pdm_volume_all_brands,
    calc_kpi_by_vague, calc_delta, get_latest_vague, get_previous_vague,
    calc_funnel, calc_marque_principale,
    calc_tom_all_brands, calc_notoriete_all_brands,
    calc_penetration_all_brands, calc_marque_principale_all,
    VAGUE_SHORT, MAIN_COMPETITORS
)
from components.styles import kpi_card, section_header, insight_box, styled_divider
from components.narrative import trend_word, signed, prev_wave_label, leader_of
from components.charts import (
    line_chart_evolution, funnel_chart, multi_line_chart,
    BETCLIC_RED, OPINIONWAY_PURPLE, COLORS_SEQ, brand_color,
)


def render():
    data = st.session_state["data"]
    vagues = st.session_state["selected_vagues"]
    villes = st.session_state["selected_villes"]
    genres = st.session_state["selected_genres"]
    segments = st.session_state["selected_segments"]
    ages = st.session_state.get("selected_ages", [])

    df = apply_filters(data, vagues, villes or None, genres or None, segments or None, ages=ages or None)
    _waves = sort_vagues(df["Vague"].dropna().unique().tolist())
    main_brands = get_main_competitors(df)  # Betclic + 4 concurrents, selon les données

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
    col1, col2, col3, col4 = st.columns(4)
    _render_kpi(col1, "Considération", consid_v)
    _render_kpi(col2, "Marque Principale", pref_v)
    _render_kpi(col3, "PDM Volume", pdm_v)
    _render_kpi(col4, "Rappel Pub", rappel_v)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Insights automatiques ──
    latest_tom = get_latest_vague(tom_v)
    latest_pen = get_latest_vague(pen_v)
    latest_nps = get_latest_vague(nps_v)
    latest_pdm = get_latest_vague(pdm_v)
    d_tom, _ = calc_delta(latest_tom, get_previous_vague(tom_v))
    d_pen, _ = calc_delta(latest_pen, get_previous_vague(pen_v))
    d_nps, _ = calc_delta(latest_nps, get_previous_vague(nps_v))
    prev_lbl = prev_wave_label(tom_v)
    vs_prev = f" vs {prev_lbl}" if prev_lbl else ""

    # Positionnement TOM / PDM vs le premier concurrent (vague la plus récente)
    _lv = sort_vagues([k for k, v in tom_v.items() if v is not None])
    _df_lv = df[df["Vague"] == _lv[-1]] if _lv else df
    tom_lead, tom_lead_v = leader_of(calc_tom_all_brands(_df_lv), exclude="Betclic")
    pdm_lead, pdm_lead_v = leader_of(calc_pdm_volume_all_brands(_df_lv), exclude="Betclic")

    if tom_lead and latest_tom is not None and tom_lead_v > latest_tom:
        tom_txt = (f"Betclic est cité en premier par <strong>{latest_tom}%</strong> des répondants "
                   f"({signed(d_tom)}{vs_prev}), derrière <strong>{tom_lead}</strong> ({tom_lead_v}%).")
    else:
        tom_txt = (f"Betclic est la marque la plus citée en premier avec <strong>{latest_tom}%</strong> "
                   f"de Top of Mind ({signed(d_tom)}{vs_prev}).")
    if pdm_lead and latest_pdm is not None and pdm_lead_v > latest_pdm:
        pdm_txt = (f" En PDM Volume, <strong>{pdm_lead}</strong> passe devant ({pdm_lead_v}% vs "
                   f"{latest_pdm}% pour Betclic).")
    else:
        pdm_txt = f" Betclic reste leader en PDM Volume (<strong>{latest_pdm}%</strong>)."

    st.markdown(insight_box(
        f"{tom_txt} La pénétration {trend_word(d_pen)} à <strong>{latest_pen}%</strong> "
        f"({signed(d_pen)}{vs_prev}).{pdm_txt} Le NPS {trend_word(d_nps)} à "
        f"<strong>{latest_nps} pts</strong> ({signed(d_nps, 'pts')}{vs_prev})."
    ), unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Comparatif concurrentiel ──
    st.markdown(section_header(
        "Scorecard Concurrentiel",
        "Comparaison Betclic vs principaux concurrents du marché ivoirien"
    ), unsafe_allow_html=True)

    latest_vague_name = [v for v in _waves[::-1] if v in vagues]
    df_latest = df[df["Vague"] == latest_vague_name[0]] if latest_vague_name else df

    tom_all = calc_tom_all_brands(df_latest)
    not_all = calc_notoriete_all_brands(df_latest)
    pen_all = calc_penetration_all_brands(df_latest)
    mp_all = calc_marque_principale_all(df_latest)

    # Helper : bar chart simple par marque, trié décroissant, couleurs charte client
    def _brand_bar(data: dict, title: str, height: int = 330):
        sorted_brands = sorted(main_brands, key=lambda b: -data.get(b, 0))
        vals = [data.get(b, 0) for b in sorted_brands]
        fig = go.Figure(go.Bar(
            x=sorted_brands,
            y=vals,
            text=[f"{v:.1f}%" for v in vals],
            textposition="outside",
            textfont=dict(size=12),
            marker_color=[brand_color(b) for b in sorted_brands],
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="#1A1D23", size=12),
            margin=dict(l=40, r=40, t=50, b=40),
            height=height,
            title=dict(text=title, font=dict(size=14)),
            yaxis=dict(range=[0, max(vals) * 1.22 if vals else 100], gridcolor="rgba(0,0,0,0.06)", title="%"),
            showlegend=False,
        )
        return fig

    # 4 charts séparés (un par KPI), disposés sur 2 lignes de 2 colonnes
    row1_l, row1_r = st.columns(2)
    with row1_l:
        st.plotly_chart(_brand_bar(tom_all, "Top of Mind (Q1A)"), width='stretch')
    with row1_r:
        st.plotly_chart(_brand_bar(not_all, "Notoriété Totale (Q1A+Q1B+Q1C)"), width='stretch')

    row2_l, row2_r = st.columns(2)
    with row2_l:
        st.plotly_chart(_brand_bar(pen_all, "Pénétration (Q5)"), width='stretch')
    with row2_r:
        st.plotly_chart(_brand_bar(mp_all, "Marque Principale (Q6)"), width='stretch')

    # Comparative table for precise reading
    table_rows = []
    for b in sorted(main_brands, key=lambda b: -tom_all.get(b, 0)):
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
            "TOM": {v: tom_v.get(v, 0) for v in _waves if tom_v.get(v) is not None},
            "Pénétration": {v: pen_v.get(v, 0) for v in _waves if pen_v.get(v) is not None},
            "Considération": {v: consid_v.get(v, 0) for v in _waves if consid_v.get(v) is not None},
            "Préférence": {v: pref_v.get(v, 0) for v in _waves if pref_v.get(v) is not None},
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
        nps_evol = {v: nps_v[v] for v in _waves if nps_v.get(v) is not None}
        fig = line_chart_evolution(nps_evol, "Évolution NPS", suffix=" pts", height=320)
        st.plotly_chart(fig, width='stretch')

    with col_right:
        sat_evol = {v: sat_v[v] for v in _waves if sat_v.get(v) is not None}
        fig = line_chart_evolution(sat_evol, "Évolution Satisfaction /5", suffix="/5", height=320)
        st.plotly_chart(fig, width='stretch')
