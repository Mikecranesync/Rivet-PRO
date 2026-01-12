"""
Fix the Insert to Cache SQL column names
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
WORKFLOW_ID = 'HQgppQgX9H2yyQdN'
BASE_URL = 'https://mikecranesync.app.n8n.cloud/api/v1/workflows'

print("="*80)
print("FIXING INSERT TO CACHE SQL COLUMN NAMES")
print("="*80)

# Load the integrated workflow
with open('manual_hunter_integrated.json', 'r', encoding='utf-8') as f:
    workflow = json.load(f)

print("\n[1/3] Finding Insert to Cache node...")

insert_node = None
for node in workflow['nodes']:
    if node.get('name') == 'Insert to Cache':
        insert_node = node
        break

if not insert_node:
    print("[ERROR] Insert to Cache node not found")
    exit(1)

print("       [OK] Found node")

# Fix the SQL query
corrected_sql = """INSERT INTO manual_hunter_cache (
  manufacturer,
  model_number,
  product_family,
  pdf_url,
  confidence_score,
  search_tier,
  validation_score,
  validation_content_type,
  search_count,
  created_at,
  last_accessed
) VALUES (
  '{{ $('Extract Webhook Data').item.json.manufacturer }}',
  '{{ $('Extract Webhook Data').item.json.model_number }}',
  '{{ $('Extract Webhook Data').item.json.product_family }}',
  '{{ $json.pdf_url }}',
  {{ $json.confidence }},
  '{{ $json.tier }}',
  {{ $json.validation.score }},
  '{{ $json.validation.content_type }}',
  1,
  NOW(),
  NOW()
)
ON CONFLICT (manufacturer, model_number)
DO UPDATE SET
  pdf_url = EXCLUDED.pdf_url,
  confidence_score = EXCLUDED.confidence_score,
  validation_score = EXCLUDED.validation_score,
  validation_content_type = EXCLUDED.validation_content_type,
  last_accessed = NOW()
RETURNING *;"""

print("\n[2/3] Updating SQL query...")
insert_node['parameters']['query'] = corrected_sql
print("       [OK] Query updated with correct column names:")
print("          - confidence -> confidence_score")
print("          - tier -> search_tier")

# Save locally
with open('manual_hunter_fixed_sql.json', 'w', encoding='utf-8') as f:
    json.dump(workflow, f, indent=2)

print(f"\n       Saved to: manual_hunter_fixed_sql.json")

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
    print("SQL FIX APPLIED")
    print("="*80)
    print("\nThe Insert to Cache node now uses correct column names.")
    print("Ready to test again!")

else:
    print(f"       [ERROR] Failed to update: {response.status_code}")
    print(f"Response: {response.text}")
