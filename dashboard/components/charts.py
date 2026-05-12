"""
Reusable Plotly chart builders for the Betclic Brand Pulse Dashboard.
"""

import plotly.graph_objects as go
import plotly.express as px
import numpy as np

# ── Color palette ──
BETCLIC_RED = "#C0392B"
OPINIONWAY_PURPLE = "#6C3483"
SLATE = "#2C3E50"
COLORS_VAGUES = {"Vague 1": "#E74C3C", "Vague 2": "#F39C12", "Vague 3": "#27AE60"}
COLORS_SEQ = ["#C0392B", "#6C3483", "#2980B9", "#27AE60", "#F39C12", "#E67E22", "#1ABC9C", "#8E44AD", "#34495E"]

LAYOUT_DEFAULTS = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#FAFAFA", size=12),
    margin=dict(l=40, r=40, t=50, b=40),
    hoverlabel=dict(bgcolor="#2C3E50", font_size=13, font_family="Inter"),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
)


def _apply_layout(fig, title="", height=400):
    fig.update_layout(**LAYOUT_DEFAULTS, title=dict(text=title, font=dict(size=16, color="#FAFAFA")), height=height)
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)", zerolinecolor="rgba(255,255,255,0.1)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)", zerolinecolor="rgba(255,255,255,0.1)")
    return fig


def bar_chart_brands(data: dict, title: str = "", highlight: str = "Betclic", height=400):
    """Horizontal bar chart comparing brands."""
    sorted_data = dict(sorted(data.items(), key=lambda x: x[1], reverse=True))
    brands = list(sorted_data.keys())
    values = list(sorted_data.values())
    colors = [BETCLIC_RED if b == highlight else "#4A5568" for b in brands]

    fig = go.Figure(go.Bar(
        y=brands, x=values, orientation="h",
        marker_color=colors,
        text=[f"{v}%" for v in values],
        textposition="outside",
        textfont=dict(size=13, color="#FAFAFA"),
    ))
    fig.update_yaxes(autorange="reversed")
    return _apply_layout(fig, title, height)


def grouped_bar_vagues(data_by_vague: dict, title: str = "", height=400):
    """Grouped bar chart by vague for brand comparison."""
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
    """Line chart showing KPI evolution across waves."""
    vagues = list(vague_values.keys())
    values = list(vague_values.values())
    labels = ["V1", "V2", "V3"][:len(vagues)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels, y=values,
        mode="lines+markers+text",
        line=dict(color=BETCLIC_RED, width=3),
        marker=dict(size=12, color=BETCLIC_RED, line=dict(width=2, color="#FAFAFA")),
        text=[f"{v}{suffix}" for v in values],
        textposition="top center",
        textfont=dict(size=14, color="#FAFAFA"),
        fill="tozeroy",
        fillcolor="rgba(192,57,43,0.1)",
    ))
    return _apply_layout(fig, title, height)


def multi_line_chart(data: dict, title: str = "", suffix="%", height=400):
    """Multi-line chart for multiple KPIs across waves."""
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
    """Radar chart for image attributes across waves."""
    fig = go.Figure()
    for vague, scores in data_by_vague.items():
        categories = list(scores.keys())
        values = list(scores.values())
        values.append(values[0])  # Close the polygon
        categories.append(categories[0])

        fig.add_trace(go.Scatterpolar(
            r=values, theta=categories,
            fill="toself",
            name=vague,
            line_color=COLORS_VAGUES.get(vague, SLATE),
            fillcolor=f"rgba({','.join(str(int(COLORS_VAGUES.get(vague, '#2C3E50').lstrip('#')[i:i+2], 16)) for i in (0,2,4))},0.1)",
        ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[1, 5], gridcolor="rgba(255,255,255,0.1)"),
            angularaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    return _apply_layout(fig, title, height)


def donut_chart(data: dict, title: str = "", hole=0.55, height=350, colors=None):
    """Donut chart."""
    if colors is None:
        colors = COLORS_SEQ[:len(data)]
    fig = go.Figure(go.Pie(
        labels=list(data.keys()),
        values=list(data.values()),
        hole=hole,
        marker=dict(colors=colors),
        textinfo="label+percent",
        textfont=dict(size=12, color="#FAFAFA"),
        hoverinfo="label+value+percent",
    ))
    return _apply_layout(fig, title, height)


def funnel_chart(data: dict, title: str = "", height=400):
    """Funnel chart for brand conversion funnel."""
    labels = list(data.keys())
    values = list(data.values())
    colors_f = [BETCLIC_RED, "#E74C3C", OPINIONWAY_PURPLE, "#2980B9", "#27AE60", "#F39C12"]

    fig = go.Figure(go.Funnel(
        y=labels, x=values,
        textinfo="value+percent initial",
        textfont=dict(size=13),
        marker=dict(color=colors_f[:len(labels)]),
        connector=dict(line=dict(color="rgba(255,255,255,0.1)", width=1)),
    ))
    return _apply_layout(fig, title, height)


def gauge_chart(value: float, title: str = "", max_val: float = 100, height=250):
    """Gauge chart for single KPI."""
    color = "#27AE60" if value > 60 else ("#F39C12" if value > 30 else "#E74C3C")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title=dict(text=title, font=dict(size=14, color="#8899A6")),
        number=dict(suffix="%", font=dict(size=28, color="#FAFAFA")),
        gauge=dict(
            axis=dict(range=[0, max_val], tickcolor="#8899A6"),
            bar=dict(color=color),
            bgcolor="#1A1D23",
            borderwidth=0,
            steps=[
                dict(range=[0, max_val * 0.33], color="rgba(231,76,60,0.15)"),
                dict(range=[max_val * 0.33, max_val * 0.66], color="rgba(243,156,18,0.15)"),
                dict(range=[max_val * 0.66, max_val], color="rgba(39,174,96,0.15)"),
            ],
        ),
    ))
    return _apply_layout(fig, "", height)


def nps_gauge(nps_score: float, height=280):
    """NPS-specific gauge chart."""
    color = "#27AE60" if nps_score > 30 else ("#F39C12" if nps_score > 0 else "#E74C3C")
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=nps_score,
        title=dict(text="Net Promoter Score", font=dict(size=16, color="#8899A6")),
        number=dict(font=dict(size=36, color="#FAFAFA")),
        gauge=dict(
            axis=dict(range=[-100, 100], tickcolor="#8899A6"),
            bar=dict(color=color),
            bgcolor="#1A1D23",
            borderwidth=0,
            steps=[
                dict(range=[-100, 0], color="rgba(231,76,60,0.15)"),
                dict(range=[0, 30], color="rgba(243,156,18,0.15)"),
                dict(range=[30, 100], color="rgba(39,174,96,0.15)"),
            ],
            threshold=dict(line=dict(color="white", width=2), thickness=0.75, value=nps_score),
        ),
    ))
    return _apply_layout(fig, "", height)


def heatmap_cities(city_data: dict, kpi_name: str = "", height=300):
    """Heatmap for city comparison."""
    cities = list(city_data.keys())
    values = [list(v.values()) if isinstance(v, dict) else [v] for v in city_data.values()]

    fig = go.Figure(go.Bar(
        x=cities, y=[v[0] if isinstance(v, list) else v for v in city_data.values()],
        marker=dict(
            color=[v[0] if isinstance(v, list) else v for v in city_data.values()],
            colorscale=[[0, SLATE], [0.5, OPINIONWAY_PURPLE], [1, BETCLIC_RED]],
            showscale=True,
            colorbar=dict(title=dict(text=kpi_name, font=dict(size=11))),
        ),
        text=[f"{v[0] if isinstance(v, list) else v}%" for v in city_data.values()],
        textposition="outside",
        textfont=dict(size=13, color="#FAFAFA"),
    ))
    return _apply_layout(fig, kpi_name, height)


def bubble_chart(data: list, title: str = "", height=500):
    """Bubble chart for competitive positioning.
    data: list of dicts with keys: name, x, y, size, color
    """
    fig = go.Figure()
    for d in data:
        fig.add_trace(go.Scatter(
            x=[d["x"]], y=[d["y"]],
            mode="markers+text",
            marker=dict(size=d.get("size", 30), color=d.get("color", SLATE), opacity=0.8,
                        line=dict(width=2, color="#FAFAFA" if d["name"] == "Betclic" else "rgba(255,255,255,0.3)")),
            text=[d["name"]],
            textposition="top center",
            textfont=dict(size=12, color="#FAFAFA"),
            name=d["name"],
            showlegend=False,
        ))
    return _apply_layout(fig, title, height)


def stacked_bar(categories: list, series: dict, title: str = "", height=400):
    """Stacked bar chart."""
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
    """Simple timeline/scatter for events."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=[1] * len(dates),
        mode="markers+text",
        marker=dict(size=14, color=BETCLIC_RED, symbol="diamond"),
        text=events,
        textposition="top center",
        textfont=dict(size=10, color="#FAFAFA"),
    ))
    fig.update_yaxes(visible=False)
    return _apply_layout(fig, title, height)
