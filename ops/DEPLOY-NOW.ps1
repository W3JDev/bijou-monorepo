# ============================================================================
# ⚠️  DEPRECATED — DO NOT RUN (2026-08-09)
# ----------------------------------------------------------------------------
# This script targets the Fly app `bijou-staging`, which no longer exists.
# Bijou was consolidated onto a single Fly app (`bijou-production`).
# Running this will fail with "Could not find app bijou-staging".
#
# To deploy the backend now, use:
#   cd packages/backend
#   fly deploy --app bijou-production --config fly.production.toml
#
# For the per-tenant bridge, see packages/bridge/fly.bridge-production.toml
# and the CI workflow at .github/workflows/bridge.yml.
# Kept in the tree only for historical reference; safe to delete in a
# follow-up cleanup pass once the user confirms nothing depends on it.
# ============================================================================

# PHASE 2 DEPLOYMENT - RUN THIS NOW
# ============================================

Write-Host "⚠️  This script is DEPRECATED. See banner above. Exiting." -ForegroundColor Red
exit 1


# Step 1: Deploy code
Write-Host "`n1. Deploying to Fly.io..." -ForegroundColor Yellow
cd w3j-bijou-enterprise
fly deploy --app bijou-staging --config fly.staging.toml --ha=false

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Deploy failed" -ForegroundColor Red
    exit 1
}

# Step 2: Set secrets
Write-Host "`n2. Setting environment variables..." -ForegroundColor Yellow
fly secrets set `
  OWNER_WHATSAPP_JID="+601160600963@s.whatsapp.net" `
  ENABLE_MULTI_TENANT="true" `
  ENABLE_ANALYTICS="true" `
  -a bijou-staging

# Step 3: Restart
Write-Host "`n3. Restarting app..." -ForegroundColor Yellow
fly apps restart bijou-staging

Write-Host "`n⏳ Waiting 30 seconds for startup..." -ForegroundColor Gray
Start-Sleep -Seconds 30

# Step 4: Check health
Write-Host "`n4. Checking health..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "https://bijou-staging.fly.dev/health" -UseBasicParsing -TimeoutSec 10
    Write-Host "✅ App is healthy" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Health check failed, checking logs..." -ForegroundColor Yellow
    fly logs -a bijou-staging -n 20
}

# Done
Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "✅ PHASE 2 DEPLOYED" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "`nTest tenants created:" -ForegroundColor White
Write-Host "  1. Mamak Restaurant (+60123456789)" -ForegroundColor Gray
Write-Host "  2. Prime Properties (+60198765432)" -ForegroundColor Gray
Write-Host "`nTest owner commands:" -ForegroundColor White
Write-Host "  Send: /owner help" -ForegroundColor Gray
Write-Host "`nView logs:" -ForegroundColor White
Write-Host "  fly logs -a bijou-staging" -ForegroundColor Gray
Write-Host ""
