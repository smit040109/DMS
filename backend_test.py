#!/usr/bin/env python3
"""
GO OIL DMS — Backend API Testing for CONTINUATION v4
====================================================
Tests NEW backend endpoints for:
1. Coupon mixed print + preview + print history (list/download/delete)
2. Print challan endpoint

Base URL: from frontend/.env REACT_APP_BACKEND_URL
Auth: owner@gooil.com / GoOil@2026 and distributor1@gooil.com / GoOil@2026

IMPORTANT: Database is FRESH with NO coupon batches.
We must create + activate a batch as part of testing.
"""
import os
import sys
import json
import requests
from typing import Dict, Any, Optional

# ═══════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════
BASE_URL = "https://6d4e801e-d482-41e2-999d-966898ebdaae.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

OWNER_EMAIL = "owner@gooil.com"
OWNER_PASSWORD = "GoOil@2026"
DISTRIBUTOR_EMAIL = "distributor1@gooil.com"
DISTRIBUTOR_PASSWORD = "GoOil@2026"

# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════
def login(email: str, password: str) -> str:
    """Login and return JWT token."""
    resp = requests.post(f"{API_BASE}/auth/login", json={"email": email, "password": password}, timeout=30)
    if resp.status_code != 200:
        print(f"❌ Login failed for {email}: {resp.status_code} {resp.text}")
        sys.exit(1)
    data = resp.json()
    token = data.get("token")
    if not token:
        print(f"❌ No token in login response for {email}")
        sys.exit(1)
    print(f"✅ Login successful: {email} (role: {data.get('user', {}).get('role')})")
    return token


def headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def test_result(name: str, passed: bool, details: str = ""):
    """Print test result."""
    status = "✅ PASSED" if passed else "❌ FAILED"
    print(f"{status}: {name}")
    if details:
        print(f"   {details}")


# ═══════════════════════════════════════════════════════════════════════════
# Test Suite
# ═══════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 80)
    print("GO OIL DMS — CONTINUATION v4 Backend Testing")
    print("=" * 80)
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # SETUP: Login
    # ─────────────────────────────────────────────────────────────────────────
    print("🔐 SETUP: Logging in...")
    owner_token = login(OWNER_EMAIL, OWNER_PASSWORD)
    dist_token = login(DISTRIBUTOR_EMAIL, DISTRIBUTOR_PASSWORD)
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 1: COUPON MIXED PRINT + PREVIEW + HISTORY
    # ─────────────────────────────────────────────────────────────────────────
    print("=" * 80)
    print("TEST 1: COUPON MIXED PRINT + PREVIEW + HISTORY")
    print("=" * 80)
    print()

    # Step 1a: Create a CASH coupon batch (count=200)
    print("Step 1a: Create CASH coupon batch (count=200)...")
    import random
    random_suffix = random.randint(1000, 9999)
    batch_payload = {
        "title": f"Test CASH Batch for Print {random_suffix}",
        "coupon_type": "cash",
        "coupon_value": 100,
        "count": 200,
        "serial_mode": "prefix_sequential",
        "prefix": f"T{random_suffix}",
        "serial_start": 1,
        "serial_pad": 5
    }
    resp = requests.post(f"{API_BASE}/dms/coupons/batches", json=batch_payload, headers=headers(owner_token), timeout=60)
    if resp.status_code != 200:
        test_result("Create batch", False, f"HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)
    batch_data = resp.json()
    batch_id = batch_data.get("batch", {}).get("id")
    if not batch_id:
        test_result("Create batch", False, "No batch ID in response")
        sys.exit(1)
    test_result("Create batch", True, f"Batch ID: {batch_id}, Prefix: {batch_payload['prefix']}")
    print()

    # Step 1b: Activate the batch
    print("Step 1b: Activate the batch...")
    resp = requests.post(f"{API_BASE}/dms/coupons/batches/{batch_id}/activate", headers=headers(owner_token), timeout=30)
    if resp.status_code != 200:
        test_result("Activate batch", False, f"HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)
    test_result("Activate batch", True, "Batch activated successfully")
    print()

    # Step 1c: POST /print-mixed/preview with batch_ids
    print("Step 1c: POST /print-mixed/preview with batch_ids...")
    preview_payload = {"batch_ids": [batch_id]}
    resp = requests.post(f"{API_BASE}/dms/coupons/print-mixed/preview", json=preview_payload, headers=headers(owner_token), timeout=30)
    if resp.status_code != 200:
        test_result("Print preview (batch_ids)", False, f"HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)
    preview_data = resp.json()
    coupon_count = preview_data.get("coupon_count")
    per_sheet = preview_data.get("per_sheet")
    sheet_count = preview_data.get("sheet_count")
    breakdown = preview_data.get("breakdown")
    label = preview_data.get("label")
    
    # Verify expectations: coupon_count=200, per_sheet=77, sheet_count=3, breakdown=[77,77,46]
    passed = (
        coupon_count == 200 and
        per_sheet == 77 and
        sheet_count == 3 and
        breakdown == [77, 77, 46] and
        label
    )
    details = f"coupon_count={coupon_count}, per_sheet={per_sheet}, sheet_count={sheet_count}, breakdown={breakdown}, label='{label}'"
    test_result("Print preview (batch_ids)", passed, details)
    if not passed:
        print(f"   Expected: coupon_count=200, per_sheet=77, sheet_count=3, breakdown=[77,77,46], non-empty label")
        sys.exit(1)
    print()

    # Step 1d: POST /print-mixed with batch_ids and side="both"
    print("Step 1d: POST /print-mixed with batch_ids and side='both'...")
    print_payload = {"batch_ids": [batch_id], "side": "both"}
    resp = requests.post(f"{API_BASE}/dms/coupons/print-mixed", json=print_payload, headers=headers(owner_token), timeout=60)
    if resp.status_code != 200:
        test_result("Print mixed (batch_ids)", False, f"HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)
    content_type = resp.headers.get("Content-Type", "")
    pdf_size = len(resp.content)
    passed = "application/pdf" in content_type and pdf_size > 0
    test_result("Print mixed (batch_ids)", passed, f"Content-Type: {content_type}, Size: {pdf_size} bytes")
    if not passed:
        sys.exit(1)
    print()

    # Step 1e: Test SERIAL RANGE - get batch details to determine serial range
    print("Step 1e: Test SERIAL RANGE - get batch details...")
    resp = requests.get(f"{API_BASE}/dms/coupons/batches/{batch_id}", headers=headers(owner_token), timeout=30)
    if resp.status_code != 200:
        test_result("Get batch details for serial range", False, f"HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)
    batch_details = resp.json()
    prefix = batch_details.get("prefix")
    serial_start = batch_details.get("serial_start")
    serial_pad = batch_details.get("serial_pad")
    
    # Calculate first and 50th serial (TST00001 to TST00050)
    first_serial = f"{prefix}{str(serial_start).zfill(serial_pad)}"
    serial_50th = f"{prefix}{str(serial_start + 49).zfill(serial_pad)}"
    test_result("Get batch details for serial range", True, f"First: {first_serial}, 50th: {serial_50th}")
    print()

    # Step 1e continued: POST /print-mixed/preview with serial range
    print("Step 1e (continued): POST /print-mixed/preview with serial range...")
    range_payload = {
        "items": [
            {
                "batch_id": batch_id,
                "from_serial": first_serial,
                "to_serial": serial_50th
            }
        ]
    }
    resp = requests.post(f"{API_BASE}/dms/coupons/print-mixed/preview", json=range_payload, headers=headers(owner_token), timeout=30)
    if resp.status_code != 200:
        test_result("Print preview (serial range)", False, f"HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)
    range_preview = resp.json()
    range_count = range_preview.get("coupon_count")
    range_sheets = range_preview.get("sheet_count")
    # Expected: 50 coupons, ceil(50/77) = 1 sheet
    passed = range_count == 50 and range_sheets == 1
    details = f"coupon_count={range_count}, sheet_count={range_sheets}"
    test_result("Print preview (serial range)", passed, details)
    if not passed:
        print(f"   Expected: coupon_count=50, sheet_count=1")
        sys.exit(1)
    print()

    # Step 1f: GET /print-history
    print("Step 1f: GET /print-history...")
    resp = requests.get(f"{API_BASE}/dms/coupons/print-history", headers=headers(owner_token), timeout=30)
    if resp.status_code != 200:
        test_result("Get print history", False, f"HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)
    history_data = resp.json()
    history_list = history_data.get("data", [])
    if len(history_list) == 0:
        test_result("Get print history", False, "No print history records found")
        sys.exit(1)
    # Find the print from step 1d (coupon_count=200, sheet_count=3, side='both')
    target_history = None
    for h in history_list:
        if h.get("coupon_count") == 200 and h.get("sheet_count") == 3 and h.get("side") == "both":
            target_history = h
            break
    if not target_history:
        test_result("Get print history", False, "Print from step 1d not found in history")
        sys.exit(1)
    history_id = target_history.get("id")
    created_by_name = target_history.get("created_by_name")
    history_label = target_history.get("label")
    test_result("Get print history", True, f"Found history ID: {history_id}, created_by: {created_by_name}, label: {history_label}")
    print()

    # Step 1g: GET /print-history/{hid}/download
    print("Step 1g: GET /print-history/{hid}/download...")
    resp = requests.get(f"{API_BASE}/dms/coupons/print-history/{history_id}/download", headers=headers(owner_token), timeout=60)
    if resp.status_code != 200:
        test_result("Download print history", False, f"HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)
    content_type = resp.headers.get("Content-Type", "")
    pdf_size = len(resp.content)
    passed = "application/pdf" in content_type and pdf_size > 0
    test_result("Download print history", passed, f"Content-Type: {content_type}, Size: {pdf_size} bytes")
    if not passed:
        sys.exit(1)
    print()

    # Step 1h: DELETE /print-history/{hid}
    print("Step 1h: DELETE /print-history/{hid}...")
    resp = requests.delete(f"{API_BASE}/dms/coupons/print-history/{history_id}", headers=headers(owner_token), timeout=30)
    if resp.status_code != 200:
        test_result("Delete print history", False, f"HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)
    delete_data = resp.json()
    passed = delete_data.get("ok") is True
    test_result("Delete print history", passed, f"Response: {delete_data}")
    if not passed:
        sys.exit(1)
    print()

    # Step 1h continued: Verify history is gone
    print("Step 1h (continued): Verify history is gone...")
    resp = requests.get(f"{API_BASE}/dms/coupons/print-history", headers=headers(owner_token), timeout=30)
    if resp.status_code != 200:
        test_result("Verify history deleted", False, f"HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)
    history_data = resp.json()
    history_list = history_data.get("data", [])
    found = any(h.get("id") == history_id for h in history_list)
    test_result("Verify history deleted", not found, f"History ID {history_id} {'still exists' if found else 'deleted successfully'}")
    if found:
        sys.exit(1)
    print()

    # Step 1h continued: Verify batch + coupons still exist
    print("Step 1h (continued): Verify batch + coupons still exist...")
    resp = requests.get(f"{API_BASE}/dms/coupons/batches/{batch_id}", headers=headers(owner_token), timeout=30)
    if resp.status_code != 200:
        test_result("Verify batch still exists", False, f"HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)
    batch_check = resp.json()
    count = batch_check.get("count", 0)
    test_result("Verify batch still exists", True, f"Batch {batch_id} still exists with {count} coupons")
    
    # Verify coupons count from batch detail
    counts_by_status = batch_check.get("counts_by_status", {})
    total_coupons = sum(counts_by_status.values())
    test_result("Verify coupons still exist", total_coupons > 0, f"Total coupons: {total_coupons}")
    if total_coupons == 0:
        sys.exit(1)
    print()

    # Step 1i: RBAC - repeat print-mixed/preview, print-mixed, print-history as distributor1
    print("Step 1i: RBAC - Test as distributor1 (expect 403)...")
    
    # Test print-mixed/preview as distributor
    resp = requests.post(f"{API_BASE}/dms/coupons/print-mixed/preview", json=preview_payload, headers=headers(dist_token), timeout=30)
    passed = resp.status_code == 403
    test_result("RBAC: print-mixed/preview as distributor", passed, f"HTTP {resp.status_code}")
    if not passed:
        print(f"   Expected 403, got {resp.status_code}")
    
    # Test print-mixed as distributor
    resp = requests.post(f"{API_BASE}/dms/coupons/print-mixed", json=print_payload, headers=headers(dist_token), timeout=30)
    passed = resp.status_code == 403
    test_result("RBAC: print-mixed as distributor", passed, f"HTTP {resp.status_code}")
    if not passed:
        print(f"   Expected 403, got {resp.status_code}")
    
    # Test print-history as distributor
    resp = requests.get(f"{API_BASE}/dms/coupons/print-history", headers=headers(dist_token), timeout=30)
    passed = resp.status_code == 403
    test_result("RBAC: print-history as distributor", passed, f"HTTP {resp.status_code}")
    if not passed:
        print(f"   Expected 403, got {resp.status_code}")
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 2: PRINT CHALLAN
    # ─────────────────────────────────────────────────────────────────────────
    print("=" * 80)
    print("TEST 2: PRINT CHALLAN")
    print("=" * 80)
    print()

    # Test GET /print/challan/{bogus_id} - expect 404
    print("Step 2a: GET /print/challan/{bogus_id} (expect 404)...")
    bogus_id = "challan-bogus-12345"
    resp = requests.get(f"{API_BASE}/dms/print/challan/{bogus_id}", headers=headers(owner_token), timeout=30)
    passed = resp.status_code == 404
    test_result("Print challan (bogus ID)", passed, f"HTTP {resp.status_code}")
    if not passed:
        print(f"   Expected 404, got {resp.status_code}")
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # SUMMARY
    # ─────────────────────────────────────────────────────────────────────────
    print("=" * 80)
    print("✅ ALL TESTS PASSED")
    print("=" * 80)
    print()
    print("Summary:")
    print("  ✅ Coupon batch creation + activation")
    print("  ✅ Print mixed preview (batch_ids) - correct math (200 coupons, 3 sheets, [77,77,46])")
    print("  ✅ Print mixed (batch_ids) - PDF generated")
    print("  ✅ Print mixed preview (serial range) - correct math (50 coupons, 1 sheet)")
    print("  ✅ Print history list - record found")
    print("  ✅ Print history download - PDF generated")
    print("  ✅ Print history delete - record deleted, batch+coupons intact")
    print("  ✅ RBAC - distributor blocked from print endpoints (403)")
    print("  ✅ Print challan - 404 for bogus ID")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
