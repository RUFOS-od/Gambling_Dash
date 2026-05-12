"""Brand Health Tracker — Tableau Croisé Dynamique (Pivot)."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from data.loader import apply_filters, COMPETITORS, IMAGE_ATTRIBUTES
from components.styles import section_header, insight_box, styled_divider
from components.charts import BETCLIC_RED, OPINIONWAY_PURPLE, SLATE, TEXT_MUTED

# ── Column categories for user selection ──
DIMENSION_COLS = {
    "Vague": "Vague",
    "Ville": "Ville",
    "Genre": "Genre",
    "Tranche d'âge": "Tranche_Age",
    "Type de répondant": "Type_Repondant",
    "Segment parieur": "Segment_Parieur",
    "Marque principale utilisée": "Marque_Principale_Utilisee",
    "TOM (marque citée)": "TOM_Marque_Citee",
    "Canal de découverte": "Canal_Decouverte",
    "Sport préféré": "Sport_Prefere",
    "Type de pari préféré": "Type_Pari_Prefere",
    "Moyen de paiement": "Moyen_Paiement_Principal",
    "Catégorie NPS": "NPS_Categorie",
    "Risque de churn": "Risque_Churn",
    "Principal irritant": "Principal_Irritant",
    "Intention réutilisation": "Intention_Reutilisation",
    "Ambassadeur rappelé": "Ambassadeur_Rappele",
}

MEASURE_COLS = {
    "Nombre de répondants": {"col": None, "agg": "count"},
    "Notoriété Totale Betclic (%)": {"col": "Notoriete_Totale_Betclic", "agg": "pct"},
    "Utilise Betclic (%)": {"col": "Utilise_Betclic", "agg": "pct"},
    "Considération Betclic (%)": {"col": "Consideration_Betclic", "agg": "pct"},
    "Préférence Betclic (%)": {"col": "Preference_Betclic", "agg": "pct"},
    "Multi-Application (%)": {"col": "Multi_Application", "agg": "pct"},
    "Rappel Campagne (%)": {"col": "Rappel_Campagne_Betclic", "agg": "pct"},
    "Wallet Share moyen (%)": {"col": "Part_Portefeuille_Betclic", "agg": "mean_pct"},
    "Satisfaction moyenne (/5)": {"col": "Satisfaction_Globale_Betclic", "agg": "mean"},
    "NPS Score": {"col": "NPS_Score", "agg": "mean"},
    "Fréquence paris/mois": {"col": "Frequence_Paris_Mois", "agg": "mean"},
    "Nb apps utilisées": {"col": "Nb_Apps_Utilisees", "agg": "mean"},
    "Image — Modernité (/5)": {"col": "Image_Modernite", "agg": "mean"},
    "Image — Fiabilité (/5)": {"col": "Image_Fiabilite", "agg": "mean"},
    "Image — Sécurité (/5)": {"col": "Image_Securite", "agg": "mean"},
    "Image — Rapidité Paiements (/5)": {"col": "Image_Rapidite_Paiements", "agg": "mean"},
    "Image — Proximité (/5)": {"col": "Image_Proximite", "agg": "mean"},
    "Image — Innovation (/5)": {"col": "Image_Innovation", "agg": "mean"},
    "Image — Qualité App (/5)": {"col": "Image_Qualite_App", "agg": "mean"},
    "Image — Simplicité (/5)": {"col": "Image_Simplicite", "agg": "mean"},
}

# Notoriete for all brands
for brand in COMPETITORS:
    MEASURE_COLS[f"Notoriété Totale {brand} (%)"] = {
        "col": f"Notoriete_Totale_{brand}",
        "agg": "pct",
    }


def _compute_pivot(df, row_dim, col_dim, measure_name):
    """Compute a pivot table from the raw data."""
    measure = MEASURE_COLS[measure_name]
    col_name = measure["col"]
    agg_type = measure["agg"]

    row_col = DIMENSION_COLS[row_dim]
    has_col_dim = col_dim != "(aucune)"
    cross_col = DIMENSION_COLS.get(col_dim) if has_col_dim else None

    groups = [row_col]
    if has_col_dim:
        groups.append(cross_col)

    if agg_type == "count":
        result = df.groupby(groups).size().reset_index(name="Valeur")
    elif agg_type == "pct":
        result = df.groupby(groups)[col_name].mean().reset_index(name="Valeur")
        result["Valeur"] = (result["Valeur"] * 100).round(1)
    elif agg_type == "mean_pct":
        result = df.groupby(groups)[col_name].mean().reset_index(name="Valeur")
        result["Valeur"] = (result["Valeur"] * 100).round(1)
    elif agg_type == "mean":
        result = df.groupby(groups)[col_name].mean().reset_index(name="Valeur")
        result["Valeur"] = result["Valeur"].round(2)

    if has_col_dim:
        pivot = result.pivot_table(
            index=row_col, columns=cross_col, values="Valeur", aggfunc="first"
        )
    else:
        pivot = result.set_index(row_col)[["Valeur"]]

    # Add base sizes
    base_sizes = df.groupby(row_col).size()
    pivot.insert(0, "Base (n)", base_sizes)

    return pivot


def _make_heatmap(pivot_df, measure_name):
    """Create a Plotly heatmap from the pivot table."""
    # Exclude the Base column for the heatmap
    display_df = pivot_df.drop(columns=["Base (n)"], errors="ignore")

    if display_df.empty or display_df.shape[1] == 0:
        return None

    fig = go.Figure(data=go.Heatmap(
        z=display_df.values,
        x=[str(c) for c in display_df.columns],
        y=[str(r) for r in display_df.index],
        colorscale=[
            [0.0, "#F8F0FC"],
            [0.25, "#E8D5F0"],
            [0.5, "#D4A9E6"],
            [0.75, "#C0392B"],
            [1.0, "#8B1A1A"],
        ],
        texttemplate="%{z}",
        textfont={"size": 12, "color": "#1A1D23"},
        hovertemplate="<b>%{y}</b> × %{x}<br>Valeur : %{z}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text=measure_name, font=dict(size=16, color=SLATE)),
        height=max(350, len(display_df) * 40 + 120),
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(side="top", tickfont=dict(size=11)),
        yaxis=dict(tickfont=dict(size=11), autorange="reversed"),
    )
    return fig


def _make_bar_chart(pivot_df, measure_name):
    """Create a grouped bar chart from the pivot."""
    display_df = pivot_df.drop(columns=["Base (n)"], errors="ignore")

    if display_df.empty:
        return None

    colors = [BETCLIC_RED, OPINIONWAY_PURPLE, "#2980B9", "#27AE60", "#F39C12",
              "#1ABC9C", "#E67E22", "#8E44AD", "#34495E", "#D35400"]

    fig = go.Figure()
    for i, col in enumerate(display_df.columns):
        fig.add_trace(go.Bar(
            name=str(col),
            x=[str(r) for r in display_df.index],
            y=display_df[col].values,
            marker_color=colors[i % len(colors)],
            text=display_df[col].values,
            textposition="outside",
            textfont=dict(size=10),
        ))

    fig.update_layout(
        barmode="group",
        title=dict(text=measure_name, font=dict(size=16, color=SLATE)),
        height=max(400, 450),
        margin=dict(l=20, r=20, t=60, b=80),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
        yaxis=dict(gridcolor="#F0F0F0"),
        xaxis=dict(tickangle=-30),
    )
    return fig


def render():
    data = st.session_state["data"]
    vagues = st.session_state["selected_vagues"]
    villes = st.session_state["selected_villes"]
    genres = st.session_state["selected_genres"]
    segments = st.session_state["selected_segments"]
    marques = st.session_state.get("selected_marques", [])

    df = apply_filters(data, vagues, villes, genres, segments)

    # Apply brand filter if set
    if marques:
        df = df[df["Marque_Principale_Utilisee"].isin(marques)]

    st.markdown(section_header(
        "Tableau Croisé Dynamique",
        "Croisez librement toutes les variables de l'enquête"
    ), unsafe_allow_html=True)

    # ── Pivot configuration ──
    st.markdown("#### Configuration du croisement")

    c1, c2, c3 = st.columns(3)

    with c1:
        row_dim = st.selectbox(
            "Variable en ligne (axe Y)",
            list(DIMENSION_COLS.keys()),
            index=0,
            key="pivot_row",
        )
    with c2:
        col_options = ["(aucune)"] + [d for d in DIMENSION_COLS.keys() if d != row_dim]
        col_dim = st.selectbox(
            "Variable en colonne (axe X)",
            col_options,
            index=0,
            key="pivot_col",
        )
    with c3:
        measure_name = st.selectbox(
            "Indicateur à calculer",
            list(MEASURE_COLS.keys()),
            index=0,
            key="pivot_measure",
        )

    # Viz type
    viz_options = ["Tableau", "Heatmap", "Graphique barres"]
    viz_type = st.radio(
        "Mode de visualisation",
        viz_options,
        horizontal=True,
        key="pivot_viz",
    )

    st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

    # ── Compute ──
    if len(df) == 0:
        st.warning("Aucune donnée avec les filtres actuels.")
        return

    pivot = _compute_pivot(df, row_dim, col_dim, measure_name)

    # ── Display base info ──
    n_total = len(df)
    st.markdown(
        f"<div style='color:#4A5568; font-size:0.85rem; margin-bottom:1rem;'>"
        f"Base filtrée : <strong>{n_total:,}</strong> répondants | "
        f"Lignes : <strong>{row_dim}</strong> | "
        f"Colonnes : <strong>{col_dim}</strong> | "
        f"Mesure : <strong>{measure_name}</strong></div>",
        unsafe_allow_html=True,
    )

    # ── Render ──
    if viz_type == "Tableau":
        # Style the dataframe
        styled = pivot.style.format("{:.1f}", na_rep="—").format(
            {"Base (n)": "{:.0f}"}, na_rep="—"
        )

        # Highlight max/min for non-base columns
        display_cols = [c for c in pivot.columns if c != "Base (n)"]
        if display_cols:
            styled = styled.highlight_max(
                subset=display_cols, color="rgba(192,57,43,0.15)"
            ).highlight_min(
                subset=display_cols, color="rgba(108,52,131,0.10)"
            )

        st.dataframe(styled, width='stretch', height=min(600, len(pivot) * 40 + 60))

        # Insight
        display_data = pivot.drop(columns=["Base (n)"], errors="ignore")
        if not display_data.empty:
            if display_data.shape[1] == 1:
                max_row = display_data.iloc[:, 0].idxmax()
                max_val = display_data.iloc[:, 0].max()
                min_row = display_data.iloc[:, 0].idxmin()
                min_val = display_data.iloc[:, 0].min()
                st.markdown(insight_box(
                    f"<strong>Max :</strong> {max_row} = <strong>{max_val}</strong> | "
                    f"<strong>Min :</strong> {min_row} = <strong>{min_val}</strong> | "
                    f"<strong>Écart :</strong> {round(max_val - min_val, 1)}"
                ), unsafe_allow_html=True)
            else:
                grand_max = display_data.max().max()
                grand_min = display_data.min().min()
                st.markdown(insight_box(
                    f"<strong>Valeur max :</strong> {grand_max} | "
                    f"<strong>Valeur min :</strong> {grand_min} | "
                    f"<strong>Amplitude :</strong> {round(grand_max - grand_min, 1)}"
                ), unsafe_allow_html=True)

    elif viz_type == "Heatmap":
        fig = _make_heatmap(pivot, measure_name)
        if fig:
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Pas assez de données pour la heatmap.")

    elif viz_type == "Graphique barres":
        fig = _make_bar_chart(pivot, measure_name)
        if fig:
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Pas assez de données pour le graphique.")

    # ── Export pivot as CSV ──
    st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)
    csv = pivot.to_csv(sep=";", decimal=",")
    st.download_button(
        "Exporter ce tableau croise (CSV)",
        csv,
        f"pivot_{row_dim}_{col_dim}_{measure_name}.csv",
        "text/csv",
        width='stretch',
    )
