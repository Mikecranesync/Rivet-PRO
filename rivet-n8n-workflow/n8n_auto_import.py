#!/usr/bin/env python3
"""
RIVET Pro - n8n Workflow Auto-Import Script

Automatically imports workflow and configures credentials using n8n API.

Requirements:
- n8n running (local or remote)
- n8n API key configured
- .env file with API keys

Usage:
    python n8n_auto_import.py --n8n-url http://localhost:5678 --api-key YOUR_KEY

Or with environment variable:
    export N8N_API_KEY=your-key
    python n8n_auto_import.py
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import requests
from dotenv import load_dotenv


class N8nAutoImporter:
    """Handles automatic import of RIVET Pro workflow to n8n."""

    def __init__(self, n8n_url: str, api_key: str):
        self.n8n_url = n8n_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'X-N8N-API-KEY': api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        self.workflow_dir = Path(__file__).parent

    def test_connection(self) -> bool:
        """Test n8n API connection."""
        try:
            response = requests.get(
                f'{self.n8n_url}/api/v1/workflows',
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                print(f"✅ Connected to n8n at {self.n8n_url}")
                return True
            elif response.status_code == 401:
                print(f"❌ Authentication failed. Check your API key.")
                return False
            else:
                print(f"❌ Connection failed: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to n8n at {self.n8n_url}")
            print("   Make sure n8n is running: n8n start")
            return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False

    def load_workflow(self) -> Dict[str, Any]:
        """Load workflow JSON from file."""
        workflow_file = self.workflow_dir / 'rivet_workflow.json'
        if not workflow_file.exists():
            raise FileNotFoundError(f"Workflow file not found: {workflow_file}")

        with open(workflow_file, 'r') as f:
            workflow = json.load(f)

        print(f"✅ Loaded workflow: {workflow['name']}")
        return workflow

    def create_credential(self, name: str, type_name: str, data: Dict[str, Any]) -> Optional[str]:
        """Create credential in n8n."""
        payload = {
            'name': name,
            'type': type_name,
            'data': data
        }

        try:
            response = requests.post(
                f'{self.n8n_url}/api/v1/credentials',
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                credential = response.json()
                print(f"✅ Created credential: {name} (ID: {credential.get('id')})")
                return credential.get('id')
            elif response.status_code == 409:
                print(f"⚠️  Credential '{name}' already exists")
                # Try to get existing credential ID
                return self.find_credential_by_name(name)
            else:
                print(f"❌ Failed to create credential '{name}': {response.status_code}")
                print(f"   Response: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error creating credential '{name}': {e}")
            return None

    def find_credential_by_name(self, name: str) -> Optional[str]:
        """Find credential by name and return ID."""
        try:
            response = requests.get(
                f'{self.n8n_url}/api/v1/credentials',
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                credentials = response.json()
                for cred in credentials:
                    if cred.get('name') == name:
                        print(f"   Found existing credential ID: {cred.get('id')}")
                        return cred.get('id')
        except Exception as e:
            print(f"   Warning: Could not search credentials: {e}")
        return None

    def setup_credentials(self, env_vars: Dict[str, str]) -> Dict[str, str]:
        """Create all required credentials from .env file."""
        credentials = {}

        print("\n📝 Setting up credentials...")

        # 1. Telegram Bot
        if 'TELEGRAM_BOT_TOKEN' in env_vars:
            cred_id = self.create_credential(
                name='Telegram Bot - RIVET',
                type_name='telegramApi',
                data={'accessToken': env_vars['TELEGRAM_BOT_TOKEN']}
            )
            if cred_id:
                credentials['telegram'] = cred_id

        # 2. Tavily API (you'll need to add this to .env)
        if 'TAVILY_API_KEY' in env_vars:
            cred_id = self.create_credential(
                name='Tavily API',
                type_name='httpHeaderAuth',
                data={
                    'name': 'Authorization',
                    'value': f"Bearer {env_vars['TAVILY_API_KEY']}"
                }
            )
            if cred_id:
                credentials['tavily'] = cred_id
        else:
            print("⚠️  TAVILY_API_KEY not found in .env - you'll need to add this manually")

        # 3. Atlas CMMS API
        if 'ATLAS_CMMS_API_KEY' in env_vars:
            cred_id = self.create_credential(
                name='Atlas CMMS API',
                type_name='httpHeaderAuth',
                data={
                    'name': 'Authorization',
                    'value': f"Bearer {env_vars['ATLAS_CMMS_API_KEY']}"
                }
            )
            if cred_id:
                credentials['atlas_cmms'] = cred_id
        else:
            print("⚠️  ATLAS_CMMS_API_KEY not found in .env - you'll need to add this manually")

        return credentials

    def update_workflow_credentials(self, workflow: Dict[str, Any], credential_ids: Dict[str, str]) -> Dict[str, Any]:
        """Update workflow nodes with actual credential IDs."""
        credential_mapping = {
            'telegramApi': credential_ids.get('telegram'),
            'httpHeaderAuth': credential_ids.get('tavily')  # Default to Tavily, will be overridden
        }

        for node in workflow.get('nodes', []):
            if 'credentials' in node:
                for cred_type, cred_config in node['credentials'].items():
                    # Replace CONFIGURE_AFTER_IMPORT placeholder
                    if cred_config.get('id') == 'CONFIGURE_AFTER_IMPORT':
                        if cred_type in credential_mapping and credential_mapping[cred_type]:
                            node['credentials'][cred_type]['id'] = credential_mapping[cred_type]
                            print(f"   Updated {node['name']}: {cred_type} → {credential_mapping[cred_type]}")

        return workflow

    def import_workflow(self, workflow: Dict[str, Any]) -> Optional[str]:
        """Import workflow to n8n."""
        try:
            response = requests.post(
                f'{self.n8n_url}/api/v1/workflows',
                headers=self.headers,
                json=workflow,
                timeout=30
            )

            if response.status_code in [200, 201]:
                result = response.json()
                workflow_id = result.get('id')
                print(f"\n✅ Workflow imported successfully!")
                print(f"   Workflow ID: {workflow_id}")
                print(f"   Name: {result.get('name')}")
                print(f"   Nodes: {len(result.get('nodes', []))}")
                return workflow_id
            else:
                print(f"\n❌ Failed to import workflow: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
        except Exception as e:
            print(f"\n❌ Error importing workflow: {e}")
            return None

    def set_workflow_variables(self, env_vars: Dict[str, str]):
        """Set n8n environment variables from .env."""
        print("\n📝 Setting environment variables...")

        variables = {
            'GOOGLE_API_KEY': env_vars.get('GOOGLE_API_KEY'),
            'ATLAS_CMMS_URL': env_vars.get('ATLAS_CMMS_URL', 'https://rivet-cmms.com')
        }

        for var_name, var_value in variables.items():
            if var_value:
                print(f"   {var_name} = {var_value[:20]}... (set in n8n Settings → Variables)")
            else:
                print(f"   ⚠️  {var_name} not found in .env")

        print("\n   Note: Variables must be set manually in n8n UI:")
        print("   n8n → Settings → Variables → Add Variable")

    def run(self):
        """Execute full import process."""
        print("=" * 60)
        print("RIVET Pro - n8n Workflow Auto-Import")
        print("=" * 60)

        # 1. Test connection
        if not self.test_connection():
            return False

        # 2. Load environment variables
        env_file = self.workflow_dir.parent / 'rivet_pro' / '.env'
        if env_file.exists():
            load_dotenv(env_file)
            print(f"✅ Loaded .env from {env_file}")
        else:
            print(f"⚠️  .env file not found at {env_file}")

        env_vars = dict(os.environ)

        # 3. Setup credentials
        credential_ids = self.setup_credentials(env_vars)

        # 4. Load and update workflow
        print("\n📦 Loading workflow...")
        workflow = self.load_workflow()

        if credential_ids:
            print("\n🔗 Updating workflow with credentials...")
            workflow = self.update_workflow_credentials(workflow, credential_ids)

        # 5. Import workflow
        print("\n📤 Importing workflow to n8n...")
        workflow_id = self.import_workflow(workflow)

        if not workflow_id:
            return False

        # 6. Set variables
        self.set_workflow_variables(env_vars)

        # 7. Success summary
        print("\n" + "=" * 60)
        print("✅ IMPORT COMPLETE!")
        print("=" * 60)
        print(f"\nWorkflow URL: {self.n8n_url}/workflow/{workflow_id}")
        print("\n📋 Next Steps:")
        print("   1. Open workflow in n8n")
        print("   2. Set variables: GOOGLE_API_KEY, ATLAS_CMMS_URL")
        print("   3. Add missing credentials (Tavily, Atlas CMMS)")
        print("   4. Activate workflow")
        print("   5. Test with Telegram bot\n")

        return True


def main():
    parser = argparse.ArgumentParser(
        description='Auto-import RIVET Pro workflow to n8n'
    )
    parser.add_argument(
        '--n8n-url',
        default=os.getenv('N8N_URL', 'http://localhost:5678'),
        help='n8n instance URL (default: http://localhost:5678)'
    )
    parser.add_argument(
        '--api-key',
        default=os.getenv('N8N_API_KEY'),
        help='n8n API key (or set N8N_API_KEY env var)'
    )

    args = parser.parse_args()

    if not args.api_key:
        print("❌ Error: n8n API key required")
        print("\nOptions:")
        print("  1. Set environment variable: export N8N_API_KEY=your-key")
        print("  2. Pass as argument: --api-key your-key")
        print("\nTo get your API key:")
        print("  n8n → Settings → API → Generate API Key")
        sys.exit(1)

    importer = N8nAutoImporter(args.n8n_url, args.api_key)
    success = importer.run()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
