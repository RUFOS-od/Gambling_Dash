"""
Collecteur Google Trends via pytrends (pas de cle API necessaire).
Scope : interet de recherche des marques suivies en Cote d'Ivoire, 12 derniers mois,
par semaine. Betclic sert d'ancre dans chaque requete pour garder une echelle commune.
"""

import time
import pandas as pd

from .base import Collector, CollectorError, COMPETITORS, GEO_CODE

# Termes de recherche (Google Trends compare des requetes, pas des marques)
SEARCH_TERMS = {"Bet 360": "Bet360", "Premier Bet": "Premierbet"}


class GoogleTrendsCollector(Collector):
    name = "google_trends"
    table = "trends"
    required_env: list = []      # pytrends fonctionne sans cle, mais peut etre limite par Google

    CHUNK_SIZE = 5                # pytrends limite a 5 termes par requete
    TIMEFRAME = "today 12-m"
    GEO = GEO_CODE                # "CI"

    def fetch(self) -> pd.DataFrame:
        try:
            from pytrends.request import TrendReq
        except ImportError:
            raise RuntimeError(
                "Module pytrends absent. Installer avec : pip install pytrends"
            )

        # Pas de parametres retries/backoff : pytrends les transmet a urllib3 sous un nom
        # supprime en urllib3 2.x (method_whitelist), ce qui faisait echouer chaque requete.
        pytrends = TrendReq(hl="fr-FR", tz=0)
        all_frames, errors = [], []
        anchor = "Betclic"
        others = [k for k in COMPETITORS if k != anchor]
        chunks = [
            [anchor] + others[i:i + self.CHUNK_SIZE - 1]
            for i in range(0, len(others), self.CHUNK_SIZE - 1)
        ]

        for brands in chunks:
            terms = [SEARCH_TERMS.get(b, b) for b in brands]
            back = dict(zip(terms, brands))
            try:
                pytrends.build_payload(terms, timeframe=self.TIMEFRAME, geo=self.GEO)
                df = pytrends.interest_over_time()
                if df is None or df.empty:
                    continue
                if "isPartial" in df.columns:
                    df = df.drop(columns=["isPartial"])
                long = df.reset_index().melt(id_vars="date", var_name="keyword", value_name="interest")
                long["keyword"] = long["keyword"].map(lambda k: back.get(k, k))
                all_frames.append(long)
            except Exception as e:
                errors.append(str(e)[:120])
                print(f"[google_trends] chunk {brands} : {e}")
            time.sleep(1.5)      # limite le risque de blocage (HTTP 429)

        if not all_frames:
            if errors:
                raise CollectorError(f"Google Trends indisponible : {errors[0]}")
            return pd.DataFrame()

        out = pd.concat(all_frames, ignore_index=True)
        out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
        out["geo"] = self.GEO
        out = out.drop_duplicates(subset=["date", "keyword"], keep="first")
        return out
