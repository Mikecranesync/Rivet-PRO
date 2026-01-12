import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
BASE_URL = 'https://mikecranesync.app.n8n.cloud/api/v1/workflows'

headers = {'X-N8N-API-KEY': API_KEY}

# Get test workflow
test_id = 'YhW8Up8oM2eHXicx'
test_response = requests.get(f"{BASE_URL}/{test_id}", headers=headers)
test_workflow = test_response.json()

# Get production workflow
with open('production_deployment.json', 'r') as f:
    prod_id = json.load(f)['workflow_id']

prod_response = requests.get(f"{BASE_URL}/{prod_id}", headers=headers)
prod_workflow = prod_response.json()

print("="*80)
print("COMPARING TEST vs PRODUCTION WORKFLOWS")
print("="*80)
print(f"\nTest Workflow ID: {test_id}")
print(f"Prod Workflow ID: {prod_id}")
print()

# Compare HTTP Request node
def find_http_node(workflow):
    for node in workflow.get('nodes', []):
        if 'HTTP HEAD' in node.get('name', ''):
            return node
    return None

test_http = find_http_node(test_workflow)
prod_http = find_http_node(prod_workflow)

if test_http and prod_http:
    print("HTTP HEAD Check Node Comparison:")
    print("-"*80)
    print(f"Test HTTP Node:")
    print(f"  continueOnFail: {test_http.get('continueOnFail')}")
    print(f"  Parameters: {json.dumps(test_http.get('parameters'), indent=4)}")
    print()
    print(f"Production HTTP Node:")
    print(f"  continueOnFail: {prod_http.get('continueOnFail')}")
    print(f"  Parameters: {json.dumps(prod_http.get('parameters'), indent=4)}")
    print()

    if test_http.get('continueOnFail') != prod_http.get('continueOnFail'):
        print("[DIFFERENCE] continueOnFail mismatch!")
        print(f"  Test: {test_http.get('continueOnFail')}")
        print(f"  Prod: {prod_http.get('continueOnFail')}")

# Save full workflows for inspection
with open('test_workflow_current.json', 'w', encoding='utf-8') as f:
    json.dump(test_workflow, f, indent=2)

with open('prod_workflow_current.json', 'w', encoding='utf-8') as f:
    json.dump(prod_workflow, f, indent=2)

print("\nFull workflows saved:")
print("  test_workflow_current.json")
print("  prod_workflow_current.json")
