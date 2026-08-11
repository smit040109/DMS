#!/usr/bin/env python3
"""
Backend API Testing for Owner-managed logins + full-process onboarding
Tests 5 areas as specified in the review request.
"""
import requests
import json
import random
import string
from typing import Dict, Any, List

# Configuration
BASE_URL = "https://auth-mongo-secure.preview.emergentagent.com/api"
OWNER_EMAIL = "gooilindia13@gmail.com"
OWNER_PASSWORD = "Arjun@india13"

# Test tracking
test_results = []
created_items = {
    "distributors": [],
    "retailers": [],
    "users": []
}


def log_test(area: str, test_name: str, passed: bool, details: str = ""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    result = f"{status} | {area} | {test_name}"
    if details:
        result += f"\n    Details: {details}"
    print(result)
    test_results.append({
        "area": area,
        "test": test_name,
        "passed": passed,
        "details": details
    })


def random_email():
    """Generate random email for testing"""
    rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"qa_test_{rand}@test.com"


def get_owner_token() -> str:
    """Login as owner and get JWT token"""
    print(f"\n🔐 Logging in as owner: {OWNER_EMAIL}")
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}
    )
    if resp.status_code != 200:
        raise Exception(f"Owner login failed: {resp.status_code} {resp.text}")
    token = resp.json().get("token")
    print(f"✅ Owner login successful, token obtained")
    return token


def headers_with_token(token: str) -> Dict[str, str]:
    """Return headers with Authorization Bearer token"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def test_area_1_distributor_onboarding(token: str):
    """
    TEST AREA 1: POST /api/dms/distributors (owner only) — FULL-PROCESS ONBOARDING enforcement
    """
    print("\n" + "="*80)
    print("TEST AREA 1: Distributor Full-Process Onboarding")
    print("="*80)
    
    headers = headers_with_token(token)
    
    # Test 1a: Missing fields should return 400
    print("\n📋 Test 1a: Incomplete onboarding (missing fields) should return 400")
    incomplete_payload = {
        "name": "Test Distributor Incomplete",
        "email": random_email(),
        "password": "Test@123",
        "phone": "9876543210",
        "address": "Test Address"
    }
    resp = requests.post(f"{BASE_URL}/dms/distributors", json=incomplete_payload, headers=headers)
    
    if resp.status_code == 400:
        detail = resp.json().get("detail", "")
        if detail.startswith("Complete the full onboarding before creating the login. Missing:"):
            expected_missing = ["Region", "GSTIN", "PAN", "Shop / Trade License", 
                              "Bank Name", "Bank Account", "Bank IFSC", "At least one uploaded Document"]
            all_present = all(field in detail for field in expected_missing)
            log_test("Area 1a", "Incomplete onboarding rejected with proper error", 
                    all_present, f"Error message: {detail}")
        else:
            log_test("Area 1a", "Incomplete onboarding rejected", False, 
                    f"Wrong error message: {detail}")
    else:
        log_test("Area 1a", "Incomplete onboarding rejected", False, 
                f"Expected 400, got {resp.status_code}")
    
    # Test 1b: Complete onboarding should succeed
    print("\n📋 Test 1b: Complete onboarding with all fields should succeed")
    complete_email = random_email()
    complete_payload = {
        "name": "Test Distributor Complete",
        "email": complete_email,
        "password": "Test@123",
        "phone": "9876543211",
        "address": "123 Test Street, Test City",
        "region": "North",
        "gstin": "29ABCDE1234F1Z5",
        "pan": "ABCDE1234F",
        "shop_license": "SL123456789",
        "bank_name": "Test Bank",
        "bank_account": "1234567890",
        "bank_ifsc": "TEST0001234",
        "documents": [
            {
                "name": "pan.jpg",
                "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            }
        ]
    }
    resp = requests.post(f"{BASE_URL}/dms/distributors", json=complete_payload, headers=headers)
    
    if resp.status_code in [200, 201]:
        data = resp.json()
        distributor_id = data.get("id")
        if distributor_id:
            created_items["distributors"].append(distributor_id)
            log_test("Area 1b", "Complete onboarding succeeded", True, 
                    f"Created distributor: {distributor_id}")
            
            # Test 1c: Verify the created distributor's login works
            print("\n📋 Test 1c: Verify created distributor can login")
            login_resp = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": complete_email, "password": "Test@123"}
            )
            if login_resp.status_code == 200:
                login_data = login_resp.json()
                if login_data.get("token") and login_data.get("user", {}).get("role") == "distributor":
                    log_test("Area 1c", "Distributor login successful", True, 
                            f"Role: {login_data['user']['role']}")
                else:
                    log_test("Area 1c", "Distributor login successful", False, 
                            "Token or role missing")
            else:
                log_test("Area 1c", "Distributor login successful", False, 
                        f"Login failed: {login_resp.status_code}")
        else:
            log_test("Area 1b", "Complete onboarding succeeded", False, 
                    "No distributor ID returned")
    else:
        log_test("Area 1b", "Complete onboarding succeeded", False, 
                f"Expected 200/201, got {resp.status_code}: {resp.text}")


def test_area_2_retailer_login_rules(token: str):
    """
    TEST AREA 2: POST /api/dms/retailers (owner) — login rule
    """
    print("\n" + "="*80)
    print("TEST AREA 2: Retailer Login Rules")
    print("="*80)
    
    headers = headers_with_token(token)
    
    # First, get a valid distributor_id
    print("\n📋 Getting valid distributor_id...")
    dist_resp = requests.get(f"{BASE_URL}/dms/distributors", headers=headers)
    if dist_resp.status_code != 200:
        print("❌ Failed to get distributors, cannot test retailer creation")
        return
    
    dist_data = dist_resp.json()
    distributors = dist_data.get("data", []) if isinstance(dist_data, dict) else dist_data
    if not distributors:
        print("❌ No distributors found, cannot test retailer creation")
        return
    
    distributor_id = distributors[0]["id"]
    print(f"✅ Using distributor_id: {distributor_id}")
    
    # Test 2a: No email (no login) should succeed
    print("\n📋 Test 2a: Retailer without email (no login) should succeed")
    no_email_payload = {
        "name": "Test Retailer No Login",
        "phone": "9876543220",
        "address": "456 Retailer Street",
        "distributor_id": distributor_id
    }
    resp = requests.post(f"{BASE_URL}/dms/retailers", json=no_email_payload, headers=headers)
    
    if resp.status_code in [200, 201]:
        data = resp.json()
        retailer_id = data.get("id")
        if retailer_id:
            created_items["retailers"].append(retailer_id)
            log_test("Area 2a", "Retailer without email succeeded", True, 
                    f"Created retailer: {retailer_id}, no login created")
        else:
            log_test("Area 2a", "Retailer without email succeeded", False, 
                    "No retailer ID returned")
    else:
        log_test("Area 2a", "Retailer without email succeeded", False, 
                f"Expected 200/201, got {resp.status_code}: {resp.text}")
    
    # Test 2b: With email but missing required fields should fail
    print("\n📋 Test 2b: Retailer with email but missing onboarding fields should fail")
    incomplete_login_payload = {
        "name": "Test Retailer Incomplete Login",
        "phone": "9876543221",
        "address": "789 Retailer Avenue",
        "distributor_id": distributor_id,
        "email": random_email()
        # Missing: region, gstin, shop_license, password, documents
    }
    resp = requests.post(f"{BASE_URL}/dms/retailers", json=incomplete_login_payload, headers=headers)
    
    if resp.status_code == 400:
        detail = resp.json().get("detail", "")
        if detail.startswith("Complete the full onboarding before creating the retailer login. Missing:"):
            expected_missing = ["Region", "GSTIN", "Shop License", "Login Password", 
                              "At least one uploaded Document"]
            all_present = all(field in detail for field in expected_missing)
            log_test("Area 2b", "Incomplete retailer login rejected", all_present, 
                    f"Error message: {detail}")
        else:
            log_test("Area 2b", "Incomplete retailer login rejected", False, 
                    f"Wrong error message: {detail}")
    else:
        log_test("Area 2b", "Incomplete retailer login rejected", False, 
                f"Expected 400, got {resp.status_code}")
    
    # Test 2c: With email and all required fields should succeed
    print("\n📋 Test 2c: Retailer with email and complete onboarding should succeed")
    complete_retailer_email = random_email()
    complete_login_payload = {
        "name": "Test Retailer Complete Login",
        "phone": "9876543222",
        "address": "101 Retailer Boulevard",
        "distributor_id": distributor_id,
        "email": complete_retailer_email,
        "password": "Retailer@123",
        "region": "South",
        "gstin": "29XYZAB5678G1Z5",
        "shop_license": "RSL987654321",
        "documents": [
            {
                "name": "shop_license.jpg",
                "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            }
        ]
    }
    resp = requests.post(f"{BASE_URL}/dms/retailers", json=complete_login_payload, headers=headers)
    
    if resp.status_code in [200, 201]:
        data = resp.json()
        retailer_id = data.get("id")
        if retailer_id:
            created_items["retailers"].append(retailer_id)
            log_test("Area 2c", "Complete retailer login succeeded", True, 
                    f"Created retailer: {retailer_id}")
            
            # Verify retailer can login
            print("   Verifying retailer login...")
            login_resp = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": complete_retailer_email, "password": "Retailer@123"}
            )
            if login_resp.status_code == 200:
                login_data = login_resp.json()
                if login_data.get("token") and login_data.get("user", {}).get("role") == "retailer":
                    log_test("Area 2c", "Retailer login authentication", True, 
                            f"Role: {login_data['user']['role']}")
                else:
                    log_test("Area 2c", "Retailer login authentication", False, 
                            "Token or role missing")
            else:
                log_test("Area 2c", "Retailer login authentication", False, 
                        f"Login failed: {login_resp.status_code}")
        else:
            log_test("Area 2c", "Complete retailer login succeeded", False, 
                    "No retailer ID returned")
    else:
        log_test("Area 2c", "Complete retailer login succeeded", False, 
                f"Expected 200/201, got {resp.status_code}: {resp.text}")


def test_area_3_owner_users_role_restriction(token: str):
    """
    TEST AREA 3: POST /api/dms/owner/users — role restriction
    """
    print("\n" + "="*80)
    print("TEST AREA 3: Owner Users Role Restriction")
    print("="*80)
    
    headers = headers_with_token(token)
    
    # Test 3a: role="distributor" should fail
    print("\n📋 Test 3a: Creating role=distributor should fail")
    dist_payload = {
        "name": "Test Distributor User",
        "email": random_email(),
        "password": "Test@123",
        "role": "distributor"
    }
    resp = requests.post(f"{BASE_URL}/dms/owner/users", json=dist_payload, headers=headers)
    
    if resp.status_code == 400:
        detail = resp.json().get("detail", "")
        if "Cannot create role=distributor from owner panel" in detail:
            log_test("Area 3a", "Distributor role blocked", True, f"Error: {detail}")
        else:
            log_test("Area 3a", "Distributor role blocked", False, f"Wrong error: {detail}")
    else:
        log_test("Area 3a", "Distributor role blocked", False, 
                f"Expected 400, got {resp.status_code}")
    
    # Test 3b: role="retailer" should fail
    print("\n📋 Test 3b: Creating role=retailer should fail")
    ret_payload = {
        "name": "Test Retailer User",
        "email": random_email(),
        "password": "Test@123",
        "role": "retailer"
    }
    resp = requests.post(f"{BASE_URL}/dms/owner/users", json=ret_payload, headers=headers)
    
    if resp.status_code == 400:
        detail = resp.json().get("detail", "")
        if "Cannot create role=retailer from owner panel" in detail:
            log_test("Area 3b", "Retailer role blocked", True, f"Error: {detail}")
        else:
            log_test("Area 3b", "Retailer role blocked", False, f"Wrong error: {detail}")
    else:
        log_test("Area 3b", "Retailer role blocked", False, 
                f"Expected 400, got {resp.status_code}")
    
    # Test 3c: role="salesperson" should succeed
    print("\n📋 Test 3c: Creating role=salesperson should succeed")
    sp_email = random_email()
    sp_payload = {
        "name": "Test Salesperson",
        "email": sp_email,
        "password": "Test@123",
        "role": "salesperson"
    }
    resp = requests.post(f"{BASE_URL}/dms/owner/users", json=sp_payload, headers=headers)
    
    if resp.status_code == 200:
        data = resp.json()
        if data.get("ok") and data.get("user"):
            user_id = data["user"].get("id")
            if user_id:
                created_items["users"].append(user_id)
                log_test("Area 3c", "Salesperson role created", True, 
                        f"Created user: {user_id}")
            else:
                log_test("Area 3c", "Salesperson role created", False, "No user ID returned")
        else:
            log_test("Area 3c", "Salesperson role created", False, "Invalid response structure")
    else:
        log_test("Area 3c", "Salesperson role created", False, 
                f"Expected 200, got {resp.status_code}: {resp.text}")


def test_area_4_owner_edit_users(token: str):
    """
    TEST AREA 4: PATCH /api/dms/owner/users/{uid} — owner edits ANY user incl self
    """
    print("\n" + "="*80)
    print("TEST AREA 4: Owner Edit Users (including self)")
    print("="*80)
    
    headers = headers_with_token(token)
    
    # Test 4a: Get owner's own user id and edit name
    print("\n📋 Test 4a: Owner edits own name")
    users_resp = requests.get(f"{BASE_URL}/dms/owner/users?role=owner", headers=headers)
    
    if users_resp.status_code != 200:
        log_test("Area 4a", "Get owner user", False, 
                f"Failed to get users: {users_resp.status_code}")
        return
    
    users_data = users_resp.json()
    users = users_data.get("data", []) if isinstance(users_data, dict) else users_data
    owner_user = None
    for u in users:
        if u.get("role") == "owner":
            owner_user = u
            break
    
    if not owner_user:
        log_test("Area 4a", "Get owner user", False, "No owner user found")
        return
    
    owner_uid = owner_user["id"]
    original_name = owner_user.get("name", "")
    print(f"   Owner user ID: {owner_uid}, Original name: {original_name}")
    
    # Change name
    new_name = "Rakesh Agarwal (Owner) - Test Edit"
    patch_resp = requests.patch(
        f"{BASE_URL}/dms/owner/users/{owner_uid}",
        json={"name": new_name},
        headers=headers
    )
    
    if patch_resp.status_code == 200:
        # Verify the change
        verify_resp = requests.get(f"{BASE_URL}/dms/owner/users?role=owner", headers=headers)
        if verify_resp.status_code == 200:
            verify_data = verify_resp.json()
            updated_users = verify_data.get("data", []) if isinstance(verify_data, dict) else verify_data
            updated_owner = next((u for u in updated_users if u["id"] == owner_uid), None)
            if updated_owner and updated_owner.get("name") == new_name:
                log_test("Area 4a", "Owner edits own name", True, 
                        f"Name changed to: {new_name}")
                
                # Restore original name
                print("   Restoring original name...")
                restore_resp = requests.patch(
                    f"{BASE_URL}/dms/owner/users/{owner_uid}",
                    json={"name": "Rakesh Agarwal (Owner)"},
                    headers=headers
                )
                if restore_resp.status_code == 200:
                    print("   ✅ Original name restored")
                else:
                    print(f"   ⚠️ Failed to restore name: {restore_resp.status_code}")
            else:
                log_test("Area 4a", "Owner edits own name", False, 
                        "Name not updated in database")
        else:
            log_test("Area 4a", "Owner edits own name", False, 
                    f"Failed to verify: {verify_resp.status_code}")
    else:
        log_test("Area 4a", "Owner edits own name", False, 
                f"PATCH failed: {patch_resp.status_code}: {patch_resp.text}")
    
    # Test 4b: Edit email of a non-owner user
    print("\n📋 Test 4b: Owner edits email of non-owner user")
    
    # Create a test user first
    test_user_email = random_email()
    create_resp = requests.post(
        f"{BASE_URL}/dms/owner/users",
        json={
            "name": "Test User For Email Edit",
            "email": test_user_email,
            "password": "Test@123",
            "role": "salesperson"
        },
        headers=headers
    )
    
    if create_resp.status_code != 200:
        log_test("Area 4b", "Create test user for email edit", False, 
                f"Failed to create: {create_resp.status_code}")
        return
    
    test_user_id = create_resp.json()["user"]["id"]
    created_items["users"].append(test_user_id)
    print(f"   Created test user: {test_user_id}, email: {test_user_email}")
    
    # Change email
    new_email = random_email()
    patch_resp = requests.patch(
        f"{BASE_URL}/dms/owner/users/{test_user_id}",
        json={"email": new_email},
        headers=headers
    )
    
    if patch_resp.status_code == 200:
        # Verify login works with new email
        login_resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": new_email, "password": "Test@123"}
        )
        if login_resp.status_code == 200:
            log_test("Area 4b", "Email change and login verification", True, 
                    f"New email: {new_email}, login successful")
            
            # Test duplicate email (should fail)
            print("   Testing duplicate email rejection...")
            dup_resp = requests.patch(
                f"{BASE_URL}/dms/owner/users/{test_user_id}",
                json={"email": OWNER_EMAIL},  # Try to use owner's email
                headers=headers
            )
            if dup_resp.status_code == 400:
                detail = dup_resp.json().get("detail", "")
                if "already in use" in detail or "already exists" in detail:
                    log_test("Area 4b", "Duplicate email rejected", True, 
                            f"Error: {detail}")
                else:
                    log_test("Area 4b", "Duplicate email rejected", False, 
                            f"Wrong error: {detail}")
            else:
                log_test("Area 4b", "Duplicate email rejected", False, 
                        f"Expected 400, got {dup_resp.status_code}")
        else:
            log_test("Area 4b", "Email change and login verification", False, 
                    f"Login with new email failed: {login_resp.status_code}")
    else:
        log_test("Area 4b", "Email change and login verification", False, 
                f"PATCH failed: {patch_resp.status_code}: {patch_resp.text}")


def test_area_5_single_owner_integrity(token: str):
    """
    TEST AREA 5: Single-owner integrity
    """
    print("\n" + "="*80)
    print("TEST AREA 5: Single-Owner Integrity")
    print("="*80)
    
    headers = headers_with_token(token)
    
    print("\n📋 Test 5: Verify exactly ONE owner exists")
    resp = requests.get(f"{BASE_URL}/dms/owner/users", headers=headers)
    
    if resp.status_code == 200:
        resp_data = resp.json()
        users = resp_data.get("data", []) if isinstance(resp_data, dict) else resp_data
        owners = [u for u in users if u.get("role") == "owner"]
        
        if len(owners) == 1:
            owner = owners[0]
            log_test("Area 5", "Single owner integrity", True, 
                    f"Exactly 1 owner found: {owner.get('name')} ({owner.get('email')})")
        else:
            log_test("Area 5", "Single owner integrity", False, 
                    f"Expected 1 owner, found {len(owners)}")
    else:
        log_test("Area 5", "Single owner integrity", False, 
                f"Failed to get users: {resp.status_code}")


def cleanup_test_data(token: str):
    """
    Clean up all test data created during testing
    """
    print("\n" + "="*80)
    print("CLEANUP: Deleting test data")
    print("="*80)
    
    headers = headers_with_token(token)
    
    # Delete test retailers
    print(f"\n🗑️  Deleting {len(created_items['retailers'])} test retailers...")
    for rid in created_items["retailers"]:
        resp = requests.delete(f"{BASE_URL}/dms/retailers/{rid}", headers=headers)
        if resp.status_code == 200:
            print(f"   ✅ Deleted retailer: {rid}")
        else:
            print(f"   ⚠️  Failed to delete retailer {rid}: {resp.status_code}")
    
    # Delete test distributors
    print(f"\n🗑️  Deleting {len(created_items['distributors'])} test distributors...")
    for did in created_items["distributors"]:
        resp = requests.delete(f"{BASE_URL}/dms/distributors/{did}", headers=headers)
        if resp.status_code == 200:
            print(f"   ✅ Deleted distributor: {did}")
        else:
            print(f"   ⚠️  Failed to delete distributor {did}: {resp.status_code}")
    
    # Delete test users
    print(f"\n🗑️  Deleting {len(created_items['users'])} test users...")
    for uid in created_items["users"]:
        resp = requests.delete(f"{BASE_URL}/dms/owner/users/{uid}", headers=headers)
        if resp.status_code == 200:
            print(f"   ✅ Deleted user: {uid}")
        else:
            print(f"   ⚠️  Failed to delete user {uid}: {resp.status_code}")
    
    print("\n✅ Cleanup complete")


def verify_owner_login_still_works():
    """
    Final verification that owner account still works
    """
    print("\n" + "="*80)
    print("FINAL VERIFICATION: Owner Login")
    print("="*80)
    
    print(f"\n🔐 Verifying owner login: {OWNER_EMAIL}")
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}
    )
    
    if resp.status_code == 200:
        data = resp.json()
        if data.get("token") and data.get("user", {}).get("role") == "owner":
            print("✅ Owner login still works correctly")
            log_test("Final", "Owner login verification", True, 
                    "Owner account functional after all tests")
        else:
            print("❌ Owner login response invalid")
            log_test("Final", "Owner login verification", False, 
                    "Invalid response structure")
    else:
        print(f"❌ Owner login failed: {resp.status_code}")
        log_test("Final", "Owner login verification", False, 
                f"Login failed: {resp.status_code}")


def print_summary():
    """
    Print test summary
    """
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    # Group by area
    areas = {}
    for result in test_results:
        area = result["area"]
        if area not in areas:
            areas[area] = {"passed": 0, "failed": 0, "tests": []}
        if result["passed"]:
            areas[area]["passed"] += 1
        else:
            areas[area]["failed"] += 1
        areas[area]["tests"].append(result)
    
    # Print by area
    total_passed = 0
    total_failed = 0
    
    for area, data in sorted(areas.items()):
        passed = data["passed"]
        failed = data["failed"]
        total = passed + failed
        total_passed += passed
        total_failed += failed
        
        status = "✅ PASS" if failed == 0 else "❌ FAIL"
        print(f"\n{status} | {area}: {passed}/{total} tests passed")
        
        # Show failed tests
        if failed > 0:
            for test in data["tests"]:
                if not test["passed"]:
                    print(f"   ❌ {test['test']}")
                    if test["details"]:
                        print(f"      {test['details']}")
    
    # Overall summary
    print("\n" + "="*80)
    total = total_passed + total_failed
    percentage = (total_passed / total * 100) if total > 0 else 0
    print(f"OVERALL: {total_passed}/{total} tests passed ({percentage:.1f}%)")
    print("="*80)
    
    # Created items summary
    print(f"\nTest items created:")
    print(f"  - Distributors: {len(created_items['distributors'])}")
    print(f"  - Retailers: {len(created_items['retailers'])}")
    print(f"  - Users: {len(created_items['users'])}")


def main():
    """
    Main test execution
    """
    print("="*80)
    print("GO OIL DMS - Owner-Managed Logins + Full-Process Onboarding Tests")
    print("="*80)
    print(f"Backend URL: {BASE_URL}")
    print(f"Owner: {OWNER_EMAIL}")
    
    try:
        # Get owner token
        token = get_owner_token()
        
        # Run all test areas
        test_area_1_distributor_onboarding(token)
        test_area_2_retailer_login_rules(token)
        test_area_3_owner_users_role_restriction(token)
        test_area_4_owner_edit_users(token)
        test_area_5_single_owner_integrity(token)
        
        # Cleanup
        cleanup_test_data(token)
        
        # Final verification
        verify_owner_login_still_works()
        
        # Print summary
        print_summary()
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
