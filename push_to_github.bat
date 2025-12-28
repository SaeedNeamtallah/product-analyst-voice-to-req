@echo off
chcp 65001 >nul
color 0B
echo ========================================
echo    RAGMind - Push to GitHub
echo    رفع المشروع على GitHub
echo ========================================
echo.

:: Repository URL - CHANGE THIS!
set REPO_URL=https://github.com/ZozElwakil/RAGMind.git

echo [!] هام: تأكد من تغيير REPO_URL في هذا الملف!
echo     Current URL: %REPO_URL%
echo.
choice /C YN /M "هل قمت بتغيير الرابط إلى repository الخاص بك؟"
if errorlevel 2 (
    echo [!] يرجى تعديل الملف وتغيير REPO_URL
    pause
    exit /b 1
)

echo.
echo ========================================
echo 1. تهيئة Git Repository
echo ========================================

:: Check if already initialized
if exist ".git\" (
    echo [✓] Git repository موجود بالفعل
) else (
    echo [INFO] جاري تهيئة Git...
    git init
    if errorlevel 1 (
        echo [ERROR] فشل تهيئة Git!
        echo تأكد من تثبيت Git: https://git-scm.com/
        pause
        exit /b 1
    )
    echo [✓] تم تهيئة Git بنجاح
)
echo.

echo ========================================
echo 2. إضافة جميع الملفات
echo ========================================
git add .
if errorlevel 1 (
    echo [ERROR] فشل إضافة الملفات!
    pause
    exit /b 1
)
echo [✓] تم إضافة جميع الملفات
echo.

echo ========================================
echo 3. عمل Commit
echo ========================================
git commit -m "Initial commit: RAGMind - Intelligent Document Q&A System"
if errorlevel 1 (
    echo [WARNING] ربما لا توجد تغييرات جديدة أو Commit موجود بالفعل
)
echo [✓] تم عمل Commit
echo.

echo ========================================
echo 4. تسمية البرانش الرئيسي
echo ========================================
git branch -M main
echo [✓] تم تسمية البرانش بـ main
echo.

echo ========================================
echo 5. ربط المشروع بـ GitHub
echo ========================================

:: Check if origin already exists
git remote | findstr /C:"origin" >nul 2>&1
if errorlevel 1 (
    echo [INFO] جاري ربط المشروع بـ %REPO_URL%...
    git remote add origin %REPO_URL%
    if errorlevel 1 (
        echo [ERROR] فشل ربط المشروع!
        pause
        exit /b 1
    )
    echo [✓] تم ربط المشروع بنجاح
) else (
    echo [!] Remote origin موجود بالفعل
    echo [INFO] تحديث الرابط...
    git remote set-url origin %REPO_URL%
    echo [✓] تم تحديث الرابط
)
echo.

echo ========================================
echo 6. رفع الملفات على GitHub
echo ========================================
echo [INFO] جاري رفع الملفات...
echo [!] سيُطلب منك إدخال:
echo     - Username: اسم المستخدم على GitHub
echo     - Password: Personal Access Token (ليس الباسورد العادي!)
echo.
echo [INFO] للحصول على Token:
echo     GitHub → Settings → Developer settings → Personal access tokens
echo.

git push -u origin main
if errorlevel 1 (
    echo.
    echo [ERROR] فشل رفع الملفات!
    echo.
    echo الأسباب المحتملة:
    echo   1. بيانات الدخول غير صحيحة (استخدم Token ليس Password)
    echo   2. الرابط غير صحيح
    echo   3. لا يوجد اتصال بالإنترنت
    echo.
    echo للمحاولة مرة أخرى، شغل الأمر:
    echo   git push -u origin main
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ تم رفع المشروع بنجاح!
echo ========================================
echo.
echo يمكنك الآن زيارة المشروع على:
echo %REPO_URL%
echo.
echo للتحديثات المستقبلية، استخدم: update_github.bat
echo.
pause
