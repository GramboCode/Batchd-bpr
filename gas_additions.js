// ══════════════════════════════════════════════════════════════════════════
// FILE 1: Add to AConfig.gs — new column + BPR Railway URL
// ══════════════════════════════════════════════════════════════════════════

// Add to CONFIG.COL (inside the existing COL object):
//   STICKERED_QTY: 14,   // N  ← already exists, renamed from RND_PDF
//   BPR_STATUS:    36,   // AJ ← NEW

// Add as a new top-level constant:
// const BPR_APP_URL = "https://your-railway-bpr-app.railway.app";
// Replace with your actual Railway deployment URL once deployed.


// ══════════════════════════════════════════════════════════════════════════
// FILE 2: Add to your main GAS server file (wherever serverGetBatch lives)
// ══════════════════════════════════════════════════════════════════════════

/**
 * Returns the current BPR status for a batch from the UID_TRACKER.
 * Called by the batch detail page on load.
 */
function serverGetBPRStatus(uid) {
  try {
    const ss    = SpreadsheetApp.openById(CONFIG.TRACKER_SS_ID);
    const sheet = ss.getSheetByName(CONFIG.TRACKER_TAB);
    const lastRow = sheet.getLastRow();

    for (let r = CONFIG.DATA_START_ROW; r <= lastRow; r++) {
      const rowUID = String(sheet.getRange(r, CONFIG.COL.METRC_UID).getValue()).trim();
      if (rowUID !== uid) continue;
      const bprStatus = String(sheet.getRange(r, 36).getValue() || "").trim(); // col AJ
      return { success: true, bprStatus: bprStatus || "not_started" };
    }
    return { success: false, error: "UID not found" };
  } catch(e) {
    return { success: false, error: e.message };
  }
}

/**
 * Updates BPR_STATUS in UID_TRACKER col AJ.
 * Called by the Railway BPR webhook on completion.
 */
function serverUpdateBPRStatus(uid, bprStatus, pdfUrl) {
  try {
    const ss    = SpreadsheetApp.openById(CONFIG.TRACKER_SS_ID);
    const sheet = ss.getSheetByName(CONFIG.TRACKER_TAB);
    const lastRow = sheet.getLastRow();

    for (let r = CONFIG.DATA_START_ROW; r <= lastRow; r++) {
      const rowUID = String(sheet.getRange(r, CONFIG.COL.METRC_UID).getValue()).trim();
      if (rowUID !== uid) continue;
      sheet.getRange(r, 36).setValue(bprStatus);          // col AJ: BPR_STATUS
      if (pdfUrl) sheet.getRange(r, 37).setValue(pdfUrl); // col AK: BPR_PDF_URL (optional)
      sheet.getRange(r, CONFIG.COL.LAST_UPDATED).setValue(new Date());
      return { success: true };
    }
    return { success: false, error: "UID not found" };
  } catch(e) {
    return { success: false, error: e.message };
  }
}

/**
 * doPost handler — receives webhook from Railway BPR app.
 * Add this to your main GAS file (or create a doPost.gs).
 * The web app deployment must be set to "Execute as: Me" and
 * "Who has access: Anyone" for Railway to reach it.
 */
function doPost(e) {
  try {
    const payload = JSON.parse(e.postData.contents);

    if (payload.action === "updateBPRStatus") {
      const result = serverUpdateBPRStatus(
        payload.uid,
        payload.bprStatus,
        payload.pdfUrl || null
      );
      return ContentService
        .createTextOutput(JSON.stringify(result))
        .setMimeType(ContentService.MimeType.JSON);
    }

    return ContentService
      .createTextOutput(JSON.stringify({ success: false, error: "Unknown action" }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch(err) {
    return ContentService
      .createTextOutput(JSON.stringify({ success: false, error: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}


// ══════════════════════════════════════════════════════════════════════════
// FILE 3: batch.html additions — paste into the existing file
// ══════════════════════════════════════════════════════════════════════════
//
// STEP A — Add to the Label card in batch.html (right-col)
// Find the existing Label card div and add this action button:
//
// <button class="action-btn" id="openBPRBtn" onclick="openBPR()" style="display:none;">
//   <span class="action-title" style="color:#1A56DB;">📋 Open Batch Production Record</span>
//   <span class="action-desc" id="bprStatusText">Start or continue the digital BPR for this batch</span>
// </button>
//
// STEP B — Add these JS functions to the <script> block in batch.html:

const OPEN_BPR_JS = `
  // ── BPR Integration ──────────────────────────────────────────────────
  // Set this to your Railway BPR app URL:
  var BPR_APP_URL = 'https://your-railway-bpr-app.railway.app';

  function openBPR() {
    if (!batch) return;
    var params = new URLSearchParams({
      uid:         batch.metrcUID,
      product:     batch.item || '',
      batchId:     batch.batchID || '',
      mfgDate:     batch.mfgDate || '',
      category:    batch.category || '',
      returnUrl:   window.location.href,
    });
    window.open(BPR_APP_URL + '/bpr?' + params.toString(), '_blank');
  }

  function loadBPRStatus(uid) {
    google.script.run
      .withSuccessHandler(function(result) {
        if (!result.success) return;
        renderBPRStatus(result.bprStatus);
      })
      .serverGetBPRStatus(uid);
  }

  function renderBPRStatus(status) {
    var btn  = document.getElementById('openBPRBtn');
    var desc = document.getElementById('bprStatusText');
    if (!btn || !desc) return;

    btn.style.display = 'flex';

    if (status === 'completed') {
      btn.style.borderColor = 'var(--green)';
      btn.style.background  = 'var(--green-bg)';
      btn.querySelector('.action-title').style.color = 'var(--green)';
      desc.textContent = '✓ BPR Complete — click to view';
    } else if (status === 'in_progress') {
      btn.style.borderColor = 'var(--punch-blue)';
      btn.style.background  = 'var(--blue-bg)';
      desc.textContent = '▶ BPR in progress — click to continue';
    } else {
      btn.style.borderColor = 'var(--punch-blue)';
      btn.style.background  = 'var(--blue-bg)';
      desc.textContent = 'Start the digital Batch Production Record';
    }
  }

  // Call loadBPRStatus at the end of onBatchLoaded:
  // Add this line at the end of your onBatchLoaded function:
  //   if (batch && batch.metrcUID) loadBPRStatus(batch.metrcUID);
`;

// ══════════════════════════════════════════════════════════════════════════
// FILE 4: QR Code generation utility
// Add this GAS function to generate a printable QR code link for any batch
// ══════════════════════════════════════════════════════════════════════════

/**
 * Generates a BPR QR code URL for a batch.
 * The QR code encodes the Railway BPR URL with the batch context pre-filled.
 * Use a QR code generator (e.g., qrserver.com) to render it.
 *
 * Usage: call from a sidebar or add a "Generate QR" button to batch detail.
 */
function serverGetBPRQRCode(uid) {
  try {
    const ss    = SpreadsheetApp.openById(CONFIG.TRACKER_SS_ID);
    const sheet = ss.getSheetByName(CONFIG.TRACKER_TAB);
    const lastRow = sheet.getLastRow();

    for (let r = CONFIG.DATA_START_ROW; r <= lastRow; r++) {
      const rowUID = String(sheet.getRange(r, CONFIG.COL.METRC_UID).getValue()).trim();
      if (rowUID !== uid) continue;

      const item    = String(sheet.getRange(r, CONFIG.COL.ITEM).getValue() || "").trim();
      const batchID = String(sheet.getRange(r, CONFIG.COL.BATCH_ID).getValue() || "").trim();
      const mfgDate = sheet.getRange(r, CONFIG.COL.MFG_DATE).getValue();
      const category = String(sheet.getRange(r, CONFIG.COL.CATEGORY).getValue() || "").trim();

      const mfgDateStr = mfgDate
        ? Utilities.formatDate(new Date(mfgDate), Session.getScriptTimeZone(), "yyyy-MM-dd")
        : "";

      const BPR_APP_URL = "https://your-railway-bpr-app.railway.app"; // update this
      const params = {
        uid, product: item, batchId: batchID, mfgDate: mfgDateStr, category
      };
      const bprUrl = BPR_APP_URL + "/bpr?" + Object.entries(params)
        .map(([k,v]) => encodeURIComponent(k) + "=" + encodeURIComponent(v))
        .join("&");

      // Use qrserver.com API to generate QR code image URL
      const qrImageUrl = "https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=" +
        encodeURIComponent(bprUrl);

      return {
        success: true,
        bprUrl,
        qrImageUrl,
        item, batchID, uid
      };
    }
    return { success: false, error: "UID not found" };
  } catch(e) {
    return { success: false, error: e.message };
  }
}

/**
 * Shows a sidebar with the BPR QR code for the selected/current batch.
 * Wire this to a menu item or button in the sheet.
 */
function showBPRQRSidebar() {
  // Get currently viewed UID from selection or prompt
  const ui     = SpreadsheetApp.getUi();
  const sheet  = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("UID");
  const row    = SpreadsheetApp.getActiveRange().getRow();

  if (row < CONFIG.DATA_START_ROW) {
    ui.alert("Select a batch row first.");
    return;
  }

  const uid = String(sheet.getRange(row, CONFIG.COL.METRC_UID).getValue()).trim();
  if (!uid) { ui.alert("No METRC UID in this row."); return; }

  const result = serverGetBPRQRCode(uid);
  if (!result.success) { ui.alert("Error: " + result.error); return; }

  const html = HtmlService.createHtmlOutput(`
    <div style="font-family: Arial, sans-serif; padding: 16px; text-align: center;">
      <div style="font-size: 0.7rem; font-weight: bold; text-transform: uppercase;
                  letter-spacing: 0.1em; color: #888; margin-bottom: 4px;">
        BATCH PRODUCTION RECORD
      </div>
      <div style="font-size: 1rem; font-weight: 800; color: #0F1117; margin-bottom: 2px;">
        ${result.item}
      </div>
      <div style="font-size: 0.75rem; color: #8890A8; font-family: monospace; margin-bottom: 14px;">
        ${result.batchID}
      </div>
      <img src="${result.qrImageUrl}" width="180" height="180"
           style="border: 1px solid #E2E6EF; border-radius: 8px; padding: 8px;" />
      <div style="font-size: 0.72rem; color: #8890A8; margin-top: 10px; word-break: break-all;">
        ${result.uid}
      </div>
      <div style="margin-top: 14px;">
        <a href="${result.bprUrl}" target="_blank"
           style="display: inline-block; padding: 9px 18px; background: #E8192C; color: white;
                  border-radius: 6px; font-size: 0.82rem; font-weight: 700; text-decoration: none;
                  text-transform: uppercase; letter-spacing: 0.05em;">
          Open BPR ↗
        </a>
      </div>
      <p style="font-size: 0.68rem; color: #aaa; margin-top: 12px; line-height: 1.5;">
        Scan with a phone camera or share the link to open the digital batch record.
      </p>
    </div>
  `).setTitle("BPR QR Code").setWidth(260);

  SpreadsheetApp.getUi().showSidebar(html);
}
