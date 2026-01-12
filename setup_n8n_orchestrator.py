#!/usr/bin/env python3
"""
Setup n8n Orchestrator Workflow
Automatically imports the Rivet-PRO startup orchestration workflow into n8n
"""
import json
import os
import sys
import requests
from pathlib import Path


def check_n8n_running(n8n_url):
    """Check if n8n is running"""
    print(f"\n>> Checking n8n at {n8n_url}...")
    try:
        r = requests.get(f"{n8n_url}/healthz", timeout=5)
        if r.status_code == 200:
            print(">> n8n is running")
            return True
        else:
            print(f"WARNING: n8n returned HTTP {r.status_code}")
            return False
    except Exception as e:
        print(f"ERROR: Could not connect to n8n: {e}")
        print("\nPlease start n8n:")
        print("  npx n8n")
        print("  or")
        print("  n8n start")
        return False


def get_n8n_api_key():
    """Get n8n API key from .env or prompt user"""
    env_file = Path(".env")

    # Try to read from .env
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.startswith("N8N_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    if key and key != "your_n8n_api_key_here":
                        print(f">> Found N8N_API_KEY in .env")
                        return key

    # Prompt user
    print("\nN8N_API_KEY not found in .env")
    print("\nTo get your n8n API key:")
    print("  1. Open http://localhost:5678")
    print("  2. Go to Settings → API")
    print("  3. Create new API key")
    print("  4. Copy the key\n")

    key = input("Enter your n8n API key (or press Enter to skip): ").strip()
    if not key:
        return None

    # Save to .env
    save = input("\nSave this key to .env? (y/n): ").strip().lower()
    if save == 'y':
        with open(env_file, 'a') as f:
            f.write(f"\nN8N_API_KEY={key}\n")
        print(">> Saved to .env")

    return key


def import_workflow(n8n_url, api_key, workflow_file):
    """Import workflow into n8n"""
    print(f"\n>> Importing workflow from {workflow_file.name}...")

    # Load workflow JSON
    with open(workflow_file, encoding='utf-8') as f:
        workflow_data = json.load(f)

    # Import via API
    headers = {
        "X-N8N-API-KEY": api_key,
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(
            f"{n8n_url}/api/v1/workflows",
            headers=headers,
            json=workflow_data,
            timeout=10
        )

        if r.status_code in [200, 201]:
            workflow = r.json()
            workflow_id = workflow.get('id')
            print(f">> Workflow imported successfully!")
            print(f">> Workflow ID: {workflow_id}")
            print(f">> Workflow URL: {n8n_url}/workflow/{workflow_id}")
            return workflow_id
        else:
            print(f"ERROR: Failed to import workflow (HTTP {r.status_code})")
            print(f"Response: {r.text}")
            return None

    except Exception as e:
        print(f"ERROR: Failed to import workflow: {e}")
        return None


def activate_workflow(n8n_url, api_key, workflow_id):
    """Activate the workflow"""
    print(f"\n>> Activating workflow {workflow_id}...")

    headers = {
        "X-N8N-API-KEY": api_key,
        "Content-Type": "application/json"
    }

    try:
        r = requests.patch(
            f"{n8n_url}/api/v1/workflows/{workflow_id}",
            headers=headers,
            json={"active": True},
            timeout=10
        )

        if r.status_code == 200:
            print(">> Workflow activated!")
            return True
        else:
            print(f"WARNING: Could not activate workflow (HTTP {r.status_code})")
            return False

    except Exception as e:
        print(f"WARNING: Failed to activate workflow: {e}")
        return False


def main():
    """Main entry point"""
    print("=" * 60)
    print("  RIVET-PRO N8N ORCHESTRATOR SETUP")
    print("=" * 60)

    # Configuration
    N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
    WORKFLOW_FILE = Path("rivet-n8n-workflow/rivet_startup_orchestration.json")

    # Check workflow file exists
    if not WORKFLOW_FILE.exists():
        print(f"ERROR: Workflow file not found: {WORKFLOW_FILE}")
        sys.exit(1)

    # Check n8n is running
    if not check_n8n_running(N8N_URL):
        sys.exit(1)

    # Get API key
    api_key = get_n8n_api_key()
    if not api_key:
        print("\nERROR: N8N_API_KEY is required")
        print("You can also manually import the workflow:")
        print(f"  1. Open {N8N_URL}")
        print("  2. Click 'Add workflow' → 'Import from file'")
        print(f"  3. Select: {WORKFLOW_FILE.absolute()}")
        sys.exit(1)

    # Import workflow
    workflow_id = import_workflow(N8N_URL, api_key, WORKFLOW_FILE)
    if not workflow_id:
        sys.exit(1)

    # Activate workflow
    activate_workflow(N8N_URL, api_key, workflow_id)

    # Success
    print("\n" + "=" * 60)
    print("  SETUP COMPLETE!")
    print("=" * 60)
    print(f"\n>> Workflow URL: {N8N_URL}/workflow/{workflow_id}")
    print("\nTo use the orchestrator:")
    print(f"  1. Open {N8N_URL}")
    print("  2. Find 'Rivet-PRO Startup Orchestrator' workflow")
    print("  3. Click 'Execute Workflow' to start Rivet-PRO")
    print("\nThe workflow will:")
    print("  ✓ Check Docker is running")
    print("  ✓ Start CMMS containers if needed")
    print("  ✓ Wait for CMMS to be healthy")
    print("  ✓ Test login with mike@cranesync.com")
    print("  ✓ Start Telegram bot")
    print("  ✓ Send success notification to Telegram")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
