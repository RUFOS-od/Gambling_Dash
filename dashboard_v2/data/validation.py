"""
Module de validation qualite pour les bases de donnees des vagues Brand Pulse.
Verifie integrite, coherence et completude des fichiers Excel recus.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Structure attendue des fichiers
EXPECTED_COLUMNS = [
    "ID_Repondant", "Vague", "Mois_Collecte", "Ville", "Tranche_Age", "Genre",
    "Type_Repondant", "Segment_Parieur", "Frequence_Paris_Mois", "TOM_Marque_Citee",
    "Notoriete_Totale_Betclic", "Notoriete_Aidee_Betclic",
    "Notoriete_Totale_1XBET", "Notoriete_Totale_Sportcash", "Notoriete_Totale_PremierBet",
    "Notoriete_Totale_Chopbet", "Notoriete_Totale_Melbet", "Notoriete_Totale_Betmomo",
    "Notoriete_Totale_AkwaBet", "Notoriete_Totale_Paripesa",
    "Rappel_Campagne_Betclic", "Ambassadeur_Rappele", "Canal_Decouverte",
    "Utilise_Betclic", "Marque_Principale_Utilisee", "Multi_Application",
    "Nb_Apps_Utilisees", "Sport_Prefere", "Type_Pari_Prefere",
    "Moyen_Paiement_Principal", "Part_Portefeuille_Betclic",
    "Consideration_Betclic", "Preference_Betclic",
    "Image_Modernite", "Image_Fiabilite", "Image_Securite",
    "Image_Rapidite_Paiements", "Image_Proximite", "Image_Innovation",
    "Image_Qualite_App", "Image_Simplicite", "Image_Variete_Paris",
    "Image_Jeu_Responsable", "Image_Rapport_Qualite_Bonus", "Image_Transparence",
    "Satisfaction_Globale_Betclic", "NPS_Score", "NPS_Categorie",
    "Risque_Churn", "Principal_Irritant", "Intention_Reutilisation",
]

EXPECTED_VILLES = ["Abidjan", "Bouake", "Bouaké", "Yamoussoukro", "San Pedro", "Daloa", "Korhogo", "Abengourou"]
EXPECTED_GENRES = ["Homme", "Femme"]
EXPECTED_TYPES = ["Parieur", "Non-parieur"]

BINARY_COLS = [
    "Notoriete_Totale_Betclic", "Notoriete_Aidee_Betclic",
    "Notoriete_Totale_1XBET", "Notoriete_Totale_Sportcash", "Notoriete_Totale_PremierBet",
    "Notoriete_Totale_Chopbet", "Notoriete_Totale_Melbet", "Notoriete_Totale_Betmomo",
    "Notoriete_Totale_AkwaBet", "Notoriete_Totale_Paripesa",
    "Rappel_Campagne_Betclic", "Utilise_Betclic", "Multi_Application",
    "Consideration_Betclic", "Preference_Betclic",
]

IMAGE_COLS = [
    "Image_Modernite", "Image_Fiabilite", "Image_Securite",
    "Image_Rapidite_Paiements", "Image_Proximite", "Image_Innovation",
    "Image_Qualite_App", "Image_Simplicite", "Image_Variete_Paris",
    "Image_Jeu_Responsable", "Image_Rapport_Qualite_Bonus", "Image_Transparence",
]


def validate_wave(df: pd.DataFrame, wave_name: str) -> dict:
    """
    Valide une base de donnees d'une vague et retourne un rapport complet.
    Retour: dict avec 'ok' (bool), 'errors', 'warnings', 'stats'.
    """
    errors = []
    warnings = []
    stats = {}

    stats["wave"] = wave_name
    stats["n_rows"] = len(df)
    stats["n_cols"] = len(df.columns)

    # 1. Colonnes manquantes
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        errors.append(f"{len(missing)} colonnes manquantes : {', '.join(missing[:5])}...")
    stats["missing_cols"] = missing

    # 2. Colonnes inattendues (nouvelles modalites potentielles)
    extra = [c for c in df.columns if c not in EXPECTED_COLUMNS]
    if extra:
        warnings.append(f"{len(extra)} colonnes inattendues : {', '.join(extra[:5])}")
    stats["extra_cols"] = extra

    # 3. Doublons d'ID
    if "ID_Repondant" in df.columns:
        n_duplicates = df["ID_Repondant"].duplicated().sum()
        stats["duplicates"] = int(n_duplicates)
        if n_duplicates > 0:
            errors.append(f"{n_duplicates} ID_Repondant en doublon")

    # 4. Taux de non-reponse global
    fill_rate = (1 - df.isna().sum().sum() / (df.shape[0] * df.shape[1])) * 100
    stats["fill_rate"] = round(fill_rate, 1)
    if fill_rate < 60:
        warnings.append(f"Taux de remplissage tres bas : {fill_rate:.1f}%")

    # 5. Villes inattendues
    if "Ville" in df.columns:
        unknown_cities = set(df["Ville"].dropna().unique()) - set(EXPECTED_VILLES)
        stats["unknown_cities"] = sorted(unknown_cities)
        if unknown_cities:
            warnings.append(f"Villes inconnues : {', '.join(sorted(unknown_cities))}")

    # 6. Genres inattendus
    if "Genre" in df.columns:
        unknown_genres = set(df["Genre"].dropna().unique()) - set(EXPECTED_GENRES)
        if unknown_genres:
            warnings.append(f"Genres inconnus : {', '.join(unknown_genres)}")

    # 7. Valeurs binaires hors (0,1)
    out_of_bounds_bin = {}
    for col in BINARY_COLS:
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce").dropna()
            bad = ((vals != 0) & (vals != 1)).sum()
            if bad > 0:
                out_of_bounds_bin[col] = int(bad)
    if out_of_bounds_bin:
        warnings.append(f"Valeurs non binaires dans : {', '.join(list(out_of_bounds_bin.keys())[:3])}...")
    stats["binary_out_of_bounds"] = out_of_bounds_bin

    # 8. Scores image hors [1,5]
    out_of_bounds_img = {}
    for col in IMAGE_COLS:
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce").dropna()
            bad = ((vals < 1) | (vals > 5)).sum()
            if bad > 0:
                out_of_bounds_img[col] = int(bad)
    if out_of_bounds_img:
        warnings.append(f"Scores image hors [1,5] : {len(out_of_bounds_img)} colonnes concernees")
    stats["image_out_of_bounds"] = out_of_bounds_img

    # 9. Coherence parieurs / non-parieurs
    if "Type_Repondant" in df.columns and "Utilise_Betclic" in df.columns:
        non_parieurs_using = df[
            (df["Type_Repondant"] == "Non-parieur") & (df["Utilise_Betclic"] == 1)
        ]
        if len(non_parieurs_using) > 0:
            errors.append(f"{len(non_parieurs_using)} non-parieurs declares comme utilisateurs Betclic")
        stats["non_parieurs_using"] = len(non_parieurs_using)

    # 10. Distribution par ville
    if "Ville" in df.columns:
        city_dist = df["Ville"].value_counts().to_dict()
        stats["city_distribution"] = city_dist
        # Alerte si une ville a moins de 50 reponses (base trop faible)
        small_cities = [c for c, n in city_dist.items() if n < 50]
        if small_cities:
            warnings.append(f"Bases faibles (<50) : {', '.join(small_cities)}")

    # 11. Genre / age / segment distributions
    if "Genre" in df.columns:
        stats["genre_distribution"] = df["Genre"].value_counts().to_dict()
    if "Tranche_Age" in df.columns:
        stats["age_distribution"] = df["Tranche_Age"].value_counts().to_dict()
    if "Segment_Parieur" in df.columns:
        stats["segment_distribution"] = df["Segment_Parieur"].value_counts().to_dict()

    # 12. Taux de non-reponse par colonne cle
    key_cols = ["TOM_Marque_Citee", "NPS_Categorie", "Satisfaction_Globale_Betclic",
                "Principal_Irritant", "Intention_Reutilisation"]
    missing_rates = {}
    for col in key_cols:
        if col in df.columns:
            rate = df[col].isna().sum() / len(df) * 100
            missing_rates[col] = round(rate, 1)
    stats["key_missing_rates"] = missing_rates

    # Verdict final
    ok = len(errors) == 0

    return {
        "ok": ok,
        "errors": errors,
        "warnings": warnings,
        "stats": stats,
    }


def validate_all_waves(waves_data: dict) -> list:
    """
    Valide toutes les vagues disponibles.
    waves_data : dict {wave_name: dataframe}
    """
    reports = []
    for wave_name, df in waves_data.items():
        report = validate_wave(df, wave_name)
        reports.append(report)
    return reports


def detect_wave_files(data_dir: Path) -> list:
    """
    Auto-detecte tous les fichiers de vague dans le dossier donne.
    Pattern : Bases_Betclic_BrandPulse_Tracker_V*.xlsx
    Retourne une liste triee de dicts : [{'num': 1, 'path': Path, 'name': 'Vague 1'}, ...]
    """
    files = []
    for f in data_dir.glob("Bases_Betclic_BrandPulse_Tracker_V*.xlsx"):
        # Extraire le numero de vague
        stem = f.stem
        # Ex : "Bases_Betclic_BrandPulse_Tracker_V12" -> 12
        try:
            num_str = stem.split("_V")[-1]
            num = int(num_str)
            files.append({
                "num": num,
                "path": f,
                "name": f"Vague {num}",
                "filename": f.name,
                "size_kb": round(f.stat().st_size / 1024, 1),
            })
        except (ValueError, IndexError):
            continue

    files.sort(key=lambda x: x["num"])
    return files


def compare_waves_consistency(waves_data: dict) -> dict:
    """
    Compare les vagues entre elles pour detecter des ruptures de protocole.
    (Ex : nouvelle modalite ajoutee, changement de formulation, etc.)
    """
    issues = []

    if len(waves_data) < 2:
        return {"issues": [], "n_waves": len(waves_data)}

    # Comparer les modalites des variables categorielles
    cat_cols = ["Ville", "Tranche_Age", "Genre", "Segment_Parieur",
                "Sport_Prefere", "Moyen_Paiement_Principal", "Canal_Decouverte",
                "TOM_Marque_Citee", "Marque_Principale_Utilisee",
                "Ambassadeur_Rappele", "NPS_Categorie", "Risque_Churn",
                "Principal_Irritant", "Intention_Reutilisation", "Type_Pari_Prefere"]

    reference_wave = list(waves_data.keys())[0]
    ref_df = waves_data[reference_wave]

    for col in cat_cols:
        if col not in ref_df.columns:
            continue
        ref_mods = set(ref_df[col].dropna().unique())
        for wave_name, df in waves_data.items():
            if wave_name == reference_wave or col not in df.columns:
                continue
            wave_mods = set(df[col].dropna().unique())
            new_mods = wave_mods - ref_mods
            removed_mods = ref_mods - wave_mods
            if new_mods:
                issues.append({
                    "type": "new_modality",
                    "wave": wave_name,
                    "column": col,
                    "values": sorted(new_mods),
                })
            if removed_mods:
                issues.append({
                    "type": "removed_modality",
                    "wave": wave_name,
                    "column": col,
                    "values": sorted(removed_mods),
                })

    # Comparer la taille des echantillons
    sizes = {w: len(df) for w, df in waves_data.items()}
    ref_size = list(sizes.values())[0]
    for w, size in sizes.items():
        deviation = abs(size - ref_size) / ref_size * 100
        if deviation > 15:
            issues.append({
                "type": "size_deviation",
                "wave": w,
                "size": size,
                "reference_size": ref_size,
                "deviation_pct": round(deviation, 1),
            })

    return {
        "issues": issues,
        "n_waves": len(waves_data),
        "sample_sizes": sizes,
    }
