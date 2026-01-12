import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
WORKFLOW_ID = 'YhW8Up8oM2eHXicx'
API_URL = f'https://mikecranesync.app.n8n.cloud/api/v1/executions'

headers = {
    'X-N8N-API-KEY': API_KEY
}

# Get recent executions for this workflow
params = {
    'workflowId': WORKFLOW_ID,
    'limit': 5
}

print(f"Fetching recent executions for workflow {WORKFLOW_ID}...")
response = requests.get(API_URL, headers=headers, params=params)

if response.status_code == 200:
    result = response.json()
    executions = result.get('data', [])

    print(f"\nFound {len(executions)} recent executions:")
    print("="*80)

    for exe in executions:
        exe_id = exe.get('id')
        status = exe.get('status')
        finished = exe.get('finished')
        started = exe.get('startedAt')

        print(f"\nExecution ID: {exe_id}")
        print(f"  Status: {status}")
        print(f"  Started: {started}")
        print(f"  Finished: {finished}")

        # Get detailed execution data
        detail_response = requests.get(f"{API_URL}/{exe_id}", headers=headers)
        if detail_response.status_code == 200:
            detail = detail_response.json()
            data = detail.get('data', {})
            result_data = data.get('resultData', {})

            print(f"  Error: {data.get('executionError')}")
            print(f"  Last node: {result_data.get('lastNodeExecuted')}")
        print()
else:
    print(f"[ERROR] Failed to fetch executions: {response.status_code}")
    print(response.text)
