@echo off
echo ========================================
echo  Bijou AI WhatsApp Connection Setup
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running. Please start Docker Desktop first.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

echo [1/4] Starting WhatsApp Bridge...
echo.

REM Navigate to bridge directory
cd ..\whatsapp-bridge

REM Build the bridge image
echo Building WhatsApp Bridge Docker image...
docker build -t whatsapp-bridge .

if %errorlevel% neq 0 (
    echo [ERROR] Failed to build WhatsApp Bridge
    pause
    exit /b 1
)

REM Run the bridge container
echo Starting WhatsApp Bridge container...
docker run -d --name whatsapp-bridge -p 8080:8080 -v "%CD%\store:/app/store" whatsapp-bridge

if %errorlevel% neq 0 (
    echo [ERROR] Failed to start WhatsApp Bridge
    pause
    exit /b 1
)

echo ✅ WhatsApp Bridge started on http://localhost:8080

echo.
echo [2/4] Waiting for bridge to initialize...
timeout /t 10 /nobreak >nul

echo.
echo [3/4] Getting WhatsApp QR Code...
echo.
echo Open your browser and go to: http://localhost:8080
echo.
echo You should see a QR code. Use your WhatsApp mobile app to scan it:
echo 1. Open WhatsApp on your phone
echo 2. Go to Settings > Linked Devices
echo 3. Tap "Link a Device"
echo 4. Scan the QR code from your browser
echo.

echo [4/4] Bridge Status:
echo ✅ WhatsApp Bridge: http://localhost:8080
echo ✅ Bijou AI Service: https://bijou-ai-enterprise-w3j.fly.dev
echo.
echo [NEXT STEPS]
echo 1. Scan QR code to link WhatsApp
echo 2. Send a test message to your WhatsApp number
echo 3. Check bridge logs: docker logs whatsapp-bridge
echo 4. Check Bijou AI logs: flyctl logs -a bijou-ai-enterprise-w3j
echo.
echo [MANAGEMENT COMMANDS]
echo - Stop bridge: docker stop whatsapp-bridge
echo - Start bridge: docker start whatsapp-bridge
echo - View logs: docker logs whatsapp-bridge
echo - Remove bridge: docker rm -f whatsapp-bridge
echo.
echo Press any key to open browser to QR code...
pause >nul

REM Open browser to QR code
start http://localhost:8080

echo.
echo Connection setup complete!
echo Your Bijou AI is ready for multi-language WhatsApp conversations!
echo.
pause
