import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
WORKFLOW_ID = 'HQgppQgX9H2yyQdN'  # TEST - RIVET - Manual Hunter
API_URL = f'https://mikecranesync.app.n8n.cloud/api/v1/workflows/{WORKFLOW_ID}'

headers = {'X-N8N-API-KEY': API_KEY}

print(f"Fetching Manual Hunter workflow...")
print(f"ID: {WORKFLOW_ID}")

response = requests.get(API_URL, headers=headers)

if response.status_code == 200:
    workflow = response.json()

    # Save full workflow
    with open('manual_hunter_current.json', 'w', encoding='utf-8') as f:
        json.dump(workflow, f, indent=2)

    print(f"\n[SUCCESS] Workflow fetched")
    print(f"  Name: {workflow.get('name')}")
    print(f"  Active: {workflow.get('active')}")
    print(f"  Nodes: {len(workflow.get('nodes', []))}")

    print(f"\nNode Structure:")
    print("-" * 80)
    for node in workflow.get('nodes', []):
        node_type = node.get('type', 'unknown').split('.')[-1]
        print(f"  [{node_type}] {node.get('name')}")

    # Find webhook node
    for node in workflow.get('nodes', []):
        if node.get('type') == 'n8n-nodes-base.webhook':
            print(f"\nWebhook Configuration:")
            print(f"  Path: {node.get('parameters', {}).get('path')}")
            print(f"  Method: {node.get('parameters', {}).get('httpMethod', 'POST')}")
            print(f"  Response Mode: {node.get('parameters', {}).get('responseMode')}")

    print(f"\nFull workflow saved to: manual_hunter_current.json")

else:
    print(f"[ERROR] Failed to fetch: {response.status_code}")
    print(response.text)
