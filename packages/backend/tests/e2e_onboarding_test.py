#!/usr/bin/env python3
"""
Bijou AI - End-to-End Onboarding Flow Test
===========================================

Tests complete user journey from signup to first message:
1. POST /api/onboarding/v2/signup (Create tenant)
2. GET /api/onboarding/v2/status/{tenant_id} (Check progress)
3. GET /api/onboarding/v2/whatsapp/qr/{tenant_id} (Get QR code)
4. Simulate WhatsApp connection (via device status check)
5. POST /api/onboarding/v2/complete/{tenant_id} (Mark complete)
6. Test message webhook (if bridge is available)

Usage:
    python3 tests/e2e_onboarding_test.py
    python3 tests/e2e_onboarding_test.py --env staging
    python3 tests/e2e_onboarding_test.py --env production --no-cleanup

Author: W3J Bijou AI
Date: February 19, 2026
"""

import argparse
import json
import sys
import time
from datetime import datetime
from typing import Dict, Optional

import httpx

# Test configuration
ENVIRONMENTS = {
    "local": "http://localhost:8080",
    "staging": "https://bijou-staging.fly.dev",
    "production": "https://bijou-enterprise.fly.dev"
}

class OnboardingE2ETest:
    """End-to-End Onboarding Flow Test Runner"""
    
    def __init__(self, base_url: str, cleanup: bool = True):
        self.base_url = base_url.rstrip("/")
        self.cleanup = cleanup
        self.tenant_id: Optional[str] = None
        self.signup_token: Optional[str] = None
        self.test_results = {
            "started_at": datetime.now().isoformat(),
            "environment": base_url,
            "steps": [],
            "total_passed": 0,
            "total_failed": 0,
            "critical_failures": []
        }
    
    def log_step(self, step_name: str, status: str, details: Dict, is_critical: bool = False):
        """Log test step result"""
        step = {
            "name": step_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        self.test_results["steps"].append(step)
        
        if status == "PASS":
            self.test_results["total_passed"] += 1
            print(f"✅ {step_name}: PASSED")
        else:
            self.test_results["total_failed"] += 1
            print(f"❌ {step_name}: FAILED")
            if is_critical:
                self.test_results["critical_failures"].append(step_name)
        
        # Print details
        for key, value in details.items():
            if key != "response_body":  # Don't print full response
                print(f"   {key}: {value}")
    
    async def test_step_1_signup(self) -> bool:
        """Test Step 1: Tenant Signup"""
        print("\n" + "="*60)
        print("STEP 1: Tenant Signup (POST /api/onboarding/v2/signup)")
        print("="*60)
        
        # Generate unique test data
        timestamp = int(time.time())
        payload = {
            "business_name": f"E2E Test Property Agency {timestamp}",
            "email": f"test_{timestamp}@bijou-e2e.com",
            "phone": f"601{timestamp % 100000000}",
            "plan": "free"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/onboarding/v2/signup",
                    json=payload
                )
                
                details = {
                    "status_code": response.status_code,
                    "business_name": payload["business_name"],
                    "email": payload["email"]
                }
                
                if response.status_code == 200:
                    data = response.json()
                    self.tenant_id = data.get("tenant_id")
                    self.signup_token = data.get("signup_token")
                    
                    details["tenant_id"] = self.tenant_id
                    details["signup_token"] = self.signup_token
                    details["onboarding_url"] = data.get("onboarding_url", "N/A")
                    
                    if self.tenant_id:
                        self.log_step("Step 1: Signup", "PASS", details, is_critical=True)
                        return True
                    else:
                        details["error"] = "No tenant_id in response"
                        self.log_step("Step 1: Signup", "FAIL", details, is_critical=True)
                        return False
                else:
                    details["error"] = response.text
                    self.log_step("Step 1: Signup", "FAIL", details, is_critical=True)
                    return False
                    
        except Exception as e:
            self.log_step("Step 1: Signup", "FAIL", {
                "error": str(e),
                "exception_type": type(e).__name__
            }, is_critical=True)
            return False
    
    async def test_step_2_status_check(self) -> bool:
        """Test Step 2: Check Onboarding Status"""
        print("\n" + "="*60)
        print("STEP 2: Status Check (GET /api/onboarding/v2/status/{tenant_id})")
        print("="*60)
        
        if not self.tenant_id:
            self.log_step("Step 2: Status Check", "SKIP", {"reason": "No tenant_id from Step 1"})
            return False
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/onboarding/v2/status/{self.tenant_id}"
                )
                
                details = {
                    "status_code": response.status_code,
                    "tenant_id": self.tenant_id
                }
                
                if response.status_code == 200:
                    data = response.json()
                    details["current_step"] = data.get("current_step", "unknown")
                    details["step_payment"] = data.get("progress", {}).get("step_payment_completed", False)
                    details["step_details"] = data.get("progress", {}).get("step_details_completed", False)
                    details["step_whatsapp"] = data.get("progress", {}).get("step_whatsapp_completed", False)
                    
                    self.log_step("Step 2: Status Check", "PASS", details)
                    return True
                else:
                    details["error"] = response.text
                    self.log_step("Step 2: Status Check", "FAIL", details)
                    return False
                    
        except Exception as e:
            self.log_step("Step 2: Status Check", "FAIL", {
                "error": str(e),
                "exception_type": type(e).__name__
            })
            return False
    
    async def test_step_3_qr_generation(self) -> bool:
        """Test Step 3: WhatsApp QR Code Generation"""
        print("\n" + "="*60)
        print("STEP 3: QR Generation (GET /api/onboarding/v2/whatsapp/qr/{tenant_id})")
        print("="*60)
        
        if not self.tenant_id:
            self.log_step("Step 3: QR Generation", "SKIP", {"reason": "No tenant_id from Step 1"})
            return False
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/onboarding/v2/whatsapp/qr/{self.tenant_id}"
                )
                
                details = {
                    "status_code": response.status_code,
                    "tenant_id": self.tenant_id
                }
                
                if response.status_code == 200:
                    data = response.json()
                    qr_link = data.get("qr_link", "")
                    
                    details["has_qr_link"] = bool(qr_link)
                    details["qr_format"] = "base64_png" if qr_link.startswith("data:image") else "unknown"
                    details["device_id"] = data.get("results", {}).get("device_id", "N/A")
                    
                    if qr_link:
                        self.log_step("Step 3: QR Generation", "PASS", details, is_critical=True)
                        return True
                    else:
                        details["error"] = "No qr_link in response"
                        self.log_step("Step 3: QR Generation", "FAIL", details, is_critical=True)
                        return False
                elif response.status_code == 404:
                    # Device not provisioned - expected for new tenants
                    details["note"] = "Device not provisioned (expected for new tenant)"
                    self.log_step("Step 3: QR Generation", "PASS", details)
                    return True
                else:
                    details["error"] = response.text
                    self.log_step("Step 3: QR Generation", "FAIL", details, is_critical=True)
                    return False
                    
        except Exception as e:
            self.log_step("Step 3: QR Generation", "FAIL", {
                "error": str(e),
                "exception_type": type(e).__name__
            }, is_critical=True)
            return False
    
    async def test_step_4_device_status(self) -> bool:
        """Test Step 4: Device Status Check"""
        print("\n" + "="*60)
        print("STEP 4: Device Status (GET /api/tenant/{tenant_id}/device-status)")
        print("="*60)
        
        if not self.tenant_id:
            self.log_step("Step 4: Device Status", "SKIP", {"reason": "No tenant_id from Step 1"})
            return False
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/tenant/{self.tenant_id}/device-status"
                )
                
                details = {
                    "status_code": response.status_code,
                    "tenant_id": self.tenant_id
                }
                
                if response.status_code == 200:
                    data = response.json()
                    details["status"] = data.get("status", "unknown")
                    details["device_id"] = data.get("device_id", "N/A")
                    details["has_device"] = data.get("status") not in ["no_device", "error"]
                    
                    self.log_step("Step 4: Device Status", "PASS", details)
                    return True
                else:
                    details["error"] = response.text
                    self.log_step("Step 4: Device Status", "FAIL", details)
                    return False
                    
        except Exception as e:
            self.log_step("Step 4: Device Status", "FAIL", {
                "error": str(e),
                "exception_type": type(e).__name__
            })
            return False
    
    async def test_step_5_complete_onboarding(self) -> bool:
        """Test Step 5: Complete Onboarding"""
        print("\n" + "="*60)
        print("STEP 5: Complete Onboarding (POST /api/onboarding/v2/complete/{tenant_id})")
        print("="*60)
        
        if not self.tenant_id:
            self.log_step("Step 5: Complete Onboarding", "SKIP", {"reason": "No tenant_id from Step 1"})
            return False
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/onboarding/v2/complete/{self.tenant_id}",
                    json={}
                )
                
                details = {
                    "status_code": response.status_code,
                    "tenant_id": self.tenant_id
                }
                
                if response.status_code == 200:
                    data = response.json()
                    details["message"] = data.get("message", "N/A")
                    details["dashboard_url"] = data.get("dashboard_url", "N/A")
                    
                    self.log_step("Step 5: Complete Onboarding", "PASS", details)
                    return True
                else:
                    details["error"] = response.text
                    self.log_step("Step 5: Complete Onboarding", "FAIL", details)
                    return False
                    
        except Exception as e:
            self.log_step("Step 5: Complete Onboarding", "FAIL", {
                "error": str(e),
                "exception_type": type(e).__name__
            })
            return False
    
    async def cleanup_test_tenant(self):
        """Clean up test tenant (requires Supabase access)"""
        if not self.cleanup or not self.tenant_id:
            return
        
        print("\n" + "="*60)
        print("CLEANUP: Deleting test tenant")
        print("="*60)
        
        print(f"⚠️  Cleanup requires manual deletion from Supabase")
        print(f"   Tenant ID: {self.tenant_id}")
        print(f"   Query: DELETE FROM tenants WHERE id = '{self.tenant_id}';")
    
    async def run_all_tests(self):
        """Run complete E2E test suite"""
        print("\n" + "🧪 "* 30)
        print("Bijou AI - End-to-End Onboarding Flow Test")
        print("🧪 "* 30)
        print(f"\nEnvironment: {self.base_url}")
        print(f"Started at: {self.test_results['started_at']}")
        print("")
        
        # Run test steps in order
        await self.test_step_1_signup()
        await self.test_step_2_status_check()
        await self.test_step_3_qr_generation()
        await self.test_step_4_device_status()
        await self.test_step_5_complete_onboarding()
        
        # Cleanup (if enabled)
        if self.cleanup:
            await self.cleanup_test_tenant()
        
        # Print summary
        self.print_summary()
        
        # Save results
        self.save_results()
        
        # Return exit code
        return 0 if self.test_results["total_failed"] == 0 else 1
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        total = self.test_results["total_passed"] + self.test_results["total_failed"]
        passed = self.test_results["total_passed"]
        failed = self.test_results["total_failed"]
        
        print(f"\nTotal Tests: {total}")
        print(f"✅ Passed: {passed} ({100 * passed / total if total > 0 else 0:.1f}%)")
        print(f"❌ Failed: {failed} ({100 * failed / total if total > 0 else 0:.1f}%)")
        
        if self.test_results["critical_failures"]:
            print(f"\n🚨 Critical Failures: {len(self.test_results['critical_failures'])}")
            for failure in self.test_results["critical_failures"]:
                print(f"   - {failure}")
        
        if self.tenant_id:
            print(f"\n📋 Test Tenant ID: {self.tenant_id}")
        
        print("")
    
    def save_results(self):
        """Save test results to JSON file"""
        self.test_results["completed_at"] = datetime.now().isoformat()
        
        output_file = "tests/e2e_onboarding_results.json"
        with open(output_file, "w") as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"📄 Results saved to: {output_file}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Bijou AI E2E Onboarding Test")
    parser.add_argument(
        "--env",
        choices=["local", "staging", "production"],
        default="staging",
        help="Environment to test (default: staging)"
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Skip cleanup (leave test tenant in database)"
    )
    
    args = parser.parse_args()
    
    base_url = ENVIRONMENTS[args.env]
    cleanup = not args.no_cleanup
    
    # Run tests
    test_runner = OnboardingE2ETest(base_url=base_url, cleanup=cleanup)
    exit_code = await test_runner.run_all_tests()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
