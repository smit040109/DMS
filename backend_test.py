#!/usr/bin/env python3
"""GO OIL DMS — Backend Testing Suite for Parts B/C/D + Light Regression.

Tests:
- Part B: Performance (caching, response times)
- Part C: Security (rate limiting, headers, RBAC, password strength, health check)
- Part D: Exports (35 collections, 4 formats, auth)
- Light Regression: Part A functionality (login, exception scanner, KPI, party360)
"""
import requests
import time
import json
from typing import Dict, Any, List, Tuple

# Base URL from frontend/.env
BASE_URL = "https://38026b09-a311-4ef3-8159-6cb799593d83.preview.emergentagent.com/api"

# Test credentials (all use password: GoOil@2026)
CREDENTIALS = {
    "admin": {"email": "admin@gooil.com", "password": "GoOil@2026"},
    "customer": {"email": "customer@gooil.com", "password": "GoOil@2026"},
    "company_admin": {"email": "company@gooil.com", "password": "GoOil@2026"},
    "regional_manager": {"email": "regional@gooil.com", "password": "GoOil@2026"},
    "sales_executive": {"email": "sales@gooil.com", "password": "GoOil@2026"},
    "distributor": {"email": "distributor@gooil.com", "password": "GoOil@2026"},
    "distributor_accountant": {"email": "accountant@gooil.com", "password": "GoOil@2026"},
    "retailer": {"email": "retailer@gooil.com", "password": "GoOil@2026"},
}

# Test results storage
test_results = {
    "part_b_performance": [],
    "part_c_security": [],
    "part_d_exports": [],
    "part_a_regression": [],
}


def log_test(category: str, test_name: str, passed: bool, details: str = "", priority: str = "MEDIUM"):
    """Log test result."""
    result = {
        "test": test_name,
        "passed": passed,
        "details": details,
        "priority": priority,
    }
    test_results[category].append(result)
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} [{priority}] {test_name}: {details}")


def login(role: str = "admin") -> Tuple[str, Dict[str, Any]]:
    """Login and return (token, user)."""
    creds = CREDENTIALS.get(role)
    if not creds:
        raise ValueError(f"Unknown role: {role}")
    
    resp = requests.post(f"{BASE_URL}/auth/login", json=creds, timeout=10)
    if resp.status_code != 200:
        raise Exception(f"Login failed for {role}: {resp.status_code} {resp.text}")
    
    data = resp.json()
    return data["token"], data["user"]


def get_headers(token: str) -> Dict[str, str]:
    """Return auth headers."""
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# PART B — PERFORMANCE TESTS
# ============================================================================

def test_part_b_performance():
    """Test Part B: Performance (caching, response times)."""
    print("\n" + "="*80)
    print("PART B — PERFORMANCE TESTS")
    print("="*80)
    
    token, user = login("admin")
    headers = get_headers(token)
    
    # Test 1: GET /api/analytics/dimensions — should respond < 200ms both cold and warm (cached 60s)
    print("\n[B1] Testing /api/analytics/dimensions caching and response time...")
    
    # Cold call
    start = time.time()
    resp = requests.get(f"{BASE_URL}/analytics/dimensions", headers=headers, timeout=10)
    cold_time = (time.time() - start) * 1000
    
    if resp.status_code == 200:
        data = resp.json()
        branches = len(data.get("branches", []))
        distributors = len(data.get("distributors", []))
        
        # Warm call (should be cached)
        start = time.time()
        resp2 = requests.get(f"{BASE_URL}/analytics/dimensions", headers=headers, timeout=10)
        warm_time = (time.time() - start) * 1000
        
        # Check response times
        cold_ok = cold_time < 200
        warm_ok = warm_time < 200
        
        details = f"Cold: {cold_time:.0f}ms, Warm: {warm_time:.0f}ms (cached 60s). Branches: {branches}, Distributors: {distributors}"
        passed = resp.status_code == 200 and cold_ok and warm_ok
        log_test("part_b_performance", "Dimensions endpoint caching", passed, details, "HIGH")
    else:
        log_test("part_b_performance", "Dimensions endpoint caching", False, 
                f"Failed: {resp.status_code} {resp.text[:200]}", "HIGH")
    
    # Test 2: GET /api/analytics/scorecards/distributor — should respond < 300ms warm (cached 45s)
    print("\n[B2] Testing /api/analytics/scorecards/distributor caching and response time...")
    
    # Cold call
    start = time.time()
    resp = requests.get(f"{BASE_URL}/analytics/scorecards/distributor", headers=headers, timeout=10)
    cold_time = (time.time() - start) * 1000
    
    if resp.status_code == 200:
        data = resp.json()
        rows = len(data.get("rows", []))
        
        # Warm call (should be cached)
        start = time.time()
        resp2 = requests.get(f"{BASE_URL}/analytics/scorecards/distributor", headers=headers, timeout=10)
        warm_time = (time.time() - start) * 1000
        
        warm_ok = warm_time < 300
        
        details = f"Cold: {cold_time:.0f}ms, Warm: {warm_time:.0f}ms (cached 45s). Rows: {rows}"
        passed = resp.status_code == 200 and warm_ok
        log_test("part_b_performance", "Scorecards endpoint caching", passed, details, "HIGH")
    else:
        log_test("part_b_performance", "Scorecards endpoint caching", False,
                f"Failed: {resp.status_code} {resp.text[:200]}", "HIGH")
    
    # Test 3: Verify all Phase 1-4 endpoints still return < 3s response time
    print("\n[B3] Testing Phase 1-4 endpoint response times (< 3s)...")
    
    endpoints = [
        ("/collections/branches", "Branches"),
        ("/collections/products", "Products"),
        ("/collections/primary-orders", "Primary Orders"),
        ("/collections/invoices", "Invoices"),
        ("/analytics/kpi/executive?range=month", "Executive KPI"),
        ("/analytics/party360/distributor/dist-100", "Party 360"),
        ("/analytics/sales", "Sales Analytics"),
        ("/analytics/inventory", "Inventory Analytics"),
        ("/analytics/finance", "Finance Analytics"),
        ("/analytics/alerts", "Business Alerts"),
    ]
    
    slow_endpoints = []
    for endpoint, name in endpoints:
        start = time.time()
        resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=10)
        elapsed = (time.time() - start) * 1000
        
        if elapsed > 3000:
            slow_endpoints.append(f"{name} ({elapsed:.0f}ms)")
        
        # Categorize response time
        if elapsed < 100:
            bracket = "fast <100ms"
        elif elapsed < 500:
            bracket = "ok <500ms"
        elif elapsed < 3000:
            bracket = "slow <3s"
        else:
            bracket = "terrible >3s"
        
        print(f"  {name}: {elapsed:.0f}ms [{bracket}]")
    
    if slow_endpoints:
        log_test("part_b_performance", "Phase 1-4 response times", False,
                f"Slow endpoints (>3s): {', '.join(slow_endpoints)}", "CRITICAL")
    else:
        log_test("part_b_performance", "Phase 1-4 response times", True,
                "All endpoints < 3s", "HIGH")


# ============================================================================
# PART C — SECURITY TESTS
# ============================================================================

def test_part_c_security():
    """Test Part C: Security (rate limiting, headers, RBAC, password strength, health check)."""
    print("\n" + "="*80)
    print("PART C — SECURITY TESTS")
    print("="*80)
    
    # Test 1: Rate limiting on /auth/login (10/minute)
    print("\n[C1] Testing rate limiting on /auth/login (10/minute)...")
    
    bad_creds = {"email": "admin@gooil.com", "password": "wrongpassword"}
    rate_limited = False
    attempts = 0
    
    for i in range(12):
        resp = requests.post(f"{BASE_URL}/auth/login", json=bad_creds, timeout=10)
        attempts += 1
        if resp.status_code == 429:
            rate_limited = True
            break
    
    if rate_limited:
        log_test("part_c_security", "Login rate limiting", True,
                f"429 received after {attempts} attempts (expected ~11)", "HIGH")
    else:
        log_test("part_c_security", "Login rate limiting", False,
                f"No 429 after {attempts} attempts", "CRITICAL")
    
    # Wait a bit to avoid rate limit for next tests
    time.sleep(2)
    
    # Test 2: Rate limiting on /auth/register (5/minute)
    print("\n[C2] Testing rate limiting on /auth/register (5/minute)...")
    
    rate_limited = False
    attempts = 0
    
    for i in range(7):
        test_user = {
            "email": f"test{i}_{int(time.time())}@example.com",
            "password": "TestPass123",
            "name": f"Test User {i}",
            "role": "customer"
        }
        resp = requests.post(f"{BASE_URL}/auth/register", json=test_user, timeout=10)
        attempts += 1
        if resp.status_code == 429:
            rate_limited = True
            break
    
    if rate_limited:
        log_test("part_c_security", "Register rate limiting", True,
                f"429 received after {attempts} attempts (expected ~6)", "HIGH")
    else:
        log_test("part_c_security", "Register rate limiting", False,
                f"No 429 after {attempts} attempts", "CRITICAL")
    
    # Wait a bit to avoid rate limit
    time.sleep(2)
    
    # Test 3: Security headers on /api/health
    print("\n[C3] Testing security headers on /api/health...")
    
    resp = requests.get(f"{BASE_URL}/health", timeout=10)
    headers = resp.headers
    
    required_headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": lambda v: v is not None,  # Just check it exists
    }
    
    missing_headers = []
    for header, expected in required_headers.items():
        value = headers.get(header)
        if callable(expected):
            if not expected(value):
                missing_headers.append(header)
        elif value != expected:
            missing_headers.append(f"{header} (got: {value})")
    
    if missing_headers:
        log_test("part_c_security", "Security headers", False,
                f"Missing/incorrect: {', '.join(missing_headers)}", "HIGH")
    else:
        log_test("part_c_security", "Security headers", True,
                "All required headers present", "HIGH")
    
    # Test 4: RBAC - customer can't access /admin/users
    print("\n[C4] Testing RBAC - customer can't access /admin/users...")
    
    customer_token, _ = login("customer")
    customer_headers = get_headers(customer_token)
    
    resp = requests.get(f"{BASE_URL}/admin/users", headers=customer_headers, timeout=10)
    
    if resp.status_code == 403:
        log_test("part_c_security", "RBAC - customer denied /admin/users", True,
                "403 Forbidden as expected", "HIGH")
    else:
        log_test("part_c_security", "RBAC - customer denied /admin/users", False,
                f"Expected 403, got {resp.status_code}", "CRITICAL")
    
    # Test 5: RBAC - admin can access /admin/users
    print("\n[C5] Testing RBAC - admin can access /admin/users...")
    
    admin_token, _ = login("admin")
    admin_headers = get_headers(admin_token)
    
    resp = requests.get(f"{BASE_URL}/admin/users", headers=admin_headers, timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        count = data.get("count", 0)
        log_test("part_c_security", "RBAC - admin allowed /admin/users", True,
                f"200 OK, {count} users returned", "HIGH")
    else:
        log_test("part_c_security", "RBAC - admin allowed /admin/users", False,
                f"Expected 200, got {resp.status_code}", "CRITICAL")
    
    # Test 6: RBAC - customer can't POST to /collections/products
    print("\n[C6] Testing RBAC - customer can't POST to /collections/products...")
    
    test_product = {"name": "Test Product", "code": "TEST-001"}
    resp = requests.post(f"{BASE_URL}/collections/products", json=test_product,
                        headers=customer_headers, timeout=10)
    
    if resp.status_code == 403:
        log_test("part_c_security", "RBAC - customer denied POST /collections", True,
                "403 Forbidden as expected", "HIGH")
    else:
        log_test("part_c_security", "RBAC - customer denied POST /collections", False,
                f"Expected 403, got {resp.status_code}", "CRITICAL")
    
    # Test 7: RBAC - admin can POST to /collections/products
    print("\n[C7] Testing RBAC - admin can POST to /collections/products...")
    
    test_product = {
        "name": f"Test Product {int(time.time())}",
        "code": f"TEST-{int(time.time())}",
        "category": "Lubricants"
    }
    resp = requests.post(f"{BASE_URL}/collections/products", json=test_product,
                        headers=admin_headers, timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        log_test("part_c_security", "RBAC - admin allowed POST /collections", True,
                f"200 OK, product created: {data.get('id')}", "HIGH")
    else:
        log_test("part_c_security", "RBAC - admin allowed POST /collections", False,
                f"Expected 200, got {resp.status_code}: {resp.text[:200]}", "HIGH")
    
    # Test 8: RBAC - customer can GET /collections/products
    print("\n[C8] Testing RBAC - customer can GET /collections/products...")
    
    resp = requests.get(f"{BASE_URL}/collections/products", headers=customer_headers, timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        count = data.get("count", 0)
        log_test("part_c_security", "RBAC - customer allowed GET /collections", True,
                f"200 OK, {count} products returned", "MEDIUM")
    else:
        log_test("part_c_security", "RBAC - customer allowed GET /collections", False,
                f"Expected 200, got {resp.status_code}", "HIGH")
    
    # Test 9: Password strength validation - weak password
    print("\n[C9] Testing password strength validation - weak password...")
    
    weak_user = {
        "email": f"weak_{int(time.time())}@example.com",
        "password": "weak",
        "name": "Weak User",
        "role": "customer"
    }
    resp = requests.post(f"{BASE_URL}/auth/register", json=weak_user, timeout=10)
    
    if resp.status_code == 400:
        log_test("part_c_security", "Password strength - weak rejected", True,
                f"400 Bad Request: {resp.json().get('detail', '')[:100]}", "HIGH")
    else:
        log_test("part_c_security", "Password strength - weak rejected", False,
                f"Expected 400, got {resp.status_code}", "HIGH")
    
    # Test 10: Password strength validation - strong password
    print("\n[C10] Testing password strength validation - strong password...")
    
    strong_user = {
        "email": f"strong_{int(time.time())}@example.com",
        "password": "AllUpper2026",
        "name": "Strong User",
        "role": "customer"
    }
    resp = requests.post(f"{BASE_URL}/auth/register", json=strong_user, timeout=10)
    
    if resp.status_code in [200, 400]:  # 400 if email exists is also acceptable
        if resp.status_code == 200:
            log_test("part_c_security", "Password strength - strong accepted", True,
                    "200 OK, user created", "MEDIUM")
        else:
            # Check if it's email exists error
            detail = resp.json().get("detail", "")
            if "already registered" in detail.lower():
                log_test("part_c_security", "Password strength - strong accepted", True,
                        "Password validation passed (email exists)", "MEDIUM")
            else:
                log_test("part_c_security", "Password strength - strong accepted", False,
                        f"400 but not email exists: {detail}", "HIGH")
    else:
        log_test("part_c_security", "Password strength - strong accepted", False,
                f"Expected 200/400, got {resp.status_code}", "HIGH")
    
    # Test 11: Health check endpoint
    print("\n[C11] Testing health check endpoint...")
    
    resp = requests.get(f"{BASE_URL}/health", timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        status = data.get("status")
        db = data.get("db")
        
        if status == "ok" and db == "connected":
            log_test("part_c_security", "Health check endpoint", True,
                    f"200 OK: status={status}, db={db}", "MEDIUM")
        else:
            log_test("part_c_security", "Health check endpoint", False,
                    f"200 but wrong data: {data}", "HIGH")
    else:
        log_test("part_c_security", "Health check endpoint", False,
                f"Expected 200, got {resp.status_code}", "HIGH")


# ============================================================================
# PART D — EXPORTS TESTS
# ============================================================================

def test_part_d_exports():
    """Test Part D: Exports (35 collections, 4 formats, auth)."""
    print("\n" + "="*80)
    print("PART D — EXPORTS TESTS")
    print("="*80)
    
    token, user = login("admin")
    headers = get_headers(token)
    
    # Test 1: GET /api/exports/collections — returns array of 35 exportable resources
    print("\n[D1] Testing /api/exports/collections...")
    
    resp = requests.get(f"{BASE_URL}/exports/collections", headers=headers, timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        collections = data.get("data", [])
        count = len(collections)
        
        if count == 35:
            log_test("part_d_exports", "Exports collections list", True,
                    f"35 exportable resources returned", "HIGH")
        else:
            log_test("part_d_exports", "Exports collections list", False,
                    f"Expected 35 resources, got {count}", "HIGH")
    else:
        log_test("part_d_exports", "Exports collections list", False,
                f"Expected 200, got {resp.status_code}", "CRITICAL")
    
    # Test 2: GET /api/exports/products?format=csv — 200 with content-type text/csv
    print("\n[D2] Testing /api/exports/products?format=csv...")
    
    resp = requests.get(f"{BASE_URL}/exports/products?format=csv", headers=headers, timeout=10)
    
    if resp.status_code == 200:
        content_type = resp.headers.get("Content-Type", "")
        content = resp.text
        
        # Check if first line looks like CSV headers
        first_line = content.split("\n")[0] if content else ""
        has_headers = "," in first_line
        
        if "text/csv" in content_type and has_headers:
            log_test("part_d_exports", "Export CSV format", True,
                    f"text/csv, {len(content)} bytes, headers: {first_line[:50]}", "HIGH")
        else:
            log_test("part_d_exports", "Export CSV format", False,
                    f"Content-Type: {content_type}, headers: {has_headers}", "HIGH")
    else:
        log_test("part_d_exports", "Export CSV format", False,
                f"Expected 200, got {resp.status_code}", "CRITICAL")
    
    # Test 3: GET /api/exports/products?format=xlsx — 200 with correct content-type
    print("\n[D3] Testing /api/exports/products?format=xlsx...")
    
    resp = requests.get(f"{BASE_URL}/exports/products?format=xlsx", headers=headers, timeout=10)
    
    if resp.status_code == 200:
        content_type = resp.headers.get("Content-Type", "")
        content = resp.content
        
        # Check if it's a valid zip (xlsx is a zip file)
        is_zip = content[:4] == b'PK\x03\x04'
        
        if "application/vnd.openxmlformats" in content_type and is_zip:
            log_test("part_d_exports", "Export XLSX format", True,
                    f"Valid XLSX, {len(content)} bytes", "HIGH")
        else:
            log_test("part_d_exports", "Export XLSX format", False,
                    f"Content-Type: {content_type}, is_zip: {is_zip}", "HIGH")
    else:
        log_test("part_d_exports", "Export XLSX format", False,
                f"Expected 200, got {resp.status_code}", "CRITICAL")
    
    # Test 4: GET /api/exports/invoices?format=pdf — 200 with content-type application/pdf
    print("\n[D4] Testing /api/exports/invoices?format=pdf...")
    
    resp = requests.get(f"{BASE_URL}/exports/invoices?format=pdf", headers=headers, timeout=10)
    
    if resp.status_code == 200:
        content_type = resp.headers.get("Content-Type", "")
        content = resp.content
        
        # Check if it starts with %PDF
        is_pdf = content[:4] == b'%PDF'
        
        if "application/pdf" in content_type and is_pdf:
            log_test("part_d_exports", "Export PDF format", True,
                    f"Valid PDF, {len(content)} bytes", "HIGH")
        else:
            log_test("part_d_exports", "Export PDF format", False,
                    f"Content-Type: {content_type}, is_pdf: {is_pdf}", "HIGH")
    else:
        log_test("part_d_exports", "Export PDF format", False,
                f"Expected 200, got {resp.status_code}", "CRITICAL")
    
    # Test 5: GET /api/exports/outstanding?format=print — 200 with content-type text/html
    print("\n[D5] Testing /api/exports/outstanding?format=print...")
    
    resp = requests.get(f"{BASE_URL}/exports/outstanding?format=print", headers=headers, timeout=10)
    
    if resp.status_code == 200:
        content_type = resp.headers.get("Content-Type", "")
        content = resp.text
        
        has_table = "<table>" in content.lower()
        
        if "text/html" in content_type and has_table:
            log_test("part_d_exports", "Export Print HTML format", True,
                    f"Valid HTML with <table>, {len(content)} bytes", "HIGH")
        else:
            log_test("part_d_exports", "Export Print HTML format", False,
                    f"Content-Type: {content_type}, has_table: {has_table}", "HIGH")
    else:
        log_test("part_d_exports", "Export Print HTML format", False,
                f"Expected 200, got {resp.status_code}", "CRITICAL")
    
    # Test 6: POST /api/exports/render with custom data
    print("\n[D6] Testing POST /api/exports/render...")
    
    test_data = {
        "rows": [
            {"a": 1, "b": "x"},
            {"a": 2, "b": "y"}
        ],
        "format": "csv",
        "title": "Test Export"
    }
    resp = requests.post(f"{BASE_URL}/exports/render", json=test_data, headers=headers, timeout=10)
    
    if resp.status_code == 200:
        content_type = resp.headers.get("Content-Type", "")
        content = resp.text
        
        if "text/csv" in content_type:
            log_test("part_d_exports", "Export render endpoint", True,
                    f"CSV rendered, {len(content)} bytes", "HIGH")
        else:
            log_test("part_d_exports", "Export render endpoint", False,
                    f"Content-Type: {content_type}", "HIGH")
    else:
        log_test("part_d_exports", "Export render endpoint", False,
                f"Expected 200, got {resp.status_code}: {resp.text[:200]}", "CRITICAL")
    
    # Test 7: Invalid format — expect 400 or validation error
    print("\n[D7] Testing invalid export format...")
    
    resp = requests.get(f"{BASE_URL}/exports/products?format=badformat", headers=headers, timeout=10)
    
    if resp.status_code in [400, 422]:
        log_test("part_d_exports", "Export invalid format rejected", True,
                f"{resp.status_code} as expected", "MEDIUM")
    else:
        log_test("part_d_exports", "Export invalid format rejected", False,
                f"Expected 400/422, got {resp.status_code}", "HIGH")
    
    # Test 8: Unknown resource — expect 404
    print("\n[D8] Testing unknown export resource...")
    
    resp = requests.get(f"{BASE_URL}/exports/nothingness?format=csv", headers=headers, timeout=10)
    
    if resp.status_code == 404:
        log_test("part_d_exports", "Export unknown resource rejected", True,
                "404 as expected", "MEDIUM")
    else:
        log_test("part_d_exports", "Export unknown resource rejected", False,
                f"Expected 404, got {resp.status_code}", "HIGH")
    
    # Test 9: Auth required — no bearer token
    print("\n[D9] Testing export auth requirement...")
    
    resp = requests.get(f"{BASE_URL}/exports/products?format=csv", timeout=10)
    
    if resp.status_code == 401:
        log_test("part_d_exports", "Export auth required", True,
                "401 Unauthorized as expected", "HIGH")
    else:
        log_test("part_d_exports", "Export auth required", False,
                f"Expected 401, got {resp.status_code}", "CRITICAL")


# ============================================================================
# PART A — LIGHT REGRESSION TESTS
# ============================================================================

def test_part_a_regression():
    """Test Part A: Light regression (ensure nothing broke)."""
    print("\n" + "="*80)
    print("PART A — LIGHT REGRESSION TESTS")
    print("="*80)
    
    # Test 1: Login all 8 personas
    print("\n[A1] Testing login for all 8 personas...")
    
    failed_logins = []
    for role in CREDENTIALS.keys():
        try:
            token, user = login(role)
            print(f"  ✓ {role}: {user.get('email')}")
        except Exception as e:
            failed_logins.append(f"{role}: {str(e)[:100]}")
            print(f"  ✗ {role}: {str(e)[:100]}")
    
    if failed_logins:
        log_test("part_a_regression", "Login all personas", False,
                f"Failed: {', '.join(failed_logins)}", "CRITICAL")
    else:
        log_test("part_a_regression", "Login all personas", True,
                "All 8 personas logged in successfully", "HIGH")
    
    # Get admin token for remaining tests
    token, user = login("admin")
    headers = get_headers(token)
    
    # Test 2: POST /api/reverse/exceptions/scan — should return 200 with no ObjectId leaks
    print("\n[A2] Testing POST /api/reverse/exceptions/scan (no ObjectId leaks)...")
    
    resp = requests.post(f"{BASE_URL}/reverse/exceptions/scan", headers=headers, timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        content = json.dumps(data)
        
        # Check for ObjectId leaks
        has_objectid = "ObjectId" in content or "_id" in content
        
        if not has_objectid:
            found = data.get("found", 0)
            log_test("part_a_regression", "Exception scanner no ObjectId leaks", True,
                    f"200 OK, found={found}, no ObjectId leaks", "HIGH")
        else:
            log_test("part_a_regression", "Exception scanner no ObjectId leaks", False,
                    "ObjectId leak detected in response", "CRITICAL")
    else:
        log_test("part_a_regression", "Exception scanner no ObjectId leaks", False,
                f"Expected 200, got {resp.status_code}: {resp.text[:200]}", "CRITICAL")
    
    # Test 3: GET /api/analytics/kpi/executive?range=month — should return 15 KPIs
    print("\n[A3] Testing GET /api/analytics/kpi/executive?range=month (15 KPIs)...")
    
    resp = requests.get(f"{BASE_URL}/analytics/kpi/executive?range=month", headers=headers, timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        kpis = data.get("kpis", {})
        kpi_count = len(kpis)
        
        expected_kpis = [
            "revenue", "inventory_value", "inventory_health", "outstanding",
            "collections", "cash_flow", "claims_amount", "claims_count",
            "returns_amount", "returns_count", "replacement_cost",
            "approval_queue", "exception_count", "business_risk_score",
            "company_health_score"
        ]
        
        missing_kpis = [k for k in expected_kpis if k not in kpis]
        
        if kpi_count == 15 and not missing_kpis:
            log_test("part_a_regression", "Executive KPI 15 metrics", True,
                    f"All 15 KPIs present: revenue=${kpis.get('revenue', 0)/1e6:.1f}M", "HIGH")
        else:
            log_test("part_a_regression", "Executive KPI 15 metrics", False,
                    f"Expected 15 KPIs, got {kpi_count}. Missing: {missing_kpis}", "CRITICAL")
    else:
        log_test("part_a_regression", "Executive KPI 15 metrics", False,
                f"Expected 200, got {resp.status_code}", "CRITICAL")
    
    # Test 4: GET /api/analytics/party360/distributor/dist-100 — should return unified profile
    print("\n[A4] Testing GET /api/analytics/party360/distributor/dist-100...")
    
    resp = requests.get(f"{BASE_URL}/analytics/party360/distributor/dist-100", headers=headers, timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        
        required_sections = ["profile", "financials", "performance", "risk_score", "health_score", "timeline"]
        missing_sections = [s for s in required_sections if s not in data]
        
        if not missing_sections:
            profile = data.get("profile", {})
            financials = data.get("financials", {})
            log_test("part_a_regression", "Party 360 unified profile", True,
                    f"All sections present. Party: {profile.get('name', '?')}, Outstanding: ${financials.get('outstanding', 0)/1e6:.1f}M", "HIGH")
        else:
            log_test("part_a_regression", "Party 360 unified profile", False,
                    f"Missing sections: {missing_sections}", "CRITICAL")
    else:
        log_test("part_a_regression", "Party 360 unified profile", False,
                f"Expected 200, got {resp.status_code}", "CRITICAL")


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def print_summary():
    """Print test summary."""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    categories = [
        ("PART B — PERFORMANCE", "part_b_performance"),
        ("PART C — SECURITY", "part_c_security"),
        ("PART D — EXPORTS", "part_d_exports"),
        ("PART A — REGRESSION", "part_a_regression"),
    ]
    
    total_tests = 0
    total_passed = 0
    critical_failures = []
    high_failures = []
    medium_failures = []
    
    for category_name, category_key in categories:
        results = test_results[category_key]
        passed = sum(1 for r in results if r["passed"])
        total = len(results)
        
        total_tests += total
        total_passed += passed
        
        print(f"\n{category_name}: {passed}/{total} passed")
        
        for result in results:
            if not result["passed"]:
                status = "❌"
                priority = result["priority"]
                
                if priority == "CRITICAL":
                    critical_failures.append(f"{category_name}: {result['test']}")
                elif priority == "HIGH":
                    high_failures.append(f"{category_name}: {result['test']}")
                else:
                    medium_failures.append(f"{category_name}: {result['test']}")
            else:
                status = "✅"
            
            print(f"  {status} [{result['priority']}] {result['test']}")
            if result["details"]:
                print(f"      {result['details']}")
    
    print("\n" + "="*80)
    print(f"OVERALL: {total_passed}/{total_tests} tests passed ({total_passed*100//total_tests if total_tests else 0}%)")
    print("="*80)
    
    if critical_failures:
        print(f"\n🚨 CRITICAL FAILURES ({len(critical_failures)}):")
        for f in critical_failures:
            print(f"  - {f}")
    
    if high_failures:
        print(f"\n⚠️  HIGH PRIORITY FAILURES ({len(high_failures)}):")
        for f in high_failures:
            print(f"  - {f}")
    
    if medium_failures:
        print(f"\n⚡ MEDIUM PRIORITY FAILURES ({len(medium_failures)}):")
        for f in medium_failures:
            print(f"  - {f}")
    
    if not critical_failures and not high_failures:
        print("\n✅ All critical and high priority tests passed!")


if __name__ == "__main__":
    print("GO OIL DMS — Backend Testing Suite")
    print("Testing Parts B/C/D + Light Regression")
    print("="*80)
    
    try:
        test_part_b_performance()
        test_part_c_security()
        test_part_d_exports()
        test_part_a_regression()
        print_summary()
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
        print_summary()
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        print_summary()
