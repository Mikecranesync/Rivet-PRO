"""
Verify Knowledge Base tables exist and are properly configured.
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()


async def verify_tables():
    """Verify KB tables exist and check structure."""
    db_url = os.getenv("NEON_DB_URL")

    print("[*] Connecting to Neon database...")
    conn = await asyncpg.connect(db_url)
    print("[OK] Connected\n")

    # Check knowledge_atoms table
    print("[*] Checking knowledge_atoms table...")
    atoms_count = await conn.fetchval("SELECT COUNT(*) FROM knowledge_atoms")
    print(f"[OK] knowledge_atoms exists with {atoms_count} rows")

    # Check knowledge_gaps table
    print("\n[*] Checking knowledge_gaps table...")
    gaps_count = await conn.fetchval("SELECT COUNT(*) FROM knowledge_gaps")
    print(f"[OK] knowledge_gaps exists with {gaps_count} rows")

    # Check pgvector extension
    print("\n[*] Checking pgvector extension...")
    vector_check = await conn.fetchval(
        "SELECT COUNT(*) FROM pg_extension WHERE extname='vector'"
    )
    if vector_check > 0:
        print(f"[OK] pgvector extension is enabled")
    else:
        print(f"[ERROR] pgvector extension NOT found!")

    # Show sample atoms if any exist
    if atoms_count > 0:
        print(f"\n[*] Sample knowledge atoms:")
        sample_atoms = await conn.fetch(
            "SELECT atom_id, type, manufacturer, title FROM knowledge_atoms LIMIT 3"
        )
        for atom in sample_atoms:
            print(f"  - [{atom['type']}] {atom['manufacturer']}: {atom['title'][:50]}")

    # Show sample gaps if any exist
    if gaps_count > 0:
        print(f"\n[*] Sample knowledge gaps:")
        sample_gaps = await conn.fetch(
            "SELECT gap_id, query, manufacturer, priority FROM knowledge_gaps LIMIT 3"
        )
        for gap in sample_gaps:
            print(f"  - Priority {gap['priority']:.2f}: {gap['query'][:50]}... ({gap['manufacturer']})")

    await conn.close()
    print("\n[SUCCESS] All KB tables verified!")


if __name__ == "__main__":
    asyncio.run(verify_tables())
