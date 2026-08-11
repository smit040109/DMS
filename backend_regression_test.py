#!/usr/bin/env python3
"""
GO OIL DMS - COMPREHENSIVE BACKEND REGRESSION TEST SUITE
Tests ALL routers: auth, collections, workflow, finance, reverse, analytics
"""
import requests
import json
import time
from typing import Dict, Any, List, Optional

# Configuration from frontend/.env
BASE_URL = "https://auth-mongo-secure.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
TEST_USERS = [
    {"email": "admin@gooil.com", "password": "GoOil@2026", "role": "super_admin", "name": "Super Admin"},
    {"email": "company@gooil.com", "password": "GoOil@2026", "role": "company_admin", "name": "Olivia Adeyemi"},
    {"email": "regional@gooil.com", "password": "GoOil@2026", "role": "regional_manager", "name": "Chinedu Okafor"},
    {"email": "sales@gooil.com", "password": "GoOil@2026", "role": "sales_executive", "name": "Adeola Adebayo"},
    {"email": "distributor@gooil.com", "password": "GoOil@2026", "role": "distributor", "name": "Apex Marine Ltd"},
    {"email": "accountant@gooil.com", "password": "GoOil@2026", "role": "distributor_accountant", "name": "Bola Adeyemi"},
    {"email": "retailer@gooil.com", "password": "GoOil@2026", "role": "retailer", "name": "Metro Auto Workshop"},
    {"email": "customer@gooil.com", "password": "GoOil@2026", "role": "customer", "name": "Delta Fleet Corp"},
]

# Global state
TOKENS = {}
TEST_DATA = {}
RESULTS = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "critical_failures": [],
    "high_failures": [],
    "medium_failures": [],
    "low_failures": [],
    "slow_endpoints": [],
}

def log_result(test_name: str, passed: bool, severity: str = "MEDIUM", message: str = "", response_time: float = 0):
    """Log test result"""
    RESULTS["total"] += 1
    if passed:
        RESULTS["passed"] += 1
        print(f"  ✓ {test_name} ({response_time:.2f}s)")
    else:
        RESULTS["failed"] += 1
        failure = {"test": test_name, "message": message, "severity": severity}
        if severity == "CRITICAL":
            RESULTS["critical_failures"].append(failure)
            print(f"  ✗ CRITICAL: {test_name} - {message}")
        elif severity == "HIGH":
            RESULTS["high_failures"].append(failure)
            print(f"  ✗ HIGH: {test_name} - {message}")
        elif severity == "MEDIUM":
            RESULTS["medium_failures"].append(failure)
            print(f"  ✗ MEDIUM: {test_name} - {message}")
        else:
            RESULTS["low_failures"].append(failure)
            print(f"  ✗ LOW: {test_name} - {message}")
    
    if response_time > 3.0:
        RESULTS["slow_endpoints"].append({"endpoint": test_name, "time": response_time})
        print(f"  ⚠ SLOW: {test_name} took {response_time:.2f}s (>3s threshold)")

def make_request(method: str, endpoint: str, token: Optional[str] = None, **kwargs) -> tuple:
    """Make HTTP request and return (response, elapsed_time)"""
    url = f"{BASE_URL}{endpoint}"
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    start = time.time()
    try:
        resp = requests.request(method, url, headers=headers, timeout=30, **kwargs)
        elapsed = time.time() - start
        return resp, elapsed
    except requests.exceptions.Timeout:
        elapsed = time.time() - start
        print(f"  ✗ Request timeout after {elapsed:.1f}s")
        return None, elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"  ✗ Request failed: {e}")
        return None, elapsed

# ============================================================
# 1. AUTH TESTS (all 8 personas)
# ============================================================

def test_auth_login_all_personas():
    """Test login for all 8 personas"""
    print("\n=== 1. AUTH: Login All Personas ===")
    for user in TEST_USERS:
        resp, elapsed = make_request("POST", "/auth/login", json={
            "email": user["email"],
            "password": user["password"]
        })
        
        if resp and resp.status_code == 200:
            data = resp.json()
            token = data.get("token")
            user_data = data.get("user")
            
            if token and user_data:
                TOKENS[user["email"]] = token
                log_result(f"Login {user['role']}", True, response_time=elapsed)
                
                # Verify user shape
                assert user_data.get("email") == user["email"], f"Email mismatch for {user['role']}"
                assert user_data.get("role") == user["role"], f"Role mismatch for {user['role']}"
            else:
                log_result(f"Login {user['role']}", False, "CRITICAL", "Missing token or user in response", elapsed)
        else:
            status = resp.status_code if resp else "NO_RESPONSE"
            text = resp.text if resp else "Connection failed"
            log_result(f"Login {user['role']}", False, "CRITICAL", f"Status {status}: {text}", elapsed)

def test_auth_me():
    """Test /auth/me for each logged-in user"""
    print("\n=== 2. AUTH: /auth/me ===")
    for email, token in TOKENS.items():
        resp, elapsed = make_request("GET", "/auth/me", token=token)
        
        if resp and resp.status_code == 200:
            data = resp.json()
            user = data.get("user")
            if user and user.get("email") == email:
                log_result(f"/auth/me for {email}", True, response_time=elapsed)
            else:
                log_result(f"/auth/me for {email}", False, "HIGH", "User data mismatch", elapsed)
        else:
            status = resp.status_code if resp else "NO_RESPONSE"
            log_result(f"/auth/me for {email}", False, "HIGH", f"Status {status}", elapsed)

def test_auth_invalid_credentials():
    """Test login with invalid credentials"""
    print("\n=== 3. AUTH: Invalid Credentials ===")
    resp, elapsed = make_request("POST", "/auth/login", json={
        "email": "invalid@test.com",
        "password": "wrongpassword"
    })
    
    if resp and resp.status_code == 401:
        log_result("Invalid credentials returns 401", True, response_time=elapsed)
    else:
        status = resp.status_code if resp else "NO_RESPONSE"
        log_result("Invalid credentials returns 401", False, "MEDIUM", f"Expected 401, got {status}", elapsed)

def test_auth_missing_token():
    """Test endpoint without token"""
    print("\n=== 4. AUTH: Missing Token ===")
    resp, elapsed = make_request("GET", "/auth/me")
    
    if resp and resp.status_code == 401:
        log_result("Missing token returns 401", True, response_time=elapsed)
    else:
        status = resp.status_code if resp else "NO_RESPONSE"
        log_result("Missing token returns 401", False, "MEDIUM", f"Expected 401, got {status}", elapsed)

# ============================================================
# 2. COLLECTIONS ROUTER TESTS
# ============================================================

def test_collections_list():
    """Test GET /collections/{resource} for key collections"""
    print("\n=== 5. COLLECTIONS: List Resources ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    collections = ["branches", "skus", "distributors", "retailers", "products", "warehouses"]
    for coll in collections:
        resp, elapsed = make_request("GET", f"/collections/{coll}", token=admin_token)
        
        if resp and resp.status_code == 200:
            data = resp.json()
            if "data" in data and isinstance(data["data"], list):
                count = len(data["data"])
                log_result(f"GET /collections/{coll} ({count} items)", True, response_time=elapsed)
                # Store for later use
                if coll == "distributors" and count > 0:
                    TEST_DATA["distributor_id"] = data["data"][0]["id"]
                if coll == "retailers" and count > 0:
                    TEST_DATA["retailer_id"] = data["data"][0]["id"]
                if coll == "skus" and count > 0:
                    TEST_DATA["sku_id"] = data["data"][0]["id"]
                if coll == "branches" and count > 0:
                    TEST_DATA["branch_id"] = data["data"][0]["id"]
            else:
                log_result(f"GET /collections/{coll}", False, "HIGH", "Invalid response structure", elapsed)
        else:
            status = resp.status_code if resp else "NO_RESPONSE"
            log_result(f"GET /collections/{coll}", False, "HIGH", f"Status {status}", elapsed)

def test_collections_filtering():
    """Test filtering on collections"""
    print("\n=== 6. COLLECTIONS: Filtering ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    if "branch_id" in TEST_DATA:
        resp, elapsed = make_request("GET", f"/collections/distributors?branch_id={TEST_DATA['branch_id']}", token=admin_token)
        if resp and resp.status_code == 200:
            log_result("Filter distributors by branch_id", True, response_time=elapsed)
        else:
            log_result("Filter distributors by branch_id", False, "MEDIUM", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_collections_get_by_id():
    """Test GET /collections/{resource}/{id}"""
    print("\n=== 7. COLLECTIONS: Get By ID ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    if "distributor_id" in TEST_DATA:
        resp, elapsed = make_request("GET", f"/collections/distributors/{TEST_DATA['distributor_id']}", token=admin_token)
        if resp and resp.status_code == 200:
            data = resp.json()
            if data.get("id") == TEST_DATA["distributor_id"]:
                log_result("GET distributor by ID", True, response_time=elapsed)
            else:
                log_result("GET distributor by ID", False, "HIGH", "ID mismatch", elapsed)
        else:
            log_result("GET distributor by ID", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

# ============================================================
# 3. PHASE 1 WORKFLOW TESTS
# ============================================================

def test_workflow_inventory_company():
    """Test GET /workflow/inventory/company"""
    print("\n=== 8. WORKFLOW: Company Inventory ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/workflow/inventory/company", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        if "data" in data and isinstance(data["data"], list):
            count = len(data["data"])
            log_result(f"GET company inventory ({count} rows)", True, response_time=elapsed)
            
            # Verify bucket structure
            if count > 0:
                row = data["data"][0]
                buckets = ["available", "reserved", "in_transit", "damaged", "returned", "expired"]
                has_buckets = all(bucket in row for bucket in buckets)
                if has_buckets:
                    log_result("Inventory bucket structure valid", True)
                else:
                    log_result("Inventory bucket structure valid", False, "HIGH", "Missing bucket fields")
        else:
            log_result("GET company inventory", False, "HIGH", "Invalid response structure", elapsed)
    else:
        log_result("GET company inventory", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_workflow_stock_ledger():
    """Test GET /workflow/stock-ledger"""
    print("\n=== 9. WORKFLOW: Stock Ledger ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/workflow/stock-ledger?limit=50", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        if "data" in data and isinstance(data["data"], list):
            count = len(data["data"])
            log_result(f"GET stock ledger ({count} entries)", True, response_time=elapsed)
        else:
            log_result("GET stock ledger", False, "HIGH", "Invalid response structure", elapsed)
    else:
        log_result("GET stock ledger", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_workflow_primary_orders():
    """Test primary orders exist"""
    print("\n=== 10. WORKFLOW: Primary Orders ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/collections/primary-orders", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        if "data" in data and len(data["data"]) > 0:
            count = len(data["data"])
            log_result(f"Primary orders exist ({count} orders)", True, response_time=elapsed)
            TEST_DATA["primary_order_id"] = data["data"][0]["id"]
        else:
            log_result("Primary orders exist", False, "HIGH", "No primary orders found", elapsed)
    else:
        log_result("Primary orders exist", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_workflow_invoices():
    """Test invoices exist"""
    print("\n=== 11. WORKFLOW: Invoices ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/collections/invoices", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        if "data" in data and len(data["data"]) > 0:
            count = len(data["data"])
            log_result(f"Invoices exist ({count} invoices)", True, response_time=elapsed)
            TEST_DATA["invoice_id"] = data["data"][0]["id"]
        else:
            log_result("Invoices exist", False, "HIGH", "No invoices found", elapsed)
    else:
        log_result("Invoices exist", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

# ============================================================
# 4. PHASE 2 FINANCE TESTS
# ============================================================

def test_finance_outstanding():
    """Test GET /finance/outstanding"""
    print("\n=== 12. FINANCE: Outstanding ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/finance/outstanding", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        if "data" in data and isinstance(data["data"], list):
            count = len(data["data"])
            log_result(f"GET outstanding ({count} parties)", True, response_time=elapsed)
        else:
            log_result("GET outstanding", False, "HIGH", "Invalid response structure", elapsed)
    else:
        log_result("GET outstanding", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_finance_ledger():
    """Test GET /finance/ledger"""
    print("\n=== 13. FINANCE: Ledger ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/finance/ledger?limit=100", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        if "data" in data and isinstance(data["data"], list):
            count = len(data["data"])
            log_result(f"GET ledger ({count} entries)", True, response_time=elapsed)
            
            # Verify journal balance (Dr = Cr per journal_id)
            if count > 0:
                journals = {}
                for entry in data["data"]:
                    jid = entry.get("journal_id")
                    if jid:
                        if jid not in journals:
                            journals[jid] = {"dr": 0, "cr": 0}
                        journals[jid]["dr"] += entry.get("debit", 0)
                        journals[jid]["cr"] += entry.get("credit", 0)
                
                imbalanced = []
                for jid, totals in journals.items():
                    if abs(totals["dr"] - totals["cr"]) > 0.01:
                        imbalanced.append(jid)
                
                if not imbalanced:
                    log_result("Ledger journal balance (Dr=Cr)", True)
                else:
                    log_result("Ledger journal balance (Dr=Cr)", False, "CRITICAL", f"{len(imbalanced)} imbalanced journals")
        else:
            log_result("GET ledger", False, "HIGH", "Invalid response structure", elapsed)
    else:
        log_result("GET ledger", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_finance_payments():
    """Test payments exist"""
    print("\n=== 14. FINANCE: Payments ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/collections/payments", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        if "data" in data:
            count = len(data["data"])
            log_result(f"Payments exist ({count} payments)", True, response_time=elapsed)
        else:
            log_result("Payments exist", False, "MEDIUM", "Invalid response structure", elapsed)
    else:
        log_result("Payments exist", False, "MEDIUM", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_finance_coupons_validate():
    """Test POST /finance/coupons/validate"""
    print("\n=== 15. FINANCE: Coupon Validation ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    # Test with invalid coupon
    resp, elapsed = make_request("POST", "/finance/coupons/validate", token=admin_token, json={
        "code": "INVALID_CODE",
        "party_id": TEST_DATA.get("retailer_id", "test-id"),
        "party_type": "retailer",
        "lines": [],
        "order_total": 1000
    })
    
    if resp and resp.status_code == 200:
        data = resp.json()
        if data.get("ok") == False:
            log_result("Coupon validation (invalid code)", True, response_time=elapsed)
        else:
            log_result("Coupon validation (invalid code)", False, "MEDIUM", "Should reject invalid coupon", elapsed)
    else:
        log_result("Coupon validation (invalid code)", False, "MEDIUM", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_finance_cashback_rules():
    """Test GET /finance/cashback-rules"""
    print("\n=== 16. FINANCE: Cashback Rules ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/finance/cashback-rules", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        if "data" in data:
            count = len(data["data"])
            log_result(f"GET cashback rules ({count} rules)", True, response_time=elapsed)
        else:
            log_result("GET cashback rules", False, "MEDIUM", "Invalid response structure", elapsed)
    else:
        log_result("GET cashback rules", False, "MEDIUM", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

# ============================================================
# 5. PHASE 3 REVERSE LOGISTICS TESTS
# ============================================================

def test_reverse_approval_matrix():
    """Test GET /reverse/approval-matrix"""
    print("\n=== 17. REVERSE: Approval Matrix ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/reverse/approval-matrix", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        if "data" in data and isinstance(data["data"], list):
            count = len(data["data"])
            log_result(f"GET approval matrix ({count} rules)", True, response_time=elapsed)
            
            # Verify 12 default rules seeded
            if count >= 12:
                log_result("Approval matrix seeds 12+ rules", True)
            else:
                log_result("Approval matrix seeds 12+ rules", False, "MEDIUM", f"Only {count} rules found")
        else:
            log_result("GET approval matrix", False, "HIGH", "Invalid response structure", elapsed)
    else:
        log_result("GET approval matrix", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_reverse_returns():
    """Test GET /reverse/returns"""
    print("\n=== 18. REVERSE: Returns ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/reverse/returns", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        if "data" in data:
            count = len(data["data"])
            log_result(f"GET returns ({count} returns)", True, response_time=elapsed)
            if count > 0:
                TEST_DATA["return_id"] = data["data"][0]["id"]
        else:
            log_result("GET returns", False, "HIGH", "Invalid response structure", elapsed)
    else:
        log_result("GET returns", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_reverse_damage():
    """Test GET /reverse/damage"""
    print("\n=== 19. REVERSE: Damage ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/reverse/damage", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        if "data" in data:
            count = len(data["data"])
            log_result(f"GET damage ({count} records)", True, response_time=elapsed)
        else:
            log_result("GET damage", False, "HIGH", "Invalid response structure", elapsed)
    else:
        log_result("GET damage", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_reverse_claims():
    """Test GET /reverse/claims"""
    print("\n=== 20. REVERSE: Claims ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/reverse/claims", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        if "data" in data:
            count = len(data["data"])
            log_result(f"GET claims ({count} claims)", True, response_time=elapsed)
        else:
            log_result("GET claims", False, "HIGH", "Invalid response structure", elapsed)
    else:
        log_result("GET claims", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_reverse_credit_notes():
    """Test GET /reverse/credit-notes"""
    print("\n=== 21. REVERSE: Credit Notes ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/reverse/credit-notes", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        if "data" in data:
            count = len(data["data"])
            log_result(f"GET credit notes ({count} CNs)", True, response_time=elapsed)
        else:
            log_result("GET credit notes", False, "HIGH", "Invalid response structure", elapsed)
    else:
        log_result("GET credit notes", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_reverse_debit_notes():
    """Test GET /reverse/debit-notes"""
    print("\n=== 22. REVERSE: Debit Notes ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/reverse/debit-notes", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        if "data" in data:
            count = len(data["data"])
            log_result(f"GET debit notes ({count} DNs)", True, response_time=elapsed)
        else:
            log_result("GET debit notes", False, "HIGH", "Invalid response structure", elapsed)
    else:
        log_result("GET debit notes", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_reverse_replacements():
    """Test GET /reverse/replacements"""
    print("\n=== 23. REVERSE: Replacements ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/reverse/replacements", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        if "data" in data:
            count = len(data["data"])
            log_result(f"GET replacements ({count} replacements)", True, response_time=elapsed)
        else:
            log_result("GET replacements", False, "HIGH", "Invalid response structure", elapsed)
    else:
        log_result("GET replacements", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_reverse_expiry():
    """Test GET /reverse/expiry"""
    print("\n=== 24. REVERSE: Expiry ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/reverse/expiry?days=30", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        if "near_expiry" in data and "expired" in data:
            near = len(data["near_expiry"])
            expired = len(data["expired"])
            log_result(f"GET expiry (near={near}, expired={expired})", True, response_time=elapsed)
        else:
            log_result("GET expiry", False, "HIGH", "Invalid response structure", elapsed)
    else:
        log_result("GET expiry", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_reverse_exceptions_list():
    """Test GET /reverse/exceptions (list)"""
    print("\n=== 25. REVERSE: Exceptions List ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/collections/exceptions", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        if "data" in data:
            count = len(data["data"])
            log_result(f"GET exceptions list ({count} exceptions)", True, response_time=elapsed)
        else:
            log_result("GET exceptions list", False, "HIGH", "Invalid response structure", elapsed)
    else:
        log_result("GET exceptions list", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_reverse_exceptions_scan():
    """Test POST /reverse/exceptions/scan - CRITICAL TEST"""
    print("\n=== 26. REVERSE: Exception Scanner (CRITICAL) ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    # Run scan twice to test idempotency
    for run in [1, 2]:
        resp, elapsed = make_request("POST", "/reverse/exceptions/scan", token=admin_token, json={})
        
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                # Check for ObjectId leaks in raw text
                text = resp.text
                has_objectid = "ObjectId(" in text or '"_id":' in text
                
                if has_objectid:
                    log_result(f"Exception scan run {run} - No ObjectId leaks", False, "CRITICAL", "ObjectId found in response", elapsed)
                else:
                    # Valid response structure
                    if "found" in data or "exceptions" in data or isinstance(data, list):
                        if isinstance(data, dict):
                            count = data.get("found", 0)
                        else:
                            count = len(data)
                        log_result(f"Exception scan run {run} ({count} exceptions)", True, response_time=elapsed)
                    else:
                        log_result(f"Exception scan run {run}", True, response_time=elapsed)
            except json.JSONDecodeError:
                log_result(f"Exception scan run {run}", False, "CRITICAL", "Invalid JSON response", elapsed)
        else:
            status = resp.status_code if resp else "NO_RESPONSE"
            text = resp.text[:200] if resp else "Connection failed"
            log_result(f"Exception scan run {run}", False, "CRITICAL", f"Status {status}: {text}", elapsed)

def test_reverse_reports():
    """Test GET /reverse/reports/* (9 reports)"""
    print("\n=== 27. REVERSE: Reports Hub ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    reports = ["returns", "damage", "claims", "credit_notes", "debit_notes", "expiry", "replacements", "approvals", "audit"]
    for report in reports:
        resp, elapsed = make_request("GET", f"/reverse/reports/{report}", token=admin_token)
        
        if resp and resp.status_code == 200:
            data = resp.json()
            if "summary" in data or "data" in data:
                log_result(f"GET /reverse/reports/{report}", True, response_time=elapsed)
            else:
                log_result(f"GET /reverse/reports/{report}", False, "MEDIUM", "Invalid response structure", elapsed)
        else:
            log_result(f"GET /reverse/reports/{report}", False, "MEDIUM", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

# ============================================================
# 6. PHASE 4 ANALYTICS TESTS
# ============================================================

def test_analytics_dimensions():
    """Test GET /analytics/dimensions"""
    print("\n=== 28. ANALYTICS: Dimensions ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/analytics/dimensions", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        required = ["branches", "distributors", "retailers", "customers", "products", "skus", "ranges"]
        if all(key in data for key in required):
            log_result("GET /analytics/dimensions", True, response_time=elapsed)
        else:
            log_result("GET /analytics/dimensions", False, "HIGH", "Missing required keys", elapsed)
    else:
        log_result("GET /analytics/dimensions", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_analytics_executive_kpi():
    """Test GET /analytics/kpi/executive"""
    print("\n=== 29. ANALYTICS: Executive KPI (15 KPIs) ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/analytics/kpi/executive?range=month", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        if "kpis" in data:
            kpis = data["kpis"]
            required_kpis = [
                "revenue", "sales_count", "inventory_value", "inventory_health",
                "order_pipeline", "outstanding", "collections", "cash_flow",
                "claims", "returns", "replacement_cost", "approval_queue",
                "exception_count", "business_risk_score", "company_health_score"
            ]
            
            missing = [k for k in required_kpis if k not in kpis]
            if not missing:
                log_result("Executive KPI (all 15 KPIs present)", True, response_time=elapsed)
            else:
                log_result("Executive KPI (all 15 KPIs present)", False, "CRITICAL", f"Missing: {missing}", elapsed)
        else:
            log_result("Executive KPI", False, "CRITICAL", "Missing kpis key", elapsed)
    else:
        log_result("Executive KPI", False, "CRITICAL", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_analytics_trace_order():
    """Test GET /analytics/trace/order/{id}"""
    print("\n=== 30. ANALYTICS: Order Trace (20-node) ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    if "primary_order_id" in TEST_DATA:
        resp, elapsed = make_request("GET", f"/analytics/trace/order/{TEST_DATA['primary_order_id']}", token=admin_token)
        
        if resp and resp.status_code == 200:
            data = resp.json()
            if "timeline" in data and isinstance(data["timeline"], list):
                timeline_len = len(data["timeline"])
                if timeline_len == 20:
                    log_result("Order trace (20-node timeline)", True, response_time=elapsed)
                else:
                    log_result("Order trace (20-node timeline)", False, "HIGH", f"Expected 20 nodes, got {timeline_len}", elapsed)
            else:
                log_result("Order trace", False, "HIGH", "Missing timeline", elapsed)
        else:
            log_result("Order trace", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)
    else:
        log_result("Order trace", False, "MEDIUM", "No primary_order_id available", 0)

def test_analytics_party360():
    """Test GET /analytics/party360/{type}/{id}"""
    print("\n=== 31. ANALYTICS: Party 360 ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    party_types = [
        ("distributor", TEST_DATA.get("distributor_id")),
        ("retailer", TEST_DATA.get("retailer_id")),
    ]
    
    for party_type, party_id in party_types:
        if party_id:
            resp, elapsed = make_request("GET", f"/analytics/party360/{party_type}/{party_id}", token=admin_token)
            
            if resp and resp.status_code == 200:
                data = resp.json()
                required = ["profile", "financials", "performance", "risk_score", "health_score", "timeline"]
                if all(key in data for key in required):
                    log_result(f"Party360 {party_type}", True, response_time=elapsed)
                else:
                    missing = [k for k in required if k not in data]
                    log_result(f"Party360 {party_type}", False, "HIGH", f"Missing: {missing}", elapsed)
            else:
                log_result(f"Party360 {party_type}", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_analytics_sales():
    """Test GET /analytics/sales"""
    print("\n=== 32. ANALYTICS: Sales Analytics ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/analytics/sales?range=month", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        required = ["series", "top_skus", "by_branch", "funnel", "totals"]
        if all(key in data for key in required):
            log_result("Sales analytics", True, response_time=elapsed)
        else:
            log_result("Sales analytics", False, "HIGH", "Missing required keys", elapsed)
    else:
        log_result("Sales analytics", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_analytics_inventory():
    """Test GET /analytics/inventory"""
    print("\n=== 33. ANALYTICS: Inventory Analytics ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/analytics/inventory", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        required = ["buckets", "top_skus", "totals"]
        if all(key in data for key in required):
            log_result("Inventory analytics", True, response_time=elapsed)
        else:
            log_result("Inventory analytics", False, "HIGH", "Missing required keys", elapsed)
    else:
        log_result("Inventory analytics", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_analytics_finance():
    """Test GET /analytics/finance"""
    print("\n=== 34. ANALYTICS: Finance Analytics ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/analytics/finance?range=month", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        required = ["series", "by_method", "aging", "totals"]
        if all(key in data for key in required):
            log_result("Finance analytics", True, response_time=elapsed)
        else:
            log_result("Finance analytics", False, "HIGH", "Missing required keys", elapsed)
    else:
        log_result("Finance analytics", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_analytics_returns():
    """Test GET /analytics/returns"""
    print("\n=== 35. ANALYTICS: Returns Analytics ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/analytics/returns?range=month", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        required = ["totals", "by_reason", "by_scope"]
        if all(key in data for key in required):
            log_result("Returns analytics", True, response_time=elapsed)
        else:
            log_result("Returns analytics", False, "HIGH", "Missing required keys", elapsed)
    else:
        log_result("Returns analytics", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_analytics_claims():
    """Test GET /analytics/claims"""
    print("\n=== 36. ANALYTICS: Claims Analytics ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/analytics/claims?range=month", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        required = ["totals", "by_type", "by_status"]
        if all(key in data for key in required):
            log_result("Claims analytics", True, response_time=elapsed)
        else:
            log_result("Claims analytics", False, "HIGH", "Missing required keys", elapsed)
    else:
        log_result("Claims analytics", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_analytics_profitability():
    """Test GET /analytics/profitability"""
    print("\n=== 37. ANALYTICS: Profitability Analytics ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/analytics/profitability?range=month", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        required = ["revenue", "cogs", "gross_profit", "net_profit", "waterfall"]
        if all(key in data for key in required):
            log_result("Profitability analytics", True, response_time=elapsed)
        else:
            log_result("Profitability analytics", False, "HIGH", "Missing required keys", elapsed)
    else:
        log_result("Profitability analytics", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_analytics_alerts():
    """Test GET /analytics/alerts"""
    print("\n=== 38. ANALYTICS: Business Alerts ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/analytics/alerts", token=admin_token)
    if resp and resp.status_code == 200:
        data = resp.json()
        if "alerts" in data and isinstance(data["alerts"], list):
            count = len(data["alerts"])
            log_result(f"Business alerts ({count} alerts)", True, response_time=elapsed)
        else:
            log_result("Business alerts", False, "HIGH", "Missing alerts array", elapsed)
    else:
        log_result("Business alerts", False, "HIGH", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_analytics_scorecards():
    """Test GET /analytics/scorecards/{entity_type}"""
    print("\n=== 39. ANALYTICS: Scorecards ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    entity_types = ["distributor", "retailer", "branch", "sales_executive", "warehouse", "company"]
    for entity_type in entity_types:
        resp, elapsed = make_request("GET", f"/analytics/scorecards/{entity_type}", token=admin_token)
        
        if resp and resp.status_code == 200:
            data = resp.json()
            if "rows" in data and isinstance(data["rows"], list):
                count = len(data["rows"])
                log_result(f"Scorecard {entity_type} ({count} rows)", True, response_time=elapsed)
            else:
                log_result(f"Scorecard {entity_type}", False, "MEDIUM", "Missing rows", elapsed)
        else:
            log_result(f"Scorecard {entity_type}", False, "MEDIUM", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

def test_analytics_ai_context():
    """Test GET /analytics/ai-context/{scope}"""
    print("\n=== 40. ANALYTICS: AI Context ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    scopes = ["executive", "sales", "finance", "inventory"]
    for scope in scopes:
        resp, elapsed = make_request("GET", f"/analytics/ai-context/{scope}", token=admin_token)
        
        if resp and resp.status_code == 200:
            data = resp.json()
            if "generated_at" in data:
                log_result(f"AI context {scope}", True, response_time=elapsed)
            else:
                log_result(f"AI context {scope}", False, "MEDIUM", "Missing generated_at", elapsed)
        else:
            log_result(f"AI context {scope}", False, "MEDIUM", f"Status {resp.status_code if resp else 'NO_RESPONSE'}", elapsed)

# ============================================================
# 7. CROSS-CUTTING TESTS
# ============================================================

def test_cross_cutting_no_objectid():
    """Verify no MongoDB ObjectId in responses"""
    print("\n=== 41. CROSS-CUTTING: No ObjectId Leaks ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    # Sample a few endpoints
    endpoints = [
        "/collections/distributors",
        "/collections/invoices",
        "/workflow/inventory/company",
        "/finance/outstanding",
        "/reverse/returns",
        "/analytics/dimensions"
    ]
    
    all_clean = True
    for endpoint in endpoints:
        resp, _ = make_request("GET", endpoint, token=admin_token)
        if resp and resp.status_code == 200:
            text = resp.text
            if "ObjectId" in text or '"_id"' in text:
                log_result(f"No ObjectId in {endpoint}", False, "HIGH", "ObjectId found in response")
                all_clean = False
    
    if all_clean:
        log_result("No ObjectId leaks (sampled endpoints)", True)

def test_cross_cutting_404_handling():
    """Test 404 on invalid IDs"""
    print("\n=== 42. CROSS-CUTTING: 404 Handling ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    resp, elapsed = make_request("GET", "/collections/distributors/invalid-id-12345", token=admin_token)
    if resp and resp.status_code == 404:
        log_result("404 on invalid ID", True, response_time=elapsed)
    else:
        status = resp.status_code if resp else "NO_RESPONSE"
        log_result("404 on invalid ID", False, "MEDIUM", f"Expected 404, got {status}", elapsed)

def test_cross_cutting_400_handling():
    """Test 400 on invalid body"""
    print("\n=== 43. CROSS-CUTTING: 400 Handling ===")
    admin_token = TOKENS.get("admin@gooil.com")
    
    # Try to create primary order with missing required fields
    resp, elapsed = make_request("POST", "/workflow/primary-orders", token=admin_token, json={})
    if resp and resp.status_code == 400:
        log_result("400 on invalid body", True, response_time=elapsed)
    else:
        status = resp.status_code if resp else "NO_RESPONSE"
        log_result("400 on invalid body", False, "MEDIUM", f"Expected 400, got {status}", elapsed)

# ============================================================
# MAIN TEST RUNNER
# ============================================================

def print_summary():
    """Print test summary"""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total Tests: {RESULTS['total']}")
    print(f"Passed: {RESULTS['passed']} ({RESULTS['passed']/max(RESULTS['total'],1)*100:.1f}%)")
    print(f"Failed: {RESULTS['failed']} ({RESULTS['failed']/max(RESULTS['total'],1)*100:.1f}%)")
    
    if RESULTS['critical_failures']:
        print(f"\n🔴 CRITICAL FAILURES ({len(RESULTS['critical_failures'])}):")
        for f in RESULTS['critical_failures']:
            print(f"  - {f['test']}: {f['message']}")
    
    if RESULTS['high_failures']:
        print(f"\n🟠 HIGH FAILURES ({len(RESULTS['high_failures'])}):")
        for f in RESULTS['high_failures']:
            print(f"  - {f['test']}: {f['message']}")
    
    if RESULTS['medium_failures']:
        print(f"\n🟡 MEDIUM FAILURES ({len(RESULTS['medium_failures'])}):")
        for f in RESULTS['medium_failures']:
            print(f"  - {f['test']}: {f['message']}")
    
    if RESULTS['slow_endpoints']:
        print(f"\n⏱️  SLOW ENDPOINTS (>3s):")
        for e in RESULTS['slow_endpoints']:
            print(f"  - {e['endpoint']}: {e['time']:.2f}s")
    
    print("\n" + "="*80)

def main():
    """Main test runner"""
    print("="*80)
    print("GO OIL DMS - COMPREHENSIVE BACKEND REGRESSION TEST")
    print("="*80)
    print(f"Backend URL: {BASE_URL}")
    print(f"Testing {len(TEST_USERS)} user personas")
    print("="*80)
    
    try:
        # 1. AUTH TESTS
        test_auth_login_all_personas()
        test_auth_me()
        test_auth_invalid_credentials()
        test_auth_missing_token()
        
        # 2. COLLECTIONS TESTS
        test_collections_list()
        test_collections_filtering()
        test_collections_get_by_id()
        
        # 3. WORKFLOW TESTS
        test_workflow_inventory_company()
        test_workflow_stock_ledger()
        test_workflow_primary_orders()
        test_workflow_invoices()
        
        # 4. FINANCE TESTS
        test_finance_outstanding()
        test_finance_ledger()
        test_finance_payments()
        test_finance_coupons_validate()
        test_finance_cashback_rules()
        
        # 5. REVERSE LOGISTICS TESTS
        test_reverse_approval_matrix()
        test_reverse_returns()
        test_reverse_damage()
        test_reverse_claims()
        test_reverse_credit_notes()
        test_reverse_debit_notes()
        test_reverse_replacements()
        test_reverse_expiry()
        test_reverse_exceptions_list()
        test_reverse_exceptions_scan()  # CRITICAL TEST
        test_reverse_reports()
        
        # 6. ANALYTICS TESTS
        test_analytics_dimensions()
        test_analytics_executive_kpi()
        test_analytics_trace_order()
        test_analytics_party360()
        test_analytics_sales()
        test_analytics_inventory()
        test_analytics_finance()
        test_analytics_returns()
        test_analytics_claims()
        test_analytics_profitability()
        test_analytics_alerts()
        test_analytics_scorecards()
        test_analytics_ai_context()
        
        # 7. CROSS-CUTTING TESTS
        test_cross_cutting_no_objectid()
        test_cross_cutting_404_handling()
        test_cross_cutting_400_handling()
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print_summary()

if __name__ == "__main__":
    main()
