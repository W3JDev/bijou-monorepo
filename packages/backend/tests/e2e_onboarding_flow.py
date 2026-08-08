#!/usr/bin/env python3
"""
Bijou AI - E2E Onboarding Flow Test
====================================

Automates the complete onboarding flow from signup to dashboard:
1. Create test tenant (POST /api/onboarding/v2/signup)
2. Generate QR code (GET /api/onboarding/v2/whatsapp/qr/{tenant_id})
3. Check onboarding status (GET /api/onboarding/v2/status/{tenant_id})
4. Validate system health endpoints
5. Test device status endpoint

Usage:
    python tests/e2e_onboarding_flow.py --env staging
    python tests/e2e_onboarding_flow.py --env production --verbose
    
Exit Codes:
    0 - All tests passed
    1 - One or more tests failed
"""

import argparse
import base64
import json
import os
import re
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"


class E2EOnboardingTest:
    def __init__(self, base_url: str, bridge_url: str, verbose: bool = False):
        self.base_url = base_url.rstrip("/")
        self.bridge_url = bridge_url.rstrip("/")
        self.verbose = verbose
        self.results: List[Tuple[str, bool, str]] = []
        self.start_time = datetime.now()
        
        # Test data (generated during test run)
        self.test_tenant_id: Optional[str] = None
        self.test_email: Optional[str] = None
        self.test_business_name: Optional[str] = None

    def log(self, message: str, color: str = RESET):
        """Print colored log message"""
        try:
            print(f"{color}{message}{RESET}")
        except UnicodeEncodeError:
            # Fallback: remove emojis
            message_no_emoji = re.sub(r'[^\x00-\x7F]+', '', message)
            print(f"{color}{message_no_emoji}{RESET}")

    def verbose_log(self, message: str):
        """Print debug log only in verbose mode"""
        if self.verbose:
            self.log(f"  [DEBUG] {message}", CYAN)

    def record_result(self, check_name: str, passed: bool, details: str = ""):
        """Record test result"""
        self.results.append((check_name, passed, details))
        status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
        self.log(f"  {status} - {details}")

    def validate_uuid(self, value: str) -> bool:
        """Validate UUID format"""
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, value.lower()))

    def validate_base64_image(self, data: str) -> bool:
        """Validate base64 image data"""
        try:
            # Check if it's a data URI
            if data.startswith("data:image"):
                # Extract base64 part
                base64_part = data.split(",")[1] if "," in data else data
            else:
                base64_part = data
            
            # Try to decode
            decoded = base64.b64decode(base64_part)
            
            # Check if it's a PNG (starts with PNG magic number)
            if decoded[:8] == b'\x89PNG\r\n\x1a\n':
                return True
            
            # Check for other image formats (JPEG, etc.)
            return len(decoded) > 100  # At least some meaningful data
        except Exception:
            return False

    def test_create_tenant(self) -> bool:
        """Step 1: Create test tenant via signup endpoint"""
        self.log(f"\n{BLUE}[1/5] Creating test tenant...{RESET}")
        
        # Generate unique test data
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.test_email = f"test-{timestamp}@bijou-e2e-test.com"
        self.test_business_name = f"E2E Test Cafe {timestamp}"
        
        payload = {
            "business_name": self.test_business_name,
            "owner_name": "E2E Test Bot",
            "email": self.test_email,
            "phone": "+60100000000"  # Test number (won't actually connect)
        }
        
        self.verbose_log(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(
                f"{self.base_url}/api/onboarding/v2/signup",
                json=payload,
                timeout=10
            )
            
            self.verbose_log(f"Status Code: {response.status_code}")
            self.verbose_log(f"Response: {response.text[:500]}")
            
            if response.status_code not in [200, 201]:
                self.record_result(
                    "Tenant Creation",
                    False,
                    f"HTTP {response.status_code} - {response.text[:200]}"
                )
                return False
            
            data = response.json()
            
            # Validate response structure
            if "tenant_id" not in data:
                self.record_result(
                    "Tenant Creation",
                    False,
                    "Missing 'tenant_id' in response"
                )
                return False
            
            self.test_tenant_id = data["tenant_id"]
            
            # Validate UUID format
            if not self.test_tenant_id or not self.validate_uuid(self.test_tenant_id):
                self.record_result(
                    "Tenant Creation",
                    False,
                    f"Invalid UUID format: {self.test_tenant_id}"
                )
                return False
            
            self.record_result(
                "Tenant Creation",
                True,
                f"Tenant ID: {self.test_tenant_id}"
            )
            return True
            
        except Exception as e:
            self.record_result("Tenant Creation", False, f"Error: {str(e)}")
            return False

    def test_generate_qr(self) -> bool:
        """Step 2: Generate QR code for WhatsApp connection"""
        self.log(f"\n{BLUE}[2/5] Generating QR code...{RESET}")
        
        if not self.test_tenant_id:
            self.record_result("QR Generation", False, "No tenant_id (skipped)")
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/api/onboarding/v2/whatsapp/qr/{self.test_tenant_id}",
                timeout=15
            )
            
            self.verbose_log(f"Status Code: {response.status_code}")
            
            if response.status_code != 200:
                # Known issue: Device not provisioned yet
                if response.status_code == 500 and "not provisioned" in response.text:
                    self.record_result(
                        "QR Generation",
                        False,
                        f"Device not provisioned (known issue - see api_test_plan.md)"
                    )
                else:
                    self.record_result(
                        "QR Generation",
                        False,
                        f"HTTP {response.status_code} - {response.text[:200]}"
                    )
                return False
            
            data = response.json()
            
            # Validate response structure
            if "qr_code" not in data and "qr_data" not in data:
                self.record_result(
                    "QR Generation",
                    False,
                    "Missing QR code data in response"
                )
                return False
            
            qr_data = data.get("qr_code") or data.get("qr_data")
            
            # Validate base64 image
            if not self.validate_base64_image(qr_data):
                self.record_result(
                    "QR Generation",
                    False,
                    "Invalid base64 image data"
                )
                return False
            
            # Calculate size
            qr_size_kb = len(qr_data) / 1024
            
            self.record_result(
                "QR Generation",
                True,
                f"QR code generated ({qr_size_kb:.1f}KB base64 image)"
            )
            return True
            
        except Exception as e:
            self.record_result("QR Generation", False, f"Error: {str(e)}")
            return False

    def test_onboarding_status(self) -> bool:
        """Step 3: Check onboarding status"""
        self.log(f"\n{BLUE}[3/5] Checking onboarding status...{RESET}")
        
        if not self.test_tenant_id:
            self.record_result("Onboarding Status", False, "No tenant_id (skipped)")
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/api/onboarding/v2/status/{self.test_tenant_id}",
                timeout=10
            )
            
            self.verbose_log(f"Status Code: {response.status_code}")
            self.verbose_log(f"Response: {response.text[:500]}")
            
            if response.status_code != 200:
                self.record_result(
                    "Onboarding Status",
                    False,
                    f"HTTP {response.status_code}"
                )
                return False
            
            data = response.json()
            
            # Validate response structure
            required_fields = ["tenant_id", "progress"]
            for field in required_fields:
                if field not in data:
                    self.record_result(
                        "Onboarding Status",
                        False,
                        f"Missing required field: {field}"
                    )
                    return False
            
            # Validate tenant_id matches
            if data["tenant_id"] != self.test_tenant_id:
                self.record_result(
                    "Onboarding Status",
                    False,
                    f"tenant_id mismatch: {data['tenant_id']} != {self.test_tenant_id}"
                )
                return False
            
            progress = data["progress"]
            current_step = progress.get("current_step", "unknown")
            whatsapp_completed = progress.get("step_whatsapp_completed", None)
            
            # For newly created tenant, WhatsApp should not be completed
            if whatsapp_completed is True:
                self.log(f"  {YELLOW}⚠ WARNING{RESET} - WhatsApp already completed (unexpected for new tenant)")
            
            self.record_result(
                "Onboarding Status",
                True,
                f"Status: {current_step} (whatsapp_completed={whatsapp_completed})"
            )
            return True
            
        except Exception as e:
            self.record_result("Onboarding Status", False, f"Error: {str(e)}")
            return False

    def test_system_health(self) -> bool:
        """Step 4: Validate system health endpoints"""
        self.log(f"\n{BLUE}[4/5] Validating system health...{RESET}")
        
        all_passed = True
        start_time = time.time()
        
        # Test backend health
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            elapsed_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                version = data.get("version", "unknown")
                status = data.get("status", "unknown")
                
                if elapsed_ms < 2000:
                    self.record_result(
                        "Backend Health",
                        True,
                        f"v{version}, status={status} ({elapsed_ms:.0f}ms)"
                    )
                else:
                    self.record_result(
                        "Backend Health",
                        False,
                        f"Response too slow ({elapsed_ms:.0f}ms > 2000ms)"
                    )
                    all_passed = False
            else:
                self.record_result(
                    "Backend Health",
                    False,
                    f"HTTP {response.status_code}"
                )
                all_passed = False
        except Exception as e:
            self.record_result("Backend Health", False, f"Error: {str(e)}")
            all_passed = False
        
        # Test bridge health
        try:
            start_time = time.time()
            response = requests.get(f"{self.bridge_url}/health", timeout=10)
            elapsed_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                sessions = data.get("active_sessions", 0)
                status = data.get("status", "unknown")
                
                if elapsed_ms < 2000:
                    self.record_result(
                        "Bridge Health",
                        True,
                        f"status={status}, sessions={sessions} ({elapsed_ms:.0f}ms)"
                    )
                else:
                    self.record_result(
                        "Bridge Health",
                        False,
                        f"Response too slow ({elapsed_ms:.0f}ms > 2000ms)"
                    )
                    all_passed = False
            else:
                self.record_result(
                    "Bridge Health",
                    False,
                    f"HTTP {response.status_code}"
                )
                all_passed = False
        except Exception as e:
            self.record_result("Bridge Health", False, f"Error: {str(e)}")
            all_passed = False
        
        return all_passed

    def test_device_status(self) -> bool:
        """Step 5: Test device status endpoint"""
        self.log(f"\n{BLUE}[5/5] Testing device status endpoint...{RESET}")
        
        if not self.test_tenant_id:
            self.record_result("Device Status", False, "No tenant_id (skipped)")
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/api/tenant/{self.test_tenant_id}/device/status",
                timeout=10
            )
            
            self.verbose_log(f"Status Code: {response.status_code}")
            self.verbose_log(f"Response: {response.text[:500]}")
            
            if response.status_code == 500:
                # Known issue: get_supabase not defined
                if "get_supabase" in response.text or "not defined" in response.text:
                    self.record_result(
                        "Device Status",
                        False,
                        "Endpoint has code error (known issue - see api_test_plan.md)"
                    )
                else:
                    self.record_result(
                        "Device Status",
                        False,
                        f"HTTP 500 - {response.text[:200]}"
                    )
                return False
            
            if response.status_code != 200:
                self.record_result(
                    "Device Status",
                    False,
                    f"HTTP {response.status_code}"
                )
                return False
            
            data = response.json()
            
            # For new tenant, expect "no_device" or device data
            connection_status = data.get("connection_status", "unknown")
            
            if connection_status == "no_device":
                self.record_result(
                    "Device Status",
                    True,
                    f"Endpoint accessible (state: no_device)"
                )
            elif "device" in data:
                self.record_result(
                    "Device Status",
                    True,
                    f"Endpoint accessible (state: {connection_status})"
                )
            else:
                self.record_result(
                    "Device Status",
                    False,
                    f"Unexpected response structure: {json.dumps(data)[:200]}"
                )
                return False
            
            return True
            
        except Exception as e:
            self.record_result("Device Status", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self) -> bool:
        """Run all E2E tests"""
        self.log(f"\n{'='*60}")
        self.log(f"🧪 BIJOU AI - E2E ONBOARDING FLOW TEST", BLUE)
        self.log(f"{'='*60}")
        self.log(f"Environment: {self.base_url}")
        self.log(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run tests in order
        tests = [
            self.test_create_tenant,
            self.test_generate_qr,
            self.test_onboarding_status,
            self.test_system_health,
            self.test_device_status,
        ]
        
        for test_func in tests:
            try:
                test_func()
            except Exception as e:
                self.log(f"{RED}Unexpected error in {test_func.__name__}: {e}{RESET}")
        
        # Print summary
        self.print_summary()
        
        # Return overall status
        return all(passed for _, passed, _ in self.results)

    def print_summary(self):
        """Print test summary"""
        duration = (datetime.now() - self.start_time).total_seconds()
        passed = sum(1 for _, p, _ in self.results if p)
        failed = sum(1 for _, p, _ in self.results if not p)
        total = len(self.results)
        
        self.log(f"\n{'='*60}")
        self.log(f"📊 SUMMARY", BLUE)
        self.log(f"{'='*60}")
        self.log(f"Total Checks: {total}")
        self.log(f"Passed: {passed}", GREEN if passed == total else YELLOW)
        self.log(f"Failed: {failed}", RED if failed > 0 else GREEN)
        self.log(f"Duration: {duration:.2f}s")
        
        if failed > 0:
            self.log(f"\n{RED}❌ E2E ONBOARDING FLOW TEST FAILED{RESET}")
            self.log(f"\nFailed Checks:")
            for name, passed, details in self.results:
                if not passed:
                    self.log(f"  - {name}: {details}", RED)
        else:
            self.log(f"\n{GREEN}✅ E2E ONBOARDING FLOW TEST PASSED{RESET}")
        
        self.log(f"{'='*60}")
        
        # Print test tenant info
        if self.test_tenant_id:
            self.log(f"\nTest Tenant ID: {self.test_tenant_id}")
            self.log(f"Test Email: {self.test_email}")
            self.log(f"Business Name: {self.test_business_name}")
            self.log(f"{YELLOW}(Manual cleanup required){RESET}")
        
        self.log(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Bijou AI E2E Onboarding Flow Test"
    )
    parser.add_argument(
        "--env",
        choices=["staging", "production", "local"],
        default="staging",
        help="Environment to test",
    )
    parser.add_argument(
        "--base-url",
        help="Override base URL",
    )
    parser.add_argument(
        "--bridge-url",
        help="Override bridge URL",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose debug output",
    )
    
    args = parser.parse_args()
    
    # Environment URLs
    env_config = {
        "staging": {
            "base_url": "https://bijou-staging.fly.dev",
            "bridge_url": "https://whatsapp-bridge-staging-w3j.fly.dev",
        },
        "production": {
            "base_url": "https://bijou-production.fly.dev",
            "bridge_url": "https://whatsapp-bridge-production-w3j.fly.dev",
        },
        "local": {
            "base_url": "http://localhost:8000",
            "bridge_url": "http://localhost:8080",
        },
    }
    
    config = env_config[args.env]
    base_url = args.base_url or config["base_url"]
    bridge_url = args.bridge_url or config["bridge_url"]
    
    # Run tests
    tester = E2EOnboardingTest(base_url, bridge_url, verbose=args.verbose)
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
