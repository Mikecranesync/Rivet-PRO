"""
Test KB-001 Schema and Bidirectional Linking
Run on VPS after deployment

Tests:
1. Schema columns exist (last_used_at, source_type, source_id, source_interaction_id)
2. Interactions columns exist (atom_id, atom_created)
3. Create test user
4. Create interaction -> atom flow with bidirectional linking
5. Verify bidirectional link works correctly
6. Cleanup test data
"""
import asyncio
import asyncpg
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from rivet_pro.config.settings import settings

async def test_kb001():
    """Test KB-001 implementation"""
    conn = await asyncpg.connect(settings.database_url)

    print("=" * 60)
    print("KB-001 Schema & Linking Test")
    print("=" * 60)

    try:
        # Test 1: Verify schema columns exist
        print("\n[1/6] Checking knowledge_atoms schema...")
        cols = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'knowledge_atoms'
            AND column_name IN ('last_used_at', 'source_type', 'source_id', 'source_interaction_id')
            ORDER BY column_name
        """)

        expected = {'last_used_at', 'source_type', 'source_id', 'source_interaction_id'}
        found = {c['column_name'] for c in cols}

        if found == expected:
            print(f"✓ All columns exist: {', '.join(sorted(found))}")
            for col in cols:
                print(f"  - {col['column_name']}: {col['data_type']}")
        else:
            missing = expected - found
            print(f"✗ Missing columns: {', '.join(missing)}")
            return False

        # Test 2: Check interactions schema
        print("\n[2/6] Checking interactions schema...")
        int_cols = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'interactions'
            AND column_name IN ('atom_id', 'atom_created')
        """)

        if len(int_cols) == 2:
            print("✓ Interactions columns exist:")
            for col in int_cols:
                print(f"  - {col['column_name']}: {col['data_type']}")
        else:
            print("✗ Missing interactions columns")
            return False

        # Test 3: Create test user
        print("\n[3/6] Creating test data...")
        user_id = await conn.fetchval("""
            INSERT INTO users (telegram_id, full_name)
            VALUES (999888777, 'KB Test User')
            ON CONFLICT (telegram_id) DO UPDATE SET full_name='KB Test User'
            RETURNING id
        """)
        print(f"✓ Test user created/updated: {user_id}")

        # Test 4: Create interaction -> atom flow
        print("\n[4/6] Testing interaction -> atom bidirectional flow...")

        # Create interaction first
        interaction_id = await conn.fetchval("""
            INSERT INTO interactions (user_id, interaction_type, outcome)
            VALUES ($1, 'manual_lookup', 'manual_delivered')
            RETURNING id
        """, user_id)
        print(f"✓ Interaction created: {interaction_id}")

        # Create atom with source_interaction_id
        atom_id = await conn.fetchval("""
            INSERT INTO knowledge_atoms (
                atom_id, atom_type, title, summary, content,
                manufacturer, model, difficulty, source_document, source_pages,
                confidence, source_type, source_id,
                source_interaction_id, last_used_at, created_by, human_verified
            )
            VALUES (
                gen_random_uuid()::text, 'specification', 'Test Atom', 'Test Summary', 'Test content for KB-001',
                'TestManufacturer', 'TestModel-X', 'beginner', 'test_kb_001', ARRAY[]::integer[],
                0.8, 'test', $1, $2, NOW(), 'system', false
            )
            RETURNING atom_id
        """, str(user_id), interaction_id)
        print(f"✓ Atom created: {atom_id}")

        # Link interaction to atom (bidirectional)
        await conn.execute("""
            UPDATE interactions
            SET atom_id = $1, atom_created = TRUE
            WHERE id = $2
        """, atom_id, interaction_id)
        print("✓ Bidirectional link established")

        # Test 5: Verify bidirectional link
        print("\n[5/6] Verifying bidirectional link...")
        link = await conn.fetchrow("""
            SELECT
                i.id as interaction_id,
                i.atom_id as interaction_to_atom,
                i.atom_created,
                ka.atom_id as atom_id,
                ka.source_interaction_id as atom_to_interaction,
                ka.source_type,
                ka.last_used_at
            FROM interactions i
            JOIN knowledge_atoms ka ON i.atom_id = ka.atom_id
            WHERE i.id = $1
        """, interaction_id)

        if link:
            # Check all expected values
            checks = [
                (link['interaction_to_atom'] == atom_id, "Interaction links to atom"),
                (link['atom_to_interaction'] == interaction_id, "Atom links back to interaction"),
                (link['atom_created'] == True, "atom_created flag is TRUE"),
                (link['source_type'] == 'test', "source_type is correct"),
                (link['last_used_at'] is not None, "last_used_at is populated")
            ]

            all_passed = True
            for check, description in checks:
                if check:
                    print(f"  ✓ {description}")
                else:
                    print(f"  ✗ {description}")
                    all_passed = False

            if not all_passed:
                print("\n✗ Some bidirectional link checks failed")
                print(f"Link data: {dict(link)}")
                return False

            print(f"\n✓ Complete bidirectional link verified:")
            print(f"  Interaction {interaction_id} -> Atom {atom_id}")
            print(f"  Atom {atom_id} -> Interaction {interaction_id}")
            print(f"  Source: {link['source_type']}")
            print(f"  Last used: {link['last_used_at']}")
        else:
            print("✗ No link found in database - JOIN failed")
            return False

        # Test 6: Cleanup
        print("\n[6/6] Cleaning up test data...")
        # Break circular FK by nulling out references first
        await conn.execute(
            "UPDATE interactions SET atom_id = NULL WHERE id = $1",
            interaction_id
        )
        await conn.execute(
            "UPDATE knowledge_atoms SET source_interaction_id = NULL WHERE atom_id = $1",
            atom_id
        )
        # Now delete both
        deleted_interactions = await conn.execute(
            "DELETE FROM interactions WHERE id = $1",
            interaction_id
        )
        deleted_atoms = await conn.execute(
            "DELETE FROM knowledge_atoms WHERE atom_id = $1",
            atom_id
        )
        print(f"✓ Cleaned up: atom {atom_id}, interaction {interaction_id}")

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED - KB-001 IMPLEMENTATION SUCCESSFUL")
        print("=" * 60)
        print("\nBidirectional linking is working correctly:")
        print("  • Interactions can create atoms")
        print("  • Atoms track their source interaction")
        print("  • Both directions of the link are maintained")
        print("  • New columns are populated correctly")
        return True

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await conn.close()

if __name__ == "__main__":
    success = asyncio.run(test_kb001())
    sys.exit(0 if success else 1)
