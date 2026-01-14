"""
Verify Manual Hunter workflow configuration
"""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
WORKFLOW_ID = 'HQgppQgX9H2yyQdN'
BASE_URL = 'https://mikecranesync.app.n8n.cloud/api/v1'

headers = {'X-N8N-API-KEY': API_KEY}

print("="*80)
print("VERIFYING MANUAL HUNTER CONFIGURATION")
print("="*80)

response = requests.get(f'{BASE_URL}/workflows/{WORKFLOW_ID}', headers=headers)

if response.status_code == 200:
    workflow = response.json()

    print(f"\nWorkflow: {workflow.get('name')}")
    print(f"ID: {workflow.get('id')}")
    print(f"Active: {workflow.get('active')}")
    print(f"Nodes: {len(workflow.get('nodes', []))}")

    # Find webhook node
    webhook_node = None
    for node in workflow.get('nodes', []):
        if node.get('type') == 'n8n-nodes-base.webhook':
            webhook_node = node
            break

    if webhook_node:
        print(f"\nWebhook Configuration:")
        params = webhook_node.get('parameters', {})
        print(f"  Path: {params.get('path')}")
        print(f"  Method: {params.get('httpMethod', 'POST')}")
        print(f"  Response Mode: {params.get('responseMode')}")
        print(f"  Response Data: {params.get('responseData')}")

        # Build full webhook URL
        path = params.get('path', '')
        webhook_url = f"https://mikecranesync.app.n8n.cloud/webhook/{path}"
        print(f"\n  Full URL: {webhook_url}")

    # List all nodes to verify integration
    print(f"\nAll Nodes ({len(workflow.get('nodes', []))}):")
    for node in workflow.get('nodes', []):
        node_type = node.get('type', '').split('.')[-1]
        print(f"  [{node_type:15}] {node.get('name')}")

    # Check for validation nodes
    validation_nodes = [n for n in workflow.get('nodes', [])
                       if 'Validate' in n.get('name', '') or 'Valid?' in n.get('name', '')]

    print(f"\nValidation Nodes Found: {len(validation_nodes)}")
    for vnode in validation_nodes:
        print(f"  - {vnode.get('name')}")

    # Check connections for one of the new nodes
    connections = workflow.get('connections', {})
    if 'Tier 1 Success?' in connections:
        tier1_success_conn = connections['Tier 1 Success?']
        print(f"\n'Tier 1 Success?' connections:")
        print(f"  TRUE branch: {tier1_success_conn.get('main', [[]])[0]}")

    # Save workflow for inspection
    with open('manual_hunter_current_config.json', 'w') as f:
        json.dump(workflow, f, indent=2)

    print(f"\nFull config saved to: manual_hunter_current_config.json")

else:
    print(f"[ERROR] Failed to fetch workflow: {response.status_code}")
    print(response.text)
