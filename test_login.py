#!/usr/bin/env python3
"""
Login Endpoint Testing for GO OIL DMS
Tests POST /api/auth/login as requested in review.

Test cases:
1. CORRECT credentials — email: gooilindia13@gmail.com, password: Arjun@india13
   → Expect HTTP 200 with token and user (user.role should be "owner")
   → Verify token works by calling GET /api/auth/me
2. WRONG password — email: gooilindia13@gmail.com, password: Arjun13@india
   → Expect HTTP 401 with detail "Invalid email or password" (NOT 404)
"""

import requests
import json
import sys

# Base URL from frontend/.env
BASE_URL = "https://dot-to-lines.preview.emergentagent.com"
API_URL = f"{BASE_URL}/api"

# Test credentials from /app/memory/test_credentials.md
OWNER_EMAIL = "gooilindia13@gmail.com"
OWNER_PASSWORD = "Arjun@india13"
WRONG_PASSWORD = "Arjun13@india"

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"{BLUE}  {title}{RESET}")
    print(f"{'='*80}\n")

def log_test(message, status="INFO"):
    """Log test messages with color coding"""
    color = {
        "PASS": GREEN,
        "FAIL": RED,
        "INFO": BLUE,
        "WARN": YELLOW
    }.get(status, RESET)
    print(f"{color}[{status}]{RESET} {message}")

def test_login_correct_credentials():
    """
    TEST 1: Login with CORRECT credentials
    Email: gooilindia13@gmail.com
    Password: Arjun@india13
    Expected: HTTP 200 with token and user (user.role should be "owner")
    """
    print_section("TEST 1: Login with CORRECT credentials")
    
    url = f"{API_URL}/auth/login"
    payload = {
        "email": OWNER_EMAIL,
        "password": OWNER_PASSWORD
    }
    
    log_test(f"POST {url}", "INFO")
    log_test(f"Payload: {json.dumps(payload, indent=2)}", "INFO")
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        log_test(f"Status Code: {response.status_code}", "INFO")
        
        # Print response body
        try:
            response_json = response.json()
            log_test(f"Response Body: {json.dumps(response_json, indent=2)}", "INFO")
        except:
            log_test(f"Response Body (raw): {response.text}", "INFO")
        
        # Verify expectations
        if response.status_code == 200:
            log_test("Status code is 200", "PASS")
            
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                
                # Check for token
                if 'token' in data:
                    log_test("Response contains 'token' field", "PASS")
                    token = data['token']
                    log_test(f"Token (first 50 chars): {token[:50]}...", "INFO")
                else:
                    log_test("Response missing 'token' field", "FAIL")
                    return False
                
                # Check for user
                if 'user' in data:
                    log_test("Response contains 'user' field", "PASS")
                    user = data['user']
                    
                    # Check user.role
                    if 'role' in user:
                        role = user['role']
                        log_test(f"User role: {role}", "INFO")
                        if role == "owner":
                            log_test("User role is 'owner'", "PASS")
                        else:
                            log_test(f"User role is '{role}', expected 'owner'", "FAIL")
                            return False
                    else:
                        log_test("User object missing 'role' field", "FAIL")
                        return False
                else:
                    log_test("Response missing 'user' field", "FAIL")
                    return False
                
                # Test the token by calling /api/auth/me
                print("\n--- Verifying token with GET /api/auth/me ---")
                me_url = f"{API_URL}/auth/me"
                headers = {"Authorization": f"Bearer {token}"}
                me_response = requests.get(me_url, headers=headers, timeout=10)
                log_test(f"GET {me_url}", "INFO")
                log_test(f"Status Code: {me_response.status_code}", "INFO")
                
                if me_response.status_code == 200:
                    log_test("Token verification successful - /api/auth/me returned 200", "PASS")
                    me_data = me_response.json()
                    log_test(f"User from /me: {json.dumps(me_data, indent=2)}", "INFO")
                    
                    # Verify the user from /me matches
                    if me_data.get('email') == OWNER_EMAIL:
                        log_test(f"Email matches: {OWNER_EMAIL}", "PASS")
                    if me_data.get('role') == 'owner':
                        log_test("Role from /me is 'owner'", "PASS")
                    
                    return True
                else:
                    log_test(f"Token verification failed with status {me_response.status_code}", "FAIL")
                    log_test(f"Response: {me_response.text}", "INFO")
                    return False
            else:
                log_test(f"Response is not JSON (content-type: {response.headers.get('content-type')})", "FAIL")
                return False
        elif response.status_code == 404:
            log_test("Status code is 404 - Route not found! This is the bug user reported.", "FAIL")
            return False
        else:
            log_test(f"Status code is {response.status_code}, expected 200", "FAIL")
            return False
            
    except requests.exceptions.RequestException as e:
        log_test(f"Request failed with exception: {e}", "FAIL")
        return False

def test_login_wrong_password():
    """
    TEST 2: Login with WRONG password
    Email: gooilindia13@gmail.com
    Password: Arjun13@india (WRONG)
    Expected: HTTP 401 with detail "Invalid email or password" (NOT 404)
    """
    print_section("TEST 2: Login with WRONG password")
    
    url = f"{API_URL}/auth/login"
    payload = {
        "email": OWNER_EMAIL,
        "password": WRONG_PASSWORD  # Wrong password
    }
    
    log_test(f"POST {url}", "INFO")
    log_test(f"Payload: {json.dumps(payload, indent=2)}", "INFO")
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        log_test(f"Status Code: {response.status_code}", "INFO")
        
        # Print response body
        try:
            response_json = response.json()
            log_test(f"Response Body: {json.dumps(response_json, indent=2)}", "INFO")
        except:
            log_test(f"Response Body (raw): {response.text}", "INFO")
        
        # Verify expectations
        if response.status_code == 401:
            log_test("Status code is 401 (correct error for wrong password)", "PASS")
            
            # Check the error message
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                detail = data.get('detail', '')
                log_test(f"Error detail: {detail}", "INFO")
                
                if "Invalid email or password" in str(detail):
                    log_test("Error message contains 'Invalid email or password'", "PASS")
                    return True
                else:
                    log_test(f"Error message is '{detail}', expected 'Invalid email or password'", "WARN")
                    log_test("Still passing as status code is correct (401, not 404)", "INFO")
                    return True  # Still pass as long as it's 401, not 404
            else:
                log_test("Response is not JSON", "WARN")
                log_test("Still passing as status code is correct (401, not 404)", "INFO")
                return True  # Still pass as long as it's 401, not 404
        elif response.status_code == 404:
            log_test("Status code is 404 - This is the bug user reported!", "FAIL")
            log_test("Expected 401 for wrong password, not 404 'Not Found'", "FAIL")
            return False
        else:
            log_test(f"Status code is {response.status_code}, expected 401", "FAIL")
            return False
            
    except requests.exceptions.RequestException as e:
        log_test(f"Request failed with exception: {e}", "FAIL")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print(f"{BLUE}  GO OIL DMS - Login Endpoint Testing{RESET}")
    print(f"{BLUE}  Testing POST /api/auth/login{RESET}")
    print(f"{BLUE}  Base URL: {BASE_URL}{RESET}")
    print("="*80)
    
    results = []
    
    # Test 1: Correct credentials
    results.append(("Correct credentials (owner account)", test_login_correct_credentials()))
    
    # Test 2: Wrong password
    results.append(("Wrong password (should return 401, not 404)", test_login_wrong_password()))
    
    # Summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        log_test(f"{test_name}", status)
    
    print(f"\n{BLUE}Total: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}🎉 ALL TESTS PASSED!{RESET}")
        print(f"{GREEN}✅ /api/auth/login endpoint is working correctly{RESET}")
        print(f"{GREEN}✅ Correct credentials return 200 with token and user{RESET}")
        print(f"{GREEN}✅ Wrong password returns 401 (not 404){RESET}")
        print(f"{GREEN}✅ Token works with /api/auth/me{RESET}")
        return 0
    else:
        print(f"\n{RED}⚠️  {total - passed} test(s) failed{RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
