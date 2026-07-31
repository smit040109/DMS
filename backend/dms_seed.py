"""Simple DMS demo seed — idempotent."""
import bcrypt
import uuid
from datetime import datetime, timezone

DMS_TENANT_ID = "tnt-dms-oil"
DMS_PASSWORD = "Demo@2026"


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _nid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


async def ensure_dms_tenant(raw_db):
    """Ensure the DMS tenant exists so users have somewhere to live."""
    if not await raw_db.tenants.find_one({"id": DMS_TENANT_ID}):
        await raw_db.tenants.insert_one({
            "id": DMS_TENANT_ID,
            "slug": "dms-oil",
            "name": "Bharat Oil DMS",
            "industry": "lubricants",
            "currency": "INR",
            "timezone": "Asia/Kolkata",
            "status": "active",
            "brand_colors": {"primary": "#0f766e", "secondary": "#134e4a", "accent": "#f59e0b"},
            "labels": {},
            "created_at": _now(),
        })


async def seed_dms(raw_db):
    """Idempotently seed 8 demo users, sample categories, products, distributors."""
    await ensure_dms_tenant(raw_db)

    # --- users ---
    users = [
        {"email": "owner@dms.com",       "name": "Rajesh Bharat",      "role": "owner",                  "phone": "+91-9876500001"},
        {"email": "acct@dms.com",        "name": "Sunita Owner Acct",  "role": "owner_accountant",       "phone": "+91-9876500002"},
        {"email": "dist1@dms.com",       "name": "Amit Distributor",   "role": "distributor",            "phone": "+91-9876500011"},
        {"email": "dist2@dms.com",       "name": "Priya Traders",      "role": "distributor",            "phone": "+91-9876500012"},
        {"email": "distacct@dms.com",    "name": "Kumar Dist Acct",    "role": "distributor_accountant", "phone": "+91-9876500021"},
        {"email": "retailer1@dms.com",   "name": "Sharma Auto Shop",   "role": "retailer",               "phone": "+91-9876500031"},
        {"email": "retailer2@dms.com",   "name": "Verma Motors",       "role": "retailer",               "phone": "+91-9876500032"},
        {"email": "sales@dms.com",       "name": "Karan Salesperson",  "role": "salesperson",            "phone": "+91-9876500041"},
        {"email": "tl@dms.com",          "name": "Neha Team Leader",   "role": "team_leader",            "phone": "+91-9876500051"},
        {"email": "rm@dms.com",          "name": "Vikram Regional Mgr","role": "regional_manager",       "phone": "+91-9876500061"},
    ]

    user_ids_by_email = {}
    for u in users:
        existing = await raw_db.users.find_one({"email": u["email"]})
        if existing:
            user_ids_by_email[u["email"]] = existing["id"]
            # ensure tenant is DMS
            if existing.get("tenant_id") != DMS_TENANT_ID:
                await raw_db.users.update_one(
                    {"id": existing["id"]},
                    {"$set": {"tenant_id": DMS_TENANT_ID, "password_hash": _hash(DMS_PASSWORD), "role": u["role"], "phone": u["phone"]}},
                )
            continue
        uid = _nid("usr")
        user_ids_by_email[u["email"]] = uid
        doc = {
            "id": uid,
            "tenant_id": DMS_TENANT_ID,
            "email": u["email"],
            "name": u["name"],
            "role": u["role"],
            "phone": u["phone"],
            "password_hash": _hash(DMS_PASSWORD),
            "active": True,
            "created_at": _now(),
            "avatar": "".join([w[0] for w in u["name"].split()[:2]]).upper(),
        }
        await raw_db.users.insert_one(doc)

    # --- categories ---
    def _cat_doc(name, desc):
        return {"id": _nid("cat"), "tenant_id": DMS_TENANT_ID, "name": name, "description": desc, "created_at": _now()}

    if await raw_db.dms_categories.count_documents({"tenant_id": DMS_TENANT_ID}) == 0:
        cats = [
            _cat_doc("Engine Oil",      "Passenger & commercial vehicle engine oils"),
            _cat_doc("Gear Oil",        "Gear oils for automotive and industrial"),
            _cat_doc("Brake Fluid",     "DOT-3 / DOT-4 brake fluids"),
            _cat_doc("Grease",          "Multi-purpose lubricating grease"),
            _cat_doc("Coolant",         "Radiator coolants & anti-freeze"),
        ]
        await raw_db.dms_categories.insert_many(cats)
        cat_ids = {c["name"]: c["id"] for c in cats}
    else:
        cat_ids = {c["name"]: c["id"] async for c in raw_db.dms_categories.find({"tenant_id": DMS_TENANT_ID}, {"_id": 0, "name": 1, "id": 1})}

    # --- products ---
    def _prod(name, category, sku, box_qty, price, hsn="27101980", gst=18, desc=""):
        return {
            "id": _nid("prd"),
            "tenant_id": DMS_TENANT_ID,
            "name": name,
            "category_id": cat_ids[category],
            "sku_code": sku,
            "description": desc,
            "box_qty": box_qty,
            "unit_price": float(price),      # per box
            "previous_price": None,
            "hsn": hsn,
            "gst_pct": gst,
            "active": True,
            "created_at": _now(),
        }

    if await raw_db.dms_products.count_documents({"tenant_id": DMS_TENANT_ID}) == 0:
        prods = [
            _prod("Bharat Super 20W40 (1L)",  "Engine Oil",  "BSE-20W40-1L",  12, 3600, desc="High-mileage engine oil, 1L bottle"),
            _prod("Bharat Super 15W40 (1L)",  "Engine Oil",  "BSE-15W40-1L",  12, 3900),
            _prod("Bharat Diesel 20W40 (5L)", "Engine Oil",  "BSD-20W40-5L",   4, 6800),
            _prod("Bharat Gear GL-4 (1L)",    "Gear Oil",    "BSG-GL4-1L",    12, 2400),
            _prod("Bharat Gear GL-5 (500ml)", "Gear Oil",    "BSG-GL5-500",   24, 2800),
            _prod("Bharat Brake DOT-4 (500ml)", "Brake Fluid", "BSB-DOT4-500", 20, 3200),
            _prod("Bharat Multi-Purpose Grease (500g)", "Grease", "BSGR-MP-500", 20, 2200),
            _prod("Bharat EP-2 Grease (1kg)", "Grease",      "BSGR-EP2-1K",   10, 3400),
            _prod("Bharat Coolant Green (1L)","Coolant",     "BSC-GR-1L",     12, 1800),
            _prod("Bharat Coolant Concentrate (5L)","Coolant","BSC-CC-5L",     4, 3600),
            _prod("Bharat Racer 5W30 (1L)",   "Engine Oil",  "BSR-5W30-1L",   12, 4800),
            _prod("Bharat Two-Wheeler 20W40 (1L)","Engine Oil","BSW-20W40-1L",12, 3400),
        ]
        await raw_db.dms_products.insert_many(prods)
        # initial price batches
        for p in prods:
            await raw_db.dms_price_batches.insert_one({
                "id": _nid("pb"),
                "tenant_id": DMS_TENANT_ID,
                "product_id": p["id"],
                "price": p["unit_price"],
                "from_date": _now(),
                "to_date": None,
                "created_at": _now(),
            })

    products = await raw_db.dms_products.find({"tenant_id": DMS_TENANT_ID}, {"_id": 0}).to_list(1000)

    # --- distributors ---
    # backfill: existing seed rows created before gps fields — inject Delhi/Mumbai coords
    _dist_coords = {
        "dist1@dms.com": (28.6139, 77.2090),
        "dist2@dms.com": (19.0760, 72.8777),
    }
    async for d in raw_db.dms_distributors.find({"tenant_id": DMS_TENANT_ID}, {"_id": 0}):
        if d.get("gps_lat") is None and d.get("email") in _dist_coords:
            lat, lng = _dist_coords[d["email"]]
            await raw_db.dms_distributors.update_one(
                {"id": d["id"]},
                {"$set": {
                    "gps_lat": lat, "gps_lng": lng,
                    "location_link": f"https://maps.google.com/?q={lat},{lng}",
                }},
            )
    # backfill: existing retailers — add location_link if missing
    _ret_link_needed = raw_db.dms_retailers.find(
        {"tenant_id": DMS_TENANT_ID, "gps_lat": {"$ne": None}, "location_link": {"$in": [None, ""]}},
        {"_id": 0},
    )
    async for r in _ret_link_needed:
        await raw_db.dms_retailers.update_one(
            {"id": r["id"]},
            {"$set": {"location_link": f"https://maps.google.com/?q={r['gps_lat']},{r['gps_lng']}"}},
        )
    if await raw_db.dms_distributors.count_documents({"tenant_id": DMS_TENANT_ID}) == 0:
        dist_pairs = [
            ("dist1@dms.com", "Amit Distributor",  "Delhi",  "07AAACD1234M1Z5", 28.6139, 77.2090),
            ("dist2@dms.com", "Priya Traders",     "Mumbai", "27AAACP4321F1Z0", 19.0760, 72.8777),
        ]
        for email, name, region, gstin, lat, lng in dist_pairs:
            uid = user_ids_by_email.get(email)
            if not uid:
                continue
            did = _nid("dist")
            await raw_db.dms_distributors.insert_one({
                "id": did,
                "tenant_id": DMS_TENANT_ID,
                "name": name,
                "email": email,
                "phone": "+91-9876500011",
                "address": f"{region}, India",
                "region": region,
                "gps_lat": lat,
                "gps_lng": lng,
                "location_link": f"https://maps.google.com/?q={lat},{lng}",
                "user_id": uid,
                "accountant_user_id": user_ids_by_email.get("distacct@dms.com") if email == "dist1@dms.com" else None,
                "kyc": {
                    "gstin": gstin,
                    "pan": "ABCDE1234F",
                    "aadhaar": "",
                    "shop_license": "SHP-2024-" + region[:3].upper(),
                    "bank_name": "State Bank of India",
                    "bank_account": "3527" + str(hash(email))[-6:],
                    "bank_ifsc": "SBIN0001234",
                    "notes": "",
                },
                "credit_limit": 500000,
                "active": True,
                "created_at": _now(),
            })
            # link user
            await raw_db.users.update_one({"id": uid}, {"$set": {"distributor_id": did}})
            # link distributor_accountant
            if email == "dist1@dms.com":
                dacct = user_ids_by_email.get("distacct@dms.com")
                if dacct:
                    await raw_db.users.update_one({"id": dacct}, {"$set": {"distributor_id": did}})

    # --- owner initial stock (60 boxes of each product) ---
    if await raw_db.dms_owner_inventory.count_documents({"tenant_id": DMS_TENANT_ID}) == 0:
        for p in products:
            await raw_db.dms_owner_inventory.insert_one({
                "id": _nid("oinv"),
                "tenant_id": DMS_TENANT_ID,
                "product_id": p["id"],
                "qty_boxes": 60,
                "updated_at": _now(),
            })
            await raw_db.dms_stock_ledger.insert_one({
                "id": _nid("sl"),
                "tenant_id": DMS_TENANT_ID,
                "scope": "owner",
                "product_id": p["id"],
                "delta_boxes": 60,
                "reason": "initial_stock",
                "reference": "",
                "at": _now(),
            })

    # --- Distributors initial stock (10 boxes of each so retailers can order) ---
    dists = await raw_db.dms_distributors.find({"tenant_id": DMS_TENANT_ID}, {"_id": 0}).to_list(100)
    if await raw_db.dms_distributor_inventory.count_documents({"tenant_id": DMS_TENANT_ID}) == 0:
        for d in dists:
            for p in products:
                await raw_db.dms_distributor_inventory.insert_one({
                    "id": _nid("dinv"),
                    "tenant_id": DMS_TENANT_ID,
                    "distributor_id": d["id"],
                    "product_id": p["id"],
                    "qty_boxes": 15,
                    "cost_price": p["unit_price"],
                    "updated_at": _now(),
                })

    # --- Retailer selling prices (owner sets, distributor sells at this) — cost + 15% ---
    if await raw_db.dms_retailer_prices.count_documents({"tenant_id": DMS_TENANT_ID}) == 0:
        for d in dists:
            for p in products:
                await raw_db.dms_retailer_prices.insert_one({
                    "id": _nid("rp"),
                    "tenant_id": DMS_TENANT_ID,
                    "distributor_id": d["id"],
                    "product_id": p["id"],
                    "selling_price": round(p["unit_price"] * 1.15, 2),
                    "updated_at": _now(),
                })

    # --- Retailers ---
    if await raw_db.dms_retailers.count_documents({"tenant_id": DMS_TENANT_ID}) == 0 and dists:
        primary_dist_id = next((d["id"] for d in dists if d["email"] == "dist1@dms.com"), dists[0]["id"])
        retailers_seed = [
            ("retailer1@dms.com", "Sharma Auto Shop", "+91-9876500031", "Karol Bagh, New Delhi", "box_pcs", 28.6448, 77.2167),
            ("retailer2@dms.com", "Verma Motors",     "+91-9876500032", "Rohini, New Delhi",     "box",     28.7495, 77.0567),
        ]
        for email, name, phone, addr, mode, lat, lng in retailers_seed:
            uid = user_ids_by_email.get(email)
            rid = _nid("ret")
            await raw_db.dms_retailers.insert_one({
                "id": rid, "tenant_id": DMS_TENANT_ID,
                "name": name, "phone": phone, "email": email,
                "address": addr, "region": "Delhi",
                "gps_lat": lat, "gps_lng": lng,
                "distributor_id": primary_dist_id,
                "onboarded_by": user_ids_by_email.get("owner@dms.com"),
                "onboarded_by_role": "owner",
                "user_id": uid,
                "kyc": {"gstin": "", "shop_license": "SHP-DL-" + str(hash(email))[-4:], "notes": ""},
                "documents": [], "credit_limit": 100000, "active": True,
                "created_at": _now(),
            })
            if uid:
                await raw_db.users.update_one({"id": uid}, {"$set": {"retailer_id": rid, "distributor_id": primary_dist_id}})
            # selling mode
            await raw_db.dms_ret_mode.insert_one({
                "id": _nid("rm"), "tenant_id": DMS_TENANT_ID,
                "distributor_id": primary_dist_id, "retailer_id": rid, "mode": mode, "updated_at": _now(),
            })

    # --- Sales team assignments ---
    tl_id = user_ids_by_email.get("tl@dms.com")
    sp_id = user_ids_by_email.get("sales@dms.com")
    rm_id = user_ids_by_email.get("rm@dms.com")
    # Team leader gets both distributors; salesperson gets dist1; RM gets TL
    if tl_id and dists and await raw_db.dms_tl_assignments.count_documents({"team_leader_id": tl_id}) == 0:
        for d in dists:
            await raw_db.dms_tl_assignments.insert_one({
                "id": _nid("tla"), "tenant_id": DMS_TENANT_ID,
                "team_leader_id": tl_id, "distributor_id": d["id"],
                "assigned_by": user_ids_by_email.get("owner@dms.com"), "at": _now(),
            })
    if sp_id and dists and await raw_db.dms_sp_assignments.count_documents({"salesperson_id": sp_id}) == 0:
        primary_did = next((d["id"] for d in dists if d["email"] == "dist1@dms.com"), dists[0]["id"])
        await raw_db.dms_sp_assignments.insert_one({
            "id": _nid("spa"), "tenant_id": DMS_TENANT_ID,
            "salesperson_id": sp_id, "distributor_id": primary_did,
            "assigned_by": tl_id, "at": _now(),
        })
    if rm_id and tl_id and await raw_db.dms_rm_assignments.count_documents({"regional_manager_id": rm_id}) == 0:
        await raw_db.dms_rm_assignments.insert_one({
            "id": _nid("rma"), "tenant_id": DMS_TENANT_ID,
            "regional_manager_id": rm_id, "team_leader_id": tl_id,
            "assigned_by": user_ids_by_email.get("owner@dms.com"), "at": _now(),
        })
    return True
