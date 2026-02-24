@echo off
REM Tawasul One-Click Startup (Docker + Backend + Frontend)

echo ========================================
echo    Tawasul One-Click Start
echo ========================================
echo.

REM Start Docker services (Postgres)
set SKIP_DOCKER_PAUSE=1
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
