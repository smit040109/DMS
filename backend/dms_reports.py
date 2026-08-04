"""
Phase 3 — Reports Module.

Provides:
- REPORT_CATALOG: metadata for all ~40 reports across 5 categories
- role_can_see_report(): RBAC gate on the report itself
- Sale Report engine (fully live in this iteration)

Other reports are catalogued as status="coming_soon" for the frontend Hub.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 40-Report Catalogue
# ---------------------------------------------------------------------------
# status: "live"  → endpoint implemented in this release
#         "coming_soon" → placeholder tile in Reports Hub
# allowed_roles: list of roles that can see this report at all.
#                Retailer is never allowed. Sales team roles get scoped data
#                inside the report itself.
# ---------------------------------------------------------------------------

_MGMT_ROLES = [
    "owner", "owner_accountant",
    "distributor", "distributor_accountant",
    "salesperson", "team_leader", "regional_manager",
]

_ADMIN_ROLES = ["owner", "owner_accountant", "team_leader", "regional_manager"]
_ADMIN_AND_DIST = _ADMIN_ROLES + ["distributor", "distributor_accountant"]
_ALL_NON_RETAILER = _MGMT_ROLES
_ADMIN_ONLY = ["owner", "owner_accountant"]

REPORT_CATALOG: List[Dict[str, Any]] = [
    # ---------------- 1. TRANSACTION REPORTS ----------------
    {
        "id": "sale",
        "name": "Sale Report",
        "category": "transaction",
        "description": "Primary + secondary sale bills within a date range.",
        "status": "live",
        "allowed_roles": _ALL_NON_RETAILER,
        "filters": ["date_from", "date_to", "sale_type", "party_id"],
    },
    {"id": "purchase", "name": "Purchase Report", "category": "transaction",
     "description": "Purchases made by the entity in the selected period.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": ["date_from", "date_to"]},
    {"id": "sale_order", "name": "Sale Order Report", "category": "transaction",
     "description": "Sale orders (before invoicing) placed in the period.",
     "status": "coming_soon", "allowed_roles": _ALL_NON_RETAILER, "filters": ["date_from", "date_to"]},
    {"id": "day_book", "name": "Day Book", "category": "transaction",
     "description": "All transactions of a specific day.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": ["date"]},
    {"id": "all_transactions", "name": "All Transactions", "category": "transaction",
     "description": "Combined view of every voucher in the period.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": ["date_from", "date_to"]},
    {"id": "bill_wise_profit", "name": "Bill Wise Profit", "category": "transaction",
     "description": "Profit realised on each bill (revenue − cost).",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": ["date_from", "date_to"]},
    {"id": "profit_loss", "name": "Profit & Loss", "category": "transaction",
     "description": "P&L statement over the period.",
     "status": "coming_soon", "allowed_roles": _ADMIN_ONLY, "filters": ["date_from", "date_to"]},
    {"id": "sale_aging", "name": "Sale Aging Report", "category": "transaction",
     "description": "Ageing buckets for outstanding sale invoices.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": ["date_to"]},
    {"id": "purchase_aging", "name": "Purchase Aging Report", "category": "transaction",
     "description": "Ageing buckets for outstanding purchase invoices.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": ["date_to"]},
    {"id": "cashflow", "name": "Cashflow", "category": "transaction",
     "description": "Cash in/out across bank, cash register and loan flows.",
     "status": "coming_soon", "allowed_roles": _ADMIN_ONLY, "filters": ["date_from", "date_to"]},
    {"id": "balance_sheet", "name": "Balance Sheet", "category": "transaction",
     "description": "Assets vs liabilities snapshot.",
     "status": "coming_soon", "allowed_roles": _ADMIN_ONLY, "filters": ["as_on_date"]},
    {"id": "expense", "name": "Expense Report", "category": "transaction",
     "description": "Expenses booked in the period, by category.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": ["date_from", "date_to", "category"]},

    # ---------------- 2. PARTY REPORTS ----------------
    {"id": "party_statement", "name": "Party Statement", "category": "party",
     "description": "Full ledger statement for one party.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": ["date_from", "date_to", "party_id"]},
    {"id": "party_wise_profit_loss", "name": "Party Wise Profit & Loss", "category": "party",
     "description": "Profitability per party.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": ["date_from", "date_to"]},
    {"id": "all_parties", "name": "All Parties Report", "category": "party",
     "description": "Master list of every party with basic details.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": []},
    {"id": "party_by_items", "name": "Party Report by Items", "category": "party",
     "description": "Item-wise breakdown per party.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": ["date_from", "date_to", "party_id"]},
    {"id": "sale_purchase_by_party", "name": "Sale/Purchase by Party", "category": "party",
     "description": "Sales + purchase totals grouped by party.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": ["date_from", "date_to"]},
    {"id": "outstanding_due", "name": "Outstanding/Due Report", "category": "party",
     "description": "All outstanding balances receivable/payable.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": ["as_on_date"]},

    # ---------------- 3. GST REPORTS ----------------
    {"id": "gstr1", "name": "GSTR-1", "category": "gst",
     "description": "Outward supplies (data-view + export only, no GSTN filing).",
     "status": "coming_soon", "allowed_roles": _ADMIN_ONLY, "filters": ["date_from", "date_to"]},
    {"id": "gstr2", "name": "GSTR-2", "category": "gst",
     "description": "Inward supplies (data-view + export only).",
     "status": "coming_soon", "allowed_roles": _ADMIN_ONLY, "filters": ["date_from", "date_to"]},
    {"id": "gstr3b", "name": "GSTR-3B", "category": "gst",
     "description": "Summary return (data-view + export only).",
     "status": "coming_soon", "allowed_roles": _ADMIN_ONLY, "filters": ["date_from", "date_to"]},
    {"id": "gst_transaction", "name": "GST Transaction Report", "category": "gst",
     "description": "Every taxable transaction with GST breakup.",
     "status": "coming_soon", "allowed_roles": _ADMIN_ONLY, "filters": ["date_from", "date_to"]},
    {"id": "gstr9", "name": "GSTR-9", "category": "gst",
     "description": "Annual return summary (data-view + export only).",
     "status": "coming_soon", "allowed_roles": _ADMIN_ONLY, "filters": ["fy_year"]},
    {"id": "sale_summary_hsn", "name": "Sale Summary by HSN", "category": "gst",
     "description": "Sale totals grouped by HSN code.",
     "status": "coming_soon", "allowed_roles": _ADMIN_ONLY, "filters": ["date_from", "date_to"]},
    {"id": "sac_report", "name": "SAC Report", "category": "gst",
     "description": "Service Accounting Code report for services rendered.",
     "status": "coming_soon", "allowed_roles": _ADMIN_ONLY, "filters": ["date_from", "date_to"]},

    # ---------------- 4. ITEM / STOCK REPORTS ----------------
    {"id": "stock_summary", "name": "Stock Summary Report", "category": "stock",
     "description": "Current on-hand quantity for every SKU.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": []},
    {"id": "item_by_party", "name": "Item Report by Party", "category": "stock",
     "description": "Items sold/purchased grouped by party.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": ["date_from", "date_to"]},
    {"id": "item_wise_profit_loss", "name": "Item Wise Profit & Loss", "category": "stock",
     "description": "Profit contribution per SKU.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": ["date_from", "date_to"]},
    {"id": "low_stock_summary", "name": "Low Stock Summary Report", "category": "stock",
     "description": "SKUs at or below their reorder level.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": []},
    {"id": "item_detail", "name": "Item Detail Report", "category": "stock",
     "description": "Master detail card for a single item.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": ["item_id"]},
    {"id": "stock_detail", "name": "Stock Detail Report", "category": "stock",
     "description": "Movement history for stock across all godowns.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": ["date_from", "date_to"]},
    {"id": "sale_purchase_by_item_category", "name": "Sale/Purchase by Item Category", "category": "stock",
     "description": "Sales + purchases rolled up per item category.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": ["date_from", "date_to"]},
    {"id": "stock_summary_by_item_category", "name": "Stock Summary by Item Category", "category": "stock",
     "description": "On-hand stock grouped by item category.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": []},
    {"id": "item_batch", "name": "Item Batch Report", "category": "stock",
     "description": "Batch-wise stock and movements.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": ["date_from", "date_to"]},
    {"id": "item_serial", "name": "Item Serial Report", "category": "stock",
     "description": "Serial-number-wise tracking (where applicable).",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": ["date_from", "date_to"]},
    {"id": "item_wise_discount", "name": "Item Wise Discount", "category": "stock",
     "description": "Discounts applied per SKU across sales.",
     "status": "coming_soon", "allowed_roles": _ADMIN_AND_DIST, "filters": ["date_from", "date_to"]},
    {"id": "godown_transfer", "name": "Godown/Stock Transfer Report", "category": "stock",
     "description": "Stock transfers between godowns (and owner ↔ godown).",
     "status": "coming_soon", "allowed_roles": _ADMIN_ONLY, "filters": ["date_from", "date_to"]},

    # ---------------- 5. SALES TEAM / FIELD REPORTS ----------------
    {"id": "sp_performance", "name": "Sales Person Wise Performance Report", "category": "sales_team",
     "description": "Orders, revenue, retailers covered per salesperson.",
     "status": "coming_soon", "allowed_roles": ["owner", "owner_accountant", "team_leader", "regional_manager"],
     "filters": ["date_from", "date_to"]},
    {"id": "sp_collection", "name": "Sales Person Wise Collection Report", "category": "sales_team",
     "description": "Cash / cheque collection totals per salesperson.",
     "status": "coming_soon", "allowed_roles": ["owner", "owner_accountant", "team_leader", "regional_manager"],
     "filters": ["date_from", "date_to"]},
    {"id": "tl_rsm_team", "name": "TL/RSM Team Report", "category": "sales_team",
     "description": "Team-level performance for TL and RSM hierarchies.",
     "status": "coming_soon", "allowed_roles": ["owner", "owner_accountant", "regional_manager"],
     "filters": ["date_from", "date_to"]},
    {"id": "live_tracking_visits", "name": "Live Tracking / Visit Report", "category": "sales_team",
     "description": "Field-visit and GPS trail summary per salesperson.",
     "status": "coming_soon", "allowed_roles": ["owner", "owner_accountant", "team_leader", "regional_manager"],
     "filters": ["date_from", "date_to"]},
    {"id": "order_cancellation", "name": "Order Cancellation Report", "category": "sales_team",
     "description": "Orders cancelled after being placed, with reason + role.",
     "status": "coming_soon", "allowed_roles": _ALL_NON_RETAILER, "filters": ["date_from", "date_to"]},
]

# Category display order + labels
CATEGORY_ORDER = [
    ("transaction", "Transaction Reports"),
    ("party", "Party Reports"),
    ("gst", "GST Reports"),
    ("stock", "Item / Stock Reports"),
    ("sales_team", "Sales Team / Field Reports"),
]


def role_can_see_report(report: Dict[str, Any], role: str) -> bool:
    """Return True if the given role is allowed to see this report at all.
    Retailer is never allowed regardless of report config."""
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
# Sale Report — live engine
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
    # Force timezone-aware so downstream comparisons don't crash.
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


async def _scoped_distributor_ids(db, user: Dict[str, Any]) -> Optional[List[str]]:
    """Return the list of distributor IDs this user can see, or None if unrestricted."""
    role = user.get("role")
    if role in ("owner", "owner_accountant", "super_admin"):
        return None  # no restriction
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


async def run_sale_report(
    db,
    user: Dict[str, Any],
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sale_type: str = "both",  # "primary" | "secondary" | "both"
    party_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Return combined Sale Report rows for the given date range and RBAC scope."""
    role = user.get("role")
    if role == "retailer":
        # This is enforced at endpoint level too but double-check.
        return {"rows": [], "totals": {"count": 0, "subtotal": 0.0, "gst_total": 0.0, "total": 0.0}}

    df = _parse_iso_date(date_from)
    dt = _parse_iso_date(date_to)
    if dt:
        # inclusive of the whole day
        dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)

    scoped_dist_ids = await _scoped_distributor_ids(db, user)

    rows: List[Dict[str, Any]] = []

    # ---- primary bills (Owner → Distributor) ----
    if sale_type in ("primary", "both"):
        q: Dict[str, Any] = {}
        if scoped_dist_ids is not None:
            q["distributor_id"] = {"$in": scoped_dist_ids}
        if party_id:
            q["distributor_id"] = party_id
        # SP cannot see primary bills (they don't place primary orders) —
        # scoped_dist_ids handles this naturally.
        if role == "salesperson":
            # Salesperson explicitly limited to secondary they placed.
            pass
        else:
            async for b in db.dms_ebills.find(q, {"_id": 0}):
                created_at = _parse_iso_date(b.get("created_at"))
                if df and created_at and created_at < df:
                    continue
                if dt and created_at and created_at > dt:
                    continue
                rows.append({
                    "sale_type": "primary",
                    "bill_no": b.get("ebill_no", ""),
                    "bill_id": b.get("id"),
                    "date": b.get("created_at", ""),
                    "party_type": "distributor",
                    "party_id": b.get("distributor_id"),
                    "party_name": b.get("distributor_name", ""),
                    "order_no": b.get("order_no", ""),
                    "items_count": len(b.get("items", [])),
                    "subtotal": float(b.get("subtotal", 0) or 0),
                    "gst_total": float(b.get("gst_total", 0) or 0),
                    "total": float(b.get("total", 0) or 0),
                })

    # ---- secondary bills (Distributor → Retailer) ----
    if sale_type in ("secondary", "both"):
        q2: Dict[str, Any] = {}
        if scoped_dist_ids is not None:
            q2["distributor_id"] = {"$in": scoped_dist_ids}
        if party_id:
            # party_id may be either distributor or retailer for secondary
            q2["$or"] = [{"distributor_id": party_id}, {"retailer_id": party_id}]
            q2.pop("distributor_id", None)

        # Salesperson: only bills tied to secondary orders they placed
        sp_order_ids: Optional[set] = None
        if role == "salesperson":
            sp_orders = await db.dms_secondary_orders.find(
                {"placed_by": user["id"]}, {"_id": 0, "id": 1}
            ).to_list(5000)
            sp_order_ids = {o["id"] for o in sp_orders}
            if not sp_order_ids:
                sp_order_ids = {"__none__"}

        # Pre-fetch retailer names for enrichment
        retailer_names: Dict[str, str] = {}
        r_ids: List[str] = []
        async for r in db.dms_retailer_bills.find(q2, {"_id": 0, "retailer_id": 1}):
            rid = r.get("retailer_id")
            if rid:
                r_ids.append(rid)
        if r_ids:
            async for r in db.dms_retailers.find(
                {"id": {"$in": r_ids}}, {"_id": 0, "id": 1, "name": 1}
            ):
                retailer_names[r["id"]] = r.get("name", "")

        async for b in db.dms_retailer_bills.find(q2, {"_id": 0}):
            created_at = _parse_iso_date(b.get("created_at"))
            if df and created_at and created_at < df:
                continue
            if dt and created_at and created_at > dt:
                continue
            if sp_order_ids is not None and b.get("order_id") not in sp_order_ids:
                continue
            rows.append({
                "sale_type": "secondary",
                "bill_no": b.get("bill_no", ""),
                "bill_id": b.get("id"),
                "date": b.get("created_at", ""),
                "party_type": "retailer",
                "party_id": b.get("retailer_id"),
                "party_name": retailer_names.get(b.get("retailer_id"), ""),
                "distributor_id": b.get("distributor_id"),
                "order_no": b.get("order_no", ""),
                "items_count": len(b.get("items", [])),
                "subtotal": float(b.get("subtotal", 0) or 0),
                "gst_total": float(b.get("gst_total", 0) or 0),
                "total": float(b.get("total", 0) or 0),
            })

    # Sort chronologically (newest first)
    rows.sort(key=lambda r: r.get("date") or "", reverse=True)

    totals = {
        "count": len(rows),
        "subtotal": round(sum(r["subtotal"] for r in rows), 2),
        "gst_total": round(sum(r["gst_total"] for r in rows), 2),
        "total": round(sum(r["total"] for r in rows), 2),
        "primary_count": sum(1 for r in rows if r["sale_type"] == "primary"),
        "secondary_count": sum(1 for r in rows if r["sale_type"] == "secondary"),
    }

    return {"rows": rows, "totals": totals}
