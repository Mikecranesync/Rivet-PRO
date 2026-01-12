"""
Check actual manual_hunter_cache table schema
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

NEON_DB_URL = os.getenv('NEON_DB_URL')

try:
    conn = psycopg2.connect(NEON_DB_URL)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT column_name, data_type, column_default, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'manual_hunter_cache'
        ORDER BY ordinal_position
    """)

    columns = cursor.fetchall()

    print("="*80)
    print("MANUAL_HUNTER_CACHE TABLE SCHEMA")
    print("="*80)

    if columns:
        print(f"\nFound {len(columns)} columns:\n")
        for col_name, col_type, col_default, nullable in columns:
            default_str = f"DEFAULT {col_default}" if col_default else ""
            null_str = "NULL" if nullable == 'YES' else "NOT NULL"
            print(f"  {col_name:30} {col_type:20} {null_str:10} {default_str}")
    else:
        print("\n[WARNING] Table not found or has no columns")

    # Check if table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_name = 'manual_hunter_cache'
        )
    """)
    exists = cursor.fetchone()[0]
    print(f"\nTable 'manual_hunter_cache' exists: {exists}")

    # List all tables to see what's available
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)

    tables = cursor.fetchall()
    print(f"\nAll tables in database ({len(tables)}):")
    for table in tables:
        print(f"  - {table[0]}")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"[ERROR] {e}")
