// ============================================================
// Batches.gs — Punch Edibles & Extracts | Punch Tools
// ============================================================

function getAllBatches() {
  const sheet = getTrackerSheet();
  const lastRow = sheet.getLastRow();

  if (lastRow < CONFIG.DATA_START_ROW) return [];

  const totalCols = CONFIG.COL.LAST_UPDATED; // col 22, skip COA cols W-AI

  const data = sheet
    .getRange(CONFIG.DATA_START_ROW, 1, lastRow - CONFIG.DATA_START_ROW + 1, totalCols)
    .getValues();

  const batches = [];

  const SKIP_STATUSES = [
    'avail in distru/on menu',
    'compliance passed',
    'passed but not avail in distru',
    'archived',
  ];

  for (let i = 0; i < data.length; i++) {
    const row = data[i];
    const metrcUID = row[CONFIG.COL.METRC_UID - 1];

    if (!metrcUID) continue;

    const batchID = row[CONFIG.COL.BATCH_ID - 1];

    // Skip unassigned rows
    if (!batchID) continue;

    // Skip terminal/inactive statuses — too many historical rows
    const status = String(row[CONFIG.COL.STATUS - 1] || '').trim().toLowerCase();
    if (SKIP_STATUSES.includes(status)) continue;

    batches.push({
      rowIndex:       i + CONFIG.DATA_START_ROW,
      metrcUID:       String(metrcUID).trim(),
      item:           row[CONFIG.COL.ITEM - 1]              || "",
      category:       row[CONFIG.COL.CATEGORY - 1]          || "",
      itemStrain:     row[CONFIG.COL.ITEM_STRAIN - 1]       || "",
      batchID:        batchID                               || "",
      mfgDate:        _formatRowDate(row[CONFIG.COL.MFG_DATE - 1]),
      quantity:       row[CONFIG.COL.QUANTITY - 1]          || "",
      targetQty:      row[CONFIG.COL.TARGET_QTY - 1]   || "",
      uom:            row[CONFIG.COL.UNIT_OF_MEASURE - 1]   || "",
      lab:            row[CONFIG.COL.LAB - 1]               || "",
      status:         row[CONFIG.COL.STATUS - 1]            || "",
      testDate:       _formatRowDate(row[CONFIG.COL.TEST_DATE - 1]),
      mridLabel:      row[CONFIG.COL.MRID_LABEL - 1]        || "",
      rndPDF:         row[CONFIG.COL.RND_PDF - 1]           || "",
      retailIDMade:   row[CONFIG.COL.RETAIL_ID_MADE - 1]    === true,
      metrcSynced:    row[CONFIG.COL.METRC_SYNCED - 1]      === true,
      labSampleIDRND: row[CONFIG.COL.LAB_SAMPLE_ID_RND - 1] || "",
      labSampleIDCOA: row[CONFIG.COL.LAB_SAMPLE_ID_COA - 1] || "",
      labResultsURL:  row[CONFIG.COL.LAB_RESULTS_URL - 1]   || "",
      createdAt:      _formatRowDate(row[CONFIG.COL.CREATED_AT - 1]),
      lastUpdated:    _formatRowDate(row[CONFIG.COL.LAST_UPDATED - 1]),
      isAssigned:     !!batchID,
    });
  }

  return batches;
}

// ── CONSTANTS ────────────────────────────────────────────────
const BATCH_RECORD_MASTER_ID = '1GdrkPEzBb2bO8Iz1UZd_E7cp6cU63Edh63P7ozQ8br0';
const BATCH_RECORD_FOLDER_ID = '1K31eoqHn8eujCvNziZ_OLTRdjE8-0YJN';

// ── TAB MAP ──────────────────────────────────────────────────
const BATCH_RECORD_TAB_MAP = {
  punch_live_rosin:    'PUNCH Live Rosin',
  rosin_wash:          'PUNCH Ice Extraction',
  punch_bho_badder:    'PUNCH BHO',
  punch_bho_shatter:   'PUNCH BHO',
  punch_rocket:        'PUNCH Rockets',
  punch_stinger:       'PUNCH Stingers',
  punch_gummies:       'PUNCH Gummies',
  punch_asteroids:     'PUNCH Asteroids',
  punch_punchbar:      '__CHOC_DYNAMIC__',      // routes through detectChocolateTab()
  punch_cookie:        'PUNCH Cookie Delight',
  punch_malt_balls:    'PUNCH Malt Balls',
  punch_rosin_aio:     'PUNCH Rosin Vapes',
  punch_vapes:         'Distillate Vapes',
  punch_2g_dist_vapes: 'Distillate Vapes',
  tempo_aio:           'Distillate Vapes',
  tempo_blends:        'Distillate Vapes',
  tempo_lr_aio:        'TEMPO LR Vape',
  tempo_lr_diamonds:   'Tempo LR Diamonds',
  tempo_live_rosin:    'PUNCH Live Rosin', 
  dr_norms:            '__NORMS_DYNAMIC__',      // routes through detectNormsTab()
  liquidabs:           'LiquiDabs',
};

// ── HEADER CELL MAP ──────────────────────────────────────────
// Shared across ALL tabs (standardized header layout)
const HEADER_CELLS = {
  productName: 'I5',
  batchID:     'C7',
  metrcUID:    'I7',
  mfgDate:     'C10',
  labName:     'I10',
  targetQty:   'C42',
  quantity:    'D42',
  // QR "SCAN TO ACCESS BPR" anchor — top-left of the merged N34:P40 placeholder
  // on the standardized product tabs (the wash template uses M5 separately).
  qrCode:      'N34',
};

// ── CHOCOLATE TAB DETECTION ───────────────────────────────────
// All three chocolate variants share templateKey 'punch_punchbar'.
// Differentiate by flavor/SKU string passed in item name.
function detectChocolateTab(itemName) {
  const n = itemName.toLowerCase();

  // Sugar-Free: "sugar-free", "sugar free", "sf dark", "sf milk"
  if (n.includes('sugar-free') || n.includes('sugar free') || 
      n.includes('sf dark') || n.includes('sf milk')) {
    return 'PUNCH Choc SF';
  }

  // Peanut Butter: "peanut butter", "pb dark", "pb milk", "pbj"
  if (n.includes('peanut butter') || n.includes('pb dark') || 
      n.includes('pb milk') || n.includes('pbj')) {
    return 'PUNCH Choc PB';
  }

  // Default: standard chocolate
  Logger.log('detectChocolateTab: no SF/PB match for "' + itemName + '" — using PUNCH Chocolate');
  return 'PUNCH Chocolate';
}

// ── DR. NORM'S TAB DETECTION ─────────────────────────────────
function detectNormsTab(itemName) {
  const n = itemName.toLowerCase();

  // Sleep products — BOTH variants share one BPR
  if (n.includes('sleep')) return 'DN Mini SLP Brwn 2:1';

  // NANO products (Cookies N Cream has no non-nano tab — route both there)
  if (n.includes('cookies n cream') || n.includes('cookies & cream')) return 'DN C&C Nano';
  if (n.includes('nano rkt cinnamon') || n.includes('cinnamon toast'))  return 'DN RKT CTC';
  if (n.includes('nano rkt very berry') || n.includes('very berry'))   return 'DN RKT Very Berry';

  // RKT products
  if (n.includes('rkt matcha'))                                        return 'DN RKT Matcha';
  if (n.includes('rkt original'))                                      return 'DN RKT Original';
  if (n.includes('rkt fruity'))                                        return 'DN RKT Fruity Pebbles';
  if (n.includes('rkt chocolate') || n.includes('rkt choc'))          return 'DN RKT Chocolate';
  // RKT Captain Crunch + Fiery Hot Crunch Bar — discontinued, no explicit route,
  // falls through to default below (fine, since nobody should be selecting these anymore)

  // Brownies / bars — split
  if (n.includes('salted caramel') || n.includes('blondie'))          return 'DN Salted Caramel Blondie';
  if (n.includes('peanut butter cup brownie') || n.includes('pb cup')) return 'DN PB Cup Brwn HASH';
  if (n.includes('brownie'))                                           return 'DN Fudg Brwn'; // Chocolate Fudge + Solventless PB Chocolate Brownie

  // Cookies
  if (n.includes('snickerdoodle'))                                     return 'DN Snickerdoodle';
  if (n.includes('red velvet'))                                        return 'DN Red Velvet';
  if (n.includes('peanut butter') || n.includes('pb choc'))           return 'DN PB Choc';
  if (n.includes('pecan shortbread'))                                  return 'DN Pecan SB';
  if (n.includes('chocolate chip') || n.includes('choc chip'))        return 'DN Choc Chip';

  Logger.log('detectNormsTab: no match for "' + itemName + '" — using DN Choc Chip as fallback');
  return 'DN Choc Chip';
}

// ── CREATE BATCH RECORD ──────────────────────────────────────
// Called from BatchD when a new batch is created.
// Params:
//   uid         — METRC UID string
//   item        — full generated product name (e.g. "Punch – 100mg Gummies – Blueberry Lemonade")
//   batchID     — batch ID string (e.g. "TCAVSTRBTZ005")
//   templateKey — product type key from BATCH_RECORD_TAB_MAP
//   mfgDate     — manufacturing date string (e.g. "06/23/2026") [optional]
//   quantity    — unit quantity number [optional]
//   labName     — testing lab name string [optional]
//
function createBatchRecord(uid, item, batchID, templateKey, mfgDate, quantity, labName) {
  Logger.log('createBatchRecord called — templateKey: "' + templateKey + '" | item: "' + item + '"');
  try {
    // ── 1. Resolve tab name ──────────────────────────────────
    let tabName = BATCH_RECORD_TAB_MAP[templateKey];
    if (!tabName) {
      Logger.log('createBatchRecord: no tab mapped for templateKey "' + templateKey + '"');
      return null;
    }
    if (tabName === '__CHOC_DYNAMIC__') tabName = detectChocolateTab(item);
    if (tabName === '__NORMS_DYNAMIC__') tabName = detectNormsTab(item);

    // ── 2. Open master & find source tab ────────────────────
    const masterSS    = SpreadsheetApp.openById(BATCH_RECORD_MASTER_ID);
    const sourceSheet = masterSS.getSheetByName(tabName);
    if (!sourceSheet) {
      Logger.log('createBatchRecord: tab "' + tabName + '" not found in master BPR spreadsheet');
      return null;
    }

    // ── 3. Create new spreadsheet named for this batch ──────
    const newSS   = SpreadsheetApp.create(item + ' — ' + batchID);
    const newFile = DriveApp.getFileById(newSS.getId());

    // ── 4. File into UID subfolder under COA Archive ─────────
    const coaFolder = getCOAArchiveFolder();
    if (coaFolder) {
      const uidFolder = getOrCreateUIDFolder(coaFolder, uid);
      uidFolder.addFile(newFile);
    } else {
      const batchFolder = DriveApp.getFolderById(BATCH_RECORD_FOLDER_ID);
      batchFolder.addFile(newFile);
    }
    DriveApp.getRootFolder().removeFile(newFile);

    // ── 5. Copy template tab into new spreadsheet ────────────
    const newSheet = sourceSheet.copyTo(newSS);
    newSheet.setName(tabName);

    const defaultSheet = newSS.getSheetByName('Sheet1');
    if (defaultSheet) newSS.deleteSheet(defaultSheet);

    // ── 6. Write header fields ───────────────────────────────
    // Required — always written
    newSheet.getRange(HEADER_CELLS.productName).setValue(item);
    newSheet.getRange(HEADER_CELLS.batchID).setValue(batchID);
    newSheet.getRange(HEADER_CELLS.metrcUID).setValue(uid);

    // Optional — only written if provided
    if (mfgDate)  newSheet.getRange(HEADER_CELLS.mfgDate).setValue(mfgDate);
    if (quantity) newSheet.getRange(HEADER_CELLS.quantity).setValue(quantity);
    if (labName)  newSheet.getRange(HEADER_CELLS.labName).setValue(labName);

    // ── 6b. QR deep link → digital BPR ───────────────────────
    // Every template has a "SCAN TO ACCESS BPR" placeholder, but only the wash
    // path embedded a QR until now. Scan the printed sheet → land in the BPR app
    // for THIS batch (finished goods key on the METRC UID). Non-fatal: a QR
    // hiccup must never block batch-record creation.
    try {
      var bprDeepLink = 'https://batchd-bpr.netlify.app' +
        '?uid=' + encodeURIComponent(uid) +
        '&product=' + encodeURIComponent(item) +
        '&batchId=' + encodeURIComponent(batchID) +
        (mfgDate ? '&mfgDate=' + encodeURIComponent(mfgDate) : '');
      var qrBlob = UrlFetchApp.fetch(
        'https://quickchart.io/qr?text=' + encodeURIComponent(bprDeepLink) + '&size=200'
      ).getBlob().setName('bpr_qr.png');
      var qrAnchor = newSheet.getRange(HEADER_CELLS.qrCode);
      newSheet.insertImage(qrBlob, qrAnchor.getColumn(), qrAnchor.getRow())
              .setWidth(130).setHeight(130);  // fills the N34:P40 placeholder
    } catch(qrErr) {
      Logger.log('QR embed failed (non-fatal): ' + qrErr.message);
    }

    // ── 7. Inject formulas ───────────────────────────────────
    injectBPRFormulas(newSheet, templateKey);

    const url = newSS.getUrl();
    Logger.log('createBatchRecord: success — ' + url);
    return url;

  } catch(e) {
    Logger.log('createBatchRecord error: ' + e.message);
    return null;
  }
}

function getBatchByUID(uid) {
  if (!uid) return null;

  // Try active cache first
  let batch = getAllBatches().find(b => normalize(b.metrcUID) === normalize(uid));

  // Fallback — direct sheet scan for archived/completed batches
  if (!batch) {
    try {
      const sheet   = getTrackerSheet();
      const lastRow = sheet.getLastRow();
      const data    = sheet.getRange(
        CONFIG.DATA_START_ROW, 1,
        lastRow - CONFIG.DATA_START_ROW + 1,
        CONFIG.COL.LAST_UPDATED
      ).getValues();

      for (let i = 0; i < data.length; i++) {
        if (normalize(String(data[i][CONFIG.COL.METRC_UID - 1])) === normalize(uid)) {
          const row = data[i];
          const batchID = row[CONFIG.COL.BATCH_ID - 1];
          batch = {
            rowIndex:       i + CONFIG.DATA_START_ROW,
            metrcUID:       String(row[CONFIG.COL.METRC_UID - 1]).trim(),
            item:           row[CONFIG.COL.ITEM - 1]              || "",
            category:       row[CONFIG.COL.CATEGORY - 1]          || "",
            itemStrain:     row[CONFIG.COL.ITEM_STRAIN - 1]       || "",
            batchID:        batchID                               || "",
            mfgDate:        _formatRowDate(row[CONFIG.COL.MFG_DATE - 1]),
            quantity:       row[CONFIG.COL.QUANTITY - 1]          || "",
            targetQty:      row[CONFIG.COL.TARGET_QTY - 1]   || "",
            uom:            row[CONFIG.COL.UNIT_OF_MEASURE - 1]   || "",
            lab:            row[CONFIG.COL.LAB - 1]               || "",
            status:         row[CONFIG.COL.STATUS - 1]            || "",
            testDate:       _formatRowDate(row[CONFIG.COL.TEST_DATE - 1]),
            mridLabel:      row[CONFIG.COL.MRID_LABEL - 1]        || "",
            batchSheetURL:  row[CONFIG.COL.BATCH_SHEET_URL - 1]   || "",
            retailIDMade:   row[CONFIG.COL.RETAIL_ID_MADE - 1]    === true,
            metrcSynced:    row[CONFIG.COL.METRC_SYNCED - 1]      === true,
            labSampleIDRND: row[CONFIG.COL.LAB_SAMPLE_ID_RND - 1] || "",
            labSampleIDCOA: row[CONFIG.COL.LAB_SAMPLE_ID_COA - 1] || "",
            labResultsURL:  row[CONFIG.COL.LAB_RESULTS_URL - 1]   || "",
            createdAt:      _formatRowDate(row[CONFIG.COL.CREATED_AT - 1]),
            lastUpdated:    _formatRowDate(row[CONFIG.COL.LAST_UPDATED - 1]),
            isAssigned:     !!batchID,
          };
          break;
        }
      }
    } catch(e) {
      Logger.log('getBatchByUID fallback error: ' + e.message);
    }
  }

  if (!batch) return null;

  // Read folderURL from rich text on col C
  try {
    const sheet   = getTrackerSheet();
    const lastRow = sheet.getLastRow();
    const data    = sheet.getRange(
      CONFIG.DATA_START_ROW, CONFIG.COL.METRC_UID,
      lastRow - CONFIG.DATA_START_ROW + 1, 1
    ).getValues();

    for (let i = 0; i < data.length; i++) {
      if (normalize(String(data[i][0])) === normalize(uid)) {
        const richText = sheet.getRange(
          CONFIG.DATA_START_ROW + i, CONFIG.COL.ITEM
        ).getRichTextValue();
        batch.folderURL = richText ? richText.getLinkUrl() : '';
        break;
      }
    }
  } catch(e) {
    batch.folderURL = '';
  }

  return batch;
}


function getBatchByBatchID(batchID) {
  if (!batchID) return null;
  const batches = getAllBatches();
  return batches.find(b => normalize(b.batchID) === normalize(batchID)) || null;
}


function getNextAvailableUID() {
  const sheet = getTrackerSheet();
  const lastRow = sheet.getLastRow();

  if (lastRow < CONFIG.DATA_START_ROW) return null;

  const data = sheet
    .getRange(CONFIG.DATA_START_ROW, 1, lastRow - CONFIG.DATA_START_ROW + 1, CONFIG.COL.BATCH_ID)
    .getValues();

  for (let i = data.length - 1; i >= 0; i--) {
    const metrcUID = data[i][CONFIG.COL.METRC_UID - 1];
    const batchID  = data[i][CONFIG.COL.BATCH_ID - 1];

    if (metrcUID && !batchID) {
      return { uid: String(metrcUID).trim(), rowIndex: i + CONFIG.DATA_START_ROW };
    }
  }

  return null;
}


function createBatch(data) {
  const required = ["item", "batchID", "mfgDate", "category"];
  for (const field of required) {
    if (!data[field] || !data[field].toString().trim()) {
      throw new Error("Missing required field: " + field);
    }
  }

  const existing = getBatchByBatchID(data.batchID);
  if (existing) {
    throw new Error("Batch ID already exists: " + data.batchID + " (assigned to " + existing.item + ")");
  }

  const available = getNextAvailableUID();
  if (!available) {
    throw new Error("No available METRC UIDs. Please import new tags before creating a batch.");
  }

  const sheet      = getTrackerSheet();
  const mfgDateObj = parseISODate(data.mfgDate);
  const row        = available.rowIndex;
  const now        = new Date();

  const rowData = new Array(20).fill('');
  rowData[CONFIG.COL.ITEM           - 3] = data.item.trim();
  rowData[CONFIG.COL.CATEGORY       - 3] = data.category.trim();
  rowData[CONFIG.COL.ITEM_STRAIN    - 3] = (data.itemStrain || '').trim();
  rowData[CONFIG.COL.BATCH_ID       - 3] = data.batchID.trim().toUpperCase();
  rowData[CONFIG.COL.MFG_DATE       - 3] = mfgDateObj;
  rowData[CONFIG.COL.TARGET_QTY    - 3] = data.quantity || '';
  rowData[CONFIG.COL.QUANTITY      - 3] = '';
  rowData[CONFIG.COL.UNIT_OF_MEASURE- 3] = data.uom || 'ea';
  rowData[CONFIG.COL.LAB            - 3] = data.lab || '';
  rowData[CONFIG.COL.STATUS         - 3] = CONFIG.STATUS.IN_PRODUCTION;
  rowData[CONFIG.COL.CREATED_AT     - 3] = now;
  rowData[CONFIG.COL.LAST_UPDATED   - 3] = now;

  // Write cols 3-22 (skip col B which already has METRC_UID)
  sheet.getRange(row, 3, 1, 20).setValues([rowData]);
  SpreadsheetApp.flush();

  log("Batch created", { uid: available.uid, batchID: data.batchID, item: data.item });

  // ── Create UID folder in COA Archive ─────────────────────
  let uidFolderUrl = null;
  try {
    const coaFolder = getCOAArchiveFolder();
    if (coaFolder) {
      const uidFolder = getOrCreateUIDFolder(coaFolder, available.uid);
      uidFolderUrl = uidFolder.getUrl();
      Logger.log('UID folder ready: ' + available.uid);
    }
  } catch(folderErr) {
    Logger.log('UID folder creation failed (non-fatal): ' + folderErr.message);
  }

  // ── Create Batch Record from template ────────────────────
  try {
    const batchRecordUrl = createBatchRecord(
      available.uid,
      data.item.trim(),
      data.batchID.trim().toUpperCase(),
      data.templateKey || '',
      data.mfgDate     || '',
      data.quantity    || '',
      data.lab         || ''
    );
    if (batchRecordUrl) {
      Logger.log('Batch record created and filed in UID folder: ' + batchRecordUrl);
    }
  } catch(recErr) {
    Logger.log('Batch record creation failed (non-fatal): ' + recErr.message);
  }

  // ── Col C → hyperlink to UID Drive folder ────────────────
  try {
    if (uidFolderUrl) {
      const itemName = sheet.getRange(row, CONFIG.COL.ITEM).getValue();
      const richText = SpreadsheetApp.newRichTextValue()
        .setText(itemName)
        .setLinkUrl(uidFolderUrl)
        .build();
      sheet.getRange(row, CONFIG.COL.ITEM).setRichTextValue(richText);
      Logger.log('Col C hyperlinked to UID folder');
    }
  } catch(linkErr) {
    Logger.log('Col C hyperlink failed (non-fatal): ' + linkErr.message);
  }

  return getBatchByUID(available.uid);
}  


function updateBatchStatus(uid, status) {
  const validStatuses = Object.values(CONFIG.STATUS);
  if (!validStatuses.includes(status)) {
    throw new Error("Invalid status value: '" + status + "'");
  }

  const batch = getBatchByUID(uid);
  if (!batch) throw new Error("Batch not found: " + uid);

  const sheet = getTrackerSheet();
  sheet.getRange(batch.rowIndex, CONFIG.COL.STATUS).setValue(status);
  sheet.getRange(batch.rowIndex, CONFIG.COL.LAST_UPDATED).setValue(new Date());
  bustCache();
  syncUIDToDistroLog(uid, status); 

  log("Status updated", { uid, status });
  return { success: true, status };
}


function requestTesting(uid, testType, testDate) {
  const batch = getBatchByUID(uid);
  if (!batch) throw new Error("UID not found: " + uid);

  const current = batch.status;

  if (testType === "RND") {
    if (current === CONFIG.STATUS.READY_FOR_RND) {
      throw new Error("RND testing already requested for this batch.");
    }
    if (current === CONFIG.STATUS.READY_FOR_TESTING) {
      throw new Error("Cannot request RND after full compliance testing.");
    }
  }

  if (testType === "FULL") {
    if (current === CONFIG.STATUS.READY_FOR_TESTING) {
      throw new Error("Full compliance testing already requested.");
    }
  }

  const newStatus = testType === "RND"
    ? CONFIG.STATUS.READY_FOR_RND
    : CONFIG.STATUS.SUBMITTED_COMPLIANCE;

  const sheet = getTrackerSheet();
  sheet.getRange(batch.rowIndex, CONFIG.COL.STATUS).setValue(newStatus);
  sheet.getRange(batch.rowIndex, CONFIG.COL.TEST_DATE).setValue(parseISODate(testDate));
  sheet.getRange(batch.rowIndex, CONFIG.COL.LAST_UPDATED).setValue(new Date());

  log("Testing requested", { uid, testType, testDate, newStatus });
  return getBatchByUID(uid);
}


function importUIDs(uidList) {
  if (!uidList || uidList.length === 0) throw new Error("No UIDs provided.");

  const sheet = getTrackerSheet();
  const existingBatches = getAllBatches();
  const existingUIDs = new Set(existingBatches.map(b => b.metrcUID.trim()));

  const METRC_UID_PATTERN = /^(1A|ABC)[A-Z0-9]{22}$/i;

  let imported = 0;
  let skipped  = 0;
  let errors   = [];
  let toImport = [];

  for (const rawUID of uidList) {
    const uid = rawUID.toString().trim();
    if (!uid) continue;

    if (!METRC_UID_PATTERN.test(uid)) {
      errors.push(uid + " — invalid format");
      continue;
    }

    if (existingUIDs.has(uid)) {
      skipped++;
      continue;
    }

    toImport.push(uid);
    existingUIDs.add(uid);
  }

  toImport.sort().reverse(); // descending

  if (toImport.length > 0) {
    // Insert rows at DATA_START_ROW to push existing data down
    sheet.insertRowsBefore(CONFIG.DATA_START_ROW, toImport.length);
    const rowsToWrite = toImport.map(uid => [uid]);
    sheet.getRange(CONFIG.DATA_START_ROW, CONFIG.COL.METRC_UID, toImport.length, 1)
      .setValues(rowsToWrite);
    imported = toImport.length;
  }

  log("UIDs imported", { imported, skipped, errors: errors.length });
  return { imported, skipped, errors, nextAvailable: getNextAvailableUID() };
}


function searchBatches(query, filters) {
  let batches = getAllBatches();

  if (query && query.trim()) {
    const q = normalize(query);
    batches = batches.filter(b =>
      normalize(b.item).includes(q)     ||
      normalize(b.batchID).includes(q)  ||
      normalize(b.metrcUID).includes(q) ||
      normalize(b.category).includes(q)
    );
  }

  if (filters) {
    if (filters.status) {
      batches = batches.filter(b => normalize(b.status) === normalize(filters.status));
    }
    if (filters.lab) {
      batches = batches.filter(b => normalize(b.lab) === normalize(filters.lab));
    }
    if (filters.assigned !== undefined && filters.assigned !== null) {
      batches = batches.filter(b => b.isAssigned === filters.assigned);
    }
    if (filters.activeOnly) {
      const inactiveStatuses = [
        "Passed BUT NOT Avail in Distru",
        "Avail in Distru/On Menu",
      ];
      batches = batches.filter(b => !inactiveStatuses.includes(b.status));
    }
  }

  return batches.reverse();
}


function updateLabResults(uid, sampleID, resultsURL, newStatus, isRND) {
  const batch = getBatchByUID(uid);
  if (!batch) throw new Error("UID not found: " + uid);

  const sheet = getTrackerSheet();
  const row   = batch.rowIndex;
  const now   = new Date();

  if (sampleID) {
    const col = (isRND !== false)
      ? CONFIG.COL.LAB_SAMPLE_ID_RND
      : CONFIG.COL.LAB_SAMPLE_ID_COA;
    sheet.getRange(row, col).setValue(sampleID.trim());
  }

  if (resultsURL) {
    sheet.getRange(row, CONFIG.COL.LAB_RESULTS_URL).setValue(resultsURL.trim());
  }

  if (newStatus) {
    const validStatuses = Object.values(CONFIG.STATUS);
    if (validStatuses.includes(newStatus)) {
      sheet.getRange(row, CONFIG.COL.STATUS).setValue(newStatus);
    }
  }

  sheet.getRange(row, CONFIG.COL.LAST_UPDATED).setValue(now);
  log("Lab results updated", { uid, sampleID, newStatus });
  return getBatchByUID(uid);
}


function getBatchBySampleID(sampleID) {
  if (!sampleID) return null;

  const sheet   = getTrackerSheet();
  const lastRow = sheet.getLastRow();
  if (lastRow < CONFIG.DATA_START_ROW) return null;

  // Check RND column first
  const rndData = sheet
    .getRange(CONFIG.DATA_START_ROW, CONFIG.COL.LAB_SAMPLE_ID_RND, lastRow - CONFIG.DATA_START_ROW + 1, 1)
    .getValues();

  for (let i = 0; i < rndData.length; i++) {
    if (rndData[i][0] && normalize(String(rndData[i][0])) === normalize(sampleID)) {
      const uid = sheet.getRange(i + CONFIG.DATA_START_ROW, CONFIG.COL.METRC_UID).getValue();
      return getBatchByUID(uid);
    }
  }

  // Then check COA column
  const coaData = sheet
    .getRange(CONFIG.DATA_START_ROW, CONFIG.COL.LAB_SAMPLE_ID_COA, lastRow - CONFIG.DATA_START_ROW + 1, 1)
    .getValues();

  for (let i = 0; i < coaData.length; i++) {
    if (coaData[i][0] && normalize(String(coaData[i][0])) === normalize(sampleID)) {
      const uid = sheet.getRange(i + CONFIG.DATA_START_ROW, CONFIG.COL.METRC_UID).getValue();
      return getBatchByUID(uid);
    }
  }

  return null;
}


function getBatchByOrderNumber(orderNumber) {
  log("getBatchByOrderNumber called", orderNumber);
  return [];
}


function recordStatusChange(uid, newStatus, source) {
  const batch = getBatchByUID(uid);
  if (!batch) throw new Error("UID not found: " + uid);

  const validStatuses = Object.values(CONFIG.STATUS);
  if (!validStatuses.includes(newStatus)) throw new Error("Invalid status: " + newStatus);

  const sheet = getTrackerSheet();
  const now   = new Date();

  sheet.getRange(batch.rowIndex, CONFIG.COL.STATUS).setValue(newStatus);
  sheet.getRange(batch.rowIndex, CONFIG.COL.LAST_UPDATED).setValue(now);

  log("Status changed", { uid, from: batch.status, to: newStatus, source: source || "unknown", time: now.toISOString() });

  // Future: _appendStatusLog(uid, batch.status, newStatus, source, now);
  return true;
}

function searchBatchesCached(query, filters) {
  let batches = getAllBatchesCached();

  if (query && query.trim()) {
    const q = normalize(query);
    batches = batches.filter(b =>
      normalize(b.item).includes(q)     ||
      normalize(b.batchID).includes(q)  ||
      normalize(b.metrcUID).includes(q) ||
      normalize(b.category).includes(q)
    );
  }

  if (filters) {
    if (filters.status) {
      batches = batches.filter(b => normalize(b.status) === normalize(filters.status));
    }
    if (filters.lab) {
      batches = batches.filter(b => normalize(b.lab) === normalize(filters.lab));
    }
    if (filters.assigned !== undefined && filters.assigned !== null) {
      batches = batches.filter(b => b.isAssigned === filters.assigned);
    }
    if (filters.activeOnly) {
      const inactiveStatuses = [
        "Passed BUT NOT Avail in Distru",
        "Avail in Distru/On Menu",
      ];
      batches = batches.filter(b => !inactiveStatuses.includes(b.status));
    }
  }

  return batches.reverse();
}

function getAllBatchesCached() {
  try {
    const cache  = CacheService.getScriptCache();
    const cached = cache.get('punch_all_batches');
    if (cached) {
      const parsed = JSON.parse(cached);
      if (parsed && parsed.split) {
        // Reassemble from split cache
        const part1 = cache.get('punch_all_batches_1');
        const part2 = cache.get('punch_all_batches_2');
        if (part1 && part2) {
          log("Cache HIT (split)");
          return [...JSON.parse(part1), ...JSON.parse(part2)];
        }
      } else {
        log("Cache HIT");
        return parsed;
      }
    }
  } catch(e) { log("Cache read error", e.message); }

  const batches = getAllBatches();

  try {
    const cache = CacheService.getScriptCache();
    const slim = batches.map(b => ({
      rowIndex:   b.rowIndex,
      metrcUID:   b.metrcUID,
      item:       b.item,
      batchID:    b.batchID,
      category:   b.category,
      itemStrain: b.itemStrain,
      lab:        b.lab,
      status:     b.status,
      mfgDate:    b.mfgDate,
      testDate:   b.testDate,
      quantity:   b.quantity,
      uom:        b.uom,
      isAssigned: b.isAssigned,
    }));
    const serialized = JSON.stringify(slim);
    log("Slim cache size: " + serialized.length + " chars");
    if (serialized.length < 90000) {
      cache.put('punch_all_batches', serialized, 300);
      log("Cache saved ✓");
    } else {
      const half = Math.ceil(slim.length / 2);
      const part1 = JSON.stringify(slim.slice(0, half));
      const part2 = JSON.stringify(slim.slice(half));
      if (part1.length < 90000 && part2.length < 90000) {
        cache.put('punch_all_batches_1', part1, 300);
        cache.put('punch_all_batches_2', part2, 300);
        cache.put('punch_all_batches', JSON.stringify({split: true}), 300);
        log("Split cache saved ✓");
      } else {
        log("Cache too large even split — skipping");
      }
    }
  } catch(e) { log("Cache write error", e.message); }

  return batches;
}

function bustCache() {
  try {
    const cache = CacheService.getScriptCache();
    cache.removeAll(['punch_all_batches', 'punch_all_batches_1', 'punch_all_batches_2']);
    log("Cache busted");
  } catch(e) { log("Cache bust error", e.message); }
}

// ── HASH LOT WASH BATCH RECORD — coordinates verified against
// PUNCH Ice Extraction template directly (NOT via HEADER_CELLS,
// which is stale — see flagged bug, fix pending)
const WASH_HEADER_CELLS = {
  productName: 'I5',
  strain:      'I6',
  hashLotId:   'C7',
  metrcUid:    'I7',
  washDate:    'C9',   // merged C9:E9 — Section 1 "Wash Date" field (was C10, wrong row)
  qrCode:      'M5',
};


function createWashBatchRecord(uid, item, hashLotId, strain, washDate) {
  Logger.log('createWashBatchRecord called — hashLotId: "' + hashLotId + '" | item: "' + item + '"');
  try {
    const tabName = 'PUNCH Ice Extraction';

    const masterSS    = SpreadsheetApp.openById(BATCH_RECORD_MASTER_ID);
    const sourceSheet = masterSS.getSheetByName(tabName);
    if (!sourceSheet) {
      Logger.log('createWashBatchRecord: tab "' + tabName + '" not found in master BPR spreadsheet');
      return null;
    }

    const newSS   = SpreadsheetApp.create(item + ' — ' + hashLotId);
    const newFile = DriveApp.getFileById(newSS.getId());

    const coaFolder = getCOAArchiveFolder();
    if (coaFolder) {
      const uidFolder = getOrCreateUIDFolder(coaFolder, uid);
      uidFolder.addFile(newFile);
    } else {
      const batchFolder = DriveApp.getFolderById(BATCH_RECORD_FOLDER_ID);
      batchFolder.addFile(newFile);
    }
    DriveApp.getRootFolder().removeFile(newFile);

    // Copy BOTH tabs — the main BPR AND the session log
    const bprSheet = sourceSheet.copyTo(newSS);
    bprSheet.setName(tabName);

    const sessionLogSource = masterSS.getSheetByName('Ice Extraction Session Log');
    if (sessionLogSource) {
      const sessionLogSheet = sessionLogSource.copyTo(newSS);
      sessionLogSheet.setName('Ice Extraction Session Log');
    } else {
      Logger.log('createWashBatchRecord: "Ice Extraction Session Log" tab not found — session data will have no destination');
    }

    const defaultSheet = newSS.getSheetByName('Sheet1');
    if (defaultSheet) newSS.deleteSheet(defaultSheet);

    bprSheet.getRange(WASH_HEADER_CELLS.productName).setValue(item);
    bprSheet.getRange(WASH_HEADER_CELLS.strain).setValue(strain || '');
    bprSheet.getRange(WASH_HEADER_CELLS.hashLotId).setValue(hashLotId);
    bprSheet.getRange(WASH_HEADER_CELLS.metrcUid).setValue(uid);
    if (washDate) bprSheet.getRange(WASH_HEADER_CELLS.washDate).setValue(parseISODate(washDate));

    // QR deep link → digital BPR. Scan the printed sheet, land in the app.
    try {
      var bprDeepLink = 'https://batchd-bpr.netlify.app' +
        '?uid=' + encodeURIComponent(hashLotId) +
        '&product=' + encodeURIComponent(item) +
        '&batchId=' + encodeURIComponent(hashLotId) +
        '&category=rosin_wash&bprType=wash';
      var qrBlob = UrlFetchApp.fetch(
        'https://quickchart.io/qr?text=' + encodeURIComponent(bprDeepLink) + '&size=200'
      ).getBlob().setName('bpr_qr.png');

      // Anchor the image over the QR cell; tweak offsets/size to taste
      var qrAnchor = bprSheet.getRange(WASH_HEADER_CELLS.qrCode);
      bprSheet.insertImage(qrBlob, qrAnchor.getColumn(), qrAnchor.getRow())
              .setWidth(100).setHeight(100);
    } catch(qrErr) {
      Logger.log('QR embed failed (non-fatal): ' + qrErr.message);
    }

    const url = newSS.getUrl();
    Logger.log('createWashBatchRecord: success — ' + url);
    return url;

  } catch(e) {
    Logger.log('createWashBatchRecord error: ' + e.message);
    return null;
  }
}

// ─────────────────────────────────────────────────────────────
// PRIVATE HELPERS
// ─────────────────────────────────────────────────────────────

function _formatRowDate(value) {
  if (!value) return "";
  if (value instanceof Date) return formatDate(value);
  try {
    const d = new Date(value);
    if (!isNaN(d)) return formatDate(d);
  } catch(e) {}
  return value.toString();
}

function _getBatchSheetURL(sheet, rowIndex) {
  try {
    const richText = sheet.getRange(rowIndex, CONFIG.COL.BATCH_SHEET_URL).getRichTextValue();
    return richText ? (richText.getLinkUrl() || "") : "";
  } catch(e) {
    return "";
  }
}

function testGetBatch() {
  const batches = getAllBatches();
  Logger.log("Total batches: " + batches.length);
  if (batches.length > 0) {
    Logger.log(JSON.stringify(batches[0]));
  }
}

function diagnoseDashboard() {
  try {
    const result = serverGetDashboard();
    Logger.log("success: " + result.success);
    if (!result.success) Logger.log("error: " + result.error);
    Logger.log("batches: " + (result.batches ? result.batches.length : "null"));
    Logger.log("stats: " + JSON.stringify(result.stats));
  } catch(e) {
    Logger.log("EXCEPTION: " + e.message);
    Logger.log(e.stack);
  }
}

function testSearchCached() {
  Logger.log(typeof searchBatchesCached);
  Logger.log(typeof searchBatches);
}

function setupStatusDropdown() {
  const sheet = getTrackerSheet();
  const lastRow = Math.max(sheet.getLastRow(), 1000); // cover future rows too
  const dataStart = 4;

  const statuses = [
    "In Production",
    "Ready for Packaging",
    "Packaging Complete",
    "Submitted for RND",
    "Passed RND",
    "Remake",
    "Need Labels",
    "Labels Made",
    "Ready for Testing",
    "Submitted for Compliance",
    "Delayed in Testing",
    "Testing Cancelled",
    "Failed",
    "Compliance Review",
    "Passed BUT NOT Avail in Distru",
    "Avail in Distru/On Menu",
    "Ice Extraction",
  ];

  // Apply dropdown to entire status column (col K) from data start down
  const statusRange = sheet.getRange(dataStart, 11, lastRow - dataStart + 1, 1);

  const rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(statuses, true) // true = show dropdown arrow
    .setAllowInvalid(false)
    .setHelpText("Select a status from the list")
    .build();

  statusRange.setDataValidation(rule);

  Logger.log("Status dropdown applied to " + (lastRow - dataStart + 1) + " rows in col K");
}
function testActiveFilter() {
  const result = searchBatchesCached("", { assigned: true, activeOnly: true });
  Logger.log("Active batches: " + result.length);
  if (result.length > 0) {
    Logger.log("First batch status: " + result[0].status);
  }
}

function cleanStatusValues() {
  const sheet = getTrackerSheet();
  const lastRow = sheet.getLastRow();
  const dataStart = CONFIG.DATA_START_ROW;
  
  const statuses = sheet
    .getRange(dataStart, CONFIG.COL.STATUS, lastRow - dataStart + 1, 1)
    .getValues();
  
  const cleaned = statuses.map(function(row) {
    return [row[0] ? row[0].toString().trim() : ""];
  });
  
  sheet.getRange(dataStart, CONFIG.COL.STATUS, lastRow - dataStart + 1, 1)
    .setValues(cleaned);
  
  bustCache();
  Logger.log("Status values cleaned: " + statuses.length + " rows");
}

function diagnoseStatuses() {
  const sheet = getTrackerSheet();
  const lastRow = sheet.getLastRow();
  const dataStart = CONFIG.DATA_START_ROW;
  const data = sheet.getRange(dataStart, 1, lastRow - dataStart + 1, 10).getValues();
  
  let empty = 0, hasStatus = 0, noUID = 0, breakdown = {};
  
  for (let i = 0; i < data.length; i++) {
    const uid    = data[i][0];
    const status = data[i][9];
    
    if (!uid) { noUID++; continue; }
    if (!status || status.toString().trim() === "") { empty++; continue; }
    
    const s = status.toString().trim();
    breakdown[s] = (breakdown[s] || 0) + 1;
    hasStatus++;
  }
  
  Logger.log("No UID (blank rows): " + noUID);
  Logger.log("Has UID, no status: " + empty);
  Logger.log("Has status: " + hasStatus);
  Logger.log("Breakdown: " + JSON.stringify(breakdown, null, 2));
}

function migrateHistoricalStatuses() {
  const sheet = getTrackerSheet();
  const lastRow = sheet.getLastRow();
  const dataStart = CONFIG.DATA_START_ROW;
  const numRows = lastRow - dataStart + 1;

  const data = sheet.getRange(dataStart, 1, numRows, 10).getValues();

  let updated = 0;
  const updates = [];

  for (let i = 0; i < data.length; i++) {
    const uid    = data[i][0];
    const status = data[i][9];

    if (!uid) continue;

    // Catch empty, whitespace-only, and null
    if (!status || status.toString().trim() === "") {
      updates.push({ row: dataStart + i, status: "Avail in Distru/On Menu" });
      updated++;
    }
  }

  // Batch write for speed
  for (const u of updates) {
    sheet.getRange(u.row, 10).setValue("Avail in Distru/On Menu");
  }

  bustCache();
  Logger.log("Migration complete — updated: " + updated + " rows");
}
function testActiveOnly() {
  const result = searchBatchesCached("", { 
    assigned: true, 
    activeOnly: true 
  });
  Logger.log("Count with activeOnly: " + result.length);
  result.forEach(b => Logger.log(b.item + " — " + b.status));
}
function testBatchPage() {
  const output = HtmlService.createHtmlOutputFromFile("batch");
  const content = output.getContent();
  Logger.log("Has placeholder: " + content.includes("__BATCH_UID__"));
  Logger.log("Content length: " + content.length);
}

function testColumnAlignment() {
  const batches = getAllBatches();
  if (batches.length === 0) {
    Logger.log("No batches found");
    return;
  }
  const b = batches[0];
  Logger.log("METRC UID: " + b.metrcUID);
  Logger.log("Item: " + b.item);
  Logger.log("Batch ID: " + b.batchID);
  Logger.log("Lab: " + b.lab);
  Logger.log("Status: " + b.status);
  Logger.log("Created At: " + b.createdAt);
  Logger.log("Last Updated: " + b.lastUpdated);
}

function debugTemplates() {
  try {
    const raw = PropertiesService.getScriptProperties().getProperty('PRODUCT_TEMPLATES');
    Logger.log('Raw value: ' + raw);
    Logger.log('Type: ' + typeof raw);
    if (raw) {
      const parsed = JSON.parse(raw);
      Logger.log('Parsed keys: ' + Object.keys(parsed).join(', '));
    }
  } catch(e) {
    Logger.log('ERROR: ' + e.message);
  }
}

function resetTemplatesToDefault() {
  const defaults = PropertiesService.getScriptProperties().getProperty('PRODUCT_TEMPLATES');
  if (!defaults) {
    // Trigger the default by calling serverResetTemplates
    serverResetTemplates();
    Logger.log('Templates reset to defaults');
  }
}

function debugTemplates2() {
  const raw = PropertiesService.getScriptProperties().getProperty("punch_templates");
  Logger.log('punch_templates: ' + raw);
}

const COA_ARCHIVE_FOLDER_ID = 'PASTE_DRIVE_COA_FOLDER_ID_HERE';

// ── COA ARCHIVE FOLDER HELPERS ────────────────────────────────
function getCOAArchiveFolder() {
  const folders = DriveApp.getFoldersByName('COA Archive');
  return folders.hasNext() ? folders.next() : null;
}

function getOrCreateUIDFolder(coaArchiveFolder, metrcUid) {
  const existing = coaArchiveFolder.getFoldersByName(metrcUid);
  if (existing.hasNext()) return existing.next();
  const uidFolder = coaArchiveFolder.createFolder(metrcUid);
  uidFolder.createFolder('Labels');
  Logger.log('Created UID folder: ' + metrcUid);
  return uidFolder;
}

function invalidateBatchCache() {
  CacheService.getScriptCache().remove('punch_all_batches');
}
function clearTemplateCache() {
  PropertiesService.getScriptProperties().deleteProperty('punch_templates');
  PropertiesService.getScriptProperties().deleteProperty('PRODUCT_TEMPLATES');
}


function forceRefreshCache() {
  CacheService.getScriptCache().remove('punch_all_batches');
  Logger.log('Cache cleared');
  const batches = getAllBatches();
  Logger.log('Fresh batch count: ' + batches.length);
  const serialized = JSON.stringify(batches);
  Logger.log('New cache size: ' + serialized.length + ' chars');
}

function diagnoseBatchSize() {
  const batches = getAllBatches();
  if (batches.length === 0) { Logger.log('No batches'); return; }
  const b = batches[0];
  Logger.log('Single batch size: ' + JSON.stringify(b).length + ' chars');
  Logger.log('Fields:');
  for (const key of Object.keys(b)) {
    const val = String(b[key] || '');
    Logger.log('  ' + key + ': ' + val.length + ' chars — "' + val.substring(0, 80) + '"');
  }
}

function diagnoseColumns() {
  const sheet = getTrackerSheet();
  const row = sheet.getRange(357, 1, 1, 22).getValues()[0];
  for (let i = 0; i < row.length; i++) {
    Logger.log('Col ' + (i+1) + ' (' + String.fromCharCode(64+i+1) + '): ' + String(row[i]).substring(0, 50));
  }
}

function findShiftedRows() {
  const sheet = getTrackerSheet();
  const lastRow = sheet.getLastRow();
  const data = sheet.getRange(
    CONFIG.DATA_START_ROW, 1,
    lastRow - CONFIG.DATA_START_ROW + 1, 11
  ).getValues();

  let count = 0;
  for (let i = 0; i < data.length; i++) {
    const batchID  = String(data[i][CONFIG.COL.BATCH_ID - 1] || '').trim();
    const quantity = data[i][CONFIG.COL.QUANTITY - 1];

    if (!batchID) continue;

    if (typeof quantity === 'string' && (
      quantity.includes('Production') || quantity.includes('RND') ||
      quantity.includes('Compliance') || quantity.includes('Labels') ||
      quantity.includes('Testing') || quantity.includes('Passed') ||
      quantity.includes('Failed') || quantity.includes('Remake')
    )) {
      Logger.log('SHIFTED ROW ' + (CONFIG.DATA_START_ROW + i) + ': ' + batchID + ' — col H shows: "' + quantity + '"');
      count++;
    }
  }
  Logger.log('Total shifted rows: ' + count);
}

function diagSlimSize() {
  const batches = getAllBatches();
  const slim = batches.map(b => ({
    rowIndex: b.rowIndex, metrcUID: b.metrcUID,
    item: b.item, batchID: b.batchID, category: b.category,
    itemStrain: b.itemStrain, lab: b.lab, status: b.status,
    mfgDate: b.mfgDate, testDate: b.testDate,
    quantity: b.quantity, uom: b.uom, isAssigned: b.isAssigned,
  }));
  
  // Find the largest entries
  const sized = slim.map((b, i) => ({ 
    i, batchID: b.batchID, size: JSON.stringify(b).length 
  }));
  sized.sort((a, b) => b.size - a.size);
  sized.slice(0, 5).forEach(b => 
    Logger.log('Row ' + b.i + ' ' + b.batchID + ': ' + b.size + ' chars')
  );
  Logger.log('Average size: ' + Math.round(slim.reduce((s,b) => s + JSON.stringify(b).length, 0) / slim.length));
}

function diagActualCacheSize() {
  const batches = getAllBatches();
  Logger.log('Total batches from getAllBatches: ' + batches.length);
  Logger.log('Full serialized size: ' + JSON.stringify(batches).length);
  
  // Check if any single batch is huge
  let maxSize = 0;
  let maxBatch = null;
  for (const b of batches) {
    const size = JSON.stringify(b).length;
    if (size > maxSize) { maxSize = size; maxBatch = b.batchID; }
  }
  Logger.log('Largest single batch: ' + maxBatch + ' at ' + maxSize + ' chars');
  
  // Check what slim gives us
  const slim = batches.map(b => ({
    rowIndex: b.rowIndex, metrcUID: b.metrcUID,
    item: b.item, batchID: b.batchID, category: b.category,
    itemStrain: b.itemStrain, lab: b.lab, status: b.status,
    mfgDate: b.mfgDate, testDate: b.testDate,
    quantity: b.quantity, uom: b.uom, isAssigned: b.isAssigned,
  }));
  Logger.log('Slim serialized size: ' + JSON.stringify(slim).length);
  Logger.log('Slim batch count: ' + slim.length);
}

function debugTemplateKeys() {
  const props = PropertiesService.getScriptProperties().getProperties();
  Logger.log('All keys: ' + Object.keys(props).join(', '));
  const pt = props['PRODUCT_TEMPLATES'];
  const pt2 = props['punch_templates'];
  Logger.log('PRODUCT_TEMPLATES has asteroids: ' + (pt ? pt.includes('asteroids') : 'key not found'));
  Logger.log('punch_templates has asteroids: ' + (pt2 ? pt2.includes('asteroids') : 'key not found'));
}

function testAsteroids() {
  const t = getProductTemplates();
  Logger.log('Keys: ' + Object.keys(t).join(', '));
  Logger.log('Has asteroids: ' + ('punch_asteroids' in t));
}

function pushUpdatedTemplates() {
  // Clears stored templates so getProductTemplates() falls back to DEFAULT_TEMPLATES
  // which now includes tempo_live_rosin
  PropertiesService.getScriptProperties().deleteProperty('PRODUCT_TEMPLATES');
  PropertiesService.getScriptProperties().deleteProperty('punch_templates');
  Logger.log('Template cache cleared — DEFAULT_TEMPLATES will be used on next load');
  
  // Verify it's there
  const t = getProductTemplates();
  Logger.log('tempo_live_rosin present: ' + ('tempo_live_rosin' in t));
  Logger.log('All keys: ' + Object.keys(t).join(', '));
}

function serverAssignUidToHashLot(hashLotId, item, strain, washDate) {
  const available = getNextAvailableUID();
  if (!available) {
    throw new Error("No available METRC UIDs. Please import new tags before creating a wash batch.");
  }

  const sheet = getTrackerSheet();
  const mfgDateObj = parseISODate(washDate);
  const row = available.rowIndex;
  const now = new Date();

  const rowData = new Array(20).fill('');
  rowData[CONFIG.COL.ITEM            - 3] = item;
  rowData[CONFIG.COL.CATEGORY        - 3] = 'Live Rosin';
  rowData[CONFIG.COL.ITEM_STRAIN     - 3] = strain || '';
  rowData[CONFIG.COL.BATCH_ID        - 3] = hashLotId;
  rowData[CONFIG.COL.MFG_DATE        - 3] = mfgDateObj;
  rowData[CONFIG.COL.UNIT_OF_MEASURE - 3] = 'g';
  rowData[CONFIG.COL.STATUS          - 3] = 'Ice Extraction';
  rowData[CONFIG.COL.CREATED_AT      - 3] = now;
  rowData[CONFIG.COL.LAST_UPDATED    - 3] = now;

  sheet.getRange(row, 3, 1, 20).setValues([rowData]);
  SpreadsheetApp.flush();
  bustCache();

  log("Wash batch UID assigned", { uid: available.uid, hashLotId, item });

  // UID folder in Drive — same as normal batch creation
  let uidFolderUrl = null;
  try {
    const coaFolder = getCOAArchiveFolder();
    if (coaFolder) {
      uidFolderUrl = getOrCreateUIDFolder(coaFolder, available.uid).getUrl();
    }
  } catch(e) {
    Logger.log('UID folder creation failed (non-fatal): ' + e.message);
  }

  // Col C → hyperlink to UID folder (parity with createBatch)
  try {
    if (uidFolderUrl) {
      const richText = SpreadsheetApp.newRichTextValue()
        .setText(item).setLinkUrl(uidFolderUrl).build();
      sheet.getRange(row, CONFIG.COL.ITEM).setRichTextValue(richText);
    }
  } catch(e) { Logger.log('Col C hyperlink failed (non-fatal): ' + e.message); }

  return { uid: available.uid, folderUrl: uidFolderUrl };
}

/**
 * ONE-TIME CLEANUP v2 — targets sheet-scoped duplicate named ranges,
 * the kind created when a tab is copied. Their getName() includes the
 * sheet qualifier, e.g.  'PUNCH Ice Extraction'!ROSIN_BATCH_ID
 * Healthy ranges have plain names (ROSIN_BATCH_ID) and are untouched.
 *
 * SAFETY: run with DRY_RUN = true first. It only logs what it WOULD
 * remove. Read the log; if the list looks right, flip to false and rerun.
 */
function purgeScopedNamedRanges() {
  const DRY_RUN = false;   // ← flip to false after reviewing the log

  const ss = SpreadsheetApp.openById(BATCH_RECORD_MASTER_ID);
  const all = ss.getNamedRanges();
  let hits = 0;

  all.forEach(function(nr) {
    const name = nr.getName();
    // The "!" only appears in sheet-scoped names — plain ranges can't
    // contain it, so this is a precise fingerprint, not a fuzzy match.
    if (name.indexOf('!') !== -1) {
      hits++;
      if (DRY_RUN) {
        Logger.log('WOULD REMOVE: ' + name);
      } else {
        Logger.log('Removing: ' + name);
        nr.remove();
      }
    }
  });

  Logger.log((DRY_RUN ? 'Dry run — ' : 'Done — ') + hits + ' scoped ranges of ' + all.length + ' total.');
}

/**
 * ONE-TIME SETUP — bulk-creates all Section 6 named ranges on the
 * PUNCH Ice Extraction tab of the BPR master template.
 * 18 step rows starting at row 48, 7 writable cells per row = 126 ranges.
 * Idempotent: setNamedRange() overwrites a same-named range instead of
 * duplicating, so re-running after a layout change just re-points them.
 */
function createWashSection6NamedRanges() {
  const ss    = SpreadsheetApp.openById(BATCH_RECORD_MASTER_ID);
  const sheet = ss.getSheetByName('PUNCH Ice Extraction');
  if (!sheet) { Logger.log('Tab "PUNCH Ice Extraction" not found'); return; }

  const START_ROW = 48;   // Section 6, step 1
  const STEP_COUNT = 18;  // consecutive rows 48–65

  // Column map — per DKing 7/11. Op 2 (H) and Target (K) deliberately
  // excluded: Op 2 is a manual field, Target is pre-filled template content.
  const COLS = {
    DATE:     'D',
    START:    'E',
    END:      'F',
    OP1:      'G',
    VERIFIED: 'I',
    VALUE:    'J',
    PASSFAIL: 'L',
  };

  let created = 0;
  for (let step = 1; step <= STEP_COUNT; step++) {
    const row = START_ROW + (step - 1);
    for (const key in COLS) {
      const name = 'WASH_S6_STEP' + step + '_' + key;
      ss.setNamedRange(name, sheet.getRange(COLS[key] + row));
      created++;
    }
  }
  Logger.log('Created/updated ' + created + ' WASH_S6 named ranges (steps 1-' + STEP_COUNT + ', rows ' + START_ROW + '-' + (START_ROW + STEP_COUNT - 1) + ')');
}

function createWashSection4NamedRanges() {
  const ss    = SpreadsheetApp.openById(BATCH_RECORD_MASTER_ID);
  const sheet = ss.getSheetByName('PUNCH Ice Extraction');
  // [VERIFY] equipment rows 1-6 sit on sheet rows 29-34, Checked By = col I,
  // Time = col J — confirm against the template before running
  const ROWS = { 1:29, 2:30, 3:31, 4:32, 5:33, 6:34 };
  const COLS = { CHECKEDBY:'I', TIME:'J' };
  let n = 0;
  for (const r in ROWS) {
    ss.setNamedRange('WASH_S4_ROW' + r + '_CHECKEDBY', sheet.getRange(COLS.CHECKEDBY + ROWS[r]));
    ss.setNamedRange('WASH_S4_ROW' + r + '_TIME',      sheet.getRange(COLS.TIME      + ROWS[r]));
    n += 2;
  }
  Logger.log('Created/updated ' + n + ' WASH_S4 named ranges');
}

function createWashSection5NamedRanges() {
  const ss    = SpreadsheetApp.openById(BATCH_RECORD_MASTER_ID);
  const sheet = ss.getSheetByName('PUNCH Ice Extraction');
  if (!sheet) { Logger.log('Tab not found'); return; }

  const START_ROW = 38;   // [VERIFY] sanitation row 1
  const ROW_COUNT = 7;    // 7 equipment/surface rows

  const COLS = {          // [VERIFY] every letter
    DATE:      'C',
    START:     'D',
    END:       'E',
    PPM:       'G',
    STRIPS:    'I',
    PASS:      'J',
    CLEANEDBY: 'K',
    DRYBEFORE: 'L',
  };

  let n = 0;
  for (let r = 1; r <= ROW_COUNT; r++) {
    const row = START_ROW + (r - 1);
    for (const key in COLS) {
      ss.setNamedRange('WASH_S5_ROW' + r + '_' + key, sheet.getRange(COLS[key] + row));
      n++;
    }
  }
  Logger.log('Created/updated ' + n + ' WASH_S5 named ranges (rows ' + START_ROW + '-' + (START_ROW + ROW_COUNT - 1) + ')');
}

// ── SECTION 8 — QUALITY CONTROL REVIEW ───────────────────────
// ⚠ [VERIFY] — I do NOT have confirmed row/column positions for
// Section 8. From the released PDF the columns are:
//   # | QC Step / Check | Result | QC Reviewer | Date & Time | Pass/Fail/N-A | Notes
// Find the sheet row of QC check #1 and the column letters for
// Result / QC Reviewer / Date & Time / Pass-Fail, set them below,
// then run.
function createWashSection8NamedRanges() {
  const ss    = SpreadsheetApp.openById(BATCH_RECORD_MASTER_ID);
  const sheet = ss.getSheetByName('PUNCH Ice Extraction');
  if (!sheet) { Logger.log('Tab not found'); return; }

  const START_ROW = 76;   // [VERIFY] sheet row of QC check #1
  const ROW_COUNT = 8;    // 8 QC review rows

  const COLS = {          // [VERIFY] every letter
    RESULT:   'G',
    REVIEWER: 'H',
    DATETIME: 'I',
    PASSFAIL: 'J',
  };

  let n = 0;
  for (let r = 1; r <= ROW_COUNT; r++) {
    const row = START_ROW + (r - 1);
    for (const key in COLS) {
      ss.setNamedRange('WASH_S8_ROW' + r + '_' + key, sheet.getRange(COLS[key] + row));
      n++;
    }
  }
  Logger.log('Created/updated ' + n + ' WASH_S8 named ranges (rows ' + START_ROW + '-' + (START_ROW + ROW_COUNT - 1) + ')');
}

function debugCheckStoredTemplates() {
  const props = PropertiesService.getScriptProperties();
  const a = props.getProperty("PRODUCT_TEMPLATES");
  const b = props.getProperty("punch_templates");
  Logger.log("PRODUCT_TEMPLATES exists: " + (a !== null) + " | length: " + (a ? a.length : 0));
  Logger.log("punch_templates exists: " + (b !== null) + " | length: " + (b ? b.length : 0));
}

function debugClearStoredTemplates() {
  const props = PropertiesService.getScriptProperties();
  props.deleteProperty("PRODUCT_TEMPLATES");
  props.deleteProperty("punch_templates");
  Logger.log("Cleared. getProductTemplates() will now fall back to CONFIG.DEFAULT_TEMPLATES.");
}

function debugDumpStoredTemplates() {
  const props = PropertiesService.getScriptProperties();
  const stored = props.getProperty("PRODUCT_TEMPLATES");
  if (!stored) { Logger.log("No PRODUCT_TEMPLATES property found."); return; }

  Logger.log("Total length: " + stored.length + " / 9216 byte limit");

  // Log in 1500-char chunks so nothing gets truncated
  for (let i = 0; i < stored.length; i += 1500) {
    Logger.log(stored.substring(i, i + 1500));
  }

  // Also log just the top-level keys, so you can eyeball what exists
  const parsed = JSON.parse(stored);
  Logger.log("Template keys currently stored: " + Object.keys(parsed).join(", "));
}

function migrateTemplateUpdates_2026_07_13() {
  const props = PropertiesService.getScriptProperties();
  const stored = props.getProperty("PRODUCT_TEMPLATES");
  if (!stored) { Logger.log("No PRODUCT_TEMPLATES found — aborting."); return; }

  const templates = JSON.parse(stored);

  // 1. Rosin AIO — preset → dynamic (custom strain name entry)
  templates.punch_rosin_aio = {
    brand: "Punch", label: "Rosin AIO Vape",
    category: "Vape Cartridge (weight - each)", uom: "Each",
    type: "dynamic", fields: ["strain"],
    pattern: "Punch - Rosin AIO Vape - {strain} (1g)",
    hint: "e.g. Banana Punch, Benzina, Cherry Paloma..."
  };

  // 2. Live Resin Diamonds — preset → dynamic
  //    NOTE: this drops "King Louie" and "Blue Dream" which were admin-added
  //    to the old preset list — fine, since strain is now free text anyway.
  templates.tempo_lr_diamonds = {
    brand: "Tempo", label: "Live Resin Diamonds",
    category: "Extract (weight - each)", uom: "Each",
    type: "dynamic", fields: ["strain"],
    pattern: "Tempo - Live Resin Diamonds - {strain} (1g)",
    hint: "e.g. Tangie Dream (Sativa), Super Glue (Indica)..."
  };

  // 3. Relabel 510 vapes for clarity (flavors untouched — preserves any admin edits)
  if (templates.punch_vapes) {
    templates.punch_vapes.label = "510 Distillate Vapes";
  }

  // 4. NEW — 2g Distillate AIO (duplicate of 510 list for now, per your call)
  templates.punch_2g_dist_vapes = {
    brand: "Punch", label: "2g Distillate AIO",
    category: "Vape Cartridge (weight - each)", uom: "Each",
    type: "preset", fields: ["flavor_select"],
    flavors: [
      "Ambrosia", "Blue Dream","Diablo OG","Dulce Fresa","Forbidden Fruit",
      "GDP", "Gelato", "Island Breeze", "King Louie XIII OG",
      "Papaya", "Platinum OG","Maui Wowie",
      "Mimosa","Northern Lights",
      "Original Jack", "Blue Z", "Rainbow Sherbert",
      "Super Sour Diesel","XJ-13",
      "Strawberry Cough","The Z", "Tropical Smoothie"
    ],
    pattern: "Punch - 2g Distillate AIO - {flavor} (2g)"
  };

  // ── Size guard — refuse to save if it would exceed the 9KB property limit ──
  const newJson = JSON.stringify(templates);
  Logger.log("New size: " + newJson.length + " / 9216 byte limit");

  if (newJson.length > 9216) {
    Logger.log("ABORTED — new size exceeds PropertiesService limit. Nothing was saved.");
    return;
  }

  props.setProperty("PRODUCT_TEMPLATES", newJson);
  Logger.log("Saved successfully. Keys now stored: " + Object.keys(templates).join(", "));
}


function verifyNormsBPRTabs() {
  const masterSS = SpreadsheetApp.openById(BATCH_RECORD_MASTER_ID);
  const existingTabs = masterSS.getSheets().map(function(s) { return s.getName(); });

  const templates = getProductTemplates(); // reads live PropertiesService data, not Config.gs
  const normsFlavors = (templates.dr_norms && templates.dr_norms.flavors) || [];

  Logger.log("── Dr. Norm's BPR Tab Verification ──");
  const missing = [];

  normsFlavors.forEach(function(flavor) {
    const itemName = "Dr. Norm's- 100mg " + flavor; // mirrors the actual naming pattern
    const tab = detectNormsTab(itemName);
    const exists = existingTabs.indexOf(tab) !== -1;
    if (!exists) missing.push(flavor + " → " + tab);
    Logger.log((exists ? "OK   " : "MISS ") + flavor + "  →  " + tab);
  });

  Logger.log("── Summary: " + missing.length + " of " + normsFlavors.length + " flavors point to a tab that doesn't exist ──");
  if (missing.length) Logger.log(missing.join("\n"));
}




