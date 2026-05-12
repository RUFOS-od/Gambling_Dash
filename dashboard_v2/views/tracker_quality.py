"""Brand Health Tracker — Qualite des Donnees (data quality report par vague)."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.loader import detect_available_waves, load_waves_individually
from data.validation import validate_all_waves, compare_waves_consistency
from components.styles import section_header, insight_box, alert_box, styled_divider
from components.charts import BETCLIC_RED, OPINIONWAY_PURPLE, SLATE


def _status_badge(ok: bool, n_errors: int, n_warnings: int) -> str:
    """Generate a status badge HTML."""
    if ok and n_warnings == 0:
        return '<span class="quality-badge quality-ok">VALIDE</span>'
    elif ok:
        return '<span class="quality-badge quality-warn">VALIDE AVEC ALERTES</span>'
    else:
        return '<span class="quality-badge quality-ko">ERREURS</span>'


QUALITY_CSS = """
<style>
.quality-card {
    background: #FFFFFF;
    border: 1px solid #E2E4E8;
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.04);
}
.quality-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.quality-ok {
    background: rgba(29, 131, 72, 0.1);
    color: #1D8348;
    border: 1px solid rgba(29, 131, 72, 0.3);
}
.quality-warn {
    background: rgba(212, 118, 10, 0.1);
    color: #D4760A;
    border: 1px solid rgba(212, 118, 10, 0.3);
}
.quality-ko {
    background: rgba(192, 57, 43, 0.1);
    color: #C0392B;
    border: 1px solid rgba(192, 57, 43, 0.3);
}
.quality-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.8rem;
}
.quality-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: #1A1D23;
}
.quality-stat {
    display: inline-block;
    margin-right: 1.5rem;
    color: #4A5568;
    font-size: 0.88rem;
}
.quality-stat strong {
    color: #1A1D23;
    font-weight: 700;
}
.quality-error {
    background: rgba(192, 57, 43, 0.05);
    border-left: 3px solid #C0392B;
    padding: 0.5rem 0.8rem;
    margin: 0.3rem 0;
    font-size: 0.85rem;
    color: #1A1D23;
    border-radius: 0 6px 6px 0;
}
.quality-warning {
    background: rgba(212, 118, 10, 0.05);
    border-left: 3px solid #D4760A;
    padding: 0.5rem 0.8rem;
    margin: 0.3rem 0;
    font-size: 0.85rem;
    color: #1A1D23;
    border-radius: 0 6px 6px 0;
}
</style>
"""


def render():
    st.markdown(QUALITY_CSS, unsafe_allow_html=True)
    st.markdown(section_header(
        "Qualite des Donnees",
        "Rapport de validation automatique des bases recues par vague"
    ), unsafe_allow_html=True)

    # Detect waves
    wave_files = detect_available_waves()

    if not wave_files:
        st.warning("Aucun fichier de vague detecte dans le dossier racine.")
        st.info(
            "**Nommage attendu :** `Bases_Betclic_BrandPulse_Tracker_V1.xlsx`, "
            "`Bases_Betclic_BrandPulse_Tracker_V2.xlsx`, etc."
        )
        return

    # Summary header
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="quality-card">
            <div style="color:#4A5568;font-size:0.75rem;text-transform:uppercase;font-weight:700;letter-spacing:0.05em;">Vagues detectees</div>
            <div style="font-size:2rem;font-weight:800;color:{BETCLIC_RED};line-height:1;margin-top:0.3rem;">{len(wave_files)}</div>
        </div>
        """, unsafe_allow_html=True)

    # Load all waves individually
    waves_data = load_waves_individually()

    with c2:
        total_rows = sum(len(df) for df in waves_data.values())
        st.markdown(f"""
        <div class="quality-card">
            <div style="color:#4A5568;font-size:0.75rem;text-transform:uppercase;font-weight:700;letter-spacing:0.05em;">Interviews totales</div>
            <div style="font-size:2rem;font-weight:800;color:{OPINIONWAY_PURPLE};line-height:1;margin-top:0.3rem;">{total_rows:,}</div>
        </div>
        """, unsafe_allow_html=True)

    # Validation
    reports = validate_all_waves(waves_data)
    n_ok = sum(1 for r in reports if r["ok"] and len(r["warnings"]) == 0)
    n_warn = sum(1 for r in reports if r["ok"] and len(r["warnings"]) > 0)
    n_ko = sum(1 for r in reports if not r["ok"])

    with c3:
        st.markdown(f"""
        <div class="quality-card">
            <div style="color:#4A5568;font-size:0.75rem;text-transform:uppercase;font-weight:700;letter-spacing:0.05em;">Vagues valides</div>
            <div style="font-size:2rem;font-weight:800;color:#1D8348;line-height:1;margin-top:0.3rem;">{n_ok + n_warn} / {len(reports)}</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        avg_fill = round(sum(r["stats"].get("fill_rate", 0) for r in reports) / max(len(reports), 1), 1)
        st.markdown(f"""
        <div class="quality-card">
            <div style="color:#4A5568;font-size:0.75rem;text-transform:uppercase;font-weight:700;letter-spacing:0.05em;">Taux remplissage moyen</div>
            <div style="font-size:2rem;font-weight:800;color:{SLATE};line-height:1;margin-top:0.3rem;">{avg_fill}%</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

    # Coherence inter-vagues
    if len(waves_data) >= 2:
        st.markdown("### Coherence inter-vagues")
        consistency = compare_waves_consistency(waves_data)

        if not consistency["issues"]:
            st.markdown(alert_box(
                "Aucune rupture de protocole detectee entre les vagues. Toutes les modalites sont coherentes.",
                "success"
            ), unsafe_allow_html=True)
        else:
            new_modalities = [i for i in consistency["issues"] if i["type"] == "new_modality"]
            removed = [i for i in consistency["issues"] if i["type"] == "removed_modality"]
            size_dev = [i for i in consistency["issues"] if i["type"] == "size_deviation"]

            if new_modalities:
                for nm in new_modalities:
                    st.markdown(
                        f'<div class="quality-warning">'
                        f'<strong>{nm["wave"]}</strong> — Nouvelle(s) modalite(s) dans <code>{nm["column"]}</code> : '
                        f'{", ".join(str(v) for v in nm["values"])}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            if removed:
                for rm in removed:
                    st.markdown(
                        f'<div class="quality-warning">'
                        f'<strong>{rm["wave"]}</strong> — Modalite(s) disparue(s) de <code>{rm["column"]}</code> : '
                        f'{", ".join(str(v) for v in rm["values"])}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            if size_dev:
                for sd in size_dev:
                    st.markdown(
                        f'<div class="quality-warning">'
                        f'<strong>{sd["wave"]}</strong> — Taille echantillon : {sd["size"]} '
                        f'(reference : {sd["reference_size"]}, ecart : {sd["deviation_pct"]}%)'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        # Evolution taille echantillon
        sizes = consistency["sample_sizes"]
        if sizes:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=list(sizes.keys()),
                y=list(sizes.values()),
                marker_color=[BETCLIC_RED if v >= 950 else "#D4760A" for v in sizes.values()],
                text=[f"n={v}" for v in sizes.values()],
                textposition="outside",
            ))
            fig.update_layout(
                title="Taille d'echantillon par vague",
                height=320,
                margin=dict(l=20, r=20, t=50, b=40),
                paper_bgcolor="white",
                plot_bgcolor="white",
                yaxis=dict(title="Interviews (n)", gridcolor="#F0F0F0"),
                showlegend=False,
            )
            st.plotly_chart(fig, width='stretch')

        st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

    # Rapport par vague
    st.markdown("### Rapport detaille par vague")

    for report, wave_info in zip(reports, wave_files):
        stats = report["stats"]
        wave_name = stats["wave"]
        ok = report["ok"]
        n_err = len(report["errors"])
        n_warn = len(report["warnings"])

        badge = _status_badge(ok, n_err, n_warn)

        with st.expander(f"{wave_name} — {wave_info['filename']} ({wave_info['size_kb']} Ko)", expanded=(not ok or n_warn > 0)):
            st.markdown(f"""
            <div class="quality-header">
                <div class="quality-title">Statut</div>
                <div>{badge}</div>
            </div>
            <div>
                <span class="quality-stat"><strong>{stats['n_rows']:,}</strong> repondants</span>
                <span class="quality-stat"><strong>{stats['n_cols']}</strong> variables</span>
                <span class="quality-stat">Remplissage : <strong>{stats.get('fill_rate', 0)}%</strong></span>
                <span class="quality-stat">Doublons ID : <strong>{stats.get('duplicates', 0)}</strong></span>
            </div>
            """, unsafe_allow_html=True)

            if report["errors"]:
                st.markdown("**Erreurs bloquantes :**")
                for err in report["errors"]:
                    st.markdown(f'<div class="quality-error">{err}</div>', unsafe_allow_html=True)

            if report["warnings"]:
                st.markdown("**Alertes :**")
                for w in report["warnings"]:
                    st.markdown(f'<div class="quality-warning">{w}</div>', unsafe_allow_html=True)

            # Distributions
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if stats.get("city_distribution"):
                    st.markdown("**Distribution par ville**")
                    df_c = pd.DataFrame(list(stats["city_distribution"].items()), columns=["Ville", "n"])
                    df_c = df_c.sort_values("n", ascending=False)
                    st.dataframe(df_c, hide_index=True, width='stretch', height=250)
            with col_b:
                if stats.get("age_distribution"):
                    st.markdown("**Distribution par age**")
                    df_a = pd.DataFrame(list(stats["age_distribution"].items()), columns=["Tranche", "n"])
                    st.dataframe(df_a, hide_index=True, width='stretch', height=250)
            with col_c:
                if stats.get("key_missing_rates"):
                    st.markdown("**Taux de non-reponse (variables cles)**")
                    df_m = pd.DataFrame(
                        [(k.replace("_", " "), f"{v}%") for k, v in stats["key_missing_rates"].items()],
                        columns=["Variable", "NR"]
                    )
                    st.dataframe(df_m, hide_index=True, width='stretch', height=250)

    st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)
    st.caption(
        "Chaque nouvelle vague deposee dans le dossier racine est automatiquement detectee et validee. "
        "Nommage attendu : `Bases_Betclic_BrandPulse_Tracker_V{N}.xlsx`."
    )
