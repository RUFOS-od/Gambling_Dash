"""Brand Health Tracker · Casino en ligne (Section 5B du questionnaire, à partir de V4)."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from data.loader import (
    apply_filters, sort_vagues, vague_short, VAGUE_MONTHS, MAIN_COMPETITORS,
    calc_kpi_by_vague, calc_delta, get_latest_vague, get_previous_vague,
    get_casino_base, get_casino_joueurs, load_verbatim_themes,
    calc_casino_statut, calc_casino_penetration, calc_casino_penetration_active,
    calc_casino_offre_notoriete, calc_casino_offre_notoriete_all,
    calc_casino_penetration_brand, calc_casino_penetration_all,
    calc_casino_marque_principale, calc_casino_marque_principale_all,
    calc_casino_pdm_volume, calc_casino_pdm_volume_all,
    calc_casino_frequence, calc_casino_jeux, calc_casino_pratique,
    calc_casino_funnel, calc_casino_cross_sell,
)
from components.styles import kpi_card, section_header, insight_box, styled_divider
from components.charts import funnel_chart, donut_chart, brand_color, BETCLIC_RED, OPINIONWAY_PURPLE

# 1WIN est ajouté aux marques principales : acteur très orienté casino.
CASINO_BRANDS = MAIN_COMPETITORS + ["1WIN"]


def _brand_bar(data: dict, title: str, height: int = 340, suffix: str = "%"):
    brands = sorted([b for b in CASINO_BRANDS if b in data], key=lambda b: -data.get(b, 0))
    vals = [data.get(b, 0) for b in brands]
    fig = go.Figure(go.Bar(
        x=brands, y=vals,
        text=[f"{v:.1f}{suffix}" for v in vals],
        textposition="outside",
        textfont=dict(size=12),
        marker_color=[brand_color(b) for b in brands],
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#1A1D23", size=12),
        margin=dict(l=40, r=40, t=50, b=40),
        height=height,
        title=dict(text=title, font=dict(size=14)),
        yaxis=dict(range=[0, (max(vals) * 1.25) if vals and max(vals) > 0 else 100],
                   gridcolor="rgba(0,0,0,0.06)", title="%"),
        showlegend=False,
    )
    return fig


def _horizontal_bar(dist: dict, title: str, color: str, height: int = 330, keep_order: bool = False):
    if not dist:
        return None
    items = list(dist.items()) if keep_order else sorted(dist.items(), key=lambda x: x[1], reverse=True)
    labels = [k for k, _ in items][::-1]
    values = [v for _, v in items][::-1]
    fig = go.Figure(go.Bar(
        y=labels, x=values, orientation="h",
        marker=dict(color=color),
        text=[f"{v:.1f}%" for v in values],
        textposition="outside",
        textfont=dict(size=12, color="#1A1D23"),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#1A1D23", size=11),
        margin=dict(l=10, r=70, t=40, b=20),
        height=height,
        title=dict(text=title, font=dict(size=14)),
        xaxis=dict(range=[0, max(values) * 1.2 if values else 100], showticklabels=False,
                   gridcolor="rgba(0,0,0,0.04)"),
        yaxis=dict(automargin=True),
    )
    return fig


def _render_themes(block: dict, color: str):
    themes = block.get("themes") or []
    n_total = block.get("n_total", 0)
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
        margin=dict(l=10, r=80, t=40, b=30),
        height=380,
        title=dict(text=f"Premier contact avec Betclic Casino · base : {n_total} réponses", font=dict(size=13)),
        xaxis=dict(range=[0, max(t["share_pct"] for t in themes) * 1.25],
                   gridcolor="rgba(0,0,0,0.06)", showticklabels=False),
        yaxis=dict(automargin=True),
    )
    st.plotly_chart(fig, width='stretch')
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


def render():
    data = st.session_state["data"]
    vagues = st.session_state["selected_vagues"]
    villes = st.session_state["selected_villes"]
    genres = st.session_state["selected_genres"]
    segments = st.session_state["selected_segments"]
    ages = st.session_state.get("selected_ages", [])

    df = apply_filters(data, vagues, villes or None, genres or None, segments or None, ages=ages or None)
    base_all = get_casino_base(df)
    casino_waves = sort_vagues(base_all["Vague"].dropna().unique().tolist())

    st.markdown(section_header(
        "Casino en ligne",
        "Notoriété de l'offre casino, pratique et marques utilisées | Module introduit en V4"
    ), unsafe_allow_html=True)

    if not casino_waves:
        st.info(
            "Le module Casino en ligne a été ajouté au questionnaire à partir de la Vague 4 "
            "(Novembre 2026). Sélectionnez la Vague 4 dans les filtres pour afficher ces résultats."
        )
        return

    lv = casino_waves[-1]
    df_lv = df[df["Vague"] == lv]
    base = get_casino_base(df_lv)
    joueurs = get_casino_joueurs(df_lv)
    n_base, n_joueurs = len(base), len(joueurs)

    st.caption(
        f"Vague {vague_short(lv)} ({VAGUE_MONTHS.get(lv, '')}) · base échantillon total : n = {n_base} · "
        f"joueurs casino (ont déjà joué en ligne) : n = {n_joueurs}"
    )

    # ── KPI cards (delta seulement si au moins 2 vagues casino) ──
    df_cas = df[df["Vague"].isin(casino_waves)]
    kpis_row1 = [
        ("Ont déjà joué au casino en ligne", calc_casino_penetration, {}),
        ("Joueurs actifs (6 derniers mois)", calc_casino_penetration_active, {}),
        ("Notoriété offre Betclic Casino", calc_casino_offre_notoriete, {"brand": "Betclic"}),
        ("Pénétration Betclic Casino", calc_casino_penetration_brand, {"brand": "Betclic"}),
    ]
    kpis_row2 = [
        ("Marque casino principale Betclic", calc_casino_marque_principale, {"brand": "Betclic"}),
        ("PDM Volume casino Betclic", calc_casino_pdm_volume, {"brand": "Betclic"}),
    ]

    def _render_row(items):
        cols = st.columns(len(items))
        for col, (label, fn, kw) in zip(cols, items):
            by_v = calc_kpi_by_vague(df_cas, fn, **kw)
            by_v = {k: v for k, v in by_v.items() if k in casino_waves}
            latest = get_latest_vague(by_v)
            prev = get_previous_vague(by_v)
            d, direction = calc_delta(latest, prev)
            with col:
                st.markdown(kpi_card(label, f"{latest}%", f"{d} pt" if d else None, direction),
                            unsafe_allow_html=True)

    _render_row(kpis_row1)
    st.markdown("", unsafe_allow_html=True)

    cross = calc_casino_cross_sell(df_lv, "Betclic")
    cols = st.columns(4)
    _render_row_cols = cols[:2]
    for col, (label, fn, kw) in zip(_render_row_cols, kpis_row2):
        by_v = {k: v for k, v in calc_kpi_by_vague(df_cas, fn, **kw).items() if k in casino_waves}
        latest = get_latest_vague(by_v)
        d, direction = calc_delta(latest, get_previous_vague(by_v))
        with col:
            st.markdown(kpi_card(label, f"{latest}%", f"{d} pt" if d else None, direction), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(kpi_card("Parieurs Betclic ayant joué à son casino",
                             f"{cross.get('taux_parieurs', 0)}%", None, "neutral"), unsafe_allow_html=True)
    with cols[3]:
        st.markdown(kpi_card("Conversion offre connue vers jeu",
                             f"{cross.get('taux_conversion_offre', 0)}%", None, "neutral"), unsafe_allow_html=True)
    st.caption(
        "Bases : notoriété de l'offre, pénétration = échantillon total · marque casino principale = joueurs casino "
        f"ayant répondu · passerelle = parieurs ayant déjà parié sur Betclic (n = {cross.get('n_parieurs', 0)}) · "
        f"conversion = répondants sachant que Betclic propose du casino (n = {cross.get('n_offre', 0)})."
    )

    # ── Insight ──
    offre_all = calc_casino_offre_notoriete_all(df_lv)
    pdm_all = calc_casino_pdm_volume_all(df_lv)
    mp_all = calc_casino_marque_principale_all(df_lv)
    jeux = calc_casino_jeux(df_lv)
    leader_pdm = max(pdm_all.items(), key=lambda x: x[1]) if pdm_all else (None, 0)
    leader_offre = max(offre_all.items(), key=lambda x: x[1]) if offre_all else (None, 0)
    top_jeu = next(iter(jeux.items()), (None, 0))
    txt = (
        f"<strong>{calc_casino_penetration(df_lv)}%</strong> des répondants ont déjà joué au casino en ligne "
        f"(<strong>{calc_casino_penetration_active(df_lv)}%</strong> au cours des 6 derniers mois). "
    )
    if leader_offre[0] and leader_offre[0] != "Betclic":
        txt += (f"L'offre casino de Betclic est connue de <strong>{offre_all.get('Betclic', 0)}%</strong> "
                f"de l'échantillon, contre {leader_offre[1]}% pour {leader_offre[0]}. ")
    else:
        txt += f"Betclic a l'offre casino la plus connue ({offre_all.get('Betclic', 0)}%). "
    if leader_pdm[0] and leader_pdm[0] != "Betclic":
        txt += (f"En PDM Volume casino, <strong>{leader_pdm[0]}</strong> mène ({leader_pdm[1]}%) devant "
                f"Betclic ({pdm_all.get('Betclic', 0)}%). ")
    else:
        txt += f"Betclic mène en PDM Volume casino ({pdm_all.get('Betclic', 0)}%). "
    if top_jeu[0]:
        txt += f"Type de jeu le plus pratiqué : <strong>{top_jeu[0]}</strong> ({top_jeu[1]}% des joueurs)."
    st.markdown(insight_box(txt), unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Entonnoirs casino Betclic vs 1XBET ──
    st.markdown(section_header(
        "Entonnoir casino",
        "Base échantillon total · étapes emboîtées : notoriété, connaissance de l'offre, essai, marque principale"
    ), unsafe_allow_html=True)
    col_l, col_r = st.columns(2)
    with col_l:
        st.plotly_chart(funnel_chart(calc_casino_funnel(df_lv, "Betclic"),
                                     f"Betclic Casino ({vague_short(lv)})", height=360), width='stretch')
    with col_r:
        st.plotly_chart(funnel_chart(calc_casino_funnel(df_lv, "1XBET"),
                                     f"1XBET Casino ({vague_short(lv)})", height=360), width='stretch')

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Comparatif concurrentiel ──
    st.markdown(section_header(
        "Comparatif concurrentiel casino",
        "Betclic vs principaux concurrents (1WIN ajouté, acteur orienté casino)"
    ), unsafe_allow_html=True)
    pen_all = calc_casino_penetration_all(df_lv)
    r1l, r1r = st.columns(2)
    with r1l:
        st.plotly_chart(_brand_bar(offre_all, "Sait que la marque propose du casino (QC1)"), width='stretch')
    with r1r:
        st.plotly_chart(_brand_bar(pen_all, "A déjà joué au casino sur la marque (QC4)"), width='stretch')
    r2l, r2r = st.columns(2)
    with r2l:
        st.plotly_chart(_brand_bar(mp_all, "Marque casino principale (QC5 · base joueurs)"), width='stretch')
    with r2r:
        st.plotly_chart(_brand_bar(pdm_all, "PDM Volume casino (QC4 marque / total QC4)"), width='stretch')

    rows = []
    for b in sorted(CASINO_BRANDS, key=lambda b: -pdm_all.get(b, 0)):
        cs = calc_casino_cross_sell(df_lv, b)
        rows.append({
            "Marque": b,
            "Notoriété offre casino (%)": offre_all.get(b, 0),
            "Pénétration casino (%)": pen_all.get(b, 0),
            "Marque casino principale (%)": mp_all.get(b, 0),
            "PDM Volume casino (%)": pdm_all.get(b, 0),
            "Parieurs de la marque ayant joué à son casino (%)": cs.get("taux_parieurs", 0),
        })
    st.dataframe(pd.DataFrame(rows).set_index("Marque"), width='stretch', height=280)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Profil des joueurs ──
    st.markdown(section_header(
        "Profil des joueurs casino",
        "Statut, fréquence, types de jeux et arbitrage avec les paris sportifs"
    ), unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        statut = calc_casino_statut(df_lv)
        if statut:
            st.plotly_chart(donut_chart(statut, "Pratique du casino en ligne (QC3 · base totale)",
                                        colors=[BETCLIC_RED, "#F39C12", "#CBD5E0"], height=340), width='stretch')
    with c2:
        fig = _horizontal_bar(calc_casino_frequence(df_lv), "Fréquence de jeu casino (QC6 · base joueurs)",
                              OPINIONWAY_PURPLE, keep_order=True)
        if fig:
            st.plotly_chart(fig, width='stretch')
    c3, c4 = st.columns(2)
    with c3:
        fig = _horizontal_bar(jeux, "Types de jeux pratiqués (QC7 · multi-réponse, base joueurs)", "#2980B9")
        if fig:
            st.plotly_chart(fig, width='stretch')
    with c4:
        pratique = calc_casino_pratique(df_lv)
        if pratique:
            st.plotly_chart(donut_chart(pratique, "Paris sportifs vs casino (QC8 · base joueurs)",
                                        colors=["#2980B9", "#F39C12", BETCLIC_RED], height=340), width='stretch')

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Découverte de Betclic Casino (QC2, question ouverte) ──
    st.markdown(section_header(
        "Comment Betclic Casino a été découvert",
        "QC2 · question ouverte posée aux répondants sachant que Betclic propose du casino"
    ), unsafe_allow_html=True)
    themes = (load_verbatim_themes(lv) or {}).get("casino_decouverte")
    if themes and themes.get("themes"):
        _render_themes(themes, BETCLIC_RED)
        st.caption("Thèmes générés par IA sur l'ensemble de la vague (hors filtres).")
    else:
        verb = base["Casino_Decouverte_Betclic"].dropna().astype(str).str.strip()
        verb = verb[verb.str.len() > 1]
        if len(verb):
            st.info("Thèmes non encore générés pour cette vague. Aperçu des réponses les plus fréquentes :")
            top = verb.str.lower().value_counts().head(10)
            st.dataframe(pd.DataFrame({"Réponse": top.index, "Citations": top.values}),
                         width='stretch', hide_index=True)
