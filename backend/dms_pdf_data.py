"""GO OIL Distributor Price List (MAY'26) — extracted from official PDF.
This is the source of truth for the initial Product Master + Price Circular.
"""

CIRCULAR_TITLE = "GO OIL Distributor Price Circular — MAY'26"
CIRCULAR_EFFECTIVE_DATE = "2026-05-01"

# Each row = one SKU (product) with its MAY'26 pricing.
# Product Master (visible in UI): category, material_description, grade_specs, pack_size
# Price Circular (separate module): mrp, dlp, distributor_margin_pct, cash_coupon, foc_benefits, monthly_gift, trade_discount
PDF_ROWS = [
    # ── MCO — SYNTHETIC BLEND ──
    {"category": "MCO — Synthetic Blend", "material_description": "POWER 4T 15W50", "grade_specs": "SN",   "pack_size": "2.5 L", "mrp": 1150, "dlp": 845, "margin_pct": 9,  "cash_coupon": "₹50 — ₹100", "foc_benefits": "",       "monthly_gift": "",   "trade_discount": "Available"},
    {"category": "MCO — Synthetic Blend", "material_description": "POWER 4T 20W40", "grade_specs": "SN",   "pack_size": "1 L",   "mrp": 498,  "dlp": 334, "margin_pct": 9,  "cash_coupon": "",           "foc_benefits": "FOC 9+1","monthly_gift": "",   "trade_discount": "Available"},
    {"category": "MCO — Synthetic Blend", "material_description": "POWER 4T 20W40", "grade_specs": "SN",   "pack_size": "0.9 L", "mrp": 464,  "dlp": 312, "margin_pct": 9,  "cash_coupon": "",           "foc_benefits": "FOC 9+1","monthly_gift": "",   "trade_discount": "Available"},
    {"category": "MCO — Synthetic Blend", "material_description": "POWER 4T 10W30", "grade_specs": "SN",   "pack_size": "1 L",   "mrp": 506,  "dlp": 339, "margin_pct": 9,  "cash_coupon": "",           "foc_benefits": "FOC 9+1","monthly_gift": "",   "trade_discount": "Available"},
    {"category": "MCO — Synthetic Blend", "material_description": "POWER 4T 10W30", "grade_specs": "SN",   "pack_size": "0.9 L", "mrp": 472,  "dlp": 317, "margin_pct": 9,  "cash_coupon": "",           "foc_benefits": "FOC 9+1","monthly_gift": "",   "trade_discount": "Available"},
    {"category": "MCO — Synthetic Blend", "material_description": "POWER 4T 10W30", "grade_specs": "SN",   "pack_size": "0.8 L", "mrp": 434,  "dlp": 291, "margin_pct": 9,  "cash_coupon": "",           "foc_benefits": "FOC 9+1","monthly_gift": "",   "trade_discount": "Available"},
    {"category": "MCO — Synthetic Blend", "material_description": "10W30 COMBO",     "grade_specs": "SN",   "pack_size": "0.8 L", "mrp": 445,  "dlp": 298, "margin_pct": 9,  "cash_coupon": "",           "foc_benefits": "",       "monthly_gift": "",   "trade_discount": "Available"},
    {"category": "MCO — Synthetic Blend", "material_description": "FORK OIL",        "grade_specs": "SN",   "pack_size": "175 ml","mrp": 97,   "dlp": 49,  "margin_pct": 9,  "cash_coupon": "",           "foc_benefits": "",       "monthly_gift": "",   "trade_discount": ""},

    # ── MCO — SUPER ──
    {"category": "MCO — Super", "material_description": "SUPER 4T 20W40", "grade_specs": "SL", "pack_size": "1 L",   "mrp": 366, "dlp": 262, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹10",  "trade_discount": ""},
    {"category": "MCO — Super", "material_description": "SUPER 4T 20W40", "grade_specs": "SL", "pack_size": "0.9 L", "mrp": 345, "dlp": 247, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹10",  "trade_discount": ""},
    {"category": "MCO — Super", "material_description": "SUPER 4T 10W30", "grade_specs": "SL", "pack_size": "1 L",   "mrp": 373, "dlp": 266, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹10",  "trade_discount": ""},
    {"category": "MCO — Super", "material_description": "SUPER 4T 10W30", "grade_specs": "SL", "pack_size": "0.9 L", "mrp": 350, "dlp": 250, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹10",  "trade_discount": ""},
    {"category": "MCO — Super", "material_description": "TWO STROKE (2T)","grade_specs": "-",  "pack_size": "1 L",   "mrp": 361, "dlp": 257, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},

    # ── SUPER CNG ──
    {"category": "Super CNG", "material_description": "CNG SPECIAL 20W50", "grade_specs": "CF/SF", "pack_size": "1 L", "mrp": 331, "dlp": 197, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},
    {"category": "Super CNG", "material_description": "CNG SHIELD 20W50",  "grade_specs": "CF/SF", "pack_size": "2 L", "mrp": 651, "dlp": 398, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},

    # ── SPECIAL CNG ──
    {"category": "Special CNG", "material_description": "CNG SPECIAL 20W50", "grade_specs": "SM", "pack_size": "1 L",   "mrp": 388, "dlp": 243, "margin_pct": 7, "cash_coupon": "",             "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},
    {"category": "Special CNG", "material_description": "CNG SHIELD 20W50",  "grade_specs": "SN", "pack_size": "2.1 L", "mrp": 977, "dlp": 611, "margin_pct": 7, "cash_coupon": "₹50 — ₹150",  "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},

    # ── MCO — SEMI SYNTHETIC ──
    {"category": "MCO — Semi Synthetic", "material_description": "SYNTH POWER 10W40", "grade_specs": "SN", "pack_size": "1 L",   "mrp": 570, "dlp": 383, "margin_pct": 10, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹40", "trade_discount": "Available"},
    {"category": "MCO — Semi Synthetic", "material_description": "SYNTH POWER 20W50", "grade_specs": "SN", "pack_size": "1 L",   "mrp": 565, "dlp": 381, "margin_pct": 10, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹40", "trade_discount": "Available"},
    {"category": "MCO — Semi Synthetic", "material_description": "SYNTH POWER 20W50", "grade_specs": "SN", "pack_size": "1.2 L", "mrp": 675, "dlp": 455, "margin_pct": 10, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹40", "trade_discount": "Available"},

    # ── MCO — FULL SYNTHETIC ──
    {"category": "MCO — Full Synthetic", "material_description": "4T PREMIUM 10W40",   "grade_specs": "SN", "pack_size": "1 L",   "mrp": 713,  "dlp": 479,  "margin_pct": 12, "cash_coupon": "",              "foc_benefits": "", "monthly_gift": "₹50", "trade_discount": "Available"},
    {"category": "MCO — Full Synthetic", "material_description": "4T PREMIUM 20W50",   "grade_specs": "SN", "pack_size": "1 L",   "mrp": 718,  "dlp": 481,  "margin_pct": 12, "cash_coupon": "",              "foc_benefits": "", "monthly_gift": "₹50", "trade_discount": "Available"},
    {"category": "MCO — Full Synthetic", "material_description": "4T PREMIUM 10W30",   "grade_specs": "SP", "pack_size": "1.2 L", "mrp": 860,  "dlp": 579,  "margin_pct": 12, "cash_coupon": "₹50 — ₹100",   "foc_benefits": "", "monthly_gift": "",    "trade_discount": "Available"},
    {"category": "MCO — Full Synthetic", "material_description": "4T PREMIUM 20W50",   "grade_specs": "SP", "pack_size": "1.2 L", "mrp": 865,  "dlp": 583,  "margin_pct": 12, "cash_coupon": "₹50 — ₹100",   "foc_benefits": "", "monthly_gift": "",    "trade_discount": "Available"},
    {"category": "MCO — Full Synthetic", "material_description": "4T PREMIUM 5W30",    "grade_specs": "SP", "pack_size": "900 ml","mrp": 642,  "dlp": 431,  "margin_pct": 12, "cash_coupon": "₹30 — ₹40",    "foc_benefits": "", "monthly_gift": "",    "trade_discount": "Available"},
    {"category": "MCO — Full Synthetic", "material_description": "SYNTH PREMIUM 5W30", "grade_specs": "SP", "pack_size": "650 ml","mrp": 425,  "dlp": 279,  "margin_pct": 12, "cash_coupon": "",              "foc_benefits": "", "monthly_gift": "₹10", "trade_discount": "Available"},
    {"category": "MCO — Full Synthetic", "material_description": "ROYAL 4T 15W50",     "grade_specs": "SN", "pack_size": "2.5 L", "mrp": 1750, "dlp": 1177, "margin_pct": 12, "cash_coupon": "₹100 — ₹200", "foc_benefits": "", "monthly_gift": "",    "trade_discount": "Available"},

    # ── GEAR OIL — GL4 ──
    {"category": "Gear Oil — GL4", "material_description": "EP 90",  "grade_specs": "GL4", "pack_size": "1 L",  "mrp": 398,  "dlp": 270,  "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},
    {"category": "Gear Oil — GL4", "material_description": "EP 90",  "grade_specs": "GL4", "pack_size": "5 L",  "mrp": 1956, "dlp": 1313, "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},
    {"category": "Gear Oil — GL4", "material_description": "EP 90",  "grade_specs": "GL4", "pack_size": "10 L", "mrp": 3890, "dlp": 2558, "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},
    {"category": "Gear Oil — GL4", "material_description": "EP 90",  "grade_specs": "GL4", "pack_size": "20 L", "mrp": 7330, "dlp": 5050, "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},
    {"category": "Gear Oil — GL4", "material_description": "EP 140", "grade_specs": "GL4", "pack_size": "1 L",  "mrp": 426,  "dlp": 286,  "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},
    {"category": "Gear Oil — GL4", "material_description": "EP 140", "grade_specs": "GL4", "pack_size": "5 L",  "mrp": 2086, "dlp": 1400, "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},
    {"category": "Gear Oil — GL4", "material_description": "EP 140", "grade_specs": "GL4", "pack_size": "20 L", "mrp": 7480, "dlp": 5330, "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},

    # ── GEAR OIL — GL5 ──
    {"category": "Gear Oil — GL5", "material_description": "GEAR GUARD 80W90",  "grade_specs": "GL5", "pack_size": "1 L",   "mrp": 442,  "dlp": 290,   "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "Gear Oil — GL5", "material_description": "GEAR GUARD 80W90",  "grade_specs": "GL5", "pack_size": "5 L",   "mrp": 2187, "dlp": 1468,  "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹50",  "trade_discount": ""},
    {"category": "Gear Oil — GL5", "material_description": "GEAR GUARD 80W90",  "grade_specs": "GL5", "pack_size": "7 L",   "mrp": 2983, "dlp": 2002,  "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹80",  "trade_discount": ""},
    {"category": "Gear Oil — GL5", "material_description": "GEAR GUARD 80W90",  "grade_specs": "GL5", "pack_size": "20 L",  "mrp": 7793, "dlp": 5555,  "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹200", "trade_discount": ""},
    {"category": "Gear Oil — GL5", "material_description": "GEAR GUARD 75W90",  "grade_specs": "GL5", "pack_size": "2.5 L", "mrp": 1260, "dlp": 845.5, "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "Gear Oil — GL5", "material_description": "GEAR GUARD 85W140", "grade_specs": "GL5", "pack_size": "1 L",   "mrp": 456,  "dlp": 306,   "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "Gear Oil — GL5", "material_description": "GEAR GUARD 85W140", "grade_specs": "GL5", "pack_size": "5 L",   "mrp": 2277, "dlp": 1528,  "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹50",  "trade_discount": ""},
    {"category": "Gear Oil — GL5", "material_description": "GEAR GUARD 85W140", "grade_specs": "GL5", "pack_size": "12 L",  "mrp": 5185, "dlp": 3576,  "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹150", "trade_discount": ""},
    {"category": "Gear Oil — GL5", "material_description": "GEAR GUARD 85W140", "grade_specs": "GL5", "pack_size": "20 L",  "mrp": 8148, "dlp": 5820,  "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹200", "trade_discount": ""},

    # ── LITHIUM BASED GREASE — SMOOTH RIDE 100K ──
    {"category": "Lithium Based Grease", "material_description": "SMOOTH RIDE 100K", "grade_specs": "NLG13", "pack_size": "0.5 kg", "mrp": 337,  "dlp": 216,  "margin_pct": 9, "cash_coupon": "",              "foc_benefits": "", "monthly_gift": "₹10",  "trade_discount": ""},
    {"category": "Lithium Based Grease", "material_description": "SMOOTH RIDE 100K", "grade_specs": "NLG13", "pack_size": "1 kg",   "mrp": 649,  "dlp": 424,  "margin_pct": 9, "cash_coupon": "₹20 — ₹50",   "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "Lithium Based Grease", "material_description": "SMOOTH RIDE 100K", "grade_specs": "NLG13", "pack_size": "2 kg",   "mrp": 1269, "dlp": 836,  "margin_pct": 9, "cash_coupon": "",              "foc_benefits": "", "monthly_gift": "₹50",  "trade_discount": ""},
    {"category": "Lithium Based Grease", "material_description": "SMOOTH RIDE 100K", "grade_specs": "NLG13", "pack_size": "3 kg",   "mrp": 1902, "dlp": 1254, "margin_pct": 9, "cash_coupon": "",              "foc_benefits": "", "monthly_gift": "₹80",  "trade_discount": ""},
    {"category": "Lithium Based Grease", "material_description": "SMOOTH RIDE 100K", "grade_specs": "NLG13", "pack_size": "5 kg",   "mrp": 3155, "dlp": 2095, "margin_pct": 9, "cash_coupon": "",              "foc_benefits": "", "monthly_gift": "₹200", "trade_discount": ""},
    {"category": "Lithium Based Grease", "material_description": "SMOOTH RIDE 100K", "grade_specs": "NLG13", "pack_size": "7 kg",   "mrp": 4392, "dlp": 2929, "margin_pct": 9, "cash_coupon": "",              "foc_benefits": "", "monthly_gift": "₹200", "trade_discount": ""},
    {"category": "Lithium Based Grease", "material_description": "SMOOTH RIDE 100K", "grade_specs": "NLG13", "pack_size": "10 kg",  "mrp": 6261, "dlp": 4140, "margin_pct": 9, "cash_coupon": "",              "foc_benefits": "", "monthly_gift": "₹300", "trade_discount": ""},

    # ── LITHIUM BASED GREASE — SMOOTH RIDE 50K ──
    {"category": "Lithium Based Grease", "material_description": "SMOOTH RIDE 50K", "grade_specs": "NLG13", "pack_size": "0.5 kg", "mrp": 298,  "dlp": 195,  "margin_pct": 9, "cash_coupon": "",             "foc_benefits": "", "monthly_gift": "₹10",  "trade_discount": ""},
    {"category": "Lithium Based Grease", "material_description": "SMOOTH RIDE 50K", "grade_specs": "NLG13", "pack_size": "1 kg",   "mrp": 531,  "dlp": 366,  "margin_pct": 9, "cash_coupon": "₹20 — ₹50",  "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "Lithium Based Grease", "material_description": "SMOOTH RIDE 50K", "grade_specs": "NLG13", "pack_size": "2 kg",   "mrp": 1050, "dlp": 728,  "margin_pct": 9, "cash_coupon": "",             "foc_benefits": "", "monthly_gift": "₹50",  "trade_discount": ""},
    {"category": "Lithium Based Grease", "material_description": "SMOOTH RIDE 50K", "grade_specs": "NLG13", "pack_size": "3 kg",   "mrp": 1575, "dlp": 1098, "margin_pct": 9, "cash_coupon": "",             "foc_benefits": "", "monthly_gift": "₹80",  "trade_discount": ""},
    {"category": "Lithium Based Grease", "material_description": "SMOOTH RIDE 50K", "grade_specs": "NLG13", "pack_size": "5 kg",   "mrp": 2625, "dlp": 1762, "margin_pct": 9, "cash_coupon": "",             "foc_benefits": "", "monthly_gift": "₹200", "trade_discount": ""},
    {"category": "Lithium Based Grease", "material_description": "SMOOTH RIDE 50K", "grade_specs": "NLG13", "pack_size": "7 kg",   "mrp": 3640, "dlp": 2452, "margin_pct": 9, "cash_coupon": "",             "foc_benefits": "", "monthly_gift": "₹200", "trade_discount": ""},
    {"category": "Lithium Based Grease", "material_description": "SMOOTH RIDE 50K", "grade_specs": "NLG13", "pack_size": "10 kg",  "mrp": 5200, "dlp": 3470, "margin_pct": 9, "cash_coupon": "",             "foc_benefits": "", "monthly_gift": "₹300", "trade_discount": ""},
    {"category": "Lithium Based Grease", "material_description": "SMOOTH RIDE 50K", "grade_specs": "NLG13", "pack_size": "18 kg",  "mrp": 9090, "dlp": 6292, "margin_pct": 9, "cash_coupon": "",             "foc_benefits": "", "monthly_gift": "₹500", "trade_discount": ""},

    # ── LITHIUM BASED GREASE — SMOOTH FLOW MP3 ──
    {"category": "Lithium Based Grease", "material_description": "SMOOTH FLOW MP3", "grade_specs": "NLG12", "pack_size": "0.5 kg", "mrp": 239,  "dlp": 163,  "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},
    {"category": "Lithium Based Grease", "material_description": "SMOOTH FLOW MP3", "grade_specs": "NLG12", "pack_size": "1 kg",   "mrp": 454,  "dlp": 316,  "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},
    {"category": "Lithium Based Grease", "material_description": "SMOOTH FLOW MP3", "grade_specs": "NLG12", "pack_size": "2 kg",   "mrp": 885,  "dlp": 622,  "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},
    {"category": "Lithium Based Grease", "material_description": "SMOOTH FLOW MP3", "grade_specs": "NLG12", "pack_size": "18 kg",  "mrp": 7524, "dlp": 5310, "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},

    # ── CALCIUM BASED GREASE — SAFE RUN GPG RED ──
    {"category": "Calcium Based Grease", "material_description": "SAFE RUN GPG RED", "grade_specs": "-", "pack_size": "200 g", "mrp": 92,   "dlp": 57,   "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},
    {"category": "Calcium Based Grease", "material_description": "SAFE RUN GPG RED", "grade_specs": "-", "pack_size": "500 g", "mrp": 190,  "dlp": 118,  "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},
    {"category": "Calcium Based Grease", "material_description": "SAFE RUN GPG RED", "grade_specs": "-", "pack_size": "1 kg",  "mrp": 359,  "dlp": 227,  "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},
    {"category": "Calcium Based Grease", "material_description": "SAFE RUN GPG RED", "grade_specs": "-", "pack_size": "2 kg",  "mrp": 690,  "dlp": 446,  "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},
    {"category": "Calcium Based Grease", "material_description": "SAFE RUN GPG RED", "grade_specs": "-", "pack_size": "5 kg",  "mrp": 1700, "dlp": 954,  "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},
    {"category": "Calcium Based Grease", "material_description": "SAFE RUN GPG RED", "grade_specs": "-", "pack_size": "10 kg", "mrp": 2931, "dlp": 1800, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},
    {"category": "Calcium Based Grease", "material_description": "SAFE RUN GPG RED", "grade_specs": "-", "pack_size": "18 kg", "mrp": 4960, "dlp": 3246, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},

    # ── CALCIUM BASED GREASE — SAFE RUN GPG YELLOW ──
    {"category": "Calcium Based Grease", "material_description": "SAFE RUN GPG YELLOW", "grade_specs": "-", "pack_size": "5 kg",  "mrp": 1650, "dlp": 940,  "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},
    {"category": "Calcium Based Grease", "material_description": "SAFE RUN GPG YELLOW", "grade_specs": "-", "pack_size": "10 kg", "mrp": 2877, "dlp": 1770, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},
    {"category": "Calcium Based Grease", "material_description": "SAFE RUN GPG YELLOW", "grade_specs": "-", "pack_size": "18 kg", "mrp": 4820, "dlp": 3096, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "", "trade_discount": ""},

    # ── DEO ──
    {"category": "DEO", "material_description": "TURBO POWER 15W40",         "grade_specs": "CI4",   "pack_size": "1 L",    "mrp": 431,  "dlp": 289,  "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "DEO", "material_description": "TURBO POWER 15W40",         "grade_specs": "CI4",   "pack_size": "7.5 L",  "mrp": 3335, "dlp": 2238, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹80",  "trade_discount": ""},
    {"category": "DEO", "material_description": "TURBO POWER 15W40",         "grade_specs": "CI4",   "pack_size": "10 L",   "mrp": 4344, "dlp": 2996, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹200", "trade_discount": ""},
    {"category": "DEO", "material_description": "TURBO POWER 15W40",         "grade_specs": "CI4",   "pack_size": "15 L",   "mrp": 6150, "dlp": 4393, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹300", "trade_discount": ""},
    {"category": "DEO", "material_description": "POWER DRIVE 20W40",         "grade_specs": "CF",    "pack_size": "1 L",    "mrp": 405,  "dlp": 272,  "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "DEO", "material_description": "POWER DRIVE 20W40",         "grade_specs": "CF",    "pack_size": "7.5 L",  "mrp": 2975, "dlp": 1997, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "DEO", "material_description": "POWER DRIVE 20W40",         "grade_specs": "CF",    "pack_size": "10 L",   "mrp": 3825, "dlp": 2638, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "DEO", "material_description": "POWER DRIVE 20W40",         "grade_specs": "CF",    "pack_size": "15 L",   "mrp": 5481, "dlp": 3915, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "DEO", "material_description": "ULTRA MOTIVE",              "grade_specs": "SM/CF", "pack_size": "7.5 L",  "mrp": 3379, "dlp": 2268, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹150", "trade_discount": ""},
    {"category": "DEO", "material_description": "ULTRA MOTIVE",              "grade_specs": "SM/CF", "pack_size": "10 L",   "mrp": 4338, "dlp": 2992, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹200", "trade_discount": ""},
    {"category": "DEO", "material_description": "ULTRA MOTIVE",              "grade_specs": "SM/CF", "pack_size": "15 L",   "mrp": 5985, "dlp": 4275, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹300", "trade_discount": ""},
    {"category": "DEO", "material_description": "POWER MAXX DIESEL 15W40",   "grade_specs": "CH4",   "pack_size": "7.5 L",  "mrp": 3157, "dlp": 2119, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "DEO", "material_description": "POWER MAXX DIESEL 15W40",   "grade_specs": "CH4",   "pack_size": "10 L",   "mrp": 4019, "dlp": 2772, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "DEO", "material_description": "POWER MAXX DIESEL 15W40",   "grade_specs": "CH4",   "pack_size": "15 L",   "mrp": 5775, "dlp": 4125, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},

    # ── DEO — SYNTHETIC BLEND ──
    {"category": "DEO — Synthetic Blend", "material_description": "TURBO POWER 15W40", "grade_specs": "CI4+", "pack_size": "1 L",   "mrp": 459,  "dlp": 308,  "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "DEO — Synthetic Blend", "material_description": "TURBO POWER 15W40", "grade_specs": "CI4+", "pack_size": "7.5 L", "mrp": 3405, "dlp": 2396, "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹150", "trade_discount": ""},
    {"category": "DEO — Synthetic Blend", "material_description": "TURBO POWER 15W40", "grade_specs": "CI4+", "pack_size": "10 L",  "mrp": 4398, "dlp": 3200, "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹300", "trade_discount": ""},
    {"category": "DEO — Synthetic Blend", "material_description": "TURBO POWER 15W40", "grade_specs": "CI4+", "pack_size": "15 L",  "mrp": 6597, "dlp": 4605, "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹300", "trade_discount": ""},
    {"category": "DEO — Synthetic Blend", "material_description": "TURBO POWER 15W40", "grade_specs": "CI4+", "pack_size": "18 L",  "mrp": 8190, "dlp": 5850, "margin_pct": 9, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹400", "trade_discount": ""},

    # ── DEO — FULL SYNTHETIC ──
    {"category": "DEO — Full Synthetic", "material_description": "TURBO SYNTH 15W40", "grade_specs": "CK4", "pack_size": "7 L",   "mrp": 4202,  "dlp": 2820, "margin_pct": 12, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹150", "trade_discount": ""},
    {"category": "DEO — Full Synthetic", "material_description": "TURBO SYNTH 15W40", "grade_specs": "CK4", "pack_size": "11 L",  "mrp": 6408,  "dlp": 4419, "margin_pct": 12, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹300", "trade_discount": ""},
    {"category": "DEO — Full Synthetic", "material_description": "TURBO SYNTH 15W40", "grade_specs": "CK4", "pack_size": "15 L",  "mrp": 8336,  "dlp": 5954, "margin_pct": 12, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹400", "trade_discount": ""},
    {"category": "DEO — Full Synthetic", "material_description": "TURBO SYNTH 15W40", "grade_specs": "CK4", "pack_size": "18 L",  "mrp": 10109, "dlp": 7221, "margin_pct": 12, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹500", "trade_discount": ""},

    # ── PCMO ──
    {"category": "PCMO", "material_description": "EXTREME POWER 20W50", "grade_specs": "SM",    "pack_size": "1 L", "mrp": 446,  "dlp": 299,  "margin_pct": 8, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "PCMO", "material_description": "EXTREME POWER 20W40", "grade_specs": "SM",    "pack_size": "1 L", "mrp": 429,  "dlp": 288,  "margin_pct": 8, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "PCMO", "material_description": "EXTREME POWER 20W40", "grade_specs": "SM",    "pack_size": "3 L", "mrp": 1342, "dlp": 901,  "margin_pct": 8, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹50",  "trade_discount": ""},
    {"category": "PCMO", "material_description": "ULTRA MOTIVE 15W40",  "grade_specs": "SM/CF", "pack_size": "1 L", "mrp": 479,  "dlp": 319,  "margin_pct": 8, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "PCMO", "material_description": "ULTRA MOTIVE 20W40",  "grade_specs": "SM/CF", "pack_size": "3 L", "mrp": 1392, "dlp": 921,  "margin_pct": 8, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹50",  "trade_discount": ""},
    {"category": "PCMO", "material_description": "ULTRA MOTIVE 20W40",  "grade_specs": "SM/CF", "pack_size": "5 L", "mrp": 2192, "dlp": 1586, "margin_pct": 8, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹80",  "trade_discount": ""},
    {"category": "PCMO", "material_description": "TURBO POWER 15W40",   "grade_specs": "CI4+",  "pack_size": "3 L", "mrp": 1342, "dlp": 921,  "margin_pct": 8, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹50",  "trade_discount": "Available"},
    {"category": "PCMO", "material_description": "TURBO POWER 15W40",   "grade_specs": "CI4+",  "pack_size": "5 L", "mrp": 2366, "dlp": 1568, "margin_pct": 8, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹100", "trade_discount": "Available"},
    {"category": "PCMO", "material_description": "TURBO POWER 20W40",   "grade_specs": "CI4+",  "pack_size": "5 L", "mrp": 2366, "dlp": 1568, "margin_pct": 8, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹100", "trade_discount": "Available"},

    # ── PCMO — SEMI SYNTHETIC ──
    {"category": "PCMO — Semi Synthetic", "material_description": "SYNTH POWER 5W30",  "grade_specs": "SN/CF", "pack_size": "3 L",   "mrp": 2167, "dlp": 1725, "margin_pct": 10, "cash_coupon": "₹50 — ₹150",  "foc_benefits": "", "monthly_gift": "", "trade_discount": "Available"},
    {"category": "PCMO — Semi Synthetic", "material_description": "SYNTH POWER 5W30",  "grade_specs": "SN/CF", "pack_size": "3.5 L", "mrp": 2378, "dlp": 1875, "margin_pct": 10, "cash_coupon": "₹100 — ₹200", "foc_benefits": "", "monthly_gift": "", "trade_discount": "Available"},
    {"category": "PCMO — Semi Synthetic", "material_description": "SYNTH POWER 10W40", "grade_specs": "SN/CF", "pack_size": "3 L",   "mrp": 2167, "dlp": 1725, "margin_pct": 10, "cash_coupon": "₹50 — ₹150",  "foc_benefits": "", "monthly_gift": "", "trade_discount": "Available"},
    {"category": "PCMO — Semi Synthetic", "material_description": "SYNTH POWER 20W50", "grade_specs": "SN/CF", "pack_size": "3 L",   "mrp": 2303, "dlp": 1841, "margin_pct": 10, "cash_coupon": "₹50 — ₹150",  "foc_benefits": "", "monthly_gift": "", "trade_discount": "Available"},
    {"category": "PCMO — Semi Synthetic", "material_description": "SYNTH POWER 20W50", "grade_specs": "SN/CF", "pack_size": "5 L",   "mrp": 3322, "dlp": 1920, "margin_pct": 10, "cash_coupon": "₹50 — ₹150",  "foc_benefits": "", "monthly_gift": "", "trade_discount": "Available"},

    # ── PCMO — FULL SYNTHETIC ──
    {"category": "PCMO — Full Synthetic", "material_description": "SYNTH PREMIUM 5W30",  "grade_specs": "SN/CF", "pack_size": "3 L",   "mrp": 2167, "dlp": 1725, "margin_pct": 12, "cash_coupon": "₹100 — ₹200", "foc_benefits": "", "monthly_gift": "", "trade_discount": "Available"},
    {"category": "PCMO — Full Synthetic", "material_description": "SYNTH PREMIUM 5W30",  "grade_specs": "SN/CF", "pack_size": "3.5 L", "mrp": 2488, "dlp": 1472, "margin_pct": 12, "cash_coupon": "₹100 — ₹200", "foc_benefits": "", "monthly_gift": "", "trade_discount": "Available"},
    {"category": "PCMO — Full Synthetic", "material_description": "SYNTH PREMIUM 5W30",  "grade_specs": "SN/CF", "pack_size": "5 L",   "mrp": 3415, "dlp": 2265, "margin_pct": 12, "cash_coupon": "₹100 — ₹200", "foc_benefits": "", "monthly_gift": "", "trade_discount": "Available"},
    {"category": "PCMO — Full Synthetic", "material_description": "SYNTH PREMIUM 10W40", "grade_specs": "SN/CF", "pack_size": "3 L",   "mrp": 2228, "dlp": 1288, "margin_pct": 12, "cash_coupon": "₹100 — ₹200", "foc_benefits": "", "monthly_gift": "", "trade_discount": "Available"},
    {"category": "PCMO — Full Synthetic", "material_description": "SYNTH PREMIUM 10W40", "grade_specs": "SN/CF", "pack_size": "3.5 L", "mrp": 2571, "dlp": 1486, "margin_pct": 12, "cash_coupon": "₹100 — ₹200", "foc_benefits": "", "monthly_gift": "", "trade_discount": "Available"},
    {"category": "PCMO — Full Synthetic", "material_description": "SYNTH PREMIUM 10W40", "grade_specs": "SN/CF", "pack_size": "5 L",   "mrp": 3752, "dlp": 2192, "margin_pct": 12, "cash_coupon": "₹100 — ₹200", "foc_benefits": "", "monthly_gift": "", "trade_discount": "Available"},
    {"category": "PCMO — Full Synthetic", "material_description": "SYNTH PREMIUM 20W50", "grade_specs": "SN/CF", "pack_size": "3.5 L", "mrp": 2607, "dlp": 1507, "margin_pct": 12, "cash_coupon": "₹100 — ₹200", "foc_benefits": "", "monthly_gift": "", "trade_discount": "Available"},
    {"category": "PCMO — Full Synthetic", "material_description": "SYNTH PREMIUM 20W50", "grade_specs": "SN/CF", "pack_size": "5 L",   "mrp": 3738, "dlp": 2167, "margin_pct": 12, "cash_coupon": "₹100 — ₹200", "foc_benefits": "", "monthly_gift": "", "trade_discount": "Available"},

    # ── ESSENTIAL ──
    {"category": "Essential", "material_description": "COOLANT GREEN",     "grade_specs": "-",  "pack_size": "1 L",   "mrp": 350,  "dlp": 118,  "margin_pct": 8, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "Essential", "material_description": "COOLANT BLUE",      "grade_specs": "-",  "pack_size": "1 L",   "mrp": 370,  "dlp": 143,  "margin_pct": 8, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "Essential", "material_description": "WET BRAKE (UTTO)",  "grade_specs": "-",  "pack_size": "5 L",   "mrp": 1656, "dlp": 1147, "margin_pct": 8, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "Essential", "material_description": "HYDRAULIC OIL",     "grade_specs": "-",  "pack_size": "1 L",   "mrp": 400,  "dlp": 269,  "margin_pct": 8, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹100", "trade_discount": ""},
    {"category": "Essential", "material_description": "HYDRAULIC OIL",     "grade_specs": "-",  "pack_size": "20 L",  "mrp": 6202, "dlp": 4430, "margin_pct": 6, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "₹200", "trade_discount": ""},
    {"category": "Essential", "material_description": "HYDRAULIC 46",      "grade_specs": "AW", "pack_size": "1 L",   "mrp": 398,  "dlp": 274,  "margin_pct": 6, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "Essential", "material_description": "HYDRAULIC 46",      "grade_specs": "AW", "pack_size": "5 L",   "mrp": 1550, "dlp": 1014, "margin_pct": 6, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "Essential", "material_description": "HYDRAULIC 46",      "grade_specs": "AW", "pack_size": "20 L",  "mrp": 5215, "dlp": 3525, "margin_pct": 6, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "Essential", "material_description": "HYDRAULIC 68",      "grade_specs": "AW", "pack_size": "1 L",   "mrp": 418,  "dlp": 289,  "margin_pct": 6, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "Essential", "material_description": "HYDRAULIC 68",      "grade_specs": "AW", "pack_size": "5 L",   "mrp": 1833, "dlp": 1245, "margin_pct": 6, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "Essential", "material_description": "HYDRAULIC 68",      "grade_specs": "AW", "pack_size": "20 L",  "mrp": 5215, "dlp": 3525, "margin_pct": 6, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "Essential", "material_description": "OIL TQ",            "grade_specs": "-",  "pack_size": "1 L",   "mrp": 192,  "dlp": 122,  "margin_pct": 6, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "Essential", "material_description": "SAE 40",            "grade_specs": "-",  "pack_size": "1 L",   "mrp": 440,  "dlp": 274,  "margin_pct": 6, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "Essential", "material_description": "SAE 40",            "grade_specs": "-",  "pack_size": "1.2 L", "mrp": 364,  "dlp": 251,  "margin_pct": 6, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "Essential", "material_description": "SAE 40",            "grade_specs": "-",  "pack_size": "5 L",   "mrp": 1584, "dlp": 1051, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "Essential", "material_description": "POWER TILLER 40",   "grade_specs": "-",  "pack_size": "3.5 L", "mrp": 1051, "dlp": 725,  "margin_pct": 6, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "Essential", "material_description": "BRAKE OIL — DOT 4", "grade_specs": "-",  "pack_size": "500 ml","mrp": 200,  "dlp": 174,  "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
    {"category": "Essential", "material_description": "BRAKE OIL — DOT 4", "grade_specs": "-",  "pack_size": "20 L",  "mrp": 4141, "dlp": 2782, "margin_pct": 7, "cash_coupon": "", "foc_benefits": "", "monthly_gift": "",     "trade_discount": ""},
]
