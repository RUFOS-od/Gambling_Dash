"""
Collecteur Google News via flux RSS (pas de cle API). Une requete par marque.
Retourne les 30 dernieres actualites francophones geolocalisees Cote d'Ivoire.
"""

from datetime import datetime
from urllib.parse import quote_plus
import pandas as pd

from .base import Collector, COMPETITORS


def _brand_query(brand: str) -> str:
    """Construit une requete ciblee pour chaque marque (context paris sportifs CI)."""
    # On elargit Sportcash pour eviter le bruit financier
    extras = {
        "Sportcash": "Sportcash paris sportifs",
        "Chopbet": "Chopbet paris",
        "Melbet": "Melbet paris",
        "1XBET": "1xBet paris",
    }
    base = extras.get(brand, brand)
    return f'{base} ("Cote d\'Ivoire" OR Abidjan)'


class GoogleNewsCollector(Collector):
    name = "google_news"
    table = "news"
    required_env: list = []

    HL = "fr"         # langue
    GL = "CI"         # pays de l'utilisateur
    CEID = "CI:fr"    # edition / langue

    def _feed_url(self, query: str) -> str:
        q = quote_plus(query)
        return (
            f"https://news.google.com/rss/search?q={q}"
            f"&hl={self.HL}&gl={self.GL}&ceid={self.CEID}"
        )

    def fetch(self) -> pd.DataFrame:
        try:
            import feedparser
        except ImportError:
            raise RuntimeError(
                "Module feedparser absent. Installer avec : pip install feedparser"
            )

        rows = []
        for brand in COMPETITORS:
            query = _brand_query(brand)
            url = self._feed_url(query)
            try:
                feed = feedparser.parse(url)
            except Exception as e:
                print(f"[google_news] {brand} : {e}")
                continue

            for entry in feed.entries[:30]:
                pub = entry.get("published", "") or entry.get("updated", "")
                # normaliser la date
                try:
                    pub_iso = datetime(*entry.published_parsed[:6]).isoformat()
                except Exception:
                    pub_iso = pub

                source = ""
                if getattr(entry, "source", None):
                    source = entry.source.get("title", "") if isinstance(entry.source, dict) else str(entry.source)

                rows.append({
                    "published": pub_iso,
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "source": source,
                    "summary": (entry.get("summary", "") or "")[:500],
                    "brand": brand,
                })

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df = df.drop_duplicates(subset=["link"], keep="first")
        return df
