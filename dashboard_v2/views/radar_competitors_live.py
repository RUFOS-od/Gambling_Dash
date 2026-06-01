"""AI Market Radar · Fiches concurrents (donnees reelles)."""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from data.collectors import Storage
from data.collectors.base import COMPETITORS
from components.styles import section_header, styled_divider
from components.charts import BETCLIC_RED, OPINIONWAY_PURPLE, SLATE


def render():
    st.markdown(section_header(
        "Fiches Concurrents",
        "Détail par marque : actualités, tendances de recherche, publicités et présence vidéo"
    ), unsafe_allow_html=True)

    storage = Storage()
    news_df = storage.latest("news")
    trends_df = storage.latest("trends")
    ads_df = storage.latest("ads")
    yt_df = storage.latest("youtube_videos")

    brand = st.selectbox("Selectionner un concurrent", COMPETITORS, index=0)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Stats de base ──
    n_news = len(news_df[news_df["brand"] == brand]) if len(news_df) else 0
    n_ads = len(ads_df[ads_df["brand"] == brand]) if len(ads_df) else 0
    n_yt = len(yt_df[yt_df["brand"] == brand]) if len(yt_df) else 0
    yt_views = int(yt_df[yt_df["brand"] == brand]["views"].sum()) if len(yt_df) else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Articles de presse", n_news)
    c2.metric("Publicites Meta actives", n_ads)
    c3.metric("Videos YouTube", n_yt)
    c4.metric("Vues YouTube cumulees", f"{yt_views:,}")

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Tendance Google sur 12 mois ──
    if len(trends_df) > 0 and brand in trends_df["keyword"].unique():
        df_b = trends_df[trends_df["keyword"] == brand].copy()
        df_b["date"] = pd.to_datetime(df_b["date"])
        df_b = df_b.sort_values("date")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_b["date"], y=df_b["interest"],
            mode="lines+markers",
            line=dict(color=BETCLIC_RED if brand == "Betclic" else OPINIONWAY_PURPLE, width=3),
            marker=dict(size=6),
            name=brand,
        ))
        fig.update_layout(
            title=f"Interet Google pour {brand} (12 derniers mois, Cote d'Ivoire)",
            height=360, paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(l=20, r=20, t=50, b=40),
            yaxis=dict(title="Interet (0-100)", gridcolor="#F0F0F0"),
            xaxis=dict(gridcolor="#F0F0F0"),
        )
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("Aucune donnee Google Trends pour cette marque.")

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Dernieres news ──
    col_n, col_v = st.columns(2)
    with col_n:
        st.markdown("**Dernieres actualites**")
        if len(news_df) > 0:
            news_b = news_df[news_df["brand"] == brand].head(10)
            if len(news_b) > 0:
                for _, row in news_b.iterrows():
                    st.markdown(
                        f"- [{row['title']}]({row['link']})  \n"
                        f"  <span style='color:#7B8794;font-size:0.8rem'>{row.get('source','')} · {row.get('published','')[:10]}</span>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("Aucune actualite pour cette marque.")
        else:
            st.caption("Base de news vide.")

    with col_v:
        st.markdown("**Videos YouTube les plus vues**")
        if len(yt_df) > 0:
            yt_b = yt_df[yt_df["brand"] == brand].sort_values("views", ascending=False).head(10)
            if len(yt_b) > 0:
                for _, row in yt_b.iterrows():
                    url = f"https://youtube.com/watch?v={row['video_id']}"
                    st.markdown(
                        f"- [{row['title']}]({url})  \n"
                        f"  <span style='color:#7B8794;font-size:0.8rem'>{row.get('channel','')} · {int(row.get('views',0)):,} vues</span>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("Aucune video pour cette marque.")
        else:
            st.caption("Veille vidéo : aucune donnée disponible pour le moment.")
