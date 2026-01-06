"""
Run migration 009: Knowledge Atoms and Gaps

Executes the migration SQL file against the Neon database.
"""

import asyncio
import asyncpg
import os
from pathlib import Path


async def run_migration():
    """Execute migration 009 on Neon database."""
    # Read migration file
    migration_file = Path("rivet_pro/migrations/009_knowledge_atoms.sql")

    if not migration_file.exists():
        print(f"[ERROR] Migration file not found: {migration_file}")
        return False

    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()

    # Get database URL
    db_url = os.getenv("NEON_DB_URL")
    if not db_url:
        print("[ERROR] NEON_DB_URL not found in environment")
        return False

    print(f"[*] Connecting to Neon database...")

    try:
        # Connect to database
        conn = await asyncpg.connect(db_url)

        print(f"[OK] Connected to database")
        print(f"[*] Executing migration 009_knowledge_atoms.sql...")

        # Execute migration
        await conn.execute(migration_sql)

        print(f"[OK] Migration executed successfully!")

        # Verify tables created
        print(f"\n[*] Verifying tables...")

        # Check knowledge_atoms table
        atoms_count = await conn.fetchval(
            "SELECT COUNT(*) FROM knowledge_atoms"
        )
        print(f"[OK] knowledge_atoms table exists ({atoms_count} rows)")

        # Check knowledge_gaps table
        gaps_count = await conn.fetchval(
            "SELECT COUNT(*) FROM knowledge_gaps"
        )
        print(f"[OK] knowledge_gaps table exists ({gaps_count} rows)")

        # Check pgvector extension
        vector_check = await conn.fetchval(
            "SELECT COUNT(*) FROM pg_extension WHERE extname='vector'"
        )
        if vector_check > 0:
            print(f"[OK] pgvector extension enabled")
        else:
            print(f"[WARN] pgvector extension not found")

        # Close connection
        await conn.close()

        print(f"\n[SUCCESS] Migration 009 complete!")
        return True

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        return False


if __name__ == "__main__":
    # Load .env
    from dotenv import load_dotenv
    load_dotenv()

    # Run migration
    success = asyncio.run(run_migration())

    if success:
        print("\n[SUCCESS] All migrations applied successfully!")
    else:
        print("\n[ERROR] Migration failed. Check errors above.")
