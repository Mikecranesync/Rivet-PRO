#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Import RIVET test workflows to n8n"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv(override=True)

N8N_URL = os.getenv("N8N_WEBHOOK_BASE_URL", "https://mikecranesync.app.n8n.cloud")
API_KEY = os.getenv("N8N_CLOUD_API_KEY")

if not API_KEY:
    print("ERROR: N8N_CLOUD_API_KEY not found in environment")
    exit(1)

WORKFLOWS = [
    ("n8n/workflows/test/rivet_llm_judge.json", "QaFV6k14mQroMfat"),
    ("n8n/workflows/test/rivet_test_runner.json", "bc6oMDj0hVuW4ZXX")
]

headers = {
    "X-N8N-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

print(f"Importing workflows to {N8N_URL}...")
print(f"API Key: {API_KEY[:20]}...{API_KEY[-10:]}")

for workflow_file, workflow_id in WORKFLOWS:
    print(f"\nUpdating {workflow_file}...")

    try:
        with open(workflow_file, 'r') as f:
            workflow_data = json.load(f)

        # Remove properties that n8n API doesn't accept
        properties_to_remove = ['id', 'pinData', 'triggerCount', 'updatedAt', 'versionId', 'staticData', 'tags']
        for prop in properties_to_remove:
            workflow_data.pop(prop, None)

        # Update existing workflow using PUT
        response = requests.put(
            f"{N8N_URL}/api/v1/workflows/{workflow_id}",
            headers=headers,
            json=workflow_data,
            timeout=30
        )

        if response.status_code in [200, 201]:
            result = response.json()
            workflow_id = result.get('id', 'unknown')
            print(f"[OK] SUCCESS: Imported as workflow ID {workflow_id}")

            # Activate the workflow
            activate_response = requests.post(
                f"{N8N_URL}/api/v1/workflows/{workflow_id}/activate",
                headers=headers,
                timeout=10
            )

            if activate_response.status_code == 200:
                print(f"[OK] Activated workflow {workflow_id}")
            else:
                print(f"[WARN] Could not activate: {activate_response.status_code}")

        else:
            print(f"[ERROR] FAILED: {response.status_code}")
            print(f"Response: {response.text[:200]}")

    except FileNotFoundError:
        print(f"[ERROR] File not found: {workflow_file}")
    except Exception as e:
        print(f"[ERROR] Error: {e}")

print("\n" + "="*60)
print("Import complete!")
print("="*60)
