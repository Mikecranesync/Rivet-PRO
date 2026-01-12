@echo off
title Rivet-PRO CMMS Telegram Bot - Quick Test
color 0A

echo.
echo  ========================================
echo   RIVET-PRO CMMS TELEGRAM BOT TEST
echo  ========================================
echo.

REM Check if CMMS is running
echo [1/4] Checking if CMMS is running...
curl -s -o nul -w "%%{http_code}" http://localhost:8081 > temp_status.txt 2>&1
set /p STATUS=<temp_status.txt
del temp_status.txt

if "%STATUS%"=="000" (
    echo [X] CMMS is NOT running!
    echo.
    echo Please start CMMS first:
    echo   1. Open another terminal
    echo   2. cd C:\Users\hharp\OneDrive\Desktop\grashjs-cmms
    echo   3. docker-compose up -d
    echo.
    pause
    exit /b 1
)

echo [OK] CMMS is accessible at http://localhost:8081
echo.

echo [2/4] Checking Python dependencies...
python -c "import requests" 2>nul
if %errorlevel% neq 0 (
    echo [!] Installing requests...
    pip install requests
)

python -c "import telegram" 2>nul
if %errorlevel% neq 0 (
    echo [!] Installing python-telegram-bot...
    pip install python-telegram-bot
)
echo [OK] All dependencies installed
echo.

echo [3/4] Configuration
echo.
echo You'll need:
echo   1. Your CMMS email (from http://localhost:3001)
echo   2. Your CMMS password
echo   3. Your Telegram Bot Token (from @BotFather)
echo.

set /p CMMS_EMAIL="Enter CMMS email: "
set /p CMMS_PASSWORD="Enter CMMS password: "
set /p BOT_TOKEN="Enter Telegram bot token: "

REM Save to environment
set CMMS_EMAIL=%CMMS_EMAIL%
set CMMS_PASSWORD=%CMMS_PASSWORD%
set TELEGRAM_BOT_TOKEN=%BOT_TOKEN%

echo.
echo [4/4] Starting bot...
echo.
echo ========================================
echo  BOT IS STARTING...
echo ========================================
echo.
echo Configuration:
echo   CMMS: http://localhost:8081
echo   Email: %CMMS_EMAIL%
echo   Token: %BOT_TOKEN:~0,15%...
echo.
echo ========================================
echo.
echo The bot will now connect to CMMS and start.
echo.
echo When you see "Bot is running!" open Telegram
echo and send /start to your bot.
echo.
echo Press Ctrl+C to stop the bot.
echo.
echo ========================================
echo.

python test_telegram_bot.py

echo.
echo Bot stopped.
pause
