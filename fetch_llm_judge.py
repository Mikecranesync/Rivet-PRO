"""
Fetch LLM Judge workflow from n8n cloud
"""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
WORKFLOW_ID = 'QaFV6k14mQroMfat'
BASE_URL = 'https://mikecranesync.app.n8n.cloud/api/v1'

headers = {'X-N8N-API-KEY': API_KEY}

print("="*80)
print("FETCHING LLM JUDGE WORKFLOW")
print("="*80)

response = requests.get(f'{BASE_URL}/workflows/{WORKFLOW_ID}', headers=headers)

if response.status_code == 200:
    workflow = response.json()

    print(f"\nWorkflow: {workflow.get('name')}")
    print(f"ID: {workflow.get('id')}")
    print(f"Active: {workflow.get('active')}")
    print(f"Nodes: {len(workflow.get('nodes', []))}")

    # Save to file
    with open('llm_judge_current.json', 'w', encoding='utf-8') as f:
        json.dump(workflow, f, indent=2)

    print(f"\nSaved to: llm_judge_current.json")

    # List nodes
    print(f"\nNodes:")
    for node in workflow.get('nodes', []):
        node_type = node.get('type', '').split('.')[-1]
        print(f"  [{node_type:15}] {node.get('name')}")

    # Find webhook
    for node in workflow.get('nodes', []):
        if node.get('type') == 'n8n-nodes-base.webhook':
            params = node.get('parameters', {})
            path = params.get('path', '')
            webhook_url = f"https://mikecranesync.app.n8n.cloud/webhook/{path}"
            print(f"\nWebhook URL: {webhook_url}")

    # Check for errors in node configuration
    print(f"\nChecking for issues...")
    issues = []

    for node in workflow.get('nodes', []):
        # Check HTTP Request nodes for proper configuration
        if node.get('type') == 'n8n-nodes-base.httpRequest':
            params = node.get('parameters', {})
            if not params.get('url'):
                issues.append(f"  [ISSUE] {node.get('name')}: Missing URL")

        # Check Code nodes for errors
        if node.get('type') == 'n8n-nodes-base.code':
            params = node.get('parameters', {})
            if not params.get('jsCode'):
                issues.append(f"  [ISSUE] {node.get('name')}: Missing JavaScript code")

    if issues:
        print(f"\nFound {len(issues)} issue(s):")
        for issue in issues:
            print(issue)
    else:
        print("  No obvious configuration issues found")

else:
    print(f"[ERROR] Failed to fetch workflow: {response.status_code}")
    print(response.text)
