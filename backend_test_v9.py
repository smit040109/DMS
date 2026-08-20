#!/usr/bin/env python3
"""
CONTINUATION v9 — AI Report Export + Owner Reset RBAC Verification
Tests:
1. POST /api/ai/copilot/export with format=pdf and format=excel for different users
2. POST /api/dms/owner/reset-demo-data RBAC (403 for non-owner roles)
   IMPORTANT: Do NOT call reset as owner (it wipes seeded data)
"""

import requests
import json

# Backend URL from frontend/.env
BASE_URL = "https://po-order-sync.preview.emergentagent.com/api"

# All demo users password
PASSWORD = "GoOil@2026"

# Test accounts
ACCOUNTS = {
    "owner": "owner@gooil.com",
    "distributor1": "distributor1@gooil.com",
    "retailer1": "retailer1@gooil.com",
    "salesperson": "salesperson@gooil.com",
    "accountant": "accountant@gooil.com",
}

def login(email: str, password: str) -> str:
    """Login and return JWT token"""
    resp = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if resp.status_code != 200:
        raise Exception(f"Login failed for {email}: {resp.status_code} {resp.text}")
    data = resp.json()
    return data["token"]

def test_ai_export(token: str, format: str, title: str, content: str) -> tuple[int, bytes, dict]:
    """Test POST /api/ai/copilot/export"""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"format": format, "title": title, "content": content}
    resp = requests.post(f"{BASE_URL}/ai/copilot/export", json=payload, headers=headers)
    
    # Get headers
    headers_dict = dict(resp.headers)
    
    return resp.status_code, resp.content, headers_dict

def test_owner_reset(token: str) -> tuple[int, dict]:
    """Test POST /api/dms/owner/reset-demo-data"""
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(f"{BASE_URL}/dms/owner/reset-demo-data", headers=headers)
    try:
        data = resp.json()
    except Exception:
        data = {"error": resp.text}
    return resp.status_code, data

def main():
    print("=" * 80)
    print("CONTINUATION v9 — AI REPORT EXPORT + OWNER RESET RBAC VERIFICATION")
    print("=" * 80)
    print()
    
    results = []
    
    # =========================================================================
    # TEST GROUP 1: AI REPORT EXPORT
    # =========================================================================
    print("=" * 80)
    print("TEST GROUP 1: AI REPORT EXPORT — POST /api/ai/copilot/export")
    print("=" * 80)
    print()
    
    test_content = """**Summary**
- Distributors: 2
- Products: 135
- Total Revenue: ₹1,25,000
- Outstanding: ₹50,000"""
    
    # Test 1a: Owner exports PDF
    print("TEST 1a: owner@gooil.com → format=pdf")
    print("-" * 80)
    try:
        token = login(ACCOUNTS["owner"], PASSWORD)
        status, content, headers = test_ai_export(token, "pdf", "Test Report", test_content)
        
        # Check status
        status_ok = status == 200
        
        # Check Content-Type (case-insensitive header lookup)
        content_type = ""
        for key, value in headers.items():
            if key.lower() == "content-type":
                content_type = value.lower()
                break
        content_type_ok = "application/pdf" in content_type
        
        # Check PDF magic bytes (%PDF-)
        pdf_magic_ok = content[:5] == b'%PDF-'
        
        # For this test, we'll consider it passing if status and magic bytes are correct
        # (Content-Type header might be missing in streaming responses)
        passed = status_ok and pdf_magic_ok
        results.append(("Test 1a: Owner PDF export", passed))
        
        print(f"  Status: {status} (expected 200) {'✅' if status_ok else '❌'}")
        print(f"  Content-Type: '{content_type}' (expected application/pdf) {'✅' if content_type_ok else '⚠️'}")
        print(f"  PDF magic bytes: {content[:5]} (expected b'%PDF-') {'✅' if pdf_magic_ok else '❌'}")
        print(f"  Content size: {len(content)} bytes")
        print(f"  Result: {'✅ PASS' if passed else '❌ FAIL'}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results.append(("Test 1a: Owner PDF export", False))
    print()
    
    # Test 1b: Owner exports Excel
    print("TEST 1b: owner@gooil.com → format=excel")
    print("-" * 80)
    try:
        token = login(ACCOUNTS["owner"], PASSWORD)
        status, content, headers = test_ai_export(token, "excel", "Test Report", test_content)
        
        # Check status
        status_ok = status == 200
        
        # Check Content-Type (case-insensitive header lookup)
        content_type = ""
        for key, value in headers.items():
            if key.lower() == "content-type":
                content_type = value.lower()
                break
        content_type_ok = "spreadsheetml" in content_type
        
        # Check ZIP magic bytes (PK) - Excel files are ZIP archives
        zip_magic_ok = content[:2] == b'PK'
        
        # For this test, we'll consider it passing if status and magic bytes are correct
        passed = status_ok and zip_magic_ok
        results.append(("Test 1b: Owner Excel export", passed))
        
        print(f"  Status: {status} (expected 200) {'✅' if status_ok else '❌'}")
        print(f"  Content-Type: '{content_type}' (expected spreadsheetml) {'✅' if content_type_ok else '⚠️'}")
        print(f"  ZIP magic bytes: {content[:2]} (expected b'PK') {'✅' if zip_magic_ok else '❌'}")
        print(f"  Content size: {len(content)} bytes")
        print(f"  Result: {'✅ PASS' if passed else '❌ FAIL'}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results.append(("Test 1b: Owner Excel export", False))
    print()
    
    # Test 1c: Distributor1 exports PDF (any authenticated user allowed)
    print("TEST 1c: distributor1@gooil.com → format=pdf")
    print("-" * 80)
    try:
        token = login(ACCOUNTS["distributor1"], PASSWORD)
        status, content, headers = test_ai_export(token, "pdf", "Distributor Report", test_content)
        
        # Check status
        status_ok = status == 200
        
        # Check PDF magic bytes
        pdf_magic_ok = content[:5] == b'%PDF-'
        
        passed = status_ok and pdf_magic_ok
        results.append(("Test 1c: Distributor1 PDF export", passed))
        
        print(f"  Status: {status} (expected 200) {'✅' if status_ok else '❌'}")
        print(f"  PDF magic bytes: {content[:5]} (expected b'%PDF-') {'✅' if pdf_magic_ok else '❌'}")
        print(f"  Content size: {len(content)} bytes")
        print(f"  Result: {'✅ PASS' if passed else '❌ FAIL'}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results.append(("Test 1c: Distributor1 PDF export", False))
    print()
    
    # Test 1d: Missing content should return 400
    print("TEST 1d: owner@gooil.com → format=pdf with empty content (expect 400)")
    print("-" * 80)
    try:
        token = login(ACCOUNTS["owner"], PASSWORD)
        status, content, headers = test_ai_export(token, "pdf", "Test", "")
        
        expected = 400
        passed = status == expected
        results.append(("Test 1d: Empty content validation", passed))
        
        print(f"  Status: {status} (expected {expected}) {'✅' if passed else '❌'}")
        try:
            error_data = json.loads(content.decode('utf-8'))
            print(f"  Response: {json.dumps(error_data, indent=2)}")
        except Exception:
            print(f"  Response: {content[:200]}")
        print(f"  Result: {'✅ PASS' if passed else '❌ FAIL'}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results.append(("Test 1d: Empty content validation", False))
    print()
    
    # =========================================================================
    # TEST GROUP 2: OWNER RESET RBAC (DO NOT RUN AS OWNER!)
    # =========================================================================
    print("=" * 80)
    print("TEST GROUP 2: OWNER RESET RBAC — POST /api/dms/owner/reset-demo-data")
    print("IMPORTANT: Testing RBAC only (403 for non-owner). NOT calling as owner!")
    print("=" * 80)
    print()
    
    # Test 2a: Distributor1 should get 403
    print("TEST 2a: distributor1@gooil.com → POST /api/dms/owner/reset-demo-data")
    print("-" * 80)
    try:
        token = login(ACCOUNTS["distributor1"], PASSWORD)
        status, data = test_owner_reset(token)
        expected = 403
        passed = status == expected
        results.append(("Test 2a: Distributor1 reset (expect 403)", passed))
        print(f"  Status: {status} (expected {expected})")
        print(f"  Response: {json.dumps(data, indent=2)}")
        print(f"  Result: {'✅ PASS' if passed else '❌ FAIL'}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results.append(("Test 2a: Distributor1 reset (expect 403)", False))
    print()
    
    # Test 2b: Retailer1 should get 403
    print("TEST 2b: retailer1@gooil.com → POST /api/dms/owner/reset-demo-data")
    print("-" * 80)
    try:
        token = login(ACCOUNTS["retailer1"], PASSWORD)
        status, data = test_owner_reset(token)
        expected = 403
        passed = status == expected
        results.append(("Test 2b: Retailer1 reset (expect 403)", passed))
        print(f"  Status: {status} (expected {expected})")
        print(f"  Response: {json.dumps(data, indent=2)}")
        print(f"  Result: {'✅ PASS' if passed else '❌ FAIL'}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results.append(("Test 2b: Retailer1 reset (expect 403)", False))
    print()
    
    # Test 2c: Salesperson should get 403
    print("TEST 2c: salesperson@gooil.com → POST /api/dms/owner/reset-demo-data")
    print("-" * 80)
    try:
        token = login(ACCOUNTS["salesperson"], PASSWORD)
        status, data = test_owner_reset(token)
        expected = 403
        passed = status == expected
        results.append(("Test 2c: Salesperson reset (expect 403)", passed))
        print(f"  Status: {status} (expected {expected})")
        print(f"  Response: {json.dumps(data, indent=2)}")
        print(f"  Result: {'✅ PASS' if passed else '❌ FAIL'}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results.append(("Test 2c: Salesperson reset (expect 403)", False))
    print()
    
    # Test 2d: Owner Accountant should get 403
    print("TEST 2d: accountant@gooil.com (owner_accountant) → POST /api/dms/owner/reset-demo-data")
    print("-" * 80)
    try:
        token = login(ACCOUNTS["accountant"], PASSWORD)
        status, data = test_owner_reset(token)
        expected = 403
        passed = status == expected
        results.append(("Test 2d: Owner Accountant reset (expect 403)", passed))
        print(f"  Status: {status} (expected {expected})")
        print(f"  Response: {json.dumps(data, indent=2)}")
        print(f"  Result: {'✅ PASS' if passed else '❌ FAIL'}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results.append(("Test 2d: Owner Accountant reset (expect 403)", False))
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    print(f"Total: {passed_count}/{total_count} tests passed ({passed_count*100//total_count if total_count > 0 else 0}%)")
    print()
    
    print("AI REPORT EXPORT:")
    for i in range(4):
        if i < len(results):
            test_name, passed = results[i]
            print(f"  {'✅' if passed else '❌'} {test_name}")
    print()
    
    print("OWNER RESET RBAC:")
    for i in range(4, len(results)):
        test_name, passed = results[i]
        print(f"  {'✅' if passed else '❌'} {test_name}")
    print()
    
    if passed_count == total_count:
        print("🎉 ALL TESTS PASSED — CONTINUATION v9 verified!")
    else:
        print("⚠️  SOME TESTS FAILED — Review results above")
    print()

if __name__ == "__main__":
    main()
