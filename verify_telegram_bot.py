import os
import requests
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("STEP 1: VERIFY TELEGRAM BOT CONNECTION")
print("=" * 80)
print()

# Get all Telegram bot tokens from .env
bots = {
    'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN'),
    'ORCHESTRATOR_BOT_TOKEN': os.getenv('ORCHESTRATOR_BOT_TOKEN'),
    'PUBLIC_TELEGRAM_BOT_TOKEN': os.getenv('PUBLIC_TELEGRAM_BOT_TOKEN'),
    'TELEGRAM_RIVET_CMMS_TOKEN': os.getenv('TELEGRAM_RIVET_CMMS_TOKEN')
}

print("TELEGRAM BOTS CONFIGURED:")
print("-" * 80)

active_bots = []

for name, token in bots.items():
    if not token:
        print(f"[{name}] Not configured")
        continue

    # Get bot info
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data.get('result', {})
                bot_name = bot_info.get('username', 'Unknown')
                bot_id = bot_info.get('id', 'Unknown')
                first_name = bot_info.get('first_name', 'Unknown')

                print(f"\n[{name}] ACTIVE")
                print(f"  Username: @{bot_name}")
                print(f"  Name: {first_name}")
                print(f"  ID: {bot_id}")

                # Check if bot can receive updates
                updates_url = f"https://api.telegram.org/bot{token}/getUpdates"
                updates_response = requests.get(updates_url, timeout=5)

                if updates_response.status_code == 200:
                    updates_data = updates_response.json()
                    if updates_data.get('ok'):
                        updates = updates_data.get('result', [])
                        print(f"  Recent Updates: {len(updates)}")

                        active_bots.append({
                            'env_name': name,
                            'username': bot_name,
                            'id': bot_id,
                            'token': token,
                            'updates': len(updates)
                        })
            else:
                print(f"\n[{name}] INVALID")
                print(f"  Error: {data.get('description', 'Unknown error')}")
        else:
            print(f"\n[{name}] FAILED")
            print(f"  Status: {response.status_code}")

    except Exception as e:
        print(f"\n[{name}] ERROR")
        print(f"  Exception: {e}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Active bots: {len(active_bots)}")

if active_bots:
    print("\nRecommended bot for testing:")
    # Prefer the main TELEGRAM_BOT_TOKEN
    main_bot = next((b for b in active_bots if b['env_name'] == 'TELEGRAM_BOT_TOKEN'), active_bots[0])
    print(f"  @{main_bot['username']} (ID: {main_bot['id']})")
    print(f"  Telegram link: https://t.me/{main_bot['username']}")

    print("\n" + "=" * 80)
    print("NEXT STEP: Send a test message to the bot")
    print("=" * 80)
    print(f"\n1. Open Telegram and search for: @{main_bot['username']}")
    print(f"2. Start a chat with the bot")
    print(f"3. Send the command: /start")
    print(f"4. The bot should respond if connected to n8n workflows")
    print(f"\nBot Link: https://t.me/{main_bot['username']}")
else:
    print("\n[ERROR] No active Telegram bots found!")
    print("Check your bot tokens in .env file")

print("\n" + "=" * 80)
