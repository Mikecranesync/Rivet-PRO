@echo off
echo ========================================
echo Rivet-PRO CMMS Telegram Bot Test Setup
echo ========================================
echo.

echo Step 1: Installing required packages...
pip install python-telegram-bot requests

echo.
echo Step 2: Checking CMMS connection...
echo.

REM Test if CMMS is accessible
curl -s http://localhost:8081 > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] CMMS is not accessible at http://localhost:8081
    echo.
    echo Please start CMMS first:
    echo   cd C:\Users\hharp\OneDrive\Desktop\grashjs-cmms
    echo   docker-compose up -d
    echo.
    pause
    exit /b 1
)

echo [OK] CMMS is running at http://localhost:8081
echo.

echo Step 3: Setting up environment...
echo.
echo Please provide the following information:
echo.

set /p BOT_TOKEN="Enter your Telegram Bot Token: "
set /p CMMS_EMAIL="Enter your CMMS email (from http://localhost:3001): "
set /p CMMS_PASSWORD="Enter your CMMS password: "

echo.
echo Setting environment variables...
set TELEGRAM_BOT_TOKEN=%BOT_TOKEN%
set CMMS_EMAIL=%CMMS_EMAIL%
set CMMS_PASSWORD=%CMMS_PASSWORD%
set CMMS_URL=http://localhost:8081

echo.
echo ========================================
echo Ready to test!
echo ========================================
echo.
echo Environment:
echo   CMMS URL: %CMMS_URL%
echo   CMMS Email: %CMMS_EMAIL%
echo   Bot Token: %BOT_TOKEN:~0,10%...
echo.
echo ========================================
echo.

set /p RUN_TEST="Run API connection test first? (y/n): "
if /i "%RUN_TEST%"=="y" (
    echo.
    echo Running API connection test...
    python test_cmms_connection.py
    echo.
    pause
)

echo.
set /p RUN_BOT="Start Telegram bot now? (y/n): "
if /i "%RUN_BOT%"=="y" (
    echo.
    echo Starting Telegram bot...
    echo.
    echo Open Telegram and send /start to your bot!
    echo Press Ctrl+C to stop the bot.
    echo.
    python test_telegram_bot.py
)

echo.
echo Done!
pause
