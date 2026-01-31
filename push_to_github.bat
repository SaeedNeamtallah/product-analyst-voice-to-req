@echo off
chcp 65001 >nul
color 0B
echo ========================================
echo    RAGMind - Push to GitHub
echo    Push project to GitHub
echo ========================================
echo.

:: Repository URL - CHANGE THIS!
set REPO_URL=https://github.com/ZozElwakil/RAGMind.git

echo [!] هام: تأكد من تغيير REPO_URL في هذا الملف!
echo     Current URL: %REPO_URL%
echo.
choice /C YN /M "Have you changed REPO_URL to your repository?"
if errorlevel 2 (
    echo [!] Please edit this file and change REPO_URL
    pause
    exit /b 1
)

echo.
echo ========================================
echo 1. Initialize Git repository
echo ========================================

:: Check if already initialized
if exist ".git\" (
    echo [✓] Git repository already exists
) else (
    echo [INFO] Initializing Git...
    git init
    if errorlevel 1 (
        echo [ERROR] Failed to initialize Git!
        echo Make sure Git is installed: https://git-scm.com/
        pause
        exit /b 1
    )
    echo [✓] Git initialized successfully
)
echo.

echo ========================================
echo 2. Add all files
echo ========================================
git add .
if errorlevel 1 (
    echo [ERROR] Failed to add files!
    pause
    exit /b 1
)
echo [✓] All files added
echo.

echo ========================================
echo 3. Create commit
echo ========================================
git commit -m "Initial commit: RAGMind - Intelligent Document Q&A System"
if errorlevel 1 (
    echo [WARNING] Maybe no new changes or commit already exists
)
echo [✓] Commit created
echo.

echo ========================================
echo 4. Name main branch
echo ========================================
git branch -M main
echo [✓] Branch renamed to main
echo.

echo ========================================
echo 5. Link project to GitHub
echo ========================================

:: Check if origin already exists
git remote | findstr /C:"origin" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Linking project to %REPO_URL%...
    git remote add origin %REPO_URL%
    if errorlevel 1 (
        echo [ERROR] Failed to add remote!
        pause
        exit /b 1
    )
    echo [✓] Project linked successfully
) else (
    echo [!] Remote origin already exists
    echo [INFO] Updating remote URL...
    git remote set-url origin %REPO_URL%
    echo [✓] URL updated
)
echo.

echo ========================================
echo 6. Push files to GitHub
echo ========================================
echo [INFO] Pushing files...
echo [!] You will be prompted for:
echo     - Username: your GitHub username
echo     - Password: Personal Access Token (use a PAT, not your regular password)
echo.
echo [INFO] To get a token:
echo     GitHub → Settings → Developer settings → Personal access tokens
echo.

git push -u origin main
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to push files!
    echo.
    echo Possible reasons:
    echo   1. Incorrect credentials (use a token, not a password)
    echo   2. Incorrect repository URL
    echo   3. No internet connection
    echo.
    echo To try again, run:
    echo   git push -u origin main
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ Project pushed successfully!
echo ========================================
echo.
echo You can now visit the project at:
echo %REPO_URL%
echo.
echo For future updates, use: update_github.bat
echo.
pause
