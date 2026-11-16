"""
Classe de base pour tous les collecteurs de veille.
Chaque collecteur concret implemente `fetch()` qui retourne un DataFrame
normalise. Le framework se charge du logging, des timeouts et du stockage.

Le perimetre est le marche ivoirien : marques du questionnaire en vigueur,
contenus publies en Cote d'Ivoire ou qui la concernent, 12 derniers mois.
"""

import re
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
import traceback
import pandas as pd


# Marques suivies : questionnaire en vigueur (Vague Novembre 2026).
# Bet365 n'est pas deploye en Cote d'Ivoire : retire. Bet 360 est une marque distincte.
COMPETITORS = [
    "Betclic", "1XBET", "Melbet", "BetMomo", "Sportcash", "Paripesa", "Premier Bet",
    "1WIN", "Betwinner", "Bet 360", "AkwaBet", "YellowBet", "Afropari", "BetPawa",
    "Chopbet", "Betway", "KifBet",
]

# Graphies rencontrees dans la presse et sur YouTube (comparaison sans accents ni casse)
BRAND_ALIASES = {
    "Betclic": ["betclic"],
    "1XBET": ["1xbet", "1x bet"],
    "Melbet": ["melbet"],
    "BetMomo": ["betmomo", "bet momo"],
    "Sportcash": ["sportcash", "sport cash"],
    "Paripesa": ["paripesa", "pari pesa"],
    "Premier Bet": ["premier bet", "premierbet"],
    "1WIN": ["1win"],
    "Betwinner": ["betwinner"],
    "Bet 360": ["bet 360", "bet360"],
    "AkwaBet": ["akwabet", "akwa bet"],
    "YellowBet": ["yellowbet", "yellow bet"],
    "Afropari": ["afropari"],
    "BetPawa": ["betpawa"],
    "Chopbet": ["chopbet"],
    "Betway": ["betway"],
    "KifBet": ["kifbet"],
}

# Marche cible
GEO_CODE = "CI"          # ISO Cote d'Ivoire
LANG = "fr"              # francais
COUNTRY_NAME = "Côte d'Ivoire"
MAX_AGE_DAYS = 365       # fenetre de veille : 12 derniers mois

# Reperes ivoiriens : un contenu est retenu s'il cite l'un d'eux ou vient d'un media ivoirien
CI_KEYWORDS = [
    "cote d'ivoire", "cote d ivoire", "cotedivoire", "ivoirien", "ivoirienne", "abidjan",
    "yamoussoukro", "bouake", "korhogo", "daloa", "san pedro", "abengourou", "babi",
    "fcfa", "lonaci", "arjh", "elephants", "ligue 1 ivoirienne", "ci",
]
CI_SOURCES = [
    "abidjan.net", "fratmat", "linfodrome", "aip", "agence ivoirienne", "connectionivoirienne",
    "sport-ivoire", "mondialsport", "koaci", "pressecotedivoire", "l'intelligent d'abidjan",
    "abidjantv", "lebanco", "ivoirematin", "afrikipresse", "rti", "digitalmag.ci", "yeclo",
    "linfodrome", "lepointsur", "7info", "allo abidjan", "intelligent d'abidjan",
]
# Contenus d'affiliation (codes promo, avis, APK, classements) : bruit pour la veille de marque
AFFILIATE_PATTERNS = [
    r"code[s]? (promo|bonus)", r"\bpromo code", r"\bavis\b", r"\btest (complet|detaille)",
    r"\bapk\b", r"telecharger", r"meilleurs sites", r"top \d+", r"\bbonus d.inscription",
    r"comment (s.inscrire|s.inscrit|parier|gagner|faire|retirer|deposer|installer|ouvrir|creer|activer)",
    r"\binscription\b", r"\btutori", r"\bguide\b", r"devenir partenaire", r"\bfaille\b",
    r"bonus exclusif", r"nouveau compte", r"creer un compte", r"\binstaller\b",
    r"creation de compte", r"bonus supplementaire",
    r"\bcoupon du jour", r"\bpronostic", r"la reference des paris",
]
# Hors marche ivoirien : montants en euros, homonymes francais
NON_CI_PATTERNS = [r"€", r"\beuros?\b", r"betclic elite", r"\bfdj\b", r"\bloto\b", r"\barjel\b", r"\banj\b"]


def norm(text) -> str:
    """Minuscules, sans accents ni ponctuation superflue (pour les comparaisons)."""
    s = str(text or "").replace("’", "'").replace("‘", "'")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s)


def clean_title(title, source: str = "") -> str:
    """Retire le nom du média ajouté en fin de titre ("... – AIP – Agence Ivoirienne de Presse")."""
    t = str(title or "").strip()
    dash = lambda s: re.sub(r"\s*[-–—]\s*", " - ", s).strip()
    if source:
        td, sd = dash(t), dash(source)
        if td.lower().endswith(sd.lower()) and len(td) > len(sd) + 5:
            t = td[: -len(sd)]
    return t.rstrip(" -–—").replace("—", "-").strip()


def mentions_brand(text, brand: str) -> bool:
    t = norm(text)
    return any(re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", t)
               for a in BRAND_ALIASES.get(brand, [brand.lower()]))


def is_ci_context(text, source: str = "") -> bool:
    t, s = norm(text), norm(source)
    if any(cs in s for cs in CI_SOURCES) or s.endswith(".ci"):
        return True
    return any(re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", t) for k in CI_KEYWORDS)


def is_affiliate(text) -> bool:
    t = norm(text)
    return any(re.search(p, t) for p in AFFILIATE_PATTERNS)


def is_non_ci(text) -> bool:
    raw = str(text or "")
    t = norm(raw)
    return "€" in raw or any(re.search(p, t) for p in NON_CI_PATTERNS)


OTHER_COUNTRIES = ["benin", "senegal", "cameroun", "togo", "burkina", "mali", "guinee", "congo",
                   "gabon", "niger", "nigeria", "ghana", "kenya", "rdc", "france", "angola", "maroc"]


def other_country_only(text) -> bool:
    """Le titre cite un autre pays sans aucun repère ivoirien (ex. spot TV tourné au Bénin)."""
    t = norm(text)
    cites_other = any(re.search(r"(?<![a-z])" + c + r"(?![a-z])", t) for c in OTHER_COUNTRIES)
    return cites_other and not is_ci_context(text)


def has_non_latin(text) -> bool:
    """Titres en alphabets non latins (bengali, hindi, etc.) : hors cible francophone."""
    return any(ord(ch) > 0x24F and not (0x2000 <= ord(ch) <= 0x2BFF) and not (0x1F000 <= ord(ch) <= 0x1FAFF)
               for ch in str(text or ""))


def within_window(published, days: int = MAX_AGE_DAYS) -> bool:
    d = pd.to_datetime(published, errors="coerce", utc=True)
    if pd.isna(d):
        return False
    return d >= datetime.now(timezone.utc) - timedelta(days=days)


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


class CollectorError(RuntimeError):
    """Echec global d'une source (toutes les requetes ont echoue) : le statut passe en ECHEC."""


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
