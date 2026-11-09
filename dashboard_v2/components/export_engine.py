"""
Export Engine · rapports PPTX, PDF et Excel (niveau présentation client).

Les trois formats partagent les mêmes données (components.report_data) :
- PPTX : deck 16:9, titres formulés comme le message clé, graphiques natifs
  PowerPoint (modifiables), couleurs de marque, section Casino.
- PDF  : rapport A4 paysage, mêmes sections, graphiques vectoriels.
- Excel: classeur de données chiffrées (vraies valeurs numériques) avec
  graphiques natifs Excel et mise en forme conditionnelle.
"""

import io
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import (
    XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION, XL_TICK_MARK, XL_MARKER_STYLE,
)
from fpdf import FPDF
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

from data.loader import vague_short, keep_brands
from components.charts import brand_color
from components.report_data import (
    build_report, fr, fmt_value, fmt_delta, DEFINITIONS,
)

APP_DIR = Path(__file__).resolve().parent.parent
LOGO_BETCLIC = APP_DIR / "betclic-logo.png"
LOGO_OW = APP_DIR / "assets" / "logo_opinionway.png"

# ── Palette (encre / surfaces / statuts) ──
HEX = {
    "red": "#C0392B", "ink": "#0F172A", "ink2": "#475569", "muted": "#94A3B8",
    "line": "#E2E8F0", "soft": "#F8FAFC", "white": "#FFFFFF",
    "good": "#15803D", "good_bg": "#DCFCE7", "bad": "#B91C1C", "bad_bg": "#FEE2E2",
    "flat_bg": "#F1F5F9", "prev": "#CBD5E1",
    # Paire divergente (avance / retard vs concurrent)
    "adv": "#0F766E", "lag": "#C2410C",
    # Composition NPS (statuts)
    "prom": "#15803D", "pas": "#CBD5E1", "det": "#B91C1C",
}
FONT = "Arial"


def _rgb(h: str) -> RGBColor:
    return RGBColor.from_string(h.lstrip("#").upper())


def _brand_hex(b: str) -> str:
    return brand_color(b, default="#94A3B8")


# ═══════════════════════════════════════════════════════════════════
# PPTX
# ═══════════════════════════════════════════════════════════════════

SW, SH = Inches(13.333), Inches(7.5)
X0, XW = Inches(0.55), Inches(12.23)          # marges gauche / largeur utile
Y0 = Inches(1.62)                             # haut de la zone de contenu
YB = Inches(6.85)                             # bas de la zone de contenu


def _tx(slide, x, y, w, h, text, size=12, bold=False, color="ink", align=PP_ALIGN.LEFT,
        anchor=MSO_ANCHOR.TOP, italic=False, spacing=None):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    lines = text if isinstance(text, list) else [text]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if spacing:
            p.space_after = Pt(spacing)
        r = p.add_run()
        r.text = str(line)
        f = r.font
        f.size, f.bold, f.italic, f.name = Pt(size), bold, italic, FONT
        f.color.rgb = _rgb(HEX.get(color, color))
    return tb


def _box(slide, x, y, w, h, fill="white", line=None, rounded=False, radius=0.06):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = _rgb(HEX.get(fill, fill))
    if line:
        shp.line.color.rgb = _rgb(HEX.get(line, line))
        shp.line.width = Pt(0.75)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    if rounded:
        shp.adjustments[0] = radius
    return shp


def _slide(ctx, section, title, subtitle=""):
    s = ctx["prs"].slides.add_slide(ctx["prs"].slide_layouts[6])
    ctx["page"] += 1
    _box(s, Inches(0.55), Inches(0.42), Inches(0.06), Inches(0.66), "red")
    _tx(s, Inches(0.75), Inches(0.36), Inches(11.5), Inches(0.25), section.upper(), 10, True, "red")
    tsize = 22 if len(title) <= 68 else (19 if len(title) <= 80 else 17)
    _tx(s, Inches(0.75), Inches(0.6), Inches(12.0), Inches(0.55), title, tsize, True, "ink")
    if subtitle:
        _tx(s, Inches(0.75), Inches(1.17), Inches(12.0), Inches(0.3), subtitle, 11, False, "ink2")
    _box(s, X0, Inches(7.0), XW, Emu(9525), "line")
    _tx(s, X0, Inches(7.08), Inches(9.5), Inches(0.25), ctx["footer"], 8, False, "muted")
    _tx(s, Inches(12.28), Inches(7.08), Inches(0.5), Inches(0.25), str(ctx["page"]), 8, False, "muted",
        align=PP_ALIGN.RIGHT)
    if LOGO_OW.exists():
        s.shapes.add_picture(str(LOGO_OW), Inches(10.95), Inches(7.02), height=Inches(0.32))
    return s


def _chart_label(slide, x, y, w, text, note=""):
    _tx(slide, x, y, w, Inches(0.28), text, 12, True, "ink")
    if note:
        _tx(slide, x, y + Inches(0.27), w, Inches(0.22), note, 9, False, "muted")


def _bar(slide, x, y, w, h, categories, series, horizontal=False, stacked=False, pct_stacked=False,
         fmt='0.0', legend=True, max_val=None, min_val=0, gap=55, font=10, labels=True,
         label_pos=None):
    """series = [(nom, valeurs, couleur_hex | [couleurs par point])]."""
    cd = CategoryChartData()
    cd.categories = categories
    for name, vals, _ in series:
        cd.add_series(name, [None if v is None else float(v) for v in vals])
    if horizontal:
        ct = (XL_CHART_TYPE.BAR_STACKED_100 if pct_stacked else
              XL_CHART_TYPE.BAR_STACKED if stacked else XL_CHART_TYPE.BAR_CLUSTERED)
    else:
        ct = (XL_CHART_TYPE.COLUMN_STACKED_100 if pct_stacked else
              XL_CHART_TYPE.COLUMN_STACKED if stacked else XL_CHART_TYPE.COLUMN_CLUSTERED)
    ch = slide.shapes.add_chart(ct, x, y, w, h, cd).chart
    ch.font.size, ch.font.name = Pt(font), FONT
    ch.font.color.rgb = _rgb(HEX["ink2"])
    ch.has_title = False
    ch.has_legend = bool(legend and len(series) > 1)
    if ch.has_legend:
        ch.legend.position = XL_LEGEND_POSITION.TOP
        ch.legend.include_in_layout = False
        ch.legend.font.size = Pt(font)
    plot = ch.plots[0]
    plot.gap_width = gap
    plot.overlap = 100 if (stacked or pct_stacked) else -10
    va = ch.value_axis
    va.has_major_gridlines = False
    va.visible = False
    if not pct_stacked:
        if max_val is not None:
            va.maximum_scale = max_val
        if min_val is not None:
            va.minimum_scale = min_val
    ca = ch.category_axis
    ca.major_tick_mark = XL_TICK_MARK.NONE
    ca.format.line.color.rgb = _rgb(HEX["line"])
    ca.tick_labels.font.size = Pt(font)
    ca.tick_labels.font.color.rgb = _rgb(HEX["ink"])
    if horizontal:
        ca.reverse_order = True
    for i, (_, vals, color) in enumerate(series):
        ser = plot.series[i]
        ser.invert_if_negative = False
        if isinstance(color, list):
            for j, c in enumerate(color):
                pt = ser.points[j]
                pt.format.fill.solid()
                pt.format.fill.fore_color.rgb = _rgb(c)
        else:
            ser.format.fill.solid()
            ser.format.fill.fore_color.rgb = _rgb(color)
    if labels:
        plot.has_data_labels = True
        dl = plot.data_labels
        dl.number_format = fmt
        dl.number_format_is_linked = False
        dl.font.size = Pt(font - 1)
        dl.font.color.rgb = _rgb(HEX["white"] if (stacked or pct_stacked) else HEX["ink"])
        dl.position = label_pos or (XL_LABEL_POSITION.CENTER if (stacked or pct_stacked)
                                    else XL_LABEL_POSITION.OUTSIDE_END)
        if stacked or pct_stacked:
            for i, (_, _, color) in enumerate(series):
                if isinstance(color, str) and _is_light(color):
                    sdl = plot.series[i].data_labels
                    sdl.number_format, sdl.number_format_is_linked = fmt, False
                    sdl.show_value = True
                    sdl.position = XL_LABEL_POSITION.CENTER
                    sdl.font.size = Pt(font - 1)
                    sdl.font.color.rgb = _rgb(HEX["ink"])
    return ch


def _is_light(h: str) -> bool:
    r, g, b = (int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.65


def _line(slide, x, y, w, h, categories, series, fmt="0.0", font=10, min_val=None, max_val=None):
    cd = CategoryChartData()
    cd.categories = categories
    for name, vals, _ in series:
        cd.add_series(name, [None if v is None else float(v) for v in vals])
    ch = slide.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, x, y, w, h, cd).chart
    ch.font.size, ch.font.name = Pt(font), FONT
    ch.font.color.rgb = _rgb(HEX["ink2"])
    ch.has_title = False
    ch.has_legend = len(series) > 1
    if ch.has_legend:
        ch.legend.position = XL_LEGEND_POSITION.TOP
        ch.legend.include_in_layout = False
    va = ch.value_axis
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = _rgb(HEX["line"])
    va.format.line.fill.background()
    va.tick_labels.font.size = Pt(font - 1)
    va.tick_labels.font.color.rgb = _rgb(HEX["muted"])
    va.number_format, va.number_format_is_linked = ("0.0" if fmt == "0.00" else "0"), False
    if min_val is not None:
        va.minimum_scale = min_val
    if max_val is not None:
        va.maximum_scale = max_val
    ca = ch.category_axis
    ca.major_tick_mark = XL_TICK_MARK.NONE
    ca.format.line.color.rgb = _rgb(HEX["line"])
    lasts = {}
    for i, (_, vals, _) in enumerate(series):
        k = max((j for j, v in enumerate(vals) if v is not None), default=None)
        if k is not None:
            lasts[i] = (k, float(vals[k]))
    allv = [float(v) for _, vals, _ in series for v in vals if v is not None]
    lo = min(allv + ([min_val] if min_val is not None else [])) if allv else 0
    span = (max(allv) - lo) if allv else 1
    # Regroupe les derniers points proches (en chaîne) puis répartit les étiquettes
    # au-dessus / à droite / en dessous pour éviter qu'elles se chevauchent.
    pos = {}
    order = sorted(lasts.items(), key=lambda kv: -kv[1][1])
    clusters, cur = [], []
    for i, (k, v) in order:
        if cur and abs(lasts[cur[-1]][1] - v) < span * 0.05:
            cur.append(i)
        else:
            if cur:
                clusters.append(cur)
            cur = [i]
    if cur:
        clusters.append(cur)
    for cl in clusters:
        if len(cl) == 2:
            pos[cl[0]], pos[cl[1]] = XL_LABEL_POSITION.ABOVE, XL_LABEL_POSITION.BELOW
        elif len(cl) >= 3:
            pos[cl[0]], pos[cl[-1]] = XL_LABEL_POSITION.ABOVE, XL_LABEL_POSITION.BELOW
    for i, (_, vals, color) in enumerate(series):
        ser = ch.plots[0].series[i]
        ser.smooth = False
        ser.format.line.color.rgb = _rgb(color)
        ser.format.line.width = Pt(2.25)
        ser.marker.style = XL_MARKER_STYLE.CIRCLE
        ser.marker.size = 8
        ser.marker.format.fill.solid()
        ser.marker.format.fill.fore_color.rgb = _rgb(color)
        ser.marker.format.line.color.rgb = _rgb(HEX["white"])
        # Étiquette sur le dernier point seulement (étiquetage sélectif)
        last = max((k for k, v in enumerate(vals) if v is not None), default=None)
        if last is not None:
            dl = ser.points[last].data_label
            dl.has_text_frame = True
            dl.text_frame.text = fr(vals[last], 2 if fmt == "0.00" else 1)
            dl.position = pos.get(i, XL_LABEL_POSITION.RIGHT)
            run = dl.text_frame.paragraphs[0].runs[0]
            run.font.size, run.font.bold = Pt(font), True
            run.font.color.rgb = _rgb(HEX["ink"])
    return ch


def _table(slide, x, y, w, header, rows, widths, row_h=Inches(0.32), font=10, aligns=None,
           fills=None, colors=None, bold_rows=()):
    nr, nc = len(rows) + 1, len(header)
    gf = slide.shapes.add_table(nr, nc, x, y, w, row_h * nr)
    tbl = gf.table
    tbl.first_row = True
    tbl.horz_banding = False
    total = sum(widths)
    for i, wd in enumerate(widths):
        tbl.columns[i].width = Emu(int(w * wd / total))
    aligns = aligns or ([PP_ALIGN.LEFT] + [PP_ALIGN.CENTER] * (nc - 1))
    for r in range(nr):
        tbl.rows[r].height = row_h
        for c in range(nc):
            cell = tbl.cell(r, c)
            cell.margin_left = cell.margin_right = Inches(0.08)
            cell.margin_top = cell.margin_bottom = Inches(0.02)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            txt = header[c] if r == 0 else rows[r - 1][c]
            tf = cell.text_frame
            tf.text = "" if txt is None else str(txt)
            p = tf.paragraphs[0]
            p.alignment = aligns[c]
            run = p.runs[0] if p.runs else p.add_run()
            run.font.name, run.font.size = FONT, Pt(font if r else font - 1)
            cell.fill.solid()
            if r == 0:
                cell.fill.fore_color.rgb = _rgb(HEX["ink"])
                run.font.bold = True
                run.font.color.rgb = _rgb(HEX["white"])
            else:
                f = (fills or {}).get((r - 1, c)) or (HEX["soft"] if r % 2 == 0 else HEX["white"])
                cell.fill.fore_color.rgb = _rgb(f)
                run.font.color.rgb = _rgb((colors or {}).get((r - 1, c), HEX["ink"]))
                run.font.bold = (r - 1) in bold_rows
    return tbl


def _kpi_tile(slide, x, y, w, h, label, value, delta_txt, direction, foot="", vs=""):
    _box(slide, x, y, w, h, "white", line="line", rounded=True, radius=0.05)
    _box(slide, x, y + Inches(0.18), Inches(0.05), h - Inches(0.36), "red")
    pad = Inches(0.25)
    _tx(slide, x + pad, y + Inches(0.12), w - pad * 2, Inches(0.4), label, 10, True, "ink2")
    _tx(slide, x + pad, y + Inches(0.52), w - pad * 2, Inches(0.5), value, 26, True, "ink")
    if delta_txt:
        bg, fg, arrow = {"up": ("good_bg", "good", "▲ "), "down": ("bad_bg", "bad", "▼ "),
                         "flat": ("flat_bg", "ink2", "")}[direction]
        pill = _box(slide, x + pad, y + Inches(1.04), Inches(1.55), Inches(0.26), bg, rounded=True, radius=0.5)
        tf = pill.text_frame
        tf.margin_left = tf.margin_right = Inches(0.05)
        tf.margin_top = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = f"{arrow}{delta_txt} {vs}".strip()
        r.font.size, r.font.bold, r.font.name = Pt(9), True, FONT
        r.font.color.rgb = _rgb(HEX[fg])
    if foot:
        _tx(slide, x + pad, y + h - Inches(0.25), w - pad * 2, Inches(0.2), foot, 8, False, "muted")


def _wave_series_txt(by_wave, unit, dec):
    return "   ".join(f"{vague_short(v)} {fr(x, dec)}" for v, x in by_wave.items() if x is not None)


def _sorted_brands(d: dict, brands, top=None):
    items = sorted([(b, d.get(b)) for b in brands if d.get(b) is not None], key=lambda x: -x[1])
    return items[:top] if top else items


# ── Slides ──

def _pptx_cover(ctx, R):
    s = ctx["prs"].slides.add_slide(ctx["prs"].slide_layouts[6])
    ctx["page"] += 1
    _box(s, 0, 0, Inches(0.28), SH, "red")
    if LOGO_BETCLIC.exists():
        s.shapes.add_picture(str(LOGO_BETCLIC), Inches(0.9), Inches(0.75), height=Inches(0.6))
    if LOGO_OW.exists():
        s.shapes.add_picture(str(LOGO_OW), Inches(10.2), Inches(0.6), height=Inches(0.9))
    _tx(s, Inches(0.9), Inches(2.3), Inches(11), Inches(0.9), "Betclic Brand Pulse", 44, True, "ink")
    _tx(s, Inches(0.9), Inches(3.15), Inches(11), Inches(0.5),
        "Baromètre de santé de marque · Paris sportifs et casino en ligne · Côte d'Ivoire", 18, False, "ink2")
    _box(s, Inches(0.9), Inches(3.85), Inches(1.2), Emu(38100), "red")
    _tx(s, Inches(0.9), Inches(4.1), Inches(11), Inches(0.5), R["lv_label"], 24, True, "red")
    _tx(s, Inches(0.9), Inches(4.7), Inches(11.5), Inches(0.9), [
        f"Base {R['lv_s']} : {R['n']} répondants dont {R['n_parieurs']} parieurs et "
        f"{R['n_users']} utilisateurs principaux de Betclic",
        f"Périmètre : {R['filters']}",
    ], 12, False, "ink2", spacing=4)
    if R["provisional"]:
        pill = _box(s, Inches(0.9), Inches(5.65), Inches(4.6), Inches(0.38), "bad_bg", rounded=True, radius=0.5)
        tf = pill.text_frame
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = f"Résultats provisoires : terrain {R['lv_s']} en cours"
        r.font.size, r.font.bold, r.font.name = Pt(11), True, FONT
        r.font.color.rgb = _rgb(HEX["bad"])
    _box(s, Inches(0.28), Inches(6.85), SW - Inches(0.28), Inches(0.65), "ink")
    _tx(s, Inches(0.9), Inches(7.02), Inches(9), Inches(0.3),
        "Document confidentiel · OpinionWay Africa pour Betclic Côte d'Ivoire", 10, False, "white")
    _tx(s, Inches(9.5), Inches(7.02), Inches(3.3), Inches(0.3), f"Édité le {R['generated']}", 10, False,
        "white", align=PP_ALIGN.RIGHT)


def _pptx_synthese(ctx, R):
    s = _slide(ctx, "Synthèse", f"Les faits marquants de la {R['lv_label']}",
               f"Évolutions calculées par rapport à la {R['pv_s'] or 'vague précédente'} · "
               f"base {R['n']} répondants")
    y = Y0 + Inches(0.05)
    for i, t in enumerate(R["takeaways"]):
        circ = _box(s, X0, y, Inches(0.42), Inches(0.42), "red", rounded=True, radius=0.5)
        tf = circ.text_frame
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = str(i + 1)
        r.font.size, r.font.bold, r.font.name = Pt(13), True, FONT
        r.font.color.rgb = _rgb(HEX["white"])
        _tx(s, X0 + Inches(0.65), y + Inches(0.05), Inches(11.4), Inches(0.6), t, 14, False, "ink",
            anchor=MSO_ANCHOR.TOP)
        y += Inches(0.68)
    if R["provisional"]:
        _box(s, X0, YB - Inches(0.42), XW, Inches(0.42), "bad_bg", rounded=True, radius=0.3)
        _tx(s, X0 + Inches(0.2), YB - Inches(0.34), XW - Inches(0.4), Inches(0.3),
            f"Terrain {R['lv_s']} en cours (n = {R['n_by_wave'][R['lv']]} vs "
            f"{R['n_by_wave'][R['pv']]} en {R['pv_s']}) : résultats provisoires, la répartition par ville "
            f"n'est pas encore complète.", 11, True, "bad")


def _pptx_scorecard(ctx, R):
    vs = f"vs {R['pv_s']}" if R["pv_s"] else ""
    s = _slide(ctx, "Scorecard Betclic", f"Indicateurs clés de santé de marque · {R['lv_label']}",
               f"Valeur {R['lv_s']}, évolution {vs} et historique des vagues")
    cols, gw, gh = 3, Inches(0.22), Inches(0.2)
    tw = int((XW - gw * (cols - 1)) / cols)
    th = Inches(1.63)
    for i, k in enumerate(R["kpis"]):
        r_, c_ = divmod(i, cols)
        x = X0 + (tw + gw) * c_
        y = Y0 + (th + gh) * r_
        _kpi_tile(s, x, y, tw, th, f"{k['label']} · {k['base']}", fmt_value(k["value"], k["unit"], k["dec"]),
                  fmt_delta(k["delta"], k["unit"], k["dec"]), k["dir"],
                  _wave_series_txt(k["by_wave"], k["unit"], k["dec"]), vs)


def _pptx_evolution(ctx, R):
    K = R["K"]
    cats = [vague_short(v) for v in R["waves"]]
    s = _slide(ctx, "Tendances", "Évolution des indicateurs Betclic d'une vague à l'autre",
               "En % · les indicateurs de recommandation sont présentés à part (échelles différentes)")
    w1 = Inches(7.6)
    _chart_label(s, X0, Y0, w1, "Notoriété, usage et part de marché (%)")
    series = [(K[k]["label"], [K[k]["by_wave"].get(v) for v in R["waves"]], c) for k, c in [
        ("tom", HEX["red"]), ("penetration", "#2563EB"), ("marque_principale", "#7C3AED"),
        ("pdm_volume", "#0F766E"), ("rappel", "#D97706")]]
    _line(s, X0, Y0 + Inches(0.35), w1, Inches(4.8), cats, series, min_val=0)
    x2 = X0 + w1 + Inches(0.4)
    w2 = XW - w1 - Inches(0.4)
    _chart_label(s, x2, Y0, w2, "NPS Betclic (pts)")
    _line(s, x2, Y0 + Inches(0.35), w2, Inches(2.25), cats,
          [("NPS", [K["nps"]["by_wave"].get(v) for v in R["waves"]], HEX["red"])])
    _chart_label(s, x2, Y0 + Inches(2.7), w2, "Satisfaction Betclic (/5)")
    _line(s, x2, Y0 + Inches(3.05), w2, Inches(2.1), cats,
          [("Satisfaction", [K["satisfaction"]["by_wave"].get(v) for v in R["waves"]], "#7C3AED")],
          fmt="0.00")


def _pptx_funnel(ctx, R):
    F = R["funnel"]
    s = _slide(ctx, "Parcours client", R["titles"]["funnel"],
               "Entonnoir de conversion Betclic · base échantillon total · étapes emboîtées")
    series = []
    if F["pv"]:
        series.append((R["pv_s"], F["pv"], HEX["prev"]))
    series.append((R["lv_s"], F["lv"], HEX["red"]))
    _bar(s, X0, Y0, Inches(8.2), Inches(5.1), F["labels"], series, horizontal=True,
         fmt='0.0" %"', max_val=115, gap=45, font=11)
    # Lecture : taux de passage entre étapes
    x2 = X0 + Inches(8.6)
    _tx(s, x2, Y0 + Inches(0.1), Inches(3.6), Inches(0.3), "Taux de passage d'une étape à l'autre", 12, True)
    rows = []
    for i in range(1, len(F["lv"])):
        a, b = F["lv"][i - 1], F["lv"][i]
        rows.append([F["labels"][i], f"{fr(b / a * 100 if a else 0, 0)} %"])
    _table(s, x2, Y0 + Inches(0.5), Inches(3.6), ["Étape", f"{R['lv_s']}"], rows, [3, 1], font=10)
    _tx(s, x2, Y0 + Inches(2.35), Inches(3.6), Inches(1.2),
        "Lecture : part des répondants de l'étape précédente qui atteignent l'étape suivante.",
        9, False, "muted", italic=True)


def _pptx_comp(ctx, R):
    s = _slide(ctx, "Paysage concurrentiel", R["titles"]["comp"],
               f"{R['lv_s']} · TOM, notoriété et pénétration : échantillon total · marque principale, PDM et "
               f"rappel : parieurs")
    metrics = list(R["comp"].keys())
    series = [(b, [R["comp"][m].get(b) for m in metrics], _brand_hex(b)) for b in R["main"]]
    _bar(s, X0, Y0, XW, Inches(3.4), metrics, series, fmt='0', max_val=110, gap=70, font=10)
    rows = [[b] + [fr(R["comp"][m].get(b)) for m in metrics] for b in R["main"]]
    _table(s, X0, Y0 + Inches(3.55), XW, ["Marque (%)"] + metrics, rows, [1.6] + [1] * len(metrics),
           row_h=Inches(0.27), font=9, bold_rows=(0,),
           colors={(0, c): HEX["red"] for c in range(len(metrics) + 1)})


def _pptx_pdm(ctx, R):
    s = _slide(ctx, "Part de marché", R["titles"]["pdm"],
               f"PDM Volume = essais de la marque (Q5) / total des essais · base parieurs {R['lv_s']} "
               f"(n = {R['n_parieurs']})")
    top = _sorted_brands(R["comp"]["PDM Volume"], R["main"])
    rest = round(100 - sum(v for _, v in top), 1)
    if rest > 0.05:
        top.append(("Autres marques", rest))
    _bar(s, X0, Y0, Inches(7.4), Inches(5.1), [b for b, _ in top],
         [("PDM Volume", [v for _, v in top], [_brand_hex(b) for b, _ in top])],
         horizontal=True, fmt='0.0" %"', max_val=max(v for _, v in top) * 1.18, gap=40, font=11)
    x2 = X0 + Inches(7.9)
    _tx(s, x2, Y0 + Inches(0.1), Inches(4.3), Inches(0.3), "Évolution de la PDM Volume (%)", 12, True)
    rows = [[vague_short(v)] + [fr(R["pdm_by_wave"][b].get(v)) for b in ["Betclic", "1XBET"]]
            for v in R["waves"]]
    _table(s, x2, Y0 + Inches(0.5), Inches(4.3), ["Vague", "Betclic", "1XBET"], rows, [1, 1, 1], font=11,
           bold_rows=(len(rows) - 1,))


def _pptx_notoriete(ctx, R):
    s = _slide(ctx, "Notoriété & communication", R["titles"]["notoriete"],
               f"{R['lv_s']} · notoriété totale : échantillon total (n = {R['n']}) · rappel publicitaire "
               f"spontané : parieurs (n = {R['n_parieurs']})")
    half = Inches(5.9)
    for i, (metric, title, top) in enumerate([("Notoriété totale", "Notoriété totale (Q1A+Q1B+Q1C)", 10),
                                              ("Rappel pub", "Rappel publicitaire spontané (Q18)", 8)]):
        x = X0 + (half + Inches(0.43)) * i
        items = _sorted_brands(R["comp"][metric], R["main"])
        _chart_label(s, x, Y0, half, title)
        _bar(s, x, Y0 + Inches(0.35), half, Inches(4.8), [b for b, _ in items],
             [(metric, [v for _, v in items], [_brand_hex(b) for b, _ in items])],
             horizontal=True, fmt='0.0" %"', max_val=max(v for _, v in items) * 1.2, gap=40)


def _pptx_image(ctx, R):
    rows_img = R["image"]
    if not rows_img:
        return
    s = _slide(ctx, "Attributs fonctionnels", R["titles"]["image"],
               f"Scores moyens de 1 à 5 (Q12) parmi les utilisateurs de chaque marque · {R['lv_s']}")
    vs = R["pv_s"]
    rows, colors = [], {}
    for i, r in enumerate(rows_img):
        d = fmt_delta(r["delta"], "/5", 2) if r["delta"] is not None else ""
        rows.append([r["attr"], fr(r["betclic"], 2), d, fr(r["x1"], 2) if r["x1"] is not None else "n.d."])
        if r["delta"] is not None and abs(r["delta"]) >= 0.05:
            colors[(i, 2)] = HEX["good"] if r["delta"] > 0 else HEX["bad"]
    _table(s, X0, Y0, Inches(6.3), ["Attribut", "Betclic", f"Δ vs {vs}" if vs else "Δ", "1XBET"], rows,
           [3.2, 1, 1, 1], row_h=Inches(0.33), font=10, colors=colors)
    gaps = sorted([r for r in rows_img if r["gap"] is not None], key=lambda r: -r["gap"])
    x2 = X0 + Inches(6.7)
    _chart_label(s, x2, Y0 - Inches(0.05), Inches(5.5), "Écart Betclic moins 1XBET (points de score)",
                 "Vert sarcelle : avance de Betclic · orange : retard")
    _bar(s, x2, Y0 + Inches(0.45), Inches(5.5), Inches(4.75), [r["attr"] for r in gaps],
         [("Écart", [r["gap"] for r in gaps], [HEX["adv"] if r["gap"] >= 0 else HEX["lag"] for r in gaps])],
         horizontal=True, fmt='+0.00;-0.00;0.00', min_val=None, gap=35, font=9)


def _pptx_satisfaction(ctx, R):
    s = _slide(ctx, "Satisfaction & recommandation", R["titles"]["sat"],
               "Base : parieurs dont c'est la marque principale (Q6) · marques avec au moins 10 répondants")
    sat = R["sat"]
    if sat:
        cats = [f"{r['brand']} (n={r['n']})" for r in sat]
        _chart_label(s, X0, Y0, Inches(7), "Composition du NPS (%)")
        _bar(s, X0, Y0 + Inches(0.35), Inches(7), Inches(min(4.8, 1.2 + 1.1 * len(sat))), cats, [
            ("Promoteurs (9-10)", [r["prom"] for r in sat], HEX["prom"]),
            ("Passifs (7-8)", [r["pas"] for r in sat], HEX["pas"]),
            ("Détracteurs (0-6)", [r["det"] for r in sat], HEX["det"]),
        ], horizontal=True, pct_stacked=True, fmt='0', gap=50)
        rows = [[r["brand"], str(r["n"]), fr(r["satisfaction"], 2), fr(r["nps"])] for r in sat]
        _table(s, X0 + Inches(7.4), Y0 + Inches(0.35), Inches(4.8), ["Marque", "Base", "Satisf. /5", "NPS"],
               rows, [1.6, 0.8, 1, 1], font=11, bold_rows=(0,))
        notes = ["NPS = % promoteurs (9-10) moins % détracteurs (0-6) à la question de recommandation (Q15).",
                 "Chaque marque est évaluée par ses propres utilisateurs principaux."]
        small = [r["brand"] for r in sat if r["n"] < 30]
        if small:
            notes.append(f"Base inférieure à 30 : {', '.join(small)} (à lire avec prudence).")
        _tx(s, X0 + Inches(7.4), Y0 + Inches(0.6) + Inches(0.32) * (len(sat) + 1), Inches(4.8), Inches(1.6),
            notes, 9, False, "muted", italic=True, spacing=4)


def _pptx_verbatims(ctx, R):
    th = R["themes"]
    if not (th["detractors"].get("themes") or th["promoters"].get("themes")):
        return
    s = _slide(ctx, "Verbatims", "Ce qui motive la note de recommandation des utilisateurs Betclic",
               f"Q16 · regroupement thématique des réponses ouvertes ({R['lv_s']}, ensemble de la vague)")
    half = Inches(5.9)
    for i, (key, label, color) in enumerate([("detractors", "Détracteurs (0-6)", HEX["det"]),
                                             ("promoters", "Promoteurs (9-10)", HEX["prom"])]):
        blk = th.get(key) or {}
        themes = (blk.get("themes") or [])[:6]
        if not themes:
            continue
        x = X0 + (half + Inches(0.43)) * i
        _chart_label(s, x, Y0, half, f"{label} · n = {blk.get('n_total', 0)} verbatims")
        _bar(s, x, Y0 + Inches(0.35), half, Inches(2.9), [t["label"] for t in themes],
             [(label, [t["share_pct"] for t in themes], color)], horizontal=True, fmt='0" %"',
             max_val=max(t["share_pct"] for t in themes) * 1.25, gap=35, font=9)
        quotes = []
        for t in themes[:4]:
            q = (t.get("illustrative_quotes") or [""])[0]
            if q:
                quotes.append(f"« {q.strip()[:120]} »")
        _box(s, x, Y0 + Inches(3.4), half, Inches(1.75), "soft", rounded=True, radius=0.04)
        _tx(s, x + Inches(0.2), Y0 + Inches(3.52), half - Inches(0.4), Inches(1.6), quotes, 9.5, False, "ink2",
            italic=True, spacing=4)


def _pptx_casino(ctx, R):
    C = R["casino"]
    if not C:
        return
    # 1. Chiffres clés + entonnoir
    pdc = C["comp"]["PDM Volume casino"]
    cl = max(((b, v) for b, v in pdc.items() if b != "Betclic" and v is not None), key=lambda x: x[1],
             default=(None, None))
    t_cas = (f"Casino en ligne : {cl[0]} devance Betclic en part de marché ({fr(cl[1])} % vs "
             f"{fr(pdc.get('Betclic'))} %)" if cl[0] and cl[1] > (pdc.get("Betclic") or 0) else
             f"Casino en ligne : Betclic en tête de la part de marché ({fr(pdc.get('Betclic'))} %)")
    s = _slide(ctx, "Casino en ligne", t_cas,
               f"Section introduite en V4 · base {C['n']} répondants dont {C['n_joueurs']} joueurs casino")
    cols, gw = 3, Inches(0.18)
    tw = int((Inches(6.6) - gw * (cols - 1)) / cols)
    th = Inches(1.6)
    for i, t in enumerate(C["tiles"]):
        r_, c_ = divmod(i, cols)
        _kpi_tile(s, X0 + (tw + gw) * c_, Y0 + (th + Inches(0.18)) * r_, tw, th, t["label"],
                  fmt_value(t["value"], "%"), fmt_delta(t["delta"], "%"), t["dir"], t["base"])
    cr = C["cross"]
    _tx(s, X0, Y0 + Inches(3.6), Inches(6.6), Inches(1.5), [
        f"Passerelle paris vers casino : {fr(cr.get('taux_parieurs'))} % des parieurs Betclic "
        f"(n = {cr.get('n_parieurs')}) ont déjà joué à Betclic Casino.",
        f"Conversion de l'offre : {fr(cr.get('taux_conversion_offre'))} % de ceux qui savent que Betclic "
        f"propose du casino (n = {cr.get('n_offre')}) y ont déjà joué.",
    ], 11, False, "ink", spacing=6)
    x2 = X0 + Inches(6.95)
    F = C["funnel"]
    _chart_label(s, x2, Y0, Inches(5.3), "Entonnoir casino (% de l'échantillon total)")
    _bar(s, x2, Y0 + Inches(0.35), Inches(5.3), Inches(4.8), F["labels"],
         [("Betclic", F["Betclic"], _brand_hex("Betclic")), ("1XBET", F["1XBET"], _brand_hex("1XBET"))],
         horizontal=True, fmt='0.0" %"', max_val=118, gap=50, font=10)

    # 2. Concurrence casino
    s = _slide(ctx, "Casino en ligne", "Notoriété de l'offre, essai et préférence casino par marque",
               "Notoriété de l'offre et pénétration : échantillon total · marque principale : joueurs casino · "
               "PDM : part des essais QC4")
    metrics = list(C["comp"].keys())
    series = [(b, [C["comp"][m].get(b) for m in metrics], _brand_hex(b)) for b in C["main"]]
    _bar(s, X0, Y0, XW, Inches(3.4), metrics, series, fmt='0', max_val=max(
        max((v or 0) for v in C["comp"][m].values()) for m in metrics) * 1.2, gap=70)
    rows = [[b] + [fr(C["comp"][m].get(b)) for m in metrics] for b in C["main"]]
    _table(s, X0, Y0 + Inches(3.55), XW, ["Marque (%)"] + metrics, rows, [1.6] + [1] * len(metrics),
           row_h=Inches(0.25), font=9, bold_rows=(0,), colors={(0, c): HEX["red"] for c in range(len(metrics) + 1)})

    # 3. Profil des joueurs
    top_jeu = next(iter(C["jeux"].items()), (None, None))
    top_prat = max(C["pratique"].items(), key=lambda x: x[1], default=(None, None))
    t_prof = "Profil des joueurs casino"
    if top_jeu[0]:
        t_prof += f" : {top_jeu[0]} en tête ({fr(top_jeu[1], 0)} %)"
    if top_prat[0]:
        t_prof += f", « {top_prat[0].lower()} » pour {fr(top_prat[1], 0)} %"
    s = _slide(ctx, "Casino en ligne", t_prof,
               f"Base joueurs casino (ont déjà joué en ligne) · n = {C['n_joueurs']}")
    third = Inches(3.9)
    blocks = [("Types de jeux pratiqués (QC7, 3 réponses max)", C["jeux"], "#2563EB", True),
              ("Fréquence de jeu casino (QC6)", C["frequence"], "#7C3AED", False),
              ("Arbitrage paris sportifs / casino (QC8)", C["pratique"], "#0F766E", False)]
    for i, (title, dist, color, sort) in enumerate(blocks):
        if not dist:
            continue
        items = sorted(dist.items(), key=lambda x: -x[1]) if sort else list(dist.items())
        x = X0 + (third + Inches(0.26)) * i
        _chart_label(s, x, Y0, third, title)
        _bar(s, x, Y0 + Inches(0.4), third, Inches(4.7), [k for k, _ in items],
             [(title, [v for _, v in items], color)], horizontal=True, fmt='0" %"',
             max_val=max(v for _, v in items) * 1.3, gap=35, font=9)

    # 4. Découverte
    blk = R["themes"].get("casino") or {}
    themes = (blk.get("themes") or [])[:7]
    if themes:
        t_dec = f"Betclic Casino se découvre d'abord par « {themes[0]['label']} »"
        if len(themes) > 1:
            t_dec += f" et « {themes[1]['label']} »"
        s = _slide(ctx, "Casino en ligne", t_dec,
                   f"QC2 (question ouverte) · répondants sachant que Betclic propose du casino · "
                   f"n = {blk.get('n_total', 0)}")
        _bar(s, X0, Y0, Inches(7.4), Inches(5.1), [t["label"] for t in themes],
             [("Découverte", [t["share_pct"] for t in themes], HEX["red"])], horizontal=True, fmt='0" %"',
             max_val=max(t["share_pct"] for t in themes) * 1.25, gap=35, font=11)
        quotes = []
        for t in themes:
            if t["label"].lower().startswith(("ne sait", "sans pr")):
                continue
            for q in (t.get("illustrative_quotes") or [])[:2]:
                if q and len(quotes) < 9:
                    quotes.append(f"« {q.strip()[:110]} »")
        x2 = X0 + Inches(7.8)
        _box(s, x2, Y0, Inches(4.4), Inches(5.0), "soft", rounded=True, radius=0.03)
        _tx(s, x2 + Inches(0.25), Y0 + Inches(0.2), Inches(3.9), Inches(0.3), "Verbatims", 12, True)
        _tx(s, x2 + Inches(0.25), Y0 + Inches(0.6), Inches(3.9), Inches(4.2), quotes, 11, False, "ink2",
            italic=True, spacing=10)


def _heat(v, lo, hi):
    """Teinte séquentielle (une seule teinte, clair vers foncé) pour les tableaux."""
    if v is None or hi <= lo:
        return HEX["white"], HEX["ink"]
    t = (v - lo) / (hi - lo)
    ramp = ["#FDF2F1", "#F9D9D5", "#F2B1A9", "#E07F73", "#C0392B"]
    i = min(int(t * len(ramp)), len(ramp) - 1)
    return ramp[i], (HEX["white"] if i >= 3 else HEX["ink"])


def _geo_table_data(R):
    keys = [("tom", "Top of Mind"), ("notoriete", "Notoriété"), ("penetration", "Pénétration"),
            ("mp", "Marque principale"), ("nps", "NPS")]
    rows, fills, colors = [], {}, {}
    for j, (k, _) in enumerate(keys):
        vals = [g[k] for g in R["geo"] if g[k] is not None]
        lo, hi = (min(vals), max(vals)) if vals else (0, 0)
        for i, g in enumerate(R["geo"]):
            f, c = _heat(g[k], lo, hi)
            fills[(i, j + 2)], colors[(i, j + 2)] = f, c
    for g in R["geo"]:
        nps = fr(g["nps"]) + ("*" if g["n_users"] < 30 else "")
        rows.append([g["city"], str(g["n"]), fr(g["tom"]), fr(g["notoriete"]), fr(g["penetration"]),
                     fr(g["mp"]), nps])
    return ["Ville", "Base"] + [k[1] for k in keys], rows, fills, colors


def _pptx_geo(ctx, R):
    if not R["geo"]:
        return
    s = _slide(ctx, "Géographie", f"Performance de Betclic par ville · {R['lv_s']}",
               "En % (NPS en points) · couleur : du plus faible (clair) au plus fort (foncé) au sein de chaque colonne")
    header, rows, fills, colors = _geo_table_data(R)
    _table(s, X0, Y0, XW, header, rows, [2, 0.8, 1, 1, 1, 1.2, 1], row_h=Inches(0.42), font=11,
           fills=fills, colors=colors)
    _tx(s, X0, Y0 + Inches(0.42) * (len(rows) + 1) + Inches(0.15), XW, Inches(0.5),
        "* NPS calculé sur moins de 30 utilisateurs Betclic : à lire avec prudence. Marque principale : base parieurs.",
        9, False, "muted", italic=True)


def _pptx_methodo(ctx, R):
    s = _slide(ctx, "Méthodologie", "Dispositif, bases et définitions",
               "Enquête en face-à-face (CAPI) · 7 villes de Côte d'Ivoire · OpinionWay Africa")
    rows = [[m["vague"], m["mois"], m["dates"], str(m["n"]), str(m["parieurs"]), str(m["users"])]
            for m in R["methodo"]]
    _table(s, X0, Y0, Inches(6.4), ["Vague", "Mois", "Dates de terrain", "Base", "Parieurs", "Util. Betclic"],
           rows, [0.8, 1.2, 2, 0.8, 0.9, 1], font=10)
    notes = [
        f"Périmètre de ce rapport : {R['filters']}.",
        "Les marques absentes du questionnaire d'une vague ne sont pas comptées à 0 : elles sont exclues des "
        "comparaisons de cette vague.",
        "V4 : ajout de KifBet, Bet 360, Betwinner, 1WIN et d'une section Casino en ligne. Bet365, non déployé "
        "en Côte d'Ivoire, a été retiré ; Bet 360 est une marque distincte.",
        "Thèmes de verbatims regroupés par IA sur l'ensemble de la vague (hors filtres).",
    ]
    if R["provisional"]:
        notes.insert(0, f"Terrain {R['lv_s']} en cours : résultats provisoires.")
    _tx(s, X0, Y0 + Inches(0.32) * (len(rows) + 1) + Inches(0.3), Inches(6.4), Inches(2.5),
        [f"• {n}" for n in notes], 10, False, "ink2", spacing=5)
    x2 = X0 + Inches(6.8)
    _tx(s, x2, Y0, Inches(5.4), Inches(0.3), "Définitions des indicateurs", 12, True)
    _tx(s, x2, Y0 + Inches(0.38), Inches(5.4), Inches(4.8),
        [f"{k} : {v}" for k, v in DEFINITIONS], 9, False, "ink2", spacing=5)


def generate_pptx(df, vagues_list=None, filters_desc: str = "") -> bytes:
    R = build_report(df, vagues_list, filters_desc)
    prs = Presentation()
    prs.slide_width, prs.slide_height = SW, SH
    buf = io.BytesIO()
    if R is None:
        prs.save(buf)
        return buf.getvalue()
    ctx = {"prs": prs, "page": 0,
           "footer": f"Betclic Brand Pulse · {R['lv_label']} · Source : OpinionWay Africa"
                     + (" · Résultats provisoires" if R["provisional"] else "")}
    _pptx_cover(ctx, R)
    _pptx_synthese(ctx, R)
    _pptx_scorecard(ctx, R)
    if len(R["waves"]) > 1:
        _pptx_evolution(ctx, R)
    _pptx_funnel(ctx, R)
    _pptx_comp(ctx, R)
    _pptx_pdm(ctx, R)
    _pptx_notoriete(ctx, R)
    _pptx_image(ctx, R)
    _pptx_satisfaction(ctx, R)
    _pptx_verbatims(ctx, R)
    _pptx_casino(ctx, R)
    _pptx_geo(ctx, R)
    _pptx_methodo(ctx, R)
    prs.save(buf)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════
# PDF (A4 paysage, graphiques vectoriels)
# ═══════════════════════════════════════════════════════════════════

_PDF_REPL = {"—": "-", "–": "-", "’": "'", "‘": "'", "“": '"', "”": '"',
             "…": "...", "œ": "oe", "Œ": "OE", "→": "->", "▲": "+", "▼": "-",
             "Δ": "Delta", "≤": "<=", "≥": ">=", " ": " "}


def _lat(text) -> str:
    s = str(text)
    for k, v in _PDF_REPL.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


def _h2rgb(h):
    h = HEX.get(h, h).lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class ReportPDF(FPDF):
    W, H = 297, 210
    M = 14

    def __init__(self, R):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.R = R
        self.set_auto_page_break(False)
        self.set_margins(self.M, self.M, self.M)
        self.cover = True

    def footer(self):
        if self.cover:
            return
        self.set_draw_color(*_h2rgb("line"))
        self.set_line_width(0.3)
        self.line(self.M, self.H - 11, self.W - self.M, self.H - 11)
        self.set_xy(self.M, self.H - 9.5)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*_h2rgb("muted"))
        foot = f"Betclic Brand Pulse · {self.R['lv_label']} · Source : OpinionWay Africa"
        if self.R["provisional"]:
            foot += " · Résultats provisoires"
        self.cell(200, 4, _lat(foot))
        self.set_xy(self.W - self.M - 20, self.H - 9.5)
        self.cell(20, 4, str(self.page_no()), align="R")

    # ── primitives ──
    def txt(self, x, y, w, text, size=10, style="", color="ink", h=None, align="L"):
        self.set_xy(x, y)
        self.set_font("Helvetica", style, size)
        self.set_text_color(*_h2rgb(color))
        self.multi_cell(w, h or size * 0.45, _lat(text), align=align)
        return self.get_y()

    def box(self, x, y, w, h, fill="white", line=None, r=0):
        self.set_fill_color(*_h2rgb(fill))
        if line:
            self.set_draw_color(*_h2rgb(line))
            self.set_line_width(0.25)
        style = "DF" if line else "F"
        if r:
            self.rect(x, y, w, h, style=style, round_corners=True, corner_radius=r)
        else:
            self.rect(x, y, w, h, style=style)

    def page_title(self, section, title, subtitle=""):
        self.add_page()          # dessine le pied de page de la page précédente
        self.cover = False
        self.box(self.M, 12, 1.4, 15, "red")
        self.txt(self.M + 4, 11, 260, section.upper(), 8.5, "B", "red")
        self.txt(self.M + 4, 15.5, 265, title, 15, "B", "ink", h=7)
        if subtitle:
            self.txt(self.M + 4, 24, 265, subtitle, 8.5, "", "ink2")
        return 34

    def tile(self, x, y, w, h, label, value, delta, direction, foot=""):
        self.box(x, y, w, h, "white", line="line", r=2)
        self.box(x, y + 4, 1.1, h - 8, "red")
        self.txt(x + 5, y + 4, w - 8, label, 8.5, "B", "ink2", h=4)
        self.txt(x + 5, y + 12, w - 8, value, 22, "B", "ink", h=10)
        if delta:
            bg, fg = {"up": ("good_bg", "good"), "down": ("bad_bg", "bad"), "flat": ("flat_bg", "ink2")}[direction]
            self.box(x + 5, y + 25, 38, 6.5, bg, r=3)
            self.txt(x + 5, y + 26.2, 38, delta, 8.5, "B", fg, h=4, align="C")
        if foot:
            self.txt(x + 5, y + h - 7, w - 8, foot, 7.5, "", "muted", h=3.5)

    def hbars(self, x, y, w, items, colors, fmt=lambda v: fr(v), vmax=None, label_w=45, bar_h=7.5,
              gap=4.2, title="", note=""):
        if title:
            self.txt(x, y, w, title, 10.5, "B", "ink")
            y += 7
        if note:
            self.txt(x, y - 1, w, note, 7, "", "muted")
            y += 4
        vmax = vmax or max((v for _, v in items if v is not None), default=1) or 1
        bw = w - label_w - 16
        for i, (lab, v) in enumerate(items):
            yy = y + i * (bar_h + gap)
            self.txt(x, yy + (bar_h - 3.8) / 2, label_w - 2, lab, 8.5, "", "ink", h=3.8)
            if v is not None:
                ln = max(0.4, bw * max(v, 0) / vmax)
                c = colors[i] if isinstance(colors, list) else colors
                self.box(x + label_w, yy, ln, bar_h, c)
                self.txt(x + label_w + ln + 1.5, yy + (bar_h - 3.8) / 2, 18, fmt(v), 8.5, "B", "ink", h=3.8)
        return y + len(items) * (bar_h + gap)

    def gbars(self, x, y, w, cats, series, fmt=lambda v: fr(v, 0), vmax=None, h=72, title=""):
        """Colonnes groupées : séries = [(nom, valeurs, couleur)]."""
        if title:
            self.txt(x, y, w, title, 9.5, "B", "ink")
            y += 6
        # légende
        lx = x
        for name, _, c in series:
            self.box(lx, y + 0.8, 3, 3, c)
            self.txt(lx + 4, y + 0.4, 30, name, 7, "", "ink2", h=3.6)
            lx += 6 + self.get_string_width(_lat(name)) + 6
        y += 7
        vmax = vmax or max((v for _, vals, _ in series for v in vals if v is not None), default=1) or 1
        gw = w / len(cats)
        n = len(series)
        bw = min(6, (gw - 6) / n)
        base_y = y + h
        self.set_draw_color(*_h2rgb("line"))
        self.line(x, base_y, x + w, base_y)
        for ci, cat in enumerate(cats):
            gx = x + ci * gw + (gw - bw * n) / 2
            for si, (_, vals, c) in enumerate(series):
                v = vals[ci]
                if v is None:
                    continue
                bh = h * max(v, 0) / vmax
                self.box(gx + si * bw, base_y - bh, bw - 0.6, bh, c)
                self.set_font("Helvetica", "", 6.5)
                self.set_text_color(*_h2rgb("ink"))
                self.set_xy(gx + si * bw - 1, base_y - bh - 3.2)
                self.cell(bw + 1.4, 3, _lat(fmt(v)), align="C")
            self.txt(x + ci * gw, base_y + 1.5, gw, cat, 7.5, "B", "ink", h=3.5, align="C")
        return base_y + 10

    def table(self, x, y, widths, header, rows, row_h=8, size=9, fills=None, colors=None, bold_rows=(),
              aligns=None):
        aligns = aligns or (["L"] + ["C"] * (len(header) - 1))
        self.set_font("Helvetica", "B", size)
        self.set_fill_color(*_h2rgb("ink"))
        self.set_text_color(255, 255, 255)
        self.set_xy(x, y)
        for w_, h_, a in zip(widths, header, aligns):
            self.cell(w_, row_h, _lat(h_), fill=True, align=a)
        y += row_h
        for i, r in enumerate(rows):
            self.set_xy(x, y)
            for j, (w_, v, a) in enumerate(zip(widths, r, aligns)):
                f = (fills or {}).get((i, j)) or ("soft" if i % 2 else "white")
                self.set_fill_color(*_h2rgb(f))
                self.set_text_color(*_h2rgb((colors or {}).get((i, j), "ink")))
                self.set_font("Helvetica", "B" if i in bold_rows else "", size)
                self.cell(w_, row_h, _lat("" if v is None else v), fill=True, align=a)
            y += row_h
        return y


def generate_pdf(df, vagues_list=None, filters_desc: str = "") -> bytes:
    R = build_report(df, vagues_list, filters_desc)
    pdf = ReportPDF(R or {"lv_label": "", "provisional": False})
    if R is None:
        pdf.add_page()
        return bytes(pdf.output())
    M, W = pdf.M, pdf.W - 2 * pdf.M
    vs = f"vs {R['pv_s']}" if R["pv_s"] else ""

    # ── Couverture ──
    pdf.add_page()
    pdf.box(0, 0, 7, 210, "red")
    if LOGO_BETCLIC.exists():
        pdf.image(str(LOGO_BETCLIC), x=24, y=18, h=15)
    if LOGO_OW.exists():
        pdf.image(str(LOGO_OW), x=pdf.W - 80, y=14, h=24)
    pdf.txt(24, 62, 250, "Betclic Brand Pulse", 34, "B", "ink", h=14)
    pdf.txt(24, 80, 250, "Baromètre de santé de marque · Paris sportifs et casino en ligne · Côte d'Ivoire", 14, "",
            "ink2", h=7)
    pdf.box(24, 94, 30, 1, "red")
    pdf.txt(24, 100, 250, R["lv_label"], 20, "B", "red", h=9)
    pdf.txt(24, 114, 250, f"Base {R['lv_s']} : {R['n']} répondants dont {R['n_parieurs']} parieurs et "
                          f"{R['n_users']} utilisateurs principaux de Betclic", 10, "", "ink2", h=5)
    pdf.txt(24, 121, 250, f"Périmètre : {R['filters']}", 10, "", "ink2", h=5)
    if R["provisional"]:
        pdf.box(24, 132, 92, 8, "bad_bg", r=4)
        pdf.txt(24, 133.6, 92, f"Résultats provisoires : terrain {R['lv_s']} en cours", 9, "B", "bad", h=5,
                align="C")
    pdf.box(7, 192, 290, 18, "ink")
    pdf.txt(24, 198.5, 180, "Document confidentiel · OpinionWay Africa pour Betclic Côte d'Ivoire", 9, "", "white")
    pdf.txt(200, 198.5, 83, f"Édité le {R['generated']}", 9, "", "white", align="R")

    # ── Synthèse ──
    y = pdf.page_title("Synthèse", f"Les faits marquants de la {R['lv_label']}",
                       f"Évolutions par rapport à la {R['pv_s'] or 'vague précédente'}")
    for i, t in enumerate(R["takeaways"]):
        pdf.box(M, y + 0.5, 7, 7, "red", r=3.5)
        pdf.txt(M, y + 1.8, 7, str(i + 1), 9, "B", "white", h=4, align="C")
        y = max(pdf.txt(M + 11, y + 1, W - 11, t, 10.5, "", "ink", h=5.2), y + 8) + 4
    if R["provisional"]:
        pdf.box(M, 178, W, 9, "bad_bg", r=3)
        pdf.txt(M + 4, 180.3, W - 8, f"Terrain {R['lv_s']} en cours (n = {R['n_by_wave'][R['lv']]} vs "
                                     f"{R['n_by_wave'][R['pv']]} en {R['pv_s']}) : résultats provisoires.",
                9, "B", "bad", h=4.5)

    # ── Scorecard ──
    y = pdf.page_title("Scorecard Betclic", f"Indicateurs clés de santé de marque · {R['lv_label']}",
                       f"Valeur {R['lv_s']}, évolution {vs} et historique des vagues")
    tw, th = (W - 2 * 5) / 3, 45
    for i, k in enumerate(R["kpis"]):
        r_, c_ = divmod(i, 3)
        d = fmt_delta(k["delta"], k["unit"], k["dec"])
        pdf.tile(M + c_ * (tw + 5), y + r_ * (th + 4), tw, th, f"{k['label']} · {k['base']}",
                 fmt_value(k["value"], k["unit"], k["dec"]), f"{d} {vs}".strip() if d else "", k["dir"],
                 _wave_series_txt(k["by_wave"], k["unit"], k["dec"]))

    # ── Évolution (tableau) + funnel ──
    y = pdf.page_title("Tendances & parcours", R["titles"]["funnel"],
                       "Historique des indicateurs Betclic · entonnoir de conversion (base échantillon total)")
    header = ["Indicateur"] + [vague_short(v) for v in R["waves"]] + [f"Δ {vs}" if vs else "Δ"]
    rows, colors = [], {}
    for i, k in enumerate(R["kpis"]):
        rows.append([k["label"]] + [fr(k["by_wave"].get(v), k["dec"]) for v in R["waves"]]
                    + [fmt_delta(k["delta"], k["unit"], k["dec"])])
        if k["dir"] != "flat":
            colors[(i, len(header) - 1)] = "good" if k["dir"] == "up" else "bad"
    pdf.table(M, y, [46] + [19] * len(R["waves"]) + [24], header, rows, colors=colors, row_h=11, size=10)
    F = R["funnel"]
    fx = M + 46 + 19 * len(R["waves"]) + 24 + 12
    items = list(zip(F["labels"], F["lv"]))
    pdf.hbars(fx, y, pdf.W - M - fx, items, HEX["red"], fmt=lambda v: f"{fr(v)} %", vmax=100, label_w=38,
              bar_h=12, gap=8,
              title=f"Entonnoir Betclic {R['lv_s']} (%)",
              note=(f"{R['pv_s']} : " + " / ".join(fr(v) for v in F["pv"])) if F["pv"] else "")

    # ── Concurrence ──
    y = pdf.page_title("Paysage concurrentiel", R["titles"]["comp"],
                       "TOM, notoriété, pénétration : échantillon total · marque principale, PDM, rappel : parieurs")
    metrics = list(R["comp"].keys())
    y = pdf.gbars(M, y, W, metrics, [(b, [R["comp"][m].get(b) for m in metrics], _brand_hex(b))
                                     for b in R["main"]], vmax=100, h=85)
    rows = [[b] + [fr(R["comp"][m].get(b)) for m in metrics] for b in R["main"]]
    pdf.table(M, y + 2, [40] + [(W - 40) / len(metrics)] * len(metrics), ["Marque (%)"] + metrics, rows,
              bold_rows=(0,), colors={(0, c): "red" for c in range(len(metrics) + 1)})

    # ── PDM + notoriété ──
    y = pdf.page_title("Part de marché & notoriété", R["titles"]["pdm"],
                       f"PDM Volume : base parieurs (n = {R['n_parieurs']}) · notoriété : échantillon total "
                       f"(n = {R['n']})")
    top = _sorted_brands(R["comp"]["PDM Volume"], R["main"])
    rest = round(100 - sum(v for _, v in top), 1)
    if rest > 0.05:
        top.append(("Autres marques", rest))
    pdf.hbars(M, y, 125, top, [_brand_hex(b) for b, _ in top], fmt=lambda v: f"{fr(v)} %", label_w=32,
              bar_h=10, gap=5.5, title="PDM Volume (%)")
    items = _sorted_brands(R["comp"]["Notoriété totale"], R["main"])
    pdf.hbars(M + 140, y, W - 140, items, [_brand_hex(b) for b, _ in items], fmt=lambda v: f"{fr(v)} %",
              vmax=100, label_w=32, bar_h=9, gap=5, title="Notoriété totale (%)")

    # ── Attributs ──
    if R["image"]:
        y = pdf.page_title("Attributs fonctionnels", R["titles"]["image"],
                           f"Scores moyens de 1 à 5 (Q12) · {R['lv_s']} · écart = Betclic moins 1XBET")
        rows, colors = [], {}
        for i, r in enumerate(R["image"]):
            rows.append([r["attr"], fr(r["betclic"], 2),
                         fmt_delta(r["delta"], "/5", 2) if r["delta"] is not None else "",
                         fr(r["x1"], 2) if r["x1"] is not None else "n.d.",
                         (f"{'+' if r['gap'] >= 0 else '-'}{fr(abs(r['gap']), 2)}" if r["gap"] is not None else "")])
            if r["delta"] is not None and abs(r["delta"]) >= 0.05:
                colors[(i, 2)] = "good" if r["delta"] > 0 else "bad"
            if r["gap"] is not None:
                colors[(i, 4)] = "adv" if r["gap"] >= 0 else "lag"
        pdf.table(M, y, [70, 28, 30, 28, 34], ["Attribut", "Betclic", f"Δ {vs}" if vs else "Δ", "1XBET",
                                              "Écart vs 1XBET"], rows, row_h=9.6, size=9.5, colors=colors)

    # ── Satisfaction / NPS ──
    y = pdf.page_title("Satisfaction & recommandation", R["titles"]["sat"],
                       "Base : parieurs dont c'est la marque principale (Q6) · marques avec au moins 10 répondants")
    if R["sat"]:
        rows = [[r["brand"], str(r["n"]), fr(r["satisfaction"], 2), fr(r["nps"]), f"{fr(r['prom'])} %",
                 f"{fr(r['pas'])} %", f"{fr(r['det'])} %"] for r in R["sat"]]
        y = pdf.table(M, y, [40, 22, 28, 22, 30, 30, 30], ["Marque", "Base", "Satisf. /5", "NPS", "Promoteurs",
                                                         "Passifs", "Détracteurs"], rows, bold_rows=(0,)) + 8
    for i, (key, label, color) in enumerate([("detractors", "Principaux irritants (détracteurs)", "det"),
                                             ("promoters", "Motifs de recommandation (promoteurs)", "prom")]):
        blk = R["themes"].get(key) or {}
        themes = (blk.get("themes") or [])[:6]
        if themes:
            pdf.hbars(M + i * (W / 2 + 3), y, W / 2 - 3, [(t["label"], t["share_pct"]) for t in themes], color,
                      fmt=lambda v: f"{fr(v, 0)} %", label_w=70, bar_h=10, gap=6,
                      title=f"{label} · n = {blk.get('n_total', 0)}")

    # ── Casino ──
    C = R["casino"]
    if C:
        y = pdf.page_title("Casino en ligne", "Chiffres clés et entonnoir casino",
                           f"Section introduite en V4 · base {C['n']} répondants dont {C['n_joueurs']} joueurs casino")
        tw, th = (150 - 2 * 4) / 3, 44
        for i, t in enumerate(C["tiles"]):
            r_, c_ = divmod(i, 3)
            pdf.tile(M + c_ * (tw + 4), y + r_ * (th + 4), tw, th, t["label"], fmt_value(t["value"], "%"),
                     fmt_delta(t["delta"], "%"), t["dir"], t["base"])
        cr = C["cross"]
        pdf.txt(M, y + 2 * (th + 4) + 3, 150,
                f"Passerelle : {fr(cr.get('taux_parieurs'))} % des parieurs Betclic (n = {cr.get('n_parieurs')}) "
                f"ont déjà joué à Betclic Casino. Conversion de l'offre : {fr(cr.get('taux_conversion_offre'))} % "
                f"(n = {cr.get('n_offre')}).", 8.5, "", "ink", h=4.5)
        Fc = C["funnel"]
        pdf.gbars(M + 162, y, W - 162, ["Notoriété", "Sait (offre)", "A joué", "Principale"],
                  [("Betclic", Fc["Betclic"], _brand_hex("Betclic")), ("1XBET", Fc["1XBET"], _brand_hex("1XBET"))],
                  vmax=100, h=105, title="Entonnoir casino (% échantillon total)")

        y = pdf.page_title("Casino en ligne", "Concurrence et profil des joueurs casino",
                           "Offre et pénétration : échantillon total · marque principale, jeux, fréquence : joueurs casino")
        metrics = list(C["comp"].keys())
        y = pdf.gbars(M, y, W, metrics, [(b, [C["comp"][m].get(b) for m in metrics], _brand_hex(b))
                                         for b in C["main"]], h=55)
        third = (W - 16) / 3
        for i, (title, dist, color, srt) in enumerate([("Types de jeux (QC7)", C["jeux"], "#2563EB", True),
                                                       ("Fréquence (QC6)", C["frequence"], "#7C3AED", False),
                                                       ("Paris / casino (QC8)", C["pratique"], "#0F766E", False)]):
            if dist:
                items = sorted(dist.items(), key=lambda x: -x[1]) if srt else list(dist.items())
                pdf.hbars(M + i * (third + 8), y + 2, third, items, color, fmt=lambda v: f"{fr(v, 0)} %",
                          label_w=42, bar_h=5.6, gap=2.6, title=title)
        blk = R["themes"].get("casino") or {}
        if blk.get("themes"):
            y = pdf.page_title("Casino en ligne", "Comment Betclic Casino a été découvert",
                               f"QC2 · répondants sachant que Betclic propose du casino · n = {blk.get('n_total', 0)}")
            themes = blk["themes"][:7]
            pdf.hbars(M, y, 150, [(t["label"], t["share_pct"]) for t in themes], "red",
                      fmt=lambda v: f"{fr(v, 0)} %", label_w=55, bar_h=12, gap=7)
            qy = y + 2
            pdf.box(M + 160, y - 2, W - 160, 140, "soft", r=2)
            pdf.txt(M + 165, qy, W - 170, "Verbatims", 10.5, "B", "ink")
            qy += 8
            n_q = 0
            for t in themes:
                if t["label"].lower().startswith(("ne sait", "sans pr")):
                    continue
                for q in (t.get("illustrative_quotes") or [])[:2]:
                    if q and n_q < 9:
                        qy = pdf.txt(M + 165, qy, W - 170, f"« {q.strip()[:110]} »", 9, "I", "ink2", h=4.6) + 3.5
                        n_q += 1

    # ── Géographie ──
    if R["geo"]:
        y = pdf.page_title("Géographie", f"Performance de Betclic par ville · {R['lv_s']}",
                           "En % (NPS en points) · couleur du plus faible (clair) au plus fort (foncé) par colonne")
        header, rows, fills, colors = _geo_table_data(R)
        y = pdf.table(M, y, [55, 25, 38, 38, 38, 42, 33], header, rows, row_h=13, size=10.5, fills=fills,
                      colors=colors)
        pdf.txt(M, y + 3, W, "* NPS calculé sur moins de 30 utilisateurs Betclic : à lire avec prudence.", 7.5, "I",
                "muted")

    # ── Méthodologie ──
    y = pdf.page_title("Méthodologie", "Dispositif, bases et définitions",
                       "Enquête en face-à-face (CAPI) · 7 villes de Côte d'Ivoire · OpinionWay Africa")
    rows = [[m["vague"], m["mois"], m["dates"], str(m["n"]), str(m["parieurs"]), str(m["users"])] for m in R["methodo"]]
    y2 = pdf.table(M, y, [16, 26, 42, 16, 18, 22], ["Vague", "Mois", "Dates de terrain", "Base", "Parieurs",
                                                    "Util. Betclic"], rows)
    notes = [f"Périmètre : {R['filters']}.",
             "Marques absentes du questionnaire d'une vague : exclues des comparaisons de cette vague (pas de 0).",
             "V4 : ajout de KifBet, Bet 360, Betwinner, 1WIN et d'une section Casino. Bet365, non déployé en Côte "
             "d'Ivoire, a été retiré ; Bet 360 est une marque distincte.",
             "Thèmes de verbatims regroupés par IA sur l'ensemble de la vague (hors filtres)."]
    if R["provisional"]:
        notes.insert(0, f"Terrain {R['lv_s']} en cours : résultats provisoires.")
    for n in notes:
        y2 = pdf.txt(M, y2 + 3, 140, f"- {n}", 8, "", "ink2", h=4)
    dy = y
    pdf.txt(M + 150, dy, W - 150, "Définitions des indicateurs", 9.5, "B")
    dy += 6
    for k, v in DEFINITIONS:
        dy = pdf.txt(M + 150, dy, W - 150, f"{k} : {v}", 7.8, "", "ink2", h=3.9) + 1.6
    return bytes(pdf.output())


# ═══════════════════════════════════════════════════════════════════
# EXCEL (données chiffrées + graphiques natifs)
# ═══════════════════════════════════════════════════════════════════

def generate_excel(df, vagues_list=None, filters_desc: str = "") -> bytes:
    R = build_report(df, vagues_list, filters_desc)
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True, "nan_inf_to_errors": True})
    if R is None:
        wb.add_worksheet("Vide")
        wb.close()
        return buf.getvalue()

    base = {"font_name": "Arial", "font_size": 10, "valign": "vcenter"}

    def F(**kw):
        return wb.add_format({**base, **kw})

    f_title = F(bold=True, font_size=16, font_color=HEX["ink"])
    f_sub = F(font_color=HEX["ink2"], italic=True)
    f_sec = F(bold=True, font_size=11, font_color=HEX["red"])
    f_head = F(bold=True, font_color="#FFFFFF", bg_color=HEX["ink"], align="center", border=1,
               border_color=HEX["ink"], text_wrap=True)
    f_head_l = F(bold=True, font_color="#FFFFFF", bg_color=HEX["ink"], border=1, border_color=HEX["ink"])
    f_lab = F(border=1, border_color=HEX["line"])
    f_lab_b = F(border=1, border_color=HEX["line"], bold=True, font_color=HEX["red"])
    f_pct = F(border=1, border_color=HEX["line"], num_format='0.0%', align="center")
    f_pct_b = F(border=1, border_color=HEX["line"], num_format='0.0%', align="center", bold=True, font_color=HEX["red"])
    f_n1 = F(border=1, border_color=HEX["line"], num_format='0.0', align="center")
    f_n2 = F(border=1, border_color=HEX["line"], num_format='0.00', align="center")
    f_int = F(border=1, border_color=HEX["line"], num_format='0', align="center")
    f_d_pt = F(border=1, border_color=HEX["line"], num_format='+0.0" pt";-0.0" pt";"="', align="center")
    f_d_pts = F(border=1, border_color=HEX["line"], num_format='+0.0" pts";-0.0" pts";"="', align="center")
    f_d_2 = F(border=1, border_color=HEX["line"], num_format='+0.00;-0.00;"="', align="center")
    f_wrap = F(text_wrap=True, valign="top")
    f_warn = F(bold=True, font_color=HEX["bad"], bg_color=HEX["bad_bg"])
    f_green = F(font_color=HEX["good"])
    f_red = F(font_color=HEX["bad"])

    def sheet(name, title, sub=""):
        ws = wb.add_worksheet(name)
        ws.hide_gridlines(2)
        ws.set_landscape()
        ws.fit_to_pages(1, 0)
        ws.set_column(0, 0, 3)
        ws.write(1, 1, title, f_title)
        if sub:
            ws.write(2, 1, sub, f_sub)
        return ws

    def pct(v):
        return None if v is None else float(v) / 100

    def cond_delta(ws, rng):
        ws.conditional_format(rng, {"type": "cell", "criteria": ">", "value": 0, "format": f_green})
        ws.conditional_format(rng, {"type": "cell", "criteria": "<", "value": 0, "format": f_red})

    def chart_style(ch, title, y_title=None, legend=True):
        ch.set_title({"name": title, "name_font": {"name": "Arial", "size": 11, "bold": True, "color": HEX["ink"]}})
        ch.set_legend({"position": "top", "font": {"name": "Arial", "size": 9}} if legend else {"none": True})
        ch.set_chartarea({"border": {"none": True}})
        ch.set_plotarea({"border": {"none": True}})
        ch.set_y_axis({"major_gridlines": {"visible": True, "line": {"color": HEX["line"]}},
                       "line": {"none": True}, "num_font": {"name": "Arial", "size": 9, "color": HEX["muted"]},
                       **({"name": y_title} if y_title else {})})
        ch.set_x_axis({"num_font": {"name": "Arial", "size": 9, "color": HEX["ink"]},
                       "line": {"color": HEX["line"]}})

    waves = R["waves"]
    nw = len(waves)
    vs = f"vs {R['pv_s']}" if R["pv_s"] else ""

    # ── 1. Synthèse ──
    ws = sheet("Synthèse", f"Betclic Brand Pulse · {R['lv_label']}",
               f"Base {R['lv_s']} : {R['n']} répondants ({R['n_parieurs']} parieurs, {R['n_users']} utilisateurs "
               f"Betclic) · Périmètre : {R['filters']} · Édité le {R['generated']}")
    ws.set_column(1, 1, 30)
    ws.set_column(2, 2 + nw + 2, 12)
    r = 4
    if R["provisional"]:
        ws.merge_range(r, 1, r, 2 + nw + 1, f"Terrain {R['lv_s']} en cours : résultats provisoires "
                                           f"(n = {R['n_by_wave'][R['lv']]} vs {R['n_by_wave'][R['pv']]} en {R['pv_s']}).",
                       f_warn)
        r += 2
    ws.write(r, 1, "Faits marquants", f_sec)
    for i, t in enumerate(R["takeaways"]):
        ws.merge_range(r + 1 + i, 1, r + 1 + i, 2 + nw + 1, f"{i + 1}. {t}", f_wrap)
        ws.set_row(r + 1 + i, 30)
    r += len(R["takeaways"]) + 3
    ws.write(r, 1, "Indicateurs clés Betclic", f_sec)
    r += 1
    ws.write(r, 1, "Indicateur", f_head_l)
    for j, v in enumerate(waves):
        ws.write(r, 2 + j, vague_short(v), f_head)
    ws.write(r, 2 + nw, f"Δ {vs}" if vs else "Δ", f_head)
    ws.write(r, 3 + nw, "Base", f_head)
    ws.set_column(3 + nw, 3 + nw, 30)
    first = r + 1
    for i, k in enumerate(R["kpis"]):
        rr = first + i
        ws.write(rr, 1, k["label"], f_lab)
        for j, v in enumerate(waves):
            val = k["by_wave"].get(v)
            if k["unit"] == "%":
                ws.write(rr, 2 + j, pct(val), f_pct)
            else:
                ws.write(rr, 2 + j, val, f_n2 if k["unit"] == "/5" else f_n1)
        dfmt = {"%": f_d_pt, "pts": f_d_pts, "/5": f_d_2}[k["unit"]]
        ws.write(rr, 2 + nw, k["delta"], dfmt)
        ws.write(rr, 3 + nw, k["base"], f_lab)
    cond_delta(ws, f"{xl_col_to_name(2 + nw)}{first + 1}:{xl_col_to_name(2 + nw)}{first + len(R['kpis'])}")
    if nw > 1:
        ch = wb.add_chart({"type": "line"})
        line_colors = {"tom": HEX["red"], "penetration": "#2563EB", "marque_principale": "#7C3AED",
                       "pdm_volume": "#0F766E", "rappel": "#D97706"}
        for i, k in enumerate(R["kpis"][:7]):
            if k["key"] in line_colors:
                c = line_colors[k["key"]]
                ch.add_series({"name": ["Synthèse", first + i, 1],
                               "categories": ["Synthèse", first - 1, 2, first - 1, 1 + nw],
                               "values": ["Synthèse", first + i, 2, first + i, 1 + nw],
                               "line": {"width": 2.25, "color": c},
                               "marker": {"type": "circle", "size": 6, "fill": {"color": c},
                                          "border": {"color": "#FFFFFF"}}})
        chart_style(ch, "Évolution des indicateurs Betclic (%)")
        ch.set_y_axis({"num_format": "0%", "min": 0, "major_gridlines": {"visible": True, "line": {"color": HEX["line"]}},
                       "line": {"none": True}})
        ch.set_size({"width": 760, "height": 340})
        ws.insert_chart(first + len(R["kpis"]) + 2, 1, ch)

    # ── 2. Concurrence ──
    ws = sheet("Concurrence", f"Paysage concurrentiel · {R['lv_s']}",
               "TOM, notoriété, pénétration : échantillon total · marque principale, PDM, rappel : parieurs")
    metrics = list(R["comp"].keys())
    ws.set_column(1, 1, 18)
    ws.set_column(2, 1 + len(metrics), 16)
    ws.write(4, 1, "Marque", f_head_l)
    for j, m in enumerate(metrics):
        ws.write(4, 2 + j, m, f_head)
    brands = [b for b, _ in _sorted_brands(R["comp"]["Notoriété totale"], R["main"])]
    for i, b in enumerate(brands):
        bold = b == "Betclic"
        ws.write(5 + i, 1, b, f_lab_b if bold else f_lab)
        for j, m in enumerate(metrics):
            ws.write(5 + i, 2 + j, pct(R["comp"][m].get(b)), f_pct_b if bold else f_pct)
    ch = wb.add_chart({"type": "column"})
    for b in R["main"]:
        if b in brands:
            i = brands.index(b)
            ch.add_series({"name": ["Concurrence", 5 + i, 1],
                           "categories": ["Concurrence", 4, 2, 4, 1 + len(metrics)],
                           "values": ["Concurrence", 5 + i, 2, 5 + i, 1 + len(metrics)],
                           "fill": {"color": _brand_hex(b)}, "gap": 80})
    chart_style(ch, "Betclic vs principaux concurrents")
    ch.set_y_axis({"num_format": "0%", "min": 0, "major_gridlines": {"visible": True, "line": {"color": HEX["line"]}},
                   "line": {"none": True}})
    ch.set_size({"width": 900, "height": 360})
    ws.insert_chart(6 + len(brands), 1, ch)

    # ── 3. Historique PDM / KPIs par marque ──
    ws = sheet("Part de marché", "PDM Volume par vague", "Essais Q5 de la marque / total des essais · base parieurs")
    ws.set_column(1, 1, 14)
    ws.set_column(2, 3, 14)
    ws.write(4, 1, "Vague", f_head_l)
    ws.write(4, 2, "Betclic", f_head)
    ws.write(4, 3, "1XBET", f_head)
    for i, v in enumerate(waves):
        ws.write(5 + i, 1, vague_short(v), f_lab)
        ws.write(5 + i, 2, pct(R["pdm_by_wave"]["Betclic"].get(v)), f_pct)
        ws.write(5 + i, 3, pct(R["pdm_by_wave"]["1XBET"].get(v)), f_pct)
    ch = wb.add_chart({"type": "line"})
    for j, b in enumerate(["Betclic", "1XBET"]):
        ch.add_series({"name": ["Part de marché", 4, 2 + j], "categories": ["Part de marché", 5, 1, 4 + nw, 1],
                       "values": ["Part de marché", 5, 2 + j, 4 + nw, 2 + j],
                       "line": {"color": _brand_hex(b), "width": 2.5},
                       "marker": {"type": "circle", "size": 7, "fill": {"color": _brand_hex(b)},
                                  "border": {"color": "#FFFFFF"}},
                       "data_labels": {"value": True, "num_format": "0.0%", "position": "above"}})
    chart_style(ch, "PDM Volume : Betclic vs 1XBET")
    ch.set_y_axis({"num_format": "0%", "min": 0, "major_gridlines": {"visible": True, "line": {"color": HEX["line"]}},
                   "line": {"none": True}})
    ch.set_size({"width": 620, "height": 320})
    ws.insert_chart(4, 5, ch)

    # ── 4. Attributs ──
    if R["image"]:
        ws = sheet("Attributs", f"Attributs fonctionnels · {R['lv_s']}",
                   "Scores moyens de 1 à 5 (Q12) parmi les utilisateurs de chaque marque")
        ws.set_column(1, 1, 30)
        ws.set_column(2, 5, 14)
        hdr = ["Attribut", f"Betclic {R['lv_s']}", f"Δ {vs}" if vs else "Δ", f"1XBET {R['lv_s']}", "Écart vs 1XBET"]
        for j, h in enumerate(hdr):
            ws.write(4, 1 + j, h, f_head_l if j == 0 else f_head)
        for i, row in enumerate(R["image"]):
            ws.write(5 + i, 1, row["attr"], f_lab)
            ws.write(5 + i, 2, row["betclic"], f_n2)
            ws.write(5 + i, 3, row["delta"], f_d_2)
            ws.write(5 + i, 4, row["x1"], f_n2)
            ws.write(5 + i, 5, row["gap"], f_d_2)
        last = 4 + len(R["image"])
        cond_delta(ws, f"D6:D{last + 1}")
        cond_delta(ws, f"F6:F{last + 1}")
        ch = wb.add_chart({"type": "bar"})
        for j, (b, col) in enumerate([("Betclic", 2), ("1XBET", 4)]):
            ch.add_series({"name": b, "categories": ["Attributs", 5, 1, last, 1],
                           "values": ["Attributs", 5, col, last, col], "fill": {"color": _brand_hex(b)}, "gap": 60})
        chart_style(ch, "Betclic vs 1XBET (score /5)")
        ch.set_x_axis({"min": 1, "max": 5, "major_gridlines": {"visible": True, "line": {"color": HEX["line"]}}})
        ch.set_y_axis({"reverse": True, "num_font": {"name": "Arial", "size": 9}})
        ch.set_size({"width": 620, "height": 520})
        ws.insert_chart(4, 7, ch)

    # ── 5. Satisfaction & verbatims ──
    ws = sheet("Satisfaction NPS", f"Satisfaction et recommandation · {R['lv_s']}",
               "Base : parieurs dont c'est la marque principale (Q6) · marques avec au moins 10 répondants")
    ws.set_column(1, 1, 44)
    ws.set_column(2, 7, 13)
    hdr = ["Marque", "Base", "Satisfaction /5", "NPS", "Promoteurs", "Passifs", "Détracteurs"]
    for j, h in enumerate(hdr):
        ws.write(4, 1 + j, h, f_head_l if j == 0 else f_head)
    for i, s_ in enumerate(R["sat"]):
        bold = s_["brand"] == "Betclic"
        ws.write(5 + i, 1, s_["brand"], f_lab_b if bold else f_lab)
        ws.write(5 + i, 2, s_["n"], f_int)
        ws.write(5 + i, 3, s_["satisfaction"], f_n2)
        ws.write(5 + i, 4, s_["nps"], f_n1)
        ws.write(5 + i, 5, pct(s_["prom"]), f_pct)
        ws.write(5 + i, 6, pct(s_["pas"]), f_pct)
        ws.write(5 + i, 7, pct(s_["det"]), f_pct)
    r = 7 + len(R["sat"])
    for key, label in [("detractors", "Irritants · détracteurs Betclic (Q16)"),
                       ("promoters", "Motifs de recommandation · promoteurs Betclic (Q16)")]:
        blk = R["themes"].get(key) or {}
        ws.write(r, 1, f"{label} · n = {blk.get('n_total', 0)}", f_sec)
        ws.write(r + 1, 1, "Thème", f_head_l)
        ws.write(r + 1, 2, "Citations", f_head)
        ws.write(r + 1, 3, "% verbatims", f_head)
        ws.merge_range(r + 1, 4, r + 1, 7, "Verbatim illustratif", f_head)
        for i, t in enumerate(blk.get("themes") or []):
            ws.write(r + 2 + i, 1, t["label"], f_lab)
            ws.write(r + 2 + i, 2, t["count"], f_int)
            ws.write(r + 2 + i, 3, pct(t["share_pct"]), f_pct)
            ws.merge_range(r + 2 + i, 4, r + 2 + i, 7, (t.get("illustrative_quotes") or [""])[0], f_lab)
        r += 4 + len(blk.get("themes") or [])

    # ── 6. Casino ──
    C = R["casino"]
    if C:
        ws = sheet("Casino", "Casino en ligne (section introduite en V4)",
                   f"Base {C['n']} répondants dont {C['n_joueurs']} joueurs casino")
        ws.set_column(1, 1, 38)
        ws.set_column(2, 6, 18)
        ws.write(4, 1, "Indicateur", f_head_l)
        ws.write(4, 2, "Valeur", f_head)
        ws.write(4, 3, "Base", f_head)
        for i, t in enumerate(C["tiles"]):
            ws.write(5 + i, 1, t["label"], f_lab)
            ws.write(5 + i, 2, pct(t["value"]), f_pct)
            ws.write(5 + i, 3, t["base"], f_lab)
        cr = C["cross"]
        r = 5 + len(C["tiles"])
        ws.write(r, 1, "Parieurs Betclic ayant joué à Betclic Casino", f_lab)
        ws.write(r, 2, pct(cr.get("taux_parieurs")), f_pct)
        ws.write(r, 3, f"Parieurs Betclic (n = {cr.get('n_parieurs')})", f_lab)
        ws.write(r + 1, 1, "Conversion offre connue vers jeu", f_lab)
        ws.write(r + 1, 2, pct(cr.get("taux_conversion_offre")), f_pct)
        ws.write(r + 1, 3, f"Connaissent l'offre (n = {cr.get('n_offre')})", f_lab)
        r += 4
        metrics = list(C["comp"].keys())
        ws.write(r, 1, "Comparatif par marque", f_sec)
        ws.write(r + 1, 1, "Marque", f_head_l)
        for j, m in enumerate(metrics):
            ws.write(r + 1, 2 + j, m, f_head)
        cb = [b for b in C["main"]]
        for i, b in enumerate(cb):
            bold = b == "Betclic"
            ws.write(r + 2 + i, 1, b, f_lab_b if bold else f_lab)
            for j, m in enumerate(metrics):
                ws.write(r + 2 + i, 2 + j, pct(C["comp"][m].get(b)), f_pct_b if bold else f_pct)
        comp_r = r + 1
        ch = wb.add_chart({"type": "column"})
        for i, b in enumerate(cb):
            ch.add_series({"name": ["Casino", comp_r + 1 + i, 1],
                           "categories": ["Casino", comp_r, 2, comp_r, 1 + len(metrics)],
                           "values": ["Casino", comp_r + 1 + i, 2, comp_r + 1 + i, 1 + len(metrics)],
                           "fill": {"color": _brand_hex(b)}, "gap": 80})
        chart_style(ch, "Casino : Betclic vs concurrents")
        ch.set_y_axis({"num_format": "0%", "min": 0,
                       "major_gridlines": {"visible": True, "line": {"color": HEX["line"]}}, "line": {"none": True}})
        ch.set_size({"width": 760, "height": 340})
        ws.insert_chart(4, 8, ch)
        r = r + 3 + len(cb)
        for title, dist in [("Pratique du casino (QC3, base totale)", C["statut"]),
                            ("Types de jeux (QC7, base joueurs)", C["jeux"]),
                            ("Fréquence (QC6, base joueurs)", C["frequence"]),
                            ("Paris sportifs / casino (QC8, base joueurs)", C["pratique"])]:
            ws.write(r, 1, title, f_sec)
            for i, (k, v) in enumerate(dist.items()):
                ws.write(r + 1 + i, 1, k, f_lab)
                ws.write(r + 1 + i, 2, pct(v), f_pct)
            r += len(dist) + 3
        blk = R["themes"].get("casino") or {}
        if blk.get("themes"):
            ws.write(r, 1, f"Découverte de Betclic Casino (QC2) · n = {blk.get('n_total', 0)}", f_sec)
            ws.write(r + 1, 1, "Canal", f_head_l)
            ws.write(r + 1, 2, "Citations", f_head)
            ws.write(r + 1, 3, "%", f_head)
            ws.merge_range(r + 1, 4, r + 1, 6, "Verbatim illustratif", f_head)
            for i, t in enumerate(blk["themes"]):
                ws.write(r + 2 + i, 1, t["label"], f_lab)
                ws.write(r + 2 + i, 2, t["count"], f_int)
                ws.write(r + 2 + i, 3, pct(t["share_pct"]), f_pct)
                q = "" if t["label"].lower().startswith(("ne sait", "sans pr")) else \
                    (t.get("illustrative_quotes") or [""])[0]
                ws.merge_range(r + 2 + i, 4, r + 2 + i, 6, q, f_lab)

    # ── 7. Géographie ──
    if R["geo"]:
        ws = sheet("Géographie", f"Performance de Betclic par ville · {R['lv_s']}",
                   "En % (NPS en points) · échelle de couleur par colonne")
        ws.set_column(1, 1, 16)
        ws.set_column(2, 8, 14)
        hdr = ["Ville", "Base", "Util. Betclic", "Top of Mind", "Notoriété", "Pénétration", "Marque principale", "NPS"]
        for j, h in enumerate(hdr):
            ws.write(4, 1 + j, h, f_head_l if j == 0 else f_head)
        for i, g in enumerate(R["geo"]):
            ws.write(5 + i, 1, g["city"], f_lab)
            ws.write(5 + i, 2, g["n"], f_int)
            ws.write(5 + i, 3, g["n_users"], f_int)
            for j, k in enumerate(["tom", "notoriete", "penetration", "mp"]):
                ws.write(5 + i, 4 + j, pct(g[k]), f_pct)
            ws.write(5 + i, 8, g["nps"], f_n1)
        last = 5 + len(R["geo"])
        for col in "EFGHI":
            ws.conditional_format(f"{col}6:{col}{last}", {"type": "2_color_scale", "min_color": "#FDF2F1",
                                                          "max_color": "#E07F73"})
        ws.write(last + 1, 1, "NPS sur moins de 30 utilisateurs Betclic : à lire avec prudence.", f_sub)

    # ── 8. Méthodologie ──
    ws = sheet("Méthodologie", "Dispositif, bases et définitions",
               "Enquête en face-à-face (CAPI) · 7 villes de Côte d'Ivoire · OpinionWay Africa")
    ws.set_column(1, 1, 22)
    ws.set_column(2, 6, 16)
    hdr = ["Vague", "Mois", "Dates de terrain", "Base", "Parieurs", "Util. Betclic"]
    for j, h in enumerate(hdr):
        ws.write(4, 1 + j, h, f_head_l if j == 0 else f_head)
    for i, m in enumerate(R["methodo"]):
        for j, k in enumerate(["vague", "mois", "dates", "n", "parieurs", "users"]):
            ws.write(5 + i, 1 + j, m[k], f_int if k in ("n", "parieurs", "users") else f_lab)
    r = 7 + len(R["methodo"])
    ws.write(r, 1, "Définitions", f_sec)
    for i, (k, v) in enumerate(DEFINITIONS):
        ws.write(r + 1 + i, 1, k, f_lab_b)
        ws.merge_range(r + 1 + i, 2, r + 1 + i, 6, v, f_lab)
    r += len(DEFINITIONS) + 2
    ws.write(r, 1, "Notes", f_sec)
    notes = [f"Périmètre : {R['filters']}.",
             "Marques absentes du questionnaire d'une vague : exclues des comparaisons de cette vague.",
             "V4 : ajout de KifBet, Bet 360, Betwinner, 1WIN et d'une section Casino. Bet365, non déployé en Côte "
             "d'Ivoire, a été retiré ; Bet 360 est une marque distincte.",
             "Les pourcentages sont stockés en valeurs numériques (réutilisables dans vos propres calculs)."]
    for i, n in enumerate(notes):
        ws.merge_range(r + 1 + i, 1, r + 1 + i, 6, n, f_wrap)
        ws.set_row(r + 1 + i, 28)

    wb.close()
    return buf.getvalue()
