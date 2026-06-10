"""Brand Health Tracker · Usage & Pénétration."""

import streamlit as st
from data.loader import (
    apply_filters, calc_penetration, calc_marque_principale, calc_marque_principale_all,
    calc_penetration_all_brands, calc_pdm_volume_all_brands,
    calc_multi_app, calc_consideration, calc_preference,
    calc_sport_distribution, calc_pari_type_distribution, calc_paiement_distribution,
    calc_kpi_by_vague, calc_delta, get_latest_vague, get_previous_vague,
    calc_funnel, get_parieurs, VAGUE_SHORT, MAIN_COMPETITORS
)
from components.styles import kpi_card, section_header, insight_box, styled_divider
from components.charts import (
    bar_chart_brands, line_chart_evolution, donut_chart, funnel_chart,
    multi_line_chart, BETCLIC_RED, OPINIONWAY_PURPLE, COLORS_SEQ, brand_color
)
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
        "Usage & Pénétration",
        "Funnel de conversion, multi-app, paiements et sports"
    ), unsafe_allow_html=True)

    # ── KPI Cards ──
    pen_v = calc_kpi_by_vague(df, calc_penetration)
    mp_v = calc_kpi_by_vague(df, calc_marque_principale)
    multi_v = calc_kpi_by_vague(df, calc_multi_app)
    consid_v = calc_kpi_by_vague(df, calc_consideration)
    pref_v = calc_kpi_by_vague(df, calc_preference)

    col1, col2, col3 = st.columns(3)
    col4, col5 = st.columns(2)

    for col, label, vdata in [
        (col1, "Pénétration", pen_v),
        (col2, "Marque Principale", mp_v),
        (col3, "Multi-App", multi_v),
        (col4, "Considération", consid_v),
        (col5, "Préférence", pref_v),
    ]:
        latest = get_latest_vague(vdata)
        prev = get_previous_vague(vdata)
        d, direction = calc_delta(latest, prev)
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

    # ── Comparatif concurrentiel ──
    st.markdown(section_header(
        "Comparatif concurrentiel",
        "Pénétration (Q5) et Marque Principale (Q6) par marque"
    ), unsafe_allow_html=True)

    pen_all = calc_penetration_all_brands(df_latest)
    mp_all = calc_marque_principale_all(df_latest)
    pdm_vol_all = calc_pdm_volume_all_brands(df_latest)

    # Helper pour bar charts simples par marque — couleurs charte client
    def _brand_bar(data: dict, title: str, height: int = 380):
        sorted_brands = sorted(MAIN_COMPETITORS, key=lambda b: -data.get(b, 0))
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

    # 1) Pénétrations groupées (toutes les marques côte à côte)
    st.plotly_chart(
        _brand_bar(pen_all, "Pénétration par marque (Q5 · a déjà parié sur)"),
        width='stretch',
    )

    # 2) Marques principales groupées (toutes les marques côte à côte)
    st.plotly_chart(
        _brand_bar(mp_all, "Marque Principale par marque (Q6)"),
        width='stretch',
    )

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Part de Marché en Volume (basée sur Q5, somme = 100%) ──
    st.markdown(section_header(
        "Part de Marché en Volume",
        "PDM Volume = essais par marque sur l'ensemble des essais marché (Q5_marque / Σ Q5)"
    ), unsafe_allow_html=True)

    st.plotly_chart(
        _brand_bar(pdm_vol_all, "PDM Volume par marque", height=420),
        width='stretch',
    )

    # Tableau récap
    import pandas as _pd
    table_rows = []
    for b in sorted(MAIN_COMPETITORS, key=lambda b: -pdm_vol_all.get(b, 0)):
        table_rows.append({
            "Marque": b,
            "Pénétration Q5 (%)": pen_all.get(b, 0),
            "PDM Volume (%)": pdm_vol_all.get(b, 0),
            "Marque Principale Q6 (%)": mp_all.get(b, 0),
        })
    st.dataframe(_pd.DataFrame(table_rows).set_index("Marque"), width='stretch', height=240)
    st.caption(
        f"📊 Somme PDM Volume sur l'ensemble des marques · {sum(pdm_vol_all.values()):.0f}% "
        "(léger écart possible dû aux arrondis)."
    )

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Marque principale / PDM Volume (toutes marques) ──
    col_left, col_right = st.columns(2)
    with col_left:
        fig = bar_chart_brands(mp_all, "Marque Principale des parieurs (toutes marques)", height=380)
        st.plotly_chart(fig, width='stretch')

    with col_right:
        fig = bar_chart_brands(pdm_vol_all, "PDM Volume · toutes marques", height=380)
        st.plotly_chart(fig, width='stretch')

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Sports, Paris, Paiements ──
    st.markdown(section_header("Profil des Parieurs", "Sports, types de paris et moyens de paiement"), unsafe_allow_html=True)

    def _horizontal_bar(dist: dict, title: str, color: str, height: int = 320):
        """Trie décroissant + horizontal bar chart : lisible même si très déséquilibré."""
        if not dist:
            return None
        sorted_items = sorted(dist.items(), key=lambda x: x[1], reverse=True)
        labels = [k for k, _ in sorted_items][::-1]  # reverse for plotly y-axis top-down
        values = [v for _, v in sorted_items][::-1]
        # Shorten very long labels (e.g. mobile money providers)
        def _short(lbl):
            if len(lbl) <= 35:
                return lbl
            return lbl[:32].rsplit(" ", 1)[0] + "…"
        fig = go.Figure(go.Bar(
            y=[_short(l) for l in labels],
            x=values,
            orientation="h",
            marker=dict(color=color),
            text=[f"{v:.1f}%" for v in values],
            textposition="outside",
            textfont=dict(size=12, color="#1A1D23"),
            hovertext=labels,
            hovertemplate="%{hovertext}<br>%{x:.1f}%<extra></extra>",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="#1A1D23", size=11),
            margin=dict(l=10, r=70, t=40, b=20),
            height=height,
            title=dict(text=title, font=dict(size=14)),
            xaxis=dict(range=[0, max(values) * 1.18], showticklabels=False,
                       gridcolor="rgba(0,0,0,0.04)"),
            yaxis=dict(automargin=True),
        )
        return fig

    col1, col2, col3 = st.columns(3)

    with col1:
        sports = calc_sport_distribution(df_latest)
        fig = _horizontal_bar(sports, "Sports sur lesquels les parieurs misent (Q11, multi-réponse)", BETCLIC_RED)
        if fig:
            st.plotly_chart(fig, width='stretch')

    with col2:
        paiements = calc_paiement_distribution(df_latest)
        fig = _horizontal_bar(paiements, "Moyen de paiement le plus utilisé (Q9)", "#2980B9")
        if fig:
            st.plotly_chart(fig, width='stretch')

    with col3:
        types = calc_pari_type_distribution(df_latest)
        fig = _horizontal_bar(types, "Type de pari préféré", OPINIONWAY_PURPLE)
        if fig:
            st.plotly_chart(fig, width='stretch')
        else:
            st.caption("Donnée Type de pari non collectée dans cette vague.")
