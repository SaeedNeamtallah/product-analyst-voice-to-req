@echo off
REM RAGMind One-Click Startup (Docker + Backend + Frontend)

echo ========================================
echo    RAGMind One-Click Start
echo ========================================
echo.

REM Start Docker services (Postgres + Qdrant)
call start_docker.bat
if errorlevel 1 (
	echo [ERROR] Docker services failed to start.
	pause
	exit /b 1
)

REM Start backend (also starts frontend)
call start_backend.bat
if errorlevel 1 (
	echo [ERROR] Backend failed to start.
	pause
	exit /b 1
)
