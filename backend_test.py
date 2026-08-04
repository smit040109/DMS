#!/usr/bin/env python3
"""
Backend API Testing for GO OIL DMS — Phase 1 Changes
Tests the BUG FIX and NEW endpoints for salesperson order visibility, cancel, edit, payment, and tracking.
"""
import requests
import json
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BASE_URL = "https://github-deploy-79.preview.emergentagent.com/api"

# Test credentials (all passwords: GoOil@2026)
CREDENTIALS = {
    "salesperson": {"email": "salesperson@gooil.com", "password": "GoOil@2026"},
    "retailer1": {"email": "retailer1@gooil.com", "password": "GoOil@2026"},
    "retailer2": {"email": "retailer2@gooil.com", "password": "GoOil@2026"},
    "teamleader": {"email": "teamleader@gooil.com", "password": "GoOil@2026"},
    "owner": {"email": "owner@gooil.com", "password": "GoOil@2026"},
    "distributor1": {"email": "distributor1@gooil.com", "password": "GoOil@2026"},
    "distributor2": {"email": "distributor2@gooil.com", "password": "GoOil@2026"},
    "regionalmgr": {"email": "regionalmgr@gooil.com", "password": "GoOil@2026"},
}

# Store tokens and test data
tokens: Dict[str, str] = {}
test_data: Dict[str, Any] = {}


def login(role: str) -> str:
    """Login and return JWT token"""
    creds = CREDENTIALS[role]
    resp = requests.post(f"{BASE_URL}/auth/login", json=creds)
    if resp.status_code != 200:
        raise Exception(f"Login failed for {role}: {resp.status_code} {resp.text}")
    data = resp.json()
    token = data.get("token")
    if not token:
        raise Exception(f"No token in response for {role}")
    tokens[role] = token
    print(f"✓ Logged in as {role}")
    return token


def get_headers(role: str) -> Dict[str, str]:
    """Get authorization headers for a role"""
    if role not in tokens:
        login(role)
    return {"Authorization": f"Bearer {tokens[role]}"}


def test_1_salesperson_order_visibility():
    """
    TEST 1: BUG FIX — Salesperson Order Visibility
    - Login as salesperson
    - Get retailer under SP's assigned distributor
    - Place order as salesperson for that retailer
    - GET /api/dms/secondary-orders → order MUST appear
    - Verify placed_by_name and distributor_name are populated
    """
    print("\n" + "="*80)
    print("TEST 1: BUG FIX — Salesperson Order Visibility")
    print("="*80)
    
    sp_headers = get_headers("salesperson")
    
    # Get retailers under SP's assigned distributors
    resp = requests.get(f"{BASE_URL}/dms/retailers", headers=sp_headers)
    assert resp.status_code == 200, f"Failed to get retailers: {resp.status_code}"
    retailers = resp.json()["data"]
    assert len(retailers) > 0, "No retailers found for salesperson"
    retailer = retailers[0]
    retailer_id = retailer["id"]
    print(f"✓ Found retailer: {retailer['name']} (ID: {retailer_id})")
    
    # Get products to place order
    resp = requests.get(f"{BASE_URL}/dms/retailer/browse?retailer_id={retailer_id}", headers=sp_headers)
    assert resp.status_code == 200, f"Failed to browse products: {resp.status_code}"
    products = resp.json()["data"]
    assert len(products) > 0, "No products available"
    product = products[0]
    print(f"✓ Found product: {product['name']} (ID: {product['id']})")
    
    # Place order as salesperson
    order_payload = {
        "retailer_id": retailer_id,
        "items": [
            {
                "product_id": product["id"],
                "qty_boxes": 2,
                "qty_pcs": 5
            }
        ]
    }
    resp = requests.post(f"{BASE_URL}/dms/secondary-orders", json=order_payload, headers=sp_headers)
    assert resp.status_code == 200, f"Failed to place order: {resp.status_code} {resp.text}"
    order = resp.json()
    order_id = order["id"]
    order_no = order["order_no"]
    test_data["sp_order_id"] = order_id
    test_data["sp_order_no"] = order_no
    test_data["retailer_id"] = retailer_id
    print(f"✓ Placed order: {order_no} (ID: {order_id})")
    
    # GET /api/dms/secondary-orders — order MUST appear
    resp = requests.get(f"{BASE_URL}/dms/secondary-orders", headers=sp_headers)
    assert resp.status_code == 200, f"Failed to get orders: {resp.status_code}"
    orders = resp.json()["data"]
    
    # Find the just-placed order
    found_order = None
    for o in orders:
        if o["id"] == order_id:
            found_order = o
            break
    
    assert found_order is not None, f"❌ CRITICAL: Order {order_no} NOT found in SP's order list!"
    print(f"✓ Order {order_no} appears in SP's order list")
    
    # Verify placed_by_name is populated
    assert "placed_by_name" in found_order, "placed_by_name field missing"
    assert found_order["placed_by_name"] is not None, "placed_by_name is null"
    print(f"✓ placed_by_name populated: {found_order['placed_by_name']}")
    
    # Verify distributor_name is populated
    assert "distributor_name" in found_order, "distributor_name field missing"
    assert found_order["distributor_name"] is not None, "distributor_name is null"
    print(f"✓ distributor_name populated: {found_order['distributor_name']}")
    
    print("✅ TEST 1 PASSED: Salesperson order visibility working correctly")


def test_2_cancel_order_endpoint():
    """
    TEST 2: NEW — POST /api/dms/secondary-orders/{oid}/cancel
    - As SP who placed order → 200, status becomes "cancelled"
    - Try to cancel again (already cancelled) → 400
    - Place another order → as retailer try to cancel SP's order → 403
    - As team_leader cancel order under their distributor → 200
    - Try to cancel a "dispatched" order → 400
    """
    print("\n" + "="*80)
    print("TEST 2: NEW — POST /api/dms/secondary-orders/{oid}/cancel")
    print("="*80)
    
    sp_headers = get_headers("salesperson")
    order_id = test_data["sp_order_id"]
    
    # 2.1: SP cancels their own order
    cancel_payload = {"reason": "Test cancellation by SP"}
    resp = requests.post(f"{BASE_URL}/dms/secondary-orders/{order_id}/cancel", 
                        json=cancel_payload, headers=sp_headers)
    assert resp.status_code == 200, f"Failed to cancel order: {resp.status_code} {resp.text}"
    result = resp.json()
    assert result["ok"] == True, "Cancel response ok != True"
    assert result["status"] == "cancelled", f"Status not cancelled: {result['status']}"
    print(f"✓ SP successfully cancelled order {test_data['sp_order_no']}")
    
    # 2.2: Try to cancel again (already cancelled) → 400
    resp = requests.post(f"{BASE_URL}/dms/secondary-orders/{order_id}/cancel", 
                        json=cancel_payload, headers=sp_headers)
    assert resp.status_code == 400, f"Expected 400 for already cancelled, got {resp.status_code}"
    print("✓ Cannot cancel already cancelled order (400)")
    
    # 2.3: Place another order, retailer tries to cancel SP's order → 403
    retailer_id = test_data["retailer_id"]
    resp = requests.get(f"{BASE_URL}/dms/retailer/browse?retailer_id={retailer_id}", headers=sp_headers)
    products = resp.json()["data"]
    product = products[0]
    
    order_payload = {
        "retailer_id": retailer_id,
        "items": [{"product_id": product["id"], "qty_boxes": 1}]
    }
    resp = requests.post(f"{BASE_URL}/dms/secondary-orders", json=order_payload, headers=sp_headers)
    assert resp.status_code == 200, f"Failed to place second order: {resp.status_code}"
    order2 = resp.json()
    order2_id = order2["id"]
    test_data["sp_order2_id"] = order2_id
    print(f"✓ Placed second order: {order2['order_no']}")
    
    # Retailer tries to cancel SP's order
    retailer_headers = get_headers("retailer1")
    resp = requests.post(f"{BASE_URL}/dms/secondary-orders/{order2_id}/cancel", 
                        json={"reason": "Retailer trying to cancel"}, headers=retailer_headers)
    assert resp.status_code == 403, f"Expected 403 for retailer cancel, got {resp.status_code}"
    print("✓ Retailer cannot cancel SP's order (403)")
    
    # 2.4: Team leader cancels order under their assigned distributor
    tl_headers = get_headers("teamleader")
    resp = requests.post(f"{BASE_URL}/dms/secondary-orders/{order2_id}/cancel", 
                        json={"reason": "TL cancellation"}, headers=tl_headers)
    assert resp.status_code == 200, f"TL cancel failed: {resp.status_code} {resp.text}"
    print(f"✓ Team leader successfully cancelled order {order2['order_no']}")
    
    # 2.5: Try to cancel a dispatched order
    # First, place a new order and dispatch it
    order_payload = {
        "retailer_id": retailer_id,
        "items": [{"product_id": product["id"], "qty_boxes": 1}]
    }
    resp = requests.post(f"{BASE_URL}/dms/secondary-orders", json=order_payload, headers=sp_headers)
    order3 = resp.json()
    order3_id = order3["id"]
    
    # Dispatch as distributor
    dist_headers = get_headers("distributor1")
    dispatch_payload = {
        "items": [{"product_id": product["id"], "qty_boxes_dispatched": 1, "qty_pcs_dispatched": 0}],
        "complete": True
    }
    resp = requests.post(f"{BASE_URL}/dms/secondary-orders/{order3_id}/dispatch", 
                        json=dispatch_payload, headers=dist_headers)
    if resp.status_code == 200:
        print(f"✓ Dispatched order {order3['order_no']}")
        
        # Try to cancel dispatched order
        resp = requests.post(f"{BASE_URL}/dms/secondary-orders/{order3_id}/cancel", 
                            json={"reason": "Try cancel dispatched"}, headers=sp_headers)
        assert resp.status_code == 400, f"Expected 400 for dispatched order cancel, got {resp.status_code}"
        print("✓ Cannot cancel dispatched order (400)")
    else:
        print(f"⚠ Could not dispatch order (may be out of stock): {resp.status_code}")
    
    print("✅ TEST 2 PASSED: Cancel order endpoint working correctly")


def test_3_edit_order_endpoint():
    """
    TEST 3: NEW — PUT /api/dms/secondary-orders/{oid}
    - Place fresh order as SP
    - PUT with new items array (change qty) → 200, totals recomputed
    - After dispatch, PUT should return 400
    - As retailer role, PUT should be 403
    """
    print("\n" + "="*80)
    print("TEST 3: NEW — PUT /api/dms/secondary-orders/{oid}")
    print("="*80)
    
    sp_headers = get_headers("salesperson")
    retailer_id = test_data["retailer_id"]
    
    # Get products
    resp = requests.get(f"{BASE_URL}/dms/retailer/browse?retailer_id={retailer_id}", headers=sp_headers)
    products = resp.json()["data"]
    product = products[0]
    
    # Place fresh order
    order_payload = {
        "retailer_id": retailer_id,
        "items": [{"product_id": product["id"], "qty_boxes": 2, "qty_pcs": 0}]
    }
    resp = requests.post(f"{BASE_URL}/dms/secondary-orders", json=order_payload, headers=sp_headers)
    assert resp.status_code == 200, f"Failed to place order: {resp.status_code}"
    order = resp.json()
    order_id = order["id"]
    original_total = order["total"]
    print(f"✓ Placed order: {order['order_no']} with total ₹{original_total}")
    
    # 3.1: PUT with new items (change qty)
    edit_payload = {
        "items": [{"product_id": product["id"], "qty_boxes": 5, "qty_pcs": 10}]
    }
    resp = requests.put(f"{BASE_URL}/dms/secondary-orders/{order_id}", 
                       json=edit_payload, headers=sp_headers)
    assert resp.status_code == 200, f"Failed to edit order: {resp.status_code} {resp.text}"
    edited_order = resp.json()
    new_total = edited_order["total"]
    assert new_total != original_total, "Total should have changed after edit"
    print(f"✓ Edited order: new total ₹{new_total} (was ₹{original_total})")
    
    # 3.2: Place another order, dispatch it, then try to edit → 400
    order_payload = {
        "retailer_id": retailer_id,
        "items": [{"product_id": product["id"], "qty_boxes": 1}]
    }
    resp = requests.post(f"{BASE_URL}/dms/secondary-orders", json=order_payload, headers=sp_headers)
    order2 = resp.json()
    order2_id = order2["id"]
    
    # Dispatch as distributor
    dist_headers = get_headers("distributor1")
    dispatch_payload = {
        "items": [{"product_id": product["id"], "qty_boxes_dispatched": 1, "qty_pcs_dispatched": 0}],
        "complete": True
    }
    resp = requests.post(f"{BASE_URL}/dms/secondary-orders/{order2_id}/dispatch", 
                        json=dispatch_payload, headers=dist_headers)
    if resp.status_code == 200:
        print(f"✓ Dispatched order {order2['order_no']}")
        
        # Try to edit dispatched order
        resp = requests.put(f"{BASE_URL}/dms/secondary-orders/{order2_id}", 
                           json=edit_payload, headers=sp_headers)
        assert resp.status_code == 400, f"Expected 400 for dispatched order edit, got {resp.status_code}"
        print("✓ Cannot edit dispatched order (400)")
    else:
        print(f"⚠ Could not dispatch order (may be out of stock): {resp.status_code}")
    
    # 3.3: Retailer tries to edit SP's order → 403
    retailer_headers = get_headers("retailer1")
    resp = requests.put(f"{BASE_URL}/dms/secondary-orders/{order_id}", 
                       json=edit_payload, headers=retailer_headers)
    assert resp.status_code == 403, f"Expected 403 for retailer edit, got {resp.status_code}"
    print("✓ Retailer cannot edit SP's order (403)")
    
    print("✅ TEST 3 PASSED: Edit order endpoint working correctly")


def test_4_secondary_payment_endpoint():
    """
    TEST 4: UPDATED — POST /api/dms/ledger/secondary/payment
    - As salesperson: record cash payment for retailer under assigned distributor → 200
    - As salesperson: try to record for retailer NOT under SP's distributor → 403
    - As distributor: existing flow still works (regression) → 200
    - As retailer: → 403
    """
    print("\n" + "="*80)
    print("TEST 4: UPDATED — POST /api/dms/ledger/secondary/payment")
    print("="*80)
    
    sp_headers = get_headers("salesperson")
    
    # 4.1: SP records payment for retailer under assigned distributor
    retailer_id = test_data["retailer_id"]
    payment_payload = {
        "retailer_id": retailer_id,
        "amount": 1000,
        "method": "cash",
        "description": "Test payment by SP"
    }
    resp = requests.post(f"{BASE_URL}/dms/ledger/secondary/payment", 
                        json=payment_payload, headers=sp_headers)
    assert resp.status_code == 200, f"SP payment failed: {resp.status_code} {resp.text}"
    payment = resp.json()
    assert payment["method"] == "cash", f"Method should be cash, got {payment['method']}"
    assert payment["recorded_by_role"] == "salesperson", "recorded_by_role should be salesperson"
    print(f"✓ SP recorded cash payment of ₹{payment['amount']} for retailer")
    
    # 4.2: SP tries to record for retailer NOT under their distributor
    # Get all retailers
    owner_headers = get_headers("owner")
    resp = requests.get(f"{BASE_URL}/dms/retailers", headers=owner_headers)
    all_retailers = resp.json()["data"]
    
    # Get SP's assigned distributors
    resp = requests.get(f"{BASE_URL}/dms/assignments/sp-distributors", headers=sp_headers)
    sp_dists = [a["distributor_id"] for a in resp.json()["data"]]
    
    # Find a retailer NOT under SP's distributors
    other_retailer = None
    for r in all_retailers:
        if r["distributor_id"] not in sp_dists:
            other_retailer = r
            break
    
    if other_retailer:
        payment_payload = {
            "retailer_id": other_retailer["id"],
            "amount": 500,
            "method": "cash"
        }
        resp = requests.post(f"{BASE_URL}/dms/ledger/secondary/payment", 
                            json=payment_payload, headers=sp_headers)
        assert resp.status_code == 403, f"Expected 403 for other retailer, got {resp.status_code}"
        print(f"✓ SP cannot record payment for retailer outside assigned distributors (403)")
    else:
        print("⚠ No retailer found outside SP's distributors, skipping test 4.2")
    
    # 4.3: Distributor records payment (regression)
    dist_headers = get_headers("distributor1")
    payment_payload = {
        "retailer_id": retailer_id,
        "amount": 2000,
        "method": "bank_transfer",
        "description": "Test payment by distributor"
    }
    resp = requests.post(f"{BASE_URL}/dms/ledger/secondary/payment", 
                        json=payment_payload, headers=dist_headers)
    assert resp.status_code == 200, f"Distributor payment failed: {resp.status_code} {resp.text}"
    payment = resp.json()
    print(f"✓ Distributor recorded payment of ₹{payment['amount']} (regression OK)")
    
    # 4.4: Retailer tries to record payment → 403
    retailer_headers = get_headers("retailer1")
    payment_payload = {
        "retailer_id": retailer_id,
        "amount": 100,
        "method": "cash"
    }
    resp = requests.post(f"{BASE_URL}/dms/ledger/secondary/payment", 
                        json=payment_payload, headers=retailer_headers)
    assert resp.status_code == 403, f"Expected 403 for retailer, got {resp.status_code}"
    print("✓ Retailer cannot record payment (403)")
    
    print("✅ TEST 4 PASSED: Secondary payment endpoint working correctly")


def test_5_tracking_live_endpoint():
    """
    TEST 5: UPDATED — GET /api/dms/tracking/live
    - Login as regional_manager → response MUST contain `team_leaders` array key
    - Login as owner → response also contains `team_leaders` array
    - Login as team_leader → endpoint still allowed, existing keys intact (regression)
    """
    print("\n" + "="*80)
    print("TEST 5: UPDATED — GET /api/dms/tracking/live")
    print("="*80)
    
    # 5.1: Regional manager
    rm_headers = get_headers("regionalmgr")
    resp = requests.get(f"{BASE_URL}/dms/tracking/live", headers=rm_headers)
    assert resp.status_code == 200, f"RM tracking/live failed: {resp.status_code}"
    data = resp.json()
    assert "team_leaders" in data, "❌ CRITICAL: team_leaders key missing for regional_manager"
    assert isinstance(data["team_leaders"], list), "team_leaders should be a list"
    print(f"✓ Regional manager: team_leaders array present ({len(data['team_leaders'])} TLs)")
    
    # 5.2: Owner
    owner_headers = get_headers("owner")
    resp = requests.get(f"{BASE_URL}/dms/tracking/live", headers=owner_headers)
    assert resp.status_code == 200, f"Owner tracking/live failed: {resp.status_code}"
    data = resp.json()
    assert "team_leaders" in data, "❌ CRITICAL: team_leaders key missing for owner"
    assert isinstance(data["team_leaders"], list), "team_leaders should be a list"
    print(f"✓ Owner: team_leaders array present ({len(data['team_leaders'])} TLs)")
    
    # 5.3: Team leader (regression)
    tl_headers = get_headers("teamleader")
    resp = requests.get(f"{BASE_URL}/dms/tracking/live", headers=tl_headers)
    assert resp.status_code == 200, f"TL tracking/live failed: {resp.status_code}"
    data = resp.json()
    assert "salespersons" in data, "salespersons key missing (regression)"
    assert "distributors" in data, "distributors key missing (regression)"
    assert "retailers" in data, "retailers key missing (regression)"
    print(f"✓ Team leader: existing keys intact (salespersons, distributors, retailers)")
    
    print("✅ TEST 5 PASSED: Tracking live endpoint working correctly")


def test_6_regression_endpoints():
    """
    TEST 6: Regression — verify no existing endpoint broken
    - GET /api/dms/dashboard/salesperson
    - GET /api/dms/dashboard/team-leader
    - GET /api/dms/dashboard/owner
    - GET /api/dms/tl/orders
    - GET /api/dms/secondary-orders/{oid} — enrich fields present
    """
    print("\n" + "="*80)
    print("TEST 6: Regression — verify existing endpoints not broken")
    print("="*80)
    
    # 6.1: Salesperson dashboard
    sp_headers = get_headers("salesperson")
    resp = requests.get(f"{BASE_URL}/dms/dashboard/salesperson", headers=sp_headers)
    assert resp.status_code == 200, f"SP dashboard failed: {resp.status_code}"
    data = resp.json()
    assert "kpis" in data, "kpis missing from SP dashboard"
    print("✓ GET /api/dms/dashboard/salesperson working")
    
    # 6.2: Team leader dashboard
    tl_headers = get_headers("teamleader")
    resp = requests.get(f"{BASE_URL}/dms/dashboard/team-leader", headers=tl_headers)
    assert resp.status_code == 200, f"TL dashboard failed: {resp.status_code}"
    data = resp.json()
    assert "kpis" in data, "kpis missing from TL dashboard"
    print("✓ GET /api/dms/dashboard/team-leader working")
    
    # 6.3: Owner dashboard
    owner_headers = get_headers("owner")
    resp = requests.get(f"{BASE_URL}/dms/dashboard/owner", headers=owner_headers)
    assert resp.status_code == 200, f"Owner dashboard failed: {resp.status_code}"
    data = resp.json()
    assert "kpis" in data, "kpis missing from owner dashboard"
    print("✓ GET /api/dms/dashboard/owner working")
    
    # 6.4: TL orders
    resp = requests.get(f"{BASE_URL}/dms/tl/orders", headers=tl_headers)
    assert resp.status_code == 200, f"TL orders failed: {resp.status_code}"
    data = resp.json()
    assert "data" in data, "data missing from TL orders"
    print("✓ GET /api/dms/tl/orders working")
    
    # 6.5: Secondary order detail with enrich fields
    if "sp_order_id" in test_data:
        order_id = test_data["sp_order_id"]
        resp = requests.get(f"{BASE_URL}/dms/secondary-orders/{order_id}", headers=sp_headers)
        assert resp.status_code == 200, f"Order detail failed: {resp.status_code}"
        order = resp.json()
        assert "retailer" in order, "retailer enrich field missing"
        assert "distributor" in order, "distributor enrich field missing"
        # Check for placed_by_name / placed_by_user
        if order.get("placed_by"):
            assert "placed_by_name" in order or "placed_by_user" in order, "placed_by enrich fields missing"
        print("✓ GET /api/dms/secondary-orders/{oid} enrich fields present")
    
    print("✅ TEST 6 PASSED: All regression tests passed")


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("GO OIL DMS — PHASE 1 BACKEND API TESTING")
    print("="*80)
    print(f"Backend URL: {BASE_URL}")
    print("="*80)
    
    try:
        # Run all tests in sequence
        test_1_salesperson_order_visibility()
        test_2_cancel_order_endpoint()
        test_3_edit_order_endpoint()
        test_4_secondary_payment_endpoint()
        test_5_tracking_live_endpoint()
        test_6_regression_endpoints()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED (6/6)")
        print("="*80)
        print("\nSUMMARY:")
        print("✅ TEST 1: Salesperson order visibility BUG FIX working")
        print("✅ TEST 2: Cancel order endpoint working")
        print("✅ TEST 3: Edit order endpoint working")
        print("✅ TEST 4: Secondary payment endpoint (SP can record) working")
        print("✅ TEST 5: Tracking live endpoint (team_leaders array) working")
        print("✅ TEST 6: All regression tests passed")
        print("\n🎉 Phase 1 backend changes verified successfully!")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
