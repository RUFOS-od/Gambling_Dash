# Betclic Brand Pulse — Business Intelligence Dashboard 2026

**OpinionWay Africa x Betclic Cote d'Ivoire**

Dashboard Streamlit multi-modules pour le pilotage de la marque Betclic sur le marche ivoirien des paris sportifs.

## Modules

### Module A — Brand Health Tracker (Betclic Brand Pulse)
- Vue d'ensemble / Scorecard executif
- Notoriete & Visibilite (TOM, notoriete totale, rappel campagne, ambassadeurs)
- Usage & Penetration (funnel, wallet share, multi-app, paiements, sports)
- Image de Marque (12 attributs, radar chart comparatif 3 vagues)
- Satisfaction & Fidelite (NPS, satisfaction, churn, irritants, intention)
- Analyse Geographique (7 villes)

### Module B — AI Market Radar (Veille Concurrentielle)
- Vue d'ensemble (positionnement, SOV, sentiment, risques)
- Fiches Concurrents (9 acteurs)
- Social & Sentiment Analysis
- Alertes & Signaux Faibles

## Lancement

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

Ou simplement :
```bash
bash run.sh
```

## Structure

```
dashboard/
  app.py                  # Point d'entree
  .streamlit/config.toml  # Theme et config
  data/
    loader.py             # Chargement donnees et calcul KPIs
    simulator.py          # Donnees simulees AI Market Radar
  components/
    styles.py             # CSS custom et composants UI
    charts.py             # Builders Plotly reutilisables
  pages/
    tracker_overview.py   # Scorecard executif
    tracker_notoriete.py  # Notoriete & Visibilite
    tracker_usage.py      # Usage & Penetration
    tracker_image.py      # Image de Marque
    tracker_satisfaction.py # Satisfaction & Fidelite
    tracker_geo.py        # Analyse Geographique
    radar_overview.py     # AI Market Radar overview
    radar_competitors.py  # Fiches concurrents
    radar_social.py       # Social & Sentiment
    radar_alerts.py       # Alertes & Signaux
```

## Donnees

- **Bases brutes** : 3 fichiers Excel (V1, V2, V3), 1000 interviews CAPI chacun
- **KPIs de reference** : Fichier de synthese comparatif 3 vagues
- Tous les KPIs du Brand Tracker sont calcules dynamiquement depuis les bases brutes
- Les donnees AI Market Radar sont simulees de maniere coherente avec les donnees reelles

## Stack

- Python 3.10+
- Streamlit
- Plotly
- Pandas / NumPy
