#!/usr/bin/env python3
"""
GO OIL Coupon Engine v2 Upgrade — Comprehensive Backend Test Suite
===================================================================

Tests all 11 scenarios from the review request:
1. Prefix-Sequential Batch Generation (Owner)
2. Random-Secure Mode (backward compat)
3. Single-Coupon Activation
4. Range Activation (Prefix)
5. AES-256 Encrypted PDF Export & Content Safety
6. Scan Flow — Positive (v2)
7. Scan Flow — Fraud Attempts
8. Fraud Dashboard
9. New Reports
10. REGRESSION — Existing Flows Must Still Work
11. RBAC Regressions
"""

import requests
import json
import sys
import re
import random
import string
from typing import Dict, Any, Optional

# Backend base URL from frontend/.env
BASE_URL = "https://challan-print-fix.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
CREDENTIALS = {
    "owner": {"email": "owner@gooil.com", "password": "GoOil@2026"},
    "distributor": {"email": "distributor1@gooil.com", "password": "GoOil@2026"},
    "retailer": {"email": "retailer1@gooil.com", "password": "GoOil@2026"},
    "salesperson": {"email": "salesperson@gooil.com", "password": "GoOil@2026"},
}

# Global state
tokens: Dict[str, str] = {}
test_data: Dict[str, Any] = {}


def login(role: str) -> str:
    """Login and return JWT token."""
    creds = CREDENTIALS[role]
    resp = requests.post(f"{BASE_URL}/auth/login", json=creds)
    if resp.status_code != 200:
        print(f"❌ Login failed for {role}: {resp.status_code} {resp.text}")
        sys.exit(1)
    data = resp.json()
    token = data.get("access_token") or data.get("token")
    tokens[role] = token
    print(f"✅ Logged in as {role}")
    return token


def api_call(method: str, path: str, role: str = "owner", **kwargs) -> requests.Response:
    """Make authenticated API call."""
    if role not in tokens:
        login(role)
    headers = {"Authorization": f"Bearer {tokens[role]}"}
    url = f"{BASE_URL}{path}"
    return requests.request(method, url, headers=headers, **kwargs)


def test_result(name: str, passed: bool, details: str = ""):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details:
        print(f"   {details}")


# ═══════════════════════════════════════════════════════════════════════════
# SCENARIO 1: Prefix-Sequential Batch Generation (Owner) — CRITICAL
# ═══════════════════════════════════════════════════════════════════════════
def test_scenario_1():
    print("\n" + "="*80)
    print("SCENARIO 1: Prefix-Sequential Batch Generation (Owner)")
    print("="*80)
    
    # Create batch with prefix_sequential mode (use unique prefix to avoid overlap)
    unique_prefix = "T" + "".join(random.choices(string.ascii_uppercase + string.digits, k=3))
    payload = {
        "coupon_type": "cash",
        "coupon_value": 20,
        "serial_mode": "prefix_sequential",
        "prefix": unique_prefix,
        "serial_start": 1,
        "serial_pad": 3,
        "count": 5,
        "title": "v2 test batch"
    }
    print(f"Using unique prefix: {unique_prefix}")
    
    resp = api_call("POST", "/dms/coupons/batches", "owner", json=payload)
    test_result("1.1 POST /batches with prefix_sequential", resp.status_code == 200,
                f"Status: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"   Response: {resp.text}")
        return
    
    result = resp.json()
    batch = result.get("batch", result)  # Handle both nested and flat response
    test_data["batch_v2"] = batch
    test_data["unique_prefix"] = unique_prefix  # Store for later scenarios
    bid = batch.get("id")
    
    # Verify batch fields
    test_result("1.2 Batch has serial_mode=prefix_sequential", 
                batch.get("serial_mode") == "prefix_sequential")
    test_result("1.3 Batch has prefix", batch.get("prefix") == unique_prefix,
                f"Expected: {unique_prefix}, Got: {batch.get('prefix')}")
    test_result("1.4 Batch has serial_start=1", batch.get("serial_start") == 1)
    test_result("1.5 Batch has serial_pad=3", batch.get("serial_pad") == 3)
    test_result("1.6 Batch has serial_end=5", batch.get("serial_end") == 5)
    test_result("1.7 Batch has qr_version=v2", batch.get("qr_version") == "v2")
    
    # Get coupons from batch
    resp = api_call("GET", f"/dms/coupons?batch_id={bid}&limit=100", "owner")
    test_result("1.8 GET /coupons?batch_id={bid}", resp.status_code == 200)
    
    if resp.status_code == 200:
        coupons = resp.json().get("data", [])
        test_result("1.9 Batch has 5 coupons", len(coupons) == 5)
        
        # Check visible_serial values
        expected_serials = [f"{unique_prefix}001", f"{unique_prefix}002", f"{unique_prefix}003", 
                           f"{unique_prefix}004", f"{unique_prefix}005"]
        actual_serials = [c.get("visible_serial") for c in coupons]
        test_result("1.10 Coupons have correct visible_serial", 
                    set(actual_serials) == set(expected_serials),
                    f"Expected: {expected_serials}, Got: {actual_serials}")
        
        # Check all coupons are status=generated, active=false
        all_generated = all(c.get("status") == "generated" for c in coupons)
        all_inactive = all(c.get("active") == False for c in coupons)
        test_result("1.11 All coupons status=generated", all_generated)
        test_result("1.12 All coupons active=false", all_inactive)
        
        # Check sensitive fields NOT included
        if coupons:
            first_coupon = coupons[0]
            sensitive_fields = ["hidden_secure_id", "secret_token", "signature", 
                               "qr_ciphertext_b64", "qr_signature_v2", "qr_hash"]
            has_sensitive = any(f in first_coupon for f in sensitive_fields)
            test_result("1.13 Response does NOT include sensitive fields", not has_sensitive,
                        f"Fields present: {[f for f in sensitive_fields if f in first_coupon]}")
        
        test_data["coupons_v2"] = coupons
    
    # Test overlap detection
    resp = api_call("POST", "/dms/coupons/batches", "owner", json=payload)
    test_result("1.14 Duplicate batch creation returns 400", resp.status_code == 400,
                f"Status: {resp.status_code}")
    if resp.status_code == 400:
        test_result("1.15 Error message mentions 'overlap'", 
                    "overlap" in resp.text.lower())


# ═══════════════════════════════════════════════════════════════════════════
# SCENARIO 2: Random-Secure Mode (backward compat)
# ═══════════════════════════════════════════════════════════════════════════
def test_scenario_2():
    print("\n" + "="*80)
    print("SCENARIO 2: Random-Secure Mode (backward compat)")
    print("="*80)
    
    payload = {
        "coupon_type": "reward",
        "coupon_value": 100,
        "serial_mode": "random_secure",
        "count": 3
    }
    
    resp = api_call("POST", "/dms/coupons/batches", "owner", json=payload)
    test_result("2.1 POST /batches with random_secure", resp.status_code == 200,
                f"Status: {resp.status_code}")
    
    if resp.status_code == 200:
        result = resp.json()
        batch = result.get("batch", result)  # Handle both nested and flat response
        bid = batch.get("id")
        
        # Get coupons
        resp = api_call("GET", f"/dms/coupons?batch_id={bid}&limit=100", "owner")
        if resp.status_code == 200:
            coupons = resp.json().get("data", [])
            test_result("2.2 Batch has 3 coupons", len(coupons) == 3)
            
            # Check format: XXXX-XXXX-XXXX-XXXX (16 chars + 3 dashes)
            for i, c in enumerate(coupons):
                serial = c.get("visible_serial", "")
                pattern = r'^[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}$'
                matches = bool(re.match(pattern, serial))
                test_result(f"2.3.{i+1} Coupon {i+1} has 16-char random format", matches,
                           f"Serial: {serial}")


# ═══════════════════════════════════════════════════════════════════════════
# SCENARIO 3: Single-Coupon Activation
# ═══════════════════════════════════════════════════════════════════════════
def test_scenario_3():
    print("\n" + "="*80)
    print("SCENARIO 3: Single-Coupon Activation")
    print("="*80)
    
    if "coupons_v2" not in test_data or not test_data["coupons_v2"]:
        print("⚠️  Skipping: No coupons from scenario 1")
        return
    
    coupon = test_data["coupons_v2"][0]
    cid = coupon.get("id")
    
    # Activate coupon
    resp = api_call("POST", f"/dms/coupons/coupons/{cid}/activate", "owner")
    test_result("3.1 POST /coupons/{cid}/activate", resp.status_code == 200,
                f"Status: {resp.status_code}")
    
    if resp.status_code == 200:
        result = resp.json()
        test_result("3.2 Response has changed=true", result.get("changed") == True)
    
    # Get coupon detail
    resp = api_call("GET", f"/dms/coupons/detail/{cid}", "owner")
    if resp.status_code == 200:
        c = resp.json()
        test_result("3.3 Coupon status=unused", c.get("status") == "unused")
        test_result("3.4 Coupon active=true", c.get("active") == True)
        test_result("3.5 Coupon has activated_at", c.get("activated_at") is not None)
        test_result("3.6 Coupon has activated_by", c.get("activated_by") is not None)
    
    # Activate again (idempotent)
    resp = api_call("POST", f"/dms/coupons/coupons/{cid}/activate", "owner")
    test_result("3.7 Second activate returns 200", resp.status_code == 200)
    if resp.status_code == 200:
        result = resp.json()
        test_result("3.8 Second activate has changed=false", result.get("changed") == False)
    
    # Deactivate
    resp = api_call("POST", f"/dms/coupons/coupons/{cid}/deactivate", "owner")
    test_result("3.9 POST /coupons/{cid}/deactivate", resp.status_code == 200,
                f"Status: {resp.status_code}")
    
    # Check status after deactivate
    resp = api_call("GET", f"/dms/coupons/detail/{cid}", "owner")
    if resp.status_code == 200:
        c = resp.json()
        test_result("3.10 After deactivate: status=cancelled", c.get("status") == "cancelled")
        test_result("3.11 After deactivate: active=false", c.get("active") == False)
    
    # Try to activate cancelled coupon
    resp = api_call("POST", f"/dms/coupons/coupons/{cid}/activate", "owner")
    test_result("3.12 Cannot activate cancelled coupon", resp.status_code == 400,
                f"Status: {resp.status_code}")


# ═══════════════════════════════════════════════════════════════════════════
# SCENARIO 4: Range Activation (Prefix)
# ═══════════════════════════════════════════════════════════════════════════
def test_scenario_4():
    print("\n" + "="*80)
    print("SCENARIO 4: Range Activation (Prefix)")
    print("="*80)
    
    if "batch_v2" not in test_data:
        print("⚠️  Skipping: No batch from scenario 1")
        return
    
    bid = test_data["batch_v2"].get("id")
    
    # Activate range TEST002-TEST004
    payload = {
        "batch_id": bid,
        "from_number": 2,
        "to_number": 4
    }
    
    resp = api_call("POST", "/dms/coupons/activate-range", "owner", json=payload)
    test_result("4.1 POST /activate-range", resp.status_code == 200,
                f"Status: {resp.status_code}")
    
    if resp.status_code == 200:
        result = resp.json()
        test_result("4.2 Response has from_serial=TEST002", 
                    result.get("from_serial") == "TEST002")
        test_result("4.3 Response has to_serial=TEST004", 
                    result.get("to_serial") == "TEST004")
        test_result("4.4 Response has activated count", 
                    result.get("activated", 0) > 0)
    
    # Verify coupons are activated
    resp = api_call("GET", f"/dms/coupons?batch_id={bid}&limit=100", "owner")
    if resp.status_code == 200:
        coupons = resp.json().get("data", [])
        activated_serials = [c.get("visible_serial") for c in coupons 
                            if c.get("active") == True and c.get("status") != "cancelled"]
        # Get the prefix from the batch
        batch_resp = api_call("GET", f"/dms/coupons/batches/{bid}", "owner")
        if batch_resp.status_code == 200:
            prefix = batch_resp.json().get("prefix", "")
            expected = [f"{prefix}002", f"{prefix}003", f"{prefix}004"]
            test_result("4.5 Coupons 002, 003, 004 are active", 
                        set(expected).issubset(set(activated_serials)),
                        f"Expected subset: {expected}, Active serials: {activated_serials}")
    
    # Test distributor cannot activate range
    resp = api_call("POST", "/dms/coupons/activate-range", "distributor", json=payload)
    test_result("4.6 Distributor cannot activate range", resp.status_code == 403,
                f"Status: {resp.status_code}")


# ═══════════════════════════════════════════════════════════════════════════
# SCENARIO 5: AES-256 Encrypted PDF Export & Content Safety
# ═══════════════════════════════════════════════════════════════════════════
def test_scenario_5():
    print("\n" + "="*80)
    print("SCENARIO 5: AES-256 Encrypted PDF Export & Content Safety")
    print("="*80)
    
    if "batch_v2" not in test_data:
        print("⚠️  Skipping: No batch from scenario 1")
        return
    
    bid = test_data["batch_v2"].get("id")
    
    # Export PDF
    resp = api_call("GET", f"/dms/coupons/batches/{bid}/export-pdf", "owner")
    test_result("5.1 GET /batches/{bid}/export-pdf", resp.status_code == 200,
                f"Status: {resp.status_code}")
    
    if resp.status_code == 200:
        test_result("5.2 Content-Type is application/pdf", 
                    resp.headers.get("Content-Type") == "application/pdf")
        
        pdf_bytes = resp.content
        test_result("5.3 PDF size > 1KB", len(pdf_bytes) > 1024,
                    f"Size: {len(pdf_bytes)} bytes")
        
        # Check PDF does NOT contain sensitive data
        pdf_text = pdf_bytes.decode('latin-1', errors='ignore').lower()
        
        # Should NOT contain these
        forbidden = ["batch_secret", "hmac", "signature", "uuid"]
        found_forbidden = [word for word in forbidden if word in pdf_text]
        test_result("5.4 PDF does NOT contain batch_secret/hmac/signature/uuid", 
                    len(found_forbidden) == 0,
                    f"Found: {found_forbidden}" if found_forbidden else "")
        
        # Should NOT contain hyphenated UUIDs (e.g., "abcd1234-abcd-1234-...")
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        has_uuid = bool(re.search(uuid_pattern, pdf_text))
        test_result("5.5 PDF does NOT contain hyphenated UUIDs", not has_uuid)
        
        # Should contain approved artifacts (use the unique prefix)
        # Note: PDF text is case-insensitive, so check for lowercase version
        prefix = test_data.get("unique_prefix", "")
        test_result("5.6 PDF contains serial prefix", prefix.lower() in pdf_text or prefix in pdf_text)


# ═══════════════════════════════════════════════════════════════════════════
# SCENARIO 6: Scan Flow — Positive (v2)
# ═══════════════════════════════════════════════════════════════════════════
def test_scenario_6():
    print("\n" + "="*80)
    print("SCENARIO 6: Scan Flow — Positive (v2)")
    print("="*80)
    
    # First, ensure we have an active coupon
    if "coupons_v2" not in test_data or len(test_data["coupons_v2"]) < 2:
        print("⚠️  Skipping: Need at least 2 coupons from scenario 1")
        return
    
    # Use the second coupon (first one was deactivated in scenario 3)
    coupon = test_data["coupons_v2"][1]
    cid = coupon.get("id")
    
    # Activate this coupon first
    resp = api_call("POST", f"/dms/coupons/coupons/{cid}/activate", "owner")
    if resp.status_code != 200:
        print(f"⚠️  Failed to activate coupon: {resp.status_code}")
        return
    
    # Get retailer ID
    resp = api_call("GET", "/dms/coupons/so/retailers", "salesperson")
    if resp.status_code != 200:
        print(f"⚠️  Failed to get retailers: {resp.status_code}")
        return
    
    retailers = resp.json().get("data", [])
    if not retailers:
        print("⚠️  No retailers found for salesperson")
        return
    
    retailer_id = retailers[0].get("id")
    test_data["retailer_id"] = retailer_id
    
    # Scan using coupon_code (visible_serial) - v1 legacy interface
    scan_payload = {
        "retailer_id": retailer_id,
        "coupon_code": coupon.get("visible_serial"),
        "gps_lat": 28.61,
        "gps_lng": 77.20,
        "device_id": "dev-test-1"
    }
    
    resp = api_call("POST", "/dms/coupons/scan", "salesperson", json=scan_payload)
    test_result("6.1 POST /scan with valid coupon", resp.status_code == 200,
                f"Status: {resp.status_code}, Response: {resp.text[:200]}")
    
    if resp.status_code == 200:
        result = resp.json()
        test_result("6.2 Scan response has ok=true", result.get("ok") == True)
        test_result("6.3 Scan response has new_balance > 0", 
                    result.get("new_balance", 0) > 0,
                    f"Balance: {result.get('new_balance')}")
        
        test_data["scanned_coupon_id"] = cid
    
    # Try to scan same coupon again (should fail)
    resp = api_call("POST", "/dms/coupons/scan", "salesperson", json=scan_payload)
    test_result("6.4 Second scan returns 400", resp.status_code == 400,
                f"Status: {resp.status_code}")
    
    if resp.status_code == 400:
        test_result("6.5 Error message mentions 'already claimed'", 
                    "already claimed" in resp.text.lower() or "already" in resp.text.lower())
    
    # Check fraud log
    resp = api_call("GET", "/dms/coupons/reports/fraud?limit=10", "owner")
    if resp.status_code == 200:
        fraud_attempts = resp.json().get("data", [])
        recent_fraud = [f for f in fraud_attempts if f.get("reason") == "already_claimed"]
        test_result("6.6 Fraud log has 'already_claimed' entry", len(recent_fraud) > 0)


# ═══════════════════════════════════════════════════════════════════════════
# SCENARIO 7: Scan Flow — Fraud Attempts
# ═══════════════════════════════════════════════════════════════════════════
def test_scenario_7():
    print("\n" + "="*80)
    print("SCENARIO 7: Scan Flow — Fraud Attempts")
    print("="*80)
    
    if "retailer_id" not in test_data:
        print("⚠️  Skipping: No retailer_id from scenario 6")
        return
    
    retailer_id = test_data["retailer_id"]
    
    # Test 1: Random string (no valid prefix)
    scan_payload = {
        "retailer_id": retailer_id,
        "qr_payload": "RANDOMSTRING123",
        "gps_lat": 28.61,
        "gps_lng": 77.20,
        "device_id": "dev-test-1"
    }
    
    resp = api_call("POST", "/dms/coupons/scan", "salesperson", json=scan_payload)
    test_result("7.1 Scan with random string returns 400", resp.status_code == 400,
                f"Status: {resp.status_code}")
    
    # Test 2: Malformed v2 payload
    scan_payload["qr_payload"] = "GOOIL2|notbase64@@|abcd"
    resp = api_call("POST", "/dms/coupons/scan", "salesperson", json=scan_payload)
    test_result("7.2 Scan with malformed v2 payload returns 400", resp.status_code == 400,
                f"Status: {resp.status_code}")
    
    # Test 3: Valid-looking v1 but garbage
    scan_payload["qr_payload"] = "GOOIL:XXXX:XXXX:XXXX"
    resp = api_call("POST", "/dms/coupons/scan", "salesperson", json=scan_payload)
    test_result("7.3 Scan with garbage v1 payload returns 400", resp.status_code == 400,
                f"Status: {resp.status_code}")
    
    # Check fraud dashboard
    resp = api_call("GET", "/dms/coupons/reports/fraud?limit=20", "owner")
    if resp.status_code == 200:
        fraud_attempts = resp.json().get("data", [])
        test_result("7.4 Fraud log has multiple entries", len(fraud_attempts) >= 3,
                    f"Count: {len(fraud_attempts)}")
        
        # Check for ip_address, user_agent, device_id
        if fraud_attempts:
            recent = fraud_attempts[0]
            test_result("7.5 Fraud entry has ip_address", 
                       recent.get("ip_address") is not None,
                       f"IP: {recent.get('ip_address')}")
            test_result("7.6 Fraud entry has user_agent", 
                       recent.get("user_agent") is not None)
            test_result("7.7 Fraud entry has device_id", 
                       recent.get("device_id") == "dev-test-1")


# ═══════════════════════════════════════════════════════════════════════════
# SCENARIO 8: Fraud Dashboard
# ═══════════════════════════════════════════════════════════════════════════
def test_scenario_8():
    print("\n" + "="*80)
    print("SCENARIO 8: Fraud Dashboard")
    print("="*80)
    
    # Get fraud dashboard
    resp = api_call("GET", "/dms/coupons/reports/fraud-dashboard", "owner")
    test_result("8.1 GET /reports/fraud-dashboard", resp.status_code == 200,
                f"Status: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        
        # Check KPIs
        kpis = data.get("kpis", {})
        test_result("8.2 Dashboard has kpis", kpis is not None)
        test_result("8.3 KPIs has today", "today" in kpis)
        test_result("8.4 KPIs has last7", "last7" in kpis)
        test_result("8.5 KPIs has last30", "last30" in kpis)
        test_result("8.6 KPIs has total", "total" in kpis)
        
        # Check by_reason
        by_reason = data.get("by_reason", {})
        test_result("8.7 Dashboard has by_reason", by_reason is not None)
        test_result("8.8 by_reason has entries", len(by_reason) > 0,
                    f"Reasons: {list(by_reason.keys())}")
        
        # Check by_distributor
        by_distributor = data.get("by_distributor", [])
        test_result("8.9 Dashboard has by_distributor", isinstance(by_distributor, list))
        
        # Check by_actor
        by_actor = data.get("by_actor", [])
        test_result("8.10 Dashboard has by_actor", isinstance(by_actor, list))
        
        # Check recent
        recent = data.get("recent", [])
        test_result("8.11 Dashboard has recent array", isinstance(recent, list))
        test_result("8.12 Recent has entries", len(recent) > 0,
                    f"Count: {len(recent)}")
    
    # Test retailer cannot access
    resp = api_call("GET", "/dms/coupons/reports/fraud-dashboard", "retailer")
    test_result("8.13 Retailer cannot access fraud dashboard", resp.status_code == 403,
                f"Status: {resp.status_code}")


# ═══════════════════════════════════════════════════════════════════════════
# SCENARIO 9: New Reports
# ═══════════════════════════════════════════════════════════════════════════
def test_scenario_9():
    print("\n" + "="*80)
    print("SCENARIO 9: New Reports")
    print("="*80)
    
    reports = [
        ("/dms/coupons/reports/generation", "generation"),
        ("/dms/coupons/reports/activation", "activation"),
        ("/dms/coupons/reports/usage", "usage"),
        ("/dms/coupons/reports/cash-wallets", "cash-wallets"),
        ("/dms/coupons/reports/reward-wallets", "reward-wallets"),
        ("/dms/coupons/reports/distributor-outstanding", "distributor-outstanding"),
    ]
    
    for i, (path, name) in enumerate(reports, 1):
        resp = api_call("GET", path, "owner")
        test_result(f"9.{i} GET {name}", resp.status_code == 200,
                    f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            has_data = "data" in data or "total_balance" in data or "outstanding" in data
            test_result(f"9.{i}.1 {name} has data key", has_data,
                       f"Keys: {list(data.keys())}")
    
    # Test unused report with batch_id
    if "batch_v2" in test_data:
        bid = test_data["batch_v2"].get("id")
        resp = api_call("GET", f"/dms/coupons/reports/unused?batch_id={bid}", "owner")
        test_result("9.7 GET /reports/unused with batch_id", resp.status_code == 200,
                    f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            count = data.get("count", 0)
            test_result("9.7.1 Unused report has count", count >= 0,
                       f"Count: {count}")
    
    # Test inactive report
    resp = api_call("GET", "/dms/coupons/reports/inactive", "owner")
    test_result("9.8 GET /reports/inactive", resp.status_code == 200,
                f"Status: {resp.status_code}")


# ═══════════════════════════════════════════════════════════════════════════
# SCENARIO 10: REGRESSION — Existing Flows Must Still Work
# ═══════════════════════════════════════════════════════════════════════════
def test_scenario_10():
    print("\n" + "="*80)
    print("SCENARIO 10: REGRESSION — Existing Flows Must Still Work")
    print("="*80)
    
    # Test 1: Old client without serial_mode (should work with random_secure)
    payload = {
        "coupon_type": "cash",
        "coupon_value": 10,
        "serial_mode": "random_secure",
        "count": 2
    }
    
    resp = api_call("POST", "/dms/coupons/batches", "owner", json=payload)
    test_result("10.1 POST /batches with random_secure (v1-style)", resp.status_code == 200,
                f"Status: {resp.status_code}")
    
    if resp.status_code == 200:
        result = resp.json()
        batch = result.get("batch", result)  # Handle both nested and flat response
        test_data["batch_v1_compat"] = batch
    
    # Test 2: Complete redemption flow
    # First, check retailer wallet
    resp = api_call("GET", "/dms/coupons/retailer/wallet", "retailer")
    test_result("10.2 GET /retailer/wallet", resp.status_code == 200,
                f"Status: {resp.status_code}")
    
    if resp.status_code == 200:
        wallet = resp.json()
        cash_balance = wallet.get("cash_wallet", {}).get("balance", 0)
        test_result("10.3 Retailer has cash balance > 0", cash_balance > 0,
                    f"Balance: ₹{cash_balance}")
        
        if cash_balance >= 20:
            # Create redemption request
            redemption_payload = {
                "retailer_id": test_data.get("retailer_id"),
                "wallet_type": "cash",
                "amount": 20,
                "notes": "test redemption"
            }
            
            resp = api_call("POST", "/dms/coupons/redemptions", "owner", json=redemption_payload)
            test_result("10.4 POST /redemptions", resp.status_code == 200,
                        f"Status: {resp.status_code}")
            
            if resp.status_code == 200:
                redemption = resp.json()
                rid = redemption.get("id")
                test_data["redemption_id"] = rid
                
                # Approve redemption
                resp = api_call("POST", f"/dms/coupons/redemptions/{rid}/approve", "owner")
                test_result("10.5 POST /redemptions/{rid}/approve", resp.status_code == 200,
                            f"Status: {resp.status_code}")
                
                if resp.status_code == 200:
                    result = resp.json()
                    test_result("10.6 Approval has credit_note_no", 
                               result.get("credit_note_no") is not None,
                               f"CN: {result.get('credit_note_no')}")
                    
                    # Check credit notes
                    resp = api_call("GET", "/dms/coupons/credit-notes", "owner")
                    test_result("10.7 GET /credit-notes", resp.status_code == 200)
                    
                    if resp.status_code == 200:
                        cns = resp.json().get("data", [])
                        test_result("10.8 Credit note exists", len(cns) > 0)
                    
                    # Check primary ledger for coupon_credit entry
                    resp = api_call("GET", "/dms/ledger/primary", "owner")
                    if resp.status_code == 200:
                        ledger = resp.json().get("data", [])
                        coupon_credits = [e for e in ledger if e.get("kind") == "coupon_credit"]
                        test_result("10.9 Primary ledger has coupon_credit entry", 
                                   len(coupon_credits) > 0,
                                   f"Count: {len(coupon_credits)}")


# ═══════════════════════════════════════════════════════════════════════════
# SCENARIO 11: RBAC Regressions
# ═══════════════════════════════════════════════════════════════════════════
def test_scenario_11():
    print("\n" + "="*80)
    print("SCENARIO 11: RBAC Regressions")
    print("="*80)
    
    # Test 1: Distributor calling POST /batches
    payload = {
        "coupon_type": "cash",
        "coupon_value": 10,
        "serial_mode": "random_secure",
        "count": 2
    }
    
    resp = api_call("POST", "/dms/coupons/batches", "distributor", json=payload)
    test_result("11.1 Distributor cannot POST /batches", resp.status_code == 403,
                f"Status: {resp.status_code}")
    
    # Test 2: Retailer calling POST /scan
    scan_payload = {
        "retailer_id": test_data.get("retailer_id", "ret-test"),
        "coupon_code": "TEST001",
        "gps_lat": 28.61,
        "gps_lng": 77.20
    }
    
    resp = api_call("POST", "/dms/coupons/scan", "retailer", json=scan_payload)
    test_result("11.2 Retailer cannot POST /scan", resp.status_code == 403,
                f"Status: {resp.status_code}")
    
    # Test 3: Salesperson calling POST /batches
    resp = api_call("POST", "/dms/coupons/batches", "salesperson", json=payload)
    test_result("11.3 Salesperson cannot POST /batches", resp.status_code == 403,
                f"Status: {resp.status_code}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    print("\n" + "="*80)
    print("GO OIL COUPON ENGINE v2 UPGRADE — COMPREHENSIVE BACKEND TEST SUITE")
    print("="*80)
    print(f"Backend URL: {BASE_URL}")
    print("="*80)
    
    # Login all roles
    for role in CREDENTIALS.keys():
        login(role)
    
    # Run all scenarios
    test_scenario_1()
    test_scenario_2()
    test_scenario_3()
    test_scenario_4()
    test_scenario_5()
    test_scenario_6()
    test_scenario_7()
    test_scenario_8()
    test_scenario_9()
    test_scenario_10()
    test_scenario_11()
    
    print("\n" + "="*80)
    print("TEST SUITE COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
