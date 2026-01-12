import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
WORKFLOW_ID = 'YhW8Up8oM2eHXicx'
API_URL = f'https://mikecranesync.app.n8n.cloud/api/v1/workflows/{WORKFLOW_ID}'

headers = {
    'X-N8N-API-KEY': API_KEY
}

# Get cloud workflow
print("Fetching cloud workflow...")
response = requests.get(API_URL, headers=headers)
cloud_workflow = response.json()

# Load local workflow
print("Loading local workflow...")
with open('n8n/workflows/test/rivet_url_validator.json', 'r', encoding='utf-8') as f:
    local_workflow = json.load(f)

# Compare
print("\n" + "="*60)
print("COMPARISON")
print("="*60)

print(f"\nLocal nodes: {len(local_workflow.get('nodes', []))}")
print(f"Cloud nodes: {len(cloud_workflow.get('nodes', []))}")

# Check Extract Request Data node
local_extract = None
cloud_extract = None

for node in local_workflow.get('nodes', []):
    if node.get('name') == 'Extract Request Data':
        local_extract = node
        break

for node in cloud_workflow.get('nodes', []):
    if node.get('name') == 'Extract Request Data':
        cloud_extract = node
        break

if local_extract and cloud_extract:
    print("\n[Extract Request Data Node]")
    local_code = local_extract.get('parameters', {}).get('jsCode', '')[:100]
    cloud_code = cloud_extract.get('parameters', {}).get('jsCode', '')[:100]

    print(f"Local code preview: {local_code}...")
    print(f"Cloud code preview: {cloud_code}...")

    if local_code == cloud_code:
        print("[OK] Code matches!")
    else:
        print("[MISMATCH] Code is different!")

# Check webhook configuration
for node in cloud_workflow.get('nodes', []):
    if node.get('type') == 'n8n-nodes-base.webhook':
        print(f"\n[Webhook Node]")
        print(f"  Response Mode: {node.get('parameters', {}).get('responseMode')}")
        print(f"  Path: {node.get('parameters', {}).get('path')}")

# Save cloud workflow for inspection
with open('cloud_workflow_current.json', 'w', encoding='utf-8') as f:
    json.dump(cloud_workflow, f, indent=2)

print("\n[SAVED] Cloud workflow saved to: cloud_workflow_current.json")
