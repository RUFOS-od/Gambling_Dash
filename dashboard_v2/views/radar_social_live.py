"""AI Market Radar · Social & Sentiment (donnees reelles)."""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from data.collectors import Storage
from data.collectors.base import COMPETITORS
from components.styles import section_header, styled_divider, insight_box
from components.llm_analyst import classify_sentiment


def render():
    st.markdown(section_header(
        "Social & Sentiment",
        "Analyse semantique des mentions : presse, tendances, classification IA"
    ), unsafe_allow_html=True)

    storage = Storage()
    news_df = storage.latest("news")
    trends_df = storage.latest("trends")

    if len(news_df) == 0:
        st.warning("Aucune actualité disponible. Lancez une collecte depuis le menu latéral.")
        return

    # ── Sentiment via LLM ──
    with st.spinner("Classification des sentiments..."):
        texts = news_df["title"].fillna("").tolist()[:150]
        sent_df = classify_sentiment(texts)
        sent_df["brand"] = news_df["brand"].values[:len(sent_df)]
        sent_df["published"] = news_df["published"].values[:len(sent_df)]
        sent_df["link"] = news_df["link"].values[:len(sent_df)]

    # Indicateur de source (analyse IA / fallback lexical)
    src = sent_df["source"].iloc[0] if len(sent_df) else "heuristic"
    if src.startswith("claude"):
        st.caption("Analyse de sentiment alimentée par IA.")
    else:
        st.caption("Analyse de sentiment via lexique français (mode dégradé).")

    # ── Distribution globale ──
    dist = sent_df["sentiment"].value_counts().to_dict()
    c1, c2, c3 = st.columns(3)
    c1.metric("Positif", dist.get("positif", 0))
    c2.metric("Neutre", dist.get("neutre", 0))
    c3.metric("Negatif", dist.get("negatif", 0))

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Sentiment empile par marque ──
    brands = sent_df["brand"].unique().tolist()
    pivot = sent_df.groupby(["brand", "sentiment"]).size().unstack(fill_value=0)
    for col in ["positif", "neutre", "negatif"]:
        if col not in pivot.columns:
            pivot[col] = 0
    pivot = pivot[["positif", "neutre", "negatif"]]
    pivot = pivot.reindex([b for b in COMPETITORS if b in pivot.index])

    fig = go.Figure()
    for col, color in [("positif", "#1D8348"), ("neutre", "#94A3B8"), ("negatif", "#C0392B")]:
        fig.add_trace(go.Bar(
            name=col.capitalize(),
            x=pivot.index, y=pivot[col],
            marker_color=color,
        ))
    fig.update_layout(
        barmode="stack", title="Sentiment par marque (news classifies)",
        height=420, paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(l=20, r=20, t=50, b=40),
    )
    st.plotly_chart(fig, width='stretch')

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Articles negatifs les plus critiques ──
    st.markdown("**Articles les plus negatifs a surveiller**")
    neg = sent_df[sent_df["sentiment"] == "negatif"].sort_values("score").head(10)
    if len(neg) > 0:
        for _, row in neg.iterrows():
            st.markdown(
                f"- **{row['brand']}** · [{row['text']}]({row['link']})  \n"
                f"  <span style='color:#7B8794;font-size:0.8rem'>score={row['score']:.2f} · {row['rationale']}</span>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("Aucun article negatif detecte dans l'echantillon.")

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Tendance Share of Search ──
    if len(trends_df) > 0:
        df_t = trends_df.copy()
        df_t["date"] = pd.to_datetime(df_t["date"])
        df_t["interest"] = pd.to_numeric(df_t["interest"], errors="coerce").fillna(0)
        pivot_t = df_t.pivot_table(index="date", columns="keyword", values="interest", aggfunc="mean").fillna(0)
        total = pivot_t.sum(axis=1).replace(0, 1)
        sos = pivot_t.divide(total, axis=0) * 100

        fig2 = go.Figure()
        for col in sos.columns:
            fig2.add_trace(go.Scatter(
                x=sos.index, y=sos[col], mode="lines", name=col, stackgroup="one",
            ))
        fig2.update_layout(
            title="Share of Search (%) · evolution hebdomadaire",
            height=400, paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(l=20, r=20, t=50, b=40),
            yaxis=dict(title="% du volume total", gridcolor="#F0F0F0"),
            xaxis=dict(gridcolor="#F0F0F0"),
        )
        st.plotly_chart(fig2, width='stretch')
