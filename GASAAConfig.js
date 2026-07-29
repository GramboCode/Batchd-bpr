// ============================================================
// Config.gs - Punch Tools
// ============================================================

const CONFIG = {

  // ── SPREADSHEET ───────────────────────────────────────────
  TRACKER_SS_ID: "1yNldRwg8E0paStewgW82ZGouIRqE9S9XKYdfEPmOEqU",
  TRACKER_TAB:   "UID",
  DATA_START_ROW: 4,
  DATE_FORMAT:   "M/d/yyyy",

   // ── COLUMN MAP (1-based) ──────────────────────────────────
  // Col A = CHECKBOX (bound script only — not read by web app)
  COL: {
    CHECKBOX:           1,  // A — checkbox (for the sheet)
    METRC_UID:          2,  // B
    ITEM:               3,  // C
    CATEGORY:           4,  // D
    ITEM_STRAIN:        5,  // E
    BATCH_ID:           6,  // F
    MFG_DATE:           7,  // G
    QUANTITY:           8,  // H
    UNIT_OF_MEASURE:    9,  // I
    LAB:                10, // J
    STATUS:             11, // K
    TEST_DATE:          12, // L
    MRID_LABEL:         13, // M
    TARGET_QTY:         14, // N
    BATCH_SHEET_URL:    15, // O
    RETAIL_ID_MADE:     16, // P
    METRC_SYNCED:       17, // Q
    LAB_SAMPLE_ID_RND:  18, // R
    LAB_SAMPLE_ID_COA:  19, // S
    LAB_RESULTS_URL:    20, // T
    CREATED_AT:         21, // U
    LAST_UPDATED:       22, // V
    COA_LINK:           23, // W
    THC_PCT:            24, // X
    THC_MG_G:           25, // Y
    THC_MG_PKG:         26, // Z
    CBD_PCT:            27, // AA
    CBD_MG_G:           28, // AB
    CBD_MG_PKG:         29, // AC
    TOTAL_CB_PCT:       30, // AD
    TOTAL_CB_MG_G:      31, // AE
    TOTAL_CB_MG_PKG:    32, // AF
    RND_THC_MG_PKG:     33, // AG — RND potency stored for tolerance check
    LABEL_CLAIM_MG:     34, // AH — 100 for edibles, blank for others
    TOLERANCE_FLAG:     35, // AI — WITHIN / OVER / UNDER
    BPR_STATUS:         36, // AJ
    BPR_PDF_URL:        37, // AK
  },

  // ── STATUSES ──────────────────────────────────────────────
  STATUS: {
    // In Production group
    IN_PRODUCTION:        "In Production",
    READY_FOR_PACKAGING:  "Ready for Packaging",
    PACKAGING_COMPLETE:   "Packaging Complete",
    SUBMITTED_FOR_RND:    "Submitted for RND",
    PASSED_RND:           "Passed RND",
    REMAKE:               "Remake",
    ARCHIVED:             "Archived",

    // Need Labels group
    NEED_LABELS:          "Need Labels",
    LABELS_MADE:          "Labels Made",
    
    // Ready for Testing group
    READY_FOR_TESTING:    "Ready for Testing",

    // Awaiting Results group
    SUBMITTED_COMPLIANCE: "Submitted for Compliance",
    COMPLIANCE_PASSED:   "Compliance Passed",
    DELAYED_IN_TESTING:   "Delayed in Testing",
    TESTING_CANCELLED:    "Testing Cancelled",

    // Failed
    FAILED:               "Failed",
    COMPLIANCE_REVIEW:    "Compliance Review",

    // Complete — drops off active filter
    PASSED_NOT_DISTRO:    "Passed BUT NOT Avail in Distru",
    AVAIL_IN_DISTRO:      "Avail in Distru/On Menu",
  },

  // ── STATUS LIST (ordered for selector) ───────────────────
  STATUS_LIST: [
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
    "Failed",
    "Compliance Review",
    "Passed BUT NOT Avail in Distru",
    "Avail in Distru/On Menu",
    "Archived",
  ],

  // ── STAT CARD GROUPINGS ───────────────────────────────────
  STAT_GROUPS: {
    inProduction: [
      "In Production",
      "Ready for Packaging",
      "Packaging Complete",
      "Submitted for RND",
      "Passed RND",
      "Remake",
    ],
    needLabels: [
      "Need Labels",
      "Labels Made",
    ],
    readyForTesting: [
      "Ready for Testing",
    ],
    awaitingResults: [
      "Submitted for Compliance",
      "Delayed in Testing",
      "Testing Cancelled",
      
    ],
    failed: [
      "Failed",
    ],
    complete: [
      "Compliance Passed",
      "Compliance Review",
      "Passed BUT NOT Avail in Distru",
    ],
    archived: [
      "Archived",
      "Avail in Distru/On Menu",
    ],
  },

  // ── INACTIVE STATUSES (hidden when Active Only checked) ───
  INACTIVE_STATUSES: [
    "Compliance Passed",
    "Passed BUT NOT Avail in Distru",
    "Avail in Distru/On Menu",
    "Archived",
  ],

  // ── LABS ─────────────────────────────────────────────────
  LABS: ["Encore", "Infinite", "Landau"],

  // ── ADMIN USERS ──────────────────────────────────────────
  ADMINS: ["darrayl@punchedibles.com","grayson@punchedibles.com","yoka@punchedibles.com","ismaelramirez@punchedibles.com"],

  // ── DEFAULT PRODUCT TEMPLATES ────────────────────────────
   DEFAULT_TEMPLATES: {
    punch_live_rosin: {
      brand: "Punch", label: "Live Rosin",
      category: "Extract (weight - each)", uom: "Each",
      type: "dynamic",
      fields: ["strain","format","tier"],
      formats: ["Badder","Fresh Press","Half & Half","Jar Tech"],
      tiers: ["Tier 1","Tier 2","Tier 3","Tier 4"],
      defaultFormat: "Badder", defaultTier: "Tier 4",
      pattern: "Punch - Live Rosin - {strain} - {format} (1g) - {tier}",
      hint: "e.g. Demon Timez, Moroccan Papaya..."
    },
    tempo_live_rosin: {
      brand: "Tempo", label: "Live Rosin",
      category: "Extract (weight - each)", uom: "Each",
      type: "preset", fields: ["flavor_select"],
      flavors: [
        // Sativa — Revive
        "Solar Nectar - Badder (1g) - (Sativa)",
        "Mandarin Mirage - Badder (1g) - (Sativa)",
        "Peach Squeeze - Badder (1g) - (Sativa)",
        "Sunkissed Lime - Badder (1g) - (Sativa)",
        // Indica — Relax
        "Velvet Jelly - Badder (1g) - (Indica)",
        "Moonbow Glow - Badder (1g) - (Indica)",
        "Papaya Plum Cake - Badder (1g) - (Indica)",
        "Mulberry Mind Meltz - Badder (1g) - (Indica)",
        // Hybrid — Balance
        "Moss Theory - Badder (1g) - (Hybrid)",
        "Pine Bloom - Badder (1g) - (Hybrid)",
        "Cosmic Grove - Badder (1g) - (Hybrid)",
        "Happy Hollow - Badder (1g) - (Hybrid)"
      ],
      pattern: "Tempo - Live Rosin - {flavor}"
      // Full name example: "Tempo - Live Rosin - Solar Nectar - Badder (1g) - (Sativa)"
    },
    
    punch_bho_badder: {
      brand: "Punch", label: "BHO Badder",
      category: "Extract (weight - each)", uom: "Each",
      type: "dynamic", fields: ["strain"],
      pattern: "Punch - BHO Badder - {strain} (1g)",
      hint: "e.g. Gelato 41, Kush Mintz..."
    },
    punch_bho_shatter: {
      brand: "Punch", label: "BHO Shatter",
      category: "Extract (weight - each)", uom: "Each",
      type: "dynamic", fields: ["strain"],
      pattern: "Punch - BHO Shatter - {strain} (1g)",
      hint: "e.g. Pink Runtz, King Louie OG..."
    },
    punch_rocket: {
      brand: "Punch", label: "Rocket (1.6g)",
      category: "Pre-Roll Infused", uom: "Each",
      type: "dynamic", fields: ["strain","collab"],
      collabs: ["White","C.A.M.","Bosky","Claybourne","Connected","LAX","COTC","Oakfruitland","3C","True Classic"],
      defaultCollab: "White",
      pattern: "Punch - Rocket - {strain} (1.6g) - ({collab})",
      hint: "e.g. Bubba's Girl x Guava Pop..."
    },
    punch_stinger: {
      brand: "Punch", label: "Stinger (2.5g)",
      category: "Pre-Roll Infused", uom: "Each",
      type: "preset", fields: ["flavor_select"],
      flavors: [
        "Blue Dream","Dulce Fresa","Florida's Finest","Fruit Punch",
        "Gelato","Island Breeze",
        "King Louie XIII OG","Maui Wowie","Mimosa",
        "Peach Rings","Platinum OG",
        "Sour Diesel","Summer Lemon","Summer Sandia",
        "Sweet Strawberry","The Z","Watermelon Splash"
      ],
      pattern: "Punch - Stinger - {flavor} (2.5g) 5 pre-rolls"
    },
    punch_gummies: {
      brand: "Punch", label: "Gummies 100mg",
      category: "Edible (weight - each)", uom: "Each",
      type: "preset", fields: ["flavor_select"],
      flavors: [
        "Apple Pear","Blueberry Lemonade","Cherry Cola","Cherry Limeade",
        "Kiwi Strawberry","Orange Guava","Peach Mango",
        "Strawberry Lemonade","Tropical Punch","Watermelon"
      ],
      pattern: "Punch - 100mg Gummies - {flavor}"
    },
    punch_punchbar: {
      brand: "Punch", label: "Chocolate",
      category: "Edible (weight - each)", uom: "Each",
      type: "preset", fields: ["flavor_select"],
      flavors: [
        "Dark Chocolate Almonds","Milk Chocolate","Mint Dark Chocolate",
        "S'mores Milk Chocolate","Sea Salt Dark Chocolate","Toffee Milk Chocolate",
        "Peanut Butter Jelly Dark Chocolate","Peanut Butter Milk Chocolate",
        "Strawberry Cheesecake",
        "Caramel Bits (Solventless)","Raspberry Dark (Solventless)",
        "Sugar-Free Dark Chocolate (Solventless)",
        "Sugar-Free Milk Chocolate (Solventless)",
        "Peanut Butter Milk Chocolate Crunch (Solventless)",
        "Cookies 'N Cream Cream (Solventless)","Key Lime Pie Cream (Solventless)"
      ],
      pattern: "Punch - 100mg PunchBar - {flavor}"
    },
    punch_malt_balls: {
      brand: "Punch", label: "Malt Balls",
      category: "Edible (weight - each)", uom: "Each",
      type: "preset", fields: ["flavor_select"],
      flavors: [
        "Cookies N Cream","Dark Chocolate Mocha","Milk Chocolate",
        "Peanut Butter","Strawberry White Chocolate"
      ],
      pattern: "Punch - 100mg Solventless Malt Balls - {flavor}"
    },
    punch_asteroids: {
      brand: "Punch", label: "Solventless Asteroids",
      category: "Edible (weight - each)", uom: "Each",
      type: "preset", fields: ["flavor_select"],
      flavors: [
        "Galactic Fruit Punch",
        "Watermelon Nova",
        "Cherry Razz Storm",
        "Strawberry Grape Nebula",
        "Pineapple Peach Portal"
      ],
      pattern: "Punch - 100mg Solventless Asteroids - {flavor}"
    },
    punch_rosin_aio: {
      brand: "Punch", label: "Rosin AIO Vape",
      category: "Vape Cartridge (weight - each)", uom: "Each",
      type: "dynamic", fields: ["strain"],
      pattern: "Punch - Rosin AIO Vape - {strain} (1g)",
      hint: "e.g. Banana Punch, Benzina, Cherry Paloma..."
    },
    punch_vapes: {
      brand: "Punch", label: "510 Distillate Vapes",   // relabeled for clarity — was just "Distillate Vapes"
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
      pattern: "Punch - 510 Distillate Cart - {flavor} (1g)"
    },
    punch_2g_dist_vapes: {
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
        // TODO: append effect tags — e.g. "Rainbow Sherbert (Hybrid)" — before go-live
      ],
      pattern: "Punch - 2g Distillate AIO - {flavor} (2g)"
      // Full name once effects are added: "Punch - 2g Distillate AIO - Rainbow Sherbert (Hybrid) (2g)"
    },
    tempo_aio: {
      brand: "Tempo", label: "AIO Vape",
      category: "Vape Cartridge (weight - each)", uom: "Each",
      type: "preset", fields: ["flavor_select"],
      flavors: [
        "Blue Razz Ice","Cherry Passion Ice","Huckleberry Ice",
        "Kiwi Kush","Kush Mints Ice","Mystic Mango",
        "OG Grape","Strawberry Beltz","Yuzu Haze"
      ],
      pattern: "Tempo - AIO Vape - {flavor} (1g)"
    },
    tempo_blends: {
      brand: "Tempo", label: "Blends AIO Vape",
      category: "Vape Cartridge (weight - each)", uom: "Each",
      type: "preset", fields: ["flavor_select"],
      flavors: ["Peach Ringz","Space Jelly","Watermelon Frost", "Fuji Apple Pear", "Stoned Fruit", "Dragonfruit Freeze"],
      pattern: "Tempo - Blends AIO Vape - {flavor} (1g)"
    },
    tempo_lr_aio: {
      brand: "Tempo", label: "Live Resin AIO",
      category: "Vape Cartridge (weight - each)", uom: "Each",
      type: "preset", fields: ["flavor_select"],
      flavors: [
        "Chemdawg (Hybrid)","Durban Lime (Sativa)",
        "Grandaddy Purp (Indica)","Super Glue (Indica)",
        "Tangie Dream (Sativa)","Thin Mint GSC (Hybrid)"
      ],
      pattern: "Tempo - Live Resin AIO Vape - {flavor} - (1g)"
    },
    tempo_lr_diamonds: {
      brand: "Tempo", label: "Live Resin Diamonds",
      category: "Extract (weight - each)", uom: "Each",
      type: "dynamic", fields: ["strain"],
      pattern: "Tempo - Live Resin Diamonds - {strain} (1g)",
      hint: "e.g. Tangie Dream (Sativa), Super Glue (Indica)..."
    },
    dr_norms: {
      brand: "Dr. Norm's", label: "Baked Goods",
      category: "Edible (weight - each)", uom: "Each",
      type: "preset", fields: ["flavor_select"],
      flavors: [
        "Chocolate Chip Cookies (10 cookies)",
        "Chocolate Chip 1:1 (10 cookies)",
        "Chocolate Chip 20mg Cookies (5 cookies)",
        "Peanut Butter Chocolate Chip (10 cookies)",
        "PB Chocolate Chip 1:1 (10 cookies)",
        "Peanut Butter 20mg Cookies (5 cookies)",
        "Red Velvet (10 cookies)",
        "Red Velvet 20mg Cookies (5 cookies)",
        "Snickerdoodle (10 cookies)",
        "Snickerdoodle 20mg Cookies (5 cookies)",
        "Pecan Shortbread Cookies (10 cookies)",
        "MAX Chocolate Chip Cookie",
        "MAX Peanut Butter Chocolate Chip Cookie",
        "MAX Red Velvet Cookie",
        "MAX Snickerdoodle Cookie",
        "Chocolate Fudge Brownie",
        "Salted Caramel Blondie",
        "Solventless PB Chocolate Brownie",
        "Solventless Peanut Butter Cup Brownie",
        "Mini Sleep Brownies 2:1",
        "RKT Matcha","RKT Original","RKT Fruity Pebbles",
        "RKT Chocolate","RKT Captain Crunch berries",
        "NANO RKT Cinnamon Toast Crunch","NANO RKT Very Berry Crunch",
        "100mg Cookies N Cream NANO (10 cookies)",
        "MAX Cookies N Cream NANO",
      ],
      pattern: "Dr. Norm's- 100mg {flavor}"
    }
  },
};

// ─────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────

function getTrackerSheet() {
  const ss = SpreadsheetApp.openById(CONFIG.TRACKER_SS_ID);
  const sheet = ss.getSheetByName(CONFIG.TRACKER_TAB);
  if (!sheet) throw new Error('Sheet "' + CONFIG.TRACKER_TAB + '" not found.');
  return sheet;
}

function getActiveLabs() {
  try {
    const props = PropertiesService.getScriptProperties();
    const stored = props.getProperty("punch_labs");
    if (stored) return JSON.parse(stored);
  } catch(e) {}
  return CONFIG.LABS;
}

function getProductTemplates() {
  try {
    const props = PropertiesService.getScriptProperties();
    // Check both keys for backward compatibility
    const stored = props.getProperty("PRODUCT_TEMPLATES") || props.getProperty("punch_templates");
    if (stored) return JSON.parse(stored);
  } catch(e) {}
  return CONFIG.DEFAULT_TEMPLATES;
}

function formatDate(date) {
  if (!date) return "";
  try {
    return Utilities.formatDate(
      date instanceof Date ? date : new Date(date),
      Session.getScriptTimeZone(),
      CONFIG.DATE_FORMAT
    );
  } catch(e) {
    return String(date);
  }
}

function parseISODate(isoStr) {
  if (!isoStr) return null;
  const parts = isoStr.split("-");
  if (parts.length !== 3) return null;
  return new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
}

function normalize(str) {
  return String(str || "").toLowerCase().trim();
}

function log(message, data) {
  const prefix = "[Punch Tools] ";
  if (data !== undefined) {
    Logger.log(prefix + message + ": " + JSON.stringify(data));
  } else {
    Logger.log(prefix + message);
  }
}
