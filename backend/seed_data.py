"""Rich seed data for GO OIL DMS across all 28 modules."""
from datetime import datetime, timezone, timedelta
import random
import uuid

random.seed(42)

NOW = datetime.now(timezone.utc)


def iso(dt):
    return dt.isoformat()


def d(days_ago=0):
    return iso(NOW - timedelta(days=days_ago))


# ---------- Branches / Regions ----------
BRANCHES = [
    {"id": "br-lagos", "name": "Lagos Central", "code": "LGC", "region": "South-West", "manager": "Chinedu Okafor", "address": "12 Marina Rd, Lagos"},
    {"id": "br-abuja", "name": "Abuja Depot", "code": "ABJ", "region": "North-Central", "manager": "Fatima Bello", "address": "Plot 44, Wuse II, Abuja"},
    {"id": "br-ph", "name": "Port Harcourt", "code": "PHC", "region": "South-South", "manager": "Ibrahim Musa", "address": "Aba Rd, Port Harcourt"},
    {"id": "br-kano", "name": "Kano North", "code": "KAN", "region": "North-West", "manager": "Zainab Yusuf", "address": "Bompai Industrial, Kano"},
    {"id": "br-ibadan", "name": "Ibadan Hub", "code": "IBD", "region": "South-West", "manager": "Adeola Adebayo", "address": "Ring Rd, Ibadan"},
]

# ---------- Roles ----------
ROLES = [
    {"id": "role-super-admin", "key": "super_admin", "name": "Super Admin", "description": "Full platform access across companies", "permission_count": 128, "user_count": 2},
    {"id": "role-company-admin", "key": "company_admin", "name": "Company Admin", "description": "Full access to GO OIL Holdings", "permission_count": 96, "user_count": 4},
    {"id": "role-regional-manager", "key": "regional_manager", "name": "Regional Manager", "description": "Regional sales, operations and approvals", "permission_count": 62, "user_count": 8},
    {"id": "role-sales-executive", "key": "sales_executive", "name": "Sales Executive", "description": "Field sales, secondary orders, customer visits", "permission_count": 34, "user_count": 24},
    {"id": "role-distributor", "key": "distributor", "name": "Distributor", "description": "Distributor portal, primary orders, inventory", "permission_count": 28, "user_count": 42},
    {"id": "role-distributor-accountant", "key": "distributor_accountant", "name": "Distributor Accountant", "description": "Payments, ledger, reconciliation", "permission_count": 22, "user_count": 12},
    {"id": "role-retailer", "key": "retailer", "name": "Retailer", "description": "Retailer portal, secondary orders, cashback", "permission_count": 14, "user_count": 156},
    {"id": "role-customer", "key": "customer", "name": "Customer", "description": "End customer portal, order tracking, invoices", "permission_count": 8, "user_count": 892},
]

# ---------- Product Categories & SKUs ----------
CATEGORIES = ["Engine Oil", "Gear Oil", "Hydraulic Oil", "Industrial Lubricant", "Grease", "Coolant", "Brake Fluid", "Transmission Fluid"]
PACK_SIZES = ["1L", "4L", "5L", "20L", "50L", "208L"]

def make_products():
    products = []
    skus = []
    grades = {
        "Engine Oil": ["5W-30", "10W-40", "15W-40", "20W-50", "0W-20"],
        "Gear Oil": ["80W-90", "85W-140", "75W-90"],
        "Hydraulic Oil": ["ISO VG 32", "ISO VG 46", "ISO VG 68", "ISO VG 100"],
        "Industrial Lubricant": ["EP 220", "EP 320", "EP 460"],
        "Grease": ["EP-2", "EP-3", "Lithium Complex"],
        "Coolant": ["Long-life Green", "Long-life Red"],
        "Brake Fluid": ["DOT 3", "DOT 4", "DOT 5.1"],
        "Transmission Fluid": ["ATF Dex III", "ATF Multi", "CVT"],
    }
    idx = 100
    for cat in CATEGORIES:
        for grade in grades[cat]:
            pid = f"prod-{idx}"
            products.append({
                "id": pid,
                "code": f"GO-{cat[:3].upper()}-{idx}",
                "name": f"GO {cat} {grade}",
                "category": cat,
                "grade": grade,
                "description": f"Premium synthetic {cat.lower()} engineered for high performance {grade} spec.",
                "hsn": "27101990",
                "gst_rate": 18,
                "active": True,
                "created_at": d(random.randint(60, 400)),
            })
            for pack in random.sample(PACK_SIZES, k=random.randint(2, 4)):
                skus.append({
                    "id": f"sku-{idx}-{pack}",
                    "product_id": pid,
                    "product_name": f"GO {cat} {grade}",
                    "sku_code": f"GO-{cat[:3].upper()}-{idx}-{pack}",
                    "pack_size": pack,
                    "unit": "L" if pack.endswith("L") else "kg",
                    "mrp": round(random.uniform(600, 42000), 2),
                    "cost": round(random.uniform(400, 32000), 2),
                    "trade_price": round(random.uniform(500, 36000), 2),
                    "barcode": f"890{random.randint(1000000000, 9999999999)}",
                    "active": True,
                })
            idx += 1
    return products, skus


PRODUCTS, SKUS = make_products()


# ---------- Batches ----------
def make_batches():
    batches = []
    for i, sku in enumerate(random.sample(SKUS, k=min(60, len(SKUS)))):
        batches.append({
            "id": f"batch-{1000+i}",
            "batch_no": f"B{2025}{i:04d}",
            "sku_id": sku["id"],
            "sku_code": sku["sku_code"],
            "product_name": sku["product_name"],
            "manufactured_on": d(random.randint(30, 300)),
            "expires_on": iso(NOW + timedelta(days=random.randint(180, 900))),
            "quantity": random.randint(200, 5000),
            "quality_status": random.choice(["Approved", "Approved", "Approved", "Under Test", "Rejected"]),
            "warehouse_id": random.choice(["wh-lagos-1", "wh-abuja-1", "wh-ph-1"]),
        })
    return batches


BATCHES = make_batches()

# ---------- Warehouses ----------
WAREHOUSES = [
    {"id": "wh-lagos-1", "name": "Lagos Main Warehouse", "branch_id": "br-lagos", "capacity": 50000, "occupied": 38200, "manager": "Tunde Ola", "type": "Primary"},
    {"id": "wh-lagos-2", "name": "Lagos Bond Warehouse", "branch_id": "br-lagos", "capacity": 20000, "occupied": 14100, "manager": "Kemi Sanni", "type": "Bonded"},
    {"id": "wh-abuja-1", "name": "Abuja Depot Warehouse", "branch_id": "br-abuja", "capacity": 30000, "occupied": 21500, "manager": "Aisha Musa", "type": "Primary"},
    {"id": "wh-ph-1", "name": "Port Harcourt Warehouse", "branch_id": "br-ph", "capacity": 25000, "occupied": 19800, "manager": "Nnamdi Eze", "type": "Primary"},
    {"id": "wh-kano-1", "name": "Kano Warehouse", "branch_id": "br-kano", "capacity": 15000, "occupied": 9800, "manager": "Sadiq Umar", "type": "Regional"},
    {"id": "wh-ibadan-1", "name": "Ibadan Regional Depot", "branch_id": "br-ibadan", "capacity": 12000, "occupied": 6400, "manager": "Bola Adeyemi", "type": "Regional"},
]


# ---------- Inventory ----------
def make_inventory():
    inv = []
    for wh in WAREHOUSES:
        for sku in random.sample(SKUS, k=min(20, len(SKUS))):
            on_hand = random.randint(0, 800)
            reorder = random.randint(50, 200)
            inv.append({
                "id": f"inv-{wh['id']}-{sku['id']}",
                "warehouse_id": wh["id"],
                "warehouse_name": wh["name"],
                "sku_id": sku["id"],
                "sku_code": sku["sku_code"],
                "product_name": sku["product_name"],
                "pack_size": sku["pack_size"],
                "on_hand": on_hand,
                "reserved": random.randint(0, min(50, on_hand)) if on_hand else 0,
                "reorder_level": reorder,
                "status": "OK" if on_hand > reorder else ("Low" if on_hand > 0 else "Stock-out"),
                "last_movement": d(random.randint(0, 20)),
            })
    return inv


INVENTORY = make_inventory()


# ---------- Distributors ----------
DIST_NAMES = ["Apex Marine", "Nexa Energy", "BlueGrid Retail", "Summit Logistics", "Vertex Fuels",
              "Harbor Trade", "Meridian Oils", "Orion Motors", "Zenith Petroleum", "Northline Group",
              "Skyway Motors", "Ironclad Industries", "Coastal Marine", "Delta Fleet", "Prime Movers"]

def make_distributors():
    out = []
    for i, name in enumerate(DIST_NAMES):
        out.append({
            "id": f"dist-{100+i}",
            "code": f"DIST-{1000+i}",
            "name": name,
            "contact": f"+234-80{random.randint(10000000, 99999999)}",
            "email": f"{name.lower().replace(' ', '')}@partners.gooil.com",
            "branch_id": random.choice([b["id"] for b in BRANCHES]),
            "credit_limit": random.choice([500000, 1000000, 2000000, 5000000]),
            "outstanding": random.randint(0, 800000),
            "status": random.choice(["Active", "Active", "Active", "On Hold"]),
            "onboarded_on": d(random.randint(60, 800)),
            "gstin": f"27AAECG{random.randint(1000, 9999)}A1Z{random.randint(1,9)}",
            "rating": round(random.uniform(3.4, 4.9), 1),
        })
    return out


DISTRIBUTORS = make_distributors()

# ---------- Retailers ----------
def make_retailers():
    types = ["Auto Workshop", "Fuel Station", "Retail Outlet", "Service Center", "Fleet Operator"]
    cities = ["Lagos", "Abuja", "Port Harcourt", "Kano", "Ibadan", "Enugu", "Benin City", "Kaduna"]
    out = []
    for i in range(40):
        out.append({
            "id": f"ret-{200+i}",
            "code": f"RET-{2000+i}",
            "name": f"{random.choice(['Prime', 'Star', 'Metro', 'Elite', 'Royal', 'Nova', 'Alpha', 'Peak'])} {random.choice(types)} #{i+1}",
            "type": random.choice(types),
            "city": random.choice(cities),
            "distributor_id": random.choice([d["id"] for d in DISTRIBUTORS]),
            "contact": f"+234-90{random.randint(10000000, 99999999)}",
            "outstanding": random.randint(0, 250000),
            "cashback_earned": random.randint(0, 45000),
            "status": random.choice(["Active", "Active", "Active", "Pending KYC"]),
            "onboarded_on": d(random.randint(15, 400)),
        })
    return out


RETAILERS = make_retailers()

# ---------- Customers ----------
def make_customers():
    segments = ["Fleet", "Marine", "Industrial", "Individual", "Government"]
    out = []
    for i in range(60):
        out.append({
            "id": f"cust-{300+i}",
            "code": f"CUST-{3000+i}",
            "name": f"{random.choice(['Delta','Falcon','Titan','Orion','Global','Nova','Vertex'])} {random.choice(['Corp','Fleet','Marine','Industries','Trading'])}",
            "segment": random.choice(segments),
            "city": random.choice(["Lagos", "Abuja", "Port Harcourt", "Kano", "Ibadan"]),
            "email": f"customer{i}@corp.com",
            "phone": f"+234-70{random.randint(10000000, 99999999)}",
            "ltv": random.randint(50000, 4500000),
            "orders_count": random.randint(1, 120),
            "status": random.choice(["Active", "Active", "Dormant"]),
            "onboarded_on": d(random.randint(10, 700)),
        })
    return out


CUSTOMERS = make_customers()


# ---------- Orders ----------
ORDER_STATUS = ["Draft", "Approved", "Ready", "Dispatched", "Invoiced", "Closed", "Delayed"]

def make_orders(order_type, count, prefix):
    out = []
    for i in range(count):
        if order_type == "primary":
            party = random.choice(DISTRIBUTORS)
            party_type = "Distributor"
        else:
            party = random.choice(RETAILERS)
            party_type = "Retailer"
        items = random.randint(2, 8)
        total = sum(random.uniform(5000, 60000) for _ in range(items))
        out.append({
            "id": f"{prefix}-{10000+i}",
            "order_no": f"{prefix}-{10000+i}",
            "type": order_type,
            "party_id": party["id"],
            "party_name": party["name"],
            "party_type": party_type,
            "branch_id": random.choice([b["id"] for b in BRANCHES]),
            "line_items": items,
            "subtotal": round(total, 2),
            "tax": round(total * 0.18, 2),
            "total": round(total * 1.18, 2),
            "status": random.choice(ORDER_STATUS),
            "sla": random.choice(["1h", "3h", "5h", "12h", "Overdue", "Closed"]),
            "placed_on": d(random.randint(0, 45)),
            "expected_on": iso(NOW + timedelta(days=random.randint(-3, 10))),
            "created_by": "sales@gooil.com",
        })
    return out


PRIMARY_ORDERS = make_orders("primary", 80, "PO")
SECONDARY_ORDERS = make_orders("secondary", 120, "SO")

# ---------- Invoices ----------
def make_invoices():
    out = []
    for i, o in enumerate(random.sample(PRIMARY_ORDERS + SECONDARY_ORDERS, k=100)):
        out.append({
            "id": f"inv-{20000+i}",
            "invoice_no": f"INV-{20000+i}",
            "order_id": o["id"],
            "party_id": o["party_id"],
            "party_name": o["party_name"],
            "branch_id": o["branch_id"],
            "subtotal": o["subtotal"],
            "tax": o["tax"],
            "total": o["total"],
            "paid": round(o["total"] * random.uniform(0, 1), 2),
            "status": random.choice(["Paid", "Partial", "Unpaid", "Overdue"]),
            "issued_on": d(random.randint(0, 60)),
            "due_on": iso(NOW + timedelta(days=random.randint(-15, 30))),
        })
    return out


INVOICES = make_invoices()

# ---------- Dispatches ----------
DISPATCH_STATUS = ["Prepared", "Loaded", "In Transit", "Delivered", "Delayed"]

def make_dispatches():
    out = []
    for i, o in enumerate(random.sample(PRIMARY_ORDERS + SECONDARY_ORDERS, k=90)):
        out.append({
            "id": f"disp-{30000+i}",
            "dispatch_no": f"DSP-{30000+i}",
            "order_id": o["id"],
            "party_name": o["party_name"],
            "vehicle_no": f"LG-{random.randint(100,999)}-{chr(random.randint(65,90))}{chr(random.randint(65,90))}",
            "driver": random.choice(["Musa A.", "Tunde O.", "Sadiq I.", "Ahmed B.", "Femi K."]),
            "route": random.choice(["Lagos → Ibadan", "Lagos → Abuja", "Abuja → Kano", "PH → Aba", "Lagos → Benin"]),
            "distance_km": random.randint(80, 1200),
            "status": random.choice(DISPATCH_STATUS),
            "eta": iso(NOW + timedelta(hours=random.randint(-24, 72))),
            "dispatched_on": d(random.randint(0, 20)),
        })
    return out


DISPATCHES = make_dispatches()

# ---------- Goods In Transit ----------
GIT = [d for d in DISPATCHES if d["status"] in ["Loaded", "In Transit"]]

# ---------- GRN ----------
def make_grn():
    out = []
    for i, d_ in enumerate(random.sample(DISPATCHES, k=60)):
        out.append({
            "id": f"grn-{40000+i}",
            "grn_no": f"GRN-{40000+i}",
            "dispatch_id": d_["id"],
            "received_by": random.choice(["Warehouse A", "Warehouse B", "Warehouse C"]),
            "received_on": d(random.randint(0, 30)),
            "condition": random.choice(["Good", "Good", "Good", "Damaged", "Short"]),
            "variance": random.choice([0, 0, 0, -2, -5, 3]),
            "status": random.choice(["Accepted", "Accepted", "Under Review", "Disputed"]),
        })
    return out


GRNS = make_grn()

# ---------- Payments ----------
def make_payments():
    out = []
    modes = ["Bank Transfer", "UPI", "Cheque", "Cash", "RTGS"]
    for i, inv in enumerate(random.sample(INVOICES, k=80)):
        out.append({
            "id": f"pay-{50000+i}",
            "payment_no": f"PAY-{50000+i}",
            "invoice_id": inv["id"],
            "party_name": inv["party_name"],
            "amount": round(inv["paid"] if inv["paid"] > 0 else inv["total"] * 0.5, 2),
            "mode": random.choice(modes),
            "reference": f"REF{random.randint(100000, 999999)}",
            "received_on": d(random.randint(0, 45)),
            "status": random.choice(["Cleared", "Cleared", "Pending", "Bounced"]),
        })
    return out


PAYMENTS = make_payments()

# ---------- Ledger ----------
def make_ledger():
    out = []
    for i in range(150):
        party = random.choice(DISTRIBUTORS + RETAILERS)
        amt = random.randint(1000, 200000)
        dr = random.choice([True, False])
        out.append({
            "id": f"led-{60000+i}",
            "party_id": party["id"],
            "party_name": party["name"],
            "date": d(random.randint(0, 90)),
            "particulars": random.choice(["Invoice", "Payment", "Credit Note", "Debit Note", "Opening Bal", "Adjustment"]),
            "reference": f"REF-{random.randint(1000,9999)}",
            "debit": amt if dr else 0,
            "credit": 0 if dr else amt,
            "balance": random.randint(-50000, 500000),
        })
    return out


LEDGER = make_ledger()

# ---------- Expenses ----------
def make_expenses():
    cats = ["Transport", "Fuel", "Warehouse Rent", "Salaries", "Marketing", "Utilities", "Repairs", "Travel"]
    out = []
    for i in range(70):
        out.append({
            "id": f"exp-{70000+i}",
            "expense_no": f"EXP-{70000+i}",
            "category": random.choice(cats),
            "branch_id": random.choice([b["id"] for b in BRANCHES]),
            "amount": random.randint(2000, 350000),
            "vendor": random.choice(["Shell Logistics", "Elite Movers", "Metro Cleaning", "Zenith Bank", "Ace Marketing"]),
            "date": d(random.randint(0, 90)),
            "status": random.choice(["Approved", "Pending", "Approved", "Reimbursed"]),
        })
    return out


EXPENSES = make_expenses()

# ---------- Cashback ----------
def make_cashback():
    out = []
    for i in range(50):
        r = random.choice(RETAILERS)
        out.append({
            "id": f"cb-{80000+i}",
            "retailer_id": r["id"],
            "retailer_name": r["name"],
            "campaign": random.choice(["Q1 Volume Bonus", "New SKU Push", "Loyalty Tier 3", "Referral Bonus"]),
            "earned": random.randint(500, 25000),
            "redeemed": random.randint(0, 15000),
            "status": random.choice(["Credited", "Redeemed", "Pending", "Expired"]),
            "issued_on": d(random.randint(0, 90)),
        })
    return out


CASHBACK = make_cashback()

# ---------- Coupons ----------
def make_coupons():
    out = []
    for i in range(24):
        out.append({
            "id": f"cpn-{90000+i}",
            "code": f"GO{random.choice(['LOYAL','FLEET','MARINE','QUARTER'])}{random.randint(10,99)}",
            "campaign": random.choice(["Loyalty Q1", "Marine Sector Push", "Fleet Volume", "New Distributor"]),
            "discount_type": random.choice(["Flat", "Percent"]),
            "value": random.choice([5, 10, 15, 20, 1000, 2500, 5000]),
            "usage": random.randint(0, 400),
            "limit": random.choice([500, 1000, 2000, 5000]),
            "valid_till": iso(NOW + timedelta(days=random.randint(15, 180))),
            "status": random.choice(["Active", "Active", "Paused", "Expired"]),
        })
    return out


COUPONS = make_coupons()

# ---------- Approvals ----------
def make_approvals():
    out = []
    types = [("Credit limit increase", "Finance"),
             ("Price override", "Sales"),
             ("Damaged GRN write-off", "Warehouse"),
             ("Refund request", "Finance"),
             ("New distributor onboarding", "Ops"),
             ("Discount above policy", "Sales")]
    for i in range(30):
        t = random.choice(types)
        out.append({
            "id": f"apr-{5000+i}",
            "title": t[0],
            "module": t[1],
            "requested_by": random.choice(["Chinedu O.", "Fatima B.", "Ibrahim M.", "Adeola A.", "Zainab Y."]),
            "amount": random.randint(10000, 900000),
            "sla": random.choice(["1h", "3h", "6h", "1d", "Overdue"]),
            "status": random.choice(["Pending", "Pending", "Approved", "Rejected"]),
            "created_at": d(random.randint(0, 15)),
        })
    return out


APPROVALS = make_approvals()

# ---------- Notifications ----------
def make_notifications():
    out = []
    kinds = [("Dispatch approval cleared", "success", "Warehouse"),
             ("Invoice batch posted", "info", "Finance"),
             ("Stock-out exception escalated", "warning", "Inventory"),
             ("Credit hold released", "success", "Sales Ops"),
             ("Sync job completed", "info", "Integration"),
             ("Overdue payment reminder", "warning", "Finance"),
             ("New distributor pending KYC", "info", "Ops")]
    for i in range(40):
        k = random.choice(kinds)
        out.append({
            "id": f"ntf-{6000+i}",
            "title": k[0],
            "severity": k[1],
            "module": k[2],
            "created_at": d(random.randint(0, 30)),
            "read": random.choice([True, False, False]),
        })
    return out


NOTIFICATIONS = make_notifications()


# ---------- Reports & Analytics ----------
def make_trend(n=12):
    v = 60
    out = []
    for i in range(n):
        v += random.uniform(-6, 10)
        v = max(30, min(100, v))
        out.append(round(v, 1))
    return out


ANALYTICS = {
    "primary_trend": make_trend(12),
    "revenue_trend": [round(random.uniform(1.2, 3.4) * 1000000, 0) for _ in range(12)],
    "orders_by_status": [
        {"status": "Open", "count": 138},
        {"status": "Ready", "count": 92},
        {"status": "Delayed", "count": 41},
        {"status": "Invoiced", "count": 156},
        {"status": "Closed", "count": 401},
    ],
    "top_skus": [
        {"sku": s["sku_code"], "product": s["product_name"], "revenue": random.randint(200000, 3200000), "units": random.randint(120, 4200)}
        for s in random.sample(SKUS, k=8)
    ],
    "branch_health": [
        {"branch": b["name"], "on_track": random.randint(30, 80), "at_risk": random.randint(4, 24), "blocked": random.randint(0, 10)}
        for b in BRANCHES
    ],
}


# ---------- Users ----------
def make_test_users():
    """Create one user per role for demo."""
    users = [
        {"email": "admin@gooil.com", "name": "Super Admin", "role": "super_admin", "branch_id": None, "title": "Platform Administrator"},
        {"email": "company@gooil.com", "name": "Olivia Adeyemi", "role": "company_admin", "branch_id": None, "title": "Company Admin"},
        {"email": "regional@gooil.com", "name": "Chinedu Okafor", "role": "regional_manager", "branch_id": "br-lagos", "title": "Regional Manager - South-West"},
        {"email": "sales@gooil.com", "name": "Adeola Adebayo", "role": "sales_executive", "branch_id": "br-ibadan", "title": "Sales Executive"},
        {"email": "distributor@gooil.com", "name": "Apex Marine Ltd", "role": "distributor", "branch_id": "br-lagos", "title": "Distributor"},
        {"email": "accountant@gooil.com", "name": "Bola Adeyemi", "role": "distributor_accountant", "branch_id": "br-lagos", "title": "Distributor Accountant"},
        {"email": "retailer@gooil.com", "name": "Metro Auto Workshop", "role": "retailer", "branch_id": "br-lagos", "title": "Retailer"},
        {"email": "customer@gooil.com", "name": "Delta Fleet Corp", "role": "customer", "branch_id": None, "title": "Fleet Customer"},
    ]
    return users


TEST_USERS = make_test_users()

# ---------- Master Data ----------
MASTER_DATA = {
    "tax_rates": [
        {"id": "tax-gst-5", "name": "GST 5%", "rate": 5, "type": "Output"},
        {"id": "tax-gst-12", "name": "GST 12%", "rate": 12, "type": "Output"},
        {"id": "tax-gst-18", "name": "GST 18%", "rate": 18, "type": "Output"},
        {"id": "tax-gst-28", "name": "GST 28%", "rate": 28, "type": "Output"},
    ],
    "uoms": [
        {"id": "uom-l", "code": "L", "name": "Litre"},
        {"id": "uom-ml", "code": "mL", "name": "Milliliter"},
        {"id": "uom-kg", "code": "kg", "name": "Kilogram"},
        {"id": "uom-drum", "code": "drum", "name": "Drum (208L)"},
    ],
    "payment_terms": [
        {"id": "pt-net-15", "name": "Net 15", "days": 15},
        {"id": "pt-net-30", "name": "Net 30", "days": 30},
        {"id": "pt-net-45", "name": "Net 45", "days": 45},
        {"id": "pt-cod", "name": "Cash on Delivery", "days": 0},
    ],
    "regions": [
        {"id": "reg-sw", "name": "South-West"},
        {"id": "reg-nc", "name": "North-Central"},
        {"id": "reg-ss", "name": "South-South"},
        {"id": "reg-nw", "name": "North-West"},
    ],
}


SEED = {
    "branches": BRANCHES,
    "roles": ROLES,
    "products": PRODUCTS,
    "skus": SKUS,
    "batches": BATCHES,
    "warehouses": WAREHOUSES,
    "inventory": INVENTORY,
    "distributors": DISTRIBUTORS,
    "retailers": RETAILERS,
    "customers": CUSTOMERS,
    "primary_orders": PRIMARY_ORDERS,
    "secondary_orders": SECONDARY_ORDERS,
    "invoices": INVOICES,
    "dispatches": DISPATCHES,
    "grns": GRNS,
    "payments": PAYMENTS,
    "ledger": LEDGER,
    "expenses": EXPENSES,
    "cashback": CASHBACK,
    "coupons": COUPONS,
    "approvals": APPROVALS,
    "notifications": NOTIFICATIONS,
    "analytics": ANALYTICS,
    "master_data": MASTER_DATA,
    "test_users": TEST_USERS,
}
