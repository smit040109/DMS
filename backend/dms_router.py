"""
Simple DMS — Distribution Management System.
Fresh, minimal router. Only two workflows:
  1) Primary Sales   (Owner  ↔ Distributor)
  2) Secondary Sales (Distributor ↔ Retailer)

All endpoints prefixed /api/dms/*
All collections prefixed dms_*
Tenant scope: `tnt-dms-oil` (dedicated tenant so existing tenancy wrapper isolates it).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Body, Query, UploadFile, File
from pydantic import BaseModel


DMS_TENANT_ID = "tnt-dms-oil"

# ────────────────────────────── helpers ──────────────────────────────
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _nid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _clean(d: Dict[str, Any]) -> Dict[str, Any]:
    if d and "_id" in d:
        d.pop("_id", None)
    return d


def _round(v: Any, n: int = 2) -> float:
    try:
        return round(float(v), n)
    except Exception:
        return 0.0


# ────────────────────────────── router builder ──────────────────────────────
def build_dms_router(db, get_current_user):
    router = APIRouter(prefix="/dms", tags=["dms"])

    # =========================================================================
    # role guards
    # =========================================================================
    def _guard(*allowed):
        async def _dep(user: dict = Depends(get_current_user)) -> dict:
            role = user.get("role")
            if role in allowed or role == "super_admin":
                return user
            raise HTTPException(status_code=403, detail=f"Requires role in {allowed}")
        return _dep

    owner_only = _guard("owner")  # super_admin implicit
    owner_or_accountant = _guard("owner", "owner_accountant")
    distributor_only = _guard("distributor")
    retailer_only = _guard("retailer")
    salesperson_only = _guard("salesperson")
    team_leader_only = _guard("team_leader")
    regional_manager_only = _guard("regional_manager")
    dist_or_dacct = _guard("distributor", "distributor_accountant")

    # =========================================================================
    # Notifications (simple in-app)
    # =========================================================================
    async def notify(recipient_id: str, kind: str, title: str, body: str, link: Optional[str] = None):
        await db.dms_notifications.insert_one({
            "id": _nid("ntf"),
            "recipient_id": recipient_id,
            "kind": kind,
            "title": title,
            "body": body,
            "link": link,
            "read": False,
            "created_at": _now(),
        })

    @router.get("/notifications")
    async def get_notifications(user: dict = Depends(get_current_user)):
        docs = await db.dms_notifications.find(
            {"recipient_id": user["id"]}, {"_id": 0}
        ).sort("created_at", -1).to_list(50)
        unread = await db.dms_notifications.count_documents({"recipient_id": user["id"], "read": False})
        return {"data": docs, "unread": unread}

    @router.post("/notifications/{nid}/read")
    async def mark_read(nid: str, user: dict = Depends(get_current_user)):
        await db.dms_notifications.update_one(
            {"id": nid, "recipient_id": user["id"]}, {"$set": {"read": True}}
        )
        return {"ok": True}

    @router.post("/notifications/read-all")
    async def mark_all_read(user: dict = Depends(get_current_user)):
        await db.dms_notifications.update_many(
            {"recipient_id": user["id"], "read": False}, {"$set": {"read": True}}
        )
        return {"ok": True}

    # =========================================================================
    # CATEGORIES (product types)
    # =========================================================================
    @router.get("/categories")
    async def list_categories(user: dict = Depends(get_current_user)):
        docs = await db.dms_categories.find({}, {"_id": 0}).sort("name", 1).to_list(500)
        return {"data": docs, "count": len(docs)}

    @router.post("/categories")
    async def create_category(body: Dict[str, Any] = Body(...), user: dict = Depends(owner_only)):
        if not body.get("name"):
            raise HTTPException(status_code=400, detail="name required")
        doc = {
            "id": _nid("cat"),
            "name": body["name"],
            "description": body.get("description", ""),
            "created_at": _now(),
        }
        await db.dms_categories.insert_one(doc)
        return _clean(doc)

    @router.put("/categories/{cid}")
    async def update_category(cid: str, body: Dict[str, Any] = Body(...), user: dict = Depends(owner_only)):
        upd = {k: v for k, v in body.items() if k in {"name", "description"}}
        r = await db.dms_categories.update_one({"id": cid}, {"$set": upd})
        if r.matched_count == 0:
            raise HTTPException(status_code=404, detail="Category not found")
        return {"ok": True}

    @router.delete("/categories/{cid}")
    async def delete_category(cid: str, user: dict = Depends(owner_only)):
        # block if products exist
        cnt = await db.dms_products.count_documents({"category_id": cid})
        if cnt > 0:
            raise HTTPException(status_code=400, detail=f"Category has {cnt} products; delete them first")
        await db.dms_categories.delete_one({"id": cid})
        return {"ok": True}

    # =========================================================================
    # PRODUCTS + PRICE BATCHES
    # =========================================================================
    async def _resolve_visible_products_for_distributor(distributor_id: str) -> List[Dict[str, Any]]:
        """Return products that owner has NOT hidden for this distributor."""
        hidden = set()
        async for v in db.dms_dist_visibility.find({"distributor_id": distributor_id, "visible": False}, {"_id": 0}):
            hidden.add(v["product_id"])
        products = await db.dms_products.find({"active": True}, {"_id": 0}).sort("name", 1).to_list(1000)
        return [p for p in products if p["id"] not in hidden]

    @router.get("/products")
    async def list_products(user: dict = Depends(get_current_user)):
        """Owner sees ALL; distributor sees visible ones only."""
        role = user.get("role")
        if role == "distributor":
            dist_id = user.get("distributor_id")
            if not dist_id:
                return {"data": [], "count": 0}
            docs = await _resolve_visible_products_for_distributor(dist_id)
        else:
            docs = await db.dms_products.find({}, {"_id": 0}).sort("name", 1).to_list(1000)
        # Enrich with category name
        cats = {c["id"]: c["name"] async for c in db.dms_categories.find({}, {"_id": 0, "id": 1, "name": 1})}
        for p in docs:
            p["category_name"] = cats.get(p.get("category_id"), "")
        return {"data": docs, "count": len(docs)}

    @router.post("/products")
    async def create_product(body: Dict[str, Any] = Body(...), user: dict = Depends(owner_only)):
        required = ["name", "category_id", "sku_code", "box_qty", "unit_price"]
        for k in required:
            if body.get(k) in (None, ""):
                raise HTTPException(status_code=400, detail=f"{k} required")
        # sku unique
        existing = await db.dms_products.find_one({"sku_code": body["sku_code"]})
        if existing:
            raise HTTPException(status_code=400, detail="SKU code already exists")
        pid = _nid("prd")
        unit_price = _round(body["unit_price"])
        box_qty = int(body["box_qty"])
        doc = {
            "id": pid,
            "name": body["name"],
            "category_id": body["category_id"],
            "sku_code": body["sku_code"],
            "description": body.get("description", ""),
            "box_qty": box_qty,       # bottles per box
            "unit_price": unit_price, # per box
            "previous_price": None,
            "hsn": body.get("hsn", ""),
            "gst_pct": _round(body.get("gst_pct", 18)),
            "coupons_per_box": int(body.get("coupons_per_box", 100)),
            "points_value": _round(body.get("points_value", 10)),
            "active": True,
            "created_at": _now(),
        }
        await db.dms_products.insert_one(doc)
        # initial price batch
        await db.dms_price_batches.insert_one({
            "id": _nid("pb"),
            "product_id": pid,
            "price": unit_price,
            "from_date": _now(),
            "to_date": None,
            "created_at": _now(),
        })
        return _clean(doc)

    @router.put("/products/{pid}")
    async def update_product(pid: str, body: Dict[str, Any] = Body(...), user: dict = Depends(owner_only)):
        current = await db.dms_products.find_one({"id": pid}, {"_id": 0})
        if not current:
            raise HTTPException(status_code=404, detail="Product not found")
        upd: Dict[str, Any] = {}
        for k in ["name", "description", "box_qty", "hsn", "gst_pct", "active", "coupons_per_box", "points_value"]:
            if k in body:
                upd[k] = body[k]
        if "unit_price" in body:
            new_price = _round(body["unit_price"])
            if new_price != current.get("unit_price"):
                # close current batch, open new batch
                await db.dms_price_batches.update_one(
                    {"product_id": pid, "to_date": None},
                    {"$set": {"to_date": _now()}}
                )
                await db.dms_price_batches.insert_one({
                    "id": _nid("pb"),
                    "product_id": pid,
                    "price": new_price,
                    "from_date": _now(),
                    "to_date": None,
                    "created_at": _now(),
                })
                upd["previous_price"] = current.get("unit_price")
                upd["unit_price"] = new_price
        upd["updated_at"] = _now()
        await db.dms_products.update_one({"id": pid}, {"$set": upd})
        doc = await db.dms_products.find_one({"id": pid}, {"_id": 0})
        return _clean(doc or {})

    @router.get("/products/{pid}/price-history")
    async def price_history(pid: str, user: dict = Depends(get_current_user)):
        docs = await db.dms_price_batches.find({"product_id": pid}, {"_id": 0}).sort("from_date", -1).to_list(200)
        return {"data": docs}

    # =========================================================================
    # OWNER INVENTORY
    # =========================================================================
    async def _get_owner_stock(product_id: str) -> int:
        doc = await db.dms_owner_inventory.find_one({"product_id": product_id}, {"_id": 0})
        return int(doc.get("qty_boxes", 0)) if doc else 0

    async def _adjust_owner_stock(product_id: str, delta_boxes: int, reason: str, ref: str = ""):
        cur = await db.dms_owner_inventory.find_one({"product_id": product_id})
        if cur:
            new_qty = int(cur.get("qty_boxes", 0)) + delta_boxes
            await db.dms_owner_inventory.update_one(
                {"product_id": product_id},
                {"$set": {"qty_boxes": max(new_qty, 0), "updated_at": _now()}},
            )
        else:
            await db.dms_owner_inventory.insert_one({
                "id": _nid("oinv"),
                "product_id": product_id,
                "qty_boxes": max(delta_boxes, 0),
                "updated_at": _now(),
            })
        # ledger row
        await db.dms_stock_ledger.insert_one({
            "id": _nid("sl"),
            "scope": "owner",
            "product_id": product_id,
            "delta_boxes": delta_boxes,
            "reason": reason,
            "reference": ref,
            "at": _now(),
        })

    @router.get("/owner/inventory")
    async def owner_inventory(user: dict = Depends(owner_or_accountant)):
        rows = await db.dms_owner_inventory.find({}, {"_id": 0}).to_list(1000)
        # enrich with product info
        pids = [r["product_id"] for r in rows]
        prods = {p["id"]: p async for p in db.dms_products.find({"id": {"$in": pids}}, {"_id": 0})}
        for r in rows:
            p = prods.get(r["product_id"], {})
            r["product_name"] = p.get("name", "")
            r["sku_code"] = p.get("sku_code", "")
            r["box_qty"] = p.get("box_qty", 0)
            r["unit_price"] = p.get("unit_price", 0)
            r["value"] = _round((r.get("qty_boxes", 0) or 0) * (p.get("unit_price", 0) or 0))
        rows.sort(key=lambda x: x.get("product_name", ""))
        return {"data": rows, "total_value": _round(sum(r.get("value", 0) for r in rows))}

    @router.post("/owner/inventory/adjust")
    async def owner_inv_adjust(body: Dict[str, Any] = Body(...), user: dict = Depends(owner_only)):
        pid = body.get("product_id")
        delta = int(body.get("delta_boxes", 0))
        if not pid or delta == 0:
            raise HTTPException(status_code=400, detail="product_id + non-zero delta_boxes required")
        await _adjust_owner_stock(pid, delta, body.get("reason", "manual_adjust"), body.get("reference", ""))
        return {"ok": True, "new_qty": await _get_owner_stock(pid)}

    # =========================================================================
    # DISTRIBUTORS + KYC + user
    # =========================================================================
    async def _create_dms_user(email: str, password: str, name: str, role: str, extra: Dict[str, Any] = None):
        import bcrypt
        existing = await db.users.find_one({"email": email.lower()})
        if existing:
            raise HTTPException(status_code=400, detail=f"User email {email} already exists")
        uid = _nid("usr")
        doc = {
            "id": uid,
            "email": email.lower(),
            "name": name,
            "role": role,
            "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
            "active": True,
            "created_at": _now(),
        }
        if extra:
            doc.update(extra)
        await db.users.insert_one(doc)
        return uid

    @router.get("/distributors")
    async def list_distributors(user: dict = Depends(get_current_user)):
        role = user.get("role")
        query: Dict[str, Any] = {}
        # salesperson: only assigned; team_leader: only their assigned; distributor: only themselves
        if role == "distributor":
            query = {"id": user.get("distributor_id")}
        elif role == "salesperson":
            # only assigned distributors
            assigns = await db.dms_sp_assignments.find({"salesperson_id": user["id"]}, {"_id": 0}).to_list(500)
            ids = [a["distributor_id"] for a in assigns]
            query = {"id": {"$in": ids}} if ids else {"id": "__none__"}
        elif role == "team_leader":
            assigns = await db.dms_tl_assignments.find({"team_leader_id": user["id"]}, {"_id": 0}).to_list(500)
            ids = [a["distributor_id"] for a in assigns]
            query = {"id": {"$in": ids}} if ids else {"id": "__none__"}
        docs = await db.dms_distributors.find(query, {"_id": 0}).sort("name", 1).to_list(500)
        return {"data": docs, "count": len(docs)}

    @router.post("/distributors")
    async def create_distributor(body: Dict[str, Any] = Body(...), user: dict = Depends(owner_only)):
        required = ["name", "email", "password", "phone", "address"]
        for k in required:
            if not body.get(k):
                raise HTTPException(status_code=400, detail=f"{k} required")
        did = _nid("dist")
        # create user for distributor
        uid = await _create_dms_user(
            email=body["email"],
            password=body["password"],
            name=body["name"],
            role="distributor",
            extra={"distributor_id": did, "phone": body["phone"]},
        )
        # optional accountant
        accountant_uid = None
        if body.get("accountant_email"):
            accountant_uid = await _create_dms_user(
                email=body["accountant_email"],
                password=body.get("accountant_password") or "Demo@2026",
                name=body.get("accountant_name") or f"{body['name']} Accountant",
                role="distributor_accountant",
                extra={"distributor_id": did},
            )
        dist = {
            "id": did,
            "name": body["name"],
            "email": body["email"].lower(),
            "phone": body["phone"],
            "address": body["address"],
            "region": body.get("region", ""),
            "user_id": uid,
            "accountant_user_id": accountant_uid,
            # geo — for Owner live map
            "location_link": body.get("location_link", ""),
            "gps_lat": body.get("gps_lat"),
            "gps_lng": body.get("gps_lng"),
            # KYC
            "kyc": {
                "gstin": body.get("gstin", ""),
                "pan": body.get("pan", ""),
                "aadhaar": body.get("aadhaar", ""),
                "shop_license": body.get("shop_license", ""),
                "bank_name": body.get("bank_name", ""),
                "bank_account": body.get("bank_account", ""),
                "bank_ifsc": body.get("bank_ifsc", ""),
                "notes": body.get("kyc_notes", ""),
            },
            "credit_limit": _round(body.get("credit_limit", 0)),
            "documents": body.get("documents", []),
            "active": True,
            "created_at": _now(),
        }
        await db.dms_distributors.insert_one(dist)
        return _clean(dist)

    @router.get("/distributors/{did}")
    async def get_distributor(did: str, user: dict = Depends(get_current_user)):
        doc = await db.dms_distributors.find_one({"id": did}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Distributor not found")
        return doc

    @router.put("/distributors/{did}")
    async def update_distributor(did: str, body: Dict[str, Any] = Body(...), user: dict = Depends(owner_only)):
        upd: Dict[str, Any] = {}
        for k in ["name", "phone", "address", "region", "credit_limit", "active",
                  "location_link", "gps_lat", "gps_lng", "documents"]:
            if k in body:
                upd[k] = body[k]
        if "kyc" in body:
            upd["kyc"] = body["kyc"]
        upd["updated_at"] = _now()
        r = await db.dms_distributors.update_one({"id": did}, {"$set": upd})
        if r.matched_count == 0:
            raise HTTPException(status_code=404, detail="Distributor not found")
        return {"ok": True}

    # ── product visibility per distributor (owner control) ──
    @router.get("/distributors/{did}/visibility")
    async def get_dist_visibility(did: str, user: dict = Depends(owner_only)):
        products = await db.dms_products.find({}, {"_id": 0}).sort("name", 1).to_list(1000)
        vis_map = {v["product_id"]: v.get("visible", True)
                   async for v in db.dms_dist_visibility.find({"distributor_id": did}, {"_id": 0})}
        out = []
        for p in products:
            out.append({
                "product_id": p["id"],
                "product_name": p["name"],
                "sku_code": p["sku_code"],
                "visible": vis_map.get(p["id"], True),
            })
        return {"data": out}

    @router.put("/distributors/{did}/visibility")
    async def set_dist_visibility(did: str, body: Dict[str, Any] = Body(...), user: dict = Depends(owner_only)):
        pid = body.get("product_id")
        visible = bool(body.get("visible", True))
        if not pid:
            raise HTTPException(status_code=400, detail="product_id required")
        await db.dms_dist_visibility.update_one(
            {"distributor_id": did, "product_id": pid},
            {"$set": {"distributor_id": did, "product_id": pid, "visible": visible, "updated_at": _now()}},
            upsert=True,
        )
        return {"ok": True}

    # =========================================================================
    # DISTRIBUTOR — browse & place primary order
    # =========================================================================
    @router.get("/distributor/browse")
    async def distributor_browse(user: dict = Depends(distributor_only)):
        did = user.get("distributor_id")
        if not did:
            raise HTTPException(status_code=400, detail="Not linked to a distributor")
        products = await _resolve_visible_products_for_distributor(did)
        cats = {c["id"]: c["name"] async for c in db.dms_categories.find({}, {"_id": 0, "id": 1, "name": 1})}
        # attach available owner stock, category name
        for p in products:
            p["category_name"] = cats.get(p.get("category_id"), "")
            p["owner_stock_boxes"] = await _get_owner_stock(p["id"])
        return {"data": products}

    # =========================================================================
    # PRIMARY ORDERS
    #   Lifecycle: pending → partially_fulfilled → ready_to_go → received
    # =========================================================================
    @router.post("/primary-orders")
    async def place_primary_order(body: Dict[str, Any] = Body(...), user: dict = Depends(distributor_only)):
        did = user.get("distributor_id")
        if not did:
            raise HTTPException(status_code=400, detail="Not linked to a distributor")
        items = body.get("items") or []
        if not items:
            raise HTTPException(status_code=400, detail="items[] required")
        dist = await db.dms_distributors.find_one({"id": did}, {"_id": 0})
        if not dist:
            raise HTTPException(status_code=404, detail="Distributor not found")

        # normalise items — always price at CURRENT price
        order_items = []
        subtotal = 0.0
        gst_total = 0.0
        # global GST% from settings (default 0 until owner configures)
        settings_doc = await db.dms_settings.find_one({"id": "global"}, {"_id": 0}) or {}
        global_gst = float(settings_doc.get("gst_pct") or 0)
        for it in items:
            pid = it.get("product_id")
            qty_boxes = int(it.get("qty_boxes", 0))
            if not pid or qty_boxes <= 0:
                continue
            p = await db.dms_products.find_one({"id": pid}, {"_id": 0})
            if not p:
                raise HTTPException(status_code=400, detail=f"Product {pid} not found")
            unit_price = _round(p["unit_price"])
            line_sub = _round(unit_price * qty_boxes)
            line_gst = _round(line_sub * (global_gst / 100.0))
            subtotal += line_sub
            gst_total += line_gst
            order_items.append({
                "product_id": pid,
                "product_name": p["name"],
                "sku_code": p["sku_code"],
                "box_qty": p["box_qty"],
                "unit_price": unit_price,           # price applied
                "previous_price": p.get("previous_price"),
                "gst_pct": global_gst,
                "qty_boxes_ordered": qty_boxes,
                "qty_boxes_fulfilled": 0,
                "line_subtotal": line_sub,
                "line_gst": line_gst,
                "line_total": _round(line_sub + line_gst),
            })
        if not order_items:
            raise HTTPException(status_code=400, detail="No valid items")

        total = _round(subtotal + gst_total)
        order = {
            "id": _nid("po"),
            "order_no": f"PO-{datetime.now().strftime('%y%m%d%H%M%S')}",
            "distributor_id": did,
            "distributor_name": dist["name"],
            "items": order_items,
            "subtotal": _round(subtotal),
            "gst_total": _round(gst_total),
            "total": total,
            "status": "pending",
            "fulfillment_pct": 0,
            "notes": body.get("notes", ""),
            "created_at": _now(),
            "created_by": user["id"],
            "ready_at": None,
            "received_at": None,
            "ebill_id": None,
        }
        await db.dms_primary_orders.insert_one(order)

        # notify all owners + owner_accountants
        async for u in db.users.find({"role": {"$in": ["owner", "owner_accountant"]}}, {"_id": 0, "id": 1}):
            await notify(
                u["id"], "primary_order",
                f"New order from {dist['name']}",
                f"{order['order_no']} — {len(order_items)} items — ₹{total:,.0f}",
                f"/dms/owner/primary-orders/{order['id']}",
            )
        return _clean(order)

    @router.get("/primary-orders")
    async def list_primary_orders(status: Optional[str] = None, user: dict = Depends(get_current_user)):
        role = user.get("role")
        q: Dict[str, Any] = {}
        if status:
            q["status"] = status
        if role == "distributor":
            q["distributor_id"] = user.get("distributor_id")
        elif role in ("distributor_accountant",):
            q["distributor_id"] = user.get("distributor_id")
        docs = await db.dms_primary_orders.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
        return {"data": docs, "count": len(docs)}

    @router.get("/primary-orders/{oid}")
    async def get_primary_order(oid: str, user: dict = Depends(get_current_user)):
        doc = await db.dms_primary_orders.find_one({"id": oid}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Order not found")
        role = user.get("role")
        if role in ("distributor", "distributor_accountant") and doc.get("distributor_id") != user.get("distributor_id"):
            raise HTTPException(status_code=403, detail="Forbidden")
        # attach ebill + attachments
        if doc.get("ebill_id"):
            eb = await db.dms_ebills.find_one({"id": doc["ebill_id"]}, {"_id": 0})
            doc["ebill"] = eb
        atts = await db.dms_attachments.find({"reference_id": oid}, {"_id": 0}).to_list(50)
        doc["attachments"] = atts
        return doc

    @router.post("/primary-orders/{oid}/fulfill-line")
    async def fulfill_primary_line(oid: str, body: Dict[str, Any] = Body(...), user: dict = Depends(owner_only)):
        """Set qty_boxes_fulfilled for a specific product line."""
        pid = body.get("product_id")
        qty = int(body.get("qty_boxes_fulfilled", 0))
        if not pid:
            raise HTTPException(status_code=400, detail="product_id required")
        order = await db.dms_primary_orders.find_one({"id": oid}, {"_id": 0})
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order["status"] in ("ready_to_go", "received"):
            raise HTTPException(status_code=400, detail="Order already sent")
        # update line
        line = next((it for it in order["items"] if it["product_id"] == pid), None)
        if not line:
            raise HTTPException(status_code=400, detail="Line not in order")
        qty = max(0, min(qty, line["qty_boxes_ordered"]))
        line["qty_boxes_fulfilled"] = qty
        # recompute fulfillment_pct
        ord_total = sum(it["qty_boxes_ordered"] for it in order["items"])
        ful_total = sum(it["qty_boxes_fulfilled"] for it in order["items"])
        pct = int(round((ful_total / ord_total) * 100)) if ord_total > 0 else 0
        new_status = order["status"]
        if pct == 0:
            new_status = "pending"
        elif pct < 100:
            new_status = "partially_fulfilled"
        else:
            new_status = "fulfilled"
        await db.dms_primary_orders.update_one(
            {"id": oid},
            {"$set": {"items": order["items"], "fulfillment_pct": pct, "status": new_status, "updated_at": _now()}},
        )
        return {"ok": True, "fulfillment_pct": pct, "status": new_status}

    @router.post("/primary-orders/{oid}/ready")
    async def mark_ready_to_go(oid: str, user: dict = Depends(owner_only)):
        order = await db.dms_primary_orders.find_one({"id": oid}, {"_id": 0})
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order["status"] not in ("partially_fulfilled", "fulfilled", "pending"):
            raise HTTPException(status_code=400, detail=f"Cannot ready an order in status {order['status']}")
        # decrement owner inventory for fulfilled quantities
        # (owner stock may already be low — we just record the movement)
        for it in order["items"]:
            if it["qty_boxes_fulfilled"] > 0:
                await _adjust_owner_stock(
                    it["product_id"], -it["qty_boxes_fulfilled"], "primary_dispatch", order["order_no"]
                )
        # generate e-bill
        # total based on fulfilled qty × price
        sub = 0.0
        gst = 0.0
        billed_items = []
        for it in order["items"]:
            if it["qty_boxes_fulfilled"] <= 0:
                continue
            line_sub = _round(it["unit_price"] * it["qty_boxes_fulfilled"])
            line_gst = _round(line_sub * (it["gst_pct"] / 100.0))
            sub += line_sub
            gst += line_gst
            billed_items.append({
                **it,
                "billed_qty_boxes": it["qty_boxes_fulfilled"],
                "line_subtotal": line_sub,
                "line_gst": line_gst,
                "line_total": _round(line_sub + line_gst),
            })
        total = _round(sub + gst)
        ebill = {
            "id": _nid("eb"),
            "ebill_no": f"EB-{datetime.now().strftime('%y%m%d%H%M%S')}",
            "order_id": oid,
            "order_no": order["order_no"],
            "distributor_id": order["distributor_id"],
            "distributor_name": order["distributor_name"],
            "items": billed_items,
            "subtotal": _round(sub),
            "gst_total": _round(gst),
            "total": total,
            "status": "issued",
            "created_at": _now(),
        }
        await db.dms_ebills.insert_one(ebill)
        # primary ledger: debit distributor (they owe)
        await db.dms_primary_ledger.insert_one({
            "id": _nid("le"),
            "distributor_id": order["distributor_id"],
            "kind": "invoice",
            "reference_id": ebill["id"],
            "reference_no": ebill["ebill_no"],
            "amount": total,
            "description": f"Invoice for order {order['order_no']}",
            "at": _now(),
        })
        # update order
        await db.dms_primary_orders.update_one(
            {"id": oid},
            {"$set": {"status": "ready_to_go", "ebill_id": ebill["id"], "ready_at": _now(), "updated_at": _now()}},
        )
        # ── Coupon auto-assignment: pull next N unused coupons per line ──
        assigned_summary = []
        for it in billed_items:
            pid_ = it["product_id"]
            prod = await db.dms_products.find_one({"id": pid_}, {"_id": 0, "coupons_per_box": 1, "name": 1})
            per_box = int((prod or {}).get("coupons_per_box", 100) or 100)
            need = int(it["billed_qty_boxes"]) * per_box
            if need <= 0:
                continue
            unused = await db.dms_coupons.find(
                {"product_id": pid_, "status": "unused"}, {"_id": 0, "id": 1, "coupon_code": 1}
            ).sort("created_at", 1).limit(need).to_list(need)
            assigned_summary.append({
                "product_id": pid_, "product_name": (prod or {}).get("name"),
                "requested": need, "assigned": len(unused),
                "shortfall": max(0, need - len(unused)),
            })
            if unused:
                ids = [u["id"] for u in unused]
                await db.dms_coupons.update_many(
                    {"id": {"$in": ids}},
                    {"$set": {
                        "assigned_distributor_id": order["distributor_id"],
                        "assigned_distributor_name": order["distributor_name"],
                        "assigned_on": _now(),
                        "assigned_on_ebill_id": ebill["id"],
                        "assigned_on_ebill_no": ebill["ebill_no"],
                        "status": "assigned",
                    }},
                )
        if assigned_summary:
            await db.dms_ebills.update_one({"id": ebill["id"]}, {"$set": {"coupons_assigned": assigned_summary}})
        # notify distributor
        dist_user = await db.users.find_one({"distributor_id": order["distributor_id"], "role": "distributor"}, {"_id": 0, "id": 1})
        if dist_user:
            await notify(
                dist_user["id"], "order_ready",
                f"Order {order['order_no']} ready to go",
                f"e-Bill {ebill['ebill_no']} • Total ₹{total:,.0f}",
                f"/dms/distributor/my-orders/{oid}",
            )
        return {"ok": True, "ebill_id": ebill["id"], "status": "ready_to_go"}

    @router.post("/primary-orders/{oid}/receive")
    async def mark_received(oid: str, user: dict = Depends(distributor_only)):
        order = await db.dms_primary_orders.find_one({"id": oid}, {"_id": 0})
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.get("distributor_id") != user.get("distributor_id"):
            raise HTTPException(status_code=403, detail="Not your order")
        if order["status"] != "ready_to_go":
            raise HTTPException(status_code=400, detail=f"Cannot receive an order in status {order['status']}")
        # move stock into distributor inventory
        for it in order["items"]:
            q = int(it.get("qty_boxes_fulfilled", 0))
            if q <= 0:
                continue
            existing = await db.dms_distributor_inventory.find_one(
                {"distributor_id": order["distributor_id"], "product_id": it["product_id"]}
            )
            if existing:
                await db.dms_distributor_inventory.update_one(
                    {"id": existing["id"]},
                    {"$set": {
                        "qty_boxes": int(existing.get("qty_boxes", 0)) + q,
                        "cost_price": it["unit_price"],  # purchase cost
                        "updated_at": _now(),
                    }},
                )
            else:
                await db.dms_distributor_inventory.insert_one({
                    "id": _nid("dinv"),
                    "distributor_id": order["distributor_id"],
                    "product_id": it["product_id"],
                    "qty_boxes": q,
                    "cost_price": it["unit_price"],
                    "updated_at": _now(),
                })
            await db.dms_stock_ledger.insert_one({
                "id": _nid("sl"),
                "scope": "distributor",
                "distributor_id": order["distributor_id"],
                "product_id": it["product_id"],
                "delta_boxes": q,
                "reason": "primary_receive",
                "reference": order["order_no"],
                "at": _now(),
            })
        await db.dms_primary_orders.update_one(
            {"id": oid}, {"$set": {"status": "received", "received_at": _now(), "updated_at": _now()}}
        )
        # notify owner
        async for u in db.users.find({"role": {"$in": ["owner", "owner_accountant"]}}, {"_id": 0, "id": 1}):
            await notify(
                u["id"], "order_received",
                f"{order['distributor_name']} received {order['order_no']}",
                f"Received on {datetime.now().strftime('%d-%b-%y')}",
                f"/dms/owner/primary-orders/{oid}",
            )
        return {"ok": True, "status": "received"}

    # =========================================================================
    # E-BILL ATTACHMENTS (owner accountant uploads invoice image / doc URL)
    # =========================================================================
    @router.post("/attachments")
    async def add_attachment(body: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        """Simple attachment: {reference_id, kind, name, url}."""
        if not body.get("reference_id") or not body.get("url"):
            raise HTTPException(status_code=400, detail="reference_id + url required")
        doc = {
            "id": _nid("att"),
            "reference_id": body["reference_id"],
            "kind": body.get("kind", "invoice"),
            "name": body.get("name", "Attachment"),
            "url": body["url"],
            "uploaded_by": user["id"],
            "uploader_role": user["role"],
            "created_at": _now(),
        }
        await db.dms_attachments.insert_one(doc)
        return _clean(doc)

    @router.get("/attachments")
    async def list_attachments(reference_id: str, user: dict = Depends(get_current_user)):
        docs = await db.dms_attachments.find({"reference_id": reference_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
        return {"data": docs}

    # =========================================================================
    # PRIMARY LEDGER (owner ↔ distributor)
    # =========================================================================
    @router.get("/ledger/primary")
    async def primary_ledger(distributor_id: Optional[str] = None, user: dict = Depends(get_current_user)):
        role = user.get("role")
        q: Dict[str, Any] = {}
        # distributor scope
        if role in ("distributor", "distributor_accountant"):
            q["distributor_id"] = user.get("distributor_id")
        elif distributor_id:
            q["distributor_id"] = distributor_id
        entries = await db.dms_primary_ledger.find(q, {"_id": 0}).sort("at", -1).to_list(1000)
        # summary per distributor
        summary: Dict[str, Dict[str, Any]] = {}
        for e in entries:
            did = e["distributor_id"]
            s = summary.setdefault(did, {"distributor_id": did, "billed": 0.0, "paid": 0.0, "outstanding": 0.0})
            if e["kind"] == "invoice":
                s["billed"] += e["amount"]
                s["outstanding"] += e["amount"]
            elif e["kind"] in ("payment", "coupon_credit"):
                s["paid"] += e["amount"]
                s["outstanding"] -= e["amount"]
        # enrich with dist names
        dids = list(summary.keys())
        dnames = {d["id"]: d["name"] async for d in db.dms_distributors.find({"id": {"$in": dids}}, {"_id": 0, "id": 1, "name": 1})}
        for s in summary.values():
            s["distributor_name"] = dnames.get(s["distributor_id"], "")
            for k in ("billed", "paid", "outstanding"):
                s[k] = _round(s[k])
        return {"entries": entries, "summary": sorted(summary.values(), key=lambda x: -x["outstanding"])}

    @router.post("/ledger/primary/payment")
    async def record_primary_payment(body: Dict[str, Any] = Body(...), user: dict = Depends(owner_or_accountant)):
        did = body.get("distributor_id")
        amt = _round(body.get("amount", 0))
        if not did or amt <= 0:
            raise HTTPException(status_code=400, detail="distributor_id + amount>0 required")
        entry = {
            "id": _nid("le"),
            "distributor_id": did,
            "kind": "payment",
            "reference_no": body.get("reference_no", f"PMT-{datetime.now().strftime('%y%m%d%H%M%S')}"),
            "amount": amt,
            "method": body.get("method", "bank_transfer"),
            "description": body.get("description", "Payment received"),
            "at": _now(),
            "recorded_by": user["id"],
        }
        await db.dms_primary_ledger.insert_one(entry)
        return _clean(entry)

    # =========================================================================
    # DASHBOARDS
    # =========================================================================
    @router.get("/dashboard/owner")
    async def owner_dashboard(user: dict = Depends(owner_or_accountant)):
        n_dist = await db.dms_distributors.count_documents({"active": True})
        n_products = await db.dms_products.count_documents({"active": True})
        n_pending = await db.dms_primary_orders.count_documents({"status": {"$in": ["pending", "partially_fulfilled"]}})
        n_ready = await db.dms_primary_orders.count_documents({"status": "ready_to_go"})
        # revenue mtd = sum of e-bill total
        mtd_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        revenue = 0.0
        async for eb in db.dms_ebills.find({"created_at": {"$gte": mtd_start}}, {"_id": 0, "total": 1}):
            revenue += eb.get("total", 0)
        # outstanding = sum(invoices) - sum(payments)
        billed = 0.0
        paid = 0.0
        async for e in db.dms_primary_ledger.find({}, {"_id": 0, "kind": 1, "amount": 1}):
            if e["kind"] == "invoice":
                billed += e["amount"]
            elif e["kind"] in ("payment", "coupon_credit"):
                paid += e["amount"]
        # owner inventory value
        inv_value = 0.0
        async for r in db.dms_owner_inventory.find({}, {"_id": 0}):
            p = await db.dms_products.find_one({"id": r["product_id"]}, {"_id": 0, "unit_price": 1})
            if p:
                inv_value += (r.get("qty_boxes", 0) or 0) * (p.get("unit_price", 0) or 0)
        return {
            "kpis": {
                "distributors": n_dist,
                "products": n_products,
                "pending_orders": n_pending,
                "ready_to_go": n_ready,
                "revenue_mtd": _round(revenue),
                "outstanding_receivable": _round(billed - paid),
                "inventory_value": _round(inv_value),
            }
        }

    @router.get("/dashboard/distributor")
    async def distributor_dashboard(user: dict = Depends(dist_or_dacct)):
        did = user.get("distributor_id")
        if not did:
            raise HTTPException(status_code=400, detail="Not linked to a distributor")
        # current stock (value at cost)
        stock_qty = 0
        stock_value = 0.0
        async for r in db.dms_distributor_inventory.find({"distributor_id": did}, {"_id": 0}):
            q = r.get("qty_boxes", 0) or 0
            cp = r.get("cost_price", 0) or 0
            stock_qty += q
            stock_value += q * cp
        # payable to owner = primary outstanding
        billed = 0.0
        paid = 0.0
        async for e in db.dms_primary_ledger.find({"distributor_id": did}, {"_id": 0}):
            if e["kind"] == "invoice":
                billed += e["amount"]
            elif e["kind"] in ("payment", "coupon_credit"):
                paid += e["amount"]
        payable = _round(billed - paid)
        # pending orders
        pend = await db.dms_primary_orders.count_documents({"distributor_id": did, "status": {"$in": ["pending", "partially_fulfilled"]}})
        ready = await db.dms_primary_orders.count_documents({"distributor_id": did, "status": "ready_to_go"})
        return {
            "kpis": {
                "stock_boxes": stock_qty,
                "stock_value": _round(stock_value),
                "payable_to_owner": payable,
                "pending_primary_orders": pend,
                "ready_to_receive": ready,
                # secondary sales — iteration 2
                "receivable_from_retailers": 0,
                "sales_mtd": 0,
                "revenue_mtd": 0,
            }
        }

    # =========================================================================
    # ME endpoint — enriched with distributor info if applicable
    # =========================================================================
    @router.get("/me")
    async def me(user: dict = Depends(get_current_user)):
        out = dict(user)
        if user.get("distributor_id"):
            d = await db.dms_distributors.find_one({"id": user["distributor_id"]}, {"_id": 0})
            out["distributor"] = d
        if user.get("retailer_id"):
            r = await db.dms_retailers.find_one({"id": user["retailer_id"]}, {"_id": 0})
            out["retailer"] = r
        return out

    # =========================================================================
    # ITERATION 2 — SECONDARY SALES (Distributor ↔ Retailer)
    # =========================================================================

    async def _resolve_visible_products_for_retailer(distributor_id: str, retailer_id: str) -> List[Dict[str, Any]]:
        """Return products distributor has NOT hidden for this retailer AND has stock for."""
        hidden = set()
        async for v in db.dms_ret_visibility.find({"distributor_id": distributor_id, "retailer_id": retailer_id, "visible": False}, {"_id": 0}):
            hidden.add(v["product_id"])
        # only include products distributor has stock in
        prods = []
        async for inv in db.dms_distributor_inventory.find({"distributor_id": distributor_id}, {"_id": 0}):
            if inv["product_id"] in hidden:
                continue
            if int(inv.get("qty_boxes", 0)) <= 0:
                continue
            p = await db.dms_products.find_one({"id": inv["product_id"]}, {"_id": 0})
            if not p or not p.get("active"):
                continue
            # distributor's SP = cost + margin (we allow override in retailer_price)
            sp_map = await db.dms_retailer_prices.find_one({"distributor_id": distributor_id, "product_id": p["id"]}, {"_id": 0})
            selling_price = _round(sp_map["selling_price"]) if sp_map else _round(inv.get("cost_price", p["unit_price"]) * 1.15)
            prods.append({
                **p,
                "distributor_stock_boxes": int(inv["qty_boxes"]),
                "selling_price": selling_price,
                "cost_price": inv.get("cost_price", p["unit_price"]),
            })
        return prods

    async def _get_retailer_selling_mode(distributor_id: str, retailer_id: str) -> str:
        doc = await db.dms_ret_mode.find_one({"distributor_id": distributor_id, "retailer_id": retailer_id}, {"_id": 0})
        return doc.get("mode", "box") if doc else "box"

    # ── retailer prices (distributor's selling price to retailers, configurable by owner/TL) ──
    @router.get("/distributors/{did}/retailer-prices")
    async def get_retailer_prices(did: str, user: dict = Depends(get_current_user)):
        role = user.get("role")
        if role not in ("owner", "super_admin", "team_leader", "distributor") or (role == "distributor" and user.get("distributor_id") != did):
            raise HTTPException(status_code=403, detail="Forbidden")
        products = await db.dms_products.find({"active": True}, {"_id": 0}).sort("name", 1).to_list(1000)
        price_map = {p["product_id"]: p["selling_price"] async for p in db.dms_retailer_prices.find({"distributor_id": did}, {"_id": 0})}
        # get purchase price from distributor inventory
        inv_map = {i["product_id"]: i.get("cost_price", 0) async for i in db.dms_distributor_inventory.find({"distributor_id": did}, {"_id": 0})}
        out = []
        for p in products:
            cp = inv_map.get(p["id"], p["unit_price"])
            out.append({
                "product_id": p["id"],
                "product_name": p["name"],
                "sku_code": p["sku_code"],
                "cost_price": _round(cp),
                "selling_price": price_map.get(p["id"], _round(cp * 1.15)),
            })
        return {"data": out}

    @router.put("/distributors/{did}/retailer-prices")
    async def set_retailer_price(did: str, body: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        role = user.get("role")
        # Owner or Team Leader can set; distributor cannot set their own selling price (per doc)
        if role not in ("owner", "super_admin", "team_leader"):
            raise HTTPException(status_code=403, detail="Only owner or team leader can set selling prices")
        pid = body.get("product_id"); sp = _round(body.get("selling_price", 0))
        if not pid or sp <= 0:
            raise HTTPException(status_code=400, detail="product_id + selling_price>0 required")
        await db.dms_retailer_prices.update_one(
            {"distributor_id": did, "product_id": pid},
            {"$set": {"distributor_id": did, "product_id": pid, "selling_price": sp, "updated_at": _now(), "updated_by": user["id"]}},
            upsert=True,
        )
        return {"ok": True}

    # ── retailers ──
    async def _get_dist_id_for_user(user: dict) -> Optional[str]:
        role = user.get("role")
        if role == "distributor":
            return user.get("distributor_id")
        if role == "distributor_accountant":
            return user.get("distributor_id")
        if role == "salesperson":
            # returns first assigned distributor
            a = await db.dms_sp_assignments.find_one({"salesperson_id": user["id"]}, {"_id": 0})
            return a.get("distributor_id") if a else None
        return None

    @router.get("/retailers")
    async def list_retailers(distributor_id: Optional[str] = None, user: dict = Depends(get_current_user)):
        role = user.get("role")
        q: Dict[str, Any] = {"active": True}
        if role == "retailer":
            q["id"] = user.get("retailer_id")
        elif role in ("distributor", "distributor_accountant"):
            q["distributor_id"] = user.get("distributor_id")
        elif role == "salesperson":
            # retailers under my assigned distributors
            assigns = await db.dms_sp_assignments.find({"salesperson_id": user["id"]}, {"_id": 0}).to_list(500)
            dids = [a["distributor_id"] for a in assigns]
            q["distributor_id"] = {"$in": dids} if dids else "__none__"
        elif distributor_id:
            q["distributor_id"] = distributor_id
        docs = await db.dms_retailers.find(q, {"_id": 0}).sort("name", 1).to_list(1000)
        return {"data": docs, "count": len(docs)}

    @router.post("/retailers")
    async def create_retailer(body: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        role = user.get("role")
        if role not in ("distributor", "salesperson", "owner", "super_admin"):
            raise HTTPException(status_code=403, detail="Forbidden")
        did = body.get("distributor_id") or await _get_dist_id_for_user(user)
        if not did:
            raise HTTPException(status_code=400, detail="distributor_id required")
        required = ["name", "phone", "address"]
        for k in required:
            if not body.get(k):
                raise HTTPException(status_code=400, detail=f"{k} required")
        rid = _nid("ret")
        # user login (optional)
        ruser_id = None
        if body.get("email"):
            try:
                ruser_id = await _create_dms_user(
                    email=body["email"],
                    password=body.get("password") or "Demo@2026",
                    name=body["name"],
                    role="retailer",
                    extra={"retailer_id": rid, "distributor_id": did, "phone": body["phone"]},
                )
            except HTTPException:
                # email already exists — link to existing user if it's a retailer
                existing = await db.users.find_one({"email": body["email"].lower()})
                if existing and existing.get("role") == "retailer":
                    ruser_id = existing["id"]
                    await db.users.update_one({"id": existing["id"]}, {"$set": {"retailer_id": rid, "distributor_id": did}})
                else:
                    raise
        doc = {
            "id": rid,
            "name": body["name"],
            "phone": body["phone"],
            "email": (body.get("email") or "").lower(),
            "address": body["address"],
            "region": body.get("region", ""),
            "gps_lat": body.get("gps_lat"),
            "gps_lng": body.get("gps_lng"),
            "location_link": body.get("location_link", ""),
            "distributor_id": did,
            "onboarded_by": user["id"],
            "onboarded_by_role": user["role"],
            "user_id": ruser_id,
            "kyc": {
                "gstin": body.get("gstin", ""),
                "shop_license": body.get("shop_license", ""),
                "notes": body.get("kyc_notes", ""),
            },
            "documents": body.get("documents", []),
            "credit_limit": _round(body.get("credit_limit", 0)),
            "active": True,
            "created_at": _now(),
        }
        await db.dms_retailers.insert_one(doc)
        return _clean(doc)

    @router.get("/retailers/{rid}")
    async def get_retailer(rid: str, user: dict = Depends(get_current_user)):
        doc = await db.dms_retailers.find_one({"id": rid}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Retailer not found")
        return doc

    @router.put("/retailers/{rid}")
    async def update_retailer(rid: str, body: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        upd: Dict[str, Any] = {}
        for k in ["name", "phone", "address", "region", "gps_lat", "gps_lng", "location_link", "credit_limit", "active", "documents"]:
            if k in body:
                upd[k] = body[k]
        if "kyc" in body:
            upd["kyc"] = body["kyc"]
        upd["updated_at"] = _now()
        r = await db.dms_retailers.update_one({"id": rid}, {"$set": upd})
        if r.matched_count == 0:
            raise HTTPException(status_code=404, detail="Retailer not found")
        return {"ok": True}

    # ── retailer visibility (distributor controls) ──
    @router.get("/retailers/{rid}/visibility")
    async def get_ret_visibility(rid: str, user: dict = Depends(get_current_user)):
        retailer = await db.dms_retailers.find_one({"id": rid}, {"_id": 0})
        if not retailer:
            raise HTTPException(status_code=404, detail="Retailer not found")
        did = retailer["distributor_id"]
        # only distributor/dist_acct/owner can view
        if user["role"] not in ("owner", "super_admin", "team_leader") and user.get("distributor_id") != did:
            raise HTTPException(status_code=403, detail="Forbidden")
        products = await db.dms_products.find({"active": True}, {"_id": 0}).sort("name", 1).to_list(1000)
        vis_map = {v["product_id"]: v.get("visible", True) async for v in db.dms_ret_visibility.find({"distributor_id": did, "retailer_id": rid}, {"_id": 0})}
        out = []
        for p in products:
            out.append({
                "product_id": p["id"],
                "product_name": p["name"],
                "sku_code": p["sku_code"],
                "visible": vis_map.get(p["id"], True),
            })
        return {"data": out}

    @router.put("/retailers/{rid}/visibility")
    async def set_ret_visibility(rid: str, body: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        retailer = await db.dms_retailers.find_one({"id": rid}, {"_id": 0})
        if not retailer:
            raise HTTPException(status_code=404, detail="Retailer not found")
        did = retailer["distributor_id"]
        if user["role"] not in ("owner", "super_admin") and user.get("distributor_id") != did:
            raise HTTPException(status_code=403, detail="Forbidden")
        pid = body.get("product_id"); visible = bool(body.get("visible", True))
        if not pid:
            raise HTTPException(status_code=400, detail="product_id required")
        await db.dms_ret_visibility.update_one(
            {"distributor_id": did, "retailer_id": rid, "product_id": pid},
            {"$set": {"distributor_id": did, "retailer_id": rid, "product_id": pid, "visible": visible, "updated_at": _now()}},
            upsert=True,
        )
        return {"ok": True}

    # ── retailer selling mode ──
    @router.get("/retailers/{rid}/selling-mode")
    async def get_ret_mode(rid: str, user: dict = Depends(get_current_user)):
        retailer = await db.dms_retailers.find_one({"id": rid}, {"_id": 0})
        if not retailer:
            raise HTTPException(status_code=404, detail="Retailer not found")
        did = retailer["distributor_id"]
        mode = await _get_retailer_selling_mode(did, rid)
        return {"mode": mode}

    @router.put("/retailers/{rid}/selling-mode")
    async def set_ret_mode(rid: str, body: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        retailer = await db.dms_retailers.find_one({"id": rid}, {"_id": 0})
        if not retailer:
            raise HTTPException(status_code=404, detail="Retailer not found")
        did = retailer["distributor_id"]
        if user["role"] not in ("owner", "super_admin") and user.get("distributor_id") != did:
            raise HTTPException(status_code=403, detail="Forbidden")
        mode = body.get("mode", "box")
        if mode not in ("box", "box_pcs"):
            raise HTTPException(status_code=400, detail="mode must be 'box' or 'box_pcs'")
        await db.dms_ret_mode.update_one(
            {"distributor_id": did, "retailer_id": rid},
            {"$set": {"distributor_id": did, "retailer_id": rid, "mode": mode, "updated_at": _now()}},
            upsert=True,
        )
        return {"ok": True, "mode": mode}

    # ── retailer browse ──
    @router.get("/retailer/browse")
    async def retailer_browse(retailer_id: Optional[str] = None, user: dict = Depends(get_current_user)):
        # retailer sees their own; salesperson may pass retailer_id explicitly
        role = user.get("role")
        rid = retailer_id or user.get("retailer_id")
        if not rid:
            raise HTTPException(status_code=400, detail="retailer_id required")
        retailer = await db.dms_retailers.find_one({"id": rid}, {"_id": 0})
        if not retailer:
            raise HTTPException(status_code=404, detail="Retailer not found")
        # access check
        if role == "retailer" and user.get("retailer_id") != rid:
            raise HTTPException(status_code=403, detail="Forbidden")
        did = retailer["distributor_id"]
        products = await _resolve_visible_products_for_retailer(did, rid)
        cats = {c["id"]: c["name"] async for c in db.dms_categories.find({}, {"_id": 0, "id": 1, "name": 1})}
        for p in products:
            p["category_name"] = cats.get(p.get("category_id"), "")
        mode = await _get_retailer_selling_mode(did, rid)
        # pending qty for this retailer
        pending = []
        async for pd in db.dms_retailer_pending.find({"retailer_id": rid, "distributor_id": did}, {"_id": 0}):
            if int(pd.get("pending_qty_boxes", 0)) > 0 or int(pd.get("pending_qty_pcs", 0)) > 0:
                pending.append(pd)
        return {"data": products, "mode": mode, "retailer": retailer, "pending": pending}

    # ── secondary orders ──
    @router.post("/secondary-orders")
    async def place_secondary_order(body: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        role = user.get("role")
        if role not in ("retailer", "salesperson", "distributor", "owner", "super_admin"):
            raise HTTPException(status_code=403, detail="Forbidden")
        rid = body.get("retailer_id") or user.get("retailer_id")
        if not rid:
            raise HTTPException(status_code=400, detail="retailer_id required")
        retailer = await db.dms_retailers.find_one({"id": rid}, {"_id": 0})
        if not retailer:
            raise HTTPException(status_code=404, detail="Retailer not found")
        if role == "retailer" and user.get("retailer_id") != rid:
            raise HTTPException(status_code=403, detail="Forbidden")
        did = retailer["distributor_id"]
        items = body.get("items") or []
        include_pending = bool(body.get("include_pending", False))
        if not items and not include_pending:
            raise HTTPException(status_code=400, detail="items[] required")
        mode = await _get_retailer_selling_mode(did, rid)
        # merge with pending if include_pending
        pending_add: Dict[str, Dict[str, Any]] = {}
        if include_pending:
            async for pd in db.dms_retailer_pending.find({"retailer_id": rid, "distributor_id": did}, {"_id": 0}):
                if int(pd.get("pending_qty_boxes", 0)) > 0 or int(pd.get("pending_qty_pcs", 0)) > 0:
                    pending_add[pd["product_id"]] = pd

        order_items = []
        subtotal = 0.0
        gst_total = 0.0
        # global GST% from settings
        _s = await db.dms_settings.find_one({"id": "global"}, {"_id": 0}) or {}
        global_gst = float(_s.get("gst_pct") or 0)
        for it in items:
            pid = it.get("product_id")
            qty_boxes = int(it.get("qty_boxes", 0))
            qty_pcs = int(it.get("qty_pcs", 0)) if mode == "box_pcs" else 0
            if not pid or (qty_boxes == 0 and qty_pcs == 0):
                continue
            p = await db.dms_products.find_one({"id": pid}, {"_id": 0})
            if not p:
                continue
            sp_map = await db.dms_retailer_prices.find_one({"distributor_id": did, "product_id": pid}, {"_id": 0})
            box_price = _round(sp_map["selling_price"]) if sp_map else _round(p["unit_price"] * 1.15)
            pcs_price = _round(box_price / max(p["box_qty"], 1))
            # add pending
            pend = pending_add.pop(pid, None)
            if pend:
                qty_boxes += int(pend.get("pending_qty_boxes", 0))
                qty_pcs += int(pend.get("pending_qty_pcs", 0))
            line_sub = _round(box_price * qty_boxes + pcs_price * qty_pcs)
            line_gst = _round(line_sub * (global_gst / 100.0))
            subtotal += line_sub; gst_total += line_gst
            order_items.append({
                "product_id": pid,
                "product_name": p["name"],
                "sku_code": p["sku_code"],
                "box_qty": p["box_qty"],
                "box_price": box_price,
                "pcs_price": pcs_price,
                "gst_pct": global_gst,
                "qty_boxes_ordered": qty_boxes,
                "qty_pcs_ordered": qty_pcs,
                "qty_boxes_dispatched": 0,
                "qty_pcs_dispatched": 0,
                "line_subtotal": line_sub,
                "line_gst": line_gst,
                "line_total": _round(line_sub + line_gst),
                "carried_pending": bool(pend),
            })
        # any remaining pending items also included?
        for pid, pend in pending_add.items():
            p = await db.dms_products.find_one({"id": pid}, {"_id": 0})
            if not p:
                continue
            sp_map = await db.dms_retailer_prices.find_one({"distributor_id": did, "product_id": pid}, {"_id": 0})
            box_price = _round(sp_map["selling_price"]) if sp_map else _round(p["unit_price"] * 1.15)
            pcs_price = _round(box_price / max(p["box_qty"], 1))
            qb = int(pend.get("pending_qty_boxes", 0)); qp = int(pend.get("pending_qty_pcs", 0))
            line_sub = _round(box_price * qb + pcs_price * qp)
            line_gst = _round(line_sub * (global_gst / 100.0))
            subtotal += line_sub; gst_total += line_gst
            order_items.append({
                "product_id": pid, "product_name": p["name"], "sku_code": p["sku_code"],
                "box_qty": p["box_qty"], "box_price": box_price, "pcs_price": pcs_price,
                "gst_pct": global_gst, "qty_boxes_ordered": qb, "qty_pcs_ordered": qp,
                "qty_boxes_dispatched": 0, "qty_pcs_dispatched": 0,
                "line_subtotal": line_sub, "line_gst": line_gst, "line_total": _round(line_sub + line_gst),
                "carried_pending": True,
            })

        if not order_items:
            raise HTTPException(status_code=400, detail="No valid items")
        total = _round(subtotal + gst_total)
        order = {
            "id": _nid("so"),
            "order_no": f"SO-{datetime.now().strftime('%y%m%d%H%M%S')}",
            "retailer_id": rid,
            "retailer_name": retailer["name"],
            "distributor_id": did,
            "mode": mode,
            "items": order_items,
            "subtotal": _round(subtotal),
            "gst_total": _round(gst_total),
            "total": total,
            "status": "pending",
            "fulfillment_pct": 0,
            "notes": body.get("notes", ""),
            "placed_by": user["id"],
            "placed_by_role": user["role"],
            "created_at": _now(),
        }
        await db.dms_secondary_orders.insert_one(order)
        # if pending was included, mark those pending records consumed
        if include_pending:
            await db.dms_retailer_pending.update_many(
                {"retailer_id": rid, "distributor_id": did},
                {"$set": {"pending_qty_boxes": 0, "pending_qty_pcs": 0, "consumed_at": _now(), "consumed_by_order": order["id"]}},
            )
        # notify distributor + dist accountant
        async for u in db.users.find({"distributor_id": did, "role": {"$in": ["distributor", "distributor_accountant"]}}, {"_id": 0, "id": 1}):
            await notify(u["id"], "secondary_order", f"New order from {retailer['name']}",
                         f"{order['order_no']} — {len(order_items)} items — \u20b9{total:,.0f}",
                         f"/dms/distributor/retail-orders/{order['id']}")
        return _clean(order)

    @router.get("/secondary-orders")
    async def list_secondary_orders(status: Optional[str] = None, user: dict = Depends(get_current_user)):
        role = user.get("role")
        q: Dict[str, Any] = {}
        if status:
            q["status"] = status
        if role == "retailer":
            q["retailer_id"] = user.get("retailer_id")
        elif role in ("distributor", "distributor_accountant"):
            q["distributor_id"] = user.get("distributor_id")
        elif role == "salesperson":
            # BUG FIX (Phase 1): SP should see orders they placed AND orders under their assigned distributors
            assigns = await db.dms_sp_assignments.find({"salesperson_id": user["id"]}, {"_id": 0}).to_list(500)
            dids = [a["distributor_id"] for a in assigns]
            or_clauses = [{"placed_by": user["id"]}]
            if dids:
                or_clauses.append({"distributor_id": {"$in": dids}})
            q["$or"] = or_clauses
        docs = await db.dms_secondary_orders.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
        # Enrich with placed_by user name and distributor name for UI convenience
        placed_ids = list({d.get("placed_by") for d in docs if d.get("placed_by")})
        placed_map = {}
        if placed_ids:
            async for u in db.users.find({"id": {"$in": placed_ids}}, {"_id": 0, "id": 1, "name": 1, "role": 1}):
                placed_map[u["id"]] = {"name": u.get("name"), "role": u.get("role")}
        dist_ids = list({d.get("distributor_id") for d in docs if d.get("distributor_id")})
        dist_map = {}
        if dist_ids:
            async for dd in db.dms_distributors.find({"id": {"$in": dist_ids}}, {"_id": 0, "id": 1, "name": 1}):
                dist_map[dd["id"]] = dd.get("name")
        for d in docs:
            pb = placed_map.get(d.get("placed_by"))
            d["placed_by_name"] = pb.get("name") if pb else None
            d["distributor_name"] = d.get("distributor_name") or dist_map.get(d.get("distributor_id"))
        return {"data": docs, "count": len(docs)}

    @router.get("/secondary-orders/{oid}")
    async def get_secondary_order(oid: str, user: dict = Depends(get_current_user)):
        doc = await db.dms_secondary_orders.find_one({"id": oid}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Order not found")
        role = user.get("role")
        if role == "retailer" and doc["retailer_id"] != user.get("retailer_id"):
            raise HTTPException(status_code=403, detail="Forbidden")
        if role in ("distributor", "distributor_accountant") and doc["distributor_id"] != user.get("distributor_id"):
            raise HTTPException(status_code=403, detail="Forbidden")
        atts = await db.dms_attachments.find({"reference_id": oid}, {"_id": 0}).to_list(50)
        doc["attachments"] = atts
        # enrich retailer & distributor names
        r = await db.dms_retailers.find_one({"id": doc["retailer_id"]}, {"_id": 0, "name": 1, "phone": 1, "address": 1})
        doc["retailer"] = r
        d = await db.dms_distributors.find_one({"id": doc["distributor_id"]}, {"_id": 0, "name": 1, "phone": 1, "address": 1, "kyc": 1})
        doc["distributor"] = d
        # Phase 1: enrich placed_by user info for TL Order Monitoring detail
        if doc.get("placed_by"):
            pu = await db.users.find_one({"id": doc["placed_by"]}, {"_id": 0, "id": 1, "name": 1, "role": 1, "phone": 1})
            if pu:
                doc["placed_by_user"] = pu
                doc["placed_by_name"] = pu.get("name")
        return doc

    @router.post("/secondary-orders/{oid}/dispatch")
    async def dispatch_secondary(oid: str, body: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        """Body: {items: [{product_id, qty_boxes_dispatched, qty_pcs_dispatched}], complete: bool}"""
        role = user.get("role")
        if role not in ("distributor", "owner", "super_admin"):
            raise HTTPException(status_code=403, detail="Forbidden")
        order = await db.dms_secondary_orders.find_one({"id": oid}, {"_id": 0})
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if role == "distributor" and user.get("distributor_id") != order["distributor_id"]:
            raise HTTPException(status_code=403, detail="Forbidden")
        if order["status"] in ("dispatched", "completed"):
            raise HTTPException(status_code=400, detail="Already dispatched")
        did = order["distributor_id"]; rid = order["retailer_id"]
        items = body.get("items") or []
        item_map = {it["product_id"]: it for it in items}
        # apply
        billed_items = []
        subtotal = 0.0
        gst_total = 0.0
        for it in order["items"]:
            di = item_map.get(it["product_id"], {})
            db_qty = int(di.get("qty_boxes_dispatched", 0))
            dp_qty = int(di.get("qty_pcs_dispatched", 0)) if order["mode"] == "box_pcs" else 0
            db_qty = min(db_qty, it["qty_boxes_ordered"])
            dp_qty = min(dp_qty, it["qty_pcs_ordered"])
            it["qty_boxes_dispatched"] = db_qty
            it["qty_pcs_dispatched"] = dp_qty
            # decrement distributor inventory
            total_pcs = db_qty * it["box_qty"] + dp_qty
            if total_pcs > 0:
                inv = await db.dms_distributor_inventory.find_one({"distributor_id": did, "product_id": it["product_id"]})
                if inv:
                    boxes_to_deduct = db_qty + (dp_qty // max(it["box_qty"], 1))
                    remaining_pcs = dp_qty % max(it["box_qty"], 1)
                    # Simplified: deduct boxes; treat pcs as fractional; for simplicity we deduct ceil
                    new_qty = max(0, int(inv.get("qty_boxes", 0)) - db_qty - (1 if remaining_pcs > 0 else 0))
                    await db.dms_distributor_inventory.update_one({"id": inv["id"]}, {"$set": {"qty_boxes": new_qty, "updated_at": _now()}})
                    await db.dms_stock_ledger.insert_one({
                        "id": _nid("sl"), "scope": "distributor", "distributor_id": did,
                        "product_id": it["product_id"], "delta_boxes": -(db_qty + (1 if remaining_pcs > 0 else 0)),
                        "reason": "secondary_dispatch", "reference": order["order_no"], "at": _now(),
                    })
            line_sub = _round(it["box_price"] * db_qty + it["pcs_price"] * dp_qty)
            line_gst = _round(line_sub * (it["gst_pct"] / 100.0))
            subtotal += line_sub; gst_total += line_gst
            billed_items.append({
                **it,
                "dispatched_qty_boxes": db_qty,
                "dispatched_qty_pcs": dp_qty,
                "line_subtotal": line_sub, "line_gst": line_gst, "line_total": _round(line_sub + line_gst),
            })
            # pending qty
            pending_boxes = it["qty_boxes_ordered"] - db_qty
            pending_pcs = it["qty_pcs_ordered"] - dp_qty
            if pending_boxes > 0 or pending_pcs > 0:
                await db.dms_retailer_pending.update_one(
                    {"retailer_id": rid, "distributor_id": did, "product_id": it["product_id"]},
                    {"$set": {
                        "retailer_id": rid, "distributor_id": did, "product_id": it["product_id"],
                        "pending_qty_boxes": pending_boxes, "pending_qty_pcs": pending_pcs,
                        "product_name": it["product_name"], "sku_code": it["sku_code"],
                        "updated_at": _now(),
                    }},
                    upsert=True,
                )
        # bill
        total = _round(subtotal + gst_total)
        bill = {
            "id": _nid("rb"), "bill_no": f"RB-{datetime.now().strftime('%y%m%d%H%M%S')}",
            "order_id": oid, "order_no": order["order_no"],
            "retailer_id": rid, "distributor_id": did,
            "items": billed_items, "subtotal": _round(subtotal), "gst_total": _round(gst_total), "total": total,
            "status": "issued", "created_at": _now(),
        }
        await db.dms_retailer_bills.insert_one(bill)
        await db.dms_retailer_ledger.insert_one({
            "id": _nid("rle"),
            "distributor_id": did, "retailer_id": rid,
            "kind": "invoice", "reference_id": bill["id"], "reference_no": bill["bill_no"],
            "amount": total, "description": f"Bill for {order['order_no']}", "at": _now(),
        })
        # compute fulfillment
        ord_total_pcs = sum(it["qty_boxes_ordered"] * it["box_qty"] + it["qty_pcs_ordered"] for it in order["items"])
        disp_total_pcs = sum(it["qty_boxes_dispatched"] * it["box_qty"] + it["qty_pcs_dispatched"] for it in order["items"])
        pct = int(round((disp_total_pcs / ord_total_pcs) * 100)) if ord_total_pcs > 0 else 0
        new_status = "dispatched"
        await db.dms_secondary_orders.update_one(
            {"id": oid},
            {"$set": {"items": order["items"], "fulfillment_pct": pct, "status": new_status,
                      "bill_id": bill["id"], "dispatched_at": _now(), "updated_at": _now()}},
        )
        # notify retailer
        r_user = await db.users.find_one({"retailer_id": rid, "role": "retailer"}, {"_id": 0, "id": 1})
        if r_user:
            await notify(r_user["id"], "order_dispatched", f"Order {order['order_no']} dispatched",
                         f"Bill {bill['bill_no']} \u2022 \u20b9{total:,.0f}",
                         f"/dms/retailer/my-orders/{oid}")
        return {"ok": True, "bill_id": bill["id"], "fulfillment_pct": pct, "status": new_status}

    # ── Cancel / Edit secondary order (Phase 1 additions) ──
    @router.post("/secondary-orders/{oid}/cancel")
    async def cancel_secondary_order(oid: str, body: Dict[str, Any] = Body(default={}), user: dict = Depends(get_current_user)):
        """Cancel a pending secondary (retailer) order. Allowed: TL (assigned distributor), SP (own placed_by), Owner, Super Admin, Distributor (own)."""
        role = user.get("role")
        order = await db.dms_secondary_orders.find_one({"id": oid}, {"_id": 0})
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.get("status") in ("dispatched", "delivered", "completed", "cancelled"):
            raise HTTPException(status_code=400, detail=f"Cannot cancel — order is {order.get('status')}")
        # Phase 2A: FY lock check
        await _check_fy_lock(order.get("created_at"), "order")

        # RBAC
        allowed = False
        if role in ("owner", "super_admin"):
            allowed = True
        elif role in ("distributor", "distributor_accountant") and user.get("distributor_id") == order.get("distributor_id"):
            allowed = True
        elif role == "team_leader":
            tl_dists = [a["distributor_id"] async for a in db.dms_tl_assignments.find({"team_leader_id": user["id"]}, {"_id": 0, "distributor_id": 1})]
            if order.get("distributor_id") in tl_dists:
                allowed = True
        elif role == "salesperson":
            if order.get("placed_by") == user["id"]:
                allowed = True
        if not allowed:
            raise HTTPException(status_code=403, detail="Forbidden")

        reason = str(body.get("reason") or "").strip() or "Cancelled"
        await db.dms_secondary_orders.update_one(
            {"id": oid},
            {"$set": {
                "status": "cancelled",
                "cancelled_at": _now(),
                "cancelled_by": user["id"],
                "cancelled_by_role": role,
                "cancel_reason": reason,
                "updated_at": _now(),
            }},
        )
        # notify distributor
        async for u in db.users.find({"distributor_id": order["distributor_id"], "role": {"$in": ["distributor", "distributor_accountant"]}}, {"_id": 0, "id": 1}):
            await notify(u["id"], "order_cancelled", f"Order {order['order_no']} cancelled",
                         f"Reason: {reason}", f"/dms/distributor/retail-orders/{oid}")
        return {"ok": True, "status": "cancelled"}

    @router.put("/secondary-orders/{oid}")
    async def edit_secondary_order(oid: str, body: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        """Edit a pending secondary order's items. Allowed: SP who placed, TL (assigned dist), Owner/SuperAdmin, Distributor."""
        role = user.get("role")
        order = await db.dms_secondary_orders.find_one({"id": oid}, {"_id": 0})
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.get("status") != "pending":
            raise HTTPException(status_code=400, detail=f"Can only edit pending orders (current: {order.get('status')})")
        # Phase 2A: FY lock check
        await _check_fy_lock(order.get("created_at"), "order")

        # RBAC (same as cancel)
        allowed = False
        if role in ("owner", "super_admin"):
            allowed = True
        elif role in ("distributor", "distributor_accountant") and user.get("distributor_id") == order.get("distributor_id"):
            allowed = True
        elif role == "team_leader":
            tl_dists = [a["distributor_id"] async for a in db.dms_tl_assignments.find({"team_leader_id": user["id"]}, {"_id": 0, "distributor_id": 1})]
            if order.get("distributor_id") in tl_dists:
                allowed = True
        elif role == "salesperson" and order.get("placed_by") == user["id"]:
            allowed = True
        if not allowed:
            raise HTTPException(status_code=403, detail="Forbidden")

        did = order["distributor_id"]
        rid = order["retailer_id"]
        mode = order.get("mode", "box")
        items = body.get("items") or []
        if not items:
            raise HTTPException(status_code=400, detail="items[] required")
        _s = await db.dms_settings.find_one({"id": "global"}, {"_id": 0}) or {}
        global_gst = float(_s.get("gst_pct") or 0)
        new_items = []
        subtotal = 0.0
        gst_total = 0.0
        for it in items:
            pid = it.get("product_id")
            qty_boxes = int(it.get("qty_boxes", 0))
            qty_pcs = int(it.get("qty_pcs", 0)) if mode == "box_pcs" else 0
            # Phase 1: also honor qty_pcs even in box mode if explicitly sent (user asked Box + Nos always available)
            if mode != "box_pcs" and it.get("qty_pcs"):
                qty_pcs = int(it.get("qty_pcs", 0))
            if not pid or (qty_boxes == 0 and qty_pcs == 0):
                continue
            p = await db.dms_products.find_one({"id": pid}, {"_id": 0})
            if not p:
                continue
            sp_map = await db.dms_retailer_prices.find_one({"distributor_id": did, "product_id": pid}, {"_id": 0})
            box_price = _round(sp_map["selling_price"]) if sp_map else _round(p["unit_price"] * 1.15)
            pcs_price = _round(box_price / max(p["box_qty"], 1))
            line_sub = _round(box_price * qty_boxes + pcs_price * qty_pcs)
            line_gst = _round(line_sub * (global_gst / 100.0))
            subtotal += line_sub; gst_total += line_gst
            new_items.append({
                "product_id": pid, "product_name": p["name"], "sku_code": p["sku_code"],
                "box_qty": p["box_qty"], "box_price": box_price, "pcs_price": pcs_price,
                "gst_pct": global_gst, "qty_boxes_ordered": qty_boxes, "qty_pcs_ordered": qty_pcs,
                "qty_boxes_dispatched": 0, "qty_pcs_dispatched": 0,
                "line_subtotal": line_sub, "line_gst": line_gst, "line_total": _round(line_sub + line_gst),
                "carried_pending": False,
            })
        if not new_items:
            raise HTTPException(status_code=400, detail="No valid items")
        total = _round(subtotal + gst_total)
        await db.dms_secondary_orders.update_one(
            {"id": oid},
            {"$set": {
                "items": new_items,
                "subtotal": _round(subtotal), "gst_total": _round(gst_total), "total": total,
                "notes": body.get("notes", order.get("notes", "")),
                "edited_at": _now(),
                "edited_by": user["id"],
                "updated_at": _now(),
            }},
        )
        return {"ok": True, "id": oid, "total": total, "item_count": len(new_items)}

    # ── secondary ledger ──
    @router.get("/ledger/secondary")
    async def secondary_ledger(retailer_id: Optional[str] = None, user: dict = Depends(get_current_user)):
        role = user.get("role")
        q: Dict[str, Any] = {}
        if role == "retailer":
            q["retailer_id"] = user.get("retailer_id")
        elif role in ("distributor", "distributor_accountant"):
            q["distributor_id"] = user.get("distributor_id")
        if retailer_id and role not in ("retailer",):
            q["retailer_id"] = retailer_id
        entries = await db.dms_retailer_ledger.find(q, {"_id": 0}).sort("at", -1).to_list(2000)
        # summary per retailer
        summary: Dict[str, Dict[str, Any]] = {}
        for e in entries:
            rid = e["retailer_id"]
            s = summary.setdefault(rid, {"retailer_id": rid, "billed": 0.0, "paid": 0.0, "outstanding": 0.0})
            if e["kind"] == "invoice":
                s["billed"] += e["amount"]; s["outstanding"] += e["amount"]
            elif e["kind"] in ("payment", "coupon_credit"):
                s["paid"] += e["amount"]; s["outstanding"] -= e["amount"]
        rids = list(summary.keys())
        rnames = {r["id"]: r["name"] async for r in db.dms_retailers.find({"id": {"$in": rids}}, {"_id": 0, "id": 1, "name": 1})}
        for s in summary.values():
            s["retailer_name"] = rnames.get(s["retailer_id"], "")
            for k in ("billed", "paid", "outstanding"):
                s[k] = _round(s[k])
        return {"entries": entries, "summary": sorted(summary.values(), key=lambda x: -x["outstanding"])}

    @router.post("/ledger/secondary/payment")
    async def record_secondary_payment(body: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        role = user.get("role")
        # Phase 1: allow salesperson to record cash payment collected from retailer
        if role not in ("distributor", "distributor_accountant", "owner", "super_admin", "salesperson"):
            raise HTTPException(status_code=403, detail="Forbidden")
        rid = body.get("retailer_id")
        amt = _round(body.get("amount", 0))
        if not rid or amt <= 0:
            raise HTTPException(status_code=400, detail="retailer_id + amount>0 required")
        retailer = await db.dms_retailers.find_one({"id": rid}, {"_id": 0})
        if not retailer:
            raise HTTPException(status_code=404, detail="Retailer not found")
        # If SP: retailer must be under one of SP's assigned distributors
        if role == "salesperson":
            assigns = await db.dms_sp_assignments.find({"salesperson_id": user["id"]}, {"_id": 0, "distributor_id": 1}).to_list(500)
            dids = [a["distributor_id"] for a in assigns]
            if retailer.get("distributor_id") not in dids:
                raise HTTPException(status_code=403, detail="Retailer not in your assigned distributors")
        entry = {
            "id": _nid("rle"),
            "distributor_id": retailer["distributor_id"], "retailer_id": rid,
            "kind": "payment",
            "reference_no": body.get("reference_no", f"PMT-{datetime.now().strftime('%y%m%d%H%M%S')}"),
            "amount": amt, "method": body.get("method", "cash" if role == "salesperson" else "bank_transfer"),
            "description": body.get("description", "Payment received"),
            "at": _now(), "recorded_by": user["id"], "recorded_by_role": role,
        }
        await db.dms_retailer_ledger.insert_one(entry)
        return _clean(entry)

    # =========================================================================
    # SALES TEAM (Salesperson + Team Leader + Regional Manager)
    # =========================================================================

    # ── assignments ──
    @router.get("/assignments/tl-distributors")
    async def list_tl_dist_assignments(team_leader_id: Optional[str] = None, user: dict = Depends(get_current_user)):
        q: Dict[str, Any] = {}
        if team_leader_id:
            q["team_leader_id"] = team_leader_id
        elif user["role"] == "team_leader":
            q["team_leader_id"] = user["id"]
        docs = await db.dms_tl_assignments.find(q, {"_id": 0}).to_list(500)
        return {"data": docs}

    @router.post("/assignments/tl-distributors")
    async def assign_tl_dist(body: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        if user["role"] not in ("owner", "super_admin"):
            raise HTTPException(status_code=403, detail="Only owner can assign distributors to team leaders")
        tid = body.get("team_leader_id"); did = body.get("distributor_id")
        if not tid or not did:
            raise HTTPException(status_code=400, detail="team_leader_id + distributor_id required")
        await db.dms_tl_assignments.update_one(
            {"team_leader_id": tid, "distributor_id": did},
            {"$set": {"team_leader_id": tid, "distributor_id": did, "assigned_by": user["id"], "at": _now()}},
            upsert=True,
        )
        return {"ok": True}

    @router.delete("/assignments/tl-distributors")
    async def unassign_tl_dist(team_leader_id: str, distributor_id: str, user: dict = Depends(get_current_user)):
        if user["role"] not in ("owner", "super_admin"):
            raise HTTPException(status_code=403, detail="Forbidden")
        await db.dms_tl_assignments.delete_one({"team_leader_id": team_leader_id, "distributor_id": distributor_id})
        return {"ok": True}

    @router.get("/assignments/sp-distributors")
    async def list_sp_assignments(salesperson_id: Optional[str] = None, user: dict = Depends(get_current_user)):
        q: Dict[str, Any] = {}
        if salesperson_id:
            q["salesperson_id"] = salesperson_id
        elif user["role"] == "salesperson":
            q["salesperson_id"] = user["id"]
        docs = await db.dms_sp_assignments.find(q, {"_id": 0}).to_list(500)
        return {"data": docs}

    @router.post("/assignments/sp-distributors")
    async def assign_sp_dist(body: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        if user["role"] not in ("team_leader", "owner", "super_admin"):
            raise HTTPException(status_code=403, detail="Only team leader / owner can assign salespersons")
        spid = body.get("salesperson_id"); did = body.get("distributor_id")
        if not spid or not did:
            raise HTTPException(status_code=400, detail="salesperson_id + distributor_id required")
        # TL can only assign their own distributors
        if user["role"] == "team_leader":
            tl_dist = await db.dms_tl_assignments.find_one({"team_leader_id": user["id"], "distributor_id": did})
            if not tl_dist:
                raise HTTPException(status_code=403, detail="This distributor is not assigned to your team")
        await db.dms_sp_assignments.update_one(
            {"salesperson_id": spid, "distributor_id": did},
            {"$set": {"salesperson_id": spid, "distributor_id": did, "assigned_by": user["id"], "at": _now()}},
            upsert=True,
        )
        return {"ok": True}

    @router.delete("/assignments/sp-distributors")
    async def unassign_sp_dist(salesperson_id: str, distributor_id: str, user: dict = Depends(get_current_user)):
        if user["role"] not in ("team_leader", "owner", "super_admin"):
            raise HTTPException(status_code=403, detail="Forbidden")
        await db.dms_sp_assignments.delete_one({"salesperson_id": salesperson_id, "distributor_id": distributor_id})
        return {"ok": True}

    @router.get("/assignments/rm-tls")
    async def list_rm_tl_assignments(regional_manager_id: Optional[str] = None, user: dict = Depends(get_current_user)):
        q: Dict[str, Any] = {}
        if regional_manager_id:
            q["regional_manager_id"] = regional_manager_id
        elif user["role"] == "regional_manager":
            q["regional_manager_id"] = user["id"]
        docs = await db.dms_rm_assignments.find(q, {"_id": 0}).to_list(500)
        return {"data": docs}

    @router.post("/assignments/rm-tls")
    async def assign_rm_tl(body: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        if user["role"] not in ("owner", "super_admin"):
            raise HTTPException(status_code=403, detail="Forbidden")
        rmid = body.get("regional_manager_id"); tlid = body.get("team_leader_id")
        if not rmid or not tlid:
            raise HTTPException(status_code=400, detail="regional_manager_id + team_leader_id required")
        await db.dms_rm_assignments.update_one(
            {"regional_manager_id": rmid, "team_leader_id": tlid},
            {"$set": {"regional_manager_id": rmid, "team_leader_id": tlid, "assigned_by": user["id"], "at": _now()}},
            upsert=True,
        )
        return {"ok": True}

    @router.delete("/assignments/rm-tls")
    async def unassign_rm_tl(regional_manager_id: str, team_leader_id: str, user: dict = Depends(get_current_user)):
        if user["role"] not in ("owner", "super_admin"):
            raise HTTPException(status_code=403, detail="Forbidden")
        await db.dms_rm_assignments.delete_one({"regional_manager_id": regional_manager_id, "team_leader_id": team_leader_id})
        return {"ok": True}

    # ── list users by role (used by assignment UIs) ──
    @router.get("/users")
    async def list_dms_users(role: Optional[str] = None, user: dict = Depends(get_current_user)):
        if user["role"] not in ("owner", "super_admin", "team_leader", "regional_manager"):
            raise HTTPException(status_code=403, detail="Forbidden")
        q: Dict[str, Any] = {}
        if role:
            q["role"] = role
        docs = await db.users.find(q, {"_id": 0, "password_hash": 0}).to_list(1000)
        return {"data": docs}

    # ── punch in / out ──
    @router.post("/punch/in")
    async def punch_in(body: Dict[str, Any] = Body(...), user: dict = Depends(salesperson_only)):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        existing = await db.dms_punch.find_one({"salesperson_id": user["id"], "date": today, "out_at": None})
        if existing:
            return {"ok": True, "already": True, "punch": _clean(existing)}
        doc = {
            "id": _nid("pn"), "salesperson_id": user["id"], "date": today,
            "in_at": _now(), "out_at": None,
            "gps_in": {"lat": body.get("lat"), "lng": body.get("lng")},
            "gps_out": None,
        }
        await db.dms_punch.insert_one(doc)
        return {"ok": True, "punch": _clean(doc)}

    @router.post("/punch/out")
    async def punch_out(body: Dict[str, Any] = Body(...), user: dict = Depends(salesperson_only)):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        p = await db.dms_punch.find_one({"salesperson_id": user["id"], "date": today, "out_at": None})
        if not p:
            raise HTTPException(status_code=400, detail="Not punched in today")
        await db.dms_punch.update_one({"id": p["id"]}, {"$set": {
            "out_at": _now(),
            "gps_out": {"lat": body.get("lat"), "lng": body.get("lng")},
        }})
        p2 = await db.dms_punch.find_one({"id": p["id"]}, {"_id": 0})
        return {"ok": True, "punch": p2}

    @router.get("/punch/today")
    async def punch_today(user: dict = Depends(get_current_user)):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        p = await db.dms_punch.find_one({"salesperson_id": user["id"], "date": today}, {"_id": 0})
        return {"punch": p}

    @router.get("/punch/history")
    async def punch_history(salesperson_id: Optional[str] = None, user: dict = Depends(get_current_user)):
        target = salesperson_id
        if not target and user["role"] == "salesperson":
            target = user["id"]
        docs = await db.dms_punch.find({"salesperson_id": target}, {"_id": 0}).sort("in_at", -1).to_list(60)
        return {"data": docs}

    # =========================================================================
    # DASHBOARDS — sales team roles
    # =========================================================================
    @router.get("/dashboard/salesperson")
    async def sp_dashboard(user: dict = Depends(salesperson_only)):
        assigns = await db.dms_sp_assignments.find({"salesperson_id": user["id"]}, {"_id": 0}).to_list(500)
        dids = [a["distributor_id"] for a in assigns]
        n_dists = len(dids)
        n_retailers = await db.dms_retailers.count_documents({"distributor_id": {"$in": dids}, "active": True}) if dids else 0
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        orders_today = await db.dms_secondary_orders.count_documents({
            "placed_by": user["id"],
            "created_at": {"$gte": today + "T00:00:00"},
        })
        punch = await db.dms_punch.find_one({"salesperson_id": user["id"], "date": today}, {"_id": 0})
        return {
            "kpis": {
                "assigned_distributors": n_dists,
                "assigned_retailers": n_retailers,
                "orders_today": orders_today,
                "punched_in": bool(punch and not punch.get("out_at")),
            },
            "today_punch": punch,
        }

    @router.get("/dashboard/team-leader")
    async def tl_dashboard(user: dict = Depends(team_leader_only)):
        """
        Strict-spec TL dashboard. Returns:
          today_sales, monthly_sales, total_orders, pending_orders, fulfillment_pct,
          assigned_distributors, assigned_salespersons, total_retailers, stock_alerts
        """
        my_dists = await db.dms_tl_assignments.find({"team_leader_id": user["id"]}, {"_id": 0}).to_list(500)
        dids = [a["distributor_id"] for a in my_dists]

        today = _today()
        mtd_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

        today_sales = 0.0; monthly_sales = 0.0
        total_orders = 0; pending_orders = 0; delivered_orders = 0
        async for so in db.dms_secondary_orders.find({"distributor_id": {"$in": dids}}, {"_id": 0}):
            total_orders += 1
            if so.get("created_at", "").startswith(today):
                today_sales += so.get("total", 0)
            if so.get("created_at", "") >= mtd_start:
                monthly_sales += so.get("total", 0)
            st = so.get("status")
            if st == "pending":
                pending_orders += 1
            elif st in ("dispatched", "delivered"):
                delivered_orders += 1
        fulfillment_pct = _round((delivered_orders / total_orders * 100) if total_orders else 0, 1)

        n_sp = await db.dms_sp_assignments.count_documents({"distributor_id": {"$in": dids}}) if dids else 0
        n_ret = await db.dms_retailers.count_documents({"distributor_id": {"$in": dids}, "active": True}) if dids else 0

        # Stock alerts — distributor-wise low stock (<5 boxes) — count only
        stock_alerts = 0
        async for inv in db.dms_distributor_inventory.find({"distributor_id": {"$in": dids}}, {"_id": 0, "qty_boxes": 1}):
            if inv.get("qty_boxes", 0) < 5:
                stock_alerts += 1

        return {
            "kpis": {
                "today_sales": _round(today_sales),
                "monthly_sales": _round(monthly_sales),
                "total_orders": total_orders,
                "pending_orders": pending_orders,
                "fulfillment_pct": fulfillment_pct,
                "assigned_distributors": len(dids),
                "assigned_salespersons": n_sp,
                "total_retailers": n_ret,
                "stock_alerts": stock_alerts,
            }
        }

    # -------- TL: Distributor performance ---------
    @router.get("/tl/distributors")
    async def tl_distributor_performance(user: dict = Depends(team_leader_only)):
        assigns = await db.dms_tl_assignments.find({"team_leader_id": user["id"]}, {"_id": 0}).to_list(500)
        dids = [a["distributor_id"] for a in assigns]
        today = _today()
        mtd_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        out = []
        for did in dids:
            d = await db.dms_distributors.find_one({"id": did}, {"_id": 0})
            if not d: continue
            stock = 0
            async for inv in db.dms_distributor_inventory.find({"distributor_id": did}, {"_id": 0, "qty_boxes": 1}):
                stock += inv.get("qty_boxes", 0)
            # Outstanding payable = primary (owner→dist) invoices - payments
            po_billed = 0.0; po_paid = 0.0
            async for e in db.dms_primary_ledger.find({"distributor_id": did}, {"_id": 0}):
                if e.get("kind") == "invoice": po_billed += e.get("amount", 0)
                elif e.get("kind") in ("payment", "coupon_credit"): po_paid += e.get("amount", 0)
            outstanding_payable = po_billed - po_paid
            # Outstanding receivable = secondary (dist→retailer) invoices - payments
            so_billed = 0.0; so_paid = 0.0
            async for e in db.dms_retailer_ledger.find({"distributor_id": did}, {"_id": 0}):
                if e.get("kind") == "invoice": so_billed += e.get("amount", 0)
                elif e.get("kind") in ("payment", "coupon_credit"): so_paid += e.get("amount", 0)
            outstanding_receivable = so_billed - so_paid
            today_s = 0.0; monthly_s = 0.0; pending = 0
            async for so in db.dms_secondary_orders.find({"distributor_id": did}, {"_id": 0}):
                if so.get("created_at", "").startswith(today): today_s += so.get("total", 0)
                if so.get("created_at", "") >= mtd_start: monthly_s += so.get("total", 0)
                if so.get("status") == "pending": pending += 1
            out.append({
                "id": did, "name": d.get("name"), "region": d.get("region"),
                "available_stock": stock,
                "outstanding_payable_to_owner": _round(outstanding_payable),
                "outstanding_receivable_from_retailers": _round(outstanding_receivable),
                "today_sales": _round(today_s),
                "monthly_sales": _round(monthly_s),
                "revenue": _round(so_billed),
                "pending_orders": pending,
            })
        return {"data": out}

    # -------- TL: Salesperson list with live status ---------
    @router.get("/tl/salespersons")
    async def tl_salespersons(user: dict = Depends(team_leader_only)):
        assigns = await db.dms_tl_assignments.find({"team_leader_id": user["id"]}, {"_id": 0}).to_list(500)
        dids = [a["distributor_id"] for a in assigns]
        sp_ids = set()
        async for a in db.dms_sp_assignments.find({"distributor_id": {"$in": dids}}, {"_id": 0}):
            sp_ids.add(a["salesperson_id"])
        today = _today()
        out = []
        async for u in db.users.find({"role": "salesperson", "id": {"$in": list(sp_ids)}}, {"_id": 0, "password_hash": 0}):
            last_at = (u.get("last_gps") or {}).get("at") or u.get("last_active_at")
            online = False
            try:
                if last_at:
                    dt = datetime.fromisoformat(last_at.replace("Z", "+00:00"))
                    online = (datetime.now(timezone.utc) - dt).total_seconds() < 300
            except Exception:
                pass
            punch = await db.dms_punch.find_one({"salesperson_id": u["id"], "date": today}, {"_id": 0})
            # today's orders + new retailers
            orders_today = await db.dms_secondary_orders.count_documents({"placed_by": u["id"], "created_at": {"$gte": today + "T00:00:00"}})
            new_ret_today = await db.dms_retailers.count_documents({"onboarded_by": u["id"], "created_at": {"$gte": today + "T00:00:00"}})
            # unique retailer visits today (from proximity to any retailer)
            pings = await db.dms_sp_pings.find({"salesperson_id": u["id"], "date": today}, {"_id": 0}).to_list(2000)
            visits = 0
            if pings:
                async for r in db.dms_retailers.find({"distributor_id": {"$in": dids}, "gps_lat": {"$ne": None}}, {"_id": 0}):
                    for p in pings:
                        if _haversine_km(r["gps_lat"], r["gps_lng"], p["lat"], p["lng"]) < 0.20:
                            visits += 1
                            break
            out.append({
                "id": u["id"], "name": u.get("name"), "phone": u.get("phone"),
                "online": online, "last_seen_at": last_at,
                "live_location": u.get("last_gps"),
                "punch_in": (punch or {}).get("in_at"),
                "punch_out": (punch or {}).get("out_at"),
                "today_visits": visits,
                "orders_today": orders_today,
                "new_retailers_today": new_ret_today,
            })
        return {"data": out}

    # -------- TL: Order monitoring ---------
    @router.get("/tl/orders")
    async def tl_orders(
        status: Optional[str] = None,
        distributor_id: Optional[str] = None,
        salesperson_id: Optional[str] = None,
        retailer_id: Optional[str] = None,
        user: dict = Depends(team_leader_only),
    ):
        assigns = await db.dms_tl_assignments.find({"team_leader_id": user["id"]}, {"_id": 0}).to_list(500)
        my_dids = [a["distributor_id"] for a in assigns]
        q: Dict[str, Any] = {"distributor_id": {"$in": my_dids}}
        if status: q["status"] = status
        if distributor_id and distributor_id in my_dids: q["distributor_id"] = distributor_id
        if salesperson_id: q["placed_by"] = salesperson_id
        if retailer_id: q["retailer_id"] = retailer_id
        docs = await db.dms_secondary_orders.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
        # enrich
        for o in docs:
            r = await db.dms_retailers.find_one({"id": o.get("retailer_id")}, {"_id": 0, "name": 1})
            d = await db.dms_distributors.find_one({"id": o.get("distributor_id")}, {"_id": 0, "name": 1})
            o["retailer_name"] = (r or {}).get("name")
            o["distributor_name"] = (d or {}).get("name")
        return {"data": docs, "count": len(docs)}

    # -------- TL: Retailers ---------
    @router.get("/tl/retailers")
    async def tl_retailers(user: dict = Depends(team_leader_only)):
        assigns = await db.dms_tl_assignments.find({"team_leader_id": user["id"]}, {"_id": 0}).to_list(500)
        dids = [a["distributor_id"] for a in assigns]
        out = []
        async for r in db.dms_retailers.find({"distributor_id": {"$in": dids}, "active": True}, {"_id": 0}):
            # outstanding
            billed = 0.0; paid = 0.0
            async for e in db.dms_retailer_ledger.find({"retailer_id": r["id"]}, {"_id": 0}):
                if e.get("kind") == "invoice": billed += e.get("amount", 0)
                elif e.get("kind") in ("payment", "coupon_credit"): paid += e.get("amount", 0)
            # last order
            last = await db.dms_secondary_orders.find_one({"retailer_id": r["id"]}, {"_id": 0}, sort=[("created_at", -1)])
            total_purchases = 0.0
            async for so in db.dms_secondary_orders.find({"retailer_id": r["id"]}, {"_id": 0, "total": 1}):
                total_purchases += so.get("total", 0)
            out.append({
                "id": r["id"], "name": r.get("name"), "phone": r.get("phone"),
                "address": r.get("address"), "region": r.get("region"),
                "gps_lat": r.get("gps_lat"), "gps_lng": r.get("gps_lng"),
                "location_link": r.get("location_link"),
                "outstanding": _round(billed - paid),
                "last_order_at": (last or {}).get("created_at"),
                "total_purchases": _round(total_purchases),
            })
        return {"data": out}

    # -------- TL: Attendance (own) ---------
    @router.get("/tl/attendance")
    async def tl_attendance(user: dict = Depends(team_leader_only)):
        docs = await db.dms_punch.find({"salesperson_id": user["id"]}, {"_id": 0}).sort("in_at", -1).to_list(60)
        return {"data": docs}

    @router.post("/tl/punch/in")
    async def tl_punch_in(body: Dict[str, Any] = Body(...), user: dict = Depends(team_leader_only)):
        today = _today()
        existing = await db.dms_punch.find_one({"salesperson_id": user["id"], "date": today, "out_at": None})
        if existing:
            return {"ok": True, "already": True}
        doc = {"id": _nid("pn"), "salesperson_id": user["id"], "date": today,
               "in_at": _now(), "out_at": None,
               "gps_in": {"lat": body.get("lat"), "lng": body.get("lng")}, "gps_out": None}
        await db.dms_punch.insert_one(doc)
        return {"ok": True, "punch": _clean(doc)}

    @router.post("/tl/punch/out")
    async def tl_punch_out(body: Dict[str, Any] = Body(...), user: dict = Depends(team_leader_only)):
        today = _today()
        p = await db.dms_punch.find_one({"salesperson_id": user["id"], "date": today, "out_at": None})
        if not p:
            raise HTTPException(status_code=400, detail="Not punched in today")
        await db.dms_punch.update_one({"id": p["id"]}, {"$set": {
            "out_at": _now(), "gps_out": {"lat": body.get("lat"), "lng": body.get("lng")},
        }})
        return {"ok": True}

    # =========================================================================
    # OWNER — TL Performance Dashboard + Distributor Sales Drilldown
    # =========================================================================
    @router.get("/owner/tl-performance")
    async def owner_tl_performance(user: dict = Depends(owner_only)):
        today = _today()
        mtd_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        rows = []
        async for tl in db.users.find({"role": "team_leader"}, {"_id": 0, "password_hash": 0}):
            assigns = await db.dms_tl_assignments.find({"team_leader_id": tl["id"]}, {"_id": 0}).to_list(500)
            dids = [a["distributor_id"] for a in assigns]
            n_sp = await db.dms_sp_assignments.count_documents({"distributor_id": {"$in": dids}}) if dids else 0
            total = 0.0; today_s = 0.0; monthly = 0.0; n_orders = 0; pending = 0
            # date-wise last 7 days
            by_date: Dict[str, float] = {}
            async for so in db.dms_secondary_orders.find({"distributor_id": {"$in": dids}}, {"_id": 0}):
                amt = so.get("total", 0)
                total += amt
                n_orders += 1
                d = so.get("created_at", "")[:10]
                by_date[d] = by_date.get(d, 0) + amt
                if d == today: today_s += amt
                if so.get("created_at", "") >= mtd_start: monthly += amt
                if so.get("status") == "pending": pending += 1
            # last 7 days series
            series = []
            for i in range(6, -1, -1):
                d = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
                series.append({"date": d, "sales": _round(by_date.get(d, 0))})
            rows.append({
                "team_leader_id": tl["id"],
                "name": tl.get("name"),
                "email": tl.get("email"),
                "assigned_distributors": len(dids),
                "assigned_salespersons": n_sp,
                "total_sales": _round(total),
                "today_sales": _round(today_s),
                "monthly_sales": _round(monthly),
                "total_orders": n_orders,
                "pending_orders": pending,
                "series_7d": series,
            })
        # ranking by total_sales desc
        rows.sort(key=lambda r: r["total_sales"], reverse=True)
        return {"data": rows}

    @router.get("/owner/distributor-sales/{did}")
    async def owner_distributor_sales(did: str, user: dict = Depends(owner_only)):
        """Complete drilldown: which retailers, which products, quantities, prices."""
        dist = await db.dms_distributors.find_one({"id": did}, {"_id": 0})
        if not dist:
            raise HTTPException(status_code=404, detail="Distributor not found")
        # all secondary orders for this distributor
        orders = await db.dms_secondary_orders.find({"distributor_id": did}, {"_id": 0}).sort("created_at", -1).to_list(1000)
        # aggregate by retailer & by product
        by_retailer: Dict[str, Dict[str, Any]] = {}
        by_product: Dict[str, Dict[str, Any]] = {}
        for o in orders:
            rid = o.get("retailer_id")
            if rid not in by_retailer:
                r = await db.dms_retailers.find_one({"id": rid}, {"_id": 0, "name": 1, "address": 1})
                by_retailer[rid] = {"retailer_id": rid, "retailer_name": (r or {}).get("name"), "address": (r or {}).get("address"),
                                    "orders": 0, "total_revenue": 0.0}
            by_retailer[rid]["orders"] += 1
            by_retailer[rid]["total_revenue"] += o.get("total", 0)
            for it in (o.get("items") or []):
                pid = it.get("product_id")
                if pid not in by_product:
                    p = await db.dms_products.find_one({"id": pid}, {"_id": 0, "name": 1, "sku_code": 1})
                    by_product[pid] = {"product_id": pid, "product_name": (p or {}).get("name"),
                                       "sku_code": (p or {}).get("sku_code"),
                                       "qty_boxes": 0, "qty_pcs": 0, "revenue": 0.0,
                                       "prices_seen": set()}
                by_product[pid]["qty_boxes"] += int(it.get("qty_boxes", 0) or 0)
                by_product[pid]["qty_pcs"] += int(it.get("qty_pcs", 0) or 0)
                by_product[pid]["revenue"] += float(it.get("line_total", 0) or 0)
                if it.get("box_price"): by_product[pid]["prices_seen"].add(float(it["box_price"]))
        # normalise prices set → list
        for p in by_product.values():
            p["prices_seen"] = sorted(list(p["prices_seen"]))
            p["revenue"] = _round(p["revenue"])
        for r in by_retailer.values():
            r["total_revenue"] = _round(r["total_revenue"])
        # slim orders (last 30)
        recent = []
        for o in orders[:30]:
            r = await db.dms_retailers.find_one({"id": o.get("retailer_id")}, {"_id": 0, "name": 1})
            recent.append({
                "id": o["id"], "at": o.get("created_at"),
                "retailer": (r or {}).get("name"),
                "total": _round(o.get("total", 0)),
                "status": o.get("status"),
                "items_count": len(o.get("items") or []),
            })
        return {
            "distributor": {"id": dist["id"], "name": dist.get("name"), "region": dist.get("region"),
                             "gps_lat": dist.get("gps_lat"), "gps_lng": dist.get("gps_lng")},
            "by_retailer": list(by_retailer.values()),
            "by_product": list(by_product.values()),
            "recent_orders": recent,
            "totals": {
                "orders": len(orders),
                "revenue": _round(sum(o.get("total", 0) for o in orders)),
                "retailers_active": len(by_retailer),
                "products_sold": len(by_product),
            },
        }

    @router.get("/dashboard/team-leader-legacy-sales-mtd")
    async def _tl_sales_mtd_legacy(user: dict = Depends(team_leader_only)):
        # kept only so any old client that still calls this doesn't 404
        return {"kpis": {"sales_mtd": 0}}


    @router.get("/dashboard/regional-manager")
    async def rm_dashboard(user: dict = Depends(regional_manager_only)):
        """
        Strict-spec RM dashboard: total_tls, total_distributors, total_retailers,
        total_salespersons, today_sales, monthly_sales, outstanding, revenue, fulfillment_pct.
        """
        my_tls = await db.dms_rm_assignments.find({"regional_manager_id": user["id"]}, {"_id": 0}).to_list(500)
        tlids = [a["team_leader_id"] for a in my_tls]
        # distributors under those TLs
        dids = list({a["distributor_id"] async for a in db.dms_tl_assignments.find({"team_leader_id": {"$in": tlids}}, {"_id": 0, "distributor_id": 1})})
        sp_ids = list({a["salesperson_id"] async for a in db.dms_sp_assignments.find({"distributor_id": {"$in": dids}}, {"_id": 0, "salesperson_id": 1})})
        n_ret = await db.dms_retailers.count_documents({"distributor_id": {"$in": dids}, "active": True}) if dids else 0
        today = _today()
        mtd_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        today_s = 0.0; monthly = 0.0; total_rev = 0.0; total_n = 0; delivered = 0
        async for so in db.dms_secondary_orders.find({"distributor_id": {"$in": dids}}, {"_id": 0}):
            total_n += 1
            total_rev += so.get("total", 0)
            if so.get("created_at", "").startswith(today): today_s += so.get("total", 0)
            if so.get("created_at", "") >= mtd_start: monthly += so.get("total", 0)
            if so.get("status") in ("dispatched", "delivered"): delivered += 1
        # outstanding (retailer ledger) across those distributors
        billed = 0.0; paid = 0.0
        async for e in db.dms_retailer_ledger.find({"distributor_id": {"$in": dids}}, {"_id": 0}):
            if e.get("kind") == "invoice": billed += e.get("amount", 0)
            elif e.get("kind") in ("payment", "coupon_credit"): paid += e.get("amount", 0)
        return {
            "kpis": {
                "team_leaders": len(tlids),
                "distributors": len(dids),
                "retailers": n_ret,
                "salespersons": len(sp_ids),
                "today_sales": _round(today_s),
                "monthly_sales": _round(monthly),
                "outstanding": _round(billed - paid),
                "revenue": _round(total_rev),
                "fulfillment_pct": _round((delivered / total_n * 100) if total_n else 0, 1),
            }
        }

    # --------- RM: TL monitoring ---------
    @router.get("/rm/team-leaders")
    async def rm_team_leaders(user: dict = Depends(regional_manager_only)):
        my_tls = await db.dms_rm_assignments.find({"regional_manager_id": user["id"]}, {"_id": 0}).to_list(500)
        tlids = [a["team_leader_id"] for a in my_tls]
        rows = []
        for tlid in tlids:
            tl = await db.users.find_one({"id": tlid}, {"_id": 0, "password_hash": 0})
            if not tl: continue
            dids = [a["distributor_id"] async for a in db.dms_tl_assignments.find({"team_leader_id": tlid}, {"_id": 0, "distributor_id": 1})]
            active_sp = 0
            for spid in [a["salesperson_id"] async for a in db.dms_sp_assignments.find({"distributor_id": {"$in": dids}}, {"_id": 0, "salesperson_id": 1})]:
                u = await db.users.find_one({"id": spid}, {"_id": 0, "last_active_at": 1})
                la = (u or {}).get("last_active_at")
                if la:
                    try:
                        dt = datetime.fromisoformat(la.replace("Z", "+00:00"))
                        if (datetime.now(timezone.utc) - dt).total_seconds() < 300: active_sp += 1
                    except Exception: pass
            sales = 0.0; pending = 0
            async for so in db.dms_secondary_orders.find({"distributor_id": {"$in": dids}}, {"_id": 0}):
                sales += so.get("total", 0)
                if so.get("status") == "pending": pending += 1
            rows.append({
                "id": tlid, "name": tl.get("name"), "email": tl.get("email"),
                "sales": _round(sales),
                "active_salespersons": active_sp,
                "active_distributors": len(dids),
                "pending_orders": pending,
                "revenue": _round(sales),
            })
        rows.sort(key=lambda r: r["sales"], reverse=True)
        return {"data": rows}

    # --------- RM: Distributor monitoring (read only) ---------
    @router.get("/rm/distributors")
    async def rm_distributors(user: dict = Depends(regional_manager_only)):
        my_tls = await db.dms_rm_assignments.find({"regional_manager_id": user["id"]}, {"_id": 0}).to_list(500)
        tlids = [a["team_leader_id"] for a in my_tls]
        dids = list({a["distributor_id"] async for a in db.dms_tl_assignments.find({"team_leader_id": {"$in": tlids}}, {"_id": 0, "distributor_id": 1})})
        rows = []
        for did in dids:
            d = await db.dms_distributors.find_one({"id": did}, {"_id": 0})
            if not d: continue
            stock = 0
            async for inv in db.dms_distributor_inventory.find({"distributor_id": did}, {"_id": 0, "qty_boxes": 1}):
                stock += inv.get("qty_boxes", 0)
            po_billed = 0.0; po_paid = 0.0
            async for e in db.dms_primary_ledger.find({"distributor_id": did}, {"_id": 0}):
                if e.get("kind") == "invoice": po_billed += e.get("amount", 0)
                elif e.get("kind") in ("payment", "coupon_credit"): po_paid += e.get("amount", 0)
            revenue = 0.0; orders = 0
            async for so in db.dms_secondary_orders.find({"distributor_id": did}, {"_id": 0}):
                revenue += so.get("total", 0); orders += 1
            n_ret = await db.dms_retailers.count_documents({"distributor_id": did, "active": True})
            rows.append({
                "id": did, "name": d.get("name"), "region": d.get("region"),
                "stock": stock, "pending_payments": _round(po_billed - po_paid),
                "revenue": _round(revenue), "retailers": n_ret, "orders": orders,
            })
        return {"data": rows}

    # --------- RM: Salesperson monitoring (read only) ---------
    @router.get("/rm/salespersons")
    async def rm_salespersons(user: dict = Depends(regional_manager_only)):
        my_tls = await db.dms_rm_assignments.find({"regional_manager_id": user["id"]}, {"_id": 0}).to_list(500)
        tlids = [a["team_leader_id"] for a in my_tls]
        dids = list({a["distributor_id"] async for a in db.dms_tl_assignments.find({"team_leader_id": {"$in": tlids}}, {"_id": 0, "distributor_id": 1})})
        sp_ids = list({a["salesperson_id"] async for a in db.dms_sp_assignments.find({"distributor_id": {"$in": dids}}, {"_id": 0, "salesperson_id": 1})})
        today = _today()
        rows = []
        async for u in db.users.find({"role": "salesperson", "id": {"$in": sp_ids}}, {"_id": 0, "password_hash": 0}):
            la = (u.get("last_gps") or {}).get("at") or u.get("last_active_at")
            online = False
            try:
                if la:
                    dt = datetime.fromisoformat(la.replace("Z", "+00:00"))
                    online = (datetime.now(timezone.utc) - dt).total_seconds() < 300
            except Exception: pass
            punch = await db.dms_punch.find_one({"salesperson_id": u["id"], "date": today}, {"_id": 0})
            visits = 0
            pings = await db.dms_sp_pings.find({"salesperson_id": u["id"], "date": today}, {"_id": 0}).to_list(2000)
            if pings:
                async for r in db.dms_retailers.find({"distributor_id": {"$in": dids}, "gps_lat": {"$ne": None}}, {"_id": 0}):
                    for p in pings:
                        if _haversine_km(r["gps_lat"], r["gps_lng"], p["lat"], p["lng"]) < 0.20:
                            visits += 1; break
            orders_today = await db.dms_secondary_orders.count_documents({"placed_by": u["id"], "created_at": {"$gte": today + "T00:00:00"}})
            new_ret = await db.dms_retailers.count_documents({"onboarded_by": u["id"], "created_at": {"$gte": today + "T00:00:00"}})
            rows.append({
                "id": u["id"], "name": u.get("name"), "phone": u.get("phone"),
                "online": online, "live_location": u.get("last_gps"),
                "punch_in": (punch or {}).get("in_at"), "punch_out": (punch or {}).get("out_at"),
                "orders_today": orders_today, "today_visits": visits, "new_retailers_today": new_ret,
            })
        return {"data": rows}

    # --------- RM: Region performance (dist-wise, TL-wise, SP-wise sales) ---------
    @router.get("/rm/region-performance")
    async def rm_region_performance(user: dict = Depends(regional_manager_only)):
        my_tls = await db.dms_rm_assignments.find({"regional_manager_id": user["id"]}, {"_id": 0}).to_list(500)
        tlids = [a["team_leader_id"] for a in my_tls]
        tl_dists = {a["team_leader_id"]: [] async for a in db.dms_tl_assignments.find({"team_leader_id": {"$in": tlids}}, {"_id": 0})}
        # accumulate
        async for a in db.dms_tl_assignments.find({"team_leader_id": {"$in": tlids}}, {"_id": 0}):
            tl_dists.setdefault(a["team_leader_id"], []).append(a["distributor_id"])
        all_dids = list({d for lst in tl_dists.values() for d in lst})

        by_dist = {}; by_tl = {}; by_sp = {}
        async for so in db.dms_secondary_orders.find({"distributor_id": {"$in": all_dids}}, {"_id": 0}):
            amt = so.get("total", 0)
            by_dist[so["distributor_id"]] = by_dist.get(so["distributor_id"], 0) + amt
            placed_by = so.get("placed_by")
            if placed_by: by_sp[placed_by] = by_sp.get(placed_by, 0) + amt

        # attribute to TLs via TL→dist mapping
        for tlid, dlist in tl_dists.items():
            by_tl[tlid] = sum(by_dist.get(d, 0) for d in dlist)

        # enrich with names
        async def _name(uid):
            u = await db.users.find_one({"id": uid}, {"_id": 0, "name": 1})
            return (u or {}).get("name", uid)
        async def _dname(did):
            d = await db.dms_distributors.find_one({"id": did}, {"_id": 0, "name": 1})
            return (d or {}).get("name", did)

        out_dist = [{"id": did, "name": await _dname(did), "sales": _round(v)} for did, v in by_dist.items()]
        out_tl = [{"id": tid, "name": await _name(tid), "sales": _round(v)} for tid, v in by_tl.items()]
        out_sp = [{"id": sid, "name": await _name(sid), "sales": _round(v)} for sid, v in by_sp.items()]
        for lst in (out_dist, out_tl, out_sp): lst.sort(key=lambda r: r["sales"], reverse=True)
        return {"by_distributor": out_dist, "by_team_leader": out_tl, "by_salesperson": out_sp}


    @router.get("/dashboard/retailer")
    async def retailer_dashboard(user: dict = Depends(retailer_only)):
        rid = user.get("retailer_id")
        if not rid:
            raise HTTPException(status_code=400, detail="Not linked to a retailer")
        billed = 0.0; paid = 0.0
        async for e in db.dms_retailer_ledger.find({"retailer_id": rid}, {"_id": 0}):
            if e["kind"] == "invoice":
                billed += e["amount"]
            elif e["kind"] in ("payment", "coupon_credit"):
                paid += e["amount"]
        pending = 0
        async for pd in db.dms_retailer_pending.find({"retailer_id": rid}, {"_id": 0}):
            pending += int(pd.get("pending_qty_boxes", 0)) + int(pd.get("pending_qty_pcs", 0))
        n_orders = await db.dms_secondary_orders.count_documents({"retailer_id": rid})
        n_dispatched = await db.dms_secondary_orders.count_documents({"retailer_id": rid, "status": "dispatched"})
        return {
            "kpis": {
                "total_orders": n_orders,
                "in_transit": n_dispatched,
                "outstanding": _round(billed - paid),
                "pending_items": pending,
            }
        }

    @router.get("/dashboard/super-admin")
    async def superadmin_dashboard(user: dict = Depends(_guard())):
        # Owner + super_admin both allowed (roles unified per user request)
        if user["role"] not in ("super_admin", "owner"):
            raise HTTPException(status_code=403, detail="Owner only")
        n_owners = await db.users.count_documents({"role": "owner"})
        n_tl = await db.users.count_documents({"role": "team_leader"})
        n_sp = await db.users.count_documents({"role": "salesperson"})
        n_dist = await db.dms_distributors.count_documents({"active": True})
        n_ret = await db.dms_retailers.count_documents({"active": True})
        n_po = await db.dms_primary_orders.count_documents({})
        n_so = await db.dms_secondary_orders.count_documents({})
        return {
            "kpis": {
                "owners": n_owners, "team_leaders": n_tl, "salespersons": n_sp,
                "distributors": n_dist, "retailers": n_ret,
                "primary_orders": n_po, "secondary_orders": n_so,
            }
        }

    # =========================================================================
    # LIVE TRACKING — Salesperson GPS pings (Phase 2 + 3)
    # =========================================================================
    def _haversine_km(lat1, lng1, lat2, lng2) -> float:
        """Great-circle distance between two lat/lng points in KM."""
        from math import radians, sin, cos, asin, sqrt
        try:
            lat1, lng1, lat2, lng2 = map(float, (lat1, lng1, lat2, lng2))
        except Exception:
            return 0.0
        R = 6371.0
        dLat = radians(lat2 - lat1)
        dLng = radians(lng2 - lng1)
        a = sin(dLat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dLng/2)**2
        return 2 * R * asin(sqrt(a))

    def _yyyy_mm_dd(iso_or_dt) -> str:
        if isinstance(iso_or_dt, str):
            return iso_or_dt[:10]
        return iso_or_dt.strftime("%Y-%m-%d")

    def _today() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _tl_can_see_sp(tl_id: str, sp_user: dict, db_ref) -> bool:
        # placeholder — narrower check happens inline; kept for readability
        return True

    async def _sp_visible_ids_for(user: dict) -> List[str]:
        """
        Return the list of salesperson user_ids the given user is allowed to see.
        owner / super_admin → all
        regional_manager → SPs assigned to TLs under this RM
        team_leader → SPs assigned to distributors under this TL
        """
        role = user.get("role")
        if role in ("owner", "super_admin"):
            ids = [u["id"] async for u in db.users.find({"role": "salesperson"}, {"_id": 0, "id": 1})]
            return ids
        if role == "team_leader":
            tl_dists = [a["distributor_id"] async for a in db.dms_tl_assignments.find({"team_leader_id": user["id"]}, {"_id": 0, "distributor_id": 1})]
            if not tl_dists:
                return []
            ids = set()
            async for a in db.dms_sp_assignments.find({"distributor_id": {"$in": tl_dists}}, {"_id": 0, "salesperson_id": 1}):
                ids.add(a["salesperson_id"])
            return list(ids)
        if role == "regional_manager":
            tls = [a["team_leader_id"] async for a in db.dms_rm_assignments.find({"regional_manager_id": user["id"]}, {"_id": 0, "team_leader_id": 1})]
            dists = set()
            async for a in db.dms_tl_assignments.find({"team_leader_id": {"$in": tls}}, {"_id": 0, "distributor_id": 1}):
                dists.add(a["distributor_id"])
            ids = set()
            async for a in db.dms_sp_assignments.find({"distributor_id": {"$in": list(dists)}}, {"_id": 0, "salesperson_id": 1}):
                ids.add(a["salesperson_id"])
            return list(ids)
        if role == "salesperson":
            return [user["id"]]
        return []

    @router.post("/tracking/ping")
    async def tracking_ping(body: Dict[str, Any] = Body(...), user: dict = Depends(salesperson_only)):
        """Salesperson posts current GPS every 60s."""
        lat = body.get("lat"); lng = body.get("lng")
        if lat is None or lng is None:
            raise HTTPException(status_code=400, detail="lat and lng required")
        now = _now()
        doc = {
            "id": _nid("png"),
            "salesperson_id": user["id"],
            "lat": float(lat),
            "lng": float(lng),
            "accuracy": body.get("accuracy"),
            "speed": body.get("speed"),
            "date": _today(),
            "created_at": now,
        }
        await db.dms_sp_pings.insert_one(doc)
        # also stamp "last_active_at" on the user so live status reflects
        await db.users.update_one({"id": user["id"]}, {"$set": {
            "last_active_at": now,
            "last_gps": {"lat": doc["lat"], "lng": doc["lng"], "at": now},
        }})
        return {"ok": True}

    @router.get("/tracking/live")
    async def tracking_live(user: dict = Depends(get_current_user)):
        """
        Current live map data for Owner / TL / RM.
        Returns:
          - salespersons: [{id, name, phone, lat, lng, last_ping_at, online}]
          - distributors: [{id, name, lat, lng, address}]
          - retailers:    [{id, name, lat, lng, address, distributor_id}]
        """
        role = user.get("role")
        if role not in ("owner", "super_admin", "team_leader", "regional_manager"):
            raise HTTPException(status_code=403, detail="Forbidden")

        sp_ids = await _sp_visible_ids_for(user)
        sps = []
        async for u in db.users.find({"role": "salesperson", "id": {"$in": sp_ids}}, {"_id": 0, "password_hash": 0}):
            gps = u.get("last_gps") or {}
            last_at = gps.get("at") or u.get("last_active_at")
            online = False
            try:
                if last_at:
                    dt = datetime.fromisoformat(last_at.replace("Z", "+00:00"))
                    online = (datetime.now(timezone.utc) - dt).total_seconds() < 300
            except Exception:
                pass
            sps.append({
                "id": u["id"], "name": u.get("name"), "phone": u.get("phone"),
                "lat": gps.get("lat"), "lng": gps.get("lng"),
                "last_ping_at": last_at,
                "online": online,
            })

        # distributors — filter by role hierarchy
        dq: Dict[str, Any] = {"active": True}
        if role == "team_leader":
            dids = [a["distributor_id"] async for a in db.dms_tl_assignments.find({"team_leader_id": user["id"]}, {"_id": 0, "distributor_id": 1})]
            dq["id"] = {"$in": dids}
        elif role == "regional_manager":
            tls = [a["team_leader_id"] async for a in db.dms_rm_assignments.find({"regional_manager_id": user["id"]}, {"_id": 0, "team_leader_id": 1})]
            dids = [a["distributor_id"] async for a in db.dms_tl_assignments.find({"team_leader_id": {"$in": tls}}, {"_id": 0, "distributor_id": 1})]
            dq["id"] = {"$in": dids}
        dists = []
        async for d in db.dms_distributors.find(dq, {"_id": 0}):
            dists.append({
                "id": d["id"], "name": d.get("name"),
                "lat": d.get("gps_lat"), "lng": d.get("gps_lng"),
                "location_link": d.get("location_link"),
                "address": d.get("address"), "region": d.get("region"),
            })

        # retailers — under those distributors
        rq: Dict[str, Any] = {"active": True}
        if "id" in dq:
            rq["distributor_id"] = dq["id"]
        rets = []
        async for r in db.dms_retailers.find(rq, {"_id": 0}):
            rets.append({
                "id": r["id"], "name": r.get("name"),
                "lat": r.get("gps_lat"), "lng": r.get("gps_lng"),
                "location_link": r.get("location_link"),
                "address": r.get("address"),
                "distributor_id": r.get("distributor_id"),
            })

        # Phase 1: Team Leaders live positions (for RSM / Owner view — "ASM"=TL in this DMS)
        tls: List[Dict[str, Any]] = []
        tl_query_ids: List[str] = []
        if role == "regional_manager":
            tl_query_ids = [a["team_leader_id"] async for a in db.dms_rm_assignments.find({"regional_manager_id": user["id"]}, {"_id": 0, "team_leader_id": 1})]
        elif role in ("owner", "super_admin"):
            tl_query_ids = [u["id"] async for u in db.users.find({"role": "team_leader"}, {"_id": 0, "id": 1})]
        if tl_query_ids:
            async for u in db.users.find({"id": {"$in": tl_query_ids}, "role": "team_leader"}, {"_id": 0, "password_hash": 0}):
                gps = u.get("last_gps") or {}
                last_at = gps.get("at") or u.get("last_active_at")
                online = False
                try:
                    if last_at:
                        dt = datetime.fromisoformat(last_at.replace("Z", "+00:00"))
                        online = (datetime.now(timezone.utc) - dt).total_seconds() < 300
                except Exception:
                    pass
                tls.append({
                    "id": u["id"], "name": u.get("name"), "phone": u.get("phone"),
                    "lat": gps.get("lat"), "lng": gps.get("lng"),
                    "last_ping_at": last_at, "online": online,
                })

        return {"salespersons": sps, "distributors": dists, "retailers": rets, "team_leaders": tls}

    @router.get("/tracking/salesperson/{sid}")
    async def tracking_salesperson_detail(
        sid: str,
        date: Optional[str] = Query(None, description="YYYY-MM-DD; defaults to today"),
        user: dict = Depends(get_current_user),
    ):
        """
        Full detail for one salesperson on one date:
          - profile + current live location
          - punch in / out + working hours
          - full route (ordered pings)
          - total distance travelled
          - visited distributors / retailers (proximity < 200m to any ping)
        """
        # RBAC — same visibility rules as /tracking/live
        allowed = await _sp_visible_ids_for(user)
        if sid not in allowed:
            raise HTTPException(status_code=403, detail="Not permitted to view this salesperson")

        day = date or _today()
        sp = await db.users.find_one({"id": sid, "role": "salesperson"}, {"_id": 0, "password_hash": 0})
        if not sp:
            raise HTTPException(status_code=404, detail="Salesperson not found")

        # punch
        punch = await db.dms_punch.find_one({"salesperson_id": sid, "date": day}, {"_id": 0})
        working_hours = 0.0
        if punch and punch.get("in_at"):
            try:
                a = datetime.fromisoformat(punch["in_at"].replace("Z", "+00:00"))
                b = datetime.fromisoformat((punch.get("out_at") or _now()).replace("Z", "+00:00"))
                working_hours = max(0.0, (b - a).total_seconds() / 3600.0)
            except Exception:
                pass

        # pings for the day
        pings = await db.dms_sp_pings.find(
            {"salesperson_id": sid, "date": day}, {"_id": 0}
        ).sort("created_at", 1).to_list(5000)

        # distance
        distance_km = 0.0
        for i in range(1, len(pings)):
            distance_km += _haversine_km(pings[i-1]["lat"], pings[i-1]["lng"], pings[i]["lat"], pings[i]["lng"])

        # visited shops = distributors/retailers with a ping within 200m
        def _near(pt_lat, pt_lng) -> bool:
            for p in pings:
                if _haversine_km(pt_lat, pt_lng, p["lat"], p["lng"]) < 0.20:
                    return True
            return False

        visited_dists = []
        async for d in db.dms_distributors.find({"active": True, "gps_lat": {"$ne": None}}, {"_id": 0}):
            if d.get("gps_lat") is None or d.get("gps_lng") is None: continue
            if _near(d["gps_lat"], d["gps_lng"]):
                visited_dists.append({"id": d["id"], "name": d["name"], "lat": d.get("gps_lat"), "lng": d.get("gps_lng")})

        visited_rets = []
        async for r in db.dms_retailers.find({"active": True, "gps_lat": {"$ne": None}}, {"_id": 0}):
            if r.get("gps_lat") is None or r.get("gps_lng") is None: continue
            if _near(r["gps_lat"], r["gps_lng"]):
                visited_rets.append({"id": r["id"], "name": r["name"], "lat": r.get("gps_lat"), "lng": r.get("gps_lng")})

        return {
            "salesperson": {
                "id": sp["id"], "name": sp.get("name"), "phone": sp.get("phone"),
                "current_gps": sp.get("last_gps"),
                "last_active_at": sp.get("last_active_at"),
            },
            "date": day,
            "punch": punch,
            "working_hours": _round(working_hours, 2),
            "distance_km": _round(distance_km, 2),
            "route": pings,
            "visited": {"distributors": visited_dists, "retailers": visited_rets},
        }

    @router.get("/tracking/salesperson/{sid}/history")
    async def tracking_history(
        sid: str,
        days: int = Query(30, ge=1, le=365),
        user: dict = Depends(get_current_user),
    ):
        """Date-wise summary (last N days) for the salesperson."""
        allowed = await _sp_visible_ids_for(user)
        if sid not in allowed:
            raise HTTPException(status_code=403, detail="Not permitted")
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        # group pings by date
        pipe = [
            {"$match": {"salesperson_id": sid, "created_at": {"$gte": start.isoformat()}}},
            {"$group": {"_id": "$date", "count": {"$sum": 1}}},
            {"$sort": {"_id": -1}},
        ]
        counts = {r["_id"]: r["count"] async for r in db.dms_sp_pings.aggregate(pipe)}
        punches = {p["date"]: p async for p in db.dms_punch.find({"salesperson_id": sid, "date": {"$gte": start.strftime("%Y-%m-%d")}}, {"_id": 0})}
        out = []
        for date_str, cnt in sorted(counts.items(), reverse=True):
            p = punches.get(date_str)
            hrs = 0.0
            if p and p.get("in_at"):
                try:
                    a = datetime.fromisoformat(p["in_at"].replace("Z", "+00:00"))
                    b = datetime.fromisoformat((p.get("out_at") or _now()).replace("Z", "+00:00"))
                    hrs = (b - a).total_seconds() / 3600.0
                except Exception:
                    pass
            out.append({
                "date": date_str, "pings": cnt,
                "in_at": (p or {}).get("in_at"), "out_at": (p or {}).get("out_at"),
                "working_hours": _round(hrs, 2),
            })
        return {"data": out}

    # =========================================================================
    # OWNER — Complete User Management + Impersonation (Phase 1)
    # =========================================================================
    OWNER_MANAGEABLE_ROLES = [
        "owner_accountant", "distributor", "distributor_accountant",
        "retailer", "salesperson", "team_leader", "regional_manager",
    ]

    def _is_online(u: dict) -> bool:
        """A user is considered online if last activity ping / login was <5min ago."""
        last = u.get("last_login_at") or u.get("last_active_at")
        if not last:
            return False
        try:
            dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            return (datetime.now(timezone.utc) - dt).total_seconds() < 300
        except Exception:
            return False

    @router.get("/owner/users")
    async def owner_list_users(role: Optional[str] = None, user: dict = Depends(owner_only)):
        q: Dict[str, Any] = {"tenant_id": DMS_TENANT_ID}
        if role:
            q["role"] = role
        docs = await db.users.find(q, {"_id": 0, "password_hash": 0}).sort("role", 1).to_list(2000)
        for u in docs:
            u["online"] = _is_online(u)
        return {"data": docs, "count": len(docs)}

    @router.post("/owner/users")
    async def owner_create_user(body: Dict[str, Any] = Body(...), user: dict = Depends(owner_only)):
        import bcrypt
        for k in ("email", "password", "name", "role"):
            if not body.get(k):
                raise HTTPException(status_code=400, detail=f"{k} required")
        role = body["role"]
        if role not in OWNER_MANAGEABLE_ROLES:
            raise HTTPException(status_code=400, detail=f"Cannot create role={role} from owner panel")
        email = body["email"].lower().strip()
        if await db.users.find_one({"email": email}):
            raise HTTPException(status_code=400, detail=f"Email {email} already exists")
        uid = _nid("usr")
        doc = {
            "id": uid,
            "tenant_id": DMS_TENANT_ID,
            "email": email,
            "name": body["name"],
            "role": role,
            "phone": body.get("phone", ""),
            "password_hash": bcrypt.hashpw(body["password"].encode(), bcrypt.gensalt()).decode(),
            "active": True,
            "created_at": _now(),
            "avatar": "".join([w[0] for w in body["name"].split()[:2]]).upper(),
            "created_by": user["id"],
        }
        # optional linkage
        for k in ("distributor_id", "retailer_id"):
            if body.get(k):
                doc[k] = body[k]
        await db.users.insert_one(doc)
        doc.pop("password_hash", None)
        doc.pop("_id", None)
        return {"ok": True, "user": doc}

    @router.patch("/owner/users/{uid}")
    async def owner_update_user(uid: str, body: Dict[str, Any] = Body(...), user: dict = Depends(owner_only)):
        target = await db.users.find_one({"id": uid, "tenant_id": DMS_TENANT_ID})
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        updatable = {"name", "phone", "active", "distributor_id", "retailer_id"}
        upd = {k: v for k, v in body.items() if k in updatable}
        if not upd:
            raise HTTPException(status_code=400, detail="Nothing to update")
        await db.users.update_one({"id": uid}, {"$set": upd})
        return {"ok": True}

    @router.post("/owner/users/{uid}/reset-password")
    async def owner_reset_password(uid: str, body: Dict[str, Any] = Body(...), user: dict = Depends(owner_only)):
        import bcrypt
        new_pw = (body.get("new_password") or "").strip()
        if len(new_pw) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        target = await db.users.find_one({"id": uid, "tenant_id": DMS_TENANT_ID})
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        await db.users.update_one(
            {"id": uid},
            {"$set": {"password_hash": bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()}},
        )
        return {"ok": True}

    @router.post("/owner/impersonate/{uid}")
    async def owner_impersonate(uid: str, user: dict = Depends(owner_only)):
        target = await db.users.find_one({"id": uid, "tenant_id": DMS_TENANT_ID}, {"_id": 0, "password_hash": 0})
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        if target.get("role") == "owner":
            raise HTTPException(status_code=400, detail="Cannot impersonate another owner")
        import jwt as _jwt, os as _os
        payload = {
            "sub": target["id"], "email": target["email"], "role": target["role"],
            "tenant_id": target.get("tenant_id"),
            "exp": datetime.now(timezone.utc) + timedelta(hours=2),
            "type": "access",
            "impersonated_by": user["id"],
        }
        tok = _jwt.encode(payload, _os.environ["JWT_SECRET"], algorithm="HS256")
        return {"token": tok, "user": target, "impersonated_by": {"id": user["id"], "name": user.get("name"), "email": user.get("email")}}

    # =========================================================================
    # COUPON MANAGEMENT — Distributor-based security (Phase 7)
    # =========================================================================
    async def _next_coupon_serial() -> int:
        """Global sequential CPN000001+ serial. Reads from meta counter."""
        c = await db.dms_meta.find_one_and_update(
            {"key": "coupon_counter"},
            {"$inc": {"value": 1}},
            upsert=True, return_document=True,
        )
        return int((c or {}).get("value", 1))

    def _coupon_code(n: int) -> str:
        return f"CPN{n:06d}"

    @router.post("/owner/coupons/generate")
    async def gen_coupons(body: Dict[str, Any] = Body(...), user: dict = Depends(owner_only)):
        """Generate N unused coupons for a product. Returns start_code + end_code + batch_id."""
        pid = body.get("product_id")
        count = int(body.get("count", 0) or 0)
        if not pid or count <= 0:
            raise HTTPException(status_code=400, detail="product_id and positive count required")
        if count > 100000:
            raise HTTPException(status_code=400, detail="Max 100,000 coupons per batch")
        prod = await db.dms_products.find_one({"id": pid}, {"_id": 0, "name": 1, "points_value": 1})
        if not prod:
            raise HTTPException(status_code=404, detail="Product not found")
        pts = _round(prod.get("points_value", 10))
        batch_id = _nid("cbt")
        docs = []
        first_n = None; last_n = None
        for _ in range(count):
            n = await _next_coupon_serial()
            if first_n is None: first_n = n
            last_n = n
            docs.append({
                "id": _nid("cpn"),
                "coupon_code": _coupon_code(n),
                "batch_id": batch_id,
                "product_id": pid,
                "product_name": prod.get("name"),
                "assigned_distributor_id": None,
                "assigned_distributor_name": None,
                "assigned_on": None,
                "status": "unused",
                "redeemed_by_retailer_id": None,
                "redeemed_at": None,
                "points_value": pts,
                "created_at": _now(),
            })
        if docs:
            await db.dms_coupons.insert_many(docs)
        # store batch meta
        await db.dms_coupon_batches.insert_one({
            "id": batch_id,
            "product_id": pid,
            "product_name": prod.get("name"),
            "count": count,
            "start_code": _coupon_code(first_n) if first_n else None,
            "end_code": _coupon_code(last_n) if last_n else None,
            "created_by": user["id"],
            "created_at": _now(),
        })
        return {"ok": True, "batch_id": batch_id, "count": count,
                "start_code": docs[0]["coupon_code"] if docs else None,
                "end_code": docs[-1]["coupon_code"] if docs else None}

    @router.get("/owner/coupons")
    async def owner_list_coupons(
        status: Optional[str] = None,
        product_id: Optional[str] = None,
        distributor_id: Optional[str] = None,
        retailer_id: Optional[str] = None,
        limit: int = 200,
        user: dict = Depends(owner_only),
    ):
        q: Dict[str, Any] = {}
        if status: q["status"] = status
        if product_id: q["product_id"] = product_id
        if distributor_id: q["assigned_distributor_id"] = distributor_id
        if retailer_id: q["redeemed_by_retailer_id"] = retailer_id
        docs = await db.dms_coupons.find(q, {"_id": 0}).sort("created_at", -1).limit(min(limit, 1000)).to_list(1000)
        return {"data": docs, "count": len(docs)}

    @router.get("/owner/coupons/batches")
    async def owner_coupon_batches(user: dict = Depends(owner_only)):
        docs = await db.dms_coupon_batches.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
        return {"data": docs}

    # ── Retailer scan (redeem) ──
    @router.post("/retailer/coupons/scan")
    async def retailer_scan_coupon(body: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        if user.get("role") != "retailer":
            raise HTTPException(status_code=403, detail="Only retailers can scan coupons")
        code = (body.get("coupon_code") or "").strip().upper()
        if not code:
            raise HTTPException(status_code=400, detail="coupon_code required")
        # my retailer + distributor
        ret = await db.dms_retailers.find_one({"id": user.get("retailer_id")}, {"_id": 0}) if user.get("retailer_id") else None
        if not ret:
            ret = await db.dms_retailers.find_one({"user_id": user["id"]}, {"_id": 0})
        if not ret:
            raise HTTPException(status_code=400, detail="Retailer profile not found for this user")
        my_did = ret.get("distributor_id")

        cp = await db.dms_coupons.find_one({"coupon_code": code}, {"_id": 0})

        async def _log_fraud(reason: str, coupon_owner_did: Optional[str] = None):
            await db.dms_coupon_fraud_attempts.insert_one({
                "id": _nid("fra"),
                "coupon_code": code,
                "attempted_by_retailer_id": ret["id"],
                "attempted_by_retailer_name": ret.get("name"),
                "attempted_by_retailer_distributor_id": my_did,
                "coupon_owner_distributor_id": coupon_owner_did,
                "reason": reason,
                "at": _now(),
            })

        if not cp:
            await _log_fraud("invalid_code")
            raise HTTPException(status_code=400, detail="Invalid coupon code")
        if cp.get("status") == "redeemed":
            await _log_fraud("already_redeemed", cp.get("assigned_distributor_id"))
            raise HTTPException(status_code=400, detail=f"Coupon already redeemed on {cp.get('redeemed_at','')[:10]}")
        if not cp.get("assigned_distributor_id"):
            await _log_fraud("not_dispatched")
            raise HTTPException(status_code=400, detail="Coupon not dispatched yet — cannot redeem")
        if cp["assigned_distributor_id"] != my_did:
            await _log_fraud("distributor_mismatch", cp.get("assigned_distributor_id"))
            raise HTTPException(status_code=403, detail="This coupon does not belong to your distributor network.")

        # redeem — mark coupon redeemed
        coupon_value = _round(cp.get("points_value", 0))
        await db.dms_coupons.update_one(
            {"id": cp["id"]},
            {"$set": {
                "status": "redeemed",
                "redeemed_by_retailer_id": ret["id"],
                "redeemed_by_retailer_name": ret.get("name"),
                "redeemed_at": _now(),
                "redemption_channel": "retailer",
            }},
        )
        # Ledger credit — retailer's outstanding to distributor reduces by coupon value
        if coupon_value > 0 and my_did:
            await db.dms_retailer_ledger.insert_one({
                "id": _nid("rle"),
                "distributor_id": my_did,
                "retailer_id": ret["id"],
                "kind": "coupon_credit",
                "reference_no": f"CPN-{cp['coupon_code']}",
                "amount": coupon_value,
                "method": "coupon_redemption",
                "description": f"Coupon {cp['coupon_code']} redeemed — {cp.get('product_name', '')}",
                "at": _now(),
                "recorded_by": user["id"],
            })
        return {
            "ok": True,
            "coupon_code": cp["coupon_code"],
            "product_name": cp.get("product_name"),
            "points_value": coupon_value,
            "credit_amount": coupon_value,
            "message": f"₹{coupon_value:,.0f} credited to your ledger against your distributor.",
        }

    # ── Distributor scan coupon — same mechanic, credits Owner ledger ──
    @router.post("/distributor/coupons/scan")
    async def distributor_scan_coupon(body: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        if user.get("role") not in ("distributor", "distributor_accountant"):
            raise HTTPException(status_code=403, detail="Only distributors can scan coupons")
        code = (body.get("coupon_code") or "").strip().upper()
        if not code:
            raise HTTPException(status_code=400, detail="coupon_code required")
        my_did = user.get("distributor_id")
        if not my_did:
            raise HTTPException(status_code=400, detail="Distributor profile not linked to this user")

        cp = await db.dms_coupons.find_one({"coupon_code": code}, {"_id": 0})
        if not cp:
            raise HTTPException(status_code=400, detail="Invalid coupon code")
        if cp.get("status") == "redeemed":
            raise HTTPException(status_code=400, detail=f"Coupon already redeemed on {cp.get('redeemed_at','')[:10]}")
        if not cp.get("assigned_distributor_id"):
            raise HTTPException(status_code=400, detail="Coupon not dispatched yet")
        if cp["assigned_distributor_id"] != my_did:
            raise HTTPException(status_code=403, detail="This coupon does not belong to you.")

        coupon_value = _round(cp.get("points_value", 0))
        await db.dms_coupons.update_one(
            {"id": cp["id"]},
            {"$set": {
                "status": "redeemed",
                "redeemed_by_distributor_id": my_did,
                "redeemed_at": _now(),
                "redemption_channel": "distributor",
            }},
        )
        # Ledger credit — distributor's outstanding to owner reduces by coupon value
        if coupon_value > 0:
            await db.dms_primary_ledger.insert_one({
                "id": _nid("le"),
                "distributor_id": my_did,
                "kind": "coupon_credit",
                "reference_no": f"CPN-{cp['coupon_code']}",
                "amount": coupon_value,
                "method": "coupon_redemption",
                "description": f"Coupon {cp['coupon_code']} redeemed — {cp.get('product_name', '')}",
                "at": _now(),
                "recorded_by": user["id"],
            })
        return {
            "ok": True,
            "coupon_code": cp["coupon_code"],
            "product_name": cp.get("product_name"),
            "credit_amount": coupon_value,
            "message": f"₹{coupon_value:,.0f} credited to your ledger against Owner.",
        }

    @router.get("/retailer/coupons/my-history")
    async def retailer_coupon_history(user: dict = Depends(get_current_user)):
        if user.get("role") != "retailer":
            raise HTTPException(status_code=403, detail="Retailers only")
        ret = await db.dms_retailers.find_one({"id": user.get("retailer_id")}, {"_id": 0}) if user.get("retailer_id") else await db.dms_retailers.find_one({"user_id": user["id"]}, {"_id": 0})
        if not ret:
            return {"data": [], "total_points": 0}
        docs = await db.dms_coupons.find({"redeemed_by_retailer_id": ret["id"]}, {"_id": 0}).sort("redeemed_at", -1).to_list(500)
        return {"data": docs, "total_points": _round(sum(c.get("points_value", 0) for c in docs))}

    # ── Reports for Owner ──
    @router.get("/owner/coupons/reports/summary")
    async def coupons_report_summary(user: dict = Depends(owner_only)):
        """Returns totals + distributor-wise + retailer-wise + unused + fraud counts."""
        total = await db.dms_coupons.count_documents({})
        unused = await db.dms_coupons.count_documents({"status": "unused"})
        assigned = await db.dms_coupons.count_documents({"status": "assigned"})
        redeemed = await db.dms_coupons.count_documents({"status": "redeemed"})

        # distributor-wise
        by_dist: Dict[str, Dict[str, Any]] = {}
        async for c in db.dms_coupons.find({"assigned_distributor_id": {"$ne": None}}, {"_id": 0}):
            did = c["assigned_distributor_id"]
            row = by_dist.setdefault(did, {
                "distributor_id": did,
                "distributor_name": c.get("assigned_distributor_name"),
                "assigned": 0, "redeemed": 0, "points_redeemed": 0.0,
            })
            row["assigned"] += 1
            if c.get("status") == "redeemed":
                row["redeemed"] += 1
                row["points_redeemed"] += c.get("points_value", 0)

        # retailer-wise (redemptions)
        by_ret: Dict[str, Dict[str, Any]] = {}
        async for c in db.dms_coupons.find({"redeemed_by_retailer_id": {"$ne": None}}, {"_id": 0}):
            rid = c["redeemed_by_retailer_id"]
            row = by_ret.setdefault(rid, {
                "retailer_id": rid,
                "retailer_name": c.get("redeemed_by_retailer_name"),
                "redeemed": 0, "points": 0.0,
            })
            row["redeemed"] += 1
            row["points"] += c.get("points_value", 0)

        # fraud count
        fraud = await db.dms_coupon_fraud_attempts.count_documents({})

        return {
            "totals": {
                "total": total, "unused": unused, "assigned": assigned,
                "redeemed": redeemed, "fraud_attempts": fraud,
            },
            "by_distributor": sorted(by_dist.values(), key=lambda r: r["redeemed"], reverse=True),
            "by_retailer": sorted(by_ret.values(), key=lambda r: r["redeemed"], reverse=True),
        }

    @router.get("/owner/coupons/reports/fraud")
    async def coupons_fraud(user: dict = Depends(owner_only)):
        docs = await db.dms_coupon_fraud_attempts.find({}, {"_id": 0}).sort("at", -1).to_list(500)
        return {"data": docs, "count": len(docs)}

    @router.get("/owner/coupons/reports/history")
    async def coupons_history(user: dict = Depends(owner_only)):
        docs = await db.dms_coupons.find({"status": "redeemed"}, {"_id": 0}).sort("redeemed_at", -1).limit(500).to_list(500)
        return {"data": docs, "count": len(docs)}

    # =========================================================================
    # PRODUCTS — Excel Import / Export (Owner)
    # =========================================================================
    @router.get("/owner/products/export")
    async def export_products(user: dict = Depends(owner_only)):
        from openpyxl import Workbook
        from io import BytesIO
        from fastapi.responses import Response
        wb = Workbook()
        ws = wb.active
        ws.title = "Products"
        headers = ["sku_code", "name", "category_name", "description", "box_qty", "hsn", "gst_pct", "unit_price", "coupons_per_box", "points_value", "active"]
        ws.append(headers)
        cats = {c["id"]: c["name"] async for c in db.dms_categories.find({}, {"_id": 0, "id": 1, "name": 1})}
        async for p in db.dms_products.find({}, {"_id": 0}):
            ws.append([
                p.get("sku_code"), p.get("name"),
                cats.get(p.get("category_id"), ""),
                p.get("description", ""),
                p.get("box_qty", 0), p.get("hsn", ""),
                p.get("gst_pct", 18),
                p.get("unit_price", 0),
                p.get("coupons_per_box", 100),
                p.get("points_value", 10),
                bool(p.get("active", True)),
            ])
        # widen columns
        for col_letter in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]:
            ws.column_dimensions[col_letter].width = 18
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        return Response(
            content=buf.read(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="products_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'},
        )

    @router.post("/owner/products/import")
    async def import_products(file: UploadFile = File(...), user: dict = Depends(owner_only)):
        from openpyxl import load_workbook
        from io import BytesIO
        raw = await file.read()
        try:
            wb = load_workbook(BytesIO(raw), data_only=True)
            ws = wb.active
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Cannot read xlsx: {e}")
        # read headers
        header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), None)
        if not header_row:
            raise HTTPException(status_code=400, detail="Empty file")
        headers = [str(h or "").strip().lower() for h in header_row]
        col = {h: i for i, h in enumerate(headers)}
        required = ["sku_code", "name", "category_name", "box_qty", "unit_price"]
        for req in required:
            if req not in col:
                raise HTTPException(status_code=400, detail=f"Missing required column: {req}")

        # cache category id map
        cats = {c["name"].strip().lower(): c["id"] async for c in db.dms_categories.find({}, {"_id": 0, "name": 1, "id": 1})}

        created, updated, skipped, errors = 0, 0, 0, []
        for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or all(v is None or v == "" for v in row):
                continue
            try:
                sku = (str(row[col["sku_code"]]) if row[col["sku_code"]] is not None else "").strip()
                name = (str(row[col["name"]]) if row[col["name"]] is not None else "").strip()
                cat_name = (str(row[col["category_name"]]) if row[col["category_name"]] is not None else "").strip()
                if not sku or not name or not cat_name:
                    skipped += 1; errors.append(f"Row {i}: missing sku/name/category"); continue
                cat_id = cats.get(cat_name.lower())
                if not cat_id:
                    # auto-create category
                    cid = _nid("cat")
                    await db.dms_categories.insert_one({"id": cid, "name": cat_name, "created_at": _now()})
                    cats[cat_name.lower()] = cid
                    cat_id = cid
                box_qty = int(row[col["box_qty"]] or 0)
                unit_price = float(row[col["unit_price"]] or 0)
                gst = float(row[col.get("gst_pct", -1)] if "gst_pct" in col and row[col["gst_pct"]] is not None else 18)
                hsn = str(row[col.get("hsn", -1)] or "") if "hsn" in col else ""
                desc = str(row[col.get("description", -1)] or "") if "description" in col else ""
                per_box = int(row[col["coupons_per_box"]] or 100) if "coupons_per_box" in col and row[col["coupons_per_box"]] is not None else 100
                points = float(row[col["points_value"]] or 10) if "points_value" in col and row[col["points_value"]] is not None else 10
                active = bool(row[col["active"]]) if "active" in col and row[col["active"]] is not None else True

                existing = await db.dms_products.find_one({"sku_code": sku}, {"_id": 0})
                if existing:
                    upd = {
                        "name": name, "category_id": cat_id, "description": desc,
                        "box_qty": box_qty, "hsn": hsn, "gst_pct": _round(gst),
                        "coupons_per_box": per_box, "points_value": _round(points),
                        "active": active, "updated_at": _now(),
                    }
                    if float(existing.get("unit_price", 0)) != unit_price:
                        # price change → close previous batch, open new (same as PUT path)
                        await db.dms_price_batches.update_one({"product_id": existing["id"], "to_date": None}, {"$set": {"to_date": _now()}})
                        await db.dms_price_batches.insert_one({
                            "id": _nid("pb"), "product_id": existing["id"], "price": _round(unit_price),
                            "from_date": _now(), "to_date": None, "created_at": _now(),
                        })
                        upd["previous_price"] = existing.get("unit_price")
                        upd["unit_price"] = _round(unit_price)
                    await db.dms_products.update_one({"id": existing["id"]}, {"$set": upd})
                    updated += 1
                else:
                    pid = _nid("prd")
                    await db.dms_products.insert_one({
                        "id": pid, "name": name, "category_id": cat_id, "sku_code": sku,
                        "description": desc, "box_qty": box_qty, "unit_price": _round(unit_price),
                        "previous_price": None, "hsn": hsn, "gst_pct": _round(gst),
                        "coupons_per_box": per_box, "points_value": _round(points),
                        "active": active, "created_at": _now(),
                    })
                    await db.dms_price_batches.insert_one({
                        "id": _nid("pb"), "product_id": pid, "price": _round(unit_price),
                        "from_date": _now(), "to_date": None, "created_at": _now(),
                    })
                    created += 1
            except Exception as e:
                skipped += 1
                errors.append(f"Row {i}: {e}")

        return {"ok": True, "created": created, "updated": updated, "skipped": skipped, "errors": errors[:20]}

    # =========================================================================
    # SUPER ADMIN — login-as (impersonation)
    # =========================================================================
    @router.get("/admin/users")
    async def admin_list_users(user: dict = Depends(get_current_user)):
        if user["role"] not in ("super_admin", "owner"):
            raise HTTPException(status_code=403, detail="Owner only")
        docs = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
        return {"data": docs}

    @router.post("/admin/impersonate/{uid}")
    async def impersonate(uid: str, user: dict = Depends(get_current_user)):
        if user["role"] not in ("super_admin", "owner"):
            raise HTTPException(status_code=403, detail="Owner only")
        target = await db.users.find_one({"id": uid}, {"_id": 0, "password_hash": 0})
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        # Generate a token for the target user (super_admin origin recorded)
        import jwt as _jwt, os as _os
        payload = {
            "sub": target["id"], "email": target["email"], "role": target["role"],
            "tenant_id": target.get("tenant_id"),
            "exp": datetime.now(timezone.utc) + timedelta(hours=2),
            "type": "access",
            "impersonated_by": user["id"],
        }
        tok = _jwt.encode(payload, _os.environ["JWT_SECRET"], algorithm="HS256")
        return {"token": tok, "user": target}

    # =========================================================================
    # PRINTABLE E-BILL / RETAILER BILL data
    # =========================================================================
    @router.get("/print/ebill/{ebill_id}")
    async def print_ebill(ebill_id: str, user: dict = Depends(get_current_user)):
        eb = await db.dms_ebills.find_one({"id": ebill_id}, {"_id": 0})
        if not eb:
            raise HTTPException(status_code=404, detail="e-Bill not found")
        # RBAC
        role = user.get("role")
        if role in ("distributor", "distributor_accountant") and eb["distributor_id"] != user.get("distributor_id"):
            raise HTTPException(status_code=403, detail="Forbidden")
        dist = await db.dms_distributors.find_one({"id": eb["distributor_id"]}, {"_id": 0})
        eb["distributor"] = dist
        # Phase 2A: expose invoice T&C / message from global settings
        s = await db.dms_settings.find_one({"id": "global"}, {"_id": 0, "invoice_terms": 1, "invoice_message": 1, "company_name": 1}) or {}
        eb["invoice_terms"] = s.get("invoice_terms") or ""
        eb["invoice_message"] = s.get("invoice_message") or ""
        eb["company_name"] = s.get("company_name") or "GO OIL Lubricants"
        return eb

    @router.get("/print/retailer-bill/{bill_id}")
    async def print_retailer_bill(bill_id: str, user: dict = Depends(get_current_user)):
        b = await db.dms_retailer_bills.find_one({"id": bill_id}, {"_id": 0})
        if not b:
            raise HTTPException(status_code=404, detail="Bill not found")
        role = user.get("role")
        if role == "retailer" and b["retailer_id"] != user.get("retailer_id"):
            raise HTTPException(status_code=403, detail="Forbidden")
        if role in ("distributor", "distributor_accountant") and b["distributor_id"] != user.get("distributor_id"):
            raise HTTPException(status_code=403, detail="Forbidden")
        retailer = await db.dms_retailers.find_one({"id": b["retailer_id"]}, {"_id": 0})
        distributor = await db.dms_distributors.find_one({"id": b["distributor_id"]}, {"_id": 0})
        b["retailer"] = retailer
        b["distributor"] = distributor
        # Phase 2A: expose invoice T&C / message from global settings
        s = await db.dms_settings.find_one({"id": "global"}, {"_id": 0, "invoice_terms": 1, "invoice_message": 1, "company_name": 1}) or {}
        b["invoice_terms"] = s.get("invoice_terms") or ""
        b["invoice_message"] = s.get("invoice_message") or ""
        b["company_name"] = s.get("company_name") or "GO OIL Lubricants"
        return b

    # =========================================================================
    # SETTINGS  (global — GST % is configured here; default 0)
    # =========================================================================
    async def _get_settings() -> Dict[str, Any]:
        doc = await db.dms_settings.find_one({"id": "global"}, {"_id": 0})
        if not doc:
            doc = {"id": "global", "gst_pct": 0.0, "company_name": "GO OIL Lubricants", "updated_at": _now()}
            await db.dms_settings.insert_one(doc)
        return doc

    @router.get("/settings")
    async def get_settings(user: dict = Depends(get_current_user)):
        s = await _get_settings()
        return _clean(s)

    @router.put("/settings")
    async def update_settings(body: Dict[str, Any] = Body(...), user: dict = Depends(owner_only)):
        upd: Dict[str, Any] = {}
        if "gst_pct" in body:
            try:
                gst = float(body["gst_pct"])
            except Exception:
                raise HTTPException(status_code=400, detail="gst_pct must be a number")
            if gst < 0 or gst > 100:
                raise HTTPException(status_code=400, detail="gst_pct must be between 0 and 100")
            upd["gst_pct"] = gst
        if "company_name" in body and isinstance(body["company_name"], str):
            upd["company_name"] = body["company_name"].strip() or "GO OIL Lubricants"
        # Phase 2A: invoice customization
        if "invoice_terms" in body:
            upd["invoice_terms"] = str(body.get("invoice_terms") or "").strip()
        if "invoice_message" in body:
            upd["invoice_message"] = str(body.get("invoice_message") or "").strip()
        # Phase 2A: Financial Year lock date (YYYY-MM-DD). Can only move forward.
        if "fy_lock_date" in body:
            lock = str(body.get("fy_lock_date") or "").strip()
            if lock:
                try:
                    datetime.strptime(lock, "%Y-%m-%d")
                except Exception:
                    raise HTTPException(status_code=400, detail="fy_lock_date must be YYYY-MM-DD")
                cur = await _get_settings()
                cur_lock = cur.get("fy_lock_date") or ""
                if cur_lock and lock < cur_lock:
                    raise HTTPException(status_code=400, detail=f"fy_lock_date can only move forward (current: {cur_lock})")
            upd["fy_lock_date"] = lock or None
        upd["updated_at"] = _now()
        await db.dms_settings.update_one({"id": "global"}, {"$set": upd}, upsert=True)
        s = await _get_settings()
        return _clean(s)

    # -- Financial year lock helper -----------------------------------------
    async def _fy_lock_date() -> Optional[str]:
        s = await db.dms_settings.find_one({"id": "global"}, {"_id": 0, "fy_lock_date": 1}) or {}
        return s.get("fy_lock_date")

    async def _check_fy_lock(entity_date_iso: Optional[str], what: str = "record") -> None:
        """Raise 400 if entity's date is on/before the FY lock date. Accepts ISO datetime or YYYY-MM-DD."""
        lock = await _fy_lock_date()
        if not lock or not entity_date_iso:
            return
        try:
            d = entity_date_iso[:10]
        except Exception:
            return
        if d <= lock:
            raise HTTPException(status_code=400, detail=f"Financial year locked (up to {lock}); {what} on {d} cannot be modified")

    @router.post("/finance/fy-close")
    async def fy_close(body: Dict[str, Any] = Body(...), user: dict = Depends(owner_only)):
        """Close (lock) the financial year up to a given date. Alias of PUT /settings with fy_lock_date."""
        lock = str(body.get("lock_date") or "").strip()
        if not lock:
            raise HTTPException(status_code=400, detail="lock_date required (YYYY-MM-DD)")
        try:
            datetime.strptime(lock, "%Y-%m-%d")
        except Exception:
            raise HTTPException(status_code=400, detail="lock_date must be YYYY-MM-DD")
        cur = await _get_settings()
        cur_lock = cur.get("fy_lock_date") or ""
        if cur_lock and lock < cur_lock:
            raise HTTPException(status_code=400, detail=f"lock_date can only move forward (current: {cur_lock})")
        await db.dms_settings.update_one({"id": "global"}, {"$set": {"fy_lock_date": lock, "fy_locked_at": _now(), "fy_locked_by": user["id"], "updated_at": _now()}}, upsert=True)
        return {"ok": True, "fy_lock_date": lock}

    # =========================================================================
    # EXPENSES  (Phase 2A) — CRUD for all roles except retailer
    # =========================================================================
    def _exp_can_view(role: str) -> bool:
        return role in ("owner", "owner_accountant", "super_admin", "distributor", "distributor_accountant", "salesperson", "team_leader", "regional_manager")

    def _exp_all_visible_roles() -> tuple:
        return ("owner", "owner_accountant", "super_admin")

    @router.get("/expenses")
    async def list_expenses(user: dict = Depends(get_current_user), start: Optional[str] = None, end: Optional[str] = None, category: Optional[str] = None):
        role = user.get("role")
        if role == "retailer":
            raise HTTPException(status_code=403, detail="Forbidden")
        q: Dict[str, Any] = {}
        if role not in _exp_all_visible_roles():
            q["created_by"] = user["id"]
        if start:
            q["date"] = q.get("date", {}); q["date"]["$gte"] = start
        if end:
            q["date"] = q.get("date", {}); q["date"]["$lte"] = end
        if category:
            q["category"] = category
        docs = await db.dms_expenses.find(q, {"_id": 0}).sort("date", -1).to_list(1000)
        # summary
        total = sum(float(d.get("amount", 0)) for d in docs)
        # enrich creator names
        ids = list({d.get("created_by") for d in docs if d.get("created_by")})
        name_map = {}
        if ids:
            async for u in db.users.find({"id": {"$in": ids}}, {"_id": 0, "id": 1, "name": 1, "role": 1}):
                name_map[u["id"]] = {"name": u.get("name"), "role": u.get("role")}
        for d in docs:
            u = name_map.get(d.get("created_by") or "")
            if u:
                d["created_by_name"] = u.get("name")
                d["created_by_role"] = d.get("created_by_role") or u.get("role")
        return {"data": docs, "count": len(docs), "total": _round(total)}

    @router.post("/expenses")
    async def create_expense(body: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        role = user.get("role")
        if role == "retailer":
            raise HTTPException(status_code=403, detail="Forbidden")
        category = str(body.get("category") or "").strip()
        try:
            amount = float(body.get("amount") or 0)
        except Exception:
            raise HTTPException(status_code=400, detail="amount must be a number")
        if not category or amount <= 0:
            raise HTTPException(status_code=400, detail="category and amount>0 required")
        date = str(body.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d"))[:10]
        # Enforce FY lock on backdated new entries
        await _check_fy_lock(date, "expense")
        seq = await db.dms_expenses.count_documents({}) + 1
        doc = {
            "id": _nid("exp"),
            "expense_no": body.get("expense_no") or f"EXP-{80000 + seq}",
            "category": category,
            "amount": _round(amount),
            "date": date,
            "description": str(body.get("description") or "").strip(),
            "vendor": str(body.get("vendor") or "").strip(),
            "receipt_url": str(body.get("receipt_url") or "").strip() or None,
            "status": body.get("status") or "Approved",
            "created_by": user["id"],
            "created_by_role": role,
            "created_at": _now(),
        }
        await db.dms_expenses.insert_one(doc)
        return _clean(doc)

    @router.put("/expenses/{eid}")
    async def update_expense(eid: str, body: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        role = user.get("role")
        if role == "retailer":
            raise HTTPException(status_code=403, detail="Forbidden")
        doc = await db.dms_expenses.find_one({"id": eid}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Expense not found")
        # only creator OR owner/accountant can edit
        if role not in _exp_all_visible_roles() and doc.get("created_by") != user["id"]:
            raise HTTPException(status_code=403, detail="You can only edit your own expenses")
        # FY lock on existing date AND on new date
        await _check_fy_lock(doc.get("date"), "expense")
        upd: Dict[str, Any] = {}
        for f in ("category", "description", "vendor", "receipt_url", "status", "expense_no"):
            if f in body:
                upd[f] = str(body[f] or "").strip() or None
        if "amount" in body:
            try:
                amt = float(body["amount"])
                if amt <= 0:
                    raise ValueError()
                upd["amount"] = _round(amt)
            except Exception:
                raise HTTPException(status_code=400, detail="amount must be a positive number")
        if "date" in body:
            new_date = str(body["date"] or "")[:10]
            await _check_fy_lock(new_date, "expense")
            upd["date"] = new_date
        upd["updated_at"] = _now()
        upd["updated_by"] = user["id"]
        await db.dms_expenses.update_one({"id": eid}, {"$set": upd})
        doc.update(upd)
        return _clean(doc)

    @router.delete("/expenses/{eid}")
    async def delete_expense(eid: str, user: dict = Depends(get_current_user)):
        role = user.get("role")
        if role not in _exp_all_visible_roles():
            raise HTTPException(status_code=403, detail="Only Owner/Accountant can delete expenses")
        doc = await db.dms_expenses.find_one({"id": eid}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Expense not found")
        await _check_fy_lock(doc.get("date"), "expense")
        await db.dms_expenses.delete_one({"id": eid})
        return {"ok": True, "id": eid}

    @router.get("/expenses/categories")
    async def expense_categories(user: dict = Depends(get_current_user)):
        if user.get("role") == "retailer":
            raise HTTPException(status_code=403, detail="Forbidden")
        # distinct categories used
        seen = set()
        async for d in db.dms_expenses.find({}, {"_id": 0, "category": 1}):
            c = (d.get("category") or "").strip()
            if c:
                seen.add(c)
        # baseline defaults
        for c in ("Transport", "Fuel", "Warehouse Rent", "Salaries", "Marketing", "Utilities", "Repairs", "Travel", "Office Supplies", "Miscellaneous"):
            seen.add(c)
        return {"data": sorted(seen)}

    # =========================================================================
    # INVOICE/BILL NUMBER OVERRIDE (Phase 2A) — Owner/Accountant/Distributor
    # =========================================================================
    @router.put("/ebills/{ebid}/number")
    async def update_ebill_number(ebid: str, body: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        role = user.get("role")
        if role not in ("owner", "owner_accountant", "super_admin"):
            raise HTTPException(status_code=403, detail="Forbidden")
        new_no = str(body.get("ebill_no") or "").strip()
        if not new_no:
            raise HTTPException(status_code=400, detail="ebill_no required")
        eb = await db.dms_ebills.find_one({"id": ebid}, {"_id": 0})
        if not eb:
            raise HTTPException(status_code=404, detail="e-Bill not found")
        await _check_fy_lock(eb.get("created_at"), "e-Bill")
        dup = await db.dms_ebills.find_one({"ebill_no": new_no, "id": {"$ne": ebid}}, {"_id": 0, "id": 1})
        if dup:
            raise HTTPException(status_code=400, detail="ebill_no already used")
        await db.dms_ebills.update_one({"id": ebid}, {"$set": {"ebill_no": new_no, "ebill_no_edited_at": _now(), "ebill_no_edited_by": user["id"]}})
        return {"ok": True, "id": ebid, "ebill_no": new_no}

    @router.put("/retailer-bills/{bid}/number")
    async def update_retailer_bill_number(bid: str, body: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        role = user.get("role")
        b = await db.dms_retailer_bills.find_one({"id": bid}, {"_id": 0})
        if not b:
            raise HTTPException(status_code=404, detail="Bill not found")
        if role not in ("owner", "owner_accountant", "super_admin") and not (role in ("distributor", "distributor_accountant") and user.get("distributor_id") == b.get("distributor_id")):
            raise HTTPException(status_code=403, detail="Forbidden")
        await _check_fy_lock(b.get("created_at"), "Bill")
        new_no = str(body.get("bill_no") or "").strip()
        if not new_no:
            raise HTTPException(status_code=400, detail="bill_no required")
        dup = await db.dms_retailer_bills.find_one({"bill_no": new_no, "id": {"$ne": bid}}, {"_id": 0, "id": 1})
        if dup:
            raise HTTPException(status_code=400, detail="bill_no already used")
        await db.dms_retailer_bills.update_one({"id": bid}, {"$set": {"bill_no": new_no, "bill_no_edited_at": _now(), "bill_no_edited_by": user["id"]}})
        return {"ok": True, "id": bid, "bill_no": new_no}

    # =========================================================================
    # PRICE CIRCULAR  (source-of-truth for pricing history; separate from Product Master)
    # =========================================================================
    @router.get("/price-circulars")
    async def list_price_circulars(user: dict = Depends(get_current_user)):
        headers = await db.dms_price_circulars.find(
            {"kind": {"$ne": "line"}}, {"_id": 0}
        ).sort([("batch_no", -1)]).to_list(500)
        # attach line counts
        for h in headers:
            h["lines_count"] = await db.dms_price_circulars.count_documents(
                {"kind": "line", "circular_id": h["id"]}
            )
        return {"data": headers, "count": len(headers)}

    @router.get("/price-circulars/{cid}")
    async def get_price_circular(cid: str, user: dict = Depends(get_current_user)):
        header = await db.dms_price_circulars.find_one({"id": cid}, {"_id": 0})
        if not header or header.get("kind") == "line":
            raise HTTPException(status_code=404, detail="Circular not found")
        lines = await db.dms_price_circulars.find(
            {"kind": "line", "circular_id": cid}, {"_id": 0}
        ).to_list(2000)
        # enrich with product info
        pids = [ln["product_id"] for ln in lines]
        prods = await db.dms_products.find({"id": {"$in": pids}}, {"_id": 0}).to_list(2000)
        pmap = {p["id"]: p for p in prods}
        cats = {c["id"]: c["name"] async for c in db.dms_categories.find({}, {"_id": 0, "id": 1, "name": 1})}
        for ln in lines:
            p = pmap.get(ln["product_id"], {})
            ln["material_description"] = p.get("material_description", p.get("name", ""))
            ln["grade_specs"] = p.get("grade_specs", "-")
            ln["pack_size"] = p.get("pack_size", "")
            ln["category_name"] = cats.get(p.get("category_id"), "")
        header["lines"] = lines
        return _clean(header)

    @router.post("/price-circulars")
    async def create_price_circular(body: Dict[str, Any] = Body(...), user: dict = Depends(owner_only)):
        """Create a new Price Circular batch.

        Body:
          title            : str  (required)
          effective_date   : YYYY-MM-DD (required)
          notes            : str  (optional)
          lines            : list of { product_id, mrp, dlp, distributor_margin_pct,
                                       cash_coupon, foc_benefits, monthly_gift, trade_discount }
                             (at least 1 required)

        Behaviour:
          - Deactivates ALL previous circular lines for the products included here.
          - Marks previous circular headers as inactive if they had lines only for these products.
          - Creates a new batch (auto batch_no = max+1).
          - Auto-updates product.previous_price = old DLP, product.unit_price = new DLP.
          - Closes any open dms_price_batches row and opens a new one — so old-vs-new price
            still works with existing order/browse logic.
          - Never deletes historical lines — full history preserved.
        """
        title = (body.get("title") or "").strip()
        eff_date = (body.get("effective_date") or "").strip()
        lines = body.get("lines") or []
        if not title:
            raise HTTPException(status_code=400, detail="title required")
        if not eff_date:
            raise HTTPException(status_code=400, detail="effective_date required")
        if not lines:
            raise HTTPException(status_code=400, detail="At least one line required")

        # next batch number
        latest = await db.dms_price_circulars.find_one(
            {"kind": {"$ne": "line"}},
            {"_id": 0, "batch_no": 1},
            sort=[("batch_no", -1)],
        )
        next_batch = int((latest or {}).get("batch_no", 0)) + 1
        circular_id = _nid("pcir")

        header_doc = {
            "id": circular_id,
            "tenant_id": DMS_TENANT_ID,
            "title": title,
            "effective_date": eff_date,
            "batch_no": next_batch,
            "batch_label": f"Batch {next_batch} — {title}",
            "is_active": True,
            "notes": (body.get("notes") or "").strip(),
            "created_by": user.get("id"),
            "created_at": _now(),
        }
        await db.dms_price_circulars.insert_one(header_doc)

        included_product_ids = []
        inserted_lines = 0
        for ln in lines:
            pid = ln.get("product_id")
            if not pid:
                continue
            product = await db.dms_products.find_one({"id": pid}, {"_id": 0})
            if not product:
                continue
            try:
                dlp = float(ln.get("dlp"))
            except Exception:
                raise HTTPException(status_code=400, detail=f"Invalid DLP for product {pid}")
            try:
                mrp = float(ln.get("mrp") or 0)
            except Exception:
                mrp = 0.0
            try:
                margin = float(ln.get("distributor_margin_pct") or 0)
            except Exception:
                margin = 0.0

            # Deactivate the previous active line for this product
            await db.dms_price_circulars.update_many(
                {"kind": "line", "product_id": pid, "is_active": True},
                {"$set": {"is_active": False, "deactivated_at": _now()}},
            )

            # New circular line
            await db.dms_price_circulars.insert_one({
                "id": _nid("pcl"),
                "tenant_id": DMS_TENANT_ID,
                "kind": "line",
                "circular_id": circular_id,
                "product_id": pid,
                "effective_date": eff_date,
                "batch_no": next_batch,
                "mrp": mrp,
                "dlp": dlp,
                "distributor_margin_pct": margin,
                "cash_coupon": (ln.get("cash_coupon") or "").strip(),
                "foc_benefits": (ln.get("foc_benefits") or "").strip(),
                "monthly_gift": (ln.get("monthly_gift") or "").strip(),
                "trade_discount": (ln.get("trade_discount") or "").strip(),
                "is_active": True,
                "created_at": _now(),
            })
            inserted_lines += 1
            included_product_ids.append(pid)

            # Also mirror new DLP into product.unit_price so existing order code works
            old_price = float(product.get("unit_price") or 0)
            if dlp != old_price:
                await db.dms_products.update_one(
                    {"id": pid},
                    {"$set": {"previous_price": old_price, "unit_price": dlp, "updated_at": _now()}},
                )
                # Close open legacy price-batch row + open a new one (for price-history endpoint)
                await db.dms_price_batches.update_one(
                    {"product_id": pid, "to_date": None},
                    {"$set": {"to_date": _now()}}
                )
                await db.dms_price_batches.insert_one({
                    "id": _nid("pb"),
                    "tenant_id": DMS_TENANT_ID,
                    "product_id": pid,
                    "price": dlp,
                    "from_date": _now(),
                    "to_date": None,
                    "created_at": _now(),
                    "circular_id": circular_id,
                    "batch_no": next_batch,
                })

        if inserted_lines == 0:
            # rollback header
            await db.dms_price_circulars.delete_one({"id": circular_id})
            raise HTTPException(status_code=400, detail="No valid product lines")

        header_doc["lines_count"] = inserted_lines
        return _clean(header_doc)

    @router.get("/products/{pid}/circular-history")
    async def product_circular_history(pid: str, user: dict = Depends(get_current_user)):
        """Full pricing history from all circulars for one product (latest first)."""
        rows = await db.dms_price_circulars.find(
            {"kind": "line", "product_id": pid}, {"_id": 0}
        ).sort([("batch_no", -1)]).to_list(500)
        # attach circular title
        cids = list({r["circular_id"] for r in rows})
        headers = await db.dms_price_circulars.find(
            {"id": {"$in": cids}, "kind": {"$ne": "line"}},
            {"_id": 0, "id": 1, "title": 1, "batch_label": 1}
        ).to_list(500)
        hmap = {h["id"]: h for h in headers}
        for r in rows:
            h = hmap.get(r["circular_id"], {})
            r["circular_title"] = h.get("title", "")
            r["batch_label"] = h.get("batch_label", "")
        return {"data": rows}

    @router.get("/price-circulars/{cid}/active-lines")
    async def circular_active_lines(cid: str, user: dict = Depends(get_current_user)):
        """Helper — for a specific circular, which lines are still the *current* active price."""
        lines = await db.dms_price_circulars.find(
            {"kind": "line", "circular_id": cid, "is_active": True}, {"_id": 0}
        ).to_list(2000)
        return {"data": lines, "count": len(lines)}

    return router
