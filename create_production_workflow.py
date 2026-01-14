import json
from datetime import datetime

# Load the current working workflow (simplified version)
with open('n8n/workflows/test/rivet_url_validator_simplified.json', 'r', encoding='utf-8') as f:
    workflow = json.load(f)

# Update for production
workflow['name'] = 'RIVET URL Validator - PRODUCTION'

# Update webhook path to production endpoint
for node in workflow['nodes']:
    if node.get('type') == 'n8n-nodes-base.webhook':
        # Change from test path to production path
        node['parameters']['path'] = 'rivet-url-validator-prod'
        print(f"Updated webhook path to: {node['parameters']['path']}")

# Add production metadata
workflow['tags'] = []  # Remove to avoid read-only issues
workflow['updatedAt'] = datetime.now().isoformat()
workflow['versionId'] = '1.0-production'

# Remove test-specific fields that might cause issues
if 'pinData' in workflow:
    workflow['pinData'] = {}
if 'staticData' in workflow:
    workflow['staticData'] = None
if 'triggerCount' in workflow:
    del workflow['triggerCount']

# Save production version
output_file = 'n8n/workflows/prod/rivet_url_validator_production.json'

# Create prod directory if it doesn't exist
import os
os.makedirs('n8n/workflows/prod', exist_ok=True)

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(workflow, f, indent=2)

print(f"\nProduction workflow created:")
print(f"  Name: {workflow['name']}")
print(f"  File: {output_file}")
print(f"  Nodes: {len(workflow['nodes'])}")
print(f"  Version: {workflow['versionId']}")
print(f"\nWebhook endpoint will be:")
print(f"  https://mikecranesync.app.n8n.cloud/webhook/rivet-url-validator-prod")
