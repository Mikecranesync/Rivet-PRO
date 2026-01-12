#!/usr/bin/env python3
"""
Simple bot launcher - no fancy characters, just works
"""
import os
import sys

# Configuration
CMMS_EMAIL = "mike@cranesync.com"
CMMS_PASSWORD = "Bo1ws2er@12"
CMMS_API_URL = "http://localhost:8081"
BOT_TOKEN = "7855741814:AAFHIk0vPmG9ZHACISMl-izzDwdS0bk_nYo"

print("="*50)
print("RIVET-PRO CMMS BOT")
print("="*50)
print(f"CMMS: {CMMS_API_URL}")
print(f"Email: {CMMS_EMAIL}")
print("="*50)

# Import and configure the bot
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'integrations'))
import cmms_bot

# Override settings
cmms_bot.CMMS_EMAIL = CMMS_EMAIL
cmms_bot.CMMS_PASSWORD = CMMS_PASSWORD
cmms_bot.CMMS_API_URL = CMMS_API_URL
cmms_bot.BOT_TOKEN = BOT_TOKEN

# Run it
print("\nStarting bot...")
print("Open Telegram and send /start to your bot!")
print("Press Ctrl+C to stop\n")
cmms_bot.main()
