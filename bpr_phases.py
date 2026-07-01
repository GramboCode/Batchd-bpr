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
        "ccps": [7],
        "ccp_labels": {7: "THC Distillate weight (g)"},
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
          "Wait until the gelatin hardens (5 mins approx); then cut into smaller pieces to dissolve easier" ,
          "Before adding gelatin mixture, reduce the simmering pot down to 310°F",
          "Monitor temperature — reach minimum 300°F before combining mixtures"
          "At the same time, combine the heated mixture, gelatin mixture, and the citric acid in the induction pot. Continue to stir",
          "Once the citric Acid is fully dissolved, please add the distillate (and soy lecithin if required)",
          "Continue to stir until final mixture is FULLY DISSOLVED",
          "Verify temperature does not exceed 330°F",
          "Record the weight of the total mixture",
          
        ],
        "ccps": [6, 7],
        "ccp_labels": {6: "Temperature before Gelatin (°F) — must be 300–320°F", 7: "Temperature confirmed below 340°F (yes/no)"},
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
  # TEMPO VAPES / DISTILLATE VAPES (510 + TEMPO AIO)
  # ─────────────────────────────────────────────────────────────────
  "vapes": {
    "label": "Vape Cartridges / AIO (Distillate & Live Rosin)",
    "sop_ref": "P007 / MMP-DVP-001",
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



DR_NORMS_PREFIXES = ("dr. norm", "dr norm", "dr.norm", "norms", "doctor norm")

def detect_product_family(item_name: str, category: str = "") -> str:
    """
    Maps a product name / category to a BPR phase family key.
    Returns the key or None if not recognized.
    Dr. Norm's detection runs first — before generic keyword checks.
    """
    n = (item_name or "").lower().strip()
    c = (category or "").lower().strip()

    # Dr. Norm's detection (runs FIRST)
    is_norms = any(n.startswith(p) for p in DR_NORMS_PREFIXES)
    if is_norms:
        # Sleep Bites — dual cannabinoid, own key
        if any(x in n for x in ("sleep bite", "sleep bites", "sleep brownie")):
            return "dr_norms_brownie_sleep"
        # Brownie / Blondie / PB Cup
        if any(x in n for x in ("brownie", "blondie", "pb cup", "peanut butter cup")):
            return "dr_norms_brownie"
        # NANO cookies — own key
        if any(x in n for x in ("nano", "cookies & cream", "cookies and cream", "cookies n cream")):
            return "dr_norms_cookie_nano"
        # RKT
        if any(x in n for x in ("rkt", "rice krispy", "rice krispie",
                                  "krispie treat", "krispy treat", "matcha")):
            return "dr_norms_rkt"
        # Standard cookies — default fallback for Dr. Norm's
        return "dr_norms_cookie"

    # Existing Punch / Tempo detection (unchanged)
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

