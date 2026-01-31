@echo off
REM RAGMind Docker Services Startup Script

echo ========================================
echo    RAGMind - Docker Services
echo ========================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed!
    echo Please install Docker Desktop from: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo [✓] Docker is running
echo.

REM Start services
echo Starting PostgreSQL and Qdrant containers...
docker-compose up -d

if errorlevel 1 (
    echo [ERROR] Failed to start Docker services!
    pause
    exit /b 1
)

echo.
echo ========================================
echo [✓] Docker services started successfully!
echo ========================================
echo.
echo Services running:
echo   - PostgreSQL: localhost:5432
echo   - Qdrant:     localhost:6333
echo.
echo Database connection string:
echo   postgresql://ragmind:ragmind123@localhost:5432/ragmind
echo.
echo To stop services: stop_docker.bat
echo To view logs: docker-compose logs -f
echo.
pause
