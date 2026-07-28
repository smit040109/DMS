#!/usr/bin/env python3
"""Focused rate limit test."""
import requests
import time

BASE_URL = "https://38026b09-a311-4ef3-8159-6cb799593d83.preview.emergentagent.com/api"

print("Testing rate limiting on /auth/login (10/minute)...")
print("Making 12 rapid login attempts with bad credentials...")

bad_creds = {"email": "admin@gooil.com", "password": "wrongpassword"}
results = []

for i in range(12):
    resp = requests.post(f"{BASE_URL}/auth/login", json=bad_creds, timeout=10)
    results.append((i+1, resp.status_code))
    print(f"  Attempt {i+1}: {resp.status_code}")
    if resp.status_code == 429:
        print(f"\n✅ Rate limit triggered at attempt {i+1}")
        break
    time.sleep(0.1)  # Small delay between attempts

if all(status != 429 for _, status in results):
    print(f"\n❌ No 429 received after {len(results)} attempts")
else:
    print(f"\n✅ Rate limiting is working correctly")
