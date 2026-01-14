#!/usr/bin/env python3
"""Simple CMMS login tester"""
import requests
import sys

# Test credentials
email = "mike@cranesync.com"
password = "Bo1ws2er@12"
url = "http://localhost:8081/auth/login"

print("=" * 50)
print("CMMS LOGIN TESTER")
print("=" * 50)
print(f"Email: {email}")
print(f"Password: {password}")
print(f"URL: {url}")
print()

try:
    print("Testing login...")
    r = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json={"email": email, "password": password},
        timeout=10
    )

    print(f"HTTP Status: {r.status_code}")
    print(f"Response length: {len(r.text)} bytes")

    if r.status_code == 200:
        print("\nSUCCESS! Login works!")
        data = r.json()
        if 'token' in data:
            print(f"Token: {data['token'][:50]}...")
        print("\nYour credentials are CORRECT!")
        print("The bot should work now.")

    elif r.status_code == 403:
        print("\nFAILED! HTTP 403 Forbidden")
        print("\nThis means:")
        print("- Wrong email or password")
        print("- Account doesn't exist")
        print("- Account is disabled")
        print("\nWhat to do:")
        print("1. Go to http://localhost:3001")
        print("2. Try logging in with the same credentials")
        print("3. If it works in web UI but not here, there's a bug")
        print("4. If it doesn't work, reset your password")

    elif r.status_code == 401:
        print("\nFAILED! HTTP 401 Unauthorized")
        print("Wrong email or password")

    else:
        print(f"\nUNEXPECTED: HTTP {r.status_code}")
        if r.text:
            print(f"Response: {r.text[:200]}")

except requests.exceptions.ConnectionError:
    print("\nERROR: Could not connect to CMMS")
    print("Make sure CMMS is running:")
    print("  cd C:\\Users\\hharp\\OneDrive\\Desktop\\grashjs-cmms")
    print("  docker-compose up -d")
    sys.exit(1)

except Exception as e:
    print(f"\nERROR: {e}")
    sys.exit(1)

print("\n" + "=" * 50)
