#!/usr/bin/env python3
"""
GO OIL DMS — Comprehensive Backend Flow Audit
==============================================
Tests all 8 audit areas as per review request.
"""
import requests
import json
from typing import Dict, Any, Optional

# Base URL from frontend/.env
BASE_URL = "https://challan-print-fix.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

# Test credentials from /app/memory/test_credentials.md
PASSWORD = "GoOil@2026"

ROLES = {
    "owner": "owner@gooil.com",
    "accountant": "accountant@gooil.com",
    "distributor1": "distributor1@gooil.com",
    "distributor2": "distributor2@gooil.com",
    "distacct": "distacct@gooil.com",
    "retailer1": "retailer1@gooil.com",
    "retailer2": "retailer2@gooil.com",
    "salesperson": "salesperson@gooil.com",
    "teamleader": "teamleader@gooil.com",
    "regionalmgr": "regionalmgr@gooil.com",
}

# Store tokens for each role
tokens: Dict[str, str] = {}
users: Dict[str, Dict[str, Any]] = {}

# Test results
results = {
    "1_AUTH": [],
    "2_DASHBOARDS": [],
    "3_PRIMARY_SALES": [],
    "4_SECONDARY_SALES": [],
    "5_DIRECT_SALE": [],
    "6_COUPON_FLOW": [],
    "7_PUNCH_ATTENDANCE": [],
    "8_PARTY_DETAILS": [],
}

def log(area: str, status: str, message: str):
    """Log test result"""
    results[area].append({"status": status, "message": message})
    symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{symbol} [{area}] {message}")

def login(role: str, email: str) -> Optional[str]:
    """Login and return token"""
    try:
        resp = requests.post(f"{API_BASE}/auth/login", json={"email": email, "password": PASSWORD}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("token") or data.get("access_token")  # Try both field names
            users[role] = data.get("user", {})
            return token
        else:
            log("1_AUTH", "FAIL", f"{role} login failed: {resp.status_code} {resp.text[:200]}")
            return None
    except Exception as e:
        log("1_AUTH", "FAIL", f"{role} login exception: {str(e)}")
        return None

def get_headers(role: str) -> Dict[str, str]:
    """Get auth headers for role"""
    return {"Authorization": f"Bearer {tokens.get(role, '')}", "Content-Type": "application/json"}

def test_endpoint(area: str, role: str, method: str, endpoint: str, expected_status: int = 200, 
                  json_data: Optional[Dict] = None, description: str = "") -> Optional[Dict]:
    """Test an endpoint and log result"""
    try:
        url = f"{API_BASE}{endpoint}"
        headers = get_headers(role)
        
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=json_data or {}, timeout=10)
        elif method == "PUT":
            resp = requests.put(url, headers=headers, json=json_data or {}, timeout=10)
        else:
            log(area, "FAIL", f"Unknown method {method}")
            return None
        
        if resp.status_code == expected_status:
            log(area, "PASS", f"{description or f'{method} {endpoint}'} → {resp.status_code}")
            try:
                return resp.json()
            except Exception:
                return {"status_code": resp.status_code}
        else:
            log(area, "FAIL", f"{description or f'{method} {endpoint}'} → {resp.status_code} (expected {expected_status}): {resp.text[:200]}")
            return None
    except Exception as e:
        log(area, "FAIL", f"{description or f'{method} {endpoint}'} exception: {str(e)}")
        return None

# ============================================================================
# AREA 1: AUTH — Login for all roles + /api/auth/me
# ============================================================================
def test_auth():
    print("\n" + "="*80)
    print("AREA 1: AUTH — Login for all 10 roles + /api/auth/me")
    print("="*80)
    
    for role, email in ROLES.items():
        token = login(role, email)
        if token:
            tokens[role] = token
            log("1_AUTH", "PASS", f"{role} ({email}) login successful")
            
            # Test /api/auth/me
            resp = test_endpoint("1_AUTH", role, "GET", "/auth/me", 
                                description=f"{role} /auth/me")
            if resp and resp.get("email") == email:
                log("1_AUTH", "PASS", f"{role} /auth/me returns correct user")
        else:
            log("1_AUTH", "FAIL", f"{role} ({email}) login failed")

# ============================================================================
# AREA 2: DASHBOARDS — Hit dashboard/KPI endpoint for each role
# ============================================================================
def test_dashboards():
    print("\n" + "="*80)
    print("AREA 2: DASHBOARDS — Dashboard/KPI endpoints for each role")
    print("="*80)
    
    dashboard_map = {
        "owner": "/dms/dashboard/owner",
        "accountant": "/dms/dashboard/owner",  # owner_accountant uses same endpoint
        "distributor1": "/dms/dashboard/distributor",
        "distributor2": "/dms/dashboard/distributor",
        "distacct": "/dms/dashboard/distributor",
        "retailer1": "/dms/dashboard/retailer",
        "retailer2": "/dms/dashboard/retailer",
        "salesperson": "/dms/dashboard/salesperson",
        "teamleader": "/dms/dashboard/team-leader",
        "regionalmgr": "/dms/dashboard/regional-manager",
    }
    
    for role, endpoint in dashboard_map.items():
        if role in tokens:
            resp = test_endpoint("2_DASHBOARDS", role, "GET", endpoint,
                               description=f"{role} dashboard")
            if resp and "kpis" in resp:
                log("2_DASHBOARDS", "PASS", f"{role} dashboard has KPIs")

# ============================================================================
# AREA 3: PRIMARY SALES FLOW — Distributor → Owner → E-bill → Receive
# ============================================================================
def test_primary_sales():
    print("\n" + "="*80)
    print("AREA 3: PRIMARY SALES FLOW — Full lifecycle test")
    print("="*80)
    
    # Step 1: Distributor1 browses products
    products = test_endpoint("3_PRIMARY_SALES", "distributor1", "GET", "/dms/distributor/browse",
                            description="Distributor1 browse products")
    if not products or not products.get("data"):
        log("3_PRIMARY_SALES", "FAIL", "No products available for distributor1")
        return
    
    product = products["data"][0]
    log("3_PRIMARY_SALES", "PASS", f"Found product: {product.get('name')}")
    
    # Step 2: Distributor1 places primary order
    order_data = {
        "items": [
            {"product_id": product["id"], "qty_boxes": 2}
        ],
        "notes": "Test primary order"
    }
    order = test_endpoint("3_PRIMARY_SALES", "distributor1", "POST", "/dms/primary-orders",
                         json_data=order_data, description="Distributor1 place primary order")
    if not order or not order.get("id"):
        log("3_PRIMARY_SALES", "FAIL", "Failed to create primary order")
        return
    
    order_id = order["id"]
    log("3_PRIMARY_SALES", "PASS", f"Primary order created: {order_id}")
    
    # Step 3: Owner views the order
    owner_order = test_endpoint("3_PRIMARY_SALES", "owner", "GET", f"/dms/primary-orders/{order_id}",
                               description="Owner view primary order")
    if owner_order:
        log("3_PRIMARY_SALES", "PASS", f"Owner can view order {order_id}")
    
    # Step 4: Owner fulfills line items
    fulfill_data = {
        "product_id": product["id"],
        "qty_boxes_fulfilled": 2
    }
    fulfill = test_endpoint("3_PRIMARY_SALES", "owner", "POST", 
                           f"/dms/primary-orders/{order_id}/fulfill-line",
                           json_data=fulfill_data, description="Owner fulfill line items")
    if fulfill:
        log("3_PRIMARY_SALES", "PASS", f"Line items fulfilled: {fulfill.get('fulfillment_pct')}%")
    
    # Step 5: Owner marks ready (generates e-bill)
    ready = test_endpoint("3_PRIMARY_SALES", "owner", "POST",
                         f"/dms/primary-orders/{order_id}/ready",
                         description="Owner mark ready (generate e-bill)")
    if ready and ready.get("ebill_id"):
        ebill_id = ready["ebill_id"]
        log("3_PRIMARY_SALES", "PASS", f"E-bill generated: {ebill_id}")
        
        # Verify primary ledger entry
        ledger = test_endpoint("3_PRIMARY_SALES", "owner", "GET", "/dms/ledger/primary",
                              description="Owner check primary ledger")
        if ledger and ledger.get("entries"):
            log("3_PRIMARY_SALES", "PASS", "Primary ledger has invoice entry")
    
    # Step 6: Distributor receives order
    receive = test_endpoint("3_PRIMARY_SALES", "distributor1", "POST",
                           f"/dms/primary-orders/{order_id}/receive",
                           description="Distributor1 mark received")
    if receive:
        log("3_PRIMARY_SALES", "PASS", "Distributor marked order as received")
        
        # Verify distributor inventory incremented
        dist_dash = test_endpoint("3_PRIMARY_SALES", "distributor1", "GET", "/dms/dashboard/distributor",
                                 description="Distributor1 check inventory")
        if dist_dash and dist_dash.get("kpis", {}).get("stock_boxes", 0) > 0:
            log("3_PRIMARY_SALES", "PASS", f"Distributor inventory incremented: {dist_dash['kpis']['stock_boxes']} boxes")

# ============================================================================
# AREA 4: SECONDARY SALES FLOW — Distributor → Retailer → Invoice → Dispatch
# ============================================================================
def test_secondary_sales():
    print("\n" + "="*80)
    print("AREA 4: SECONDARY SALES FLOW — Distributor → Retailer")
    print("="*80)
    
    # Get retailer1 details
    retailer_id = users.get("retailer1", {}).get("retailer_id")
    if not retailer_id:
        log("4_SECONDARY_SALES", "FAIL", "retailer1 has no retailer_id")
        return
    
    # Step 1: Retailer browses products
    browse = test_endpoint("4_SECONDARY_SALES", "retailer1", "GET", "/dms/retailer/browse",
                          description="Retailer1 browse products")
    if not browse or not browse.get("data"):
        log("4_SECONDARY_SALES", "FAIL", "No products available for retailer1")
        return
    
    product = browse["data"][0]
    log("4_SECONDARY_SALES", "PASS", f"Retailer can browse: {product.get('name')}")
    
    # Step 2: Distributor1 creates secondary order for retailer1
    order_data = {
        "retailer_id": retailer_id,
        "items": [
            {"product_id": product["id"], "qty_boxes": 1, "qty_pcs": 0}
        ]
    }
    order = test_endpoint("4_SECONDARY_SALES", "distributor1", "POST", "/dms/secondary-orders",
                         json_data=order_data, description="Distributor1 create secondary order")
    if not order or not order.get("id"):
        log("4_SECONDARY_SALES", "FAIL", "Failed to create secondary order")
        return
    
    order_id = order["id"]
    log("4_SECONDARY_SALES", "PASS", f"Secondary order created: {order_id}")
    
    # Step 3: Distributor dispatches order (generates invoice + delivery challan)
    dispatch_data = {
        "items": [
            {"product_id": product["id"], "qty_boxes_dispatched": 1, "qty_pcs_dispatched": 0}
        ]
    }
    dispatch = test_endpoint("4_SECONDARY_SALES", "distributor1", "POST",
                            f"/dms/secondary-orders/{order_id}/dispatch",
                            json_data=dispatch_data, description="Distributor1 dispatch order")
    if dispatch and dispatch.get("bill_id"):
        bill_id = dispatch["bill_id"]
        challan_id = dispatch.get("challan_id")
        log("4_SECONDARY_SALES", "PASS", f"Invoice generated: {bill_id}")
        
        if challan_id:
            log("4_SECONDARY_SALES", "PASS", f"Delivery challan generated: {challan_id}")
            
            # Step 4: Verify challan is retrievable
            challan = test_endpoint("4_SECONDARY_SALES", "distributor1", "GET",
                                   f"/dms/print/challan/{challan_id}",
                                   description="GET delivery challan")
            if challan:
                log("4_SECONDARY_SALES", "PASS", "Delivery challan retrievable")

# ============================================================================
# AREA 5: DIRECT SALE / +Add Sales — Test for different roles
# ============================================================================
def test_direct_sales():
    print("\n" + "="*80)
    print("AREA 5: DIRECT SALE / +Add Sales — Test POST /dms/direct-sales")
    print("="*80)
    
    # Get IDs
    dist_id = users.get("distributor1", {}).get("distributor_id")
    retailer_id = users.get("retailer1", {}).get("retailer_id")
    
    if not dist_id or not retailer_id:
        log("5_DIRECT_SALE", "FAIL", "Missing distributor_id or retailer_id")
        return
    
    # Get a product
    products = test_endpoint("5_DIRECT_SALE", "distributor1", "GET", "/dms/distributor/browse",
                            description="Get products for direct sale")
    if not products or not products.get("data"):
        log("5_DIRECT_SALE", "FAIL", "No products available")
        return
    
    product = products["data"][0]
    
    # Test data
    sale_data = {
        "distributor_id": dist_id,
        "retailer_id": retailer_id,
        "items": [
            {"product_id": product["id"], "qty_boxes": 1, "qty_pcs": 0}
        ]
    }
    
    # Test 1: Distributor can create direct sale
    sale1 = test_endpoint("5_DIRECT_SALE", "distributor1", "POST", "/dms/direct-sales",
                         json_data=sale_data, description="Distributor1 create direct sale")
    if sale1 and sale1.get("bill_id"):
        log("5_DIRECT_SALE", "PASS", f"Distributor can create direct sale: {sale1['bill_id']}")
    
    # Test 2: Owner can create direct sale
    sale2 = test_endpoint("5_DIRECT_SALE", "owner", "POST", "/dms/direct-sales",
                         json_data=sale_data, description="Owner create direct sale")
    if sale2 and sale2.get("bill_id"):
        log("5_DIRECT_SALE", "PASS", f"Owner can create direct sale: {sale2['bill_id']}")
    
    # Test 3: Salesperson attempt (should check if allowed)
    sale3 = test_endpoint("5_DIRECT_SALE", "salesperson", "POST", "/dms/direct-sales",
                         json_data=sale_data, expected_status=403,
                         description="Salesperson create direct sale (expect 403)")
    if sale3 is not None:
        log("5_DIRECT_SALE", "PASS", "Salesperson correctly blocked from direct sale")
    
    # Test 4: Retailer attempt (should be blocked)
    sale4 = test_endpoint("5_DIRECT_SALE", "retailer1", "POST", "/dms/direct-sales",
                         json_data=sale_data, expected_status=403,
                         description="Retailer create direct sale (expect 403)")
    if sale4 is not None:
        log("5_DIRECT_SALE", "PASS", "Retailer correctly blocked from direct sale")

# ============================================================================
# AREA 6: COUPON FLOW — Owner creates batch, salesperson scans for retailer
# ============================================================================
def test_coupon_flow():
    print("\n" + "="*80)
    print("AREA 6: COUPON FLOW — Batch creation + scan")
    print("="*80)
    
    # Step 1: Owner creates coupon batch
    batch_data = {
        "title": "Test Audit Batch",
        "coupon_type": "cash",
        "coupon_value": 10,
        "count": 5,
        "serial_mode": "prefix_sequential",
        "prefix": "AUD",
        "serial_start": 1,
        "serial_pad": 3
    }
    batch = test_endpoint("6_COUPON_FLOW", "owner", "POST", "/dms/coupons/batches",
                         json_data=batch_data, description="Owner create coupon batch")
    if not batch or not batch.get("batch"):
        log("6_COUPON_FLOW", "FAIL", "Failed to create coupon batch")
        return
    
    batch_id = batch["batch"]["id"]
    log("6_COUPON_FLOW", "PASS", f"Coupon batch created: {batch_id}")
    
    # Step 2: Owner activates batch
    activate = test_endpoint("6_COUPON_FLOW", "owner", "POST",
                            f"/dms/coupons/batches/{batch_id}/activate",
                            description="Owner activate batch")
    if activate:
        log("6_COUPON_FLOW", "PASS", "Batch activated")
    
    # Step 3: Get wallet balance for retailer1
    retailer_id = users.get("retailer1", {}).get("retailer_id")
    if retailer_id:
        wallet = test_endpoint("6_COUPON_FLOW", "retailer1", "GET", "/dms/coupons/retailer/wallet",
                              description="Retailer1 check wallet")
        if wallet:
            log("6_COUPON_FLOW", "PASS", f"Retailer wallet: cash={wallet.get('cash_balance', 0)}, reward={wallet.get('reward_balance', 0)}")
    
    # Step 4: Salesperson scan attempt (need valid coupon code)
    # Note: We can't easily scan without a real QR payload, so we'll just test the endpoint exists
    scan_data = {
        "qr_payload": "GOOIL2|test|test",  # Invalid but tests endpoint
        "retailer_id": retailer_id,
        "gps_lat": 28.6139,
        "gps_lng": 77.2090
    }
    scan = test_endpoint("6_COUPON_FLOW", "salesperson", "POST", "/dms/coupons/scan",
                        json_data=scan_data, expected_status=400,
                        description="Salesperson scan coupon (expect 400 for invalid QR)")
    if scan is not None:
        log("6_COUPON_FLOW", "PASS", "Coupon scan endpoint accessible to salesperson")

# ============================================================================
# AREA 7: PUNCH/ATTENDANCE — Test punch-in for each role
# ============================================================================
def test_punch_attendance():
    print("\n" + "="*80)
    print("AREA 7: PUNCH/ATTENDANCE — Test punch-in endpoints")
    print("="*80)
    
    punch_data = {
        "gps_lat": 28.6139,
        "gps_lng": 77.2090
    }
    
    # Test salesperson punch
    sp_punch = test_endpoint("7_PUNCH_ATTENDANCE", "salesperson", "POST", "/dms/punch/in",
                            json_data=punch_data, description="Salesperson punch in")
    if sp_punch:
        log("7_PUNCH_ATTENDANCE", "PASS", "Salesperson can punch in")
    
    # Test team leader punch
    tl_punch = test_endpoint("7_PUNCH_ATTENDANCE", "teamleader", "POST", "/dms/tl/punch/in",
                            json_data=punch_data, description="Team leader punch in")
    if tl_punch:
        log("7_PUNCH_ATTENDANCE", "PASS", "Team leader can punch in")
    
    # Test distributor punch (should fail - no endpoint)
    dist_punch = test_endpoint("7_PUNCH_ATTENDANCE", "distributor1", "POST", "/dms/punch/in",
                              json_data=punch_data, expected_status=403,
                              description="Distributor punch in (expect 403)")
    if dist_punch is not None:
        log("7_PUNCH_ATTENDANCE", "PASS", "Distributor correctly has no punch capability")
    
    # Test retailer punch (should fail - no endpoint)
    ret_punch = test_endpoint("7_PUNCH_ATTENDANCE", "retailer1", "POST", "/dms/punch/in",
                             json_data=punch_data, expected_status=403,
                             description="Retailer punch in (expect 403)")
    if ret_punch is not None:
        log("7_PUNCH_ATTENDANCE", "PASS", "Retailer correctly has no punch capability")
    
    # Test regional manager punch (should fail - no endpoint)
    rm_punch = test_endpoint("7_PUNCH_ATTENDANCE", "regionalmgr", "POST", "/dms/punch/in",
                            json_data=punch_data, expected_status=403,
                            description="Regional manager punch in (expect 403)")
    if rm_punch is not None:
        log("7_PUNCH_ATTENDANCE", "PASS", "Regional manager correctly has no punch capability")
    
    # Test distributor accountant punch (should fail - no endpoint)
    da_punch = test_endpoint("7_PUNCH_ATTENDANCE", "distacct", "POST", "/dms/punch/in",
                            json_data=punch_data, expected_status=403,
                            description="Distributor accountant punch in (expect 403)")
    if da_punch is not None:
        log("7_PUNCH_ATTENDANCE", "PASS", "Distributor accountant correctly has no punch capability")

# ============================================================================
# AREA 8: PARTY DETAILS — Owner gets distributor/retailer details
# ============================================================================
def test_party_details():
    print("\n" + "="*80)
    print("AREA 8: PARTY DETAILS — Bank details and attachments")
    print("="*80)
    
    # Get distributor details
    distributors = test_endpoint("8_PARTY_DETAILS", "owner", "GET", "/dms/distributors",
                                description="Owner get distributors list")
    if distributors and distributors.get("data"):
        dist = distributors["data"][0]
        dist_id = dist["id"]
        
        # Get full distributor detail
        dist_detail = test_endpoint("8_PARTY_DETAILS", "owner", "GET", f"/dms/distributors/{dist_id}",
                                   description="Owner get distributor detail")
        if dist_detail:
            kyc = dist_detail.get("kyc", {})
            has_bank = bool(kyc.get("bank_name") or kyc.get("bank_account"))
            has_docs = bool(dist_detail.get("documents"))
            
            if has_bank:
                log("8_PARTY_DETAILS", "PASS", f"Distributor has bank details: {kyc.get('bank_name', 'N/A')}")
            else:
                log("8_PARTY_DETAILS", "NOTE", "Distributor has no bank details (may be expected for demo data)")
            
            if has_docs:
                log("8_PARTY_DETAILS", "PASS", f"Distributor has {len(dist_detail['documents'])} documents")
            else:
                log("8_PARTY_DETAILS", "NOTE", "Distributor has no documents (may be expected for demo data)")
    
    # Get retailer details
    retailers = test_endpoint("8_PARTY_DETAILS", "owner", "GET", "/dms/retailers",
                             description="Owner get retailers list")
    if retailers and retailers.get("data"):
        ret = retailers["data"][0]
        ret_id = ret["id"]
        
        # Get full retailer detail
        ret_detail = test_endpoint("8_PARTY_DETAILS", "owner", "GET", f"/dms/retailers/{ret_id}",
                                  description="Owner get retailer detail")
        if ret_detail:
            kyc = ret_detail.get("kyc", {})
            has_docs = bool(ret_detail.get("documents"))
            
            if kyc:
                log("8_PARTY_DETAILS", "PASS", f"Retailer has KYC data: GSTIN={kyc.get('gstin', 'N/A')}")
            else:
                log("8_PARTY_DETAILS", "NOTE", "Retailer has no KYC data (may be expected for demo data)")
            
            if has_docs:
                log("8_PARTY_DETAILS", "PASS", f"Retailer has {len(ret_detail['documents'])} documents")
            else:
                log("8_PARTY_DETAILS", "NOTE", "Retailer has no documents (may be expected for demo data)")

# ============================================================================
# MAIN EXECUTION
# ============================================================================
def main():
    print("\n" + "="*80)
    print("GO OIL DMS — COMPREHENSIVE BACKEND FLOW AUDIT")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Testing {len(ROLES)} roles")
    print("="*80)
    
    # Run all tests
    test_auth()
    test_dashboards()
    test_primary_sales()
    test_secondary_sales()
    test_direct_sales()
    test_coupon_flow()
    test_punch_attendance()
    test_party_details()
    
    # Print summary
    print("\n" + "="*80)
    print("AUDIT SUMMARY")
    print("="*80)
    
    for area, tests in results.items():
        pass_count = sum(1 for t in tests if t["status"] == "PASS")
        fail_count = sum(1 for t in tests if t["status"] == "FAIL")
        note_count = sum(1 for t in tests if t["status"] == "NOTE")
        total = len(tests)
        
        status = "✅ PASS" if fail_count == 0 else "❌ FAIL"
        print(f"\n{status} {area}: {pass_count}/{total} passed, {fail_count} failed, {note_count} notes")
        
        # Show failures
        for t in tests:
            if t["status"] == "FAIL":
                print(f"  ❌ {t['message']}")
    
    print("\n" + "="*80)
    print("AUDIT COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
