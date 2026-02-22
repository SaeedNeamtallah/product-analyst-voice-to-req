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

REM Clean up any existing containers to avoid name conflicts
echo [INFO] Stopping any old RAGMind containers...
docker compose down >nul 2>&1

REM Also remove orphan containers with the same names (from previous runs or manual creates)
for %%C in (ragmind-postgres) do (
    docker rm -f %%C >nul 2>&1
)

REM Start services
echo Starting PostgreSQL container...
docker compose up -d

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
echo   - PostgreSQL: localhost:5555
echo.
echo Database connection string:
echo   postgresql://ragmind:ragmind123@localhost:5555/ragmind
echo.
echo To stop services: stop_docker.bat
echo To view logs: docker-compose logs -f
echo.
if not defined SKIP_DOCKER_PAUSE (
    pause
)
