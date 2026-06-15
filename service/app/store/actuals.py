"""Actuals store.

The feedback loop's memory. Each completion is logged with both its specific
signature and its category, so the learned estimator can query either level:
the exact recurring item, or the category average it falls back to. SQLite
keeps it zero-infra — one file on disk, no server.
"""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

_DEFAULT_PATH = Path(__file__).resolve().parents[2] / "gtb.db"


class ActualsStore:
    def __init__(self, path: str | Path = _DEFAULT_PATH):
        self._path = str(path)
        self._lock = threading.Lock()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self._path)
        c.row_factory = sqlite3.Row
        return c

    def _init_db(self) -> None:
        with self._lock, self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS actuals (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    signature  TEXT NOT NULL,
                    category   TEXT NOT NULL DEFAULT '',
                    active     INTEGER NOT NULL,
                    total      INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_actuals_sig ON actuals(signature)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_actuals_cat ON actuals(category)")

    def record(self, signature: str, category: str, active: int, total: int) -> None:
        """Log one real completion under its specific signature + category."""
        with self._lock, self._conn() as c:
            c.execute(
                "INSERT INTO actuals (signature, category, active, total) VALUES (?, ?, ?, ?)",
                (signature, category, int(active), int(total)),
            )

    def _stats(self, column: str, value: str) -> tuple[int, float, float]:
        with self._lock, self._conn() as c:
            row = c.execute(
                f"SELECT COUNT(*) n, AVG(active) ma, AVG(total) mt "
                f"FROM actuals WHERE {column} = ?",
                (value,),
            ).fetchone()
        n = row["n"] or 0
        return n, (row["ma"] or 0.0), (row["mt"] or 0.0)

    def stats(self, signature: str) -> tuple[int, float, float]:
        """(count, mean_active, mean_total) for a specific signature."""
        return self._stats("signature", signature)

    def stats_category(self, category: str) -> tuple[int, float, float]:
        """(count, mean_active, mean_total) for a whole category — the fallback."""
        return self._stats("category", category)
