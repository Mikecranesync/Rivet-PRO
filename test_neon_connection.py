"""
Test the EXACT connection n8n should be using to Neon
"""
import psycopg2

# EXACT settings from your n8n "Postgres account 3" credential
HOST = "ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech"
DATABASE = "neondb"
USER = "neondb_owner"
PASSWORD = "npg_c3UNa4KOlCeL"
PORT = 5432

print("="*60)
print("TESTING NEON CONNECTION")
print("="*60)
print(f"Host: {HOST}")
print(f"Database: {DATABASE}")
print(f"User: {USER}")
print(f"Port: {PORT}")
print()

try:
    # Connect with SSL (same as n8n)
    conn = psycopg2.connect(
        host=HOST,
        database=DATABASE,
        user=USER,
        password=PASSWORD,
        port=PORT,
        sslmode='require'
    )
    cur = conn.cursor()

    print("[OK] Connection successful!")
    print()

    # Test 1: Check current database
    print("Test 1: Current database")
    cur.execute("SELECT current_database(), current_schema();")
    db, schema = cur.fetchone()
    print(f"  Database: {db}")
    print(f"  Schema: {schema}")
    print()

    # Test 2: List ralph tables
    print("Test 2: Ralph tables in public schema")
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name LIKE 'ralph_%'
        ORDER BY table_name;
    """)
    tables = cur.fetchall()
    print(f"  Found {len(tables)} tables:")
    for table in tables:
        print(f"    - {table[0]}")
    print()

    # Test 3: Try the EXACT INSERT that n8n is doing
    print("Test 3: Running n8n's INSERT query")
    query = "INSERT INTO ralph_executions (project_id, status) VALUES (1, 'running') RETURNING id"
    print(f"  Query: {query}")

    try:
        cur.execute(query)
        result = cur.fetchone()
        execution_id = result[0]
        print(f"  [SUCCESS] Inserted! Execution ID: {execution_id}")

        # Clean up - delete the test execution
        cur.execute(f"DELETE FROM ralph_executions WHERE id = {execution_id}")
        conn.commit()
        print(f"  [CLEANUP] Deleted test execution {execution_id}")

    except Exception as e:
        print(f"  [ERROR] INSERT failed: {e}")
        conn.rollback()

    print()

    # Test 4: Check if ralph_executions table exists in current schema
    print("Test 4: Check ralph_executions directly")
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename = 'ralph_executions'
        );
    """)
    exists = cur.fetchone()[0]
    print(f"  ralph_executions exists in public schema: {exists}")

    if exists:
        cur.execute("SELECT COUNT(*) FROM ralph_executions;")
        count = cur.fetchone()[0]
        print(f"  Row count: {count}")

    print()

    # Test 5: Check search_path
    print("Test 5: Check search_path")
    cur.execute("SHOW search_path;")
    search_path = cur.fetchone()[0]
    print(f"  search_path: {search_path}")

    if 'public' not in search_path:
        print("  [WARNING] 'public' not in search_path!")
        print("  This might be why n8n can't find the tables")

    print()

    # Test 6: Try INSERT with explicit schema
    print("Test 6: INSERT with explicit schema (public.ralph_executions)")
    query_explicit = "INSERT INTO public.ralph_executions (project_id, status) VALUES (1, 'running') RETURNING id"

    try:
        cur.execute(query_explicit)
        result = cur.fetchone()
        execution_id = result[0]
        print(f"  [SUCCESS] Inserted! Execution ID: {execution_id}")

        # Clean up
        cur.execute(f"DELETE FROM public.ralph_executions WHERE id = {execution_id}")
        conn.commit()
        print(f"  [CLEANUP] Deleted test execution {execution_id}")

    except Exception as e:
        print(f"  [ERROR] INSERT failed: {e}")
        conn.rollback()

    print()
    print("="*60)
    print("DIAGNOSIS COMPLETE")
    print("="*60)

    cur.close()
    conn.close()

except psycopg2.OperationalError as e:
    print(f"[ERROR] Connection failed: {e}")
    print()
    print("Possible issues:")
    print("1. Wrong host, database, user, or password")
    print("2. SSL/TLS connection issue")
    print("3. Network/firewall blocking connection")
    print("4. Neon database is down or suspended")

except Exception as e:
    print(f"[ERROR] Unexpected error: {e}")
    import traceback
    traceback.print_exc()
