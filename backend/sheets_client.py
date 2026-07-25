"""
sheets_client.py — Python port of Config.gs + Batches.gs read/write layer.

This is the single source of truth for how the FastAPI backend talks to
UID_TRACKER. Mirrors CONFIG.COL from Config.gs exactly — if the sheet's
columns ever shift, this is the ONE place to update, same principle as
Config.gs itself.
"""

import json
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

    def get_batches(self) -> list[dict]:
        """
        Parses raw rows into batch dicts, mirroring the exact shape
        getAllBatches() returns in Batches.gs (same field names), so the
        frontend JS needs minimal changes when it swaps
        google.script.run calls for fetch() calls against the new API.
        """
        rows = self.get_all_rows()
        batches = []

        for i, row in enumerate(rows):
            row = _pad_row(row, COL["LAST_UPDATED"])
            metrc_uid = row[COL["METRC_UID"] - 1]
            if not metrc_uid:
                continue

            batch_id = row[COL["BATCH_ID"] - 1]
            if not batch_id:
                continue

            batches.append({
                "rowIndex": i + DATA_START_ROW,
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
                "batchSheetURL": row[COL["BATCH_SHEET_URL"] - 1] or "",
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