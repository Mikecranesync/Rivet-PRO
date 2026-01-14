@echo off
title Rivet-PRO CMMS Bot - Setup and Run
color 0A

echo.
echo ================================================
echo   RIVET-PRO CMMS TELEGRAM BOT - SETUP
echo ================================================
echo.

cd /d "%~dp0"

REM Check if CMMS is running
echo [1/5] Checking if CMMS is running...
curl -s -o nul -w "%%{http_code}" http://localhost:8081/actuator/health > temp_status.txt
set /p status=<temp_status.txt
del temp_status.txt

if "%status%"=="403" (
    echo [OK] CMMS is running at http://localhost:8081
    echo.
) else (
    echo [ERROR] CMMS is not running!
    echo.
    echo Please start CMMS first:
    echo   cd C:\Users\hharp\OneDrive\Desktop\grashjs-cmms
    echo   docker-compose up -d
    echo.
    pause
    exit /b 1
)

echo [2/5] Have you created a CMMS account yet?
echo.
echo If not, please:
echo   1. Open http://localhost:3001 in your browser
echo   2. Click "Sign Up"
echo   3. Create your account (email + password)
echo   4. Come back here!
echo.
set /p continue="Press ENTER when you have an account..."

echo.
echo [3/5] Enter your CMMS credentials:
echo.
set /p cmms_email="CMMS Email: "
set /p cmms_password="CMMS Password: "

echo.
echo [4/5] Testing connection to CMMS...

REM Test the credentials
python -c "import sys; sys.path.insert(0, 'integrations'); from grashjs_client import GrashjsClient; c = GrashjsClient('http://localhost:8081'); c.login('%cmms_email%', '%cmms_password%'); print('[OK] Successfully connected to CMMS!'); u = c.get_current_user(); print('Logged in as:', u.get('email')); print('Organization:', u.get('organizationName', 'N/A'))" 2>nul

if errorlevel 1 (
    echo [ERROR] Could not connect with these credentials!
    echo.
    echo Please check:
    echo   - Email is correct
    echo   - Password is correct
    echo   - You created the account at http://localhost:3001
    echo.
    pause
    exit /b 1
)

echo.
echo [5/5] Updating bot configuration...

REM Create a temporary Python script to update the bot file
python -c "import re; f = open('cmms_bot.py', 'r', encoding='utf-8'); content = f.read(); f.close(); content = re.sub(r'CMMS_EMAIL = \".*?\"', 'CMMS_EMAIL = \"%cmms_email%\"', content); content = re.sub(r'CMMS_PASSWORD = \".*?\"', 'CMMS_PASSWORD = \"%cmms_password%\"', content); f = open('cmms_bot.py', 'w', encoding='utf-8'); f.write(content); f.close(); print('[OK] Bot configured!')"

echo.
echo ================================================
echo   SETUP COMPLETE!
echo ================================================
echo.
echo Your bot is configured with:
echo   Email: %cmms_email%
echo   CMMS: http://localhost:8081
echo.
echo [6/6] Starting bot...
echo.
echo Open Telegram and send /start to your bot!
echo.
echo ================================================
echo.

python cmms_bot.py

pause
