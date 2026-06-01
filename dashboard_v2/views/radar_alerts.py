"""AI Market Radar · Alertes & Signaux Faibles."""

import streamlit as st
from data.simulator import generate_alerts, generate_competitor_actions, generate_risk_levels, COMPETITORS
from components.styles import kpi_card, section_header, insight_box, styled_divider, alert_box
from components.charts import BETCLIC_RED, OPINIONWAY_PURPLE
import plotly.graph_objects as go


def render():
    st.markdown(section_header(
        "Alertes & Signaux Faibles",
        "Détection proactive des risques et opportunités du marché"
    ), unsafe_allow_html=True)

    alerts = generate_alerts()
    actions = generate_competitor_actions()
    risks = generate_risk_levels()

    # ── Alert summary ──
    high = sum(1 for a in alerts if a["severity"] == "high")
    medium = sum(1 for a in alerts if a["severity"] == "medium")
    low = sum(1 for a in alerts if a["severity"] == "low")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(kpi_card("Alertes Critiques", str(high), None, "down"), unsafe_allow_html=True)
    with col2:
        st.markdown(kpi_card("Alertes Modérées", str(medium), None, "neutral"), unsafe_allow_html=True)
    with col3:
        st.markdown(kpi_card("Signaux Faibles", str(low), None, "up"), unsafe_allow_html=True)
    with col4:
        st.markdown(kpi_card("Total Alertes", str(len(alerts)), "+2 / semaine", "neutral"), unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Alerts feed ──
    st.markdown(section_header("Fil d'Alertes Stratégiques"), unsafe_allow_html=True)

    severity_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    severity_css = {"high": "", "medium": "warning", "low": "success"}

    for alert in alerts:
        icon = severity_icons.get(alert["severity"], "⚪")
        css = severity_css.get(alert["severity"], "")
        st.markdown(f"""
        <div class="alert-box {css}">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
                <strong>{icon} {alert['title']}</strong>
                <span style="color:#8899A6;font-size:0.8rem;">{alert['date']} | {alert['category']}</span>
            </div>
            {alert['detail']}
        </div>
        """, unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Timeline of competitor actions ──
    st.markdown(section_header("Timeline des Actions Concurrentes (Mars 2026)"), unsafe_allow_html=True)

    # Flatten all actions
    all_actions = []
    for brand, brand_actions in actions.items():
        if brand == "Betclic":
            continue
        for action in brand_actions:
            all_actions.append({**action, "brand": brand})

    all_actions.sort(key=lambda x: x["date"], reverse=True)

    # Display as timeline
    fig = go.Figure()

    impact_colors = {"Fort": "#E74C3C", "Moyen": "#F39C12", "Faible": "#27AE60"}
    impact_sizes = {"Fort": 16, "Moyen": 12, "Faible": 8}

    brands_seen = set()
    for action in all_actions:
        show_legend = action["brand"] not in brands_seen
        brands_seen.add(action["brand"])

        fig.add_trace(go.Scatter(
            x=[action["date"]],
            y=[action["brand"]],
            mode="markers",
            marker=dict(
                size=impact_sizes.get(action["impact"], 10),
                color=impact_colors.get(action["impact"], "#4A5568"),
                symbol="diamond",
                line=dict(width=1, color="#1A1D23"),
            ),
            text=[f"{action['type']}: {action['detail'][:60]}..."],
            hoverinfo="text+x",
            showlegend=False,
            name=action["brand"],
        ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#1A1D23", size=12),
        margin=dict(l=40, r=40, t=30, b=40), height=350,
        xaxis=dict(gridcolor="rgba(0,0,0,0.06)", title="Date"),
        yaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
    )
    st.plotly_chart(fig, width='stretch')

    # Legend
    st.markdown("""
    <div style="display:flex;gap:2rem;justify-content:center;margin:0.5rem 0 1rem 0;">
        <span>🔴 Impact Fort</span>
        <span>🟡 Impact Moyen</span>
        <span>🟢 Impact Faible</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Recommendations ──
    st.markdown(section_header("Recommandations Stratégiques"), unsafe_allow_html=True)

    recommendations = [
        {
            "priority": "Haute",
            "title": "Contrer la surenchère promotionnelle 1XBET",
            "action": "Activer une campagne CRM ciblée sur les parieurs occasionnels avec offre de fidélisation (pas de surenchère bonus). Focus sur la valeur ajoutée app + jeu responsable.",
            "timeline": "Immédiat",
        },
        {
            "priority": "Haute",
            "title": "Répondre à la campagne TV Sportcash",
            "action": "Amplifier la visibilité Willy Dumbo sur les réseaux sociaux pendant les matchs CAN. Budget digital > TV pour un meilleur ROI.",
            "timeline": "Sous 48h",
        },
        {
            "priority": "Moyenne",
            "title": "Investir le territoire e-sport",
            "action": "Le signal faible e-sport est une opportunité de first-mover. Proposer un partenariat avec un événement e-sport local pour tester l'appétence.",
            "timeline": "Q2 2026",
        },
        {
            "priority": "Moyenne",
            "title": "Renforcer la communication sur les délais de retrait",
            "action": "Le marché souffre d'une perception négative sur les retraits. Betclic peut se différencier en communiquant proactivement sur ses SLA de paiement.",
            "timeline": "Mars-Avril 2026",
        },
        {
            "priority": "Basse",
            "title": "Surveiller les nouveaux entrants potentiels",
            "action": "Mettre en place une veille LONACI pour détecter les nouvelles demandes de licence. Préparer un dossier de défense si nécessaire.",
            "timeline": "Continu",
        },
    ]

    for reco in recommendations:
        priority_color = {"Haute": "", "Moyenne": "warning", "Basse": "success"}
        css = priority_color.get(reco["priority"], "")
        st.markdown(f"""
        <div class="alert-box {css}">
            <div style="display:flex;justify-content:space-between;margin-bottom:0.5rem;">
                <strong>{'🔴' if reco['priority'] == 'Haute' else '🟡' if reco['priority'] == 'Moyenne' else '🟢'} {reco['title']}</strong>
                <span style="color:#8899A6;font-size:0.8rem;">Priorité: {reco['priority']} | {reco['timeline']}</span>
            </div>
            {reco['action']}
        </div>
        """, unsafe_allow_html=True)
