"""
Test Atlas Database Adapter

Verifies:
- Connection to Neon PostgreSQL
- Basic query execution
- Dict-based results
- Agent Factory compatible interface
"""

import asyncio
from rivet.atlas.database import AtlasDatabase


async def test_database():
    """Test database connection and basic operations."""
    print("=" * 60)
    print("Testing Atlas Database Adapter")
    print("=" * 60)

    db = AtlasDatabase()

    try:
        # Test 1: Connection
        print("\n[TEST 1] Connecting to database...")
        await db.connect()
        print("[OK] Connected successfully")

        # Test 2: Basic SELECT 1
        print("\n[TEST 2] Running SELECT 1...")
        result = await db.execute("SELECT 1 AS test")
        print(f"[OK] Result: {result}")
        assert result == [{"test": 1}], f"Expected [{{'test': 1}}], got {result}"

        # Test 3: Agent Factory compatible interface
        print("\n[TEST 3] Testing execute_query_async (Agent Factory interface)...")
        result = await db.execute_query_async("SELECT $1 AS message", ("Hello Atlas!",))
        print(f"[OK] Result: {result}")
        assert result == [{"message": "Hello Atlas!"}]

        # Test 4: Check if cmms_equipment table exists
        print("\n[TEST 4] Checking if cmms_equipment table exists...")
        result = await db.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'cmms_equipment'
            )
        """)
        table_exists = result[0]["exists"]
        print(f"[{'OK' if table_exists else 'WARNING'}] cmms_equipment table exists: {table_exists}")

        # Test 5: Check if work_orders table exists
        print("\n[TEST 5] Checking if work_orders table exists...")
        result = await db.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'work_orders'
            )
        """)
        table_exists = result[0]["exists"]
        print(f"[{'OK' if table_exists else 'WARNING'}] work_orders table exists: {table_exists}")

        # Test 6: Check if user_machines table exists
        print("\n[TEST 6] Checking if user_machines table exists...")
        result = await db.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'user_machines'
            )
        """)
        table_exists = result[0]["exists"]
        print(f"[{'OK' if table_exists else 'WARNING'}] user_machines table exists: {table_exists}")

        # Test 7: fetch_one convenience method
        print("\n[TEST 7] Testing fetch_one...")
        result = await db.fetch_one("SELECT 'test_value' AS col1, 42 AS col2")
        print(f"[OK] Result: {result}")
        assert result == {"col1": "test_value", "col2": 42}

        # Test 8: fetch_all convenience method
        print("\n[TEST 8] Testing fetch_all...")
        result = await db.fetch_all("SELECT generate_series(1, 3) AS num")
        print(f"[OK] Result: {result}")
        assert len(result) == 3
        assert result[0]["num"] == 1

        print("\n" + "=" * 60)
        print("[SUCCESS] All database tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await db.close()
        print("\n[CLEANUP] Database connection closed")

    return True


if __name__ == "__main__":
    success = asyncio.run(test_database())
    exit(0 if success else 1)
