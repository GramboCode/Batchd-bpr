"""
routers/tracker.py — Punch Tools endpoints backed by UID_TRACKER.

This is the FastAPI equivalent of WebApp.gs's serverGet* functions. The
guiding rule for this whole file: each endpoint returns the SAME JSON
shape its google.script.run counterpart returned, so rewriting the
frontend is a matter of swapping HOW it calls (fetch vs google.script.run)
without rewriting what it does with the response.

Reads:
  GET   /tracker/dashboard   <- serverGetDashboard
  GET   /tracker/batch/{uid} <- serverGetBatch
  GET   /tracker/search      <- serverSearch

Writes (this file's first write endpoint):
  PATCH /tracker/batch/{uid} <- serverUpdateBatchInfo / serverUpdateLab
                                (direct sheet writes) + serverUpdateStatus
                                (routed through the GAS webhook so its side
                                effects still run — see _gas_set_batch_status).

Still on GAS: batch creation and tag imports.
"""

import os
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
import httpx

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


@router.get("/check-batch-id")
def check_batch_id(
    batch_id: str = Query(..., alias="batchId"),
    user: dict = Depends(get_current_user),
):
    """
    Port of serverCheckBatchID (confirmed against WebApp.gs). Returns the
    {available, assignedTo, suggestion} shape renderBatchIDStatus()
    expects — all three keys always present, null where GAS's version
    would also send null.
    """
    try:
        client = get_sheets_client()
        return client.check_batch_id_availability(batch_id)
    except Exception as e:
        return {"available": None, "assignedTo": None, "suggestion": None, "error": str(e)}


@router.get("/search-batch-prefix")
def search_batch_prefix(
    prefix: str = Query(...),
    user: dict = Depends(get_current_user),
):
    """
    Port of serverSearchBatchPrefix (confirmed against WebApp.gs).
    Returns the {matches: [...]} shape renderPrefixDropdown() expects.
    """
    try:
        client = get_sheets_client()
        matches = client.search_batch_prefix(prefix)
        return {"matches": matches}
    except Exception as e:
        return {"matches": [], "error": str(e)}


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


# ── WRITE PATH — batch-detail editable fields ──────────────────────────────
# First write endpoint in this file. Field edits (lab/target_qty/quantity/
# mfg_date) write straight to UID_TRACKER; a status change routes through the
# GAS webhook so updateBatchStatus's side effects still run (see the note on
# the status branch below). Every field is optional — the frontend sends only
# what changed, so a lab-only save doesn't touch quantity, etc.

class BatchUpdate(BaseModel):
    status: Optional[str] = None
    lab: Optional[str] = None
    target_qty: Optional[str] = None
    quantity: Optional[str] = None
    mfg_date: Optional[str] = None
    lab_sample_id_rnd: Optional[str] = None
    lab_sample_id_coa: Optional[str] = None


async def _gas_post(action: str, fields: dict) -> dict:
    """
    POSTs an action to the GAS webhook (doPost) and returns its JSON result.
    Used for every operation that must run inside GAS to preserve side effects
    the backend can't replicate — status changes (updateBatchStatus) and testing
    pushes (serverPushToTestingOrder / serverRemoveTestingSubmission, which write
    a separate testing-order sheet + the Distro Log). Stamps the shared secret so
    it clears the doPost gate; returns {success: false, error} if the webhook is
    unreachable or returns non-JSON.
    """
    webhook_url = os.environ.get("GAS_WEBHOOK_URL")
    if not webhook_url:
        return {"success": False, "error": "GAS_WEBHOOK_URL not configured"}

    payload = {"action": action, "secret": os.environ.get("GAS_SHARED_SECRET", ""), **fields}
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.post(webhook_url, json=payload)
            try:
                return resp.json()
            except Exception:
                return {
                    "success": False,
                    "error": f"GAS returned non-JSON ({resp.status_code}): {resp.text[:200]}",
                }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.patch("/batch/{uid}")
async def update_batch(
    uid: str,
    body: BatchUpdate,
    user: dict = Depends(get_current_user),
):
    """
    Port of the batch-detail edits (serverUpdateBatchInfo / serverUpdateLab /
    serverUpdateStatus). Returns the same {success, batch} shape get_batch
    does, so the frontend can drop the fresh batch straight back into state.
    """
    try:
        client = get_sheets_client()

        # ── Plain field edits — direct sheet write, no side effects ──
        field_updates = {
            k: v for k, v in {
                "lab":               body.lab,
                "target_qty":        body.target_qty,
                "quantity":          body.quantity,
                "mfg_date":          body.mfg_date,
                "lab_sample_id_rnd": body.lab_sample_id_rnd,
                "lab_sample_id_coa": body.lab_sample_id_coa,
            }.items() if v is not None
        }
        if field_updates:
            if not client.update_batch_fields(uid, field_updates):
                return {"success": False, "error": f"Batch not found: {uid}"}

        # ── Status change — routed through GAS (per the side-effect note) ──
        if body.status is not None:
            if body.status not in STATUS_LIST:
                return {"success": False, "error": f"Invalid status: {body.status}"}
            gas_result = await _gas_post("setBatchStatus", {"uid": uid, "status": body.status})
            if not gas_result.get("success"):
                return {
                    "success": False,
                    "error": gas_result.get("error", "GAS status update failed"),
                }

        # Read back the row so the client re-renders from the source of truth
        # (GAS wrote the status synchronously above, so it's already reflected).
        batch = client.get_batch_by_uid(uid)
        if not batch:
            return {"success": False, "error": f"Batch not found: {uid}"}
        return {"success": True, "batch": batch}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ── TESTING PUSH — delegated to GAS ────────────────────────────────────────
# serverPushToTestingOrder / serverRemoveTestingSubmission live in a GAS file
# (they write a separate testing-order sheet + the Distro Log), so these
# endpoints just relay to the webhook rather than reimplement that logic. Both
# read the batch back afterward so the client re-renders with the new status.

class PushTestingRequest(BaseModel):
    push_type: str                        # "RND" | "COMPLIANCE"
    date: str                             # submission date (yyyy-mm-dd)
    sample_size: Optional[str] = None     # units sent to lab, or None
    rnd_type: Optional[str] = None        # R&D test type (RND only); GAS uses 'Compliance' otherwise


@router.post("/batch/{uid}/push-testing")
async def push_testing(
    uid: str,
    body: PushTestingRequest,
    user: dict = Depends(get_current_user),
):
    """
    Relays to GAS serverPushToTestingOrder(uid, pushType, date, sampleSize,
    rndType). GAS requires the batch to already have a lab assigned; if it
    doesn't, GAS returns {success:false, error}, which we surface as-is.
    """
    try:
        gas = await _gas_post("pushToTestingOrder", {
            "uid":        uid,
            "pushType":   body.push_type,
            "date":       body.date,
            "sampleSize": body.sample_size,
            "rndType":    body.rnd_type or "Compliance",
        })
        if not gas.get("success"):
            return {"success": False, "error": gas.get("error", "Push to testing failed")}

        batch = get_sheets_client().get_batch_by_uid(uid)
        return {
            "success": True,
            "batch": batch,
            "newStatus": gas.get("newStatus"),
            "tabName": gas.get("tabName"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/batch/{uid}/remove-testing")
async def remove_testing(uid: str, user: dict = Depends(get_current_user)):
    """
    Relays to GAS serverRemoveTestingSubmission(uid): removes the batch from the
    testing order sheet and reverts status to In Production.
    """
    try:
        gas = await _gas_post("removeTestingSubmission", {"uid": uid})
        if not gas.get("success"):
            return {"success": False, "error": gas.get("error", "Remove testing failed")}

        batch = get_sheets_client().get_batch_by_uid(uid)
        return {"success": True, "batch": batch}
    except Exception as e:
        return {"success": False, "error": str(e)}