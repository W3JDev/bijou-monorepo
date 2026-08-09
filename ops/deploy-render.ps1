# ============================================================================
# ⚠️  DEPRECATED — DO NOT RUN (2026-08-09)
# ----------------------------------------------------------------------------
# Targets Render.com, not the current Fly.io infra. Bijou was migrated to
# Fly.io; Render is no longer in use.
#
# ALSO: this file contains a hardcoded Render API key
#   $RENDER_API_KEY = "rnd_OXcBzcJ53fkTlzH2CAtjHMBK3xMM"
# at line 7. That key should be ROTATED on Render ASAP — anyone with read
# access to this repo can use it to create/modify Render services until
# the key is revoked.
#
# For the current backend, use:
#   cd packages/backend
#   fly deploy --app bijou-production --config fly.production.toml
# For the per-tenant bridge:
#   fly deploy --app <tenant-app> --config packages/bridge/fly.bridge-production.toml
# Kept for historical reference only.
# ============================================================================

# Automated Render Deployment Script for Bijou AI WhatsApp System
# This script deploys both WhatsApp Bridge and Bijou AI to Render with live monitoring

Write-Host "⚠️  This script is DEPRECATED. See banner above. Exiting." -ForegroundColor Red
exit 1

$ErrorActionPreference = "Stop"

# Configuration
$RENDER_API_KEY = "rnd_OXcBzcJ53fkTlzH2CAtjHMBK3xMM"
$GITHUB_REPO = "https://github.com/W3JDev/w3j-bijou-ai.git"
$BRANCH = "dev/phase-4-copilot"
$OWNER_ID = "tea-cvardqfnoe9s73feg2jg"

# API Base URL
$API_BASE = "https://api.render.com/v1"

# Headers for API requests
$headers = @{
    "Authorization" = "Bearer $RENDER_API_KEY"
    "Content-Type" = "application/json"
}

Write-Host "🚀 BIJOU AI RENDER DEPLOYMENT STARTING..." -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Function to make API calls
function Invoke-RenderAPI {
    param(
        [string]$Method,
        [string]$Endpoint,
        [object]$Body
    )

    $uri = "$API_BASE$Endpoint"
    $params = @{
        Uri = $uri
        Method = $Method
        Headers = $headers
    }

    if ($Body) {
        $params.Body = ($Body | ConvertTo-Json -Depth 10)
    }

    try {
        $response = Invoke-RestMethod @params
        return $response
    } catch {
        Write-Host "❌ API Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Response: $($_.ErrorDetails.Message)" -ForegroundColor Red
        throw
    }
}

# Function to wait for service to be live
function Wait-ServiceLive {
    param(
        [string]$ServiceId,
        [string]$ServiceName
    )

    Write-Host "⏳ Waiting for $ServiceName to deploy..." -ForegroundColor Yellow

    $maxAttempts = 60  # 5 minutes max
    $attempt = 0

    while ($attempt -lt $maxAttempts) {
        try {
            $service = Invoke-RenderAPI -Method "GET" -Endpoint "/services/$ServiceId"

            if ($service.service.serviceDetails.url) {
                Write-Host "✅ $ServiceName is LIVE!" -ForegroundColor Green
                Write-Host "   URL: $($service.service.serviceDetails.url)" -ForegroundColor Cyan
                return $service.service.serviceDetails.url
            }

            Write-Host "   Status: Deploying... (attempt $($attempt + 1)/$maxAttempts)" -ForegroundColor Yellow
            Start-Sleep -Seconds 5
            $attempt++
        } catch {
            Write-Host "   Checking... (attempt $($attempt + 1)/$maxAttempts)" -ForegroundColor Yellow
            Start-Sleep -Seconds 5
            $attempt++
        }
    }

    throw "Service $ServiceName did not become live within timeout"
}

Write-Host "📋 Step 1: Creating WhatsApp Bridge Service..." -ForegroundColor Cyan
Write-Host "------------------------------------------------" -ForegroundColor Cyan

$bridgePayload = @{
    type = "web_service"
    name = "whatsapp-bridge-bijou"
    ownerId = $OWNER_ID
    repo = $GITHUB_REPO
    branch = $BRANCH
    rootDir = "whatsapp-bridge"
    envSpecificDetails = @{
        docker = @{
            dockerfilePath = "Dockerfile"
            dockerContext = "."
        }
    }
    serviceDetails = @{
        env = "docker"
        region = "singapore"
        plan = "starter"
        healthCheckPath = "/health"
        autoDeploy = "yes"
    }
    envVars = @(
        @{
            key = "PORT"
            value = "8080"
        },
        @{
            key = "ENVIRONMENT"
            value = "production"
        },
        @{
            key = "GIN_MODE"
            value = "release"
        }
    )
    disk = @{
        name = "bridge-data"
        mountPath = "/app/store"
        sizeGB = 1
    }
}

Write-Host "   Creating service..." -ForegroundColor Yellow
try {
    $bridgeService = Invoke-RenderAPI -Method "POST" -Endpoint "/services" -Body $bridgePayload
    $bridgeId = $bridgeService.id
    Write-Host "✅ Bridge service created! ID: $bridgeId" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to create bridge service" -ForegroundColor Red
    Write-Host "This might mean the service already exists. Continuing..." -ForegroundColor Yellow

    # Try to find existing service
    $services = Invoke-RenderAPI -Method "GET" -Endpoint "/services?name=whatsapp-bridge-bijou"
    if ($services -and $services[0]) {
        $bridgeId = $services[0].service.id
        Write-Host "✅ Found existing bridge service: $bridgeId" -ForegroundColor Green
    } else {
        throw "Could not create or find bridge service"
    }
}

Write-Host ""
$bridgeUrl = Wait-ServiceLive -ServiceId $bridgeId -ServiceName "WhatsApp Bridge"

Write-Host ""
Write-Host "📋 Step 2: Creating Bijou AI Service..." -ForegroundColor Cyan
Write-Host "------------------------------------------------" -ForegroundColor Cyan

$bijouPayload = @{
    type = "web_service"
    name = "bijou-ai-enterprise"
    ownerId = $OWNER_ID
    repo = $GITHUB_REPO
    branch = $BRANCH
    rootDir = "w3j-bijou-enterprise"
    serviceDetails = @{
        env = "python"
        region = "singapore"
        plan = "starter"
        buildCommand = "pip install -r requirements.txt"
        startCommand = "python src/core/bijou.py"
        healthCheckPath = "/health"
        autoDeploy = "yes"
    }
    envVars = @(
        @{ key = "AI_MODEL"; value = "gemini-2.5-flash" },
        @{ key = "BRIDGE_URL"; value = "https://$bridgeUrl" },
        @{ key = "GEMINI_API_KEY"; value = "AIza_REDACTED" },
        @{ key = "OPENAI_API_KEY"; value = "sk-proj_REDACTED" },
        @{ key = "WHATSAPP_OWNER"; value = "+601160600963" },
        @{ key = "OWNER_WHATSAPP_JID"; value = "601160600963@s.whatsapp.net" },
        @{ key = "DB_TYPE"; value = "sqlite" },
        @{ key = "BIJOU_DB_PATH"; value = "/data/bijou.db" },
        @{ key = "PRIMARY_LANGUAGES"; value = "ms,zh,ta,en,en-my" },
        @{ key = "CULTURAL_CONTEXT_ENABLED"; value = "true" },
        @{ key = "MANGLISH_DETECTION"; value = "true" },
        @{ key = "ESCALATION_ENABLED"; value = "true" },
        @{ key = "TRACE_ENABLED"; value = "true" },
        @{ key = "POLLING_INTERVAL"; value = "2" },
        @{ key = "MAX_MESSAGES_PER_POLL"; value = "50" },
        @{ key = "ENVIRONMENT"; value = "production" },
        @{ key = "LOG_LEVEL"; value = "INFO" },
        @{ key = "PORT"; value = "8080" }
    )
    disk = @{
        name = "bijou-data"
        mountPath = "/data"
        sizeGB = 1
    }
}

Write-Host "   Creating service with Bridge URL: https://$bridgeUrl" -ForegroundColor Yellow
try {
    $bijouService = Invoke-RenderAPI -Method "POST" -Endpoint "/services" -Body $bijouPayload
    $bijouId = $bijouService.id
    Write-Host "✅ Bijou service created! ID: $bijouId" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to create Bijou service" -ForegroundColor Red
    Write-Host "This might mean the service already exists. Continuing..." -ForegroundColor Yellow

    # Try to find existing service
    $services = Invoke-RenderAPI -Method "GET" -Endpoint "/services?name=bijou-ai-enterprise"
    if ($services -and $services[0]) {
        $bijouId = $services[0].service.id
        Write-Host "✅ Found existing Bijou service: $bijouId" -ForegroundColor Green
    } else {
        throw "Could not create or find Bijou service"
    }
}

Write-Host ""
$bijouUrl = Wait-ServiceLive -ServiceId $bijouId -ServiceName "Bijou AI"

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "✅ DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📱 WhatsApp Bridge: https://$bridgeUrl" -ForegroundColor Cyan
Write-Host "🤖 Bijou AI: https://$bijouUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "🎯 NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Open https://$bridgeUrl in your browser" -ForegroundColor White
Write-Host "2. Scan QR code with WhatsApp Business (+60174106981)" -ForegroundColor White
Write-Host "3. Send test message from your phone (+601160600963)" -ForegroundColor White
Write-Host "4. Bijou will respond automatically!" -ForegroundColor White
Write-Host ""
Write-Host "📊 Monitor Logs:" -ForegroundColor Yellow
Write-Host "   Render Dashboard: https://dashboard.render.com" -ForegroundColor White
Write-Host ""
Write-Host "✨ Your Bijou AI is LIVE and ready! ✨" -ForegroundColor Green
Write-Host ""
