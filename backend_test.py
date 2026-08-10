#!/usr/bin/env python3
"""
CONTINUATION v6 Backend Testing
Tests: Settings company profile, Invoice data object, Bank+Docs, Direct-sales RBAC, Live map field_staff
"""

import requests
import json
import time
import random
import string
from datetime import datetime

# Base URL from frontend/.env
BASE_URL = "https://transport-bill-3.preview.emergentagent.com/api"

# Test credentials (all password: GoOil@2026)
CREDENTIALS = {
    "owner": {"email": "owner@gooil.com", "password": "GoOil@2026"},
    "accountant": {"email": "accountant@gooil.com", "password": "GoOil@2026"},
    "distributor1": {"email": "distributor1@gooil.com", "password": "GoOil@2026"},
    "distributor2": {"email": "distributor2@gooil.com", "password": "GoOil@2026"},
    "retailer1": {"email": "retailer1@gooil.com", "password": "GoOil@2026"},
    "retailer2": {"email": "retailer2@gooil.com", "password": "GoOil@2026"},
    "salesperson": {"email": "salesperson@gooil.com", "password": "GoOil@2026"},
}

# Existing sample IDs from load_demo.py
EBILL_ID = "eb-3573b814ba"
RETAILER_BILL_ID = "rb-88ec18e1ce"

def login(role):
    """Login and return JWT token"""
    creds = CREDENTIALS[role]
    resp = requests.post(f"{BASE_URL}/auth/login", json=creds)
    if resp.status_code != 200:
        print(f"❌ Login failed for {role}: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    return data.get("token")

def headers(token):
    """Return headers with JWT token"""
    return {"Authorization": f"Bearer {token}"}

def random_id():
    """Generate random string for unique emails"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

# ============================================================================
# TEST 1: SETTINGS COMPANY PROFILE
# ============================================================================
def test_settings_company_profile():
    print("\n" + "="*80)
    print("TEST 1: SETTINGS COMPANY PROFILE")
    print("="*80)
    
    owner_token = login("owner")
    dist1_token = login("distributor1")
    
    if not owner_token or not dist1_token:
        print("❌ TEST 1 FAILED: Login failed")
        return False
    
    # 1a. GET /settings as owner → 200
    print("\n[1a] GET /settings as owner...")
    resp = requests.get(f"{BASE_URL}/dms/settings", headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"❌ GET /settings failed: {resp.status_code} {resp.text}")
        return False
    settings_before = resp.json()
    print(f"✅ GET /settings → 200 (current company_name: {settings_before.get('company_name', 'N/A')})")
    
    # 1b. PUT /settings as owner with company profile fields → 200
    print("\n[1b] PUT /settings as owner with company profile...")
    company_profile = {
        "company_gstin": "07ABCDE1234F1Z5",
        "company_address": "Plot 12, Sector 18, Delhi",
        "company_state": "Delhi",
        "company_state_code": "07",
        "company_phone": "9000000010",
        "company_email": "billing@gooil.com",
        "company_bank_name": "HDFC Bank",
        "company_bank_account": "1234567890",
        "company_bank_ifsc": "HDFC0000123",
        "company_bank_branch": "CP Delhi",
        "company_upi_id": "gooil@hdfcbank",
        "company_upi_name": "GO OIL",
        "invoice_signatory": "For GO OIL Lubricants",
        "invoice_show_acknowledgement": True,
        "invoice_terms": "Goods once sold will not be taken back",
        "invoice_message": "Thank you for your business"
    }
    resp = requests.put(f"{BASE_URL}/dms/settings", json=company_profile, headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"❌ PUT /settings failed: {resp.status_code} {resp.text}")
        return False
    print(f"✅ PUT /settings → 200")
    
    # 1c. GET /settings and verify all fields persisted
    print("\n[1c] GET /settings and verify all fields persisted...")
    resp = requests.get(f"{BASE_URL}/dms/settings", headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"❌ GET /settings failed: {resp.status_code} {resp.text}")
        return False
    settings_after = resp.json()
    
    # Verify all fields
    failed_fields = []
    for key, expected_value in company_profile.items():
        actual_value = settings_after.get(key)
        if actual_value != expected_value:
            failed_fields.append(f"{key}: expected={expected_value}, actual={actual_value}")
    
    if failed_fields:
        print(f"❌ Fields not persisted correctly:")
        for field in failed_fields:
            print(f"   - {field}")
        return False
    
    print(f"✅ All company profile fields persisted correctly:")
    print(f"   - company_gstin: {settings_after['company_gstin']}")
    print(f"   - company_address: {settings_after['company_address']}")
    print(f"   - company_state: {settings_after['company_state']}")
    print(f"   - company_bank_name: {settings_after['company_bank_name']}")
    print(f"   - company_upi_id: {settings_after['company_upi_id']}")
    print(f"   - invoice_signatory: {settings_after['invoice_signatory']}")
    print(f"   - invoice_show_acknowledgement: {settings_after['invoice_show_acknowledgement']}")
    
    # 1d. PUT /settings as distributor1 → expect 403
    print("\n[1d] PUT /settings as distributor1 → expect 403...")
    resp = requests.put(f"{BASE_URL}/dms/settings", json={"company_name": "Hacked"}, headers=headers(dist1_token))
    if resp.status_code != 403:
        print(f"❌ Expected 403, got {resp.status_code}")
        return False
    print(f"✅ PUT /settings as distributor1 → 403 (correct RBAC)")
    
    print("\n✅ TEST 1 PASSED: Settings company profile working")
    return True

# ============================================================================
# TEST 2: INVOICE DATA OBJECT
# ============================================================================
def test_invoice_data_object():
    print("\n" + "="*80)
    print("TEST 2: INVOICE DATA OBJECT")
    print("="*80)
    
    owner_token = login("owner")
    retailer2_token = login("retailer2")
    
    if not owner_token or not retailer2_token:
        print("❌ TEST 2 FAILED: Login failed")
        return False
    
    # 2a. GET /print/ebill/{id} as owner → 200, verify invoice object
    print(f"\n[2a] GET /print/ebill/{EBILL_ID} as owner...")
    resp = requests.get(f"{BASE_URL}/dms/print/ebill/{EBILL_ID}", headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"❌ GET /print/ebill failed: {resp.status_code} {resp.text}")
        return False
    
    ebill_data = resp.json()
    if "invoice" not in ebill_data:
        print(f"❌ Response missing 'invoice' key")
        return False
    
    invoice = ebill_data["invoice"]
    
    # Verify required keys
    required_keys = [
        "doc_title", "doc_no", "date", "seller", "bill_to", "items", "totals",
        "amount_in_words", "acknowledgement_enabled", "upi_qr"
    ]
    missing_keys = [key for key in required_keys if key not in invoice]
    if missing_keys:
        print(f"❌ Invoice missing keys: {missing_keys}")
        return False
    
    # Verify seller structure
    if not isinstance(invoice["seller"], dict):
        print(f"❌ invoice.seller is not a dict")
        return False
    
    seller_keys = ["name", "gstin", "bank_name", "upi_id"]
    missing_seller_keys = [key for key in seller_keys if key not in invoice["seller"]]
    if missing_seller_keys:
        print(f"❌ invoice.seller missing keys: {missing_seller_keys}")
        return False
    
    # Verify seller.name is GO OIL
    if "GO OIL" not in invoice["seller"]["name"]:
        print(f"❌ invoice.seller.name should contain 'GO OIL', got: {invoice['seller']['name']}")
        return False
    
    # Verify items structure
    if not isinstance(invoice["items"], list) or len(invoice["items"]) == 0:
        print(f"❌ invoice.items should be non-empty list")
        return False
    
    item = invoice["items"][0]
    item_keys = ["name", "hsn", "qty_label", "rate", "taxable", "gst_pct", "gst_amt", "amount"]
    missing_item_keys = [key for key in item_keys if key not in item]
    if missing_item_keys:
        print(f"❌ invoice.items[0] missing keys: {missing_item_keys}")
        return False
    
    # Verify totals structure
    totals_keys = ["subtotal", "gst_total", "sgst", "cgst", "igst", "is_interstate", "round_off", "grand_total"]
    missing_totals_keys = [key for key in totals_keys if key not in invoice["totals"]]
    if missing_totals_keys:
        print(f"❌ invoice.totals missing keys: {missing_totals_keys}")
        return False
    
    # Verify amount_in_words starts with "Rupees"
    if not invoice["amount_in_words"].startswith("Rupees"):
        print(f"❌ amount_in_words should start with 'Rupees', got: {invoice['amount_in_words']}")
        return False
    
    # Verify acknowledgement_enabled is true (from test 1)
    if invoice["acknowledgement_enabled"] != True:
        print(f"❌ acknowledgement_enabled should be true, got: {invoice['acknowledgement_enabled']}")
        return False
    
    # Verify upi_qr is a data URL
    if not invoice["upi_qr"].startswith("data:image/png;base64,"):
        print(f"❌ upi_qr should be a data:image/png;base64 URL, got: {invoice['upi_qr'][:50]}...")
        return False
    
    print(f"✅ GET /print/ebill/{EBILL_ID} → 200")
    print(f"   - invoice object present with all required keys")
    print(f"   - seller.name: {invoice['seller']['name']}")
    print(f"   - bill_to: {invoice['bill_to']}")
    print(f"   - items: {len(invoice['items'])} items")
    print(f"   - amount_in_words: {invoice['amount_in_words'][:50]}...")
    print(f"   - upi_qr: {invoice['upi_qr'][:50]}...")
    
    # 2b. GET /print/retailer-bill/{id} as owner → 200, verify invoice object
    print(f"\n[2b] GET /print/retailer-bill/{RETAILER_BILL_ID} as owner...")
    resp = requests.get(f"{BASE_URL}/dms/print/retailer-bill/{RETAILER_BILL_ID}", headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"❌ GET /print/retailer-bill failed: {resp.status_code} {resp.text}")
        return False
    
    rbill_data = resp.json()
    if "invoice" not in rbill_data:
        print(f"❌ Response missing 'invoice' key")
        return False
    
    rinvoice = rbill_data["invoice"]
    
    # Verify seller is DISTRIBUTOR (not GO OIL)
    if "GO OIL" in rinvoice["seller"]["name"]:
        print(f"❌ retailer-bill seller should be DISTRIBUTOR, not GO OIL. Got: {rinvoice['seller']['name']}")
        return False
    
    # Verify bill_to is retailer
    if not rinvoice["bill_to"]:
        print(f"❌ retailer-bill bill_to should be retailer name")
        return False
    
    print(f"✅ GET /print/retailer-bill/{RETAILER_BILL_ID} → 200")
    print(f"   - invoice object present")
    print(f"   - seller (distributor): {rinvoice['seller']['name']}")
    print(f"   - bill_to (retailer): {rinvoice['bill_to']}")
    
    # 2c. RBAC: GET /print/retailer-bill as retailer2 (not owner) → expect 403
    print(f"\n[2c] GET /print/retailer-bill/{RETAILER_BILL_ID} as retailer2 → expect 403...")
    resp = requests.get(f"{BASE_URL}/dms/print/retailer-bill/{RETAILER_BILL_ID}", headers=headers(retailer2_token))
    if resp.status_code != 403:
        print(f"❌ Expected 403, got {resp.status_code}")
        return False
    print(f"✅ GET /print/retailer-bill as retailer2 → 403 (correct RBAC)")
    
    print("\n✅ TEST 2 PASSED: Invoice data object working")
    return True

# ============================================================================
# TEST 3: BANK + DOCUMENTS ROUND-TRIP
# ============================================================================
def test_bank_documents_roundtrip():
    print("\n" + "="*80)
    print("TEST 3: BANK + DOCUMENTS ROUND-TRIP")
    print("="*80)
    
    owner_token = login("owner")
    
    if not owner_token:
        print("❌ TEST 3 FAILED: Login failed")
        return False
    
    rand = random_id()
    
    # 3a. Create throwaway distributor with bank + documents
    print(f"\n[3a] Create throwaway distributor with bank + documents...")
    dist_payload = {
        "name": f"V6 Test Dist {rand}",
        "email": f"v6dist_{rand}@gooil.com",
        "password": "GoOil@2026",
        "phone": "9999999999",
        "address": "Test Address",
        "gstin": f"07ABCDE{rand[:4]}F1Z5",
        "bank": {
            "bank_name": "SBI",
            "bank_account": "999",
            "bank_ifsc": "SBIN0001",
            "bank_branch": "MG Road",
            "upi_id": "v6dist@sbi",
            "upi_name": "V6 Dist"
        },
        "documents": [
            {
                "name": "PAN",
                "url": "data:image/png;base64,iVBOR",
                "type": "image"
            }
        ]
    }
    resp = requests.post(f"{BASE_URL}/dms/distributors", json=dist_payload, headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"❌ POST /distributors failed: {resp.status_code} {resp.text}")
        return False
    
    dist_data = resp.json()
    dist_id = dist_data.get("id")
    if not dist_id:
        print(f"❌ Response missing 'id' key")
        return False
    
    print(f"✅ POST /distributors → 200 (id: {dist_id})")
    
    # 3b. GET distributor and verify bank + documents persisted
    print(f"\n[3b] GET /distributors/{dist_id} and verify bank + documents...")
    resp = requests.get(f"{BASE_URL}/dms/distributors/{dist_id}", headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"❌ GET /distributors/{dist_id} failed: {resp.status_code} {resp.text}")
        return False
    
    dist_get = resp.json()
    
    # Verify bank
    if "bank" not in dist_get or not isinstance(dist_get["bank"], dict):
        print(f"❌ bank not persisted or not a dict")
        return False
    
    bank = dist_get["bank"]
    if bank.get("bank_name") != "SBI" or bank.get("upi_id") != "v6dist@sbi":
        print(f"❌ bank fields not persisted correctly: {bank}")
        return False
    
    # Verify documents
    if "documents" not in dist_get or not isinstance(dist_get["documents"], list):
        print(f"❌ documents not persisted or not a list")
        return False
    
    if len(dist_get["documents"]) != 1 or dist_get["documents"][0].get("name") != "PAN":
        print(f"❌ documents not persisted correctly: {dist_get['documents']}")
        return False
    
    print(f"✅ GET /distributors/{dist_id} → 200")
    print(f"   - bank persisted: {bank['bank_name']}, {bank['upi_id']}")
    print(f"   - documents persisted: {len(dist_get['documents'])} docs")
    
    # 3c. PUT distributor updating bank.upi_id and adding another document
    print(f"\n[3c] PUT /distributors/{dist_id} updating bank.upi_id and adding document...")
    update_payload = {
        "bank": {
            "bank_name": "SBI",
            "bank_account": "999",
            "bank_ifsc": "SBIN0001",
            "bank_branch": "MG Road",
            "upi_id": "v6dist_updated@sbi",
            "upi_name": "V6 Dist Updated"
        },
        "documents": [
            {
                "name": "PAN",
                "url": "data:image/png;base64,iVBOR",
                "type": "image"
            },
            {
                "name": "GST Certificate",
                "url": "data:image/png;base64,iVBOR2",
                "type": "image"
            }
        ]
    }
    resp = requests.put(f"{BASE_URL}/dms/distributors/{dist_id}", json=update_payload, headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"❌ PUT /distributors/{dist_id} failed: {resp.status_code} {resp.text}")
        return False
    
    print(f"✅ PUT /distributors/{dist_id} → 200")
    
    # 3d. GET distributor and verify updates
    print(f"\n[3d] GET /distributors/{dist_id} and verify updates...")
    resp = requests.get(f"{BASE_URL}/dms/distributors/{dist_id}", headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"❌ GET /distributors/{dist_id} failed: {resp.status_code} {resp.text}")
        return False
    
    dist_updated = resp.json()
    
    if dist_updated["bank"].get("upi_id") != "v6dist_updated@sbi":
        print(f"❌ bank.upi_id not updated: {dist_updated['bank'].get('upi_id')}")
        return False
    
    if len(dist_updated["documents"]) != 2:
        print(f"❌ documents not updated, expected 2, got {len(dist_updated['documents'])}")
        return False
    
    print(f"✅ GET /distributors/{dist_id} → 200")
    print(f"   - bank.upi_id updated: {dist_updated['bank']['upi_id']}")
    print(f"   - documents updated: {len(dist_updated['documents'])} docs")
    
    # 3e. Create throwaway retailer with bank + documents + state
    print(f"\n[3e] Create throwaway retailer with bank + documents + state...")
    retailer_payload = {
        "name": f"V6 Test Retailer {rand}",
        "email": f"v6retailer_{rand}@gooil.com",
        "password": "GoOil@2026",
        "phone": "8888888888",
        "address": "Test Retailer Address",
        "distributor_id": dist_id,
        "state": "Maharashtra",
        "state_code": "27",
        "bank": {
            "bank_name": "ICICI",
            "bank_account": "888",
            "bank_ifsc": "ICIC0001",
            "bank_branch": "Andheri",
            "upi_id": "v6retailer@icici",
            "upi_name": "V6 Retailer"
        },
        "documents": [
            {
                "name": "Shop License",
                "url": "data:image/png;base64,iVBOR3",
                "type": "image"
            }
        ]
    }
    resp = requests.post(f"{BASE_URL}/dms/retailers", json=retailer_payload, headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"❌ POST /retailers failed: {resp.status_code} {resp.text}")
        return False
    
    retailer_data = resp.json()
    retailer_id = retailer_data.get("id")
    if not retailer_id:
        print(f"❌ Response missing 'id' key")
        return False
    
    print(f"✅ POST /retailers → 200 (id: {retailer_id})")
    
    # 3f. GET retailer and verify bank + documents + state persisted
    print(f"\n[3f] GET /retailers/{retailer_id} and verify bank + documents + state...")
    resp = requests.get(f"{BASE_URL}/dms/retailers/{retailer_id}", headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"❌ GET /retailers/{retailer_id} failed: {resp.status_code} {resp.text}")
        return False
    
    retailer_get = resp.json()
    
    # Verify bank
    if "bank" not in retailer_get or not isinstance(retailer_get["bank"], dict):
        print(f"❌ retailer bank not persisted or not a dict")
        return False
    
    rbank = retailer_get["bank"]
    if rbank.get("bank_name") != "ICICI" or rbank.get("upi_id") != "v6retailer@icici":
        print(f"❌ retailer bank fields not persisted correctly: {rbank}")
        return False
    
    # Verify documents
    if "documents" not in retailer_get or not isinstance(retailer_get["documents"], list):
        print(f"❌ retailer documents not persisted or not a list")
        return False
    
    if len(retailer_get["documents"]) != 1 or retailer_get["documents"][0].get("name") != "Shop License":
        print(f"❌ retailer documents not persisted correctly: {retailer_get['documents']}")
        return False
    
    # Verify state
    if retailer_get.get("state") != "Maharashtra" or retailer_get.get("state_code") != "27":
        print(f"❌ retailer state not persisted correctly: state={retailer_get.get('state')}, state_code={retailer_get.get('state_code')}")
        return False
    
    print(f"✅ GET /retailers/{retailer_id} → 200")
    print(f"   - bank persisted: {rbank['bank_name']}, {rbank['upi_id']}")
    print(f"   - documents persisted: {len(retailer_get['documents'])} docs")
    print(f"   - state persisted: {retailer_get['state']} ({retailer_get['state_code']})")
    
    # 3g. Cleanup: DELETE retailer then distributor
    print(f"\n[3g] Cleanup: DELETE retailer and distributor...")
    resp = requests.delete(f"{BASE_URL}/dms/retailers/{retailer_id}", headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"⚠️ DELETE /retailers/{retailer_id} failed: {resp.status_code} {resp.text}")
    else:
        print(f"✅ DELETE /retailers/{retailer_id} → 200")
    
    resp = requests.delete(f"{BASE_URL}/dms/distributors/{dist_id}", headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"⚠️ DELETE /distributors/{dist_id} failed: {resp.status_code} {resp.text}")
    else:
        print(f"✅ DELETE /distributors/{dist_id} → 200")
    
    print("\n✅ TEST 3 PASSED: Bank + documents round-trip working")
    return True

# ============================================================================
# TEST 4: BILL FOR EVERYONE — DIRECT-SALES RBAC
# ============================================================================
def test_direct_sales_rbac():
    print("\n" + "="*80)
    print("TEST 4: BILL FOR EVERYONE — DIRECT-SALES RBAC")
    print("="*80)
    
    owner_token = login("owner")
    sp_token = login("salesperson")
    dist1_token = login("distributor1")
    retailer1_token = login("retailer1")
    accountant_token = login("accountant")
    
    if not all([owner_token, sp_token, dist1_token, retailer1_token, accountant_token]):
        print("❌ TEST 4 FAILED: Login failed")
        return False
    
    # Get a product ID
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
    
    # 4a. Get distributors and retailers
    print(f"\n[4a] Get distributors and retailers for testing...")
    resp = requests.get(f"{BASE_URL}/dms/distributors", headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"❌ GET /distributors failed: {resp.status_code} {resp.text}")
        return False
    
    distributors_data = resp.json()
    distributors = distributors_data.get("data", distributors_data) if isinstance(distributors_data, dict) else distributors_data
    if not distributors or len(distributors) < 2:
        print(f"⚠️ Need at least 2 distributors for testing, found {len(distributors) if distributors else 0}")
        dist1_id = distributors[0]["id"] if distributors else None
        dist2_id = None
    else:
        dist1_id = distributors[0]["id"]
        dist2_id = distributors[1]["id"]
    
    # Get retailers
    resp = requests.get(f"{BASE_URL}/dms/retailers", headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"❌ GET /retailers failed: {resp.status_code} {resp.text}")
        return False
    
    retailers_data = resp.json()
    retailers = retailers_data.get("data", retailers_data) if isinstance(retailers_data, dict) else retailers_data
    retailer_under_dist1 = None
    
    for r in retailers:
        if r.get("distributor_id") == dist1_id:
            retailer_under_dist1 = r
            break
    
    if not retailer_under_dist1:
        print(f"⚠️ No retailer found under distributor1")
        return False
    
    print(f"✅ Found distributor1: {dist1_id}, retailer: {retailer_under_dist1['id']}")
    
    # 4b. Assign salesperson to distributor1
    print(f"\n[4b] Assign salesperson to distributor1...")
    assign_payload = {
        "salesperson_id": "sp-salesperson",  # Assuming this is the salesperson's ID
        "distributor_ids": [dist1_id]
    }
    # Try to assign - if it fails, continue anyway
    resp = requests.post(f"{BASE_URL}/dms/assignments/sp-distributors", json=assign_payload, headers=headers(owner_token))
    if resp.status_code == 200:
        print(f"✅ Salesperson assigned to distributor1")
    else:
        print(f"⚠️ Could not assign salesperson (may already be assigned): {resp.status_code}")
    
    # 4c. POST /direct-sales as salesperson with assigned distributor → 200
    print(f"\n[4c] POST /direct-sales as salesperson with assigned distributor...")
    ds_payload = {
        "distributor_id": dist1_id,
        "retailer_id": retailer_under_dist1["id"],
        "items": [
            {
                "product_id": product_id,
                "qty_boxes": 1
            }
        ]
    }
    resp = requests.post(f"{BASE_URL}/dms/direct-sales", json=ds_payload, headers=headers(sp_token))
    if resp.status_code != 200:
        print(f"❌ POST /direct-sales (assigned) failed: {resp.status_code} {resp.text}")
        return False
    
    bill_data = resp.json()
    print(f"✅ POST /direct-sales (assigned) → 200 (bill_no: {bill_data.get('bill_no', 'N/A')})")
    
    # 4d. POST /direct-sales with unassigned distributor → 403
    if dist2_id:
        print(f"\n[4d] POST /direct-sales as salesperson with unassigned distributor → expect 403...")
        ds_payload_unassigned = {
            "distributor_id": dist2_id,
            "retailer_id": retailer_under_dist1["id"],
            "items": [
                {
                    "product_id": product_id,
                    "qty_boxes": 1
                }
            ]
        }
        resp = requests.post(f"{BASE_URL}/dms/direct-sales", json=ds_payload_unassigned, headers=headers(sp_token))
        if resp.status_code != 403:
            print(f"❌ Expected 403, got {resp.status_code}")
            return False
        print(f"✅ POST /direct-sales (unassigned) → 403 (correct RBAC)")
    
    # 4e. As retailer: POST /direct-sales (counter-sale) → 200
    print(f"\n[4e] POST /direct-sales as retailer (counter-sale)...")
    time.sleep(1)  # Avoid bill number collision
    retailer_ds_payload = {
        "items": [
            {
                "product_id": product_id,
                "qty_boxes": 1,
                "box_price": 500
            }
        ],
        "customer": {
            "name": "Walk-in Ramesh",
            "phone": "9876543210"
        }
    }
    resp = requests.post(f"{BASE_URL}/dms/direct-sales", json=retailer_ds_payload, headers=headers(retailer1_token))
    if resp.status_code != 200:
        print(f"❌ POST /direct-sales (retailer counter-sale) failed: {resp.status_code} {resp.text}")
        return False
    
    retailer_bill = resp.json()
    print(f"✅ POST /direct-sales (retailer counter-sale) → 200")
    print(f"   - bill_no: {retailer_bill.get('bill_no', 'N/A')}")
    print(f"   - customer.name: {retailer_bill.get('customer', {}).get('name', 'N/A')}")
    print(f"   - source: {retailer_bill.get('source', 'N/A')}")
    
    # 4f. Verify retailer counter-sale did NOT create ledger entry
    print(f"\n[4f] Verify retailer counter-sale did NOT create ledger entry...")
    resp = requests.get(f"{BASE_URL}/dms/ledger/secondary", headers=headers(retailer1_token))
    if resp.status_code != 200:
        print(f"❌ GET /ledger/secondary failed: {resp.status_code} {resp.text}")
        return False
    
    ledger_data = resp.json()
    
    # Handle both list and dict responses
    if isinstance(ledger_data, list):
        ledger_entries = ledger_data
    elif isinstance(ledger_data, dict):
        ledger_entries = ledger_data.get("entries", [])
    else:
        ledger_entries = []
    
    # Check if the counter-sale bill is in the ledger
    counter_sale_in_ledger = any(
        entry.get("reference_id") == retailer_bill.get("id") or 
        entry.get("reference_no") == retailer_bill.get("bill_no")
        for entry in ledger_entries
    )
    
    if counter_sale_in_ledger:
        print(f"❌ Counter-sale bill found in retailer ledger (should NOT be there)")
        return False
    
    print(f"✅ Counter-sale bill NOT in retailer ledger (correct)")
    
    # 4g. As distributor1: POST /direct-sales for own retailer → 200 (regression)
    print(f"\n[4g] POST /direct-sales as distributor1 for own retailer → 200 (regression)...")
    time.sleep(1)  # Avoid bill number collision
    resp = requests.get(f"{BASE_URL}/dms/retailers", headers=headers(dist1_token))
    if resp.status_code != 200:
        print(f"❌ GET /retailers failed: {resp.status_code} {resp.text}")
        return False
    
    dist1_retailers_data = resp.json()
    dist1_retailers = dist1_retailers_data.get("data", dist1_retailers_data) if isinstance(dist1_retailers_data, dict) else dist1_retailers_data
    if not dist1_retailers:
        print(f"⚠️ Distributor1 has no retailers, skipping regression test")
    else:
        dist1_retailer_id = dist1_retailers[0]["id"]
        dist1_ds_payload = {
            "retailer_id": dist1_retailer_id,
            "items": [
                {
                    "product_id": product_id,
                    "qty_boxes": 1
                }
            ]
        }
        resp = requests.post(f"{BASE_URL}/dms/direct-sales", json=dist1_ds_payload, headers=headers(dist1_token))
        if resp.status_code != 200:
            print(f"❌ POST /direct-sales (distributor1) failed: {resp.status_code} {resp.text}")
            return False
        
        print(f"✅ POST /direct-sales (distributor1) → 200 (regression OK)")
    
    # 4h. As owner_accountant: POST /direct-sales → expect 403
    print(f"\n[4h] POST /direct-sales as owner_accountant → expect 403...")
    accountant_ds_payload = {
        "retailer_id": dist1_retailer_id if dist1_retailers else "dummy",
        "items": [
            {
                "product_id": product_id,
                "qty_boxes": 1
            }
        ]
    }
    resp = requests.post(f"{BASE_URL}/dms/direct-sales", json=accountant_ds_payload, headers=headers(accountant_token))
    if resp.status_code != 403:
        print(f"❌ Expected 403, got {resp.status_code}")
        return False
    print(f"✅ POST /direct-sales (owner_accountant) → 403 (correct RBAC)")
    
    print("\n✅ TEST 4 PASSED: Direct-sales RBAC working")
    return True

# ============================================================================
# TEST 5: LIVE MAP FIELD_STAFF
# ============================================================================
def test_live_map_field_staff():
    print("\n" + "="*80)
    print("TEST 5: LIVE MAP FIELD_STAFF")
    print("="*80)
    
    owner_token = login("owner")
    sp_token = login("salesperson")
    dist1_token = login("distributor1")
    retailer1_token = login("retailer1")
    
    if not all([owner_token, sp_token, dist1_token, retailer1_token]):
        print("❌ TEST 5 FAILED: Login failed")
        return False
    
    # 5a. GET /tracking/live as owner → 200, verify field_staff array present
    print(f"\n[5a] GET /tracking/live as owner → verify field_staff array...")
    resp = requests.get(f"{BASE_URL}/dms/tracking/live", headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"❌ GET /tracking/live failed: {resp.status_code} {resp.text}")
        return False
    
    live_data = resp.json()
    if "field_staff" not in live_data:
        print(f"❌ Response missing 'field_staff' key")
        return False
    
    if not isinstance(live_data["field_staff"], list):
        print(f"❌ field_staff is not a list")
        return False
    
    print(f"✅ GET /tracking/live → 200")
    print(f"   - field_staff array present (currently {len(live_data['field_staff'])} staff)")
    
    # 5b. Punch-in salesperson and send GPS ping
    print(f"\n[5b] Punch-in salesperson and send GPS ping...")
    punch_payload = {
        "lat": 28.6,
        "lng": 77.2
    }
    resp = requests.post(f"{BASE_URL}/dms/punch/in", json=punch_payload, headers=headers(sp_token))
    if resp.status_code != 200:
        print(f"❌ POST /punch/in failed: {resp.status_code} {resp.text}")
        return False
    print(f"✅ POST /punch/in (salesperson) → 200")
    
    # Send GPS ping
    ping_payload = {
        "lat": 28.6,
        "lng": 77.2
    }
    resp = requests.post(f"{BASE_URL}/dms/tracking/ping", json=ping_payload, headers=headers(sp_token))
    if resp.status_code != 200:
        print(f"❌ POST /tracking/ping failed: {resp.status_code} {resp.text}")
        return False
    print(f"✅ POST /tracking/ping (salesperson) → 200")
    
    # 5c. GET /tracking/live as owner and verify field_staff contains salesperson
    print(f"\n[5c] GET /tracking/live as owner and verify field_staff contains salesperson...")
    time.sleep(1)  # Give it a moment to update
    resp = requests.get(f"{BASE_URL}/dms/tracking/live", headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"❌ GET /tracking/live failed: {resp.status_code} {resp.text}")
        return False
    
    live_data = resp.json()
    field_staff = live_data.get("field_staff", [])
    
    # Find salesperson in field_staff
    sp_in_field_staff = None
    for staff in field_staff:
        if staff.get("role") == "salesperson":
            sp_in_field_staff = staff
            break
    
    if not sp_in_field_staff:
        print(f"❌ Salesperson not found in field_staff array")
        return False
    
    # Verify role_label is present
    if "role_label" not in sp_in_field_staff:
        print(f"❌ Salesperson in field_staff missing 'role_label' key")
        return False
    
    print(f"✅ GET /tracking/live → 200")
    print(f"   - field_staff contains salesperson")
    print(f"   - role: {sp_in_field_staff['role']}")
    print(f"   - role_label: {sp_in_field_staff['role_label']}")
    print(f"   - punched_in: {sp_in_field_staff.get('punched_in', False)}")
    
    # 5d. Punch-in distributor1 and send GPS ping
    print(f"\n[5d] Punch-in distributor1 and send GPS ping...")
    resp = requests.post(f"{BASE_URL}/dms/punch/in", json=punch_payload, headers=headers(dist1_token))
    if resp.status_code != 200:
        print(f"❌ POST /punch/in (distributor1) failed: {resp.status_code} {resp.text}")
        return False
    print(f"✅ POST /punch/in (distributor1) → 200")
    
    resp = requests.post(f"{BASE_URL}/dms/tracking/ping", json=ping_payload, headers=headers(dist1_token))
    if resp.status_code != 200:
        print(f"❌ POST /tracking/ping (distributor1) failed: {resp.status_code} {resp.text}")
        return False
    print(f"✅ POST /tracking/ping (distributor1) → 200")
    
    # 5e. GET /tracking/live as owner and verify field_staff includes distributor
    print(f"\n[5e] GET /tracking/live as owner and verify field_staff includes distributor...")
    time.sleep(1)
    resp = requests.get(f"{BASE_URL}/dms/tracking/live", headers=headers(owner_token))
    if resp.status_code != 200:
        print(f"❌ GET /tracking/live failed: {resp.status_code} {resp.text}")
        return False
    
    live_data = resp.json()
    field_staff = live_data.get("field_staff", [])
    
    # Find distributor in field_staff
    dist_in_field_staff = None
    for staff in field_staff:
        if staff.get("role") == "distributor":
            dist_in_field_staff = staff
            break
    
    if not dist_in_field_staff:
        print(f"❌ Distributor not found in field_staff array")
        return False
    
    print(f"✅ GET /tracking/live → 200")
    print(f"   - field_staff includes distributor")
    print(f"   - role: {dist_in_field_staff['role']}")
    print(f"   - role_label: {dist_in_field_staff.get('role_label', 'N/A')}")
    
    # 5f. As retailer1 → GET /tracking/live should be 403
    print(f"\n[5f] GET /tracking/live as retailer1 → expect 403...")
    resp = requests.get(f"{BASE_URL}/dms/tracking/live", headers=headers(retailer1_token))
    if resp.status_code != 403:
        print(f"❌ Expected 403, got {resp.status_code}")
        return False
    print(f"✅ GET /tracking/live (retailer1) → 403 (correct RBAC)")
    
    print("\n✅ TEST 5 PASSED: Live map field_staff working")
    return True

# ============================================================================
# MAIN
# ============================================================================
def main():
    print("\n" + "="*80)
    print("CONTINUATION v6 BACKEND TESTING")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Test credentials: all @gooil.com / GoOil@2026")
    print(f"Existing sample IDs: ebill={EBILL_ID}, retailer_bill={RETAILER_BILL_ID}")
    
    results = {
        "TEST 1: Settings Company Profile": test_settings_company_profile(),
        "TEST 2: Invoice Data Object": test_invoice_data_object(),
        "TEST 3: Bank + Documents Round-trip": test_bank_documents_roundtrip(),
        "TEST 4: Direct-sales RBAC": test_direct_sales_rbac(),
        "TEST 5: Live Map field_staff": test_live_map_field_staff(),
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
