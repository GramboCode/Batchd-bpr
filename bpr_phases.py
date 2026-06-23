"""
BPR Phase definitions for all product families.
Each phase has:
  - id: unique slug
  - name: display name
  - steps: list of checklist items
  - ccps: list of step indices that are Critical Control Points (require measurement)
  - ccp_labels: measurement label for each CCP step index
  - notes_required: whether notes field is mandatory before sign-off
"""

BPR_PHASES = {

  # ─────────────────────────────────────────────────────────────────
  # LIVE ROSIN
  # ─────────────────────────────────────────────────────────────────
  "live_rosin": {
    "label": "Live Rosin Concentrate",
    "sop_ref": "P007 / MMP-MASTER-001",
    "uom": "grams",
    "phases": [
      {
        "id": "pre_production",
        "name": "Pre-Production Setup",
        "steps": [
          "Verify UID tag is attached to source material container",
          "Confirm source material weight on certified scale — record wet flower weight",
          "Verify all equipment is clean, sanitized, and dry (washers, freeze dryer, rosin press, trays, tools)",
          "Confirm freezer temperature is at or below 35°F",
          "Confirm work area is free of clutter — only items essential to this run are present",
          "Gloves on — maintain throughout all extraction stages",
          "Complete allergen pre-run clearance check",
        ],
        "ccps": [1],
        "ccp_labels": {1: "Source material wet weight (g)"},
        "notes_required": False,
      },
      {
        "id": "ice_water_wash",
        "name": "Ice Water Wash",
        "steps": [
          "Fill tea bags with 4,000g wet material each — keep frozen until washing begins",
          "Load washers: 3 buckets ice per washer → add 3–4 tea bags → add 3 more buckets ice → fill with water until bags fully submerged",
          "Run 2 wash cycles — keep room cold, act quickly between cycles",
          "Remove tea bags and allow hash to drain",
          "Drain water through ice extract 2.0 bags",
          "Return tea bags to washer, refill with ice and water — run 2 more cycles",
          "Collect hash onto tray using sterile spoon",
          "Load hash into freeze dryer immediately",
          "Record weight washed in Fresh Frozen to Rosin tracker (Google Sheet)",
          "Dispose of cannabis by-product in locked cannabis waste receptacle — record in Waste Management Log",
        ],
        "ccps": [],
        "ccp_labels": {},
        "notes_required": False,
      },
      {
        "id": "freeze_drying",
        "name": "Freeze Drying",
        "steps": [
          "Confirm freeze dryer was pre-cooled before batch loading",
          "Load batches into freeze dryer — place heaviest/wettest batches first",
          "Turn on vacuum pump — set drying time appropriate to water content",
          "Check oil level — perform oil change if needed",
          "Break up thick portions of hash mid-cycle as needed",
          "Remove hash after drying is confirmed complete",
          "Strain hash and weigh on certified scale — record dry hash weight",
          "Press defrost — open valve before initiating to let water drain",
          "Clean freeze dryer trays immediately after use",
        ],
        "ccps": [6],
        "ccp_labels": {6: "Dry hash weight (g)"},
        "notes_required": False,
      },
      {
        "id": "pressing",
        "name": "Rosin Press",
        "steps": [
          "Remove hash from freezer — mold into 5–6g rectangles",
          "Set and fold each rectangle into mesh screen",
          "Confirm press temperature is at recommended setting for this material",
          "Set parchment, place under press — start press cycle",
          "Allow rosin to run through — do not rush the press",
          "Freeze pressed hash squares when complete",
          "Weigh rosin yield on certified scale on parchment paper — record rosin yield weight",
          "Measure waste, label, dispose in locked waste box — record in Waste Log",
          "Clean rosin press plates immediately after use",
        ],
        "ccps": [6],
        "ccp_labels": {6: "Rosin yield weight (g)"},
        "notes_required": False,
      },
      {
        "id": "qc_yield",
        "name": "QC & Yield Verification",
        "steps": [
          "Calculate yield percentage: (Rosin yield ÷ Dry hash weight) × 100",
          "Verify yield is within acceptable range for this material",
          "Inspect rosin for visual quality: color, consistency, absence of foreign material",
          "Confirm all UID tags remain with the product",
          "Weigh final batch quantity for METRC package creation",
          "Note any deviations from expected yield in deviation log",
        ],
        "ccps": [0, 4],
        "ccp_labels": {0: "Yield % (calculated)", 4: "Final batch weight (g)"},
        "notes_required": False,
      },
      {
        "id": "packaging",
        "name": "Packaging & Labeling",
        "steps": [
          "Confirm glass containers are clean and wiped free of dust/lint",
          "Fill containers to target weight — verify on certified scale",
          "Seal containers immediately after filling",
          "Apply UID label and batch label to each container",
          "Verify all required label fields present: Product Name, Batch#, UID#, Mfg Date, Exp Date, THC%, net weight",
          "Place sealed containers in temperature-controlled storage area",
          "Record final packaged unit count",
        ],
        "ccps": [1, 6],
        "ccp_labels": {1: "Container fill weight (g)", 6: "Total packaged units"},
        "notes_required": False,
      },
      {
        "id": "sanitation",
        "name": "Post-Run Sanitation",
        "steps": [
          "Flush washers thoroughly with hot water — use ISO-alcohol or chlorine sanitizer EOD",
          "Clean ice extract bags or replace if worn",
          "Clean freeze dryer trays — do not clean while in use",
          "Clean rosin press plates — check oil levels and lubricate if needed",
          "Wipe all tabletop counters and surfaces with 70–99% ISO-alcohol",
          "Dispose of all single-use materials (parchment, mesh bags if worn)",
          "Complete cleaning log entry — date, equipment cleaned, method, PPM verified, initials",
        ],
        "ccps": [],
        "ccp_labels": {},
        "notes_required": False,
      },
    ]
  },

  # ─────────────────────────────────────────────────────────────────
  # GUMMIES (also covers Asteroids, Fruit Snacks)
  # ─────────────────────────────────────────────────────────────────
  "gummies": {
    "label": "Gummies / Fruit Snacks",
    "sop_ref": "P007 / P003 / MMP-MASTER-001",
    "uom": "units",
    "phases": [
      {
        "id": "pre_production",
        "name": "Pre-Production Setup",
        "steps": [
          "Verify UID tag is attached to cannabis source material (distillate)",
          "Confirm all equipment is clean, sanitized, and completely DRY (moisture ruins gummy texture)",
          "Silicon molds: hot water only — verify dry before use",
          "Mixing bowls and utensils: hot water, soap, sanitize — verify dry",
          "Induction burner: hot water only",
          "All tabletop counters and surfaces: 70–99% ISO-alcohol",
          "Work area is free of clutter — only items for this run present",
          "Gloves on — maintain throughout production",
          "Complete allergen pre-run clearance check",
          "Confirm Apple Juice Concentrate is available (should be stored frozen)",
        ],
        "ccps": [],
        "ccp_labels": {},
        "notes_required": False,
      },
      {
        "id": "ingredient_prep",
        "name": "Ingredient Prep & Weighing",
        "steps": [
          "Weigh Apple Juice Concentrate on calibrated scale — record weight",
          "Weigh Corn Syrup — record weight",
          "Weigh Sugar — record weight",
          "Weigh Modified Cornstarch and Cornstarch — record combined weight",
          "Weigh Water for Agar — record weight",
          "Weigh Agar Agar — soak in water for minimum 10 minutes before cooking",
          "Weigh Citric Acid — record weight",
          "Weigh THC Distillate on precision scale (.001g) — record weight",
          "Weigh Flavoring — record weight",
          "Weigh Color — record weight per flavor",
          "All ingredient weights verified against MMP-MASTER-001 batch formula",
          "All ingredients in assigned, sealed bins — LOT numbers confirmed",
        ],
        "ccps": [7],
        "ccp_labels": {7: "THC Distillate weight (g)"},
        "notes_required": False,
      },
      {
        "id": "cook",
        "name": "Cook",
        "steps": [
          "Combine Apple Juice Concentrate and Corn Syrup in pot — add 2g of designated color on top",
          "Set burner to 330°F — stir continuously",
          "Cook until mixture is fully broken down and 'runny' (10–15 min) — mixture should be smooth, not lumpy",
          "Add Sugar and THC Distillate — switch to KitchenAid for continuous stirring",
          "Continue until sugar is fully dissolved, not granular (10–15 min)",
          "Add Flavoring — stir 5 minutes (caution: steam at this stage)",
          "Monitor temperature — reach minimum 200°F before adding Agar",
          "Verify temperature does not exceed 250°F (Agar denatures above 250°F)",
          "Add Agar — switch to spatula, stir until mixture thickens, scrape sides",
          "Add remaining dry ingredients (cornstarch mix) — no clumps",
          "Switch to KitchenAid mixer — confirm no cornstarch clumps remain",
          "Add remaining color — confirm final color consistency",
        ],
        "ccps": [6, 7],
        "ccp_labels": {6: "Temperature before Agar (°F) — must be 200–250°F", 7: "Temperature confirmed below 250°F (yes/no)"},
        "notes_required": False,
      },
      {
        "id": "depositing",
        "name": "Depositing",
        "steps": [
          "Confirm dispensing machine is preheated to 210°F (needs 30 min warm-up)",
          "Confirm molds are clean and coated with cornstarch",
          "Lubricate nozzles with vegetable oil or coconut oil (no animal fat)",
          "Pull handle 5 times before first pour to calibrate machine",
          "Dispense mixture into molds — verify each cavity fills without over-pouring",
          "Weigh sample units from first molds — confirm weight 2.4g < X < 2.6g per piece",
          "Cover filled racks immediately to prevent foreign material contamination",
          "Allow gummies to cure on racks — do not move until set",
        ],
        "ccps": [5],
        "ccp_labels": {5: "Sample unit weight (g) — target 2.4–2.6g"},
        "notes_required": False,
      },
      {
        "id": "curing",
        "name": "Curing",
        "steps": [
          "Confirm racks are covered throughout curing period",
          "Curing time: minimum 24 hours before packaging",
          "Check set: gummies should be firm and release cleanly from mold",
          "Clean flashing (excess material around each square) from mold borders",
          "Pop gummies onto parchment-lined baking sheets — 3–4 molds per sheet",
          "Set aside any pieces dramatically smaller or larger than mold cavity (dosing risk)",
          "Create single layer on each rack — allow additional drying time",
          "Create single layer on each rack — do not pile",
        ],
        "ccps": [],
        "ccp_labels": {},
        "notes_required": False,
      },
      {
        "id": "qc_weight",
        "name": "QC Weight Check",
        "steps": [
          "Pull representative sample (minimum 10 pieces per batch) for weight verification",
          "Weigh each sample unit on calibrated scale — record individual weights",
          "Confirm all samples are within tolerance: 2.4g < X < 2.6g",
          "Flag and set aside any out-of-spec pieces — do not package",
          "Record number of approved units and number of rejected/waste units",
          "Confirm UID tag remains with batch at all times",
        ],
        "ccps": [0],
        "ccp_labels": {0: "Sample weight range (g) — confirm all within 2.4–2.6g"},
        "notes_required": True,
      },
      {
        "id": "packaging",
        "name": "Packaging & Labeling",
        "steps": [
          "Select 10 units per package — alternate 3 flavors in 3-4-3 quantities (for multi-flavor SKUs)",
          "Place into child-resistant mylar pouch",
          "Press firmly to seal — remove excess air from packaging",
          "Feed through continuous sealing machine (preheat to 180°F)",
          "Confirm tamper seal is intact",
          "Apply batch label — verify all required fields: Product Name, Batch#, UID#, Mfg Date, Exp Date, THC mg/unit, THC total, 'Contains' allergen statement",
          "Inspect label legibility and accuracy on 5 sample units before full batch labeling",
          "Record total packaged unit count",
        ],
        "ccps": [5],
        "ccp_labels": {5: "Total packaged units"},
        "notes_required": False,
      },
      {
        "id": "sanitation",
        "name": "Post-Run Sanitation",
        "steps": [
          "Truffly Gummy Machine: separate all components (hopper, dispensers, nozzles, stoppers) — wash hot water + soap — sanitize — dry completely",
          "Silicon molds: hot water only — dry completely",
          "Mixing bowls and utensils: hot water + soap + sanitize",
          "Induction burner: hot water only",
          "All tabletop counters and surfaces: 70–99% ISO-alcohol",
          "Complete cleaning log entry — date, equipment, method, PPM verified, initials",
        ],
        "ccps": [],
        "ccp_labels": {},
        "notes_required": False,
      },
    ]
  },

  # ─────────────────────────────────────────────────────────────────
  # TEMPO VAPES / DISTILLATE VAPES (510 + TEMPO AIO)
  # ─────────────────────────────────────────────────────────────────
  "vapes": {
    "label": "Vape Cartridges / AIO (Distillate & Live Rosin)",
    "sop_ref": "P007 / MMP-MASTER-001",
    "uom": "units",
    "phases": [
      {
        "id": "pre_production",
        "name": "Pre-Production Setup",
        "steps": [
          "Verify UID tag is attached to oil source material",
          "Confirm hardware (cartridges/pods) lot and supplier match spec for this SKU",
          "VapeJet machine: flush needles, reservoirs, oil lines, and tanks with 70–99% ISO-alcohol — dry completely",
          "All tabletop counters and surfaces: 70–99% ISO-alcohol",
          "Confirm oil is at appropriate viscosity for filling temperature",
          "Work area is free of clutter — only items for this run present",
          "Gloves on — maintain throughout production",
          "Complete allergen pre-run clearance check (N/A for solventless — confirm)",
        ],
        "ccps": [],
        "ccp_labels": {},
        "notes_required": False,
      },
      {
        "id": "hardware_inspection",
        "name": "Hardware Inspection",
        "steps": [
          "Inspect each cartridge/pod: no cracks, no defective threading, no visible debris",
          "Confirm hardware matches the correct SKU spec (510 vs AIO vs TEMPO)",
          "Confirm cartridge resistance/coil spec matches this oil type",
          "Pull visual sample (minimum 10 units) — reject any with cosmetic defects",
          "Record hardware lot number for batch record",
          "Confirm child-resistant packaging is available and correct for SKU",
        ],
        "ccps": [],
        "ccp_labels": {},
        "notes_required": False,
      },
      {
        "id": "filling",
        "name": "Filling (VapeJet)",
        "steps": [
          "Load oil into VapeJet reservoir — confirm no air bubbles in oil lines",
          "Set filling temperature appropriate for oil viscosity",
          "Run test fills on 3 units — weigh to confirm fill weight is on target",
          "Confirm fill weight tolerance: verify against MMP spec for this SKU",
          "Begin production run — monitor fill weight periodically (every 25 units minimum)",
          "Cap each unit immediately after filling",
          "Set aside any units with visible underfill, overfill, or oil contamination on exterior",
          "Track total units filled and waste units",
        ],
        "ccps": [2, 3],
        "ccp_labels": {2: "Test fill weight (g)", 3: "Target fill weight per MMP spec (g)"},
        "notes_required": False,
      },
      {
        "id": "capping_sealing",
        "name": "Capping & Sealing",
        "steps": [
          "Confirm all units are capped securely — no cross-threading",
          "Apply tamper-evident seal or band if required for this SKU",
          "Wipe exterior of each unit clean — no oil residue on outside",
          "Place into individual unit packaging (child-resistant blister, box, or tube)",
          "Confirm packaging is correctly assembled and child-resistant mechanism works",
        ],
        "ccps": [],
        "ccp_labels": {},
        "notes_required": False,
      },
      {
        "id": "qc_sample",
        "name": "QC Sample Check",
        "steps": [
          "Pull QC sample: minimum 3 units from run",
          "Weigh each QC unit — confirm fill weight within tolerance",
          "Visually inspect for leaks, threading issues, cleanliness",
          "Activate each QC unit briefly — confirm oil flow and vapor production",
          "Record QC results — pass or flag for investigation",
          "Record total approved units and rejected/waste units",
          "Confirm UID tag remains with batch",
        ],
        "ccps": [0],
        "ccp_labels": {0: "QC unit weights (g) — list all three"},
        "notes_required": True,
      },
      {
        "id": "packaging",
        "name": "Packaging & Labeling",
        "steps": [
          "Apply batch label to each outer package — verify all required fields: Product Name, Batch#, UID#, Mfg Date, Exp Date, THC%, net weight",
          "Confirm 'Contains' allergen statement if applicable",
          "Inspect label legibility on 5 sample units before full batch labeling",
          "Box into outer cases — confirm case count",
          "Record total packaged unit count",
        ],
        "ccps": [4],
        "ccp_labels": {4: "Total packaged units"},
        "notes_required": False,
      },
      {
        "id": "sanitation",
        "name": "Post-Run Sanitation",
        "steps": [
          "VapeJet: flush all needles, reservoirs, oil lines, tanks with 70–99% ISO-alcohol",
          "Wipe all exposed VapeJet surfaces with ISO-alcohol",
          "Wipe all tabletop counters and surfaces with 70–99% ISO-alcohol",
          "Flush between strains — do not allow cross-contamination of different oil types",
          "Complete cleaning log entry — date, equipment, method, PPM verified, initials",
        ],
        "ccps": [],
        "ccp_labels": {},
        "notes_required": False,
      },
    ]
  },

  # ─────────────────────────────────────────────────────────────────
  # BHO BADDER / SHATTER
  # ─────────────────────────────────────────────────────────────────
  "bho_badder": {
    "label": "BHO Badder / Shatter",
    "sop_ref": "P007 / MMP-MASTER-001",
    "uom": "grams",
    "phases": [
      {
        "id": "pre_production",
        "name": "Pre-Production Setup",
        "steps": [
          "Verify UID tag is attached to source material — confirm UID matches METRC record",
          "Confirm source material weight on certified scale — record incoming weight",
          "Verify all extraction equipment is clean, sanitized, and free of residue from previous run",
          "All tabletop counters and surfaces: 70–99% ISO-alcohol",
          "Confirm work area ventilation is adequate for BHO extraction",
          "Confirm solvent (butane) supply is adequate for this batch",
          "Gloves and eye protection on — maintain throughout extraction",
          "Work area is free of clutter — only items for this run present",
          "Complete allergen pre-run clearance check",
        ],
        "ccps": [1],
        "ccp_labels": {1: "Source material incoming weight (g)"},
        "notes_required": False,
      },
      {
        "id": "material_receipt",
        "name": "Material Receipt & UID Verification",
        "steps": [
          "Confirm source material UID tag matches the UID on the METRC transfer record",
          "Inspect source material: no visible mold, no foreign material, correct strain",
          "Record source material strain, weight, and LOT/batch from originating transfer",
          "Source material remains labeled with UID and batch info at all times during extraction",
        ],
        "ccps": [],
        "ccp_labels": {},
        "notes_required": False,
      },
      {
        "id": "extraction",
        "name": "Extraction",
        "steps": [
          "Load material into extraction vessel per established protocol for this equipment",
          "Run extraction — monitor pressure and temperature throughout",
          "Collect crude extract into clean, pre-weighed collection vessel",
          "Weigh crude extract — record crude yield weight",
          "Calculate crude extraction efficiency: (crude yield ÷ input material) × 100",
          "Proceed to purging immediately — do not allow crude to degrade",
        ],
        "ccps": [3, 4],
        "ccp_labels": {3: "Crude extract weight (g)", 4: "Crude extraction % yield"},
        "notes_required": False,
      },
      {
        "id": "purging",
        "name": "Purging",
        "steps": [
          "Transfer crude extract to vacuum oven — spread evenly on parchment",
          "Set vacuum oven to appropriate temperature and pressure for this product type",
          "Purge for required duration — do not rush this step (residual solvent risk)",
          "Flip/work material at appropriate intervals per protocol",
          "Monitor consistency — badder should have appropriate texture, shatter should be clear",
          "Final weight after purging — record post-purge weight",
          "Verify residual solvent reduction per protocol — note purge duration and conditions",
          "For badder: whip to appropriate consistency if required",
        ],
        "ccps": [5, 6],
        "ccp_labels": {5: "Post-purge weight (g)", 6: "Purge duration (hours) and temperature (°F)"},
        "notes_required": True,
      },
      {
        "id": "qc_yield",
        "name": "QC & Yield Verification",
        "steps": [
          "Calculate total yield: (post-purge weight ÷ source material weight) × 100",
          "Visually inspect product: color, consistency, absence of foreign material or contamination",
          "Confirm product meets visual quality standards for this SKU",
          "Confirm UID tag remains with all product throughout",
          "Weigh final batch quantity for METRC package creation",
          "Record any deviations in deviation log",
        ],
        "ccps": [0, 4],
        "ccp_labels": {0: "Total yield % (calculated)", 4: "Final batch weight for packaging (g)"},
        "notes_required": False,
      },
      {
        "id": "packaging",
        "name": "Packaging & Labeling",
        "steps": [
          "Confirm glass containers are clean and free of residue",
          "Fill containers to target weight — verify on certified scale (.001g precision)",
          "Seal containers immediately after filling",
          "Apply UID label and batch label to each container",
          "Verify all required label fields: Product Name, Batch#, UID#, Mfg Date, Exp Date, THC%, net weight",
          "Place sealed containers in temperature-controlled storage",
          "Record total packaged unit count",
        ],
        "ccps": [1, 6],
        "ccp_labels": {1: "Container fill weight (g)", 6: "Total packaged units"},
        "notes_required": False,
      },
      {
        "id": "sanitation",
        "name": "Post-Run Sanitation",
        "steps": [
          "Clean all extraction equipment with ISO-alcohol — flush all lines and vessels",
          "Clean vacuum oven surfaces — remove all residue",
          "Wipe all tabletop counters and surfaces with 70–99% ISO-alcohol",
          "Dispose of all single-use materials (parchment, filters) appropriately",
          "Complete cleaning log entry — date, equipment, method, PPM, initials",
        ],
        "ccps": [],
        "ccp_labels": {},
        "notes_required": False,
      },
    ]
  },
}


def detect_product_family(item_name: str, category: str = "") -> str:
    """
    Maps a product name / category to a BPR phase family key.
    Returns the key or None if not recognized.
    """
    n = (item_name or "").lower()
    c = (category or "").lower()

    if "live rosin" in n and "vape" not in n and "aio" not in n:
        return "live_rosin"
    if "bho badder" in n or "bho shatter" in n:
        return "bho_badder"
    if "gummies" in n or "asteroids" in n or "fruit snack" in n:
        return "gummies"
    if "tempo" in n or "aio" in n or "distillate" in n or "510" in n or "vape" in n or "rosin vape" in n:
        return "vapes"

    # category fallback
    if "concentrate" in c or "rosin" in c:
        return "live_rosin"
    if "vape" in c or "cartridge" in c:
        return "vapes"
    if "edible" in c or "gummy" in c:
        return "gummies"

    return None
