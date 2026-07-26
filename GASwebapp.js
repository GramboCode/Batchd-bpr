// ============================================================
// WebApp.gs — Punch Edibles & Extracts | Punch Tools
// ============================================================

function doGet(e) {
  // GAS sometimes passes params differently — check all possible locations
  var page = "index";
  
  try {
    if (e && e.parameter && e.parameter.page) {
      page = e.parameter.page;
    } else if (e && e.parameters && e.parameters.page) {
      page = e.parameters.page[0];
    } else if (e && e.queryString) {
      // Parse queryString manually as last resort
      var qs = e.queryString || "";
      var match = qs.match(/(?:^|&)page=([^&]*)/);
      if (match) page = decodeURIComponent(match[1]);
    }
  } catch(err) {
    page = "index";
  }

  Logger.log('queryString: ' + (e ? e.queryString : 'no e'));
  Logger.log('page resolved: ' + page);

  // Webhook ping
  if (e && e.parameter && e.parameter.webhook === "ping") {
    return ContentService
      .createTextOutput(JSON.stringify({ success: true, status: "Punch Tools active" }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  var pageMap = {
    "index":  "index",
    "batch":  "batch",
    "create": "create",
    "import": "import",
    "admin":  "admin",
    "wash":   "wash",
  };

  var template = pageMap[page] || "index";
  var output   = HtmlService.createHtmlOutputFromFile(template);

  if (page === "batch") {
    var uid = (e && e.parameter && e.parameter.uid) ? e.parameter.uid : "";
    var raw = output.getContent();
    var injected = uid ? raw.replaceAll("__BATCH_UID__", uid) : raw;
    output.setContent(injected);
  }
  Logger.log('serving template: ' + template);

  return output
    .setTitle("Punch Tools")
    .addMetaTag("viewport", "width=device-width, initial-scale=1")
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

// ── DASHBOARD ────────────────────────────────────────────────

function serverGetDashboard() {
  try {
    // ── Fast unassigned UID count (separate lightweight read) ──
    let unassignedCount = 0;
    try {
      const sheet   = getTrackerSheet();
      const lastRow = sheet.getLastRow();
      if (lastRow >= CONFIG.DATA_START_ROW) {
        const cols = sheet.getRange(
          CONFIG.DATA_START_ROW,
          CONFIG.COL.METRC_UID,
          lastRow - CONFIG.DATA_START_ROW + 1,
          CONFIG.COL.BATCH_ID - CONFIG.COL.METRC_UID + 1
        ).getValues();
        for (const row of cols) {
          const uid     = String(row[0] || '').trim();
          const batchID = String(row[CONFIG.COL.BATCH_ID - CONFIG.COL.METRC_UID] || '').trim();
          if (uid && !batchID) unassignedCount++;
        }
      }
    } catch(e) { log('Unassigned count error', e.message); }

    const allBatches = getAllBatchesCached();

    const stats = {
      inProduction:    0,
      needLabels:      0,
      readyForTesting: 0,
      awaitingResults: 0,
      failed:          0,
      unassignedUIDs:  unassignedCount,
    };

    const failedBatches  = [];
    const activeBatches  = [];
    const inactiveStatuses = [
      "passed but not avail in distru",
      "avail in distru/on menu",
      "compliance passed",
      "archived",
    ];

    for (const b of allBatches) {
      const s = (b.status || "").toLowerCase().trim();

      // Count stats
      if (["in production","ready for packaging","packaging complete",
           "submitted for rnd","passed rnd","remake"].includes(s)) {
        stats.inProduction++;
      } else if (["need labels","labels made"].includes(s)) {
        stats.needLabels++;
      } else if (s === "ready for testing") {
        stats.readyForTesting++;
      } else if (["submitted for compliance","delayed in testing",
                  "testing cancelled","compliance review"].includes(s)) {
        stats.awaitingResults++;
      } else if (s === "failed") {
        stats.failed++;
        failedBatches.push({ batchID: b.batchID, item: b.item, metrcUID: b.metrcUID });
      }

      // Only send active batches to browser
      if (!inactiveStatuses.includes(s)) {
        activeBatches.push(b);
      }
    }

    return {
      success:       true,
      batches:       activeBatches,
      stats:         stats,
      failedBatches: failedBatches,
      statuses:      CONFIG.STATUS_LIST,
      labs:          getActiveLabs(),
    };

  } catch(e) {
    log("serverGetDashboard error", e.message);
    return { success: false, error: e.message };
  }
}

function serverSearch(query, filters) {
  try {
    _validateString(query, "query", { required: false, maxLength: 100 });
    const batches = searchBatchesCached(query || "", filters || {});
    return { success: true, batches: batches, count: batches.length };
  } catch(e) {
    log("serverSearch error", e.message);
    return { success: false, error: e.message };
  }
}

function serverGetBatch(uid) {
  try {
    _validateString(uid, "uid", { required: true, maxLength: 50 });
    const batch = getBatchByUID(uid);
    if (!batch) return { success: false, error: "Batch not found: " + uid };
    return { success: true, batch: batch };
  } catch(e) {
    log("serverGetBatch error", e.message);
    return { success: false, error: e.message };
  }
}

function serverCreateBatch(data) {
  try {
    _validateString(data.item,     "item",     { required: true,  maxLength: 200 });
    _validateString(data.category, "category", { required: true,  maxLength: 100 });
    _validateString(data.batchID,  "batchID",  { required: true,  maxLength: 50  });
    _validateString(data.mfgDate,  "mfgDate",  { required: true,  maxLength: 20  });
    _validateString(data.uom,      "uom",      { required: false, maxLength: 20  });

    if (/[<>:"\\|?*\x00-\x1f]/.test(data.batchID)) {
      throw new Error('Batch ID contains invalid characters. Avoid: < > : " \\ | ? *');
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(data.mfgDate)) {
      throw new Error("Invalid date format. Expected YYYY-MM-DD.");
    }
    // Use getActiveLabs() so admin-managed labs are validated correctly
    const activeLabs = getActiveLabs();
    if (data.lab && !activeLabs.includes(data.lab)) {
      throw new Error("Invalid lab: " + data.lab);
    }

    const newBatch = createBatch(data);
    return { success: true, batch: newBatch };
  } catch(e) {
    log("serverCreateBatch error", e.message);
    return { success: false, error: e.message };
  }
}

function serverUpdateStatus(uid, status) {
  try {
    _validateString(uid,    "uid",    { required: true, maxLength: 50 });
    _validateString(status, "status", { required: true, maxLength: 100 });
    updateBatchStatus(uid, status);
    return { success: true };
  } catch(e) {
    log("serverUpdateStatus error", e.message);
    return { success: false, error: e.message };
  }
}

function serverRequestTesting(uid, testType, testDate) {
  try {
    _validateString(uid,      "uid",      { required: true, maxLength: 50 });
    _validateString(testType, "testType", { required: true, maxLength: 10 });
    _validateString(testDate, "testDate", { required: true, maxLength: 20 });

    if (!["RND", "FULL"].includes(testType)) {
      throw new Error("Invalid test type. Must be RND or FULL.");
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(testDate)) {
      throw new Error("Invalid date format. Expected YYYY-MM-DD.");
    }

    const updatedBatch = requestTesting(uid, testType, testDate);
    return { success: true, batch: updatedBatch };
  } catch(e) {
    log("serverRequestTesting error", e.message);
    return { success: false, error: e.message };
  }
}

function serverImportUIDs(rawText) {
  try {
    if (!rawText || !rawText.trim()) {
      throw new Error("No UIDs provided. Paste your METRC tags and try again.");
    }
    const uidList = rawText
      .split(/[\n\r,]+/)
      .map(s => s.trim())
      .filter(s => s.length);

    if (uidList.length === 0) throw new Error("No valid UIDs found in the pasted text.");
    if (uidList.length > 500) throw new Error("Maximum 500 UIDs per import.");

    const result = importUIDs(uidList);
    return { success: true, ...result };
  } catch(e) {
    log("serverImportUIDs error", e.message);
    return { success: false, error: e.message };
  }
}

function serverGetStats() {
  try {
    const batches = getAllBatches();
    const stats   = _buildStats(batches);
    return { success: true, stats: stats };
  } catch(e) {
    log("serverGetStats error", e.message);
    return { success: false, error: e.message };
  }
}

function serverGetLabs() {
  return { success: true, labs: getActiveLabs() };
}

function serverGetStatuses() {
  return {
    success: true,
    statuses: [
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
      "Compliance Passed",
      "Compliance Review",
      "Failed",
      "Passed BUT NOT Avail in Distru",
      "Avail in Distru/On Menu",
      "Archived",
    ]
  };
}

function serverGetNextUID() {
  try {
    const next = getNextAvailableUID();
    if (!next) return { success: true, uid: null, message: "No available UIDs" };
    return { success: true, uid: next.uid, rowIndex: next.rowIndex };
  } catch(e) {
    log("serverGetNextUID error", e.message);
    return { success: false, error: e.message };
  }
}

function serverUpdateRetailID(uid, value) {
  try {
    _validateString(uid, "uid", { required: true, maxLength: 50 });
    updateBatchField(uid, CONFIG.COL.RETAIL_ID_MADE, value === true);
    return { success: true };
  } catch(e) {
    log("serverUpdateRetailID error", e.message);
    return { success: false, error: e.message };
  }
}

function serverGetTemplates() {
  try {
    return {
      success:   true,
      templates: getProductTemplates(),
      labs:      getActiveLabs()
    };
  } catch(e) {
    log("serverGetTemplates error", e.message);
    return { success: false, error: e.message };
  }
}

// ── ADMIN ────────────────────────────────────────────────────

function _isAdmin() {
  try {
    const email = Session.getActiveUser().getEmail().toLowerCase().trim();
    return CONFIG.ADMINS.map(e => e.toLowerCase().trim()).includes(email);
  } catch(e) {
    return false;
  }
}

function serverGetAdminData() {
  if (!_isAdmin()) return { success: false, error: "Access denied. Admin only." };
  return {
    success:   true,
    templates: getProductTemplates(),
    labs:      getActiveLabs(),
    email:     Session.getActiveUser().getEmail()
  };
}

function serverSaveTemplates(templates) {
  if (!_isAdmin()) return { success: false, error: "Access denied." };
  try {
    if (typeof templates !== "object" || !templates) throw new Error("Invalid template data.");
    PropertiesService.getScriptProperties().setProperty("PRODUCT_TEMPLATES", JSON.stringify(templates));
    log("Templates saved by", Session.getActiveUser().getEmail());
    return { success: true, count: Object.keys(templates).length };
  } catch(e) {
    log("serverSaveTemplates error", e.message);
    return { success: false, error: e.message };
  }
}

function serverSaveLabs(labs) {
  if (!_isAdmin()) return { success: false, error: "Access denied." };
  try {
    if (!Array.isArray(labs)) throw new Error("Labs must be an array.");
    PropertiesService.getScriptProperties().setProperty("LABS", JSON.stringify(labs));
    log("Labs saved by", Session.getActiveUser().getEmail());
    return { success: true, labs: labs };
  } catch(e) {
    log("serverSaveLabs error", e.message);
    return { success: false, error: e.message };
  }
}

function serverAddFlavor(templateKey, flavor) {
  if (!_isAdmin()) return { success: false, error: "Access denied." };
  try {
    _validateString(templateKey, "templateKey", { required: true, maxLength: 50 });
    _validateString(flavor,      "flavor",      { required: true, maxLength: 200 });

    const templates = getProductTemplates();
    if (!templates[templateKey]) throw new Error("Template not found: " + templateKey);
    if (!templates[templateKey].flavors) throw new Error("This template does not have a flavor list.");

    const existing = templates[templateKey].flavors.map(f => f.toLowerCase());
    if (existing.includes(flavor.toLowerCase().trim())) {
      throw new Error("'" + flavor + "' already exists in this list.");
    }

    templates[templateKey].flavors.push(flavor.trim());
    PropertiesService.getScriptProperties().setProperty("PRODUCT_TEMPLATES", JSON.stringify(templates));
    return { success: true, flavors: templates[templateKey].flavors };
  } catch(e) {
    log("serverAddFlavor error", e.message);
    return { success: false, error: e.message };
  }
}

function serverRemoveFlavor(templateKey, flavorIndex) {
  if (!_isAdmin()) return { success: false, error: "Access denied." };
  try {
    const templates = getProductTemplates();
    if (!templates[templateKey] || !templates[templateKey].flavors) {
      throw new Error("Template or flavor list not found.");
    }
    const idx = parseInt(flavorIndex);
    if (isNaN(idx) || idx < 0 || idx >= templates[templateKey].flavors.length) {
      throw new Error("Invalid flavor index.");
    }
    templates[templateKey].flavors.splice(idx, 1);
    PropertiesService.getScriptProperties().setProperty("PRODUCT_TEMPLATES", JSON.stringify(templates));
    return { success: true, flavors: templates[templateKey].flavors };
  } catch(e) {
    log("serverRemoveFlavor error", e.message);
    return { success: false, error: e.message };
  }
}

function serverResetTemplates() {
  if (!_isAdmin()) return { success: false, error: "Access denied." };
  PropertiesService.getScriptProperties().deleteProperty("PRODUCT_TEMPLATES");
  log("Templates reset to defaults by", Session.getActiveUser().getEmail());
  return { success: true, templates: getProductTemplates() };
}

// ── PRIVATE HELPERS ──────────────────────────────────────────

function _buildStats(batches) {
  const assigned = batches.filter(b => b.isAssigned);
  return {
    totalBatches:    assigned.length,
    inProduction:    assigned.filter(b => b.status === CONFIG.STATUS.IN_PRODUCTION).length,
    readyForTesting: assigned.filter(b => b.status === CONFIG.STATUS.READY_FOR_TESTING).length,
    needLabels:      assigned.filter(b => b.status === CONFIG.STATUS.NEED_LABELS).length,
    inDistro:        assigned.filter(b => b.status === CONFIG.STATUS.AVAIL_IN_DISTRO).length,
    unassignedUIDs:  batches.filter(b => !b.isAssigned).length,
  };
}

function _validateString(value, fieldName, options) {
  const opts = options || {};
  if (opts.required && (!value || !value.toString().trim())) {
    throw new Error(fieldName + " is required.");
  }
  if (value && opts.maxLength && value.toString().length > opts.maxLength) {
    throw new Error(fieldName + " exceeds maximum length of " + opts.maxLength + " characters.");
  }
}

function serverUpdateSampleID(uid, sampleID, type) {
  try {
    _validateString(uid,      "uid",      { required: true, maxLength: 50 });
    _validateString(sampleID, "sampleID", { required: true, maxLength: 50 });

    const col = type === "COA"
      ? CONFIG.COL.LAB_SAMPLE_ID_COA
      : CONFIG.COL.LAB_SAMPLE_ID_RND;

    updateBatchField(uid, col, sampleID.trim().toUpperCase());
    return { success: true };
  } catch(e) {
    log("serverUpdateSampleID error", e.message);
    return { success: false, error: e.message };
  }
}

function serverPushToTestingOrder(uid, testType, submissionDate, sampleSize, rndType) {
  try {
    _validateString(uid,            "uid",            { required: true, maxLength: 50 });
    _validateString(testType,       "testType",       { required: true, maxLength: 15 });
    _validateString(submissionDate, "submissionDate", { required: true, maxLength: 20 });

    if (!["RND", "COMPLIANCE"].includes(testType)) {
      throw new Error("Invalid test type. Must be RND or COMPLIANCE.");
    }

    if (!/^\d{4}-\d{2}-\d{2}$/.test(submissionDate)) {
      throw new Error("Invalid date format. Expected YYYY-MM-DD.");
    }

    const result = pushToTestingOrder(
      uid,
      testType,
      submissionDate,
      sampleSize ? parseInt(sampleSize) : null,
      rndType || null
    );

    return result;

  } catch(e) {
    log("serverPushToTestingOrder error", e.message);
    return { success: false, error: e.message };
  }
}

/**
 * serverGetTestingOrderTabs()
 * Returns existing testing order tab names for the modal dropdown.
 */
function serverGetTestingOrderTabs() {
  try {
    const tabs = getTestingOrderTabs();
    return { success: true, tabs: tabs };
  } catch(e) {
    return { success: false, error: e.message };
  }
}

function doPost(e) {
  try {
    const payload = (e && e.postData && e.postData.contents) 
      ? e.postData.contents : "";
    const params = JSON.stringify((e && e.parameter) ? e.parameter : {});
    
    if (payload) {
      try {
        const parsed = JSON.parse(payload);

        // ── Shared-secret gate ──────────────────────────────
        // Every action below requires this. Scoped to only fire when
        // parsed.action exists, so third-party webhooks with a different
        // shape (Confident Cannabis, etc.) still fall through to the
        // email-forwarding handler below untouched — this only gates
        // OUR OWN Railway-originated actions.
        //
        // Set the matching value in THIS project's Script Properties
        // (Project Settings → Script Properties → GAS_SHARED_SECRET) —
        // separate storage from Railway's env var of the same name,
        // must be set to the identical value in both places.
        if (parsed.action) {
          const expectedSecret = PropertiesService.getScriptProperties().getProperty('GAS_SHARED_SECRET');
          if (!expectedSecret || parsed.secret !== expectedSecret) {
            log('doPost: rejected — missing or invalid shared secret', { action: parsed.action });
            return ContentService
              .createTextOutput(JSON.stringify({ success: false, error: 'Unauthorized' }))
              .setMimeType(ContentService.MimeType.JSON);
          }
        }

                // ── BPR status + PDF link write-back from Railway ────
        // Fired by ping_gas_webhook() after a BPR is finalized and its PDF
        // is on Drive. Sends { uid, bprStatus, pdfUrl } → writes BPR_STATUS
        // (col 36) + BPR_PDF_URL (col 37) in UID_TRACKER. (Was mistakenly
        // wired to createBatch(), which reads item/batchID/etc. Railway
        // never sends — so the write-back was silently no-op'ing.)
        if (parsed.action === "updateBPRStatus") {
          const result = serverUpdateBPRStatus(
            parsed.uid,
            parsed.bprStatus,
            parsed.pdfUrl || ''
          );
          return ContentService
            .createTextOutput(JSON.stringify(result))
            .setMimeType(ContentService.MimeType.JSON);
        }

                // ── Batch STATUS change from BatchD (Railway) ─────────
        // Routed through GAS on purpose so updateBatchStatus's side effects
        // (bustCache + syncUIDToDistroLog) still run — a direct backend sheet
        // write would skip them. try/catch so an invalid status / unknown UID
        // returns a JSON error instead of falling through to the email handler.
        if (parsed.action === "setBatchStatus") {
          try {
            const result = updateBatchStatus(parsed.uid, parsed.status);
            return ContentService
              .createTextOutput(JSON.stringify(result))
              .setMimeType(ContentService.MimeType.JSON);
          } catch (statusErr) {
            return ContentService
              .createTextOutput(JSON.stringify({ success: false, error: statusErr.message }))
              .setMimeType(ContentService.MimeType.JSON);
          }
        }
                // ── Push batch to testing order (from BatchD) ─────────
        // Delegates to serverPushToTestingOrder, which writes the testing
        // order sheet + Distro Log and returns { success, newStatus, tabName }.
        if (parsed.action === "pushToTestingOrder") {
          try {
            const result = serverPushToTestingOrder(
              parsed.uid,
              parsed.pushType,
              parsed.date,
              parsed.sampleSize || null,
              parsed.rndType
            );
            return ContentService
              .createTextOutput(JSON.stringify(result))
              .setMimeType(ContentService.MimeType.JSON);
          } catch (pushErr) {
            return ContentService
              .createTextOutput(JSON.stringify({ success: false, error: pushErr.message }))
              .setMimeType(ContentService.MimeType.JSON);
          }
        }

        // ── Remove testing submission (from BatchD) ───────────
        if (parsed.action === "removeTestingSubmission") {
          try {
            const result = serverRemoveTestingSubmission(parsed.uid);
            return ContentService
              .createTextOutput(JSON.stringify(result))
              .setMimeType(ContentService.MimeType.JSON);
          } catch (rmErr) {
            return ContentService
              .createTextOutput(JSON.stringify({ success: false, error: rmErr.message }))
              .setMimeType(ContentService.MimeType.JSON);
          }
        }


        // ── BPR field write-back from digital app ────────────
        if (parsed.action === 'writeBPRFields') {
          const result = serverWriteBPRFields(
            parsed.uid,
            parsed.fields || {}
          );
          return ContentService
            .createTextOutput(JSON.stringify(result))
            .setMimeType(ContentService.MimeType.JSON);
        }
        
        // ── BPR field write-back via direct cell map (successor to writeBPRFields) ──
        if (parsed.action === 'writeBPRFieldsByCellMap') {
          const result = serverWriteBPRFieldsByCellMap(
            parsed.uid,
            parsed.templateKey,
            parsed.fields || {}
          );
          return ContentService
            .createTextOutput(JSON.stringify(result))
            .setMimeType(ContentService.MimeType.JSON);
        }

        // ── Sanitation log write-back from digital app ────────
        if (parsed.action === 'writeSanitationLog') {
          const result = serverWriteSanitationLog(
            parsed.uid,
            parsed.entries || []
          );
          return ContentService
            .createTextOutput(JSON.stringify(result))
            .setMimeType(ContentService.MimeType.JSON);
        }

        // ── Wash BPR field write-back (named ranges) ──────────
        if (parsed.action === 'writeWashBPRFields') {
          const result = serverWriteWashBPRFields(parsed.sheetUrl, parsed.fields || {});
          return ContentService
            .createTextOutput(JSON.stringify(result))
            .setMimeType(ContentService.MimeType.JSON);
        }

        // ── Wash session log row append ───────────────────────
        if (parsed.action === 'appendWashSessionLog') {
          const result = serverAppendWashSessionLog(parsed.sheetUrl, parsed.block, parsed.row || {});
          return ContentService
            .createTextOutput(JSON.stringify(result))
            .setMimeType(ContentService.MimeType.JSON);
        }

      } catch(parseErr) {
        // Not JSON or unrecognized action — fall through to email handler
      }
    }

    // ── Confident Cannabis / other webhook email handler ──────
    log("doPost received", {
      payload: payload.substring(0, 500),
      params:  params,
      type:    (e && e.postData) ? e.postData.type : "none"
    });

    if (payload || params !== "{}") {
      GmailApp.sendEmail(
        "darrayl@punchedibles.com",
        "Confident Cannabis Webhook — Raw Payload",
        "Payload:\n\n" + payload + "\n\nParams:\n" + params
      );
    }

    return ContentService
      .createTextOutput(JSON.stringify({ success: true, received: true }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch(err) {
    log("doPost error", err.message);
    return ContentService
      .createTextOutput(JSON.stringify({ success: false, error: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// ─────────────────────────────────────────────────────────────
// serverUpdateBatchInfo(uid, updates)
//
// Updates editable batch fields in UID_TRACKER.
// Called by the Edit Batch Info form on batch detail page.
// ─────────────────────────────────────────────────────────────

function serverUpdateBatchInfo(uid, updates) {
  try {
    _validateString(uid, "uid", { required: true, maxLength: 50 });

    const batch = getBatchByUID(uid);
    if (!batch) throw new Error("Batch not found: " + uid);

    const sheet = getTrackerSheet();
    const row   = batch.rowIndex;
    const now   = new Date();

    // Write each updated field
    if (updates.item)       sheet.getRange(row, CONFIG.COL.ITEM).setValue(updates.item.trim());
    if (updates.batchID)    sheet.getRange(row, CONFIG.COL.BATCH_ID).setValue(updates.batchID.trim().toUpperCase());
    if (updates.category)   sheet.getRange(row, CONFIG.COL.CATEGORY).setValue(updates.category.trim());
    if (updates.itemStrain !== undefined) sheet.getRange(row, CONFIG.COL.ITEM_STRAIN).setValue((updates.itemStrain || "").trim());
    if (updates.quantity !== undefined)   sheet.getRange(row, CONFIG.COL.QUANTITY).setValue(updates.quantity || "");
    if (updates.stickeredQty !== undefined) sheet.getRange(row, CONFIG.COL.TARGET_QTY).setValue(updates.stickeredQty || "");
    if (updates.uom)        sheet.getRange(row, CONFIG.COL.UNIT_OF_MEASURE).setValue(updates.uom.trim());
    if (updates.lab !== undefined)        sheet.getRange(row, CONFIG.COL.LAB).setValue(updates.lab || "");

    // Parse and write mfg date if provided
    if (updates.mfgDate) {
      const dateObj = parseISODate(updates.mfgDate);
      if (dateObj) sheet.getRange(row, CONFIG.COL.MFG_DATE).setValue(dateObj);
    }

    // Stamp last updated
    sheet.getRange(row, CONFIG.COL.LAST_UPDATED).setValue(now);

    bustCache();
    log("Batch info updated", { uid, updates });

    // Return fresh batch data
    const updated = getBatchByUID(uid);
    return { success: true, batch: updated };

  } catch(e) {
    log("serverUpdateBatchInfo error", e.message);
    return { success: false, error: e.message };
  }
}


// ─────────────────────────────────────────────────────────────
// serverRemoveTestingSubmission(uid)
//
// Removes a batch from the testing order sheet and reverts
// its status back to "In Production".
//
// Looks for the batch in any testing order tab by METRC UID.
// Removes the matching row from that tab.
// Also removes from Distro Log if present.
// ─────────────────────────────────────────────────────────────

function serverRemoveTestingSubmission(uid) {
  try {
    _validateString(uid, "uid", { required: true, maxLength: 50 });

    const batch = getBatchByUID(uid);
    if (!batch) throw new Error("Batch not found: " + uid);

    // Remove from testing order sheet
    const removedFrom = _removeFromTestingOrderSheet(uid);

    // Remove from distro log
    _removeFromDistroLog(uid);

    // Revert status to In Production
    const sheet = getTrackerSheet();
    sheet.getRange(batch.rowIndex, CONFIG.COL.STATUS).setValue(CONFIG.STATUS.IN_PRODUCTION);
    sheet.getRange(batch.rowIndex, CONFIG.COL.TEST_DATE).setValue("");
    sheet.getRange(batch.rowIndex, CONFIG.COL.LAST_UPDATED).setValue(new Date());

    bustCache();
    log("Testing submission removed", { uid, removedFrom });

    return {
      success:     true,
      removedFrom: removedFrom,
      newStatus:   CONFIG.STATUS.IN_PRODUCTION,
    };

  } catch(e) {
    log("serverRemoveTestingSubmission error", e.message);
    return { success: false, error: e.message };
  }
}


// ─────────────────────────────────────────────────────────────
// _removeFromTestingOrderSheet(uid)
//
// Scans all tabs in the testing order sheet for the METRC UID.
// Deletes the matching row and returns the tab name.
// ─────────────────────────────────────────────────────────────

function _removeFromTestingOrderSheet(uid) {
  try {
    const ss    = SpreadsheetApp.openById("1MtLBI21V9qvYHFTFznbWSfKZ5SMYSI0PounMaA4mwxg");
    const sheets = ss.getSheets();

    for (const sheet of sheets) {
      const name = sheet.getName();
      if (name === "LabName M/DD/YYYY") continue;

      const lastRow = sheet.getLastRow();
      if (lastRow < 9) continue;

      const numRows = lastRow - 9 + 1;
      const uidCol  = sheet.getRange(9, 6, numRows, 1).getValues(); // col F = METRC UID

      for (let i = 0; i < uidCol.length; i++) {
        if (normalize(String(uidCol[i][0])) === normalize(uid)) {
          sheet.deleteRow(9 + i);
          log("Removed from testing order tab", { tab: name, uid });
          return name;
        }
      }
    }

    log("UID not found in any testing order tab", uid);
    return null;

  } catch(e) {
    log("_removeFromTestingOrderSheet error", e.message);
    return null;
  }
}


// ─────────────────────────────────────────────────────────────
// _removeFromDistroLog(uid)
//
// Removes matching row from Distro Testing Log "Full List" tab.
// Matches by METRC UID in col C.
// ─────────────────────────────────────────────────────────────

function _removeFromDistroLog(uid) {
  try {
    const ss    = SpreadsheetApp.openById("1Y6k_do81N6gNEDEuRxcPj7WH7OmOvyybIEo4fY2iTTg");
    const sheet = ss.getSheetByName("Full List");
    if (!sheet) return;

    const lastRow = sheet.getLastRow();
    if (lastRow < 7) return;

    const numRows = lastRow - 7 + 1;
    const uidCol  = sheet.getRange(7, 3, numRows, 1).getValues(); // col C = METRC UID

    // Scan from bottom up so row deletion doesn't affect indices
    for (let i = uidCol.length - 1; i >= 0; i--) {
      if (normalize(String(uidCol[i][0])) === normalize(uid)) {
        sheet.deleteRow(7 + i);
        log("Removed from distro log", uid);
      }
    }

  } catch(e) {
    log("_removeFromDistroLog error", e.message);
  }
}
function serverUpdateLab(uid, lab) {
  try {
    _validateString(uid, "uid", { required: true, maxLength: 50 });
    _validateString(lab, "lab", { required: true, maxLength: 50 });

    const activeLabs = getActiveLabs();
    if (!activeLabs.includes(lab)) {
      throw new Error("Invalid lab: " + lab);
    }

    updateBatchField(uid, CONFIG.COL.LAB, lab);
    return { success: true };
  } catch(e) {
    log("serverUpdateLab error", e.message);
    return { success: false, error: e.message };
  }
}

function serverCheckBatchID(batchID) {
  try {
    if (!batchID || batchID.length < 3) return { available: null, assignedTo: null, suggestion: null };

    const sheet   = getTrackerSheet();
    const lastRow = sheet.getLastRow();
    if (lastRow < CONFIG.DATA_START_ROW) return { available: true, assignedTo: null, suggestion: null };

    const numRows = lastRow - CONFIG.DATA_START_ROW + 1;
    const data    = sheet.getRange(CONFIG.DATA_START_ROW, CONFIG.COL.BATCH_ID, numRows, 2).getValues();
    // cols: [0]=BATCH_ID, [1]=ITEM

    const normalizedInput = batchID.trim().toUpperCase();
    let assignedTo = null;

    // Check if this exact batch ID exists
    for (var i = 0; i < data.length; i++) {
      var rowBatchID = String(data[i][0] || "").trim().toUpperCase();
      if (rowBatchID === normalizedInput) {
        assignedTo = String(data[i][1] || "Unknown item").trim();
        break;
      }
    }

    if (!assignedTo) return { available: true, assignedTo: null, suggestion: null };

    // Build a set of all existing batch IDs for suggestion lookup
    var allBatchIDs = {};
    data.forEach(function(row) {
      var id = String(row[0] || "").trim().toUpperCase();
      if (id) allBatchIDs[id] = true;
    });

    // Suggest next: strip trailing digits, increment
    var suggestion = getNextBatchID(normalizedInput, allBatchIDs);

    return { available: false, assignedTo: assignedTo, suggestion: suggestion };

  } catch(e) {
    log("serverCheckBatchID error", e.message);
    return { available: null, assignedTo: null, suggestion: null };
  }
}

function getNextBatchID(batchID, existingIDs) {
  // Split into prefix + numeric suffix
  // e.g. "TCAVSTRBTZ005" → prefix="TCAVSTRBTZ", num="005", pad=3
  var match = batchID.match(/^(.*?)(\d+)$/);
  if (!match) return null;

  var prefix  = match[1];
  var numStr  = match[2];
  var padLen  = numStr.length;
  var num     = parseInt(numStr, 10);

  // Increment until we find one that doesn't exist
  for (var i = 0; i < 50; i++) {
    num++;
    var candidate = prefix + String(num).padStart(padLen, '0');
    if (!existingIDs[candidate]) return candidate;
  }
  return null;
}

function serverSearchBatchPrefix(prefix) {
  try {
    if (!prefix || prefix.length < 3) return { matches: [] };

    const sheet   = getTrackerSheet();
    const lastRow = sheet.getLastRow();
    if (lastRow < CONFIG.DATA_START_ROW) return { matches: [] };

    const numRows = lastRow - CONFIG.DATA_START_ROW + 1;
    const data    = sheet.getRange(
      CONFIG.DATA_START_ROW, 1, numRows,
      Math.max(CONFIG.COL.STATUS, CONFIG.COL.BATCH_ID, CONFIG.COL.ITEM, CONFIG.COL.CREATED_AT)
    ).getValues();

    const normalizedPrefix = prefix.trim().toUpperCase();

    // Collect all batch IDs matching prefix
    // Group by prefix (everything except trailing digits)
    var prefixGroups = {}; // prefixKey → { latestBatchID, item, status, num }

    data.forEach(function(row) {
      var batchID = String(row[CONFIG.COL.BATCH_ID - 1] || '').trim().toUpperCase();
      var item    = String(row[CONFIG.COL.ITEM   - 1] || '').trim();
      var status  = String(row[CONFIG.COL.STATUS - 1] || '').trim();

      if (!batchID || !batchID.startsWith(normalizedPrefix)) return;

      // Split into alpha prefix + numeric suffix
      var match = batchID.match(/^(.*?)(\d+)$/);
      if (!match) return;

      var alphaPrefix = match[1];
      var num         = parseInt(match[2], 10);

      if (!prefixGroups[alphaPrefix] || num > prefixGroups[alphaPrefix].num) {
        prefixGroups[alphaPrefix] = {
          latestBatchID: batchID,
          alphaPrefix:   alphaPrefix,
          item:          item,
          status:        status,
          num:           num,
        };
      }
    });

    // Build suggestions — next ID for each prefix group
    var allBatchIDs = {};
    data.forEach(function(row) {
      var id = String(row[CONFIG.COL.BATCH_ID - 1] || '').trim().toUpperCase();
      if (id) allBatchIDs[id] = true;
    });

    var matches = Object.values(prefixGroups).map(function(g) {
      return {
        latestBatchID: g.latestBatchID,
        alphaPrefix:   g.alphaPrefix,
        item:          g.item,
        status:        g.status,
        nextBatchID:   getNextBatchID(g.latestBatchID, allBatchIDs),
      };
    });

    // Sort by alphaPrefix alphabetically
    matches.sort(function(a, b) { return a.alphaPrefix.localeCompare(b.alphaPrefix); });

    // Cap at 8 results
    return { matches: matches.slice(0, 8) };

  } catch(e) {
    log("serverSearchBatchPrefix error", e.message);
    return { matches: [] };
  }
}

function serverUpdateBatchField(uid, field, value) {
  try {
    const sheet = getTrackerSheet();
    const lastRow = sheet.getLastRow();
    const data = sheet.getRange(
      CONFIG.DATA_START_ROW, CONFIG.COL.METRC_UID,
      lastRow - CONFIG.DATA_START_ROW + 1, 1
    ).getValues();

    for (let i = 0; i < data.length; i++) {
      if (normalize(String(data[i][0])) === normalize(uid)) {
        const row = CONFIG.DATA_START_ROW + i;
        if (field === 'quantity') {
          sheet.getRange(row, CONFIG.COL.QUANTITY).setValue(parseInt(value));
        } else if (field === 'mfgDate') {
          const parts = value.split('-');
          const date = new Date(parseInt(parts[0]), parseInt(parts[1])-1, parseInt(parts[2]));
          sheet.getRange(row, CONFIG.COL.MFG_DATE).setValue(date);
        }
        sheet.getRange(row, CONFIG.COL.LAST_UPDATED).setValue(new Date());
        invalidateBatchCache();
        return { success: true };
      }
    }
    return { success: false, error: 'UID not found' };
  } catch(e) {
    return { success: false, error: e.message };
  }
}

function invalidateBatchCache() {
  CacheService.getScriptCache().remove('punch_all_batches');
}

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

      const BPR_APP_URL = "https://batchd-bpr.netlify.app";
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
