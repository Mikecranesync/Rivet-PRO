"""
Complete setup automation for RIVET Photo Bot v2 workflow
This script:
1. Updates workflow nodes with credential IDs
2. Activates the workflow
3. Gets webhook URL
4. Registers webhook with Telegram
5. Tests the bot
"""

import requests
import json
import time

# Configuration
N8N_URL = "http://72.60.175.144:5678"
N8N_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxNzBlNDViYy1iNjFjLTQwOGItYTFmYS00OGQyMTA5Y2FjZWMiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY3ODU5OTc0LCJleHAiOjE3NzA0NDA0MDB9.UW7Z-lSRZ9at6M1l_MwRj3SMBkf2SkzTCagFyu3Ohv4"
WORKFLOW_ID = "7LMKcMmldZsu1l6g"
TELEGRAM_BOT_TOKEN = "8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE"
TELEGRAM_CRED_ID = "if4EOJbvMirfWqCC"

headers = {
    "X-N8N-API-KEY": N8N_API_KEY,
    "Content-Type": "application/json"
}

def log(message, prefix="INFO"):
    print(f"[{prefix}] {message}")

def update_workflow_credentials():
    """Update workflow nodes to use the created credential IDs"""
    log("Fetching workflow...")

    r = requests.get(f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}", headers=headers)
    if r.status_code != 200:
        log(f"Failed to fetch workflow: {r.text}", "ERROR")
        return False

    workflow = r.json()
    log(f"Workflow fetched: {workflow['name']}")

    # Update all Telegram nodes to use the credential
    updated = False
    for node in workflow['nodes']:
        if node['type'] == 'n8n-nodes-base.telegram':
            log(f"Updating Telegram node: {node['name']}")
            if 'credentials' not in node:
                node['credentials'] = {}
            node['credentials']['telegramApi'] = {
                'id': TELEGRAM_CRED_ID,
                'name': 'Telegram Bot API - RIVET'
            }
            updated = True

    if updated:
        log("Saving updated workflow...")
        # Remove fields that can't be updated via API
        clean_workflow = {
            'name': workflow['name'],
            'nodes': workflow['nodes'],
            'connections': workflow['connections'],
            'settings': workflow.get('settings', {}),
            'staticData': workflow.get('staticData')
        }

        r = requests.put(
            f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}",
            headers=headers,
            json=clean_workflow
        )

        if r.status_code in [200, 201]:
            log("Workflow updated successfully!", "SUCCESS")
            return True
        else:
            log(f"Failed to update workflow: {r.text}", "ERROR")
            return False
    else:
        log("No Telegram nodes found to update", "WARNING")
        return True

def activate_workflow():
    """Activate the workflow"""
    log("Activating workflow...")

    r = requests.post(
        f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}/activate",
        headers=headers
    )

    if r.status_code in [200, 201]:
        log("Workflow activated successfully!", "SUCCESS")
        return True
    else:
        log(f"Failed to activate workflow: {r.text}", "ERROR")
        return False

def get_webhook_url():
    """Get the webhook URL from the workflow"""
    webhook_path = "rivet-photo-bot-v2"
    webhook_url = f"{N8N_URL}/webhook/{webhook_path}"
    log(f"Webhook URL: {webhook_url}")
    return webhook_url

def register_telegram_webhook(webhook_url):
    """Register the webhook with Telegram"""
    log("Registering webhook with Telegram...")

    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
        json={'url': webhook_url}
    )

    result = r.json()
    if result.get('ok'):
        log("Webhook registered successfully!", "SUCCESS")
        log(f"Response: {result.get('description')}")
        return True
    else:
        log(f"Failed to register webhook: {result}", "ERROR")
        return False

def verify_telegram_webhook():
    """Verify webhook is registered"""
    log("Verifying webhook registration...")

    r = requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
    )

    result = r.json()
    if result.get('ok'):
        info = result.get('result', {})
        log(f"Webhook URL: {info.get('url')}")
        log(f"Pending Updates: {info.get('pending_update_count', 0)}")
        log(f"Last Error: {info.get('last_error_message', 'None')}")
        return True
    else:
        log(f"Failed to get webhook info: {result}", "ERROR")
        return False

def test_bot():
    """Send a test message to verify bot is working"""
    log("To test the bot:")
    log("1. Open Telegram")
    log("2. Search for @rivet_local_dev_bot (or the bot using token 8161680636)")
    log("3. Send a text message (expect help response)")
    log("4. Send a photo of equipment (expect analysis)")
    log("")
    log("Monitor executions at: http://72.60.175.144:5678/workflow/7LMKcMmldZsu1l6g/executions")

def main():
    print("=" * 60)
    print("RIVET Photo Bot v2 - Complete Setup")
    print("=" * 60)
    print()

    # Step 1: Update credentials
    log("Step 1: Updating workflow with credential IDs...", "STEP")
    if not update_workflow_credentials():
        log("Setup failed at credential update", "ERROR")
        return
    print()

    # Step 2: Activate workflow
    log("Step 2: Activating workflow...", "STEP")
    if not activate_workflow():
        log("Setup failed at activation", "ERROR")
        return
    print()

    # Step 3: Get webhook URL
    log("Step 3: Getting webhook URL...", "STEP")
    webhook_url = get_webhook_url()
    print()

    # Step 4: Register webhook
    log("Step 4: Registering webhook with Telegram...", "STEP")
    if not register_telegram_webhook(webhook_url):
        log("Setup failed at webhook registration", "ERROR")
        return
    print()

    # Step 5: Verify webhook
    log("Step 5: Verifying webhook registration...", "STEP")
    verify_telegram_webhook()
    print()

    # Step 6: Test instructions
    log("Step 6: Testing instructions...", "STEP")
    test_bot()
    print()

    print("=" * 60)
    log("Setup completed successfully!", "SUCCESS")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Configure Google Gemini API credential in n8n UI")
    print("2. Open http://72.60.175.144:5678/workflow/7LMKcMmldZsu1l6g")
    print("3. Click 'Gemini Vision Analysis' node")
    print("4. Select credential 'Google Gemini(PaLM) Api account 3' or create new")
    print("5. Save workflow")
    print("6. Test by sending photo to bot")

if __name__ == "__main__":
    main()
