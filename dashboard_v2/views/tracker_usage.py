"""Brand Health Tracker — Usage & Pénétration."""

import streamlit as st
from data.loader import (
    apply_filters, calc_penetration, calc_marque_principale, calc_marque_principale_all,
    calc_penetration_all_brands, calc_pdm_valeur_all_brands,
    calc_multi_app, calc_consideration, calc_preference, calc_wallet_share,
    calc_sport_distribution, calc_pari_type_distribution, calc_paiement_distribution,
    calc_kpi_by_vague, calc_delta, get_latest_vague, get_previous_vague,
    calc_funnel, get_parieurs, VAGUE_SHORT, MAIN_COMPETITORS
)
from components.styles import kpi_card, section_header, insight_box, styled_divider
from components.charts import (
    bar_chart_brands, line_chart_evolution, donut_chart, funnel_chart,
    multi_line_chart, BETCLIC_RED, OPINIONWAY_PURPLE, COLORS_SEQ
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

    for col, label, vdata, is_currency in [
        (col1, "Pénétration", pen_v, False),
        (col2, "Marque Principale", mp_v, False),
        (col3, "Multi-App", multi_v, False),
        (col4, "Considération", consid_v, False),
        (col5, "Préférence", pref_v, False),
        (col6, "Wallet Share", wallet_v, True),
    ]:
        latest = get_latest_vague(vdata)
        prev = get_previous_vague(vdata)
        d, direction = calc_delta(latest, prev)
        if is_currency:
            value_str = f"{int(round(float(latest))):,}".replace(",", " ") + " F CFA"
            if d:
                try:
                    raw = float(str(d).replace(",", ".").replace("+", "").strip())
                    sign = "+" if raw >= 0 else "−"
                    delta_str = f"{sign}{int(round(abs(raw))):,}".replace(",", " ") + " F CFA"
                except Exception:
                    delta_str = f"{d} F CFA"
            else:
                delta_str = None
        else:
            value_str = f"{latest}%"
            delta_str = f"{d} pt" if d else None
        with col:
            st.markdown(kpi_card(label, value_str, delta_str, direction), unsafe_allow_html=True)

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

    # ── Comparatif concurrentiel : Pénétration vs Marque Principale ──
    st.markdown(section_header(
        "Comparatif concurrentiel",
        "Pénétration (Q5 : a déjà parié) vs Marque Principale (Q6) par marque"
    ), unsafe_allow_html=True)

    pen_all = calc_penetration_all_brands(df_latest)
    mp_all = calc_marque_principale_all(df_latest)

    fig_cmp = go.Figure()
    fig_cmp.add_trace(go.Bar(
        name="Pénétration (Q5)",
        x=MAIN_COMPETITORS,
        y=[pen_all.get(b, 0) for b in MAIN_COMPETITORS],
        text=[f"{pen_all.get(b, 0):.1f}%" for b in MAIN_COMPETITORS],
        textposition="outside",
        marker_color=BETCLIC_RED,
    ))
    fig_cmp.add_trace(go.Bar(
        name="Marque Principale (Q6)",
        x=MAIN_COMPETITORS,
        y=[mp_all.get(b, 0) for b in MAIN_COMPETITORS],
        text=[f"{mp_all.get(b, 0):.1f}%" for b in MAIN_COMPETITORS],
        textposition="outside",
        marker_color=OPINIONWAY_PURPLE,
    ))
    fig_cmp.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#1A1D23", size=12),
        margin=dict(l=40, r=40, t=50, b=80),
        height=400,
        title=dict(text="Funnel essai → préférence par marque", font=dict(size=15)),
        yaxis=dict(range=[0, max(max(pen_all.values()), max(mp_all.values())) * 1.2], gridcolor="rgba(0,0,0,0.06)", title="%"),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.18),
    )
    st.plotly_chart(fig_cmp, width='stretch')

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Part de marché : Volume vs Valeur ──
    st.markdown(section_header(
        "Part de Marché — Volume vs Valeur",
        "PDM Volume = part des utilisateurs principaux (Q6) | PDM Valeur = part du chiffre d'affaires théorique (Q6 × Q10)"
    ), unsafe_allow_html=True)

    pdm_valeur_all = calc_pdm_valeur_all_brands(df_latest)

    fig_pdm = go.Figure()
    fig_pdm.add_trace(go.Bar(
        name="PDM Volume (% utilisateurs principaux)",
        x=MAIN_COMPETITORS,
        y=[mp_all.get(b, 0) for b in MAIN_COMPETITORS],
        text=[f"{mp_all.get(b, 0):.1f}%" for b in MAIN_COMPETITORS],
        textposition="outside",
        marker_color=BETCLIC_RED,
    ))
    fig_pdm.add_trace(go.Bar(
        name="PDM Valeur (% du marché en FCFA)",
        x=MAIN_COMPETITORS,
        y=[pdm_valeur_all.get(b, 0) for b in MAIN_COMPETITORS],
        text=[f"{pdm_valeur_all.get(b, 0):.1f}%" for b in MAIN_COMPETITORS],
        textposition="outside",
        marker_color=OPINIONWAY_PURPLE,
    ))
    fig_pdm.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#1A1D23", size=12),
        margin=dict(l=40, r=40, t=50, b=80),
        height=420,
        title=dict(text="PDM Volume vs PDM Valeur par marque", font=dict(size=15)),
        yaxis=dict(range=[0, max(max(mp_all.values()), max(pdm_valeur_all.values())) * 1.25],
                   gridcolor="rgba(0,0,0,0.06)", title="%"),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.18),
    )
    st.plotly_chart(fig_pdm, width='stretch')

    # Insight comparison + table
    import pandas as _pd
    table_rows = []
    for b in MAIN_COMPETITORS:
        vol = mp_all.get(b, 0)
        val = pdm_valeur_all.get(b, 0)
        ratio = round(val - vol, 1)
        table_rows.append({
            "Marque": b,
            "PDM Volume (%)": vol,
            "PDM Valeur (%)": val,
            "Écart Valeur-Volume": f"+{ratio} pt" if ratio > 0 else f"{ratio} pt" if ratio < 0 else "≈ 0",
        })
    st.dataframe(_pd.DataFrame(table_rows).set_index("Marque"), width='stretch', height=240)
    st.caption(
        "💡 Écart positif = utilisateurs à plus fort budget (marque premium en valeur) · "
        "Écart négatif = utilisateurs à plus petit budget (marque populaire en volume mais moins en valeur)."
    )

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Marque principale ──
    col_left, col_right = st.columns(2)
    with col_left:
        fig = bar_chart_brands(mp_all, "Marque Principale des parieurs (toutes marques)", height=380)
        st.plotly_chart(fig, width='stretch')

    with col_right:
        wallet_evol = {v: wallet_v[v] for v in ["Vague 1", "Vague 2", "Vague 3"] if wallet_v.get(v) is not None}
        if len(wallet_evol) >= 2:
            fig = line_chart_evolution(wallet_evol, "Évolution Wallet Share Betclic (F CFA / mois)", height=380)
            st.plotly_chart(fig, width='stretch')
        else:
            fig = bar_chart_brands(pdm_valeur_all, "PDM Valeur — toutes marques", height=380)
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
