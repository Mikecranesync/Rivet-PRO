import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
WORKFLOW_ID = 'YhW8Up8oM2eHXicx'
API_URL = f'https://mikecranesync.app.n8n.cloud/api/v1/executions'

headers = {
    'X-N8N-API-KEY': API_KEY
}

# Get recent executions
params = {
    'workflowId': WORKFLOW_ID,
    'limit': 20
}

print("Fetching recent executions...")
response = requests.get(API_URL, headers=headers, params=params)

if response.status_code == 200:
    result = response.json()
    executions = result.get('data', [])

    print(f"\nFound {len(executions)} recent executions")
    print("="*80)

    success_count = 0
    error_count = 0

    for exe in executions:
        exe_id = exe.get('id')
        status = exe.get('status')
        started = exe.get('startedAt')
        finished = exe.get('finished')

        if status == 'success':
            success_count += 1
        elif status == 'error':
            error_count += 1

        print(f"\nExecution {exe_id}: {status}")
        print(f"  Started: {started}")
        print(f"  Finished: {finished}")

    # Statistics
    print("\n" + "="*80)
    print("EXECUTION STATISTICS")
    print("="*80)
    print(f"Total: {len(executions)}")
    print(f"Success: {success_count} ({success_count/len(executions)*100:.1f}%)")
    print(f"Error: {error_count} ({error_count/len(executions)*100:.1f}%)")

    # Get detailed data for most recent execution
    if executions:
        latest = executions[0]
        exe_id = latest.get('id')

        print(f"\n" + "="*80)
        print(f"LATEST EXECUTION DETAILS (ID: {exe_id})")
        print("="*80)

        detail_response = requests.get(f"{API_URL}/{exe_id}", headers=headers)
        if detail_response.status_code == 200:
            detail = detail_response.json()

            # Save to file for inspection
            with open(f'execution_{exe_id}_detail.json', 'w', encoding='utf-8') as f:
                json.dump(detail, f, indent=2)

            print(f"Status: {detail.get('status')}")
            print(f"Mode: {detail.get('mode')}")

            data = detail.get('data', {})
            print(f"Execution Error: {data.get('executionError')}")

            result_data = data.get('resultData', {})
            print(f"Last Node Executed: {result_data.get('lastNodeExecuted')}")

            # Check node executions
            run_data = result_data.get('runData', {})
            if run_data:
                print(f"\nNodes executed: {len(run_data)}")
                for node_name, node_data in run_data.items():
                    print(f"  - {node_name}")

            print(f"\nDetailed execution saved to: execution_{exe_id}_detail.json")

else:
    print(f"[ERROR] Failed to fetch executions: {response.status_code}")
    print(response.text)
