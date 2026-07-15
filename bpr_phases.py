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
  "dr_norms_cookie": {
    "label": "Dr. Norm's Cookie",
    "sop_ref": "MMP-DN-CC / RV / SD / PSB / PBCC v1.0",
    "uom": "units",
    "phases": [
        {
            "id": "pre_production",
            "name": "Pre-Production Setup",
            "steps": [
                "Allergen pre-run clearance signed \u2014 confirm allergens this SKU vs prior run. If different: full equipment clean-out required.",
                "Confirm freezer is at or below 0F \u2014 required for dough freeze step",
                "Verify scale seal is current \u2014 record scale Asset ID on BPR",
                "Confirm cannabis input METRC UID entered on BPR before starting",
                "THC Distillate COA confirmed \u2014 record mg/g THC from COA",
                "Calculate total mg THC required for batch \u2014 record calculation on BPR",
                "All ingredients pulled and lot numbers recorded on BPR",
                "Equipment inspected \u2014 clean, undamaged, no foreign material"
            ],
            "ccps": [
                1,
                4
            ],
            "ccp_labels": {
                "1": "Freezer Temp (F) \u2014 must be \u2264 0F",
                "4": "COA THC Potency (mg/g)"
            },
            "ccp_specs": {
                "1": {
                    "unit": "F",
                    "min": -20,
                    "max": 0
                },
                "4": {
                    "unit": "mg/g",
                    "min": 1,
                    "max": 9999
                }
            },
            "corrective_actions": {
                "1": "If >0F: do not use freezer. Contact facilities.",
                "4": "No COA: halt production. Contact QA sam@punchedibles.com."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "infusion",
            "name": "Infusion \u2014 Distillate Prep",
            "steps": [
                "Melt carrier (coconut oil or butter per SKU) on induction hot plate until fully melted",
                "Warm THC distillate on separate induction stove",
                "CCP-1: Verify distillate temp reaches 310\u2013330F before adding to carrier \u2014 record temp",
                "Add calculated distillate to carrier via syringe \u2014 record exact amount used",
                "Transfer to mason jar. Shake vigorously \u2014 open lid to release pressure \u2014 reshake",
                "Return jar to 310\u2013330F for 10 more min \u2014 final shake. Record final temp.",
                "Cool jars to room temp 68\u201375F before transferring to mixing team"
            ],
            "ccps": [
                2,
                3,
                5,
                6
            ],
            "ccp_labels": {
                "2": "Distillate Temp (F) \u2014 must be 310\u2013330F",
                "3": "Distillate Amount Added (g)",
                "5": "Final Blend Temp (F) \u2014 must be 310\u2013330F",
                "6": "Blend Temp at Transfer (F) \u2014 must be 68\u201375F"
            },
            "ccp_specs": {
                "2": {
                    "unit": "F",
                    "min": 310,
                    "max": 330
                },
                "3": {
                    "unit": "g",
                    "min": 1,
                    "max": 9999
                },
                "5": {
                    "unit": "F",
                    "min": 310,
                    "max": 330
                },
                "6": {
                    "unit": "F",
                    "min": 68,
                    "max": 75
                }
            },
            "corrective_actions": {
                "2": "<310F: extend heat, re-verify. >330F: reduce heat. Log deviation if OOS after 15 min.",
                "3": "Record actual. Do not estimate. Any variance from calculation: note on BPR.",
                "5": "Same as CCP-1. Log final temp on BPR regardless.",
                "6": "If >75F: continue cooling. Do not add warm blend to mixer."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "mixing",
            "name": "Mixing \u2014 Dough Preparation",
            "steps": [
                "Soften butter/vegan butter in microwave (do NOT fully melt). Add butter and sugars to Hobart.",
                "Mix: L1x10s scrape | L2x10s scrape | L3x20s scrape. Full scrape after every speed.",
                "CCP-2: Add THC/carrier blend to mixer \u2014 verify blend at room temp 68\u201375F. Record temp.",
                "Scrape jar and lid to recover ALL carrier. Mix: L1x10s scrape | L2x20s scrape | L3x20s scrape | L4x10s. Re-scrape.",
                "Add eggs (or egg replacer per SKU) and vanilla. Mix: L1x10s scrape | L2x10s scrape | L3x15s scrape",
                "Add dry ingredients per MMP (flour, leavening, salt, SKU-specific). Mix: L1x10s scrape | L2x10s scrape | L3x30s scrape | L4x60s scrape",
                "Add inclusions (chips, pieces, nuts per MMP). Mix: L1x10s scrape | L2x10s | L3x15s"
            ],
            "ccps": [
                2
            ],
            "ccp_labels": {
                "2": "Blend Temp at Mixer Addition (F) \u2014 must be 68\u201375F"
            },
            "ccp_specs": {
                "2": {
                    "unit": "F",
                    "min": 68,
                    "max": 75
                }
            },
            "corrective_actions": {
                "2": "If >75F: stop, allow to cool, re-verify. Do not add warm blend to softened butter."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "forming",
            "name": "Forming \u2014 Freeze and Deposit",
            "steps": [
                "Spread dough onto parchment-lined pans. Label parchment with SKU and batch ID.",
                "Freeze minimum 2 hours (standard) or overnight (butter-carrier SKUs: SD, PSB, PBCC). Dough must be firm to touch.",
                "Set up Formatic depositor. Run minimum 30 calibration doughballs before production.",
                "CCP-3: Pre-run calibration weight \u2014 record average weight of 30 calibration doughballs",
                "Process dough through depositor. Keep hopper full at all times \u2014 empty hopper causes weight variability.",
                "CCP-4: In-process weight check \u2014 verify 1 in every 10 doughballs is within spec. Record weight.",
                "Record total units formed \u2014 yield count"
            ],
            "ccps": [
                1,
                3,
                5,
                6
            ],
            "ccp_labels": {
                "1": "Freeze Duration (hours) \u2014 min 2 hrs standard / overnight for butter-carrier SKUs",
                "3": "Calibration Doughball Weight (g) \u2014 must be within SKU spec",
                "5": "In-Process Unit Weight (g) \u2014 must be within SKU spec",
                "6": "Units Formed (yield count)"
            },
            "ccp_specs": {
                "1": {
                    "unit": "hours",
                    "min": 2,
                    "max": 16
                },
                "3": {
                    "unit": "g",
                    "min": 7.8,
                    "max": 13.0
                },
                "5": {
                    "unit": "g",
                    "min": 7.8,
                    "max": 13.0
                },
                "6": {
                    "unit": "units",
                    "min": 1,
                    "max": 9999
                }
            },
            "corrective_actions": {
                "1": "If not firm after min time: extend in 30-min increments. Do not run soft dough.",
                "3": "OOS: adjust depositor, re-run 10 doughballs, re-verify. Do not start production until in-spec.",
                "5": "OOS: check last 10 units. If >3 OOS: stop, recalibrate, re-check. Log deviation.",
                "6": "Yield%: Actual / Theoretical x 100. Outside 95-105%: Deviation Log."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "baking",
            "name": "Baking",
            "steps": [
                "Preheat oven to correct temp per SKU: standard cookies 300F | Pecan Shortbread 350F. Verify oven temp.",
                "Load pans. Record start time. Bake per SKU: standard 10 min | Pecan Shortbread 14 min. Record end time.",
                "Remove pans from oven. Transfer to cooling racks. Do not stack hot pans."
            ],
            "ccps": [
                0,
                1
            ],
            "ccp_labels": {
                "0": "Oven Temp (F)",
                "1": "Bake Time (minutes)"
            },
            "ccp_specs": {
                "0": {
                    "unit": "F",
                    "min": 295,
                    "max": 355
                },
                "1": {
                    "unit": "minutes",
                    "min": 9,
                    "max": 15
                }
            },
            "corrective_actions": {
                "0": "Cannot reach set temp: contact facilities. Do not bake.",
                "1": "Visibly over-baked: remove, assess, log deviation."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "cooling",
            "name": "Cooling",
            "steps": [
                "Leave product on cooling racks until the FOLLOWING DAY. Do not package warm.",
                "Verify product is fully cooled \u2014 no warmth to touch before proceeding to packaging."
            ],
            "ccps": [],
            "ccp_labels": {},
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "packaging",
            "name": "Packaging and Labeling",
            "steps": [
                "CCP-5: Post-bake unit weight \u2014 verify 1 in every 10 units within spec. Record weight.",
                "Record total units packaged \u2014 final yield count",
                "Package per SKU config: 10mg = 10 cookies/bag | 100mg MAX = 1 cookie + cutting card/bag. Heat seal.",
                "Verify heat seal integrity \u2014 100% of bags. No open seals.",
                "Apply compliant label \u2014 verify: potency/serving, total cannabinoids/package, serving size, net weight, DCC# DCC-10003615, METRC UID, universal symbol, warning statements, mfg date.",
                "ALLERGEN CHECK: Confirm allergen declarations on label match PQP Section 3 for this SKU.",
                "Assign finished goods METRC UID \u2014 enter on BPR and tag packaging.",
                "Record 2 retention samples \u2014 label with SKU, batch ID, METRC UID, mfg date. Store minimum 1 year."
            ],
            "ccps": [
                0,
                1
            ],
            "ccp_labels": {
                "0": "Post-Bake Unit Weight (g) \u2014 must be within SKU spec",
                "1": "Final Packaged Yield (units)"
            },
            "ccp_specs": {
                "0": {
                    "unit": "g",
                    "min": 7.8,
                    "max": 12.5
                },
                "1": {
                    "unit": "units",
                    "min": 1,
                    "max": 9999
                }
            },
            "corrective_actions": {
                "0": "OOS: set aside. If >5% OOS: investigate depositor calibration and bake shrinkage. Log deviation.",
                "1": "Outside 95-105%: Deviation Log required."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator",
                "QA Supervisor"
            ]
        },
        {
            "id": "qc_release",
            "name": "QC Batch Release",
            "steps": [
                "All BPR phases signed off with concurrent timestamps \u2014 no back-fill",
                "All ingredient lot numbers recorded on BPR",
                "Cannabis input METRC UID and finished goods METRC UID both entered",
                "COA received from licensed 3rd-party lab \u2014 record lab name and sample ID",
                "CCP-6: COA potency within +/-20% of label claim. 10mg: accept 8-12mg. 100mg: accept 80-120mg.",
                "All open deviations have documented CAPA",
                "Scale Calibration Log verified current",
                "BATCH RELEASE DECISION \u2014 mark RELEASED or ON HOLD with reason"
            ],
            "ccps": [
                4
            ],
            "ccp_labels": {
                "4": "COA THC (mg/serving) \u2014 10mg SKU: 8\u201312mg | 100mg SKU: 80\u2013120mg"
            },
            "ccp_specs": {
                "4": {
                    "unit": "mg",
                    "min": 8,
                    "max": 120
                }
            },
            "corrective_actions": {
                "4": "OOS: HOLD batch. Consult QA. Recall assessment may be required per DCC \u00a726120."
            },
            "notes_required": True,
            "sign_off_roles": [
                "QA Supervisor"
            ]
        }
    ]
  },

    "dr_norms_cookie_nano": {
    "label": "Dr. Norm's Cookie \u2014 NANO (Cookies & Cream NANO only)",
    "sop_ref": "MMP-DN-CN-10 / CN-100 v1.0",
    "uom": "units",
    "phases": [
        {
            "id": "pre_production",
            "name": "Pre-Production Setup",
            "steps": [
                "NANO FORMAT: Confirm this is Cookies and Cream NANO (CN-10 or CN-100). Bake time = 11.5 min \u2014 NOT 10 min.",
                "Allergen pre-run clearance signed (Oreo contains MILK, WHEAT, SOY \u2014 confirm prior run allergens)",
                "Confirm freezer is at or below 0F",
                "Verify scale seal is current \u2014 record scale Asset ID on BPR",
                "Confirm cannabis input METRC UID entered on BPR before starting",
                "THC Distillate COA confirmed \u2014 record mg/g THC",
                "Calculate total mg THC for batch \u2014 record on BPR",
                "All ingredients pulled and lot numbers recorded",
                "Equipment inspected \u2014 clean, undamaged, no foreign material"
            ],
            "ccps": [
                2,
                5
            ],
            "ccp_labels": {
                "2": "Freezer Temp (F) \u2014 must be \u2264 0F",
                "5": "COA THC Potency (mg/g)"
            },
            "ccp_specs": {
                "2": {
                    "unit": "F",
                    "min": -20,
                    "max": 0
                },
                "5": {
                    "unit": "mg/g",
                    "min": 1,
                    "max": 9999
                }
            },
            "corrective_actions": {
                "2": "If >0F: do not use freezer. Contact facilities.",
                "5": "No COA: halt. Contact QA sam@punchedibles.com."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "infusion",
            "name": "Infusion \u2014 Distillate Prep",
            "steps": [
                "Melt coconut oil (carrier) on induction hot plate until fully melted",
                "Warm THC distillate on separate induction stove",
                "CCP-1: Verify distillate temp 310\u2013330F before adding to carrier \u2014 record temp",
                "Add calculated distillate to carrier via syringe \u2014 record exact amount used",
                "Transfer to mason jar. Shake vigorously \u2014 open lid to release pressure \u2014 reshake",
                "Return jar to 310\u2013330F for 10 more min \u2014 final shake. Record final temp.",
                "Cool jars to room temp 68\u201375F before use in NANO mixing phase"
            ],
            "ccps": [
                2,
                3,
                5,
                6
            ],
            "ccp_labels": {
                "2": "Distillate Temp (F) \u2014 must be 310\u2013330F",
                "3": "Distillate Amount Added (g)",
                "5": "Final Blend Temp (F) \u2014 must be 310\u2013330F",
                "6": "Blend Temp after cooling (F) \u2014 must be 68\u201375F before NANO step"
            },
            "ccp_specs": {
                "2": {
                    "unit": "F",
                    "min": 310,
                    "max": 330
                },
                "3": {
                    "unit": "g",
                    "min": 1,
                    "max": 9999
                },
                "5": {
                    "unit": "F",
                    "min": 310,
                    "max": 330
                },
                "6": {
                    "unit": "F",
                    "min": 68,
                    "max": 75
                }
            },
            "corrective_actions": {
                "2": "<310F: extend heat. >330F: reduce heat. Log deviation if OOS after 15 min.",
                "3": "Record actual. Do not estimate.",
                "5": "Same as CCP-1.",
                "6": "If >75F: continue cooling before NANO addition."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "mixing",
            "name": "Mixing \u2014 Dough Preparation (NANO Process)",
            "steps": [
                "Soften butter in microwave. Add butter and sugars to Hobart.",
                "Mix butter and sugars: L1x10s | L2x20s | L3x30s. Scrape after each.",
                "NANO CCP-2: Add THC/oil blend at EXACTLY 109F \u2014 measure temp immediately before pouring. Record temp.",
                "Mix with blend: L1x30s scrape | L2x40s scrape | L3x90s scrape. Full scrape after every speed.",
                "Add eggs and vanilla. Mix: L1x10s scrape | L2x40s scrape | L3x60s scrape",
                "Add flour, baking soda, salt. Mix: L1x40s scrape | L2x60s scrape | L3x90s scrape",
                "Add Oreo cookie pieces. Mix: L1x20s scrape | L2x30s scrape"
            ],
            "ccps": [
                2
            ],
            "ccp_labels": {
                "2": "NANO Blend Temp at Mixer Addition (F) \u2014 must be 104\u2013114F (target 109F)"
            },
            "ccp_specs": {
                "2": {
                    "unit": "F",
                    "min": 104,
                    "max": 114
                }
            },
            "corrective_actions": {
                "2": "NANO emulsification CCP \u2014 unique to this SKU. <104F: rewarm to 109F, re-verify. >114F: cool, re-verify. Deviation from 109F affects cannabinoid distribution."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "forming",
            "name": "Forming \u2014 Freeze and Deposit",
            "steps": [
                "Spread dough onto parchment-lined pans. Label parchment with SKU and batch ID.",
                "Freeze minimum 2 hours. Dough must be firm to touch.",
                "Set up Formatic depositor. Run minimum 30 calibration doughballs before production.",
                "CCP-3: Pre-run calibration weight \u2014 record average of 30 calibration doughballs",
                "Process dough through depositor. Keep hopper full at all times.",
                "CCP-4: In-process weight \u2014 verify 1 in every 10 doughballs is within spec. Record weight.",
                "Record total units formed \u2014 yield count"
            ],
            "ccps": [
                1,
                3,
                5,
                6
            ],
            "ccp_labels": {
                "1": "Freeze Duration (hours) \u2014 min 2 hrs",
                "3": "Calibration Doughball Weight (g)",
                "5": "In-Process Unit Weight (g)",
                "6": "Units Formed (yield count)"
            },
            "ccp_specs": {
                "1": {
                    "unit": "hours",
                    "min": 2,
                    "max": 16
                },
                "3": {
                    "unit": "g",
                    "min": 7.8,
                    "max": 13.0
                },
                "5": {
                    "unit": "g",
                    "min": 7.8,
                    "max": 13.0
                },
                "6": {
                    "unit": "units",
                    "min": 1,
                    "max": 9999
                }
            },
            "corrective_actions": {
                "1": "If not firm: extend in 30-min increments. Do not run soft dough.",
                "3": "OOS: adjust depositor, re-run 10 doughballs, re-verify.",
                "5": "OOS: check last 10 units. If >3 OOS: stop, recalibrate. Log deviation.",
                "6": "Outside 95-105%: Deviation Log."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "baking",
            "name": "Baking",
            "steps": [
                "Preheat oven to 300F. Verify oven temp.",
                "Load pans. Record start time. Bake EXACTLY 11 minutes 30 seconds \u2014 NOT the standard 10-min time. Record end time.",
                "Remove pans. Transfer to cooling racks. Do not stack hot pans."
            ],
            "ccps": [
                0,
                1
            ],
            "ccp_labels": {
                "0": "Oven Temp (F) \u2014 must be 295\u2013305F",
                "1": "Bake Time (minutes) \u2014 must be 11\u201312 min"
            },
            "ccp_specs": {
                "0": {
                    "unit": "F",
                    "min": 295,
                    "max": 305
                },
                "1": {
                    "unit": "minutes",
                    "min": 11,
                    "max": 12
                }
            },
            "corrective_actions": {
                "0": "Cannot reach 300F: contact facilities.",
                "1": "NANO requires 11.5 min \u2014 do not use standard 10-min time."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "cooling",
            "name": "Cooling",
            "steps": [
                "Leave product on cooling racks until the FOLLOWING DAY. Do not package warm.",
                "Verify product is fully cooled \u2014 no warmth to touch before proceeding."
            ],
            "ccps": [],
            "ccp_labels": {},
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "packaging",
            "name": "Packaging and Labeling",
            "steps": [
                "CCP-5: Post-bake unit weight \u2014 verify 1 in every 10 units within spec. Record weight.",
                "Record total units packaged \u2014 final yield count",
                "Package per SKU: 10mg = 10 cookies/bag | 100mg MAX = 1 cookie + cutting card/bag. Heat seal.",
                "Verify heat seal integrity \u2014 100% of bags. No open seals.",
                "Apply compliant label \u2014 verify all required elements including DCC# DCC-10003615, METRC UID.",
                "ALLERGEN CHECK: Confirm MILK, WHEAT, SOY declarations on label (Oreo allergens).",
                "Assign finished goods METRC UID \u2014 enter on BPR and tag packaging.",
                "Record 2 retention samples \u2014 label with SKU, batch ID, METRC UID, mfg date."
            ],
            "ccps": [
                0,
                1
            ],
            "ccp_labels": {
                "0": "Post-Bake Unit Weight (g)",
                "1": "Final Packaged Yield (units)"
            },
            "ccp_specs": {
                "0": {
                    "unit": "g",
                    "min": 7.8,
                    "max": 12.5
                },
                "1": {
                    "unit": "units",
                    "min": 1,
                    "max": 9999
                }
            },
            "corrective_actions": {
                "0": "OOS: set aside. >5% OOS: investigate. Log deviation.",
                "1": "Outside 95-105%: Deviation Log."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator",
                "QA Supervisor"
            ]
        },
        {
            "id": "qc_release",
            "name": "QC Batch Release",
            "steps": [
                "All BPR phases signed off with concurrent timestamps \u2014 no back-fill",
                "All ingredient lot numbers recorded",
                "Cannabis input METRC UID and finished goods METRC UID both entered",
                "COA received from licensed 3rd-party lab \u2014 record lab name and sample ID",
                "CCP-6: COA potency within +/-20% of label claim (10mg: 8-12mg | 100mg: 80-120mg)",
                "All open deviations have documented CAPA",
                "Scale Calibration Log verified current",
                "BATCH RELEASE DECISION \u2014 mark RELEASED or ON HOLD with reason"
            ],
            "ccps": [
                4
            ],
            "ccp_labels": {
                "4": "COA THC (mg/serving) \u2014 10mg: 8\u201312mg | 100mg: 80\u2013120mg"
            },
            "ccp_specs": {
                "4": {
                    "unit": "mg",
                    "min": 8,
                    "max": 120
                }
            },
            "corrective_actions": {
                "4": "OOS: HOLD. Consult QA. Recall assessment may be required."
            },
            "notes_required": True,
            "sign_off_roles": [
                "QA Supervisor"
            ]
        }
    ]
  },

    "dr_norms_rkt": {
    "label": "Dr. Norm's Rice Krispy Treat (all flavors)",
    "sop_ref": "MMP-DN-RKT-O / FP / CH / CTC / VB / MRKT v1.0",
    "uom": "units",
    "phases": [
        {
            "id": "pre_production",
            "name": "Pre-Production Setup",
            "steps": [
                "Verify scale seal is current \u2014 record scale Asset ID",
                "ALLERGEN: RKT allergen profile differs by flavor/cereal. Confirm this SKU's allergens vs prior run. Sign allergen pre-run clearance.",
                "Confirm cannabis input METRC UID entered on BPR",
                "THC Distillate COA confirmed \u2014 record mg/g THC",
                "Calculate total mg THC for batch: 50 bars x 100mg = 5,000mg THC. Record on BPR.",
                "All ingredients pulled \u2014 lot numbers recorded. Verify correct cereal type for this RKT flavor.",
                "Inspect equipment: hot plate, pot, spatulas, Hobart bowl, pressing machine, cutting machine."
            ],
            "ccps": [
                3
            ],
            "ccp_labels": {
                "3": "COA THC Potency (mg/g)"
            },
            "ccp_specs": {
                "3": {
                    "unit": "mg/g",
                    "min": 1,
                    "max": 9999
                }
            },
            "corrective_actions": {
                "3": "No COA: halt. Contact QA."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "infusion",
            "name": "Infusion \u2014 Butter + Cannabis",
            "steps": [
                "Add salted butter to pot on induction hot plate. Melt fully.",
                "Add calculated THC distillate to fully melted butter. Begin continuous stirring.",
                "CCP-1a: Record hot plate temp at 1-minute mark of continuous stirring",
                "CCP-1b: Record hot plate temp at 2-minute mark \u2014 must maintain 225\u2013250F for full 2 min minimum",
                "Record distillate amount added \u2014 must match BPR Section 4 calculation"
            ],
            "ccps": [
                2,
                3,
                4
            ],
            "ccp_labels": {
                "2": "Infusion Temp @ 1 min (F) \u2014 must be 225\u2013250F",
                "3": "Infusion Temp @ 2 min (F) \u2014 must be 225\u2013250F",
                "4": "Distillate Amount Added (g)"
            },
            "ccp_specs": {
                "2": {
                    "unit": "F",
                    "min": 225,
                    "max": 250
                },
                "3": {
                    "unit": "F",
                    "min": 225,
                    "max": 250
                },
                "4": {
                    "unit": "g",
                    "min": 1,
                    "max": 9999
                }
            },
            "corrective_actions": {
                "2": "<225F: increase heat. >250F: reduce heat immediately. Butter browning/smoking: remove from heat, assess, deviation log.",
                "3": "Both readings must be in spec. If either OOS: extend hold, re-verify, document.",
                "4": "Any variance from calculated amount: note on BPR. Do not estimate."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "marshmallow_melt",
            "name": "Marshmallow Melt",
            "steps": [
                "Add Jet-Puffed mini marshmallows to butter/cannabis mixture. Record start time.",
                "Stir continuously on heat. Do not leave unattended. Target: smooth, creamy, slightly yellowed, no lumps.",
                "CCP-2: Record melt duration. Confirm visual acceptance: smooth/creamy/yellowed/lump-free.",
                "Turn OFF heat once marshmallow mixture meets visual acceptance."
            ],
            "ccps": [
                2
            ],
            "ccp_labels": {
                "2": "Melt Duration (minutes) \u2014 target 15\u201320 min"
            },
            "ccp_specs": {
                "2": {
                    "unit": "minutes",
                    "min": 15,
                    "max": 20
                }
            },
            "corrective_actions": {
                "2": "<15 min still lumpy: continue. >20 min with lumps: 5 more min. At 25 min still lumpy: STOP. Consult QA. Deviation log."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "cereal_mix",
            "name": "Mixing \u2014 Cereal Combine",
            "steps": [
                "Add cereal (correct type per MMP for this RKT flavor) to marshmallow mixture. Stir with wooden spoon until fully coated.",
                "Transfer entire mixture to Hobart mixer bowl. Scrape pot completely.",
                "CCP-3: Mix in Hobart at Level 1 for EXACTLY 5 seconds. Stop immediately."
            ],
            "ccps": [
                2
            ],
            "ccp_labels": {
                "2": "Hobart Mix Duration (seconds) \u2014 must be 4\u20136 sec"
            },
            "ccp_specs": {
                "2": {
                    "unit": "seconds",
                    "min": 4,
                    "max": 6
                }
            },
            "corrective_actions": {
                "2": "Over-mix destroys cereal texture and causes weight inconsistency. If over-mixed: assess, document, inform QA."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "forming",
            "name": "Forming \u2014 Pan and Press",
            "steps": [
                "Pour entire mixture into full-size sheet pan. Spread evenly.",
                "CCP-4: Weigh pan on calibrated scale \u2014 TARE empty pan first. Record net weight of mixture only.",
                "Place pan in pressing machine. Press to uniform thickness.",
                "Transfer pressed pan to cooling rack. Cool overnight at room temperature \u2014 do not refrigerate."
            ],
            "ccps": [
                1
            ],
            "ccp_labels": {
                "1": "Pan Net Weight excl tare (oz) \u2014 target per SKU MMP"
            },
            "ccp_specs": {
                "1": {
                    "unit": "oz",
                    "min": 140,
                    "max": 165
                }
            },
            "corrective_actions": {
                "1": "Short of spec: add remaining mixture. Over spec: remove excess. If >5% short: investigate quantities, log deviation."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "cooling",
            "name": "Cooling",
            "steps": [
                "Cool RKT on rack at room temperature overnight. Do not refrigerate \u2014 condensation causes texture defects.",
                "Verify RKT is fully set and firm before cutting \u2014 press finger lightly to test."
            ],
            "ccps": [],
            "ccp_labels": {},
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "cut_and_weigh",
            "name": "Cutting and Weighing",
            "steps": [
                "Place cooled RKT slab in cutting machine. Cut into 50 pieces.",
                "CCP-5: Weigh EVERY individual bar. Target: 78\u201382g (80g = 100mg THC). Record each bar weight.",
                "Record total bars in spec \u2014 yield count. Target: 50 bars.",
                "Cannabis Waste Log entry \u2014 record total weight of all trimmings."
            ],
            "ccps": [
                1,
                2
            ],
            "ccp_labels": {
                "1": "Individual Bar Weight (g) \u2014 must be 78\u201382g",
                "2": "Bars in Spec / yield count \u2014 target 50 bars"
            },
            "ccp_specs": {
                "1": {
                    "unit": "g",
                    "min": 78,
                    "max": 82
                },
                "2": {
                    "unit": "bars",
                    "min": 48,
                    "max": 50
                }
            },
            "corrective_actions": {
                "1": "OOS: trim to spec (surgery). Trimmings = cannabis waste log. >3 consecutive OOS same direction: stop, investigate cutting calibration.",
                "2": "<48 bars: investigate pan weight and cutting settings. Log yield deviation."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator",
                "QA Supervisor"
            ]
        },
        {
            "id": "packaging",
            "name": "Packaging and Labeling",
            "steps": [
                "Place 1 bar per bag with cutting card. Heat seal.",
                "Verify heat seal integrity \u2014 100% of bags.",
                "Apply compliant label \u2014 verify: 100mg THC, DCC# DCC-10003615, METRC UID, universal symbol, warnings, mfg date, net weight.",
                "ALLERGEN CHECK: Verify allergen declaration matches cereal type used in THIS batch \u2014 allergens differ by RKT flavor.",
                "Assign finished goods METRC UID \u2014 enter on BPR and tag packaging.",
                "Record 2 retention samples \u2014 label with SKU, batch ID, METRC UID, mfg date."
            ],
            "ccps": [],
            "ccp_labels": {},
            "notes_required": False,
            "sign_off_roles": [
                "Operator",
                "QA Supervisor"
            ]
        },
        {
            "id": "qc_release",
            "name": "QC Batch Release",
            "steps": [
                "All phases signed off with concurrent timestamps \u2014 no back-fill",
                "Cannabis input and finished goods METRC UIDs both recorded",
                "COA received from licensed lab \u2014 record lab name and sample ID",
                "CCP-6: COA THC potency within +/-20% of 100mg label claim (accept 80\u2013120mg per bar)",
                "All cannabis waste (bar trimmings) logged on Cannabis Waste Log",
                "All open deviations have documented CAPA",
                "BATCH RELEASE DECISION \u2014 mark RELEASED or ON HOLD with reason"
            ],
            "ccps": [
                3
            ],
            "ccp_labels": {
                "3": "COA THC (mg/bar) \u2014 must be 80\u2013120mg"
            },
            "ccp_specs": {
                "3": {
                    "unit": "mg",
                    "min": 80,
                    "max": 120
                }
            },
            "corrective_actions": {
                "3": "OOS: HOLD. Consult QA. Recall assessment may be required."
            },
            "notes_required": True,
            "sign_off_roles": [
                "QA Supervisor"
            ]
        }
    ]
  },

    "dr_norms_brownie": {
    "label": "Dr. Norm's Brownie / Blondie",
    "sop_ref": "MMP-DN-VB / SCB / PBC v1.0",
    "uom": "units",
    "phases": [
        {
            "id": "pre_production",
            "name": "Pre-Production Setup",
            "steps": [
                "Verify scale seal is current \u2014 record scale Asset ID",
                "PBC-100 ONLY: Allergen Pre-Run Clearance Form MUST be signed by supervisor BEFORE ANY MIXING BEGINS. Peanut allergen \u2014 mandatory.",
                "All other SKUs: allergen pre-run clearance signed for this SKU's allergen profile.",
                "Confirm cannabis input METRC UID on BPR (PBC-100: Solventless Hash UID)",
                "THC distillate COA confirmed (or Solventless Hash COA for PBC-100) \u2014 record mg/g THC",
                "Calculate total mg THC for batch \u2014 record on BPR. QA to verify PBC-100 hash calculation.",
                "SCB-100 ONLY: Freeze caramel bits NOW \u2014 must be frozen solid before grinding. Place in freezer immediately.",
                "All ingredients pulled \u2014 lot numbers recorded. Vegan butter brand verified if VB-100.",
                "Inspect all equipment including probe thermometer \u2014 verify thermometer is working."
            ],
            "ccps": [
                4
            ],
            "ccp_labels": {
                "4": "COA THC Potency (mg/g) \u2014 or Hash COA for PBC-100"
            },
            "ccp_specs": {
                "4": {
                    "unit": "mg/g",
                    "min": 1,
                    "max": 9999
                }
            },
            "corrective_actions": {
                "4": "No COA: halt. PBC-100: Hash COA must be for this specific lot \u2014 no rolling COA."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "chocolate_melt",
            "name": "Chocolate Melt",
            "steps": [
                "Melt butter + chocolate chips in TWO BATCHES per MMP recipe. Low-medium heat.",
                "Stir continuously until smooth and fully combined. Set aside to cool before adding to mixer.",
                "PBC-100 ONLY: This melt is MINI CHOC CHIPS only \u2014 NOT Reese's pieces. Keep Reese's separate for fold-in step."
            ],
            "ccps": [],
            "ccp_labels": {},
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "infusion",
            "name": "Infusion \u2014 Butter + Cannabis",
            "steps": [
                "VB-100 ONLY: Mix soy lecithin powder fully into infusion vegan butter BEFORE adding distillate.",
                "Add THC distillate (or Solventless Hash for PBC-100) to infusion butter. Heat gently.",
                "CCP-1: Infusion butter/cannabis temp \u2014 must be 88\u201391F at point of introduction to dough. Record temp.",
                "Confirm blend is visually homogeneous \u2014 no separation or undissolved particles."
            ],
            "ccps": [
                2
            ],
            "ccp_labels": {
                "2": "Infusion Butter Temp at Introduction (F) \u2014 must be 88\u201391F"
            },
            "ccp_specs": {
                "2": {
                    "unit": "F",
                    "min": 88,
                    "max": 91
                }
            },
            "corrective_actions": {
                "2": "<88F: rewarm gently, re-verify. >91F: cool, re-verify. NEVER exceed 95F \u2014 oil separation risk. OOS after 2 attempts: halt, consult QA, Deviation Log."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "mixing",
            "name": "Mixing \u2014 Dough Preparation",
            "steps": [
                "Add chocolate/butter melt and sugars to Hobart. Mix: L1x10s | L2x20s | L3x30s. Scrape after each.",
                "CCP-2: Add infusion butter/THC blend at 88\u201391F \u2014 verify temp immediately before adding. Record temp.",
                "Mix: L1x30s scrape | L2x40s scrape | L3x60s scrape",
                "Add remaining sugars per MMP. Mix: L1x10s scrape | L2x40s scrape | L3x60s scrape",
                "Add vanilla and eggs (or egg replacer for vegan SKUs). Mix: L1x10s scrape | L2x30s scrape | L3x30s scrape",
                "Add dry ingredients per MMP (flour, leavening, salt, SKU-specific). Mix: L1x40s scrape | L2x60s scrape | L3x60s scrape",
                "Fold in inclusions per MMP (choc chips, Reese's for PBC-100). Mix: L1x30s | L2x50s scrape"
            ],
            "ccps": [
                1
            ],
            "ccp_labels": {
                "1": "Butter/THC Temp at Mixer Addition (F) \u2014 must be 88\u201391F"
            },
            "ccp_specs": {
                "1": {
                    "unit": "F",
                    "min": 88,
                    "max": 91
                }
            },
            "corrective_actions": {
                "1": "Same corrective action as CCP-1. Do not add OOS blend."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "forming",
            "name": "Forming \u2014 Freeze and Deposit",
            "steps": [
                "Spread dough onto parchment-lined pans. Label parchment with SKU and batch ID.",
                "CCP-3: Freeze dough minimum 30 min. Dough must be firm to touch but NOT frozen solid.",
                "Set up Formatic depositor with BROWNIE die (rectangle). Verify die is clean.",
                "CCP-4: Weigh EVERY brownie/blondie individually \u2014 100% weighing required. Target: 78\u201382g per unit.",
                "Record total units formed \u2014 yield count",
                "SCB-100 ONLY: Sprinkle finely ground sea salt on top of each blondie before baking. Record amount used."
            ],
            "ccps": [
                1,
                3,
                4
            ],
            "ccp_labels": {
                "1": "Freeze Duration (minutes) \u2014 min 30 min, dough firm to touch",
                "3": "Unit Weight (g) \u2014 must be 78\u201382g per brownie",
                "4": "Units Formed (yield count)"
            },
            "ccp_specs": {
                "1": {
                    "unit": "minutes",
                    "min": 30,
                    "max": 90
                },
                "3": {
                    "unit": "g",
                    "min": 78,
                    "max": 82
                },
                "4": {
                    "unit": "units",
                    "min": 1,
                    "max": 9999
                }
            },
            "corrective_actions": {
                "1": "Soft after 30 min: extend in 10-min increments. Frozen solid: temper 5\u201310 min room temp.",
                "3": "OOS: adjust or trim. Trimmings = cannabis waste log. >5% systematically OOS: stop, recalibrate, investigate.",
                "4": "Outside 95-105%: Deviation Log."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "baking",
            "name": "Baking",
            "steps": [
                "Preheat oven to 300F. Verify oven temp.",
                "Load pans. Record start time. Bake 11 min 30 sec. Record end time.",
                "Remove pans. Transfer to cooling racks. Do not stack hot pans."
            ],
            "ccps": [
                0,
                1
            ],
            "ccp_labels": {
                "0": "Oven Temp (F) \u2014 must be 295\u2013305F",
                "1": "Bake Time (minutes) \u2014 must be 11\u201312 min"
            },
            "ccp_specs": {
                "0": {
                    "unit": "F",
                    "min": 295,
                    "max": 305
                },
                "1": {
                    "unit": "minutes",
                    "min": 11,
                    "max": 12
                }
            },
            "corrective_actions": {
                "0": "Cannot reach 300F: contact facilities.",
                "1": "Brownies continue to set after removal. Do not over-bake."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "cooling",
            "name": "Cooling",
            "steps": [
                "Leave product on cooling racks until the FOLLOWING DAY. Do not package warm.",
                "Verify product is fully cooled \u2014 no warmth to touch before proceeding to packaging."
            ],
            "ccps": [],
            "ccp_labels": {},
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "packaging",
            "name": "Packaging and Labeling",
            "steps": [
                "CCP-5: Post-cool spot weight \u2014 weigh 10% of units after cooling. Verify 78\u201382g.",
                "Record final packaged yield count",
                "Place 1 brownie/blondie per bag with cutting card. Heat seal.",
                "Verify heat seal integrity \u2014 100% of bags.",
                "Apply compliant label. Verify DCC# DCC-10003615, METRC UID, potency, warnings.",
                "PBC-100 ALLERGEN: Supervisor must confirm PEANUT declaration is present and correct on every label.",
                "Assign finished goods METRC UID \u2014 enter on BPR and tag packaging.",
                "Record 2 retention samples \u2014 label with SKU, batch ID, METRC UID, mfg date.",
                "PBC-100 ONLY: Post-run peanut allergen clean-out \u2014 supervisor must inspect all contact surfaces and sign Post-Run Allergen Clean-Out form."
            ],
            "ccps": [
                0,
                1
            ],
            "ccp_labels": {
                "0": "Post-Cool Unit Weight (g) \u2014 verify 78\u201382g",
                "1": "Final Yield (units)"
            },
            "ccp_specs": {
                "0": {
                    "unit": "g",
                    "min": 77,
                    "max": 83
                },
                "1": {
                    "unit": "units",
                    "min": 1,
                    "max": 9999
                }
            },
            "corrective_actions": {
                "0": "Shifted significantly from pre-bake: investigate moisture loss. Log deviation if >5% OOS.",
                "1": "Outside 95-105%: Deviation Log."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator",
                "QA Supervisor"
            ]
        },
        {
            "id": "qc_release",
            "name": "QC Batch Release",
            "steps": [
                "All phases signed off with concurrent timestamps",
                "All METRC UIDs recorded (cannabis input + finished goods)",
                "COA received from licensed lab",
                "CCP-6: COA THC within +/-20% of 100mg label claim (accept 80\u2013120mg per unit)",
                "All cannabis waste logged on Cannabis Waste Log",
                "PBC-100: Post-run allergen clean-out form signed by supervisor",
                  "All open deviations have documented CAPA",
                "BATCH RELEASE DECISION \u2014 mark RELEASED or ON HOLD"
            ],
            "ccps": [
                3
            ],
            "ccp_labels": {
                "3": "COA THC (mg/unit) \u2014 must be 80\u2013120mg"
            },
            "ccp_specs": {
                "3": {
                    "unit": "mg",
                    "min": 80,
                    "max": 120
                }
            },
            "corrective_actions": {
                "3": "OOS: HOLD. Consult QA."
            },
            "notes_required": True,
            "sign_off_roles": [
                "QA Supervisor"
            ]
        }
    ]
  },

    "dr_norms_brownie_sleep": {
    "label": "Dr. Norm's Sleep Bites Mini Brownie (100mg THC + 50mg CBN)",
    "sop_ref": "MMP-DN-SB-100 v1.0",
    "uom": "units",
    "phases": [
        {
            "id": "pre_production",
            "name": "Pre-Production Setup",
            "steps": [
                "SLEEP BITES (SB-100): DUAL-CANNABINOID. TWO cannabis inputs required: THC Distillate + CBN Distillate. Two COAs and two METRC UIDs required.",
                "Verify scale seal is current \u2014 record scale Asset ID",
                "Allergen pre-run clearance signed (SOY \u2014 soy lecithin in formula)",
                "Confirm THC Distillate METRC UID on BPR (Input 1 of 2)",
                "Confirm CBN Distillate METRC UID on BPR (Input 2 of 2)",
                "THC Distillate COA confirmed \u2014 record mg/g THC",
                "CBN Distillate COA confirmed \u2014 record mg/g CBN (SEPARATE COA required)",
                "Calculate mg THC for batch. Record on BPR. QA must verify.",
                "Calculate mg CBN SEPARATELY: batch yield x 50mg / COA mg/g CBN = grams needed. QA must verify.",
                "All ingredients pulled \u2014 lot numbers recorded. Vegan butter and soy lecithin lot verified.",
                "Inspect all equipment including probe thermometer."
            ],
            "ccps": [
                5,
                6
            ],
            "ccp_labels": {
                "5": "COA THC Potency (mg/g)",
                "6": "COA CBN Potency (mg/g) \u2014 SEPARATE COA"
            },
            "ccp_specs": {
                "5": {
                    "unit": "mg/g",
                    "min": 1,
                    "max": 9999
                },
                "6": {
                    "unit": "mg/g",
                    "min": 1,
                    "max": 9999
                }
            },
            "corrective_actions": {
                "5": "No THC COA: halt. Contact QA.",
                "6": "No CBN COA: halt. Must be from DCC-licensed 3rd-party lab. Do not use estimated potency."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "chocolate_melt",
            "name": "Chocolate Melt",
            "steps": [
                "Melt VEGAN butter + VEGAN choc chips in TWO BATCHES per MMP (3 lbs butter + 10.5 lbs choc chips total, split).",
                "Stir continuously until smooth. Set aside to cool before mixing."
            ],
            "ccps": [],
            "ccp_labels": {},
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "infusion",
            "name": "Infusion \u2014 THC + CBN Dual Infusion",
            "steps": [
                "Mix soy lecithin powder (4 oz) fully into infusion vegan butter (3 lbs) BEFORE adding any distillate.",
                "Add calculated THC distillate to infusion butter/lecithin blend. Record exact amount added.",
                "Add calculated CBN distillate to same blend. Record exact amount added SEPARATELY.",
                "CCP-1: Heat dual infusion blend to 88\u201391F. Record temp before introduction to dough.",
                "Verify blend is visually homogeneous \u2014 both distillates fully incorporated."
            ],
            "ccps": [
                1,
                2,
                3
            ],
            "ccp_labels": {
                "1": "THC Distillate Amount Added (g)",
                "2": "CBN Distillate Amount Added (g) \u2014 record separately from THC",
                "3": "Dual Infusion Butter Temp (F) \u2014 must be 88\u201391F"
            },
            "ccp_specs": {
                "1": {
                    "unit": "g",
                    "min": 1,
                    "max": 9999
                },
                "2": {
                    "unit": "g",
                    "min": 1,
                    "max": 9999
                },
                "3": {
                    "unit": "F",
                    "min": 88,
                    "max": 91
                }
            },
            "corrective_actions": {
                "1": "Record actual. Any variance: note on BPR.",
                "2": "Record CBN separately from THC entry. Do not combine into one entry.",
                "3": "<88F: rewarm. >91F: cool. Never exceed 95F. OOS after 2 attempts: halt, QA, Deviation Log."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "mixing",
            "name": "Mixing \u2014 Dough Preparation",
            "steps": [
                "Add choc/vegan butter melt and sugars to Hobart. Mix: L1x10s | L2x20s | L3x30s. Scrape after each.",
                "CCP-2: Add THC+CBN infusion blend at 88\u201391F \u2014 verify temp immediately before adding. Record temp.",
                "Mix: L1x30s scrape | L2x40s scrape | L3x60s scrape",
                "Add invert sugar, white granulated sugar, remaining brown sugar. Mix: L1x10s scrape | L2x40s scrape | L3x60s scrape",
                "Add vanilla extract. Mix: L1x10s scrape | L2x30s scrape | L3x30s scrape",
                "Add flour, baking soda, baking powder, salt, Bitter Blocker, Valerian Root. Mix: L1x40s scrape | L2x60s scrape | L3x60s scrape",
                "Add vegan choc chips and cocoa powder. Mix: L1x30s | L2x50s scrape"
            ],
            "ccps": [
                1
            ],
            "ccp_labels": {
                "1": "Dual Infusion Temp at Mixer Addition (F) \u2014 must be 88\u201391F"
            },
            "ccp_specs": {
                "1": {
                    "unit": "F",
                    "min": 88,
                    "max": 91
                }
            },
            "corrective_actions": {
                "1": "Same as CCP-1. Re-temp and correct before adding."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "forming",
            "name": "Forming \u2014 Freeze and Deposit",
            "steps": [
                "Spread dough onto parchment-lined pans. Label parchment SB-100 and batch ID.",
                "CCP-3: Freeze dough minimum 30 min. Firm to touch but NOT frozen solid.",
                "Set up Formatic depositor with SHALLOW die for mini-brownie format.",
                "CCP-4: Weigh EVERY mini brownie \u2014 100% weighing. MINI FORMAT: 7.8\u20138.2g per unit (NOT 78\u201382g).",
                "Record total units formed \u2014 yield count"
            ],
            "ccps": [
                1,
                3,
                4
            ],
            "ccp_labels": {
                "1": "Freeze Duration (minutes) \u2014 min 30 min",
                "3": "Mini Unit Weight (g) \u2014 must be 7.8\u20138.2g (MINI FORMAT)",
                "4": "Units Formed (yield count)"
            },
            "ccp_specs": {
                "1": {
                    "unit": "minutes",
                    "min": 30,
                    "max": 90
                },
                "3": {
                    "unit": "g",
                    "min": 7.8,
                    "max": 8.2
                },
                "4": {
                    "unit": "units",
                    "min": 1,
                    "max": 9999
                }
            },
            "corrective_actions": {
                "1": "Soft: extend in 10-min increments. Frozen solid: temper 5\u201310 min.",
                "3": "MINI FORMAT \u2014 7.8\u20138.2g NOT 78\u201382g. OOS: adjust or discard. Trimmings = cannabis waste log.",
                "4": "Outside 95-105%: Deviation Log."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "baking",
            "name": "Baking",
            "steps": [
                "SLEEP BITES: Preheat oven to 325F (NOT 300F \u2014 different from standard brownies). Verify oven temp.",
                "SLEEP BITES: Bake exactly 7 minutes (NOT 11.5 min \u2014 mini format bakes faster). Record start and end time.",
                "Remove pans. Transfer to cooling racks."
            ],
            "ccps": [
                0,
                1
            ],
            "ccp_labels": {
                "0": "Oven Temp (F) \u2014 must be 322\u2013328F (325F target)",
                "1": "Bake Time (minutes) \u2014 must be 6.5\u20137.5 min"
            },
            "ccp_specs": {
                "0": {
                    "unit": "F",
                    "min": 322,
                    "max": 328
                },
                "1": {
                    "unit": "minutes",
                    "min": 6.5,
                    "max": 7.5
                }
            },
            "corrective_actions": {
                "0": "325F only. Do not use 300F standard brownie setting.",
                "1": "7-min bake only. Do not use 11.5-min full-size brownie time."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "cooling",
            "name": "Cooling",
            "steps": [
                "Leave product on cooling racks until the FOLLOWING DAY. Do not package warm.",
                "Verify product is fully cooled \u2014 no warmth to touch before proceeding."
            ],
            "ccps": [],
            "ccp_labels": {},
            "notes_required": False,
            "sign_off_roles": [
                "Operator"
            ]
        },
        {
            "id": "packaging",
            "name": "Packaging and Labeling",
            "steps": [
                "CCP-5: Post-cool spot weight \u2014 10% of units. Verify 7.8\u20138.2g (MINI format).",
                "Record final packaged yield count",
                "Package per SKU configuration. Heat seal.",
                "Verify heat seal integrity \u2014 100% of bags.",
                "DUAL CANNABINOID LABEL: Label MUST declare BOTH 100mg THC AND 50mg CBN per serving. Supervisor verifies both present.",
                "Apply full compliant label \u2014 verify DCC# DCC-10003615, METRC UID, universal symbol, warnings, mfg date.",
                "Assign finished goods METRC UID \u2014 enter on BPR. Link to both THC and CBN input UIDs.",
                "Record 2 retention samples \u2014 label with SB-100, batch ID, all METRC UIDs, mfg date."
            ],
            "ccps": [
                0,
                1
            ],
            "ccp_labels": {
                "0": "Post-Cool Mini Unit Weight (g) \u2014 must be 7.5\u20138.5g",
                "1": "Final Yield (units)"
            },
            "ccp_specs": {
                "0": {
                    "unit": "g",
                    "min": 7.5,
                    "max": 8.5
                },
                "1": {
                    "unit": "units",
                    "min": 1,
                    "max": 9999
                }
            },
            "corrective_actions": {
                "0": "Mini format. If shifted: investigate moisture loss. Log deviation.",
                "1": "Outside 95-105%: Deviation Log."
            },
            "notes_required": False,
            "sign_off_roles": [
                "Operator",
                "QA Supervisor"
            ]
        },
        {
            "id": "qc_release",
            "name": "QC Batch Release",
            "steps": [
                "All phases signed off with concurrent timestamps",
                "THREE METRC UIDs recorded: THC input + CBN input + finished goods",
                "BOTH COAs received from licensed lab (THC COA + CBN COA)",
                "CCP-6: COA THC within +/-20% of 100mg label claim (accept 80\u2013120mg per unit)",
                "CCP-7: COA CBN within +/-20% of 50mg label claim (accept 40\u201360mg per unit)",
                "All cannabis waste logged on Cannabis Waste Log",
                "All open deviations have documented CAPA",
                "BATCH RELEASE DECISION \u2014 mark RELEASED or ON HOLD"
            ],
            "ccps": [
                3,
                4
            ],
            "ccp_labels": {
                "3": "COA THC (mg/unit) \u2014 must be 80\u2013120mg",
                "4": "COA CBN (mg/unit) \u2014 must be 40\u201360mg"
            },
            "ccp_specs": {
                "3": {
                    "unit": "mg",
                    "min": 80,
                    "max": 120
                },
                "4": {
                    "unit": "mg",
                    "min": 40,
                    "max": 60
                }
            },
            "corrective_actions": {
                "3": "OOS: HOLD. Consult QA.",
                "4": "OOS: HOLD. Dual OOS may trigger recall assessment."
            },
            "notes_required": True,
            "sign_off_roles": [
                "QA Supervisor"
            ]
        }
    ]
  },    
  
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
          "Confirm work area, trays, and tools free of food/allergen residue from any prior production",
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
    "label": "Gummies",
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
          "Induction burner: remove any debris or residue w/ hot water and toweel only",
          "All tabletop counters and surfaces: 70–99% ISO-alcohol",
          "Work area is free of clutter — only items for this run present",
          "Gloves & hairnet on — maintain throughout production",
          "Complete allergen pre-run clearance check",
        ],
        "ccps": [],
        "ccp_labels": {},
        "notes_required": False,
      },
      {
        "id": "ingredient_prep",
        "name": "Ingredient Prep & Weighing",
        "steps": [
          "Weigh Corn Syrup — record weight",
          "Weigh Sugar on calibrated scale — record weight",
          "Weigh Gelatin — record weight", 
          "Weigh Sorbitol — record weight",      
          "Weigh Citric Acid — record weight",
          "Weigh THC Distillate on precision scale (.001g) — record weight",
          "Weigh Flavoring — record weight",
          "Weigh Distillated Water — record weight",
          "Weigh Color — record weight per flavor",
          "Weigh Soy Lecithin — record weight",
          "All ingredient weights verified against MMP-MASTER-001 batch formula",
          "All ingredients in assigned, sealed bins — LOT numbers confirmed",
        ],
        "ccps": [5],   # ← was [7]
        "ccp_labels": {5: "THC Distillate weight (g)"},
        "notes_required": False,
      },
      {
        "id": "cook",
        "name": "Cook",
        "steps": [
            "Set Induction burner to 360°F, add Corn Syrup in induction pot — wait until it simmers",
            "Add Sugar in induction pot — stir continuously until it dissolves (10–15 min)",
            "Add Sorbitol in induction pot — mix continuously until it dissolves",
            "Add Flavor in induction pot — stir and wait until mixture is uniform",
            "While waiting for the flavor to simmer, In another mixing bowl, add water and color and whisk until color is dissolved",
            "Add Gelatin to the water/color mixing bowl and whisk continuously until fully dissolved",
            "Wait until the gelatin hardens (5 mins approx); then cut into smaller pieces to dissolve easier",
            "Before adding gelatin mixture, reduce the simmering pot down to 310°F",
            "Monitor temperature — reach minimum 300°F before combining mixtures",   # ← comma added
            "At the same time, combine the heated mixture, gelatin mixture, and the citric acid in the induction pot. Continue to stir",
            "Once the citric Acid is fully dissolved, please add the distillate (and soy lecithin if required)",
            "Continue to stir until final mixture is FULLY DISSOLVED",
            "Verify temperature does not exceed 330°F",
            "Record the weight of the total mixture",
        ],
        "ccps": [8, 12],   # ← was [6, 7] — now correctly at "Monitor temp ≥300°F" and "Verify temp ≤330°F"
        "ccp_labels": {8: "Temperature before Gelatin (°F) — must be 300–320°F", 12: "Temperature confirmed below 340°F (yes/no)"},
        "notes_required": False,
      },
      {
        "id": "depositing",
        "name": "Depositing",
        "steps": [
          "Ensure nozzles are lubricated with vegetable oil (no animal fat)",
          "Confirm dispensing machine is preheated to 165°F (needs 30 min warm-up)",
          "Monitor temperature — reach minimum 165°F",
          "Pour gummy mixture into the depositor"
          "Confirm molds are clean and free of debris",          
          "Ensure machine calibration by test pouring; pulling the handle 5 times on a blank tray",
          "Dispense mixture into molds — verify each cavity fills without over-pouring",
          "Upon curing, weigh sample units from first molds — confirm weight 2.4g < X < 2.6g per piece",
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
          "Select 10 approved units per package",
          "Place into child-resistant mylar pouch",
          "Press firmly to seal — remove excess air from packaging",
          "Feed through continuous sealing machine (preheat to 160-180°F)",
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
          "Induction burner: hot water & towel to remove any debris and residue",
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
  # DISTILLATE VAPE 510 / TEMPO AIO / TEMPO LIVE RESIN VAPE
  # Matches BPR-DVP-001 v2.0 and BPR-TLR-001 v2.0 (water-bath blend →
  # VapeJet fill → Squish-o-matic cap). Rosin AIO Vape does NOT use this
  # family — it has a multi-day decarb stage first, see "rosin_vape_decarb".
  # ─────────────────────────────────────────────────────────────────
  "vapes": {
    "label": "Distillate Vape 510 / TEMPO AIO / Tempo Live Resin Vape",
    "sop_ref": "MMP-DVP-001 v1.0 / PQP-DVP-001 v1.0",
    "uom": "units",
    "phases": [
      {
        "id": "pre_production",
        "name": "Pre-Production Setup",
        "steps": [
          "ISO-flush VapeJet lines, syringe, and reservoir — air dry completely",
          "Purge fresh oil through needle before production — confirm no air bubbles at tip",
          "Verify cannabis distillate COA (and HTE COA if Tempo Live Resin — both required) — record METRC UID(s), potency %, required weight, actual weight, variance, THC/unit",
          "Supervisor sign-off on cannabis verification — mandatory before processing",
          "Confirm hardware (510 cartridge / TEMPO AIO pod) lot matches spec for this SKU",
          "Calibrate VapeJet platform (level). Set fill weight in software: 1.0g",
          "All tabletop counters and surfaces: 70–99% ISO-alcohol",
        ],
        "ccps": [2, 5],
        "ccp_labels": {2: "Cannabis COA verified — UID / potency / weight / variance recorded", 5: "Fill weight set in VapeJet software (g) — target 1.0g"},
        "ccp_specs": {2: {"unit": "boolean", "min": 1, "max": 1}, 5: {"unit": "g", "min": 1.0, "max": 1.0}},
        "corrective_actions": {2: "No COA or UID mismatch: halt production, contact QA.", 5: "Reset software fill weight to 1.0g before proceeding."},
        "notes_required": False,
      },
      {
        "id": "source_prep",
        "name": "Source Prep — Water Bath & Blend",
        "steps": [
          "Place distillate in sterile glass container in water bath at 80–90°F until fluid",
          "510/TEMPO AIO: place terpenes in vacuum oven at 175°F. Tempo Live Resin: place HTE in warm container.",
          "Weigh distillate and terpenes/HTE per batch formula. Add liquidizer (TEMPO AIO only). Add menthol (ICE SKUs only). Record ALL weights.",
          "Combine in clean beaker. Immersion blend minimum 15 minutes until fully uniform — no separation or cloudiness.",
        ],
        "ccps": [0, 2, 3],
        "ccp_labels": {0: "Water bath temp (°F) — must be 80–90°F", 2: "Component weights recorded (g)", 3: "Blend uniformity — ≥15 min, no separation/cloudiness"},
        "ccp_specs": {0: {"unit": "F", "min": 80, "max": 90}, 2: {"unit": "g", "min": 0.1, "max": 99999}, 3: {"unit": "minutes", "min": 15, "max": 999}},
        "corrective_actions": {0: "Outside 80–90°F: adjust bath, re-verify before weighing.", 2: "Record actual — any variance from formula noted on BPR.", 3: "If separation/cloudiness persists after 15 min: extend blend time, do not proceed until uniform."},
        "notes_required": False,
      },
      {
        "id": "fill_calibration",
        "name": "Fill Calibration (Mandatory Before Production)",
        "steps": [
          "Load blend into VapeJet reservoir. Purge lines — confirm fresh oil at needle tip, no air bubbles.",
          "PRE-RUN FILL WEIGHT CALIBRATION: run 3–5 pump cycles. Weigh 3 filled units on certified scale.",
          "Confirm average within target: 1.0g ±0.05g. Adjust VapeJet and re-verify if outside tolerance.",
        ],
        "ccps": [1],
        "ccp_labels": {1: "Pre-run calibration weight, avg of 3 units (g) — must be 1.0g ±0.05g"},
        "ccp_specs": {1: {"unit": "g", "min": 0.95, "max": 1.05}},
        "corrective_actions": {1: "Outside tolerance: adjust VapeJet, re-run 3-unit check. Do NOT begin production run until in spec."},
        "notes_required": False,
      },
      {
        "id": "filling",
        "name": "Filling & Capping",
        "steps": [
          "Load rack (100 units 510 / 50 units TEMPO AIO / 24 units Tempo Live Resin AIO). Run fill cycle — monitor for overflow.",
          "Transfer to Squish-o-matic 1000. Press Squish — hydraulic cap applied.",
          "Pull-test spot-check cap seal per rack.",
          "Wipe exterior of each unit clean — no oil residue on outside.",
          "Record total units filled and any waste/rejected units.",
        ],
        "ccps": [2],
        "ccp_labels": {2: "Cap pull-test — cap does not separate (pass/fail per rack)"},
        "ccp_specs": {2: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {2: "Fail: rework or reject rack. Do not package units with failed pull-test."},
        "notes_required": False,
      },
      {
        "id": "packaging",
        "name": "Packaging & Labeling",
        "steps": [
          "Place each unit into SKU-correct CR packaging / mylar",
          "Apply required info sticker — verify all 5 fields: product name, batch#, METRC UID, mfg date, THC%",
          "Supervisor label approval — mandatory before full labeling run",
          "20CT case packaging — count and record",
          "Record total packaged unit count",
        ],
        "ccps": [1, 3],
        "ccp_labels": {1: "Label verification — all 5 fields present (yes/no)", 3: "Total packaged units"},
        "ccp_specs": {1: {"unit": "boolean", "min": 1, "max": 1}, 3: {"unit": "units", "min": 1, "max": 99999}},
        "corrective_actions": {1: "Any missing field: halt labeling, correct before proceeding.", 3: "Outside 95–105% of filled units: Deviation Log."},
        "notes_required": False,
        "sign_off_roles": ["Operator", "Supervisor"],
      },
      {
        "id": "sanitation",
        "name": "Post-Run Sanitation",
        "steps": [
          "ISO-flush VapeJet lines, syringe, reservoir, and needle — air dry",
          "Wipe all tabletop counters and surfaces with 70–99% ISO-alcohol",
          "Flush between strains — do not allow cross-contamination of different oil types",
          "Complete cleaning log entry — date, equipment, method, initials (Section 5)",
          "METRC manufacturing activity entry within 24 hours",
        ],
        "ccps": [4],
        "ccp_labels": {4: "METRC entry completed within 24 hours (yes/no)"},
        "ccp_specs": {4: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {4: "Missed 24hr window: log deviation, file entry immediately, notify QA."},
        "notes_required": False,
      },
    ]
  },

  # ─────────────────────────────────────────────────────────────────
  # ROSIN AIO VAPE (.5g Disp & 1g AIO)
  # Matches BPR-RVP-001 v2.0. Distinct from "vapes" — this SKU
  # decarboxylates raw live rosin over several days at 76°F BEFORE any
  # VapeJet fill step. Do not route this to "vapes" — it is not a wash
  # (that's "rosin_wash") and not a press (that's "rosin_press"); it is
  # a downstream vape-fill product made FROM already-pressed rosin.
  # ─────────────────────────────────────────────────────────────────
  "rosin_vape_decarb": {
    "label": "Live Rosin Vape — Decarb & Fill (.5g Disp / 1g AIO)",
    "sop_ref": "MMP-RVP-001 v1.0 / PQP-RVP-001 v1.0",
    "uom": "units",
    "phases": [
      {
        "id": "pre_production",
        "name": "Pre-Production Setup",
        "steps": [
          "ISO-flush VapeJet lines, syringe, and reservoir — air dry completely",
          "Verify rosin COA (and distillate COA for 1g SKU, used as blending agent only) — record METRC UID(s), potency %, weights",
          "Supervisor sign-off on cannabis verification — mandatory before processing",
          "Confirm hardware (.5g Blinc / 1g AIO) lot matches spec for this SKU",
          "All tabletop counters and surfaces: 70–99% ISO-alcohol",
        ],
        "ccps": [1],
        "ccp_labels": {1: "Cannabis COA verified — UID / potency / weight recorded"},
        "ccp_specs": {1: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {1: "No COA or UID mismatch: halt production, contact QA."},
        "notes_required": False,
      },
      {
        "id": "decarboxylation",
        "name": "Decarboxylation — Multi-Day (NOT a wash step)",
        "steps": [
          "Day 1: place rosin in sterile glass container in vacuum oven at 76°F",
          "Stir and initial BPR daily stir log — initials required EACH DAY, no exceptions",
          "Day 2: stir rosin in oven. Check conversion — rosin becoming oil-like.",
          "Day 3+: continue daily stir and initials until rosin fully converted from THC-a to THC oil form. Do not rush.",
          "Confirm fluid oil consistency, no solid chunks, before proceeding to blend/fill",
        ],
        "ccps": [0, 4],
        "ccp_labels": {0: "Oven temp (°F) — must hold at 76°F", 4: "Rosin conversion — fluid oil consistency, no solid chunks (pass/fail)"},
        "ccp_specs": {0: {"unit": "F", "min": 74, "max": 78}, 4: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {0: "Outside 74–78°F: adjust oven, re-verify before continuing decarb.", 4: "Not fully converted: continue daily stir cycle, do not proceed to fill."},
        "notes_required": True,
      },
      {
        "id": "blend",
        "name": "Blend (1g SKU only)",
        "steps": [
          "1g SKU only: once converted, weigh ~50g distillate as blending agent",
          "Immersion blend rosin + distillate minimum 15 minutes until homogenized",
          ".5g SKU: skip this phase — proceed directly to fill calibration with converted rosin",
        ],
        "ccps": [1],
        "ccp_labels": {1: "Blend uniformity — ≥15 min, homogenized (1g SKU only)"},
        "ccp_specs": {1: {"unit": "minutes", "min": 15, "max": 999}},
        "corrective_actions": {1: "Not homogenized after 15 min: extend blend time before fill."},
        "notes_required": False,
      },
      {
        "id": "fill_calibration",
        "name": "Fill Calibration (Mandatory Before Production)",
        "steps": [
          "Load rosin (or rosin/distillate blend) into VapeJet reservoir. Purge lines — confirm clean oil at tip, no air bubbles.",
          "PRE-RUN FILL WEIGHT CALIBRATION: weigh 3 units after pump cycles.",
          "Confirm average within target: .5g SKU = 0.5g ±0.03g | 1g SKU = 1.0g ±0.05g",
        ],
        "ccps": [1],
        "ccp_labels": {1: "Pre-run calibration weight, avg of 3 units (g) — .5g ±0.03g or 1.0g ±0.05g"},
        "ccp_specs": {1: {"unit": "g", "min": 0.47, "max": 1.05}},
        "corrective_actions": {1: "Outside tolerance: adjust VapeJet, re-run 3-unit check. Do NOT begin production run until in spec."},
        "notes_required": False,
      },
      {
        "id": "filling",
        "name": "Filling & Capping",
        "steps": [
          "Load hardware rack (.5g: 50 units | 1g: 24 units). Run fill cycle — monitor for overflow.",
          "Transfer to Squish-o-matic 1000. Press Squish — hydraulic cap applied.",
          "Pull-test spot-check cap seal per rack.",
          "Record total units filled and any waste/rejected units.",
        ],
        "ccps": [2],
        "ccp_labels": {2: "Cap pull-test — cap does not separate (pass/fail per rack)"},
        "ccp_specs": {2: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {2: "Fail: rework or reject rack. Do not package units with failed pull-test."},
        "notes_required": False,
      },
      {
        "id": "packaging",
        "name": "Packaging & Labeling",
        "steps": [
          "Place into SKU-correct CR packaging. Apply strain sticker. Heat-seal mylar at 180°F if applicable.",
          "Apply required info sticker — verify all 5 fields: product name, batch#, METRC UID, mfg date, THC%",
          "Supervisor label approval — mandatory before full labeling run",
          "20CT case packaging — count and record",
        ],
        "ccps": [1],
        "ccp_labels": {1: "Label verification — all 5 fields present (yes/no)"},
        "ccp_specs": {1: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {1: "Any missing field: halt labeling, correct before proceeding."},
        "notes_required": False,
        "sign_off_roles": ["Operator", "Supervisor"],
      },
      {
        "id": "sanitation",
        "name": "Post-Run Sanitation",
        "steps": [
          "ISO-flush VapeJet lines, syringe, reservoir, and needle — air dry",
          "Wipe vacuum oven interior with ISO-alcohol",
          "Wipe all tabletop counters and surfaces with 70–99% ISO-alcohol",
          "Complete cleaning log entry — date, equipment, method, initials (Section 5)",
          "METRC manufacturing activity entry within 24 hours",
        ],
        "ccps": [4],
        "ccp_labels": {4: "METRC entry completed within 24 hours (yes/no)"},
        "ccp_specs": {4: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {4: "Missed 24hr window: log deviation, file entry immediately, notify QA."},
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
          "Confirm work area, trays, and tools free of food/allergen residue from any prior production",
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
  },   # ← closes "bho_badder"

  # ─────────────────────────────────────────────────────────────────
  # ROSIN WASH
  # ─────────────────────────────────────────────────────────────────
  "rosin_wash": {
    "label": "Live Rosin — Ice Water Wash / Freeze Dry / Sift",
    "sop_ref": "MMP-LRS-001 v1.0",
    "uom": "grams",
    "input_type": "fresh_frozen",
    "output_type": "hash_lot",
    "phases": [
      {
        "id": "pre_production",
        "name": "Pre-Production Setup",
        "steps": [
          "Verify all fresh frozen METRC UIDs recorded on BPR Section 2 before starting",
          "Confirm all input materials are frozen solid — do not allow to thaw",
          "Verify all equipment clean, sanitized, dry: washers, bubble bags, trays, tools",
          "Inspect bubble bags — replace if torn, holes, or worn mesh",
          "Confirm freeze dryer pre-cooled — verify pump oil level",
          "Confirm work area temperature is cold — minimize warm exposure time",
          "Gloves on — maintain throughout all wash stages",
          "Confirm work area, trays, and tools free of food/allergen residue from any prior production",
        ],
        "ccps": [],
        "ccp_labels": {},
        "ccp_specs": {},
        "corrective_actions": {},
        "notes_required": False,
        "sign_off_roles": ["Operator"],
      },
      {
        "id": "ice_water_wash",
        "name": "Ice Water Wash",
        "steps": [
          "Fill tea bags with 4,000g wet material each on certified scale — keep frozen until loading",
          "Record wet weight per tea bag — enter on BPR",
          "Load washers: 3 buckets ice → add 3-4 tea bags → 3 more buckets ice → fill with RO water (NOT tap) until bags submerged",
          "Run 2 full wash cycles — record start and end time for each cycle",
          "Drain wash water through bubble bags — agitate to separate plant matter from hash resin",
          "Collect hash on clean tray using sterile spoon",
          "Record total WET WEIGHT of hash on tray immediately after collection",
          "Place cannabis by-product in locking waste receptacle — record in Waste Management Log",
          "For multi-strain washes: label each collection tray with strain name before mixing",
        ],
        "ccps": [0, 1, 6],
        "ccp_labels": {
          0: "Tea bag fill weight (g) — target 4,000g per bag ±50g",
          1: "RO water confirmed (not tap water) — yes/no",
          6: "Wet hash weight on tray (g) — record before freeze dryer",
        },
        "ccp_specs": {
          0: {"unit": "g",       "min": 3950, "max": 4050},
          1: {"unit": "boolean", "min": 1,    "max": 1},
          6: {"unit": "g",       "min": 1,    "max": 99999},
        },
        "corrective_actions": {
          0: "Short of 3,950g: top up. Over 4,050g: remove excess.",
          1: "Tap water confirmed: STOP. Drain and restart with RO water. Log deviation.",
          6: "Record actual. Significantly below expected: investigate bag integrity.",
        },
        "notes_required": False,
        "sign_off_roles": ["Operator"],
      },
      {
        "id": "freeze_drying",
        "name": "Freeze Drying",
        "steps": [
          "Load hash trays into freeze dryer immediately after collection — minimize air exposure",
          "Check pump oil level — refill if low before starting",
          "Turn on vacuum pump — record start time",
          "Set drying time appropriate to water content and tray weight",
          "Check periodically — break up thick portions of hash as they dry",
          "Verify fully dry: powdery texture, no moisture clumps, no wet spots",
          "Open valve before Defrost — let water drain completely. Press Defrost.",
          "Remove dried hash from freeze dryer — record dry weight immediately",
        ],
        "ccps": [1, 7],
        "ccp_labels": {
          1: "Pump oil level checked — ok/refilled",
          7: "Dry hash weight after freeze drying (g)",
        },
        "ccp_specs": {
          1: {"unit": "boolean", "min": 1,    "max": 1},
          7: {"unit": "g",       "min": 1,    "max": 99999},
        },
        "corrective_actions": {
          1: "Oil low: refill before running. Running with low oil risks pump damage.",
          7: "Record actual. Log if yield seems abnormally low.",
        },
        "notes_required": False,
        "sign_off_roles": ["Operator"],
      },
      {
        "id": "sifting",
        "name": "Sifting & Yield Verification",
        "steps": [
          "Sift dried hash through appropriate screen to remove plant material and large particles",
          "Record SIFT WEIGHT — this is the final usable hash weight",
          "Calculate yield: sift weight ÷ wet weight × 100 — record yield %",
          "Inspect hash quality: color, texture, absence of contamination",
          "Vacuum seal sifted hash in labeled plastic bag",
          "Label bag with: hash lot ID, strain(s), sift weight, wash date",
          "Place in freezer — record storage location on BPR",
          "Update hash lot status to 'available' in BPR app",
        ],
        "ccps": [0, 1, 4],
        "ccp_labels": {
          0: "Sift weight / final usable hash weight (g)",
          1: "Yield % — sift ÷ wet × 100",
          4: "Storage location confirmed (freezer + shelf)",
        },
        "ccp_specs": {
          0: {"unit": "g",  "min": 1,   "max": 99999},
          1: {"unit": "%",  "min": 0.5, "max": 25},
          4: {"unit": "boolean", "min": 1, "max": 1},
        },
        "corrective_actions": {
          0: "Record actual. If near zero: investigate freeze dryer run and bag integrity.",
          1: "Outside 0.5-25%: investigate. Very low yield may indicate equipment issue.",
          4: "Must be labeled and stored before BPR sign-off.",
        },
        "notes_required": True,
        "sign_off_roles": ["Operator", "Supervisor"],
      },
      {
        "id": "sanitation",
        "name": "Post-Run Sanitation",
        "steps": [
          "Flush washers with hot water — ISO-alcohol or chlorine sanitizer EOD",
          "Clean bubble bags with RO water — air dry completely",
          "Clean freeze dryer trays with ISO-alcohol — inspect for residue",
          "Clean all collection trays and tools with ISO-alcohol",
          "Wipe all tabletop surfaces with 70-99% ISO-alcohol",
          "Record cleaning log: date, equipment, method, PPM, initials (Section 5)",
          "ISO-alcohol wipe washing machines between strains — prevent cross-contamination",
        ],
        "ccps": [],
        "ccp_labels": {},
        "ccp_specs": {},
        "corrective_actions": {},
        "notes_required": False,
        "sign_off_roles": ["Operator"],
      },
    ],
  },  # ← closes "rosin_wash"

  # ─────────────────────────────────────────────────────────────────
  # ROSIN PRESS
  # ─────────────────────────────────────────────────────────────────
  "rosin_press": {
    "label": "Live Rosin — Press / Cure (Badder) / Package",
    "sop_ref": "MMP-LRS-001 v1.0",
    "uom": "grams",
    "input_type": "hash_lot",
    "output_type": "metrc_uid",
    "phases": [
      {
        "id": "pre_production",
        "name": "Pre-Production Setup",
        "steps": [
          "Verify hash lot ID(s) recorded on BPR Section 2 before starting",
          "Confirm hash lot status is 'available' — not already in use by another batch",
          "Pull hash from freezer — record weight of each hash lot being used",
          "Verify all equipment clean: rosin presses, plates, tools, parchment",
          "Preheat rosin press #1 to 162°F — verify with thermometer before pressing",
          "Preheat rosin press #2 to 162°F if using — verify temp",
          "Preheat rosin press #3 to 162°F if using — verify temp",
          "Preheat rosin press #4 to 162°F if using — verify temp",
          "Confirm parchment supply is sufficient for batch",
          "Gloves on — maintain throughout",
        ],
        "ccps": [4, 5, 6, 7],
        "ccp_group_min": 1,
        "ccp_labels": {
          4: "Rosin press #1 temp (°F)",
          5: "Rosin press #2 temp (°F) — if using",
          6: "Rosin press #3 temp (°F) — if using",
          7: "Rosin press #4 temp (°F) — if using",
        },
        "ccp_specs": {
          4: {"unit": "F", "min": 158, "max": 166},
          5: {"unit": "F", "min": 158, "max": 166},
          6: {"unit": "F", "min": 158, "max": 166},
          7: {"unit": "F", "min": 158, "max": 166},
        },
        "corrective_actions": {
          4: "Below 158°F: wait and re-verify. Do not press until at temp.",
          5: "Below 158°F: wait and re-verify. Do not press until at temp.",
          6: "Below 158°F: wait and re-verify. Do not press until at temp.",
          7: "Below 158°F: wait and re-verify. Do not press until at temp.",
        },
        "notes_required": False,
        "sign_off_roles": ["Operator"],
      },
      {
        "id": "pressing",
        "name": "Rosin Pressing",
        "steps": [
          "Remove hash from freezer — mold into 5-6g rectangles immediately",
          "Place each rectangle into mesh screen — fold ends to secure",
          "Set parchment on press platform and beneath",
          "Press with foot trigger — allow rosin to run through sides completely",
          "Record yield weight per press on parchment — do not combine until weighed",
          "Freeze pressed hash squares (Jar Tech material) — label for later use",
          "Collect all rosin from parchment — record total rosin yield weight",
          "Place press waste in locking waste receptacle — record in Waste Management Log",
          "Clean press plates with ISO-alcohol between strain changes",
        ],
        "ccps": [6, 7],
        "ccp_labels": {
          6: "Total rosin yield weight (g)",
          7: "Press waste weight (g) — for Waste Management Log",
        },
        "ccp_specs": {
          6: {"unit": "g", "min": 1, "max": 99999},
          7: {"unit": "g", "min": 0, "max": 99999},
        },
        "corrective_actions": {
          6: "Record actual. Calculate press yield %: rosin ÷ hash × 100.",
          7: "All press waste must be logged. Zero waste is unusual — verify.",
        },
        "notes_required": False,
        "sign_off_roles": ["Operator"],
      },
      {
        "id": "curing",
        "name": "Curing — Fresh Press or Badder",
        "steps": [
          "FRESH PRESS: Proceed directly to filling — skip remaining steps in this phase",
          "BADDER: Collect rosin in clean glass container",
          "BADDER: Allow to nucleate at room temperature — do not disturb for first 24 hours",
          "BADDER: After nucleation begins, whip with clean tool until uniform badder consistency",
          "BADDER: Check consistency — smooth, creamy, no separation",
          "Record cure method used: Fresh Press or Badder",
          "Record cure start time and completion time",
        ],
        "ccps": [5, 6],
        "ccp_labels": {
          5: "Cure method confirmed — Fresh Press or Badder",
          6: "Cure duration (hours) — Badder only",
        },
        "ccp_specs": {
          5: {"unit": "boolean", "min": 1, "max": 1},
          6: {"unit": "hours",   "min": 0, "max": 72},
        },
        "corrective_actions": {
          5: "Must be documented. Fresh Press and Badder are different products.",
          6: "Badder not nucleating after 48 hrs: consult supervisor. Document.",
        },
        "notes_required": False,
        "sign_off_roles": ["Operator"],
      },
      {
        "id": "filling",
        "name": "Filling — Jar / Container",
        "steps": [
          "Wipe CR glass jars inside and out with clean microfiber cloth",
          "Calibrate scale — verify reads 0.0g with parchment",
          "Weigh 1.0-1.05g rosin per jar on certified scale",
          "Change gloves when hands become sticky — cross-contamination risk",
          "Record total jars filled",
          "Apply CR cap immediately after filling each jar",
        ],
        "ccps": [2, 4],
        "ccp_labels": {
          2: "Fill weight per jar (g) — must be 1.0-1.05g",
          4: "Total jars filled (yield count)",
        },
        "ccp_specs": {
          2: {"unit": "g",     "min": 1.0, "max": 1.05},
          4: {"unit": "units", "min": 1,   "max": 99999},
        },
        "corrective_actions": {
          2: "OOS: remove excess or top up. Do not seal OOS jars without correction.",
          4: "Outside 95-105%: Deviation Log.",
        },
        "notes_required": False,
        "sign_off_roles": ["Operator"],
      },
      {
        "id": "packaging",
        "name": "Packaging & Labeling",
        "steps": [
          "Apply strain top sticker to CR cap",
          "Apply wrap sticker to jar exterior",
          "Place in product box",
          "Apply required info sticker — verify all 5 fields: product name, batch #, METRC UID, mfg date, THC%",
          "Supervisor label approval — all 5 fields confirmed before labeling run",
          "Record total packaged units",
          "Record 2 retention samples — label with strain, batch ID, METRC UID, mfg date",
        ],
        "ccps": [3, 5],
        "ccp_labels": {
          3: "Label verification — all 5 required fields present (yes/no)",
          5: "Total packaged units",
        },
        "ccp_specs": {
          3: {"unit": "boolean", "min": 1, "max": 1},
          5: {"unit": "units",   "min": 1, "max": 99999},
        },
        "corrective_actions": {
          3: "Any missing field: halt labeling. Correct before proceeding.",
          5: "Outside 95-105% of filled jars: Deviation Log.",
        },
        "notes_required": False,
        "sign_off_roles": ["Operator", "Supervisor"],
      },
      {
        "id": "sanitation",
        "name": "Post-Run Sanitation",
        "steps": [
          "Wipe rosin press plates with ISO-alcohol — inspect for residue",
          "Clean all filling tools and utensils with ISO-alcohol",
          "Wipe all tabletop surfaces with 70-99% ISO-alcohol",
          "UV light on overnight after ISO clean",
          "Record cleaning log entries (Section 5)",
        ],
        "ccps": [],
        "ccp_labels": {},
        "ccp_specs": {},
        "corrective_actions": {},
        "notes_required": False,
        "sign_off_roles": ["Operator"],
      },
    ],
  },

  # ─────────────────────────────────────────────────────────────────
  # PUNCHBAR — STANDARD CHOCOLATE (Distillate or Hash)
  # Matches BPR-CHO-001 v2.0. Two-pour temper-and-cast process.
  # NOT for Sugar-Free (different process, hard 87°F stop — see
  # "punch_chocolate_sf") or Peanut Butter Combo (dedicated dual-line
  # equipment + mandatory allergen clearance — see "punch_chocolate_pb").
  # ─────────────────────────────────────────────────────────────────
  "punch_chocolate": {
    "label": "Punchbar — Standard Chocolate",
    "sop_ref": "MMP-CHO-001 v1.0 / PQP-CHO-001 v1.0",
    "uom": "units",
    "phases": [
      {
        "id": "pre_production",
        "name": "Pre-Production Setup",
        "steps": [
          "All equipment BONE DRY and sanitized — moisture destroys chocolate, zero tolerance",
          "Verify cannabis COA (distillate or hash per SKU) — record METRC UID, batch#, potency %, required weight, actual weight, variance, THC/unit",
          "Supervisor sign-off on cannabis verification — mandatory before processing",
          "Preheat cooling tunnel: setting 7 (~45°F), belt speed 6 — confirm at temp BEFORE first pour",
          "Allergen control check — confirm no cross-contact with prior run's allergens; verify closed labeled containers",
        ],
        "ccps": [0, 1, 3],
        "ccp_labels": {0: "Equipment dryness — bone dry, zero moisture (pass/fail)", 1: "Cannabis COA verified — UID / potency / weight / variance recorded", 3: "Cooling tunnel temp (°F) — must be at 45°F, belt speed 6, before first pour"},
        "ccp_specs": {0: {"unit": "boolean", "min": 1, "max": 1}, 1: {"unit": "boolean", "min": 1, "max": 1}, 3: {"unit": "F", "min": 43, "max": 47}},
        "corrective_actions": {0: "Any moisture detected: halt, fully dry equipment before proceeding.", 1: "No COA or UID mismatch: halt production, contact QA.", 3: "Not at temp: continue preheat, do not begin pour until confirmed."},
        "notes_required": False,
      },
      {
        "id": "temper",
        "name": "Temper",
        "steps": [
          "Load chocolate wafers (milk/dark/white per SKU) into temper machine at 120°F",
          "Stir until internal temp reaches 100–108°F — approximately 40 minutes",
          "Monitor continuously with temperature gun",
          "Confirm chocolate fully melted, smooth, no lumps before proceeding",
        ],
        "ccps": [1],
        "ccp_labels": {1: "Internal chocolate temp (°F) — must be 100–108°F"},
        "ccp_specs": {1: {"unit": "F", "min": 100, "max": 108}},
        "corrective_actions": {1: "Outside range: continue tempering, re-check every 5 min. Do not proceed until in spec."},
        "notes_required": False,
      },
      {
        "id": "cannabis_incorporation",
        "name": "Cannabis Incorporation",
        "steps": [
          "CANNABIS INCORPORATION: weigh cannabis per COA-adjusted formula — record actual weight",
          "Add cannabis to melted chocolate",
          "Stir minimum 40 minutes until fully homogenized — no visible oil pooling or separation",
          "Supervisor initials mandatory on this step",
          "Add SKU-specific inclusions and flavoring — stir until uniform, no clumping",
        ],
        "ccps": [0, 2],
        "ccp_labels": {0: "Actual cannabis weight recorded (g)", 2: "Incorporation — ≥40 min, homogenized, no oil pooling (pass/fail)"},
        "ccp_specs": {0: {"unit": "g", "min": 0.1, "max": 99999}, 2: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {0: "Record actual — any variance from COA-adjusted formula noted on BPR.", 2: "Oil pooling/separation after 40 min: continue stirring, do not proceed to pour."},
        "notes_required": False,
        "sign_off_roles": ["Operator", "Supervisor"],
      },
      {
        "id": "pour_and_mold",
        "name": "Pour & Mold (2-Pour Process)",
        "steps": [
          "POUR 1: foot pedal dispense — approximately 50% fill into each mold cavity",
          "Place inclusions per cavity",
          "Feed molds into cooling tunnel one at a time — no stacking",
          "Remove molds at tunnel output",
          "POUR 2: fill remaining cavity with chocolate cap — feed through tunnel again",
          "Record Pour 1 and Pour 2 timestamps",
        ],
        "ccps": [5],
        "ccp_labels": {5: "Pour 1 and Pour 2 timestamps logged (both required)"},
        "ccp_specs": {5: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {5: "Missing either timestamp: log deviation, do not release batch until resolved."},
        "notes_required": False,
      },
      {
        "id": "demold_qc",
        "name": "Demold & Weight QC",
        "steps": [
          "Demold: invert over parchment-lined table, tap firmly",
          "Inspect bars — no bloom, no cracks",
          "UNIT WEIGHT SPOT CHECK: weigh 3 units per mold",
          "Confirm target: 21.75–22.5 g average",
          "Bloom on any unit = quarantine ENTIRE mold",
        ],
        "ccps": [2],
        "ccp_labels": {2: "Unit weight, avg of 3 per mold (g) — must be 21.75–22.5g"},
        "ccp_specs": {2: {"unit": "g", "min": 21.75, "max": 22.5}},
        "corrective_actions": {2: "Outside range or bloom present: quarantine entire mold, log deviation."},
        "notes_required": False,
      },
      {
        "id": "labeling_packaging",
        "name": "Labeling & Packaging",
        "steps": [
          "VIDEOJET TEST PRINT: supervisor approves all 5 required fields, font ≥6pt",
          "Do NOT begin run without supervisor approval",
          "Ilapak Carrera 500 foil wrap — verify digital sensor pass on each unit",
          "Feed units face-down through Videojet — confirm print placement legible, no smearing",
          "Insert into CRP box — align Punch fist logo, lock top securely",
          "Record total packaged unit count",
        ],
        "ccps": [0, 2],
        "ccp_labels": {0: "Videojet test print — all 5 fields, ≥6pt, supervisor approved (pass/fail)", 2: "Ilapak sensor pass — all units (pass/fail)"},
        "ccp_specs": {0: {"unit": "boolean", "min": 1, "max": 1}, 2: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {0: "Any field missing/illegible: halt run, correct before proceeding.", 2: "Sensor fail on any unit: pull unit, do not package."},
        "notes_required": False,
        "sign_off_roles": ["Operator", "Supervisor"],
      },
      {
        "id": "sanitation",
        "name": "Post-Run Sanitation",
        "steps": [
          "Temper machine and acrylic molds — must return to BONE DRY, no moisture residue",
          "Cooling tunnel and Ilapak Carrera 500 metal tracks — sanitize per Section 5",
          "Ilapak conveyor belt — scrape, wash, re-oil chain",
          "Videojet printer conveyor — ISO-alcohol wipe",
          "Complete cleaning log entry — date, equipment, method, initials (Section 5)",
          "METRC manufacturing activity entry within 24 hours",
        ],
        "ccps": [5],
        "ccp_labels": {5: "METRC entry completed within 24 hours (yes/no)"},
        "ccp_specs": {5: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {5: "Missed 24hr window: log deviation, file entry immediately, notify QA."},
        "notes_required": False,
      },
    ]
  },

  # ─────────────────────────────────────────────────────────────────
  # PUNCHBAR — SUGAR-FREE (SEEDING METHOD)
  # Matches BPR-SFB-001 v2.0. Distinct from "punch_chocolate": this is a
  # two-phase seeding temper with a HARD 87°F pour ceiling — exceeding
  # it destabilizes the chocolate and destroys the full batch. Do NOT
  # route Sugar-Free product to "punch_chocolate" — the standard 100–108°F
  # temper target does not apply here and the seeding steps have no
  # equivalent in the standard process.
  # ─────────────────────────────────────────────────────────────────
  "punch_chocolate_sf": {
    "label": "Punchbar — Sugar-Free (Seeding Method)",
    "sop_ref": "MMP-SFB-001 v1.0 / PQP-SFB-001 v1.0",
    "uom": "units",
    "phases": [
      {
        "id": "pre_production",
        "name": "Pre-Production Setup",
        "steps": [
          "All equipment BONE DRY — CRITICAL for sugar-free chocolate, moisture = immediate batch failure",
          "Verify hash COA — record METRC UID, batch#, potency %, required weight, actual weight, variance, THC/unit",
          "Supervisor sign-off on cannabis verification — mandatory before processing",
          "Preheat cooling tunnel: 45°F, belt speed 6 — confirm BEFORE production",
          "Allergen control check — hazelnut/milk/soy per SKU, confirm no cross-contact",
        ],
        "ccps": [0, 1, 3],
        "ccp_labels": {0: "Equipment dryness — bone dry, zero moisture (pass/fail)", 1: "Hash COA verified — UID / potency / weight recorded", 3: "Cooling tunnel temp (°F) — must be 45°F, belt speed 6"},
        "ccp_specs": {0: {"unit": "boolean", "min": 1, "max": 1}, 1: {"unit": "boolean", "min": 1, "max": 1}, 3: {"unit": "F", "min": 43, "max": 47}},
        "corrective_actions": {0: "Any moisture detected: halt, fully dry equipment. Immediate batch failure risk.", 1: "No COA or UID mismatch: halt production, contact QA.", 3: "Not at temp: continue preheat before production."},
        "notes_required": False,
      },
      {
        "id": "seeding_phases",
        "name": "Seeding — Phase 1 & Phase 2",
        "steps": [
          "PHASE 1: load 25 lbs SF chocolate wafers at 120°F",
          "Monitor with temp gun — target internal 105–110°F",
          "PHASE 2 SEEDING: once at 105–110°F, gradually add 10 lbs SF chocolate (seeding)",
          "Stir continuously — lower temperature to approximately 90°F",
        ],
        "ccps": [1, 3],
        "ccp_labels": {1: "Phase 1 internal temp (°F) — target 105–110°F", 3: "Phase 2 seeding temp (°F) — target ~90°F"},
        "ccp_specs": {1: {"unit": "F", "min": 105, "max": 110}, 3: {"unit": "F", "min": 85, "max": 95}},
        "corrective_actions": {1: "Outside range: continue heating/cooling, re-check every 5 min.", 3: "Not decreasing toward 90°F: continue stirring, do not proceed to roux until in range."},
        "notes_required": False,
      },
      {
        "id": "roux_cannabis_incorporation",
        "name": "Roux — Cannabis Incorporation",
        "steps": [
          "ROUX: separately melt 5 lbs SF chocolate",
          "Add cannabis hash — stir until fully dissolved, no oil pooling",
          "Add SKU-specific flavoring",
          "Cannabis MUST be fully incorporated in roux before combining with main batch",
          "Supervisor initials mandatory on this step",
          "Record actual hash weight (from roux step) on BPR cannabis traceability block",
        ],
        "ccps": [1, 5],
        "ccp_labels": {1: "Roux — fully dissolved, no oil pooling (pass/fail)", 5: "Actual hash weight recorded (g)"},
        "ccp_specs": {1: {"unit": "boolean", "min": 1, "max": 1}, 5: {"unit": "g", "min": 0.1, "max": 99999}},
        "corrective_actions": {1: "Oil pooling present: continue stirring, do not combine until resolved.", 5: "Record actual — any variance from formula noted on BPR."},
        "notes_required": False,
        "sign_off_roles": ["Operator", "Supervisor"],
      },
      {
        "id": "temper_and_snap_test",
        "name": "Final Temper & Snap Test",
        "steps": [
          "Add remaining chocolate a handful at a time while stirring",
          "Target final temper: 85°F — 87°F is the ABSOLUTE MAXIMUM",
          "STOP and cool if approaching 87°F",
          "Snap test on small sample — crisp snap = properly tempered, smooth and glossy",
          "If no snap or bloom present: DO NOT POUR",
        ],
        "ccps": [1, 3],
        "ccp_labels": {1: "Final temper temp (°F) — target 85°F, 87°F HARD MAX", 3: "Snap test — crisp snap, no bloom (pass/fail)"},
        "ccp_specs": {1: {"unit": "F", "min": 80, "max": 87}, 3: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {1: "Approaching or exceeding 87°F: STOP immediately, cool to 80°F before continuing. Batch loss risk above 87°F.", 3: "Fail: do not pour. Re-temper and re-test."},
        "notes_required": False,
      },
      {
        "id": "pour_87f_hardstop",
        "name": "Pour — 87°F Hard Stop Monitoring",
        "steps": [
          "POUR 1: foot pedal — monitor temp gun CONTINUOUSLY throughout pour",
          "If temp exceeds 87°F: PAUSE immediately, lower to 80°F, stir, wait before resuming",
          "Feed molds through cooling tunnel",
          "Remove at tunnel output",
          "POUR 2: fill remaining cavity — feed through tunnel again",
          "Record Pour 1 and Pour 2 timestamps",
        ],
        "ccps": [1],
        "ccp_labels": {1: "Pour temp — never exceeded 87°F, pause protocol followed if it did (pass/fail)"},
        "ccp_specs": {1: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {1: "Any exceedance not immediately paused/cooled: log deviation, notify QA — full batch loss risk."},
        "notes_required": True,
      },
      {
        "id": "demold_qc",
        "name": "Demold & Weight QC",
        "steps": [
          "Demold — inspect bars, no bloom, no cracks",
          "UNIT WEIGHT: 3 per mold, target 21.75–22.5 g average",
          "Snap test on demolded units",
          "BLOOM on any unit = quarantine ENTIRE mold",
        ],
        "ccps": [1, 3],
        "ccp_labels": {1: "Unit weight, avg of 3 per mold (g) — must be 21.75–22.5g", 3: "Bloom inspection — zero bloom across all units (pass/fail)"},
        "ccp_specs": {1: {"unit": "g", "min": 21.75, "max": 22.5}, 3: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {1: "Outside range: quarantine mold, log deviation.", 3: "Any bloom: quarantine entire mold."},
        "notes_required": False,
      },
      {
        "id": "labeling_packaging",
        "name": "Labeling & Packaging",
        "steps": [
          "VIDEOJET TEST PRINT: supervisor approves all 5 required fields, font ≥6pt",
          "Ilapak Carrera 500 foil wrap — verify sensor pass on each unit",
          "Label, insert into CRP box",
          "Record total packaged unit count",
        ],
        "ccps": [0],
        "ccp_labels": {0: "Videojet test print — all 5 fields, supervisor approved (pass/fail)"},
        "ccp_specs": {0: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {0: "Any field missing/illegible: halt run, correct before proceeding."},
        "notes_required": False,
        "sign_off_roles": ["Operator", "Supervisor"],
      },
      {
        "id": "sanitation",
        "name": "Post-Run Sanitation",
        "steps": [
          "Temper machine and acrylic molds — return to BONE DRY, no moisture residue",
          "Cooling tunnel and Ilapak tracks — sanitize per Section 5",
          "Complete cleaning log entry — date, equipment, method, initials",
          "METRC manufacturing activity entry within 24 hours",
        ],
        "ccps": [3],
        "ccp_labels": {3: "METRC entry completed within 24 hours (yes/no)"},
        "ccp_specs": {3: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {3: "Missed 24hr window: log deviation, file entry immediately, notify QA."},
        "notes_required": False,
      },
    ]
  },

  # ─────────────────────────────────────────────────────────────────
  # PUNCHBAR — PEANUT BUTTER COMBO
  # Matches BPR-PBC-001 v2.0. TOP-9 ALLERGEN (PEANUTS) — dedicated
  # dual-temper equipment with physically separated paddles, and
  # MANDATORY allergen clearance both before and after the run. Do not
  # route this SKU to "punch_chocolate" — the allergen-clearance CCPs
  # here are safety-critical and have no equivalent there.
  # ─────────────────────────────────────────────────────────────────
  "punch_chocolate_pb": {
    "label": "Punchbar — Peanut Butter Combo",
    "sop_ref": "MMP-PBC-001 v1.0 / PQP-PBC-001 v1.0",
    "uom": "units",
    "phases": [
      {
        "id": "pre_production_allergen_clearance",
        "name": "Pre-Production & Allergen Clearance (Mandatory)",
        "steps": [
          "PRE-RUN ALLERGEN CLEARANCE: supervisor verifies full allergen sanitation of all equipment from previous run",
          "Swab test if transitioning from a non-peanut product",
          "Sign allergen clearance block — mandatory before any peanut butter is introduced",
          "Confirm DEDICATED PADDLES are labeled and physically separated — no cross-contact points between PB and chocolate lines",
          "All equipment BONE DRY",
          "Verify cannabis COA — record METRC UID, potency %, weight, variance, THC/unit",
          "Preheat cooling tunnel: 45°F, belt speed 6",
        ],
        "ccps": [0, 3, 5],
        "ccp_labels": {0: "Pre-run allergen clearance — prior residue removed, supervisor signed (pass/fail)", 3: "Dedicated paddles confirmed labeled and separated (pass/fail)", 5: "Cannabis COA verified — UID / potency / weight recorded"},
        "ccp_specs": {0: {"unit": "boolean", "min": 1, "max": 1}, 3: {"unit": "boolean", "min": 1, "max": 1}, 5: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {0: "Clearance not signed: DO NOT START production — this is a hard stop.", 3: "Paddles not separated: correct and re-verify before production.", 5: "No COA or UID mismatch: halt production, contact QA."},
        "notes_required": False,
        "sign_off_roles": ["Operator", "Supervisor"],
      },
      {
        "id": "dual_temper",
        "name": "Dual Temper Setup",
        "steps": [
          "DUAL TEMPER: load 25 lbs PB wafers into Machine #1, 25 lbs chocolate into Machine #2 — both at 120°F",
          "Monitor BOTH machines with temp gun — target 100–108°F",
          "Stir EACH vessel with its DEDICATED PADDLE — no cross-contact between paddles",
          "Approximately 40 minutes each until uniformly melted",
        ],
        "ccps": [1, 2],
        "ccp_labels": {1: "Both machines internal temp (°F) — must be 100–108°F", 2: "No cross-contact between dedicated paddles (pass/fail)"},
        "ccp_specs": {1: {"unit": "F", "min": 100, "max": 108}, 2: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {1: "Either machine outside range: continue tempering, re-check every 5 min.", 2: "Cross-contact detected: stop, full allergen clean-out required before continuing."},
        "notes_required": False,
      },
      {
        "id": "cannabis_incorporation",
        "name": "Cannabis Incorporation",
        "steps": [
          "CANNABIS INCORPORATION: add cannabis to the PB vessel only — stir until homogenized",
          "Record actual cannabis weight",
          "Supervisor initials mandatory on this step",
          "Add SKU inclusions (crushed peanuts, jelly per SKU) — stir to incorporate",
        ],
        "ccps": [1],
        "ccp_labels": {1: "Actual cannabis weight recorded (g)"},
        "ccp_specs": {1: {"unit": "g", "min": 0.1, "max": 99999}},
        "corrective_actions": {1: "Record actual — any variance from COA-adjusted formula noted on BPR."},
        "notes_required": False,
        "sign_off_roles": ["Operator", "Supervisor"],
      },
      {
        "id": "pour_and_mold",
        "name": "Pour & Mold (2-Pour Process)",
        "steps": [
          "POUR 1: foot pedal — PB mixture to approximately 50% fill each cavity",
          "Feed molds through cooling tunnel — remove at output",
          "POUR 2: dispense chocolate (Machine #2) to complete fill — feed through tunnel again",
          "Record Pour 1 and Pour 2 timestamps",
        ],
        "ccps": [2],
        "ccp_labels": {2: "Pour 1 and Pour 2 timestamps logged (both required)"},
        "ccp_specs": {2: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {2: "Missing either timestamp: log deviation before releasing batch."},
        "notes_required": False,
      },
      {
        "id": "demold_qc",
        "name": "Demold & Weight QC",
        "steps": [
          "Demold — unit weight: 3 per mold, target 21.75–22.5 g average",
          "Inspect — no bloom, no cracks",
        ],
        "ccps": [0],
        "ccp_labels": {0: "Unit weight, avg of 3 per mold (g) — must be 21.75–22.5g"},
        "ccp_specs": {0: {"unit": "g", "min": 21.75, "max": 22.5}},
        "corrective_actions": {0: "Outside range or bloom present: quarantine mold, log deviation."},
        "notes_required": False,
      },
      {
        "id": "labeling_and_postrun_allergen_clearance",
        "name": "Labeling & Post-Run Allergen Clearance (Mandatory)",
        "steps": [
          "VIDEOJET TEST PRINT: supervisor approves all 5 required fields",
          "Ilapak wrap — sensor pass. Label. CRP box.",
          "POST-RUN ALLERGEN CLEARANCE: full sanitation of ALL PB-contact equipment",
          "Document clearance on Section 5 — supervisor sign-off MANDATORY",
        ],
        "ccps": [0, 2],
        "ccp_labels": {0: "Videojet test print — all 5 fields, supervisor approved (pass/fail)", 2: "Post-run allergen clearance — all PB-contact surfaces sanitized, supervisor signed (pass/fail)"},
        "ccp_specs": {0: {"unit": "boolean", "min": 1, "max": 1}, 2: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {0: "Any field missing/illegible: halt run, correct before proceeding.", 2: "Clearance not signed: batch and equipment held — cannot release or reuse equipment for non-peanut product."},
        "notes_required": False,
        "sign_off_roles": ["Operator", "Supervisor"],
      },
      {
        "id": "sanitation",
        "name": "Final Sanitation & METRC Entry",
        "steps": [
          "Confirm all PB-contact and chocolate-contact equipment fully sanitized per Section 5",
          "Complete cleaning log entry — date, equipment, method, initials",
          "METRC manufacturing activity entry within 24 hours",
        ],
        "ccps": [2],
        "ccp_labels": {2: "METRC entry completed within 24 hours (yes/no)"},
        "ccp_specs": {2: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {2: "Missed 24hr window: log deviation, file entry immediately, notify QA."},
        "notes_required": False,
      },
    ]
  },

  # ─────────────────────────────────────────────────────────────────
  # COOKIE DELIGHT BARS
  # Matches BPR-CKD-001 v2.0. Shares the punch_chocolate temper/pour
  # skeleton (single temper machine, distillate OR hash, 100–108°F,
  # 21.75–22.5g), but with a time-critical cookie embed inserted
  # between Pour 1 and Pour 2, and a pre-count/type-verification CCP
  # that punch_chocolate has no equivalent for (wrong cookie type in
  # the wrong SKU is a mislabeling risk, not just a quality miss).
  # ─────────────────────────────────────────────────────────────────
  "punch_cookie_delight": {
    "label": "Cookie Delight Bars",
    "sop_ref": "MMP-CKD-001 v1.0 / PQP-CKD-001 v1.0",
    "uom": "units",
    "phases": [
      {
        "id": "pre_production",
        "name": "Pre-Production Setup",
        "steps": [
          "All equipment BONE DRY and sanitized — verify per Section 5",
          "Verify cannabis COA (distillate or hash per SKU) — record METRC UID, potency %, required weight, actual weight, variance, THC/unit",
          "Supervisor sign-off on cannabis verification — mandatory before processing",
          "COOKIE COUNT & TYPE VERIFICATION: confirm correct cookie type for this SKU — vanilla shortbread vs chocolate shortbread",
          "Pre-count 960 cookies — record count on BPR",
          "Preheat cooling tunnel: 45°F, belt speed 6 — confirm BEFORE production",
        ],
        "ccps": [0, 1, 3, 4, 5],
        "ccp_labels": {
          0: "Equipment dryness — bone dry, zero moisture (pass/fail)",
          1: "Cannabis COA verified — UID / potency / weight / variance recorded",
          3: "Cookie type confirmed correct for this SKU (pass/fail)",
          4: "Cookies pre-counted (must equal 960)",
          5: "Cooling tunnel temp (°F) — must be 45°F, belt speed 6",
        },
        "ccp_specs": {
          0: {"unit": "boolean", "min": 1, "max": 1},
          1: {"unit": "boolean", "min": 1, "max": 1},
          3: {"unit": "boolean", "min": 1, "max": 1},
          4: {"unit": "count", "min": 960, "max": 960},
          5: {"unit": "F", "min": 43, "max": 47},
        },
        "corrective_actions": {
          0: "Any moisture detected: halt, fully dry equipment before proceeding.",
          1: "No COA or UID mismatch: halt production, contact QA.",
          3: "Wrong cookie type pulled for this SKU: halt, swap stock before production — mislabeling risk if run continues.",
          4: "Count does not equal 960: recount before starting. Do not estimate.",
          5: "Not at temp: continue preheat, do not begin pour until confirmed.",
        },
        "notes_required": False,
      },
      {
        "id": "temper",
        "name": "Temper",
        "steps": [
          "Melt chocolate wafers (milk/dark/white per SKU) at 120°F",
          "Stir until internal temp reaches 100–108°F — approximately 40 minutes",
          "Monitor continuously with temperature gun",
        ],
        "ccps": [1],
        "ccp_labels": {1: "Internal chocolate temp (°F) — must be 100–108°F"},
        "ccp_specs": {1: {"unit": "F", "min": 100, "max": 108}},
        "corrective_actions": {1: "Outside range: continue tempering, re-check every 5 min. Do not proceed until in spec."},
        "notes_required": False,
      },
      {
        "id": "cannabis_incorporation",
        "name": "Cannabis Incorporation",
        "steps": [
          "CANNABIS INCORPORATION: add cannabis to melted chocolate — record actual weight",
          "Stir minimum 40 minutes until fully homogenized — no visible oil pooling",
          "Add SKU-specific flavoring",
          "Supervisor initials mandatory on this step",
        ],
        "ccps": [0, 1],
        "ccp_labels": {0: "Actual cannabis weight recorded (g)", 1: "Incorporation — ≥40 min, homogenized, no oil pooling (pass/fail)"},
        "ccp_specs": {0: {"unit": "g", "min": 0.1, "max": 99999}, 1: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {0: "Record actual — any variance from COA-adjusted formula noted on BPR.", 1: "Oil pooling/separation after 40 min: continue stirring, do not proceed to pour."},
        "notes_required": False,
        "sign_off_roles": ["Operator", "Supervisor"],
      },
      {
        "id": "pour_and_cookie_embed",
        "name": "Pour 1, Cookie Embed & Pour 2",
        "steps": [
          "POUR 1: foot pedal dispense — approximately 50% fill into each mold cavity",
          "COOKIE EMBED WHILE HOT: place exactly 1 cookie per cavity, centered, while chocolate is still hot",
          "Feed molds into cooling tunnel IMMEDIATELY — no delay, chocolate must still be molten around the cookie",
          "Remove molds at tunnel output",
          "POUR 2: fill remaining cavity with chocolate cap — feed through tunnel again",
          "Record Pour 1 and Pour 2 timestamps",
        ],
        "ccps": [1, 5],
        "ccp_labels": {
          1: "Cookie embed — centered, embedded while hot, fed into tunnel immediately (pass/fail)",
          5: "Pour 1 and Pour 2 timestamps logged (both required)",
        },
        "ccp_specs": {1: {"unit": "boolean", "min": 1, "max": 1}, 5: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {
          1: "Cookie not embedded while hot, off-center, or tunnel feed delayed: reject cavity — do not proceed with a cooled or misaligned embed.",
          5: "Missing either timestamp: log deviation, do not release batch until resolved.",
        },
        "notes_required": False,
      },
      {
        "id": "demold_qc",
        "name": "Demold & Weight QC",
        "steps": [
          "Demold: invert over parchment-lined table, tap firmly",
          "Confirm cookie is visible and intact at the base of each bar",
          "UNIT WEIGHT SPOT CHECK: weigh 3 units per mold — target 21.75–22.5 g average",
          "Confirm cookie remains intact inside each bar — not shattered or displaced",
        ],
        "ccps": [1, 2],
        "ccp_labels": {1: "Cookie intact and visible at base (pass/fail)", 2: "Unit weight, avg of 3 per mold (g) — must be 21.75–22.5g"},
        "ccp_specs": {1: {"unit": "boolean", "min": 1, "max": 1}, 2: {"unit": "g", "min": 21.75, "max": 22.5}},
        "corrective_actions": {1: "Cookie broken/displaced/not visible: quarantine mold, log deviation.", 2: "Outside range: quarantine mold, log deviation."},
        "notes_required": False,
      },
      {
        "id": "labeling_packaging",
        "name": "Labeling & Packaging",
        "steps": [
          "VIDEOJET TEST PRINT: supervisor approves all 5 required fields, font ≥6pt",
          "Ilapak Carrera 500 foil wrap — verify digital sensor pass on each unit",
          "Insert into CRP box",
          "Record total packaged unit count",
        ],
        "ccps": [0, 1],
        "ccp_labels": {0: "Videojet test print — all 5 fields, supervisor approved (pass/fail)", 1: "Ilapak sensor pass — all units (pass/fail)"},
        "ccp_specs": {0: {"unit": "boolean", "min": 1, "max": 1}, 1: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {0: "Any field missing/illegible: halt run, correct before proceeding.", 1: "Sensor fail on any unit: pull unit, do not package."},
        "notes_required": False,
        "sign_off_roles": ["Operator", "Supervisor"],
      },
      {
        "id": "sanitation",
        "name": "Post-Run Sanitation",
        "steps": [
          "Temper machine and molds — return to BONE DRY, no moisture residue",
          "Cooling tunnel and Ilapak tracks — sanitize per Section 5",
          "Complete cleaning log entry — date, equipment, method, initials",
          "METRC manufacturing activity entry within 24 hours",
        ],
        "ccps": [3],
        "ccp_labels": {3: "METRC entry completed within 24 hours (yes/no)"},
        "ccp_specs": {3: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {3: "Missed 24hr window: log deviation, file entry immediately, notify QA."},
        "notes_required": False,
      },
    ]
  },

  # ─────────────────────────────────────────────────────────────────
  # SOLVENTLESS MALT BALLS 100mg
  # Matches BPR-MLT-001 v2.0. Structurally unlike the punch_chocolate
  # family (no temper/mold/pour) — this is a panning process spanning
  # TWO CALENDAR DAYS with a mandatory 24-hour rest between coating and
  # glossing, and independent humidity CCPs gating both days. Do NOT
  # rush the Day 1 → Day 2 boundary or treat this as a same-day recipe.
  # ─────────────────────────────────────────────────────────────────
  "punch_malt_balls": {
    "label": "Solventless Malt Balls 100mg",
    "sop_ref": "MMP-MLT-001 v1.0 / PQP-MLT-001 v1.0",
    "uom": "units",
    "phases": [
      {
        "id": "pre_production_day1",
        "name": "Pre-Production Setup — Day 1",
        "steps": [
          "Panner machine fully cleaned, sanitized, DRY — line bin with new plastic liner",
          "Verify hash COA — record METRC UID, batch#, potency %, required weight, actual weight, variance, THC/unit",
          "Supervisor sign-off on cannabis verification — mandatory before processing",
          "HUMIDITY CHECK — DAY 1: record humidity reading — must be 30–50% RH before coating begins",
        ],
        "ccps": [0, 1, 3],
        "ccp_labels": {
          0: "Panner clean, sanitized, dry, new liner (pass/fail)",
          1: "Cannabis COA verified — UID / potency / weight / variance recorded",
          3: "Day 1 humidity (%RH) — must be 30–50% RH before coating",
        },
        "ccp_specs": {
          0: {"unit": "boolean", "min": 1, "max": 1},
          1: {"unit": "boolean", "min": 1, "max": 1},
          3: {"unit": "%RH", "min": 30, "max": 50},
        },
        "corrective_actions": {
          0: "Any residue, moisture, or old liner present: re-clean and re-line before proceeding.",
          1: "No COA or UID mismatch: halt production, contact QA.",
          3: "Outside 30–50% RH: delay coating and document. Do not begin outside range.",
        },
        "notes_required": False,
      },
      {
        "id": "chocolate_cannabis_prep",
        "name": "Chocolate Melt & Cannabis Incorporation",
        "steps": [
          "Melt chocolate wafers at 120°F",
          "Stir until internal temp reaches 100–108°F",
          "Add hash — stir until homogenized, no oil pooling",
          "Record actual hash weight added",
          "Supervisor initials mandatory on this step",
        ],
        "ccps": [1, 3],
        "ccp_labels": {1: "Internal chocolate temp (°F) — must be 100–108°F", 3: "Actual hash weight recorded (g) — per MMP ±0.2g"},
        "ccp_specs": {1: {"unit": "F", "min": 100, "max": 108}, 3: {"unit": "g", "min": 0.1, "max": 99999}},
        "corrective_actions": {1: "Outside range: continue tempering, re-check every 5 min.", 3: "Record actual — any variance from COA-adjusted formula noted on BPR."},
        "notes_required": False,
        "sign_off_roles": ["Operator", "Supervisor"],
      },
      {
        "id": "panning_coat",
        "name": "Panning — Coat (Day 1)",
        "steps": [
          "Load malt ball centers into panner",
          "Set cold air to 44°F",
          "Set sprayer cycle: 1 minute on / 20 seconds off",
          "Tumble at 45° rotation",
          "Spray ALL chocolate onto malt ball centers — verify uniform coating, no bare spots, before switching to hot air",
          "Switch to hot air at 113°F for approximately 10 minutes — monitor closely, do not overheat",
          "Confirm chocolate is smooth, not separating",
          "Switch back to cold air — tumble approximately 10 minutes to harden",
        ],
        "ccps": [1, 5, 6],
        "ccp_labels": {
          1: "Cold air temp (°F) — must be 44°F",
          5: "Hot air temp (°F) — must be 113°F, ~10 min",
          6: "Chocolate coating texture — smooth, not separating (pass/fail)",
        },
        "ccp_specs": {
          1: {"unit": "F", "min": 42, "max": 46},
          5: {"unit": "F", "min": 111, "max": 115},
          6: {"unit": "boolean", "min": 1, "max": 1},
        },
        "corrective_actions": {
          1: "Outside range: adjust panner, re-verify before spraying.",
          5: "Overheating risk: reduce heat immediately, monitor continuously.",
          6: "Separation/graininess observed: stop hot air cycle, cool and reassess before continuing.",
        },
        "notes_required": False,
      },
      {
        "id": "rest_24hr",
        "name": "24-Hour Rest (Mandatory Before Glossing)",
        "steps": [
          "24-HOUR REST: remove product from panner immediately after Day 1 coating",
          "Record rest START time",
          "Hold undisturbed minimum 24 hours before glossing — DO NOT rush",
          "Record rest END time and confirm 24 hours has elapsed before proceeding to Day 2",
        ],
        "ccps": [3],
        "ccp_labels": {3: "Rest duration (hours) — must be ≥24 hrs before glossing"},
        "ccp_specs": {3: {"unit": "hours", "min": 24, "max": 72}},
        "corrective_actions": {3: "Less than 24 hrs elapsed: continue rest, do not begin Day 2 gloss steps early."},
        "notes_required": False,
      },
      {
        "id": "day2_setup_and_humidity",
        "name": "Day 2 Setup & Humidity Check",
        "steps": [
          "DAY 2: CLEAN PANNER COMPLETELY before adding any polishing compounds — chocolate residue ruins gloss drying",
          "HUMIDITY CHECK — DAY 2: confirm 30–50% RH, air temp approximately 60°F",
          "Record humidity and air temp on BPR",
        ],
        "ccps": [0, 1],
        "ccp_labels": {0: "Panner clean — no chocolate residue before gloss compounds added (pass/fail)", 1: "Day 2 humidity (%RH) — must be 30–50% RH"},
        "ccp_specs": {0: {"unit": "boolean", "min": 1, "max": 1}, 1: {"unit": "%RH", "min": 30, "max": 50}},
        "corrective_actions": {0: "Any chocolate residue present: re-clean panner fully before proceeding.", 1: "Outside 30–50% RH: DO NOT gloss — delay and document."},
        "notes_required": False,
      },
      {
        "id": "glossing_and_sealing",
        "name": "Glossing & Sealing",
        "steps": [
          "1st Gloss: apply 3 g PO-TT154A per kg product — run 10 minutes",
          "Record g/kg and run time for 1st gloss",
          "2nd Gloss: apply 2 g PO-TT154A per kg — run 10 minutes",
          "Record g/kg and run time for 2nd gloss",
          "3rd Gloss (optional): apply 1 g per kg if additional shine needed — run 10 minutes, inspect before deciding",
          "SEALING: 1 application GZ-F400 at 2 g per kg — run 5 minutes",
        ],
        "ccps": [1, 3, 5],
        "ccp_labels": {
          1: "1st gloss applied (g/kg) — target 3 g/kg, 10 min run",
          3: "2nd gloss applied (g/kg) — target 2 g/kg, 10 min run",
          5: "Sealing (GZ-F400) applied (g/kg) — target 2 g/kg, 5 min run",
        },
        "ccp_specs": {
          1: {"unit": "g/kg", "min": 3, "max": 3},
          3: {"unit": "g/kg", "min": 2, "max": 2},
          5: {"unit": "g/kg", "min": 2, "max": 2},
        },
        "corrective_actions": {
          1: "Amount/time off target: record actual, note deviation.",
          3: "Amount/time off target: record actual, note deviation.",
          5: "Sealing incomplete or off target: re-run before packaging — seal integrity depends on this step.",
        },
        "notes_required": False,
      },
      {
        "id": "labeling_packaging",
        "name": "Labeling & Packaging",
        "steps": [
          "VIDEOJET TEST PRINT: supervisor approves all 5 required fields, font ≥6pt",
          "Feed packaging bottom-up",
          "Fill each CR tube with exactly 10 quality-approved malt balls",
          "Inspect for foreign material",
          "Apply CR cap",
          "Apply CA warning tamper-proof label across cap-to-tube junction",
          "Pull-test label seam — must be continuous across junction, no gaps",
        ],
        "ccps": [0, 6],
        "ccp_labels": {0: "Videojet test print — all 5 fields, supervisor approved (pass/fail)", 6: "Tamper label pull-test — continuous across cap-to-tube junction (pass/fail)"},
        "ccp_specs": {0: {"unit": "boolean", "min": 1, "max": 1}, 6: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {0: "Any field missing/illegible: halt run, correct before proceeding.", 6: "Gap or fail on pull-test: re-apply label, re-test before packaging."},
        "notes_required": False,
        "sign_off_roles": ["Operator", "Supervisor"],
      },
      {
        "id": "sanitation",
        "name": "Post-Run Sanitation",
        "steps": [
          "Post-production clean-down — complete Section 5 end times",
          "Panner, sprayer/injector, humidity sensor — clean and store per Section 5",
          "Complete cleaning log entry — date, equipment, method, initials",
          "METRC manufacturing activity entry within 24 hours",
        ],
        "ccps": [3],
        "ccp_labels": {3: "METRC entry completed within 24 hours (yes/no)"},
        "ccp_specs": {3: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {3: "Missed 24hr window: log deviation, file entry immediately, notify QA."},
        "notes_required": False,
      },
    ]
  },

  # ─────────────────────────────────────────────────────────────────
  # STINGER PRE-ROLLS 2.5g 5-PACK (Flower + Distillate + Kief)
  # Matches BPR-STG-001 v2.0. Distinct from Rosin Rocket — Stinger uses
  # spray + paint + kief-roll on ground flower loaded into an ActionPac
  # cone filler, with a mandatory 4-6hr post-roll dry before jarring.
  # Rocket uses whole-flower hand-rolling with a frozen pre-weighed
  # rosin worm — no ActionPac, no kief, no dry-time gate. These are
  # NOT interchangeable processes; Rocket gets its own family.
  # ─────────────────────────────────────────────────────────────────
  "punch_stinger": {
    "label": "Stinger Pre-Rolls 2.5g 5-Pack",
    "sop_ref": "MMP-STG-001 v1.0 / PQP-STG-001 v1.0",
    "uom": "units",
    "phases": [
      {
        "id": "pre_production",
        "name": "Pre-Production Setup",
        "steps": [
          "ISO-clean grinder, spray gun, magnetic stirrer, ActionPac, paint brushes, and rolling trays — air dry",
          "Verify COAs for flower, distillate, AND kief — all 3 required. Record all 3 METRC UIDs, all 3 potencies, all 3 weights.",
          "Supervisor sign-off on all 3 cannabis verifications — mandatory before processing",
          "Apply strain-specific sticker to each glass jar BEFORE filling — confirm sticker matches strain being produced",
        ],
        "ccps": [0, 1, 3],
        "ccp_labels": {
          0: "Equipment clean and dry — grinder, spray gun, stirrer, ActionPac, brushes, trays (pass/fail)",
          1: "All 3 cannabis COAs verified — flower / distillate / kief UIDs, potencies, weights recorded",
          3: "Jar strain sticker matches batch strain (pass/fail)",
        },
        "ccp_specs": {
          0: {"unit": "boolean", "min": 1, "max": 1},
          1: {"unit": "boolean", "min": 1, "max": 1},
          3: {"unit": "boolean", "min": 1, "max": 1},
        },
        "corrective_actions": {
          0: "Any residue present: re-clean before proceeding.",
          1: "Any of the 3 COAs missing or UID mismatch: halt production, contact QA.",
          3: "Sticker/strain mismatch: correct before filling — do not fill mismatched jars.",
        },
        "notes_required": False,
      },
      {
        "id": "grind_and_coat",
        "name": "Grind & Spray Coat",
        "steps": [
          "Grind 10 lbs flower to shake consistency using commercial grinder — uniform grind, no whole buds",
          "SPRAY: mix 9.5g terpenes + 300g distillate in spray gun — spray evenly over all ground flower, no dry spots",
          "PAINTING MIX: combine remaining terpenes + remaining distillate — magnetic stir until uniform. This is the painting solution used later.",
        ],
        "ccps": [1],
        "ccp_labels": {1: "Spray coat coverage — no dry spots on flower (pass/fail)"},
        "ccp_specs": {1: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {1: "Dry spots present: re-spray affected flower before proceeding to fill."},
        "notes_required": False,
      },
      {
        "id": "cone_fill_calibration",
        "name": "Cone Fill Calibration (Mandatory Before Production)",
        "steps": [
          "ACTIONPAC CALIBRATION: load coated flower into ActionPac — verify setting: 0.5g per cone",
          "Run 3 test cones. Weigh all 3 on certified scale. Confirm average within 0.5g ±0.05g. MANDATORY before production run.",
          "Fill cones. Spot-weigh 5 cones per batch. Record on CCP log.",
          "Twist end of each cone to close. Snip excess paper.",
        ],
        "ccps": [1, 2],
        "ccp_labels": {
          1: "ActionPac calibration weight, avg of 3 test cones (g) — must be 0.5g ±0.05g",
          2: "Production spot-check, avg of 5 cones per batch (g) — must be 0.5g ±0.05g",
        },
        "ccp_specs": {1: {"unit": "g", "min": 0.45, "max": 0.55}, 2: {"unit": "g", "min": 0.45, "max": 0.55}},
        "corrective_actions": {
          1: "Outside tolerance: adjust ActionPac, re-run 3-cone check. Do NOT begin production run until in spec.",
          2: "Outside tolerance: pause run, re-calibrate, re-check before continuing.",
        },
        "notes_required": False,
      },
      {
        "id": "painting_and_kief",
        "name": "Painting & Kief Roll",
        "steps": [
          "PAINTING: using soft bristle brush, coat each joint paper evenly with painting mixture — uniform coat, no drips, no bare patches",
          "KIEF ROLLING: IMMEDIATELY roll the wet joint in kief tray — kief adheres to the distillate coating. Must be done while still wet.",
        ],
        "ccps": [0, 1],
        "ccp_labels": {
          0: "Painting coat — uniform, no drips, no bare patches (pass/fail)",
          1: "Kief adhesion — rolled while wet, full coverage (pass/fail)",
        },
        "ccp_specs": {0: {"unit": "boolean", "min": 1, "max": 1}, 1: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {
          0: "Drips or bare patches: touch up before kief roll — coating must be complete before kief step.",
          1: "Joint dried before kief rolling: kief will not adhere — reject and redo from painting step.",
        },
        "notes_required": False,
      },
      {
        "id": "drying",
        "name": "Drying (4-6 Hour Minimum, Mandatory Before Jarring)",
        "steps": [
          "DRYING: place finished joints on clean rolling tray immediately after kief rolling",
          "Record drying START time",
          "Hold undisturbed minimum 4–6 hours at room temperature — DO NOT package wet",
          "Record drying END time and confirm total drying duration",
        ],
        "ccps": [3],
        "ccp_labels": {3: "Drying duration (hours) — must be ≥4–6 hrs before jarring"},
        "ccp_specs": {3: {"unit": "hours", "min": 4, "max": 24}},
        "corrective_actions": {3: "Less than 4 hrs elapsed: continue drying, do not proceed to jarring."},
        "notes_required": False,
      },
      {
        "id": "qc_jarring",
        "name": "Dryness QC & Jarring",
        "steps": [
          "Verify joints fully dry — firm to touch, no tackiness",
          "Place 5 approved Stinger joints into 1 glass CR jar",
          "Apply color-coordinated cap matching strain",
        ],
        "ccps": [0],
        "ccp_labels": {0: "Joint dryness — firm to touch, no tackiness (pass/fail)"},
        "ccp_specs": {0: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {0: "Tacky or soft joints: continue drying, do not jar until firm."},
        "notes_required": False,
      },
      {
        "id": "labeling_packaging",
        "name": "Labeling & Packaging",
        "steps": [
          "Apply required info sticker — verify all 5 fields: product name, batch#, METRC UID, mfg date, THC%",
          "Supervisor label approval — mandatory before full labeling run",
          "25CT distribution packaging — 20 jars per shipper",
          "Count and record total packaged units",
        ],
        "ccps": [0],
        "ccp_labels": {0: "Label verification — all 5 fields present, supervisor approved (pass/fail)"},
        "ccp_specs": {0: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {0: "Any field missing/illegible: halt labeling, correct before proceeding."},
        "notes_required": False,
        "sign_off_roles": ["Operator", "Supervisor"],
      },
      {
        "id": "sanitation",
        "name": "Post-Run Sanitation",
        "steps": [
          "Post-production clean-down — complete Section 5 end times",
          "ISO-clean grinder, spray gun, ActionPac, and brushes — inspect for residue",
          "Complete cleaning log entry — date, equipment, method, initials",
          "METRC manufacturing activity entry within 24 hours",
        ],
        "ccps": [3],
        "ccp_labels": {3: "METRC entry completed within 24 hours (yes/no)"},
        "ccp_specs": {3: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {3: "Missed 24hr window: log deviation, file entry immediately, notify QA."},
        "notes_required": False,
      },
    ]
  },

  # ─────────────────────────────────────────────────────────────────
  # ROSIN ROCKET PRE-ROLL 1.6g SINGLE (Flower + Live Rosin Worm)
  # Matches BPR-RKT-001 v2.0. Distinct from Stinger — Rocket is a
  # hand-rolled single joint built around a frozen pre-weighed rosin
  # worm inserted mid-roll (must stay frozen until the moment of use,
  # then placed and rolled QUICKLY before it softens). No ActionPac,
  # no kief coat, no spray/paint stage, no multi-hour dry-time gate —
  # do not route this SKU to punch_stinger.
  # ─────────────────────────────────────────────────────────────────
  "rosin_rocket": {
    "label": "Rosin Rocket Pre-Roll 1.6g Single",
    "sop_ref": "MMP-RKT-001 v1.0 / PQP-RKT-001 v1.0",
    "uom": "units",
    "phases": [
      {
        "id": "pre_production",
        "name": "Pre-Production Setup",
        "steps": [
          "ISO-wipe all rolling trays, tools, and plastic weighing cups — air dry",
          "Verify flower AND rosin COAs — both required. Record both METRC UIDs, both potencies, both weights.",
          "Supervisor sign-off on both cannabis verifications — mandatory before processing",
        ],
        "ccps": [0, 1],
        "ccp_labels": {
          0: "Equipment clean and dry — trays, tools, cups (pass/fail)",
          1: "Both cannabis COAs verified — flower / rosin UIDs, potencies, weights recorded",
        },
        "ccp_specs": {0: {"unit": "boolean", "min": 1, "max": 1}, 1: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {
          0: "Any residue present: re-clean before proceeding.",
          1: "Either COA missing or UID mismatch: halt production, contact QA.",
        },
        "notes_required": False,
      },
      {
        "id": "pre_weigh",
        "name": "Flower & Rosin Worm Pre-Weigh",
        "steps": [
          "FLOWER PRE-WEIGH: pre-weigh flower into clean plastic cups at 1.3g per cup (±0.05g). Seal and bag in groups of 100.",
          "ROSIN WORM PRE-WEIGH: pre-weigh rosin at 0.3g balls (±0.05g). Roll each into a thin worm shape.",
          "Place rosin worms on parchment in freezer — keep FROZEN until the moment of use",
          "Glass tip prep: apply GlueGar (non-toxic) to adhere paper crutch to each glass tip — allow to dry. NO saliva.",
        ],
        "ccps": [0, 1],
        "ccp_labels": {
          0: "Flower pre-weigh per cup (g) — must be 1.3g ±0.05g",
          1: "Rosin worm pre-weigh (g) — must be 0.3g ±0.05g",
        },
        "ccp_specs": {0: {"unit": "g", "min": 1.25, "max": 1.35}, 1: {"unit": "g", "min": 0.25, "max": 0.35}},
        "corrective_actions": {
          0: "Outside tolerance: adjust and re-weigh cup before sealing.",
          1: "Outside tolerance: adjust and re-weigh worm before freezing.",
        },
        "notes_required": False,
      },
      {
        "id": "rolling_assembly",
        "name": "Rolling Assembly",
        "steps": [
          "Grind 1 cup of pre-weighed flower per rolling session on a clean rolling tray",
          "Place rolling paper on tray — position glass tip at one end, glass end protruding beyond paper",
          "Distribute ground flower evenly along paper — no gaps",
        ],
        "ccps": [],
        "ccp_labels": {},
        "ccp_specs": {},
        "corrective_actions": {},
        "notes_required": False,
      },
      {
        "id": "rosin_placement_and_seal",
        "name": "Rosin Placement & Seal (Time-Critical)",
        "steps": [
          "ROSIN: remove 1 worm from freezer. Place on top of flower approximately 1/4 from the tip end.",
          "Work QUICKLY — rosin softens fast once removed from freezer. Roll immediately after placement.",
          "Press and roll paper into a cylinder — even distribution, no voids",
          "Apply GlueGar along the gum line. Roll final flap to seal. NO saliva.",
          "Tap glass tip on tray to pack flower. Fill remaining space. Leave ~3mm paper at tip end, twist to close. Apply logo sticker.",
        ],
        "ccps": [0, 3],
        "ccp_labels": {
          0: "Rosin worm removed from freezer immediately before placement (pass/fail)",
          3: "Seal — GlueGar only on gum line, no saliva contact (pass/fail)",
        },
        "ccp_specs": {0: {"unit": "boolean", "min": 1, "max": 1}, 3: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {
          0: "Worm sat out too long and softened before placement/roll: discard worm, use a fresh frozen one.",
          3: "Any saliva contact: reject unit — do not package. Redo with GlueGar only.",
        },
        "notes_required": False,
      },
      {
        "id": "unit_weight_qc",
        "name": "Unit Weight QC",
        "steps": [
          "UNIT WEIGHT CHECK: weigh each finished joint on certified scale",
          "Confirm target: 1.6g ±0.1g. Record on CCP log.",
          "Out-of-range: rework or reject the unit",
        ],
        "ccps": [1],
        "ccp_labels": {1: "Finished joint weight (g) — must be 1.6g ±0.1g"},
        "ccp_specs": {1: {"unit": "g", "min": 1.5, "max": 1.7}},
        "corrective_actions": {1: "Outside tolerance: rework if possible, otherwise reject — do not package out-of-spec units."},
        "notes_required": False,
      },
      {
        "id": "tube_and_pouch_seal",
        "name": "Tube Insert & Pouch Seal",
        "steps": [
          "Insert 1 quality-approved Rocket into glass CR tube. Apply plastic cap securely.",
          "Insert glass tube into 3-sided CRP pouch. Seal using band sealer at 180°F. Inspect seal integrity.",
        ],
        "ccps": [1],
        "ccp_labels": {1: "Pouch seal — 180°F, continuous, no gaps (pass/fail)"},
        "ccp_specs": {1: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {1: "Seal gap or failure: re-seal before packaging. Do not ship units with an incomplete seal."},
        "notes_required": False,
      },
      {
        "id": "labeling_packaging",
        "name": "Labeling & Packaging",
        "steps": [
          "Apply required info sticker — verify all 5 fields: product name, batch#, METRC UID, mfg date, THC%",
          "Supervisor label approval — mandatory before full labeling run",
          "10CT case packaging — count and record total packaged units",
        ],
        "ccps": [0],
        "ccp_labels": {0: "Label verification — all 5 fields present, supervisor approved (pass/fail)"},
        "ccp_specs": {0: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {0: "Any field missing/illegible: halt labeling, correct before proceeding."},
        "notes_required": False,
        "sign_off_roles": ["Operator", "Supervisor"],
      },
      {
        "id": "sanitation",
        "name": "Post-Run Sanitation",
        "steps": [
          "Post-production clean-down — complete Section 5 end times",
          "ISO-wipe rolling trays, tools, and cups — air dry",
          "Verify freezer temp and clean interior per Section 5",
          "Complete cleaning log entry — date, equipment, method, initials",
          "METRC manufacturing activity entry within 24 hours",
        ],
        "ccps": [4],
        "ccp_labels": {4: "METRC entry completed within 24 hours (yes/no)"},
        "ccp_specs": {4: {"unit": "boolean", "min": 1, "max": 1}},
        "corrective_actions": {4: "Missed 24hr window: log deviation, file entry immediately, notify QA."},
        "notes_required": False,
      },
    ]
  },

}

DR_NORMS_PREFIXES = ("dr. norm", "dr norm", "dr.norm", "norms", "doctor norm")

def detect_product_family(item_name: str, category: str = "",
                           bpr_type: str = "") -> str:
    """
    bpr_type param added: "wash" or "press" routes rosin correctly.
    Called from /bpr/create with the extra field.

    IMPORTANT: every return value below is validated against BPR_PHASES
    before this function returns (see the safety check at the bottom).
    That check exists because this function previously returned family
    names — "punch_chocolate", "punch_cookie_delight", "punch_malt_balls",
    "punch_stinger", "rosin_aio", "rosin_rocket" — that had no matching
    entry in BPR_PHASES, which meant creating a BPR for any of those
    products would fail. Do NOT add a new `return "some_family"` line
    here without also adding "some_family" to BPR_PHASES — the safety
    check will otherwise silently fall back to None (unmapped) rather
    than crash, but the product still won't route anywhere useful.
    """
    n = (item_name or "").lower().strip()
    c = (category or "").lower().strip()
    t = (bpr_type or "").lower().strip()
    family = None

    # Dr. Norm's — runs first
    is_norms = any(n.startswith(p) for p in DR_NORMS_PREFIXES)
    if is_norms:
        if any(x in n for x in ("sleep bite", "sleep bites", "sleep brownie")):
            family = "dr_norms_brownie_sleep"
        elif any(x in n for x in ("brownie", "blondie", "pb cup", "peanut butter cup")):
            family = "dr_norms_brownie"
        elif any(x in n for x in ("nano", "cookies & cream", "cookies and cream", "cookies n cream")):
            family = "dr_norms_cookie_nano"
        elif any(x in n for x in ("rkt", "rice krispy", "rice krispie",
                                    "krispie treat", "krispy treat", "matcha")):
            family = "dr_norms_rkt"
        else:
            family = "dr_norms_cookie"

    # Rosin AIO Vape (.5g Disp / 1g AIO) — multi-day decarb, NOT the
    # generic "vapes" fill family. Must be checked BEFORE the general
    # "live rosin" wash/press check below, since "rosin vape" also
    # contains "rosin".
    elif "rosin aio" in n or "rosin vape" in n:
        family = "rosin_vape_decarb"

    # Live Rosin Concentrate (wash / press) — split by bpr_type.
    # Excludes rosin vape/AIO, already handled above.
    elif "live rosin" in n and "vape" not in n and "aio" not in n:
        if t == "wash":
            family = "rosin_wash"
        else:
            family = "rosin_press"  # covers "press" and default (finished-product batches)

    elif "rocket" in n:
        family = "rosin_rocket"

    # BHO
    elif "bho badder" in n or "bho shatter" in n:
        family = "bho_badder"

    # Edibles
    elif "gummies" in n or "asteroids" in n:
        family = "gummies"
    elif "malt balls" in n:
        family = "punch_malt_balls"
    elif "punchbar" in n or "chocolate" in n:
        # Sugar-Free and PB Combo must be checked BEFORE the generic
        # "punchbar"/"chocolate" fallback — each has its own family
        # with genuinely different CCPs (SF: 87°F hard stop / seeding
        # method. PB Combo: dedicated allergen-critical equipment).
        if any(x in n for x in ("sugar-free", "sugar free", " sf ", "-sf")) or n.endswith(" sf"):
            family = "punch_chocolate_sf"
        elif any(x in n for x in ("peanut butter", "pb combo", " pb ")) or n.endswith(" pb"):
            family = "punch_chocolate_pb"
        else:
            family = "punch_chocolate"
    elif "cookie delight" in n:
        family = "punch_cookie_delight"
    elif "stinger" in n:
        family = "punch_stinger"

    # Vapes — 510, TEMPO AIO, Tempo Live Resin. Checked after the rosin
    # vape/AIO branch above so "rosin aio" doesn't fall through to here.
    elif "tempo" in n or "aio" in n or "distillate" in n or \
         "510" in n or "vape" in n:
        family = "vapes"

    # Category fallback
    elif c == "rosin_wash":
        family = "rosin_wash"
    elif "concentrate" in c or "rosin" in c:
        family = "rosin_press"
    elif "vape" in c or "cartridge" in c:
        family = "vapes"
    elif "edible" in c:
        family = "gummies"

    # Safety net: never hand back a family key that BPR_PHASES doesn't
    # actually define. All families this router can return are now
    # built (as of this pass — if you add a new `elif ... family =
    # "something_new"` branch above, make sure "something_new" is
    # added to BPR_PHASES too, or it will silently fall back to None).
    if family is not None and family not in BPR_PHASES:
        return None

    return family
