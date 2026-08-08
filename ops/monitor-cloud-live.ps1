# Monitor Bijou AI and Bridge Logs Live
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
