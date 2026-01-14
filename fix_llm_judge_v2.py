"""
Fix LLM Judge workflow - Use correct Gemini 2.5 Flash model
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
WORKFLOW_ID = 'QaFV6k14mQroMfat'
BASE_URL = 'https://mikecranesync.app.n8n.cloud/api/v1/workflows'

print("="*80)
print("FIXING LLM JUDGE WORKFLOW - GEMINI 2.5 FLASH")
print("="*80)

# Load current workflow
response = requests.get(f'{BASE_URL}/{WORKFLOW_ID}', headers={'X-N8N-API-KEY': API_KEY})
workflow = response.json()

print(f"\n[1/3] Loaded workflow: {workflow.get('name')}")
print(f"       Current nodes: {len(workflow['nodes'])}")

# Find and fix the LLM Analysis node
print("\n[2/3] Fixing LLM Analysis (Gemini) node...")

for node in workflow['nodes']:
    if node.get('name') == 'LLM Analysis (Gemini)':
        print(f"       Found node: {node.get('name')}")

        # Update to correct endpoint with Gemini 2.5 Flash
        old_url = node['parameters']['url']
        print(f"       Old URL: {old_url}")

        # Use v1 API with gemini-2.5-flash (latest model)
        node['parameters']['url'] = "=https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={{ $env.GOOGLE_API_KEY }}"

        print(f"       New URL: {node['parameters']['url']}")
        print("       [OK] Updated to Gemini 2.5 Flash")
        break

# Save locally
with open('llm_judge_fixed_v2.json', 'w', encoding='utf-8') as f:
    json.dump(workflow, f, indent=2)

print(f"\n       Saved to: llm_judge_fixed_v2.json")

# Upload to n8n
print("\n[3/3] Uploading to n8n cloud...")

headers = {
    'X-N8N-API-KEY': API_KEY,
    'Content-Type': 'application/json'
}

# Filter settings
allowed_settings = ['executionOrder', 'callerPolicy']
settings = workflow.get('settings', {})
filtered_settings = {k: v for k, v in settings.items() if k in allowed_settings}

payload = {
    'name': workflow.get('name'),
    'nodes': workflow.get('nodes'),
    'connections': workflow.get('connections'),
    'settings': filtered_settings,
    'staticData': workflow.get('staticData'),
}

response = requests.put(f"{BASE_URL}/{WORKFLOW_ID}", headers=headers, json=payload)

if response.status_code == 200:
    print("       [OK] Workflow updated successfully!")

    result = response.json()
    print(f"\nWorkflow: {result.get('name')}")
    print(f"Nodes: {len(result.get('nodes'))}")
    print(f"Active: {result.get('active')}")

    print("\n" + "="*80)
    print("FIX APPLIED")
    print("="*80)
    print("\nWhat was fixed:")
    print("  - Updated to Gemini 2.5 Flash (latest model)")
    print("  - Using v1 API endpoint")
    print("  - Model: gemini-2.5-flash")
    print("\nReady to test!")

else:
    print(f"       [ERROR] Failed to update: {response.status_code}")
    print(f"Response: {response.text}")
