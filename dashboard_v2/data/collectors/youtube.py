"""
Collecteur YouTube Data API v3.
Variable d'environnement requise : YOUTUBE_API_KEY (cle gratuite, 10 000 unites de quota/jour).
Sans cle, retour vide sans erreur.

Scope : videos des 12 derniers mois qui citent la marque dans leur titre et concernent
la Cote d'Ivoire (titre, description ou chaine). Exclus : videos en alphabets non latins,
contenus en euros (Betclic France), pronostics et codes promo (affiliation).
"""

import os
from datetime import datetime, timedelta, timezone
import html
import pandas as pd

from .base import (Collector, CollectorError, COMPETITORS, BRAND_ALIASES, mentions_brand,
                   is_ci_context, is_affiliate, is_non_ci, has_non_latin, other_country_only,
                   MAX_AGE_DAYS)


class YouTubeCollector(Collector):
    name = "youtube"
    table = "youtube_videos"
    required_env = ["YOUTUBE_API_KEY"]

    SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
    VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
    REGION = "CI"
    LANG = "fr"
    MAX_PER_BRAND = 50

    def fetch(self) -> pd.DataFrame:
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if not api_key:
            return pd.DataFrame()

        try:
            import requests
        except ImportError:
            raise RuntimeError("Module requests absent. pip install requests")

        after = (datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows, n_ok, last_err = [], 0, ""
        for brand in COMPETITORS:
            alias = BRAND_ALIASES.get(brand, [brand])[0]
            try:
                params = {
                    "part": "snippet",
                    "q": f"{alias} Côte d'Ivoire",
                    "type": "video",
                    "regionCode": self.REGION,
                    "relevanceLanguage": self.LANG,
                    "publishedAfter": after,
                    "order": "relevance",
                    "maxResults": self.MAX_PER_BRAND,
                    "key": api_key,
                }
                r = requests.get(self.SEARCH_URL, params=params, timeout=20)
                if r.status_code != 200:
                    last_err = f"HTTP {r.status_code}"
                    print(f"[youtube] search {brand} HTTP {r.status_code}: {r.text[:200]}")
                    continue
                n_ok += 1
                items = r.json().get("items", [])
            except Exception as e:
                last_err = type(e).__name__
                print(f"[youtube] search {brand} : {e}")
                continue

            keep = []
            for it in items:
                sn = it.get("snippet", {})
                title = html.unescape(sn.get("title", ""))
                desc = html.unescape(sn.get("description", ""))
                channel = sn.get("channelTitle", "")
                if not it.get("id", {}).get("videoId"):
                    continue
                if not mentions_brand(title, brand) or has_non_latin(title):
                    continue
                if is_non_ci(title + " " + desc) or is_affiliate(title) or other_country_only(title):
                    continue
                if not is_ci_context(f"{title} {desc} {channel}"):
                    continue
                keep.append((it["id"]["videoId"], title, channel, sn.get("publishedAt", "")))
            if not keep:
                continue

            # Statistiques (vues / likes / commentaires)
            stats = {}
            try:
                r2 = requests.get(
                    self.VIDEOS_URL,
                    params={"part": "statistics", "id": ",".join(k[0] for k in keep), "key": api_key},
                    timeout=20,
                )
                if r2.status_code == 200:
                    for v in r2.json().get("items", []):
                        s = v.get("statistics", {}) or {}
                        stats[v["id"]] = {
                            "views": int(s.get("viewCount", 0) or 0),
                            "likes": int(s.get("likeCount", 0) or 0),
                            "comments": int(s.get("commentCount", 0) or 0),
                        }
            except Exception as e:
                print(f"[youtube] stats {brand} : {e}")

            for vid, title, channel, published in keep:
                st = stats.get(vid, {})
                rows.append({
                    "video_id": vid, "title": title, "channel": channel, "published": published,
                    "views": st.get("views", 0), "likes": st.get("likes", 0),
                    "comments": st.get("comments", 0), "brand": brand,
                })

        if n_ok == 0:
            raise CollectorError(f"API YouTube indisponible ({last_err or 'aucune réponse'}).")
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows).drop_duplicates(subset=["video_id", "brand"])
