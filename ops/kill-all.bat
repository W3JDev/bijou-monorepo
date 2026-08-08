@echo off
echo Stopping all services...

REM Kill processes on port 8080
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080"') do (
    taskkill /F /PID %%a 2>nul
)

REM Kill processes on port 5000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000"') do (
    taskkill /F /PID %%a 2>nul
)

REM Kill any remaining Python/Go processes
taskkill /F /IM python.exe 2>nul
taskkill /F /IM go.exe 2>nul

echo All services stopped!
timeout /t 2 >nul
