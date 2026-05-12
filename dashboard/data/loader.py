"""
Data loader and KPI calculation engine for Betclic Brand Pulse Tracker.
All KPIs are computed dynamically from the raw Excel bases (V1, V2, V3).
"""

import pandas as pd
import numpy as np
from pathlib import Path
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent.parent

COMPETITORS = [
    "Betclic", "1XBET", "Sportcash", "PremierBet", "Chopbet",
    "Melbet", "Betmomo", "AkwaBet", "Paripesa"
]

VAGUE_LABELS = {"Vague 1": "V1 — Jan 2026", "Vague 2": "V2 — Fév 2026", "Vague 3": "V3 — Mar 2026"}
VAGUE_SHORT = {"Vague 1": "V1", "Vague 2": "V2", "Vague 3": "V3"}
VAGUE_MONTHS = {"Vague 1": "Janvier 2026", "Vague 2": "Février 2026", "Vague 3": "Mars 2026"}

IMAGE_ATTRIBUTES = {
    "Image_Modernite": "Modernité",
    "Image_Fiabilite": "Fiabilité",
    "Image_Securite": "Sécurité",
    "Image_Rapidite_Paiements": "Rapidité Paiements",
    "Image_Proximite": "Proximité",
    "Image_Innovation": "Innovation",
    "Image_Qualite_App": "Qualité App",
    "Image_Simplicite": "Simplicité",
    "Image_Variete_Paris": "Variété Paris",
    "Image_Jeu_Responsable": "Jeu Responsable",
    "Image_Rapport_Qualite_Bonus": "Qualité/Bonus",
    "Image_Transparence": "Transparence",
}

CITIES = ["Abidjan", "Bouaké", "Yamoussoukro", "San Pedro", "Daloa", "Korhogo", "Abengourou"]


@st.cache_data(ttl=3600)
def load_raw_data() -> pd.DataFrame:
    """Load and concatenate all 3 raw tracker bases."""
    frames = []
    for v in [1, 2, 3]:
        fpath = DATA_DIR / f"Bases_Betclic_BrandPulse_Tracker_V{v}.xlsx"
        df = pd.read_excel(fpath, header=1)
        frames.append(df)
    data = pd.concat(frames, ignore_index=True)

    # Clean numeric columns
    numeric_cols = [
        "Frequence_Paris_Mois", "Notoriete_Totale_Betclic", "Notoriete_Aidee_Betclic",
        "Notoriete_Totale_1XBET", "Notoriete_Totale_Sportcash", "Notoriete_Totale_PremierBet",
        "Notoriete_Totale_Chopbet", "Notoriete_Totale_Melbet", "Notoriete_Totale_Betmomo",
        "Notoriete_Totale_AkwaBet", "Notoriete_Totale_Paripesa",
        "Rappel_Campagne_Betclic", "Utilise_Betclic", "Multi_Application",
        "Nb_Apps_Utilisees", "Part_Portefeuille_Betclic",
        "Consideration_Betclic", "Preference_Betclic",
        "Satisfaction_Globale_Betclic", "NPS_Score",
    ]
    for col in numeric_cols:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    for col in IMAGE_ATTRIBUTES:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    return data


@st.cache_data(ttl=3600)
def load_kpi_reference() -> pd.DataFrame:
    """Load the KPI reference file for validation."""
    fpath = DATA_DIR / "Betclic_BrandPulse_Tracker_KPIS_V1V2V3.xlsx"
    df = pd.read_excel(fpath, sheet_name=1, header=2)
    return df


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
# KPI CALCULATION FUNCTIONS
# ──────────────────────────────────────────────

def calc_tom(df: pd.DataFrame, brand: str = "Betclic") -> float:
    """Top-of-Mind: % of respondents citing brand first."""
    total = len(df)
    if total == 0:
        return 0.0
    return round((df["TOM_Marque_Citee"] == brand).sum() / total * 100, 1)


def calc_tom_all_brands(df: pd.DataFrame) -> dict:
    """TOM for all brands."""
    total = len(df)
    if total == 0:
        return {}
    result = {}
    for brand in COMPETITORS:
        result[brand] = round((df["TOM_Marque_Citee"] == brand).sum() / total * 100, 1)
    return result


def calc_notoriete_totale(df: pd.DataFrame, brand: str = "Betclic") -> float:
    """Total awareness for a brand."""
    col = f"Notoriete_Totale_{brand}"
    if col not in df.columns:
        return 0.0
    total = len(df)
    if total == 0:
        return 0.0
    return round(df[col].sum() / total * 100, 1)


def calc_notoriete_all_brands(df: pd.DataFrame) -> dict:
    """Total awareness for all brands."""
    result = {}
    for brand in COMPETITORS:
        result[brand] = calc_notoriete_totale(df, brand)
    return result


def calc_notoriete_aidee(df: pd.DataFrame) -> float:
    """Aided awareness for Betclic."""
    total = len(df)
    if total == 0:
        return 0.0
    return round(df["Notoriete_Aidee_Betclic"].sum() / total * 100, 1)


def calc_rappel_campagne(df: pd.DataFrame) -> float:
    """Campaign recall among bettors."""
    parieurs = get_parieurs(df)
    if len(parieurs) == 0:
        return 0.0
    return round(parieurs["Rappel_Campagne_Betclic"].sum() / len(parieurs) * 100, 1)


def calc_ambassadeur_distribution(df: pd.DataFrame) -> dict:
    """Distribution of ambassador recall."""
    parieurs = get_parieurs(df)
    rappel = parieurs[parieurs["Rappel_Campagne_Betclic"] == 1]
    if len(rappel) == 0:
        return {}
    return rappel["Ambassadeur_Rappele"].value_counts(normalize=True).apply(lambda x: round(x * 100, 1)).to_dict()


def calc_canal_decouverte(df: pd.DataFrame) -> dict:
    """Discovery channel distribution."""
    valid = df[df["Canal_Decouverte"].notna()]
    if len(valid) == 0:
        return {}
    return valid["Canal_Decouverte"].value_counts(normalize=True).apply(lambda x: round(x * 100, 1)).to_dict()


def calc_penetration(df: pd.DataFrame) -> float:
    """Betclic penetration rate among bettors."""
    parieurs = get_parieurs(df)
    if len(parieurs) == 0:
        return 0.0
    return round(parieurs["Utilise_Betclic"].sum() / len(parieurs) * 100, 1)


def calc_marque_principale(df: pd.DataFrame) -> float:
    """% bettors whose primary brand is Betclic."""
    parieurs = get_parieurs(df)
    if len(parieurs) == 0:
        return 0.0
    return round((parieurs["Marque_Principale_Utilisee"] == "Betclic").sum() / len(parieurs) * 100, 1)


def calc_marque_principale_all(df: pd.DataFrame) -> dict:
    """Primary brand share for all brands."""
    parieurs = get_parieurs(df)
    if len(parieurs) == 0:
        return {}
    total = len(parieurs)
    result = {}
    for brand in COMPETITORS:
        result[brand] = round((parieurs["Marque_Principale_Utilisee"] == brand).sum() / total * 100, 1)
    return result


def calc_multi_app(df: pd.DataFrame) -> float:
    """% bettors using 2+ apps."""
    parieurs = get_parieurs(df)
    if len(parieurs) == 0:
        return 0.0
    return round(parieurs["Multi_Application"].sum() / len(parieurs) * 100, 1)


def calc_consideration(df: pd.DataFrame) -> float:
    """Consideration for Betclic among bettors."""
    parieurs = get_parieurs(df)
    if len(parieurs) == 0:
        return 0.0
    return round(parieurs["Consideration_Betclic"].sum() / len(parieurs) * 100, 1)


def calc_preference(df: pd.DataFrame) -> float:
    """Preference for Betclic among bettors."""
    parieurs = get_parieurs(df)
    if len(parieurs) == 0:
        return 0.0
    return round(parieurs["Preference_Betclic"].sum() / len(parieurs) * 100, 1)


def calc_wallet_share(df: pd.DataFrame) -> float:
    """Average wallet share for Betclic among its users."""
    users = get_utilisateurs_betclic(df)
    if len(users) == 0:
        return 0.0
    return round(users["Part_Portefeuille_Betclic"].mean() * 100, 1)


def calc_sport_distribution(df: pd.DataFrame) -> dict:
    """Distribution of preferred sports."""
    parieurs = get_parieurs(df)
    if len(parieurs) == 0:
        return {}
    return parieurs["Sport_Prefere"].value_counts(normalize=True).apply(lambda x: round(x * 100, 1)).to_dict()


def calc_pari_type_distribution(df: pd.DataFrame) -> dict:
    """Distribution of bet types."""
    parieurs = get_parieurs(df)
    valid = parieurs[parieurs["Type_Pari_Prefere"].notna()]
    if len(valid) == 0:
        return {}
    return valid["Type_Pari_Prefere"].value_counts(normalize=True).apply(lambda x: round(x * 100, 1)).to_dict()


def calc_paiement_distribution(df: pd.DataFrame) -> dict:
    """Distribution of payment methods."""
    parieurs = get_parieurs(df)
    valid = parieurs[parieurs["Moyen_Paiement_Principal"].notna()]
    if len(valid) == 0:
        return {}
    return valid["Moyen_Paiement_Principal"].value_counts(normalize=True).apply(lambda x: round(x * 100, 1)).to_dict()


def calc_image_scores(df: pd.DataFrame) -> dict:
    """Average image attribute scores for Betclic (among those who know it)."""
    aware = df[df["Notoriete_Totale_Betclic"] == 1]
    result = {}
    for col, label in IMAGE_ATTRIBUTES.items():
        vals = aware[col].dropna()
        if len(vals) > 0:
            result[label] = round(vals.mean(), 2)
        else:
            result[label] = 0.0
    return result


def calc_satisfaction(df: pd.DataFrame) -> float:
    """Average satisfaction among Betclic users."""
    users = get_utilisateurs_betclic(df)
    vals = users["Satisfaction_Globale_Betclic"].dropna()
    if len(vals) == 0:
        return 0.0
    return round(vals.mean(), 2)


def calc_nps(df: pd.DataFrame) -> dict:
    """NPS calculation among Betclic users."""
    users = get_utilisateurs_betclic(df)
    nps_data = users["NPS_Categorie"].dropna()
    total = len(nps_data)
    if total == 0:
        return {"nps": 0, "promoteurs": 0, "passifs": 0, "detracteurs": 0}
    promoteurs = (nps_data == "Promoteur").sum() / total * 100
    passifs = (nps_data == "Passif").sum() / total * 100
    detracteurs = (nps_data.isin(["Détracteur", "Detracteur"])).sum() / total * 100
    nps_score = round(promoteurs - detracteurs, 1)
    return {
        "nps": nps_score,
        "promoteurs": round(promoteurs, 1),
        "passifs": round(passifs, 1),
        "detracteurs": round(detracteurs, 1),
    }


def calc_churn_risk(df: pd.DataFrame) -> dict:
    """Churn risk distribution among Betclic users."""
    users = get_utilisateurs_betclic(df)
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
    """Distribution of main irritants among Betclic users."""
    users = get_utilisateurs_betclic(df)
    valid = users["Principal_Irritant"].dropna()
    if len(valid) == 0:
        return {}
    return valid.value_counts(normalize=True).apply(lambda x: round(x * 100, 1)).to_dict()


def calc_intention(df: pd.DataFrame) -> dict:
    """Reuse intention distribution among Betclic users."""
    users = get_utilisateurs_betclic(df)
    valid = users["Intention_Reutilisation"].dropna()
    total = len(valid)
    if total == 0:
        return {}
    order = ["Certainement", "Probablement", "Incertain", "Probablement pas"]
    result = {}
    for cat in order:
        result[cat] = round((valid == cat).sum() / total * 100, 1)
    return result


def calc_intention_positive(df: pd.DataFrame) -> float:
    """% Certainement + Probablement among Betclic users."""
    intent = calc_intention(df)
    return round(intent.get("Certainement", 0) + intent.get("Probablement", 0), 1)


# ──────────────────────────────────────────────
# MULTI-VAGUE COMPARISON HELPERS
# ──────────────────────────────────────────────

def calc_kpi_by_vague(df: pd.DataFrame, calc_func, **kwargs) -> dict:
    """Calculate a KPI for each vague separately."""
    result = {}
    for vague in ["Vague 1", "Vague 2", "Vague 3"]:
        sub = df[df["Vague"] == vague]
        if len(sub) > 0:
            result[vague] = calc_func(sub, **kwargs)
        else:
            result[vague] = None
    return result


def calc_delta(current, previous) -> tuple:
    """Calculate delta and direction between two values."""
    if current is None or previous is None:
        return None, "neutral"
    delta = round(current - previous, 1)
    if delta > 0:
        return f"+{delta}", "up"
    elif delta < 0:
        return str(delta), "down"
    else:
        return "0", "neutral"


def get_latest_vague(vague_dict: dict):
    """Get the latest vague value from a dict."""
    for v in ["Vague 3", "Vague 2", "Vague 1"]:
        if v in vague_dict and vague_dict[v] is not None:
            return vague_dict[v]
    return None


def get_previous_vague(vague_dict: dict):
    """Get the previous vague value."""
    keys = [k for k in ["Vague 1", "Vague 2", "Vague 3"] if k in vague_dict and vague_dict[k] is not None]
    if len(keys) >= 2:
        return vague_dict[keys[-2]]
    return None


# ──────────────────────────────────────────────
# GEO ANALYSIS
# ──────────────────────────────────────────────

def calc_kpi_by_city(df: pd.DataFrame, calc_func, **kwargs) -> dict:
    """Calculate a KPI for each city."""
    result = {}
    for city in CITIES:
        sub = df[df["Ville"] == city]
        if len(sub) > 0:
            result[city] = calc_func(sub, **kwargs)
    return result


# ──────────────────────────────────────────────
# FUNNEL DATA
# ──────────────────────────────────────────────

def calc_funnel(df: pd.DataFrame) -> dict:
    """Calculate the brand funnel for Betclic."""
    return {
        "Notoriété Totale": calc_notoriete_totale(df),
        "Notoriété Aidée": calc_notoriete_aidee(df),
        "Considération": calc_consideration(df),
        "Pénétration": calc_penetration(df),
        "Préférence": calc_preference(df),
        "Marque Principale": calc_marque_principale(df),
    }
