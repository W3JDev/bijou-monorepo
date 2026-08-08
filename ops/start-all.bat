@echo off
REM ============================================================
REM W3J Bijou AI - Auto Start Script (Windows)
REM ============================================================
REM This script automatically starts all required services:
REM 1. WhatsApp Bridge (Go)
REM 2. Bijou AI (Python TRACE framework)
REM 3. Dashboard API (Flask)
REM ============================================================

echo.
echo ============================================================
echo   W3J Bijou AI - Starting All Services
echo ============================================================
echo.

REM Check if port 8080 is in use (bridge running)
netstat -ano | findstr :8080 >NUL 2>&1
if "%ERRORLEVEL%"=="0" (
    echo [INFO] WhatsApp Bridge already running on port 8080
) else (
    echo [1/3] Starting WhatsApp Bridge...
    cd ..\whatsapp-bridge
    start "WhatsApp Bridge" cmd /k "go run ."
    timeout /t 3 >nul
    echo [OK] WhatsApp Bridge started on port 8080
)

echo.
echo [2/3] Starting Bijou AI TRACE Engine...
cd ..\w3j-bijou-enterprise
start "Bijou AI" cmd /k "python src/core/bijou.py"
timeout /t 2 >nul
echo [OK] Bijou AI started

echo.
echo [3/3] Starting Dashboard API...
cd ..
start "Dashboard" cmd /k "cd w3j-bijou-enterprise && python dashboard.py"
timeout /t 2 >nul
echo [OK] Dashboard started on http://localhost:5000

echo.
echo ============================================================
echo   All Services Started Successfully!
echo ============================================================
echo.
echo   WhatsApp Bridge:  http://localhost:8080
echo   Dashboard:        http://localhost:5000
echo   Bijou AI:         Running in background
echo.
echo Press any key to exit this window (services continue running)
pause >nul
