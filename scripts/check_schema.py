"""
Check existing knowledge_atoms schema.
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()


async def check_schema():
    """Check knowledge_atoms schema."""
    db_url = os.getenv("NEON_DB_URL")

    conn = await asyncpg.connect(db_url)

    # Get column info
    schema_info = await conn.fetch("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'knowledge_atoms'
        ORDER BY ordinal_position
    """)

    print("[*] knowledge_atoms schema:")
    for col in schema_info:
        print(f"  {col['column_name']}: {col['data_type']} {'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(check_schema())
