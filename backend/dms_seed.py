"""GO OIL DMS demo seed — clean-slate, idempotent, versioned.

Bumping SEED_VERSION forces a full reset of all DMS demo data:
- Deletes old products, categories, orders, ledgers, inventories, retailers,
  distributors, retailer prices, notifications, coupons, price batches, etc.
- Deletes the old demo users (only those with tenant_id=tnt-dms-oil).
- Reseeds Product Master + MAY'26 Price Circular from the official GO OIL PDF.
- Creates fresh GO OIL-themed demo users for every role.
"""
import bcrypt
import uuid
from datetime import datetime, timezone

from dms_pdf_data import PDF_ROWS, CIRCULAR_EFFECTIVE_DATE, CIRCULAR_TITLE

DMS_TENANT_ID = "tnt-dms-oil"
DMS_PASSWORD = "GoOil@2026"

# Bump this whenever you want a full data reset on the next server boot.
SEED_VERSION = "gooil-v2-may26"


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _nid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _slug(text: str) -> str:
    keep = []
    for ch in text.upper():
        if ch.isalnum():
            keep.append(ch)
        elif ch in " -":
            keep.append("-")
    return "".join(keep).strip("-")[:24]


async def ensure_dms_tenant(raw_db):
    tenant = await raw_db.tenants.find_one({"id": DMS_TENANT_ID})
    payload = {
        "id": DMS_TENANT_ID,
        "slug": "go-oil-dms",
        "name": "GO OIL DMS",
        "industry": "lubricants",
        "currency": "INR",
        "timezone": "Asia/Kolkata",
        "status": "active",
        # White + Gold premium theme
        "brand_colors": {"primary": "#c9a227", "secondary": "#1f2937", "accent": "#a67c00"},
        "labels": {},
        "created_at": _now(),
    }
    if tenant:
        await raw_db.tenants.update_one({"id": DMS_TENANT_ID}, {"$set": payload})
    else:
        await raw_db.tenants.insert_one(payload)


async def _reset_dms_business_data(raw_db):
    """Wipe every collection that holds demo business data for the DMS tenant."""
    collections_full_drop = [
        "dms_categories", "dms_products", "dms_price_batches", "dms_price_circulars",
        "dms_owner_inventory", "dms_distributor_inventory", "dms_stock_ledger",
        "dms_distributors", "dms_retailers", "dms_retailer_prices", "dms_ret_mode",
        "dms_dist_visibility", "dms_retailer_visibility",
        "dms_primary_orders", "dms_secondary_orders", "dms_ebills", "dms_retailer_bills",
        "dms_primary_ledger", "dms_secondary_ledger", "dms_attachments", "dms_pending",
        "dms_notifications",
        "dms_tl_assignments", "dms_sp_assignments", "dms_rm_assignments",
        "dms_punch", "dms_gps_pings", "dms_visits",
        "dms_coupons", "dms_coupon_batches", "dms_coupon_fraud",
        "dms_settings",
    ]
    for coll in collections_full_drop:
        try:
            await raw_db[coll].delete_many({})
        except Exception:
            pass
    # Delete old demo users of this tenant so we can recreate cleanly.
    await raw_db.users.delete_many({"tenant_id": DMS_TENANT_ID})


async def _seed_users(raw_db):
    """Fresh GO OIL-themed demo accounts."""
    users_spec = [
        # email, name, role, phone
        ("superadmin@gooil.com",     "Aarav Mehta (Super Admin)", "super_admin",           "+91-9000000001"),
        ("owner@gooil.com",          "Rakesh Agarwal (Owner)",    "owner",                 "+91-9000000010"),
        ("accountant@gooil.com",     "Sunita Sharma (Accounts)",  "owner_accountant",      "+91-9000000011"),
        ("distributor1@gooil.com",   "Anil Distributor — Delhi",  "distributor",           "+91-9000000021"),
        ("distributor2@gooil.com",   "Meena Traders — Mumbai",    "distributor",           "+91-9000000022"),
        ("distacct@gooil.com",       "Kiran Distributor Accts",   "distributor_accountant","+91-9000000023"),
        ("retailer1@gooil.com",      "Sharma Auto Parts",         "retailer",              "+91-9000000031"),
        ("retailer2@gooil.com",      "Verma Motors Store",        "retailer",              "+91-9000000032"),
        ("salesperson@gooil.com",    "Karan Salesperson",         "salesperson",           "+91-9000000041"),
        ("teamleader@gooil.com",     "Neha Team Leader",          "team_leader",           "+91-9000000051"),
        ("regionalmgr@gooil.com",    "Vikram Regional Manager",   "regional_manager",      "+91-9000000061"),
    ]
    ids: dict = {}
    for email, name, role, phone in users_spec:
        uid = _nid("usr")
        ids[email] = uid
        await raw_db.users.insert_one({
            "id": uid,
            "tenant_id": DMS_TENANT_ID,
            "email": email,
            "name": name,
            "role": role,
            "phone": phone,
            "password_hash": _hash(DMS_PASSWORD),
            "active": True,
            "created_at": _now(),
            "avatar": "".join([w[0] for w in name.split()[:2]]).upper(),
        })
    return ids


async def _seed_settings(raw_db):
    """Global settings — GST% starts at 0 (owner configures later)."""
    await raw_db.dms_settings.insert_one({
        "id": "global",
        "tenant_id": DMS_TENANT_ID,
        "gst_pct": 0.0,                     # default 0% until owner sets
        "company_name": "GO OIL Lubricants",
        "updated_at": _now(),
    })


async def _seed_products_and_circular(raw_db):
    """Insert Product Master (category, material, grade, pack) + initial MAY'26 Price Circular."""
    # ── categories ──
    category_names = []
    for row in PDF_ROWS:
        if row["category"] not in category_names:
            category_names.append(row["category"])
    cat_ids: dict = {}
    for name in category_names:
        cid = _nid("cat")
        cat_ids[name] = cid
        await raw_db.dms_categories.insert_one({
            "id": cid,
            "tenant_id": DMS_TENANT_ID,
            "name": name,
            "description": f"{name} category",
            "created_at": _now(),
        })

    # ── circular header ──
    circular_id = _nid("pcir")
    await raw_db.dms_price_circulars.insert_one({
        "id": circular_id,
        "tenant_id": DMS_TENANT_ID,
        "title": CIRCULAR_TITLE,
        "effective_date": CIRCULAR_EFFECTIVE_DATE,   # YYYY-MM-DD
        "batch_no": 1,
        "batch_label": "Batch 1 — MAY'26",
        "is_active": True,
        "notes": "Initial price circular seeded from official PDF.",
        "created_by": None,
        "created_at": _now(),
    })

    # ── products (Product Master) + circular lines ──
    for row in PDF_ROWS:
        pid = _nid("prd")
        sku_root = _slug(f"{row['material_description']} {row['pack_size']}")
        product_doc = {
            "id": pid,
            "tenant_id": DMS_TENANT_ID,
            # ── UI-visible fields (Product Master) ──
            "category_id": cat_ids[row["category"]],
            "material_description": row["material_description"],
            "grade_specs": row["grade_specs"] or "-",
            "pack_size": row["pack_size"],
            # ── legacy fields kept for backward-compat with existing order code ──
            "name": f"{row['material_description']} ({row['pack_size']})",
            "sku_code": sku_root or _nid("SKU"),
            "description": "",
            "box_qty": 1,                          # DLP is per pack; order in packs
            "unit_price": float(row["dlp"]),       # mirror of latest active DLP
            "previous_price": None,
            # ── hidden bookkeeping fields ──
            "hsn": "27101980",
            "gst_pct": 0.0,                        # global setting overrides at order time
            "coupons_per_box": 100,
            "points_value": 10,
            "active": True,
            "created_at": _now(),
        }
        await raw_db.dms_products.insert_one(product_doc)

        # Legacy price_batches row (kept so order history / previous price still work)
        await raw_db.dms_price_batches.insert_one({
            "id": _nid("pb"),
            "tenant_id": DMS_TENANT_ID,
            "product_id": pid,
            "price": float(row["dlp"]),
            "from_date": _now(),
            "to_date": None,
            "created_at": _now(),
        })

        # NEW: one Price Circular line per product
        await raw_db.dms_price_circulars.insert_one({
            "id": _nid("pcl"),
            "tenant_id": DMS_TENANT_ID,
            "kind": "line",
            "circular_id": circular_id,
            "product_id": pid,
            "effective_date": CIRCULAR_EFFECTIVE_DATE,
            "batch_no": 1,
            "mrp": float(row["mrp"]),
            "dlp": float(row["dlp"]),
            "distributor_margin_pct": float(row["margin_pct"]),
            "cash_coupon": row["cash_coupon"] or "",
            "foc_benefits": row["foc_benefits"] or "",
            "monthly_gift": row["monthly_gift"] or "",
            "trade_discount": row["trade_discount"] or "",
            "is_active": True,
            "created_at": _now(),
        })


async def _seed_distributors_and_retailers(raw_db, ids):
    """Two distributors (Delhi/Mumbai), two retailers, with KYC + GPS."""
    dist_specs = [
        ("distributor1@gooil.com", "Anil Distributor — Delhi",  "Delhi",  "07AAACD1234M1Z5", 28.6139, 77.2090),
        ("distributor2@gooil.com", "Meena Traders — Mumbai",    "Mumbai", "27AAACM4321F1Z0", 19.0760, 72.8777),
    ]
    dist_ids: dict = {}
    for email, name, region, gstin, lat, lng in dist_specs:
        uid = ids.get(email)
        did = _nid("dist")
        dist_ids[email] = did
        await raw_db.dms_distributors.insert_one({
            "id": did,
            "tenant_id": DMS_TENANT_ID,
            "name": name,
            "email": email,
            "phone": "+91-9000000021",
            "address": f"{region}, India",
            "region": region,
            "gps_lat": lat,
            "gps_lng": lng,
            "location_link": f"https://maps.google.com/?q={lat},{lng}",
            "user_id": uid,
            "accountant_user_id": ids.get("distacct@gooil.com") if email == "distributor1@gooil.com" else None,
            "kyc": {
                "gstin": gstin,
                "pan": "ABCDE1234F",
                "aadhaar": "",
                "shop_license": f"SHP-2026-{region[:3].upper()}",
                "bank_name": "State Bank of India",
                "bank_account": "35270" + str(hash(email))[-6:],
                "bank_ifsc": "SBIN0001234",
                "notes": "",
            },
            "credit_limit": 1000000,
            "active": True,
            "created_at": _now(),
        })
        if uid:
            await raw_db.users.update_one({"id": uid}, {"$set": {"distributor_id": did}})
        if email == "distributor1@gooil.com":
            dacct = ids.get("distacct@gooil.com")
            if dacct:
                await raw_db.users.update_one({"id": dacct}, {"$set": {"distributor_id": did}})

    # Retailers linked to distributor1
    primary_did = dist_ids["distributor1@gooil.com"]
    retailer_specs = [
        ("retailer1@gooil.com", "Sharma Auto Parts",  "+91-9000000031", "Karol Bagh, New Delhi", "box_pcs", 28.6448, 77.2167),
        ("retailer2@gooil.com", "Verma Motors Store", "+91-9000000032", "Rohini, New Delhi",     "box",     28.7495, 77.0567),
    ]
    for email, name, phone, addr, mode, lat, lng in retailer_specs:
        uid = ids.get(email)
        rid = _nid("ret")
        await raw_db.dms_retailers.insert_one({
            "id": rid,
            "tenant_id": DMS_TENANT_ID,
            "name": name,
            "phone": phone,
            "email": email,
            "address": addr,
            "region": "Delhi",
            "gps_lat": lat,
            "gps_lng": lng,
            "location_link": f"https://maps.google.com/?q={lat},{lng}",
            "distributor_id": primary_did,
            "onboarded_by": ids.get("owner@gooil.com"),
            "onboarded_by_role": "owner",
            "user_id": uid,
            "kyc": {"gstin": "", "shop_license": f"SHP-DL-{str(hash(email))[-4:]}", "notes": ""},
            "documents": [],
            "credit_limit": 200000,
            "active": True,
            "created_at": _now(),
        })
        if uid:
            await raw_db.users.update_one({"id": uid}, {"$set": {"retailer_id": rid, "distributor_id": primary_did}})
        await raw_db.dms_ret_mode.insert_one({
            "id": _nid("rm"),
            "tenant_id": DMS_TENANT_ID,
            "distributor_id": primary_did,
            "retailer_id": rid,
            "mode": mode,
            "updated_at": _now(),
        })
    return dist_ids


async def _seed_inventory_and_retailer_prices(raw_db, dist_ids):
    """Owner starting inventory + distributor starting inventory + retailer selling prices."""
    products = await raw_db.dms_products.find({"tenant_id": DMS_TENANT_ID}, {"_id": 0}).to_list(2000)
    # owner stock
    for p in products:
        await raw_db.dms_owner_inventory.insert_one({
            "id": _nid("oinv"),
            "tenant_id": DMS_TENANT_ID,
            "product_id": p["id"],
            "qty_boxes": 100,
            "updated_at": _now(),
        })
        await raw_db.dms_stock_ledger.insert_one({
            "id": _nid("sl"),
            "tenant_id": DMS_TENANT_ID,
            "scope": "owner",
            "product_id": p["id"],
            "delta_boxes": 100,
            "reason": "initial_stock",
            "reference": "",
            "at": _now(),
        })
    # distributor stock + retailer selling price (cost + 15%)
    dists = await raw_db.dms_distributors.find({"tenant_id": DMS_TENANT_ID}, {"_id": 0}).to_list(50)
    for d in dists:
        for p in products:
            await raw_db.dms_distributor_inventory.insert_one({
                "id": _nid("dinv"),
                "tenant_id": DMS_TENANT_ID,
                "distributor_id": d["id"],
                "product_id": p["id"],
                "qty_boxes": 20,
                "cost_price": p["unit_price"],
                "updated_at": _now(),
            })
            await raw_db.dms_retailer_prices.insert_one({
                "id": _nid("rp"),
                "tenant_id": DMS_TENANT_ID,
                "distributor_id": d["id"],
                "product_id": p["id"],
                "selling_price": round(p["unit_price"] * 1.15, 2),
                "updated_at": _now(),
            })


async def _seed_assignments(raw_db, ids):
    dists = await raw_db.dms_distributors.find({"tenant_id": DMS_TENANT_ID}, {"_id": 0}).to_list(50)
    tl = ids.get("teamleader@gooil.com")
    sp = ids.get("salesperson@gooil.com")
    rm = ids.get("regionalmgr@gooil.com")
    owner_id = ids.get("owner@gooil.com")
    for d in dists:
        if tl:
            await raw_db.dms_tl_assignments.insert_one({
                "id": _nid("tla"),
                "tenant_id": DMS_TENANT_ID,
                "team_leader_id": tl,
                "distributor_id": d["id"],
                "assigned_by": owner_id,
                "at": _now(),
            })
    if sp and dists:
        await raw_db.dms_sp_assignments.insert_one({
            "id": _nid("spa"),
            "tenant_id": DMS_TENANT_ID,
            "salesperson_id": sp,
            "distributor_id": dists[0]["id"],
            "assigned_by": tl,
            "at": _now(),
        })
    if rm and tl:
        await raw_db.dms_rm_assignments.insert_one({
            "id": _nid("rma"),
            "tenant_id": DMS_TENANT_ID,
            "regional_manager_id": rm,
            "team_leader_id": tl,
            "assigned_by": owner_id,
            "at": _now(),
        })


async def seed_dms(raw_db):
    """Idempotent seed guarded by SEED_VERSION marker."""
    await ensure_dms_tenant(raw_db)

    marker = await raw_db.dms_meta.find_one({"id": "seed_marker"})
    if marker and marker.get("version") == SEED_VERSION:
        return True  # already seeded at this version

    # Full reset then reseed
    await _reset_dms_business_data(raw_db)
    ids = await _seed_users(raw_db)
    await _seed_settings(raw_db)
    await _seed_products_and_circular(raw_db)
    dist_ids = await _seed_distributors_and_retailers(raw_db, ids)
    await _seed_inventory_and_retailer_prices(raw_db, dist_ids)
    await _seed_assignments(raw_db, ids)

    await raw_db.dms_meta.update_one(
        {"id": "seed_marker"},
        {"$set": {"id": "seed_marker", "version": SEED_VERSION, "at": _now()}},
        upsert=True,
    )
    return True
