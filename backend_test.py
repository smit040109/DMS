#!/usr/bin/env python3
"""
Backend API Testing for GO OIL DMS - NEW Coupon/Box Enhancements
Tests: Box Stats, Box Label PDF, Box Scan History, Fraud Alert Notifications, Regression
"""

import requests
import json
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "http://localhost:8001"
API_BASE = f"{BASE_URL}/api"

# Test credentials (password: GoOil@2026)
CREDENTIALS = {
    "owner": {"email": "owner@gooil.com", "password": "GoOil@2026"},
    "salesperson": {"email": "salesperson@gooil.com", "password": "GoOil@2026"},
    "retailer1": {"email": "retailer1@gooil.com", "password": "GoOil@2026"},
    "distributor1": {"email": "distributor1@gooil.com", "password": "GoOil@2026"},
    "distributor2": {"email": "distributor2@gooil.com", "password": "GoOil@2026"},
}

# Global tokens storage
tokens: Dict[str, str] = {}

# Test results tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "tests": []
}

def log_test(test_name: str, passed: bool, details: str = ""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")
    if details:
        print(f"  {details}")
    
    test_results["tests"].append({
        "name": test_name,
        "passed": passed,
        "details": details
    })
    
    if passed:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1

def login(role: str) -> Optional[str]:
    """Login and return token"""
    if role in tokens:
        return tokens[role]
    
    creds = CREDENTIALS.get(role)
    if not creds:
        print(f"❌ No credentials for role: {role}")
        return None
    
    try:
        resp = requests.post(f"{API_BASE}/auth/login", json=creds, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            # Token is in 'token' field (not 'access_token')
            token = data.get("token") or data.get("access_token")
            if token:
                tokens[role] = token
                print(f"✅ Login successful: {role} ({creds['email']})")
                return token
            else:
                print(f"❌ Login failed for {role}: No token in response")
                return None
        else:
            print(f"❌ Login failed for {role}: {resp.status_code} - {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Login exception for {role}: {e}")
        return None

def api_get(endpoint: str, token: str, params: Dict = None) -> requests.Response:
    """Make GET request with auth"""
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get(f"{API_BASE}{endpoint}", headers=headers, params=params, timeout=10)

def api_post(endpoint: str, token: str, data: Dict = None) -> requests.Response:
    """Make POST request with auth"""
    headers = {"Authorization": f"Bearer {token}"}
    return requests.post(f"{API_BASE}{endpoint}", headers=headers, json=data, timeout=10)

def api_put(endpoint: str, token: str, data: Dict = None) -> requests.Response:
    """Make PUT request with auth"""
    headers = {"Authorization": f"Bearer {token}"}
    return requests.put(f"{API_BASE}{endpoint}", headers=headers, json=data, timeout=10)

# ============================================================================
# TEST 1: BOX STATS + ROUTE ORDERING
# ============================================================================
def test_1_box_stats_and_route_ordering():
    """Test box stats endpoint and ensure route ordering doesn't shadow real box IDs"""
    print("\n" + "="*80)
    print("TEST 1: BOX STATS + ROUTE ORDERING")
    print("="*80)
    
    token = login("owner")
    if not token:
        log_test("TEST 1 - Login", False, "Owner login failed")
        return None, None
    
    # 1.1: GET /boxes/stats should return stats
    try:
        resp = api_get("/dms/coupons/boxes/stats", token)
        if resp.status_code == 200:
            data = resp.json()
            required_keys = ["boxes_total", "boxes_assigned", "boxes_unassigned", 
                           "coupons_in_boxes", "coupons_claimed"]
            missing = [k for k in required_keys if k not in data]
            if missing:
                log_test("TEST 1.1 - Box Stats Keys", False, f"Missing keys: {missing}")
            else:
                # Verify all values are integers
                all_ints = all(isinstance(data[k], int) for k in required_keys)
                if all_ints:
                    log_test("TEST 1.1 - Box Stats", True, 
                           f"Stats: total={data['boxes_total']}, assigned={data['boxes_assigned']}, "
                           f"unassigned={data['boxes_unassigned']}, in_boxes={data['coupons_in_boxes']}, "
                           f"claimed={data['coupons_claimed']}")
                else:
                    log_test("TEST 1.1 - Box Stats Types", False, "Not all values are integers")
        else:
            log_test("TEST 1.1 - Box Stats", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log_test("TEST 1.1 - Box Stats", False, f"Exception: {e}")
    
    # 1.2: Create a box to get a real box ID
    box_id = None
    box_number = None
    try:
        resp = api_post("/dms/coupons/boxes", token, {})
        if resp.status_code == 200:
            data = resp.json()
            box_id = data.get("box", {}).get("id")
            box_number = data.get("box", {}).get("box_number")
            if box_id and box_number:
                log_test("TEST 1.2 - Create Box", True, f"Created box: {box_number} (id={box_id})")
            else:
                log_test("TEST 1.2 - Create Box", False, "No box id/number in response")
        else:
            log_test("TEST 1.2 - Create Box", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log_test("TEST 1.2 - Create Box", False, f"Exception: {e}")
    
    # 1.3: GET /boxes/{bid} should resolve to the real box (not shadowed by /boxes/stats)
    if box_id:
        try:
            resp = api_get(f"/dms/coupons/boxes/{box_id}", token)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("box", {}).get("id") == box_id:
                    log_test("TEST 1.3 - Route Ordering", True, 
                           f"GET /boxes/{box_id} correctly resolves to box (not shadowed by /stats)")
                else:
                    log_test("TEST 1.3 - Route Ordering", False, "Box ID mismatch")
            else:
                log_test("TEST 1.3 - Route Ordering", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            log_test("TEST 1.3 - Route Ordering", False, f"Exception: {e}")
    else:
        log_test("TEST 1.3 - Route Ordering", False, "No box_id from previous test")
    
    return box_id, box_number

# ============================================================================
# TEST 2: BOX LABEL PDF
# ============================================================================
def test_2_box_label_pdf(box_id: Optional[str]):
    """Test box label PDF generation"""
    print("\n" + "="*80)
    print("TEST 2: BOX LABEL PDF")
    print("="*80)
    
    token = login("owner")
    if not token:
        log_test("TEST 2 - Login", False, "Owner login failed")
        return
    
    # 2.1: GET /boxes/{bid}/label-pdf should return PDF
    if box_id:
        try:
            resp = api_get(f"/dms/coupons/boxes/{box_id}/label-pdf", token)
            if resp.status_code == 200:
                content_type = resp.headers.get("content-type", "")
                size = len(resp.content)
                if "application/pdf" in content_type and size > 1000:
                    log_test("TEST 2.1 - Box Label PDF", True, 
                           f"PDF generated: {size} bytes, content-type={content_type}")
                else:
                    log_test("TEST 2.1 - Box Label PDF", False, 
                           f"Invalid PDF: size={size}, content-type={content_type}")
            else:
                log_test("TEST 2.1 - Box Label PDF", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            log_test("TEST 2.1 - Box Label PDF", False, f"Exception: {e}")
    else:
        log_test("TEST 2.1 - Box Label PDF", False, "No box_id from previous test")
    
    # 2.2: GET /boxes/BOGUSID/label-pdf should return 404
    try:
        resp = api_get("/dms/coupons/boxes/BOGUSID/label-pdf", token)
        if resp.status_code == 404:
            log_test("TEST 2.2 - Label PDF 404", True, "Bogus ID correctly returns 404")
        else:
            log_test("TEST 2.2 - Label PDF 404", False, f"Expected 404, got {resp.status_code}")
    except Exception as e:
        log_test("TEST 2.2 - Label PDF 404", False, f"Exception: {e}")
    
    # 2.3: Distributor should get 403 (owner_or_accountant only)
    dist_token = login("distributor1")
    if dist_token and box_id:
        try:
            resp = api_get(f"/dms/coupons/boxes/{box_id}/label-pdf", dist_token)
            if resp.status_code == 403:
                log_test("TEST 2.3 - Label PDF RBAC", True, "Distributor correctly blocked (403)")
            else:
                log_test("TEST 2.3 - Label PDF RBAC", False, 
                       f"Expected 403, got {resp.status_code}")
        except Exception as e:
            log_test("TEST 2.3 - Label PDF RBAC", False, f"Exception: {e}")
    else:
        log_test("TEST 2.3 - Label PDF RBAC", False, "No distributor token or box_id")

# ============================================================================
# TEST 3: FULL BOX FLOW + SCAN HISTORY + FRAUD ALERT
# ============================================================================
def test_3_full_box_flow_scan_history_fraud():
    """Test complete box flow with scan history and fraud detection"""
    print("\n" + "="*80)
    print("TEST 3: FULL BOX FLOW + SCAN HISTORY + FRAUD ALERT")
    print("="*80)
    
    token = login("owner")
    if not token:
        log_test("TEST 3 - Login", False, "Owner login failed")
        return
    
    # 3a: Create a coupon batch
    batch_id = None
    try:
        batch_data = {
            "prefix": "HB",
            "count": 20,
            "coupon_type": "reward",
            "coupon_value": 10,
            "generation_mode": "prefix_sequential"
        }
        resp = api_post("/dms/coupons/batches", token, batch_data)
        if resp.status_code == 200:
            data = resp.json()
            batch_id = data.get("batch", {}).get("id")
            if batch_id:
                log_test("TEST 3a - Create Batch", True, f"Batch created: {batch_id}")
            else:
                log_test("TEST 3a - Create Batch", False, "No batch_id in response")
        else:
            log_test("TEST 3a - Create Batch", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log_test("TEST 3a - Create Batch", False, f"Exception: {e}")
    
    if not batch_id:
        print("⚠️  Cannot continue TEST 3 without batch_id")
        return
    
    # 3a: Activate the batch
    try:
        resp = api_post(f"/dms/coupons/batches/{batch_id}/activate", token, {})
        if resp.status_code == 200:
            log_test("TEST 3a - Activate Batch", True, "Batch activated")
        else:
            log_test("TEST 3a - Activate Batch", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log_test("TEST 3a - Activate Batch", False, f"Exception: {e}")
    
    # 3b: Create a box
    box_id = None
    box_number = None
    try:
        resp = api_post("/dms/coupons/boxes", token, {})
        if resp.status_code == 200:
            data = resp.json()
            box_id = data.get("box", {}).get("id")
            box_number = data.get("box", {}).get("box_number")
            if box_id:
                log_test("TEST 3b - Create Box", True, f"Box created: {box_number}")
            else:
                log_test("TEST 3b - Create Box", False, "No box_id in response")
        else:
            log_test("TEST 3b - Create Box", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log_test("TEST 3b - Create Box", False, f"Exception: {e}")
    
    if not box_id:
        print("⚠️  Cannot continue TEST 3 without box_id")
        return
    
    # 3b: Assign coupons to box (first 10 from batch)
    assigned_serials = []
    try:
        assign_data = {
            "batch_id": batch_id,
            "from_serial": "HB001",
            "to_serial": "HB010"
        }
        resp = api_post(f"/dms/coupons/boxes/{box_id}/assign-coupons", token, assign_data)
        if resp.status_code == 200:
            data = resp.json()
            assigned = data.get("assigned", 0)
            if assigned > 0:
                assigned_serials = [f"HB{str(i).zfill(3)}" for i in range(1, assigned + 1)]
                log_test("TEST 3b - Assign Coupons", True, 
                       f"Assigned {assigned} coupons to box")
            else:
                log_test("TEST 3b - Assign Coupons", False, "No coupons assigned")
        else:
            log_test("TEST 3b - Assign Coupons", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log_test("TEST 3b - Assign Coupons", False, f"Exception: {e}")
    
    if not assigned_serials:
        print("⚠️  Cannot continue TEST 3 without assigned coupons")
        return
    
    # 3c: Get distributor1 ID
    distributor_id = None
    try:
        resp = api_get("/dms/distributors", token)
        if resp.status_code == 200:
            data = resp.json()
            distributors = data.get("data", [])
            # Find distributor with "Anil" or "Delhi" in name
            for d in distributors:
                if "Anil" in d.get("name", "") or "Delhi" in d.get("name", ""):
                    distributor_id = d.get("id")
                    log_test("TEST 3c - Get Distributor", True, 
                           f"Found distributor: {d.get('name')} (id={distributor_id})")
                    break
            if not distributor_id and distributors:
                # Fallback to first distributor
                distributor_id = distributors[0].get("id")
                log_test("TEST 3c - Get Distributor", True, 
                       f"Using first distributor: {distributors[0].get('name')}")
        else:
            log_test("TEST 3c - Get Distributor", False, f"HTTP {resp.status_code}")
    except Exception as e:
        log_test("TEST 3c - Get Distributor", False, f"Exception: {e}")
    
    if not distributor_id:
        print("⚠️  Cannot continue TEST 3 without distributor_id")
        return
    
    # 3c: Assign box to distributor
    try:
        assign_data = {"distributor_id": distributor_id}
        resp = api_post(f"/dms/coupons/boxes/{box_id}/assign-distributor", token, assign_data)
        if resp.status_code == 200:
            data = resp.json()
            coupons_updated = data.get("coupons_updated", 0)
            log_test("TEST 3c - Assign Distributor", True, 
                   f"Distributor assigned, {coupons_updated} coupons updated")
        else:
            log_test("TEST 3c - Assign Distributor", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log_test("TEST 3c - Assign Distributor", False, f"Exception: {e}")
    
    # 3d: Get retailer under this distributor
    retailer_id = None
    sp_token = login("salesperson")
    if sp_token:
        try:
            resp = api_get("/dms/coupons/so/retailers", sp_token)
            if resp.status_code == 200:
                data = resp.json()
                retailers = data.get("data", [])
                # Find retailer under our distributor
                for r in retailers:
                    if r.get("distributor_id") == distributor_id:
                        retailer_id = r.get("id")
                        log_test("TEST 3d - Get Retailer", True, 
                               f"Found retailer: {r.get('name')} under distributor")
                        break
                if not retailer_id and retailers:
                    # Fallback to first retailer
                    retailer_id = retailers[0].get("id")
                    log_test("TEST 3d - Get Retailer", True, 
                           f"Using first retailer: {retailers[0].get('name')}")
            else:
                log_test("TEST 3d - Get Retailer", False, f"HTTP {resp.status_code}")
        except Exception as e:
            log_test("TEST 3d - Get Retailer", False, f"Exception: {e}")
    
    if not retailer_id:
        print("⚠️  Cannot continue TEST 3 without retailer_id")
        return
    
    # 3e: Scan a boxed coupon (should succeed)
    scanned_serial = assigned_serials[0]
    if sp_token:
        try:
            scan_data = {
                "retailer_id": retailer_id,
                "coupon_code": scanned_serial
            }
            resp = api_post("/dms/coupons/scan", sp_token, scan_data)
            if resp.status_code == 200:
                data = resp.json()
                fraud = data.get("fraud", True)
                box_num = data.get("box_number")
                if not fraud and box_num:
                    log_test("TEST 3e - Scan Valid Coupon", True, 
                           f"Scan successful: fraud=False, box={box_num}, wallet credited")
                else:
                    log_test("TEST 3e - Scan Valid Coupon", False, 
                           f"Unexpected: fraud={fraud}, box_number={box_num}")
            else:
                log_test("TEST 3e - Scan Valid Coupon", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            log_test("TEST 3e - Scan Valid Coupon", False, f"Exception: {e}")
    
    # 3f: Get box scan history
    try:
        resp = api_get(f"/dms/coupons/boxes/{box_id}/scan-history", token)
        if resp.status_code == 200:
            data = resp.json()
            claimed_count = data.get("claimed_count", 0)
            scan_data = data.get("data", [])
            if claimed_count >= 1 and scan_data:
                # Check if scanned coupon is in history
                found = any(c.get("visible_serial") == scanned_serial for c in scan_data)
                has_retailer = any(c.get("retailer_name") for c in scan_data)
                has_claimed_by = any(c.get("claimed_by_user_name") for c in scan_data)
                has_timestamp = any(c.get("claim_timestamp") for c in scan_data)
                
                if found and has_retailer and has_claimed_by and has_timestamp:
                    log_test("TEST 3f - Box Scan History", True, 
                           f"Scan history: claimed={claimed_count}, scanned coupon present with all fields")
                else:
                    log_test("TEST 3f - Box Scan History", False, 
                           f"Missing fields: found={found}, retailer={has_retailer}, "
                           f"claimed_by={has_claimed_by}, timestamp={has_timestamp}")
            else:
                log_test("TEST 3f - Box Scan History", False, 
                       f"No scans in history: claimed_count={claimed_count}")
        else:
            log_test("TEST 3f - Box Scan History", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log_test("TEST 3f - Box Scan History", False, f"Exception: {e}")
    
    # 3g: Distributor2 should get 403 for scan history
    dist2_token = login("distributor2")
    if dist2_token:
        try:
            resp = api_get(f"/dms/coupons/boxes/{box_id}/scan-history", dist2_token)
            if resp.status_code == 403:
                log_test("TEST 3g - Scan History RBAC", True, 
                       "Distributor2 correctly blocked from other distributor's box (403)")
            else:
                log_test("TEST 3g - Scan History RBAC", False, 
                       f"Expected 403, got {resp.status_code}")
        except Exception as e:
            log_test("TEST 3g - Scan History RBAC", False, f"Exception: {e}")

# ============================================================================
# TEST 4: FRAUD ALERT NOTIFICATION
# ============================================================================
def test_4_fraud_alert_notification():
    """Test fraud alert notification creation"""
    print("\n" + "="*80)
    print("TEST 4: FRAUD ALERT NOTIFICATION")
    print("="*80)
    
    sp_token = login("salesperson")
    if not sp_token:
        log_test("TEST 4 - Login", False, "Salesperson login failed")
        return
    
    # Get a retailer
    retailer_id = None
    try:
        resp = api_get("/dms/coupons/so/retailers", sp_token)
        if resp.status_code == 200:
            data = resp.json()
            retailers = data.get("data", [])
            if retailers:
                retailer_id = retailers[0].get("id")
                log_test("TEST 4 - Get Retailer", True, f"Found retailer: {retailers[0].get('name')}")
        else:
            log_test("TEST 4 - Get Retailer", False, f"HTTP {resp.status_code}")
    except Exception as e:
        log_test("TEST 4 - Get Retailer", False, f"Exception: {e}")
    
    if not retailer_id:
        print("⚠️  Cannot continue TEST 4 without retailer_id")
        return
    
    # 4.1: Trigger fraud with invalid coupon code
    try:
        scan_data = {
            "retailer_id": retailer_id,
            "coupon_code": "ZZZZZ999"
        }
        resp = api_post("/dms/coupons/scan", sp_token, scan_data)
        if resp.status_code == 400:
            log_test("TEST 4.1 - Trigger Fraud", True, 
                   "Invalid coupon correctly rejected (400)")
        else:
            log_test("TEST 4.1 - Trigger Fraud", False, 
                   f"Expected 400, got {resp.status_code}")
    except Exception as e:
        log_test("TEST 4.1 - Trigger Fraud", False, f"Exception: {e}")
    
    # 4.2: Check owner notifications for fraud alert
    owner_token = login("owner")
    if owner_token:
        try:
            resp = api_get("/dms/notifications", owner_token)
            if resp.status_code == 200:
                data = resp.json()
                notifications = data.get("data", [])
                # Find recent fraud notification
                fraud_notifs = [n for n in notifications 
                              if n.get("kind") == "coupon_fraud" 
                              and "Fraud alert:" in n.get("title", "")]
                
                if fraud_notifs:
                    notif = fraud_notifs[0]
                    title = notif.get("title", "")
                    body = notif.get("body", "")
                    link = notif.get("link", "")
                    
                    has_title = title.startswith("Fraud alert:")
                    has_coupon = "ZZZZZ999" in body or "coupon" in body.lower()
                    has_location = any(x in body for x in ["GPS", "IP", "location"])
                    has_link = link == "/dms/owner/coupons/fraud"
                    
                    if has_title and has_coupon and has_location and has_link:
                        log_test("TEST 4.2 - Fraud Notification", True, 
                               f"Fraud notification found: kind=coupon_fraud, "
                               f"title='{title}', link={link}")
                    else:
                        log_test("TEST 4.2 - Fraud Notification", False, 
                               f"Incomplete notification: title={has_title}, "
                               f"coupon={has_coupon}, location={has_location}, link={has_link}")
                else:
                    log_test("TEST 4.2 - Fraud Notification", False, 
                           "No fraud notification found in owner's notifications")
            else:
                log_test("TEST 4.2 - Fraud Notification", False, f"HTTP {resp.status_code}")
        except Exception as e:
            log_test("TEST 4.2 - Fraud Notification", False, f"Exception: {e}")

# ============================================================================
# TEST 5: REGRESSION
# ============================================================================
def test_5_regression():
    """Test existing functionality still works"""
    print("\n" + "="*80)
    print("TEST 5: REGRESSION")
    print("="*80)
    
    token = login("owner")
    if not token:
        log_test("TEST 5 - Login", False, "Owner login failed")
        return
    
    # 5.1: GET /scan-permission
    try:
        resp = api_get("/dms/coupons/scan-permission", token)
        if resp.status_code == 200:
            data = resp.json()
            enabled = data.get("retailer_scan_enabled")
            log_test("TEST 5.1 - Get Scan Permission", True, 
                   f"Scan permission: enabled={enabled}")
        else:
            log_test("TEST 5.1 - Get Scan Permission", False, f"HTTP {resp.status_code}")
    except Exception as e:
        log_test("TEST 5.1 - Get Scan Permission", False, f"Exception: {e}")
    
    # 5.2: PUT /scan-permission (enable)
    try:
        resp = api_put("/dms/coupons/scan-permission", token, {"enabled": True})
        if resp.status_code == 200:
            log_test("TEST 5.2 - Enable Scan Permission", True, "Permission enabled")
        else:
            log_test("TEST 5.2 - Enable Scan Permission", False, f"HTTP {resp.status_code}")
    except Exception as e:
        log_test("TEST 5.2 - Enable Scan Permission", False, f"Exception: {e}")
    
    # 5.3: PUT /scan-permission (disable)
    try:
        resp = api_put("/dms/coupons/scan-permission", token, {"enabled": False})
        if resp.status_code == 200:
            log_test("TEST 5.3 - Disable Scan Permission", True, "Permission disabled")
        else:
            log_test("TEST 5.3 - Disable Scan Permission", False, f"HTTP {resp.status_code}")
    except Exception as e:
        log_test("TEST 5.3 - Disable Scan Permission", False, f"Exception: {e}")
    
    # 5.4: Box create → assign-coupons → assign-distributor sequence
    try:
        # Create box
        resp = api_post("/dms/coupons/boxes", token, {})
        if resp.status_code != 200:
            log_test("TEST 5.4 - Box Workflow", False, f"Create box failed: {resp.status_code}")
            return
        
        box_id = resp.json().get("box", {}).get("id")
        if not box_id:
            log_test("TEST 5.4 - Box Workflow", False, "No box_id in response")
            return
        
        # Get an existing batch with active coupons
        resp = api_get("/dms/coupons/batches", token)
        if resp.status_code != 200:
            log_test("TEST 5.4 - Box Workflow", False, f"Get batches failed: {resp.status_code}")
            return
        
        batches = resp.json().get("data", [])
        active_batch = None
        for b in batches:
            if b.get("status") == "active":
                active_batch = b
                break
        
        if not active_batch:
            log_test("TEST 5.4 - Box Workflow", False, "No active batch found")
            return
        
        # Assign coupons (try a small range)
        batch_id = active_batch.get("id")
        prefix = active_batch.get("prefix", "")
        assign_data = {
            "batch_id": batch_id,
            "from_serial": f"{prefix}011",
            "to_serial": f"{prefix}015"
        }
        resp = api_post(f"/dms/coupons/boxes/{box_id}/assign-coupons", token, assign_data)
        if resp.status_code != 200:
            # Try without batch_id filter
            assign_data = {
                "from_serial": f"{prefix}011",
                "to_serial": f"{prefix}015"
            }
            resp = api_post(f"/dms/coupons/boxes/{box_id}/assign-coupons", token, assign_data)
        
        if resp.status_code != 200:
            log_test("TEST 5.4 - Box Workflow", False, 
                   f"Assign coupons failed: {resp.status_code} - {resp.text[:200]}")
            return
        
        coupons_updated = resp.json().get("assigned", 0)
        if coupons_updated == 0:
            log_test("TEST 5.4 - Box Workflow", False, "No coupons assigned (might be already boxed)")
            return
        
        # Get distributor
        resp = api_get("/dms/distributors", token)
        if resp.status_code != 200:
            log_test("TEST 5.4 - Box Workflow", False, f"Get distributors failed: {resp.status_code}")
            return
        
        distributors = resp.json().get("data", [])
        if not distributors:
            log_test("TEST 5.4 - Box Workflow", False, "No distributors found")
            return
        
        distributor_id = distributors[0].get("id")
        
        # Assign distributor
        resp = api_post(f"/dms/coupons/boxes/{box_id}/assign-distributor", token, 
                       {"distributor_id": distributor_id})
        if resp.status_code == 200:
            data = resp.json()
            coupons_updated = data.get("coupons_updated", 0)
            if coupons_updated > 0:
                log_test("TEST 5.4 - Box Workflow", True, 
                       f"Complete workflow: box created → coupons assigned → "
                       f"distributor assigned ({coupons_updated} coupons updated)")
            else:
                log_test("TEST 5.4 - Box Workflow", False, "No coupons updated")
        else:
            log_test("TEST 5.4 - Box Workflow", False, 
                   f"Assign distributor failed: {resp.status_code}")
    except Exception as e:
        log_test("TEST 5.4 - Box Workflow", False, f"Exception: {e}")

# ============================================================================
# MAIN
# ============================================================================
def main():
    print("\n" + "="*80)
    print("GO OIL DMS - NEW COUPON/BOX ENHANCEMENTS - BACKEND API TESTING")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"API Base: {API_BASE}")
    print("="*80)
    
    # Run all tests
    box_id, box_number = test_1_box_stats_and_route_ordering()
    test_2_box_label_pdf(box_id)
    test_3_full_box_flow_scan_history_fraud()
    test_4_fraud_alert_notification()
    test_5_regression()
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    total = test_results["passed"] + test_results["failed"]
    pass_rate = (test_results["passed"] / total * 100) if total > 0 else 0
    print(f"Total Tests: {total}")
    print(f"Passed: {test_results['passed']} ✅")
    print(f"Failed: {test_results['failed']} ❌")
    print(f"Pass Rate: {pass_rate:.1f}%")
    print("="*80)
    
    # Print failed tests
    if test_results["failed"] > 0:
        print("\nFAILED TESTS:")
        for test in test_results["tests"]:
            if not test["passed"]:
                print(f"  ❌ {test['name']}")
                if test["details"]:
                    print(f"     {test['details']}")
    
    print("\n✅ Testing complete!")

if __name__ == "__main__":
    main()
