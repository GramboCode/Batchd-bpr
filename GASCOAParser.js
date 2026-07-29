// ============================================================
// COA PARSER — Punch Tools
// Reads PDFs from "COA Archive" Drive folder
// Writes to COA_LOG tab, UID_TRACKER pulls via QUERY formula
// ============================================================

// ── CONFIG ──────────────────────────────────────────────────
const COA_CONFIG = {
  UID_TRACKER_ID: '1yNldRwg8E0paStewgW82ZGouIRqE9S9XKYdfEPmOEqU',
  LOG_TAB:        'COA_LOG',
  TRACKER_TAB:    'UID',
  COA_FOLDER:     'COA Archive',
  LOG_COLS: {
    PARSE_DATE:      1,
    TEST_DATE:       2,
    LAB:             3,
    METRC_UID:       4,
    BATCH_ID:        5,
    LAB_SAMPLE_ID:   6,
    PRODUCT_NAME:    7,
    PKG_SIZE_G:      8,
    THC_PCT:         9,
    THC_MG_G:        10,
    THC_MG_PKG:      11,
    CBD_PCT:         12,
    CBD_MG_G:        13,
    CBD_MG_PKG:      14,
    TOTAL_CB_PCT:    15,
    TOTAL_CB_MG_G:   16,
    TOTAL_CB_MG_PKG: 17,
    COA_LINK:        18,
    MATCH_STATUS:    19,
    TEST_TYPE:       20,
    RESULT:          21,
  },
};

// ── MENU ────────────────────────────────────────────────────
// Add to your existing onOpen or call separately
function addCOAMenuItems(menu) {
  menu.addItem('Scan COA Archive Now', 'scanCOAArchive')
      .addItem('Setup COA_LOG Tab', 'setupCOALogTab');
}

// ── TRIGGER SETUP ───────────────────────────────────────────
function createCOATrigger() {
  // Remove existing COA triggers first
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === 'scanCOAArchive') {
      ScriptApp.deleteTrigger(t);
    }
  });
  // Run every 2 hours
  ScriptApp.newTrigger('scanCOAArchive')
    .timeBased()
    .everyHours(2)
    .create();
  SpreadsheetApp.getUi().alert('COA auto-scan trigger set (every 2 hours).');
}

// ── MAIN SCANNER ────────────────────────────────────────────
function scanCOAArchive() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) {
    Logger.log('COA scan: could not acquire lock, skipping.');
    return;
  }

  try {
    const ss       = SpreadsheetApp.openById(CONFIG.TRACKER_SS_ID);
    const logSheet = getOrCreateLogSheet(ss);
    const folder   = getCOAFolder();

    if (!folder) {
      Logger.log('COA Archive folder not found.');
      return;
    }

    const processedLinks = getProcessedLinks(logSheet);
    const trackerIndex   = buildTrackerIndex(ss);

    // Only scan PDFs in root of COA Archive — not subfolders
    const files  = folder.getFilesByType(MimeType.PDF);
    let newCount = 0;

    while (files.hasNext()) {
      const file    = files.next();
      const fileUrl = file.getUrl();

      // Skip sticker/label files — leave them in root
      const fileName = file.getName();
      if (/sticker|label|reel|xtra|extra/i.test(fileName) &&
          !/encore|infinite|icc-|tagleaf|lims/i.test(fileName)) {
        Logger.log('Skipping likely sticker/label file: ' + fileName);
        continue;
      }

      if (processedLinks.has(fileUrl)) {
        Logger.log('Already processed: ' + fileName);
        continue;
      }

      try {
        const parsed = parseCOAPdf(file);
        if (!parsed) {
          Logger.log('Could not parse: ' + fileName);
          continue;
        }

        const matchResult = matchToTracker(parsed, trackerIndex);

        // ── Move file to UID folder if matched ──────────────
        let finalFileUrl = fileUrl;
        if (matchResult.matched) {
          try {
            const metrcUid = parsed.metrcUid ||
              _getUIDFromRow(ss, matchResult.row);

            if (metrcUid) {
              const uidFolder = getOrCreateUIDFolder(folder, metrcUid);
              folder.removeFile(file);
              uidFolder.addFile(file);
              finalFileUrl = file.getUrl(); // URL stays the same after move
              Logger.log('Moved ' + fileName + ' → ' + metrcUid + '/');
            }
          } catch(moveErr) {
            Logger.log('Could not move file (non-fatal): ' + moveErr.message);
            // Continue with original URL if move fails
          }
        }

        appendToLog(logSheet, parsed, finalFileUrl, matchResult);
        newCount++;

        if (matchResult.matched) {
          updateTrackerRow(ss, matchResult.row, parsed, finalFileUrl);
        }

        Utilities.sleep(500);

      } catch (e) {
        Logger.log('Error parsing ' + fileName + ': ' + e.message);
      }
    }

    Logger.log('COA scan complete. New records: ' + newCount);

  } finally {
    lock.releaseLock();
  }
}

// ── UID FOLDER HELPERS ───────────────────────────────────────

function getOrCreateUIDFolder(coaArchiveFolder, metrcUid) {
  // Look for existing UID subfolder
  const existing = coaArchiveFolder.getFoldersByName(metrcUid);
  if (existing.hasNext()) return existing.next();

  // Create new UID folder + Labels subfolder
  const uidFolder    = coaArchiveFolder.createFolder(metrcUid);
  uidFolder.createFolder('Labels');
  Logger.log('Created UID folder: ' + metrcUid);
  return uidFolder;
}

function _getUIDFromRow(ss, rowNum) {
  // Fallback — read METRC UID directly from tracker row
  const sheet = ss.getSheetByName(CONFIG.TRACKER_TAB);
  const uid   = sheet.getRange(rowNum, CONFIG.COL.METRC_UID).getValue();
  return uid ? String(uid).trim() : null;
}

// ── PDF PARSER ──────────────────────────────────────────────
function parseCOAPdf(file) {
  // Convert PDF to text via Google Drive export
  const text = extractPdfText(file);
  if (!text || text.length < 100) return null;

  // Detect lab
  const isEncore     = /encore\s*labs/i.test(text);
  const isInfiniteCAL = /infinite\s*chemical/i.test(text);
  const isLandau = /landau\s+laboratories/i.test(text);

  if (isEncore)      return parseEncoreCOA(text, file.getName());
  if (isInfiniteCAL) return parseInfiniteCALCOA(text, file.getName());
  if (isLandau)      return parseLandauCOA(text, file.getName());

  // Unknown lab — try generic extraction
  return parseGenericCOA(text, file.getName());
}


function extractPdfText(file) {
  try {
    const token    = ScriptApp.getOAuthToken();
    const boundary = 'coa_boundary_xyz';
    const meta     = JSON.stringify({
      name:     '__temp_coa_' + file.getId(),
      mimeType: 'application/vnd.google-apps.document'
    });

    const bodyStart  = Utilities.newBlob('--' + boundary + '\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n' + meta + '\r\n--' + boundary + '\r\nContent-Type: application/pdf\r\n\r\n').getBytes();
    const pdfBytes   = file.getBlob().getBytes();
    const bodyEnd    = Utilities.newBlob('\r\n--' + boundary + '--').getBytes();
    const fullBody   = bodyStart.concat(pdfBytes).concat(bodyEnd);

    const uploadResp = UrlFetchApp.fetch(
      'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart',
      {
        method:  'POST',
        headers: {
          Authorization:  'Bearer ' + token,
          'Content-Type': 'multipart/related; boundary=' + boundary,
        },
        payload:           Utilities.newBlob(fullBody).getBytes(),
        muteHttpExceptions: true,
      }
    );

    if (uploadResp.getResponseCode() !== 200) {
      Logger.log('PDF upload failed: ' + uploadResp.getContentText());
      return null;
    }

    const tempId  = JSON.parse(uploadResp.getContentText()).id;
    const docText = DocumentApp.openById(tempId).getBody().getText();
    DriveApp.getFileById(tempId).setTrashed(true);

    return docText;

  } catch (e) {
    Logger.log('Text extraction error: ' + e.message);
    return null;
  }
}

// ── ENCORE LABS PARSER ──────────────────────────────────────
function parseEncoreCOA(text, filename) {
  const result = {
    lab:         'Encore Labs',
    filename:    filename,
    metrcUid:    null,
    batchId:     null,
    labSampleId: null,
    productName: null,
    testDate:    null,
    pkgSizeG:    1.0, // default
    testType:     /Regulatory\s+Compliance\s+Testing/i.test(text) ? 'COMPLIANCE' : 'RND',
    overallResult: /^Batch\s+Fail/im.test(text) ? 'FAIL' : 'PASS',
    thcPct:      null,
    thcMgG:      null,
    thcMgPkg:    null,
    cbdPct:      null,
    cbdMgG:      null,
    cbdMgPkg:    null,
    totalCbPct:  null,
    totalCbMgG:  null,
    totalCbMgPkg:null,
  };

  // Sample ID — e.g. "Sample ID: 2603ENC4366_3826"
  const sampleIdMatch = text.match(/Sample\s+ID[:\s]+([A-Z0-9_]+)/i);
  if (sampleIdMatch) result.labSampleId = sampleIdMatch[1].trim();

   // METRC UID — try multiple formats Encore uses
  const metrcPatterns = [
    /METRC\s+Batch[:\s]+(1A[A-Z0-9]{22})/i,
    /METRC\s+Sample[:\s]+(1A[A-Z0-9]{22})/i,
    /METRC\s+Source\s+UID[:\s]+(1A[A-Z0-9]{22})/i,
    /Source\s+UID[:\s]+(1A[A-Z0-9]{22})/i,
    /(1A[A-Z0-9]{22})/,  // raw UID anywhere in text
  ];
  for (const pat of metrcPatterns) {
    const m = text.match(pat);
    if (m) { result.metrcUid = m[1].trim(); break; }
  }

  // Batch ID — Encore uses "Batch ID:" or "External Batch ID:"
  const batchPatterns = [
    /External\s+Batch\s+ID[:\s]+([A-Z0-9]+)/i,
    /Batch\s+ID[:\s]+([A-Z0-9]+)/i,
    /Batch\s*#[:\s]+([A-Z0-9]+(?:[A-Z0-9]*\d{3}))/i, // must end in 3 digits
  ];
  for (const pat of batchPatterns) {
    const m = text.match(pat);
    if (m && m[1] !== 'Pass' && m[1] !== 'Fail' && m[1].length > 3) {
      result.batchId = m[1].trim();
      break;
    }
  }

  // Product name — first line after "Certificate of Analysis"
  const nameMatch = text.match(/Certificate of Analysis[^\n]*\n([^\n]+)/i);
  if (nameMatch) result.productName = nameMatch[1].trim();

  // Test date — "Cannabinoids  MM/DD/YYYY"
  const dateMatch = text.match(/Cannabinoids\s+(\d{2}\/\d{2}\/\d{4})/i);
  if (dateMatch) result.testDate = dateMatch[1];

  // Package size — look for "Sample Size: N units" or product name "(Xg)"
  const pkgSizeMatch = text.match(/\((\d+(?:\.\d+)?)\s*g\)/i);
  if (pkgSizeMatch) result.pkgSizeG = parseFloat(pkgSizeMatch[1]);

  // ── Potency values ──
  // Encore format: "Total THC  77.008  770.09"  (% then mg/g on same line)
  const thcLine = text.match(/Total\s+THC[\s\t]+([\d.]+)[\s\t]+([\d.]+)/i);
  if (thcLine) {
    result.thcPct  = parseFloat(thcLine[1]);
    result.thcMgG  = parseFloat(thcLine[2]);
    result.thcMgPkg = roundTo(result.thcMgG * result.pkgSizeG, 2);
  }

  const cbdLine = text.match(/Total\s+CBD[\s\t]+([\d.]+)[\s\t]+([\d.]+)/i);
  if (cbdLine) {
    result.cbdPct  = parseFloat(cbdLine[1]);
    result.cbdMgG  = parseFloat(cbdLine[2]);
    result.cbdMgPkg = roundTo(result.cbdMgG * result.pkgSizeG, 2);
  }

  const totalLine = text.match(/Total\s+Cannabinoids[\s\t]+([\d.]+)[\s\t]+([\d.]+)/i);
  if (totalLine) {
    result.totalCbPct  = parseFloat(totalLine[1]);
    result.totalCbMgG  = parseFloat(totalLine[2]);
    result.totalCbMgPkg = roundTo(result.totalCbMgG * result.pkgSizeG, 2);
  }

  return result;
}

// ── INFINITE CAL PARSER ─────────────────────────────────────
function parseInfiniteCALCOA(text, filename) {
  const result = {
    lab:         'Infinite CAL',
    filename:    filename,
    metrcUid:    null,
    batchId:     null,
    labSampleId: null,
    productName: null,
    testDate:    null,
    pkgSizeG:    1.0,
    testType: (function() {
      if (/REGULATORY\s+COMPLIANCE\s+TESTING/i.test(text)) return 'COMPLIANCE';
      return 'RND'; // potency-only AND big-3 both treated as RND
    })(),
    overallResult: /Batch\s+Result[:\s]+Fail/i.test(text) ? 'FAIL' : 'PASS',
    thcPct:      null,
    thcMgG:      null,
    thcMgPkg:    null,
    cbdPct:      null,
    cbdMgG:      null,
    cbdMgPkg:    null,
    totalCbPct:  null,
    totalCbMgG:  null,
    totalCbMgPkg:null,
  };

  // Batch No. — e.g. "Batch No.: PEBADMNTMZ001"
  const batchMatch = text.match(/Batch\s+No\.[:\s]+([A-Z0-9]+)/i);
  if (batchMatch) result.batchId = batchMatch[1].trim();

  // Sample ID — e.g. "Sample ID: ICC-260330-37-004"
  const sampleMatch = text.match(/Sample\s+ID[:\s]+([A-Z0-9\-]+)/i);
  if (sampleMatch) result.labSampleId = sampleMatch[1].trim();

  // Src Pkg (METRC UID) — e.g. "Src Pkg: 1A4060300005D6A000006354"
  const srcPkgMatch = text.match(/Src\s+Pkg[:\s]+([A-Z0-9]+)/i);
  if (srcPkgMatch) result.metrcUid = srcPkgMatch[1].trim();

  // Product name — after "Sample:"
  const nameMatch = text.match(/Sample[:\s]+([^\n•]+?)(?:\s*•|\n)/i);
  if (nameMatch) result.productName = nameMatch[1].trim();

  // Test date — "Produced: Apr 02, 2026"
  const dateMatch = text.match(/Produced[:\s]+([A-Za-z]+\s+\d{2},\s+\d{4})/i);
  if (dateMatch) result.testDate = dateMatch[1];

  // Package size — "Package Size: 1 g"
  const pkgMatch = text.match(/Package\s+Size[:\s]+([\d.]+)\s*g/i);
  if (pkgMatch) result.pkgSizeG = parseFloat(pkgMatch[1]);

  // ── Potency values ──
  // Infinite CAL format: "** \nTotal THC 67.1 671 N/A"
  // Columns: Amt(%) then Amt(mg/g) — no mg/pkg on RND format
  // Compliance format has mg/pkg as first column, detect which by checking header

  const hasLimit = /Limit \(mg\)/.test(text); // compliance format has Limit column

  if (hasLimit) {
    // Compliance: Limit(mg) | Amt(mg/pkg) | Amt(%) | Amt(mg/g)
    const thcLine = text.match(/Total\s+THC\*{0,2}\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)/i);
    if (thcLine) { result.thcMgPkg = parseFloat(thcLine[1]); result.thcPct = parseFloat(thcLine[2]); result.thcMgG = parseFloat(thcLine[3]); }
    const cbdLine = text.match(/Total\s+CBD\*{0,2}\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)/i);
    if (cbdLine) { result.cbdMgPkg = parseFloat(cbdLine[1]); result.cbdPct = parseFloat(cbdLine[2]); result.cbdMgG = parseFloat(cbdLine[3]); }
    const totLine = text.match(/Total\s+Cannabinoids\*{0,2}\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)/i);
    if (totLine) { result.totalCbMgPkg = parseFloat(totLine[1]); result.totalCbPct = parseFloat(totLine[2]); result.totalCbMgG = parseFloat(totLine[3]); }
  } else {
    // RND / non-compliance: Amt(%) then Amt(mg/g), calculate mg/pkg
    const thcLine = text.match(/Total\s+THC\s+([\d.]+)\s+([\d.]+)/i);
    if (thcLine) { result.thcPct = parseFloat(thcLine[1]); result.thcMgG = parseFloat(thcLine[2]); result.thcMgPkg = roundTo(result.thcMgG * result.pkgSizeG, 2); }
    const cbdLine = text.match(/Total\s+CBD\s+([\d.]+)\s+([\d.]+)/i);
    if (cbdLine) { result.cbdPct = parseFloat(cbdLine[1]); result.cbdMgG = parseFloat(cbdLine[2]); result.cbdMgPkg = roundTo(result.cbdMgG * result.pkgSizeG, 2); }
    const totLine = text.match(/Total\s+Cannabinoids\s+([\d.]+)\s+([\d.]+)/i);
    if (totLine) { result.totalCbPct = parseFloat(totLine[1]); result.totalCbMgG = parseFloat(totLine[2]); result.totalCbMgPkg = roundTo(result.totalCbMgG * result.pkgSizeG, 2); }
  }

  return result;
}

// ── LANDAU LABS PARSER ──────────────────────────────────────
function parseLandauCOA(text, filename) {
  const result = {
    lab:          'Landau',
    filename:     filename,
    metrcUid:     null,
    batchId:      null,
    labSampleId:  null,
    productName:  null,
    testDate:     null,
    pkgSizeG:     1.0,
    testType:     /Regulatory\s+Compliance\s+Testing/i.test(text) ? 'COMPLIANCE' : 'RND',
    overallResult: /^Batch\s+Fail/im.test(text) ? 'FAIL' : 'PASS',
    thcPct:       null,
    thcMgG:       null,
    thcMgPkg:     null,
    cbdPct:       null,
    cbdMgG:       null,
    cbdMgPkg:     null,
    totalCbPct:   null,
    totalCbMgG:   null,
    totalCbMgPkg: null,
  };

  // METRC UID — "METRC Sample: 1A4060300044C65000449613"
  const metrcMatch = text.match(/METRC\s+(?:Sample|Batch)[:\s]+(1A[A-Z0-9]{22})/i);
  if (metrcMatch) result.metrcUid = metrcMatch[1].trim();

  // Also try METRC Batch for the source UID
  if (!result.metrcUid) {
    const batchMetrcMatch = text.match(/METRC\s+Batch[:\s]+(1A[A-Z0-9]{22})/i);
    if (batchMetrcMatch) result.metrcUid = batchMetrcMatch[1].trim();
  }

  // Sample ID — "Sample ID: 2603LLI0418.1302"
  const sampleMatch = text.match(/Sample\s+ID[:\s]+([\w.]+)/i);
  if (sampleMatch) result.labSampleId = sampleMatch[1].trim();

  // Internal Batch# — "Batch#: BR-CHOC-054"
  const batchMatch = text.match(/Batch\s*#[:\s]+([\w-]+)/i);
  if (batchMatch && batchMatch[1] !== 'Pass' && batchMatch[1] !== 'Fail') {
    result.batchId = batchMatch[1].trim();
  }

  // Product name — first line of the document (before METRC Sample line)
  const nameMatch = text.match(/^([^\n]+)\nMETRC\s+Sample/im);
  if (nameMatch) result.productName = nameMatch[1].trim();

  // Test date — "Cannabinoids  03/11/2026"
  const dateMatch = text.match(/Cannabinoids\s+(\d{2}\/\d{2}\/\d{4})/i);
  if (dateMatch) result.testDate = dateMatch[1];

  // Package size — e.g. "(1g)" in product name or sample size
  const pkgMatch = text.match(/\((\d+(?:\.\d+)?)\s*g\)/i);
  if (pkgMatch) result.pkgSizeG = parseFloat(pkgMatch[1]);

  // Number of servings — "10 serving(s) per container"
  const servingsMatch = text.match(/(\d+)\s+serving[s]?\s+per\s+container/i);
  const servings = servingsMatch ? parseInt(servingsMatch[1]) : 1;

  // ── Potency values ──
  // Landau format: Total THC  10.432  1.304  0.130  104.320
  // Columns:       mg/serving  mg/g   %      mg/container
  const thcLine = text.match(/Total\s+THC\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)/i);
  if (thcLine) {
    result.thcMgPkg = parseFloat(thcLine[1]) * servings; // mg/serving × servings = mg/pkg
    result.thcMgG   = parseFloat(thcLine[2]);
    result.thcPct   = parseFloat(thcLine[3]);
  }

  const cbdLine = text.match(/Total\s+CBD\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)/i);
  if (cbdLine) {
    result.cbdMgPkg = parseFloat(cbdLine[1]) * servings;
    result.cbdMgG   = parseFloat(cbdLine[2]);
    result.cbdPct   = parseFloat(cbdLine[3]);
  }

  // Total Cannabinoids — Landau labels it "Total" at the bottom
  const totalLine = text.match(/^Total\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)/im);
  if (totalLine) {
    result.totalCbMgPkg = parseFloat(totalLine[1]) * servings;
    result.totalCbMgG   = parseFloat(totalLine[2]);
    result.totalCbPct   = parseFloat(totalLine[3]);
  }

  return result;
}

// ── GENERIC PARSER (fallback) ────────────────────────────────
function parseGenericCOA(text, filename) {
  
  const result = {
    lab:         'Unknown',
    filename:    filename,
    metrcUid:    null,
    batchId:     null,
    labSampleId: null,
    productName: null,
    testDate:    null,
    pkgSizeG:    1.0,
    testType:     'RND',
    overallResult: /^Batch\s+Fail/im.test(text) ? 'FAIL' : 'PASS',
    thcPct:      null,
    thcMgG:      null,
    thcMgPkg:    null,
    cbdPct:      null,
    cbdMgG:      null,
    cbdMgPkg:    null,
    totalCbPct:  null,
    totalCbMgG:  null,
    totalCbMgPkg:null,
  };

  const thcPctMatch = text.match(/Total\s+THC[^\d]+([\d.]+)\s*%/i);
  if (thcPctMatch) result.thcPct = parseFloat(thcPctMatch[1]);

  const cbdPctMatch = text.match(/Total\s+CBD[^\d]+([\d.]+)\s*%/i);
  if (cbdPctMatch) result.cbdPct = parseFloat(cbdPctMatch[1]);

  return result;
}

// ── TRACKER MATCHING ─────────────────────────────────────────
function buildTrackerIndex(ss) {
  const sheet   = ss.getSheetByName(COA_CONFIG.TRACKER_TAB);
  const lastRow = sheet.getLastRow();
  if (lastRow < CONFIG.DATA_START_ROW) return { byMetrc: {}, byBatch: {} };

  const data = sheet.getRange(
    CONFIG.DATA_START_ROW, 1,
    lastRow - CONFIG.DATA_START_ROW + 1,
    CONFIG.COL.BATCH_ID
  ).getValues();

  const index = { byMetrc: {}, byBatch: {} };

  data.forEach((row, i) => {
    const sheetRow = CONFIG.DATA_START_ROW + i;
    const metrcUid = String(row[CONFIG.COL.METRC_UID - 1] || '').trim();
    const batchId  = String(row[CONFIG.COL.BATCH_ID  - 1] || '').trim();

    if (metrcUid) index.byMetrc[metrcUid] = sheetRow;
    if (batchId)  index.byBatch[batchId]  = sheetRow;
  });

  return index;
}

function matchToTracker(parsed, index) {
  // Try METRC UID first
  if (parsed.metrcUid && index.byMetrc[parsed.metrcUid]) {
    return { matched: true, row: index.byMetrc[parsed.metrcUid], method: 'METRC_UID' };
  }
  // Fall back to Batch ID
  if (parsed.batchId && index.byBatch[parsed.batchId]) {
    return { matched: true, row: index.byBatch[parsed.batchId], method: 'BATCH_ID' };
  }
  return { matched: false, row: null, method: 'NONE' };
}

// ── SHEET WRITERS ────────────────────────────────────────────
function appendToLog(logSheet, parsed, fileUrl, matchResult) {
  const cols = COA_CONFIG.LOG_COLS;
  const row  = new Array(21).fill('');  // expanded to 21

  row[cols.PARSE_DATE       - 1] = new Date();
  row[cols.TEST_DATE        - 1] = parsed.testDate      || '';
  row[cols.LAB              - 1] = parsed.lab            || '';
  row[cols.METRC_UID        - 1] = parsed.metrcUid       || '';
  row[cols.BATCH_ID         - 1] = parsed.batchId        || '';
  row[cols.LAB_SAMPLE_ID    - 1] = parsed.labSampleId    || '';
  row[cols.PRODUCT_NAME     - 1] = parsed.productName    || '';
  row[cols.PKG_SIZE_G       - 1] = parsed.pkgSizeG       || 1;
  row[cols.THC_PCT          - 1] = parsed.thcPct         !== null ? parsed.thcPct         : '';
  row[cols.THC_MG_G         - 1] = parsed.thcMgG         !== null ? parsed.thcMgG         : '';
  row[cols.THC_MG_PKG       - 1] = parsed.thcMgPkg       !== null ? parsed.thcMgPkg       : '';
  row[cols.CBD_PCT          - 1] = parsed.cbdPct         !== null ? parsed.cbdPct         : '';
  row[cols.CBD_MG_G         - 1] = parsed.cbdMgG         !== null ? parsed.cbdMgG         : '';
  row[cols.CBD_MG_PKG       - 1] = parsed.cbdMgPkg       !== null ? parsed.cbdMgPkg       : '';
  row[cols.TOTAL_CB_PCT     - 1] = parsed.totalCbPct     !== null ? parsed.totalCbPct     : '';
  row[cols.TOTAL_CB_MG_G    - 1] = parsed.totalCbMgG     !== null ? parsed.totalCbMgG     : '';
  row[cols.TOTAL_CB_MG_PKG  - 1] = parsed.totalCbMgPkg   !== null ? parsed.totalCbMgPkg   : '';
  row[cols.COA_LINK         - 1] = fileUrl;
  row[cols.MATCH_STATUS     - 1] = matchResult.matched
    ? 'MATCHED (' + matchResult.method + ')'
    : 'UNMATCHED';
  row[cols.TEST_TYPE        - 1] = parsed.testType       || '';
  row[cols.RESULT           - 1] = parsed.overallResult  || '';

  logSheet.appendRow(row);
}

function updateTrackerRow(ss, rowNum, parsed, fileUrl) {
  const sheet = ss.getSheetByName(COA_CONFIG.TRACKER_TAB);
  const C     = CONFIG.COL; // use master column map

  const potencyRow = new Array(10).fill('');
  potencyRow[0]  = fileUrl;                                              // W COA_LINK
  potencyRow[1]  = parsed.thcPct        !== null ? parsed.thcPct        : '';
  potencyRow[2]  = parsed.thcMgG        !== null ? parsed.thcMgG        : '';
  potencyRow[3]  = parsed.thcMgPkg      !== null ? parsed.thcMgPkg      : '';
  potencyRow[4]  = parsed.cbdPct        !== null ? parsed.cbdPct        : '';
  potencyRow[5]  = parsed.cbdMgG        !== null ? parsed.cbdMgG        : '';
  potencyRow[6]  = parsed.cbdMgPkg      !== null ? parsed.cbdMgPkg      : '';
  potencyRow[7]  = parsed.totalCbPct    !== null ? parsed.totalCbPct    : '';
  potencyRow[8]  = parsed.totalCbMgG    !== null ? parsed.totalCbMgG    : '';
  potencyRow[9]  = parsed.totalCbMgPkg  !== null ? parsed.totalCbMgPkg  : '';

  // Write cols W(23) through AF(32) in one call
  sheet.getRange(rowNum, CONFIG.COL.COA_LINK, 1, 10).setValues([potencyRow]);

  SpreadsheetApp.flush();

  const testType      = (parsed.testType     || '').toUpperCase();
  const result        = (parsed.overallResult|| '').toUpperCase();
  const currentStatus = String(sheet.getRange(rowNum, C.STATUS).getValue() || '').trim().toLowerCase();
  const now           = new Date();

  // ── Any fail → Failed immediately ───────────────────────
  if (result === 'FAIL') {
    sheet.getRange(rowNum, C.STATUS).setValue(CONFIG.STATUS.FAILED);
    sheet.getRange(rowNum, C.LAST_UPDATED).setValue(now);
    Logger.log('Status → Failed for row ' + rowNum);
    return;
  }

  // ── RND Pass ─────────────────────────────────────────────
  if (testType === 'RND' && result === 'PASS') {
    // Store RND potency for later tolerance check
    if (parsed.thcMgPkg !== null) {
      sheet.getRange(rowNum, C.RND_THC_MG_PKG).setValue(parsed.thcMgPkg);
    }

    const rndTerminal = [
      'passed rnd', 'submitted for compliance', 'compliance passed',
      'compliance review', 'avail in distru/on menu',
      'passed but not avail in distru', 'archived'
    ];
    if (rndTerminal.includes(currentStatus)) {
      Logger.log('RND Pass — already past RND stage (' + currentStatus + ') row ' + rowNum);
    } else {
      sheet.getRange(rowNum, C.STATUS).setValue(CONFIG.STATUS.PASSED_RND);
      sheet.getRange(rowNum, C.LAST_UPDATED).setValue(now);
      Logger.log('Status → Passed RND for row ' + rowNum);
    }
    return;
  }

  // ── Compliance Pass — with tolerance check ───────────────
  if (testType === 'COMPLIANCE' && result === 'PASS') {

    // Skip if already at a terminal/complete status
    const terminalStatuses = [
      'compliance passed', 'avail in distru/on menu',
      'passed but not avail in distru', 'archived'
    ];
    if (terminalStatuses.includes(currentStatus)) {
      Logger.log('Compliance Pass — already terminal status (' + currentStatus + ') row ' + rowNum);
      return;
    }

    const toleranceResult = _checkTolerance(sheet, rowNum, parsed, C);
    Logger.log('Tolerance check: ' + toleranceResult + ' for row ' + rowNum);

    sheet.getRange(rowNum, C.TOLERANCE_FLAG).setValue(toleranceResult);

    if (toleranceResult === 'WITHIN') {
      sheet.getRange(rowNum, C.STATUS).setValue(CONFIG.STATUS.COMPLIANCE_PASSED);
      Logger.log('Status → Compliance Passed for row ' + rowNum);
    } else {
      sheet.getRange(rowNum, C.STATUS).setValue(CONFIG.STATUS.COMPLIANCE_REVIEW);
      Logger.log('Status → Compliance Review (' + toleranceResult + ') for row ' + rowNum);
    }

    sheet.getRange(rowNum, C.LAST_UPDATED).setValue(now);
    return;
  }
}

// ── TOLERANCE CHECK ──────────────────────────────────────────
function _checkTolerance(sheet, rowNum, parsed, C) {
  const category = String(sheet.getRange(rowNum, C.CATEGORY).getValue() || '').trim().toLowerCase();

  const isEdible = category.includes('edible');

  const complianceMgPkg = parsed.thcMgPkg;
  if (complianceMgPkg === null) return 'WITHIN'; // no data — can't check, pass through

  let labelClaim;

  if (isEdible) {
    // Edibles: label claim is always 100mg
    labelClaim = 100;
    // Write 100 to LABEL_CLAIM_MG if not already set
    const existing = sheet.getRange(rowNum, C.LABEL_CLAIM_MG).getValue();
    if (!existing) sheet.getRange(rowNum, C.LABEL_CLAIM_MG).setValue(100);
  } else {
    // Concentrates/Vapes/Prerolls: label claim = RND result
    labelClaim = sheet.getRange(rowNum, C.RND_THC_MG_PKG).getValue();
    if (!labelClaim) {
      // No RND result stored — can't check tolerance, pass through
      Logger.log('No RND result stored for tolerance check — row ' + rowNum);
      return 'WITHIN';
    }
  }

  // Calculate % difference from label claim
  const pctDiff = ((complianceMgPkg - labelClaim) / labelClaim) * 100;

  Logger.log('Tolerance: compliance=' + complianceMgPkg + 
             ' labelClaim=' + labelClaim + 
             ' diff=' + pctDiff.toFixed(1) + '%');

  if (pctDiff > 10)  return 'OVER';
  if (pctDiff < -10) return 'UNDER';
  return 'WITHIN';
}

// ── LOG SHEET SETUP ──────────────────────────────────────────
function setupCOALogTab() {
  const ss = SpreadsheetApp.openById(CONFIG.TRACKER_SS_ID);
  let logSheet = ss.getSheetByName(COA_CONFIG.LOG_TAB);

  if (!logSheet) {
    logSheet = ss.insertSheet(COA_CONFIG.LOG_TAB);
  } else {
    logSheet.clearContents();
  }

  const headers = [
    'Parse Date',
    'Test Date',
    'Lab',
    'METRC UID',
    'Batch ID',
    'Lab Sample ID',
    'Product Name',
    'Pkg Size (g)',
    'THC %',
    'THC mg/g',
    'THC mg/pkg',
    'CBD %',
    'CBD mg/g',
    'CBD mg/pkg',
    'Total CB %',
    'Total CB mg/g',
    'Total CB mg/pkg',
    'COA Drive Link',
    'Match Status',
  ];

  logSheet.getRange(1, 1, 1, headers.length).setValues([headers]);

  // Format header row
  const headerRange = logSheet.getRange(1, 1, 1, headers.length);
  headerRange.setBackground('#1a1a2e');
  headerRange.setFontColor('#ffffff');
  headerRange.setFontWeight('bold');
  logSheet.setFrozenRows(1);

  // Column widths
  logSheet.setColumnWidth(1, 140);  // Parse Date
  logSheet.setColumnWidth(2, 100);  // Test Date
  logSheet.setColumnWidth(3, 120);  // Lab
  logSheet.setColumnWidth(4, 200);  // METRC UID
  logSheet.setColumnWidth(5, 140);  // Batch ID
  logSheet.setColumnWidth(6, 160);  // Lab Sample ID
  logSheet.setColumnWidth(7, 260);  // Product Name
  logSheet.setColumnWidth(8, 80);   // Pkg Size
  logSheet.setColumnWidth(18, 200); // COA Link
  logSheet.setColumnWidth(19, 180); // Match Status

  SpreadsheetApp.getUi().alert('COA_LOG tab is ready.');
  return logSheet;
}

// ── UID_TRACKER QUERY FORMULAS ───────────────────────────────

function getTrackerFormulas() {
  // Returns the formula strings to paste into tracker

  const formulas = {
    COA_LINK:       `=IFERROR(INDEX(COA_LOG!R:R,MATCH(1,(COA_LOG!D:D=B4)*(COA_LOG!A:A=MAXIFS(COA_LOG!A:A,COA_LOG!D:D,B4)),0)),"")`,
    THC_PCT:        `=IFERROR(INDEX(COA_LOG!I:I,MATCH(1,(COA_LOG!D:D=B4)*(COA_LOG!A:A=MAXIFS(COA_LOG!A:A,COA_LOG!D:D,B4)),0)),"")`,
    THC_MG_G:       `=IFERROR(INDEX(COA_LOG!J:J,MATCH(1,(COA_LOG!D:D=B4)*(COA_LOG!A:A=MAXIFS(COA_LOG!A:A,COA_LOG!D:D,B4)),0)),"")`,
    THC_MG_PKG:     `=IFERROR(INDEX(COA_LOG!K:K,MATCH(1,(COA_LOG!D:D=B4)*(COA_LOG!A:A=MAXIFS(COA_LOG!A:A,COA_LOG!D:D,B4)),0)),"")`,
    CBD_PCT:        `=IFERROR(INDEX(COA_LOG!L:L,MATCH(1,(COA_LOG!D:D=B4)*(COA_LOG!A:A=MAXIFS(COA_LOG!A:A,COA_LOG!D:D,B4)),0)),"")`,
    CBD_MG_G:       `=IFERROR(INDEX(COA_LOG!M:M,MATCH(1,(COA_LOG!D:D=B4)*(COA_LOG!A:A=MAXIFS(COA_LOG!A:A,COA_LOG!D:D,B4)),0)),"")`,
    CBD_MG_PKG:     `=IFERROR(INDEX(COA_LOG!N:N,MATCH(1,(COA_LOG!D:D=B4)*(COA_LOG!A:A=MAXIFS(COA_LOG!A:A,COA_LOG!D:D,B4)),0)),"")`,
    TOTAL_CB_PCT:   `=IFERROR(INDEX(COA_LOG!O:O,MATCH(1,(COA_LOG!D:D=B4)*(COA_LOG!A:A=MAXIFS(COA_LOG!A:A,COA_LOG!D:D,B4)),0)),"")`,
    TOTAL_CB_MG_G:  `=IFERROR(INDEX(COA_LOG!P:P,MATCH(1,(COA_LOG!D:D=B4)*(COA_LOG!A:A=MAXIFS(COA_LOG!A:A,COA_LOG!D:D,B4)),0)),"")`,
    TOTAL_CB_MG_PKG:`=IFERROR(INDEX(COA_LOG!Q:Q,MATCH(1,(COA_LOG!D:D=B4)*(COA_LOG!A:A=MAXIFS(COA_LOG!A:A,COA_LOG!D:D,B4)),0)),"")`,
  };

  Logger.log(JSON.stringify(formulas, null, 2));
  return formulas;
}

// ── HELPERS ──────────────────────────────────────────────────
function getOrCreateLogSheet(ss) {
  let logSheet = ss.getSheetByName(COA_CONFIG.LOG_TAB);
  if (!logSheet) logSheet = setupCOALogTab();
  return logSheet;
}

function getCOAFolder() {
  const folders = DriveApp.getFoldersByName(COA_CONFIG.COA_FOLDER);
  return folders.hasNext() ? folders.next() : null;
}


function getProcessedLinks(logSheet) {
  const lastRow = logSheet.getLastRow();
  if (lastRow < 2) return new Set();
  const links = logSheet.getRange(2, COA_CONFIG.LOG_COLS.COA_LINK, lastRow - 1, 1).getValues();
  return new Set(links.flat().filter(Boolean));
}

function roundTo(val, decimals) {
  return Math.round(val * Math.pow(10, decimals)) / Math.pow(10, decimals);
}

function debugOnePDF() {
  const folder = getCOAFolder();
  const files  = folder.getFilesByType(MimeType.PDF);
  let count    = 0;

  while (files.hasNext() && count < 2) {
    const file = files.next();
    const text = extractPdfText(file);
    if (!text) continue;

    Logger.log('=== FILE: ' + file.getName() + ' ===');
    Logger.log(text.substring(0, 2000)); // first 2000 chars
    count++;
  }
}

function diagnoseCOAConfig() {
  Logger.log('COA_CONFIG defined: ' + (typeof COA_CONFIG !== 'undefined'));
  Logger.log('CONFIG defined: ' + (typeof CONFIG !== 'undefined'));
  
  try {
    const ss = SpreadsheetApp.openById(CONFIG.TRACKER_SS_ID);
    Logger.log('SS opened OK');
    
    const sheet = ss.getSheetByName(COA_CONFIG.TRACKER_TAB);
    Logger.log('Sheet found: ' + (sheet !== null));
    Logger.log('Last row: ' + sheet.getLastRow());
    Logger.log('DATA_START_ROW: ' + CONFIG.DATA_START_ROW);
    Logger.log('COL.BATCH_ID: ' + CONFIG.COL.BATCH_ID);
    Logger.log('COL.METRC_UID: ' + CONFIG.COL.METRC_UID);
  } catch(e) {
    Logger.log('ERROR: ' + e.message);
    Logger.log('Stack: ' + e.stack);
  }
}