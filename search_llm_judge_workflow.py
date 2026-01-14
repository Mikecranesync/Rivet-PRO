"""
Search for LLM Judge workflow in n8n cloud
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
BASE_URL = 'https://mikecranesync.app.n8n.cloud/api/v1'

headers = {'X-N8N-API-KEY': API_KEY}

print("="*80)
print("SEARCHING FOR LLM JUDGE WORKFLOW")
print("="*80)

# Get all workflows
response = requests.get(f'{BASE_URL}/workflows', headers=headers)

if response.status_code == 200:
    workflows = response.json().get('data', [])

    print(f"\nTotal workflows: {len(workflows)}")

    # Search for LLM Judge
    llm_judge = [w for w in workflows if 'judge' in w.get('name', '').lower() or 'llm' in w.get('name', '').lower()]

    if llm_judge:
        print(f"\nFound {len(llm_judge)} LLM/Judge workflow(s):")
        for wf in llm_judge:
            print(f"\n  Name: {wf.get('name')}")
            print(f"  ID: {wf.get('id')}")
            print(f"  Active: {wf.get('active')}")
            print(f"  Nodes: {len(wf.get('nodes', []))}")
            print(f"  Updated: {wf.get('updatedAt')}")
    else:
        print("\nNo LLM Judge workflow found in n8n cloud")
        print("\nAll workflows:")
        for wf in workflows[:10]:
            print(f"  - {wf.get('name')} (ID: {wf.get('id')})")

else:
    print(f"[ERROR] Failed to fetch workflows: {response.status_code}")
    print(response.text)
