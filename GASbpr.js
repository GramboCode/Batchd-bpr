// ── BPR.gs ────────────────────────────────────────────────────────────

var BPR_APP_URL = 'https://batchd-bpr.netlify.app';

function serverGetBPRStatus(uid) {
  try {
    var ss    = SpreadsheetApp.openById(CONFIG.TRACKER_SS_ID);
    var sheet = ss.getSheetByName(CONFIG.TRACKER_TAB);
    var lastRow = sheet.getLastRow();

    for (var r = CONFIG.DATA_START_ROW; r <= lastRow; r++) {
      var rowUID = String(sheet.getRange(r, CONFIG.COL.METRC_UID).getValue()).trim();
      if (rowUID !== uid) continue;
      var bprStatus = String(sheet.getRange(r, 36).getValue() || '').trim();
      return { success: true, bprStatus: bprStatus || 'not_started' };
    }
    return { success: false, error: 'UID not found' };
  } catch(e) {
    return { success: false, error: e.message };
  }
}

function serverUpdateBPRStatus(uid, bprStatus, pdfUrl) {
  try {
    var ss    = SpreadsheetApp.openById(CONFIG.TRACKER_SS_ID);
    var sheet = ss.getSheetByName(CONFIG.TRACKER_TAB);
    var lastRow = sheet.getLastRow();

    for (var r = CONFIG.DATA_START_ROW; r <= lastRow; r++) {
      var rowUID = String(sheet.getRange(r, CONFIG.COL.METRC_UID).getValue()).trim();
      if (rowUID !== uid) continue;
      sheet.getRange(r, 36).setValue(bprStatus);
      if (pdfUrl) sheet.getRange(r, 37).setValue(pdfUrl);
      sheet.getRange(r, CONFIG.COL.LAST_UPDATED).setValue(new Date());
      return { success: true };
    }
    return { success: false, error: 'UID not found' };
  } catch(e) {
    return { success: false, error: e.message };
  }
}


/**
 * Generates a standard BPR cell map (BPR-*-001 v2.0 template family).
 * Only ingCount and stepCount vary by product — everything else is
 * fixed by the standardized template layout (confirmed identical
 * across Gummies and Live Rosin Press).
 *
 * ingCount:  number of non-cannabis ingredient rows actually used (max 15, items #2–16)
 * stepCount: number of real production steps actually used (max 20)
 * stepRowOffset: (optional) shifts ONLY the Section 6 step rows down by N rows.
 *   Standard tabs use 0. Templates that grew the equipment/sanitation sections
 *   (LiquiDabs/Nano: +3 equipment, +1 sanitation = +4) push Section 6 down, so
 *   STEP{n} → row 70+n+offset. Only STEP cells are ever written by the phase
 *   write-back, so the other sections don't need shifting here.
 */
function buildStandardBPRCellMap(ingCount, stepCount, stepRowOffset) {
  const map = {};
  stepRowOffset = stepRowOffset || 0;

  // Cannabis Source Material — always 7 rows, 16–22
  for (let i = 1; i <= 7; i++) {
    const row = 15 + i;
    map['CANN' + i + '_LOTCOA']     = 'C' + row;
    map['CANN' + i + '_UID']        = 'D' + row;
    map['CANN' + i + '_TARGETQTY']  = 'E' + row;   // Section 2 Target Qty (was unmapped)
    map['CANN' + i + '_ACTUALQTY']  = 'F' + row;
    map['CANN' + i + '_WEIGHEDBY']  = 'I' + row;
    map['CANN' + i + '_VERIFIEDBY'] = 'J' + row;
    map['CANN' + i + '_TIME']       = 'K' + row;
  }
  map['CANN_SUPERVISOR']        = 'A23';
  map['CANN_VERIFIED_DATETIME'] = 'H23';

  // Non-Cannabis Ingredients — item #2 onward, rows 25+
  for (let i = 0; i < ingCount; i++) {
    map['ING' + (i + 2) + '_ACTUALQTY'] = 'F' + (25 + i);
  }

  // Yield & Label Count — always 3 rows, 42–44
  const yieldRows = [42, 43, 44];
  yieldRows.forEach((row, i) => {
    const n = i + 1;
    map['YIELD' + n + '_EXPECTED']  = 'C' + row;   // Section 3 Expected/Target (was unmapped)
    map['YIELD' + n + '_ACTUAL']    = 'D' + row;
    map['YIELD' + n + '_INITIALS']  = 'J' + row;
    map['YIELD' + n + '_TIME']      = 'K' + row;
  });

  // Equipment Check-In/Sign — always 9 rows, 48–56
  for (let i = 1; i <= 9; i++) {
    const row = 47 + i;
    map['EQUIP' + i + '_CHECKEDBY'] = 'I' + row;
    map['EQUIP' + i + '_TIME']      = 'J' + row;
  }

  // Sanitation Log — always 9 usable rows, 59–67 (row 68 reserve)
  for (let i = 1; i <= 9; i++) {
    const row = 58 + i;
    map['SAN' + i + '_DATE']         = 'C' + row;
    map['SAN' + i + '_CLEANSTART']   = 'D' + row;
    map['SAN' + i + '_CLEANEND']     = 'E' + row;
    map['SAN' + i + '_PPM']          = 'G' + row;
    map['SAN' + i + '_STRIPSUSED']   = 'I' + row;
    map['SAN' + i + '_PASS']         = 'J' + row;
    map['SAN' + i + '_CLEANEDBY']    = 'K' + row;
    map['SAN' + i + '_DRYBEFOREUSE'] = 'L' + row;
  }

  // Production Steps & CCP — variable count, starting row 71 (+ offset)
  for (let i = 1; i <= stepCount; i++) {
    const row = 70 + i + stepRowOffset;
    map['STEP' + i + '_DATE']     = 'D' + row;
    map['STEP' + i + '_START']    = 'E' + row;
    map['STEP' + i + '_END']      = 'F' + row;
    map['STEP' + i + '_OP1']      = 'G' + row;
    map['STEP' + i + '_OP2']      = 'H' + row;
    map['STEP' + i + '_VERIFIED'] = 'I' + row;
    map['STEP' + i + '_VALUE']    = 'J' + row;
    map['STEP' + i + '_PASSFAIL'] = 'L' + row;
  }

  // QC Review & Batch Release — always 14 rows, 99–112
  for (let i = 1; i <= 14; i++) {
    const row = 98 + i;
    map['QC' + i + '_RESULT']   = 'H' + row;   // Section 8 Result (was unmapped)
    map['QC' + i + '_REVIEWER'] = 'I' + row;
    map['QC' + i + '_DATETIME'] = 'J' + row;
    map['QC' + i + '_PASSFAIL'] = 'K' + row;
    map['QC' + i + '_NOTES']    = 'L' + row;
  }
  map['DISPOSITION']            = 'A113';
  map['QC_SIGNATURE']           = 'E114';
  map['SUPERVISOR_SIGNATURE']   = 'I114';

  return map;
}

// Live Rosin Press: 5 real ingredients (CR Jars, Caps, Strain stickers, Wrap stickers, boxes), 11 real steps
const GUMMIES_CELL_MAP    = buildStandardBPRCellMap(11, 18); // 11 non-cannabis ingredients, 17 real steps
const LIVE_ROSIN_CELL_MAP = buildStandardBPRCellMap(5, 11);  // 5 non-cannabis ingredients, 11 real steps

// Universal map — every product BPR tab shares the standardized layout
// (gummies was the template all others were standardized against), so ONE map
// built at the maximum counts (15 ingredients #2–16, 20 production steps) is a
// superset that fits every product. serverWriteBPRFieldsByCellMap only writes
// the fields actually sent and skips the rest, so unused rows are harmless.
// New products get pointed at this instead of a bespoke buildStandardBPRCellMap.
const UNIVERSAL_BPR_CELL_MAP = buildStandardBPRCellMap(15, 20);

// Ultrasonic nanoemulsion products run longer Section 6 lists than the 20-step
// standard AND grew the sections above it — equipment +3 rows, sanitation +1 —
// so Section 6 sits +4 rows lower. STEP{n} → row 74+n (70 + n + 4 offset).
const NANO_STEP_OFFSET = 4;
const LIQUIDABS_CELL_MAP = buildStandardBPRCellMap(15, 26, NANO_STEP_OFFSET);    // BPR-LQD, 26 steps
const NANO_ISOLATE_CELL_MAP = buildStandardBPRCellMap(15, 28, NANO_STEP_OFFSET); // BPR-DNANO, 28 steps

const BPR_CELL_MAPS = {
  punch_gummies:   GUMMIES_CELL_MAP,
  punch_live_rosin: LIVE_ROSIN_CELL_MAP,
  tempo_live_rosin: LIVE_ROSIN_CELL_MAP, // shares the same BPR tab per BATCH_RECORD_TAB_MAP

  // Standardized-layout products → universal superset map. The per-product
  // difference lives entirely in the Python PHASE_TO_STEPS mapping (which sheet
  // rows each phase timestamps), NOT in the cell positions.
  punch_bho_badder:  UNIVERSAL_BPR_CELL_MAP,
  punch_bho_shatter: UNIVERSAL_BPR_CELL_MAP,
  punch_rocket:      UNIVERSAL_BPR_CELL_MAP,
  tempo_lr_diamonds: UNIVERSAL_BPR_CELL_MAP,
  punch_rosin_aio:   UNIVERSAL_BPR_CELL_MAP,
  punch_stinger:     UNIVERSAL_BPR_CELL_MAP,
  punch_cookie:      UNIVERSAL_BPR_CELL_MAP,
  punch_malt_balls:  UNIVERSAL_BPR_CELL_MAP,
  punch_asteroids:   UNIVERSAL_BPR_CELL_MAP,
  punch_vapes:       UNIVERSAL_BPR_CELL_MAP,  // Distillate Vape / TEMPO AIO
  tempo_lr_aio:      UNIVERSAL_BPR_CELL_MAP,  // Tempo Live Resin Vape
  // Dynamic-tab families: templateKey → __*_DYNAMIC__ placeholder; the tab is
  // resolved by the single-tab fallback in serverWriteBPRFieldsByCellMap.
  punch_punchbar:    UNIVERSAL_BPR_CELL_MAP,  // all 3 chocolate variants
  dr_norms:          UNIVERSAL_BPR_CELL_MAP,  // all 5 Dr. Norm's families
  liquidabs:         LIQUIDABS_CELL_MAP,      // 26-step ultrasonic nanoemulsion
  nano_isolate:      NANO_ISOLATE_CELL_MAP,   // 28-step component nanoemulsion
};

// ── BPR WRITE-BACK SYSTEM ─────────────────────────────────────
// Receives field data from digital BPR app and writes to named
// ranges in the batch's Google Sheet BPR file.

// ── FIND BPR FILE FOR UID ─────────────────────────────────────
function getBPRFileForUID(uid) {
  try {
    const coaFolder = getCOAArchiveFolder();
    if (!coaFolder) {
      Logger.log('getBPRFileForUID: COA Archive folder not found');
      return null;
    }

    const uidFolder = coaFolder.getFoldersByName(uid);
    if (!uidFolder.hasNext()) {
      Logger.log('getBPRFileForUID: UID folder not found for ' + uid);
      return null;
    }

    const folder = uidFolder.next();
    const files  = folder.getFilesByType(MimeType.GOOGLE_SHEETS);

    while (files.hasNext()) {
      const file = files.next();
      // BPR file name contains the batch ID and item name — skip Labels subfolder files
      if (!file.getName().includes('Labels')) {
        return file;
      }
    }

    Logger.log('getBPRFileForUID: no BPR spreadsheet found in UID folder ' + uid);
    return null;

  } catch(e) {
    Logger.log('getBPRFileForUID error: ' + e.message);
    return null;
  }
}

// ── WRITE BPR FIELDS VIA NAMED RANGES ────────────────────────
// Called from digital app on each phase completion.
// fields = { namedRangeName: value, ... }
function serverWriteBPRFields(uid, fields) {
  try {
    const file = getBPRFileForUID(uid);
    if (!file) {
      return { success: false, error: 'No BPR file found for UID: ' + uid };
    }

    const ss = SpreadsheetApp.openById(file.getId());

    // Get all named ranges once — outside loop
    const namedRangeMap = {};
    ss.getNamedRanges().forEach(nr => {
      namedRangeMap[nr.getName()] = nr;
    });

    const results  = {};
    const notFound = [];

    for (const [fieldName, value] of Object.entries(fields)) {
      try {
        if (namedRangeMap[fieldName]) {
          namedRangeMap[fieldName].getRange().setValue(value);
          results[fieldName] = 'written';
        } else {
          notFound.push(fieldName);
          results[fieldName] = 'named range not found';
        }
      } catch(e) {
        results[fieldName] = 'error: ' + e.message;
        Logger.log('writeBPRFields error on ' + fieldName + ': ' + e.message);
      }
    }

    SpreadsheetApp.flush();

    if (notFound.length > 0) {
      Logger.log('writeBPRFields: named ranges not found — ' + notFound.join(', '));
    }

    Logger.log('writeBPRFields: wrote ' + Object.keys(fields).length + ' fields for UID ' + uid);
    return { success: true, results, notFound };

  } catch(e) {
    Logger.log('serverWriteBPRFields error: ' + e.message);
    return { success: false, error: e.message };
  }
}

function serverWriteBPRFieldsByCellMap(uid, templateKey, fields) {
  const file = getBPRFileForUID(uid);
  if (!file) {
    return { success: false, error: 'No BPR file found for UID: ' + uid };
  }

  const cellMap = BPR_CELL_MAPS[templateKey];
  if (!cellMap) {
    return { success: false, error: 'No cell map defined for templateKey: ' + templateKey };
  }

  try {
    const ss = SpreadsheetApp.openById(file.getId());
    const tabName = BATCH_RECORD_TAB_MAP[templateKey];
    let sheet = tabName ? ss.getSheetByName(tabName) : null;

    // Dynamic-tab products (chocolate → __CHOC_DYNAMIC__, Dr. Norm's →
    // __NORMS_DYNAMIC__) resolve their real tab per-flavor at CREATION time, so
    // BATCH_RECORD_TAB_MAP[templateKey] here is a placeholder that getSheetByName
    // can't find. Every finished-goods BPR file has exactly ONE product tab
    // (createBatchRecord copies one template tab and deletes Sheet1), so fall
    // back to that single tab. Also covers a tab that was renamed post-creation.
    if (!sheet) {
      const sheets = ss.getSheets();
      sheet = sheets.length ? sheets[0] : null;
    }
    if (!sheet) {
      return { success: false, error: 'No writable tab in BPR file for UID: ' + uid };
    }

    let written = 0;
    const missing = [];

    for (const name in fields) {
      const a1 = cellMap[name];
      if (a1) {
        sheet.getRange(a1).setValue(fields[name]);
        written++;
      } else {
        missing.push(name);
      }
    }

    if (missing.length) {
      Logger.log('writeBPRFieldsByCellMap — fields not in map for "' + templateKey + '": ' + missing.join(', '));
    }

    SpreadsheetApp.flush();
    Logger.log('writeBPRFieldsByCellMap: wrote ' + written + ' fields for UID ' + uid + ' [' + templateKey + ']');
    return { success: true, written: written, missing: missing };

  } catch (e) {
    Logger.log('serverWriteBPRFieldsByCellMap error: ' + e.message);
    return { success: false, error: e.message };
  }
}

// ── WRITE SANITATION ROW (Section 7) ─────────────────────────
// Matches equipment by name in col B, writes to that row.
// sanitationEntries = [
//   { equipment: 'Washing Machine #1', date: '06/24/2026',
//     start: '08:00', end: '08:15', ppm: '200', pass: 'Yes',
//     cleanedBy: 'J. Martinez', dryBeforeUse: 'Yes' },
//   ...
// ]
function serverWriteSanitationLog(uid, sanitationEntries) {
  try {
    const file = getBPRFileForUID(uid);
    if (!file) {
      return { success: false, error: 'No BPR file found for UID: ' + uid };
    }

    const ss = SpreadsheetApp.openById(file.getId());

    // Get all named ranges once
    const namedRangeMap = {};
    ss.getNamedRanges().forEach(nr => {
      namedRangeMap[nr.getName()] = nr;
    });

    const results  = [];
    const notFound = [];

    // sanitationEntries = [
    //   { row: 1, date: '06/24/2026', start: '08:00', end: '08:15',
    //     ppm: '200', pass: 'Yes', cleanedBy: 'J. Martinez', dryBefore: 'Yes' },
    //   ...
    // ]
    for (const entry of sanitationEntries) {
      const r      = entry.row; // 1–10 matching equipment row number
      const prefix = 'ROSIN_S7_ROW' + r;

      const writes = {
        [prefix + '_DATE']:       entry.date       || '',
        [prefix + '_START']:      entry.start      || '',
        [prefix + '_END']:        entry.end        || '',
        [prefix + '_PPM']:        entry.ppm        || '',
        [prefix + '_PASS']:       entry.pass       || '',
        [prefix + '_CLEANED_BY']: entry.cleanedBy  || '',
        [prefix + '_DRY_BEFORE']: entry.dryBefore  || '',
      };

      for (const [rangeName, value] of Object.entries(writes)) {
        if (namedRangeMap[rangeName]) {
          namedRangeMap[rangeName].getRange().setValue(value);
          results.push({ range: rangeName, status: 'written' });
        } else {
          notFound.push(rangeName);
          results.push({ range: rangeName, status: 'not found' });
        }
      }
    }

    SpreadsheetApp.flush();

    if (notFound.length > 0) {
      Logger.log('writeSanitationLog: ranges not found — ' + notFound.join(', '));
    }

    Logger.log('writeSanitationLog: processed ' + sanitationEntries.length + 
               ' entries for UID ' + uid);
    return { success: true, results, notFound };

  } catch(e) {
    Logger.log('serverWriteSanitationLog error: ' + e.message);
    return { success: false, error: e.message };
  }
}

// ── FORMULA INJECTION ON BATCH CREATION ──────────────────────
// Called inside createBatchRecord after tab is copied.
// Injects Section 5 deviation formulas that don't survive copyTo.
function injectBPRFormulas(sheet, templateKey) {
  // Retired as of BPR-*-001 v2.0 standardization — Section 3 deviation formulas
  // are baked directly into the master template (confirmed on both Gummies and
  // Live Rosin Press tabs) and survive sheet.copyTo() automatically.
  // Retained as a no-op stub in case a future non-standardized template needs
  // code-side formula injection again.
  return;
}



