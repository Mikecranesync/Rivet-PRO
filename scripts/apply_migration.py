#!/usr/bin/env python3
"""
Apply database migration script.
Usage: python scripts/apply_migration.py rivet_pro/migrations/017_manual_matching.sql
"""

import asyncio
import sys
from pathlib import Path

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rivet_pro.infra.database import Database
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)


async def apply_migration(migration_file: Path):
    """Apply SQL migration file to database."""
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return 1

    print(f"📄 Reading migration: {migration_file.name}")
    sql = migration_file.read_text(encoding='utf-8')

    print("🔌 Connecting to database...")
    db = Database()

    try:
        await db.connect()
        print("✅ Connected to database")

        print(f"🚀 Applying migration: {migration_file.name}")

        # Execute migration in a transaction
        async with db.acquire() as conn:
            async with conn.transaction():
                await conn.execute(sql)

        print(f"✅ Migration applied successfully: {migration_file.name}")

        # Verify tables were created
        print("\n📊 Verifying tables...")
        tables = await db.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
                AND table_name IN ('equipment_manual_searches', 'manual_cache')
        """)

        for table in tables:
            print(f"  ✅ Table exists: {table['table_name']}")

        # Check manual_cache columns
        columns = await db.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'manual_cache'
                AND column_name IN ('llm_validated', 'llm_confidence', 'manual_type', 'atom_id')
        """)

        print(f"\n  ✅ manual_cache extended with {len(columns)} new columns:")
        for col in columns:
            print(f"     - {col['column_name']} ({col['data_type']})")

        return 0

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        print(f"\n❌ Migration failed: {e}")
        return 1

    finally:
        await db.disconnect()
        print("\n🔌 Database connection closed")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/apply_migration.py <migration_file>")
        print("Example: python scripts/apply_migration.py rivet_pro/migrations/017_manual_matching.sql")
        sys.exit(1)

    migration_file = Path(sys.argv[1])
    exit_code = asyncio.run(apply_migration(migration_file))
    sys.exit(exit_code)
