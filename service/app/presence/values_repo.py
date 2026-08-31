"""Persistent protect list — the things the user wants reclaimed time spent on.

The in-memory ValuesStore reset on every restart; this keeps the list in the
shared gtb.db so what you add sticks. Same list()/add() surface as before, plus
remove(). Seeded once from the mock defaults so a fresh install isn't empty.
"""
from __future__ import annotations

from ..db import connect, lock
from .values import Value


class ValuesRepo:
    def __init__(self, seed=None):
        self._init_db()
        if seed and self._count() == 0:
            for v in seed:
                self._write(v)

    def _init_db(self):
        with lock(), connect() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS values_protect (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                minutes INTEGER NOT NULL,
                start_at TEXT NOT NULL DEFAULT '',
                priority INTEGER NOT NULL DEFAULT 99)""")

    def _count(self):
        with lock(), connect() as c:
            return c.execute("SELECT COUNT(*) FROM values_protect").fetchone()[0]

    def _write(self, v: Value):
        with lock(), connect() as c:
            c.execute("INSERT OR REPLACE INTO values_protect "
                      "(id, label, minutes, start_at, priority) VALUES (?,?,?,?,?)",
                      (v.id, v.label, int(v.minutes), v.when, int(v.priority)))

    def list(self):
        with lock(), connect() as c:
            rows = c.execute("SELECT id, label, minutes, start_at, priority "
                             "FROM values_protect ORDER BY priority, label").fetchall()
        return [Value(id=r[0], label=r[1], minutes=r[2], when=r[3], priority=r[4])
                for r in rows]

    def add(self, value: Value) -> Value:
        self._write(value)
        return value

    def remove(self, value_id: str) -> bool:
        with lock(), connect() as c:
            return c.execute("DELETE FROM values_protect WHERE id = ?",
                             (value_id,)).rowcount > 0
