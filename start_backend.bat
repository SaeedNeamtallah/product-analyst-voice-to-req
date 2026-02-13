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
    set SKIP_DOCKER_PAUSE=1
    call start_docker.bat
    set SKIP_DOCKER_PAUSE=
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

REM Kill any existing processes on our ports to avoid conflicts
echo Cleaning up old processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8500" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
echo.

REM Start server
echo Starting FastAPI server...
echo Server will be available at: http://127.0.0.1:8500
echo API docs at: http://127.0.0.1:8500/docs
echo.
echo Starting frontend server at: http://localhost:3000
start "" cmd /c "cd /d %~dp0frontend && python -m http.server 3000"
echo Opening frontend in your browser...
start "" "http://localhost:3000"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8500
