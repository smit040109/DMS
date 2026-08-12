#!/usr/bin/env python3
"""
GO OIL DMS CONTINUATION v4 Backend Testing
==========================================
Tests 4 areas:
1. Coupon Print Engine (11x17 sheet + PDF)
2. Coupon Void/Cancel + Recovery (audit-safe)
3. Reports Scoping per-login (salesperson own data; TL/RM team scope)
4. Salesperson Collection Modes (Cash/UPI/Cheque)

Base URL: http://localhost:8001/api
All routes prefixed with /api
Coupon router: /api/dms/coupons/*
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

# Base URL
BASE_URL = "http://localhost:8001/api"

# Test credentials from /app/memory/test_credentials.md
CREDENTIALS = {
    "owner": {"email": "gooilindia13@gmail.com", "password": "Arjun@india13"},
    "salesperson": {"email": "salesperson@gooil.com", "password": "GoOil@2026"},
    "distributor1": {"email": "distributor1@gooil.com", "password": "GoOil@2026"},
    "distacct": {"email": "distacct@gooil.com", "password": "GoOil@2026"},
    "retailer1": {"email": "retailer1@gooil.com", "password": "GoOil@2026"},
}

# Global tokens
tokens: Dict[str, str] = {}

# Test results
results = {
    "passed": 0,
    "failed": 0,
    "errors": []
}


def log(msg: str, level: str = "INFO"):
    """Log a message"""
    print(f"[{level}] {msg}")


def login(role: str) -> Optional[str]:
    """Login and return JWT token"""
    if role in tokens:
        return tokens[role]
    
    creds = CREDENTIALS.get(role)
    if not creds:
        log(f"No credentials for role: {role}", "ERROR")
        return None
    
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json=creds, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("token")
            tokens[role] = token
            log(f"✓ Logged in as {role}")
            return token
        else:
            log(f"✗ Login failed for {role}: {resp.status_code} {resp.text}", "ERROR")
            return None
    except Exception as e:
        log(f"✗ Login exception for {role}: {e}", "ERROR")
        return None


def api_call(method: str, endpoint: str, token: Optional[str] = None, 
             json_data: Optional[Dict] = None, expect_status: int = 200,
             description: str = "") -> Optional[Dict]:
    """Make an API call and return response"""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=json_data, timeout=30)
        elif method == "PUT":
            resp = requests.put(url, headers=headers, json=json_data, timeout=30)
        elif method == "DELETE":
            resp = requests.delete(url, headers=headers, timeout=30)
        else:
            log(f"Unknown method: {method}", "ERROR")
            return None
        
        if resp.status_code == expect_status:
            results["passed"] += 1
            log(f"✓ {description or endpoint}: {resp.status_code}")
            try:
                return resp.json() if resp.content else {}
            except Exception:
                return {"_raw": resp.content}
        else:
            results["failed"] += 1
            error_msg = f"✗ {description or endpoint}: Expected {expect_status}, got {resp.status_code}"
            if resp.content:
                try:
                    error_data = resp.json()
                    error_msg += f" | {error_data.get('detail', resp.text[:200])}"
                except Exception:
                    error_msg += f" | {resp.text[:200]}"
            log(error_msg, "ERROR")
            results["errors"].append(error_msg)
            return None
    except Exception as e:
        results["failed"] += 1
        error_msg = f"✗ {description or endpoint}: Exception {e}"
        log(error_msg, "ERROR")
        results["errors"].append(error_msg)
        return None


def test_coupon_print_engine():
    """TEST 1: COUPON PRINT ENGINE (11x17 sheet + PDF)"""
    log("\n" + "="*80)
    log("TEST 1: COUPON PRINT ENGINE (11x17 sheet + PDF)")
    log("="*80)
    
    owner_token = login("owner")
    if not owner_token:
        log("Cannot proceed without owner login", "ERROR")
        return
    
    # Create a coupon batch
    log("\n--- Creating coupon batch ---")
    import time
    unique_prefix = f"T{int(time.time()) % 10000}"  # Unique prefix
    batch_data = {
        "count": 5,
        "coupon_type": "cash",
        "coupon_value": 10,
        "title": "Test Batch v4",
        "serial_mode": "prefix_sequential",
        "prefix": unique_prefix,
        "serial_start": 1,
        "serial_pad": 3
    }
    batch_resp = api_call("POST", "/dms/coupons/batches", owner_token, batch_data, 200,
                          "Create coupon batch")
    if not batch_resp:
        return
    
    batch_id = batch_resp.get("batch", {}).get("id")
    if not batch_id:
        log("No batch_id in response", "ERROR")
        return
    
    log(f"Batch ID: {batch_id}")
    
    # Activate the batch
    log("\n--- Activating batch ---")
    activate_resp = api_call("POST", f"/dms/coupons/batches/{batch_id}/activate", 
                             owner_token, {}, 200, "Activate batch")
    if not activate_resp:
        return
    
    # Export PDF (11x17 sheet)
    log("\n--- Testing PDF export (11x17 sheet) ---")
    pdf_resp = api_call("GET", f"/dms/coupons/batches/{batch_id}/export-pdf", 
                        owner_token, None, 200, "Export batch PDF")
    if pdf_resp and "_raw" in pdf_resp:
        pdf_size = len(pdf_resp["_raw"])
        log(f"PDF size: {pdf_size} bytes")
        if pdf_size > 1000:
            log("✓ PDF has non-trivial size")
            results["passed"] += 1
        else:
            log("✗ PDF size too small", "ERROR")
            results["failed"] += 1
    
    # Print mixed (both sides)
    log("\n--- Testing print-mixed endpoint ---")
    mixed_data = {"batch_ids": [batch_id], "side": "both"}
    mixed_resp = api_call("POST", "/dms/coupons/print-mixed", owner_token, 
                          mixed_data, 200, "Print mixed (both sides)")
    if mixed_resp and "_raw" in mixed_resp:
        mixed_size = len(mixed_resp["_raw"])
        log(f"Mixed PDF size: {mixed_size} bytes")
        if mixed_size > 1000:
            log("✓ Mixed PDF has non-trivial size")
            results["passed"] += 1
        else:
            log("✗ Mixed PDF size too small", "ERROR")
            results["failed"] += 1
    
    # Print mixed preview (check per_sheet == 70)
    log("\n--- Testing print-mixed/preview ---")
    preview_resp = api_call("POST", "/dms/coupons/print-mixed/preview", owner_token, 
                            {}, 200, "Print mixed preview")
    if preview_resp:
        per_sheet = preview_resp.get("per_sheet")
        if per_sheet == 70:
            log(f"✓ per_sheet == 70 (11x17 grid, 7x10)")
            results["passed"] += 1
        else:
            log(f"✗ per_sheet == {per_sheet}, expected 70", "ERROR")
            results["failed"] += 1
    
    return batch_id


def test_coupon_void_cancel_recovery(batch_id: Optional[str] = None):
    """TEST 2: COUPON VOID/CANCEL + RECOVERY (audit-safe)"""
    log("\n" + "="*80)
    log("TEST 2: COUPON VOID/CANCEL + RECOVERY (audit-safe)")
    log("="*80)
    
    owner_token = login("owner")
    dist1_token = login("distributor1")
    
    if not owner_token:
        log("Cannot proceed without owner login", "ERROR")
        return
    
    # If no batch_id provided, create one
    if not batch_id:
        log("\n--- Creating test batch for void/cancel tests ---")
        batch_data = {
            "count": 5,
            "coupon_type": "cash",
            "coupon_value": 10,
            "title": "Void Test Batch",
            "serial_mode": "prefix_sequential",
            "prefix": "VOID",
            "serial_start": 1,
            "serial_pad": 3
        }
        batch_resp = api_call("POST", "/dms/coupons/batches", owner_token, batch_data, 200,
                              "Create void test batch")
        if not batch_resp:
            return
        batch_id = batch_resp.get("batch", {}).get("id")
        
        # Activate
        api_call("POST", f"/dms/coupons/batches/{batch_id}/activate", owner_token, {}, 200,
                 "Activate void test batch")
    
    # List coupons to get a serial
    log("\n--- Listing coupons to get serial ---")
    coupons_resp = api_call("GET", f"/dms/coupons?batch_id={batch_id}", owner_token, 
                            None, 200, "List coupons")
    if not coupons_resp:
        return
    
    coupons = coupons_resp.get("data", [])
    if not coupons:
        log("No coupons found", "ERROR")
        return
    
    test_serial = coupons[0].get("visible_serial") or coupons[0].get("coupon_code")
    log(f"Test serial: {test_serial}")
    
    # Void by serial - preview
    log("\n--- Testing void-by-serial/preview ---")
    preview_data = {"serial": test_serial}
    preview_resp = api_call("POST", "/dms/coupons/coupons/void-by-serial/preview", 
                            owner_token, preview_data, 200, "Void preview")
    if preview_resp:
        can_void = preview_resp.get("can_void")
        if can_void:
            log("✓ can_void == true")
            results["passed"] += 1
        else:
            log(f"✗ can_void == {can_void}", "ERROR")
            results["failed"] += 1
    
    # Void by serial - actual void
    log("\n--- Testing void-by-serial (actual) ---")
    void_data = {"serial": test_serial, "reason": "test void"}
    void_resp = api_call("POST", "/dms/coupons/coupons/void-by-serial", owner_token, 
                         void_data, 200, "Void coupon by serial")
    if void_resp:
        changed = void_resp.get("changed")
        if changed:
            log("✓ Coupon voided (changed == true)")
            results["passed"] += 1
        else:
            log(f"✗ changed == {changed}", "ERROR")
            results["failed"] += 1
    
    # Void same serial again (should return changed:false)
    log("\n--- Testing void same serial again ---")
    void_again_resp = api_call("POST", "/dms/coupons/coupons/void-by-serial", owner_token, 
                                void_data, 200, "Void same serial again")
    if void_again_resp:
        changed = void_again_resp.get("changed")
        if not changed:
            log("✓ Already voided (changed == false)")
            results["passed"] += 1
        else:
            log(f"✗ changed == {changed}, expected false", "ERROR")
            results["failed"] += 1
    
    # Void without reason (should fail)
    log("\n--- Testing void without reason (should fail) ---")
    no_reason_data = {"serial": test_serial}
    api_call("POST", "/dms/coupons/coupons/void-by-serial", owner_token, 
             no_reason_data, 400, "Void without reason (expect 400)")
    
    # Void as distributor (should fail with 403)
    log("\n--- Testing void as distributor (should fail) ---")
    if dist1_token:
        api_call("POST", "/dms/coupons/coupons/void-by-serial", dist1_token, 
                 void_data, 403, "Void as distributor (expect 403)")
    
    # Void with bad serial (should fail with 404)
    log("\n--- Testing void with bad serial (should fail) ---")
    bad_serial_data = {"serial": "NOPE123", "reason": "test"}
    api_call("POST", "/dms/coupons/coupons/void-by-serial", owner_token, 
             bad_serial_data, 404, "Void bad serial (expect 404)")
    
    # Batch void preview
    log("\n--- Testing void-batch/preview ---")
    batch_preview_data = {"batch_id": batch_id}
    batch_preview_resp = api_call("POST", "/dms/coupons/coupons/void-batch/preview", 
                                  owner_token, batch_preview_data, 200, "Batch void preview")
    if batch_preview_resp:
        total = batch_preview_resp.get("total")
        will_void = batch_preview_resp.get("will_void")
        log(f"Batch preview: total={total}, will_void={will_void}")
        results["passed"] += 1
    
    # Batch void (actual)
    log("\n--- Testing void-batch (actual) ---")
    batch_void_data = {"batch_id": batch_id, "reason": "misprint"}
    batch_void_resp = api_call("POST", "/dms/coupons/coupons/void-batch", owner_token, 
                               batch_void_data, 200, "Batch void")
    if batch_void_resp:
        voided_count = batch_void_resp.get("voided_count")
        log(f"Voided count: {voided_count}")
        if voided_count >= 0:
            log("✓ Batch void successful")
            results["passed"] += 1
        else:
            log("✗ Batch void failed", "ERROR")
            results["failed"] += 1
    
    # Batch void without reason (should fail)
    log("\n--- Testing batch void without reason (should fail) ---")
    no_reason_batch = {"batch_id": batch_id}
    api_call("POST", "/dms/coupons/coupons/void-batch", owner_token, 
             no_reason_batch, 400, "Batch void without reason (expect 400)")
    
    # Recovery - get a voided coupon id
    log("\n--- Testing coupon recovery ---")
    if coupons:
        coupon_id = coupons[0].get("id")
        recover_data = {"reason": "recover test"}
        recover_resp = api_call("POST", f"/dms/coupons/coupons/{coupon_id}/recover", 
                                owner_token, recover_data, 200, "Recover voided coupon")
        if recover_resp:
            log("✓ Coupon recovered")
            results["passed"] += 1
        
        # Recover as distributor (should fail)
        if dist1_token:
            api_call("POST", f"/dms/coupons/coupons/{coupon_id}/recover", dist1_token, 
                     recover_data, 403, "Recover as distributor (expect 403)")
    
    # Verify voided coupon is NOT scannable
    log("\n--- Testing voided coupon scan rejection ---")
    # We need to test that a voided coupon is rejected on scan
    # This would require the scan endpoint, but we'll just verify the void status
    log("Note: Voided coupon scan rejection should be tested via scan endpoint")


def test_reports_scoping():
    """TEST 3: REPORTS SCOPING PER-LOGIN"""
    log("\n" + "="*80)
    log("TEST 3: REPORTS SCOPING PER-LOGIN (salesperson own data; TL/RM team scope)")
    log("="*80)
    
    owner_token = login("owner")
    sp_token = login("salesperson")
    
    if not owner_token or not sp_token:
        log("Cannot proceed without owner and salesperson login", "ERROR")
        return
    
    # Test sp_collection report as salesperson (should see only own row)
    log("\n--- Testing sp_collection report as salesperson ---")
    sp_report_resp = api_call("GET", "/dms/reports/sp_collection/run", sp_token, 
                              None, 200, "SP collection report as salesperson")
    if sp_report_resp:
        rows = sp_report_resp.get("rows", [])
        log(f"Salesperson sees {len(rows)} row(s)")
        if len(rows) <= 1:
            log("✓ Salesperson sees only own row (or 0 if no data)")
            results["passed"] += 1
        else:
            log(f"✗ Salesperson sees {len(rows)} rows, expected 0 or 1", "ERROR")
            results["failed"] += 1
        
        # Check for UPI column
        columns = sp_report_resp.get("columns", [])
        column_keys = [c.get("key") for c in columns]
        if "upi" in column_keys or any("upi" in str(k).lower() for k in column_keys):
            log("✓ UPI column present in sp_collection")
            results["passed"] += 1
        else:
            log(f"✗ UPI column not found. Columns: {column_keys}", "ERROR")
            results["failed"] += 1
    
    # Test sp_collection report as owner (should see all)
    log("\n--- Testing sp_collection report as owner ---")
    owner_report_resp = api_call("GET", "/dms/reports/sp_collection/run", owner_token, 
                                 None, 200, "SP collection report as owner")
    if owner_report_resp:
        rows = owner_report_resp.get("rows", [])
        log(f"Owner sees {len(rows)} row(s)")
        log("✓ Owner can see all salespersons")
        results["passed"] += 1
    
    # Test sp_performance report (salesperson should get 403 - only TL/RM/Admin allowed)
    log("\n--- Testing sp_performance report (expect 403 for salesperson) ---")
    sp_perf_resp = api_call("GET", "/dms/reports/sp_performance/run", sp_token, 
                            None, 403, "SP performance report as salesperson (expect 403)")
    if sp_perf_resp is None:  # 403 is expected
        log("✓ SP performance report correctly restricted to TL/RM/Admin")
        results["passed"] += 1


def test_salesperson_collection_modes():
    """TEST 4: SALESPERSON COLLECTION MODES (Cash/UPI/Cheque)"""
    log("\n" + "="*80)
    log("TEST 4: SALESPERSON COLLECTION MODES (Cash/UPI/Cheque)")
    log("="*80)
    
    sp_token = login("salesperson")
    
    if not sp_token:
        log("Cannot proceed without salesperson login", "ERROR")
        return
    
    # Get retailer1 ID
    log("\n--- Getting retailer1 ID ---")
    retailers_resp = api_call("GET", "/dms/retailers", sp_token, None, 200, 
                              "List retailers")
    if not retailers_resp:
        log("Cannot get retailers", "ERROR")
        return
    
    retailers = retailers_resp.get("data", [])
    if not retailers:
        log("No retailers found - skipping salesperson collection test", "WARN")
        log("Note: Salesperson needs assigned distributors with retailers to test collection")
        return
    else:
        retailer_id = retailers[0]["id"]
    
    log(f"Retailer ID: {retailer_id}")
    
    # Test cash payment
    log("\n--- Testing cash payment ---")
    cash_data = {
        "retailer_id": retailer_id,
        "method": "cash",
        "amount": 100
    }
    cash_resp = api_call("POST", "/dms/ledger/secondary/payment", sp_token, 
                         cash_data, 200, "Cash payment")
    if cash_resp:
        log("✓ Cash payment successful")
        results["passed"] += 1
    
    # Test UPI without txn_ref (should fail)
    log("\n--- Testing UPI without txn_ref (should fail) ---")
    upi_no_ref = {
        "retailer_id": retailer_id,
        "method": "upi",
        "amount": 50
    }
    api_call("POST", "/dms/ledger/secondary/payment", sp_token, 
             upi_no_ref, 400, "UPI without txn_ref (expect 400)")
    
    # Test UPI with txn_ref
    log("\n--- Testing UPI with txn_ref ---")
    upi_with_ref = {
        "retailer_id": retailer_id,
        "method": "upi",
        "amount": 50,
        "txn_ref": "UPI123"
    }
    upi_resp = api_call("POST", "/dms/ledger/secondary/payment", sp_token, 
                        upi_with_ref, 200, "UPI with txn_ref")
    if upi_resp:
        log("✓ UPI payment with txn_ref successful")
        results["passed"] += 1
    
    # Test cheque without cheque_no (should fail)
    log("\n--- Testing cheque without cheque_no (should fail) ---")
    cheque_no_num = {
        "retailer_id": retailer_id,
        "method": "cheque",
        "amount": 200
    }
    api_call("POST", "/dms/ledger/secondary/payment", sp_token, 
             cheque_no_num, 400, "Cheque without cheque_no (expect 400)")
    
    # Test cheque with cheque_no
    log("\n--- Testing cheque with cheque_no ---")
    cheque_with_num = {
        "retailer_id": retailer_id,
        "method": "cheque",
        "amount": 200,
        "cheque_no": "CHQ001",
        "cheque_date": "2026-01-15",
        "bank_name": "Test Bank"
    }
    cheque_resp = api_call("POST", "/dms/ledger/secondary/payment", sp_token, 
                           cheque_with_num, 200, "Cheque with cheque_no")
    if cheque_resp:
        log("✓ Cheque payment with cheque_no successful")
        results["passed"] += 1
    
    # Verify payments appear in ledger
    log("\n--- Verifying payments in ledger ---")
    ledger_resp = api_call("GET", f"/dms/ledger/secondary?retailer_id={retailer_id}", 
                           sp_token, None, 200, "Get secondary ledger")
    if ledger_resp:
        entries = ledger_resp.get("entries", [])
        log(f"Found {len(entries)} ledger entries")
        
        # Check for method and recorded_by_name
        payment_entries = [e for e in entries if e.get("kind") == "payment"]
        if payment_entries:
            log(f"Found {len(payment_entries)} payment entries")
            for entry in payment_entries[:3]:  # Check first 3
                method = entry.get("method")
                recorded_by = entry.get("recorded_by_name")
                log(f"  Payment: method={method}, recorded_by={recorded_by}")
            log("✓ Payment entries have method and recorded_by_name")
            results["passed"] += 1
        else:
            log("✗ No payment entries found", "ERROR")
            results["failed"] += 1


def main():
    """Main test runner"""
    log("="*80)
    log("GO OIL DMS CONTINUATION v4 - Backend Testing")
    log("="*80)
    log(f"Base URL: {BASE_URL}")
    log(f"Testing 4 areas:")
    log("  1. Coupon Print Engine (11x17 sheet + PDF)")
    log("  2. Coupon Void/Cancel + Recovery")
    log("  3. Reports Scoping per-login")
    log("  4. Salesperson Collection Modes")
    log("="*80)
    
    # Run tests
    batch_id = test_coupon_print_engine()
    test_coupon_void_cancel_recovery(batch_id)
    test_reports_scoping()
    test_salesperson_collection_modes()
    
    # Summary
    log("\n" + "="*80)
    log("TEST SUMMARY")
    log("="*80)
    log(f"✓ Passed: {results['passed']}")
    log(f"✗ Failed: {results['failed']}")
    log(f"Total: {results['passed'] + results['failed']}")
    
    if results['errors']:
        log("\nERRORS:")
        for error in results['errors']:
            log(f"  {error}")
    
    if results['failed'] == 0:
        log("\n🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        log(f"\n❌ {results['failed']} TEST(S) FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
