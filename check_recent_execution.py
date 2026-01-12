"""
Check the most recent LLM Judge execution to see what went wrong
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
print("CHECKING RECENT LLM JUDGE EXECUTION")
print("="*80)

# Get recent executions
response = requests.get(
    f'{BASE_URL}/executions',
    headers=headers,
    params={'workflowId': WORKFLOW_ID, 'limit': 5}
)

if response.status_code == 200:
    executions = response.json().get('data', [])

    if executions:
        latest = executions[0]
        exec_id = latest.get('id')

        print(f"\nLatest execution:")
        print(f"  ID: {exec_id}")
        print(f"  Status: {latest.get('status')}")
        print(f"  Started: {latest.get('startedAt')}")

        # Get detailed execution
        detail_response = requests.get(
            f'{BASE_URL}/executions/{exec_id}',
            headers=headers
        )

        if detail_response.status_code == 200:
            detail = detail_response.json()

            # Save full execution for inspection
            with open(f'execution_{exec_id}.json', 'w') as f:
                json.dump(detail, f, indent=2)

            print(f"\nSaved execution details to: execution_{exec_id}.json")

            # Check if there's error info
            data = detail.get('data', {})
            result_data = data.get('resultData', {})

            if result_data.get('error'):
                print(f"\n[ERROR] {result_data['error']}")

            print("\nExecution completed successfully")
            print("Check the JSON file for detailed node outputs")

else:
    print(f"[ERROR] Failed to fetch executions: {response.status_code}")
