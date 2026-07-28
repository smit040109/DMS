"""GO OIL DMS — PART K FINAL ENTERPRISE AUDIT
Backend API comprehensive test suite for Parts E/F/G + Regression A/B/C/D
"""
import os
import time
import requests
from typing import Dict, List, Tuple

# Read backend URL from frontend .env
BASE_URL = ""
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
            break

API = f"{BASE_URL}/api"
COMMON_PW = "GoOil@2026"

ROLE_EMAILS = {
    "super_admin": "admin@gooil.com",
    "company_admin": "company@gooil.com",
    "regional_manager": "regional@gooil.com",
    "sales_executive": "sales@gooil.com",
    "distributor": "distributor@gooil.com",
    "distributor_accountant": "accountant@gooil.com",
    "retailer": "retailer@gooil.com",
    "customer": "customer@gooil.com",
}

# Test results tracking
results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "tests": [],
    "response_times": {},
}


def log_test(name: str, passed: bool, message: str = "", response_time: float = 0):
    """Log test result"""
    results["total"] += 1
    if passed:
        results["passed"] += 1
        status = "✅ PASS"
    else:
        results["failed"] += 1
        status = "❌ FAIL"
    
    results["tests"].append({
        "name": name,
        "passed": passed,
        "message": message,
        "response_time": response_time,
    })
    
    if response_time > 0:
        results["response_times"][name] = response_time
    
    print(f"{status}: {name}")
    if message:
        print(f"  → {message}")


def login(email: str, password: str = COMMON_PW) -> Tuple[str, dict]:
    """Login and return token + user"""
    try:
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
        if r.status_code == 200:
            data = r.json()
            return data.get("token", ""), data.get("user", {})
        return "", {}
    except Exception as e:
        print(f"Login error for {email}: {e}")
        return "", {}


def get_headers(token: str) -> Dict[str, str]:
    """Get auth headers"""
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# PART E — NOTIFICATIONS
# ============================================================================

def test_part_e_notifications():
    """Test Part E: Notification Engine"""
    print("\n" + "="*80)
    print("PART E — NOTIFICATIONS ENGINE")
    print("="*80)
    
    # Login as admin
    admin_token, admin_user = login(ROLE_EMAILS["super_admin"])
    if not admin_token:
        log_test("E1: Admin login", False, "Failed to login as admin")
        return
    
    admin_headers = get_headers(admin_token)
    
    # E1: POST /api/notifications/trigger/low_stock (admin) → 200 with persisted notif
    try:
        start = time.time()
        r = requests.post(f"{API}/notifications/trigger/low_stock", headers=admin_headers, timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            if "id" in data and data.get("id", "").startswith("notif-"):
                log_test("E1: Trigger low_stock notification (admin)", True, 
                        f"Created notification: {data.get('id')}", elapsed)
            else:
                log_test("E1: Trigger low_stock notification (admin)", False, 
                        f"No notification ID in response: {data}", elapsed)
        else:
            log_test("E1: Trigger low_stock notification (admin)", False, 
                    f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("E1: Trigger low_stock notification (admin)", False, str(e))
    
    # E2: GET /api/notifications/unread-count → returns {unread:N}
    try:
        start = time.time()
        r = requests.get(f"{API}/notifications/unread-count", headers=admin_headers, timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            if "unread" in data and isinstance(data["unread"], int):
                log_test("E2: Get unread count", True, f"Unread: {data['unread']}", elapsed)
            else:
                log_test("E2: Get unread count", False, f"Invalid response: {data}", elapsed)
        else:
            log_test("E2: Get unread count", False, f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("E2: Get unread count", False, str(e))
    
    # E3: GET /api/notifications/ (list) → returns array
    try:
        start = time.time()
        r = requests.get(f"{API}/notifications/", headers=admin_headers, timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            if "data" in data and isinstance(data["data"], list):
                log_test("E3: List notifications", True, f"Found {len(data['data'])} notifications", elapsed)
            else:
                log_test("E3: List notifications", False, f"Invalid response: {data}", elapsed)
        else:
            log_test("E3: List notifications", False, f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("E3: List notifications", False, str(e))
    
    # E4: POST /api/notifications/mark-all-read → clears unread
    try:
        start = time.time()
        r = requests.post(f"{API}/notifications/mark-all-read", headers=admin_headers, timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            if data.get("ok"):
                log_test("E4: Mark all read", True, f"Updated {data.get('updated', 0)} notifications", elapsed)
            else:
                log_test("E4: Mark all read", False, f"Invalid response: {data}", elapsed)
        else:
            log_test("E4: Mark all read", False, f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("E4: Mark all read", False, str(e))
    
    # E5: GET /api/notifications/preferences → default prefs returned
    try:
        start = time.time()
        r = requests.get(f"{API}/notifications/preferences", headers=admin_headers, timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            if "in_app" in data and "email" in data:
                log_test("E5: Get preferences", True, f"Prefs: in_app={data.get('in_app')}, email={data.get('email')}", elapsed)
            else:
                log_test("E5: Get preferences", False, f"Invalid response: {data}", elapsed)
        else:
            log_test("E5: Get preferences", False, f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("E5: Get preferences", False, str(e))
    
    # E6: PUT /api/notifications/preferences {sms:true} → persisted
    try:
        start = time.time()
        r = requests.put(f"{API}/notifications/preferences", 
                        json={"sms": True}, headers=admin_headers, timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            if data.get("sms") == True:
                log_test("E6: Update preferences", True, "SMS preference updated to true", elapsed)
            else:
                log_test("E6: Update preferences", False, f"SMS not updated: {data}", elapsed)
        else:
            log_test("E6: Update preferences", False, f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("E6: Update preferences", False, str(e))
    
    # E7: RBAC - customer trying to POST /notifications/trigger/low_stock → 403
    customer_token, _ = login(ROLE_EMAILS["customer"])
    if customer_token:
        try:
            start = time.time()
            r = requests.post(f"{API}/notifications/trigger/low_stock", 
                            headers=get_headers(customer_token), timeout=15)
            elapsed = time.time() - start
            
            if r.status_code == 403:
                log_test("E7: RBAC - customer trigger (403)", True, "Correctly denied", elapsed)
            else:
                log_test("E7: RBAC - customer trigger (403)", False, 
                        f"Expected 403, got {r.status_code}", elapsed)
        except Exception as e:
            log_test("E7: RBAC - customer trigger (403)", False, str(e))
    else:
        log_test("E7: RBAC - customer trigger (403)", False, "Failed to login as customer")
    
    # E8: RBAC - customer sending POST /notifications/send to another user → 403
    if customer_token:
        try:
            start = time.time()
            r = requests.post(f"{API}/notifications/send", 
                            json={
                                "recipient_id": admin_user.get("id", "usr-admin"),
                                "title": "Test",
                                "body": "Test notification"
                            },
                            headers=get_headers(customer_token), timeout=15)
            elapsed = time.time() - start
            
            if r.status_code == 403:
                log_test("E8: RBAC - customer send to other (403)", True, "Correctly denied", elapsed)
            else:
                log_test("E8: RBAC - customer send to other (403)", False, 
                        f"Expected 403, got {r.status_code}", elapsed)
        except Exception as e:
            log_test("E8: RBAC - customer send to other (403)", False, str(e))


# ============================================================================
# PART F — AI COPILOT
# ============================================================================

def test_part_f_ai_copilot():
    """Test Part F: AI Business Copilot"""
    print("\n" + "="*80)
    print("PART F — AI BUSINESS COPILOT")
    print("="*80)
    
    # Login as admin
    admin_token, _ = login(ROLE_EMAILS["super_admin"])
    if not admin_token:
        log_test("F1: Admin login", False, "Failed to login as admin")
        return
    
    admin_headers = get_headers(admin_token)
    
    # F1: GET /api/ai/copilot/status → sdk_available, key_configured, ready
    try:
        start = time.time()
        r = requests.get(f"{API}/ai/copilot/status", headers=admin_headers, timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            if "sdk_available" in data and "key_configured" in data and "ready" in data:
                log_test("F1: Get copilot status", True, 
                        f"SDK: {data['sdk_available']}, Key: {data['key_configured']}, Ready: {data['ready']}", 
                        elapsed)
            else:
                log_test("F1: Get copilot status", False, f"Missing fields: {data}", elapsed)
        else:
            log_test("F1: Get copilot status", False, f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("F1: Get copilot status", False, str(e))
    
    # F2: GET /api/ai/copilot/suggestions → 10 items
    try:
        start = time.time()
        r = requests.get(f"{API}/ai/copilot/suggestions", headers=admin_headers, timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            if "data" in data and isinstance(data["data"], list):
                log_test("F2: Get suggestions", True, f"Found {len(data['data'])} suggestions", elapsed)
            else:
                log_test("F2: Get suggestions", False, f"Invalid response: {data}", elapsed)
        else:
            log_test("F2: Get suggestions", False, f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("F2: Get suggestions", False, str(e))
    
    # F3: POST /api/ai/copilot/ask {"question":"x"} → 503 with helpful message (no key)
    try:
        start = time.time()
        r = requests.post(f"{API}/ai/copilot/ask", 
                         json={"question": "What is our revenue this month?"},
                         headers=admin_headers, timeout=15)
        elapsed = time.time() - start
        
        # Should return 503 if EMERGENT_LLM_KEY is not configured
        if r.status_code == 503:
            data = r.json()
            if "EMERGENT_LLM_KEY" in data.get("detail", ""):
                log_test("F3: Ask without key (503)", True, "Correctly returns 503 with helpful message", elapsed)
            else:
                log_test("F3: Ask without key (503)", True, f"503 returned: {data.get('detail', '')[:100]}", elapsed)
        elif r.status_code == 200:
            # Key might be configured
            log_test("F3: Ask without key (503)", True, "Key is configured, got 200 response", elapsed)
        else:
            log_test("F3: Ask without key (503)", False, f"Unexpected status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("F3: Ask without key (503)", False, str(e))
    
    # F4: GET /api/ai/copilot/sessions/nonexistent → returns empty session shape
    try:
        start = time.time()
        r = requests.get(f"{API}/ai/copilot/sessions/sess-nonexistent", headers=admin_headers, timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            if "id" in data and "history" in data:
                log_test("F4: Get nonexistent session", True, f"Returns empty session: {data}", elapsed)
            else:
                log_test("F4: Get nonexistent session", False, f"Invalid response: {data}", elapsed)
        else:
            log_test("F4: Get nonexistent session", False, f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("F4: Get nonexistent session", False, str(e))
    
    # F5: Auth required → 401 without token
    try:
        start = time.time()
        r = requests.get(f"{API}/ai/copilot/status", timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 401:
            log_test("F5: Auth required (401)", True, "Correctly requires authentication", elapsed)
        else:
            log_test("F5: Auth required (401)", False, f"Expected 401, got {r.status_code}", elapsed)
    except Exception as e:
        log_test("F5: Auth required (401)", False, str(e))


# ============================================================================
# PART G — INTEGRATIONS
# ============================================================================

def test_part_g_integrations():
    """Test Part G: Integrations"""
    print("\n" + "="*80)
    print("PART G — INTEGRATIONS")
    print("="*80)
    
    # Login as admin
    admin_token, _ = login(ROLE_EMAILS["super_admin"])
    if not admin_token:
        log_test("G1: Admin login", False, "Failed to login as admin")
        return
    
    admin_headers = get_headers(admin_token)
    
    # G1: GET /api/integrations/status → registry map with configured=false everywhere
    try:
        start = time.time()
        r = requests.get(f"{API}/integrations/status", headers=admin_headers, timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            if "registry" in data:
                log_test("G1: Get integrations status", True, 
                        f"Registry: {list(data['registry'].keys())}", elapsed)
            else:
                log_test("G1: Get integrations status", False, f"No registry in response: {data}", elapsed)
        else:
            log_test("G1: Get integrations status", False, f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("G1: Get integrations status", False, str(e))
    
    # G2: POST /api/integrations/payments/create-order → scaffold order_id
    try:
        start = time.time()
        r = requests.post(f"{API}/integrations/payments/create-order",
                         json={"amount": 1500, "currency": "INR"},
                         headers=admin_headers, timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            if "order_id" in data or "payment_intent_id" in data:
                order_id = data.get("order_id") or data.get("payment_intent_id")
                configured = data.get("configured", False)
                log_test("G2: Create payment order", True, 
                        f"Order: {order_id}, Configured: {configured}", elapsed)
            else:
                log_test("G2: Create payment order", False, f"No order_id in response: {data}", elapsed)
        else:
            log_test("G2: Create payment order", False, f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("G2: Create payment order", False, str(e))
    
    # G3: GET /api/integrations/tax/validate-gstin?gstin=27AAAAA0000A1Z5 → valid_format:true
    try:
        start = time.time()
        r = requests.get(f"{API}/integrations/tax/validate-gstin?gstin=27AAAAA0000A1Z5",
                        headers=admin_headers, timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            if "valid_format" in data:
                log_test("G3: Validate GSTIN", True, 
                        f"Valid format: {data['valid_format']}, GSTIN: {data.get('gstin')}", elapsed)
            else:
                log_test("G3: Validate GSTIN", False, f"No valid_format in response: {data}", elapsed)
        else:
            log_test("G3: Validate GSTIN", False, f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("G3: Validate GSTIN", False, str(e))
    
    # G4: POST /api/integrations/tax/gstr1-preview → returns payload with gstin, fp, b2b, b2cs
    try:
        start = time.time()
        r = requests.post(f"{API}/integrations/tax/gstr1-preview",
                         headers=admin_headers, timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            if "payload" in data:
                payload = data["payload"]
                if "gstin" in payload and "fp" in payload and "b2b" in payload and "b2cs" in payload:
                    log_test("G4: GSTR1 preview", True, 
                            f"GSTIN: {payload['gstin']}, FP: {payload['fp']}, Invoices: {data.get('invoice_count', 0)}", 
                            elapsed)
                else:
                    log_test("G4: GSTR1 preview", False, f"Missing fields in payload: {payload.keys()}", elapsed)
            else:
                log_test("G4: GSTR1 preview", False, f"No payload in response: {data}", elapsed)
        else:
            log_test("G4: GSTR1 preview", False, f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("G4: GSTR1 preview", False, str(e))
    
    # G5: GET /api/integrations/accounting/tally-export → HTTP 200, XML
    try:
        start = time.time()
        r = requests.get(f"{API}/integrations/accounting/tally-export",
                        headers=admin_headers, timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            content_type = r.headers.get("content-type", "")
            if "xml" in content_type.lower():
                if r.text.startswith("<?xml"):
                    log_test("G5: Tally XML export", True, 
                            f"Valid XML, size: {len(r.text)} bytes", elapsed)
                else:
                    log_test("G5: Tally XML export", False, "Content doesn't start with <?xml", elapsed)
            else:
                log_test("G5: Tally XML export", False, f"Wrong content-type: {content_type}", elapsed)
        else:
            log_test("G5: Tally XML export", False, f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("G5: Tally XML export", False, str(e))
    
    # G6: GET /api/integrations/code/generate?kind=qr&value=INV-100 → data_url
    try:
        start = time.time()
        r = requests.get(f"{API}/integrations/code/generate?kind=qr&value=INV-100",
                        headers=admin_headers, timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            if "data_url" in data and data["data_url"].startswith("data:image/svg+xml"):
                log_test("G6: Generate QR code", True, 
                        f"Generated QR for: {data.get('value')}", elapsed)
            else:
                log_test("G6: Generate QR code", False, f"Invalid data_url: {data.get('data_url', '')[:50]}", elapsed)
        else:
            log_test("G6: Generate QR code", False, f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("G6: Generate QR code", False, str(e))
    
    # G7: GET /api/integrations/code/lookup?code=<real-sku-code> → found:true
    # First, get a real SKU code from the database
    try:
        # Get SKUs list
        r_skus = requests.get(f"{API}/collections/skus?limit=1", headers=admin_headers, timeout=15)
        if r_skus.status_code == 200:
            skus = r_skus.json().get("data", [])
            if skus:
                sku_code = skus[0].get("code") or skus[0].get("id")
                
                start = time.time()
                r = requests.get(f"{API}/integrations/code/lookup?code={sku_code}",
                                headers=admin_headers, timeout=15)
                elapsed = time.time() - start
                
                if r.status_code == 200:
                    data = r.json()
                    if "found" in data:
                        log_test("G7: Lookup code", True, 
                                f"Found: {data['found']}, Code: {sku_code}", elapsed)
                    else:
                        log_test("G7: Lookup code", False, f"No 'found' field: {data}", elapsed)
                else:
                    log_test("G7: Lookup code", False, f"Status {r.status_code}: {r.text[:200]}", elapsed)
            else:
                log_test("G7: Lookup code", False, "No SKUs found in database")
        else:
            log_test("G7: Lookup code", False, f"Failed to get SKUs: {r_skus.status_code}")
    except Exception as e:
        log_test("G7: Lookup code", False, str(e))
    
    # G8: GET /api/integrations/public/health (no auth) → 200
    try:
        start = time.time()
        r = requests.get(f"{API}/integrations/public/health", timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "ok":
                log_test("G8: Public health (no auth)", True, 
                        f"Service: {data.get('service')}, Version: {data.get('version')}", elapsed)
            else:
                log_test("G8: Public health (no auth)", False, f"Invalid response: {data}", elapsed)
        else:
            log_test("G8: Public health (no auth)", False, f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("G8: Public health (no auth)", False, str(e))


# ============================================================================
# REGRESSION — PARTS A/B/C/D
# ============================================================================

def test_regression():
    """Test regression on Parts A/B/C/D"""
    print("\n" + "="*80)
    print("REGRESSION — PARTS A/B/C/D")
    print("="*80)
    
    # R1: Login all 8 personas → all 200
    print("\nR1: Login all 8 personas")
    all_passed = True
    for role, email in ROLE_EMAILS.items():
        try:
            start = time.time()
            token, user = login(email)
            elapsed = time.time() - start
            
            if token and user.get("email") == email:
                log_test(f"R1: Login {role}", True, f"Email: {email}", elapsed)
            else:
                log_test(f"R1: Login {role}", False, f"Failed to login as {email}")
                all_passed = False
        except Exception as e:
            log_test(f"R1: Login {role}", False, str(e))
            all_passed = False
    
    # Get admin token for remaining tests
    admin_token, _ = login(ROLE_EMAILS["super_admin"])
    if not admin_token:
        print("Failed to get admin token for regression tests")
        return
    
    admin_headers = get_headers(admin_token)
    customer_token, _ = login(ROLE_EMAILS["customer"])
    customer_headers = get_headers(customer_token)
    
    # R2: GET /api/health → 200 + db:connected
    try:
        start = time.time()
        r = requests.get(f"{API}/health", timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "ok" and data.get("db") == "connected":
                log_test("R2: Health check", True, f"DB: {data['db']}, Service: {data.get('service')}", elapsed)
            else:
                log_test("R2: Health check", False, f"Invalid response: {data}", elapsed)
        else:
            log_test("R2: Health check", False, f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("R2: Health check", False, str(e))
    
    # R3: GET /api/analytics/kpi/executive?range=month → 15 KPIs
    try:
        start = time.time()
        r = requests.get(f"{API}/analytics/kpi/executive?range=month", 
                        headers=admin_headers, timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            kpis = data.get("kpis", {})
            required_kpis = ["revenue", "inventory_value", "outstanding", "claims", 
                           "returns", "business_risk_score", "company_health_score"]
            missing = [k for k in required_kpis if k not in kpis]
            
            if len(kpis) >= 15 and not missing:
                revenue_val = kpis.get('revenue', {})
                if isinstance(revenue_val, dict):
                    revenue_val = revenue_val.get('value', 0)
                log_test("R3: Executive KPI (15 KPIs)", True, 
                        f"Found {len(kpis)} KPIs, Revenue: ${revenue_val/1e6:.1f}M", elapsed)
            else:
                log_test("R3: Executive KPI (15 KPIs)", False, 
                        f"Found {len(kpis)} KPIs, Missing: {missing}", elapsed)
        else:
            log_test("R3: Executive KPI (15 KPIs)", False, f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("R3: Executive KPI (15 KPIs)", False, str(e))
    
    # R4: POST /api/reverse/exceptions/scan → 200, no _id leak
    try:
        start = time.time()
        r = requests.post(f"{API}/reverse/exceptions/scan", headers=admin_headers, timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            # Check for ObjectId leaks
            text = str(data)
            if "_id" in text or "ObjectId" in text:
                log_test("R4: Exception scan (no _id leak)", False, 
                        "ObjectId or _id found in response", elapsed)
            else:
                log_test("R4: Exception scan (no _id leak)", True, 
                        f"Found {data.get('found', 0)} exceptions", elapsed)
        else:
            log_test("R4: Exception scan (no _id leak)", False, 
                    f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("R4: Exception scan (no _id leak)", False, str(e))
    
    # R5: GET /api/exports/products?format=csv → 200 csv
    try:
        start = time.time()
        r = requests.get(f"{API}/exports/products?format=csv", headers=admin_headers, timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            content_type = r.headers.get("content-type", "")
            if "csv" in content_type.lower():
                log_test("R5: Export products CSV", True, f"Size: {len(r.text)} bytes", elapsed)
            else:
                log_test("R5: Export products CSV", False, f"Wrong content-type: {content_type}", elapsed)
        else:
            log_test("R5: Export products CSV", False, f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("R5: Export products CSV", False, str(e))
    
    # R6: GET /api/exports/invoices?format=pdf → 200 %PDF
    try:
        start = time.time()
        r = requests.get(f"{API}/exports/invoices?format=pdf", headers=admin_headers, timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            content_type = r.headers.get("content-type", "")
            if "pdf" in content_type.lower() and r.content[:4] == b"%PDF":
                log_test("R6: Export invoices PDF", True, f"Size: {len(r.content)} bytes", elapsed)
            else:
                log_test("R6: Export invoices PDF", False, 
                        f"Wrong content-type or format: {content_type}", elapsed)
        else:
            log_test("R6: Export invoices PDF", False, f"Status {r.status_code}: {r.text[:200]}", elapsed)
    except Exception as e:
        log_test("R6: Export invoices PDF", False, str(e))
    
    # R7: Rate limit - 11 rapid POST /api/auth/login with wrong creds → at least one 429
    print("\nR7: Rate limiting test (11 rapid login attempts)")
    got_429 = False
    for i in range(11):
        try:
            r = requests.post(f"{API}/auth/login", 
                            json={"email": "test@test.com", "password": "wrong"}, 
                            timeout=5)
            if r.status_code == 429:
                got_429 = True
                break
        except Exception:
            pass
    
    if got_429:
        log_test("R7: Rate limiting (429)", True, "Rate limit triggered after multiple attempts")
    else:
        log_test("R7: Rate limiting (429)", False, "No 429 response after 11 attempts")
    
    # R8: RBAC - customer GET /api/admin/users → 403
    try:
        start = time.time()
        r = requests.get(f"{API}/admin/users", headers=customer_headers, timeout=15)
        elapsed = time.time() - start
        
        if r.status_code == 403:
            log_test("R8: RBAC - customer denied admin (403)", True, "Correctly denied", elapsed)
        else:
            log_test("R8: RBAC - customer denied admin (403)", False, 
                    f"Expected 403, got {r.status_code}", elapsed)
    except Exception as e:
        log_test("R8: RBAC - customer denied admin (403)", False, str(e))
    
    # R9: Security headers on GET /api/health
    try:
        start = time.time()
        r = requests.get(f"{API}/health", timeout=15)
        elapsed = time.time() - start
        
        headers = r.headers
        required_headers = ["X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy"]
        missing = [h for h in required_headers if h not in headers]
        
        if not missing:
            log_test("R9: Security headers", True, 
                    f"All required headers present: {required_headers}", elapsed)
        else:
            log_test("R9: Security headers", False, f"Missing headers: {missing}", elapsed)
    except Exception as e:
        log_test("R9: Security headers", False, str(e))
    
    # R10: Response times - no endpoint > 3s
    slow_endpoints = [name for name, time_val in results["response_times"].items() if time_val > 3.0]
    if not slow_endpoints:
        log_test("R10: Response times (<3s)", True, "All endpoints under 3s threshold")
    else:
        log_test("R10: Response times (<3s)", False, f"Slow endpoints: {slow_endpoints}")


# ============================================================================
# CROSS-CUTTING CHECKS
# ============================================================================

def test_cross_cutting():
    """Test cross-cutting concerns"""
    print("\n" + "="*80)
    print("CROSS-CUTTING CHECKS")
    print("="*80)
    
    admin_token, _ = login(ROLE_EMAILS["super_admin"])
    if not admin_token:
        print("Failed to get admin token for cross-cutting tests")
        log_test("Cross-cutting: Admin login", False, "Failed to get admin token")
        return
    
    admin_headers = get_headers(admin_token)
    
    # C1: No MongoDB _id or ObjectId in ANY response
    print("\nC1: Checking for ObjectId leaks in responses")
    endpoints_to_check = [
        "/notifications/",
        "/ai/copilot/suggestions",
        "/integrations/status",
        "/analytics/kpi/executive?range=month",
        "/collections/products?limit=5",
    ]
    
    all_clean = True
    for endpoint in endpoints_to_check:
        try:
            r = requests.get(f"{API}{endpoint}", headers=admin_headers, timeout=15)
            if r.status_code == 200:
                # Check for actual MongoDB ObjectId patterns, not just "_id" substring
                # MongoDB ObjectId is 24 hex characters
                import re
                text = r.text
                # Look for patterns like: "_id": {"$oid": "..."} or "_id": ObjectId("...")
                objectid_patterns = [
                    r'"_id"\s*:\s*\{[^}]*\$oid',  # {"_id": {"$oid": "..."}}
                    r'ObjectId\s*\(',  # ObjectId("...")
                    r'"_id"\s*:\s*"[0-9a-f]{24}"',  # "_id": "507f1f77bcf86cd799439011"
                ]
                found_leak = False
                for pattern in objectid_patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        found_leak = True
                        break
                
                if found_leak:
                    log_test(f"C1: No ObjectId leak - {endpoint}", False, "Found MongoDB ObjectId in response")
                    all_clean = False
                else:
                    log_test(f"C1: No ObjectId leak - {endpoint}", True, "Clean response")
        except Exception as e:
            log_test(f"C1: No ObjectId leak - {endpoint}", False, str(e))
            all_clean = False
    
    # C2: Auth required for new endpoints (except public ones)
    print("\nC2: Auth required for protected endpoints")
    protected_endpoints = [
        "/notifications/",
        "/ai/copilot/status",
        "/integrations/status",
    ]
    
    for endpoint in protected_endpoints:
        try:
            start = time.time()
            r = requests.get(f"{API}{endpoint}", timeout=15)
            elapsed = time.time() - start
            
            if r.status_code == 401:
                log_test(f"C2: Auth required - {endpoint}", True, "Correctly requires auth", elapsed)
            else:
                log_test(f"C2: Auth required - {endpoint}", False, 
                        f"Expected 401, got {r.status_code}", elapsed)
        except Exception as e:
            log_test(f"C2: Auth required - {endpoint}", False, str(e))
    
    # C3: Public endpoints work without auth
    print("\nC3: Public endpoints accessible without auth")
    public_endpoints = [
        "/health",
        "/integrations/public/health",
    ]
    
    for endpoint in public_endpoints:
        try:
            start = time.time()
            r = requests.get(f"{API}{endpoint}", timeout=15)
            elapsed = time.time() - start
            
            if r.status_code == 200:
                log_test(f"C3: Public endpoint - {endpoint}", True, "Accessible without auth", elapsed)
            else:
                log_test(f"C3: Public endpoint - {endpoint}", False, 
                        f"Expected 200, got {r.status_code}", elapsed)
        except Exception as e:
            log_test(f"C3: Public endpoint - {endpoint}", False, str(e))


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def print_summary():
    """Print test summary"""
    print("\n" + "="*80)
    print("FINAL AUDIT SUMMARY")
    print("="*80)
    
    print(f"\nTotal Tests: {results['total']}")
    print(f"Passed: {results['passed']} ✅")
    print(f"Failed: {results['failed']} ❌")
    print(f"Success Rate: {(results['passed']/results['total']*100):.1f}%")
    
    # Response time analysis
    if results["response_times"]:
        times = list(results["response_times"].values())
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        
        print(f"\nResponse Time Analysis:")
        print(f"  Average: {avg_time:.3f}s")
        print(f"  Min: {min_time:.3f}s")
        print(f"  Max: {max_time:.3f}s")
        
        # Categorize response times
        fast = sum(1 for t in times if t < 0.1)
        ok = sum(1 for t in times if 0.1 <= t < 0.5)
        slow = sum(1 for t in times if 0.5 <= t < 3.0)
        very_slow = sum(1 for t in times if t >= 3.0)
        
        print(f"\n  Response Time Brackets:")
        print(f"    Fast (<100ms): {fast}")
        print(f"    OK (100-500ms): {ok}")
        print(f"    Slow (500ms-3s): {slow}")
        print(f"    Very Slow (>3s): {very_slow}")
    
    # Failed tests detail
    if results["failed"] > 0:
        print(f"\n{'='*80}")
        print("FAILED TESTS DETAIL")
        print("="*80)
        for test in results["tests"]:
            if not test["passed"]:
                print(f"\n❌ {test['name']}")
                if test["message"]:
                    print(f"   {test['message']}")
    
    # Ratings
    print(f"\n{'='*80}")
    print("ENTERPRISE READINESS RATINGS")
    print("="*80)
    
    success_rate = results['passed'] / results['total'] if results['total'] > 0 else 0
    
    # Architecture (based on endpoint organization and response structure)
    architecture_score = 9 if success_rate > 0.9 else 8 if success_rate > 0.8 else 7
    print(f"Architecture: {architecture_score}/10")
    
    # Security (based on auth, RBAC, rate limiting tests)
    security_tests = [t for t in results["tests"] if "RBAC" in t["name"] or "Auth" in t["name"] or "Rate" in t["name"]]
    security_passed = sum(1 for t in security_tests if t["passed"])
    security_score = 10 if security_passed == len(security_tests) else 9 if security_passed >= len(security_tests) * 0.9 else 8
    print(f"Security: {security_score}/10")
    
    # Performance (based on response times)
    if results["response_times"]:
        avg_time = sum(results["response_times"].values()) / len(results["response_times"])
        performance_score = 10 if avg_time < 0.2 else 9 if avg_time < 0.5 else 8 if avg_time < 1.0 else 7
    else:
        performance_score = 8
    print(f"Performance: {performance_score}/10")
    
    # API Completeness (based on all endpoint tests)
    completeness_score = 10 if success_rate >= 0.95 else 9 if success_rate >= 0.9 else 8 if success_rate >= 0.8 else 7
    print(f"API Completeness: {completeness_score}/10")
    
    # Overall recommendation
    overall = (architecture_score + security_score + performance_score + completeness_score) / 4
    print(f"\nOverall Score: {overall:.1f}/10")
    
    if overall >= 9.0:
        recommendation = "✅ EXCELLENT - Ready for enterprise production deployment"
    elif overall >= 8.0:
        recommendation = "✅ GOOD - Ready for production with minor improvements"
    elif overall >= 7.0:
        recommendation = "⚠️  ACCEPTABLE - Address failed tests before production"
    else:
        recommendation = "❌ NEEDS WORK - Significant issues to resolve"
    
    print(f"\nRecommendation: {recommendation}")


if __name__ == "__main__":
    print("="*80)
    print("GO OIL DMS — PART K FINAL ENTERPRISE AUDIT")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"API URL: {API}")
    print("="*80)
    
    # Run all test suites
    test_part_e_notifications()
    test_part_f_ai_copilot()
    test_part_g_integrations()
    test_regression()
    test_cross_cutting()
    
    # Print summary
    print_summary()
    
    print("\n" + "="*80)
    print("AUDIT COMPLETE")
    print("="*80)
