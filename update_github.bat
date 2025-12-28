@echo off
chcp 65001 >nul
color 0E
echo ========================================
echo    RAGMind - Update GitHub
echo    تحديث المشروع على GitHub
echo ========================================
echo.

:: Check if Git is initialized
if not exist ".git\" (
    echo [ERROR] المشروع غير مربوط بـ Git!
    echo يرجى تشغيل push_to_github.bat أولاً
    pause
    exit /b 1
)

echo ========================================
echo 1. إضافة التعديلات الجديدة
echo ========================================
git add .
echo [✓] تم إضافة التعديلات
echo.

echo ========================================
echo 2. عرض الملفات المتغيرة
echo ========================================
git status --short
echo.

echo ========================================
echo 3. عمل Commit
echo ========================================
set /p COMMIT_MSG="اكتب وصف التعديلات: "
if "%COMMIT_MSG%"=="" set COMMIT_MSG=Update project files

git commit -m "%COMMIT_MSG%"
if errorlevel 1 (
    echo [WARNING] لا توجد تغييرات جديدة للـ commit
    echo.
    choice /C YN /M "هل تريد المتابعة على أي حال؟"
    if errorlevel 2 (
        echo [INFO] تم الإلغاء
        pause
        exit /b 0
    )
)
echo [✓] تم عمل Commit
echo.

echo ========================================
echo 4. رفع التحديثات على GitHub
echo ========================================
echo [INFO] جاري رفع التحديثات...
git push
if errorlevel 1 (
    echo.
    echo [ERROR] فشل رفع التحديثات!
    echo.
    echo جرب الأمر التالي:
    echo   git pull origin main --rebase
    echo   git push
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ تم تحديث المشروع بنجاح!
echo ========================================
echo.
pause
