"""
BatchD BPR — FastAPI backend  (v2.0 — generic component lot system)
Deploy alongside ManifestD on Railway.
All BPR routes are prefixed /bpr

WHAT CHANGED IN v2.0
────────────────────
• hash_lots is retired. The spine is now bpr_component_lots — a generic lot
  table for ANY intermediate/component material (ice water hash, nanos,
  edibles rosin, cured rosin, third-party distillate, etc.)
• bpr_component_types is a registry: adding a new component type is an
  INSERT, not a code deploy.
• bpr_lot_transactions is a quantity ledger: every gram in or out is a row.
  Current inventory = SUM(qty_delta). This is the audit trail and the
  future METRC write-back surface.
• All legacy /hash/* routes still work — they are thin wrappers over the
  generic system, so the existing GAS wash page and BPR frontend keep
  functioning unchanged. New clients should use /components/* routes.
• NEW: /bpr/create now writes wash_bpr_id onto the component lot itself
  (fixes the bug where wash_bpr_id was never populated).
• NEW: lot creation status comes from the type registry's default_status
  ('washing' for hash) instead of being hardcoded.

DEPLOYMENT ORDER (do these back-to-back):
  1. Deploy this file to Railway
  2. Run the 10 FK re-aim statements (saved from planning session)
  3. Rename hash_lots:  ALTER TABLE hash_lots RENAME TO zz_retired_hash_lots
  4. Create a test wash batch end-to-end to verify

Environment variables required (add to Railway):
  DATABASE_URL           — Railway Postgres connection string (already set for ManifestD)
  GAS_WEBHOOK_URL        — GAS doPost URL to ping on BPR completion
  GOOGLE_SERVICE_ACCOUNT — JSON string of service account credentials (for Drive PDF upload)
  DRIVE_COA_FOLDER_ID    — Root COA Archive folder ID (to find UID subfolders)

TODO (dedicated security session): add API-key auth on all write routes,
tighten CORS to the Netlify origin, add rate limiting.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import psycopg2
import psycopg2.extras
import os, json, uuid, httpx
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel

# ── Import phase definitions ──────────────────────────────────────────────
import sys
sys.path.append(os.path.dirname(__file__))
from bpr_phases import BPR_PHASES, detect_product_family

app = FastAPI(title="BatchD BPR API", version="2.1.0")

# ── CORS: only our own frontends may call from a browser ────────────────
# Netlify app + GAS-served pages (which load from rotating
# *.googleusercontent.com subdomains, hence the regex) + local dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://batchd-bpr.netlify.app",
        "http://localhost:5173",
    ],
    allow_origin_regex=r"https://.*\.googleusercontent\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API key gate ─────────────────────────────────────────────────────────
# Every request must carry X-API-Key matching the BATCHD_API_KEY env var.
# Exemptions: /health (uptime checks), and OPTIONS (CORS preflights never
# carry custom headers — blocking them would break the browser clients).
# If BATCHD_API_KEY is unset the gate stands down, so a missing variable
# degrades to "open" loudly in the logs rather than bricking production.
@app.middleware("http")
async def require_api_key(request: Request, call_next):
    if request.method == "OPTIONS" or request.url.path in ("/health", "/bpr/health"):
        return await call_next(request)
    expected = os.environ.get("BATCHD_API_KEY")
    if not expected:
        print("WARNING: BATCHD_API_KEY not set — API is OPEN")
        return await call_next(request)
    if request.headers.get("X-API-Key") != expected:
        return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
    return await call_next(request)

# ── Health check — defined FIRST to avoid being swallowed by /bpr/{uid} ──
@app.get("/health")
@app.get("/bpr/health")
def health():
    return {"status": "ok", "service": "BatchD BPR", "version": "2.1.0"}

# ── DB connection ─────────────────────────────────────────────────────────
def get_db():
    return psycopg2.connect(
        os.environ["DATABASE_URL"],
        cursor_factory=psycopg2.extras.RealDictCursor
    )

# ── Schema init ───────────────────────────────────────────────────────────
# NOTE: hash_lots and hash_lot_usage are deliberately ABSENT from this schema.
# They are retired. If they were still here as CREATE IF NOT EXISTS, a fresh
# boot after the rename would silently recreate an empty ghost table.
# Session/allocation/input tables now reference bpr_component_lots(lot_code)
# so a fresh install (or future multi-tenant instance) builds correctly
# from nothing.
SCHEMA = """
CREATE TABLE IF NOT EXISTS bpr_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    uid             TEXT NOT NULL UNIQUE,
    product_name    TEXT NOT NULL,
    batch_id        TEXT,
    mfg_date        TEXT,
    category        TEXT,
    product_family  TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'in_progress',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    supervisor_name TEXT,
    supervisor_at   TIMESTAMPTZ,
    pdf_drive_url   TEXT,
    deviation_notes TEXT,
    total_yield     TEXT
);

CREATE TABLE IF NOT EXISTS bpr_phase_signoffs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bpr_id          UUID NOT NULL REFERENCES bpr_records(id) ON DELETE CASCADE,
    uid             TEXT NOT NULL,
    phase_id        TEXT NOT NULL,
    phase_name      TEXT NOT NULL,
    employee_name   TEXT NOT NULL,
    signed_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes           TEXT,
    ccp_values      JSONB,
    UNIQUE(bpr_id, phase_id)
);

CREATE TABLE IF NOT EXISTS bpr_step_checks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bpr_id          UUID NOT NULL REFERENCES bpr_records(id) ON DELETE CASCADE,
    uid             TEXT NOT NULL,
    phase_id        TEXT NOT NULL,
    step_index      INT NOT NULL,
    checked         BOOLEAN NOT NULL DEFAULT FALSE,
    checked_by      TEXT,
    checked_at      TIMESTAMPTZ,
    UNIQUE(bpr_id, phase_id, step_index)
);

CREATE INDEX IF NOT EXISTS idx_bpr_uid ON bpr_records(uid);
CREATE INDEX IF NOT EXISTS idx_signoffs_bpr ON bpr_phase_signoffs(bpr_id);
CREATE INDEX IF NOT EXISTS idx_steps_bpr_phase ON bpr_step_checks(bpr_id, phase_id);

-- ── Component type registry ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bpr_component_types (
    key                  TEXT PRIMARY KEY,
    display_name         TEXT NOT NULL,
    uid_prefix           TEXT NOT NULL,
    is_produced_inhouse  BOOLEAN NOT NULL DEFAULT TRUE,
    bpr_family           TEXT,
    default_status       TEXT NOT NULL,
    status_workflow      JSONB NOT NULL,
    unit_of_measure      TEXT NOT NULL DEFAULT 'g',
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed known types on fresh installs. ON CONFLICT DO NOTHING means existing
-- rows (which you may have edited by hand) are never overwritten on boot.
INSERT INTO bpr_component_types
    (key, display_name, uid_prefix, is_produced_inhouse, bpr_family, default_status, status_workflow, unit_of_measure)
VALUES
    ('ice_water_hash', 'Ice Water Hash', 'HASH', TRUE, 'rosin_wash', 'washing',
     '[{"key":"washing","label":"Ice Extraction"},{"key":"drying","label":"Freeze Drying"},{"key":"sifting","label":"Sifting"},{"key":"available","label":"Available"},{"key":"in_use","label":"In Use"},{"key":"depleted","label":"Depleted"}]', 'g'),
    ('edibles_rosin', 'Edibles Rosin', 'EROSIN', TRUE, 'rosin_press', 'pressing',
     '[{"key":"pressing","label":"Pressing"},{"key":"curing","label":"Curing"},{"key":"available","label":"Available"},{"key":"in_use","label":"In Use"},{"key":"depleted","label":"Depleted"}]', 'g'),
    ('cured_rosin', 'Cured Rosin (AIO)', 'CROSIN', TRUE, 'rosin_press', 'pressing',
     '[{"key":"pressing","label":"Pressing"},{"key":"curing","label":"Curing"},{"key":"available","label":"Available"},{"key":"in_use","label":"In Use"},{"key":"depleted","label":"Depleted"}]', 'g'),
    ('nano_thc', 'NANO-THC', 'NANOTHC', TRUE, NULL, 'in_production',
     '[{"key":"in_production","label":"In Production"},{"key":"qc_hold","label":"QC Hold"},{"key":"available","label":"Available"},{"key":"in_use","label":"In Use"},{"key":"depleted","label":"Depleted"}]', 'ml'),
    ('nano_cbn', 'NANO-CBN', 'NANOCBN', TRUE, NULL, 'in_production',
     '[{"key":"in_production","label":"In Production"},{"key":"qc_hold","label":"QC Hold"},{"key":"available","label":"Available"},{"key":"in_use","label":"In Use"},{"key":"depleted","label":"Depleted"}]', 'ml'),
    ('distillate_3p', 'Distillate (3rd Party)', 'DIST', FALSE, NULL, 'received',
     '[{"key":"received","label":"Received"},{"key":"qc_hold","label":"QC Hold"},{"key":"available","label":"Available"},{"key":"in_use","label":"In Use"},{"key":"depleted","label":"Depleted"}]', 'g'),
    ('bho_badder_3p', 'BHO Badder (3rd Party)', 'BADDER', FALSE, NULL, 'received',
     '[{"key":"received","label":"Received"},{"key":"qc_hold","label":"QC Hold"},{"key":"available","label":"Available"},{"key":"in_use","label":"In Use"},{"key":"depleted","label":"Depleted"}]', 'g'),
    ('shatter_3p', 'Shatter (3rd Party)', 'SHATTER', FALSE, NULL, 'received',
     '[{"key":"received","label":"Received"},{"key":"qc_hold","label":"QC Hold"},{"key":"available","label":"Available"},{"key":"in_use","label":"In Use"},{"key":"depleted","label":"Depleted"}]', 'g')
ON CONFLICT (key) DO NOTHING;

-- ── Generic component lots (the spine) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS bpr_component_lots (
    id               BIGSERIAL PRIMARY KEY,
    lot_code         TEXT NOT NULL UNIQUE,
    component_type   TEXT NOT NULL REFERENCES bpr_component_types(key),
    status           TEXT NOT NULL,
    source           TEXT NOT NULL DEFAULT 'produced' CHECK (source IN ('produced','received')),
    metrc_uid        TEXT,
    strain           TEXT,
    description      TEXT,
    initial_qty      NUMERIC(12,3),
    unit             TEXT NOT NULL DEFAULT 'g',
    supplier         TEXT,
    manifest_number  TEXT,
    coa_ref          TEXT,
    legacy_id        UUID UNIQUE,
    storage_location TEXT,
    sheet_url        TEXT,
    type_data        JSONB NOT NULL DEFAULT '{}',
    created_by       TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_component_lots_type_status ON bpr_component_lots (component_type, status);
CREATE INDEX IF NOT EXISTS idx_component_lots_metrc_uid   ON bpr_component_lots (metrc_uid);

-- ── Quantity ledger ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bpr_lot_transactions (
    id              BIGSERIAL PRIMARY KEY,
    lot_id          BIGINT NOT NULL REFERENCES bpr_component_lots(id),
    txn_type        TEXT NOT NULL CHECK (txn_type IN
                        ('production','receipt','consumption','waste','adjustment','metrc_package')),
    qty_delta       NUMERIC(12,3) NOT NULL,
    unit            TEXT NOT NULL,
    reference_type  TEXT,
    reference_id    TEXT,
    note            TEXT,
    performed_by    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lot_txn_lot     ON bpr_lot_transactions (lot_id);
CREATE INDEX IF NOT EXISTS idx_lot_txn_created ON bpr_lot_transactions (created_at);

-- ── Live inventory view (dashboard reads this) ────────────────────────────
CREATE OR REPLACE VIEW v_component_inventory AS
SELECT
    l.id, l.lot_code, l.component_type, t.display_name, l.status, l.source,
    l.strain, l.metrc_uid,
    COALESCE(SUM(x.qty_delta), 0) AS current_qty,
    l.unit, l.storage_location, l.created_at
FROM bpr_component_lots l
JOIN bpr_component_types t ON t.key = l.component_type
LEFT JOIN bpr_lot_transactions x ON x.lot_id = l.id
GROUP BY l.id, t.display_name;

-- ── Input materials for a lot (fresh frozen UIDs feeding a wash, etc.) ───
-- Table keeps its legacy name for now; the hash_lot_id column holds the
-- lot_code of ANY component lot. Rename pass can come later.
CREATE TABLE IF NOT EXISTS hash_lot_inputs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hash_lot_id      TEXT NOT NULL REFERENCES bpr_component_lots(lot_code),
    fresh_frozen_uid TEXT NOT NULL,
    strain_name      TEXT,
    input_weight_g   NUMERIC,
    added_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hash_inputs_lot ON hash_lot_inputs(hash_lot_id);

-- ── Multi-session pipeline tables (wash → freeze-dry → sift) ──────────────
CREATE TABLE IF NOT EXISTS hash_lot_wash_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hash_lot_id         TEXT NOT NULL REFERENCES bpr_component_lots(lot_code),
    session_num         INT NOT NULL,
    operator_name       TEXT NOT NULL,
    equipment_id        TEXT,
    tea_bag_count       INT,
    fresh_frozen_uids   TEXT[],
    wet_weight_g        NUMERIC NOT NULL,
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    ro_water_confirmed  BOOLEAN,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hash_lot_freezedry_sessions (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hash_lot_id           TEXT NOT NULL REFERENCES bpr_component_lots(lot_code),
    session_num           INT NOT NULL,
    operator_name         TEXT NOT NULL,
    equipment_id          TEXT,
    input_wet_weight_g    NUMERIC NOT NULL,
    output_dry_weight_g   NUMERIC,
    started_at            TIMESTAMPTZ,
    completed_at          TIMESTAMPTZ,
    pump_oil_checked      BOOLEAN,
    notes                 TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hash_lot_sift_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hash_lot_id         TEXT NOT NULL REFERENCES bpr_component_lots(lot_code),
    session_num         INT NOT NULL,
    operator_name       TEXT NOT NULL,
    dry_weight_in_g     NUMERIC NOT NULL,
    sift_weight_out_g   NUMERIC,
    storage_location    TEXT,
    completed_at        TIMESTAMPTZ,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hash_lot_wash_to_freezedry_allocations (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wash_session_id       UUID NOT NULL REFERENCES hash_lot_wash_sessions(id),
    freezedry_session_id  UUID NOT NULL REFERENCES hash_lot_freezedry_sessions(id),
    weight_allocated_g    NUMERIC NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hash_lot_freezedry_to_sift_allocations (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    freezedry_session_id  UUID NOT NULL REFERENCES hash_lot_freezedry_sessions(id),
    sift_session_id       UUID NOT NULL REFERENCES hash_lot_sift_sessions(id),
    weight_allocated_g    NUMERIC NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wash_sessions_lot       ON hash_lot_wash_sessions(hash_lot_id);
CREATE INDEX IF NOT EXISTS idx_freezedry_sessions_lot  ON hash_lot_freezedry_sessions(hash_lot_id);
CREATE INDEX IF NOT EXISTS idx_sift_sessions_lot       ON hash_lot_sift_sessions(hash_lot_id);
CREATE INDEX IF NOT EXISTS idx_w2f_wash                ON hash_lot_wash_to_freezedry_allocations(wash_session_id);
CREATE INDEX IF NOT EXISTS idx_w2f_freezedry           ON hash_lot_wash_to_freezedry_allocations(freezedry_session_id);
CREATE INDEX IF NOT EXISTS idx_f2s_freezedry           ON hash_lot_freezedry_to_sift_allocations(freezedry_session_id);
CREATE INDEX IF NOT EXISTS idx_f2s_sift                ON hash_lot_freezedry_to_sift_allocations(sift_session_id);
"""

@app.on_event("startup")
async def startup():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()
    finally:
        conn.close()

# ── Pydantic models (BPR) ─────────────────────────────────────────────────

class BPRCreateRequest(BaseModel):
    uid: str
    product_name: str
    batch_id: Optional[str] = None
    mfg_date: Optional[str] = None
    category: Optional[str] = None
    bpr_type: Optional[str] = None

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

class SupervisorReleaseRequest(BaseModel):
    supervisor_name: str
    deviation_notes: Optional[str] = None
    total_yield: Optional[str] = None

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
    wet_weight_g: Optional[float] = None  # allow correction at close if needed
    notes: Optional[str] = None

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

class SiftSessionCreate(BaseModel):
    operator_name: str
    storage_location: Optional[str] = None
    notes: Optional[str] = None
    allocations: List[dict]  # [{"freezedry_session_id": "...", "weight_allocated_g": 1200}]

class SiftSessionClose(BaseModel):
    sift_weight_out_g: float
    notes: Optional[str] = None

# ── Pydantic models (component lots — generic) ────────────────────────────

class LotInputMaterial(BaseModel):
    fresh_frozen_uid: str
    strain_name: Optional[str] = None
    input_weight_g: Optional[float] = None

class ComponentLotCreate(BaseModel):
    component_type: str                      # must exist in bpr_component_types
    strain: Optional[str] = None
    is_mixed: bool = False                   # affects lot code generation
    description: Optional[str] = None
    initial_qty: Optional[float] = None      # for received lots: opening balance
    metrc_uid: Optional[str] = None          # for received lots: package tag
    supplier: Optional[str] = None
    manifest_number: Optional[str] = None
    coa_ref: Optional[str] = None
    storage_location: Optional[str] = None
    created_by: Optional[str] = None
    type_data: Optional[dict] = None         # type-specific extras (wet_weight_g, etc.)
    inputs: List[LotInputMaterial] = []      # source materials feeding this lot

class ComponentStatusUpdate(BaseModel):
    status: str

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




# ── Helpers ───────────────────────────────────────────────────────────────

def now_utc():
    return datetime.now(timezone.utc).isoformat()

from zoneinfo import ZoneInfo
LOCAL_TZ = ZoneInfo("America/Los_Angeles")

def fmt_ts(ts):
    if not ts:
        return None
    if isinstance(ts, str):
        return ts
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)   # naive DB values are UTC
    return ts.astimezone(LOCAL_TZ).strftime("%-m/%-d/%Y %-I:%M %p")

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

@app.get("/components/types")
def list_component_types():
    """Registry listing — frontends build their type dropdowns from this."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM bpr_component_types ORDER BY display_name")
            types = [dict(r) for r in cur.fetchall()]
        return {"types": types, "count": len(types)}
    finally:
        conn.close()


@app.post("/components")
def create_component_lot(req: ComponentLotCreate):
    conn = get_db()
    try:
        lot = create_component_lot_internal(conn, req)
        return {
            "lot_code": lot["lot_code"],
            "lot": lot,
            "message": f"Component lot created: {lot['lot_code']}. Label the container now."
        }
    finally:
        conn.close()


@app.get("/components/inventory")
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


@app.get("/components/{lot_code}")
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


@app.patch("/components/{lot_code}/status")
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


@app.post("/components/{lot_code}/transactions")
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

@app.post("/hash/create")
def create_hash_lot(req: HashLotCreateRequest):
    conn = get_db()
    try:
        generic_req = ComponentLotCreate(
            component_type="ice_water_hash",
            strain=req.primary_strain,
            is_mixed=req.is_mixed,
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


@app.get("/hash/available")
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
@app.get("/hash/{hash_lot_id}")
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


@app.patch("/hash/{hash_lot_id}/weights")
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


@app.patch("/hash/{hash_lot_id}/status")
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


@app.patch("/hash/{hash_lot_id}/assign-uid")
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

@app.post("/hash/{hash_lot_id}/sanitation")
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
@app.get("/bpr/phases")
def get_all_phases():
    return {"families": BPR_PHASES}

# ─────────────────────────────────────────────────────────────────────────
# GET /bpr/phases/{family}
# ─────────────────────────────────────────────────────────────────────────
@app.get("/bpr/phases/{family}")
def get_phases(family: str):
    if family not in BPR_PHASES:
        raise HTTPException(404, f"No BPR template found for product family: {family}")
    return {"family": family, "definition": BPR_PHASES[family]}

# ─────────────────────────────────────────────────────────────────────────
# POST /bpr/create
# Initializes a BPR record. Idempotent — returns existing if UID already has one.
# NEW in v2.0: writes the BPR id back onto the component lot (wash_bpr_id fix)
# ─────────────────────────────────────────────────────────────────────────
@app.post("/bpr/create")
def create_bpr(req: BPRCreateRequest):
    family = detect_product_family(req.product_name, req.category or "", req.bpr_type or "")
    if not family:
        raise HTTPException(400, f"Could not detect product family for: {req.product_name}")

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Check if exists
            cur.execute("SELECT * FROM bpr_records WHERE uid = %s", (req.uid,))
            existing = cur.fetchone()
            if existing:
                return {
                    "created": False,
                    "bpr": dict(existing),
                    "phases": BPR_PHASES[existing["product_family"]],
                    "message": "BPR already exists for this batch"
                }

            # Create new
            cur.execute("""
                INSERT INTO bpr_records (uid, product_name, batch_id, mfg_date, category, product_family)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (req.uid, req.product_name, req.batch_id, req.mfg_date, req.category, family))
            record = dict(cur.fetchone())

            # Pre-create step check rows for all phases
            definition = BPR_PHASES[family]
            for phase in definition["phases"]:
                for i, _ in enumerate(phase["steps"]):
                    cur.execute("""
                        INSERT INTO bpr_step_checks (bpr_id, uid, phase_id, step_index)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (record["id"], req.uid, phase["id"], i))

            # ── wash_bpr_id fix ─────────────────────────────────────────
            # For wash BPRs the uid IS the lot code. Link the BPR to its
            # component lot server-side so the frontend can never forget to.
            # Harmless no-op if no matching lot exists (finished-goods BPRs).
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
@app.get("/bpr/{uid}")
def get_bpr(uid: str):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM bpr_records WHERE uid = %s", (uid,))
            record = cur.fetchone()
            if not record:
                raise HTTPException(404, "No BPR found for this batch UID")
            record = dict(record)

            cur.execute("""
                SELECT * FROM bpr_phase_signoffs WHERE uid = %s ORDER BY signed_at
            """, (uid,))
            signoffs = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT * FROM bpr_step_checks WHERE uid = %s ORDER BY phase_id, step_index
            """, (uid,))
            steps = [dict(r) for r in cur.fetchall()]

            family = record["product_family"]
            definition = BPR_PHASES.get(family, {})

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
                "family": family
            }
    finally:
        conn.close()

# ─────────────────────────────────────────────────────────────────────────
# POST /bpr/{uid}/step
# ─────────────────────────────────────────────────────────────────────────
@app.post("/bpr/{uid}/step")
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
@app.post("/bpr/{uid}/phase/signoff")
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
            missing_ccps = [i for i in ccps if str(i) not in ccp_values and i not in ccp_values]
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
@app.post("/bpr/{uid}/release")
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

            cur.execute("""
                SELECT phase_id FROM bpr_phase_signoffs WHERE bpr_id = %s
            """, (rec["id"],))
            signed_phases = {r["phase_id"] for r in cur.fetchall()}
            all_phases = {p["id"] for p in definition["phases"]}
            unsigned = all_phases - signed_phases
            if unsigned:
                phase_names = [p["name"] for p in definition["phases"] if p["id"] in unsigned]
                raise HTTPException(400, {
                    "message": "All phases must be signed off before supervisor release",
                    "unsigned_phases": phase_names
                })

            cur.execute("""
                SELECT * FROM bpr_phase_signoffs WHERE bpr_id = %s ORDER BY signed_at
            """, (rec["id"],))
            signoffs = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT * FROM bpr_step_checks WHERE bpr_id = %s ORDER BY phase_id, step_index
            """, (rec["id"],))
            steps = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                UPDATE bpr_records SET
                    status = 'completed',
                    completed_at = %s,
                    supervisor_name = %s,
                    supervisor_at = %s,
                    deviation_notes = %s,
                    total_yield = %s,
                    updated_at = %s
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
        conn.close()

        # Generate PDF + upload to Drive (async, non-blocking for response)
        pdf_url = await generate_and_upload_pdf(completed, definition, signoffs, steps)

        if pdf_url:
            conn2 = get_db()
            try:
                with conn2.cursor() as cur2:
                    cur2.execute("UPDATE bpr_records SET pdf_drive_url = %s WHERE uid = %s",
                                 (pdf_url, uid))
                conn2.commit()
                completed["pdf_drive_url"] = pdf_url
            finally:
                conn2.close()

        # Ping GAS webhook to update BPR_STATUS in UID_TRACKER
        await ping_gas_webhook(uid, "completed", pdf_url)

        # rosin_wash: write the Section 2 source summary + Section 3 yield
        # rollups into the wash BPR sheet now that all numbers are final
        if family == "rosin_wash":
            # Release = the lot becomes press-eligible: flip to 'available'
            # and adopt the sift storage location if the lot has none.
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
            await push_wash_release_summary(uid, req.supervisor_name)

# ─────────────────────────────────────────────────────────────────────────
# GET /bpr/{uid}/status
# ─────────────────────────────────────────────────────────────────────────
@app.get("/bpr/{uid}/status")
def get_bpr_status(uid: str):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT uid, status, product_family, created_at, completed_at,
                       supervisor_name, pdf_drive_url,
                       (SELECT COUNT(*) FROM bpr_phase_signoffs WHERE bpr_id = bpr_records.id) as phases_signed
                FROM bpr_records WHERE uid = %s
            """, (uid,))
            rec = cur.fetchone()
            if not rec:
                return {"exists": False, "uid": uid}

            rec = dict(rec)
            family = rec["product_family"]
            total_phases = len(BPR_PHASES.get(family, {}).get("phases", []))
            return {
                "exists": True,
                "uid": uid,
                "status": rec["status"],
                "product_family": family,
                "phases_signed": rec["phases_signed"],
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
            await client.post(webhook_url, json={
                "action": "updateBPRStatus",
                "uid": uid,
                "bprStatus": status,
                "pdfUrl": pdf_url,
                "secret": os.environ.get("GAS_SHARED_SECRET", ""),
            })
    except Exception as e:
        print(f"GAS webhook ping failed (non-fatal): {e}")

# ── Product family → GAS templateKey (BPR_CELL_MAPS key in BPR.gs) ──
# ── Product family → GAS templateKey (BPR_CELL_MAPS key in BPR.gs) ──
PRODUCT_FAMILY_TO_TEMPLATE_KEY = {
    "gummies":     "punch_gummies",
    "rosin_press": "punch_live_rosin",
    # "rosin_wash" stays on its own dedicated pathway (push_wash_phase_to_gas)
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
    ("pre_production", 4):  3,
    ("pre_production", 5):  3,
    ("pressing", 5):        5,
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

# ── Per-family lookup registries ──
PHASE_TO_STEPS_MAPS = {
    "gummies":     GUMMIES_PHASE_TO_STEPS,
    "rosin_press": LIVE_ROSIN_PHASE_TO_STEPS,
}
CCP_VALUES_MAPS = {
    "gummies":     GUMMIES_CCP_VALUES,
    "rosin_press": LIVE_ROSIN_CCP_VALUES,
}
CANN_VALUES_MAPS = {
    "gummies":     GUMMIES_CANN_VALUES,
    "rosin_press": LIVE_ROSIN_CANN_VALUES,
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
        print(f"GAS BPR write-back failed (non-fatal): {e}")

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


async def _post_wash_gas(payload: dict, label: str):
    """Shared fire-and-forget POST to the GAS webhook."""
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

@app.post("/hash/{hash_lot_id}/wash-session")
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


@app.get("/hash/{hash_lot_id}/wash-sessions")
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


@app.patch("/hash/wash-session/{session_id}")
async def close_wash_session(session_id: str, req: WashSessionClose):
    # async so the Session Log push can fire as a background task —
    # create_task needs a running event loop (the phase_signoff lesson)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE hash_lot_wash_sessions SET
                    completed_at = NOW(),
                    wet_weight_g = COALESCE(%s, wet_weight_g),
                    notes = COALESCE(%s, notes)
                WHERE id = %s
                RETURNING *
            """, (req.wet_weight_g, req.notes, session_id))
            updated = cur.fetchone()
            if not updated:
                raise HTTPException(404, "Wash session not found")
            updated = dict(updated)
        conn.commit()

        # Mirror the closed session into the BPR sheet's Session Log tab
        import asyncio
        asyncio.create_task(push_wash_session_row(updated["hash_lot_id"], "wash", {
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

        return {"session": updated, "message": "Wash session closed"}
    finally:
        conn.close()


# ── FREEZE-DRY SESSIONS + ALLOCATIONS ──────────────────────────

@app.get("/hash/{hash_lot_id}/available-wash-sessions")
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


@app.post("/hash/{hash_lot_id}/freezedry-session")
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


@app.get("/hash/{hash_lot_id}/freezedry-sessions")
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


@app.patch("/hash/freezedry-session/{session_id}")
async def close_freezedry_session(session_id: str, req: FreezeDrySessionClose):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE hash_lot_freezedry_sessions SET
                    completed_at = NOW(),
                    output_dry_weight_g = %s,
                    notes = COALESCE(%s, notes)
                WHERE id = %s
                RETURNING *
            """, (req.output_dry_weight_g, req.notes, session_id))
            updated = cur.fetchone()
            if not updated:
                raise HTTPException(404, "Freeze-dry session not found")
            updated = dict(updated)

            # "S1: 4,000g; S2: 3,500g" — which wash sessions fed this dryer load
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
        asyncio.create_task(push_wash_session_row(updated["hash_lot_id"], "freezedry", {
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

        return {"session": updated, "message": "Freeze-dry session closed"}
    finally:
        conn.close()

# ── SIFT SESSIONS + ALLOCATIONS ─────────────────────────────────

@app.get("/hash/{hash_lot_id}/available-freezedry-sessions")
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


@app.post("/hash/{hash_lot_id}/sift-session")
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


@app.get("/hash/{hash_lot_id}/sift-sessions")
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


@app.patch("/hash/sift-session/{session_id}")
async def close_sift_session(session_id: str, req: SiftSessionClose):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE hash_lot_sift_sessions SET
                    completed_at = NOW(),
                    sift_weight_out_g = %s,
                    notes = COALESCE(%s, notes)
                WHERE id = %s
                RETURNING *
            """, (req.sift_weight_out_g, req.notes, session_id))
            updated = cur.fetchone()
            if not updated:
                raise HTTPException(404, "Sift session not found")
            updated = dict(updated)

            # Which freeze-dry loads fed this sift
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

            # ── LEDGER: inventory is born as sift sessions close ──────────
            # Target = total sift output across ALL closed sessions for this
            # lot; we insert the DELTA vs. what the ledger already shows as
            # produced. Closing session 2 adds only session 2's grams, and
            # RE-closing a session to correct a weight adjusts rather than
            # double-counts — same convergence rule as everywhere else.
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
                                note=f"Sift session {updated['session_num']} closed",
                                performed_by=updated["operator_name"])
        conn.commit()

        import asyncio
        asyncio.create_task(push_wash_session_row(updated["hash_lot_id"], "sift", {
            "session_num":  updated["session_num"],
            "operator":     updated["operator_name"],
            "fd_used":      fd_used,
            "dry_in":       float(updated["dry_weight_in_g"]) if updated["dry_weight_in_g"] is not None else "",
            "sift_out":     float(updated["sift_weight_out_g"]) if updated["sift_weight_out_g"] is not None else "",
            "storage":      updated["storage_location"] or "",
            "completed_at": fmt_ts(updated["completed_at"]) or "",
            "notes":        updated["notes"] or "",
        }))

        return {"session": updated, "message": "Sift session closed"}
    finally:
        conn.close()

@app.get("/hash/{hash_lot_id}/reconciliation")
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
