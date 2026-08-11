#!/usr/bin/env python3
"""
CONTINUATION v8 — Punch RBAC Fix Verification
Tests that punch endpoints are FIELD-ONLY (salesperson, team_leader, regional_manager)
and correctly reject distributor, retailer, accountant, owner roles.
"""

import requests
import json

# Backend URL from frontend/.env
BASE_URL = "https://auth-mongo-secure.preview.emergentagent.com/api"

# All demo users password
PASSWORD = "GoOil@2026"

# Test accounts
ACCOUNTS = {
    "distributor1": "distributor1@gooil.com",
    "retailer1": "retailer1@gooil.com",
    "distacct": "distacct@gooil.com",
    "accountant": "accountant@gooil.com",
    "owner": "owner@gooil.com",
    "salesperson": "salesperson@gooil.com",
    "teamleader": "teamleader@gooil.com",
}

def login(email: str, password: str) -> str:
    """Login and return JWT token"""
    resp = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if resp.status_code != 200:
        raise Exception(f"Login failed for {email}: {resp.status_code} {resp.text}")
    data = resp.json()
    return data["token"]

def test_punch_in(token: str, lat: float = 28.6, lng: float = 77.2) -> tuple[int, dict]:
    """Test POST /api/dms/punch/in"""
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(f"{BASE_URL}/dms/punch/in", json={"lat": lat, "lng": lng}, headers=headers)
    try:
        data = resp.json()
    except Exception:
        data = {"error": resp.text}
    return resp.status_code, data

def test_punch_today(token: str) -> tuple[int, dict]:
    """Test GET /api/dms/punch/today"""
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/dms/punch/today", headers=headers)
    try:
        data = resp.json()
    except Exception:
        data = {"error": resp.text}
    return resp.status_code, data

def test_tl_punch_in(token: str, lat: float = 28.6, lng: float = 77.2) -> tuple[int, dict]:
    """Test POST /api/dms/tl/punch/in"""
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(f"{BASE_URL}/dms/tl/punch/in", json={"lat": lat, "lng": lng}, headers=headers)
    try:
        data = resp.json()
    except Exception:
        data = {"error": resp.text}
    return resp.status_code, data

def main():
    print("=" * 80)
    print("CONTINUATION v8 — PUNCH RBAC FIX VERIFICATION")
    print("=" * 80)
    print()
    
    results = []
    
    # Test 1: Distributor1 should get 403
    print("TEST 1: distributor1@gooil.com → POST /api/dms/punch/in")
    print("-" * 80)
    try:
        token = login(ACCOUNTS["distributor1"], PASSWORD)
        status, data = test_punch_in(token)
        expected = 403
        passed = status == expected
        results.append(("Test 1: Distributor1 punch/in", passed))
        print(f"  Status: {status} (expected {expected})")
        print(f"  Response: {json.dumps(data, indent=2)}")
        print(f"  Result: {'✅ PASS' if passed else '❌ FAIL'}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results.append(("Test 1: Distributor1 punch/in", False))
    print()
    
    # Test 2: Retailer1 should get 403
    print("TEST 2: retailer1@gooil.com → POST /api/dms/punch/in")
    print("-" * 80)
    try:
        token = login(ACCOUNTS["retailer1"], PASSWORD)
        status, data = test_punch_in(token)
        expected = 403
        passed = status == expected
        results.append(("Test 2: Retailer1 punch/in", passed))
        print(f"  Status: {status} (expected {expected})")
        print(f"  Response: {json.dumps(data, indent=2)}")
        print(f"  Result: {'✅ PASS' if passed else '❌ FAIL'}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results.append(("Test 2: Retailer1 punch/in", False))
    print()
    
    # Test 3: Distributor Accountant should get 403
    print("TEST 3: distacct@gooil.com (distributor_accountant) → POST /api/dms/punch/in")
    print("-" * 80)
    try:
        token = login(ACCOUNTS["distacct"], PASSWORD)
        status, data = test_punch_in(token)
        expected = 403
        passed = status == expected
        results.append(("Test 3: Distributor Accountant punch/in", passed))
        print(f"  Status: {status} (expected {expected})")
        print(f"  Response: {json.dumps(data, indent=2)}")
        print(f"  Result: {'✅ PASS' if passed else '❌ FAIL'}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results.append(("Test 3: Distributor Accountant punch/in", False))
    print()
    
    # Test 4: Owner Accountant should get 403
    print("TEST 4: accountant@gooil.com (owner_accountant) → POST /api/dms/punch/in")
    print("-" * 80)
    try:
        token = login(ACCOUNTS["accountant"], PASSWORD)
        status, data = test_punch_in(token)
        expected = 403
        passed = status == expected
        results.append(("Test 4: Owner Accountant punch/in", passed))
        print(f"  Status: {status} (expected {expected})")
        print(f"  Response: {json.dumps(data, indent=2)}")
        print(f"  Result: {'✅ PASS' if passed else '❌ FAIL'}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results.append(("Test 4: Owner Accountant punch/in", False))
    print()
    
    # Test 5: Owner should get 403
    print("TEST 5: owner@gooil.com → POST /api/dms/punch/in")
    print("-" * 80)
    try:
        token = login(ACCOUNTS["owner"], PASSWORD)
        status, data = test_punch_in(token)
        expected = 403
        passed = status == expected
        results.append(("Test 5: Owner punch/in", passed))
        print(f"  Status: {status} (expected {expected})")
        print(f"  Response: {json.dumps(data, indent=2)}")
        print(f"  Result: {'✅ PASS' if passed else '❌ FAIL'}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results.append(("Test 5: Owner punch/in", False))
    print()
    
    # Test 6: Salesperson should get 200 (field staff allowed)
    print("TEST 6: salesperson@gooil.com → POST /api/dms/punch/in")
    print("-" * 80)
    try:
        token = login(ACCOUNTS["salesperson"], PASSWORD)
        status, data = test_punch_in(token)
        # 200 or 400 (already punched in) are both acceptable
        expected = "200 or 400 (already punched in)"
        passed = status in [200, 400]
        results.append(("Test 6: Salesperson punch/in", passed))
        print(f"  Status: {status} (expected {expected})")
        print(f"  Response: {json.dumps(data, indent=2)}")
        print(f"  Result: {'✅ PASS' if passed else '❌ FAIL'}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results.append(("Test 6: Salesperson punch/in", False))
    print()
    
    # Test 7: Team Leader should get 200 for GET /api/dms/punch/today
    print("TEST 7: teamleader@gooil.com → GET /api/dms/punch/today")
    print("-" * 80)
    try:
        token = login(ACCOUNTS["teamleader"], PASSWORD)
        status, data = test_punch_today(token)
        expected = 200
        passed = status == expected
        results.append(("Test 7: Team Leader punch/today", passed))
        print(f"  Status: {status} (expected {expected})")
        print(f"  Response: {json.dumps(data, indent=2)}")
        print(f"  Result: {'✅ PASS' if passed else '❌ FAIL'}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results.append(("Test 7: Team Leader punch/today", False))
    print()
    
    # Test 7b: Team Leader POST /api/dms/tl/punch/in (if applicable)
    print("TEST 7b: teamleader@gooil.com → POST /api/dms/tl/punch/in")
    print("-" * 80)
    try:
        token = login(ACCOUNTS["teamleader"], PASSWORD)
        status, data = test_tl_punch_in(token)
        # 200 or 400 (already punched in) are both acceptable
        expected = "200 or 400 (already punched in)"
        passed = status in [200, 400]
        results.append(("Test 7b: Team Leader tl/punch/in", passed))
        print(f"  Status: {status} (expected {expected})")
        print(f"  Response: {json.dumps(data, indent=2)}")
        print(f"  Result: {'✅ PASS' if passed else '❌ FAIL'}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results.append(("Test 7b: Team Leader tl/punch/in", False))
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    print(f"Total: {passed_count}/{total_count} tests passed ({passed_count*100//total_count}%)")
    print()
    for test_name, passed in results:
        print(f"  {'✅' if passed else '❌'} {test_name}")
    print()
    
    if passed_count == total_count:
        print("🎉 ALL TESTS PASSED — Punch RBAC fix verified!")
    else:
        print("⚠️  SOME TESTS FAILED — Review results above")
    print()

if __name__ == "__main__":
    main()
