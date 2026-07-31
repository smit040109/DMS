"""GO OIL Distribution Management System — Backend."""
from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

import bcrypt
import jwt as pyjwt
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, Body, Query
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr

from seed_data import SEED
from workflow import build_workflow_router
from finance import build_finance_router
from reverse import build_reverse_router
from analytics import build_analytics_router
from exports import build_exports_router
from notifications import build_notifications_router
from ai_copilot import build_ai_copilot_router
from integrations import build_integrations_router
from seed_workflow import run_seed_workflow
from security import (
    validate_env, parse_cors_origins, limiter, SecurityHeadersMiddleware, role_guard,
)
from tenancy import (
    TenantScopedDatabase, TENANT_EXEMPT_COLLECTIONS,
    DEFAULT_TENANT_ID, DEFAULT_TENANT_SLUG,
    current_tenant_id, bypass_scope, backfill_tenant_id, ensure_tenant_indexes,
)
from platform_router import build_platform_router, bootstrap_platform_data
from dms_router import build_dms_router
from dms_seed import seed_dms, DMS_TENANT_ID
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("vayuerp.core")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
_raw_db = client[os.environ["DB_NAME"]]
# --- Tenant-scoped wrapper. All existing routers see this and become
# --- tenant-safe with zero code changes.
db = TenantScopedDatabase(_raw_db, exempt=TENANT_EXEMPT_COLLECTIONS)

JWT_ALGO = "HS256"
JWT_SECRET = os.environ["JWT_SECRET"]
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@gooil.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "GoOil@2026")
PLATFORM_OWNER_EMAIL = os.environ.get("PLATFORM_OWNER_EMAIL", "owner@vayuerp.com")
PLATFORM_OWNER_PASSWORD = os.environ.get("PLATFORM_OWNER_PASSWORD", "VayuERP@2026")
PLATFORM_NAME = os.environ.get("PLATFORM_NAME", "VayuERP")
SEED_DEMO_DATA = os.environ.get("SEED_DEMO_DATA", "false").lower() in {"1", "true", "yes"}


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def create_access_token(user_id: str, email: str, role: str, tenant_id: Optional[str] = None) -> str:
    payload = {
        "sub": user_id, "email": email, "role": role,
        "tenant_id": tenant_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=12),
        "type": "access",
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        # Users collection is tenant-scoped; look up via RAW db so cross-tenant
        # login continues to work (users email is globally unique).
        user = await _raw_db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        # Set tenant context for this request. Platform owner has None.
        tid = user.get("tenant_id") or payload.get("tenant_id")
        current_tenant_id.set(tid)
        return user
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Guards specific to platform-level access
async def platform_owner_guard(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "platform_owner":
        raise HTTPException(status_code=403, detail="Platform owner access required")
    return user


async def tenant_admin_guard(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") not in {"platform_owner", "super_admin", "company_admin"}:
        raise HTTPException(status_code=403, detail="Tenant admin access required")
    return user


app = FastAPI(title=f"{PLATFORM_NAME} API")
api = APIRouter(prefix="/api")

# Rate-limiter binding
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security headers on every response
app.add_middleware(SecurityHeadersMiddleware, enable_hsts=os.environ.get("ENABLE_HSTS", "").lower() == "true")


# ---------- API usage tracking (Module 9/10) ----------
# Records every /api/* call to platform_events. Non-blocking — errors are
# swallowed so the request path stays fast.
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402

class ApiUsageMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        import time as _t
        started = _t.perf_counter()
        # Extract tenant_id from JWT at request entry so we log it correctly.
        tid_from_jwt = None
        try:
            tok = request.cookies.get("access_token")
            if not tok:
                auth = request.headers.get("Authorization", "")
                if auth.startswith("Bearer "):
                    tok = auth[7:]
            if tok:
                payload = pyjwt.decode(tok, JWT_SECRET, algorithms=[JWT_ALGO], options={"verify_exp": False})
                tid_from_jwt = payload.get("tenant_id")
                # pre-set contextvar so downstream code sees it even if the
                # endpoint doesn't call get_current_user (public endpoints etc).
                current_tenant_id.set(tid_from_jwt)
        except Exception:
            pass

        response = await call_next(request)

        try:
            path = request.url.path
            if path.startswith("/api/") and not path.startswith("/api/health"):
                duration_ms = int((_t.perf_counter() - started) * 1000)
                await _raw_db["platform_events"].insert_one({
                    "id": f"evt-{uuid.uuid4().hex[:12]}",
                    "kind": "api_call",
                    "tenant_id": tid_from_jwt,
                    "method": request.method,
                    "path": path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "at": datetime.now(timezone.utc).isoformat(),
                })
        except Exception:
            pass
        return response

app.add_middleware(ApiUsageMiddleware)

# CORS — driven from env for production. Falls back to '*' for dev.
_cors_origins = parse_cors_origins()
# Allow any preview.emergentagent.com subdomain so dev previews with credentials work
_cors_regex = os.environ.get(
    "CORS_ORIGIN_REGEX",
    r"https://.*\.preview\.emergentagent\.com",
)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_cors_origins if _cors_origins != ["*"] else [],
    allow_origin_regex=_cors_regex,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Role-guard factory shared with all routers
require_admin_role = role_guard(get_current_user)("super_admin", "company_admin")
require_finance_role = role_guard(get_current_user)(
    "super_admin", "company_admin", "distributor_accountant",
)
require_ops_role = role_guard(get_current_user)(
    "super_admin", "company_admin", "regional_manager",
)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "customer"

    def validate_password(self):
        pw = self.password
        errors = []
        if len(pw) < 8:
            errors.append("at least 8 characters")
        if not any(c.isupper() for c in pw):
            errors.append("one uppercase letter")
        if not any(c.isdigit() for c in pw):
            errors.append("one digit")
        if errors:
            raise HTTPException(status_code=400, detail=f"Password must contain: {', '.join(errors)}")


class AiIn(BaseModel):
    prompt: str
    context: Optional[str] = None


# ---------- Auth ----------
@api.post("/auth/login")
@limiter.limit("10/minute")
async def login(request: Request, response: Response, body: LoginIn):
    email = body.email.lower().strip()
    # Users are tenant-scoped in the wrapper; use raw db for the login lookup
    # since email is globally unique across tenants.
    user = await _raw_db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        logger.warning(f"Failed login for {email} from {request.client.host if request.client else '?'}")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    # Suspended tenant guard
    tid = user.get("tenant_id")
    if tid:
        t = await _raw_db.tenants.find_one({"id": tid}, {"_id": 0, "status": 1})
        if t and t.get("status") == "suspended":
            raise HTTPException(status_code=403, detail="Tenant suspended — contact platform administrator")
    # record last login for the master user panel
    try:
        await _raw_db.users.update_one(
            {"id": user["id"]},
            {"$set": {"last_login_at": datetime.now(timezone.utc).isoformat()}},
        )
    except Exception:
        pass
    token = create_access_token(user["id"], user["email"], user["role"], tenant_id=tid)
    response.set_cookie("access_token", token, httponly=True, secure=True, samesite="none", max_age=43200, path="/")
    user.pop("password_hash", None); user.pop("_id", None)
    # set request tenant context
    current_tenant_id.set(tid)
    return {"user": user, "token": token}


@api.post("/auth/register")
@limiter.limit("5/minute")
async def register(request: Request, response: Response, body: RegisterIn):
    body.validate_password()
    email = body.email.lower().strip()
    if await _raw_db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    valid_roles = {r["key"] for r in SEED["roles"]}
    if body.role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role")
    # Self-registration defaults to the GO OIL tenant. In production this
    # endpoint should be scoped by subdomain / tenant_slug in body.
    tid = DEFAULT_TENANT_ID
    user = {
        "id": f"usr-{uuid.uuid4().hex[:12]}",
        "tenant_id": tid,
        "email": email, "name": body.name, "role": body.role, "branch_id": None,
        "title": body.role.replace("_", " ").title(),
        "password_hash": hash_password(body.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "avatar": "".join([w[0] for w in body.name.split()[:2]]).upper(),
    }
    await _raw_db.users.insert_one(user)
    token = create_access_token(user["id"], user["email"], user["role"], tenant_id=tid)
    response.set_cookie("access_token", token, httponly=True, secure=True, samesite="none", max_age=43200, path="/")
    user.pop("password_hash", None); user.pop("_id", None)
    current_tenant_id.set(tid)
    return {"user": user, "token": token}


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"user": user}


@api.get("/auth/roles")
async def get_roles():
    return {"roles": [{"key": r["key"], "name": r["name"]} for r in SEED["roles"]]}


# ---------- Dashboard / specific routes (must come BEFORE generic) ----------
@api.get("/dashboard/kpis")
async def dashboard_kpis(user: dict = Depends(get_current_user)):
    invoices_total = 0
    async for inv in db.invoices.find({}, {"total": 1, "_id": 0}):
        invoices_total += inv.get("total", 0)
    n_orders = await db.primary_orders.count_documents({}) + await db.secondary_orders.count_documents({})
    open_orders = await db.primary_orders.count_documents({"status": {"$in": ["Draft", "Approved", "Ready"]}})
    delayed = await db.dispatches.count_documents({"status": "Delayed"})
    role = user.get("role", "company_admin")

    kpis_by_role = {
        "super_admin": [
            {"label": "Total Revenue", "value": f"${invoices_total/1_000_000:.1f}M", "delta": "+8.2%", "trend": "up"},
            {"label": "Active Tenants", "value": "12", "delta": "+2", "trend": "up"},
            {"label": "Orders (30d)", "value": f"{n_orders:,}", "delta": "+5.6%", "trend": "up"},
            {"label": "SLA Health", "value": "97.1%", "delta": "+1.2%", "trend": "up"},
            {"label": "Open Approvals", "value": "18", "delta": "-3", "trend": "down"},
        ],
        "company_admin": [
            {"label": "Revenue", "value": f"${invoices_total/1_000_000:.1f}M", "delta": "+8.2%", "trend": "up"},
            {"label": "Dispatch Volume", "value": "12,480", "delta": "+5.6%", "trend": "up"},
            {"label": "Fill Rate", "value": "97.1%", "delta": "+1.2%", "trend": "up"},
            {"label": "Open Orders", "value": f"{open_orders}", "delta": "-3.4%", "trend": "down"},
            {"label": "Collection Efficiency", "value": "92.8%", "delta": "-1.1%", "trend": "down"},
        ],
        "regional_manager": [
            {"label": "Region Revenue", "value": "$4.2M", "delta": "+6.4%", "trend": "up"},
            {"label": "Active Distributors", "value": "18", "delta": "+2", "trend": "up"},
            {"label": "Region Fill Rate", "value": "96.4%", "delta": "+0.9%", "trend": "up"},
            {"label": "Delayed Dispatches", "value": str(delayed), "delta": "-2", "trend": "down"},
            {"label": "Retailer Coverage", "value": "84%", "delta": "+3%", "trend": "up"},
        ],
        "sales_executive": [
            {"label": "My Target", "value": "$180K", "delta": "72% achieved", "trend": "up"},
            {"label": "Visits This Week", "value": "34", "delta": "+8", "trend": "up"},
            {"label": "Secondary Orders", "value": "26", "delta": "+4", "trend": "up"},
            {"label": "New Retailers", "value": "5", "delta": "+2", "trend": "up"},
            {"label": "Pending Collections", "value": "$12.4K", "delta": "3 overdue", "trend": "down"},
        ],
        "distributor": [
            {"label": "Available Credit", "value": "$420K", "delta": "84% utilized", "trend": "up"},
            {"label": "Open Primary Orders", "value": "8", "delta": "2 pending approval", "trend": "up"},
            {"label": "Stock Value", "value": "$1.8M", "delta": "+4.2%", "trend": "up"},
            {"label": "Retailers Under Me", "value": "42", "delta": "+3", "trend": "up"},
            {"label": "MTD Payments", "value": "$96K", "delta": "+12%", "trend": "up"},
        ],
        "distributor_accountant": [
            {"label": "Receivables", "value": "$342K", "delta": "12 overdue", "trend": "down"},
            {"label": "Payables", "value": "$118K", "delta": "on time", "trend": "up"},
            {"label": "Reconciliation Pending", "value": "6", "delta": "-2", "trend": "down"},
            {"label": "Credit Notes", "value": "3", "delta": "$8.4K", "trend": "up"},
            {"label": "Ledger Health", "value": "Balanced", "delta": "verified", "trend": "up"},
        ],
        "retailer": [
            {"label": "Cashback Balance", "value": "$1,240", "delta": "+$220", "trend": "up"},
            {"label": "MTD Orders", "value": "9", "delta": "+2", "trend": "up"},
            {"label": "Outstanding", "value": "$2,180", "delta": "next due in 6d", "trend": "up"},
            {"label": "Loyalty Tier", "value": "Gold", "delta": "1,240 pts", "trend": "up"},
            {"label": "Active Coupons", "value": "3", "delta": "expires soon", "trend": "up"},
        ],
        "customer": [
            {"label": "Active Orders", "value": "2", "delta": "1 in transit", "trend": "up"},
            {"label": "Lifetime Value", "value": "$18,420", "delta": "+$1.2K", "trend": "up"},
            {"label": "Loyalty Points", "value": "980", "delta": "+120", "trend": "up"},
            {"label": "Next Delivery", "value": "Tomorrow", "delta": "SO-10486", "trend": "up"},
            {"label": "Saved Products", "value": "12", "delta": "+2", "trend": "up"},
        ],
    }
    return {"kpis": kpis_by_role.get(role, kpis_by_role["company_admin"])}


@api.get("/dashboard/analytics")
async def dashboard_analytics(user: dict = Depends(get_current_user)):
    return SEED["analytics"]


@api.get("/dashboard/activity")
async def activity(user: dict = Depends(get_current_user)):
    docs = await db.notifications.find({}, {"_id": 0}).sort("created_at", -1).to_list(20)
    return {"activity": docs}


@api.get("/dashboard/tasks")
async def tasks(user: dict = Depends(get_current_user)):
    docs = await db.approvals.find({"status": "Pending"}, {"_id": 0}).to_list(20)
    return {"tasks": docs}


@api.get("/master-data")
async def master_data(user: dict = Depends(get_current_user)):
    return SEED["master_data"]


@api.get("/admin/users")
async def list_users(user: dict = Depends(require_admin_role)):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(500)
    return {"data": users, "count": len(users)}


@api.post("/ai/ask")
async def ai_ask(body: AiIn, user: dict = Depends(get_current_user)):
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI library not available: {e}")
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")
    prod_ct = await db.products.count_documents({})
    sku_ct = await db.skus.count_documents({})
    po_ct = await db.primary_orders.count_documents({})
    so_ct = await db.secondary_orders.count_documents({})
    inv_ct = await db.invoices.count_documents({})
    ctx = (
        f"You are the AI Copilot inside the GO OIL Distribution Management System (DMS). "
        f"You help {user.get('role','company_admin').replace('_',' ')} users with insights on orders, "
        f"inventory, dispatches, ledger and KPIs. Respond concisely (max 6 short bullet points). "
        f"Never invent numbers not supported by context.\n\n"
        f"BUSINESS SNAPSHOT: products={prod_ct}, skus={sku_ct}, primary_orders={po_ct}, "
        f"secondary_orders={so_ct}, invoices={inv_ct}."
    )
    if body.context:
        ctx += f"\n\nEXTRA CONTEXT:\n{body.context}"
    session_id = f"{user['id']}-{uuid.uuid4().hex[:8]}"
    try:
        chat = LlmChat(api_key=key, session_id=session_id, system_message=ctx).with_model("anthropic", "claude-sonnet-4-5-20250929")
        reply = await chat.send_message(UserMessage(text=body.prompt))
        return {"reply": reply}
    except Exception as e:
        logger.exception("AI error")
        raise HTTPException(status_code=500, detail=f"AI error: {e}")


# ---------- Generic collection routes (last) ----------
COLLECTIONS = {
    "branches": "branches",
    "roles": "roles",
    "products": "products",
    "skus": "skus",
    "batches": "batches",
    "warehouses": "warehouses",
    "inventory": "inventory",
    "distributors": "distributors",
    "retailers": "retailers",
    "customers": "customers",
    "customer-orders": "customer_orders",
    "primary-orders": "primary_orders",
    "secondary-orders": "secondary_orders",
    "invoices": "invoices",
    "dispatches": "dispatches",
    "grns": "grns",
    "payments": "payments",
    "ledger": "ledger",
    "expenses": "expenses",
    "cashback": "cashback",
    "coupons": "coupons",
    "approvals": "approvals",
    "notifications": "notifications",
    # Phase 3 collections (readable via generic list route)
    "returns": "returns",
    "damage": "damage",
    "claims": "claims",
    "credit-notes": "credit_notes",
    "debit-notes": "debit_notes",
    "replacements": "replacements",
    "expiry-records": "expiry_records",
    "approval-matrix": "approval_matrix",
    "approval-requests": "approval_requests",
    "exceptions": "exceptions",
    "audit-log": "audit_log",
}


@api.get("/collections/{resource}")
async def list_resource(resource: str, branch_id: Optional[str] = None, status: Optional[str] = None,
                          q: Optional[str] = None, limit: int = 500,
                          user: dict = Depends(get_current_user)):
    coll = COLLECTIONS.get(resource)
    if not coll:
        raise HTTPException(status_code=404, detail="Resource not found")
    query: Dict[str, Any] = {}
    if branch_id:
        query["branch_id"] = branch_id
    if status:
        query["status"] = status
    docs = await db[coll].find(query, {"_id": 0}).to_list(limit)
    if q:
        ql = q.lower()
        docs = [d for d in docs if any(ql in str(v).lower() for v in d.values())]
    return {"data": docs, "count": len(docs)}


@api.get("/collections/{resource}/{item_id}")
async def get_resource(resource: str, item_id: str, user: dict = Depends(get_current_user)):
    if resource not in COLLECTIONS:
        raise HTTPException(status_code=404, detail="Resource not found")
    doc = await db[COLLECTIONS[resource]].find_one({"id": item_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return doc


@api.post("/collections/{resource}")
async def create_resource(resource: str, payload: Dict[str, Any] = Body(...),
                            user: dict = Depends(require_admin_role)):
    if resource not in COLLECTIONS:
        raise HTTPException(status_code=404, detail="Resource not found")
    payload["id"] = payload.get("id") or f"{resource[:3]}-{uuid.uuid4().hex[:10]}"
    payload["created_at"] = datetime.now(timezone.utc).isoformat()
    payload["created_by"] = user.get("email")
    await db[COLLECTIONS[resource]].insert_one(payload)
    payload.pop("_id", None)
    return payload


@api.put("/collections/{resource}/{item_id}")
async def update_resource(resource: str, item_id: str, payload: Dict[str, Any] = Body(...),
                            user: dict = Depends(require_admin_role)):
    if resource not in COLLECTIONS:
        raise HTTPException(status_code=404, detail="Resource not found")
    payload.pop("_id", None)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    payload["updated_by"] = user.get("email")
    r = await db[COLLECTIONS[resource]].update_one({"id": item_id}, {"$set": payload})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db[COLLECTIONS[resource]].find_one({"id": item_id}, {"_id": 0})
    return doc


@api.delete("/collections/{resource}/{item_id}")
async def delete_resource(resource: str, item_id: str, user: dict = Depends(require_admin_role)):
    if resource not in COLLECTIONS:
        raise HTTPException(status_code=404, detail="Resource not found")
    r = await db[COLLECTIONS[resource]].delete_one({"id": item_id})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@api.get("/health")
async def health():
    """Public health check for k8s / load balancer probes."""
    try:
        await _raw_db.command("ping")
        return {"status": "ok", "db": "connected", "service": PLATFORM_NAME.lower()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"db_unavailable: {e}")


@api.get("/")
async def root():
    return {"service": PLATFORM_NAME, "status": "operational", "version": "6.0.0-saas",
             "features": ["multi-tenant", "white-label", "subscriptions", "marketplace", "api-platform"]}


# Workflow router (Phase 1 business engine)
api.include_router(build_workflow_router(db, get_current_user))
# Finance router (Phase 2 financial engine)
finance_router = build_finance_router(db, get_current_user)
api.include_router(finance_router)
# Reverse Logistics router (Phase 3: returns, claims, credit/debit notes, replacements, expiry, approvals, exceptions, audit)
reverse_router = build_reverse_router(db, get_current_user, finance_router)
api.include_router(reverse_router)
# Analytics & BI router (Phase 4: executive KPIs, trace, party360, alerts, scorecards, AI-ready)
analytics_router = build_analytics_router(db, get_current_user)
api.include_router(analytics_router)
# Exports router (Part D: CSV / Excel / PDF / Print View for every collection)
exports_router = build_exports_router(db, get_current_user)
api.include_router(exports_router)
# Notifications router (Part E: in-app + email/whatsapp/sms scaffold + preferences)
notifications_router = build_notifications_router(db, get_current_user)
api.include_router(notifications_router)
# AI Business Copilot router (Part F: emergentintegrations + business-analyst persona)
ai_copilot_router = build_ai_copilot_router(db, get_current_user, analytics_router)
api.include_router(ai_copilot_router)
# Integrations router (Part G: Razorpay/Stripe/GST/Tally/Barcode/QR/Excel-import/Webhooks — scaffold)
integrations_router = build_integrations_router(db, get_current_user)
api.include_router(integrations_router)
# Platform router (VayuERP SaaS control plane — tenants, plans, subscriptions, modules, api keys, branding, analytics)
platform_router = build_platform_router(db, get_current_user, platform_owner_guard, tenant_admin_guard)
api.include_router(platform_router)
# Simple DMS router (fresh — /api/dms/*)
dms_router = build_dms_router(db, get_current_user)
api.include_router(dms_router)


# ---------- Startup ----------
async def seed_users():
    from seed_data import TEST_USERS
    common_pw = ADMIN_PASSWORD
    for u in TEST_USERS:
        # Use raw db so users are seeded regardless of tenant context (bootstrap).
        existing = await _raw_db.users.find_one({"email": u["email"]})
        pw_hash = hash_password(common_pw)
        if not existing:
            doc = {
                "id": f"usr-{uuid.uuid4().hex[:12]}",
                "tenant_id": DEFAULT_TENANT_ID,   # all seed users belong to GO OIL tenant
                "email": u["email"], "name": u["name"], "role": u["role"],
                "branch_id": u.get("branch_id"), "title": u.get("title", ""),
                "password_hash": pw_hash,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "avatar": "".join([w[0] for w in u["name"].split()[:2]]).upper(),
            }
            await _raw_db.users.insert_one(doc)
        else:
            update: Dict[str, Any] = {}
            if not verify_password(common_pw, existing.get("password_hash", "")):
                update["password_hash"] = pw_hash
            if not existing.get("tenant_id"):
                update["tenant_id"] = DEFAULT_TENANT_ID
            if update:
                await _raw_db.users.update_one({"email": u["email"]}, {"$set": update})


async def seed_all():
    # Skip transactional collections — workflow engine will produce them.
    TRANSACTIONAL = {"primary_orders", "secondary_orders", "invoices", "dispatches", "grns", "batches", "inventory",
                     "payments", "ledger", "cashback"}
    # During bootstrap seed we set the current tenant to GO OIL so tenant_id
    # is auto-stamped by the wrapper.
    from tenancy import scope_tenant
    with scope_tenant(DEFAULT_TENANT_ID):
        for key, coll_name in COLLECTIONS.items():
            seed_key = coll_name
            if seed_key not in SEED:
                continue
            if seed_key in TRANSACTIONAL:
                continue
            count = await _raw_db[coll_name].count_documents({})
            if count == 0 and SEED[seed_key]:
                # stamp tenant_id on each doc explicitly (raw db insert)
                docs = [{**d, "tenant_id": DEFAULT_TENANT_ID} for d in SEED[seed_key]]
                await _raw_db[coll_name].insert_many(docs)
                logger.info(f"Seeded {coll_name}: {len(docs)} docs (tenant={DEFAULT_TENANT_ID})")
    await _raw_db.users.create_index("email", unique=True)
    # Phase 1 — inventory & workflow
    await db.company_inventory.create_index([("sku_id", 1), ("batch_id", 1)])
    await db.distributor_inventory.create_index([("partner_id", 1), ("sku_id", 1), ("batch_id", 1)])
    await db.retailer_inventory.create_index([("partner_id", 1), ("sku_id", 1), ("batch_id", 1)])
    await db.stock_ledger.create_index([("sku_id", 1), ("timestamp", -1)])
    await db.stock_ledger.create_index([("reference_id", 1)])
    await db.batches.create_index([("sku_id", 1)])
    await db.batches.create_index([("expires_on", 1)])
    await db.skus.create_index([("product_id", 1)])
    await db.skus.create_index([("code", 1)])
    await db.primary_orders.create_index([("status", 1), ("created_at", -1)])
    await db.primary_orders.create_index([("distributor_id", 1)])
    await db.primary_orders.create_index([("order_no", 1)])
    await db.secondary_orders.create_index([("status", 1), ("created_at", -1)])
    await db.secondary_orders.create_index([("distributor_id", 1)])
    await db.secondary_orders.create_index([("retailer_id", 1)])
    await db.customer_orders.create_index([("retailer_id", 1)])
    await db.customer_orders.create_index([("customer_id", 1)])
    await db.customer_orders.create_index([("created_at", -1)])
    await db.invoices.create_index([("invoice_no", 1)])
    await db.invoices.create_index([("party_id", 1), ("party_type", 1)])
    await db.invoices.create_index([("status", 1), ("created_at", -1)])
    await db.invoices.create_index([("primary_order_id", 1)])
    await db.dispatches.create_index([("order_id", 1)])
    await db.dispatches.create_index([("status", 1), ("created_at", -1)])
    await db.grns.create_index([("dispatch_id", 1)])
    await db.grns.create_index([("created_at", -1)])
    # Phase 2 — finance
    await db.double_ledger.create_index([("party_id", 1), ("timestamp", 1)])
    await db.double_ledger.create_index([("reference_id", 1)])
    await db.double_ledger.create_index([("account", 1), ("timestamp", 1)])
    await db.outstanding.create_index([("party_id", 1), ("party_type", 1)], unique=True)
    await db.payments.create_index([("party_id", 1), ("party_type", 1)])
    await db.payments.create_index([("reference", 1), ("party_id", 1)])
    await db.payments.create_index([("created_at", -1)])
    await db.wallets.create_index([("party_id", 1), ("party_type", 1)], unique=True)
    await db.cashback_transactions.create_index([("party_id", 1), ("created_at", -1)])
    await db.cashback_rules.create_index([("active", 1)])
    await db.coupons.create_index([("code", 1)], unique=False)
    await db.coupon_redemptions.create_index([("code", 1), ("party_id", 1)])
    await db.audit_log.create_index([("timestamp", -1)])
    await db.audit_log.create_index([("entity_id", 1)])
    await db.audit_log.create_index([("action", 1), ("timestamp", -1)])
    # Phase 3 — reverse logistics
    await db.returns.create_index([("created_at", -1)])
    await db.returns.create_index([("party_id", 1)])
    await db.returns.create_index([("status", 1)])
    await db.claims.create_index([("created_at", -1)])
    await db.claims.create_index([("status", 1)])
    await db.claims.create_index([("invoice_id", 1), ("type", 1)])
    await db.credit_notes.create_index([("created_at", -1)])
    await db.credit_notes.create_index([("party_id", 1)])
    await db.debit_notes.create_index([("created_at", -1)])
    await db.debit_notes.create_index([("party_id", 1)])
    await db.replacements.create_index([("created_at", -1)])
    await db.exceptions.create_index([("detected_at", -1)])
    await db.exceptions.create_index([("status", 1), ("kind", 1)])
    await db.approval_requests.create_index([("status", 1), ("requested_at", -1)])
    await db.approval_requests.create_index([("entity_type", 1), ("entity_id", 1)])
    await db.approval_matrix.create_index([("entity_type", 1), ("amount_min", 1)])
    # Notifications
    await db.notifications.create_index([("recipient_id", 1), ("created_at", -1)])
    await db.notifications.create_index([("created_at", -1)])
    await db.notifications.create_index([("read", 1), ("recipient_id", 1)])


@app.on_event("startup")
async def on_startup():
    logger.info(f"Starting {PLATFORM_NAME} backend (SaaS multi-tenant)...")
    try:
        env_summary = validate_env()
        logger.info(f"[env] validated. CORS mode: {'restricted' if env_summary['cors'] != '*' else 'open (dev)'}")
    except Exception as e:
        logger.error(f"[env] validation failed: {e}")
        raise

    # --- Platform bootstrap (idempotent) ---
    logger.info("[tenancy] Bootstrapping platform data (plans, modules, owner, GO OIL tenant)...")
    boot_report = await bootstrap_platform_data(_raw_db, PLATFORM_OWNER_EMAIL, PLATFORM_OWNER_PASSWORD)
    logger.info(f"[tenancy] bootstrap complete: {boot_report}")

    # --- Backfill tenant_id on any pre-existing data (migrating single-tenant → multi-tenant) ---
    migration_report = await backfill_tenant_id(_raw_db, DEFAULT_TENANT_ID, TENANT_EXEMPT_COLLECTIONS)
    if migration_report:
        logger.info(f"[tenancy] migration: stamped tenant_id={DEFAULT_TENANT_ID} on {sum(migration_report.values())} docs across {len(migration_report)} collections")
        logger.info(f"[tenancy] migration detail: {migration_report}")
    else:
        logger.info("[tenancy] migration: all docs already had tenant_id — noop")

    # --- Seed baseline data (inside GO OIL tenant scope so wrapper stamps tenant_id) ---
    if SEED_DEMO_DATA:
        await seed_all()
        logger.info("[seed] Demo business data seeded (SEED_DEMO_DATA=true)")
    else:
        logger.info("[seed] Skipping business demo data seed (SEED_DEMO_DATA=false — production-clean start)")
    await seed_users()

    # --- Tenant indexes ---
    idx = await ensure_tenant_indexes(_raw_db, TENANT_EXEMPT_COLLECTIONS)
    logger.info(f"[tenancy] tenant_id indexes ensured on {len(idx)} collections")

    # --- Simple DMS demo seed (idempotent) ---
    try:
        await seed_dms(_raw_db)
        logger.info("[dms] Simple DMS demo seed complete (tenant=%s)", DMS_TENANT_ID)
    except Exception as e:
        logger.warning(f"[dms] Seed skipped: {e}")

    # --- Business workflow seed (must run inside GO OIL tenant scope) ---
    if SEED_DEMO_DATA:
        from tenancy import scope_tenant
        with scope_tenant(DEFAULT_TENANT_ID):
            await run_seed_workflow(db)
            # Phase 2 finance auto-post
            try:
                await finance_router.autopost_existing_invoices()
            except Exception as e:
                logger.warning(f"Finance autopost skipped: {e}")
    else:
        logger.info("[seed] Skipping workflow / transactional seed (production-clean start)")

    logger.info(f"{PLATFORM_NAME} startup complete.")


@app.on_event("shutdown")
async def on_shutdown():
    client.close()


app.include_router(api)
