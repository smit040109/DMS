#!/usr/bin/env python3
"""
GO OIL Coupon Engine — Comprehensive Backend Test Suite
========================================================
Tests all 10 sections from the review request:
1. Batch generation (Owner only)
2. Batch lifecycle
3. Coupon listing
4. Sales Officer flow
5. Scan flow (critical)
6. Retailer wallet (view-only)
7. Redemption flow
8. RBAC (403 tests)
9. Reports
10. Immutable wallet derivation
"""
import requests
import json
import sys
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "http://localhost:8001/api"
PASSWORD = "GoOil@2026"

# Test credentials
CREDENTIALS = {
    "owner": "owner@gooil.com",
    "accountant": "accountant@gooil.com",
    "tl": "teamleader@gooil.com",
    "salesperson": "salesperson@gooil.com",
    "distributor1": "distributor1@gooil.com",
    "retailer1": "retailer1@gooil.com",
    "retailer2": "retailer2@gooil.com",
}

# Global state
tokens: Dict[str, str] = {}
test_data: Dict[str, Any] = {}
results = {
    "passed": 0,
    "failed": 0,
    "sections": {}
}


def log(msg: str, level: str = "INFO"):
    """Log test messages."""
    prefix = {
        "INFO": "ℹ️ ",
        "PASS": "✅",
        "FAIL": "❌",
        "WARN": "⚠️ ",
    }.get(level, "  ")
    print(f"{prefix} {msg}")


def login(role: str) -> str:
    """Login and return JWT token."""
    email = CREDENTIALS[role]
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": PASSWORD},
        timeout=10
    )
    if resp.status_code != 200:
        log(f"Login failed for {role}: {resp.status_code} {resp.text}", "FAIL")
        sys.exit(1)
    token = resp.json()["token"]
    tokens[role] = token
    log(f"Logged in as {role} ({email})")
    return token


def api_call(
    method: str,
    endpoint: str,
    token: Optional[str] = None,
    json_data: Optional[Dict] = None,
    params: Optional[Dict] = None,
    expect_status: int = 200,
    expect_binary: bool = False,
) -> Any:
    """Make API call and return response."""
    url = f"{BASE_URL}{endpoint}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, params=params, timeout=30)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=json_data, timeout=30)
        elif method == "PUT":
            resp = requests.put(url, headers=headers, json=json_data, timeout=30)
        elif method == "DELETE":
            resp = requests.delete(url, headers=headers, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        if resp.status_code != expect_status:
            log(f"{method} {endpoint} → {resp.status_code} (expected {expect_status})", "FAIL")
            log(f"Response: {resp.text[:500]}", "FAIL")
            return None
        
        if expect_binary:
            return resp
        
        if resp.status_code == 204:
            return {}
        
        return resp.json()
    except Exception as e:
        log(f"{method} {endpoint} → Exception: {e}", "FAIL")
        return None


def assert_true(condition: bool, message: str, section: str):
    """Assert condition and track results."""
    if condition:
        log(f"{message}", "PASS")
        results["passed"] += 1
        if section not in results["sections"]:
            results["sections"][section] = {"passed": 0, "failed": 0}
        results["sections"][section]["passed"] += 1
    else:
        log(f"{message}", "FAIL")
        results["failed"] += 1
        if section not in results["sections"]:
            results["sections"][section] = {"passed": 0, "failed": 0}
        results["sections"][section]["failed"] += 1


def test_section_1_batch_generation():
    """Section 1: Batch generation (Owner only)"""
    section = "1. Batch Generation"
    log(f"\n{'='*60}\n{section}\n{'='*60}")
    
    owner_token = tokens["owner"]
    retailer_token = tokens["retailer1"]
    
    # Test 1a: Create CASH batch
    log("Test 1a: Create CASH batch (20 coupons, ₹20 each)")
    cash_batch = api_call(
        "POST", "/dms/coupons/batches",
        token=owner_token,
        json_data={
            "coupon_type": "cash",
            "coupon_value": 20,
            "count": 20,
            "title": "Test Cash 1"
        }
    )
    assert_true(
        cash_batch and cash_batch.get("ok") is True,
        "Cash batch created successfully",
        section
    )
    assert_true(
        cash_batch and "GO-C-" in cash_batch.get("batch", {}).get("batch_label", ""),
        "Cash batch label matches GO-C-##### pattern",
        section
    )
    assert_true(
        cash_batch and cash_batch.get("batch", {}).get("status") == "generated",
        "Cash batch status is 'generated'",
        section
    )
    assert_true(
        cash_batch and cash_batch.get("batch", {}).get("active") is False,
        "Cash batch active is False",
        section
    )
    if cash_batch:
        test_data["cash_batch_id"] = cash_batch["batch"]["id"]
        test_data["cash_batch_label"] = cash_batch["batch"]["batch_label"]
    
    # Test 1b: Create REWARD batch
    log("Test 1b: Create REWARD batch (15 coupons, 50 points each)")
    reward_batch = api_call(
        "POST", "/dms/coupons/batches",
        token=owner_token,
        json_data={
            "coupon_type": "reward",
            "coupon_value": 50,
            "count": 15,
            "title": "Test Reward 1"
        }
    )
    assert_true(
        reward_batch and reward_batch.get("ok") is True,
        "Reward batch created successfully",
        section
    )
    assert_true(
        reward_batch and "GO-R-" in reward_batch.get("batch", {}).get("batch_label", ""),
        "Reward batch label matches GO-R-##### pattern",
        section
    )
    if reward_batch:
        test_data["reward_batch_id"] = reward_batch["batch"]["id"]
        test_data["reward_batch_label"] = reward_batch["batch"]["batch_label"]
    
    # Test 1c: Non-owner (retailer) POST → 403
    log("Test 1c: Non-owner (retailer) tries to create batch → 403")
    retailer_batch = api_call(
        "POST", "/dms/coupons/batches",
        token=retailer_token,
        json_data={
            "coupon_type": "cash",
            "coupon_value": 10,
            "count": 5,
            "title": "Unauthorized"
        },
        expect_status=403
    )
    assert_true(
        retailer_batch is None or retailer_batch == {},
        "Retailer cannot create batch (403)",
        section
    )
    
    # Test 1d: Invalid body - count=0 → 400
    log("Test 1d: Invalid body - count=0 → 400")
    invalid_count = api_call(
        "POST", "/dms/coupons/batches",
        token=owner_token,
        json_data={
            "coupon_type": "cash",
            "coupon_value": 10,
            "count": 0,
            "title": "Invalid Count"
        },
        expect_status=400
    )
    assert_true(
        invalid_count is None or invalid_count == {},
        "count=0 returns 400",
        section
    )
    
    # Test 1e: Invalid body - count > 100000 → 400
    log("Test 1e: Invalid body - count > 100000 → 400")
    invalid_large = api_call(
        "POST", "/dms/coupons/batches",
        token=owner_token,
        json_data={
            "coupon_type": "cash",
            "coupon_value": 10,
            "count": 100001,
            "title": "Too Large"
        },
        expect_status=400
    )
    assert_true(
        invalid_large is None or invalid_large == {},
        "count > 100000 returns 400",
        section
    )
    
    # Test 1f: Invalid body - coupon_type="xyz" → 400
    log("Test 1f: Invalid body - coupon_type='xyz' → 400")
    invalid_type = api_call(
        "POST", "/dms/coupons/batches",
        token=owner_token,
        json_data={
            "coupon_type": "xyz",
            "coupon_value": 10,
            "count": 5,
            "title": "Invalid Type"
        },
        expect_status=400
    )
    assert_true(
        invalid_type is None or invalid_type == {},
        "coupon_type='xyz' returns 400",
        section
    )


def test_section_2_batch_lifecycle():
    """Section 2: Batch lifecycle"""
    section = "2. Batch Lifecycle"
    log(f"\n{'='*60}\n{section}\n{'='*60}")
    
    owner_token = tokens["owner"]
    retailer_token = tokens["retailer1"]
    cash_batch_id = test_data.get("cash_batch_id")
    
    if not cash_batch_id:
        log("Skipping section 2: No cash_batch_id from section 1", "WARN")
        return
    
    # Test 2a: GET /batches → both batches listed
    log("Test 2a: GET /batches → both batches listed")
    batches_list = api_call("GET", "/dms/coupons/batches", token=owner_token)
    assert_true(
        batches_list and len(batches_list.get("data", [])) >= 2,
        f"GET /batches returns at least 2 batches (got {len(batches_list.get('data', []))})",
        section
    )
    
    # Test 2b: GET /batches/{bid} → returns batch with counts_by_status, total_value
    log(f"Test 2b: GET /batches/{cash_batch_id} → returns batch detail")
    batch_detail = api_call("GET", f"/dms/coupons/batches/{cash_batch_id}", token=owner_token)
    assert_true(
        batch_detail and "counts_by_status" in batch_detail,
        "Batch detail includes counts_by_status",
        section
    )
    assert_true(
        batch_detail and "total_value" in batch_detail,
        "Batch detail includes total_value",
        section
    )
    assert_true(
        batch_detail and "hmac_secret" not in batch_detail,
        "Batch detail does NOT include hmac_secret (security)",
        section
    )
    
    # Test 2c: POST /batches/{bid}/activate → status→"activated", active=true
    log(f"Test 2c: POST /batches/{cash_batch_id}/activate")
    activate_resp = api_call("POST", f"/dms/coupons/batches/{cash_batch_id}/activate", token=owner_token)
    assert_true(
        activate_resp and activate_resp.get("ok") is True,
        "Batch activated successfully",
        section
    )
    
    # Verify activation
    batch_after_activate = api_call("GET", f"/dms/coupons/batches/{cash_batch_id}", token=owner_token)
    assert_true(
        batch_after_activate and batch_after_activate.get("status") == "activated",
        "Batch status is 'activated'",
        section
    )
    assert_true(
        batch_after_activate and batch_after_activate.get("active") is True,
        "Batch active is True",
        section
    )
    
    # Test 2d: Second activate call → 400
    log("Test 2d: Second activate call → 400")
    second_activate = api_call(
        "POST", f"/dms/coupons/batches/{cash_batch_id}/activate",
        token=owner_token,
        expect_status=400
    )
    assert_true(
        second_activate is None or second_activate == {},
        "Second activate returns 400",
        section
    )
    
    # Test 2e: POST /batches/{bid}/mark-printed → OK
    log(f"Test 2e: POST /batches/{cash_batch_id}/mark-printed")
    mark_printed = api_call("POST", f"/dms/coupons/batches/{cash_batch_id}/mark-printed", token=owner_token)
    assert_true(
        mark_printed and mark_printed.get("ok") is True,
        "Batch marked as printed",
        section
    )
    
    # Test 2f: POST /batches/{bid}/issue-to-production → OK
    log(f"Test 2f: POST /batches/{cash_batch_id}/issue-to-production")
    issue_prod = api_call("POST", f"/dms/coupons/batches/{cash_batch_id}/issue-to-production", token=owner_token)
    assert_true(
        issue_prod and issue_prod.get("ok") is True,
        "Batch issued to production",
        section
    )
    
    # Test 2g: GET /batches/{bid}/export-pdf → 200, Content-Type application/pdf
    log(f"Test 2g: GET /batches/{cash_batch_id}/export-pdf")
    pdf_resp = api_call(
        "GET", f"/dms/coupons/batches/{cash_batch_id}/export-pdf",
        token=owner_token,
        expect_binary=True
    )
    assert_true(
        pdf_resp and pdf_resp.status_code == 200,
        "PDF export returns 200",
        section
    )
    assert_true(
        pdf_resp and "application/pdf" in pdf_resp.headers.get("Content-Type", ""),
        "PDF export has Content-Type application/pdf",
        section
    )
    assert_true(
        pdf_resp and pdf_resp.content[:4] == b"%PDF",
        "PDF export body starts with %PDF",
        section
    )
    
    # Test 2h: GET /batches/{bid}/export-xlsx → 200, xlsx MIME
    log(f"Test 2h: GET /batches/{cash_batch_id}/export-xlsx")
    xlsx_resp = api_call(
        "GET", f"/dms/coupons/batches/{cash_batch_id}/export-xlsx",
        token=owner_token,
        expect_binary=True
    )
    assert_true(
        xlsx_resp and xlsx_resp.status_code == 200,
        "XLSX export returns 200",
        section
    )
    assert_true(
        xlsx_resp and "spreadsheetml" in xlsx_resp.headers.get("Content-Type", ""),
        "XLSX export has xlsx MIME type",
        section
    )
    assert_true(
        xlsx_resp and xlsx_resp.content[:2] == b"PK",
        "XLSX export body starts with PK (zip magic)",
        section
    )
    
    # Test 2i: Non-owner accessing activate/export → 403
    log("Test 2i: Non-owner (retailer) accessing activate → 403")
    retailer_activate = api_call(
        "POST", f"/dms/coupons/batches/{cash_batch_id}/activate",
        token=retailer_token,
        expect_status=403
    )
    assert_true(
        retailer_activate is None or retailer_activate == {},
        "Retailer cannot activate batch (403)",
        section
    )
    
    log("Test 2j: Non-owner (retailer) accessing export-pdf → 403")
    retailer_pdf = api_call(
        "GET", f"/dms/coupons/batches/{cash_batch_id}/export-pdf",
        token=retailer_token,
        expect_status=403,
        expect_binary=True
    )
    assert_true(
        retailer_pdf is None or retailer_pdf.status_code == 403,
        "Retailer cannot export PDF (403)",
        section
    )


def test_section_3_coupon_listing():
    """Section 3: Coupon listing"""
    section = "3. Coupon Listing"
    log(f"\n{'='*60}\n{section}\n{'='*60}")
    
    owner_token = tokens["owner"]
    retailer_token = tokens["retailer1"]
    cash_batch_id = test_data.get("cash_batch_id")
    
    if not cash_batch_id:
        log("Skipping section 3: No cash_batch_id", "WARN")
        return
    
    # Test 3a: GET /coupons?batch_id={bid} → returns list of coupons
    log(f"Test 3a: GET /coupons?batch_id={cash_batch_id}")
    coupons_list = api_call("GET", "/dms/coupons", token=owner_token, params={"batch_id": cash_batch_id})
    assert_true(
        coupons_list and len(coupons_list.get("data", [])) > 0,
        f"GET /coupons returns coupons (got {len(coupons_list.get('data', []))})",
        section
    )
    
    # Verify secret_token & signature NOT included
    if coupons_list and coupons_list.get("data"):
        first_coupon = coupons_list["data"][0]
        assert_true(
            "secret_token" not in first_coupon,
            "Coupon list does NOT include secret_token (security)",
            section
        )
        assert_true(
            "signature" not in first_coupon,
            "Coupon list does NOT include signature (security)",
            section
        )
        # Save a coupon code for scan tests
        test_data["cash_coupon_code"] = first_coupon.get("coupon_code")
        test_data["cash_coupon_id"] = first_coupon.get("id")
    
    # Test 3b: GET /coupons?status=unused&coupon_type=cash → filters correctly
    log("Test 3b: GET /coupons?status=unused&coupon_type=cash")
    filtered_coupons = api_call(
        "GET", "/dms/coupons",
        token=owner_token,
        params={"status": "unused", "coupon_type": "cash"}
    )
    assert_true(
        filtered_coupons and len(filtered_coupons.get("data", [])) > 0,
        "Filtered coupons returns results",
        section
    )
    if filtered_coupons and filtered_coupons.get("data"):
        all_unused_cash = all(
            c.get("status") == "unused" and c.get("coupon_type") == "cash"
            for c in filtered_coupons["data"]
        )
        assert_true(
            all_unused_cash,
            "All filtered coupons are unused cash coupons",
            section
        )
    
    # Test 3c: Retailer accessing /coupons → 403
    log("Test 3c: Retailer accessing /coupons → 403")
    retailer_coupons = api_call(
        "GET", "/dms/coupons",
        token=retailer_token,
        expect_status=403
    )
    assert_true(
        retailer_coupons is None or retailer_coupons == {},
        "Retailer cannot access /coupons (403)",
        section
    )


def test_section_4_sales_officer_flow():
    """Section 4: Sales Officer flow"""
    section = "4. Sales Officer Flow"
    log(f"\n{'='*60}\n{section}\n{'='*60}")
    
    sp_token = tokens["salesperson"]
    
    # Test 4a: GET /so/retailers → returns retailers
    log("Test 4a: GET /so/retailers")
    retailers = api_call("GET", "/dms/coupons/so/retailers", token=sp_token)
    assert_true(
        retailers and len(retailers.get("data", [])) > 0,
        f"GET /so/retailers returns retailers (got {len(retailers.get('data', []))})",
        section
    )
    
    if retailers and retailers.get("data"):
        test_data["sp_retailer_id"] = retailers["data"][0]["id"]
        test_data["sp_retailer_name"] = retailers["data"][0].get("name", "Unknown")
        log(f"   Saved retailer: {test_data['sp_retailer_name']} ({test_data['sp_retailer_id']})")
    
    # Test 4b: Salesperson calling /batches (POST) → 403
    log("Test 4b: Salesperson calling /batches (POST) → 403")
    sp_batch = api_call(
        "POST", "/dms/coupons/batches",
        token=sp_token,
        json_data={
            "coupon_type": "cash",
            "coupon_value": 10,
            "count": 5,
            "title": "Unauthorized"
        },
        expect_status=403
    )
    assert_true(
        sp_batch is None or sp_batch == {},
        "Salesperson cannot create batch (403)",
        section
    )


def test_section_5_scan_flow():
    """Section 5: Scan flow (critical)"""
    section = "5. Scan Flow (CRITICAL)"
    log(f"\n{'='*60}\n{section}\n{'='*60}")
    
    sp_token = tokens["salesperson"]
    owner_token = tokens["owner"]
    retailer_token = tokens["retailer1"]
    
    retailer_id = test_data.get("sp_retailer_id")
    coupon_code = test_data.get("cash_coupon_code")
    coupon_id = test_data.get("cash_coupon_id")
    
    if not retailer_id or not coupon_code:
        log("Skipping section 5: Missing retailer_id or coupon_code", "WARN")
        return
    
    # Test 5a: Valid scan → 200, wallet credited
    log(f"Test 5a: Valid scan - retailer={retailer_id}, coupon={coupon_code}")
    scan_resp = api_call(
        "POST", "/dms/coupons/scan",
        token=sp_token,
        json_data={
            "retailer_id": retailer_id,
            "coupon_code": coupon_code
        }
    )
    assert_true(
        scan_resp and scan_resp.get("ok") is True,
        "Valid scan returns ok=true",
        section
    )
    assert_true(
        scan_resp and scan_resp.get("new_balance", 0) >= 20,
        f"Wallet balance increased (new_balance={scan_resp.get('new_balance', 0)})",
        section
    )
    assert_true(
        scan_resp and scan_resp.get("wallet_type") == "cash",
        "Wallet type is 'cash'",
        section
    )
    assert_true(
        scan_resp and "₹" in scan_resp.get("message", ""),
        "Success message contains ₹",
        section
    )
    
    # Test 5b: Verify coupon status=claimed
    log(f"Test 5b: Verify coupon status=claimed via GET /detail/{coupon_id}")
    coupon_detail = api_call("GET", f"/dms/coupons/detail/{coupon_id}", token=owner_token)
    assert_true(
        coupon_detail and coupon_detail.get("status") == "claimed",
        "Coupon status is 'claimed'",
        section
    )
    assert_true(
        coupon_detail and coupon_detail.get("retailer_id") == retailer_id,
        "Coupon has retailer_id set",
        section
    )
    assert_true(
        coupon_detail and coupon_detail.get("distributor_id") is not None,
        "Coupon has distributor_id set",
        section
    )
    
    # Test 5c: Duplicate scan → 400 with "already claimed"
    log("Test 5c: Duplicate scan of same code → 400")
    duplicate_scan = api_call(
        "POST", "/dms/coupons/scan",
        token=sp_token,
        json_data={
            "retailer_id": retailer_id,
            "coupon_code": coupon_code
        },
        expect_status=400
    )
    assert_true(
        duplicate_scan is None or duplicate_scan == {},
        "Duplicate scan returns 400",
        section
    )
    
    # Verify fraud log
    log("Test 5d: Check fraud log for duplicate scan")
    fraud_log = api_call("GET", "/dms/coupons/reports/fraud", token=owner_token)
    assert_true(
        fraud_log and len(fraud_log.get("data", [])) > 0,
        "Fraud log contains entries",
        section
    )
    if fraud_log and fraud_log.get("data"):
        has_already_claimed = any(
            f.get("reason") == "already_claimed" for f in fraud_log["data"]
        )
        assert_true(
            has_already_claimed,
            "Fraud log contains 'already_claimed' entry",
            section
        )
    
    # Test 5e: Malformed QR → 400
    log("Test 5e: Malformed QR payload → 400")
    malformed_scan = api_call(
        "POST", "/dms/coupons/scan",
        token=sp_token,
        json_data={
            "retailer_id": retailer_id,
            "qr_payload": "garbage"
        },
        expect_status=400
    )
    assert_true(
        malformed_scan is None or malformed_scan == {},
        "Malformed QR returns 400",
        section
    )
    
    # Test 5f: Invalid code → 400
    log("Test 5f: Invalid coupon code → 400")
    invalid_scan = api_call(
        "POST", "/dms/coupons/scan",
        token=sp_token,
        json_data={
            "retailer_id": retailer_id,
            "coupon_code": "AAAA-BBBB-CCCC-DDDD"
        },
        expect_status=400
    )
    assert_true(
        invalid_scan is None or invalid_scan == {},
        "Invalid code returns 400",
        section
    )
    
    # Test 5g: Retailer trying to scan directly → 403
    log("Test 5g: Retailer trying to scan directly → 403")
    retailer_scan = api_call(
        "POST", "/dms/coupons/scan",
        token=retailer_token,
        json_data={
            "retailer_id": retailer_id,
            "coupon_code": "TEST-CODE-1234-5678"
        },
        expect_status=403
    )
    assert_true(
        retailer_scan is None or retailer_scan == {},
        "Retailer cannot scan (403)",
        section
    )
    
    # Test 5h: Scan a REWARD coupon
    reward_batch_id = test_data.get("reward_batch_id")
    if reward_batch_id:
        # First activate the reward batch
        log("Test 5h: Activate reward batch")
        activate_reward = api_call(
            "POST", f"/dms/coupons/batches/{reward_batch_id}/activate",
            token=owner_token
        )
        
        # Get a reward coupon
        reward_coupons = api_call(
            "GET", "/dms/coupons",
            token=owner_token,
            params={"batch_id": reward_batch_id, "status": "unused"}
        )
        
        if reward_coupons and reward_coupons.get("data"):
            reward_code = reward_coupons["data"][0]["coupon_code"]
            log(f"Test 5i: Scan reward coupon {reward_code}")
            reward_scan = api_call(
                "POST", "/dms/coupons/scan",
                token=sp_token,
                json_data={
                    "retailer_id": retailer_id,
                    "coupon_code": reward_code
                }
            )
            assert_true(
                reward_scan and reward_scan.get("ok") is True,
                "Reward coupon scan successful",
                section
            )
            assert_true(
                reward_scan and reward_scan.get("wallet_type") == "reward",
                "Wallet type is 'reward'",
                section
            )
            assert_true(
                reward_scan and reward_scan.get("new_balance", 0) >= 50,
                f"Reward wallet balance increased (new_balance={reward_scan.get('new_balance', 0)})",
                section
            )


def test_section_6_retailer_wallet():
    """Section 6: Retailer wallet (view-only)"""
    section = "6. Retailer Wallet"
    log(f"\n{'='*60}\n{section}\n{'='*60}")
    
    retailer_token = tokens["retailer1"]
    
    # Test 6a: GET /retailer/wallet → returns wallet balances
    log("Test 6a: GET /retailer/wallet")
    wallet = api_call("GET", "/dms/coupons/retailer/wallet", token=retailer_token)
    assert_true(
        wallet and "cash_wallet" in wallet,
        "Wallet response includes cash_wallet",
        section
    )
    assert_true(
        wallet and "reward_wallet" in wallet,
        "Wallet response includes reward_wallet",
        section
    )
    assert_true(
        wallet and "pending_redemptions" in wallet,
        "Wallet response includes pending_redemptions",
        section
    )
    
    if wallet:
        cash_balance = wallet.get("cash_wallet", {}).get("balance", 0)
        reward_balance = wallet.get("reward_wallet", {}).get("balance", 0)
        log(f"   Cash balance: ₹{cash_balance}, Reward balance: {reward_balance} pts")
        test_data["retailer_cash_balance"] = cash_balance
        test_data["retailer_reward_balance"] = reward_balance
        
        assert_true(
            cash_balance >= 20,
            f"Cash balance reflects credited coupon (balance={cash_balance})",
            section
        )
    
    # Test 6b: GET /retailer/transactions → returns immutable tx list
    log("Test 6b: GET /retailer/transactions")
    transactions = api_call("GET", "/dms/coupons/retailer/transactions", token=retailer_token)
    assert_true(
        transactions and len(transactions.get("data", [])) > 0,
        f"Transactions list has entries (got {len(transactions.get('data', []))})",
        section
    )
    
    if transactions and transactions.get("data"):
        has_credit_coupon = any(
            tx.get("kind") == "credit_coupon" for tx in transactions["data"]
        )
        assert_true(
            has_credit_coupon,
            "Transactions include 'credit_coupon' kind",
            section
        )
    
    # Test 6c: GET /retailer/coupons → shows claimed coupons
    log("Test 6c: GET /retailer/coupons")
    retailer_coupons = api_call("GET", "/dms/coupons/retailer/coupons", token=retailer_token)
    assert_true(
        retailer_coupons and len(retailer_coupons.get("data", [])) > 0,
        f"Retailer coupons list has entries (got {len(retailer_coupons.get('data', []))})",
        section
    )
    
    # Test 6d: Retailer trying POST /scan → 403
    log("Test 6d: Retailer trying POST /scan → 403")
    retailer_scan = api_call(
        "POST", "/dms/coupons/scan",
        token=retailer_token,
        json_data={
            "retailer_id": "any",
            "coupon_code": "TEST"
        },
        expect_status=403
    )
    assert_true(
        retailer_scan is None or retailer_scan == {},
        "Retailer cannot POST /scan (403)",
        section
    )
    
    # Test 6e: Retailer trying to access /batches → 403
    log("Test 6e: Retailer trying to access /batches → 403")
    retailer_batches = api_call(
        "GET", "/dms/coupons/batches",
        token=retailer_token,
        expect_status=403
    )
    assert_true(
        retailer_batches is None or retailer_batches == {},
        "Retailer cannot access /batches (403)",
        section
    )


def test_section_7_redemption_flow():
    """Section 7: Redemption flow"""
    section = "7. Redemption Flow"
    log(f"\n{'='*60}\n{section}\n{'='*60}")
    
    owner_token = tokens["owner"]
    retailer_id = test_data.get("sp_retailer_id")
    cash_balance = test_data.get("retailer_cash_balance", 0)
    
    if not retailer_id:
        log("Skipping section 7: No retailer_id", "WARN")
        return
    
    # Test 7a: Create CASH redemption → pending
    log(f"Test 7a: Create CASH redemption for retailer {retailer_id}, amount=20")
    redemption = api_call(
        "POST", "/dms/coupons/redemptions",
        token=owner_token,
        json_data={
            "retailer_id": retailer_id,
            "wallet_type": "cash",
            "amount": 20,
            "notes": "Month end"
        }
    )
    assert_true(
        redemption and redemption.get("ok") is True,
        "Cash redemption created successfully",
        section
    )
    assert_true(
        redemption and redemption.get("redemption", {}).get("status") == "pending",
        "Redemption status is 'pending'",
        section
    )
    assert_true(
        redemption and "CR-" in redemption.get("redemption", {}).get("redemption_no", ""),
        "Redemption number matches CR-YY-##### pattern",
        section
    )
    
    if redemption:
        test_data["cash_redemption_id"] = redemption["redemption"]["id"]
        test_data["cash_redemption_no"] = redemption["redemption"]["redemption_no"]
    
    # Test 7b: GET /redemptions?status=pending → contains it
    log("Test 7b: GET /redemptions?status=pending")
    pending_redemptions = api_call(
        "GET", "/dms/coupons/redemptions",
        token=owner_token,
        params={"status": "pending"}
    )
    assert_true(
        pending_redemptions and len(pending_redemptions.get("data", [])) > 0,
        f"Pending redemptions list has entries (got {len(pending_redemptions.get('data', []))})",
        section
    )
    
    # Test 7c: Approve cash redemption → credit_note_no
    redemption_id = test_data.get("cash_redemption_id")
    if redemption_id:
        log(f"Test 7c: Approve cash redemption {redemption_id}")
        approve_resp = api_call(
            "POST", f"/dms/coupons/redemptions/{redemption_id}/approve",
            token=owner_token
        )
        assert_true(
            approve_resp and approve_resp.get("ok") is True,
            "Cash redemption approved successfully",
            section
        )
        assert_true(
            approve_resp and "CN-" in approve_resp.get("credit_note_no", ""),
            "Credit note number matches CN-YY-##### pattern",
            section
        )
        
        if approve_resp:
            test_data["credit_note_no"] = approve_resp.get("credit_note_no")
    
    # Test 7d: GET /credit-notes → CN present
    log("Test 7d: GET /credit-notes")
    credit_notes = api_call("GET", "/dms/coupons/credit-notes", token=owner_token)
    assert_true(
        credit_notes and len(credit_notes.get("data", [])) > 0,
        f"Credit notes list has entries (got {len(credit_notes.get('data', []))})",
        section
    )
    
    if credit_notes and credit_notes.get("data"):
        has_cn = any(
            cn.get("amount") == 20 for cn in credit_notes["data"]
        )
        assert_true(
            has_cn,
            "Credit note with amount 20 exists",
            section
        )
    
    # Test 7e: Verify primary ledger entry (check via retailer wallet balance)
    log("Test 7e: Verify wallet balance decreased after redemption")
    retailer_token = tokens["retailer1"]
    wallet_after = api_call("GET", "/dms/coupons/retailer/wallet", token=retailer_token)
    if wallet_after:
        new_cash_balance = wallet_after.get("cash_wallet", {}).get("balance", 0)
        expected_balance = cash_balance - 20
        assert_true(
            abs(new_cash_balance - expected_balance) < 0.01,
            f"Wallet balance decreased correctly (expected={expected_balance}, got={new_cash_balance})",
            section
        )
    
    # Test 7f: Create another pending redemption and reject it
    log("Test 7f: Create another cash redemption and reject it")
    redemption2 = api_call(
        "POST", "/dms/coupons/redemptions",
        token=owner_token,
        json_data={
            "retailer_id": retailer_id,
            "wallet_type": "cash",
            "amount": 10,
            "notes": "Test reject"
        }
    )
    
    if redemption2 and redemption2.get("redemption"):
        redemption2_id = redemption2["redemption"]["id"]
        log(f"Test 7g: Reject redemption {redemption2_id}")
        reject_resp = api_call(
            "POST", f"/dms/coupons/redemptions/{redemption2_id}/reject",
            token=owner_token
        )
        assert_true(
            reject_resp and reject_resp.get("ok") is True,
            "Redemption rejected successfully",
            section
        )
    
    # Test 7h: REWARD redemption → dispatch_advice_no
    reward_balance = test_data.get("retailer_reward_balance", 0)
    if reward_balance >= 50:
        log(f"Test 7h: Create REWARD redemption for retailer {retailer_id}, amount=50")
        reward_redemption = api_call(
            "POST", "/dms/coupons/redemptions",
            token=owner_token,
            json_data={
                "retailer_id": retailer_id,
                "wallet_type": "reward",
                "amount": 50,
                "notes": "Reward redemption"
            }
        )
        
        if reward_redemption and reward_redemption.get("redemption"):
            reward_redemption_id = reward_redemption["redemption"]["id"]
            log(f"Test 7i: Approve reward redemption {reward_redemption_id}")
            approve_reward = api_call(
                "POST", f"/dms/coupons/redemptions/{reward_redemption_id}/approve",
                token=owner_token
            )
            assert_true(
                approve_reward and approve_reward.get("ok") is True,
                "Reward redemption approved successfully",
                section
            )
            assert_true(
                approve_reward and "DA-" in approve_reward.get("dispatch_advice_no", ""),
                "Dispatch advice number matches DA-YY-##### pattern",
                section
            )
            
            if approve_reward:
                test_data["dispatch_advice_id"] = approve_reward.get("dispatch_advice_id")
    
    # Test 7j: GET /dispatch-advices
    log("Test 7j: GET /dispatch-advices")
    dispatch_advices = api_call("GET", "/dms/coupons/dispatch-advices", token=owner_token)
    assert_true(
        dispatch_advices and len(dispatch_advices.get("data", [])) > 0,
        f"Dispatch advices list has entries (got {len(dispatch_advices.get('data', []))})",
        section
    )
    
    # Test 7k: Mark dispatch advice as dispatched
    da_id = test_data.get("dispatch_advice_id")
    if da_id:
        log(f"Test 7k: Mark dispatch advice {da_id} as dispatched")
        mark_dispatched = api_call(
            "POST", f"/dms/coupons/dispatch-advices/{da_id}/mark-dispatched",
            token=owner_token
        )
        assert_true(
            mark_dispatched and mark_dispatched.get("ok") is True,
            "Dispatch advice marked as dispatched",
            section
        )
    
    # Test 7l: Insufficient balance test
    log("Test 7l: Try redemption with amount > available balance → 400")
    insufficient = api_call(
        "POST", "/dms/coupons/redemptions",
        token=owner_token,
        json_data={
            "retailer_id": retailer_id,
            "wallet_type": "cash",
            "amount": 999999,
            "notes": "Too much"
        },
        expect_status=400
    )
    assert_true(
        insufficient is None or insufficient == {},
        "Insufficient balance returns 400",
        section
    )


def test_section_8_rbac():
    """Section 8: RBAC (403 tests)"""
    section = "8. RBAC (403 Tests)"
    log(f"\n{'='*60}\n{section}\n{'='*60}")
    
    retailer_token = tokens["retailer1"]
    distributor_token = tokens["distributor1"]
    sp_token = tokens["salesperson"]
    
    # Test 8a: Retailer calling /batches (POST) → 403
    log("Test 8a: Retailer calling /batches (POST) → 403")
    retailer_batch = api_call(
        "POST", "/dms/coupons/batches",
        token=retailer_token,
        json_data={"coupon_type": "cash", "coupon_value": 10, "count": 5, "title": "Test"},
        expect_status=403
    )
    assert_true(
        retailer_batch is None or retailer_batch == {},
        "Retailer cannot POST /batches (403)",
        section
    )
    
    # Test 8b: Retailer calling /batches (GET) → 403
    log("Test 8b: Retailer calling /batches (GET) → 403")
    retailer_batches = api_call(
        "GET", "/dms/coupons/batches",
        token=retailer_token,
        expect_status=403
    )
    assert_true(
        retailer_batches is None or retailer_batches == {},
        "Retailer cannot GET /batches (403)",
        section
    )
    
    # Test 8c: Retailer calling /coupons (GET) → 403
    log("Test 8c: Retailer calling /coupons (GET) → 403")
    retailer_coupons = api_call(
        "GET", "/dms/coupons",
        token=retailer_token,
        expect_status=403
    )
    assert_true(
        retailer_coupons is None or retailer_coupons == {},
        "Retailer cannot GET /coupons (403)",
        section
    )
    
    # Test 8d: Retailer calling /redemptions/{id}/approve → 403
    log("Test 8d: Retailer calling /redemptions/{id}/approve → 403")
    retailer_approve = api_call(
        "POST", "/dms/coupons/redemptions/fake-id/approve",
        token=retailer_token,
        expect_status=403
    )
    assert_true(
        retailer_approve is None or retailer_approve == {},
        "Retailer cannot approve redemptions (403)",
        section
    )
    
    # Test 8e: Distributor calling /batches (POST) → 403
    log("Test 8e: Distributor calling /batches (POST) → 403")
    dist_batch = api_call(
        "POST", "/dms/coupons/batches",
        token=distributor_token,
        json_data={"coupon_type": "cash", "coupon_value": 10, "count": 5, "title": "Test"},
        expect_status=403
    )
    assert_true(
        dist_batch is None or dist_batch == {},
        "Distributor cannot POST /batches (403)",
        section
    )
    
    # Test 8f: Distributor calling /reports/summary → should work (not 403)
    log("Test 8f: Distributor calling /reports/summary → should work")
    dist_reports = api_call(
        "GET", "/dms/coupons/reports/summary",
        token=distributor_token
    )
    assert_true(
        dist_reports is not None,
        "Distributor can access /reports/summary",
        section
    )
    
    # Test 8g: Salesperson calling /batches (POST) → 403
    log("Test 8g: Salesperson calling /batches (POST) → 403")
    sp_batch = api_call(
        "POST", "/dms/coupons/batches",
        token=sp_token,
        json_data={"coupon_type": "cash", "coupon_value": 10, "count": 5, "title": "Test"},
        expect_status=403
    )
    assert_true(
        sp_batch is None or sp_batch == {},
        "Salesperson cannot POST /batches (403)",
        section
    )
    
    # Test 8h: Distributor GET /redemptions → returns ONLY own distributor_id
    log("Test 8h: Distributor GET /redemptions → filtered to own distributor_id")
    dist_redemptions = api_call(
        "GET", "/dms/coupons/redemptions",
        token=distributor_token
    )
    assert_true(
        dist_redemptions is not None,
        "Distributor can access /redemptions",
        section
    )
    # Note: We can't verify filtering without knowing distributor's ID, but endpoint should work


def test_section_9_reports():
    """Section 9: Reports"""
    section = "9. Reports"
    log(f"\n{'='*60}\n{section}\n{'='*60}")
    
    owner_token = tokens["owner"]
    
    # Test 9a: GET /reports/summary
    log("Test 9a: GET /reports/summary")
    summary = api_call("GET", "/dms/coupons/reports/summary", token=owner_token)
    assert_true(
        summary and "totals" in summary,
        "Summary report includes 'totals'",
        section
    )
    assert_true(
        summary and "by_type" in summary,
        "Summary report includes 'by_type'",
        section
    )
    assert_true(
        summary and "batches" in summary,
        "Summary report includes 'batches'",
        section
    )
    assert_true(
        summary and "fraud_attempts" in summary,
        "Summary report includes 'fraud_attempts'",
        section
    )
    assert_true(
        summary and "wallet_totals" in summary,
        "Summary report includes 'wallet_totals'",
        section
    )
    
    # Test 9b: GET /reports/salesperson
    log("Test 9b: GET /reports/salesperson")
    sp_report = api_call("GET", "/dms/coupons/reports/salesperson", token=owner_token)
    assert_true(
        sp_report and len(sp_report.get("data", [])) > 0,
        f"Salesperson report has entries (got {len(sp_report.get('data', []))})",
        section
    )
    
    if sp_report and sp_report.get("data"):
        # Find salesperson with scans >= 2
        sp_with_scans = [sp for sp in sp_report["data"] if sp.get("scans", 0) >= 2]
        assert_true(
            len(sp_with_scans) > 0,
            f"At least one salesperson has scans >= 2 (found {len(sp_with_scans)})",
            section
        )
    
    # Test 9c: GET /reports/wallet-summary
    log("Test 9c: GET /reports/wallet-summary")
    wallet_summary = api_call("GET", "/dms/coupons/reports/wallet-summary", token=owner_token)
    assert_true(
        wallet_summary and len(wallet_summary.get("data", [])) > 0,
        f"Wallet summary has entries (got {len(wallet_summary.get('data', []))})",
        section
    )
    
    # Test 9d: GET /audit-log
    log("Test 9d: GET /audit-log")
    audit_log = api_call("GET", "/dms/coupons/audit-log", token=owner_token)
    assert_true(
        audit_log and len(audit_log.get("data", [])) > 0,
        f"Audit log has entries (got {len(audit_log.get('data', []))})",
        section
    )
    
    if audit_log and audit_log.get("data"):
        # Check for expected events
        events = [e.get("event") for e in audit_log["data"]]
        has_batch_generated = "batch.generated" in events
        has_batch_activated = "batch.activated" in events
        has_coupon_claimed = "coupon.claimed" in events
        
        assert_true(
            has_batch_generated,
            "Audit log contains 'batch.generated' event",
            section
        )
        assert_true(
            has_batch_activated,
            "Audit log contains 'batch.activated' event",
            section
        )
        assert_true(
            has_coupon_claimed,
            "Audit log contains 'coupon.claimed' event",
            section
        )


def test_section_10_wallet_derivation():
    """Section 10: Immutable wallet derivation"""
    section = "10. Immutable Wallet Derivation"
    log(f"\n{'='*60}\n{section}\n{'='*60}")
    
    retailer_token = tokens["retailer1"]
    
    # Test 10a: Get wallet balance
    log("Test 10a: Get wallet balance from /retailer/wallet")
    wallet = api_call("GET", "/dms/coupons/retailer/wallet", token=retailer_token)
    assert_true(
        wallet is not None,
        "Wallet endpoint returns data",
        section
    )
    
    if not wallet:
        return
    
    cash_balance = wallet.get("cash_wallet", {}).get("balance", 0)
    reward_balance = wallet.get("reward_wallet", {}).get("balance", 0)
    log(f"   Wallet balances: Cash=₹{cash_balance}, Reward={reward_balance} pts")
    
    # Test 10b: Get all transactions and manually sum
    log("Test 10b: Get all transactions from /retailer/transactions")
    transactions = api_call("GET", "/dms/coupons/retailer/transactions", token=retailer_token)
    assert_true(
        transactions is not None,
        "Transactions endpoint returns data",
        section
    )
    
    if not transactions:
        return
    
    # Calculate balances from transactions
    cash_sum = 0.0
    reward_sum = 0.0
    
    for tx in transactions.get("data", []):
        wallet_type = tx.get("wallet_type")
        amount = tx.get("amount", 0)
        
        if wallet_type == "cash":
            cash_sum += amount
        elif wallet_type == "reward":
            reward_sum += amount
    
    log(f"   Calculated from transactions: Cash=₹{cash_sum}, Reward={reward_sum} pts")
    
    # Test 10c: Verify balances match
    assert_true(
        abs(cash_balance - cash_sum) < 0.01,
        f"Cash wallet balance matches transaction sum (wallet={cash_balance}, sum={cash_sum})",
        section
    )
    assert_true(
        abs(reward_balance - reward_sum) < 0.01,
        f"Reward wallet balance matches transaction sum (wallet={reward_balance}, sum={reward_sum})",
        section
    )


def print_summary():
    """Print test summary."""
    log(f"\n{'='*60}\nTEST SUMMARY\n{'='*60}")
    
    total = results["passed"] + results["failed"]
    pass_rate = (results["passed"] / total * 100) if total > 0 else 0
    
    log(f"Total Tests: {total}")
    log(f"Passed: {results['passed']} ✅")
    log(f"Failed: {results['failed']} ❌")
    log(f"Pass Rate: {pass_rate:.1f}%")
    
    log(f"\n{'='*60}\nSECTION BREAKDOWN\n{'='*60}")
    for section, counts in results["sections"].items():
        section_total = counts["passed"] + counts["failed"]
        section_rate = (counts["passed"] / section_total * 100) if section_total > 0 else 0
        status = "✅" if counts["failed"] == 0 else "❌"
        log(f"{status} {section}: {counts['passed']}/{section_total} ({section_rate:.0f}%)")
    
    return results["failed"] == 0


def main():
    """Main test runner."""
    log("="*60)
    log("GO OIL Coupon Engine - Backend Test Suite")
    log("="*60)
    
    # Login all users
    log("\n--- Logging in all test users ---")
    for role in CREDENTIALS.keys():
        login(role)
    
    # Run all test sections
    try:
        test_section_1_batch_generation()
        test_section_2_batch_lifecycle()
        test_section_3_coupon_listing()
        test_section_4_sales_officer_flow()
        test_section_5_scan_flow()
        test_section_6_retailer_wallet()
        test_section_7_redemption_flow()
        test_section_8_rbac()
        test_section_9_reports()
        test_section_10_wallet_derivation()
    except Exception as e:
        log(f"Test suite error: {e}", "FAIL")
        import traceback
        traceback.print_exc()
    
    # Print summary
    success = print_summary()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
