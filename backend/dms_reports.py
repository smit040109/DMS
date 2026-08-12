"""
Phase 3 — Reports Module.

Contains:
- REPORT_CATALOG: metadata for all ~42 reports across 5 categories
- Per-report run functions returning {rows, totals, columns}
- Column metadata for generic frontend rendering
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable, Tuple, Awaitable

# ---------------------------------------------------------------------------
# Role sets
# ---------------------------------------------------------------------------
_ALL_NON_RETAILER = [
    "owner", "owner_accountant",
    "distributor", "distributor_accountant",
    "salesperson", "team_leader", "regional_manager",
]
_ADMIN_ONLY = ["owner", "owner_accountant"]
_ADMIN_AND_DIST = _ADMIN_ONLY + ["distributor", "distributor_accountant"]
_ADMIN_TL_RM = _ADMIN_ONLY + ["team_leader", "regional_manager"]

# ---------------------------------------------------------------------------
# Column helpers — used to build catalog "columns" arrays
# ---------------------------------------------------------------------------
def _col(key, label, type="string", align=None, totals=False):
    c = {"key": key, "label": label, "type": type}
    c["align"] = align or ("right" if type in ("currency", "number", "int", "pct") else "left")
    if totals:
        c["totals"] = True
    return c

# ---------------------------------------------------------------------------
# Category order
# ---------------------------------------------------------------------------
CATEGORY_ORDER = [
    ("transaction", "Transaction Reports"),
    ("party", "Party Reports"),
    ("gst", "GST Reports"),
    ("stock", "Item / Stock Reports"),
    ("sales_team", "Sales Team / Field Reports"),
]

# ---------------------------------------------------------------------------
# Report catalogue
# ---------------------------------------------------------------------------
REPORT_CATALOG: List[Dict[str, Any]] = [
    # ---------------- 1. TRANSACTION REPORTS ----------------
    {"id": "sale", "name": "Sale Report", "category": "transaction",
     "description": "Primary + secondary sale bills within a date range.",
     "status": "live", "allowed_roles": _ALL_NON_RETAILER,
     "filters": ["date_from", "date_to", "sale_type", "party_id"]},
    {"id": "purchase", "name": "Purchase Report", "category": "transaction",
     "description": "Primary purchases (goods received from Owner).",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST,
     "filters": ["date_from", "date_to", "party_id"]},
    {"id": "sale_order", "name": "Sale Order Report", "category": "transaction",
     "description": "Sale orders placed (before invoicing).",
     "status": "live", "allowed_roles": _ALL_NON_RETAILER,
     "filters": ["date_from", "date_to", "sale_type", "status"]},
    {"id": "day_book", "name": "Day Book", "category": "transaction",
     "description": "All transactions of a specific day.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST,
     "filters": ["date"]},
    {"id": "all_transactions", "name": "All Transactions", "category": "transaction",
     "description": "Combined view of every voucher in the period.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST,
     "filters": ["date_from", "date_to"]},
    {"id": "bill_wise_profit", "name": "Bill Wise Profit", "category": "transaction",
     "description": "Profit realised per secondary bill (revenue − cost).",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST,
     "filters": ["date_from", "date_to"]},
    {"id": "profit_loss", "name": "Profit & Loss", "category": "transaction",
     "description": "Revenue − Cost of Goods Sold − Expenses.",
     "status": "live", "allowed_roles": _ADMIN_ONLY,
     "filters": ["date_from", "date_to"]},
    {"id": "sale_aging", "name": "Sale Aging Report", "category": "transaction",
     "description": "Ageing buckets for outstanding sale invoices.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST,
     "filters": ["as_on_date"]},
    {"id": "purchase_aging", "name": "Purchase Aging Report", "category": "transaction",
     "description": "Ageing buckets for outstanding purchase invoices.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST,
     "filters": ["as_on_date"]},
    {"id": "cashflow", "name": "Cashflow", "category": "transaction",
     "description": "Cash in/out across bank, cash register and loan flows.",
     "status": "live", "allowed_roles": _ADMIN_ONLY,
     "filters": ["date_from", "date_to"]},
    {"id": "balance_sheet", "name": "Balance Sheet", "category": "transaction",
     "description": "Assets vs liabilities snapshot.",
     "status": "live", "allowed_roles": _ADMIN_ONLY,
     "filters": ["as_on_date"]},
    {"id": "expense", "name": "Expense Report", "category": "transaction",
     "description": "Expenses booked in the period, by category.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST,
     "filters": ["date_from", "date_to", "category"]},

    # ---------------- 2. PARTY REPORTS ----------------
    {"id": "party_statement", "name": "Party Statement", "category": "party",
     "description": "Full ledger statement for one party.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST,
     "filters": ["date_from", "date_to", "party_id"]},
    {"id": "party_wise_profit_loss", "name": "Party Wise Profit & Loss", "category": "party",
     "description": "Profitability per party.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST,
     "filters": ["date_from", "date_to"]},
    {"id": "all_parties", "name": "All Parties Report", "category": "party",
     "description": "Master list of every party with basic details.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST, "filters": []},
    {"id": "party_by_items", "name": "Party Report by Items", "category": "party",
     "description": "Item-wise breakdown per party.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST,
     "filters": ["date_from", "date_to", "party_id"]},
    {"id": "sale_purchase_by_party", "name": "Sale/Purchase by Party", "category": "party",
     "description": "Sales + purchase totals grouped by party.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST,
     "filters": ["date_from", "date_to"]},
    {"id": "outstanding_due", "name": "Outstanding/Due Report", "category": "party",
     "description": "All outstanding balances receivable/payable.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST,
     "filters": ["as_on_date"]},

    # ---------------- 3. GST REPORTS ----------------
    {"id": "gstr1", "name": "GSTR-1", "category": "gst",
     "description": "Outward supplies (data view + export only, no GSTN filing).",
     "status": "live", "allowed_roles": _ADMIN_ONLY,
     "filters": ["date_from", "date_to"]},
    {"id": "gstr2", "name": "GSTR-2", "category": "gst",
     "description": "Inward supplies (data view + export only).",
     "status": "live", "allowed_roles": _ADMIN_ONLY,
     "filters": ["date_from", "date_to"]},
    {"id": "gstr3b", "name": "GSTR-3B", "category": "gst",
     "description": "Summary return (data view + export only).",
     "status": "live", "allowed_roles": _ADMIN_ONLY,
     "filters": ["date_from", "date_to"]},
    {"id": "gst_transaction", "name": "GST Transaction Report", "category": "gst",
     "description": "Every taxable transaction with GST breakup.",
     "status": "live", "allowed_roles": _ADMIN_ONLY,
     "filters": ["date_from", "date_to"]},
    {"id": "gstr9", "name": "GSTR-9", "category": "gst",
     "description": "Annual return summary (data view + export only).",
     "status": "live", "allowed_roles": _ADMIN_ONLY,
     "filters": ["date_from", "date_to"]},
    {"id": "sale_summary_hsn", "name": "Sale Summary by HSN", "category": "gst",
     "description": "Sale totals grouped by HSN code.",
     "status": "live", "allowed_roles": _ADMIN_ONLY,
     "filters": ["date_from", "date_to"]},
    {"id": "sac_report", "name": "SAC Report", "category": "gst",
     "description": "Service Accounting Code report for services rendered.",
     "status": "live", "allowed_roles": _ADMIN_ONLY,
     "filters": ["date_from", "date_to"]},

    # ---------------- 4. ITEM / STOCK REPORTS ----------------
    {"id": "stock_summary", "name": "Stock Summary Report", "category": "stock",
     "description": "Current on-hand quantity for every SKU.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST, "filters": []},
    {"id": "item_by_party", "name": "Item Report by Party", "category": "stock",
     "description": "Items sold/purchased grouped by party.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST,
     "filters": ["date_from", "date_to", "party_id"]},
    {"id": "item_wise_profit_loss", "name": "Item Wise Profit & Loss", "category": "stock",
     "description": "Profit contribution per SKU.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST,
     "filters": ["date_from", "date_to"]},
    {"id": "low_stock_summary", "name": "Low Stock Summary Report", "category": "stock",
     "description": "SKUs at or below their reorder level.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST, "filters": []},
    {"id": "item_detail", "name": "Item Detail Report", "category": "stock",
     "description": "Master details for every item.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST,
     "filters": ["category"]},
    {"id": "stock_detail", "name": "Stock Detail Report", "category": "stock",
     "description": "Movement history across the period.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST,
     "filters": ["date_from", "date_to", "item_id"]},
    {"id": "sale_purchase_by_item_category", "name": "Sale/Purchase by Item Category", "category": "stock",
     "description": "Sales + purchase totals per item category.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST,
     "filters": ["date_from", "date_to"]},
    {"id": "stock_summary_by_item_category", "name": "Stock Summary by Item Category", "category": "stock",
     "description": "On-hand stock grouped by item category.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST, "filters": []},
    {"id": "item_batch", "name": "Item Batch Report", "category": "stock",
     "description": "Batch/lot-wise sale movements across items.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST,
     "filters": ["date_from", "date_to"]},
    {"id": "item_serial", "name": "Item Serial Report", "category": "stock",
     "description": "Coupon serial numbers assigned/redeemed per item.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST,
     "filters": ["date_from", "date_to"]},
    {"id": "item_wise_discount", "name": "Item Wise Discount", "category": "stock",
     "description": "Discounts (MRP → sale price) per SKU.",
     "status": "live", "allowed_roles": _ADMIN_AND_DIST,
     "filters": ["date_from", "date_to"]},
    {"id": "godown_transfer", "name": "Godown/Stock Transfer Report", "category": "stock",
     "description": "Stock transfers between godowns / owner ↔ godown.",
     "status": "live", "allowed_roles": _ADMIN_ONLY,
     "filters": ["date_from", "date_to"]},

    # ---------------- 5. SALES TEAM / FIELD REPORTS ----------------
    {"id": "sp_performance", "name": "Sales Person Wise Performance Report",
     "category": "sales_team",
     "description": "Orders, revenue, retailers covered per salesperson.",
     "status": "live", "allowed_roles": _ADMIN_TL_RM,
     "filters": ["date_from", "date_to"]},
    {"id": "sp_collection", "name": "Sales Person Wise Collection Report",
     "category": "sales_team",
     "description": "Cash + cheque collections per salesperson.",
     "status": "live", "allowed_roles": _ADMIN_TL_RM + ["salesperson"],
     "filters": ["date_from", "date_to"]},
    {"id": "tl_rsm_team", "name": "TL/RSM Team Report", "category": "sales_team",
     "description": "Team-level performance for TL/RSM hierarchies.",
     "status": "live", "allowed_roles": _ADMIN_ONLY + ["regional_manager"],
     "filters": ["date_from", "date_to"]},
    {"id": "live_tracking_visits", "name": "Live Tracking / Visit Report",
     "category": "sales_team",
     "description": "Field-visit + GPS trail summary per salesperson.",
     "status": "live", "allowed_roles": _ADMIN_TL_RM,
     "filters": ["date_from", "date_to"]},
    {"id": "order_cancellation", "name": "Order Cancellation Report",
     "category": "sales_team",
     "description": "Orders cancelled after being placed.",
     "status": "live", "allowed_roles": _ALL_NON_RETAILER,
     "filters": ["date_from", "date_to"]},
]


def role_can_see_report(report: Dict[str, Any], role: str) -> bool:
    if role == "retailer":
        return False
    if role == "super_admin":
        return True
    return role in report.get("allowed_roles", [])


def get_report_by_id(report_id: str) -> Optional[Dict[str, Any]]:
    for r in REPORT_CATALOG:
        if r["id"] == report_id:
            return r
    return None


# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------
def _parse_iso_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        try:
            d = datetime.strptime(s, "%Y-%m-%d")
        except Exception:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


def _in_range(iso_str: Optional[str], df: Optional[datetime], dt: Optional[datetime]) -> bool:
    if not iso_str:
        return True
    d = _parse_iso_date(iso_str)
    if not d:
        return True
    if df and d < df:
        return False
    if dt and d > dt:
        return False
    return True


def _end_of_day(dt: Optional[datetime]) -> Optional[datetime]:
    if not dt:
        return None
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def _days_between(iso_str: Optional[str], as_on: datetime) -> int:
    d = _parse_iso_date(iso_str)
    if not d:
        return 0
    diff = as_on - d
    return max(0, int(diff.days))


def _age_bucket(days: int) -> str:
    if days <= 30:
        return "0-30"
    if days <= 60:
        return "31-60"
    if days <= 90:
        return "61-90"
    return "90+"


async def _scoped_distributor_ids(db, user: Dict[str, Any]) -> Optional[List[str]]:
    """Distributor IDs visible to this user, or None if unrestricted."""
    role = user.get("role")
    if role in ("owner", "owner_accountant", "super_admin"):
        return None
    if role in ("distributor", "distributor_accountant"):
        return [user.get("distributor_id")] if user.get("distributor_id") else []
    if role == "salesperson":
        assigns = await db.dms_sp_assignments.find(
            {"salesperson_id": user["id"]}, {"_id": 0, "distributor_id": 1}
        ).to_list(500)
        return [a["distributor_id"] for a in assigns]
    if role == "team_leader":
        assigns = await db.dms_tl_assignments.find(
            {"team_leader_id": user["id"]}, {"_id": 0, "distributor_id": 1}
        ).to_list(500)
        return [a["distributor_id"] for a in assigns]
    if role == "regional_manager":
        tl_assigns = await db.dms_rm_assignments.find(
            {"regional_manager_id": user["id"]}, {"_id": 0, "team_leader_id": 1}
        ).to_list(500)
        tl_ids = [a["team_leader_id"] for a in tl_assigns]
        if not tl_ids:
            return []
        dist_assigns = await db.dms_tl_assignments.find(
            {"team_leader_id": {"$in": tl_ids}}, {"_id": 0, "distributor_id": 1}
        ).to_list(2000)
        return list({a["distributor_id"] for a in dist_assigns})
    return []


async def _scoped_salesperson_ids(db, user: Dict[str, Any]) -> Optional[List[str]]:
    """Salesperson IDs whose data this user may see, or None if unrestricted.
    owner/accountant/super_admin → None (all); salesperson → only self;
    TL/RM/distributor → salespersons under their scoped distributors."""
    role = user.get("role")
    if role in ("owner", "owner_accountant", "super_admin"):
        return None
    if role == "salesperson":
        return [user["id"]]
    scoped = await _scoped_distributor_ids(db, user)
    if scoped is None:
        return None
    if not scoped:
        return []
    assigns = await db.dms_sp_assignments.find(
        {"distributor_id": {"$in": scoped}}, {"_id": 0, "salesperson_id": 1}
    ).to_list(5000)
    return list({a["salesperson_id"] for a in assigns})



async def _product_map(db):
    m = {}
    async for p in db.dms_products.find({}, {"_id": 0}):
        m[p["id"]] = p
    return m


async def _category_map(db):
    m = {}
    async for c in db.dms_categories.find({}, {"_id": 0}):
        m[c["id"]] = c.get("name", "")
    return m


async def _distributor_map(db):
    m = {}
    async for d in db.dms_distributors.find({}, {"_id": 0}):
        m[d["id"]] = d
    return m


async def _retailer_map(db):
    m = {}
    async for r in db.dms_retailers.find({}, {"_id": 0}):
        m[r["id"]] = r
    return m


def _fmt_date_short(iso_str: Optional[str]) -> str:
    d = _parse_iso_date(iso_str)
    if not d:
        return ""
    return d.strftime("%Y-%m-%d")


# ===========================================================================
# 1. TRANSACTION REPORTS
# ===========================================================================

# ---------- Sale Report ----------
async def _run_sale(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    sale_type = filters.get("sale_type") or "both"
    party_id = filters.get("party_id")
    scoped = await _scoped_distributor_ids(db, user)
    rows = []

    if sale_type in ("primary", "both") and user.get("role") != "salesperson":
        q = {}
        if scoped is not None:
            q["distributor_id"] = {"$in": scoped}
        if party_id:
            q["distributor_id"] = party_id
        async for b in db.dms_ebills.find(q, {"_id": 0}):
            if not _in_range(b.get("created_at"), df, dt):
                continue
            rows.append({
                "sale_type": "primary",
                "bill_no": b.get("ebill_no", ""),
                "date": _fmt_date_short(b.get("created_at")),
                "order_no": b.get("order_no", ""),
                "party_type": "distributor",
                "party_name": b.get("distributor_name", ""),
                "items_count": len(b.get("items", [])),
                "subtotal": float(b.get("subtotal", 0) or 0),
                "gst_total": float(b.get("gst_total", 0) or 0),
                "total": float(b.get("total", 0) or 0),
            })

    if sale_type in ("secondary", "both"):
        q2 = {}
        if scoped is not None:
            q2["distributor_id"] = {"$in": scoped}
        if party_id:
            q2 = {"$or": [{"distributor_id": party_id}, {"retailer_id": party_id}]}
            if scoped is not None:
                q2 = {"$and": [{"distributor_id": {"$in": scoped}}, q2]}
        sp_ids = None
        if user.get("role") == "salesperson":
            sos = await db.dms_secondary_orders.find(
                {"placed_by": user["id"]}, {"_id": 0, "id": 1}
            ).to_list(5000)
            sp_ids = {o["id"] for o in sos} or {"__none__"}
        rmap = await _retailer_map(db)
        async for b in db.dms_retailer_bills.find(q2, {"_id": 0}):
            if not _in_range(b.get("created_at"), df, dt):
                continue
            if sp_ids is not None and b.get("order_id") not in sp_ids:
                continue
            rows.append({
                "sale_type": "secondary",
                "bill_no": b.get("bill_no", ""),
                "date": _fmt_date_short(b.get("created_at")),
                "order_no": b.get("order_no", ""),
                "party_type": "retailer",
                "party_name": rmap.get(b.get("retailer_id"), {}).get("name", ""),
                "items_count": len(b.get("items", [])),
                "subtotal": float(b.get("subtotal", 0) or 0),
                "gst_total": float(b.get("gst_total", 0) or 0),
                "total": float(b.get("total", 0) or 0),
            })

    rows.sort(key=lambda r: r["date"], reverse=True)
    totals = {
        "count": len(rows),
        "subtotal": round(sum(r["subtotal"] for r in rows), 2),
        "gst_total": round(sum(r["gst_total"] for r in rows), 2),
        "total": round(sum(r["total"] for r in rows), 2),
        "primary_count": sum(1 for r in rows if r["sale_type"] == "primary"),
        "secondary_count": sum(1 for r in rows if r["sale_type"] == "secondary"),
    }
    columns = [
        _col("sale_type", "Type"),
        _col("bill_no", "Bill No"),
        _col("date", "Date", "date"),
        _col("order_no", "Order No"),
        _col("party_name", "Party"),
        _col("items_count", "Items", "int"),
        _col("subtotal", "Subtotal", "currency", totals=True),
        _col("gst_total", "GST", "currency", totals=True),
        _col("total", "Total", "currency", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Purchase Report ----------
async def _run_purchase(db, user, filters):
    """Primary orders received from Owner (goods purchased by distributor)."""
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    party_id = filters.get("party_id")
    scoped = await _scoped_distributor_ids(db, user)
    rows = []
    q = {}
    if scoped is not None:
        q["distributor_id"] = {"$in": scoped}
    if party_id:
        q["distributor_id"] = party_id
    async for b in db.dms_ebills.find(q, {"_id": 0}):
        if not _in_range(b.get("created_at"), df, dt):
            continue
        rows.append({
            "bill_no": b.get("ebill_no", ""),
            "date": _fmt_date_short(b.get("created_at")),
            "order_no": b.get("order_no", ""),
            "supplier": "GO OIL Lubricants (Owner)",
            "distributor": b.get("distributor_name", ""),
            "items_count": len(b.get("items", [])),
            "subtotal": float(b.get("subtotal", 0) or 0),
            "gst_total": float(b.get("gst_total", 0) or 0),
            "total": float(b.get("total", 0) or 0),
        })
    rows.sort(key=lambda r: r["date"], reverse=True)
    totals = {
        "count": len(rows),
        "subtotal": round(sum(r["subtotal"] for r in rows), 2),
        "gst_total": round(sum(r["gst_total"] for r in rows), 2),
        "total": round(sum(r["total"] for r in rows), 2),
    }
    columns = [
        _col("bill_no", "Bill No"),
        _col("date", "Date", "date"),
        _col("order_no", "Order No"),
        _col("supplier", "Supplier"),
        _col("distributor", "Distributor"),
        _col("items_count", "Items", "int"),
        _col("subtotal", "Subtotal", "currency", totals=True),
        _col("gst_total", "GST", "currency", totals=True),
        _col("total", "Total", "currency", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Sale Order Report ----------
async def _run_sale_order(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    sale_type = filters.get("sale_type") or "both"
    status_filter = filters.get("status")
    scoped = await _scoped_distributor_ids(db, user)
    rows = []

    if sale_type in ("primary", "both") and user.get("role") != "salesperson":
        q = {}
        if scoped is not None:
            q["distributor_id"] = {"$in": scoped}
        if status_filter:
            q["status"] = status_filter
        async for o in db.dms_primary_orders.find(q, {"_id": 0}):
            if not _in_range(o.get("created_at"), df, dt):
                continue
            rows.append({
                "sale_type": "primary",
                "order_no": o.get("order_no", ""),
                "date": _fmt_date_short(o.get("created_at")),
                "party_name": o.get("distributor_name", ""),
                "status": o.get("status", ""),
                "fulfillment_pct": float(o.get("fulfillment_pct", 0) or 0),
                "items_count": len(o.get("items", [])),
                "total": float(o.get("total", 0) or 0),
            })

    if sale_type in ("secondary", "both"):
        q2 = {}
        if scoped is not None:
            q2["distributor_id"] = {"$in": scoped}
        if status_filter:
            q2["status"] = status_filter
        if user.get("role") == "salesperson":
            q2["placed_by"] = user["id"]
        rmap = await _retailer_map(db)
        async for o in db.dms_secondary_orders.find(q2, {"_id": 0}):
            if not _in_range(o.get("created_at"), df, dt):
                continue
            rows.append({
                "sale_type": "secondary",
                "order_no": o.get("order_no", ""),
                "date": _fmt_date_short(o.get("created_at")),
                "party_name": rmap.get(o.get("retailer_id"), {}).get("name", ""),
                "status": o.get("status", ""),
                "fulfillment_pct": float(o.get("fulfillment_pct", 0) or 0),
                "items_count": len(o.get("items", [])),
                "total": float(o.get("total", 0) or 0),
            })

    rows.sort(key=lambda r: r["date"], reverse=True)
    totals = {
        "count": len(rows),
        "total": round(sum(r["total"] for r in rows), 2),
        "primary_count": sum(1 for r in rows if r["sale_type"] == "primary"),
        "secondary_count": sum(1 for r in rows if r["sale_type"] == "secondary"),
    }
    columns = [
        _col("sale_type", "Type"),
        _col("order_no", "Order No"),
        _col("date", "Date", "date"),
        _col("party_name", "Party"),
        _col("status", "Status"),
        _col("fulfillment_pct", "Fulfil %", "pct"),
        _col("items_count", "Items", "int"),
        _col("total", "Total", "currency", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Day Book ----------
async def _run_day_book(db, user, filters):
    date_str = filters.get("date")
    d = _parse_iso_date(date_str) if date_str else _parse_iso_date(datetime.now().date().isoformat())
    if not d:
        d = _parse_iso_date(datetime.now().date().isoformat())
    df = d.replace(hour=0, minute=0, second=0, microsecond=0)
    dt = d.replace(hour=23, minute=59, second=59, microsecond=999999)

    scoped = await _scoped_distributor_ids(db, user)
    rows = []

    # Sales (primary + secondary)
    q_pe = {"distributor_id": {"$in": scoped}} if scoped is not None else {}
    async for b in db.dms_ebills.find(q_pe, {"_id": 0}):
        if _in_range(b.get("created_at"), df, dt):
            rows.append({"time": b.get("created_at", ""), "voucher_type": "Primary Bill",
                         "reference": b.get("ebill_no", ""),
                         "party": b.get("distributor_name", ""),
                         "debit": 0.0, "credit": float(b.get("total", 0) or 0)})
    rmap = await _retailer_map(db)
    q_rb = {"distributor_id": {"$in": scoped}} if scoped is not None else {}
    async for b in db.dms_retailer_bills.find(q_rb, {"_id": 0}):
        if _in_range(b.get("created_at"), df, dt):
            rows.append({"time": b.get("created_at", ""), "voucher_type": "Retailer Bill",
                         "reference": b.get("bill_no", ""),
                         "party": rmap.get(b.get("retailer_id"), {}).get("name", ""),
                         "debit": 0.0, "credit": float(b.get("total", 0) or 0)})

    # Expenses (visible to all admin/dist)
    async for e in db.dms_expenses.find({}, {"_id": 0}):
        if _in_range(e.get("date") or e.get("created_at"), df, dt):
            rows.append({"time": e.get("date") or e.get("created_at", ""),
                         "voucher_type": "Expense",
                         "reference": e.get("expense_no", ""),
                         "party": e.get("category", ""),
                         "debit": float(e.get("amount", 0) or 0), "credit": 0.0})

    # Cash / bank transactions
    if user.get("role") in ("owner", "owner_accountant", "super_admin"):
        async for t in db.dms_bank_transactions.find({}, {"_id": 0}):
            if _in_range(t.get("date") or t.get("created_at"), df, dt):
                amt = float(t.get("amount", 0) or 0)
                is_debit = (t.get("type") == "withdrawal")
                rows.append({"time": t.get("date") or t.get("created_at", ""),
                             "voucher_type": "Bank " + str(t.get("type", "")),
                             "reference": t.get("ref_no", "") or t.get("id", ""),
                             "party": t.get("narration", ""),
                             "debit": amt if is_debit else 0.0,
                             "credit": 0.0 if is_debit else amt})
        async for t in db.dms_cash_register.find({}, {"_id": 0}):
            if _in_range(t.get("date") or t.get("created_at"), df, dt):
                amt = float(t.get("amount", 0) or 0)
                is_out = (t.get("type") == "out")
                rows.append({"time": t.get("date") or t.get("created_at", ""),
                             "voucher_type": "Cash " + str(t.get("type", "")),
                             "reference": t.get("id", ""),
                             "party": t.get("narration", ""),
                             "debit": amt if is_out else 0.0,
                             "credit": 0.0 if is_out else amt})

    rows.sort(key=lambda r: r["time"])
    totals = {
        "count": len(rows),
        "debit": round(sum(r["debit"] for r in rows), 2),
        "credit": round(sum(r["credit"] for r in rows), 2),
    }
    columns = [
        _col("time", "Time", "date"),
        _col("voucher_type", "Voucher"),
        _col("reference", "Reference"),
        _col("party", "Party / Narration"),
        _col("debit", "Debit", "currency", totals=True),
        _col("credit", "Credit", "currency", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- All Transactions ----------
async def _run_all_transactions(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    scoped = await _scoped_distributor_ids(db, user)
    rows = []

    q_pe = {"distributor_id": {"$in": scoped}} if scoped is not None else {}
    async for b in db.dms_ebills.find(q_pe, {"_id": 0}):
        if _in_range(b.get("created_at"), df, dt):
            rows.append({"date": _fmt_date_short(b.get("created_at")),
                         "voucher_type": "Sale (Primary)",
                         "reference": b.get("ebill_no", ""),
                         "party": b.get("distributor_name", ""),
                         "amount": float(b.get("total", 0) or 0)})
    rmap = await _retailer_map(db)
    q_rb = {"distributor_id": {"$in": scoped}} if scoped is not None else {}
    async for b in db.dms_retailer_bills.find(q_rb, {"_id": 0}):
        if _in_range(b.get("created_at"), df, dt):
            rows.append({"date": _fmt_date_short(b.get("created_at")),
                         "voucher_type": "Sale (Secondary)",
                         "reference": b.get("bill_no", ""),
                         "party": rmap.get(b.get("retailer_id"), {}).get("name", ""),
                         "amount": float(b.get("total", 0) or 0)})
    async for e in db.dms_expenses.find({}, {"_id": 0}):
        if _in_range(e.get("date") or e.get("created_at"), df, dt):
            rows.append({"date": _fmt_date_short(e.get("date") or e.get("created_at")),
                         "voucher_type": "Expense",
                         "reference": e.get("expense_no", ""),
                         "party": e.get("category", ""),
                         "amount": float(e.get("amount", 0) or 0)})
    if user.get("role") in ("owner", "owner_accountant", "super_admin"):
        async for t in db.dms_bank_transactions.find({}, {"_id": 0}):
            if _in_range(t.get("date") or t.get("created_at"), df, dt):
                rows.append({"date": _fmt_date_short(t.get("date") or t.get("created_at")),
                             "voucher_type": "Bank " + str(t.get("type", "")),
                             "reference": t.get("ref_no", "") or t.get("id", ""),
                             "party": t.get("narration", ""),
                             "amount": float(t.get("amount", 0) or 0)})
    rows.sort(key=lambda r: r["date"], reverse=True)
    totals = {"count": len(rows), "amount": round(sum(r["amount"] for r in rows), 2)}
    columns = [
        _col("date", "Date", "date"),
        _col("voucher_type", "Voucher"),
        _col("reference", "Reference"),
        _col("party", "Party / Narration"),
        _col("amount", "Amount", "currency", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Bill Wise Profit ----------
async def _run_bill_wise_profit(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    scoped = await _scoped_distributor_ids(db, user)
    q = {"distributor_id": {"$in": scoped}} if scoped is not None else {}
    pmap = await _product_map(db)
    rmap = await _retailer_map(db)
    rows = []
    async for b in db.dms_retailer_bills.find(q, {"_id": 0}):
        if not _in_range(b.get("created_at"), df, dt):
            continue
        cost = 0.0
        for it in b.get("items", []):
            p = pmap.get(it.get("product_id"), {})
            unit_cost = float(p.get("unit_price", 0) or 0)
            qb = float(it.get("dispatched_qty_boxes", it.get("qty_boxes_ordered", 0)) or 0)
            box_qty = float(it.get("box_qty", 1) or 1)
            qp = float(it.get("dispatched_qty_pcs", 0) or 0)
            cost += unit_cost * (qb + (qp / box_qty if box_qty else 0))
        revenue = float(b.get("subtotal", 0) or 0)
        profit = round(revenue - cost, 2)
        pct = round((profit / revenue) * 100, 2) if revenue else 0.0
        rows.append({
            "bill_no": b.get("bill_no", ""),
            "date": _fmt_date_short(b.get("created_at")),
            "retailer": rmap.get(b.get("retailer_id"), {}).get("name", ""),
            "revenue": round(revenue, 2),
            "cost": round(cost, 2),
            "profit": profit,
            "margin_pct": pct,
        })
    rows.sort(key=lambda r: r["date"], reverse=True)
    totals = {
        "count": len(rows),
        "revenue": round(sum(r["revenue"] for r in rows), 2),
        "cost": round(sum(r["cost"] for r in rows), 2),
        "profit": round(sum(r["profit"] for r in rows), 2),
    }
    columns = [
        _col("bill_no", "Bill No"),
        _col("date", "Date", "date"),
        _col("retailer", "Retailer"),
        _col("revenue", "Revenue", "currency", totals=True),
        _col("cost", "Cost", "currency", totals=True),
        _col("profit", "Profit", "currency", totals=True),
        _col("margin_pct", "Margin %", "pct"),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Profit & Loss ----------
async def _run_profit_loss(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    revenue = 0.0
    async for b in db.dms_ebills.find({}, {"_id": 0}):
        if _in_range(b.get("created_at"), df, dt):
            revenue += float(b.get("total", 0) or 0)
    secondary_rev = 0.0
    async for b in db.dms_retailer_bills.find({}, {"_id": 0}):
        if _in_range(b.get("created_at"), df, dt):
            secondary_rev += float(b.get("total", 0) or 0)
    expenses = 0.0
    async for e in db.dms_expenses.find({}, {"_id": 0}):
        if _in_range(e.get("date") or e.get("created_at"), df, dt):
            expenses += float(e.get("amount", 0) or 0)
    # Owner doesn't have a "purchase" cost — its inventory value is initial
    net = round(revenue - expenses, 2)
    rows = [
        {"head": "Revenue", "sub_head": "Primary Sales (Owner → Distributor)", "amount": round(revenue, 2)},
        {"head": "Revenue", "sub_head": "Secondary Sales (Distributor → Retailer)", "amount": round(secondary_rev, 2)},
        {"head": "Expenses", "sub_head": "Operating Expenses", "amount": round(expenses, 2)},
        {"head": "Net", "sub_head": "Net Profit / (Loss) — Primary only", "amount": net},
    ]
    totals = {"net": net, "revenue": round(revenue, 2), "expenses": round(expenses, 2)}
    columns = [
        _col("head", "Head"),
        _col("sub_head", "Detail"),
        _col("amount", "Amount", "currency"),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Sale Aging ----------
async def _run_sale_aging(db, user, filters):
    as_on = _end_of_day(_parse_iso_date(filters.get("as_on_date")) or _parse_iso_date(datetime.now().date().isoformat()))
    scoped = await _scoped_distributor_ids(db, user)
    rows = []
    q = {"distributor_id": {"$in": scoped}} if scoped is not None else {}
    dmap = await _distributor_map(db)
    rmap = await _retailer_map(db)

    # Primary bills (ebills) → paid_amt from primary_ledger
    async for b in db.dms_ebills.find(q, {"_id": 0}):
        paid = 0.0
        async for l in db.dms_primary_ledger.find(
            {"reference_id": b.get("id"), "kind": "payment"}, {"_id": 0, "amount": 1}
        ):
            paid += float(l.get("amount", 0) or 0)
        outstanding = float(b.get("total", 0) or 0) - paid
        if outstanding <= 0.01:
            continue
        days = _days_between(b.get("created_at"), as_on)
        rows.append({
            "bill_type": "Primary",
            "bill_no": b.get("ebill_no", ""),
            "date": _fmt_date_short(b.get("created_at")),
            "party": dmap.get(b.get("distributor_id"), {}).get("name", ""),
            "amount": round(float(b.get("total", 0) or 0), 2),
            "paid": round(paid, 2),
            "outstanding": round(outstanding, 2),
            "days_old": days,
            "bucket": _age_bucket(days),
        })
    # Secondary
    async for b in db.dms_retailer_bills.find(q, {"_id": 0}):
        paid = 0.0
        async for l in db.dms_retailer_ledger.find(
            {"reference_id": b.get("id"), "kind": "payment"}, {"_id": 0, "amount": 1}
        ):
            paid += float(l.get("amount", 0) or 0)
        outstanding = float(b.get("total", 0) or 0) - paid
        if outstanding <= 0.01:
            continue
        days = _days_between(b.get("created_at"), as_on)
        rows.append({
            "bill_type": "Secondary",
            "bill_no": b.get("bill_no", ""),
            "date": _fmt_date_short(b.get("created_at")),
            "party": rmap.get(b.get("retailer_id"), {}).get("name", ""),
            "amount": round(float(b.get("total", 0) or 0), 2),
            "paid": round(paid, 2),
            "outstanding": round(outstanding, 2),
            "days_old": days,
            "bucket": _age_bucket(days),
        })
    rows.sort(key=lambda r: r["days_old"], reverse=True)
    totals = {
        "count": len(rows),
        "amount": round(sum(r["amount"] for r in rows), 2),
        "paid": round(sum(r["paid"] for r in rows), 2),
        "outstanding": round(sum(r["outstanding"] for r in rows), 2),
        "b_0_30": round(sum(r["outstanding"] for r in rows if r["bucket"] == "0-30"), 2),
        "b_31_60": round(sum(r["outstanding"] for r in rows if r["bucket"] == "31-60"), 2),
        "b_61_90": round(sum(r["outstanding"] for r in rows if r["bucket"] == "61-90"), 2),
        "b_90p": round(sum(r["outstanding"] for r in rows if r["bucket"] == "90+"), 2),
    }
    columns = [
        _col("bill_type", "Type"), _col("bill_no", "Bill No"), _col("date", "Date", "date"),
        _col("party", "Party"),
        _col("amount", "Amount", "currency", totals=True),
        _col("paid", "Paid", "currency", totals=True),
        _col("outstanding", "Outstanding", "currency", totals=True),
        _col("days_old", "Days", "int"),
        _col("bucket", "Bucket"),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Purchase Aging ----------
async def _run_purchase_aging(db, user, filters):
    """Same as sale aging but from the distributor's perspective (primary bills owed to owner)."""
    as_on = _end_of_day(_parse_iso_date(filters.get("as_on_date")) or _parse_iso_date(datetime.now().date().isoformat()))
    scoped = await _scoped_distributor_ids(db, user)
    q = {"distributor_id": {"$in": scoped}} if scoped is not None else {}
    dmap = await _distributor_map(db)
    rows = []
    async for b in db.dms_ebills.find(q, {"_id": 0}):
        paid = 0.0
        async for l in db.dms_primary_ledger.find(
            {"reference_id": b.get("id"), "kind": "payment"}, {"_id": 0, "amount": 1}
        ):
            paid += float(l.get("amount", 0) or 0)
        outstanding = float(b.get("total", 0) or 0) - paid
        if outstanding <= 0.01:
            continue
        days = _days_between(b.get("created_at"), as_on)
        rows.append({
            "bill_no": b.get("ebill_no", ""),
            "date": _fmt_date_short(b.get("created_at")),
            "supplier": "GO OIL Lubricants (Owner)",
            "distributor": dmap.get(b.get("distributor_id"), {}).get("name", ""),
            "amount": round(float(b.get("total", 0) or 0), 2),
            "paid": round(paid, 2),
            "outstanding": round(outstanding, 2),
            "days_old": days,
            "bucket": _age_bucket(days),
        })
    rows.sort(key=lambda r: r["days_old"], reverse=True)
    totals = {
        "count": len(rows),
        "amount": round(sum(r["amount"] for r in rows), 2),
        "paid": round(sum(r["paid"] for r in rows), 2),
        "outstanding": round(sum(r["outstanding"] for r in rows), 2),
    }
    columns = [
        _col("bill_no", "Bill No"), _col("date", "Date", "date"),
        _col("supplier", "Supplier"), _col("distributor", "Distributor"),
        _col("amount", "Amount", "currency", totals=True),
        _col("paid", "Paid", "currency", totals=True),
        _col("outstanding", "Outstanding", "currency", totals=True),
        _col("days_old", "Days", "int"), _col("bucket", "Bucket"),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Cashflow ----------
async def _run_cashflow(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    rows = []
    async for t in db.dms_bank_transactions.find({}, {"_id": 0}):
        if _in_range(t.get("date") or t.get("created_at"), df, dt):
            amt = float(t.get("amount", 0) or 0)
            is_out = t.get("type") == "withdrawal"
            rows.append({"date": _fmt_date_short(t.get("date") or t.get("created_at")),
                         "channel": "Bank",
                         "type": t.get("type", ""),
                         "narration": t.get("narration", ""),
                         "cash_in": 0.0 if is_out else amt,
                         "cash_out": amt if is_out else 0.0})
    async for t in db.dms_cash_register.find({}, {"_id": 0}):
        if _in_range(t.get("date") or t.get("created_at"), df, dt):
            amt = float(t.get("amount", 0) or 0)
            is_out = t.get("type") == "out"
            rows.append({"date": _fmt_date_short(t.get("date") or t.get("created_at")),
                         "channel": "Cash Register",
                         "type": t.get("type", ""),
                         "narration": t.get("narration", ""),
                         "cash_in": 0.0 if is_out else amt,
                         "cash_out": amt if is_out else 0.0})
    async for t in db.dms_loan_transactions.find({}, {"_id": 0}):
        if _in_range(t.get("date") or t.get("created_at"), df, dt):
            amt = float(t.get("amount", 0) or 0)
            kind = t.get("kind", "")
            is_out = kind in ("repayment", "interest")
            rows.append({"date": _fmt_date_short(t.get("date") or t.get("created_at")),
                         "channel": "Loan",
                         "type": kind,
                         "narration": t.get("narration", ""),
                         "cash_in": 0.0 if is_out else amt,
                         "cash_out": amt if is_out else 0.0})
    rows.sort(key=lambda r: r["date"])
    totals = {
        "count": len(rows),
        "cash_in": round(sum(r["cash_in"] for r in rows), 2),
        "cash_out": round(sum(r["cash_out"] for r in rows), 2),
        "net": round(sum(r["cash_in"] for r in rows) - sum(r["cash_out"] for r in rows), 2),
    }
    columns = [
        _col("date", "Date", "date"),
        _col("channel", "Channel"),
        _col("type", "Type"),
        _col("narration", "Narration"),
        _col("cash_in", "Cash In", "currency", totals=True),
        _col("cash_out", "Cash Out", "currency", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Balance Sheet ----------
async def _run_balance_sheet(db, user, filters):
    # As-on-date snapshot
    # Assets
    cash_bank = 0.0
    async for a in db.dms_bank_accounts.find({}, {"_id": 0}):
        cash_bank += float(a.get("current_balance", 0) or 0)
    cash_in = 0.0
    cash_out = 0.0
    async for t in db.dms_cash_register.find({}, {"_id": 0}):
        amt = float(t.get("amount", 0) or 0)
        if t.get("type") == "in":
            cash_in += amt
        else:
            cash_out += amt
    cash_hand = round(cash_in - cash_out, 2)
    inv_value = 0.0
    pmap = await _product_map(db)
    async for i in db.dms_owner_inventory.find({}, {"_id": 0}):
        p = pmap.get(i.get("product_id"), {})
        inv_value += float(p.get("unit_price", 0) or 0) * float(i.get("qty_boxes", 0) or 0)
    async for i in db.dms_distributor_inventory.find({}, {"_id": 0}):
        p = pmap.get(i.get("product_id"), {})
        inv_value += float(p.get("unit_price", 0) or 0) * float(i.get("qty_boxes", 0) or 0)
    # Receivables (outstanding sales)
    receivables = 0.0
    async for b in db.dms_ebills.find({}, {"_id": 0}):
        paid = 0.0
        async for l in db.dms_primary_ledger.find(
            {"reference_id": b.get("id"), "kind": "payment"}, {"_id": 0, "amount": 1}
        ):
            paid += float(l.get("amount", 0) or 0)
        receivables += max(0.0, float(b.get("total", 0) or 0) - paid)

    # Liabilities
    loans = 0.0
    async for l in db.dms_loan_accounts.find({}, {"_id": 0}):
        loans += float(l.get("outstanding", 0) or 0)

    assets = round(cash_bank + cash_hand + inv_value + receivables, 2)
    liab = round(loans, 2)
    equity = round(assets - liab, 2)

    rows = [
        {"section": "Assets", "head": "Cash in Bank", "amount": round(cash_bank, 2)},
        {"section": "Assets", "head": "Cash in Hand", "amount": cash_hand},
        {"section": "Assets", "head": "Inventory (owner + distributor)", "amount": round(inv_value, 2)},
        {"section": "Assets", "head": "Sundry Receivables", "amount": round(receivables, 2)},
        {"section": "Assets", "head": "TOTAL ASSETS", "amount": assets},
        {"section": "Liabilities", "head": "Loans (Outstanding)", "amount": loans},
        {"section": "Liabilities", "head": "TOTAL LIABILITIES", "amount": liab},
        {"section": "Equity", "head": "Owner's Equity (Assets − Liabilities)", "amount": equity},
    ]
    totals = {"assets": assets, "liabilities": liab, "equity": equity}
    columns = [
        _col("section", "Section"),
        _col("head", "Item"),
        _col("amount", "Amount", "currency"),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Expense Report ----------
async def _run_expense(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    cat = filters.get("category")
    rows = []
    async for e in db.dms_expenses.find({}, {"_id": 0}):
        if not _in_range(e.get("date") or e.get("created_at"), df, dt):
            continue
        if cat and e.get("category") != cat:
            continue
        rows.append({
            "expense_no": e.get("expense_no", ""),
            "date": _fmt_date_short(e.get("date") or e.get("created_at")),
            "category": e.get("category", ""),
            "vendor": e.get("vendor", ""),
            "description": e.get("description", ""),
            "amount": float(e.get("amount", 0) or 0),
        })
    rows.sort(key=lambda r: r["date"], reverse=True)
    totals = {"count": len(rows), "amount": round(sum(r["amount"] for r in rows), 2)}
    columns = [
        _col("expense_no", "Expense No"),
        _col("date", "Date", "date"),
        _col("category", "Category"),
        _col("vendor", "Vendor"),
        _col("description", "Description"),
        _col("amount", "Amount", "currency", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ===========================================================================
# 2. PARTY REPORTS
# ===========================================================================

# ---------- Party Statement ----------
async def _run_party_statement(db, user, filters):
    party_id = filters.get("party_id") or ""
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    rows = []
    party_name = ""
    running = 0.0
    # Try primary ledger first (distributor)
    async for l in db.dms_primary_ledger.find({"distributor_id": party_id}, {"_id": 0}):
        if not _in_range(l.get("at"), df, dt):
            continue
        amt = float(l.get("amount", 0) or 0)
        _is_debit = l.get("kind") in ("invoice", "debit_note")
        signed = amt if _is_debit else -amt
        running += signed
        rows.append({"date": _fmt_date_short(l.get("at")),
                     "kind": l.get("kind", ""),
                     "reference": l.get("reference_no", ""),
                     "description": l.get("description", ""),
                     "debit": amt if _is_debit else 0.0,
                     "credit": amt if not _is_debit else 0.0,
                     "balance": round(running, 2)})
    if not rows:
        # Retailer ledger
        async for l in db.dms_retailer_ledger.find({"retailer_id": party_id}, {"_id": 0}):
            if not _in_range(l.get("at"), df, dt):
                continue
            amt = float(l.get("amount", 0) or 0)
            _is_debit = l.get("kind") in ("invoice", "debit_note")
            signed = amt if _is_debit else -amt
            running += signed
            rows.append({"date": _fmt_date_short(l.get("at")),
                         "kind": l.get("kind", ""),
                         "reference": l.get("reference_no", ""),
                         "description": l.get("description", ""),
                         "debit": amt if _is_debit else 0.0,
                         "credit": amt if not _is_debit else 0.0,
                         "balance": round(running, 2)})
    # Lookup party name
    if party_id:
        d = await db.dms_distributors.find_one({"id": party_id}, {"_id": 0, "name": 1})
        if d:
            party_name = d.get("name", "")
        else:
            r = await db.dms_retailers.find_one({"id": party_id}, {"_id": 0, "name": 1})
            party_name = (r or {}).get("name", "")

    rows.sort(key=lambda r: r["date"])
    totals = {
        "count": len(rows),
        "debit": round(sum(r["debit"] for r in rows), 2),
        "credit": round(sum(r["credit"] for r in rows), 2),
        "balance": round(running, 2),
        "party_name": party_name,
    }
    columns = [
        _col("date", "Date", "date"),
        _col("kind", "Type"),
        _col("reference", "Reference"),
        _col("description", "Description"),
        _col("debit", "Debit", "currency", totals=True),
        _col("credit", "Credit", "currency", totals=True),
        _col("balance", "Running Bal.", "currency"),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Party Wise P&L ----------
async def _run_party_wise_profit_loss(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    scoped = await _scoped_distributor_ids(db, user)
    q = {"distributor_id": {"$in": scoped}} if scoped is not None else {}
    rmap = await _retailer_map(db)
    pmap = await _product_map(db)
    agg: Dict[str, Dict[str, Any]] = {}
    async for b in db.dms_retailer_bills.find(q, {"_id": 0}):
        if not _in_range(b.get("created_at"), df, dt):
            continue
        rid = b.get("retailer_id", "")
        row = agg.setdefault(rid, {"party_name": rmap.get(rid, {}).get("name", ""),
                                     "revenue": 0.0, "cost": 0.0, "bills": 0})
        row["bills"] += 1
        row["revenue"] += float(b.get("subtotal", 0) or 0)
        for it in b.get("items", []):
            p = pmap.get(it.get("product_id"), {})
            unit_cost = float(p.get("unit_price", 0) or 0)
            qb = float(it.get("dispatched_qty_boxes", it.get("qty_boxes_ordered", 0)) or 0)
            row["cost"] += unit_cost * qb
    rows = []
    for _, v in agg.items():
        rev = v["revenue"]
        cost = v["cost"]
        profit = round(rev - cost, 2)
        rows.append({
            "party_name": v["party_name"],
            "bills": v["bills"],
            "revenue": round(rev, 2),
            "cost": round(cost, 2),
            "profit": profit,
            "margin_pct": round((profit / rev) * 100, 2) if rev else 0.0,
        })
    rows.sort(key=lambda r: r["profit"], reverse=True)
    totals = {
        "count": len(rows),
        "revenue": round(sum(r["revenue"] for r in rows), 2),
        "cost": round(sum(r["cost"] for r in rows), 2),
        "profit": round(sum(r["profit"] for r in rows), 2),
    }
    columns = [
        _col("party_name", "Party"),
        _col("bills", "Bills", "int"),
        _col("revenue", "Revenue", "currency", totals=True),
        _col("cost", "Cost", "currency", totals=True),
        _col("profit", "Profit", "currency", totals=True),
        _col("margin_pct", "Margin %", "pct"),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- All Parties ----------
async def _run_all_parties(db, user, filters):
    rows = []
    scoped = await _scoped_distributor_ids(db, user)
    dq = {}
    if scoped is not None:
        dq = {"id": {"$in": scoped}}
    async for d in db.dms_distributors.find(dq, {"_id": 0}):
        rows.append({"party_type": "Distributor", "name": d.get("name", ""),
                     "email": d.get("email", ""), "phone": d.get("phone", ""),
                     "gstin": d.get("gstin", ""), "address": d.get("address", ""),
                     "credit_limit": float(d.get("credit_limit", 0) or 0)})
    rq = {}
    if scoped is not None:
        rq = {"distributor_id": {"$in": scoped}}
    async for r in db.dms_retailers.find(rq, {"_id": 0}):
        rows.append({"party_type": "Retailer", "name": r.get("name", ""),
                     "email": r.get("email", ""), "phone": r.get("phone", ""),
                     "gstin": r.get("gstin", ""), "address": r.get("address", ""),
                     "credit_limit": 0.0})
    totals = {"count": len(rows),
              "distributors": sum(1 for r in rows if r["party_type"] == "Distributor"),
              "retailers": sum(1 for r in rows if r["party_type"] == "Retailer")}
    columns = [
        _col("party_type", "Type"),
        _col("name", "Name"),
        _col("email", "Email"),
        _col("phone", "Phone"),
        _col("gstin", "GSTIN"),
        _col("address", "Address"),
        _col("credit_limit", "Credit Limit", "currency"),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Party Report by Items ----------
async def _run_party_by_items(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    party_id = filters.get("party_id")
    scoped = await _scoped_distributor_ids(db, user)
    q = {"distributor_id": {"$in": scoped}} if scoped is not None else {}
    if party_id:
        q = {"$or": [{"distributor_id": party_id}, {"retailer_id": party_id}]}
    rmap = await _retailer_map(db)
    dmap = await _distributor_map(db)
    rows = []
    # Secondary
    async for b in db.dms_retailer_bills.find(q, {"_id": 0}):
        if not _in_range(b.get("created_at"), df, dt):
            continue
        pname = rmap.get(b.get("retailer_id"), {}).get("name", "")
        for it in b.get("items", []):
            rows.append({
                "party_name": pname,
                "sku_code": it.get("sku_code", ""),
                "product_name": it.get("product_name", ""),
                "qty_boxes": float(it.get("dispatched_qty_boxes", it.get("qty_boxes_ordered", 0)) or 0),
                "amount": float(it.get("line_total", it.get("line_subtotal", 0)) or 0),
                "bill_no": b.get("bill_no", ""),
                "date": _fmt_date_short(b.get("created_at")),
            })
    # Primary
    q_p = {}
    if scoped is not None:
        q_p["distributor_id"] = {"$in": scoped}
    if party_id:
        q_p["distributor_id"] = party_id
    async for b in db.dms_ebills.find(q_p, {"_id": 0}):
        if not _in_range(b.get("created_at"), df, dt):
            continue
        pname = dmap.get(b.get("distributor_id"), {}).get("name", "")
        for it in b.get("items", []):
            rows.append({
                "party_name": pname,
                "sku_code": it.get("sku_code", ""),
                "product_name": it.get("product_name", ""),
                "qty_boxes": float(it.get("billed_qty_boxes", it.get("qty_boxes_fulfilled", 0)) or 0),
                "amount": float(it.get("line_total", it.get("line_subtotal", 0)) or 0),
                "bill_no": b.get("ebill_no", ""),
                "date": _fmt_date_short(b.get("created_at")),
            })
    rows.sort(key=lambda r: (r["party_name"], r["sku_code"]))
    totals = {
        "count": len(rows),
        "qty_boxes": round(sum(r["qty_boxes"] for r in rows), 2),
        "amount": round(sum(r["amount"] for r in rows), 2),
    }
    columns = [
        _col("party_name", "Party"),
        _col("sku_code", "SKU"),
        _col("product_name", "Product"),
        _col("qty_boxes", "Qty (Boxes)", "number", totals=True),
        _col("amount", "Amount", "currency", totals=True),
        _col("bill_no", "Bill No"),
        _col("date", "Date", "date"),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Sale/Purchase by Party ----------
async def _run_sale_purchase_by_party(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    scoped = await _scoped_distributor_ids(db, user)
    dmap = await _distributor_map(db)
    rmap = await _retailer_map(db)
    agg = {}
    # Primary sales (distributor perspective: purchase; owner perspective: sale)
    q_p = {"distributor_id": {"$in": scoped}} if scoped is not None else {}
    async for b in db.dms_ebills.find(q_p, {"_id": 0}):
        if not _in_range(b.get("created_at"), df, dt):
            continue
        did = b.get("distributor_id", "")
        row = agg.setdefault(did, {"party_name": dmap.get(did, {}).get("name", ""),
                                    "party_type": "Distributor",
                                    "sale_amount": 0.0, "purchase_amount": 0.0})
        row["purchase_amount"] += float(b.get("total", 0) or 0)  # distributor is buying
    # Secondary sales
    q_s = {"distributor_id": {"$in": scoped}} if scoped is not None else {}
    async for b in db.dms_retailer_bills.find(q_s, {"_id": 0}):
        if not _in_range(b.get("created_at"), df, dt):
            continue
        rid = b.get("retailer_id", "")
        row = agg.setdefault(rid, {"party_name": rmap.get(rid, {}).get("name", ""),
                                    "party_type": "Retailer",
                                    "sale_amount": 0.0, "purchase_amount": 0.0})
        row["sale_amount"] += float(b.get("total", 0) or 0)
    rows = list(agg.values())
    rows.sort(key=lambda r: r["sale_amount"] + r["purchase_amount"], reverse=True)
    totals = {
        "count": len(rows),
        "sale_amount": round(sum(r["sale_amount"] for r in rows), 2),
        "purchase_amount": round(sum(r["purchase_amount"] for r in rows), 2),
    }
    columns = [
        _col("party_type", "Type"),
        _col("party_name", "Party"),
        _col("sale_amount", "Sales", "currency", totals=True),
        _col("purchase_amount", "Purchases", "currency", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Outstanding/Due ----------
async def _run_outstanding_due(db, user, filters):
    scoped = await _scoped_distributor_ids(db, user)
    dmap = await _distributor_map(db)
    rmap = await _retailer_map(db)
    rows = []
    # Primary: outstanding by distributor
    dist_agg: Dict[str, Dict[str, Any]] = {}
    q_p = {"distributor_id": {"$in": scoped}} if scoped is not None else {}
    async for b in db.dms_ebills.find(q_p, {"_id": 0}):
        did = b.get("distributor_id", "")
        row = dist_agg.setdefault(did, {"billed": 0.0, "paid": 0.0})
        row["billed"] += float(b.get("total", 0) or 0)
    async for l in db.dms_primary_ledger.find({"kind": "payment"}, {"_id": 0}):
        did = l.get("distributor_id", "")
        if did in dist_agg:
            dist_agg[did]["paid"] += float(l.get("amount", 0) or 0)
    for did, v in dist_agg.items():
        outstanding = round(v["billed"] - v["paid"], 2)
        if abs(outstanding) < 0.01:
            continue
        rows.append({"party_type": "Distributor",
                     "party_name": dmap.get(did, {}).get("name", ""),
                     "billed": round(v["billed"], 2),
                     "paid": round(v["paid"], 2),
                     "outstanding": outstanding})
    # Secondary: outstanding by retailer
    ret_agg: Dict[str, Dict[str, Any]] = {}
    q_s = {"distributor_id": {"$in": scoped}} if scoped is not None else {}
    async for b in db.dms_retailer_bills.find(q_s, {"_id": 0}):
        rid = b.get("retailer_id", "")
        row = ret_agg.setdefault(rid, {"billed": 0.0, "paid": 0.0})
        row["billed"] += float(b.get("total", 0) or 0)
    async for l in db.dms_retailer_ledger.find({"kind": "payment"}, {"_id": 0}):
        rid = l.get("retailer_id", "")
        if rid in ret_agg:
            ret_agg[rid]["paid"] += float(l.get("amount", 0) or 0)
    for rid, v in ret_agg.items():
        outstanding = round(v["billed"] - v["paid"], 2)
        if abs(outstanding) < 0.01:
            continue
        rows.append({"party_type": "Retailer",
                     "party_name": rmap.get(rid, {}).get("name", ""),
                     "billed": round(v["billed"], 2),
                     "paid": round(v["paid"], 2),
                     "outstanding": outstanding})
    rows.sort(key=lambda r: r["outstanding"], reverse=True)
    totals = {
        "count": len(rows),
        "billed": round(sum(r["billed"] for r in rows), 2),
        "paid": round(sum(r["paid"] for r in rows), 2),
        "outstanding": round(sum(r["outstanding"] for r in rows), 2),
    }
    columns = [
        _col("party_type", "Type"),
        _col("party_name", "Party"),
        _col("billed", "Billed", "currency", totals=True),
        _col("paid", "Paid", "currency", totals=True),
        _col("outstanding", "Outstanding", "currency", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ===========================================================================
# 3. GST REPORTS  (data-view + export only, no GSTN filing)
# ===========================================================================

# ---------- GSTR-1 (Outward Supplies) ----------
async def _run_gstr1(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    dmap = await _distributor_map(db)
    rmap = await _retailer_map(db)
    pmap = await _product_map(db)
    rows = []
    async for b in db.dms_ebills.find({}, {"_id": 0}):
        if not _in_range(b.get("created_at"), df, dt):
            continue
        d = dmap.get(b.get("distributor_id"), {})
        first_hsn = ""
        for it in b.get("items", []):
            p = pmap.get(it.get("product_id"), {})
            if p.get("hsn"):
                first_hsn = p["hsn"]; break
        rows.append({
            "date": _fmt_date_short(b.get("created_at")),
            "invoice_no": b.get("ebill_no", ""),
            "party_name": d.get("name", ""),
            "gstin": d.get("gstin", ""),
            "hsn": first_hsn,
            "taxable": float(b.get("subtotal", 0) or 0),
            "gst": float(b.get("gst_total", 0) or 0),
            "total": float(b.get("total", 0) or 0),
        })
    async for b in db.dms_retailer_bills.find({}, {"_id": 0}):
        if not _in_range(b.get("created_at"), df, dt):
            continue
        r = rmap.get(b.get("retailer_id"), {})
        first_hsn = ""
        for it in b.get("items", []):
            p = pmap.get(it.get("product_id"), {})
            if p.get("hsn"):
                first_hsn = p["hsn"]; break
        rows.append({
            "date": _fmt_date_short(b.get("created_at")),
            "invoice_no": b.get("bill_no", ""),
            "party_name": r.get("name", ""),
            "gstin": r.get("gstin", ""),
            "hsn": first_hsn,
            "taxable": float(b.get("subtotal", 0) or 0),
            "gst": float(b.get("gst_total", 0) or 0),
            "total": float(b.get("total", 0) or 0),
        })
    rows.sort(key=lambda r: r["date"], reverse=True)
    totals = {
        "count": len(rows),
        "taxable": round(sum(r["taxable"] for r in rows), 2),
        "gst": round(sum(r["gst"] for r in rows), 2),
        "total": round(sum(r["total"] for r in rows), 2),
    }
    columns = [
        _col("date", "Date", "date"),
        _col("invoice_no", "Invoice No"),
        _col("party_name", "Party"),
        _col("gstin", "GSTIN"),
        _col("hsn", "HSN"),
        _col("taxable", "Taxable", "currency", totals=True),
        _col("gst", "GST", "currency", totals=True),
        _col("total", "Total", "currency", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- GSTR-2 (Inward Supplies) ----------
async def _run_gstr2(db, user, filters):
    # Purchases from Owner (from a distributor's perspective).
    # For an Owner tenant, there are no inward supplies modelled — will be empty.
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    pmap = await _product_map(db)
    dmap = await _distributor_map(db)
    rows = []
    async for b in db.dms_ebills.find({}, {"_id": 0}):
        if not _in_range(b.get("created_at"), df, dt):
            continue
        first_hsn = ""
        for it in b.get("items", []):
            p = pmap.get(it.get("product_id"), {})
            if p.get("hsn"):
                first_hsn = p["hsn"]; break
        rows.append({
            "date": _fmt_date_short(b.get("created_at")),
            "invoice_no": b.get("ebill_no", ""),
            "supplier": "GO OIL Lubricants (Owner)",
            "gstin": "",
            "hsn": first_hsn,
            "distributor": dmap.get(b.get("distributor_id"), {}).get("name", ""),
            "taxable": float(b.get("subtotal", 0) or 0),
            "gst": float(b.get("gst_total", 0) or 0),
            "total": float(b.get("total", 0) or 0),
        })
    rows.sort(key=lambda r: r["date"], reverse=True)
    totals = {
        "count": len(rows),
        "taxable": round(sum(r["taxable"] for r in rows), 2),
        "gst": round(sum(r["gst"] for r in rows), 2),
        "total": round(sum(r["total"] for r in rows), 2),
    }
    columns = [
        _col("date", "Date", "date"),
        _col("invoice_no", "Invoice No"),
        _col("supplier", "Supplier"),
        _col("gstin", "GSTIN"),
        _col("hsn", "HSN"),
        _col("distributor", "Buyer (Distributor)"),
        _col("taxable", "Taxable", "currency", totals=True),
        _col("gst", "GST", "currency", totals=True),
        _col("total", "Total", "currency", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- GSTR-3B (Summary) ----------
async def _run_gstr3b(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    out_taxable = 0.0
    out_gst = 0.0
    async for b in db.dms_ebills.find({}, {"_id": 0}):
        if _in_range(b.get("created_at"), df, dt):
            out_taxable += float(b.get("subtotal", 0) or 0)
            out_gst += float(b.get("gst_total", 0) or 0)
    async for b in db.dms_retailer_bills.find({}, {"_id": 0}):
        if _in_range(b.get("created_at"), df, dt):
            out_taxable += float(b.get("subtotal", 0) or 0)
            out_gst += float(b.get("gst_total", 0) or 0)
    rows = [
        {"row": "3.1(a)", "description": "Outward taxable supplies (other than zero rated)",
         "taxable_value": round(out_taxable, 2), "igst": 0.0, "cgst": round(out_gst / 2, 2),
         "sgst": round(out_gst / 2, 2), "cess": 0.0},
        {"row": "3.1(b)", "description": "Outward taxable supplies (zero rated)",
         "taxable_value": 0.0, "igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0},
        {"row": "3.1(c)", "description": "Other outward supplies (Nil rated, exempted)",
         "taxable_value": 0.0, "igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0},
        {"row": "4(A)(5)", "description": "All other ITC",
         "taxable_value": 0.0, "igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0},
    ]
    totals = {
        "taxable": round(out_taxable, 2),
        "gst": round(out_gst, 2),
    }
    columns = [
        _col("row", "Row"),
        _col("description", "Description"),
        _col("taxable_value", "Taxable Value", "currency"),
        _col("igst", "IGST", "currency"),
        _col("cgst", "CGST", "currency"),
        _col("sgst", "SGST", "currency"),
        _col("cess", "Cess", "currency"),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- GST Transaction Report ----------
async def _run_gst_transaction(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    pmap = await _product_map(db)
    rows = []
    for coll, kind, num_field in [
        ("dms_ebills", "Primary", "ebill_no"),
        ("dms_retailer_bills", "Secondary", "bill_no"),
    ]:
        async for b in db[coll].find({}, {"_id": 0}):
            if not _in_range(b.get("created_at"), df, dt):
                continue
            for it in b.get("items", []):
                p = pmap.get(it.get("product_id"), {})
                sub = float(it.get("line_subtotal", 0) or 0)
                gst = float(it.get("line_gst", 0) or 0)
                rows.append({
                    "type": kind,
                    "invoice_no": b.get(num_field, ""),
                    "date": _fmt_date_short(b.get("created_at")),
                    "hsn": p.get("hsn", ""),
                    "sku_code": p.get("sku_code", ""),
                    "product_name": p.get("name", it.get("product_name", "")),
                    "taxable": sub,
                    "gst_pct": float(it.get("gst_pct", 0) or 0),
                    "cgst": round(gst / 2, 2),
                    "sgst": round(gst / 2, 2),
                    "total": sub + gst,
                })
    rows.sort(key=lambda r: (r["date"], r["invoice_no"]), reverse=True)
    totals = {
        "count": len(rows),
        "taxable": round(sum(r["taxable"] for r in rows), 2),
        "cgst": round(sum(r["cgst"] for r in rows), 2),
        "sgst": round(sum(r["sgst"] for r in rows), 2),
        "total": round(sum(r["total"] for r in rows), 2),
    }
    columns = [
        _col("type", "Type"),
        _col("invoice_no", "Invoice"),
        _col("date", "Date", "date"),
        _col("hsn", "HSN"),
        _col("sku_code", "SKU"),
        _col("product_name", "Product"),
        _col("taxable", "Taxable", "currency", totals=True),
        _col("gst_pct", "GST %", "pct"),
        _col("cgst", "CGST", "currency", totals=True),
        _col("sgst", "SGST", "currency", totals=True),
        _col("total", "Total", "currency", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- GSTR-9 (Annual Return) ----------
async def _run_gstr9(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    out_taxable = 0.0
    out_gst = 0.0
    async for b in db.dms_ebills.find({}, {"_id": 0}):
        if _in_range(b.get("created_at"), df, dt):
            out_taxable += float(b.get("subtotal", 0) or 0)
            out_gst += float(b.get("gst_total", 0) or 0)
    async for b in db.dms_retailer_bills.find({}, {"_id": 0}):
        if _in_range(b.get("created_at"), df, dt):
            out_taxable += float(b.get("subtotal", 0) or 0)
            out_gst += float(b.get("gst_total", 0) or 0)
    rows = [
        {"table": "Pt II - 4A", "description": "Supplies made to unregistered persons (B2C)",
         "taxable": round(out_taxable, 2), "gst": round(out_gst, 2)},
        {"table": "Pt II - 4B", "description": "Supplies made to registered persons (B2B)",
         "taxable": 0.0, "gst": 0.0},
        {"table": "Pt II - 4C", "description": "Zero rated supplies (Export) on payment of tax",
         "taxable": 0.0, "gst": 0.0},
        {"table": "Pt II - 5A", "description": "Zero rated supplies without payment of tax",
         "taxable": 0.0, "gst": 0.0},
        {"table": "Pt III - 6", "description": "Details of ITC availed",
         "taxable": 0.0, "gst": 0.0},
    ]
    totals = {"taxable": round(out_taxable, 2), "gst": round(out_gst, 2)}
    columns = [
        _col("table", "Table"),
        _col("description", "Description"),
        _col("taxable", "Taxable Value", "currency"),
        _col("gst", "GST", "currency"),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Sale Summary by HSN ----------
async def _run_sale_summary_hsn(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    pmap = await _product_map(db)
    agg: Dict[str, Dict[str, Any]] = {}
    for coll in ["dms_ebills", "dms_retailer_bills"]:
        async for b in db[coll].find({}, {"_id": 0}):
            if not _in_range(b.get("created_at"), df, dt):
                continue
            for it in b.get("items", []):
                p = pmap.get(it.get("product_id"), {})
                hsn = p.get("hsn", "") or "N/A"
                row = agg.setdefault(hsn, {"hsn": hsn, "description": p.get("name", ""),
                                            "qty_boxes": 0.0, "taxable": 0.0,
                                            "gst_pct": float(it.get("gst_pct", 0) or 0), "gst": 0.0})
                row["qty_boxes"] += float(it.get("dispatched_qty_boxes", it.get("billed_qty_boxes", it.get("qty_boxes_ordered", 0))) or 0)
                row["taxable"] += float(it.get("line_subtotal", 0) or 0)
                row["gst"] += float(it.get("line_gst", 0) or 0)
    rows = list(agg.values())
    rows.sort(key=lambda r: r["taxable"], reverse=True)
    totals = {
        "count": len(rows),
        "qty_boxes": round(sum(r["qty_boxes"] for r in rows), 2),
        "taxable": round(sum(r["taxable"] for r in rows), 2),
        "gst": round(sum(r["gst"] for r in rows), 2),
    }
    columns = [
        _col("hsn", "HSN"),
        _col("description", "Description"),
        _col("qty_boxes", "Qty (Boxes)", "number", totals=True),
        _col("gst_pct", "GST %", "pct"),
        _col("taxable", "Taxable", "currency", totals=True),
        _col("gst", "GST", "currency", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- SAC Report ----------
async def _run_sac_report(db, user, filters):
    # No service items modeled in DMS — return empty schema.
    columns = [
        _col("sac_code", "SAC Code"),
        _col("description", "Service Description"),
        _col("taxable", "Taxable", "currency"),
        _col("gst_pct", "GST %", "pct"),
        _col("gst", "GST", "currency"),
    ]
    return {"rows": [], "totals": {"count": 0, "taxable": 0, "gst": 0}, "columns": columns,
            "empty_message": "No service (SAC) transactions in the selected period."}


# ===========================================================================
# 4. ITEM / STOCK REPORTS
# ===========================================================================

# ---------- Stock Summary ----------
async def _run_stock_summary(db, user, filters):
    pmap = await _product_map(db)
    role = user.get("role", "")
    rows = []
    if role in ("owner", "owner_accountant", "super_admin"):
        async for i in db.dms_owner_inventory.find({}, {"_id": 0}):
            p = pmap.get(i.get("product_id"), {})
            rows.append({
                "sku_code": p.get("sku_code", ""),
                "product_name": p.get("name", ""),
                "pack_size": p.get("pack_size", ""),
                "location": "Owner",
                "qty_boxes": float(i.get("qty_boxes", 0) or 0),
                "unit_price": float(p.get("unit_price", 0) or 0),
                "stock_value": round(float(p.get("unit_price", 0) or 0) * float(i.get("qty_boxes", 0) or 0), 2),
            })
        async for i in db.dms_godown_inventory.find({}, {"_id": 0}):
            p = pmap.get(i.get("product_id"), {})
            g = await db.dms_godowns.find_one({"id": i.get("godown_id")}, {"_id": 0, "name": 1})
            rows.append({
                "sku_code": p.get("sku_code", ""),
                "product_name": p.get("name", ""),
                "pack_size": p.get("pack_size", ""),
                "location": (g or {}).get("name", "Godown"),
                "qty_boxes": float(i.get("qty_boxes", 0) or 0),
                "unit_price": float(p.get("unit_price", 0) or 0),
                "stock_value": round(float(p.get("unit_price", 0) or 0) * float(i.get("qty_boxes", 0) or 0), 2),
            })
    if role in ("distributor", "distributor_accountant"):
        did = user.get("distributor_id")
        async for i in db.dms_distributor_inventory.find({"distributor_id": did}, {"_id": 0}):
            p = pmap.get(i.get("product_id"), {})
            rows.append({
                "sku_code": p.get("sku_code", ""),
                "product_name": p.get("name", ""),
                "pack_size": p.get("pack_size", ""),
                "location": "Distributor",
                "qty_boxes": float(i.get("qty_boxes", 0) or 0),
                "unit_price": float(p.get("unit_price", 0) or 0),
                "stock_value": round(float(p.get("unit_price", 0) or 0) * float(i.get("qty_boxes", 0) or 0), 2),
            })
    rows.sort(key=lambda r: r["stock_value"], reverse=True)
    totals = {
        "count": len(rows),
        "qty_boxes": round(sum(r["qty_boxes"] for r in rows), 2),
        "stock_value": round(sum(r["stock_value"] for r in rows), 2),
    }
    columns = [
        _col("sku_code", "SKU"),
        _col("product_name", "Product"),
        _col("pack_size", "Pack"),
        _col("location", "Location"),
        _col("qty_boxes", "Qty (Boxes)", "number", totals=True),
        _col("unit_price", "Unit Price", "currency"),
        _col("stock_value", "Stock Value", "currency", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Item Report by Party ----------
async def _run_item_by_party(db, user, filters):
    return await _run_party_by_items(db, user, filters)  # reuses same logic


# ---------- Item Wise P&L ----------
async def _run_item_wise_profit_loss(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    scoped = await _scoped_distributor_ids(db, user)
    q = {"distributor_id": {"$in": scoped}} if scoped is not None else {}
    pmap = await _product_map(db)
    agg: Dict[str, Dict[str, Any]] = {}
    async for b in db.dms_retailer_bills.find(q, {"_id": 0}):
        if not _in_range(b.get("created_at"), df, dt):
            continue
        for it in b.get("items", []):
            pid = it.get("product_id", "")
            p = pmap.get(pid, {})
            row = agg.setdefault(pid, {"sku_code": p.get("sku_code", ""),
                                       "product_name": p.get("name", ""),
                                       "qty": 0.0, "revenue": 0.0, "cost": 0.0})
            qb = float(it.get("dispatched_qty_boxes", it.get("qty_boxes_ordered", 0)) or 0)
            row["qty"] += qb
            row["revenue"] += float(it.get("line_subtotal", 0) or 0)
            row["cost"] += float(p.get("unit_price", 0) or 0) * qb
    rows = []
    for _, v in agg.items():
        rev = v["revenue"]; cost = v["cost"]
        profit = round(rev - cost, 2)
        rows.append({
            "sku_code": v["sku_code"], "product_name": v["product_name"],
            "qty_sold": v["qty"],
            "revenue": round(rev, 2), "cost": round(cost, 2),
            "profit": profit,
            "margin_pct": round((profit / rev) * 100, 2) if rev else 0.0,
        })
    rows.sort(key=lambda r: r["profit"], reverse=True)
    totals = {
        "count": len(rows),
        "revenue": round(sum(r["revenue"] for r in rows), 2),
        "cost": round(sum(r["cost"] for r in rows), 2),
        "profit": round(sum(r["profit"] for r in rows), 2),
    }
    columns = [
        _col("sku_code", "SKU"),
        _col("product_name", "Product"),
        _col("qty_sold", "Qty Sold", "number", totals=True),
        _col("revenue", "Revenue", "currency", totals=True),
        _col("cost", "Cost", "currency", totals=True),
        _col("profit", "Profit", "currency", totals=True),
        _col("margin_pct", "Margin %", "pct"),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Low Stock Summary ----------
async def _run_low_stock_summary(db, user, filters):
    pmap = await _product_map(db)
    rows = []
    async for i in db.dms_godown_inventory.find(
        {"reorder_level_boxes": {"$gt": 0},
         "$expr": {"$lte": ["$qty_boxes", "$reorder_level_boxes"]}}, {"_id": 0}
    ):
        p = pmap.get(i.get("product_id"), {})
        g = await db.dms_godowns.find_one({"id": i.get("godown_id")}, {"_id": 0, "name": 1})
        rows.append({
            "sku_code": p.get("sku_code", ""),
            "product_name": p.get("name", ""),
            "godown": (g or {}).get("name", ""),
            "on_hand": float(i.get("qty_boxes", 0) or 0),
            "reorder_level": float(i.get("reorder_level_boxes", 0) or 0),
            "shortfall": max(0.0, float(i.get("reorder_level_boxes", 0) or 0) - float(i.get("qty_boxes", 0) or 0)),
        })
    rows.sort(key=lambda r: r["shortfall"], reverse=True)
    totals = {"count": len(rows), "shortfall": round(sum(r["shortfall"] for r in rows), 2)}
    columns = [
        _col("sku_code", "SKU"),
        _col("product_name", "Product"),
        _col("godown", "Godown"),
        _col("on_hand", "On Hand", "number"),
        _col("reorder_level", "Reorder Level", "number"),
        _col("shortfall", "Shortfall", "number", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Item Detail ----------
async def _run_item_detail(db, user, filters):
    cat = filters.get("category")
    q = {}
    if cat and cat != "all":
        q["category_id"] = cat
    cmap = await _category_map(db)
    rows = []
    async for p in db.dms_products.find(q, {"_id": 0}):
        rows.append({
            "sku_code": p.get("sku_code", ""),
            "product_name": p.get("name", ""),
            "category": cmap.get(p.get("category_id", ""), ""),
            "pack_size": p.get("pack_size", ""),
            "box_qty": float(p.get("box_qty", 0) or 0),
            "hsn": p.get("hsn", ""),
            "gst_pct": float(p.get("gst_pct", 0) or 0),
            "unit_price": float(p.get("unit_price", 0) or 0),
            "previous_price": float(p.get("previous_price", 0) or 0),
        })
    rows.sort(key=lambda r: r["product_name"])
    totals = {"count": len(rows)}
    columns = [
        _col("sku_code", "SKU"),
        _col("product_name", "Product"),
        _col("category", "Category"),
        _col("pack_size", "Pack"),
        _col("box_qty", "Box Qty", "number"),
        _col("hsn", "HSN"),
        _col("gst_pct", "GST %", "pct"),
        _col("unit_price", "Unit Price", "currency"),
        _col("previous_price", "Prev. Price", "currency"),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Stock Detail (movement history) ----------
async def _run_stock_detail(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    item_id = filters.get("item_id")
    q = {}
    if item_id and item_id != "all":
        q["product_id"] = item_id
    pmap = await _product_map(db)
    rows = []
    async for l in db.dms_stock_ledger.find(q, {"_id": 0}):
        if not _in_range(l.get("at"), df, dt):
            continue
        p = pmap.get(l.get("product_id"), {})
        rows.append({
            "date": _fmt_date_short(l.get("at")),
            "sku_code": p.get("sku_code", ""),
            "product_name": p.get("name", ""),
            "scope": l.get("scope", ""),
            "delta_boxes": float(l.get("delta_boxes", 0) or 0),
            "reason": l.get("reason", ""),
            "reference": l.get("reference", ""),
        })
    rows.sort(key=lambda r: r["date"], reverse=True)
    totals = {
        "count": len(rows),
        "in": round(sum(r["delta_boxes"] for r in rows if r["delta_boxes"] > 0), 2),
        "out": round(-sum(r["delta_boxes"] for r in rows if r["delta_boxes"] < 0), 2),
    }
    columns = [
        _col("date", "Date", "date"),
        _col("sku_code", "SKU"),
        _col("product_name", "Product"),
        _col("scope", "Scope"),
        _col("delta_boxes", "Delta (Boxes)", "number"),
        _col("reason", "Reason"),
        _col("reference", "Reference"),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Sale/Purchase by Item Category ----------
async def _run_sale_purchase_by_item_category(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    pmap = await _product_map(db)
    cmap = await _category_map(db)
    agg: Dict[str, Dict[str, Any]] = {}
    for coll, key in [("dms_ebills", "purchase_amount"),
                       ("dms_retailer_bills", "sale_amount")]:
        async for b in db[coll].find({}, {"_id": 0}):
            if not _in_range(b.get("created_at"), df, dt):
                continue
            for it in b.get("items", []):
                p = pmap.get(it.get("product_id"), {})
                cat_id = p.get("category_id", "")
                cat_name = cmap.get(cat_id, "N/A")
                row = agg.setdefault(cat_id or "N/A", {"category": cat_name,
                                                        "sale_amount": 0.0,
                                                        "purchase_amount": 0.0})
                row[key] += float(it.get("line_total", it.get("line_subtotal", 0)) or 0)
    rows = list(agg.values())
    rows.sort(key=lambda r: r["sale_amount"] + r["purchase_amount"], reverse=True)
    totals = {
        "count": len(rows),
        "sale_amount": round(sum(r["sale_amount"] for r in rows), 2),
        "purchase_amount": round(sum(r["purchase_amount"] for r in rows), 2),
    }
    columns = [
        _col("category", "Category"),
        _col("sale_amount", "Sales", "currency", totals=True),
        _col("purchase_amount", "Purchases", "currency", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Stock Summary by Item Category ----------
async def _run_stock_summary_by_item_category(db, user, filters):
    pmap = await _product_map(db)
    cmap = await _category_map(db)
    agg: Dict[str, Dict[str, Any]] = {}
    role = user.get("role", "")
    collections = []
    if role in ("owner", "owner_accountant", "super_admin"):
        collections = [("dms_owner_inventory", None), ("dms_godown_inventory", None)]
    else:
        did = user.get("distributor_id")
        if did:
            collections = [("dms_distributor_inventory", {"distributor_id": did})]
    for coll, extra in collections:
        q = extra or {}
        async for i in db[coll].find(q, {"_id": 0}):
            p = pmap.get(i.get("product_id"), {})
            cid = p.get("category_id", "")
            cname = cmap.get(cid, "N/A")
            row = agg.setdefault(cid or "N/A",
                {"category": cname, "qty_boxes": 0.0, "stock_value": 0.0})
            row["qty_boxes"] += float(i.get("qty_boxes", 0) or 0)
            row["stock_value"] += float(p.get("unit_price", 0) or 0) * float(i.get("qty_boxes", 0) or 0)
    rows = list(agg.values())
    rows.sort(key=lambda r: r["stock_value"], reverse=True)
    totals = {
        "count": len(rows),
        "qty_boxes": round(sum(r["qty_boxes"] for r in rows), 2),
        "stock_value": round(sum(r["stock_value"] for r in rows), 2),
    }
    columns = [
        _col("category", "Category"),
        _col("qty_boxes", "Qty (Boxes)", "number", totals=True),
        _col("stock_value", "Stock Value", "currency", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Item Batch Report ----------
async def _run_item_batch(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    pmap = await _product_map(db)
    rows = []
    async for pb in db.dms_price_batches.find({}, {"_id": 0}):
        if not _in_range(pb.get("from_date"), df, dt):
            continue
        p = pmap.get(pb.get("product_id"), {})
        rows.append({
            "batch_id": pb.get("id", ""),
            "sku_code": p.get("sku_code", ""),
            "product_name": p.get("name", ""),
            "from_date": _fmt_date_short(pb.get("from_date")),
            "to_date": _fmt_date_short(pb.get("to_date")) or "Active",
            "price": float(pb.get("price", 0) or 0),
            "active": pb.get("to_date") is None,
        })
    rows.sort(key=lambda r: r["from_date"], reverse=True)
    totals = {"count": len(rows)}
    columns = [
        _col("sku_code", "SKU"),
        _col("product_name", "Product"),
        _col("from_date", "From", "date"),
        _col("to_date", "To"),
        _col("price", "Price", "currency"),
        _col("active", "Active"),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Item Serial (Coupon serials) ----------
async def _run_item_serial(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    pmap = await _product_map(db)
    rows = []
    async for c in db.dms_coupons.find({}, {"_id": 0}).limit(1000):
        if not _in_range(c.get("created_at"), df, dt):
            continue
        p = pmap.get(c.get("product_id"), {})
        rows.append({
            "serial_no": c.get("coupon_code", ""),
            "sku_code": p.get("sku_code", ""),
            "product_name": p.get("name", ""),
            "status": c.get("status", ""),
            "assigned_on": _fmt_date_short(c.get("assigned_on")),
            "redeemed_on": _fmt_date_short(c.get("redeemed_at")),
        })
    rows.sort(key=lambda r: r["serial_no"])
    totals = {"count": len(rows),
              "unused": sum(1 for r in rows if r["status"] == "unused"),
              "assigned": sum(1 for r in rows if r["status"] == "assigned"),
              "redeemed": sum(1 for r in rows if r["status"] == "redeemed")}
    columns = [
        _col("serial_no", "Serial (Coupon)"),
        _col("sku_code", "SKU"),
        _col("product_name", "Product"),
        _col("status", "Status"),
        _col("assigned_on", "Assigned", "date"),
        _col("redeemed_on", "Redeemed", "date"),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Item Wise Discount ----------
async def _run_item_wise_discount(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    pmap = await _product_map(db)
    agg: Dict[str, Dict[str, Any]] = {}
    for coll in ("dms_ebills", "dms_retailer_bills"):
        async for b in db[coll].find({}, {"_id": 0}):
            if not _in_range(b.get("created_at"), df, dt):
                continue
            for it in b.get("items", []):
                pid = it.get("product_id", "")
                p = pmap.get(pid, {})
                mrp = float(p.get("mrp", p.get("unit_price", 0)) or 0)
                sale_price = float(it.get("unit_price", it.get("box_price", 0)) or 0)
                qb = float(it.get("dispatched_qty_boxes", it.get("billed_qty_boxes", it.get("qty_boxes_ordered", 0))) or 0)
                discount_per_box = max(0.0, mrp - sale_price)
                total_discount = discount_per_box * qb
                row = agg.setdefault(pid, {"sku_code": p.get("sku_code", ""),
                                            "product_name": p.get("name", ""),
                                            "mrp": mrp, "sale_price_avg": sale_price,
                                            "qty": 0.0, "discount": 0.0})
                row["qty"] += qb
                row["discount"] += total_discount
    rows = list(agg.values())
    for r in rows:
        r["discount"] = round(r["discount"], 2)
    rows.sort(key=lambda r: r["discount"], reverse=True)
    totals = {"count": len(rows),
              "discount": round(sum(r["discount"] for r in rows), 2)}
    columns = [
        _col("sku_code", "SKU"),
        _col("product_name", "Product"),
        _col("mrp", "MRP", "currency"),
        _col("sale_price_avg", "Sale Price", "currency"),
        _col("qty", "Qty (Boxes)", "number"),
        _col("discount", "Discount", "currency", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Godown / Stock Transfer ----------
async def _run_godown_transfer(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    rows = []
    gmap = {}
    async for g in db.dms_godowns.find({}, {"_id": 0, "id": 1, "name": 1}):
        gmap[g["id"]] = g.get("name", "")
    async for t in db.dms_stock_transfers.find({}, {"_id": 0}):
        if not _in_range(t.get("created_at") or t.get("date"), df, dt):
            continue
        src = "Owner" if t.get("source_type") == "owner" else gmap.get(t.get("source_godown_id"), "Godown")
        dst = "Owner" if t.get("destination_type") == "owner" else gmap.get(t.get("destination_godown_id"), "Godown")
        total_boxes = sum(float(it.get("qty_boxes", 0) or 0) for it in t.get("items", []))
        rows.append({
            "transfer_no": t.get("transfer_no", ""),
            "date": _fmt_date_short(t.get("created_at") or t.get("date")),
            "from": src,
            "to": dst,
            "boxes": total_boxes,
            "note": t.get("note", ""),
        })
    rows.sort(key=lambda r: r["date"], reverse=True)
    totals = {"count": len(rows), "boxes": round(sum(r["boxes"] for r in rows), 2)}
    columns = [
        _col("transfer_no", "Transfer No"),
        _col("date", "Date", "date"),
        _col("from", "From"),
        _col("to", "To"),
        _col("boxes", "Boxes", "number", totals=True),
        _col("note", "Note"),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ===========================================================================
# 5. SALES TEAM / FIELD REPORTS
# ===========================================================================

# ---------- SP Performance ----------
async def _run_sp_performance(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    sps: Dict[str, Dict[str, Any]] = {}
    _sp_scope = await _scoped_salesperson_ids(db, user)
    _uq = {"role": "salesperson"}
    if _sp_scope is not None:
        _uq["id"] = {"$in": _sp_scope or ["__none__"]}
    async for u in db.users.find(_uq, {"_id": 0, "id": 1, "name": 1}):
        sps[u["id"]] = {"salesperson": u.get("name", ""), "orders": 0, "revenue": 0.0,
                        "retailers": set(), "new_retailers": 0}
    async for o in db.dms_secondary_orders.find({}, {"_id": 0}):
        if not _in_range(o.get("created_at"), df, dt):
            continue
        pby = o.get("placed_by", "")
        if o.get("placed_by_role") != "salesperson":
            continue
        if pby in sps:
            sps[pby]["orders"] += 1
            sps[pby]["revenue"] += float(o.get("total", 0) or 0)
            if o.get("retailer_id"):
                sps[pby]["retailers"].add(o["retailer_id"])
    async for r in db.dms_retailers.find({}, {"_id": 0, "created_by": 1, "created_at": 1}):
        if not _in_range(r.get("created_at"), df, dt):
            continue
        by = r.get("created_by", "")
        if by in sps:
            sps[by]["new_retailers"] += 1
    rows = []
    for _, v in sps.items():
        rows.append({
            "salesperson": v["salesperson"],
            "orders": v["orders"],
            "revenue": round(v["revenue"], 2),
            "retailers_covered": len(v["retailers"]),
            "new_retailers": v["new_retailers"],
        })
    rows.sort(key=lambda r: r["revenue"], reverse=True)
    totals = {
        "count": len(rows),
        "orders": sum(r["orders"] for r in rows),
        "revenue": round(sum(r["revenue"] for r in rows), 2),
        "retailers_covered": sum(r["retailers_covered"] for r in rows),
        "new_retailers": sum(r["new_retailers"] for r in rows),
    }
    columns = [
        _col("salesperson", "Salesperson"),
        _col("orders", "Orders", "int", totals=True),
        _col("revenue", "Revenue", "currency", totals=True),
        _col("retailers_covered", "Retailers Covered", "int", totals=True),
        _col("new_retailers", "New Retailers", "int", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- SP Collection ----------
async def _run_sp_collection(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    sps: Dict[str, Dict[str, Any]] = {}
    _sp_scope = await _scoped_salesperson_ids(db, user)
    _uq = {"role": "salesperson"}
    if _sp_scope is not None:
        _uq["id"] = {"$in": _sp_scope or ["__none__"]}
    async for u in db.users.find(_uq, {"_id": 0, "id": 1, "name": 1}):
        sps[u["id"]] = {"salesperson": u.get("name", ""), "cash": 0.0, "upi": 0.0, "cheque": 0.0, "count": 0}
    async for l in db.dms_retailer_ledger.find({"kind": "payment"}, {"_id": 0}):
        if not _in_range(l.get("at"), df, dt):
            continue
        by = l.get("recorded_by", "")
        if by not in sps:
            continue
        method = (l.get("method") or "").lower()
        amt = float(l.get("amount", 0) or 0)
        if method == "cheque":
            sps[by]["cheque"] += amt
        elif method in ("upi", "bank_transfer", "neft", "rtgs", "card"):
            sps[by]["upi"] += amt
        else:
            sps[by]["cash"] += amt
        sps[by]["count"] += 1
    rows = []
    for _, v in sps.items():
        rows.append({
            "salesperson": v["salesperson"],
            "count": v["count"],
            "cash": round(v["cash"], 2),
            "upi": round(v["upi"], 2),
            "cheque": round(v["cheque"], 2),
            "total": round(v["cash"] + v["upi"] + v["cheque"], 2),
        })
    rows.sort(key=lambda r: r["total"], reverse=True)
    totals = {
        "count": sum(r["count"] for r in rows),
        "cash": round(sum(r["cash"] for r in rows), 2),
        "upi": round(sum(r["upi"] for r in rows), 2),
        "cheque": round(sum(r["cheque"] for r in rows), 2),
        "total": round(sum(r["total"] for r in rows), 2),
    }
    columns = [
        _col("salesperson", "Salesperson"),
        _col("count", "Payments", "int", totals=True),
        _col("cash", "Cash", "currency", totals=True),
        _col("upi", "UPI/Digital", "currency", totals=True),
        _col("cheque", "Cheque", "currency", totals=True),
        _col("total", "Total Collected", "currency", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- TL/RSM Team Report ----------
async def _run_tl_rsm_team(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    rows = []
    # scope: RM sees only their own team leaders (+ themselves); admin sees all
    _tl_q = {"role": "team_leader"}
    _rm_q = {"role": "regional_manager"}
    if user.get("role") == "regional_manager":
        _my_tls = [a["team_leader_id"] async for a in db.dms_rm_assignments.find(
            {"regional_manager_id": user["id"]}, {"_id": 0, "team_leader_id": 1})]
        _tl_q["id"] = {"$in": _my_tls or ["__none__"]}
        _rm_q["id"] = user["id"]
    # Iterate team leaders
    async for tl in db.users.find(_tl_q, {"_id": 0, "id": 1, "name": 1}):
        tlid = tl["id"]
        dist_ids = [a["distributor_id"] async for a in db.dms_tl_assignments.find(
            {"team_leader_id": tlid}, {"_id": 0, "distributor_id": 1})]
        revenue = 0.0
        orders = 0
        async for b in db.dms_retailer_bills.find({"distributor_id": {"$in": dist_ids}}, {"_id": 0}):
            if _in_range(b.get("created_at"), df, dt):
                revenue += float(b.get("total", 0) or 0)
                orders += 1
        sp_ids = [a["salesperson_id"] async for a in db.dms_sp_assignments.find(
            {"distributor_id": {"$in": dist_ids}}, {"_id": 0, "salesperson_id": 1})]
        rows.append({
            "role": "Team Leader",
            "member": tl.get("name", ""),
            "distributors": len(dist_ids),
            "salespersons": len(set(sp_ids)),
            "orders": orders,
            "revenue": round(revenue, 2),
        })
    async for rm in db.users.find(_rm_q, {"_id": 0, "id": 1, "name": 1}):
        rmid = rm["id"]
        tl_ids = [a["team_leader_id"] async for a in db.dms_rm_assignments.find(
            {"regional_manager_id": rmid}, {"_id": 0, "team_leader_id": 1})]
        dist_ids = []
        if tl_ids:
            dist_ids = [a["distributor_id"] async for a in db.dms_tl_assignments.find(
                {"team_leader_id": {"$in": tl_ids}}, {"_id": 0, "distributor_id": 1})]
        revenue = 0.0
        orders = 0
        if dist_ids:
            async for b in db.dms_retailer_bills.find({"distributor_id": {"$in": dist_ids}}, {"_id": 0}):
                if _in_range(b.get("created_at"), df, dt):
                    revenue += float(b.get("total", 0) or 0)
                    orders += 1
        rows.append({
            "role": "Regional Manager",
            "member": rm.get("name", ""),
            "distributors": len(set(dist_ids)),
            "salespersons": len(tl_ids),
            "orders": orders,
            "revenue": round(revenue, 2),
        })
    rows.sort(key=lambda r: r["revenue"], reverse=True)
    totals = {
        "count": len(rows),
        "orders": sum(r["orders"] for r in rows),
        "revenue": round(sum(r["revenue"] for r in rows), 2),
    }
    columns = [
        _col("role", "Role"),
        _col("member", "Name"),
        _col("distributors", "Distributors", "int"),
        _col("salespersons", "SPs / TLs", "int"),
        _col("orders", "Orders", "int", totals=True),
        _col("revenue", "Revenue", "currency", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Live Tracking / Visits ----------
async def _run_live_tracking_visits(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    sps: Dict[str, Dict[str, Any]] = {}
    _sp_scope = await _scoped_salesperson_ids(db, user)
    _uq = {"role": "salesperson"}
    if _sp_scope is not None:
        _uq["id"] = {"$in": _sp_scope or ["__none__"]}
    async for u in db.users.find(_uq, {"_id": 0, "id": 1, "name": 1}):
        sps[u["id"]] = {"salesperson": u.get("name", ""), "visits": 0, "punch_days": 0, "gps_pings": 0}
    async for v in db.dms_visits.find({}, {"_id": 0}):
        if _in_range(v.get("at"), df, dt) and v.get("salesperson_id") in sps:
            sps[v["salesperson_id"]]["visits"] += 1
    async for p in db.dms_punch.find({}, {"_id": 0}):
        if _in_range(p.get("date") or p.get("punch_in"), df, dt) and p.get("user_id") in sps:
            sps[p["user_id"]]["punch_days"] += 1
    async for pg in db.dms_gps_pings.find({}, {"_id": 0}):
        if _in_range(pg.get("at"), df, dt) and pg.get("user_id") in sps:
            sps[pg["user_id"]]["gps_pings"] += 1
    rows = list(sps.values())
    rows.sort(key=lambda r: r["visits"], reverse=True)
    totals = {
        "count": len(rows),
        "visits": sum(r["visits"] for r in rows),
        "punch_days": sum(r["punch_days"] for r in rows),
        "gps_pings": sum(r["gps_pings"] for r in rows),
    }
    columns = [
        _col("salesperson", "Salesperson"),
        _col("visits", "Retailer Visits", "int", totals=True),
        _col("punch_days", "Punch Days", "int", totals=True),
        _col("gps_pings", "GPS Pings", "int", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------- Order Cancellation ----------
async def _run_order_cancellation(db, user, filters):
    df = _parse_iso_date(filters.get("date_from"))
    dt = _end_of_day(_parse_iso_date(filters.get("date_to")))
    scoped = await _scoped_distributor_ids(db, user)
    rows = []
    q = {"status": "cancelled"}
    if scoped is not None:
        q["distributor_id"] = {"$in": scoped}
    if user.get("role") == "salesperson":
        q["placed_by"] = user["id"]
    async for o in db.dms_secondary_orders.find(q, {"_id": 0}):
        if not _in_range(o.get("cancelled_at") or o.get("updated_at") or o.get("created_at"), df, dt):
            continue
        rows.append({
            "order_no": o.get("order_no", ""),
            "order_type": "Secondary",
            "date": _fmt_date_short(o.get("created_at")),
            "cancelled_on": _fmt_date_short(o.get("cancelled_at") or o.get("updated_at")),
            "cancelled_by_role": o.get("cancelled_by_role", ""),
            "reason": o.get("cancel_reason", ""),
            "amount": float(o.get("total", 0) or 0),
        })
    q_p = {"status": "cancelled"}
    if scoped is not None:
        q_p["distributor_id"] = {"$in": scoped}
    async for o in db.dms_primary_orders.find(q_p, {"_id": 0}):
        if not _in_range(o.get("cancelled_at") or o.get("updated_at") or o.get("created_at"), df, dt):
            continue
        rows.append({
            "order_no": o.get("order_no", ""),
            "order_type": "Primary",
            "date": _fmt_date_short(o.get("created_at")),
            "cancelled_on": _fmt_date_short(o.get("cancelled_at") or o.get("updated_at")),
            "cancelled_by_role": o.get("cancelled_by_role", ""),
            "reason": o.get("cancel_reason", ""),
            "amount": float(o.get("total", 0) or 0),
        })
    rows.sort(key=lambda r: r["cancelled_on"], reverse=True)
    totals = {"count": len(rows), "amount": round(sum(r["amount"] for r in rows), 2)}
    columns = [
        _col("order_no", "Order No"),
        _col("order_type", "Type"),
        _col("date", "Placed", "date"),
        _col("cancelled_on", "Cancelled", "date"),
        _col("cancelled_by_role", "By"),
        _col("reason", "Reason"),
        _col("amount", "Amount", "currency", totals=True),
    ]
    return {"rows": rows, "totals": totals, "columns": columns}


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------
RUN_REGISTRY: Dict[str, Callable[[Any, Dict, Dict], Awaitable[Dict]]] = {
    "sale": _run_sale,
    "purchase": _run_purchase,
    "sale_order": _run_sale_order,
    "day_book": _run_day_book,
    "all_transactions": _run_all_transactions,
    "bill_wise_profit": _run_bill_wise_profit,
    "profit_loss": _run_profit_loss,
    "sale_aging": _run_sale_aging,
    "purchase_aging": _run_purchase_aging,
    "cashflow": _run_cashflow,
    "balance_sheet": _run_balance_sheet,
    "expense": _run_expense,
    "party_statement": _run_party_statement,
    "party_wise_profit_loss": _run_party_wise_profit_loss,
    "all_parties": _run_all_parties,
    "party_by_items": _run_party_by_items,
    "sale_purchase_by_party": _run_sale_purchase_by_party,
    "outstanding_due": _run_outstanding_due,
    "gstr1": _run_gstr1,
    "gstr2": _run_gstr2,
    "gstr3b": _run_gstr3b,
    "gst_transaction": _run_gst_transaction,
    "gstr9": _run_gstr9,
    "sale_summary_hsn": _run_sale_summary_hsn,
    "sac_report": _run_sac_report,
    "stock_summary": _run_stock_summary,
    "item_by_party": _run_item_by_party,
    "item_wise_profit_loss": _run_item_wise_profit_loss,
    "low_stock_summary": _run_low_stock_summary,
    "item_detail": _run_item_detail,
    "stock_detail": _run_stock_detail,
    "sale_purchase_by_item_category": _run_sale_purchase_by_item_category,
    "stock_summary_by_item_category": _run_stock_summary_by_item_category,
    "item_batch": _run_item_batch,
    "item_serial": _run_item_serial,
    "item_wise_discount": _run_item_wise_discount,
    "godown_transfer": _run_godown_transfer,
    "sp_performance": _run_sp_performance,
    "sp_collection": _run_sp_collection,
    "tl_rsm_team": _run_tl_rsm_team,
    "live_tracking_visits": _run_live_tracking_visits,
    "order_cancellation": _run_order_cancellation,
}


async def run_report(db, user, report_id: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    filters = filters or {}
    fn = RUN_REGISTRY.get(report_id)
    if not fn:
        return {"rows": [], "totals": {}, "columns": [], "error": "Unknown report"}
    return await fn(db, user, filters)


# Legacy alias for existing router import
async def run_sale_report(db, user, date_from=None, date_to=None, sale_type="both", party_id=None):
    return await _run_sale(db, user,
        {"date_from": date_from, "date_to": date_to, "sale_type": sale_type, "party_id": party_id})
