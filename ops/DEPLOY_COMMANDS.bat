@echo off
REM Quick deployment script - Run from whatsapp-mcp\whatsapp-mcp directory

echo ========================================
echo Deploying WhatsApp Bridge (Buildpacks)
echo ========================================
echo.
echo Go to: https://console.cloud.google.com/run?project=gen-lang-client-0423187661
echo.
echo COPY AND RUN THIS COMMAND IN YOUR POWERSHELL:
echo.
echo gcloud run deploy whatsapp-bridge --source ./whatsapp-bridge --region asia-southeast1 --platform managed --allow-unauthenticated --port 8080 --memory 512Mi --cpu 1 --min-instances 1 --max-instances 3 --set-env-vars "BRIDGE_DB_PATH=/app/store/messages.db"
echo.
echo After deployment completes, get the URL:
echo gcloud run services describe whatsapp-bridge --region asia-southeast1 --format "value(status.url)"
echo.
pause
