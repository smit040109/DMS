#!/usr/bin/env python3
"""
Bug Fix Verification: Non-clickable "Create Record" buttons across master-data pages
Testing POST /api/collections/{resource} for all master-data collections
"""

import requests
import json
from datetime import datetime

# Backend URL from frontend/.env
BASE_URL = "https://sales-network-10.preview.emergentagent.com/api"

# Test credentials
CREDS = {
    "company_admin": {"email": "company@gooil.com", "password": "GoOil@2026"},
    "retailer": {"email": "retailer@gooil.com", "password": "GoOil@2026"},
    "acme_admin": {"email": "admin@acmepaint.com", "password": "AcmePaint@2026"},
}

# Test payloads for each resource
TEST_PAYLOADS = {
    "products": {
        "code": "TEST-PRD-001",
        "name": "Test Engine Oil",
        "category": "Engine Oil",
        "grade": "5W-30",
        "hsn": "27101990",
        "gst_rate": 18
    },
    "skus": {
        "sku_code": "TEST-SKU-001",
        "product_name": "Test Product",
        "pack_size": "1L",
        "barcode": "1234567890",
        "mrp": 1000,
        "trade_price": 800,
        "cost": 600
    },
    "batches": {
        "batch_no": "TEST-B-001",
        "sku_code": "GO-ENG-100-1L",
        "product_name": "GO Engine Oil",
        "manufactured_on": "2026-01-01",
        "expires_on": "2027-01-01",
        "batch_quantity": 1000
    },
    "distributors": {
        "code": "TEST-DIST-001",
        "name": "Test Distributor Ltd",
        "contact": "+1-555-0100",
        "gstin": "27TEST1234F1Z5",
        "credit_limit": 100000
    },
    "retailers": {
        "code": "TEST-RET-001",
        "name": "Test Retailer",
        "type": "Workshop",
        "city": "Test City"
    },
    "customers": {
        "code": "TEST-CUS-001",
        "name": "Test Customer",
        "segment": "Retail",
        "city": "Test City",
        "phone": "+1-555-0200"
    },
    "warehouses": {
        "name": "Test Warehouse",
        "type": "Central",
        "manager": "Test Manager",
        "capacity": 50000,
        "occupied": 0
    }
}

def login(email, password):
    """Login and return JWT token"""
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("access_token") or data.get("token")
        else:
            print(f"❌ Login failed for {email}: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"❌ Login exception for {email}: {e}")
        return None

def test_create_record(resource, payload, token):
    """Test POST /api/collections/{resource}"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(
            f"{BASE_URL}/collections/{resource}",
            json=payload,
            headers=headers,
            timeout=10
        )
        return resp
    except Exception as e:
        print(f"❌ Exception testing {resource}: {e}")
        return None

def test_get_records(resource, token):
    """Test GET /api/collections/{resource}"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(
            f"{BASE_URL}/collections/{resource}",
            headers=headers,
            timeout=10
        )
        return resp
    except Exception as e:
        print(f"❌ Exception getting {resource}: {e}")
        return None

def test_delete_record(resource, record_id, token):
    """Test DELETE /api/collections/{resource}/{id}"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.delete(
            f"{BASE_URL}/collections/{resource}/{record_id}",
            headers=headers,
            timeout=10
        )
        return resp
    except Exception as e:
        print(f"❌ Exception deleting {resource}/{record_id}: {e}")
        return None

def run_tests():
    """Run all test scenarios"""
    print("=" * 80)
    print("BUG FIX VERIFICATION: Non-clickable 'Create Record' buttons")
    print("=" * 80)
    print()
    
    results = {
        "part1": [],
        "part2": [],
        "part3": [],
        "part4": [],
        "created_records": []
    }
    
    # ========================================================================
    # PART 1: Verify POST /api/collections/{resource} works for master-data
    # ========================================================================
    print("PART 1: Testing POST /api/collections/{resource} for master-data collections")
    print("-" * 80)
    
    # Login as company admin (authorized)
    token = login(CREDS["company_admin"]["email"], CREDS["company_admin"]["password"])
    if not token:
        print("❌ CRITICAL: Cannot login as company admin. Aborting tests.")
        return results
    
    print(f"✅ Logged in as company@gooil.com")
    print()
    
    for resource, payload in TEST_PAYLOADS.items():
        print(f"Testing {resource}...")
        
        # POST to create record
        resp = test_create_record(resource, payload, token)
        if not resp:
            results["part1"].append({
                "resource": resource,
                "status": "FAIL",
                "reason": "Request exception"
            })
            print(f"  ❌ POST failed (exception)")
            continue
        
        if resp.status_code != 200:
            results["part1"].append({
                "resource": resource,
                "status": "FAIL",
                "reason": f"Status {resp.status_code}: {resp.text[:200]}"
            })
            print(f"  ❌ POST failed: {resp.status_code} - {resp.text[:100]}")
            continue
        
        # Verify response structure
        try:
            data = resp.json()
            if not isinstance(data, dict):
                results["part1"].append({
                    "resource": resource,
                    "status": "FAIL",
                    "reason": "Response is not a dict"
                })
                print(f"  ❌ Response is not a dict")
                continue
            
            # Check required fields
            record_id = data.get("id")
            tenant_id = data.get("tenant_id")
            created_at = data.get("created_at")
            created_by = data.get("created_by")
            
            if not record_id:
                results["part1"].append({
                    "resource": resource,
                    "status": "FAIL",
                    "reason": "Missing 'id' field in response"
                })
                print(f"  ❌ Missing 'id' field")
                continue
            
            if tenant_id != "tnt-gooil":
                results["part1"].append({
                    "resource": resource,
                    "status": "FAIL",
                    "reason": f"tenant_id is '{tenant_id}', expected 'tnt-gooil'"
                })
                print(f"  ❌ tenant_id is '{tenant_id}', expected 'tnt-gooil'")
                continue
            
            if not created_at:
                results["part1"].append({
                    "resource": resource,
                    "status": "FAIL",
                    "reason": "Missing 'created_at' field"
                })
                print(f"  ❌ Missing 'created_at' field")
                continue
            
            if not created_by:
                results["part1"].append({
                    "resource": resource,
                    "status": "FAIL",
                    "reason": "Missing 'created_by' field"
                })
                print(f"  ❌ Missing 'created_by' field")
                continue
            
            print(f"  ✅ POST successful: id={record_id}, tenant_id={tenant_id}")
            
            # Store for cleanup
            results["created_records"].append({
                "resource": resource,
                "id": record_id
            })
            
            # Verify record appears in GET list
            get_resp = test_get_records(resource, token)
            if get_resp and get_resp.status_code == 200:
                records = get_resp.json()
                found = False
                if isinstance(records, list):
                    found = any(r.get("id") == record_id for r in records)
                elif isinstance(records, dict) and "data" in records:
                    found = any(r.get("id") == record_id for r in records["data"])
                
                if found:
                    print(f"  ✅ Record appears in GET list")
                else:
                    print(f"  ⚠️  Record NOT found in GET list (may be pagination)")
            
            # Delete record for cleanup
            del_resp = test_delete_record(resource, record_id, token)
            if del_resp and del_resp.status_code in [200, 204]:
                print(f"  ✅ Record deleted (cleanup)")
            else:
                print(f"  ⚠️  Could not delete record (status: {del_resp.status_code if del_resp else 'N/A'})")
            
            results["part1"].append({
                "resource": resource,
                "status": "PASS",
                "id": record_id
            })
            
        except json.JSONDecodeError:
            results["part1"].append({
                "resource": resource,
                "status": "FAIL",
                "reason": "Response is not valid JSON"
            })
            print(f"  ❌ Response is not valid JSON")
        except Exception as e:
            results["part1"].append({
                "resource": resource,
                "status": "FAIL",
                "reason": f"Exception: {str(e)}"
            })
            print(f"  ❌ Exception: {e}")
        
        print()
    
    # ========================================================================
    # PART 2: Verify unauthorized roles CANNOT create records
    # ========================================================================
    print()
    print("PART 2: Testing unauthorized role (retailer) CANNOT create records")
    print("-" * 80)
    
    retailer_token = login(CREDS["retailer"]["email"], CREDS["retailer"]["password"])
    if retailer_token:
        print(f"✅ Logged in as retailer@gooil.com")
        
        # Try to create a product (should fail with 403)
        try:
            headers = {"Authorization": f"Bearer {retailer_token}"}
            resp = requests.post(
                f"{BASE_URL}/collections/products",
                json=TEST_PAYLOADS["products"],
                headers=headers,
                timeout=15
            )
            if resp.status_code == 403:
                print(f"  ✅ POST /collections/products returns 403 (as expected)")
                results["part2"].append({
                    "test": "Retailer cannot create products",
                    "status": "PASS"
                })
            else:
                print(f"  ❌ POST /collections/products returns {resp.status_code}, expected 403")
                print(f"      Response: {resp.text[:200]}")
                results["part2"].append({
                    "test": "Retailer cannot create products",
                    "status": "FAIL",
                    "reason": f"Got {resp.status_code} instead of 403"
                })
        except Exception as e:
            print(f"  ❌ Request exception: {e}")
            results["part2"].append({
                "test": "Retailer cannot create products",
                "status": "FAIL",
                "reason": f"Request exception: {e}"
            })
    else:
        print(f"❌ Cannot login as retailer")
        results["part2"].append({
            "test": "Retailer cannot create products",
            "status": "FAIL",
            "reason": "Cannot login as retailer"
        })
    
    print()
    
    # ========================================================================
    # PART 3: Verify tenant isolation preserved
    # ========================================================================
    print()
    print("PART 3: Testing tenant isolation")
    print("-" * 80)
    
    acme_token = login(CREDS["acme_admin"]["email"], CREDS["acme_admin"]["password"])
    if acme_token:
        print(f"✅ Logged in as admin@acmepaint.com (Tenant #2)")
        
        # Create a product as Acme Paint
        acme_payload = {
            "code": "ACME-PAINT-001",
            "name": "Acme Premium Paint",
            "category": "Paint",
            "grade": "Premium",
            "hsn": "32091000",
            "gst_rate": 18
        }
        
        resp = test_create_record("products", acme_payload, acme_token)
        if resp and resp.status_code == 200:
            acme_product = resp.json()
            acme_product_id = acme_product.get("id")
            print(f"  ✅ Created Acme product: id={acme_product_id}")
            
            # Now login as GO OIL admin and verify they CANNOT see Acme's product
            gooil_token = login(CREDS["company_admin"]["email"], CREDS["company_admin"]["password"])
            if gooil_token:
                print(f"  ✅ Logged in as company@gooil.com (Tenant #1)")
                
                # Get GO OIL products
                get_resp = test_get_records("products", gooil_token)
                if get_resp and get_resp.status_code == 200:
                    gooil_products = get_resp.json()
                    
                    # Check if Acme product is in the list
                    found = False
                    if isinstance(gooil_products, list):
                        found = any(p.get("id") == acme_product_id for p in gooil_products)
                    elif isinstance(gooil_products, dict) and "data" in gooil_products:
                        found = any(p.get("id") == acme_product_id for p in gooil_products["data"])
                    
                    if not found:
                        print(f"  ✅ GO OIL admin CANNOT see Acme's product (tenant isolation working)")
                        results["part3"].append({
                            "test": "Tenant isolation - GO OIL cannot see Acme products",
                            "status": "PASS"
                        })
                    else:
                        print(f"  ❌ GO OIL admin CAN see Acme's product (TENANT ISOLATION BROKEN)")
                        results["part3"].append({
                            "test": "Tenant isolation - GO OIL cannot see Acme products",
                            "status": "FAIL",
                            "reason": "Acme product visible to GO OIL admin"
                        })
                else:
                    print(f"  ⚠️  Cannot get GO OIL products")
                    results["part3"].append({
                        "test": "Tenant isolation - GO OIL cannot see Acme products",
                        "status": "FAIL",
                        "reason": "Cannot get GO OIL products"
                    })
            
            # Cleanup: delete Acme product
            del_resp = test_delete_record("products", acme_product_id, acme_token)
            if del_resp and del_resp.status_code in [200, 204]:
                print(f"  ✅ Acme product deleted (cleanup)")
        else:
            print(f"  ❌ Cannot create Acme product: {resp.status_code if resp else 'N/A'}")
            results["part3"].append({
                "test": "Tenant isolation - GO OIL cannot see Acme products",
                "status": "FAIL",
                "reason": "Cannot create Acme product"
            })
    else:
        print(f"❌ Cannot login as Acme admin")
        results["part3"].append({
            "test": "Tenant isolation - GO OIL cannot see Acme products",
            "status": "FAIL",
            "reason": "Cannot login as Acme admin"
        })
    
    print()
    
    # ========================================================================
    # PART 4: Regression check
    # ========================================================================
    print()
    print("PART 4: Regression check on existing endpoints")
    print("-" * 80)
    
    # Use GO OIL company admin token
    token = login(CREDS["company_admin"]["email"], CREDS["company_admin"]["password"])
    if not token:
        print("❌ Cannot login as company admin")
        return results
    
    print(f"✅ Logged in as company@gooil.com")
    print()
    
    # Test 1: GET /collections/products
    print("Testing GET /collections/products...")
    resp = test_get_records("products", token)
    if resp and resp.status_code == 200:
        products = resp.json()
        count = len(products) if isinstance(products, list) else len(products.get("data", []))
        if count >= 26:
            print(f"  ✅ Returns {count} products (>= 26)")
            results["part4"].append({
                "endpoint": "GET /collections/products",
                "status": "PASS",
                "count": count
            })
        else:
            print(f"  ⚠️  Returns {count} products (expected >= 26)")
            results["part4"].append({
                "endpoint": "GET /collections/products",
                "status": "FAIL",
                "reason": f"Only {count} products, expected >= 26"
            })
    else:
        print(f"  ❌ Failed: {resp.status_code if resp else 'N/A'}")
        results["part4"].append({
            "endpoint": "GET /collections/products",
            "status": "FAIL",
            "reason": f"Status {resp.status_code if resp else 'N/A'}"
        })
    print()
    
    # Test 2: GET /analytics/kpi/executive?range=month
    print("Testing GET /analytics/kpi/executive?range=month...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(
            f"{BASE_URL}/analytics/kpi/executive?range=month",
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            # Check for revenue > 0
            revenue = 0
            if isinstance(data, dict):
                if "kpis" in data and "revenue" in data["kpis"]:
                    revenue = data["kpis"]["revenue"].get("value", 0)
                elif "revenue" in data:
                    revenue = data["revenue"].get("value", 0) if isinstance(data["revenue"], dict) else data["revenue"]
            
            if revenue > 0:
                print(f"  ✅ Revenue = ${revenue:,.2f} (> 0)")
                results["part4"].append({
                    "endpoint": "GET /analytics/kpi/executive?range=month",
                    "status": "PASS",
                    "revenue": revenue
                })
            else:
                print(f"  ⚠️  Revenue = ${revenue:,.2f} (expected > 0)")
                results["part4"].append({
                    "endpoint": "GET /analytics/kpi/executive?range=month",
                    "status": "FAIL",
                    "reason": f"Revenue is {revenue}, expected > 0"
                })
        else:
            print(f"  ❌ Failed: {resp.status_code}")
            results["part4"].append({
                "endpoint": "GET /analytics/kpi/executive?range=month",
                "status": "FAIL",
                "reason": f"Status {resp.status_code}"
            })
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        results["part4"].append({
            "endpoint": "GET /analytics/kpi/executive?range=month",
            "status": "FAIL",
            "reason": f"Exception: {e}"
        })
    print()
    
    # Test 3: GET /platform/me/tenant
    print("Testing GET /platform/me/tenant...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(
            f"{BASE_URL}/platform/me/tenant",
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and data.get("name"):
                print(f"  ✅ Returns tenant config: {data.get('name')}")
                results["part4"].append({
                    "endpoint": "GET /platform/me/tenant",
                    "status": "PASS",
                    "tenant": data.get("name")
                })
            else:
                print(f"  ⚠️  Response structure unexpected")
                results["part4"].append({
                    "endpoint": "GET /platform/me/tenant",
                    "status": "FAIL",
                    "reason": "Response structure unexpected"
                })
        else:
            print(f"  ❌ Failed: {resp.status_code}")
            results["part4"].append({
                "endpoint": "GET /platform/me/tenant",
                "status": "FAIL",
                "reason": f"Status {resp.status_code}"
            })
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        results["part4"].append({
            "endpoint": "GET /platform/me/tenant",
            "status": "FAIL",
            "reason": f"Exception: {e}"
        })
    print()
    
    # Test 4: Login flow for all 3 personas
    print("Testing login flow for 3 personas...")
    personas = [
        ("owner@vayuerp.com", "VayuERP@2026", "Platform Owner"),
        ("company@gooil.com", "GoOil@2026", "Company Admin"),
        ("retailer@gooil.com", "GoOil@2026", "Retailer")
    ]
    
    all_login_pass = True
    for email, password, role in personas:
        token_test = login(email, password)
        if token_test:
            print(f"  ✅ {role} ({email}) login successful")
        else:
            print(f"  ❌ {role} ({email}) login failed")
            all_login_pass = False
    
    if all_login_pass:
        results["part4"].append({
            "endpoint": "Login flow (3 personas)",
            "status": "PASS"
        })
    else:
        results["part4"].append({
            "endpoint": "Login flow (3 personas)",
            "status": "FAIL",
            "reason": "One or more logins failed"
        })
    
    print()
    
    return results

def print_summary(results):
    """Print test summary"""
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    
    # Part 1
    print("PART 1: POST /api/collections/{resource} for master-data")
    print("-" * 80)
    part1_pass = sum(1 for r in results["part1"] if r["status"] == "PASS")
    part1_total = len(results["part1"])
    print(f"Result: {part1_pass}/{part1_total} PASSED")
    for r in results["part1"]:
        status_icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"  {status_icon} {r['resource']}: {r['status']}")
        if r["status"] == "FAIL":
            print(f"      Reason: {r.get('reason', 'Unknown')}")
    print()
    
    # Part 2
    print("PART 2: Unauthorized role cannot create records")
    print("-" * 80)
    part2_pass = sum(1 for r in results["part2"] if r["status"] == "PASS")
    part2_total = len(results["part2"])
    print(f"Result: {part2_pass}/{part2_total} PASSED")
    for r in results["part2"]:
        status_icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"  {status_icon} {r['test']}: {r['status']}")
        if r["status"] == "FAIL":
            print(f"      Reason: {r.get('reason', 'Unknown')}")
    print()
    
    # Part 3
    print("PART 3: Tenant isolation")
    print("-" * 80)
    part3_pass = sum(1 for r in results["part3"] if r["status"] == "PASS")
    part3_total = len(results["part3"])
    print(f"Result: {part3_pass}/{part3_total} PASSED")
    for r in results["part3"]:
        status_icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"  {status_icon} {r['test']}: {r['status']}")
        if r["status"] == "FAIL":
            print(f"      Reason: {r.get('reason', 'Unknown')}")
    print()
    
    # Part 4
    print("PART 4: Regression check")
    print("-" * 80)
    part4_pass = sum(1 for r in results["part4"] if r["status"] == "PASS")
    part4_total = len(results["part4"])
    print(f"Result: {part4_pass}/{part4_total} PASSED")
    for r in results["part4"]:
        status_icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"  {status_icon} {r['endpoint']}: {r['status']}")
        if r["status"] == "FAIL":
            print(f"      Reason: {r.get('reason', 'Unknown')}")
    print()
    
    # Overall
    total_pass = part1_pass + part2_pass + part3_pass + part4_pass
    total_tests = part1_total + part2_total + part3_total + part4_total
    print("=" * 80)
    print(f"OVERALL: {total_pass}/{total_tests} TESTS PASSED ({100*total_pass//total_tests}%)")
    print("=" * 80)
    print()

if __name__ == "__main__":
    results = run_tests()
    print_summary(results)
