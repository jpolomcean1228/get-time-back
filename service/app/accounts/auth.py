"""User accounts + sessions (SQLite).

Prototype-grade and clearly so: passwords are salted + PBKDF2-hashed (good), but
there's no email verification, tokens don't expire, and there's no rate
limiting. It's a real multi-user foundation to harden, not a finished auth
system. See the hardening notes in ACCOUNTS_SETUP.md.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

from ..db import connect, lock

_ITERATIONS = 120_000


@dataclass
class User:
    id: str
    name: str
    email: str


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _ITERATIONS).hex()


class AuthStore:
    def __init__(self):
        self._init_db()

    def _init_db(self) -> None:
        with lock(), connect() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
                pw_hash TEXT NOT NULL, pw_salt TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')))""")
            c.execute("""CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY, user_id TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(user_id) REFERENCES users(id))""")

    def register(self, name: str, email: str, password: str) -> str:
        email = email.strip().lower()
        uid = "u_" + secrets.token_hex(8)
        salt = secrets.token_hex(16)
        with lock(), connect() as c:
            if c.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
                raise ValueError("That email is already registered.")
            c.execute("INSERT INTO users (id,name,email,pw_hash,pw_salt) VALUES (?,?,?,?,?)",
                      (uid, name.strip(), email, _hash(password, salt), salt))
        return self._new_session(uid)

    def login(self, email: str, password: str) -> str:
        email = email.strip().lower()
        with lock(), connect() as c:
            row = c.execute("SELECT id,pw_hash,pw_salt FROM users WHERE email=?", (email,)).fetchone()
        if not row or _hash(password, row["pw_salt"]) != row["pw_hash"]:
            raise ValueError("Wrong email or password.")
        return self._new_session(row["id"])

    def _new_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        with lock(), connect() as c:
            c.execute("INSERT INTO sessions (token,user_id) VALUES (?,?)", (token, user_id))
        return token

    def logout(self, token: str) -> None:
        with lock(), connect() as c:
            c.execute("DELETE FROM sessions WHERE token=?", (token,))

    def user_for_token(self, token: str) -> User | None:
        if not token:
            return None
        with lock(), connect() as c:
            row = c.execute(
                "SELECT u.id,u.name,u.email FROM sessions s JOIN users u ON u.id=s.user_id "
                "WHERE s.token=?", (token,)).fetchone()
        return User(id=row["id"], name=row["name"], email=row["email"]) if row else None
