#!/usr/bin/env python3
"""
Backend API Testing for GO OIL DMS Continuation Sprint
Tests 5 specific areas:
1. Owner stock column in order detail
2. Insufficient stock -> HTTP 409 + allow_oversell bypass
3. Backorder auto-create on mark-ready
4. Direct Team-Leader -> Salesperson assignment + hierarchy + visibility
5. Team-Leader tracking detail works for owner
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "http://localhost:8001/api"
OWNER_EMAIL = "gooilindia13@gmail.com"
OWNER_PASSWORD = "Arjun@india13"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def log(msg: str, color: str = Colors.RESET):
    print(f"{color}{msg}{Colors.RESET}")

def log_success(msg: str):
    log(f"✅ {msg}", Colors.GREEN)

def log_error(msg: str):
    log(f"❌ {msg}", Colors.RED)

def log_info(msg: str):
    log(f"ℹ️  {msg}", Colors.BLUE)

def log_warning(msg: str):
    log(f"⚠️  {msg}", Colors.YELLOW)

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_pass(self):
        self.passed += 1
    
    def add_fail(self, error: str):
        self.failed += 1
        self.errors.append(error)
    
    def summary(self):
        total = self.passed + self.failed
        log("\n" + "="*80)
        log(f"TEST SUMMARY: {self.passed}/{total} PASSED", 
            Colors.GREEN if self.failed == 0 else Colors.YELLOW)
        if self.errors:
            log("\nFAILED TESTS:", Colors.RED)
            for i, error in enumerate(self.errors, 1):
                log(f"{i}. {error}", Colors.RED)
        log("="*80 + "\n")
        return self.failed == 0

results = TestResults()

def login_owner() -> Optional[str]:
    """Login as owner and return JWT token"""
    log_info(f"Logging in as owner: {OWNER_EMAIL}")
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("token")
            user = data.get("user", {})
            log_success(f"Login successful - Role: {user.get('role')}, Tenant: {user.get('tenant_id')}")
            return token
        else:
            log_error(f"Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        log_error(f"Login exception: {str(e)}")
        return None

def get_headers(token: str) -> Dict[str, str]:
    """Get headers with authorization token"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

# ============================================================================
# TEST AREA 1: Owner stock column in order detail
# ============================================================================
def test_owner_stock_column(token: str):
    log("\n" + "="*80)
    log("TEST AREA 1: Owner stock column in order detail", Colors.BLUE)
    log("="*80)
    
    headers = get_headers(token)
    
    # Get list of primary orders
    log_info("Step 1: Getting list of primary orders...")
    try:
        response = requests.get(f"{BASE_URL}/dms/primary-orders", headers=headers, timeout=10)
        if response.status_code != 200:
            log_error(f"Failed to get orders: {response.status_code}")
            results.add_fail("Area 1: Failed to get primary orders list")
            return
        
        orders = response.json().get("data", [])
        if not orders:
            log_warning("No orders found. Creating a test order...")
            # Create a test order
            order_id = create_test_order(token)
            if not order_id:
                results.add_fail("Area 1: Could not create test order")
                return
        else:
            order_id = orders[0].get("id")
            log_success(f"Found {len(orders)} orders. Using order: {order_id}")
        
        # Get order detail
        log_info(f"Step 2: Getting order detail for {order_id}...")
        response = requests.get(f"{BASE_URL}/dms/primary-orders/{order_id}", headers=headers, timeout=10)
        
        if response.status_code != 200:
            log_error(f"Failed to get order detail: {response.status_code} - {response.text}")
            results.add_fail(f"Area 1: GET /primary-orders/{order_id} returned {response.status_code}")
            return
        
        order = response.json()
        items = order.get("items", [])
        
        if not items:
            log_error("Order has no items")
            results.add_fail("Area 1: Order has no items")
            return
        
        log_info(f"Order has {len(items)} items. Checking for owner_stock_boxes field...")
        
        all_have_stock = True
        for i, item in enumerate(items, 1):
            product_name = item.get("product_name", "Unknown")
            owner_stock = item.get("owner_stock_boxes")
            
            if owner_stock is None:
                log_error(f"Item {i} ({product_name}): owner_stock_boxes field MISSING")
                all_have_stock = False
            else:
                log_success(f"Item {i} ({product_name}): owner_stock_boxes = {owner_stock}")
        
        if all_have_stock:
            log_success("✅ AREA 1 PASSED: All items have owner_stock_boxes field")
            results.add_pass()
        else:
            log_error("❌ AREA 1 FAILED: Some items missing owner_stock_boxes field")
            results.add_fail("Area 1: owner_stock_boxes field missing in some items")
    
    except Exception as e:
        log_error(f"Exception in test_owner_stock_column: {str(e)}")
        results.add_fail(f"Area 1: Exception - {str(e)}")

def create_test_order(token: str) -> Optional[str]:
    """Create a test order for testing"""
    headers = get_headers(token)
    
    # Get a distributor
    response = requests.get(f"{BASE_URL}/dms/distributors", headers=headers, timeout=10)
    if response.status_code != 200:
        log_error("Failed to get distributors")
        return None
    
    distributors = response.json().get("data", [])
    if not distributors:
        log_error("No distributors found")
        return None
    
    distributor = distributors[0]
    distributor_id = distributor.get("id")
    distributor_email = distributor.get("email")
    
    # Get products
    response = requests.get(f"{BASE_URL}/dms/products", headers=headers, timeout=10)
    if response.status_code != 200:
        log_error("Failed to get products")
        return None
    
    products = response.json().get("data", [])
    if not products:
        log_error("No products found")
        return None
    
    product = products[0]
    
    # Login as distributor to create order
    dist_login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": distributor_email, "password": "Test@2026"},  # Try Test@2026 first
        timeout=10
    )
    
    if dist_login_response.status_code != 200:
        # Try Demo@2026 as fallback
        dist_login_response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": distributor_email, "password": "Demo@2026"},
            timeout=10
        )
    
    if dist_login_response.status_code != 200:
        log_error(f"Failed to login as distributor: {dist_login_response.status_code}")
        return None
    
    dist_token = dist_login_response.json().get("token")
    dist_headers = get_headers(dist_token)
    
    # Create order as distributor
    order_data = {
        "items": [
            {
                "product_id": product.get("id"),
                "qty_boxes": 5
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/dms/primary-orders", json=order_data, headers=dist_headers, timeout=10)
    if response.status_code == 200:
        order = response.json()
        order_id = order.get("id")
        log_success(f"Created test order: {order_id}")
        return order_id
    else:
        log_error(f"Failed to create order: {response.status_code} - {response.text}")
        return None

# ============================================================================
# TEST AREA 2: Insufficient stock -> HTTP 409 + allow_oversell bypass
# ============================================================================
def test_insufficient_stock_and_oversell(token: str):
    log("\n" + "="*80)
    log("TEST AREA 2: Insufficient stock -> HTTP 409 + allow_oversell bypass", Colors.BLUE)
    log("="*80)
    
    headers = get_headers(token)
    
    try:
        # Step 1: Get owner inventory to find a product
        log_info("Step 1: Getting owner inventory...")
        response = requests.get(f"{BASE_URL}/dms/owner/inventory", headers=headers, timeout=10)
        if response.status_code != 200:
            log_error(f"Failed to get inventory: {response.status_code}")
            results.add_fail("Area 2: Failed to get owner inventory")
            return
        
        inventory = response.json().get("data", [])
        if not inventory:
            log_error("No inventory found")
            results.add_fail("Area 2: No inventory found")
            return
        
        # Find a product with some stock
        test_product = None
        for item in inventory:
            stock = item.get("stock_boxes") or item.get("qty_boxes", 0)
            if stock > 0:
                test_product = item
                break
        
        if not test_product:
            log_error("No products with stock found")
            results.add_fail("Area 2: No products with stock")
            return
        
        product_id = test_product.get("product_id")
        current_stock = test_product.get("stock_boxes") or test_product.get("qty_boxes", 0)
        product_name = test_product.get("product_name", "Unknown")
        
        log_success(f"Found product: {product_name} (ID: {product_id}) with stock: {current_stock} boxes")
        
        # Step 2: Adjust stock to a low value (e.g., 2 boxes)
        log_info("Step 2: Adjusting stock to low value (2 boxes)...")
        target_stock = 2
        delta = target_stock - current_stock
        
        if delta != 0:
            adjust_data = {
                "product_id": product_id,
                "delta_boxes": delta,
                "reason": "Test setup - setting low stock"
            }
            
            response = requests.post(f"{BASE_URL}/dms/owner/inventory/adjust", json=adjust_data, headers=headers, timeout=10)
            if response.status_code != 200:
                log_error(f"Failed to adjust inventory: {response.status_code}")
                results.add_fail("Area 2: Failed to adjust inventory")
                return
            
            log_success(f"Stock adjusted to {target_stock} boxes")
        else:
            log_success(f"Stock already at target value: {target_stock} boxes")
        
        # Step 3: Check settings for stop_sale_on_negative
        log_info("Step 3: Checking settings for stop_sale_on_negative...")
        response = requests.get(f"{BASE_URL}/dms/settings", headers=headers, timeout=10)
        if response.status_code == 200:
            settings = response.json()
            stop_sale = settings.get("stop_sale_on_negative", True)
            log_info(f"stop_sale_on_negative = {stop_sale}")
        
        # Step 4: Create or find a pending order
        log_info("Step 4: Finding or creating a pending order...")
        response = requests.get(f"{BASE_URL}/dms/primary-orders?status=pending", headers=headers, timeout=10)
        
        orders = response.json().get("data", [])
        order_id = None
        
        # Find an order with our test product
        for order in orders:
            items = order.get("items", [])
            for item in items:
                if item.get("product_id") == product_id:
                    order_id = order.get("id")
                    break
            if order_id:
                break
        
        if not order_id:
            # Create a new order as distributor
            log_info("Creating a new test order as distributor...")
            distributors_resp = requests.get(f"{BASE_URL}/dms/distributors", headers=headers, timeout=10)
            distributors = distributors_resp.json().get("data", [])
            if not distributors:
                log_error("No distributors found")
                results.add_fail("Area 2: No distributors found")
                return
            
            distributor = distributors[0]
            distributor_email = distributor.get("email")
            
            # Login as distributor
            dist_login_response = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": distributor_email, "password": "Test@2026"},
                timeout=10
            )
            
            if dist_login_response.status_code != 200:
                # Try Demo@2026 as fallback
                dist_login_response = requests.post(
                    f"{BASE_URL}/auth/login",
                    json={"email": distributor_email, "password": "Demo@2026"},
                    timeout=10
                )
            
            if dist_login_response.status_code != 200:
                log_error(f"Failed to login as distributor: {dist_login_response.status_code}")
                results.add_fail("Area 2: Failed to login as distributor")
                return
            
            dist_token = dist_login_response.json().get("token")
            dist_headers = get_headers(dist_token)
            
            order_data = {
                "items": [
                    {
                        "product_id": product_id,
                        "qty_boxes": 10  # More than stock
                    }
                ]
            }
            
            response = requests.post(f"{BASE_URL}/dms/primary-orders", json=order_data, headers=dist_headers, timeout=10)
            if response.status_code == 200:
                order = response.json()
                order_id = order.get("id")
                log_success(f"Created test order: {order_id}")
            else:
                log_error(f"Failed to create order: {response.status_code}")
                results.add_fail("Area 2: Failed to create test order")
                return
        else:
            log_success(f"Using existing order: {order_id}")
        
        # Step 5: Try to fulfill more than stock (should get 409)
        log_info(f"Step 5: Attempting to fulfill {target_stock + 5} boxes (more than stock of {target_stock})...")
        
        fulfill_data = {
            "product_id": product_id,
            "qty_boxes_fulfilled": target_stock + 5  # More than available stock
        }
        
        response = requests.post(
            f"{BASE_URL}/dms/primary-orders/{order_id}/fulfill-line",
            json=fulfill_data,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 409:
            error_detail = response.json().get("detail", "")
            if "Insufficient owner stock" in error_detail or "insufficient" in error_detail.lower():
                log_success(f"✅ Got expected 409 error: {error_detail}")
            else:
                log_warning(f"Got 409 but unexpected message: {error_detail}")
        else:
            log_error(f"Expected 409, got {response.status_code}: {response.text}")
            results.add_fail(f"Area 2: Expected 409 for insufficient stock, got {response.status_code}")
            return
        
        # Step 6: Try again with allow_oversell=true (should succeed)
        log_info("Step 6: Attempting same fulfillment with allow_oversell=true...")
        
        fulfill_data["allow_oversell"] = True
        
        response = requests.post(
            f"{BASE_URL}/dms/primary-orders/{order_id}/fulfill-line",
            json=fulfill_data,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            order = response.json()
            status = order.get("status")
            log_success(f"✅ Fulfillment succeeded with allow_oversell=true. Order status: {status}")
            
            # Verify the line was fulfilled
            items = order.get("items", [])
            fulfilled_item = None
            for item in items:
                if item.get("product_id") == product_id:
                    fulfilled_item = item
                    break
            
            if fulfilled_item:
                qty_fulfilled = fulfilled_item.get("qty_boxes_fulfilled", 0)
                log_success(f"Product fulfilled quantity: {qty_fulfilled} boxes")
            
            log_success("✅ AREA 2 PASSED: Insufficient stock returns 409, allow_oversell bypass works")
            results.add_pass()
        else:
            log_error(f"Expected 200 with allow_oversell, got {response.status_code}: {response.text}")
            results.add_fail(f"Area 2: allow_oversell=true failed with {response.status_code}")
    
    except Exception as e:
        log_error(f"Exception in test_insufficient_stock_and_oversell: {str(e)}")
        results.add_fail(f"Area 2: Exception - {str(e)}")

# ============================================================================
# TEST AREA 3: Backorder auto-create on mark-ready
# ============================================================================
def test_backorder_creation(token: str):
    log("\n" + "="*80)
    log("TEST AREA 3: Backorder auto-create on mark-ready", Colors.BLUE)
    log("="*80)
    
    headers = get_headers(token)
    
    try:
        # Step 1: Create a new order with partial fulfillment
        log_info("Step 1: Creating a new order for backorder testing...")
        
        # Get distributor and products
        distributors_resp = requests.get(f"{BASE_URL}/dms/distributors", headers=headers, timeout=10)
        distributors = distributors_resp.json().get("data", [])
        if not distributors:
            log_error("No distributors found")
            results.add_fail("Area 3: No distributors found")
            return
        
        distributor = distributors[0]
        distributor_email = distributor.get("email")
        
        products_resp = requests.get(f"{BASE_URL}/dms/products", headers=headers, timeout=10)
        products = products_resp.json().get("data", [])
        if len(products) < 1:
            log_error("Not enough products found")
            results.add_fail("Area 3: Not enough products")
            return
        
        product = products[0]
        product_id = product.get("id")
        product_name = product.get("name", "Unknown")
        
        # Login as distributor
        dist_login_response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": distributor_email, "password": "Test@2026"},
            timeout=10
        )
        
        if dist_login_response.status_code != 200:
            # Try Demo@2026 as fallback
            dist_login_response = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": distributor_email, "password": "Demo@2026"},
                timeout=10
            )
        
        if dist_login_response.status_code != 200:
            log_error(f"Failed to login as distributor: {dist_login_response.status_code}")
            results.add_fail("Area 3: Failed to login as distributor")
            return
        
        dist_token = dist_login_response.json().get("token")
        dist_headers = get_headers(dist_token)
        
        # Create order as distributor
        order_data = {
            "items": [
                {
                    "product_id": product_id,
                    "qty_boxes": 10  # Order 10 boxes
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/dms/primary-orders", json=order_data, headers=dist_headers, timeout=10)
        if response.status_code != 200:
            log_error(f"Failed to create order: {response.status_code}")
            results.add_fail("Area 3: Failed to create test order")
            return
        
        order = response.json()
        order_id = order.get("id")
        order_no = order.get("order_no")
        log_success(f"Created order: {order_no} (ID: {order_id})")
        
        # Step 2: Partially fulfill the order (e.g., fulfill 4 out of 10)
        log_info("Step 2: Partially fulfilling order (4 out of 10 boxes)...")
        
        fulfill_data = {
            "product_id": product_id,
            "qty_boxes_fulfilled": 4,
            "allow_oversell": True  # In case stock is low
        }
        
        response = requests.post(
            f"{BASE_URL}/dms/primary-orders/{order_id}/fulfill-line",
            json=fulfill_data,
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            log_error(f"Failed to fulfill line: {response.status_code} - {response.text}")
            results.add_fail("Area 3: Failed to fulfill line")
            return
        
        order = response.json()
        status = order.get("status")
        log_success(f"Order partially fulfilled. Status: {status}")
        
        # Step 3: Mark order as ready (should create backorder)
        log_info("Step 3: Marking order as ready (should create backorder)...")
        
        response = requests.post(
            f"{BASE_URL}/dms/primary-orders/{order_id}/ready",
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            log_error(f"Failed to mark ready: {response.status_code} - {response.text}")
            results.add_fail(f"Area 3: Mark ready failed with {response.status_code}")
            return
        
        ready_response = response.json()
        has_backorder = ready_response.get("has_backorder", False)
        backorder_id = ready_response.get("backorder_id")
        
        log_info(f"Mark ready response: has_backorder={has_backorder}, backorder_id={backorder_id}")
        
        if not has_backorder:
            log_error("Response does not indicate backorder was created")
            results.add_fail("Area 3: has_backorder=false in response")
            return
        
        if not backorder_id:
            log_error("No backorder_id in response")
            results.add_fail("Area 3: backorder_id missing in response")
            return
        
        log_success(f"✅ Backorder created: {backorder_id}")
        
        # Step 4: Verify the backorder exists
        log_info("Step 4: Verifying backorder exists...")
        
        response = requests.get(f"{BASE_URL}/dms/primary-orders/{backorder_id}", headers=headers, timeout=10)
        if response.status_code != 200:
            log_error(f"Failed to get backorder: {response.status_code}")
            results.add_fail("Area 3: Backorder not found")
            return
        
        backorder = response.json()
        is_backorder = backorder.get("is_backorder", False)
        backorder_of = backorder.get("backorder_of")
        backorder_status = backorder.get("status")
        backorder_no = backorder.get("order_no")
        
        log_info(f"Backorder details: order_no={backorder_no}, is_backorder={is_backorder}, backorder_of={backorder_of}, status={backorder_status}")
        
        # Verify backorder properties
        checks_passed = True
        
        if not is_backorder:
            log_error("is_backorder is not True")
            checks_passed = False
        else:
            log_success("✅ is_backorder = True")
        
        if backorder_of != order_id:
            log_error(f"backorder_of ({backorder_of}) does not match original order ({order_id})")
            checks_passed = False
        else:
            log_success(f"✅ backorder_of = {order_id}")
        
        if backorder_status != "pending":
            log_error(f"Backorder status is {backorder_status}, expected 'pending'")
            checks_passed = False
        else:
            log_success("✅ status = pending")
        
        if not backorder_no.endswith("-B"):
            log_error(f"Backorder order_no ({backorder_no}) does not end with '-B'")
            checks_passed = False
        else:
            log_success(f"✅ order_no ends with '-B': {backorder_no}")
        
        # Check backorder quantities
        backorder_items = backorder.get("items", [])
        if backorder_items:
            item = backorder_items[0]
            qty_ordered = item.get("qty_boxes_ordered", 0)
            expected_qty = 10 - 4  # Original 10 - fulfilled 4 = 6
            
            if qty_ordered == expected_qty:
                log_success(f"✅ Backorder quantity correct: {qty_ordered} boxes (10 - 4)")
            else:
                log_error(f"Backorder quantity incorrect: {qty_ordered}, expected {expected_qty}")
                checks_passed = False
        
        # Step 5: Try to mark ready again (should not create duplicate backorder)
        log_info("Step 5: Attempting to mark ready again (should fail - already ready)...")
        
        response = requests.post(
            f"{BASE_URL}/dms/primary-orders/{order_id}/ready",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 400:
            log_success("✅ Second mark-ready correctly rejected (400)")
        else:
            log_warning(f"Second mark-ready returned {response.status_code} (expected 400)")
        
        # Step 6: Verify only ONE backorder exists for this order
        log_info("Step 6: Verifying only ONE backorder exists for original order...")
        
        response = requests.get(f"{BASE_URL}/dms/primary-orders", headers=headers, timeout=10)
        all_orders = response.json().get("data", [])
        
        backorders_for_original = [
            o for o in all_orders 
            if o.get("backorder_of") == order_id
        ]
        
        if len(backorders_for_original) == 1:
            log_success(f"✅ Exactly ONE backorder found for original order")
        else:
            log_error(f"Found {len(backorders_for_original)} backorders, expected 1")
            checks_passed = False
        
        if checks_passed:
            log_success("✅ AREA 3 PASSED: Backorder auto-creation works correctly")
            results.add_pass()
        else:
            log_error("❌ AREA 3 FAILED: Some backorder checks failed")
            results.add_fail("Area 3: Backorder validation checks failed")
    
    except Exception as e:
        log_error(f"Exception in test_backorder_creation: {str(e)}")
        results.add_fail(f"Area 3: Exception - {str(e)}")

# ============================================================================
# TEST AREA 4: Direct Team-Leader -> Salesperson assignment + hierarchy
# ============================================================================
def test_tl_sp_assignment(token: str):
    log("\n" + "="*80)
    log("TEST AREA 4: Direct Team-Leader -> Salesperson assignment + hierarchy", Colors.BLUE)
    log("="*80)
    
    headers = get_headers(token)
    
    try:
        # Step 1: Get team leaders and salespersons
        log_info("Step 1: Getting team leaders...")
        response = requests.get(f"{BASE_URL}/dms/owner/users?role=team_leader", headers=headers, timeout=10)
        if response.status_code != 200:
            log_error(f"Failed to get team leaders: {response.status_code}")
            results.add_fail("Area 4: Failed to get team leaders")
            return
        
        team_leaders = response.json().get("data", [])
        if not team_leaders:
            log_error("No team leaders found")
            results.add_fail("Area 4: No team leaders found")
            return
        
        tl = team_leaders[0]
        tl_id = tl.get("id")
        tl_name = tl.get("name", "Unknown")
        log_success(f"Found team leader: {tl_name} (ID: {tl_id})")
        
        log_info("Step 2: Getting salespersons...")
        response = requests.get(f"{BASE_URL}/dms/owner/users?role=salesperson", headers=headers, timeout=10)
        if response.status_code != 200:
            log_error(f"Failed to get salespersons: {response.status_code}")
            results.add_fail("Area 4: Failed to get salespersons")
            return
        
        salespersons = response.json().get("data", [])
        if not salespersons:
            log_error("No salespersons found")
            results.add_fail("Area 4: No salespersons found")
            return
        
        sp = salespersons[0]
        sp_id = sp.get("id")
        sp_name = sp.get("name", "Unknown")
        log_success(f"Found salesperson: {sp_name} (ID: {sp_id})")
        
        # Step 2: Assign salesperson to team leader
        log_info("Step 3: Assigning salesperson to team leader...")
        
        assign_data = {
            "team_leader_id": tl_id,
            "salesperson_id": sp_id
        }
        
        response = requests.post(
            f"{BASE_URL}/dms/assignments/tl-salespersons",
            json=assign_data,
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            log_error(f"Failed to assign: {response.status_code} - {response.text}")
            results.add_fail(f"Area 4: TL-SP assignment failed with {response.status_code}")
            return
        
        log_success(f"✅ Successfully assigned {sp_name} to {tl_name}")
        
        # Step 3: Verify assignment in hierarchy
        log_info("Step 4: Checking hierarchy for assignment...")
        
        response = requests.get(f"{BASE_URL}/dms/owner/hierarchy", headers=headers, timeout=10)
        if response.status_code != 200:
            log_error(f"Failed to get hierarchy: {response.status_code}")
            results.add_fail("Area 4: Failed to get hierarchy")
            return
        
        hierarchy = response.json()
        
        # Check if hierarchy has expected structure
        tree = hierarchy.get("tree", [])
        unassigned_tls = hierarchy.get("unassigned_team_leaders", [])
        
        log_info(f"Hierarchy has {len(tree)} regional managers, {len(unassigned_tls)} unassigned TLs")
        
        # Find the TL in hierarchy
        tl_found = False
        sp_in_tl = False
        
        # Check in tree
        for rm in tree:
            team_leaders_in_rm = rm.get("team_leaders", [])
            for tl_node in team_leaders_in_rm:
                if tl_node.get("id") == tl_id:
                    tl_found = True
                    salespersons_in_tl = tl_node.get("salespersons", [])
                    log_info(f"Found TL in tree with {len(salespersons_in_tl)} salespersons")
                    
                    for sp_node in salespersons_in_tl:
                        if sp_node.get("id") == sp_id:
                            sp_in_tl = True
                            log_success(f"✅ Found {sp_name} in {tl_name}'s salespersons array")
                            break
                    break
        
        # Check in unassigned TLs
        if not tl_found:
            for tl_node in unassigned_tls:
                if tl_node.get("id") == tl_id:
                    tl_found = True
                    salespersons_in_tl = tl_node.get("salespersons", [])
                    log_info(f"Found TL in unassigned_team_leaders with {len(salespersons_in_tl)} salespersons")
                    
                    for sp_node in salespersons_in_tl:
                        if sp_node.get("id") == sp_id:
                            sp_in_tl = True
                            log_success(f"✅ Found {sp_name} in {tl_name}'s salespersons array")
                            break
                    break
        
        if not tl_found:
            log_error(f"Team leader {tl_name} not found in hierarchy")
            results.add_fail("Area 4: TL not found in hierarchy")
            return
        
        if not sp_in_tl:
            log_error(f"Salesperson {sp_name} not found in TL's salespersons array")
            results.add_fail("Area 4: SP not in TL's salespersons array")
            return
        
        # Step 4: Test DELETE assignment
        log_info("Step 5: Testing DELETE assignment...")
        
        response = requests.delete(
            f"{BASE_URL}/dms/assignments/tl-salespersons?team_leader_id={tl_id}&salesperson_id={sp_id}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            log_error(f"Failed to delete assignment: {response.status_code}")
            results.add_fail(f"Area 4: DELETE assignment failed with {response.status_code}")
            return
        
        log_success("✅ Successfully deleted assignment")
        
        # Verify deletion in hierarchy
        log_info("Step 6: Verifying deletion in hierarchy...")
        
        response = requests.get(f"{BASE_URL}/dms/owner/hierarchy", headers=headers, timeout=10)
        hierarchy = response.json()
        
        tree = hierarchy.get("tree", [])
        unassigned_tls = hierarchy.get("unassigned_team_leaders", [])
        
        sp_still_in_tl = False
        
        # Check in tree
        for rm in tree:
            team_leaders_in_rm = rm.get("team_leaders", [])
            for tl_node in team_leaders_in_rm:
                if tl_node.get("id") == tl_id:
                    salespersons_in_tl = tl_node.get("salespersons", [])
                    for sp_node in salespersons_in_tl:
                        if sp_node.get("id") == sp_id:
                            sp_still_in_tl = True
                            break
        
        # Check in unassigned TLs
        for tl_node in unassigned_tls:
            if tl_node.get("id") == tl_id:
                salespersons_in_tl = tl_node.get("salespersons", [])
                for sp_node in salespersons_in_tl:
                    if sp_node.get("id") == sp_id:
                        sp_still_in_tl = True
                        break
        
        if sp_still_in_tl:
            log_error("Salesperson still appears in TL's salespersons array after deletion")
            results.add_fail("Area 4: SP still in hierarchy after DELETE")
            return
        else:
            log_success("✅ Salesperson no longer in TL's salespersons array")
        
        log_success("✅ AREA 4 PASSED: TL-SP assignment and hierarchy working correctly")
        results.add_pass()
    
    except Exception as e:
        log_error(f"Exception in test_tl_sp_assignment: {str(e)}")
        results.add_fail(f"Area 4: Exception - {str(e)}")

# ============================================================================
# TEST AREA 5: Team-Leader tracking detail works for owner
# ============================================================================
def test_tl_tracking_detail(token: str):
    log("\n" + "="*80)
    log("TEST AREA 5: Team-Leader tracking detail works for owner", Colors.BLUE)
    log("="*80)
    
    headers = get_headers(token)
    
    try:
        # Step 1: Get a team leader
        log_info("Step 1: Getting team leader user...")
        response = requests.get(f"{BASE_URL}/dms/owner/users?role=team_leader", headers=headers, timeout=10)
        if response.status_code != 200:
            log_error(f"Failed to get team leaders: {response.status_code}")
            results.add_fail("Area 5: Failed to get team leaders")
            return
        
        team_leaders = response.json().get("data", [])
        if not team_leaders:
            log_error("No team leaders found")
            results.add_fail("Area 5: No team leaders found")
            return
        
        tl = team_leaders[0]
        tl_user_id = tl.get("id")
        tl_name = tl.get("name", "Unknown")
        log_success(f"Found team leader: {tl_name} (User ID: {tl_user_id})")
        
        # Step 2: Call tracking detail endpoint for TL
        log_info(f"Step 2: Getting tracking detail for TL user {tl_user_id}...")
        
        response = requests.get(
            f"{BASE_URL}/dms/tracking/salesperson/{tl_user_id}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 404:
            log_error(f"Got 404 - endpoint not found or TL not trackable")
            results.add_fail(f"Area 5: GET tracking/salesperson/{tl_user_id} returned 404")
            return
        
        if response.status_code == 403:
            log_error(f"Got 403 - owner forbidden from accessing TL tracking")
            results.add_fail(f"Area 5: GET tracking/salesperson/{tl_user_id} returned 403")
            return
        
        if response.status_code != 200:
            log_error(f"Unexpected status code: {response.status_code} - {response.text}")
            results.add_fail(f"Area 5: GET tracking/salesperson/{tl_user_id} returned {response.status_code}")
            return
        
        tracking_data = response.json()
        
        log_success(f"✅ Got 200 response for TL tracking detail")
        
        # Verify expected structure
        log_info("Step 3: Verifying response structure...")
        
        expected_keys = ["route", "punch", "working_hours"]
        missing_keys = []
        
        for key in expected_keys:
            if key not in tracking_data:
                missing_keys.append(key)
            else:
                value = tracking_data[key]
                log_success(f"✅ Field '{key}' present: {type(value).__name__}")
        
        if missing_keys:
            log_error(f"Missing expected keys: {missing_keys}")
            results.add_fail(f"Area 5: Missing keys in response: {missing_keys}")
            return
        
        # Check route structure (can be empty array)
        route = tracking_data.get("route", [])
        log_info(f"Route has {len(route)} points (empty is OK)")
        
        # Step 4: Regression check - verify live tracking still works
        log_info("Step 4: Regression check - GET /tracking/live...")
        
        response = requests.get(f"{BASE_URL}/dms/tracking/live", headers=headers, timeout=10)
        if response.status_code != 200:
            log_error(f"Live tracking failed: {response.status_code}")
            results.add_fail("Area 5: Regression - live tracking broken")
            return
        
        live_data = response.json()
        
        expected_live_keys = ["salespersons", "distributors", "retailers", "team_leaders", "field_staff"]
        missing_live_keys = []
        
        for key in expected_live_keys:
            if key not in live_data:
                missing_live_keys.append(key)
            else:
                count = len(live_data[key]) if isinstance(live_data[key], list) else "N/A"
                log_success(f"✅ Live tracking has '{key}': {count} items")
        
        if missing_live_keys:
            log_error(f"Live tracking missing keys: {missing_live_keys}")
            results.add_fail(f"Area 5: Live tracking missing keys: {missing_live_keys}")
            return
        
        log_success("✅ AREA 5 PASSED: TL tracking detail works for owner, live tracking intact")
        results.add_pass()
    
    except Exception as e:
        log_error(f"Exception in test_tl_tracking_detail: {str(e)}")
        results.add_fail(f"Area 5: Exception - {str(e)}")

# ============================================================================
# SETUP TEST DATA
# ============================================================================
def setup_test_data(token: str) -> Dict[str, Any]:
    """Create minimal test data needed for testing"""
    log("\n" + "="*80)
    log("SETUP: Creating test data", Colors.BLUE)
    log("="*80)
    
    headers = get_headers(token)
    test_data = {}
    
    try:
        # Create a category
        log_info("Creating test category...")
        category_data = {
            "name": "Test Category",
            "description": "Test category for API testing"
        }
        response = requests.post(f"{BASE_URL}/dms/categories", json=category_data, headers=headers, timeout=10)
        if response.status_code == 200:
            category = response.json()
            test_data["category_id"] = category.get("id")
            log_success(f"Created category: {category.get('id')}")
        else:
            log_warning(f"Category creation returned {response.status_code}")
        
        # Create a product
        log_info("Creating test product...")
        import time
        unique_sku = f"TEST-{int(time.time())}"
        product_data = {
            "name": "Test Product",
            "sku_code": unique_sku,
            "category_id": test_data.get("category_id"),
            "material_description": "Test Material",
            "grade_specs": "Test Grade",
            "pack_size": "1 L",
            "box_qty": 12,
            "unit_price": 100.0,
            "hsn": "27101980",
            "gst_pct": 18.0,
            "active": True
        }
        response = requests.post(f"{BASE_URL}/dms/products", json=product_data, headers=headers, timeout=10)
        if response.status_code == 200:
            product = response.json()
            test_data["product_id"] = product.get("id")
            log_success(f"Created product: {product.get('id')}")
        else:
            log_warning(f"Product creation returned {response.status_code}: {response.text}")
        
        # Add inventory
        if test_data.get("product_id"):
            log_info("Adding inventory...")
            inventory_data = {
                "product_id": test_data["product_id"],
                "delta_boxes": 50,
                "reason": "Initial test stock"
            }
            response = requests.post(f"{BASE_URL}/dms/owner/inventory/adjust", json=inventory_data, headers=headers, timeout=10)
            if response.status_code == 200:
                log_success("Added 50 boxes to inventory")
            else:
                log_warning(f"Inventory adjustment returned {response.status_code}")
            
            # Make product visible to all distributors
            log_info("Setting product visibility for all distributors...")
            # Get all distributors
            dist_resp = requests.get(f"{BASE_URL}/dms/distributors", headers=headers, timeout=10)
            if dist_resp.status_code == 200:
                all_distributors = dist_resp.json().get("data", [])
                for dist in all_distributors:
                    dist_id = dist.get("id")
                    visibility_data = {
                        "product_id": test_data["product_id"],
                        "visible": True
                    }
                    vis_resp = requests.put(
                        f"{BASE_URL}/dms/distributors/{dist_id}/visibility",
                        json=visibility_data,
                        headers=headers,
                        timeout=10
                    )
                    if vis_resp.status_code == 200:
                        log_success(f"Product visible to distributor {dist_id}")
                    else:
                        log_warning(f"Visibility update returned {vis_resp.status_code}")
        
        # Use existing distributor or create a new one
        log_info("Checking for existing distributors...")
        dist_resp = requests.get(f"{BASE_URL}/dms/distributors", headers=headers, timeout=10)
        if dist_resp.status_code == 200:
            existing_dists = dist_resp.json().get("data", [])
            if existing_dists:
                test_data["distributor_id"] = existing_dists[0].get("id")
                log_success(f"Using existing distributor: {test_data['distributor_id']}")
            else:
                # Create a distributor only if none exist
                log_info("Creating test distributor...")
                distributor_data = {
                    "name": "Test Distributor",
                    "email": "testdist@test.com",
                    "password": "Test@2026",
                    "phone": "+91-9999999999",
                    "address": "Test Address",
                    "region": "Test Region",
                    "city": "Test City",
                    "state": "Test State",
                    "pincode": "123456",
                    "gstin": "29ABCDE1234F1Z5",
                    "pan": "ABCDE1234F",
                    "shop_license": "TEST-LIC-123",
                    "bank_name": "Test Bank",
                    "bank_account": "1234567890",
                    "bank_ifsc": "TEST0001234",
                    "credit_limit": 100000.0,
                    "documents": [{"type": "gstin", "url": "https://example.com/doc.pdf"}]
                }
                response = requests.post(f"{BASE_URL}/dms/distributors", json=distributor_data, headers=headers, timeout=10)
                if response.status_code == 200:
                    distributor = response.json()
                    test_data["distributor_id"] = distributor.get("id")
                    log_success(f"Created distributor: {distributor.get('id')}")
                else:
                    log_warning(f"Distributor creation returned {response.status_code}: {response.text}")
        
        log_success("✅ Test data setup complete")
        return test_data
    
    except Exception as e:
        log_error(f"Exception in setup_test_data: {str(e)}")
        return test_data

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================
def main():
    log("\n" + "="*80)
    log("GO OIL DMS CONTINUATION SPRINT - BACKEND API TESTING", Colors.BLUE)
    log("="*80)
    log(f"Base URL: {BASE_URL}")
    log(f"Owner: {OWNER_EMAIL}")
    log("="*80 + "\n")
    
    # Login
    token = login_owner()
    if not token:
        log_error("Failed to login. Cannot proceed with tests.")
        sys.exit(1)
    
    # Setup test data
    test_data = setup_test_data(token)
    
    # Run all tests
    test_owner_stock_column(token)
    test_insufficient_stock_and_oversell(token)
    test_backorder_creation(token)
    test_tl_sp_assignment(token)
    test_tl_tracking_detail(token)
    
    # Summary
    success = results.summary()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
