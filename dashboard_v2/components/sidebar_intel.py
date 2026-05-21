"""
Bloc sidebar "Veille concurrentielle" : bouton Refresh + statut des collecteurs.
A appeler dans la sidebar de app.py (cote module AI Market Radar).
"""

from datetime import datetime
import streamlit as st

from data.collectors import run_all, get_status, Storage


BADGE_CSS = """
<style>
.intel-status-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 4px 0; font-size: 0.82rem; color: #4A5568;
}
.intel-badge {
    display: inline-block; padding: 2px 10px; border-radius: 10px;
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.04em;
}
.intel-ok { background: rgba(29,131,72,0.12); color: #1D8348; }
.intel-warn { background: rgba(212,118,10,0.12); color: #D4760A; }
.intel-ko { background: rgba(192,57,43,0.12); color: #C0392B; }
.intel-na { background: rgba(74,85,104,0.12); color: #4A5568; }
</style>
"""


def _fmt_age(minutes):
    if minutes is None:
        return "jamais"
    if minutes < 60:
        return f"il y a {int(minutes)} min"
    if minutes < 60 * 24:
        return f"il y a {int(minutes/60)} h"
    return f"il y a {int(minutes/60/24)} j"


def render_sidebar_block():
    """Injecte le bouton Refresh et le tableau de statut dans la sidebar."""
    st.markdown(BADGE_CSS, unsafe_allow_html=True)
    st.markdown("**VEILLE CONCURRENTIELLE**")

    storage = Storage()
    status = get_status(storage)

    # ── Bouton principal ──
    if st.button("Rafraîchir la veille", width='stretch', key="refresh_intel"):
        with st.spinner("Collecte en cours sur toutes les sources..."):
            results = run_all(storage=storage)
        st.session_state["last_intel_run"] = {
            "at": datetime.now().isoformat(),
            "results": [r.to_dict() for r in results],
        }
        st.rerun()

    # ── Etat des collecteurs ──
    labels = {
        "google_trends": "Google Trends",
        "google_news": "Google News",
        "meta_ads": "Meta Ads",
        "youtube": "YouTube",
    }
    for key, lbl in labels.items():
        info = status.get(key, {})
        last = info.get("last_run_info")
        age = info.get("age_minutes")
        available = info.get("available", True)

        if not available:
            badge_cls, badge_txt = "intel-na", "EN ATTENTE"
        elif last is None:
            badge_cls, badge_txt = "intel-na", "À LANCER"
        elif last.get("ok"):
            # Fraicheur : < 24h vert, < 7j orange, sinon rouge
            if age is None or age > 60 * 24 * 7:
                badge_cls, badge_txt = "intel-ko", "OBSOLÈTE"
            elif age > 60 * 24:
                badge_cls, badge_txt = "intel-warn", "ANCIEN"
            else:
                badge_cls, badge_txt = "intel-ok", "À JOUR"
        else:
            badge_cls, badge_txt = "intel-ko", "ÉCHEC"

        st.markdown(
            f'<div class="intel-status-row">'
            f'<span>{lbl}<br><span style="font-size:0.72rem;color:#7B8794">{_fmt_age(age)}</span></span>'
            f'<span class="intel-badge {badge_cls}">{badge_txt}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Afficher le detail du dernier run si present
    last = st.session_state.get("last_intel_run")
    if last:
        n_ok = sum(1 for r in last["results"] if r["ok"])
        n_total = len(last["results"])
        n_rows = sum(r["n_rows"] for r in last["results"])
        st.caption(f"Dernière collecte : {n_ok}/{n_total} sources, {n_rows} signaux récoltés")
