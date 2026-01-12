"""
Wire Manual Hunter to Production URL Validator
This script modifies the Manual Hunter workflow to add URL validation
"""
import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
WORKFLOW_ID = 'HQgppQgX9H2yyQdN'
BASE_URL = 'https://mikecranesync.app.n8n.cloud/api/v1/workflows'

print("="*80)
print("WIRING MANUAL HUNTER TO URL VALIDATOR")
print("="*80)

# Load current workflow
with open('manual_hunter_current.json', 'r', encoding='utf-8') as f:
    workflow = json.load(f)

print(f"\n[1/7] Loaded workflow: {workflow.get('name')}")
print(f"       Current nodes: {len(workflow['nodes'])}")

# Step 1: Add Tier 1 Validation Nodes
tier1_validate = {
    "parameters": {
        "method": "POST",
        "url": "https://mikecranesync.app.n8n.cloud/webhook/rivet-url-validator-prod",
        "sendBody": True,
        "bodyParameters": {
            "parameters": [
                {
                    "name": "url",
                    "value": "={{ $json.pdf_url }}"
                }
            ]
        },
        "options": {
            "timeout": 30000
        }
    },
    "id": "validate-tier1-url",
    "name": "Validate Tier 1 URL",
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [1340, 400],
    "continueOnFail": True
}

tier1_parse = {
    "parameters": {
        "jsCode": """const validationResult = $input.item.json;
const originalData = $('Parse Tier 1 Result').item.json;

return {
  json: {
    ...originalData,
    validation: {
      valid: validationResult.valid || false,
      score: validationResult.score || 0,
      status_code: validationResult.status_code || 0,
      content_type: validationResult.content_type || '',
      error: validationResult.error || null
    }
  }
};"""
    },
    "id": "parse-tier1-validation",
    "name": "Parse Tier 1 Validation",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [1560, 400]
}

tier1_check = {
    "parameters": {
        "conditions": {
            "options": {
                "caseSensitive": True,
                "leftValue": "",
                "typeValidation": "strict"
            },
            "conditions": [
                {
                    "id": "validation-valid",
                    "leftValue": "={{ $json.validation.valid }}",
                    "rightValue": True,
                    "operator": {
                        "type": "boolean",
                        "operation": "equals"
                    }
                },
                {
                    "id": "validation-score",
                    "leftValue": "={{ $json.validation.score }}",
                    "rightValue": 6,
                    "operator": {
                        "type": "number",
                        "operation": "gte"
                    }
                }
            ],
            "combinator": "and"
        }
    },
    "id": "tier1-url-valid",
    "name": "Tier 1 URL Valid?",
    "type": "n8n-nodes-base.if",
    "typeVersion": 2,
    "position": [1780, 400]
}

print("\n[2/7] Adding Tier 1 validation nodes:")
print("       - Validate Tier 1 URL (HTTP Request)")
print("       - Parse Tier 1 Validation (Code)")
print("       - Tier 1 URL Valid? (IF)")

workflow['nodes'].extend([tier1_validate, tier1_parse, tier1_check])

# Step 2: Add Tier 2 Validation Nodes (same pattern)
tier2_validate = {
    **tier1_validate,
    "id": "validate-tier2-url",
    "name": "Validate Tier 2 URL",
    "position": [1340, 700]
}

tier2_parse = {
    **tier1_parse,
    "parameters": {
        "jsCode": tier1_parse["parameters"]["jsCode"].replace(
            "Parse Tier 1 Result",
            "Parse Tier 2 Result"
        )
    },
    "id": "parse-tier2-validation",
    "name": "Parse Tier 2 Validation",
    "position": [1560, 700]
}

tier2_check = {
    **tier1_check,
    "id": "tier2-url-valid",
    "name": "Tier 2 URL Valid?",
    "position": [1780, 700]
}

print("\n[3/7] Adding Tier 2 validation nodes:")
print("       - Validate Tier 2 URL (HTTP Request)")
print("       - Parse Tier 2 Validation (Code)")
print("       - Tier 2 URL Valid? (IF)")

workflow['nodes'].extend([tier2_validate, tier2_parse, tier2_check])

# Step 3: Update connections
print("\n[4/7] Updating workflow connections...")

# Original: Tier 1 Success? (TRUE) → Insert to Cache
# New: Tier 1 Success? (TRUE) → Validate Tier 1 URL
workflow['connections']['Tier 1 Success?']['main'][0] = [
    {
        "node": "Validate Tier 1 URL",
        "type": "main",
        "index": 0
    }
]

# Add: Validate Tier 1 URL → Parse Tier 1 Validation
workflow['connections']['Validate Tier 1 URL'] = {
    "main": [[{
        "node": "Parse Tier 1 Validation",
        "type": "main",
        "index": 0
    }]]
}

# Add: Parse Tier 1 Validation → Tier 1 URL Valid?
workflow['connections']['Parse Tier 1 Validation'] = {
    "main": [[{
        "node": "Tier 1 URL Valid?",
        "type": "main",
        "index": 0
    }]]
}

# Add: Tier 1 URL Valid?
#   TRUE → Insert to Cache
#   FALSE → Tier 2: Serper Search
workflow['connections']['Tier 1 URL Valid?'] = {
    "main": [
        [{
            "node": "Insert to Cache",
            "type": "main",
            "index": 0
        }],
        [{
            "node": "Tier 2: Serper Search",
            "type": "main",
            "index": 0
        }]
    ]
}

# Original: Tier 2 Success? (TRUE) → Insert to Cache
# New: Tier 2 Success? (TRUE) → Validate Tier 2 URL
workflow['connections']['Tier 2 Success?']['main'][0] = [
    {
        "node": "Validate Tier 2 URL",
        "type": "main",
        "index": 0
    }
]

# Add: Validate Tier 2 URL → Parse Tier 2 Validation
workflow['connections']['Validate Tier 2 URL'] = {
    "main": [[{
        "node": "Parse Tier 2 Validation",
        "type": "main",
        "index": 0
    }]]
}

# Add: Parse Tier 2 Validation → Tier 2 URL Valid?
workflow['connections']['Parse Tier 2 Validation'] = {
    "main": [[{
        "node": "Tier 2 URL Valid?",
        "type": "main",
        "index": 0
    }]]
}

# Add: Tier 2 URL Valid?
#   TRUE → Insert to Cache
#   FALSE → Insert to Human Queue
workflow['connections']['Tier 2 URL Valid?'] = {
    "main": [
        [{
            "node": "Insert to Cache",
            "type": "main",
            "index": 0
        }],
        [{
            "node": "Insert to Human Queue",
            "type": "main",
            "index": 0
        }]
    ]
}

print("       [OK] Tier 1 validation flow wired")
print("       [OK] Tier 2 validation flow wired")

# Step 4: Update Insert to Cache query
print("\n[5/7] Updating Insert to Cache SQL query...")

for node in workflow['nodes']:
    if node.get('name') == 'Insert to Cache':
        node['parameters']['query'] = """INSERT INTO manual_hunter_cache (
  manufacturer,
  model_number,
  product_family,
  pdf_url,
  confidence,
  tier,
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
  confidence = EXCLUDED.confidence,
  validation_score = EXCLUDED.validation_score,
  validation_content_type = EXCLUDED.validation_content_type,
  last_accessed = NOW()
RETURNING *;"""
        print("       [OK] SQL query updated with validation columns")

# Step 5: Update Telegram success message
print("\n[6/7] Updating Telegram success message...")

for node in workflow['nodes']:
    if node.get('name') == 'Send Found Success':
        node['parameters']['text'] = """✅ Found your manual!

📖 {{ $('Extract Webhook Data').item.json.manufacturer }} {{ $('Extract Webhook Data').item.json.model_number }}
🔗 [Download Manual]({{ $json.pdf_url }})

✨ Quality Score: {{ $json.validation.score }}/10
📄 Format: {{ $json.validation.content_type }}
🎯 Confidence: {{ $json.confidence }}%
🔍 Source: {{ $json.tier === 'tier1' ? 'Tavily Search' : 'Serper Search' }}

Manual validated and ready for field use!"""
        print("       [OK] Message enhanced with validation info")

# Save modified workflow
output_file = 'manual_hunter_integrated.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(workflow, f, indent=2)

print(f"\n[7/7] Modified workflow saved to: {output_file}")
print(f"       Total nodes: {len(workflow['nodes'])} (added 6)")

# Upload to n8n cloud
print("\n" + "="*80)
print("UPLOADING TO N8N CLOUD")
print("="*80)

headers = {
    'X-N8N-API-KEY': API_KEY,
    'Content-Type': 'application/json'
}

# Filter settings to only include allowed keys
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
    print("\n[SUCCESS] Manual Hunter updated with URL validation!")
    result = response.json()
    print(f"\nWorkflow Details:")
    print(f"  Name: {result.get('name')}")
    print(f"  ID: {result.get('id')}")
    print(f"  Active: {result.get('active')}")
    print(f"  Nodes: {len(result.get('nodes'))}")

    print("\n" + "="*80)
    print("INTEGRATION COMPLETE")
    print("="*80)
    print("\nWhat was added:")
    print("  [OK] Tier 1 URL validation (3 nodes)")
    print("  [OK] Tier 2 URL validation (3 nodes)")
    print("  [OK] Validation metadata in cache")
    print("  [OK] Enhanced Telegram messages")
    print("\nNext steps:")
    print("  1. Run update_db_schema.sql on Neon database")
    print("  2. Test the workflow with equipment data")
    print("  3. Monitor validation success rates")

else:
    print(f"\n[ERROR] Failed to update workflow: {response.status_code}")
    print(f"Response: {response.text}")
    print("\nWorkflow was saved locally but not uploaded.")
    print(f"Review: {output_file}")
