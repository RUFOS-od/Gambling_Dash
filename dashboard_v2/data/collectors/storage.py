"""
Couche de persistance SQLite + snapshots JSON pour les donnees de veille.

Schema :
  trends(run_id, collected_at, keyword, date, interest, geo)
  news(run_id, collected_at, published, title, link, source, summary, brand)
  ads(run_id, collected_at, page_name, brand, ad_snapshot_url, start_date,
      impressions_range, country, ad_creative_body)
  youtube_videos(run_id, collected_at, video_id, title, channel, published,
                 views, likes, comments, brand)
  run_log(id, collector, started_at, ok, n_rows, error)
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional
import pandas as pd


DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "intel.db"
SNAPSHOT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "intel_snapshots"


SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS trends (
        run_id TEXT, collected_at TEXT, keyword TEXT, date TEXT,
        interest INTEGER, geo TEXT
    );""",
    """CREATE TABLE IF NOT EXISTS news (
        run_id TEXT, collected_at TEXT, published TEXT, title TEXT,
        link TEXT, source TEXT, summary TEXT, brand TEXT
    );""",
    """CREATE TABLE IF NOT EXISTS ads (
        run_id TEXT, collected_at TEXT, page_name TEXT, brand TEXT,
        ad_snapshot_url TEXT, start_date TEXT, impressions_range TEXT,
        country TEXT, ad_creative_body TEXT
    );""",
    """CREATE TABLE IF NOT EXISTS youtube_videos (
        run_id TEXT, collected_at TEXT, video_id TEXT, title TEXT,
        channel TEXT, published TEXT, views INTEGER, likes INTEGER,
        comments INTEGER, brand TEXT
    );""",
    """CREATE TABLE IF NOT EXISTS run_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        collector TEXT, started_at TEXT, ok INTEGER,
        n_rows INTEGER, error TEXT
    );""",
    "CREATE INDEX IF NOT EXISTS idx_trends_kw ON trends(keyword, date);",
    "CREATE INDEX IF NOT EXISTS idx_news_brand ON news(brand, published);",
    "CREATE INDEX IF NOT EXISTS idx_ads_brand ON ads(brand, start_date);",
    "CREATE INDEX IF NOT EXISTS idx_yt_brand ON youtube_videos(brand, published);",
    "CREATE INDEX IF NOT EXISTS idx_log_collector ON run_log(collector, started_at);",
]


class Storage:
    """Acces SQLite + snapshots JSON. Thread-safe via connections a la demande."""

    def __init__(self, db_path: Path = DEFAULT_DB, snapshot_dir: Path = SNAPSHOT_DIR):
        self.db_path = Path(db_path)
        self.snapshot_dir = Path(snapshot_dir)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    @contextmanager
    def _conn(self):
        con = sqlite3.connect(str(self.db_path))
        try:
            yield con
            con.commit()
        finally:
            con.close()

    def _ensure_schema(self):
        with self._conn() as con:
            for stmt in SCHEMA_STATEMENTS:
                con.execute(stmt)

    # ------------------------------------------------------------------
    # Ecriture
    # ------------------------------------------------------------------
    def save(self, table: str, df: pd.DataFrame, snapshot: bool = True):
        """Ajoute les lignes dans `table`. Enregistre optionnellement un snapshot JSON."""
        if df is None or len(df) == 0:
            return
        df = df.copy()
        if "run_id" not in df.columns:
            df["run_id"] = datetime.now().strftime("%Y%m%d_%H%M%S")
        if "collected_at" not in df.columns:
            df["collected_at"] = datetime.now().isoformat()

        # Harmoniser colonnes avec la table
        with self._conn() as con:
            cols_info = con.execute(f"PRAGMA table_info({table})").fetchall()
            table_cols = [c[1] for c in cols_info]
            if not table_cols:
                raise ValueError(f"Table inconnue : {table}")
            # Colonnes non declarees : on les ignore pour garder la coherence du schema
            df = df[[c for c in df.columns if c in table_cols]]
            # Colonnes manquantes : on remplit par None
            for c in table_cols:
                if c not in df.columns:
                    df[c] = None
            df = df[table_cols]
            df.to_sql(table, con, if_exists="append", index=False)

        if snapshot:
            self._write_snapshot(table, df)

    def _write_snapshot(self, table: str, df: pd.DataFrame):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.snapshot_dir / f"{table}_{ts}.json"
        try:
            df.head(200).to_json(path, orient="records", force_ascii=False, indent=2)
        except Exception:
            pass  # un snapshot manquant ne doit jamais bloquer le run

    def log_run(self, collector: str, ok: bool, n_rows: int, error: Optional[str]):
        with self._conn() as con:
            con.execute(
                "INSERT INTO run_log (collector, started_at, ok, n_rows, error) VALUES (?, ?, ?, ?, ?)",
                (collector, datetime.now().isoformat(), 1 if ok else 0, n_rows, error),
            )

    # ------------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------------
    def latest(self, table: str, limit: Optional[int] = None) -> pd.DataFrame:
        """Retourne le snapshot le plus recent : uniquement les lignes du dernier run_id."""
        with self._conn() as con:
            try:
                last_run = con.execute(
                    f"SELECT run_id FROM {table} ORDER BY collected_at DESC LIMIT 1"
                ).fetchone()
            except sqlite3.OperationalError:
                return pd.DataFrame()
            if not last_run:
                return pd.DataFrame()
            run_id = last_run[0]
            q = f"SELECT * FROM {table} WHERE run_id = ?"
            if limit:
                q += f" LIMIT {int(limit)}"
            return pd.read_sql_query(q, con, params=(run_id,))

    def all_rows(self, table: str, limit: Optional[int] = None) -> pd.DataFrame:
        with self._conn() as con:
            q = f"SELECT * FROM {table} ORDER BY collected_at DESC"
            if limit:
                q += f" LIMIT {int(limit)}"
            try:
                return pd.read_sql_query(q, con)
            except Exception:
                return pd.DataFrame()

    def last_run_info(self, collector: str) -> Optional[dict]:
        with self._conn() as con:
            row = con.execute(
                "SELECT collector, started_at, ok, n_rows, error "
                "FROM run_log WHERE collector = ? ORDER BY started_at DESC LIMIT 1",
                (collector,),
            ).fetchone()
        if not row:
            return None
        return {
            "collector": row[0],
            "started_at": row[1],
            "ok": bool(row[2]),
            "n_rows": row[3],
            "error": row[4],
        }

    def age_minutes(self, collector: str) -> Optional[float]:
        info = self.last_run_info(collector)
        if not info:
            return None
        try:
            t = datetime.fromisoformat(info["started_at"])
            return (datetime.now() - t).total_seconds() / 60.0
        except Exception:
            return None
