"""Brand Health Tracker — Banque des Images (photos terrain par vague)."""

import streamlit as st
import base64
from pathlib import Path
from components.styles import section_header, insight_box

APP_DIR = Path(__file__).resolve().parent.parent
PHOTO_DIR = APP_DIR / "assets" / "field_photos"

VAGUE_FOLDERS = {
    "Vague 1": "Vague_1",
    "Vague 2": "Vague_2",
    "Vague 3": "Vague_3",
}

VAGUE_META = {
    "Vague 1": {"mois": "Janvier 2026", "color": "#C0392B"},
    "Vague 2": {"mois": "Février 2026", "color": "#6C3483"},
    "Vague 3": {"mois": "Mars 2026", "color": "#2980B9"},
}

CITIES = ["Abidjan", "Bouaké", "Yamoussoukro", "San Pedro", "Daloa", "Korhogo", "Abengourou"]

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

# Préfixes courts utilisés par le terrain en début de nom de fichier
# (ex: "Abj_yop_220526.jpg" → Abidjan ; "BK_220526.jpg" → Bouaké)
CITY_PREFIXES = {
    "abj":  "Abidjan",
    "bk":   "Bouaké",
    "bke":  "Bouaké",
    "dal":  "Daloa",
    "kgo":  "Korhogo",
    "krg":  "Korhogo",
    "yak":  "Yamoussoukro",
    "yam":  "Yamoussoukro",
    "ykro": "Yamoussoukro",
    "sp":   "San Pedro",
    "sape": "San Pedro",
    "abg":  "Abengourou",
    "aben": "Abengourou",
}


def _detect_city(stem: str) -> str:
    """Return the city for a given filename stem, using prefix or substring."""
    parts = stem.split("_")
    if parts:
        head = parts[0].lower()
        if head in CITY_PREFIXES:
            return CITY_PREFIXES[head]
    # Fallback : substring matching on the full filename
    lower = stem.lower()
    for c in CITIES:
        if c.lower() in lower:
            return c
    return "—"


def _scan_local_photos(vague: str) -> list:
    """Scan local field_photos/Vague_X folder for real images."""
    folder = PHOTO_DIR / VAGUE_FOLDERS[vague]
    if not folder.exists():
        return []

    photos = []
    for f in sorted(folder.iterdir()):
        if f.suffix.lower() in IMAGE_EXTS:
            stem = f.stem
            city = _detect_city(stem)
            photos.append({
                "local_path": f,
                "caption": stem.replace("_", " ").title(),
                "city": city,
                "date": VAGUE_META[vague]["mois"],
            })
    return photos


def _img_to_b64(path: Path) -> str:
    """Convert local image to base64 for inline display."""
    suffix = path.suffix.lower().lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp", "gif": "gif"}.get(suffix, "jpeg")
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:image/{mime};base64,{data}"


def _render_photo_card(photo: dict, idx: int, vague_color: str):
    """Render a single photo card with caption."""
    img_src = _img_to_b64(photo["local_path"])

    html = f"""
    <div class="photo-card">
        <div class="photo-img-wrap">
            <img src="{img_src}" alt="{photo['caption']}" class="photo-img" />
            <div class="photo-badge" style="background:{vague_color};">#{idx:03d}</div>
        </div>
        <div class="photo-info">
            <div class="photo-caption">{photo['caption']}</div>
            <div class="photo-meta">
                <span class="photo-meta-item">📍 {photo['city']}</span>
            </div>
            <div class="photo-date">{photo['date']}</div>
        </div>
    </div>
    """
    return html


def _render_empty_state(vague: str, vague_color: str):
    """Show a clean message when no photos are available yet for a wave."""
    folder = VAGUE_FOLDERS[vague]
    st.markdown(f"""
    <div style="
        background: #FFFFFF;
        border: 2px dashed #E2E4E8;
        border-radius: 14px;
        padding: 3rem 2rem;
        text-align: center;
        margin-top: 1rem;
    ">
        <div style="font-size: 3rem; margin-bottom: 1rem;">📷</div>
        <div style="font-size: 1.1rem; font-weight: 700; color: {vague_color}; margin-bottom: 0.5rem;">
            Photos terrain non encore disponibles
        </div>
        <div style="color: #4A5568; font-size: 0.9rem; line-height: 1.5;">
            Les photos de cette vague seront affichées ici dès leur réception.<br>
            Dossier attendu&nbsp;: <code>assets/field_photos/{folder}/</code>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_wave_gallery(vague: str):
    """Render the photo gallery for a single wave."""
    meta = VAGUE_META[vague]
    vague_color = meta["color"]

    photos = _scan_local_photos(vague)

    # ── Header stats ──
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"""
        <div class="wave-header" style="border-left:4px solid {vague_color};">
            <div class="wave-title" style="color:{vague_color};">{vague}</div>
            <div class="wave-subtitle">{meta['mois']} — Collecte CAPI face-à-face</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="wave-stat">
            <div class="wave-stat-label">Photos</div>
            <div class="wave-stat-value" style="color:{vague_color};">{len(photos)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        cities_count = len(set(p["city"] for p in photos if p["city"] != "—"))
        st.markdown(f"""
        <div class="wave-stat">
            <div class="wave-stat-label">Villes couvertes</div>
            <div class="wave-stat-value" style="color:{vague_color};">{cities_count}</div>
        </div>
        """, unsafe_allow_html=True)

    if not photos:
        _render_empty_state(vague, vague_color)
        return

    # ── Filters ──
    fc1, fc2 = st.columns([2, 2])
    with fc1:
        city_filter = st.multiselect(
            "Filtrer par ville",
            sorted(set(p["city"] for p in photos if p["city"] != "—")),
            default=[],
            key=f"photo_city_{vague}",
        )
    with fc2:
        search = st.text_input(
            "Rechercher (légende, ville...)",
            "",
            key=f"photo_search_{vague}",
        )

    # Apply filters
    filtered = photos
    if city_filter:
        filtered = [p for p in filtered if p["city"] in city_filter]
    if search:
        s = search.lower()
        filtered = [
            p for p in filtered
            if s in p["caption"].lower() or s in p["city"].lower()
        ]

    if not filtered:
        st.info("Aucune photo ne correspond à vos filtres.")
        return

    # ── Gallery grid — 3 cols ──
    st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)
    cols_per_row = 3
    for i in range(0, len(filtered), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(filtered):
                with col:
                    st.markdown(
                        _render_photo_card(filtered[idx], idx + 1, vague_color),
                        unsafe_allow_html=True,
                    )


PHOTO_CSS = """
<style>
.wave-header {
    background: #FFFFFF;
    border: 1px solid #E2E4E8;
    border-radius: 14px;
    padding: 1rem 1.2rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.04);
}
.wave-title {
    font-size: 1.5rem;
    font-weight: 800;
    margin: 0;
}
.wave-subtitle {
    color: #4A5568;
    font-size: 0.9rem;
    margin-top: 0.2rem;
}
.wave-stat {
    background: #FFFFFF;
    border: 1px solid #E2E4E8;
    border-radius: 14px;
    padding: 0.8rem;
    text-align: center;
    height: 100%;
    box-shadow: 0 2px 10px rgba(0,0,0,0.04);
}
.wave-stat-label {
    color: #4A5568;
    font-size: 0.72rem;
    text-transform: uppercase;
    font-weight: 700;
    letter-spacing: 0.05em;
}
.wave-stat-value {
    font-size: 1.8rem;
    font-weight: 800;
    line-height: 1.1;
    margin-top: 0.2rem;
}

/* Photo cards */
.photo-card {
    background: #FFFFFF;
    border: 1px solid #E2E4E8;
    border-radius: 14px;
    overflow: hidden;
    margin-bottom: 1rem;
    transition: all 0.3s ease;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}
.photo-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 28px rgba(0,0,0,0.12);
    border-color: #C0392B;
}
.photo-img-wrap {
    position: relative;
    width: 100%;
    aspect-ratio: 3/2;
    overflow: hidden;
    background: #F5F6F8;
}
.photo-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    transition: transform 0.4s ease;
}
.photo-card:hover .photo-img {
    transform: scale(1.05);
}
.photo-badge {
    position: absolute;
    top: 10px;
    right: 10px;
    color: #FFFFFF;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}
.photo-info {
    padding: 0.9rem 1rem 1rem 1rem;
}
.photo-caption {
    font-size: 0.92rem;
    font-weight: 700;
    color: #1A1D23;
    line-height: 1.3;
    margin-bottom: 0.5rem;
}
.photo-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
    margin-bottom: 0.4rem;
}
.photo-meta-item {
    font-size: 0.78rem;
    color: #4A5568;
    font-weight: 500;
}
.photo-date {
    font-size: 0.72rem;
    color: #7B8794;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
    border-top: 1px dashed #E2E4E8;
    padding-top: 0.5rem;
    margin-top: 0.3rem;
}
</style>
"""


def render():
    st.markdown(PHOTO_CSS, unsafe_allow_html=True)
    st.markdown(section_header(
        "Banque des Images",
        "Photos prises sur le terrain, organisées par vague de collecte"
    ), unsafe_allow_html=True)

    # Sub-tabs per vague
    t1, t2, t3 = st.tabs([
        "Vague 1 — Janvier 2026",
        "Vague 2 — Février 2026",
        "Vague 3 — Mars 2026",
    ])

    with t1:
        _render_wave_gallery("Vague 1")
    with t2:
        _render_wave_gallery("Vague 2")
    with t3:
        _render_wave_gallery("Vague 3")
