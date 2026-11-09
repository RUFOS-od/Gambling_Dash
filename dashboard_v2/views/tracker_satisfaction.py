"""Brand Health Tracker · Satisfaction & Fidélité."""

import streamlit as st
from data.loader import (
    sort_vagues, get_main_competitors, keep_brands,
    apply_filters, calc_satisfaction, calc_satisfaction_all_brands,
    calc_nps, calc_nps_by_brand, calc_nps_all_brands, calc_churn_risk,
    calc_irritants, calc_motifs_satisfaction, load_verbatim_themes,
    calc_kpi_by_vague, calc_delta, get_latest_vague, get_previous_vague,
    get_utilisateurs_betclic, MAIN_COMPETITORS
)
from components.styles import kpi_card, section_header, insight_box, styled_divider
from components.narrative import trend_word, signed, prev_wave_label
from components.charts import (
    nps_gauge, line_chart_evolution, donut_chart, bar_chart_brands,
    BETCLIC_RED, OPINIONWAY_PURPLE, COLORS_SEQ, brand_color
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
    _waves = sort_vagues(df["Vague"].dropna().unique().tolist())
    main_brands = get_main_competitors(df)  # Betclic + 4 concurrents, selon les données

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
        latest_vague = [v for v in _waves[::-1] if v in vagues]
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
        # NPS + Satisfaction evolution · affiché seulement si au moins 2 vagues disponibles
        nps_evol = {v: nps_v[v] for v in _waves if nps_v.get(v) is not None}
        sat_evol = {v: sat_v[v] for v in _waves if sat_v.get(v) is not None}

        if len(nps_evol) >= 2:
            fig = line_chart_evolution(nps_evol, "Évolution NPS", suffix=" pts", height=300)
            st.plotly_chart(fig, width='stretch')
        if len(sat_evol) >= 2:
            fig = line_chart_evolution(sat_evol, "Évolution Satisfaction", suffix="/5", height=300)
            st.plotly_chart(fig, width='stretch')
        if len(nps_evol) < 2 and len(sat_evol) < 2:
            st.info(
                "📊 Les courbes d'évolution s'affichent dès que 2 vagues au moins sont sélectionnées."
            )

    # Insight
    latest_sat = get_latest_vague(sat_v)
    prev_sat = get_previous_vague(sat_v)
    d_sat = round(latest_sat - prev_sat, 2) if (latest_sat is not None and prev_sat is not None) else None
    latest_nps_v = get_latest_vague(nps_v)
    delta_nps, _ = calc_delta(latest_nps_v, get_previous_vague(nps_v))
    _prev = prev_wave_label(nps_v)
    _vs = f" vs {_prev}" if _prev else ""
    _nps_detail = calc_nps(df[df["Vague"] == latest_vague[0]]) if latest_vague else {}
    _sat_delta_txt = f" ({d_sat:+.2f}{_vs})" if d_sat is not None else ""
    st.markdown(insight_box(
        f"La satisfaction {trend_word(d_sat, threshold=0.05)} à <strong>{latest_sat}/5</strong>{_sat_delta_txt}. "
        f"Le NPS {trend_word(delta_nps)} à <strong>{latest_nps_v} pts</strong> ({signed(delta_nps, 'pts')}{_vs}) : "
        f"{_nps_detail.get('promoteurs', 0)}% de promoteurs pour "
        f"{_nps_detail.get('detracteurs', 0)}% de détracteurs."
    ), unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Churn Risk + Verbatims NPS ──
    st.markdown(section_header(
        "Risque de Churn & Verbatims NPS",
        "Profil de risque et raisons exprimées par les utilisateurs Betclic"
    ), unsafe_allow_html=True)

    col_left, col_right = st.columns(2)

    with col_left:
        if latest_vague:
            churn = calc_churn_risk(df[df["Vague"] == latest_vague[0]])
            if churn:
                fig = donut_chart(churn, "Répartition Risque de Churn", colors=["#27AE60", "#F39C12", "#E74C3C"], height=350)
                st.plotly_chart(fig, width='stretch')

        # Churn evolution · affiché seulement si au moins 2 vagues
        churn_evol = {v: churn_v[v] for v in _waves if churn_v.get(v) is not None}
        if len(churn_evol) >= 2:
            fig = line_chart_evolution(churn_evol, "Évolution Churn Élevé (%)", height=300)
            st.plotly_chart(fig, width='stretch')

    with col_right:
        if latest_vague:
            wave_name = latest_vague[0]
            themes_data = load_verbatim_themes(wave_name)

            t_irr, t_sat = st.tabs([
                "🔴 Irritants (Détracteurs)",
                "🟢 Motifs satisfaction (Promoteurs)",
            ])

            def _render_themes(block: dict | None, color: str, palette_label: str):
                if not block or not block.get("themes"):
                    note = (block or {}).get("note") or "Thèmes non encore générés."
                    st.info(note)
                    return
                n_total = block.get("n_total", 0)
                themes = block["themes"]
                # Bar chart of themes
                fig = go.Figure(go.Bar(
                    y=[t["label"] for t in themes][::-1],
                    x=[t["share_pct"] for t in themes][::-1],
                    orientation="h",
                    marker=dict(color=color),
                    text=[f"{t['share_pct']:.0f}% ({t['count']})" for t in themes][::-1],
                    textposition="outside",
                    textfont=dict(size=11),
                ))
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter, sans-serif", color="#1A1D23", size=11),
                    margin=dict(l=10, r=80, t=30, b=30),
                    height=380,
                    title=dict(text=f"Thèmes {palette_label} · base : {n_total} verbatims", font=dict(size=13)),
                    xaxis=dict(range=[0, max(t["share_pct"] for t in themes) * 1.25],
                               gridcolor="rgba(0,0,0,0.06)", showticklabels=False),
                    yaxis=dict(automargin=True),
                )
                st.plotly_chart(fig, width='stretch')

                # Illustrative quotes for top 3 themes
                st.markdown("**Verbatims illustratifs**")
                for t in themes[:3]:
                    quotes = t.get("illustrative_quotes", [])
                    if quotes:
                        quote_html = "<br>".join(f"• <em>« {q} »</em>" for q in quotes)
                        st.markdown(
                            f"""<div style="background:#FFFFFF;border-left:3px solid {color};
                            padding:0.7rem 1rem;margin-bottom:0.5rem;border-radius:6px;
                            font-size:0.85rem;color:#4A5568;">
                            <strong style="color:#1A1D23;">{t['label']}</strong><br>{quote_html}
                            </div>""",
                            unsafe_allow_html=True,
                        )

            with t_irr:
                if themes_data:
                    _render_themes(themes_data.get("detractors"), "#E74C3C", "détracteurs")
                    st.caption(f"Thèmes générés par IA · {themes_data.get('generated_at','')[:16].replace('T',' ')}")
                else:
                    st.info(
                        "Thèmes non encore générés pour cette vague. "
                        "Exécuter `python dashboard_v2/scripts/build_verbatim_themes.py --vague N`."
                    )
            with t_sat:
                if themes_data:
                    _render_themes(themes_data.get("promoters"), "#27AE60", "promoteurs")
                    st.caption(f"Thèmes générés par IA · {themes_data.get('generated_at','')[:16].replace('T',' ')}")
                else:
                    st.info(
                        "Thèmes non encore générés pour cette vague. "
                        "Exécuter `python dashboard_v2/scripts/build_verbatim_themes.py --vague N`."
                    )

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Comparatif concurrentiel ──
    st.markdown(section_header(
        "Satisfaction & NPS · Comparaison concurrentielle",
        "Indicateurs mesurés sur les utilisateurs principaux de chaque marque (Q6)"
    ), unsafe_allow_html=True)

    df_eval = df[df["Vague"] == latest_vague[0]] if latest_vague else df
    sat_all = calc_satisfaction_all_brands(df_eval)
    nps_all = calc_nps_all_brands(df_eval)

    # Keep only brands with at least 10 respondents for reliable scores
    base_per_brand = {b: int((df_eval["Marque_Principale_Utilisee"] == b).sum()) for b in main_brands}
    eligible = [b for b in main_brands if base_per_brand[b] >= 10]

    if eligible:
        col_l, col_r = st.columns(2)
        with col_l:
            fig_sat = go.Figure()
            fig_sat.add_trace(go.Bar(
                x=eligible,
                y=[sat_all.get(b, 0) for b in eligible],
                text=[f"{sat_all.get(b, 0):.2f}/5" for b in eligible],
                textposition="outside",
                marker_color=[brand_color(b) for b in eligible],
            ))
            fig_sat.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", color="#1A1D23", size=12),
                margin=dict(l=40, r=40, t=50, b=40),
                height=380,
                title=dict(text="Satisfaction globale (/5) par marque", font=dict(size=15)),
                yaxis=dict(range=[0, 5.3], gridcolor="rgba(0,0,0,0.06)"),
                showlegend=False,
            )
            st.plotly_chart(fig_sat, width='stretch')

        with col_r:
            fig_nps = go.Figure()
            fig_nps.add_trace(go.Bar(
                x=eligible,
                y=[nps_all.get(b, 0) for b in eligible],
                text=[f"{nps_all.get(b, 0):.0f}" for b in eligible],
                textposition="outside",
                marker_color=[brand_color(b) for b in eligible],
            ))
            min_nps = min(nps_all.get(b, 0) for b in eligible)
            max_nps = max(nps_all.get(b, 0) for b in eligible)
            fig_nps.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", color="#1A1D23", size=12),
                margin=dict(l=40, r=40, t=50, b=40),
                height=380,
                title=dict(text="NPS par marque", font=dict(size=15)),
                yaxis=dict(range=[min(min_nps, -10) - 10, max(max_nps, 10) + 15],
                           gridcolor="rgba(0,0,0,0.06)", zeroline=True, zerolinecolor="#1A1D23"),
                showlegend=False,
            )
            st.plotly_chart(fig_nps, width='stretch')

        # Caption with base sizes
        base_str = " • ".join([f"{b}: n={base_per_brand[b]}" for b in eligible])
        st.caption(f"Base d'utilisateurs principaux par marque · {base_str}")
    else:
        st.info("Pas assez d'utilisateurs principaux pour comparer (minimum 10 par marque).")
