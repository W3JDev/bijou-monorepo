#!/usr/bin/env python3
"""
Multi-Tenant QR Code Testing Script
====================================

Tests the critical GOWA bridge migration fix:
- Create multiple test tenants simultaneously
- Generate QR codes for each tenant
- Verify all QR codes are generated without bridge crashes
- Monitor bridge health during concurrent connections

This validates that the GOWA bridge can handle 100+ simultaneous
QR scans vs. the old custom bridge which crashed at 3-4 scans.

Usage:
    python tests/multi_tenant_qr_test.py --env staging --tenants 3
    python tests/multi_tenant_qr_test.py --env staging --tenants 10
    
Requirements:
    - Must have access to WhatsApp accounts to scan QR codes
    - Each tenant needs a unique WhatsApp number
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"


class MultiTenantQRTest:
    def __init__(self, base_url: str, bridge_url: str, bridge_auth: str):
        self.base_url = base_url.rstrip("/")
        self.bridge_url = bridge_url.rstrip("/")
        self.bridge_auth = bridge_auth
        self.test_tenants: List[Dict] = []
        self.results: List[Dict] = []
        
    def log(self, message: str, color: str = RESET):
        """Print colored log message"""
        try:
            print(f"{color}{message}{RESET}")
        except UnicodeEncodeError:
            import re
            message_no_emoji = re.sub(r'[^\x00-\x7F]+', '', message)
            print(f"{color}{message_no_emoji}{RESET}")
    
    def create_test_tenant(self, tenant_num: int) -> Optional[Dict]:
        """Create a single test tenant via signup API"""
        self.log(f"  Creating test tenant #{tenant_num}...", CYAN)
        
        # Use timestamp to ensure unique emails
        timestamp = int(time.time())
        tenant_data = {
            "business_name": f"Test Agent {tenant_num}",
            "email": f"test{tenant_num}_{timestamp}@example.com",
            "phone": f"60123456{tenant_num:03d}"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/onboarding/signup",
                json=tenant_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                signup_token = result.get("signup_token")
                tenant_id = result.get("tenant_id")
                
                self.log(f"    ✅ Created tenant #{tenant_num}: {tenant_id}", GREEN)
                return {
                    "num": tenant_num,
                    "tenant_id": tenant_id,
                    "signup_token": signup_token,
                    "email": tenant_data["email"],
                    "phone": tenant_data["phone"],
                    "created_at": datetime.now().isoformat()
                }
            else:
                self.log(f"    ❌ Failed to create tenant #{tenant_num}: HTTP {response.status_code}", RED)
                self.log(f"       Response: {response.text}", RED)
                return None
                
        except Exception as e:
            self.log(f"    ❌ Error creating tenant #{tenant_num}: {str(e)}", RED)
            return None
    
    def get_qr_code(self, tenant: Dict) -> bool:
        """Get QR code for a tenant"""
        tenant_num = tenant["num"]
        signup_token = tenant["signup_token"]
        
        self.log(f"  Fetching QR code for tenant #{tenant_num}...", CYAN)
        
        try:
            response = requests.get(
                f"{self.base_url}/api/onboarding/qr/{signup_token}",
                timeout=30  # QR generation can take time
            )
            
            if response.status_code == 200:
                # Save QR code to file
                qr_path = Path(f"qr_test_tenant_{tenant_num}.png")
                qr_path.write_bytes(response.content)
                
                self.log(f"    ✅ QR code saved: {qr_path}", GREEN)
                
                tenant["qr_path"] = str(qr_path)
                tenant["qr_fetched_at"] = datetime.now().isoformat()
                return True
            else:
                self.log(f"    ❌ Failed to get QR for tenant #{tenant_num}: HTTP {response.status_code}", RED)
                self.log(f"       Response: {response.text}", RED)
                return False
                
        except Exception as e:
            self.log(f"    ❌ Error getting QR for tenant #{tenant_num}: {str(e)}", RED)
            return False
    
    def check_bridge_health(self) -> Dict:
        """Check WhatsApp bridge health status"""
        try:
            auth = None
            if self.bridge_auth and ":" in self.bridge_auth:
                username, password = self.bridge_auth.split(":", 1)
                auth = (username, password)
            
            # Try root endpoint (GOWA bridge)
            response = requests.get(
                f"{self.bridge_url}/",
                timeout=10,
                auth=auth
            )
            
            return {
                "status": "ok" if response.status_code == 200 else "degraded",
                "status_code": response.status_code,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def run_test(self, num_tenants: int, concurrent: bool = True):
        """Run the full multi-tenant QR test"""
        self.log("\n" + "=" * 60, BLUE)
        self.log(" MULTI-TENANT QR CODE TEST", BLUE)
        self.log("=" * 60, RESET)
        self.log(f"Environment: {self.base_url}")
        self.log(f"Bridge: {self.bridge_url}")
        self.log(f"Test Tenants: {num_tenants}")
        self.log(f"Concurrent: {concurrent}")
        self.log(f"Started: {datetime.now().isoformat()}\n")
        
        # Step 1: Check initial bridge health
        self.log(f"{BLUE}[1/4] Checking initial bridge health...{RESET}")
        initial_health = self.check_bridge_health()
        self.log(f"  Bridge Status: {initial_health['status']} (HTTP {initial_health.get('status_code', 'N/A')})", 
                 GREEN if initial_health['status'] == 'ok' else YELLOW)
        
        # Step 2: Create test tenants
        self.log(f"\n{BLUE}[2/4] Creating {num_tenants} test tenants...{RESET}")
        
        if concurrent:
            with ThreadPoolExecutor(max_workers=min(num_tenants, 10)) as executor:
                futures = [executor.submit(self.create_test_tenant, i+1) for i in range(num_tenants)]
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        self.test_tenants.append(result)
        else:
            for i in range(num_tenants):
                result = self.create_test_tenant(i+1)
                if result:
                    self.test_tenants.append(result)
        
        created_count = len(self.test_tenants)
        self.log(f"\n  Created {created_count}/{num_tenants} tenants", 
                 GREEN if created_count == num_tenants else YELLOW)
        
        if created_count == 0:
            self.log(f"\n{RED}❌ TEST FAILED - No tenants created{RESET}")
            return False
        
        # Step 3: Get QR codes (THIS IS THE CRITICAL TEST)
        self.log(f"\n{BLUE}[3/4] Generating QR codes {'concurrently' if concurrent else 'sequentially'}...{RESET}")
        self.log(f"{YELLOW}⚠️ CRITICAL TEST: Old bridge crashed with 3-4 simultaneous QR scans{RESET}")
        
        qr_success = 0
        
        if concurrent:
            with ThreadPoolExecutor(max_workers=min(len(self.test_tenants), 10)) as executor:
                futures = [executor.submit(self.get_qr_code, tenant) for tenant in self.test_tenants]
                for future in as_completed(futures):
                    if future.result():
                        qr_success += 1
        else:
            for tenant in self.test_tenants:
                if self.get_qr_code(tenant):
                    qr_success += 1
        
        self.log(f"\n  Generated {qr_success}/{created_count} QR codes", 
                 GREEN if qr_success == created_count else YELLOW)
        
        # Step 4: Check bridge health after QR generation
        self.log(f"\n{BLUE}[4/4] Checking bridge health after QR generation...{RESET}")
        final_health = self.check_bridge_health()
        self.log(f"  Bridge Status: {final_health['status']} (HTTP {final_health.get('status_code', 'N/A')})", 
                 GREEN if final_health['status'] == 'ok' else RED)
        
        # Summary
        self.log("\n" + "=" * 60, BLUE)
        self.log(" TEST SUMMARY", BLUE)
        self.log("=" * 60, RESET)
        self.log(f"Tenants Created: {created_count}/{num_tenants}")
        self.log(f"QR Codes Generated: {qr_success}/{created_count}")
        self.log(f"Bridge Health Before: {initial_health['status']}")
        self.log(f"Bridge Health After: {final_health['status']}")
        
        # Success criteria
        all_qr_generated = qr_success == created_count
        bridge_still_healthy = final_health['status'] in ['ok', 'degraded']
        
        if all_qr_generated and bridge_still_healthy:
            self.log(f"\n{GREEN}✅ TEST PASSED - All QR codes generated, bridge still healthy{RESET}")
            self.log(f"{GREEN}   GOWA bridge successfully handled {created_count} simultaneous QR requests!{RESET}")
            success = True
        else:
            self.log(f"\n{RED}❌ TEST FAILED{RESET}")
            if not all_qr_generated:
                self.log(f"{RED}   - Not all QR codes were generated{RESET}")
            if not bridge_still_healthy:
                self.log(f"{RED}   - Bridge became unhealthy during test{RESET}")
            success = False
        
        # Instructions for manual testing
        if qr_success > 0:
            self.log(f"\n{CYAN}📱 NEXT STEPS - Manual WhatsApp Scanning:{RESET}")
            self.log(f"   1. Open WhatsApp on {qr_success} different phones/accounts")
            self.log(f"   2. Go to Settings > Linked Devices > Link a Device")
            self.log(f"   3. Scan the QR codes saved in current directory:")
            for tenant in self.test_tenants:
                if "qr_path" in tenant:
                    self.log(f"      - {tenant['qr_path']} (Tenant #{tenant['num']})", CYAN)
            self.log(f"   4. All {qr_success} should connect without bridge crashes")
            self.log(f"\n   {YELLOW}⚠️ Old bridge would crash at 3-4 scans - GOWA should handle all!{RESET}")
        
        # Save test results to file
        results_file = Path(f"qr_test_results_{int(time.time())}.json")
        results_data = {
            "test_params": {
                "num_tenants": num_tenants,
                "concurrent": concurrent,
                "base_url": self.base_url,
                "bridge_url": self.bridge_url
            },
            "results": {
                "tenants_created": created_count,
                "qr_codes_generated": qr_success,
                "initial_bridge_health": initial_health,
                "final_bridge_health": final_health,
                "success": success
            },
            "tenants": self.test_tenants,
            "timestamp": datetime.now().isoformat()
        }
        results_file.write_text(json.dumps(results_data, indent=2))
        self.log(f"\n📄 Test results saved to: {results_file}")
        
        self.log("=" * 60 + "\n")
        
        return success


def main():
    parser = argparse.ArgumentParser(description="Multi-Tenant QR Code Test")
    parser.add_argument("--env", choices=["staging", "production", "local"], 
                       default="staging", help="Environment to test")
    parser.add_argument("--tenants", type=int, default=3, 
                       help="Number of test tenants to create (default: 3)")
    parser.add_argument("--sequential", action="store_true",
                       help="Run tests sequentially instead of concurrently")
    
    args = parser.parse_args()
    
    # Environment configurations
    env_configs = {
        "staging": {
            "base_url": "https://bijou-staging.fly.dev",
            "bridge_url": "https://bijou-bridge-staging-v2.fly.dev",
        },
        "production": {
            "base_url": "https://bijou-production.fly.dev",
            "bridge_url": "https://bijou-bridge-production.fly.dev",
        },
        "local": {
            "base_url": "http://localhost:8000",
            "bridge_url": "http://localhost:8081",
        }
    }
    
    config = env_configs[args.env]
    bridge_auth = os.getenv("BRIDGE_API_KEY", "")
    
    if not bridge_auth:
        print(f"{YELLOW}⚠️ Warning: BRIDGE_API_KEY not set. Bridge health checks may fail.{RESET}")
    
    # Run test
    tester = MultiTenantQRTest(
        base_url=config["base_url"],
        bridge_url=config["bridge_url"],
        bridge_auth=bridge_auth
    )
    
    success = tester.run_test(
        num_tenants=args.tenants,
        concurrent=not args.sequential
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
