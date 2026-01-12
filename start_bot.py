#!/usr/bin/env python3
"""
Easy launcher for Rivet-PRO CMMS Bot
Handles credential setup automatically
"""
import os
import sys
import json
from pathlib import Path

# Add integrations to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'integrations'))

def check_cmms():
    """Check if CMMS is running"""
    import requests
    try:
        r = requests.get("http://localhost:8081/actuator/health", timeout=3)
        return True
    except:
        return False

def get_credentials():
    """Get or prompt for credentials"""
    config_file = Path("bot_config.json")

    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)
            print("\n=== Saved Credentials Found ===")
            print(f"Email: {config['email']}")
            print(f"API: {config['api_url']}")

            use_saved = input("\nUse these credentials? (Y/n): ").strip().lower()
            if use_saved != 'n':
                return config

    print("\n=== CMMS Account Setup ===")
    print("\nIf you don't have an account yet:")
    print("  1. Open http://localhost:3001 in your browser")
    print("  2. Click 'Sign Up'")
    print("  3. Create your account")
    print("  4. Come back here!\n")

    email = input("Enter your CMMS email: ").strip()
    password = input("Enter your CMMS password: ").strip()

    config = {
        "email": email,
        "password": password,
        "api_url": "http://localhost:8081",
        "bot_token": "7855741814:AAFHIk0vPmG9ZHACISMl-izzDwdS0bk_nYo"
    }

    # Save for next time
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"\n✓ Credentials saved to {config_file}")

    return config

def test_connection(email, password, api_url):
    """Test CMMS connection"""
    from grashjs_client import GrashjsClient

    try:
        print("\n=== Testing Connection ===")
        cmms = GrashjsClient(api_url)
        cmms.login(email, password)

        user_info = cmms.get_current_user()
        print(f"✓ Connected to CMMS")
        print(f"✓ Logged in as: {user_info.get('email')}")
        print(f"✓ Organization: {user_info.get('organizationName', 'N/A')}")

        return True

    except Exception as e:
        print(f"\n✗ Connection failed: {e}")
        print("\nPlease check:")
        print("  - CMMS is running at http://localhost:8081")
        print("  - Email and password are correct")
        print("  - You created the account at http://localhost:3001")
        return False

def update_bot_file(email, password):
    """Update the bot file with credentials"""
    bot_file = Path("cmms_bot.py")

    if not bot_file.exists():
        print("✗ cmms_bot.py not found!")
        return False

    content = bot_file.read_text(encoding='utf-8')

    # Update credentials
    import re
    content = re.sub(r'CMMS_EMAIL = ".*?"', f'CMMS_EMAIL = "{email}"', content)
    content = re.sub(r'CMMS_PASSWORD = ".*?"', f'CMMS_PASSWORD = "{password}"', content)

    bot_file.write_text(content, encoding='utf-8')
    print("✓ Bot configured")

    return True

def main():
    print("=" * 50)
    print("  RIVET-PRO CMMS TELEGRAM BOT")
    print("=" * 50)

    # Check CMMS
    print("\n[1/4] Checking CMMS...")
    if not check_cmms():
        print("✗ CMMS is not running!")
        print("\nPlease start CMMS:")
        print("  cd C:\\Users\\hharp\\OneDrive\\Desktop\\grashjs-cmms")
        print("  docker-compose up -d")
        input("\nPress Enter to exit...")
        return

    print("✓ CMMS is running at http://localhost:8081")

    # Get credentials
    print("\n[2/4] Getting credentials...")
    config = get_credentials()

    # Test connection
    print("\n[3/4] Testing connection...")
    if not test_connection(config['email'], config['password'], config['api_url']):
        retry = input("\nTry again? (Y/n): ").strip().lower()
        if retry != 'n':
            # Delete config and retry
            Path("bot_config.json").unlink(missing_ok=True)
            return main()
        else:
            return

    # Update bot file
    print("\n[4/4] Configuring bot...")
    if not update_bot_file(config['email'], config['password']):
        return

    # Start bot
    print("\n" + "=" * 50)
    print("  STARTING BOT")
    print("=" * 50)
    print("\n✓ Bot is ready!")
    print("✓ Open Telegram and send /start to your bot")
    print("\nBot token: " + config['bot_token'][:20] + "...")
    print("\nPress Ctrl+C to stop\n")
    print("=" * 50 + "\n")

    # Import and run the bot
    import cmms_bot
    cmms_bot.CMMS_EMAIL = config['email']
    cmms_bot.CMMS_PASSWORD = config['password']
    cmms_bot.CMMS_API_URL = config['api_url']
    cmms_bot.BOT_TOKEN = config['bot_token']
    cmms_bot.main()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nBot stopped by user")
    except Exception as e:
        print(f"\n\n✗ Error: {e}")
        input("\nPress Enter to exit...")
