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

headers = {
    'X-N8N-API-KEY': API_KEY,
    'Content-Type': 'application/json'
}

# Try different activation approaches
print("Attempting to activate workflow via API...")
print(f"Workflow ID: {workflow_id}")
print()

# Approach 1: POST to activate endpoint
print("Trying: POST /workflows/{id}/activate")
response = requests.post(
    f'https://mikecranesync.app.n8n.cloud/api/v1/workflows/{workflow_id}/activate',
    headers=headers
)
print(f"  Status: {response.status_code}")
if response.status_code == 200:
    print("  [SUCCESS] Workflow activated!")
    result = response.json()
    print(f"  Active: {result.get('active')}")

    # Update deployment info
    deployment['active'] = True
    with open('production_deployment.json', 'w') as f:
        json.dump(deployment, f, indent=2)

    print(f"\nProduction webhook is now live:")
    print(f"  {deployment['webhook_url']}")
else:
    print(f"  Response: {response.text[:200]}")
    print("\n[INFO] API activation not available.")
    print("[INFO] Please activate manually via n8n UI.")
