"""
Orchestrateur : execute tous les collecteurs dans l'ordre, collecte les rapports,
retourne un resume.
"""

from typing import List, Optional
from .base import Collector, CollectorResult
from .storage import Storage
from .meta_ads import MetaAdsCollector
from .google_trends import GoogleTrendsCollector
from .google_news import GoogleNewsCollector
from .youtube import YouTubeCollector


DEFAULT_COLLECTORS: List[Collector] = [
    GoogleTrendsCollector(),
    GoogleNewsCollector(),
    MetaAdsCollector(),
    YouTubeCollector(),
]


def run_all(collectors: Optional[List[Collector]] = None,
            storage: Optional[Storage] = None) -> List[CollectorResult]:
    """Execute chaque collecteur sequentiellement et retourne un rapport par collecteur."""
    collectors = collectors or DEFAULT_COLLECTORS
    storage = storage or Storage()
    results = []
    for c in collectors:
        results.append(c.run(storage))
    return results


def get_status(storage: Optional[Storage] = None) -> dict:
    """Retourne l'etat de chaque collecteur (dernier run, age, ok/ko)."""
    storage = storage or Storage()
    status = {}
    for c in DEFAULT_COLLECTORS:
        info = storage.last_run_info(c.name)
        age_min = storage.age_minutes(c.name)
        status[c.name] = {
            "last_run_info": info,
            "age_minutes": age_min,
            "available": c.is_available(),
            "required_env": c.required_env,
        }
    return status
