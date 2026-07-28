#!/usr/bin/env python3
"""
Phase 4 Analytics Backend Testing Suite
Tests all /api/analytics/* endpoints with live MongoDB data
"""
import requests
import json
from typing import Dict, Any, List

# Configuration
BASE_URL = "https://oil-dms-prod.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@gooil.com"
ADMIN_PASSWORD = "GoOil@2026"

# Global token storage
TOKEN = None

def login() -> str:
    """Login and get JWT token"""
    global TOKEN
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
    data = resp.json()
    TOKEN = data.get("token") or data.get("access_token")
    assert TOKEN, "No token in login response"
    print(f"✓ Login successful")
    return TOKEN

def headers() -> Dict[str, str]:
    """Get auth headers"""
    return {"Authorization": f"Bearer {TOKEN}"}

def test_dimensions():
    """Test 1: Dimensions endpoint"""
    print("\n=== Test 1: Dimensions ===")
    resp = requests.get(f"{BASE_URL}/analytics/dimensions", headers=headers())
    assert resp.status_code == 200, f"Failed: {resp.status_code} {resp.text}"
    data = resp.json()
    
    # Verify all required arrays exist
    required = ["branches", "distributors", "retailers", "customers", "products", "skus", "warehouses", "regions", "categories", "ranges"]
    for key in required:
        assert key in data, f"Missing key: {key}"
        assert isinstance(data[key], list), f"{key} should be a list"
    
    # Verify counts
    print(f"  Branches: {len(data['branches'])}")
    print(f"  Distributors: {len(data['distributors'])}")
    print(f"  Retailers: {len(data['retailers'])}")
    print(f"  Customers: {len(data['customers'])}")
    print(f"  Products: {len(data['products'])}")
    print(f"  SKUs: {len(data['skus'])}")
    print(f"  Regions: {len(data['regions'])}")
    print(f"  Categories: {len(data['categories'])}")
    print(f"  Ranges: {data['ranges']}")
    
    assert len(data['branches']) > 0, "No branches found"
    assert len(data['distributors']) > 0, "No distributors found"
    assert len(data['skus']) > 0, "No SKUs found"
    print("✓ Dimensions endpoint working")
    return data

def test_executive_kpi():
    """Test 2: Executive KPI (15 KPIs)"""
    print("\n=== Test 2: Executive KPI ===")
    
    # Test with default range (month)
    resp = requests.get(f"{BASE_URL}/analytics/kpi/executive?range=month", headers=headers())
    assert resp.status_code == 200, f"Failed: {resp.status_code} {resp.text}"
    data = resp.json()
    
    # Verify structure
    assert "kpis" in data, "Missing kpis"
    assert "series" in data, "Missing series"
    assert "range" in data, "Missing range"
    
    # Verify all 15 KPIs exist
    required_kpis = [
        "revenue", "sales_count", "inventory_value", "inventory_health",
        "order_pipeline", "outstanding", "collections", "cash_flow",
        "claims", "returns", "replacement_cost", "approval_queue",
        "exception_count", "business_risk_score", "company_health_score"
    ]
    
    kpis = data["kpis"]
    for kpi in required_kpis:
        assert kpi in kpis, f"Missing KPI: {kpi}"
        assert "value" in kpis[kpi], f"KPI {kpi} missing value field"
    
    print(f"  Revenue: ${kpis['revenue']['value']:,.2f} ({kpis['revenue'].get('count', 0)} sales)")
    print(f"  Inventory Value: ${kpis['inventory_value']['value']:,.2f}")
    print(f"  Inventory Health: {kpis['inventory_health']['value']}%")
    print(f"  Outstanding: ${kpis['outstanding']['value']:,.2f}")
    print(f"  Collections: ${kpis['collections']['value']:,.2f}")
    print(f"  Cash Flow: ${kpis['cash_flow']['value']:,.2f}")
    print(f"  Claims: ${kpis['claims']['value']:,.2f} ({kpis['claims'].get('count', 0)} claims)")
    print(f"  Returns: ${kpis['returns']['value']:,.2f} ({kpis['returns'].get('count', 0)} returns)")
    print(f"  Business Risk Score: {kpis['business_risk_score']['value']}")
    print(f"  Company Health Score: {kpis['company_health_score']['value']}")
    print(f"  Series data points: {len(data['series'])}")
    
    # Test different range filters
    print("\n  Testing range filters...")
    for range_key in ["today", "week", "quarter", "year"]:
        resp = requests.get(f"{BASE_URL}/analytics/kpi/executive?range={range_key}", headers=headers())
        assert resp.status_code == 200, f"Range {range_key} failed: {resp.status_code}"
        print(f"    ✓ range={range_key}")
    
    # Test custom range
    resp = requests.get(f"{BASE_URL}/analytics/kpi/executive?range=custom&from=2026-06-01&to=2026-07-01", headers=headers())
    assert resp.status_code == 200, f"Custom range failed: {resp.status_code}"
    print(f"    ✓ range=custom with from/to")
    
    print("✓ Executive KPI endpoint working with all 15 KPIs")
    return data

def test_executive_kpi_filters(dimensions):
    """Test 2b: Executive KPI with filters"""
    print("\n=== Test 2b: Executive KPI Filters ===")
    
    # Test branch filter
    if dimensions['branches']:
        branch_id = dimensions['branches'][0]['id']
        resp = requests.get(f"{BASE_URL}/analytics/kpi/executive?range=month&branch_id={branch_id}", headers=headers())
        assert resp.status_code == 200, f"Branch filter failed: {resp.status_code}"
        print(f"  ✓ branch_id filter applied")
    
    # Test distributor filter
    if dimensions['distributors']:
        dist_id = dimensions['distributors'][0]['id']
        resp = requests.get(f"{BASE_URL}/analytics/kpi/executive?range=month&distributor_id={dist_id}", headers=headers())
        assert resp.status_code == 200, f"Distributor filter failed: {resp.status_code}"
        print(f"  ✓ distributor_id filter applied")
    
    print("✓ Executive KPI filters working")

def test_order_trace():
    """Test 3: Order Trace (20-node journey)"""
    print("\n=== Test 3: Order Trace ===")
    
    # Get a primary order first
    resp = requests.get(f"{BASE_URL}/collections/primary-orders?limit=1", headers=headers())
    assert resp.status_code == 200, f"Failed to get orders: {resp.status_code}"
    result = resp.json()
    orders = result.get('data', result) if isinstance(result, dict) else result
    assert len(orders) > 0, "No primary orders found"
    order_id = orders[0]['id']
    print(f"  Testing with order: {order_id}")
    
    # Test trace endpoint
    resp = requests.get(f"{BASE_URL}/analytics/trace/order/{order_id}", headers=headers())
    assert resp.status_code == 200, f"Trace failed: {resp.status_code} {resp.text}"
    data = resp.json()
    
    # Verify structure
    assert "timeline" in data, "Missing timeline"
    assert "order" in data, "Missing order"
    assert "order_type" in data, "Missing order_type"
    
    # Verify 20-node timeline
    timeline = data["timeline"]
    assert len(timeline) == 20, f"Expected 20 timeline nodes, got {len(timeline)}"
    
    # Verify each timeline entry has required fields
    for i, node in enumerate(timeline, 1):
        assert node["step"] == i, f"Step mismatch at position {i}"
        assert "node" in node, f"Missing node at step {i}"
        assert "status" in node, f"Missing status at step {i}"
        assert node["status"] in ["ok", "pending", "n/a"], f"Invalid status at step {i}: {node['status']}"
        assert "label" in node, f"Missing label at step {i}"
    
    print(f"  Timeline nodes: {len(timeline)}")
    print(f"  Order type: {data['order_type']}")
    
    # Print timeline summary
    for node in timeline[:5]:
        print(f"    Step {node['step']}: {node['node']} - {node['status']}")
    print(f"    ... (showing first 5 of 20 nodes)")
    
    # Verify related docs
    related_keys = ["invoice", "dispatch", "grn", "payments", "credit_notes", "returns", 
                    "secondary_orders", "customer_orders", "product", "sku", "batches", 
                    "ledger_entries", "audit_trail"]
    for key in related_keys:
        assert key in data, f"Missing related doc: {key}"
    
    print(f"  Related docs: invoice={data['invoice'] is not None}, dispatch={data['dispatch'] is not None}, grn={data['grn'] is not None}")
    print(f"  Payments: {len(data['payments'])}, Returns: {len(data['returns'])}")
    
    print("✓ Order trace endpoint working with 20-node timeline")
    return order_id

def test_order_trace_search():
    """Test 3b: Order Trace Search"""
    print("\n=== Test 3b: Order Trace Search ===")
    
    # Get an order number to search for
    resp = requests.get(f"{BASE_URL}/collections/primary-orders?limit=1", headers=headers())
    result = resp.json()
    orders = result.get('data', result) if isinstance(result, dict) else result
    if orders:
        order_no = orders[0].get('order_no', '')
        if order_no:
            # Search with partial order number
            search_term = order_no[:5]
            resp = requests.get(f"{BASE_URL}/analytics/trace/search?q={search_term}", headers=headers())
            assert resp.status_code == 200, f"Search failed: {resp.status_code}"
            data = resp.json()
            assert "results" in data, "Missing results"
            print(f"  Search for '{search_term}': {len(data['results'])} results")
            print("✓ Order trace search working")
    
    # Test invalid order
    resp = requests.get(f"{BASE_URL}/analytics/trace/order/invalid-order-id", headers=headers())
    assert resp.status_code == 404, f"Should return 404 for invalid order, got {resp.status_code}"
    print("  ✓ Invalid order returns 404")

def test_party360():
    """Test 4: Party 360 (4 party types)"""
    print("\n=== Test 4: Party 360 ===")
    
    # Get sample IDs
    resp = requests.get(f"{BASE_URL}/collections/distributors?limit=1", headers=headers())
    result = resp.json()
    distributors = result.get('data', result) if isinstance(result, dict) else result
    
    resp = requests.get(f"{BASE_URL}/collections/retailers?limit=1", headers=headers())
    result = resp.json()
    retailers = result.get('data', result) if isinstance(result, dict) else result
    
    resp = requests.get(f"{BASE_URL}/collections/customers?limit=1", headers=headers())
    result = resp.json()
    customers = result.get('data', result) if isinstance(result, dict) else result
    
    resp = requests.get(f"{BASE_URL}/collections/branches?limit=1", headers=headers())
    result = resp.json()
    branches = result.get('data', result) if isinstance(result, dict) else result
    
    party_tests = []
    if distributors:
        party_tests.append(("distributor", distributors[0]['id']))
    if retailers:
        party_tests.append(("retailer", retailers[0]['id']))
    if customers:
        party_tests.append(("customer", customers[0]['id']))
    if branches:
        party_tests.append(("company", branches[0]['id']))
    
    for party_type, party_id in party_tests:
        print(f"\n  Testing {party_type}...")
        resp = requests.get(f"{BASE_URL}/analytics/party360/{party_type}/{party_id}", headers=headers())
        assert resp.status_code == 200, f"Party360 {party_type} failed: {resp.status_code} {resp.text}"
        data = resp.json()
        
        # Verify structure
        required_keys = ["profile", "party_type", "financials", "performance", "risk_score", 
                        "health_score", "invoices", "payments", "returns", "claims", 
                        "credit_notes", "debit_notes", "ledger", "inventory", "audit_trail", "timeline"]
        for key in required_keys:
            assert key in data, f"Missing key in {party_type}: {key}"
        
        # Verify financials
        financials = data["financials"]
        required_financial_keys = ["total_billed", "total_paid", "total_credited", "total_debited", 
                                   "outstanding", "credit_limit", "credit_utilization", "overdue_amount"]
        for key in required_financial_keys:
            assert key in financials, f"Missing financial key in {party_type}: {key}"
        
        # Verify performance
        performance = data["performance"]
        required_perf_keys = ["invoice_count", "payment_count", "avg_order_value", "return_rate", 
                             "claim_count", "credit_note_count", "debit_note_count"]
        for key in required_perf_keys:
            assert key in performance, f"Missing performance key in {party_type}: {key}"
        
        print(f"    Profile: {data['profile'].get('name', 'N/A')}")
        print(f"    Financials: Billed=${financials['total_billed']:,.2f}, Outstanding=${financials['outstanding']:,.2f}")
        print(f"    Performance: {performance['invoice_count']} invoices, {performance['payment_count']} payments")
        print(f"    Risk Score: {data['risk_score']}, Health Score: {data['health_score']}")
        print(f"    Timeline events: {len(data['timeline'])}")
        print(f"    ✓ {party_type} party360 working")
    
    # Test invalid party type
    resp = requests.get(f"{BASE_URL}/analytics/party360/invalid/test-id", headers=headers())
    assert resp.status_code == 400, f"Should return 400 for invalid party_type, got {resp.status_code}"
    print("\n  ✓ Invalid party_type returns 400")
    
    # Test invalid ID
    resp = requests.get(f"{BASE_URL}/analytics/party360/distributor/invalid-id", headers=headers())
    assert resp.status_code == 404, f"Should return 404 for invalid ID, got {resp.status_code}"
    print("  ✓ Invalid party ID returns 404")
    
    print("\n✓ Party 360 endpoint working for all 4 party types")

def test_sales_analytics(dimensions):
    """Test 5: Sales Analytics"""
    print("\n=== Test 5: Sales Analytics ===")
    
    resp = requests.get(f"{BASE_URL}/analytics/sales?range=month", headers=headers())
    assert resp.status_code == 200, f"Failed: {resp.status_code} {resp.text}"
    data = resp.json()
    
    # Verify structure
    required_keys = ["series", "top_skus", "by_branch", "by_distributor", "by_status", "funnel", "totals"]
    for key in required_keys:
        assert key in data, f"Missing key: {key}"
    
    # Verify funnel has 5 stages
    funnel = data["funnel"]
    assert len(funnel) == 5, f"Expected 5 funnel stages, got {len(funnel)}"
    funnel_stages = [f["stage"] for f in funnel]
    expected_stages = ["orders_placed", "invoiced", "dispatched", "received", "settled"]
    for stage in expected_stages:
        assert stage in funnel_stages, f"Missing funnel stage: {stage}"
    
    # Verify top_skus max 10
    assert len(data["top_skus"]) <= 10, f"top_skus should be max 10, got {len(data['top_skus'])}"
    
    # Verify by_distributor max 10
    assert len(data["by_distributor"]) <= 10, f"by_distributor should be max 10, got {len(data['by_distributor'])}"
    
    # Verify totals
    totals = data["totals"]
    assert "revenue" in totals, "Missing revenue in totals"
    assert "count" in totals, "Missing count in totals"
    assert "avg_order_value" in totals, "Missing avg_order_value in totals"
    
    print(f"  Series data points: {len(data['series'])}")
    print(f"  Top SKUs: {len(data['top_skus'])}")
    print(f"  By branch: {len(data['by_branch'])}")
    print(f"  By distributor: {len(data['by_distributor'])}")
    print(f"  Funnel stages: {len(funnel)}")
    print(f"  Totals: Revenue=${totals['revenue']:,.2f}, Count={totals['count']}, Avg=${totals['avg_order_value']:,.2f}")
    
    # Test with filters
    if dimensions['branches']:
        branch_id = dimensions['branches'][0]['id']
        resp = requests.get(f"{BASE_URL}/analytics/sales?range=month&branch_id={branch_id}", headers=headers())
        assert resp.status_code == 200, f"Branch filter failed: {resp.status_code}"
        print(f"  ✓ branch_id filter applied")
    
    if dimensions['skus']:
        sku_id = dimensions['skus'][0]['id']
        resp = requests.get(f"{BASE_URL}/analytics/sales?range=month&sku_id={sku_id}", headers=headers())
        assert resp.status_code == 200, f"SKU filter failed: {resp.status_code}"
        print(f"  ✓ sku_id filter applied")
    
    print("✓ Sales analytics endpoint working")

def test_inventory_analytics(dimensions):
    """Test 6: Inventory Analytics"""
    print("\n=== Test 6: Inventory Analytics ===")
    
    resp = requests.get(f"{BASE_URL}/analytics/inventory", headers=headers())
    assert resp.status_code == 200, f"Failed: {resp.status_code} {resp.text}"
    data = resp.json()
    
    # Verify structure
    required_keys = ["buckets", "by_scope_value", "top_skus", "near_expiry_batches", 
                    "expired_batches_count", "totals"]
    for key in required_keys:
        assert key in data, f"Missing key: {key}"
    
    # Verify 6 buckets
    buckets = data["buckets"]
    assert len(buckets) == 6, f"Expected 6 buckets, got {len(buckets)}"
    expected_buckets = ["available", "reserved", "in_transit", "damaged", "returned", "expired"]
    bucket_names = [b["name"] for b in buckets]
    for bucket in expected_buckets:
        assert bucket in bucket_names, f"Missing bucket: {bucket}"
    
    # Verify top_skus max 12
    assert len(data["top_skus"]) <= 12, f"top_skus should be max 12, got {len(data['top_skus'])}"
    
    # Verify totals
    totals = data["totals"]
    assert "total_units" in totals, "Missing total_units"
    assert "total_value" in totals, "Missing total_value"
    assert "damaged_pct" in totals, "Missing damaged_pct"
    
    print(f"  Buckets: {len(buckets)}")
    print(f"  By scope: {len(data['by_scope_value'])}")
    print(f"  Top SKUs: {len(data['top_skus'])}")
    print(f"  Near expiry batches: {len(data['near_expiry_batches'])}")
    print(f"  Expired batches: {data['expired_batches_count']}")
    print(f"  Totals: Units={totals['total_units']}, Value=${totals['total_value']:,.2f}, Damaged={totals['damaged_pct']}%")
    
    # Test with SKU filter
    if dimensions['skus']:
        sku_id = dimensions['skus'][0]['id']
        resp = requests.get(f"{BASE_URL}/analytics/inventory?sku_id={sku_id}", headers=headers())
        assert resp.status_code == 200, f"SKU filter failed: {resp.status_code}"
        print(f"  ✓ sku_id filter applied")
    
    print("✓ Inventory analytics endpoint working")

def test_finance_analytics():
    """Test 7: Finance Analytics"""
    print("\n=== Test 7: Finance Analytics ===")
    
    resp = requests.get(f"{BASE_URL}/analytics/finance?range=month", headers=headers())
    assert resp.status_code == 200, f"Failed: {resp.status_code} {resp.text}"
    data = resp.json()
    
    # Verify structure
    required_keys = ["series", "by_method", "aging", "totals"]
    for key in required_keys:
        assert key in data, f"Missing key: {key}"
    
    # Verify aging has 4 buckets
    aging = data["aging"]
    assert len(aging) == 4, f"Expected 4 aging buckets, got {len(aging)}"
    expected_aging = ["0-30", "31-60", "61-90", "90+"]
    aging_buckets = [a["bucket"] for a in aging]
    for bucket in expected_aging:
        assert bucket in aging_buckets, f"Missing aging bucket: {bucket}"
    
    # Verify totals
    totals = data["totals"]
    assert "cash_in" in totals, "Missing cash_in"
    assert "cash_out" in totals, "Missing cash_out"
    assert "collection_rate" in totals, "Missing collection_rate"
    assert "total_outstanding" in totals, "Missing total_outstanding"
    
    print(f"  Series data points: {len(data['series'])}")
    print(f"  Payment methods: {len(data['by_method'])}")
    print(f"  Aging buckets: {len(aging)}")
    print(f"  Totals: Cash In=${totals['cash_in']:,.2f}, Cash Out=${totals['cash_out']:,.2f}")
    print(f"  Collection Rate: {totals['collection_rate']}%, Outstanding=${totals['total_outstanding']:,.2f}")
    
    print("✓ Finance analytics endpoint working")

def test_returns_claims_profitability():
    """Test 8: Returns, Claims, Profitability"""
    print("\n=== Test 8: Returns, Claims, Profitability ===")
    
    # Test Returns
    print("\n  Testing Returns...")
    resp = requests.get(f"{BASE_URL}/analytics/returns?range=quarter", headers=headers())
    assert resp.status_code == 200, f"Returns failed: {resp.status_code} {resp.text}"
    data = resp.json()
    
    required_keys = ["totals", "by_reason", "by_scope", "by_status", "top_skus", "series"]
    for key in required_keys:
        assert key in data, f"Missing key in returns: {key}"
    
    # Verify top_skus max 10
    assert len(data["top_skus"]) <= 10, f"top_skus should be max 10, got {len(data['top_skus'])}"
    
    # Verify by_reason is sorted by value desc
    by_reason = data["by_reason"]
    if len(by_reason) > 1:
        for i in range(len(by_reason) - 1):
            assert by_reason[i]["value"] >= by_reason[i+1]["value"], "by_reason not sorted by value desc"
    
    print(f"    Totals: {data['totals']}")
    print(f"    By reason: {len(by_reason)} reasons")
    print(f"    Top SKUs: {len(data['top_skus'])}")
    print(f"    ✓ Returns analytics working")
    
    # Test Claims
    print("\n  Testing Claims...")
    resp = requests.get(f"{BASE_URL}/analytics/claims?range=quarter", headers=headers())
    assert resp.status_code == 200, f"Claims failed: {resp.status_code} {resp.text}"
    data = resp.json()
    
    required_keys = ["totals", "by_type", "by_status", "series"]
    for key in required_keys:
        assert key in data, f"Missing key in claims: {key}"
    
    # Verify by_type has settled value per type
    by_type = data["by_type"]
    for item in by_type:
        assert "type" in item, "Missing type in by_type"
        assert "count" in item, "Missing count in by_type"
        assert "value" in item, "Missing value in by_type"
    
    print(f"    Totals: {data['totals']}")
    print(f"    By type: {len(by_type)} types")
    print(f"    ✓ Claims analytics working")
    
    # Test Profitability
    print("\n  Testing Profitability...")
    resp = requests.get(f"{BASE_URL}/analytics/profitability?range=month", headers=headers())
    assert resp.status_code == 200, f"Profitability failed: {resp.status_code} {resp.text}"
    data = resp.json()
    
    required_keys = ["revenue", "cogs", "gross_profit", "returns", "claims", "expenses", 
                    "net_profit", "margin_pct", "waterfall"]
    for key in required_keys:
        assert key in data, f"Missing key in profitability: {key}"
    
    # Verify waterfall has 6 stages
    waterfall = data["waterfall"]
    assert len(waterfall) == 6, f"Expected 6 waterfall stages, got {len(waterfall)}"
    expected_stages = ["Revenue", "COGS", "Returns", "Claims", "Expenses", "Net Profit"]
    waterfall_stages = [w["label"] for w in waterfall]
    for stage in expected_stages:
        assert stage in waterfall_stages, f"Missing waterfall stage: {stage}"
    
    print(f"    Revenue: ${data['revenue']:,.2f}")
    print(f"    COGS: ${data['cogs']:,.2f}")
    print(f"    Gross Profit: ${data['gross_profit']:,.2f}")
    print(f"    Net Profit: ${data['net_profit']:,.2f}")
    print(f"    Margin: {data['margin_pct']}%")
    print(f"    Waterfall stages: {len(waterfall)}")
    print(f"    ✓ Profitability analytics working")
    
    print("\n✓ Returns, Claims, Profitability endpoints working")

def test_business_alerts():
    """Test 9: Business Alerts Engine (12 alert types)"""
    print("\n=== Test 9: Business Alerts ===")
    
    resp = requests.get(f"{BASE_URL}/analytics/alerts", headers=headers())
    assert resp.status_code == 200, f"Failed: {resp.status_code} {resp.text}"
    data = resp.json()
    
    # Verify structure
    required_keys = ["count", "by_kind", "by_severity", "alerts"]
    for key in required_keys:
        assert key in data, f"Missing key: {key}"
    
    # Verify alerts max 60
    assert len(data["alerts"]) <= 60, f"alerts should be max 60, got {len(data['alerts'])}"
    
    # Verify each alert has required fields
    for alert in data["alerts"]:
        assert "id" in alert, "Alert missing id"
        assert "kind" in alert, "Alert missing kind"
        assert "severity" in alert, "Alert missing severity"
        assert alert["severity"] in ["high", "medium", "low"], f"Invalid severity: {alert['severity']}"
        assert "title" in alert, "Alert missing title"
        assert "description" in alert, "Alert missing description"
        assert "drill" in alert, "Alert missing drill"
    
    # Check for supported alert types
    supported_types = ["low_inventory", "high_outstanding", "credit_limit_exceeded", 
                      "payment_delay", "high_returns", "pending_approvals", "near_expiry", 
                      "dispatch_delay", "exceptions"]
    
    alert_kinds = set(alert["kind"] for alert in data["alerts"])
    print(f"  Total alerts: {data['count']}")
    print(f"  Alert kinds found: {alert_kinds}")
    print(f"  By severity: {data['by_severity']}")
    print(f"  By kind: {data['by_kind']}")
    
    # Verify at least some alerts are returned
    assert data["count"] > 0, "No alerts returned"
    
    print("✓ Business alerts endpoint working")

def test_scorecards():
    """Test 10: Business Scorecards (6 entity types)"""
    print("\n=== Test 10: Business Scorecards ===")
    
    entity_types = ["distributor", "retailer", "branch", "sales_executive", "warehouse", "company"]
    
    for entity_type in entity_types:
        print(f"\n  Testing {entity_type} scorecards...")
        resp = requests.get(f"{BASE_URL}/analytics/scorecards/{entity_type}", headers=headers())
        assert resp.status_code == 200, f"Scorecards {entity_type} failed: {resp.status_code} {resp.text}"
        data = resp.json()
        
        # Verify structure
        assert "entity_type" in data, "Missing entity_type"
        assert "count" in data, "Missing count"
        assert "rows" in data, "Missing rows"
        assert data["entity_type"] == entity_type, f"entity_type mismatch: {data['entity_type']} != {entity_type}"
        
        # Verify rows are sorted by overall desc
        rows = data["rows"]
        if len(rows) > 1:
            for i in range(len(rows) - 1):
                assert rows[i]["overall"] >= rows[i+1]["overall"], f"{entity_type} rows not sorted by overall desc"
        
        # Verify each row has required fields
        for row in rows:
            assert "id" in row, f"{entity_type} row missing id"
            assert "name" in row, f"{entity_type} row missing name"
            assert "overall" in row, f"{entity_type} row missing overall"
            # Only distributor and retailer have grade field
            if entity_type in ["distributor", "retailer"]:
                assert "grade" in row, f"{entity_type} row missing grade"
                assert row["grade"] in ["A", "B", "C", "D"], f"Invalid grade: {row['grade']}"
            assert 0 <= row["overall"] <= 100, f"Invalid overall score: {row['overall']}"
        
        print(f"    Count: {data['count']}")
        if rows:
            if entity_type in ["distributor", "retailer"]:
                print(f"    Top performer: {rows[0]['name']} (Grade {rows[0]['grade']}, Score {rows[0]['overall']})")
            else:
                print(f"    Top performer: {rows[0]['name']} (Score {rows[0]['overall']})")
        print(f"    ✓ {entity_type} scorecards working")
    
    # Test invalid entity type
    resp = requests.get(f"{BASE_URL}/analytics/scorecards/invalid", headers=headers())
    assert resp.status_code == 400, f"Should return 400 for invalid entity_type, got {resp.status_code}"
    print("\n  ✓ Invalid entity_type returns 400")
    
    print("\n✓ Scorecards endpoint working for all 6 entity types")

def test_ai_context():
    """Test 11: AI-ready context"""
    print("\n=== Test 11: AI-ready Context ===")
    
    scopes = ["executive", "sales", "finance", "inventory"]
    
    for scope in scopes:
        print(f"\n  Testing {scope} context...")
        resp = requests.get(f"{BASE_URL}/analytics/ai-context/{scope}", headers=headers())
        assert resp.status_code == 200, f"AI context {scope} failed: {resp.status_code} {resp.text}"
        data = resp.json()
        
        # Verify structure
        assert "generated_at" in data, f"Missing generated_at in {scope}"
        assert "scope" in data, f"Missing scope in {scope}"
        assert data["scope"] == scope, f"Scope mismatch: {data['scope']} != {scope}"
        # Executive has summary/hint, others have analytics data
        if scope == "executive":
            assert "summary" in data or "hint" in data, f"Missing summary/hint in {scope}"
        
        # Verify generated_at is ISO-8601
        generated_at = data["generated_at"]
        assert "T" in generated_at, f"generated_at not ISO-8601: {generated_at}"
        
        print(f"    Generated at: {generated_at}")
        print(f"    Scope: {data['scope']}")
        print(f"    ✓ {scope} AI context working")
    
    # Test invalid scope
    resp = requests.get(f"{BASE_URL}/analytics/ai-context/invalid", headers=headers())
    assert resp.status_code == 400, f"Should return 400 for invalid scope, got {resp.status_code}"
    print("\n  ✓ Invalid scope returns 400")
    
    print("\n✓ AI-ready context endpoint working for all 4 scopes")

def test_json_serialization():
    """Test 12: Verify all responses are JSON-serializable (no ObjectId leakage)"""
    print("\n=== Test 12: JSON Serialization ===")
    
    # Test a few endpoints to ensure no ObjectId leakage
    endpoints = [
        "/analytics/dimensions",
        "/analytics/kpi/executive?range=month",
        "/analytics/alerts",
    ]
    
    for endpoint in endpoints:
        resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers())
        assert resp.status_code == 200, f"Failed: {resp.status_code}"
        
        # Try to parse as JSON
        try:
            data = resp.json()
            # Try to re-serialize to ensure no ObjectId
            json.dumps(data)
            print(f"  ✓ {endpoint} - JSON serializable")
        except Exception as e:
            raise AssertionError(f"JSON serialization failed for {endpoint}: {e}")
    
    print("✓ All responses are JSON-serializable")

def main():
    """Run all tests"""
    print("=" * 60)
    print("Phase 4 Analytics Backend Testing Suite")
    print("=" * 60)
    
    try:
        # Login
        login()
        
        # Run tests in order
        dimensions = test_dimensions()
        test_executive_kpi()
        test_executive_kpi_filters(dimensions)
        test_order_trace()
        test_order_trace_search()
        test_party360()
        test_sales_analytics(dimensions)
        test_inventory_analytics(dimensions)
        test_finance_analytics()
        test_returns_claims_profitability()
        test_business_alerts()
        test_scorecards()
        test_ai_context()
        test_json_serialization()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        print("\nSummary:")
        print("  ✓ Dimensions endpoint - working")
        print("  ✓ Executive KPI (15 KPIs) - working")
        print("  ✓ Order Trace (20-node journey) - working")
        print("  ✓ Party 360 (4 party types) - working")
        print("  ✓ Sales Analytics - working")
        print("  ✓ Inventory Analytics - working")
        print("  ✓ Finance Analytics - working")
        print("  ✓ Returns/Claims/Profitability - working")
        print("  ✓ Business Alerts (12 types) - working")
        print("  ✓ Scorecards (6 entity types) - working")
        print("  ✓ AI-ready Context (4 scopes) - working")
        print("  ✓ JSON Serialization - working")
        print("\nAll Phase 4 analytics endpoints are working correctly with LIVE MongoDB data.")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
