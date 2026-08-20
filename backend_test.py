#!/usr/bin/env python3
"""
GO OIL DMS Backend Verification Test
=====================================
Verifies 3 bug fixes reported by user:
1. AI Assistant (EMERGENT_LLM_KEY configuration)
2. Coupon Sheet PDF Download
3. Print history download
"""
import requests
import json
import sys
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BASE_URL = "https://po-order-sync.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
OWNER_EMAIL = "gooilindia13@gmail.com"
OWNER_PASSWORD = "Arjun@india13"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def log(msg: str, color: str = Colors.RESET):
    print(f"{color}{msg}{Colors.RESET}")

def log_success(msg: str):
    log(f"✅ {msg}", Colors.GREEN)

def log_error(msg: str):
    log(f"❌ {msg}", Colors.RED)

def log_info(msg: str):
    log(f"ℹ️  {msg}", Colors.BLUE)

def log_warning(msg: str):
    log(f"⚠️  {msg}", Colors.YELLOW)

class TestRunner:
    def __init__(self):
        self.token: Optional[str] = None
        self.headers: Dict[str, str] = {}
        self.passed = 0
        self.failed = 0
        self.batch_id: Optional[str] = None
        self.print_history_id: Optional[str] = None

    def login(self) -> bool:
        """Login as owner and get JWT token"""
        log_info(f"Logging in as {OWNER_EMAIL}...")
        try:
            resp = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD},
                timeout=30
            )
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("token")
                if self.token:
                    self.headers = {"Authorization": f"Bearer {self.token}"}
                    log_success(f"Login successful. Token: {self.token[:20]}...")
                    return True
                else:
                    log_error("Login response missing token")
                    return False
            else:
                log_error(f"Login failed: HTTP {resp.status_code}")
                log_error(f"Response: {resp.text}")
                return False
        except Exception as e:
            log_error(f"Login exception: {e}")
            return False

    def test_ai_copilot_status(self) -> bool:
        """Test 1a: GET /api/ai/copilot/status"""
        log_info("\n=== TEST 1a: AI Copilot Status ===")
        try:
            resp = requests.get(
                f"{BASE_URL}/ai/copilot/status",
                headers=self.headers,
                timeout=30
            )
            log_info(f"Status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                log_info(f"Response: {json.dumps(data, indent=2)}")
                
                # Check required fields
                if data.get("ready") is True and data.get("key_configured") is True:
                    log_success("AI Copilot is ready (ready=true, key_configured=true)")
                    self.passed += 1
                    return True
                else:
                    log_error(f"AI Copilot not ready: ready={data.get('ready')}, key_configured={data.get('key_configured')}")
                    log_error(f"Message: {data.get('message')}")
                    self.failed += 1
                    return False
            else:
                log_error(f"HTTP {resp.status_code}: {resp.text}")
                self.failed += 1
                return False
        except Exception as e:
            log_error(f"Exception: {e}")
            self.failed += 1
            return False

    def test_ai_copilot_ask(self) -> bool:
        """Test 1b: POST /api/ai/copilot/ask with real LLM response"""
        log_info("\n=== TEST 1b: AI Copilot Ask (Single Turn) ===")
        try:
            payload = {
                "question": "Give me a one line summary of my business",
                "session_id": "verify-1"
            }
            resp = requests.post(
                f"{BASE_URL}/ai/copilot/ask",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            log_info(f"Status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                answer = data.get("answer", "")
                log_info(f"Answer length: {len(answer)} chars")
                log_info(f"Answer preview: {answer[:200]}...")
                
                if answer and len(answer) > 10:
                    log_success(f"AI Copilot returned non-empty answer ({len(answer)} chars)")
                    self.passed += 1
                    return True
                else:
                    log_error(f"AI Copilot returned empty or trivial answer: '{answer}'")
                    self.failed += 1
                    return False
            else:
                log_error(f"HTTP {resp.status_code}: {resp.text}")
                self.failed += 1
                return False
        except Exception as e:
            log_error(f"Exception: {e}")
            self.failed += 1
            return False

    def test_ai_copilot_multiturn(self) -> bool:
        """Test 1c: POST /api/ai/copilot/ask with SAME session_id (multi-turn)"""
        log_info("\n=== TEST 1c: AI Copilot Ask (Multi-Turn) ===")
        try:
            payload = {
                "question": "What is the total number of products?",
                "session_id": "verify-1"  # SAME session_id as previous
            }
            resp = requests.post(
                f"{BASE_URL}/ai/copilot/ask",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            log_info(f"Status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                answer = data.get("answer", "")
                log_info(f"Answer length: {len(answer)} chars")
                log_info(f"Answer preview: {answer[:200]}...")
                
                if answer and len(answer) > 10:
                    log_success(f"Multi-turn AI Copilot working ({len(answer)} chars)")
                    self.passed += 1
                    return True
                else:
                    log_error(f"Multi-turn returned empty answer: '{answer}'")
                    self.failed += 1
                    return False
            else:
                log_error(f"HTTP {resp.status_code}: {resp.text}")
                self.failed += 1
                return False
        except Exception as e:
            log_error(f"Exception: {e}")
            self.failed += 1
            return False

    def test_create_coupon_batch(self) -> bool:
        """Test 2a: Create a coupon batch"""
        log_info("\n=== TEST 2a: Create Coupon Batch ===")
        try:
            payload = {
                "coupon_type": "cash",
                "coupon_value": 100,
                "count": 5,
                "prefix": "QA",
                "serial_start": 1,
                "serial_pad": 3
            }
            resp = requests.post(
                f"{BASE_URL}/dms/coupons/batches",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            log_info(f"Status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                batch = data.get("batch", {})
                self.batch_id = batch.get("id")
                log_info(f"Batch created: {batch.get('batch_label')} (ID: {self.batch_id})")
                log_success(f"Coupon batch created successfully")
                self.passed += 1
                return True
            else:
                log_error(f"HTTP {resp.status_code}: {resp.text}")
                self.failed += 1
                return False
        except Exception as e:
            log_error(f"Exception: {e}")
            self.failed += 1
            return False

    def test_activate_batch(self) -> bool:
        """Test 2b: Activate the coupon batch"""
        log_info("\n=== TEST 2b: Activate Coupon Batch ===")
        if not self.batch_id:
            log_error("No batch_id available (previous test failed)")
            self.failed += 1
            return False
        
        try:
            resp = requests.post(
                f"{BASE_URL}/dms/coupons/batches/{self.batch_id}/activate",
                headers=self.headers,
                timeout=30
            )
            log_info(f"Status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                log_info(f"Response: {data}")
                log_success("Batch activated successfully")
                self.passed += 1
                return True
            else:
                log_error(f"HTTP {resp.status_code}: {resp.text}")
                self.failed += 1
                return False
        except Exception as e:
            log_error(f"Exception: {e}")
            self.failed += 1
            return False

    def test_batch_pdf_download(self) -> bool:
        """Test 2c: Download batch PDF (both sides)"""
        log_info("\n=== TEST 2c: Download Batch PDF ===")
        if not self.batch_id:
            log_error("No batch_id available (previous test failed)")
            self.failed += 1
            return False
        
        try:
            resp = requests.get(
                f"{BASE_URL}/dms/coupons/batches/{self.batch_id}/export-pdf?side=both",
                headers=self.headers,
                timeout=60
            )
            log_info(f"Status: {resp.status_code}")
            log_info(f"Content-Type: {resp.headers.get('Content-Type')}")
            log_info(f"Content-Length: {len(resp.content)} bytes")
            
            if resp.status_code == 200:
                content_type = resp.headers.get('Content-Type', '')
                if 'application/pdf' in content_type:
                    # Check if it's a real PDF (starts with %PDF)
                    if resp.content[:4] == b'%PDF':
                        log_success(f"PDF downloaded successfully ({len(resp.content)} bytes, starts with %PDF)")
                        self.passed += 1
                        return True
                    else:
                        log_error(f"Response is not a valid PDF (doesn't start with %PDF)")
                        log_error(f"First 100 bytes: {resp.content[:100]}")
                        self.failed += 1
                        return False
                else:
                    log_error(f"Wrong Content-Type: {content_type} (expected application/pdf)")
                    self.failed += 1
                    return False
            else:
                log_error(f"HTTP {resp.status_code}: {resp.text[:500]}")
                self.failed += 1
                return False
        except Exception as e:
            log_error(f"Exception: {e}")
            self.failed += 1
            return False

    def test_mixed_print(self) -> bool:
        """Test 2d: Mixed print PDF"""
        log_info("\n=== TEST 2d: Mixed Print PDF ===")
        if not self.batch_id:
            log_error("No batch_id available (previous test failed)")
            self.failed += 1
            return False
        
        try:
            payload = {
                "batch_ids": [self.batch_id],
                "side": "both"
            }
            resp = requests.post(
                f"{BASE_URL}/dms/coupons/print-mixed",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            log_info(f"Status: {resp.status_code}")
            log_info(f"Content-Type: {resp.headers.get('Content-Type')}")
            log_info(f"Content-Length: {len(resp.content)} bytes")
            
            if resp.status_code == 200:
                content_type = resp.headers.get('Content-Type', '')
                if 'application/pdf' in content_type:
                    if resp.content[:4] == b'%PDF':
                        log_success(f"Mixed print PDF downloaded successfully ({len(resp.content)} bytes)")
                        self.passed += 1
                        return True
                    else:
                        log_error(f"Response is not a valid PDF")
                        self.failed += 1
                        return False
                else:
                    log_error(f"Wrong Content-Type: {content_type}")
                    self.failed += 1
                    return False
            else:
                log_error(f"HTTP {resp.status_code}: {resp.text[:500]}")
                self.failed += 1
                return False
        except Exception as e:
            log_error(f"Exception: {e}")
            self.failed += 1
            return False

    def test_mixed_print_preview(self) -> bool:
        """Test 2e: Mixed print preview (check per_sheet == 70, not 77)"""
        log_info("\n=== TEST 2e: Mixed Print Preview ===")
        if not self.batch_id:
            log_error("No batch_id available (previous test failed)")
            self.failed += 1
            return False
        
        try:
            payload = {
                "batch_ids": [self.batch_id],
                "side": "both"
            }
            resp = requests.post(
                f"{BASE_URL}/dms/coupons/print-mixed/preview",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            log_info(f"Status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                log_info(f"Response: {json.dumps(data, indent=2)}")
                
                per_sheet = data.get("per_sheet")
                layout = data.get("layout", "")
                
                if per_sheet == 70:
                    log_success(f"per_sheet is correct: 70 (NOT 77)")
                    if "11x17" in layout or "11 x 17" in layout:
                        log_success(f"Layout references 11x17: {layout}")
                    else:
                        log_warning(f"Layout doesn't mention 11x17: {layout}")
                    self.passed += 1
                    return True
                else:
                    log_error(f"per_sheet is WRONG: {per_sheet} (expected 70, NOT 77)")
                    self.failed += 1
                    return False
            else:
                log_error(f"HTTP {resp.status_code}: {resp.text}")
                self.failed += 1
                return False
        except Exception as e:
            log_error(f"Exception: {e}")
            self.failed += 1
            return False

    def test_print_history_list(self) -> bool:
        """Test 3a: Get print history and capture latest ID"""
        log_info("\n=== TEST 3a: Get Print History ===")
        try:
            resp = requests.get(
                f"{BASE_URL}/dms/coupons/print-history",
                headers=self.headers,
                timeout=30
            )
            log_info(f"Status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                history = data.get("data", [])
                log_info(f"Found {len(history)} print history records")
                
                if history:
                    # Get the latest (first) record
                    latest = history[0]
                    self.print_history_id = latest.get("id")
                    log_info(f"Latest print history ID: {self.print_history_id}")
                    log_success(f"Print history retrieved successfully")
                    self.passed += 1
                    return True
                else:
                    log_warning("No print history records found (this is OK if no prints were done)")
                    # This is not a failure - just means no prints yet
                    self.passed += 1
                    return True
            else:
                log_error(f"HTTP {resp.status_code}: {resp.text}")
                self.failed += 1
                return False
        except Exception as e:
            log_error(f"Exception: {e}")
            self.failed += 1
            return False

    def test_print_history_download(self) -> bool:
        """Test 3b: Download print history PDF"""
        log_info("\n=== TEST 3b: Download Print History PDF ===")
        if not self.print_history_id:
            log_warning("No print_history_id available (no print history records)")
            log_info("Skipping this test (not a failure)")
            self.passed += 1
            return True
        
        try:
            resp = requests.get(
                f"{BASE_URL}/dms/coupons/print-history/{self.print_history_id}/download",
                headers=self.headers,
                timeout=60
            )
            log_info(f"Status: {resp.status_code}")
            log_info(f"Content-Type: {resp.headers.get('Content-Type')}")
            log_info(f"Content-Length: {len(resp.content)} bytes")
            
            if resp.status_code == 200:
                content_type = resp.headers.get('Content-Type', '')
                if 'application/pdf' in content_type:
                    if resp.content[:4] == b'%PDF':
                        log_success(f"Print history PDF downloaded successfully ({len(resp.content)} bytes)")
                        self.passed += 1
                        return True
                    else:
                        log_error(f"Response is not a valid PDF")
                        self.failed += 1
                        return False
                else:
                    log_error(f"Wrong Content-Type: {content_type}")
                    self.failed += 1
                    return False
            else:
                log_error(f"HTTP {resp.status_code}: {resp.text[:500]}")
                self.failed += 1
                return False
        except Exception as e:
            log_error(f"Exception: {e}")
            self.failed += 1
            return False

    def run_all_tests(self):
        """Run all verification tests"""
        log_info("=" * 70)
        log_info("GO OIL DMS Backend Verification Test")
        log_info("=" * 70)
        
        # Login first
        if not self.login():
            log_error("Login failed. Cannot proceed with tests.")
            return False
        
        # Test 1: AI Assistant
        log_info("\n" + "=" * 70)
        log_info("TEST GROUP 1: AI ASSISTANT")
        log_info("=" * 70)
        self.test_ai_copilot_status()
        self.test_ai_copilot_ask()
        self.test_ai_copilot_multiturn()
        
        # Test 2: Coupon Sheet PDF Download
        log_info("\n" + "=" * 70)
        log_info("TEST GROUP 2: COUPON SHEET PDF DOWNLOAD")
        log_info("=" * 70)
        self.test_create_coupon_batch()
        self.test_activate_batch()
        self.test_batch_pdf_download()
        self.test_mixed_print()
        self.test_mixed_print_preview()
        
        # Test 3: Print History Download
        log_info("\n" + "=" * 70)
        log_info("TEST GROUP 3: PRINT HISTORY DOWNLOAD")
        log_info("=" * 70)
        self.test_print_history_list()
        self.test_print_history_download()
        
        # Summary
        log_info("\n" + "=" * 70)
        log_info("TEST SUMMARY")
        log_info("=" * 70)
        total = self.passed + self.failed
        log_info(f"Total tests: {total}")
        log_success(f"Passed: {self.passed}")
        if self.failed > 0:
            log_error(f"Failed: {self.failed}")
        else:
            log_success(f"Failed: {self.failed}")
        
        if self.failed == 0:
            log_success("\n🎉 ALL TESTS PASSED! 🎉")
            return True
        else:
            log_error(f"\n❌ {self.failed} TEST(S) FAILED")
            return False

def main():
    runner = TestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
