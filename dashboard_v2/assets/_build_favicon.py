"""Generate a combined Betclic × OpinionWay favicon for the dashboard.

Run once after either logo changes. Produces favicon.png (256x256) at the
project root, used by st.set_page_config(page_icon=...).
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent.parent  # dashboard_v2/
BETCLIC = HERE / "betclic-logo.png"
OW = HERE / "Opinionway-logo.png"
OUT = HERE / "favicon.png"

CANVAS = 256          # output size (browsers downscale to 16-64px)
PAD = 16              # padding around content
GAP = 12              # space between the two logos
SEP_COLOR = "#1A1D23"  # dark slate for separator dot/cross


def load_trimmed(path: Path) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    # Trim transparent borders if any
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    return img


def fit_height(img: Image.Image, target_h: int) -> Image.Image:
    """Resize image keeping aspect ratio so height == target_h."""
    w, h = img.size
    new_w = max(1, int(round(w * (target_h / h))))
    return img.resize((new_w, target_h), Image.LANCZOS)


def main():
    betclic = load_trimmed(BETCLIC)
    ow = load_trimmed(OW)

    inner_h = CANVAS - 2 * PAD
    betclic_r = fit_height(betclic, inner_h)
    ow_r = fit_height(ow, inner_h)

    # Compute composite width
    composite_w = betclic_r.width + GAP + ow_r.width

    # If composite is wider than canvas - 2*PAD, scale down proportionally
    max_inner_w = CANVAS - 2 * PAD
    if composite_w > max_inner_w:
        scale = max_inner_w / composite_w
        new_h = int(round(inner_h * scale))
        betclic_r = fit_height(betclic, new_h)
        ow_r = fit_height(ow, new_h)
        composite_w = betclic_r.width + GAP + ow_r.width
    else:
        new_h = inner_h

    # Create transparent canvas
    canvas = Image.new("RGBA", (CANVAS, CANVAS), (255, 255, 255, 0))

    # Center horizontally and vertically
    x_start = (CANVAS - composite_w) // 2
    y_start = (CANVAS - new_h) // 2

    canvas.paste(betclic_r, (x_start, y_start), betclic_r)
    canvas.paste(ow_r, (x_start + betclic_r.width + GAP, y_start), ow_r)

    # Optional separator: a small grey dot between logos
    draw = ImageDraw.Draw(canvas)
    dot_x = x_start + betclic_r.width + GAP // 2
    dot_y = CANVAS // 2
    r = 3
    draw.ellipse((dot_x - r, dot_y - r, dot_x + r, dot_y + r), fill=SEP_COLOR + "AA")

    canvas.save(OUT, "PNG")
    print(f"Favicon saved: {OUT}  ({CANVAS}x{CANVAS})")


if __name__ == "__main__":
    main()
