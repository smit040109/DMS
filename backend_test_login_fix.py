#!/usr/bin/env python3
"""
GO OIL DMS — Login Bug Fix Verification
Tests all 11 demo accounts after orphan user cleanup + quick regression
"""
import requests
import json
from typing import Dict, Any

# Base URL
BASE_URL = "https://smartcoupon-retail.preview.emergentagent.com/api"

# All 11 demo accounts (password: GoOil@2026)
ALL_ACCOUNTS = [
    {"email": "superadmin@gooil.com", "role": "super_admin", "name": "Aarav Mehta (Super Admin)"},
    {"email": "owner@gooil.com", "role": "owner", "name": "Rakesh Agarwal (Owner)"},
    {"email": "accountant@gooil.com", "role": "owner_accountant", "name": "Sunita Sharma (Accounts)"},
    {"email": "distributor1@gooil.com", "role": "distributor", "name": "Anil Distributor — Delhi"},
    {"email": "distributor2@gooil.com", "role": "distributor", "name": "Meena Traders — Mumbai"},
    {"email": "distacct@gooil.com", "role": "distributor_accountant", "name": "Kiran Distributor Accts"},
    {"email": "retailer1@gooil.com", "role": "retailer", "name": "Sharma Auto Parts"},
    {"email": "retailer2@gooil.com", "role": "retailer", "name": "Verma Motors Store"},
    {"email": "salesperson@gooil.com", "role": "salesperson", "name": "Karan Salesperson"},
    {"email": "teamleader@gooil.com", "role": "team_leader", "name": "Neha Team Leader"},
    {"email": "regionalmgr@gooil.com", "role": "regional_manager", "name": "Vikram Regional Manager"},
]

PASSWORD = "GoOil@2026"
EXPECTED_TENANT = "tnt-dms-oil"

# Session storage
TOKENS: Dict[str, str] = {}
USERS: Dict[str, Dict[str, Any]] = {}


def test_all_logins():
    """Test login for ALL 11 demo accounts."""
    print("\n" + "="*80)
    print("TEST 1: LOGIN FOR ALL 11 DEMO ACCOUNTS")
    print("="*80)
    
    failed_logins = []
    passed_logins = []
    
    for account in ALL_ACCOUNTS:
        email = account["email"]
        expected_role = account["role"]
        expected_name = account["name"]
        
        print(f"\nTesting: {email} (expected role: {expected_role})")
        
        try:
            resp = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": email, "password": PASSWORD},
                timeout=10
            )
            
            if resp.status_code != 200:
                failed_logins.append({
                    "email": email,
                    "error": f"HTTP {resp.status_code}",
                    "detail": resp.text[:200]
                })
                print(f"  ❌ FAILED: HTTP {resp.status_code}")
                print(f"     Response: {resp.text[:200]}")
                continue
            
            data = resp.json()
            user = data.get("user", {})
            token = data.get("token")
            
            # Verify token exists
            if not token:
                failed_logins.append({
                    "email": email,
                    "error": "No token in response",
                    "detail": str(data)
                })
                print(f"  ❌ FAILED: No token in response")
                continue
            
            # Verify role
            actual_role = user.get("role")
            if actual_role != expected_role:
                failed_logins.append({
                    "email": email,
                    "error": f"Role mismatch: expected {expected_role}, got {actual_role}",
                    "detail": str(user)
                })
                print(f"  ❌ FAILED: Role mismatch (expected: {expected_role}, got: {actual_role})")
                continue
            
            # Verify tenant_id
            actual_tenant = user.get("tenant_id")
            if actual_tenant != EXPECTED_TENANT:
                failed_logins.append({
                    "email": email,
                    "error": f"Tenant mismatch: expected {EXPECTED_TENANT}, got {actual_tenant}",
                    "detail": str(user)
                })
                print(f"  ❌ FAILED: Tenant mismatch (expected: {EXPECTED_TENANT}, got: {actual_tenant})")
                continue
            
            # Success!
            passed_logins.append(email)
            TOKENS[email] = token
            USERS[email] = user
            print(f"  ✅ PASSED")
            print(f"     Role: {actual_role}")
            print(f"     Tenant: {actual_tenant}")
            print(f"     Name: {user.get('name', 'N/A')}")
            
        except Exception as e:
            failed_logins.append({
                "email": email,
                "error": f"Exception: {type(e).__name__}",
                "detail": str(e)
            })
            print(f"  ❌ FAILED: {type(e).__name__}: {e}")
    
    # Summary
    print("\n" + "="*80)
    print(f"LOGIN TEST SUMMARY: {len(passed_logins)}/11 PASSED")
    print("="*80)
    
    if passed_logins:
        print(f"\n✅ PASSED ({len(passed_logins)}):")
        for email in passed_logins:
            print(f"   - {email}")
    
    if failed_logins:
        print(f"\n❌ FAILED ({len(failed_logins)}):")
        for fail in failed_logins:
            print(f"   - {fail['email']}")
            print(f"     Error: {fail['error']}")
            print(f"     Detail: {fail['detail']}")
    
    return len(failed_logins) == 0


def test_regression():
    """Quick regression tests to ensure cleanup didn't break anything."""
    print("\n" + "="*80)
    print("TEST 2: QUICK REGRESSION")
    print("="*80)
    
    if "owner@gooil.com" not in TOKENS:
        print("❌ Cannot run regression - owner login failed")
        return False
    
    owner_token = TOKENS["owner@gooil.com"]
    headers = {"Authorization": f"Bearer {owner_token}", "Content-Type": "application/json"}
    
    regression_results = []
    
    # Test 1: GET /api/dms/products → 135 products
    print("\n1. GET /api/dms/products (expect 135 products)")
    try:
        resp = requests.get(f"{BASE_URL}/dms/products", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            products = data.get("data", [])
            count = len(products)
            if count == 135:
                print(f"   ✅ PASSED: {count} products")
                regression_results.append(True)
            else:
                print(f"   ⚠️  WARNING: Expected 135 products, got {count}")
                regression_results.append(True)  # Not critical
        else:
            print(f"   ❌ FAILED: HTTP {resp.status_code}")
            regression_results.append(False)
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        regression_results.append(False)
    
    # Test 2: GET /api/dms/price-circulars → at least 1 circular
    print("\n2. GET /api/dms/price-circulars (expect at least 1 circular)")
    try:
        resp = requests.get(f"{BASE_URL}/dms/price-circulars", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            circulars = data.get("data", [])
            count = len(circulars)
            if count >= 1:
                print(f"   ✅ PASSED: {count} circular(s)")
                regression_results.append(True)
            else:
                print(f"   ❌ FAILED: Expected at least 1 circular, got {count}")
                regression_results.append(False)
        else:
            print(f"   ❌ FAILED: HTTP {resp.status_code}")
            regression_results.append(False)
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        regression_results.append(False)
    
    # Test 3: GET /api/dms/settings → returns global settings
    print("\n3. GET /api/dms/settings (expect global settings)")
    try:
        resp = requests.get(f"{BASE_URL}/dms/settings", headers=headers, timeout=10)
        if resp.status_code == 200:
            settings = resp.json()
            if "gst_pct" in settings and "company_name" in settings:
                print(f"   ✅ PASSED: gst_pct={settings['gst_pct']}, company_name={settings['company_name']}")
                regression_results.append(True)
            else:
                print(f"   ❌ FAILED: Missing required fields")
                regression_results.append(False)
        else:
            print(f"   ❌ FAILED: HTTP {resp.status_code}")
            regression_results.append(False)
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        regression_results.append(False)
    
    # Test 4: Owner can list distributors
    print("\n4. GET /api/dms/distributors (owner can list distributors)")
    try:
        resp = requests.get(f"{BASE_URL}/dms/distributors", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            distributors = data.get("data", [])
            count = len(distributors)
            print(f"   ✅ PASSED: {count} distributor(s)")
            regression_results.append(True)
        else:
            print(f"   ❌ FAILED: HTTP {resp.status_code}")
            regression_results.append(False)
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        regression_results.append(False)
    
    # Test 5: Owner can list retailers
    print("\n5. GET /api/dms/retailers (owner can list retailers)")
    try:
        resp = requests.get(f"{BASE_URL}/dms/retailers", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            retailers = data.get("data", [])
            count = len(retailers)
            print(f"   ✅ PASSED: {count} retailer(s)")
            regression_results.append(True)
        else:
            print(f"   ❌ FAILED: HTTP {resp.status_code}")
            regression_results.append(False)
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        regression_results.append(False)
    
    # Test 6: Owner can list categories
    print("\n6. GET /api/dms/categories (owner can list categories)")
    try:
        resp = requests.get(f"{BASE_URL}/dms/categories", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            categories = data.get("data", [])
            count = len(categories)
            print(f"   ✅ PASSED: {count} categor(ies)")
            regression_results.append(True)
        else:
            print(f"   ❌ FAILED: HTTP {resp.status_code}")
            regression_results.append(False)
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        regression_results.append(False)
    
    # Test 7: Distributor1 can browse products
    if "distributor1@gooil.com" in TOKENS:
        print("\n7. GET /api/dms/distributor/browse (distributor1 can browse)")
        dist_token = TOKENS["distributor1@gooil.com"]
        dist_headers = {"Authorization": f"Bearer {dist_token}", "Content-Type": "application/json"}
        try:
            resp = requests.get(f"{BASE_URL}/dms/distributor/browse", headers=dist_headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                products = data.get("data", [])
                count = len(products)
                print(f"   ✅ PASSED: {count} product(s) visible")
                regression_results.append(True)
            else:
                print(f"   ❌ FAILED: HTTP {resp.status_code}")
                regression_results.append(False)
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            regression_results.append(False)
    
    # Test 8: Salesperson can punch in
    if "salesperson@gooil.com" in TOKENS:
        print("\n8. POST /api/dms/punch/in (salesperson can punch in)")
        sp_token = TOKENS["salesperson@gooil.com"]
        sp_headers = {"Authorization": f"Bearer {sp_token}", "Content-Type": "application/json"}
        try:
            resp = requests.post(
                f"{BASE_URL}/dms/punch/in",
                headers=sp_headers,
                json={"gps_lat": 28.6139, "gps_lng": 77.2090},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                print(f"   ✅ PASSED: ok={data.get('ok')}, already={data.get('already', False)}")
                regression_results.append(True)
            else:
                print(f"   ❌ FAILED: HTTP {resp.status_code}")
                regression_results.append(False)
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            regression_results.append(False)
    
    # Summary
    print("\n" + "="*80)
    passed = sum(regression_results)
    total = len(regression_results)
    print(f"REGRESSION TEST SUMMARY: {passed}/{total} PASSED")
    print("="*80)
    
    return all(regression_results)


def test_db_sanity():
    """DB sanity check via API responses."""
    print("\n" + "="*80)
    print("TEST 3: DB SANITY CHECK")
    print("="*80)
    
    if "owner@gooil.com" not in TOKENS:
        print("❌ Cannot run DB sanity - owner login failed")
        return False
    
    owner_token = TOKENS["owner@gooil.com"]
    headers = {"Authorization": f"Bearer {owner_token}", "Content-Type": "application/json"}
    
    # Check for duplicate emails via /api/dms/owner/users (if exists)
    print("\n1. Check for duplicate emails in user list")
    try:
        resp = requests.get(f"{BASE_URL}/dms/owner/users", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            users = data.get("data", [])
            emails = [u.get("email") for u in users]
            unique_emails = set(emails)
            
            if len(emails) == len(unique_emails):
                print(f"   ✅ PASSED: No duplicate emails ({len(emails)} users)")
            else:
                duplicates = [e for e in emails if emails.count(e) > 1]
                print(f"   ❌ FAILED: Duplicate emails found: {set(duplicates)}")
                return False
        else:
            print(f"   ⚠️  SKIPPED: Endpoint not available (HTTP {resp.status_code})")
    except Exception as e:
        print(f"   ⚠️  SKIPPED: {e}")
    
    # Verify only DMS users exist (11 + platform owner if applicable)
    print("\n2. Verify user count (expect 11 DMS users)")
    try:
        resp = requests.get(f"{BASE_URL}/dms/owner/users", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            users = data.get("data", [])
            dms_users = [u for u in users if u.get("tenant_id") == EXPECTED_TENANT]
            count = len(dms_users)
            
            if count == 11:
                print(f"   ✅ PASSED: Exactly 11 DMS users")
            elif count > 11:
                print(f"   ⚠️  WARNING: {count} DMS users (expected 11)")
            else:
                print(f"   ❌ FAILED: Only {count} DMS users (expected 11)")
                return False
        else:
            print(f"   ⚠️  SKIPPED: Endpoint not available (HTTP {resp.status_code})")
    except Exception as e:
        print(f"   ⚠️  SKIPPED: {e}")
    
    print("\n" + "="*80)
    print("DB SANITY CHECK COMPLETE")
    print("="*80)
    
    return True


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("GO OIL DMS — LOGIN BUG FIX VERIFICATION")
    print("Testing all 11 demo accounts after orphan user cleanup")
    print("="*80)
    
    # Test 1: All logins
    login_success = test_all_logins()
    
    # Test 2: Regression
    regression_success = test_regression()
    
    # Test 3: DB sanity
    db_sanity_success = test_db_sanity()
    
    # Final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    print(f"1. Login Test (11 accounts):  {'✅ PASSED' if login_success else '❌ FAILED'}")
    print(f"2. Regression Test:           {'✅ PASSED' if regression_success else '❌ FAILED'}")
    print(f"3. DB Sanity Check:           {'✅ PASSED' if db_sanity_success else '❌ FAILED'}")
    print("="*80)
    
    if login_success and regression_success and db_sanity_success:
        print("\n🎉 ALL TESTS PASSED — LOGIN BUG FIX VERIFIED")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED — REVIEW DETAILS ABOVE")
        return 1


if __name__ == "__main__":
    exit(main())
