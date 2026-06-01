"""Custom CSS styles for the Betclic Brand Pulse Dashboard · V2 White Premium."""

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

/* ── KPI Cards · Premium Power BI style ── */
.kpi-card {
    background: #FFFFFF;
    border: 1px solid #E8EAEE;
    border-radius: 14px;
    padding: 1.3rem 1.1rem 1.15rem 1.15rem;
    text-align: left;
    position: relative;
    overflow: hidden;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 1px 2px rgba(15, 23, 42, 0.03);
    min-height: 160px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    box-sizing: border-box;
}
/* Accent bar à gauche (style Power BI cards) */
.kpi-card::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    width: 4px;
    background: linear-gradient(180deg, #C0392B 0%, #6C3483 100%);
    opacity: 0.85;
    transition: width 0.25s ease;
}
.kpi-card:hover {
    transform: translateY(-3px);
    border-color: #D5D8DD;
    box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08), 0 4px 10px rgba(192, 57, 43, 0.06);
}
.kpi-card:hover::before {
    width: 6px;
}
.kpi-value {
    font-size: clamp(1.9rem, 3.6vw, 2.7rem);
    font-weight: 800;
    color: #0F172A;
    line-height: 1.1;
    margin: 0.2rem 0 0 0;
    letter-spacing: -0.025em;
    font-variant-numeric: tabular-nums;
}
.kpi-label {
    font-size: clamp(0.65rem, 1.1vw, 0.78rem);
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 700;
    line-height: 1.3;
    margin-bottom: 0.4rem;
}
.kpi-delta {
    font-size: clamp(0.72rem, 1.05vw, 0.85rem);
    font-weight: 700;
    margin-top: 0.4rem;
    display: inline-flex;
    align-items: center;
    gap: 0.15rem;
    padding: 0.18rem 0.55rem;
    border-radius: 8px;
    width: fit-content;
}
.delta-up    { color: #15803D; background: rgba(34, 197, 94, 0.10); }
.delta-down  { color: #B91C1C; background: rgba(239, 68, 68, 0.10); }
.delta-neutral { color: #B45309; background: rgba(245, 158, 11, 0.10); }

/* ── Section Headers · premium typography with underline ── */
.section-header {
    color: #0F172A;
    font-size: 1.6rem;
    font-weight: 800;
    margin: 2.2rem 0 0.3rem 0;
    letter-spacing: -0.025em;
    position: relative;
    padding-bottom: 0.55rem;
}
.section-header::after {
    content: "";
    position: absolute;
    bottom: 0;
    left: 0;
    width: 52px;
    height: 3px;
    background: linear-gradient(90deg, #C0392B 0%, #6C3483 100%);
    border-radius: 2px;
}
.section-subheader {
    color: #64748B;
    font-size: 0.92rem;
    margin-top: 0.4rem;
    margin-bottom: 1.6rem;
    font-weight: 500;
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

/* ── Tabs · Power BI style segmented controls ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #F1F3F6;
    padding: 4px !important;
    border-radius: 12px;
    border: 1px solid #E2E5EA;
    box-shadow: inset 0 1px 2px rgba(15,23,42,0.04);
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px !important;
    padding: 8px 18px !important;
    color: #64748B;
    font-weight: 600;
    font-size: 0.88rem;
    transition: all 0.2s ease;
    border: none !important;
    margin: 0 !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #0F172A;
    background: rgba(255,255,255,0.6);
}
.stTabs [aria-selected="true"] {
    background: #FFFFFF !important;
    color: #C0392B !important;
    box-shadow: 0 2px 6px rgba(15,23,42,0.08), 0 1px 2px rgba(15,23,42,0.04);
    border-radius: 8px !important;
}
/* Tab highlight indicator (red bottom bar) */
.stTabs [aria-selected="true"]::after {
    content: "";
    display: block;
    width: 28px;
    height: 2px;
    background: linear-gradient(90deg, #C0392B 0%, #6C3483 100%);
    margin: 4px auto -2px auto;
    border-radius: 2px;
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

/* ── Metric containers · premium card style ── */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E8EAEE;
    border-radius: 14px;
    padding: 1rem 1.2rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    transition: all 0.2s ease;
}
[data-testid="stMetric"]:hover {
    box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06);
    transform: translateY(-1px);
}
[data-testid="stMetric"] label {
    color: #64748B !important;
    font-weight: 700;
    text-transform: uppercase;
    font-size: 0.72rem !important;
    letter-spacing: 0.07em;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 2rem !important;
    font-weight: 800;
    color: #0F172A !important;
    font-variant-numeric: tabular-nums;
}

/* ── Plotly charts container ── */
.stPlotlyChart {
    border-radius: 14px;
    overflow: hidden;
    background: #FFFFFF;
    border: 1px solid #EDF0F3;
    padding: 0.4rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    transition: all 0.2s ease;
    margin-bottom: 0.5rem;
}
.stPlotlyChart:hover {
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
}

/* ── Buttons (Download / Refresh / etc.) ── */
.stDownloadButton button, .stButton button {
    background: #FFFFFF;
    color: #C0392B;
    border: 1px solid #E2E5EA;
    border-radius: 10px;
    font-weight: 600;
    font-size: 0.85rem;
    padding: 0.45rem 1rem;
    transition: all 0.2s ease;
    box-shadow: 0 1px 2px rgba(15,23,42,0.04);
}
.stDownloadButton button:hover, .stButton button:hover {
    background: linear-gradient(135deg, #C0392B 0%, #6C3483 100%);
    color: #FFFFFF;
    border-color: transparent;
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(192, 57, 43, 0.18);
}

/* ── Dataframes · Power BI grid look ── */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #E8EAEE;
    box-shadow: 0 1px 3px rgba(15,23,42,0.04);
}

/* ── Multiselect / Selectbox (filters) · cleaner pills ── */
[data-baseweb="tag"] {
    background: linear-gradient(135deg, #C0392B 0%, #A93226 100%) !important;
    border-radius: 8px !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    border: none !important;
}
[data-baseweb="tag"] svg {
    color: rgba(255,255,255,0.85) !important;
}

/* ── Divider · subtle, less garish ── */
.styled-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, #E2E5EA 20%, #E2E5EA 80%, transparent 100%);
    border: none;
    margin: 2.2rem 0 1.6rem 0;
}

/* ── Block container padding (more breathing room) ── */
.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1400px;
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

/* ── Hide Streamlit defaults (header kept visible so sidebar toggle works) ── */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {background: transparent !important;}
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
    # Inject JS via components to access parent DOM (invisible iframe)
    import streamlit.components.v1 as components
    components.html(TAB_NAV_JS, height=0, width=0)


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
