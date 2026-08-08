# Get Fresh WhatsApp QR Code from Cloud Bridge

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "  WHATSAPP QR CODE - SCAN WITH YOUR PHONE" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Add Fly CLI to path
$env:Path += ";C:\Users\w3jbt\.fly\bin"

Write-Host "Fetching QR code from cloud bridge..." -ForegroundColor Yellow
Write-Host ""

# Get logs and display QR code section
flyctl logs -a whatsapp-bridge-w3j --no-tail | Select-String -Pattern "Scan this QR" -Context 0, 35

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  STEPS TO CONNECT:" -ForegroundColor Yellow
Write-Host "  1. Open WhatsApp on your phone" -ForegroundColor White
Write-Host "  2. Go to Settings -> Linked Devices" -ForegroundColor White
Write-Host "  3. Tap 'Link a Device'" -ForegroundColor White
Write-Host "  4. Scan the QR code above" -ForegroundColor White
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "After scanning, your PC can be OFF!" -ForegroundColor Green
Write-Host "Bijou AI will run 24/7 in the cloud." -ForegroundColor Green
Write-Host ""
