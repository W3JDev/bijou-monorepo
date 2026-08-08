# Simple WhatsApp Bridge Deployment
# Run from repo root or ops/ (uses ../whatsapp-bridge when in ops/)

Write-Host "========================================" -ForegroundColor Green
Write-Host "Deploying WhatsApp Bridge to Cloud Run" -ForegroundColor Green  
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

$bridgePath = if (Test-Path ".\whatsapp-bridge") { ".\whatsapp-bridge" } else { "..\whatsapp-bridge" }
gcloud run deploy whatsapp-bridge `
  --source $bridgePath `
  --region asia-southeast1 `
  --platform managed `
  --allow-unauthenticated `
  --port 8080 `
  --memory 512Mi `
  --cpu 1 `
  --min-instances 1 `
  --max-instances 3 `
  --set-env-vars "BRIDGE_DB_PATH=/app/store/messages.db"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ WhatsApp Bridge deployed successfully!" -ForegroundColor Green
    Write-Host ""
    $BRIDGE_URL = gcloud run services describe whatsapp-bridge --region asia-southeast1 --format "value(status.url)"
    Write-Host "Bridge URL: $BRIDGE_URL" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Save this URL for the next step!" -ForegroundColor Yellow
    $BRIDGE_URL | Out-File -FilePath "bridge-url.txt" -Encoding utf8
} else {
    Write-Host ""
    Write-Host "❌ Deployment failed. Check logs above." -ForegroundColor Red
}
