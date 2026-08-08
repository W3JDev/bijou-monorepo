#!/bin/bash
#
# Bijou AI - End-to-End Onboarding Flow Test (Bash + curl)
# ==========================================================
#
# Tests complete user journey from signup to WhatsApp setup
#
# Usage:
#   ./tests/e2e_onboarding_test.sh
#   ./tests/e2e_onboarding_test.sh staging
#   ./tests/e2e_onboarding_test.sh production
#
# Author: W3J Bijou AI
# Date: February 19, 2026
#

# Exit on error
set -e

# Configuration
ENV=${1:-staging}

case "$ENV" in
  local)
    BASE_URL="http://localhost:8080"
    ;;
  staging)
    BASE_URL="https://bijou-staging.fly.dev"
    ;;
  production)
    BASE_URL="https://bijou-enterprise.fly.dev"
    ;;
  *)
    echo "❌ Invalid environment: $ENV"
    echo "Usage: $0 [local|staging|production]"
    exit 1
    ;;
esac

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test state
TENANT_ID=""
SIGNUP_TOKEN=""
PASSED=0
FAILED=0
TIMESTAMP=$(date +%s)

# Results file
RESULTS_FILE="tests/e2e_onboarding_results.json"

echo ""
echo "🧪 ═══════════════════════════════════════════════════════"
echo "   Bijou AI - End-to-End Onboarding Flow Test"
echo "🧪 ═══════════════════════════════════════════════════════"
echo ""
echo "Environment: $BASE_URL"
echo "Started at: $(date -Iseconds)"
echo ""

# Helper function to log test results
log_step() {
  local step_name="$1"
  local status="$2"
  local details="$3"
  
  if [ "$status" = "PASS" ]; then
    echo -e "${GREEN}✅ $step_name: PASSED${NC}"
    ((PASSED++))
  elif [ "$status" = "FAIL" ]; then
    echo -e "${RED}❌ $step_name: FAILED${NC}"
    ((FAILED++))
  else
    echo -e "${YELLOW}⏭️  $step_name: SKIPPED${NC}"
  fi
  
  if [ -n "$details" ]; then
    echo "   $details"
  fi
  echo ""
}

# ═══════════════════════════════════════════════════════════════
# STEP 1: Tenant Signup
# ═══════════════════════════════════════════════════════════════
echo "═══════════════════════════════════════════════════════════"
echo "STEP 1: Tenant Signup (POST /api/onboarding/v2/signup)"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Generate unique test data
TEST_BUSINESS="E2E Test Property Agency $TIMESTAMP"
TEST_EMAIL="test_${TIMESTAMP}@bijou-e2e.com"
TEST_PHONE="601${TIMESTAMP: -8}"

# Create signup payload
SIGNUP_PAYLOAD=$(cat <<EOF
{
  "business_name": "$TEST_BUSINESS",
  "email": "$TEST_EMAIL",
  "phone": "$TEST_PHONE",
  "plan": "free"
}
EOF
)

echo "📤 Request payload:"
echo "$SIGNUP_PAYLOAD" | jq . 2>/dev/null || echo "$SIGNUP_PAYLOAD"
echo ""

# Make request
SIGNUP_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -X POST \
  -H "Content-Type: application/json" \
  -d "$SIGNUP_PAYLOAD" \
  "$BASE_URL/api/onboarding/v2/signup")

HTTP_STATUS=$(echo "$SIGNUP_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
RESPONSE_BODY=$(echo "$SIGNUP_RESPONSE" | sed '/HTTP_STATUS:/d')

echo "📥 Response (HTTP $HTTP_STATUS):"
echo "$RESPONSE_BODY" | jq . 2>/dev/null || echo "$RESPONSE_BODY"
echo ""

if [ "$HTTP_STATUS" = "200" ]; then
  TENANT_ID=$(echo "$RESPONSE_BODY" | jq -r '.tenant_id // empty')
  SIGNUP_TOKEN=$(echo "$RESPONSE_BODY" | jq -r '.signup_token // empty')
  
  if [ -n "$TENANT_ID" ]; then
    log_step "Step 1: Signup" "PASS" "Tenant ID: $TENANT_ID"
  else
    log_step "Step 1: Signup" "FAIL" "No tenant_id in response"
    exit 1
  fi
else
  log_step "Step 1: Signup" "FAIL" "HTTP $HTTP_STATUS: $RESPONSE_BODY"
  exit 1
fi

# ═══════════════════════════════════════════════════════════════
# STEP 2: Check Onboarding Status
# ═══════════════════════════════════════════════════════════════
echo "═══════════════════════════════════════════════════════════"
echo "STEP 2: Status Check (GET /api/onboarding/v2/status/{tenant_id})"
echo "═══════════════════════════════════════════════════════════"
echo ""

if [ -z "$TENANT_ID" ]; then
  log_step "Step 2: Status Check" "SKIP" "No tenant_id from Step 1"
else
  STATUS_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    "$BASE_URL/api/onboarding/v2/status/$TENANT_ID")
  
  HTTP_STATUS=$(echo "$STATUS_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
  RESPONSE_BODY=$(echo "$STATUS_RESPONSE" | sed '/HTTP_STATUS:/d')
  
  echo "📥 Response (HTTP $HTTP_STATUS):"
  echo "$RESPONSE_BODY" | jq . 2>/dev/null || echo "$RESPONSE_BODY"
  echo ""
  
  if [ "$HTTP_STATUS" = "200" ]; then
    CURRENT_STEP=$(echo "$RESPONSE_BODY" | jq -r '.current_step // "unknown"')
    log_step "Step 2: Status Check" "PASS" "Current step: $CURRENT_STEP"
  else
    log_step "Step 2: Status Check" "FAIL" "HTTP $HTTP_STATUS"
  fi
fi

# ═══════════════════════════════════════════════════════════════
# STEP 3: WhatsApp QR Code Generation
# ═══════════════════════════════════════════════════════════════
echo "═══════════════════════════════════════════════════════════"
echo "STEP 3: QR Generation (GET /api/onboarding/v2/whatsapp/qr/{tenant_id})"
echo "═══════════════════════════════════════════════════════════"
echo ""

if [ -z "$TENANT_ID" ]; then
  log_step "Step 3: QR Generation" "SKIP" "No tenant_id from Step 1"
else
  QR_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    "$BASE_URL/api/onboarding/v2/whatsapp/qr/$TENANT_ID")
  
  HTTP_STATUS=$(echo "$QR_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
  RESPONSE_BODY=$(echo "$QR_RESPONSE" | sed '/HTTP_STATUS:/d')
  
  # Don't print full QR response (too long), just check if qr_link exists
  HAS_QR=$(echo "$RESPONSE_BODY" | jq -r '.qr_link // empty' | wc -c)
  
  echo "📥 Response (HTTP $HTTP_STATUS):"
  if [ "$HAS_QR" -gt 100 ]; then
    echo "   qr_link: <base64 image data (${HAS_QR} bytes)>"
    echo "$RESPONSE_BODY" | jq 'del(.qr_link)' 2>/dev/null || echo "{truncated}"
  else
    echo "$RESPONSE_BODY" | jq . 2>/dev/null || echo "$RESPONSE_BODY"
  fi
  echo ""
  
  if [ "$HTTP_STATUS" = "200" ]; then
    if [ "$HAS_QR" -gt 100 ]; then
      DEVICE_ID=$(echo "$RESPONSE_BODY" | jq -r '.results.device_id // "N/A"')
      log_step "Step 3: QR Generation" "PASS" "QR code generated (device_id: $DEVICE_ID)"
    else
      log_step "Step 3: QR Generation" "FAIL" "No qr_link in response"
    fi
  elif [ "$HTTP_STATUS" = "404" ]; then
    # Device not provisioned - expected for new tenants
    log_step "Step 3: QR Generation" "PASS" "Device not provisioned (expected for new tenant)"
  else
    log_step "Step 3: QR Generation" "FAIL" "HTTP $HTTP_STATUS"
  fi
fi

# ═══════════════════════════════════════════════════════════════
# STEP 4: Device Status Check
# ═══════════════════════════════════════════════════════════════
echo "═══════════════════════════════════════════════════════════"
echo "STEP 4: Device Status (GET /api/tenant/{tenant_id}/device-status)"
echo "═══════════════════════════════════════════════════════════"
echo ""

if [ -z "$TENANT_ID" ]; then
  log_step "Step 4: Device Status" "SKIP" "No tenant_id from Step 1"
else
  DEVICE_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    "$BASE_URL/api/tenant/$TENANT_ID/device-status")
  
  HTTP_STATUS=$(echo "$DEVICE_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
  RESPONSE_BODY=$(echo "$DEVICE_RESPONSE" | sed '/HTTP_STATUS:/d')
  
  echo "📥 Response (HTTP $HTTP_STATUS):"
  echo "$RESPONSE_BODY" | jq . 2>/dev/null || echo "$RESPONSE_BODY"
  echo ""
  
  if [ "$HTTP_STATUS" = "200" ]; then
    DEVICE_STATUS=$(echo "$RESPONSE_BODY" | jq -r '.status // "unknown"')
    log_step "Step 4: Device Status" "PASS" "Status: $DEVICE_STATUS"
  else
    log_step "Step 4: Device Status" "FAIL" "HTTP $HTTP_STATUS"
  fi
fi

# ═══════════════════════════════════════════════════════════════
# STEP 5: Complete Onboarding
# ═══════════════════════════════════════════════════════════════
echo "═══════════════════════════════════════════════════════════"
echo "STEP 5: Complete Onboarding (POST /api/onboarding/v2/complete/{tenant_id})"
echo "═══════════════════════════════════════════════════════════"
echo ""

if [ -z "$TENANT_ID" ]; then
  log_step "Step 5: Complete Onboarding" "SKIP" "No tenant_id from Step 1"
else
  COMPLETE_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{}' \
    "$BASE_URL/api/onboarding/v2/complete/$TENANT_ID")
  
  HTTP_STATUS=$(echo "$COMPLETE_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
  RESPONSE_BODY=$(echo "$COMPLETE_RESPONSE" | sed '/HTTP_STATUS:/d')
  
  echo "📥 Response (HTTP $HTTP_STATUS):"
  echo "$RESPONSE_BODY" | jq . 2>/dev/null || echo "$RESPONSE_BODY"
  echo ""
  
  if [ "$HTTP_STATUS" = "200" ]; then
    DASHBOARD_URL=$(echo "$RESPONSE_BODY" | jq -r '.dashboard_url // "N/A"')
    log_step "Step 5: Complete Onboarding" "PASS" "Dashboard: $DASHBOARD_URL"
  else
    log_step "Step 5: Complete Onboarding" "FAIL" "HTTP $HTTP_STATUS"
  fi
fi

# ═══════════════════════════════════════════════════════════════
# TEST SUMMARY
# ═══════════════════════════════════════════════════════════════
echo "═══════════════════════════════════════════════════════════"
echo "TEST SUMMARY"
echo "═══════════════════════════════════════════════════════════"
echo ""

TOTAL=$((PASSED + FAILED))
PASS_RATE=0
if [ "$TOTAL" -gt 0 ]; then
  PASS_RATE=$((100 * PASSED / TOTAL))
fi

echo "Total Tests: $TOTAL"
echo -e "${GREEN}✅ Passed: $PASSED ($PASS_RATE%)${NC}"
echo -e "${RED}❌ Failed: $FAILED${NC}"
echo ""

if [ -n "$TENANT_ID" ]; then
  echo "📋 Test Tenant ID: $TENANT_ID"
  echo "   To delete: DELETE FROM tenants WHERE id = '$TENANT_ID';"
  echo ""
fi

# Save results to JSON
cat > "$RESULTS_FILE" <<EOF
{
  "started_at": "$(date -Iseconds)",
  "environment": "$BASE_URL",
  "total_tests": $TOTAL,
  "passed": $PASSED,
  "failed": $FAILED,
  "pass_rate": $PASS_RATE,
  "tenant_id": "$TENANT_ID",
  "signup_token": "$SIGNUP_TOKEN",
  "test_data": {
    "business_name": "$TEST_BUSINESS",
    "email": "$TEST_EMAIL",
    "phone": "$TEST_PHONE"
  }
}
EOF

echo "📄 Results saved to: $RESULTS_FILE"
echo ""

# Exit with appropriate code
if [ "$FAILED" -gt 0 ]; then
  exit 1
else
  exit 0
fi
