@echo off
REM RAGMind Docker Services Stop Script

echo ========================================
echo    RAGMind - Stop Docker Services
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running!
    pause
    exit /b 1
)

echo Stopping Docker services...
docker-compose down

if errorlevel 1 (
    echo [ERROR] Failed to stop Docker services!
    pause
    exit /b 1
)

echo.
echo ========================================
echo [✓] Docker services stopped successfully!
echo ========================================
echo.
echo Note: Data is preserved in Docker volumes.
echo To remove all data: docker-compose down -v
echo.
pause
