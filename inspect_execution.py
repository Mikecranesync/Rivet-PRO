"""
Inspect a specific Manual Hunter execution in detail
"""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
EXECUTION_ID = '6448'  # Most recent execution
BASE_URL = 'https://mikecranesync.app.n8n.cloud/api/v1'

headers = {'X-N8N-API-KEY': API_KEY}

print("="*80)
print(f"INSPECTING EXECUTION {EXECUTION_ID}")
print("="*80)

response = requests.get(
    f'{BASE_URL}/executions/{EXECUTION_ID}',
    headers=headers
)

if response.status_code == 200:
    execution = response.json()

    print(f"\nStatus: {execution.get('status')}")
    print(f"Finished: {execution.get('finished')}")

    data = execution.get('data', {})
    result_data = data.get('resultData', {})

    print(f"\nRun Data Keys: {list(result_data.keys())}")

    # Check last node executed
    last_node = result_data.get('lastNodeExecuted')
    print(f"Last Node Executed: {last_node}")

    # Get runData (execution path)
    run_data = result_data.get('runData', {})

    print(f"\nNodes that executed ({len(run_data)} total):")
    for node_name in run_data.keys():
        print(f"  - {node_name}")

    # Check for errors in any node
    print("\nChecking for errors...")
    has_errors = False

    for node_name, node_runs in run_data.items():
        for run in node_runs:
            if run.get('error'):
                print(f"  [ERROR] {node_name}: {run['error'].get('message')}")
                has_errors = True

    if not has_errors:
        print("  No errors found")

    # Check what data Tier 1 Search returned
    if 'Tier 1: Tavily Search' in run_data:
        print("\nTier 1 Search Results:")
        tier1_data = run_data['Tier 1: Tavily Search'][0].get('data', {})
        if tier1_data.get('main'):
            items = tier1_data['main'][0]
            print(f"  Items returned: {len(items)}")
            if items:
                print(f"  First item keys: {list(items[0].get('json', {}).keys())}")

    # Check if validation nodes ran
    if 'Validate Tier 1 URL' in run_data:
        print("\nValidation Tier 1 ran:")
        val_data = run_data['Validate Tier 1 URL'][0].get('data', {})
        print(f"  Keys: {val_data.keys()}")

    # Save full execution to file for detailed analysis
    with open(f'execution_{EXECUTION_ID}_detail.json', 'w') as f:
        json.dump(execution, f, indent=2)

    print(f"\nFull execution saved to: execution_{EXECUTION_ID}_detail.json")

else:
    print(f"[ERROR] Failed to fetch execution: {response.status_code}")
    print(response.text)
