@echo off
cls
echo ===============================================
echo WHATSAPP QR CODE - REFRESHING...
echo ===============================================
echo.
gcloud compute ssh bijou-ai-vm --zone=asia-southeast1-a --command="sudo docker logs bijou-whatsapp-bridge 2>&1 | tail -40"
echo.
echo ===============================================
echo SCAN THIS QR CODE NOW! (Expires in 20 seconds)
echo ===============================================
echo.
echo Press any key to refresh QR code...
pause >nul
%0
