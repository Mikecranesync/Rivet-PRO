import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
# Echo webhook ID from the debug output
WORKFLOW_ID = 'DUuWTD4FLTGnqeyD'  # TEST - RIVET - Echo Webhook (Active)
API_URL = f'https://mikecranesync.app.n8n.cloud/api/v1/workflows/{WORKFLOW_ID}'

headers = {
    'X-N8N-API-KEY': API_KEY
}

print("Fetching Echo webhook workflow...")
response = requests.get(API_URL, headers=headers)

if response.status_code == 200:
    workflow = response.json()

    # Save for inspection
    with open('echo_workflow.json', 'w', encoding='utf-8') as f:
        json.dump(workflow, f, indent=2)

    print(f"Workflow: {workflow.get('name')}")
    print(f"Nodes: {len(workflow.get('nodes', []))}")

    # Find Code nodes
    for node in workflow.get('nodes', []):
        if node.get('type') == 'n8n-nodes-base.code':
            print(f"\nCode Node: {node.get('name')}")
            print(f"TypeVersion: {node.get('typeVersion')}")
            code = node.get('parameters', {}).get('jsCode', '')
            print(f"Code:\n{code[:500]}")

    print("\n[SAVED] Full workflow saved to: echo_workflow.json")
else:
    print(f"[ERROR] {response.status_code}")
    print(response.text)
