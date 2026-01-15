#!/usr/bin/env python3
"""
Sync CMMS schema and data from Neon to Supabase for failover support.

Usage:
    python scripts/sync_supabase.py              # Schema + data sync
    python scripts/sync_supabase.py --schema     # Schema only
    python scripts/sync_supabase.py --data       # Data only
"""

import asyncio
import os
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()


async def run_schema_migration():
    """Run schema migration on Supabase."""
    import asyncpg

    print("\n" + "="*60)
    print("STEP 1: Schema Migration")
    print("="*60)

    supabase_url = os.getenv("SUPABASE_DB_URL")
    if not supabase_url:
        print("ERROR: SUPABASE_DB_URL not set")
        return False

    # Read SQL file
    sql_file = Path(__file__).parent / "sync_supabase_schema.sql"
    if not sql_file.exists():
        print(f"ERROR: {sql_file} not found")
        return False

    with open(sql_file, 'r') as f:
        schema_sql = f.read()

    try:
        conn = await asyncpg.connect(supabase_url)

        # Execute schema SQL (split by statements for better error handling)
        print("Running schema migration...")
        await conn.execute(schema_sql)

        print("✓ Schema migration completed successfully")
        await conn.close()
        return True

    except Exception as e:
        print(f"✗ Schema migration failed: {e}")
        return False


async def sync_data():
    """Sync data from Neon to Supabase."""
    import asyncpg

    print("\n" + "="*60)
    print("STEP 2: Data Sync")
    print("="*60)

    neon_url = os.getenv("DATABASE_URL")
    supabase_url = os.getenv("SUPABASE_DB_URL")

    if not neon_url:
        print("ERROR: DATABASE_URL (Neon) not set")
        return False
    if not supabase_url:
        print("ERROR: SUPABASE_DB_URL not set")
        return False

    try:
        neon = await asyncpg.connect(neon_url)
        supabase = await asyncpg.connect(supabase_url)

        # Sync users
        print("\nSyncing users...")
        users = await neon.fetch("""
            SELECT id, telegram_id, full_name, NULL as username,
                   subscription_tier, subscription_status, created_at, last_active_at
            FROM users
            WHERE telegram_id IS NOT NULL
        """)

        for user in users:
            await supabase.execute("""
                INSERT INTO users (id, telegram_id, full_name, username,
                                   subscription_tier, subscription_status, created_at, last_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (telegram_id) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    username = EXCLUDED.username,
                    subscription_tier = EXCLUDED.subscription_tier,
                    subscription_status = EXCLUDED.subscription_status,
                    last_active = EXCLUDED.last_active
            """, user['id'], user['telegram_id'], user['full_name'],
                user['username'], user['subscription_tier'] or 'free',
                user['subscription_status'] or 'active', user['created_at'],
                user['last_active_at'])
        print(f"  ✓ Synced {len(users)} users")

        # Sync equipment
        print("\nSyncing equipment...")
        equipment = await neon.fetch("""
            SELECT id, equipment_number, equipment_model_id, manufacturer, model_number,
                   serial_number, equipment_type, location, department, criticality,
                   owned_by_user_id, first_reported_by, machine_id, description,
                   photo_file_id, installation_date, last_maintenance_date,
                   work_order_count, total_downtime_hours, last_reported_fault,
                   last_work_order_at, created_at, updated_at
            FROM cmms_equipment
        """)

        for eq in equipment:
            await supabase.execute("""
                INSERT INTO cmms_equipment (
                    id, equipment_number, equipment_model_id, manufacturer, model_number,
                    serial_number, equipment_type, location, department, criticality,
                    owned_by_user_id, first_reported_by, machine_id, description,
                    photo_file_id, installation_date, last_maintenance_date,
                    work_order_count, total_downtime_hours, last_reported_fault,
                    last_work_order_at, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23)
                ON CONFLICT (equipment_number) DO UPDATE SET
                    manufacturer = EXCLUDED.manufacturer,
                    model_number = EXCLUDED.model_number,
                    work_order_count = EXCLUDED.work_order_count,
                    updated_at = EXCLUDED.updated_at
            """, eq['id'], eq['equipment_number'], eq['equipment_model_id'],
                eq['manufacturer'], eq['model_number'], eq['serial_number'],
                eq['equipment_type'], eq['location'], eq['department'],
                eq['criticality'], eq['owned_by_user_id'], eq['first_reported_by'],
                eq['machine_id'], eq['description'], eq['photo_file_id'],
                eq['installation_date'], eq['last_maintenance_date'],
                eq['work_order_count'], eq['total_downtime_hours'],
                eq['last_reported_fault'], eq['last_work_order_at'],
                eq['created_at'], eq['updated_at'])
        print(f"  ✓ Synced {len(equipment)} equipment records")

        # Sync work orders
        print("\nSyncing work orders...")
        work_orders = await neon.fetch("""
            SELECT id, work_order_number, user_id, telegram_username, created_by_agent,
                   source, equipment_id, equipment_number, manufacturer, model_number,
                   serial_number, equipment_type, machine_id, location, title, description,
                   fault_codes, symptoms, answer_text, confidence_score, route_taken,
                   suggested_actions, safety_warnings, cited_kb_atoms, manual_links,
                   status, priority, trace_id, conversation_id, research_triggered,
                   enrichment_triggered, created_at, updated_at, completed_at,
                   feedback_at, user_feedback
            FROM work_orders
        """)

        for wo in work_orders:
            await supabase.execute("""
                INSERT INTO work_orders (
                    id, work_order_number, user_id, telegram_username, created_by_agent,
                    source, equipment_id, equipment_number, manufacturer, model_number,
                    serial_number, equipment_type, machine_id, location, title, description,
                    fault_codes, symptoms, answer_text, confidence_score, route_taken,
                    suggested_actions, safety_warnings, cited_kb_atoms, manual_links,
                    status, priority, trace_id, conversation_id, research_triggered,
                    enrichment_triggered, created_at, updated_at, completed_at,
                    feedback_at, user_feedback
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                        $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28,
                        $29, $30, $31, $32, $33, $34, $35, $36)
                ON CONFLICT (work_order_number) DO UPDATE SET
                    status = EXCLUDED.status,
                    updated_at = EXCLUDED.updated_at,
                    completed_at = EXCLUDED.completed_at
            """, wo['id'], wo['work_order_number'], wo['user_id'], wo['telegram_username'],
                wo['created_by_agent'], wo['source'], wo['equipment_id'], wo['equipment_number'],
                wo['manufacturer'], wo['model_number'], wo['serial_number'], wo['equipment_type'],
                wo['machine_id'], wo['location'], wo['title'], wo['description'],
                wo['fault_codes'], wo['symptoms'], wo['answer_text'], wo['confidence_score'],
                wo['route_taken'], wo['suggested_actions'], wo['safety_warnings'],
                wo['cited_kb_atoms'], wo['manual_links'], wo['status'], wo['priority'],
                wo['trace_id'], wo['conversation_id'], wo['research_triggered'],
                wo['enrichment_triggered'], wo['created_at'], wo['updated_at'],
                wo['completed_at'], wo['feedback_at'], wo['user_feedback'])
        print(f"  ✓ Synced {len(work_orders)} work orders")

        # Sync manual cache
        print("\nSyncing manual cache...")
        manuals = await neon.fetch("""
            SELECT id, manufacturer, model, manual_url, pdf_stored, confidence_score,
                   found_via, created_at, updated_at, access_count, last_accessed,
                   manual_title, source, verified, found_at, llm_validated,
                   llm_confidence, validation_reasoning, manual_type, atom_id,
                   product_family_id, local_file_available, download_priority
            FROM manual_cache
        """)

        for m in manuals:
            await supabase.execute("""
                INSERT INTO manual_cache (
                    id, manufacturer, model, manual_url, pdf_stored, confidence_score,
                    found_via, created_at, updated_at, access_count, last_accessed,
                    manual_title, source, verified, found_at, llm_validated,
                    llm_confidence, validation_reasoning, manual_type, atom_id,
                    product_family_id, local_file_available, download_priority
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                        $16, $17, $18, $19, $20, $21, $22, $23)
                ON CONFLICT (id) DO UPDATE SET
                    access_count = EXCLUDED.access_count,
                    last_accessed = EXCLUDED.last_accessed,
                    updated_at = EXCLUDED.updated_at
            """, m['id'], m['manufacturer'], m['model'], m['manual_url'], m['pdf_stored'],
                m['confidence_score'], m['found_via'], m['created_at'], m['updated_at'],
                m['access_count'], m['last_accessed'], m['manual_title'], m['source'],
                m['verified'], m['found_at'], m['llm_validated'], m['llm_confidence'],
                m['validation_reasoning'], m['manual_type'], m['atom_id'],
                m['product_family_id'], m['local_file_available'], m['download_priority'])
        print(f"  ✓ Synced {len(manuals)} manual cache entries")

        await neon.close()
        await supabase.close()

        print("\n✓ Data sync completed successfully")
        return True

    except Exception as e:
        print(f"✗ Data sync failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_sync():
    """Verify sync was successful."""
    import asyncpg

    print("\n" + "="*60)
    print("STEP 3: Verification")
    print("="*60)

    supabase_url = os.getenv("SUPABASE_DB_URL")

    try:
        conn = await asyncpg.connect(supabase_url)

        # Count records
        users = await conn.fetchval("SELECT COUNT(*) FROM users")
        equipment = await conn.fetchval("SELECT COUNT(*) FROM cmms_equipment")
        work_orders = await conn.fetchval("SELECT COUNT(*) FROM work_orders")
        manuals = await conn.fetchval("SELECT COUNT(*) FROM manual_cache")

        print(f"\nSupabase now contains:")
        print(f"  Users: {users}")
        print(f"  Equipment: {equipment}")
        print(f"  Work Orders: {work_orders}")
        print(f"  Manual Cache: {manuals}")

        await conn.close()

        if equipment > 0:
            print("\n✓ Supabase is ready for failover!")
            return True
        else:
            print("\n⚠ No equipment synced - check Neon connection")
            return False

    except Exception as e:
        print(f"✗ Verification failed: {e}")
        return False


async def main():
    """Run full sync."""
    print("="*60)
    print("SUPABASE FAILOVER SYNC")
    print("="*60)

    args = sys.argv[1:]
    schema_only = "--schema" in args
    data_only = "--data" in args

    if schema_only:
        success = await run_schema_migration()
    elif data_only:
        success = await sync_data()
        if success:
            await verify_sync()
    else:
        # Full sync
        schema_ok = await run_schema_migration()
        if schema_ok:
            data_ok = await sync_data()
            if data_ok:
                await verify_sync()

    print("\n" + "="*60)
    print("SYNC COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
