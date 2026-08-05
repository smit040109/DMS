#!/usr/bin/env python3
"""
Backend Test Suite for Coupon Activation Live Preview + PDF Export
===================================================================

Tests the NEW backend endpoint for coupon activation Live Preview + 
the redesigned coupon PDF export. Does NOT re-test any other coupon endpoints.

Test Scenarios:
1. Live Preview happy path (all inactive)
2. Activate a sub-range then re-preview
3. Number-mode input
4. Auto-swap when from > to
5. Invalid from_serial (out of batch range)
6. Invalid batch_id
7. RBAC — distributor cannot preview
8. /activate-range still requires existence (regression)
9. PDF export smoke test with security checks
"""

import os
import sys
import requests
import json
from typing import Dict, Any, Optional

# Backend URL from environment
BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")
API_BASE = f"{BACKEND_URL}/api"

# Test credentials
OWNER_EMAIL = "owner@gooil.com"
OWNER_PASSWORD = "GoOil@2026"
DISTRIBUTOR_EMAIL = "distributor1@gooil.com"
DISTRIBUTOR_PASSWORD = "GoOil@2026"

# Global state
owner_token: Optional[str] = None
distributor_token: Optional[str] = None
test_batch_id: Optional[str] = None
test_batch_label: Optional[str] = None

# Test results
test_results = []


def log_test(test_num: int, test_name: str, passed: bool, details: str = ""):
    """Log test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    result = {
        "test": f"TEST {test_num}",
        "name": test_name,
        "passed": passed,
        "details": details
    }
    test_results.append(result)
    print(f"\n{status} — TEST {test_num}: {test_name}")
    if details:
        print(f"  Details: {details}")


def login(email: str, password: str) -> Optional[str]:
    """Login and return JWT token."""
    try:
        resp = requests.post(
            f"{API_BASE}/auth/login",
            json={"email": email, "password": password},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("token")
            print(f"✅ Login successful: {email} (role: {data.get('user', {}).get('role')})")
            return token
        else:
            print(f"❌ Login failed for {email}: HTTP {resp.status_code}")
            print(f"   Response: {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Login exception for {email}: {e}")
        return None


def create_test_batch(token: str) -> tuple[Optional[str], Optional[str]]:
    """Create a fresh coupon batch for testing."""
    try:
        payload = {
            "title": "QA Test",
            "coupon_type": "cash",
            "coupon_value": 20,
            "count": 100,
            "serial_mode": "prefix_sequential",
            "prefix": "QAT",
            "serial_start": 1,
            "serial_pad": 3
        }
        resp = requests.post(
            f"{API_BASE}/dms/coupons/batches",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            batch = data.get("batch", {})
            batch_id = batch.get("id")
            batch_label = batch.get("batch_label")
            print(f"✅ Test batch created: {batch_label} (ID: {batch_id})")
            return batch_id, batch_label
        else:
            print(f"❌ Batch creation failed: HTTP {resp.status_code}")
            print(f"   Response: {resp.text[:500]}")
            return None, None
    except Exception as e:
        print(f"❌ Batch creation exception: {e}")
        return None, None


def test_1_preview_happy_path(token: str, batch_id: str):
    """TEST 1 — Live Preview happy path (all inactive)"""
    try:
        payload = {
            "batch_id": batch_id,
            "from_serial": "QAT001",
            "to_serial": "QAT100"
        }
        resp = requests.post(
            f"{API_BASE}/dms/coupons/activate-range/preview",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if resp.status_code != 200:
            log_test(1, "Live Preview happy path (all inactive)", False,
                    f"HTTP {resp.status_code}: {resp.text[:200]}")
            return
        
        data = resp.json()
        
        # Verify all expected fields
        checks = []
        checks.append(("coupons_found == 100", data.get("coupons_found") == 100))
        checks.append(("already_active == 0", data.get("already_active") == 0))
        checks.append(("ready_to_activate == 100", data.get("ready_to_activate") == 100))
        checks.append(("skipped == 0", data.get("skipped") == 0))
        checks.append(("from_serial == 'QAT001'", data.get("from_serial") == "QAT001"))
        checks.append(("to_serial == 'QAT100'", data.get("to_serial") == "QAT100"))
        checks.append(("batch_label present", bool(data.get("batch_label"))))
        checks.append(("coupon_type == 'cash'", data.get("coupon_type") == "cash"))
        checks.append(("coupon_value == 20", data.get("coupon_value") == 20))
        
        failed_checks = [c[0] for c in checks if not c[1]]
        
        if failed_checks:
            log_test(1, "Live Preview happy path (all inactive)", False,
                    f"Failed checks: {', '.join(failed_checks)}. Response: {json.dumps(data, indent=2)}")
        else:
            log_test(1, "Live Preview happy path (all inactive)", True,
                    f"All checks passed. coupons_found={data['coupons_found']}, ready_to_activate={data['ready_to_activate']}")
    
    except Exception as e:
        log_test(1, "Live Preview happy path (all inactive)", False, f"Exception: {e}")


def test_2_activate_subrange_then_preview(token: str, batch_id: str):
    """TEST 2 — Activate a sub-range (existing endpoint) then re-preview"""
    try:
        # First, activate QAT001-QAT020
        activate_payload = {
            "batch_id": batch_id,
            "from_serial": "QAT001",
            "to_serial": "QAT020"
        }
        resp = requests.post(
            f"{API_BASE}/dms/coupons/activate-range",
            json=activate_payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if resp.status_code != 200:
            log_test(2, "Activate sub-range then re-preview", False,
                    f"Activation failed: HTTP {resp.status_code}: {resp.text[:200]}")
            return
        
        activate_data = resp.json()
        activated_count = activate_data.get("activated", 0)
        
        if activated_count != 20:
            log_test(2, "Activate sub-range then re-preview", False,
                    f"Expected activated=20, got {activated_count}")
            return
        
        # Now preview the full range again
        preview_payload = {
            "batch_id": batch_id,
            "from_serial": "QAT001",
            "to_serial": "QAT100"
        }
        resp = requests.post(
            f"{API_BASE}/dms/coupons/activate-range/preview",
            json=preview_payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if resp.status_code != 200:
            log_test(2, "Activate sub-range then re-preview", False,
                    f"Preview failed: HTTP {resp.status_code}: {resp.text[:200]}")
            return
        
        data = resp.json()
        
        # Verify expected counts
        checks = []
        checks.append(("coupons_found == 100", data.get("coupons_found") == 100))
        checks.append(("already_active == 20", data.get("already_active") == 20))
        checks.append(("ready_to_activate == 80", data.get("ready_to_activate") == 80))
        checks.append(("skipped == 0", data.get("skipped") == 0))
        
        failed_checks = [c[0] for c in checks if not c[1]]
        
        if failed_checks:
            log_test(2, "Activate sub-range then re-preview", False,
                    f"Failed checks: {', '.join(failed_checks)}. Response: {json.dumps(data, indent=2)}")
        else:
            log_test(2, "Activate sub-range then re-preview", True,
                    f"Activated 20, then preview shows already_active=20, ready_to_activate=80")
    
    except Exception as e:
        log_test(2, "Activate sub-range then re-preview", False, f"Exception: {e}")


def test_3_number_mode_input(token: str, batch_id: str):
    """TEST 3 — Number-mode input"""
    try:
        payload = {
            "batch_id": batch_id,
            "from_number": 21,
            "to_number": 40
        }
        resp = requests.post(
            f"{API_BASE}/dms/coupons/activate-range/preview",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if resp.status_code != 200:
            log_test(3, "Number-mode input", False,
                    f"HTTP {resp.status_code}: {resp.text[:200]}")
            return
        
        data = resp.json()
        
        # Verify expected fields
        checks = []
        checks.append(("from_serial == 'QAT021'", data.get("from_serial") == "QAT021"))
        checks.append(("to_serial == 'QAT040'", data.get("to_serial") == "QAT040"))
        checks.append(("coupons_found == 20", data.get("coupons_found") == 20))
        checks.append(("ready_to_activate == 20", data.get("ready_to_activate") == 20))
        
        failed_checks = [c[0] for c in checks if not c[1]]
        
        if failed_checks:
            log_test(3, "Number-mode input", False,
                    f"Failed checks: {', '.join(failed_checks)}. Response: {json.dumps(data, indent=2)}")
        else:
            log_test(3, "Number-mode input", True,
                    f"Number mode works: from_number=21 → QAT021, to_number=40 → QAT040")
    
    except Exception as e:
        log_test(3, "Number-mode input", False, f"Exception: {e}")


def test_4_auto_swap(token: str, batch_id: str):
    """TEST 4 — Auto-swap when from > to"""
    try:
        payload = {
            "batch_id": batch_id,
            "from_serial": "QAT050",
            "to_serial": "QAT030"
        }
        resp = requests.post(
            f"{API_BASE}/dms/coupons/activate-range/preview",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if resp.status_code != 200:
            log_test(4, "Auto-swap when from > to", False,
                    f"HTTP {resp.status_code}: {resp.text[:200]}")
            return
        
        data = resp.json()
        
        # Verify auto-swap happened
        checks = []
        checks.append(("from_serial == 'QAT030'", data.get("from_serial") == "QAT030"))
        checks.append(("to_serial == 'QAT050'", data.get("to_serial") == "QAT050"))
        
        failed_checks = [c[0] for c in checks if not c[1]]
        
        if failed_checks:
            log_test(4, "Auto-swap when from > to", False,
                    f"Failed checks: {', '.join(failed_checks)}. Response: {json.dumps(data, indent=2)}")
        else:
            log_test(4, "Auto-swap when from > to", True,
                    f"Auto-swap works: QAT050→QAT030 became QAT030→QAT050")
    
    except Exception as e:
        log_test(4, "Auto-swap when from > to", False, f"Exception: {e}")


def test_5_invalid_from_serial(token: str, batch_id: str):
    """TEST 5 — Invalid from_serial (out of batch range)"""
    try:
        payload = {
            "batch_id": batch_id,
            "from_serial": "QAT500",
            "to_serial": "QAT600"
        }
        resp = requests.post(
            f"{API_BASE}/dms/coupons/activate-range/preview",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        # Expect HTTP 400
        if resp.status_code == 400:
            detail = resp.json().get("detail", "")
            if "QAT500" in detail and "not found" in detail.lower():
                log_test(5, "Invalid from_serial (out of batch range)", True,
                        f"Correctly returned 400 with detail: {detail}")
            else:
                log_test(5, "Invalid from_serial (out of batch range)", False,
                        f"Got 400 but detail doesn't mention 'QAT500 not found': {detail}")
        else:
            log_test(5, "Invalid from_serial (out of batch range)", False,
                    f"Expected HTTP 400, got {resp.status_code}: {resp.text[:200]}")
    
    except Exception as e:
        log_test(5, "Invalid from_serial (out of batch range)", False, f"Exception: {e}")


def test_6_invalid_batch_id(token: str):
    """TEST 6 — Invalid batch_id"""
    try:
        payload = {
            "batch_id": "cbt-nonexistent",
            "from_serial": "QAT001",
            "to_serial": "QAT010"
        }
        resp = requests.post(
            f"{API_BASE}/dms/coupons/activate-range/preview",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        # Expect HTTP 404
        if resp.status_code == 404:
            log_test(6, "Invalid batch_id", True,
                    f"Correctly returned 404 for nonexistent batch")
        else:
            log_test(6, "Invalid batch_id", False,
                    f"Expected HTTP 404, got {resp.status_code}: {resp.text[:200]}")
    
    except Exception as e:
        log_test(6, "Invalid batch_id", False, f"Exception: {e}")


def test_7_rbac_distributor_cannot_preview(distributor_token: str, batch_id: str):
    """TEST 7 — RBAC — distributor cannot preview"""
    try:
        payload = {
            "batch_id": batch_id,
            "from_serial": "QAT001",
            "to_serial": "QAT010"
        }
        resp = requests.post(
            f"{API_BASE}/dms/coupons/activate-range/preview",
            json=payload,
            headers={"Authorization": f"Bearer {distributor_token}"},
            timeout=10
        )
        
        # Expect HTTP 403
        if resp.status_code == 403:
            log_test(7, "RBAC — distributor cannot preview", True,
                    f"Correctly returned 403 for distributor")
        else:
            log_test(7, "RBAC — distributor cannot preview", False,
                    f"Expected HTTP 403, got {resp.status_code}: {resp.text[:200]}")
    
    except Exception as e:
        log_test(7, "RBAC — distributor cannot preview", False, f"Exception: {e}")


def test_8_activate_range_existence_check(token: str, batch_id: str):
    """TEST 8 — /activate-range still requires existence (regression)"""
    try:
        payload = {
            "batch_id": batch_id,
            "from_serial": "QAT999",
            "to_serial": "QAT1000"
        }
        resp = requests.post(
            f"{API_BASE}/dms/coupons/activate-range",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        # Expect HTTP 400 (from serial not found)
        if resp.status_code == 400:
            detail = resp.json().get("detail", "")
            if "not found" in detail.lower():
                log_test(8, "/activate-range still requires existence (regression)", True,
                        f"Correctly returned 400 with detail: {detail}")
            else:
                log_test(8, "/activate-range still requires existence (regression)", False,
                        f"Got 400 but detail doesn't mention 'not found': {detail}")
        else:
            log_test(8, "/activate-range still requires existence (regression)", False,
                    f"Expected HTTP 400, got {resp.status_code}: {resp.text[:200]}")
    
    except Exception as e:
        log_test(8, "/activate-range still requires existence (regression)", False, f"Exception: {e}")


def test_9_pdf_export_smoke_test(token: str, batch_id: str):
    """TEST 9 — PDF export smoke test with security checks"""
    try:
        # First, get batch details to fetch hmac_secret if possible
        batch_resp = requests.get(
            f"{API_BASE}/dms/coupons/batches/{batch_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        batch_data = {}
        if batch_resp.status_code == 200:
            batch_data = batch_resp.json()
        
        # Now export PDF
        resp = requests.get(
            f"{API_BASE}/dms/coupons/batches/{batch_id}/export-pdf",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )
        
        if resp.status_code != 200:
            log_test(9, "PDF export smoke test", False,
                    f"HTTP {resp.status_code}: {resp.text[:200]}")
            return
        
        # Check Content-Type
        content_type = resp.headers.get("Content-Type", "")
        if "application/pdf" not in content_type:
            log_test(9, "PDF export smoke test", False,
                    f"Wrong Content-Type: {content_type}")
            return
        
        # Check body size
        pdf_bytes = resp.content
        pdf_size = len(pdf_bytes)
        if pdf_size < 100_000:  # Should be > 100 KB
            log_test(9, "PDF export smoke test", False,
                    f"PDF too small: {pdf_size} bytes (expected > 100 KB)")
            return
        
        # Check PDF header
        if not pdf_bytes.startswith(b"%PDF-1."):
            log_test(9, "PDF export smoke test", False,
                    f"PDF doesn't start with %PDF-1.x header")
            return
        
        # CRITICAL SECURITY CHECK — byte-scan for forbidden strings
        pdf_text = pdf_bytes.decode("latin-1", errors="ignore")
        
        forbidden_strings = [
            "hmac_secret",
            "hidden_secure_id",
            "qr_signature_v2",
            "secret_token",
        ]
        
        # Check for GOOIL2| plaintext (should NOT appear as text literal)
        # It may appear in compressed image streams, but not as plaintext
        if "GOOIL2|" in pdf_text:
            # Check if it's in a text context (not just binary)
            # Simple heuristic: if surrounded by printable chars, it's likely plaintext
            idx = pdf_text.find("GOOIL2|")
            context = pdf_text[max(0, idx-20):idx+50]
            # If context has mostly printable ASCII, it's suspicious
            printable_ratio = sum(1 for c in context if 32 <= ord(c) <= 126) / len(context)
            if printable_ratio > 0.7:
                log_test(9, "PDF export smoke test", False,
                        f"SECURITY VIOLATION: Found 'GOOIL2|' as plaintext in PDF. Context: {repr(context)}")
                return
        
        found_forbidden = []
        for forbidden in forbidden_strings:
            if forbidden in pdf_text:
                found_forbidden.append(forbidden)
        
        if found_forbidden:
            log_test(9, "PDF export smoke test", False,
                    f"SECURITY VIOLATION: Found forbidden strings in PDF: {', '.join(found_forbidden)}")
            return
        
        # All checks passed
        log_test(9, "PDF export smoke test", True,
                f"PDF export OK: {pdf_size} bytes, Content-Type correct, no secrets leaked")
    
    except Exception as e:
        log_test(9, "PDF export smoke test", False, f"Exception: {e}")


def print_summary():
    """Print test summary."""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in test_results if r["passed"])
    total = len(test_results)
    
    for result in test_results:
        status = "✅" if result["passed"] else "❌"
        print(f"{status} {result['test']}: {result['name']}")
        if result["details"] and not result["passed"]:
            print(f"   {result['details']}")
    
    print("\n" + "="*80)
    print(f"TOTAL: {passed}/{total} tests passed ({passed*100//total if total > 0 else 0}%)")
    print("="*80)
    
    return passed == total


def main():
    """Main test runner."""
    global owner_token, distributor_token, test_batch_id, test_batch_label
    
    print("="*80)
    print("COUPON ACTIVATION LIVE PREVIEW + PDF EXPORT TEST SUITE")
    print("="*80)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"API Base: {API_BASE}")
    print()
    
    # SETUP: Login as owner
    print("SETUP — Login as owner...")
    owner_token = login(OWNER_EMAIL, OWNER_PASSWORD)
    if not owner_token:
        print("❌ FATAL: Cannot login as owner. Aborting tests.")
        sys.exit(1)
    
    # SETUP: Login as distributor
    print("\nSETUP — Login as distributor...")
    distributor_token = login(DISTRIBUTOR_EMAIL, DISTRIBUTOR_PASSWORD)
    if not distributor_token:
        print("❌ FATAL: Cannot login as distributor. Aborting tests.")
        sys.exit(1)
    
    # SETUP: Create test batch
    print("\nSETUP — Create test batch...")
    test_batch_id, test_batch_label = create_test_batch(owner_token)
    if not test_batch_id:
        print("❌ FATAL: Cannot create test batch. Aborting tests.")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("RUNNING TESTS")
    print("="*80)
    
    # Run all tests
    test_1_preview_happy_path(owner_token, test_batch_id)
    test_2_activate_subrange_then_preview(owner_token, test_batch_id)
    test_3_number_mode_input(owner_token, test_batch_id)
    test_4_auto_swap(owner_token, test_batch_id)
    test_5_invalid_from_serial(owner_token, test_batch_id)
    test_6_invalid_batch_id(owner_token)
    test_7_rbac_distributor_cannot_preview(distributor_token, test_batch_id)
    test_8_activate_range_existence_check(owner_token, test_batch_id)
    test_9_pdf_export_smoke_test(owner_token, test_batch_id)
    
    # Print summary
    all_passed = print_summary()
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
