import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL
db_url = os.getenv('NEON_DB_URL') or os.getenv('DATABASE_URL')

print("Connecting to Neon database...")
print(f"Database: {db_url.split('@')[1].split('/')[0]}")

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # Read the migration file
    print("\nReading migration file...")
    with open('rivet_pro/migrations/010_ralph_system.sql', 'r', encoding='utf-8') as f:
        migration_sql = f.read()

    print("Executing migration...")
    cur.execute(migration_sql)
    conn.commit()

    print("\n[SUCCESS] Migration executed!")

    # Verify tables
    print("\nVerifying tables...")
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_name LIKE 'ralph_%'
        ORDER BY table_name;
    """)
    tables = cur.fetchall()

    print(f"\nFound {len(tables)} tables:")
    for table in tables:
        print(f"  - {table[0]}")

    # Verify stories
    print("\nVerifying stories...")
    cur.execute("SELECT COUNT(*) FROM ralph_stories;")
    count = cur.fetchone()[0]
    print(f"Found {count} stories")

    if count == 5:
        cur.execute("SELECT story_id, ai_model FROM ralph_stories ORDER BY priority;")
        stories = cur.fetchall()
        print("\nStories:")
        for story in stories:
            print(f"  {story[0]}: {story[1]}")

    cur.close()
    conn.close()

    print("\n[SUCCESS] Database is ready for RALPH!")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
