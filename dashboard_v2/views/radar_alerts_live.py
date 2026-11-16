"""AI Market Radar · Alertes & Signaux (données réelles + brief exécutif IA)."""

import pandas as pd
import streamlit as st

from components.styles import section_header, styled_divider, alert_box
from components.llm_analyst import detect_weak_signals, build_executive_brief
from components.radar_common import load_radar, collected_caption, news_sentiment, tracker_kpis


SEVERITY_STYLES = {
    "high":   ("#C0392B", "PRIORITAIRE"),
    "medium": ("#D4760A", "À SUIVRE"),
    "low":    ("#1D8348", "INFORMATION"),
    "info":   ("#4A5568", "INFORMATION"),
}


def _signal_card(s: dict) -> str:
    color, label = SEVERITY_STYLES.get(s["severity"], ("#4A5568", "INFORMATION"))
    brand_txt = f" · <strong>{s['brand']}</strong>" if s.get("brand") else ""
    msg = s["message"]
    if s.get("link"):
        msg = f'<a href="{s["link"]}" target="_blank" style="color:#1A1D23;">{msg}</a>'
    return (
        f'<div style="background:#FFFFFF;border-left:4px solid {color};'
        f'padding:0.8rem 1rem;margin-bottom:0.6rem;border-radius:0 8px 8px 0;'
        f'box-shadow:0 2px 6px rgba(0,0,0,0.04);">'
        f'<span style="color:{color};font-weight:700;letter-spacing:0.05em;">{label}{brand_txt}</span>'
        f'<div style="margin-top:0.3rem;color:#1A1D23;">{msg}</div>'
        f'<div style="margin-top:0.2rem;color:#4A5568;font-size:0.82rem;">{s.get("evidence", "")}</div>'
        f'</div>'
    )


def render():
    st.markdown(section_header(
        "Alertes & Signaux Faibles",
        "Détection automatique : réglementation (ARJH, LONACI), réputation, jeu responsable, "
        "activité marketing et pics de recherche, puis brief exécutif IA"
    ), unsafe_allow_html=True)

    R = load_radar()
    if R["empty"]:
        st.warning("Aucune donnée de veille. Lancez une collecte depuis le menu latéral.")
        return
    st.caption(collected_caption(R))
    news, trends = R["news"], R["trends"]

    signals = detect_weak_signals(news_df=news, trends_df=trends)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total signaux", len(signals))
    c2.metric("Prioritaires", sum(1 for s in signals if s["severity"] == "high"))
    c3.metric("À suivre", sum(1 for s in signals if s["severity"] == "medium"))
    c4.metric("Information", sum(1 for s in signals if s["severity"] in ("low", "info")))

    st.markdown(styled_divider(), unsafe_allow_html=True)

    st.markdown("### Signaux détectés")
    if signals:
        for s in signals[:30]:
            st.markdown(_signal_card(s), unsafe_allow_html=True)
    else:
        st.markdown(alert_box("Aucun signal détecté sur la dernière collecte.", "success"),
                    unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    st.markdown("### Brief exécutif · Analyse IA")
    with st.spinner("Rédaction du brief..."):
        sent = news_sentiment(news)
        sent_summary = {b: sent[sent["brand"] == b]["sentiment"].value_counts().to_dict()
                        for b in sent["brand"].unique()} if len(sent) else {}
        trends_snapshot = pd.DataFrame()
        if len(trends):
            trends_snapshot = trends.groupby("keyword")["interest"].agg(["mean", "max"]).round(1).reset_index()
            trends_snapshot.columns = ["marque", "indice_moyen", "indice_max"]
            trends_snapshot = trends_snapshot.sort_values("indice_moyen", ascending=False)
        recent = news.sort_values("published", ascending=False) if len(news) else news
        brief = build_executive_brief({
            "news_count_by_brand": news["brand"].value_counts().to_dict() if len(news) else {},
            "sentiment_summary": sent_summary,
            "signals": signals,
            "trends_snapshot": trends_snapshot,
            "news_titles": [f"{r['brand']} · {str(r['published'])[:10]} · {r['title']}"
                            for _, r in recent.head(40).iterrows()],
            "tracker_kpis": tracker_kpis(),
        })

    if brief.get("source", "").startswith("claude"):
        st.caption("Brief rédigé par IA à partir des seules données de la veille et du baromètre.")
    else:
        st.caption("Brief établi par règles automatiques (IA indisponible).")

    st.markdown(f"**Résumé.** {brief.get('summary', '')}")
    col_i, col_t = st.columns(2)
    with col_i:
        st.markdown("**Points clés**")
        for it in brief.get("key_insights", []):
            st.markdown(f"- {it}")
    with col_t:
        st.markdown("**Menaces**")
        for it in brief.get("threats", []) or ["Aucune menace identifiée sur la période."]:
            st.markdown(f"- {it}")
    col_o, col_r = st.columns(2)
    with col_o:
        st.markdown("**Opportunités**")
        for it in brief.get("opportunities", []) or ["Aucune opportunité nette identifiée sur la période."]:
            st.markdown(f"- {it}")
    with col_r:
        st.markdown("**Recommandations**")
        for it in brief.get("recommendations", []):
            st.markdown(f"- {it}")
