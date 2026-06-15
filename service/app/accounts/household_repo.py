"""Persistent shared household (SQLite).

A household is created by one user and joined by others via an invite code.
Each member sets their own driving capability, consent flags, and busy windows.
build_for_user() assembles the live Household / TimeMap / Consent the matcher
needs — the multi-user replacement for the fixture loader.
"""
from __future__ import annotations

import secrets

from ..db import connect, lock
from ..household import Consent, Household, Member, MemberConsent, TimeMap


class HouseholdRepo:
    def __init__(self):
        self._init_db()

    def _init_db(self) -> None:
        with lock(), connect() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS households (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, code TEXT UNIQUE NOT NULL,
                owner_id TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT (datetime('now')))""")
            c.execute("""CREATE TABLE IF NOT EXISTS memberships (
                household_id TEXT NOT NULL, user_id TEXT NOT NULL,
                can_drive INTEGER NOT NULL DEFAULT 1,
                shares INTEGER NOT NULL DEFAULT 0,
                accepts INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (household_id, user_id))""")
            c.execute("""CREATE TABLE IF NOT EXISTS availability (
                user_id TEXT NOT NULL, start_min INTEGER NOT NULL, end_min INTEGER NOT NULL)""")

    # --- household lifecycle ---
    def create(self, name: str, owner_id: str) -> dict:
        hid = "h_" + secrets.token_hex(6)
        code = secrets.token_hex(3).upper()      # short invite code
        with lock(), connect() as c:
            c.execute("INSERT INTO households (id,name,code,owner_id) VALUES (?,?,?,?)",
                      (hid, name.strip(), code, owner_id))
            c.execute("INSERT INTO memberships (household_id,user_id,can_drive,shares,accepts) "
                      "VALUES (?,?,1,1,1)", (hid, owner_id))   # owner opts in by default
        return {"id": hid, "name": name.strip(), "code": code}

    def join(self, code: str, user_id: str) -> dict:
        code = code.strip().upper()
        with lock(), connect() as c:
            h = c.execute("SELECT id,name FROM households WHERE code=?", (code,)).fetchone()
            if not h:
                raise ValueError("No household with that code.")
            c.execute("INSERT OR IGNORE INTO memberships (household_id,user_id) VALUES (?,?)",
                      (h["id"], user_id))
        return {"id": h["id"], "name": h["name"], "code": code}

    def household_of(self, user_id: str) -> str | None:
        with lock(), connect() as c:
            row = c.execute("SELECT household_id FROM memberships WHERE user_id=? LIMIT 1",
                            (user_id,)).fetchone()
        return row["household_id"] if row else None

    # --- per-member settings ---
    def set_membership(self, household_id: str, user_id: str,
                       can_drive: bool, shares: bool, accepts: bool) -> None:
        with lock(), connect() as c:
            c.execute("UPDATE memberships SET can_drive=?,shares=?,accepts=? "
                      "WHERE household_id=? AND user_id=?",
                      (int(can_drive), int(shares), int(accepts), household_id, user_id))

    def set_availability(self, user_id: str, busy: list[tuple[int, int]]) -> None:
        with lock(), connect() as c:
            c.execute("DELETE FROM availability WHERE user_id=?", (user_id,))
            c.executemany("INSERT INTO availability (user_id,start_min,end_min) VALUES (?,?,?)",
                          [(user_id, s, e) for s, e in busy])

    # --- assemble for the matcher ---
    def build_for_user(self, user_id: str):
        """Return (Household, TimeMap, Consent) for this user's household, or None."""
        hid = self.household_of(user_id)
        if not hid:
            return None
        with lock(), connect() as c:
            rows = c.execute(
                "SELECT u.id,u.name,u.email,m.can_drive,m.shares,m.accepts "
                "FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.household_id=?",
                (hid,)).fetchall()
            busy_rows = c.execute(
                "SELECT a.user_id,a.start_min,a.end_min FROM availability a "
                "JOIN memberships m ON m.user_id=a.user_id WHERE m.household_id=?",
                (hid,)).fetchall()
        members = [Member(id=r["id"], name=r["name"], can_drive=bool(r["can_drive"]),
                          email=r["email"]) for r in rows]
        household = Household(me=user_id, members=members)
        busy: dict[str, list[tuple[int, int]]] = {}
        for r in busy_rows:
            busy.setdefault(r["user_id"], []).append((r["start_min"], r["end_min"]))
        timemap = TimeMap(busy)
        consent = Consent({r["id"]: MemberConsent(shares_availability=bool(r["shares"]),
                                                  accepts_handoffs=bool(r["accepts"])) for r in rows})
        return household, timemap, consent

    def roster(self, user_id: str) -> dict:
        hid = self.household_of(user_id)
        if not hid:
            return {"household": None, "members": []}
        with lock(), connect() as c:
            h = c.execute("SELECT name,code FROM households WHERE id=?", (hid,)).fetchone()
            rows = c.execute(
                "SELECT u.id,u.name,m.can_drive,m.shares,m.accepts FROM memberships m "
                "JOIN users u ON u.id=m.user_id WHERE m.household_id=?", (hid,)).fetchall()
        return {
            "household": {"name": h["name"], "code": h["code"]},
            "members": [{"id": r["id"], "name": r["name"], "can_drive": bool(r["can_drive"]),
                         "shares_availability": bool(r["shares"]), "accepts_handoffs": bool(r["accepts"]),
                         "is_me": r["id"] == user_id} for r in rows],
        }
