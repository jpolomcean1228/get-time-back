"""Shared SQLite connection for the persistent stores (accounts, household).

One file on disk, several tables. Keeps the multi-user backend zero-infra while
being a real, shared, persistent store rather than a fixture.
"""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "gtb.db"
_lock = threading.Lock()


def connect() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def lock():
    return _lock
