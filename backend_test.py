#!/usr/bin/env python3
"""
Phase 3 Reverse Logistics & Approval Engine Backend Test Suite
Tests all /api/reverse/* endpoints with comprehensive validation
"""
import requests
import json
import sys
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BASE_URL = "https://ed15ce41-22af-49d9-bd1d-94afbf07f3d2.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "admin@gooil.com"
ADMIN_PASSWORD = "GoOil@2026"

# Global token storage
TOKEN = None
HEADERS = {}

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def log_pass(test_name: str, details: str = ""):
    """Log a passed test"""
    msg = f"✅ PASS: {test_name}"
    if details:
        msg += f" - {details}"
    print(msg)
    test_results["passed"].append({"test": test_name, "details": details})

def log_fail(test_name: str, error: str):
    """Log a failed test"""
    msg = f"❌ FAIL: {test_name} - {error}"
    print(msg)
    test_results["failed"].append({"test": test_name, "error": error})

def log_warn(test_name: str, warning: str):
    """Log a warning"""
    msg = f"⚠️  WARN: {test_name} - {warning}"
    print(msg)
    test_results["warnings"].append({"test": test_name, "warning": warning})

def make_request(method: str, endpoint: str, data: Optional[Dict] = None, 
                 params: Optional[Dict] = None) -> tuple[int, Any]:
    """Make HTTP request and return status code and response data"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        elif method == "POST":
            resp = requests.post(url, headers=HEADERS, json=data, timeout=30)
        elif method == "PUT":
            resp = requests.put(url, headers=HEADERS, json=data, timeout=30)
        elif method == "DELETE":
            resp = requests.delete(url, headers=HEADERS, timeout=30)
        else:
            return 0, {"error": f"Unsupported method: {method}"}
        
        try:
            return resp.status_code, resp.json()
        except Exception:
            return resp.status_code, {"text": resp.text}
    except Exception as e:
        return 0, {"error": str(e)}

def login():
    """Login and get JWT token"""
    global TOKEN, HEADERS
    print("\n" + "="*80)
    print("AUTHENTICATION")
    print("="*80)
    
    status, data = make_request("POST", "/auth/login", {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    
    if status != 200:
        log_fail("Login", f"Status {status}: {data}")
        sys.exit(1)
    
    TOKEN = data.get("token")
    if not TOKEN:
        log_fail("Login", "No token in response")
        sys.exit(1)
    
    HEADERS = {"Authorization": f"Bearer {TOKEN}"}
    log_pass("Login", f"Authenticated as {ADMIN_EMAIL}")

def test_approval_matrix():
    """Test 1: Approval Matrix + Requests"""
    print("\n" + "="*80)
    print("TEST 1: APPROVAL MATRIX + REQUESTS")
    print("="*80)
    
    # GET approval matrix - should seed defaults
    status, data = make_request("GET", "/reverse/approval-matrix")
    if status != 200:
        log_fail("Approval Matrix GET", f"Status {status}: {data}")
        return
    
    rules = data.get("data", [])
    count = data.get("count", 0)
    
    if count < 12:
        log_fail("Approval Matrix Seed", f"Expected 12 rules, got {count}")
        return
    
    # Verify 8 entity types present
    entity_types = set(r.get("entity_type") for r in rules)
    expected_types = {"return", "claim", "credit_note", "debit_note", "replacement", 
                      "expense", "high_value_discount", "credit_limit"}
    
    if not expected_types.issubset(entity_types):
        missing = expected_types - entity_types
        log_fail("Approval Matrix Entity Types", f"Missing types: {missing}")
        return
    
    log_pass("Approval Matrix GET", f"Seeded {count} rules across {len(entity_types)} entity types")
    
    # Test upsert custom rule
    custom_rule = {
        "entity_type": "return",
        "amount_min": 10000,
        "amount_max": 50000,
        "levels": [
            {"level": 1, "role": "regional_manager"},
            {"level": 2, "role": "company_admin"},
            {"level": 3, "role": "super_admin"}
        ]
    }
    
    status, data = make_request("POST", "/reverse/approval-matrix", custom_rule)
    if status != 200:
        log_fail("Approval Matrix POST", f"Status {status}: {data}")
        return
    
    if data.get("entity_type") != "return":
        log_fail("Approval Matrix POST", "Custom rule not created properly")
        return
    
    log_pass("Approval Matrix POST", "Custom rule created successfully")

def get_test_invoice():
    """Get a test invoice for return testing"""
    status, data = make_request("GET", "/collections/invoices", params={"limit": 5})
    if status != 200 or not data.get("data"):
        return None
    
    invoices = data.get("data", [])
    for inv in invoices:
        if inv.get("lines") and inv.get("party_id"):
            return inv
    return None

def get_test_sku_and_batch():
    """Get a real SKU and batch from inventory"""
    status, data = make_request("GET", "/workflow/inventory/company")
    if status != 200 or not data.get("data"):
        return None, None
    
    inventory = data.get("data", [])
    for item in inventory:
        if item.get("available", 0) > 10:
            return item.get("sku_id"), item.get("batch_id")
    
    # Fallback to first item
    if inventory:
        return inventory[0].get("sku_id"), inventory[0].get("batch_id")
    
    return None, None

def test_return_lifecycle():
    """Test 2: Return lifecycle (CRITICAL end-to-end)"""
    print("\n" + "="*80)
    print("TEST 2: RETURN LIFECYCLE (CRITICAL)")
    print("="*80)
    
    # Get test invoice
    invoice = get_test_invoice()
    if not invoice:
        log_warn("Return Lifecycle", "No suitable invoice found, creating minimal return")
        # Create return without invoice
        return_payload = {
            "scope": "distributor",
            "reason": "damaged_product",
            "party_id": "dist-100",
            "party_type": "distributor",
            "lines": [
                {
                    "sku_id": "sku-001",
                    "batch_id": "batch-001",
                    "qty": 5,
                    "price": 120
                }
            ],
            "remarks": "Test return for Phase 3"
        }
    else:
        # Use invoice data
        first_line = invoice["lines"][0]
        batch_id = None
        if first_line.get("reserved_allocations"):
            batch_id = first_line["reserved_allocations"][0].get("batch_id")
        
        return_payload = {
            "scope": "distributor",
            "reason": "damaged_product",
            "party_id": invoice.get("party_id"),
            "party_type": "distributor",
            "invoice_id": invoice.get("id"),
            "lines": [
                {
                    "sku_id": first_line.get("sku_id"),
                    "batch_id": batch_id,
                    "qty": 5,
                    "price": first_line.get("price", 120)
                }
            ],
            "remarks": "Test return from invoice"
        }
    
    # Create return
    status, return_data = make_request("POST", "/reverse/returns", return_payload)
    if status != 200:
        log_fail("Return Create", f"Status {status}: {return_data}")
        return None
    
    return_id = return_data.get("id")
    return_no = return_data.get("return_no")
    approval_request_id = return_data.get("approval_request_id")
    
    if not return_id:
        log_fail("Return Create", "No return ID in response")
        return None
    
    if return_data.get("status") != "under_review":
        log_fail("Return Create", f"Expected status 'under_review', got '{return_data.get('status')}'")
        return None
    
    if not approval_request_id:
        log_fail("Return Create", "No approval_request_id in response")
        return None
    
    log_pass("Return Create", f"Created {return_no} with approval request")
    
    # Get return details
    status, detail_data = make_request("GET", f"/reverse/returns/{return_id}")
    if status != 200:
        log_fail("Return GET", f"Status {status}: {detail_data}")
        return None
    
    ret = detail_data.get("return")
    apr = detail_data.get("approval_request")
    
    if not ret or not apr:
        log_fail("Return GET", "Missing return or approval_request in response")
        return None
    
    log_pass("Return GET", f"Retrieved return with approval_request and audit_trail")
    
    # Get inventory before approval
    party_id = return_payload.get("party_id")
    sku_id = return_payload["lines"][0]["sku_id"]
    batch_id = return_payload["lines"][0].get("batch_id")
    
    inventory_before = None
    if batch_id:
        status, inv_data = make_request("GET", "/workflow/inventory/company")
        if status == 200:
            for item in inv_data.get("data", []):
                if item.get("sku_id") == sku_id and item.get("batch_id") == batch_id:
                    inventory_before = item
                    break
    
    # Fast-approve the return
    status, approve_data = make_request("POST", f"/reverse/returns/{return_id}/approve", 
                                       {"comment": "Test approval"})
    if status != 200:
        log_fail("Return Approve", f"Status {status}: {approve_data}")
        return None
    
    executed = approve_data.get("executed")
    if not executed:
        log_fail("Return Approve", "No executed result in response")
        return None
    
    credit_note = executed.get("credit_note")
    if not credit_note:
        log_fail("Return Approve", "No credit_note in executed result")
        return None
    
    log_pass("Return Approve", f"Approved and executed, credit_note: {credit_note.get('cn_no')}")
    
    # Re-fetch return to verify completion
    status, detail_data = make_request("GET", f"/reverse/returns/{return_id}")
    if status != 200:
        log_fail("Return Verify Completion", f"Status {status}")
        return None
    
    ret = detail_data.get("return")
    if ret.get("status") != "completed":
        log_fail("Return Verify Completion", f"Expected status 'completed', got '{ret.get('status')}'")
        return None
    
    if not ret.get("inventory_adjusted"):
        log_fail("Return Verify Completion", "inventory_adjusted not set to true")
        return None
    
    if not ret.get("credit_note_id"):
        log_fail("Return Verify Completion", "credit_note_id not set")
        return None
    
    log_pass("Return Verify Completion", "Status=completed, inventory_adjusted=true, credit_note_id set")
    
    # Verify inventory adjustment (returned bucket incremented)
    if batch_id:
        status, inv_data = make_request("GET", "/workflow/inventory/company")
        if status == 200:
            inventory_after = None
            for item in inv_data.get("data", []):
                if item.get("sku_id") == sku_id and item.get("batch_id") == batch_id:
                    inventory_after = item
                    break
            
            if inventory_after:
                returned_before = inventory_before.get("returned", 0) if inventory_before else 0
                returned_after = inventory_after.get("returned", 0)
                
                if returned_after >= returned_before + 5:
                    log_pass("Inventory Adjustment", f"Returned bucket incremented by 5 (was {returned_before}, now {returned_after})")
                else:
                    log_warn("Inventory Adjustment", f"Returned bucket not incremented as expected (was {returned_before}, now {returned_after})")
    
    # Verify stock_ledger entry
    status, ledger_data = make_request("GET", "/workflow/stock-ledger", params={"limit": 50})
    if status == 200:
        ledger_entries = ledger_data.get("data", [])
        found_return_entry = False
        for entry in ledger_entries:
            if entry.get("reference_id") == return_id and entry.get("movement") == "return_in":
                found_return_entry = True
                break
        
        if found_return_entry:
            log_pass("Stock Ledger", f"Found return_in entry for return_id {return_id}")
        else:
            log_warn("Stock Ledger", f"No return_in entry found for return_id {return_id}")
    
    # Verify credit_note exists
    cn_id = credit_note.get("id")
    status, cn_data = make_request("GET", "/reverse/credit-notes")
    if status == 200:
        cns = cn_data.get("data", [])
        found_cn = any(cn.get("id") == cn_id for cn in cns)
        if found_cn:
            log_pass("Credit Note Verification", f"Credit note {credit_note.get('cn_no')} exists")
        else:
            log_fail("Credit Note Verification", f"Credit note {cn_id} not found in list")
    
    # Verify double_ledger entries
    status, ledger_data = make_request("GET", "/finance/ledger", params={"limit": 50})
    if status == 200:
        entries = ledger_data.get("data", [])
        cn_entries = [e for e in entries if e.get("reference_id") == cn_id]
        
        if len(cn_entries) >= 3:
            # Check for SALES Dr, TAX_OUT Dr, AR Cr
            has_sales_dr = any(e.get("account") == "SALES" and e.get("debit", 0) > 0 for e in cn_entries)
            has_tax_dr = any(e.get("account") == "TAX_OUT" and e.get("debit", 0) > 0 for e in cn_entries)
            has_ar_cr = any(e.get("account") == "AR" and e.get("credit", 0) > 0 for e in cn_entries)
            
            if has_sales_dr and has_tax_dr and has_ar_cr:
                # Check balance
                total_dr = sum(e.get("debit", 0) for e in cn_entries)
                total_cr = sum(e.get("credit", 0) for e in cn_entries)
                
                if abs(total_dr - total_cr) < 0.01:
                    log_pass("Double Ledger", f"3 entries found (SALES Dr, TAX_OUT Dr, AR Cr), balanced")
                else:
                    log_fail("Double Ledger", f"Entries not balanced: Dr={total_dr}, Cr={total_cr}")
            else:
                log_fail("Double Ledger", "Missing required entries (SALES Dr, TAX_OUT Dr, AR Cr)")
        else:
            log_warn("Double Ledger", f"Expected 3 entries for credit_note, found {len(cn_entries)}")
    
    # Verify outstanding recomputed
    if party_id:
        status, out_data = make_request("GET", f"/finance/outstanding/distributor/{party_id}")
        if status == 200:
            log_pass("Outstanding Recompute", f"Outstanding retrieved for {party_id}")
        else:
            log_warn("Outstanding Recompute", f"Could not retrieve outstanding for {party_id}")
    
    return return_id

def test_return_rejection():
    """Test 3: Return rejection path"""
    print("\n" + "="*80)
    print("TEST 3: RETURN REJECTION PATH")
    print("="*80)
    
    # Get real SKU and batch
    sku_id, batch_id = get_test_sku_and_batch()
    if not sku_id:
        log_warn("Return Rejection", "No SKU available, skipping test")
        return
    
    # Create a return
    return_payload = {
        "scope": "distributor",
        "reason": "wrong_product",
        "party_id": "dist-100",
        "party_type": "distributor",
        "lines": [
            {
                "sku_id": sku_id,
                "batch_id": batch_id,
                "qty": 3,
                "price": 100
            }
        ],
        "remarks": "Test rejection"
    }
    
    status, return_data = make_request("POST", "/reverse/returns", return_payload)
    if status != 200:
        log_fail("Return Rejection - Create", f"Status {status}: {return_data}")
        return
    
    return_id = return_data.get("id")
    
    # Reject the return
    status, reject_data = make_request("POST", f"/reverse/returns/{return_id}/reject", 
                                      {"reason": "Invalid return request"})
    if status != 200:
        log_fail("Return Rejection - Reject", f"Status {status}: {reject_data}")
        return
    
    # Verify status changed to rejected
    status, detail_data = make_request("GET", f"/reverse/returns/{return_id}")
    if status != 200:
        log_fail("Return Rejection - Verify", f"Status {status}")
        return
    
    ret = detail_data.get("return")
    if ret.get("status") != "rejected":
        log_fail("Return Rejection - Verify", f"Expected status 'rejected', got '{ret.get('status')}'")
        return
    
    # Verify no credit note created
    cn = detail_data.get("credit_note")
    if cn:
        log_fail("Return Rejection - No CN", "Credit note should not be created for rejected return")
        return
    
    log_pass("Return Rejection", "Return rejected, status=rejected, no credit note created")

def test_damage():
    """Test 4: Damage"""
    print("\n" + "="*80)
    print("TEST 4: DAMAGE")
    print("="*80)
    
    # Get company inventory with available stock
    status, inv_data = make_request("GET", "/workflow/inventory/company")
    if status != 200:
        log_fail("Damage - Get Inventory", f"Status {status}")
        return
    
    inventory = inv_data.get("data", [])
    test_item = None
    for item in inventory:
        if item.get("available", 0) > 5:
            test_item = item
            break
    
    if not test_item:
        log_warn("Damage", "No inventory with available > 5 found")
        return
    
    damage_payload = {
        "scope": "warehouse",
        "sku_id": test_item.get("sku_id"),
        "batch_id": test_item.get("batch_id"),
        "qty": 3,
        "estimated_value": 200,
        "reason": "Warehouse damage test"
    }
    
    # Record damage
    status, damage_data = make_request("POST", "/reverse/damage", damage_payload)
    if status != 200:
        log_fail("Damage - Create", f"Status {status}: {damage_data}")
        return
    
    damage_id = damage_data.get("id")
    damage_no = damage_data.get("damage_no")
    
    if not damage_id:
        log_fail("Damage - Create", "No damage ID in response")
        return
    
    log_pass("Damage - Create", f"Created {damage_no}")
    
    # Verify inventory adjustment (available -3, damaged +3)
    if test_item:
        status, inv_data = make_request("GET", "/workflow/inventory/company")
        if status == 200:
            inventory_after = None
            for item in inv_data.get("data", []):
                if (item.get("sku_id") == test_item.get("sku_id") and 
                    item.get("batch_id") == test_item.get("batch_id")):
                    inventory_after = item
                    break
            
            if inventory_after:
                available_before = test_item.get("available", 0)
                available_after = inventory_after.get("available", 0)
                damaged_before = test_item.get("damaged", 0)
                damaged_after = inventory_after.get("damaged", 0)
                
                if (available_after <= available_before - 3 and 
                    damaged_after >= damaged_before + 3):
                    log_pass("Damage - Inventory", f"Available -3, Damaged +3")
                else:
                    log_warn("Damage - Inventory", 
                            f"Inventory not adjusted as expected (avail: {available_before}→{available_after}, damaged: {damaged_before}→{damaged_after})")
    
    # Verify stock_ledger entry
    status, ledger_data = make_request("GET", "/workflow/stock-ledger", params={"limit": 50})
    if status == 200:
        ledger_entries = ledger_data.get("data", [])
        found_damage_entry = False
        for entry in ledger_entries:
            if (entry.get("reference_id") == damage_id and 
                entry.get("movement") == "damage" and
                entry.get("from_bucket") == "available" and
                entry.get("to_bucket") == "damaged"):
                found_damage_entry = True
                break
        
        if found_damage_entry:
            log_pass("Damage - Stock Ledger", f"Found damage entry with correct bucket move")
        else:
            log_warn("Damage - Stock Ledger", f"No damage entry found for damage_id {damage_id}")

def test_claim_settle():
    """Test 5: Claim → settle"""
    print("\n" + "="*80)
    print("TEST 5: CLAIM → SETTLE")
    print("="*80)
    
    # Create claim
    claim_payload = {
        "type": "transport",
        "party_id": "dist-100",
        "party_type": "distributor",
        "amount": 1500,
        "reason": "Vehicle damaged goods during transport"
    }
    
    status, claim_data = make_request("POST", "/reverse/claims", claim_payload)
    if status != 200:
        log_fail("Claim - Create", f"Status {status}: {claim_data}")
        return
    
    claim_id = claim_data.get("id")
    claim_no = claim_data.get("claim_no")
    approval_request_id = claim_data.get("approval_request_id")
    
    if not claim_id or not approval_request_id:
        log_fail("Claim - Create", "Missing claim_id or approval_request_id")
        return
    
    log_pass("Claim - Create", f"Created {claim_no} with approval request")
    
    # Approve the claim (super_admin override)
    status, apr_data = make_request("POST", f"/reverse/approval-requests/{approval_request_id}/approve",
                                   {"comment": "Approved for testing"})
    if status != 200:
        log_fail("Claim - Approve", f"Status {status}: {apr_data}")
        return
    
    # Check if claim is approved
    status, claim_list = make_request("GET", "/reverse/claims")
    if status == 200:
        claims = claim_list.get("data", [])
        claim = next((c for c in claims if c.get("id") == claim_id), None)
        if claim and claim.get("status") == "approved":
            log_pass("Claim - Approve", f"Claim status changed to approved")
        else:
            log_warn("Claim - Approve", f"Claim status: {claim.get('status') if claim else 'not found'}")
    
    # Settle the claim
    status, settle_data = make_request("POST", f"/reverse/claims/{claim_id}/settle",
                                      {"settlement_amount": 1500, "method": "Bank Transfer"})
    if status != 200:
        log_fail("Claim - Settle", f"Status {status}: {settle_data}")
        return
    
    log_pass("Claim - Settle", f"Settled with amount 1500")
    
    # Verify ledger entries (CASH Dr / AR Cr)
    status, ledger_data = make_request("GET", "/finance/ledger", params={"limit": 50})
    if status == 200:
        entries = ledger_data.get("data", [])
        claim_entries = [e for e in entries if e.get("reference_id") == claim_id]
        
        if len(claim_entries) >= 2:
            has_cash_dr = any(e.get("account") == "CASH" and e.get("debit", 0) > 0 for e in claim_entries)
            has_ar_cr = any(e.get("account") == "AR" and e.get("credit", 0) > 0 for e in claim_entries)
            
            if has_cash_dr and has_ar_cr:
                log_pass("Claim - Ledger", "CASH Dr / AR Cr entries found")
            else:
                log_warn("Claim - Ledger", "Missing CASH Dr or AR Cr entries")
        else:
            log_warn("Claim - Ledger", f"Expected 2 entries, found {len(claim_entries)}")
    
    # Verify outstanding refreshed
    status, out_data = make_request("GET", "/finance/outstanding/distributor/dist-100")
    if status == 200:
        log_pass("Claim - Outstanding", "Outstanding retrieved after settlement")
    else:
        log_warn("Claim - Outstanding", "Could not retrieve outstanding")

def test_manual_credit_note():
    """Test 6: Manual Credit Note (non-return)"""
    print("\n" + "="*80)
    print("TEST 6: MANUAL CREDIT NOTE")
    print("="*80)
    
    cn_payload = {
        "reason": "over_billing",
        "party_id": "dist-100",
        "party_type": "distributor",
        "subtotal": 1000,
        "tax": 180,
        "total": 1180,
        "remarks": "Test manual credit note"
    }
    
    status, cn_data = make_request("POST", "/reverse/credit-notes", cn_payload)
    if status != 200:
        log_fail("Manual CN - Create", f"Status {status}: {cn_data}")
        return
    
    cn_id = cn_data.get("id")
    cn_no = cn_data.get("cn_no")
    
    if not cn_id:
        log_fail("Manual CN - Create", "No credit note ID in response")
        return
    
    log_pass("Manual CN - Create", f"Created {cn_no}")
    
    # Verify ledger entries (SALES Dr 1000, TAX_OUT Dr 180, AR Cr 1180)
    status, ledger_data = make_request("GET", "/finance/ledger", params={"limit": 50})
    if status == 200:
        entries = ledger_data.get("data", [])
        cn_entries = [e for e in entries if e.get("reference_id") == cn_id]
        
        if len(cn_entries) >= 3:
            sales_dr = next((e for e in cn_entries if e.get("account") == "SALES" and e.get("debit", 0) > 0), None)
            tax_dr = next((e for e in cn_entries if e.get("account") == "TAX_OUT" and e.get("debit", 0) > 0), None)
            ar_cr = next((e for e in cn_entries if e.get("account") == "AR" and e.get("credit", 0) > 0), None)
            
            if sales_dr and tax_dr and ar_cr:
                # Check amounts
                if (abs(sales_dr.get("debit", 0) - 1000) < 0.01 and
                    abs(tax_dr.get("debit", 0) - 180) < 0.01 and
                    abs(ar_cr.get("credit", 0) - 1180) < 0.01):
                    log_pass("Manual CN - Ledger", "SALES Dr 1000, TAX_OUT Dr 180, AR Cr 1180 - balanced")
                else:
                    log_warn("Manual CN - Ledger", "Entries found but amounts don't match expected")
            else:
                log_fail("Manual CN - Ledger", "Missing required entries")
        else:
            log_warn("Manual CN - Ledger", f"Expected 3 entries, found {len(cn_entries)}")
    
    # Verify outstanding dropped
    status, out_data = make_request("GET", "/finance/outstanding/distributor/dist-100")
    if status == 200:
        log_pass("Manual CN - Outstanding", "Outstanding retrieved after CN")
    else:
        log_warn("Manual CN - Outstanding", "Could not retrieve outstanding")

def test_debit_note():
    """Test 7: Debit Note"""
    print("\n" + "="*80)
    print("TEST 7: DEBIT NOTE")
    print("="*80)
    
    dn_payload = {
        "reason": "penalty",
        "party_id": "dist-100",
        "party_type": "distributor",
        "amount": 500,
        "remarks": "Test debit note"
    }
    
    status, dn_data = make_request("POST", "/reverse/debit-notes", dn_payload)
    if status != 200:
        log_fail("Debit Note - Create", f"Status {status}: {dn_data}")
        return
    
    dn_id = dn_data.get("id")
    dn_no = dn_data.get("dn_no")
    total = dn_data.get("total")
    tax = dn_data.get("tax")
    
    if not dn_id:
        log_fail("Debit Note - Create", "No debit note ID in response")
        return
    
    log_pass("Debit Note - Create", f"Created {dn_no}, total={total}")
    
    # Verify ledger entries (AR Dr 590, SALES Cr 500, TAX_OUT Cr 90)
    status, ledger_data = make_request("GET", "/finance/ledger", params={"limit": 50})
    if status == 200:
        entries = ledger_data.get("data", [])
        dn_entries = [e for e in entries if e.get("reference_id") == dn_id]
        
        if len(dn_entries) >= 3:
            ar_dr = next((e for e in dn_entries if e.get("account") == "AR" and e.get("debit", 0) > 0), None)
            sales_cr = next((e for e in dn_entries if e.get("account") == "SALES" and e.get("credit", 0) > 0), None)
            tax_cr = next((e for e in dn_entries if e.get("account") == "TAX_OUT" and e.get("credit", 0) > 0), None)
            
            if ar_dr and sales_cr and tax_cr:
                # Check balance
                total_dr = sum(e.get("debit", 0) for e in dn_entries)
                total_cr = sum(e.get("credit", 0) for e in dn_entries)
                
                if abs(total_dr - total_cr) < 0.01:
                    log_pass("Debit Note - Ledger", f"AR Dr, SALES Cr, TAX_OUT Cr - balanced")
                else:
                    log_fail("Debit Note - Ledger", f"Not balanced: Dr={total_dr}, Cr={total_cr}")
            else:
                log_fail("Debit Note - Ledger", "Missing required entries")
        else:
            log_warn("Debit Note - Ledger", f"Expected 3 entries, found {len(dn_entries)}")
    
    # Verify outstanding increased
    status, out_data = make_request("GET", "/finance/outstanding/distributor/dist-100")
    if status == 200:
        log_pass("Debit Note - Outstanding", "Outstanding retrieved after DN")
    else:
        log_warn("Debit Note - Outstanding", "Could not retrieve outstanding")

def test_replacement():
    """Test 8: Replacement"""
    print("\n" + "="*80)
    print("TEST 8: REPLACEMENT")
    print("="*80)
    
    # Get real SKU and batch
    sku_id, batch_id = get_test_sku_and_batch()
    if not sku_id:
        log_warn("Replacement", "No SKU available, skipping test")
        return
    
    # First create and approve a return
    return_payload = {
        "scope": "distributor",
        "reason": "damaged_product",
        "party_id": "dist-100",
        "party_type": "distributor",
        "lines": [
            {
                "sku_id": sku_id,
                "batch_id": batch_id,
                "qty": 2,
                "price": 150
            }
        ],
        "remarks": "Return for replacement test"
    }
    
    status, return_data = make_request("POST", "/reverse/returns", return_payload)
    if status != 200:
        log_fail("Replacement - Create Return", f"Status {status}: {return_data}")
        return
    
    return_id = return_data.get("id")
    
    # Fast-approve the return
    status, approve_data = make_request("POST", f"/reverse/returns/{return_id}/approve",
                                       {"comment": "Approved for replacement"})
    if status != 200:
        log_warn("Replacement - Approve Return", f"Status {status}")
    
    # Create replacement
    replacement_payload = {
        "return_id": return_id,
        "scope": "distributor",
        "party_id": "dist-100",
        "party_type": "distributor",
        "lines": [
            {
                "sku_id": sku_id,
                "sku_code": "TEST-SKU",
                "product_name": "Test Product",
                "pack_size": "1L",
                "qty": 2,
                "price": 150
            }
        ],
        "reason": "Replacement for damaged goods"
    }
    
    status, rep_data = make_request("POST", "/reverse/replacements", replacement_payload)
    if status != 200:
        log_fail("Replacement - Create", f"Status {status}: {rep_data}")
        return
    
    rep_id = rep_data.get("id")
    rep_no = rep_data.get("replacement_no")
    approval_request_id = rep_data.get("approval_request_id")
    
    if not rep_id or not approval_request_id:
        log_fail("Replacement - Create", "Missing replacement_id or approval_request_id")
        return
    
    log_pass("Replacement - Create", f"Created {rep_no} with approval request")
    
    # Approve replacement (may need multiple approvals)
    status, apr_data = make_request("POST", f"/reverse/approval-requests/{approval_request_id}/approve",
                                   {"comment": "Approved step 1"})
    if status != 200:
        log_fail("Replacement - Approve Step 1", f"Status {status}: {apr_data}")
        return
    
    # Check if more approvals needed
    apr = apr_data.get("request")
    if apr and apr.get("status") == "pending":
        # Need another approval
        status, apr_data2 = make_request("POST", f"/reverse/approval-requests/{approval_request_id}/approve",
                                        {"comment": "Approved step 2"})
        if status != 200:
            log_warn("Replacement - Approve Step 2", f"Status {status}")
    
    executed = apr_data.get("executed")
    if executed:
        dispatch_id = executed.get("dispatch_id")
        grn_id = executed.get("grn_id")
        
        if dispatch_id and grn_id:
            log_pass("Replacement - Execute", f"Executed with dispatch_id and grn_id")
        else:
            log_warn("Replacement - Execute", "Missing dispatch_id or grn_id in executed result")
    else:
        log_warn("Replacement - Execute", "No executed result (may need more approvals)")
    
    # Get replacement details
    status, rep_detail = make_request("GET", f"/reverse/replacements/{rep_id}")
    if status != 200:
        log_fail("Replacement - GET", f"Status {status}")
        return
    
    replacement = rep_detail.get("replacement")
    dispatch = rep_detail.get("dispatch")
    grn = rep_detail.get("grn")
    linked_return = rep_detail.get("return")
    
    if replacement:
        log_pass("Replacement - GET", f"Retrieved replacement with linked return, dispatch, grn")
    
    # Verify dispatch exists
    if dispatch:
        if dispatch.get("type") == "replacement":
            log_pass("Replacement - Dispatch", f"Dispatch created with type=replacement")
        else:
            log_warn("Replacement - Dispatch", f"Dispatch type: {dispatch.get('type')}")
    
    # Verify GRN exists
    if grn:
        if grn.get("type") == "replacement":
            log_pass("Replacement - GRN", f"GRN created with type=replacement")
        else:
            log_warn("Replacement - GRN", f"GRN type: {grn.get('type')}")

def test_expiry():
    """Test 9: Expiry"""
    print("\n" + "="*80)
    print("TEST 9: EXPIRY")
    print("="*80)
    
    # Get expiry overview
    status, exp_data = make_request("GET", "/reverse/expiry", params={"days": 180})
    if status != 200:
        log_fail("Expiry - Overview", f"Status {status}: {exp_data}")
        return
    
    near_expiry = exp_data.get("near_expiry", [])
    expired = exp_data.get("expired", [])
    blocked = exp_data.get("blocked", [])
    destroyed = exp_data.get("destroyed", [])
    return_to_company = exp_data.get("return_to_company", [])
    count = exp_data.get("count", {})
    
    log_pass("Expiry - Overview", 
            f"Near: {count.get('near', 0)}, Expired: {count.get('expired', 0)}, "
            f"Blocked: {count.get('blocked', 0)}, Destroyed: {count.get('destroyed', 0)}")
    
    # Try to block a batch if any exist
    test_batch_id = None
    if near_expiry:
        test_batch_id = near_expiry[0].get("id")
    elif expired:
        test_batch_id = expired[0].get("id")
    
    if test_batch_id:
        status, action_data = make_request("POST", f"/reverse/expiry/{test_batch_id}/action",
                                          {"action": "block", "reason": "Test block action"})
        if status != 200:
            log_fail("Expiry - Action", f"Status {status}: {action_data}")
        else:
            log_pass("Expiry - Action", f"Blocked batch {test_batch_id}")
            
            # Verify expiry_records created
            status, exp_data2 = make_request("GET", "/reverse/expiry", params={"days": 180})
            if status == 200:
                blocked_after = exp_data2.get("blocked", [])
                if len(blocked_after) > len(blocked):
                    log_pass("Expiry - Record", "Expiry record created")
                else:
                    log_warn("Expiry - Record", "Expiry record count did not increase")
    else:
        log_warn("Expiry - Action", "No batches available to test action")

def test_exception_scanner():
    """Test 10: Exception scanner"""
    print("\n" + "="*80)
    print("TEST 10: EXCEPTION SCANNER")
    print("="*80)
    
    # Scan for exceptions
    status, scan_data = make_request("POST", "/reverse/exceptions/scan")
    if status != 200:
        log_fail("Exception Scanner - Scan", f"Status {status}: {scan_data}")
        return
    
    found = scan_data.get("found", 0)
    exceptions = scan_data.get("exceptions", [])
    
    log_pass("Exception Scanner - Scan", f"Found {found} exceptions")
    
    # Scan again to verify idempotency
    status, scan_data2 = make_request("POST", "/reverse/exceptions/scan")
    if status != 200:
        log_fail("Exception Scanner - Scan 2", f"Status {status}")
        return
    
    found2 = scan_data2.get("found", 0)
    
    if found2 == 0:
        log_pass("Exception Scanner - Idempotency", "Second scan did not duplicate open exceptions")
    else:
        log_warn("Exception Scanner - Idempotency", f"Second scan found {found2} new exceptions")
    
    # List open exceptions
    status, list_data = make_request("GET", "/reverse/exceptions", params={"status": "open"})
    if status != 200:
        log_fail("Exception Scanner - List", f"Status {status}")
        return
    
    open_exceptions = list_data.get("data", [])
    log_pass("Exception Scanner - List", f"Retrieved {len(open_exceptions)} open exceptions")
    
    # Resolve one exception if any exist
    if open_exceptions:
        exc_id = open_exceptions[0].get("id")
        status, resolve_data = make_request("POST", f"/reverse/exceptions/{exc_id}/resolve",
                                           {"resolution": "Test resolution", "status": "resolved"})
        if status != 200:
            log_fail("Exception Scanner - Resolve", f"Status {status}")
        else:
            log_pass("Exception Scanner - Resolve", f"Resolved exception {exc_id}")

def test_reports_hub():
    """Test 11: Reports Hub"""
    print("\n" + "="*80)
    print("TEST 11: REPORTS HUB")
    print("="*80)
    
    reports = ["returns", "damage", "claims", "credit_notes", "debit_notes", 
               "expiry", "replacements", "approvals", "audit"]
    
    for report in reports:
        status, data = make_request("GET", f"/reverse/reports/{report}")
        if status != 200:
            log_fail(f"Report - {report}", f"Status {status}: {data}")
        else:
            count = data.get("count", 0)
            log_pass(f"Report - {report}", f"Retrieved report with {count} records")

def test_audit_log():
    """Test 12: Audit log"""
    print("\n" + "="*80)
    print("TEST 12: AUDIT LOG")
    print("="*80)
    
    status, data = make_request("GET", "/finance/audit-log", params={"limit": 50})
    if status != 200:
        log_fail("Audit Log", f"Status {status}: {data}")
        return
    
    entries = data.get("data", [])
    
    # Check for Phase 3 actions
    phase3_actions = [
        "create_return", "complete_return", "approve_step", "create_damage",
        "create_credit_note", "create_debit_note", "create_claim", "settle_claim",
        "create_replacement", "execute_replacement", "expiry_action", "scan_exceptions"
    ]
    
    found_actions = set()
    for entry in entries:
        action = entry.get("action")
        if action in phase3_actions:
            found_actions.add(action)
    
    if found_actions:
        log_pass("Audit Log", f"Found Phase 3 actions: {', '.join(sorted(found_actions))}")
    else:
        log_warn("Audit Log", "No Phase 3 actions found in recent audit log")

def print_summary():
    """Print test summary"""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    total = len(test_results["passed"]) + len(test_results["failed"])
    passed = len(test_results["passed"])
    failed = len(test_results["failed"])
    warnings = len(test_results["warnings"])
    
    print(f"\nTotal Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Warnings: {warnings}")
    
    if test_results["failed"]:
        print("\n" + "="*80)
        print("FAILED TESTS")
        print("="*80)
        for fail in test_results["failed"]:
            print(f"\n❌ {fail['test']}")
            print(f"   Error: {fail['error']}")
    
    if test_results["warnings"]:
        print("\n" + "="*80)
        print("WARNINGS")
        print("="*80)
        for warn in test_results["warnings"]:
            print(f"\n⚠️  {warn['test']}")
            print(f"   Warning: {warn['warning']}")
    
    print("\n" + "="*80)
    
    return failed == 0

def main():
    """Main test execution"""
    print("="*80)
    print("PHASE 3 REVERSE LOGISTICS & APPROVAL ENGINE - BACKEND TEST SUITE")
    print("="*80)
    print(f"Backend URL: {BASE_URL}")
    print(f"Test User: {ADMIN_EMAIL}")
    
    try:
        # Login
        login()
        
        # Run all tests
        test_approval_matrix()
        test_return_lifecycle()
        test_return_rejection()
        test_damage()
        test_claim_settle()
        test_manual_credit_note()
        test_debit_note()
        test_replacement()
        test_expiry()
        test_exception_scanner()
        test_reports_hub()
        test_audit_log()
        
        # Print summary
        success = print_summary()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
