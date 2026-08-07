"""
routers/bpr.py — BPR record lifecycle: /bpr/*.

Moved from bpr_api.py. Same mechanical-split rule as components.py: every
function body and SQL string below is identical to what was already
running. Only the decorators (@app. -> @router.) and where get_db/
now_utc/fmt_ts/BPR_PHASES come from have changed.

This file owns bpr_records / bpr_phase_signoffs / bpr_step_checks --
the digital Batch Production Record itself (phases, step checks,
supervisor signoff, release). It does reach into bpr_component_lots
directly in a few places (_get_wash_sheet_url, _wash_block_stats) when a
BPR phase needs to pull in wash-session data for a hash lot -- that's a
read against the same tables components.py also touches, not a call
into components.py's functions, so there's no circular import here.
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import httpx

from db import get_db
from utils import now_utc, fmt_ts, _post_wash_gas, bpr_sheet_exists, describe_exc
from bpr_phases import BPR_PHASES, detect_product_family
# Component ledger helpers — reused so a BPR consuming a component lot decrements
# inventory through the exact same ledger path the components router uses.
# (components.py does NOT import bpr, so this import introduces no cycle.)
from routers.components import (
    get_lot as _get_component_lot,
    lot_balance as _lot_balance,
    add_transaction as _add_transaction,
    get_component_type as _get_component_type,
    workflow_keys as _workflow_keys,
    SanitationLogRequest,   # reused so the sanitation UI can serve wash + cell-mapped BPRs
)

router = APIRouter(tags=["bpr"])


# ═══════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════════

class BPRCreateRequest(BaseModel):
    uid: str                             
    product_name: str
    batch_id: Optional[str] = None
    mfg_date: Optional[str] = None
    category: Optional[str] = None
    bpr_type: Optional[str] = None
    metrc_uid: Optional[str] = None      

class StepCheckRequest(BaseModel):
    phase_id: str
    step_index: int
    checked: bool
    checked_by: str

class PhaseSignoffRequest(BaseModel):
    phase_id: str
    employee_name: str
    notes: Optional[str] = None
    ccp_values: Optional[dict] = None

class ConsumeComponentRequest(BaseModel):
    lot_code: str
    weight_g: float
    recorded_by: Optional[str] = None

class SupervisorReleaseRequest(BaseModel):
    supervisor_name: str
    deviation_notes: Optional[str] = None
    total_yield: Optional[str] = None

class EquipmentCheckEntry(BaseModel):
    row: int                          # Section 4 equipment row 1-9, matching the sheet
    checked_by: Optional[str] = None  # operator who verified this specific equipment
    time: Optional[str] = None        # "08:00" — defaults to server time if omitted

class EquipmentCheckRequest(BaseModel):
    entries: List[EquipmentCheckEntry]



# ═══════════════════════════════════════════════════════════════════════
# ROUTES + INLINE HELPERS  (find_existing_bpr, _get_wash_sheet_url,
# _post_wash_gas, _wash_block_stats all live in this range in the
# original file, interspersed with the routes that call them)
# ═══════════════════════════════════════════════════════════════════════

@router.get("/bpr/phases")
def get_all_phases():
    return {"families": BPR_PHASES}

# ─────────────────────────────────────────────────────────────────────────
# GET /bpr/phases/{family}
# ─────────────────────────────────────────────────────────────────────────
@router.get("/bpr/phases/{family}")
def get_phases(family: str):
    if family not in BPR_PHASES:
        raise HTTPException(404, f"No BPR template found for product family: {family}")
    return {"family": family, "definition": BPR_PHASES[family]}

def find_existing_bpr(cur, uid: str, metrc_uid: Optional[str] = None):
    """
    Resolve a BPR. `uid` is the lot code — the primary, unique key — and is
    tried first. `metrc_uid` is the source METRC tag, which is deliberately
    NON-unique: one tag can cover several wash lots (confirmed in production
    data — some tags map to 9 different hash lots), so it can never be a
    primary key. It's a fallback for callers that only know the tag, and
    returns the OLDEST match to stay deterministic when a tag is ambiguous.
    """
    cur.execute("SELECT * FROM bpr_records WHERE uid = %s", (uid,))
    row = cur.fetchone()
    if row:
        return row

    mu = (metrc_uid or "").strip()
    if mu:
        cur.execute(
            "SELECT * FROM bpr_records WHERE metrc_uid = %s ORDER BY created_at ASC LIMIT 1",
            (mu,)
        )
        return cur.fetchone()
    return None



# ─────────────────────────────────────────────────────────────────────────
# POST /bpr/create
# Initializes a BPR record. Idempotent — returns existing if UID already has one.
# NEW in v2.0: writes the BPR id back onto the component lot (wash_bpr_id fix)
# ─────────────────────────────────────────────────────────────────────────
@router.post("/bpr/create")
async def create_bpr(req: BPRCreateRequest):
    family = detect_product_family(req.product_name, req.category or "", req.bpr_type or "")
    if not family:
        raise HTTPException(400, f"Could not detect product family for: {req.product_name}")

    conn = get_db()
    try:
        with conn.cursor() as cur:
            existing = find_existing_bpr(cur, req.uid, req.metrc_uid)
            if existing:
                return {
                    "created": False,
                    "bpr": dict(existing),
                    "phases": BPR_PHASES[existing["product_family"]],
                    "message": "BPR already exists for this batch"
                }

            # ── PRECONDITION: a physical batch record must exist ─────────
            # Checked here, at create, so an operator finds out BEFORE doing
            # the work rather than after. Without this, a UID that was
            # hand-assigned in the tracker but never run through "Create Batch
            # Records" would produce a fully-filled BPR whose every sheet
            # write-back silently no-ops (getBPRFileForUID returns null and
            # each writer bails). See bpr_sheet_exists() for the fail-open
            # rules — an unreachable GAS never blocks production.
            #
            # rosin_wash is exempt on purpose, and this is NOT an oversight:
            # createWashBatchRecord() files the wash sheet into a folder named
            # for the METRC tag, while a wash BPR's `uid` is the HASH LOT ID.
            # Probing by uid would therefore find nothing and block every wash
            # BPR. Wash has its own existence signal already — the lot's
            # sheet_url, which _get_wash_sheet_url() checks before each write.
            if family != "rosin_wash":
                allowed, reason = await bpr_sheet_exists(req.uid)
                if not allowed:
                    raise HTTPException(409, {
                        "message": (
                            "No batch record exists for this UID yet, so nothing "
                            "entered here could be saved to it. Create the batch "
                            "record first (Punch Tools → Create Batch Records for "
                            "Selected), then reopen this BPR."
                        ),
                        "uid": req.uid,
                        "batch_id": req.batch_id,
                        "reason": reason,
                        "code": "no_batch_record_sheet",
                    })

            cur.execute("""
                INSERT INTO bpr_records
                    (uid, product_name, batch_id, mfg_date, category, product_family, metrc_uid)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (req.uid, req.product_name, req.batch_id, req.mfg_date,
                  req.category, family, req.metrc_uid or None))
            record = dict(cur.fetchone())

            definition = BPR_PHASES[family]
            for phase in definition["phases"]:
                for i, _ in enumerate(phase["steps"]):
                    cur.execute("""
                        INSERT INTO bpr_step_checks (bpr_id, uid, phase_id, step_index)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (record["id"], req.uid, phase["id"], i))

            # uid IS the lot code in this model, so matching on it directly
            # is correct again — no more juggling a separate lookup value.
            cur.execute("""
                UPDATE bpr_component_lots
                SET type_data = type_data || %s::jsonb, updated_at = NOW()
                WHERE lot_code = %s
            """, (json.dumps({"wash_bpr_id": str(record["id"])}), req.uid))

        conn.commit()
        return {
            "created": True,
            "bpr": record,
            "phases": BPR_PHASES[family],
            "message": f"BPR created for {req.product_name}"
        }
    finally:
        conn.close()

# ─────────────────────────────────────────────────────────────────────────
# GET /bpr/{uid}
# ─────────────────────────────────────────────────────────────────────────
@router.get("/bpr/{uid}")
def get_bpr(uid: str, metrc_uid: Optional[str] = Query(None)):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            record = find_existing_bpr(cur, uid, metrc_uid)
            if not record:
                raise HTTPException(404, "No BPR found for this batch UID")
            record = dict(record)

            # ── The critical line ──────────────────────────────────────
            # Every child query keys off the RESOLVED record's uid. Using the
            # path param here would return the correct header with zero step
            # checks whenever the caller arrived by lot code — a blank-looking
            # BPR sitting on top of fully populated data. That failure is
            # silent: no error, no 404, just unchecked boxes.
            ruid = record["uid"]

            cur.execute(
                "SELECT * FROM bpr_phase_signoffs WHERE uid = %s ORDER BY signed_at",
                (ruid,)
            )
            signoffs = [dict(r) for r in cur.fetchall()]

            cur.execute(
                "SELECT * FROM bpr_step_checks WHERE uid = %s ORDER BY phase_id, step_index",
                (ruid,)
            )
            steps = [dict(r) for r in cur.fetchall()]

            family = record["product_family"]
            definition = BPR_PHASES.get(family, {})

            # Component consumption: which component type (if any) this family
            # draws down, plus whatever lots have already been recorded.
            consumes_component = FAMILY_CONSUMES_COMPONENT.get(family)
            cur.execute(
                "SELECT * FROM bpr_component_consumption WHERE bpr_uid = %s ORDER BY created_at",
                (ruid,)
            )
            consumed_components = [dict(r) for r in cur.fetchall()]

            signoff_map = {s["phase_id"]: s for s in signoffs}

            step_map = {}
            for s in steps:
                key = f"{s['phase_id']}:{s['step_index']}"
                step_map[key] = {
                    "checked": s["checked"],
                    "checked_by": s["checked_by"],
                    "checked_at": fmt_ts(s["checked_at"])
                }

            return {
                "bpr": record,
                "signoffs": signoff_map,
                "steps": step_map,
                "phases": definition,
                "family": family,
                "consumes_component": consumes_component,
                "consumed_components": consumed_components,
            }
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────
# COMPONENT CONSUMPTION — a product BPR draws down a component lot
# (nano isolate, ice water hash) and records it as a Section 2 cannabis input.
# Mirror of the wash→press handoff, generalized to any component type.
# ─────────────────────────────────────────────────────────────────────────

async def _push_cann_row_to_gas(uid: str, family: str, section_row: int,
                                 lot: dict, weight_g: float, recorded_by: str):
    """
    Best-effort: write a consumed component lot into the BPR sheet's Section 2
    cannabis table (rows 1-7). Uses the same writeBPRFieldsByCellMap action the
    phase write-back uses. Non-fatal — the DB ledger is the source of truth; a
    sheet hiccup must never block the inventory decrement that already committed.
    """
    webhook_url = os.environ.get("GAS_WEBHOOK_URL")
    template_key = PRODUCT_FAMILY_TO_TEMPLATE_KEY.get(family)
    if not webhook_url or not template_key or not section_row:
        return
    i = section_row
    fields = {
        f"CANN{i}_LOTCOA":    lot.get("coa_ref") or lot.get("lot_code"),
        f"CANN{i}_UID":       lot.get("metrc_uid") or lot.get("lot_code"),
        f"CANN{i}_ACTUALQTY": weight_g,
        f"CANN{i}_WEIGHEDBY": recorded_by or "",
        f"CANN{i}_TIME":      (fmt_ts(now_utc()) or "")[-8:],
    }
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.post(webhook_url, json={
                "action":      "writeBPRFieldsByCellMap",
                "uid":         uid,
                "templateKey": template_key,
                "fields":      fields,
                "secret":      os.environ.get("GAS_SHARED_SECRET", ""),
            })
            print(f"GAS CANN-row write-back: {resp.status_code} — {resp.text[:160]}")
    except Exception as e:
        print(f"GAS CANN-row write-back failed (non-fatal) [uid={uid}]: {describe_exc(e)}")


@router.post("/bpr/{uid}/consume-component")
async def consume_component(uid: str, req: ConsumeComponentRequest):
    """
    Record that this BPR consumed `weight_g` of component lot `lot_code`:
      1. decrement the lot via a consumption ledger txn (auto-deplete at zero),
      2. store the BPR↔lot link (with the Section 2 row it occupies),
      3. best-effort mirror it into the sheet's Section 2 cannabis table.
    Rejects over-draw and lots that aren't available.
    """
    if req.weight_g <= 0:
        raise HTTPException(400, "weight_g must be positive")

    conn = get_db()
    try:
        with conn.cursor() as cur:
            bpr = find_existing_bpr(cur, uid)   # resolves lot code OR metrc tag
            if not bpr:
                raise HTTPException(404, "BPR not found")
            bpr = dict(bpr)
            uid = bpr["uid"]                     # pin child rows to the resolved uid
            family = bpr["product_family"]

            lot = _get_component_lot(cur, req.lot_code)  # 404s if missing
            expected = FAMILY_CONSUMES_COMPONENT.get(family)
            if expected and lot["component_type"] != expected:
                raise HTTPException(
                    400,
                    f"{family} consumes {expected} lots, but {req.lot_code} "
                    f"is {lot['component_type']}."
                )

            balance = _lot_balance(cur, lot["id"])
            if req.weight_g > balance:
                raise HTTPException(
                    400,
                    f"Only {balance} {lot['unit']} remain in {req.lot_code}; "
                    f"cannot consume {req.weight_g}."
                )

            # 1. Ledger decrement (mirrors POST /components/{lot}/transactions)
            txn = _add_transaction(
                cur, lot, "consumption", -abs(req.weight_g),
                reference_type="bpr", reference_id=uid,
                note=bpr.get("product_name"), performed_by=req.recorded_by,
            )
            new_balance = _lot_balance(cur, lot["id"])
            if new_balance <= 0 and "depleted" in _workflow_keys(
                    _get_component_type(cur, lot["component_type"])):
                cur.execute(
                    "UPDATE bpr_component_lots SET status='depleted', updated_at=NOW() WHERE id=%s",
                    (lot["id"],)
                )

            # 2. Next free Section 2 row (1-7) for this BPR
            cur.execute(
                "SELECT COUNT(*) AS n FROM bpr_component_consumption WHERE bpr_uid = %s",
                (uid,)
            )
            section_row = int(cur.fetchone()["n"]) + 1

            cur.execute("""
                INSERT INTO bpr_component_consumption
                    (bpr_uid, lot_code, component_type, weight_g, unit,
                     section_row, txn_id, recorded_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                uid, lot["lot_code"], lot["component_type"], abs(req.weight_g),
                lot["unit"], section_row, txn["id"], req.recorded_by,
            ))
            consumption = dict(cur.fetchone())
        conn.commit()

        # 3. Sheet mirror — after commit, best-effort, never blocks the decrement
        if section_row <= 7:
            await _push_cann_row_to_gas(uid, family, section_row, lot,
                                        abs(req.weight_g), req.recorded_by)

        return {
            "consumption": consumption,
            "lot_code": lot["lot_code"],
            "remaining_qty": new_balance,
            "unit": lot["unit"],
        }
    finally:
        conn.close()


@router.delete("/bpr/{uid}/consume-component/{consumption_id}")
def undo_consume_component(uid: str, consumption_id: str):
    """
    Reverse a mistaken consumption: append an offsetting adjustment txn (which
    restores the lot balance and un-depletes it) and delete the link row. The
    sheet's Section 2 cell isn't auto-cleared — an operator correction there is
    rare and safer done by hand than by blanking cells programmatically.
    """
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM bpr_component_consumption WHERE id = %s AND bpr_uid = %s",
                (consumption_id, uid)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "Consumption record not found")
            row = dict(row)

            lot = _get_component_lot(cur, row["lot_code"])
            # Offsetting adjustment puts the weight back on the ledger
            _add_transaction(
                cur, lot, "adjustment", abs(float(row["weight_g"])),
                reference_type="bpr_undo", reference_id=uid,
                note=f"Reversed consumption {consumption_id}",
            )
            # If the lot had auto-depleted, restore it to available now that it
            # carries balance again.
            new_balance = _lot_balance(cur, lot["id"])
            if lot["status"] == "depleted" and new_balance > 0:
                cur.execute(
                    "UPDATE bpr_component_lots SET status='available', updated_at=NOW() WHERE id=%s",
                    (lot["id"],)
                )

            cur.execute("DELETE FROM bpr_component_consumption WHERE id = %s", (consumption_id,))
        conn.commit()
        return {"success": True, "lot_code": row["lot_code"], "restored_qty": new_balance}
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────
# POST /bpr/{uid}/step
# ─────────────────────────────────────────────────────────────────────────
@router.post("/bpr/{uid}/step")
def update_step(uid: str, req: StepCheckRequest):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM bpr_records WHERE uid = %s", (uid,))
            rec = cur.fetchone()
            if not rec:
                raise HTTPException(404, "BPR not found")

            cur.execute("""
                UPDATE bpr_step_checks
                SET checked = %s, checked_by = %s, checked_at = %s
                WHERE bpr_id = %s AND phase_id = %s AND step_index = %s
            """, (
                req.checked,
                req.checked_by if req.checked else None,
                now_utc() if req.checked else None,
                rec["id"], req.phase_id, req.step_index
            ))

            cur.execute("UPDATE bpr_records SET updated_at = %s WHERE uid = %s",
                        (now_utc(), uid))
        conn.commit()
        return {"success": True}
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────
# POST /bpr/{uid}/phase/signoff
# ─────────────────────────────────────────────────────────────────────────
@router.post("/bpr/{uid}/phase/signoff")
async def phase_signoff(uid: str, req: PhaseSignoffRequest):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM bpr_records WHERE uid = %s", (uid,))
            rec = dict(cur.fetchone() or {})
            if not rec:
                raise HTTPException(404, "BPR not found")
            if rec["status"] == "completed":
                raise HTTPException(400, "BPR is already completed and released")

            family = rec["product_family"]
            definition = BPR_PHASES[family]

            phase_def = next((p for p in definition["phases"] if p["id"] == req.phase_id), None)
            if not phase_def:
                raise HTTPException(404, f"Phase {req.phase_id} not found in {family} template")

            cur.execute("""
                SELECT step_index, checked FROM bpr_step_checks
                WHERE bpr_id = %s AND phase_id = %s
                ORDER BY step_index
            """, (rec["id"], req.phase_id))
            checks = {r["step_index"]: r["checked"] for r in cur.fetchall()}

            unchecked = [i for i, s in enumerate(phase_def["steps"]) if not checks.get(i, False)]
            if unchecked:
                raise HTTPException(400, {
                    "message": "All steps must be checked before signing off",
                    "unchecked_steps": unchecked
                })

            ccps = phase_def.get("ccps", [])
            ccp_values = req.ccp_values or {}
            group_min = phase_def.get("ccp_group_min")

            def has_value(i):
                v = ccp_values.get(str(i), ccp_values.get(i))
                return v not in (None, "")

            if group_min is not None:
                # "At least N of these" instead of "all required" — e.g. variable press count
                provided_count = sum(1 for i in ccps if has_value(i))
                if provided_count < group_min:
                    ccp_labels = phase_def.get("ccp_labels", {})
                    raise HTTPException(400, {
                        "message": f"At least {group_min} CCP measurement(s) required from: "
                                   + ", ".join(ccp_labels.get(i, f"Step {i+1}") for i in ccps),
                        "provided_count": provided_count
                    })
            else:
                missing_ccps = [i for i in ccps if not has_value(i)]
                if missing_ccps:
                    ccp_labels = phase_def.get("ccp_labels", {})
                    missing_labels = [ccp_labels.get(i, f"Step {i+1}") for i in missing_ccps]
                    raise HTTPException(400, {
                        "message": "CCP measurements required before sign-off",
                        "missing_ccps": missing_labels
                    })

            if phase_def.get("notes_required") and not (req.notes or "").strip():
                raise HTTPException(400, {"message": "Notes are required before signing off this phase"})

            cur.execute("""
                INSERT INTO bpr_phase_signoffs
                    (bpr_id, uid, phase_id, phase_name, employee_name, notes, ccp_values)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (bpr_id, phase_id) DO UPDATE SET
                    employee_name = EXCLUDED.employee_name,
                    notes = EXCLUDED.notes,
                    ccp_values = EXCLUDED.ccp_values,
                    signed_at = NOW()
                RETURNING *
            """, (
                rec["id"], uid, req.phase_id, phase_def["name"],
                req.employee_name, req.notes,
                json.dumps(ccp_values)
            ))
            signoff = dict(cur.fetchone())

            cur.execute("UPDATE bpr_records SET updated_at = %s WHERE uid = %s",
                        (now_utc(), uid))
        conn.commit()
        # ── Write phase data back to Google Sheet BPR ────────────
        with conn.cursor() as cur2:
            cur2.execute("""
                SELECT * FROM bpr_step_checks
                WHERE bpr_id = %s AND phase_id = %s
                ORDER BY step_index
            """, (rec["id"], req.phase_id))
            phase_steps = [dict(r) for r in cur2.fetchall()]

        # Fire and forget — non-blocking, non-fatal
        import asyncio
        asyncio.create_task(push_phase_to_gas_bpr(
            uid          = uid,
            phase_id     = req.phase_id,
            phase_def    = phase_def,
            signoff      = signoff,
            steps        = phase_steps,
            product_family = rec["product_family"]
        ))

        return {
            "success": True,
            "signoff": signoff,
            "message": f"Phase '{phase_def['name']}' signed off by {req.employee_name}"
        }

    finally:
        conn.close()

# ─────────────────────────────────────────────────────────────────────────
# POST /bpr/{uid}/release
# ─────────────────────────────────────────────────────────────────────────
@router.post("/bpr/{uid}/release")
async def supervisor_release(uid: str, req: SupervisorReleaseRequest):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM bpr_records WHERE uid = %s", (uid,))
            rec = dict(cur.fetchone() or {})
            if not rec:
                raise HTTPException(404, "BPR not found")
            if rec["status"] == "completed":
                raise HTTPException(400, "BPR is already completed")

            family = rec["product_family"]
            definition = BPR_PHASES[family]

            # ── PRECONDITION, SECOND GATE ────────────────────────────────
            # The create-time guard can't help BPRs that were already in the
            # DB before it existed — find_existing_bpr() short-circuits create
            # for those, so they'd sail straight through to release exactly
            # like before. This is the net that catches that backlog, and the
            # last point where a batch can still be stopped from being marked
            # released with no physical record behind it.
            #
            # Blocking here is recoverable, which is why it's safe to do: all
            # the operator's work is already committed to the DB. They create
            # the batch record sheet and press release again — nothing is lost.
            # Same rosin_wash exemption and same fail-open-on-error rules as
            # create; see bpr_sheet_exists().
            if family != "rosin_wash":
                allowed, reason = await bpr_sheet_exists(uid)
                if not allowed:
                    raise HTTPException(409, {
                        "message": (
                            "This BPR can't be released: no batch record exists "
                            "for this UID, so the release would not be written to "
                            "any record. Create the batch record (Punch Tools → "
                            "Create Batch Records for Selected), then release again. "
                            "Nothing you've entered will be lost."
                        ),
                        "uid": uid,
                        "batch_id": rec.get("batch_id"),
                        "reason": reason,
                        "code": "no_batch_record_sheet",
                    })

            cur.execute("SELECT phase_id FROM bpr_phase_signoffs WHERE bpr_id = %s", (rec["id"],))
            signed_phases = {r["phase_id"] for r in cur.fetchall()}
            all_phases = {p["id"] for p in definition["phases"]}
            unsigned = all_phases - signed_phases
            if unsigned:
                phase_names = [p["name"] for p in definition["phases"] if p["id"] in unsigned]
                raise HTTPException(400, {
                    "message": "All phases must be signed off before supervisor release",
                    "unsigned_phases": phase_names
                })

            cur.execute("SELECT * FROM bpr_phase_signoffs WHERE bpr_id = %s ORDER BY signed_at", (rec["id"],))
            signoffs = [dict(r) for r in cur.fetchall()]

            cur.execute("SELECT * FROM bpr_step_checks WHERE bpr_id = %s ORDER BY phase_id, step_index", (rec["id"],))
            steps = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                UPDATE bpr_records SET
                    status = 'completed', completed_at = %s, supervisor_name = %s,
                    supervisor_at = %s, deviation_notes = %s, total_yield = %s, updated_at = %s
                WHERE uid = %s
                RETURNING *
            """, (now_utc(), req.supervisor_name, now_utc(),
                  req.deviation_notes, req.total_yield, now_utc(), uid))
            completed = dict(cur.fetchone())

        conn.commit()

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Failed to release BPR: {str(e)}")
    finally:
        conn.close()   # ← finally now ONLY closes the connection. Nothing else.

    # ── Everything below only runs after a successful commit ──────────
    #
    # THE RELEASE IS ALREADY DONE AT THIS POINT. Every step below is a
    # downstream side effect — PDF, sheet write-back, tracker ping — and none
    # of them can un-release the batch, because the transaction that marked it
    # `completed` has already committed and its connection is closed.
    #
    # So an exception down here must NOT become a 500. That exact bug bit us:
    # push_wash_release_summary() raised NameError, the operator saw "500
    # Internal Server Error" and reasonably concluded the release had failed —
    # but the DB said completed, so every retry hit "BPR is already completed",
    # and the batch was stuck with no way forward from the UI.
    #
    # Each step is therefore isolated: a failure is recorded as a warning and
    # reported honestly in the response, and the rest still run. Reporting
    # matters as much as the isolation — silently swallowing these is how the
    # PDF upload managed to fail on every single release without anyone
    # noticing. The operator gets "released, but the sheet write-back failed",
    # which is the truth and is actionable.
    warnings: List[str] = []

    async def _side_effect(label: str, coro):
        """Run one post-release side effect; never let it fail the request."""
        try:
            return await coro
        except Exception as exc:
            print(f"post-release [{label}] failed for {uid}: {exc}")
            import traceback; traceback.print_exc()
            warnings.append(f"{label} failed: {exc}")
            return None

    pdf_url = await _side_effect(
        "PDF generation/upload",
        generate_and_upload_pdf(completed, definition, signoffs, steps),
    )

    if pdf_url:
        try:
            conn2 = get_db()
            try:
                with conn2.cursor() as cur2:
                    cur2.execute("UPDATE bpr_records SET pdf_drive_url = %s WHERE uid = %s",
                                 (pdf_url, uid))
                conn2.commit()
                completed["pdf_drive_url"] = pdf_url
            finally:
                conn2.close()
        except Exception as exc:
            print(f"post-release [PDF url save] failed for {uid}: {exc}")
            warnings.append(f"PDF url save failed: {exc}")

    await _side_effect("tracker status ping", ping_gas_webhook(uid, "completed", pdf_url))

    if family == "rosin_wash":
        # Marking the lot available is the one step here with real downstream
        # consequence (it's what lets a press BPR draw this hash down), so it
        # gets its own warning rather than being lumped in with the sheet write.
        try:
            conn3 = get_db()
            try:
                with conn3.cursor() as cur3:
                    cur3.execute("""
                        UPDATE bpr_component_lots SET
                            status = 'available',
                            storage_location = COALESCE(NULLIF(storage_location, ''), (
                                SELECT storage_location FROM hash_lot_sift_sessions
                                WHERE hash_lot_id = %s AND storage_location IS NOT NULL
                                ORDER BY completed_at DESC NULLS LAST LIMIT 1
                            )),
                            updated_at = NOW()
                        WHERE lot_code = %s
                    """, (uid, uid))
                conn3.commit()
            finally:
                conn3.close()
        except Exception as exc:
            print(f"post-release [lot → available] failed for {uid}: {exc}")
            import traceback; traceback.print_exc()
            warnings.append(f"marking lot available failed: {exc}")

        await _side_effect(
            "wash sheet release summary",
            push_wash_release_summary(uid, req.supervisor_name),
        )
    else:
        # Cell-mapped standardized BPRs: write Section 3 yield (Expected/Actual)
        # at release. The wash sheet handles its own Section 3 above via
        # push_wash_release_summary; every other family lands here.
        await _side_effect(
            "sheet release summary",
            push_release_summary_bpr(completed, req.supervisor_name, req.total_yield),
        )

    message = f"BPR released by {req.supervisor_name}"
    if warnings:
        message += (" — released successfully, but some follow-up steps failed "
                    "(see warnings); the release itself is recorded.")

    return {
        "success": True,
        "bpr": completed,
        "warnings": warnings,
        "message": message
    }

# ─────────────────────────────────────────────────────────────────────────
# POST /bpr/{uid}/sanitation  — Section 5 (cell-mapped families)
# POST /bpr/{uid}/equipment   — Section 4 (cell-mapped families)
# Non-wash counterparts to the wash's submit_wash_sanitation(). Both write to
# the standardized cell map (SAN{i}_* / EQUIP{i}_*) via writeBPRFieldsByCellMap,
# and both are PER-ROW by design: §17210(c)/§17221 rows name specific surfaces
# and equipment, so each row must carry its own operator-entered attestation —
# never a bulk stamp across every listed row.
# ─────────────────────────────────────────────────────────────────────────

# Nano tabs (LiquiDabs / Nano Isolate) grew S4 to 12 rows and S5 to 11 rows —
# their cell map (NANO_SECTION_OPTS in BPR.gs) shifts S5/S8 down accordingly.
NANO_TEMPLATE_FAMILIES = {"liquidabs", "nano_isolate"}


def _bpr_template_key_or_404(uid: str) -> tuple[dict, str]:
    """Load the BPR record and resolve its cell-map templateKey, or raise."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM bpr_records WHERE uid = %s", (uid,))
            rec = cur.fetchone()
    finally:
        conn.close()
    if not rec:
        raise HTTPException(404, "BPR not found")
    rec = dict(rec)
    template_key = PRODUCT_FAMILY_TO_TEMPLATE_KEY.get(rec.get("product_family"))
    if not template_key:
        raise HTTPException(400, f"No cell-map template for family {rec.get('product_family')}")
    return rec, template_key


@router.post("/bpr/{uid}/sanitation")
async def submit_bpr_sanitation(uid: str, req: SanitationLogRequest):
    """
    Section 5 sanitation log for cell-mapped standardized BPRs. Reuses the wash
    SanitationEntry model 1:1 so ONE frontend sanitation UI serves both paths;
    only the destination differs (SAN{i}_* cell fields here vs WASH_S5_ROW{n}_*
    named ranges on the wash sheet).
    """
    rec, template_key = _bpr_template_key_or_404(uid)
    max_san = 11 if rec.get("product_family") in NANO_TEMPLATE_FAMILIES else 10

    fields = {}
    incomplete = []
    for e in req.entries:
        if not (1 <= e.row <= max_san):   # SAN: standard 1-10 (rows 59-68), nano 1-11 (62-72)
            raise HTTPException(400, f"Invalid sanitation row: {e.row} (must be 1-{max_san})")
        # Untouched rows are fine to skip — not every run cleans every surface.
        # A PARTIALLY filled row is a §17210(c) violation, so reject those loudly.
        if not any([e.date, e.clean_start, e.clean_end, e.passed, e.cleaned_by]):
            continue
        if not (e.date and e.clean_start and e.clean_end and e.cleaned_by):
            incomplete.append(e.row)
            continue
        p = f"SAN{e.row}"
        fields[p + "_DATE"]         = e.date
        fields[p + "_CLEANSTART"]   = e.clean_start
        fields[p + "_CLEANEND"]     = e.clean_end
        fields[p + "_PPM"]          = e.ppm or ""
        fields[p + "_STRIPSUSED"]   = e.strips_used or ""
        fields[p + "_PASS"]         = e.passed or ""
        fields[p + "_CLEANEDBY"]    = e.cleaned_by
        fields[p + "_DRYBEFOREUSE"] = e.dry_before_use or ""

    if incomplete:
        raise HTTPException(400, {
            "message": "Sanitation rows missing required fields (date, start, end, cleaned by are all required — §17210(c))",
            "incomplete_rows": incomplete,
        })
    if not fields:
        raise HTTPException(400, "No sanitation entries provided")

    await _post_wash_gas({
        "action":      "writeBPRFieldsByCellMap",
        "uid":         uid,
        "templateKey": template_key,
        "fields":      fields,
    }, f"BPR sanitation log ({rec.get('product_family')})")

    return {"success": True, "rows_written": len(fields) // 8,
            "message": "Sanitation log written to BPR sheet"}


@router.post("/bpr/{uid}/equipment")
async def submit_bpr_equipment(uid: str, req: EquipmentCheckRequest):
    """
    Section 4 equipment check-in for cell-mapped standardized BPRs. Per-row:
    the operator confirms each specific equipment item, so we stamp only the
    rows submitted with a checked_by — Checked By (col I) + Time (col J).
    """
    rec, template_key = _bpr_template_key_or_404(uid)
    max_equip = 12 if rec.get("product_family") in NANO_TEMPLATE_FAMILIES else 9

    now_time = (fmt_ts(datetime.now(timezone.utc)) or "").split(" ", 1)[-1]  # time portion

    fields = {}
    for e in req.entries:
        if not (1 <= e.row <= max_equip):   # EQUIP: standard 1-9 (rows 48-56), nano 1-12 (48-59)
            raise HTTPException(400, f"Invalid equipment row: {e.row} (must be 1-{max_equip})")
        if not e.checked_by:        # untouched row — skip
            continue
        p = f"EQUIP{e.row}"
        fields[p + "_CHECKEDBY"] = e.checked_by
        fields[p + "_TIME"]      = e.time or now_time

    if not fields:
        raise HTTPException(400, "No equipment check-ins provided")

    await _post_wash_gas({
        "action":      "writeBPRFieldsByCellMap",
        "uid":         uid,
        "templateKey": template_key,
        "fields":      fields,
    }, f"BPR equipment check-in ({rec.get('product_family')})")

    return {"success": True, "rows_written": len(fields) // 2,
            "message": "Equipment check-in written to BPR sheet"}


# ─────────────────────────────────────────────────────────────────────────
# GET /bpr/{uid}/status
# ─────────────────────────────────────────────────────────────────────────
@router.get("/bpr/{uid}/status")
def get_bpr_status(uid: str, metrc_uid: Optional[str] = Query(None)):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            rec = find_existing_bpr(cur, uid, metrc_uid)
            if not rec:
                return {"exists": False, "uid": uid}
            rec = dict(rec)

            cur.execute(
                "SELECT COUNT(*) AS n FROM bpr_phase_signoffs WHERE bpr_id = %s",
                (rec["id"],)
            )
            phases_signed = cur.fetchone()["n"]

            family = rec["product_family"]
            total_phases = len(BPR_PHASES.get(family, {}).get("phases", []))
            return {
                "exists": True,
                "uid": rec["uid"],
                "metrc_uid": rec.get("metrc_uid"),
                "status": rec["status"],
                "product_family": family,
                "phases_signed": phases_signed,
                "total_phases": total_phases,
                "created_at": fmt_ts(rec["created_at"]),
                "completed_at": fmt_ts(rec["completed_at"]),
                "supervisor_name": rec["supervisor_name"],
                "pdf_drive_url": rec["pdf_drive_url"],
            }
    finally:
        conn.close()

# ─────────────────────────────────────────────────────────────────────────
# PDF generation + Google Drive upload
# ─────────────────────────────────────────────────────────────────────────
async def generate_and_upload_pdf(bpr: dict, definition: dict, signoffs: list, steps: list) -> Optional[str]:
    """
    Generates a BPR PDF using reportlab and uploads to the UID's Google Drive folder.
    Returns the Drive file URL or None on failure.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, HRFlowable
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
        import io

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                                leftMargin=0.75*inch, rightMargin=0.75*inch,
                                topMargin=0.75*inch, bottomMargin=0.75*inch)

        styles = getSampleStyleSheet()
        PUNCH_RED = colors.HexColor("#E8192C")
        DARK = colors.HexColor("#1A1D2E")
        MID = colors.HexColor("#4A5068")
        LIGHT = colors.HexColor("#F4F6FA")

        title_style = ParagraphStyle("Title", fontName="Helvetica-Bold", fontSize=16,
                                     textColor=DARK, spaceAfter=2)
        sub_style   = ParagraphStyle("Sub",   fontName="Helvetica",      fontSize=9,
                                     textColor=MID, spaceAfter=6)
        label_style = ParagraphStyle("Label", fontName="Helvetica-Bold", fontSize=8,
                                     textColor=MID, spaceAfter=2, spaceBefore=8)
        body_style  = ParagraphStyle("Body",  fontName="Helvetica",      fontSize=9,
                                     textColor=DARK, spaceAfter=4)
        phase_style = ParagraphStyle("Phase", fontName="Helvetica-Bold", fontSize=10,
                                     textColor=PUNCH_RED, spaceAfter=4, spaceBefore=12)
        ccp_style   = ParagraphStyle("CCP",   fontName="Helvetica-Bold", fontSize=8,
                                     textColor=colors.HexColor("#B45309"))

        story = []

        # Header
        header_data = [
            [Paragraph("PUNCH MEDIA LLC", ParagraphStyle("H", fontName="Helvetica-Bold", fontSize=14, textColor=PUNCH_RED)),
             Paragraph(f"BATCH PRODUCTION RECORD", ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=11, textColor=DARK, alignment=2)),],
            [Paragraph(f"DCC License: DCC-10003615", sub_style),
             Paragraph("COMPLETED & RELEASED", ParagraphStyle("R", fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#0A7A3E"), alignment=2)),],
        ]
        header_table = Table(header_data, colWidths=[3.5*inch, 3.5*inch])
        header_table.setStyle(TableStyle([
            ("LINEBELOW", (0,1), (-1,1), 1.5, PUNCH_RED),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 12))

        # Batch info table
        mfg = bpr.get("mfg_date") or "—"
        completed_at = fmt_ts(bpr.get("completed_at")) or "—"
        info_data = [
            ["Product Name", bpr.get("product_name","—"), "Batch ID", bpr.get("batch_id","—")],
            ["METRC UID", bpr.get("uid","—"), "Mfg Date", mfg],
            ["Product Family", definition.get("label","—"), "Completed", completed_at],
            ["SOP Reference", definition.get("sop_ref","—"), "Supervisor Release", bpr.get("supervisor_name","—")],
        ]
        info_table = Table(info_data, colWidths=[1.3*inch, 2.2*inch, 1.3*inch, 2.2*inch])
        info_table.setStyle(TableStyle([
            ("FONTNAME",    (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTNAME",    (2,0), (2,-1), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 8),
            ("TEXTCOLOR",   (0,0), (0,-1), MID),
            ("TEXTCOLOR",   (2,0), (2,-1), MID),
            ("BACKGROUND",  (0,0), (0,-1), LIGHT),
            ("BACKGROUND",  (2,0), (2,-1), LIGHT),
            ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#E2E6EF")),
            ("TOPPADDING",  (0,0), (-1,-1), 5),
            ("BOTTOMPADDING",(0,0), (-1,-1), 5),
            ("LEFTPADDING", (0,0), (-1,-1), 7),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 14))

        # Build signoff lookup
        signoff_map = {s["phase_id"]: s for s in signoffs}
        step_map = {}
        for s in steps:
            step_map[f"{s['phase_id']}:{s['step_index']}"] = s

        # Phases
        for phase_def in definition["phases"]:
            pid = phase_def["id"]
            signoff = signoff_map.get(pid)

            story.append(Paragraph(phase_def["name"].upper(), phase_style))

            # Steps table
            step_rows = []
            for i, step_text in enumerate(phase_def["steps"]):
                is_ccp = i in phase_def.get("ccps", [])
                check = step_map.get(f"{pid}:{i}", {})
                checked = check.get("checked", False)
                mark = "✓" if checked else "○"
                by_str = f"  [{check.get('checked_by','')}]" if checked and check.get("checked_by") else ""
                label = f"★ CCP: {phase_def['ccp_labels'].get(i,'')}  |  " if is_ccp else ""
                cell_text = f"{label}{step_text}{by_str}"
                cell_color = colors.HexColor("#FFFBEB") if is_ccp else colors.white
                step_rows.append([
                    Paragraph(mark, ParagraphStyle("mark", fontName="Helvetica-Bold", fontSize=9,
                                                   textColor=colors.HexColor("#0A7A3E") if checked else MID)),
                    Paragraph(cell_text, ccp_style if is_ccp else body_style),
                ])

            if step_rows:
                t = Table(step_rows, colWidths=[0.3*inch, 6.7*inch])
                t.setStyle(TableStyle([
                    ("VALIGN",      (0,0), (-1,-1), "TOP"),
                    ("TOPPADDING",  (0,0), (-1,-1), 3),
                    ("BOTTOMPADDING",(0,0), (-1,-1), 3),
                    ("LEFTPADDING", (0,0), (-1,-1), 4),
                    ("LINEBELOW",   (0,-1), (-1,-1), 0.5, colors.HexColor("#E2E6EF")),
                ]))
                story.append(t)

            # CCP values
            if signoff and signoff.get("ccp_values"):
                ccpv = signoff["ccp_values"]
                if isinstance(ccpv, str):
                    try: ccpv = json.loads(ccpv)
                    except: ccpv = {}
                if ccpv:
                    ccp_rows = []
                    for k, v in ccpv.items():
                        label = phase_def["ccp_labels"].get(int(k), f"Step {k}")
                        ccp_rows.append([
                            Paragraph(f"★ {label}:", ParagraphStyle("cl", fontName="Helvetica-Bold", fontSize=8, textColor=colors.HexColor("#B45309"))),
                            Paragraph(str(v), body_style),
                        ])
                    ct = Table(ccp_rows, colWidths=[2.5*inch, 4.5*inch])
                    ct.setStyle(TableStyle([
                        ("BACKGROUND",  (0,0), (-1,-1), colors.HexColor("#FFFBEB")),
                        ("TOPPADDING",  (0,0), (-1,-1), 4),
                        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
                        ("LEFTPADDING", (0,0), (-1,-1), 7),
                        ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#FEF3C7")),
                    ]))
                    story.append(Spacer(1, 4))
                    story.append(ct)

            # Phase sign-off row
            if signoff:
                so_data = [[
                    Paragraph("PHASE SIGNED OFF", ParagraphStyle("sol", fontName="Helvetica-Bold", fontSize=8, textColor=colors.HexColor("#0A7A3E"))),
                    Paragraph(signoff.get("employee_name","—"), body_style),
                    Paragraph(fmt_ts(signoff.get("signed_at")) or "—", body_style),
                    Paragraph(signoff.get("notes","") or "", ParagraphStyle("n", fontName="Helvetica-Oblique", fontSize=8, textColor=MID)),
                ]]
                so_t = Table(so_data, colWidths=[1.4*inch, 1.8*inch, 1.8*inch, 2*inch])
                so_t.setStyle(TableStyle([
                    ("BACKGROUND",  (0,0), (-1,-1), colors.HexColor("#ECFDF3")),
                    ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#D1FAE5")),
                    ("TOPPADDING",  (0,0), (-1,-1), 5),
                    ("BOTTOMPADDING",(0,0), (-1,-1), 5),
                    ("LEFTPADDING", (0,0), (-1,-1), 7),
                ]))
                story.append(Spacer(1, 4))
                story.append(so_t)

            story.append(Spacer(1, 8))

        # Final yield + deviation notes
        if bpr.get("total_yield") or bpr.get("deviation_notes"):
            story.append(HRFlowable(width="100%", thickness=1, color=PUNCH_RED))
            story.append(Spacer(1, 8))
            if bpr.get("total_yield"):
                story.append(Paragraph("TOTAL BATCH YIELD", label_style))
                story.append(Paragraph(bpr["total_yield"], body_style))
            if bpr.get("deviation_notes"):
                story.append(Paragraph("DEVIATION LOG", label_style))
                story.append(Paragraph(bpr["deviation_notes"], body_style))
            story.append(Spacer(1, 8))

        # Supervisor release block
        story.append(HRFlowable(width="100%", thickness=1.5, color=DARK))
        story.append(Spacer(1, 8))
        rel_data = [[
            Paragraph("SUPERVISOR RELEASE", ParagraphStyle("sr", fontName="Helvetica-Bold", fontSize=9, textColor=DARK)),
            Paragraph(bpr.get("supervisor_name","—"), ParagraphStyle("srv", fontName="Helvetica-Bold", fontSize=10, textColor=PUNCH_RED)),
            Paragraph(fmt_ts(bpr.get("supervisor_at")) or "—", body_style),
        ]]
        rel_t = Table(rel_data, colWidths=[1.8*inch, 2.5*inch, 2.7*inch])
        rel_t.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,-1), LIGHT),
            ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#E2E6EF")),
            ("TOPPADDING",  (0,0), (-1,-1), 8),
            ("BOTTOMPADDING",(0,0), (-1,-1), 8),
            ("LEFTPADDING", (0,0), (-1,-1), 10),
            ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(rel_t)

        doc.build(story)
        pdf_bytes = buffer.getvalue()

        # Upload to Google Drive
        return await upload_to_drive(pdf_bytes, bpr["uid"], bpr["batch_id"])

    except Exception as e:
        print(f"PDF generation error (non-fatal): {e}")
        import traceback; traceback.print_exc()
        return None


async def upload_to_drive(pdf_bytes: bytes, uid: str, batch_id: str) -> Optional[str]:
    """
    Uploads the released-BPR PDF to the batch's UID subfolder inside COA
    Archive on Google Drive.

    Two behaviors worth knowing:
    1. Folders are keyed by the SOURCE METRC UID (UID_TRACKER col B). Wash
       BPRs use the lot code (HASH-...) as their uid, so we resolve the lot's
       real METRC tag first — otherwise we'd mint stray HASH-named folders
       next to the proper tag-named ones.
    2. All Drive calls pass supportsAllDrives=True so this works whether COA
       Archive lives in My Drive or a Shared Drive. NOTE: the upload itself
       will 403 ("Service Accounts do not have storage quota") until the
       folder is inside a Shared Drive — that's Google policy, not a bug here.
    """
    try:
        import google.auth
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload
        import io

        sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT")
        if not sa_json:
            print("No GOOGLE_SERVICE_ACCOUNT env var set — skipping Drive upload")
            return None

        creds_dict = json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        service = build("drive", "v3", credentials=creds)

        root_folder_id = os.environ.get("DRIVE_COA_FOLDER_ID")
        if not root_folder_id:
            print("No DRIVE_COA_FOLDER_ID env var — skipping Drive upload")
            return None

        # ── Resolve the folder key: lot code → source METRC UID ──────────
        # Finished-goods BPRs already use the tag as uid, so the lookup
        # simply finds no lot and falls through to uid unchanged.
        folder_key = uid
        try:
            _conn = get_db()
            try:
                with _conn.cursor() as _cur:
                    _cur.execute(
                        "SELECT metrc_uid FROM bpr_component_lots WHERE lot_code = %s",
                        (uid,)
                    )
                    _row = _cur.fetchone()
                    if _row and _row["metrc_uid"]:
                        folder_key = _row["metrc_uid"]
            finally:
                _conn.close()
        except Exception as _e:
            print(f"folder key lookup failed, using uid as-is: {_e}")

        # ── Find (or create) the UID subfolder ───────────────────────────
        results = service.files().list(
            q=f"name='{folder_key}' and '{root_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        folders = results.get("files", [])

        if not folders:
            folder_meta = {
                "name": folder_key,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [root_folder_id]
            }
            folder = service.files().create(
                body=folder_meta, fields="id", supportsAllDrives=True
            ).execute()
            folder_id = folder["id"]
        else:
            folder_id = folders[0]["id"]

        # ── Upload the PDF ────────────────────────────────────────────────
        filename = f"BPR_{batch_id or uid}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        file_meta = {"name": filename, "parents": [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype="application/pdf")
        file = service.files().create(
            body=file_meta, media_body=media, fields="id, webViewLink",
            supportsAllDrives=True
        ).execute()

        print(f"BPR PDF uploaded: {file.get('webViewLink')}")
        return file.get("webViewLink")

    except Exception as e:
        print(f"Drive upload error (non-fatal): {e}")
        return None


async def ping_gas_webhook(uid: str, status: str, pdf_url: Optional[str]):
    """
    Pings the GAS doPost webhook to update BPR_STATUS in UID_TRACKER.
    """
    webhook_url = os.environ.get("GAS_WEBHOOK_URL")
    if not webhook_url:
        return
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.post(webhook_url, json={
                "action": "updateBPRStatus",
                "uid": uid,
                "bprStatus": status,
                "pdfUrl": pdf_url,
                "secret": os.environ.get("GAS_SHARED_SECRET", ""),
            })
            # The response was being discarded entirely, so an "Unauthorized"
            # from the doPost secret gate looked identical to a success.
            print(f"GAS webhook ping ({uid}): {resp.status_code} — {resp.text[:200]}")
    except Exception as e:
        print(f"GAS webhook ping failed (non-fatal) [uid={uid}]: {describe_exc(e)}")

# ── Product family → GAS templateKey (BPR_CELL_MAPS key in BPR.gs) ──
# ── Product family → GAS templateKey (BPR_CELL_MAPS key in BPR.gs) ──
PRODUCT_FAMILY_TO_TEMPLATE_KEY = {
    "gummies":              "punch_gummies",
    "rosin_press":          "punch_live_rosin",
    "rosin_rocket":         "punch_rocket",
    "bho_badder":           "punch_bho_badder",   # phase def rewritten to match BPR-BHO-001
    "tempo_diamonds":       "tempo_lr_diamonds",  # → 'Tempo LR Diamonds' tab
    "rosin_vape_decarb":    "punch_rosin_aio",    # → 'PUNCH Rosin Vapes' tab
    "punch_stinger":        "punch_stinger",      # → 'PUNCH Stingers' tab
    "punch_cookie_delight": "punch_cookie",       # → 'PUNCH Cookie Delight' tab
    "punch_malt_balls":     "punch_malt_balls",   # → 'PUNCH Malt Balls' tab
    "asteroids":            "punch_asteroids",    # → 'PUNCH Asteroids' tab
    # Dynamic-tab families — templateKey → __*_DYNAMIC__ placeholder; the GAS
    # write-back resolves the real per-flavor tab via the single-tab fallback.
    "punch_chocolate":        "punch_punchbar",
    "punch_chocolate_sf":     "punch_punchbar",
    "punch_chocolate_pb":     "punch_punchbar",
    "dr_norms_cookie":        "dr_norms",
    "dr_norms_cookie_nano":   "dr_norms",
    "dr_norms_rkt":           "dr_norms",
    "dr_norms_brownie":       "dr_norms",
    "dr_norms_brownie_sleep": "dr_norms",
    "vapes":                  "punch_vapes",    # → 'Distillate Vapes' tab
    "tempo_lr_vape":          "tempo_lr_aio",   # → 'TEMPO LR Vape' tab
    "liquidabs":              "liquidabs",      # → 'LiquiDabs' tab (26-step cell map)
    "nano_isolate":           "nano_isolate",   # → Nano-Isolate component tab (28-step map)
    # "rosin_wash" stays on its own dedicated pathway (push_wash_phase_to_gas)
    # ⚠ liquidabs/nano_isolate cell maps assume Section 6 steps start at the
    # standard row 71 — verify against the real tabs (smoke test) before trusting.
}

# ── Product family → component type it draws down as a Section 2 input ──────
# A NANO SKU BPR consumes a nano_isolate lot exactly the way a rosin press
# consumes an ice_water_hash lot: the operator picks an available lot from
# inventory at the start of the run, records the weight, and that weight is
# both written into the BPR's Section 2 cannabis table AND decremented from the
# component lot's ledger. Families absent from this map show no picker.
FAMILY_CONSUMES_COMPONENT = {
    "rosin_press":          "ice_water_hash",   # live rosin pressed from wash
    "rosin_rocket":         "ice_water_hash",
    "dr_norms_cookie_nano": "nano_isolate",     # NANO cookie SKU
    "liquidabs":            "nano_isolate",      # nano tincture
}

# ── GUMMIES: phase → BPR write-back mapping (BPR-GUM-001 v2.0, 18-step) ──
GUMMIES_PHASE_TO_STEPS = {
    "pre_production":  [1],
    "ingredient_prep": [2],
    "cook":            [3, 4, 5, 6, 7, 8],
    "depositing":      [9, 10],
    "curing":          [11],
    "qc_weight":       [12],
    "packaging":       [13, 14, 15, 16],
    "sanitation":      [17],
}

GUMMIES_CCP_VALUES = {
    ("cook", 8):       6,
    ("cook", 12):      8,
    ("cook", 13):      8,
    ("qc_weight", 1):  12,
    ("packaging", 5):  15,
    ("packaging", 7):  16,
}

GUMMIES_CANN_VALUES = {
    ("ingredient_prep", 5): "CANN1",
}

# ── LIVE ROSIN PRESS: phase → BPR write-back mapping (BPR-LRS-001 v2.0, 12-step) ──
LIVE_ROSIN_PHASE_TO_STEPS = {
    "pre_production": [1, 3],
    "pressing":        [2, 4, 5],
    "curing":          [6],
    "filling":         [7, 8],
    "packaging":       [9, 10],
    "sanitation":      [11],
}

LIVE_ROSIN_CCP_VALUES = {
    ("pre_production", 4):  3,   # Press #1
    ("pre_production", 5):  3,   # Press #2
    ("pre_production", 6):  3,   # Press #3
    ("pre_production", 7):  3,   # Press #4
    ("pressing", 6):        5,
    ("pressing", 7):        5,
    ("curing", 5):          6,
    ("curing", 6):          6,
    ("filling", 2):         8,
    ("filling", 4):         8,
    ("packaging", 3):       10,
    ("packaging", 5):       10,
}

LIVE_ROSIN_CANN_VALUES = {
    ("pre_production", 2): "CANN1",   # hash weight pulled from freezer → Section 2 row 1
}

# ── ROSIN ROCKET: phase → BPR write-back mapping (BPR-RKT-001 v2.0, 19 steps) ──
# The sheet's Section 6 order (from the master template) is the source of truth.
# The app's rosin_rocket phases were authored from this BPR, so they map cleanly
# and contiguously — no interleaving like live rosin.
ROSIN_ROCKET_PHASE_TO_STEPS = {
    "pre_production":           [1, 2],           # ISO-wipe; verify flower+rosin COAs
    "pre_weigh":                [3, 4, 5],        # flower pre-weigh; rosin worm; glass-tip prep
    "rolling_assembly":         [6, 7, 8],        # grind; lay paper+tip; distribute flower
    "rosin_placement_and_seal": [9, 10, 11, 12],  # place worm; roll; GlueGar seal; pack+twist
    "unit_weight_qc":           [13],             # finished joint weight check
    "tube_and_pouch_seal":      [14, 15],         # insert tube; pouch seal 180°F
    "labeling_packaging":       [16, 17],         # info sticker; 10CT case
    "sanitation":               [18, 19],         # clean-down; METRC entry
}

# CCP monitoring value → the sheet step whose VALUE/PASSFAIL cell it lands on.
# Keys are (phase_id, ccp_index) where ccp_index matches the phase's ccp_labels.
ROSIN_ROCKET_CCP_VALUES = {
    ("pre_production", 0):           1,   # equipment clean/dry
    ("pre_production", 1):           2,   # both cannabis COAs verified
    ("pre_weigh", 0):                3,   # flower pre-weigh 1.3 g/cup
    ("pre_weigh", 1):                4,   # rosin worm pre-weigh 0.3 g
    ("rosin_placement_and_seal", 0): 9,   # worm out of freezer at placement
    ("rosin_placement_and_seal", 3): 11,  # GlueGar-only seal, no saliva
    ("unit_weight_qc", 1):           13,  # finished joint 1.6 g ±0.1 g
    ("tube_and_pouch_seal", 1):      15,  # pouch seal 180°F
    ("labeling_packaging", 0):       16,  # label verification, 5 fields
    ("sanitation", 4):               19,  # METRC entry within 24 h
}

# Flower + rosin are pre-weighed and recorded in Section 2 by hand (supervisor
# sign-off block) BEFORE production, so there's no in-production cannabis-weight
# CCP to fan out to CANN rows — unlike gummies/live-rosin, whose cannabis is
# weighed at incorporation time. Left empty deliberately.
ROSIN_ROCKET_CANN_VALUES = {}

# ── BHO BADDER/SHATTER: phase → BPR write-back mapping (BPR-BHO-001 v2.0) ──
# Maps the REWRITTEN bho_badder phases (receive-and-package) to the sheet's
# Section 6. Sheet steps 5 (Badder portion) and 6–7 (Shatter portion+seal) are
# SKU-specific — a given batch is one or the other. The timestamp fan-out below
# will stamp all of [5,6,7] for the portioning phase regardless of SKU; that's a
# known limitation (a Badder batch shows Shatter steps timestamped too). Refine
# later to stamp only operator-completed steps if the auditor flags it.
BHO_PHASE_TO_STEPS = {
    "receiving":          [1, 2],      # receiving verification; SDS review
    "pre_production":     [3, 4],      # ISO-wipe; calibrate scale
    "portioning":         [5, 6, 7],   # Badder portion; Shatter portion; Shatter seal
    "labeling_packaging": [8, 9, 10],  # Badder label; info sticker; 10CT case
    "sanitation":         [11, 12],    # clean-down; METRC entry
}
BHO_CCP_VALUES = {
    ("receiving", 0):           1,   # COA/transfer/intact
    ("receiving", 2):           2,   # SDS reviewed
    ("pre_production", 0):      3,   # tools/surfaces ISO-wiped
    ("portioning", 0):          5,   # Badder fill weight
    ("portioning", 1):          6,   # Shatter portion weight
    ("portioning", 2):          7,   # Shatter seal
    ("labeling_packaging", 1):  9,   # label verification
    ("sanitation", 1):          12,  # METRC entry within 24h
}
# Bulk BHO weight is recorded by hand in Section 2 (supervisor sign-off block),
# same as Rocket — no in-production cannabis-weight CCP to fan out.
BHO_CANN_VALUES = {}

# For all products below: Section 2 cannabis weights are recorded by hand
# (supervisor sign-off block, "complete BEFORE production"), so CANN maps are
# empty — the in-production cannabis-weight CCPs land on their Section 6 STEP
# VALUE cells like every other CCP, not on Section 2.

# ── TEMPO DIAMONDS (BPR-DIA-001, 10 steps) ──
TEMPO_DIAMONDS_PHASE_TO_STEPS = {
    "receiving_verification": [1],        # COA/transfer/intact
    "pre_production_prep":    [2],        # ISO-wipe tools/tables/jars
    "component_blend":        [3, 4],     # weigh 4 components; mix uniform
    "portioning":             [5],        # portion 1.0-1.05 g/jar
    "labeling_packaging":     [6, 7, 8],  # cap+stickers; info sticker; 10CT case
    "sanitation":             [9, 10],    # clean-down/UV; METRC
}
TEMPO_DIAMONDS_CCP_VALUES = {
    ("receiving_verification", 0): 1, ("receiving_verification", 1): 1,
    ("component_blend", 1): 3, ("component_blend", 3): 4,
    ("portioning", 1): 5,
    ("labeling_packaging", 2): 7, ("labeling_packaging", 3): 7,
    ("sanitation", 3): 10,
}

# ── ROSIN VAPE DECARB (BPR-RVP-001, 16 steps) ──
ROSIN_VAPE_DECARB_PHASE_TO_STEPS = {
    "pre_production":   [1, 2, 3],    # ISO-flush; verify rosin COA; calibrate/set fill
    "decarboxylation":  [4, 5, 6],    # decarb day 1/2/3+
    "blend":            [7],          # 1g SKU distillate blend
    "fill_calibration": [8, 9],       # load/purge; pre-run fill calibration
    "filling":          [10, 11],     # load rack fill; squish cap
    "packaging":        [12, 13, 14], # CR pkg heat-seal; info sticker; 20CT case
    "sanitation":       [15, 16],     # clean-down; METRC
}
ROSIN_VAPE_DECARB_CCP_VALUES = {
    ("pre_production", 1): 2,
    ("decarboxylation", 0): 4, ("decarboxylation", 4): 6,
    ("blend", 1): 7,
    ("fill_calibration", 1): 9,
    ("filling", 2): 11,
    ("packaging", 1): 13,
    ("sanitation", 4): 16,
}

# ── STINGER PRE-ROLLS (BPR-STG-001, 17 steps) ──
STINGER_PHASE_TO_STEPS = {
    "pre_production":        [1, 2, 3],   # ISO-clean; verify 3 COAs; jar strain sticker
    "grind_and_coat":        [4, 5, 6],   # grind; spray; painting mix
    "cone_fill_calibration": [7, 8, 9],   # ActionPac cal; fill spot-weigh; twist close
    "painting_and_kief":     [10, 11],    # painting coat; kief rolling
    "drying":                [12],        # 4-6 hr drying
    "qc_jarring":            [13],        # verify dry, jar
    "labeling_packaging":    [14, 15],    # info sticker; 25CT case
    "sanitation":            [16, 17],    # clean-down; METRC
}
STINGER_CCP_VALUES = {
    ("pre_production", 0): 1, ("pre_production", 1): 2, ("pre_production", 3): 3,
    ("grind_and_coat", 1): 5,
    ("cone_fill_calibration", 1): 7, ("cone_fill_calibration", 2): 8,
    ("painting_and_kief", 0): 10, ("painting_and_kief", 1): 11,
    ("drying", 3): 12,
    ("qc_jarring", 0): 13,
    ("labeling_packaging", 0): 14,
    ("sanitation", 3): 17,
}

# ── COOKIE DELIGHT (BPR-CKD-001, 14 steps) ──
COOKIE_DELIGHT_PHASE_TO_STEPS = {
    "pre_production":         [1, 2, 3, 4], # dry sanit; COA; cookie count&type; preheat tunnel
    "temper":                [5],           # melt chocolate 100-108F
    "cannabis_incorporation": [6],          # cannabis incorporation
    "pour_and_cookie_embed":  [7, 8, 9],    # pour1; cookie embed; pour2
    "demold_qc":             [10, 11],      # demold; unit weight spot-check
    "labeling_packaging":    [12],          # videojet+ilapak+label
    "sanitation":            [13, 14],      # clean-down; METRC
}
COOKIE_DELIGHT_CCP_VALUES = {
    ("pre_production", 0): 1, ("pre_production", 1): 2, ("pre_production", 3): 3,
    ("pre_production", 4): 3, ("pre_production", 5): 4,
    ("temper", 1): 5,
    ("cannabis_incorporation", 0): 6, ("cannabis_incorporation", 1): 6,
    ("pour_and_cookie_embed", 1): 8, ("pour_and_cookie_embed", 5): 9,
    ("demold_qc", 1): 11, ("demold_qc", 2): 11,
    ("labeling_packaging", 0): 12, ("labeling_packaging", 1): 12,
    ("sanitation", 3): 14,
}

# ── MALT BALLS (BPR-MLT-001, 20 steps, 2-day process) ──
MALT_BALLS_PHASE_TO_STEPS = {
    "pre_production_day1":      [1, 2, 3],       # panner clean; COA; day1 humidity
    "chocolate_cannabis_prep":  [4],             # melt choc + hash
    "panning_coat":             [5, 6, 7, 8],    # cold-air load; spray; hot-air; cold-air harden
    "rest_24hr":                [9],             # 24-hr rest
    "day2_setup_and_humidity":  [10, 11],        # day2 clean panner; day2 humidity
    "glossing_and_sealing":     [12, 13, 14, 15],# 1st/2nd/3rd gloss; sealing
    "labeling_packaging":       [16, 17, 18],    # videojet; fill tube; CR cap tamper
    "sanitation":               [19, 20],        # clean-down; METRC
}
MALT_BALLS_CCP_VALUES = {
    ("pre_production_day1", 0): 1, ("pre_production_day1", 1): 2, ("pre_production_day1", 3): 3,
    ("chocolate_cannabis_prep", 1): 4, ("chocolate_cannabis_prep", 3): 4,
    ("panning_coat", 1): 5, ("panning_coat", 5): 7, ("panning_coat", 6): 7,
    ("rest_24hr", 3): 9,
    ("day2_setup_and_humidity", 0): 10, ("day2_setup_and_humidity", 1): 11,
    ("glossing_and_sealing", 1): 12, ("glossing_and_sealing", 3): 13, ("glossing_and_sealing", 5): 15,
    ("labeling_packaging", 0): 16, ("labeling_packaging", 6): 18,
    ("sanitation", 3): 20,
}

# ── ASTEROIDS (BPR-AST-001, 17 steps) — own family (see bpr_phases.py) ──
ASTEROIDS_PHASE_TO_STEPS = {
    "pre_production":  [1],           # sanitation
    "ingredient_prep": [2, 3],        # COA; water+gelatin bloom
    "cook":            [4, 5, 6, 7, 8],  # cook + cannabis incorporation
    "depositing":      [9, 10],       # hopper 165F; pour molds
    "pop":             [11],          # 1-hour same-day pop
    "demold":          [12],          # demold within 1 hr
    "coating":         [13, 14],      # bubble bits; air-dry
    "packaging":       [15],          # label + fill CR tin
    "sanitation":      [16, 17],      # clean-down; METRC
}
ASTEROIDS_CCP_VALUES = {
    ("pre_production", 0): 1,
    ("ingredient_prep", 0): 2,
    ("cook", 0): 4, ("cook", 2): 6, ("cook", 4): 8,
    ("depositing", 0): 9,
    ("pop", 0): 11,
    ("demold", 0): 12,
    ("coating", 1): 14,
    ("packaging", 0): 15,
    ("sanitation", 1): 17,
}

# ── CHOCOLATE — Standard (BPR-CHO-001, 17), SF (BPR-SFB-001, 15), PB (BPR-PBC-001, 17) ──
CHOC_STD_PHASE_TO_STEPS = {
    "pre_production":         [1, 2, 3],
    "temper":                [4],
    "cannabis_incorporation": [5, 6],
    "pour_and_mold":          [7, 8, 9],
    "demold_qc":             [10, 11],
    "labeling_packaging":    [12, 13, 14, 15],
    "sanitation":            [16, 17],
}
CHOC_STD_CCP_VALUES = {
    ("pre_production", 0): 1, ("pre_production", 1): 2, ("pre_production", 3): 3,
    ("temper", 1): 4,
    ("cannabis_incorporation", 0): 5, ("cannabis_incorporation", 2): 5,
    ("pour_and_mold", 5): 9,
    ("demold_qc", 2): 11,
    ("labeling_packaging", 0): 12, ("labeling_packaging", 2): 13,
    ("sanitation", 5): 17,
}
CHOC_SF_PHASE_TO_STEPS = {  # roux/temper interleave on the sheet
    "pre_production":              [1, 2, 3],
    "seeding_phases":              [4, 5],
    "roux_cannabis_incorporation": [6, 9],
    "temper_and_snap_test":        [7, 8],
    "pour_87f_hardstop":           [10, 11],
    "demold_qc":                   [12],
    "labeling_packaging":          [13],
    "sanitation":                  [14, 15],
}
CHOC_SF_CCP_VALUES = {
    ("pre_production", 0): 1, ("pre_production", 1): 2, ("pre_production", 3): 3,
    ("seeding_phases", 1): 4, ("seeding_phases", 3): 5,
    ("roux_cannabis_incorporation", 1): 6, ("roux_cannabis_incorporation", 5): 9,
    ("temper_and_snap_test", 1): 7, ("temper_and_snap_test", 3): 8,
    ("pour_87f_hardstop", 1): 10,
    ("demold_qc", 1): 12, ("demold_qc", 3): 12,
    ("labeling_packaging", 0): 13,
    ("sanitation", 3): 15,
}
CHOC_PB_PHASE_TO_STEPS = {
    "pre_production_allergen_clearance":        [1, 2, 3, 4, 5],
    "dual_temper":                              [6, 7],
    "cannabis_incorporation":                   [8, 9],
    "pour_and_mold":                            [10, 11, 12],
    "demold_qc":                                [13],
    "labeling_and_postrun_allergen_clearance":  [14, 15],
    "sanitation":                               [16, 17],
}
CHOC_PB_CCP_VALUES = {
    ("pre_production_allergen_clearance", 0): 1, ("pre_production_allergen_clearance", 3): 2, ("pre_production_allergen_clearance", 5): 4,
    ("dual_temper", 1): 6, ("dual_temper", 2): 7,
    ("cannabis_incorporation", 1): 8,
    ("pour_and_mold", 2): 12,
    ("demold_qc", 0): 13,
    ("labeling_and_postrun_allergen_clearance", 0): 14, ("labeling_and_postrun_allergen_clearance", 2): 15,
    ("sanitation", 2): 17,
}

# ── DR. NORM'S ── cookie/nano (20-step bake), rkt (14-step press), brownie
# (16) / brownie_sleep (17). ⚠ App CCP labels show some infusion temps as 310°F
# while the DN sheets say 320°F — a label drift to verify; does not affect
# write-back (operator's entered value lands in the cell either way).
DN_COOKIE_PHASE_TO_STEPS = {
    "pre_production": [1, 2], "infusion": [3, 4, 5, 6],
    "mixing": [7, 8, 9, 10, 11], "forming": [12, 13, 14],
    "baking": [15], "cooling": [16], "packaging": [17, 18, 19], "qc_release": [20],
}
DN_COOKIE_CCP_VALUES = {
    ("pre_production", 1): 1, ("pre_production", 4): 2,
    ("infusion", 2): 4, ("infusion", 3): 5, ("infusion", 5): 5, ("infusion", 6): 6,
    ("mixing", 2): 8,
    ("forming", 1): 12, ("forming", 3): 13, ("forming", 5): 14, ("forming", 6): 14,
    ("baking", 0): 15, ("baking", 1): 15,
    ("packaging", 0): 17, ("packaging", 1): 18,
    ("qc_release", 4): 20,
}
DN_COOKIE_NANO_CCP_VALUES = dict(DN_COOKIE_CCP_VALUES)
DN_COOKIE_NANO_CCP_VALUES.pop(("pre_production", 1)); DN_COOKIE_NANO_CCP_VALUES.pop(("pre_production", 4))
DN_COOKIE_NANO_CCP_VALUES[("pre_production", 2)] = 1   # NANO: freezer temp
DN_COOKIE_NANO_CCP_VALUES[("pre_production", 5)] = 2   # NANO: COA potency
DN_RKT_PHASE_TO_STEPS = {
    "pre_production": [1, 2], "infusion": [3], "marshmallow_melt": [4],
    "cereal_mix": [5, 6], "forming": [7, 8], "cooling": [9],
    "cut_and_weigh": [10, 11], "packaging": [12, 13], "qc_release": [14],
}
DN_RKT_CCP_VALUES = {
    ("pre_production", 3): 2,
    ("infusion", 2): 3, ("infusion", 3): 3, ("infusion", 4): 3,
    ("marshmallow_melt", 2): 4,
    ("cereal_mix", 2): 6,
    ("forming", 1): 7,
    ("cut_and_weigh", 1): 11, ("cut_and_weigh", 2): 11,
    ("qc_release", 3): 14,
}
DN_BROWNIE_PHASE_TO_STEPS = {
    "pre_production": [1], "chocolate_melt": [2], "infusion": [3],
    "mixing": [4, 5, 6, 7, 8, 9], "forming": [10, 11], "baking": [12],
    "cooling": [13], "packaging": [14, 15], "qc_release": [16],
}
DN_BROWNIE_CCP_VALUES = {
    ("pre_production", 4): 1,
    ("infusion", 2): 3,
    ("mixing", 1): 5,
    ("forming", 1): 10, ("forming", 3): 11, ("forming", 4): 11,
    ("baking", 0): 12, ("baking", 1): 12,
    ("packaging", 0): 14, ("packaging", 1): 15,
    ("qc_release", 3): 16,
}
DN_BROWNIE_SLEEP_PHASE_TO_STEPS = {
    "pre_production": [1], "chocolate_melt": [2], "infusion": [3, 4],
    "mixing": [5, 6, 7, 8, 9, 10], "forming": [11, 12], "baking": [13],
    "cooling": [14], "packaging": [15, 16], "qc_release": [17],
}
DN_BROWNIE_SLEEP_CCP_VALUES = {
    ("pre_production", 5): 1, ("pre_production", 6): 1,
    ("infusion", 1): 3, ("infusion", 2): 3, ("infusion", 3): 4,
    ("mixing", 1): 6,
    ("forming", 1): 11, ("forming", 3): 12, ("forming", 4): 12,
    ("baking", 0): 13, ("baking", 1): 13,
    ("packaging", 0): 15, ("packaging", 1): 16,
    ("qc_release", 3): 17, ("qc_release", 4): 17,
}

# ── DISTILLATE VAPE / TEMPO AIO (BPR-DVP-001, 14 steps) — "vapes" family ──
VAPES_PHASE_TO_STEPS = {
    "pre_production":   [1, 2, 3],   # ISO-flush; COA; calibrate/set 1.0g
    "source_prep":      [4, 5, 6],   # water bath+terpenes; weigh; immersion blend
    "fill_calibration": [7, 8],      # load/purge; pre-run fill calibration
    "filling":          [9, 10],     # load rack fill; squish cap
    "packaging":        [11, 12],    # label; 20CT case
    "sanitation":       [13, 14],    # clean-down ISO flush; METRC
}
VAPES_CCP_VALUES = {
    ("pre_production", 2): 2, ("pre_production", 5): 3,
    ("source_prep", 0): 4, ("source_prep", 2): 5, ("source_prep", 3): 6,
    ("fill_calibration", 1): 8,
    ("filling", 2): 10,
    ("packaging", 1): 11, ("packaging", 3): 12,
    ("sanitation", 4): 14,
}

# ── TEMPO LIVE RESIN VAPE (BPR-TLR-001, 15 steps) — own family, own tab ──
TEMPO_LR_VAPE_PHASE_TO_STEPS = {
    "receiving_verification": [1],       # both COAs / transfers
    "pre_production":         [2, 3, 4], # ISO-flush; record both UIDs; calibrate 1.0g
    "source_prep":            [5, 6, 7], # water bath/HTE; weigh both; immersion blend
    "fill_calibration":       [8, 9],    # load/purge; pre-run calibration
    "filling":                [10, 11],  # load rack fill; squish cap
    "packaging":              [12, 13],  # mylar label; 20CT case
    "sanitation":             [14, 15],  # clean-down; METRC
}
TEMPO_LR_VAPE_CCP_VALUES = {
    ("receiving_verification", 0): 1,
    ("pre_production", 0): 2, ("pre_production", 1): 3, ("pre_production", 2): 4,
    ("source_prep", 0): 5, ("source_prep", 1): 6, ("source_prep", 2): 7,
    ("fill_calibration", 0): 8, ("fill_calibration", 1): 9,
    ("filling", 1): 11,
    ("packaging", 0): 12,
    ("sanitation", 1): 15,
}

# ── LIQUIDABS (BPR-LQD-NANO-001, 26 steps) — extended cell map (15,26) ──
# ⚠ Assumes Section 6 step rows start at the standard row 71 (STEP{n} → row
# 70+n). Verify against the real tab before trusting (see smoke-test note).
LIQUIDABS_PHASE_TO_STEPS = {
    "sanitation_setup": [1, 2, 3, 4, 5, 6],
    "oil_phase":        [7, 8, 9],
    "aqueous_phase":    [10, 11, 12, 13],
    "coarse_emulsion":  [14, 15],
    "ultrasonic":       [16, 17, 18, 19],
    "verification":     [20, 21, 22],
    "filling_packaging": [23, 24],
    "post_run":         [25, 26],
}
LIQUIDABS_CCP_VALUES = {
    ("sanitation_setup", 0): 1, ("sanitation_setup", 1): 2, ("sanitation_setup", 2): 3,
    ("sanitation_setup", 3): 4, ("sanitation_setup", 4): 5,
    ("oil_phase", 0): 7, ("oil_phase", 2): 9,
    ("aqueous_phase", 1): 11, ("aqueous_phase", 2): 12, ("aqueous_phase", 3): 13,
    ("coarse_emulsion", 0): 14,
    ("ultrasonic", 1): 17, ("ultrasonic", 2): 18,
    ("verification", 0): 20, ("verification", 1): 21, ("verification", 2): 22,
    ("filling_packaging", 0): 23, ("filling_packaging", 1): 24,
    ("post_run", 0): 25, ("post_run", 1): 26,
}

# ── NANO-ISOLATE COMPONENT (BPR-DNANO-001, 28 steps) — extended cell map (15,28) ──
NANO_ISOLATE_PHASE_TO_STEPS = {
    "sanitation_setup":    [1, 2, 3, 4, 5, 6],
    "isolate_dissolution": [7, 8, 9, 10, 11],
    "aqueous_phase":       [12, 13, 14, 15],
    "coarse_emulsion":     [16, 17],
    "ultrasonic":          [18, 19, 20, 21],
    "verification":        [22, 23, 24],
    "component_release":   [25, 26],
    "post_run":            [27, 28],
}
NANO_ISOLATE_CCP_VALUES = {
    ("sanitation_setup", 0): 1, ("sanitation_setup", 1): 2, ("sanitation_setup", 2): 3,
    ("sanitation_setup", 3): 4, ("sanitation_setup", 4): 5,
    ("isolate_dissolution", 0): 7, ("isolate_dissolution", 2): 9, ("isolate_dissolution", 3): 10,
    ("aqueous_phase", 1): 13, ("aqueous_phase", 2): 14, ("aqueous_phase", 3): 15,
    ("coarse_emulsion", 0): 16,
    ("ultrasonic", 1): 19, ("ultrasonic", 2): 20,
    ("verification", 0): 22, ("verification", 1): 23, ("verification", 2): 24,
    ("component_release", 0): 25, ("component_release", 1): 26,
    ("post_run", 0): 27, ("post_run", 1): 28,
}

# ── Per-family lookup registries ──
PHASE_TO_STEPS_MAPS = {
    "gummies":                GUMMIES_PHASE_TO_STEPS,
    "rosin_press":            LIVE_ROSIN_PHASE_TO_STEPS,
    "rosin_rocket":           ROSIN_ROCKET_PHASE_TO_STEPS,
    "bho_badder":             BHO_PHASE_TO_STEPS,
    "tempo_diamonds":         TEMPO_DIAMONDS_PHASE_TO_STEPS,
    "rosin_vape_decarb":      ROSIN_VAPE_DECARB_PHASE_TO_STEPS,
    "punch_stinger":          STINGER_PHASE_TO_STEPS,
    "punch_cookie_delight":   COOKIE_DELIGHT_PHASE_TO_STEPS,
    "punch_malt_balls":       MALT_BALLS_PHASE_TO_STEPS,
    "asteroids":              ASTEROIDS_PHASE_TO_STEPS,
    "punch_chocolate":        CHOC_STD_PHASE_TO_STEPS,
    "punch_chocolate_sf":     CHOC_SF_PHASE_TO_STEPS,
    "punch_chocolate_pb":     CHOC_PB_PHASE_TO_STEPS,
    "dr_norms_cookie":        DN_COOKIE_PHASE_TO_STEPS,
    "dr_norms_cookie_nano":   DN_COOKIE_PHASE_TO_STEPS,
    "dr_norms_rkt":           DN_RKT_PHASE_TO_STEPS,
    "dr_norms_brownie":       DN_BROWNIE_PHASE_TO_STEPS,
    "dr_norms_brownie_sleep": DN_BROWNIE_SLEEP_PHASE_TO_STEPS,
    "vapes":                  VAPES_PHASE_TO_STEPS,
    "tempo_lr_vape":          TEMPO_LR_VAPE_PHASE_TO_STEPS,
    "liquidabs":              LIQUIDABS_PHASE_TO_STEPS,
    "nano_isolate":           NANO_ISOLATE_PHASE_TO_STEPS,
}
CCP_VALUES_MAPS = {
    "gummies":                GUMMIES_CCP_VALUES,
    "rosin_press":            LIVE_ROSIN_CCP_VALUES,
    "rosin_rocket":           ROSIN_ROCKET_CCP_VALUES,
    "bho_badder":             BHO_CCP_VALUES,
    "tempo_diamonds":         TEMPO_DIAMONDS_CCP_VALUES,
    "rosin_vape_decarb":      ROSIN_VAPE_DECARB_CCP_VALUES,
    "punch_stinger":          STINGER_CCP_VALUES,
    "punch_cookie_delight":   COOKIE_DELIGHT_CCP_VALUES,
    "punch_malt_balls":       MALT_BALLS_CCP_VALUES,
    "asteroids":              ASTEROIDS_CCP_VALUES,
    "punch_chocolate":        CHOC_STD_CCP_VALUES,
    "punch_chocolate_sf":     CHOC_SF_CCP_VALUES,
    "punch_chocolate_pb":     CHOC_PB_CCP_VALUES,
    "dr_norms_cookie":        DN_COOKIE_CCP_VALUES,
    "dr_norms_cookie_nano":   DN_COOKIE_NANO_CCP_VALUES,
    "dr_norms_rkt":           DN_RKT_CCP_VALUES,
    "dr_norms_brownie":       DN_BROWNIE_CCP_VALUES,
    "dr_norms_brownie_sleep": DN_BROWNIE_SLEEP_CCP_VALUES,
    "vapes":                  VAPES_CCP_VALUES,
    "tempo_lr_vape":          TEMPO_LR_VAPE_CCP_VALUES,
    "liquidabs":              LIQUIDABS_CCP_VALUES,
    "nano_isolate":           NANO_ISOLATE_CCP_VALUES,
}
# CANN maps only for families that capture cannabis weight in-production
# (gummies/rosin_press). Everything else defaults to {} via .get() — their
# Section 2 cannabis weights are recorded by hand pre-production.
CANN_VALUES_MAPS = {
    "gummies":      GUMMIES_CANN_VALUES,
    "rosin_press":  LIVE_ROSIN_CANN_VALUES,
    "rosin_rocket": ROSIN_ROCKET_CANN_VALUES,
    "bho_badder":   BHO_CANN_VALUES,
}

async def push_phase_to_gas_bpr(uid: str, phase_id: str, phase_def: dict,
                                  signoff: dict, steps: list, product_family: str):
    """
    Writes a signed-off phase to its BPR sheet via direct cell-map addressing
    (successor to the old named-range approach — see session notes on why
    named ranges failed in production for both live_rosin and rosin_wash's
    Section 6 attempt). Three write categories per phase:
      1. Timestamp fan-out — every sheet step a phase covers gets DATE/OP1/VERIFIED
      2. CCP values — specific checklist numbers landing on one STEPn's VALUE
      3. Cannabis-row values — writes into Section 2 (CANNn_*), not Section 6
    """
    webhook_url = os.environ.get("GAS_WEBHOOK_URL")
    if not webhook_url:
        print("No GAS_WEBHOOK_URL — skipping BPR write-back")
        return

    if product_family == "rosin_wash":
        await push_wash_phase_to_gas(uid, phase_id, phase_def, signoff, steps)
        return

    template_key = PRODUCT_FAMILY_TO_TEMPLATE_KEY.get(product_family)
    if not template_key:
        print(f"BPR write-back not yet implemented for {product_family} — skipping")
        return

    phase_to_steps = PHASE_TO_STEPS_MAPS.get(product_family, {})
    ccp_value_map  = CCP_VALUES_MAPS.get(product_family, {})
    cann_value_map = CANN_VALUES_MAPS.get(product_family, {})

    if not phase_to_steps:
        print(f"No PHASE_TO_STEPS map defined for {product_family} yet — skipping write-back")
        return

    step_lookup = {s["step_index"]: s for s in steps if s["phase_id"] == phase_id}
    signed_at = fmt_ts(signoff.get("signed_at")) or ""
    employee  = signoff.get("employee_name") or ""

    ccp_values = signoff.get("ccp_values") or {}
    if isinstance(ccp_values, str):
        try: ccp_values = json.loads(ccp_values)
        except Exception: ccp_values = {}

    fields = {}

    # ── 1. Timestamp fan-out — every sheet step this phase covers ──
    sheet_steps = phase_to_steps.get(phase_id, [])
    date_part, time_part = "", ""
    if signed_at:
        date_part, _, time_part = signed_at.partition(" ")
    for sheet_step_num in sheet_steps:
        prefix = f"STEP{sheet_step_num}"
        fields[prefix + "_DATE"]     = date_part
        fields[prefix + "_END"]      = time_part  # phase signoff = step completion time
        fields[prefix + "_OP1"]      = employee
        fields[prefix + "_VERIFIED"] = "✓"

    # ── 2. CCP-specific values — group by target sheet step, concatenate ──
    step_value_parts = {}  # sheet_step_num -> list of "label: value" strings
    ccp_labels = phase_def.get("ccp_labels", {})
    for (p_id, step_idx), sheet_step_num in ccp_value_map.items():
        if p_id != phase_id:
            continue
        val = ccp_values.get(str(step_idx))
        if val is None:
            val = ccp_values.get(step_idx, "")
        if val in (None, ""):
            continue
        label = str(ccp_labels.get(step_idx, f"Item {step_idx}")).split("—")[0].split("(")[0].strip()
        step_value_parts.setdefault(sheet_step_num, []).append(f"{label}: {val}")

    for sheet_step_num, parts in step_value_parts.items():
        prefix = f"STEP{sheet_step_num}"
        fields[prefix + "_VALUE"]    = " | ".join(parts)
        fields[prefix + "_PASSFAIL"] = "Pass"

    # ── 3. Cannabis-row values — Section 2, not Section 6 ──
    for (p_id, step_idx), cann_prefix in cann_value_map.items():
        if p_id != phase_id:
            continue
        step_data = step_lookup.get(step_idx, {})
        checked_at = fmt_ts(step_data.get("checked_at")) if step_data.get("checked_at") else signed_at
        checked_by = step_data.get("checked_by") or employee
        val = ccp_values.get(str(step_idx))
        if val is None:
            val = ccp_values.get(step_idx, "")

        fields[cann_prefix + "_ACTUALQTY"]  = val
        fields[cann_prefix + "_WEIGHEDBY"]  = checked_by
        fields[cann_prefix + "_TIME"]       = checked_at[-8:] if checked_at else ""

    # ── 3b. COA attestation → Section 2, row 1 (lightweight, ALL families) ──
    # We deliberately do NOT re-key every component COA into every batch BPR:
    # the source COA lives on the batch, and its potency is already captured via
    # the CCP flow (lands on a STEP value cell). Section 2 only needs a CONCURRENT
    # record that the COA was verified present, and by whom — §17216(c). So detect
    # the standardized "COA confirmed/received" checklist step in this phase and
    # stamp Cannabis row 1's Time + Verified By.
    #
    # ASSUMPTIONS (flagged intentionally): (1) always row 1 (CANN1) — the primary
    # cannabis input; multi-source products (e.g. PBC-100 hash) would need a second
    # row wired later. (2) setdefault, so any family with an explicit cann_value_map
    # (richer CANN1 data above) wins over this fallback rather than double-writing.
    import re as _re
    _coa_re = _re.compile(r"COA (confirmed|received|verified)", _re.I)
    for _idx, _text in enumerate(phase_def.get("steps", [])):
        if not _coa_re.search(_text or ""):
            continue
        _sd = step_lookup.get(_idx, {})
        if _sd.get("checked"):
            _when = fmt_ts(_sd.get("checked_at")) or signed_at
            fields.setdefault("CANN1_TIME",       _when or "")
            fields.setdefault("CANN1_VERIFIEDBY", _sd.get("checked_by") or employee)
        break

    if not fields:
        print(f"push_phase_to_gas_bpr: no mapped fields for phase {phase_id} [{product_family}]")
        return

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.post(webhook_url, json={
                "action":      "writeBPRFieldsByCellMap",
                "uid":         uid,
                "templateKey": template_key,
                "fields":      fields,
                "secret":      os.environ.get("GAS_SHARED_SECRET", ""),
            })
            print(f"GAS BPR write-back: {resp.status_code} — {resp.text[:200]}")
    except Exception as e:
        print(f"GAS BPR write-back failed (non-fatal) [uid={uid}]: {describe_exc(e)}")


async def push_release_summary_bpr(rec: dict, supervisor_name: str, total_yield):
    """
    Section 3 (Yield & Label Count) write-back for the CELL-MAPPED standardized
    BPRs — the non-wash counterpart to push_wash_release_summary(), which only
    handles the named-range wash sheet.

    Writes the unit-yield row (Section 3 row 1 = sheet row 42) via the standard
    cell-map fields resolved by buildStandardBPRCellMap() in BPR.gs:
      • YIELD1_ACTUAL   ← total_yield captured at supervisor release (Final Qty, D42)
      • YIELD1_EXPECTED ← the batch's Target Qty from UID_TRACKER  (Expected,   C42)
      • YIELD1_INITIALS ← supervisor (J42);  YIELD1_TIME ← release timestamp (K42)

    Fire-and-forget (via _post_wash_gas): a Sheets or tracker-read hiccup can
    never block or fail a release that has already committed.
    """
    product_family = rec.get("product_family")
    template_key = PRODUCT_FAMILY_TO_TEMPLATE_KEY.get(product_family)
    if not template_key:
        print(f"release summary: no template key for {product_family} — skipping S3 write")
        return

    fields = {
        "YIELD1_ACTUAL":   total_yield or "",
        "YIELD1_INITIALS": supervisor_name,
        "YIELD1_TIME":     fmt_ts(datetime.now(timezone.utc)) or "",
    }

    # Expected (Target) lives on UID_TRACKER, keyed by the source METRC tag.
    # Ideally C42 is also stamped at sheet-creation time so operators see the
    # target BEFORE production; sending it here as well guarantees it's filled
    # even on sheets created before that creation-time wiring exists.
    try:
        mu = rec.get("metrc_uid")
        if mu:
            from sheets_client import get_sheets_client
            batch = get_sheets_client().get_batch_by_uid(mu)
            if batch and batch.get("targetQty") not in (None, ""):
                fields["YIELD1_EXPECTED"] = batch["targetQty"]
    except Exception as e:
        print(f"release summary: target-qty lookup failed (non-fatal): {e}")

    await _post_wash_gas({
        "action":      "writeBPRFieldsByCellMap",
        "uid":         rec["uid"],
        "templateKey": template_key,
        "fields":      fields,
    }, f"BPR release summary ({product_family})")


# ═══════════════════════════════════════════════════════════════════════════
# ROSIN WASH → GOOGLE SHEET WRITE-BACK
# Three write paths into the wash BPR sheet, mirroring how the paperwork flows:
#   1. Phase signoff       → Section 6 step rows   (named ranges WASH_S6_STEP{n}_*)
#   2. Session close       → 'Ice Extraction Session Log' tab (row append via GAS)
#   3. Supervisor release  → Section 2/3 rollups   (WASH_S2_* / WASH_S3_*)
# All fire-and-forget: a Sheets hiccup never blocks an operator mid-production.
# GAS side: serverWriteWashBPRFields / serverAppendWashSessionLog
# ═══════════════════════════════════════════════════════════════════════════

# App (phase_id, step_index) → Section 6 sheet step row, for per-step phases.
# pre_production app steps 1-8 map to sheet rows 1-8; sanitation's 7 app steps
# map to sheet rows 12-18. Rows 9-11 are the multi-session summary rows below.
WASH_S6_PER_STEP_ROWS = {
    "pre_production": {i: i + 1 for i in range(8)},
    "sanitation":     {i: i + 12 for i in range(7)},
}
# Multi-session phases collapse to one summary row on the sheet — the full
# per-session detail lives in the Session Log tab, not Section 6.
WASH_S6_SUMMARY_ROWS = {"ice_water_wash": 9, "freeze_drying": 10, "sifting": 11}


# ── Section 4: equipment rows attested by existing pre-production steps ──
# Many-to-one: one app checkbox covers several equipment rows.
# step_index → list of S4 equipment row numbers (1-6 on the sheet)
WASH_S4_FROM_STEPS = {
    2: [1, 4, 5, 6],  # "Verify all equipment clean..." → Washer, Scale*, Sift Screens, Vac Sealer
    3: [2],           # "Inspect bubble bags"           → Bubble Bags
    4: [3],           # "Freeze dryer pre-cooled/oil"   → Freeze Dryer(s)
}

def _get_wash_sheet_url(lot_code: str) -> Optional[str]:
    """
    The wash BPR sheet URL is stored on the component lot at UID-assignment
    time. Sending it to GAS lets the handler openByUrl() — deterministic,
    same lesson as the COA folder fix: never locate documents by name search.
    """
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT sheet_url FROM bpr_component_lots WHERE lot_code = %s",
                        (lot_code,))
            row = cur.fetchone()
            return row["sheet_url"] if row else None
    finally:
        conn.close()


# _post_wash_gas moved to utils.py — it's shared by both this router and
# components.py, and centralizing it there makes the shared-secret injection
# a single chokepoint (see utils.py for the full rationale). Imported at the
# top of this file now instead of defined inline.


def _wash_block_stats(lot_code: str, phase_id: str):
    """
    Session rollups for a multi-session phase's summary row: a readable
    summary string plus the block's start/end timestamps.
    """
    conn = get_db()
    try:
        with conn.cursor() as cur:
            if phase_id == "ice_water_wash":
                cur.execute("""
                    SELECT COUNT(*) AS n, COALESCE(SUM(wet_weight_g),0) AS total,
                           MIN(started_at) AS s, MAX(completed_at) AS e
                    FROM hash_lot_wash_sessions WHERE hash_lot_id = %s
                """, (lot_code,))
                r = cur.fetchone()
                return (f"{r['n']} session(s) | {float(r['total']):,.0f} g wet collected",
                        fmt_ts(r["s"]), fmt_ts(r["e"]))
            if phase_id == "freeze_drying":
                cur.execute("""
                    SELECT COUNT(*) AS n, COALESCE(SUM(input_wet_weight_g),0) AS wet,
                           COALESCE(SUM(output_dry_weight_g),0) AS dry,
                           MIN(started_at) AS s, MAX(completed_at) AS e
                    FROM hash_lot_freezedry_sessions WHERE hash_lot_id = %s
                """, (lot_code,))
                r = cur.fetchone()
                return (f"{r['n']} load(s) | in {float(r['wet']):,.0f} g wet → out {float(r['dry']):,.0f} g dry",
                        fmt_ts(r["s"]), fmt_ts(r["e"]))
            if phase_id == "sifting":
                cur.execute("""
                    SELECT COUNT(*) AS n, COALESCE(SUM(dry_weight_in_g),0) AS din,
                           COALESCE(SUM(sift_weight_out_g),0) AS dout,
                           MAX(completed_at) AS e
                    FROM hash_lot_sift_sessions WHERE hash_lot_id = %s
                """, (lot_code,))
                r = cur.fetchone()
                return (f"{r['n']} sift(s) | in {float(r['din']):,.0f} g → final {float(r['dout']):,.0f} g",
                        None, fmt_ts(r["e"]))
    finally:
        conn.close()
    return ("", None, None)


async def push_wash_phase_to_gas(uid: str, phase_id: str, phase_def: dict,
                                 signoff: dict, steps: list):
    """Writes a signed-off rosin_wash phase into Section 6 of the wash BPR sheet."""
    sheet_url = _get_wash_sheet_url(uid)
    if not sheet_url:
        print(f"wash write-back: no sheet_url on lot {uid} — skipping")
        return

    signed_at  = fmt_ts(signoff.get("signed_at")) or ""
    employee   = signoff.get("employee_name") or ""
    ccp_values = signoff.get("ccp_values") or {}
    if isinstance(ccp_values, str):
        try: ccp_values = json.loads(ccp_values)
        except Exception: ccp_values = {}

    step_map = {s["step_index"]: s for s in steps if s["phase_id"] == phase_id}
    fields = {}

    # Per-step phases: every checklist row gets date / operator / checkmark
    for step_idx, sheet_row in WASH_S6_PER_STEP_ROWS.get(phase_id, {}).items():
        sd = step_map.get(step_idx, {})
        checked_at = fmt_ts(sd.get("checked_at")) or signed_at
        date_part, _, time_part = (checked_at or "").partition(" ")
        prefix = f"WASH_S6_STEP{sheet_row}"
        fields[prefix + "_DATE"]     = date_part
        fields[prefix + "_START"]    = time_part
        fields[prefix + "_OP1"]      = sd.get("checked_by") or employee
        fields[prefix + "_VERIFIED"] = "✓" if sd.get("checked") else ""

    # Section 4 equipment rows: fan out the pre-production attestations
    if phase_id == "pre_production":
        for step_idx, s4_rows in WASH_S4_FROM_STEPS.items():
            sd = step_map.get(step_idx, {})
            if not sd.get("checked"):
                continue
            when = fmt_ts(sd.get("checked_at")) or signed_at
            for r in s4_rows:
                p = f"WASH_S4_ROW{r}"
                fields[p + "_CHECKEDBY"] = sd.get("checked_by") or employee
                fields[p + "_TIME"]      = when

    # Multi-session phases: one summary row, detail lives in the Session Log
    sheet_row = WASH_S6_SUMMARY_ROWS.get(phase_id)
    if sheet_row:
        summary, block_start, block_end = _wash_block_stats(uid, phase_id)

        # Compact CCP readout for the Value cell: "Tea bag fill weight: 4010; ..."
        labels = phase_def.get("ccp_labels", {})
        ccp_bits = []
        for idx in phase_def.get("ccps", []):
            val = ccp_values.get(str(idx)) if ccp_values.get(str(idx)) is not None else ccp_values.get(idx)
            if val not in (None, ""):
                short = str(labels.get(idx, f"CCP {idx}")).split("—")[0].split("(")[0].strip()
                ccp_bits.append(f"{short}: {val}")
        value = summary + ((" | " + "; ".join(ccp_bits)) if ccp_bits else "")

        prefix = f"WASH_S6_STEP{sheet_row}"
        fields[prefix + "_DATE"]     = signed_at[:10] if signed_at else ""
        fields[prefix + "_OP1"]      = employee
        fields[prefix + "_VERIFIED"] = "✓"
        fields[prefix + "_VALUE"]    = value
        if block_start: fields[prefix + "_START"] = block_start
        if block_end:   fields[prefix + "_END"]   = block_end

        # Pass/Fail: sifting has a numeric spec we can actually check (yield
        # 0.5-25% per ccp_specs); other summary rows pass by virtue of the
        # signoff having cleared the app's CCP validation.
        passfail = "Pass"
        if phase_id == "sifting":
            y = ccp_values.get("1") if ccp_values.get("1") is not None else ccp_values.get(1)
            import re as _re
            m = _re.search(r"(\d+(?:\.\d+)?)\s*%", str(y or "")) or _re.search(r"(\d+(?:\.\d+)?)", str(y or ""))
            if m:
                passfail = "Pass" if 0.5 <= float(m.group(1)) <= 25 else "FAIL"
            else:
                passfail = "Pass" if y not in (None, "") else ""
        fields[prefix + "_PASSFAIL"] = passfail

    if not fields:
        print(f"wash write-back: nothing to write for phase {phase_id}")
        return

    await _post_wash_gas({
        "action":   "writeWashBPRFields",
        "uid":      uid,
        "sheetUrl": sheet_url,
        "fields":   fields,
    }, f"wash BPR write-back ({phase_id})")


async def push_wash_session_row(lot_code: str, block: str, row: dict):
    """Mirrors one closed session as a row in the Session Log tab."""
    sheet_url = _get_wash_sheet_url(lot_code)
    if not sheet_url:
        print(f"session log: no sheet_url on lot {lot_code} — skipping")
        return
    await _post_wash_gas({
        "action":   "appendWashSessionLog",
        "uid":      lot_code,
        "sheetUrl": sheet_url,
        "block":    block,
        "row":      row,
    }, f"session log append ({block})")


async def push_wash_release_summary(uid: str, supervisor_name: str):
    """
    At supervisor release: Section 2 source summary, Section 3 yield
    rollups, and Section 8 auto-verifiable QC checks (rows 2-6).
    """
    sheet_url = _get_wash_sheet_url(uid)
    if not sheet_url:
        print(f"release summary: no sheet_url on lot {uid} — skipping")
        return

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) AS n, COALESCE(SUM(wet_weight_g),0) AS wet,
                       COUNT(*) FILTER (WHERE fresh_frozen_uids IS NULL
                                        OR COALESCE(array_length(fresh_frozen_uids,1),0) = 0) AS missing_uids,
                       COUNT(*) FILTER (WHERE ro_water_confirmed IS NOT TRUE) AS no_ro
                FROM hash_lot_wash_sessions WHERE hash_lot_id = %s
            """, (uid,))
            wash = cur.fetchone()

            cur.execute("""
                SELECT COUNT(DISTINCT u) AS n FROM (
                    SELECT unnest(fresh_frozen_uids) AS u
                    FROM hash_lot_wash_sessions WHERE hash_lot_id = %s
                ) x
            """, (uid,))
            ff = cur.fetchone()

            cur.execute("""
                SELECT COUNT(*) AS n, COALESCE(SUM(output_dry_weight_g),0) AS dry,
                       COUNT(*) FILTER (WHERE pump_oil_checked IS NOT TRUE) AS no_oil
                FROM hash_lot_freezedry_sessions WHERE hash_lot_id = %s
            """, (uid,))
            fd = cur.fetchone()

            cur.execute("""
                SELECT COUNT(*) AS n, COALESCE(SUM(sift_weight_out_g),0) AS sift,
                       COUNT(*) FILTER (WHERE storage_location IS NOT NULL
                                        AND storage_location <> '') AS with_loc
                FROM hash_lot_sift_sessions WHERE hash_lot_id = %s
            """, (uid,))
            sift = cur.fetchone()

            cur.execute("SELECT storage_location FROM bpr_component_lots WHERE lot_code = %s", (uid,))
            lot_row = cur.fetchone() or {}
    finally:
        conn.close()

    wet, dry, out = float(wash["wet"]), float(fd["dry"]), float(sift["sift"])
    yield_pct = round(out / wet * 100, 2) if wet > 0 else ""
    now_str = fmt_ts(datetime.now(timezone.utc))
    today   = datetime.now(timezone.utc).strftime("%m/%d/%Y")

    # ── Sections 2 + 3 (unchanged from previous version) ──────────────────
    fields = {
        "WASH_S2_TOTAL_SESSIONS": wash["n"],
        "WASH_S2_TOTAL_FF_UIDS":  ff["n"],
        "WASH_S2_TOTAL_WET_G":    wet,
        "WASH_S2_VERIFIED_BY":    supervisor_name,
        "WASH_S2_VERIFIED_DATE":  today,
        "WASH_S3_WET_ACTUAL":      wet,       "WASH_S3_WET_INITIALS":      supervisor_name, "WASH_S3_WET_TIME":      now_str,
        "WASH_S3_DRY_ACTUAL":      dry,       "WASH_S3_DRY_INITIALS":      supervisor_name, "WASH_S3_DRY_TIME":      now_str,
        "WASH_S3_SIFT_ACTUAL":     out,       "WASH_S3_SIFT_INITIALS":     supervisor_name, "WASH_S3_SIFT_TIME":     now_str,
        "WASH_S3_YIELDPCT_ACTUAL": yield_pct, "WASH_S3_YIELDPCT_INITIALS": supervisor_name, "WASH_S3_YIELDPCT_TIME": now_str,
    }

    # ── Section 8 auto-verification (rows 2-6) ────────────────────────────
    # Each check: (row, pass_condition, result_text)
    storage_ok = bool((lot_row.get("storage_location") or "").strip()) or sift["with_loc"] > 0
    yield_ok = isinstance(yield_pct, float) and 0.5 <= yield_pct <= 25

    s8_checks = [
        (2, wash["missing_uids"] == 0 and wash["n"] > 0,
            f"{wash['n']} session(s), {ff['n']} distinct FF UID(s); "
            f"{wash['missing_uids']} session(s) missing UIDs"),
        (3, wash["no_ro"] == 0 and wash["n"] > 0,
            f"{wash['n'] - wash['no_ro']}/{wash['n']} sessions RO-confirmed"),
        (4, fd["no_oil"] == 0 and fd["n"] > 0,
            f"{fd['n'] - fd['no_oil']}/{fd['n']} loads pump-oil-checked"),
        (5, yield_ok,
            f"Overall yield {yield_pct}% (spec 0.5-25%)"),
        (6, storage_ok,
            f"Storage location: {(lot_row.get('storage_location') or '').strip() or 'recorded on sift session' if storage_ok else 'NOT RECORDED'}"),
    ]
    for row, ok, result in s8_checks:
        p = f"WASH_S8_ROW{row}"
        fields[p + "_RESULT"]   = result
        fields[p + "_REVIEWER"] = "BatchD auto-verify"
        fields[p + "_DATETIME"] = now_str
        fields[p + "_PASSFAIL"] = "Pass" if ok else "FAIL"

    await _post_wash_gas({
        "action":   "writeWashBPRFields",
        "uid":      uid,
        "sheetUrl": sheet_url,
        "fields":   fields,
    }, "wash release summary")


# ── WASH SESSIONS ──────────────────────────────────────────────

