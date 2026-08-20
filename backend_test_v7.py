#!/usr/bin/env python3
"""
CONTINUATION v7 Backend Testing
Tests: SELF BANK endpoints (/api/dms/my/bank) + TRANSPORT on direct-sales + invoice
"""

import requests
import json
import time
import random
import string
from datetime import datetime

# Base URL from frontend/.env
BASE_URL = "https://po-order-sync.preview.emergentagent.com/api"

# Test credentials (all password: GoOil@2026)
CREDENTIALS = {
    "owner": {"email": "owner@gooil.com", "password": "GoOil@2026"},
    "distributor1": {"email": "distributor1@gooil.com", "password": "GoOil@2026"},
    "retailer1": {"email": "retailer1@gooil.com", "password": "GoOil@2026"},
    "salesperson": {"email": "salesperson@gooil.com", "password": "GoOil@2026"},
}

def login(role):
    """Login and return JWT token and user data"""
    creds = CREDENTIALS[role]
    resp = requests.post(f"{BASE_URL}/auth/login", json=creds)
    if resp.status_code != 200:
        print(f"❌ Login failed for {role}: {resp.status_code} {resp.text}")
        return None, None
    data = resp.json()
    return data.get("token"), data.get("user")

def headers(token):
    """Return headers with JWT token"""
    return {"Authorization": f"Bearer {token}"}

# ============================================================================
# TEST 1: SELF BANK ENDPOINTS (/api/dms/my/bank)
# ============================================================================
def test_self_bank_endpoints():
    print("\n" + "="*80)
    print("TEST 1: SELF BANK ENDPOINTS (/api/dms/my/bank)")
    print("="*80)
    
    owner_token, owner_user = login("owner")
    dist1_token, dist1_user = login("distributor1")
    retailer1_token, retailer1_user = login("retailer1")
    sp_token, sp_user = login("salesperson")
    
    if not all([owner_token, dist1_token, retailer1_token, sp_token]):
        print("❌ TEST 1 FAILED: Login failed")
        return False
    
    # 1a. As distributor1: GET /my/bank → 200, returns {party_type:"distributor", id, name, bank:{}}
    print("\n[1a] GET /my/bank as distributor1...")
    resp = requests.get(f"{BASE_URL}/dms/my/bank", headers=headers(dist1_token))
    if resp.status_code != 200:
        print(f"❌ GET /my/bank failed: {resp.status_code} {resp.text}")
        return False
    
    dist1_bank_before = resp.json()
    
    # Verify structure
    if dist1_bank_before.get("party_type") != "distributor":
        print(f"❌ Expected party_type='distributor', got: {dist1_bank_before.get('party_type')}")
        return False
    
    if not dist1_bank_before.get("id"):
        print(f"❌ Missing 'id' field")
        return False
    
    if not dist1_bank_before.get("name"):
        print(f"❌ Missing 'name' field")
        return False
    
    if "bank" not in dist1_bank_before:
        print(f"❌ Missing 'bank' field")
        return False
    
    dist1_id = dist1_bank_before["id"]
    
    print(f"✅ GET /my/bank as distributor1 → 200")
    print(f"   - party_type: {dist1_bank_before['party_type']}")
    print(f"   - id: {dist1_id}")
    print(f"   - name: {dist1_bank_before['name']}")
    print(f"   - bank: {dist1_bank_before['bank']}")
    
    # 1b. As distributor1: PUT /my/bank with bank details → 200 ok:true
    print("\n[1b] PUT /my/bank as distributor1 with bank details...")
    bank_payload = {
        "bank": {
            "bank_name": "ICICI",
            "bank_account": "111222",
            "bank_ifsc": "ICIC0001",
            "bank_branch": "Karol Bagh",
            "upi_id": "anil@icici",
            "upi_name": "Anil Dist",
            "gstin": "07AAACD1234M1Z5",
            "qr_url": "data:image/png;base64,AAA"
        }
    }
    resp = requests.put(f"{BASE_URL}/dms/my/bank", json=bank_payload, headers=headers(dist1_token))
    if resp.status_code != 200:
        print(f"❌ PUT /my/bank failed: {resp.status_code} {resp.text}")
        return False
    
    put_response = resp.json()
    if not put_response.get("ok"):
        print(f"❌ Expected ok:true, got: {put_response}")
        return False
    
    print(f"✅ PUT /my/bank as distributor1 → 200, ok:true")
    
    # 1c. GET /my/bank again and verify bank fields persisted
    print("\n[1c] GET /my/bank as distributor1 and verify bank fields persisted...")
    resp = requests.get(f"{BASE_URL}/dms/my/bank", headers=headers(dist1_token))
    if resp.status_code != 200:
        print(f"❌ GET /my/bank failed: {resp.status_code} {resp.text}")
        return False
    
    dist1_bank_after = resp.json()
    bank = dist1_bank_after.get("bank", {})
    
    # Verify all fields
    expected_fields = {
        "bank_name": "ICICI",
        "bank_account": "111222",
        "bank_ifsc": "ICIC0001",
        "bank_branch": "Karol Bagh",
        "upi_id": "anil@icici",
        "upi_name": "Anil Dist",
        "gstin": "07AAACD1234M1Z5",
        "qr_url": "data:image/png;base64,AAA"
    }
    
    failed_fields = []
    for key, expected_value in expected_fields.items():
        actual_value = bank.get(key)
        if actual_value != expected_value:
            failed_fields.append(f"{key}: expected={expected_value}, actual={actual_value}")
    
    if failed_fields:
        print(f"❌ Bank fields not persisted correctly:")
        for field in failed_fields:
            print(f"   - {field}")
        return False
    
    print(f"✅ GET /my/bank → bank fields persisted correctly")
    print(f"   - bank_name: {bank['bank_name']}")
    print(f"   - bank_account: {bank['bank_account']}")
    print(f"   - bank_ifsc: {bank['bank_ifsc']}")
    print(f"   - bank_branch: {bank['bank_branch']}")
    print(f"   - upi_id: {bank['upi_id']}")
    print(f"   - upi_name: {bank['upi_name']}")
    print(f"   - gstin: {bank['gstin']}")
    print(f"   - qr_url: {bank['qr_url'][:30]}...")
    
    # 1d. GET /distributors/{dist1_id} as owner and confirm same bank object visible
    print(f"\n[1d] GET /distributors/{dist1_id} as owner and verify bank object...")
    resp = requests.get(f"{BASE_URL}/dms/distributors/{dist1_id}", headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"❌ GET /distributors/{dist1_id} failed: {resp.status_code} {resp.text}")
        return False
    
    dist_data = resp.json()
    owner_view_bank = dist_data.get("bank", {})
    
    # Verify same bank object
    for key, expected_value in expected_fields.items():
        actual_value = owner_view_bank.get(key)
        if actual_value != expected_value:
            print(f"❌ Owner view bank mismatch for {key}: expected={expected_value}, actual={actual_value}")
            return False
    
    print(f"✅ GET /distributors/{dist1_id} as owner → bank object matches")
    
    # 1e. As retailer1: GET /my/bank → 200 party_type:"retailer"
    print("\n[1e] GET /my/bank as retailer1...")
    resp = requests.get(f"{BASE_URL}/dms/my/bank", headers=headers(retailer1_token))
    if resp.status_code != 200:
        print(f"❌ GET /my/bank failed: {resp.status_code} {resp.text}")
        return False
    
    retailer1_bank = resp.json()
    
    if retailer1_bank.get("party_type") != "retailer":
        print(f"❌ Expected party_type='retailer', got: {retailer1_bank.get('party_type')}")
        return False
    
    retailer1_id = retailer1_bank["id"]
    
    print(f"✅ GET /my/bank as retailer1 → 200")
    print(f"   - party_type: {retailer1_bank['party_type']}")
    print(f"   - id: {retailer1_id}")
    print(f"   - name: {retailer1_bank['name']}")
    
    # 1f. As retailer1: PUT /my/bank with bank object → 200
    print("\n[1f] PUT /my/bank as retailer1 with bank details...")
    retailer_bank_payload = {
        "bank": {
            "bank_name": "HDFC",
            "bank_account": "333444",
            "bank_ifsc": "HDFC0002",
            "bank_branch": "Nehru Place",
            "upi_id": "retailer1@hdfc",
            "upi_name": "Retailer One",
            "gstin": "07BBBCD5678N2Z6",
            "qr_url": "data:image/png;base64,BBB"
        }
    }
    resp = requests.put(f"{BASE_URL}/dms/my/bank", json=retailer_bank_payload, headers=headers(retailer1_token))
    if resp.status_code != 200:
        print(f"❌ PUT /my/bank failed: {resp.status_code} {resp.text}")
        return False
    
    print(f"✅ PUT /my/bank as retailer1 → 200")
    
    # 1g. GET /my/bank as retailer1 and verify persisted
    print("\n[1g] GET /my/bank as retailer1 and verify persisted...")
    resp = requests.get(f"{BASE_URL}/dms/my/bank", headers=headers(retailer1_token))
    if resp.status_code != 200:
        print(f"❌ GET /my/bank failed: {resp.status_code} {resp.text}")
        return False
    
    retailer1_bank_after = resp.json()
    retailer_bank = retailer1_bank_after.get("bank", {})
    
    if retailer_bank.get("bank_name") != "HDFC" or retailer_bank.get("upi_id") != "retailer1@hdfc":
        print(f"❌ Retailer bank not persisted correctly: {retailer_bank}")
        return False
    
    print(f"✅ GET /my/bank as retailer1 → bank persisted correctly")
    print(f"   - bank_name: {retailer_bank['bank_name']}")
    print(f"   - upi_id: {retailer_bank['upi_id']}")
    
    # 1h. As owner: GET /my/bank → expect 403 (owner has no own party bank)
    print("\n[1h] GET /my/bank as owner → expect 403...")
    resp = requests.get(f"{BASE_URL}/dms/my/bank", headers=headers(owner_token))
    if resp.status_code != 403:
        print(f"❌ Expected 403, got {resp.status_code}")
        return False
    
    print(f"✅ GET /my/bank as owner → 403 (correct)")
    
    # 1i. As salesperson: GET /my/bank → expect 403
    print("\n[1i] GET /my/bank as salesperson → expect 403...")
    resp = requests.get(f"{BASE_URL}/dms/my/bank", headers=headers(sp_token))
    if resp.status_code != 403:
        print(f"❌ Expected 403, got {resp.status_code}")
        return False
    
    print(f"✅ GET /my/bank as salesperson → 403 (correct)")
    
    print("\n✅ TEST 1 PASSED: Self bank endpoints working correctly")
    return True

# ============================================================================
# TEST 2: TRANSPORT ON DIRECT-SALES + INVOICE
# ============================================================================
def test_transport_on_direct_sales():
    print("\n" + "="*80)
    print("TEST 2: TRANSPORT ON DIRECT-SALES + INVOICE")
    print("="*80)
    
    owner_token, owner_user = login("owner")
    dist1_token, dist1_user = login("distributor1")
    
    if not all([owner_token, dist1_token]):
        print("❌ TEST 2 FAILED: Login failed")
        return False
    
    # 2a. Get a product ID
    print("\n[2a] Get product ID for testing...")
    resp = requests.get(f"{BASE_URL}/dms/products", headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"❌ Failed to get products: {resp.status_code} {resp.text}")
        return False
    
    products_data = resp.json()
    products = products_data.get("data", products_data) if isinstance(products_data, dict) else products_data
    if not products or len(products) == 0:
        print(f"❌ No products found in database")
        return False
    
    product_id = products[0]["id"]
    print(f"✅ Found product: {product_id}")
    
    # 2b. Get distributor1's retailers
    print("\n[2b] Get distributor1's retailers...")
    resp = requests.get(f"{BASE_URL}/dms/retailers", headers=headers(dist1_token))
    if resp.status_code != 200:
        print(f"❌ GET /retailers failed: {resp.status_code} {resp.text}")
        return False
    
    retailers_data = resp.json()
    retailers = retailers_data.get("data", retailers_data) if isinstance(retailers_data, dict) else retailers_data
    if not retailers or len(retailers) == 0:
        print(f"❌ No retailers found for distributor1")
        return False
    
    retailer_id = retailers[0]["id"]
    print(f"✅ Found retailer: {retailer_id}")
    
    # 2c. As distributor1: POST /direct-sales with transport object → 200
    print("\n[2c] POST /direct-sales as distributor1 with transport object...")
    time.sleep(1)  # Avoid bill number collision
    
    transport_payload = {
        "mode": "Road",
        "vehicle_no": "DL01AB1234",
        "transporter": "Blue Dart",
        "lr_no": "LR-99"
    }
    
    ds_payload = {
        "retailer_id": retailer_id,
        "items": [
            {
                "product_id": product_id,
                "qty_boxes": 1,
                "box_price": 500
            }
        ],
        "transport": transport_payload
    }
    
    resp = requests.post(f"{BASE_URL}/dms/direct-sales", json=ds_payload, headers=headers(dist1_token))
    if resp.status_code != 200:
        print(f"❌ POST /direct-sales failed: {resp.status_code} {resp.text}")
        return False
    
    bill_data = resp.json()
    bill_id = bill_data.get("id")
    bill_no = bill_data.get("bill_no")
    
    if not bill_id:
        print(f"❌ Response missing 'id' field")
        return False
    
    print(f"✅ POST /direct-sales → 200")
    print(f"   - bill_id: {bill_id}")
    print(f"   - bill_no: {bill_no}")
    
    # Verify transport in response
    if "transport" not in bill_data:
        print(f"❌ Response missing 'transport' field")
        return False
    
    bill_transport = bill_data.get("transport", {})
    for key, expected_value in transport_payload.items():
        actual_value = bill_transport.get(key)
        if actual_value != expected_value:
            print(f"❌ Transport field mismatch for {key}: expected={expected_value}, actual={actual_value}")
            return False
    
    print(f"✅ Bill response contains correct transport object")
    print(f"   - mode: {bill_transport['mode']}")
    print(f"   - vehicle_no: {bill_transport['vehicle_no']}")
    print(f"   - transporter: {bill_transport['transporter']}")
    print(f"   - lr_no: {bill_transport['lr_no']}")
    
    # 2d. GET /print/retailer-bill/{bill_id} as owner → 200
    print(f"\n[2d] GET /print/retailer-bill/{bill_id} as owner...")
    resp = requests.get(f"{BASE_URL}/dms/print/retailer-bill/{bill_id}", headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"❌ GET /print/retailer-bill failed: {resp.status_code} {resp.text}")
        return False
    
    print_data = resp.json()
    
    # 2e. Verify response.invoice.transport equals the transport sent
    print("\n[2e] Verify response.invoice.transport...")
    if "invoice" not in print_data:
        print(f"❌ Response missing 'invoice' field")
        return False
    
    invoice = print_data["invoice"]
    
    if "transport" not in invoice:
        print(f"❌ invoice missing 'transport' field")
        return False
    
    invoice_transport = invoice.get("transport", {})
    
    # Verify all transport fields
    for key, expected_value in transport_payload.items():
        actual_value = invoice_transport.get(key)
        if actual_value != expected_value:
            print(f"❌ Invoice transport mismatch for {key}: expected={expected_value}, actual={actual_value}")
            return False
    
    print(f"✅ invoice.transport matches sent transport object")
    print(f"   - mode: {invoice_transport['mode']}")
    print(f"   - vehicle_no: {invoice_transport['vehicle_no']}")
    print(f"   - transporter: {invoice_transport['transporter']}")
    print(f"   - lr_no: {invoice_transport['lr_no']}")
    
    # 2f. Verify invoice object still has all required fields
    print("\n[2f] Verify invoice object has all required fields...")
    required_invoice_keys = [
        "doc_title", "doc_no", "date", "seller", "bill_to", "items", 
        "totals", "amount_in_words"
    ]
    
    missing_keys = [key for key in required_invoice_keys if key not in invoice]
    if missing_keys:
        print(f"❌ Invoice missing keys: {missing_keys}")
        return False
    
    # Verify seller
    if not isinstance(invoice["seller"], dict) or not invoice["seller"].get("name"):
        print(f"❌ invoice.seller invalid or missing name")
        return False
    
    # Verify bill_to
    if not invoice.get("bill_to"):
        print(f"❌ invoice.bill_to missing")
        return False
    
    # Verify items
    if not isinstance(invoice["items"], list) or len(invoice["items"]) == 0:
        print(f"❌ invoice.items invalid or empty")
        return False
    
    # Verify totals
    if not isinstance(invoice["totals"], dict):
        print(f"❌ invoice.totals invalid")
        return False
    
    # Verify amount_in_words
    if not invoice.get("amount_in_words") or not invoice["amount_in_words"].startswith("Rupees"):
        print(f"❌ invoice.amount_in_words invalid")
        return False
    
    print(f"✅ invoice object has all required fields")
    print(f"   - seller: {invoice['seller']['name']}")
    print(f"   - bill_to: {invoice['bill_to']}")
    print(f"   - items: {len(invoice['items'])} items")
    print(f"   - totals: subtotal={invoice['totals'].get('subtotal')}, grand_total={invoice['totals'].get('grand_total')}")
    print(f"   - amount_in_words: {invoice['amount_in_words'][:50]}...")
    
    print("\n✅ TEST 2 PASSED: Transport on direct-sales + invoice working correctly")
    return True

# ============================================================================
# MAIN
# ============================================================================
def main():
    print("\n" + "="*80)
    print("CONTINUATION v7 BACKEND TESTING")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Test credentials: all @gooil.com / GoOil@2026")
    
    results = {
        "TEST 1: Self Bank Endpoints": test_self_bank_endpoints(),
        "TEST 2: Transport on Direct-Sales + Invoice": test_transport_on_direct_sales(),
    }
    
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed*100//total}%)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit(main())
