"""Password authentication and server-side sessions (Argon2id + HttpOnly cookie)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import HTTPException, Request

from app.config import settings

_hasher = PasswordHasher()
COOKIE_NAME = "av_session"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def users_exist(conn) -> bool:
    return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0


def create_user(conn, password: str) -> int:
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if users_exist(conn):
        raise HTTPException(status_code=409, detail="Password is already configured")
    cur = conn.execute(
        "INSERT INTO users (password_hash, created_at) VALUES (?, ?)",
        (hash_password(password), _now().isoformat()),
    )
    conn.commit()
    return int(cur.lastrowid)


def authenticate(conn, password: str) -> int | None:
    row = conn.execute("SELECT id, password_hash FROM users ORDER BY id LIMIT 1").fetchone()
    if row is None or not verify_password(password, row["password_hash"]):
        return None
    return int(row["id"])


def create_session(conn, user_id: int, remember: bool = False) -> tuple[str, int]:
    token = secrets.token_urlsafe(32)
    days = settings.remember_days if remember else 0
    hours = settings.session_hours
    expires = _now() + (timedelta(days=days) if remember else timedelta(hours=hours))
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
        (_token_hash(token), user_id, expires.isoformat(), _now().isoformat()),
    )
    conn.execute("DELETE FROM sessions WHERE expires_at < ?", (_now().isoformat(),))
    conn.commit()
    max_age = int((expires - _now()).total_seconds())
    return token, max_age


def delete_session(conn, token: str) -> None:
    conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
    conn.commit()


def session_user(conn, token: str | None) -> dict | None:
    if not token:
        return None
    row = conn.execute(
        "SELECT s.user_id, s.expires_at FROM sessions s WHERE s.token_hash = ?",
        (_token_hash(token),),
    ).fetchone()
    if row is None:
        return None
    if datetime.fromisoformat(row["expires_at"]) < _now():
        delete_session(conn, token)
        return None
    return {"id": int(row["user_id"])}


def require_user(request: Request, conn) -> dict:
    user = session_user(conn, request.cookies.get(COOKIE_NAME))
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
