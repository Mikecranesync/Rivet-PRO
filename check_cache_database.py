"""
Check manual_hunter_cache database for recent results
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

NEON_DB_URL = os.getenv('NEON_DB_URL')

if not NEON_DB_URL:
    print("[ERROR] NEON_DB_URL not found")
    exit(1)

print("="*80)
print("CHECKING MANUAL HUNTER CACHE DATABASE")
print("="*80)

try:
    conn = psycopg2.connect(NEON_DB_URL)
    cursor = conn.cursor()

    # Check total count
    cursor.execute("SELECT COUNT(*) FROM manual_hunter_cache")
    total = cursor.fetchone()[0]
    print(f"\nTotal cached manuals: {total}")

    # Check recent entries (last 10)
    cursor.execute("""
        SELECT
            manufacturer,
            model_number,
            pdf_url,
            confidence_score,
            search_tier,
            validation_score,
            validation_content_type,
            created_at
        FROM manual_hunter_cache
        ORDER BY created_at DESC
        LIMIT 10
    """)

    recent = cursor.fetchall()

    if recent:
        print(f"\nMost recent {len(recent)} entries:")
        print("-"*80)

        for row in recent:
            mfr, model, url, conf, tier, val_score, val_type, created = row
            print(f"\n{mfr} {model}")
            print(f"  URL: {url}")
            print(f"  Confidence: {conf}%")
            print(f"  Tier: {tier}")
            print(f"  Validation Score: {val_score}/10")
            print(f"  Content Type: {val_type}")
            print(f"  Created: {created}")
    else:
        print("\nNo entries in cache")

    # Check for test entries
    cursor.execute("""
        SELECT manufacturer, model_number, created_at
        FROM manual_hunter_cache
        WHERE manufacturer IN ('Caterpillar', 'John Deere', 'Bobcat', 'Komatsu', 'Hitachi')
        ORDER BY created_at DESC
        LIMIT 5
    """)

    test_entries = cursor.fetchall()

    if test_entries:
        print(f"\n\nTest Equipment Entries Found ({len(test_entries)}):")
        for mfr, model, created in test_entries:
            print(f"  {mfr} {model} - {created}")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"[ERROR] {e}")
