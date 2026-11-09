"""Données communes aux exports PPTX / PDF / Excel.

Tous les chiffres des rapports sont calculés ici, une seule fois, avec les
mêmes fonctions que le dashboard (data.loader). Les trois formats ne font que
mettre en forme ce dictionnaire : un chiffre ne peut donc pas différer d'un
format à l'autre ni du dashboard.
"""

import datetime
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd

from data.loader import (
    sort_vagues, vague_short, VAGUE_LABELS, VAGUE_MONTHS, CITIES,
    get_main_competitors, get_casino_main_brands, keep_brands,
    get_parieurs, brands_in_scope, load_verbatim_themes,
    calc_tom, calc_notoriete_totale, calc_penetration, calc_consideration,
    calc_marque_principale, calc_pdm_volume, calc_rappel_campagne, calc_satisfaction, calc_nps,
    calc_kpi_by_vague, calc_kpi_by_city, calc_funnel,
    calc_tom_all_brands, calc_notoriete_all_brands, calc_penetration_all_brands,
    calc_marque_principale_all, calc_pdm_volume_all_brands, calc_rappel_campagne_all_brands,
    calc_image_scores, calc_nps_by_brand,
    get_casino_base, get_casino_joueurs,
    calc_casino_penetration, calc_casino_penetration_active,
    calc_casino_offre_notoriete, calc_casino_offre_notoriete_all,
    calc_casino_penetration_brand, calc_casino_penetration_all,
    calc_casino_marque_principale, calc_casino_marque_principale_all,
    calc_casino_pdm_volume, calc_casino_pdm_volume_all,
    calc_casino_frequence, calc_casino_jeux, calc_casino_pratique, calc_casino_statut,
    calc_casino_funnel, calc_casino_cross_sell,
)


# (clé, libellé, fonction, unité, décimales, base)
KPI_DEFS = [
    ("tom", "Top of Mind", calc_tom, "%", 1, "Échantillon total"),
    ("notoriete", "Notoriété totale", calc_notoriete_totale, "%", 1, "Échantillon total"),
    ("penetration", "Pénétration", calc_penetration, "%", 1, "Échantillon total"),
    ("consideration", "Considération", calc_consideration, "%", 1, "Parieurs"),
    ("marque_principale", "Marque principale", calc_marque_principale, "%", 1, "Parieurs"),
    ("pdm_volume", "PDM Volume", calc_pdm_volume, "%", 1, "Essais Q5 des parieurs"),
    ("rappel", "Rappel publicitaire", calc_rappel_campagne, "%", 1, "Parieurs"),
    ("satisfaction", "Satisfaction", calc_satisfaction, "/5", 2, "Utilisateurs principaux Betclic"),
    ("nps", "NPS", lambda d: calc_nps(d)["nps"], "pts", 1, "Utilisateurs principaux Betclic"),
]

FUNNEL_SHORT = ["Notoriété totale", "Notoriété spontanée", "Considération",
                "Pénétration (essai)", "Marque principale"]

DEFINITIONS = [
    ("Top of Mind", "Marque citée en premier spontanément (Q1A). Base : échantillon total."),
    ("Notoriété totale", "Citée en Q1A, Q1B ou reconnue en Q1C. Base : échantillon total."),
    ("Pénétration", "A déjà parié sur la marque (Q5). Base : échantillon total."),
    ("Considération", "A déjà parié sur la marque (Q5) ou parierait probablement avec Betclic (Q13). Base : parieurs."),
    ("Marque principale", "Marque la plus utilisée pour parier (Q6). Base : parieurs."),
    ("PDM Volume", "Essais de la marque (Q5) / total des essais toutes marques. Base : parieurs."),
    ("Rappel publicitaire", "Marque citée spontanément pour une publicité vue le mois dernier (Q18). Base : parieurs."),
    ("Satisfaction", "Satisfaction globale de 1 à 5 (Q14). Base : utilisateurs dont c'est la marque principale."),
    ("NPS", "% promoteurs (9-10) moins % détracteurs (0-6) à la Q15. Même base que la satisfaction."),
    ("Casino", "QC1 notoriété de l'offre et QC4 pénétration : échantillon total. QC5 à QC8 : joueurs casino."),
]


# ── Mise en forme française ─────────────────────────────────────────

def fr(v, dec=1) -> str:
    """Nombre au format français, arrondi « demi supérieur » comme PowerPoint et Excel
    (le format Python arrondit 8,5 à 8 ; les graphiques natifs l'affichent 9)."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "n.d."
    q = Decimal(str(float(v))).quantize(Decimal(1).scaleb(-dec), rounding=ROUND_HALF_UP)
    return f"{q:.{dec}f}".replace(".", ",")


def fmt_value(v, unit, dec=1) -> str:
    if v is None:
        return "n.d."
    if unit == "%":
        return f"{fr(v, dec)} %"
    if unit == "/5":
        return f"{fr(v, dec)}/5"
    if unit == "pts":
        return f"{fr(v, dec)} pts"
    return fr(v, dec)


def fmt_delta(d, unit, dec=1) -> str:
    if d is None:
        return ""
    if abs(d) < 0.5 * 10 ** (-dec):
        return "="
    u = {"%": " pt", "pts": " pts", "/5": ""}.get(unit, "")
    return f"{'+' if d > 0 else '-'}{fr(abs(d), dec)}{u}"


def delta_dir(d, threshold) -> str:
    if d is None or abs(d) < threshold:
        return "flat"
    return "up" if d > 0 else "down"


def _f(v):
    return None if v is None else float(v)


# ── Construction du rapport ────────────────────────────────────────

def build_report(df: pd.DataFrame, vagues_list=None, filters_desc: str = ""):
    waves = sort_vagues(df["Vague"].dropna().unique().tolist()) if len(df) else []
    if not waves:
        return None
    lv = waves[-1]
    pv = waves[-2] if len(waves) > 1 else None
    d_lv = df[df["Vague"] == lv]
    d_pv = df[df["Vague"] == pv] if pv else None

    R = {
        "waves": waves, "lv": lv, "pv": pv,
        "lv_s": vague_short(lv), "pv_s": vague_short(pv) if pv else "",
        "lv_label": VAGUE_LABELS.get(lv, lv), "lv_month": VAGUE_MONTHS.get(lv, ""),
        "filters": filters_desc or "Aucun filtre (échantillon complet)",
        "generated": datetime.date.today().strftime("%d/%m/%Y"),
        "n": len(d_lv), "n_parieurs": len(get_parieurs(d_lv)),
        "n_users": int(d_lv["Utilise_Betclic"].sum()),
    }
    R["n_by_wave"] = {v: int((df["Vague"] == v).sum()) for v in waves}
    R["provisional"] = bool(pv and R["n_by_wave"][lv] < 0.8 * R["n_by_wave"][pv])

    # Méthodologie : tailles et dates de terrain
    meth = []
    for v in waves:
        d = df[df["Vague"] == v]
        dates = pd.to_datetime(d.get("Date_Interview"), errors="coerce").dropna()
        meth.append({
            "vague": vague_short(v), "mois": VAGUE_MONTHS.get(v, ""),
            "dates": (f"{dates.min():%d/%m} au {dates.max():%d/%m/%Y}" if len(dates) else ""),
            "n": len(d), "parieurs": len(get_parieurs(d)), "users": int(d["Utilise_Betclic"].sum()),
        })
    R["methodo"] = meth

    # ── KPIs Betclic par vague ──
    kpis = []
    for key, label, fn, unit, dec, base in KPI_DEFS:
        by_v = {v: _f(x) for v, x in calc_kpi_by_vague(df, fn).items() if v in waves}
        latest = by_v.get(lv)
        prev = by_v.get(pv) if pv else None
        delta = round(latest - prev, dec) if (latest is not None and prev is not None) else None
        thr = 0.05 if unit == "/5" else 0.5
        kpis.append({
            "key": key, "label": label, "unit": unit, "dec": dec, "base": base,
            "value": latest, "prev": prev, "delta": delta, "dir": delta_dir(delta, thr),
            "by_wave": by_v,
        })
    R["kpis"] = kpis
    K = {k["key"]: k for k in kpis}
    R["K"] = K

    # ── Funnel ──
    f_lv = calc_funnel(d_lv)
    R["funnel"] = {"labels": FUNNEL_SHORT, "lv": [_f(x) for x in f_lv.values()]}
    R["funnel"]["pv"] = [_f(x) for x in calc_funnel(d_pv).values()] if pv else None

    # ── Concurrence (vague la plus récente) ──
    comp = {
        "Top of Mind": calc_tom_all_brands(d_lv),
        "Notoriété totale": calc_notoriete_all_brands(d_lv),
        "Pénétration": calc_penetration_all_brands(d_lv),
        "Marque principale": calc_marque_principale_all(d_lv),
        "PDM Volume": calc_pdm_volume_all_brands(d_lv),
        "Rappel pub": calc_rappel_campagne_all_brands(d_lv),
    }
    R["comp"] = {m: {b: _f(v) for b, v in d.items()} for m, d in comp.items()}
    R["brands_scope"] = brands_in_scope(d_lv)
    # Principaux concurrents recalculés sur le périmètre (Betclic + 4)
    R["main"] = get_main_competitors(df)
    R["pdm_by_wave"] = {
        b: {v: _f(x) for v, x in calc_kpi_by_vague(df, calc_pdm_volume, brand=b).items()}
        for b in ["Betclic", "1XBET"]
    }

    # ── Attributs fonctionnels ──
    img = calc_image_scores(d_lv)
    img_prev = calc_image_scores(d_pv) if pv else {}
    img_x = calc_image_scores(d_lv, "1XBET")
    rows = []
    for a, s in sorted(img.items(), key=lambda x: -x[1]):
        p = img_prev.get(a)
        x = img_x.get(a)
        rows.append({
            "attr": a, "betclic": float(s),
            "delta": round(float(s) - float(p), 2) if p is not None else None,
            "x1": float(x) if x is not None else None,
            "gap": round(float(s) - float(x), 2) if x is not None else None,
        })
    R["image"] = rows

    # ── Satisfaction / NPS par marque ──
    sat_rows = []
    for b in R["main"]:
        nb = calc_nps_by_brand(d_lv, b)
        if nb["n"] >= 10:
            sat_rows.append({
                "brand": b, "n": nb["n"], "satisfaction": _f(calc_satisfaction(d_lv, b)),
                "nps": _f(nb["nps"]), "prom": _f(nb["promoteurs"]),
                "pas": _f(nb["passifs"]), "det": _f(nb["detracteurs"]),
            })
    R["sat"] = sat_rows

    themes = load_verbatim_themes(lv) or {}
    R["themes"] = {
        "detractors": (themes.get("detractors") or {}),
        "promoters": (themes.get("promoters") or {}),
        "casino": (themes.get("casino_decouverte") or {}),
    }

    # ── Géographie ──
    geo = []
    tom_c = calc_kpi_by_city(d_lv, calc_tom)
    not_c = calc_kpi_by_city(d_lv, calc_notoriete_totale)
    pen_c = calc_kpi_by_city(d_lv, calc_penetration)
    mp_c = calc_kpi_by_city(d_lv, calc_marque_principale)
    for c in CITIES:
        sub = d_lv[d_lv["Ville"] == c]
        if not len(sub):
            continue
        nb = calc_nps(sub)
        geo.append({
            "city": c, "n": len(sub), "n_users": int(sub["Utilise_Betclic"].sum()),
            "tom": _f(tom_c.get(c)), "notoriete": _f(not_c.get(c)),
            "penetration": _f(pen_c.get(c)), "mp": _f(mp_c.get(c)), "nps": _f(nb["nps"]),
        })
    R["geo"] = geo

    # ── Casino ──
    R["casino"] = _build_casino(df, d_lv)

    R["takeaways"] = _takeaways(R)
    R["titles"] = _action_titles(R)
    return R


def _build_casino(df, d_lv):
    if not len(get_casino_base(d_lv)):
        return None
    cw = sort_vagues(get_casino_base(df)["Vague"].dropna().unique().tolist())
    d_cas = df[df["Vague"].isin(cw)]
    C = {"n": len(get_casino_base(d_lv)), "n_joueurs": len(get_casino_joueurs(d_lv)),
         "main": get_casino_main_brands(d_lv)}
    tiles = [
        ("Ont déjà joué au casino en ligne", calc_casino_penetration, {}, "Échantillon total"),
        ("Joueurs actifs (6 derniers mois)", calc_casino_penetration_active, {}, "Échantillon total"),
        ("Notoriété de l'offre Betclic Casino", calc_casino_offre_notoriete, {"brand": "Betclic"}, "Échantillon total"),
        ("Pénétration Betclic Casino", calc_casino_penetration_brand, {"brand": "Betclic"}, "Échantillon total"),
        ("Marque casino principale : Betclic", calc_casino_marque_principale, {"brand": "Betclic"}, "Joueurs casino"),
        ("PDM Volume casino Betclic", calc_casino_pdm_volume, {"brand": "Betclic"}, "Essais casino QC4"),
    ]
    out = []
    for label, fn, kw, base in tiles:
        by_v = {v: _f(x) for v, x in calc_kpi_by_vague(d_cas, fn, **kw).items() if v in cw}
        vals = [by_v[v] for v in cw if by_v.get(v) is not None]
        latest = vals[-1] if vals else None
        prev = vals[-2] if len(vals) > 1 else None
        delta = round(latest - prev, 1) if prev is not None else None
        out.append({"label": label, "value": latest, "delta": delta, "dir": delta_dir(delta, 0.5),
                    "unit": "%", "dec": 1, "base": base})
    C["tiles"] = out
    C["cross"] = calc_casino_cross_sell(d_lv, "Betclic")
    fb, fx = calc_casino_funnel(d_lv, "Betclic"), calc_casino_funnel(d_lv, "1XBET")
    C["funnel"] = {"labels": ["Notoriété de la marque", "Sait qu'elle propose du casino",
                              "A déjà joué à son casino", "Marque casino principale"],
                   "Betclic": [_f(x) for x in fb.values()], "1XBET": [_f(x) for x in fx.values()]}
    C["comp"] = {
        "Notoriété de l'offre": {b: _f(v) for b, v in calc_casino_offre_notoriete_all(d_lv).items()},
        "Pénétration casino": {b: _f(v) for b, v in calc_casino_penetration_all(d_lv).items()},
        "Marque casino principale": {b: _f(v) for b, v in calc_casino_marque_principale_all(d_lv).items()},
        "PDM Volume casino": {b: _f(v) for b, v in calc_casino_pdm_volume_all(d_lv).items()},
    }
    C["statut"] = calc_casino_statut(d_lv)
    C["frequence"] = calc_casino_frequence(d_lv)
    C["jeux"] = calc_casino_jeux(d_lv)
    C["pratique"] = calc_casino_pratique(d_lv)
    return C


# ── Textes générés à partir des données ─────────────────────────────

def _leader(scores: dict, exclude="Betclic"):
    items = [(b, v) for b, v in scores.items() if b != exclude and v is not None]
    return max(items, key=lambda x: x[1]) if items else (None, None)


def _verb(d, thr):
    if d is None or abs(d) < thr:
        return "reste stable"
    return "progresse" if d > 0 else "recule"


def _takeaways(R):
    K, pv_s = R["K"], R["pv_s"]
    vs = f" vs {pv_s}" if pv_s else ""
    out = []
    tom = K["tom"]["value"]
    lead, lead_v = _leader(R["comp"]["Top of Mind"])
    if lead and lead_v is not None and tom is not None and lead_v > tom:
        out.append(f"Top of Mind : {lead} est cité en premier par {fmt_value(lead_v, '%')} des répondants, "
                   f"devant Betclic ({fmt_value(tom, '%')}, {fmt_delta(K['tom']['delta'], '%') or 'n.d.'}{vs}).")
    else:
        out.append(f"Betclic est la marque la plus citée en premier ({fmt_value(tom, '%')} de Top of Mind).")
    k = K["penetration"]
    out.append(f"La pénétration de Betclic {_verb(k['delta'], 0.5)} à {fmt_value(k['value'], '%')}"
               f"{' (' + fmt_delta(k['delta'], '%') + vs + ')' if k['delta'] is not None else ''} ; "
               f"considération à {fmt_value(K['consideration']['value'], '%')} des parieurs.")
    pdm = K["pdm_volume"]["value"]
    plead, plead_v = _leader(R["comp"]["PDM Volume"])
    if plead and plead_v is not None and pdm is not None and plead_v > pdm:
        out.append(f"PDM Volume : {plead} passe devant avec {fmt_value(plead_v, '%')} des essais, "
                   f"contre {fmt_value(pdm, '%')} pour Betclic ({fmt_delta(K['pdm_volume']['delta'], '%') or 'n.d.'}{vs}).")
    else:
        out.append(f"Betclic reste leader en PDM Volume avec {fmt_value(pdm, '%')} des essais.")
    k = K["rappel"]
    out.append(f"Le rappel publicitaire spontané de Betclic {_verb(k['delta'], 0.5)} à {fmt_value(k['value'], '%')}"
               f"{' (' + fmt_delta(k['delta'], '%') + vs + ')' if k['delta'] is not None else ''}.")
    k = K["nps"]
    out.append(f"Le NPS de Betclic {_verb(k['delta'], 0.5)} à {fmt_value(k['value'], 'pts')}"
               f"{' (' + fmt_delta(k['delta'], 'pts') + vs + ')' if k['delta'] is not None else ''}, "
               f"satisfaction à {fmt_value(K['satisfaction']['value'], '/5', 2)}.")
    if R["image"]:
        best, worst = R["image"][0], R["image"][-1]
        out.append(f"Attributs : point fort « {best['attr']} » ({fr(best['betclic'], 2)}/5), "
                   f"axe de progrès « {worst['attr']} » ({fr(worst['betclic'], 2)}/5).")
    C = R["casino"]
    if C:
        played, offre = C["tiles"][0]["value"], C["tiles"][2]["value"]
        pd_c = C["comp"]["PDM Volume casino"]
        cl, cl_v = _leader(pd_c)
        txt = (f"Casino : {fmt_value(played, '%')} ont déjà joué en ligne ; "
               f"l'offre Betclic Casino est connue de {fmt_value(offre, '%')}")
        if cl and cl_v is not None and cl_v > pd_c.get("Betclic", 0):
            txt += f" et {cl} mène en PDM Volume casino ({fmt_value(cl_v, '%')} vs {fmt_value(pd_c.get('Betclic'), '%')})."
        else:
            txt += f" et Betclic mène en PDM Volume casino ({fmt_value(pd_c.get('Betclic'), '%')})."
        out.append(txt)
    return out


def _action_titles(R):
    """Titres de slides formulés comme le message principal (style cabinet de conseil)."""
    K = R["K"]
    T = {}
    lead, lead_v = _leader(R["comp"]["Top of Mind"])
    tom = K["tom"]["value"]
    pen = R["comp"]["Pénétration"]
    pen_lead, pen_lead_v = _leader(pen)
    pen_b = pen.get("Betclic")
    if pen_lead and pen_lead_v is not None and pen_b is not None:
        gap = pen_b - pen_lead_v
        pen_txt = (f"Betclic devant en pénétration (+{fr(gap)} pt)" if gap >= 0.5 else
                   (f"{pen_lead} devant en pénétration ({fr(-gap)} pt d'écart)" if gap <= -0.5 else
                    "pénétration au coude-à-coude"))
    else:
        pen_txt = ""
    if (lead and lead_v is not None and tom is not None and lead_v > tom
            and pen_lead == lead and pen_b is not None and pen_lead_v - pen_b >= 0.5):
        T["comp"] = (f"{lead} devance Betclic en Top of Mind ({fr(lead_v, 0)} % vs {fr(tom, 0)} %) "
                     f"et en pénétration ({fr(pen_lead_v, 0)} % vs {fr(pen_b, 0)} %)")
    elif lead and lead_v is not None and tom is not None and lead_v > tom:
        T["comp"] = f"{lead} domine le Top of Mind" + (f", {pen_txt}" if pen_txt else "")
    else:
        T["comp"] = "Betclic en tête du Top of Mind" + (f", {pen_txt}" if pen_txt else "")
    plead, plead_v = _leader(R["comp"]["PDM Volume"])
    pdm = K["pdm_volume"]["value"]
    if plead and plead_v is not None and pdm is not None and plead_v > pdm:
        T["pdm"] = f"{plead} passe devant Betclic en part de marché volume ({fr(plead_v)} % vs {fr(pdm)} %)"
    else:
        T["pdm"] = f"Betclic leader en part de marché volume ({fr(pdm)} %)"
    k = K["nps"]
    T["sat"] = (f"Le NPS de Betclic {_verb(k['delta'], 0.5)} à {fr(k['value'])} pts"
                + (f" ({fmt_delta(k['delta'], 'pts')} vs {R['pv_s']})" if k["delta"] is not None else ""))
    k = K["penetration"]
    T["funnel"] = (f"La pénétration {_verb(k['delta'], 0.5)} à {fr(k['value'])} %"
                   + (f" ({fmt_delta(k['delta'], '%')} vs {R['pv_s']})" if k["delta"] is not None else ""))
    if R["image"]:
        best = R["image"][0]
        n_adv = sum(1 for r in R["image"] if r["gap"] is not None and r["gap"] > 0)
        n_tot = sum(1 for r in R["image"] if r["gap"] is not None)
        if n_tot and n_adv == n_tot:
            T["image"] = f"Betclic devance 1XBET sur les {n_tot} attributs, porté par « {best['attr']} »"
        elif n_tot:
            T["image"] = f"Betclic devance 1XBET sur {n_adv} attributs sur {n_tot}, porté par « {best['attr']} »"
        else:
            T["image"] = f"Point fort de Betclic : « {best['attr']} »"
    k = K["rappel"]
    T["notoriete"] = (f"Rappel publicitaire Betclic : {fr(k['value'])} %"
                      + (f" ({fmt_delta(k['delta'], '%')} vs {R['pv_s']})" if k["delta"] is not None else ""))
    return T
