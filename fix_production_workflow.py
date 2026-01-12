import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
BASE_URL = 'https://mikecranesync.app.n8n.cloud/api/v1/workflows'

headers = {
    'X-N8N-API-KEY': API_KEY,
    'Content-Type': 'application/json'
}

# Load current test workflow (which is working)
test_id = 'YhW8Up8oM2eHXicx'
test_response = requests.get(f"{BASE_URL}/{test_id}", headers=headers)
test_workflow = test_response.json()

# Load production workflow
with open('production_deployment.json', 'r') as f:
    prod_id = json.load(f)['workflow_id']

prod_response = requests.get(f"{BASE_URL}/{prod_id}", headers=headers)
prod_workflow = prod_response.json()

print("Fixing production workflow HTTP node configuration...")
print(f"Production ID: {prod_id}")

# Find and copy HTTP node config from test to prod
for test_node in test_workflow.get('nodes', []):
    if 'HTTP HEAD' in test_node.get('name', ''):
        # Find corresponding node in prod
        for prod_node in prod_workflow.get('nodes', []):
            if 'HTTP HEAD' in prod_node.get('name', ''):
                print(f"\nCopying configuration from test to production:")
                print(f"  continueOnFail: {test_node.get('continueOnFail')}")
                print(f"  Parameters: Full HTTP config with headers and options")

                # Copy the working configuration
                prod_node['continueOnFail'] = test_node.get('continueOnFail')
                prod_node['parameters'] = test_node.get('parameters').copy()

                # Keep the production webhook path
                break
        break

# Update production workflow
payload = {
    'name': prod_workflow.get('name'),
    'nodes': prod_workflow.get('nodes'),
    'connections': prod_workflow.get('connections'),
    'settings': prod_workflow.get('settings'),
    'staticData': prod_workflow.get('staticData'),
}

print(f"\nUpdating production workflow...")
response = requests.put(f"{BASE_URL}/{prod_id}", headers=headers, json=payload)

if response.status_code == 200:
    print("[SUCCESS] Production workflow updated!")
    result = response.json()
    print(f"  Name: {result.get('name')}")
    print(f"  ID: {result.get('id')}")
    print(f"  Active: {result.get('active')}")
else:
    print(f"[ERROR] Failed to update: {response.status_code}")
    print(response.text)
    exit(1)

print("\nProduction workflow now has the same HTTP configuration as test workflow.")
print("Ready to test!")
