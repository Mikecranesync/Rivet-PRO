import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL
db_url = os.getenv('NEON_DB_URL') or os.getenv('DATABASE_URL')

print("Verifying RALPH Database Setup...\n")

try:
    # Connect to database
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # Check tables exist
    print("=" * 60)
    print("1. Checking Tables")
    print("=" * 60)
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_name LIKE 'ralph_%'
        ORDER BY table_name;
    """)
    tables = cur.fetchall()

    if len(tables) == 4:
        print("[OK] All 4 tables exist:")
        for table in tables:
            print(f"   - {table[0]}")
    else:
        print(f"[ERROR] Expected 4 tables, found {len(tables)}")
        for table in tables:
            print(f"   - {table[0]}")

    # Check stories
    print("\n" + "=" * 60)
    print("2. Checking Stories")
    print("=" * 60)
    cur.execute("""
        SELECT story_id, ai_model, status, priority
        FROM ralph_stories
        ORDER BY priority;
    """)
    stories = cur.fetchall()

    if len(stories) == 5:
        print("[OK] All 5 stories exist:\n")
        print(f"{'Story ID':<12} {'AI Model':<30} {'Status':<8} {'Priority'}")
        print("-" * 70)
        for story in stories:
            print(f"{story[0]:<12} {story[1]:<30} {story[2]:<8} {story[3]}")

        # Check model distribution
        sonnet_count = sum(1 for s in stories if 'sonnet-4' in s[1])
        haiku_count = sum(1 for s in stories if 'haiku' in s[1])

        print("\nModel Distribution:")
        print(f"   Sonnet 4: {sonnet_count} stories (RIVET-001, 002, 003)")
        print(f"   Haiku:    {haiku_count} stories (RIVET-004, 005)")

        if sonnet_count == 3 and haiku_count == 2:
            print("   [OK] Correct model distribution!")
        else:
            print("   [ERROR] Incorrect model distribution!")

    else:
        print(f"[ERROR] Expected 5 stories, found {len(stories)}")
        for story in stories:
            print(f"   {story[0]} - {story[1]}")

    # Check project
    print("\n" + "=" * 60)
    print("3. Checking Project")
    print("=" * 60)
    cur.execute("SELECT * FROM ralph_projects;")
    projects = cur.fetchall()

    if len(projects) == 1:
        project = projects[0]
        print("[OK] Project exists:")
        print(f"   ID: {project[0]}")
        print(f"   Name: {project[1]}")
        print(f"   Max Iterations: {project[2]}")
        print(f"   Token Budget: {project[3]:,}")
        print(f"   Telegram Chat ID: {project[4]}")

        if project[4] == '8445149012':
            print("   [OK] Correct Telegram Chat ID!")
        else:
            print(f"   [ERROR] Wrong Chat ID: {project[4]} (expected: 8445149012)")
    else:
        print(f"[ERROR] Expected 1 project, found {len(projects)}")

    # Check indexes
    print("\n" + "=" * 60)
    print("4. Checking Indexes")
    print("=" * 60)
    cur.execute("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename LIKE 'ralph_%'
        ORDER BY indexname;
    """)
    indexes = cur.fetchall()

    print(f"[OK] Found {len(indexes)} indexes:")
    for idx in indexes:
        print(f"   - {idx[0]}")

    # Final summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    all_good = (
        len(tables) == 4 and
        len(stories) == 5 and
        len(projects) == 1 and
        sum(1 for s in stories if 'sonnet-4' in s[1]) == 3 and
        sum(1 for s in stories if 'haiku' in s[1]) == 2 and
        projects[0][4] == '8445149012'
    )

    if all_good:
        print("[SUCCESS] ALL CHECKS PASSED! Database is ready for RALPH.")
        print("\nNext step: Configure n8n workflows")
    else:
        print("[WARNING] Some checks failed. Review output above.")

    cur.close()
    conn.close()

except Exception as e:
    print(f"[ERROR] Database connection error: {e}")
    print("\nTroubleshooting:")
    print("1. Check DATABASE_URL or NEON_DB_URL in .env")
    print("2. Verify network connection to Neon")
    print("3. Confirm migration ran successfully")
