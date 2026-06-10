"""
Betclic Brand Pulse · Business Intelligence Dashboard 2026
Main application entry point with sidebar navigation and global filters.
"""

import streamlit as st
import os
import sys
import base64
from pathlib import Path

# Add project root to path
APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

# Bridge st.secrets -> os.environ so collectors/llm_analyst pick up keys
# whether running locally (via .streamlit/secrets.toml) or on Streamlit Cloud.
for _key in ("ANTHROPIC_API_KEY", "YOUTUBE_API_KEY", "META_ACCESS_TOKEN"):
    if _key not in os.environ and _key in st.secrets:
        os.environ[_key] = st.secrets[_key]

from components.styles import inject_css
from data.loader import load_raw_data, apply_filters, VAGUE_LABELS, CITIES, COMPETITORS


def _load_image_b64(path: Path) -> str:
    """Load an image file as base64 data URI."""
    suffix = path.suffix.lower()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "svg": "image/svg+xml"}
    mime_type = mime.get(suffix.lstrip("."), "image/png")
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:{mime_type};base64,{data}"

# Favicon combiné Betclic × OpinionWay (regenerable via assets/_build_favicon.py)
_favicon_path = APP_DIR / "favicon.png"
if not _favicon_path.exists():
    _favicon_path = APP_DIR / "betclic-logo.png"
_favicon = str(_favicon_path) if _favicon_path.exists() else "B"

st.set_page_config(
    page_title="Betclic Brand Pulse · BI Dashboard 2026",
    page_icon=_favicon,
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

# ── Load data ──
data = load_raw_data()

# ──────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────
with st.sidebar:
    # ── Logos ──
    logo_betclic_path = APP_DIR / "assets" / "logo_betclic.svg"
    logo_ow_path = APP_DIR / "assets" / "logo_opinionway.png"

    betclic_b64 = _load_image_b64(logo_betclic_path)
    ow_b64 = _load_image_b64(logo_ow_path)

    st.markdown(f"""
    <div class="logo-container">
        <div class="sidebar-logos">
            <img src="{betclic_b64}" alt="Betclic" class="sidebar-logo-betclic" />
            <span class="sidebar-logo-x">&times;</span>
            <img src="{ow_b64}" alt="OpinionWay" class="sidebar-logo-ow" />
        </div>
        <h1>BRAND PULSE</h1>
        <p>Business Intelligence 2026</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

    # Module selector
    module = st.radio(
        "MODULE",
        ["Brand Health Tracker", "AI Market Radar"],
        index=0,
        label_visibility="visible",
    )

    st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

    all_vagues = sorted(data["Vague"].unique().tolist())

    if module == "Brand Health Tracker":
        # ── Global filters (tracker only) ──
        st.markdown("**FILTRES GLOBAUX**")

        selected_vagues = st.multiselect(
            "Vagues", all_vagues, default=all_vagues,
            help="Sélectionnez les vagues à analyser"
        )

        selected_villes = st.multiselect(
            "Villes", CITIES, default=[],
            help="Laisser vide = toutes les villes"
        )

        all_genres = sorted(data["Genre"].unique().tolist())
        selected_genres = st.multiselect(
            "Genre", all_genres, default=[],
            help="Laisser vide = tous les genres"
        )

        # Tri naturel des tranches d'âge (18-24, 25-34, 35-44, 45+)
        _age_order = {"18 – 24 ans": 1, "25 – 34 ans": 2, "35 – 44 ans": 3, "45 ans et plus": 4}
        all_ages = sorted(
            data["Tranche_Age"].dropna().unique().tolist(),
            key=lambda x: _age_order.get(x, 99),
        )
        selected_ages = st.multiselect(
            "Tranche d'âge", all_ages, default=[],
            help="Laisser vide = toutes les tranches"
        )

        all_segments = sorted(data["Segment_Parieur"].dropna().unique().tolist())
        selected_segments = st.multiselect(
            "Segment Parieur", all_segments, default=[],
            help="Laisser vide = tous les segments"
        )

        # ── Filtre par marque utilisée ──
        all_marques = sorted(data["Marque_Principale_Utilisee"].dropna().unique().tolist())
        selected_marques = st.multiselect(
            "Marque Utilisée",
            all_marques,
            default=[],
            help="Filtrer par marque principale utilisée par les parieurs. Vide = toutes."
        )

        st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

        # ── Export Reporting ──
        st.markdown("**EXPORT REPORTING**")

        # Compute filtered data for export
        _vagues = selected_vagues if selected_vagues else all_vagues
        _df_export = apply_filters(data, _vagues,
                                   selected_villes if selected_villes else [],
                                   selected_genres if selected_genres else [],
                                   selected_segments if selected_segments else [],
                                   ages=selected_ages if selected_ages else [])
        if selected_marques:
            _df_export = _df_export[_df_export["Marque_Principale_Utilisee"].isin(selected_marques)]

        # Lazy import of export engine
        from components.export_engine import generate_pptx, generate_pdf, generate_excel

        col_e1, col_e2, col_e3 = st.columns(3)
        with col_e1:
            pptx_data = generate_pptx(_df_export, _vagues)
            st.download_button(
                "PPTX",
                pptx_data,
                "Betclic_BrandPulse_Report.pptx",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                width='stretch',
            )
        with col_e2:
            pdf_data = generate_pdf(_df_export, _vagues)
            st.download_button(
                "PDF",
                pdf_data,
                "Betclic_BrandPulse_Report.pdf",
                "application/pdf",
                width='stretch',
            )
        with col_e3:
            xlsx_data = generate_excel(_df_export, _vagues)
            st.download_button(
                "Excel",
                xlsx_data,
                "Betclic_BrandPulse_Report.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width='stretch',
            )

        st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

        # Sample info
        filtered_count = len(_df_export)
        st.caption(f"Base totale : {len(data):,} répondants")
        st.caption(f"Filtré : {filtered_count:,} répondants")
    else:
        # ── AI Market Radar : filtres et export désactivés ──
        selected_vagues = all_vagues
        selected_villes = []
        selected_genres = []
        selected_ages = []
        selected_segments = []
        selected_marques = []

        # Veille concurrentielle (collecteurs live)
        try:
            from components.sidebar_intel import render_sidebar_block
            render_sidebar_block()
        except Exception as _e:
            st.caption(f"Veille indisponible : {_e}")

        st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)
        st.caption(
            "ℹ️ Les filtres globaux Tracker ne s'appliquent pas au module AI Market Radar : "
            "la veille agrège des données externes (web, social, ads)."
        )

    st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)
    st.caption("© 2026 OpinionWay Africa × Betclic CI")

# Store filters in session state
st.session_state["selected_vagues"] = selected_vagues if selected_vagues else all_vagues
st.session_state["selected_villes"] = selected_villes if selected_villes else []
st.session_state["selected_genres"] = selected_genres if selected_genres else []
st.session_state["selected_ages"] = selected_ages if selected_ages else []
st.session_state["selected_segments"] = selected_segments if selected_segments else []
st.session_state["selected_marques"] = selected_marques if selected_marques else []
st.session_state["data"] = data

# ──────────────────────────────────────────────
# MAIN CONTENT ROUTING
# ──────────────────────────────────────────────
if module == "Brand Health Tracker":
    from views import tracker_overview, tracker_notoriete, tracker_usage, tracker_image, tracker_satisfaction, tracker_geo, tracker_pivot, banque_images

    # ── Détection OpinionWay : onglet Tableau Croisé visible uniquement
    # pour l'équipe interne (domaines email autorisés).
    OPINIONWAY_DOMAINS = ("opinion-way.com", "opinionway.com", "oway.fr")
    is_opinionway = False
    try:
        user_email = getattr(getattr(st, "user", None), "email", None) or ""
        if user_email and user_email.lower().split("@")[-1] in OPINIONWAY_DOMAINS:
            is_opinionway = True
    except Exception:
        # En local (pas d'auth Streamlit Cloud) on suppose dev OpinionWay
        is_opinionway = True

    base_tabs = [
        "Vue d'ensemble",
        "Notoriété & Visibilité",
        "Usage & Pénétration",
        "Attributs Fonctionnels",
        "Satisfaction & Fidélité",
        "Analyse Géographique",
        "Banque des Images",
    ]
    if is_opinionway:
        # On insère "Tableau Croisé" juste avant la Banque des Images
        tab_labels = base_tabs[:-1] + ["Tableau Croisé", base_tabs[-1]]
    else:
        tab_labels = base_tabs

    tabs = st.tabs(tab_labels)

    # Mapping label -> render function
    renderers = {
        "Vue d'ensemble": tracker_overview.render,
        "Notoriété & Visibilité": tracker_notoriete.render,
        "Usage & Pénétration": tracker_usage.render,
        "Attributs Fonctionnels": tracker_image.render,
        "Satisfaction & Fidélité": tracker_satisfaction.render,
        "Analyse Géographique": tracker_geo.render,
        "Tableau Croisé": tracker_pivot.render,
        "Banque des Images": banque_images.render,
    }
    for tab, label in zip(tabs, tab_labels):
        with tab:
            renderers[label]()

else:
    # Live mode : utilise les collecteurs réels (Google Trends/News, YouTube, Meta Ads)
    # avec analyse de sentiment Claude. Bascule possible via toggle ci-dessous.
    use_live = st.session_state.get("radar_live_mode", True)

    if use_live:
        from views import (
            radar_overview_live as radar_overview,
            radar_competitors_live as radar_competitors,
            radar_social_live as radar_social,
            radar_alerts_live as radar_alerts,
        )
    else:
        from views import radar_overview, radar_competitors, radar_social, radar_alerts

    tab1, tab2, tab3, tab4 = st.tabs([
        "Vue d'ensemble",
        "Fiches Concurrents",
        "Social & Sentiment",
        "Alertes & Signaux",
    ])

    with tab1:
        radar_overview.render()
    with tab2:
        radar_competitors.render()
    with tab3:
        radar_social.render()
    with tab4:
        radar_alerts.render()
