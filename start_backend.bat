@echo off
setlocal
REM RAGMind Backend Startup Script (delegates to PowerShell)

echo ========================================
echo    RAGMind Backend Server
echo ========================================
echo.

set "PS_SCRIPT=%~dp0start_backend.ps1"

if not exist "%PS_SCRIPT%" (
    echo [ERROR] Missing PowerShell startup script:
    echo         %PS_SCRIPT%
    pause
    exit /b 1
)

where powershell >nul 2>&1
if errorlevel 1 (
    echo [ERROR] powershell.exe is not available in PATH.
    pause
    exit /b 1
)

echo [INFO] Launching PowerShell startup flow...
powershell -ExecutionPolicy Bypass -File "%PS_SCRIPT%"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] Startup failed with exit code %EXIT_CODE%.
    pause
)

exit /b %EXIT_CODE%
