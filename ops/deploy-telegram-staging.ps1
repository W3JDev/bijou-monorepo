# deploy-telegram-staging.ps1
# Deploy Bijou AI with Telegram support to Fly.io Staging
# ========================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  BIJOU AI - TELEGRAM DEPLOYMENT" -ForegroundColor Cyan
Write-Host "  Target: bijou-staging.fly.dev" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to the correct directory
$projectDir = Split-Path -Parent $PSScriptRoot
$bijouDir = Join-Path $projectDir "w3j-bijou-enterprise"

Write-Host "[1/5] Navigating to $bijouDir" -ForegroundColor Yellow
Set-Location $bijouDir

# Step 1: Check Fly CLI
Write-Host ""
Write-Host "[2/5] Checking Fly.io CLI..." -ForegroundColor Yellow
try {
    $flyVersion = fly version
    Write-Host "  Fly CLI: $flyVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Fly CLI not found. Install from https://fly.io/docs/hands-on/install-flyctl/" -ForegroundColor Red
    exit 1
}

# Step 2: Check current secrets
Write-Host ""
Write-Host "[3/5] Checking secrets (TELEGRAM_BOT_TOKEN, GEMINI_API_KEYS)..." -ForegroundColor Yellow
Write-Host "  Current secrets in bijou-staging:" -ForegroundColor Gray

fly secrets list --app bijou-staging

Write-Host ""
Write-Host "  If TELEGRAM_BOT_TOKEN or GEMINI_API_KEYS are missing, set them:" -ForegroundColor Yellow
Write-Host '  fly secrets set --app bijou-staging TELEGRAM_BOT_TOKEN="your-token"' -ForegroundColor Gray
Write-Host '  fly secrets set --app bijou-staging GEMINI_API_KEYS="key1,key2,key3"' -ForegroundColor Gray
Write-Host ""

# Prompt to continue
$continue = Read-Host "Continue with deployment? (y/n)"
if ($continue -ne "y" -and $continue -ne "Y") {
    Write-Host "Deployment cancelled." -ForegroundColor Red
    exit 0
}

# Step 3: Deploy to staging
Write-Host ""
Write-Host "[4/5] Deploying to bijou-staging..." -ForegroundColor Yellow
Write-Host "  Using: fly.staging.toml" -ForegroundColor Gray
Write-Host ""

fly deploy --app bijou-staging --config fly.staging.toml

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Deployment failed!" -ForegroundColor Red
    exit 1
}

# Step 4: Check status and restart if needed
Write-Host ""
Write-Host "[5/5] Checking app status..." -ForegroundColor Yellow

fly status --app bijou-staging

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Staging URL:  https://bijou-staging.fly.dev" -ForegroundColor Cyan
Write-Host "  Health:       https://bijou-staging.fly.dev/health" -ForegroundColor Cyan
Write-Host "  WA Webhook:   https://bijou-staging.fly.dev/webhook/message" -ForegroundColor Cyan
Write-Host "  TG Webhook:   https://bijou-staging.fly.dev/webhook/telegram" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Monitor logs:" -ForegroundColor Yellow
Write-Host "  fly logs --app bijou-staging" -ForegroundColor Gray
Write-Host ""
Write-Host "  If app is suspended, restart with:" -ForegroundColor Yellow
Write-Host "  fly machine start --app bijou-staging" -ForegroundColor Gray
Write-Host ""
