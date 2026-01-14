import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
API_URL = 'https://mikecranesync.app.n8n.cloud/api/v1/workflows'

print("="*80)
print("DEPLOYING RIVET URL VALIDATOR TO PRODUCTION")
print("="*80)

# Read the production workflow
workflow_file = 'n8n/workflows/prod/rivet_url_validator_production.json'
print(f"\nReading production workflow from: {workflow_file}")

with open(workflow_file, 'r', encoding='utf-8') as f:
    workflow_data = json.load(f)

print(f"[OK] Loaded workflow: {workflow_data.get('name')}")
print(f"[OK] Nodes count: {len(workflow_data.get('nodes', []))}")

# Find webhook path
webhook_path = None
for node in workflow_data.get('nodes', []):
    if node.get('type') == 'n8n-nodes-base.webhook':
        webhook_path = node.get('parameters', {}).get('path')
        break

print(f"[OK] Webhook path: {webhook_path}")

# Prepare payload - only include allowed fields for API
payload = {
    'name': workflow_data.get('name'),
    'nodes': workflow_data.get('nodes'),
    'connections': workflow_data.get('connections'),
    'settings': workflow_data.get('settings'),
    'staticData': workflow_data.get('staticData'),
}

# Create new workflow via API (POST, not PUT)
headers = {
    'X-N8N-API-KEY': API_KEY,
    'Content-Type': 'application/json'
}

print("\n" + "="*80)
print("UPLOADING TO N8N CLOUD (Creating New Workflow)")
print("="*80)

response = requests.post(API_URL, headers=headers, json=payload)

if response.status_code == 200 or response.status_code == 201:
    print("[SUCCESS] Production workflow created successfully!")
    result = response.json()

    workflow_id = result.get('id')

    print(f"\nProduction Workflow Details:")
    print(f"  Name: {result.get('name')}")
    print(f"  ID: {workflow_id}")
    print(f"  Active: {result.get('active')}")
    print(f"  Nodes: {len(result.get('nodes', []))}")

    # Save production deployment info
    deployment_info = {
        "workflow_id": workflow_id,
        "workflow_name": result.get('name'),
        "webhook_url": f"https://mikecranesync.app.n8n.cloud/webhook/{webhook_path}",
        "deployed_at": result.get('createdAt'),
        "active": result.get('active'),
        "nodes": len(result.get('nodes', []))
    }

    with open('production_deployment.json', 'w', encoding='utf-8') as f:
        json.dump(deployment_info, f, indent=2)

    print(f"\n" + "="*80)
    print("PRODUCTION DEPLOYMENT SUCCESSFUL")
    print("="*80)
    print(f"Workflow ID: {workflow_id}")
    print(f"Webhook URL: {deployment_info['webhook_url']}")
    print(f"Status: {'Active' if result.get('active') else 'Inactive'}")
    print(f"\nDeployment info saved to: production_deployment.json")

    # Activate the workflow if not already active
    if not result.get('active'):
        print("\n[INFO] Workflow is not active. To activate, use n8n UI.")

else:
    print(f"[ERROR] Failed to create workflow: {response.status_code}")
    print(f"Response: {response.text}")
    exit(1)

print("\n" + "="*80)
print("NEXT STEPS:")
print("="*80)
print("1. Activate the workflow in n8n cloud UI (if not already active)")
print("2. Test the production webhook endpoint")
print("3. Update client applications to use production URL")
print("="*80)
