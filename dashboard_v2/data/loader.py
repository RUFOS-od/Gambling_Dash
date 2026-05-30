"""
Data loader and KPI calculation engine for Betclic Brand Pulse Tracker.

Handles two file formats automatically:
  - RAW CAPI export (new): columns like QF1, Q1A, A_Q1B_1, T_Q12A_1, etc.
  - LEGACY normalized (fictional/old): columns like Vague, TOM_Marque_Citee, etc.

The raw format is transformed into the normalized schema on load, so all
downstream views/KPI functions keep using the same column names.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent.parent

# ──────────────────────────────────────────────
# REFERENCE LISTS — updated to match real V1 questionnaire
# ──────────────────────────────────────────────

# 14 competing sports betting brands tracked in the questionnaire
COMPETITORS = [
    "Betclic", "Chopbet", "1XBET", "Sportcash", "BetPawa",
    "Melbet", "Premier Bet", "BetMomo", "AkwaBet", "YellowBet",
    "Betway", "Afropari", "Paripesa", "Bet365",
]

# Marques principales à afficher dans les comparaisons concurrentielles
# (basé sur le top notoriété + part de marché sur le marché ivoirien)
MAIN_COMPETITORS = ["Betclic", "1XBET", "Sportcash", "Melbet", "BetMomo"]

VAGUE_LABELS = {"Vague 1": "V1 — Mai 2026"}
VAGUE_SHORT = {"Vague 1": "V1"}
VAGUE_MONTHS = {"Vague 1": "Mai 2026"}


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
            VAGUE_LABELS[v_name] = f"V{num} — {months_fr[month_idx][:3]} {year}"
        except (ValueError, TypeError):
            VAGUE_SHORT[v_name] = v_name
            VAGUE_MONTHS[v_name] = ""
            VAGUE_LABELS[v_name] = v_name


# 13 image attributes (Q12) — matches the real questionnaire
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
}

CITIES = ["Abidjan", "Bouaké", "Yamoussoukro", "San Pedro", "Daloa", "Korhogo", "Abengourou"]


# ──────────────────────────────────────────────
# RAW → NORMALIZED ADAPTER
# ──────────────────────────────────────────────

# Map raw index suffix (_1.._14) to brand name (as in COMPETITORS)
RAW_BRAND_BY_INDEX = {
    1: "Betclic", 2: "Chopbet", 3: "1XBET", 4: "Sportcash",
    5: "BetPawa", 6: "Melbet", 7: "Premier Bet", 8: "BetMomo",
    9: "AkwaBet", 10: "YellowBet", 11: "Betway", 12: "Afropari",
    13: "Paripesa", 14: "Bet365",
}
# Map Q12 letter (A..N) to brand
RAW_BRAND_BY_LETTER = {
    "A": "Betclic", "B": "Chopbet", "C": "1XBET", "D": "Sportcash",
    "E": "BetPawa", "F": "Melbet", "G": "Premier Bet", "H": "BetMomo",
    "I": "AkwaBet", "J": "YellowBet", "K": "Betway", "L": "Afropari",
    "M": "Paripesa", "N": "Bet365",
}
# Map Q12 attribute suffix (_1.._13) to normalized image column
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
}

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
    df["Profession"] = df_raw.get("Q28", "")

    # ── Type respondant ──
    type_rep = df_raw["Type_Rep"].astype(str).str.strip()
    df["Type_Repondant"] = type_rep.map({
        "PARIEUR": "Parieur",
        "NON  PARIEUR": "Non-parieur",
        "NON PARIEUR": "Non-parieur",
    }).fillna(type_rep)
    df["Segment_Parieur"] = df["Type_Repondant"]
    df["Frequence_Paris"] = df_raw.get("Q8", None)
    df["Frequence_Paris_Mois"] = df["Frequence_Paris"]
    df["Montant_Mise_Mensuel"] = df_raw.get("Q10", None)
    # Numeric version (FCFA, milieu de tranche) — utilisé pour les agrégations pivot
    df["Montant_Mise_Mensuel_FCFA"] = df["Montant_Mise_Mensuel"].map(Q10_MIDPOINTS_FCFA)

    # ── TOM (Top of Mind) ──
    tom_raw = df_raw["Q1A"].astype(str).str.strip()
    df["TOM_Marque_Citee"] = tom_raw.where(tom_raw.isin(COMPETITORS), None)

    # ── Awareness per brand (TOM + spontaneous + aided + total) ──
    # User-validated formula:
    #   Notoriete Totale  = Q1A=brand OR A_Q1B_idx OR A_Q1C_idx   (Q1A + Q1B + Q1C)
    #   Notoriete Spont.  = Q1A=brand OR A_Q1B_idx                (Q1A + Q1B)
    #   Notoriete Aidee   = A_Q1C_idx only                        (Q1C alone)
    q1a = df_raw["Q1A"].astype(str).str.strip()
    for idx, brand in RAW_BRAND_BY_INDEX.items():
        col_b = f"A_Q1B_{idx}"
        col_c = f"A_Q1C_{idx}"
        is_tom = (q1a == brand).astype(int).values
        spont_b = _str_yes_no(df_raw[col_b]).values if col_b in df_raw.columns else np.zeros(n, dtype=int)
        aided_c = _str_yes_no(df_raw[col_c]).values if col_c in df_raw.columns else np.zeros(n, dtype=int)
        df[f"Notoriete_Spontanee_{brand}"] = ((is_tom == 1) | (spont_b == 1)).astype(int)
        df[f"Notoriete_Aidee_{brand}"] = aided_c
        df[f"Notoriete_Totale_{brand}"] = (
            (is_tom == 1) | (spont_b == 1) | (aided_c == 1)
        ).astype(int)

    # ── Usage ──
    q6 = df_raw.get("Q6", pd.Series([None] * n))
    df["Marque_Principale_Utilisee"] = q6
    df["Utilise_Betclic"] = (q6.astype(str) == "Betclic").astype(int)

    # Multi-app: count how many A_Q5_X are non-"0"
    a_q5_cols = [f"A_Q5_{i}" for i in range(1, 15) if f"A_Q5_{i}" in df_raw.columns]
    if a_q5_cols:
        nb_apps = sum(_str_yes_no(df_raw[c]) for c in a_q5_cols)
        df["Nb_Apps_Utilisees"] = nb_apps.values
        df["Multi_Application"] = (nb_apps.values >= 2).astype(int)
    else:
        df["Nb_Apps_Utilisees"] = 0
        df["Multi_Application"] = 0

    # Per-brand "has bet on" flag (from A_Q5_X)
    for idx, brand in RAW_BRAND_BY_INDEX.items():
        col = f"A_Q5_{idx}"
        df[f"A_Deja_Parie_{brand}"] = _str_yes_no(df_raw[col]).values if col in df_raw.columns else 0

    # ── Sport préféré : first non-"0" A_Q11_X ──
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
    # Q13 = "Probabilité de recommander Q6 (NPS)" — asked to parieurs only.
    # For non-parieurs Q13 is NaN, so the flag = 0.
    intent_raw = df_raw.get("Q13", pd.Series([None] * n)).astype(str).str.strip()
    intent_strong = (
        (intent_raw == "Très probablement") | (intent_raw == "Probablement")
    ).astype(int)
    df["Intention_Recommande_Forte"] = intent_strong.values

    # ── Considération (user-validated): Q5 (a déjà parié) OU Q13 ∈ {Très/Probablement} ──
    # Per-row flag. A_Deja_Parie_Betclic was set above.
    for brand in RAW_BRAND_BY_INDEX.values():
        col = f"A_Deja_Parie_{brand}"
        if col in df.columns:
            df[f"Consideration_{brand}"] = (
                (df[col] == 1) | (df["Intention_Recommande_Forte"] == 1)
            ).astype(int)
        else:
            df[f"Consideration_{brand}"] = df["Intention_Recommande_Forte"]
    # ── Préférence (user-validated): Q6 == "Betclic" ──
    df["Preference_Betclic"] = df["Utilise_Betclic"]

    # ── Image attributes for Betclic (Q12A) ──
    for idx, attr_col in RAW_IMAGE_ATTRS.items():
        raw_col = f"T_Q12A_{idx}"
        df[attr_col] = pd.to_numeric(df_raw[raw_col], errors="coerce") if raw_col in df_raw.columns else None

    # ── Image attributes per competitor (for radar/positioning views) ──
    for letter, brand in RAW_BRAND_BY_LETTER.items():
        for idx, attr_col in RAW_IMAGE_ATTRS.items():
            raw_col = f"T_Q12{letter}_{idx}"
            if raw_col in df_raw.columns:
                df[f"{attr_col}_{brand}"] = pd.to_numeric(df_raw[raw_col], errors="coerce")

    # ── Importance (Q4) — used by some views ──
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
    for idx, brand in RAW_BRAND_BY_INDEX.items():
        col = f"A_Q18_{idx}"
        df[f"Rappel_Campagne_{brand}"] = (
            _str_yes_no(df_raw[col]).values if col in df_raw.columns else 0
        )

    # Q21 = recall World Cup campaign
    q21 = df_raw.get("Q21", pd.Series([None] * n)).astype(str)
    df["Rappel_CDM_Betclic"] = q21.str.startswith("Oui").astype(int)

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

    # ── Date column for export engine ──
    df["Date_Interview"] = pd.to_datetime(df_raw.get("Date_Inter"), errors="coerce")

    return df


# ──────────────────────────────────────────────
# FILE DISCOVERY & LOADING
# ──────────────────────────────────────────────

def detect_available_waves() -> list:
    """Auto-detect all Bases_Betclic_BrandPulse_Tracker_V*.xlsx files."""
    from data.validation import detect_wave_files
    return detect_wave_files(DATA_DIR)


@st.cache_data(ttl=3600)
def load_raw_data() -> pd.DataFrame:
    """Load and concatenate all available tracker bases (auto-detects format)."""
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


@st.cache_data(ttl=3600)
def load_waves_individually() -> dict:
    """Load each wave separately (for validation reports)."""
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

def apply_filters(df: pd.DataFrame, vagues=None, villes=None, genres=None, segments=None) -> pd.DataFrame:
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
    return {b: round((df["TOM_Marque_Citee"] == b).sum() / total * 100, 1) for b in COMPETITORS}


def calc_notoriete_totale(df: pd.DataFrame, brand: str = "Betclic") -> float:
    col = f"Notoriete_Totale_{brand}"
    if col not in df.columns:
        return 0.0
    total = len(df)
    if total == 0:
        return 0.0
    return round(df[col].sum() / total * 100, 1)


def calc_notoriete_all_brands(df: pd.DataFrame) -> dict:
    return {b: calc_notoriete_totale(df, b) for b in COMPETITORS}


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
    return {b: calc_rappel_campagne(df, b) for b in COMPETITORS}


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
    return {b: calc_penetration(df, b) for b in COMPETITORS}


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
        for b in COMPETITORS
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
    parieurs = get_parieurs(df)
    if len(parieurs) == 0 or "Sport_Prefere" not in parieurs.columns:
        return {}
    valid = parieurs[parieurs["Sport_Prefere"].notna()]
    if len(valid) == 0:
        return {}
    return valid["Sport_Prefere"].value_counts(normalize=True).apply(lambda x: round(x * 100, 1)).to_dict()


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
        if target_col in aware.columns:
            vals = aware[target_col].dropna()
            result[label] = round(vals.mean(), 2) if len(vals) > 0 else 0.0
        else:
            result[label] = 0.0
    return result


def calc_image_scores_main_brands(df: pd.DataFrame) -> dict:
    """Image scores per brand for the main competitors. Returns {brand: {attr: score}}."""
    out = {}
    for b in MAIN_COMPETITORS:
        out[b] = calc_image_scores(df, b)
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
    return {b: calc_satisfaction(df, b) for b in COMPETITORS}


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
    return {b: calc_nps_by_brand(df, b)["nps"] for b in COMPETITORS}


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
    users = get_utilisateurs_betclic(df)
    if "Principal_Irritant" not in users.columns:
        return {}
    valid = users["Principal_Irritant"].dropna()
    if len(valid) == 0:
        return {}
    # If the column contains free-text verbatims, group only the most frequent ones
    counts = valid.value_counts()
    top = counts.head(10)
    pct = (top / len(valid) * 100).round(1)
    return pct.to_dict()


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
    all_vagues = sorted(
        df["Vague"].dropna().unique().tolist(),
        key=lambda x: int(x.replace("Vague ", "")) if x.replace("Vague ", "").isdigit() else 999,
    )
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
