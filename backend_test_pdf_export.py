#!/usr/bin/env python3
"""
Focused test for PDF export after pypng dependency installation.
Tests ONLY the PDF export flow with security verification.
"""

import requests
import os
import re
from io import BytesIO

# Get backend URL from environment
BACKEND_URL = os.getenv("REACT_APP_BACKEND_URL", "https://smartcoupon-retail.preview.emergentagent.com")
BASE_URL = f"{BACKEND_URL}/api"

# Test credentials
OWNER_EMAIL = "owner@gooil.com"
OWNER_PASSWORD = "GoOil@2026"

def login(email, password):
    """Login and return JWT token"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password}
    )
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        print(f"Response: {response.text}")
        return None
    
    data = response.json()
    token = data.get("token")
    print(f"✅ Login successful as {email}")
    return token

def create_test_batch(token):
    """Create a small test batch for PDF export"""
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "coupon_type": "cash",
        "coupon_value": 20,
        "serial_mode": "prefix_sequential",
        "prefix": "PDFX",  # Changed to avoid overlap
        "serial_start": 1,
        "serial_pad": 3,
        "count": 3
    }
    
    print("\n📝 Creating test batch...")
    print(f"Payload: {payload}")
    
    response = requests.post(
        f"{BASE_URL}/dms/coupons/batches",
        json=payload,
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Batch creation failed: {response.status_code}")
        print(f"Response: {response.text}")
        return None
    
    data = response.json()
    # The batch_id is in data["batch"]["id"]
    batch_id = data.get("batch", {}).get("id")
    print(f"✅ Batch created: {batch_id}")
    print(f"   Batch details: {data}")
    return batch_id

def activate_batch(token, batch_id):
    """Activate the entire batch"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\n🔓 Activating batch {batch_id}...")
    
    response = requests.post(
        f"{BASE_URL}/dms/coupons/batches/{batch_id}/activate",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Batch activation failed: {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    data = response.json()
    print(f"✅ Batch activated successfully")
    print(f"   Response: {data}")
    return True

def export_pdf(token, batch_id):
    """Export PDF and verify security requirements"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\n📄 Exporting PDF for batch {batch_id}...")
    
    response = requests.get(
        f"{BASE_URL}/dms/coupons/batches/{batch_id}/export-pdf",
        headers=headers
    )
    
    print(f"\n=== PDF EXPORT VERIFICATION ===")
    
    # Check 1: HTTP 200
    if response.status_code != 200:
        print(f"❌ FAIL: HTTP status {response.status_code} (expected 200)")
        print(f"Response: {response.text}")
        return False
    print(f"✅ PASS: HTTP 200")
    
    # Check 2: Content-Type
    content_type = response.headers.get("Content-Type", "")
    if content_type != "application/pdf":
        print(f"❌ FAIL: Content-Type '{content_type}' (expected 'application/pdf')")
        return False
    print(f"✅ PASS: Content-Type: application/pdf")
    
    # Check 3: Response body size > 5 KB
    body_size = len(response.content)
    if body_size <= 5 * 1024:
        print(f"❌ FAIL: Body size {body_size} bytes (expected > 5 KB)")
        return False
    print(f"✅ PASS: Body size {body_size} bytes (> 5 KB)")
    
    # Check 4: Body starts with %PDF-
    if not response.content.startswith(b'%PDF-'):
        print(f"❌ FAIL: Body does not start with '%PDF-'")
        print(f"First 20 bytes: {response.content[:20]}")
        return False
    print(f"✅ PASS: Body starts with '%PDF-'")
    
    # Check 5: Extract text and verify NO SECRETS LEAKED
    print(f"\n🔍 Extracting PDF text for security verification...")
    
    try:
        import PyPDF2
        pdf_reader = PyPDF2.PdfReader(BytesIO(response.content))
        
        # Extract all text from all pages
        all_text = ""
        for page in pdf_reader.pages:
            all_text += page.extract_text()
        
        print(f"📝 Extracted text length: {len(all_text)} characters")
        print(f"📝 First 500 characters of extracted text:")
        print(all_text[:500])
        print("...")
        
        # Security checks - MUST NOT contain these strings
        forbidden_strings = [
            "hmac_secret",
            "secret_token",
            "signature:",
            "GO-C-",
            "GO-R-",
            "Do not photocopy"
        ]
        
        print(f"\n🔒 Security Check: Forbidden strings...")
        leaked_secrets = []
        for forbidden in forbidden_strings:
            if forbidden in all_text:
                leaked_secrets.append(forbidden)
                print(f"❌ FAIL: Found forbidden string '{forbidden}'")
        
        if not leaked_secrets:
            print(f"✅ PASS: No forbidden strings found")
        
        # Check for 32-char hex tokens (secret_token leak)
        print(f"\n🔒 Security Check: 32-char hex tokens...")
        hex_pattern = re.compile(r'\b[0-9a-f]{32}\b')
        hex_matches = hex_pattern.findall(all_text.lower())
        if hex_matches:
            print(f"❌ FAIL: Found {len(hex_matches)} 32-char hex tokens (potential secret_token leak)")
            print(f"   Matches: {hex_matches[:3]}")  # Show first 3
            leaked_secrets.append("32-char-hex-token")
        else:
            print(f"✅ PASS: No 32-char hex tokens found")
        
        # Check for UUID pattern (hidden_secure_id leak)
        print(f"\n🔒 Security Check: UUID patterns...")
        uuid_pattern = re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.IGNORECASE)
        uuid_matches = uuid_pattern.findall(all_text)
        if uuid_matches:
            print(f"❌ FAIL: Found {len(uuid_matches)} UUID patterns (potential hidden_secure_id leak)")
            print(f"   Matches: {uuid_matches[:3]}")  # Show first 3
            leaked_secrets.append("uuid-pattern")
        else:
            print(f"✅ PASS: No UUID patterns found")
        
        # Check for REQUIRED visible elements
        print(f"\n✅ Content Check: Required visible elements...")
        required_elements = {
            "PDFX001": "Visible serial PDFX001",
            "PDFX002": "Visible serial PDFX002",
            "PDFX003": "Visible serial PDFX003",
            "CASH": "Coupon type CASH",
            "20": "Coupon value 20"
        }
        
        missing_elements = []
        for element, description in required_elements.items():
            if element in all_text:
                print(f"✅ PASS: Found {description}")
            else:
                print(f"❌ FAIL: Missing {description}")
                missing_elements.append(element)
        
        # Final verdict
        print(f"\n{'='*50}")
        print(f"FINAL VERDICT:")
        print(f"{'='*50}")
        
        if leaked_secrets:
            print(f"❌ CRITICAL SECURITY FAILURE: {len(leaked_secrets)} secret(s) leaked")
            print(f"   Leaked: {leaked_secrets}")
            return False
        
        if missing_elements:
            print(f"❌ CONTENT FAILURE: {len(missing_elements)} required element(s) missing")
            print(f"   Missing: {missing_elements}")
            return False
        
        print(f"✅ ALL CHECKS PASSED")
        print(f"   - No secrets leaked")
        print(f"   - All required elements present")
        print(f"   - PDF format valid")
        return True
        
    except ImportError:
        print(f"⚠️ WARNING: PyPDF2 not installed, trying pdfplumber...")
        
        try:
            import pdfplumber
            
            all_text = ""
            with pdfplumber.open(BytesIO(response.content)) as pdf:
                for page in pdf.pages:
                    all_text += page.extract_text() or ""
            
            print(f"📝 Extracted text length: {len(all_text)} characters")
            print(f"📝 First 500 characters of extracted text:")
            print(all_text[:500])
            
            # Same security checks as above
            forbidden_strings = [
                "hmac_secret", "secret_token", "signature:", 
                "GO-C-", "GO-R-", "Do not photocopy"
            ]
            
            leaked_secrets = []
            for forbidden in forbidden_strings:
                if forbidden in all_text:
                    leaked_secrets.append(forbidden)
            
            hex_pattern = re.compile(r'\b[0-9a-f]{32}\b')
            if hex_pattern.findall(all_text.lower()):
                leaked_secrets.append("32-char-hex-token")
            
            uuid_pattern = re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.IGNORECASE)
            if uuid_pattern.findall(all_text):
                leaked_secrets.append("uuid-pattern")
            
            required_elements = ["PDFX001", "PDFX002", "PDFX003", "CASH", "20"]
            missing_elements = [e for e in required_elements if e not in all_text]
            
            if leaked_secrets or missing_elements:
                print(f"❌ FAIL: Leaked secrets: {leaked_secrets}, Missing: {missing_elements}")
                return False
            
            print(f"✅ ALL CHECKS PASSED (via pdfplumber)")
            return True
            
        except ImportError:
            print(f"❌ ERROR: Neither PyPDF2 nor pdfplumber installed")
            print(f"   Cannot verify PDF text content")
            print(f"   However, PDF was generated successfully (HTTP 200, correct Content-Type, valid size)")
            return False

def main():
    print("="*60)
    print("PDF EXPORT RETEST (after pypng installation)")
    print("="*60)
    
    # Step 1: Login
    token = login(OWNER_EMAIL, OWNER_PASSWORD)
    if not token:
        print("\n❌ TEST FAILED: Cannot login")
        return
    
    # Step 2: Create test batch
    batch_id = create_test_batch(token)
    if not batch_id:
        print("\n❌ TEST FAILED: Cannot create batch")
        return
    
    # Step 3: Activate batch
    if not activate_batch(token, batch_id):
        print("\n❌ TEST FAILED: Cannot activate batch")
        return
    
    # Step 4: Export PDF and verify
    success = export_pdf(token, batch_id)
    
    print("\n" + "="*60)
    if success:
        print("✅ PDF EXPORT TEST PASSED")
        print("   The pypng dependency fix is working correctly.")
        print("   PDF contains only approved elements (QR, serial, type, value).")
        print("   No secrets leaked.")
    else:
        print("❌ PDF EXPORT TEST FAILED")
        print("   See details above.")
    print("="*60)

if __name__ == "__main__":
    main()
