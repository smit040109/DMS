#!/usr/bin/env python3
"""
GO OIL DMS — Backend API Testing for NEW endpoints (CONTINUATION v3)

Tests:
1. SMART PRICE-LIST IMPORT
   - GET /api/dms/owner/products/import-template
   - POST /api/dms/owner/products/import-circular
2. COUPON SCANNING + AUDIT
   - GET /api/dms/coupons/scan-permission
   - PUT /api/dms/coupons/scan-permission
   - GET /api/dms/coupons/distributor/wallet
   - POST /api/dms/coupons/distributor/scan
   - GET /api/dms/coupons/audit
3. DELETE ENDPOINTS
   - DELETE /api/dms/distributors/{did}
   - DELETE /api/dms/retailers/{rid}
   - DELETE /api/dms/owner/users/{uid}
4. HIERARCHY
   - GET /api/dms/owner/hierarchy
"""

import requests
import sys
import io
from openpyxl import Workbook

# Base URL from frontend/.env
BASE_URL = "https://2025d85f-a2d8-4129-a13b-26acc1a60644.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

# Test credentials from test_credentials.md
CREDENTIALS = {
    "owner": {"email": "owner@gooil.com", "password": "GoOil@2026"},
    "distributor1": {"email": "distributor1@gooil.com", "password": "GoOil@2026"},
    "retailer1": {"email": "retailer1@gooil.com", "password": "GoOil@2026"},
    "salesperson": {"email": "salesperson@gooil.com", "password": "GoOil@2026"},
}

def login(email, password):
    """Login and return JWT token"""
    resp = requests.post(f"{API_BASE}/auth/login", json={"email": email, "password": password})
    if resp.status_code != 200:
        print(f"❌ Login failed for {email}: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    return data.get("token")

def headers(token):
    """Return authorization headers"""
    return {"Authorization": f"Bearer {token}"}

def build_test_xlsx():
    """Build a small test xlsx file with GO OIL price list format"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Price List"
    
    # Header row
    headers = ["MATERIAL DESCRIPTION", "GRADE/ SPECS", "PACK SIZE", "MRP", "DLP",
               "DISTRIBUTOR MARGINE", "CASH COUPON", "FOC BENEFITS", "MONTHLY GIFT", "TRADE DISCOUNT"]
    ws.append(headers)
    
    # Category row (full-width)
    ws.append(["TEST CATEGORY A"])
    
    # Product rows
    ws.append(["PROD ONE", "SN", "1 ltr", 500, 350, "9%", "10", "", "AVAILABLE", ""])
    ws.append(["PROD TWO", "SN", "2 ltr", 800, 600, "9%", "20", "", "AVAILABLE", ""])
    
    # Another category
    ws.append(["TEST CATEGORY B"])
    ws.append(["PROD THREE", "GL5", "500 ml", 300, 200, "9%", "", "FOC 9+1", "", ""])
    
    # Save to bytes
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()

def test_price_import():
    """Test SMART PRICE-LIST IMPORT endpoints"""
    print("\n" + "="*80)
    print("TEST 1: SMART PRICE-LIST IMPORT")
    print("="*80)
    
    owner_token = login(**CREDENTIALS["owner"])
    dist1_token = login(**CREDENTIALS["distributor1"])
    
    if not owner_token or not dist1_token:
        print("❌ Failed to login")
        return False
    
    # Test 1a: GET import-template as owner → 200, xlsx file
    print("\n1a. GET /api/dms/owner/products/import-template as owner")
    resp = requests.get(f"{API_BASE}/dms/owner/products/import-template", headers=headers(owner_token))
    if resp.status_code == 200 and "spreadsheet" in resp.headers.get("content-type", ""):
        print(f"✅ Owner: 200, content-type={resp.headers.get('content-type')}, size={len(resp.content)} bytes")
    else:
        print(f"❌ Owner: {resp.status_code}, content-type={resp.headers.get('content-type')}")
        return False
    
    # Test 1b: GET import-template as distributor1 → 403
    print("\n1b. GET /api/dms/owner/products/import-template as distributor1 → 403")
    resp = requests.get(f"{API_BASE}/dms/owner/products/import-template", headers=headers(dist1_token))
    if resp.status_code == 403:
        print(f"✅ Distributor1: 403 (correct RBAC)")
    else:
        print(f"❌ Distributor1: {resp.status_code} (expected 403)")
        return False
    
    # Test 1c: POST import-circular as owner with test file
    print("\n1c. POST /api/dms/owner/products/import-circular as owner (first import)")
    xlsx_data = build_test_xlsx()
    files = {"file": ("test_price_list.xlsx", xlsx_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    resp = requests.post(f"{API_BASE}/dms/owner/products/import-circular", 
                        headers=headers(owner_token), files=files)
    if resp.status_code == 200:
        data = resp.json()
        # Accept either created=3 (first run) or updated=3 (subsequent runs - idempotent)
        if data.get("ok") and (data.get("created") == 3 or data.get("updated") == 3) and data.get("categories") == 2:
            print(f"✅ Owner: 200, created={data.get('created')}, updated={data.get('updated')}, categories={data.get('categories')}, circular_batch_no={data.get('circular_batch_no')}")
            circular_batch_no = data.get("circular_batch_no")
        else:
            print(f"❌ Owner: 200 but unexpected data: {data}")
            return False
    else:
        print(f"❌ Owner: {resp.status_code} {resp.text}")
        return False
    
    # Test 1d: POST same file again → idempotent (created=0, updated=3)
    print("\n1d. POST /api/dms/owner/products/import-circular as owner (re-import same file)")
    files = {"file": ("test_price_list.xlsx", build_test_xlsx(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    resp = requests.post(f"{API_BASE}/dms/owner/products/import-circular", 
                        headers=headers(owner_token), files=files)
    if resp.status_code == 200:
        data = resp.json()
        if data.get("ok") and data.get("created") == 0 and data.get("updated") == 3:
            print(f"✅ Owner: 200, created=0, updated=3 (idempotent)")
        else:
            print(f"⚠️  Owner: 200 but unexpected data: created={data.get('created')}, updated={data.get('updated')}")
    else:
        print(f"❌ Owner: {resp.status_code} {resp.text}")
        return False
    
    # Test 1e: POST as distributor1 → 403
    print("\n1e. POST /api/dms/owner/products/import-circular as distributor1 → 403")
    files = {"file": ("test.xlsx", build_test_xlsx(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    resp = requests.post(f"{API_BASE}/dms/owner/products/import-circular", 
                        headers=headers(dist1_token), files=files)
    if resp.status_code == 403:
        print(f"✅ Distributor1: 403 (correct RBAC)")
    else:
        print(f"❌ Distributor1: {resp.status_code} (expected 403)")
        return False
    
    # Test 1f: Verify products exist
    print("\n1f. GET /api/dms/products as owner → verify imported products")
    resp = requests.get(f"{API_BASE}/dms/products", headers=headers(owner_token))
    if resp.status_code == 200:
        data = resp.json()
        products = data.get("data", [])
        imported = [p for p in products if "PROD ONE" in p.get("material_description", "") or 
                   "PROD TWO" in p.get("material_description", "") or 
                   "PROD THREE" in p.get("material_description", "")]
        if len(imported) >= 3:
            print(f"✅ Owner: 200, found {len(imported)} imported products with material_description/grade_specs/pack_size")
        else:
            print(f"⚠️  Owner: 200 but only found {len(imported)} imported products (expected 3)")
    else:
        print(f"❌ Owner: {resp.status_code}")
        return False
    
    # Test 1g: Verify price-circulars
    print("\n1g. GET /api/dms/price-circulars as owner → verify new circular")
    resp = requests.get(f"{API_BASE}/dms/price-circulars", headers=headers(owner_token))
    if resp.status_code == 200:
        data = resp.json()
        circulars = data.get("data", [])
        if len(circulars) > 0:
            print(f"✅ Owner: 200, {len(circulars)} circulars exist")
        else:
            print(f"⚠️  Owner: 200 but no circulars found")
    else:
        print(f"❌ Owner: {resp.status_code}")
        return False
    
    return True

def test_coupon_scanning():
    """Test COUPON SCANNING + AUDIT endpoints"""
    print("\n" + "="*80)
    print("TEST 2: COUPON SCANNING + AUDIT")
    print("="*80)
    
    owner_token = login(**CREDENTIALS["owner"])
    dist1_token = login(**CREDENTIALS["distributor1"])
    
    if not owner_token or not dist1_token:
        print("❌ Failed to login")
        return False
    
    # Test 2a: GET scan-permission as owner
    print("\n2a. GET /api/dms/coupons/scan-permission as owner")
    resp = requests.get(f"{API_BASE}/dms/coupons/scan-permission", headers=headers(owner_token))
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Owner: 200, retailer_scan_enabled={data.get('retailer_scan_enabled')}")
    else:
        print(f"❌ Owner: {resp.status_code}")
        return False
    
    # Test 2b: PUT scan-permission as owner
    print("\n2b. PUT /api/dms/coupons/scan-permission as owner (enable)")
    resp = requests.put(f"{API_BASE}/dms/coupons/scan-permission", 
                       headers=headers(owner_token), json={"enabled": True})
    if resp.status_code == 200:
        data = resp.json()
        if data.get("ok"):
            print(f"✅ Owner: 200, ok=true")
        else:
            print(f"❌ Owner: 200 but ok=false")
            return False
    else:
        print(f"❌ Owner: {resp.status_code}")
        return False
    
    # Test 2c: PUT scan-permission as distributor1 → 403
    print("\n2c. PUT /api/dms/coupons/scan-permission as distributor1 → 403")
    resp = requests.put(f"{API_BASE}/dms/coupons/scan-permission", 
                       headers=headers(dist1_token), json={"enabled": False})
    if resp.status_code == 403:
        print(f"✅ Distributor1: 403 (correct RBAC)")
    else:
        print(f"❌ Distributor1: {resp.status_code} (expected 403)")
        return False
    
    # Test 2d: GET distributor/wallet as distributor1
    print("\n2d. GET /api/dms/coupons/distributor/wallet as distributor1")
    resp = requests.get(f"{API_BASE}/dms/coupons/distributor/wallet", headers=headers(dist1_token))
    if resp.status_code == 200:
        data = resp.json()
        if "cash_wallet" in data and "reward_wallet" in data:
            print(f"✅ Distributor1: 200, cash_wallet={data.get('cash_wallet')}, reward_wallet={data.get('reward_wallet')}")
        else:
            print(f"❌ Distributor1: 200 but missing wallet fields: {data}")
            return False
    else:
        print(f"❌ Distributor1: {resp.status_code}")
        return False
    
    # Test 2e: GET distributor/wallet as owner (should work or return empty)
    print("\n2e. GET /api/dms/coupons/distributor/wallet as owner")
    resp = requests.get(f"{API_BASE}/dms/coupons/distributor/wallet", headers=headers(owner_token))
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Owner: 200, {data}")
    else:
        print(f"⚠️  Owner: {resp.status_code} (may be expected if owner has no distributor profile)")
    
    # Test 2f: POST distributor/scan with bogus coupon → 400
    print("\n2f. POST /api/dms/coupons/distributor/scan as distributor1 with bogus coupon → 400")
    resp = requests.post(f"{API_BASE}/dms/coupons/distributor/scan", 
                        headers=headers(dist1_token), 
                        json={"coupon_code": "BOGUS123"})
    if resp.status_code == 400:
        print(f"✅ Distributor1: 400 (rejected, not 500)")
    else:
        print(f"❌ Distributor1: {resp.status_code} (expected 400)")
        return False
    
    # Test 2g: POST distributor/scan as owner (non-distributor) → 403
    print("\n2g. POST /api/dms/coupons/distributor/scan as owner → 403")
    resp = requests.post(f"{API_BASE}/dms/coupons/distributor/scan", 
                        headers=headers(owner_token), 
                        json={"coupon_code": "TEST123"})
    if resp.status_code == 403:
        print(f"✅ Owner: 403 (correct RBAC)")
    else:
        print(f"❌ Owner: {resp.status_code} (expected 403)")
        return False
    
    # Test 2h: GET audit as owner
    print("\n2h. GET /api/dms/coupons/audit as owner")
    resp = requests.get(f"{API_BASE}/dms/coupons/audit", headers=headers(owner_token))
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Owner: 200, data={data.get('data', [])}, count={data.get('count')}")
    else:
        print(f"❌ Owner: {resp.status_code}")
        return False
    
    # Test 2i: GET audit as distributor1 → 403
    print("\n2i. GET /api/dms/coupons/audit as distributor1 → 403")
    resp = requests.get(f"{API_BASE}/dms/coupons/audit", headers=headers(dist1_token))
    if resp.status_code == 403:
        print(f"✅ Distributor1: 403 (correct RBAC)")
    else:
        print(f"❌ Distributor1: {resp.status_code} (expected 403)")
        return False
    
    # Test 2j: GET audit with channel filter
    print("\n2j. GET /api/dms/coupons/audit?channel=distributor_self_scan as owner")
    resp = requests.get(f"{API_BASE}/dms/coupons/audit?channel=distributor_self_scan", headers=headers(owner_token))
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Owner: 200, filtered data count={data.get('count')}")
    else:
        print(f"❌ Owner: {resp.status_code}")
        return False
    
    return True

def test_delete_endpoints():
    """Test DELETE endpoints with RBAC + guards"""
    print("\n" + "="*80)
    print("TEST 3: DELETE ENDPOINTS")
    print("="*80)
    
    owner_token = login(**CREDENTIALS["owner"])
    dist1_token = login(**CREDENTIALS["distributor1"])
    retailer1_token = login(**CREDENTIALS["retailer1"])
    
    if not owner_token or not dist1_token or not retailer1_token:
        print("❌ Failed to login")
        return False
    
    # Test 3a: Create throwaway distributor
    print("\n3a. POST /api/dms/distributors as owner (create throwaway)")
    resp = requests.post(f"{API_BASE}/dms/distributors", 
                        headers=headers(owner_token),
                        json={
                            "name": "ZZ Test Dist",
                            "email": "zztestdist@gooil.com",
                            "password": "GoOil@2026",
                            "phone": "9999999999",
                            "address": "Test Address",
                            "region": "X"
                        })
    if resp.status_code == 200:
        data = resp.json()
        throwaway_dist_id = data.get("id")
        print(f"✅ Owner: 200, created distributor id={throwaway_dist_id}")
    else:
        print(f"❌ Owner: {resp.status_code} {resp.text}")
        return False
    
    # Test 3b: DELETE distributor as owner → ok
    print(f"\n3b. DELETE /api/dms/distributors/{throwaway_dist_id} as owner")
    resp = requests.delete(f"{API_BASE}/dms/distributors/{throwaway_dist_id}", headers=headers(owner_token))
    if resp.status_code == 200:
        data = resp.json()
        if data.get("ok"):
            print(f"✅ Owner: 200, ok=true")
        else:
            print(f"❌ Owner: 200 but ok=false")
            return False
    else:
        print(f"❌ Owner: {resp.status_code} {resp.text}")
        return False
    
    # Test 3c: DELETE same distributor again → 404
    print(f"\n3c. DELETE /api/dms/distributors/{throwaway_dist_id} again → 404")
    resp = requests.delete(f"{API_BASE}/dms/distributors/{throwaway_dist_id}", headers=headers(owner_token))
    if resp.status_code == 404:
        print(f"✅ Owner: 404 (correct)")
    else:
        print(f"❌ Owner: {resp.status_code} (expected 404)")
        return False
    
    # Test 3d: DELETE distributor as distributor1 → 403
    print("\n3d. Create another throwaway distributor and try DELETE as distributor1 → 403")
    resp = requests.post(f"{API_BASE}/dms/distributors", 
                        headers=headers(owner_token),
                        json={
                            "name": "ZZ Test Dist 2",
                            "email": "zztestdist2@gooil.com",
                            "password": "GoOil@2026",
                            "phone": "8888888888",
                            "address": "Test Address 2",
                            "region": "Y"
                        })
    if resp.status_code == 200:
        throwaway_dist_id2 = resp.json().get("id")
        resp = requests.delete(f"{API_BASE}/dms/distributors/{throwaway_dist_id2}", headers=headers(dist1_token))
        if resp.status_code == 403:
            print(f"✅ Distributor1: 403 (correct RBAC)")
            # Clean up
            requests.delete(f"{API_BASE}/dms/distributors/{throwaway_dist_id2}", headers=headers(owner_token))
        else:
            print(f"❌ Distributor1: {resp.status_code} (expected 403)")
            return False
    else:
        print(f"⚠️  Could not create second throwaway distributor")
    
    # Test 3e: Create throwaway retailer
    print("\n3e. POST /api/dms/retailers as owner (create throwaway)")
    resp = requests.post(f"{API_BASE}/dms/retailers", 
                        headers=headers(owner_token),
                        json={
                            "name": "ZZ Test Retailer",
                            "email": "zztestretailer@gooil.com",
                            "password": "GoOil@2026",
                            "phone": "7777777777",
                            "address": "Test Retailer Address",
                            "distributor_id": "dist-existing"  # Use existing distributor
                        })
    if resp.status_code == 200:
        data = resp.json()
        throwaway_ret_id = data.get("id")
        print(f"✅ Owner: 200, created retailer id={throwaway_ret_id}")
    else:
        # Try with distributor1 token
        resp = requests.post(f"{API_BASE}/dms/retailers", 
                            headers=headers(dist1_token),
                            json={
                                "name": "ZZ Test Retailer",
                                "phone": "7777777777",
                                "address": "Test Retailer Address"
                            })
        if resp.status_code == 200:
            throwaway_ret_id = resp.json().get("id")
            print(f"✅ Distributor1: 200, created retailer id={throwaway_ret_id}")
        else:
            print(f"⚠️  Could not create throwaway retailer: {resp.status_code}")
            throwaway_ret_id = None
    
    # Test 3f: DELETE retailer as owner → ok
    if throwaway_ret_id:
        print(f"\n3f. DELETE /api/dms/retailers/{throwaway_ret_id} as owner")
        resp = requests.delete(f"{API_BASE}/dms/retailers/{throwaway_ret_id}", headers=headers(owner_token))
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                print(f"✅ Owner: 200, ok=true")
            else:
                print(f"❌ Owner: 200 but ok=false")
                return False
        else:
            print(f"❌ Owner: {resp.status_code} {resp.text}")
            return False
    
    # Test 3g: Create throwaway user (or use existing if already created)
    print("\n3g. POST /api/dms/owner/users as owner (create throwaway)")
    resp = requests.post(f"{API_BASE}/dms/owner/users", 
                        headers=headers(owner_token),
                        json={
                            "email": "zztestuser@gooil.com",
                            "password": "GoOil@2026",
                            "name": "ZZ User",
                            "role": "salesperson"
                        })
    if resp.status_code == 200:
        data = resp.json()
        user_obj = data.get("user", {})
        throwaway_user_id = user_obj.get("id")
        print(f"✅ Owner: 200, created user id={throwaway_user_id}")
    elif resp.status_code == 400 and "already exists" in resp.text:
        # User already exists from previous test run - find it
        print(f"⚠️  User already exists, finding existing user...")
        resp = requests.get(f"{API_BASE}/dms/owner/users", headers=headers(owner_token))
        if resp.status_code == 200:
            users = resp.json().get("data", [])
            existing = [u for u in users if u.get("email") == "zztestuser@gooil.com"]
            if existing:
                throwaway_user_id = existing[0].get("id")
                print(f"✅ Owner: Found existing user id={throwaway_user_id}")
            else:
                print(f"❌ Could not find existing user")
                return False
        else:
            print(f"❌ Could not list users: {resp.status_code}")
            return False
    else:
        print(f"❌ Owner: {resp.status_code} {resp.text}")
        return False
    
    # Test 3h: DELETE user as owner → ok
    print(f"\n3h. DELETE /api/dms/owner/users/{throwaway_user_id} as owner")
    resp = requests.delete(f"{API_BASE}/dms/owner/users/{throwaway_user_id}", headers=headers(owner_token))
    if resp.status_code == 200:
        data = resp.json()
        if data.get("ok"):
            print(f"✅ Owner: 200, ok=true")
        else:
            print(f"❌ Owner: 200 but ok=false")
            return False
    else:
        print(f"❌ Owner: {resp.status_code} {resp.text}")
        return False
    
    # Test 3i: Try DELETE own owner id → 400
    print("\n3i. Try DELETE own owner id → 400")
    # Get owner user id
    resp = requests.get(f"{API_BASE}/dms/me", headers=headers(owner_token))
    if resp.status_code == 200:
        owner_user_id = resp.json().get("id")
        resp = requests.delete(f"{API_BASE}/dms/owner/users/{owner_user_id}", headers=headers(owner_token))
        if resp.status_code == 400:
            print(f"✅ Owner: 400 (cannot delete self)")
        else:
            print(f"❌ Owner: {resp.status_code} (expected 400)")
            return False
    else:
        print(f"⚠️  Could not get owner user id")
    
    # Test 3j: DELETE user as distributor1 → 403
    print("\n3j. Create another throwaway user and try DELETE as distributor1 → 403")
    resp = requests.post(f"{API_BASE}/dms/owner/users", 
                        headers=headers(owner_token),
                        json={
                            "email": "zztestuser2@gooil.com",
                            "password": "GoOil@2026",
                            "name": "ZZ User 2",
                            "role": "salesperson"
                        })
    if resp.status_code == 200:
        user_obj = resp.json().get("user", {})
        throwaway_user_id2 = user_obj.get("id")
        resp = requests.delete(f"{API_BASE}/dms/owner/users/{throwaway_user_id2}", headers=headers(dist1_token))
        if resp.status_code == 403:
            print(f"✅ Distributor1: 403 (correct RBAC)")
            # Clean up
            requests.delete(f"{API_BASE}/dms/owner/users/{throwaway_user_id2}", headers=headers(owner_token))
        else:
            print(f"❌ Distributor1: {resp.status_code} (expected 403)")
            return False
    else:
        print(f"⚠️  Could not create second throwaway user")
    
    return True

def test_hierarchy():
    """Test HIERARCHY endpoint"""
    print("\n" + "="*80)
    print("TEST 4: HIERARCHY")
    print("="*80)
    
    owner_token = login(**CREDENTIALS["owner"])
    dist1_token = login(**CREDENTIALS["distributor1"])
    
    if not owner_token or not dist1_token:
        print("❌ Failed to login")
        return False
    
    # Test 4a: GET hierarchy as owner
    print("\n4a. GET /api/dms/owner/hierarchy as owner")
    resp = requests.get(f"{API_BASE}/dms/owner/hierarchy", headers=headers(owner_token))
    if resp.status_code == 200:
        data = resp.json()
        required_keys = ["tree", "unassigned_team_leaders", "unassigned_distributors", "all"]
        if all(k in data for k in required_keys):
            all_data = data.get("all", {})
            all_keys = ["regional_managers", "team_leaders", "salespersons", "distributors"]
            if all(k in all_data for k in all_keys):
                print(f"✅ Owner: 200, all required keys present")
                print(f"   tree: {len(data.get('tree', []))} regional managers")
                print(f"   unassigned_team_leaders: {len(data.get('unassigned_team_leaders', []))}")
                print(f"   unassigned_distributors: {len(data.get('unassigned_distributors', []))}")
                print(f"   all.regional_managers: {len(all_data.get('regional_managers', []))}")
                print(f"   all.team_leaders: {len(all_data.get('team_leaders', []))}")
                print(f"   all.salespersons: {len(all_data.get('salespersons', []))}")
                print(f"   all.distributors: {len(all_data.get('distributors', []))}")
            else:
                print(f"❌ Owner: 200 but missing keys in 'all': {all_data.keys()}")
                return False
        else:
            print(f"❌ Owner: 200 but missing required keys: {data.keys()}")
            return False
    else:
        print(f"❌ Owner: {resp.status_code}")
        return False
    
    # Test 4b: GET hierarchy as distributor1 → 403
    print("\n4b. GET /api/dms/owner/hierarchy as distributor1 → 403")
    resp = requests.get(f"{API_BASE}/dms/owner/hierarchy", headers=headers(dist1_token))
    if resp.status_code == 403:
        print(f"✅ Distributor1: 403 (correct RBAC)")
    else:
        print(f"❌ Distributor1: {resp.status_code} (expected 403)")
        return False
    
    return True

def main():
    print("\n" + "="*80)
    print("GO OIL DMS — Backend API Testing (CONTINUATION v3)")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"API Base: {API_BASE}")
    
    results = {
        "SMART PRICE-LIST IMPORT": False,
        "COUPON SCANNING + AUDIT": False,
        "DELETE ENDPOINTS": False,
        "HIERARCHY": False,
    }
    
    try:
        results["SMART PRICE-LIST IMPORT"] = test_price_import()
    except Exception as e:
        print(f"\n❌ SMART PRICE-LIST IMPORT failed with exception: {e}")
    
    try:
        results["COUPON SCANNING + AUDIT"] = test_coupon_scanning()
    except Exception as e:
        print(f"\n❌ COUPON SCANNING + AUDIT failed with exception: {e}")
    
    try:
        results["DELETE ENDPOINTS"] = test_delete_endpoints()
    except Exception as e:
        print(f"\n❌ DELETE ENDPOINTS failed with exception: {e}")
    
    try:
        results["HIERARCHY"] = test_hierarchy()
    except Exception as e:
        print(f"\n❌ HIERARCHY failed with exception: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nTotal: {passed}/{total} tests passed ({int(passed/total*100)}%)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
