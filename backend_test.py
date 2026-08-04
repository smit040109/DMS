#!/usr/bin/env python3
"""
Phase 2A Backend Testing — Expenses CRUD, FY Close, Editable Invoice Numbers, Invoice T&C
All test credentials in /app/memory/test_credentials.md — passwords are GoOil@2026
Base URL from /app/frontend/.env: REACT_APP_BACKEND_URL
All endpoints prefixed with /api
"""
import requests
import json
from datetime import datetime, timedelta

# Read base URL from frontend/.env
with open("/app/frontend/.env", "r") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=")[1].strip()
            break

API_BASE = f"{BASE_URL}/api"
PASSWORD = "GoOil@2026"

# Test accounts
ACCOUNTS = {
    "owner": "owner@gooil.com",
    "accountant": "accountant@gooil.com",
    "distributor1": "distributor1@gooil.com",
    "distributor2": "distributor2@gooil.com",
    "retailer1": "retailer1@gooil.com",
    "salesperson": "salesperson@gooil.com",
}

def login(email: str) -> str:
    """Login and return JWT token"""
    resp = requests.post(f"{API_BASE}/auth/login", json={"email": email, "password": PASSWORD})
    if resp.status_code != 200:
        raise Exception(f"Login failed for {email}: {resp.status_code} {resp.text}")
    return resp.json()["token"]

def headers(token: str) -> dict:
    """Return authorization headers"""
    return {"Authorization": f"Bearer {token}"}

# ============================================================================
# TEST SUITE
# ============================================================================
def main():
    print("=" * 80)
    print("PHASE 2A BACKEND TESTING — GO OIL DMS")
    print("=" * 80)
    
    # Login all accounts
    print("\n[1] Logging in all test accounts...")
    tokens = {}
    for role, email in ACCOUNTS.items():
        try:
            tokens[role] = login(email)
            print(f"  ✅ {role}: {email}")
        except Exception as e:
            print(f"  ❌ {role}: {email} — {e}")
            return
    
    print(f"\n✅ All {len(tokens)} accounts logged in successfully\n")
    
    # ========================================================================
    # TEST 1: EXPENSES CRUD — RBAC
    # ========================================================================
    print("=" * 80)
    print("TEST 1: EXPENSES CRUD — RBAC")
    print("=" * 80)
    
    # 1.1: Retailer GET /api/dms/expenses → 403
    print("\n[1.1] Retailer GET /api/dms/expenses → 403 Forbidden")
    resp = requests.get(f"{API_BASE}/dms/expenses", headers=headers(tokens["retailer1"]))
    if resp.status_code == 403:
        print(f"  ✅ PASS: Retailer blocked (403)")
    else:
        print(f"  ❌ FAIL: Expected 403, got {resp.status_code}")
    
    # 1.2: Salesperson POST /api/dms/expenses → 201/200
    print("\n[1.2] Salesperson POST /api/dms/expenses → 201/200")
    expense_data = {
        "category": "Travel",
        "amount": 500,
        "date": "2026-08-01",
        "description": "Client meet"
    }
    resp = requests.post(f"{API_BASE}/dms/expenses", json=expense_data, headers=headers(tokens["salesperson"]))
    if resp.status_code in [200, 201]:
        sp_expense = resp.json()
        print(f"  ✅ PASS: Expense created (expense_no: {sp_expense.get('expense_no')})")
        sp_expense_id = sp_expense.get("id")
    else:
        print(f"  ❌ FAIL: Expected 200/201, got {resp.status_code} — {resp.text}")
        sp_expense_id = None
    
    # 1.3: Salesperson GET /api/dms/expenses → should return only own expenses
    print("\n[1.3] Salesperson GET /api/dms/expenses → returns only own expenses")
    resp = requests.get(f"{API_BASE}/dms/expenses", headers=headers(tokens["salesperson"]))
    if resp.status_code == 200:
        data = resp.json()
        expenses = data.get("data", [])
        # Check all expenses have created_by == salesperson's id
        sp_user_resp = requests.get(f"{API_BASE}/auth/me", headers=headers(tokens["salesperson"]))
        sp_user_id = sp_user_resp.json().get("id")
        all_own = all(e.get("created_by") == sp_user_id for e in expenses)
        if all_own:
            print(f"  ✅ PASS: Salesperson sees only own expenses (count: {len(expenses)})")
        else:
            print(f"  ❌ FAIL: Salesperson sees expenses from other users")
    else:
        print(f"  ❌ FAIL: Expected 200, got {resp.status_code}")
    
    # 1.4: Owner GET /api/dms/expenses → returns ALL expenses
    print("\n[1.4] Owner GET /api/dms/expenses → returns ALL expenses")
    resp = requests.get(f"{API_BASE}/dms/expenses", headers=headers(tokens["owner"]))
    if resp.status_code == 200:
        data = resp.json()
        expenses = data.get("data", [])
        if len(expenses) > 0:
            print(f"  ✅ PASS: Owner sees all expenses (count: {len(expenses)})")
        else:
            print(f"  ⚠️  WARNING: No expenses found (expected at least 1)")
    else:
        print(f"  ❌ FAIL: Expected 200, got {resp.status_code}")
    
    # 1.5: Owner POST /api/dms/expenses with amount<=0 → 400
    print("\n[1.5] Owner POST /api/dms/expenses with amount<=0 → 400")
    resp = requests.post(f"{API_BASE}/dms/expenses", json={"category": "Test", "amount": 0, "date": "2026-08-01"}, headers=headers(tokens["owner"]))
    if resp.status_code == 400:
        print(f"  ✅ PASS: Amount validation working (400)")
    else:
        print(f"  ❌ FAIL: Expected 400, got {resp.status_code}")
    
    # 1.6: Owner PUT /api/dms/expenses/{id} → 200
    print("\n[1.6] Owner PUT /api/dms/expenses/{id} → 200")
    if sp_expense_id:
        resp = requests.put(f"{API_BASE}/dms/expenses/{sp_expense_id}", json={"category": "Transport", "amount": 600}, headers=headers(tokens["owner"]))
        if resp.status_code == 200:
            print(f"  ✅ PASS: Owner can edit any expense")
        else:
            print(f"  ❌ FAIL: Expected 200, got {resp.status_code}")
    else:
        print(f"  ⚠️  SKIP: No expense ID to test")
    
    # 1.7: Salesperson tries PUT on Owner's expense → 403
    print("\n[1.7] Salesperson tries PUT on Owner's expense → 403")
    # First create an expense as owner
    resp = requests.post(f"{API_BASE}/dms/expenses", json={"category": "Office", "amount": 1000, "date": "2026-08-01"}, headers=headers(tokens["owner"]))
    if resp.status_code in [200, 201]:
        owner_expense_id = resp.json().get("id")
        # Now try to edit as salesperson
        resp = requests.put(f"{API_BASE}/dms/expenses/{owner_expense_id}", json={"amount": 2000}, headers=headers(tokens["salesperson"]))
        if resp.status_code == 403:
            print(f"  ✅ PASS: Salesperson blocked from editing owner's expense (403)")
        else:
            print(f"  ❌ FAIL: Expected 403, got {resp.status_code}")
    else:
        print(f"  ⚠️  SKIP: Could not create owner expense")
    
    # 1.8: Salesperson tries DELETE any expense → 403
    print("\n[1.8] Salesperson tries DELETE any expense → 403")
    if sp_expense_id:
        resp = requests.delete(f"{API_BASE}/dms/expenses/{sp_expense_id}", headers=headers(tokens["salesperson"]))
        if resp.status_code == 403:
            print(f"  ✅ PASS: Salesperson blocked from deleting (403)")
        else:
            print(f"  ❌ FAIL: Expected 403, got {resp.status_code}")
    else:
        print(f"  ⚠️  SKIP: No expense ID to test")
    
    # 1.9: Owner DELETE /api/dms/expenses/{id} → 200
    print("\n[1.9] Owner DELETE /api/dms/expenses/{id} → 200")
    # Create a new expense to delete
    resp = requests.post(f"{API_BASE}/dms/expenses", json={"category": "Test", "amount": 100, "date": "2026-08-01"}, headers=headers(tokens["owner"]))
    if resp.status_code in [200, 201]:
        delete_expense_id = resp.json().get("id")
        resp = requests.delete(f"{API_BASE}/dms/expenses/{delete_expense_id}", headers=headers(tokens["owner"]))
        if resp.status_code == 200:
            print(f"  ✅ PASS: Owner can delete expense")
        else:
            print(f"  ❌ FAIL: Expected 200, got {resp.status_code}")
    else:
        print(f"  ⚠️  SKIP: Could not create expense to delete")
    
    # 1.10: GET /api/dms/expenses/categories → returns list
    print("\n[1.10] GET /api/dms/expenses/categories → returns list")
    resp = requests.get(f"{API_BASE}/dms/expenses/categories", headers=headers(tokens["owner"]))
    if resp.status_code == 200:
        categories = resp.json().get("data", [])
        if len(categories) > 0:
            print(f"  ✅ PASS: Categories returned (count: {len(categories)})")
        else:
            print(f"  ⚠️  WARNING: No categories found")
    else:
        print(f"  ❌ FAIL: Expected 200, got {resp.status_code}")
    
    # ========================================================================
    # TEST 2: FINANCIAL YEAR CLOSE
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 2: FINANCIAL YEAR CLOSE")
    print("=" * 80)
    
    # 2.1: GET /api/dms/settings → note current fy_lock_date
    print("\n[2.1] GET /api/dms/settings → note current fy_lock_date")
    resp = requests.get(f"{API_BASE}/dms/settings", headers=headers(tokens["owner"]))
    if resp.status_code == 200:
        settings = resp.json()
        current_lock = settings.get("fy_lock_date")
        print(f"  ✅ PASS: Current fy_lock_date: {current_lock}")
    else:
        print(f"  ❌ FAIL: Expected 200, got {resp.status_code}")
        current_lock = None
    
    # 2.2: POST /api/dms/finance/fy-close with {lock_date: "2026-01-31"} → 200
    print("\n[2.2] POST /api/dms/finance/fy-close with lock_date=2026-01-31 → 200")
    resp = requests.post(f"{API_BASE}/dms/finance/fy-close", json={"lock_date": "2026-01-31"}, headers=headers(tokens["owner"]))
    if resp.status_code == 200:
        result = resp.json()
        print(f"  ✅ PASS: FY locked to {result.get('fy_lock_date')}")
    else:
        print(f"  ❌ FAIL: Expected 200, got {resp.status_code} — {resp.text}")
    
    # 2.3: Try again with earlier date (2025-12-31) → 400
    print("\n[2.3] POST /api/dms/finance/fy-close with lock_date=2025-12-31 (earlier) → 400")
    resp = requests.post(f"{API_BASE}/dms/finance/fy-close", json={"lock_date": "2025-12-31"}, headers=headers(tokens["owner"]))
    if resp.status_code == 400:
        print(f"  ✅ PASS: Cannot move lock backwards (400)")
    else:
        print(f"  ❌ FAIL: Expected 400, got {resp.status_code}")
    
    # 2.4: Try again with later date (2026-02-28) → 200
    print("\n[2.4] POST /api/dms/finance/fy-close with lock_date=2026-02-28 (later) → 200")
    resp = requests.post(f"{API_BASE}/dms/finance/fy-close", json={"lock_date": "2026-02-28"}, headers=headers(tokens["owner"]))
    if resp.status_code == 200:
        result = resp.json()
        print(f"  ✅ PASS: FY lock moved forward to {result.get('fy_lock_date')}")
    else:
        print(f"  ❌ FAIL: Expected 200, got {resp.status_code}")
    
    # 2.5: POST as salesperson (not owner) → 403
    print("\n[2.5] POST /api/dms/finance/fy-close as salesperson → 403")
    resp = requests.post(f"{API_BASE}/dms/finance/fy-close", json={"lock_date": "2026-03-31"}, headers=headers(tokens["salesperson"]))
    if resp.status_code == 403:
        print(f"  ✅ PASS: Salesperson blocked (403)")
    else:
        print(f"  ❌ FAIL: Expected 403, got {resp.status_code}")
    
    # 2.6: POST with invalid date format → 400
    print("\n[2.6] POST /api/dms/finance/fy-close with invalid date → 400")
    resp = requests.post(f"{API_BASE}/dms/finance/fy-close", json={"lock_date": "not-a-date"}, headers=headers(tokens["owner"]))
    if resp.status_code == 400:
        print(f"  ✅ PASS: Invalid date rejected (400)")
    else:
        print(f"  ❌ FAIL: Expected 400, got {resp.status_code}")
    
    # 2.7: PUT /api/dms/settings with fy_lock_date → 200 (alternative path)
    print("\n[2.7] PUT /api/dms/settings with fy_lock_date=2026-03-31 → 200")
    resp = requests.put(f"{API_BASE}/dms/settings", json={"fy_lock_date": "2026-03-31"}, headers=headers(tokens["owner"]))
    if resp.status_code == 200:
        result = resp.json()
        print(f"  ✅ PASS: FY lock updated via settings (fy_lock_date: {result.get('fy_lock_date')})")
    else:
        print(f"  ❌ FAIL: Expected 200, got {resp.status_code}")
    
    # 2.8: Enforcement test — POST expense with date before lock → 400
    print("\n[2.8] POST expense with date=2026-01-15 (before lock) → 400")
    resp = requests.post(f"{API_BASE}/dms/expenses", json={"category": "Test", "amount": 100, "date": "2026-01-15"}, headers=headers(tokens["owner"]))
    if resp.status_code == 400:
        print(f"  ✅ PASS: Expense before lock rejected (400)")
    else:
        print(f"  ❌ FAIL: Expected 400, got {resp.status_code}")
    
    # 2.9: POST expense with date after lock → 200
    print("\n[2.9] POST expense with date=2026-05-15 (after lock) → 200")
    resp = requests.post(f"{API_BASE}/dms/expenses", json={"category": "Test", "amount": 100, "date": "2026-05-15"}, headers=headers(tokens["owner"]))
    if resp.status_code in [200, 201]:
        print(f"  ✅ PASS: Expense after lock allowed")
    else:
        print(f"  ❌ FAIL: Expected 200/201, got {resp.status_code}")
    
    # 2.10: POST with empty body → 400
    print("\n[2.10] POST /api/dms/finance/fy-close with empty body → 400")
    resp = requests.post(f"{API_BASE}/dms/finance/fy-close", json={}, headers=headers(tokens["owner"]))
    if resp.status_code == 400:
        print(f"  ✅ PASS: Empty body rejected (400)")
    else:
        print(f"  ❌ FAIL: Expected 400, got {resp.status_code}")
    
    # ========================================================================
    # TEST 3: EDITABLE INVOICE/BILL NUMBERS
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 3: EDITABLE INVOICE/BILL NUMBERS")
    print("=" * 80)
    
    # 3.1: Find an existing e-bill
    print("\n[3.1] Finding an existing e-bill...")
    resp = requests.get(f"{API_BASE}/dms/owner/primary-orders", headers=headers(tokens["owner"]))
    ebill_id = None
    if resp.status_code == 200:
        orders = resp.json().get("data", [])
        for order in orders:
            if order.get("ebill_id"):
                ebill_id = order.get("ebill_id")
                print(f"  ✅ Found e-bill: {ebill_id}")
                break
    
    if not ebill_id:
        print(f"  ⚠️  No e-bill found, creating one...")
        # Place a primary order as distributor1
        resp = requests.get(f"{API_BASE}/dms/distributor/browse", headers=headers(tokens["distributor1"]))
        if resp.status_code == 200:
            products = resp.json().get("data", [])
            if len(products) > 0:
                product = products[0]
                order_data = {
                    "lines": [{"product_id": product["id"], "qty_boxes": 2}]
                }
                resp = requests.post(f"{API_BASE}/dms/primary-orders", json=order_data, headers=headers(tokens["distributor1"]))
                if resp.status_code in [200, 201]:
                    order_id = resp.json().get("id")
                    # Fulfill the order as owner
                    resp = requests.get(f"{API_BASE}/dms/owner/primary-orders/{order_id}", headers=headers(tokens["owner"]))
                    if resp.status_code == 200:
                        order = resp.json()
                        line_id = order["lines"][0]["id"]
                        # Fulfill line
                        resp = requests.post(f"{API_BASE}/dms/owner/primary-orders/{order_id}/fulfill", json={"line_id": line_id, "qty_boxes": 2}, headers=headers(tokens["owner"]))
                        # Mark ready
                        resp = requests.post(f"{API_BASE}/dms/owner/primary-orders/{order_id}/ready", headers=headers(tokens["owner"]))
                        if resp.status_code == 200:
                            ebill_id = resp.json().get("ebill_id")
                            print(f"  ✅ Created e-bill: {ebill_id}")
    
    # 3.2: Owner PUT /api/dms/ebills/{id}/number → 200
    if ebill_id:
        print("\n[3.2] Owner PUT /api/dms/ebills/{id}/number with custom number → 200")
        custom_no = f"EB-CUSTOM-{datetime.now().strftime('%H%M%S')}"
        resp = requests.put(f"{API_BASE}/dms/ebills/{ebill_id}/number", json={"ebill_no": custom_no}, headers=headers(tokens["owner"]))
        if resp.status_code == 200:
            print(f"  ✅ PASS: E-bill number updated to {custom_no}")
            # Verify via print endpoint
            resp = requests.get(f"{API_BASE}/dms/print/ebill/{ebill_id}", headers=headers(tokens["owner"]))
            if resp.status_code == 200:
                ebill = resp.json()
                if ebill.get("ebill_no") == custom_no:
                    print(f"  ✅ PASS: E-bill number verified via print endpoint")
                else:
                    print(f"  ❌ FAIL: E-bill number mismatch (expected {custom_no}, got {ebill.get('ebill_no')})")
        else:
            print(f"  ❌ FAIL: Expected 200, got {resp.status_code} — {resp.text}")
        
        # 3.3: Try same custom number on a second bill → 400 duplicate
        print("\n[3.3] Try same custom number on another e-bill → 400 duplicate")
        # Find another e-bill
        resp = requests.get(f"{API_BASE}/dms/owner/primary-orders", headers=headers(tokens["owner"]))
        if resp.status_code == 200:
            orders = resp.json().get("data", [])
            other_ebill_id = None
            for order in orders:
                if order.get("ebill_id") and order.get("ebill_id") != ebill_id:
                    other_ebill_id = order.get("ebill_id")
                    break
            
            if other_ebill_id:
                resp = requests.put(f"{API_BASE}/dms/ebills/{other_ebill_id}/number", json={"ebill_no": custom_no}, headers=headers(tokens["owner"]))
                if resp.status_code == 400:
                    print(f"  ✅ PASS: Duplicate e-bill number rejected (400)")
                else:
                    print(f"  ❌ FAIL: Expected 400, got {resp.status_code}")
            else:
                print(f"  ⚠️  SKIP: No second e-bill found")
        
        # 3.4: Salesperson tries PUT /api/dms/ebills/{id}/number → 403
        print("\n[3.4] Salesperson PUT /api/dms/ebills/{id}/number → 403")
        resp = requests.put(f"{API_BASE}/dms/ebills/{ebill_id}/number", json={"ebill_no": "EB-HACK-001"}, headers=headers(tokens["salesperson"]))
        if resp.status_code == 403:
            print(f"  ✅ PASS: Salesperson blocked (403)")
        else:
            print(f"  ❌ FAIL: Expected 403, got {resp.status_code}")
    else:
        print(f"  ⚠️  SKIP: No e-bill available for testing")
    
    # 3.5: Retailer bills — same tests
    print("\n[3.5] Finding an existing retailer bill...")
    resp = requests.get(f"{API_BASE}/dms/ledger/secondary", headers=headers(tokens["distributor1"]))
    bill_id = None
    if resp.status_code == 200:
        entries = resp.json().get("entries", [])
        for entry in entries:
            if entry.get("bill_id"):
                bill_id = entry.get("bill_id")
                print(f"  ✅ Found retailer bill: {bill_id}")
                break
    
    if not bill_id:
        print(f"  ⚠️  No retailer bill found, creating one...")
        # Place a secondary order as retailer1
        resp = requests.get(f"{API_BASE}/dms/retailer/browse", headers=headers(tokens["retailer1"]))
        if resp.status_code == 200:
            products = resp.json().get("data", [])
            if len(products) > 0:
                product = products[0]
                order_data = {
                    "lines": [{"product_id": product["id"], "qty_boxes": 1, "qty_pcs": 0}]
                }
                resp = requests.post(f"{API_BASE}/dms/secondary-orders", json=order_data, headers=headers(tokens["retailer1"]))
                if resp.status_code in [200, 201]:
                    order_id = resp.json().get("id")
                    # Dispatch the order as distributor1
                    resp = requests.get(f"{API_BASE}/dms/secondary-orders/{order_id}", headers=headers(tokens["distributor1"]))
                    if resp.status_code == 200:
                        order = resp.json()
                        line_id = order["lines"][0]["id"]
                        # Dispatch line
                        resp = requests.post(f"{API_BASE}/dms/secondary-orders/{order_id}/dispatch", json={"line_id": line_id, "qty_boxes": 1, "qty_pcs": 0}, headers=headers(tokens["distributor1"]))
                        if resp.status_code == 200:
                            bill_id = resp.json().get("bill_id")
                            print(f"  ✅ Created retailer bill: {bill_id}")
    
    if bill_id:
        print("\n[3.6] Owner PUT /api/dms/retailer-bills/{id}/number → 200")
        custom_no = f"RB-CUSTOM-{datetime.now().strftime('%H%M%S')}"
        resp = requests.put(f"{API_BASE}/dms/retailer-bills/{bill_id}/number", json={"bill_no": custom_no}, headers=headers(tokens["owner"]))
        if resp.status_code == 200:
            print(f"  ✅ PASS: Retailer bill number updated to {custom_no}")
        else:
            print(f"  ❌ FAIL: Expected 200, got {resp.status_code} — {resp.text}")
        
        # 3.7: Retailer tries PUT → 403
        print("\n[3.7] Retailer PUT /api/dms/retailer-bills/{id}/number → 403")
        resp = requests.put(f"{API_BASE}/dms/retailer-bills/{bill_id}/number", json={"bill_no": "RB-HACK-001"}, headers=headers(tokens["retailer1"]))
        if resp.status_code == 403:
            print(f"  ✅ PASS: Retailer blocked (403)")
        else:
            print(f"  ❌ FAIL: Expected 403, got {resp.status_code}")
        
        # 3.8: Distributor (owner of bill) → 200
        print("\n[3.8] Distributor (owner of bill) PUT /api/dms/retailer-bills/{id}/number → 200")
        custom_no2 = f"RB-DIST-{datetime.now().strftime('%H%M%S')}"
        resp = requests.put(f"{API_BASE}/dms/retailer-bills/{bill_id}/number", json={"bill_no": custom_no2}, headers=headers(tokens["distributor1"]))
        if resp.status_code == 200:
            print(f"  ✅ PASS: Distributor can edit own bill number")
        else:
            print(f"  ❌ FAIL: Expected 200, got {resp.status_code}")
        
        # 3.9: Different distributor → 403
        print("\n[3.9] Different distributor PUT /api/dms/retailer-bills/{id}/number → 403")
        resp = requests.put(f"{API_BASE}/dms/retailer-bills/{bill_id}/number", json={"bill_no": "RB-HACK-002"}, headers=headers(tokens["distributor2"]))
        if resp.status_code == 403:
            print(f"  ✅ PASS: Different distributor blocked (403)")
        else:
            print(f"  ❌ FAIL: Expected 403, got {resp.status_code}")
    else:
        print(f"  ⚠️  SKIP: No retailer bill available for testing")
    
    # ========================================================================
    # TEST 4: PRINT ENDPOINTS INCLUDE T&C / MESSAGE
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 4: PRINT ENDPOINTS INCLUDE T&C / MESSAGE")
    print("=" * 80)
    
    # 4.1: Owner PUT /api/dms/settings with invoice_terms and invoice_message → 200
    print("\n[4.1] Owner PUT /api/dms/settings with invoice_terms and invoice_message → 200")
    settings_data = {
        "invoice_terms": "Goods once sold will not be taken back.",
        "invoice_message": "Thank you for your business!"
    }
    resp = requests.put(f"{API_BASE}/dms/settings", json=settings_data, headers=headers(tokens["owner"]))
    if resp.status_code == 200:
        print(f"  ✅ PASS: Settings updated with invoice T&C")
    else:
        print(f"  ❌ FAIL: Expected 200, got {resp.status_code}")
    
    # 4.2: GET /api/dms/print/ebill/{id} → includes invoice_terms, invoice_message, company_name
    if ebill_id:
        print("\n[4.2] GET /api/dms/print/ebill/{id} → includes invoice_terms, invoice_message, company_name")
        resp = requests.get(f"{API_BASE}/dms/print/ebill/{ebill_id}", headers=headers(tokens["owner"]))
        if resp.status_code == 200:
            ebill = resp.json()
            has_terms = "invoice_terms" in ebill
            has_message = "invoice_message" in ebill
            has_company = "company_name" in ebill
            if has_terms and has_message and has_company:
                print(f"  ✅ PASS: E-bill includes invoice_terms, invoice_message, company_name")
                print(f"    - invoice_terms: {ebill.get('invoice_terms')}")
                print(f"    - invoice_message: {ebill.get('invoice_message')}")
                print(f"    - company_name: {ebill.get('company_name')}")
            else:
                print(f"  ❌ FAIL: Missing fields (terms: {has_terms}, message: {has_message}, company: {has_company})")
        else:
            print(f"  ❌ FAIL: Expected 200, got {resp.status_code}")
    else:
        print(f"  ⚠️  SKIP: No e-bill available")
    
    # 4.3: GET /api/dms/print/retailer-bill/{id} → same
    if bill_id:
        print("\n[4.3] GET /api/dms/print/retailer-bill/{id} → includes invoice_terms, invoice_message, company_name")
        resp = requests.get(f"{API_BASE}/dms/print/retailer-bill/{bill_id}", headers=headers(tokens["distributor1"]))
        if resp.status_code == 200:
            bill = resp.json()
            has_terms = "invoice_terms" in bill
            has_message = "invoice_message" in bill
            has_company = "company_name" in bill
            if has_terms and has_message and has_company:
                print(f"  ✅ PASS: Retailer bill includes invoice_terms, invoice_message, company_name")
            else:
                print(f"  ❌ FAIL: Missing fields (terms: {has_terms}, message: {has_message}, company: {has_company})")
        else:
            print(f"  ❌ FAIL: Expected 200, got {resp.status_code}")
    else:
        print(f"  ⚠️  SKIP: No retailer bill available")
    
    # ========================================================================
    # TEST 5: REGRESSION
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 5: REGRESSION")
    print("=" * 80)
    
    # 5.1: GET /api/dms/settings still returns gst_pct + company_name
    print("\n[5.1] GET /api/dms/settings → still returns gst_pct + company_name")
    resp = requests.get(f"{API_BASE}/dms/settings", headers=headers(tokens["owner"]))
    if resp.status_code == 200:
        settings = resp.json()
        has_gst = "gst_pct" in settings
        has_company = "company_name" in settings
        if has_gst and has_company:
            print(f"  ✅ PASS: Settings include gst_pct and company_name")
        else:
            print(f"  ❌ FAIL: Missing fields (gst_pct: {has_gst}, company_name: {has_company})")
    else:
        print(f"  ❌ FAIL: Expected 200, got {resp.status_code}")
    
    # 5.2: POST /api/dms/secondary-orders as SP → 200
    print("\n[5.2] POST /api/dms/secondary-orders as salesperson → 200")
    resp = requests.get(f"{API_BASE}/dms/retailer/browse", headers=headers(tokens["retailer1"]))
    if resp.status_code == 200:
        products = resp.json().get("data", [])
        if len(products) > 0:
            product = products[0]
            order_data = {
                "lines": [{"product_id": product["id"], "qty_boxes": 1, "qty_pcs": 0}]
            }
            resp = requests.post(f"{API_BASE}/dms/secondary-orders", json=order_data, headers=headers(tokens["salesperson"]))
            if resp.status_code in [200, 201]:
                print(f"  ✅ PASS: Salesperson can place secondary order")
            else:
                print(f"  ❌ FAIL: Expected 200/201, got {resp.status_code}")
    
    # 5.3: GET /api/dms/secondary-orders as SP → returns own orders
    print("\n[5.3] GET /api/dms/secondary-orders as salesperson → returns own orders")
    resp = requests.get(f"{API_BASE}/dms/secondary-orders", headers=headers(tokens["salesperson"]))
    if resp.status_code == 200:
        print(f"  ✅ PASS: Salesperson can view secondary orders")
    else:
        print(f"  ❌ FAIL: Expected 200, got {resp.status_code}")
    
    # 5.4: GET /api/dms/dashboard/owner → returns valid data
    print("\n[5.4] GET /api/dms/dashboard/owner → returns valid data")
    resp = requests.get(f"{API_BASE}/dms/dashboard/owner", headers=headers(tokens["owner"]))
    if resp.status_code == 200:
        print(f"  ✅ PASS: Owner dashboard working")
    else:
        print(f"  ❌ FAIL: Expected 200, got {resp.status_code}")
    
    # 5.5: GET /api/dms/dashboard/team-leader → returns valid data
    print("\n[5.5] GET /api/dms/dashboard/team-leader → returns valid data")
    # Login team leader
    tl_token = login("teamleader@gooil.com")
    resp = requests.get(f"{API_BASE}/dms/dashboard/team-leader", headers=headers(tl_token))
    if resp.status_code == 200:
        print(f"  ✅ PASS: Team leader dashboard working")
    else:
        print(f"  ❌ FAIL: Expected 200, got {resp.status_code}")
    
    # 5.6: GET /api/dms/dashboard/salesperson → returns valid data
    print("\n[5.6] GET /api/dms/dashboard/salesperson → returns valid data")
    resp = requests.get(f"{API_BASE}/dms/dashboard/salesperson", headers=headers(tokens["salesperson"]))
    if resp.status_code == 200:
        print(f"  ✅ PASS: Salesperson dashboard working")
    else:
        print(f"  ❌ FAIL: Expected 200, got {resp.status_code}")
    
    print("\n" + "=" * 80)
    print("PHASE 2A BACKEND TESTING COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
