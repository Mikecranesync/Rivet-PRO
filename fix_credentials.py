#!/usr/bin/env python3
"""
Fix CMMS Credentials
Interactive script to test and update CMMS login credentials
"""
import requests
import json
import sys
from pathlib import Path


def test_login(email, password):
    """Test CMMS login with credentials"""
    url = "http://localhost:8081/auth/login"

    try:
        r = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={"email": email, "password": password},
            timeout=10
        )

        print(f"\nHTTP Status: {r.status_code}")

        if r.status_code == 200:
            data = r.json()
            print("✅ LOGIN SUCCESSFUL!")
            print(f"Token: {data.get('token', 'N/A')[:50]}...")
            return True, data.get('token')
        elif r.status_code == 403:
            print("❌ LOGIN FAILED - HTTP 403 Forbidden")
            print("This usually means:")
            print("  - Wrong email or password")
            print("  - Account doesn't exist")
            print("  - Account is disabled")
            return False, None
        elif r.status_code == 401:
            print("❌ LOGIN FAILED - HTTP 401 Unauthorized")
            print("Wrong email or password")
            return False, None
        else:
            print(f"❌ UNEXPECTED RESPONSE: HTTP {r.status_code}")
            print(f"Body: {r.text}")
            return False, None

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False, None


def update_bot_files(email, password):
    """Update bot files with new credentials"""
    files_to_update = [
        ("cmms_bot.py", [
            ('CMMS_EMAIL = "', 'CMMS_EMAIL = "'),
            ('CMMS_PASSWORD = "', 'CMMS_PASSWORD = "')
        ]),
        ("bot_launcher.py", [
            ('CMMS_EMAIL = "', 'CMMS_EMAIL = "'),
            ('CMMS_PASSWORD = "', 'CMMS_PASSWORD = "')
        ]),
        ("run_bot_simple.py", [
            ('CMMS_EMAIL = "', 'CMMS_EMAIL = "'),
            ('CMMS_PASSWORD = "', 'CMMS_PASSWORD = "')
        ])
    ]

    updated = []

    for filename, patterns in files_to_update:
        filepath = Path(filename)
        if not filepath.exists():
            print(f"⚠️  {filename} not found, skipping...")
            continue

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Replace email
            if 'CMMS_EMAIL' in content:
                # Find the line and replace
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'CMMS_EMAIL = "' in line:
                        lines[i] = f'CMMS_EMAIL = "{email}"'
                    elif 'CMMS_PASSWORD = "' in line:
                        lines[i] = f'CMMS_PASSWORD = "{password}"'

                content = '\n'.join(lines)

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)

                print(f"✅ Updated {filename}")
                updated.append(filename)

        except Exception as e:
            print(f"❌ Error updating {filename}: {e}")

    return updated


def main():
    """Main entry point"""
    print("=" * 60)
    print("  CMMS CREDENTIAL TESTER & FIXER")
    print("=" * 60)

    print("\nThis script will:")
    print("1. Test your CMMS login credentials")
    print("2. Update all bot files if credentials work")
    print("3. Show you the correct values to use")

    # Check CMMS is running
    print("\n>> Checking CMMS is running...")
    try:
        r = requests.get("http://localhost:8081/actuator/health", timeout=3)
        if r.status_code in [200, 403]:
            print("✅ CMMS API is responding")
        else:
            print(f"⚠️  CMMS returned HTTP {r.status_code}")
    except Exception as e:
        print(f"❌ CMMS is not running: {e}")
        print("\nPlease start CMMS:")
        print("  cd C:\\Users\\hharp\\OneDrive\\Desktop\\grashjs-cmms")
        print("  docker-compose up -d")
        sys.exit(1)

    # Current credentials
    print("\n" + "=" * 60)
    print("CURRENT CREDENTIALS IN BOT FILES:")
    print("=" * 60)
    print("Email: mike@cranesync.com")
    print("Password: Bo1ws2er@12")
    print()

    # Test current credentials
    print(">> Testing current credentials...")
    success, token = test_login("mike@cranesync.com", "Bo1ws2er@12")

    if success:
        print("\n" + "=" * 60)
        print("✅ CREDENTIALS ARE CORRECT!")
        print("=" * 60)
        print("\nYour bot should work with these credentials.")
        print("If it's still not working, there may be another issue.")
        return

    # Credentials failed, ask for new ones
    print("\n" + "=" * 60)
    print("CREDENTIALS FAILED - LET'S FIX THEM")
    print("=" * 60)
    print("\nOptions:")
    print("1. Enter different credentials to test")
    print("2. Reset password in CMMS web UI")
    print("3. Create new account")

    choice = input("\nWhat would you like to do? (1/2/3): ").strip()

    if choice == "1":
        email = input("\nEnter CMMS email: ").strip()
        password = input("Enter CMMS password: ").strip()

        print(f"\n>> Testing {email}...")
        success, token = test_login(email, password)

        if success:
            print("\n" + "=" * 60)
            print("✅ THESE CREDENTIALS WORK!")
            print("=" * 60)

            update = input("\nUpdate bot files with these credentials? (y/n): ").strip().lower()
            if update == 'y':
                print("\n>> Updating bot files...")
                updated = update_bot_files(email, password)

                print("\n" + "=" * 60)
                print("✅ CREDENTIALS UPDATED!")
                print("=" * 60)
                print(f"\nUpdated files: {', '.join(updated)}")
                print("\nYou can now run START_RIVET.bat and it should work!")
            else:
                print("\nNo files updated. You'll need to update them manually:")
                print(f"  Email: {email}")
                print(f"  Password: {password}")
        else:
            print("\n❌ These credentials don't work either.")
            print("\nPlease:")
            print("1. Go to http://localhost:3001")
            print("2. Try logging in manually")
            print("3. If you can't login, reset password or create new account")
            print("4. Run this script again with the correct credentials")

    elif choice == "2":
        print("\nTo reset password:")
        print("1. Go to http://localhost:3001")
        print("2. Click 'Forgot Password' (if available)")
        print("3. Or login with current credentials and change password in settings")
        print("4. Run this script again to update bot files")

    elif choice == "3":
        print("\nTo create new account:")
        print("1. Go to http://localhost:3001")
        print("2. Click 'Sign Up'")
        print("3. Create new account")
        print("4. Run this script again with the new credentials")

    else:
        print("\nInvalid choice. Exiting.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
