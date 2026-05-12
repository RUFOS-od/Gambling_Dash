"""Custom CSS styles for the Betclic Brand Pulse Dashboard — V2 White Premium."""

CUSTOM_CSS = """
<style>
/* ── Global ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #FFFFFF 0%, #F5F6F8 100%);
    border-right: 1px solid #E8E9ED;
}

[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label {
    color: #2C3E50;
    font-weight: 600;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* ── KPI Cards ── */
.kpi-card {
    background: #FFFFFF;
    border: 1px solid #E2E4E8;
    border-radius: 16px;
    padding: 1.4rem 1rem;
    text-align: center;
    transition: all 0.3s ease;
    box-shadow: 0 2px 12px rgba(0,0,0,0.05);
    min-height: 160px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
}
.kpi-card:hover {
    border-color: #C0392B;
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(192,57,43,0.12);
}
.kpi-value {
    font-size: clamp(1.8rem, 3.5vw, 2.6rem);
    font-weight: 800;
    color: #1A1D23;
    line-height: 1.15;
    margin: 0.3rem 0;
}
.kpi-label {
    font-size: clamp(0.65rem, 1.2vw, 0.8rem);
    color: #4A5568;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 700;
    line-height: 1.3;
    min-height: 1.6em;
    display: flex;
    align-items: center;
    justify-content: center;
}
.kpi-delta {
    font-size: clamp(0.7rem, 1.1vw, 0.88rem);
    font-weight: 700;
    margin-top: 0.25rem;
}
.delta-up { color: #1D8348; }
.delta-down { color: #C0392B; }
.delta-neutral { color: #D4760A; }

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
    color: #5A6676;
    font-size: 0.95rem;
    margin-top: -0.8rem;
    margin-bottom: 1.5rem;
}

/* ── Insight Boxes ── */
.insight-box {
    background: linear-gradient(135deg, rgba(192,57,43,0.04) 0%, rgba(108,52,131,0.04) 100%);
    border-left: 4px solid #C0392B;
    border-radius: 0 12px 12px 0;
    padding: 1rem 1.2rem;
    margin: 1rem 0;
    font-size: 0.9rem;
    color: #2C3E50;
    line-height: 1.5;
}
.insight-box strong {
    color: #C0392B;
}

/* ── Alert Box ── */
.alert-box {
    background: rgba(231, 76, 60, 0.05);
    border: 1px solid rgba(231, 76, 60, 0.2);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin: 0.8rem 0;
    font-size: 0.85rem;
    color: #2C3E50;
}
.alert-box.warning {
    background: rgba(243, 156, 18, 0.05);
    border-color: rgba(243, 156, 18, 0.25);
}
.alert-box.success {
    background: rgba(39, 174, 96, 0.05);
    border-color: rgba(39, 174, 96, 0.25);
}

/* ── Competitor Cards ── */
.competitor-card {
    background: #FFFFFF;
    border: 1px solid #E8E9ED;
    border-radius: 16px;
    padding: 1.2rem;
    text-align: center;
    transition: all 0.3s ease;
}
.competitor-card:hover {
    border-color: #6C3483;
    box-shadow: 0 8px 24px rgba(108,52,131,0.08);
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 2px solid #E8E9ED;
}
.stTabs [data-baseweb="tab"] {
    background-color: transparent;
    border-radius: 8px 8px 0 0;
    padding: 8px 16px;
    color: #4A5568;
    font-weight: 600;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #C0392B 0%, #6C3483 100%);
    color: white !important;
    border-radius: 8px;
}

/* ── Horizontal scroll for tabs with nav arrows ── */
.stTabs {
    position: relative;
}
.stTabs [data-baseweb="tab-list"] {
    overflow-x: auto !important;
    scroll-behavior: smooth;
    scrollbar-width: none;
    -ms-overflow-style: none;
    padding: 0 40px !important;
    flex-wrap: nowrap !important;
}
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
    display: none;
}
.stTabs [data-baseweb="tab"] {
    flex-shrink: 0 !important;
    white-space: nowrap;
}

/* Nav arrow buttons injected via JS */
.tab-nav-arrow {
    position: absolute;
    top: 0;
    height: 40px;
    width: 34px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid #E2E4E8;
    border-radius: 50%;
    cursor: pointer;
    z-index: 10;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    transition: all 0.2s ease;
    color: #C0392B;
    font-size: 1.2rem;
    font-weight: 700;
    user-select: none;
    top: 2px;
}
.tab-nav-arrow:hover {
    background: linear-gradient(135deg, #C0392B, #6C3483);
    color: #FFFFFF;
    border-color: transparent;
    transform: scale(1.1);
    box-shadow: 0 4px 12px rgba(192, 57, 43, 0.25);
}
.tab-nav-arrow.tab-nav-left {
    left: 0;
}
.tab-nav-arrow.tab-nav-right {
    right: 0;
}
.tab-nav-arrow.hidden {
    opacity: 0;
    pointer-events: none;
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
    background: #FFFFFF;
    border: 1px solid #E8E9ED;
    border-radius: 16px;
    padding: 1rem 1.2rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
[data-testid="stMetric"] label {
    color: #4A5568 !important;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.75rem !important;
    letter-spacing: 0.05em;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 2rem !important;
    font-weight: 800;
    color: #1A1D23 !important;
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
}
.sidebar-logo-x {
    color: #B0B8C1;
    font-size: 1rem;
    font-weight: 300;
}
.sidebar-logo-ow {
    height: 30px;
    width: auto;
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
    color: #4A5568;
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
    background: #F5F6F8;
    border: 1px solid #E8E9ED;
    border-radius: 10px;
    padding: 0.6rem 1rem;
    cursor: pointer;
    transition: all 0.2s ease;
    font-weight: 600;
    font-size: 0.88rem;
    color: #2C3E50;
}
[data-testid="stSidebar"] .stRadio > div > label:hover {
    border-color: rgba(192,57,43,0.4);
    background: rgba(192,57,43,0.04);
}
[data-testid="stSidebar"] .stRadio > div > label[data-checked="true"],
[data-testid="stSidebar"] .stRadio > div > label:has(input:checked) {
    background: linear-gradient(135deg, rgba(192,57,43,0.08), rgba(108,52,131,0.08));
    border-color: #C0392B;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid #E8E9ED;
    border-radius: 12px;
    overflow: hidden;
}

/* ── Hide Streamlit defaults ── */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""


TAB_NAV_JS = """
<script>
(function() {
    function setupTabNav() {
        // Find all tab-list containers in parent document (Streamlit iframe context)
        const doc = window.parent.document;
        const tabLists = doc.querySelectorAll('.stTabs [data-baseweb="tab-list"]');

        tabLists.forEach(function(list) {
            if (list.dataset.navInit === '1') return;
            list.dataset.navInit = '1';

            const wrapper = list.closest('.stTabs');
            if (!wrapper) return;

            // Create left arrow
            const leftBtn = doc.createElement('button');
            leftBtn.className = 'tab-nav-arrow tab-nav-left';
            leftBtn.innerHTML = '&#x2039;';
            leftBtn.type = 'button';
            leftBtn.setAttribute('aria-label', 'Défiler vers la gauche');

            // Create right arrow
            const rightBtn = doc.createElement('button');
            rightBtn.className = 'tab-nav-arrow tab-nav-right';
            rightBtn.innerHTML = '&#x203A;';
            rightBtn.type = 'button';
            rightBtn.setAttribute('aria-label', 'Défiler vers la droite');

            wrapper.appendChild(leftBtn);
            wrapper.appendChild(rightBtn);

            function updateArrows() {
                const maxScroll = list.scrollWidth - list.clientWidth;
                if (maxScroll <= 2) {
                    leftBtn.classList.add('hidden');
                    rightBtn.classList.add('hidden');
                    return;
                }
                if (list.scrollLeft <= 2) {
                    leftBtn.classList.add('hidden');
                } else {
                    leftBtn.classList.remove('hidden');
                }
                if (list.scrollLeft >= maxScroll - 2) {
                    rightBtn.classList.add('hidden');
                } else {
                    rightBtn.classList.remove('hidden');
                }
            }

            leftBtn.addEventListener('click', function() {
                list.scrollBy({ left: -200, behavior: 'smooth' });
            });
            rightBtn.addEventListener('click', function() {
                list.scrollBy({ left: 200, behavior: 'smooth' });
            });
            list.addEventListener('scroll', updateArrows);
            window.addEventListener('resize', updateArrows);

            // Initial update
            setTimeout(updateArrows, 100);
            setTimeout(updateArrows, 500);
        });
    }

    // Re-run periodically because Streamlit re-renders the DOM
    setupTabNav();
    setInterval(setupTabNav, 1000);
})();
</script>
"""


def inject_css():
    """Inject custom CSS and tab navigation JS into the Streamlit app."""
    import streamlit as st
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    # Inject JS via iframe to access parent DOM
    st.iframe(TAB_NAV_JS, height=0, width=0)


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
