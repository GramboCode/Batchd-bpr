"""
utils.py — small shared helpers used by more than one router.

now_utc() and fmt_ts() were originally defined once in bpr_api.py and used
by BOTH the BPR-record routes and the component-lot/hash routes. Since a
router split needs each side to be independently importable, these move
to their own tiny module instead of picking one router to "own" them (and
having the other import across sideways, which is a smell).
"""

import os
import time
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


def describe_exc(e: BaseException) -> str:
    """
    Render an exception in a form that's actually diagnosable in Railway logs.

    WHY THIS EXISTS: every GAS call site logged `f"...: {e}"`, and several of
    the exceptions that actually occur here — httpx.ReadTimeout,
    httpx.ConnectTimeout, httpx.ConnectError — carry an EMPTY message. So the
    logs read:

        wash release summary failed (non-fatal):

    ...with nothing after the colon. Every GAS write-back in production was
    failing and the log said nothing about why. The exception TYPE is the
    single most useful bit (timeout vs. DNS vs. TLS vs. protocol), and it was
    the one part being thrown away.

    Always includes the class name; appends the message only when non-empty.
    """
    msg = str(e).strip()
    name = type(e).__name__
    return f"{name}: {msg}" if msg else f"{name} (no message)"


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
    started = time.monotonic()
    try:
        # 45s, raised from 20s. An Apps Script web app that opens a Spreadsheet
        # or walks Drive folders routinely takes 5-15s, and a cold script
        # container adds more on top; measured round trips to this endpoint run
        # ~6s when everything is healthy. 20s left very little headroom, and a
        # timeout here is indistinguishable from a real failure to the operator.
        # Safe to be generous: this call is fire-and-forget, so nobody waits on it.
        async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client:
            resp = await client.post(webhook_url, json=payload)
            print(f"{label}: {resp.status_code} in {time.monotonic() - started:.1f}s "
                  f"— {resp.text[:200]}")
    except Exception as e:
        # Three things this line needs and previously had none of:
        #   action    — a burst of these is otherwise unattributable
        #   exc type  — see describe_exc; str(e) is EMPTY for httpx timeouts
        #   elapsed   — the tell that separates the two likely causes. Failing
        #               at ~the timeout value means GAS is too slow; failing in
        #               well under a second means we never connected (DNS,
        #               egress block, TLS) and no timeout bump will help.
        print(f"{label} failed (non-fatal) after {time.monotonic() - started:.1f}s "
              f"[action={payload.get('action')}]: {describe_exc(e)}")


async def bpr_sheet_exists(uid: str) -> tuple[bool, str]:
    """
    Ask GAS whether a real batch record sheet exists in Drive for `uid`.

    Returns (allowed, reason).

    THE BUG THIS EXISTS FOR
    -----------------------
    A METRC UID can be sitting in UID_TRACKER with a batch ID next to it and
    still have NO batch record sheet — that happens whenever someone assigns a
    UID by hand and doesn't run "Create Batch Records for Selected". Nothing in
    the app noticed. An operator could open that UID, sign off every phase, and
    release it, while every sheet write-back quietly returned "No BPR file
    found for UID" into a log nobody reads. The DB record looked complete; the
    physical record for that batch never existed.

    FAIL-OPEN ON UNCERTAINTY — AND WHY
    ----------------------------------
    We block ONLY on a definitive "no sheet" answer (checked=True, exists=False).
    A GAS timeout, a missing GAS_WEBHOOK_URL, a Drive outage, a non-JSON
    response — all of those return allowed=True.

    That asymmetry is the whole design. A false block halts a production line
    over an outage in a system that is not the source of truth; a false allow
    reproduces today's behavior, which is what we already live with. The DB
    stays the record of what happened either way, so an allow-on-error is
    recoverable and a block-on-error is not. Every fail-open path logs, so the
    "we couldn't check" cases stay visible rather than looking like passes.

    PRODUCTION NOTE: this adds a synchronous GAS round trip to BPR create and
    release. GAS cold starts can take several seconds, hence the 15s timeout —
    long enough to be a real check, short enough not to hang the UI. If that
    latency becomes a problem, cache per-UID results for the life of a shift;
    do NOT solve it by dropping the check at release, which is the one that
    matters most.
    """
    webhook_url = os.environ.get("GAS_WEBHOOK_URL")
    if not webhook_url:
        print(f"bpr_sheet_exists({uid}): no GAS_WEBHOOK_URL — allowing unchecked")
        return True, "guard skipped: GAS_WEBHOOK_URL not configured"

    payload = {
        "action": "bprSheetExists",
        "uid": uid,
        "secret": os.environ.get("GAS_SHARED_SECRET", ""),
    }

    started = time.monotonic()
    try:
        # Deliberately NOT raised to 45s like _post_wash_gas: an operator is
        # waiting on this one (it gates create + release), so a slow GAS should
        # fail open quickly rather than freeze the UI. 15s is the tradeoff.
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.post(webhook_url, json=payload)
            data = resp.json()
    except Exception as e:
        detail = describe_exc(e)
        print(f"bpr_sheet_exists({uid}): probe failed after "
              f"{time.monotonic() - started:.1f}s — allowing unchecked: {detail}")
        return True, f"guard skipped: {detail}"

    # GAS couldn't determine an answer (Drive error, archive folder unreachable).
    # Not the same as "no sheet" — don't treat it as one.
    if not data.get("checked"):
        reason = data.get("reason") or data.get("error") or "unknown"
        print(f"bpr_sheet_exists({uid}): indeterminate — allowing unchecked: {reason}")
        return True, f"guard indeterminate: {reason}"

    if data.get("exists"):
        return True, "batch record sheet found"

    # Definitive: GAS looked, and there is no batch record sheet for this UID.
    return False, data.get("reason") or "no batch record sheet found for this UID"


async def call_gas(payload: dict, label: str) -> dict:
    """
    Like _post_wash_gas, but RETURNS the GAS response JSON (secret stamped the
    same way). Use when the caller needs the result — e.g. the URL of a sheet
    GAS just created — rather than fire-and-forget. Never raises: returns
    {"success": False, "error": ...} on any failure so callers degrade cleanly.
    """
    webhook_url = os.environ.get("GAS_WEBHOOK_URL")
    if not webhook_url:
        return {"success": False, "error": "GAS_WEBHOOK_URL not configured"}
    payload["secret"] = os.environ.get("GAS_SHARED_SECRET", "")
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.post(webhook_url, json=payload)
            try:
                return resp.json()
            except Exception:
                return {"success": False,
                        "error": f"GAS non-JSON ({resp.status_code}): {resp.text[:200]}"}
    except Exception as e:
        detail = describe_exc(e)
        print(f"{label} failed (non-fatal) [action={payload.get('action')}]: {detail}")
        return {"success": False, "error": detail}
