import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
API_URL = 'https://mikecranesync.app.n8n.cloud/api/v1/workflows'

headers = {
    'X-N8N-API-KEY': API_KEY
}

print("=" * 80)
print("N8N WORKFLOW STATUS REPORT")
print("=" * 80)
print()

try:
    # Get all workflows
    response = requests.get(API_URL, headers=headers)
    if response.status_code != 200:
        print(f"[ERROR] Failed to fetch workflows: {response.status_code}")
        print(response.text)
        exit(1)

    workflows_data = response.json()
    workflows = workflows_data.get('data', [])
    print(f"Total workflows in n8n: {len(workflows)}")
    print()

    active_count = 0
    inactive_count = 0

    # Process each workflow
    for wf in workflows:
        name = wf.get('name', 'Unnamed')
        active = wf.get('active', False)
        nodes = wf.get('nodes', [])
        created = wf.get('createdAt', 'Unknown')
        updated = wf.get('updatedAt', 'Unknown')

        if active:
            active_count += 1
            status_icon = "[ACTIVE]"
        else:
            inactive_count += 1
            status_icon = "[INACTIVE]"

        wf_id = wf.get('id', 'Unknown')

        print(f"{status_icon}")
        print(f"  Name: {name}")
        print(f"  ID: {wf_id}")
        print(f"  Nodes: {len(nodes)}")
        print(f"  Created: {created}")
        print(f"  Updated: {updated}")

        # Check for webhooks
        webhooks = [n for n in nodes if n.get('type') == 'n8n-nodes-base.webhook']
        if webhooks:
            print(f"  Webhooks: {len(webhooks)}")
            for wh in webhooks:
                path = wh.get('parameters', {}).get('path', 'N/A')
                print(f"    - /{path}")

        # Check for Telegram triggers
        telegram_nodes = [n for n in nodes if 'telegram' in n.get('type', '').lower()]
        if telegram_nodes:
            print(f"  Telegram nodes: {len(telegram_nodes)}")

        print()

    print("=" * 80)
    print(f"SUMMARY: {active_count} active, {inactive_count} inactive")
    print("=" * 80)

except Exception as e:
    print(f"[ERROR] {type(e).__name__}: {e}")
