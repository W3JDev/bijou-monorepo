@echo off
REM ============================================================
REM W3J Bijou AI - Stop All Services (Windows)
REM ============================================================

echo.
echo ============================================================
echo   W3J Bijou AI - Stopping All Services
echo ============================================================
echo.

echo [1/3] Stopping WhatsApp Bridge...
taskkill /FI "WINDOWTITLE eq WhatsApp Bridge*" /F >nul 2>&1
if "%ERRORLEVEL%"=="0" (
    echo [OK] WhatsApp Bridge stopped
) else (
    echo [INFO] WhatsApp Bridge not running
)

echo.
echo [2/3] Stopping Bijou AI...
taskkill /FI "WINDOWTITLE eq Bijou AI*" /F >nul 2>&1
if "%ERRORLEVEL%"=="0" (
    echo [OK] Bijou AI stopped
) else (
    echo [INFO] Bijou AI not running
)

echo.
echo [3/3] Stopping Dashboard...
taskkill /FI "WINDOWTITLE eq Dashboard*" /F >nul 2>&1
if "%ERRORLEVEL%"=="0" (
    echo [OK] Dashboard stopped
) else (
    echo [INFO] Dashboard not running
)

echo.
echo ============================================================
echo   All Services Stopped
echo ============================================================
echo.
pause
