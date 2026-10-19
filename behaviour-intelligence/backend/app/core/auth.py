"""Simple login for the dashboard, Python standard library only.

- Users live in a small SQLite file (backend/users.db, gitignored).
- Passwords are stored as PBKDF2-HMAC-SHA256 hashes with a random salt.
- A session token is "<payload>.<signature>": base64url JSON {uid, exp, jti}
  signed with HMAC-SHA256. Logout stores the token id (jti) as revoked.
"""
import base64
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import time
from contextlib import closing

from app.core.config import AUTH_SECRET_PATH, SESSION_HOURS, USERS_DB_PATH

PBKDF2_ITERATIONS = 200_000
ROLES = ["Grid Planner", "Analyst", "Engineer", "Researcher"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

DEMO_USER = {
    "name": "Demo Planner",
    "email": "demo@ceb.lk",
    "organisation": "Ceylon Electricity Board",
    "role": "Grid Planner",
    "password": "Demo@2026",
}


class AuthError(Exception):
    """Raised with a plain-English message and an HTTP status code."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


# ── storage ──────────────────────────────────────────────────────────────────
def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(USERS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the tables if needed and make sure the demo account exists."""
    with closing(_connect()) as conn, conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            organisation TEXT NOT NULL,
            role TEXT NOT NULL,
            salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS revoked_tokens (
            jti TEXT PRIMARY KEY,
            expires_at INTEGER NOT NULL)""")
        conn.execute("DELETE FROM revoked_tokens WHERE expires_at < ?", (int(time.time()),))
        exists = conn.execute("SELECT 1 FROM users WHERE email = ?", (DEMO_USER["email"],)).fetchone()
    if not exists:
        create_user(DEMO_USER)


def _secret() -> bytes:
    """Token signing key: random, created once and kept in a gitignored file."""
    if not AUTH_SECRET_PATH.exists():
        AUTH_SECRET_PATH.write_text(secrets.token_hex(32), encoding="utf-8")
    return AUTH_SECRET_PATH.read_text(encoding="utf-8").strip().encode()


# ── passwords ────────────────────────────────────────────────────────────────
def _hash_password(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), PBKDF2_ITERATIONS).hex()


def _public(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "name": row["name"], "email": row["email"],
            "organisation": row["organisation"], "role": row["role"]}


# ── validation ───────────────────────────────────────────────────────────────
def validate_signup(data: dict) -> dict:
    """Return cleaned fields or raise AuthError(400) with a simple message."""
    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    organisation = str(data.get("organisation") or "").strip()
    role = str(data.get("role") or "").strip()
    password = str(data.get("password") or "")
    confirm = data.get("confirm_password")

    if len(name) < 2:
        raise AuthError(400, "Please enter your full name.")
    if not EMAIL_RE.match(email):
        raise AuthError(400, "Please enter a valid email address, for example name@ceb.lk.")
    if len(organisation) < 2:
        raise AuthError(400, "Please enter your organisation.")
    if role not in ROLES:
        raise AuthError(400, f"Please choose a role: {', '.join(ROLES)}.")
    if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise AuthError(400, "Password must be at least 8 characters and contain a letter and a number.")
    if confirm is not None and confirm != password:
        raise AuthError(400, "The two passwords do not match.")
    return {"name": name, "email": email, "organisation": organisation, "role": role, "password": password}


# ── users ────────────────────────────────────────────────────────────────────
def create_user(data: dict) -> dict:
    fields = validate_signup(data)
    salt = secrets.token_hex(16)
    try:
        with closing(_connect()) as conn, conn:
            cur = conn.execute(
                "INSERT INTO users (name, email, organisation, role, salt, password_hash) VALUES (?, ?, ?, ?, ?, ?)",
                (fields["name"], fields["email"], fields["organisation"], fields["role"], salt,
                 _hash_password(fields["password"], salt)))
            row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    except sqlite3.IntegrityError:
        raise AuthError(400, "An account with this email already exists. Please log in instead.")
    return _public(row)


def authenticate(email: str, password: str) -> dict:
    email = str(email or "").strip().lower()
    if not email or not password:
        raise AuthError(400, "Please enter your email and password.")
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if row is None or not hmac.compare_digest(_hash_password(password, row["salt"]), row["password_hash"]):
        raise AuthError(401, "Email or password is incorrect.")
    return _public(row)


# ── tokens ───────────────────────────────────────────────────────────────────
def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def issue_token(user_id: int) -> tuple[str, int]:
    expires = int(time.time()) + SESSION_HOURS * 3600
    payload = _b64(json.dumps({"uid": user_id, "exp": expires, "jti": secrets.token_hex(8)}).encode())
    signature = _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}", expires


def _decode(token: str) -> dict:
    try:
        payload, signature = token.split(".")
        expected = _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        claims = json.loads(_unb64(payload))
    except Exception:
        raise AuthError(401, "Your session is not valid. Please log in again.")
    if claims.get("exp", 0) < time.time():
        raise AuthError(401, "Your session has expired. Please log in again.")
    return claims


def user_from_token(token: str) -> dict:
    if not token:
        raise AuthError(401, "Please log in first.")
    claims = _decode(token)
    with closing(_connect()) as conn:
        if conn.execute("SELECT 1 FROM revoked_tokens WHERE jti = ?", (claims["jti"],)).fetchone():
            raise AuthError(401, "You have logged out. Please log in again.")
        row = conn.execute("SELECT * FROM users WHERE id = ?", (claims["uid"],)).fetchone()
    if row is None:
        raise AuthError(401, "This account no longer exists.")
    return _public(row)


def revoke_token(token: str) -> None:
    claims = _decode(token)
    with closing(_connect()) as conn, conn:
        conn.execute("INSERT OR IGNORE INTO revoked_tokens (jti, expires_at) VALUES (?, ?)",
                     (claims["jti"], int(claims["exp"])))
