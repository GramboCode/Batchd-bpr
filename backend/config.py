"""
config.py — shared environment variables and constants.

Single source of truth for every env var this service reads. Nothing in
this file talks to a database or the network — it's pure configuration,
so it's safe for every other module (db.py, auth.py, routers/*) to import
without creating circular-import headaches or accidental side effects.
"""

import os
from zoneinfo import ZoneInfo

# ── Environment variables ────────────────────────────────────────────────
# Fail loudly and immediately if something required is missing, rather
# than letting a route crash confusingly on its first real request.
def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"Required environment variable {name} is not set.")
    return val


def _optional_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


# Postgres (Railway) — required, service is useless without it
DATABASE_URL = _require_env("DATABASE_URL")

# Legacy shared-secret gate — kept alongside JWT during the transition.
# Existing clients (wash.html, BatchD frontend) send this header today;
# we don't break them the moment JWT auth lands.
BATCHD_API_KEY = _optional_env("BATCHD_API_KEY")

# GAS webhook — pinged on BPR completion (existing behavior, moved as-is)
GAS_WEBHOOK_URL = _optional_env("GAS_WEBHOOK_URL")

# Google service account JSON (raw string, not a file path) — used for
# both Drive PDF upload (existing) and the new Sheets API client.
GOOGLE_SERVICE_ACCOUNT = _optional_env("GOOGLE_SERVICE_ACCOUNT")

# Root COA Archive Drive folder — existing behavior, moved as-is
DRIVE_COA_FOLDER_ID = _optional_env("DRIVE_COA_FOLDER_ID")

# ── JWT settings (new) ───────────────────────────────────────────────────
# The secret that SIGNS our own short-lived tokens. This is NOT your Google
# credentials — it's a random string only this backend knows, used to prove
# a JWT was issued by us and hasn't been tampered with.
# Generate one with: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET = _require_env("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 48  # 48h — internal tool; was 60 (1h), which forced re-sign-in many times a day

# Google OAuth client ID — needed to verify Google ID tokens actually came
# from OUR frontend's Google Sign-In button (not just any Google login).
GOOGLE_OAUTH_CLIENT_ID = _optional_env("GOOGLE_OAUTH_CLIENT_ID")

# Allowed email domain for login — simplest correct check if everyone is
# on Google Workspace. Leave blank to fall back to an explicit allowlist
# instead (see auth.py).
ALLOWED_EMAIL_DOMAIN = _optional_env("ALLOWED_EMAIL_DOMAIN", "punchedibles.com")

# Admins — same list Config.gs's CONFIG.ADMINS holds today. Comma-separated
# in the env var so it can be edited on Railway without a code deploy.
ADMIN_EMAILS = {
    e.strip().lower()
    for e in _optional_env(
        "ADMIN_EMAILS",
        "darrayl@punchedibles.com,grayson@punchedibles.com,"
        "yoka@punchedibles.com,ismaelramirez@punchedibles.com",
    ).split(",")
    if e.strip()
}
# Explicit allowlist for people WITHOUT a @punchedibles.com Workspace
# account (e.g. contractors, or staff in a new state before their
# Workspace account is provisioned). Comma-separated in Railway so this
# never needs a code deploy to update. Starts empty — add entries as
# non-Workspace users come on board.
EXTRA_ALLOWED_EMAILS = {
    e.strip().lower()
    for e in _optional_env("EXTRA_ALLOWED_EMAILS", "").split(",")
    if e.strip()
}

# ── Sheets (Punch Tools / UID_TRACKER) ───────────────────────────────────
TRACKER_SS_ID = "1yNldRwg8E0paStewgW82ZGouIRqE9S9XKYdfEPmOEqU"
TRACKER_TAB = "UID"
DATA_START_ROW = 4

# ── Shared timezone ───────────────────────────────────────────────────────
# Railway/Postgres stores everything in UTC; every place that displays a
# timestamp to a human converts to this at the last possible moment.
LOCAL_TZ = ZoneInfo("America/Los_Angeles")

# ── CORS ──────────────────────────────────────────────────────────────────
# Centralized here so main.py, and any future service, reads from one list
# instead of the origins list drifting between files over time.
CORS_ALLOWED_ORIGINS = [
    "https://batchd-bpr.netlify.app",
    "http://localhost:5173",
]
CORS_ALLOWED_ORIGIN_REGEX = r"https://.*\.googleusercontent\.com"