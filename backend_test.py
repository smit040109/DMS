#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Coupon Engine v2 Follow-up Features
==========================================================================

Testing 7 scenarios from review request:
1. hidden_secure_id NOW visible to Owner + Accountant
2. Sensitive crypto material still hidden
3. NEW: QR image endpoint
4. NEW: QR payload endpoint
5. NEW: Bulk activate by IDs
6. NEW: Range activation with SERIAL FORMAT (smart normalization)
7. Regression on existing endpoints
"""

import requests
import json
import sys
import time
from typing import Dict, Any, List, Optional

# Backend URL from frontend/.env
BASE_URL = "https://loyalty-qr-system-3.preview.emergentagent.com/api"

# Generate unique prefix for test batches
TEST_PREFIX = f"T{int(time.time()) % 100000}"

# Test credentials from /app/memory/test_credentials.md
OWNER_EMAIL = "owner@gooil.com"
OWNER_PASSWORD = "GoOil@2026"
ACCOUNTANT_EMAIL = "accountant@gooil.com"
ACCOUNTANT_PASSWORD = "GoOil@2026"
RETAILER1_EMAIL = "retailer1@gooil.com"
RETAILER1_PASSWORD = "GoOil@2026"
DISTRIBUTOR1_EMAIL = "distributor1@gooil.com"
DISTRIBUTOR1_PASSWORD = "GoOil@2026"

# Test results tracking
test_results = []
total_tests = 0
passed_tests = 0


def log_test(scenario: str, test_name: str, passed: bool, details: str = ""):
    """Log test result"""
    global total_tests, passed_tests
    total_tests += 1
    if passed:
        passed_tests += 1
    status = "✅ PASS" if passed else "❌ FAIL"
    test_results.append({
        "scenario": scenario,
        "test": test_name,
        "status": status,
        "passed": passed,
        "details": details
    })
    print(f"{status} | {scenario} | {test_name}")
    if details and not passed:
        print(f"  Details: {details}")


def login(email: str, password: str) -> Optional[str]:
    """Login and return JWT token"""
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": email,
            "password": password
        }, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("token")
        else:
            print(f"❌ Login failed for {email}: {resp.status_code} {resp.text}")
            return None
    except Exception as e:
        print(f"❌ Login exception for {email}: {e}")
        return None


def get_headers(token: str) -> Dict[str, str]:
    """Get headers with auth token"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def test_scenario_1_hidden_secure_id_visible():
    """
    SCENARIO 1: hidden_secure_id is NOW visible to Owner + Accountant
    """
    print("\n" + "="*80)
    print("SCENARIO 1: hidden_secure_id NOW visible to Owner + Accountant")
    print("="*80)
    
    # Test 1a: Login as owner
    owner_token = login(OWNER_EMAIL, OWNER_PASSWORD)
    log_test("1", "Login as owner@gooil.com", owner_token is not None)
    if not owner_token:
        return
    
    # Test 1b: GET /api/dms/coupons?limit=5 as owner
    try:
        resp = requests.get(
            f"{BASE_URL}/dms/coupons?limit=5",
            headers=get_headers(owner_token),
            timeout=10
        )
        log_test("1", "GET /api/dms/coupons?limit=5 as owner", resp.status_code == 200,
                f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            coupons = data.get("data", [])
            
            # Test 1c: Check if coupons exist
            log_test("1", "Coupons list not empty", len(coupons) > 0,
                    f"Count: {len(coupons)}")
            
            if len(coupons) > 0:
                first_coupon = coupons[0]
                
                # Test 1d: Check hidden_secure_id field exists
                has_hidden_id = "hidden_secure_id" in first_coupon
                log_test("1", "hidden_secure_id field present", has_hidden_id,
                        f"Fields: {list(first_coupon.keys())}")
                
                # Test 1e: Check hidden_secure_id is a valid UUID v4
                if has_hidden_id:
                    hidden_id = first_coupon.get("hidden_secure_id")
                    is_uuid = hidden_id and len(str(hidden_id)) == 36 and "-" in str(hidden_id)
                    log_test("1", "hidden_secure_id is UUID format", is_uuid,
                            f"Value: {hidden_id}")
    except Exception as e:
        log_test("1", "GET /api/dms/coupons exception", False, str(e))
    
    # Test 1f: Login as accountant
    accountant_token = login(ACCOUNTANT_EMAIL, ACCOUNTANT_PASSWORD)
    log_test("1", "Login as accountant@gooil.com", accountant_token is not None)
    
    if accountant_token:
        # Test 1g: GET /api/dms/coupons?limit=5 as accountant
        try:
            resp = requests.get(
                f"{BASE_URL}/dms/coupons?limit=5",
                headers=get_headers(accountant_token),
                timeout=10
            )
            log_test("1", "GET /api/dms/coupons?limit=5 as accountant", resp.status_code == 200,
                    f"Status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                coupons = data.get("data", [])
                if len(coupons) > 0:
                    has_hidden_id = "hidden_secure_id" in coupons[0]
                    log_test("1", "Accountant sees hidden_secure_id", has_hidden_id)
        except Exception as e:
            log_test("1", "GET /api/dms/coupons as accountant exception", False, str(e))
    
    # Test 1h: GET /api/dms/coupons as retailer1 → 403
    retailer_token = login(RETAILER1_EMAIL, RETAILER1_PASSWORD)
    if retailer_token:
        try:
            resp = requests.get(
                f"{BASE_URL}/dms/coupons?limit=5",
                headers=get_headers(retailer_token),
                timeout=10
            )
            log_test("1", "GET /api/dms/coupons as retailer → 403", resp.status_code == 403,
                    f"Status: {resp.status_code}")
        except Exception as e:
            log_test("1", "GET /api/dms/coupons as retailer exception", False, str(e))


def test_scenario_2_sensitive_crypto_hidden():
    """
    SCENARIO 2: Sensitive crypto material still hidden
    """
    print("\n" + "="*80)
    print("SCENARIO 2: Sensitive crypto material still hidden")
    print("="*80)
    
    owner_token = login(OWNER_EMAIL, OWNER_PASSWORD)
    if not owner_token:
        log_test("2", "Login as owner", False, "Login failed")
        return
    
    try:
        resp = requests.get(
            f"{BASE_URL}/dms/coupons?limit=5",
            headers=get_headers(owner_token),
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            coupons = data.get("data", [])
            
            if len(coupons) > 0:
                first_coupon = coupons[0]
                
                # Check that sensitive fields are NOT present
                forbidden_fields = ["secret_token", "signature", "qr_ciphertext_b64", 
                                   "qr_signature_v2", "qr_hash"]
                
                for field in forbidden_fields:
                    is_hidden = field not in first_coupon
                    log_test("2", f"{field} NOT in response", is_hidden,
                            f"Present: {field in first_coupon}")
                
                # Test 2f: Verify visible_serial IS present (public field)
                has_visible_serial = "visible_serial" in first_coupon or "coupon_code" in first_coupon
                log_test("2", "visible_serial or coupon_code present", has_visible_serial)
            else:
                log_test("2", "No coupons to test", False, "Empty coupon list")
        else:
            log_test("2", "GET /api/dms/coupons failed", False, f"Status: {resp.status_code}")
    except Exception as e:
        log_test("2", "Sensitive crypto check exception", False, str(e))


def test_scenario_3_qr_image_endpoint():
    """
    SCENARIO 3: NEW: QR image endpoint
    """
    print("\n" + "="*80)
    print("SCENARIO 3: NEW: QR image endpoint")
    print("="*80)
    
    owner_token = login(OWNER_EMAIL, OWNER_PASSWORD)
    if not owner_token:
        log_test("3", "Login as owner", False, "Login failed")
        return
    
    # First, get a coupon ID
    try:
        resp = requests.get(
            f"{BASE_URL}/dms/coupons?limit=1",
            headers=get_headers(owner_token),
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            coupons = data.get("data", [])
            
            if len(coupons) > 0:
                coupon_id = coupons[0].get("id")
                log_test("3", "Got coupon ID for testing", coupon_id is not None,
                        f"ID: {coupon_id}")
                
                if coupon_id:
                    # Test 3a: GET /api/dms/coupons/coupons/{cid}/qr-image as owner
                    try:
                        resp = requests.get(
                            f"{BASE_URL}/dms/coupons/coupons/{coupon_id}/qr-image?size=6",
                            headers=get_headers(owner_token),
                            timeout=10
                        )
                        
                        # Test 3b: Check status 200
                        log_test("3", "GET qr-image as owner → 200", resp.status_code == 200,
                                f"Status: {resp.status_code}")
                        
                        if resp.status_code == 200:
                            # Test 3c: Check Content-Type
                            content_type = resp.headers.get("Content-Type", "")
                            is_png = "image/png" in content_type
                            log_test("3", "Content-Type: image/png", is_png,
                                    f"Content-Type: {content_type}")
                            
                            # Test 3d: Check body size > 200 bytes
                            body_size = len(resp.content)
                            log_test("3", "Body size > 200 bytes", body_size > 200,
                                    f"Size: {body_size} bytes")
                            
                            # Test 3e: Check PNG magic bytes
                            starts_with_png = resp.content[:4] == b'\x89PNG'
                            log_test("3", "Starts with PNG magic bytes", starts_with_png,
                                    f"First 4 bytes: {resp.content[:4]}")
                    except Exception as e:
                        log_test("3", "GET qr-image exception", False, str(e))
                    
                    # Test 3f: GET qr-image as retailer → 403
                    retailer_token = login(RETAILER1_EMAIL, RETAILER1_PASSWORD)
                    if retailer_token:
                        try:
                            resp = requests.get(
                                f"{BASE_URL}/dms/coupons/coupons/{coupon_id}/qr-image?size=6",
                                headers=get_headers(retailer_token),
                                timeout=10
                            )
                            log_test("3", "GET qr-image as retailer → 403", resp.status_code == 403,
                                    f"Status: {resp.status_code}")
                        except Exception as e:
                            log_test("3", "GET qr-image as retailer exception", False, str(e))
            else:
                log_test("3", "No coupons available for testing", False)
        else:
            log_test("3", "Failed to get coupons", False, f"Status: {resp.status_code}")
    except Exception as e:
        log_test("3", "QR image test exception", False, str(e))


def test_scenario_4_qr_payload_endpoint():
    """
    SCENARIO 4: NEW: QR payload endpoint
    """
    print("\n" + "="*80)
    print("SCENARIO 4: NEW: QR payload endpoint")
    print("="*80)
    
    owner_token = login(OWNER_EMAIL, OWNER_PASSWORD)
    if not owner_token:
        log_test("4", "Login as owner", False, "Login failed")
        return
    
    # Get a coupon ID
    try:
        resp = requests.get(
            f"{BASE_URL}/dms/coupons?limit=1",
            headers=get_headers(owner_token),
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            coupons = data.get("data", [])
            
            if len(coupons) > 0:
                coupon_id = coupons[0].get("id")
                
                if coupon_id:
                    # Test 4a: GET /api/dms/coupons/coupons/{cid}/qr-payload as owner
                    try:
                        resp = requests.get(
                            f"{BASE_URL}/dms/coupons/coupons/{coupon_id}/qr-payload",
                            headers=get_headers(owner_token),
                            timeout=10
                        )
                        
                        # Test 4b: Check status 200
                        log_test("4", "GET qr-payload as owner → 200", resp.status_code == 200,
                                f"Status: {resp.status_code}")
                        
                        if resp.status_code == 200:
                            payload_data = resp.json()
                            
                            # Test 4c: Check required fields
                            required_fields = ["visible_serial", "hidden_secure_id", "qr_version",
                                             "qr_payload", "coupon_type", "coupon_value", 
                                             "status", "active"]
                            
                            for field in required_fields:
                                has_field = field in payload_data
                                log_test("4", f"Field '{field}' present", has_field,
                                        f"Value: {payload_data.get(field)}")
                            
                            # Test 4d: Check qr_payload format
                            qr_payload = payload_data.get("qr_payload", "")
                            is_v2_format = qr_payload.startswith("GOOIL2|")
                            is_v1_format = qr_payload.startswith("GOOIL:")
                            is_valid_format = is_v2_format or is_v1_format
                            log_test("4", "qr_payload has valid format (v2 or v1)", is_valid_format,
                                    f"Starts with: {qr_payload[:20] if qr_payload else 'empty'}")
                    except Exception as e:
                        log_test("4", "GET qr-payload exception", False, str(e))
                    
                    # Test 4e: GET qr-payload as retailer → 403
                    retailer_token = login(RETAILER1_EMAIL, RETAILER1_PASSWORD)
                    if retailer_token:
                        try:
                            resp = requests.get(
                                f"{BASE_URL}/dms/coupons/coupons/{coupon_id}/qr-payload",
                                headers=get_headers(retailer_token),
                                timeout=10
                            )
                            log_test("4", "GET qr-payload as retailer → 403", resp.status_code == 403,
                                    f"Status: {resp.status_code}")
                        except Exception as e:
                            log_test("4", "GET qr-payload as retailer exception", False, str(e))
            else:
                log_test("4", "No coupons available for testing", False)
        else:
            log_test("4", "Failed to get coupons", False, f"Status: {resp.status_code}")
    except Exception as e:
        log_test("4", "QR payload test exception", False, str(e))


def test_scenario_5_bulk_activate():
    """
    SCENARIO 5: NEW: Bulk activate by IDs
    """
    print("\n" + "="*80)
    print("SCENARIO 5: NEW: Bulk activate by IDs")
    print("="*80)
    
    owner_token = login(OWNER_EMAIL, OWNER_PASSWORD)
    if not owner_token:
        log_test("5", "Login as owner", False, "Login failed")
        return
    
    # Test 5a: Create a small batch of 5 coupons
    try:
        batch_payload = {
            "coupon_type": "cash",
            "coupon_value": 10,
            "serial_mode": "prefix_sequential",
            "prefix": f"BLK{TEST_PREFIX}",
            "serial_start": 1,
            "serial_pad": 3,
            "count": 5
        }
        
        resp = requests.post(
            f"{BASE_URL}/dms/coupons/batches",
            headers=get_headers(owner_token),
            json=batch_payload,
            timeout=10
        )
        
        log_test("5", "Create batch with 5 coupons", resp.status_code == 200,
                f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            batch_data = resp.json()
            batch_id = batch_data.get("id")
            log_test("5", "Batch ID received", batch_id is not None, f"ID: {batch_id}")
            
            if batch_id:
                # Test 5b: Get the 5 coupon IDs
                try:
                    resp = requests.get(
                        f"{BASE_URL}/dms/coupons?batch_id={batch_id}",
                        headers=get_headers(owner_token),
                        timeout=10
                    )
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        coupons = data.get("data", [])
                        log_test("5", "Got 5 coupons from batch", len(coupons) == 5,
                                f"Count: {len(coupons)}")
                        
                        if len(coupons) >= 3:
                            coupon_ids = [c["id"] for c in coupons[:3]]
                            
                            # Test 5c: Bulk activate 3 coupons
                            try:
                                resp = requests.post(
                                    f"{BASE_URL}/dms/coupons/coupons/bulk-activate",
                                    headers=get_headers(owner_token),
                                    json={"coupon_ids": coupon_ids},
                                    timeout=10
                                )
                                
                                log_test("5", "POST bulk-activate → 200", resp.status_code == 200,
                                        f"Status: {resp.status_code}")
                                
                                if resp.status_code == 200:
                                    result = resp.json()
                                    
                                    # Test 5d: Check response fields
                                    log_test("5", "Response has 'ok' field", result.get("ok") == True)
                                    log_test("5", "requested = 3", result.get("requested") == 3,
                                            f"requested: {result.get('requested')}")
                                    log_test("5", "activated = 3", result.get("activated") == 3,
                                            f"activated: {result.get('activated')}")
                                    log_test("5", "skipped = 0", result.get("skipped") == 0,
                                            f"skipped: {result.get('skipped')}")
                                    
                                    # Test 5e: Verify coupons are now active
                                    resp = requests.get(
                                        f"{BASE_URL}/dms/coupons?batch_id={batch_id}",
                                        headers=get_headers(owner_token),
                                        timeout=10
                                    )
                                    
                                    if resp.status_code == 200:
                                        data = resp.json()
                                        coupons = data.get("data", [])
                                        active_count = sum(1 for c in coupons if c.get("active") == True)
                                        log_test("5", "3 coupons now active", active_count == 3,
                                                f"Active count: {active_count}")
                                        
                                        unused_count = sum(1 for c in coupons if c.get("status") == "unused")
                                        log_test("5", "3 coupons status=unused", unused_count == 3,
                                                f"Unused count: {unused_count}")
                                    
                                    # Test 5f: Bulk activate again (idempotent)
                                    resp = requests.post(
                                        f"{BASE_URL}/dms/coupons/coupons/bulk-activate",
                                        headers=get_headers(owner_token),
                                        json={"coupon_ids": coupon_ids},
                                        timeout=10
                                    )
                                    
                                    if resp.status_code == 200:
                                        result = resp.json()
                                        log_test("5", "Second bulk-activate: activated=0", 
                                                result.get("activated") == 0,
                                                f"activated: {result.get('activated')}")
                                        log_test("5", "Second bulk-activate: skipped=3", 
                                                result.get("skipped") == 3,
                                                f"skipped: {result.get('skipped')}")
                                    
                                    # Test 5g: Bulk deactivate 1 coupon
                                    resp = requests.post(
                                        f"{BASE_URL}/dms/coupons/coupons/bulk-deactivate",
                                        headers=get_headers(owner_token),
                                        json={"coupon_ids": [coupon_ids[0]]},
                                        timeout=10
                                    )
                                    
                                    log_test("5", "POST bulk-deactivate → 200", resp.status_code == 200,
                                            f"Status: {resp.status_code}")
                                    
                                    if resp.status_code == 200:
                                        result = resp.json()
                                        log_test("5", "deactivated = 1", result.get("deactivated") == 1,
                                                f"deactivated: {result.get('deactivated')}")
                            except Exception as e:
                                log_test("5", "Bulk activate exception", False, str(e))
                except Exception as e:
                    log_test("5", "Get coupons from batch exception", False, str(e))
                
                # Test 5h: Bulk activate as distributor → 403
                distributor_token = login(DISTRIBUTOR1_EMAIL, DISTRIBUTOR1_PASSWORD)
                if distributor_token:
                    try:
                        resp = requests.post(
                            f"{BASE_URL}/dms/coupons/coupons/bulk-activate",
                            headers=get_headers(distributor_token),
                            json={"coupon_ids": ["dummy-id"]},
                            timeout=10
                        )
                        log_test("5", "Bulk-activate as distributor → 403", resp.status_code == 403,
                                f"Status: {resp.status_code}")
                    except Exception as e:
                        log_test("5", "Bulk-activate as distributor exception", False, str(e))
    except Exception as e:
        log_test("5", "Bulk activate test exception", False, str(e))


def test_scenario_6_range_activation_smart_normalization():
    """
    SCENARIO 6: NEW: Range activation with SERIAL FORMAT (smart normalization)
    """
    print("\n" + "="*80)
    print("SCENARIO 6: NEW: Range activation with SERIAL FORMAT (smart normalization)")
    print("="*80)
    
    owner_token = login(OWNER_EMAIL, OWNER_PASSWORD)
    if not owner_token:
        log_test("6", "Login as owner", False, "Login failed")
        return
    
    # Create a batch for range testing
    try:
        prefix = f"RNG{TEST_PREFIX}"
        batch_payload = {
            "coupon_type": "cash",
            "coupon_value": 10,
            "serial_mode": "prefix_sequential",
            "prefix": prefix,
            "serial_start": 1,
            "serial_pad": 3,
            "count": 10
        }
        
        resp = requests.post(
            f"{BASE_URL}/dms/coupons/batches",
            headers=get_headers(owner_token),
            json=batch_payload,
            timeout=10
        )
        
        log_test("6", "Create batch for range testing", resp.status_code == 200,
                f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            batch_data = resp.json()
            batch_id = batch_data.get("id")
            
            if batch_id:
                # Test 6a: Range activation with short format "{prefix}2" to "{prefix}4"
                try:
                    resp = requests.post(
                        f"{BASE_URL}/dms/coupons/activate-range",
                        headers=get_headers(owner_token),
                        json={
                            "batch_id": batch_id,
                            "from_serial": f"{prefix}2",
                            "to_serial": f"{prefix}4"
                        },
                        timeout=10
                    )
                    
                    log_test("6", f"POST activate-range ({prefix}2-{prefix}4) → 200", 
                            resp.status_code == 200,
                            f"Status: {resp.status_code}")
                    
                    if resp.status_code == 200:
                        result = resp.json()
                        
                        # Test 6b: Check normalized serials in response
                        from_serial = result.get("from_serial")
                        to_serial = result.get("to_serial")
                        expected_from = f"{prefix}002"
                        expected_to = f"{prefix}004"
                        
                        log_test("6", f"from_serial normalized to {expected_from}", 
                                from_serial == expected_from,
                                f"from_serial: {from_serial}")
                        log_test("6", f"to_serial normalized to {expected_to}", 
                                to_serial == expected_to,
                                f"to_serial: {to_serial}")
                        
                        # Test 6c: Check activated count
                        activated = result.get("activated", 0)
                        log_test("6", "activated > 0", activated > 0,
                                f"activated: {activated}")
                except Exception as e:
                    log_test("6", "Range activation (short format) exception", False, str(e))
                
                # Test 6d: Range activation with just numbers "6" to "8"
                try:
                    resp = requests.post(
                        f"{BASE_URL}/dms/coupons/activate-range",
                        headers=get_headers(owner_token),
                        json={
                            "batch_id": batch_id,
                            "from_serial": "6",
                            "to_serial": "8"
                        },
                        timeout=10
                    )
                    
                    log_test("6", "POST activate-range (6-8) → 200", 
                            resp.status_code == 200,
                            f"Status: {resp.status_code}")
                    
                    if resp.status_code == 200:
                        result = resp.json()
                        from_serial = result.get("from_serial")
                        to_serial = result.get("to_serial")
                        expected_from = f"{prefix}006"
                        expected_to = f"{prefix}008"
                        
                        log_test("6", f"from_serial normalized to {expected_from}", 
                                from_serial == expected_from,
                                f"from_serial: {from_serial}")
                        log_test("6", f"to_serial normalized to {expected_to}", 
                                to_serial == expected_to,
                                f"to_serial: {to_serial}")
                except Exception as e:
                    log_test("6", "Range activation (numbers only) exception", False, str(e))
                
                # Test 6e: Range activation with lowercase "{prefix.lower()}1" to "{prefix.lower()}5"
                try:
                    resp = requests.post(
                        f"{BASE_URL}/dms/coupons/activate-range",
                        headers=get_headers(owner_token),
                        json={
                            "batch_id": batch_id,
                            "from_serial": f"{prefix.lower()}1",
                            "to_serial": f"{prefix.lower()}5"
                        },
                        timeout=10
                    )
                    
                    log_test("6", "POST activate-range (lowercase) → 200", 
                            resp.status_code == 200,
                            f"Status: {resp.status_code}")
                    
                    if resp.status_code == 200:
                        result = resp.json()
                        from_serial = result.get("from_serial")
                        to_serial = result.get("to_serial")
                        expected_from = f"{prefix}001"
                        expected_to = f"{prefix}005"
                        
                        log_test("6", f"from_serial normalized to {expected_from}", 
                                from_serial == expected_from,
                                f"from_serial: {from_serial}")
                        log_test("6", f"to_serial normalized to {expected_to}", 
                                to_serial == expected_to,
                                f"to_serial: {to_serial}")
                except Exception as e:
                    log_test("6", "Range activation (lowercase) exception", False, str(e))
    except Exception as e:
        log_test("6", "Range activation test exception", False, str(e))


def test_scenario_7_regression():
    """
    SCENARIO 7: Regression on existing endpoints
    """
    print("\n" + "="*80)
    print("SCENARIO 7: Regression on existing endpoints")
    print("="*80)
    
    owner_token = login(OWNER_EMAIL, OWNER_PASSWORD)
    if not owner_token:
        log_test("7", "Login as owner", False, "Login failed")
        return
    
    # Test 7a: POST /api/dms/coupons/batches with random_secure
    try:
        batch_payload = {
            "coupon_type": "reward",
            "coupon_value": 50,
            "serial_mode": "random_secure",
            "count": 2
        }
        
        resp = requests.post(
            f"{BASE_URL}/dms/coupons/batches",
            headers=get_headers(owner_token),
            json=batch_payload,
            timeout=10
        )
        
        log_test("7", "POST batches (random_secure) → 200", resp.status_code == 200,
                f"Status: {resp.status_code}")
    except Exception as e:
        log_test("7", "POST batches exception", False, str(e))
    
    # Test 7b: GET /api/dms/coupons/reports/fraud-dashboard
    try:
        resp = requests.get(
            f"{BASE_URL}/dms/coupons/reports/fraud-dashboard",
            headers=get_headers(owner_token),
            timeout=10
        )
        
        log_test("7", "GET fraud-dashboard → 200", resp.status_code == 200,
                f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            has_kpis = "kpis" in data
            has_by_reason = "by_reason" in data
            log_test("7", "Fraud dashboard has kpis", has_kpis)
            log_test("7", "Fraud dashboard has by_reason", has_by_reason)
    except Exception as e:
        log_test("7", "GET fraud-dashboard exception", False, str(e))
    
    # Test 7c: GET /api/dms/coupons/batches
    try:
        resp = requests.get(
            f"{BASE_URL}/dms/coupons/batches",
            headers=get_headers(owner_token),
            timeout=10
        )
        
        log_test("7", "GET batches → 200", resp.status_code == 200,
                f"Status: {resp.status_code}")
    except Exception as e:
        log_test("7", "GET batches exception", False, str(e))


def print_summary():
    """Print test summary"""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    # Group by scenario
    scenarios = {}
    for result in test_results:
        scenario = result["scenario"]
        if scenario not in scenarios:
            scenarios[scenario] = {"passed": 0, "failed": 0, "tests": []}
        
        if result["passed"]:
            scenarios[scenario]["passed"] += 1
        else:
            scenarios[scenario]["failed"] += 1
        
        scenarios[scenario]["tests"].append(result)
    
    # Print by scenario
    for scenario_num in sorted(scenarios.keys()):
        scenario_data = scenarios[scenario_num]
        total = scenario_data["passed"] + scenario_data["failed"]
        pass_rate = (scenario_data["passed"] / total * 100) if total > 0 else 0
        
        status = "✅" if scenario_data["failed"] == 0 else "❌"
        print(f"\n{status} SCENARIO {scenario_num}: {scenario_data['passed']}/{total} passed ({pass_rate:.1f}%)")
        
        # Show failed tests
        if scenario_data["failed"] > 0:
            print("  Failed tests:")
            for test in scenario_data["tests"]:
                if not test["passed"]:
                    print(f"    ❌ {test['test']}")
                    if test["details"]:
                        print(f"       {test['details']}")
    
    # Overall summary
    print("\n" + "="*80)
    pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    print(f"OVERALL: {passed_tests}/{total_tests} tests passed ({pass_rate:.1f}%)")
    print("="*80)
    
    # Return exit code
    return 0 if passed_tests == total_tests else 1


def main():
    """Main test runner"""
    print("="*80)
    print("Coupon Engine v2 Follow-up Testing")
    print("="*80)
    print(f"Backend URL: {BASE_URL}")
    print(f"Test credentials: {OWNER_EMAIL} / {OWNER_PASSWORD}")
    print("="*80)
    
    # Run all scenarios
    test_scenario_1_hidden_secure_id_visible()
    test_scenario_2_sensitive_crypto_hidden()
    test_scenario_3_qr_image_endpoint()
    test_scenario_4_qr_payload_endpoint()
    test_scenario_5_bulk_activate()
    test_scenario_6_range_activation_smart_normalization()
    test_scenario_7_regression()
    
    # Print summary and exit
    exit_code = print_summary()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
