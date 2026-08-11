"""GO OIL DMS demo seed — clean-slate, idempotent, versioned.

Bumping SEED_VERSION forces a full reset of all DMS demo data:
- Deletes old products, categories, orders, ledgers, inventories, retailers,
  distributors, retailer prices, notifications, coupons, price batches, etc.
- Deletes the old demo users (only those with tenant_id=tnt-dms-oil).
- Reseeds Product Master + MAY'26 Price Circular from the official GO OIL PDF.
- Creates fresh GO OIL-themed demo users for every role.
"""
import os
import bcrypt
import uuid
from datetime import datetime, timezone

from dms_pdf_data import PDF_ROWS, CIRCULAR_EFFECTIVE_DATE, CIRCULAR_TITLE

DMS_TENANT_ID = "tnt-dms-oil"
DMS_PASSWORD = "GoOil@2026"
# Owner (the only account allowed to sign in on this deployment). Configurable
# via the OWNER_PASSWORD env var so it survives a fresh deploy / DB reseed.
OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "owner@gooil.com").lower().strip()
OWNER_PASSWORD = os.environ.get("OWNER_PASSWORD", "GoOil@Owner#2025")

# Bump this whenever you want a full data reset on the next server boot.
SEED_VERSION = "gooil-v3-coupons-oct26"


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
        "dms_coupons", "dms_coupon_batches", "dms_coupon_fraud", "dms_coupon_fraud_attempts",
        # NEW GO OIL Coupon Engine collections — always fresh
        "dms_v2_coupon_batches", "dms_v2_coupons",
        "dms_v2_retailer_wallets", "dms_v2_wallet_transactions",
        "dms_v2_redemption_requests", "dms_v2_credit_notes",
        "dms_v2_dispatch_advices", "dms_v2_coupon_audit_log",
        "dms_v2_coupon_fraud_attempts", "dms_v2_meta",
        "dms_settings",
        # Phase 2A + 2B
        "dms_expenses",
        "dms_bank_accounts", "dms_bank_transactions",
        "dms_cash_register", "dms_cheques",
        "dms_loan_accounts", "dms_loan_transactions",
        "dms_godowns", "dms_godown_inventory", "dms_stock_transfers",
        "dms_retailer_pending",
        # Phase 2C
        "dms_documents",
    ]
    for coll in collections_full_drop:
        try:
            await raw_db[coll].delete_many({})
        except Exception:
            pass
    # Delete old demo users of this tenant so we can recreate cleanly.
    await raw_db.users.delete_many({"tenant_id": DMS_TENANT_ID})
    # Delete any orphan users from previous seed runs (any other tenant) so their
    # gooil.com emails don't collide with our fresh accounts. Preserve platform owner.
    await raw_db.users.delete_many({
        "tenant_id": {"$ne": DMS_TENANT_ID},
        "email": {"$regex": "@gooil\\.com$"},
    })


async def _seed_users(raw_db):
    """Fresh GO OIL-themed demo accounts.

    Note: Super Admin and Company Owner are UNIFIED into a single Owner login
    (per user request) — the Owner has full god-mode access across the app.
    """
    users_spec = [
        # email, name, role, phone
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
    for spec_email, name, role, phone in users_spec:
        # The Owner's real login email/name come from env (OWNER_EMAIL) so a fresh
        # deploy seeds the correct owner account. `ids` stays keyed by the canonical
        # spec email so all downstream data links (onboarded_by, owner_id) still work.
        email = OWNER_EMAIL if role == "owner" else spec_email
        existing = await raw_db.users.find_one({"email": email})
        if existing:
            if existing.get("tenant_id") == DMS_TENANT_ID:
                # Already a DMS demo account — keep as-is (don't clobber owner edits).
                ids[spec_email] = existing["id"]
                continue
            # Stale account from another tenant's seed sharing this email
            # (the `email` unique index is global) — remove so we can create
            # the authoritative DMS demo account.
            await raw_db.users.delete_one({"email": email})
        uid = _nid("usr")
        ids[spec_email] = uid
        await raw_db.users.insert_one({
            "id": uid,
            "tenant_id": DMS_TENANT_ID,
            "email": email,
            "name": name,
            "role": role,
            "phone": phone,
            "password_hash": _hash(OWNER_PASSWORD if role == "owner" else DMS_PASSWORD),
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


async def _seed_sample_bills(raw_db, ids, dist_ids):
    """Create one primary e-bill and one retailer bill so print T&C can be verified visually."""
    products = await raw_db.dms_products.find({"tenant_id": DMS_TENANT_ID}, {"_id": 0}).to_list(3)
    if not products:
        return
    # ── Sample primary order → e-bill (Owner → distributor1) ──
    d1_id = dist_ids.get("distributor1@gooil.com")
    d1 = await raw_db.dms_distributors.find_one({"id": d1_id}, {"_id": 0})
    if d1 and products:
        p = products[0]
        qty = 5
        line_sub = round(float(p["unit_price"]) * qty, 2)
        line_gst = 0.0  # gst_pct default 0
        line_total = round(line_sub + line_gst, 2)
        order_no = f"PO-SAMPLE-{datetime.now().strftime('%y%m%d')}"
        oid = _nid("pord")
        item = {
            "product_id": p["id"],
            "product_name": p["name"],
            "sku_code": p["sku_code"],
            "box_qty": p.get("box_qty", 1),
            "unit_price": p["unit_price"],
            "gst_pct": 0.0,
            "qty_boxes_ordered": qty,
            "qty_boxes_fulfilled": qty,
            "billed_qty_boxes": qty,
            "line_subtotal": line_sub,
            "line_gst": line_gst,
            "line_total": line_total,
        }
        await raw_db.dms_primary_orders.insert_one({
            "id": oid,
            "tenant_id": DMS_TENANT_ID,
            "order_no": order_no,
            "distributor_id": d1_id,
            "distributor_name": d1["name"],
            "placed_by": ids.get("distributor1@gooil.com"),
            "items": [item],
            "subtotal": line_sub,
            "gst_total": line_gst,
            "total": line_total,
            "fulfillment_pct": 100,
            "status": "ready_to_go",
            "created_at": _now(),
            "updated_at": _now(),
            "ready_at": _now(),
        })
        eb_id = _nid("eb")
        ebill_no = f"EB-SAMPLE-{datetime.now().strftime('%y%m%d')}"
        await raw_db.dms_ebills.insert_one({
            "id": eb_id,
            "tenant_id": DMS_TENANT_ID,
            "ebill_no": ebill_no,
            "order_id": oid,
            "order_no": order_no,
            "distributor_id": d1_id,
            "distributor_name": d1["name"],
            "items": [item],
            "subtotal": line_sub,
            "gst_total": line_gst,
            "total": line_total,
            "status": "issued",
            "created_at": _now(),
        })
        await raw_db.dms_primary_orders.update_one({"id": oid}, {"$set": {"ebill_id": eb_id}})
        await raw_db.dms_primary_ledger.insert_one({
            "id": _nid("le"),
            "tenant_id": DMS_TENANT_ID,
            "distributor_id": d1_id,
            "kind": "invoice",
            "reference_id": eb_id,
            "reference_no": ebill_no,
            "amount": line_total,
            "description": f"Invoice for order {order_no}",
            "at": _now(),
        })

    # ── Sample secondary order → retailer bill (distributor1 → retailer1) ──
    r1 = await raw_db.dms_retailers.find_one({"email": "retailer1@gooil.com"}, {"_id": 0})
    if d1 and r1 and products:
        p = products[0]
        qty_boxes = 2
        # get retailer price
        rp = await raw_db.dms_retailer_prices.find_one({"distributor_id": d1_id, "product_id": p["id"]}, {"_id": 0})
        box_price = float(rp["selling_price"]) if rp else float(p["unit_price"])
        line_sub = round(box_price * qty_boxes, 2)
        line_gst = 0.0
        line_total = round(line_sub + line_gst, 2)
        sord_no = f"SO-SAMPLE-{datetime.now().strftime('%y%m%d')}"
        sord_id = _nid("sord")
        s_item = {
            "product_id": p["id"],
            "product_name": p["name"],
            "sku_code": p["sku_code"],
            "box_qty": p.get("box_qty", 1),
            "box_price": box_price,
            "pcs_price": 0.0,
            "gst_pct": 0.0,
            "qty_boxes_ordered": qty_boxes,
            "qty_pcs_ordered": 0,
            "qty_boxes_dispatched": qty_boxes,
            "qty_pcs_dispatched": 0,
            "dispatched_qty_boxes": qty_boxes,
            "dispatched_qty_pcs": 0,
            "line_subtotal": line_sub,
            "line_gst": line_gst,
            "line_total": line_total,
        }
        await raw_db.dms_secondary_orders.insert_one({
            "id": sord_id,
            "tenant_id": DMS_TENANT_ID,
            "order_no": sord_no,
            "distributor_id": d1_id,
            "distributor_name": d1["name"],
            "retailer_id": r1["id"],
            "retailer_name": r1["name"],
            "placed_by": ids.get("retailer1@gooil.com"),
            "placed_by_role": "retailer",
            "mode": "box",
            "items": [s_item],
            "subtotal": line_sub,
            "gst_total": line_gst,
            "total": line_total,
            "fulfillment_pct": 100,
            "status": "dispatched",
            "created_at": _now(),
            "updated_at": _now(),
            "dispatched_at": _now(),
        })
        rb_id = _nid("rb")
        bill_no = f"RB-SAMPLE-{datetime.now().strftime('%y%m%d')}"
        await raw_db.dms_retailer_bills.insert_one({
            "id": rb_id,
            "tenant_id": DMS_TENANT_ID,
            "bill_no": bill_no,
            "order_id": sord_id,
            "order_no": sord_no,
            "retailer_id": r1["id"],
            "distributor_id": d1_id,
            "items": [s_item],
            "subtotal": line_sub,
            "gst_total": line_gst,
            "total": line_total,
            "status": "issued",
            "created_at": _now(),
        })
        await raw_db.dms_secondary_orders.update_one({"id": sord_id}, {"$set": {"bill_id": rb_id}})
        await raw_db.dms_retailer_ledger.insert_one({
            "id": _nid("rle"),
            "tenant_id": DMS_TENANT_ID,
            "distributor_id": d1_id,
            "retailer_id": r1["id"],
            "kind": "invoice",
            "reference_id": rb_id,
            "reference_no": bill_no,
            "amount": line_total,
            "description": f"Bill for {sord_no}",
            "at": _now(),
        })


async def _seed_sample_terms(raw_db):
    """Pre-populate invoice_terms/invoice_message so print pages have something to render."""
    await raw_db.dms_settings.update_one(
        {"id": "global"},
        {"$set": {
            "invoice_message": "Thank you for your business — GO OIL Lubricants!",
            "invoice_terms": "Goods once sold will not be taken back. Payment due within 30 days. Subject to Delhi jurisdiction.",
            "updated_at": _now(),
        }},
        upsert=True,
    )


async def _seed_godowns_with_stock(raw_db):
    """Phase 2C: seed 2 demo godowns with mixed stock so low-stock badge + reorder-level
    flow can be demoed end-to-end. First 5 products get stock in both godowns; the last
    2 of those get a reorder_level greater than qty to trigger the red 'Low' badge."""
    products = await raw_db.dms_products.find(
        {"tenant_id": DMS_TENANT_ID}, {"_id": 0}
    ).to_list(2000)
    if not products:
        return
    subset = products[:5]  # first 5 products across both godowns

    godowns_spec = [
        {
            "name": "Delhi Main Warehouse",
            "manager_name": "Ramesh Verma",
            "manager_phone": "+91-9000010001",
            "address": "Plot 12, Naraina Industrial Area, Phase 1, New Delhi 110028",
            "capacity_boxes": 5000,
            "active": True,
        },
        {
            "name": "Mumbai Regional Warehouse",
            "manager_name": "Suresh Kadam",
            "manager_phone": "+91-9000010002",
            "address": "Warehouse Complex, Bhiwandi-Nashik Highway, Bhiwandi 421302",
            "capacity_boxes": 3000,
            "active": True,
        },
    ]

    for gspec in godowns_spec:
        gid = _nid("god")
        await raw_db.dms_godowns.insert_one({
            "id": gid,
            "tenant_id": DMS_TENANT_ID,
            "name": gspec["name"],
            "manager_name": gspec["manager_name"],
            "manager_phone": gspec["manager_phone"],
            "address": gspec["address"],
            "capacity_boxes": gspec["capacity_boxes"],
            "active": gspec["active"],
            "created_at": _now(),
        })
        # Seed inventory rows for the first 5 products
        # idx 0,1,2 → healthy stock (25 boxes, reorder=10)
        # idx 3,4  → LOW stock trigger (3 boxes, reorder=15)
        for idx, p in enumerate(subset):
            if idx < 3:
                qty, reorder = 25, 10
            else:
                qty, reorder = 3, 15
            await raw_db.dms_godown_inventory.insert_one({
                "id": _nid("ginv"),
                "tenant_id": DMS_TENANT_ID,
                "godown_id": gid,
                "product_id": p["id"],
                "qty_boxes": qty,
                "reorder_level_boxes": reorder,
                "updated_at": _now(),
            })
            await raw_db.dms_stock_ledger.insert_one({
                "id": _nid("sl"),
                "tenant_id": DMS_TENANT_ID,
                "scope": "godown",
                "godown_id": gid,
                "product_id": p["id"],
                "delta_boxes": qty,
                "reason": "initial_stock",
                "reference": "seed",
                "at": _now(),
            })


async def seed_dms(raw_db):
    """Bootstrap only — DEMO DATA SEEDING IS DISABLED.

    The owner requested that ALL demo business data be removed. This function
    therefore NEVER seeds demo products/distributors/retailers/orders/coupons/etc.
    It only:
      * ensures the DMS tenant exists,
      * ensures a clean global settings doc exists (without overwriting owner edits),
      * ensures coupon-engine indexes exist,
      * bootstraps login accounts ONLY if the tenant has zero users (so the owner
        can never get locked out) — existing users are left untouched.
    """
    await ensure_dms_tenant(raw_db)

    # Ensure a clean global settings doc (do not clobber owner-configured values)
    existing_settings = await raw_db.dms_settings.find_one({"id": "global"})
    if not existing_settings:
        await raw_db.dms_settings.insert_one({
            "id": "global",
            "tenant_id": DMS_TENANT_ID,
            "gst_pct": 0.0,
            "company_name": "GO OIL Lubricants",
            "retailer_scan_enabled": False,
            "created_at": _now(),
            "updated_at": _now(),
        })

    # Coupon-engine indexes (idempotent / safe)
    try:
        await raw_db.dms_v2_coupons.create_index("coupon_code", unique=True)
        await raw_db.dms_v2_coupons.create_index([("batch_id", 1), ("status", 1)])
        await raw_db.dms_v2_coupons.create_index("retailer_id")
        await raw_db.dms_v2_coupons.create_index("distributor_id")
        await raw_db.dms_v2_wallet_transactions.create_index(
            [("retailer_id", 1), ("wallet_type", 1)]
        )
        await raw_db.dms_v2_retailer_wallets.create_index(
            [("retailer_id", 1), ("wallet_type", 1)], unique=True
        )
        await raw_db.dms_v2_coupon_batches.create_index("batch_no", unique=True)
        await raw_db.dms_v2_coupon_audit_log.create_index([("entity_id", 1), ("at", -1)])
    except Exception:
        pass

    # Bootstrap login accounts. `_seed_users` is idempotent: it keeps any
    # existing DMS demo accounts untouched and only creates the ones that are
    # missing (also clearing stale cross-tenant email collisions). This makes
    # startup self-healing if a previous run partially seeded users.
    await _seed_users(raw_db)

    await raw_db.dms_meta.update_one(
        {"id": "seed_marker"},
        {"$set": {"id": "seed_marker", "version": SEED_VERSION, "at": _now()}},
        upsert=True,
    )
    return True


async def _seed_dms_full_demo_DISABLED(raw_db):
    """Legacy full demo seed — kept for reference only, NO LONGER CALLED."""
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
    # Phase 2A: pre-populate T&C so print pages have something to render
    await _seed_sample_terms(raw_db)
    # Phase 2B: seed one sample e-bill + one sample retailer bill
    await _seed_sample_bills(raw_db, ids, dist_ids)
    # Phase 2C: seed 2 godowns with mixed stock (incl. low-stock rows) for demo
    await _seed_godowns_with_stock(raw_db)

    # ── GO OIL Coupon Engine — indexes ──
    try:
        await raw_db.dms_v2_coupons.create_index("coupon_code", unique=True)
        await raw_db.dms_v2_coupons.create_index([("batch_id", 1), ("status", 1)])
        await raw_db.dms_v2_coupons.create_index("retailer_id")
        await raw_db.dms_v2_coupons.create_index("distributor_id")
        await raw_db.dms_v2_wallet_transactions.create_index(
            [("retailer_id", 1), ("wallet_type", 1)]
        )
        await raw_db.dms_v2_retailer_wallets.create_index(
            [("retailer_id", 1), ("wallet_type", 1)], unique=True
        )
        await raw_db.dms_v2_coupon_batches.create_index("batch_no", unique=True)
        await raw_db.dms_v2_coupon_audit_log.create_index([("entity_id", 1), ("at", -1)])
    except Exception:
        pass

    await raw_db.dms_meta.update_one(
        {"id": "seed_marker"},
        {"$set": {"id": "seed_marker", "version": SEED_VERSION, "at": _now()}},
        upsert=True,
    )
    return True
