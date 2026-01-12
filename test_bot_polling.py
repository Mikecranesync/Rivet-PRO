"""
Test the RIVET Photo Bot v2 workflow using Telegram long polling
This bypasses the need for HTTPS webhook by simulating Telegram updates
"""

import requests
import json
import time

N8N_URL = "http://72.60.175.144:5678"
TELEGRAM_BOT_TOKEN = "8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE"
WEBHOOK_PATH = "rivet-photo-bot-v2"

def get_bot_info():
    """Get bot information"""
    r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe")
    if r.json().get('ok'):
        bot = r.json().get('result')
        print(f"Bot Username: @{bot.get('username')}")
        print(f"Bot ID: {bot.get('id')}")
        print(f"Bot Name: {bot.get('first_name')}")
        return bot
    else:
        print(f"Failed to get bot info: {r.json()}")
        return None

def delete_webhook():
    """Delete any existing webhook to enable polling mode"""
    print("\nDeleting existing webhook...")
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook",
        json={'drop_pending_updates': True}
    )
    result = r.json()
    if result.get('ok'):
        print("✓ Webhook deleted successfully")
        return True
    else:
        print(f"✗ Failed to delete webhook: {result}")
        return False

def forward_update_to_n8n(update):
    """Forward a Telegram update to the n8n webhook"""
    webhook_url = f"{N8N_URL}/webhook/{WEBHOOK_PATH}"

    try:
        r = requests.post(webhook_url, json=update, timeout=30)
        print(f"  → n8n response: {r.status_code}")
        if r.status_code == 200:
            print(f"  → Response body: {r.json()}")
            return True
        else:
            print(f"  → Error: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"  → Error forwarding to n8n: {e}")
        return False

def poll_updates():
    """Poll for updates and forward them to n8n webhook"""
    print("\n" + "="*60)
    print("Starting polling mode...")
    print("="*60)
    print("\nWaiting for messages... (Ctrl+C to stop)")
    print("Send a message or photo to the bot to test!")
    print()

    offset = None

    try:
        while True:
            params = {'timeout': 30, 'allowed_updates': ['message']}
            if offset:
                params['offset'] = offset

            r = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
                params=params,
                timeout=35
            )

            result = r.json()
            if not result.get('ok'):
                print(f"Error getting updates: {result}")
                time.sleep(5)
                continue

            updates = result.get('result', [])

            for update in updates:
                offset = update['update_id'] + 1

                # Extract message info
                message = update.get('message', {})
                chat_id = message.get('chat', {}).get('id')
                text = message.get('text', '')
                has_photo = 'photo' in message

                print(f"\n[Update {update['update_id']}]")
                print(f"  Chat ID: {chat_id}")
                print(f"  Text: {text if text else '(no text)'}")
                print(f"  Has Photo: {has_photo}")

                # Forward to n8n
                print(f"  Forwarding to n8n webhook...")
                forward_update_to_n8n(update)

            if not updates:
                print(".", end="", flush=True)

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nStopping polling mode...")
        return

def test_workflow_manually():
    """Send a test update directly to n8n"""
    print("\n" + "="*60)
    print("Manual Workflow Test")
    print("="*60)

    test_update = {
        "update_id": 999999,
        "message": {
            "message_id": 123,
            "from": {
                "id": 123456789,
                "first_name": "Test",
                "username": "testuser"
            },
            "chat": {
                "id": 123456789,
                "first_name": "Test",
                "username": "testuser",
                "type": "private"
            },
            "date": int(time.time()),
            "text": "/start"
        }
    }

    print("\nSending test update (text message)...")
    forward_update_to_n8n(test_update)

def main():
    print("="*60)
    print("RIVET Photo Bot v2 - Polling Mode Tester")
    print("="*60)

    # Get bot info
    bot = get_bot_info()
    if not bot:
        print("Cannot proceed without bot info")
        return

    print("\nOptions:")
    print("1. Start polling mode (receive real messages)")
    print("2. Send test message to workflow")
    print("3. Delete webhook and start polling")
    print()

    choice = input("Choose option (1-3): ").strip()

    if choice == "1":
        poll_updates()
    elif choice == "2":
        test_workflow_manually()
    elif choice == "3":
        delete_webhook()
        time.sleep(2)
        poll_updates()
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()
