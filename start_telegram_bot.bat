@echo off
setlocal
REM Tawasul Telegram Bot Startup Script

set "SCRIPT_DIR=%~dp0"

echo ========================================
echo    Tawasul Telegram Bot
echo ========================================
echo.

REM Activate virtual environment
set "VENV_DIR="
if exist "%SCRIPT_DIR%.venv-3\Scripts\activate.bat" set "VENV_DIR=.venv-3"
if not defined VENV_DIR if exist "%SCRIPT_DIR%.venv-2\Scripts\activate.bat" set "VENV_DIR=.venv-2"
if not defined VENV_DIR if exist "%SCRIPT_DIR%venv\Scripts\activate.bat" set "VENV_DIR=venv"

if not defined VENV_DIR (
    echo ERROR: Virtual environment not found!
    echo Expected one of: .venv-3 or .venv-2 or venv
    echo Please create a virtual environment first.
    pause
    exit /b 1
)

echo Activating virtual environment: %VENV_DIR%
call "%SCRIPT_DIR%%VENV_DIR%\Scripts\activate.bat"
echo.

set "PYTHON_EXE=%SCRIPT_DIR%%VENV_DIR%\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    echo ERROR: Python executable not found at:
    echo %PYTHON_EXE%
    pause
    exit /b 1
)

REM Check if bot token is configured
echo Checking configuration...
"%PYTHON_EXE%" -c "from telegram_bot.config import bot_settings; assert bot_settings.telegram_bot_token != 'your_telegram_bot_token_here', 'Please configure TELEGRAM_BOT_TOKEN in .env file'" 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: Telegram bot token not configured!
    echo Please set TELEGRAM_BOT_TOKEN in the .env file
    echo.
    pause
    exit /b 1
)

REM Start bot
echo Starting Telegram bot...
echo.
python -m telegram_bot.bot
