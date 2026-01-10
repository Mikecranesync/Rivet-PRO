#!/usr/bin/env python3
"""Check if Atlas CMMS tables exist in Neon"""

import asyncio
import sys

try:
    import asyncpg
except ImportError:
    print("[*] Installing asyncpg...")
    import os
    os.system("pip install asyncpg")
    import asyncpg

DATABASE_URL = "postgresql://neondb_owner:npg_c3UNa4KOlCeL@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require"

async def check_tables():
    print("[*] Connecting to Neon PostgreSQL...")

    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("[OK] Connected\n")

        # Get all tables
        tables = await conn.fetch("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)

        print(f"[*] Found {len(tables)} tables in database:\n")

        atlas_tables = []
        other_tables = []

        for t in tables:
            table_name = t['tablename']
            if 'cmms' in table_name or 'work_order' in table_name or 'technician' in table_name:
                atlas_tables.append(table_name)
            else:
                other_tables.append(table_name)

        if atlas_tables:
            print("[SUCCESS] Atlas CMMS tables found:")
            for table in atlas_tables:
                print(f"   [OK] {table}")
        else:
            print("[WARNING] No Atlas CMMS tables found!")

        if other_tables:
            print(f"\n[*] Other tables ({len(other_tables)}):")
            for table in other_tables:
                print(f"   - {table}")

        # Check for specific Atlas tables
        print("\n[*] Checking required Atlas CMMS tables:")
        required_tables = ['cmms_equipment', 'work_orders', 'technicians']

        all_table_names = [t['tablename'] for t in tables]

        for required in required_tables:
            if required in all_table_names:
                print(f"   [OK] {required} exists")
            else:
                print(f"   [MISSING] {required}")

        await conn.close()

        return len(atlas_tables) > 0

    except Exception as e:
        print(f"[ERROR] {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(check_tables())
    sys.exit(0 if result else 1)
