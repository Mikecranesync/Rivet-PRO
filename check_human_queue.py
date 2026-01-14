"""
Check manual_hunter_queue for recent entries
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

NEON_DB_URL = os.getenv('NEON_DB_URL')

try:
    conn = psycopg2.connect(NEON_DB_URL)
    cursor = conn.cursor()

    print("="*80)
    print("CHECKING MANUAL HUNTER QUEUE (Human Review)")
    print("="*80)

    # Check total count
    cursor.execute("SELECT COUNT(*) FROM manual_hunter_queue")
    total = cursor.fetchone()[0]
    print(f"\nTotal entries in queue: {total}")

    # Check recent entries
    cursor.execute("""
        SELECT *
        FROM manual_hunter_queue
        ORDER BY created_at DESC
        LIMIT 10
    """)

    columns = [desc[0] for desc in cursor.description]
    recent = cursor.fetchall()

    if recent:
        print(f"\nMost recent {len(recent)} queue entries:")
        print("-"*80)

        for row in recent:
            print()
            for col, val in zip(columns, row):
                print(f"  {col}: {val}")
    else:
        print("\nNo entries in queue")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"[ERROR] {e}")
