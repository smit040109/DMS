"""
VayuERP Platform Router — the SaaS control plane.

Endpoints (all mounted under /api/platform):

 Tenants & Onboarding
  POST   /tenants                       — create tenant + admin (onboarding wizard)
  GET    /tenants                       — list tenants (platform owner only)
  GET    /tenants/{id}                  — tenant detail (platform owner or same-tenant admin)
  PUT    /tenants/{id}                  — update tenant (branding, settings)
  PUT    /tenants/{id}/status           — suspend / activate / archive
  DELETE /tenants/{id}                  — soft delete
  GET    /tenants/{id}/usage            — usage metrics + limits
  POST   /tenants/{id}/impersonate      — issue tenant-admin token (owner only)

 Current tenant (any authenticated user in that tenant)
  GET    /me/tenant                     — full tenant config for chrome
  PUT    /me/tenant/branding            — update branding (tenant admin)
  PUT    /me/tenant/settings            — update settings (tenant admin)

 Subscription plans
  GET    /plans                         — list catalogue
  POST   /plans                         — create/update (owner)
  GET    /subscriptions                 — list (owner sees all, tenant admin sees own)
  POST   /subscriptions                 — create subscription for a tenant
  POST   /subscriptions/{id}/renew      — renew
  POST   /subscriptions/{id}/cancel     — cancel

 Modules catalogue (App Marketplace)
  GET    /modules                       — full catalogue
  POST   /modules                       — create (owner)
  GET    /me/modules                    — modules enabled for current tenant
  POST   /me/modules/{key}/enable       — enable module for tenant
  POST   /me/modules/{key}/disable      — disable

 API Keys / Webhooks (per tenant)
  GET    /me/api-keys
  POST   /me/api-keys                   — issue new key
  DELETE /me/api-keys/{id}              — revoke
  GET    /me/webhooks
  POST   /me/webhooks
  DELETE /me/webhooks/{id}

 Platform analytics (owner only)
  GET    /analytics                     — MRR/ARR/active tenants/usage
  GET    /health                        — platform health rollup

 Billing (mock)
  GET    /me/billing/invoices           — tenant sees own billing invoices
  POST   /platform-invoices             — owner mints
  POST   /platform-invoices/{id}/pay    — mock payment

 Backups
  GET    /backups
  POST   /backups                       — trigger a backup (mock)
  POST   /backups/{id}/restore          — mock restore

 Announcements & Feature flags (owner controls)
  GET    /announcements                 — visible to current tenant
  POST   /announcements
  GET    /feature-flags                 — resolved for current tenant
  POST   /feature-flags                 — owner sets flag
"""
from __future__ import annotations

import os
import secrets
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from pydantic import BaseModel, EmailStr, Field

from tenancy import (
    DEFAULT_TENANT_ID, DEFAULT_TENANT_SLUG,
    bypass_scope, scope_tenant, current_tenant_id, TENANT_EXEMPT_COLLECTIONS,
)

logger = logging.getLogger("vayuerp.platform")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str, length: int = 12) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:length]}"


def _hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


# ------- Pydantic models -----------------------------------------------
class BrandColors(BaseModel):
    primary: str = "#0F172A"
    secondary: str = "#F59E0B"
    accent: str = "#10B981"


class TenantContact(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None


class TenantAddress(BaseModel):
    line1: Optional[str] = None
    line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None


class TaxConfig(BaseModel):
    tax_name: str = "VAT"
    tax_percent: float = 0.0
    tax_number: Optional[str] = None


class InitialAdmin(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=8)


class TenantOnboardIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: Optional[str] = None                 # url-safe id, auto-derived if absent
    industry: str = "distribution"
    country: str = "Nigeria"
    currency: str = "USD"
    timezone: str = "UTC"
    tax: TaxConfig = Field(default_factory=TaxConfig)
    logo_url: Optional[str] = None
    brand_colors: BrandColors = Field(default_factory=BrandColors)
    address: TenantAddress = Field(default_factory=TenantAddress)
    contact: TenantContact = Field(default_factory=TenantContact)
    admin: InitialAdmin
    plan: str = "starter"


class TenantBrandingIn(BaseModel):
    logo_url: Optional[str] = None
    brand_colors: Optional[BrandColors] = None
    display_name: Optional[str] = None
    email_footer: Optional[str] = None
    invoice_footer: Optional[str] = None
    support_email: Optional[str] = None
    support_phone: Optional[str] = None


class TenantSettingsIn(BaseModel):
    industry: Optional[str] = None
    currency: Optional[str] = None
    timezone: Optional[str] = None
    tax: Optional[TaxConfig] = None
    address: Optional[TenantAddress] = None
    contact: Optional[TenantContact] = None
    labels: Optional[Dict[str, str]] = None       # productization labels
    modules_enabled: Optional[List[str]] = None


class PlanIn(BaseModel):
    key: str
    name: str
    price_monthly: float
    price_yearly: float
    currency: str = "USD"
    limits: Dict[str, Any] = Field(default_factory=dict)
    modules: List[str] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)
    trial_days: int = 0


class SubscriptionIn(BaseModel):
    tenant_id: str
    plan_key: str
    billing_cycle: str = "monthly"                # monthly|yearly|trial
    starts_on: Optional[str] = None
    ends_on: Optional[str] = None
    coupon_code: Optional[str] = None


class ModuleIn(BaseModel):
    key: str
    name: str
    category: str
    description: str
    icon: Optional[str] = None
    default_enabled: bool = False
    plan_gated: List[str] = Field(default_factory=list)   # plans that grant this


class ApiKeyIn(BaseModel):
    name: str
    scopes: List[str] = Field(default_factory=lambda: ["read"])
    expires_days: int = 365


class WebhookIn(BaseModel):
    name: str
    url: str
    events: List[str] = Field(default_factory=list)
    secret: Optional[str] = None


class AnnouncementIn(BaseModel):
    title: str
    body: str
    severity: str = "info"                                # info|warn|critical
    audience: str = "all"                                 # all|plan:<key>|tenant:<id>
    starts_on: Optional[str] = None
    ends_on: Optional[str] = None


class FeatureFlagIn(BaseModel):
    key: str
    value: Any
    scope: str = "global"                                 # global|tenant:<id>|plan:<key>


class PlatformInvoiceIn(BaseModel):
    tenant_id: str
    subscription_id: Optional[str] = None
    period_start: str
    period_end: str
    amount: float
    currency: str = "USD"
    items: List[Dict[str, Any]] = Field(default_factory=list)
    tax_percent: float = 0.0
    coupon_code: Optional[str] = None


# ------- Defaults -------------------------------------------------------
DEFAULT_PLANS: List[Dict[str, Any]] = [
    {
        "key": "starter", "name": "Starter",
        "price_monthly": 49, "price_yearly": 490, "currency": "USD",
        "limits": {"users": 5, "storage_gb": 5, "api_calls_per_day": 5000, "warehouses": 1, "modules": 6},
        "modules": ["core", "inventory", "sales", "finance"],
        "features": ["Basic reports", "Email support"],
        "trial_days": 14,
    },
    {
        "key": "professional", "name": "Professional",
        "price_monthly": 199, "price_yearly": 1990, "currency": "USD",
        "limits": {"users": 25, "storage_gb": 50, "api_calls_per_day": 50000, "warehouses": 5, "modules": 15},
        "modules": ["core", "inventory", "sales", "finance", "reverse", "analytics", "crm"],
        "features": ["All Starter features", "Business Intelligence", "Priority support"],
        "trial_days": 14,
    },
    {
        "key": "enterprise", "name": "Enterprise",
        "price_monthly": 799, "price_yearly": 7990, "currency": "USD",
        "limits": {"users": -1, "storage_gb": 500, "api_calls_per_day": 500000, "warehouses": -1, "modules": -1},
        "modules": ["*"],
        "features": ["All modules", "White label", "Dedicated support", "SLA"],
        "trial_days": 30,
    },
    {
        "key": "custom", "name": "Custom",
        "price_monthly": 0, "price_yearly": 0, "currency": "USD",
        "limits": {"users": -1, "storage_gb": -1, "api_calls_per_day": -1, "warehouses": -1, "modules": -1},
        "modules": ["*"],
        "features": ["Everything negotiable"],
        "trial_days": 0,
    },
]


DEFAULT_MODULES: List[Dict[str, Any]] = [
    {"key": "core", "name": "Core", "category": "core", "description": "Base modules (dashboard, users, settings)", "icon": "layout-dashboard", "default_enabled": True},
    {"key": "inventory", "name": "Inventory & Warehouses", "category": "operations", "description": "Batches, stock, dispatches, GRN", "icon": "boxes", "default_enabled": True},
    {"key": "sales", "name": "Sales & Orders", "category": "operations", "description": "Primary/Secondary/Customer orders", "icon": "shopping-cart", "default_enabled": True},
    {"key": "finance", "name": "Finance", "category": "finance", "description": "Ledger, payments, outstanding, coupons, cashback", "icon": "wallet", "default_enabled": True},
    {"key": "reverse", "name": "Reverse Logistics", "category": "operations", "description": "Returns, claims, credit/debit notes, replacements", "icon": "rotate-ccw", "default_enabled": True},
    {"key": "analytics", "name": "Business Intelligence", "category": "analytics", "description": "Executive KPIs, order trace, party 360, alerts", "icon": "bar-chart-3", "default_enabled": True},
    {"key": "crm", "name": "CRM", "category": "growth", "description": "Leads, opportunities, campaigns", "icon": "users", "default_enabled": False},
    {"key": "hrms", "name": "HRMS", "category": "hr", "description": "Employees, attendance, leave", "icon": "user-check", "default_enabled": False},
    {"key": "payroll", "name": "Payroll", "category": "hr", "description": "Salary structures, payslips, statutory", "icon": "banknote", "default_enabled": False},
    {"key": "manufacturing", "name": "Manufacturing", "category": "operations", "description": "BOM, work orders, MRP", "icon": "factory", "default_enabled": False},
    {"key": "transport", "name": "Transport", "category": "operations", "description": "Vehicles, trips, driver logs", "icon": "truck", "default_enabled": False},
    {"key": "assets", "name": "Asset Management", "category": "operations", "description": "Fixed assets, depreciation, maintenance", "icon": "package", "default_enabled": False},
    {"key": "projects", "name": "Project Management", "category": "operations", "description": "Projects, tasks, gantt, timesheets", "icon": "clipboard-list", "default_enabled": False},
    {"key": "visitor", "name": "Visitor Management", "category": "workplace", "description": "Sign-ins, appointments", "icon": "user-plus", "default_enabled": False},
    {"key": "ai_module", "name": "AI Copilot", "category": "ai", "description": "AI-powered business assistant", "icon": "sparkles", "default_enabled": True},
]


DEFAULT_INDUSTRY_LABELS: Dict[str, Dict[str, str]] = {
    "distribution":  {"unit": "unit",  "sku_word": "SKU",     "product_word": "Product", "batch_word": "Batch"},
    "lubricants":    {"unit": "litre", "sku_word": "SKU",     "product_word": "Grade",   "batch_word": "Batch"},
    "fmcg":          {"unit": "unit",  "sku_word": "SKU",     "product_word": "Product", "batch_word": "Lot"},
    "chemicals":     {"unit": "kg",    "sku_word": "Grade",   "product_word": "Product", "batch_word": "Batch"},
    "paint":         {"unit": "litre", "sku_word": "Shade",   "product_word": "Product", "batch_word": "Batch"},
    "pharma":        {"unit": "unit",  "sku_word": "SKU",     "product_word": "Medicine","batch_word": "Batch"},
    "automotive":    {"unit": "unit",  "sku_word": "Part",    "product_word": "Model",   "batch_word": "Lot"},
    "manufacturing": {"unit": "unit",  "sku_word": "Part",    "product_word": "Product", "batch_word": "Lot"},
}


# ============================================================================
def build_platform_router(db, get_current_user, platform_owner_guard, tenant_admin_guard):
    """
    db                   — TenantScopedDatabase (we mostly use raw for platform-level ops)
    get_current_user     — FastAPI dependency (returns dict with id/email/role/tenant_id)
    platform_owner_guard — FastAPI dependency that raises 403 unless user.role == 'platform_owner'
    tenant_admin_guard   — FastAPI dependency that raises 403 unless user is tenant admin / super admin / company admin
    """
    raw = db.raw  # raw motor db for platform-scoped ops
    router = APIRouter(prefix="/platform", tags=["platform"])

    # -------------------- helpers --------------------
    async def _get_tenant(tenant_id: str) -> Dict[str, Any]:
        t = await raw["tenants"].find_one({"id": tenant_id}, {"_id": 0})
        if not t:
            raise HTTPException(404, "Tenant not found")
        return t

    async def _ensure_slug_unique(slug: str) -> None:
        if await raw["tenants"].find_one({"slug": slug}):
            raise HTTPException(400, f"Slug '{slug}' already in use")

    def _slugify(name: str) -> str:
        import re
        s = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
        return s or _new_id("t", 6)

    async def _assert_current_tenant(user: dict) -> str:
        tid = user.get("tenant_id") or current_tenant_id.get()
        if not tid:
            raise HTTPException(400, "No tenant context")
        return tid

    # =====================================================================
    # ONBOARDING — anyone (including platform owner) can POST /tenants.
    # =====================================================================
    @router.post("/tenants")
    async def create_tenant(payload: TenantOnboardIn, user: dict = Depends(get_current_user)):
        # only platform owner may create additional tenants; unauthenticated
        # onboarding could be enabled later via a public marketing form.
        if user.get("role") != "platform_owner":
            raise HTTPException(403, "Only platform owner can onboard tenants")

        slug = payload.slug or _slugify(payload.name)
        await _ensure_slug_unique(slug)
        tid = _new_id("tnt")

        # tenant document
        tenant_doc = {
            "id": tid,
            "slug": slug,
            "name": payload.name,
            "display_name": payload.name,
            "industry": payload.industry,
            "country": payload.country,
            "currency": payload.currency,
            "timezone": payload.timezone,
            "tax": payload.tax.model_dump(),
            "logo_url": payload.logo_url,
            "brand_colors": payload.brand_colors.model_dump(),
            "address": payload.address.model_dump(),
            "contact": payload.contact.model_dump(),
            "labels": DEFAULT_INDUSTRY_LABELS.get(payload.industry, DEFAULT_INDUSTRY_LABELS["distribution"]).copy(),
            "modules_enabled": [m["key"] for m in DEFAULT_MODULES if m["default_enabled"]],
            "plan": payload.plan,
            "status": "active",
            "created_at": _now_iso(),
            "created_by": user["email"],
        }
        await raw["tenants"].insert_one(tenant_doc)

        # initial admin user
        admin_id = _new_id("usr")
        admin_doc = {
            "id": admin_id,
            "tenant_id": tid,
            "email": payload.admin.email.lower().strip(),
            "name": payload.admin.name,
            "role": "company_admin",
            "title": "Tenant Administrator",
            "branch_id": None,
            "password_hash": _hash_password(payload.admin.password),
            "created_at": _now_iso(),
            "avatar": "".join([w[0] for w in payload.admin.name.split()[:2]]).upper(),
        }
        await raw["users"].insert_one(admin_doc)

        # default subscription
        sub_doc = {
            "id": _new_id("sub"),
            "tenant_id": tid,
            "plan_key": payload.plan,
            "billing_cycle": "trial" if payload.plan == "starter" else "monthly",
            "status": "trial" if payload.plan == "starter" else "active",
            "starts_on": _now_iso(),
            "ends_on": (datetime.now(timezone.utc) + timedelta(days=14 if payload.plan == "starter" else 30)).isoformat(),
            "created_at": _now_iso(),
        }
        await raw["subscriptions"].insert_one(sub_doc)

        # seed default roles / permissions rows if any (tenant-scoped)
        await raw["roles"].insert_many([
            {"id": _new_id("rol"), "tenant_id": tid, "key": "company_admin", "name": "Company Admin"},
            {"id": _new_id("rol"), "tenant_id": tid, "key": "regional_manager", "name": "Regional Manager"},
            {"id": _new_id("rol"), "tenant_id": tid, "key": "sales_executive", "name": "Sales Executive"},
            {"id": _new_id("rol"), "tenant_id": tid, "key": "distributor", "name": "Distributor"},
            {"id": _new_id("rol"), "tenant_id": tid, "key": "distributor_accountant", "name": "Distributor Accountant"},
            {"id": _new_id("rol"), "tenant_id": tid, "key": "retailer", "name": "Retailer"},
            {"id": _new_id("rol"), "tenant_id": tid, "key": "customer", "name": "Customer"},
        ])

        tenant_doc.pop("_id", None)
        admin_doc.pop("_id", None); admin_doc.pop("password_hash", None)
        return {"tenant": tenant_doc, "admin": admin_doc, "subscription": {**sub_doc, "_id": None}}

    # =====================================================================
    # TENANT LIST / DETAIL / UPDATE — platform owner
    # =====================================================================
    @router.get("/tenants")
    async def list_tenants(_: dict = Depends(platform_owner_guard),
                            status: Optional[str] = None, q: Optional[str] = None):
        query: Dict[str, Any] = {}
        if status: query["status"] = status
        rows = await raw["tenants"].find(query, {"_id": 0}).sort("created_at", -1).to_list(2000)
        if q:
            ql = q.lower()
            rows = [r for r in rows if ql in (r.get("name","") + r.get("slug","")).lower()]
        # enrich with subscription + user_count
        for r in rows:
            sub = await raw["subscriptions"].find_one({"tenant_id": r["id"], "status": {"$in": ["active","trial"]}}, {"_id": 0}, sort=[("created_at", -1)])
            r["subscription"] = sub
            r["user_count"] = await raw["users"].count_documents({"tenant_id": r["id"]})
        return {"data": rows, "count": len(rows)}

    @router.get("/tenants/{tenant_id}")
    async def get_tenant(tenant_id: str, user: dict = Depends(get_current_user)):
        if user.get("role") != "platform_owner" and user.get("tenant_id") != tenant_id:
            raise HTTPException(403, "Not allowed")
        t = await _get_tenant(tenant_id)
        t["subscription"] = await raw["subscriptions"].find_one({"tenant_id": tenant_id}, {"_id": 0}, sort=[("created_at",-1)])
        t["user_count"] = await raw["users"].count_documents({"tenant_id": tenant_id})
        return t

    @router.put("/tenants/{tenant_id}")
    async def update_tenant(tenant_id: str, payload: Dict[str, Any] = Body(...),
                              _: dict = Depends(platform_owner_guard)):
        payload.pop("_id", None); payload.pop("id", None)
        payload["updated_at"] = _now_iso()
        r = await raw["tenants"].update_one({"id": tenant_id}, {"$set": payload})
        if r.matched_count == 0:
            raise HTTPException(404, "Tenant not found")
        return await raw["tenants"].find_one({"id": tenant_id}, {"_id": 0})

    @router.put("/tenants/{tenant_id}/status")
    async def set_tenant_status(tenant_id: str, status: str = Body(..., embed=True),
                                  _: dict = Depends(platform_owner_guard)):
        if status not in {"active", "suspended", "archived"}:
            raise HTTPException(400, "Invalid status")
        await raw["tenants"].update_one({"id": tenant_id}, {"$set": {"status": status, "updated_at": _now_iso()}})
        return {"ok": True, "status": status}

    @router.delete("/tenants/{tenant_id}")
    async def delete_tenant(tenant_id: str, _: dict = Depends(platform_owner_guard)):
        await raw["tenants"].update_one({"id": tenant_id}, {"$set": {"status": "archived", "updated_at": _now_iso()}})
        return {"ok": True}

    @router.get("/tenants/{tenant_id}/usage")
    async def tenant_usage(tenant_id: str, user: dict = Depends(get_current_user)):
        if user.get("role") != "platform_owner" and user.get("tenant_id") != tenant_id:
            raise HTTPException(403, "Not allowed")
        # count docs per tenant across common colls
        colls = ["users", "products", "skus", "batches", "invoices", "primary_orders",
                  "secondary_orders", "customer_orders", "payments"]
        usage = {}
        for c in colls:
            try:
                usage[c] = await raw[c].count_documents({"tenant_id": tenant_id})
            except Exception:
                usage[c] = 0
        # API usage
        usage["api_calls_last_24h"] = await raw["platform_events"].count_documents(
            {"tenant_id": tenant_id, "kind": "api_call",
              "at": {"$gte": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}})
        # storage estimate (rough)
        usage["storage_bytes_estimate"] = sum(usage.get(c, 0) for c in colls) * 4096
        return {"tenant_id": tenant_id, "usage": usage, "as_of": _now_iso()}

    # =====================================================================
    # ME — current tenant view
    # =====================================================================
    @router.get("/me/tenant")
    async def my_tenant(user: dict = Depends(get_current_user)):
        tid = user.get("tenant_id")
        if not tid:
            # platform_owner has no tenant — return a synthetic "platform" shell
            return {"id": "platform", "name": "VayuERP Platform", "slug": "platform",
                     "brand_colors": {"primary": "#0F172A", "secondary": "#F59E0B", "accent": "#10B981"},
                     "labels": {}, "is_platform": True}
        t = await raw["tenants"].find_one({"id": tid}, {"_id": 0})
        if not t:
            raise HTTPException(404, "Tenant not found")
        t["is_platform"] = False
        return t

    @router.put("/me/tenant/branding")
    async def update_my_branding(payload: TenantBrandingIn, user: dict = Depends(tenant_admin_guard)):
        tid = await _assert_current_tenant(user)
        upd: Dict[str, Any] = {"updated_at": _now_iso()}
        d = payload.model_dump(exclude_none=True)
        if "brand_colors" in d:
            upd["brand_colors"] = d.pop("brand_colors")
        upd.update(d)
        await raw["tenants"].update_one({"id": tid}, {"$set": upd})
        return await raw["tenants"].find_one({"id": tid}, {"_id": 0})

    @router.put("/me/tenant/settings")
    async def update_my_settings(payload: TenantSettingsIn, user: dict = Depends(tenant_admin_guard)):
        tid = await _assert_current_tenant(user)
        d = payload.model_dump(exclude_none=True)
        if "tax" in d: d["tax"] = d["tax"]
        if "address" in d: d["address"] = d["address"]
        if "contact" in d: d["contact"] = d["contact"]
        d["updated_at"] = _now_iso()
        await raw["tenants"].update_one({"id": tid}, {"$set": d})
        return await raw["tenants"].find_one({"id": tid}, {"_id": 0})

    # =====================================================================
    # PLANS + SUBSCRIPTIONS
    # =====================================================================
    @router.get("/plans")
    async def list_plans(user: dict = Depends(get_current_user)):
        rows = await raw["subscription_plans"].find({}, {"_id": 0}).to_list(200)
        return {"data": rows, "count": len(rows)}

    @router.post("/plans")
    async def upsert_plan(payload: PlanIn, _: dict = Depends(platform_owner_guard)):
        doc = payload.model_dump()
        doc["updated_at"] = _now_iso()
        await raw["subscription_plans"].update_one({"key": payload.key}, {"$set": doc, "$setOnInsert": {"created_at": _now_iso()}}, upsert=True)
        return await raw["subscription_plans"].find_one({"key": payload.key}, {"_id": 0})

    @router.get("/subscriptions")
    async def list_subscriptions(user: dict = Depends(get_current_user), tenant_id: Optional[str] = None):
        q: Dict[str, Any] = {}
        if user.get("role") == "platform_owner":
            if tenant_id: q["tenant_id"] = tenant_id
        else:
            q["tenant_id"] = user.get("tenant_id")
        rows = await raw["subscriptions"].find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
        return {"data": rows, "count": len(rows)}

    @router.post("/subscriptions")
    async def create_subscription(payload: SubscriptionIn, _: dict = Depends(platform_owner_guard)):
        plan = await raw["subscription_plans"].find_one({"key": payload.plan_key}, {"_id": 0})
        if not plan:
            raise HTTPException(400, "Plan not found")
        # end current active
        await raw["subscriptions"].update_many(
            {"tenant_id": payload.tenant_id, "status": {"$in": ["active","trial"]}},
            {"$set": {"status": "cancelled", "cancelled_at": _now_iso()}}
        )
        starts = payload.starts_on or _now_iso()
        days = 30 if payload.billing_cycle == "monthly" else (365 if payload.billing_cycle == "yearly" else plan.get("trial_days", 14))
        ends = payload.ends_on or (datetime.fromisoformat(starts.replace("Z","+00:00")) + timedelta(days=days)).isoformat()
        sub = {
            "id": _new_id("sub"),
            "tenant_id": payload.tenant_id,
            "plan_key": payload.plan_key,
            "billing_cycle": payload.billing_cycle,
            "status": "trial" if payload.billing_cycle == "trial" else "active",
            "starts_on": starts, "ends_on": ends,
            "coupon_code": payload.coupon_code,
            "created_at": _now_iso(),
        }
        await raw["subscriptions"].insert_one(sub)
        await raw["tenants"].update_one({"id": payload.tenant_id}, {"$set": {"plan": payload.plan_key}})
        sub.pop("_id", None)
        return sub

    @router.post("/subscriptions/{sub_id}/renew")
    async def renew_subscription(sub_id: str, _: dict = Depends(platform_owner_guard),
                                    billing_cycle: str = Body("monthly", embed=True)):
        sub = await raw["subscriptions"].find_one({"id": sub_id}, {"_id": 0})
        if not sub: raise HTTPException(404, "Subscription not found")
        days = 30 if billing_cycle == "monthly" else 365
        new_end = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        await raw["subscriptions"].update_one({"id": sub_id}, {"$set": {
            "status": "active", "billing_cycle": billing_cycle, "ends_on": new_end, "renewed_at": _now_iso()
        }})
        return await raw["subscriptions"].find_one({"id": sub_id}, {"_id": 0})

    @router.post("/subscriptions/{sub_id}/cancel")
    async def cancel_subscription(sub_id: str, _: dict = Depends(platform_owner_guard)):
        await raw["subscriptions"].update_one({"id": sub_id}, {"$set": {"status": "cancelled", "cancelled_at": _now_iso()}})
        return {"ok": True}

    # =====================================================================
    # MODULES CATALOG
    # =====================================================================
    @router.get("/modules")
    async def list_modules(user: dict = Depends(get_current_user)):
        rows = await raw["modules_catalog"].find({}, {"_id": 0}).to_list(500)
        return {"data": rows, "count": len(rows)}

    @router.post("/modules")
    async def upsert_module(payload: ModuleIn, _: dict = Depends(platform_owner_guard)):
        doc = payload.model_dump()
        doc["updated_at"] = _now_iso()
        await raw["modules_catalog"].update_one({"key": payload.key}, {"$set": doc, "$setOnInsert": {"created_at": _now_iso()}}, upsert=True)
        return await raw["modules_catalog"].find_one({"key": payload.key}, {"_id": 0})

    @router.get("/me/modules")
    async def my_modules(user: dict = Depends(get_current_user)):
        tid = user.get("tenant_id")
        t = await raw["tenants"].find_one({"id": tid}, {"_id": 0}) if tid else None
        enabled = set((t or {}).get("modules_enabled", []))
        catalog = await raw["modules_catalog"].find({}, {"_id": 0}).to_list(500)
        for m in catalog:
            m["enabled"] = m["key"] in enabled
        return {"data": catalog, "enabled": list(enabled)}

    @router.post("/me/modules/{module_key}/enable")
    async def enable_module(module_key: str, user: dict = Depends(tenant_admin_guard)):
        tid = await _assert_current_tenant(user)
        m = await raw["modules_catalog"].find_one({"key": module_key})
        if not m: raise HTTPException(404, "Module not found")
        await raw["tenants"].update_one({"id": tid}, {"$addToSet": {"modules_enabled": module_key}})
        return {"ok": True}

    @router.post("/me/modules/{module_key}/disable")
    async def disable_module(module_key: str, user: dict = Depends(tenant_admin_guard)):
        tid = await _assert_current_tenant(user)
        await raw["tenants"].update_one({"id": tid}, {"$pull": {"modules_enabled": module_key}})
        return {"ok": True}

    # =====================================================================
    # API KEYS
    # =====================================================================
    @router.get("/me/api-keys")
    async def list_api_keys(user: dict = Depends(tenant_admin_guard)):
        tid = await _assert_current_tenant(user)
        rows = await raw["api_keys"].find({"tenant_id": tid}, {"_id": 0, "secret_hash": 0}).to_list(200)
        return {"data": rows, "count": len(rows)}

    @router.post("/me/api-keys")
    async def create_api_key(payload: ApiKeyIn, user: dict = Depends(tenant_admin_guard)):
        tid = await _assert_current_tenant(user)
        secret = secrets.token_urlsafe(32)
        prefix = f"vayu_{secrets.token_hex(4)}"
        doc = {
            "id": _new_id("key"),
            "tenant_id": tid,
            "name": payload.name,
            "prefix": prefix,
            "secret_hash": _hash_password(secret),
            "scopes": payload.scopes,
            "created_by": user["email"],
            "created_at": _now_iso(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=payload.expires_days)).isoformat(),
            "last_used_at": None,
            "revoked": False,
        }
        await raw["api_keys"].insert_one(doc)
        # return plaintext once
        out = {k: v for k, v in doc.items() if k not in {"_id", "secret_hash"}}
        out["secret"] = secret            # shown ONCE
        out["full_key"] = f"{prefix}.{secret}"
        return out

    @router.delete("/me/api-keys/{key_id}")
    async def revoke_api_key(key_id: str, user: dict = Depends(tenant_admin_guard)):
        tid = await _assert_current_tenant(user)
        r = await raw["api_keys"].update_one({"id": key_id, "tenant_id": tid}, {"$set": {"revoked": True, "revoked_at": _now_iso()}})
        if r.matched_count == 0: raise HTTPException(404, "Key not found")
        return {"ok": True}

    # =====================================================================
    # WEBHOOKS
    # =====================================================================
    @router.get("/me/webhooks")
    async def list_webhooks(user: dict = Depends(tenant_admin_guard)):
        tid = await _assert_current_tenant(user)
        rows = await raw["webhooks"].find({"tenant_id": tid}, {"_id": 0}).to_list(200)
        return {"data": rows, "count": len(rows)}

    @router.post("/me/webhooks")
    async def create_webhook(payload: WebhookIn, user: dict = Depends(tenant_admin_guard)):
        tid = await _assert_current_tenant(user)
        doc = {
            "id": _new_id("whk"),
            "tenant_id": tid,
            "name": payload.name,
            "url": payload.url,
            "events": payload.events,
            "secret": payload.secret or secrets.token_urlsafe(16),
            "active": True,
            "created_at": _now_iso(),
        }
        await raw["webhooks"].insert_one(doc)
        doc.pop("_id", None)
        return doc

    @router.delete("/me/webhooks/{whk_id}")
    async def delete_webhook(whk_id: str, user: dict = Depends(tenant_admin_guard)):
        tid = await _assert_current_tenant(user)
        r = await raw["webhooks"].delete_one({"id": whk_id, "tenant_id": tid})
        if r.deleted_count == 0: raise HTTPException(404, "Webhook not found")
        return {"ok": True}

    # =====================================================================
    # PLATFORM ANALYTICS  (platform owner)
    # =====================================================================
    @router.get("/analytics")
    async def platform_analytics(_: dict = Depends(platform_owner_guard)):
        total_tenants = await raw["tenants"].count_documents({})
        active_tenants = await raw["tenants"].count_documents({"status": "active"})
        suspended = await raw["tenants"].count_documents({"status": "suspended"})
        trial_subs = await raw["subscriptions"].count_documents({"status": "trial"})
        active_subs = await raw["subscriptions"].count_documents({"status": "active"})
        total_users = await raw["users"].count_documents({})
        # MRR / ARR
        plans = {p["key"]: p async for p in raw["subscription_plans"].find({}, {"_id": 0})}
        mrr = 0.0
        arr = 0.0
        async for s in raw["subscriptions"].find({"status": {"$in": ["active"]}}, {"_id": 0}):
            plan = plans.get(s.get("plan_key"))
            if not plan: continue
            if s.get("billing_cycle") == "monthly":
                mrr += float(plan.get("price_monthly", 0) or 0)
            elif s.get("billing_cycle") == "yearly":
                mrr += float(plan.get("price_yearly", 0) or 0) / 12
        arr = mrr * 12
        # revenue (mock — from platform_invoices marked paid)
        revenue = 0.0
        async for inv in raw["platform_invoices"].find({"status": "paid"}, {"_id": 0}):
            revenue += float(inv.get("amount", 0) or 0)
        # storage rough
        return {
            "totals": {
                "tenants": total_tenants,
                "active_tenants": active_tenants,
                "suspended_tenants": suspended,
                "users": total_users,
                "active_subscriptions": active_subs,
                "trial_subscriptions": trial_subs,
            },
            "revenue": {"mrr": round(mrr, 2), "arr": round(arr, 2), "revenue_paid": round(revenue, 2)},
            "generated_at": _now_iso(),
        }

    @router.get("/health")
    async def platform_health(_: dict = Depends(platform_owner_guard)):
        try:
            await raw.command("ping")
            db_ok = True
        except Exception:
            db_ok = False
        return {"db_ok": db_ok, "tenants": await raw["tenants"].count_documents({})}

    # =====================================================================
    # BILLING (mock)
    # =====================================================================
    @router.get("/me/billing/invoices")
    async def list_billing_invoices(user: dict = Depends(get_current_user)):
        q = {"tenant_id": user.get("tenant_id")} if user.get("role") != "platform_owner" else {}
        rows = await raw["platform_invoices"].find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
        return {"data": rows, "count": len(rows)}

    @router.post("/platform-invoices")
    async def create_platform_invoice(payload: PlatformInvoiceIn, _: dict = Depends(platform_owner_guard)):
        subtotal = payload.amount
        tax = round(subtotal * (payload.tax_percent or 0) / 100, 2)
        doc = {
            "id": _new_id("pinv"),
            "tenant_id": payload.tenant_id,
            "subscription_id": payload.subscription_id,
            "period_start": payload.period_start,
            "period_end": payload.period_end,
            "amount": subtotal, "tax": tax,
            "total": round(subtotal + tax, 2),
            "currency": payload.currency,
            "items": payload.items,
            "coupon_code": payload.coupon_code,
            "status": "open",
            "created_at": _now_iso(),
        }
        await raw["platform_invoices"].insert_one(doc)
        doc.pop("_id", None)
        return doc

    @router.post("/platform-invoices/{inv_id}/pay")
    async def pay_platform_invoice(inv_id: str, _: dict = Depends(platform_owner_guard),
                                       method: str = Body("mock", embed=True)):
        inv = await raw["platform_invoices"].find_one({"id": inv_id}, {"_id": 0})
        if not inv: raise HTTPException(404, "Not found")
        payment = {
            "id": _new_id("ppay"),
            "tenant_id": inv["tenant_id"],
            "invoice_id": inv_id,
            "amount": inv["total"],
            "method": method,
            "status": "success",
            "paid_at": _now_iso(),
        }
        await raw["platform_payments"].insert_one(payment)
        await raw["platform_invoices"].update_one({"id": inv_id}, {"$set": {"status": "paid", "paid_at": _now_iso()}})
        payment.pop("_id", None)
        return payment

    # =====================================================================
    # BACKUPS  (mock)
    # =====================================================================
    @router.get("/backups")
    async def list_backups(user: dict = Depends(get_current_user)):
        q = {} if user.get("role") == "platform_owner" else {"tenant_id": user.get("tenant_id")}
        rows = await raw["backups"].find(q, {"_id": 0}).sort("created_at", -1).to_list(200)
        return {"data": rows, "count": len(rows)}

    @router.post("/backups")
    async def create_backup(user: dict = Depends(get_current_user),
                              tenant_id: Optional[str] = Body(None, embed=True),
                              kind: str = Body("manual", embed=True)):
        if user.get("role") != "platform_owner" and tenant_id and tenant_id != user.get("tenant_id"):
            raise HTTPException(403, "Not allowed")
        target_tid = tenant_id or user.get("tenant_id")
        doc = {
            "id": _new_id("bkp"),
            "tenant_id": target_tid,
            "kind": kind,
            "status": "success",
            "size_bytes": 1024 * 1024,
            "created_at": _now_iso(),
            "created_by": user["email"],
            "note": "mock backup — production would dump per-tenant collections",
        }
        await raw["backups"].insert_one(doc)
        doc.pop("_id", None)
        return doc

    @router.post("/backups/{bkp_id}/restore")
    async def restore_backup(bkp_id: str, _: dict = Depends(platform_owner_guard)):
        bkp = await raw["backups"].find_one({"id": bkp_id}, {"_id": 0})
        if not bkp: raise HTTPException(404, "Backup not found")
        # MOCK: real impl would restore per-tenant collections from S3/dump
        await raw["backups"].update_one({"id": bkp_id}, {"$set": {"last_restored_at": _now_iso()}})
        return {"ok": True, "note": "MOCK restore succeeded — no data actually replaced."}

    # =====================================================================
    # ANNOUNCEMENTS & FEATURE FLAGS
    # =====================================================================
    @router.get("/announcements")
    async def list_announcements(user: dict = Depends(get_current_user)):
        now = _now_iso()
        # visible to current tenant if audience matches
        rows = await raw["platform_announcements"].find({}, {"_id": 0}).sort("starts_on", -1).to_list(50)
        tid = user.get("tenant_id")
        plan = None
        if tid:
            t = await raw["tenants"].find_one({"id": tid}, {"_id": 0})
            plan = (t or {}).get("plan")
        out = []
        for r in rows:
            if r.get("ends_on") and r["ends_on"] < now: continue
            aud = r.get("audience", "all")
            if aud == "all" or aud == f"tenant:{tid}" or aud == f"plan:{plan}":
                out.append(r)
        return {"data": out, "count": len(out)}

    @router.post("/announcements")
    async def create_announcement(payload: AnnouncementIn, _: dict = Depends(platform_owner_guard)):
        doc = {"id": _new_id("ann"), **payload.model_dump(), "created_at": _now_iso()}
        await raw["platform_announcements"].insert_one(doc)
        doc.pop("_id", None)
        return doc

    @router.get("/feature-flags")
    async def list_feature_flags(user: dict = Depends(get_current_user)):
        rows = await raw["platform_feature_flags"].find({}, {"_id": 0}).to_list(500)
        tid = user.get("tenant_id")
        plan = None
        if tid:
            t = await raw["tenants"].find_one({"id": tid}, {"_id": 0})
            plan = (t or {}).get("plan")
        resolved: Dict[str, Any] = {}
        # global first, then plan, then tenant (most specific wins)
        for r in sorted(rows, key=lambda x: {"global":0,"plan":1,"tenant":2}.get(x.get("scope","global").split(":")[0], 0)):
            scope = r.get("scope","global")
            if scope == "global" or scope == f"plan:{plan}" or scope == f"tenant:{tid}":
                resolved[r["key"]] = r.get("value")
        return {"data": rows, "resolved": resolved}

    @router.post("/feature-flags")
    async def upsert_feature_flag(payload: FeatureFlagIn, _: dict = Depends(platform_owner_guard)):
        doc = payload.model_dump()
        doc["updated_at"] = _now_iso()
        await raw["platform_feature_flags"].update_one({"key": payload.key, "scope": payload.scope}, {"$set": doc, "$setOnInsert": {"created_at": _now_iso()}}, upsert=True)
        return await raw["platform_feature_flags"].find_one({"key": payload.key, "scope": payload.scope}, {"_id": 0})

    # -------------------- expose helpers on router -----------------------
    router.raw_db = raw
    router.DEFAULT_PLANS = DEFAULT_PLANS
    router.DEFAULT_MODULES = DEFAULT_MODULES
    router.DEFAULT_INDUSTRY_LABELS = DEFAULT_INDUSTRY_LABELS

    return router


# =====================================================================
# BOOTSTRAP HELPERS — called from server.py on startup
# =====================================================================
async def bootstrap_platform_data(raw_db, owner_email: str, owner_password: str) -> Dict[str, Any]:
    """Idempotent seed of platform-level data:
       * subscription_plans (from DEFAULT_PLANS)
       * modules_catalog (from DEFAULT_MODULES)
       * platform_owner user (owner_email)
       * default GO OIL tenant (DEFAULT_TENANT_ID) if missing
       * default subscription for GO OIL if missing

    Returns a small report.
    """
    report: Dict[str, Any] = {"created": {}, "skipped": {}}

    # plans
    for p in DEFAULT_PLANS:
        existing = await raw_db["subscription_plans"].find_one({"key": p["key"]})
        if not existing:
            doc = {**p, "created_at": _now_iso()}
            await raw_db["subscription_plans"].insert_one(doc)
            report["created"].setdefault("plans", []).append(p["key"])
        else:
            report["skipped"].setdefault("plans", []).append(p["key"])

    # modules
    for m in DEFAULT_MODULES:
        existing = await raw_db["modules_catalog"].find_one({"key": m["key"]})
        if not existing:
            doc = {**m, "created_at": _now_iso()}
            await raw_db["modules_catalog"].insert_one(doc)
            report["created"].setdefault("modules", []).append(m["key"])

    # GO OIL tenant
    gooil = await raw_db["tenants"].find_one({"id": DEFAULT_TENANT_ID})
    if not gooil:
        gooil_doc = {
            "id": DEFAULT_TENANT_ID,
            "slug": DEFAULT_TENANT_SLUG,
            "name": "GO OIL",
            "display_name": "GO OIL Distribution",
            "industry": "lubricants",
            "country": "Nigeria",
            "currency": "USD",
            "timezone": "Africa/Lagos",
            "tax": {"tax_name": "VAT", "tax_percent": 7.5, "tax_number": "GO-OIL-VAT-001"},
            "logo_url": None,
            "brand_colors": {"primary": "#0F172A", "secondary": "#F59E0B", "accent": "#10B981"},
            "address": {"line1": "Victoria Island", "city": "Lagos", "country": "Nigeria"},
            "contact": {"email": "support@gooil.com", "phone": "+234-800-0000-000", "website": "https://gooil.example"},
            "labels": DEFAULT_INDUSTRY_LABELS["lubricants"],
            "modules_enabled": [m["key"] for m in DEFAULT_MODULES if m.get("default_enabled")],
            "plan": "enterprise",
            "status": "active",
            "created_at": _now_iso(),
            "created_by": "system",
        }
        await raw_db["tenants"].insert_one(gooil_doc)
        report["created"]["gooil_tenant"] = True

        # default subscription for GO OIL — enterprise, 1-year
        sub = {
            "id": _new_id("sub"),
            "tenant_id": DEFAULT_TENANT_ID,
            "plan_key": "enterprise",
            "billing_cycle": "yearly",
            "status": "active",
            "starts_on": _now_iso(),
            "ends_on": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
            "created_at": _now_iso(),
        }
        await raw_db["subscriptions"].insert_one(sub)
    else:
        report["skipped"]["gooil_tenant"] = True

    # platform owner user (no tenant_id)
    owner = await raw_db["users"].find_one({"email": owner_email.lower()})
    if not owner:
        owner_doc = {
            "id": _new_id("usr"),
            "tenant_id": None,                     # platform-level
            "email": owner_email.lower(),
            "name": "VayuERP Platform Owner",
            "role": "platform_owner",
            "title": "Platform Owner",
            "branch_id": None,
            "password_hash": _hash_password(owner_password),
            "created_at": _now_iso(),
            "avatar": "VE",
        }
        await raw_db["users"].insert_one(owner_doc)
        report["created"]["platform_owner"] = owner_email
    else:
        # ensure password up to date + role correct
        upd = {"role": "platform_owner", "tenant_id": None}
        try:
            pw_ok = bcrypt.checkpw(owner_password.encode(), (owner.get("password_hash") or "").encode())
        except Exception:
            pw_ok = False
        if not pw_ok:
            upd["password_hash"] = _hash_password(owner_password)
        await raw_db["users"].update_one({"email": owner_email.lower()}, {"$set": upd})
        report["skipped"]["platform_owner"] = owner_email

    return report
