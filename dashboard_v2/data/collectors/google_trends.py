"""
Collecteur Google Trends via pytrends (pas de cle API necessaire).
Scope : interet de recherche pour les 9 marques suivies, sur la Cote d'Ivoire,
sur les 12 derniers mois, par semaine.
"""

from datetime import datetime
import pandas as pd

from .base import Collector, COMPETITORS, GEO_CODE


class GoogleTrendsCollector(Collector):
    name = "google_trends"
    table = "trends"
    required_env: list = []      # pytrends fonctionne sans cle, mais peut etre rate-limite

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

        pytrends = TrendReq(hl="fr-FR", tz=0, retries=2, backoff_factor=0.3)
        all_frames = []
        # Betclic reste dans chaque chunk pour normaliser les echelles inter-chunks
        anchor = "Betclic"
        others = [k for k in COMPETITORS if k != anchor]
        chunks = [
            [anchor] + others[i:i + self.CHUNK_SIZE - 1]
            for i in range(0, len(others), self.CHUNK_SIZE - 1)
        ]

        for kws in chunks:
            try:
                pytrends.build_payload(kws, timeframe=self.TIMEFRAME, geo=self.GEO)
                df = pytrends.interest_over_time()
                if df is None or df.empty:
                    continue
                if "isPartial" in df.columns:
                    df = df.drop(columns=["isPartial"])
                df = df.reset_index().rename(columns={"date": "date"})
                long = df.melt(id_vars="date", var_name="keyword", value_name="interest")
                all_frames.append(long)
            except Exception as e:
                # Un chunk qui echoue ne doit pas tuer les autres
                print(f"[google_trends] chunk {kws} : {e}")
                continue

        if not all_frames:
            return pd.DataFrame()

        out = pd.concat(all_frames, ignore_index=True)
        out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
        out["geo"] = self.GEO
        # dedupliquer (Betclic apparait dans chaque chunk)
        out = out.drop_duplicates(subset=["date", "keyword"], keep="first")
        return out
