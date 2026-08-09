# ============================================================================
# ⚠️  DEPRECATED — DO NOT RUN (2026-08-09)
# ----------------------------------------------------------------------------
# Targets two dead Fly apps:
#   - whatsapp-bridge-w3j         (replaced by bijou-bridge-production-v2)
#   - bijou-ai-enterprise-w3j     (replaced by bijou-production)
#
# For the current stack:
#   fly logs -a bijou-production
#   fly logs -a <tenant-app-name>
# ============================================================================

# Monitor Bijou AI and Bridge Logs Live
Write-Host "⚠️  This script is DEPRECATED. See banner above. Exiting." -ForegroundColor Red
exit 1

Write-Host "`nLIVE MONITORING - Bijou AI and WhatsApp Bridge" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "`nSend a WhatsApp message now, then watch the logs below..." -ForegroundColor Yellow
Write-Host ""

# Add Fly CLI to path
$env:Path += ";C:\Users\w3jbt\.fly\bin"

Write-Host "[BRIDGE LOGS]" -ForegroundColor Green
flyctl logs -a whatsapp-bridge-w3j --no-tail | Select-Object -Last 30
Write-Host ""
Write-Host "[BIJOU AI LOGS]" -ForegroundColor Magenta
flyctl logs -a bijou-ai-enterprise-w3j --no-tail | Select-Object -Last 30
