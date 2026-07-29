// bprSectionRows.js — Section 4 (equipment) & Section 5 (sanitation) row labels
// per product family, for the cell-mapped standardized BPRs.
//
// These are the fixed template rows the operator fills in the app. The BACKEND
// cell map (buildStandardBPRCellMap in BPR.gs) owns the SHEET positions — this
// file only owns the human-readable labels and the row NUMBER, which must match
// the sheet order 1:1 (equipment row 1 → EQUIP1 → sheet row 48, etc.).
//
// Keyed by product_family (the value BPRForm reads from bprData.family). Wash and
// multi-session families are deliberately absent — they have their own dedicated
// UI (SanitationLogWash) and don't use this panel.
//
// Equipment row:   { row, name }
// Sanitation row:  { row, name, method, target }   (method/target are read-only
//                  reference text pulled straight from the template)
//
// ── TO ADD A PRODUCT: copy a block, change the key to its product_family, and
//    transcribe its Section 4 and Section 5 rows from the master BPR workbook.
//    Standard tabs have 9 equipment / 10 sanitation rows; the two nano tabs have
//    12 / 11 (the backend cell map already shifts their sheet positions).

export const BPR_SECTION_ROWS = {
  // ── GUMMIES (BPR-GUM-001) — standard 9 / 10 ────────────────────────────────
  gummies: {
    equipment: [
      { row: 1, name: "Burner / Cooktop" },
      { row: 2, name: "Cooking Vessel / Pot" },
      { row: 3, name: "Thermometer (cooking)" },
      { row: 4, name: "Production Scale (certified)" },
      { row: 5, name: "Truffly Hopper / Dispenser" },
      { row: 6, name: "Silicone Molds (144-cavity)" },
      { row: 7, name: "Metal Cooling Trays" },
      { row: 8, name: "Band Sealer" },
      { row: 9, name: "Litmus / ppm Tester" },
    ],
    sanitation: [
      { row: 1,  name: "Cooking Vessel / Pot",                       method: "Hot water + soap → chlorine sanitizer", target: "200 ppm" },
      { row: 2,  name: "Silicone Molds (water ONLY — no sanitizer)", method: "Hot water + rinse → air dry",           target: "N/A — water" },
      { row: 3,  name: "Stainless Utensils / Spoons",                method: "Hot water + soap → ISO-Alcohol",        target: "ISO-Alcohol" },
      { row: 4,  name: "Truffly Hopper / Dispenser",                 method: "Hot water + soap → air dry",            target: "200 ppm" },
      { row: 5,  name: "Metal Cooling Trays",                        method: "Hot water + soap → sanitize",           target: "200 ppm" },
      { row: 6,  name: "Band Sealer",                                method: "Damp cloth → ISO-Alcohol wipe",         target: "ISO-Alcohol" },
      { row: 7,  name: "Production tabletops",                       method: "ISO-Alcohol or sanitizer bucket",       target: "200 ppm" },
      { row: 8,  name: "Scale / weighing surface",                   method: "New parchment paper",                   target: "N/A" },
      { row: 9,  name: "Sanitation solution (replace every 4 hrs)",  method: "Fresh chlorine solution",               target: "200 ppm" },
      { row: 10, name: "Reserve",                                    method: "",                                      target: "" },
    ],
  },

  // ── PUNCH CHOCOLATE (BPR-CHO-001, standard) — 9 / 10 ───────────────────────
  punch_chocolate: {
    equipment: [
      { row: 1, name: "Chocolate Temper Machine" },
      { row: 2, name: "Temperature Gun" },
      { row: 3, name: "Acrylic Molds (15-cavity)" },
      { row: 4, name: "Cooling Tunnel (Chiller)" },
      { row: 5, name: "Ilapak Carrera 500 Foil Wrapper" },
      { row: 6, name: "Videojet Printer" },
      { row: 7, name: "Production Scale (certified)" },
      { row: 8, name: "Foot Pedal Dispensing Unit" },
      { row: 9, name: "Reserve" },
    ],
    sanitation: [
      { row: 1,  name: "Temper Machine (BONE DRY — no moisture residue)", method: "Wash + air dry completely",       target: "N/A — dry only" },
      { row: 2,  name: "Acrylic Molds (BONE DRY)",                        method: "Wash + air dry completely",       target: "N/A — dry only" },
      { row: 3,  name: "Cooling Tunnel",                                  method: "Wash + air dry / inspect belt",   target: "200 ppm" },
      { row: 4,  name: "Ilapak Carrera 500 — metal tracks",              method: "Wash + sanitize",                 target: "200 ppm" },
      { row: 5,  name: "Ilapak conveyor belt",                            method: "Scrape → wash → re-oil chain",    target: "N/A — re-oil" },
      { row: 6,  name: "Videojet printer conveyor",                       method: "ISO-Alcohol wipe",                target: "ISO-Alcohol" },
      { row: 7,  name: "Production tabletops",                            method: "ISO-Alcohol or sanitizer bucket", target: "200 ppm" },
      { row: 8,  name: "Packaging tabletops",                             method: "ISO-Alcohol or sanitizer bucket", target: "200 ppm" },
      { row: 9,  name: "Scale / weighing surface",                        method: "New parchment paper",             target: "N/A" },
      { row: 10, name: "Sanitation solution (replace every 4 hrs)",       method: "Fresh chlorine solution",         target: "200 ppm" },
    ],
  },

  // ── NANO tabs (BPR-LQD / BPR-DNANO) — 12 / 11, identical equipment/surfaces ─
  // The backend cell map already shifts these sheet positions (S5→62, S8→103).
  liquidabs: nanoRows(),
  nano_isolate: nanoRows(),
};

function nanoRows() {
  return {
    equipment: [
      { row: 1,  name: "Ultrasonic processor / generator (20 kHz)" },
      { row: 2,  name: "Sonotrode / probe (Ti-6Al-4V) — WEAR PART" },
      { row: 3,  name: "Jacketed process vessel" },
      { row: 4,  name: "Recirculating chiller" },
      { row: 5,  name: "High-shear rotor/stator mixer (pre-emulsion)" },
      { row: 6,  name: "Calibrated probe thermocouple / in-line temp sensor" },
      { row: 7,  name: "Production scale (certified, §17221)" },
      { row: 8,  name: "pH meter" },
      { row: 9,  name: "Particle size analyzer (DLS) or calibrated turbidimeter" },
      { row: 10, name: "Filling pump / peristaltic filler" },
      { row: 11, name: "RO / purified water system" },
      { row: 12, name: "Container sealing / capping equipment" },
    ],
    sanitation: [
      { row: 1,  name: "Jacketed process vessel (product contact)", method: "Alkaline detergent → potable rinse → sanitizer → RO rinse", target: "200 ppm" },
      { row: 2,  name: "Sonotrode / probe",                         method: "70-99% ISO-Alcohol; autoclave per manual if applicable",   target: "N/A" },
      { row: 3,  name: "Transfer lines / flow cell / valves",       method: "Alkaline detergent → potable rinse → sanitizer → RO rinse", target: "200 ppm" },
      { row: 4,  name: "Rotor/stator mixing head",                  method: "Alkaline detergent → sanitizer → air dry",                 target: "200 ppm" },
      { row: 5,  name: "Filling pump, tubing, and nozzle",          method: "Sanitizer flush → RO rinse; or new sterile tubing",        target: "200 ppm" },
      { row: 6,  name: "pH probe and thermocouple",                 method: "RO rinse → 70% ISO-Alcohol wipe → RO rinse",               target: "N/A" },
      { row: 7,  name: "Containers / closures",                     method: "Food-grade sealed cases — do not rinse unless required",   target: "N/A" },
      { row: 8,  name: "Production tabletops / wet work surfaces",   method: "70-99% ISO-Alcohol or sanitizer bucket",                   target: "200 ppm" },
      { row: 9,  name: "Scale / weighing surface",                  method: "New parchment paper",                                      target: "N/A" },
      { row: 10, name: "Sanitizer solution",                        method: "Fresh chlorine solution",                                  target: "200 ppm" },
      { row: 11, name: "Floor drains / wet area (WET-PROCESS)",      method: "Detergent scrub → sanitizer",                              target: "200 ppm" },
    ],
  };
}
