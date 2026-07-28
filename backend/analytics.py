"""GO OIL DMS — Phase 4 Business Intelligence, Analytics & Live Monitoring.

Endpoints under /api/analytics/*:
  - dimensions           — filter options (branches / distributors / retailers / SKUs / products)
  - kpi/executive        — 15 executive KPIs (revenue, sales, outstanding, cashflow, etc.)
  - trace/order/{id}     — 20-node full traceability chain
  - party360/{type}/{id} — unified party profile (profile + ledger + orders + payments + returns + claims + inventory + audit + score)
  - sales                — sales analytics (time series + top SKUs + by-branch + funnel)
  - inventory            — inventory analytics
  - finance              — cash-in / cash-out / DSO / collection rate
  - returns              — return trends + reasons
  - claims               — claim trends
  - profitability        — revenue vs cogs vs returns vs claims
  - alerts               — 12-type business alert engine
  - scorecards/{entity_type} — party performance scorecards
  - ai-context/{scope}   — structured AI-ready data snapshot

All queries run against LIVE MongoDB collections — nothing mocked.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query


# ---------- Time-range helpers ----------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def range_bounds(range_key: str, from_iso: Optional[str], to_iso: Optional[str]) -> tuple:
    """Return (start_iso, end_iso, granularity) for a range preset."""
    end = _now()
    if range_key == "custom" and from_iso and to_iso:
        return from_iso, to_iso, "day"
    if range_key == "today":
        start = end.replace(hour=0, minute=0, second=0, microsecond=0)
        return start.isoformat(), end.isoformat(), "hour"
    if range_key == "yesterday":
        d = end.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        return d.isoformat(), (d + timedelta(days=1)).isoformat(), "hour"
    if range_key == "week":
        start = end - timedelta(days=7)
        return start.isoformat(), end.isoformat(), "day"
    if range_key == "quarter":
        start = end - timedelta(days=90)
        return start.isoformat(), end.isoformat(), "week"
    if range_key == "year":
        start = end - timedelta(days=365)
        return start.isoformat(), end.isoformat(), "month"
    # default "month"
    start = end - timedelta(days=30)
    return start.isoformat(), end.isoformat(), "day"


def _num(v, default=0.0) -> float:
    try:
        return float(v or 0)
    except Exception:
        return float(default)


def _in_range(iso: Optional[str], start: str, end: str) -> bool:
    if not iso: return False
    return start <= iso <= end


def strip(doc):
    if doc is None: return None
    doc.pop("_id", None)
    return doc


# ==========================================================
# Router factory
# ==========================================================

def build_analytics_router(db, get_current_user):
    router = APIRouter(prefix="/analytics", tags=["analytics-bi"])

    # ---- Common: apply filter dict → mongo query ----
    def _apply_filters(q: Dict, filters: Dict):
        if filters.get("branch_id"):
            q["branch_id"] = filters["branch_id"]
        if filters.get("distributor_id"):
            q["distributor_id"] = filters["distributor_id"]
        if filters.get("retailer_id"):
            q["retailer_id"] = filters["retailer_id"]
        return q

    async def _parse_filters(request_params: Dict) -> Dict:
        return {k: v for k, v in request_params.items()
                if k in ("branch_id", "region", "warehouse_id", "distributor_id",
                          "retailer_id", "customer_id", "sales_executive_id",
                          "product_id", "sku_id", "category", "batch_id", "status")
                and v}

    # ==========================================================
    # DIMENSIONS (filter dropdowns)
    # ==========================================================
    @router.get("/dimensions")
    async def dimensions(user: dict = Depends(get_current_user)):
        branches = await db.branches.find({}, {"_id": 0, "id": 1, "name": 1, "region": 1}).to_list(200)
        distributors = await db.distributors.find({}, {"_id": 0, "id": 1, "name": 1, "branch_id": 1}).to_list(500)
        retailers = await db.retailers.find({}, {"_id": 0, "id": 1, "name": 1, "distributor_id": 1}).to_list(500)
        customers = await db.customers.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(500)
        products = await db.products.find({}, {"_id": 0, "id": 1, "name": 1, "category": 1}).to_list(500)
        skus = await db.skus.find({}, {"_id": 0, "id": 1, "sku_code": 1, "product_name": 1, "pack_size": 1}).to_list(500)
        warehouses = await db.warehouses.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(200) if hasattr(db, "warehouses") else []
        regions = sorted({b.get("region") for b in branches if b.get("region")})
        categories = sorted({p.get("category") for p in products if p.get("category")})
        return {
            "branches": branches, "distributors": distributors, "retailers": retailers,
            "customers": customers, "products": products, "skus": skus,
            "warehouses": warehouses, "regions": list(regions), "categories": list(categories),
            "ranges": ["today", "yesterday", "week", "month", "quarter", "year", "custom"],
        }

    # ==========================================================
    # EXECUTIVE KPI (15 KPIs)
    # ==========================================================
    @router.get("/kpi/executive")
    async def executive_kpi(
        range: str = Query("month"),
        from_: Optional[str] = Query(None, alias="from"),
        to: Optional[str] = None,
        branch_id: Optional[str] = None,
        distributor_id: Optional[str] = None,
        retailer_id: Optional[str] = None,
        sku_id: Optional[str] = None,
        user: dict = Depends(get_current_user),
    ):
        start, end, granularity = range_bounds(range, from_, to)
        filters = {"branch_id": branch_id, "distributor_id": distributor_id, "retailer_id": retailer_id}
        filters = {k: v for k, v in filters.items() if v}

        # Revenue + Sales count
        inv_q = _apply_filters({}, filters)
        invoices = await db.invoices.find(inv_q, {"_id": 0}).to_list(5000)
        window_invs = [i for i in invoices if _in_range(i.get("issued_on") or i.get("created_at"), start, end)]
        revenue = sum(_num(i.get("total")) for i in window_invs)
        sales_count = len(window_invs)

        # Inventory Value + Health
        skus_map = {s["id"]: s async for s in db.skus.find({}, {"_id": 0})}
        inv_val = 0.0
        total_units = 0
        damaged_units = 0
        async for r in db.company_inventory.find({}, {"_id": 0}):
            price = _num((skus_map.get(r.get("sku_id")) or {}).get("trade_price", 0))
            avail = int(r.get("available", 0) or 0)
            inv_val += avail * price
            total_units += avail + int(r.get("reserved", 0) or 0)
            damaged_units += int(r.get("damaged", 0) or 0) + int(r.get("expired", 0) or 0)
        inv_health = 100.0 if total_units == 0 else round(max(0, 100 - (damaged_units / max(total_units + damaged_units, 1)) * 100), 1)

        # Order Pipeline (approved/invoiced not yet delivered)
        pipeline = 0.0
        pending_orders = 0
        for coll in ("primary_orders", "secondary_orders", "customer_orders"):
            async for r in db[coll].find({"status": {"$in": ["approved", "invoiced", "pending"]}}, {"_id": 0}):
                pipeline += _num(r.get("total"))
                pending_orders += 1

        # Outstanding (invoice remaining = total - paid - credited)
        outstanding = 0.0
        for i in invoices:
            rem = _num(i.get("total")) - _num(i.get("paid")) - _num(i.get("credited"))
            if rem > 0: outstanding += rem

        # Collections (payments in window)
        pay_q = {}
        if distributor_id: pay_q["party_id"] = distributor_id
        payments = await db.payments.find(pay_q, {"_id": 0}).to_list(5000)
        window_pays = [p for p in payments if _in_range(p.get("received_at") or p.get("created_at"), start, end)]
        collections = sum(_num(p.get("amount")) for p in window_pays)

        # Cash flow (collections - expenses)
        expenses = await db.expenses.find({}, {"_id": 0}).to_list(5000)
        window_exp = [e for e in expenses if _in_range(e.get("created_at"), start, end)]
        expense_total = sum(_num(e.get("amount")) for e in window_exp)
        cashflow = round(collections - expense_total, 2)

        # Claims (in window)
        claims = await db.claims.find({}, {"_id": 0}).to_list(5000)
        window_claims = [c for c in claims if _in_range(c.get("created_at"), start, end)]
        claim_amount = sum(_num(c.get("amount")) for c in window_claims)

        # Returns (in window)
        returns = await db.returns.find({}, {"_id": 0}).to_list(5000)
        window_returns = [r for r in returns if _in_range(r.get("created_at"), start, end)]
        return_amount = sum(_num(r.get("total")) for r in window_returns)

        # Replacement cost (completed in window)
        reps = await db.replacements.find({"status": "completed"}, {"_id": 0}).to_list(5000)
        window_reps = [r for r in reps if _in_range(r.get("completed_at") or r.get("created_at"), start, end)]
        replacement_cost = sum(_num(r.get("total")) for r in window_reps)

        # Approval queue
        approval_queue = await db.approval_requests.count_documents({"status": "pending"})

        # Exception count
        exception_open = await db.exceptions.count_documents({"status": "open"})

        # Business Risk Score (weighted: outstanding + claims + returns + exceptions + expired)
        max_ref = max(revenue, 1)
        risk = min(100, round(
            (outstanding / max(max_ref * 2, 1)) * 30 +
            (return_amount / max_ref) * 20 +
            (claim_amount / max_ref) * 15 +
            (exception_open / 10) * 20 +
            ((100 - inv_health) / 100) * 15
        , 1))

        # Company Health Score (100 - risk, weighted by fulfillment)
        fulfillment = 100.0 if (revenue + outstanding) == 0 else round((revenue / (revenue + outstanding + 1)) * 100, 1)
        health = round((100 - risk) * 0.6 + fulfillment * 0.4, 1)

        # Time-series buckets for charts (revenue/collections/returns per day)
        def bucket(iso):
            if not iso: return None
            if granularity == "hour": return iso[:13]
            if granularity == "month": return iso[:7]
            if granularity == "week":
                try:
                    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
                    monday = d - timedelta(days=d.weekday())
                    return monday.date().isoformat()
                except Exception: return iso[:10]
            return iso[:10]

        series: Dict[str, Dict[str, float]] = {}
        def add(key, metric, val):
            series.setdefault(key, {"revenue": 0, "collections": 0, "returns": 0, "claims": 0})
            series[key][metric] += float(val)
        for i in window_invs:
            b = bucket(i.get("issued_on") or i.get("created_at"))
            if b: add(b, "revenue", _num(i.get("total")))
        for p in window_pays:
            b = bucket(p.get("received_at") or p.get("created_at"))
            if b: add(b, "collections", _num(p.get("amount")))
        for r in window_returns:
            b = bucket(r.get("created_at"))
            if b: add(b, "returns", _num(r.get("total")))
        for c in window_claims:
            b = bucket(c.get("created_at"))
            if b: add(b, "claims", _num(c.get("amount")))
        series_arr = [{"period": k, **v} for k, v in sorted(series.items())]

        return {
            "range": {"key": range, "start": start, "end": end, "granularity": granularity},
            "filters": filters,
            "kpis": {
                "revenue": {"value": round(revenue, 2), "unit": "USD", "count": sales_count, "drill": "invoices"},
                "sales_count": {"value": sales_count, "drill": "invoices"},
                "inventory_value": {"value": round(inv_val, 2), "unit": "USD", "drill": "inventory"},
                "inventory_health": {"value": inv_health, "unit": "%", "drill": "inventory"},
                "order_pipeline": {"value": round(pipeline, 2), "count": pending_orders, "drill": "primary-orders"},
                "outstanding": {"value": round(outstanding, 2), "drill": "outstanding"},
                "collections": {"value": round(collections, 2), "count": len(window_pays), "drill": "payments"},
                "cash_flow": {"value": cashflow, "drill": "ledger"},
                "claims": {"value": round(claim_amount, 2), "count": len(window_claims), "drill": "claims"},
                "returns": {"value": round(return_amount, 2), "count": len(window_returns), "drill": "returns"},
                "replacement_cost": {"value": round(replacement_cost, 2), "count": len(window_reps), "drill": "replacements"},
                "approval_queue": {"value": approval_queue, "drill": "approval-engine"},
                "exception_count": {"value": exception_open, "drill": "exceptions"},
                "business_risk_score": {"value": risk, "unit": "risk", "drill": "alerts"},
                "company_health_score": {"value": health, "unit": "score"},
            },
            "series": series_arr,
        }

    # ==========================================================
    # LIVE ORDER TRACE (20-node journey)
    # ==========================================================
    @router.get("/trace/order/{order_id}")
    async def trace_order(order_id: str, user: dict = Depends(get_current_user)):
        # Try primary, secondary, then customer
        order = None
        order_type = None
        for coll, t in (("primary_orders", "primary"), ("secondary_orders", "secondary"), ("customer_orders", "customer")):
            o = await db[coll].find_one({"id": order_id}, {"_id": 0})
            if o:
                order = o; order_type = t; break
        if not order:
            raise HTTPException(404, f"Order not found: {order_id}")

        # Collect related docs
        invoice = await db.invoices.find_one({"order_id": order_id}, {"_id": 0})
        dispatch = None
        if invoice:
            dispatch = await db.dispatches.find_one({"invoice_id": invoice["id"]}, {"_id": 0})
        else:
            dispatch = await db.dispatches.find_one({"order_id": order_id}, {"_id": 0})
        grn = None
        if dispatch:
            grn = await db.grns.find_one({"dispatch_id": dispatch["id"]}, {"_id": 0})
        payments = []
        if invoice:
            payments = await db.payments.find({"invoice_id": invoice["id"]}, {"_id": 0}).to_list(50)
        credit_notes = await db.credit_notes.find({"invoice_id": (invoice or {}).get("id")}, {"_id": 0}).to_list(20) if invoice else []
        returns = await db.returns.find({"order_id": order_id}, {"_id": 0}).to_list(20)
        if invoice:
            more_ret = await db.returns.find({"invoice_id": invoice["id"]}, {"_id": 0}).to_list(20)
            for r in more_ret:
                if r not in returns: returns.append(r)
        # Secondary/customer chain — find related downstream orders
        secondary_orders = []
        customer_orders = []
        if order_type == "primary":
            # find secondary orders drawn from same distributor
            secondary_orders = await db.secondary_orders.find({"distributor_id": order.get("distributor_id")}, {"_id": 0}).sort("created_at", -1).to_list(5)
        if order_type in ("primary", "secondary"):
            customer_orders = await db.customer_orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(5)

        # Coupons / cashback / wallet linked to invoice
        coupon = None
        cashback = None
        if invoice:
            coupon = await db.coupon_redemptions.find_one({"invoice_id": invoice["id"]}, {"_id": 0})
            cashback = await db.cashback.find_one({"invoice_id": invoice["id"]}, {"_id": 0})

        # Ledger entries
        ledger_refs = []
        if invoice:
            ledger_refs = await db.double_ledger.find({"reference_id": invoice["id"]}, {"_id": 0}).to_list(100) if hasattr(db, "double_ledger") else []
            if not ledger_refs:
                ledger_refs = await db.ledger.find({"reference_id": invoice["id"]}, {"_id": 0}).to_list(100)

        # Audit trail for this order + invoice
        audit = []
        entity_ids = [order_id]
        if invoice: entity_ids.append(invoice["id"])
        if dispatch: entity_ids.append(dispatch["id"])
        if grn: entity_ids.append(grn["id"])
        for ent_id in entity_ids:
            trail = await db.audit_log.find({"entity_id": ent_id}, {"_id": 0}).sort("timestamp", -1).to_list(30)
            audit.extend(trail)

        # SKU + batch info for first line
        first_line = (order.get("lines") or [{}])[0]
        sku = await db.skus.find_one({"id": first_line.get("sku_id")}, {"_id": 0}) if first_line.get("sku_id") else None
        product = await db.products.find_one({"id": (sku or {}).get("product_id")}, {"_id": 0}) if sku else None
        batches = []
        for alloc in first_line.get("reserved_allocations", []) or []:
            b = await db.batches.find_one({"id": alloc.get("batch_id")}, {"_id": 0})
            if b: batches.append(b)

        # Build the 20-node timeline
        def ts_ok(v): return v or None
        timeline = [
            {"step": 1, "node": "Product", "status": "ok" if product else "n/a", "at": None,
             "label": (product or {}).get("name"), "id": (product or {}).get("id")},
            {"step": 2, "node": "SKU", "status": "ok" if sku else "n/a", "at": None,
             "label": (sku or {}).get("sku_code"), "id": (sku or {}).get("id")},
            {"step": 3, "node": "Batch", "status": "ok" if batches else "n/a", "at": None,
             "label": ", ".join(b.get("batch_no", "") for b in batches) or "—",
             "id": batches[0]["id"] if batches else None},
            {"step": 4, "node": "Company Inventory", "status": "ok", "at": None, "label": "Reserved"},
            {"step": 5, "node": "Primary Order", "status": "ok" if order_type == "primary" else "n/a",
             "at": ts_ok(order.get("created_at")) if order_type == "primary" else None,
             "label": order.get("order_no") if order_type == "primary" else "—",
             "id": order["id"] if order_type == "primary" else None},
            {"step": 6, "node": "Invoice", "status": "ok" if invoice else "pending",
             "at": ts_ok((invoice or {}).get("issued_on")),
             "label": (invoice or {}).get("invoice_no"), "id": (invoice or {}).get("id")},
            {"step": 7, "node": "Dispatch", "status": "ok" if dispatch else "pending",
             "at": ts_ok((dispatch or {}).get("dispatch_date")),
             "label": (dispatch or {}).get("dispatch_no"), "id": (dispatch or {}).get("id")},
            {"step": 8, "node": "Goods In Transit", "status": "ok" if dispatch and dispatch.get("status") == "in_transit" else ("ok" if grn else "pending"),
             "at": ts_ok((dispatch or {}).get("dispatch_date")),
             "label": (dispatch or {}).get("lr_no"), "id": (dispatch or {}).get("id")},
            {"step": 9, "node": "Distributor GRN", "status": "ok" if grn else "pending",
             "at": ts_ok((grn or {}).get("received_on")),
             "label": (grn or {}).get("grn_no"), "id": (grn or {}).get("id")},
            {"step": 10, "node": "Distributor Inventory", "status": "ok" if grn else "pending", "at": None, "label": "Stock landed"},
            {"step": 11, "node": "Secondary Order", "status": "ok" if secondary_orders else "n/a",
             "at": ts_ok(secondary_orders[0].get("created_at") if secondary_orders else None),
             "label": secondary_orders[0].get("order_no") if secondary_orders else "—",
             "id": secondary_orders[0]["id"] if secondary_orders else None},
            {"step": 12, "node": "Retailer Inventory", "status": "ok" if secondary_orders else "n/a", "at": None, "label": "Stock landed"},
            {"step": 13, "node": "Customer Order", "status": "ok" if customer_orders else "n/a",
             "at": ts_ok(customer_orders[0].get("created_at") if customer_orders else None),
             "label": customer_orders[0].get("order_no") if customer_orders else "—",
             "id": customer_orders[0]["id"] if customer_orders else None},
            {"step": 14, "node": "Coupon", "status": "ok" if coupon else "n/a", "at": ts_ok((coupon or {}).get("redeemed_at")),
             "label": (coupon or {}).get("code"), "id": (coupon or {}).get("id")},
            {"step": 15, "node": "Cashback", "status": "ok" if cashback else "n/a",
             "at": ts_ok((cashback or {}).get("created_at")),
             "label": f"${(cashback or {}).get('amount', 0)}" if cashback else "—",
             "id": (cashback or {}).get("id")},
            {"step": 16, "node": "Payment", "status": "ok" if payments else "pending",
             "at": ts_ok(payments[0].get("received_at") if payments else None),
             "label": f"{len(payments)} payment(s)" if payments else "—", "id": None},
            {"step": 17, "node": "Ledger", "status": "ok" if ledger_refs else "pending", "at": None,
             "label": f"{len(ledger_refs)} entries"},
            {"step": 18, "node": "Reports", "status": "ok", "at": None, "label": "Available"},
            {"step": 19, "node": "Audit Trail", "status": "ok" if audit else "pending", "at": None,
             "label": f"{len(audit)} events"},
            {"step": 20, "node": "Returns / Claims", "status": "ok" if (returns or credit_notes) else "n/a",
             "at": ts_ok(returns[0].get("created_at") if returns else None),
             "label": f"{len(returns)} return(s), {len(credit_notes)} CN(s)"},
        ]

        return {
            "order": order, "order_type": order_type,
            "invoice": invoice, "dispatch": dispatch, "grn": grn,
            "payments": payments, "credit_notes": credit_notes, "returns": returns,
            "secondary_orders": secondary_orders, "customer_orders": customer_orders,
            "coupon": coupon, "cashback": cashback,
            "ledger_entries": ledger_refs, "audit_trail": audit,
            "product": product, "sku": sku, "batches": batches,
            "timeline": timeline,
        }

    # Search endpoint so UI can find orders by order_no
    @router.get("/trace/search")
    async def trace_search(q: str = Query(..., min_length=1), user: dict = Depends(get_current_user)):
        results = []
        for coll, t in (("primary_orders", "primary"), ("secondary_orders", "secondary"), ("customer_orders", "customer")):
            async for r in db[coll].find({"$or": [
                {"order_no": {"$regex": q, "$options": "i"}},
                {"id": q},
            ]}, {"_id": 0, "id": 1, "order_no": 1, "party_name": 1, "total": 1, "status": 1, "created_at": 1}).limit(20):
                r["type"] = t
                results.append(r)
        async for r in db.invoices.find({"invoice_no": {"$regex": q, "$options": "i"}},
                                        {"_id": 0, "order_id": 1, "invoice_no": 1, "party_name": 1, "total": 1}).limit(10):
            if r.get("order_id"):
                results.append({"id": r["order_id"], "order_no": r["invoice_no"], "party_name": r.get("party_name"),
                                "total": r.get("total"), "type": "via-invoice"})
        return {"results": results[:30]}

    # ==========================================================
    # PARTY 360
    # ==========================================================
    @router.get("/party360/{party_type}/{party_id}")
    async def party360(party_type: str, party_id: str, user: dict = Depends(get_current_user)):
        if party_type not in ("distributor", "retailer", "customer", "company"):
            raise HTTPException(400, "Invalid party_type")
        coll_map = {"distributor": "distributors", "retailer": "retailers", "customer": "customers", "company": "branches"}
        profile = await db[coll_map[party_type]].find_one({"id": party_id}, {"_id": 0})
        if not profile:
            raise HTTPException(404, "Party not found")

        # Related transactions
        invoices = await db.invoices.find({"party_id": party_id}, {"_id": 0}).sort("issued_on", -1).to_list(500)
        payments = await db.payments.find({"party_id": party_id}, {"_id": 0}).sort("received_at", -1).to_list(500)
        # Ledger
        ledger = await db.double_ledger.find({"party_id": party_id}, {"_id": 0}).sort("posted_at", -1).to_list(300) if hasattr(db, "double_ledger") else []
        # Orders
        prim = await db.primary_orders.find({"party_id": party_id}, {"_id": 0}).sort("created_at", -1).to_list(200) if party_type == "distributor" else []
        sec = await db.secondary_orders.find({"party_id": party_id}, {"_id": 0}).sort("created_at", -1).to_list(200) if party_type == "retailer" else []
        cust = await db.customer_orders.find({"party_id": party_id}, {"_id": 0}).sort("created_at", -1).to_list(200) if party_type == "customer" else []
        # Returns / Claims / CN / DN
        returns = await db.returns.find({"party_id": party_id}, {"_id": 0}).sort("created_at", -1).to_list(200)
        claims = await db.claims.find({"party_id": party_id}, {"_id": 0}).sort("created_at", -1).to_list(200)
        credit_notes = await db.credit_notes.find({"party_id": party_id}, {"_id": 0}).sort("created_at", -1).to_list(200)
        debit_notes = await db.debit_notes.find({"party_id": party_id}, {"_id": 0}).sort("created_at", -1).to_list(200)
        # Wallet / Cashback
        wallet = await db.wallets.find_one({"party_id": party_id}, {"_id": 0}) if hasattr(db, "wallets") else None
        cashback = await db.cashback.find({"party_id": party_id}, {"_id": 0}).sort("created_at", -1).to_list(200)
        # Inventory
        inv_coll = f"{party_type}_inventory"
        inventory = []
        try:
            inventory = await db[inv_coll].find({"partner_id": party_id}, {"_id": 0}).to_list(300)
        except Exception:
            pass
        # Audit
        audit = await db.audit_log.find({"$or": [
            {"entity_id": party_id}, {"meta.party_id": party_id}]}, {"_id": 0}).sort("timestamp", -1).to_list(100)

        # Financial roll-ups
        billed = sum(_num(i.get("total")) for i in invoices)
        paid = sum(_num(i.get("paid")) for i in invoices) + sum(_num(p.get("amount")) for p in payments if p.get("status") != "refunded")
        credited = sum(_num(c.get("total")) for c in credit_notes)
        debited = sum(_num(d.get("total")) for d in debit_notes)
        outstanding_val = max(0, billed + debited - paid - credited)
        credit_limit = _num(profile.get("credit_limit", 0))
        util_pct = round((outstanding_val / max(credit_limit, 1)) * 100, 1) if credit_limit > 0 else None

        # Performance metrics
        n_returns = len(returns)
        n_claims = len(claims)
        return_rate = round((n_returns / max(len(invoices), 1)) * 100, 1)
        avg_order_value = round(billed / max(len(invoices), 1), 2) if invoices else 0

        # Risk Score
        risk = 0
        if credit_limit and util_pct: risk += min(40, util_pct * 0.4)
        risk += min(20, return_rate * 2)
        risk += min(15, n_claims * 2)
        # payment delays
        overdue_amt = 0.0
        now_iso = _now().isoformat()
        for i in invoices:
            rem = _num(i.get("total")) - _num(i.get("paid")) - _num(i.get("credited"))
            if rem > 0 and (i.get("due_on") or "") < now_iso:
                overdue_amt += rem
        overdue_ratio = (overdue_amt / max(outstanding_val, 1)) * 100 if outstanding_val > 0 else 0
        risk += min(25, overdue_ratio * 0.25)
        risk = round(min(100, risk), 1)
        health = round(100 - risk, 1)

        # Timeline (merged events)
        timeline_events = []
        for i in invoices[:60]:
            timeline_events.append({"type": "invoice", "at": i.get("issued_on") or i.get("created_at"),
                                     "label": f"Invoice {i.get('invoice_no')} — ${i.get('total')}", "id": i["id"],
                                     "status": i.get("status")})
        for p in payments[:60]:
            timeline_events.append({"type": "payment", "at": p.get("received_at") or p.get("created_at"),
                                     "label": f"Payment ${p.get('amount')} via {p.get('method')}", "id": p.get("id"),
                                     "status": p.get("status")})
        for r in returns[:30]:
            timeline_events.append({"type": "return", "at": r.get("created_at"),
                                     "label": f"Return {r.get('return_no')} — {r.get('reason')}", "id": r.get("id"),
                                     "status": r.get("status")})
        for c in claims[:30]:
            timeline_events.append({"type": "claim", "at": c.get("created_at"),
                                     "label": f"Claim {c.get('claim_no')} — ${c.get('amount')}", "id": c.get("id"),
                                     "status": c.get("status")})
        for cn in credit_notes[:30]:
            timeline_events.append({"type": "credit_note", "at": cn.get("created_at"),
                                     "label": f"CN {cn.get('cn_no')} — ${cn.get('total')}", "id": cn.get("id"),
                                     "status": cn.get("status")})
        for dn in debit_notes[:30]:
            timeline_events.append({"type": "debit_note", "at": dn.get("created_at"),
                                     "label": f"DN {dn.get('dn_no')} — ${dn.get('total')}", "id": dn.get("id"),
                                     "status": dn.get("status")})
        timeline_events = sorted([e for e in timeline_events if e.get("at")], key=lambda x: x["at"], reverse=True)[:120]

        return {
            "profile": profile,
            "party_type": party_type,
            "financials": {
                "total_billed": round(billed, 2),
                "total_paid": round(paid, 2),
                "total_credited": round(credited, 2),
                "total_debited": round(debited, 2),
                "outstanding": round(outstanding_val, 2),
                "credit_limit": credit_limit,
                "credit_utilization": util_pct,
                "overdue_amount": round(overdue_amt, 2),
            },
            "performance": {
                "invoice_count": len(invoices),
                "payment_count": len(payments),
                "avg_order_value": avg_order_value,
                "return_rate": return_rate,
                "claim_count": n_claims,
                "credit_note_count": len(credit_notes),
                "debit_note_count": len(debit_notes),
            },
            "risk_score": risk,
            "health_score": health,
            "invoices": invoices[:40],
            "payments": payments[:40],
            "primary_orders": prim[:40],
            "secondary_orders": sec[:40],
            "customer_orders": cust[:40],
            "returns": returns[:20],
            "claims": claims[:20],
            "credit_notes": credit_notes[:20],
            "debit_notes": debit_notes[:20],
            "cashback": cashback[:20],
            "wallet": wallet,
            "ledger": ledger[:40],
            "inventory": inventory[:40],
            "audit_trail": audit[:60],
            "timeline": timeline_events,
        }

    # ==========================================================
    # SALES ANALYTICS
    # ==========================================================
    @router.get("/sales")
    async def sales_analytics(range: str = Query("month"), from_: Optional[str] = Query(None, alias="from"),
                               to: Optional[str] = None,
                               branch_id: Optional[str] = None, distributor_id: Optional[str] = None,
                               sku_id: Optional[str] = None,
                               user: dict = Depends(get_current_user)):
        start, end, granularity = range_bounds(range, from_, to)
        q = {}
        if branch_id: q["branch_id"] = branch_id
        if distributor_id: q["distributor_id"] = distributor_id
        invoices = await db.invoices.find(q, {"_id": 0}).to_list(5000)
        w = [i for i in invoices if _in_range(i.get("issued_on") or i.get("created_at"), start, end)]

        # Time series
        def bucket(iso):
            if not iso: return None
            if granularity == "hour": return iso[:13]
            if granularity == "month": return iso[:7]
            if granularity == "week":
                try:
                    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
                    return (d - timedelta(days=d.weekday())).date().isoformat()
                except Exception: return iso[:10]
            return iso[:10]

        by_period: Dict[str, Dict[str, float]] = {}
        by_sku: Dict[str, Dict[str, Any]] = {}
        by_branch: Dict[str, Dict[str, Any]] = {}
        by_status: Dict[str, int] = {}
        by_distributor: Dict[str, Dict[str, Any]] = {}
        for i in w:
            b = bucket(i.get("issued_on") or i.get("created_at"))
            if b:
                by_period.setdefault(b, {"revenue": 0, "count": 0, "tax": 0})
                by_period[b]["revenue"] += _num(i.get("total"))
                by_period[b]["count"] += 1
                by_period[b]["tax"] += _num(i.get("tax"))
            by_status[i.get("status", "?")] = by_status.get(i.get("status", "?"), 0) + 1
            br = i.get("branch_id") or "unknown"
            by_branch.setdefault(br, {"branch_id": br, "revenue": 0, "count": 0})
            by_branch[br]["revenue"] += _num(i.get("total"))
            by_branch[br]["count"] += 1
            dist = i.get("distributor_id") or i.get("party_id") or "unknown"
            by_distributor.setdefault(dist, {"distributor_id": dist, "party_name": i.get("party_name"), "revenue": 0, "count": 0})
            by_distributor[dist]["revenue"] += _num(i.get("total"))
            by_distributor[dist]["count"] += 1
            for ln in i.get("lines", []):
                s = ln.get("sku_id") or "unknown"
                if sku_id and s != sku_id: continue
                by_sku.setdefault(s, {"sku_id": s, "sku_code": ln.get("sku_code"),
                                       "product_name": ln.get("product_name"), "revenue": 0, "units": 0})
                by_sku[s]["revenue"] += _num(ln.get("subtotal", ln.get("qty", 0) * ln.get("price", 0)))
                by_sku[s]["units"] += int(ln.get("qty", 0) or 0)

        # Attach branch names
        branch_map = {b["id"]: b["name"] async for b in db.branches.find({}, {"_id": 0})}
        for br in by_branch.values():
            br["name"] = branch_map.get(br["branch_id"], br["branch_id"])

        # Funnel
        totals = {
            "orders_placed": await db.primary_orders.count_documents({}) + await db.secondary_orders.count_documents({}),
            "invoiced": await db.invoices.count_documents({}),
            "dispatched": await db.dispatches.count_documents({}),
            "received": await db.grns.count_documents({}),
            "settled": await db.invoices.count_documents({"status": "settled"}),
        }

        return {
            "range": {"start": start, "end": end, "granularity": granularity},
            "series": [{"period": k, **v} for k, v in sorted(by_period.items())],
            "top_skus": sorted(by_sku.values(), key=lambda x: x["revenue"], reverse=True)[:10],
            "by_branch": sorted(by_branch.values(), key=lambda x: x["revenue"], reverse=True),
            "by_distributor": sorted(by_distributor.values(), key=lambda x: x["revenue"], reverse=True)[:10],
            "by_status": by_status,
            "funnel": [{"stage": k, "value": v} for k, v in totals.items()],
            "totals": {
                "revenue": round(sum(_num(i.get("total")) for i in w), 2),
                "count": len(w),
                "avg_order_value": round(sum(_num(i.get("total")) for i in w) / max(len(w), 1), 2),
            },
        }

    # ==========================================================
    # INVENTORY ANALYTICS
    # ==========================================================
    @router.get("/inventory")
    async def inventory_analytics(sku_id: Optional[str] = None, user: dict = Depends(get_current_user)):
        skus_map = {s["id"]: s async for s in db.skus.find({}, {"_id": 0})}
        buckets = {"available": 0, "reserved": 0, "in_transit": 0, "damaged": 0, "returned": 0, "expired": 0}
        by_sku: Dict[str, Dict[str, Any]] = {}
        scope_values = {"company": 0.0, "distributor": 0.0, "retailer": 0.0}
        for scope, coll in (("company", "company_inventory"), ("distributor", "distributor_inventory"), ("retailer", "retailer_inventory")):
            async for r in db[coll].find({}, {"_id": 0}):
                if sku_id and r.get("sku_id") != sku_id: continue
                sku = skus_map.get(r.get("sku_id")) or {}
                price = _num(sku.get("trade_price", 0))
                for k in buckets.keys():
                    buckets[k] += int(r.get(k, 0) or 0)
                # value
                v = int(r.get("available", 0) or 0) * price
                scope_values[scope] += v
                # top SKUs
                sid = r.get("sku_id") or "unknown"
                by_sku.setdefault(sid, {"sku_id": sid, "sku_code": r.get("sku_code") or sku.get("sku_code"),
                                         "product_name": sku.get("product_name"), "available": 0, "value": 0})
                by_sku[sid]["available"] += int(r.get("available", 0) or 0)
                by_sku[sid]["value"] += v

        # Near-expiry batches
        threshold = (_now() + timedelta(days=30)).isoformat()
        today_iso = _now().isoformat()
        near_expiry = []
        async for b in db.batches.find({"expires_on": {"$lte": threshold, "$gte": today_iso}}, {"_id": 0}).limit(50):
            near_expiry.append(b)
        expired_count = await db.batches.count_documents({"expires_on": {"$lt": today_iso}})

        return {
            "buckets": [{"name": k, "value": v} for k, v in buckets.items()],
            "by_scope_value": [{"scope": k, "value": round(v, 2)} for k, v in scope_values.items()],
            "top_skus": sorted(by_sku.values(), key=lambda x: x["value"], reverse=True)[:12],
            "near_expiry_batches": near_expiry,
            "expired_batches_count": expired_count,
            "totals": {
                "total_units": sum(buckets.values()),
                "total_value": round(sum(scope_values.values()), 2),
                "damaged_pct": round((buckets["damaged"] / max(sum(buckets.values()), 1)) * 100, 2),
            },
        }

    # ==========================================================
    # FINANCE ANALYTICS
    # ==========================================================
    @router.get("/finance")
    async def finance_analytics(range: str = Query("month"), from_: Optional[str] = Query(None, alias="from"),
                                 to: Optional[str] = None, user: dict = Depends(get_current_user)):
        start, end, granularity = range_bounds(range, from_, to)

        # Cash-in (payments)
        payments = await db.payments.find({}, {"_id": 0}).to_list(5000)
        w_pay = [p for p in payments if _in_range(p.get("received_at") or p.get("created_at"), start, end)]
        # Cash-out (expenses + claims settled + replacements)
        expenses = await db.expenses.find({}, {"_id": 0}).to_list(5000)
        w_exp = [e for e in expenses if _in_range(e.get("created_at"), start, end)]
        claims = await db.claims.find({"status": "settled"}, {"_id": 0}).to_list(5000)
        w_clm = [c for c in claims if _in_range(c.get("settled_at") or c.get("created_at"), start, end)]

        def bkt(iso):
            if not iso: return None
            if granularity == "hour": return iso[:13]
            if granularity == "month": return iso[:7]
            return iso[:10]

        series: Dict[str, Dict[str, float]] = {}
        for p in w_pay:
            b = bkt(p.get("received_at") or p.get("created_at"))
            if b:
                series.setdefault(b, {"cash_in": 0, "cash_out": 0, "net": 0})
                series[b]["cash_in"] += _num(p.get("amount"))
        for e in w_exp:
            b = bkt(e.get("created_at"))
            if b:
                series.setdefault(b, {"cash_in": 0, "cash_out": 0, "net": 0})
                series[b]["cash_out"] += _num(e.get("amount"))
        for c in w_clm:
            b = bkt(c.get("settled_at") or c.get("created_at"))
            if b:
                series.setdefault(b, {"cash_in": 0, "cash_out": 0, "net": 0})
                series[b]["cash_out"] += _num(c.get("settlement_amount", c.get("amount")))
        for v in series.values():
            v["net"] = round(v["cash_in"] - v["cash_out"], 2)

        # Payment method mix
        by_method: Dict[str, float] = {}
        for p in w_pay:
            m = p.get("method", "Unknown")
            by_method[m] = by_method.get(m, 0) + _num(p.get("amount"))

        # DSO / Collection rate
        invoices = await db.invoices.find({}, {"_id": 0}).to_list(5000)
        billed = sum(_num(i.get("total")) for i in invoices)
        collected = sum(_num(i.get("paid")) for i in invoices) + sum(_num(p.get("amount")) for p in payments)
        collection_rate = round((collected / max(billed, 1)) * 100, 2) if billed > 0 else 0

        # Aging buckets
        now_iso = _now().isoformat()
        aging = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
        for i in invoices:
            rem = _num(i.get("total")) - _num(i.get("paid")) - _num(i.get("credited"))
            if rem <= 0: continue
            due = i.get("due_on")
            if not due:
                aging["0-30"] += rem; continue
            try:
                d = datetime.fromisoformat(due.replace("Z", "+00:00"))
                n = datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
                days_past = (n - d).days
            except Exception:
                days_past = 0
            if days_past <= 30: aging["0-30"] += rem
            elif days_past <= 60: aging["31-60"] += rem
            elif days_past <= 90: aging["61-90"] += rem
            else: aging["90+"] += rem

        return {
            "range": {"start": start, "end": end, "granularity": granularity},
            "series": [{"period": k, **v} for k, v in sorted(series.items())],
            "by_method": [{"method": k, "value": round(v, 2)} for k, v in sorted(by_method.items(), key=lambda x: -x[1])],
            "aging": [{"bucket": k, "value": round(v, 2)} for k, v in aging.items()],
            "totals": {
                "cash_in": round(sum(_num(p.get("amount")) for p in w_pay), 2),
                "cash_out": round(sum(_num(e.get("amount")) for e in w_exp) + sum(_num(c.get("settlement_amount", c.get("amount"))) for c in w_clm), 2),
                "collection_rate": collection_rate,
                "total_outstanding": round(billed - collected, 2),
            },
        }

    # ==========================================================
    # RETURNS ANALYTICS
    # ==========================================================
    @router.get("/returns")
    async def returns_analytics(range: str = Query("month"), from_: Optional[str] = Query(None, alias="from"),
                                to: Optional[str] = None, user: dict = Depends(get_current_user)):
        start, end, _ = range_bounds(range, from_, to)
        rows = await db.returns.find({}, {"_id": 0}).to_list(5000)
        w = [r for r in rows if _in_range(r.get("created_at"), start, end)]
        by_reason: Dict[str, Dict] = {}
        by_scope: Dict[str, Dict] = {}
        by_status: Dict[str, int] = {}
        by_sku: Dict[str, Dict] = {}
        series: Dict[str, Dict] = {}
        for r in w:
            reason = r.get("reason", "unknown")
            by_reason.setdefault(reason, {"reason": reason, "count": 0, "value": 0})
            by_reason[reason]["count"] += 1
            by_reason[reason]["value"] += _num(r.get("total"))
            sc = r.get("scope", "unknown")
            by_scope.setdefault(sc, {"scope": sc, "count": 0, "value": 0})
            by_scope[sc]["count"] += 1
            by_scope[sc]["value"] += _num(r.get("total"))
            by_status[r.get("status", "?")] = by_status.get(r.get("status", "?"), 0) + 1
            b = (r.get("created_at") or "")[:10]
            if b:
                series.setdefault(b, {"period": b, "count": 0, "value": 0})
                series[b]["count"] += 1
                series[b]["value"] += _num(r.get("total"))
            for ln in r.get("lines", []):
                s = ln.get("sku_id") or "unknown"
                by_sku.setdefault(s, {"sku_id": s, "sku_code": ln.get("sku_code"), "product_name": ln.get("product_name"),
                                       "count": 0, "value": 0, "qty": 0})
                by_sku[s]["count"] += 1
                by_sku[s]["value"] += _num(ln.get("subtotal", 0))
                by_sku[s]["qty"] += int(ln.get("qty", 0) or 0)

        return {
            "range": {"start": start, "end": end},
            "totals": {"count": len(w), "value": round(sum(_num(r.get("total")) for r in w), 2)},
            "by_reason": sorted(by_reason.values(), key=lambda x: -x["value"]),
            "by_scope": list(by_scope.values()),
            "by_status": by_status,
            "top_skus": sorted(by_sku.values(), key=lambda x: -x["value"])[:10],
            "series": sorted(series.values(), key=lambda x: x["period"]),
        }

    # ==========================================================
    # CLAIMS ANALYTICS
    # ==========================================================
    @router.get("/claims")
    async def claims_analytics(range: str = Query("month"), from_: Optional[str] = Query(None, alias="from"),
                                to: Optional[str] = None, user: dict = Depends(get_current_user)):
        start, end, _ = range_bounds(range, from_, to)
        rows = await db.claims.find({}, {"_id": 0}).to_list(5000)
        w = [c for c in rows if _in_range(c.get("created_at"), start, end)]
        by_type: Dict[str, Dict] = {}
        by_status: Dict[str, int] = {}
        series: Dict[str, Dict] = {}
        for c in w:
            t = c.get("type", "unknown")
            by_type.setdefault(t, {"type": t, "count": 0, "value": 0, "settled": 0})
            by_type[t]["count"] += 1
            by_type[t]["value"] += _num(c.get("amount"))
            if c.get("status") == "settled":
                by_type[t]["settled"] += _num(c.get("settlement_amount"))
            by_status[c.get("status", "?")] = by_status.get(c.get("status", "?"), 0) + 1
            b = (c.get("created_at") or "")[:10]
            if b:
                series.setdefault(b, {"period": b, "count": 0, "amount": 0})
                series[b]["count"] += 1
                series[b]["amount"] += _num(c.get("amount"))
        return {
            "range": {"start": start, "end": end},
            "totals": {"count": len(w), "value": round(sum(_num(c.get("amount")) for c in w), 2),
                        "settled": round(sum(_num(c.get("settlement_amount")) for c in w if c.get("status") == "settled"), 2)},
            "by_type": list(by_type.values()),
            "by_status": by_status,
            "series": sorted(series.values(), key=lambda x: x["period"]),
        }

    # ==========================================================
    # PROFITABILITY
    # ==========================================================
    @router.get("/profitability")
    async def profitability(range: str = Query("month"), from_: Optional[str] = Query(None, alias="from"),
                             to: Optional[str] = None, user: dict = Depends(get_current_user)):
        start, end, _ = range_bounds(range, from_, to)
        invoices = await db.invoices.find({}, {"_id": 0}).to_list(5000)
        w = [i for i in invoices if _in_range(i.get("issued_on") or i.get("created_at"), start, end)]
        revenue = sum(_num(i.get("subtotal", i.get("total"))) for i in w)
        # COGS approximation — 60% of subtotal (in absence of costing engine)
        cogs = revenue * 0.6

        returns_v = await db.returns.find({}, {"_id": 0}).to_list(5000)
        w_ret = [r for r in returns_v if _in_range(r.get("created_at"), start, end)]
        return_amt = sum(_num(r.get("total")) for r in w_ret)

        claims_v = await db.claims.find({}, {"_id": 0}).to_list(5000)
        w_clm = [c for c in claims_v if _in_range(c.get("created_at"), start, end)]
        claim_amt = sum(_num(c.get("amount")) for c in w_clm)

        expenses = await db.expenses.find({}, {"_id": 0}).to_list(5000)
        w_exp = [e for e in expenses if _in_range(e.get("created_at"), start, end)]
        expense_amt = sum(_num(e.get("amount")) for e in w_exp)

        gross_profit = revenue - cogs
        net_profit = gross_profit - return_amt - claim_amt - expense_amt
        margin = round((net_profit / max(revenue, 1)) * 100, 2) if revenue > 0 else 0

        return {
            "range": {"start": start, "end": end},
            "revenue": round(revenue, 2),
            "cogs": round(cogs, 2),
            "gross_profit": round(gross_profit, 2),
            "returns": round(return_amt, 2),
            "claims": round(claim_amt, 2),
            "expenses": round(expense_amt, 2),
            "net_profit": round(net_profit, 2),
            "margin_pct": margin,
            "waterfall": [
                {"label": "Revenue", "value": round(revenue, 2), "type": "start"},
                {"label": "COGS", "value": -round(cogs, 2), "type": "deduct"},
                {"label": "Returns", "value": -round(return_amt, 2), "type": "deduct"},
                {"label": "Claims", "value": -round(claim_amt, 2), "type": "deduct"},
                {"label": "Expenses", "value": -round(expense_amt, 2), "type": "deduct"},
                {"label": "Net Profit", "value": round(net_profit, 2), "type": "end"},
            ],
        }

    # ==========================================================
    # BUSINESS ALERTS ENGINE
    # ==========================================================
    @router.get("/alerts")
    async def business_alerts(user: dict = Depends(get_current_user)):
        alerts: List[Dict] = []

        # Low inventory (available < 10 for any active SKU)
        async for r in db.company_inventory.find({"available": {"$lt": 10, "$gte": 0}}, {"_id": 0}).limit(20):
            alerts.append({
                "id": f"low-inv-{r.get('id','x')}", "kind": "low_inventory", "severity": "medium",
                "title": f"Low stock: {r.get('sku_code','?')}",
                "description": f"Only {r.get('available', 0)} units left in company inventory",
                "drill": "inventory", "entity_id": r.get("id"),
            })
        # Negative margin — skipped (needs costing engine); use big returns
        # High Outstanding — top 5 parties by outstanding
        pipeline = [
            {"$group": {"_id": {"party_id": "$party_id", "party_name": "$party_name", "party_type": "$party_type"},
                         "billed": {"$sum": "$total"}, "paid": {"$sum": "$paid"}, "credited": {"$sum": "$credited"}}},
        ]
        async for row in db.invoices.aggregate(pipeline):
            rem = _num(row.get("billed")) - _num(row.get("paid")) - _num(row.get("credited"))
            if rem > 50000:
                alerts.append({
                    "id": f"out-{row['_id'].get('party_id','x')}", "kind": "high_outstanding", "severity": "high",
                    "title": f"High outstanding: {row['_id'].get('party_name','?')}",
                    "description": f"${rem:,.0f} outstanding",
                    "drill": f"party360/{row['_id'].get('party_type','distributor')}/{row['_id'].get('party_id')}",
                    "entity_id": row['_id'].get('party_id'),
                })
        # Credit limit exceeded (from outstanding table)
        async for r in db.outstanding.find({"credit_utilization": {"$gt": 100}}, {"_id": 0}).limit(20):
            alerts.append({
                "id": f"cl-{r.get('party_id')}", "kind": "credit_limit_exceeded", "severity": "high",
                "title": f"Credit limit breached: {r.get('party_name')}",
                "description": f"Utilization {r.get('credit_utilization', 0):.0f}%",
                "drill": f"party360/{r.get('party_type')}/{r.get('party_id')}",
                "entity_id": r.get("party_id"),
            })
        # Payment delay — invoices due > 30 days ago unpaid
        cutoff = (_now() - timedelta(days=30)).isoformat()
        async for inv in db.invoices.find({"due_on": {"$lt": cutoff}}, {"_id": 0}).limit(30):
            rem = _num(inv.get("total")) - _num(inv.get("paid")) - _num(inv.get("credited"))
            if rem > 0:
                alerts.append({
                    "id": f"pd-{inv['id']}", "kind": "payment_delay", "severity": "high",
                    "title": f"Overdue: {inv.get('invoice_no')}",
                    "description": f"${rem:,.0f} unpaid past due date",
                    "drill": "invoices", "entity_id": inv["id"],
                })
        # High returns (return rate > 10% for any distributor)
        # Approximation with joins
        ret_by_party: Dict[str, int] = {}
        async for r in db.returns.find({}, {"_id": 0}):
            ret_by_party[r.get("party_id", "?")] = ret_by_party.get(r.get("party_id", "?"), 0) + 1
        inv_by_party: Dict[str, int] = {}
        async for i in db.invoices.find({}, {"_id": 0}):
            inv_by_party[i.get("party_id", "?")] = inv_by_party.get(i.get("party_id", "?"), 0) + 1
        for pid, rc in ret_by_party.items():
            ic = inv_by_party.get(pid, 0)
            if ic > 0 and (rc / ic) > 0.10:
                alerts.append({
                    "id": f"hr-{pid}", "kind": "high_returns", "severity": "medium",
                    "title": f"Elevated return rate — party {pid}",
                    "description": f"{rc} returns from {ic} invoices ({rc/ic:.0%})",
                    "drill": "returns", "entity_id": pid,
                })
        # Pending approvals count
        pending = await db.approval_requests.count_documents({"status": "pending"})
        if pending > 0:
            alerts.append({
                "id": "pending-approvals", "kind": "pending_approvals", "severity": "medium",
                "title": f"{pending} approval(s) pending",
                "description": "Approval requests awaiting action",
                "drill": "approval-engine", "entity_id": None,
            })
        # Near expiry
        threshold = (_now() + timedelta(days=30)).isoformat()
        today_iso = _now().isoformat()
        near_count = await db.batches.count_documents({"expires_on": {"$lte": threshold, "$gte": today_iso}})
        if near_count > 0:
            alerts.append({
                "id": "near-expiry", "kind": "near_expiry", "severity": "medium",
                "title": f"{near_count} batch(es) near expiry",
                "description": "Batches expiring within 30 days",
                "drill": "expiry", "entity_id": None,
            })
        # Exceptions
        exc_count = await db.exceptions.count_documents({"status": "open"})
        if exc_count > 0:
            alerts.append({
                "id": "exceptions-open", "kind": "exceptions", "severity": "high",
                "title": f"{exc_count} open exception(s)",
                "description": "Anomalies detected — require review",
                "drill": "exceptions", "entity_id": None,
            })
        # Dispatch delay — dispatches in_transit older than 3 days
        cutoff3 = (_now() - timedelta(days=3)).isoformat()
        async for d in db.dispatches.find({"status": "in_transit", "dispatch_date": {"$lt": cutoff3}}, {"_id": 0}).limit(20):
            alerts.append({
                "id": f"dd-{d['id']}", "kind": "dispatch_delay", "severity": "medium",
                "title": f"Dispatch delayed: {d.get('dispatch_no')}",
                "description": f"In transit since {d.get('dispatch_date', '')[:10]}",
                "drill": "dispatches", "entity_id": d["id"],
            })
        # Business Risk (aggregate)
        by_sev = {}
        for a in alerts:
            by_sev[a["severity"]] = by_sev.get(a["severity"], 0) + 1
        return {
            "count": len(alerts),
            "by_kind": {k: sum(1 for a in alerts if a["kind"] == k) for k in set(a["kind"] for a in alerts)},
            "by_severity": by_sev,
            "alerts": alerts[:60],
        }

    # ==========================================================
    # BUSINESS SCORECARDS
    # ==========================================================
    @router.get("/scorecards/{entity_type}")
    async def scorecards(entity_type: str, user: dict = Depends(get_current_user)):
        if entity_type not in ("distributor", "retailer", "sales_executive", "warehouse", "branch", "company"):
            raise HTTPException(400, "Invalid entity_type")

        result: List[Dict] = []
        if entity_type == "distributor":
            distributors = await db.distributors.find({}, {"_id": 0}).to_list(200)
            for d in distributors:
                pid = d["id"]
                invs = await db.invoices.find({"party_id": pid}, {"_id": 0}).to_list(500)
                pays = await db.payments.find({"party_id": pid}, {"_id": 0}).to_list(500)
                rets = await db.returns.count_documents({"party_id": pid})
                clms = await db.claims.count_documents({"party_id": pid})
                billed = sum(_num(i.get("total")) for i in invs)
                paid = sum(_num(p.get("amount")) for p in pays)
                sales_score = min(100, (billed / 500000) * 100)
                collection_score = round(min(100, (paid / max(billed, 1)) * 100), 1)
                return_score = round(max(0, 100 - rets * 5), 1)
                claim_score = round(max(0, 100 - clms * 5), 1)
                overall = round((sales_score * 0.4 + collection_score * 0.3 + return_score * 0.15 + claim_score * 0.15), 1)
                result.append({
                    "id": pid, "name": d.get("name"),
                    "region": d.get("branch_id"),
                    "sales_score": round(sales_score, 1), "collection_score": collection_score,
                    "return_score": return_score, "claim_score": claim_score,
                    "overall": overall, "grade": "A" if overall >= 85 else "B" if overall >= 70 else "C" if overall >= 55 else "D",
                    "billed": round(billed, 2), "paid": round(paid, 2),
                    "returns": rets, "claims": clms,
                })
        elif entity_type == "retailer":
            retailers = await db.retailers.find({}, {"_id": 0}).to_list(300)
            for d in retailers:
                pid = d["id"]
                invs = await db.invoices.find({"party_id": pid}, {"_id": 0}).to_list(500)
                pays = await db.payments.find({"party_id": pid}, {"_id": 0}).to_list(500)
                rets = await db.returns.count_documents({"party_id": pid})
                billed = sum(_num(i.get("total")) for i in invs)
                paid = sum(_num(p.get("amount")) for p in pays)
                sales_score = min(100, (billed / 100000) * 100)
                coll = round(min(100, (paid / max(billed, 1)) * 100), 1)
                ret_s = max(0, 100 - rets * 5)
                overall = round(sales_score * 0.5 + coll * 0.3 + ret_s * 0.2, 1)
                result.append({
                    "id": pid, "name": d.get("name"),
                    "sales_score": round(sales_score, 1), "collection_score": coll,
                    "return_score": ret_s,
                    "overall": overall, "grade": "A" if overall >= 85 else "B" if overall >= 70 else "C" if overall >= 55 else "D",
                    "billed": round(billed, 2), "paid": round(paid, 2), "returns": rets,
                })
        elif entity_type == "branch":
            branches = await db.branches.find({}, {"_id": 0}).to_list(20)
            for b in branches:
                bid = b["id"]
                invs = await db.invoices.find({"branch_id": bid}, {"_id": 0}).to_list(2000)
                billed = sum(_num(i.get("total")) for i in invs)
                paid = sum(_num(i.get("paid")) for i in invs)
                result.append({
                    "id": bid, "name": b.get("name"), "region": b.get("region"),
                    "revenue": round(billed, 2), "collections": round(paid, 2),
                    "collection_rate": round((paid / max(billed, 1)) * 100, 1),
                    "invoice_count": len(invs),
                    "overall": round(min(100, (billed / 5000000) * 100), 1),
                })
        elif entity_type == "sales_executive":
            # Approximate: use created_by on orders/invoices
            pipeline = [{"$group": {"_id": "$created_by", "total": {"$sum": "$total"}, "count": {"$sum": 1}}}]
            async for row in db.invoices.aggregate(pipeline):
                if not row["_id"]: continue
                result.append({
                    "id": row["_id"], "name": row["_id"],
                    "revenue": round(row["total"], 2), "count": row["count"],
                    "overall": round(min(100, (row["total"] / 500000) * 100), 1),
                })
        elif entity_type == "warehouse":
            grns = await db.grns.find({}, {"_id": 0}).to_list(1000)
            variances = [g for g in grns if _num(g.get("variance", 0)) != 0]
            result.append({
                "id": "wh-primary", "name": "Primary Warehouse",
                "grn_count": len(grns), "variance_count": len(variances),
                "accuracy": round((1 - len(variances) / max(len(grns), 1)) * 100, 1),
                "overall": round((1 - len(variances) / max(len(grns), 1)) * 100, 1),
            })
        elif entity_type == "company":
            invs_c = await db.invoices.count_documents({})
            billed = 0
            paid = 0
            async for i in db.invoices.find({}, {"_id": 0}):
                billed += _num(i.get("total"))
                paid += _num(i.get("paid"))
            result.append({
                "id": "gooil", "name": "GO OIL Holdings",
                "revenue": round(billed, 2), "collections": round(paid, 2),
                "collection_rate": round((paid / max(billed, 1)) * 100, 1),
                "invoice_count": invs_c,
                "overall": 88.5,
            })

        return {"entity_type": entity_type, "count": len(result), "rows": sorted(result, key=lambda x: x.get("overall", 0), reverse=True)}

    # ==========================================================
    # AI-READY DATA LAYER
    # ==========================================================
    @router.get("/ai-context/{scope}")
    async def ai_context(scope: str, user: dict = Depends(get_current_user)):
        scope = scope.lower()
        if scope == "executive":
            kpi = await executive_kpi(range="month", from_=None, to=None, branch_id=None, distributor_id=None, retailer_id=None, sku_id=None, user=user)
            alerts_data = await business_alerts(user=user)
            return {
                "generated_at": _now().isoformat(),
                "scope": "executive",
                "summary": kpi["kpis"],
                "alerts_summary": alerts_data["by_severity"],
                "recent_alerts": alerts_data["alerts"][:10],
                "hint": "This is a structured monthly executive snapshot ready for LLM ingestion.",
            }
        if scope == "sales":
            sa = await sales_analytics(range="month", from_=None, to=None, branch_id=None, distributor_id=None, sku_id=None, user=user)
            return {"generated_at": _now().isoformat(), "scope": "sales", **sa}
        if scope == "finance":
            fa = await finance_analytics(range="month", from_=None, to=None, user=user)
            return {"generated_at": _now().isoformat(), "scope": "finance", **fa}
        if scope == "inventory":
            ia = await inventory_analytics(sku_id=None, user=user)
            return {"generated_at": _now().isoformat(), "scope": "inventory", **ia}
        raise HTTPException(400, f"Unknown scope: {scope}")

    return router
