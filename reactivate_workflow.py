import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
WORKFLOW_ID = 'YhW8Up8oM2eHXicx'
API_URL = f'https://mikecranesync.app.n8n.cloud/api/v1/workflows/{WORKFLOW_ID}'

headers = {
    'X-N8N-API-KEY': API_KEY,
    'Content-Type': 'application/json'
}

print("Deactivating workflow...")
response = requests.patch(API_URL, headers=headers, json={'active': False})
if response.status_code == 200:
    print("[OK] Workflow deactivated")
else:
    print(f"[ERROR] Failed to deactivate: {response.status_code}")
    print(response.text)
    exit(1)

import time
print("Waiting 2 seconds...")
time.sleep(2)

print("Activating workflow...")
response = requests.patch(API_URL, headers=headers, json={'active': True})
if response.status_code == 200:
    print("[OK] Workflow activated")
    print("\nWorkflow is now active and ready to test!")
else:
    print(f"[ERROR] Failed to activate: {response.status_code}")
    print(response.text)
