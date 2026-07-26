"""
utils.py — small shared helpers used by more than one router.

now_utc() and fmt_ts() were originally defined once in bpr_api.py and used
by BOTH the BPR-record routes and the component-lot/hash routes. Since a
router split needs each side to be independently importable, these move
to their own tiny module instead of picking one router to "own" them (and
having the other import across sideways, which is a smell).
"""

import os
from datetime import datetime, timezone

import httpx

from config import LOCAL_TZ


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def fmt_ts(ts):
    """
    Formats a timestamp for display. DB values come back as naive UTC
    datetimes (or sometimes already a string, or None) -- this handles
    all three without the caller needing to check first.
    """
    if not ts:
        return None
    if isinstance(ts, str):
        return ts
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)   # naive DB values are UTC
    return ts.astimezone(LOCAL_TZ).strftime("%-m/%-d/%Y %-I:%M %p")


async def _post_wash_gas(payload: dict, label: str):
    """
    Shared fire-and-forget POST to the GAS doPost webhook.

    Lives here (not in a single router) on purpose: BOTH bpr.py and
    components.py write back to the wash BPR sheet, and this is the ONE
    place that stamps the shared secret onto every outgoing payload. That
    single-chokepoint property is what makes it safe to require the secret
    on the GAS side — if this injection lived in only one router, the other
    router's calls would silently fail auth the moment the gate is armed.

    Fire-and-forget by design: a Sheets/GAS hiccup must never block an
    operator mid-production, so every failure is caught and logged, never
    raised.
    """
    webhook_url = os.environ.get("GAS_WEBHOOK_URL")
    if not webhook_url:
        print(f"{label}: no GAS_WEBHOOK_URL — skipping")
        return
    payload["secret"] = os.environ.get("GAS_SHARED_SECRET", "")   # auth for doPost guard
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.post(webhook_url, json=payload)
            print(f"{label}: {resp.status_code} — {resp.text[:200]}")
    except Exception as e:
        print(f"{label} failed (non-fatal): {e}")
