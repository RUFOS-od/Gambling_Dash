"""Brand Health Tracker — Usage & Pénétration."""

import streamlit as st
from data.loader import (
    apply_filters, calc_penetration, calc_marque_principale, calc_marque_principale_all,
    calc_multi_app, calc_consideration, calc_preference, calc_wallet_share,
    calc_sport_distribution, calc_pari_type_distribution, calc_paiement_distribution,
    calc_kpi_by_vague, calc_delta, get_latest_vague, get_previous_vague,
    calc_funnel, get_parieurs, VAGUE_SHORT
)
from components.styles import kpi_card, section_header, insight_box, styled_divider
from components.charts import (
    bar_chart_brands, line_chart_evolution, donut_chart, funnel_chart,
    multi_line_chart, BETCLIC_RED, OPINIONWAY_PURPLE, COLORS_SEQ
)


def render():
    data = st.session_state["data"]
    vagues = st.session_state["selected_vagues"]
    villes = st.session_state["selected_villes"]
    genres = st.session_state["selected_genres"]
    segments = st.session_state["selected_segments"]

    df = apply_filters(data, vagues, villes or None, genres or None, segments or None)

    st.markdown(section_header(
        "Usage & Pénétration",
        "Funnel de conversion, wallet share, multi-app, paiements et sports"
    ), unsafe_allow_html=True)

    # ── KPI Cards ──
    pen_v = calc_kpi_by_vague(df, calc_penetration)
    mp_v = calc_kpi_by_vague(df, calc_marque_principale)
    multi_v = calc_kpi_by_vague(df, calc_multi_app)
    consid_v = calc_kpi_by_vague(df, calc_consideration)
    pref_v = calc_kpi_by_vague(df, calc_preference)
    wallet_v = calc_kpi_by_vague(df, calc_wallet_share)

    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)

    for col, label, vdata in [
        (col1, "Pénétration", pen_v),
        (col2, "Marque Principale", mp_v),
        (col3, "Multi-App", multi_v),
        (col4, "Considération", consid_v),
        (col5, "Préférence", pref_v),
        (col6, "Wallet Share", wallet_v),
    ]:
        latest = get_latest_vague(vdata)
        prev = get_previous_vague(vdata)
        d, direction = calc_delta(latest, prev)
        with col:
            st.markdown(kpi_card(label, f"{latest}%", f"{d} pt" if d else None, direction), unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Funnel + Evolution ──
    col_left, col_right = st.columns(2)

    with col_left:
        latest_vague = [v for v in ["Vague 3", "Vague 2", "Vague 1"] if v in vagues]
        lv = latest_vague[0] if latest_vague else "Vague 3"
        df_latest = df[df["Vague"] == lv]
        funnel_data = calc_funnel(df_latest)
        fig = funnel_chart(funnel_data, f"Funnel Betclic ({VAGUE_SHORT.get(lv, lv)})", height=420)
        st.plotly_chart(fig, width='stretch')

    with col_right:
        kpi_evol = {
            "Pénétration": {v: pen_v.get(v, 0) for v in ["Vague 1", "Vague 2", "Vague 3"] if pen_v.get(v) is not None},
            "Considération": {v: consid_v.get(v, 0) for v in ["Vague 1", "Vague 2", "Vague 3"] if consid_v.get(v) is not None},
            "Préférence": {v: pref_v.get(v, 0) for v in ["Vague 1", "Vague 2", "Vague 3"] if pref_v.get(v) is not None},
        }
        fig = multi_line_chart(kpi_evol, "Évolution Funnel Betclic", height=420)
        st.plotly_chart(fig, width='stretch')

    # Insight
    latest_pen = get_latest_vague(pen_v)
    delta_pen, _ = calc_delta(latest_pen, pen_v.get("Vague 1"))
    latest_consid = get_latest_vague(consid_v)
    st.markdown(insight_box(
        f"La pénétration Betclic s'accélère à <strong>{latest_pen}%</strong> des parieurs "
        f"({delta_pen} pt depuis V1). La considération atteint <strong>{latest_consid}%</strong>, "
        f"signe que le recrutement de nouveaux utilisateurs reste dynamique."
    ), unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Marque principale ──
    col_left, col_right = st.columns(2)
    with col_left:
        mp_all = calc_marque_principale_all(df_latest)
        fig = bar_chart_brands(mp_all, "Marque Principale des parieurs", height=380)
        st.plotly_chart(fig, width='stretch')

    with col_right:
        wallet_evol = {v: wallet_v[v] for v in ["Vague 1", "Vague 2", "Vague 3"] if wallet_v.get(v) is not None}
        fig = line_chart_evolution(wallet_evol, "Évolution Wallet Share Betclic", height=380)
        st.plotly_chart(fig, width='stretch')

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Sports, Paris, Paiements ──
    st.markdown(section_header("Profil des Parieurs", "Sports, types de paris et moyens de paiement"), unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        sports = calc_sport_distribution(df_latest)
        if sports:
            fig = donut_chart(sports, "Sport préféré", colors=COLORS_SEQ[:len(sports)], height=350)
            st.plotly_chart(fig, width='stretch')

    with col2:
        types = calc_pari_type_distribution(df_latest)
        if types:
            fig = donut_chart(types, "Type de pari préféré", colors=COLORS_SEQ[:len(types)], height=350)
            st.plotly_chart(fig, width='stretch')

    with col3:
        paiements = calc_paiement_distribution(df_latest)
        if paiements:
            fig = donut_chart(paiements, "Moyen de paiement", colors=COLORS_SEQ[:len(paiements)], height=350)
            st.plotly_chart(fig, width='stretch')
