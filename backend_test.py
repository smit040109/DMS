#!/usr/bin/env python3
"""
GO OIL DMS — Login Rate Limit Bug Fix Verification
Test the rate limit fix for /auth/login endpoint
"""

import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# Backend URL from frontend/.env
BASE_URL = "https://github-deploy-79.preview.emergentagent.com/api"

# Test credentials
CORRECT_PASSWORD = "GoOil@2026"
TEST_ACCOUNTS = [
    {"email": "superadmin@gooil.com", "role": "super_admin", "name": "Aarav Mehta"},
    {"email": "owner@gooil.com", "role": "owner", "name": "Rakesh Agarwal"},
    {"email": "accountant@gooil.com", "role": "owner_accountant", "name": "Sunita Sharma"},
    {"email": "distributor1@gooil.com", "role": "distributor", "name": "Anil Distributor"},
    {"email": "distributor2@gooil.com", "role": "distributor", "name": "Meena Traders"},
    {"email": "distacct@gooil.com", "role": "distributor_accountant", "name": "Kiran Distributor Accts"},
    {"email": "retailer1@gooil.com", "role": "retailer", "name": "Sharma Auto Parts"},
    {"email": "retailer2@gooil.com", "role": "retailer", "name": "Verma Motors Store"},
    {"email": "salesperson@gooil.com", "role": "salesperson", "name": "Karan Salesperson"},
    {"email": "teamleader@gooil.com", "role": "team_leader", "name": "Neha Team Leader"},
    {"email": "regionalmgr@gooil.com", "role": "regional_manager", "name": "Vikram Regional Manager"},
]

def login(email, password):
    """Perform login and return response"""
    url = f"{BASE_URL}/auth/login"
    payload = {"email": email, "password": password}
    try:
        response = requests.post(url, json=payload, timeout=10)
        return {
            "status_code": response.status_code,
            "email": email,
            "response": response.json() if response.status_code == 200 else response.text
        }
    except Exception as e:
        return {
            "status_code": 0,
            "email": email,
            "error": str(e)
        }

def test_rapid_login_stress():
    """TEST 1: Fire 15 consecutive login requests as fast as possible"""
    print("\n" + "="*80)
    print("TEST 1: RAPID LOGIN STRESS TEST (15 consecutive requests)")
    print("="*80)
    print(f"Testing: owner@gooil.com with password {CORRECT_PASSWORD}")
    print("Expected: All 15 should return HTTP 200 (no 429 rate limit errors)")
    print()
    
    results = []
    start_time = time.time()
    
    # Fire 15 requests as fast as possible
    for i in range(15):
        result = login("owner@gooil.com", CORRECT_PASSWORD)
        results.append(result)
        print(f"Request {i+1:2d}: HTTP {result['status_code']}", end="")
        if result['status_code'] == 200:
            print(" ✅")
        elif result['status_code'] == 429:
            print(" ❌ RATE LIMITED!")
        else:
            print(f" ❌ ERROR: {result.get('error', result.get('response', 'Unknown'))}")
    
    elapsed = time.time() - start_time
    print(f"\nCompleted 15 requests in {elapsed:.2f} seconds")
    
    # Analysis
    success_count = sum(1 for r in results if r['status_code'] == 200)
    rate_limited_count = sum(1 for r in results if r['status_code'] == 429)
    error_count = sum(1 for r in results if r['status_code'] not in [200, 429])
    
    print(f"\nResults:")
    print(f"  ✅ Success (200): {success_count}/15")
    print(f"  ❌ Rate Limited (429): {rate_limited_count}/15")
    print(f"  ❌ Other Errors: {error_count}/15")
    
    if success_count == 15:
        print("\n✅ TEST 1 PASSED: All 15 requests successful, no rate limiting!")
        return True
    else:
        print(f"\n❌ TEST 1 FAILED: Only {success_count}/15 requests successful")
        if rate_limited_count > 0:
            print("   CRITICAL: Rate limit still blocking requests!")
        return False

def test_all_demo_accounts():
    """TEST 2: Login with all 11 demo accounts"""
    print("\n" + "="*80)
    print("TEST 2: ALL 11 DEMO ACCOUNTS LOGIN")
    print("="*80)
    print(f"Testing all accounts with password: {CORRECT_PASSWORD}")
    print("Expected: All return HTTP 200 with correct role and tenant_id=tnt-dms-oil")
    print()
    
    results = []
    for account in TEST_ACCOUNTS:
        result = login(account['email'], CORRECT_PASSWORD)
        results.append({**result, **account})
        
        status = "✅" if result['status_code'] == 200 else "❌"
        print(f"{status} {account['email']:30s} → HTTP {result['status_code']}", end="")
        
        if result['status_code'] == 200:
            response = result['response']
            role = response.get('user', {}).get('role', 'UNKNOWN')
            tenant_id = response.get('user', {}).get('tenant_id', 'UNKNOWN')
            print(f" | Role: {role:20s} | Tenant: {tenant_id}")
            
            # Verify role matches expected
            if role != account['role']:
                print(f"   ⚠️  WARNING: Expected role '{account['role']}' but got '{role}'")
            if tenant_id != "tnt-dms-oil":
                print(f"   ⚠️  WARNING: Expected tenant 'tnt-dms-oil' but got '{tenant_id}'")
        else:
            print(f" | ERROR: {result.get('error', result.get('response', 'Unknown'))}")
    
    # Analysis
    success_count = sum(1 for r in results if r['status_code'] == 200)
    
    print(f"\nResults: {success_count}/11 accounts logged in successfully")
    
    if success_count == 11:
        print("\n✅ TEST 2 PASSED: All 11 demo accounts working!")
        return True
    else:
        print(f"\n❌ TEST 2 FAILED: Only {success_count}/11 accounts working")
        failed = [r for r in results if r['status_code'] != 200]
        for f in failed:
            print(f"   Failed: {f['email']} → HTTP {f['status_code']}")
        return False

def test_wrong_password():
    """TEST 3: Wrong password should return 401"""
    print("\n" + "="*80)
    print("TEST 3: WRONG PASSWORD SECURITY CHECK")
    print("="*80)
    print("Testing: owner@gooil.com with WRONG password")
    print("Expected: HTTP 401 (Unauthorized)")
    print()
    
    result = login("owner@gooil.com", "WrongPassword123!")
    
    print(f"Request: owner@gooil.com with wrong password")
    print(f"Response: HTTP {result['status_code']}")
    
    if result['status_code'] == 401:
        print("\n✅ TEST 3 PASSED: Wrong password correctly returns 401")
        return True
    else:
        print(f"\n❌ TEST 3 FAILED: Expected 401 but got {result['status_code']}")
        print(f"   Response: {result.get('response', result.get('error', 'Unknown'))}")
        return False

def test_regression_endpoints():
    """TEST 4: Quick regression checks on critical endpoints"""
    print("\n" + "="*80)
    print("TEST 4: REGRESSION SANITY CHECKS")
    print("="*80)
    print("Testing critical endpoints to ensure nothing broke")
    print()
    
    # First login as owner to get token
    login_result = login("owner@gooil.com", CORRECT_PASSWORD)
    if login_result['status_code'] != 200:
        print("❌ Cannot proceed: Owner login failed")
        return False
    
    token = login_result['response'].get('token')
    headers = {"Authorization": f"Bearer {token}"}
    
    tests = [
        {
            "name": "GET /api/dms/products",
            "url": f"{BASE_URL}/dms/products",
            "method": "GET",
            "expected_status": 200,
            "check": lambda r: len(r.json()) == 135,
            "check_desc": "135 products"
        },
        {
            "name": "GET /api/dms/price-circulars",
            "url": f"{BASE_URL}/dms/price-circulars",
            "method": "GET",
            "expected_status": 200,
            "check": lambda r: len(r.json()) > 0,
            "check_desc": "returns list"
        },
        {
            "name": "GET /api/dms/settings",
            "url": f"{BASE_URL}/dms/settings",
            "method": "GET",
            "expected_status": 200,
            "check": lambda r: 'gst_pct' in r.json() and 'company_name' in r.json(),
            "check_desc": "returns global settings"
        }
    ]
    
    results = []
    for test in tests:
        try:
            if test['method'] == 'GET':
                response = requests.get(test['url'], headers=headers, timeout=10)
            
            status_ok = response.status_code == test['expected_status']
            check_ok = test['check'](response) if status_ok else False
            
            status = "✅" if (status_ok and check_ok) else "❌"
            print(f"{status} {test['name']:35s} → HTTP {response.status_code}", end="")
            
            if status_ok and check_ok:
                print(f" | {test['check_desc']}")
                results.append(True)
            elif status_ok:
                print(f" | FAILED: {test['check_desc']}")
                results.append(False)
            else:
                print(f" | Expected {test['expected_status']}")
                results.append(False)
                
        except Exception as e:
            print(f"❌ {test['name']:35s} → ERROR: {str(e)}")
            results.append(False)
    
    success_count = sum(results)
    print(f"\nResults: {success_count}/{len(tests)} regression tests passed")
    
    if success_count == len(tests):
        print("\n✅ TEST 4 PASSED: All regression checks working!")
        return True
    else:
        print(f"\n❌ TEST 4 FAILED: Only {success_count}/{len(tests)} checks passed")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("GO OIL DMS — LOGIN RATE LIMIT BUG FIX VERIFICATION")
    print("="*80)
    print(f"Backend URL: {BASE_URL}")
    print(f"Test Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Background: Rate limit was 10/minute per IP on /auth/login.")
    print("In Kubernetes, all requests come from single proxy IP.")
    print("Fix: Increased to 100/minute for login, 30/minute for register.")
    print()
    
    # Run all tests
    test1_passed = test_rapid_login_stress()
    test2_passed = test_all_demo_accounts()
    test3_passed = test_wrong_password()
    test4_passed = test_regression_endpoints()
    
    # Final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    
    all_tests = [
        ("TEST 1: Rapid Login Stress (15 requests)", test1_passed),
        ("TEST 2: All 11 Demo Accounts", test2_passed),
        ("TEST 3: Wrong Password Security", test3_passed),
        ("TEST 4: Regression Sanity Checks", test4_passed),
    ]
    
    for test_name, passed in all_tests:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    total_passed = sum(1 for _, passed in all_tests if passed)
    print(f"\nOverall: {total_passed}/4 tests passed")
    
    if total_passed == 4:
        print("\n🎉 ALL TESTS PASSED! Login rate limit fix verified successfully.")
        print("   - No rate limiting on 15 consecutive requests")
        print("   - All 11 demo accounts working")
        print("   - Security intact (wrong password → 401)")
        print("   - No regressions in critical endpoints")
    else:
        print(f"\n⚠️  {4 - total_passed} TEST(S) FAILED - See details above")
    
    print("="*80)

if __name__ == "__main__":
    main()
