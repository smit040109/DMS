#!/usr/bin/env python3
"""
Backend Test Suite for NEW Coupon Printing + Share Link Endpoints
Tests ONLY the new PDF export and share-link features.
"""

import requests
import json
import sys
from datetime import datetime, timedelta

# Public URL from frontend/.env
BASE_URL = "https://transport-bill-3.preview.emergentagent.com/api"

# Test credentials
OWNER_EMAIL = "owner@gooil.com"
OWNER_PASSWORD = "GoOil@2026"
DISTRIBUTOR_EMAIL = "distributor1@gooil.com"
DISTRIBUTOR_PASSWORD = "GoOil@2026"

def log(msg):
    """Print with timestamp"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def login(email, password):
    """Login and return JWT token"""
    log(f"Logging in as {email}...")
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": password
    })
    if resp.status_code != 200:
        log(f"❌ Login failed: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    token = data.get("token") or data.get("access_token")
    if not token:
        log(f"❌ Login failed: No token in response")
        return None
    log(f"✅ Login successful, token: {token[:20]}...")
    return token

def get_or_create_batch(token):
    """Get existing batch or create one for testing"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try to get existing batches
    log("Fetching existing coupon batches...")
    resp = requests.get(f"{BASE_URL}/dms/coupons/batches", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        batches = data.get("data", [])
        if batches:
            batch_id = batches[0]["id"]
            log(f"✅ Using existing batch: {batch_id}")
            return batch_id
    
    # Create new batch
    log("No existing batches found, creating new batch...")
    payload = {
        "title": "PrintQA",
        "coupon_type": "cash",
        "coupon_value": 20,
        "count": 100,
        "serial_mode": "prefix_sequential",
        "prefix": "PQA",
        "serial_start": 1,
        "serial_pad": 3
    }
    resp = requests.post(f"{BASE_URL}/dms/coupons/batches", json=payload, headers=headers)
    if resp.status_code != 200:
        log(f"❌ Failed to create batch: {resp.status_code} {resp.text}")
        return None
    
    batch_id = resp.json().get("id")
    log(f"✅ Created new batch: {batch_id}")
    return batch_id

def test_pdf_export_default_diameter(token, batch_id):
    """TEST 1 — PDF export with default diameter (34mm)"""
    log("\n=== TEST 1: PDF export with default diameter (34mm) ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.get(f"{BASE_URL}/dms/coupons/batches/{batch_id}/export-pdf", headers=headers)
    
    # Check status
    if resp.status_code != 200:
        log(f"❌ FAILED: Expected 200, got {resp.status_code}")
        log(f"   Response: {resp.text[:200]}")
        return False
    
    # Check Content-Type
    content_type = resp.headers.get("Content-Type", "")
    if "application/pdf" not in content_type:
        log(f"❌ FAILED: Expected Content-Type: application/pdf, got {content_type}")
        return False
    
    # Check Content-Disposition filename
    content_disp = resp.headers.get("Content-Disposition", "")
    if "_34mm.pdf" not in content_disp:
        log(f"❌ FAILED: Expected filename with _34mm.pdf, got {content_disp}")
        return False
    
    # Check PDF header
    pdf_header = resp.content[:8]
    if pdf_header != b'%PDF-1.4':
        log(f"❌ FAILED: Expected PDF header %PDF-1.4, got {pdf_header}")
        return False
    
    # Check size
    size = len(resp.content)
    if size < 500 * 1024:  # 500 KB
        log(f"❌ FAILED: Expected size > 500 KB, got {size / 1024:.1f} KB")
        return False
    
    log(f"✅ PASSED: Status=200, Content-Type=application/pdf, filename contains _34mm.pdf")
    log(f"   PDF header: {pdf_header}, Size: {size / 1024:.1f} KB")
    return True

def test_pdf_export_custom_diameter(token, batch_id):
    """TEST 2 — PDF export with custom diameter (50mm)"""
    log("\n=== TEST 2: PDF export with custom diameter (50mm) ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.get(f"{BASE_URL}/dms/coupons/batches/{batch_id}/export-pdf?diameter_mm=50", headers=headers)
    
    if resp.status_code != 200:
        log(f"❌ FAILED: Expected 200, got {resp.status_code}")
        return False
    
    content_disp = resp.headers.get("Content-Disposition", "")
    if "_50mm.pdf" not in content_disp:
        log(f"❌ FAILED: Expected filename with _50mm.pdf, got {content_disp}")
        return False
    
    pdf_header = resp.content[:8]
    size = len(resp.content)
    
    if pdf_header != b'%PDF-1.4' or size < 500 * 1024:
        log(f"❌ FAILED: Invalid PDF or size too small")
        return False
    
    log(f"✅ PASSED: Status=200, filename contains _50mm.pdf, Size: {size / 1024:.1f} KB")
    return True

def test_pdf_export_clamp_high(token, batch_id):
    """TEST 3a — PDF export with out-of-range diameter (200mm → clamps to 80mm)"""
    log("\n=== TEST 3a: PDF export with diameter=200 (should clamp to 80mm) ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.get(f"{BASE_URL}/dms/coupons/batches/{batch_id}/export-pdf?diameter_mm=200", headers=headers)
    
    if resp.status_code != 200:
        log(f"❌ FAILED: Expected 200, got {resp.status_code}")
        return False
    
    content_disp = resp.headers.get("Content-Disposition", "")
    if "_80mm.pdf" not in content_disp:
        log(f"❌ FAILED: Expected filename with _80mm.pdf (clamped), got {content_disp}")
        return False
    
    pdf_header = resp.content[:8]
    if pdf_header != b'%PDF-1.4':
        log(f"❌ FAILED: Invalid PDF header")
        return False
    
    log(f"✅ PASSED: Status=200, clamped to 80mm, valid PDF")
    return True

def test_pdf_export_clamp_low(token, batch_id):
    """TEST 3b — PDF export with out-of-range diameter (5mm → clamps to 20mm)"""
    log("\n=== TEST 3b: PDF export with diameter=5 (should clamp to 20mm) ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.get(f"{BASE_URL}/dms/coupons/batches/{batch_id}/export-pdf?diameter_mm=5", headers=headers)
    
    if resp.status_code != 200:
        log(f"❌ FAILED: Expected 200, got {resp.status_code}")
        return False
    
    content_disp = resp.headers.get("Content-Disposition", "")
    if "_20mm.pdf" not in content_disp:
        log(f"❌ FAILED: Expected filename with _20mm.pdf (clamped), got {content_disp}")
        return False
    
    log(f"✅ PASSED: Status=200, clamped to 20mm, valid PDF")
    return True

def test_create_share_link_default(token, batch_id):
    """TEST 4 — Create share link (34mm default)"""
    log("\n=== TEST 4: Create share link with default diameter ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.post(f"{BASE_URL}/dms/coupons/batches/{batch_id}/share-link", json={}, headers=headers)
    
    if resp.status_code != 200:
        log(f"❌ FAILED: Expected 200, got {resp.status_code}")
        log(f"   Response: {resp.text[:200]}")
        return False, None
    
    data = resp.json()
    
    # Check required fields
    required_fields = ["ok", "share_url", "expires_at", "batch_label", "coupon_count", "diameter_mm"]
    for field in required_fields:
        if field not in data:
            log(f"❌ FAILED: Missing field '{field}' in response")
            return False, None
    
    if not data.get("ok"):
        log(f"❌ FAILED: ok field is not true")
        return False, None
    
    share_url = data.get("share_url", "")
    if "/public-download/" not in share_url:
        log(f"❌ FAILED: share_url does not contain /public-download/")
        return False, None
    
    # Check expires_at is ~24h in future
    expires_at = data.get("expires_at")
    diameter_mm = data.get("diameter_mm")
    
    if diameter_mm != 34.0:
        log(f"❌ FAILED: Expected diameter_mm=34.0, got {diameter_mm}")
        return False, None
    
    log(f"✅ PASSED: ok=true, share_url={share_url}")
    log(f"   expires_at={expires_at}, diameter_mm={diameter_mm}")
    log(f"   batch_label={data.get('batch_label')}, coupon_count={data.get('coupon_count')}")
    
    return True, share_url

def test_create_share_link_custom(token, batch_id):
    """TEST 5 — Create share link with custom diameter"""
    log("\n=== TEST 5: Create share link with custom diameter (50mm) ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.post(f"{BASE_URL}/dms/coupons/batches/{batch_id}/share-link", 
                        json={"diameter_mm": 50}, headers=headers)
    
    if resp.status_code != 200:
        log(f"❌ FAILED: Expected 200, got {resp.status_code}")
        return False
    
    data = resp.json()
    diameter_mm = data.get("diameter_mm")
    
    if diameter_mm != 50.0:
        log(f"❌ FAILED: Expected diameter_mm=50.0, got {diameter_mm}")
        return False
    
    log(f"✅ PASSED: diameter_mm=50.0")
    return True

def test_public_download_valid(share_url):
    """TEST 6 — Public download WITHOUT auth (using valid share_url)"""
    log("\n=== TEST 6: Public download with valid token (NO AUTH) ===")
    
    # Extract token from share_url
    token = share_url.split("/public-download/")[-1]
    log(f"Extracted token: {token[:20]}...")
    
    # NO Authorization header
    resp = requests.get(f"{BASE_URL}/dms/coupons/batches/public-download/{token}")
    
    if resp.status_code != 200:
        log(f"❌ FAILED: Expected 200, got {resp.status_code}")
        log(f"   Response: {resp.text[:200]}")
        return False
    
    content_type = resp.headers.get("Content-Type", "")
    if "application/pdf" not in content_type:
        log(f"❌ FAILED: Expected Content-Type: application/pdf, got {content_type}")
        return False
    
    size = len(resp.content)
    if size < 500 * 1024:
        log(f"❌ FAILED: Expected size > 500 KB, got {size / 1024:.1f} KB")
        return False
    
    pdf_header = resp.content[:8]
    if pdf_header != b'%PDF-1.4':
        log(f"❌ FAILED: Invalid PDF header")
        return False
    
    log(f"✅ PASSED: Public download works WITHOUT auth, valid PDF, size={size / 1024:.1f} KB")
    return True

def test_public_download_tampered(share_url):
    """TEST 7 — Public download with tampered token"""
    log("\n=== TEST 7: Public download with tampered token ===")
    
    token = share_url.split("/public-download/")[-1]
    # Tamper the token (change one character in the middle)
    tampered_token = token[:len(token)//2] + "X" + token[len(token)//2+1:]
    log(f"Tampered token: {tampered_token[:20]}...")
    
    resp = requests.get(f"{BASE_URL}/dms/coupons/batches/public-download/{tampered_token}")
    
    if resp.status_code not in [400, 403]:
        log(f"❌ FAILED: Expected 400 or 403, got {resp.status_code}")
        return False
    
    log(f"✅ PASSED: Tampered token rejected with {resp.status_code}")
    return True

def test_public_download_random():
    """TEST 8 — Public download with completely random token"""
    log("\n=== TEST 8: Public download with random token ===")
    
    random_token = "randomgarbagestring"
    resp = requests.get(f"{BASE_URL}/dms/coupons/batches/public-download/{random_token}")
    
    if resp.status_code not in [400, 403]:
        log(f"❌ FAILED: Expected 400 or 403, got {resp.status_code}")
        return False
    
    log(f"✅ PASSED: Random token rejected with {resp.status_code}")
    return True

def test_rbac_share_link_creation(distributor_token, batch_id):
    """TEST 10 — RBAC on share-link creation (distributor should get 403)"""
    log("\n=== TEST 10: RBAC - Distributor cannot create share link ===")
    headers = {"Authorization": f"Bearer {distributor_token}"}
    
    resp = requests.post(f"{BASE_URL}/dms/coupons/batches/{batch_id}/share-link", 
                        json={}, headers=headers)
    
    if resp.status_code != 403:
        log(f"❌ FAILED: Expected 403, got {resp.status_code}")
        return False
    
    log(f"✅ PASSED: Distributor correctly denied (403)")
    return True

def test_regression_preview_endpoint(token, batch_id):
    """TEST 11 — Regression: preview endpoint still works"""
    log("\n=== TEST 11: Regression - Preview endpoint still works ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "batch_id": batch_id,
        "from_number": 1,
        "to_number": 10
    }
    
    resp = requests.post(f"{BASE_URL}/dms/coupons/activate-range/preview", 
                        json=payload, headers=headers)
    
    if resp.status_code != 200:
        log(f"❌ FAILED: Expected 200, got {resp.status_code}")
        log(f"   Response: {resp.text[:200]}")
        return False
    
    data = resp.json()
    expected_keys = ["coupons_found", "already_active", "ready_to_activate", "skipped"]
    for key in expected_keys:
        if key not in data:
            log(f"❌ FAILED: Missing key '{key}' in response")
            return False
    
    log(f"✅ PASSED: Preview endpoint working, keys present")
    log(f"   coupons_found={data.get('coupons_found')}, ready_to_activate={data.get('ready_to_activate')}")
    return True

def test_security_no_secrets_in_pdf(token, batch_id):
    """TEST 12 — SECURITY: PDFs do not contain secrets"""
    log("\n=== TEST 12: SECURITY - PDFs do not contain secrets ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    forbidden_strings = [
        b"hmac_secret",
        b"hidden_secure_id",
        b"qr_signature_v2",
        b"secret_token",
        b"GOOIL2|"
    ]
    
    # Test 34mm PDF
    log("Checking 34mm PDF...")
    resp = requests.get(f"{BASE_URL}/dms/coupons/batches/{batch_id}/export-pdf", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAILED: Could not fetch 34mm PDF")
        return False
    
    pdf_34mm = resp.content
    for secret in forbidden_strings:
        if secret in pdf_34mm:
            # Find surrounding bytes
            idx = pdf_34mm.index(secret)
            surrounding = pdf_34mm[max(0, idx-20):idx+len(secret)+20]
            log(f"❌ FAILED: Found forbidden string '{secret.decode()}' in 34mm PDF")
            log(f"   Surrounding bytes: {surrounding}")
            return False
    
    log("✅ 34mm PDF: No secrets found")
    
    # Test 50mm PDF
    log("Checking 50mm PDF...")
    resp = requests.get(f"{BASE_URL}/dms/coupons/batches/{batch_id}/export-pdf?diameter_mm=50", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAILED: Could not fetch 50mm PDF")
        return False
    
    pdf_50mm = resp.content
    for secret in forbidden_strings:
        if secret in pdf_50mm:
            idx = pdf_50mm.index(secret)
            surrounding = pdf_50mm[max(0, idx-20):idx+len(secret)+20]
            log(f"❌ FAILED: Found forbidden string '{secret.decode()}' in 50mm PDF")
            log(f"   Surrounding bytes: {surrounding}")
            return False
    
    log("✅ 50mm PDF: No secrets found")
    log("✅ PASSED: Both PDFs are secure (no secrets leaked)")
    return True

def main():
    """Run all tests"""
    log("=" * 80)
    log("BACKEND TEST SUITE: NEW COUPON PRINTING + SHARE LINK ENDPOINTS")
    log("=" * 80)
    
    results = {}
    
    # Login as owner
    owner_token = login(OWNER_EMAIL, OWNER_PASSWORD)
    if not owner_token:
        log("❌ CRITICAL: Owner login failed, cannot proceed")
        sys.exit(1)
    
    # Login as distributor (for RBAC test)
    distributor_token = login(DISTRIBUTOR_EMAIL, DISTRIBUTOR_PASSWORD)
    if not distributor_token:
        log("⚠️  WARNING: Distributor login failed, RBAC test will be skipped")
    
    # Get or create batch
    batch_id = get_or_create_batch(owner_token)
    if not batch_id:
        log("❌ CRITICAL: Could not get/create batch, cannot proceed")
        sys.exit(1)
    
    # Run tests
    results["TEST 1: PDF export default (34mm)"] = test_pdf_export_default_diameter(owner_token, batch_id)
    results["TEST 2: PDF export custom (50mm)"] = test_pdf_export_custom_diameter(owner_token, batch_id)
    results["TEST 3a: PDF export clamp high (200→80mm)"] = test_pdf_export_clamp_high(owner_token, batch_id)
    results["TEST 3b: PDF export clamp low (5→20mm)"] = test_pdf_export_clamp_low(owner_token, batch_id)
    
    success, share_url = test_create_share_link_default(owner_token, batch_id)
    results["TEST 4: Create share link default"] = success
    
    results["TEST 5: Create share link custom (50mm)"] = test_create_share_link_custom(owner_token, batch_id)
    
    if share_url:
        results["TEST 6: Public download valid (NO AUTH)"] = test_public_download_valid(share_url)
        results["TEST 7: Public download tampered token"] = test_public_download_tampered(share_url)
    else:
        log("⚠️  WARNING: Skipping TEST 6-7 (no share_url)")
        results["TEST 6: Public download valid (NO AUTH)"] = False
        results["TEST 7: Public download tampered token"] = False
    
    results["TEST 8: Public download random token"] = test_public_download_random()
    
    if distributor_token:
        results["TEST 10: RBAC - Distributor denied"] = test_rbac_share_link_creation(distributor_token, batch_id)
    else:
        log("⚠️  WARNING: Skipping TEST 10 (no distributor token)")
        results["TEST 10: RBAC - Distributor denied"] = False
    
    results["TEST 11: Regression - Preview endpoint"] = test_regression_preview_endpoint(owner_token, batch_id)
    results["TEST 12: SECURITY - No secrets in PDFs"] = test_security_no_secrets_in_pdf(owner_token, batch_id)
    
    # Summary
    log("\n" + "=" * 80)
    log("TEST SUMMARY")
    log("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        log(f"{status}: {test_name}")
    
    log("=" * 80)
    log(f"TOTAL: {passed}/{total} tests passed ({passed*100//total}%)")
    log("=" * 80)
    
    if passed == total:
        log("🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        log("⚠️  SOME TESTS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
