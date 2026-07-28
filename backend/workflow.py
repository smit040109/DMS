"""GO OIL DMS — End-to-end business workflow engine.

Chain: Product → SKU → Batch → Company Inventory → Primary Order → Primary Invoice →
Dispatch → GIT → Distributor GRN → Distributor Inventory → Secondary Order →
Secondary Invoice → Secondary Dispatch → Retailer GRN → Retailer Inventory.

Every mutation:
  1. Runs validations (stock availability, credit limit, valid transitions).
  2. Updates inventory buckets (available / reserved / in_transit / damaged / returned / expired).
  3. Appends immutable rows to `stock_ledger`.
  4. Cascades state on the next-hop entity.

FIFO batch consumption is enforced at reservation time.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from fastapi import APIRouter, Depends, HTTPException, Body

# ---------- Utilities ----------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"

def strip_id(doc):
    if doc is None:
        return None
    doc.pop("_id", None)
    return doc

# ---------- State machines ----------

PRIMARY_ORDER_STATES = {"draft", "pending_approval", "approved", "partial", "rejected", "backorder", "invoiced", "dispatched", "delivered", "completed"}
SECONDARY_ORDER_STATES = {"draft", "pending_approval", "approved", "partial", "rejected", "invoiced", "dispatched", "delivered", "completed"}
INVOICE_STATES = {"issued", "dispatched", "delivered", "cancelled"}
DISPATCH_STATES = {"prepared", "in_transit", "delivered", "cancelled"}
GRN_STATES = {"pending", "accepted", "disputed"}
BATCH_STATES = {"pending_qc", "approved", "rejected", "stocked_in"}


# ==========================================================================
# Router factory: takes a database instance and returns a mounted APIRouter.
# ==========================================================================

def build_workflow_router(db, get_current_user):
    """Create workflow router. `db` = motor db, `get_current_user` = FastAPI dep."""
    router = APIRouter(prefix="/workflow", tags=["workflow"])

    # ---------------- Helper: stock ledger ----------------
    async def ledger_append(**kw):
        entry = {
            "id": new_id("led"),
            "timestamp": now_iso(),
            **kw,
        }
        await db.stock_ledger.insert_one(entry)
        return strip_id(entry)

    # ---------------- Helper: company inventory ops ----------------
    async def get_company_stock_by_sku(sku_id: str) -> Dict[str, int]:
        """Aggregate across all batches for a SKU."""
        totals = {"available": 0, "reserved": 0, "in_transit": 0, "damaged": 0, "returned": 0, "expired": 0}
        async for row in db.company_inventory.find({"sku_id": sku_id}, {"_id": 0}):
            for k in totals:
                totals[k] += int(row.get(k, 0) or 0)
        return totals

    async def reserve_fifo_company(sku_id: str, qty: int) -> List[Dict[str, Any]]:
        """Move qty from available -> reserved consuming oldest batches first.
        Returns list of {batch_id, qty} allocations. Raises if insufficient."""
        rows = await db.company_inventory.find({"sku_id": sku_id, "available": {"$gt": 0}}, {"_id": 0}).to_list(500)
        # sort by batch manufactured_on (older first)
        batch_ids = [r["batch_id"] for r in rows]
        batches = {}
        async for b in db.batches.find({"id": {"$in": batch_ids}}, {"_id": 0}):
            batches[b["id"]] = b
        rows.sort(key=lambda r: batches.get(r["batch_id"], {}).get("manufactured_on", ""))

        allocations = []
        need = qty
        for r in rows:
            if need <= 0:
                break
            take = min(r["available"], need)
            if take <= 0:
                continue
            await db.company_inventory.update_one(
                {"id": r["id"]},
                {"$inc": {"available": -take, "reserved": take}},
            )
            allocations.append({"batch_id": r["batch_id"], "qty": take})
            need -= take
        if need > 0:
            # Roll back
            for a in allocations:
                await db.company_inventory.update_one(
                    {"sku_id": sku_id, "batch_id": a["batch_id"]},
                    {"$inc": {"available": a["qty"], "reserved": -a["qty"]}},
                )
            raise HTTPException(status_code=400, detail=f"Insufficient stock for SKU {sku_id} — short by {need}")
        return allocations

    async def move_company_bucket(sku_id: str, batch_id: str, from_bucket: str, to_bucket: str, qty: int):
        r = await db.company_inventory.update_one(
            {"sku_id": sku_id, "batch_id": batch_id, from_bucket: {"$gte": qty}},
            {"$inc": {from_bucket: -qty, to_bucket: qty}},
        )
        if r.matched_count == 0:
            raise HTTPException(status_code=400, detail=f"Company bucket move failed: {from_bucket}→{to_bucket} sku={sku_id} batch={batch_id} qty={qty}")

    async def add_company_stock(sku_id: str, batch_id: str, warehouse_id: str, qty: int, sku_meta: dict):
        row = await db.company_inventory.find_one({"sku_id": sku_id, "batch_id": batch_id})
        if row:
            await db.company_inventory.update_one({"id": row["id"]}, {"$inc": {"available": qty}})
        else:
            await db.company_inventory.insert_one({
                "id": new_id("cinv"),
                "sku_id": sku_id, "sku_code": sku_meta.get("sku_code"),
                "product_name": sku_meta.get("product_name"),
                "pack_size": sku_meta.get("pack_size"),
                "batch_id": batch_id, "warehouse_id": warehouse_id,
                "available": qty, "reserved": 0, "in_transit": 0,
                "damaged": 0, "returned": 0, "expired": 0,
            })

    # ---------------- Helper: distributor & retailer inventory ----------------
    async def add_partner_stock(collection: str, partner_id: str, sku_id: str, batch_id: str, qty: int, sku_meta: dict):
        row = await db[collection].find_one({"partner_id": partner_id, "sku_id": sku_id, "batch_id": batch_id})
        if row:
            await db[collection].update_one({"id": row["id"]}, {"$inc": {"available": qty}})
        else:
            await db[collection].insert_one({
                "id": new_id(collection[:4]),
                "partner_id": partner_id, "sku_id": sku_id,
                "sku_code": sku_meta.get("sku_code"),
                "product_name": sku_meta.get("product_name"),
                "pack_size": sku_meta.get("pack_size"),
                "batch_id": batch_id,
                "available": qty, "reserved": 0, "in_transit": 0,
                "damaged": 0, "returned": 0, "expired": 0,
            })

    async def reserve_fifo_partner(collection: str, partner_id: str, sku_id: str, qty: int) -> List[Dict[str, Any]]:
        rows = await db[collection].find({"partner_id": partner_id, "sku_id": sku_id, "available": {"$gt": 0}}, {"_id": 0}).to_list(500)
        batch_ids = [r["batch_id"] for r in rows]
        batches = {}
        async for b in db.batches.find({"id": {"$in": batch_ids}}, {"_id": 0}):
            batches[b["id"]] = b
        rows.sort(key=lambda r: batches.get(r["batch_id"], {}).get("manufactured_on", ""))
        allocations = []
        need = qty
        for r in rows:
            if need <= 0: break
            take = min(r["available"], need)
            if take <= 0: continue
            await db[collection].update_one({"id": r["id"]}, {"$inc": {"available": -take, "reserved": take}})
            allocations.append({"batch_id": r["batch_id"], "qty": take})
            need -= take
        if need > 0:
            for a in allocations:
                await db[collection].update_one(
                    {"partner_id": partner_id, "sku_id": sku_id, "batch_id": a["batch_id"]},
                    {"$inc": {"available": a["qty"], "reserved": -a["qty"]}},
                )
            raise HTTPException(status_code=400, detail=f"Insufficient partner stock for SKU {sku_id} — short by {need}")
        return allocations

    async def move_partner_bucket(collection: str, partner_id: str, sku_id: str, batch_id: str, from_bucket: str, to_bucket: str, qty: int):
        r = await db[collection].update_one(
            {"partner_id": partner_id, "sku_id": sku_id, "batch_id": batch_id, from_bucket: {"$gte": qty}},
            {"$inc": {from_bucket: -qty, to_bucket: qty}},
        )
        if r.matched_count == 0:
            raise HTTPException(status_code=400, detail=f"Partner bucket move failed on {collection}: {from_bucket}→{to_bucket}")

    async def credit_check(entity_coll: str, entity_id: str, invoice_total: float) -> Dict[str, Any]:
        p = await db[entity_coll].find_one({"id": entity_id}, {"_id": 0})
        if not p:
            raise HTTPException(status_code=404, detail=f"{entity_coll} not found")
        limit = float(p.get("credit_limit", 0) or 0)
        outstanding = float(p.get("outstanding", 0) or 0)
        headroom = limit - outstanding
        ok = invoice_total <= headroom if limit > 0 else True
        return {"credit_limit": limit, "outstanding": outstanding, "headroom": headroom, "required": invoice_total, "ok": ok}

    # ==================================================================
    # 1) BATCHES  (Stock In)
    # ==================================================================
    @router.post("/batches")
    async def create_batch(payload: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        sku = await db.skus.find_one({"id": payload.get("sku_id")}, {"_id": 0})
        if not sku:
            raise HTTPException(status_code=400, detail="Invalid sku_id")
        batch = {
            "id": new_id("batch"),
            "batch_no": payload.get("batch_no") or f"B{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "sku_id": sku["id"], "sku_code": sku["sku_code"], "product_name": sku["product_name"],
            "pack_size": sku["pack_size"],
            "manufactured_on": payload.get("manufactured_on") or now_iso(),
            "expires_on": payload.get("expires_on") or now_iso(),
            "batch_quantity": int(payload.get("batch_quantity") or 0),
            "quantity": int(payload.get("batch_quantity") or 0),
            "quality_status": "Under Test",
            "status": "pending_qc",
            "warehouse_id": payload.get("warehouse_id"),
            "stocked_in": False,
            "created_at": now_iso(), "created_by": user.get("email"),
        }
        await db.batches.insert_one(batch)
        return strip_id(batch)

    @router.post("/batches/{batch_id}/qc-approve")
    async def qc_approve_batch(batch_id: str, user: dict = Depends(get_current_user)):
        b = await db.batches.find_one({"id": batch_id})
        if not b: raise HTTPException(404, "Batch not found")
        if b.get("status") == "stocked_in":
            raise HTTPException(400, "Already stocked in")
        await db.batches.update_one({"id": batch_id}, {"$set": {"status": "approved", "quality_status": "Approved"}})
        return {"ok": True, "status": "approved"}

    @router.post("/batches/{batch_id}/stock-in")
    async def stock_in_batch(batch_id: str, user: dict = Depends(get_current_user)):
        b = await db.batches.find_one({"id": batch_id}, {"_id": 0})
        if not b: raise HTTPException(404, "Batch not found")
        if b.get("stocked_in"):
            raise HTTPException(400, "Batch already stocked in")
        # auto-approve if pending
        if b.get("status") not in ("approved", "stocked_in"):
            await db.batches.update_one({"id": batch_id}, {"$set": {"status": "approved", "quality_status": "Approved"}})
        sku = await db.skus.find_one({"id": b["sku_id"]}, {"_id": 0})
        qty = int(b["batch_quantity"])
        await add_company_stock(b["sku_id"], batch_id, b.get("warehouse_id") or "wh-lagos-1", qty, sku or {})
        await db.batches.update_one({"id": batch_id}, {"$set": {"stocked_in": True, "status": "stocked_in"}})
        await ledger_append(
            movement="stock_in", scope="company", sku_id=b["sku_id"], sku_code=b.get("sku_code"),
            batch_id=batch_id, qty=qty, from_bucket=None, to_bucket="available",
            reference_type="batch", reference_id=batch_id, by_user=user.get("email"),
            notes=f"Manufacturing batch {b['batch_no']} stocked in",
        )
        return {"ok": True, "sku_id": b["sku_id"], "batch_id": batch_id, "qty_in": qty}

    # ==================================================================
    # 2) PRIMARY ORDER  (Distributor → Company)
    # ==================================================================
    @router.post("/primary-orders")
    async def create_primary_order(payload: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        distributor_id = payload.get("distributor_id")
        lines_in = payload.get("lines") or []
        if not distributor_id or not lines_in:
            raise HTTPException(400, "distributor_id and lines are required")
        dist = await db.distributors.find_one({"id": distributor_id}, {"_id": 0})
        if not dist: raise HTTPException(404, "Distributor not found")

        # stock check
        stock_check = []
        lines_out = []
        subtotal = 0.0
        for ln in lines_in:
            sku = await db.skus.find_one({"id": ln.get("sku_id")}, {"_id": 0})
            if not sku: raise HTTPException(400, f"Invalid sku_id {ln.get('sku_id')}")
            qty = int(ln.get("qty") or 0)
            if qty <= 0: raise HTTPException(400, "Qty must be > 0")
            price = float(ln.get("price") or sku.get("trade_price") or 0)
            avail = await get_company_stock_by_sku(sku["id"])
            ok = avail["available"] >= qty
            stock_check.append({"sku_id": sku["id"], "sku_code": sku["sku_code"], "requested": qty, "available": avail["available"], "ok": ok})
            line_total = qty * price
            subtotal += line_total
            lines_out.append({
                "sku_id": sku["id"], "sku_code": sku["sku_code"],
                "product_name": sku["product_name"], "pack_size": sku["pack_size"],
                "qty": qty, "price": price, "subtotal": line_total,
                "reserved_allocations": [],
            })
        tax = round(subtotal * 0.18, 2)
        total = round(subtotal + tax, 2)
        credit = await credit_check("distributors", distributor_id, total)

        status = "pending_approval"
        if not credit["ok"] or not all(s["ok"] for s in stock_check):
            status = "backorder" if all(s["ok"] for s in stock_check) is False else "pending_approval"

        order = {
            "id": new_id("po"),
            "order_no": f"PO-{int(datetime.now().timestamp())}",
            "type": "primary",
            "distributor_id": distributor_id, "party_id": distributor_id,
            "party_name": dist["name"], "party_type": "Distributor",
            "branch_id": dist.get("branch_id"),
            "lines": lines_out, "line_items": len(lines_out),
            "subtotal": round(subtotal, 2), "tax": tax, "total": total,
            "status": status,
            "stock_check": stock_check, "credit_check": credit,
            "sla": "12h",
            "placed_on": now_iso(), "created_at": now_iso(), "created_by": user.get("email"),
        }
        await db.primary_orders.insert_one(order)
        return strip_id(order)

    @router.post("/primary-orders/{order_id}/approve")
    async def approve_primary_order(order_id: str, user: dict = Depends(get_current_user)):
        order = await db.primary_orders.find_one({"id": order_id}, {"_id": 0})
        if not order: raise HTTPException(404, "Order not found")
        if order["status"] not in ("pending_approval", "backorder", "draft"):
            raise HTTPException(400, f"Cannot approve from status {order['status']}")

        # reserve FIFO for each line
        updated_lines = []
        for ln in order["lines"]:
            allocs = await reserve_fifo_company(ln["sku_id"], ln["qty"])
            ln["reserved_allocations"] = allocs
            updated_lines.append(ln)
            for a in allocs:
                await ledger_append(
                    movement="reserve", scope="company", sku_id=ln["sku_id"], sku_code=ln["sku_code"],
                    batch_id=a["batch_id"], qty=a["qty"], from_bucket="available", to_bucket="reserved",
                    reference_type="primary_order", reference_id=order_id, by_user=user.get("email"),
                    notes=f"Reserved for order {order['order_no']}",
                )
        await db.primary_orders.update_one({"id": order_id}, {"$set": {
            "status": "approved", "lines": updated_lines, "approved_at": now_iso(), "approved_by": user.get("email"),
        }})

        # Auto-generate invoice on approve
        return await _generate_primary_invoice_internal(order_id, user)

    @router.post("/primary-orders/{order_id}/reject")
    async def reject_primary_order(order_id: str, payload: Dict[str, Any] = Body(default={}), user: dict = Depends(get_current_user)):
        order = await db.primary_orders.find_one({"id": order_id})
        if not order: raise HTTPException(404, "Order not found")
        if order["status"] not in ("pending_approval", "backorder", "draft"):
            raise HTTPException(400, "Only pending orders can be rejected")
        await db.primary_orders.update_one({"id": order_id}, {"$set": {"status": "rejected", "reject_reason": payload.get("reason", "Rejected by manager"), "rejected_at": now_iso()}})
        return {"ok": True, "status": "rejected"}

    # ==================================================================
    # 3) PRIMARY INVOICE
    # ==================================================================
    async def _generate_primary_invoice_internal(order_id: str, user: dict):
        order = await db.primary_orders.find_one({"id": order_id}, {"_id": 0})
        if not order: raise HTTPException(404, "Order not found")
        if order["status"] != "approved":
            raise HTTPException(400, "Order must be approved to invoice")

        inv_id = new_id("inv")
        invoice = {
            "id": inv_id,
            "invoice_no": f"INV-{int(datetime.now().timestamp())}",
            "order_id": order_id, "order_no": order["order_no"],
            "type": "primary",
            "distributor_id": order["distributor_id"],
            "party_id": order["distributor_id"], "party_name": order["party_name"],
            "branch_id": order.get("branch_id"),
            "lines": order["lines"],
            "subtotal": order["subtotal"], "tax": order["tax"], "total": order["total"],
            "paid": 0,
            "status": "issued",
            "issued_on": now_iso(),
            "due_on": now_iso(),
            "created_by": user.get("email"),
        }
        await db.invoices.insert_one(invoice)
        await db.primary_orders.update_one({"id": order_id}, {"$set": {"status": "invoiced", "invoice_id": inv_id}})
        return strip_id(invoice)

    @router.post("/primary-invoices/generate/{order_id}")
    async def generate_primary_invoice(order_id: str, user: dict = Depends(get_current_user)):
        return await _generate_primary_invoice_internal(order_id, user)

    # ==================================================================
    # 4) DISPATCH (Company → GIT)
    # ==================================================================
    @router.post("/invoices/{invoice_id}/dispatch")
    async def dispatch_invoice(invoice_id: str, payload: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        inv = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not inv: raise HTTPException(404, "Invoice not found")
        if inv["status"] != "issued":
            raise HTTPException(400, "Invoice not in issued state")

        is_primary = inv.get("type") == "primary"
        # Move stock reserved → in_transit for each line + batch allocation
        for ln in inv["lines"]:
            for a in ln.get("reserved_allocations", []):
                if is_primary:
                    await move_company_bucket(ln["sku_id"], a["batch_id"], "reserved", "in_transit", a["qty"])
                    await ledger_append(
                        movement="dispatch_out", scope="company", sku_id=ln["sku_id"], sku_code=ln["sku_code"],
                        batch_id=a["batch_id"], qty=a["qty"], from_bucket="reserved", to_bucket="in_transit",
                        reference_type="invoice", reference_id=invoice_id, by_user=user.get("email"),
                        notes=f"Dispatch for invoice {inv['invoice_no']}",
                    )
                else:
                    # secondary: distributor stock reserved → in_transit
                    await move_partner_bucket("distributor_inventory", inv["distributor_id"], ln["sku_id"], a["batch_id"], "reserved", "in_transit", a["qty"])
                    await ledger_append(
                        movement="dispatch_out", scope="distributor", partner_id=inv["distributor_id"],
                        sku_id=ln["sku_id"], sku_code=ln["sku_code"],
                        batch_id=a["batch_id"], qty=a["qty"], from_bucket="reserved", to_bucket="in_transit",
                        reference_type="invoice", reference_id=invoice_id, by_user=user.get("email"),
                        notes=f"Dispatch to retailer for invoice {inv['invoice_no']}",
                    )

        dispatch = {
            "id": new_id("disp"),
            "dispatch_no": f"DSP-{int(datetime.now().timestamp())}",
            "invoice_id": invoice_id, "invoice_no": inv["invoice_no"],
            "order_id": inv["order_id"],
            "type": "primary" if is_primary else "secondary",
            "party_name": inv["party_name"],
            "distributor_id": inv.get("distributor_id"),
            "retailer_id": inv.get("retailer_id"),
            "lines": inv["lines"],
            "vehicle_no": payload.get("vehicle_no", "LG-000-XX"),
            "driver": payload.get("driver", "TBD"),
            "lr_no": payload.get("lr_no", f"LR{int(datetime.now().timestamp())}"),
            "transporter": payload.get("transporter", "GO OIL Transport"),
            "route": payload.get("route", "Lagos → Destination"),
            "distance_km": int(payload.get("distance_km", 300)),
            "dispatch_date": now_iso(),
            "eta": now_iso(),
            "status": "in_transit",
            "created_by": user.get("email"),
        }
        await db.dispatches.insert_one(dispatch)
        await db.invoices.update_one({"id": invoice_id}, {"$set": {"status": "dispatched", "dispatch_id": dispatch["id"]}})
        if is_primary:
            await db.primary_orders.update_one({"id": inv["order_id"]}, {"$set": {"status": "dispatched"}})
        else:
            await db.secondary_orders.update_one({"id": inv["order_id"]}, {"$set": {"status": "dispatched"}})
        return strip_id(dispatch)

    # ==================================================================
    # 5) GRN (Distributor / Retailer Receive)
    # ==================================================================
    @router.post("/dispatches/{dispatch_id}/receive")
    async def receive_dispatch(dispatch_id: str, payload: Dict[str, Any] = Body(default={}), user: dict = Depends(get_current_user)):
        d = await db.dispatches.find_one({"id": dispatch_id}, {"_id": 0})
        if not d: raise HTTPException(404, "Dispatch not found")
        if d["status"] not in ("in_transit", "prepared"):
            raise HTTPException(400, f"Dispatch is {d['status']}")

        is_primary = d.get("type") == "primary"
        partner_coll = "distributor_inventory" if is_primary else "retailer_inventory"
        partner_id = d["distributor_id"] if is_primary else d["retailer_id"]

        # Optional per-line receipts, else full acceptance
        line_receipts = {ln["sku_id"]: ln for ln in (payload.get("line_receipts") or [])}
        received_lines = []
        overall_condition = "Good"
        for ln in d["lines"]:
            recv = line_receipts.get(ln["sku_id"], {})
            received_qty = int(recv.get("received_qty", ln["qty"]))
            damaged_qty = int(recv.get("damaged_qty", 0))
            shortage_qty = int(recv.get("shortage_qty", max(0, ln["qty"] - received_qty)))
            excess_qty = int(recv.get("excess_qty", max(0, received_qty - ln["qty"])))

            for a in ln.get("reserved_allocations", []):
                dispatched = a["qty"]
                # Allocate received_qty proportionally
                actual_recv = int(round(received_qty * dispatched / ln["qty"])) if ln["qty"] else dispatched
                actual_damaged = int(round(damaged_qty * dispatched / ln["qty"])) if ln["qty"] else 0

                if is_primary:
                    # Company: in_transit -= dispatched
                    await move_company_bucket(ln["sku_id"], a["batch_id"], "in_transit", "in_transit", 0)  # noop guard
                    await db.company_inventory.update_one(
                        {"sku_id": ln["sku_id"], "batch_id": a["batch_id"]},
                        {"$inc": {"in_transit": -dispatched}},
                    )
                    await ledger_append(
                        movement="dispatch_settled", scope="company", sku_id=ln["sku_id"], sku_code=ln["sku_code"],
                        batch_id=a["batch_id"], qty=dispatched, from_bucket="in_transit", to_bucket="cleared",
                        reference_type="dispatch", reference_id=dispatch_id, by_user=user.get("email"),
                        notes=f"Company in-transit cleared on GRN",
                    )

                sku = await db.skus.find_one({"id": ln["sku_id"]}, {"_id": 0}) or {}
                if actual_recv > 0:
                    await add_partner_stock(partner_coll, partner_id, ln["sku_id"], a["batch_id"], actual_recv, sku)
                    await ledger_append(
                        movement="grn_in", scope="distributor" if is_primary else "retailer", partner_id=partner_id,
                        sku_id=ln["sku_id"], sku_code=ln["sku_code"],
                        batch_id=a["batch_id"], qty=actual_recv, from_bucket=None, to_bucket="available",
                        reference_type="dispatch", reference_id=dispatch_id, by_user=user.get("email"),
                        notes=f"Received via {d['dispatch_no']}",
                    )
                if actual_damaged > 0:
                    await add_partner_stock(partner_coll, partner_id, ln["sku_id"], a["batch_id"], 0, sku)
                    await db[partner_coll].update_one(
                        {"partner_id": partner_id, "sku_id": ln["sku_id"], "batch_id": a["batch_id"]},
                        {"$inc": {"damaged": actual_damaged}},
                    )
                    await ledger_append(
                        movement="damage", scope="distributor" if is_primary else "retailer", partner_id=partner_id,
                        sku_id=ln["sku_id"], sku_code=ln["sku_code"],
                        batch_id=a["batch_id"], qty=actual_damaged, from_bucket=None, to_bucket="damaged",
                        reference_type="dispatch", reference_id=dispatch_id, by_user=user.get("email"),
                        notes="Damage recorded on GRN",
                    )
            if damaged_qty or shortage_qty or excess_qty:
                overall_condition = "Damaged" if damaged_qty else ("Short" if shortage_qty else "Good")
            received_lines.append({
                "sku_id": ln["sku_id"], "sku_code": ln["sku_code"],
                "dispatched_qty": ln["qty"], "received_qty": received_qty,
                "damaged_qty": damaged_qty, "shortage_qty": shortage_qty, "excess_qty": excess_qty,
            })

        grn = {
            "id": new_id("grn"),
            "grn_no": f"GRN-{int(datetime.now().timestamp())}",
            "dispatch_id": dispatch_id, "dispatch_no": d.get("dispatch_no"),
            "type": "primary" if is_primary else "secondary",
            "distributor_id": d.get("distributor_id"),
            "retailer_id": d.get("retailer_id"),
            "received_by": d["party_name"],
            "received_on": now_iso(),
            "lines": received_lines,
            "condition": overall_condition,
            "variance": sum([l["shortage_qty"] - l["excess_qty"] for l in received_lines]),
            "status": "Accepted" if overall_condition == "Good" else "Under Review",
            "notes": payload.get("notes", ""),
        }
        await db.grns.insert_one(grn)
        await db.dispatches.update_one({"id": dispatch_id}, {"$set": {"status": "delivered", "grn_id": grn["id"], "delivered_at": now_iso()}})
        await db.invoices.update_one({"id": d["invoice_id"]}, {"$set": {"status": "delivered"}})
        if is_primary:
            await db.primary_orders.update_one({"id": d["order_id"]}, {"$set": {"status": "completed"}})
        else:
            await db.secondary_orders.update_one({"id": d["order_id"]}, {"$set": {"status": "completed"}})
        return strip_id(grn)

    # ==================================================================
    # 6) SECONDARY ORDER (Retailer → Distributor)
    # ==================================================================
    @router.post("/secondary-orders")
    async def create_secondary_order(payload: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        retailer_id = payload.get("retailer_id")
        lines_in = payload.get("lines") or []
        if not retailer_id or not lines_in:
            raise HTTPException(400, "retailer_id and lines are required")
        ret = await db.retailers.find_one({"id": retailer_id}, {"_id": 0})
        if not ret: raise HTTPException(404, "Retailer not found")
        distributor_id = payload.get("distributor_id") or ret.get("distributor_id")
        dist = await db.distributors.find_one({"id": distributor_id}, {"_id": 0})
        if not dist: raise HTTPException(404, "Distributor not found")

        stock_check = []
        lines_out = []
        subtotal = 0.0
        for ln in lines_in:
            sku = await db.skus.find_one({"id": ln.get("sku_id")}, {"_id": 0})
            if not sku: raise HTTPException(400, f"Invalid sku_id {ln.get('sku_id')}")
            qty = int(ln.get("qty") or 0)
            if qty <= 0: raise HTTPException(400, "Qty must be > 0")
            price = float(ln.get("price") or sku.get("mrp") or 0)
            # aggregate available in distributor inventory
            total_avail = 0
            async for row in db.distributor_inventory.find({"partner_id": distributor_id, "sku_id": sku["id"]}, {"_id": 0}):
                total_avail += int(row.get("available", 0) or 0)
            ok = total_avail >= qty
            stock_check.append({"sku_id": sku["id"], "sku_code": sku["sku_code"], "requested": qty, "available": total_avail, "ok": ok})
            subtotal += qty * price
            lines_out.append({
                "sku_id": sku["id"], "sku_code": sku["sku_code"],
                "product_name": sku["product_name"], "pack_size": sku["pack_size"],
                "qty": qty, "price": price, "subtotal": qty * price,
                "reserved_allocations": [],
            })
        tax = round(subtotal * 0.18, 2)
        total = round(subtotal + tax, 2)
        credit = await credit_check("retailers", retailer_id, total)

        status = "pending_approval" if credit["ok"] and all(s["ok"] for s in stock_check) else "backorder"

        order = {
            "id": new_id("so"),
            "order_no": f"SO-{int(datetime.now().timestamp())}",
            "type": "secondary",
            "distributor_id": distributor_id, "retailer_id": retailer_id,
            "party_id": retailer_id, "party_name": ret["name"], "party_type": "Retailer",
            "branch_id": dist.get("branch_id"),
            "lines": lines_out, "line_items": len(lines_out),
            "subtotal": round(subtotal, 2), "tax": tax, "total": total,
            "status": status,
            "stock_check": stock_check, "credit_check": credit,
            "sla": "6h",
            "placed_on": now_iso(), "created_at": now_iso(), "created_by": user.get("email"),
        }
        await db.secondary_orders.insert_one(order)
        return strip_id(order)

    @router.post("/secondary-orders/{order_id}/approve")
    async def approve_secondary_order(order_id: str, user: dict = Depends(get_current_user)):
        order = await db.secondary_orders.find_one({"id": order_id}, {"_id": 0})
        if not order: raise HTTPException(404, "Order not found")
        if order["status"] not in ("pending_approval", "backorder", "draft"):
            raise HTTPException(400, f"Cannot approve from status {order['status']}")

        updated_lines = []
        for ln in order["lines"]:
            allocs = await reserve_fifo_partner("distributor_inventory", order["distributor_id"], ln["sku_id"], ln["qty"])
            ln["reserved_allocations"] = allocs
            updated_lines.append(ln)
            for a in allocs:
                await ledger_append(
                    movement="reserve", scope="distributor", partner_id=order["distributor_id"],
                    sku_id=ln["sku_id"], sku_code=ln["sku_code"],
                    batch_id=a["batch_id"], qty=a["qty"], from_bucket="available", to_bucket="reserved",
                    reference_type="secondary_order", reference_id=order_id, by_user=user.get("email"),
                    notes=f"Reserved for retailer order {order['order_no']}",
                )
        await db.secondary_orders.update_one({"id": order_id}, {"$set": {
            "status": "approved", "lines": updated_lines, "approved_at": now_iso(), "approved_by": user.get("email"),
        }})
        # Auto-generate secondary invoice
        return await _generate_secondary_invoice_internal(order_id, user)

    @router.post("/secondary-orders/{order_id}/reject")
    async def reject_secondary_order(order_id: str, payload: Dict[str, Any] = Body(default={}), user: dict = Depends(get_current_user)):
        order = await db.secondary_orders.find_one({"id": order_id})
        if not order: raise HTTPException(404, "Order not found")
        await db.secondary_orders.update_one({"id": order_id}, {"$set": {"status": "rejected", "reject_reason": payload.get("reason", "Rejected"), "rejected_at": now_iso()}})
        return {"ok": True, "status": "rejected"}

    # ==================================================================
    # 7) SECONDARY INVOICE
    # ==================================================================
    async def _generate_secondary_invoice_internal(order_id: str, user: dict):
        order = await db.secondary_orders.find_one({"id": order_id}, {"_id": 0})
        if not order: raise HTTPException(404, "Order not found")
        if order["status"] != "approved":
            raise HTTPException(400, "Order must be approved to invoice")
        inv_id = new_id("inv")
        invoice = {
            "id": inv_id,
            "invoice_no": f"INV-{int(datetime.now().timestamp())}",
            "order_id": order_id, "order_no": order["order_no"],
            "type": "secondary",
            "distributor_id": order["distributor_id"], "retailer_id": order["retailer_id"],
            "party_id": order["retailer_id"], "party_name": order["party_name"],
            "branch_id": order.get("branch_id"),
            "lines": order["lines"],
            "subtotal": order["subtotal"], "tax": order["tax"], "total": order["total"],
            "paid": 0, "status": "issued",
            "issued_on": now_iso(), "due_on": now_iso(),
            "created_by": user.get("email"),
        }
        await db.invoices.insert_one(invoice)
        await db.secondary_orders.update_one({"id": order_id}, {"$set": {"status": "invoiced", "invoice_id": inv_id}})
        return strip_id(invoice)

    @router.post("/secondary-invoices/generate/{order_id}")
    async def generate_secondary_invoice(order_id: str, user: dict = Depends(get_current_user)):
        return await _generate_secondary_invoice_internal(order_id, user)

    # ==================================================================
    # 8) INVENTORY VIEWS
    # ==================================================================
    @router.get("/inventory/company")
    async def inventory_company(sku_id: Optional[str] = None, warehouse_id: Optional[str] = None,
                                  user: dict = Depends(get_current_user)):
        q = {}
        if sku_id: q["sku_id"] = sku_id
        if warehouse_id: q["warehouse_id"] = warehouse_id
        rows = await db.company_inventory.find(q, {"_id": 0}).to_list(1000)
        return {"data": rows, "count": len(rows)}

    @router.get("/inventory/distributor/{partner_id}")
    async def inventory_distributor(partner_id: str, user: dict = Depends(get_current_user)):
        rows = await db.distributor_inventory.find({"partner_id": partner_id}, {"_id": 0}).to_list(1000)
        return {"data": rows, "count": len(rows)}

    @router.get("/inventory/retailer/{partner_id}")
    async def inventory_retailer(partner_id: str, user: dict = Depends(get_current_user)):
        rows = await db.retailer_inventory.find({"partner_id": partner_id}, {"_id": 0}).to_list(1000)
        return {"data": rows, "count": len(rows)}

    @router.get("/stock-ledger")
    async def stock_ledger(sku_id: Optional[str] = None, reference_id: Optional[str] = None,
                             scope: Optional[str] = None, limit: int = 300,
                             user: dict = Depends(get_current_user)):
        q = {}
        if sku_id: q["sku_id"] = sku_id
        if reference_id: q["reference_id"] = reference_id
        if scope: q["scope"] = scope
        rows = await db.stock_ledger.find(q, {"_id": 0}).sort("timestamp", -1).to_list(limit)
        return {"data": rows, "count": len(rows)}

    @router.get("/order/{order_id}/trace")
    async def order_trace(order_id: str, user: dict = Depends(get_current_user)):
        """Return the full linked trail for a primary or secondary order."""
        po = await db.primary_orders.find_one({"id": order_id}, {"_id": 0})
        so = None
        if not po:
            so = await db.secondary_orders.find_one({"id": order_id}, {"_id": 0})
        order = po or so
        if not order: raise HTTPException(404, "Order not found")
        inv = await db.invoices.find_one({"order_id": order_id}, {"_id": 0})
        disp = await db.dispatches.find_one({"order_id": order_id}, {"_id": 0}) if inv else None
        grn = await db.grns.find_one({"dispatch_id": disp["id"]}, {"_id": 0}) if disp else None
        ledger = await db.stock_ledger.find({"reference_id": order_id}, {"_id": 0}).sort("timestamp", 1).to_list(200)
        return {"order": order, "invoice": inv, "dispatch": disp, "grn": grn, "ledger": ledger}

    return router
