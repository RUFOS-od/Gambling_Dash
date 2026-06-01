"""
Simulated data generator for the AI Market Radar module.
Generates coherent competitive intelligence data based on the real tracker data.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from data.loader import load_raw_data, calc_tom_all_brands, calc_notoriete_all_brands, COMPETITORS

np.random.seed(42)


def _base_strength():
    """Get base brand strength from real data for coherent simulation.

    Uses the latest available wave (dynamic), not a hardcoded one.
    """
    data = load_raw_data()
    if len(data) == 0 or "Vague" not in data.columns:
        # No real data yet : assume Betclic = leader, others = uniform
        return {b: 50 if b == "Betclic" else 20 for b in COMPETITORS}

    # Pick latest wave dynamically
    vagues = sorted(
        data["Vague"].dropna().unique().tolist(),
        key=lambda x: int(x.replace("Vague ", "")) if x.replace("Vague ", "").isdigit() else 999,
    )
    latest_wave = vagues[-1] if vagues else None
    latest = data[data["Vague"] == latest_wave] if latest_wave else data

    tom = calc_tom_all_brands(latest)
    notoriete = calc_notoriete_all_brands(latest)

    # Combine TOM + awareness into a strength score
    strength = {}
    for brand in COMPETITORS:
        strength[brand] = (tom.get(brand, 0) * 0.6 + notoriete.get(brand, 0) * 0.4)
    return strength


def generate_social_mentions():
    """Generate 4 weeks of simulated social media mentions per competitor."""
    strength = _base_strength()
    weeks = ["Sem 1 (3-9 Mar)", "Sem 2 (10-16 Mar)", "Sem 3 (17-23 Mar)", "Sem 4 (24-30 Mar)"]
    data = {}

    for brand in COMPETITORS:
        base = int(strength.get(brand, 10) * 15 + np.random.randint(50, 200))
        weekly = []
        for w in range(4):
            val = max(10, int(base + np.random.normal(0, base * 0.15)))
            weekly.append(val)
            base = val  # slight momentum
        data[brand] = dict(zip(weeks, weekly))

    return data


def generate_sentiment_data():
    """Generate sentiment analysis per competitor."""
    strength = _base_strength()
    data = {}

    for brand in COMPETITORS:
        s = strength.get(brand, 20)
        # Stronger brands tend to have better sentiment
        pos_base = min(65, 30 + s * 0.4)
        neg_base = max(8, 25 - s * 0.2)
        pos = round(pos_base + np.random.normal(0, 5), 1)
        neg = round(neg_base + np.random.normal(0, 3), 1)
        neu = round(100 - pos - neg, 1)
        data[brand] = {
            "Positif": max(10, pos),
            "Neutre": max(10, neu),
            "Négatif": max(5, neg),
        }

    return data


def generate_ad_intensity():
    """Generate advertising intensity scores (0-100) per competitor."""
    strength = _base_strength()
    data = {}
    for brand in COMPETITORS:
        s = strength.get(brand, 10)
        intensity = min(95, max(10, int(s * 0.8 + np.random.normal(15, 10))))
        data[brand] = intensity
    return data


def generate_risk_levels():
    """Generate competitive risk levels per competitor."""
    strength = _base_strength()
    data = {}
    for brand in COMPETITORS:
        s = strength.get(brand, 10)
        if brand == "Betclic":
            data[brand] = {"level": "—", "score": 0, "trend": "Leader"}
        elif s > 40:
            data[brand] = {"level": "Élevé", "score": round(min(95, s * 1.2 + np.random.normal(0, 5)), 0), "trend": "En hausse"}
        elif s > 20:
            data[brand] = {"level": "Modéré", "score": round(s * 1.1 + np.random.normal(0, 5), 0), "trend": "Stable"}
        else:
            data[brand] = {"level": "Faible", "score": round(max(5, s * 0.9 + np.random.normal(0, 3)), 0), "trend": "En baisse"}
    return data


def generate_share_of_voice():
    """Generate share of voice based on social mentions."""
    mentions = generate_social_mentions()
    totals = {}
    for brand in COMPETITORS:
        totals[brand] = sum(mentions[brand].values())
    grand_total = sum(totals.values())
    sov = {brand: round(v / grand_total * 100, 1) for brand, v in totals.items()}
    return sov


def generate_competitor_actions():
    """Generate recent competitor actions/events."""
    actions = {
        "1XBET": [
            {"date": "2026-03-22", "type": "Promotion", "detail": "Bonus 200% premier dépôt lancé via Facebook Ads", "impact": "Fort"},
            {"date": "2026-03-15", "type": "Partenariat", "detail": "Sponsoring compétition e-sport locale", "impact": "Moyen"},
            {"date": "2026-03-08", "type": "Produit", "detail": "Lancement paris virtuels basket", "impact": "Moyen"},
        ],
        "Sportcash": [
            {"date": "2026-03-20", "type": "Communication", "detail": "Campagne TV pendant CAN qualifiers", "impact": "Fort"},
            {"date": "2026-03-12", "type": "Promotion", "detail": "Cashback 50% sur paris perdants", "impact": "Fort"},
        ],
        "PremierBet": [
            {"date": "2026-03-18", "type": "Paiement", "detail": "Intégration Moov Money finalisée", "impact": "Moyen"},
            {"date": "2026-03-05", "type": "Ambassadeur", "detail": "Nouveau contrat influenceur TikTok (500K followers)", "impact": "Moyen"},
        ],
        "Chopbet": [
            {"date": "2026-03-21", "type": "Promotion", "detail": "Paris gratuits weekend · campagne agressive SMS", "impact": "Moyen"},
        ],
        "Melbet": [
            {"date": "2026-03-19", "type": "Produit", "detail": "Refonte UX application mobile", "impact": "Faible"},
        ],
        "Betmomo": [
            {"date": "2026-03-17", "type": "Communication", "detail": "Activation terrain Abidjan · stands mobile money", "impact": "Moyen"},
        ],
        "AkwaBet": [
            {"date": "2026-03-10", "type": "Promotion", "detail": "Bonus inscription 5 000 FCFA", "impact": "Faible"},
        ],
        "Paripesa": [
            {"date": "2026-03-14", "type": "Produit", "detail": "Ajout cotes boostées football européen", "impact": "Faible"},
        ],
        "Betclic": [
            {"date": "2026-03-23", "type": "Communication", "detail": "Campagne Willy Dumbo · TV + digital", "impact": "Fort"},
            {"date": "2026-03-16", "type": "Produit", "detail": "Lancement section jeu responsable in-app", "impact": "Moyen"},
            {"date": "2026-03-09", "type": "Promotion", "detail": "Offre VIP parieurs intensifs", "impact": "Fort"},
        ],
    }
    return actions


def generate_alerts():
    """Generate strategic alerts and weak signals."""
    return [
        {
            "date": "2026-03-22",
            "severity": "high",
            "title": "1XBET : Surenchère promotionnelle massive",
            "detail": "Bonus 200% détecté · risque de captation parieurs occasionnels. Recommandation : activation défensive CRM sur segment Occasionnel.",
            "category": "Concurrence",
        },
        {
            "date": "2026-03-20",
            "severity": "high",
            "title": "Sportcash : Campagne TV nationale",
            "detail": "Spot TV 30s diffusé en prime time pendant qualifications CAN. Budget estimé significatif. Risque de gain TOM sur 18-24 ans.",
            "category": "Concurrence",
        },
        {
            "date": "2026-03-18",
            "severity": "medium",
            "title": "PremierBet : Expansion paiement mobile",
            "detail": "Intégration Moov Money complétée · PremierBet couvre désormais 4 opérateurs. Aligne son offre paiement sur Betclic.",
            "category": "Produit",
        },
        {
            "date": "2026-03-15",
            "severity": "low",
            "title": "Signal faible : Croissance e-sport en CI",
            "detail": "Mentions e-sport +180% sur TikTok ivoirien. 1XBET premier entrant. Opportunité de positionnement pour Betclic.",
            "category": "Tendance",
        },
        {
            "date": "2026-03-12",
            "severity": "medium",
            "title": "Sentiment négatif : Délais de retrait",
            "detail": "Hausse +15% des mentions négatives 'retrait lent' pour l'ensemble du marché. Betclic moins touché que la moyenne.",
            "category": "Réputation",
        },
        {
            "date": "2026-03-10",
            "severity": "low",
            "title": "Nouveaux entrants potentiels",
            "detail": "Rumeurs de demande de licence LONACI par 2 opérateurs internationaux. Surveillance recommandée.",
            "category": "Marché",
        },
    ]


def generate_positioning_data():
    """Generate data for competitive positioning bubble chart."""
    strength = _base_strength()
    sentiment = generate_sentiment_data()
    sov = generate_share_of_voice()

    data = []
    for brand in COMPETITORS:
        s = strength.get(brand, 10)
        sent = sentiment.get(brand, {})
        data.append({
            "name": brand,
            "x": sov.get(brand, 5),  # Share of Voice
            "y": sent.get("Positif", 30),  # Sentiment positif
            "size": max(15, s * 0.8),  # Taille = notoriété
            "color": "#C0392B" if brand == "Betclic" else "#6C3483" if brand == "1XBET" else "#4A5568",
        })
    return data
