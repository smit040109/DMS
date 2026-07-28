"""GO OIL DMS — Phase 2 Financial Workflow Engine.

Modules:
  - Customer Orders (retailer → customer, deducts retailer inventory)
  - Coupons (validation, redemption, fraud checks)
  - Cashback (rule engine, wallet, approval workflow)
  - Payments (allocation to invoices, multi-method)
  - Double-Entry Ledger (debit/credit accounts)
  - Outstanding (computed per party)
  - Reconciliation (invoice vs payment matching)
  - Audit Log (every financial action)

Automation:
    Retailer Inv → Customer Order → Coupon Validate → Cashback Compute
    → Invoice → Payment → Outstanding Reduced → Ledger Updated
    → Cashback Approved → Wallet Updated → Reports Updated
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Body

# Standard chart-of-accounts codes
ACCOUNTS = {
    "AR": "1200",           # Accounts Receivable
    "CASH": "1000",         # Cash / Bank
    "SALES": "4000",        # Sales Revenue
    "TAX_OUT": "2100",      # Output GST payable
    "DISCOUNT": "5100",     # Discount given (contra-revenue)
    "CASHBACK_EXP": "5200", # Cashback expense
    "CASHBACK_LIAB": "2200",# Cashback liability (wallet balance)
    "AP": "2000",           # Accounts Payable
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"

def strip_id(doc):
    if doc is None: return None
    doc.pop("_id", None)
    return doc


def build_finance_router(db, get_current_user):
    router = APIRouter(prefix="/finance", tags=["finance"])

    # ==========================================================
    # AUDIT LOG
    # ==========================================================
    async def audit(action: str, entity_type: str, entity_id: str, actor: str,
                    changes: Optional[dict] = None, meta: Optional[dict] = None):
        await db.audit_log.insert_one({
            "id": new_id("aud"),
            "timestamp": now_iso(),
            "action": action, "entity_type": entity_type, "entity_id": entity_id,
            "actor": actor, "changes": changes or {}, "meta": meta or {},
        })

    # ==========================================================
    # DOUBLE-ENTRY LEDGER
    # ==========================================================
    async def post_journal(entries: List[Dict[str, Any]], reference_type: str, reference_id: str,
                            narration: str, actor: str, party_scope: Optional[Dict] = None):
        """entries = [{account, debit, credit, party_id, party_type, party_name}] — must balance."""
        total_dr = sum(float(e.get("debit", 0) or 0) for e in entries)
        total_cr = sum(float(e.get("credit", 0) or 0) for e in entries)
        if abs(total_dr - total_cr) > 0.01:
            raise HTTPException(400, f"Journal imbalance: Dr={total_dr}, Cr={total_cr}")
        journal_id = new_id("jrn")
        docs = []
        for e in entries:
            docs.append({
                "id": new_id("led"),
                "journal_id": journal_id,
                "timestamp": now_iso(),
                "account": e["account"],
                "account_code": ACCOUNTS.get(e["account"], "9999"),
                "debit": round(float(e.get("debit", 0) or 0), 2),
                "credit": round(float(e.get("credit", 0) or 0), 2),
                "party_id": e.get("party_id"),
                "party_type": e.get("party_type"),
                "party_name": e.get("party_name"),
                "reference_type": reference_type, "reference_id": reference_id,
                "narration": narration, "posted_by": actor,
            })
        if docs:
            await db.double_ledger.insert_many(docs)
        return journal_id

    # ==========================================================
    # OUTSTANDING (recompute per party from ledger)
    # ==========================================================
    async def recompute_outstanding(party_type: str, party_id: str):
        """Sum AR debits - AR credits for the party."""
        cursor = db.double_ledger.find({
            "party_id": party_id, "party_type": party_type, "account": "AR",
        }, {"_id": 0})
        dr = cr = 0.0
        oldest_invoice = None
        async for row in cursor:
            dr += row.get("debit", 0) or 0
            cr += row.get("credit", 0) or 0
        outstanding = round(dr - cr, 2)
        # Overdue: sum of invoice.total where due_on passed and not fully paid
        overdue = 0.0
        overdue_days_max = 0
        overdue_count = 0
        async for inv in db.invoices.find({"party_id": party_id, "status": {"$ne": "cancelled"}}, {"_id": 0}):
            paid = float(inv.get("paid", 0) or 0)
            total = float(inv.get("total", 0) or 0)
            remaining = total - paid
            if remaining > 0.01:
                try:
                    due = datetime.fromisoformat(inv.get("due_on", now_iso()).replace("Z", "+00:00"))
                    days = (datetime.now(timezone.utc) - due).days
                    if days > 0:
                        overdue += remaining
                        overdue_days_max = max(overdue_days_max, days)
                        overdue_count += 1
                except Exception:
                    pass
        # Credit info for distributor/retailer
        credit_limit = 0
        if party_type == "distributor":
            p = await db.distributors.find_one({"id": party_id}, {"_id": 0})
            credit_limit = float((p or {}).get("credit_limit", 0) or 0)
        elif party_type == "retailer":
            p = await db.retailers.find_one({"id": party_id}, {"_id": 0})
            credit_limit = float((p or {}).get("credit_limit", 0) or 0)
        utilization = round((outstanding * 100 / credit_limit), 1) if credit_limit else 0

        # Fetch party name for display
        party_name = None
        if party_type in ("distributor", "retailer", "customer"):
            p = await db[f"{party_type}s"].find_one({"id": party_id}, {"_id": 0})
            if p: party_name = p.get("name")
        record = {
            "party_id": party_id, "party_type": party_type, "party_name": party_name,
            "outstanding": outstanding, "overdue": round(overdue, 2),
            "overdue_days_max": overdue_days_max, "overdue_count": overdue_count,
            "credit_limit": credit_limit, "credit_utilization": utilization,
            "collection_status": "Healthy" if overdue == 0 else ("Watch" if overdue_days_max <= 15 else "Overdue"),
            "updated_at": now_iso(),
        }
        await db.outstanding.update_one(
            {"party_id": party_id, "party_type": party_type},
            {"$set": record}, upsert=True,
        )
        # Mirror `outstanding` on the party doc
        if party_type in ("distributor", "retailer"):
            await db[f"{party_type}s"].update_one({"id": party_id}, {"$set": {"outstanding": outstanding}})
        return record

    # ==========================================================
    # WALLET (cashback)
    # ==========================================================
    async def get_wallet(party_id: str, party_type: str):
        w = await db.wallets.find_one({"party_id": party_id, "party_type": party_type}, {"_id": 0})
        if not w:
            w = {
                "id": new_id("wal"), "party_id": party_id, "party_type": party_type,
                "balance": 0.0, "lifetime_earned": 0.0, "lifetime_redeemed": 0.0,
                "created_at": now_iso(),
            }
            await db.wallets.insert_one(w)
        return w

    async def wallet_credit(party_id: str, party_type: str, amount: float, reason: str, ref_id: str, actor: str):
        await get_wallet(party_id, party_type)
        await db.wallets.update_one(
            {"party_id": party_id, "party_type": party_type},
            {"$inc": {"balance": amount, "lifetime_earned": amount}, "$set": {"updated_at": now_iso()}},
        )
        await db.cashback_transactions.insert_one({
            "id": new_id("cbtx"), "party_id": party_id, "party_type": party_type,
            "type": "credit", "amount": round(amount, 2), "reason": reason,
            "reference_id": ref_id, "timestamp": now_iso(), "actor": actor,
        })

    async def wallet_debit(party_id: str, party_type: str, amount: float, reason: str, ref_id: str, actor: str):
        w = await get_wallet(party_id, party_type)
        if float(w.get("balance", 0)) < amount - 0.01:
            raise HTTPException(400, f"Insufficient wallet balance: {w.get('balance')} < {amount}")
        await db.wallets.update_one(
            {"party_id": party_id, "party_type": party_type},
            {"$inc": {"balance": -amount, "lifetime_redeemed": amount}, "$set": {"updated_at": now_iso()}},
        )
        await db.cashback_transactions.insert_one({
            "id": new_id("cbtx"), "party_id": party_id, "party_type": party_type,
            "type": "debit", "amount": round(amount, 2), "reason": reason,
            "reference_id": ref_id, "timestamp": now_iso(), "actor": actor,
        })

    # ==========================================================
    # COUPON VALIDATION
    # ==========================================================
    async def validate_coupon(code: str, party_id: str, party_type: str, order_lines: List[Dict], order_total: float):
        code = (code or "").upper().strip()
        if not code:
            return {"ok": False, "reason": "Coupon code required"}
        c = await db.coupons.find_one({"code": code}, {"_id": 0})
        if not c:
            return {"ok": False, "reason": "Coupon does not exist"}
        if str(c.get("status", "Active")).lower() != "active":
            return {"ok": False, "reason": f"Coupon is {c.get('status')}"}
        # Expiry
        try:
            valid_till = datetime.fromisoformat((c.get("valid_till") or now_iso()).replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > valid_till:
                return {"ok": False, "reason": "Coupon expired"}
        except Exception: pass
        # Usage limit
        used = int(c.get("usage", 0) or 0)
        limit = int(c.get("limit", 0) or 0)
        if limit and used >= limit:
            return {"ok": False, "reason": "Coupon usage limit exceeded"}
        # Minimum order
        min_order = float(c.get("min_order", 0) or 0)
        if order_total < min_order:
            return {"ok": False, "reason": f"Minimum order value ${min_order:,.2f} required"}
        # Already used by this party (idempotency)
        already = await db.coupon_redemptions.find_one({"code": code, "party_id": party_id})
        if already:
            return {"ok": False, "reason": "Coupon already used by this party"}
        # Applicable segments (if configured)
        app_parties = c.get("applicable_parties") or []
        if app_parties and party_id not in app_parties:
            return {"ok": False, "reason": "Coupon not applicable to this party"}
        # Compute discount
        d_type = c.get("discount_type", "Flat")
        val = float(c.get("value", 0) or 0)
        if d_type == "Percent":
            discount = order_total * val / 100.0
        else:
            discount = val
        max_disc = float(c.get("max_discount", 0) or 0)
        if max_disc and discount > max_disc:
            discount = max_disc
        discount = round(min(discount, order_total), 2)
        return {"ok": True, "discount": discount, "coupon": c}

    @router.post("/coupons/validate")
    async def api_validate_coupon(payload: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        return await validate_coupon(
            code=payload.get("code", ""),
            party_id=payload.get("party_id"),
            party_type=payload.get("party_type", "customer"),
            order_lines=payload.get("lines", []),
            order_total=float(payload.get("order_total", 0) or 0),
        )

    async def redeem_coupon(code: str, party_id: str, discount: float, ref_id: str, actor: str):
        code = code.upper().strip()
        await db.coupons.update_one({"code": code}, {"$inc": {"usage": 1}})
        await db.coupon_redemptions.insert_one({
            "id": new_id("cpr"), "code": code, "party_id": party_id,
            "discount": round(discount, 2), "reference_id": ref_id,
            "redeemed_at": now_iso(), "actor": actor,
        })

    @router.post("/coupons/create")
    async def create_coupon(payload: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        c = {
            "id": new_id("cpn"),
            "code": payload["code"].upper().strip(),
            "campaign": payload.get("campaign", ""),
            "discount_type": payload.get("discount_type", "Flat"),
            "value": float(payload.get("value", 0) or 0),
            "max_discount": float(payload.get("max_discount", 0) or 0),
            "min_order": float(payload.get("min_order", 0) or 0),
            "usage": 0, "limit": int(payload.get("limit", 0) or 0),
            "valid_till": payload.get("valid_till") or (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
            "applicable_products": payload.get("applicable_products", []),
            "applicable_parties": payload.get("applicable_parties", []),
            "status": "Active",
            "created_at": now_iso(), "created_by": user.get("email"),
        }
        exists = await db.coupons.find_one({"code": c["code"]})
        if exists:
            raise HTTPException(400, "Coupon code already exists")
        await db.coupons.insert_one(c)
        await audit("create_coupon", "coupon", c["id"], user.get("email"), meta={"code": c["code"]})
        return strip_id(c)

    # ==========================================================
    # CASHBACK RULE ENGINE
    # ==========================================================
    @router.post("/cashback-rules")
    async def create_cashback_rule(payload: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        rule = {
            "id": new_id("cbr"),
            "name": payload["name"],
            "scope": payload.get("scope", "sku"),        # sku|category|product|distributor|retailer|customer|campaign
            "scope_id": payload.get("scope_id"),
            "type": payload.get("type", "percent"),      # percent|flat
            "value": float(payload.get("value", 0) or 0),
            "max_cashback": float(payload.get("max_cashback", 0) or 0),
            "daily_limit": float(payload.get("daily_limit", 0) or 0),
            "monthly_limit": float(payload.get("monthly_limit", 0) or 0),
            "approval_required": bool(payload.get("approval_required", False)),
            "party_type": payload.get("party_type", "retailer"),  # who earns
            "active": True,
            "created_at": now_iso(), "created_by": user.get("email"),
        }
        await db.cashback_rules.insert_one(rule)
        await audit("create_cashback_rule", "cashback_rule", rule["id"], user.get("email"))
        return strip_id(rule)

    @router.get("/cashback-rules")
    async def list_cashback_rules(user: dict = Depends(get_current_user)):
        rows = await db.cashback_rules.find({"active": True}, {"_id": 0}).to_list(200)
        return {"data": rows, "count": len(rows)}

    async def compute_cashback(party_id: str, party_type: str, lines: List[Dict], order_total: float, campaign: Optional[str] = None):
        """Evaluate all applicable rules, return total cashback + rule matches."""
        rules = await db.cashback_rules.find({"active": True, "party_type": party_type}, {"_id": 0}).to_list(200)
        total_cb = 0.0
        matches = []
        # today / this month usage cap
        today = datetime.now(timezone.utc).date().isoformat()
        for r in rules:
            eligible_base = 0.0
            for ln in lines:
                if r["scope"] == "sku" and r.get("scope_id") != ln.get("sku_id"):
                    continue
                if r["scope"] == "product" and r.get("scope_id") and ln.get("product_id") != r.get("scope_id"):
                    continue
                if r["scope"] == "category" and r.get("scope_id") and ln.get("category") != r.get("scope_id"):
                    continue
                if r["scope"] in ("distributor", "retailer", "customer") and r.get("scope_id") and party_id != r.get("scope_id"):
                    continue
                if r["scope"] == "campaign" and r.get("scope_id") and (campaign or "") != r.get("scope_id"):
                    continue
                eligible_base += float(ln.get("subtotal", ln.get("qty", 0) * ln.get("price", 0)))
            if eligible_base <= 0:
                continue
            cb = eligible_base * r["value"] / 100.0 if r["type"] == "percent" else r["value"]
            if r.get("max_cashback"):
                cb = min(cb, r["max_cashback"])
            # daily / monthly limit check on wallet
            if r.get("daily_limit"):
                daily = 0.0
                async for t in db.cashback_transactions.find({
                    "party_id": party_id, "party_type": party_type, "type": "credit",
                    "timestamp": {"$gte": today},
                }, {"_id": 0}):
                    daily += t.get("amount", 0)
                if daily + cb > r["daily_limit"]:
                    cb = max(0, r["daily_limit"] - daily)
            if cb > 0:
                total_cb += cb
                matches.append({"rule_id": r["id"], "rule_name": r["name"], "amount": round(cb, 2), "approval_required": r["approval_required"]})
        return {"total_cashback": round(total_cb, 2), "matches": matches}

    @router.post("/cashback/compute")
    async def api_compute_cashback(payload: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        return await compute_cashback(
            party_id=payload.get("party_id"),
            party_type=payload.get("party_type", "retailer"),
            lines=payload.get("lines", []),
            order_total=float(payload.get("order_total", 0) or 0),
            campaign=payload.get("campaign"),
        )

    @router.post("/cashback/{cb_id}/approve")
    async def approve_cashback(cb_id: str, user: dict = Depends(get_current_user)):
        cb = await db.cashback.find_one({"id": cb_id}, {"_id": 0})
        if not cb: raise HTTPException(404, "Cashback not found")
        if cb.get("status") in ("Credited", "Approved", "Paid"):
            raise HTTPException(400, "Already processed")
        amt = float(cb.get("earned", 0) or 0)
        party_id = cb.get("retailer_id") or cb.get("party_id")
        party_type = "retailer"
        # Credit wallet + ledger
        await wallet_credit(party_id, party_type, amt, f"Cashback: {cb.get('campaign','')}", cb_id, user.get("email"))
        await post_journal(
            entries=[
                {"account": "CASHBACK_EXP", "debit": amt, "credit": 0, "party_id": party_id, "party_type": party_type, "party_name": cb.get("retailer_name")},
                {"account": "CASHBACK_LIAB", "debit": 0, "credit": amt, "party_id": party_id, "party_type": party_type, "party_name": cb.get("retailer_name")},
            ], reference_type="cashback", reference_id=cb_id,
            narration=f"Cashback approved for {cb.get('campaign','')}", actor=user.get("email"),
        )
        await db.cashback.update_one({"id": cb_id}, {"$set": {"status": "Credited", "approved_at": now_iso(), "approved_by": user.get("email")}})
        await audit("approve_cashback", "cashback", cb_id, user.get("email"), meta={"amount": amt})
        return {"ok": True, "amount": amt}

    @router.post("/cashback/{cb_id}/reject")
    async def reject_cashback(cb_id: str, payload: Dict[str, Any] = Body(default={}), user: dict = Depends(get_current_user)):
        await db.cashback.update_one({"id": cb_id}, {"$set": {"status": "Rejected", "rejected_at": now_iso(), "reject_reason": payload.get("reason", "Rejected")}})
        return {"ok": True}

    # ==========================================================
    # CUSTOMER ORDER
    # ==========================================================
    @router.post("/customer-orders")
    async def create_customer_order(payload: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        retailer_id = payload.get("retailer_id")
        customer_id = payload.get("customer_id")
        lines_in = payload.get("lines") or []
        if not (retailer_id and customer_id and lines_in):
            raise HTTPException(400, "retailer_id, customer_id, lines required")
        retailer = await db.retailers.find_one({"id": retailer_id}, {"_id": 0})
        if not retailer: raise HTTPException(404, "Retailer not found")
        customer = await db.customers.find_one({"id": customer_id}, {"_id": 0})
        if not customer: raise HTTPException(404, "Customer not found")

        # Check retailer inventory and compute subtotal
        subtotal = 0.0
        lines_out = []
        for ln in lines_in:
            sku = await db.skus.find_one({"id": ln.get("sku_id")}, {"_id": 0})
            if not sku: raise HTTPException(400, f"Invalid sku_id {ln.get('sku_id')}")
            qty = int(ln.get("qty") or 0)
            if qty <= 0: raise HTTPException(400, "Qty > 0")
            price = float(ln.get("price") or sku.get("mrp") or 0)
            # Aggregate retailer inventory
            avail = 0
            async for r in db.retailer_inventory.find({"partner_id": retailer_id, "sku_id": sku["id"]}, {"_id": 0}):
                avail += int(r.get("available", 0) or 0)
            if avail < qty:
                raise HTTPException(400, f"Insufficient retailer stock for {sku['sku_code']}: need {qty}, have {avail}")
            lines_out.append({
                "sku_id": sku["id"], "sku_code": sku["sku_code"],
                "product_name": sku["product_name"], "pack_size": sku["pack_size"],
                "qty": qty, "price": price, "subtotal": qty * price,
            })
            subtotal += qty * price

        # Optional coupon
        discount = 0.0
        coupon_used = None
        if payload.get("coupon_code"):
            v = await validate_coupon(payload["coupon_code"], customer_id, "customer", lines_out, subtotal)
            if not v["ok"]:
                raise HTTPException(400, f"Coupon rejected: {v['reason']}")
            discount = v["discount"]
            coupon_used = v["coupon"]["code"]

        taxable = subtotal - discount
        tax = round(taxable * 0.18, 2)
        total = round(taxable + tax, 2)

        # Cashback compute (potential earnings)
        cb = await compute_cashback(customer_id, "customer", lines_out, total, campaign=payload.get("campaign"))

        order = {
            "id": new_id("cust"),
            "order_no": f"CUST-{int(datetime.now().timestamp())}",
            "type": "customer",
            "retailer_id": retailer_id, "retailer_name": retailer["name"],
            "customer_id": customer_id, "customer_name": customer["name"],
            "party_id": customer_id, "party_name": customer["name"], "party_type": "Customer",
            "lines": lines_out, "line_items": len(lines_out),
            "subtotal": round(subtotal, 2),
            "discount": round(discount, 2), "coupon_code": coupon_used,
            "tax": tax, "total": total,
            "cashback_estimated": cb["total_cashback"],
            "cashback_matches": cb["matches"],
            "delivery_mode": payload.get("delivery_mode", "Pickup"),
            "payment_method": payload.get("payment_method", "Cash"),
            "status": "confirmed",
            "created_at": now_iso(), "placed_on": now_iso(),
            "created_by": user.get("email"),
        }
        await db.customer_orders.insert_one(order)
        if coupon_used:
            await redeem_coupon(coupon_used, customer_id, discount, order["id"], user.get("email"))

        # Deduct retailer inventory FIFO
        for ln in lines_out:
            rows = await db.retailer_inventory.find({"partner_id": retailer_id, "sku_id": ln["sku_id"], "available": {"$gt": 0}}, {"_id": 0}).to_list(50)
            bmap = {}
            bids = [r["batch_id"] for r in rows]
            async for b in db.batches.find({"id": {"$in": bids}}, {"_id": 0}):
                bmap[b["id"]] = b
            rows.sort(key=lambda r: bmap.get(r["batch_id"], {}).get("manufactured_on", ""))
            need = ln["qty"]
            for r in rows:
                if need <= 0: break
                take = min(r["available"], need)
                if take <= 0: continue
                await db.retailer_inventory.update_one({"id": r["id"]}, {"$inc": {"available": -take}})
                await db.stock_ledger.insert_one({
                    "id": new_id("led"), "timestamp": now_iso(),
                    "movement": "customer_sale", "scope": "retailer",
                    "partner_id": retailer_id,
                    "sku_id": ln["sku_id"], "sku_code": ln["sku_code"],
                    "batch_id": r["batch_id"], "qty": take,
                    "from_bucket": "available", "to_bucket": "sold",
                    "reference_type": "customer_order", "reference_id": order["id"],
                    "by_user": user.get("email"),
                    "notes": f"Sold to {customer['name']}",
                })
                need -= take

        # Generate customer invoice + AR ledger
        inv_id = new_id("inv")
        invoice = {
            "id": inv_id, "invoice_no": f"INV-{int(datetime.now().timestamp())}",
            "order_id": order["id"], "order_no": order["order_no"],
            "type": "customer",
            "retailer_id": retailer_id, "customer_id": customer_id,
            "party_id": customer_id, "party_name": customer["name"],
            "lines": lines_out,
            "subtotal": order["subtotal"], "discount": order["discount"],
            "tax": tax, "total": total, "paid": 0,
            "status": "issued", "issued_on": now_iso(),
            "due_on": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "created_by": user.get("email"),
        }
        await db.invoices.insert_one(invoice)
        # AR journal
        await post_journal(
            entries=[
                {"account": "AR", "debit": total, "credit": 0, "party_id": customer_id, "party_type": "customer", "party_name": customer["name"]},
                {"account": "SALES", "debit": 0, "credit": taxable, "party_id": customer_id, "party_type": "customer", "party_name": customer["name"]},
                {"account": "TAX_OUT", "debit": 0, "credit": tax, "party_id": customer_id, "party_type": "customer", "party_name": customer["name"]},
                *([{"account": "DISCOUNT", "debit": discount, "credit": 0, "party_id": customer_id, "party_type": "customer", "party_name": customer["name"]}] if discount > 0 else []),
                *([{"account": "SALES", "debit": 0, "credit": discount, "party_id": customer_id, "party_type": "customer", "party_name": customer["name"]}] if discount > 0 else []),
            ],
            reference_type="invoice", reference_id=inv_id,
            narration=f"Sale to {customer['name']} via {retailer['name']}", actor=user.get("email"),
        )
        await recompute_outstanding("customer", customer_id)

        # Create pending cashback rows
        for m in cb["matches"]:
            cb_row = {
                "id": new_id("cb"),
                "retailer_id": retailer_id,
                "customer_id": customer_id,
                "party_id": customer_id, "party_type": "customer",
                "party_name": customer["name"],
                "campaign": m["rule_name"],
                "rule_id": m["rule_id"],
                "earned": m["amount"], "redeemed": 0,
                "reference_id": order["id"],
                "status": "Pending" if m["approval_required"] else "Credited",
                "issued_on": now_iso(),
            }
            await db.cashback.insert_one(cb_row)
            if not m["approval_required"]:
                await wallet_credit(customer_id, "customer", m["amount"], f"Auto cashback: {m['rule_name']}", order["id"], user.get("email"))
                await post_journal(
                    entries=[
                        {"account": "CASHBACK_EXP", "debit": m["amount"], "credit": 0, "party_id": customer_id, "party_type": "customer"},
                        {"account": "CASHBACK_LIAB", "debit": 0, "credit": m["amount"], "party_id": customer_id, "party_type": "customer"},
                    ], reference_type="cashback", reference_id=cb_row["id"],
                    narration=f"Cashback auto-credit for order {order['order_no']}", actor=user.get("email"),
                )

        await audit("create_customer_order", "customer_order", order["id"], user.get("email"), meta={"total": total, "discount": discount})
        return {**strip_id(order), "invoice_id": inv_id, "invoice_no": invoice["invoice_no"]}

    @router.post("/customer-orders/{order_id}/pack")
    async def pack_customer_order(order_id: str, user: dict = Depends(get_current_user)):
        await db.customer_orders.update_one({"id": order_id}, {"$set": {"status": "packed", "packed_at": now_iso()}})
        return {"ok": True}

    @router.post("/customer-orders/{order_id}/deliver")
    async def deliver_customer_order(order_id: str, user: dict = Depends(get_current_user)):
        await db.customer_orders.update_one({"id": order_id}, {"$set": {"status": "delivered", "delivered_at": now_iso()}})
        return {"ok": True}

    @router.post("/customer-orders/{order_id}/cancel")
    async def cancel_customer_order(order_id: str, payload: Dict[str, Any] = Body(default={}), user: dict = Depends(get_current_user)):
        # A production impl would restock inventory; keeping simple for now.
        await db.customer_orders.update_one({"id": order_id}, {"$set": {"status": "cancelled", "cancelled_at": now_iso(), "cancel_reason": payload.get("reason", "")}})
        return {"ok": True}

    # ==========================================================
    # PAYMENT ENGINE
    # ==========================================================
    @router.post("/payments")
    async def record_payment(payload: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        party_id = payload.get("party_id")
        party_type = payload.get("party_type", "distributor")
        amount = float(payload.get("amount", 0) or 0)
        method = payload.get("method", "Bank Transfer")
        invoice_ids = payload.get("invoice_ids", [])  # optional allocation targets
        if not party_id or amount <= 0:
            raise HTTPException(400, "party_id and positive amount required")

        # Fetch party
        party_coll = f"{party_type}s"
        party = await db[party_coll].find_one({"id": party_id}, {"_id": 0})
        if not party: raise HTTPException(404, f"{party_type} not found")

        payment = {
            "id": new_id("pay"),
            "payment_no": f"PAY-{int(datetime.now().timestamp())}",
            "party_id": party_id, "party_type": party_type,
            "party_name": party.get("name"),
            "amount": round(amount, 2),
            "mode": method, "method": method,
            "reference": payload.get("reference", f"REF{int(datetime.now().timestamp())}"),
            "transaction_no": payload.get("transaction_no"),
            "received_on": payload.get("received_on") or now_iso(),
            "status": "Cleared", "notes": payload.get("notes", ""),
            "created_by": user.get("email"),
            "allocations": [],
            "unallocated": round(amount, 2),
        }

        # Determine invoices to allocate to
        if not invoice_ids:
            # Auto-allocate oldest unpaid first
            cursor = db.invoices.find({"party_id": party_id, "status": {"$ne": "cancelled"}}, {"_id": 0}).sort("issued_on", 1)
            invs = await cursor.to_list(100)
            invoice_ids = [i["id"] for i in invs if float(i.get("paid", 0) or 0) < float(i.get("total", 0) or 0)]

        remaining = amount
        allocations = []
        for iid in invoice_ids:
            if remaining <= 0.01: break
            inv = await db.invoices.find_one({"id": iid}, {"_id": 0})
            if not inv: continue
            total = float(inv.get("total", 0) or 0)
            paid = float(inv.get("paid", 0) or 0)
            due = round(total - paid, 2)
            if due <= 0: continue
            alloc = min(remaining, due)
            new_paid = round(paid + alloc, 2)
            new_status = "Paid" if abs(new_paid - total) < 0.01 else ("Partial" if new_paid > 0 else "Unpaid")
            await db.invoices.update_one({"id": iid}, {"$set": {"paid": new_paid, "payment_status": new_status, "last_payment_at": now_iso()}})
            allocations.append({"invoice_id": iid, "invoice_no": inv.get("invoice_no"), "amount": alloc, "new_paid": new_paid, "new_status": new_status})
            await db.payment_allocations.insert_one({
                "id": new_id("pal"), "payment_id": payment["id"], "invoice_id": iid,
                "amount": alloc, "timestamp": now_iso(),
            })
            remaining -= alloc

        payment["allocations"] = allocations
        payment["unallocated"] = round(remaining, 2)
        await db.payments.insert_one(payment)

        # Ledger: Cash Dr / AR Cr
        await post_journal(
            entries=[
                {"account": "CASH", "debit": amount, "credit": 0, "party_id": party_id, "party_type": party_type, "party_name": party.get("name")},
                {"account": "AR", "debit": 0, "credit": amount, "party_id": party_id, "party_type": party_type, "party_name": party.get("name")},
            ],
            reference_type="payment", reference_id=payment["id"],
            narration=f"Payment received from {party.get('name')} via {method}", actor=user.get("email"),
        )
        await recompute_outstanding(party_type, party_id)
        await audit("record_payment", "payment", payment["id"], user.get("email"), meta={"amount": amount, "party": party.get("name"), "allocations": len(allocations)})
        return strip_id(payment)

    @router.post("/payments/{payment_id}/reverse")
    async def reverse_payment(payment_id: str, payload: Dict[str, Any] = Body(default={}), user: dict = Depends(get_current_user)):
        p = await db.payments.find_one({"id": payment_id}, {"_id": 0})
        if not p: raise HTTPException(404, "Payment not found")
        if p.get("status") == "Reversed":
            raise HTTPException(400, "Already reversed")
        amount = float(p["amount"])
        # Undo allocations
        for a in p.get("allocations", []):
            inv = await db.invoices.find_one({"id": a["invoice_id"]}, {"_id": 0})
            if inv:
                new_paid = max(0, round(float(inv.get("paid", 0)) - a["amount"], 2))
                new_status = "Paid" if abs(new_paid - inv["total"]) < 0.01 else ("Partial" if new_paid > 0 else "Unpaid")
                await db.invoices.update_one({"id": a["invoice_id"]}, {"$set": {"paid": new_paid, "payment_status": new_status}})
        # Reverse ledger
        await post_journal(
            entries=[
                {"account": "AR", "debit": amount, "credit": 0, "party_id": p["party_id"], "party_type": p["party_type"], "party_name": p.get("party_name")},
                {"account": "CASH", "debit": 0, "credit": amount, "party_id": p["party_id"], "party_type": p["party_type"], "party_name": p.get("party_name")},
            ],
            reference_type="payment_reversal", reference_id=payment_id,
            narration=f"Payment reversal: {payload.get('reason','')}", actor=user.get("email"),
        )
        await db.payments.update_one({"id": payment_id}, {"$set": {"status": "Reversed", "reversed_at": now_iso(), "reverse_reason": payload.get("reason", "")}})
        await recompute_outstanding(p["party_type"], p["party_id"])
        await audit("reverse_payment", "payment", payment_id, user.get("email"))
        return {"ok": True}

    # ==========================================================
    # QUERIES
    # ==========================================================
    @router.get("/outstanding/{party_type}/{party_id}")
    async def get_outstanding(party_type: str, party_id: str, user: dict = Depends(get_current_user)):
        rec = await db.outstanding.find_one({"party_id": party_id, "party_type": party_type}, {"_id": 0})
        if not rec:
            rec = await recompute_outstanding(party_type, party_id)
        return rec

    @router.get("/outstanding")
    async def list_outstanding(party_type: Optional[str] = None, user: dict = Depends(get_current_user)):
        q = {}
        if party_type: q["party_type"] = party_type
        rows = await db.outstanding.find(q, {"_id": 0}).sort("outstanding", -1).to_list(500)
        return {"data": rows, "count": len(rows)}

    @router.get("/wallets/{party_type}/{party_id}")
    async def get_wallet_endpoint(party_type: str, party_id: str, user: dict = Depends(get_current_user)):
        w = await get_wallet(party_id, party_type)
        txns = await db.cashback_transactions.find({"party_id": party_id, "party_type": party_type}, {"_id": 0}).sort("timestamp", -1).to_list(100)
        return {"wallet": w, "transactions": txns}

    @router.get("/ledger/{party_type}/{party_id}")
    async def get_party_ledger(party_type: str, party_id: str, user: dict = Depends(get_current_user)):
        rows = await db.double_ledger.find({"party_id": party_id, "party_type": party_type}, {"_id": 0}).sort("timestamp", 1).to_list(1000)
        # running balance per account
        balances: Dict[str, float] = {}
        for r in rows:
            acc = r["account"]
            balances[acc] = balances.get(acc, 0) + (r.get("debit", 0) - r.get("credit", 0))
            r["running_balance"] = round(balances[acc], 2)
        return {"data": rows, "count": len(rows), "balances": {k: round(v, 2) for k, v in balances.items()}}

    @router.get("/ledger")
    async def full_ledger(account: Optional[str] = None, party_type: Optional[str] = None,
                          limit: int = 500, user: dict = Depends(get_current_user)):
        q = {}
        if account: q["account"] = account
        if party_type: q["party_type"] = party_type
        rows = await db.double_ledger.find(q, {"_id": 0}).sort("timestamp", -1).to_list(limit)
        return {"data": rows, "count": len(rows)}

    @router.get("/audit-log")
    async def list_audit(entity_type: Optional[str] = None, actor: Optional[str] = None,
                          limit: int = 200, user: dict = Depends(get_current_user)):
        q = {}
        if entity_type: q["entity_type"] = entity_type
        if actor: q["actor"] = actor
        rows = await db.audit_log.find(q, {"_id": 0}).sort("timestamp", -1).to_list(limit)
        return {"data": rows, "count": len(rows)}

    # ==========================================================
    # RECONCILIATION
    # ==========================================================
    @router.post("/reconciliation/run")
    async def reconciliation_run(payload: Dict[str, Any] = Body(default={}), user: dict = Depends(get_current_user)):
        """Match invoices against payments and generate a variance report."""
        party_type = payload.get("party_type", "distributor")
        rows = []
        parties = await db[f"{party_type}s"].find({}, {"_id": 0}).to_list(500)
        for p in parties:
            invs = await db.invoices.find({"party_id": p["id"], "status": {"$ne": "cancelled"}}, {"_id": 0}).to_list(500)
            total_billed = sum(float(i.get("total", 0) or 0) for i in invs)
            total_paid = sum(float(i.get("paid", 0) or 0) for i in invs)
            payments_recv = 0.0
            async for pay in db.payments.find({"party_id": p["id"], "status": {"$ne": "Reversed"}}, {"_id": 0}):
                payments_recv += float(pay.get("amount", 0) or 0)
            variance = round(total_paid - payments_recv, 2)
            rows.append({
                "party_id": p["id"], "party_name": p["name"], "party_type": party_type,
                "total_billed": round(total_billed, 2),
                "total_paid_invoices": round(total_paid, 2),
                "total_payments_recv": round(payments_recv, 2),
                "variance": variance,
                "outstanding": round(total_billed - total_paid, 2),
                "status": "Balanced" if abs(variance) < 0.01 else "Variance",
            })
        report = {
            "id": new_id("rec"),
            "run_at": now_iso(), "run_by": user.get("email"),
            "party_type": party_type,
            "rows": rows,
            "summary": {
                "total_parties": len(rows),
                "balanced": sum(1 for r in rows if r["status"] == "Balanced"),
                "variance": sum(1 for r in rows if r["status"] == "Variance"),
            },
        }
        await db.reconciliation_reports.insert_one(report)
        return strip_id(report)

    @router.get("/reconciliation/reports")
    async def list_recon(user: dict = Depends(get_current_user)):
        rows = await db.reconciliation_reports.find({}, {"_id": 0}).sort("run_at", -1).to_list(50)
        return {"data": rows, "count": len(rows)}

    # ==========================================================
    # AUTO-POST HISTORICAL INVOICES INTO LEDGER (idempotent)
    # ==========================================================
    async def autopost_existing_invoices():
        """Ensure every existing invoice has a matching AR ledger journal + outstanding."""
        # If double_ledger already has AR entries, skip
        existing = await db.double_ledger.count_documents({"account": "AR"})
        if existing > 0:
            return
        async for inv in db.invoices.find({}, {"_id": 0}):
            if inv.get("status") == "cancelled": continue
            total = float(inv.get("total", 0) or 0)
            tax = float(inv.get("tax", 0) or 0)
            discount = float(inv.get("discount", 0) or 0)
            taxable = round(total - tax, 2)
            party_type = "distributor" if inv.get("type") == "primary" else ("retailer" if inv.get("type") == "secondary" else "customer")
            party_id = inv.get("party_id") or inv.get("distributor_id") or inv.get("retailer_id") or inv.get("customer_id")
            if not party_id: continue
            entries = [
                {"account": "AR", "debit": total, "credit": 0, "party_id": party_id, "party_type": party_type, "party_name": inv.get("party_name")},
                {"account": "SALES", "debit": 0, "credit": taxable, "party_id": party_id, "party_type": party_type, "party_name": inv.get("party_name")},
                {"account": "TAX_OUT", "debit": 0, "credit": tax, "party_id": party_id, "party_type": party_type, "party_name": inv.get("party_name")},
            ]
            await post_journal(entries=entries, reference_type="invoice", reference_id=inv["id"],
                                narration=f"Invoice {inv.get('invoice_no')}", actor="system@gooil.com")
        # Recompute outstanding for all parties
        for pt in ("distributor", "retailer", "customer"):
            parties = await db[f"{pt}s"].find({}, {"_id": 0}).to_list(500)
            for p in parties:
                await recompute_outstanding(pt, p["id"])

    router.autopost_existing_invoices = autopost_existing_invoices  # expose to caller
    router.recompute_outstanding = recompute_outstanding

    return router
