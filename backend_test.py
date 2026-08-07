#!/usr/bin/env python3
"""
Backend API Testing Script for GO OIL DMS - Box-Based Coupon Workflow
Tests the NEW box-based coupon business workflow as per review request.
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://25b62c98-87f3-43b6-86a6-61366389e44e.preview.emergentagent.com/api"
PASSWORD = "GoOil@2026"

# Test accounts
ACCOUNTS = {
    "owner": "owner@gooil.com",
    "accountant": "accountant@gooil.com",
    "distributor1": "distributor1@gooil.com",
    "distributor2": "distributor2@gooil.com",
    "salesperson": "salesperson@gooil.com",
    "retailer1": "retailer1@gooil.com",
    "retailer2": "retailer2@gooil.com",
}

# Global state
tokens = {}
test_data = {}
test_results = []


def log(message, level="INFO"):
    """Log test messages"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")


def login(role):
    """Login and get JWT token"""
    email = ACCOUNTS[role]
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": PASSWORD}
    )
    if response.status_code == 200:
        data = response.json()
        # Token is in 'token' field, not 'access_token'
        token = data.get("token")
        if token:
            tokens[role] = token
            log(f"✅ Login successful for {role} ({email})")
            return token
        else:
            log(f"❌ Login response missing 'token' field for {role}", "ERROR")
            return None
    else:
        log(f"❌ Login failed for {role}: {response.status_code} - {response.text}", "ERROR")
        return None


def api_call(method, endpoint, role, json_data=None, params=None, expect_status=200):
    """Make API call with authentication"""
    if role not in tokens:
        log(f"❌ No token for {role}, attempting login...", "WARN")
        if not login(role):
            log(f"❌ Login failed for {role}, cannot make API call", "ERROR")
            # Return a mock response object
            class MockResponse:
                status_code = None
                text = "Login failed"
            return MockResponse()
    
    headers = {"Authorization": f"Bearer {tokens[role]}"}
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=json_data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=json_data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            log(f"❌ Unsupported method: {method}", "ERROR")
            class MockResponse:
                status_code = None
                text = f"Unsupported method: {method}"
            return MockResponse()
        
        if response.status_code != expect_status:
            log(f"⚠️  {method} {endpoint} returned {response.status_code}, expected {expect_status}", "WARN")
            if response.status_code >= 400:
                log(f"   Response: {response.text[:200]}", "WARN")
        
        return response
    except Exception as e:
        log(f"❌ Exception during {method} {endpoint}: {str(e)}", "ERROR")
        class MockResponse:
            status_code = None
            text = str(e)
        return MockResponse()


def record_test(test_name, passed, details=""):
    """Record test result"""
    status = "✅ PASSED" if passed else "❌ FAILED"
    test_results.append({"test": test_name, "passed": passed, "details": details})
    log(f"{status}: {test_name} {details}")


# ============================================================================
# TEST 1 — BOX LIFECYCLE (owner)
# ============================================================================

def test_1_box_lifecycle():
    """Test complete box lifecycle: create batch → activate → create box → assign coupons → assign distributor"""
    log("\n" + "="*80)
    log("TEST 1 — BOX LIFECYCLE (owner)")
    log("="*80)
    
    # Step 1: Create a coupon batch
    log("\n[1.1] Creating coupon batch with prefix TESTBOX...")
    # Use timestamp to ensure unique prefix
    import time
    unique_suffix = str(int(time.time()))[-4:]
    prefix = f"TB{unique_suffix}"
    batch_payload = {
        "coupon_type": "cash",
        "coupon_value": 20,
        "count": 20,
        "serial_mode": "prefix_sequential",
        "prefix": prefix,
        "serial_start": 1,
        "serial_pad": 3
    }
    test_data["prefix"] = prefix
    resp = api_call("POST", "/dms/coupons/batches", "owner", json_data=batch_payload)
    if resp and resp.status_code == 200:
        batch_data = resp.json()
        batch = batch_data.get("batch", {})
        batch_id = batch.get("id")
        test_data["batch_id"] = batch_id
        record_test("1.1 Create batch", True, f"batch_id={batch_id}")
    else:
        record_test("1.1 Create batch", False, "Failed to create batch")
        return
    
    # Step 2: Activate the batch
    log("\n[1.2] Activating batch...")
    resp = api_call("POST", f"/dms/coupons/batches/{batch_id}/activate", "owner")
    if resp and resp.status_code == 200:
        record_test("1.2 Activate batch", True)
    else:
        record_test("1.2 Activate batch", False)
        return
    
    # Step 3: Create box
    log("\n[1.3] Creating box...")
    resp = api_call("POST", "/dms/coupons/boxes", "owner", json_data={})
    if resp and resp.status_code == 200:
        box_response = resp.json()
        box_data = box_response.get("box", {})
        box_id = box_data.get("id")
        box_number = box_data.get("box_number")
        status = box_data.get("status")
        test_data["box_id"] = box_id
        test_data["box_number"] = box_number
        if box_number and box_number.startswith("BOX") and status == "created":
            record_test("1.3 Create box", True, f"box_number={box_number}, status={status}")
        else:
            record_test("1.3 Create box", False, f"Invalid box_number or status: {box_number}, {status}")
            return
    else:
        record_test("1.3 Create box", False)
        return
    
    # Step 4: Assign coupon range to box
    log(f"\n[1.4] Assigning coupon range {prefix}001-{prefix}010 to box...")
    assign_payload = {
        "batch_id": batch_id,
        "from_serial": f"{prefix}001",
        "to_serial": f"{prefix}010"
    }
    resp = api_call("POST", f"/dms/coupons/boxes/{box_id}/assign-coupons", "owner", json_data=assign_payload)
    if resp and resp.status_code == 200:
        assign_data = resp.json()
        assigned = assign_data.get("assigned", 0)
        box_coupon_count = assign_data.get("box_coupon_count", 0)
        if assigned == 10 and box_coupon_count == 10:
            record_test("1.4 Assign coupons", True, f"assigned={assigned}, box_coupon_count={box_coupon_count}")
        else:
            record_test("1.4 Assign coupons", False, f"Expected 10 coupons, got assigned={assigned}, box_coupon_count={box_coupon_count}")
            return
    else:
        record_test("1.4 Assign coupons", False)
        return
    
    # Step 5: Get distributor ID
    log("\n[1.5] Getting distributor ID...")
    resp = api_call("GET", "/dms/distributors", "owner")
    if resp and resp.status_code == 200:
        distributors_response = resp.json()
        distributors = distributors_response.get("data", [])
        if distributors and len(distributors) > 0:
            distributor_id = distributors[0].get("id")
            distributor_name = distributors[0].get("name", "Unknown")
            test_data["distributor_id"] = distributor_id
            test_data["distributor_name"] = distributor_name
            record_test("1.5 Get distributor", True, f"distributor_id={distributor_id}, name={distributor_name}")
        else:
            record_test("1.5 Get distributor", False, "No distributors found")
            return
    else:
        record_test("1.5 Get distributor", False)
        return
    
    # Step 6: Assign distributor to box
    log("\n[1.6] Assigning distributor to box...")
    assign_dist_payload = {"distributor_id": distributor_id}
    resp = api_call("POST", f"/dms/coupons/boxes/{box_id}/assign-distributor", "owner", json_data=assign_dist_payload)
    if resp and resp.status_code == 200:
        dist_data = resp.json()
        coupons_updated = dist_data.get("coupons_updated", 0)
        if coupons_updated == 10:
            record_test("1.6 Assign distributor", True, f"coupons_updated={coupons_updated}")
        else:
            record_test("1.6 Assign distributor", False, f"Expected 10 coupons updated, got {coupons_updated}")
    else:
        record_test("1.6 Assign distributor", False)
        return
    
    # Step 7: Verify box details
    log("\n[1.7] Verifying box details...")
    resp = api_call("GET", f"/dms/coupons/boxes/{box_id}", "owner")
    if resp and resp.status_code == 200:
        box_detail_response = resp.json()
        box_detail = box_detail_response.get("box", {})
        count = box_detail.get("coupon_count", 0)
        dist_name = box_detail.get("distributor_name", "")
        box_status = box_detail.get("status", "")
        if count == 10 and dist_name and box_status == "assigned":
            record_test("1.7 Verify box details", True, f"count={count}, distributor={dist_name}, status={box_status}")
        else:
            record_test("1.7 Verify box details", False, f"Unexpected values: count={count}, distributor={dist_name}, status={box_status}")
    else:
        record_test("1.7 Verify box details", False)
    
    # Step 8: Verify box list
    log("\n[1.8] Verifying box list...")
    resp = api_call("GET", "/dms/coupons/boxes", "owner")
    if resp and resp.status_code == 200:
        boxes_response = resp.json()
        boxes = boxes_response.get("data", [])
        found = False
        for box in boxes:
            if box.get("id") == box_id:
                found = True
                break
        if found:
            record_test("1.8 Verify box list", True, f"Box {box_number} found in list")
        else:
            record_test("1.8 Verify box list", False, f"Box {box_number} not found in list")
    else:
        record_test("1.8 Verify box list", False)
    
    # Step 9: RBAC - owner_accountant CAN create box
    log("\n[1.9] RBAC: owner_accountant can create box...")
    resp = api_call("POST", "/dms/coupons/boxes", "accountant", json_data={})
    if resp and resp.status_code == 200:
        record_test("1.9 RBAC accountant create", True, "Owner accountant can create box")
    else:
        record_test("1.9 RBAC accountant create", False, f"Expected 200, got {resp.status_code if resp else 'None'}")
    
    # Step 10: RBAC - distributor CANNOT create box
    log("\n[1.10] RBAC: distributor1 cannot create box...")
    resp = api_call("POST", "/dms/coupons/boxes", "distributor1", json_data={}, expect_status=403)
    if resp and resp.status_code == 403:
        record_test("1.10 RBAC distributor create", True, "Distributor correctly blocked (403)")
    else:
        record_test("1.10 RBAC distributor create", False, f"Expected 403, got {resp.status_code if resp else 'None'}")
    
    # Step 11: RBAC - distributor CANNOT assign coupons
    log("\n[1.11] RBAC: distributor1 cannot assign coupons...")
    resp = api_call("POST", f"/dms/coupons/boxes/{box_id}/assign-coupons", "distributor1", 
                   json_data={"batch_id": batch_id, "from_serial": f"{prefix}011", "to_serial": f"{prefix}015"}, 
                   expect_status=403)
    if resp and resp.status_code == 403:
        record_test("1.11 RBAC distributor assign coupons", True, "Distributor correctly blocked (403)")
    else:
        record_test("1.11 RBAC distributor assign coupons", False, f"Expected 403, got {resp.status_code if resp else 'None'}")
    
    # Step 12: RBAC - distributor CANNOT assign distributor
    log("\n[1.12] RBAC: distributor1 cannot assign distributor...")
    resp = api_call("POST", f"/dms/coupons/boxes/{box_id}/assign-distributor", "distributor1", 
                   json_data={"distributor_id": distributor_id}, 
                   expect_status=403)
    if resp and resp.status_code == 403:
        record_test("1.12 RBAC distributor assign dist", True, "Distributor correctly blocked (403)")
    else:
        record_test("1.12 RBAC distributor assign dist", False, f"Expected 403, got {resp.status_code if resp else 'None'}")
    
    # Step 13: RBAC - distributor GET /boxes sees only own
    log("\n[1.13] RBAC: distributor1 sees only own boxes...")
    resp = api_call("GET", "/dms/coupons/boxes", "distributor1")
    if resp and resp.status_code == 200:
        boxes_response = resp.json()
        boxes = boxes_response.get("data", [])
        # Should see the box assigned to distributor1
        own_boxes = [b for b in boxes if b.get("distributor_id") == distributor_id]
        if len(own_boxes) > 0:
            record_test("1.13 RBAC distributor list", True, f"Distributor sees {len(own_boxes)} own box(es)")
        else:
            record_test("1.13 RBAC distributor list", False, "Distributor should see at least 1 box")
    else:
        record_test("1.13 RBAC distributor list", False)


# ============================================================================
# TEST 2 — SCAN PREVIEW + BOX FRAUD
# ============================================================================

def test_2_scan_preview_and_fraud():
    """Test scan preview and box fraud detection"""
    log("\n" + "="*80)
    log("TEST 2 — SCAN PREVIEW + BOX FRAUD")
    log("="*80)
    
    # Get the distributor and retailer info
    distributor_id = test_data.get("distributor_id")
    if not distributor_id:
        log("❌ No distributor_id from TEST 1, skipping TEST 2", "ERROR")
        return
    
    # Step 1: Get retailers under the distributor
    log("\n[2.1] Getting retailers under distributor...")
    resp = api_call("GET", "/dms/retailers", "owner")
    if resp and resp.status_code == 200:
        retailers_response = resp.json()
        retailers = retailers_response.get("data", [])
        retailer = None
        for r in retailers:
            if r.get("distributor_id") == distributor_id:
                retailer = r
                break
        
        if retailer:
            retailer_id = retailer.get("id")
            retailer_name = retailer.get("name", "Unknown")
            test_data["retailer_id"] = retailer_id
            test_data["retailer_name"] = retailer_name
            record_test("2.1 Get retailer", True, f"retailer_id={retailer_id}, name={retailer_name}")
        else:
            record_test("2.1 Get retailer", False, f"No retailer found under distributor {distributor_id}")
            return
    else:
        record_test("2.1 Get retailer", False)
        return
    
    # Step 2: Ensure salesperson is assigned to distributor
    log("\n[2.2] Checking salesperson assignment to distributor...")
    resp = api_call("GET", "/dms/assignments/sp-distributors", "owner")
    if resp and resp.status_code == 200:
        assignments_response = resp.json()
        assignments = assignments_response.get("data", [])
        sp_assigned = False
        for assignment in assignments:
            if assignment.get("distributor_id") == distributor_id:
                sp_assigned = True
                break
        
        if not sp_assigned:
            log("   Salesperson not assigned, creating assignment...")
            # Get salesperson user ID
            resp_users = api_call("GET", "/dms/owner/users", "owner")
            if resp_users and resp_users.status_code == 200:
                users = resp_users.json()
                sp_user = None
                for u in users:
                    if u.get("email") == ACCOUNTS["salesperson"]:
                        sp_user = u
                        break
                
                if sp_user:
                    sp_user_id = sp_user.get("id")
                    assign_payload = {
                        "salesperson_id": sp_user_id,
                        "distributor_id": distributor_id
                    }
                    resp_assign = api_call("POST", "/dms/assignments/sp-distributors", "owner", json_data=assign_payload)
                    if resp_assign and resp_assign.status_code == 200:
                        record_test("2.2 SP assignment", True, "Salesperson assigned to distributor")
                    else:
                        record_test("2.2 SP assignment", False, "Failed to assign salesperson")
                        return
                else:
                    record_test("2.2 SP assignment", False, "Salesperson user not found")
                    return
            else:
                record_test("2.2 SP assignment", False, "Failed to get users")
                return
        else:
            record_test("2.2 SP assignment", True, "Salesperson already assigned")
    else:
        record_test("2.2 SP assignment", False)
        return
    
    # Step 3: Scan preview - valid coupon (fraud=false)
    prefix = test_data.get("prefix", "TB")
    log(f"\n[2.3] Scan preview with valid coupon ({prefix}001)...")
    preview_payload = {
        "retailer_id": retailer_id,
        "coupon_code": f"{prefix}001"
    }
    resp = api_call("POST", "/dms/coupons/scan/preview", "salesperson", json_data=preview_payload)
    if resp and resp.status_code == 200:
        preview_data = resp.json()
        fraud = preview_data.get("fraud", True)
        box_number = preview_data.get("box_number", "")
        coupon_type = preview_data.get("coupon_type", "")
        coupon_value = preview_data.get("coupon_value", 0)
        distributor_name = preview_data.get("distributor_name", "")
        retailer_name_resp = preview_data.get("retailer_name", "")
        
        if not fraud and box_number and coupon_type == "cash" and coupon_value == 20:
            record_test("2.3 Scan preview valid", True, 
                       f"fraud={fraud}, box={box_number}, type={coupon_type}, value={coupon_value}")
        else:
            record_test("2.3 Scan preview valid", False, 
                       f"Unexpected values: fraud={fraud}, box={box_number}, type={coupon_type}, value={coupon_value}")
    else:
        record_test("2.3 Scan preview valid", False)
    
    # Step 4: Scan submit - valid coupon
    log(f"\n[2.4] Scan submit with valid coupon ({prefix}001)...")
    scan_payload = {
        "retailer_id": retailer_id,
        "coupon_code": f"{prefix}001"
    }
    resp = api_call("POST", "/dms/coupons/scan", "salesperson", json_data=scan_payload)
    if resp and resp.status_code == 200:
        scan_data = resp.json()
        ok = scan_data.get("ok", False)
        fraud = scan_data.get("fraud", True)
        box_number = scan_data.get("box_number", "")
        
        if ok and not fraud and box_number:
            record_test("2.4 Scan submit valid", True, f"ok={ok}, fraud={fraud}, box={box_number}")
        else:
            record_test("2.4 Scan submit valid", False, f"Unexpected values: ok={ok}, fraud={fraud}, box={box_number}")
    else:
        record_test("2.4 Scan submit valid", False)
    
    # Step 5: NEGATIVE - wrong_distributor fraud
    log("\n[2.5] NEGATIVE: Create 2nd box for different distributor...")
    # Create another batch with unique prefix
    import time
    unique_suffix2 = str(int(time.time()))[-4:]
    prefix2 = f"TB{unique_suffix2}X"
    batch2_payload = {
        "coupon_type": "cash",
        "coupon_value": 20,
        "count": 20,
        "serial_mode": "prefix_sequential",
        "prefix": prefix2,
        "serial_start": 1,
        "serial_pad": 3
    }
    resp = api_call("POST", "/dms/coupons/batches", "owner", json_data=batch2_payload)
    if resp and resp.status_code == 200:
        batch2_id = resp.json().get("batch", {}).get("id")
        
        # Activate batch2
        resp = api_call("POST", f"/dms/coupons/batches/{batch2_id}/activate", "owner")
        if resp and resp.status_code == 200:
            # Create box2
            resp = api_call("POST", "/dms/coupons/boxes", "owner", json_data={})
            if resp and resp.status_code == 200:
                box2_id = resp.json().get("id")
                
                # Assign coupons to box2
                assign2_payload = {
                    "batch_id": batch2_id,
                    "from_serial": f"{prefix2}001",
                    "to_serial": f"{prefix2}010"
                }
                resp = api_call("POST", f"/dms/coupons/boxes/{box2_id}/assign-coupons", "owner", json_data=assign2_payload)
                if resp and resp.status_code == 200:
                    # Get distributor2 ID
                    resp = api_call("GET", "/dms/distributors", "owner")
                    if resp and resp.status_code == 200:
                        distributors_response = resp.json()
                        distributors = distributors_response.get("data", [])
                        distributor2_id = None
                        for d in distributors:
                            if d.get("id") != distributor_id:
                                distributor2_id = d.get("id")
                                break
                        
                        if distributor2_id:
                            # Assign box2 to distributor2
                            assign_dist2_payload = {"distributor_id": distributor2_id}
                            resp = api_call("POST", f"/dms/coupons/boxes/{box2_id}/assign-distributor", "owner", json_data=assign_dist2_payload)
                            if resp and resp.status_code == 200:
                                # Now scan coupon from wrong distributor's box (should be fraud)
                                log("\n[2.5] Scanning coupon from wrong distributor's box...")
                                preview_wrong_payload = {
                                    "retailer_id": retailer_id,
                                    "coupon_code": f"{prefix2}001"
                                }
                                resp = api_call("POST", "/dms/coupons/scan/preview", "salesperson", json_data=preview_wrong_payload)
                                if resp and resp.status_code == 200:
                                    preview_data = resp.json()
                                    fraud = preview_data.get("fraud", False)
                                    fraud_reason = preview_data.get("fraud_reason", "")
                                    
                                    if fraud and fraud_reason == "wrong_distributor":
                                        record_test("2.5 Fraud wrong_distributor preview", True, f"fraud={fraud}, reason={fraud_reason}")
                                        
                                        # Try to submit (should be 400)
                                        log("\n[2.5b] Submitting coupon from wrong distributor (should fail)...")
                                        resp = api_call("POST", "/dms/coupons/scan", "salesperson", json_data=preview_wrong_payload, expect_status=400)
                                        if resp and resp.status_code == 400:
                                            record_test("2.5b Fraud wrong_distributor submit", True, "Submit correctly blocked (400)")
                                            
                                            # Verify fraud log
                                            log("\n[2.5c] Verifying fraud log entry...")
                                            resp = api_call("GET", "/dms/coupons/reports/fraud", "owner")
                                            if resp and resp.status_code == 200:
                                                fraud_logs = resp.json()
                                                found_wrong_dist = False
                                                for log_entry in fraud_logs:
                                                    if log_entry.get("reason") == "wrong_distributor":
                                                        found_wrong_dist = True
                                                        break
                                                
                                                if found_wrong_dist:
                                                    record_test("2.5c Fraud log entry", True, "wrong_distributor entry found in fraud log")
                                                else:
                                                    record_test("2.5c Fraud log entry", False, "wrong_distributor entry not found in fraud log")
                                            else:
                                                record_test("2.5c Fraud log entry", False, "Failed to get fraud log")
                                        else:
                                            record_test("2.5b Fraud wrong_distributor submit", False, f"Expected 400, got {resp.status_code if resp else 'None'}")
                                    else:
                                        record_test("2.5 Fraud wrong_distributor preview", False, f"Expected fraud=true with reason=wrong_distributor, got fraud={fraud}, reason={fraud_reason}")
                                else:
                                    record_test("2.5 Fraud wrong_distributor preview", False)
                            else:
                                record_test("2.5 Setup box2", False, "Failed to assign distributor2 to box2")
                        else:
                            record_test("2.5 Setup box2", False, "No second distributor found")
                    else:
                        record_test("2.5 Setup box2", False, "Failed to get distributors")
                else:
                    record_test("2.5 Setup box2", False, "Failed to assign coupons to box2")
            else:
                record_test("2.5 Setup box2", False, "Failed to create box2")
        else:
            record_test("2.5 Setup box2", False, "Failed to activate batch2")
    else:
        record_test("2.5 Setup box2", False, "Failed to create batch2")
    
    # Step 6: NEGATIVE - not_assigned fraud
    log("\n[2.6] NEGATIVE: Scan coupon not assigned to any box...")
    # Create batch3 and activate but don't box it
    import time
    unique_suffix3 = str(int(time.time()))[-4:]
    prefix3 = f"TB{unique_suffix3}Y"
    batch3_payload = {
        "coupon_type": "cash",
        "coupon_value": 20,
        "count": 10,
        "serial_mode": "prefix_sequential",
        "prefix": prefix3,
        "serial_start": 1,
        "serial_pad": 3
    }
    resp = api_call("POST", "/dms/coupons/batches", "owner", json_data=batch3_payload)
    if resp and resp.status_code == 200:
        batch3_id = resp.json().get("batch", {}).get("id")
        
        # Activate batch3
        resp = api_call("POST", f"/dms/coupons/batches/{batch3_id}/activate", "owner")
        if resp and resp.status_code == 200:
            # Don't create box, just scan
            preview_not_assigned_payload = {
                "retailer_id": retailer_id,
                "coupon_code": f"{prefix3}001"
            }
            resp = api_call("POST", "/dms/coupons/scan/preview", "salesperson", json_data=preview_not_assigned_payload)
            if resp and resp.status_code == 200:
                preview_data = resp.json()
                fraud = preview_data.get("fraud", False)
                fraud_reason = preview_data.get("fraud_reason", "")
                
                if fraud and fraud_reason == "not_assigned":
                    record_test("2.6 Fraud not_assigned", True, f"fraud={fraud}, reason={fraud_reason}")
                else:
                    record_test("2.6 Fraud not_assigned", False, f"Expected fraud=true with reason=not_assigned, got fraud={fraud}, reason={fraud_reason}")
            else:
                record_test("2.6 Fraud not_assigned", False)
        else:
            record_test("2.6 Setup batch3", False, "Failed to activate batch3")
    else:
        record_test("2.6 Setup batch3", False, "Failed to create batch3")


# ============================================================================
# TEST 3 — RETAILER SCAN PERMISSION
# ============================================================================

def test_3_retailer_scan_permission():
    """Test retailer scan permission toggle"""
    log("\n" + "="*80)
    log("TEST 3 — RETAILER SCAN PERMISSION")
    log("="*80)
    
    retailer_id = test_data.get("retailer_id")
    if not retailer_id:
        log("❌ No retailer_id from TEST 2, skipping TEST 3", "ERROR")
        return
    
    # Step 1: Get scan permission (should be false by default)
    log("\n[3.1] Getting scan permission (should be false)...")
    resp = api_call("GET", "/dms/coupons/scan-permission", "owner")
    if resp and resp.status_code == 200:
        perm_data = resp.json()
        enabled = perm_data.get("retailer_scan_enabled", True)
        if not enabled:
            record_test("3.1 Get permission default", True, f"retailer_scan_enabled={enabled}")
        else:
            record_test("3.1 Get permission default", False, f"Expected false, got {enabled}")
    else:
        record_test("3.1 Get permission default", False)
    
    # Step 2: Retailer scan preview when disabled (should be 403)
    log("\n[3.2] Retailer scan preview when disabled (should be 403)...")
    prefix = test_data.get("prefix", "TB")
    preview_payload = {
        "coupon_code": f"{prefix}002"  # Use a different coupon from the box
    }
    resp = api_call("POST", "/dms/coupons/retailer/scan/preview", "retailer1", json_data=preview_payload, expect_status=403)
    if resp and resp.status_code == 403:
        record_test("3.2 Retailer preview disabled", True, "Retailer correctly blocked (403)")
    else:
        record_test("3.2 Retailer preview disabled", False, f"Expected 403, got {resp.status_code if resp else 'None'}")
    
    # Step 3: Enable retailer scan permission
    log("\n[3.3] Enabling retailer scan permission...")
    enable_payload = {"enabled": True}
    resp = api_call("PUT", "/dms/coupons/scan-permission", "owner", json_data=enable_payload)
    if resp and resp.status_code == 200:
        record_test("3.3 Enable permission", True)
    else:
        record_test("3.3 Enable permission", False)
        return
    
    # Step 4: Retailer scan preview when enabled (should be 200)
    log("\n[3.4] Retailer scan preview when enabled (should be 200)...")
    preview_payload = {
        "coupon_code": f"{prefix}002"
    }
    resp = api_call("POST", "/dms/coupons/retailer/scan/preview", "retailer1", json_data=preview_payload)
    if resp and resp.status_code == 200:
        preview_data = resp.json()
        fraud = preview_data.get("fraud", True)
        if not fraud:
            record_test("3.4 Retailer preview enabled", True, f"fraud={fraud}")
        else:
            record_test("3.4 Retailer preview enabled", False, f"Expected fraud=false, got {fraud}")
    else:
        record_test("3.4 Retailer preview enabled", False)
    
    # Step 5: Retailer scan submit (should credit wallet)
    log("\n[3.5] Retailer scan submit (should credit wallet)...")
    # First get current wallet balance
    resp = api_call("GET", "/dms/coupons/retailer/wallet", "retailer1")
    if resp and resp.status_code == 200:
        wallet_before = resp.json().get("balance", 0)
        
        # Submit scan
        scan_payload = {
            "coupon_code": f"{prefix}002"
        }
        resp = api_call("POST", "/dms/coupons/retailer/scan", "retailer1", json_data=scan_payload)
        if resp and resp.status_code == 200:
            scan_data = resp.json()
            ok = scan_data.get("ok", False)
            
            if ok:
                # Check wallet balance increased
                resp = api_call("GET", "/dms/coupons/retailer/wallet", "retailer1")
                if resp and resp.status_code == 200:
                    wallet_after = resp.json().get("balance", 0)
                    if wallet_after > wallet_before:
                        record_test("3.5 Retailer scan submit", True, f"Wallet increased: {wallet_before} → {wallet_after}")
                    else:
                        record_test("3.5 Retailer scan submit", False, f"Wallet not increased: {wallet_before} → {wallet_after}")
                else:
                    record_test("3.5 Retailer scan submit", False, "Failed to get wallet after scan")
            else:
                record_test("3.5 Retailer scan submit", False, f"Scan not ok: {scan_data}")
        else:
            record_test("3.5 Retailer scan submit", False)
    else:
        record_test("3.5 Retailer scan submit", False, "Failed to get wallet before scan")
    
    # Step 6: Disable retailer scan permission
    log("\n[3.6] Disabling retailer scan permission...")
    disable_payload = {"enabled": False}
    resp = api_call("PUT", "/dms/coupons/scan-permission", "owner", json_data=disable_payload)
    if resp and resp.status_code == 200:
        record_test("3.6 Disable permission", True)
    else:
        record_test("3.6 Disable permission", False)
        return
    
    # Step 7: Retailer scan preview when disabled again (should be 403)
    log("\n[3.7] Retailer scan preview when disabled again (should be 403)...")
    preview_payload = {
        "coupon_code": f"{prefix}003"
    }
    resp = api_call("POST", "/dms/coupons/retailer/scan/preview", "retailer1", json_data=preview_payload, expect_status=403)
    if resp and resp.status_code == 403:
        record_test("3.7 Retailer preview disabled again", True, "Retailer correctly blocked (403)")
    else:
        record_test("3.7 Retailer preview disabled again", False, f"Expected 403, got {resp.status_code if resp else 'None'}")


# ============================================================================
# TEST 4 — REGRESSION (no 500s)
# ============================================================================

def test_4_regression():
    """Test regression - existing endpoints should still work"""
    log("\n" + "="*80)
    log("TEST 4 — REGRESSION (no 500s)")
    log("="*80)
    
    # Step 1: Coupon reports summary
    log("\n[4.1] Testing coupon reports summary...")
    resp = api_call("GET", "/dms/coupons/reports/summary", "owner")
    if resp and resp.status_code == 200:
        record_test("4.1 Reports summary", True)
    else:
        record_test("4.1 Reports summary", False, f"Status: {resp.status_code if resp else 'None'}")
    
    # Step 2: Fraud dashboard
    log("\n[4.2] Testing fraud dashboard...")
    resp = api_call("GET", "/dms/coupons/reports/fraud-dashboard", "owner")
    if resp and resp.status_code == 200:
        record_test("4.2 Fraud dashboard", True)
    else:
        record_test("4.2 Fraud dashboard", False, f"Status: {resp.status_code if resp else 'None'}")
    
    # Step 3: Print export-pdf
    log("\n[4.3] Testing print export-pdf...")
    batch_id = test_data.get("batch_id")
    if batch_id:
        resp = api_call("GET", f"/dms/coupons/batches/{batch_id}/export-pdf", "owner", params={"side": "both"})
        if resp and resp.status_code == 200:
            content_type = resp.headers.get("content-type", "")
            if "application/pdf" in content_type:
                record_test("4.3 Print export-pdf", True, f"Content-Type: {content_type}")
            else:
                record_test("4.3 Print export-pdf", False, f"Expected PDF, got {content_type}")
        else:
            record_test("4.3 Print export-pdf", False, f"Status: {resp.status_code if resp else 'None'}")
    else:
        record_test("4.3 Print export-pdf", False, "No batch_id available")
    
    # Step 4: Activation preview
    log("\n[4.4] Testing activation preview...")
    batch_id = test_data.get("batch_id")
    prefix = test_data.get("prefix", "TB")
    if batch_id:
        resp = api_call("POST", "/dms/coupons/activate-range/preview", "owner", 
                       json_data={"batch_id": batch_id, "from_serial": f"{prefix}001", "to_serial": f"{prefix}005"})
        if resp and resp.status_code == 200:
            record_test("4.4 Activation preview", True)
        else:
            record_test("4.4 Activation preview", False, f"Status: {resp.status_code if resp else 'None'}")
    else:
        record_test("4.4 Activation preview", False, "No batch_id available")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main test runner"""
    log("="*80)
    log("GO OIL DMS - Box-Based Coupon Workflow Backend Testing")
    log("="*80)
    
    # Login all accounts
    log("\n[SETUP] Logging in all test accounts...")
    for role in ACCOUNTS.keys():
        login(role)
    
    # Run tests
    test_1_box_lifecycle()
    test_2_scan_preview_and_fraud()
    test_3_retailer_scan_permission()
    test_4_regression()
    
    # Summary
    log("\n" + "="*80)
    log("TEST SUMMARY")
    log("="*80)
    
    passed = sum(1 for t in test_results if t["passed"])
    failed = sum(1 for t in test_results if not t["passed"])
    total = len(test_results)
    
    log(f"\nTotal Tests: {total}")
    log(f"✅ Passed: {passed}")
    log(f"❌ Failed: {failed}")
    log(f"Success Rate: {(passed/total*100):.1f}%")
    
    if failed > 0:
        log("\n❌ FAILED TESTS:")
        for t in test_results:
            if not t["passed"]:
                log(f"   - {t['test']}: {t['details']}")
    
    log("\n" + "="*80)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
