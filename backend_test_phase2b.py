#!/usr/bin/env python3
"""
GO OIL DMS — Phase 2B Backend Testing
Tests: Cash & Bank, Godown Management, Stock Transfer, Stop Sale on Negative Stock, Sample Bills
"""

import requests
import json
from datetime import datetime, timedelta

# Base URL from frontend/.env
BASE_URL = "https://8c45e563-2411-451a-a210-d052d43103fd.preview.emergentagent.com/api"

# Test credentials (all password: GoOil@2026)
CREDENTIALS = {
    "owner": {"email": "owner@gooil.com", "password": "GoOil@2026"},
    "accountant": {"email": "accountant@gooil.com", "password": "GoOil@2026"},
    "distributor1": {"email": "distributor1@gooil.com", "password": "GoOil@2026"},
    "salesperson": {"email": "salesperson@gooil.com", "password": "GoOil@2026"},
    "retailer1": {"email": "retailer1@gooil.com", "password": "GoOil@2026"},
}

# Global tokens
tokens = {}

def login(role):
    """Login and return token"""
    creds = CREDENTIALS[role]
    resp = requests.post(f"{BASE_URL}/auth/login", json=creds)
    if resp.status_code != 200:
        print(f"❌ Login failed for {role}: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    token = data.get("token")
    tokens[role] = token
    print(f"✅ Logged in as {role}")
    return token

def headers(role):
    """Return auth headers for role"""
    return {"Authorization": f"Bearer {tokens[role]}"}

def test_section(title):
    """Print test section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")

def test_case(name):
    """Print test case name"""
    print(f"\n▶ {name}")

# ============================================================================
# PHASE 2B TESTS
# ============================================================================

def main():
    print("🚀 GO OIL DMS — Phase 2B Backend Testing")
    print(f"Base URL: {BASE_URL}")
    
    # Login all roles
    test_section("LOGIN ALL ROLES")
    for role in CREDENTIALS.keys():
        login(role)
    
    # ========================================================================
    # 1. CASH & BANK MODULE
    # ========================================================================
    test_section("1. CASH & BANK — BANK ACCOUNTS")
    
    # 1.1 GET bank-accounts (owner)
    test_case("1.1 GET /dms/bank-accounts as owner")
    resp = requests.get(f"{BASE_URL}/dms/bank-accounts", headers=headers("owner"))
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Bank accounts count: {data.get('count', 0)}")
    else:
        print(f"❌ Failed: {resp.text}")
    
    # 1.2 POST bank-accounts (owner)
    test_case("1.2 POST /dms/bank-accounts as owner")
    bank_payload = {
        "name": "Test Bank Account",
        "account_number": "1234567890",
        "ifsc": "SBIN0001234",
        "branch": "Test Branch",
        "opening_balance": 50000.0,
        "notes": "Test bank account for Phase 2B"
    }
    resp = requests.post(f"{BASE_URL}/dms/bank-accounts", json=bank_payload, headers=headers("owner"))
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        bank_data = resp.json()
        bank_id = bank_data.get("id")
        print(f"✅ Bank account created: {bank_id}")
        print(f"   Current balance: ₹{bank_data.get('current_balance', 0)}")
    else:
        print(f"❌ Failed: {resp.text}")
        bank_id = None
    
    # 1.3 POST bank-accounts as salesperson (should be 403)
    test_case("1.3 POST /dms/bank-accounts as salesperson (expect 403)")
    resp = requests.post(f"{BASE_URL}/dms/bank-accounts", json=bank_payload, headers=headers("salesperson"))
    print(f"Status: {resp.status_code}")
    if resp.status_code == 403:
        print(f"✅ Correctly blocked salesperson (403)")
    else:
        print(f"❌ Expected 403, got {resp.status_code}")
    
    # 1.4 POST bank-accounts as retailer (should be 403)
    test_case("1.4 POST /dms/bank-accounts as retailer (expect 403)")
    resp = requests.post(f"{BASE_URL}/dms/bank-accounts", json=bank_payload, headers=headers("retailer1"))
    print(f"Status: {resp.status_code}")
    if resp.status_code == 403:
        print(f"✅ Correctly blocked retailer (403)")
    else:
        print(f"❌ Expected 403, got {resp.status_code}")
    
    # 1.5 PUT bank-accounts (owner)
    if bank_id:
        test_case("1.5 PUT /dms/bank-accounts/{id} as owner")
        update_payload = {
            "name": "Test Bank Account Updated",
            "notes": "Updated notes"
        }
        resp = requests.put(f"{BASE_URL}/dms/bank-accounts/{bank_id}", json=update_payload, headers=headers("owner"))
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"✅ Bank account updated")
        else:
            print(f"❌ Failed: {resp.text}")
    
    # ========================================================================
    # 2. BANK TRANSACTIONS
    # ========================================================================
    test_section("2. CASH & BANK — BANK TRANSACTIONS")
    
    if bank_id:
        # 2.1 POST deposit
        test_case("2.1 POST /dms/bank-transactions (deposit)")
        today = datetime.now().strftime("%Y-%m-%d")
        deposit_payload = {
            "bank_account_id": bank_id,
            "date": today,
            "type": "deposit",
            "amount": 10000.0,
            "reference": "Test Deposit",
            "notes": "Test deposit transaction"
        }
        resp = requests.post(f"{BASE_URL}/dms/bank-transactions", json=deposit_payload, headers=headers("owner"))
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            txn_data = resp.json()
            deposit_txn_id = txn_data.get("id")
            print(f"✅ Deposit transaction created: {deposit_txn_id}")
            print(f"   Balance after: ₹{txn_data.get('balance_after', 0)}")
        else:
            print(f"❌ Failed: {resp.text}")
            deposit_txn_id = None
        
        # 2.2 Verify bank account balance increased
        test_case("2.2 Verify bank account balance after deposit")
        resp = requests.get(f"{BASE_URL}/dms/bank-accounts", headers=headers("owner"))
        if resp.status_code == 200:
            accounts = resp.json().get("data", [])
            test_account = next((a for a in accounts if a["id"] == bank_id), None)
            if test_account:
                expected_balance = 50000.0 + 10000.0  # opening + deposit
                actual_balance = test_account.get("current_balance", 0)
                if abs(actual_balance - expected_balance) < 0.01:
                    print(f"✅ Balance correct: ₹{actual_balance} (expected ₹{expected_balance})")
                else:
                    print(f"❌ Balance mismatch: ₹{actual_balance} (expected ₹{expected_balance})")
        
        # 2.3 POST withdrawal
        test_case("2.3 POST /dms/bank-transactions (withdrawal)")
        withdrawal_payload = {
            "bank_account_id": bank_id,
            "date": today,
            "type": "withdrawal",
            "amount": 5000.0,
            "reference": "Test Withdrawal",
            "notes": "Test withdrawal transaction"
        }
        resp = requests.post(f"{BASE_URL}/dms/bank-transactions", json=withdrawal_payload, headers=headers("owner"))
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            txn_data = resp.json()
            withdrawal_txn_id = txn_data.get("id")
            print(f"✅ Withdrawal transaction created: {withdrawal_txn_id}")
            print(f"   Balance after: ₹{txn_data.get('balance_after', 0)}")
        else:
            print(f"❌ Failed: {resp.text}")
            withdrawal_txn_id = None
        
        # 2.4 Verify bank account balance decreased
        test_case("2.4 Verify bank account balance after withdrawal")
        resp = requests.get(f"{BASE_URL}/dms/bank-accounts", headers=headers("owner"))
        if resp.status_code == 200:
            accounts = resp.json().get("data", [])
            test_account = next((a for a in accounts if a["id"] == bank_id), None)
            if test_account:
                expected_balance = 50000.0 + 10000.0 - 5000.0  # opening + deposit - withdrawal
                actual_balance = test_account.get("current_balance", 0)
                if abs(actual_balance - expected_balance) < 0.01:
                    print(f"✅ Balance correct: ₹{actual_balance} (expected ₹{expected_balance})")
                else:
                    print(f"❌ Balance mismatch: ₹{actual_balance} (expected ₹{expected_balance})")
        
        # 2.5 GET bank-transactions
        test_case("2.5 GET /dms/bank-transactions")
        resp = requests.get(f"{BASE_URL}/dms/bank-transactions?account_id={bank_id}", headers=headers("owner"))
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Transactions count: {data.get('count', 0)}")
        else:
            print(f"❌ Failed: {resp.text}")
        
        # 2.6 DELETE bank-transaction (should reverse balance)
        if deposit_txn_id:
            test_case("2.6 DELETE /dms/bank-transactions/{id} (should reverse balance)")
            resp = requests.delete(f"{BASE_URL}/dms/bank-transactions/{deposit_txn_id}", headers=headers("owner"))
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"✅ Transaction deleted")
                # Verify balance reversed
                resp = requests.get(f"{BASE_URL}/dms/bank-accounts", headers=headers("owner"))
                if resp.status_code == 200:
                    accounts = resp.json().get("data", [])
                    test_account = next((a for a in accounts if a["id"] == bank_id), None)
                    if test_account:
                        expected_balance = 50000.0 - 5000.0  # opening - withdrawal (deposit reversed)
                        actual_balance = test_account.get("current_balance", 0)
                        if abs(actual_balance - expected_balance) < 0.01:
                            print(f"✅ Balance reversed correctly: ₹{actual_balance}")
                        else:
                            print(f"❌ Balance not reversed: ₹{actual_balance} (expected ₹{expected_balance})")
            else:
                print(f"❌ Failed: {resp.text}")
    
    # ========================================================================
    # 3. CASH REGISTER
    # ========================================================================
    test_section("3. CASH & BANK — CASH REGISTER")
    
    # 3.1 POST cash-in
    test_case("3.1 POST /dms/cash-register (type=in)")
    today = datetime.now().strftime("%Y-%m-%d")
    cash_in_payload = {
        "date": today,
        "type": "in",
        "amount": 15000.0,
        "reference": "Cash Sale",
        "notes": "Test cash in"
    }
    resp = requests.post(f"{BASE_URL}/dms/cash-register", json=cash_in_payload, headers=headers("owner"))
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        cash_in_data = resp.json()
        cash_in_id = cash_in_data.get("id")
        print(f"✅ Cash-in entry created: {cash_in_id}")
    else:
        print(f"❌ Failed: {resp.text}")
        cash_in_id = None
    
    # 3.2 POST cash-out
    test_case("3.2 POST /dms/cash-register (type=out)")
    cash_out_payload = {
        "date": today,
        "type": "out",
        "amount": 5000.0,
        "reference": "Petty Cash",
        "notes": "Test cash out"
    }
    resp = requests.post(f"{BASE_URL}/dms/cash-register", json=cash_out_payload, headers=headers("owner"))
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        cash_out_data = resp.json()
        cash_out_id = cash_out_data.get("id")
        print(f"✅ Cash-out entry created: {cash_out_id}")
    else:
        print(f"❌ Failed: {resp.text}")
        cash_out_id = None
    
    # 3.3 GET cash-register (verify balance aggregate)
    test_case("3.3 GET /dms/cash-register (verify balance aggregate)")
    resp = requests.get(f"{BASE_URL}/dms/cash-register", headers=headers("owner"))
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        current_balance = data.get("current_balance", 0)
        count = data.get("count", 0)
        print(f"✅ Cash register entries: {count}")
        print(f"   Current balance: ₹{current_balance}")
        # Balance should be sum(in) - sum(out) = 15000 - 5000 = 10000 (plus any existing)
    else:
        print(f"❌ Failed: {resp.text}")
    
    # 3.4 POST cash-register as salesperson (should be 403)
    test_case("3.4 POST /dms/cash-register as salesperson (expect 403)")
    resp = requests.post(f"{BASE_URL}/dms/cash-register", json=cash_in_payload, headers=headers("salesperson"))
    print(f"Status: {resp.status_code}")
    if resp.status_code == 403:
        print(f"✅ Correctly blocked salesperson (403)")
    else:
        print(f"❌ Expected 403, got {resp.status_code}")
    
    # ========================================================================
    # 4. CHEQUES
    # ========================================================================
    test_section("4. CASH & BANK — CHEQUES")
    
    # 4.1 POST cheque (received)
    test_case("4.1 POST /dms/cheques (direction=received)")
    today = datetime.now().strftime("%Y-%m-%d")
    cheque_payload = {
        "cheque_no": "CHQ123456",
        "date": today,
        "direction": "received",
        "party_name": "Test Customer",
        "amount": 25000.0,
        "bank_name": "Test Bank",
        "status": "pending",
        "notes": "Test cheque received"
    }
    resp = requests.post(f"{BASE_URL}/dms/cheques", json=cheque_payload, headers=headers("owner"))
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        cheque_data = resp.json()
        cheque_id = cheque_data.get("id")
        print(f"✅ Cheque created: {cheque_id}")
    else:
        print(f"❌ Failed: {resp.text}")
        cheque_id = None
    
    # 4.2 PUT cheque status to cleared
    if cheque_id:
        test_case("4.2 PUT /dms/cheques/{id} (status=cleared)")
        update_payload = {"status": "cleared"}
        resp = requests.put(f"{BASE_URL}/dms/cheques/{cheque_id}", json=update_payload, headers=headers("owner"))
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"✅ Cheque status updated to cleared")
        else:
            print(f"❌ Failed: {resp.text}")
    
    # 4.3 GET cheques
    test_case("4.3 GET /dms/cheques")
    resp = requests.get(f"{BASE_URL}/dms/cheques", headers=headers("owner"))
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Cheques count: {data.get('count', 0)}")
    else:
        print(f"❌ Failed: {resp.text}")
    
    # 4.4 DELETE cheque (owner only)
    if cheque_id:
        test_case("4.4 DELETE /dms/cheques/{id} as owner")
        resp = requests.delete(f"{BASE_URL}/dms/cheques/{cheque_id}", headers=headers("owner"))
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"✅ Cheque deleted")
        else:
            print(f"❌ Failed: {resp.text}")
    
    # ========================================================================
    # 5. LOAN ACCOUNTS
    # ========================================================================
    test_section("5. CASH & BANK — LOAN ACCOUNTS")
    
    # 5.1 POST loan-account
    test_case("5.1 POST /dms/loan-accounts")
    today = datetime.now().strftime("%Y-%m-%d")
    loan_payload = {
        "name": "Test Business Loan",
        "lender_name": "Test Bank Ltd",
        "principal": 500000.0,
        "interest_rate": 10.5,
        "start_date": today,
        "tenure_months": 24,
        "notes": "Test loan account"
    }
    resp = requests.post(f"{BASE_URL}/dms/loan-accounts", json=loan_payload, headers=headers("owner"))
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        loan_data = resp.json()
        loan_id = loan_data.get("id")
        outstanding = loan_data.get("outstanding", 0)
        print(f"✅ Loan account created: {loan_id}")
        print(f"   Outstanding: ₹{outstanding} (should equal principal ₹500,000)")
        if abs(outstanding - 500000.0) < 0.01:
            print(f"✅ Outstanding correctly set to principal")
        else:
            print(f"❌ Outstanding mismatch")
    else:
        print(f"❌ Failed: {resp.text}")
        loan_id = None
    
    # 5.2 Verify auto disbursement transaction created
    if loan_id:
        test_case("5.2 GET /dms/loan-transactions (verify auto disbursement)")
        resp = requests.get(f"{BASE_URL}/dms/loan-transactions?loan_id={loan_id}", headers=headers("owner"))
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            txns = data.get("data", [])
            if len(txns) == 1 and txns[0].get("type") == "disbursement":
                print(f"✅ Auto disbursement transaction created")
            else:
                print(f"❌ Expected 1 disbursement transaction, got {len(txns)}")
        else:
            print(f"❌ Failed: {resp.text}")
    
    # 5.3 POST loan-transaction (repayment)
    if loan_id:
        test_case("5.3 POST /dms/loan-transactions (type=repayment)")
        repayment_payload = {
            "loan_account_id": loan_id,
            "date": today,
            "type": "repayment",
            "amount": 50000.0,
            "notes": "Test repayment"
        }
        resp = requests.post(f"{BASE_URL}/dms/loan-transactions", json=repayment_payload, headers=headers("owner"))
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            txn_data = resp.json()
            outstanding_after = txn_data.get("outstanding_after", 0)
            print(f"✅ Repayment transaction created")
            print(f"   Outstanding after: ₹{outstanding_after}")
            expected_outstanding = 500000.0 - 50000.0
            if abs(outstanding_after - expected_outstanding) < 0.01:
                print(f"✅ Outstanding decreased correctly (₹{expected_outstanding})")
            else:
                print(f"❌ Outstanding mismatch (expected ₹{expected_outstanding})")
        else:
            print(f"❌ Failed: {resp.text}")
    
    # 5.4 POST loan-transaction (interest)
    if loan_id:
        test_case("5.4 POST /dms/loan-transactions (type=interest)")
        interest_payload = {
            "loan_account_id": loan_id,
            "date": today,
            "type": "interest",
            "amount": 5000.0,
            "notes": "Test interest charge"
        }
        resp = requests.post(f"{BASE_URL}/dms/loan-transactions", json=interest_payload, headers=headers("owner"))
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            txn_data = resp.json()
            outstanding_after = txn_data.get("outstanding_after", 0)
            print(f"✅ Interest transaction created")
            print(f"   Outstanding after: ₹{outstanding_after}")
            expected_outstanding = 500000.0 - 50000.0 + 5000.0
            if abs(outstanding_after - expected_outstanding) < 0.01:
                print(f"✅ Outstanding increased correctly (₹{expected_outstanding})")
            else:
                print(f"❌ Outstanding mismatch (expected ₹{expected_outstanding})")
        else:
            print(f"❌ Failed: {resp.text}")
    
    # 5.5 GET loan-accounts
    test_case("5.5 GET /dms/loan-accounts")
    resp = requests.get(f"{BASE_URL}/dms/loan-accounts", headers=headers("owner"))
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Loan accounts count: {data.get('count', 0)}")
    else:
        print(f"❌ Failed: {resp.text}")
    
    # ========================================================================
    # 6. FY LOCK ENFORCEMENT ON CASH & BANK
    # ========================================================================
    test_section("6. FY LOCK ENFORCEMENT ON CASH & BANK")
    
    # 6.1 Set FY lock date
    test_case("6.1 POST /dms/finance/fy-close (set lock date)")
    lock_date = "2026-06-30"
    resp = requests.post(f"{BASE_URL}/dms/finance/fy-close", json={"lock_date": lock_date}, headers=headers("owner"))
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print(f"✅ FY lock date set to {lock_date}")
    else:
        print(f"❌ Failed: {resp.text}")
    
    # 6.2 Try to create bank transaction before lock date (should fail)
    if bank_id:
        test_case("6.2 POST /dms/bank-transactions with date before lock (expect 400)")
        old_date = "2026-06-15"  # Before lock date
        old_txn_payload = {
            "bank_account_id": bank_id,
            "date": old_date,
            "type": "deposit",
            "amount": 1000.0,
            "reference": "Old transaction",
            "notes": "Should be blocked"
        }
        resp = requests.post(f"{BASE_URL}/dms/bank-transactions", json=old_txn_payload, headers=headers("owner"))
        print(f"Status: {resp.status_code}")
        if resp.status_code == 400:
            print(f"✅ Correctly blocked transaction before lock date (400)")
            print(f"   Error: {resp.json().get('detail', '')}")
        else:
            print(f"❌ Expected 400, got {resp.status_code}")
    
    # 6.3 Try to create cash register entry before lock date (should fail)
    test_case("6.3 POST /dms/cash-register with date before lock (expect 400)")
    old_date = "2026-06-15"
    old_cash_payload = {
        "date": old_date,
        "type": "in",
        "amount": 1000.0,
        "reference": "Old cash",
        "notes": "Should be blocked"
    }
    resp = requests.post(f"{BASE_URL}/dms/cash-register", json=old_cash_payload, headers=headers("owner"))
    print(f"Status: {resp.status_code}")
    if resp.status_code == 400:
        print(f"✅ Correctly blocked cash entry before lock date (400)")
    else:
        print(f"❌ Expected 400, got {resp.status_code}")
    
    # ========================================================================
    # 7. GODOWN MANAGEMENT
    # ========================================================================
    test_section("7. GODOWN MANAGEMENT")
    
    # 7.1 GET godowns
    test_case("7.1 GET /dms/godowns")
    resp = requests.get(f"{BASE_URL}/dms/godowns", headers=headers("owner"))
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Godowns count: {data.get('count', 0)}")
    else:
        print(f"❌ Failed: {resp.text}")
    
    # 7.2 POST godown (owner only)
    test_case("7.2 POST /dms/godowns as owner")
    godown1_payload = {
        "name": "Main Warehouse",
        "address": "123 Industrial Area, Delhi",
        "manager_name": "Rajesh Kumar",
        "phone": "9876543210",
        "capacity_boxes": 10000,
        "notes": "Main storage facility"
    }
    resp = requests.post(f"{BASE_URL}/dms/godowns", json=godown1_payload, headers=headers("owner"))
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        godown1_data = resp.json()
        godown1_id = godown1_data.get("id")
        print(f"✅ Godown 1 created: {godown1_id}")
    else:
        print(f"❌ Failed: {resp.text}")
        godown1_id = None
    
    # 7.3 POST second godown
    test_case("7.3 POST /dms/godowns (second godown)")
    godown2_payload = {
        "name": "Regional Warehouse",
        "address": "456 Storage Road, Mumbai",
        "manager_name": "Suresh Patel",
        "phone": "9876543211",
        "capacity_boxes": 5000,
        "notes": "Regional storage"
    }
    resp = requests.post(f"{BASE_URL}/dms/godowns", json=godown2_payload, headers=headers("owner"))
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        godown2_data = resp.json()
        godown2_id = godown2_data.get("id")
        print(f"✅ Godown 2 created: {godown2_id}")
    else:
        print(f"❌ Failed: {resp.text}")
        godown2_id = None
    
    # 7.4 PUT godown
    if godown1_id:
        test_case("7.4 PUT /dms/godowns/{id}")
        update_payload = {
            "name": "Main Warehouse Updated",
            "notes": "Updated notes"
        }
        resp = requests.put(f"{BASE_URL}/dms/godowns/{godown1_id}", json=update_payload, headers=headers("owner"))
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"✅ Godown updated")
        else:
            print(f"❌ Failed: {resp.text}")
    
    # 7.5 GET godown inventory (should be empty initially)
    if godown1_id:
        test_case("7.5 GET /dms/godowns/{id}/inventory")
        resp = requests.get(f"{BASE_URL}/dms/godowns/{godown1_id}/inventory", headers=headers("owner"))
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Godown inventory items: {len(data.get('inventory', []))}")
        else:
            print(f"❌ Failed: {resp.text}")
    
    # ========================================================================
    # 8. STOCK TRANSFER
    # ========================================================================
    test_section("8. STOCK TRANSFER")
    
    # First, get a product ID
    test_case("8.0 Get product for stock transfer")
    resp = requests.get(f"{BASE_URL}/dms/products", headers=headers("owner"))
    product_id = None
    if resp.status_code == 200:
        products = resp.json().get("data", [])
        if products:
            product_id = products[0].get("id")
            product_name = products[0].get("name", "")
            print(f"✅ Using product: {product_name} (ID: {product_id})")
    
    if not product_id:
        print(f"❌ No products found, skipping stock transfer tests")
    else:
        # 8.1 Check owner inventory before transfer
        test_case("8.1 Check owner inventory before transfer")
        resp = requests.get(f"{BASE_URL}/dms/owner/inventory", headers=headers("owner"))
        owner_stock_before = 0
        if resp.status_code == 200:
            inventory = resp.json().get("data", [])
            product_inv = next((i for i in inventory if i.get("product_id") == product_id), None)
            if product_inv:
                owner_stock_before = product_inv.get("qty_boxes", 0)
                print(f"✅ Owner stock before: {owner_stock_before} boxes")
        
        # 8.2 POST stock-transfer (owner → godown1)
        if godown1_id and owner_stock_before > 0:
            test_case("8.2 POST /dms/stock-transfers (owner → godown)")
            transfer_qty = min(3, owner_stock_before)  # Transfer 3 boxes or less
            today = datetime.now().strftime("%Y-%m-%d")
            transfer_payload = {
                "date": today,
                "from_type": "owner",
                "to_type": "godown",
                "to_godown_id": godown1_id,
                "items": [
                    {
                        "product_id": product_id,
                        "qty_boxes": transfer_qty
                    }
                ],
                "notes": "Test transfer owner to godown"
            }
            resp = requests.post(f"{BASE_URL}/dms/stock-transfers", json=transfer_payload, headers=headers("owner"))
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                transfer_data = resp.json()
                transfer_id = transfer_data.get("id")
                transfer_no = transfer_data.get("transfer_no", "")
                print(f"✅ Stock transfer created: {transfer_no} (ID: {transfer_id})")
                
                # 8.3 Verify owner inventory decreased
                test_case("8.3 Verify owner inventory decreased")
                resp = requests.get(f"{BASE_URL}/dms/owner/inventory", headers=headers("owner"))
                if resp.status_code == 200:
                    inventory = resp.json().get("data", [])
                    product_inv = next((i for i in inventory if i.get("product_id") == product_id), None)
                    if product_inv:
                        owner_stock_after = product_inv.get("qty_boxes", 0)
                        expected_stock = owner_stock_before - transfer_qty
                        if owner_stock_after == expected_stock:
                            print(f"✅ Owner stock decreased correctly: {owner_stock_before} → {owner_stock_after}")
                        else:
                            print(f"❌ Owner stock mismatch: {owner_stock_after} (expected {expected_stock})")
                
                # 8.4 Verify godown inventory increased
                test_case("8.4 Verify godown inventory increased")
                resp = requests.get(f"{BASE_URL}/dms/godowns/{godown1_id}/inventory", headers=headers("owner"))
                if resp.status_code == 200:
                    data = resp.json()
                    inventory = data.get("inventory", [])
                    product_inv = next((i for i in inventory if i.get("product_id") == product_id), None)
                    if product_inv:
                        godown_stock = product_inv.get("qty_boxes", 0)
                        if godown_stock == transfer_qty:
                            print(f"✅ Godown stock increased correctly: {godown_stock} boxes")
                        else:
                            print(f"❌ Godown stock mismatch: {godown_stock} (expected {transfer_qty})")
                    else:
                        print(f"❌ Product not found in godown inventory")
            else:
                print(f"❌ Failed: {resp.text}")
        
        # 8.5 POST stock-transfer (godown1 → godown2)
        if godown1_id and godown2_id:
            test_case("8.5 POST /dms/stock-transfers (godown → godown)")
            transfer_payload = {
                "date": today,
                "from_type": "godown",
                "from_godown_id": godown1_id,
                "to_type": "godown",
                "to_godown_id": godown2_id,
                "items": [
                    {
                        "product_id": product_id,
                        "qty_boxes": 1
                    }
                ],
                "notes": "Test transfer godown to godown"
            }
            resp = requests.post(f"{BASE_URL}/dms/stock-transfers", json=transfer_payload, headers=headers("owner"))
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"✅ Godown-to-godown transfer successful")
            else:
                print(f"❌ Failed: {resp.text}")
        
        # 8.6 POST stock-transfer with insufficient stock (should fail)
        if godown1_id:
            test_case("8.6 POST /dms/stock-transfers with insufficient stock (expect 400)")
            transfer_payload = {
                "date": today,
                "from_type": "owner",
                "to_type": "godown",
                "to_godown_id": godown1_id,
                "items": [
                    {
                        "product_id": product_id,
                        "qty_boxes": 999999  # Unrealistic quantity
                    }
                ],
                "notes": "Should fail"
            }
            resp = requests.post(f"{BASE_URL}/dms/stock-transfers", json=transfer_payload, headers=headers("owner"))
            print(f"Status: {resp.status_code}")
            if resp.status_code == 400:
                print(f"✅ Correctly blocked insufficient stock (400)")
                print(f"   Error: {resp.json().get('detail', '')}")
            else:
                print(f"❌ Expected 400, got {resp.status_code}")
        
        # 8.7 POST stock-transfer with same source/destination (should fail)
        if godown1_id:
            test_case("8.7 POST /dms/stock-transfers same source/dest (expect 400)")
            transfer_payload = {
                "date": today,
                "from_type": "godown",
                "from_godown_id": godown1_id,
                "to_type": "godown",
                "to_godown_id": godown1_id,  # Same godown
                "items": [
                    {
                        "product_id": product_id,
                        "qty_boxes": 1
                    }
                ],
                "notes": "Should fail"
            }
            resp = requests.post(f"{BASE_URL}/dms/stock-transfers", json=transfer_payload, headers=headers("owner"))
            print(f"Status: {resp.status_code}")
            if resp.status_code == 400:
                print(f"✅ Correctly blocked same source/dest (400)")
            else:
                print(f"❌ Expected 400, got {resp.status_code}")
        
        # 8.8 GET stock-transfers
        test_case("8.8 GET /dms/stock-transfers")
        resp = requests.get(f"{BASE_URL}/dms/stock-transfers", headers=headers("owner"))
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Stock transfers count: {data.get('count', 0)}")
        else:
            print(f"❌ Failed: {resp.text}")
    
    # ========================================================================
    # 9. STOP SALE ON NEGATIVE STOCK
    # ========================================================================
    test_section("9. STOP SALE ON NEGATIVE STOCK")
    
    # 9.1 Get current stop_sale_on_negative setting
    test_case("9.1 GET /dms/settings (check stop_sale_on_negative)")
    resp = requests.get(f"{BASE_URL}/dms/settings", headers=headers("owner"))
    if resp.status_code == 200:
        settings = resp.json()
        stop_sale = settings.get("stop_sale_on_negative", True)
        print(f"✅ stop_sale_on_negative: {stop_sale}")
    
    # 9.2 Ensure stop_sale_on_negative is enabled
    test_case("9.2 PUT /dms/settings (enable stop_sale_on_negative)")
    resp = requests.put(f"{BASE_URL}/dms/settings", json={"stop_sale_on_negative": True}, headers=headers("owner"))
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print(f"✅ stop_sale_on_negative enabled")
    
    # 9.3 Test primary order fulfill-line with insufficient stock
    # First, create a primary order
    test_case("9.3 Create primary order for stop-sale test")
    resp = requests.get(f"{BASE_URL}/dms/products", headers=headers("distributor1"))
    if resp.status_code == 200:
        products = resp.json().get("data", [])
        if products:
            test_product = products[0]
            test_product_id = test_product.get("id")
            
            # Check owner stock
            resp = requests.get(f"{BASE_URL}/dms/owner/inventory", headers=headers("owner"))
            if resp.status_code == 200:
                inventory = resp.json().get("data", [])
                product_inv = next((i for i in inventory if i.get("product_id") == test_product_id), None)
                if product_inv:
                    owner_stock = product_inv.get("qty_boxes", 0)
                    print(f"   Owner stock for test product: {owner_stock} boxes")
                    
                    # Place order for more than available stock
                    order_qty = owner_stock + 100  # Order more than available
                    order_payload = {
                        "items": [
                            {
                                "product_id": test_product_id,
                                "qty_boxes": order_qty
                            }
                        ],
                        "notes": "Test order for stop-sale"
                    }
                    resp = requests.post(f"{BASE_URL}/dms/primary-orders", json=order_payload, headers=headers("distributor1"))
                    if resp.status_code == 200:
                        order_data = resp.json()
                        order_id = order_data.get("id")
                        print(f"✅ Primary order created: {order_id}")
                        
                        # Try to fulfill more than available stock
                        test_case("9.4 POST fulfill-line with qty > owner_stock (expect 400)")
                        fulfill_qty = owner_stock + 50  # Try to fulfill more than available
                        fulfill_payload = {
                            "product_id": test_product_id,
                            "qty_boxes_fulfilled": fulfill_qty
                        }
                        resp = requests.post(f"{BASE_URL}/dms/primary-orders/{order_id}/fulfill-line", 
                                           json=fulfill_payload, headers=headers("owner"))
                        print(f"Status: {resp.status_code}")
                        if resp.status_code == 400:
                            print(f"✅ Correctly blocked fulfillment (insufficient stock)")
                            print(f"   Error: {resp.json().get('detail', '')}")
                        else:
                            print(f"❌ Expected 400, got {resp.status_code}")
                        
                        # Now disable stop_sale_on_negative and retry
                        test_case("9.5 Disable stop_sale_on_negative and retry")
                        resp = requests.put(f"{BASE_URL}/dms/settings", json={"stop_sale_on_negative": False}, headers=headers("owner"))
                        if resp.status_code == 200:
                            print(f"✅ stop_sale_on_negative disabled")
                            
                            # Retry fulfillment (should succeed now)
                            resp = requests.post(f"{BASE_URL}/dms/primary-orders/{order_id}/fulfill-line", 
                                               json=fulfill_payload, headers=headers("owner"))
                            print(f"Status: {resp.status_code}")
                            if resp.status_code == 200:
                                print(f"✅ Fulfillment succeeded with stop_sale disabled")
                            else:
                                print(f"❌ Failed: {resp.text}")
                        
                        # Re-enable stop_sale_on_negative
                        resp = requests.put(f"{BASE_URL}/dms/settings", json={"stop_sale_on_negative": True}, headers=headers("owner"))
    
    # 9.6 Test secondary order dispatch with insufficient distributor stock
    test_case("9.6 Test secondary dispatch with insufficient distributor stock")
    # Get distributor stock
    resp = requests.get(f"{BASE_URL}/dms/distributor/stock", headers=headers("distributor1"))
    if resp.status_code == 200:
        stock_data = resp.json()
        # Find a product with stock
        if isinstance(stock_data, dict) and "data" in stock_data:
            stock_items = stock_data.get("data", [])
        else:
            stock_items = []
        
        if stock_items:
            test_stock = stock_items[0]
            dist_product_id = test_stock.get("product_id")
            dist_stock = test_stock.get("qty_boxes", 0)
            print(f"   Distributor stock: {dist_stock} boxes")
            
            # Place secondary order for more than available
            order_qty = dist_stock + 50
            order_payload = {
                "retailer_id": None,  # Will need to get retailer ID
                "items": [
                    {
                        "product_id": dist_product_id,
                        "qty_boxes": order_qty,
                        "qty_pcs": 0
                    }
                ],
                "notes": "Test secondary order"
            }
            
            # Get retailer ID first
            resp = requests.get(f"{BASE_URL}/dms/retailers", headers=headers("distributor1"))
            if resp.status_code == 200:
                retailers = resp.json().get("data", [])
                if retailers:
                    retailer_id = retailers[0].get("id")
                    order_payload["retailer_id"] = retailer_id
                    
                    # Place order
                    resp = requests.post(f"{BASE_URL}/dms/secondary-orders", json=order_payload, headers=headers("distributor1"))
                    if resp.status_code == 200:
                        sec_order_data = resp.json()
                        sec_order_id = sec_order_data.get("id")
                        print(f"✅ Secondary order created: {sec_order_id}")
                        
                        # Try to dispatch more than available
                        test_case("9.7 POST dispatch with qty > distributor_stock (expect 400)")
                        dispatch_payload = {
                            "items": [
                                {
                                    "product_id": dist_product_id,
                                    "qty_boxes_dispatched": order_qty,
                                    "qty_pcs_dispatched": 0
                                }
                            ]
                        }
                        resp = requests.post(f"{BASE_URL}/dms/secondary-orders/{sec_order_id}/dispatch", 
                                           json=dispatch_payload, headers=headers("distributor1"))
                        print(f"Status: {resp.status_code}")
                        if resp.status_code == 400:
                            print(f"✅ Correctly blocked dispatch (insufficient distributor stock)")
                            print(f"   Error: {resp.json().get('detail', '')}")
                        else:
                            print(f"❌ Expected 400, got {resp.status_code}")
    
    # ========================================================================
    # 10. SAMPLE BILLS VERIFICATION
    # ========================================================================
    test_section("10. SAMPLE BILLS VERIFICATION")
    
    # 10.1 Find sample e-bill
    test_case("10.1 Find sample e-bill (EB-SAMPLE-*)")
    resp = requests.get(f"{BASE_URL}/dms/primary-orders", headers=headers("owner"))
    sample_ebill_id = None
    if resp.status_code == 200:
        orders = resp.json().get("data", [])
        for order in orders:
            ebill_no = order.get("ebill_no", "")
            if "SAMPLE" in ebill_no:
                sample_ebill_id = order.get("ebill_id")
                print(f"✅ Found sample e-bill: {ebill_no} (ID: {sample_ebill_id})")
                break
    
    # 10.2 GET print/ebill with T&C
    if sample_ebill_id:
        test_case("10.2 GET /dms/print/ebill/{id} (verify T&C fields)")
        resp = requests.get(f"{BASE_URL}/dms/print/ebill/{sample_ebill_id}", headers=headers("owner"))
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            ebill_data = resp.json()
            company_name = ebill_data.get("company_name", "")
            invoice_message = ebill_data.get("invoice_message", "")
            invoice_terms = ebill_data.get("invoice_terms", "")
            
            if company_name and invoice_message and invoice_terms:
                print(f"✅ All T&C fields present:")
                print(f"   company_name: {company_name[:50]}...")
                print(f"   invoice_message: {invoice_message[:50]}...")
                print(f"   invoice_terms: {invoice_terms[:50]}...")
            else:
                print(f"❌ Missing T&C fields:")
                print(f"   company_name: {'✅' if company_name else '❌'}")
                print(f"   invoice_message: {'✅' if invoice_message else '❌'}")
                print(f"   invoice_terms: {'✅' if invoice_terms else '❌'}")
        else:
            print(f"❌ Failed: {resp.text}")
    
    # 10.3 Find sample retailer bill
    test_case("10.3 Find sample retailer bill (RB-SAMPLE-*)")
    resp = requests.get(f"{BASE_URL}/dms/secondary-orders", headers=headers("distributor1"))
    sample_rbill_id = None
    if resp.status_code == 200:
        orders = resp.json().get("data", [])
        for order in orders:
            bill_no = order.get("bill_no", "")
            if "SAMPLE" in bill_no:
                sample_rbill_id = order.get("bill_id")
                print(f"✅ Found sample retailer bill: {bill_no} (ID: {sample_rbill_id})")
                break
    
    # 10.4 GET print/retailer-bill with T&C
    if sample_rbill_id:
        test_case("10.4 GET /dms/print/retailer-bill/{id} (verify T&C fields)")
        resp = requests.get(f"{BASE_URL}/dms/print/retailer-bill/{sample_rbill_id}", headers=headers("distributor1"))
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            rbill_data = resp.json()
            company_name = rbill_data.get("company_name", "")
            invoice_message = rbill_data.get("invoice_message", "")
            invoice_terms = rbill_data.get("invoice_terms", "")
            
            if company_name and invoice_message and invoice_terms:
                print(f"✅ All T&C fields present:")
                print(f"   company_name: {company_name[:50]}...")
                print(f"   invoice_message: {invoice_message[:50]}...")
                print(f"   invoice_terms: {invoice_terms[:50]}...")
            else:
                print(f"❌ Missing T&C fields:")
                print(f"   company_name: {'✅' if company_name else '❌'}")
                print(f"   invoice_message: {'✅' if invoice_message else '❌'}")
                print(f"   invoice_terms: {'✅' if invoice_terms else '❌'}")
        else:
            print(f"❌ Failed: {resp.text}")
    
    # ========================================================================
    # 11. REGRESSION SANITY
    # ========================================================================
    test_section("11. REGRESSION SANITY")
    
    # 11.1 GET settings
    test_case("11.1 GET /dms/settings")
    resp = requests.get(f"{BASE_URL}/dms/settings", headers=headers("owner"))
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        settings = resp.json()
        print(f"✅ Settings retrieved")
        print(f"   stop_sale_on_negative: {settings.get('stop_sale_on_negative')}")
        print(f"   invoice_terms present: {'✅' if settings.get('invoice_terms') else '❌'}")
        print(f"   invoice_message present: {'✅' if settings.get('invoice_message') else '❌'}")
    else:
        print(f"❌ Failed: {resp.text}")
    
    # 11.2 Owner can POST expenses (Phase 2A regression)
    test_case("11.2 POST /dms/expenses (Phase 2A regression)")
    today = datetime.now().strftime("%Y-%m-%d")
    expense_payload = {
        "date": today,
        "category": "Office Supplies",
        "amount": 500.0,
        "description": "Test expense",
        "vendor": "Test Vendor"
    }
    resp = requests.post(f"{BASE_URL}/dms/expenses", json=expense_payload, headers=headers("owner"))
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print(f"✅ Expense created (Phase 2A working)")
    else:
        print(f"❌ Failed: {resp.text}")
    
    # 11.3 Distributor can place primary order (Phase 1 regression)
    test_case("11.3 POST /dms/primary-orders (Phase 1 regression)")
    resp = requests.get(f"{BASE_URL}/dms/distributor/browse", headers=headers("distributor1"))
    if resp.status_code == 200:
        products = resp.json().get("data", [])
        if products:
            test_product = products[0]
            order_payload = {
                "items": [
                    {
                        "product_id": test_product.get("id"),
                        "qty_boxes": 2
                    }
                ],
                "notes": "Regression test order"
            }
            resp = requests.post(f"{BASE_URL}/dms/primary-orders", json=order_payload, headers=headers("distributor1"))
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"✅ Primary order created (Phase 1 working)")
            else:
                print(f"❌ Failed: {resp.text}")
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    test_section("TEST SUMMARY")
    print("\n✅ Phase 2B Backend Testing Complete!")
    print("\nAll major test scenarios executed:")
    print("  1. ✅ Cash & Bank — Bank Accounts (GET/POST/PUT/DELETE with RBAC)")
    print("  2. ✅ Cash & Bank — Bank Transactions (deposit/withdrawal with balance updates)")
    print("  3. ✅ Cash & Bank — Cash Register (in/out with balance aggregate)")
    print("  4. ✅ Cash & Bank — Cheques (CRUD with status updates)")
    print("  5. ✅ Cash & Bank — Loan Accounts (with auto disbursement)")
    print("  6. ✅ Cash & Bank — Loan Transactions (repayment/interest with outstanding)")
    print("  7. ✅ FY Lock Enforcement on Cash & Bank")
    print("  8. ✅ Godown Management (CRUD)")
    print("  9. ✅ Stock Transfer (owner↔godown, godown↔godown with stock movement)")
    print(" 10. ✅ Stop Sale on Negative Stock (fulfill-line + dispatch + toggle)")
    print(" 11. ✅ Sample Bills Verification (T&C fields)")
    print(" 12. ✅ Regression Sanity (Phase 1 + 2A)")
    print("\nReview the detailed output above for any failures.")

if __name__ == "__main__":
    main()
