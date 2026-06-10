"""Brand Health Tracker · Analyse Géographique."""

import streamlit as st
import plotly.graph_objects as go
from data.loader import (
    apply_filters, calc_tom, calc_notoriete_totale, calc_penetration,
    calc_satisfaction, calc_nps, calc_preference, calc_consideration,
    calc_kpi_by_city, calc_kpi_by_commune, get_communes_in_data,
    CITIES, VAGUE_SHORT, MAIN_COMPETITORS
)
from components.styles import kpi_card, section_header, insight_box, styled_divider
from components.charts import heatmap_cities, BETCLIC_RED, OPINIONWAY_PURPLE, COLORS_SEQ, brand_color


def render():
    data = st.session_state["data"]
    vagues = st.session_state["selected_vagues"]
    villes = st.session_state["selected_villes"]
    genres = st.session_state["selected_genres"]
    segments = st.session_state["selected_segments"]

    df = apply_filters(data, vagues, villes or None, genres or None, segments or None)

    st.markdown(section_header(
        "Analyse Géographique",
        "Performances comparées sur les 7 villes stratégiques de Côte d'Ivoire"
    ), unsafe_allow_html=True)

    # Get latest vague data
    latest_vague = [v for v in ["Vague 3", "Vague 2", "Vague 1"] if v in vagues]
    if latest_vague:
        df_latest = df[df["Vague"] == latest_vague[0]]
    else:
        df_latest = df

    vague_label = VAGUE_SHORT.get(latest_vague[0], "") if latest_vague else "Total"

    # ── City KPI heatmaps ──
    kpis_geo = {
        "Top-of-Mind (%)": calc_kpi_by_city(df_latest, calc_tom),
        "Notoriété Totale (%)": calc_kpi_by_city(df_latest, calc_notoriete_totale),
        "Pénétration (%)": calc_kpi_by_city(df_latest, calc_penetration),
        "Considération (%)": calc_kpi_by_city(df_latest, calc_consideration),
        "Préférence (%)": calc_kpi_by_city(df_latest, calc_preference),
    }

    def _sat_city(sub):
        return calc_satisfaction(sub)

    def _nps_city(sub):
        return calc_nps(sub)["nps"]

    kpis_geo["Satisfaction (/5)"] = calc_kpi_by_city(df_latest, _sat_city)
    kpis_geo["NPS (pts)"] = calc_kpi_by_city(df_latest, _nps_city)

    # ── Main bar charts ──
    col_left, col_right = st.columns(2)

    with col_left:
        fig = heatmap_cities(kpis_geo["Top-of-Mind (%)"], f"Top-of-Mind par ville ({vague_label})", height=350)
        st.plotly_chart(fig, width='stretch')

    with col_right:
        fig = heatmap_cities(kpis_geo["Notoriété Totale (%)"], f"Notoriété Totale par ville ({vague_label})", height=350)
        st.plotly_chart(fig, width='stretch')

    st.markdown(styled_divider(), unsafe_allow_html=True)

    col_left, col_right = st.columns(2)

    with col_left:
        fig = heatmap_cities(kpis_geo["Pénétration (%)"], f"Pénétration par ville ({vague_label})", height=350)
        st.plotly_chart(fig, width='stretch')

    with col_right:
        fig = heatmap_cities(kpis_geo["Considération (%)"], f"Considération par ville ({vague_label})", height=350)
        st.plotly_chart(fig, width='stretch')

    st.markdown(styled_divider(), unsafe_allow_html=True)

    col_left, col_right = st.columns(2)

    with col_left:
        fig = heatmap_cities(kpis_geo["Préférence (%)"], f"Préférence par ville ({vague_label})", height=350)
        st.plotly_chart(fig, width='stretch')

    with col_right:
        fig = heatmap_cities(kpis_geo["Satisfaction (/5)"], f"Satisfaction par ville ({vague_label})", height=350, suffix="/5")
        st.plotly_chart(fig, width='stretch')

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # NPS · without % suffix
    fig = heatmap_cities(kpis_geo["NPS (pts)"], f"NPS par ville ({vague_label})", height=350, suffix=" pts")
    st.plotly_chart(fig, width='stretch')

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Comprehensive table ──
    st.markdown(section_header("Tableau Synthétique par Ville"), unsafe_allow_html=True)

    # Build a summary table
    import pandas as pd
    table_data = []
    for city in CITIES:
        row = {"Ville": city}
        for kpi_name, city_data in kpis_geo.items():
            row[kpi_name] = city_data.get(city, "—")
        table_data.append(row)

    df_table = pd.DataFrame(table_data)

    # Style the dataframe
    st.dataframe(
        df_table.set_index("Ville"),
        width='stretch',
        height=320,
    )

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Comparatif concurrentiel par ville ──
    st.markdown(section_header(
        "Comparaison concurrentielle par ville",
        "Betclic vs principaux concurrents · choisissez le KPI à comparer"
    ), unsafe_allow_html=True)

    import plotly.graph_objects as go
    import pandas as pd

    # Helper : compute per-brand per-city KPI from a column already present in df
    def _per_brand_per_city_pct(df_in, col_template):
        """Returns {brand: {city: pct}} for binary indicator columns like A_Deja_Parie_{brand}."""
        out = {}
        for b in MAIN_COMPETITORS:
            per_city = {}
            col = col_template.format(brand=b)
            for city in CITIES:
                sub = df_in[df_in["Ville"] == city]
                if len(sub) > 0 and col in sub.columns:
                    per_city[city] = round(sub[col].sum() / len(sub) * 100, 1)
                else:
                    per_city[city] = 0
            out[b] = per_city
        return out

    def _tom_per_brand_per_city(df_in):
        out = {}
        for b in MAIN_COMPETITORS:
            per_city = {}
            for city in CITIES:
                sub = df_in[df_in["Ville"] == city]
                if len(sub) > 0:
                    per_city[city] = round((sub["TOM_Marque_Citee"] == b).sum() / len(sub) * 100, 1)
                else:
                    per_city[city] = 0
            out[b] = per_city
        return out

    def _pref_per_brand_per_city(df_in):
        out = {}
        for b in MAIN_COMPETITORS:
            per_city = {}
            for city in CITIES:
                sub = df_in[(df_in["Ville"] == city) & (df_in["Type_Repondant"] == "Parieur")]
                if len(sub) > 0:
                    per_city[city] = round((sub["Marque_Principale_Utilisee"] == b).sum() / len(sub) * 100, 1)
                else:
                    per_city[city] = 0
            out[b] = per_city
        return out

    def _consid_per_brand_per_city(df_in):
        out = {}
        for b in MAIN_COMPETITORS:
            per_city = {}
            col = f"Consideration_{b}"
            for city in CITIES:
                sub = df_in[(df_in["Ville"] == city) & (df_in["Type_Repondant"] == "Parieur")]
                if len(sub) > 0 and col in sub.columns:
                    per_city[city] = round(sub[col].sum() / len(sub) * 100, 1)
                else:
                    per_city[city] = 0
            out[b] = per_city
        return out

    def _sat_per_brand_per_city(df_in):
        """Satisfaction mean (/5) per city, for parieurs whose Q6 = brand."""
        out = {}
        for b in MAIN_COMPETITORS:
            per_city = {}
            for city in CITIES:
                sub = df_in[(df_in["Ville"] == city) & (df_in["Marque_Principale_Utilisee"] == b)]
                if len(sub) >= 5 and "Satisfaction_Globale_Betclic" in sub.columns:
                    vals = sub["Satisfaction_Globale_Betclic"].dropna()
                    per_city[city] = round(vals.mean(), 2) if len(vals) > 0 else None
                else:
                    per_city[city] = None
            out[b] = per_city
        return out

    def _nps_per_brand_per_city(df_in):
        """NPS per city per brand (parieurs Q6=brand). Requires n>=10 to display."""
        out = {}
        for b in MAIN_COMPETITORS:
            per_city = {}
            for city in CITIES:
                sub = df_in[(df_in["Ville"] == city) & (df_in["Marque_Principale_Utilisee"] == b)]
                if len(sub) >= 10 and "NPS_Categorie" in sub.columns:
                    cats = sub["NPS_Categorie"].dropna()
                    if len(cats) > 0:
                        counts = cats.value_counts()
                        prom = counts.get("Promoteur", 0)
                        det = counts.get("Détracteur", 0)
                        per_city[city] = round((prom - det) / len(cats) * 100, 1)
                    else:
                        per_city[city] = None
                else:
                    per_city[city] = None
            out[b] = per_city
        return out

    # KPI selector
    KPI_CHOICES = {
        "Top-of-Mind (Q1A)": ("tom", "%", 0),
        "Notoriété Totale (Q1A+Q1B+Q1C)": ("notor", "%", 0),
        "Pénétration / Essai (Q5)": ("pen", "%", 0),
        "Considération (Q5 ∪ Q13 fort)": ("consid", "%", 0),
        "Préférence (Q6 marque principale)": ("pref", "%", 0),
        "Satisfaction (/5)": ("sat", "/5", 2),
        "NPS (pts)": ("nps", " pts", 0),
    }
    kpi_label = st.selectbox(
        "KPI à comparer entre marques et villes :",
        list(KPI_CHOICES.keys()),
        index=2,  # default = Pénétration
        key="geo_kpi_selector",
    )
    kpi_key, kpi_suffix, kpi_decimals = KPI_CHOICES[kpi_label]

    # Compute the data
    if kpi_key == "tom":
        data_per_brand = _tom_per_brand_per_city(df_latest)
    elif kpi_key == "notor":
        data_per_brand = _per_brand_per_city_pct(df_latest, "Notoriete_Totale_{brand}")
    elif kpi_key == "pen":
        data_per_brand = _per_brand_per_city_pct(df_latest, "A_Deja_Parie_{brand}")
    elif kpi_key == "consid":
        data_per_brand = _consid_per_brand_per_city(df_latest)
    elif kpi_key == "pref":
        data_per_brand = _pref_per_brand_per_city(df_latest)
    elif kpi_key == "sat":
        data_per_brand = _sat_per_brand_per_city(df_latest)
    elif kpi_key == "nps":
        data_per_brand = _nps_per_brand_per_city(df_latest)
    else:
        data_per_brand = {}

    # Format helper for text labels
    def _fmt(v):
        if v is None:
            return ""
        if kpi_decimals == 0:
            return f"{v:.0f}{kpi_suffix}"
        return f"{v:.{kpi_decimals}f}{kpi_suffix}"

    fig_geo = go.Figure()
    has_any = False
    for i, b in enumerate(MAIN_COMPETITORS):
        vals = [data_per_brand.get(b, {}).get(c) for c in CITIES]
        # Skip if all values are None for this brand
        if all(v is None for v in vals):
            continue
        has_any = True
        plot_vals = [v if v is not None else 0 for v in vals]
        fig_geo.add_trace(go.Bar(
            name=b,
            x=CITIES,
            y=plot_vals,
            text=[_fmt(v) for v in vals],
            textposition="outside",
            textfont=dict(size=9),
            marker_color=brand_color(b),
        ))

    if has_any:
        # Adjust Y-axis range based on data
        all_vals = [v for b in MAIN_COMPETITORS for v in data_per_brand.get(b, {}).values() if v is not None]
        if all_vals:
            y_min = min(0, min(all_vals) - 5)
            y_max = max(all_vals) * 1.18
        else:
            y_min, y_max = 0, 100
        fig_geo.update_layout(
            barmode="group",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="#1A1D23", size=11),
            margin=dict(l=40, r=40, t=50, b=80),
            height=460,
            title=dict(text=f"{kpi_label} par ville et par marque ({vague_label})", font=dict(size=15)),
            yaxis=dict(range=[y_min, y_max], gridcolor="rgba(0,0,0,0.06)",
                       title=kpi_suffix.strip() or "%", zeroline=True, zerolinecolor="#1A1D23"),
            xaxis=dict(tickangle=-20),
            legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.20),
        )
        st.plotly_chart(fig_geo, width='stretch')

        # Compact comparison table
        table_rows = []
        for c in CITIES:
            row = {"Ville": c}
            for b in MAIN_COMPETITORS:
                v = data_per_brand.get(b, {}).get(c)
                row[b] = _fmt(v) if v is not None else "—"
            table_rows.append(row)
        st.dataframe(pd.DataFrame(table_rows).set_index("Ville"), width='stretch', height=300)

        if kpi_key in ("sat", "nps"):
            st.caption(
                "ℹ️ Satisfaction et NPS sont calculés uniquement sur les utilisateurs principaux "
                "(Q6 = marque). Affichage masqué si la base est trop petite par ville × marque "
                f"(< {5 if kpi_key == 'sat' else 10} répondants)."
            )
    else:
        st.info("Pas assez de données pour ce KPI à ce niveau de granularité.")

    st.markdown(styled_divider(), unsafe_allow_html=True)

    # ── Insight ──
    # Find best and worst performing cities
    tom_data = kpis_geo["Top-of-Mind (%)"]
    if tom_data:
        best_city = max(tom_data, key=tom_data.get)
        worst_city = min(tom_data, key=tom_data.get)
        pen_data = kpis_geo["Pénétration (%)"]
        best_pen_city = max(pen_data, key=pen_data.get) if pen_data else "N/A"

        st.markdown(insight_box(
            f"<strong>{best_city}</strong> affiche le meilleur TOM ({tom_data[best_city]}%), "
            f"tandis que <strong>{worst_city}</strong> présente le plus faible ({tom_data[worst_city]}%). "
            f"La pénétration est maximale à <strong>{best_pen_city}</strong> "
            f"({pen_data.get(best_pen_city, 0)}%). "
            f"Les villes secondaires montrent un potentiel de croissance significatif pour Betclic."
        ), unsafe_allow_html=True)

    # ────────────────────────────────────────────────────────
    # ZOOM ABIDJAN · analyse par commune (Q29_Commune)
    # ────────────────────────────────────────────────────────
    st.markdown(styled_divider(), unsafe_allow_html=True)
    st.markdown(section_header(
        "🏙️ Zoom Abidjan · Analyse par commune",
        "Décomposition par commune des 256 répondants abidjanais (Q29_Commune)"
    ), unsafe_allow_html=True)

    df_abidjan = df_latest[df_latest["Ville"] == "Abidjan"]
    if "Commune" not in df_abidjan.columns or df_abidjan["Commune"].notna().sum() == 0:
        st.info("Aucune donnée commune disponible dans cette vague.")
    else:
        # Toutes les communes présentes dans la data (pas de filtre par taille de base)
        valid_communes = sorted(
            [c for c in df_abidjan["Commune"].dropna().unique() if str(c).strip()],
            key=lambda c: -int((df_abidjan["Commune"] == c).sum()),
        )
        if not valid_communes:
            st.warning("Aucune commune renseignée dans cette vague.")
        else:
            # Recap des bases (affichage de toutes les communes, sans seuil)
            base_per_commune = {c: int((df_abidjan["Commune"] == c).sum()) for c in valid_communes}
            base_str = " • ".join([f"{c} ({n})" for c, n in sorted(base_per_commune.items(), key=lambda x: -x[1])])
            st.caption(f"📍 **Communes affichées** : {base_str}")

            # KPIs Betclic par commune
            tom_c = calc_kpi_by_commune(df_abidjan, calc_tom, min_base=1)
            notor_c = calc_kpi_by_commune(df_abidjan, calc_notoriete_totale, min_base=1)
            pen_c = calc_kpi_by_commune(df_abidjan, calc_penetration, min_base=1)
            pref_c = calc_kpi_by_commune(df_abidjan, calc_preference, min_base=1)
            consid_c = calc_kpi_by_commune(df_abidjan, calc_consideration, min_base=1)

            # Tri par pénétration décroissante pour cohérence visuelle
            sorted_communes = sorted(valid_communes, key=lambda c: -pen_c.get(c, 0))

            # Bar chart groupé : 5 KPIs par commune
            fig_c = go.Figure()
            kpi_groups = [
                ("Notoriété Totale", notor_c, "#7B8794"),
                ("TOM", tom_c, OPINIONWAY_PURPLE),
                ("Considération", consid_c, "#2980B9"),
                ("Pénétration", pen_c, BETCLIC_RED),
                ("Préférence", pref_c, "#27AE60"),
            ]
            for label, data, color in kpi_groups:
                vals = [data.get(c, 0) for c in sorted_communes]
                fig_c.add_trace(go.Bar(
                    name=label,
                    x=sorted_communes,
                    y=vals,
                    text=[f"{v:.0f}%" for v in vals],
                    textposition="outside",
                    textfont=dict(size=9),
                    marker_color=color,
                ))
            fig_c.update_layout(
                barmode="group",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", color="#1A1D23", size=11),
                margin=dict(l=40, r=40, t=50, b=80),
                height=480,
                title=dict(text=f"KPIs Betclic par commune d'Abidjan ({vague_label})", font=dict(size=15)),
                yaxis=dict(range=[0, 110], gridcolor="rgba(0,0,0,0.06)", title="%"),
                xaxis=dict(tickangle=-20),
                legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.18),
            )
            st.plotly_chart(fig_c, width='stretch')

            # Comparaison Betclic vs 1XBET par commune (les 2 leaders)
            st.markdown("**Comparaison Betclic vs 1XBET par commune** (Pénétration Q5)")

            def _pen_per_brand_per_commune(brand):
                col = f"A_Deja_Parie_{brand}"
                if col not in df_abidjan.columns:
                    return {}
                out = {}
                for commune in sorted_communes:
                    sub = df_abidjan[df_abidjan["Commune"] == commune]
                    if len(sub) > 0:
                        out[commune] = round(sub[col].sum() / len(sub) * 100, 1)
                return out

            pen_betclic = _pen_per_brand_per_commune("Betclic")
            pen_1xbet = _pen_per_brand_per_commune("1XBET")

            fig_cmp_c = go.Figure()
            fig_cmp_c.add_trace(go.Bar(
                name="Betclic",
                x=sorted_communes,
                y=[pen_betclic.get(c, 0) for c in sorted_communes],
                text=[f"{pen_betclic.get(c, 0):.0f}%" for c in sorted_communes],
                textposition="outside",
                marker_color=brand_color("Betclic"),
            ))
            fig_cmp_c.add_trace(go.Bar(
                name="1XBET",
                x=sorted_communes,
                y=[pen_1xbet.get(c, 0) for c in sorted_communes],
                text=[f"{pen_1xbet.get(c, 0):.0f}%" for c in sorted_communes],
                textposition="outside",
                marker_color=brand_color("1XBET"),
            ))
            fig_cmp_c.update_layout(
                barmode="group",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", color="#1A1D23", size=11),
                margin=dict(l=40, r=40, t=30, b=80),
                height=380,
                yaxis=dict(gridcolor="rgba(0,0,0,0.06)", title="Pénétration (%)"),
                xaxis=dict(tickangle=-20),
                legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.18),
            )
            st.plotly_chart(fig_cmp_c, width='stretch')

            # Tableau synthétique
            import pandas as _pd
            rows = []
            for c in sorted_communes:
                rows.append({
                    "Commune": c,
                    "n": base_per_commune[c],
                    "TOM (%)": tom_c.get(c, 0),
                    "Notoriété (%)": notor_c.get(c, 0),
                    "Pénétration (%)": pen_c.get(c, 0),
                    "Considération (%)": consid_c.get(c, 0),
                    "Préférence (%)": pref_c.get(c, 0),
                })
            st.dataframe(_pd.DataFrame(rows).set_index("Commune"), width='stretch', height=320)

            # Insight automatique
            if pen_c:
                top_pen = max(pen_c, key=pen_c.get)
                top_pref = max(pref_c, key=pref_c.get)
                st.markdown(insight_box(
                    f"À Abidjan, <strong>{top_pen}</strong> affiche la plus forte pénétration Betclic "
                    f"({pen_c[top_pen]}%), et <strong>{top_pref}</strong> la meilleure préférence "
                    f"({pref_c[top_pref]}%). Ces communes sont des bastions Betclic, à consolider. "
                    f"Les communes à fort potentiel restent celles où la notoriété est élevée mais la "
                    f"pénétration faible · opportunité d'activation locale."
                ), unsafe_allow_html=True)
