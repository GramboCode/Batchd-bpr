// ============================================================
// TestingOrderPush.gs — Punch Edibles & Extracts | Punch Tools
// ============================================================

const TESTING_ORDER_SS_ID = "1MtLBI21V9qvYHFTFznbWSfKZ5SMYSI0PounMaA4mwxg";
const DISTRO_LOG_SS_ID    = "1Y6k_do81N6gNEDEuRxcPj7WH7OmOvyybIEo4fY2iTTg";
const TEMPLATE_TAB_NAME   = "LabName M/DD/YYYY";
const DISTRO_FULL_LIST    = "Full List";
const ORDER_DATA_START    = 9;

// Column positions in testing order sheet (1-based)
// Col A is blank/index — all data starts at B
const TO_COL = {
  CATEGORY:     2,  // B — Product Category
  SUB_TYPE:     3,  // C — Product Sub-type
  INFUSED:      4,  // D — For Infused Pre-Rolls
  BATCH_ID:     5,  // E — External Batch ID
  METRC_UID:    6,  // F — METRC Source UID
  SAMPLE_NAME:  7,  // G — Sample Name
  HARVEST_DATE: 8,  // H — Harvest/Production Date
  REQ_TESTING:  9,  // I — Requested Testing
  BATCH_SIZE:   10, // J — Total Batch Size
  SAMPLE_SIZE:  11, // K — Sample Size Amount
  COMPLIANCE:   12, // L — Submitted For Compliance
  RND:          13, // M — Submitted For RND
  DELAYED:      14, // N — Delayed
};

// ─────────────────────────────────────────────────────────────
// pushToTestingOrder()
// ─────────────────────────────────────────────────────────────

function pushToTestingOrder(uid, testType, submissionDate, sampleSize, rndType) {
  const batch = getBatchByUID(uid);
  if (!batch) throw new Error("Batch not found: " + uid);
  if (!batch.lab) throw new Error("No lab assigned to this batch. Set a lab before pushing.");

  // Parse submission date
  const dateParts  = submissionDate.split("-");
  const dateObj    = new Date(parseInt(dateParts[0]), parseInt(dateParts[1]) - 1, parseInt(dateParts[2]));
  const dateFmt    = Utilities.formatDate(dateObj, Session.getScriptTimeZone(), "M/d/yyyy");
  const tabName    = batch.lab + " " + dateFmt;

  const isRND          = testType === "RND";
  const requestedLabel = isRND ? (rndType || "R&D - Potency only") : "Compliance";
  const newStatus = isRND ? CONFIG.STATUS.SUBMITTED_FOR_RND : CONFIG.STATUS.SUBMITTED_COMPLIANCE;
  const categoryInfo   = _getCategoryInfo(batch.category, batch.item);

  if (!isRND) {
  const missing = [];
  if (!batch.mfgDate)  missing.push("Mfg / Pkg Date");
  if (!batch.quantity) missing.push("Quantity");
  if (!batch.lab)      missing.push("Lab");
  if (missing.length > 0) {
    throw new Error("Missing required fields for compliance: " + missing.join(", "));
  }
  } else {
    if (!batch.lab) throw new Error("No lab assigned. Set a lab before pushing.");
  }

  // Write to Testing Order Sheet
  _writeToTestingOrder(batch, tabName, dateObj, dateFmt, requestedLabel, isRND, sampleSize, categoryInfo);

  

  // Update UID_TRACKER
  const sheet = getTrackerSheet();
  sheet.getRange(batch.rowIndex, CONFIG.COL.STATUS).setValue(newStatus);
  sheet.getRange(batch.rowIndex, CONFIG.COL.TEST_DATE).setValue(dateObj);
  sheet.getRange(batch.rowIndex, CONFIG.COL.LAST_UPDATED).setValue(new Date());
  bustCache();

  log("Testing order push complete", { uid, tabName, testType });

  return { success: true, tabName, testType, newStatus, distroAdded: false };
}


// ─────────────────────────────────────────────────────────────
// _writeToTestingOrder()
// ─────────────────────────────────────────────────────────────

function _writeToTestingOrder(batch, tabName, dateObj, dateFmt, requestedLabel, isRND, sampleSize, categoryInfo) {
  const ss = SpreadsheetApp.openById(TESTING_ORDER_SS_ID);

  let sheet = ss.getSheetByName(tabName);
  let isNew = false;

  if (!sheet) {
    const template = ss.getSheetByName(TEMPLATE_TAB_NAME);
    if (!template) throw new Error('Template tab "' + TEMPLATE_TAB_NAME + '" not found.');

    sheet = template.copyTo(ss);
    sheet.setName(tabName);

    // Move new tab to position 2 (right after template, newest first)
    try {
      Sheets.Spreadsheets.batchUpdate({
        requests: [{
          updateSheetProperties: {
            properties: {
              sheetId: sheet.getSheetId(),
              index: 1  // 0-based: 0 = template, 1 = new tab
            },
            fields: "index"
          }
        }]
      }, TESTING_ORDER_SS_ID);
    } catch(e) {
      log("Tab reorder failed (non-fatal)", e.message);
    }

    isNew = true;
    log("Created new testing order tab", tabName);
  }

  // Check for duplicate UID in this tab (existing tabs only)
  const lastRow = sheet.getLastRow();
  if (!isNew && lastRow >= ORDER_DATA_START) {
    const existingUIDs = sheet
      .getRange(ORDER_DATA_START, TO_COL.METRC_UID, lastRow - ORDER_DATA_START + 1, 1)
      .getValues().flat().map(String);

    if (existingUIDs.includes(String(batch.metrcUID))) {
      throw new Error(batch.item + ' is already in tab "' + tabName + '".');
    }
  }

  // Find next empty row by scanning col E (External Batch ID)
  const currentLast = sheet.getLastRow();
  let nextRow = ORDER_DATA_START;
  if (currentLast >= ORDER_DATA_START) {
    const colData = sheet
      .getRange(ORDER_DATA_START, TO_COL.BATCH_ID, currentLast - ORDER_DATA_START + 1, 1)
      .getValues();
    for (let i = 0; i < colData.length; i++) {
      if (!colData[i][0]) { nextRow = ORDER_DATA_START + i; break; }
      nextRow = ORDER_DATA_START + i + 1;
    }
  }

  // Write batch data
  sheet.getRange(nextRow, TO_COL.CATEGORY).setValue(categoryInfo.category);
  sheet.getRange(nextRow, TO_COL.SUB_TYPE).setValue(categoryInfo.subType);
  sheet.getRange(nextRow, TO_COL.INFUSED).setValue(categoryInfo.infused);
  sheet.getRange(nextRow, TO_COL.BATCH_ID).setValue(batch.batchID);
  sheet.getRange(nextRow, TO_COL.METRC_UID).setValue(batch.metrcUID);
  sheet.getRange(nextRow, TO_COL.SAMPLE_NAME).setValue(batch.item);
    let mfgDateVal = '';
  if (batch.mfgDate) {
    const parts = batch.mfgDate.split('/');
    if (parts.length === 3) {
      mfgDateVal = new Date(
        parseInt(parts[2]),
        parseInt(parts[0]) - 1,
        parseInt(parts[1])
      );
    }
  }
  if (mfgDateVal) {
    sheet.getRange(nextRow, TO_COL.HARVEST_DATE).setValue(mfgDateVal);
  }
  sheet.getRange(nextRow, TO_COL.REQ_TESTING).setValue(requestedLabel);
  sheet.getRange(nextRow, TO_COL.BATCH_SIZE).setValue(batch.quantity || "");
  sheet.getRange(nextRow, TO_COL.SAMPLE_SIZE).setValue(sampleSize || "");

  // Set correct checkbox — only one true, Delayed always false
  sheet.getRange(nextRow, TO_COL.COMPLIANCE).setValue(!isRND);
  sheet.getRange(nextRow, TO_COL.RND).setValue(isRND);
  sheet.getRange(nextRow, TO_COL.DELAYED).setValue(false);

  return { tabName, row: nextRow };
}



// ─────────────────────────────────────────────────────────────
// _writeToDistroLog()
// ─────────────────────────────────────────────────────────────

function _writeToDistroLog(batch, dateFmt, requestedLabel, sampleSize) {
  const ss    = SpreadsheetApp.openById(DISTRO_LOG_SS_ID);
  const sheet = ss.getSheetByName(DISTRO_FULL_LIST);
  if (!sheet) { log("Distro log Full List tab not found"); return; }

  // Check for duplicate
  const lastRow = sheet.getLastRow();
  if (lastRow >= 7) {
    const existing = sheet.getRange(7, 1, lastRow - 6, 8).getValues();
    const isDupe = existing.some(function(r) {
      return normalize(String(r[2])) === normalize(batch.metrcUID) &&
             normalize(String(r[5])) === normalize(requestedLabel);
    });
    if (isDupe) { log("Distro log: duplicate skipped", batch.metrcUID); return; }
  }

  // Insert at row 7 — newest first
  sheet.insertRowsBefore(7, 1);
  sheet.getRange(7, 1, 1, 8).setValues([[
    dateFmt,
    batch.batchID,
    batch.metrcUID,
    batch.item,
    batch.mfgDate,
    distroLabel,
    batch.quantity || "",
    batch.lab,
  ]]);

  log("Distro log updated", { uid: batch.metrcUID, lab: batch.lab });
}


// ─────────────────────────────────────────────────────────────
// _getCategoryInfo(category, itemName)
//
// Maps METRC category + item name to testing order columns.
// Product Category options: Plant, Ingestible, Concentrate, Vape
// Sub-type left blank — user selects from sheet dropdown.
// ─────────────────────────────────────────────────────────────

function _getCategoryInfo(category, itemName) {
  const cat  = (category  || "").toLowerCase();
  const item = (itemName  || "").toLowerCase();

  // PLANT — Pre-rolls
  if (cat.includes("pre-roll infused")) {
    return { category: "Plant", subType: "", infused: "Yes" };
  }
  if (cat.includes("pre-roll")) {
    return { category: "Plant", subType: "", infused: "No" };
  }

  // VAPE — Cartridges and AIO vapes
  if (cat.includes("vape") || cat.includes("cartridge")) {
    return { category: "Vape", subType: "", infused: "No" };
  }

  // INGESTIBLE — Edibles
  if (cat.includes("edible") || cat.includes("ingestible")) {
    return { category: "Ingestible", subType: "", infused: "No" };
  }

  // CONCENTRATE — Everything else
  return { category: "Concentrate", subType: "", infused: "No" };
}


// ─────────────────────────────────────────────────────────────
// getTestingOrderTabs()
// ─────────────────────────────────────────────────────────────

function getTestingOrderTabs() {
  try {
    const ss = SpreadsheetApp.openById(TESTING_ORDER_SS_ID);
    return ss.getSheets()
      .map(function(s) { return s.getName(); })
      .filter(function(n) { return n !== TEMPLATE_TAB_NAME; });
  } catch(e) {
    log("getTestingOrderTabs error", e.message);
    return [];
  }
}
