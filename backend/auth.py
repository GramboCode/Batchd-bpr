"""
auth.py — authentication and authorization for the whole backend.

Two systems coexist here during the migration:

1. LEGACY API KEY — the X-API-Key header check that already exists in
   bpr_api.py today. wash.html and the BatchD frontend already send this
   header on every request. Moved here unchanged so nothing breaks while
   the frontend is migrated to JWT one page at a time.

2. JWT (new) — per-user tokens issued after verifying a Google Sign-In
   ID token. This is what every NEW route (tracker.py, and eventually the
   BPR/components routes) should require instead of the shared API key,
   since it tells us WHO did something, not just THAT a valid key was used.

How the login flow works end to end:
  1. Frontend shows a "Sign in with Google" button (Google Identity
     Services JS library — no password UI of ours involved).
  2. Google hands the frontend a signed ID token proving "this really is
     person@domain.com, verified by Google."
  3. Frontend POSTs that ID token to POST /auth/login (route lives in
     routers/auth.py, added when we build main.py).
  4. This file verifies the Google token's signature, checks the email is
     allowed (Workspace domain OR explicit allowlist), then issues OUR
     OWN short-lived JWT back to the frontend.
  5. Frontend attaches that JWT as `Authorization: Bearer <token>` on every
     subsequent request. Verifying it here is fast and local (no network
     call to Google needed) until it expires and step 1-4 repeats.
"""

import time
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from config import (
    BATCHD_API_KEY,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRE_MINUTES,
    GOOGLE_OAUTH_CLIENT_ID,
    ALLOWED_EMAIL_DOMAIN,
    ADMIN_EMAILS,
    EXTRA_ALLOWED_EMAILS,
)

# Reused across requests — this object just holds an HTTP session
# internally for talking to Google's public-key endpoint, safe to share.
_google_auth_request = google_requests.Request()

# FastAPI's helper for reading "Authorization: Bearer <token>" headers.
# auto_error=False means a MISSING header doesn't immediately 403 — we
# want to produce our own clearer error message instead.
_bearer_scheme = HTTPBearer(auto_error=False)


# ═══════════════════════════════════════════════════════════════════════
# LEGACY API KEY MIDDLEWARE — moved from bpr_api.py, logic unchanged.
# main.py attaches this with: app.middleware("http")(require_api_key)
# ═══════════════════════════════════════════════════════════════════════

async def require_api_key(request: Request, call_next):
    if request.method == "OPTIONS" or request.url.path in (
        "/health", "/bpr/health", "/auth/login",
    ):
        return await call_next(request)
    if not BATCHD_API_KEY:
        print("WARNING: BATCHD_API_KEY not set — API is OPEN")
        return await call_next(request)

    # NEW: a valid JWT also satisfies this middleware, so routes migrated
    # to JWT-only auth don't ALSO need to carry the legacy header. Old
    # clients keep sending X-API-Key; new clients send Authorization:
    # Bearer instead. Either one gets past this checkpoint.
    if request.headers.get("X-API-Key") == BATCHD_API_KEY:
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            decode_access_token(auth_header[len("Bearer "):])
            return await call_next(request)
        except Exception:
            pass  # fall through to the 401 below

    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=401, content={"detail": "Invalid or missing credentials"})


# ═══════════════════════════════════════════════════════════════════════
# EMAIL AUTHORIZATION — who's allowed to use the app at all.
# ═══════════════════════════════════════════════════════════════════════

def is_allowed_email(email: str) -> bool:
    """
    True if this person is allowed to log in: either their email is on
    our Workspace domain, or they're explicitly allowlisted (the growing
    non-Workspace group as we expand into new states).
    """
    email = email.strip().lower()
    if ALLOWED_EMAIL_DOMAIN and email.endswith("@" + ALLOWED_EMAIL_DOMAIN):
        return True
    return email in EXTRA_ALLOWED_EMAILS


def role_for_email(email: str) -> str:
    """Admins get the 'admin' role claim; everyone else gets 'user'."""
    return "admin" if email.strip().lower() in ADMIN_EMAILS else "user"


# ═══════════════════════════════════════════════════════════════════════
# GOOGLE ID TOKEN VERIFICATION — step 4 of the login flow above.
# ═══════════════════════════════════════════════════════════════════════

def verify_google_id_token(google_token: str) -> dict:
    """
    Confirms a Google ID token is genuine (signed by Google, issued for
    OUR app's client ID, not expired) and returns the verified claims.
    Raises HTTPException(401) on anything wrong — bad signature, wrong
    audience, expired token, etc. This is the ONLY place we trust an
    email address without our own JWT backing it.
    """
    if not GOOGLE_OAUTH_CLIENT_ID:
        raise HTTPException(500, "GOOGLE_OAUTH_CLIENT_ID not configured on the server")

    try:
        claims = google_id_token.verify_oauth2_token(
            google_token, _google_auth_request, GOOGLE_OAUTH_CLIENT_ID
        )
    except ValueError as e:
        raise HTTPException(401, f"Invalid Google token: {e}")

    email = claims.get("email", "")
    if not claims.get("email_verified"):
        raise HTTPException(401, "Google account email is not verified")
    if not is_allowed_email(email):
        raise HTTPException(
            403,
            f"{email} is not authorized. Contact an admin to be added to the allowlist.",
        )

    return claims


# ═══════════════════════════════════════════════════════════════════════
# OUR JWT — issued after a successful Google verification, checked on
# every request afterward without needing to call Google again.
# ═══════════════════════════════════════════════════════════════════════

def create_access_token(email: str) -> str:
    """
    Builds our own short-lived, signed token. `role` rides along inside
    it so every route can check permissions without a database lookup —
    that's the whole point of a JWT versus a plain session ID.
    """
    now = int(time.time())
    payload = {
        "sub": email.strip().lower(),   # "subject" — standard JWT field for "who"
        "role": role_for_email(email),
        "iat": now,                      # issued-at
        "exp": now + JWT_EXPIRE_MINUTES * 60,  # expiry
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Verifies our own JWT's signature and expiry. Raises jwt.PyJWTError
    subclasses on anything wrong (ExpiredSignatureError, InvalidSignatureError,
    etc.) — callers should catch broadly or let it surface as a 401.
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


# ═══════════════════════════════════════════════════════════════════════
# FASTAPI DEPENDENCIES — plug these into route signatures to require auth.
# Usage:  def my_route(user: dict = Depends(get_current_user)): ...
# ═══════════════════════════════════════════════════════════════════════

def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> dict:
    """
    Pulls the caller's identity out of their JWT. Use this on any route
    that needs to know WHO is calling (audit trails, "performed_by"
    fields, per-user behavior) — not just THAT they're allowed through
    (the middleware above already gates that).
    """
    if creds is None:
        raise HTTPException(401, "Missing Authorization header")
    try:
        payload = decode_access_token(creds.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expired — please sign in again")
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid session token")

    return {"email": payload["sub"], "role": payload["role"]}


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """
    Stricter dependency for admin-only routes (template management, lab
    list editing — the same surface _isAdmin() in WebApp.gs guards today).
    """
    if user["role"] != "admin":
        raise HTTPException(403, "Admin access required")
    return user