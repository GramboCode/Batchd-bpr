// ============================================================
// LabScraper.gs — Punch Edibles & Extracts | Punch Tools
// ============================================================
// Automated lab results pipeline.
//
// Runs on a time-based trigger every 30 minutes.
// Processes emails from two labs:
//
//   TagLeaf / Infinite Chemical:
//     From: lab.infinitecal@tagleaf.com
//     Parses: product name, sample ID, pass/fail, results URL
//     Matches: by sample ID → UID_TRACKER col Q or R
//
//   Confident Cannabis / Encore:
//     From: team@confidentcannabis.com
//     Parses: order number only (no product details in email)
//     Action: sends alert to team to pull results manually
//             until webhook is configured
//
// After processing, emails are labeled "Punch/Processed"
// so they are never processed twice.
//
// Setup:
//   1. Run installLabScraperTrigger() once from Apps Script
//   2. Run createGmailLabels() once to create the Gmail labels
//   3. Deploy web app with the updated doPost() handler
//      for Confident Cannabis webhook (WebApp.gs)
// ============================================================


// ─────────────────────────────────────────────────────────────
// CONFIGURATION
// ─────────────────────────────────────────────────────────────

const SCRAPER_CONFIG = {

  // Gmail label applied to emails after processing
  // Prevents double-processing
  PROCESSED_LABEL: "Punch/Processed",
  PENDING_LABEL:   "Punch/Pending",

  // Lab email senders
  TAGLEAF_SENDER:  "lab.infinitecal@tagleaf.com",
  ENCORE_SENDER:   "team@confidentcannabis.com",

  // How many emails to process per run (safety limit)
  MAX_PER_RUN: 20,

  // Notification recipients — all departments for now
  // Future: split by event type per department
  NOTIFY_ALL: [
    
    "darrayl@punchedibles.com",
  ],

  // Status to set when R&D passes
  STATUS_RND_PASSED:  "Passed RND",
  // Status to set when compliance passes
  STATUS_COA_PASSED:  "Passed BUT NOT Avail in Distru",
  // Status to set when anything fails
  STATUS_FAILED:      "Delayed in Testing",
};


// ─────────────────────────────────────────────────────────────
// processLabEmails()
//
// Main entry point — called by the time-based trigger.
// Searches Gmail for unprocessed lab result emails
// and routes them to the correct parser.
// ─────────────────────────────────────────────────────────────

function processLabEmails() {
  log("LabScraper: starting run");

  try {
    _ensureLabels();

    const processedLabel = GmailApp.getUserLabelByName(SCRAPER_CONFIG.PROCESSED_LABEL);

    let totalProcessed = 0;

    // Search for unprocessed TagLeaf emails
    const tagleafQuery = `from:${SCRAPER_CONFIG.TAGLEAF_SENDER} -label:${SCRAPER_CONFIG.PROCESSED_LABEL} subject:"is complete" newer_than:30d`;
    const tagleafThreads = GmailApp.search(tagleafQuery, 0, SCRAPER_CONFIG.MAX_PER_RUN);

    for (const thread of tagleafThreads) {
      try {
        _processTagLeafThread(thread);
        thread.addLabel(processedLabel);
        totalProcessed++;
      } catch(e) {
        log("LabScraper: TagLeaf thread error", e.message);
        // Don't mark as processed — retry next run
      }
    }

    // Search for unprocessed Encore/Confident Cannabis emails
    const encoreQuery = `from:${SCRAPER_CONFIG.ENCORE_SENDER} -label:${SCRAPER_CONFIG.PROCESSED_LABEL} subject:"completed your order" newer_than:30d`;
    const encoreThreads = GmailApp.search(encoreQuery, 0, SCRAPER_CONFIG.MAX_PER_RUN);

    for (const thread of encoreThreads) {
      try {
        _processEncoreThread(thread);
        thread.addLabel(processedLabel);
        totalProcessed++;
      } catch(e) {
        log("LabScraper: Encore thread error", e.message);
      }
    }

    log("LabScraper: run complete", { processed: totalProcessed });

  } catch(e) {
    log("LabScraper: fatal error", e.message);
  }
}


// ─────────────────────────────────────────────────────────────
// _processTagLeafThread(thread)
//
// Parses a TagLeaf / Infinite Chemical results email.
//
// Email plain text format (from raw email analysis):
//   - {Product Name} ({SampleID}), a {type} has {passed/failed} testing.
//     View results: {URL}
//
// Example:
//   - Punch - Live Rosin - Blueberry Muffins - Badder (1g) - Tier 4
//     (ICC-260401-59-001), a QA concentrate sample has passed testing.
//     View results: https://lims.tagleaf.com/...
// ─────────────────────────────────────────────────────────────

function _processTagLeafThread(thread) {
  const message    = thread.getMessages()[0];
  const subject    = message.getSubject();
  const bodyPlain  = message.getPlainBody();

  // Extract order number from subject
  // Subject: "Your order ICC-ORD-118717 is complete!"
  const orderMatch = subject.match(/ICC-ORD-[\d]+/i);
  const orderNumber = orderMatch ? orderMatch[0] : "Unknown";

  log("LabScraper: processing TagLeaf order", orderNumber);

  // Parse each sample line from the plain text body
  // Pattern: "- {Product Name} ({SampleID}), a {type} has {passed/failed}"
  const samplePattern = /-\s+(.+?)\s+\((ICC-[\d\-]+)(?:,\s*Metrc\s+(1A[A-Z0-9]+))?\),\s+a\s+([\w\s]+)\s+has\s+(passed|failed)\s+testing\.\s+View results:\s+(https?:\/\/[^\s]+)/gi;

  const results = [];
  let match;

  // quoted-printable encoding uses =\n for line breaks — clean it first
  const cleanBody = bodyPlain
    .replace(/=\r?\n/g, '')   // remove soft line breaks
    .replace(/=3D/g, '=')     // decode = sign
    .replace(/=20/g, ' ');    // decode space

  while ((match = samplePattern.exec(cleanBody)) !== null) {
    results.push({
      productName: match[1].trim(),
      sampleID:    match[2].trim(),
      metrcUID:    match[3] ? match[3].trim() : "",  // ← NEW — from compliance emails
      sampleType:  match[4].trim(),                   // ← NEW — "compliance" or "QA"
      status:      match[5].toLowerCase().trim(),
      resultsURL:  match[6].trim(),
    });
  }

  if (results.length === 0) {
    log("LabScraper: no samples parsed from TagLeaf email", orderNumber);
    // Still notify team so they know results are in
    _sendManualReviewAlert("TagLeaf", orderNumber, subject, "Could not parse sample details — please review manually.");
    return;
  }

  log("LabScraper: parsed samples", results.length);

  // Also get the bulk download URL for all COA PDFs
  const bulkDownloadMatch = cleanBody.match(/download them all at once here:\s*(https?:\/\/[^\s]+)/i);
  const bulkDownloadURL = bulkDownloadMatch ? bulkDownloadMatch[1] : "";

  // Process each sample result
  const matched   = [];
  const unmatched = [];

  for (const result of results) {
    const batch = _findBatchForSample(result.sampleID, result.productName, result.metrcUID);

    if (batch) {
      // Determine if this is R&D or compliance test
      const isRND = !batch.labSampleIDRND ||
                    normalize(batch.labSampleIDRND) === normalize(result.sampleID);

      const newStatus = result.status === "passed"
        ? (isRND ? SCRAPER_CONFIG.STATUS_RND_PASSED : SCRAPER_CONFIG.STATUS_COA_PASSED)
        : SCRAPER_CONFIG.STATUS_FAILED;

      // Write results to UID_TRACKER
      // AFTER — remove newStatus argument:
      _writeLabResults(batch, result, isRND);

      matched.push({
        productName: result.productName,
        sampleID:    result.sampleID,
        status:      result.status,
        batchID:     batch.batchID,
        newStatus:   newStatus,
        resultsURL:  result.resultsURL,
      });

    } else {
      // No match found — log for manual review
      unmatched.push(result);
      log("LabScraper: no batch match", { sampleID: result.sampleID, product: result.productName });
    }
  }

  // Send notification email to team
  _sendTagLeafNotification(orderNumber, matched, unmatched, bulkDownloadURL);
}


// ─────────────────────────────────────────────────────────────
// _processEncoreThread(thread)
//
// Parses a Confident Cannabis / Encore results email.
// These emails only contain the order number — no product
// details or sample IDs. Until the webhook is set up,
// we just alert the team to pull results manually.
// ─────────────────────────────────────────────────────────────

function _processEncoreThread(thread) {
  const message = thread.getMessages()[0];
  const subject = message.getSubject();

  // Subject: "Encore Labs completed your order #2603ENC4539. See the results here!"
  const orderMatch = subject.match(/#([\w\d]+)/);
  const orderNumber = orderMatch ? orderMatch[1] : "Unknown";

  log("LabScraper: processing Encore order", orderNumber);

  _sendManualReviewAlert(
    "Encore / Confident Cannabis",
    orderNumber,
    subject,
    "Log in to app.confidentlims.com to download results and upload to the batch detail page."
  );
}


// ─────────────────────────────────────────────────────────────
// _findBatchForSample(sampleID, productName)
//
// Tries to find the matching batch using two strategies:
//   1. Direct sample ID match (col Q or R in UID_TRACKER)
//   2. Fuzzy product name match (fallback)
//
// Returns batch object or null.
// ─────────────────────────────────────────────────────────────

function _findBatchForSample(sampleID, productName, metrcUID) {
  // Strategy 1: direct sample ID match
  const byRND = _getBatchByColumnValue(CONFIG.COL.LAB_SAMPLE_ID_RND, sampleID);
  if (byRND) return byRND;

  const byCOA = _getBatchByColumnValue(CONFIG.COL.LAB_SAMPLE_ID_COA, sampleID);
  if (byCOA) return byCOA;
  // Strategy 1.5: direct METRC UID match (compliance emails include this)
  if (metrcUID) {
    const byUID = getBatchByUID(metrcUID);
    if (byUID) return byUID;
  }

  // Strategy 2: fuzzy product name match
  // Clean up the product name for comparison
  const cleanName = normalize(productName);
  const batches   = getAllBatches();


  const nameMatch = batches.find(b => normalize(b.item) === cleanName);

  if (nameMatch) {
    log("LabScraper: matched by product name", { sampleID, productName, batchID: nameMatch.batchID });
    return nameMatch;
  }

  return null;
}


// ─────────────────────────────────────────────────────────────
// _getBatchByColumnValue(col, value)
//
// Scans a specific column in UID_TRACKER for a value.
// Used to find batches by sample ID.
// ─────────────────────────────────────────────────────────────

function _getBatchByColumnValue(col, value) {
  if (!value || !col) return null;

  const sheet   = getTrackerSheet();
  const lastRow = sheet.getLastRow();
  if (lastRow < CONFIG.DATA_START_ROW) return null;

  const data = sheet
    .getRange(CONFIG.DATA_START_ROW, col, lastRow - CONFIG.DATA_START_ROW + 1, 1)
    .getValues();

  for (let i = 0; i < data.length; i++) {
    const stored = data[i][0];
    if (stored && normalize(String(stored)) === normalize(value)) {
      const uid = sheet.getRange(i + CONFIG.DATA_START_ROW, CONFIG.COL.METRC_UID).getValue();
      return getBatchByUID(uid);
    }
  }

  return null;
}


// ─────────────────────────────────────────────────────────────
// _writeLabResults(batch, result, isRND, newStatus)
//
// Writes lab results back to the UID_TRACKER row.
// Writes to the correct sample ID column (RND vs COA).
// ─────────────────────────────────────────────────────────────

// AFTER — keep sample ID and URL, remove status write:
function _writeLabResults(batch, result, isRND) {
  const sheet = getTrackerSheet();
  const row   = batch.rowIndex;
  const now   = new Date();

  const isRNDFinal = result.sampleType
    ? !result.sampleType.includes("compliance")
    : isRND;

  // Write sample ID to correct column
  const sampleCol = isRNDFinal ? CONFIG.COL.LAB_SAMPLE_ID_RND : CONFIG.COL.LAB_SAMPLE_ID_COA;
  sheet.getRange(row, sampleCol).setValue(result.sampleID);

  // Write results URL
  sheet.getRange(row, CONFIG.COL.LAB_RESULTS_URL).setValue(result.resultsURL);

  // NOTE: Status is NOT updated here intentionally.
  // COAParser owns all status updates once the PDF lands in Drive.
  sheet.getRange(row, CONFIG.COL.LAST_UPDATED).setValue(now);

  log("LabScraper: wrote sample ID + URL", {
    uid:      batch.metrcUID,
    batchID:  batch.batchID,
    sampleID: result.sampleID,
    isRND:    isRNDFinal,
  });
}


// ─────────────────────────────────────────────────────────────
// _sendTagLeafNotification(orderNumber, matched, unmatched, bulkURL)
//
// Sends a clean notification email to the team
// with results summary and direct links.
// ─────────────────────────────────────────────────────────────

function _sendTagLeafNotification(orderNumber, matched, unmatched, bulkURL) {
  const passedCount   = matched.filter(r => r.status === "passed").length;
  const failedCount   = matched.filter(r => r.status === "failed").length;
  const unmatchedCount = unmatched.length;
  const totalCount    = matched.length + unmatchedCount;

  const allPassed  = failedCount === 0 && unmatchedCount === 0;
  const hasFailed  = failedCount > 0;
  const needsReview = unmatchedCount > 0;

  // Subject line reflects overall result at a glance
  let subjectIcon = allPassed ? "[PASSED]" : (hasFailed ? "[FAILED]" : "[!]");
  const subject = `${subjectIcon} ${orderNumber} — ${passedCount}/${totalCount} Passed (Infinite Chemical)`;

  // ── BUILD EMAIL BODY ──────────────────────────────────────
  const now = new Date();
  const dateStr = Utilities.formatDate(now, Session.getScriptTimeZone(), "MMMM d, yyyy h:mm a");

  let body = "";
  body += `Order ${orderNumber} — Infinite Chemical Analysis Labs\n`;
  body += `Results received: ${dateStr}\n`;
  body += `${"─".repeat(50)}\n\n`;

  // Summary line
  body += `SUMMARY: ${totalCount} samples · ${passedCount} passed`;
  if (failedCount > 0)   body += ` · ${failedCount} FAILED`;
  if (unmatchedCount > 0) body += ` · ${unmatchedCount} needs manual match`;
  body += `\n\n`;

  // Matched results
  if (matched.length > 0) {
    body += `RESULTS\n`;
    body += `${"─".repeat(50)}\n`;

    for (const r of matched) {
      const icon = r.status === "passed" ? "[PASSED]" : "[FAILED]";
      body += `\n${icon} ${r.productName}\n`;
      if (r.batchID)    body += `   Batch ID:   ${r.batchID}\n`;
      body += `   Sample ID:  ${r.sampleID}\n`;
      body += `   Status →    ${r.newStatus}\n`;
      body += `   Results:    ${r.resultsURL}\n`;
    }
    body += "\n";
  }

  // Failed samples need extra attention
  if (failedCount > 0) {
    body += `${"─".repeat(50)}\n`;
    body += `[!]  ACTION REQUIRED — FAILED SAMPLES\n`;
    body += `The following batches failed testing and have been\n`;
    body += `flagged as "Delayed in Testing" in the tracker.\n\n`;
    for (const r of matched.filter(r => r.status === "failed")) {
      body += `[FAILED] ${r.productName}\n`;
      body += `   Batch ID:  ${r.batchID}\n`;
      body += `   Sample ID: ${r.sampleID}\n`;
      body += `   Results:   ${r.resultsURL}\n\n`;
    }
  }

  // Unmatched samples
  if (unmatched.length > 0) {
    body += `${"─".repeat(50)}\n`;
    body += `[!]  NEEDS MANUAL MATCHING (${unmatched.length})\n`;
    body += `These samples could not be automatically matched\n`;
    body += `to a batch. Please update the tracker manually.\n\n`;
    for (const r of unmatched) {
      const icon = r.status === "passed" ? "[PASSED]" : "[FAILED]";
      body += `${icon} ${r.productName}\n`;
      body += `   Sample ID: ${r.sampleID}\n`;
      body += `   Results:   ${r.resultsURL}\n\n`;
    }
  }

  // Bulk PDF download
  if (bulkURL) {
    body += `${"─".repeat(50)}\n`;
    body += `DOWNLOAD ALL COA PDFs`;
    body += `${bulkURL}\n\n`;
  }

  body += `${"─".repeat(50)}\n`;
  body += `Punch Tools · Lab Results Pipeline\n`;
  body += `Sample IDs recorded. Status will update automatically\n`;
  body += `when COA PDFs are uploaded to the COA Archive folder.\n`;

  _sendNotification(subject, body);
}


// ─────────────────────────────────────────────────────────────
// _sendManualReviewAlert(lab, orderNumber, subject, instructions)
//
// Sends a simple alert when we can't auto-process results.
// Used for Encore emails and parsing failures.
// ─────────────────────────────────────────────────────────────

function _sendManualReviewAlert(lab, orderNumber, originalSubject, instructions) {
  const now     = new Date();
  const dateStr = Utilities.formatDate(now, Session.getScriptTimeZone(), "MMMM d, yyyy h:mm a");

  const subject = `🔔 Results Ready: ${lab} — Order ${orderNumber}`;

  let body = "";
  body += `Lab results are ready for order ${orderNumber}.\n`;
  body += `Received: ${dateStr}\n`;
  body += `${"─".repeat(50)}\n\n`;
  body += `Lab:     ${lab}\n`;
  body += `Order:   ${orderNumber}\n\n`;
  body += `ACTION REQUIRED\n`;
  body += `${"─".repeat(50)}\n`;
  body += `${instructions}\n\n`;
  body += `Once downloaded, upload PDFs via the batch detail\n`;
  body += `page in Punch Tools to update statuses automatically.\n\n`;
  body += `${"─".repeat(50)}\n`;
  body += `Punch Tools · Lab Results Pipeline`;

  _sendNotification(subject, body);
}


// ─────────────────────────────────────────────────────────────
// _sendNotification(subject, body)
//
// Sends email to all recipients in SCRAPER_CONFIG.NOTIFY_ALL.
// Uses GmailApp.sendEmail with BCC to keep the list private.
// ─────────────────────────────────────────────────────────────

function _sendNotification(subject, body) {
  try {
    const recipients = SCRAPER_CONFIG.NOTIFY_ALL;
    if (!recipients || recipients.length === 0) {
      log("LabScraper: no recipients configured");
      return;
    }

    const to  = recipients[0];
    const bcc = recipients.slice(1).join(",");

    GmailApp.sendEmail(to, subject, body, {
      bcc:  bcc,
      name: "Punch Tools — Lab Results",
    });

    log("LabScraper: notification sent", { subject, to, bccCount: recipients.length - 1 });
  } catch(e) {
    log("LabScraper: notification failed", e.message);
  }
}

// ─────────────────────────────────────────────────────────────
// _ensureLabels()
//
// Creates the Gmail labels used for tracking processed emails.
// Safe to call multiple times — skips if labels exist.
// ─────────────────────────────────────────────────────────────

function _ensureLabels() {
  const labels = [
    SCRAPER_CONFIG.PROCESSED_LABEL,
    SCRAPER_CONFIG.PENDING_LABEL,
  ];

  for (const labelName of labels) {
    try {
      let label = GmailApp.getUserLabelByName(labelName);
      if (!label) {
        GmailApp.createLabel(labelName);
        log("LabScraper: created label", labelName);
      }
    } catch(e) {
      // Label might already exist with different case — ignore
    }
  }
}


// ─────────────────────────────────────────────────────────────
// SETUP FUNCTIONS
// Run these once manually from the Apps Script editor
// ─────────────────────────────────────────────────────────────

/**
 * installLabScraperTrigger()
 *
 * Creates a time-based trigger that runs processLabEmails()
 * every 30 minutes automatically.
 *
 * Run this ONCE from the Apps Script editor.
 * You'll see it appear under Triggers (alarm clock icon).
 */
function installLabScraperTrigger() {
  // Remove any existing triggers for this function first
  const existing = ScriptApp.getProjectTriggers();
  for (const trigger of existing) {
    if (trigger.getHandlerFunction() === "processLabEmails") {
      ScriptApp.deleteTrigger(trigger);
    }
  }

  // Create new trigger — every 30 minutes
  ScriptApp.newTrigger("processLabEmails")
    .timeBased()
    .everyMinutes(30)
    .create();

  log("LabScraper: trigger installed — runs every 30 minutes");
  return "Trigger installed. processLabEmails() will run every 30 minutes.";
}

/**
 * testLabScraper()
 *
 * Run this from the Apps Script editor to test the scraper
 * without waiting for the trigger.
 * Processes any unprocessed lab emails right now.
 */
function testLabScraper() {
  processLabEmails();
  return "Done — check Logger.log for details";
}

/**
 * testTagLeafParsing()
 *
 * Dry-run the parser on the most recent TagLeaf email
 * without writing anything to the sheet or sending emails.
 * Use this to verify parsing before going live.
 */
function testTagLeafParsing() {
  const query = `from:${SCRAPER_CONFIG.TAGLEAF_SENDER} subject:"is complete"`;
  const threads = GmailApp.search(query, 0, 1);

  if (threads.length === 0) {
    return "No TagLeaf emails found.";
  }

  const message   = threads[0].getMessages()[0];
  const subject   = message.getSubject();
  const bodyPlain = message.getPlainBody();

  const cleanBody = bodyPlain
    .replace(/=\r?\n/g, '')
    .replace(/=3D/g, '=')
    .replace(/=20/g, ' ');

  const samplePattern = /-\s+(.+?)\s+\((ICC-[\d\-]+)(?:,\s*Metrc\s+(1A[A-Z0-9]+))?\),\s+a\s+([\w\s]+)\s+has\s+(passed|failed)\s+testing\.\s+View results:\s+(https?:\/\/[^\s]+)/gi;


  const results = [];
  let match;

  while ((match = samplePattern.exec(cleanBody)) !== null) {
    results.push({
      productName: match[1].trim(),
      sampleID:    match[2].trim(),
      metrcUID:    match[3] ? match[3].trim() : "",  // ← NEW — from compliance emails
      sampleType:  match[4].trim(),                   // ← NEW — "compliance" or "QA"
      status:      match[5].toLowerCase().trim(),
      resultsURL:  match[6].trim(),
});
  }

  Logger.log("Subject: " + subject);
  Logger.log("Samples found: " + results.length);
  Logger.log(JSON.stringify(results, null, 2));

  return `Parsed ${results.length} samples from "${subject}". Check Logger for details.`;
}

function debugTagLeafEmail() {
  const query = 'from:lab.infinitecal@tagleaf.com subject:"ICC-ORD-117767"';
  const threads = GmailApp.search(query, 0, 1);
  
  if (threads.length === 0) {
    Logger.log("Email not found");
    return;
  }
  
  const body = threads[0].getMessages()[0].getPlainBody();
  Logger.log("RAW BODY (first 2000 chars):");
  Logger.log(body.substring(0, 2000));
}