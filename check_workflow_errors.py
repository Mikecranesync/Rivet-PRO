import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
API_URL = 'https://mikecranesync.app.n8n.cloud/api/v1'

headers = {
    'X-N8N-API-KEY': API_KEY
}

# Workflows with errors
PROBLEM_WORKFLOWS = {
    'LLM Judge': {'id': 'QaFV6k14mQroMfat', 'error_exec': '6463'},
    'Photo Bot v2': {'id': 'b-dRUZ6PrwkhlyRuQi7QS', 'error_execs': ['6246', '6245']}
}

print("=" * 80)
print("WORKFLOW ERROR ANALYSIS")
print("=" * 80)
print()

def get_execution_details(execution_id):
    """Get detailed execution information"""
    try:
        url = f"{API_URL}/executions/{execution_id}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error fetching execution {execution_id}: {e}")
        return None

# Check LLM Judge error
print("[LLM Judge - Execution 6463]")
llm_exec = get_execution_details('6463')
if llm_exec:
    status = llm_exec.get('status', 'unknown')
    started = llm_exec.get('startedAt', 'N/A')
    stopped = llm_exec.get('stoppedAt', 'N/A')
    mode = llm_exec.get('mode', 'N/A')

    print(f"  Status: {status}")
    print(f"  Started: {started}")
    print(f"  Stopped: {stopped}")
    print(f"  Mode: {mode}")

    # Check for error data
    data = llm_exec.get('data', {})
    result_data = data.get('resultData', {})
    error_obj = result_data.get('error', {})

    if error_obj:
        error_msg = error_obj.get('message', 'No message')
        error_node = error_obj.get('node', {}).get('name', 'Unknown node')
        print(f"  Error Node: {error_node}")
        print(f"  Error Message: {error_msg}")
    else:
        # Check last node
        last_node_executed = result_data.get('lastNodeExecuted', 'Unknown')
        print(f"  Last Node: {last_node_executed}")

        # Check if there's error in runData
        run_data = result_data.get('runData', {})
        for node_name, node_runs in run_data.items():
            if node_runs:
                for run in node_runs:
                    if run.get('error'):
                        print(f"  Error in {node_name}: {run['error']}")
else:
    print("  Could not fetch execution details")

print()

# Check Photo Bot v2 errors
print("[Photo Bot v2 - Recent Errors]")
for exec_id in ['6246', '6245']:
    print(f"\n  Execution {exec_id}:")
    photo_exec = get_execution_details(exec_id)
    if photo_exec:
        status = photo_exec.get('status', 'unknown')
        started = photo_exec.get('startedAt', 'N/A')

        print(f"    Status: {status}")
        print(f"    Started: {started}")

        data = photo_exec.get('data', {})
        result_data = data.get('resultData', {})
        error_obj = result_data.get('error', {})

        if error_obj:
            error_msg = error_obj.get('message', 'No message')
            error_node = error_obj.get('node', {}).get('name', 'Unknown node')
            print(f"    Error Node: {error_node}")
            print(f"    Error Message: {error_msg}")

            # Get more details
            error_description = error_obj.get('description', '')
            if error_description:
                print(f"    Description: {error_description[:200]}")
    else:
        print("    Could not fetch execution details")

print()
print("=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)
print()
print("Based on error analysis:")
print()
print("1. LLM Judge: Check execution 6463 for specific error details")
print("   - May be a transient API issue (recent executions successful)")
print()
print("2. Photo Bot v2: Check executions 6246 and 6245")
print("   - Errors occurred on 2026-01-09")
print("   - Recent execution (6252) was successful")
print("   - May be photo processing or Telegram API issues")
print()
print("Overall: Most workflows are healthy with occasional transient errors")
print("=" * 80)
