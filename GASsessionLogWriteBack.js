// ============================================================
// SessionLogWriteback.gs — Punch Tools
// Wash BPR write-back handlers. Receives 'writeWashBPRFields'
// and 'appendWashSessionLog' webhook actions from the Railway
// backend (BPR_api.py v2.1.0).
//
// Design note: these open the target spreadsheet by URL, which
// the backend stores on the component lot at creation time.
// No name searches, no UID lookups — deterministic by design
// (same lesson as the COA Archive folder-ID fix).
// ============================================================

/**
 * Writes a map of { namedRangeName: value } into the wash BPR spreadsheet.
 * Unknown range names are logged and skipped — a template tweak can never
 * crash a production write; you just see the miss in the execution log.
 */
function serverWriteWashBPRFields(sheetUrl, fields) {
  if (!sheetUrl) return { success: false, error: 'sheetUrl missing' };
  try {
    const ss = SpreadsheetApp.openByUrl(sheetUrl);
    let written = 0;
    const missing = [];
    for (const name in fields) {
      const range = ss.getRangeByName(name);
      if (range) {
        range.setValue(fields[name]);
        written++;
      } else {
        missing.push(name);
      }
    }
    if (missing.length) {
      Logger.log('writeWashBPRFields — ranges not found: ' + missing.join(', '));
    }
    return { success: true, written: written, missing: missing };
  } catch (e) {
    Logger.log('serverWriteWashBPRFields error: ' + e.message);
    return { success: false, error: e.message };
  }
}

// ── SESSION LOG LAYOUT ────────────────────────────────────────
// Three fixed blocks on the 'Ice Extraction Session Log' tab.
// dataStart rows confirmed by DKing 7/11: wash 5, freeze-dry 38, sift 71.
// dataEnd is each block's last usable row before the next block's header —
// adjust if the template gives blocks more/less room.
// ⚠ VERIFY the column letters against the template header row, especially
// started_at / completed_at in the freezedry and sift blocks.
const WASH_SESSION_LOG = {
  TAB: 'Ice Extraction Session Log',
  BLOCKS: {
    wash: {
      dataStart: 5, dataEnd: 35,
      cols: {
        session_num:  'A',
        operator:     'B',
        equipment:    'C',
        tea_bags:     'D',
        wet_weight:   'E',
        ff_uids:      'F',
        ro_confirmed: 'G',
        started_at:   'H',
        completed_at: 'I',
        notes:        'N',
      }
    },
    freezedry: {
      dataStart: 38, dataEnd: 68,
      cols: {
        session_num:  'A',
        operator:     'B',
        equipment:    'C',
        wash_used:    'D',   // "S1: 4,000g; S2: 3,500g"
        input_wet:    'E',
        output_dry:   'F',
        pump_oil:     'G',
        started_at:   'I',
        completed_at: 'J',
        notes:        'N',
      }
    },
    sift: {
      dataStart: 71, dataEnd: 101,
      cols: {
        session_num:  'A',
        operator:     'B',
        fd_used:      'C',   // "S1: 1,200g; S2: 800g"
        dry_in:       'D',
        sift_out:     'E',
        storage:      'F',
        completed_at: 'I',
        notes:        'N',
      }
    },
  }
};

/**
 * Writes one closed session into its block of the Session Log tab.
 * Idempotent: if a row with the same Session # already exists in the block,
 * that row is overwritten instead of duplicated — so re-closing a session
 * to correct a weight UPDATES the sheet rather than adding a second row.
 */
function serverAppendWashSessionLog(sheetUrl, block, row) {
  if (!sheetUrl) return { success: false, error: 'sheetUrl missing' };
  const cfg = WASH_SESSION_LOG.BLOCKS[block];
  if (!cfg) return { success: false, error: 'unknown block: ' + block };

  try {
    const ss = SpreadsheetApp.openByUrl(sheetUrl);
    const sheet = ss.getSheetByName(WASH_SESSION_LOG.TAB);
    if (!sheet) return { success: false, error: 'tab not found: ' + WASH_SESSION_LOG.TAB };

    // Find target row: an existing row with this session # (update),
    // otherwise the first empty row in the block (append).
    const numRows = cfg.dataEnd - cfg.dataStart + 1;
    const colA = sheet.getRange('A' + cfg.dataStart + ':A' + cfg.dataEnd).getValues();
    let targetRow = null;
    let firstEmpty = null;
    for (let i = 0; i < numRows; i++) {
      const v = String(colA[i][0] === null ? '' : colA[i][0]).trim();
      if (v !== '' && v === String(row.session_num)) {
        targetRow = cfg.dataStart + i;
        break;
      }
      if (v === '' && firstEmpty === null) firstEmpty = cfg.dataStart + i;
    }
    if (targetRow === null) targetRow = firstEmpty;
    if (targetRow === null) {
      return { success: false, error: block + ' block full (rows ' + cfg.dataStart + '-' + cfg.dataEnd + ')' };
    }

    for (const key in cfg.cols) {
      if (row[key] !== undefined) {
        sheet.getRange(cfg.cols[key] + targetRow).setValue(row[key]);
      }
    }
    Logger.log('Session log ' + block + ' → row ' + targetRow + ' (session #' + row.session_num + ')');
    return { success: true, row: targetRow };
  } catch (e) {
    Logger.log('serverAppendWashSessionLog error: ' + e.message);
    return { success: false, error: e.message };
  }
}
