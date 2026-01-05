"""
Database migration runner for Rivet Pro.
Runs all pending SQL migrations in order.

Usage:
    python run_migrations.py
"""

import asyncio
import sys
from pathlib import Path

# Add rivet_pro to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rivet_pro.infra.database import db
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)


async def main():
    """
    Run all pending database migrations.
    """
    print("=" * 80)
    print("Rivet Pro - Database Migration Runner")
    print("=" * 80)

    try:
        # Connect to database
        logger.info("Connecting to database...")
        await db.connect()

        # Run migrations
        logger.info("Running migrations...")
        await db.run_migrations()

        # Verify schema
        logger.info("Verifying schema...")
        async with db.acquire() as conn:
            # Check if schema_health view exists
            try:
                result = await conn.fetch("SELECT * FROM schema_health ORDER BY table_name")
                print("\n" + "=" * 80)
                print("Schema Health Check")
                print("=" * 80)
                for row in result:
                    print(f"{row['table_name']:30} | {row['row_count']:10} rows | {row['table_size']:15}")
                print("=" * 80)
            except Exception as e:
                logger.warning(f"Could not fetch schema_health view: {e}")

        print("\n✅ All migrations complete!")
        print("\nUnified schema ready:")
        print("- SaaS Layer: users, teams, subscription_limits")
        print("- Knowledge Base: manufacturers, equipment_models, manuals, manual_chunks, tech_notes")
        print("- CMMS Layer: cmms_equipment, work_orders, user_machines")
        print("- Tracking: interactions, manual_requests")
        print("\nNext step: python -m rivet_pro.main")

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        print(f"\n❌ Migration failed: {e}")
        print("\nCheck your .env file:")
        print("- DATABASE_URL should point to your Neon PostgreSQL instance")
        print("- Ensure the database exists and is accessible")
        sys.exit(1)

    finally:
        # Disconnect
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
