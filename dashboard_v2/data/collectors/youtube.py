"""
Collecteur YouTube Data API v3.
Variable d'environnement requise : YOUTUBE_API_KEY (cle gratuite, 10 000 quota/j).
Sans cle, retour vide sans erreur.

Scope : videos recentes mentionnant chaque marque, region CI/FR, 30 videos max par marque.
"""

import os
import pandas as pd

from .base import Collector, COMPETITORS


class YouTubeCollector(Collector):
    name = "youtube"
    table = "youtube_videos"
    required_env = ["YOUTUBE_API_KEY"]

    SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
    VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
    REGION = "CI"
    LANG = "fr"
    MAX_PER_BRAND = 25

    def fetch(self) -> pd.DataFrame:
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if not api_key:
            return pd.DataFrame()

        try:
            import requests
        except ImportError:
            raise RuntimeError("Module requests absent. pip install requests")

        rows = []
        for brand in COMPETITORS:
            # 1. Recherche
            try:
                params = {
                    "part": "snippet",
                    "q": f"{brand} paris sportifs",
                    "type": "video",
                    "regionCode": self.REGION,
                    "relevanceLanguage": self.LANG,
                    "order": "date",
                    "maxResults": self.MAX_PER_BRAND,
                    "key": api_key,
                }
                r = requests.get(self.SEARCH_URL, params=params, timeout=20)
                if r.status_code != 200:
                    print(f"[youtube] search {brand} HTTP {r.status_code}: {r.text[:200]}")
                    continue
                items = r.json().get("items", [])
            except Exception as e:
                print(f"[youtube] search {brand} : {e}")
                continue

            if not items:
                continue

            video_ids = [it["id"]["videoId"] for it in items if it.get("id", {}).get("videoId")]

            # 2. Statistiques (views / likes / comments)
            stats = {}
            try:
                r2 = requests.get(
                    self.VIDEOS_URL,
                    params={
                        "part": "statistics",
                        "id": ",".join(video_ids),
                        "key": api_key,
                    },
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

            for it in items:
                vid = it.get("id", {}).get("videoId")
                if not vid:
                    continue
                sn = it.get("snippet", {})
                st = stats.get(vid, {})
                rows.append({
                    "video_id": vid,
                    "title": sn.get("title", ""),
                    "channel": sn.get("channelTitle", ""),
                    "published": sn.get("publishedAt", ""),
                    "views": st.get("views", 0),
                    "likes": st.get("likes", 0),
                    "comments": st.get("comments", 0),
                    "brand": brand,
                })

        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows)
