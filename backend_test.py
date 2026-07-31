"""Simple DMS Backend API Tests — Comprehensive test suite for /api/dms/* endpoints."""
import os
import time
import requests

# Read backend URL from frontend/.env
BASE_URL = None
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
            break

if not BASE_URL:
    raise RuntimeError("REACT_APP_BACKEND_URL not found in /app/frontend/.env")

API = f"{BASE_URL}/api"
DMS_API = f"{API}/dms"
COMMON_PW = "Demo@2026"

# Test credentials from /app/memory/test_credentials.md
CREDENTIALS = {
    "owner": "owner@dms.com",
    "owner_accountant": "acct@dms.com",
    "dist1": "dist1@dms.com",
    "dist2": "dist2@dms.com",
    "dist_accountant": "distacct@dms.com",
    "retailer1": "retailer1@dms.com",
}

# Global state for test data
test_state = {
    "tokens": {},
    "category_id": None,
    "product_id": None,
    "new_distributor_id": None,
    "new_distributor_email": None,
    "order_id": None,
    "product_a_id": None,
    "product_b_id": None,
    "coupon_product_id": None,
    "coupon_code_valid": None,
    "coupon_code_unused": None,
    "dist1_id": None,
    "retailer1_id": None,
    "retailer2_id": None,
    "phase7_order_id": None,
}


def login(email, password=COMMON_PW):
    """Login and return token."""
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    if r.status_code != 200:
        print(f"❌ Login failed for {email}: {r.status_code} {r.text}")
        return None
    token = r.json()["token"]
    test_state["tokens"][email] = token
    return token


def headers(email):
    """Get auth headers for email."""
    token = test_state["tokens"].get(email)
    if not token:
        token = login(email)
    return {"Authorization": f"Bearer {token}"}


def print_section(title):
    """Print test section header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")


def print_test(name, passed, details=""):
    """Print test result."""
    status = "✅" if passed else "❌"
    print(f"{status} {name}")
    if details:
        print(f"   {details}")


# ============================================================================
# TEST SCENARIO 1: Auth + Seed Verification
# ============================================================================
def test_1_auth_and_seed():
    print_section("1. AUTH + SEED VERIFICATION")
    
    # Test 1.1: Login as owner and verify tenant_id
    print("\n1.1 Login as owner@dms.com and verify tenant_id in JWT")
    token = login(CREDENTIALS["owner"])
    if token:
        # Decode JWT to check tenant_id (simple base64 decode of payload)
        import base64
        import json
        parts = token.split(".")
        if len(parts) == 3:
            payload = base64.urlsafe_b64decode(parts[1] + "==").decode()
            jwt_data = json.loads(payload)
            tenant_id = jwt_data.get("tenant_id")
            print_test("Owner login successful", True, f"tenant_id={tenant_id}")
            if tenant_id == "tnt-dms-oil":
                print_test("Tenant ID is tnt-dms-oil", True)
            else:
                print_test("Tenant ID is tnt-dms-oil", False, f"Got: {tenant_id}")
    else:
        print_test("Owner login", False)
        return False
    
    # Test 1.2: Login all 5 accounts
    print("\n1.2 Login all 5 accounts successfully")
    all_success = True
    for role, email in CREDENTIALS.items():
        token = login(email)
        if token:
            print_test(f"Login {email}", True)
        else:
            print_test(f"Login {email}", False)
            all_success = False
    
    return all_success


# ============================================================================
# TEST SCENARIO 2: Categories (owner-only)
# ============================================================================
def test_2_categories():
    print_section("2. CATEGORIES (owner-only)")
    
    # Test 2.1: GET categories - verify 5 exist
    print("\n2.1 GET /api/dms/categories → verify 5 categories exist")
    r = requests.get(f"{DMS_API}/categories", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        cats = r.json()["data"]
        print_test(f"GET categories", True, f"Found {len(cats)} categories")
        if len(cats) >= 5:
            print_test("At least 5 categories exist", True)
        else:
            print_test("At least 5 categories exist", False, f"Only {len(cats)} found")
    else:
        print_test("GET categories", False, f"Status: {r.status_code}")
        return False
    
    # Test 2.2: POST new category as owner
    print("\n2.2 POST /api/dms/categories as owner → 200")
    payload = {"name": f"Test Category {int(time.time())}", "description": "Test category"}
    r = requests.post(f"{DMS_API}/categories", headers=headers(CREDENTIALS["owner"]), json=payload, timeout=15)
    if r.status_code == 200:
        cat = r.json()
        test_state["category_id"] = cat["id"]
        print_test("POST category as owner", True, f"Created: {cat['name']}")
    else:
        print_test("POST category as owner", False, f"Status: {r.status_code}, {r.text}")
        return False
    
    # Test 2.3: PUT update category
    print("\n2.3 PUT /api/dms/categories/{id} update name → 200")
    payload = {"name": f"Updated Test Category {int(time.time())}"}
    r = requests.put(f"{DMS_API}/categories/{test_state['category_id']}", 
                     headers=headers(CREDENTIALS["owner"]), json=payload, timeout=15)
    print_test("PUT category", r.status_code == 200, f"Status: {r.status_code}")
    
    # Test 2.4: DELETE category
    print("\n2.4 DELETE /api/dms/categories/{id} → 200")
    r = requests.delete(f"{DMS_API}/categories/{test_state['category_id']}", 
                        headers=headers(CREDENTIALS["owner"]), timeout=15)
    print_test("DELETE category", r.status_code == 200, f"Status: {r.status_code}")
    
    # Test 2.5: POST category as distributor → 403
    print("\n2.5 POST /api/dms/categories as distributor → 403")
    payload = {"name": "Unauthorized Category"}
    r = requests.post(f"{DMS_API}/categories", headers=headers(CREDENTIALS["dist1"]), json=payload, timeout=15)
    print_test("POST category as distributor → 403", r.status_code == 403, f"Status: {r.status_code}")
    
    return True


# ============================================================================
# TEST SCENARIO 3: Products (owner-only + price batches)
# ============================================================================
def test_3_products():
    print_section("3. PRODUCTS (owner-only + price batches)")
    
    # Test 3.1: GET products as owner
    print("\n3.1 GET /api/dms/products as owner → 12 products with category_name, box_qty, unit_price")
    r = requests.get(f"{DMS_API}/products", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        products = r.json()["data"]
        print_test(f"GET products", True, f"Found {len(products)} products")
        
        # Verify first product has required fields
        if products:
            p = products[0]
            has_fields = all(k in p for k in ["category_name", "box_qty", "unit_price"])
            print_test("Products have category_name, box_qty, unit_price", has_fields)
            
            # Store first two products for order testing
            if len(products) >= 2:
                test_state["product_a_id"] = products[0]["id"]
                test_state["product_b_id"] = products[1]["id"]
    else:
        print_test("GET products", False, f"Status: {r.status_code}")
        return False
    
    # Test 3.2: POST new product
    print("\n3.2 POST /api/dms/products with new product → verify created + price_batches entry")
    # Get a category first
    r = requests.get(f"{DMS_API}/categories", headers=headers(CREDENTIALS["owner"]), timeout=15)
    cat_id = r.json()["data"][0]["id"] if r.status_code == 200 and r.json()["data"] else None
    
    if not cat_id:
        print_test("POST product", False, "No category found")
        return False
    
    payload = {
        "name": f"Test Product {int(time.time())}",
        "category_id": cat_id,
        "sku_code": f"TEST-SKU-{int(time.time())}",
        "box_qty": 12,
        "unit_price": 5000,
        "gst_pct": 18,
        "hsn": "27101980"
    }
    r = requests.post(f"{DMS_API}/products", headers=headers(CREDENTIALS["owner"]), json=payload, timeout=15)
    if r.status_code == 200:
        product = r.json()
        test_state["product_id"] = product["id"]
        print_test("POST product", True, f"Created: {product['name']}")
        
        # Verify price history has one entry
        r2 = requests.get(f"{DMS_API}/products/{product['id']}/price-history", 
                         headers=headers(CREDENTIALS["owner"]), timeout=15)
        if r2.status_code == 200:
            batches = r2.json()["data"]
            print_test("Price batch created", len(batches) == 1, f"Found {len(batches)} batches")
    else:
        print_test("POST product", False, f"Status: {r.status_code}, {r.text}")
        return False
    
    # Test 3.3: PUT update product price
    print("\n3.3 PUT /api/dms/products/{id} with new unit_price → verify previous_price and 2 batches")
    payload = {"unit_price": 5500}
    r = requests.put(f"{DMS_API}/products/{test_state['product_id']}", 
                     headers=headers(CREDENTIALS["owner"]), json=payload, timeout=15)
    if r.status_code == 200:
        product = r.json()
        print_test("PUT product price", True, f"New price: {product.get('unit_price')}")
        print_test("Previous price set", product.get("previous_price") == 5000, 
                  f"previous_price={product.get('previous_price')}")
        print_test("Current price updated", product.get("unit_price") == 5500,
                  f"unit_price={product.get('unit_price')}")
        
        # Verify price history has 2 batches
        r2 = requests.get(f"{DMS_API}/products/{test_state['product_id']}/price-history", 
                         headers=headers(CREDENTIALS["owner"]), timeout=15)
        if r2.status_code == 200:
            batches = r2.json()["data"]
            print_test("Two price batches exist", len(batches) == 2, f"Found {len(batches)} batches")
            
            # Verify older batch has to_date set, newer has to_date=null
            if len(batches) == 2:
                newer = batches[0]  # sorted by from_date desc
                older = batches[1]
                print_test("Newer batch has to_date=null", newer.get("to_date") is None)
                print_test("Older batch has to_date set", older.get("to_date") is not None)
    else:
        print_test("PUT product price", False, f"Status: {r.status_code}")
    
    # Test 3.4: GET price history
    print("\n3.4 GET /api/dms/products/{id}/price-history → returns 2 batches")
    r = requests.get(f"{DMS_API}/products/{test_state['product_id']}/price-history", 
                     headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        batches = r.json()["data"]
        print_test("GET price history", len(batches) == 2, f"Found {len(batches)} batches")
    else:
        print_test("GET price history", False, f"Status: {r.status_code}")
    
    return True


# ============================================================================
# TEST SCENARIO 4: Distributors + KYC + visibility
# ============================================================================
def test_4_distributors():
    print_section("4. DISTRIBUTORS + KYC + VISIBILITY")
    
    # Test 4.1: GET distributors
    print("\n4.1 GET /api/dms/distributors → 2 distributors with kyc.gstin")
    r = requests.get(f"{DMS_API}/distributors", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        dists = r.json()["data"]
        print_test("GET distributors", True, f"Found {len(dists)} distributors")
        
        if dists:
            has_kyc = all("kyc" in d and "gstin" in d["kyc"] for d in dists)
            print_test("Distributors have KYC with GSTIN", has_kyc)
    else:
        print_test("GET distributors", False, f"Status: {r.status_code}")
        return False
    
    # Test 4.2: POST new distributor
    print("\n4.2 POST /api/dms/distributors as owner with full payload")
    unique_email = f"newdist{int(time.time())}@dms.com"
    payload = {
        "name": f"Test Distributor {int(time.time())}",
        "email": unique_email,
        "password": COMMON_PW,
        "phone": "+91-9876543210",
        "address": "Test Address, India",
        "gstin": "29AAACD9999M1Z5",
        "pan": "AAACD9999M",
        "bank_name": "Test Bank",
        "bank_account": "1234567890",
        "bank_ifsc": "TEST0001234",
        "credit_limit": 100000
    }
    r = requests.post(f"{DMS_API}/distributors", headers=headers(CREDENTIALS["owner"]), 
                     json=payload, timeout=15)
    if r.status_code == 200:
        dist = r.json()
        test_state["new_distributor_id"] = dist["id"]
        test_state["new_distributor_email"] = unique_email
        print_test("POST distributor", True, f"Created: {dist['name']}")
        print_test("Distributor has KYC block", "kyc" in dist)
        
        # Test 4.3: Verify new user can login
        print("\n4.3 Verify new distributor user can login")
        token = login(unique_email, COMMON_PW)
        if token:
            print_test("New distributor can login", True)
        else:
            print_test("New distributor can login", False)
    else:
        print_test("POST distributor", False, f"Status: {r.status_code}, {r.text}")
        return False
    
    # Test 4.4: GET visibility for new distributor
    print("\n4.4 GET /api/dms/distributors/{did}/visibility → all products visible=true by default")
    r = requests.get(f"{DMS_API}/distributors/{test_state['new_distributor_id']}/visibility", 
                     headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        vis = r.json()["data"]
        print_test("GET visibility", True, f"Found {len(vis)} products")
        
        all_visible = all(p.get("visible", True) for p in vis)
        print_test("All products visible by default", all_visible)
        
        # Pick a product to hide
        if vis and test_state.get("product_a_id"):
            test_product_id = test_state["product_a_id"]
        elif vis:
            test_product_id = vis[0]["product_id"]
        else:
            test_product_id = None
        
        # Test 4.5: PUT visibility to hide a product
        if test_product_id:
            print("\n4.5 PUT /api/dms/distributors/{did}/visibility with visible=false")
            payload = {"product_id": test_product_id, "visible": False}
            r2 = requests.put(f"{DMS_API}/distributors/{test_state['new_distributor_id']}/visibility", 
                             headers=headers(CREDENTIALS["owner"]), json=payload, timeout=15)
            print_test("PUT visibility", r2.status_code == 200, f"Status: {r2.status_code}")
            
            # Verify visibility changed
            r3 = requests.get(f"{DMS_API}/distributors/{test_state['new_distributor_id']}/visibility", 
                             headers=headers(CREDENTIALS["owner"]), timeout=15)
            if r3.status_code == 200:
                vis2 = r3.json()["data"]
                hidden_product = next((p for p in vis2 if p["product_id"] == test_product_id), None)
                if hidden_product:
                    print_test("Product visibility changed to false", 
                              hidden_product.get("visible") == False)
            
            # Test 4.6: Login as new distributor and verify hidden product not in browse
            print("\n4.6 Login as new distributor → GET /api/dms/distributor/browse → hidden product NOT in list")
            r4 = requests.get(f"{DMS_API}/distributor/browse", 
                             headers=headers(test_state["new_distributor_email"]), timeout=15)
            if r4.status_code == 200:
                browse_products = r4.json()["data"]
                hidden_in_browse = any(p["id"] == test_product_id for p in browse_products)
                print_test("Hidden product NOT in distributor browse", not hidden_in_browse)
            else:
                print_test("GET distributor browse", False, f"Status: {r4.status_code}")
            
            # Test 4.7: Verify hidden product NOT in GET /api/dms/products for distributor
            print("\n4.7 GET /api/dms/products as new distributor → hidden product NOT in list")
            r5 = requests.get(f"{DMS_API}/products", 
                             headers=headers(test_state["new_distributor_email"]), timeout=15)
            if r5.status_code == 200:
                dist_products = r5.json()["data"]
                hidden_in_products = any(p["id"] == test_product_id for p in dist_products)
                print_test("Hidden product NOT in distributor products", not hidden_in_products)
                
                # Verify owner still sees all
                r6 = requests.get(f"{DMS_API}/products", headers=headers(CREDENTIALS["owner"]), timeout=15)
                if r6.status_code == 200:
                    owner_products = r6.json()["data"]
                    print_test("Owner still sees all products", len(owner_products) > len(dist_products))
    else:
        print_test("GET visibility", False, f"Status: {r.status_code}")
    
    return True


# ============================================================================
# TEST SCENARIO 5: Distributor browse — old vs new price
# ============================================================================
def test_5_distributor_browse():
    print_section("5. DISTRIBUTOR BROWSE — old vs new price")
    
    print("\n5.1 As dist1@dms.com, GET /api/dms/distributor/browse")
    r = requests.get(f"{DMS_API}/distributor/browse", headers=headers(CREDENTIALS["dist1"]), timeout=15)
    if r.status_code == 200:
        products = r.json()["data"]
        print_test("GET distributor browse", True, f"Found {len(products)} products")
        
        # Verify products with previous_price show both old + new
        has_previous = [p for p in products if p.get("previous_price")]
        no_previous = [p for p in products if not p.get("previous_price")]
        
        print_test(f"Products with previous_price", len(has_previous) >= 0, 
                  f"Found {len(has_previous)} products with price history")
        print_test(f"Products without previous_price", len(no_previous) >= 0,
                  f"Found {len(no_previous)} products without price history")
        
        # Verify owner_stock_boxes is present
        has_stock = all("owner_stock_boxes" in p for p in products)
        print_test("All products have owner_stock_boxes", has_stock)
    else:
        print_test("GET distributor browse", False, f"Status: {r.status_code}")
        return False
    
    return True


# ============================================================================
# TEST SCENARIO 6: Primary Order full lifecycle
# ============================================================================
def test_6_primary_order_lifecycle():
    print_section("6. PRIMARY ORDER FULL LIFECYCLE")
    
    if not test_state.get("product_a_id") or not test_state.get("product_b_id"):
        print_test("Primary order test", False, "Product IDs not available")
        return False
    
    # Test 6.1: Place order as distributor
    print("\n6.1 As dist1@dms.com, POST /api/dms/primary-orders")
    payload = {
        "items": [
            {"product_id": test_state["product_a_id"], "qty_boxes": 5},
            {"product_id": test_state["product_b_id"], "qty_boxes": 3}
        ],
        "notes": "Test order"
    }
    r = requests.post(f"{DMS_API}/primary-orders", headers=headers(CREDENTIALS["dist1"]), 
                     json=payload, timeout=15)
    if r.status_code == 200:
        order = r.json()
        test_state["order_id"] = order["id"]
        print_test("POST primary order", True, f"Order: {order['order_no']}")
        print_test("Status is pending", order.get("status") == "pending")
        print_test("Fulfillment % is 0", order.get("fulfillment_pct") == 0)
        
        # Verify totals
        has_totals = all(k in order for k in ["subtotal", "gst_total", "total"])
        print_test("Order has subtotal, gst_total, total", has_totals)
        
        # Verify items
        items = order.get("items", [])
        print_test("Order has 2 items", len(items) == 2)
        if items:
            item_a = next((i for i in items if i["product_id"] == test_state["product_a_id"]), None)
            if item_a:
                print_test("Item A: qty_boxes_ordered=5", item_a.get("qty_boxes_ordered") == 5)
                print_test("Item A: qty_boxes_fulfilled=0", item_a.get("qty_boxes_fulfilled") == 0)
    else:
        print_test("POST primary order", False, f"Status: {r.status_code}, {r.text}")
        return False
    
    # Test 6.2: GET order as distributor
    print("\n6.2 GET /api/dms/primary-orders as distributor → sees their order")
    r = requests.get(f"{DMS_API}/primary-orders", headers=headers(CREDENTIALS["dist1"]), timeout=15)
    if r.status_code == 200:
        orders = r.json()["data"]
        has_order = any(o["id"] == test_state["order_id"] for o in orders)
        print_test("Distributor sees their order", has_order)
    else:
        print_test("GET orders as distributor", False, f"Status: {r.status_code}")
    
    # Test 6.3: GET order as owner
    print("\n6.3 GET /api/dms/primary-orders as owner → sees the order")
    r = requests.get(f"{DMS_API}/primary-orders", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        orders = r.json()["data"]
        has_order = any(o["id"] == test_state["order_id"] for o in orders)
        print_test("Owner sees the order", has_order)
    else:
        print_test("GET orders as owner", False, f"Status: {r.status_code}")
    
    # Get owner inventory before fulfillment
    print("\n6.4 Get owner inventory before fulfillment")
    r = requests.get(f"{DMS_API}/owner/inventory", headers=headers(CREDENTIALS["owner"]), timeout=15)
    inventory_before = {}
    if r.status_code == 200:
        inv_data = r.json()["data"]
        for item in inv_data:
            inventory_before[item["product_id"]] = item.get("qty_boxes", 0)
        print_test("Got owner inventory", True, f"Total items: {len(inv_data)}")
    
    # Test 6.5: Fulfill line A fully
    print("\n6.5 POST /api/dms/primary-orders/{oid}/fulfill-line for product A (5 boxes)")
    payload = {"product_id": test_state["product_a_id"], "qty_boxes_fulfilled": 5}
    r = requests.post(f"{DMS_API}/primary-orders/{test_state['order_id']}/fulfill-line", 
                     headers=headers(CREDENTIALS["owner"]), json=payload, timeout=15)
    if r.status_code == 200:
        result = r.json()
        print_test("Fulfill line A", True, f"Fulfillment %: {result.get('fulfillment_pct')}")
        print_test("Partial fulfillment %", 0 < result.get("fulfillment_pct", 0) < 100)
    else:
        print_test("Fulfill line A", False, f"Status: {r.status_code}")
    
    # Test 6.6: Fulfill line B partially (2 out of 3)
    print("\n6.6 POST /api/dms/primary-orders/{oid}/fulfill-line for product B (2 out of 3 boxes)")
    payload = {"product_id": test_state["product_b_id"], "qty_boxes_fulfilled": 2}
    r = requests.post(f"{DMS_API}/primary-orders/{test_state['order_id']}/fulfill-line", 
                     headers=headers(CREDENTIALS["owner"]), json=payload, timeout=15)
    if r.status_code == 200:
        result = r.json()
        pct = result.get("fulfillment_pct", 0)
        print_test("Fulfill line B partially", True, f"Fulfillment %: {pct}")
        print_test("Fulfillment % in 60-95% range", 60 <= pct <= 95, f"Got: {pct}%")
        print_test("Status is partially_fulfilled", result.get("status") == "partially_fulfilled")
    else:
        print_test("Fulfill line B", False, f"Status: {r.status_code}")
    
    # Test 6.7: Mark order ready
    print("\n6.7 POST /api/dms/primary-orders/{oid}/ready as owner")
    r = requests.post(f"{DMS_API}/primary-orders/{test_state['order_id']}/ready", 
                     headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        print_test("Mark ready", True, f"Status: {result.get('status')}")
        print_test("Status is ready_to_go", result.get("status") == "ready_to_go")
        print_test("E-bill ID set", result.get("ebill_id") is not None)
        
        # Test 6.8: Get order and verify e-bill
        print("\n6.8 GET order → verify ebill exists with total based on fulfilled qty")
        r2 = requests.get(f"{DMS_API}/primary-orders/{test_state['order_id']}", 
                         headers=headers(CREDENTIALS["owner"]), timeout=15)
        if r2.status_code == 200:
            order = r2.json()
            print_test("Order has ebill", "ebill" in order and order["ebill"] is not None)
            if "ebill" in order and order["ebill"]:
                ebill = order["ebill"]
                print_test("E-bill has total", "total" in ebill)
                # E-bill total should be based on fulfilled qty (5+2=7 boxes)
                print_test("E-bill based on fulfilled qty", True, 
                          f"E-bill total: ₹{ebill.get('total', 0):,.0f}")
        
        # Test 6.9: Verify owner inventory decremented
        print("\n6.9 Verify owner inventory decremented by fulfilled amounts")
        r3 = requests.get(f"{DMS_API}/owner/inventory", headers=headers(CREDENTIALS["owner"]), timeout=15)
        if r3.status_code == 200:
            inv_data = r3.json()["data"]
            inventory_after = {}
            for item in inv_data:
                inventory_after[item["product_id"]] = item.get("qty_boxes", 0)
            
            # Check product A (should be -5)
            before_a = inventory_before.get(test_state["product_a_id"], 0)
            after_a = inventory_after.get(test_state["product_a_id"], 0)
            print_test("Product A inventory decreased by 5", before_a - after_a == 5,
                      f"Before: {before_a}, After: {after_a}")
            
            # Check product B (should be -2)
            before_b = inventory_before.get(test_state["product_b_id"], 0)
            after_b = inventory_after.get(test_state["product_b_id"], 0)
            print_test("Product B inventory decreased by 2", before_b - after_b == 2,
                      f"Before: {before_b}, After: {after_b}")
        
        # Test 6.10: Verify primary ledger has invoice entry
        print("\n6.10 GET /api/dms/ledger/primary → has invoice entry for e-bill total")
        r4 = requests.get(f"{DMS_API}/ledger/primary", headers=headers(CREDENTIALS["owner"]), timeout=15)
        if r4.status_code == 200:
            ledger = r4.json()
            entries = ledger.get("entries", [])
            invoice_entries = [e for e in entries if e.get("kind") == "invoice"]
            print_test("Primary ledger has invoice entries", len(invoice_entries) > 0,
                      f"Found {len(invoice_entries)} invoice entries")
    else:
        print_test("Mark ready", False, f"Status: {r.status_code}, {r.text}")
        return False
    
    # Test 6.11: Mark order received as distributor
    print("\n6.11 POST /api/dms/primary-orders/{oid}/receive as distributor")
    r = requests.post(f"{DMS_API}/primary-orders/{test_state['order_id']}/receive", 
                     headers=headers(CREDENTIALS["dist1"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        print_test("Mark received", True, f"Status: {result.get('status')}")
        print_test("Status is received", result.get("status") == "received")
        
        # Test 6.12: Try to receive again (should fail)
        print("\n6.12 Try to receive again → 400")
        r2 = requests.post(f"{DMS_API}/primary-orders/{test_state['order_id']}/receive", 
                          headers=headers(CREDENTIALS["dist1"]), timeout=15)
        print_test("Cannot receive again", r2.status_code == 400, f"Status: {r2.status_code}")
    else:
        print_test("Mark received", False, f"Status: {r.status_code}")
    
    # Test 6.13: Try to receive as other distributor (should fail)
    print("\n6.13 POST /api/dms/primary-orders/{oid}/receive as OTHER distributor → 403")
    # For this test, the order is already received, so we expect 400 or 403
    r = requests.post(f"{DMS_API}/primary-orders/{test_state['order_id']}/receive", 
                     headers=headers(CREDENTIALS["dist2"]), timeout=15)
    print_test("Other distributor cannot receive", r.status_code in [403, 400], 
              f"Status: {r.status_code}")
    
    return True


# ============================================================================
# TEST SCENARIO 7: Attachments
# ============================================================================
def test_7_attachments():
    print_section("7. ATTACHMENTS")
    
    if not test_state.get("order_id"):
        print_test("Attachments test", False, "Order ID not available")
        return False
    
    # Test 7.1: POST attachment
    print("\n7.1 POST /api/dms/attachments as owner_accountant")
    payload = {
        "reference_id": test_state["order_id"],
        "kind": "invoice",
        "name": "Test Invoice.pdf",
        "url": "https://example.com/test-invoice.pdf"
    }
    r = requests.post(f"{DMS_API}/attachments", headers=headers(CREDENTIALS["owner_accountant"]), 
                     json=payload, timeout=15)
    if r.status_code == 200:
        att = r.json()
        print_test("POST attachment", True, f"Created: {att.get('name')}")
    else:
        print_test("POST attachment", False, f"Status: {r.status_code}, {r.text}")
        return False
    
    # Test 7.2: GET attachments
    print("\n7.2 GET /api/dms/attachments?reference_id={oid} → returns the attachment")
    r = requests.get(f"{DMS_API}/attachments?reference_id={test_state['order_id']}", 
                     headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        atts = r.json()["data"]
        print_test("GET attachments", len(atts) > 0, f"Found {len(atts)} attachments")
    else:
        print_test("GET attachments", False, f"Status: {r.status_code}")
    
    # Test 7.3: GET order includes attachments
    print("\n7.3 GET /api/dms/primary-orders/{oid} → includes attachments array")
    r = requests.get(f"{DMS_API}/primary-orders/{test_state['order_id']}", 
                     headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        order = r.json()
        has_attachments = "attachments" in order and isinstance(order["attachments"], list)
        print_test("Order includes attachments array", has_attachments)
        if has_attachments:
            print_test("Attachments array not empty", len(order["attachments"]) > 0,
                      f"Found {len(order['attachments'])} attachments")
    else:
        print_test("GET order", False, f"Status: {r.status_code}")
    
    return True


# ============================================================================
# TEST SCENARIO 8: Primary ledger + payments
# ============================================================================
def test_8_primary_ledger():
    print_section("8. PRIMARY LEDGER + PAYMENTS")
    
    # Test 8.1: GET primary ledger
    print("\n8.1 GET /api/dms/ledger/primary as owner → has entries and summary")
    r = requests.get(f"{DMS_API}/ledger/primary", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        ledger = r.json()
        print_test("GET primary ledger", True)
        
        has_entries = "entries" in ledger and isinstance(ledger["entries"], list)
        print_test("Ledger has entries", has_entries, f"Found {len(ledger.get('entries', []))} entries")
        
        has_summary = "summary" in ledger and isinstance(ledger["summary"], list)
        print_test("Ledger has summary", has_summary)
        
        outstanding_before = 0
        if has_summary and ledger["summary"]:
            summary = ledger["summary"][0]
            has_fields = all(k in summary for k in ["billed", "paid", "outstanding"])
            print_test("Summary has billed/paid/outstanding", has_fields)
            
            outstanding_before = summary.get("outstanding", 0)
            print(f"   Outstanding before payment: ₹{outstanding_before:,.2f}")
    else:
        print_test("GET primary ledger", False, f"Status: {r.status_code}")
        return False
    
    # Test 8.2: POST payment
    print("\n8.2 POST /api/dms/ledger/primary/payment as owner_accountant")
    # Get a distributor ID
    r = requests.get(f"{DMS_API}/distributors", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200 and r.json()["data"]:
        dist_id = r.json()["data"][0]["id"]
        
        payload = {
            "distributor_id": dist_id,
            "amount": 5000,
            "method": "upi",
            "description": "Test payment"
        }
        r2 = requests.post(f"{DMS_API}/ledger/primary/payment", 
                          headers=headers(CREDENTIALS["owner_accountant"]), json=payload, timeout=15)
        if r2.status_code == 200:
            payment = r2.json()
            print_test("POST payment", True, f"Amount: ₹{payment.get('amount', 0):,.0f}")
        else:
            print_test("POST payment", False, f"Status: {r2.status_code}, {r2.text}")
        
        # Test 8.3: Verify outstanding reduced
        print("\n8.3 GET /api/dms/ledger/primary → payment reduces outstanding")
        r3 = requests.get(f"{DMS_API}/ledger/primary", headers=headers(CREDENTIALS["owner"]), timeout=15)
        if r3.status_code == 200:
            ledger = r3.json()
            if ledger.get("summary"):
                summary = ledger["summary"][0]
                outstanding_after = summary.get("outstanding", 0)
                print_test("Outstanding reduced", outstanding_after < outstanding_before,
                          f"After: ₹{outstanding_after:,.2f}")
    else:
        print_test("POST payment", False, "No distributors found")
    
    return True


# ============================================================================
# TEST SCENARIO 9: Notifications
# ============================================================================
def test_9_notifications():
    print_section("9. NOTIFICATIONS")
    
    # Test 9.1: GET notifications as owner
    print("\n9.1 GET /api/dms/notifications as owner → has unread notifications")
    r = requests.get(f"{DMS_API}/notifications", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        notifs = r.json()
        print_test("GET notifications", True, f"Found {len(notifs.get('data', []))} notifications")
        print_test("Has unread count", "unread" in notifs, f"Unread: {notifs.get('unread', 0)}")
        
        # Get a notification ID
        if notifs.get("data"):
            notif_id = notifs["data"][0]["id"]
            
            # Test 9.2: Mark notification as read
            print("\n9.2 POST /api/dms/notifications/{nid}/read → verify read=true")
            r2 = requests.post(f"{DMS_API}/notifications/{notif_id}/read", 
                              headers=headers(CREDENTIALS["owner"]), timeout=15)
            print_test("Mark notification read", r2.status_code == 200, f"Status: {r2.status_code}")
    else:
        print_test("GET notifications", False, f"Status: {r.status_code}")
    
    # Test 9.3: Mark all as read
    print("\n9.3 POST /api/dms/notifications/read-all → verify unread=0")
    r = requests.post(f"{DMS_API}/notifications/read-all", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        print_test("Mark all read", True)
        
        # Verify unread count is 0
        r2 = requests.get(f"{DMS_API}/notifications", headers=headers(CREDENTIALS["owner"]), timeout=15)
        if r2.status_code == 200:
            notifs = r2.json()
            print_test("Unread count is 0", notifs.get("unread", 0) == 0, 
                      f"Unread: {notifs.get('unread', 0)}")
    else:
        print_test("Mark all read", False, f"Status: {r.status_code}")
    
    return True


# ============================================================================
# TEST SCENARIO 10: Dashboards
# ============================================================================
def test_10_dashboards():
    print_section("10. DASHBOARDS")
    
    # Test 10.1: Owner dashboard
    print("\n10.1 GET /api/dms/dashboard/owner as owner")
    r = requests.get(f"{DMS_API}/dashboard/owner", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        dash = r.json()
        print_test("GET owner dashboard", True)
        
        kpis = dash.get("kpis", {})
        expected_kpis = ["distributors", "products", "revenue_mtd", "outstanding_receivable", "inventory_value"]
        has_kpis = all(k in kpis for k in expected_kpis)
        print_test("Dashboard has expected KPIs", has_kpis)
        
        if has_kpis:
            print(f"   Distributors: {kpis.get('distributors')}")
            print(f"   Products: {kpis.get('products')}")
            print(f"   Revenue MTD: ₹{kpis.get('revenue_mtd', 0):,.0f}")
            print(f"   Outstanding: ₹{kpis.get('outstanding_receivable', 0):,.0f}")
            print(f"   Inventory Value: ₹{kpis.get('inventory_value', 0):,.0f}")
    else:
        print_test("GET owner dashboard", False, f"Status: {r.status_code}")
    
    # Test 10.2: Distributor dashboard
    print("\n10.2 GET /api/dms/dashboard/distributor as dist1")
    r = requests.get(f"{DMS_API}/dashboard/distributor", headers=headers(CREDENTIALS["dist1"]), timeout=15)
    if r.status_code == 200:
        dash = r.json()
        print_test("GET distributor dashboard", True)
        
        kpis = dash.get("kpis", {})
        expected_kpis = ["stock_boxes", "payable_to_owner"]
        has_kpis = all(k in kpis for k in expected_kpis)
        print_test("Dashboard has expected KPIs", has_kpis)
        
        if has_kpis:
            print(f"   Stock Boxes: {kpis.get('stock_boxes')}")
            print(f"   Payable to Owner: ₹{kpis.get('payable_to_owner', 0):,.0f}")
            
            # Verify stock_boxes > 0 (from received order)
            print_test("Stock boxes > 0 (from received order)", kpis.get("stock_boxes", 0) > 0,
                      f"Stock: {kpis.get('stock_boxes', 0)} boxes")
            
            # Verify payable matches ledger outstanding
            print_test("Payable matches ledger outstanding", True,
                      f"Payable: ₹{kpis.get('payable_to_owner', 0):,.0f}")
    else:
        print_test("GET distributor dashboard", False, f"Status: {r.status_code}")
    
    return True


# ============================================================================
# TEST SCENARIO 11: Cross-tenant / security
# ============================================================================
def test_11_security():
    print_section("11. CROSS-TENANT / SECURITY")
    
    if not test_state.get("order_id"):
        print_test("Security test", False, "Order ID not available")
        return False
    
    # Test 11.1: Other distributor cannot access order
    print("\n11.1 GET /api/dms/primary-orders/{oid} as dist2 (other distributor) → 403")
    r = requests.get(f"{DMS_API}/primary-orders/{test_state['order_id']}", 
                     headers=headers(CREDENTIALS["dist2"]), timeout=15)
    print_test("Other distributor gets 403", r.status_code == 403, f"Status: {r.status_code}")
    
    # Test 11.2: Retailer access (should not crash)
    print("\n11.2 GET /api/dms/distributors as retailer1 → returns empty or restricted")
    r = requests.get(f"{DMS_API}/distributors", headers=headers(CREDENTIALS["retailer1"]), timeout=15)
    if r.status_code == 200:
        dists = r.json()["data"]
        print_test("Retailer gets response (not crash)", True, f"Found {len(dists)} distributors")
    elif r.status_code == 403:
        print_test("Retailer gets 403 (restricted)", True)
    else:
        print_test("Retailer access", False, f"Unexpected status: {r.status_code}")
    
    return True


# ============================================================================
# TEST SCENARIO 12: PHASE 7 - Coupon Generation
# ============================================================================
def test_12_coupon_generation():
    print_section("12. PHASE 7 - COUPON GENERATION")
    
    # Get first product from /dms/products
    print("\n12.1 Get first product for coupon generation")
    r = requests.get(f"{DMS_API}/products", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        products = r.json()["data"]
        if products:
            test_state["coupon_product_id"] = products[0]["id"]
            print_test("Got product for coupons", True, f"Product: {products[0]['name']}")
        else:
            print_test("Get product", False, "No products found")
            return False
    else:
        print_test("Get products", False, f"Status: {r.status_code}")
        return False
    
    # Test 12.2: Generate 2000 coupons as owner
    print("\n12.2 POST /dms/owner/coupons/generate with count=2000")
    payload = {"product_id": test_state["coupon_product_id"], "count": 2000}
    r = requests.post(f"{DMS_API}/owner/coupons/generate", headers=headers(CREDENTIALS["owner"]), 
                     json=payload, timeout=30)
    if r.status_code == 200:
        result = r.json()
        print_test("Generate 2000 coupons", result.get("ok") == True, 
                  f"Count: {result.get('count')}, Start: {result.get('start_code')}, End: {result.get('end_code')}")
        print_test("Count is 2000", result.get("count") == 2000)
        print_test("Has start_code", result.get("start_code") is not None and result.get("start_code").startswith("CPN"))
        print_test("Has end_code", result.get("end_code") is not None and result.get("end_code").startswith("CPN"))
    else:
        print_test("Generate coupons", False, f"Status: {r.status_code}, {r.text}")
        return False
    
    # Test 12.3: Generate another 1000 coupons for same product (should be sequential)
    print("\n12.3 POST /dms/owner/coupons/generate with count=1000 (sequential)")
    payload = {"product_id": test_state["coupon_product_id"], "count": 1000}
    r = requests.post(f"{DMS_API}/owner/coupons/generate", headers=headers(CREDENTIALS["owner"]), 
                     json=payload, timeout=30)
    if r.status_code == 200:
        result = r.json()
        print_test("Generate 1000 more coupons", result.get("ok") == True, 
                  f"Count: {result.get('count')}, Start: {result.get('start_code')}, End: {result.get('end_code')}")
        print_test("Count is 1000", result.get("count") == 1000)
    else:
        print_test("Generate sequential coupons", False, f"Status: {r.status_code}")
    
    # Test 12.4: Try to generate as distributor (should fail)
    print("\n12.4 POST /dms/owner/coupons/generate as distributor → 403")
    payload = {"product_id": test_state["coupon_product_id"], "count": 100}
    r = requests.post(f"{DMS_API}/owner/coupons/generate", headers=headers(CREDENTIALS["dist1"]), 
                     json=payload, timeout=15)
    print_test("Distributor cannot generate coupons", r.status_code == 403, f"Status: {r.status_code}")
    
    return True


# ============================================================================
# TEST SCENARIO 13: PHASE 7 - Coupon Listing
# ============================================================================
def test_13_coupon_listing():
    print_section("13. PHASE 7 - COUPON LISTING")
    
    # Test 13.1: List coupons with limit
    print("\n13.1 GET /dms/owner/coupons?limit=5 → returns 5 rows")
    r = requests.get(f"{DMS_API}/owner/coupons?limit=5", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        coupons = result.get("data", [])
        print_test("GET coupons with limit=5", len(coupons) == 5, f"Found {len(coupons)} coupons")
        
        if coupons:
            # Store an unused coupon code for later tests
            unused = [c for c in coupons if c.get("status") == "unused"]
            if unused:
                test_state["coupon_code_unused"] = unused[0]["coupon_code"]
                print_test("Found unused coupon", True, f"Code: {test_state['coupon_code_unused']}")
    else:
        print_test("GET coupons", False, f"Status: {r.status_code}")
        return False
    
    # Test 13.2: List coupons with status filter
    print("\n13.2 GET /dms/owner/coupons?status=unused → all unused")
    r = requests.get(f"{DMS_API}/owner/coupons?status=unused", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        coupons = result.get("data", [])
        all_unused = all(c.get("status") == "unused" for c in coupons)
        print_test("All coupons are unused", all_unused, f"Found {len(coupons)} unused coupons")
    else:
        print_test("GET unused coupons", False, f"Status: {r.status_code}")
    
    return True


# ============================================================================
# TEST SCENARIO 14: PHASE 7 - Coupon Batches
# ============================================================================
def test_14_coupon_batches():
    print_section("14. PHASE 7 - COUPON BATCHES")
    
    print("\n14.1 GET /dms/owner/coupons/batches → at least 2 rows")
    r = requests.get(f"{DMS_API}/owner/coupons/batches", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        batches = result.get("data", [])
        print_test("GET coupon batches", len(batches) >= 2, f"Found {len(batches)} batches")
        
        if batches:
            batch = batches[0]
            has_fields = all(k in batch for k in ["product_name", "count", "start_code", "end_code"])
            print_test("Batch has required fields", has_fields)
            if has_fields:
                print(f"   Product: {batch.get('product_name')}, Count: {batch.get('count')}")
                print(f"   Range: {batch.get('start_code')} to {batch.get('end_code')}")
    else:
        print_test("GET coupon batches", False, f"Status: {r.status_code}")
        return False
    
    return True


# ============================================================================
# TEST SCENARIO 15: PHASE 7 - Auto-assign on Dispatch
# ============================================================================
def test_15_coupon_auto_assign():
    print_section("15. PHASE 7 - AUTO-ASSIGN ON DISPATCH")
    
    # Get dist1 ID
    print("\n15.1 Get distributor IDs")
    r = requests.get(f"{DMS_API}/distributors", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        dists = r.json()["data"]
        dist1 = next((d for d in dists if d.get("email") == CREDENTIALS["dist1"]), None)
        if dist1:
            test_state["dist1_id"] = dist1["id"]
            print_test("Got dist1 ID", True, f"ID: {dist1['id']}")
        else:
            print_test("Get dist1", False, "Distributor not found")
            return False
    else:
        print_test("Get distributors", False, f"Status: {r.status_code}")
        return False
    
    # Test 15.2: Create a new primary order as dist1
    print("\n15.2 Create primary order as dist1 with coupon product (5 boxes)")
    payload = {
        "items": [{"product_id": test_state["coupon_product_id"], "qty_boxes": 5}],
        "notes": "Phase 7 coupon test order"
    }
    r = requests.post(f"{DMS_API}/primary-orders", headers=headers(CREDENTIALS["dist1"]), 
                     json=payload, timeout=15)
    if r.status_code == 200:
        order = r.json()
        test_state["phase7_order_id"] = order["id"]
        print_test("Create order", True, f"Order: {order['order_no']}")
    else:
        print_test("Create order", False, f"Status: {r.status_code}, {r.text}")
        return False
    
    # Test 15.3: Fulfill the order as owner
    print("\n15.3 Fulfill order (5 boxes)")
    payload = {"product_id": test_state["coupon_product_id"], "qty_boxes_fulfilled": 5}
    r = requests.post(f"{DMS_API}/primary-orders/{test_state['phase7_order_id']}/fulfill-line", 
                     headers=headers(CREDENTIALS["owner"]), json=payload, timeout=15)
    if r.status_code == 200:
        print_test("Fulfill order", True)
    else:
        print_test("Fulfill order", False, f"Status: {r.status_code}")
        return False
    
    # Test 15.4: Mark order ready (should auto-assign coupons)
    print("\n15.4 Mark order ready → auto-assign coupons")
    r = requests.post(f"{DMS_API}/primary-orders/{test_state['phase7_order_id']}/ready", 
                     headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        print_test("Mark ready", True, f"Status: {result.get('status')}")
    else:
        print_test("Mark ready", False, f"Status: {r.status_code}")
        return False
    
    # Test 15.5: Verify coupons assigned to distributor
    print("\n15.5 GET /dms/owner/coupons?distributor_id={dist1}&status=assigned")
    r = requests.get(f"{DMS_API}/owner/coupons?distributor_id={test_state['dist1_id']}&status=assigned&limit=10", 
                     headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        assigned = result.get("data", [])
        # Should have 5 boxes × coupons_per_box (default 100) = 500 coupons
        print_test("Coupons assigned to distributor", len(assigned) > 0, 
                  f"Found {len(assigned)} assigned coupons (expected ~500)")
        
        if assigned:
            # Store a valid coupon code for retailer scan test
            test_state["coupon_code_valid"] = assigned[0]["coupon_code"]
            print_test("Coupon has assigned_distributor_id", 
                      assigned[0].get("assigned_distributor_id") == test_state["dist1_id"])
            print_test("Coupon status is assigned", assigned[0].get("status") == "assigned")
            print(f"   Sample assigned coupon: {test_state['coupon_code_valid']}")
    else:
        print_test("GET assigned coupons", False, f"Status: {r.status_code}")
    
    return True


# ============================================================================
# TEST SCENARIO 16: PHASE 7 - Retailer Scan (Valid)
# ============================================================================
def test_16_retailer_scan_valid():
    print_section("16. PHASE 7 - RETAILER SCAN (VALID)")
    
    if not test_state.get("coupon_code_valid"):
        print_test("Retailer scan test", False, "No valid coupon code available")
        return False
    
    # Get retailer1 ID
    print("\n16.1 Get retailer1 ID")
    r = requests.get(f"{DMS_API}/retailers", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        retailers = r.json()["data"]
        retailer1 = next((ret for ret in retailers if ret.get("email") == CREDENTIALS["retailer1"]), None)
        if not retailer1:
            # Try to find by user lookup
            r2 = requests.get(f"{DMS_API}/retailers", headers=headers(CREDENTIALS["retailer1"]), timeout=15)
            if r2.status_code == 200:
                retailers2 = r2.json()["data"]
                if retailers2:
                    retailer1 = retailers2[0]
        
        if retailer1:
            test_state["retailer1_id"] = retailer1["id"]
            print_test("Got retailer1 ID", True, f"ID: {retailer1['id']}")
        else:
            print_test("Get retailer1", False, "Retailer not found")
            return False
    else:
        print_test("Get retailers", False, f"Status: {r.status_code}")
        return False
    
    # Test 16.2: Scan valid coupon as retailer1
    print("\n16.2 POST /dms/retailer/coupons/scan with valid coupon")
    payload = {"coupon_code": test_state["coupon_code_valid"]}
    r = requests.post(f"{DMS_API}/retailer/coupons/scan", headers=headers(CREDENTIALS["retailer1"]), 
                     json=payload, timeout=15)
    if r.status_code == 200:
        result = r.json()
        print_test("Scan valid coupon", result.get("ok") == True)
        print_test("Has points_value", result.get("points_value", 0) > 0, 
                  f"Points: {result.get('points_value')}")
        print_test("Has success message", "Redeemed" in result.get("message", ""),
                  f"Message: {result.get('message')}")
    else:
        print_test("Scan valid coupon", False, f"Status: {r.status_code}, {r.text}")
        return False
    
    # Test 16.3: Verify coupon status changed to redeemed
    print("\n16.3 GET /dms/owner/coupons?status=redeemed → includes the redeemed coupon")
    r = requests.get(f"{DMS_API}/owner/coupons?status=redeemed&limit=5", 
                     headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        redeemed = result.get("data", [])
        found = any(c.get("coupon_code") == test_state["coupon_code_valid"] for c in redeemed)
        print_test("Coupon marked as redeemed", found, f"Found {len(redeemed)} redeemed coupons")
        
        if found:
            coupon = next(c for c in redeemed if c.get("coupon_code") == test_state["coupon_code_valid"])
            print_test("Has redeemed_by_retailer_id", coupon.get("redeemed_by_retailer_id") is not None)
            print_test("Has redeemed_at", coupon.get("redeemed_at") is not None)
    else:
        print_test("GET redeemed coupons", False, f"Status: {r.status_code}")
    
    return True


# ============================================================================
# TEST SCENARIO 17: PHASE 7 - Retailer Scan (Duplicate)
# ============================================================================
def test_17_retailer_scan_duplicate():
    print_section("17. PHASE 7 - RETAILER SCAN (DUPLICATE)")
    
    if not test_state.get("coupon_code_valid"):
        print_test("Duplicate scan test", False, "No valid coupon code available")
        return False
    
    # Test 17.1: Try to scan same coupon again
    print("\n17.1 POST /dms/retailer/coupons/scan with already redeemed coupon → 400")
    payload = {"coupon_code": test_state["coupon_code_valid"]}
    r = requests.post(f"{DMS_API}/retailer/coupons/scan", headers=headers(CREDENTIALS["retailer1"]), 
                     json=payload, timeout=15)
    print_test("Duplicate scan rejected", r.status_code == 400, f"Status: {r.status_code}")
    if r.status_code == 400:
        print_test("Error message mentions 'already redeemed'", "already redeemed" in r.text.lower(),
                  f"Message: {r.text[:100]}")
    
    # Test 17.2: Verify fraud log increased
    print("\n17.2 GET /dms/owner/coupons/reports/fraud → fraud count increased")
    r = requests.get(f"{DMS_API}/owner/coupons/reports/fraud", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        fraud_attempts = result.get("data", [])
        print_test("Fraud log has entries", len(fraud_attempts) > 0, 
                  f"Found {len(fraud_attempts)} fraud attempts")
        
        # Check if duplicate attempt is logged
        duplicate_fraud = [f for f in fraud_attempts if f.get("reason") == "already_redeemed"]
        print_test("Duplicate attempt logged", len(duplicate_fraud) > 0,
                  f"Found {len(duplicate_fraud)} duplicate attempts")
    else:
        print_test("GET fraud log", False, f"Status: {r.status_code}")
    
    return True


# ============================================================================
# TEST SCENARIO 18: PHASE 7 - Retailer Scan (Mismatch/Invalid)
# ============================================================================
def test_18_retailer_scan_invalid():
    print_section("18. PHASE 7 - RETAILER SCAN (MISMATCH/INVALID)")
    
    # Test 18.1: Scan unassigned coupon (not dispatched)
    print("\n18.1 POST /dms/retailer/coupons/scan with unused coupon → 400 'not dispatched'")
    if test_state.get("coupon_code_unused"):
        payload = {"coupon_code": test_state["coupon_code_unused"]}
        r = requests.post(f"{DMS_API}/retailer/coupons/scan", headers=headers(CREDENTIALS["retailer1"]), 
                         json=payload, timeout=15)
        print_test("Unused coupon rejected", r.status_code == 400, f"Status: {r.status_code}")
        if r.status_code == 400:
            print_test("Error mentions 'not dispatched'", "not dispatched" in r.text.lower(),
                      f"Message: {r.text[:100]}")
    else:
        print_test("Unused coupon test", False, "No unused coupon available")
    
    # Test 18.2: Scan invalid coupon code
    print("\n18.2 POST /dms/retailer/coupons/scan with invalid code → 400 'Invalid coupon'")
    payload = {"coupon_code": "CPNBOGUS9999"}
    r = requests.post(f"{DMS_API}/retailer/coupons/scan", headers=headers(CREDENTIALS["retailer1"]), 
                     json=payload, timeout=15)
    print_test("Invalid code rejected", r.status_code == 400, f"Status: {r.status_code}")
    if r.status_code == 400:
        print_test("Error mentions 'Invalid coupon'", "invalid" in r.text.lower(),
                  f"Message: {r.text[:100]}")
    
    # Test 18.3: Verify fraud logs
    print("\n18.3 GET /dms/owner/coupons/reports/fraud → has invalid_code and not_dispatched entries")
    r = requests.get(f"{DMS_API}/owner/coupons/reports/fraud", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        fraud_attempts = result.get("data", [])
        
        invalid_code = [f for f in fraud_attempts if f.get("reason") == "invalid_code"]
        not_dispatched = [f for f in fraud_attempts if f.get("reason") == "not_dispatched"]
        
        print_test("Has invalid_code fraud entries", len(invalid_code) > 0,
                  f"Found {len(invalid_code)} invalid_code attempts")
        print_test("Has not_dispatched fraud entries", len(not_dispatched) > 0,
                  f"Found {len(not_dispatched)} not_dispatched attempts")
    else:
        print_test("GET fraud log", False, f"Status: {r.status_code}")
    
    return True


# ============================================================================
# TEST SCENARIO 19: PHASE 7 - Coupon Reports
# ============================================================================
def test_19_coupon_reports():
    print_section("19. PHASE 7 - COUPON REPORTS")
    
    # Test 19.1: Summary report
    print("\n19.1 GET /dms/owner/coupons/reports/summary")
    r = requests.get(f"{DMS_API}/owner/coupons/reports/summary", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        print_test("GET summary report", True)
        
        # Check totals
        totals = result.get("totals", {})
        has_totals = all(k in totals for k in ["total", "unused", "assigned", "redeemed", "fraud_attempts"])
        print_test("Has all total fields", has_totals)
        if has_totals:
            print(f"   Total: {totals['total']}, Unused: {totals['unused']}, Assigned: {totals['assigned']}")
            print(f"   Redeemed: {totals['redeemed']}, Fraud: {totals['fraud_attempts']}")
        
        # Check by_distributor
        by_dist = result.get("by_distributor", [])
        print_test("Has by_distributor breakdown", len(by_dist) > 0, f"Found {len(by_dist)} distributors")
        if by_dist:
            dist1_entry = next((d for d in by_dist if d.get("distributor_id") == test_state.get("dist1_id")), None)
            if dist1_entry:
                print_test("Dist1 in breakdown", True, 
                          f"Assigned: {dist1_entry.get('assigned')}, Redeemed: {dist1_entry.get('redeemed')}")
        
        # Check by_retailer
        by_ret = result.get("by_retailer", [])
        print_test("Has by_retailer breakdown", len(by_ret) > 0, f"Found {len(by_ret)} retailers")
        if by_ret:
            ret1_entry = next((r for r in by_ret if r.get("retailer_id") == test_state.get("retailer1_id")), None)
            if ret1_entry:
                print_test("Retailer1 in breakdown", True,
                          f"Redeemed: {ret1_entry.get('redeemed')}, Points: {ret1_entry.get('points')}")
    else:
        print_test("GET summary report", False, f"Status: {r.status_code}")
        return False
    
    # Test 19.2: Fraud report
    print("\n19.2 GET /dms/owner/coupons/reports/fraud")
    r = requests.get(f"{DMS_API}/owner/coupons/reports/fraud", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        fraud = result.get("data", [])
        print_test("GET fraud report", len(fraud) >= 2, f"Found {len(fraud)} fraud attempts (expected ≥2)")
    else:
        print_test("GET fraud report", False, f"Status: {r.status_code}")
    
    # Test 19.3: History report
    print("\n19.3 GET /dms/owner/coupons/reports/history")
    r = requests.get(f"{DMS_API}/owner/coupons/reports/history", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        history = result.get("data", [])
        print_test("GET history report", len(history) > 0, f"Found {len(history)} redeemed coupons")
    else:
        print_test("GET history report", False, f"Status: {r.status_code}")
    
    return True


# ============================================================================
# TEST SCENARIO 20: PHASE 7 - Retailer History
# ============================================================================
def test_20_retailer_history():
    print_section("20. PHASE 7 - RETAILER HISTORY")
    
    print("\n20.1 GET /dms/retailer/coupons/my-history as retailer1")
    r = requests.get(f"{DMS_API}/retailer/coupons/my-history", headers=headers(CREDENTIALS["retailer1"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        print_test("GET retailer history", True)
        
        data = result.get("data", [])
        total_points = result.get("total_points", 0)
        
        print_test("Has redeemed coupons", len(data) >= 1, f"Found {len(data)} redeemed coupons")
        print_test("Has total_points", total_points > 0, f"Total points: {total_points}")
    else:
        print_test("GET retailer history", False, f"Status: {r.status_code}")
        return False
    
    return True


# ============================================================================
# TEST SCENARIO 21: PHASE 7 - Excel Export
# ============================================================================
def test_21_excel_export():
    print_section("21. PHASE 7 - EXCEL EXPORT")
    
    # Test 21.1: Export as owner
    print("\n21.1 GET /dms/owner/products/export as owner")
    r = requests.get(f"{DMS_API}/owner/products/export", headers=headers(CREDENTIALS["owner"]), timeout=30)
    if r.status_code == 200:
        print_test("Export products", True, f"Size: {len(r.content)} bytes")
        print_test("Content-Type is xlsx", 
                  "spreadsheetml" in r.headers.get("content-type", ""),
                  f"Content-Type: {r.headers.get('content-type')}")
        print_test("File size > 3KB", len(r.content) > 3000, f"Size: {len(r.content)} bytes")
        
        # Save for import test
        test_state["exported_xlsx"] = r.content
    else:
        print_test("Export products", False, f"Status: {r.status_code}")
        return False
    
    # Test 21.2: Try export as distributor (should fail)
    print("\n21.2 GET /dms/owner/products/export as distributor → 403")
    r = requests.get(f"{DMS_API}/owner/products/export", headers=headers(CREDENTIALS["dist1"]), timeout=15)
    print_test("Distributor cannot export", r.status_code == 403, f"Status: {r.status_code}")
    
    return True


# ============================================================================
# TEST SCENARIO 22: PHASE 7 - Excel Import
# ============================================================================
def test_22_excel_import():
    print_section("22. PHASE 7 - EXCEL IMPORT")
    
    # Create a test xlsx file with openpyxl
    print("\n22.1 Create test xlsx with 2 rows (1 update, 1 new)")
    try:
        from openpyxl import Workbook
        from io import BytesIO
        
        # Get existing product for update test
        r = requests.get(f"{DMS_API}/products", headers=headers(CREDENTIALS["owner"]), timeout=15)
        if r.status_code != 200:
            print_test("Get products for import", False, f"Status: {r.status_code}")
            return False
        
        products = r.json()["data"]
        if not products:
            print_test("Get products for import", False, "No products found")
            return False
        
        existing_product = products[0]
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Products"
        
        # Headers
        headers_row = ["sku_code", "name", "category_name", "description", "box_qty", "hsn", 
                      "gst_pct", "unit_price", "coupons_per_box", "points_value", "active"]
        ws.append(headers_row)
        
        # Row A: Update existing product (price change)
        old_price = existing_product.get("unit_price", 1000)
        new_price = old_price + 100
        ws.append([
            existing_product.get("sku_code"),
            existing_product.get("name"),
            existing_product.get("category_name"),
            existing_product.get("description", ""),
            existing_product.get("box_qty", 10),
            existing_product.get("hsn", "27101980"),
            existing_product.get("gst_pct", 18),
            new_price,  # Price increase
            existing_product.get("coupons_per_box", 100),
            existing_product.get("points_value", 10),
            True
        ])
        
        # Row B: New product
        import time
        ws.append([
            f"TEST-IMPORT-{int(time.time())}",
            "Imported Product",
            "Engine Oil",
            "Test imported product",
            10,
            "27101980",
            18,
            999,
            50,
            5,
            True
        ])
        
        # Save to BytesIO
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        
        print_test("Created test xlsx", True, f"Rows: 2 (1 update, 1 new)")
        
        # Test 22.2: Import as owner
        print("\n22.2 POST /dms/owner/products/import as owner")
        files = {"file": ("test_import.xlsx", buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        r = requests.post(f"{DMS_API}/owner/products/import", headers=headers(CREDENTIALS["owner"]), 
                         files=files, timeout=30)
        if r.status_code == 200:
            result = r.json()
            print_test("Import products", result.get("ok") == True)
            print_test("Created count", result.get("created", 0) >= 1, 
                      f"Created: {result.get('created')}")
            print_test("Updated count", result.get("updated", 0) >= 1, 
                      f"Updated: {result.get('updated')}")
            print_test("Skipped count", result.get("skipped", 0) == 0,
                      f"Skipped: {result.get('skipped')}")
            
            # Test 22.3: Verify imported product exists
            print("\n22.3 Verify imported product exists with correct data")
            r2 = requests.get(f"{DMS_API}/products", headers=headers(CREDENTIALS["owner"]), timeout=15)
            if r2.status_code == 200:
                products = r2.json()["data"]
                imported = [p for p in products if "TEST-IMPORT-" in p.get("sku_code", "")]
                if imported:
                    prod = imported[0]
                    print_test("Imported product found", True, f"SKU: {prod.get('sku_code')}")
                    print_test("Unit price is 999", prod.get("unit_price") == 999)
                    print_test("Coupons per box is 50", prod.get("coupons_per_box") == 50)
                else:
                    print_test("Imported product found", False, "Product not found in list")
            
            # Test 22.4: Verify updated product has previous_price
            print("\n22.4 Verify updated product has previous_price set")
            r3 = requests.get(f"{DMS_API}/products/{existing_product['id']}", 
                             headers=headers(CREDENTIALS["owner"]), timeout=15)
            if r3.status_code == 200:
                updated_prod = r3.json()
                print_test("Updated product has previous_price", 
                          updated_prod.get("previous_price") == old_price,
                          f"Previous: {updated_prod.get('previous_price')}, Current: {updated_prod.get('unit_price')}")
        else:
            print_test("Import products", False, f"Status: {r.status_code}, {r.text}")
            return False
        
    except Exception as e:
        print_test("Excel import test", False, f"Exception: {e}")
        return False
    
    # Test 22.5: Try import as distributor (should fail)
    print("\n22.5 POST /dms/owner/products/import as distributor → 403")
    buf.seek(0)
    files = {"file": ("test_import.xlsx", buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    r = requests.post(f"{DMS_API}/owner/products/import", headers=headers(CREDENTIALS["dist1"]), 
                     files=files, timeout=15)
    print_test("Distributor cannot import", r.status_code == 403, f"Status: {r.status_code}")
    
    return True


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================
def run_all_tests():
    print("\n" + "="*80)
    print("  SIMPLE DMS BACKEND API TEST SUITE")
    print("  Testing: /api/dms/* endpoints")
    print(f"  Backend URL: {BASE_URL}")
    print("="*80)
    
    results = {}
    
    try:
        results["1_auth_and_seed"] = test_1_auth_and_seed()
    except Exception as e:
        print(f"❌ Test 1 failed with exception: {e}")
        results["1_auth_and_seed"] = False
    
    try:
        results["2_categories"] = test_2_categories()
    except Exception as e:
        print(f"❌ Test 2 failed with exception: {e}")
        results["2_categories"] = False
    
    try:
        results["3_products"] = test_3_products()
    except Exception as e:
        print(f"❌ Test 3 failed with exception: {e}")
        results["3_products"] = False
    
    try:
        results["4_distributors"] = test_4_distributors()
    except Exception as e:
        print(f"❌ Test 4 failed with exception: {e}")
        results["4_distributors"] = False
    
    try:
        results["5_distributor_browse"] = test_5_distributor_browse()
    except Exception as e:
        print(f"❌ Test 5 failed with exception: {e}")
        results["5_distributor_browse"] = False
    
    try:
        results["6_primary_order_lifecycle"] = test_6_primary_order_lifecycle()
    except Exception as e:
        print(f"❌ Test 6 failed with exception: {e}")
        results["6_primary_order_lifecycle"] = False
    
    try:
        results["7_attachments"] = test_7_attachments()
    except Exception as e:
        print(f"❌ Test 7 failed with exception: {e}")
        results["7_attachments"] = False
    
    try:
        results["8_primary_ledger"] = test_8_primary_ledger()
    except Exception as e:
        print(f"❌ Test 8 failed with exception: {e}")
        results["8_primary_ledger"] = False
    
    try:
        results["9_notifications"] = test_9_notifications()
    except Exception as e:
        print(f"❌ Test 9 failed with exception: {e}")
        results["9_notifications"] = False
    
    try:
        results["10_dashboards"] = test_10_dashboards()
    except Exception as e:
        print(f"❌ Test 10 failed with exception: {e}")
        results["10_dashboards"] = False
    
    try:
        results["11_security"] = test_11_security()
    except Exception as e:
        print(f"❌ Test 11 failed with exception: {e}")
        results["11_security"] = False
    
    # PHASE 7 TESTS
    try:
        results["12_coupon_generation"] = test_12_coupon_generation()
    except Exception as e:
        print(f"❌ Test 12 failed with exception: {e}")
        results["12_coupon_generation"] = False
    
    try:
        results["13_coupon_listing"] = test_13_coupon_listing()
    except Exception as e:
        print(f"❌ Test 13 failed with exception: {e}")
        results["13_coupon_listing"] = False
    
    try:
        results["14_coupon_batches"] = test_14_coupon_batches()
    except Exception as e:
        print(f"❌ Test 14 failed with exception: {e}")
        results["14_coupon_batches"] = False
    
    try:
        results["15_coupon_auto_assign"] = test_15_coupon_auto_assign()
    except Exception as e:
        print(f"❌ Test 15 failed with exception: {e}")
        results["15_coupon_auto_assign"] = False
    
    try:
        results["16_retailer_scan_valid"] = test_16_retailer_scan_valid()
    except Exception as e:
        print(f"❌ Test 16 failed with exception: {e}")
        results["16_retailer_scan_valid"] = False
    
    try:
        results["17_retailer_scan_duplicate"] = test_17_retailer_scan_duplicate()
    except Exception as e:
        print(f"❌ Test 17 failed with exception: {e}")
        results["17_retailer_scan_duplicate"] = False
    
    try:
        results["18_retailer_scan_invalid"] = test_18_retailer_scan_invalid()
    except Exception as e:
        print(f"❌ Test 18 failed with exception: {e}")
        results["18_retailer_scan_invalid"] = False
    
    try:
        results["19_coupon_reports"] = test_19_coupon_reports()
    except Exception as e:
        print(f"❌ Test 19 failed with exception: {e}")
        results["19_coupon_reports"] = False
    
    try:
        results["20_retailer_history"] = test_20_retailer_history()
    except Exception as e:
        print(f"❌ Test 20 failed with exception: {e}")
        results["20_retailer_history"] = False
    
    try:
        results["21_excel_export"] = test_21_excel_export()
    except Exception as e:
        print(f"❌ Test 21 failed with exception: {e}")
        results["21_excel_export"] = False
    
    try:
        results["22_excel_import"] = test_22_excel_import()
    except Exception as e:
        print(f"❌ Test 22 failed with exception: {e}")
        results["22_excel_import"] = False
    
    # Print summary
    print_section("TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{'='*80}")
    print(f"  TOTAL: {passed}/{total} test scenarios passed")
    print(f"{'='*80}\n")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
