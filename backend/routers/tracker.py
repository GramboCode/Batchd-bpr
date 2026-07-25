"""
routers/tracker.py — Punch Tools endpoints backed by UID_TRACKER.

This is the FastAPI equivalent of WebApp.gs's serverGet* functions. The
guiding rule for this whole file: each endpoint returns the SAME JSON
shape its google.script.run counterpart returned, so rewriting the
frontend is a matter of swapping HOW it calls (fetch vs google.script.run)
without rewriting what it does with the response.

This first slice is READ-ONLY on purpose:
  GET /tracker/dashboard   <- serverGetDashboard
  GET /tracker/batch/{uid} <- serverGetBatch
  GET /tracker/search      <- serverSearch

Writes (status updates, batch creation, imports) come in a later pass,
once the read path is proven end-to-end against the real dashboard.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from auth import get_current_user
from sheets_client import get_sheets_client, INACTIVE_STATUSES

router = APIRouter(prefix="/tracker", tags=["tracker"])


# ── Stat-card groupings — mirrors serverGetDashboard's inline status sets ──
# These are the SAME status strings the GAS dashboard grouped by. Kept as
# lowercase sets so the comparison is case-insensitive without repeated
# .lower() calls in the loop.
STAT_GROUPS = {
    "inProduction": {
        "in production", "ready for packaging", "packaging complete",
        "submitted for rnd", "passed rnd", "remake",
    },
    "needLabels": {"need labels", "labels made"},
    "readyForTesting": {"ready for testing"},
    "awaitingResults": {
        "submitted for compliance", "delayed in testing",
        "testing cancelled", "compliance review",
    },
}

# The full ordered status list the frontend's filter dropdown expects —
# same order as CONFIG.STATUS_LIST in Config.gs.
STATUS_LIST = [
    "In Production", "Ready for Packaging", "Packaging Complete",
    "Submitted for RND", "Passed RND", "Remake",
    "Need Labels", "Labels Made", "Ready for Testing",
    "Submitted for Compliance", "Delayed in Testing", "Testing Cancelled",
    "Compliance Passed", "Failed", "Compliance Review",
    "Passed BUT NOT Avail in Distru", "Avail in Distru/On Menu", "Archived",
]

# Labs — same default list as CONFIG.LABS. In GAS this could be overridden
# via PropertiesService; that admin-managed override will move to Postgres
# or an env var in a later pass. For now the static default matches what
# the dashboard shipped with.
LABS = ["Encore", "Infinite", "Landau"]


def _count_unassigned() -> int:
    """
    Counts rows that have a METRC UID but NO batch ID yet — the pool of
    imported-but-not-yet-used tags. serverGetDashboard did this as a
    separate lightweight pass; here we derive it from the same raw pull
    get_batches() already made, to avoid a second Sheets API round trip.
    """
    client = get_sheets_client()
    rows = client.get_all_rows()
    from sheets_client import COL, _pad_row  # local import: internal helpers

    count = 0
    for row in rows:
        row = _pad_row(row, COL["BATCH_ID"])
        uid = str(row[COL["METRC_UID"] - 1] or "").strip()
        batch_id = str(row[COL["BATCH_ID"] - 1] or "").strip()
        if uid and not batch_id:
            count += 1
    return count


@router.get("/dashboard")
def get_dashboard(user: dict = Depends(get_current_user)):
    """
    Port of serverGetDashboard. Returns active batches + stat-card counts
    + failed-batch list + dropdown option lists, in the exact shape
    index.html's onDashboardLoaded() reads.

    Requires a valid JWT (Depends(get_current_user)) — the dashboard is
    not public. Every read endpoint in this file is gated the same way.
    """
    try:
        client = get_sheets_client()
        all_batches = client.get_batches()

        stats = {
            "inProduction": 0,
            "needLabels": 0,
            "readyForTesting": 0,
            "awaitingResults": 0,
            "failed": 0,
            "unassignedUIDs": _count_unassigned(),
        }

        failed_batches = []
        active_batches = []

        for b in all_batches:
            s = b["status"].lower().strip()

            # Tally stat cards — same buckets as serverGetDashboard
            if s in STAT_GROUPS["inProduction"]:
                stats["inProduction"] += 1
            elif s in STAT_GROUPS["needLabels"]:
                stats["needLabels"] += 1
            elif s in STAT_GROUPS["readyForTesting"]:
                stats["readyForTesting"] += 1
            elif s in STAT_GROUPS["awaitingResults"]:
                stats["awaitingResults"] += 1
            elif s == "failed":
                stats["failed"] += 1
                failed_batches.append({
                    "batchID": b["batchID"],
                    "item": b["item"],
                    "metrcUID": b["metrcUID"],
                })

            # Only ship active batches to the browser — the 264-vs-5653
            # filter that keeps the dashboard fast.
            if s not in INACTIVE_STATUSES:
                active_batches.append(b)

        return {
            "success": True,
            "batches": active_batches,
            "stats": stats,
            "failedBatches": failed_batches,
            "statuses": STATUS_LIST,
            "labs": LABS,
        }

    except Exception as e:
        # Match the GAS convention: return {success: false, error} rather
        # than a raw 500, since the frontend's onDashboardLoaded checks
        # result.success and shows a retry on failure.
        return {"success": False, "error": str(e)}


@router.get("/batch/{uid}")
def get_batch(uid: str, user: dict = Depends(get_current_user)):
    """
    Port of serverGetBatch. Single batch by METRC UID, same response
    shape ({success, batch} or {success:false, error}) batch.html's
    onBatchLoaded() expects.
    """
    try:
        client = get_sheets_client()
        batch = client.get_batch_by_uid(uid)
        if not batch:
            return {"success": False, "error": f"Batch not found: {uid}"}
        return {"success": True, "batch": batch}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/next-uid")
def get_next_uid(user: dict = Depends(get_current_user)):
    """
    Port of serverGetNextUID. Returns the next unassigned METRC tag in
    consumption order (oldest-imported first, per get_next_available_uid's
    bottom-up scan).

    IMPORTANT — this is a PREVIEW only, not a reservation. It doesn't
    lock or mark anything; two people opening the New Batch page at the
    same moment will see the same "next" tag. That's fine as long as the
    actual create-batch write re-runs this same lookup at commit time
    (matching createBatch()'s behavior in Batches.gs, which calls
    getNextAvailableUID() itself rather than trusting a client-supplied
    UID) — whichever request commits first gets that tag, the second
    naturally gets the next one down the list. If the future create
    endpoint ever accepts a UID from the client instead of re-deriving
    it server-side, that guarantee breaks and two people could collide
    on the same tag.
    """
    try:
        client = get_sheets_client()
        next_uid = client.get_next_available_uid()
        if not next_uid:
            return {
                "success": False,
                "error": "No available METRC UIDs. Please import new tags before creating a batch.",
            }
        return {"success": True, "uid": next_uid["uid"]}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/templates")
def get_templates(user: dict = Depends(get_current_user)):
    """
    Port of serverGetTemplates. Templates now live in the Product Catalog
    tab (see migrate_templates.gs) instead of GAS's PropertiesService —
    same {success, templates, labs} shape either way, so create.html's
    port needs no changes to how it reads the response, only how it
    fetches it.
    """
    try:
        client = get_sheets_client()
        templates = client.get_product_templates()
        return {"success": True, "templates": templates, "labs": LABS}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/search")
def search(
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    lab: Optional[str] = Query(None),
    active_only: bool = Query(True),
    user: dict = Depends(get_current_user),
):
    """
    Port of serverSearch. Text query across item/batchID/UID/category,
    plus optional status/lab/active-only filters. Same {success, batches,
    count} shape the frontend's runSearch() reads.

    Note: GAS did text search server-side because google.script.run was
    the only channel. Here it's the same idea — the server filters the
    full set so the browser doesn't have to hold all 5,653 rows just to
    search history. Empty query + active_only is the common case and
    stays cheap.
    """
    try:
        client = get_sheets_client()
        batches = client.get_batches()

        if q and q.strip():
            needle = q.strip().lower()
            batches = [
                b for b in batches
                if needle in b["item"].lower()
                or needle in b["batchID"].lower()
                or needle in b["metrcUID"].lower()
                or needle in b["category"].lower()
            ]

        if status:
            batches = [b for b in batches if b["status"].lower() == status.lower()]

        if lab:
            batches = [b for b in batches if b["lab"].lower() == lab.lower()]

        if active_only:
            batches = [
                b for b in batches
                if b["status"].lower().strip() not in INACTIVE_STATUSES
            ]

        # GAS returned newest-first (batches.reverse()). Sheet order is
        # oldest-first, so reverse to match what the dashboard shows.
        batches.reverse()

        return {"success": True, "batches": batches, "count": len(batches)}

    except Exception as e:
        return {"success": False, "error": str(e)}