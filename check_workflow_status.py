import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
WORKFLOW_ID = 'YhW8Up8oM2eHXicx'
API_URL = f'https://mikecranesync.app.n8n.cloud/api/v1/workflows/{WORKFLOW_ID}'

headers = {
    'X-N8N-API-KEY': API_KEY,
    'Content-Type': 'application/json'
}

print("Fetching workflow status...")
response = requests.get(API_URL, headers=headers)

if response.status_code == 200:
    workflow = response.json()
    print(f"\nWorkflow: {workflow.get('name')}")
    print(f"ID: {workflow.get('id')}")
    print(f"Active: {workflow.get('active')}")
    print(f"Nodes: {len(workflow.get('nodes', []))}")
    print(f"Created: {workflow.get('createdAt')}")
    print(f"Updated: {workflow.get('updatedAt')}")

    # Check if workflow needs to be activated
    if not workflow.get('active'):
        print("\n[WARNING] Workflow is NOT active!")
        print("Activating workflow...")

        # Activate the workflow
        activate_response = requests.patch(
            API_URL,
            headers=headers,
            json={'active': True}
        )

        if activate_response.status_code == 200:
            print("[SUCCESS] Workflow activated!")
        else:
            print(f"[ERROR] Failed to activate: {activate_response.status_code}")
            print(activate_response.text)
    else:
        print("\n[OK] Workflow is active")
else:
    print(f"[ERROR] Failed to get workflow: {response.status_code}")
    print(response.text)
