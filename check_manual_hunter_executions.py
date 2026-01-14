"""
Check recent Manual Hunter workflow executions
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
WORKFLOW_ID = 'HQgppQgX9H2yyQdN'
BASE_URL = 'https://mikecranesync.app.n8n.cloud/api/v1'

headers = {'X-N8N-API-KEY': API_KEY}

print("="*80)
print("CHECKING MANUAL HUNTER EXECUTIONS")
print("="*80)

# Get recent executions
response = requests.get(
    f'{BASE_URL}/executions',
    headers=headers,
    params={'workflowId': WORKFLOW_ID, 'limit': 10}
)

if response.status_code == 200:
    executions = response.json().get('data', [])

    print(f"\nFound {len(executions)} recent executions:\n")

    for i, execution in enumerate(executions[:5], 1):  # Show last 5
        print(f"Execution {i}:")
        print(f"  ID: {execution.get('id')}")
        print(f"  Status: {execution.get('status')}")
        print(f"  Finished: {execution.get('finished')}")
        print(f"  Mode: {execution.get('mode')}")
        print(f"  Started: {execution.get('startedAt')}")

        # Get detailed execution data
        exec_id = execution.get('id')
        detail_response = requests.get(
            f'{BASE_URL}/executions/{exec_id}',
            headers=headers
        )

        if detail_response.status_code == 200:
            detail = detail_response.json()
            data = detail.get('data', {})

            # Check for errors
            if data.get('resultData', {}).get('error'):
                error = data['resultData']['error']
                print(f"  ERROR: {error.get('message', 'Unknown error')}")

            # Check last node executed
            last_node = data.get('resultData', {}).get('lastNodeExecuted')
            if last_node:
                print(f"  Last Node: {last_node}")

        print()

else:
    print(f"[ERROR] Failed to fetch executions: {response.status_code}")
    print(response.text)
