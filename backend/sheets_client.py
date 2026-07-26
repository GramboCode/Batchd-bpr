"""
sheets_client.py — Python port of Config.gs + Batches.gs read/write layer.

This is the single source of truth for how the FastAPI backend talks to
UID_TRACKER. Mirrors CONFIG.COL from Config.gs exactly — if the sheet's
columns ever shift, this is the ONE place to update, same principle as
Config.gs itself.
"""

import json
import re
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build

from config import (
    TRACKER_SS_ID,
    TRACKER_TAB,
    DATA_START_ROW,
    GOOGLE_SERVICE_ACCOUNT,
)

# Column map — 1-based to match Config.gs COL exactly. Keeping the same
# numbers (not 0-based) is deliberate: makes cross-referencing Config.gs
# and this file trivial when debugging a specific cell.
COL = {
    "CHECKBOX": 1,
    "METRC_UID": 2,
    "ITEM": 3,
    "CATEGORY": 4,
    "ITEM_STRAIN": 5,
    "BATCH_ID": 6,
    "MFG_DATE": 7,
    "QUANTITY": 8,
    "UNIT_OF_MEASURE": 9,
    "LAB": 10,
    "STATUS": 11,
    "TEST_DATE": 12,
    "MRID_LABEL": 13,
    "TARGET_QTY": 14,
    "BATCH_SHEET_URL": 15,
    "RETAIL_ID_MADE": 16,
    "METRC_SYNCED": 17,
    "LAB_SAMPLE_ID_RND": 18,
    "LAB_SAMPLE_ID_COA": 19,
    "LAB_RESULTS_URL": 20,
    "CREATED_AT": 21,
    "LAST_UPDATED": 22,
    "COA_LINK": 23,
    "THC_PCT": 24,
    "THC_MG_G": 25,
    "THC_MG_PKG": 26,
    "CBD_PCT": 27,
    "CBD_MG_G": 28,
    "CBD_MG_PKG": 29,
    "TOTAL_CB_PCT": 30,
    "TOTAL_CB_MG_G": 31,
    "TOTAL_CB_MG_PKG": 32,
    "RND_THC_MG_PKG": 33,
    "LABEL_CLAIM_MG": 34,
    "TOLERANCE_FLAG": 35,
    "BPR_STATUS": 36,
    "BPR_PDF_URL": 37,
}

# Statuses that drop a batch off the "active" dashboard view — mirrors
# the SKIP_STATUSES list in Batches.gs's getAllBatches().
INACTIVE_STATUSES = {
    "compliance passed",
    "passed but not avail in distru",
    "avail in distru/on menu",
    "archived",
}

# The product catalog tab — same spreadsheet as UID_TRACKER (see
# migrate_templates.gs), replacing GAS's PropertiesService-backed
# getProductTemplates(). One row per product key: brand/label/category/
# uom/type/fields/pattern/hint as flat columns, everything else
# (flavors, formats, tiers, defaults — whatever varies by product type)
# packed into a JSON blob in the last column.
PRODUCT_CATALOG_TAB = "Product Catalog"

# Batch IDs are split into "everything before the trailing digits" and
# "the trailing digits themselves" — e.g. "TCAVSTRBTZ005" -> prefix
# "TCAVSTRBTZ", suffix "005", but just as validly "HASH-ALIENO-0724-02"
# -> prefix "HASH-ALIENO-0724-", suffix "02". Non-greedy .*? is what
# makes this find the LONGEST trailing run of digits rather than
# stopping at the first digit it sees. Matches getNextBatchID's real
# regex exactly (confirmed against WebApp.gs) — an earlier version of
# this file used an alpha-only prefix pattern that silently failed on
# any hyphenated batch ID.
_BATCH_ID_SPLIT = re.compile(r"^(.*?)(\d+)$")


class SheetsClient:
    """
    Thin wrapper around the Sheets API v4, scoped to UID_TRACKER.
    One instance per FastAPI process — the underlying googleapiclient
    service object is safe to reuse across requests (not per-user
    stateful), so it's built once at startup via get_sheets_client(),
    not per-request.
    """

    def __init__(self):
        if not GOOGLE_SERVICE_ACCOUNT:
            raise RuntimeError(
                "GOOGLE_SERVICE_ACCOUNT is not set. In Railway, paste the "
                "full service account JSON as this variable's value."
            )
        creds_info = json.loads(GOOGLE_SERVICE_ACCOUNT)
        self.creds = service_account.Credentials.from_service_account_info(
            creds_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        self.service = build("sheets", "v4", credentials=self.creds)
        self._sheet = self.service.spreadsheets()

    def _col_letter(self, col_num: int) -> str:
        """1 -> A, 2 -> B, ... 27 -> AA. Same logic Sheets uses internally."""
        letters = ""
        while col_num > 0:
            col_num, remainder = divmod(col_num - 1, 26)
            letters = chr(65 + remainder) + letters
        return letters

    def get_all_rows(self) -> list[list]:
        """
        Raw pull of every data row from DATA_START_ROW to LAST_UPDATED col.
        Direct equivalent of getAllBatches()'s range read in Batches.gs.
        Deliberately does NOT filter by status here — filtering happens
        in the caller so the finished-goods dashboard and any future
        component-focused view can apply different rules against the
        same raw pull.
        """
        last_col_letter = self._col_letter(COL["LAST_UPDATED"])
        range_name = f"{TRACKER_TAB}!A{DATA_START_ROW}:{last_col_letter}"
        result = self._sheet.values().get(
            spreadsheetId=TRACKER_SS_ID,
            range=range_name,
        ).execute()
        return result.get("values", [])

    def get_folder_urls(self) -> dict[int, str]:
        """
        Returns {row_index: folder_url}, one entry per row that has a
        Drive folder link on its ITEM cell.

        This is the Python side of what GAS's getBatchByUID() does with
        getRichTextValue().getLinkUrl() — the folder link isn't a plain
        cell value, it's a hyperlink attached to the cell, which the
        values().get() endpoint used everywhere else in this file simply
        can't see. Reading it requires spreadsheets.get() with an
        explicit `fields` mask instead.

        Pulled as one bulk call for the whole Item column rather than
        per-row (which is what the old GAS fallback path did) — same
        total data, one API round trip instead of one per batch.
        """
        item_col_letter = self._col_letter(COL["ITEM"])
        range_name = f"{TRACKER_TAB}!{item_col_letter}{DATA_START_ROW}:{item_col_letter}"
        result = self._sheet.get(
            spreadsheetId=TRACKER_SS_ID,
            ranges=[range_name],
            fields="sheets.data.rowData.values.hyperlink",
        ).execute()

        urls: dict[int, str] = {}
        try:
            row_data = result["sheets"][0]["data"][0].get("rowData", [])
        except (KeyError, IndexError):
            return urls

        for i, row in enumerate(row_data):
            values = row.get("values", [])
            if values and values[0].get("hyperlink"):
                urls[i + DATA_START_ROW] = values[0]["hyperlink"]
        return urls

    def get_batches(self) -> list[dict]:
        """
        Parses raw rows into batch dicts, mirroring the exact shape
        getAllBatches() returns in Batches.gs (same field names), so the
        frontend JS needs minimal changes when it swaps
        google.script.run calls for fetch() calls against the new API.
        """
        rows = self.get_all_rows()
        folder_urls = self.get_folder_urls()
        batches = []

        for i, row in enumerate(rows):
            row = _pad_row(row, COL["LAST_UPDATED"])
            metrc_uid = row[COL["METRC_UID"] - 1]
            if not metrc_uid:
                continue

            batch_id = row[COL["BATCH_ID"] - 1]
            if not batch_id:
                continue

            row_index = i + DATA_START_ROW

            batches.append({
                "rowIndex": row_index,
                "metrcUID": str(metrc_uid).strip(),
                "item": row[COL["ITEM"] - 1] or "",
                "category": row[COL["CATEGORY"] - 1] or "",
                "itemStrain": row[COL["ITEM_STRAIN"] - 1] or "",
                "batchID": batch_id or "",
                "mfgDate": row[COL["MFG_DATE"] - 1] or "",
                "quantity": row[COL["QUANTITY"] - 1] or "",
                "targetQty": row[COL["TARGET_QTY"] - 1] or "",
                "uom": row[COL["UNIT_OF_MEASURE"] - 1] or "",
                "lab": row[COL["LAB"] - 1] or "",
                "status": row[COL["STATUS"] - 1] or "",
                "testDate": row[COL["TEST_DATE"] - 1] or "",
                "mridLabel": row[COL["MRID_LABEL"] - 1] or "",
                # batchSheetURL dropped — confirmed dead now that the folder
                # system replaced it (column write was removed on the GAS
                # side too, to free up space on the sheet). folderURL is
                # the real, live link every batch actually has.
                "folderURL": folder_urls.get(row_index, ""),
                "retailIDMade": row[COL["RETAIL_ID_MADE"] - 1] is True,
                "metrcSynced": row[COL["METRC_SYNCED"] - 1] is True,
                "labSampleIDRND": row[COL["LAB_SAMPLE_ID_RND"] - 1] or "",
                "labSampleIDCOA": row[COL["LAB_SAMPLE_ID_COA"] - 1] or "",
                "labResultsURL": row[COL["LAB_RESULTS_URL"] - 1] or "",
                "createdAt": row[COL["CREATED_AT"] - 1] or "",
                "lastUpdated": row[COL["LAST_UPDATED"] - 1] or "",
                "isAssigned": bool(batch_id),
            })

        return batches

    def get_active_batches(self) -> list[dict]:
        """
        Same as getAllBatches()'s SKIP_STATUSES filter — drops terminal/
        inactive rows so the dashboard isn't scrolling through years of
        completed history by default.
        """
        return [
            b for b in self.get_batches()
            if b["status"].strip().lower() not in INACTIVE_STATUSES
        ]

    def get_batch_by_uid(self, uid: str) -> dict | None:
        """Direct port of getBatchByUID's primary lookup path."""
        target = uid.strip().lower()
        for b in self.get_batches():
            if b["metrcUID"].strip().lower() == target:
                return b
        return None

    def get_batch_by_batch_id(self, batch_id: str) -> dict | None:
        """Direct port of getBatchByBatchID."""
        target = (batch_id or "").strip().lower()
        if not target:
            return None
        for b in self.get_batches():
            if b["batchID"].strip().lower() == target:
                return b
        return None

    def _get_next_batch_id(self, batch_id: str, existing_ids: set[str]) -> str | None:
        """
        Direct port of getNextBatchID. Splits into prefix + numeric
        suffix, then increments — checking against every existing batch
        ID, not just the ones matching this prefix — so a gap from an
        out-of-sequence batch doesn't get suggested as if it were free.
        Gives up after 50 attempts (same cap as the original) rather
        than looping forever if something's gone very wrong with the ID
        sequence.
        """
        m = _BATCH_ID_SPLIT.match(batch_id)
        if not m:
            return None

        prefix, num_str = m.group(1), m.group(2)
        pad_len = len(num_str)
        num = int(num_str)

        for _ in range(50):
            num += 1
            candidate = f"{prefix}{str(num).zfill(pad_len)}"
            if candidate not in existing_ids:
                return candidate
        return None

    def search_batch_prefix(self, typed: str) -> list[dict]:
        """
        Port of serverSearchBatchPrefix (confirmed against WebApp.gs).
        Filters every batch whose ID STARTS WITH what's been typed so
        far (against the whole ID, not just an alpha-only portion —
        an earlier version of this file matched incorrectly here),
        then groups those matches by their alpha-prefix (everything
        before the trailing digit run) and keeps the highest-numbered
        one per group. Suggestions are computed against the FULL set of
        every batch ID in the sheet, not just the matches, since a
        collision could exist under the same prefix but outside the
        typed-so-far filter. Capped at 8 results, matching the original.
        """
        typed = (typed or "").strip().upper()
        if len(typed) < 3:
            return []

        all_batches = self.get_batches()
        all_batch_ids = {
            (b["batchID"] or "").strip().upper()
            for b in all_batches
            if b["batchID"]
        }

        groups: dict[str, dict] = {}
        for b in all_batches:
            batch_id = (b["batchID"] or "").strip().upper()
            if not batch_id.startswith(typed):
                continue

            m = _BATCH_ID_SPLIT.match(batch_id)
            if not m:
                continue
            alpha, digits = m.group(1), m.group(2)
            num = int(digits)

            existing = groups.get(alpha)
            if existing is None or num > existing["latest_num"]:
                groups[alpha] = {
                    "latest_num": num,
                    "latest_id": batch_id,
                    "item": b["item"],
                    "status": b["status"],
                }

        matches = []
        for alpha in sorted(groups.keys()):
            g = groups[alpha]
            matches.append({
                "alphaPrefix": alpha,
                "item": g["item"],
                "latestBatchID": g["latest_id"],
                "nextBatchID": self._get_next_batch_id(g["latest_id"], all_batch_ids),
                "status": g["status"],
            })
        return matches[:8]

    def check_batch_id_availability(self, batch_id: str) -> dict:
        """
        Port of serverCheckBatchID (confirmed against WebApp.gs). The
        original checks the exact typed ID against every existing batch
        ID directly (not just prefix matches), then — only if taken —
        computes a suggestion via the same getNextBatchID logic search_
        batch_prefix uses, seeded against the FULL set of batch IDs.
        """
        batch_id = (batch_id or "").strip().upper()
        if len(batch_id) < 3:
            return {"available": None, "assignedTo": None, "suggestion": None}

        all_batches = self.get_batches()
        existing = next(
            (b for b in all_batches if (b["batchID"] or "").strip().upper() == batch_id),
            None,
        )

        if not existing:
            return {"available": True, "assignedTo": None, "suggestion": None}

        all_batch_ids = {
            (b["batchID"] or "").strip().upper()
            for b in all_batches
            if b["batchID"]
        }
        suggestion = self._get_next_batch_id(batch_id, all_batch_ids)

        return {
            "available": False,
            "assignedTo": existing["item"] or "Unknown item",
            "suggestion": suggestion,
        }

    def get_next_available_uid(self) -> dict | None:
        """
        Port of getNextAvailableUID(). Scans from the BOTTOM of the sheet
        upward — this direction is deliberate, not arbitrary: importUIDs()
        inserts newly-imported tags at the TOP (row DATA_START_ROW),
        pushing existing rows down, in descending sort order. Scanning
        bottom-up therefore finds the OLDEST still-unassigned tag first,
        consuming tags in roughly the order they were imported rather
        than always grabbing the newest batch. Getting this backwards
        would still "work" (any unassigned UID gets returned) but would
        quietly change which tags get used first.

        Returns None if every imported tag is already assigned to a
        batch — caller is responsible for the "import more tags" message.
        """
        rows = self.get_all_rows()
        for i in range(len(rows) - 1, -1, -1):
            row = _pad_row(rows[i], COL["BATCH_ID"])
            metrc_uid = row[COL["METRC_UID"] - 1]
            batch_id = row[COL["BATCH_ID"] - 1]
            if metrc_uid and not batch_id:
                return {"uid": str(metrc_uid).strip(), "rowIndex": i + DATA_START_ROW}
        return None

    def get_product_templates(self) -> dict:
        """
        Reads the Product Catalog tab and rehydrates each row back into
        the same flat template shape GAS's getProductTemplates() returned
        — brand/label/category/uom/type/fields/pattern/hint as top-level
        keys, plus whatever that row's options_json holds (flavors,
        formats, tiers, defaults) merged in on top. The frontend's product
        tile picker and buildNameFromPattern() logic expect exactly this
        shape, so this is a straight rehydration, not a redesign.

        A malformed options_json on one row degrades to an empty dict
        for that row rather than taking down the whole endpoint — one
        bad row from a manual edit shouldn't block every other product
        from loading.
        """
        range_name = f"{PRODUCT_CATALOG_TAB}!A2:J"  # skip header row
        result = self._sheet.values().get(
            spreadsheetId=TRACKER_SS_ID,
            range=range_name,
        ).execute()
        rows = result.get("values", [])

        templates: dict = {}
        for row in rows:
            row = _pad_row(row, 10)
            key = row[0].strip() if row[0] else ""
            if not key:
                continue

            fields_str = row[6] or ""
            options_str = row[9] or ""

            try:
                options = json.loads(options_str) if options_str.strip() else {}
            except json.JSONDecodeError:
                options = {}

            template = {
                "brand": row[1] or "",
                "label": row[2] or "",
                "category": row[3] or "",
                "uom": row[4] or "",
                "type": row[5] or "",
                "fields": [f.strip() for f in fields_str.split(",") if f.strip()],
                "pattern": row[7] or "",
                "hint": row[8] or "",
            }
            template.update(options)  # flavors/formats/tiers/defaults, per-row

            templates[key] = template

        return templates

    def update_status(self, uid: str, status: str) -> bool:
        """Port of updateBatchStatus. Writes STATUS + LAST_UPDATED cols."""
        batch = self.get_batch_by_uid(uid)
        if not batch:
            return False

        row = batch["rowIndex"]
        status_col = self._col_letter(COL["STATUS"])
        updated_col = self._col_letter(COL["LAST_UPDATED"])
        now = datetime.utcnow().isoformat()

        self._sheet.values().batchUpdate(
            spreadsheetId=TRACKER_SS_ID,
            body={
                "valueInputOption": "USER_ENTERED",
                "data": [
                    {"range": f"{TRACKER_TAB}!{status_col}{row}", "values": [[status]]},
                    {"range": f"{TRACKER_TAB}!{updated_col}{row}", "values": [[now]]},
                ],
            },
        ).execute()
        return True


def _pad_row(row: list, min_len: int) -> list:
    """Sheets API omits trailing empty cells — pad so index access is safe."""
    if len(row) < min_len:
        row = row + [""] * (min_len - len(row))
    return row


# Singleton — built once, lazily, the first time a route needs it. Not
# built at import time, since that would make the whole app fail to boot
# if GOOGLE_SERVICE_ACCOUNT is missing, even for routes that don't touch
# Sheets at all (matches how db.py's get_db() is lazy per-call, not
# eager at import).
_sheets_client: SheetsClient | None = None


def get_sheets_client() -> SheetsClient:
    global _sheets_client
    if _sheets_client is None:
        _sheets_client = SheetsClient()
    return _sheets_client