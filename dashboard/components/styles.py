"""Custom CSS styles for the Betclic Brand Pulse Dashboard."""

CUSTOM_CSS = """
<style>
/* ── Global ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1A1D23 0%, #0E1117 100%);
    border-right: 1px solid rgba(192, 57, 43, 0.3);
}

[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label {
    color: #FAFAFA;
    font-weight: 600;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* ── KPI Cards ── */
.kpi-card {
    background: linear-gradient(135deg, #1A1D23 0%, #2C3E50 100%);
    border: 1px solid rgba(192, 57, 43, 0.2);
    border-radius: 16px;
    padding: 1.2rem 0.8rem;
    text-align: center;
    transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    height: 170px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    box-sizing: border-box;
}
.kpi-card:hover {
    border-color: #C0392B;
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(192,57,43,0.2);
}
.kpi-value {
    font-size: clamp(1.6rem, 3.5vw, 2.4rem);
    font-weight: 800;
    color: #FAFAFA;
    line-height: 1.15;
    margin: 0.25rem 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
}
.kpi-label {
    font-size: clamp(0.6rem, 1.2vw, 0.78rem);
    color: #8899A6;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
    line-height: 1.25;
    min-height: 2.1em;
    display: flex;
    align-items: center;
    justify-content: center;
    max-width: 100%;
    word-wrap: break-word;
    overflow-wrap: break-word;
    hyphens: auto;
}
.kpi-delta {
    font-size: clamp(0.65rem, 1.1vw, 0.85rem);
    font-weight: 700;
    margin-top: 0.2rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
}
.delta-up { color: #27AE60; }
.delta-down { color: #E74C3C; }
.delta-neutral { color: #F39C12; }

/* ── Section Headers ── */
.section-header {
    background: linear-gradient(90deg, #C0392B 0%, #6C3483 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 1.8rem;
    font-weight: 800;
    margin: 2rem 0 1rem 0;
    letter-spacing: -0.02em;
}
.section-subheader {
    color: #8899A6;
    font-size: 0.95rem;
    margin-top: -0.8rem;
    margin-bottom: 1.5rem;
}

/* ── Insight Boxes ── */
.insight-box {
    background: linear-gradient(135deg, rgba(192,57,43,0.08) 0%, rgba(108,52,131,0.08) 100%);
    border-left: 4px solid #C0392B;
    border-radius: 0 12px 12px 0;
    padding: 1rem 1.2rem;
    margin: 1rem 0;
    font-size: 0.9rem;
    color: #FAFAFA;
    line-height: 1.5;
}
.insight-box strong {
    color: #C0392B;
}

/* ── Alert Box ── */
.alert-box {
    background: rgba(231, 76, 60, 0.1);
    border: 1px solid rgba(231, 76, 60, 0.3);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin: 0.8rem 0;
    font-size: 0.85rem;
}
.alert-box.warning {
    background: rgba(243, 156, 18, 0.1);
    border-color: rgba(243, 156, 18, 0.3);
}
.alert-box.success {
    background: rgba(39, 174, 96, 0.1);
    border-color: rgba(39, 174, 96, 0.3);
}

/* ── Competitor Cards ── */
.competitor-card {
    background: linear-gradient(135deg, #1A1D23 0%, #2C3E50 100%);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 1.2rem;
    text-align: center;
    transition: all 0.3s ease;
}
.competitor-card:hover {
    border-color: #6C3483;
    box-shadow: 0 8px 25px rgba(108,52,131,0.2);
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    background-color: #1A1D23;
    border-radius: 8px;
    padding: 8px 16px;
    color: #8899A6;
    font-weight: 600;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #C0392B 0%, #6C3483 100%);
    color: white !important;
}

/* ── Uniform column heights for KPI rows ── */
[data-testid="stHorizontalBlock"] {
    align-items: stretch;
}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    display: flex;
    flex-direction: column;
}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > div {
    flex: 1;
    display: flex;
    flex-direction: column;
}

/* ── Metric containers ── */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #1A1D23 0%, #2C3E50 100%);
    border: 1px solid rgba(192, 57, 43, 0.15);
    border-radius: 16px;
    padding: 1rem 1.2rem;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}
[data-testid="stMetric"] label {
    color: #8899A6 !important;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.75rem !important;
    letter-spacing: 0.05em;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 2rem !important;
    font-weight: 800;
}

/* ── Plotly charts container ── */
.stPlotlyChart {
    border-radius: 16px;
    overflow: hidden;
}

/* ── Divider ── */
.styled-divider {
    height: 2px;
    background: linear-gradient(90deg, #C0392B, #6C3483, transparent);
    border: none;
    margin: 2rem 0;
    border-radius: 2px;
}

/* ── Logo area ── */
.logo-container {
    text-align: center;
    padding: 1rem 0 1.5rem 0;
}
.sidebar-logos {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.6rem;
    margin-bottom: 0.8rem;
}
.sidebar-logo-betclic {
    height: 32px;
    width: auto;
    filter: brightness(1.1);
}
.sidebar-logo-x {
    color: #4A5568;
    font-size: 1rem;
    font-weight: 300;
}
.sidebar-logo-ow {
    height: 30px;
    width: auto;
    filter: brightness(1.2);
}
.logo-container h1 {
    background: linear-gradient(90deg, #C0392B, #6C3483);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 1.5rem;
    font-weight: 800;
    margin: 0;
    letter-spacing: 0.05em;
}
.logo-container p {
    color: #8899A6;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin-top: 0.2rem;
}

/* ── Sidebar radio module selector ── */
[data-testid="stSidebar"] .stRadio > div {
    gap: 0.5rem;
}
[data-testid="stSidebar"] .stRadio > div > label {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 0.6rem 1rem;
    cursor: pointer;
    transition: all 0.2s ease;
    font-weight: 600;
    font-size: 0.88rem;
}
[data-testid="stSidebar"] .stRadio > div > label:hover {
    border-color: rgba(192,57,43,0.4);
    background: rgba(192,57,43,0.08);
}
[data-testid="stSidebar"] .stRadio > div > label[data-checked="true"],
[data-testid="stSidebar"] .stRadio > div > label:has(input:checked) {
    background: linear-gradient(135deg, rgba(192,57,43,0.15), rgba(108,52,131,0.15));
    border-color: #C0392B;
}

/* ── Hide Streamlit defaults ── */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""


def inject_css():
    """Inject custom CSS into the Streamlit app."""
    import streamlit as st
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def kpi_card(label: str, value: str, delta: str = None, delta_direction: str = "up") -> str:
    """Generate HTML for a KPI card."""
    delta_html = ""
    if delta is not None:
        arrow = "▲" if delta_direction == "up" else ("▼" if delta_direction == "down" else "●")
        css_class = f"delta-{delta_direction}"
        delta_html = f'<div class="kpi-delta {css_class}">{arrow} {delta}</div>'
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """


def section_header(title: str, subtitle: str = "") -> str:
    """Generate HTML for a section header."""
    sub = f'<p class="section-subheader">{subtitle}</p>' if subtitle else ""
    return f'<div class="section-header">{title}</div>{sub}'


def insight_box(text: str) -> str:
    """Generate HTML for an insight box."""
    return f'<div class="insight-box">{text}</div>'


def alert_box(text: str, level: str = "info") -> str:
    """Generate HTML for an alert box."""
    return f'<div class="alert-box {level}">{text}</div>'


def styled_divider() -> str:
    """Generate a styled divider."""
    return '<div class="styled-divider"></div>'
