import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

API_KEY = os.getenv('N8N_CLOUD_API_KEY')
N8N_BASE = 'https://mikecranesync.app.n8n.cloud'
API_URL = f'{N8N_BASE}/api/v1'

headers = {
    'X-N8N-API-KEY': API_KEY
}

# Core workflows to test
CORE_WORKFLOWS = {
    'URL Validator': 'YhW8Up8oM2eHXicx',
    'URL Validator PROD': '6dINHjc5VUj5oQg2',
    'LLM Judge': 'QaFV6k14mQroMfat',
    'Photo Bot v2': 'b-dRUZ6PrwkhlyRuQi7QS',
    'Manual Hunter': 'HQgppQgX9H2yyQdN',
    'Test Runner': 'bc6oMDj0hVuW4ZXX'
}

print("=" * 80)
print("RIVET CORE WORKFLOWS - TEST & VERIFICATION REPORT")
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)
print()

def test_webhook(name, path, test_data):
    """Test a webhook endpoint"""
    url = f"{N8N_BASE}/webhook/{path}"
    try:
        print(f"  Testing webhook: /{path}")
        response = requests.post(url, json=test_data, timeout=10)
        print(f"    Status: {response.status_code}")
        if response.status_code == 200:
            print(f"    Response: {response.text[:200]}")
            return True
        else:
            print(f"    Error: {response.text[:200]}")
            return False
    except requests.exceptions.Timeout:
        print(f"    Timeout (workflow may still be processing)")
        return None
    except Exception as e:
        print(f"    Exception: {e}")
        return False

def get_recent_executions(workflow_id, limit=5):
    """Get recent executions for a workflow"""
    try:
        url = f"{API_URL}/executions"
        params = {
            'workflowId': workflow_id,
            'limit': limit
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            return data.get('data', [])
        return []
    except Exception as e:
        print(f"    Error fetching executions: {e}")
        return []

def check_workflow_health(name, workflow_id):
    """Check workflow health and recent executions"""
    print(f"\n[{name}]")
    print(f"  ID: {workflow_id}")

    # Get workflow details
    try:
        response = requests.get(f"{API_URL}/workflows/{workflow_id}", headers=headers)
        if response.status_code != 200:
            print(f"  [ERROR] Cannot fetch workflow details")
            return False

        workflow = response.json()
        active = workflow.get('active', False)
        nodes = workflow.get('nodes', [])

        print(f"  Status: {'ACTIVE' if active else 'INACTIVE'}")
        print(f"  Nodes: {len(nodes)}")

        if not active:
            print(f"  [WARNING] Workflow is not active!")
            return False

        # Get recent executions
        executions = get_recent_executions(workflow_id)
        if executions:
            print(f"  Recent Executions: {len(executions)}")

            success_count = 0
            error_count = 0
            running_count = 0

            for exec_data in executions[:5]:
                status = exec_data.get('status', 'unknown')
                started = exec_data.get('startedAt', 'N/A')
                exec_id = exec_data.get('id', 'N/A')

                if status == 'success':
                    success_count += 1
                elif status == 'error':
                    error_count += 1
                elif status == 'running':
                    running_count += 1

                print(f"    - {exec_id[:12]}: {status} ({started[:19] if started != 'N/A' else 'N/A'})")

            print(f"  Summary: {success_count} success, {error_count} errors, {running_count} running")

            if error_count > 0:
                print(f"  [WARNING] Found {error_count} failed executions")
                return False
            elif success_count > 0:
                print(f"  [OK] Workflow has successful recent executions")
                return True
            else:
                print(f"  [INFO] No recent executions found")
                return None
        else:
            print(f"  [INFO] No executions found")
            return None

    except Exception as e:
        print(f"  [ERROR] {type(e).__name__}: {e}")
        return False

# Test each core workflow
results = {}
for name, workflow_id in CORE_WORKFLOWS.items():
    result = check_workflow_health(name, workflow_id)
    results[name] = result

print("\n" + "=" * 80)
print("WEBHOOK ENDPOINT TESTS")
print("=" * 80)

# Test webhook endpoints
webhook_tests = {
    'URL Validator': {
        'path': 'rivet-url-validator',
        'data': {'url': 'https://example.com', 'test': True}
    },
    'Manual Hunter': {
        'path': 'rivet-manual-hunter',
        'data': {'query': 'test motor', 'test': True}
    },
    'LLM Judge': {
        'path': 'rivet-llm-judge',
        'data': {'message': 'test message', 'test': True}
    },
    'Test Runner': {
        'path': 'rivet-test-runner',
        'data': {'test': True}
    }
}

webhook_results = {}
for name, config in webhook_tests.items():
    print(f"\n[{name}]")
    result = test_webhook(name, config['path'], config['data'])
    webhook_results[name] = result

# Final summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

working = sum(1 for v in results.values() if v is True)
failing = sum(1 for v in results.values() if v is False)
unknown = sum(1 for v in results.values() if v is None)

print(f"\nWorkflow Health:")
print(f"  Working: {working}/{len(results)}")
print(f"  Failing: {failing}/{len(results)}")
print(f"  Unknown: {unknown}/{len(results)}")

print(f"\nWebhook Tests:")
webhook_working = sum(1 for v in webhook_results.values() if v is True)
webhook_failing = sum(1 for v in webhook_results.values() if v is False)
webhook_timeout = sum(1 for v in webhook_results.values() if v is None)

print(f"  Responding: {webhook_working}/{len(webhook_results)}")
print(f"  Errors: {webhook_failing}/{len(webhook_results)}")
print(f"  Timeouts: {webhook_timeout}/{len(webhook_results)}")

print("\n" + "=" * 80)

if failing > 0 or webhook_failing > 0:
    print("[WARNING] Some workflows or endpoints are not working properly")
elif working == len(results) and webhook_working == len(webhook_results):
    print("[SUCCESS] All core workflows are working properly!")
else:
    print("[INFO] Most workflows operational, some need testing")

print("=" * 80)
