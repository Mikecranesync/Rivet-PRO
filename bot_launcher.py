#!/usr/bin/env python3
"""
Rivet-PRO Bot Launcher
Simple, robust launcher with validation and lockfile support
"""
import os
import sys
import time
import atexit
from pathlib import Path

# Configuration
CMMS_EMAIL = "mike@cranesync.com"
CMMS_PASSWORD = "Bo1ws2er@12"
CMMS_API_URL = "http://localhost:8081"
BOT_TOKEN = "7855741814:AAFHIk0vPmG9ZHACISMl-izzDwdS0bk_nYo"
LOCKFILE = Path("rivet_bot.lock")

# Add integrations to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'integrations'))


def cleanup_lockfile():
    """Remove lockfile on exit"""
    if LOCKFILE.exists():
        LOCKFILE.unlink()
        print("\n>> Lockfile removed")


def check_already_running():
    """Check if bot is already running"""
    if LOCKFILE.exists():
        print("ERROR: Bot is already running!")
        print(f"If you're sure it's not running, delete: {LOCKFILE}")
        sys.exit(1)

    # Create lockfile
    LOCKFILE.write_text(str(os.getpid()))
    atexit.register(cleanup_lockfile)


def test_cmms_connection():
    """Test CMMS API is accessible"""
    import requests

    print("\n>> Testing CMMS connection...")
    try:
        r = requests.get(f"{CMMS_API_URL}/actuator/health", timeout=5)
        if r.status_code in [200, 403]:
            print(f">> CMMS API is responding (HTTP {r.status_code})")
            return True
        else:
            print(f"WARNING: CMMS API returned HTTP {r.status_code}")
            return False
    except Exception as e:
        print(f"ERROR: Could not connect to CMMS: {e}")
        print(f"Make sure CMMS is running at {CMMS_API_URL}")
        return False


def test_cmms_login():
    """Test CMMS login credentials"""
    from grashjs_client import GrashjsClient

    print("\n>> Testing CMMS login...")
    try:
        cmms = GrashjsClient(CMMS_API_URL)
        cmms.login(CMMS_EMAIL, CMMS_PASSWORD)

        user_info = cmms.get_current_user()
        print(f">> Logged in as: {user_info.get('email')}")
        print(f">> Organization: {user_info.get('organizationName', 'N/A')}")

        # Try to get assets count
        try:
            assets = cmms.get_assets()
            count = assets.get('totalElements', 0) if assets else 0
            print(f">> Assets in CMMS: {count}")
        except:
            pass

        return True

    except Exception as e:
        print(f"ERROR: Login failed: {e}")
        print("\nPlease check:")
        print(f"  - Account {CMMS_EMAIL} exists at http://localhost:3001")
        print("  - Password is correct")
        print("  - CMMS is running")
        return False


def start_bot():
    """Start the Telegram bot"""
    print("\n" + "=" * 50)
    print("  STARTING TELEGRAM BOT")
    print("=" * 50)
    print(f"\n>> CMMS: {CMMS_API_URL}")
    print(f">> User: {CMMS_EMAIL}")
    print(f">> Bot Token: {BOT_TOKEN[:20]}...")
    print("\n>> Open Telegram and send /start to your bot!")
    print("\n>> Press Ctrl+C to stop")
    print("=" * 50 + "\n")

    # Import and run the bot
    import cmms_bot

    # Override settings
    cmms_bot.CMMS_EMAIL = CMMS_EMAIL
    cmms_bot.CMMS_PASSWORD = CMMS_PASSWORD
    cmms_bot.CMMS_API_URL = CMMS_API_URL
    cmms_bot.BOT_TOKEN = BOT_TOKEN

    # Run the bot
    cmms_bot.main()


def main():
    """Main entry point"""
    print("=" * 50)
    print("  RIVET-PRO BOT LAUNCHER")
    print("=" * 50)

    # Check if already running
    check_already_running()

    # Test CMMS connection
    if not test_cmms_connection():
        print("\nStarting bot anyway (will retry connection...)")

    # Test CMMS login
    if not test_cmms_login():
        print("\nERROR: Cannot start bot without valid CMMS login")
        sys.exit(1)

    # Start the bot
    start_bot()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n>> Bot stopped by user")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
