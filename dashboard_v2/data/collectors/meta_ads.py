"""
Collecteur Meta Ad Library.

L'API Ad Library de Meta requiert un token Graph API (variable META_ACCESS_TOKEN).
Sans token, le collecteur retourne un DataFrame vide sans erreur.
Scope : publicites actives en Cote d'Ivoire pour les 9 marques.
"""

import os
from datetime import datetime
import pandas as pd

from .base import Collector, COMPETITORS, GEO_CODE


class MetaAdsCollector(Collector):
    name = "meta_ads"
    table = "ads"
    required_env = ["META_ACCESS_TOKEN"]

    ENDPOINT = "https://graph.facebook.com/v19.0/ads_archive"
    COUNTRY = GEO_CODE
    FIELDS = (
        "id,page_name,ad_snapshot_url,ad_creative_bodies,"
        "ad_delivery_start_time,impressions,ad_creative_link_captions"
    )

    def fetch(self) -> pd.DataFrame:
        token = os.environ.get("META_ACCESS_TOKEN")
        if not token:
            # Mode degrade : pas de token, retour vide, pas d'erreur
            return pd.DataFrame()

        try:
            import requests
        except ImportError:
            raise RuntimeError("Module requests absent. pip install requests")

        rows = []
        for brand in COMPETITORS:
            params = {
                "search_terms": brand,
                "ad_reached_countries": f'["{self.COUNTRY}"]',
                "ad_active_status": "ALL",
                "fields": self.FIELDS,
                "limit": 50,
                "access_token": token,
            }
            try:
                r = requests.get(self.ENDPOINT, params=params, timeout=20)
                if r.status_code != 200:
                    print(f"[meta_ads] {brand} HTTP {r.status_code}: {r.text[:200]}")
                    continue
                data = r.json().get("data", [])
            except Exception as e:
                print(f"[meta_ads] {brand} : {e}")
                continue

            for ad in data:
                creative_bodies = ad.get("ad_creative_bodies") or []
                body = creative_bodies[0] if creative_bodies else ""
                impressions = ad.get("impressions") or {}
                if isinstance(impressions, dict):
                    imp_range = f"{impressions.get('lower_bound','')}-{impressions.get('upper_bound','')}"
                else:
                    imp_range = str(impressions)

                rows.append({
                    "page_name": ad.get("page_name", ""),
                    "brand": brand,
                    "ad_snapshot_url": ad.get("ad_snapshot_url", ""),
                    "start_date": ad.get("ad_delivery_start_time", ""),
                    "impressions_range": imp_range,
                    "country": self.COUNTRY,
                    "ad_creative_body": (body or "")[:1000],
                })

        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows)
