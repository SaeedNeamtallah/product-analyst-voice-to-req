@echo off
REM RAGMind Backend Startup Script

echo ========================================
echo    RAGMind Backend Server
echo ========================================
echo.

REM Check if Docker services are running
docker ps 2>nul | findstr "ragmind-postgres" >nul
if errorlevel 1 (
    echo [WARNING] Database container is not running!
    echo Starting Docker services...
    docker-compose up -d
    if errorlevel 1 (
        echo [ERROR] Failed to start Docker services!
        echo Please run start_docker.bat first or start Docker Desktop.
        pause
        exit /b 1
    )
    echo Waiting for database to be ready...
    timeout /t 5 /nobreak >nul
)
echo [✓] Database is running
echo.

REM Check if uv is installed
uv --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: uv is not installed!
    echo Please install uv from: https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment with uv...
    uv venv venv
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Install dependencies with uv (much faster!)
echo Installing/Updating dependencies with uv...
uv pip install -r backend\requirements.txt
echo.

REM Initialize database
echo Initializing database...
python backend\init_database.py
echo.

REM Start server
echo Starting FastAPI server...
echo Server will be available at: http://localhost:8000
echo API docs at: http://localhost:8000/docs
echo.
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
