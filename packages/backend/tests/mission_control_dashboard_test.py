#!/usr/bin/env python3
"""
Mission Control - Dashboard Endpoint Comprehensive Test
========================================================

Tests ALL 9 dashboard endpoints and generates detailed report:
1. Google OAuth (/api/dashboard/google/auth-url)
2. Google Callback (/api/dashboard/google/callback)
3. Takeover (/api/dashboard/takeover)
4. Return to AI (/api/dashboard/return-to-ai/{jid})
5. Send Message (/api/dashboard/send-message)
6. Stats (/api/dashboard/stats)
7. Conversations (/api/dashboard/conversations)
8. Escalations (/api/dashboard/escalations)
9. Webhooks (/webhook/message, /webhook/connection)

Usage:
    python tests/mission_control_dashboard_test.py --env staging
    python tests/mission_control_dashboard_test.py --env production --verbose
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Tuple

import requests

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"


class DashboardTester:
    def __init__(self, base_url: str, verbose: bool = False):
        self.base_url = base_url.rstrip("/")
        self.verbose = verbose
        self.results: List[Tuple[str, int, str, str]] = []  # (endpoint, status_code, expected, details)
        self.start_time = datetime.now()
        
        # Default tenant for testing (pilot mode fallback)
        self.tenant_id = "00000000-0000-0000-0000-000000000001"
        self.test_jid = "60123456789@s.whatsapp.net"

    def log(self, message: str, color: str = RESET):
        """Print colored log message"""
        try:
            print(f"{color}{message}{RESET}")
        except UnicodeEncodeError:
            import re
            message_no_emoji = re.sub(r'[^\x00-\x7F]+', '', message)
            print(f"{color}{message_no_emoji}{RESET}")

    def record_result(self, endpoint: str, status_code: int, expected: str, details: str = ""):
        """Record test result"""
        self.results.append((endpoint, status_code, expected, details))
        
        # Determine pass/fail based on expected codes
        expected_codes = [int(c.strip()) for c in expected.split("/")]
        passed = status_code in expected_codes
        
        status_icon = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
        status_text = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        
        if self.verbose:
            self.log(f"  {status_icon} [{status_text}] {endpoint}: HTTP {status_code} (expected {expected})")
            if details:
                self.log(f"     → {details}", CYAN)

    def test_google_oauth_auth_url(self) -> bool:
        """Test 1: Google OAuth auth URL generation"""
        self.log(f"\n{BOLD}[1/9] Testing Google OAuth Auth URL...{RESET}", BLUE)
        
        try:
            response = requests.get(
                f"{self.base_url}/api/dashboard/google/auth-url",
                params={"tenant_id": self.tenant_id},
                timeout=10
            )
            
            details = ""
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "auth_url" in data:
                        details = "OAuth URL generated successfully"
                    else:
                        details = "Response missing 'auth_url' field"
                except:
                    details = "Invalid JSON response"
            elif response.status_code == 503:
                details = "Google OAuth not configured (expected in staging)"
            elif response.status_code == 500:
                # Check error message for Google OAuth config issue
                if "GOOGLE_CLIENT_ID" in response.text or "Google OAuth" in response.text:
                    details = "Google OAuth credentials missing (configuration issue)"
                else:
                    details = f"Server error: {response.text[:100]}"
            
            # Expected: 200 (configured) OR 503 (not configured)
            self.record_result(
                "GET /api/dashboard/google/auth-url",
                response.status_code,
                "200/503",
                details
            )
            return response.status_code in [200, 503]
            
        except Exception as e:
            self.record_result(
                "GET /api/dashboard/google/auth-url",
                0,
                "200/503",
                f"Error: {str(e)}"
            )
            return False

    def test_google_oauth_callback(self) -> bool:
        """Test 2: Google OAuth callback (without valid code)"""
        self.log(f"\n{BOLD}[2/9] Testing Google OAuth Callback...{RESET}", BLUE)
        
        try:
            # Test with missing parameters (should return 400)
            response = requests.get(
                f"{self.base_url}/api/dashboard/google/callback",
                params={"code": "", "state": ""},
                timeout=10
            )
            
            details = ""
            if response.status_code == 400:
                details = "Validation working (rejects empty code/state)"
            elif response.status_code == 503:
                details = "Google OAuth not configured"
            elif response.status_code == 500:
                details = f"Server error: {response.text[:100]}"
            
            # Expected: 400 (validation error) OR 503 (not configured)
            self.record_result(
                "GET /api/dashboard/google/callback",
                response.status_code,
                "400/503",
                details
            )
            return response.status_code in [400, 503]
            
        except Exception as e:
            self.record_result(
                "GET /api/dashboard/google/callback",
                0,
                "400/503",
                f"Error: {str(e)}"
            )
            return False

    def test_takeover(self) -> bool:
        """Test 3: Takeover endpoint"""
        self.log(f"\n{BOLD}[3/9] Testing Takeover Endpoint...{RESET}", BLUE)
        
        try:
            response = requests.post(
                f"{self.base_url}/api/dashboard/takeover",
                json={
                    "customer_jid": self.test_jid,
                    "agent_name": "Test Agent"
                },
                params={"tenant_id": self.tenant_id},
                timeout=10
            )
            
            details = ""
            if response.status_code == 403:
                details = "Access denied (customer not found - expected without DB data)"
            elif response.status_code == 400:
                details = "Validation error (missing fields)"
            elif response.status_code == 401:
                details = "Authentication required"
            elif response.status_code == 200:
                details = "Takeover successful"
            elif response.status_code == 500:
                details = f"Server error: {response.text[:100]}"
            
            # Expected: 403 (customer not found) OR 401 (auth required) OR 400 (validation)
            self.record_result(
                "POST /api/dashboard/takeover",
                response.status_code,
                "403/401/400",
                details
            )
            return response.status_code in [403, 401, 400]
            
        except Exception as e:
            self.record_result(
                "POST /api/dashboard/takeover",
                0,
                "403/401/400",
                f"Error: {str(e)}"
            )
            return False

    def test_return_to_ai(self) -> bool:
        """Test 4: Return to AI endpoint"""
        self.log(f"\n{BOLD}[4/9] Testing Return to AI Endpoint...{RESET}", BLUE)
        
        try:
            response = requests.post(
                f"{self.base_url}/api/dashboard/return-to-ai/{self.test_jid}",
                params={"agent_name": "Test Agent", "tenant_id": self.tenant_id},
                timeout=10
            )
            
            details = ""
            if response.status_code == 403:
                details = "Access denied (customer not found - expected)"
            elif response.status_code == 400:
                details = "Validation error"
            elif response.status_code == 401:
                details = "Authentication required"
            elif response.status_code == 200:
                details = "Return to AI successful"
            elif response.status_code == 500:
                details = f"Server error: {response.text[:100]}"
            
            # Expected: 403/401/400 (access denied or validation)
            self.record_result(
                "POST /api/dashboard/return-to-ai/{jid}",
                response.status_code,
                "403/401/400",
                details
            )
            return response.status_code in [403, 401, 400]
            
        except Exception as e:
            self.record_result(
                "POST /api/dashboard/return-to-ai/{jid}",
                0,
                "403/401/400",
                f"Error: {str(e)}"
            )
            return False

    def test_send_message(self) -> bool:
        """Test 5: Send message endpoint"""
        self.log(f"\n{BOLD}[5/9] Testing Send Message Endpoint...{RESET}", BLUE)
        
        try:
            response = requests.post(
                f"{self.base_url}/api/dashboard/send-message",
                json={
                    "customer_jid": self.test_jid,
                    "message": "Test message",
                    "agent_name": "Test Agent"
                },
                params={"tenant_id": self.tenant_id},
                timeout=15
            )
            
            details = ""
            if response.status_code == 200:
                details = "Message sent successfully"
            elif response.status_code == 503:
                details = "Bridge not configured (BRIDGE_URL missing - expected)"
            elif response.status_code == 401:
                details = "Authentication required"
            elif response.status_code == 400:
                details = "Validation error"
            elif response.status_code == 500:
                # Check if it's a bridge connectivity issue
                if "BRIDGE_URL" in response.text or "bridge" in response.text.lower():
                    details = "Bridge configuration error"
                else:
                    details = f"Server error: {response.text[:100]}"
            
            # Expected: 200/503/401/400 (success, not configured, auth, or validation)
            self.record_result(
                "POST /api/dashboard/send-message",
                response.status_code,
                "200/503/401/400",
                details
            )
            return response.status_code in [200, 503, 401, 400]
            
        except Exception as e:
            self.record_result(
                "POST /api/dashboard/send-message",
                0,
                "200/503/401/400",
                f"Error: {str(e)}"
            )
            return False

    def test_stats(self) -> bool:
        """Test 6: Stats endpoint"""
        self.log(f"\n{BOLD}[6/9] Testing Stats Endpoint...{RESET}", BLUE)
        
        try:
            response = requests.get(
                f"{self.base_url}/api/dashboard/stats",
                params={"tenant_id": self.tenant_id},
                timeout=10
            )
            
            details = ""
            if response.status_code == 200:
                try:
                    data = response.json()
                    required_fields = [
                        "active_conversations", "total_conversations", 
                        "ai_handled", "human_handled", "leads_generated_today",
                        "messages_today", "avg_response_time", "satisfaction_rate"
                    ]
                    missing = [f for f in required_fields if f not in data]
                    if missing:
                        details = f"Missing fields: {', '.join(missing)}"
                    else:
                        details = f"All fields present ({data.get('active_conversations', 0)} active conversations)"
                except:
                    details = "Invalid JSON response"
            elif response.status_code == 401:
                details = "Authentication required"
            elif response.status_code == 500:
                details = f"Server error: {response.text[:100]}"
            
            # Expected: 200 (success) OR 401 (auth required)
            self.record_result(
                "GET /api/dashboard/stats",
                response.status_code,
                "200/401",
                details
            )
            return response.status_code in [200, 401]
            
        except Exception as e:
            self.record_result(
                "GET /api/dashboard/stats",
                0,
                "200/401",
                f"Error: {str(e)}"
            )
            return False

    def test_conversations(self) -> bool:
        """Test 7: Conversations endpoint"""
        self.log(f"\n{BOLD}[7/9] Testing Conversations Endpoint...{RESET}", BLUE)
        
        try:
            response = requests.get(
                f"{self.base_url}/api/dashboard/conversations",
                params={"tenant_id": self.tenant_id, "limit": 10},
                timeout=10
            )
            
            details = ""
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        details = f"Returned {len(data)} conversations"
                        if len(data) > 0 and "customer_phone" in data[0]:
                            details += " (with phone numbers)"
                    else:
                        details = "Invalid response format (expected array)"
                except:
                    details = "Invalid JSON response"
            elif response.status_code == 401:
                details = "Authentication required"
            elif response.status_code == 500:
                details = f"Server error: {response.text[:100]}"
            
            # Expected: 200 OR 401
            self.record_result(
                "GET /api/dashboard/conversations",
                response.status_code,
                "200/401",
                details
            )
            return response.status_code in [200, 401]
            
        except Exception as e:
            self.record_result(
                "GET /api/dashboard/conversations",
                0,
                "200/401",
                f"Error: {str(e)}"
            )
            return False

    def test_escalations(self) -> bool:
        """Test 8: Escalations endpoint"""
        self.log(f"\n{BOLD}[8/9] Testing Escalations Endpoint...{RESET}", BLUE)
        
        try:
            # Test without status filter (should return all statuses)
            response = requests.get(
                f"{self.base_url}/api/dashboard/escalations",
                params={"tenant_id": self.tenant_id},
                timeout=10
            )
            
            details = ""
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        details = f"Returned {len(data)} escalations (all statuses)"
                        if len(data) > 0:
                            statuses = set(e.get("status") for e in data if "status" in e)
                            details += f" - statuses: {', '.join(statuses)}"
                    else:
                        details = "Invalid response format"
                except:
                    details = "Invalid JSON response"
            elif response.status_code == 401:
                details = "Authentication required"
            elif response.status_code == 500:
                details = f"Server error: {response.text[:100]}"
            
            # Expected: 200 OR 401
            self.record_result(
                "GET /api/dashboard/escalations",
                response.status_code,
                "200/401",
                details
            )
            return response.status_code in [200, 401]
            
        except Exception as e:
            self.record_result(
                "GET /api/dashboard/escalations",
                0,
                "200/401",
                f"Error: {str(e)}"
            )
            return False

    def test_webhooks(self) -> bool:
        """Test 9: Webhook endpoints"""
        self.log(f"\n{BOLD}[9/9] Testing Webhook Endpoints...{RESET}", BLUE)
        
        all_passed = True
        
        # Test 9a: Message webhook
        try:
            response = requests.post(
                f"{self.base_url}/webhook/message",
                json={},
                timeout=10
            )
            
            details = ""
            if response.status_code in [400, 422]:
                details = "Validation working (rejects empty payload)"
            elif response.status_code == 200:
                details = "Webhook accepted empty payload (needs validation fix)"
            elif response.status_code == 500:
                details = f"Server error: {response.text[:100]}"
            
            # Expected: 400/422 (validation error)
            self.record_result(
                "POST /webhook/message",
                response.status_code,
                "400/422",
                details
            )
            if response.status_code not in [400, 422]:
                all_passed = False
                
        except Exception as e:
            self.record_result(
                "POST /webhook/message",
                0,
                "400/422",
                f"Error: {str(e)}"
            )
            all_passed = False
        
        # Test 9b: Connection webhook
        try:
            response = requests.post(
                f"{self.base_url}/webhook/connection",
                json={},
                timeout=10
            )
            
            details = ""
            if response.status_code in [400, 422]:
                details = "Validation working"
            elif response.status_code == 500:
                details = f"Server error: {response.text[:100]}"
            
            # Expected: 400/422
            self.record_result(
                "POST /webhook/connection",
                response.status_code,
                "400/422",
                details
            )
            if response.status_code not in [400, 422]:
                all_passed = False
                
        except Exception as e:
            self.record_result(
                "POST /webhook/connection",
                0,
                "400/422",
                f"Error: {str(e)}"
            )
            all_passed = False
        
        return all_passed

    def run_all_tests(self) -> bool:
        """Run all dashboard endpoint tests"""
        self.log(f"\n{'='*70}")
        self.log(f"{BOLD}🎯 MISSION CONTROL - DASHBOARD ENDPOINT TEST SUITE{RESET}", MAGENTA)
        self.log(f"{'='*70}")
        self.log(f"Environment: {self.base_url}")
        self.log(f"Tenant ID: {self.tenant_id}")
        self.log(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all tests
        tests = [
            self.test_google_oauth_auth_url,
            self.test_google_oauth_callback,
            self.test_takeover,
            self.test_return_to_ai,
            self.test_send_message,
            self.test_stats,
            self.test_conversations,
            self.test_escalations,
            self.test_webhooks,
        ]
        
        for test in tests:
            try:
                test()
                time.sleep(0.5)  # Small delay between tests
            except Exception as e:
                self.log(f"{RED}Unexpected error in {test.__name__}: {e}{RESET}")
        
        # Print summary
        self.print_summary()
        
        # Return overall status
        return self.calculate_pass_rate() >= 80.0

    def calculate_pass_rate(self) -> float:
        """Calculate test pass rate"""
        if not self.results:
            return 0.0
        
        passed = 0
        for endpoint, status_code, expected, _ in self.results:
            expected_codes = [int(c.strip()) for c in expected.split("/")]
            if status_code in expected_codes:
                passed += 1
        
        return (passed / len(self.results)) * 100

    def print_summary(self):
        """Print comprehensive test summary"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        # Calculate statistics
        passed = 0
        failed = 0
        errors_500 = 0
        errors_validation = 0
        errors_auth = 0
        errors_config = 0
        
        for endpoint, status_code, expected, details in self.results:
            expected_codes = [int(c.strip()) for c in expected.split("/")]
            if status_code in expected_codes:
                passed += 1
            else:
                failed += 1
                if status_code == 500:
                    errors_500 += 1
                elif status_code in [400, 422]:
                    errors_validation += 1
                elif status_code in [401, 403]:
                    errors_auth += 1
                elif status_code == 503:
                    errors_config += 1
        
        total = len(self.results)
        pass_rate = self.calculate_pass_rate()
        
        self.log(f"\n{'='*70}")
        self.log(f"{BOLD}📊 TEST SUMMARY{RESET}", CYAN)
        self.log(f"{'='*70}")
        
        # Overall statistics
        self.log(f"\n{BOLD}Overall Results:{RESET}")
        self.log(f"  Total Endpoints Tested: {total}")
        self.log(f"  Passed: {passed}", GREEN if passed == total else YELLOW)
        self.log(f"  Failed: {failed}", RED if failed > 0 else GREEN)
        self.log(f"  Pass Rate: {pass_rate:.1f}%", GREEN if pass_rate >= 80 else RED)
        self.log(f"  Duration: {duration:.2f}s")
        
        # Error breakdown
        if failed > 0:
            self.log(f"\n{BOLD}Error Breakdown:{RESET}")
            if errors_500 > 0:
                self.log(f"  500 Errors (Server): {errors_500}", RED)
            if errors_validation > 0:
                self.log(f"  400/422 Errors (Validation): {errors_validation}", YELLOW)
            if errors_auth > 0:
                self.log(f"  401/403 Errors (Auth): {errors_auth}", YELLOW)
            if errors_config > 0:
                self.log(f"  503 Errors (Config): {errors_config}", YELLOW)
        
        # Detailed results
        self.log(f"\n{BOLD}Detailed Results:{RESET}")
        for endpoint, status_code, expected, details in self.results:
            expected_codes = [int(c.strip()) for c in expected.split("/")]
            passed_test = status_code in expected_codes
            
            icon = f"{GREEN}✓{RESET}" if passed_test else f"{RED}✗{RESET}"
            status_color = GREEN if passed_test else RED
            
            self.log(f"  {icon} {endpoint}")
            self.log(f"     Status: {status_color}{status_code}{RESET} (expected: {expected})")
            if details:
                self.log(f"     Details: {details}", CYAN)
        
        # Final verdict
        self.log(f"\n{'='*70}")
        if pass_rate >= 80:
            self.log(f"{GREEN}{BOLD}✅ TESTS PASSED - DASHBOARD ENDPOINTS HEALTHY{RESET}")
            self.log(f"{GREEN}Pass rate {pass_rate:.1f}% meets threshold (>= 80%){RESET}")
        else:
            self.log(f"{RED}{BOLD}❌ TESTS FAILED - DASHBOARD NEEDS FIXES{RESET}")
            self.log(f"{RED}Pass rate {pass_rate:.1f}% below threshold (< 80%){RESET}")
            
            # Suggest next steps
            if errors_500 > 0:
                self.log(f"\n{YELLOW}⚠️  Action Required:{RESET}")
                self.log(f"  - {errors_500} endpoint(s) returning 500 errors")
                self.log(f"  - Check server logs and database connectivity")
                self.log(f"  - Verify environment variables (BRIDGE_URL, GOOGLE_CLIENT_ID, etc.)")
        
        self.log(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Mission Control - Dashboard Endpoint Comprehensive Test"
    )
    parser.add_argument(
        "--env",
        choices=["staging", "production", "local"],
        default="staging",
        help="Environment to test"
    )
    parser.add_argument(
        "--base-url",
        help="Override base URL"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output with detailed logging"
    )
    
    args = parser.parse_args()
    
    # Environment URLs
    env_config = {
        "staging": "https://bijou-staging.fly.dev",
        "production": "https://bijou-production.fly.dev",
        "local": "http://localhost:8000",
    }
    
    base_url = args.base_url or env_config[args.env]
    
    # Run tests
    tester = DashboardTester(base_url, verbose=args.verbose)
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
