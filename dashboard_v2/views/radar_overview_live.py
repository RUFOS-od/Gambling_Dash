"""AI Market Radar · Vue d'ensemble (données réelles issues des collecteurs)."""

import streamlit as st
import plotly.graph_objects as go

from components.styles import section_header, insight_box, styled_divider, kpi_card
from components.charts import bar_chart_brands
from components.llm_analyst import detect_weak_signals
from components.radar_common import (load_radar, collected_caption, news_sentiment,
                                     share_of_voice, share_of_search)


def _empty_state():
    st.warning(
        "Aucune donnée de veille disponible. Cliquez sur **Rafraîchir la veille** "
        "dans le menu latéral pour lancer la collecte."
    )


def render():
    st.markdown(section_header(
        "AI Market Radar · Vue d'ensemble",
        "Veille concurrentielle du marché ivoirien des paris sportifs : présence médiatique, "
        "recherches Google et tonalité"
    ), unsafe_allow_html=True)

    R = load_radar()
    if R["empty"]:
        _empty_state()
        return
    st.caption(collected_caption(R))

    sov, counts, n_sov = share_of_voice(R)
    sos = share_of_search(R)
    with st.spinner("Analyse de la tonalité des articles..."):
        sent = news_sentiment(R["news"])
    signals = detect_weak_signals(news_df=R["news"], trends_df=R["trends"])
    n_high = sum(1 for s in signals if s["severity"] == "high")

    # ── KPIs ──
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        lead = max(sov.items(), key=lambda x: x[1])[0] if sov else None
        st.markdown(kpi_card(
            "Part de voix Betclic", f"{sov.get('Betclic', 0):.1f} %".replace(".", ","),
            f"{counts.get('Betclic', 0)} contenus sur {n_sov}" if lead == "Betclic" or not lead
            else f"{lead} en tête ({sov[lead]:.1f} %)".replace(".", ","), "neutral",
        ), unsafe_allow_html=True)
    with c2:
        lead_s = max(sos.items(), key=lambda x: x[1])[0] if sos else None
        st.markdown(kpi_card(
            "Part de recherche Betclic", f"{sos.get('Betclic', 0):.1f} %".replace(".", ",") if sos else "n.d.",
            "Google, 12 dernières semaines" if lead_s in (None, "Betclic")
            else f"{lead_s} en tête ({sos[lead_s]:.1f} %)".replace(".", ","), "neutral",
        ), unsafe_allow_html=True)
    with c3:
        b = sent[sent["brand"] == "Betclic"]
        pos = round((b["sentiment"] == "positif").mean() * 100) if len(b) else None
        neg = int((b["sentiment"] == "negatif").sum()) if len(b) else 0
        st.markdown(kpi_card(
            "Tonalité positive Betclic", f"{pos} %" if pos is not None else "n.d.",
            f"{len(b)} articles, " + ("aucun négatif" if neg == 0 else f"dont {neg} négatif{'s' if neg > 1 else ''}"),
            "up" if neg == 0 else "down",
        ), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card(
            "Signaux prioritaires", str(n_high), f"{len(signals)} signaux au total",
            "down" if n_high else "up",
        ), unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        if sov:
            st.plotly_chart(bar_chart_brands(sov, f"Part de voix (%) · n = {n_sov} contenus",
                                             height=420), width='stretch')
            st.caption("Part de voix : part de chaque marque dans les articles de presse ivoirienne "
                       "et les vidéos YouTube retenus sur 12 mois, chaînes officielles des marques comprises.")
        else:
            st.info("Aucun article ni vidéo retenu sur la période.")
    with col_b:
        if sos:
            st.plotly_chart(bar_chart_brands(sos, "Part de recherche Google (%)", height=420), width='stretch')
            st.caption("Part de recherche : poids de chaque marque dans les recherches Google en "
                       "Côte d'Ivoire sur les 12 dernières semaines (indice relatif Google Trends).")
        else:
            st.info("Recherches Google : aucune donnée sur la dernière collecte.")

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Tonalité par marque ──
    if len(sent):
        brands = sent["brand"].value_counts().index.tolist()
        fig = go.Figure()
        for label, name, color in [("positif", "Positif", "#1D8348"), ("neutre", "Neutre", "#94A3B8"),
                                   ("negatif", "Négatif", "#C0392B")]:
            fig.add_trace(go.Bar(name=name, x=brands,
                                 y=[int(((sent["brand"] == b) & (sent["sentiment"] == label)).sum()) for b in brands],
                                 marker_color=color))
        fig.update_layout(barmode="stack", title="Tonalité des articles de presse envers chaque marque (nombre)",
                          height=400, paper_bgcolor="white", plot_bgcolor="white",
                          margin=dict(l=20, r=20, t=50, b=40), legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, width='stretch')

    # ── Lecture ──
    parts = []
    if sov:
        top = sorted(sov.items(), key=lambda x: x[1], reverse=True)[:3]
        parts.append("Présence médiatique : " + ", ".join(f"<strong>{b}</strong> ({v:.0f} %)" for b, v in top) + ".")
    if sos:
        tops = sorted(sos.items(), key=lambda x: x[1], reverse=True)[:2]
        parts.append(f"Recherches Google : <strong>{tops[0][0]}</strong> concentre {tops[0][1]:.0f} % "
                     f"de l'intérêt" + (f", devant {tops[1][0]} ({tops[1][1]:.0f} %)." if len(tops) > 1 else "."))
    parts.append(("Aucun signal prioritaire" if n_high == 0 else
                  f"<strong>{n_high}</strong> signal{'aux' if n_high > 1 else ''} prioritaire{'s' if n_high > 1 else ''}")
                 + " sur la dernière collecte (détail dans l'onglet Alertes & Signaux).")
    st.markdown(insight_box(" ".join(parts)), unsafe_allow_html=True)
