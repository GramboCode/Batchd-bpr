"""
BatchD BPR — FastAPI backend
Deploy alongside ManifestD on Railway.
All BPR routes are prefixed /bpr

Environment variables required (add to Railway):
  DATABASE_URL           — Railway Postgres connection string (already set for ManifestD)
  GAS_WEBHOOK_URL        — GAS doPost URL to ping on BPR completion
  GOOGLE_SERVICE_ACCOUNT — JSON string of service account credentials (for Drive PDF upload)
  DRIVE_COA_FOLDER_ID    — Root COA Archive folder ID (to find UID subfolders)
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

app = FastAPI(title="BatchD BPR API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to your Netlify/Railway frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health check — defined FIRST to avoid being swallowed by /bpr/{uid} ──
@app.get("/health")
@app.get("/bpr/health")
def health():
    return {"status": "ok", "service": "BatchD BPR", "version": "1.0.0"}

# ── DB connection ─────────────────────────────────────────────────────────
def get_db():
    return psycopg2.connect(
        os.environ["DATABASE_URL"],
        cursor_factory=psycopg2.extras.RealDictCursor
    )

# ── Schema init ───────────────────────────────────────────────────────────
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

# ── Pydantic models ───────────────────────────────────────────────────────

class BPRCreateRequest(BaseModel):
    uid: str
    product_name: str
    batch_id: Optional[str] = None
    mfg_date: Optional[str] = None
    category: Optional[str] = None

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

# ── Helper: now() UTC ─────────────────────────────────────────────────────
def now_utc():
    return datetime.now(timezone.utc).isoformat()

# ── Helper: format timestamp for display ─────────────────────────────────
def fmt_ts(ts):
    if not ts:
        return None
    if isinstance(ts, str):
        return ts
    return ts.strftime("%-m/%-d/%Y %-I:%M %p")

# ─────────────────────────────────────────────────────────────────────────
# GET /bpr/phases
# Returns all supported product families and their phase structures
# ─────────────────────────────────────────────────────────────────────────
@app.get("/bpr/phases")
def get_all_phases():
    return {"families": BPR_PHASES}

# ─────────────────────────────────────────────────────────────────────────
# GET /bpr/phases/{family}
# Returns phase structure for a specific product family
# ─────────────────────────────────────────────────────────────────────────
@app.get("/bpr/phases/{family}")
def get_phases(family: str):
    if family not in BPR_PHASES:
        raise HTTPException(404, f"No BPR template found for product family: {family}")
    return {"family": family, "definition": BPR_PHASES[family]}

# ─────────────────────────────────────────────────────────────────────────
# POST /bpr/create
# Initializes a BPR record. Idempotent — returns existing if UID already has one.
# ─────────────────────────────────────────────────────────────────────────
@app.post("/bpr/create")
def create_bpr(req: BPRCreateRequest):
    family = detect_product_family(req.product_name, req.category or "")
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
# Returns full BPR state: record + all signoffs + all step checks
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

            # Build signoff map: phase_id -> signoff object
            signoff_map = {s["phase_id"]: s for s in signoffs}

            # Build step check map: phase_id:step_index -> checked bool
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
# Toggle a step check on/off
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
# Sign off an entire phase — requires all non-CCP steps checked,
# all CCP values provided
# ─────────────────────────────────────────────────────────────────────────
@app.post("/bpr/{uid}/phase/signoff")
def phase_signoff(uid: str, req: PhaseSignoffRequest):
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

            # Find the phase definition
            phase_def = next((p for p in definition["phases"] if p["id"] == req.phase_id), None)
            if not phase_def:
                raise HTTPException(404, f"Phase {req.phase_id} not found in {family} template")

            # Validate all steps are checked
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

            # Validate CCP values provided for CCP steps
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

            # Validate notes if required
            if phase_def.get("notes_required") and not (req.notes or "").strip():
                raise HTTPException(400, {"message": "Notes are required before signing off this phase"})

            # Write signoff
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
        # Get step checks for this phase to include in write-back
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
# Supervisor release — completes the BPR, triggers PDF generation
# and Drive upload, pings GAS webhook
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

            # Confirm all phases are signed off
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

            # Get all signoffs for PDF
            cur.execute("""
                SELECT * FROM bpr_phase_signoffs WHERE bpr_id = %s ORDER BY signed_at
            """, (rec["id"],))
            signoffs = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT * FROM bpr_step_checks WHERE bpr_id = %s ORDER BY phase_id, step_index
            """, (rec["id"],))
            steps = [dict(r) for r in cur.fetchall()]

            # Mark as completed
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

        return {
            "success": True,
            "bpr": completed,
            "pdf_url": pdf_url,
            "message": f"BPR released and completed by {req.supervisor_name}"
        }
    finally:
        conn.close()

# ─────────────────────────────────────────────────────────────────────────
# GET /bpr/{uid}/status
# Quick status check — used by GAS batch detail page
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
    Uploads BPR PDF to the UID's subfolder inside COA Archive on Google Drive.
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

        # Find the UID subfolder inside COA Archive
        root_folder_id = os.environ.get("DRIVE_COA_FOLDER_ID")
        if not root_folder_id:
            print("No DRIVE_COA_FOLDER_ID env var — skipping Drive upload")
            return None

        # Search for UID folder
        results = service.files().list(
            q=f"name='{uid}' and '{root_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name)"
        ).execute()
        folders = results.get("files", [])

        if not folders:
            # Create UID folder
            folder_meta = {
                "name": uid,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [root_folder_id]
            }
            folder = service.files().create(body=folder_meta, fields="id").execute()
            folder_id = folder["id"]
        else:
            folder_id = folders[0]["id"]

        # Upload PDF
        filename = f"BPR_{batch_id or uid}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        file_meta = {"name": filename, "parents": [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype="application/pdf")
        file = service.files().create(
            body=file_meta, media_body=media, fields="id, webViewLink"
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
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(webhook_url, json={
                "action": "updateBPRStatus",
                "uid": uid,
                "bprStatus": status,
                "pdfUrl": pdf_url
            })
    except Exception as e:
        print(f"GAS webhook ping failed (non-fatal): {e}")

async def push_phase_to_gas_bpr(uid: str, phase_id: str, phase_def: dict, 
                                  signoff: dict, steps: list, product_family: str):
    """
    Builds the named-range field map from a completed phase signoff
    and POSTs it to GAS serverWriteBPRFields.
    Only handles live_rosin for now — extend per product family.
    """
    webhook_url = os.environ.get("GAS_WEBHOOK_URL")
    if not webhook_url:
        print("No GAS_WEBHOOK_URL — skipping BPR write-back")
        return

    if product_family != "live_rosin":
        print(f"BPR write-back not yet implemented for {product_family} — skipping")
        return

    # Build step map for this phase: step_index -> {checked_by, checked_at}
    step_map = {}
    for s in steps:
        if s["phase_id"] == phase_id:
            step_map[s["step_index"]] = s

    # CCP-only mapping: (phase_id, step_index) -> Section 4 sheet row number (1-21)
    # Verified against actual BPR sheet Step Description column
    LIVE_ROSIN_CCP_ROW_MAP = {
        # Row 1  — Verify washers/bags/trays cleaned (pre_production step 2 = equipment clean)
        ("pre_production", 2):  1,
        # Row 2  — Verify fresh frozen COA, record METRC UID, strain, input weight
        ("pre_production", 1):  2,
        # Row 3  — Tea bags at 4,000g wet weight on certified scale
        ("ice_water_wash", 0):  3,
        # Row 4  — Load washers with ice and water
        ("ice_water_wash", 1):  4,
        # Row 5  — Run 2 full wash cycles, record start/end times
        ("ice_water_wash", 2):  5,
        # Row 6  — Drain water, collect hash on tray
        ("ice_water_wash", 3):  6,
        # Row 7  — Record WET WEIGHT of hash on tray
        ("ice_water_wash", 6):  7,
        # Row 8  — Cannabis by-product in waste receptacle, record in Waste Log
        ("ice_water_wash", 9):  8,
        # Row 9  — Check pump oil, insert trays into freeze dryer ≤35°F
        ("freeze_drying",  3):  9,
        # Row 10 — Inspect periodically, break up thick portions
        ("freeze_drying",  4): 10,
        # Row 11 — Sift dried hash, record DRY SIFT WEIGHT
        ("freeze_drying",  6): 11,
        # Row 12 — Open valve, defrost, vacuum seal, store in freezer
        ("freeze_drying",  7): 12,
        # Row 13 — No CCP marker (mold hash into rectangles) — skip
        # Row 14 — Preheat rosin press to 162°F
        ("pressing",       2): 14,
        # Row 15 — Press with foot trigger
        ("pressing",       3): 15,
        # Row 16 — Weigh rosin yield, record press waste
        ("pressing",       6): 16,
        # Row 17 — Wipe CR jars, calibrate scale, weigh 1.0–1.05g per jar
        ("packaging",      1): 17,
        # Row 18 — No CCP (apply CR cap) — skip
        # Row 19 — Apply required info sticker, all 5 fields, supervisor approval
        ("packaging",      4): 19,
        # Row 20 — No CCP (post-production clean-down) — skip
        # Row 21 — METRC manufacturing activity entry within 24 hours
        ("sanitation",     6): 21,
    }

    fields = {}
    signed_at = fmt_ts(signoff.get("signed_at")) or ""
    employee  = signoff.get("employee_name") or ""

    # Parse CCP values once
    ccp_values = signoff.get("ccp_values") or {}
    if isinstance(ccp_values, str):
        try: ccp_values = json.loads(ccp_values)
        except: ccp_values = {}

    # Write only CCP steps to Section 4 named ranges
    for (p_id, step_idx), sheet_row in LIVE_ROSIN_CCP_ROW_MAP.items():
        if p_id != phase_id:
            continue  # only process rows belonging to current phase

        val = ccp_values.get(str(step_idx)) or ccp_values.get(step_idx) or ""
        prefix = f"ROSIN_S4_STEP{sheet_row}"

        step_data = step_map.get(step_idx, {})
        checked_at = fmt_ts(step_data.get("checked_at")) if step_data.get("checked_at") else signed_at
        checked_by = step_data.get("checked_by") or employee

        fields[prefix + "_DATE"]     = checked_at[:10] if checked_at else ""
        fields[prefix + "_OP1"]      = checked_by
        fields[prefix + "_VERIFIED"] = "✓" if step_data.get("checked") else ""
        fields[prefix + "_VALUE"]    = val
        fields[prefix + "_PASSFAIL"] = "Pass" if val else ""

    # Section 5 — yield fields
    if phase_id == "qc_yield":
        fields["ROSIN_S5_YIELD_ACTUAL"]  = ccp_values.get("4") or ccp_values.get(4) or ""
        fields["ROSIN_S5_INITIALS"]      = employee
        fields["ROSIN_S5_TIME_RECORDED"] = signed_at

    if phase_id == "packaging":
        fields["ROSIN_S5_LABEL_COUNT"] = ccp_values.get("6") or ccp_values.get(6) or ""

    # Section 6 CCP monitoring rows — verified against sheet CCP list
    PHASE_CCP_MAP = {
        "ice_water_wash": {
            0: 1,   # Tea bag fill weight → CCP 1
            2: 3,   # Wash cycles completed → CCP 3
            6: 4,   # Wet weight recorded → CCP 4
            9: 5,   # Cannabis waste logged → CCP 5
        },
        "freeze_drying": {
            3: 6,   # Freeze dryer temp ≤35°F → CCP 6
            3: 7,   # Pump oil level checked → CCP 7
            6: 8,   # Dry sift weight recorded → CCP 8
        },
        "pressing": {
            2: 9,   # Rosin press temp → CCP 9
            6: 10,  # Rosin yield weight → CCP 10
            6: 11,  # Press waste logged → CCP 11
        },
        "packaging": {
            1: 12,  # Jar fill weight spot-check → CCP 12
            4: 13,  # Label all 5 fields → CCP 13
        },
        "pre_production": {
            2: 2,   # RO water confirmed → CCP 2
        },
    }

    phase_ccp_map = PHASE_CCP_MAP.get(phase_id, {})
    for step_idx, ccp_row in phase_ccp_map.items():
        val = ccp_values.get(str(step_idx)) or ccp_values.get(step_idx) or ""
        prefix = f"ROSIN_S6_CCP{ccp_row}"
        fields[prefix + "_ACTUAL"]   = val
        fields[prefix + "_TIME"]     = signed_at
        fields[prefix + "_PASSFAIL"] = "Pass" if val else ""
        fields[prefix + "_OP"]       = employee

    if not fields:
        print(f"push_phase_to_gas_bpr: no fields to write for phase {phase_id}")
        return

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(webhook_url, json={
                "action": "writeBPRFields",
                "uid":    uid,
                "fields": fields
            })
            print(f"GAS BPR write-back: {resp.status_code} — {resp.text[:200]}")
    except Exception as e:
        print(f"GAS BPR write-back failed (non-fatal): {e}")


# Health check is defined at the top of this file above all /bpr/{uid} routes
