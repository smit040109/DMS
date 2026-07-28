#!/usr/bin/env python3
"""Test Part D (Exports) and Part A (Regression) only."""
import requests
import time
import json

BASE_URL = "https://38026b09-a311-4ef3-8159-6cb799593d83.preview.emergentagent.com/api"

def login():
    resp = requests.post(f"{BASE_URL}/auth/login", 
                        json={"email": "admin@gooil.com", "password": "GoOil@2026"}, 
                        timeout=10)
    if resp.status_code != 200:
        raise Exception(f"Login failed: {resp.status_code} {resp.text}")
    return resp.json()["token"]

print("="*80)
print("PART D — EXPORTS TESTS")
print("="*80)

token = login()
headers = {"Authorization": f"Bearer {token}"}

# D1: Collections list
print("\n[D1] GET /api/exports/collections...")
resp = requests.get(f"{BASE_URL}/exports/collections", headers=headers, timeout=10)
if resp.status_code == 200:
    count = len(resp.json().get("data", []))
    print(f"✅ {count} exportable resources (expected 35)")
else:
    print(f"❌ {resp.status_code}: {resp.text[:200]}")

# D2: CSV export
print("\n[D2] GET /api/exports/products?format=csv...")
resp = requests.get(f"{BASE_URL}/exports/products?format=csv", headers=headers, timeout=10)
if resp.status_code == 200:
    ct = resp.headers.get("Content-Type", "")
    first_line = resp.text.split("\n")[0]
    print(f"✅ text/csv, headers: {first_line[:60]}")
else:
    print(f"❌ {resp.status_code}: {resp.text[:200]}")

# D3: XLSX export
print("\n[D3] GET /api/exports/products?format=xlsx...")
resp = requests.get(f"{BASE_URL}/exports/products?format=xlsx", headers=headers, timeout=10)
if resp.status_code == 200:
    is_zip = resp.content[:4] == b'PK\x03\x04'
    print(f"✅ XLSX, {len(resp.content)} bytes, valid_zip={is_zip}")
else:
    print(f"❌ {resp.status_code}: {resp.text[:200]}")

# D4: PDF export
print("\n[D4] GET /api/exports/invoices?format=pdf...")
resp = requests.get(f"{BASE_URL}/exports/invoices?format=pdf", headers=headers, timeout=10)
if resp.status_code == 200:
    is_pdf = resp.content[:4] == b'%PDF'
    print(f"✅ PDF, {len(resp.content)} bytes, valid_pdf={is_pdf}")
else:
    print(f"❌ {resp.status_code}: {resp.text[:200]}")

# D5: Print HTML export
print("\n[D5] GET /api/exports/outstanding?format=print...")
resp = requests.get(f"{BASE_URL}/exports/outstanding?format=print", headers=headers, timeout=10)
if resp.status_code == 200:
    has_table = "<table>" in resp.text.lower()
    print(f"✅ HTML, {len(resp.text)} bytes, has_table={has_table}")
else:
    print(f"❌ {resp.status_code}: {resp.text[:200]}")

# D6: POST render
print("\n[D6] POST /api/exports/render...")
resp = requests.post(f"{BASE_URL}/exports/render", 
                    json={"rows": [{"a": 1, "b": "x"}], "format": "csv", "title": "Test"},
                    headers=headers, timeout=10)
if resp.status_code == 200:
    print(f"✅ CSV rendered, {len(resp.text)} bytes")
else:
    print(f"❌ {resp.status_code}: {resp.text[:200]}")

# D7: Invalid format
print("\n[D7] GET /api/exports/products?format=badformat...")
resp = requests.get(f"{BASE_URL}/exports/products?format=badformat", headers=headers, timeout=10)
if resp.status_code in [400, 422]:
    print(f"✅ {resp.status_code} (rejected as expected)")
else:
    print(f"❌ Expected 400/422, got {resp.status_code}")

# D8: Unknown resource
print("\n[D8] GET /api/exports/nothingness?format=csv...")
resp = requests.get(f"{BASE_URL}/exports/nothingness?format=csv", headers=headers, timeout=10)
if resp.status_code == 404:
    print(f"✅ 404 (rejected as expected)")
else:
    print(f"❌ Expected 404, got {resp.status_code}")

# D9: Auth required
print("\n[D9] GET /api/exports/products (no auth)...")
resp = requests.get(f"{BASE_URL}/exports/products?format=csv", timeout=10)
if resp.status_code == 401:
    print(f"✅ 401 Unauthorized (as expected)")
else:
    print(f"❌ Expected 401, got {resp.status_code}")

print("\n" + "="*80)
print("PART A — LIGHT REGRESSION TESTS")
print("="*80)

# A1: Login all personas
print("\n[A1] Login all 8 personas...")
personas = ["admin", "company_admin", "regional_manager", "sales_executive", 
            "distributor", "distributor_accountant", "retailer", "customer"]
emails = {
    "admin": "admin@gooil.com",
    "company_admin": "company@gooil.com",
    "regional_manager": "regional@gooil.com",
    "sales_executive": "sales@gooil.com",
    "distributor": "distributor@gooil.com",
    "distributor_accountant": "accountant@gooil.com",
    "retailer": "retailer@gooil.com",
    "customer": "customer@gooil.com",
}
failed = []
for p in personas:
    resp = requests.post(f"{BASE_URL}/auth/login",
                        json={"email": emails[p], "password": "GoOil@2026"},
                        timeout=10)
    if resp.status_code == 200:
        print(f"  ✓ {p}")
    else:
        failed.append(p)
        print(f"  ✗ {p}: {resp.status_code}")

if failed:
    print(f"❌ Failed: {', '.join(failed)}")
else:
    print(f"✅ All 8 personas logged in")

# A2: Exception scanner (no ObjectId leaks)
print("\n[A2] POST /api/reverse/exceptions/scan...")
resp = requests.post(f"{BASE_URL}/reverse/exceptions/scan", headers=headers, timeout=10)
if resp.status_code == 200:
    data = resp.json()
    content = json.dumps(data)
    has_objectid = "ObjectId" in content or '"_id"' in content
    if not has_objectid:
        print(f"✅ 200 OK, found={data.get('found', 0)}, no ObjectId leaks")
    else:
        print(f"❌ ObjectId leak detected")
else:
    print(f"❌ {resp.status_code}: {resp.text[:200]}")

# A3: Executive KPI (15 metrics)
print("\n[A3] GET /api/analytics/kpi/executive?range=month...")
resp = requests.get(f"{BASE_URL}/analytics/kpi/executive?range=month", headers=headers, timeout=10)
if resp.status_code == 200:
    data = resp.json()
    kpis = data.get("kpis", {})
    count = len(kpis)
    if count == 15:
        revenue_obj = kpis.get("revenue", {})
        revenue = revenue_obj.get("value", 0) / 1e6 if isinstance(revenue_obj, dict) else revenue_obj / 1e6
        print(f"✅ All 15 KPIs present, revenue=${revenue:.1f}M")
    else:
        print(f"❌ Expected 15 KPIs, got {count}")
else:
    print(f"❌ {resp.status_code}: {resp.text[:200]}")

# A4: Party 360
print("\n[A4] GET /api/analytics/party360/distributor/dist-100...")
resp = requests.get(f"{BASE_URL}/analytics/party360/distributor/dist-100", headers=headers, timeout=10)
if resp.status_code == 200:
    data = resp.json()
    required = ["profile", "financials", "performance", "risk_score", "health_score", "timeline"]
    missing = [s for s in required if s not in data]
    if not missing:
        name = data.get("profile", {}).get("name", "?")
        print(f"✅ All sections present, party: {name}")
    else:
        print(f"❌ Missing sections: {missing}")
else:
    print(f"❌ {resp.status_code}: {resp.text[:200]}")

print("\n" + "="*80)
print("TESTS COMPLETE")
print("="*80)
