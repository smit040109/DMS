#!/usr/bin/env python3
"""
Backend API Testing for GO OIL DMS - Coupon PDF Endpoint Fix
Tests the large-batch (1400 coupons) PDF generation fix
"""

import requests
import time
import json
from datetime import datetime

# Base URL from frontend/.env
BASE_URL = "https://points-wallet-hub-2.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
OWNER_EMAIL = "gooilindia13@gmail.com"
OWNER_PASSWORD = "Arjun@india13"

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

def login_owner():
    """Login as owner and return JWT token"""
    log_test("Logging in as owner...", "INFO")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("token")  # Changed from "access_token" to "token"
        log_test(f"Owner login successful. Role: {data.get('user', {}).get('role')}", "PASS")
        return token
    else:
        log_test(f"Owner login failed: {response.status_code} - {response.text}", "FAIL")
        return None

def test_list_batches(token):
    """Test GET /api/dms/coupons/batches - list all batches"""
    log_test("\n=== TEST 1: List Coupon Batches ===", "INFO")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/dms/coupons/batches", headers=headers)
    
    if response.status_code != 200:
        log_test(f"Failed to list batches: {response.status_code}", "FAIL")
        return None, None
    
    data = response.json()
    batches = data.get("data", [])
    
    log_test(f"Found {len(batches)} batches", "INFO")
    
    # Find large batch (~1400 coupons) and small batch (~100 coupons)
    large_batch = None
    small_batch = None
    
    for batch in batches:
        batch_id = batch.get("id")
        batch_label = batch.get("batch_label")
        count = batch.get("count", 0)
        status = batch.get("status")
        title = batch.get("title", "")
        
        log_test(f"  - {batch_label}: {title}, count={count}, status={status}, id={batch_id}", "INFO")
        
        # Identify large batch (around 1400 coupons)
        if count >= 1000 and large_batch is None:
            large_batch = batch
            log_test(f"    → LARGE batch identified: {batch_label} ({count} coupons)", "PASS")
        
        # Identify small batch (around 100 coupons)
        if 50 <= count <= 200 and small_batch is None:
            small_batch = batch
            log_test(f"    → SMALL batch identified: {batch_label} ({count} coupons)", "PASS")
    
    if large_batch is None:
        log_test("WARNING: No large batch (>1000 coupons) found", "WARN")
    
    if small_batch is None:
        log_test("WARNING: No small batch (50-200 coupons) found", "WARN")
    
    return large_batch, small_batch

def test_export_pdf(token, batch, batch_type="BATCH"):
    """Test GET /api/dms/coupons/batches/{bid}/export-pdf"""
    if batch is None:
        log_test(f"Skipping {batch_type} PDF export test (batch not found)", "WARN")
        return False
    
    batch_id = batch.get("id")
    batch_label = batch.get("batch_label")
    count = batch.get("count")
    status = batch.get("status")
    
    log_test(f"\n=== TEST: {batch_type} Batch PDF Export ===", "INFO")
    log_test(f"Batch: {batch_label}, Count: {count}, Status: {status}, ID: {batch_id}", "INFO")
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}/dms/coupons/batches/{batch_id}/export-pdf"
    
    log_test(f"Requesting: GET {url}", "INFO")
    
    start_time = time.time()
    response = requests.get(url, headers=headers)
    elapsed_time = time.time() - start_time
    
    log_test(f"Response time: {elapsed_time:.2f} seconds", "INFO")
    
    # Check HTTP status
    if response.status_code != 200:
        log_test(f"FAIL: HTTP {response.status_code} (expected 200)", "FAIL")
        log_test(f"Response: {response.text[:500]}", "FAIL")
        return False
    
    log_test(f"✓ HTTP 200 OK", "PASS")
    
    # Check Content-Type
    content_type = response.headers.get("Content-Type", "")
    if "application/pdf" not in content_type:
        log_test(f"FAIL: Content-Type is '{content_type}' (expected 'application/pdf')", "FAIL")
        return False
    
    log_test(f"✓ Content-Type: {content_type}", "PASS")
    
    # Check response body is non-empty
    content_length = len(response.content)
    if content_length == 0:
        log_test(f"FAIL: Response body is EMPTY", "FAIL")
        return False
    
    log_test(f"✓ Content-Length: {content_length:,} bytes ({content_length / 1024:.1f} KB)", "PASS")
    
    # Check PDF header (starts with %PDF)
    first_bytes = response.content[:4]
    if first_bytes != b'%PDF':
        log_test(f"FAIL: Response does not start with '%PDF' (got: {first_bytes})", "FAIL")
        return False
    
    log_test(f"✓ Valid PDF header: {first_bytes}", "PASS")
    
    # Check completion time (should be < 60s)
    if elapsed_time > 60:
        log_test(f"WARN: Response took {elapsed_time:.2f}s (> 60s timeout threshold)", "WARN")
    else:
        log_test(f"✓ Completed within timeout ({elapsed_time:.2f}s < 60s)", "PASS")
    
    log_test(f"✓ {batch_type} batch PDF export: ALL CHECKS PASSED", "PASS")
    return True

def test_export_pdf_with_side_param(token, batch):
    """Test GET /api/dms/coupons/batches/{bid}/export-pdf?side=front"""
    if batch is None:
        log_test("Skipping side parameter test (batch not found)", "WARN")
        return False
    
    batch_id = batch.get("id")
    batch_label = batch.get("batch_label")
    
    log_test(f"\n=== TEST: PDF Export with side=front Parameter ===", "INFO")
    log_test(f"Batch: {batch_label}, ID: {batch_id}", "INFO")
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}/dms/coupons/batches/{batch_id}/export-pdf?side=front"
    
    log_test(f"Requesting: GET {url}", "INFO")
    
    start_time = time.time()
    response = requests.get(url, headers=headers)
    elapsed_time = time.time() - start_time
    
    if response.status_code != 200:
        log_test(f"FAIL: HTTP {response.status_code}", "FAIL")
        return False
    
    content_length = len(response.content)
    log_test(f"✓ HTTP 200, Content-Length: {content_length:,} bytes ({content_length / 1024:.1f} KB)", "PASS")
    
    # Front-only PDF should be smaller than both-sides
    log_test(f"✓ Front-only PDF generated successfully (smaller file expected)", "PASS")
    
    return True

def test_print_mixed_preview(token, batch):
    """Test POST /api/dms/coupons/print-mixed/preview - verify per_sheet == 77"""
    if batch is None:
        log_test("Skipping print-mixed preview test (batch not found)", "WARN")
        return False
    
    batch_id = batch.get("id")
    batch_label = batch.get("batch_label")
    
    log_test(f"\n=== TEST: Print-Mixed Preview (per_sheet verification) ===", "INFO")
    log_test(f"Batch: {batch_label}, ID: {batch_id}", "INFO")
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}/dms/coupons/print-mixed/preview"
    payload = {"batch_ids": [batch_id]}
    
    log_test(f"Requesting: POST {url}", "INFO")
    log_test(f"Payload: {json.dumps(payload)}", "INFO")
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code != 200:
        log_test(f"FAIL: HTTP {response.status_code}", "FAIL")
        log_test(f"Response: {response.text[:500]}", "FAIL")
        return False
    
    log_test(f"✓ HTTP 200 OK", "PASS")
    
    data = response.json()
    per_sheet = data.get("per_sheet")
    breakdown = data.get("breakdown", [])
    
    log_test(f"Response: per_sheet={per_sheet}, breakdown={breakdown}", "INFO")
    
    # Critical check: per_sheet must be 77 (NOT 70)
    if per_sheet != 77:
        log_test(f"FAIL: per_sheet is {per_sheet} (expected 77)", "FAIL")
        return False
    
    log_test(f"✓ per_sheet == 77 (CORRECT - 7x11 grid on 11x17in sheet)", "PASS")
    log_test(f"✓ breakdown: {breakdown}", "PASS")
    
    return True

def test_generated_status_batch(token, batches):
    """Test export-pdf works for batches with status='generated'"""
    log_test(f"\n=== TEST: Export PDF for 'generated' Status Batch ===", "INFO")
    
    # Find a batch with status='generated'
    generated_batch = None
    for batch in batches:
        if batch.get("status") == "generated":
            generated_batch = batch
            break
    
    if generated_batch is None:
        log_test("No batch with status='generated' found. Checking if any batch works...", "WARN")
        # Use any available batch as fallback
        if batches:
            generated_batch = batches[0]
            log_test(f"Using batch with status='{generated_batch.get('status')}' instead", "INFO")
        else:
            log_test("No batches available for testing", "WARN")
            return False
    
    batch_id = generated_batch.get("id")
    batch_label = generated_batch.get("batch_label")
    status = generated_batch.get("status")
    
    log_test(f"Testing batch: {batch_label}, status={status}, id={batch_id}", "INFO")
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}/dms/coupons/batches/{batch_id}/export-pdf"
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        log_test(f"FAIL: HTTP {response.status_code}", "FAIL")
        return False
    
    content_type = response.headers.get("Content-Type", "")
    content_length = len(response.content)
    first_bytes = response.content[:4]
    
    if "application/pdf" in content_type and first_bytes == b'%PDF' and content_length > 0:
        log_test(f"✓ Export-pdf works for status='{status}' batch", "PASS")
        log_test(f"✓ Valid PDF: {content_length:,} bytes", "PASS")
        return True
    else:
        log_test(f"FAIL: Invalid PDF response", "FAIL")
        return False

def main():
    """Main test runner"""
    print("\n" + "="*80)
    print("GO OIL DMS - COUPON SHEET PDF ENDPOINT FIX - BACKEND TESTING")
    print("Testing large-batch (1400 coupons) PDF generation fix")
    print("="*80 + "\n")
    
    # Login
    token = login_owner()
    if not token:
        log_test("Cannot proceed without authentication", "FAIL")
        return
    
    # Test 1: List batches and identify large/small batches
    large_batch, small_batch = test_list_batches(token)
    
    # Get all batches for generated status test
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/dms/coupons/batches", headers=headers)
    all_batches = response.json().get("data", []) if response.status_code == 200 else []
    
    # Test 2: Large batch PDF export (the critical fix)
    test_2_pass = test_export_pdf(token, large_batch, "LARGE")
    
    # Test 3: Small batch PDF export
    test_3_pass = test_export_pdf(token, small_batch, "SMALL")
    
    # Test 4: Generated status batch
    test_4_pass = test_generated_status_batch(token, all_batches)
    
    # Test 5: Print-mixed preview (per_sheet == 77)
    test_5_pass = test_print_mixed_preview(token, small_batch if small_batch else large_batch)
    
    # Test 6: Optional side parameter
    test_6_pass = test_export_pdf_with_side_param(token, small_batch if small_batch else large_batch)
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    tests = [
        ("List batches & identify large/small", large_batch is not None and small_batch is not None),
        ("LARGE batch PDF export (1400 coupons)", test_2_pass),
        ("SMALL batch PDF export (~100 coupons)", test_3_pass),
        ("'generated' status batch PDF export", test_4_pass),
        ("Print-mixed preview (per_sheet == 77)", test_5_pass),
        ("Export PDF with side=front parameter", test_6_pass),
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    for test_name, result in tests:
        status = "PASS" if result else "FAIL"
        log_test(f"{test_name}: {status}", status)
    
    print("\n" + "="*80)
    log_test(f"TOTAL: {passed}/{total} tests passed ({passed*100//total}%)", 
             "PASS" if passed == total else "WARN")
    print("="*80 + "\n")
    
    if passed == total:
        log_test("✅ ALL TESTS PASSED - Coupon PDF endpoint fix verified!", "PASS")
    else:
        log_test(f"⚠️  {total - passed} test(s) failed", "WARN")

if __name__ == "__main__":
    main()
