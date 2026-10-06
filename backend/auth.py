"""Accounts and login sessions.

Passwords: PBKDF2-SHA256 with a random salt per user. The supplied accounts use
the format  pbkdf2_sha256$<salt>$<hex digest>  at 120,000 iterations; new
accounts are stored as  pbkdf2_sha256$600000$<salt>$<hex digest>  so the
iteration count travels with the hash. Both formats are verified.

Sessions: a random token in an HttpOnly cookie. Only a SHA-256 of the token is
stored (table `sessions`), so a copy of the database can't be used to log in.

Passwords and hashes are never returned, logged or passed to the chatbot.
"""

import hashlib
import hmac
import os
import re
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, HTTPException, Request, Response

from db import connect_rw
from models import LoginRequest, SignupRequest, UserOut

PBKDF2_ITERATIONS = 600_000
LEGACY_ITERATIONS = 120_000  # the supplied accounts' 3-part hashes
MIN_PASSWORD = 8
SESSION_COOKIE = "cc_session"
SESSION_DAYS = 7
# Set COOKIE_SECURE=1 when served over HTTPS; local dev runs on plain http.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "0") == "1"
MAX_FAILED_LOGINS = 5
FAILED_LOGIN_WINDOW = 15 * 60  # seconds

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------- passwords

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$")
    if len(parts) == 4 and parts[0] == "pbkdf2_sha256" and parts[1].isdigit():
        iterations, salt, digest = int(parts[1]), parts[2], parts[3]
    elif len(parts) == 3 and parts[0] == "pbkdf2_sha256":
        iterations, salt, digest = LEGACY_ITERATIONS, parts[1], parts[2]
    else:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()
    return hmac.compare_digest(candidate, digest)


# Checked when the email doesn't exist, so a wrong email takes as long as a wrong password.
_DUMMY_HASH = hash_password(secrets.token_hex(16))


# ---------------------------------------------------------------- sessions

def ensure_sessions_table() -> None:
    with connect_rw() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sessions (
                   token_hash TEXT PRIMARY KEY,
                   user_id INTEGER NOT NULL,
                   created_at TEXT NOT NULL DEFAULT (datetime('now')),
                   expires_at TEXT NOT NULL,
                   FOREIGN KEY (user_id) REFERENCES users(id)
               )"""
        )


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _utc(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def start_session(response: Response, user_id: int) -> None:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    with connect_rw() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (_utc(now),))
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (_token_hash(token), user_id, _utc(now + timedelta(days=SESSION_DAYS))),
        )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_DAYS * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/",
    )


def current_user(token: str | None) -> dict | None:
    """The logged-in user for a session cookie, or None. Never includes the hash."""
    if not token:
        return None
    with connect_rw() as conn:
        row = conn.execute(
            """SELECT u.id, u.first_name, u.last_name, u.name, u.email
               FROM sessions s JOIN users u ON u.id = s.user_id
               WHERE s.token_hash = ? AND s.expires_at > ?""",
            (_token_hash(token), _utc(datetime.now(timezone.utc))),
        ).fetchone()
    return public_user(row) if row else None


def public_user(row) -> dict:
    first = row["first_name"] or (row["name"] or "").split(" ")[0]
    last = row["last_name"] or ""
    return {"id": row["id"], "first_name": first, "last_name": last, "email": row["email"]}


# ---------------------------------------------------------------- login throttling

_failed: dict[str, deque] = defaultdict(deque)


def _too_many_failures(key: str) -> bool:
    attempts = _failed[key]
    cutoff = time.monotonic() - FAILED_LOGIN_WINDOW
    while attempts and attempts[0] < cutoff:
        attempts.popleft()
    return len(attempts) >= MAX_FAILED_LOGINS


# ---------------------------------------------------------------- routes

def _clean_email(email: str) -> str:
    return email.strip().lower()


@router.post("/signup", response_model=UserOut, status_code=201)
def signup(body: SignupRequest, response: Response) -> dict:
    first, last, email = body.first_name.strip(), body.last_name.strip(), _clean_email(body.email)
    if not first or not last:
        raise HTTPException(400, "Please enter your first and last name.")
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Please enter a valid email address.")
    if len(body.password) < MIN_PASSWORD:
        raise HTTPException(400, f"Password must be at least {MIN_PASSWORD} characters.")
    if body.password != body.confirm_password:
        raise HTTPException(400, "Passwords don't match.")

    with connect_rw() as conn:
        if conn.execute("SELECT 1 FROM users WHERE lower(email) = ?", (email,)).fetchone():
            raise HTTPException(409, "An account with this email already exists. Try logging in instead.")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
            (f"{first} {last}", email, hash_password(body.password), first, last),
        )
        user_id = cur.lastrowid
    start_session(response, user_id)
    return {"id": user_id, "first_name": first, "last_name": last, "email": email}


@router.post("/login", response_model=UserOut)
def login(body: LoginRequest, request: Request, response: Response) -> dict:
    email = _clean_email(body.email)
    throttle_key = f"{request.client.host if request.client else '?'}|{email}"
    if _too_many_failures(throttle_key):
        raise HTTPException(429, "Too many failed attempts. Please wait 15 minutes and try again.")

    with connect_rw() as conn:
        row = conn.execute(
            "SELECT id, first_name, last_name, name, email, password_hash FROM users WHERE lower(email) = ?",
            (email,),
        ).fetchone()
    ok = verify_password(body.password, row["password_hash"] if row else _DUMMY_HASH) and row is not None
    if not ok:
        _failed[throttle_key].append(time.monotonic())
        # Same message either way, so the form doesn't reveal which emails have accounts.
        raise HTTPException(401, "Incorrect email or password.")
    _failed.pop(throttle_key, None)
    start_session(response, row["id"])
    return public_user(row)


@router.post("/logout", status_code=204)
def logout(response: Response, cc_session: str | None = Cookie(None)) -> Response:
    if cc_session:
        with connect_rw() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(cc_session),))
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax", secure=COOKIE_SECURE)
    response.status_code = 204
    return response


@router.get("/me", response_model=UserOut | None)
def me(cc_session: str | None = Cookie(None)) -> dict | None:
    # 200 with null when logged out: "nobody is logged in" is a normal answer,
    # not an error, so the browser console stays clean.
    return current_user(cc_session)
