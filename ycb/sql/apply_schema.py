#!/usr/bin/env python3
"""
Apply YCB database schema to Supabase.

Usage:
    python -m ycb.sql.apply_schema

Or from project root:
    python ycb/sql/apply_schema.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from supabase import create_client


def apply_schema():
    """Apply YCB schema to Supabase database."""

    # Get credentials from environment
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_API_KEY") or os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("[-] Error: SUPABASE_URL and SUPABASE_API_KEY must be set")
        print("    Set these in your .env file or environment")
        return False

    print(f"[*] Connecting to Supabase: {supabase_url[:50]}...")

    try:
        client = create_client(supabase_url, supabase_key)
        print("[+] Connected to Supabase")
    except Exception as e:
        print(f"[-] Connection failed: {e}")
        return False

    # Read schema file
    schema_path = Path(__file__).parent / "schema.sql"
    if not schema_path.exists():
        print(f"[-] Schema file not found: {schema_path}")
        return False

    schema_sql = schema_path.read_text()

    # Split into individual statements (simple split on semicolons)
    # Note: This won't work for complex SQL with functions - use Supabase SQL Editor for full schema
    print("\n[!] For full schema with triggers and functions, run schema.sql in Supabase SQL Editor")
    print("    https://supabase.com/dashboard/project/YOUR_PROJECT/sql/new")
    print(f"\n    Schema file: {schema_path}")

    # Try to create basic tables using Supabase RPC if available
    # Otherwise, we'll just test the connection and provide instructions

    # Test if tables already exist
    tables_to_check = [
        "ycb_agent_status",
        "ycb_agent_logs",
        "ycb_scripts",
        "ycb_video_pipeline",
        "ycb_upload_jobs",
        "ycb_api_quota"
    ]

    print("\n[*] Checking existing tables...")
    existing_tables = []
    missing_tables = []

    for table in tables_to_check:
        try:
            result = client.table(table).select("count").limit(1).execute()
            existing_tables.append(table)
            print(f"    [+] {table}: exists")
        except Exception as e:
            if "PGRST205" in str(e) or "could not find" in str(e).lower():
                missing_tables.append(table)
                print(f"    [-] {table}: missing")
            else:
                print(f"    [?] {table}: {e}")

    if missing_tables:
        print(f"\n[!] Missing {len(missing_tables)} tables. Run schema.sql in Supabase SQL Editor:")
        print(f"    1. Go to: https://supabase.com/dashboard")
        print(f"    2. Select your project")
        print(f"    3. Go to SQL Editor")
        print(f"    4. Paste contents of: {schema_path}")
        print(f"    5. Click 'Run'")
        return False
    else:
        print(f"\n[+] All {len(existing_tables)} YCB tables exist!")
        return True


if __name__ == "__main__":
    # Load .env file if available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    success = apply_schema()
    sys.exit(0 if success else 1)
