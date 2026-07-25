"""
main.py — application entry point.

This is what Railway actually runs (e.g. `uvicorn main:app`). Its job is
narrow on purpose: build the FastAPI app, wire up CORS, attach the auth
middleware, run schema init on startup, and mount every router. All real
logic lives in the router files and the shared modules (auth.py, db.py,
sheets_client.py) -- main.py should stay small and boring forever, even
as more routers get added.

Replaces bpr_api.py's app = FastAPI(...) + CORS block + startup event +
require_api_key middleware, all of which are now imported from their new
homes instead of defined inline.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ALLOWED_ORIGINS, CORS_ALLOWED_ORIGIN_REGEX
from db import init_schema
from auth import require_api_key

from routers import auth as auth_router
from routers import components as components_router
from routers import bpr as bpr_router
# NOTE: tracker.py doesn't exist yet -- built next, on top of
# sheets_client.py. Uncomment both lines below once it lands:
from routers import tracker as tracker_router

app = FastAPI(title="BatchD API", version="3.0.0")

# ── CORS ──────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_origin_regex=CORS_ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth gate — every request passes through this before reaching a route ─
app.middleware("http")(require_api_key)


# ── Health check — kept at both paths for compatibility with anything
#    (uptime monitors, GAS pings) still hitting the old /bpr/health ──────
@app.get("/health")
@app.get("/bpr/health")
def health():
    return {"status": "ok", "service": "BatchD API", "version": "3.0.0"}


# ── Schema init on boot — replaces bpr_api.py's @app.on_event("startup") ──
@app.on_event("startup")
async def startup():
    init_schema()


# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(auth_router.router)
app.include_router(components_router.router)
app.include_router(bpr_router.router)
app.include_router(tracker_router.router)
