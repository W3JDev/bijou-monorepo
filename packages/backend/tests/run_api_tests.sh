#!/bin/bash

# Bijou Enterprise API Test Runner
# Environment: Staging (bijou-staging.fly.dev)
# Date: 2026-02-18

BASE_URL="https://bijou-staging.fly.dev"
RESULTS_DIR="tests/api_results"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Test tenant from samples
TENANT_ID="1e63900e-1b83-4dc8-ba55-9d619eae0866"
SIGNUP_TOKEN="puYl...CxrE"  # Customer B token

mkdir -p "$RESULTS_DIR"

echo "========================================" | tee tests/postman_run.log
echo "Bijou Enterprise API Test Run" | tee -a tests/postman_run.log
echo "Started: $TIMESTAMP" | tee -a tests/postman_run.log
echo "Base URL: $BASE_URL" | tee -a tests/postman_run.log
echo "========================================" | tee -a tests/postman_run.log
echo "" | tee -a tests/postman_run.log

# Counter variables
TOTAL=0
PASSED=0
FAILED=0
SKIPPED=0

# Test function
test_endpoint() {
    local METHOD=$1
    local PATH=$2
    local DESCRIPTION=$3
    local EXPECTED_STATUS=${4:-200}
    local BODY=${5:-""}
    local HEADERS=${6:-""}
    
    TOTAL=$((TOTAL + 1))
    
    echo "[$TIMESTAMP] Testing: $METHOD $PATH - $DESCRIPTION" | tee -a tests/postman_run.log
    
    if [ -n "$BODY" ]; then
        RESPONSE=$(curl -s -w "\n%{http_code}" -X $METHOD "$BASE_URL$PATH" \
            -H "Content-Type: application/json" \
            $HEADERS \
            -d "$BODY")
    else
        RESPONSE=$(curl -s -w "\n%{http_code}" -X $METHOD "$BASE_URL$PATH" $HEADERS)
    fi
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY_RESPONSE=$(echo "$RESPONSE" | sed '$d')
    
    # Save response
    echo "$BODY_RESPONSE" > "$RESULTS_DIR/$(echo $PATH | tr '/' '_').json"
    
    if [ "$HTTP_CODE" -eq "$EXPECTED_STATUS" ]; then
        echo "✅ PASSED - HTTP $HTTP_CODE (expected $EXPECTED_STATUS)" | tee -a tests/postman_run.log
        PASSED=$((PASSED + 1))
    else
        echo "❌ FAILED - HTTP $HTTP_CODE (expected $EXPECTED_STATUS)" | tee -a tests/postman_run.log
        echo "   Response: $BODY_RESPONSE" | tee -a tests/postman_run.log
        FAILED=$((FAILED + 1))
    fi
    
    echo "" | tee -a tests/postman_run.log
}

# ===== HEALTH & SYSTEM ENDPOINTS =====
echo "=== Testing Health & System Endpoints ===" | tee -a tests/postman_run.log

test_endpoint "GET" "/health" "Basic health check" 200
test_endpoint "GET" "/status" "System status" 200
test_endpoint "GET" "/bridge/health" "WhatsApp bridge health" 200
test_endpoint "GET" "/postman-collection" "Get Postman collection" 200

# ===== ONBOARDING ENDPOINTS =====
echo "=== Testing Onboarding Endpoints (V1) ===" | tee -a tests/postman_run.log

test_endpoint "GET" "/api/onboarding/health" "Onboarding service health" 200
test_endpoint "GET" "/api/onboarding/status/$SIGNUP_TOKEN" "Get onboarding status" 200

# ===== ONBOARDING V2 ENDPOINTS =====
echo "=== Testing Onboarding V2 Endpoints ===" | tee -a tests/postman_run.log

test_endpoint "GET" "/api/onboarding/v2/status/$TENANT_ID" "Get onboarding V2 status" 200
test_endpoint "GET" "/api/onboarding/v2/whatsapp/qr/$TENANT_ID" "Get QR code for WhatsApp" 200

# ===== DASHBOARD ENDPOINTS =====
echo "=== Testing Dashboard Endpoints ===" | tee -a tests/postman_run.log

test_endpoint "GET" "/api/dashboard/stats" "Get dashboard stats" 200 "" "-H 'X-Tenant-ID: $TENANT_ID'"
test_endpoint "GET" "/api/dashboard/conversations" "Get conversations" 200 "" "-H 'X-Tenant-ID: $TENANT_ID'"
test_endpoint "GET" "/api/dashboard/escalations" "Get escalations" 200 "" "-H 'X-Tenant-ID: $TENANT_ID'"
test_endpoint "GET" "/api/dashboard/whatsapp/status" "Get WhatsApp status" 200 "" "-H 'X-Tenant-ID: $TENANT_ID'"
test_endpoint "GET" "/api/dashboard/agents" "Get agents list" 200 "" "-H 'X-Tenant-ID: $TENANT_ID'"

# ===== KNOWLEDGE BASE ENDPOINTS =====
echo "=== Testing Knowledge Base Endpoints ===" | tee -a tests/postman_run.log

test_endpoint "GET" "/api/knowledge/health" "Knowledge service health" 200
test_endpoint "GET" "/api/knowledge/list" "List knowledge documents" 200 "" "-H 'X-Tenant-ID: $TENANT_ID'"

# ===== SETTINGS ENDPOINTS =====
echo "=== Testing Settings Endpoints ===" | tee -a tests/postman_run.log

test_endpoint "GET" "/api/settings/health" "Settings service health" 200

# ===== ADMIN ENDPOINTS (Read-only) =====
echo "=== Testing Admin Endpoints ===" | tee -a tests/postman_run.log

test_endpoint "GET" "/api/admin/tenants" "List all tenants (admin)" 200

# ===== PROACTIVE MESSAGING ENDPOINTS =====
echo "=== Testing Proactive Messaging Endpoints ===" | tee -a tests/postman_run.log

test_endpoint "GET" "/api/proactive/status" "Proactive messaging status" 200
test_endpoint "GET" "/api/proactive/campaigns" "List campaigns" 200 "" "-H 'X-Tenant-ID: $TENANT_ID'"
test_endpoint "GET" "/api/proactive/scheduled" "List scheduled messages" 200 "" "-H 'X-Tenant-ID: $TENANT_ID'"

# ===== TENANT STATUS ENDPOINTS =====
echo "=== Testing Tenant Device Status ===" | tee -a tests/postman_run.log

test_endpoint "GET" "/api/tenant/$TENANT_ID/device/status" "Get device status" 200

# ===== SUMMARY =====
echo "========================================" | tee -a tests/postman_run.log
echo "Test Summary" | tee -a tests/postman_run.log
echo "========================================" | tee -a tests/postman_run.log
echo "Total Tests: $TOTAL" | tee -a tests/postman_run.log
echo "Passed: $PASSED" | tee -a tests/postman_run.log
echo "Failed: $FAILED" | tee -a tests/postman_run.log
echo "Skipped: $SKIPPED" | tee -a tests/postman_run.log
echo "Success Rate: $(echo "scale=2; $PASSED * 100 / $TOTAL" | bc)%" | tee -a tests/postman_run.log
echo "========================================" | tee -a tests/postman_run.log

# Export results for JSON report
echo "{\"total\": $TOTAL, \"passed\": $PASSED, \"failed\": $FAILED, \"skipped\": $SKIPPED}" > tests/api_results/summary.json

