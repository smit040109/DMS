#!/usr/bin/env python3
"""
Phase 3 — Reports Module Backend Testing
Tests all 42 reports with RBAC, Excel export, saved filters, and favorites.
"""
import requests
import sys
from datetime import datetime

# Base URL from frontend/.env
BASE_URL = "https://98ab0a70-ac1e-4fab-a2e4-d42918cb55a1.preview.emergentagent.com/api"

# Test credentials (all passwords: GoOil@2026)
CREDENTIALS = {
    "owner": {"email": "owner@gooil.com", "password": "GoOil@2026"},
    "owner_accountant": {"email": "accountant@gooil.com", "password": "GoOil@2026"},
    "distributor1": {"email": "distributor1@gooil.com", "password": "GoOil@2026"},
    "distributor2": {"email": "distributor2@gooil.com", "password": "GoOil@2026"},
    "distributor_accountant": {"email": "distacct@gooil.com", "password": "GoOil@2026"},
    "salesperson": {"email": "salesperson@gooil.com", "password": "GoOil@2026"},
    "team_leader": {"email": "teamleader@gooil.com", "password": "GoOil@2026"},
    "regional_manager": {"email": "regionalmgr@gooil.com", "password": "GoOil@2026"},
    "retailer1": {"email": "retailer1@gooil.com", "password": "GoOil@2026"},
}

# All 42 report IDs
ALL_REPORT_IDS = [
    # Transaction (12)
    "sale", "purchase", "sale_order", "day_book", "all_transactions", "bill_wise_profit",
    "profit_loss", "sale_aging", "purchase_aging", "cashflow", "balance_sheet", "expense",
    # Party (6)
    "party_statement", "party_wise_profit_loss", "all_parties", "party_by_items",
    "sale_purchase_by_party", "outstanding_due",
    # GST (7)
    "gstr1", "gstr2", "gstr3b", "gst_transaction", "gstr9", "sale_summary_hsn", "sac_report",
    # Item/Stock (12)
    "stock_summary", "item_by_party", "item_wise_profit_loss", "low_stock_summary",
    "item_detail", "stock_detail", "sale_purchase_by_item_category",
    "stock_summary_by_item_category", "item_batch", "item_serial",
    "item_wise_discount", "godown_transfer",
    # Sales Team (5)
    "sp_performance", "sp_collection", "tl_rsm_team", "live_tracking_visits", "order_cancellation",
]

# Expected catalog counts per role
EXPECTED_CATALOG_COUNTS = {
    "owner": 42,
    "owner_accountant": 42,
    "distributor1": 25,  # Excludes admin-only reports
    "distributor_accountant": 25,
    "salesperson": 3,  # sale, sale_order, order_cancellation
    "team_leader": 8,  # salesperson + admin_tl_rm reports
    "regional_manager": 9,  # team_leader + tl_rsm_team
}

# Admin-only reports (should return 403 for distributor/salesperson)
ADMIN_ONLY_REPORTS = [
    "profit_loss", "balance_sheet", "cashflow",
    "gstr1", "gstr2", "gstr3b", "gst_transaction", "gstr9", "sale_summary_hsn", "sac_report",
    "godown_transfer",
]

# Admin + TL + RM reports (should return 403 for salesperson)
ADMIN_TL_RM_REPORTS = ["sp_performance", "sp_collection", "live_tracking_visits"]

# Test results
test_results = {
    "passed": 0,
    "failed": 0,
    "errors": []
}

def login(role_key):
    """Login and return token"""
    creds = CREDENTIALS[role_key]
    resp = requests.post(f"{BASE_URL}/auth/login", json=creds)
    if resp.status_code != 200:
        raise Exception(f"Login failed for {role_key}: {resp.status_code} {resp.text}")
    data = resp.json()
    return data["token"]

def test_catalog_visibility():
    """TEST 1: Catalog visibility per role"""
    print("\n" + "="*80)
    print("TEST 1: CATALOG VISIBILITY PER ROLE")
    print("="*80)
    
    for role_key, expected_count in EXPECTED_CATALOG_COUNTS.items():
        token = login(role_key)
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{BASE_URL}/dms/reports/catalog", headers=headers)
        
        if resp.status_code != 200:
            test_results["failed"] += 1
            test_results["errors"].append(f"❌ {role_key}: catalog returned {resp.status_code}")
            print(f"❌ {role_key}: catalog returned {resp.status_code}")
            continue
        
        data = resp.json()
        # Count total reports across all groups (API uses "groups" not "categories")
        total_reports = sum(len(group.get("items", [])) for group in data.get("groups", []))
        
        if total_reports == expected_count:
            test_results["passed"] += 1
            print(f"✅ {role_key}: {total_reports} reports (expected {expected_count})")
        else:
            test_results["failed"] += 1
            test_results["errors"].append(f"❌ {role_key}: {total_reports} reports (expected {expected_count})")
            print(f"❌ {role_key}: {total_reports} reports (expected {expected_count})")
    
    # Test retailer blocked (403)
    token = login("retailer1")
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/dms/reports/catalog", headers=headers)
    
    if resp.status_code == 403:
        test_results["passed"] += 1
        print(f"✅ retailer: 403 (correctly blocked)")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ retailer: {resp.status_code} (expected 403)")
        print(f"❌ retailer: {resp.status_code} (expected 403)")

def test_run_all_reports_as_owner():
    """TEST 2: Run all 42 reports as owner"""
    print("\n" + "="*80)
    print("TEST 2: RUN ALL 42 REPORTS AS OWNER")
    print("="*80)
    
    token = login("owner")
    headers = {"Authorization": f"Bearer {token}"}
    
    failed_reports = []
    for report_id in ALL_REPORT_IDS:
        # Test without filters
        resp = requests.get(f"{BASE_URL}/dms/reports/{report_id}/run", headers=headers)
        
        if resp.status_code != 200:
            test_results["failed"] += 1
            failed_reports.append(f"{report_id}: {resp.status_code}")
            print(f"❌ {report_id}: {resp.status_code}")
            continue
        
        data = resp.json()
        # Check response shape
        if "rows" in data and "totals" in data and "columns" in data:
            test_results["passed"] += 1
            print(f"✅ {report_id}: {len(data['rows'])} rows")
        else:
            test_results["failed"] += 1
            failed_reports.append(f"{report_id}: missing keys (rows/totals/columns)")
            print(f"❌ {report_id}: missing keys")
    
    # Test with date filters
    print("\n--- Testing with date filters ---")
    resp = requests.get(
        f"{BASE_URL}/dms/reports/sale/run",
        headers=headers,
        params={"date_from": "2025-01-01", "date_to": "2026-12-31"}
    )
    if resp.status_code == 200:
        test_results["passed"] += 1
        print(f"✅ sale with date filters: 200")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ sale with date filters: {resp.status_code}")
        print(f"❌ sale with date filters: {resp.status_code}")
    
    if failed_reports:
        test_results["errors"].append(f"Failed reports: {', '.join(failed_reports)}")

def test_rbac_scoping_distributor():
    """TEST 3: RBAC scoping for distributor"""
    print("\n" + "="*80)
    print("TEST 3: RBAC SCOPING FOR DISTRIBUTOR")
    print("="*80)
    
    token = login("distributor1")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test sale/run (should return only distributor1's data)
    resp = requests.get(f"{BASE_URL}/dms/reports/sale/run", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        test_results["passed"] += 1
        print(f"✅ sale/run: {len(data['rows'])} rows (distributor1 scope)")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ sale/run: {resp.status_code}")
        print(f"❌ sale/run: {resp.status_code}")
    
    # Test outstanding_due/run
    resp = requests.get(f"{BASE_URL}/dms/reports/outstanding_due/run", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        test_results["passed"] += 1
        print(f"✅ outstanding_due/run: {len(data['rows'])} rows (distributor1 scope)")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ outstanding_due/run: {resp.status_code}")
        print(f"❌ outstanding_due/run: {resp.status_code}")
    
    # Test stock_summary/run
    resp = requests.get(f"{BASE_URL}/dms/reports/stock_summary/run", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        test_results["passed"] += 1
        print(f"✅ stock_summary/run: {len(data['rows'])} rows (distributor1 inventory)")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ stock_summary/run: {resp.status_code}")
        print(f"❌ stock_summary/run: {resp.status_code}")
    
    # Test admin-only reports (should return 403)
    for report_id in ["profit_loss", "gstr1"]:
        resp = requests.get(f"{BASE_URL}/dms/reports/{report_id}/run", headers=headers)
        if resp.status_code == 403:
            test_results["passed"] += 1
            print(f"✅ {report_id}/run: 403 (correctly blocked)")
        else:
            test_results["failed"] += 1
            test_results["errors"].append(f"❌ {report_id}/run: {resp.status_code} (expected 403)")
            print(f"❌ {report_id}/run: {resp.status_code} (expected 403)")

def test_rbac_salesperson():
    """TEST 4: RBAC for salesperson"""
    print("\n" + "="*80)
    print("TEST 4: RBAC FOR SALESPERSON")
    print("="*80)
    
    token = login("salesperson")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test allowed reports
    for report_id in ["sale", "sale_order"]:
        resp = requests.get(f"{BASE_URL}/dms/reports/{report_id}/run", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            test_results["passed"] += 1
            print(f"✅ {report_id}/run: 200 ({len(data['rows'])} rows)")
        else:
            test_results["failed"] += 1
            test_results["errors"].append(f"❌ {report_id}/run: {resp.status_code}")
            print(f"❌ {report_id}/run: {resp.status_code}")
    
    # Test blocked reports (admin-only)
    for report_id in ["sp_performance", "profit_loss", "balance_sheet", "gstr1"]:
        resp = requests.get(f"{BASE_URL}/dms/reports/{report_id}/run", headers=headers)
        if resp.status_code == 403:
            test_results["passed"] += 1
            print(f"✅ {report_id}/run: 403 (correctly blocked)")
        else:
            test_results["failed"] += 1
            test_results["errors"].append(f"❌ {report_id}/run: {resp.status_code} (expected 403)")
            print(f"❌ {report_id}/run: {resp.status_code} (expected 403)")

def test_retailer_blocked():
    """TEST 5: Retailer blocked from all reports endpoints"""
    print("\n" + "="*80)
    print("TEST 5: RETAILER BLOCKED")
    print("="*80)
    
    token = login("retailer1")
    headers = {"Authorization": f"Bearer {token}"}
    
    endpoints = [
        ("/dms/reports/catalog", "GET", None),
        ("/dms/reports/sale/run", "GET", None),
        ("/dms/reports/outstanding_due/run", "GET", None),
        ("/dms/reports/favorites/toggle/sale", "POST", None),
        ("/dms/reports/saved-filters/sale", "GET", None),
        ("/dms/reports/saved-filters/sale", "POST", {"name": "test", "filters": {}}),
    ]
    
    for endpoint, method, payload in endpoints:
        if method == "GET":
            resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
        else:
            resp = requests.post(f"{BASE_URL}{endpoint}", headers=headers, json=payload)
        
        if resp.status_code == 403:
            test_results["passed"] += 1
            print(f"✅ {method} {endpoint}: 403")
        else:
            test_results["failed"] += 1
            test_results["errors"].append(f"❌ {method} {endpoint}: {resp.status_code} (expected 403)")
            print(f"❌ {method} {endpoint}: {resp.status_code} (expected 403)")

def test_favorites_toggle():
    """TEST 6: Favorites toggle"""
    print("\n" + "="*80)
    print("TEST 6: FAVORITES TOGGLE")
    print("="*80)
    
    token = login("owner")
    headers = {"Authorization": f"Bearer {token}"}
    
    # a) Toggle ON
    resp = requests.post(f"{BASE_URL}/dms/reports/favorites/toggle/sale", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        if data.get("ok") and data.get("is_favorite") == True:
            test_results["passed"] += 1
            print(f"✅ Toggle ON: is_favorite=true")
        else:
            test_results["failed"] += 1
            test_results["errors"].append(f"❌ Toggle ON: unexpected response {data}")
            print(f"❌ Toggle ON: unexpected response")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ Toggle ON: {resp.status_code}")
        print(f"❌ Toggle ON: {resp.status_code}")
    
    # b) Toggle OFF
    resp = requests.post(f"{BASE_URL}/dms/reports/favorites/toggle/sale", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        if data.get("ok") and data.get("is_favorite") == False:
            test_results["passed"] += 1
            print(f"✅ Toggle OFF: is_favorite=false")
        else:
            test_results["failed"] += 1
            test_results["errors"].append(f"❌ Toggle OFF: unexpected response {data}")
            print(f"❌ Toggle OFF: unexpected response")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ Toggle OFF: {resp.status_code}")
        print(f"❌ Toggle OFF: {resp.status_code}")
    
    # c) Check catalog favorites list
    resp = requests.get(f"{BASE_URL}/dms/reports/catalog", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        favorites = data.get("favorites", [])
        test_results["passed"] += 1
        print(f"✅ Catalog favorites: {len(favorites)} items")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ Catalog favorites: {resp.status_code}")
        print(f"❌ Catalog favorites: {resp.status_code}")
    
    # d) Toggle unknown report_id
    resp = requests.post(f"{BASE_URL}/dms/reports/favorites/toggle/does_not_exist", headers=headers)
    if resp.status_code == 404:
        test_results["passed"] += 1
        print(f"✅ Toggle unknown: 404")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ Toggle unknown: {resp.status_code} (expected 404)")
        print(f"❌ Toggle unknown: {resp.status_code} (expected 404)")
    
    # e) Retailer trying to toggle
    token_retailer = login("retailer1")
    headers_retailer = {"Authorization": f"Bearer {token_retailer}"}
    resp = requests.post(f"{BASE_URL}/dms/reports/favorites/toggle/sale", headers=headers_retailer)
    if resp.status_code == 403:
        test_results["passed"] += 1
        print(f"✅ Retailer toggle: 403")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ Retailer toggle: {resp.status_code} (expected 403)")
        print(f"❌ Retailer toggle: {resp.status_code} (expected 403)")

def test_excel_export():
    """TEST 7: Excel export"""
    print("\n" + "="*80)
    print("TEST 7: EXCEL EXPORT")
    print("="*80)
    
    token = login("owner")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 5 different reports
    test_reports = ["sale", "purchase", "outstanding_due", "stock_summary", "gstr1"]
    
    for report_id in test_reports:
        resp = requests.get(f"{BASE_URL}/dms/reports/{report_id}/export", headers=headers)
        
        if resp.status_code == 200:
            content_type = resp.headers.get("content-type", "")
            size = len(resp.content)
            
            if "spreadsheet" in content_type and size > 3000:
                test_results["passed"] += 1
                print(f"✅ {report_id}/export: 200, {size} bytes, {content_type}")
            else:
                test_results["failed"] += 1
                test_results["errors"].append(f"❌ {report_id}/export: invalid content ({size} bytes, {content_type})")
                print(f"❌ {report_id}/export: invalid content")
        else:
            test_results["failed"] += 1
            test_results["errors"].append(f"❌ {report_id}/export: {resp.status_code}")
            print(f"❌ {report_id}/export: {resp.status_code}")
    
    # Test retailer blocked
    token_retailer = login("retailer1")
    headers_retailer = {"Authorization": f"Bearer {token_retailer}"}
    resp = requests.get(f"{BASE_URL}/dms/reports/sale/export", headers=headers_retailer)
    if resp.status_code == 403:
        test_results["passed"] += 1
        print(f"✅ Retailer export: 403")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ Retailer export: {resp.status_code} (expected 403)")
        print(f"❌ Retailer export: {resp.status_code} (expected 403)")

def test_legacy_sale_endpoints():
    """TEST 8: Legacy sale endpoints"""
    print("\n" + "="*80)
    print("TEST 8: LEGACY SALE ENDPOINTS")
    print("="*80)
    
    token_owner = login("owner")
    headers_owner = {"Authorization": f"Bearer {token_owner}"}
    
    # Test /sale/run
    resp = requests.get(f"{BASE_URL}/dms/reports/sale/run", headers=headers_owner)
    if resp.status_code == 200:
        test_results["passed"] += 1
        print(f"✅ /sale/run (owner): 200")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ /sale/run (owner): {resp.status_code}")
        print(f"❌ /sale/run (owner): {resp.status_code}")
    
    # Test /sale/export
    resp = requests.get(f"{BASE_URL}/dms/reports/sale/export", headers=headers_owner)
    if resp.status_code == 200:
        test_results["passed"] += 1
        print(f"✅ /sale/export (owner): 200")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ /sale/export (owner): {resp.status_code}")
        print(f"❌ /sale/export (owner): {resp.status_code}")
    
    # Test retailer blocked
    token_retailer = login("retailer1")
    headers_retailer = {"Authorization": f"Bearer {token_retailer}"}
    
    resp = requests.get(f"{BASE_URL}/dms/reports/sale/run", headers=headers_retailer)
    if resp.status_code == 403:
        test_results["passed"] += 1
        print(f"✅ /sale/run (retailer): 403")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ /sale/run (retailer): {resp.status_code} (expected 403)")
        print(f"❌ /sale/run (retailer): {resp.status_code} (expected 403)")
    
    resp = requests.get(f"{BASE_URL}/dms/reports/sale/export", headers=headers_retailer)
    if resp.status_code == 403:
        test_results["passed"] += 1
        print(f"✅ /sale/export (retailer): 403")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ /sale/export (retailer): {resp.status_code} (expected 403)")
        print(f"❌ /sale/export (retailer): {resp.status_code} (expected 403)")

def test_saved_filters_crud():
    """TEST 9: Saved filters CRUD"""
    print("\n" + "="*80)
    print("TEST 9: SAVED FILTERS CRUD")
    print("="*80)
    
    token = login("owner")
    headers = {"Authorization": f"Bearer {token}"}
    
    # a) POST saved filter
    payload = {
        "name": "Q1 2026",
        "filters": {
            "date_from": "2026-01-01",
            "date_to": "2026-03-31",
            "sale_type": "primary"
        }
    }
    resp = requests.post(f"{BASE_URL}/dms/reports/saved-filters/sale", headers=headers, json=payload)
    if resp.status_code == 200:
        data = resp.json()
        filter_id = data.get("id")
        test_results["passed"] += 1
        print(f"✅ POST saved filter: {filter_id}")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ POST saved filter: {resp.status_code}")
        print(f"❌ POST saved filter: {resp.status_code}")
        return
    
    # b) GET saved filters
    resp = requests.get(f"{BASE_URL}/dms/reports/saved-filters/sale", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        if len(data) > 0:
            test_results["passed"] += 1
            print(f"✅ GET saved filters: {len(data)} items")
        else:
            test_results["failed"] += 1
            test_results["errors"].append(f"❌ GET saved filters: empty list")
            print(f"❌ GET saved filters: empty list")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ GET saved filters: {resp.status_code}")
        print(f"❌ GET saved filters: {resp.status_code}")
    
    # c) DELETE saved filter
    resp = requests.delete(f"{BASE_URL}/dms/reports/saved-filters/{filter_id}", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        if data.get("deleted") == 1:
            test_results["passed"] += 1
            print(f"✅ DELETE saved filter: deleted=1")
        else:
            test_results["failed"] += 1
            test_results["errors"].append(f"❌ DELETE saved filter: deleted={data.get('deleted')}")
            print(f"❌ DELETE saved filter: deleted={data.get('deleted')}")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ DELETE saved filter: {resp.status_code}")
        print(f"❌ DELETE saved filter: {resp.status_code}")
    
    # d) DELETE with wrong id
    resp = requests.delete(f"{BASE_URL}/dms/reports/saved-filters/wrong-id-123", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        if data.get("deleted") == 0:
            test_results["passed"] += 1
            print(f"✅ DELETE wrong id: deleted=0")
        else:
            test_results["failed"] += 1
            test_results["errors"].append(f"❌ DELETE wrong id: deleted={data.get('deleted')}")
            print(f"❌ DELETE wrong id: deleted={data.get('deleted')}")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ DELETE wrong id: {resp.status_code}")
        print(f"❌ DELETE wrong id: {resp.status_code}")
    
    # e) POST with empty name
    payload = {"name": "", "filters": {}}
    resp = requests.post(f"{BASE_URL}/dms/reports/saved-filters/sale", headers=headers, json=payload)
    if resp.status_code == 400:
        test_results["passed"] += 1
        print(f"✅ POST empty name: 400")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ POST empty name: {resp.status_code} (expected 400)")
        print(f"❌ POST empty name: {resp.status_code} (expected 400)")
    
    # f) Retailer trying
    token_retailer = login("retailer1")
    headers_retailer = {"Authorization": f"Bearer {token_retailer}"}
    
    resp = requests.get(f"{BASE_URL}/dms/reports/saved-filters/sale", headers=headers_retailer)
    if resp.status_code == 403:
        test_results["passed"] += 1
        print(f"✅ Retailer GET: 403")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ Retailer GET: {resp.status_code} (expected 403)")
        print(f"❌ Retailer GET: {resp.status_code} (expected 403)")
    
    resp = requests.post(f"{BASE_URL}/dms/reports/saved-filters/sale", headers=headers_retailer, json=payload)
    if resp.status_code == 403:
        test_results["passed"] += 1
        print(f"✅ Retailer POST: 403")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ Retailer POST: {resp.status_code} (expected 403)")
        print(f"❌ Retailer POST: {resp.status_code} (expected 403)")

def test_date_filter_sanity():
    """TEST 10: Date filter sanity"""
    print("\n" + "="*80)
    print("TEST 10: DATE FILTER SANITY")
    print("="*80)
    
    token = login("owner")
    headers = {"Authorization": f"Bearer {token}"}
    
    # a) Old date range (no data)
    resp = requests.get(
        f"{BASE_URL}/dms/reports/sale/run",
        headers=headers,
        params={"date_from": "2000-01-01", "date_to": "2000-12-31"}
    )
    if resp.status_code == 200:
        data = resp.json()
        if len(data["rows"]) == 0:
            test_results["passed"] += 1
            print(f"✅ Old date range: 0 rows")
        else:
            test_results["failed"] += 1
            test_results["errors"].append(f"❌ Old date range: {len(data['rows'])} rows (expected 0)")
            print(f"❌ Old date range: {len(data['rows'])} rows (expected 0)")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ Old date range: {resp.status_code}")
        print(f"❌ Old date range: {resp.status_code}")
    
    # b) sale_type=primary
    resp = requests.get(
        f"{BASE_URL}/dms/reports/sale/run",
        headers=headers,
        params={"sale_type": "primary"}
    )
    if resp.status_code == 200:
        data = resp.json()
        test_results["passed"] += 1
        print(f"✅ sale_type=primary: {len(data['rows'])} rows")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ sale_type=primary: {resp.status_code}")
        print(f"❌ sale_type=primary: {resp.status_code}")
    
    # c) sale_type=secondary
    resp = requests.get(
        f"{BASE_URL}/dms/reports/sale/run",
        headers=headers,
        params={"sale_type": "secondary"}
    )
    if resp.status_code == 200:
        data = resp.json()
        test_results["passed"] += 1
        print(f"✅ sale_type=secondary: {len(data['rows'])} rows")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ sale_type=secondary: {resp.status_code}")
        print(f"❌ sale_type=secondary: {resp.status_code}")
    
    # d) sale_type=invalid (may accept or reject)
    resp = requests.get(
        f"{BASE_URL}/dms/reports/sale/run",
        headers=headers,
        params={"sale_type": "invalid"}
    )
    if resp.status_code in [200, 400]:
        test_results["passed"] += 1
        print(f"✅ sale_type=invalid: {resp.status_code} (accepted behavior)")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"❌ sale_type=invalid: {resp.status_code}")
        print(f"❌ sale_type=invalid: {resp.status_code}")

def main():
    print("\n" + "="*80)
    print("PHASE 3 — REPORTS MODULE BACKEND TESTING")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Testing {len(ALL_REPORT_IDS)} reports across 5 categories")
    print("="*80)
    
    try:
        test_catalog_visibility()
        test_run_all_reports_as_owner()
        test_rbac_scoping_distributor()
        test_rbac_salesperson()
        test_retailer_blocked()
        test_favorites_toggle()
        test_excel_export()
        test_legacy_sale_endpoints()
        test_saved_filters_crud()
        test_date_filter_sanity()
        
        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"✅ PASSED: {test_results['passed']}")
        print(f"❌ FAILED: {test_results['failed']}")
        
        if test_results["errors"]:
            print("\n" + "="*80)
            print("ERRORS:")
            print("="*80)
            for error in test_results["errors"]:
                print(error)
        
        print("\n" + "="*80)
        if test_results["failed"] == 0:
            print("✅ ALL TESTS PASSED")
            print("="*80)
            return 0
        else:
            print("❌ SOME TESTS FAILED")
            print("="*80)
            return 1
    
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
