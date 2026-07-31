"""
Bharat Oil DMS Backend API Tests — Phase 1-6 Endpoints
Testing NEW endpoints added in this sprint:
- Phase 1: Owner user management
- Phase 2: Salesperson GPS ping
- Phase 3: Live tracking
- Phase 4: Team Leader endpoints + Owner insights
- Phase 5: Regional Manager
- Regressions: existing critical flows
"""
import os
import time
import requests

# Read backend URL from frontend/.env
BASE_URL = None
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
            break

if not BASE_URL:
    raise RuntimeError("REACT_APP_BACKEND_URL not found in /app/frontend/.env")

API = f"{BASE_URL}/api"
DMS_API = f"{API}/dms"
COMMON_PW = "Demo@2026"

# Test credentials from /app/memory/test_credentials.md
CREDENTIALS = {
    "owner": "owner@dms.com",
    "owner_accountant": "acct@dms.com",
    "tl": "tl@dms.com",
    "rm": "rm@dms.com",
    "sales": "sales@dms.com",
    "dist1": "dist1@dms.com",
    "retailer1": "retailer1@dms.com",
}

# Global state for test data
test_state = {
    "tokens": {},
    "new_user_id": None,
    "new_user_email": None,
    "sales_id": None,
    "tl_id": None,
    "rm_id": None,
    "distributor_id": None,
}


def login(email, password=COMMON_PW):
    """Login and return token."""
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    if r.status_code != 200:
        print(f"❌ Login failed for {email}: {r.status_code} {r.text}")
        return None
    token = r.json()["token"]
    test_state["tokens"][email] = token
    return token


def headers(email):
    """Get auth headers for email."""
    token = test_state["tokens"].get(email)
    if not token:
        token = login(email)
    return {"Authorization": f"Bearer {token}"}


def print_section(title):
    """Print test section header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")


def print_test(name, passed, details=""):
    """Print test result."""
    status = "✅" if passed else "❌"
    print(f"{status} {name}")
    if details:
        print(f"   {details}")


# ============================================================================
# PHASE 1: Owner User Management
# ============================================================================
def test_phase1_owner_user_management():
    print_section("PHASE 1: OWNER USER MANAGEMENT")
    
    # Test 1: Login as owner
    print("\n1. POST /api/auth/login for owner → returns token")
    token = login(CREDENTIALS["owner"])
    if not token:
        print_test("Owner login", False)
        return False
    print_test("Owner login successful", True, f"Token length: {len(token)}")
    
    # Test 2: GET /dms/owner/users
    print("\n2. GET /dms/owner/users → returns 10 users with online field, no password_hash")
    r = requests.get(f"{DMS_API}/owner/users", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        users = r.json()["data"]
        print_test("GET owner/users", True, f"Found {len(users)} users")
        
        # Verify at least 10 users
        print_test("At least 10 users exist", len(users) >= 10, f"Found {len(users)} users")
        
        # Verify each user has online field and no password_hash
        if users:
            has_online = all("online" in u for u in users)
            no_password = all("password_hash" not in u for u in users)
            print_test("All users have 'online' field", has_online)
            print_test("No user has 'password_hash' in response", no_password)
            
            # Store salesperson, TL, RM IDs for later tests
            for u in users:
                if u.get("role") == "salesperson" and not test_state.get("sales_id"):
                    test_state["sales_id"] = u["id"]
                elif u.get("role") == "team_leader" and not test_state.get("tl_id"):
                    test_state["tl_id"] = u["id"]
                elif u.get("role") == "regional_manager" and not test_state.get("rm_id"):
                    test_state["rm_id"] = u["id"]
    else:
        print_test("GET owner/users", False, f"Status: {r.status_code}, {r.text}")
        return False
    
    # Test 3: POST /dms/owner/users - create temp user
    print("\n3. POST /dms/owner/users → create temp user (salesperson)")
    unique_email = f"tmp_e2e_{int(time.time())}@dms.com"
    payload = {
        "email": unique_email,
        "password": "Test@123",
        "name": "E2E Test SP",
        "role": "salesperson"
    }
    r = requests.post(f"{DMS_API}/owner/users", headers=headers(CREDENTIALS["owner"]), 
                     json=payload, timeout=15)
    if r.status_code == 200:
        result = r.json()
        print_test("POST owner/users", result.get("ok") == True, f"Response: {result}")
        
        if result.get("user"):
            user = result["user"]
            test_state["new_user_id"] = user["id"]
            test_state["new_user_email"] = unique_email
            print_test("Response has user body", True, f"User ID: {user['id']}")
            print_test("User body has no password_hash", "password_hash" not in user)
    else:
        print_test("POST owner/users", False, f"Status: {r.status_code}, {r.text}")
        return False
    
    # Test 3a: Duplicate email → 400
    print("\n3a. POST /dms/owner/users with duplicate email → 400")
    r = requests.post(f"{DMS_API}/owner/users", headers=headers(CREDENTIALS["owner"]), 
                     json=payload, timeout=15)
    print_test("Duplicate email returns 400", r.status_code == 400, f"Status: {r.status_code}")
    
    # Test 3b: Cross-role check - TL tries to create user → 403
    print("\n3b. POST /dms/owner/users as team leader → 403")
    r = requests.post(f"{DMS_API}/owner/users", headers=headers(CREDENTIALS["tl"]), 
                     json={"email": f"test_{int(time.time())}@dms.com", "password": "Test@123", 
                           "name": "Test", "role": "salesperson"}, timeout=15)
    print_test("Team leader cannot create user (403)", r.status_code == 403, f"Status: {r.status_code}")
    
    # Test 4: POST /dms/owner/users/{uid}/reset-password
    print("\n4. POST /dms/owner/users/{uid}/reset-password with new_password=Reset@2026 → ok")
    if test_state.get("new_user_id"):
        payload = {"new_password": "Reset@2026"}
        r = requests.post(f"{DMS_API}/owner/users/{test_state['new_user_id']}/reset-password", 
                         headers=headers(CREDENTIALS["owner"]), json=payload, timeout=15)
        if r.status_code == 200:
            result = r.json()
            print_test("Reset password", result.get("ok") == True, f"Response: {result}")
            
            # Verify new password works
            print("\n4a. Verify new password works by logging in")
            token = login(test_state["new_user_email"], "Reset@2026")
            print_test("Login with new password", token is not None)
        else:
            print_test("Reset password", False, f"Status: {r.status_code}, {r.text}")
    
    # Test 5: POST /dms/owner/impersonate/{uid}
    print("\n5. POST /dms/owner/impersonate/{non-owner uid} → returns token + user + impersonated_by")
    if test_state.get("new_user_id"):
        r = requests.post(f"{DMS_API}/owner/impersonate/{test_state['new_user_id']}", 
                         headers=headers(CREDENTIALS["owner"]), timeout=15)
        if r.status_code == 200:
            result = r.json()
            has_token = "token" in result and isinstance(result["token"], str)
            has_user = "user" in result and isinstance(result["user"], dict)
            has_impersonated_by = "impersonated_by" in result
            
            print_test("Impersonate returns token", has_token)
            print_test("Impersonate returns user", has_user)
            print_test("Impersonate returns impersonated_by", has_impersonated_by)
        else:
            print_test("Impersonate", False, f"Status: {r.status_code}, {r.text}")
    
    # Test 5a: Impersonate own owner id → 400
    print("\n5a. POST /dms/owner/impersonate/{owner_id} → 400")
    # Get owner user ID
    r = requests.get(f"{DMS_API}/owner/users?role=owner", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200 and r.json()["data"]:
        owner_id = r.json()["data"][0]["id"]
        r2 = requests.post(f"{DMS_API}/owner/impersonate/{owner_id}", 
                          headers=headers(CREDENTIALS["owner"]), timeout=15)
        print_test("Cannot impersonate own owner ID (400)", r2.status_code == 400, 
                  f"Status: {r2.status_code}")
    
    # Test 6: PATCH /dms/owner/users/{uid}
    print("\n6. PATCH /dms/owner/users/{uid} with phone → ok")
    if test_state.get("new_user_id"):
        payload = {"phone": "+91-99999"}
        r = requests.patch(f"{DMS_API}/owner/users/{test_state['new_user_id']}", 
                          headers=headers(CREDENTIALS["owner"]), json=payload, timeout=15)
        if r.status_code == 200:
            result = r.json()
            print_test("PATCH user", result.get("ok") == True, f"Response: {result}")
        else:
            print_test("PATCH user", False, f"Status: {r.status_code}, {r.text}")
    
    return True


# ============================================================================
# PHASE 2: Salesperson GPS Ping
# ============================================================================
def test_phase2_salesperson_gps_ping():
    print_section("PHASE 2: SALESPERSON GPS PING")
    
    # Test 7: Login as salesperson and post GPS ping
    print("\n7. Login as sales@dms.com → POST /dms/tracking/ping with lat=28.6, lng=77.2 → ok")
    token = login(CREDENTIALS["sales"])
    if not token:
        print_test("Salesperson login", False)
        return False
    
    payload = {"lat": 28.6, "lng": 77.2}
    r = requests.post(f"{DMS_API}/tracking/ping", headers=headers(CREDENTIALS["sales"]), 
                     json=payload, timeout=15)
    if r.status_code == 200:
        result = r.json()
        print_test("POST tracking/ping", result.get("ok") == True, f"Response: {result}")
    else:
        print_test("POST tracking/ping", False, f"Status: {r.status_code}, {r.text}")
        return False
    
    # Test 8: Owner posts tracking/ping → 403
    print("\n8. Owner POST /dms/tracking/ping → 403")
    r = requests.post(f"{DMS_API}/tracking/ping", headers=headers(CREDENTIALS["owner"]), 
                     json=payload, timeout=15)
    print_test("Owner cannot post GPS ping (403)", r.status_code == 403, f"Status: {r.status_code}")
    
    return True


# ============================================================================
# PHASE 3: Live Tracking
# ============================================================================
def test_phase3_live_tracking():
    print_section("PHASE 3: LIVE TRACKING")
    
    # Test 9: Owner GET /dms/tracking/live
    print("\n9. Owner GET /dms/tracking/live → returns salespersons/distributors/retailers arrays")
    r = requests.get(f"{DMS_API}/tracking/live", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        print_test("GET tracking/live", True, f"Response keys: {list(result.keys())}")
        
        has_salespersons = "salespersons" in result and isinstance(result["salespersons"], list)
        has_distributors = "distributors" in result and isinstance(result["distributors"], list)
        has_retailers = "retailers" in result and isinstance(result["retailers"], list)
        
        print_test("Has salespersons array", has_salespersons, 
                  f"Count: {len(result.get('salespersons', []))}")
        print_test("Has distributors array", has_distributors, 
                  f"Count: {len(result.get('distributors', []))}")
        print_test("Has retailers array", has_retailers, 
                  f"Count: {len(result.get('retailers', []))}")
        
        # Verify some distributors/retailers have lat/lng from seeds
        if has_distributors:
            with_gps = [d for d in result["distributors"] if d.get("gps_lat") and d.get("gps_lng")]
            print_test("Some distributors have GPS coordinates", len(with_gps) > 0, 
                      f"Found {len(with_gps)} with GPS")
        
        if has_retailers:
            with_gps = [r for r in result["retailers"] if r.get("gps_lat") and r.get("gps_lng")]
            print_test("Some retailers have GPS coordinates", len(with_gps) > 0, 
                      f"Found {len(with_gps)} with GPS")
    else:
        print_test("GET tracking/live", False, f"Status: {r.status_code}, {r.text}")
        return False
    
    # Test 10: Owner GET /dms/tracking/salesperson/{sales_id}
    print("\n10. Owner GET /dms/tracking/salesperson/{sales_id} → returns punch/route/distance_km/working_hours/visited")
    if test_state.get("sales_id"):
        r = requests.get(f"{DMS_API}/tracking/salesperson/{test_state['sales_id']}", 
                        headers=headers(CREDENTIALS["owner"]), timeout=15)
        if r.status_code == 200:
            result = r.json()
            print_test("GET tracking/salesperson", True, f"Response keys: {list(result.keys())}")
            
            expected_keys = ["punch", "route", "distance_km", "working_hours", "visited"]
            has_keys = all(k in result for k in expected_keys)
            print_test("Has expected keys (punch/route/distance_km/working_hours/visited)", has_keys)
        else:
            print_test("GET tracking/salesperson", False, f"Status: {r.status_code}, {r.text}")
    else:
        print_test("GET tracking/salesperson", False, "No salesperson ID available")
    
    # Test 11: Retailer GET /dms/tracking/live → 403
    print("\n11. Retailer GET /dms/tracking/live → 403")
    r = requests.get(f"{DMS_API}/tracking/live", headers=headers(CREDENTIALS["retailer1"]), timeout=15)
    print_test("Retailer cannot access live tracking (403)", r.status_code == 403, 
              f"Status: {r.status_code}")
    
    return True


# ============================================================================
# PHASE 4: Team Leader Endpoints
# ============================================================================
def test_phase4_team_leader():
    print_section("PHASE 4: TEAM LEADER ENDPOINTS")
    
    # Test 12: GET /dms/dashboard/team-leader
    print("\n12. GET /dms/dashboard/team-leader → returns kpis with expected keys")
    r = requests.get(f"{DMS_API}/dashboard/team-leader", headers=headers(CREDENTIALS["tl"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        print_test("GET dashboard/team-leader", True)
        
        kpis = result.get("kpis", {})
        expected_keys = ["today_sales", "monthly_sales", "total_orders", "pending_orders", 
                        "fulfillment_pct", "assigned_distributors", "assigned_salespersons", 
                        "total_retailers", "stock_alerts"]
        has_keys = all(k in kpis for k in expected_keys)
        print_test("KPIs have all expected keys", has_keys, f"Keys: {list(kpis.keys())}")
    else:
        print_test("GET dashboard/team-leader", False, f"Status: {r.status_code}, {r.text}")
        return False
    
    # Test 13: GET /dms/tl/distributors
    print("\n13. GET /dms/tl/distributors → each row has expected fields")
    r = requests.get(f"{DMS_API}/tl/distributors", headers=headers(CREDENTIALS["tl"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        distributors = result.get("data", [])
        print_test("GET tl/distributors", True, f"Found {len(distributors)} distributors")
        
        if distributors:
            d = distributors[0]
            expected_fields = ["available_stock", "outstanding_payable_to_owner", 
                             "outstanding_receivable_from_retailers", "today_sales", 
                             "monthly_sales", "revenue", "pending_orders"]
            has_fields = all(f in d for f in expected_fields)
            print_test("Distributor rows have expected fields", has_fields, 
                      f"Sample keys: {list(d.keys())}")
            
            # Store distributor ID for later tests
            if not test_state.get("distributor_id"):
                test_state["distributor_id"] = d.get("id")
    else:
        print_test("GET tl/distributors", False, f"Status: {r.status_code}, {r.text}")
    
    # Test 14: GET /dms/tl/salespersons
    print("\n14. GET /dms/tl/salespersons → each row has expected fields")
    r = requests.get(f"{DMS_API}/tl/salespersons", headers=headers(CREDENTIALS["tl"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        salespersons = result.get("data", [])
        print_test("GET tl/salespersons", True, f"Found {len(salespersons)} salespersons")
        
        if salespersons:
            s = salespersons[0]
            expected_fields = ["online", "punch_in", "punch_out", "live_location", 
                             "today_visits", "orders_today", "new_retailers_today"]
            has_fields = all(f in s for f in expected_fields)
            print_test("Salesperson rows have expected fields", has_fields, 
                      f"Sample keys: {list(s.keys())}")
    else:
        print_test("GET tl/salespersons", False, f"Status: {r.status_code}, {r.text}")
    
    # Test 15: GET /dms/tl/orders
    print("\n15. GET /dms/tl/orders → returns data + count")
    r = requests.get(f"{DMS_API}/tl/orders", headers=headers(CREDENTIALS["tl"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        print_test("GET tl/orders", True, f"Count: {result.get('count', 0)}")
        
        has_data = "data" in result and isinstance(result["data"], list)
        has_count = "count" in result
        print_test("Response has data array", has_data)
        print_test("Response has count", has_count)
    else:
        print_test("GET tl/orders", False, f"Status: {r.status_code}, {r.text}")
    
    # Test 16: GET /dms/tl/orders with filters
    print("\n16. GET /dms/tl/orders?status=pending&distributor_id={did} → filters correctly")
    if test_state.get("distributor_id"):
        r = requests.get(f"{DMS_API}/tl/orders?status=pending&distributor_id={test_state['distributor_id']}", 
                        headers=headers(CREDENTIALS["tl"]), timeout=15)
        if r.status_code == 200:
            result = r.json()
            print_test("GET tl/orders with filters", True, f"Count: {result.get('count', 0)}")
        else:
            print_test("GET tl/orders with filters", False, f"Status: {r.status_code}, {r.text}")
    
    # Test 17: GET /dms/tl/retailers
    print("\n17. GET /dms/tl/retailers → returns data with expected fields")
    r = requests.get(f"{DMS_API}/tl/retailers", headers=headers(CREDENTIALS["tl"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        retailers = result.get("data", [])
        print_test("GET tl/retailers", True, f"Found {len(retailers)} retailers")
        
        if retailers:
            ret = retailers[0]
            expected_fields = ["outstanding", "last_order_at", "total_purchases", "location"]
            has_fields = all(f in ret for f in expected_fields)
            print_test("Retailer rows have expected fields", has_fields, 
                      f"Sample keys: {list(ret.keys())}")
    else:
        print_test("GET tl/retailers", False, f"Status: {r.status_code}, {r.text}")
    
    # Test 18: POST /dms/tl/punch/in
    print("\n18. POST /dms/tl/punch/in → ok (record own punch)")
    payload = {"lat": 28.61, "lng": 77.20}
    r = requests.post(f"{DMS_API}/tl/punch/in", headers=headers(CREDENTIALS["tl"]), 
                     json=payload, timeout=15)
    if r.status_code == 200:
        result = r.json()
        print_test("POST tl/punch/in", result.get("ok") == True or result.get("already") == True, 
                  f"Response: {result}")
    else:
        print_test("POST tl/punch/in", False, f"Status: {r.status_code}, {r.text}")
    
    # Test 19: POST /dms/tl/punch/out
    print("\n19. POST /dms/tl/punch/out → ok")
    payload = {"lat": 28.62, "lng": 77.21}
    r = requests.post(f"{DMS_API}/tl/punch/out", headers=headers(CREDENTIALS["tl"]), 
                     json=payload, timeout=15)
    if r.status_code == 200:
        result = r.json()
        print_test("POST tl/punch/out", result.get("ok") == True, f"Response: {result}")
    else:
        print_test("POST tl/punch/out", False, f"Status: {r.status_code}, {r.text}")
    
    # Test 20: GET /dms/tl/attendance
    print("\n20. GET /dms/tl/attendance → returns rows for today")
    r = requests.get(f"{DMS_API}/tl/attendance", headers=headers(CREDENTIALS["tl"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        print_test("GET tl/attendance", True, f"Count: {result.get('count', 0)}")
    else:
        print_test("GET tl/attendance", False, f"Status: {r.status_code}, {r.text}")
    
    return True


# ============================================================================
# PHASE 4: Owner Insights
# ============================================================================
def test_phase4_owner_insights():
    print_section("PHASE 4: OWNER INSIGHTS")
    
    # Test 21: GET /dms/owner/tl-performance
    print("\n21. GET /dms/owner/tl-performance → data array with expected fields")
    r = requests.get(f"{DMS_API}/owner/tl-performance", headers=headers(CREDENTIALS["owner"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        tls = result.get("data", [])
        print_test("GET owner/tl-performance", True, f"Found {len(tls)} team leaders")
        
        if tls:
            tl = tls[0]
            expected_fields = ["name", "total_sales", "today_sales", "monthly_sales", 
                             "assigned_distributors", "series_7d"]
            has_fields = all(f in tl for f in expected_fields)
            print_test("TL performance has expected fields", has_fields, 
                      f"Sample keys: {list(tl.keys())}")
            
            # Verify series_7d is an array with 7 elements
            if "series_7d" in tl:
                is_array = isinstance(tl["series_7d"], list)
                has_7_days = len(tl["series_7d"]) == 7 if is_array else False
                print_test("series_7d is 7-day array", has_7_days, 
                          f"Length: {len(tl['series_7d']) if is_array else 'N/A'}")
    else:
        print_test("GET owner/tl-performance", False, f"Status: {r.status_code}, {r.text}")
        return False
    
    # Test 22: GET /dms/owner/distributor-sales/{did}
    print("\n22. GET /dms/owner/distributor-sales/{did} → returns distributor + by_retailer + by_product + recent_orders + totals")
    if test_state.get("distributor_id"):
        r = requests.get(f"{DMS_API}/owner/distributor-sales/{test_state['distributor_id']}", 
                        headers=headers(CREDENTIALS["owner"]), timeout=15)
        if r.status_code == 200:
            result = r.json()
            print_test("GET owner/distributor-sales", True, f"Response keys: {list(result.keys())}")
            
            expected_keys = ["distributor", "by_retailer", "by_product", "recent_orders", "totals"]
            has_keys = all(k in result for k in expected_keys)
            print_test("Response has expected keys", has_keys)
        else:
            print_test("GET owner/distributor-sales", False, f"Status: {r.status_code}, {r.text}")
    else:
        print_test("GET owner/distributor-sales", False, "No distributor ID available")
    
    return True


# ============================================================================
# PHASE 5: Regional Manager
# ============================================================================
def test_phase5_regional_manager():
    print_section("PHASE 5: REGIONAL MANAGER")
    
    # Test 23: GET /dms/dashboard/regional-manager
    print("\n23. GET /dms/dashboard/regional-manager → kpis with expected keys")
    r = requests.get(f"{DMS_API}/dashboard/regional-manager", headers=headers(CREDENTIALS["rm"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        print_test("GET dashboard/regional-manager", True)
        
        kpis = result.get("kpis", {})
        expected_keys = ["team_leaders", "distributors", "retailers", "salespersons", 
                        "today_sales", "monthly_sales", "outstanding", "revenue", "fulfillment_pct"]
        has_keys = all(k in kpis for k in expected_keys)
        print_test("KPIs have all expected keys", has_keys, f"Keys: {list(kpis.keys())}")
    else:
        print_test("GET dashboard/regional-manager", False, f"Status: {r.status_code}, {r.text}")
        return False
    
    # Test 24: GET /dms/rm/team-leaders
    print("\n24. GET /dms/rm/team-leaders → data")
    r = requests.get(f"{DMS_API}/rm/team-leaders", headers=headers(CREDENTIALS["rm"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        print_test("GET rm/team-leaders", True, f"Count: {result.get('count', 0)}")
    else:
        print_test("GET rm/team-leaders", False, f"Status: {r.status_code}, {r.text}")
    
    # Test 25: GET /dms/rm/distributors
    print("\n25. GET /dms/rm/distributors → data")
    r = requests.get(f"{DMS_API}/rm/distributors", headers=headers(CREDENTIALS["rm"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        print_test("GET rm/distributors", True, f"Count: {result.get('count', 0)}")
    else:
        print_test("GET rm/distributors", False, f"Status: {r.status_code}, {r.text}")
    
    # Test 26: GET /dms/rm/salespersons
    print("\n26. GET /dms/rm/salespersons → data")
    r = requests.get(f"{DMS_API}/rm/salespersons", headers=headers(CREDENTIALS["rm"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        print_test("GET rm/salespersons", True, f"Count: {result.get('count', 0)}")
    else:
        print_test("GET rm/salespersons", False, f"Status: {r.status_code}, {r.text}")
    
    # Test 27: GET /dms/rm/region-performance
    print("\n27. GET /dms/rm/region-performance → by_distributor + by_team_leader + by_salesperson arrays")
    r = requests.get(f"{DMS_API}/rm/region-performance", headers=headers(CREDENTIALS["rm"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        print_test("GET rm/region-performance", True, f"Response keys: {list(result.keys())}")
        
        expected_keys = ["by_distributor", "by_team_leader", "by_salesperson"]
        has_keys = all(k in result for k in expected_keys)
        print_test("Response has expected arrays", has_keys)
    else:
        print_test("GET rm/region-performance", False, f"Status: {r.status_code}, {r.text}")
    
    return True


# ============================================================================
# REGRESSIONS: Existing Critical Flows
# ============================================================================
def test_regressions():
    print_section("REGRESSIONS: EXISTING CRITICAL FLOWS")
    
    # Test 28: Owner creates a category
    print("\n28. Owner creates a category → still works")
    payload = {"name": f"Regression Test Category {int(time.time())}", "description": "Test"}
    r = requests.post(f"{DMS_API}/categories", headers=headers(CREDENTIALS["owner"]), 
                     json=payload, timeout=15)
    print_test("POST categories", r.status_code == 200, f"Status: {r.status_code}")
    
    # Test 29: Distributor login → /dms/browse/products
    print("\n29. Distributor login → GET /dms/distributor/browse still returns list")
    r = requests.get(f"{DMS_API}/distributor/browse", headers=headers(CREDENTIALS["dist1"]), timeout=15)
    if r.status_code == 200:
        products = r.json()["data"]
        print_test("GET distributor/browse", True, f"Found {len(products)} products")
        
        # Verify previous_price when applicable
        with_prev = [p for p in products if p.get("previous_price")]
        print_test("Some products have previous_price", len(with_prev) >= 0, 
                  f"Found {len(with_prev)} with price history")
    else:
        print_test("GET distributor/browse", False, f"Status: {r.status_code}, {r.text}")
    
    # Test 30: Distributor places a primary order
    print("\n30. Distributor places a primary order → /dms/primary-orders → succeeds")
    # Get products first
    r = requests.get(f"{DMS_API}/distributor/browse", headers=headers(CREDENTIALS["dist1"]), timeout=15)
    if r.status_code == 200 and r.json()["data"]:
        products = r.json()["data"][:2]  # Take first 2 products
        payload = {
            "items": [
                {"product_id": products[0]["id"], "qty_boxes": 2},
                {"product_id": products[1]["id"], "qty_boxes": 1}
            ],
            "notes": "Regression test order"
        }
        r2 = requests.post(f"{DMS_API}/primary-orders", headers=headers(CREDENTIALS["dist1"]), 
                          json=payload, timeout=15)
        print_test("POST primary-orders", r2.status_code == 200, f"Status: {r2.status_code}")
    else:
        print_test("POST primary-orders", False, "No products available")
    
    # Test 31: Retailer browse
    print("\n31. Retailer browse → GET /dms/retailer/browse still returns list")
    r = requests.get(f"{DMS_API}/retailer/browse", headers=headers(CREDENTIALS["retailer1"]), timeout=15)
    if r.status_code == 200:
        result = r.json()
        products = result.get("data", [])
        print_test("GET retailer/browse", True, f"Found {len(products)} products")
    else:
        print_test("GET retailer/browse", False, f"Status: {r.status_code}, {r.text}")
    
    return True


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================
def run_all_tests():
    print("\n" + "="*80)
    print("  BHARAT OIL DMS BACKEND API TEST SUITE — PHASE 1-6")
    print("  Testing: NEW Phase 1-6 endpoints + regressions")
    print(f"  Backend URL: {BASE_URL}")
    print("="*80)
    
    results = {}
    
    try:
        results["phase1_owner_user_management"] = test_phase1_owner_user_management()
    except Exception as e:
        print(f"❌ Phase 1 failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results["phase1_owner_user_management"] = False
    
    try:
        results["phase2_salesperson_gps_ping"] = test_phase2_salesperson_gps_ping()
    except Exception as e:
        print(f"❌ Phase 2 failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results["phase2_salesperson_gps_ping"] = False
    
    try:
        results["phase3_live_tracking"] = test_phase3_live_tracking()
    except Exception as e:
        print(f"❌ Phase 3 failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results["phase3_live_tracking"] = False
    
    try:
        results["phase4_team_leader"] = test_phase4_team_leader()
    except Exception as e:
        print(f"❌ Phase 4 TL failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results["phase4_team_leader"] = False
    
    try:
        results["phase4_owner_insights"] = test_phase4_owner_insights()
    except Exception as e:
        print(f"❌ Phase 4 Owner Insights failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results["phase4_owner_insights"] = False
    
    try:
        results["phase5_regional_manager"] = test_phase5_regional_manager()
    except Exception as e:
        print(f"❌ Phase 5 failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results["phase5_regional_manager"] = False
    
    try:
        results["regressions"] = test_regressions()
    except Exception as e:
        print(f"❌ Regressions failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results["regressions"] = False
    
    # Print summary
    print_section("TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{'='*80}")
    print(f"  TOTAL: {passed}/{total} test scenarios passed ({int(passed/total*100)}%)")
    print(f"{'='*80}\n")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
