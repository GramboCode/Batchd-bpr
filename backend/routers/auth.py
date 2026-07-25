"""
routers/auth.py — the login endpoint.

This is where the Google Sign-In flow described in auth.py actually
becomes an HTTP route the frontend can call.

Flow:
  1. Frontend's "Sign in with Google" button gives it a Google ID token.
  2. Frontend POSTs that token here: POST /auth/login { "google_token": "..." }
  3. We verify it's genuinely from Google and the email is allowed
     (auth.verify_google_id_token handles both checks).
  4. We issue our own short-lived JWT and hand it back.
  5. Frontend stores that JWT and sends it as
     `Authorization: Bearer <token>` on every future request.

GET /auth/me is a small convenience route — the frontend can call it on
page load to confirm a stored token is still valid (and get the role
back) without needing to decode the JWT itself client-side.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import (
    verify_google_id_token,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleLoginRequest(BaseModel):
    google_token: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    role: str
    expires_in_minutes: int


@router.post("/login", response_model=LoginResponse)
def login(req: GoogleLoginRequest):
    """
    Exchanges a verified Google ID token for our own access token.
    Raises 401 if the Google token is invalid/expired, 403 if the email
    isn't on the Workspace domain or the extra allowlist — both handled
    inside verify_google_id_token so this route stays a thin wrapper.
    """
    claims = verify_google_id_token(req.google_token)
    email = claims["email"]

    access_token = create_access_token(email)

    # Import here (not at module top) to avoid a circular import — auth.py
    # doesn't need to know about this router, but we need one of its
    # constants for the response. Cheap and standard pattern for this case.
    from config import JWT_EXPIRE_MINUTES
    from auth import role_for_email

    return LoginResponse(
        access_token=access_token,
        email=email,
        role=role_for_email(email),
        expires_in_minutes=JWT_EXPIRE_MINUTES,
    )


class MeResponse(BaseModel):
    email: str
    role: str


@router.get("/me", response_model=MeResponse)
def me(user: dict = Depends(get_current_user)):
    """
    Lets the frontend confirm "is my stored token still good, and who am
    I" without decoding the JWT client-side. Cheap health check for the
    login state — call this on app load before showing any protected UI.
    """
    return MeResponse(email=user["email"], role=user["role"])