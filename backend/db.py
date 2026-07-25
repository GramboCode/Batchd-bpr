"""
db.py — single database connection point for the whole backend.

Before this split, bpr_api.py had its own get_db() and any new module
(sheets_client.py, tracker router, etc.) would have needed to either import
from that giant file or duplicate the function. Neither is good — this is
the one place a Postgres connection gets made, and everything else imports
it from here.
"""

import psycopg2
import psycopg2.extras

from config import DATABASE_URL


def get_db():
    """
    Returns a new psycopg2 connection with dict-style row access
    (row["column_name"] instead of row[0]) — identical behavior to what
    bpr_api.py already does, just centralized.

    NOTE: this opens a fresh connection per call, matching the existing
    pattern in bpr_api.py (connect -> use -> conn.close() in a finally
    block). That's fine at current traffic levels. If concurrent users
    grow significantly, this is the first place to introduce a connection
    pool (e.g. psycopg2.pool.SimpleConnectionPool) -- flagging it now so
    it's not a surprise later, not because it needs fixing today.
    """
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


# The full table-creation DDL, moved verbatim from bpr_api.py's SCHEMA
# constant (lines 110-359 of the original file). It lived next to
# get_db() there; it lives next to get_db() here -- same relationship,
# new address. Nothing in the actual SQL changed in this move.
SCHEMA = """
CREATE TABLE IF NOT EXISTS bpr_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    uid             TEXT NOT NULL UNIQUE,
    metrc_uid       TEXT,
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
CREATE INDEX IF NOT EXISTS idx_bpr_metrc_uid ON bpr_records(metrc_uid);
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

-- Correction audit trail — stays NULL on a normal first close; only
-- populated when a session that was ALREADY closed gets its weight
-- corrected. Lets the sheet/PDF distinguish "recorded once" from
-- "recorded, then someone fixed a mistake."
ALTER TABLE hash_lot_wash_sessions      ADD COLUMN IF NOT EXISTS corrected_by TEXT, ADD COLUMN IF NOT EXISTS corrected_at TIMESTAMPTZ;
ALTER TABLE hash_lot_freezedry_sessions ADD COLUMN IF NOT EXISTS corrected_by TEXT, ADD COLUMN IF NOT EXISTS corrected_at TIMESTAMPTZ;
ALTER TABLE hash_lot_sift_sessions      ADD COLUMN IF NOT EXISTS corrected_by TEXT, ADD COLUMN IF NOT EXISTS corrected_at TIMESTAMPTZ;

-- Tray/pull weigh-ins logged DURING an open session, before it closes.
-- One shared table for all three stages — same shape, different session table.
CREATE TABLE IF NOT EXISTS hash_lot_tray_weighins (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hash_lot_id  TEXT NOT NULL REFERENCES bpr_component_lots(lot_code),
    stage        TEXT NOT NULL CHECK (stage IN ('wash','freezedry','sift')),
    session_id   UUID NOT NULL,
    tray_label   TEXT,
    weight_g     NUMERIC NOT NULL,
    recorded_by  TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tray_weighins_session ON hash_lot_tray_weighins(session_id);


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


def init_schema():
    """
    Runs the full CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS
    block. Safe to call every time the app boots -- IF NOT EXISTS means
    it's a no-op on every startup after the first. Called from main.py's
    startup event, replacing bpr_api.py's old @app.on_event("startup").
    """
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()
    finally:
        conn.close()
