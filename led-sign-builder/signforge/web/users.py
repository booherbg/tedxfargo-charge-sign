"""Accounts, sessions, tiers — stdlib sqlite3 + scrypt, no dependencies.

Roles: admin | user. Tiers: free | premium (admins get premium limits).
Open mode (--open / SIGNFORGE_OPEN=1) bypasses all of it for solo self-hosts.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional

SESSION_TTL_S = 30 * 24 * 3600

TIERS: dict[str, dict] = {
    "free": {"max_cap_mm": 150.0, "builds_per_day": 6, "max_queued": 1, "priority": 10},
    "premium": {"max_cap_mm": 2000.0, "builds_per_day": 200, "max_queued": 6, "priority": 0},
}


def data_dir() -> Path:
    d = Path(os.environ.get("SIGNFORGE_DATA", Path.home() / ".signforge"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _hash_pw(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)


class UserStore:
    def __init__(self, db_path: Optional[str] = None):
        self.path = db_path or str(data_dir() / "web.db")
        self._lock = threading.Lock()
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        with self._lock, self.db:
            self.db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users(
                  id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL,
                  salt BLOB NOT NULL, pw BLOB NOT NULL,
                  role TEXT NOT NULL DEFAULT 'user',
                  tier TEXT NOT NULL DEFAULT 'free',
                  created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions(
                  token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS build_log(
                  user_id INTEGER NOT NULL, ts REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs(
                  id TEXT PRIMARY KEY, user_id INTEGER, name TEXT, status TEXT,
                  params TEXT, created REAL, finished REAL);
                """
            )

    # ---- accounts -----------------------------------------------------------
    def ensure_admin(self) -> Optional[str]:
        """Create the first admin if no users exist. Returns the one-time
        password (from SIGNFORGE_ADMIN_PASSWORD or generated) or None."""
        with self._lock:
            n = self.db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        if n:
            return None
        pw = os.environ.get("SIGNFORGE_ADMIN_PASSWORD") or secrets.token_urlsafe(10)
        self.create_user("admin@local", pw, role="admin", tier="premium")
        return pw

    def create_user(self, email: str, password: str, role: str = "user", tier: str = "free") -> dict:
        email = email.strip().lower()
        if not email or "@" not in email or len(password) < 8:
            raise ValueError("valid email and a password of at least 8 characters required")
        salt = secrets.token_bytes(16)
        with self._lock, self.db:
            try:
                cur = self.db.execute(
                    "INSERT INTO users(email, salt, pw, role, tier, created) VALUES(?,?,?,?,?,?)",
                    (email, salt, _hash_pw(password, salt), role, tier, time.time()),
                )
            except sqlite3.IntegrityError as e:
                raise ValueError("email already registered") from e
        return {"id": cur.lastrowid, "email": email, "role": role, "tier": tier}

    def verify(self, email: str, password: str) -> Optional[dict]:
        with self._lock:
            row = self.db.execute(
                "SELECT * FROM users WHERE email=?", (email.strip().lower(),)
            ).fetchone()
        if not row:
            return None
        if not secrets.compare_digest(_hash_pw(password, row["salt"]), row["pw"]):
            return None
        return dict(row)

    # ---- sessions -----------------------------------------------------------
    def create_session(self, user_id: int) -> str:
        token = secrets.token_urlsafe(24)
        with self._lock, self.db:
            self.db.execute(
                "INSERT INTO sessions(token, user_id, created) VALUES(?,?,?)",
                (token, user_id, time.time()),
            )
        return token

    def get_session(self, token: str) -> Optional[dict]:
        if not token:
            return None
        with self._lock:
            row = self.db.execute(
                "SELECT u.id, u.email, u.role, u.tier, s.created FROM sessions s "
                "JOIN users u ON u.id = s.user_id WHERE s.token=?",
                (token,),
            ).fetchone()
        if not row or time.time() - row["created"] > SESSION_TTL_S:
            return None
        return dict(row)

    def delete_session(self, token: str) -> None:
        with self._lock, self.db:
            self.db.execute("DELETE FROM sessions WHERE token=?", (token,))

    # ---- admin --------------------------------------------------------------
    def list_users(self) -> list[dict]:
        with self._lock:
            rows = self.db.execute(
                "SELECT id, email, role, tier, created FROM users ORDER BY id"
            ).fetchall()
        return [dict(r) for r in rows]

    def update_user(self, uid: int, tier: Optional[str] = None, role: Optional[str] = None) -> None:
        if tier and tier not in TIERS:
            raise ValueError(f"unknown tier {tier!r}")
        if role and role not in ("admin", "user"):
            raise ValueError(f"unknown role {role!r}")
        with self._lock, self.db:
            if tier:
                self.db.execute("UPDATE users SET tier=? WHERE id=?", (tier, uid))
            if role:
                self.db.execute("UPDATE users SET role=? WHERE id=?", (role, uid))

    def delete_user(self, uid: int) -> None:
        with self._lock, self.db:
            self.db.execute("DELETE FROM users WHERE id=?", (uid,))
            self.db.execute("DELETE FROM sessions WHERE user_id=?", (uid,))

    # ---- quotas + job log ----------------------------------------------------
    def record_build(self, uid: int) -> None:
        with self._lock, self.db:
            self.db.execute("INSERT INTO build_log(user_id, ts) VALUES(?,?)", (uid, time.time()))

    def builds_today(self, uid: int) -> int:
        cutoff = time.time() - 24 * 3600
        with self._lock:
            return self.db.execute(
                "SELECT COUNT(*) c FROM build_log WHERE user_id=? AND ts>?", (uid, cutoff)
            ).fetchone()["c"]

    def log_job(self, job_id: str, user_id: int, name: str, status: str, params_json: str) -> None:
        with self._lock, self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO jobs(id,user_id,name,status,params,created,finished) "
                "VALUES(?,?,?,?,?,COALESCE((SELECT created FROM jobs WHERE id=?),?),?)",
                (job_id, user_id, name, status, params_json, job_id, time.time(),
                 time.time() if status in ("done", "error", "cancelled") else None),
            )

    def limits_for(self, user: dict) -> dict:
        tier = "premium" if user.get("role") == "admin" else user.get("tier", "free")
        return TIERS.get(tier, TIERS["free"])


OPEN_USER = {"id": 0, "email": "local@open-mode", "role": "admin", "tier": "premium"}
