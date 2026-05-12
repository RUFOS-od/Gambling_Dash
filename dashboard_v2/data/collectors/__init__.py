"""
Collecteurs de veille concurrentielle pour le module AI Market Radar.

Chaque collecteur herite de la classe `Collector` (base.py), implemente
`fetch()` et stocke ses resultats via `Storage` (storage.py). Une execution
orchestree est offerte par `run_all()`.
"""

from .base import Collector, CollectorResult
from .storage import Storage
from .meta_ads import MetaAdsCollector
from .google_trends import GoogleTrendsCollector
from .google_news import GoogleNewsCollector
from .youtube import YouTubeCollector
from .orchestrator import run_all, get_status

__all__ = [
    "Collector",
    "CollectorResult",
    "Storage",
    "MetaAdsCollector",
    "GoogleTrendsCollector",
    "GoogleNewsCollector",
    "YouTubeCollector",
    "run_all",
    "get_status",
]
