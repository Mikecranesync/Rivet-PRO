"""
Fix LLM Judge workflow - Update parser to handle markdown code fences
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
print("FIXING LLM JUDGE PARSER - HANDLE MARKDOWN CODE FENCES")
print("="*80)

# Load current workflow
response = requests.get(f'{BASE_URL}/{WORKFLOW_ID}', headers={'X-N8N-API-KEY': API_KEY})
workflow = response.json()

print(f"\n[1/3] Loaded workflow: {workflow.get('name')}")

# Find and fix the Parse LLM Response node
print("\n[2/3] Fixing Parse LLM Response node...")

for node in workflow['nodes']:
    if node.get('name') == 'Parse LLM Response':
        print(f"       Found node: {node.get('name')}")

        # Updated code that strips markdown code fences
        updated_code = """const llmResponse = $input.item.json;

// Get URL from Prepare LLM Prompt node
const promptData = $('Prepare LLM Prompt').item.json;
const url = promptData.url;

// Parse LLM response
let criteria = {
  completeness: 0,
  technical_accuracy: 0,
  clarity: 0,
  troubleshooting_usefulness: 0,
  metadata_quality: 0
};
let feedback = 'Failed to get LLM response';
let quality_score = 0;
let error = null;

try {
  // Gemini response format: candidates[0].content.parts[0].text
  const candidate = llmResponse.candidates?.[0];
  let content = candidate?.content?.parts?.[0]?.text || '{}';

  // Strip markdown code fences if present
  content = content.replace(/^```json\\s*/i, '').replace(/\\s*```$/i, '').trim();

  const parsed = JSON.parse(content);

  // Extract scores
  criteria.completeness = parsed.completeness || 0;
  criteria.technical_accuracy = parsed.technical_accuracy || 0;
  criteria.clarity = parsed.clarity || 0;
  criteria.troubleshooting_usefulness = parsed.troubleshooting_usefulness || 0;
  criteria.metadata_quality = parsed.metadata_quality || 0;

  feedback = parsed.feedback || 'No feedback provided';

  // Calculate average quality score
  quality_score = (
    criteria.completeness +
    criteria.technical_accuracy +
    criteria.clarity +
    criteria.troubleshooting_usefulness +
    criteria.metadata_quality
  ) / 5;
  quality_score = Math.round(quality_score * 10) / 10; // Round to 1 decimal

} catch (e) {
  error = `Failed to parse LLM response: ${e.message}`;
}

return {
  json: {
    quality_score,
    criteria,
    feedback,
    llm_model_used: 'gemini-2.5-flash',
    error,
    url
  }
};"""

        node['parameters']['jsCode'] = updated_code
        print("       [OK] Updated parser to strip markdown code fences")
        break

# Save locally
with open('llm_judge_fixed_parser.json', 'w', encoding='utf-8') as f:
    json.dump(workflow, f, indent=2)

print(f"\n       Saved to: llm_judge_fixed_parser.json")

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
    print(f"Active: {result.get('active')}")

    print("\n" + "="*80)
    print("FIX APPLIED")
    print("="*80)
    print("\nWhat was fixed:")
    print("  - Parse LLM Response now strips markdown code fences")
    print("  - Handles ```json ... ``` wrapper from Gemini")
    print("  - Updated model reference to gemini-2.5-flash")
    print("\nReady to test!")

else:
    print(f"       [ERROR] Failed to update: {response.status_code}")
    print(f"Response: {response.text}")
