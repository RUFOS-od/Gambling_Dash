"""
Classe de base pour tous les collecteurs de veille.
Chaque collecteur concret implemente `fetch()` qui retourne un DataFrame
normalise. Le framework se charge du logging, des timeouts et du stockage.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import traceback
import pandas as pd


# Concurrents suivis : aligne sur la liste questionnaire V1 (14 marques)
COMPETITORS = [
    "Betclic", "Chopbet", "1XBET", "Sportcash", "BetPawa",
    "Melbet", "Premier Bet", "BetMomo", "AkwaBet", "YellowBet",
    "Betway", "Afropari", "Paripesa", "Bet365",
]

# Marche cible
GEO_CODE = "CI"          # ISO Cote d'Ivoire
LANG = "fr"              # francais
COUNTRY_NAME = "Cote d'Ivoire"


@dataclass
class CollectorResult:
    """Resultat standardise d'une execution de collecteur."""
    name: str
    ok: bool
    n_rows: int = 0
    error: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None

    @property
    def duration_s(self) -> float:
        if self.finished_at is None:
            return 0.0
        return (self.finished_at - self.started_at).total_seconds()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "ok": self.ok,
            "n_rows": self.n_rows,
            "error": self.error,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_s": round(self.duration_s, 2),
        }


class Collector(ABC):
    """Classe abstraite. Chaque collecteur concret definit `name` et `fetch()`."""

    name: str = "base"
    table: str = "base"
    required_env: list = []   # variables d'environnement necessaires (sinon mode degrade)

    @abstractmethod
    def fetch(self) -> pd.DataFrame:
        """Retourne un DataFrame normalise pour ce collecteur."""
        raise NotImplementedError

    def is_available(self) -> bool:
        """Indique si toutes les dependances externes (cles API, reseau) sont presentes."""
        import os
        for var in self.required_env:
            if not os.environ.get(var):
                return False
        return True

    def run(self, storage) -> CollectorResult:
        """Execute fetch() avec capture d'erreurs, stocke le resultat, retourne un rapport."""
        res = CollectorResult(name=self.name, ok=False)
        try:
            df = self.fetch()
            if df is None:
                df = pd.DataFrame()
            res.n_rows = len(df)
            if len(df) > 0:
                storage.save(self.table, df)
            storage.log_run(self.name, ok=True, n_rows=len(df), error=None)
            res.ok = True
        except Exception as e:
            res.error = f"{type(e).__name__}: {e}"
            tb = traceback.format_exc(limit=2)
            storage.log_run(self.name, ok=False, n_rows=0, error=res.error + "\n" + tb)
        finally:
            res.finished_at = datetime.now()
        return res
