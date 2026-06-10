"""
Reusable Plotly chart builders · V2 White Premium Theme.
"""

import plotly.graph_objects as go
import plotly.express as px
import numpy as np

# ── Color palette ──
BETCLIC_RED = "#C0392B"
OPINIONWAY_PURPLE = "#6C3483"
SLATE = "#2C3E50"
TEXT_COLOR = "#1A1D23"
TEXT_MUTED = "#4A5568"
GRID_COLOR = "rgba(0,0,0,0.06)"
COLORS_VAGUES = {"Vague 1": "#E74C3C", "Vague 2": "#F39C12", "Vague 3": "#27AE60"}
COLORS_SEQ = ["#C0392B", "#6C3483", "#2980B9", "#27AE60", "#F39C12", "#E67E22", "#1ABC9C", "#8E44AD", "#34495E"]
BAR_INACTIVE = "#CBD5E0"

# ── Couleurs de marque (charte client validée juin 2026) ──
# Chaque concurrent a sa couleur propre, alignée sur son identité visuelle.
BRAND_COLORS = {
    "Betclic":     "#C0392B",  # rouge Betclic
    "1XBET":       "#2BB6F0",  # bleu cyan
    "BetMomo":     "#0D1B4D",  # bleu marine
    "Melbet":      "#F5D547",  # jaune
    "MELBET":      "#F5D547",  # alias casse
    "Sportcash":   "#E89320",  # orange
    "SportCash":   "#E89320",  # alias casse
    "AkwaBet":     "#1E5A3E",  # vert foncé
    "Akwabet":     "#1E5A3E",
    "Paripesa":    "#2E54E0",  # bleu royal
    "PARIPESA":    "#2E54E0",
    "Premier Bet": "#9B59B6",
    "PremierBet":  "#9B59B6",
    "Betwinner":   "#2BAE5A",  # vert émeraude
    "BETWINNER":   "#2BAE5A",
    "Bet365":      "#000000",  # noir
    "bet365":      "#000000",
    "Afropari":    "#7D3C98",
    "BetPawa":     "#FF6B35",
    "YellowBet":   "#F1C40F",
    "Chopbet":     "#A93226",
    "Betway":      "#00A551",
}


def brand_color(brand: str, default: str = "#94A3B8") -> str:
    """Retourne la couleur d'une marque (charte client). Fallback gris neutre."""
    if brand in BRAND_COLORS:
        return BRAND_COLORS[brand]
    # Recherche insensible à la casse
    for k, v in BRAND_COLORS.items():
        if k.lower() == str(brand).lower():
            return v
    return default

LAYOUT_DEFAULTS = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=TEXT_COLOR, size=12),
    margin=dict(l=40, r=40, t=60, b=40),
    hoverlabel=dict(
        bgcolor="#FFFFFF",
        font_size=12,
        font_family="Inter, sans-serif",
        font_color=TEXT_COLOR,
        bordercolor="#E2E5EA",
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        borderwidth=0,
        font=dict(size=11, color=TEXT_MUTED),
    ),
    # Toolbar Plotly réduite (Power BI clean look)
    modebar=dict(
        bgcolor="rgba(0,0,0,0)",
        color="#94A3B8",
        activecolor="#C0392B",
        orientation="h",
    ),
)


def _apply_layout(fig, title="", height=400):
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=dict(
            text=title,
            font=dict(size=15, color=TEXT_COLOR, family="Inter, sans-serif"),
            x=0,
            xanchor="left",
            y=0.97,
            yanchor="top",
        ),
        height=height,
        # Réduire les boutons de la modebar à l'essentiel
        # (on garde reset/zoom, on retire les boutons exotiques)
    )
    # Axes propres : pas de top/right spine, gridlines subtiles
    fig.update_xaxes(
        gridcolor=GRID_COLOR,
        zerolinecolor="rgba(15,23,42,0.12)",
        linecolor="#E8EAEE",
        showline=True,
        ticks="outside",
        tickcolor="#E8EAEE",
        tickfont=dict(size=11, color=TEXT_MUTED),
    )
    fig.update_yaxes(
        gridcolor=GRID_COLOR,
        zerolinecolor="rgba(15,23,42,0.12)",
        linecolor="#E8EAEE",
        showline=False,
        tickfont=dict(size=11, color=TEXT_MUTED),
    )
    return fig


def bar_chart_brands(data: dict, title: str = "", highlight: str = "Betclic", height=400, use_brand_colors: bool = True):
    """Bar chart horizontal par marque. Couleurs : charte client par défaut.

    Si use_brand_colors=False, repli sur l'ancien comportement (Betclic rouge,
    autres gris) — utile pour les charts non-concurrentiels (canaux, irritants).
    """
    sorted_data = dict(sorted(data.items(), key=lambda x: x[1], reverse=True))
    brands = list(sorted_data.keys())
    values = list(sorted_data.values())
    if use_brand_colors:
        colors = [brand_color(b, default=BAR_INACTIVE) for b in brands]
    else:
        colors = [BETCLIC_RED if b == highlight else BAR_INACTIVE for b in brands]

    fig = go.Figure(go.Bar(
        y=brands, x=values, orientation="h",
        marker_color=colors,
        text=[f"{v}%" for v in values],
        textposition="outside",
        textfont=dict(size=13, color=TEXT_COLOR),
    ))
    fig.update_yaxes(autorange="reversed")
    return _apply_layout(fig, title, height)


def grouped_bar_vagues(data_by_vague: dict, title: str = "", height=400):
    fig = go.Figure()
    for vague, data in data_by_vague.items():
        sorted_data = dict(sorted(data.items(), key=lambda x: x[1], reverse=True))
        fig.add_trace(go.Bar(
            name=vague,
            x=list(sorted_data.keys()),
            y=list(sorted_data.values()),
            marker_color=COLORS_VAGUES.get(vague, SLATE),
            text=[f"{v}%" for v in sorted_data.values()],
            textposition="outside",
            textfont=dict(size=11),
        ))
    fig.update_layout(barmode="group")
    return _apply_layout(fig, title, height)


def line_chart_evolution(vague_values: dict, title: str = "", suffix="%", height=350):
    vagues = list(vague_values.keys())
    values = list(vague_values.values())
    labels = ["V1", "V2", "V3"][:len(vagues)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels, y=values,
        mode="lines+markers+text",
        line=dict(color=BETCLIC_RED, width=3),
        marker=dict(size=12, color=BETCLIC_RED, line=dict(width=2, color="#FFFFFF")),
        text=[f"{v}{suffix}" for v in values],
        textposition="top center",
        textfont=dict(size=14, color=TEXT_COLOR),
        fill="tozeroy",
        fillcolor="rgba(192,57,43,0.06)",
    ))
    return _apply_layout(fig, title, height)


def multi_line_chart(data: dict, title: str = "", suffix="%", height=400):
    fig = go.Figure()
    colors = [BETCLIC_RED, OPINIONWAY_PURPLE, "#2980B9", "#27AE60", "#F39C12", "#E67E22"]
    labels = ["V1", "V2", "V3"]

    for i, (name, values) in enumerate(data.items()):
        vals = list(values.values()) if isinstance(values, dict) else values
        color = colors[i % len(colors)]
        fig.add_trace(go.Scatter(
            x=labels[:len(vals)], y=vals,
            name=name,
            mode="lines+markers",
            line=dict(color=color, width=2.5),
            marker=dict(size=8, color=color),
        ))
    return _apply_layout(fig, title, height)


def radar_chart(data_by_vague: dict, title: str = "", height=500):
    fig = go.Figure()
    for vague, scores in data_by_vague.items():
        categories = list(scores.keys())
        values = list(scores.values())
        values.append(values[0])
        categories.append(categories[0])

        fig.add_trace(go.Scatterpolar(
            r=values, theta=categories,
            fill="toself",
            name=vague,
            line_color=COLORS_VAGUES.get(vague, SLATE),
            fillcolor=f"rgba({','.join(str(int(COLORS_VAGUES.get(vague, '#2C3E50').lstrip('#')[i:i+2], 16)) for i in (0,2,4))},0.08)",
        ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[1, 5], gridcolor=GRID_COLOR, linecolor=GRID_COLOR),
            angularaxis=dict(gridcolor=GRID_COLOR, linecolor=GRID_COLOR),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    return _apply_layout(fig, title, height)


def donut_chart(data: dict, title: str = "", hole=0.55, height=350, colors=None):
    if colors is None:
        colors = COLORS_SEQ[:len(data)]
    fig = go.Figure(go.Pie(
        labels=list(data.keys()),
        values=list(data.values()),
        hole=hole,
        marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
        textinfo="label+percent",
        textfont=dict(size=12, color=TEXT_COLOR),
        hoverinfo="label+value+percent",
    ))
    return _apply_layout(fig, title, height)


def funnel_chart(data: dict, title: str = "", height=400):
    labels = list(data.keys())
    values = list(data.values())
    colors_f = [BETCLIC_RED, "#E74C3C", OPINIONWAY_PURPLE, "#2980B9", "#27AE60", "#F39C12"]

    fig = go.Figure(go.Funnel(
        y=labels, x=values,
        # Affiche uniquement la valeur en % (les valeurs sont déjà des pourcentages)
        texttemplate="%{x:.1f}%",
        textposition="inside",
        textfont=dict(size=14, color="#FFFFFF"),
        marker=dict(color=colors_f[:len(labels)]),
        connector=dict(line=dict(color=GRID_COLOR, width=1)),
    ))
    return _apply_layout(fig, title, height)


def gauge_chart(value: float, title: str = "", max_val: float = 100, height=250):
    color = "#27AE60" if value > 60 else ("#F39C12" if value > 30 else "#E74C3C")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title=dict(text=title, font=dict(size=14, color=TEXT_MUTED)),
        number=dict(suffix="%", font=dict(size=28, color=TEXT_COLOR)),
        gauge=dict(
            axis=dict(range=[0, max_val], tickcolor=TEXT_MUTED),
            bar=dict(color=color),
            bgcolor="#F5F6F8",
            borderwidth=0,
            steps=[
                dict(range=[0, max_val * 0.33], color="rgba(231,76,60,0.08)"),
                dict(range=[max_val * 0.33, max_val * 0.66], color="rgba(243,156,18,0.08)"),
                dict(range=[max_val * 0.66, max_val], color="rgba(39,174,96,0.08)"),
            ],
        ),
    ))
    return _apply_layout(fig, "", height)


def nps_gauge(nps_score: float, height=280):
    color = "#27AE60" if nps_score > 30 else ("#F39C12" if nps_score > 0 else "#E74C3C")
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=nps_score,
        title=dict(text="Net Promoter Score", font=dict(size=16, color=TEXT_MUTED)),
        number=dict(font=dict(size=36, color=TEXT_COLOR)),
        gauge=dict(
            axis=dict(range=[-100, 100], tickcolor=TEXT_MUTED),
            bar=dict(color=color),
            bgcolor="#F5F6F8",
            borderwidth=0,
            steps=[
                dict(range=[-100, 0], color="rgba(231,76,60,0.08)"),
                dict(range=[0, 30], color="rgba(243,156,18,0.08)"),
                dict(range=[30, 100], color="rgba(39,174,96,0.08)"),
            ],
            threshold=dict(line=dict(color=SLATE, width=2), thickness=0.75, value=nps_score),
        ),
    ))
    return _apply_layout(fig, "", height)


def heatmap_cities(city_data: dict, kpi_name: str = "", height=300, suffix: str = "%"):
    """Bar-style heatmap of a KPI by city. `suffix` is appended to value labels."""
    cities = list(city_data.keys())

    fig = go.Figure(go.Bar(
        x=cities, y=[v[0] if isinstance(v, list) else v for v in city_data.values()],
        marker=dict(
            color=[v[0] if isinstance(v, list) else v for v in city_data.values()],
            colorscale=[[0, "#E8E9ED"], [0.5, OPINIONWAY_PURPLE], [1, BETCLIC_RED]],
            showscale=True,
            colorbar=dict(title=dict(text=kpi_name, font=dict(size=11))),
        ),
        text=[f"{v[0] if isinstance(v, list) else v}{suffix}" for v in city_data.values()],
        textposition="outside",
        textfont=dict(size=13, color=TEXT_COLOR),
    ))
    return _apply_layout(fig, kpi_name, height)


def bubble_chart(data: list, title: str = "", height=500):
    fig = go.Figure()
    for d in data:
        fig.add_trace(go.Scatter(
            x=[d["x"]], y=[d["y"]],
            mode="markers+text",
            marker=dict(size=d.get("size", 30), color=d.get("color", BAR_INACTIVE), opacity=0.85,
                        line=dict(width=2, color="#FFFFFF" if d["name"] == "Betclic" else "rgba(0,0,0,0.1)")),
            text=[d["name"]],
            textposition="top center",
            textfont=dict(size=12, color=TEXT_COLOR),
            name=d["name"],
            showlegend=False,
        ))
    return _apply_layout(fig, title, height)


def stacked_bar(categories: list, series: dict, title: str = "", height=400):
    fig = go.Figure()
    colors = {"Positif": "#27AE60", "Neutre": "#F39C12", "Négatif": "#E74C3C"}
    for name, values in series.items():
        fig.add_trace(go.Bar(
            x=categories, y=values, name=name,
            marker_color=colors.get(name, SLATE),
        ))
    fig.update_layout(barmode="stack")
    return _apply_layout(fig, title, height)


def timeline_chart(dates: list, events: list, title: str = "", height=300):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=[1] * len(dates),
        mode="markers+text",
        marker=dict(size=14, color=BETCLIC_RED, symbol="diamond"),
        text=events,
        textposition="top center",
        textfont=dict(size=10, color=TEXT_COLOR),
    ))
    fig.update_yaxes(visible=False)
    return _apply_layout(fig, title, height)
