"""
Data loader and KPI calculation engine for Betclic Brand Pulse Tracker.

Handles two file formats automatically:
  - RAW CAPI export (new): columns like QF1, Q1A, A_Q1B_1, T_Q12A_1, etc.
  - LEGACY normalized (fictional/old): columns like Vague, TOM_Marque_Citee, etc.

The raw format is transformed into the normalized schema on load, so all
downstream views/KPI functions keep using the same column names.
"""

import re
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent.parent

# ──────────────────────────────────────────────
# REFERENCE LISTS · updated to match real V1 questionnaire
# ──────────────────────────────────────────────

# Marques suivies dans le questionnaire. V1-V3 : 14 marques (+ KifBet en V3).
# V4 ajoute Bet 360, Betwinner et 1WIN. Une marque absente du questionnaire
# d'une vague a ses colonnes à NaN pour cette vague (et non 0).
COMPETITORS = [
    "Betclic", "Chopbet", "1XBET", "Sportcash", "BetPawa",
    "Melbet", "Premier Bet", "BetMomo", "AkwaBet", "YellowBet",
    "Betway", "Afropari", "Paripesa", "Bet365",
    "KifBet", "Bet 360", "Betwinner", "1WIN",
]

# Marques principales à afficher dans les comparaisons concurrentielles
# (basé sur le top notoriété + part de marché sur le marché ivoirien)
MAIN_COMPETITORS = ["Betclic", "1XBET", "Sportcash", "Melbet", "BetMomo"]

# Calendrier de collecte (préseedé pour respecter le cycle réel, qui saute Juillet)
VAGUE_LABELS = {
    "Vague 1": "V1 (Mai 2026)",
    "Vague 2": "V2 (Juin 2026)",
    "Vague 3": "V3 (Août 2026)",
    "Vague 4": "V4 (Novembre 2026)",
}
VAGUE_SHORT = {"Vague 1": "V1", "Vague 2": "V2", "Vague 3": "V3", "Vague 4": "V4"}
VAGUE_MONTHS = {
    "Vague 1": "Mai 2026", "Vague 2": "Juin 2026",
    "Vague 3": "Août 2026", "Vague 4": "Novembre 2026",
}


def vague_num(v) -> int:
    """'Vague 4' -> 4 (999 si non numérique)."""
    s = str(v).replace("Vague ", "")
    return int(s) if s.isdigit() else 999


def sort_vagues(vagues) -> list:
    """Tri chronologique des vagues ('Vague 10' après 'Vague 9')."""
    return sorted([v for v in vagues if v is not None and not (isinstance(v, float) and np.isnan(v))],
                  key=vague_num)


def vague_short(v) -> str:
    """'Vague 4' -> 'V4'."""
    return VAGUE_SHORT.get(v, f"V{vague_num(v)}" if vague_num(v) != 999 else str(v))


def _build_dynamic_vague_labels(vagues_list):
    """Build VAGUE_SHORT and VAGUE_MONTHS for any wave number (future-proof)."""
    months_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                 "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    for v_name in vagues_list:
        if v_name in VAGUE_SHORT:
            continue
        try:
            num = int(v_name.replace("Vague ", ""))
            VAGUE_SHORT[v_name] = f"V{num}"
            # V1 starts in May 2026 ; next waves every ~1-2 months
            month_idx = (4 + (num - 1)) % 12
            year = 2026 + (4 + (num - 1)) // 12
            VAGUE_MONTHS[v_name] = f"{months_fr[month_idx]} {year}"
            VAGUE_LABELS[v_name] = f"V{num} · {months_fr[month_idx][:3]} {year}"
        except (ValueError, TypeError):
            VAGUE_SHORT[v_name] = v_name
            VAGUE_MONTHS[v_name] = ""
            VAGUE_LABELS[v_name] = v_name


# 13 image attributes (Q12) · matches the real questionnaire
IMAGE_ATTRIBUTES = {
    "Image_Fiabilite_Paiement": "Fiabilité paiements",
    "Image_Securite": "Sécurité",
    "Image_Bonus": "Bonus & promotions",
    "Image_Variete_Paris": "Variété sports/marchés",
    "Image_Qualite_App": "Qualité app mobile",
    "Image_Simplicite": "Simplicité",
    "Image_Service_Client": "Service client",
    "Image_Depot_Retrait": "Dépôt / retrait",
    "Image_Live_Betting": "Live betting",
    "Image_Transparence": "Transparence",
    "Image_Jeu_Responsable": "Jeu responsable",
    "Image_Proximite": "Proximité locale CI",
    "Image_Cotes_Elevees": "Cotes élevées",
    "Image_Cash_Out": "Cash out élevés",
}

CITIES =["Abidjan", "Bouaké", "Yamoussoukro", "San Pedro", "Daloa", "Korhogo", "Abengourou"]


# ──────────────────────────────────────────────
# RAW → NORMALIZED ADAPTER
# ──────────────────────────────────────────────

# Fallback index -> marque (ordre réel du questionnaire V1-V3, vérifié sur les
# libellés des cellules). En pratique l'ordre est relu dans chaque base via
# `_detect_index_map`, car il a changé en V4 (KifBet, Bet 360, Betwinner, 1WIN).
RAW_BRAND_BY_INDEX = {
    1: "Betclic", 2: "Chopbet", 3: "1XBET", 4: "Sportcash",
    5: "BetPawa", 6: "Melbet", 7: "Premier Bet", 8: "BetMomo",
    9: "AkwaBet", 10: "YellowBet", 11: "Afropari", 12: "Paripesa",
    13: "Bet365", 14: "Betway",
}
# Map Q12 attribute suffix (_1.._14) to normalized image column
RAW_IMAGE_ATTRS = {
    1: "Image_Fiabilite_Paiement",
    2: "Image_Securite",
    3: "Image_Bonus",
    4: "Image_Variete_Paris",
    5: "Image_Qualite_App",
    6: "Image_Simplicite",
    7: "Image_Service_Client",
    8: "Image_Depot_Retrait",
    9: "Image_Live_Betting",
    10: "Image_Transparence",
    11: "Image_Jeu_Responsable",
    12: "Image_Proximite",
    13: "Image_Cotes_Elevees",
    14: "Image_Cash_Out",
}

# ── Casino en ligne (Section 5B, introduite en V4) ──
CASINO_GAMES = {
    1: "Machines à sous",
    2: "Roulette",
    3: "Blackjack / Baccarat",
    4: "Poker",
    5: "Casino live (croupier)",
    6: "Jeux crash (type Aviator)",
    7: "Jeux virtuels",
    8: "Autres",
}
CASINO_STATUTS = ["Joueur actif (6 derniers mois)", "Ancien joueur (+6 mois)", "Non-joueur"]

SPORT_MAP = {
    "A_Q11_1": "Football",
    "A_Q11_2": "Basketball",
    "A_Q11_3": "Tennis",
    "A_Q11_4": "Rugby",
    "A_Q11_5": "Hockey sur glace",
    "A_Q11_6": "Sports ivoiriens / africains",
    "A_Q11_7": "Autres",
}


def _is_raw_format(df: pd.DataFrame) -> bool:
    """Detect if the dataframe is in raw CAPI export format."""
    return (
        "QF1" in df.columns
        and "Q1A" in df.columns
        and "TOM_Marque_Citee" not in df.columns
    )


def _str_yes_no(series: pd.Series) -> pd.Series:
    """Convert a raw A_QxX_Y column (string brand label or '0') to 1/0.

    Rule: 1 if the cell contains the actual brand label (e.g. "Betclic"),
          0 if the cell is "0", NaN, empty, or any zero-like sentinel.

    We must check `notna` BEFORE astype(str) because pandas ArrowStringArray
    converts NaN to a representation that won't match "nan" after lowercase.
    """
    not_null = series.notna()
    s = series.astype(str).str.strip()
    # zero-like sentinels seen in real data: "0", "0.0", "", "nan", "<NA>"
    zero_like = s.isin(["0", "0.0", "", "nan", "NaN", "<NA>", "None"])
    return (not_null & ~zero_like).astype(int)


# ── Résolution des marques à partir des libellés (robuste aux changements d'ordre) ──

def _brand_key(label) -> str:
    return re.sub(r"[^a-z0-9]", "", str(label).lower())


_BRAND_LOOKUP = {_brand_key(b): b for b in COMPETITORS}


def _canonical_brand(label):
    """Libellé brut ('1win', 'Bet 360', 'MELBET') -> marque canonique, sinon None."""
    if label is None or (isinstance(label, float) and np.isnan(label)):
        return None
    return _BRAND_LOOKUP.get(_brand_key(label))


def _column_brand(series: pd.Series):
    """Marque portée par une colonne multi-réponse (libellé le plus fréquent hors '0')."""
    s = series.dropna().astype(str).str.strip()
    s = s[~s.isin(["0", "0.0", "", "nan", "NaN", "<NA>", "None"])]
    if s.empty:
        return None
    return _canonical_brand(s.value_counts().index[0])


_BRAND_LABEL_PREFIXES = ("A_Q1B", "A_Q1C", "A_Q5", "A_Q18", "A_Q19A", "A_QC4")


def _detect_index_map(df_raw: pd.DataFrame) -> dict:
    """Index -> marque pour CETTE base, lu dans les libellés des cellules.

    L'export CAPI numérote les marques dans l'ordre du questionnaire de la
    vague, et cet ordre a changé (ex. V4 : Betway passe en 11, 1WIN en 17).
    On lit donc le libellé stocké dans A_Q1B_i / A_Q1C_i / A_Q5_i ... plutôt
    que de supposer un ordre fixe.
    """
    idx_map = {}
    for i in range(1, 40):
        votes = {}
        for p in _BRAND_LABEL_PREFIXES:
            col = f"{p}_{i}"
            if col in df_raw.columns:
                b = _column_brand(df_raw[col])
                if b:
                    votes[b] = votes.get(b, 0) + 1
        if votes:
            idx_map[i] = max(votes, key=votes.get)
    return idx_map or dict(RAW_BRAND_BY_INDEX)


def _brand_columns(df_raw: pd.DataFrame, prefix: str, idx_map: dict) -> dict:
    """{marque: colonne brute} pour un bloc par marque (A_Q5_1..N, A_Q18_1..N...)."""
    out = {}
    for i in range(1, 40):
        col = f"{prefix}_{i}"
        if col not in df_raw.columns:
            continue
        brand = _column_brand(df_raw[col]) or idx_map.get(i)
        if brand and brand not in out:
            out[brand] = col
    return out


def brands_in_scope(df: pd.DataFrame) -> list:
    """Marques mesurées dans au moins une des vagues présentes dans df."""
    out = []
    for b in COMPETITORS:
        col = f"Notoriete_Totale_{b}"
        if col in df.columns and df[col].notna().any():
            out.append(b)
    return out


def _nps_category(score) -> str:
    """0-6 = Détracteur, 7-8 = Passif, 9-10 = Promoteur."""
    if pd.isna(score):
        return None
    score = float(score)
    if score >= 9:
        return "Promoteur"
    elif score >= 7:
        return "Passif"
    else:
        return "Détracteur"


def _churn_from_intention(intent) -> str:
    """Map Q13 reuse intention to a churn risk label."""
    if pd.isna(intent):
        return None
    v = str(intent).strip()
    if v.startswith("Très probablement"):
        return "Faible"
    if v.startswith("Probablement") and "pas" not in v.lower():
        return "Faible"
    if "Peut-être" in v or "peut-être" in v:
        return "Modéré"
    if "Peu probable" in v:
        return "Élevé"
    if "Pas du tout" in v.lower() or v.startswith("Pas du tout"):
        return "Élevé"
    return "Modéré"


def _map_intention(v) -> str:
    """Map raw Q13 wording to standardized intention buckets."""
    if pd.isna(v):
        return None
    v = str(v).strip()
    if v.startswith("Très probablement"):
        return "Certainement"
    if v.startswith("Probablement") and "pas" not in v.lower():
        return "Probablement"
    if "Peut-être" in v:
        return "Incertain"
    if "Peu probable" in v or "Pas du tout" in v:
        return "Probablement pas"
    return None


def _transform_raw_to_normalized(df_raw: pd.DataFrame, wave_name: str = "Vague 1") -> pd.DataFrame:
    """
    Transform raw CAPI V1 export into the normalized schema expected by views.

    The raw format has 447 columns with codes (QF1, Q1A, A_Q1B_1, T_Q12A_1...).
    The normalized format has columns like Vague, Genre, Ville, TOM_Marque_Citee,
    Notoriete_Totale_{Brand}, Image_{Attr}, NPS_Score, etc.
    """
    df = pd.DataFrame()
    n = len(df_raw)

    # Ordre des marques propre à cette base (cf. _detect_index_map)
    idx_map = _detect_index_map(df_raw)
    asked_brands = set(idx_map.values())

    # ── Identifiers & wave ──
    df["ID_Repondant"] = df_raw["SbjNum"]
    df["Vague"] = wave_name
    df["Mois_Collecte"] = pd.to_datetime(
        df_raw.get("Date_Inter", df_raw.get("Date")), errors="coerce"
    ).dt.strftime("%B %Y")

    # ── Profile ──
    df["Tranche_Age"] = df_raw["QF1"]
    df["Genre"] = df_raw["Q27"]
    df["Ville"] = df_raw["Q29"]
    # Commune (sous-dimension Abidjan uniquement)
    df["Commune"] = df_raw.get("Q29_Commune", pd.Series([None] * len(df_raw)))
    df["Profession"] = df_raw.get("Q28", "")

    # ── Type respondant ──
    # V1-V3 : variable Type_Rep. V4 : supprimée de l'export, on la reconstruit
    # depuis le filtre QF2 (Oui = parieur, Non = non-parieur), même règle.
    if "Type_Rep" in df_raw.columns:
        type_rep = df_raw["Type_Rep"].astype(str).str.strip()
        df["Type_Repondant"] = type_rep.map({
            "PARIEUR": "Parieur",
            "NON  PARIEUR": "Non-parieur",
            "NON PARIEUR": "Non-parieur",
        }).fillna(type_rep)
    else:
        qf2 = df_raw.get("QF2", pd.Series([None] * n)).astype(str).str.strip()
        df["Type_Repondant"] = np.where(
            qf2.str.startswith("Oui"), "Parieur",
            np.where(qf2.str.startswith("Non"), "Non-parieur", None),
        )
    df["Segment_Parieur"] = df["Type_Repondant"]
    df["Frequence_Paris"] = df_raw.get("Q8", None)
    df["Frequence_Paris_Mois"] = df["Frequence_Paris"]
    df["Montant_Mise_Mensuel"] = df_raw.get("Q10", None)
    # Numeric version (FCFA, milieu de tranche) · utilisé pour les agrégations pivot
    df["Montant_Mise_Mensuel_FCFA"] = df["Montant_Mise_Mensuel"].map(Q10_MIDPOINTS_FCFA)

    # ── TOM (Top of Mind) ──
    q1a_brand = df_raw["Q1A"].map(_canonical_brand)
    df["TOM_Marque_Citee"] = q1a_brand.values

    # ── Awareness per brand (TOM + spontaneous + aided + total) ──
    # User-validated formula:
    #   Notoriete Totale  = Q1A=brand OR A_Q1B_idx OR A_Q1C_idx   (Q1A + Q1B + Q1C)
    #   Notoriete Spont.  = Q1A=brand OR A_Q1B_idx                (Q1A + Q1B)
    #   Notoriete Aidee   = A_Q1C_idx only                        (Q1C alone)
    # Marque non présente dans le questionnaire de la vague -> NaN (non mesurée).
    q1b_cols = _brand_columns(df_raw, "A_Q1B", idx_map)
    q1c_cols = _brand_columns(df_raw, "A_Q1C", idx_map)
    for brand in COMPETITORS:
        if brand not in asked_brands:
            for pfx in ("Notoriete_Spontanee_", "Notoriete_Aidee_", "Notoriete_Totale_"):
                df[f"{pfx}{brand}"] = np.nan
            continue
        is_tom = (q1a_brand == brand).astype(int).values
        spont_b = _str_yes_no(df_raw[q1b_cols[brand]]).values if brand in q1b_cols else np.zeros(n, dtype=int)
        aided_c = _str_yes_no(df_raw[q1c_cols[brand]]).values if brand in q1c_cols else np.zeros(n, dtype=int)
        df[f"Notoriete_Spontanee_{brand}"] = ((is_tom == 1) | (spont_b == 1)).astype(int)
        df[f"Notoriete_Aidee_{brand}"] = aided_c
        df[f"Notoriete_Totale_{brand}"] = (
            (is_tom == 1) | (spont_b == 1) | (aided_c == 1)
        ).astype(int)

    # ── Usage ──
    q6 = df_raw.get("Q6", pd.Series([None] * n))
    q6_brand = q6.map(_canonical_brand)
    # Libellé canonique si c'est une marque suivie, sinon libellé brut ("Autres...")
    df["Marque_Principale_Utilisee"] = q6_brand.where(q6_brand.notna(), q6).values
    df["Utilise_Betclic"] = (q6_brand == "Betclic").astype(int).values

    # Per-brand "has bet on" flag (from A_Q5_X)
    q5_cols = _brand_columns(df_raw, "A_Q5", idx_map)
    for brand in COMPETITORS:
        if brand in q5_cols:
            df[f"A_Deja_Parie_{brand}"] = _str_yes_no(df_raw[q5_cols[brand]]).values
        elif brand in asked_brands:
            df[f"A_Deja_Parie_{brand}"] = 0
        else:
            df[f"A_Deja_Parie_{brand}"] = np.nan

    # Multi-app: nombre de marques suivies sur lesquelles le répondant a parié
    if q5_cols:
        nb_apps = sum(_str_yes_no(df_raw[c]) for c in q5_cols.values())
        df["Nb_Apps_Utilisees"] = nb_apps.values
        df["Multi_Application"] = (nb_apps.values >= 2).astype(int)
    else:
        df["Nb_Apps_Utilisees"] = 0
        df["Multi_Application"] = 0

    # ── Sport préféré (Q11 multi-réponse) ──
    # 1 flag par sport pour permettre l'agrégation correcte
    for raw_col, sport in SPORT_MAP.items():
        if raw_col in df_raw.columns:
            df[f"Sport_{sport.replace(' ', '_').replace('/', '_')}"] = _str_yes_no(df_raw[raw_col]).values
    # Compat : on garde le premier sport cité comme fallback
    def first_sport(row):
        for col, sport in SPORT_MAP.items():
            v = row.get(col)
            if pd.notna(v) and str(v).strip() != "0":
                return sport
        return None
    df["Sport_Prefere"] = df_raw.apply(first_sport, axis=1) if any(c in df_raw.columns for c in SPORT_MAP) else None

    # ── Moyen de paiement ──
    df["Moyen_Paiement_Principal"] = df_raw.get("Q9", None)

    # ── Type pari préféré : not asked in V1 ──
    df["Type_Pari_Prefere"] = None

    # ── Intention recommandation (Q13) per-row flag : Très probablement OU Probablement ──
    # Q13 = "Probabilité de recommander Q6 (NPS)" · asked to parieurs only.
    # For non-parieurs Q13 is NaN, so the flag = 0.
    intent_raw = df_raw.get("Q13", pd.Series([None] * n)).astype(str).str.strip()
    intent_strong = (
        (intent_raw == "Très probablement") | (intent_raw == "Probablement")
    ).astype(int)
    df["Intention_Recommande_Forte"] = intent_strong.values

    # ── Considération (user-validated): Q5 (a déjà parié) OU Q13 ∈ {Très/Probablement} ──
    # Per-row flag. A_Deja_Parie_Betclic was set above.
    for brand in COMPETITORS:
        if brand not in asked_brands:
            df[f"Consideration_{brand}"] = np.nan
            continue
        col = f"A_Deja_Parie_{brand}"
        df[f"Consideration_{brand}"] = (
            (df[col] == 1) | (df["Intention_Recommande_Forte"] == 1)
        ).astype(int)
    # ── Préférence (user-validated): Q6 == "Betclic" ──
    df["Preference_Betclic"] = df["Utilise_Betclic"]

    # ── Image attributes (Q12), deux formats d'export :
    #   V1-V3 : T_Q12{lettre}_{item}  (lettre A,B,C... = rang de la marque)
    #   V4    : {Marque}_T_Q12_{item} (ex. "1XBET_T_Q12_3")
    img_cols = {}  # {brand: {item_idx: raw_col}}
    for raw_col in df_raw.columns:
        m_old = re.match(r"^T_Q12([A-Z])_(\d+)$", str(raw_col))
        m_new = re.match(r"^(.+)_T_Q12_(\d+)$", str(raw_col))
        if m_old:
            brand = idx_map.get(ord(m_old.group(1)) - 64)
            item = int(m_old.group(2))
        elif m_new:
            brand = _canonical_brand(m_new.group(1))
            item = int(m_new.group(2))
        else:
            continue
        if brand and item in RAW_IMAGE_ATTRS:
            img_cols.setdefault(brand, {})[item] = raw_col

    # Betclic : colonnes de base Image_X (utilisées par la majorité des vues)
    for idx, attr_col in RAW_IMAGE_ATTRS.items():
        raw_col = img_cols.get("Betclic", {}).get(idx)
        df[attr_col] = pd.to_numeric(df_raw[raw_col], errors="coerce") if raw_col else np.nan

    # Toutes les marques : colonnes suffixées Image_X_{Marque}
    for brand, items in img_cols.items():
        for idx, raw_col in items.items():
            df[f"{RAW_IMAGE_ATTRS[idx]}_{brand}"] = pd.to_numeric(df_raw[raw_col], errors="coerce")

    # ── Importance (Q4) · used by some views ──
    importance_labels = list(RAW_IMAGE_ATTRS.values())
    for idx, attr_col in RAW_IMAGE_ATTRS.items():
        raw_col = f"T_Q4_{idx}"
        df[f"Importance_{attr_col.replace('Image_', '')}"] = (
            pd.to_numeric(df_raw[raw_col], errors="coerce") if raw_col in df_raw.columns else None
        )

    # ── Satisfaction & NPS ──
    df["Satisfaction_Globale_Betclic"] = pd.to_numeric(df_raw.get("T_Q14_1"), errors="coerce")
    df["NPS_Score"] = pd.to_numeric(df_raw.get("Q15"), errors="coerce")
    df["NPS_Categorie"] = df["NPS_Score"].apply(_nps_category)

    # ── Churn risk & intention (derived from Q13) ──
    df["Risque_Churn"] = intent_raw.apply(_churn_from_intention)
    df["Intention_Reutilisation"] = intent_raw.apply(_map_intention)

    # ── Principal_Irritant : Q16 verbatim (the "why" of NPS score) ──
    df["Principal_Irritant"] = df_raw.get("Q16", None)

    # ── Campaign recall ──
    q17 = df_raw.get("Q17", pd.Series([None] * n)).astype(str)
    df["Rappel_Pub_Generale"] = q17.str.startswith("Oui").astype(int)

    # Per-brand spontaneous ad recall (A_Q18_X)
    q18_cols = _brand_columns(df_raw, "A_Q18", idx_map)
    for brand in COMPETITORS:
        if brand in q18_cols:
            df[f"Rappel_Campagne_{brand}"] = _str_yes_no(df_raw[q18_cols[brand]]).values
        elif brand in asked_brands:
            df[f"Rappel_Campagne_{brand}"] = 0
        else:
            df[f"Rappel_Campagne_{brand}"] = np.nan

    # Q21 = recall World Cup campaign (section supprimée en V4 -> NaN)
    if "Q21" in df_raw.columns:
        df["Rappel_CDM_Betclic"] = df_raw["Q21"].astype(str).str.startswith("Oui").astype(int).values
    else:
        df["Rappel_CDM_Betclic"] = np.nan

    # ── Canal de découverte Betclic (Q19_O1..O10 multi-réponse) ──
    # Each Q19_OX stores the support label (Télévision, Facebook, etc.) if the
    # respondent cited it, else "0"/empty. A respondent can cite multiple supports.
    # We expose ONE boolean column per canonical support so the aggregate
    # `calc_canal_decouverte` is correct (no first-cited bias).
    CANAL_LABELS = {
        "Television": "Télévision",
        "Radio": "Radio",
        "Affichage_Fixe": "Affichage extérieur fixe : panneaux, bâches, façades murales, écrands LED",
        "Affichage_Mobile": "Affichage extérieur mobile : taxis, bus, poussettes à café, cars de transports...",
        "Facebook_Instagram": "Facebook / Instagram",
        "TikTok": "TikTok",
        "YouTube": "YouTube",
        "SMS_WhatsApp": "SMS / WhatsApp",
        "Sponsoring_Sportif": "Sponsoring sportif (maillot, stade…)",
        "Bouche_A_Oreille": "Bouche à oreille / ami",
    }
    q19_cols = [f"Q19_O{i}" for i in range(1, 11) if f"Q19_O{i}" in df_raw.columns]
    if q19_cols:
        q19_concat = df_raw[q19_cols].astype(str)
        for col_key, label in CANAL_LABELS.items():
            df[f"Canal_{col_key}"] = q19_concat.apply(
                lambda row: int(any(row[c] == label for c in q19_cols)), axis=1
            ).values

        # Also keep a "first canal cited" string column (backward compat) and
        # a list of all canals per row (for future drill-down).
        def first_canal(row):
            for c in q19_cols:
                v = row.get(c)
                if pd.notna(v) and str(v).strip() not in ("", "0"):
                    return str(v).strip()
            return None
        df["Canal_Decouverte"] = df_raw.apply(first_canal, axis=1)
    else:
        for col_key in CANAL_LABELS:
            df[f"Canal_{col_key}"] = 0
        df["Canal_Decouverte"] = None

    # ── Ambassadeur : not asked this wave ──
    df["Ambassadeur_Rappele"] = None

    # ── Canal_Decouverte : first non-empty Q19_OX (Betclic-specific supports) ──
    q19_cols = [f"Q19_O{i}" for i in range(1, 11) if f"Q19_O{i}" in df_raw.columns]
    def first_canal(row):
        for col in q19_cols:
            v = row.get(col)
            if pd.notna(v) and str(v).strip() not in ("", "0"):
                return str(v).strip()
        return None
    df["Canal_Decouverte"] = df_raw.apply(first_canal, axis=1) if q19_cols else None

    # ── Casino en ligne (Section 5B, à partir de V4) ──
    # Colonnes absentes des vagues antérieures -> NaN après concaténation,
    # ce qui permet à la vue Casino de ne retenir que les vagues concernées.
    if "QC3" in df_raw.columns:
        qc3 = df_raw["QC3"].astype(str).str.strip()
        df["Casino_Statut"] = np.where(
            qc3.str.contains("6 derniers mois"), CASINO_STATUTS[0],
            np.where(qc3.str.startswith("Oui"), CASINO_STATUTS[1],
                     np.where(qc3.str.startswith("Non"), CASINO_STATUTS[2], None)),
        )
        df["Casino_Joueur"] = qc3.str.startswith("Oui").astype(int).values
        df["Casino_Joueur_Actif"] = qc3.str.contains("6 derniers mois").astype(int).values

        # QC1 : la marque propose-t-elle du casino ? (même ordre de marques que Q1)
        for i, brand in idx_map.items():
            col = f"T_QC1_{i}"
            if col in df_raw.columns:
                df[f"Casino_Offre_{brand}"] = (
                    df_raw[col].astype(str).str.strip() == "Propose du casino"
                ).astype(int).values

        # QC4 : a déjà joué au casino sur la marque (multi-réponse)
        qc4_cols = _brand_columns(df_raw, "A_QC4", idx_map)
        for brand, col in qc4_cols.items():
            df[f"Casino_A_Joue_{brand}"] = _str_yes_no(df_raw[col]).values

        # QC5 : marque casino principale
        qc5 = df_raw.get("QC5", pd.Series([None] * n))
        qc5_brand = qc5.map(_canonical_brand)
        df["Casino_Marque_Principale"] = qc5_brand.where(qc5_brand.notna(), qc5).values

        df["Casino_Frequence"] = df_raw.get("QC6", pd.Series([None] * n)).values
        df["Casino_Pratique"] = df_raw.get("QC8", pd.Series([None] * n)).values
        df["Casino_Decouverte_Betclic"] = df_raw.get("QC2", pd.Series([None] * n)).values

        # QC7 : types de jeux (multi-réponse, 3 max)
        for i in CASINO_GAMES:
            col = f"A_QC7_{i}"
            if col in df_raw.columns:
                df[f"Casino_Jeu_{i}"] = _str_yes_no(df_raw[col]).values

    # ── Date column for export engine ──
    # Date_Inter est saisie par l'enquêteur ; si elle s'écarte de plus de 7 jours de
    # l'horodatage CAPI (colonne Date), c'est une erreur de saisie (ex. jour/mois
    # inversés) : on retient alors la date système.
    d_inter = pd.to_datetime(df_raw.get("Date_Inter"), errors="coerce")
    if "Date" in df_raw.columns:
        d_sys = pd.to_datetime(df_raw["Date"], errors="coerce").dt.normalize()
        bad = d_sys.notna() & (d_inter.isna() | ((d_inter - d_sys).abs() > pd.Timedelta(days=7)))
        d_inter = d_inter.where(~bad, d_sys)
    df["Date_Interview"] = d_inter.values

    return df


# ──────────────────────────────────────────────
# FILE DISCOVERY & LOADING
# ──────────────────────────────────────────────

def detect_available_waves() -> list:
    """Auto-detect all Bases_Betclic_BrandPulse_Tracker_V*.xlsx files."""
    from data.validation import detect_wave_files
    return detect_wave_files(DATA_DIR)


def _data_signature() -> tuple:
    """Signature (nom, taille, date de modification) des bases et du loader.

    Sert de clé au cache : dès qu'une base est remplacée (git pull sur Streamlit
    Cloud) ou que le code de transformation change, le cache est invalidé et les
    nouvelles données s'affichent immédiatement, sans attendre l'expiration (ttl).
    """
    paths = [wf["path"] for wf in detect_available_waves()]
    paths += sorted(DATA_DIR.glob("Bases_Betclic_BrandPulse_Tracker_V*.xlsx"))
    paths.append(Path(__file__))
    sig = []
    for p in sorted(set(Path(p) for p in paths)):
        try:
            s = p.stat()
            sig.append((p.name, s.st_size, s.st_mtime_ns))
        except OSError:
            continue
    return tuple(sig)


def load_raw_data() -> pd.DataFrame:
    """Load and concatenate all available tracker bases (auto-detects format)."""
    return _load_raw_data_cached(_data_signature())


@st.cache_data(ttl=3600, max_entries=3)
def _load_raw_data_cached(data_sig: tuple) -> pd.DataFrame:
    """Version mise en cache, indexée par la signature des fichiers (data_sig)."""
    wave_files = detect_available_waves()
    if not wave_files:
        # Fallback legacy : explicit V1/V2/V3 lookup
        wave_files = []
        for v in range(1, 13):
            fpath = DATA_DIR / f"Bases_Betclic_BrandPulse_Tracker_V{v}.xlsx"
            if fpath.exists():
                wave_files.append({"num": v, "path": fpath, "name": f"Vague {v}"})

    frames = []
    for wf in wave_files:
        try:
            # Try raw format first (no header offset)
            df_raw = pd.read_excel(wf["path"])
            if _is_raw_format(df_raw):
                df_norm = _transform_raw_to_normalized(df_raw, wave_name=wf["name"])
            else:
                # Legacy normalized format with 1-row header offset
                df_norm = pd.read_excel(wf["path"], header=1)
                if "Vague" in df_norm.columns:
                    df_norm["Vague"] = df_norm["Vague"].fillna(wf["name"])
            frames.append(df_norm)
        except Exception as e:
            print(f"Erreur lecture {wf['path'].name}: {e}")
            continue

    if not frames:
        return pd.DataFrame()

    data = pd.concat(frames, ignore_index=True)

    # Coerce numeric columns
    numeric_cols = [
        "Frequence_Paris_Mois", "Rappel_Campagne_Betclic", "Utilise_Betclic",
        "Multi_Application", "Nb_Apps_Utilisees",
        "Consideration_Betclic", "Preference_Betclic",
        "Satisfaction_Globale_Betclic", "NPS_Score",
    ]
    for brand in COMPETITORS:
        numeric_cols.extend([
            f"Notoriete_Totale_{brand}",
            f"Notoriete_Spontanee_{brand}",
            f"Notoriete_Aidee_{brand}",
        ])
    for col in numeric_cols:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    for col in IMAGE_ATTRIBUTES:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    return data


def load_waves_individually() -> dict:
    """Load each wave separately (for validation reports)."""
    return _load_waves_individually_cached(_data_signature())


@st.cache_data(ttl=3600, max_entries=3)
def _load_waves_individually_cached(data_sig: tuple) -> dict:
    wave_files = detect_available_waves()
    waves = {}
    for wf in wave_files:
        try:
            df_raw = pd.read_excel(wf["path"])
            if _is_raw_format(df_raw):
                waves[wf["name"]] = _transform_raw_to_normalized(df_raw, wave_name=wf["name"])
            else:
                df_norm = pd.read_excel(wf["path"], header=1)
                waves[wf["name"]] = df_norm
        except Exception:
            continue
    return waves


@st.cache_data(ttl=3600)
def load_kpi_reference() -> pd.DataFrame:
    """Load the KPI reference file for validation (legacy, optional)."""
    fpath = DATA_DIR / "Betclic_BrandPulse_Tracker_KPIS_V1V2V3.xlsx"
    if not fpath.exists():
        return pd.DataFrame()
    try:
        return pd.read_excel(fpath, sheet_name=1, header=2)
    except Exception:
        return pd.DataFrame()


# ──────────────────────────────────────────────
# FILTERS
# ──────────────────────────────────────────────

def apply_filters(df: pd.DataFrame, vagues=None, villes=None, genres=None, segments=None, ages=None) -> pd.DataFrame:
    """Apply sidebar filters to the dataframe."""
    filtered = df.copy()
    if vagues:
        filtered = filtered[filtered["Vague"].isin(vagues)]
    if villes:
        filtered = filtered[filtered["Ville"].isin(villes)]
    if genres:
        filtered = filtered[filtered["Genre"].isin(genres)]
    if segments:
        filtered = filtered[filtered["Segment_Parieur"].isin(segments)]
    if ages:
        filtered = filtered[filtered["Tranche_Age"].isin(ages)]
    return filtered


def get_parieurs(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to only bettors (parieurs)."""
    return df[df["Type_Repondant"] == "Parieur"]


def get_utilisateurs_betclic(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to Betclic users only."""
    return df[df["Utilise_Betclic"] == 1]


# ──────────────────────────────────────────────
# KPI CALCULATION FUNCTIONS (unchanged signatures)
# ──────────────────────────────────────────────

def calc_tom(df: pd.DataFrame, brand: str = "Betclic") -> float:
    total = len(df)
    if total == 0:
        return 0.0
    return round((df["TOM_Marque_Citee"] == brand).sum() / total * 100, 1)


def calc_tom_all_brands(df: pd.DataFrame) -> dict:
    total = len(df)
    if total == 0:
        return {b: 0.0 for b in COMPETITORS}
    return {b: round((df["TOM_Marque_Citee"] == b).sum() / total * 100, 1) for b in brands_in_scope(df)}


def calc_notoriete_totale(df: pd.DataFrame, brand: str = "Betclic") -> float:
    col = f"Notoriete_Totale_{brand}"
    if col not in df.columns:
        return 0.0
    total = len(df)
    if total == 0:
        return 0.0
    return round(df[col].sum() / total * 100, 1)


def calc_notoriete_all_brands(df: pd.DataFrame) -> dict:
    return {b: calc_notoriete_totale(df, b) for b in brands_in_scope(df)}


def calc_notoriete_aidee(df: pd.DataFrame, brand: str = "Betclic") -> float:
    col = f"Notoriete_Aidee_{brand}"
    if col not in df.columns:
        return 0.0
    total = len(df)
    if total == 0:
        return 0.0
    return round(df[col].sum() / total * 100, 1)


def calc_rappel_campagne(df: pd.DataFrame, brand: str = "Betclic") -> float:
    """Rappel pub spontané: % parieurs ayant cité la marque sur A_Q18_X.

    Base = parieurs (165). La question Q18 est gated par Q17 = "Oui",
    donc ceux qui n'ont vu aucune pub contribuent 0 (effet "portée").
    """
    parieurs = get_parieurs(df)
    col = f"Rappel_Campagne_{brand}"
    if len(parieurs) == 0 or col not in parieurs.columns:
        return 0.0
    return round(parieurs[col].sum() / len(parieurs) * 100, 1)


def calc_rappel_campagne_all_brands(df: pd.DataFrame) -> dict:
    """Rappel pub par marque (toutes les marques A_Q18_1..14). Base = parieurs."""
    return {b: calc_rappel_campagne(df, b) for b in brands_in_scope(df)}


def calc_ambassadeur_distribution(df: pd.DataFrame) -> dict:
    parieurs = get_parieurs(df)
    if "Ambassadeur_Rappele" not in parieurs.columns:
        return {}
    rappel = parieurs[parieurs["Ambassadeur_Rappele"].notna()]
    if len(rappel) == 0:
        return {}
    return rappel["Ambassadeur_Rappele"].value_counts(normalize=True).apply(lambda x: round(x * 100, 1)).to_dict()


def calc_canal_decouverte(df: pd.DataFrame) -> dict:
    """Distribution des supports via lesquels Betclic a été découvert/vu.

    Question Q19 = multi-réponse : chaque répondant peut citer plusieurs
    canaux. Cette fonction retourne le % de l'échantillon (base totale)
    ayant cité chaque support au moins une fois.
    La somme peut excéder 100% (multi-réponse).
    """
    if len(df) == 0:
        return {}
    canal_columns = {
        "Television": "Télévision",
        "Affichage_Mobile": "Affichage extérieur mobile",
        "Affichage_Fixe": "Affichage extérieur fixe",
        "Facebook_Instagram": "Facebook / Instagram",
        "TikTok": "TikTok",
        "YouTube": "YouTube",
        "SMS_WhatsApp": "SMS / WhatsApp",
        "Sponsoring_Sportif": "Sponsoring sportif",
        "Bouche_A_Oreille": "Bouche à oreille",
        "Radio": "Radio",
    }
    n = len(df)
    out = {}
    for raw_col, label in canal_columns.items():
        col = f"Canal_{raw_col}"
        if col in df.columns:
            pct = round(df[col].sum() / n * 100, 1)
            if pct > 0:
                out[label] = pct
    # Sort descending
    return dict(sorted(out.items(), key=lambda x: -x[1]))


def calc_penetration(df: pd.DataFrame, brand: str = "Betclic") -> float:
    """Pénétration: % de l'échantillon total qui a déjà parié sur la marque (Q5).

    Base = tout l'échantillon (parieurs + non-parieurs).
    """
    col = f"A_Deja_Parie_{brand}"
    if col not in df.columns or len(df) == 0:
        return 0.0
    return round(df[col].sum() / len(df) * 100, 1)


def calc_penetration_all_brands(df: pd.DataFrame) -> dict:
    return {b: calc_penetration(df, b) for b in brands_in_scope(df)}


def calc_marque_principale(df: pd.DataFrame, brand: str = "Betclic") -> float:
    """Préférence / Marque principale : Q6 == brand. Base = parieurs."""
    parieurs = get_parieurs(df)
    if len(parieurs) == 0:
        return 0.0
    return round((parieurs["Marque_Principale_Utilisee"] == brand).sum() / len(parieurs) * 100, 1)


def calc_marque_principale_all(df: pd.DataFrame) -> dict:
    parieurs = get_parieurs(df)
    if len(parieurs) == 0:
        return {b: 0.0 for b in COMPETITORS}
    total = len(parieurs)
    return {
        b: round((parieurs["Marque_Principale_Utilisee"] == b).sum() / total * 100, 1)
        for b in brands_in_scope(df)
    }


def calc_multi_app(df: pd.DataFrame) -> float:
    parieurs = get_parieurs(df)
    if len(parieurs) == 0 or "Multi_Application" not in parieurs.columns:
        return 0.0
    return round(parieurs["Multi_Application"].sum() / len(parieurs) * 100, 1)


def calc_consideration(df: pd.DataFrame, brand: str = "Betclic") -> float:
    """Considération: (Usage Q5 = a déjà parié sur la marque) OU
    (Q13 ∈ {"Très probablement", "Probablement"}). Base = parieurs.
    """
    parieurs = get_parieurs(df)
    col = f"Consideration_{brand}"
    if len(parieurs) == 0 or col not in parieurs.columns:
        return 0.0
    return round(parieurs[col].sum() / len(parieurs) * 100, 1)


def calc_preference(df: pd.DataFrame, brand: str = "Betclic") -> float:
    """Préférence : Q6 == brand. Base = parieurs."""
    return calc_marque_principale(df, brand)


# ── Wallet share (montant misé mensuel) ───────────────────────────────
# Q10 stocke des tranches textuelles. On utilise les milieux pour calculer une moyenne.
Q10_MIDPOINTS_FCFA = {
    "Moins de 5 000 FCFA": 2500,
    "De 5 000 à 10 000 FCFA": 7500,
    "De 10 001 à 25 000 FCFA": 17500,
    "De 25 001 à 50 000 FCFA": 37500,
    "De 50 001 à 100 000 FCFA": 75000,
    "De 100 001 à 200 000 FCFA": 150000,
    "Plus de 200 000 FCFA": 250000,
}


def calc_wallet_share(df: pd.DataFrame, brand: str = "Betclic") -> float:
    """Wallet share : montant mensuel moyen misé (Q10) chez les parieurs Q6==brand.

    Retourne la moyenne en FCFA (via les milieux de tranches).
    "Ne sait pas / Refuse de répondre" est exclu du calcul.
    """
    parieurs = get_parieurs(df)
    if len(parieurs) == 0 or "Montant_Mise_Mensuel" not in parieurs.columns:
        return 0.0
    target = parieurs[parieurs["Marque_Principale_Utilisee"] == brand]
    if len(target) == 0:
        return 0.0
    amounts = target["Montant_Mise_Mensuel"].map(Q10_MIDPOINTS_FCFA).dropna()
    if len(amounts) == 0:
        return 0.0
    return round(float(amounts.mean()), 0)


def calc_pdm_volume(df: pd.DataFrame, brand: str = "Betclic") -> float:
    """Part de Marché en VOLUME basée sur l'essai (Q5).

    Formule (validée client) :
        PDM_volume(brand) = N(parieurs ayant déjà parié sur brand)
                         / Σ N(parieurs ayant déjà parié sur chaque brand)
                         × 100

    Interprétation : sur 100 mentions d'essai du marché ivoirien, X% concernent
    Betclic. La somme sur l'ensemble des marques = 100%.

    Différent de la « Préférence » (Q6 = marque principale) qui compte une seule
    marque par parieur. Ici, on compte toutes les marques essayées (Q5 est multi-réponse).
    """
    parieurs = get_parieurs(df)
    if len(parieurs) == 0:
        return 0.0
    target_col = f"A_Deja_Parie_{brand}"
    if target_col not in parieurs.columns:
        return 0.0
    n_brand = int(parieurs[target_col].sum())
    total = 0
    for b in COMPETITORS:
        c = f"A_Deja_Parie_{b}"
        if c in parieurs.columns:
            total += int(parieurs[c].sum())
    if total == 0:
        return 0.0
    return round(n_brand / total * 100, 1)


def calc_pdm_volume_all_brands(df: pd.DataFrame) -> dict:
    """PDM Volume Q5 pour toutes les marques. Somme = 100%."""
    return {b: calc_pdm_volume(df, b) for b in brands_in_scope(df)}


def calc_pdm_valeur(df: pd.DataFrame, brand: str = "Betclic") -> float:
    """Part de Marché en VALEUR monétaire (% du marché).

    Formule : Σ(Q10 FCFA chez parieurs Q6=brand) / Σ(Q10 FCFA tous parieurs) × 100

    Interprétation business : sur 100 F CFA misés mensuellement sur le marché
    ivoirien des paris, X% vont chez Betclic (selon les déclarations Q6+Q10).
    """
    parieurs = get_parieurs(df)
    if "Montant_Mise_Mensuel_FCFA" not in parieurs.columns:
        return 0.0
    total_market = parieurs["Montant_Mise_Mensuel_FCFA"].dropna().sum()
    if total_market == 0:
        return 0.0
    brand_users = parieurs[parieurs["Marque_Principale_Utilisee"] == brand]
    brand_revenue = brand_users["Montant_Mise_Mensuel_FCFA"].dropna().sum()
    return round(float(brand_revenue) / float(total_market) * 100, 1)


def calc_pdm_valeur_all_brands(df: pd.DataFrame) -> dict:
    """PDM Valeur par marque (toutes marques COMPETITORS)."""
    return {b: calc_pdm_valeur(df, b) for b in brands_in_scope(df)}


def calc_wallet_share_distribution(df: pd.DataFrame, brand: str = "Betclic") -> dict:
    """Distribution des tranches de mise mensuelle Q10 chez les parieurs Q6==brand."""
    parieurs = get_parieurs(df)
    if len(parieurs) == 0 or "Montant_Mise_Mensuel" not in parieurs.columns:
        return {}
    target = parieurs[parieurs["Marque_Principale_Utilisee"] == brand]
    valid = target["Montant_Mise_Mensuel"].dropna()
    if len(valid) == 0:
        return {}
    return valid.value_counts(normalize=True).apply(lambda x: round(x * 100, 1)).to_dict()


def calc_sport_distribution(df: pd.DataFrame) -> dict:
    """Distribution multi-réponse Q11 : pour chaque sport, % de parieurs qui le citent.

    Q11 accepte plusieurs réponses (508 parieurs citent 1 sport, 152 en citent 2,
    107 en citent 3). On agrège donc tous les sports cités et on rapporte
    au nombre de parieurs. La somme peut dépasser 100% (multi-réponse).
    """
    parieurs = get_parieurs(df)
    if len(parieurs) == 0:
        return {}
    n = len(parieurs)
    out = {}
    for _, sport in SPORT_MAP.items():
        col = f"Sport_{sport.replace(' ', '_').replace('/', '_')}"
        if col in parieurs.columns:
            count = int(parieurs[col].sum())
            if count > 0:
                label = sport.replace(" (préciser) :", "").strip()
                out[label] = round(count / n * 100, 1)
    return dict(sorted(out.items(), key=lambda x: -x[1]))


def calc_pari_type_distribution(df: pd.DataFrame) -> dict:
    parieurs = get_parieurs(df)
    if "Type_Pari_Prefere" not in parieurs.columns:
        return {}
    valid = parieurs[parieurs["Type_Pari_Prefere"].notna()]
    if len(valid) == 0:
        return {}
    return valid["Type_Pari_Prefere"].value_counts(normalize=True).apply(lambda x: round(x * 100, 1)).to_dict()


def calc_paiement_distribution(df: pd.DataFrame) -> dict:
    parieurs = get_parieurs(df)
    if "Moyen_Paiement_Principal" not in parieurs.columns:
        return {}
    valid = parieurs[parieurs["Moyen_Paiement_Principal"].notna()]
    if len(valid) == 0:
        return {}
    return valid["Moyen_Paiement_Principal"].value_counts(normalize=True).apply(lambda x: round(x * 100, 1)).to_dict()


def calc_image_scores(df: pd.DataFrame, brand: str = "Betclic") -> dict:
    """Average image attribute scores for a given brand (among those who know it).

    For Betclic uses the base columns (Image_Modernite, ...).
    For competitors uses suffixed columns (Image_Modernite_1XBET, ...).
    """
    n_col = f"Notoriete_Totale_{brand}"
    aware = df[df.get(n_col, pd.Series([0]*len(df))) == 1]
    result = {}
    for col, label in IMAGE_ATTRIBUTES.items():
        target_col = col if brand == "Betclic" else f"{col}_{brand}"
        # Attribut non mesuré dans les vagues sélectionnées (ex. Cash out en V1/V2) : omis
        if target_col in aware.columns:
            vals = aware[target_col].dropna()
            if len(vals) > 0:
                result[label] = round(vals.mean(), 2)
    return result


def calc_image_scores_main_brands(df: pd.DataFrame, brands=None) -> dict:
    """Image scores per brand for the main competitors. Returns {brand: {attr: score}}."""
    out = {}
    for b in (brands or get_main_competitors(df)):
        out[b] = calc_image_scores(df, b)
    return out


# ──────────────────────────────────────────────
# PRINCIPAUX CONCURRENTS (sélection dynamique)
# ──────────────────────────────────────────────
N_MAIN_COMPETITORS = 5  # Betclic + 4 concurrents


def _rank(scores: dict) -> dict:
    return {b: i for i, b in enumerate(sorted(scores, key=lambda x: -(scores[x] or 0)))}


def get_main_competitors(df: pd.DataFrame, n: int = N_MAIN_COMPETITORS) -> list:
    """Betclic + les n-1 concurrents les plus forts, recalculés sur les données.

    Calcul sur la vague la plus récente du périmètre filtré : on classe les
    marques par notoriété totale et par pénétration (Q5), on additionne les deux
    rangs et on garde les mieux placées. La liste suit donc le marché : une
    marque qui monte (ex. 1WIN) entre automatiquement dans les comparatifs.
    """
    if df is None or not len(df) or "Vague" not in df.columns:
        return list(MAIN_COMPETITORS)
    waves = sort_vagues(df["Vague"].dropna().unique().tolist())
    d = df[df["Vague"] == waves[-1]] if waves else df
    brands = [b for b in brands_in_scope(d) if b != "Betclic"]
    if not brands:
        return list(MAIN_COMPETITORS)
    notor = {b: calc_notoriete_totale(d, b) for b in brands}
    pen = {b: calc_penetration(d, b) for b in brands}
    rn, rp = _rank(notor), _rank(pen)
    ordered = sorted(brands, key=lambda b: (rn[b] + rp[b], -pen[b], -notor[b]))
    return ["Betclic"] + ordered[: max(n - 1, 0)]


def keep_brands(scores: dict, brands, others_label: Optional[str] = None, total: float = 100.0) -> dict:
    """Restreint {marque: valeur} aux marques retenues (dans leur ordre).

    others_label : ajoute une ligne "Autres marques" = total - somme des marques
    retenues, pour les indicateurs qui somment à 100 % (PDM, marque principale).
    """
    out = {b: scores[b] for b in brands if b in scores and scores[b] is not None}
    if others_label:
        rest = round(total - sum(out.values()), 1)
        if rest > 0.05:
            out[others_label] = rest
    return out


def calc_satisfaction(df: pd.DataFrame, brand: str = "Betclic") -> float:
    """Satisfaction moyenne (/5) parmi les parieurs dont la marque principale (Q6) = brand.

    T_Q14_1 (Satisfaction_Globale_Betclic dans le df normalisé) capture la
    satisfaction du répondant vis-à-vis de SA marque principale Q6. On filtre
    donc Q6==brand pour avoir la satisfaction de chaque marque.
    """
    target = df[df.get("Marque_Principale_Utilisee").astype(str) == brand]
    if "Satisfaction_Globale_Betclic" not in target.columns:
        return 0.0
    vals = target["Satisfaction_Globale_Betclic"].dropna()
    if len(vals) == 0:
        return 0.0
    return round(vals.mean(), 2)


def calc_satisfaction_all_brands(df: pd.DataFrame) -> dict:
    """Satisfaction (/5) per brand. Base : parieurs dont Q6 = chaque marque."""
    return {b: calc_satisfaction(df, b) for b in brands_in_scope(df)}


def calc_nps_by_brand(df: pd.DataFrame, brand: str = "Betclic") -> dict:
    """NPS per brand (parieurs Q6 = brand). Q15 capture le NPS de leur marque."""
    target = df[df.get("Marque_Principale_Utilisee").astype(str) == brand]
    if "NPS_Categorie" not in target.columns:
        return {"nps": 0, "promoteurs": 0, "passifs": 0, "detracteurs": 0, "n": 0}
    nps_data = target["NPS_Categorie"].dropna()
    n = len(nps_data)
    if n == 0:
        return {"nps": 0, "promoteurs": 0, "passifs": 0, "detracteurs": 0, "n": 0}
    counts = nps_data.value_counts()
    prom = counts.get("Promoteur", 0)
    det = counts.get("Détracteur", 0)
    pas = counts.get("Passif", 0)
    return {
        "nps": round((prom - det) / n * 100, 1),
        "promoteurs": round(prom / n * 100, 1),
        "passifs": round(pas / n * 100, 1),
        "detracteurs": round(det / n * 100, 1),
        "n": n,
    }


def calc_nps_all_brands(df: pd.DataFrame) -> dict:
    """NPS score par marque (uniquement le score, pas le détail)."""
    return {b: calc_nps_by_brand(df, b)["nps"] for b in brands_in_scope(df)}


def calc_nps(df: pd.DataFrame) -> dict:
    users = get_utilisateurs_betclic(df)
    if "NPS_Categorie" not in users.columns:
        return {"nps": 0, "promoteurs": 0, "passifs": 0, "detracteurs": 0}
    nps_data = users["NPS_Categorie"].dropna()
    total = len(nps_data)
    if total == 0:
        return {"nps": 0, "promoteurs": 0, "passifs": 0, "detracteurs": 0}
    promoteurs = (nps_data == "Promoteur").sum() / total * 100
    passifs = (nps_data == "Passif").sum() / total * 100
    detracteurs = (nps_data.isin(["Détracteur", "Detracteur"])).sum() / total * 100
    return {
        "nps": round(promoteurs - detracteurs, 1),
        "promoteurs": round(promoteurs, 1),
        "passifs": round(passifs, 1),
        "detracteurs": round(detracteurs, 1),
    }


def calc_churn_risk(df: pd.DataFrame) -> dict:
    users = get_utilisateurs_betclic(df)
    if "Risque_Churn" not in users.columns:
        return {}
    valid = users["Risque_Churn"].dropna()
    total = len(valid)
    if total == 0:
        return {}
    return {
        "Faible": round((valid == "Faible").sum() / total * 100, 1),
        "Modéré": round((valid == "Modéré").sum() / total * 100, 1),
        "Élevé": round((valid == "Élevé").sum() / total * 100, 1),
    }


def calc_irritants(df: pd.DataFrame) -> dict:
    """Principaux irritants : verbatims Q16 (raison du NPS) parmi les Détracteurs.

    Q16 contient le "pourquoi" de la note NPS Q15. Pour les Promoteurs (9-10)
    c'est un compliment, pour les Détracteurs (0-6) c'est une critique réelle.
    On filtre donc strictement sur les Détracteurs pour avoir les vrais
    irritants.
    """
    users = get_utilisateurs_betclic(df)
    if "Principal_Irritant" not in users.columns or "NPS_Categorie" not in users.columns:
        return {}
    detractors = users[users["NPS_Categorie"] == "Détracteur"]
    valid = detractors["Principal_Irritant"].dropna()
    if len(valid) == 0:
        return {}
    counts = valid.value_counts()
    top = counts.head(10)
    pct = (top / len(valid) * 100).round(1)
    return pct.to_dict()


def calc_motifs_satisfaction(df: pd.DataFrame) -> dict:
    """Symétrique : top motifs de satisfaction (verbatims Q16 des Promoteurs)."""
    users = get_utilisateurs_betclic(df)
    if "Principal_Irritant" not in users.columns or "NPS_Categorie" not in users.columns:
        return {}
    promoters = users[users["NPS_Categorie"] == "Promoteur"]
    valid = promoters["Principal_Irritant"].dropna()
    if len(valid) == 0:
        return {}
    counts = valid.value_counts()
    top = counts.head(10)
    pct = (top / len(valid) * 100).round(1)
    return pct.to_dict()


def load_verbatim_themes(vague: str = "Vague 1") -> Optional[dict]:
    """Charge les thèmes verbatim générés par scripts/build_verbatim_themes.py.

    Retourne None si le fichier n'existe pas (ex: nouvelle vague pas encore
    thématisée). La vue Satisfaction bascule alors sur l'affichage brut.
    """
    import json
    target = (
        Path(__file__).resolve().parent.parent
        / "data" / "verbatim_themes" / f"{vague.replace(' ', '_')}.json"
    )
    if not target.exists():
        return None
    try:
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def calc_intention(df: pd.DataFrame) -> dict:
    users = get_utilisateurs_betclic(df)
    if "Intention_Reutilisation" not in users.columns:
        return {}
    valid = users["Intention_Reutilisation"].dropna()
    total = len(valid)
    if total == 0:
        return {}
    order = ["Certainement", "Probablement", "Incertain", "Probablement pas"]
    return {cat: round((valid == cat).sum() / total * 100, 1) for cat in order}


def calc_intention_positive(df: pd.DataFrame) -> float:
    intent = calc_intention(df)
    return round(intent.get("Certainement", 0) + intent.get("Probablement", 0), 1)


# ──────────────────────────────────────────────
# MULTI-VAGUE COMPARISON HELPERS
# ──────────────────────────────────────────────

def calc_kpi_by_vague(df: pd.DataFrame, calc_func, **kwargs) -> dict:
    """Calculate a KPI for each vague separately."""
    result = {}
    all_vagues = sort_vagues(df["Vague"].dropna().unique().tolist())
    _build_dynamic_vague_labels(all_vagues)
    for vague in all_vagues:
        sub = df[df["Vague"] == vague]
        result[vague] = calc_func(sub, **kwargs) if len(sub) > 0 else None
    return result


def calc_delta(current, previous) -> tuple:
    if current is None or previous is None:
        return None, "neutral"
    delta = round(current - previous, 1)
    if delta > 0:
        return f"+{delta}", "up"
    elif delta < 0:
        return str(delta), "down"
    return "0", "neutral"


def get_latest_vague(vague_dict: dict):
    sorted_keys = sorted(
        [k for k, v in vague_dict.items() if v is not None],
        key=lambda x: int(x.replace("Vague ", "")) if x.replace("Vague ", "").isdigit() else 999,
        reverse=True,
    )
    return vague_dict[sorted_keys[0]] if sorted_keys else None


def get_previous_vague(vague_dict: dict):
    sorted_keys = sorted(
        [k for k, v in vague_dict.items() if v is not None],
        key=lambda x: int(x.replace("Vague ", "")) if x.replace("Vague ", "").isdigit() else 999,
    )
    return vague_dict[sorted_keys[-2]] if len(sorted_keys) >= 2 else None


# ──────────────────────────────────────────────
# GEO ANALYSIS
# ──────────────────────────────────────────────

def calc_kpi_by_city(df: pd.DataFrame, calc_func, **kwargs) -> dict:
    result = {}
    for city in CITIES:
        sub = df[df["Ville"] == city]
        if len(sub) > 0:
            result[city] = calc_func(sub, **kwargs)
    return result


# Communes d'Abidjan ordonnées par taille de base typique (peut être ajusté)
ABIDJAN_COMMUNES = [
    "Attécoubé", "Cocody", "Treichville", "Adjamé", "Anyama",
    "Abobo", "Bingerville", "Marcory", "Yopougon", "Plateau", "Koumassi",
]


def get_communes_in_data(df: pd.DataFrame, min_base: int = 10) -> list:
    """Retourne les communes présentes dans le df avec base >= min_base."""
    if "Commune" not in df.columns:
        return []
    counts = df["Commune"].dropna().value_counts()
    return [c for c in counts.index if counts[c] >= min_base]


def calc_kpi_by_commune(df: pd.DataFrame, calc_func, min_base: int = 10, **kwargs) -> dict:
    """Compute a KPI per commune (uniquement Abidjan, communes avec base ≥ min_base)."""
    if "Commune" not in df.columns:
        return {}
    result = {}
    valid_communes = get_communes_in_data(df, min_base)
    for commune in valid_communes:
        sub = df[df["Commune"] == commune]
        if len(sub) > 0:
            result[commune] = calc_func(sub, **kwargs)
    return result


# ──────────────────────────────────────────────
# FUNNEL DATA
# ──────────────────────────────────────────────

def calc_funnel(df: pd.DataFrame, brand: str = "Betclic") -> dict:
    """Funnel de conversion **monotonique décroissant** pour la marque.

    Base unique = échantillon total (pour que la décroissance soit garantie).
    Inclusion stricte :
        Notoriété Totale  ⊇  Notoriété Spontanée  ⊇  Considération
                          ⊇  Pénétration / Essai  ⊇  Préférence

    Note métier :
      - Q13 (intention d'essayer Betclic) est posée UNIQUEMENT aux parieurs
        non-Betclic (Q6≠Betclic). La Considération unit Q5=oui et Q13 fort.
      - TOM (Q1A) est volontairement hors funnel car non-emboîté avec
        Pénétration : un répondant peut citer Betclic en 1er sans avoir essayé,
        ou avoir essayé sans le citer en 1er.
    """
    n = len(df)
    if n == 0:
        return {}

    notor_total = df.get(f"Notoriete_Totale_{brand}", pd.Series([0]*n)).astype(int)
    notor_spont = df.get(f"Notoriete_Spontanee_{brand}", pd.Series([0]*n)).astype(int)
    consid = df.get(f"Consideration_{brand}", pd.Series([0]*n)).astype(int)
    essai = df.get(f"A_Deja_Parie_{brand}", pd.Series([0]*n)).astype(int)
    marque_principale = (
        df.get("Marque_Principale_Utilisee").astype(str) == brand
    ).astype(int) if "Marque_Principale_Utilisee" in df.columns else pd.Series([0]*n)

    return {
        "Notoriété Totale (Q1A+Q1B+Q1C)": round(notor_total.sum() / n * 100, 1),
        "Notoriété Spontanée (Q1A+Q1B)": round(notor_spont.sum() / n * 100, 1),
        "Considération (Q5 ∪ Q13 fort)": round(consid.sum() / n * 100, 1),
        "Pénétration / Essai (Q5)": round(essai.sum() / n * 100, 1),
        "Préférence (Q6 = marque principale)": round(marque_principale.sum() / n * 100, 1),
    }


def calc_funnel_with_counts(df: pd.DataFrame, brand: str = "Betclic") -> list:
    """Funnel structure with explicit counts and base for display (returns list of dicts)."""
    pct = calc_funnel(df, brand)
    n = len(df)
    return [
        {"step": step, "pct": value, "count": int(round(value / 100 * n)), "base": n}
        for step, value in pct.items()
    ]


# ──────────────────────────────────────────────
# CASINO EN LIGNE (Section 5B, à partir de V4)
# ──────────────────────────────────────────────
# Conventions de base (alignées sur les KPIs paris sportifs) :
#   - Notoriété de l'offre, pénétration : base = échantillon total interrogé
#   - Marque casino principale, fréquence, jeux : base = joueurs casino (QC3 = Oui)

def get_casino_base(df: pd.DataFrame) -> pd.DataFrame:
    """Répondants des vagues où la section casino a été posée."""
    if "Casino_Statut" not in df.columns:
        return df.iloc[0:0]
    return df[df["Casino_Statut"].notna()]


def get_casino_joueurs(df: pd.DataFrame) -> pd.DataFrame:
    """Joueurs casino : ont déjà joué en ligne (actifs 6 mois + anciens)."""
    base = get_casino_base(df)
    return base[base["Casino_Joueur"] == 1]


def casino_brands_in_scope(df: pd.DataFrame) -> list:
    base = get_casino_base(df)
    return [
        b for b in COMPETITORS
        if f"Casino_Offre_{b}" in base.columns and base[f"Casino_Offre_{b}"].notna().any()
    ]


def _pct(num, den) -> float:
    return round(float(num) / float(den) * 100, 1) if den else 0.0


def calc_casino_statut(df: pd.DataFrame) -> dict:
    """Répartition QC3 (actif 6 mois / ancien / non-joueur). Base = échantillon total."""
    base = get_casino_base(df)
    n = len(base)
    return {s: _pct((base["Casino_Statut"] == s).sum(), n) for s in CASINO_STATUTS} if n else {}


def calc_casino_penetration(df: pd.DataFrame) -> float:
    """% de l'échantillon ayant déjà joué au casino en ligne (QC3 = Oui)."""
    base = get_casino_base(df)
    return _pct(base["Casino_Joueur"].sum(), len(base)) if len(base) else 0.0


def calc_casino_penetration_active(df: pd.DataFrame) -> float:
    """% de l'échantillon ayant joué au casino en ligne au cours des 6 derniers mois."""
    base = get_casino_base(df)
    return _pct(base["Casino_Joueur_Actif"].sum(), len(base)) if len(base) else 0.0


def calc_casino_offre_notoriete(df: pd.DataFrame, brand: str = "Betclic") -> float:
    """QC1 : % de l'échantillon sachant que la marque propose du casino."""
    base = get_casino_base(df)
    col = f"Casino_Offre_{brand}"
    if col not in base.columns or len(base) == 0:
        return 0.0
    return _pct(base[col].fillna(0).sum(), len(base))


def calc_casino_offre_notoriete_all(df: pd.DataFrame) -> dict:
    return {b: calc_casino_offre_notoriete(df, b) for b in casino_brands_in_scope(df)}


def calc_casino_penetration_brand(df: pd.DataFrame, brand: str = "Betclic") -> float:
    """QC4 : % de l'échantillon ayant déjà joué au casino sur la marque."""
    base = get_casino_base(df)
    col = f"Casino_A_Joue_{brand}"
    if col not in base.columns or len(base) == 0:
        return 0.0
    return _pct(base[col].fillna(0).sum(), len(base))


def calc_casino_penetration_all(df: pd.DataFrame) -> dict:
    return {b: calc_casino_penetration_brand(df, b) for b in casino_brands_in_scope(df)}


def calc_casino_marque_principale_all(df: pd.DataFrame) -> dict:
    """QC5 : marque sur laquelle les joueurs casino jouent le plus. Base = répondants QC5."""
    joueurs = get_casino_joueurs(df)
    if "Casino_Marque_Principale" not in joueurs.columns:
        return {}
    valid = joueurs["Casino_Marque_Principale"].dropna()
    n = len(valid)
    return {b: _pct((valid == b).sum(), n) for b in casino_brands_in_scope(df)} if n else {}


def calc_casino_marque_principale(df: pd.DataFrame, brand: str = "Betclic") -> float:
    return calc_casino_marque_principale_all(df).get(brand, 0.0)


def calc_casino_pdm_volume_all(df: pd.DataFrame) -> dict:
    """PDM Volume casino : essais QC4 de la marque / somme des essais QC4 toutes marques."""
    base = get_casino_base(df)
    counts = {}
    for b in casino_brands_in_scope(df):
        col = f"Casino_A_Joue_{b}"
        counts[b] = int(base[col].fillna(0).sum()) if col in base.columns else 0
    total = sum(counts.values())
    return {b: _pct(c, total) for b, c in counts.items()} if total else {}


def calc_casino_pdm_volume(df: pd.DataFrame, brand: str = "Betclic") -> float:
    return calc_casino_pdm_volume_all(df).get(brand, 0.0)


CASINO_FREQ_ORDER = [
    "Tous les jours ou presque", "Plusieurs fois par semaine", "Une fois par semaine",
    "Plusieurs fois par mois", "Une fois par mois ou moins",
]


def calc_casino_frequence(df: pd.DataFrame) -> dict:
    """QC6 : fréquence de jeu casino. Base = joueurs ayant répondu."""
    joueurs = get_casino_joueurs(df)
    if "Casino_Frequence" not in joueurs.columns:
        return {}
    valid = joueurs["Casino_Frequence"].dropna()
    n = len(valid)
    return {k: _pct((valid == k).sum(), n) for k in CASINO_FREQ_ORDER} if n else {}


def calc_casino_jeux(df: pd.DataFrame) -> dict:
    """QC7 : types de jeux (multi-réponse). Base = joueurs ayant répondu à QC7."""
    joueurs = get_casino_joueurs(df)
    cols = [f"Casino_Jeu_{i}" for i in CASINO_GAMES if f"Casino_Jeu_{i}" in joueurs.columns]
    if not cols:
        return {}
    answered = joueurs[joueurs[cols].fillna(0).sum(axis=1) > 0]
    n = len(answered)
    if not n:
        return {}
    out = {
        CASINO_GAMES[i]: _pct(answered[f"Casino_Jeu_{i}"].sum(), n)
        for i in CASINO_GAMES if f"Casino_Jeu_{i}" in answered.columns
    }
    return dict(sorted(out.items(), key=lambda x: -x[1]))


CASINO_PRATIQUE_LABELS = {
    "Vous jouez surtout des paris sportifs, le casino de temps en temps": "Surtout paris sportifs",
    "Vous jouez autant l'un que l'autre": "Autant l'un que l'autre",
    "Vous jouez surtout du casino, les paris sportifs de temps en temps": "Surtout casino",
}


def calc_casino_pratique(df: pd.DataFrame) -> dict:
    """QC8 : arbitrage paris sportifs / casino. Base = joueurs casino ayant répondu."""
    joueurs = get_casino_joueurs(df)
    if "Casino_Pratique" not in joueurs.columns:
        return {}
    valid = joueurs["Casino_Pratique"].dropna()
    n = len(valid)
    if not n:
        return {}
    return {lbl: _pct((valid == raw).sum(), n) for raw, lbl in CASINO_PRATIQUE_LABELS.items()}


def calc_casino_funnel(df: pd.DataFrame, brand: str = "Betclic") -> dict:
    """Entonnoir casino de la marque (base = échantillon total, étapes emboîtées) :
    notoriété de la marque, sait qu'elle propose du casino, a déjà joué, marque casino principale.
    """
    base = get_casino_base(df)
    n = len(base)
    if not n:
        return {}
    zeros = pd.Series(0, index=base.index)
    notor = base.get(f"Notoriete_Totale_{brand}", zeros).fillna(0) == 1
    offre = base.get(f"Casino_Offre_{brand}", zeros).fillna(0) == 1
    joue = base.get(f"Casino_A_Joue_{brand}", zeros).fillna(0) == 1
    princ = base.get("Casino_Marque_Principale", pd.Series(None, index=base.index)) == brand
    return {
        "Notoriété de la marque": _pct(notor.sum(), n),
        "Sait que la marque propose du casino (QC1)": _pct((notor & offre).sum(), n),
        "A déjà joué à son casino (QC4)": _pct((notor & offre & joue).sum(), n),
        "Marque casino principale (QC5)": _pct((notor & offre & joue & princ).sum(), n),
    }


def calc_casino_cross_sell(df: pd.DataFrame, brand: str = "Betclic") -> dict:
    """Passerelle paris sportifs vers casino pour une marque.

    - taux_parieurs : parmi ceux qui ont déjà parié sur la marque (Q5),
      % qui ont aussi joué à son casino (QC4).
    - taux_conversion_offre : parmi ceux qui savent que la marque propose
      du casino (QC1), % qui y ont joué (QC4).
    """
    base = get_casino_base(df)
    if not len(base):
        return {}
    zeros = pd.Series(0, index=base.index)
    paris = base.get(f"A_Deja_Parie_{brand}", zeros).fillna(0) == 1
    offre = base.get(f"Casino_Offre_{brand}", zeros).fillna(0) == 1
    joue = base.get(f"Casino_A_Joue_{brand}", zeros).fillna(0) == 1
    return {
        "n_parieurs": int(paris.sum()),
        "taux_parieurs": _pct((paris & joue).sum(), paris.sum()),
        "n_offre": int(offre.sum()),
        "taux_conversion_offre": _pct((offre & joue).sum(), offre.sum()),
    }


def get_casino_main_brands(df: pd.DataFrame, n: int = N_MAIN_COMPETITORS + 1) -> list:
    """Betclic + les principaux concurrents casino, recalculés sur les données.

    Même logique que get_main_competitors, sur la vague casino la plus récente :
    somme des rangs en notoriété de l'offre casino (QC1) et en pénétration
    casino (QC4). Une marque de plus que pour les paris, le casino comptant des
    acteurs spécialisés (ex. 1WIN).
    """
    base = get_casino_base(df)
    if not len(base):
        return ["Betclic"]
    waves = sort_vagues(base["Vague"].dropna().unique().tolist())
    d = df[df["Vague"] == waves[-1]]
    offre = calc_casino_offre_notoriete_all(d)
    pen = calc_casino_penetration_all(d)
    brands = [b for b in offre if b != "Betclic"]
    if not brands:
        return ["Betclic"]
    ro = _rank({b: offre[b] for b in brands})
    rp = _rank({b: pen.get(b, 0) for b in brands})
    ordered = sorted(brands, key=lambda b: (ro[b] + rp[b], -pen.get(b, 0), -offre[b]))
    return ["Betclic"] + ordered[: max(n - 1, 0)]
