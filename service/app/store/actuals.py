"""Actuals store.

The feedback loop's memory. When a task is marked done, its real duration is
recorded here; the learned estimator queries the running stats to correct
future estimates. SQLite keeps it zero-infra — one file on disk, no server.
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
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    signature TEXT NOT NULL,
                    active    INTEGER NOT NULL,
                    total     INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_actuals_sig ON actuals(signature)")

    def record(self, signature: str, active: int, total: int) -> None:
        """Log one real completion."""
        with self._lock, self._conn() as c:
            c.execute(
                "INSERT INTO actuals (signature, active, total) VALUES (?, ?, ?)",
                (signature, int(active), int(total)),
            )

    def stats(self, signature: str) -> tuple[int, float, float]:
        """Return (count, mean_active, mean_total) for a signature."""
        with self._lock, self._conn() as c:
            row = c.execute(
                "SELECT COUNT(*) n, AVG(active) ma, AVG(total) mt "
                "FROM actuals WHERE signature = ?",
                (signature,),
            ).fetchone()
        n = row["n"] or 0
        return n, (row["ma"] or 0.0), (row["mt"] or 0.0)
