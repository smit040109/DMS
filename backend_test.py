#!/usr/bin/env python3
"""
GO OIL DMS Backend Testing Script
Tests newly added/changed endpoints for multi-module update (July 2025)
"""

import requests
import json
from datetime import datetime, date
import time

# Configuration
BASE_URL = "https://sales-ops-hub-30.preview.emergentagent.com/api"
PASSWORD = "GoOil@2026"

# Test credentials
CREDENTIALS = {
    "owner": "owner@gooil.com",
    "accountant": "accountant@gooil.com",
    "distributor1": "distributor1@gooil.com",
    "distributor2": "distributor2@gooil.com",
    "retailer1": "retailer1@gooil.com",
    "retailer2": "retailer2@gooil.com",
    "salesperson": "salesperson@gooil.com",
    "teamleader": "teamleader@gooil.com",
    "regionalmgr": "regionalmgr@gooil.com",
}

# Store tokens and user IDs
tokens = {}
user_ids = {}

def login(role):
    """Login and store token"""
    email = CREDENTIALS[role]
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        tokens[role] = data["token"]
        user_ids[role] = data["user"]["id"]
        print(f"✅ {role} logged in successfully (user_id: {user_ids[role]})")
        return True
    else:
        print(f"❌ {role} login failed: {response.status_code} - {response.text}")
        return False

def get_headers(role):
    """Get authorization headers for a role"""
    return {"Authorization": f"Bearer {tokens[role]}"}

def test_punch_reopen():
    """Test Item 1: Punch Reopen Flow"""
    print("\n" + "="*80)
    print("TEST 1: PUNCH REOPEN (Item 1)")
    print("="*80)
    
    # Step 1: Salesperson punch in
    print("\n1.1: Salesperson punch in...")
    response = requests.post(
        f"{BASE_URL}/dms/punch/in",
        headers=get_headers("salesperson"),
        json={"gps_lat": 28.61, "gps_lng": 77.20}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ Punch in successful")
    else:
        print(f"   Response: {response.text}")
    
    # Step 2: Salesperson punch out
    print("\n1.2: Salesperson punch out...")
    response = requests.post(
        f"{BASE_URL}/dms/punch/out",
        headers=get_headers("salesperson"),
        json={"gps_lat": 28.62, "gps_lng": 77.21}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ Punch out successful")
    else:
        print(f"   Response: {response.text}")
    
    # Step 3: Try to punch in again (should fail with 400)
    print("\n1.3: Salesperson tries to punch in again (should fail)...")
    response = requests.post(
        f"{BASE_URL}/dms/punch/in",
        headers=get_headers("salesperson"),
        json={"gps_lat": 28.61, "gps_lng": 77.20}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 400:
        print(f"   ✅ Correctly blocked with 400")
        print(f"   Message: {response.json().get('detail', 'No detail')}")
    else:
        print(f"   ❌ Expected 400, got {response.status_code}")
        print(f"   Response: {response.text}")
    
    # Step 4: Owner reopens punch for salesperson
    print(f"\n1.4: Owner reopens punch for salesperson (user_id: {user_ids['salesperson']})...")
    response = requests.post(
        f"{BASE_URL}/dms/owner/punch/reopen/{user_ids['salesperson']}",
        headers=get_headers("owner")
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Reopen successful: {data}")
    else:
        print(f"   ❌ Reopen failed: {response.text}")
    
    # Step 5: Salesperson punch in again (should succeed now)
    print("\n1.5: Salesperson punch in again (should succeed now)...")
    response = requests.post(
        f"{BASE_URL}/dms/punch/in",
        headers=get_headers("salesperson"),
        json={"gps_lat": 28.61, "gps_lng": 77.20}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ Punch in successful after reopen")
    else:
        print(f"   ❌ Punch in failed: {response.text}")
    
    # Step 6: Check punch/today for flags
    print("\n1.6: Check GET /api/dms/punch/today for flags...")
    response = requests.get(
        f"{BASE_URL}/dms/punch/today",
        headers=get_headers("salesperson")
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Punch today data:")
        print(f"      can_punch_in: {data.get('can_punch_in')}")
        print(f"      reopen_granted: {data.get('reopen_granted')}")
    else:
        print(f"   Response: {response.text}")

def test_attendance_role_aware():
    """Test Item 7: Attendance Role-Aware"""
    print("\n" + "="*80)
    print("TEST 2: ATTENDANCE ROLE-AWARE (Item 7)")
    print("="*80)
    
    # Test salesperson view
    print("\n2.1: Salesperson GET /api/dms/attendance (should see only own)...")
    response = requests.get(
        f"{BASE_URL}/dms/attendance",
        headers=get_headers("salesperson")
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        rows = data if isinstance(data, list) else data.get('data', [])
        print(f"   ✅ Returned {len(rows)} rows")
        if len(rows) > 0:
            print(f"      Sample row: user_id={rows[0].get('user_id')}, name={rows[0].get('name')}")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    # Test team leader view
    print("\n2.2: Team Leader GET /api/dms/attendance (own + assigned SPs)...")
    response = requests.get(
        f"{BASE_URL}/dms/attendance",
        headers=get_headers("teamleader")
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        rows = data if isinstance(data, list) else data.get('data', [])
        print(f"   ✅ Returned {len(rows)} rows")
        if len(rows) > 0:
            print(f"      Sample row: user_id={rows[0].get('user_id')}, name={rows[0].get('name')}, role={rows[0].get('role')}")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    # Test regional manager view
    print("\n2.3: Regional Manager GET /api/dms/attendance (own + TLs + SPs)...")
    response = requests.get(
        f"{BASE_URL}/dms/attendance",
        headers=get_headers("regionalmgr")
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        rows = data if isinstance(data, list) else data.get('data', [])
        print(f"   ✅ Returned {len(rows)} rows")
        if len(rows) > 0:
            print(f"      Sample row: user_id={rows[0].get('user_id')}, name={rows[0].get('name')}, role={rows[0].get('role')}")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    # Test owner view
    print("\n2.4: Owner GET /api/dms/attendance (all field staff + can_reopen flag)...")
    response = requests.get(
        f"{BASE_URL}/dms/attendance",
        headers=get_headers("owner")
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        rows = data if isinstance(data, list) else data.get('data', [])
        print(f"   ✅ Returned {len(rows)} rows")
        if len(rows) > 0:
            sample = rows[0]
            print(f"      Sample row: user_id={sample.get('user_id')}, name={sample.get('name')}, role={sample.get('role')}")
            print(f"      can_reopen field present: {'can_reopen' in sample}")
    else:
        print(f"   ❌ Failed: {response.text}")

def test_expenses_approval_flow():
    """Test Item 2: Expenses Approval Flow"""
    print("\n" + "="*80)
    print("TEST 3: EXPENSES APPROVAL FLOW (Item 2)")
    print("="*80)
    
    # Step 1: Salesperson creates expense (status should be "submitted", receipt_url null)
    print("\n3.1: Salesperson creates expense (status should be 'submitted')...")
    expense_data = {
        "category": "Travel",
        "amount": 500,
        "date": date.today().isoformat(),
        "description": "Test expense for approval flow",
        "status": "Approved",  # Try to set approved (should be overridden)
        "receipt_url": "http://fake.com/receipt.jpg"  # Should be nullified
    }
    response = requests.post(
        f"{BASE_URL}/dms/expenses",
        headers=get_headers("salesperson"),
        json=expense_data
    )
    print(f"   Status: {response.status_code}")
    expense_id = None
    if response.status_code == 200:
        data = response.json()
        expense_id = data.get("id")
        print(f"   ✅ Expense created: {expense_id}")
        print(f"      Status: {data.get('status')} (should be 'submitted')")
        print(f"      Receipt URL: {data.get('receipt_url')} (should be null)")
        if data.get('status') == 'submitted' and data.get('receipt_url') is None:
            print(f"   ✅ Server correctly overrode status and receipt_url")
        else:
            print(f"   ❌ Server did not override correctly")
    else:
        print(f"   ❌ Failed: {response.text}")
        return
    
    # Step 2: Regional Manager sees it in their expenses
    print("\n3.2: Regional Manager GET /api/dms/expenses (should include SP's expense)...")
    response = requests.get(
        f"{BASE_URL}/dms/expenses",
        headers=get_headers("regionalmgr")
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        expenses = data if isinstance(data, list) else data.get('data', [])
        found = any(e.get('id') == expense_id for e in expenses)
        print(f"   ✅ Returned {len(expenses)} expenses")
        print(f"      SP's expense found: {found}")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    # Step 3: Regional Manager approves (status -> "rsm_approved")
    print("\n3.3: Regional Manager approves expense...")
    response = requests.post(
        f"{BASE_URL}/dms/expenses/{expense_id}/action",
        headers=get_headers("regionalmgr"),
        json={"action": "approve"}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Approval successful")
        print(f"      New status: {data.get('status')} (should be 'rsm_approved')")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    # Step 4: Owner approves (status -> "approved")
    print("\n3.4: Owner approves expense...")
    response = requests.post(
        f"{BASE_URL}/dms/expenses/{expense_id}/action",
        headers=get_headers("owner"),
        json={"action": "approve"}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Approval successful")
        print(f"      New status: {data.get('status')} (should be 'approved')")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    # Step 5: Create another expense and RSM rejects it
    print("\n3.5: Salesperson creates another expense for rejection test...")
    expense_data2 = {
        "category": "Office Supplies",
        "amount": 200,
        "date": date.today().isoformat(),
        "description": "Test expense for rejection"
    }
    response = requests.post(
        f"{BASE_URL}/dms/expenses",
        headers=get_headers("salesperson"),
        json=expense_data2
    )
    expense_id2 = None
    if response.status_code == 200:
        expense_id2 = response.json().get("id")
        print(f"   ✅ Expense created: {expense_id2}")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    if expense_id2:
        print("\n3.6: Regional Manager rejects expense...")
        response = requests.post(
            f"{BASE_URL}/dms/expenses/{expense_id2}/action",
            headers=get_headers("regionalmgr"),
            json={"action": "reject", "note": "Not approved"}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Rejection successful")
            print(f"      New status: {data.get('status')} (should be 'rejected')")
        else:
            print(f"   ❌ Failed: {response.text}")
    
    # Step 6: Negative test - Owner tries to action a "submitted" expense (should fail)
    print("\n3.7: Create expense and owner tries to action it directly (should fail)...")
    expense_data3 = {
        "category": "Travel",
        "amount": 100,
        "date": date.today().isoformat(),
        "description": "Test for negative case"
    }
    response = requests.post(
        f"{BASE_URL}/dms/expenses",
        headers=get_headers("salesperson"),
        json=expense_data3
    )
    expense_id3 = None
    if response.status_code == 200:
        expense_id3 = response.json().get("id")
        print(f"   ✅ Expense created: {expense_id3}")
        
        # Owner tries to approve submitted expense
        response = requests.post(
            f"{BASE_URL}/dms/expenses/{expense_id3}/action",
            headers=get_headers("owner"),
            json={"action": "approve"}
        )
        print(f"   Owner action status: {response.status_code}")
        if response.status_code == 400:
            print(f"   ✅ Correctly blocked with 400")
            print(f"      Message: {response.json().get('detail', 'No detail')}")
        else:
            print(f"   ❌ Expected 400, got {response.status_code}")
    
    # Step 7: Negative test - RSM tries to action an "rsm_approved" expense (should fail)
    print("\n3.8: RSM tries to action an already rsm_approved expense (should fail)...")
    if expense_id:  # Use the first expense which is now rsm_approved or approved
        response = requests.post(
            f"{BASE_URL}/dms/expenses/{expense_id}/action",
            headers=get_headers("regionalmgr"),
            json={"action": "approve"}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 400:
            print(f"   ✅ Correctly blocked with 400")
            print(f"      Message: {response.json().get('detail', 'No detail')}")
        else:
            print(f"   ⚠️  Got {response.status_code} (may be already approved)")

def test_rsm_my_retailers():
    """Test Item 6: RSM My Retailers"""
    print("\n" + "="*80)
    print("TEST 4: RSM MY RETAILERS (Item 6)")
    print("="*80)
    
    print("\n4.1: Regional Manager GET /api/dms/rm/retailers...")
    response = requests.get(
        f"{BASE_URL}/dms/rm/retailers",
        headers=get_headers("regionalmgr")
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        retailers = data if isinstance(data, list) else data.get('data', [])
        print(f"   ✅ Returned {len(retailers)} retailers")
        if len(retailers) > 0:
            sample = retailers[0]
            print(f"      Sample: name={sample.get('name')}, distributor_name={sample.get('distributor_name')}")
            print(f"              outstanding={sample.get('outstanding')}, onboarded_by_name={sample.get('onboarded_by_name')}")
            # Check required fields
            required_fields = ['name', 'distributor_name', 'outstanding', 'onboarded_by_name']
            missing = [f for f in required_fields if f not in sample]
            if not missing:
                print(f"   ✅ All required fields present")
            else:
                print(f"   ⚠️  Missing fields: {missing}")
    else:
        print(f"   ❌ Failed: {response.text}")

def test_distributor_order_flow():
    """Test Item 8: Distributor Order -> Invoice -> Dispatch -> Challan"""
    print("\n" + "="*80)
    print("TEST 5: DISTRIBUTOR ORDER -> INVOICE -> DISPATCH -> CHALLAN (Item 8)")
    print("="*80)
    
    # Step 1: Find or create a pending secondary order
    print("\n5.1: Finding existing pending secondary order...")
    response = requests.get(
        f"{BASE_URL}/dms/secondary-orders",
        headers=get_headers("distributor1")
    )
    
    order_id = None
    if response.status_code == 200:
        data = response.json()
        orders = data if isinstance(data, list) else data.get('data', [])
        pending_orders = [o for o in orders if o.get('status') == 'pending']
        
        if pending_orders:
            order_id = pending_orders[0]['id']
            print(f"   ✅ Found pending order: {order_id}")
        else:
            print(f"   No pending orders found. Need to create one...")
            # Get a retailer and product to create order
            retailers_resp = requests.get(f"{BASE_URL}/dms/retailers", headers=get_headers("distributor1"))
            products_resp = requests.get(f"{BASE_URL}/dms/retailer/browse", headers=get_headers("distributor1"))
            
            if retailers_resp.status_code == 200 and products_resp.status_code == 200:
                retailers_data = retailers_resp.json()
                retailers = retailers_data if isinstance(retailers_data, list) else retailers_data.get('data', [])
                products_data = products_resp.json()
                products = products_data if isinstance(products_data, list) else products_data.get('data', [])
                
                if retailers and products:
                    retailer_id = retailers[0]['id']
                    product = products[0]
                    
                    order_data = {
                        "retailer_id": retailer_id,
                        "items": [{
                            "product_id": product['id'],
                            "qty_boxes": 2,
                            "qty_pcs": 0,
                            "unit_price": product['unit_price']
                        }]
                    }
                    
                    create_resp = requests.post(
                        f"{BASE_URL}/dms/secondary-orders",
                        headers=get_headers("distributor1"),
                        json=order_data
                    )
                    
                    if create_resp.status_code == 200:
                        order_id = create_resp.json().get('id')
                        print(f"   ✅ Created new order: {order_id}")
                    else:
                        print(f"   ❌ Failed to create order: {create_resp.text}")
    
    if not order_id:
        print("   ❌ Could not find or create a pending order. Skipping flow test.")
        return
    
    # Step 2: Try to dispatch BEFORE invoicing (should fail with 400)
    print(f"\n5.2: Try to dispatch order {order_id} BEFORE invoicing (should fail)...")
    response = requests.post(
        f"{BASE_URL}/dms/secondary-orders/{order_id}/dispatch",
        headers=get_headers("distributor1"),
        json={}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 400:
        print(f"   ✅ Correctly blocked with 400")
        print(f"      Message: {response.json().get('detail', 'No detail')}")
    else:
        print(f"   ⚠️  Expected 400, got {response.status_code}")
        print(f"      Response: {response.text}")
    
    # Step 3: Generate invoice
    print(f"\n5.3: Generate invoice for order {order_id}...")
    response = requests.post(
        f"{BASE_URL}/dms/secondary-orders/{order_id}/invoice",
        headers=get_headers("distributor1"),
        json={}
    )
    print(f"   Status: {response.status_code}")
    bill_id = None
    if response.status_code == 200:
        data = response.json()
        bill_id = data.get('bill_id')
        invoice_no = data.get('invoice_no')
        print(f"   ✅ Invoice generated")
        print(f"      invoice_no: {invoice_no} (should be short format like INV-0001)")
        print(f"      bill_id: {bill_id}")
        print(f"      status: {data.get('status')} (should be 'invoiced')")
    else:
        print(f"   ❌ Failed: {response.text}")
        return
    
    # Step 4: Get distributor stock before dispatch
    print(f"\n5.4: Getting distributor stock before dispatch...")
    response = requests.get(
        f"{BASE_URL}/dms/distributor/stock",
        headers=get_headers("distributor1")
    )
    stock_before = {}
    if response.status_code == 200:
        data = response.json()
        stock_items = data if isinstance(data, list) else data.get('data', [])
        for item in stock_items:
            stock_before[item['product_id']] = item.get('qty_boxes', 0)
        print(f"   ✅ Got stock for {len(stock_before)} products")
    
    # Step 5: Dispatch order
    print(f"\n5.5: Dispatch order {order_id}...")
    response = requests.post(
        f"{BASE_URL}/dms/secondary-orders/{order_id}/dispatch",
        headers=get_headers("distributor1"),
        json={}
    )
    print(f"   Status: {response.status_code}")
    challan_id = None
    challan_no = None
    if response.status_code == 200:
        data = response.json()
        challan_id = data.get('challan_id')
        challan_no = data.get('challan_no')
        print(f"   ✅ Dispatch successful")
        print(f"      status: {data.get('status')} (should be 'dispatched')")
        print(f"      challan_no: {challan_no} (should be short format like DC-0001)")
        print(f"      challan_id: {challan_id}")
    else:
        print(f"   ❌ Failed: {response.text}")
        return
    
    # Step 6: Verify distributor stock decreased
    print(f"\n5.6: Verify distributor stock decreased...")
    response = requests.get(
        f"{BASE_URL}/dms/distributor/stock",
        headers=get_headers("distributor1")
    )
    if response.status_code == 200:
        data = response.json()
        stock_items = data if isinstance(data, list) else data.get('data', [])
        stock_after = {}
        for item in stock_items:
            stock_after[item['product_id']] = item.get('qty_boxes', 0)
        
        # Compare
        decreased = False
        for product_id, before_qty in stock_before.items():
            after_qty = stock_after.get(product_id, 0)
            if after_qty < before_qty:
                print(f"   ✅ Stock decreased for product {product_id}: {before_qty} -> {after_qty}")
                decreased = True
        
        if not decreased:
            print(f"   ⚠️  No stock decrease detected (may be testing with different products)")
    
    # Step 7: Get challan
    print(f"\n5.7: GET /api/dms/secondary-orders/{order_id}/challan...")
    response = requests.get(
        f"{BASE_URL}/dms/secondary-orders/{order_id}/challan",
        headers=get_headers("distributor1")
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Challan retrieved")
        print(f"      challan_no: {data.get('challan_no')}")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    # Step 8: Print challan
    if challan_id:
        print(f"\n5.8: GET /api/dms/print/challan/{challan_id}...")
        response = requests.get(
            f"{BASE_URL}/dms/print/challan/{challan_id}",
            headers=get_headers("distributor1")
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ Challan print endpoint working")
        else:
            print(f"   ❌ Failed: {response.text}")

def test_documents_side_effects():
    """Test Item 9: Documents Side-Effects"""
    print("\n" + "="*80)
    print("TEST 6: DOCUMENTS SIDE-EFFECTS (Item 9)")
    print("="*80)
    
    # Step 1: Try to create delivery_challan (should be blocked)
    print("\n6.1: Try to create delivery_challan document (should be blocked)...")
    response = requests.post(
        f"{BASE_URL}/dms/documents",
        headers=get_headers("distributor1"),
        json={
            "type": "delivery_challan",
            "party_type": "retailer",
            "party_id": "test-id",
            "date": date.today().isoformat(),
            "items": []
        }
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 400:
        print(f"   ✅ Correctly blocked with 400")
        print(f"      Message: {response.json().get('detail', 'No detail')}")
    else:
        print(f"   ❌ Expected 400, got {response.status_code}")
    
    # Get a retailer and product for testing
    print("\n6.2: Getting retailer and product for testing...")
    retailers_resp = requests.get(f"{BASE_URL}/dms/retailers", headers=get_headers("distributor1"))
    products_resp = requests.get(f"{BASE_URL}/dms/products", headers=get_headers("distributor1"))
    
    retailer_id = None
    product_id = None
    distributor_id = None
    
    if retailers_resp.status_code == 200:
        retailers_data = retailers_resp.json()
        retailers = retailers_data if isinstance(retailers_data, list) else retailers_data.get('data', [])
        if retailers:
            retailer_id = retailers[0]['id']
            print(f"   ✅ Got retailer: {retailer_id}")
    
    if products_resp.status_code == 200:
        products_data = products_resp.json()
        products = products_data if isinstance(products_data, list) else products_data.get('data', [])
        if products:
            product_id = products[0]['id']
            print(f"   ✅ Got product: {product_id}")
    
    # Get distributor ID
    me_resp = requests.get(f"{BASE_URL}/auth/me", headers=get_headers("distributor1"))
    if me_resp.status_code == 200:
        user_data = me_resp.json()
        distributor_id = user_data.get('distributor_id')
        if not distributor_id:
            # Try to get from distributors list
            dist_resp = requests.get(f"{BASE_URL}/dms/distributors", headers=get_headers("owner"))
            if dist_resp.status_code == 200:
                dist_data = dist_resp.json()
                dists = dist_data if isinstance(dist_data, list) else dist_data.get('data', [])
                if dists:
                    distributor_id = dists[0]['id']
        print(f"   ✅ Got distributor_id: {distributor_id}")
    
    if not (retailer_id and product_id and distributor_id):
        print("   ❌ Could not get required IDs. Skipping side-effects tests.")
        return
    
    # Get distributor stock before
    print("\n6.3: Getting distributor stock before sale_return...")
    stock_resp = requests.get(f"{BASE_URL}/dms/distributor/stock", headers=get_headers("distributor1"))
    stock_before = {}
    if stock_resp.status_code == 200:
        stock_data = stock_resp.json()
        stock_items = stock_data if isinstance(stock_data, list) else stock_data.get('data', [])
        for item in stock_items:
            stock_before[item['product_id']] = item.get('qty_boxes', 0)
        print(f"   ✅ Stock before for product {product_id}: {stock_before.get(product_id, 0)} boxes")
    
    # Step 2: Create sale_return from retailer (should INCREASE distributor stock)
    print("\n6.4: Create sale_return from retailer (should INCREASE distributor stock)...")
    response = requests.post(
        f"{BASE_URL}/dms/documents",
        headers=get_headers("distributor1"),
        json={
            "type": "sale_return",
            "party_type": "retailer",
            "party_id": retailer_id,
            "date": date.today().isoformat(),
            "items": [{
                "product_id": product_id,
                "qty": 2,
                "unit_price": 100,
                "subtotal": 200
            }]
        }
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Sale return created: {data.get('doc_no')}")
        
        # Check stock increased
        stock_resp = requests.get(f"{BASE_URL}/dms/distributor/stock", headers=get_headers("distributor1"))
        if stock_resp.status_code == 200:
            stock_data = stock_resp.json()
            stock_items = stock_data if isinstance(stock_data, list) else stock_data.get('data', [])
            for item in stock_items:
                if item['product_id'] == product_id:
                    new_stock = item.get('qty_boxes', 0)
                    old_stock = stock_before.get(product_id, 0)
                    print(f"   Stock after: {new_stock} boxes (was {old_stock})")
                    if new_stock > old_stock:
                        print(f"   ✅ Stock INCREASED by {new_stock - old_stock} boxes")
                    else:
                        print(f"   ⚠️  Stock did not increase as expected")
                    break
    else:
        print(f"   ❌ Failed: {response.text}")
    
    # Step 3: Create sale_return TO distributor (should DECREASE distributor stock)
    print("\n6.5: Create sale_return TO distributor (should DECREASE distributor stock)...")
    # Get current stock
    stock_resp = requests.get(f"{BASE_URL}/dms/distributor/stock", headers=get_headers("distributor1"))
    stock_before_2 = {}
    if stock_resp.status_code == 200:
        stock_data = stock_resp.json()
        stock_items = stock_data if isinstance(stock_data, list) else stock_data.get('data', [])
        for item in stock_items:
            stock_before_2[item['product_id']] = item.get('qty_boxes', 0)
    
    response = requests.post(
        f"{BASE_URL}/dms/documents",
        headers=get_headers("distributor1"),
        json={
            "type": "sale_return",
            "party_type": "distributor",
            "party_id": distributor_id,
            "date": date.today().isoformat(),
            "items": [{
                "product_id": product_id,
                "qty": 1,
                "unit_price": 100,
                "subtotal": 100
            }]
        }
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Sale return created: {data.get('doc_no')}")
        
        # Check stock decreased
        stock_resp = requests.get(f"{BASE_URL}/dms/distributor/stock", headers=get_headers("distributor1"))
        if stock_resp.status_code == 200:
            stock_data = stock_resp.json()
            stock_items = stock_data if isinstance(stock_data, list) else stock_data.get('data', [])
            for item in stock_items:
                if item['product_id'] == product_id:
                    new_stock = item.get('qty_boxes', 0)
                    old_stock = stock_before_2.get(product_id, 0)
                    print(f"   Stock after: {new_stock} boxes (was {old_stock})")
                    if new_stock < old_stock:
                        print(f"   ✅ Stock DECREASED by {old_stock - new_stock} boxes")
                    else:
                        print(f"   ⚠️  Stock did not decrease as expected")
                    break
    else:
        print(f"   ❌ Failed: {response.text}")
    
    # Step 4: Create credit_note for retailer (should appear in retailer ledger)
    print("\n6.6: Create credit_note for retailer (should appear in ledger)...")
    response = requests.post(
        f"{BASE_URL}/dms/documents",
        headers=get_headers("distributor1"),
        json={
            "type": "credit_note",
            "party_type": "retailer",
            "party_id": retailer_id,
            "date": date.today().isoformat(),
            "items": [{
                "product_id": product_id,
                "qty": 1,
                "unit_price": 100,
                "subtotal": 100
            }]
        }
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        cn_id = data.get('id')
        print(f"   ✅ Credit note created: {data.get('doc_no')}")
        
        # Check in retailer ledger
        ledger_resp = requests.get(
            f"{BASE_URL}/dms/ledger/secondary",
            headers=get_headers("distributor1")
        )
        if ledger_resp.status_code == 200:
            ledger_data = ledger_resp.json()
            entries = ledger_data.get('entries', [])
            found = any(e.get('kind') == 'credit_note' for e in entries)
            print(f"   Credit note in ledger: {found}")
            if found:
                print(f"   ✅ Credit note appears in retailer ledger")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    # Step 5: Create debit_note for distributor (should appear in primary ledger)
    print("\n6.7: Create debit_note for distributor (should appear in primary ledger)...")
    response = requests.post(
        f"{BASE_URL}/dms/documents",
        headers=get_headers("distributor1"),
        json={
            "type": "debit_note",
            "party_type": "distributor",
            "party_id": distributor_id,
            "date": date.today().isoformat(),
            "items": [{
                "product_id": product_id,
                "qty": 1,
                "unit_price": 100,
                "subtotal": 100
            }]
        }
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Debit note created: {data.get('doc_no')}")
        
        # Check in primary ledger
        ledger_resp = requests.get(
            f"{BASE_URL}/dms/ledger/primary",
            headers=get_headers("distributor1")
        )
        if ledger_resp.status_code == 200:
            ledger_data = ledger_resp.json()
            entries = ledger_data.get('entries', [])
            found = any(e.get('kind') == 'debit_note' for e in entries)
            print(f"   Debit note in ledger: {found}")
            if found:
                print(f"   ✅ Debit note appears in primary ledger")
    else:
        print(f"   ❌ Failed: {response.text}")

def test_retailer_login_toggle():
    """Test Item 3: Retailer Login Toggle"""
    print("\n" + "="*80)
    print("TEST 7: RETAILER LOGIN TOGGLE (Item 3)")
    print("="*80)
    
    # Step 1: Get retailers list to check fields
    print("\n7.1: Owner GET /api/dms/retailers (check login_enabled and has_login fields)...")
    response = requests.get(
        f"{BASE_URL}/dms/retailers",
        headers=get_headers("owner")
    )
    print(f"   Status: {response.status_code}")
    retailer_id = None
    if response.status_code == 200:
        retailers_data = response.json()
        retailers = retailers_data if isinstance(retailers_data, list) else retailers_data.get('data', [])
        if retailers:
            sample = retailers[0]
            retailer_id = sample['id']
            print(f"   ✅ Returned {len(retailers)} retailers")
            print(f"      Sample retailer: {sample.get('name')}")
            print(f"      login_enabled: {sample.get('login_enabled')}")
            print(f"      has_login: {sample.get('has_login')}")
    else:
        print(f"   ❌ Failed: {response.text}")
        return
    
    if not retailer_id:
        print("   ❌ No retailers found. Skipping login toggle test.")
        return
    
    # Step 2: Disable login for retailer1
    print(f"\n7.2: Owner disables login for retailer {retailer_id}...")
    response = requests.put(
        f"{BASE_URL}/dms/retailers/{retailer_id}/login-access",
        headers=get_headers("owner"),
        json={"enabled": False}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ Login access disabled")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    # Step 3: Try to login as retailer1 (should fail with 403)
    print("\n7.3: Try to login as retailer1 (should fail with 403)...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": CREDENTIALS["retailer1"],
            "password": PASSWORD
        }
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 403:
        print(f"   ✅ Login correctly blocked with 403")
        print(f"      Message: {response.json().get('detail', 'No detail')}")
    else:
        print(f"   ❌ Expected 403, got {response.status_code}")
    
    # Step 4: Re-enable login
    print(f"\n7.4: Owner re-enables login for retailer {retailer_id}...")
    response = requests.put(
        f"{BASE_URL}/dms/retailers/{retailer_id}/login-access",
        headers=get_headers("owner"),
        json={"enabled": True}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ Login access re-enabled")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    # Step 5: Try to login again (should succeed)
    print("\n7.5: Try to login as retailer1 again (should succeed)...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": CREDENTIALS["retailer1"],
            "password": PASSWORD
        }
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ Login successful after re-enabling")
    else:
        print(f"   ❌ Login failed: {response.text}")
    
    print("\n   ⚠️  IMPORTANT: Leaving retailer1 login ENABLED at the end")

def test_import_export():
    """Test Item 10: Import/Export"""
    print("\n" + "="*80)
    print("TEST 8: IMPORT/EXPORT (Item 10)")
    print("="*80)
    
    # Test as accountant
    print("\n8.1: Accountant GET /api/dms/sale-bills/import-template...")
    response = requests.get(
        f"{BASE_URL}/dms/sale-bills/import-template",
        headers=get_headers("accountant")
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        content_type = response.headers.get('content-type', '')
        size = len(response.content)
        print(f"   ✅ Template downloaded")
        print(f"      Content-Type: {content_type}")
        print(f"      Size: {size} bytes")
        if 'spreadsheet' in content_type or 'excel' in content_type:
            print(f"   ✅ Correct content type (xlsx)")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    print("\n8.2: Accountant GET /api/dms/payments/import-template...")
    response = requests.get(
        f"{BASE_URL}/dms/payments/import-template",
        headers=get_headers("accountant")
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        content_type = response.headers.get('content-type', '')
        size = len(response.content)
        print(f"   ✅ Template downloaded")
        print(f"      Content-Type: {content_type}")
        print(f"      Size: {size} bytes")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    print("\n8.3: Accountant GET /api/dms/parties/export...")
    response = requests.get(
        f"{BASE_URL}/dms/parties/export",
        headers=get_headers("accountant")
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        content_type = response.headers.get('content-type', '')
        size = len(response.content)
        print(f"   ✅ Export downloaded")
        print(f"      Content-Type: {content_type}")
        print(f"      Size: {size} bytes")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    print("\n8.4: Accountant GET /api/dms/owner/products/export...")
    response = requests.get(
        f"{BASE_URL}/dms/owner/products/export",
        headers=get_headers("accountant")
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        content_type = response.headers.get('content-type', '')
        size = len(response.content)
        print(f"   ✅ Export downloaded")
        print(f"      Content-Type: {content_type}")
        print(f"      Size: {size} bytes")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    # Test import endpoints (download template first, then upload)
    print("\n8.5: Download payments template and test import...")
    template_resp = requests.get(
        f"{BASE_URL}/dms/payments/import-template",
        headers=get_headers("accountant")
    )
    if template_resp.status_code == 200:
        # Save template
        with open('/tmp/payments_template.xlsx', 'wb') as f:
            f.write(template_resp.content)
        
        # Upload it back (should handle empty template gracefully)
        with open('/tmp/payments_template.xlsx', 'rb') as f:
            files = {'file': ('payments_template.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            response = requests.post(
                f"{BASE_URL}/dms/payments/import",
                headers=get_headers("accountant"),
                files=files
            )
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Import successful")
            print(f"      created: {data.get('created', 0)}")
            print(f"      skipped: {data.get('skipped', 0)}")
            print(f"      errors: {len(data.get('errors', []))}")
        else:
            print(f"   ⚠️  Import response: {response.text}")
    
    print("\n8.6: Download sale-bills template and test import...")
    template_resp = requests.get(
        f"{BASE_URL}/dms/sale-bills/import-template",
        headers=get_headers("accountant")
    )
    if template_resp.status_code == 200:
        # Save template
        with open('/tmp/sale_bills_template.xlsx', 'wb') as f:
            f.write(template_resp.content)
        
        # Upload it back
        with open('/tmp/sale_bills_template.xlsx', 'rb') as f:
            files = {'file': ('sale_bills_template.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            response = requests.post(
                f"{BASE_URL}/dms/sale-bills/import",
                headers=get_headers("accountant"),
                files=files
            )
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Import successful")
            print(f"      created: {data.get('created', 0)}")
            print(f"      skipped: {data.get('skipped', 0)}")
            print(f"      errors: {len(data.get('errors', []))}")
        else:
            print(f"   ⚠️  Import response: {response.text}")

def test_reports():
    """Test Item 11: Reports"""
    print("\n" + "="*80)
    print("TEST 9: REPORTS (Item 3/11)")
    print("="*80)
    
    # Test catalog for salesperson
    print("\n9.1: Salesperson GET /api/dms/reports/catalog (should include sp_collection)...")
    response = requests.get(
        f"{BASE_URL}/dms/reports/catalog",
        headers=get_headers("salesperson")
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        reports = data if isinstance(data, list) else data.get('reports', [])
        print(f"   ✅ Returned {len(reports)} reports")
        
        # Check for sp_collection
        sp_collection = any(r.get('id') == 'sp_collection' for r in reports)
        print(f"      sp_collection report present: {sp_collection}")
        if sp_collection:
            print(f"   ✅ sp_collection report found in catalog")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    # Test party statement report
    print("\n9.2: Owner runs party_statement report...")
    # First get a distributor ID
    dist_resp = requests.get(f"{BASE_URL}/dms/distributors", headers=get_headers("owner"))
    distributor_id = None
    if dist_resp.status_code == 200:
        dist_data = dist_resp.json()
        distributors = dist_data if isinstance(dist_data, list) else dist_data.get('data', [])
        if distributors:
            distributor_id = distributors[0]['id']
            print(f"   Using distributor: {distributor_id}")
    
    if distributor_id:
        response = requests.post(
            f"{BASE_URL}/dms/reports/party_statement/run",
            headers=get_headers("owner"),
            json={"party_id": distributor_id}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            rows = data.get('data', [])
            print(f"   ✅ Report ran successfully")
            print(f"      Returned {len(rows)} rows")
            if len(rows) > 0:
                sample = rows[0]
                print(f"      Sample row has debit/credit: debit={sample.get('debit')}, credit={sample.get('credit')}")
        else:
            print(f"   ❌ Failed: {response.text}")
    else:
        print("   ⚠️  No distributor found to test party statement")

def main():
    """Main test runner"""
    print("="*80)
    print("GO OIL DMS BACKEND TESTING")
    print("Multi-module Update - July 2025")
    print("="*80)
    
    # Login all users
    print("\n" + "="*80)
    print("LOGGING IN ALL TEST USERS")
    print("="*80)
    
    for role in CREDENTIALS.keys():
        if not login(role):
            print(f"⚠️  Warning: {role} login failed, some tests may be skipped")
    
    # Run all tests
    try:
        test_punch_reopen()
        test_attendance_role_aware()
        test_expenses_approval_flow()
        test_rsm_my_retailers()
        test_distributor_order_flow()
        test_documents_side_effects()
        test_retailer_login_toggle()
        test_import_export()
        test_reports()
    except Exception as e:
        print(f"\n❌ Test execution error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("TESTING COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
