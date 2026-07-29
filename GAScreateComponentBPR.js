/**
 * GAS handler for BatchD "New Component Batch" → create a Google Sheet BPR +
 * Drive folder for a component lot, mirroring how batch/wash creation works.
 * ── PASTE INTO YOUR APPS SCRIPT PROJECT, then create a NEW deployment version. ──
 *
 * The Railway backend calls the webhook right after it creates the Postgres lot:
 *   { action:"createComponentBPR", lotCode, componentType, strain, isMixed,
 *     metrcUid, date, secret }
 * and stores the { sheetUrl, folderUrl } you return (sheetUrl on the lot,
 * folderUrl in type_data) so the lot detail page links to both.
 *
 * 1) Add this branch to doPost's action switch (same secret gate as the rest):
 *
 *      if (parsed.action === 'createComponentBPR') {
 *        if (parsed.secret !== GAS_SHARED_SECRET) return jsonOut({ success:false, error:'bad secret' });
 *        return jsonOut(serverCreateComponentBPR(parsed));
 *      }
 *
 * 2) Fill in the two config blocks below (folder id + per-type templates),
 *    then add the function.
 *
 * NOTE on the easy path: if you already have a working createWashBatchRecord()
 * that clones a wash template + makes a folder + embeds a QR, the ice_water_hash
 * case can just delegate to it — see the DELEGATE example inside.
 */

// ── CONFIG 1: where component folders live (a Shared Drive folder id) ────────
var COMPONENTS_PARENT_FOLDER_ID = 'PASTE_FOLDER_ID_HERE';

// ── CONFIG 2: componentType → BPR template. Use whichever you have:
//    - templateFileId : a standalone Google Sheet template to COPY into the
//      lot's folder (cleanest, recommended), OR
//    - templateTabName: a tab in your batch-records workbook to clone.
//    Types with no entry get a FOLDER ONLY (fine for received 3rd-party inputs
//    that just need a home for their COA/manifest).
var COMPONENT_TEMPLATES = {
  ice_water_hash:   { templateFileId: 'PASTE_WASH_BPR_TEMPLATE_SHEET_ID' },
  solventless_hash: { templateFileId: 'PASTE_SOLVENTLESS_TEMPLATE_SHEET_ID' },
  nano_isolate:     { templateFileId: 'PASTE_NANO_ISOLATE_TEMPLATE_SHEET_ID' },
  // distillate_3p / bho_badder_3p / shatter_3p: folder only (no entry) —
  // add a templateFileId here if you want an intake sheet for received items.
};

// Header cells to stamp on the created sheet (adjust to your template layout).
var COMPONENT_HEADER_CELLS = {
  lotCode:  'C7',   // where the lot code / batch id goes
  strain:   'C8',
  date:     'C9',
  qrCode:   'N34',  // top-left of the QR placeholder (matches standardized BPRs)
};

function serverCreateComponentBPR(p) {
  var lotCode = p.lotCode;
  if (!lotCode) return { success: false, error: 'no lotCode' };

  // ── DELEGATE example (uncomment if you have createWashBatchRecord) ──
  // if (p.componentType === 'ice_water_hash') {
  //   var w = createWashBatchRecord(lotCode, p.strain, p.isMixed, p.date);
  //   return { success: true, sheetUrl: w.sheetUrl, folderUrl: w.folderUrl };
  // }

  var parent = DriveApp.getFolderById(COMPONENTS_PARENT_FOLDER_ID);

  // 1) Folder for this lot (reuse if it already exists)
  var folder;
  var existing = parent.getFoldersByName(lotCode);
  folder = existing.hasNext() ? existing.next() : parent.createFolder(lotCode);
  var folderUrl = folder.getUrl();

  // 2) Sheet from the per-type template (folder-only if none mapped)
  var tpl = COMPONENT_TEMPLATES[p.componentType];
  var sheetUrl = '';
  if (tpl && tpl.templateFileId) {
    var copy = DriveApp.getFileById(tpl.templateFileId)
                       .makeCopy('BPR — ' + lotCode, folder);
    var ss = SpreadsheetApp.openById(copy.getId());
    var sheet = ss.getSheets()[0];

    // Stamp header cells (guarded — skip any that don't exist in your template)
    try { sheet.getRange(COMPONENT_HEADER_CELLS.lotCode).setValue(lotCode); } catch (e) {}
    try { sheet.getRange(COMPONENT_HEADER_CELLS.strain).setValue(p.isMixed ? 'MIXED' : (p.strain || '')); } catch (e) {}
    try { sheet.getRange(COMPONENT_HEADER_CELLS.date).setValue(p.date || ''); } catch (e) {}

    // QR → the BatchD lot detail page
    try {
      var link = 'https://batchd-bpr.netlify.app/components/' + encodeURIComponent(lotCode);
      var qrUrl = 'https://quickchart.io/qr?size=130&text=' + encodeURIComponent(link);
      var img = UrlFetchApp.fetch(qrUrl).getBlob();
      sheet.insertImage(img, columnToIndex_(COMPONENT_HEADER_CELLS.qrCode),
                             rowOf_(COMPONENT_HEADER_CELLS.qrCode));
    } catch (e) { /* QR is nice-to-have, never fatal */ }

    SpreadsheetApp.flush();
    sheetUrl = ss.getUrl();
  }

  return { success: true, sheetUrl: sheetUrl, folderUrl: folderUrl };
}

// Helpers: split an A1 ref like "N34" into a 1-based column index / row for
// insertImage(blob, column, row). Replace with your own if you have them.
function columnToIndex_(a1) {
  var letters = a1.match(/[A-Z]+/)[0];
  var idx = 0;
  for (var i = 0; i < letters.length; i++) idx = idx * 26 + (letters.charCodeAt(i) - 64);
  return idx;
}
function rowOf_(a1) { return Number(a1.match(/\d+/)[0]); }
