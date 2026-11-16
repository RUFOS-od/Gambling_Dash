"""AI Market Radar · Fiches concurrents (données réelles)."""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from data.collectors.base import COMPETITORS
from components.styles import section_header, styled_divider
from components.charts import brand_color
from components.radar_common import load_radar, collected_caption


def render():
    st.markdown(section_header(
        "Fiches Concurrents",
        "Détail par marque : actualités, recherches Google et vidéos YouTube en Côte d'Ivoire"
    ), unsafe_allow_html=True)

    R = load_radar()
    if R["empty"]:
        st.warning("Aucune donnée de veille. Lancez une collecte depuis le menu latéral.")
        return
    st.caption(collected_caption(R))
    news, trends, yt = R["news"], R["trends"], R["yt"]

    brand = st.selectbox("Sélectionner une marque", COMPETITORS, index=0)
    st.markdown(styled_divider(), unsafe_allow_html=True)

    n_news = int((news["brand"] == brand).sum()) if len(news) else 0
    yt_b = yt[yt["brand"] == brand] if len(yt) else yt
    t_b = trends[trends["keyword"] == brand] if len(trends) else trends
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Articles de presse (12 mois)", n_news)
    c2.metric("Vidéos YouTube (12 mois)", len(yt_b))
    c3.metric("Vues YouTube cumulées", f"{int(yt_b['views'].sum()):,}".replace(",", " ") if len(yt_b) else "0")
    c4.metric("Indice de recherche Google moyen", f"{t_b['interest'].mean():.0f}" if len(t_b) else "n.d.",
              help="Indice Google Trends sur 12 mois en Côte d'Ivoire (100 = semaine la plus recherchée "
                   "toutes marques confondues).")

    st.markdown(styled_divider(), unsafe_allow_html=True)

    if len(t_b):
        fig = go.Figure()
        comp = ["Betclic"] if brand != "Betclic" else []
        for b in [brand] + comp:
            d = trends[trends["keyword"] == b].sort_values("date")
            fig.add_trace(go.Scatter(x=d["date"], y=d["interest"], mode="lines", name=b,
                                     line=dict(color=brand_color(b), width=3 if b == brand else 2,
                                               dash="solid" if b == brand else "dot")))
        fig.update_layout(
            title=f"Recherches Google en Côte d'Ivoire · {brand}" + (" vs Betclic" if comp else "") +
                  " (12 derniers mois)",
            height=360, paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(l=20, r=20, t=50, b=40), legend=dict(orientation="h", y=-0.2),
            yaxis=dict(title="Indice (0 à 100)", gridcolor="#F0F0F0"), xaxis=dict(gridcolor="#F0F0F0"),
        )
        st.plotly_chart(fig, width='stretch')
    else:
        st.info(f"Recherches Google : volume trop faible pour {brand} en Côte d'Ivoire.")

    st.markdown(styled_divider(), unsafe_allow_html=True)

    col_n, col_v = st.columns(2)
    with col_n:
        st.markdown("**Dernières actualités**")
        nb = news[news["brand"] == brand].sort_values("published", ascending=False).head(10) if len(news) else news
        if len(nb):
            for _, row in nb.iterrows():
                d = pd.to_datetime(row["published"], errors="coerce")
                st.markdown(
                    f"- [{row['title']}]({row['link']})  \n"
                    f"  <span style='color:#7B8794;font-size:0.8rem'>{row.get('source', '')} · "
                    f"{d:%d/%m/%Y}</span>" if pd.notna(d) else f"- [{row['title']}]({row['link']})",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Aucun article de presse ivoirienne sur cette marque au cours des 12 derniers mois.")

    with col_v:
        st.markdown("**Vidéos YouTube les plus vues**")
        if len(yt_b):
            for _, row in yt_b.sort_values("views", ascending=False).head(10).iterrows():
                url = f"https://youtube.com/watch?v={row['video_id']}"
                vues = f"{int(row['views']):,}".replace(",", " ")
                st.markdown(
                    f"- [{row['title']}]({url})  \n"
                    f"  <span style='color:#7B8794;font-size:0.8rem'>{row.get('channel', '')} · {vues} vues</span>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Aucune vidéo YouTube retenue pour cette marque sur 12 mois.")
