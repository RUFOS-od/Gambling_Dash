"""AI Market Radar · Presse, tonalité et recherches (données réelles)."""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from components.styles import section_header, styled_divider, insight_box
from components.charts import brand_color
from components.radar_common import load_radar, collected_caption, news_sentiment


def render():
    st.markdown(section_header(
        "Social & Sentiment",
        "Tonalité de la presse ivoirienne envers chaque marque et évolution des recherches Google"
    ), unsafe_allow_html=True)

    R = load_radar()
    if R["empty"]:
        st.warning("Aucune donnée de veille. Lancez une collecte depuis le menu latéral.")
        return
    st.caption(collected_caption(R))
    news, trends = R["news"], R["trends"]

    if len(news):
        with st.spinner("Analyse de la tonalité des articles..."):
            sent = news_sentiment(news)
        st.caption("Tonalité évaluée par IA, titre par titre, envers la marque citée."
                   if sent.attrs.get("ai") else "Tonalité évaluée par analyse lexicale (IA indisponible).")

        dist = sent["sentiment"].value_counts()
        c1, c2, c3 = st.columns(3)
        c1.metric("Articles positifs", int(dist.get("positif", 0)))
        c2.metric("Articles neutres", int(dist.get("neutre", 0)))
        c3.metric("Articles négatifs", int(dist.get("negatif", 0)))

        st.markdown(styled_divider(), unsafe_allow_html=True)

        # ── Détail par marque (%) ──
        brands = sent["brand"].value_counts().index.tolist()
        fig = go.Figure()
        for label, name, color in [("positif", "Positif", "#1D8348"), ("neutre", "Neutre", "#94A3B8"),
                                   ("negatif", "Négatif", "#C0392B")]:
            vals = [((sent["brand"] == b) & (sent["sentiment"] == label)).sum() / (sent["brand"] == b).sum() * 100
                    for b in brands]
            fig.add_trace(go.Bar(name=name, x=[f"{b} (n={int((sent['brand'] == b).sum())})" for b in brands],
                                 y=vals, marker_color=color,
                                 text=[f"{v:.0f} %" if v >= 8 else "" for v in vals], textposition="inside"))
        fig.update_layout(barmode="stack", title="Tonalité des articles par marque (%)",
                          height=420, paper_bgcolor="white", plot_bgcolor="white",
                          margin=dict(l=20, r=20, t=50, b=40), yaxis=dict(range=[0, 100], ticksuffix=" %"),
                          legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width='stretch')

        st.markdown("**Articles à tonalité négative**")
        neg = sent[sent["sentiment"] == "negatif"].sort_values("score")
        if len(neg):
            for _, row in neg.head(10).iterrows():
                st.markdown(
                    f"- **{row['brand']}** · [{row['title']}]({row['link']})  \n"
                    f"  <span style='color:#7B8794;font-size:0.8rem'>{row['source']} · {row['rationale']}</span>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Aucun article à tonalité négative parmi les articles retenus.")
    else:
        st.info("Aucun article de presse ivoirienne retenu sur 12 mois.")

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Recherches Google : principales marques ──
    if len(trends):
        top = trends.groupby("keyword")["interest"].mean().sort_values(ascending=False)
        top = [b for b in top.index if top[b] >= 1][:6]
        fig2 = go.Figure()
        for b in top:
            d = trends[trends["keyword"] == b].sort_values("date")
            fig2.add_trace(go.Scatter(x=d["date"], y=d["interest"], mode="lines", name=b,
                                      line=dict(color=brand_color(b), width=3 if b == "Betclic" else 2)))
        fig2.update_layout(
            title="Recherches Google en Côte d'Ivoire · principales marques (indice hebdomadaire)",
            height=420, paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(l=20, r=20, t=50, b=40), legend=dict(orientation="h", y=-0.2),
            yaxis=dict(title="Indice (0 à 100)", gridcolor="#F0F0F0"), xaxis=dict(gridcolor="#F0F0F0"),
        )
        st.plotly_chart(fig2, width='stretch')
        st.caption("Indice Google Trends : 100 = semaine la plus recherchée, toutes marques confondues. "
                   "Les marques à volume trop faible ne sont pas affichées.")
        if len(top) >= 2:
            m = trends.groupby("keyword")["interest"].mean()
            st.markdown(insight_box(
                f"Sur 12 mois, <strong>{top[0]}</strong> est la marque la plus recherchée sur Google en "
                f"Côte d'Ivoire (indice moyen {m[top[0]]:.0f}), devant <strong>{top[1]}</strong> "
                f"({m[top[1]]:.0f})."), unsafe_allow_html=True)
