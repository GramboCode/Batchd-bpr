"""
routers/components.py — component lot tracking: /components/* and /hash/*.

Moved from bpr_api.py. This is a MECHANICAL split -- every function body,
every SQL string, every route path below is byte-for-byte identical to
what was already running. The only changes are:
  - @app.get/post/patch/delete -> @router.get/post/patch/delete
  - get_db, now_utc, fmt_ts now come from db.py / utils.py instead of
    being defined in this same file
  - one duplicate `class TrayWeighInCreate` definition removed (it was
    defined twice, back to back, identically -- harmless in Python since
    the second silently wins, but there's no reason to carry a dead
    duplicate into the new structure)

This file owns everything about component lots: the generic type
registry, the ledger, and the legacy /hash/* wrapper routes (still used
by the GAS wash page and BatchD frontend today). The wash/freezedry/sift
session + tray-weighin + reconciliation routes live here too, since
they're all component-lot data, not BPR-record data.
"""

import json
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from db import get_db
from auth import require_admin
from utils import now_utc, fmt_ts, _post_wash_gas, call_gas

router = APIRouter(tags=["components"])


async def _push_wash_session_row(lot_code: str, block: str, row: dict):
    """
    Lazy bridge to bpr.push_wash_session_row, which mirrors a just-closed
    wash/freeze-dry/sift session as a row in the wash sheet's Session Log tab.

    It's imported HERE at call time — not at module top — on purpose: bpr.py
    already imports from this module (components), so a top-level
    `from routers.bpr import ...` here would be a circular import and crash on
    boot. That missing import is exactly what made every session close 500 with
    `NameError: push_wash_session_row is not defined`. The call runs inside a
    fire-and-forget asyncio task, so the deferred import cost never matters.
    """
    from routers.bpr import push_wash_session_row
    await push_wash_session_row(lot_code, block, row)


# ═══════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════════

class WashSessionCreate(BaseModel):
    operator_name: str
    equipment_id: Optional[str] = None
    tea_bag_count: Optional[int] = None
    fresh_frozen_uids: List[str] = []
    wet_weight_g: float
    started_at: Optional[str] = None
    ro_water_confirmed: Optional[bool] = None
    notes: Optional[str] = None

class WashSessionClose(BaseModel):
    wet_weight_g: Optional[float] = None
    notes: Optional[str] = None
    corrected_by: Optional[str] = None 

class FreezeDrySessionCreate(BaseModel):
    operator_name: str
    equipment_id: Optional[str] = None
    started_at: Optional[str] = None
    pump_oil_checked: Optional[bool] = None
    notes: Optional[str] = None
    allocations: List[dict]  # [{"wash_session_id": "...", "weight_allocated_g": 4000}]

class FreezeDrySessionClose(BaseModel):
    output_dry_weight_g: float
    notes: Optional[str] = None
    corrected_by: Optional[str] = None 

class SiftSessionCreate(BaseModel):
    operator_name: str
    storage_location: Optional[str] = None
    notes: Optional[str] = None
    allocations: List[dict]  # [{"freezedry_session_id": "...", "weight_allocated_g": 1200}]

class SiftSessionClose(BaseModel):
    sift_weight_out_g: float
    notes: Optional[str] = None
    corrected_by: Optional[str] = None 

class LotInputMaterial(BaseModel):
    fresh_frozen_uid: str
    strain_name: Optional[str] = None
    input_weight_g: Optional[float] = None

class ComponentLotCreate(BaseModel):
    component_type: str
    strain: Optional[str] = None
    is_mixed: bool = False
    description: Optional[str] = None
    initial_qty: Optional[float] = None
    metrc_uid: Optional[str] = None
    supplier: Optional[str] = None
    manifest_number: Optional[str] = None
    coa_ref: Optional[str] = None
    storage_location: Optional[str] = None
    created_by: Optional[str] = None
    type_data: Optional[dict] = None
    inputs: List[LotInputMaterial] = []
    lot_code_override: Optional[str] = None     # source materials feeding this lot

class ComponentStatusUpdate(BaseModel):
    status: str

class ComponentTypeCreate(BaseModel):
    key: Optional[str] = None            # auto-derived from display_name if omitted
    display_name: str
    uid_prefix: str
    is_produced_inhouse: bool = True
    unit_of_measure: str = "g"
    bpr_family: Optional[str] = None

class LotTransactionCreate(BaseModel):
    txn_type: str                            # production/receipt/consumption/waste/adjustment/metrc_package
    qty_delta: float                         # signed: positive adds, negative subtracts
    unit: Optional[str] = None               # defaults to the lot's unit
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    note: Optional[str] = None
    performed_by: Optional[str] = None

# ── Legacy hash-lot request models (kept for /hash/* compatibility) ───────

class HashLotCreateRequest(BaseModel):
    wash_bpr_id: Optional[str] = None
    primary_strain: str
    is_mixed: bool = False
    wet_weight_g: Optional[float] = None
    inputs: List[LotInputMaterial]
    lot_code_override: Optional[str] = None   # NEW

class HashLotWeightsRequest(BaseModel):
    dry_weight_g: Optional[float] = None
    sift_weight_g: Optional[float] = None
    storage_location: Optional[str] = None
    notes: Optional[str] = None

class HashLotStatusRequest(BaseModel):
    status: str
    press_bpr_id: Optional[str] = None
    press_metrc_uid: Optional[str] = None
    weight_used_g: Optional[float] = None

class HashLotAssignUidRequest(BaseModel):
    metrc_uid: str
    sheet_url: Optional[str] = None

class SanitationEntry(BaseModel):
    row: int                          # equipment row 1-7, matching the sheet
    date: Optional[str] = None        # "07/12/2026"
    clean_start: Optional[str] = None # "08:00"
    clean_end: Optional[str] = None   # "08:15"
    ppm: Optional[str] = None         # tested ppm ("200"), or "" for water/ISO rows
    strips_used: Optional[str] = None # "Yes" / "No" / ""
    passed: Optional[str] = None      # "Yes" / "No"
    cleaned_by: Optional[str] = None
    dry_before_use: Optional[str] = None  # "Yes" / "No"

class SanitationLogRequest(BaseModel):
    entries: List[SanitationEntry]

class TrayWeighInCreate(BaseModel):
    tray_label: Optional[str] = None
    weight_g: float
    recorded_by: Optional[str] = None



# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def get_component_type(cur, type_key: str) -> dict:
    """Fetch a component type from the registry, or 404."""
    cur.execute("SELECT * FROM bpr_component_types WHERE key = %s", (type_key,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, f"Unknown component type: {type_key}")
    return dict(row)

def workflow_keys(type_row: dict) -> list:
    """
    Extract the list of valid status keys from a type's status_workflow.
    Handles both formats: ["drying", ...] and [{"key":"drying","label":...}, ...]
    so hand-edited registry rows never crash the API.
    """
    wf = type_row.get("status_workflow") or []
    keys = []
    for item in wf:
        if isinstance(item, dict):
            keys.append(item.get("key"))
        else:
            keys.append(item)
    return [k for k in keys if k]

def get_lot(cur, lot_code: str) -> dict:
    """Fetch a component lot by its lot_code, or 404."""
    cur.execute("SELECT * FROM bpr_component_lots WHERE lot_code = %s", (lot_code,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, f"Lot not found: {lot_code}")
    return dict(row)

def lot_to_legacy(lot: dict) -> dict:
    """
    Presents a component lot in the shape the old hash_lots rows had, so
    existing GAS pages and the BPR frontend keep working without changes.
    type_data fields (wet_weight_g etc.) are lifted to the top level and
    lot_code is mirrored as hash_lot_id.
    """
    td = lot.get("type_data") or {}
    if isinstance(td, str):
        try: td = json.loads(td)
        except Exception: td = {}
    out = dict(lot)
    out["hash_lot_id"]   = lot["lot_code"]
    out["primary_strain"] = lot.get("strain")
    for k in ("is_mixed", "wet_weight_g", "dry_weight_g",
              "sift_weight_g", "yield_pct", "wash_bpr_id"):
        if k not in out or out.get(k) is None:
            out[k] = td.get(k)
    return out

def lot_balance(cur, lot_id: int) -> float:
    """Current inventory for a lot = sum of its ledger deltas."""
    cur.execute(
        "SELECT COALESCE(SUM(qty_delta), 0) AS bal FROM bpr_lot_transactions WHERE lot_id = %s",
        (lot_id,)
    )
    return float(cur.fetchone()["bal"])

def add_transaction(cur, lot: dict, txn_type: str, qty_delta: float,
                    unit: Optional[str] = None, reference_type: Optional[str] = None,
                    reference_id: Optional[str] = None, note: Optional[str] = None,
                    performed_by: Optional[str] = None) -> dict:
    """
    Insert a ledger transaction. For negative deltas (consumption/waste), the
    lot row is locked with FOR UPDATE first so two simultaneous pulls can't
    both pass the overdraw check — the second caller waits for the first to
    commit, then sees the updated balance. This locking is what keeps the
    ledger honest at 12-15 concurrent users.
    """
    if qty_delta < 0:
        cur.execute("SELECT id FROM bpr_component_lots WHERE id = %s FOR UPDATE", (lot["id"],))
        bal = lot_balance(cur, lot["id"])
        if bal + qty_delta < 0:
            raise HTTPException(400, {
                "message": f"Insufficient balance on {lot['lot_code']}",
                "current_balance": bal,
                "requested": abs(qty_delta)
            })
    cur.execute("""
        INSERT INTO bpr_lot_transactions
            (lot_id, txn_type, qty_delta, unit, reference_type, reference_id, note, performed_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """, (lot["id"], txn_type, qty_delta, unit or lot["unit"],
          reference_type, reference_id, note, performed_by))
    return dict(cur.fetchone())

def generate_lot_code(cur, type_row: dict, strain: Optional[str], is_mixed: bool) -> str:
    """
    Generic lot code generator: {PREFIX}-{STRAINCODE}-{MMDD}-{SEQ}.
    Prefix comes from the type registry, so ice water hash keeps producing
    HASH-... codes and nanos produce NANOTHC-... codes with zero extra logic.
    Known limitation (acceptable for now): two truly simultaneous creates for
    the same prefix could collide on SEQ; the UNIQUE constraint on lot_code
    rejects the loser, and the retry in create_component_lot_internal handles it.
    """
    import re
    from datetime import date
    mmdd = date.today().strftime("%m%d")

    if is_mixed:
        strain_code = "MIXED"
    elif strain:
        clean = re.sub(r'[^A-Z0-9]', '', strain.upper())
        strain_code = clean[:6] if clean else "UNKNWN"
    else:
        strain_code = "GEN"   # strainless types (nanos, distillate)

    prefix = f"{type_row['uid_prefix']}-{strain_code}-{mmdd}"
    cur.execute(
        "SELECT COUNT(*) AS cnt FROM bpr_component_lots WHERE lot_code LIKE %s",
        (f"{prefix}-%",)
    )
    seq = str(cur.fetchone()["cnt"] + 1).zfill(2)
    return f"{prefix}-{seq}"

def create_component_lot_internal(conn, req: ComponentLotCreate) -> dict:
    """
    Shared creation logic used by BOTH POST /components (new generic route)
    and POST /hash/create (legacy wrapper). One implementation, two doors —
    which is exactly why records look identical no matter which UI made them.
    """
    with conn.cursor() as cur:
        type_row = get_component_type(cur, req.component_type)

        status = type_row["default_status"]
        source = "produced" if type_row["is_produced_inhouse"] else "received"

        # Retry once on lot-code collision (see generate_lot_code note)
        lot = None
        for attempt in range(2):
            # Honor an operator-provided override on the first attempt only —
            # if it collides, fall back to auto-generation rather than looping
            # forever on the same rejected string.
            if req.lot_code_override and attempt == 0:
                lot_code = req.lot_code_override.strip().upper()
            else:
                lot_code = generate_lot_code(cur, type_row, req.strain, req.is_mixed)
            try:
                cur.execute("""
                    INSERT INTO bpr_component_lots
                        (lot_code, component_type, status, source, metrc_uid, strain,
                         description, initial_qty, unit, supplier, manifest_number,
                         coa_ref, storage_location, type_data, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    lot_code, req.component_type, status, source, req.metrc_uid,
                    req.strain, req.description, req.initial_qty,
                    type_row["unit_of_measure"], req.supplier, req.manifest_number,
                    req.coa_ref, req.storage_location,
                    json.dumps(req.type_data or {}), req.created_by
                ))
                lot = dict(cur.fetchone())
                break
            except psycopg2.errors.UniqueViolation:
                conn.rollback()  # clear the failed statement, try next sequence number
                if attempt == 1:
                    raise HTTPException(409, "Lot code collision — please retry")

        # Input materials (fresh frozen UIDs for hash; source packages for others)
        for inp in req.inputs:
            cur.execute("""
                INSERT INTO hash_lot_inputs
                    (hash_lot_id, fresh_frozen_uid, strain_name, input_weight_g)
                VALUES (%s, %s, %s, %s)
            """, (lot["lot_code"], inp.fresh_frozen_uid, inp.strain_name, inp.input_weight_g))

        # Received lots arrive with a known quantity — open the ledger with a receipt
        if source == "received" and req.initial_qty:
            add_transaction(cur, lot, "receipt", req.initial_qty,
                            reference_type="manifest",
                            reference_id=req.manifest_number,
                            note="Opening balance from received manifest",
                            performed_by=req.created_by)
    conn.commit()
    return lot

# ═══════════════════════════════════════════════════════════════════════════
# NEW GENERIC COMPONENT ROUTES  (/components/*)
# The webapp's future +New Batch flow and the GAS sidebar should both call
# these. Legacy /hash/* routes below wrap the same internals.
# ═══════════════════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════════════
# GENERIC COMPONENT ROUTES  (/components/*)
# ═══════════════════════════════════════════════════════════════════════

@router.get("/components/types")
def list_component_types():
    """
    Registry listing — frontends build their type dropdowns from this. Returns
    ALL types (including archived, each with its `archived` flag) so dashboards
    can still resolve names for lots of a retired type; the New Component picker
    filters archived out client-side.
    """
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM bpr_component_types ORDER BY archived, display_name")
            types = [dict(r) for r in cur.fetchall()]
        return {"types": types, "count": len(types)}
    finally:
        conn.close()


_PRODUCED_WORKFLOW = [
    {"key": "in_production", "label": "In Production"}, {"key": "qc_hold", "label": "QC Hold"},
    {"key": "available", "label": "Available"}, {"key": "in_use", "label": "In Use"},
    {"key": "depleted", "label": "Depleted"},
]
_RECEIVED_WORKFLOW = [
    {"key": "received", "label": "Received"}, {"key": "qc_hold", "label": "QC Hold"},
    {"key": "available", "label": "Available"}, {"key": "in_use", "label": "In Use"},
    {"key": "depleted", "label": "Depleted"},
]


@router.post("/components/types")
def create_component_type(req: ComponentTypeCreate, user: dict = Depends(require_admin)):
    """Admin: add a component type. Workflow/default status are auto-set from
    produced-vs-received so no hand-crafted JSON is needed. If the key already
    exists but is archived, this re-activates it."""
    import re
    if not req.display_name.strip() or not req.uid_prefix.strip():
        raise HTTPException(400, "display_name and uid_prefix are required")
    key = (req.key or req.display_name).strip().lower()
    key = re.sub(r"[^a-z0-9]+", "_", key).strip("_")
    if not key:
        raise HTTPException(400, "Could not derive a valid key")

    produced = req.is_produced_inhouse
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT archived FROM bpr_component_types WHERE key=%s", (key,))
            existing = cur.fetchone()
            if existing:
                cur.execute("UPDATE bpr_component_types SET archived=FALSE WHERE key=%s RETURNING *", (key,))
                row = dict(cur.fetchone())
                conn.commit()
                return {"type": row, "message": f"Re-activated existing type '{key}'"}
            cur.execute("""
                INSERT INTO bpr_component_types
                    (key, display_name, uid_prefix, is_produced_inhouse, bpr_family,
                     default_status, status_workflow, unit_of_measure, archived)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,FALSE)
                RETURNING *
            """, (
                key, req.display_name.strip(), req.uid_prefix.strip().upper(),
                produced, req.bpr_family,
                "in_production" if produced else "received",
                json.dumps(_PRODUCED_WORKFLOW if produced else _RECEIVED_WORKFLOW),
                (req.unit_of_measure or "g").strip(),
            ))
            row = dict(cur.fetchone())
        conn.commit()
        return {"type": row, "message": f"Component type '{key}' created"}
    finally:
        conn.close()


@router.delete("/components/types/{key}")
def archive_component_type(key: str, user: dict = Depends(require_admin)):
    """Admin: retire a type — ARCHIVED (hidden from the picker), not deleted, so
    any lot that already used it keeps resolving its name. Reversible via PATCH."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE bpr_component_types SET archived=TRUE WHERE key=%s RETURNING key", (key,))
            if not cur.fetchone():
                raise HTTPException(404, f"Unknown component type: {key}")
        conn.commit()
        return {"success": True, "archived": key}
    finally:
        conn.close()


@router.patch("/components/types/{key}")
def restore_component_type(key: str, user: dict = Depends(require_admin)):
    """Admin: un-archive a type so it shows in the picker again."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE bpr_component_types SET archived=FALSE WHERE key=%s RETURNING *", (key,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, f"Unknown component type: {key}")
        conn.commit()
        return {"type": dict(row), "success": True}
    finally:
        conn.close()


async def _create_component_bpr_sheet(conn, lot: dict) -> dict:
    """
    After a component lot is created, ask GAS to build its Google Sheet BPR +
    Drive folder (GAS owns template cloning + folder creation + the QR embed,
    exactly like batch/wash creation). Stores the returned sheet URL on the lot
    (sheet_url column) and the folder URL in type_data.folder_url so the lot
    detail page can link to both.

    Best-effort: a GAS/Drive hiccup must never fail the lot creation — the lot
    already committed. Returns {sheet_url, folder_url} (either may be None).
    """
    td = lot.get("type_data") or {}
    if isinstance(td, str):
        try: td = json.loads(td)
        except Exception: td = {}

    gas = await call_gas({
        "action":        "createComponentBPR",
        "lotCode":       lot["lot_code"],
        "componentType": lot["component_type"],
        "strain":        lot.get("strain") or "",
        "isMixed":       bool(td.get("is_mixed")),
        "metrcUid":      lot.get("metrc_uid") or "",
        "date":          td.get("date") or "",
    }, f"createComponentBPR {lot['lot_code']}")

    sheet_url  = gas.get("sheetUrl")  or gas.get("sheet_url")
    folder_url = gas.get("folderUrl") or gas.get("folder_url")
    if not sheet_url and not folder_url:
        return {"sheet_url": None, "folder_url": None}

    # Persist: sheet_url on its column, folder_url merged into type_data
    if folder_url:
        td["folder_url"] = folder_url
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE bpr_component_lots SET sheet_url = COALESCE(%s, sheet_url), "
            "type_data = %s, updated_at = NOW() WHERE lot_code = %s",
            (sheet_url, json.dumps(td), lot["lot_code"]))
    conn.commit()
    return {"sheet_url": sheet_url, "folder_url": folder_url}


@router.post("/components")
async def create_component_lot(req: ComponentLotCreate):
    conn = get_db()
    try:
        lot = create_component_lot_internal(conn, req)
        # Create the Google Sheet BPR + Drive folder (best-effort, via GAS).
        docs = await _create_component_bpr_sheet(conn, lot)
        if docs["sheet_url"]:
            lot["sheet_url"] = docs["sheet_url"]
        return {
            "lot_code": lot["lot_code"],
            "lot": lot,
            "sheet_url": docs["sheet_url"],
            "folder_url": docs["folder_url"],
            "message": f"Component lot created: {lot['lot_code']}. Label the container now."
        }
    finally:
        conn.close()


@router.get("/components/inventory")
def get_component_inventory(component_type: Optional[str] = None,
                            status: Optional[str] = None):
    """
    The fast dashboard read. Postgres answers this in milliseconds — this is
    the endpoint that replaces the slow GAS SpreadsheetApp dashboard loads.
    Optional filters: ?component_type=ice_water_hash&status=available
    """
    conn = get_db()
    try:
        with conn.cursor() as cur:
            query = "SELECT * FROM v_component_inventory WHERE 1=1"
            params = []
            if component_type:
                query += " AND component_type = %s"
                params.append(component_type)
            if status:
                query += " AND status = %s"
                params.append(status)
            query += " ORDER BY created_at DESC"
            cur.execute(query, params)
            lots = [dict(r) for r in cur.fetchall()]
        return {"lots": lots, "count": len(lots)}
    finally:
        conn.close()


@router.get("/components/available")
def get_available_components(component_type: Optional[str] = None):
    """
    The consumption-picker read. Generalizes /hash/available to ANY component
    type: a NANO SKU BPR calls ?component_type=nano_isolate to list nano-isolate
    lots it can draw down, exactly as the press flow lists ice_water_hash lots.

    Returns only lots with status='available' AND a positive remaining balance,
    each carrying current_qty (from the ledger) and its input materials — enough
    for the downstream BPR to record the lot as a Section 2 cannabis input.
    """
    conn = get_db()
    try:
        with conn.cursor() as cur:
            query = """
                SELECT l.*,
                    COALESCE(bal.qty, 0) AS current_qty,
                    t.display_name,
                    json_agg(json_build_object(
                        'fresh_frozen_uid', i.fresh_frozen_uid,
                        'strain_name',      i.strain_name,
                        'input_weight_g',   i.input_weight_g
                    )) FILTER (WHERE i.id IS NOT NULL) AS inputs
                FROM bpr_component_lots l
                JOIN bpr_component_types t ON t.key = l.component_type
                LEFT JOIN hash_lot_inputs i ON i.hash_lot_id = l.lot_code
                LEFT JOIN LATERAL (
                    SELECT SUM(qty_delta) AS qty FROM bpr_lot_transactions x
                    WHERE x.lot_id = l.id
                ) bal ON TRUE
                WHERE l.status = 'available'
            """
            params = []
            if component_type:
                query += " AND l.component_type = %s"
                params.append(component_type)
            query += """
                GROUP BY l.id, bal.qty, t.display_name
                HAVING COALESCE(bal.qty, 0) > 0
                ORDER BY l.created_at DESC
            """
            cur.execute(query, params)
            lots = [dict(r) for r in cur.fetchall()]
        return {"lots": lots, "count": len(lots)}
    finally:
        conn.close()


@router.get("/components/{lot_code}")
def get_component_lot(lot_code: str):
    """Full detail for one lot: record, inputs, ledger history, balance."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            lot = get_lot(cur, lot_code)

            cur.execute("SELECT * FROM hash_lot_inputs WHERE hash_lot_id = %s", (lot_code,))
            inputs = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT * FROM bpr_lot_transactions
                WHERE lot_id = %s ORDER BY created_at
            """, (lot["id"],))
            transactions = [dict(r) for r in cur.fetchall()]

            balance = lot_balance(cur, lot["id"])

        return {
            "lot": lot,
            "inputs": inputs,
            "transactions": transactions,
            "current_qty": balance,
        }
    finally:
        conn.close()


@router.patch("/components/{lot_code}/status")
def update_component_status(lot_code: str, req: ComponentStatusUpdate):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            lot = get_lot(cur, lot_code)
            type_row = get_component_type(cur, lot["component_type"])
            valid = workflow_keys(type_row)
            if req.status not in valid:
                # Friendly, type-aware error — this is why validation lives in
                # the API instead of a DB trigger
                raise HTTPException(400,
                    f"'{req.status}' is not a valid status for "
                    f"{type_row['display_name']}. Valid: {valid}")

            cur.execute("""
                UPDATE bpr_component_lots SET status = %s, updated_at = NOW()
                WHERE lot_code = %s RETURNING *
            """, (req.status, lot_code))
            updated = dict(cur.fetchone())
        conn.commit()
        return {"lot": updated, "message": f"{lot_code} status → {req.status}"}
    finally:
        conn.close()


@router.delete("/components/{lot_code}")
def delete_component_lot(lot_code: str, user: dict = Depends(require_admin)):
    """
    ADMIN-ONLY removal of a component lot created by mistake. Deletes the lot and
    every DB child it owns (ledger transactions, input materials, and — for hash
    lots — wash/freeze-dry/sift sessions, tray weigh-ins, and their allocations),
    in FK-safe order.

    HARD BLOCK: if any product BPR has already consumed this lot
    (bpr_component_consumption references it), deletion is refused — the lot is in
    production use, and its history must be unwound first (delete/undo those
    batches). This is DB-only; if the lot had a wash sheet, remove that separately.
    """
    conn = get_db()
    try:
        with conn.cursor() as cur:
            lot = get_lot(cur, lot_code)   # 404 if missing

            # Refuse if a BPR already drew from this lot.
            cur.execute(
                "SELECT bpr_uid FROM bpr_component_consumption WHERE lot_code = %s",
                (lot_code,))
            used_by = [r["bpr_uid"] for r in cur.fetchall()]
            if used_by:
                raise HTTPException(409, {
                    "message": f"{lot_code} was already consumed by a batch — "
                               f"delete/undo those first.",
                    "consumed_by": used_by,
                })

            # Children, deepest first. Allocations reference session ids; sessions,
            # trays, and inputs reference the lot_code; transactions reference the id.
            cur.execute("""
                DELETE FROM hash_lot_wash_to_freezedry_allocations
                WHERE wash_session_id IN (SELECT id FROM hash_lot_wash_sessions WHERE hash_lot_id=%s)
                   OR freezedry_session_id IN (SELECT id FROM hash_lot_freezedry_sessions WHERE hash_lot_id=%s)
            """, (lot_code, lot_code))
            cur.execute("""
                DELETE FROM hash_lot_freezedry_to_sift_allocations
                WHERE freezedry_session_id IN (SELECT id FROM hash_lot_freezedry_sessions WHERE hash_lot_id=%s)
                   OR sift_session_id IN (SELECT id FROM hash_lot_sift_sessions WHERE hash_lot_id=%s)
            """, (lot_code, lot_code))
            cur.execute("DELETE FROM hash_lot_tray_weighins       WHERE hash_lot_id = %s", (lot_code,))
            cur.execute("DELETE FROM hash_lot_wash_sessions       WHERE hash_lot_id = %s", (lot_code,))
            cur.execute("DELETE FROM hash_lot_freezedry_sessions  WHERE hash_lot_id = %s", (lot_code,))
            cur.execute("DELETE FROM hash_lot_sift_sessions       WHERE hash_lot_id = %s", (lot_code,))
            cur.execute("DELETE FROM hash_lot_inputs              WHERE hash_lot_id = %s", (lot_code,))
            cur.execute("DELETE FROM bpr_lot_transactions         WHERE lot_id = %s", (lot["id"],))
            cur.execute("DELETE FROM bpr_component_lots           WHERE lot_code = %s", (lot_code,))
        conn.commit()
        return {"success": True, "deleted": lot_code,
                "message": f"Component lot {lot_code} deleted."}
    finally:
        conn.close()


@router.post("/components/{lot_code}/transactions")
def create_lot_transaction(lot_code: str, req: LotTransactionCreate):
    """
    Record material movement: production yield in, consumption out, waste,
    corrections. This is THE way inventory changes — never by editing a
    quantity column, always by appending to the ledger.
    """
    valid_types = {"production", "receipt", "consumption", "waste", "adjustment", "metrc_package"}
    if req.txn_type not in valid_types:
        raise HTTPException(400, f"Invalid txn_type. Must be one of: {sorted(valid_types)}")

    conn = get_db()
    try:
        with conn.cursor() as cur:
            lot = get_lot(cur, lot_code)
            txn = add_transaction(cur, lot, req.txn_type, req.qty_delta,
                                  unit=req.unit,
                                  reference_type=req.reference_type,
                                  reference_id=req.reference_id,
                                  note=req.note,
                                  performed_by=req.performed_by)
            balance = lot_balance(cur, lot["id"])

            # Auto-deplete: when a consumption/waste takes the balance to zero,
            # flip status so the dashboard stops offering this lot
            if balance <= 0 and req.qty_delta < 0 and "depleted" in workflow_keys(
                    get_component_type(cur, lot["component_type"])):
                cur.execute(
                    "UPDATE bpr_component_lots SET status = 'depleted', updated_at = NOW() WHERE id = %s",
                    (lot["id"],)
                )
        conn.commit()
        return {"transaction": txn, "current_qty": balance}
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# LEGACY /hash/* ROUTES — thin wrappers over the generic system.
# The GAS wash page and BPR frontend call these today; they keep working
# unchanged. New code should prefer /components/*.
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/hash/create")
def create_hash_lot(req: HashLotCreateRequest):
    conn = get_db()
    try:
        generic_req = ComponentLotCreate(
            component_type="ice_water_hash",
            strain=req.primary_strain,
            is_mixed=req.is_mixed,
            lot_code_override=req.lot_code_override,   # NEW — thread it through
            type_data={
                "is_mixed": req.is_mixed,
                "wet_weight_g": req.wet_weight_g,
                "wash_bpr_id": req.wash_bpr_id,
            },
            inputs=req.inputs,
        )
        lot = create_component_lot_internal(conn, generic_req)
        legacy = lot_to_legacy(lot)
        return {
            "hash_lot_id": legacy["hash_lot_id"],
            "lot": legacy,
            "message": f"Hash lot created: {legacy['hash_lot_id']}. Write this on the vacuum seal bag."
        }
    finally:
        conn.close()


@router.get("/hash/available")
def get_available_hash_lots():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Same shape as before, plus current_qty from the ledger so the
            # press handoff screen can show how much hash actually remains
            cur.execute("""
                SELECT l.*,
                    COALESCE(bal.qty, 0) AS current_qty,
                    json_agg(json_build_object(
                        'fresh_frozen_uid', i.fresh_frozen_uid,
                        'strain_name',      i.strain_name,
                        'input_weight_g',   i.input_weight_g
                    )) FILTER (WHERE i.id IS NOT NULL) AS inputs
                FROM bpr_component_lots l
                LEFT JOIN hash_lot_inputs i ON i.hash_lot_id = l.lot_code
                LEFT JOIN LATERAL (
                    SELECT SUM(qty_delta) AS qty FROM bpr_lot_transactions t
                    WHERE t.lot_id = l.id
                ) bal ON TRUE
                WHERE l.component_type = 'ice_water_hash' AND l.status = 'available'
                GROUP BY l.id, bal.qty
                ORDER BY l.created_at DESC
            """)
            lots = [lot_to_legacy(dict(r)) for r in cur.fetchall()]
        return {"lots": lots, "count": len(lots)}
    finally:
        conn.close()


# NOTE: must stay AFTER /hash/available (first-registered route wins on conflicts)
@router.get("/hash/{hash_lot_id}")
def get_hash_lot(hash_lot_id: str):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            lot = get_lot(cur, hash_lot_id)

            cur.execute("SELECT * FROM hash_lot_inputs WHERE hash_lot_id = %s", (hash_lot_id,))
            inputs = [dict(r) for r in cur.fetchall()]

            # "usage" now comes from the ledger (consumption transactions),
            # presented in the old hash_lot_usage shape for compatibility
            cur.execute("""
                SELECT id, reference_id AS press_bpr_id, note AS press_metrc_uid,
                       ABS(qty_delta) AS weight_used_g, created_at AS used_at
                FROM bpr_lot_transactions
                WHERE lot_id = %s AND txn_type = 'consumption'
                ORDER BY created_at
            """, (lot["id"],))
            usage = [dict(r) for r in cur.fetchall()]

        return {
            "lot": lot_to_legacy(lot),
            "inputs": inputs,
            "usage": usage,
            "traceability": {
                "fresh_frozen_uids": [i["fresh_frozen_uid"] for i in inputs],
                "total_input_weight_g": sum(i["input_weight_g"] or 0 for i in inputs),
            }
        }
    finally:
        conn.close()


@router.patch("/hash/{hash_lot_id}/weights")
def update_hash_weights(hash_lot_id: str, req: HashLotWeightsRequest):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            lot = get_lot(cur, hash_lot_id)
            td = lot.get("type_data") or {}
            if isinstance(td, str):
                td = json.loads(td)

            # Yield % computed from stored wet weight, like before
            yield_pct = None
            wet = td.get("wet_weight_g")
            sift = req.sift_weight_g
            if wet and sift and float(wet) > 0:
                yield_pct = round((float(sift) / float(wet)) * 100, 2)

            # Merge new values into type_data (COALESCE semantics: only
            # overwrite what was provided)
            patch = {}
            if req.dry_weight_g is not None:  patch["dry_weight_g"] = req.dry_weight_g
            if req.sift_weight_g is not None: patch["sift_weight_g"] = req.sift_weight_g
            if yield_pct is not None:         patch["yield_pct"] = yield_pct

            cur.execute("""
                UPDATE bpr_component_lots SET
                    type_data        = type_data || %s::jsonb,
                    storage_location = COALESCE(%s, storage_location),
                    description      = COALESCE(%s, description),
                    status           = 'available',
                    updated_at       = NOW()
                WHERE lot_code = %s
                RETURNING *
            """, (json.dumps(patch), req.storage_location, req.notes, hash_lot_id))
            updated = dict(cur.fetchone())

            # LEDGER: the sift weigh-in is the moment inventory is born.
            # We insert the DELTA vs. any previously recorded production so
            # calling this endpoint twice (e.g. correcting a weight) adjusts
            # rather than double-counts.
            if req.sift_weight_g is not None:
                cur.execute("""
                    SELECT COALESCE(SUM(qty_delta), 0) AS produced
                    FROM bpr_lot_transactions
                    WHERE lot_id = %s AND txn_type = 'production'
                """, (lot["id"],))
                already = float(cur.fetchone()["produced"])
                delta = float(req.sift_weight_g) - already
                if delta != 0:
                    add_transaction(cur, lot, "production", delta,
                                    reference_type="sift_weighin",
                                    reference_id=hash_lot_id,
                                    note="Sift yield recorded" if already == 0
                                         else "Sift yield corrected")
        conn.commit()
        return {
            "lot": lot_to_legacy(updated),
            "yield_pct": yield_pct,
            "message": f"{hash_lot_id} updated — status set to available"
        }
    finally:
        conn.close()


@router.patch("/hash/{hash_lot_id}/status")
def update_hash_status(hash_lot_id: str, req: HashLotStatusRequest):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            lot = get_lot(cur, hash_lot_id)
            type_row = get_component_type(cur, lot["component_type"])
            valid = workflow_keys(type_row)
            if req.status not in valid:
                raise HTTPException(400, f"Invalid status. Must be one of: {valid}")

            cur.execute("""
                UPDATE bpr_component_lots SET status = %s, updated_at = NOW()
                WHERE lot_code = %s RETURNING *
            """, (req.status, hash_lot_id))
            updated = dict(cur.fetchone())

            # Press pulling hash → a consumption transaction in the ledger
            # (replaces the old hash_lot_usage insert, with overdraw protection)
            if req.status == "in_use" and req.press_bpr_id and req.weight_used_g:
                add_transaction(cur, lot, "consumption", -abs(req.weight_used_g),
                                reference_type="press_bpr",
                                reference_id=req.press_bpr_id,
                                note=req.press_metrc_uid)
        conn.commit()
        return {
            "lot": lot_to_legacy(updated),
            "message": f"{hash_lot_id} status → {req.status}"
        }
    finally:
        conn.close()


@router.patch("/hash/{hash_lot_id}/assign-uid")
def assign_uid_to_hash_lot(hash_lot_id: str, req: HashLotAssignUidRequest):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            lot = get_lot(cur, hash_lot_id)
            if lot["metrc_uid"]:
                raise HTTPException(400, f"Hash lot already has a METRC UID: {lot['metrc_uid']}")

            cur.execute("""
                UPDATE bpr_component_lots SET metrc_uid = %s, sheet_url = %s, updated_at = NOW()
                WHERE lot_code = %s RETURNING *
            """, (req.metrc_uid, req.sheet_url, hash_lot_id))
            updated = dict(cur.fetchone())
        conn.commit()
        return {"lot": lot_to_legacy(updated),
                "message": f"METRC UID {req.metrc_uid} assigned to {hash_lot_id}"}
    finally:
        conn.close()

@router.post("/hash/{hash_lot_id}/sanitation")
async def submit_wash_sanitation(hash_lot_id: str, req: SanitationLogRequest):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            lot = get_lot(cur, hash_lot_id)   # 404 if unknown lot
    finally:
        conn.close()

    sheet_url = lot.get("sheet_url")
    if not sheet_url:
        raise HTTPException(400, f"No BPR sheet on record for {hash_lot_id}")

    fields = {}
    incomplete = []
    for e in req.entries:
        if not (1 <= e.row <= 7):
            raise HTTPException(400, f"Invalid sanitation row: {e.row} (must be 1-7)")

        # Skip rows the operator left fully blank (not every run touches
        # every surface) — but a PARTIALLY filled row is a §17210(c)
        # violation waiting to happen, so reject those loudly.
        provided = [e.date, e.clean_start, e.clean_end, e.passed, e.cleaned_by]
        if not any(provided):
            continue
        if not (e.date and e.clean_start and e.clean_end and e.cleaned_by):
            incomplete.append(e.row)
            continue

        p = f"WASH_S5_ROW{e.row}"
        fields[p + "_DATE"]      = e.date
        fields[p + "_START"]     = e.clean_start
        fields[p + "_END"]       = e.clean_end
        fields[p + "_PPM"]       = e.ppm or ""
        fields[p + "_STRIPS"]    = e.strips_used or ""
        fields[p + "_PASS"]      = e.passed or ""
        fields[p + "_CLEANEDBY"] = e.cleaned_by
        fields[p + "_DRYBEFORE"] = e.dry_before_use or ""

    if incomplete:
        raise HTTPException(400, {
            "message": "Sanitation rows missing required fields (date, start, end, cleaned by are all required — §17210(c))",
            "incomplete_rows": incomplete
        })
    if not fields:
        raise HTTPException(400, "No sanitation entries provided")

    await _post_wash_gas({
        "action":   "writeWashBPRFields",
        "uid":      hash_lot_id,
        "sheetUrl": sheet_url,
        "fields":   fields,
    }, "wash sanitation log")

    return {"success": True, "rows_written": len(fields) // 8,
            "message": "Sanitation log submitted to BPR sheet"}        

# ─────────────────────────────────────────────────────────────────────────
# GET /bpr/phases
# ─────────────────────────────────────────────────────────────────────────


# ═══════════════════════════════════════════════════════════════════════
# WASH / FREEZE-DRY / SIFT SESSIONS, TRAY WEIGH-INS, RECONCILIATION
# ═══════════════════════════════════════════════════════════════════════

@router.post("/hash/{hash_lot_id}/wash-session")
def create_wash_session(hash_lot_id: str, req: WashSessionCreate):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Confirm lot exists (component table is the spine now)
            get_lot(cur, hash_lot_id)

            cur.execute(
                "SELECT COALESCE(MAX(session_num), 0) + 1 as next_num "
                "FROM hash_lot_wash_sessions WHERE hash_lot_id = %s",
                (hash_lot_id,)
            )
            session_num = cur.fetchone()["next_num"]

            cur.execute("""
                INSERT INTO hash_lot_wash_sessions
                    (hash_lot_id, session_num, operator_name, equipment_id,
                     tea_bag_count, fresh_frozen_uids, wet_weight_g,
                     started_at, ro_water_confirmed, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                hash_lot_id, session_num, req.operator_name, req.equipment_id,
                req.tea_bag_count, req.fresh_frozen_uids, req.wet_weight_g,
                req.started_at, req.ro_water_confirmed, req.notes
            ))
            session = dict(cur.fetchone())

            # Lots are now created in 'washing' status, so no status bump is
            # needed here — the wash session simply belongs to the wash stage.
        conn.commit()
        return {"session": session, "message": f"Wash session {session_num} logged"}
    finally:
        conn.close()


@router.get("/hash/{hash_lot_id}/wash-sessions")
def list_wash_sessions(hash_lot_id: str):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM hash_lot_wash_sessions
                WHERE hash_lot_id = %s ORDER BY session_num
            """, (hash_lot_id,))
            sessions = [dict(r) for r in cur.fetchall()]
        return {"sessions": sessions, "count": len(sessions)}
    finally:
        conn.close()


@router.patch("/hash/wash-session/{session_id}")
async def close_wash_session(session_id: str, req: WashSessionClose):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Was this session already closed BEFORE this call? That's what
            # tells us "correction" vs. "first close" — checked before the
            # UPDATE overwrites completed_at.
            cur.execute("SELECT completed_at FROM hash_lot_wash_sessions WHERE id = %s", (session_id,))
            existing = cur.fetchone()
            if not existing:
                raise HTTPException(404, "Wash session not found")
            is_correction = existing["completed_at"] is not None

            if is_correction and req.corrected_by:
                cur.execute("""
                    UPDATE hash_lot_wash_sessions SET
                        wet_weight_g = COALESCE(%s, wet_weight_g),
                        notes = COALESCE(%s, notes),
                        corrected_by = %s,
                        corrected_at = NOW()
                    WHERE id = %s
                    RETURNING *
                """, (req.wet_weight_g, req.notes, req.corrected_by, session_id))
            else:
                cur.execute("""
                    UPDATE hash_lot_wash_sessions SET
                        completed_at = NOW(),
                        wet_weight_g = COALESCE(%s, wet_weight_g),
                        notes = COALESCE(%s, notes)
                    WHERE id = %s
                    RETURNING *
                """, (req.wet_weight_g, req.notes, session_id))
            updated = dict(cur.fetchone())
        conn.commit()

        import asyncio
        asyncio.create_task(_push_wash_session_row(updated["hash_lot_id"], "wash", {
            "session_num":  updated["session_num"],
            "operator":     updated["operator_name"],
            "equipment":    updated["equipment_id"] or "",
            "tea_bags":     updated["tea_bag_count"] if updated["tea_bag_count"] is not None else "",
            "wet_weight":   float(updated["wet_weight_g"]) if updated["wet_weight_g"] is not None else "",
            "ff_uids":      ", ".join(updated["fresh_frozen_uids"] or []),
            "ro_confirmed": "Yes" if updated["ro_water_confirmed"] else "No",
            "started_at":   fmt_ts(updated["started_at"]) or "",
            "completed_at": fmt_ts(updated["completed_at"]) or "",
            "notes":        updated["notes"] or "",
        }))

        return {"session": updated, "message": "Wash session corrected" if is_correction else "Wash session closed"}
    finally:
        conn.close()


# ── FREEZE-DRY SESSIONS + ALLOCATIONS ──────────────────────────

@router.get("/hash/{hash_lot_id}/available-wash-sessions")
def get_available_wash_sessions(hash_lot_id: str):
    """
    Returns wash sessions for this lot with their remaining unallocated weight —
    powers the 'select which wash sessions go in this dryer' checklist.
    """
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    ws.*,
                    COALESCE(SUM(a.weight_allocated_g), 0) as allocated_g,
                    ws.wet_weight_g - COALESCE(SUM(a.weight_allocated_g), 0) as remaining_g
                FROM hash_lot_wash_sessions ws
                LEFT JOIN hash_lot_wash_to_freezedry_allocations a
                    ON a.wash_session_id = ws.id
                WHERE ws.hash_lot_id = %s
                GROUP BY ws.id
                HAVING ws.wet_weight_g - COALESCE(SUM(a.weight_allocated_g), 0) > 0
                ORDER BY ws.session_num
            """, (hash_lot_id,))
            sessions = [dict(r) for r in cur.fetchall()]
        return {"sessions": sessions}
    finally:
        conn.close()


@router.post("/hash/{hash_lot_id}/freezedry-session")
def create_freezedry_session(hash_lot_id: str, req: FreezeDrySessionCreate):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            get_lot(cur, hash_lot_id)

            if not req.allocations:
                raise HTTPException(400, "At least one wash session allocation is required")

            # Validate each allocation against remaining unallocated weight
            total_input = 0
            for alloc in req.allocations:
                ws_id = alloc["wash_session_id"]
                weight = alloc["weight_allocated_g"]

                cur.execute("""
                    SELECT
                        ws.wet_weight_g,
                        COALESCE(SUM(a.weight_allocated_g), 0) as already_allocated
                    FROM hash_lot_wash_sessions ws
                    LEFT JOIN hash_lot_wash_to_freezedry_allocations a
                        ON a.wash_session_id = ws.id
                    WHERE ws.id = %s
                    GROUP BY ws.wet_weight_g
                """, (ws_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(404, f"Wash session not found: {ws_id}")

                remaining = row["wet_weight_g"] - row["already_allocated"]
                if weight > remaining:
                    raise HTTPException(400, {
                        "message": f"Over-allocation on wash session {ws_id}",
                        "remaining_g": float(remaining),
                        "requested_g": weight
                    })
                total_input += weight

            cur.execute(
                "SELECT COALESCE(MAX(session_num), 0) + 1 as next_num "
                "FROM hash_lot_freezedry_sessions WHERE hash_lot_id = %s",
                (hash_lot_id,)
            )
            session_num = cur.fetchone()["next_num"]

            cur.execute("""
                INSERT INTO hash_lot_freezedry_sessions
                    (hash_lot_id, session_num, operator_name, equipment_id,
                     input_wet_weight_g, started_at, pump_oil_checked, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                hash_lot_id, session_num, req.operator_name, req.equipment_id,
                total_input, req.started_at, req.pump_oil_checked, req.notes
            ))
            fd_session = dict(cur.fetchone())

            for alloc in req.allocations:
                cur.execute("""
                    INSERT INTO hash_lot_wash_to_freezedry_allocations
                        (wash_session_id, freezedry_session_id, weight_allocated_g)
                    VALUES (%s, %s, %s)
                """, (alloc["wash_session_id"], fd_session["id"], alloc["weight_allocated_g"]))

            # First dryer load moves the lot from washing → drying
            cur.execute(
                "UPDATE bpr_component_lots SET status = 'drying', updated_at = NOW() WHERE lot_code = %s",
                (hash_lot_id,)
            )
        conn.commit()
        return {"session": fd_session, "message": f"Freeze-dry session {session_num} started"}
    finally:
        conn.close()


@router.get("/hash/{hash_lot_id}/freezedry-sessions")
def list_freezedry_sessions(hash_lot_id: str):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT fd.*,
                    json_agg(json_build_object(
                        'wash_session_id', a.wash_session_id,
                        'weight_allocated_g', a.weight_allocated_g
                    )) as wash_inputs
                FROM hash_lot_freezedry_sessions fd
                LEFT JOIN hash_lot_wash_to_freezedry_allocations a
                    ON a.freezedry_session_id = fd.id
                WHERE fd.hash_lot_id = %s
                GROUP BY fd.id
                ORDER BY fd.session_num
            """, (hash_lot_id,))
            sessions = [dict(r) for r in cur.fetchall()]
        return {"sessions": sessions}
    finally:
        conn.close()


@router.patch("/hash/freezedry-session/{session_id}")
async def close_freezedry_session(session_id: str, req: FreezeDrySessionClose):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT completed_at FROM hash_lot_freezedry_sessions WHERE id = %s", (session_id,))
            existing = cur.fetchone()
            if not existing:
                raise HTTPException(404, "Freeze-dry session not found")
            is_correction = existing["completed_at"] is not None

            if is_correction and req.corrected_by:
                cur.execute("""
                    UPDATE hash_lot_freezedry_sessions SET
                        output_dry_weight_g = %s,
                        notes = COALESCE(%s, notes),
                        corrected_by = %s,
                        corrected_at = NOW()
                    WHERE id = %s
                    RETURNING *
                """, (req.output_dry_weight_g, req.notes, req.corrected_by, session_id))
            else:
                cur.execute("""
                    UPDATE hash_lot_freezedry_sessions SET
                        completed_at = NOW(),
                        output_dry_weight_g = %s,
                        notes = COALESCE(%s, notes)
                    WHERE id = %s
                    RETURNING *
                """, (req.output_dry_weight_g, req.notes, session_id))
            updated = dict(cur.fetchone())

            cur.execute("""
                SELECT ws.session_num, a.weight_allocated_g
                FROM hash_lot_wash_to_freezedry_allocations a
                JOIN hash_lot_wash_sessions ws ON ws.id = a.wash_session_id
                WHERE a.freezedry_session_id = %s
                ORDER BY ws.session_num
            """, (session_id,))
            wash_used = "; ".join(
                f"S{r['session_num']}: {float(r['weight_allocated_g']):,.0f}g"
                for r in cur.fetchall()
            )
        conn.commit()

        import asyncio
        asyncio.create_task(_push_wash_session_row(updated["hash_lot_id"], "freezedry", {
            "session_num":  updated["session_num"],
            "operator":     updated["operator_name"],
            "equipment":    updated["equipment_id"] or "",
            "wash_used":    wash_used,
            "input_wet":    float(updated["input_wet_weight_g"]) if updated["input_wet_weight_g"] is not None else "",
            "output_dry":   float(updated["output_dry_weight_g"]) if updated["output_dry_weight_g"] is not None else "",
            "pump_oil":     "Yes" if updated["pump_oil_checked"] else "No",
            "started_at":   fmt_ts(updated["started_at"]) or "",
            "completed_at": fmt_ts(updated["completed_at"]) or "",
            "notes":        updated["notes"] or "",
        }))

        return {"session": updated, "message": "Freeze-dry session corrected" if is_correction else "Freeze-dry session closed"}
    finally:
        conn.close()

# ── SIFT SESSIONS + ALLOCATIONS ─────────────────────────────────

@router.get("/hash/{hash_lot_id}/available-freezedry-sessions")
def get_available_freezedry_sessions(hash_lot_id: str):
    """
    Returns freeze-dry sessions for this lot with remaining unallocated dry weight —
    powers the 'select which dryer loads go into this sift' checklist.
    Only includes sessions that have actually closed (have an output_dry_weight_g).
    """
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    fd.*,
                    COALESCE(SUM(a.weight_allocated_g), 0) as allocated_g,
                    fd.output_dry_weight_g - COALESCE(SUM(a.weight_allocated_g), 0) as remaining_g
                FROM hash_lot_freezedry_sessions fd
                LEFT JOIN hash_lot_freezedry_to_sift_allocations a
                    ON a.freezedry_session_id = fd.id
                WHERE fd.hash_lot_id = %s
                  AND fd.output_dry_weight_g IS NOT NULL
                GROUP BY fd.id
                HAVING fd.output_dry_weight_g - COALESCE(SUM(a.weight_allocated_g), 0) > 0
                ORDER BY fd.session_num
            """, (hash_lot_id,))
            sessions = [dict(r) for r in cur.fetchall()]
        return {"sessions": sessions}
    finally:
        conn.close()


@router.post("/hash/{hash_lot_id}/sift-session")
def create_sift_session(hash_lot_id: str, req: SiftSessionCreate):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            get_lot(cur, hash_lot_id)

            if not req.allocations:
                raise HTTPException(400, "At least one freeze-dry session allocation is required")

            total_input = 0
            for alloc in req.allocations:
                fd_id = alloc["freezedry_session_id"]
                weight = alloc["weight_allocated_g"]

                cur.execute("""
                    SELECT
                        fd.output_dry_weight_g,
                        COALESCE(SUM(a.weight_allocated_g), 0) as already_allocated
                    FROM hash_lot_freezedry_sessions fd
                    LEFT JOIN hash_lot_freezedry_to_sift_allocations a
                        ON a.freezedry_session_id = fd.id
                    WHERE fd.id = %s
                    GROUP BY fd.output_dry_weight_g
                """, (fd_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(404, f"Freeze-dry session not found: {fd_id}")
                if row["output_dry_weight_g"] is None:
                    raise HTTPException(400, f"Freeze-dry session {fd_id} has not been closed yet — no dry weight recorded")

                remaining = row["output_dry_weight_g"] - row["already_allocated"]
                if weight > remaining:
                    raise HTTPException(400, {
                        "message": f"Over-allocation on freeze-dry session {fd_id}",
                        "remaining_g": float(remaining),
                        "requested_g": weight
                    })
                total_input += weight

            cur.execute(
                "SELECT COALESCE(MAX(session_num), 0) + 1 as next_num "
                "FROM hash_lot_sift_sessions WHERE hash_lot_id = %s",
                (hash_lot_id,)
            )
            session_num = cur.fetchone()["next_num"]

            cur.execute("""
                INSERT INTO hash_lot_sift_sessions
                    (hash_lot_id, session_num, operator_name,
                     dry_weight_in_g, storage_location, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                hash_lot_id, session_num, req.operator_name,
                total_input, req.storage_location, req.notes
            ))
            sift_session = dict(cur.fetchone())

            for alloc in req.allocations:
                cur.execute("""
                    INSERT INTO hash_lot_freezedry_to_sift_allocations
                        (freezedry_session_id, sift_session_id, weight_allocated_g)
                    VALUES (%s, %s, %s)
                """, (alloc["freezedry_session_id"], sift_session["id"], alloc["weight_allocated_g"]))

            cur.execute(
                "UPDATE bpr_component_lots SET status = 'sifting', updated_at = NOW() WHERE lot_code = %s",
                (hash_lot_id,)
            )
        conn.commit()
        return {"session": sift_session, "message": f"Sift session {session_num} started"}
    finally:
        conn.close()


@router.get("/hash/{hash_lot_id}/sift-sessions")
def list_sift_sessions(hash_lot_id: str):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.*,
                    json_agg(json_build_object(
                        'freezedry_session_id', a.freezedry_session_id,
                        'weight_allocated_g', a.weight_allocated_g
                    )) as freezedry_inputs
                FROM hash_lot_sift_sessions s
                LEFT JOIN hash_lot_freezedry_to_sift_allocations a
                    ON a.sift_session_id = s.id
                WHERE s.hash_lot_id = %s
                GROUP BY s.id
                ORDER BY s.session_num
            """, (hash_lot_id,))
            sessions = [dict(r) for r in cur.fetchall()]
        return {"sessions": sessions}
    finally:
        conn.close()


@router.patch("/hash/sift-session/{session_id}")
async def close_sift_session(session_id: str, req: SiftSessionClose):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT completed_at FROM hash_lot_sift_sessions WHERE id = %s", (session_id,))
            existing = cur.fetchone()
            if not existing:
                raise HTTPException(404, "Sift session not found")
            is_correction = existing["completed_at"] is not None

            if is_correction and req.corrected_by:
                cur.execute("""
                    UPDATE hash_lot_sift_sessions SET
                        sift_weight_out_g = %s,
                        notes = COALESCE(%s, notes),
                        corrected_by = %s,
                        corrected_at = NOW()
                    WHERE id = %s
                    RETURNING *
                """, (req.sift_weight_out_g, req.notes, req.corrected_by, session_id))
            else:
                cur.execute("""
                    UPDATE hash_lot_sift_sessions SET
                        completed_at = NOW(),
                        sift_weight_out_g = %s,
                        notes = COALESCE(%s, notes)
                    WHERE id = %s
                    RETURNING *
                """, (req.sift_weight_out_g, req.notes, session_id))
            updated = dict(cur.fetchone())

            cur.execute("""
                SELECT fd.session_num, a.weight_allocated_g
                FROM hash_lot_freezedry_to_sift_allocations a
                JOIN hash_lot_freezedry_sessions fd ON fd.id = a.freezedry_session_id
                WHERE a.sift_session_id = %s
                ORDER BY fd.session_num
            """, (session_id,))
            fd_used = "; ".join(
                f"S{r['session_num']}: {float(r['weight_allocated_g']):,.0f}g"
                for r in cur.fetchall()
            )

            # ── LEDGER: runs on EVERY close, correction or not — a
            # corrected sift weight is a real inventory change and must
            # flow through. The delta-vs-already-produced math (unchanged
            # from before) means this naturally handles corrections too:
            # closing session 2 the first time adds session 2's grams;
            # re-closing it with a different number adds/subtracts just
            # the difference, never double-counts.
            lot = get_lot(cur, updated["hash_lot_id"])
            cur.execute("""
                SELECT COALESCE(SUM(sift_weight_out_g), 0) AS total_out
                FROM hash_lot_sift_sessions
                WHERE hash_lot_id = %s AND sift_weight_out_g IS NOT NULL
            """, (updated["hash_lot_id"],))
            total_out = float(cur.fetchone()["total_out"])
            cur.execute("""
                SELECT COALESCE(SUM(qty_delta), 0) AS produced
                FROM bpr_lot_transactions
                WHERE lot_id = %s AND txn_type = 'production'
            """, (lot["id"],))
            already = float(cur.fetchone()["produced"])
            delta = total_out - already
            if delta != 0:
                add_transaction(cur, lot, "production", delta,
                                reference_type="sift_session",
                                reference_id=str(session_id),
                                note=f"Sift session {updated['session_num']} "
                                     + ("corrected" if is_correction else "closed"),
                                performed_by=req.corrected_by or updated["operator_name"])
        conn.commit()

        import asyncio
        asyncio.create_task(_push_wash_session_row(updated["hash_lot_id"], "sift", {
            "session_num":  updated["session_num"],
            "operator":     updated["operator_name"],
            "fd_used":      fd_used,
            "dry_in":       float(updated["dry_weight_in_g"]) if updated["dry_weight_in_g"] is not None else "",
            "sift_out":     float(updated["sift_weight_out_g"]) if updated["sift_weight_out_g"] is not None else "",
            "storage":      updated["storage_location"] or "",
            "completed_at": fmt_ts(updated["completed_at"]) or "",
            "notes":        updated["notes"] or "",
        }))

        return {"session": updated, "message": "Sift session corrected" if is_correction else "Sift session closed"}
    finally:
        conn.close()

# ── TRAY WEIGH-INS — logged during an open session, before it closes ──

@router.post("/hash/{hash_lot_id}/{stage}-session/{session_id}/tray")
def add_tray_weighin(hash_lot_id: str, stage: str, session_id: str, req: TrayWeighInCreate):
    if stage not in ("wash", "freezedry", "sift"):
        raise HTTPException(400, "stage must be wash, freezedry, or sift")
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO hash_lot_tray_weighins
                    (hash_lot_id, stage, session_id, tray_label, weight_g, recorded_by)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (hash_lot_id, stage, session_id, req.tray_label, req.weight_g, req.recorded_by))
            tray = dict(cur.fetchone())

            cur.execute("""
                SELECT COALESCE(SUM(weight_g), 0) AS total, COUNT(*) AS n
                FROM hash_lot_tray_weighins WHERE session_id = %s
            """, (session_id,))
            totals = cur.fetchone()
        conn.commit()
        return {"tray": tray, "running_total_g": float(totals["total"]), "tray_count": totals["n"]}
    finally:
        conn.close()


@router.get("/hash/{stage}-session/{session_id}/trays")
def list_tray_weighins(stage: str, session_id: str):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM hash_lot_tray_weighins
                WHERE session_id = %s ORDER BY created_at
            """, (session_id,))
            trays = [dict(r) for r in cur.fetchall()]
            total = sum(float(t["weight_g"]) for t in trays)
        return {"trays": trays, "running_total_g": total, "tray_count": len(trays)}
    finally:
        conn.close()


@router.delete("/hash/tray/{tray_id}")
def delete_tray_weighin(tray_id: str):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM hash_lot_tray_weighins WHERE id = %s RETURNING session_id", (tray_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "Tray entry not found")
            cur.execute("""
                SELECT COALESCE(SUM(weight_g), 0) AS total FROM hash_lot_tray_weighins
                WHERE session_id = %s
            """, (row["session_id"],))
            total = cur.fetchone()["total"]
        conn.commit()
        return {"deleted": True, "running_total_g": float(total)}
    finally:
        conn.close()

@router.get("/hash/{hash_lot_id}/reconciliation")
def get_lot_reconciliation(hash_lot_id: str):
    """
    Rolls up totals across all wash, freeze-dry, and sift sessions for a lot.
    Used for the close-out summary and as a sanity check on yields.
    """
    conn = get_db()
    try:
        with conn.cursor() as cur:
            lot = get_lot(cur, hash_lot_id)

            cur.execute("""
                SELECT COUNT(*) as count, COALESCE(SUM(wet_weight_g), 0) as total_wet_weight_g,
                       COUNT(*) FILTER (WHERE completed_at IS NULL) as open_count
                FROM hash_lot_wash_sessions WHERE hash_lot_id = %s
            """, (hash_lot_id,))
            wash_summary = dict(cur.fetchone())

            cur.execute("""
                SELECT COUNT(*) as count,
                       COALESCE(SUM(input_wet_weight_g), 0) as total_input_wet_weight_g,
                       COALESCE(SUM(output_dry_weight_g), 0) as total_output_dry_weight_g,
                       COUNT(*) FILTER (WHERE completed_at IS NULL) as open_count
                FROM hash_lot_freezedry_sessions WHERE hash_lot_id = %s
            """, (hash_lot_id,))
            freezedry_summary = dict(cur.fetchone())

            cur.execute("""
                SELECT COUNT(*) as count,
                       COALESCE(SUM(dry_weight_in_g), 0) as total_dry_weight_in_g,
                       COALESCE(SUM(sift_weight_out_g), 0) as total_sift_weight_out_g,
                       COUNT(*) FILTER (WHERE completed_at IS NULL) as open_count
                FROM hash_lot_sift_sessions WHERE hash_lot_id = %s
            """, (hash_lot_id,))
            sift_summary = dict(cur.fetchone())

            cur.execute("""
                SELECT DISTINCT unnest(fresh_frozen_uids) as uid
                FROM hash_lot_wash_sessions WHERE hash_lot_id = %s
            """, (hash_lot_id,))
            all_fresh_frozen_uids = [r["uid"] for r in cur.fetchall()]

            total_wet = float(wash_summary["total_wet_weight_g"])
            total_sift = float(sift_summary["total_sift_weight_out_g"])
            overall_yield_pct = round((total_sift / total_wet) * 100, 2) if total_wet > 0 else None

            all_stages_closed = (
                wash_summary["open_count"] == 0 and wash_summary["count"] > 0 and
                freezedry_summary["open_count"] == 0 and freezedry_summary["count"] > 0 and
                sift_summary["open_count"] == 0 and sift_summary["count"] > 0
            )

        return {
            "hash_lot_id": hash_lot_id,
            "lot": lot_to_legacy(lot),
            "wash": wash_summary,
            "freeze_dry": freezedry_summary,
            "sift": sift_summary,
            "overall_yield_pct": overall_yield_pct,
            "all_fresh_frozen_uids": all_fresh_frozen_uids,
            "ready_to_close": all_stages_closed,
        }
    finally:
        conn.close()

# Health check is defined at the top of this file above all /bpr/{uid} routes
