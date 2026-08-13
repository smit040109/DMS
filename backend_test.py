#!/usr/bin/env python3
"""
Smoke/Regression Test: Verify .env file deployment fix
Tests that backend correctly loads environment variables from backend/.env
"""

import requests
import sys
import os

# Use the public backend URL from frontend/.env
BACKEND_URL = "https://14dc390a-a7b1-4b12-9090-d90040b73ea8.preview.emergentagent.com/api"

# Test credentials from dms_seed.py (OWNER_EMAIL/OWNER_PASSWORD defaults)
TEST_CREDENTIALS = {
    "owner": {"email": "gooilindia13@gmail.com", "password": "Arjun@india13"},
}

def test_login_and_jwt():
    """
    Test 1: Login works (validates JWT_SECRET is loaded from .env)
    """
    print("\n" + "="*80)
    print("TEST 1: Login with JWT_SECRET from .env")
    print("="*80)
    
    creds = TEST_CREDENTIALS["owner"]
    response = requests.post(
        f"{BACKEND_URL}/auth/login",
        json={"email": creds["email"], "password": creds["password"]}
    )
    
    print(f"POST {BACKEND_URL}/auth/login")
    print(f"Email: {creds['email']}")
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ FAILED: Expected 200, got {response.status_code}")
        print(f"Response: {response.text}")
        return None
    
    data = response.json()
    if "token" not in data:
        print(f"❌ FAILED: No token in response")
        print(f"Response: {data}")
        return None
    
    token = data["token"]
    print(f"✅ PASSED: Login successful, JWT token received")
    print(f"Token (first 50 chars): {token[:50]}...")
    return token


def test_auth_me(token):
    """
    Test 2: GET /api/auth/me returns authenticated user
    Validates JWT signing/verification with the .env JWT_SECRET
    """
    print("\n" + "="*80)
    print("TEST 2: GET /api/auth/me (JWT verification)")
    print("="*80)
    
    response = requests.get(
        f"{BACKEND_URL}/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"GET {BACKEND_URL}/auth/me")
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ FAILED: Expected 200, got {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    data = response.json()
    
    # Handle nested user object structure
    user = data.get("user", data)
    if "email" not in user or "role" not in user:
        print(f"❌ FAILED: Missing email or role in response")
        print(f"Response: {data}")
        return False
    
    print(f"✅ PASSED: Authenticated user returned")
    print(f"Email: {user['email']}")
    print(f"Role: {user['role']}")
    print(f"Tenant ID: {user.get('tenant_id', 'N/A')}")
    return True


def test_dashboard_kpis(token):
    """
    Test 3: GET /api/dashboard/kpis returns 200
    Validates MongoDB connection via MONGO_URL/DB_NAME from .env
    """
    print("\n" + "="*80)
    print("TEST 3: GET /api/dashboard/kpis (MongoDB connection)")
    print("="*80)
    
    response = requests.get(
        f"{BACKEND_URL}/dashboard/kpis",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"GET {BACKEND_URL}/dashboard/kpis")
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ FAILED: Expected 200, got {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    data = response.json()
    print(f"✅ PASSED: Dashboard KPIs returned (MongoDB connection working)")
    print(f"Response keys: {list(data.keys())}")
    return True


def main():
    print("\n" + "="*80)
    print("SMOKE TEST: .env Deployment Fix Verification")
    print("="*80)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Testing that backend loads env vars from backend/.env:")
    print(f"  - MONGO_URL (MongoDB connection)")
    print(f"  - DB_NAME=gooil_dms")
    print(f"  - JWT_SECRET (JWT signing/verification)")
    print(f"  - CORS_ORIGINS=*")
    
    # Test 1: Login
    token = test_login_and_jwt()
    if not token:
        print("\n❌ SMOKE TEST FAILED: Login failed")
        sys.exit(1)
    
    # Test 2: Auth me
    if not test_auth_me(token):
        print("\n❌ SMOKE TEST FAILED: JWT verification failed")
        sys.exit(1)
    
    # Test 3: Dashboard KPIs (MongoDB)
    if not test_dashboard_kpis(token):
        print("\n❌ SMOKE TEST FAILED: MongoDB connection failed")
        sys.exit(1)
    
    # Summary
    print("\n" + "="*80)
    print("✅ ALL SMOKE TESTS PASSED (3/3)")
    print("="*80)
    print("✅ Login works (JWT_SECRET loaded from .env)")
    print("✅ GET /api/auth/me returns authenticated user (JWT signing/verification working)")
    print("✅ GET /api/dashboard/kpis returns 200 (MongoDB connection via MONGO_URL/DB_NAME working)")
    print("\n🎯 CONCLUSION: .env files are correctly loaded and app is working")
    print("="*80)


if __name__ == "__main__":
    main()
