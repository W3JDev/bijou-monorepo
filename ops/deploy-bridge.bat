@echo off
echo ========================================
echo Deploying WhatsApp Bridge to Cloud Run
echo ========================================
echo.
echo This will take 5-7 minutes...
echo.

gcloud run deploy whatsapp-bridge ^
  --source ..\whatsapp-bridge ^
  --region asia-southeast1 ^
  --platform managed ^
  --allow-unauthenticated ^
  --port 8080 ^
  --memory 512Mi ^
  --cpu 1 ^
  --min-instances 1 ^
  --max-instances 3 ^
  --set-env-vars "BRIDGE_DB_PATH=/app/store/messages.db"

echo.
echo Getting Bridge URL...
gcloud run services describe whatsapp-bridge --region asia-southeast1 --format "value(status.url)" > bridge-url.txt
set /p BRIDGE_URL=<bridge-url.txt
echo.
echo ========================================
echo WhatsApp Bridge deployed successfully!
echo URL: %BRIDGE_URL%
echo ========================================
echo.
echo Copy this URL for the next step!
pause
