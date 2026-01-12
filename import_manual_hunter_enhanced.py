"""
Import the enhanced Manual Hunter workflow (with Groq Tier 3) to n8n
Smoke Test 1: Workflow Import & Activation
"""

import requests
import json
import sys

# Configuration
N8N_URL = "http://72.60.175.144:5678"
N8N_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxNzBlNDViYy1iNjFjLTQwOGItYTFmYS00OGQyMTA5Y2FjZWMiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY3ODU5OTc0LCJleHAiOjE3NzA0NDA0MDB9.UW7Z-lSRZ9at6M1l_MwRj3SMBkf2SkzTCagFyu3Ohv4"
WORKFLOW_FILE = "rivet-n8n-workflow/rivet_workflow.json"

headers = {
    "X-N8N-API-KEY": N8N_API_KEY,
    "Content-Type": "application/json"
}

def load_workflow():
    """Load and clean workflow JSON"""
    print("[1/5] Loading workflow from file...")
    with open(WORKFLOW_FILE, 'r', encoding='utf-8') as f:
        workflow = json.load(f)

    print(f"  Workflow: {workflow['name']}")
    print(f"  Nodes: {len(workflow['nodes'])}")
    print(f"  Connections: {len(workflow['connections'])}")

    # Clean workflow for API (remove fields that can't be POSTed)
    clean_workflow = {
        'name': workflow['name'],
        'nodes': workflow['nodes'],
        'connections': workflow['connections'],
        'settings': workflow.get('settings', {}),
        'staticData': workflow.get('staticData'),
        'tags': workflow.get('tags', [])
    }

    return clean_workflow

def import_workflow(workflow):
    """Import workflow to n8n"""
    print("\n[2/5] Importing workflow to n8n...")

    response = requests.post(
        f"{N8N_URL}/api/v1/workflows",
        headers=headers,
        json=workflow
    )

    if response.status_code in [200, 201]:
        result = response.json()
        print(f"  SUCCESS: Workflow imported")
        print(f"  Workflow ID: {result['id']}")
        print(f"  Workflow URL: {N8N_URL}/workflow/{result['id']}")
        return result['id']
    else:
        print(f"  ERROR: Import failed")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")
        return None

def activate_workflow(workflow_id):
    """Activate the imported workflow"""
    print("\n[3/5] Activating workflow...")

    response = requests.post(
        f"{N8N_URL}/api/v1/workflows/{workflow_id}/activate",
        headers=headers
    )

    if response.status_code in [200, 201]:
        print(f"  SUCCESS: Workflow activated")
        return True
    else:
        print(f"  ERROR: Activation failed")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")
        return False

def get_workflow_info(workflow_id):
    """Get workflow details including webhook URL"""
    print("\n[4/5] Getting workflow info...")

    response = requests.get(
        f"{N8N_URL}/api/v1/workflows/{workflow_id}",
        headers=headers
    )

    if response.status_code == 200:
        workflow = response.json()
        print(f"  Workflow: {workflow['name']}")
        print(f"  Active: {workflow.get('active', False)}")
        print(f"  Nodes: {len(workflow['nodes'])}")

        # Find webhook URL from Telegram Trigger node
        for node in workflow['nodes']:
            if node['type'] == 'n8n-nodes-base.telegramTrigger':
                webhook_path = node.get('webhookId', 'rivet-manual-hunter')
                webhook_url = f"{N8N_URL}/webhook-test/{webhook_path}"
                print(f"  Webhook URL: {webhook_url}")
                return webhook_url

        print(f"  WARNING: No Telegram trigger found")
        return None
    else:
        print(f"  ERROR: Failed to get workflow info")
        return None

def verify_nodes(workflow_id):
    """Verify all expected nodes are present"""
    print("\n[5/5] Verifying nodes...")

    response = requests.get(
        f"{N8N_URL}/api/v1/workflows/{workflow_id}",
        headers=headers
    )

    if response.status_code != 200:
        print(f"  ERROR: Failed to fetch workflow")
        return False

    workflow = response.json()
    nodes = workflow['nodes']

    # Expected nodes
    expected_nodes = [
        "Telegram Photo Received",
        "Has Photo?",
        "Get Telegram File",
        "Download Photo",
        "Gemini Vision OCR",
        "Parse OCR Response",
        "Confidence >= 70%?",
        "Search Atlas CMMS",
        "Asset Exists?",
        "Create Asset",
        "Update Asset",
        "Quick Manual Search",
        "PDF Found?",
        "Send PDF Link",
        "Deep Search - Manufacturer Site",
        "Deep Search Found PDF?",
        "Send Deep Search Result",
        "Groq Web Search",  # NEW
        "Parse Groq Response",  # NEW
        "Found After Groq?",  # NEW
        "Send Groq Result",  # NEW
        "Send Not Found",
        "Request Photo",
        "Ask for Clarification"
    ]

    node_names = [node['name'] for node in nodes]

    print(f"  Total nodes: {len(nodes)}")
    print(f"  Expected: {len(expected_nodes)}")

    # Check for new Groq nodes
    groq_nodes = [name for name in node_names if 'Groq' in name]
    print(f"  Groq nodes found: {len(groq_nodes)}")
    for groq_node in groq_nodes:
        print(f"    - {groq_node}")

    # Check for missing nodes
    missing = set(expected_nodes) - set(node_names)
    if missing:
        print(f"  WARNING: Missing nodes: {missing}")
    else:
        print(f"  SUCCESS: All expected nodes present")

    return len(missing) == 0

def main():
    print("=" * 60)
    print("Manual Hunter Enhanced Workflow Import")
    print("Smoke Test 1: Workflow Import & Activation")
    print("=" * 60)

    # Step 1: Load workflow
    try:
        workflow = load_workflow()
    except Exception as e:
        print(f"ERROR: Failed to load workflow: {e}")
        sys.exit(1)

    # Step 2: Import workflow
    workflow_id = import_workflow(workflow)
    if not workflow_id:
        print("\n❌ SMOKE TEST 1 FAILED: Import failed")
        sys.exit(1)

    # Step 3: Activate workflow
    if not activate_workflow(workflow_id):
        print("\n❌ SMOKE TEST 1 FAILED: Activation failed")
        sys.exit(1)

    # Step 4: Get webhook URL
    webhook_url = get_workflow_info(workflow_id)

    # Step 5: Verify nodes
    all_nodes_present = verify_nodes(workflow_id)

    # Test result
    print("\n" + "=" * 60)
    if all_nodes_present and webhook_url:
        print("✓ SMOKE TEST 1 PASSED: Workflow Import & Activation")
        print("\nNext steps:")
        print(f"1. Open n8n: {N8N_URL}/workflow/{workflow_id}")
        print("2. Configure credentials (see MANUAL_HUNTER_SETUP.md)")
        print("3. Register Telegram webhook")
        print(f"4. Test webhook: curl {webhook_url}")
    else:
        print("❌ SMOKE TEST 1 FAILED: Verification issues")
    print("=" * 60)

if __name__ == "__main__":
    main()
