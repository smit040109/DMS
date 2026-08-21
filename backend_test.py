#!/usr/bin/env python3
"""
Backend API Testing for GO OIL DMS - Coupon Features
Tests:
  GROUP A: Coupon Sheet PDF endpoints (template edits verification)
  GROUP B: Sales Person CASH coupon reduces Retailer↔Distributor outstanding
  GROUP C: POINTS coupon credits reward wallet, NOT cash ledger
"""

import requests
import time
import json
from typing import Optional, Dict, Any

# Base URL from frontend/.env
BASE_URL = "https://points-wallet-hub-2.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
OWNER_EMAIL = "gooilindia13@gmail.com"
OWNER_PASSWORD = "Arjun@india13"
SALESPERSON_EMAIL = "salesperson@gooil.com"
SALESPERSON_PASSWORD = "GoOil@2026"

# Seeded demo IDs
DISTRIBUTOR_ID = "dist-5effaa6a97"  # Anil Distributor — Delhi
RETAILER_ID = "ret-7acf91f94c"      # Sharma Auto Parts
SALESPERSON_ID = "usr-7e2502836b"

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def log_test(message, status="INFO"):
    """Log test messages with color coding"""
    color = {
        "PASS": GREEN,
        "FAIL": RED,
        "INFO": BLUE,
        "WARN": YELLOW
    }.get(status, RESET)
    print(f"{color}[{status}]{RESET} {message}")

def login(email: str, password: str) -> Optional[str]:
    """Login and return JWT token"""
    log_test(f"Logging in as {email}...", "INFO")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password}
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("token")
        role = data.get('user', {}).get('role')
        log_test(f"Login successful. Role: {role}", "PASS")
        return token
    else:
        log_test(f"Login failed: {response.status_code} - {response.text}", "FAIL")
        return None

# ═════════════════════════════════════════════════════════════════════════════
# TEST GROUP A: Coupon Sheet PDF endpoints (template edits verification)
# ═════════════════════════════════════════════════════════════════════════════

def test_group_a_pdf_endpoints(owner_token: str) -> Dict[str, bool]:
    """Test coupon PDF endpoints after template edits"""
    log_test("\n" + "="*80, "INFO")
    log_test("TEST GROUP A: Coupon Sheet PDF Endpoints", "INFO")
    log_test("="*80, "INFO")
    
    results = {}
    headers = {"Authorization": f"Bearer {owner_token}"}
    
    # Use timestamp to ensure unique prefix
    unique_suffix = str(int(time.time()))[-4:]
    
    # A1: Create CASH batch
    log_test("\n[A1] Creating CASH batch...", "INFO")
    batch_payload = {
        "coupon_type": "cash",
        "coupon_value": 100,
        "count": 100,
        "prefix": f"QA{unique_suffix}",
        "serial_start": 1,
        "serial_pad": 3,
        "title": "QA Test Batch"
    }
    response = requests.post(
        f"{BASE_URL}/dms/coupons/batches",
        headers=headers,
        json=batch_payload
    )
    
    if response.status_code == 200:
        data = response.json()
        batch_id = data.get("batch", {}).get("id")
        batch_label = data.get("batch", {}).get("batch_label")
        log_test(f"✓ Batch created: {batch_label} (ID: {batch_id})", "PASS")
        results["a1_create_batch"] = True
    else:
        log_test(f"✗ Failed to create batch: {response.status_code} - {response.text[:200]}", "FAIL")
        results["a1_create_batch"] = False
        return results
    
    # A2: Activate batch
    log_test("\n[A2] Activating batch...", "INFO")
    response = requests.post(
        f"{BASE_URL}/dms/coupons/batches/{batch_id}/activate",
        headers=headers
    )
    
    if response.status_code == 200:
        log_test(f"✓ Batch {batch_label} activated", "PASS")
        results["a2_activate_batch"] = True
    else:
        log_test(f"✗ Failed to activate batch: {response.status_code} - {response.text[:200]}", "FAIL")
        results["a2_activate_batch"] = False
        return results
    
    # A3: Export PDF (side=both)
    log_test("\n[A3] Testing export-pdf?side=both...", "INFO")
    response = requests.get(
        f"{BASE_URL}/dms/coupons/batches/{batch_id}/export-pdf?side=both",
        headers=headers
    )
    
    if response.status_code == 200:
        content_type = response.headers.get("Content-Type", "")
        content_length = len(response.content)
        first_bytes = response.content[:4]
        
        if "application/pdf" in content_type and first_bytes == b'%PDF' and content_length > 0:
            log_test(f"✓ Valid PDF returned: {content_length:,} bytes", "PASS")
            results["a3_export_pdf"] = True
        else:
            log_test(f"✗ Invalid PDF: content_type={content_type}, starts_with={first_bytes}", "FAIL")
            results["a3_export_pdf"] = False
    else:
        log_test(f"✗ Export PDF failed: {response.status_code} - {response.text[:200]}", "FAIL")
        results["a3_export_pdf"] = False
    
    # A4: Print-mixed
    log_test("\n[A4] Testing print-mixed...", "INFO")
    response = requests.post(
        f"{BASE_URL}/dms/coupons/print-mixed",
        headers=headers,
        json={"batch_ids": [batch_id], "side": "both"}
    )
    
    if response.status_code == 200:
        content_type = response.headers.get("Content-Type", "")
        content_length = len(response.content)
        first_bytes = response.content[:4]
        
        if "application/pdf" in content_type and first_bytes == b'%PDF' and content_length > 0:
            log_test(f"✓ Valid PDF returned: {content_length:,} bytes", "PASS")
            results["a4_print_mixed"] = True
        else:
            log_test(f"✗ Invalid PDF: content_type={content_type}, starts_with={first_bytes}", "FAIL")
            results["a4_print_mixed"] = False
    else:
        log_test(f"✗ Print-mixed failed: {response.status_code} - {response.text[:200]}", "FAIL")
        results["a4_print_mixed"] = False
    
    # A5: Print-mixed/preview (per_sheet should be 77)
    log_test("\n[A5] Testing print-mixed/preview (per_sheet verification)...", "INFO")
    response = requests.post(
        f"{BASE_URL}/dms/coupons/print-mixed/preview",
        headers=headers,
        json={"batch_ids": [batch_id]}
    )
    
    if response.status_code == 200:
        data = response.json()
        per_sheet = data.get("per_sheet")
        
        if per_sheet == 77:
            log_test(f"✓ per_sheet = 77 (CORRECT)", "PASS")
            results["a5_preview_per_sheet"] = True
        else:
            log_test(f"✗ per_sheet = {per_sheet} (expected 77)", "FAIL")
            results["a5_preview_per_sheet"] = False
    else:
        log_test(f"✗ Print-mixed preview failed: {response.status_code} - {response.text[:200]}", "FAIL")
        results["a5_preview_per_sheet"] = False
    
    return results

# ═════════════════════════════════════════════════════════════════════════════
# TEST GROUP B: Sales Person CASH coupon reduces Retailer↔Distributor outstanding
# ═════════════════════════════════════════════════════════════════════════════

def test_group_b_cash_coupon_ledger(owner_token: str, sp_token: str) -> Dict[str, bool]:
    """Test Sales Person CASH coupon scan reduces retailer outstanding"""
    log_test("\n" + "="*80, "INFO")
    log_test("TEST GROUP B: Sales Person CASH Coupon → Retailer Outstanding", "INFO")
    log_test("="*80, "INFO")
    
    results = {}
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    sp_headers = {"Authorization": f"Bearer {sp_token}"}
    
    # Use timestamp to ensure unique prefix
    unique_suffix = str(int(time.time()))[-4:]
    
    # B0: Setup - Create CASH batch, activate, assign to distributor via box workflow
    log_test("\n[B0] Setup: Creating CASH batch for retailer test...", "INFO")
    batch_payload = {
        "coupon_type": "cash",
        "coupon_value": 200,
        "count": 5,
        "prefix": f"CSH{unique_suffix}",
        "serial_start": 1,
        "serial_pad": 3,
        "title": "Cash Test Batch"
    }
    response = requests.post(
        f"{BASE_URL}/dms/coupons/batches",
        headers=owner_headers,
        json=batch_payload
    )
    
    if response.status_code != 200:
        log_test(f"✗ Failed to create CASH batch: {response.status_code}", "FAIL")
        results["b0_setup"] = False
        return results
    
    cash_batch_id = response.json().get("batch", {}).get("id")
    log_test(f"✓ CASH batch created: {cash_batch_id}", "PASS")
    
    # Activate batch
    response = requests.post(
        f"{BASE_URL}/dms/coupons/batches/{cash_batch_id}/activate",
        headers=owner_headers
    )
    if response.status_code != 200:
        log_test(f"✗ Failed to activate CASH batch: {response.status_code}", "FAIL")
        results["b0_setup"] = False
        return results
    log_test(f"✓ CASH batch activated", "PASS")
    
    # Create box
    response = requests.post(
        f"{BASE_URL}/dms/coupons/boxes",
        headers=owner_headers,
        json={"notes": "Test box for cash coupons"}
    )
    if response.status_code != 200:
        log_test(f"✗ Failed to create box: {response.status_code}", "FAIL")
        results["b0_setup"] = False
        return results
    
    box_id = response.json().get("box", {}).get("id")
    box_number = response.json().get("box", {}).get("box_number")
    log_test(f"✓ Box created: {box_number} (ID: {box_id})", "PASS")
    
    # Assign coupons to box
    first_serial = f"CSH{unique_suffix}001"
    last_serial = f"CSH{unique_suffix}005"
    response = requests.post(
        f"{BASE_URL}/dms/coupons/boxes/{box_id}/assign-coupons",
        headers=owner_headers,
        json={"batch_id": cash_batch_id, "from_serial": first_serial, "to_serial": last_serial}
    )
    if response.status_code != 200:
        log_test(f"✗ Failed to assign coupons to box: {response.status_code} - {response.text[:200]}", "FAIL")
        results["b0_setup"] = False
        return results
    log_test(f"✓ Coupons assigned to box", "PASS")
    
    # Assign box to distributor
    response = requests.post(
        f"{BASE_URL}/dms/coupons/boxes/{box_id}/assign-distributor",
        headers=owner_headers,
        json={"distributor_id": DISTRIBUTOR_ID}
    )
    if response.status_code != 200:
        log_test(f"✗ Failed to assign box to distributor: {response.status_code} - {response.text[:200]}", "FAIL")
        results["b0_setup"] = False
        return results
    log_test(f"✓ Box assigned to distributor {DISTRIBUTOR_ID}", "PASS")
    
    # Get one coupon code for scanning
    response = requests.get(
        f"{BASE_URL}/dms/coupons?batch_id={cash_batch_id}&limit=1",
        headers=owner_headers
    )
    if response.status_code != 200 or not response.json().get("data"):
        log_test(f"✗ Failed to fetch coupon code: {response.status_code}", "FAIL")
        results["b0_setup"] = False
        return results
    
    coupon_code = response.json()["data"][0].get("visible_serial") or response.json()["data"][0].get("coupon_code")
    log_test(f"✓ Coupon code for scanning: {coupon_code}", "PASS")
    results["b0_setup"] = True
    
    # B1: Get current outstanding for retailer
    log_test("\n[B1] Getting current outstanding for retailer...", "INFO")
    response = requests.get(
        f"{BASE_URL}/dms/ledger/secondary?retailer_id={RETAILER_ID}",
        headers=owner_headers
    )
    
    if response.status_code == 200:
        data = response.json()
        summary_list = data.get("summary", [])
        # Find the retailer in summary list
        retailer_summary = next((s for s in summary_list if s.get("retailer_id") == RETAILER_ID), None)
        if retailer_summary:
            current_outstanding = retailer_summary.get("outstanding", 0)
            log_test(f"✓ Current outstanding: ₹{current_outstanding}", "PASS")
            results["b1_get_outstanding"] = True
        else:
            current_outstanding = 0
            log_test(f"✓ No ledger entries yet, outstanding: ₹0", "PASS")
            results["b1_get_outstanding"] = True
    else:
        log_test(f"✗ Failed to get ledger: {response.status_code}", "FAIL")
        results["b1_get_outstanding"] = False
        return results
    
    # B2: Scan preview (should show projected outstanding)
    log_test("\n[B2] Testing scan/preview...", "INFO")
    response = requests.post(
        f"{BASE_URL}/dms/coupons/scan/preview",
        headers=sp_headers,
        json={"retailer_id": RETAILER_ID, "coupon_code": coupon_code}
    )
    
    if response.status_code == 200:
        data = response.json()
        preview = data.get("preview", {})
        
        if data.get("ok") and preview.get("coupon_type") == "cash":
            current = preview.get("current_outstanding")
            projected = preview.get("projected_outstanding")
            log_test(f"✓ Preview OK: current={current}, projected={projected}", "PASS")
            log_test(f"  Expected reduction: ₹200", "INFO")
            results["b2_scan_preview"] = True
        else:
            log_test(f"✗ Preview failed or not cash: ok={data.get('ok')}, type={preview.get('coupon_type')}", "FAIL")
            results["b2_scan_preview"] = False
    else:
        log_test(f"✗ Scan preview failed: {response.status_code} - {response.text[:200]}", "FAIL")
        results["b2_scan_preview"] = False
    
    # B3: Actual scan (should reduce outstanding by 200)
    log_test("\n[B3] Scanning CASH coupon...", "INFO")
    response = requests.post(
        f"{BASE_URL}/dms/coupons/scan",
        headers=sp_headers,
        json={"retailer_id": RETAILER_ID, "coupon_code": coupon_code}
    )
    
    if response.status_code == 200:
        data = response.json()
        wallet_type = data.get("wallet_type")
        new_outstanding = data.get("new_outstanding")
        
        if wallet_type == "cash":
            expected_outstanding = max(0, current_outstanding - 200)
            if abs(new_outstanding - expected_outstanding) < 0.01:
                log_test(f"✓ Scan successful: wallet_type=cash, new_outstanding=₹{new_outstanding}", "PASS")
                results["b3_scan_coupon"] = True
            else:
                log_test(f"✗ Outstanding mismatch: expected ₹{expected_outstanding}, got ₹{new_outstanding}", "FAIL")
                results["b3_scan_coupon"] = False
        else:
            log_test(f"✗ Wrong wallet_type: {wallet_type} (expected 'cash')", "FAIL")
            results["b3_scan_coupon"] = False
    else:
        log_test(f"✗ Scan failed: {response.status_code} - {response.text[:200]}", "FAIL")
        results["b3_scan_coupon"] = False
    
    # B4: Verify ledger updated
    log_test("\n[B4] Verifying ledger updated...", "INFO")
    response = requests.get(
        f"{BASE_URL}/dms/ledger/secondary?retailer_id={RETAILER_ID}",
        headers=owner_headers
    )
    
    if response.status_code == 200:
        data = response.json()
        summary_list = data.get("summary", [])
        retailer_summary = next((s for s in summary_list if s.get("retailer_id") == RETAILER_ID), None)
        
        if retailer_summary:
            new_outstanding_ledger = retailer_summary.get("outstanding", 0)
        else:
            new_outstanding_ledger = 0
        
        expected_outstanding = max(0, current_outstanding - 200)
        
        if abs(new_outstanding_ledger - expected_outstanding) < 0.01:
            log_test(f"✓ Ledger updated: outstanding dropped by ₹200 (now ₹{new_outstanding_ledger})", "PASS")
            results["b4_verify_ledger"] = True
            
            # Check for coupon_credit entry
            entries = data.get("entries", [])
            coupon_credit_found = any(e.get("kind") == "coupon_credit" for e in entries)
            if coupon_credit_found:
                log_test(f"✓ coupon_credit entry found in ledger", "PASS")
            else:
                log_test(f"⚠ No coupon_credit entry found (may be in different page)", "WARN")
        else:
            log_test(f"✗ Outstanding mismatch: expected ₹{expected_outstanding}, got ₹{new_outstanding_ledger}", "FAIL")
            results["b4_verify_ledger"] = False
    else:
        log_test(f"✗ Failed to get ledger: {response.status_code}", "FAIL")
        results["b4_verify_ledger"] = False
    
    # B5: Duplicate scan (should return 400)
    log_test("\n[B5] Testing duplicate scan (should fail)...", "INFO")
    response = requests.post(
        f"{BASE_URL}/dms/coupons/scan",
        headers=sp_headers,
        json={"retailer_id": RETAILER_ID, "coupon_code": coupon_code}
    )
    
    if response.status_code == 400:
        log_test(f"✓ Duplicate scan rejected with 400 (correct)", "PASS")
        results["b5_duplicate_rejected"] = True
    else:
        log_test(f"✗ Duplicate scan returned {response.status_code} (expected 400)", "FAIL")
        results["b5_duplicate_rejected"] = False
    
    return results

# ═════════════════════════════════════════════════════════════════════════════
# TEST GROUP C: POINTS coupon credits reward wallet, NOT cash ledger
# ═════════════════════════════════════════════════════════════════════════════

def test_group_c_points_coupon_wallet(owner_token: str, sp_token: str) -> Dict[str, bool]:
    """Test POINTS coupon credits reward wallet, NOT cash ledger"""
    log_test("\n" + "="*80, "INFO")
    log_test("TEST GROUP C: POINTS Coupon → Reward Wallet (NOT Cash Ledger)", "INFO")
    log_test("="*80, "INFO")
    
    results = {}
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    sp_headers = {"Authorization": f"Bearer {sp_token}"}
    
    # Use timestamp to ensure unique prefix
    unique_suffix = str(int(time.time()))[-4:]
    
    # C0: Setup - Create REWARD batch, activate, assign to distributor via box workflow
    log_test("\n[C0] Setup: Creating REWARD batch...", "INFO")
    batch_payload = {
        "coupon_type": "reward",
        "coupon_value": 180,
        "count": 2,
        "prefix": f"RW{unique_suffix}",
        "serial_start": 1,
        "serial_pad": 3,
        "title": "Reward Test Batch"
    }
    response = requests.post(
        f"{BASE_URL}/dms/coupons/batches",
        headers=owner_headers,
        json=batch_payload
    )
    
    if response.status_code != 200:
        log_test(f"✗ Failed to create REWARD batch: {response.status_code}", "FAIL")
        results["c0_setup"] = False
        return results
    
    reward_batch_id = response.json().get("batch", {}).get("id")
    log_test(f"✓ REWARD batch created: {reward_batch_id}", "PASS")
    
    # Activate batch
    response = requests.post(
        f"{BASE_URL}/dms/coupons/batches/{reward_batch_id}/activate",
        headers=owner_headers
    )
    if response.status_code != 200:
        log_test(f"✗ Failed to activate REWARD batch: {response.status_code}", "FAIL")
        results["c0_setup"] = False
        return results
    log_test(f"✓ REWARD batch activated", "PASS")
    
    # Create box
    response = requests.post(
        f"{BASE_URL}/dms/coupons/boxes",
        headers=owner_headers,
        json={"notes": "Test box for reward coupons"}
    )
    if response.status_code != 200:
        log_test(f"✗ Failed to create box: {response.status_code}", "FAIL")
        results["c0_setup"] = False
        return results
    
    box_id = response.json().get("box", {}).get("id")
    box_number = response.json().get("box", {}).get("box_number")
    log_test(f"✓ Box created: {box_number} (ID: {box_id})", "PASS")
    
    # Assign coupons to box
    first_serial = f"RW{unique_suffix}001"
    last_serial = f"RW{unique_suffix}002"
    response = requests.post(
        f"{BASE_URL}/dms/coupons/boxes/{box_id}/assign-coupons",
        headers=owner_headers,
        json={"batch_id": reward_batch_id, "from_serial": first_serial, "to_serial": last_serial}
    )
    if response.status_code != 200:
        log_test(f"✗ Failed to assign coupons to box: {response.status_code} - {response.text[:200]}", "FAIL")
        results["c0_setup"] = False
        return results
    log_test(f"✓ Coupons assigned to box", "PASS")
    
    # Assign box to distributor
    response = requests.post(
        f"{BASE_URL}/dms/coupons/boxes/{box_id}/assign-distributor",
        headers=owner_headers,
        json={"distributor_id": DISTRIBUTOR_ID}
    )
    if response.status_code != 200:
        log_test(f"✗ Failed to assign box to distributor: {response.status_code} - {response.text[:200]}", "FAIL")
        results["c0_setup"] = False
        return results
    log_test(f"✓ Box assigned to distributor {DISTRIBUTOR_ID}", "PASS")
    
    # Get one coupon code for scanning
    response = requests.get(
        f"{BASE_URL}/dms/coupons?batch_id={reward_batch_id}&limit=1",
        headers=owner_headers
    )
    if response.status_code != 200 or not response.json().get("data"):
        log_test(f"✗ Failed to fetch coupon code: {response.status_code}", "FAIL")
        results["c0_setup"] = False
        return results
    
    coupon_code = response.json()["data"][0].get("visible_serial") or response.json()["data"][0].get("coupon_code")
    log_test(f"✓ Coupon code for scanning: {coupon_code}", "PASS")
    results["c0_setup"] = True
    
    # C1: Get current outstanding (should NOT change after points scan)
    log_test("\n[C1] Getting current outstanding for retailer...", "INFO")
    response = requests.get(
        f"{BASE_URL}/dms/ledger/secondary?retailer_id={RETAILER_ID}",
        headers=owner_headers
    )
    
    if response.status_code == 200:
        data = response.json()
        summary_list = data.get("summary", [])
        retailer_summary = next((s for s in summary_list if s.get("retailer_id") == RETAILER_ID), None)
        
        if retailer_summary:
            outstanding_before = retailer_summary.get("outstanding", 0)
        else:
            outstanding_before = 0
        
        log_test(f"✓ Outstanding before points scan: ₹{outstanding_before}", "PASS")
        results["c1_get_outstanding"] = True
    else:
        log_test(f"✗ Failed to get ledger: {response.status_code}", "FAIL")
        results["c1_get_outstanding"] = False
        return results
    
    # C2: Scan REWARD coupon
    log_test("\n[C2] Scanning REWARD coupon...", "INFO")
    response = requests.post(
        f"{BASE_URL}/dms/coupons/scan",
        headers=sp_headers,
        json={"retailer_id": RETAILER_ID, "coupon_code": coupon_code}
    )
    
    if response.status_code == 200:
        data = response.json()
        wallet_type = data.get("wallet_type")
        new_balance = data.get("new_balance")
        
        if wallet_type == "reward":
            log_test(f"✓ Scan successful: wallet_type=reward, new_balance={new_balance} points", "PASS")
            results["c2_scan_reward"] = True
        else:
            log_test(f"✗ Wrong wallet_type: {wallet_type} (expected 'reward')", "FAIL")
            results["c2_scan_reward"] = False
    else:
        log_test(f"✗ Scan failed: {response.status_code} - {response.text[:200]}", "FAIL")
        results["c2_scan_reward"] = False
    
    # C3: Verify outstanding did NOT change
    log_test("\n[C3] Verifying outstanding did NOT change...", "INFO")
    response = requests.get(
        f"{BASE_URL}/dms/ledger/secondary?retailer_id={RETAILER_ID}",
        headers=owner_headers
    )
    
    if response.status_code == 200:
        data = response.json()
        summary_list = data.get("summary", [])
        retailer_summary = next((s for s in summary_list if s.get("retailer_id") == RETAILER_ID), None)
        
        if retailer_summary:
            outstanding_after = retailer_summary.get("outstanding", 0)
        else:
            outstanding_after = 0
        
        if abs(outstanding_after - outstanding_before) < 0.01:
            log_test(f"✓ Outstanding unchanged: ₹{outstanding_after} (CORRECT - points don't affect cash ledger)", "PASS")
            results["c3_outstanding_unchanged"] = True
        else:
            log_test(f"✗ Outstanding changed: ₹{outstanding_before} → ₹{outstanding_after} (WRONG - points should NOT affect cash ledger)", "FAIL")
            results["c3_outstanding_unchanged"] = False
    else:
        log_test(f"✗ Failed to get ledger: {response.status_code}", "FAIL")
        results["c3_outstanding_unchanged"] = False
    
    return results

# ═════════════════════════════════════════════════════════════════════════════
# MAIN TEST RUNNER
# ═════════════════════════════════════════════════════════════════════════════

def main():
    """Main test runner"""
    print("\n" + "="*80)
    print("GO OIL DMS - COUPON FEATURES BACKEND TESTING")
    print("Testing coupon PDF endpoints + Sales Person cash/points coupon flows")
    print("="*80 + "\n")
    
    # Login as owner
    owner_token = login(OWNER_EMAIL, OWNER_PASSWORD)
    if not owner_token:
        log_test("Cannot proceed without owner authentication", "FAIL")
        return
    
    # Login as salesperson
    sp_token = login(SALESPERSON_EMAIL, SALESPERSON_PASSWORD)
    if not sp_token:
        log_test("Cannot proceed without salesperson authentication", "FAIL")
        return
    
    # Run test groups
    results_a = test_group_a_pdf_endpoints(owner_token)
    results_b = test_group_b_cash_coupon_ledger(owner_token, sp_token)
    results_c = test_group_c_points_coupon_wallet(owner_token, sp_token)
    
    # Combine all results
    all_results = {**results_a, **results_b, **results_c}
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    # Group A
    log_test("\nGROUP A: Coupon Sheet PDF Endpoints", "INFO")
    for key, passed in results_a.items():
        status = "PASS" if passed else "FAIL"
        log_test(f"  {key}: {status}", status)
    
    # Group B
    log_test("\nGROUP B: Sales Person CASH Coupon → Retailer Outstanding", "INFO")
    for key, passed in results_b.items():
        status = "PASS" if passed else "FAIL"
        log_test(f"  {key}: {status}", status)
    
    # Group C
    log_test("\nGROUP C: POINTS Coupon → Reward Wallet (NOT Cash Ledger)", "INFO")
    for key, passed in results_c.items():
        status = "PASS" if passed else "FAIL"
        log_test(f"  {key}: {status}", status)
    
    # Overall
    passed = sum(1 for result in all_results.values() if result)
    total = len(all_results)
    
    print("\n" + "="*80)
    log_test(f"TOTAL: {passed}/{total} tests passed ({passed*100//total if total else 0}%)", 
             "PASS" if passed == total else "WARN")
    print("="*80 + "\n")
    
    if passed == total:
        log_test("✅ ALL TESTS PASSED - Coupon features verified!", "PASS")
    else:
        log_test(f"⚠️  {total - passed} test(s) failed", "WARN")

if __name__ == "__main__":
    main()
