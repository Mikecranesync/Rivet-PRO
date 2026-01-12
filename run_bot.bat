@echo off
title Rivet-PRO CMMS Telegram Bot
color 0A

echo.
echo ========================================
echo   RIVET-PRO CMMS TELEGRAM BOT
echo ========================================
echo.

cd /d "%~dp0"

python cmms_bot.py

pause
