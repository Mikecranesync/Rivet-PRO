"""
Fix LLM Judge - Increase maxOutputTokens to prevent truncation
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
print("FIXING MAX OUTPUT TOKENS")
print("="*80)

# Load current workflow
response = requests.get(f'{BASE_URL}/{WORKFLOW_ID}', headers={'X-N8N-API-KEY': API_KEY})
workflow = response.json()

print(f"\n[1/2] Loaded workflow: {workflow.get('name')}")

# Find and fix the Prepare LLM Prompt node
print("\n[2/2] Fixing Prepare LLM Prompt node...")

for node in workflow['nodes']:
    if node.get('name') == 'Prepare LLM Prompt':
        print(f"       Found node: {node.get('name')}")

        # Get current code
        current_code = node['parameters']['jsCode']

        # Replace maxOutputTokens: 800 with maxOutputTokens: 2000
        updated_code = current_code.replace(
            '"maxOutputTokens": 800',
            '"maxOutputTokens": 2000'
        )

        node['parameters']['jsCode'] = updated_code
        print("       [OK] Increased maxOutputTokens from 800 to 2000")
        print("       (Allows for Gemini 2.5's thinking tokens + full response)")
        break

# Upload to n8n
print("\nUploading to n8n cloud...")

headers = {
    'X-N8N-API-KEY': API_KEY,
    'Content-Type': 'application/json'
}

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
    print("[OK] Workflow updated successfully!")

    print("\n" + "="*80)
    print("ALL FIXES APPLIED")
    print("="*80)
    print("\nSummary of fixes:")
    print("  1. Updated to Gemini 2.5 Flash model")
    print("  2. Fixed parser to strip markdown code fences")
    print("  3. Increased maxOutputTokens to 2000")
    print("\nReady to test!")

else:
    print(f"[ERROR] Failed to update: {response.status_code}")
    print(f"Response: {response.text}")
