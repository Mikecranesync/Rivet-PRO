import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
API_URL = 'https://mikecranesync.app.n8n.cloud/api/v1/workflows'

headers = {
    'X-N8N-API-KEY': API_KEY
}

output = []
output.append("Fetching workflows list...")
response = requests.get(API_URL, headers=headers)
output.append(f"Status: {response.status_code}")

if response.status_code == 200:
    response_data = response.json()
    workflows = response_data.get('data', [])
    output.append(f"Total workflows: {len(workflows)}")

    for wf in workflows:
        wf_id = wf.get('id')
        output.append(f"\nWorkflow ID: {wf_id}")
        wf_response = requests.get(f"{API_URL}/{wf_id}", headers=headers)

        if wf_response.status_code == 200:
            wf = wf_response.json()
            output.append(f"  Name: {wf.get('name')}")
            output.append(f"  Active: {wf.get('active')}")
            output.append(f"  Nodes: {len(wf.get('nodes', []))}")

            # Check for webhooks
            for node in wf.get('nodes', []):
                if 'webhook' in node.get('type', '').lower():
                    output.append(f"  Webhook found:")
                    output.append(f"    Path: {node.get('parameters', {}).get('path')}")
                    output.append(f"    Response Mode: {node.get('parameters', {}).get('responseMode')}")
        else:
            output.append(f"  ERROR: {wf_response.status_code}")

# Write to file
with open('workflows_debug.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print("Output saved to: workflows_debug.txt")
