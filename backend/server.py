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
from seed_workflow import run_seed_workflow

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("gooil.dms")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

JWT_ALGO = "HS256"
JWT_SECRET = os.environ["JWT_SECRET"]
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@gooil.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "GoOil@2026")


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id, "email": email, "role": role,
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
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


app = FastAPI(title="GO OIL DMS API")
api = APIRouter(prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "customer"


class AiIn(BaseModel):
    prompt: str
    context: Optional[str] = None


# ---------- Auth ----------
@api.post("/auth/login")
async def login(response: Response, body: LoginIn):
    email = body.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user["id"], user["email"], user["role"])
    response.set_cookie("access_token", token, httponly=True, secure=True, samesite="none", max_age=43200, path="/")
    user.pop("password_hash", None); user.pop("_id", None)
    return {"user": user, "token": token}


@api.post("/auth/register")
async def register(response: Response, body: RegisterIn):
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    valid_roles = {r["key"] for r in SEED["roles"]}
    if body.role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role")
    user = {
        "id": f"usr-{uuid.uuid4().hex[:12]}",
        "email": email, "name": body.name, "role": body.role, "branch_id": None,
        "title": body.role.replace("_", " ").title(),
        "password_hash": hash_password(body.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "avatar": "".join([w[0] for w in body.name.split()[:2]]).upper(),
    }
    await db.users.insert_one(user)
    token = create_access_token(user["id"], user["email"], user["role"])
    response.set_cookie("access_token", token, httponly=True, secure=True, samesite="none", max_age=43200, path="/")
    user.pop("password_hash", None); user.pop("_id", None)
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
async def list_users(user: dict = Depends(get_current_user)):
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
                            user: dict = Depends(get_current_user)):
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
                            user: dict = Depends(get_current_user)):
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
async def delete_resource(resource: str, item_id: str, user: dict = Depends(get_current_user)):
    if resource not in COLLECTIONS:
        raise HTTPException(status_code=404, detail="Resource not found")
    r = await db[COLLECTIONS[resource]].delete_one({"id": item_id})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@api.get("/")
async def root():
    return {"service": "GO OIL DMS", "status": "operational", "version": "2.0.0-workflow"}


# Workflow router (Phase 1 business engine)
api.include_router(build_workflow_router(db, get_current_user))
# Finance router (Phase 2 financial engine)
finance_router = build_finance_router(db, get_current_user)
api.include_router(finance_router)


# ---------- Startup ----------
async def seed_users():
    from seed_data import TEST_USERS
    common_pw = ADMIN_PASSWORD
    for u in TEST_USERS:
        existing = await db.users.find_one({"email": u["email"]})
        pw_hash = hash_password(common_pw)
        if not existing:
            doc = {
                "id": f"usr-{uuid.uuid4().hex[:12]}",
                "email": u["email"], "name": u["name"], "role": u["role"],
                "branch_id": u.get("branch_id"), "title": u.get("title", ""),
                "password_hash": pw_hash,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "avatar": "".join([w[0] for w in u["name"].split()[:2]]).upper(),
            }
            await db.users.insert_one(doc)
        else:
            if not verify_password(common_pw, existing.get("password_hash", "")):
                await db.users.update_one({"email": u["email"]}, {"$set": {"password_hash": pw_hash}})


async def seed_all():
    # Skip transactional collections — workflow engine will produce them.
    TRANSACTIONAL = {"primary_orders", "secondary_orders", "invoices", "dispatches", "grns", "batches", "inventory",
                     "payments", "ledger", "cashback"}
    for key, coll_name in COLLECTIONS.items():
        seed_key = coll_name
        if seed_key not in SEED:
            continue
        if seed_key in TRANSACTIONAL:
            continue
        count = await db[coll_name].count_documents({})
        if count == 0 and SEED[seed_key]:
            await db[coll_name].insert_many([{**d} for d in SEED[seed_key]])
            logger.info(f"Seeded {coll_name}: {len(SEED[seed_key])} docs")
    await db.users.create_index("email", unique=True)
    await db.company_inventory.create_index([("sku_id", 1), ("batch_id", 1)])
    await db.distributor_inventory.create_index([("partner_id", 1), ("sku_id", 1), ("batch_id", 1)])
    await db.retailer_inventory.create_index([("partner_id", 1), ("sku_id", 1), ("batch_id", 1)])
    await db.stock_ledger.create_index([("sku_id", 1), ("timestamp", -1)])
    await db.double_ledger.create_index([("party_id", 1), ("timestamp", 1)])
    await db.double_ledger.create_index([("reference_id", 1)])
    await db.outstanding.create_index([("party_id", 1), ("party_type", 1)], unique=True)
    await db.wallets.create_index([("party_id", 1), ("party_type", 1)], unique=True)
    await db.audit_log.create_index([("timestamp", -1)])
    await db.coupon_redemptions.create_index([("code", 1), ("party_id", 1)])


@app.on_event("startup")
async def on_startup():
    logger.info("Starting GO OIL DMS backend...")
    await seed_all()
    await seed_users()
    await run_seed_workflow(db)
    # Phase 2 finance auto-post: ensure ledger + outstanding populated for existing invoices
    try:
        await finance_router.autopost_existing_invoices()
    except Exception as e:
        logger.warning(f"Finance autopost skipped: {e}")
    logger.info("Startup complete.")


@app.on_event("shutdown")
async def on_shutdown():
    client.close()


app.include_router(api)
