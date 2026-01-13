#!/usr/bin/env python3
"""Check database schema."""

import asyncio
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rivet_pro.infra.database import Database


async def check_schema():
    """Check knowledge_atoms table schema."""
    db = Database()

    try:
        await db.connect()
        print("Connected to database\n")

        # Check atom_id column type
        columns = await db.fetch("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'knowledge_atoms'
                AND column_name = 'atom_id'
        """)

        if columns:
            col = columns[0]
            print(f"atom_id column type: {col['data_type']}")
            if col['character_maximum_length']:
                print(f"Max length: {col['character_maximum_length']}")
        else:
            print("atom_id column not found")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1

    finally:
        await db.disconnect()


if __name__ == "__main__":
    exit_code = asyncio.run(check_schema())
    sys.exit(exit_code)
