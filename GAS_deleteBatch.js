/**
 * GAS handler for BatchD admin "Delete Batch" (full removal).
 * ── PASTE THIS INTO YOUR APPS SCRIPT PROJECT, then create a NEW deployment
 *    version (Deploy → Manage deployments → Edit → New version). ──
 *
 * The Railway backend calls the webhook with { action: "deleteBatch", uid, secret }.
 * `uid` is the batch's METRC UID (UID_TRACKER column B / col 2), matching how
 * the BatchD dashboard routes to a batch.
 *
 * 1) Add this branch inside doPost's action switch (same secret gate as the
 *    other OUR-OWN actions):
 *
 *      if (parsed.action === 'deleteBatch') {
 *        if (parsed.secret !== GAS_SHARED_SECRET) return jsonOut({ success:false, error:'bad secret' });
 *        return jsonOut(serverDeleteBatch(parsed.uid));
 *      }
 *
 *    (jsonOut = your existing ContentService JSON helper. If you don't have one:
 *      function jsonOut(o){ return ContentService.createTextOutput(JSON.stringify(o))
 *        .setMimeType(ContentService.MimeType.JSON); } )
 *
 * 2) Add the function below.
 */
function serverDeleteBatch(uid) {
  if (!uid) return { success: false, error: 'no uid provided' };
  var target = String(uid).trim().toLowerCase();

  var ss = SpreadsheetApp.getActiveSpreadsheet();      // the UID_TRACKER file
  var sheet = ss.getSheetByName('UID_TRACKER') || ss.getSheets()[0];
  var data = sheet.getDataRange().getValues();

  var METRC_UID_COL = 2;   // col B
  var BATCH_ID_COL  = 6;   // col F  (fallback match)
  var SHEET_URL_COL = 15;  // col O  — BATCH_SHEET_URL (#gid= points to product tab)

  // Find the row (1-indexed for the sheet). Skip the header row (i=0).
  var rowNum = -1, sheetUrl = '';
  for (var i = 1; i < data.length; i++) {
    var metrc = String(data[i][METRC_UID_COL - 1] || '').trim().toLowerCase();
    var batch = String(data[i][BATCH_ID_COL  - 1] || '').trim().toLowerCase();
    if (metrc === target || batch === target) {
      rowNum   = i + 1;
      sheetUrl = String(data[i][SHEET_URL_COL - 1] || '');
      break;
    }
  }
  if (rowNum === -1) return { success: false, error: 'batch not found in UID_TRACKER: ' + uid };

  // Best-effort: delete the product tab this batch's URL points to (#gid=NNN),
  // before removing the tracker row. Wrapped so a tab hiccup never blocks the row.
  try {
    var m = sheetUrl.match(/[#&]gid=(\d+)/);
    if (m) {
      var gid = Number(m[1]);
      var tabs = ss.getSheets();
      for (var t = 0; t < tabs.length; t++) {
        if (tabs[t].getSheetId() === gid && tabs.length > 1) { ss.deleteSheet(tabs[t]); break; }
      }
    }
  } catch (e) { /* non-fatal — row removal still proceeds */ }

  // Remove the tracker row.
  sheet.deleteRow(rowNum);
  SpreadsheetApp.flush();

  // Optional: also trash the batch's Drive folder (keyed by METRC UID). Uncomment
  // if you want the folder gone too — leaves it in Drive Trash (recoverable 30 days).
  // try {
  //   var folders = DriveApp.getFoldersByName(uid);
  //   while (folders.hasNext()) folders.next().setTrashed(true);
  // } catch (e) {}

  return { success: true, deletedRow: rowNum, uid: uid };
}
