"""Feedback harness — the agent learns your restraint, and your edits.

Records what you did with each suggestion and turns that history into learned
behavior:

  1. interrupt threshold — dismiss interrupts in a value band enough and the bar
     to interrupt you rises above it (never above a band you've welcomed);
  2. kind suppression — a kind you wave off stops earning interrupts (an *edit*
     counts as wanted, not waved off, so tweaking keeps a kind alive);
  3. preferred edits — when you keep changing a suggestion to the same thing,
     the agent surfaces that preference proactively;
  4. decay — only recent feedback shapes behavior, so the agent tracks a life
     that changes instead of anchoring on last quarter.

Keyed off a stable suggestion signature, not the volatile confirm-action id, so
learning survives across cycles. Stored in the shared gtb.db — no new infra.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from ..db import connect, lock
from .planner import _INTERRUPT_MIN as _DEFAULT_INTERRUPT

VERDICTS = ("accepted", "rejected", "edited", "ignored")

_MIN_REJECTS = 3        # don't move the threshold on thin evidence
_FLOOR, _CEIL = 30, 120
_SUPPRESS_RATE = 0.25   # kind positive-rate below this...
_SUPPRESS_SAMPLES = 4   # ...over at least this many acted-on suggestions
_MIN_EDITS = 2          # repeat an edit this many times before it's a preference
_DECAY_DAYS = 90        # only feedback newer than this shapes behavior


@dataclass
class Prefs:
    interrupt_min: int
    suppressed_kinds: frozenset
    rejected_ids: frozenset
    preferred_edits: dict = field(default_factory=dict)


def _threshold(rows) -> int:
    ints = [r for r in rows if r["interrupt"]]
    rej = sorted(r["value_minutes"] for r in ints if r["verdict"] == "rejected")
    acc = sorted(r["value_minutes"] for r in ints if r["verdict"] == "accepted")
    if len(rej) < _MIN_REJECTS:
        return _DEFAULT_INTERRUPT
    t = max(rej) + 5                     # stop interrupting below what they dismissed
    if acc:
        t = min(t, min(acc))             # but keep interrupting for values they welcomed
    return max(_FLOOR, min(_CEIL, t))


def _suppressed(rows) -> frozenset:
    tally = {}
    for r in rows:
        tally.setdefault(r["kind"], [0, 0])
        if r["verdict"] in ("accepted", "edited"):   # an edit is 'wanted, tweaked'
            tally[r["kind"]][0] += 1
        elif r["verdict"] == "rejected":
            tally[r["kind"]][1] += 1
    out = set()
    for kind, (pos, neg) in tally.items():
        n = pos + neg
        if n >= _SUPPRESS_SAMPLES and pos / n < _SUPPRESS_RATE:
            out.add(kind)
    return frozenset(out)


def _preferred_edits(rows) -> dict:
    by_sig = {}
    for r in rows:
        if r["verdict"] == "edited" and r.get("edited_to"):
            by_sig.setdefault(r["suggestion_id"], Counter())[r["edited_to"]] += 1
    out = {}
    for sig, ctr in by_sig.items():
        val, n = ctr.most_common(1)[0]
        if n >= _MIN_EDITS:
            out[sig] = val
    return out


class FeedbackStore:
    def __init__(self):
        self._init_db()

    def _init_db(self) -> None:
        with lock(), connect() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS agent_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                suggestion_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                value_minutes INTEGER NOT NULL,
                interrupt INTEGER NOT NULL,
                verdict TEXT NOT NULL,
                edited_to TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')))""")
            try:   # migrate an older table that predates edit-learning
                c.execute("ALTER TABLE agent_feedback ADD COLUMN edited_to TEXT")
            except Exception:
                pass

    def record(self, suggestion_id, kind, value_minutes, interrupt, verdict,
               user_id=None, edited_to=None):
        if verdict not in VERDICTS:
            raise ValueError(f"unknown verdict: {verdict!r}")
        with lock(), connect() as c:
            c.execute("""INSERT INTO agent_feedback
                (user_id, suggestion_id, kind, value_minutes, interrupt, verdict, edited_to)
                VALUES (?,?,?,?,?,?,?)""",
                      (user_id, suggestion_id, kind, int(value_minutes),
                       1 if interrupt else 0, verdict, edited_to))

    def _rows(self, user_id=None, within_days=None):
        clause = "user_id IS NULL" if user_id is None else "user_id = ?"
        params = [] if user_id is None else [user_id]
        q = f"SELECT * FROM agent_feedback WHERE {clause}"
        if within_days is not None:
            q += " AND created_at >= datetime('now', ?)"
            params.append(f"-{int(within_days)} days")
        with lock(), connect() as c:
            return [dict(r) for r in c.execute(q, params).fetchall()]

    def prefs(self, user_id=None) -> Prefs:
        rows = self._rows(user_id, within_days=_DECAY_DAYS)   # decay: recent only
        return Prefs(
            interrupt_min=_threshold(rows),
            suppressed_kinds=_suppressed(rows),
            rejected_ids=frozenset(r["suggestion_id"] for r in rows
                                   if r["verdict"] == "rejected"),
            preferred_edits=_preferred_edits(rows))

    def stats(self, user_id=None) -> dict:
        rows = self._rows(user_id)                            # all-time counts
        by_kind = {}
        for r in rows:
            d = by_kind.setdefault(r["kind"],
                                   {"accepted": 0, "rejected": 0, "edited": 0, "ignored": 0})
            d[r["verdict"]] = d.get(r["verdict"], 0) + 1
        p = self.prefs(user_id)
        return {"total": len(rows), "by_kind": by_kind,
                "interrupt_min": p.interrupt_min,
                "suppressed_kinds": sorted(p.suppressed_kinds),
                "preferred_edits": p.preferred_edits,
                "learning_window_days": _DECAY_DAYS}
