@echo off
chcp 65001 >nul
color 0A
echo ========================================
echo    RAGMind - Setup Script
echo    تثبيت جميع متطلبات المشروع
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python غير مثبت على الجهاز!
    echo يرجى تثبيت Python 3.8 أو أحدث من: https://www.python.org/
    pause
    exit /b 1
)

echo [✓] Python مثبت
python --version
echo.

:: Check if PostgreSQL is accessible
echo [INFO] يرجى التأكد من تثبيت PostgreSQL وأنه يعمل...
echo        يمكن تحميله من: https://www.postgresql.org/download/
echo.

:: Create virtual environment
echo ========================================
echo 1. إنشاء البيئة الافتراضية (Virtual Environment)
echo ========================================
if exist "venv\" (
    echo [!] البيئة الافتراضية موجودة بالفعل
    choice /C YN /M "هل تريد إعادة إنشائها؟"
    if errorlevel 2 goto skip_venv
    if errorlevel 1 (
        echo [INFO] حذف البيئة القديمة...
        rmdir /s /q venv
    )
)

echo [INFO] إنشاء بيئة افتراضية جديدة...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] فشل إنشاء البيئة الافتراضية!
    pause
    exit /b 1
)
echo [✓] تم إنشاء البيئة الافتراضية بنجاح
echo.

:skip_venv

:: Activate virtual environment
echo ========================================
echo 2. تفعيل البيئة الافتراضية
echo ========================================
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] فشل تفعيل البيئة الافتراضية!
    pause
    exit /b 1
)
echo [✓] تم تفعيل البيئة الافتراضية
echo.

:: Upgrade pip
echo ========================================
echo 3. تحديث pip
echo ========================================
python -m pip install --upgrade pip
echo [✓] تم تحديث pip
echo.

:: Install dependencies
echo ========================================
echo 4. تثبيت المكتبات المطلوبة (هذا قد يستغرق بضع دقائق...)
echo ========================================
pip install -r backend\requirements.txt
if errorlevel 1 (
    echo [ERROR] فشل تثبيت المكتبات!
    echo يرجى التحقق من ملف requirements.txt والاتصال بالإنترنت
    pause
    exit /b 1
)
echo [✓] تم تثبيت جميع المكتبات بنجاح
echo.

:: Create .env file if not exists
echo ========================================
echo 5. إنشاء ملف الإعدادات (.env)
echo ========================================
if exist ".env" (
    echo [!] ملف .env موجود بالفعل
    choice /C YN /M "هل تريد إعادة إنشائه من القالب؟"
    if errorlevel 2 goto skip_env
)

if exist ".env.example" (
    echo [INFO] نسخ الإعدادات من .env.example...
    copy .env.example .env >nul
    echo [✓] تم إنشاء ملف .env
    echo [!] يرجى تعديل ملف .env وإضافة:
    echo     - DATABASE_URL
    echo     - GEMINI_API_KEY
    echo     - TELEGRAM_BOT_TOKEN (اختياري)
) else (
    echo [WARNING] ملف .env.example غير موجود
    echo يرجى إنشاء ملف .env يدوياً وإضافة الإعدادات المطلوبة
)
echo.

:skip_env

:: Create uploads directory
echo ========================================
echo 6. إنشاء مجلدات المشروع
echo ========================================
if not exist "uploads\" mkdir uploads
echo [✓] تم إنشاء مجلد uploads
if not exist "qdrant_data\" mkdir qdrant_data
echo [✓] تم إنشاء مجلد qdrant_data
echo.

:: Database setup instructions
echo ========================================
echo 7. إعداد قاعدة البيانات
echo ========================================
echo [!] يجب إعداد PostgreSQL يدوياً:
echo.
echo     1. تشغيل PostgreSQL
echo     2. فتح pgAdmin أو psql
echo     3. تشغيل الأوامر من ملف create_database.sql أو:
echo.
echo        CREATE DATABASE ragmind;
echo        \c ragmind
echo        CREATE EXTENSION vector;
echo.
echo     4. تحديث DATABASE_URL في ملف .env
echo.
choice /C YN /M "هل قمت بإعداد قاعدة البيانات؟"
if errorlevel 2 (
    echo [!] يرجى إعداد قاعدة البيانات قبل تشغيل المشروع
) else (
    echo [✓] قاعدة البيانات جاهزة
)
echo.

:: Initialize database
echo ========================================
echo 8. تهيئة جداول قاعدة البيانات
echo ========================================
choice /C YN /M "هل تريد تهيئة جداول قاعدة البيانات الآن؟"
if errorlevel 1 (
    echo [INFO] جاري تهيئة قاعدة البيانات...
    python -m backend.init_database
    if errorlevel 1 (
        echo [ERROR] فشلت تهيئة قاعدة البيانات
        echo يرجى التحقق من:
        echo   - اتصال PostgreSQL
        echo   - DATABASE_URL في ملف .env
        echo   - تثبيت pgvector extension
    ) else (
        echo [✓] تم تهيئة قاعدة البيانات بنجاح
    )
) else (
    echo [!] يمكنك تهيئة قاعدة البيانات لاحقاً بالأمر:
    echo     python -m backend.init_database
)
echo.

:: Summary
echo ========================================
echo ✅ اكتمل التثبيت!
echo ========================================
echo.
echo الخطوات التالية:
echo ----------------
echo 1. تعديل ملف .env وإضافة:
echo    - DATABASE_URL (مطلوب)
echo    - GEMINI_API_KEY (مطلوب)
echo    - TELEGRAM_BOT_TOKEN (اختياري)
echo.
echo 2. لتشغيل المشروع:
echo    - تشغيل Backend: start_backend.bat
echo    - تشغيل Telegram Bot: start_telegram_bot.bat (اختياري)
echo.
echo 3. فتح المتصفح على: http://localhost:8000
echo.
echo ========================================
echo 📚 للمزيد من المعلومات، راجع ملف README.md
echo ========================================
echo.
pause
