"""
Collecteur Google Actualites via flux RSS (pas de cle API). Une requete par marque.

Filtres appliques (marche ivoirien) :
  - la marque est citee dans le titre (evite les articles ou elle n'apparait qu'en marge) ;
  - le contenu concerne la Cote d'Ivoire (mot-cle ivoirien ou media ivoirien) ;
  - publication dans les 12 derniers mois ;
  - hors contenus d'affiliation (codes promo, avis, APK, classements) et hors France
    (montants en euros, "Betclic Elite" = championnat de basket francais) ;
  - doublons de titres supprimes (publireportages repris plusieurs fois).
"""

from datetime import datetime
from urllib.parse import quote_plus
import pandas as pd

from .base import (Collector, CollectorError, COMPETITORS, BRAND_ALIASES, mentions_brand,
                   is_ci_context, is_affiliate, is_non_ci, other_country_only, within_window, norm,
                   clean_title)


def _brand_query(brand: str) -> str:
    """Requete ciblee paris sportifs / Cote d'Ivoire pour chaque marque."""
    names = " OR ".join(f'"{a}"' for a in BRAND_ALIASES.get(brand, [brand])[:2])
    return f'({names}) ("Côte d\'Ivoire" OR Abidjan OR ivoirien OR LONACI)'


class GoogleNewsCollector(Collector):
    name = "google_news"
    table = "news"
    required_env: list = []

    HL = "fr"         # langue
    GL = "CI"         # pays de l'utilisateur
    CEID = "CI:fr"    # edition / langue

    def _feed_url(self, query: str) -> str:
        q = quote_plus(query + " when:1y")
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

        rows, n_ok = [], 0
        for brand in COMPETITORS:
            try:
                feed = feedparser.parse(self._feed_url(_brand_query(brand)))
                if getattr(feed, "bozo", 0) and not feed.entries:
                    continue
                n_ok += 1
            except Exception as e:
                print(f"[google_news] {brand} : {e}")
                continue

            for entry in feed.entries[:40]:
                try:
                    pub_iso = datetime(*entry.published_parsed[:6]).isoformat()
                except Exception:
                    pub_iso = entry.get("published", "") or entry.get("updated", "")

                source = ""
                if getattr(entry, "source", None):
                    source = entry.source.get("title", "") if isinstance(entry.source, dict) else str(entry.source)
                # Google suffixe le titre par " - Nom du media" (parfois deux fois)
                title = clean_title(clean_title(entry.get("title", "") or "", source), source)

                if not (mentions_brand(title, brand) and within_window(pub_iso)
                        and is_ci_context(title, source) and not is_affiliate(title)
                        and not is_non_ci(title) and not (other_country_only(title)
                                                          and not is_ci_context("", source))):
                    continue
                rows.append({
                    "published": pub_iso,
                    "title": title,
                    "link": entry.get("link", ""),
                    "source": source,
                    "summary": "",
                    "brand": brand,
                })

        if n_ok == 0:
            raise CollectorError("Aucun flux Google Actualités n'a répondu.")
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df["_t"] = df["title"].map(norm)
        df = df.drop_duplicates(subset=["link"]).drop_duplicates(subset=["brand", "_t"]).drop(columns="_t")
        return df.sort_values("published", ascending=False).reset_index(drop=True)
