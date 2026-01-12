"""
Run database schema update on Neon
Adds validation columns to manual_hunter_cache table
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

NEON_DB_URL = os.getenv('NEON_DB_URL')

if not NEON_DB_URL:
    print("[ERROR] NEON_DB_URL not found in .env")
    exit(1)

print("="*80)
print("UPDATING MANUAL HUNTER CACHE SCHEMA")
print("="*80)

# Read SQL file
with open('update_db_schema.sql', 'r') as f:
    sql_script = f.read()

print("\n[1/3] Connecting to Neon database...")

try:
    conn = psycopg2.connect(NEON_DB_URL)
    cursor = conn.cursor()
    print("       [OK] Connected to Neon")

    print("\n[2/3] Executing schema update...")

    # Split SQL script into separate statements
    statements = sql_script.split(';')

    for i, statement in enumerate(statements):
        statement = statement.strip()
        if statement:
            print(f"       Executing statement {i+1}...")
            cursor.execute(statement)

    conn.commit()
    print("       [OK] Schema updated")

    print("\n[3/3] Verifying columns...")

    cursor.execute("""
        SELECT column_name, data_type, column_default
        FROM information_schema.columns
        WHERE table_name = 'manual_hunter_cache'
        AND column_name IN ('validation_score', 'validation_content_type', 'validated_at')
    """)

    columns = cursor.fetchall()

    if len(columns) == 3:
        print("       [OK] All validation columns added:")
        for col_name, col_type, col_default in columns:
            print(f"         - {col_name} ({col_type}) DEFAULT {col_default}")
    else:
        print(f"       [WARNING] Expected 3 columns, found {len(columns)}")

    cursor.close()
    conn.close()

    print("\n" + "="*80)
    print("DATABASE SCHEMA UPDATE COMPLETE")
    print("="*80)
    print("\nNext step: Test the integrated workflow with equipment data")

except Exception as e:
    print(f"\n[ERROR] Failed to update schema: {e}")
    if 'conn' in locals():
        conn.rollback()
        conn.close()
    exit(1)
