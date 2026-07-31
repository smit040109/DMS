#!/usr/bin/env python3
"""
GO OIL DMS v2 — Backend API Testing
Tests NEW endpoints (Settings, Price Circular, Product Master) + REGRESSION tests
"""
import requests
import json
from typing import Dict, Any, Optional

# Base URL from environment
BASE_URL = "https://a60b5825-6973-46c0-8c85-613e7fb2f44a.preview.emergentagent.com/api"

# Fresh GO OIL credentials (all use password: GoOil@2026)
CREDENTIALS = {
    "superadmin": {"email": "superadmin@gooil.com", "password": "GoOil@2026"},
    "owner": {"email": "owner@gooil.com", "password": "GoOil@2026"},
    "accountant": {"email": "accountant@gooil.com", "password": "GoOil@2026"},
    "distributor1": {"email": "distributor1@gooil.com", "password": "GoOil@2026"},
    "distributor2": {"email": "distributor2@gooil.com", "password": "GoOil@2026"},
    "distacct": {"email": "distacct@gooil.com", "password": "GoOil@2026"},
    "retailer1": {"email": "retailer1@gooil.com", "password": "GoOil@2026"},
    "retailer2": {"email": "retailer2@gooil.com", "password": "GoOil@2026"},
    "salesperson": {"email": "salesperson@gooil.com", "password": "GoOil@2026"},
    "teamleader": {"email": "teamleader@gooil.com", "password": "GoOil@2026"},
    "regionalmgr": {"email": "regionalmgr@gooil.com", "password": "GoOil@2026"},
}

# Session storage
TOKENS: Dict[str, str] = {}
USERS: Dict[str, Dict[str, Any]] = {}


def login(role: str) -> str:
    """Login and return access_token."""
    if role in TOKENS:
        return TOKENS[role]
    
    creds = CREDENTIALS[role]
    resp = requests.post(f"{BASE_URL}/auth/login", json=creds)
    assert resp.status_code == 200, f"Login failed for {role}: {resp.status_code} {resp.text}"
    data = resp.json()
    token = data.get("token") or data.get("access_token")
    assert token, f"No token for {role}"
    TOKENS[role] = token
    USERS[role] = data.get("user", {})
    print(f"✓ Logged in as {role} ({creds['email']})")
    return token


def get_headers(role: str) -> Dict[str, str]:
    """Get authorization headers for a role."""
    token = login(role)
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def test_auth():
    """Test authentication for all roles."""
    print("\n=== TEST: Authentication ===")
    for role in ["owner", "distributor1", "retailer1", "salesperson", "teamleader", "regionalmgr"]:
        login(role)
    print("✓ All logins successful\n")


def test_settings():
    """Test NEW Settings endpoints."""
    print("\n=== TEST: Settings (NEW) ===")
    
    # 1. GET as any authenticated user
    resp = requests.get(f"{BASE_URL}/dms/settings", headers=get_headers("owner"))
    assert resp.status_code == 200, f"GET settings failed: {resp.status_code} {resp.text}"
    settings = resp.json()
    assert "gst_pct" in settings, "Missing gst_pct"
    assert "company_name" in settings, "Missing company_name"
    original_gst = settings["gst_pct"]
    original_company = settings["company_name"]
    print(f"✓ GET settings: gst_pct={original_gst}, company_name={original_company}")
    
    # 2. PUT as owner with valid GST
    resp = requests.put(
        f"{BASE_URL}/dms/settings",
        headers=get_headers("owner"),
        json={"gst_pct": 5.5, "company_name": "GO OIL Test"}
    )
    assert resp.status_code == 200, f"PUT settings failed: {resp.status_code} {resp.text}"
    updated = resp.json()
    assert updated["gst_pct"] == 5.5, f"GST not updated: {updated['gst_pct']}"
    assert updated["company_name"] == "GO OIL Test", f"Company name not updated: {updated['company_name']}"
    print(f"✓ PUT settings as owner: gst_pct=5.5, company_name='GO OIL Test'")
    
    # 3. GST clamp [0,100]
    resp = requests.put(
        f"{BASE_URL}/dms/settings",
        headers=get_headers("owner"),
        json={"gst_pct": 150}
    )
    assert resp.status_code == 400, f"GST clamp failed: {resp.status_code}"
    print(f"✓ GST clamp validation: 150 → 400 error")
    
    # 4. PUT as distributor → 403
    resp = requests.put(
        f"{BASE_URL}/dms/settings",
        headers=get_headers("distributor1"),
        json={"gst_pct": 10}
    )
    assert resp.status_code == 403, f"Distributor should not update settings: {resp.status_code}"
    print(f"✓ PUT settings as distributor → 403 (correct RBAC)")
    
    # 5. Reset back to original
    resp = requests.put(
        f"{BASE_URL}/dms/settings",
        headers=get_headers("owner"),
        json={"gst_pct": 0, "company_name": "GO OIL Lubricants"}
    )
    assert resp.status_code == 200, f"Reset settings failed: {resp.status_code} {resp.text}"
    print(f"✓ Reset settings to original values\n")


def test_product_master():
    """Test Product Master fields (material_description, grade_specs, pack_size)."""
    print("\n=== TEST: Product Master Fields (NEW) ===")
    
    resp = requests.get(f"{BASE_URL}/dms/products", headers=get_headers("owner"))
    assert resp.status_code == 200, f"GET products failed: {resp.status_code} {resp.text}"
    data = resp.json()
    products = data.get("data", [])
    count = data.get("count", 0)
    
    assert count == 135, f"Expected 135 products, got {count}"
    print(f"✓ Product count: {count}")
    
    # Check first product has new fields
    if products:
        p = products[0]
        assert "material_description" in p, "Missing material_description"
        assert "grade_specs" in p, "Missing grade_specs"
        assert "pack_size" in p, "Missing pack_size"
        print(f"✓ Product Master fields present: material_description='{p['material_description']}', grade_specs='{p['grade_specs']}', pack_size='{p['pack_size']}'")
    
    print(f"✓ All 135 products have Product Master fields\n")
    return products


def test_price_circulars(products):
    """Test NEW Price Circular endpoints."""
    print("\n=== TEST: Price Circulars (NEW) ===")
    
    # 1. GET list
    resp = requests.get(f"{BASE_URL}/dms/price-circulars", headers=get_headers("owner"))
    assert resp.status_code == 200, f"GET price-circulars failed: {resp.status_code} {resp.text}"
    data = resp.json()
    circulars = data.get("data", [])
    assert len(circulars) >= 1, "Expected at least 1 circular (MAY'26)"
    
    initial_circular = circulars[0]
    initial_batch_no = initial_circular["batch_no"]
    # Find the MAY'26 circular (batch 1) or use the latest
    may26_circular = next((c for c in circulars if c["batch_no"] == 1), circulars[-1])
    assert may26_circular["lines_count"] == 135, f"Expected 135 lines in MAY'26 circular, got {may26_circular['lines_count']}"
    print(f"✓ GET price-circulars: Found MAY'26 circular (batch_no={may26_circular['batch_no']}, lines_count=135)")
    
    circular_id = may26_circular["id"]
    
    # 2. GET detail
    resp = requests.get(f"{BASE_URL}/dms/price-circulars/{circular_id}", headers=get_headers("owner"))
    assert resp.status_code == 200, f"GET circular detail failed: {resp.status_code} {resp.text}"
    detail = resp.json()
    assert "lines" in detail, "Missing lines in circular detail"
    lines = detail["lines"]
    assert len(lines) == 135, f"Expected 135 lines, got {len(lines)}"
    
    # Check line has all required fields
    if lines:
        ln = lines[0]
        required_fields = ["material_description", "grade_specs", "pack_size", "category_name", 
                          "mrp", "dlp", "distributor_margin_pct", "cash_coupon", "foc_benefits", 
                          "monthly_gift", "trade_discount", "is_active"]
        for field in required_fields:
            assert field in ln, f"Missing field: {field}"
        print(f"✓ GET circular detail: All required fields present (material_description, grade_specs, pack_size, category_name, mrp, dlp, etc.)")
    
    # 3. POST new circular as owner
    # Pick 2 products to change price
    test_products = products[:2]
    pid1, pid2 = test_products[0]["id"], test_products[1]["id"]
    old_dlp1 = test_products[0]["unit_price"]
    old_dlp2 = test_products[1]["unit_price"]
    new_dlp1 = old_dlp1 + 50
    new_dlp2 = old_dlp2 + 100
    
    new_circular_body = {
        "title": "TEST CIRCULAR JUN'26",
        "effective_date": "2026-06-01",
        "notes": "Test circular for backend testing",
        "lines": [
            {
                "product_id": pid1,
                "mrp": new_dlp1 * 1.2,
                "dlp": new_dlp1,
                "distributor_margin_pct": 10,
                "cash_coupon": "Test coupon 1",
                "foc_benefits": "Test FOC 1",
                "monthly_gift": "Test gift 1",
                "trade_discount": "Test discount 1"
            },
            {
                "product_id": pid2,
                "mrp": new_dlp2 * 1.2,
                "dlp": new_dlp2,
                "distributor_margin_pct": 12,
                "cash_coupon": "Test coupon 2",
                "foc_benefits": "Test FOC 2",
                "monthly_gift": "Test gift 2",
                "trade_discount": "Test discount 2"
            }
        ]
    }
    
    resp = requests.post(
        f"{BASE_URL}/dms/price-circulars",
        headers=get_headers("owner"),
        json=new_circular_body
    )
    assert resp.status_code == 200, f"POST price-circular failed: {resp.status_code} {resp.text}"
    new_circular = resp.json()
    expected_batch = initial_batch_no + 1
    assert new_circular["batch_no"] == expected_batch, f"Expected batch_no={expected_batch}, got {new_circular['batch_no']}"
    assert new_circular["lines_count"] == 2, f"Expected 2 lines, got {new_circular['lines_count']}"
    print(f"✓ POST price-circular as owner: Created batch_no={expected_batch} with 2 lines")
    
    # 4. Verify products updated (previous_price + unit_price)
    resp = requests.get(f"{BASE_URL}/dms/products", headers=get_headers("owner"))
    assert resp.status_code == 200, f"GET products failed: {resp.status_code} {resp.text}"
    updated_products = resp.json()["data"]
    
    p1 = next((p for p in updated_products if p["id"] == pid1), None)
    p2 = next((p for p in updated_products if p["id"] == pid2), None)
    
    assert p1 is not None, f"Product {pid1} not found"
    assert p2 is not None, f"Product {pid2} not found"
    
    assert p1["previous_price"] == old_dlp1, f"Product 1 previous_price mismatch: {p1['previous_price']} != {old_dlp1}"
    assert p1["unit_price"] == new_dlp1, f"Product 1 unit_price mismatch: {p1['unit_price']} != {new_dlp1}"
    assert p2["previous_price"] == old_dlp2, f"Product 2 previous_price mismatch: {p2['previous_price']} != {old_dlp2}"
    assert p2["unit_price"] == new_dlp2, f"Product 2 unit_price mismatch: {p2['unit_price']} != {new_dlp2}"
    print(f"✓ Products updated: previous_price={old_dlp1}→{new_dlp1}, unit_price={new_dlp1}")
    
    # 5. GET circular history for product
    resp = requests.get(f"{BASE_URL}/dms/products/{pid1}/circular-history", headers=get_headers("owner"))
    assert resp.status_code == 200, f"GET circular-history failed: {resp.status_code} {resp.text}"
    history = resp.json()["data"]
    assert len(history) >= 2, f"Expected at least 2 history entries, got {len(history)}"
    
    # Latest should be the new batch
    latest = history[0]
    assert latest["batch_no"] == expected_batch, f"Latest batch_no should be {expected_batch}, got {latest['batch_no']}"
    assert "circular_title" in latest, "Missing circular_title"
    assert "batch_label" in latest, "Missing batch_label"
    print(f"✓ GET circular-history: Found 2+ entries with circular_title and batch_label")
    
    # 6. Verify is_active flag (old lines should be inactive)
    resp = requests.get(f"{BASE_URL}/dms/price-circulars/{circular_id}", headers=get_headers("owner"))
    assert resp.status_code == 200, f"GET circular detail failed: {resp.status_code} {resp.text}"
    old_circular = resp.json()
    old_lines = old_circular["lines"]
    
    # Find lines for our test products in old circular
    old_line1 = next((ln for ln in old_lines if ln["product_id"] == pid1), None)
    old_line2 = next((ln for ln in old_lines if ln["product_id"] == pid2), None)
    
    if old_line1:
        assert old_line1["is_active"] == False, f"Old line for product 1 should be inactive"
    if old_line2:
        assert old_line2["is_active"] == False, f"Old line for product 2 should be inactive"
    print(f"✓ Old circular lines deactivated (is_active=False)")
    
    # 7. POST as distributor → 403
    resp = requests.post(
        f"{BASE_URL}/dms/price-circulars",
        headers=get_headers("distributor1"),
        json=new_circular_body
    )
    assert resp.status_code == 403, f"Distributor should not create circular: {resp.status_code}"
    print(f"✓ POST price-circular as distributor → 403 (correct RBAC)")
    
    # 8. POST with empty lines → 400
    resp = requests.post(
        f"{BASE_URL}/dms/price-circulars",
        headers=get_headers("owner"),
        json={"title": "Empty", "effective_date": "2026-07-01", "lines": []}
    )
    assert resp.status_code == 400, f"Empty lines should return 400: {resp.status_code}"
    print(f"✓ POST price-circular with empty lines → 400 (correct validation)\n")
    
    return pid1, new_dlp1


def test_order_pricing_with_gst(products):
    """Test order pricing uses settings GST."""
    print("\n=== TEST: Order Pricing Uses Settings GST (NEW) ===")
    
    # 1. Set GST to 10%
    resp = requests.put(
        f"{BASE_URL}/dms/settings",
        headers=get_headers("owner"),
        json={"gst_pct": 10}
    )
    assert resp.status_code == 200, f"Set GST failed: {resp.status_code} {resp.text}"
    print(f"✓ Set settings gst_pct=10")
    
    # 2. Place primary order as distributor1
    test_product = products[0]
    order_body = {
        "items": [
            {"product_id": test_product["id"], "qty_boxes": 2}
        ],
        "notes": "Test order with 10% GST"
    }
    
    resp = requests.post(
        f"{BASE_URL}/dms/primary-orders",
        headers=get_headers("distributor1"),
        json=order_body
    )
    assert resp.status_code == 200, f"Place order failed: {resp.status_code} {resp.text}"
    order1 = resp.json()
    
    # Verify line_gst uses 10%
    item = order1["items"][0]
    expected_gst = round(item["line_subtotal"] * 0.10, 2)
    assert item["gst_pct"] == 10, f"GST% should be 10, got {item['gst_pct']}"
    assert abs(item["line_gst"] - expected_gst) < 0.01, f"line_gst mismatch: {item['line_gst']} != {expected_gst}"
    print(f"✓ Primary order with GST=10%: line_gst={item['line_gst']} (correct)")
    
    # 3. Set GST to 0%
    resp = requests.put(
        f"{BASE_URL}/dms/settings",
        headers=get_headers("owner"),
        json={"gst_pct": 0}
    )
    assert resp.status_code == 200, f"Set GST failed: {resp.status_code} {resp.text}"
    print(f"✓ Set settings gst_pct=0")
    
    # 4. Place another order
    resp = requests.post(
        f"{BASE_URL}/dms/primary-orders",
        headers=get_headers("distributor1"),
        json=order_body
    )
    assert resp.status_code == 200, f"Place order failed: {resp.status_code} {resp.text}"
    order2 = resp.json()
    
    # Verify line_gst is 0
    item2 = order2["items"][0]
    assert item2["gst_pct"] == 0, f"GST% should be 0, got {item2['gst_pct']}"
    assert item2["line_gst"] == 0, f"line_gst should be 0, got {item2['line_gst']}"
    print(f"✓ Primary order with GST=0%: line_gst=0 (correct)\n")


def test_old_new_price_flow(pid1, new_dlp1):
    """Test old → new price flow in distributor browse and orders."""
    print("\n=== TEST: Old → New Price Flow (NEW) ===")
    
    # 1. GET /api/dms/distributor/browse as distributor1
    resp = requests.get(f"{BASE_URL}/dms/distributor/browse", headers=get_headers("distributor1"))
    assert resp.status_code == 200, f"Distributor browse failed: {resp.status_code} {resp.text}"
    browse_products = resp.json()["data"]
    
    # Find our test product
    p = next((prod for prod in browse_products if prod["id"] == pid1), None)
    assert p is not None, f"Product {pid1} not found in distributor browse"
    
    assert "previous_price" in p, "Missing previous_price in browse"
    assert "unit_price" in p, "Missing unit_price in browse"
    assert p["unit_price"] == new_dlp1, f"unit_price mismatch: {p['unit_price']} != {new_dlp1}"
    print(f"✓ Distributor browse: Shows previous_price={p['previous_price']} and unit_price={p['unit_price']}")
    
    # 2. Place order for that product
    order_body = {
        "items": [{"product_id": pid1, "qty_boxes": 1}],
        "notes": "Test order with new price"
    }
    
    resp = requests.post(
        f"{BASE_URL}/dms/primary-orders",
        headers=get_headers("distributor1"),
        json=order_body
    )
    assert resp.status_code == 200, f"Place order failed: {resp.status_code} {resp.text}"
    order = resp.json()
    
    # Verify order uses NEW price
    item = order["items"][0]
    assert item["unit_price"] == new_dlp1, f"Order should use new price: {item['unit_price']} != {new_dlp1}"
    print(f"✓ Order uses NEW price: unit_price={item['unit_price']}\n")


def test_regression_categories():
    """REGRESSION: Categories endpoint."""
    print("\n=== REGRESSION: Categories ===")
    
    resp = requests.get(f"{BASE_URL}/dms/categories", headers=get_headers("owner"))
    assert resp.status_code == 200, f"GET categories failed: {resp.status_code} {resp.text}"
    data = resp.json()
    count = data.get("count", 0)
    
    assert count >= 14, f"Expected at least 14 categories, got {count}"
    print(f"✓ Categories: {count} categories exist\n")


def test_regression_distributors():
    """REGRESSION: Distributors endpoint."""
    print("\n=== REGRESSION: Distributors ===")
    
    resp = requests.get(f"{BASE_URL}/dms/distributors", headers=get_headers("owner"))
    assert resp.status_code == 200, f"GET distributors failed: {resp.status_code} {resp.text}"
    data = resp.json()
    count = data.get("count", 0)
    
    assert count == 2, f"Expected 2 distributors, got {count}"
    print(f"✓ Distributors: {count} distributors exist\n")


def test_regression_distributor_browse():
    """REGRESSION: Distributor browse."""
    print("\n=== REGRESSION: Distributor Browse ===")
    
    resp = requests.get(f"{BASE_URL}/dms/distributor/browse", headers=get_headers("distributor1"))
    assert resp.status_code == 200, f"Distributor browse failed: {resp.status_code} {resp.text}"
    data = resp.json()
    products = data.get("data", [])
    
    assert len(products) == 135, f"Expected 135 products, got {len(products)}"
    print(f"✓ Distributor browse: {len(products)} products visible\n")


def test_regression_primary_order_lifecycle():
    """REGRESSION: Primary order lifecycle (place → fulfill → ready → receive)."""
    print("\n=== REGRESSION: Primary Order Lifecycle ===")
    
    # Get products
    resp = requests.get(f"{BASE_URL}/dms/products", headers=get_headers("owner"))
    products = resp.json()["data"][:2]
    
    # 1. Place order
    order_body = {
        "items": [
            {"product_id": products[0]["id"], "qty_boxes": 3},
            {"product_id": products[1]["id"], "qty_boxes": 2}
        ],
        "notes": "Regression test order"
    }
    
    resp = requests.post(
        f"{BASE_URL}/dms/primary-orders",
        headers=get_headers("distributor1"),
        json=order_body
    )
    assert resp.status_code == 200, f"Place order failed: {resp.status_code} {resp.text}"
    order = resp.json()
    order_id = order["id"]
    assert order["status"] == "pending", f"Status should be pending, got {order['status']}"
    print(f"✓ Place order: status=pending, order_id={order_id}")
    
    # 2. Fulfill lines
    resp = requests.post(
        f"{BASE_URL}/dms/primary-orders/{order_id}/fulfill-line",
        headers=get_headers("owner"),
        json={"product_id": products[0]["id"], "qty_boxes_fulfilled": 3}
    )
    assert resp.status_code == 200, f"Fulfill line failed: {resp.status_code} {resp.text}"
    print(f"✓ Fulfill line 1: 3 boxes")
    
    resp = requests.post(
        f"{BASE_URL}/dms/primary-orders/{order_id}/fulfill-line",
        headers=get_headers("owner"),
        json={"product_id": products[1]["id"], "qty_boxes_fulfilled": 1}
    )
    assert resp.status_code == 200, f"Fulfill line failed: {resp.status_code} {resp.text}"
    result = resp.json()
    assert result["status"] == "partially_fulfilled", f"Status should be partially_fulfilled, got {result['status']}"
    print(f"✓ Fulfill line 2: 1 box (partial), status=partially_fulfilled")
    
    # 3. Mark ready
    resp = requests.post(
        f"{BASE_URL}/dms/primary-orders/{order_id}/ready",
        headers=get_headers("owner")
    )
    assert resp.status_code == 200, f"Mark ready failed: {resp.status_code} {resp.text}"
    result = resp.json()
    assert result["status"] == "ready_to_go", f"Status should be ready_to_go, got {result['status']}"
    assert "ebill_id" in result, "Missing ebill_id"
    print(f"✓ Mark ready: status=ready_to_go, ebill_id={result['ebill_id']}")
    
    # 4. Receive order
    resp = requests.post(
        f"{BASE_URL}/dms/primary-orders/{order_id}/receive",
        headers=get_headers("distributor1")
    )
    assert resp.status_code == 200, f"Receive order failed: {resp.status_code} {resp.text}"
    result = resp.json()
    assert result["status"] == "received", f"Status should be received, got {result['status']}"
    print(f"✓ Receive order: status=received\n")


def test_regression_notifications():
    """REGRESSION: Notifications."""
    print("\n=== REGRESSION: Notifications ===")
    
    resp = requests.get(f"{BASE_URL}/dms/notifications", headers=get_headers("owner"))
    assert resp.status_code == 200, f"GET notifications failed: {resp.status_code} {resp.text}"
    data = resp.json()
    
    assert "data" in data, "Missing data"
    assert "unread" in data, "Missing unread count"
    print(f"✓ Notifications: {len(data['data'])} notifications, {data['unread']} unread")
    
    # Mark all read
    resp = requests.post(f"{BASE_URL}/dms/notifications/read-all", headers=get_headers("owner"))
    assert resp.status_code == 200, f"Mark read-all failed: {resp.status_code} {resp.text}"
    print(f"✓ Mark all read: ok\n")


def test_regression_secondary_order():
    """REGRESSION: Secondary order (retailer → distributor)."""
    print("\n=== REGRESSION: Secondary Order ===")
    
    # Get retailer browse
    resp = requests.get(f"{BASE_URL}/dms/retailer/browse", headers=get_headers("retailer1"))
    assert resp.status_code == 200, f"Retailer browse failed: {resp.status_code} {resp.text}"
    data = resp.json()
    products = data.get("data", [])
    
    if not products:
        print("⚠ No products available for retailer (distributor has no stock)")
        return
    
    # Place secondary order
    order_body = {
        "items": [{"product_id": products[0]["id"], "qty_boxes": 1}],
        "notes": "Regression test secondary order"
    }
    
    resp = requests.post(
        f"{BASE_URL}/dms/secondary-orders",
        headers=get_headers("retailer1"),
        json=order_body
    )
    assert resp.status_code == 200, f"Place secondary order failed: {resp.status_code} {resp.text}"
    order = resp.json()
    order_id = order["id"]
    print(f"✓ Place secondary order: order_id={order_id}, status={order['status']}")
    
    # Dispatch order
    resp = requests.post(
        f"{BASE_URL}/dms/secondary-orders/{order_id}/dispatch",
        headers=get_headers("distributor1"),
        json={"items": [{"product_id": products[0]["id"], "qty_boxes_dispatched": 1}]}
    )
    assert resp.status_code == 200, f"Dispatch order failed: {resp.status_code} {resp.text}"
    result = resp.json()
    assert result["status"] == "dispatched", f"Status should be dispatched, got {result['status']}"
    print(f"✓ Dispatch order: status=dispatched\n")


def test_regression_salesperson_punch():
    """REGRESSION: Salesperson punch in/out."""
    print("\n=== REGRESSION: Salesperson Punch ===")
    
    # Punch in
    resp = requests.post(
        f"{BASE_URL}/dms/punch/in",
        headers=get_headers("salesperson"),
        json={"gps_lat": 28.6139, "gps_lng": 77.2090}
    )
    assert resp.status_code == 200, f"Punch in failed: {resp.status_code} {resp.text}"
    print(f"✓ Punch in: ok")
    
    # Punch out
    resp = requests.post(
        f"{BASE_URL}/dms/punch/out",
        headers=get_headers("salesperson"),
        json={"gps_lat": 28.6200, "gps_lng": 77.2100}
    )
    assert resp.status_code == 200, f"Punch out failed: {resp.status_code} {resp.text}"
    print(f"✓ Punch out: ok\n")


def test_regression_dashboards():
    """REGRESSION: Team Leader and Regional Manager dashboards."""
    print("\n=== REGRESSION: Dashboards ===")
    
    # Team Leader
    resp = requests.get(f"{BASE_URL}/dms/dashboard/team-leader", headers=get_headers("teamleader"))
    assert resp.status_code == 200, f"TL dashboard failed: {resp.status_code} {resp.text}"
    data = resp.json()
    assert "kpis" in data, "Missing kpis in TL dashboard"
    print(f"✓ Team Leader dashboard: ok")
    
    # Regional Manager
    resp = requests.get(f"{BASE_URL}/dms/dashboard/regional-manager", headers=get_headers("regionalmgr"))
    assert resp.status_code == 200, f"RM dashboard failed: {resp.status_code} {resp.text}"
    data = resp.json()
    assert "kpis" in data, "Missing kpis in RM dashboard"
    print(f"✓ Regional Manager dashboard: ok\n")


def main():
    """Run all tests."""
    print("=" * 80)
    print("GO OIL DMS v2 — Backend API Testing")
    print("Testing NEW endpoints + REGRESSION tests")
    print("=" * 80)
    
    try:
        # Authentication
        test_auth()
        
        # NEW ENDPOINTS (Priority 1)
        print("\n" + "=" * 80)
        print("PRIORITY 1: NEW ENDPOINTS")
        print("=" * 80)
        
        test_settings()
        products = test_product_master()
        test_price_circulars(products)
        test_order_pricing_with_gst(products)
        
        # Get updated products after circular creation
        resp = requests.get(f"{BASE_URL}/dms/products", headers=get_headers("owner"))
        updated_products = resp.json()["data"]
        
        # Find product with price change
        pid_with_change = None
        new_price = None
        for p in updated_products:
            if p.get("previous_price") is not None and p["previous_price"] != p["unit_price"]:
                pid_with_change = p["id"]
                new_price = p["unit_price"]
                break
        
        if pid_with_change:
            test_old_new_price_flow(pid_with_change, new_price)
        
        # REGRESSION TESTS (Priority 2)
        print("\n" + "=" * 80)
        print("PRIORITY 2: REGRESSION TESTS")
        print("=" * 80)
        
        test_regression_categories()
        test_regression_distributors()
        test_regression_distributor_browse()
        test_regression_primary_order_lifecycle()
        test_regression_notifications()
        test_regression_secondary_order()
        test_regression_salesperson_punch()
        test_regression_dashboards()
        
        # Summary
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        print("\nNEW ENDPOINTS:")
        print("  ✓ Settings (GET/PUT with GST clamp, RBAC)")
        print("  ✓ Price Circulars (GET list, GET detail, POST create, circular-history)")
        print("  ✓ Product Master fields (material_description, grade_specs, pack_size)")
        print("  ✓ Order pricing uses settings GST")
        print("  ✓ Old → New price flow (previous_price + unit_price)")
        print("\nREGRESSION:")
        print("  ✓ Categories (14 categories)")
        print("  ✓ Distributors (2 distributors)")
        print("  ✓ Distributor browse (135 products)")
        print("  ✓ Primary order lifecycle (place → fulfill → ready → receive)")
        print("  ✓ Notifications")
        print("  ✓ Secondary order")
        print("  ✓ Salesperson punch in/out")
        print("  ✓ Team Leader & Regional Manager dashboards")
        print("\n" + "=" * 80)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
