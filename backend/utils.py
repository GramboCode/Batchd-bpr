"""
utils.py — small shared helpers used by more than one router.

now_utc() and fmt_ts() were originally defined once in bpr_api.py and used
by BOTH the BPR-record routes and the component-lot/hash routes. Since a
router split needs each side to be independently importable, these move
to their own tiny module instead of picking one router to "own" them (and
having the other import across sideways, which is a smell).
"""

from datetime import datetime, timezone

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
