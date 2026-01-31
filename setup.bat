@echo off
chcp 65001 >nul
color 0A
echo ========================================
echo    RAGMind - Setup Script
echo    Installing all project dependencies
echo ========================================
echo.

:: Check if uv is installed
uv --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] uv is not installed on the system!
    echo Please install uv from: https://docs.astral.sh/uv/getting-started/installation/
    echo You can install it with: pip install uv or winget install --id=astral-sh.uv
    pause
    exit /b 1
)

echo [✓] uv is installed
uv --version
echo.

:: Check if Docker is available (recommended for database)
echo [INFO] This project uses Docker for PostgreSQL database (recommended)
echo        Install Docker Desktop from: https://www.docker.com/products/docker-desktop
echo.

:: Create virtual environment
echo ========================================
echo 1. Create virtual environment (Virtual Environment)
echo ========================================
if exist "venv\" (
    echo [!] Virtual environment already exists
    choice /C YN /M "Do you want to recreate it?"
    if errorlevel 2 goto skip_venv
    if errorlevel 1 (
        echo [INFO] Removing old virtual environment...
        rmdir /s /q venv
    )
)

echo [INFO] Creating a new virtual environment...
uv venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment!
    pause
    exit /b 1
)
echo [✓] Virtual environment created successfully
echo.

:skip_venv

:: Activate virtual environment
echo ========================================
echo 2. Activate virtual environment
echo ========================================
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate the virtual environment!
    pause
    exit /b 1
)
echo [✓] Virtual environment activated
echo.

:: Install dependencies with uv
echo ========================================
echo 3. Install dependencies with uv (much faster!)
echo ========================================
uv pip install -r backend\requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies!
    echo Please check requirements.txt and your internet connection
    pause
    exit /b 1
)
echo [✓] All dependencies installed successfully
echo.

:: Create .env file if not exists
echo ========================================
echo 4. Create configuration file (.env)
echo ========================================
if exist ".env" (
    echo [!] .env file already exists
    choice /C YN /M "Do you want to recreate it from the template?"
    if errorlevel 2 goto skip_env
)

if exist ".env.example" (
    echo [INFO] Copying settings from .env.example...
    copy .env.example .env >nul
    echo [✓] .env file created
    echo [!] Please edit .env and add:
    echo     - DATABASE_URL
    echo     - GEMINI_API_KEY
    echo     - TELEGRAM_BOT_TOKEN (optional)
) else (
    echo [WARNING] .env.example not found
    echo Please create a .env file manually and add the required settings
)
echo.

:skip_env

:: Create uploads directory
echo ========================================
echo 5. Create project directories
echo ========================================
if not exist "uploads\" mkdir uploads
echo [✓] uploads directory created
if not exist "qdrant_data\" mkdir qdrant_data
echo [✓] qdrant_data directory created
echo.

:: Database setup with Docker
echo ========================================
echo 6. Database setup (Docker)
echo ========================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Docker is not installed!
    echo Please install Docker Desktop from: https://www.docker.com/products/docker-desktop
    echo.
    echo Alternatively, set up PostgreSQL manually:
    echo   1. Install PostgreSQL
    echo   2. Create database: CREATE DATABASE ragmind;
    echo   3. Enable pgvector: CREATE EXTENSION vector;
    echo   4. Update DATABASE_URL in .env
    echo.
    goto skip_docker
)

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Docker is not running!
    echo Please start Docker Desktop and run start_docker.bat
    goto skip_docker
)

echo [✓] Docker is available
choice /C YN /M "Do you want to start the database with Docker?"
if errorlevel 2 goto skip_docker
if errorlevel 1 (
    echo [INFO] Starting Docker services...
    docker-compose up -d
    if errorlevel 1 (
        echo [ERROR] Failed to start Docker services!
    ) else (
        echo [✓] PostgreSQL and Qdrant containers started
        echo.
        echo Waiting for database to be ready...
        timeout /t 5 /nobreak >nul
        echo [✓] Database is ready
    )
)
echo.

:skip_docker

:: Initialize database
echo ========================================
echo 7. Initialize database tables
echo ========================================
choice /C YN /M "Do you want to initialize the database tables now?"
if errorlevel 1 (
    echo [INFO] Initializing database...
    python -m backend.init_database
    if errorlevel 1 (
        echo [ERROR] Failed to initialize the database
        echo Please check:
        echo   - PostgreSQL connection
        echo   - DATABASE_URL in .env
        echo   - pgvector extension installed
    ) else (
        echo [✓] Database initialized successfully
    )
) else (
    echo [!] You can initialize the database later with:
    echo     python -m backend.init_database
)
echo.

:: Summary
echo ========================================
echo ✅ Setup complete!
echo ========================================
echo.
echo Next steps:
echo ----------------
echo 1. Start the database (if not already running):
echo    - Run: start_docker.bat
echo.
echo 2. Edit the .env file and add:
echo    - GEMINI_API_KEY (required)
echo    - TELEGRAM_BOT_TOKEN (optional)
echo    - DATABASE_URL is pre-configured for Docker
echo.
echo 3. To run the project:
echo    - Start Backend: start_backend.bat
echo    - Start Telegram Bot: start_telegram_bot.bat (optional)
echo.
echo 4. Open your browser at: http://localhost:8000
echo.
echo ========================================
echo 📚 For more information, see README.md
echo ========================================
echo.
pause
