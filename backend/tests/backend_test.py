"""GO OIL DMS — Backend API tests."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phase2c-qa.preview.emergentagent.com").rstrip("/")
# fallback to frontend env
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

API = f"{BASE_URL}/api"
COMMON_PW = "GoOil@2026"

ROLE_EMAILS = {
    "super_admin": "admin@gooil.com",
    "company_admin": "company@gooil.com",
    "regional_manager": "regional@gooil.com",
    "sales_executive": "sales@gooil.com",
    "distributor": "distributor@gooil.com",
    "distributor_accountant": "accountant@gooil.com",
    "retailer": "retailer@gooil.com",
    "customer": "customer@gooil.com",
}

COLLECTIONS = [
    "branches", "roles", "products", "skus", "batches", "warehouses", "inventory",
    "distributors", "retailers", "customers", "primary-orders", "secondary-orders",
    "invoices", "dispatches", "grns", "payments", "ledger", "expenses", "cashback",
    "coupons", "approvals", "notifications",
]


def _login(email, password=COMMON_PW):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    return r


@pytest.fixture(scope="session")
def company_token():
    r = _login("company@gooil.com")
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def auth_headers(company_token):
    return {"Authorization": f"Bearer {company_token}"}


# ---------- Health ----------
def test_root_health():
    r = requests.get(f"{API}/", timeout=15)
    assert r.status_code == 200
    j = r.json()
    assert j.get("service") == "GO OIL DMS"
    assert j.get("status") == "operational"


# ---------- Auth ----------
def test_login_company_admin_returns_token_and_cookie():
    r = _login("company@gooil.com")
    assert r.status_code == 200, r.text
    j = r.json()
    assert "token" in j and isinstance(j["token"], str) and len(j["token"]) > 20
    assert j["user"]["email"] == "company@gooil.com"
    assert j["user"]["role"] == "company_admin"
    assert "password_hash" not in j["user"]
    # cookie
    assert "access_token" in r.cookies


def test_login_invalid_credentials():
    r = requests.post(f"{API}/auth/login", json={"email": "company@gooil.com", "password": "wrong"}, timeout=15)
    assert r.status_code == 401


def test_auth_me_returns_same_user(company_token):
    r = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {company_token}"}, timeout=15)
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "company@gooil.com"


def test_auth_roles_returns_eight():
    r = requests.get(f"{API}/auth/roles", timeout=15)
    assert r.status_code == 200
    roles = r.json()["roles"]
    assert len(roles) == 8
    keys = {x["key"] for x in roles}
    assert "super_admin" in keys and "customer" in keys


def test_register_new_and_duplicate():
    email = f"test_{int(time.time())}@gooil.com"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": "TestPass@123", "name": "Test User", "role": "customer"
    }, timeout=15)
    assert r.status_code == 200, r.text
    j = r.json()
    assert "token" in j
    assert j["user"]["email"] == email

    # duplicate
    r2 = requests.post(f"{API}/auth/register", json={
        "email": email, "password": "TestPass@123", "name": "Dup", "role": "customer"
    }, timeout=15)
    assert r2.status_code == 400


def test_register_invalid_role():
    email = f"test_bad_{int(time.time())}@gooil.com"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": "TestPass@123", "name": "Bad Role", "role": "not_a_role"
    }, timeout=15)
    assert r.status_code == 400


def test_logout_clears_cookie():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "company@gooil.com", "password": COMMON_PW}, timeout=15)
    assert r.status_code == 200
    r2 = s.post(f"{API}/auth/logout", timeout=15)
    assert r2.status_code == 200
    # cookie should be cleared - either empty or deleted
    cookie_val = s.cookies.get("access_token")
    assert not cookie_val


def test_unauth_protected_endpoint_401():
    r = requests.get(f"{API}/dashboard/kpis", timeout=15)
    assert r.status_code == 401


def test_all_eight_seeded_users_can_login():
    for role, email in ROLE_EMAILS.items():
        r = _login(email)
        assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
        assert r.json()["user"]["role"] == role


# ---------- Dashboard ----------
def test_dashboard_kpis_role_variance():
    labels_by_role = {}
    for role, email in ROLE_EMAILS.items():
        tok = _login(email).json()["token"]
        r = requests.get(f"{API}/dashboard/kpis", headers={"Authorization": f"Bearer {tok}"}, timeout=15)
        assert r.status_code == 200, f"{role}: {r.text}"
        kpis = r.json()["kpis"]
        assert len(kpis) == 5, f"{role} did not return 5 kpis"
        labels_by_role[role] = tuple(k["label"] for k in kpis)
    # Ensure they differ by role - at least super_admin, distributor, retailer, customer distinct
    distinct = set(labels_by_role.values())
    assert len(distinct) >= 6, f"KPI labels don't vary enough by role: {labels_by_role}"


def test_dashboard_analytics(auth_headers):
    r = requests.get(f"{API}/dashboard/analytics", headers=auth_headers, timeout=15)
    assert r.status_code == 200
    j = r.json()
    for key in ["primary_trend", "orders_by_status", "top_skus", "branch_health"]:
        assert key in j, f"missing {key}"


def test_dashboard_activity_and_tasks(auth_headers):
    r = requests.get(f"{API}/dashboard/activity", headers=auth_headers, timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json()["activity"], list)
    r2 = requests.get(f"{API}/dashboard/tasks", headers=auth_headers, timeout=15)
    assert r2.status_code == 200
    assert isinstance(r2.json()["tasks"], list)


def test_master_data(auth_headers):
    r = requests.get(f"{API}/master-data", headers=auth_headers, timeout=15)
    assert r.status_code == 200
    j = r.json()
    for key in ["tax_rates", "uoms", "payment_terms", "regions"]:
        assert key in j and len(j[key]) > 0, f"master-data missing/empty {key}"


def test_admin_users(auth_headers):
    r = requests.get(f"{API}/admin/users", headers=auth_headers, timeout=15)
    assert r.status_code == 200
    j = r.json()
    assert j["count"] >= 8
    for u in j["data"]:
        assert "password_hash" not in u


# ---------- Collections ----------
@pytest.mark.parametrize("resource", COLLECTIONS)
def test_collection_list_populated(resource, auth_headers):
    r = requests.get(f"{API}/collections/{resource}", headers=auth_headers, timeout=20)
    assert r.status_code == 200, f"{resource}: {r.status_code} {r.text}"
    j = r.json()
    assert "data" in j and isinstance(j["data"], list)
    assert j["count"] > 0, f"{resource} is empty (seed failure?)"


def test_collection_nonexistent_returns_404(auth_headers):
    r = requests.get(f"{API}/collections/nonexistent", headers=auth_headers, timeout=15)
    assert r.status_code == 404


def test_products_crud(auth_headers):
    # CREATE
    payload = {"name": "TEST_Product_X", "sku_count": 1, "brand": "GO OIL", "status": "Active"}
    r = requests.post(f"{API}/collections/products", headers=auth_headers, json=payload, timeout=15)
    assert r.status_code == 200, r.text
    created = r.json()
    pid = created["id"]
    assert created["name"] == "TEST_Product_X"

    # GET
    r = requests.get(f"{API}/collections/products/{pid}", headers=auth_headers, timeout=15)
    assert r.status_code == 200
    assert r.json()["name"] == "TEST_Product_X"

    # UPDATE
    r = requests.put(f"{API}/collections/products/{pid}", headers=auth_headers, json={"name": "TEST_Product_X_Updated"}, timeout=15)
    assert r.status_code == 200
    assert r.json()["name"] == "TEST_Product_X_Updated"

    # GET verify
    r = requests.get(f"{API}/collections/products/{pid}", headers=auth_headers, timeout=15)
    assert r.json()["name"] == "TEST_Product_X_Updated"

    # DELETE
    r = requests.delete(f"{API}/collections/products/{pid}", headers=auth_headers, timeout=15)
    assert r.status_code == 200

    # GET 404
    r = requests.get(f"{API}/collections/products/{pid}", headers=auth_headers, timeout=15)
    assert r.status_code == 404


# ---------- AI ----------
def test_ai_ask_returns_reply(auth_headers):
    r = requests.post(f"{API}/ai/ask", headers=auth_headers,
                      json={"prompt": "Give one short bullet with total product count."},
                      timeout=60)
    assert r.status_code == 200, r.text
    j = r.json()
    assert "reply" in j
    reply = j["reply"]
    # reply may be str or dict
    if isinstance(reply, dict):
        reply_text = str(reply)
    else:
        reply_text = reply
    assert reply_text and len(reply_text) > 5
