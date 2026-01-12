import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
API_URL = 'https://mikecranesync.app.n8n.cloud/api/v1/workflows'

headers = {
    'X-N8N-API-KEY': API_KEY
}

print("Fetching all workflows...")
response = requests.get(API_URL, headers=headers)

if response.status_code == 200:
    workflow_ids = response.json()
    print(f"\nTotal workflows: {len(workflow_ids)}")
    print("\n" + "="*80)

    for wf_id in workflow_ids:
        # Fetch individual workflow details
        wf_response = requests.get(f"{API_URL}/{wf_id}", headers=headers)
        if wf_response.status_code != 200:
            continue

        wf = wf_response.json()
        name = wf.get('name')
        active = wf.get('active')
        nodes = wf.get('nodes', [])

        # Check for webhook nodes
        webhook_paths = []
        for node in nodes:
            if node.get('type') == 'n8n-nodes-base.webhook':
                path = node.get('parameters', {}).get('path', '')
                response_mode = node.get('parameters', {}).get('responseMode', 'onReceived')
                webhook_paths.append(f"{path} ({response_mode})")

        if webhook_paths:
            status = "[ACTIVE]" if active else "[INACTIVE]"
            print(f"{status} {name}")
            print(f"  ID: {wf_id}")
            print(f"  Webhooks: {', '.join(webhook_paths)}")
            print()
else:
    print(f"[ERROR] Failed to fetch workflows: {response.status_code}")
    print(response.text)
