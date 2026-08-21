#!/usr/bin/env python3
"""
Create test coupon batches for PDF export testing
"""

import requests
import json

BASE_URL = "https://points-wallet-hub-2.preview.emergentagent.com/api"
OWNER_EMAIL = "gooilindia13@gmail.com"
OWNER_PASSWORD = "Arjun@india13"

def login():
    """Login and get token"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    else:
        print(f"Login failed: {response.status_code}")
        return None

def create_batch(token, title, coupon_type, coupon_value, count, prefix):
    """Create a coupon batch"""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "title": title,
        "coupon_type": coupon_type,
        "coupon_value": coupon_value,
        "count": count,
        "serial_mode": "prefix_sequential",
        "prefix": prefix,
        "serial_start": 1,
        "serial_pad": 5,
        "notes": f"Test batch for PDF export testing ({count} coupons)"
    }
    
    print(f"\nCreating batch: {title} ({count} coupons)...")
    response = requests.post(
        f"{BASE_URL}/dms/coupons/batches",
        headers=headers,
        json=payload
    )
    
    if response.status_code == 200:
        data = response.json()
        batch_id = data.get("id")
        batch_label = data.get("batch_label")
        print(f"✓ Created: {batch_label} (ID: {batch_id})")
        return batch_id
    else:
        print(f"✗ Failed: {response.status_code} - {response.text}")
        return None

def activate_batch(token, batch_id):
    """Activate a batch"""
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Activating batch {batch_id}...")
    response = requests.post(
        f"{BASE_URL}/dms/coupons/batches/{batch_id}/activate",
        headers=headers
    )
    
    if response.status_code == 200:
        print(f"✓ Activated")
        return True
    else:
        print(f"✗ Activation failed: {response.status_code}")
        return False

def main():
    print("="*80)
    print("Creating Test Coupon Batches for PDF Export Testing")
    print("="*80)
    
    token = login()
    if not token:
        print("Cannot proceed without authentication")
        return
    
    print("✓ Logged in as owner")
    
    # Create LARGE batch (~1400 coupons) - REWARD type
    large_batch_id = create_batch(
        token,
        title="REWARD GOOIL × 1400",
        coupon_type="reward",
        coupon_value=100,
        count=1400,
        prefix="R"
    )
    
    if large_batch_id:
        activate_batch(token, large_batch_id)
    
    # Create SMALL batch (~100 coupons) - CASH type
    small_batch_id = create_batch(
        token,
        title="CASH ABC × 100",
        coupon_type="cash",
        coupon_value=50,
        count=100,
        prefix="C"
    )
    
    if small_batch_id:
        activate_batch(token, small_batch_id)
    
    print("\n" + "="*80)
    print("Test batches created successfully!")
    print("="*80)
    print(f"\nLarge batch ID: {large_batch_id}")
    print(f"Small batch ID: {small_batch_id}")
    print("\nYou can now run the PDF export tests.")

if __name__ == "__main__":
    main()
