import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
WORKFLOW_ID = 'YhW8Up8oM2eHXicx'
API_URL = f'https://mikecranesync.app.n8n.cloud/api/v1/workflows/{WORKFLOW_ID}'

print("Fixing RIVET URL Validator workflow...")
print(f"Workflow ID: {WORKFLOW_ID}")
print(f"API URL: {API_URL}")

# Read the corrected workflow from local file
workflow_file = 'n8n/workflows/test/rivet_url_validator_simplified.json'
print(f"\nReading simplified workflow from: {workflow_file}")

with open(workflow_file, 'r', encoding='utf-8') as f:
    workflow_data = json.load(f)

print(f"[OK] Loaded workflow: {workflow_data.get('name', 'Unknown')}")
print(f"[OK] Nodes count: {len(workflow_data.get('nodes', []))}")

# Prepare payload - only include allowed fields for API
payload = {
    'name': workflow_data.get('name'),
    'nodes': workflow_data.get('nodes'),
    'connections': workflow_data.get('connections'),
    'settings': workflow_data.get('settings'),
    'staticData': workflow_data.get('staticData'),
}

# Update workflow via API
headers = {
    'X-N8N-API-KEY': API_KEY,
    'Content-Type': 'application/json'
}

print("\nSending update to n8n cloud...")
response = requests.put(API_URL, headers=headers, json=payload)

if response.status_code == 200:
    print("[SUCCESS] Workflow updated successfully!")
    result = response.json()
    print(f"\nWorkflow Details:")
    print(f"  Name: {result.get('name', 'N/A')}")
    print(f"  ID: {result.get('id', 'N/A')}")
    print(f"  Active: {result.get('active', False)}")
    print(f"  Nodes: {len(result.get('nodes', []))}")
else:
    print(f"[ERROR] Failed to update workflow: {response.status_code}")
    print(f"Response: {response.text}")
    exit(1)

print("\n" + "="*60)
print("NEXT STEP: Test the workflow with:")
print("="*60)
print('curl -X POST https://mikecranesync.app.n8n.cloud/webhook/rivet-url-validator \\')
print('  -H "Content-Type: application/json" \\')
print('  -d \'{"url":"https://www.google.com"}\'')
print("="*60)
