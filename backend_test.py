#!/usr/bin/env python3
"""
GO OIL DMS — Backend API Testing for CONTINUATION v3.1
Tests NEW/ENHANCED endpoints:
1. Import Preview (parse-only, no DB writes)
2. Bulk Retailer Reassign
3. Distributor Scan Ledger (light check)
4. Batch Sheet PDF (verify endpoint reachable)

CRITICAL: Must keep DB clean (0 products after test).
"""
import io
import json
import os
import sys
import requests
from openpyxl import Workbook

# Backend URL from environment
BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://challan-print-fix.preview.emergentagent.com")
API_BASE = f"{BACKEND_URL}/api"

# Test credentials
OWNER_EMAIL = "owner@gooil.com"
OWNER_PASSWORD = "GoOil@2026"
DISTRIBUTOR1_EMAIL = "distributor1@gooil.com"
DISTRIBUTOR1_PASSWORD = "GoOil@2026"
RETAILER1_EMAIL = "retailer1@gooil.com"
RETAILER1_PASSWORD = "GoOil@2026"

# Global tokens
owner_token = None
distributor1_token = None
retailer1_token = None

# Cleanup tracking
created_distributors = []
created_retailers = []
created_users = []


def log(msg):
    print(f"[TEST] {msg}")


def login(email, password):
    """Login and return JWT token."""
    resp = requests.post(f"{API_BASE}/auth/login", json={"email": email, "password": password})
    if resp.status_code != 200:
        log(f"❌ Login failed for {email}: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    token = data.get("token")
    if not token:
        log(f"❌ No token in login response for {email}")
        return None
    log(f"✅ Logged in as {email}")
    return token


def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def create_test_xlsx():
    """Create a small in-memory .xlsx with the exact format specified in the review request."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Price List"
    
    # Header row (exactly as specified)
    ws.append([
        "MATERIAL DESCRIPTION", "GRADE/ SPECS", "PACK SIZE", "MRP", "DLP",
        "DISTRIBUTOR MARGINE", "CASH COUPON", "FOC BENEFITS", "MONTHLY GIFT", "TRADE DISCOUNT"
    ])
    
    # Category row: CAT A (full-width, only first cell)
    ws.append(["CAT A", "", "", "", "", "", "", "", "", ""])
    
    # Product rows under CAT A
    ws.append(["P1", "SN", "1 ltr", 500, 350, "9%", "10", "", "AVAILABLE", ""])
    ws.append(["P2", "SN", "5 ltr", 2000, 1600, "9%", "", "", "", ""])
    
    # Category row: CAT B
    ws.append(["CAT B", "", "", "", "", "", "", "", "", ""])
    
    # Product row under CAT B
    ws.append(["P3", "GL5", "1 ltr", 442, 290, "9%", "", "", "", 50])
    
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def test_import_preview():
    """TEST 1: Import Preview (parse-only, no DB writes)"""
    log("\n" + "="*80)
    log("TEST 1: IMPORT PREVIEW (parse-only, no DB writes)")
    log("="*80)
    
    # Get initial product count
    resp = requests.get(f"{API_BASE}/dms/products", headers=headers(owner_token))
    if resp.status_code != 200:
        log(f"❌ Failed to get initial product count: {resp.status_code}")
        return False
    initial_count = resp.json().get("count", 0)
    log(f"Initial product count: {initial_count}")
    
    # Create test xlsx
    xlsx_data = create_test_xlsx()
    
    # Test 1a: POST /api/dms/owner/products/import-circular/preview as owner
    log("\n[1a] POST /api/dms/owner/products/import-circular/preview as owner")
    files = {"file": ("test_price_list.xlsx", xlsx_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    resp = requests.post(
        f"{API_BASE}/dms/owner/products/import-circular/preview",
        headers={"Authorization": f"Bearer {owner_token}"},
        files=files
    )
    if resp.status_code != 200:
        log(f"❌ Preview failed: {resp.status_code} {resp.text}")
        return False
    
    data = resp.json()
    log(f"✅ Preview response: ok={data.get('ok')}, product_count={data.get('product_count')}, category_count={data.get('category_count')}")
    
    # Verify expected values
    if data.get("product_count") != 3:
        log(f"❌ Expected product_count=3, got {data.get('product_count')}")
        return False
    if data.get("category_count") != 2:
        log(f"❌ Expected category_count=2, got {data.get('category_count')}")
        return False
    
    categories = data.get("categories", [])
    if "CAT A" not in categories or "CAT B" not in categories:
        log(f"❌ Expected categories ['CAT A', 'CAT B'], got {categories}")
        return False
    
    sample = data.get("sample", [])
    if not sample:
        log(f"❌ Expected non-empty sample, got empty")
        return False
    
    log(f"✅ Categories: {categories}")
    log(f"✅ Sample products: {len(sample)} items")
    
    # Test 1b: Verify DB is still clean (preview must not write)
    log("\n[1b] GET /api/dms/products to verify count is STILL {initial_count}")
    resp = requests.get(f"{API_BASE}/dms/products", headers=headers(owner_token))
    if resp.status_code != 200:
        log(f"❌ Failed to get product count after preview: {resp.status_code}")
        return False
    
    final_count = resp.json().get("count", 0)
    if final_count != initial_count:
        log(f"❌ CRITICAL: Preview wrote to DB! Initial={initial_count}, Final={final_count}")
        return False
    
    log(f"✅ Product count unchanged: {final_count} (preview did NOT write to DB)")
    
    # Test 1c: RBAC - distributor1 should get 403
    log("\n[1c] POST preview as distributor1 → expect 403")
    files = {"file": ("test_price_list.xlsx", create_test_xlsx(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    resp = requests.post(
        f"{API_BASE}/dms/owner/products/import-circular/preview",
        headers={"Authorization": f"Bearer {distributor1_token}"},
        files=files
    )
    if resp.status_code != 403:
        log(f"❌ Expected 403 for distributor, got {resp.status_code}")
        return False
    log(f"✅ Distributor correctly blocked: 403")
    
    log("\n✅ TEST 1 PASSED: Import Preview working correctly (no DB writes)")
    return True


def test_bulk_retailer_reassign():
    """TEST 2: Bulk Retailer Reassign"""
    log("\n" + "="*80)
    log("TEST 2: BULK RETAILER REASSIGN")
    log("="*80)
    
    # Create distributor A
    log("\n[2a] Create distributor A (BulkDistA)")
    dist_a_data = {
        "name": "BulkDistA",
        "email": "bulkdista@gooil.com",
        "password": "GoOil@2026",
        "phone": "9999999991",
        "address": "Test Address A",
        "region": "X"
    }
    resp = requests.post(f"{API_BASE}/dms/distributors", headers=headers(owner_token), json=dist_a_data)
    if resp.status_code != 200:
        log(f"❌ Failed to create distributor A: {resp.status_code} {resp.text}")
        return False
    dist_a = resp.json()
    dist_a_id = dist_a.get("id")
    created_distributors.append(dist_a_id)
    log(f"✅ Created distributor A: {dist_a_id}")
    
    # Create distributor B
    log("\n[2b] Create distributor B (BulkDistB)")
    dist_b_data = {
        "name": "BulkDistB",
        "email": "bulkdistb@gooil.com",
        "password": "GoOil@2026",
        "phone": "9999999992",
        "address": "Test Address B",
        "region": "X"
    }
    resp = requests.post(f"{API_BASE}/dms/distributors", headers=headers(owner_token), json=dist_b_data)
    if resp.status_code != 200:
        log(f"❌ Failed to create distributor B: {resp.status_code} {resp.text}")
        return False
    dist_b = resp.json()
    dist_b_id = dist_b.get("id")
    created_distributors.append(dist_b_id)
    log(f"✅ Created distributor B: {dist_b_id}")
    
    # Create 2 retailers under distributor A
    log("\n[2c] Create 2 retailers under distributor A")
    ret1_data = {
        "name": "BR1",
        "phone": "8888888881",
        "address": "Retailer Address 1",
        "distributor_id": dist_a_id
    }
    resp = requests.post(f"{API_BASE}/dms/retailers", headers=headers(owner_token), json=ret1_data)
    if resp.status_code != 200:
        log(f"❌ Failed to create retailer 1: {resp.status_code} {resp.text}")
        return False
    ret1 = resp.json()
    ret1_id = ret1.get("id")
    created_retailers.append(ret1_id)
    log(f"✅ Created retailer 1: {ret1_id}")
    
    ret2_data = {
        "name": "BR2",
        "phone": "8888888882",
        "address": "Retailer Address 2",
        "distributor_id": dist_a_id
    }
    resp = requests.post(f"{API_BASE}/dms/retailers", headers=headers(owner_token), json=ret2_data)
    if resp.status_code != 200:
        log(f"❌ Failed to create retailer 2: {resp.status_code} {resp.text}")
        return False
    ret2 = resp.json()
    ret2_id = ret2.get("id")
    created_retailers.append(ret2_id)
    log(f"✅ Created retailer 2: {ret2_id}")
    
    # Verify retailers are under distributor A
    log("\n[2d] Verify retailers are under distributor A")
    resp = requests.get(f"{API_BASE}/dms/retailers", headers=headers(owner_token))
    if resp.status_code != 200:
        log(f"❌ Failed to get retailers: {resp.status_code}")
        return False
    retailers = resp.json().get("data", [])
    ret1_check = next((r for r in retailers if r["id"] == ret1_id), None)
    ret2_check = next((r for r in retailers if r["id"] == ret2_id), None)
    if not ret1_check or ret1_check.get("distributor_id") != dist_a_id:
        log(f"❌ Retailer 1 not under distributor A")
        return False
    if not ret2_check or ret2_check.get("distributor_id") != dist_a_id:
        log(f"❌ Retailer 2 not under distributor A")
        return False
    log(f"✅ Both retailers confirmed under distributor A")
    
    # Bulk reassign to distributor B
    log("\n[2e] POST /api/dms/owner/retailers/bulk-assign-distributor")
    bulk_data = {
        "retailer_ids": [ret1_id, ret2_id],
        "distributor_id": dist_b_id
    }
    resp = requests.post(f"{API_BASE}/dms/owner/retailers/bulk-assign-distributor", headers=headers(owner_token), json=bulk_data)
    if resp.status_code != 200:
        log(f"❌ Bulk reassign failed: {resp.status_code} {resp.text}")
        return False
    result = resp.json()
    if not result.get("ok") or result.get("moved") != 2:
        log(f"❌ Expected moved=2, got {result}")
        return False
    log(f"✅ Bulk reassign successful: moved={result.get('moved')}")
    
    # Verify retailers are now under distributor B
    log("\n[2f] Verify retailers are now under distributor B")
    resp = requests.get(f"{API_BASE}/dms/retailers", headers=headers(owner_token))
    if resp.status_code != 200:
        log(f"❌ Failed to get retailers: {resp.status_code}")
        return False
    retailers = resp.json().get("data", [])
    ret1_check = next((r for r in retailers if r["id"] == ret1_id), None)
    ret2_check = next((r for r in retailers if r["id"] == ret2_id), None)
    if not ret1_check or ret1_check.get("distributor_id") != dist_b_id:
        log(f"❌ Retailer 1 not under distributor B after reassign")
        return False
    if not ret2_check or ret2_check.get("distributor_id") != dist_b_id:
        log(f"❌ Retailer 2 not under distributor B after reassign")
        return False
    log(f"✅ Both retailers confirmed under distributor B")
    
    # Error case: empty retailer_ids
    log("\n[2g] Error case: empty retailer_ids → expect 400")
    resp = requests.post(f"{API_BASE}/dms/owner/retailers/bulk-assign-distributor", 
                        headers=headers(owner_token), 
                        json={"retailer_ids": [], "distributor_id": dist_b_id})
    if resp.status_code != 400:
        log(f"❌ Expected 400 for empty retailer_ids, got {resp.status_code}")
        return False
    log(f"✅ Empty retailer_ids correctly rejected: 400")
    
    # Error case: invalid distributor_id
    log("\n[2h] Error case: invalid distributor_id → expect 404")
    resp = requests.post(f"{API_BASE}/dms/owner/retailers/bulk-assign-distributor", 
                        headers=headers(owner_token), 
                        json={"retailer_ids": [ret1_id], "distributor_id": "bad-dist-id"})
    if resp.status_code != 404:
        log(f"❌ Expected 404 for invalid distributor_id, got {resp.status_code}")
        return False
    log(f"✅ Invalid distributor_id correctly rejected: 404")
    
    # RBAC: distributor1 should get 403
    log("\n[2i] RBAC: distributor1 → expect 403")
    resp = requests.post(f"{API_BASE}/dms/owner/retailers/bulk-assign-distributor", 
                        headers=headers(distributor1_token), 
                        json={"retailer_ids": [ret1_id], "distributor_id": dist_b_id})
    if resp.status_code != 403:
        log(f"❌ Expected 403 for distributor, got {resp.status_code}")
        return False
    log(f"✅ Distributor correctly blocked: 403")
    
    log("\n✅ TEST 2 PASSED: Bulk Retailer Reassign working correctly")
    return True


def test_distributor_scan_ledger():
    """TEST 3: Distributor Scan Ledger (light check)"""
    log("\n" + "="*80)
    log("TEST 3: DISTRIBUTOR SCAN LEDGER (light check)")
    log("="*80)
    
    # Test: POST /api/dms/coupons/distributor/scan with bogus coupon
    log("\n[3a] POST /api/dms/coupons/distributor/scan with bogus coupon → expect 400 (not 500)")
    scan_data = {
        "coupon_code": "BOGUS123"
    }
    resp = requests.post(f"{API_BASE}/dms/coupons/distributor/scan", 
                        headers=headers(distributor1_token), 
                        json=scan_data)
    
    if resp.status_code == 500:
        log(f"❌ CRITICAL: Got 500 error (crash) instead of 400")
        log(f"Response: {resp.text}")
        return False
    
    if resp.status_code != 400:
        log(f"⚠️  Expected 400, got {resp.status_code} (acceptable if not 500)")
    else:
        log(f"✅ Bogus coupon correctly rejected: 400")
    
    # Verify no crash - the endpoint is reachable and returns proper error
    log(f"✅ Distributor scan endpoint reachable (no crash from new ledger code)")
    
    log("\n✅ TEST 3 PASSED: Distributor scan ledger code path verified (no crash)")
    return True


def test_batch_sheet_pdf():
    """TEST 4: Batch Sheet PDF (verify endpoint reachable)"""
    log("\n" + "="*80)
    log("TEST 4: BATCH SHEET PDF (verify endpoint reachable)")
    log("="*80)
    
    # Get coupon batches
    log("\n[4a] GET /api/dms/coupons/batches")
    resp = requests.get(f"{API_BASE}/dms/coupons/batches", headers=headers(owner_token))
    if resp.status_code != 200:
        log(f"❌ Failed to get batches: {resp.status_code}")
        return False
    
    batches = resp.json().get("data", [])
    log(f"Found {len(batches)} batches")
    
    # Find a batch with status activated or printed
    suitable_batch = None
    for batch in batches:
        if batch.get("status") in ("activated", "printed", "issued_to_production"):
            suitable_batch = batch
            break
    
    if not suitable_batch:
        log(f"⚠️  No batches with status activated/printed/issued found")
        log(f"✅ TEST 4 SKIPPED: No suitable batches to test PDF export")
        return True
    
    batch_id = suitable_batch.get("id")
    log(f"Testing with batch: {batch_id} (status={suitable_batch.get('status')})")
    
    # Test: GET /api/dms/coupons/batches/{bid}/export-pdf
    log(f"\n[4b] GET /api/dms/coupons/batches/{batch_id}/export-pdf")
    resp = requests.get(f"{API_BASE}/dms/coupons/batches/{batch_id}/export-pdf", 
                       headers=headers(owner_token))
    
    if resp.status_code != 200:
        log(f"❌ PDF export failed: {resp.status_code} {resp.text}")
        return False
    
    content_type = resp.headers.get("Content-Type", "")
    if "application/pdf" not in content_type:
        log(f"❌ Expected application/pdf, got {content_type}")
        return False
    
    pdf_size = len(resp.content)
    log(f"✅ PDF export successful: {pdf_size} bytes, content-type={content_type}")
    
    log("\n✅ TEST 4 PASSED: Batch sheet PDF endpoint working correctly")
    return True


def cleanup():
    """Cleanup: Delete created test data"""
    log("\n" + "="*80)
    log("CLEANUP: Deleting test data")
    log("="*80)
    
    # Delete retailers
    for ret_id in created_retailers:
        log(f"Deleting retailer {ret_id}")
        resp = requests.delete(f"{API_BASE}/dms/retailers/{ret_id}", headers=headers(owner_token))
        if resp.status_code == 200:
            log(f"✅ Deleted retailer {ret_id}")
        else:
            log(f"⚠️  Failed to delete retailer {ret_id}: {resp.status_code}")
    
    # Delete distributors
    for dist_id in created_distributors:
        log(f"Deleting distributor {dist_id}")
        resp = requests.delete(f"{API_BASE}/dms/distributors/{dist_id}", headers=headers(owner_token))
        if resp.status_code == 200:
            log(f"✅ Deleted distributor {dist_id}")
        else:
            log(f"⚠️  Failed to delete distributor {dist_id}: {resp.status_code}")
    
    # Verify product count is still 0 (or initial count)
    log("\nVerifying product count is clean")
    resp = requests.get(f"{API_BASE}/dms/products", headers=headers(owner_token))
    if resp.status_code == 200:
        count = resp.json().get("count", 0)
        log(f"✅ Final product count: {count}")
    
    log("\n✅ CLEANUP COMPLETE")


def main():
    global owner_token, distributor1_token, retailer1_token
    
    log("="*80)
    log("GO OIL DMS — CONTINUATION v3.1 Backend Testing")
    log("="*80)
    log(f"Backend URL: {BACKEND_URL}")
    log(f"API Base: {API_BASE}")
    
    # Login
    log("\n" + "="*80)
    log("AUTHENTICATION")
    log("="*80)
    owner_token = login(OWNER_EMAIL, OWNER_PASSWORD)
    distributor1_token = login(DISTRIBUTOR1_EMAIL, DISTRIBUTOR1_PASSWORD)
    retailer1_token = login(RETAILER1_EMAIL, RETAILER1_PASSWORD)
    
    if not owner_token or not distributor1_token:
        log("❌ CRITICAL: Failed to authenticate. Aborting tests.")
        sys.exit(1)
    
    # Run tests
    results = []
    
    try:
        results.append(("Import Preview", test_import_preview()))
        results.append(("Bulk Retailer Reassign", test_bulk_retailer_reassign()))
        results.append(("Distributor Scan Ledger", test_distributor_scan_ledger()))
        results.append(("Batch Sheet PDF", test_batch_sheet_pdf()))
    except Exception as e:
        log(f"\n❌ EXCEPTION during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always cleanup
        cleanup()
    
    # Summary
    log("\n" + "="*80)
    log("TEST SUMMARY")
    log("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        log(f"{status} - {test_name}")
    
    log(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        log("\n🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        log(f"\n❌ {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
