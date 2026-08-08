#!/usr/bin/env python3
"""
Bijou Enterprise API Test Runner
Environment: Staging (bijou-staging.fly.dev)
Date: 2026-02-18
"""

import json
import subprocess
from datetime import datetime
from typing import Dict, List, Tuple

BASE_URL = "https://bijou-staging.fly.dev"
TENANT_ID = "1e63900e-1b83-4dc8-ba55-9d619eae0866"  # Test tenant
SIGNUP_TOKEN = "puYlMVGrBe7vJZmHg0CxrE"  # Customer B

# Results storage
results = {
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "environment": "staging",
    "base_url": BASE_URL,
    "total_requests": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "results": {},
    "critical_failures": [],
    "onboarding_health": {}
}

log_lines = []

def log(message: str):
    """Log message to both console and log file"""
    print(message)
    log_lines.append(message)

def test_endpoint(
    method: str,
    path: str,
    description: str,
    expected_status: int = 200,
    category: str = "general",
    headers: Dict[str, str] = None,
    body: Dict = None,
    skip: bool = False
) -> Tuple[bool, int, str]:
    """Test a single endpoint"""
    results["total_requests"] += 1
    
    if skip:
        results["skipped"] += 1
        log(f"⏭️  SKIPPED: {method} {path} - {description}")
        return True, 0, "skipped"
    
    # Build curl command
    cmd = ["curl", "-s", "-w", "\\n%{http_code}", "-X", method, f"{BASE_URL}{path}"]
    
    if headers:
        for key, value in headers.items():
            cmd.extend(["-H", f"{key}: {value}"])
    
    if body:
        cmd.extend(["-H", "Content-Type: application/json", "-d", json.dumps(body)])
    
    try:
        output = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        response_text = output.stdout
        
        # Split response and status code
        lines = response_text.strip().split('\n')
        http_code = int(lines[-1]) if lines[-1].isdigit() else 0
        body_response = '\n'.join(lines[:-1]) if len(lines) > 1 else ""
        
        # Determine if test passed
        passed = http_code == expected_status
        
        # Store result
        if category not in results["results"]:
            results["results"][category] = {}
        
        results["results"][category][f"{method} {path}"] = {
            "status": "passed" if passed else "failed",
            "description": description,
            "status_code": http_code,
            "expected_code": expected_status,
            "response_time_ms": 0,  # Not measuring for now
            "response_body": body_response[:500]  # Truncate
        }
        
        if passed:
            results["passed"] += 1
            log(f"✅ PASSED: {method} {path} - HTTP {http_code}")
        else:
            results["failed"] += 1
            log(f"❌ FAILED: {method} {path} - HTTP {http_code} (expected {expected_status})")
            log(f"   Response: {body_response[:200]}")
            
            # Track critical failures
            if category in ["health", "onboarding"] or expected_status == 200:
                results["critical_failures"].append({
                    "endpoint": f"{method} {path}",
                    "category": category,
                    "impact": "high" if category == "onboarding" else "medium",
                    "reason": f"HTTP {http_code} instead of {expected_status}",
                    "recommendation": "Check logs and service configuration"
                })
        
        return passed, http_code, body_response
    
    except Exception as e:
        results["failed"] += 1
        log(f"❌ ERROR: {method} {path} - {str(e)}")
        return False, 0, str(e)

# ========== RUN TESTS ==========

log("=" * 60)
log("Bijou Enterprise API Test Run")
log(f"Started: {results['timestamp']}")
log(f"Base URL: {BASE_URL}")
log("=" * 60)
log("")

# HEALTH & SYSTEM
log("=== Testing Health & System Endpoints ===")
test_endpoint("GET", "/health", "Basic health check", 200, "health")
test_endpoint("GET", "/status", "System status", 200, "health")
test_endpoint("GET", "/bridge/health", "WhatsApp bridge health", 200, "health")
test_endpoint("GET", "/postman-collection", "Postman collection export", 200, "health")

# ONBOARDING V1 (DEPRECATED - Use V2 for new integrations)
log("\n=== Testing Onboarding V1 Endpoints ===")
test_endpoint("GET", "/api/onboarding/health", "Onboarding service health", 200, "onboarding")
# V1 status endpoint deprecated - expects signup_token which may not exist
# test_endpoint("GET", f"/api/onboarding/status/{SIGNUP_TOKEN}", "Get onboarding status by token (deprecated)", 404, "onboarding")

# ONBOARDING V2
log("\n=== Testing Onboarding V2 Endpoints ===")
passed, code, body = test_endpoint("GET", f"/api/onboarding/v2/status/{TENANT_ID}", "Get onboarding V2 status", 200, "onboarding")
if passed:
    try:
        data = json.loads(body)
        results["onboarding_health"]["status_check"] = "working"
        results["onboarding_health"]["current_step"] = data.get("progress", {}).get("current_step")
    except:
        pass

test_endpoint("GET", f"/api/onboarding/v2/whatsapp/qr/{TENANT_ID}", "Generate QR code", 200, "onboarding")

# DASHBOARD
log("\n=== Testing Dashboard Endpoints ===")
headers = {"X-Tenant-ID": TENANT_ID}
test_endpoint("GET", "/api/dashboard/stats", "Dashboard stats", 200, "dashboard", headers=headers)
test_endpoint("GET", "/api/dashboard/conversations", "List conversations", 200, "dashboard", headers=headers)
test_endpoint("GET", "/api/dashboard/escalations", "List escalations", 200, "dashboard", headers=headers)
test_endpoint("GET", "/api/dashboard/whatsapp/status", "WhatsApp connection status", 200, "dashboard", headers=headers)
test_endpoint("GET", "/api/dashboard/agents", "List agents", 200, "dashboard", headers=headers)

# KNOWLEDGE BASE
log("\n=== Testing Knowledge Base Endpoints ===")
test_endpoint("GET", "/api/knowledge/health", "Knowledge service health", 200, "knowledge")
test_endpoint("GET", "/api/knowledge/list", "List knowledge documents", 200, "knowledge", headers=headers)

# SETTINGS
log("\n=== Testing Settings Endpoints ===")
test_endpoint("GET", "/api/settings/health", "Settings service health", 200, "settings")

# ADMIN (read-only)
log("\n=== Testing Admin Endpoints (Read-Only) ===")
test_endpoint("GET", "/api/admin/tenants", "List all tenants", 200, "admin")

# PROACTIVE MESSAGING
log("\n=== Testing Proactive Messaging Endpoints ===")
test_endpoint("GET", "/api/proactive/status", "Proactive messaging status", 200, "proactive", headers=headers)
test_endpoint("GET", "/api/proactive/campaigns", "List campaigns", 200, "proactive", headers=headers)
test_endpoint("GET", "/api/proactive/scheduled", "List scheduled messages", 200, "proactive", headers=headers)

# TENANT DEVICE
log("\n=== Testing Tenant Device Status ===")
test_endpoint("GET", f"/api/tenant/{TENANT_ID}/device/status", "Device status", 200, "tenant")

# WEBHOOKS (SKIP - require special auth)
log("\n=== Testing Webhooks (SKIPPED - requires auth) ===")
test_endpoint("POST", "/webhook/message", "WhatsApp message webhook", 200, "webhooks", skip=True)
test_endpoint("POST", "/webhook/connection", "WhatsApp connection webhook", 200, "webhooks", skip=True)
test_endpoint("POST", "/api/webhook", "Generic webhook", 200, "webhooks", skip=True)

# ========== SUMMARY ==========
log("\n" + "=" * 60)
log("Test Summary")
log("=" * 60)
log(f"Total Tests: {results['total_requests']}")
log(f"Passed: {results['passed']}")
log(f"Failed: {results['failed']}")
log(f"Skipped: {results['skipped']}")
if results['total_requests'] > 0:
    success_rate = (results['passed'] * 100) / (results['total_requests'] - results['skipped'])
    log(f"Success Rate: {success_rate:.1f}%")
log("=" * 60)

# Critical failures summary
if results['critical_failures']:
    log(f"\n⚠️  Critical Failures: {len(results['critical_failures'])}")
    for failure in results['critical_failures'][:5]:  # Show first 5
        log(f"  - {failure['endpoint']}: {failure['reason']}")

# Onboarding health assessment
results["onboarding_health"]["signup_working"] = any(
    r.get("status") == "passed" 
    for r in results["results"].get("onboarding", {}).values()
)
results["onboarding_health"]["qr_generation_working"] = False  # Will update based on QR test
results["onboarding_health"]["payment_integration_working"] = False  # Cannot test without Stripe
results["onboarding_health"]["whatsapp_webhook_working"] = "unknown"  # Skipped

# Save results
with open("tests/api_report.json", "w") as f:
    json.dump(results, f, indent=2)

with open("tests/postman_run.log", "w") as f:
    f.write("\n".join(log_lines))

log(f"\n✅ Results saved to:")
log(f"   - tests/api_report.json")
log(f"   - tests/postman_run.log")

