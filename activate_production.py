import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')

# Read deployment info
with open('production_deployment.json', 'r') as f:
    deployment = json.load(f)

workflow_id = deployment['workflow_id']
API_URL = f'https://mikecranesync.app.n8n.cloud/api/v1/workflows/{workflow_id}'

print(f"Activating production workflow: {workflow_id}")

# Update workflow to set active = true
headers = {
    'X-N8N-API-KEY': API_KEY,
    'Content-Type': 'application/json'
}

# Get current workflow
get_response = requests.get(API_URL, headers=headers)
if get_response.status_code != 200:
    print(f"[ERROR] Failed to get workflow: {get_response.status_code}")
    exit(1)

current_workflow = get_response.json()

# Update with active = true
payload = {
    'name': current_workflow.get('name'),
    'nodes': current_workflow.get('nodes'),
    'connections': current_workflow.get('connections'),
    'settings': current_workflow.get('settings'),
    'staticData': current_workflow.get('staticData'),
    'active': True  # Activate it
}

response = requests.put(API_URL, headers=headers, json=payload)

if response.status_code == 200:
    result = response.json()
    print(f"[SUCCESS] Workflow activated!")
    print(f"  Name: {result.get('name')}")
    print(f"  ID: {result.get('id')}")
    print(f"  Active: {result.get('active')}")

    # Update deployment info
    deployment['active'] = True
    with open('production_deployment.json', 'w') as f:
        json.dump(deployment, f, indent=2)

    print(f"\nProduction webhook is now live:")
    print(f"  {deployment['webhook_url']}")
else:
    print(f"[ERROR] Failed to activate: {response.status_code}")
    print(response.text)
