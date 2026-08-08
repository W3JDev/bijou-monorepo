# ============================================================================
# BIJOU AI - PHASE 2 DEPLOYMENT SCRIPT (Windows PowerShell)
# ============================================================================
# This script automates Phase 2 deployment to staging
# ============================================================================

$ErrorActionPreference = "Stop"

# Colors
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Success($message) {
    Write-ColorOutput Green "✅ $message"
}

function Write-Info($message) {
    Write-ColorOutput Cyan "ℹ️  $message"
}

function Write-Warning($message) {
    Write-ColorOutput Yellow "⚠️  $message"
}

function Write-Error($message) {
    Write-ColorOutput Red "❌ $message"
}

function Write-Step($step, $message) {
    Write-ColorOutput Magenta "`n$step"
    Write-Info $message
}

# Configuration
$APP_NAME = "bijou-staging"
$PROJECT_DIR = Get-Location
$MIGRATION_FILE = "supabase\migrations\004_phase2_multi_tenant.sql"

Clear-Host
Write-Output ""
Write-Output "============================================================================"
Write-ColorOutput Blue "🚀 BIJOU AI - PHASE 2 DEPLOYMENT (Windows)"
Write-Output "============================================================================"
Write-Output ""
Write-Output "This will deploy Phase 2 multi-tenant features to staging:"
Write-Output "  • Multi-tenant support"
Write-Output "  • Advanced analytics"
Write-Output "  • Workflow automation foundation"
Write-Output "  • Enhanced AI context"
Write-Output ""
Write-ColorOutput Yellow "Target: $APP_NAME"
Write-ColorOutput Yellow "Environment: STAGING"
Write-Output ""

# Confirm deployment
$confirm = Read-Host "Continue with Phase 2 deployment? (yes/no)"
if ($confirm -ne "yes") {
    Write-Error "Deployment cancelled"
    exit 0
}

Write-Output ""
Write-Output "============================================================================"
Write-ColorOutput Blue "📋 PHASE 2 DEPLOYMENT CHECKLIST"
Write-Output "============================================================================"
Write-Output ""

# Step 1: Verify Prerequisites
Write-Step "Step 1: Verifying prerequisites..." "Checking system requirements"

# Check if fly CLI is installed
try {
    $flyVersion = fly version 2>$null
    Write-Success "Fly CLI is installed"
} catch {
    Write-Error "Fly CLI not found. Please install from https://fly.io/docs/hands-on/install-flyctl/"
    exit 1
}

# Check if logged in to Fly
try {
    $flyAuth = fly auth whoami 2>$null
    Write-Success "Logged in to Fly.io as: $flyAuth"
} catch {
    Write-Error "Not logged in to Fly.io. Run: fly auth login"
    exit 1
}

# Check if app exists
try {
    fly status -a $APP_NAME 2>$null | Out-Null
    Write-Success "App '$APP_NAME' found and accessible"
} catch {
    Write-Error "App '$APP_NAME' not found or not accessible"
    exit 1
}

# Check if migration file exists
if (Test-Path $MIGRATION_FILE) {
    Write-Success "Migration file found: $MIGRATION_FILE"
} else {
    Write-Error "Migration file not found: $MIGRATION_FILE"
    exit 1
}

Write-Output ""

# Step 2: Migration Instructions
Write-Step "Step 2: Apply database migration..." "Preparing Supabase migration"

Write-Output ""
Write-ColorOutput Yellow "📝 MANUAL STEP REQUIRED - DATABASE MIGRATION"
Write-Output ""
Write-Output "Please complete these steps in Supabase Dashboard:"
Write-Output ""
Write-Output "1. Go to: https://supabase.com/dashboard/project/lrwzlujomukzjykafmic"
Write-Output "2. Navigate to: SQL Editor (left sidebar)"
Write-Output "3. Click: New Query"
Write-Output "4. Copy the contents of: $MIGRATION_FILE"
Write-Output "5. Paste into SQL Editor"
Write-Output "6. Click: Run (or press Ctrl+Enter)"
Write-Output "7. Wait for 'Success' message"
Write-Output ""
Write-Output "Verification Query:"
Write-Output "-------------------"
Write-ColorOutput Cyan @"
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('tenants', 'tenant_users', 'analytics_metrics', 'workflows')
ORDER BY table_name;
"@
Write-Output ""
Write-Output "Expected: 4 rows returned (tenants, tenant_users, analytics_metrics, workflows)"
Write-Output ""

$migrationDone = Read-Host "Have you applied the migration? (yes/no)"
if ($migrationDone -ne "yes") {
    Write-Error "Please apply the migration first, then run this script again"
    exit 0
}

Write-Success "Migration marked as applied"
Write-Output ""

# Step 3: Create Test Tenants
Write-Step "Step 3: Create test tenants..." "Setting up test businesses"

Write-Output ""
Write-ColorOutput Yellow "📝 MANUAL STEP REQUIRED - CREATE TEST TENANTS"
Write-Output ""
Write-Output "Please run this SQL in Supabase SQL Editor:"
Write-Output ""
Write-ColorOutput Cyan @"
-- Default Tenant (for existing Phase 1 data)
INSERT INTO tenants (id, name, phone_number, business_type, owner_jid, status, subscription_tier)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Default Business',
    '+60000000000',
    'general',
    '+60000000000@s.whatsapp.net',
    'active',
    'enterprise'
) ON CONFLICT (id) DO NOTHING;

-- Test Tenant 1: Restaurant
INSERT INTO tenants (name, phone_number, business_type, owner_jid, status, subscription_tier, brand_name, monthly_message_limit)
VALUES (
    'Mamak Restaurant',
    '+60123456789',
    'restaurant',
    '+60123456789@s.whatsapp.net',
    'active',
    'pro',
    'Mamak Delights',
    5000
);

-- Test Tenant 2: Real Estate
INSERT INTO tenants (name, phone_number, business_type, owner_jid, status, subscription_tier, brand_name, monthly_message_limit)
VALUES (
    'Prime Properties',
    '+60198765432',
    'real_estate',
    '+60198765432@s.whatsapp.net',
    'active',
    'pro',
    'Prime Realty Malaysia',
    5000
);

-- Verify tenants created
SELECT id, name, business_type, phone_number, status
FROM tenants
ORDER BY created_at;
"@
Write-Output ""
Write-Output "Expected: 3 tenants (Default + Mamak Restaurant + Prime Properties)"
Write-Output ""

$tenantsDone = Read-Host "Have you created the test tenants? (yes/no)"
if ($tenantsDone -ne "yes") {
    Write-Warning "Skipping tenant creation. You can create them later."
}

Write-Success "Test tenants step completed"
Write-Output ""

# Step 4: Deploy Code
Write-Step "Step 4: Deploying Phase 2 code to staging..." "Building and deploying application"

Write-Output ""
Write-Info "Deploying to $APP_NAME..."

try {
    Set-Location "w3j-bijou-enterprise"

    Write-Info "Running: fly deploy --app $APP_NAME --config fly.staging.toml --ha=false"
    fly deploy --app $APP_NAME --config fly.staging.toml --ha=false

    Set-Location $PROJECT_DIR
    Write-Success "Code deployed successfully"
} catch {
    Set-Location $PROJECT_DIR
    Write-Error "Deployment failed: $_"
    exit 1
}

Write-Output ""

# Step 5: Enable Phase 2 Features
Write-Step "Step 5: Enabling Phase 2 feature flags..." "Configuring environment variables"

Write-Output ""
Write-Info "Setting feature flags:"
Write-Output "  • ENABLE_MULTI_TENANT=true"
Write-Output "  • ENABLE_ANALYTICS=true"
Write-Output "  • ENABLE_WORKFLOWS=false (will enable in Week 2)"
Write-Output ""

try {
    fly secrets set ENABLE_MULTI_TENANT=true ENABLE_ANALYTICS=true ENABLE_WORKFLOWS=false -a $APP_NAME
    Write-Success "Feature flags enabled"
} catch {
    Write-Error "Failed to set feature flags: $_"
    exit 1
}

Write-Output ""
Write-Info "Restarting app to apply changes..."

try {
    fly apps restart $APP_NAME
    Write-Success "App restarted"
} catch {
    Write-Warning "Failed to restart app automatically. Please restart manually: fly apps restart $APP_NAME"
}

Write-Output ""
Write-Info "Waiting for app to become healthy (30 seconds)..."
Start-Sleep -Seconds 30

# Step 6: Verify Deployment
Write-Step "Step 6: Verifying deployment..." "Running health checks"

Write-Output ""
Write-Info "Checking app status..."

try {
    $status = fly status -a $APP_NAME
    if ($status -match "started") {
        Write-Success "App is running"
    } else {
        Write-Warning "App may not be running properly"
    }
} catch {
    Write-Warning "Could not verify app status"
}

Write-Output ""
Write-Info "Checking health endpoint..."

try {
    $healthResponse = Invoke-WebRequest -Uri "https://bijou-staging.fly.dev/health" -UseBasicParsing -TimeoutSec 10
    if ($healthResponse.StatusCode -eq 200) {
        Write-Success "Health check passed"
    }
} catch {
    Write-Warning "Health check failed or timeout. App may still be starting..."
}

Write-Output ""

# Step 7: Show Logs
Write-Step "Step 7: Checking recent logs..." "Verifying Phase 2 initialization"

Write-Output ""
Write-Info "Recent logs (last 20 lines):"
Write-Output "----------------------------------------"

try {
    fly logs -a $APP_NAME -n 20
} catch {
    Write-Warning "Could not fetch logs"
}

Write-Output "----------------------------------------"
Write-Output ""

# Deployment Complete
Write-Output ""
Write-Output "============================================================================"
Write-ColorOutput Green "✅ PHASE 2 DEPLOYMENT COMPLETE"
Write-Output "============================================================================"
Write-Output ""
Write-Output "🧪 NEXT STEPS - TESTING:"
Write-Output ""
Write-Output "1. Send WhatsApp message from test tenant 1 (+60123456789)"
Write-Output "   Expected: Routes to 'Mamak Restaurant'"
Write-Output ""
Write-Output "2. Send WhatsApp message from test tenant 2 (+60198765432)"
Write-Output "   Expected: Routes to 'Prime Properties'"
Write-Output ""
Write-Output "3. Check logs for tenant routing:"
Write-Output "   fly logs -a $APP_NAME"
Write-Output "   Look for: '🏢 Tenant: <name>'"
Write-Output ""
Write-Output "4. Verify database isolation in Supabase SQL Editor:"
Write-ColorOutput Cyan @"
   SELECT set_tenant_context('<tenant1-id>');
   SELECT COUNT(*) FROM conversations;
   -- Should only show tenant 1's conversations
"@
Write-Output ""
Write-Output "5. Check analytics are being tracked:"
Write-ColorOutput Cyan @"
   SELECT COUNT(*) FROM analytics_metrics;
   -- Should see metric records
"@
Write-Output ""
Write-Output "============================================================================"
Write-Output ""
Write-Output "📊 MONITORING COMMANDS:"
Write-Output ""
Write-Output "  • View logs:      fly logs -a $APP_NAME"
Write-Output "  • Check status:   fly status -a $APP_NAME"
Write-Output "  • SSH console:    fly ssh console -a $APP_NAME"
Write-Output "  • Health check:   curl https://bijou-staging.fly.dev/health"
Write-Output ""
Write-Output "============================================================================"
Write-Output ""
Write-Output "🔧 TROUBLESHOOTING:"
Write-Output ""
Write-Output "If tenant routing not working:"
Write-Output "  1. Check migration was applied correctly in Supabase"
Write-Output "  2. Verify tenants exist: SELECT * FROM tenants;"
Write-Output "  3. Check feature flags: fly secrets list -a $APP_NAME"
Write-Output "  4. Review logs: fly logs -a $APP_NAME"
Write-Output ""
Write-Output "If RLS errors occur:"
Write-Output "  1. Verify RLS policies exist in Supabase"
Write-Output "  2. Check tenant context is being set"
Write-Output "  3. Review migration was applied completely"
Write-Output ""
Write-Output "============================================================================"
Write-Output ""
Write-Output "📚 DOCUMENTATION:"
Write-Output ""
Write-Output "  • Quick Start:       PHASE2-QUICK-START.md"
Write-Output "  • Full Plan:         PHASE2-IMPLEMENTATION-PLAN.md"
Write-Output "  • Deployment Guide:  PHASE2-DEPLOY-NOW.md"
Write-Output "  • Integration:       PHASE2-INTEGRATION-GUIDE.md"
Write-Output ""
Write-Output "============================================================================"
Write-Output ""
Write-ColorOutput Blue "🎉 Phase 2 foundation deployed successfully!"
Write-Output ""
Write-Output "Current Progress:"
Write-Output "  Week 1: [████░░░] 60% (Database + Routing deployed)"
Write-Output "  Week 2: [░░░░░░░] 0%  (Workflows - not started)"
Write-Output "  Week 3: [░░░░░░░] 0%  (Dashboard - not started)"
Write-Output ""
Write-Output "Next: Implement Analytics Engine (Week 1, Days 5-7)"
Write-Output ""
Write-Output "============================================================================"
Write-Output ""
Write-ColorOutput Green "Deployment script completed! 🚀"
Write-Output ""
