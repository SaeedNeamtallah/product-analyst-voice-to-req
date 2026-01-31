@echo off
chcp 65001 >nul
color 0E
echo ========================================
echo    RAGMind - Update GitHub
echo    Updating project on GitHub
echo ========================================
echo.

:: Check if Git is initialized
if not exist ".git\" (
    echo [ERROR] Project is not initialized with Git!
    echo Please run push_to_github.bat first
    pause
    exit /b 1
)

echo ========================================
echo 1. Add changes
echo ========================================
git add .
echo [✓] Changes staged
echo.

echo ========================================
echo 2. Show changed files
echo ========================================
git status --short
echo.

echo ========================================
echo 3. Create commit
echo ========================================
set /p COMMIT_MSG="Enter commit message: "
if "%COMMIT_MSG%"=="" set COMMIT_MSG=Update project files

git commit -m "%COMMIT_MSG%"
if errorlevel 1 (
    echo [WARNING] No new changes to commit
    echo.
    choice /C YN /M "Do you want to continue anyway?"
    if errorlevel 2 (
        echo [INFO] Cancelled
        pause
        exit /b 0
    )
)
echo [✓] Commit created
echo.

echo ========================================
echo 4. Push updates to GitHub
echo ========================================
echo [INFO] Pushing updates...
git push
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to push updates!
    echo.
    echo Try the following:
    echo   git pull origin main --rebase
    echo   git push
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ Project updated successfully!
echo ========================================
echo.
pause
