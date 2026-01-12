#!/usr/bin/env python3
"""
Create Manual Hunter database tables in Neon PostgreSQL
Run: python create_manual_hunter_tables.py
"""

import os
import sys
from pathlib import Path

# Add rivet to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    print("❌ psycopg2 not installed. Installing now...")
    os.system("pip install psycopg2-binary")
    import psycopg2
    from psycopg2 import sql

# Database connection from .env
DATABASE_URL = "postgresql://neondb_owner:npg_c3UNa4KOlCeL@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require"

def create_tables():
    """Create manual_cache and manual_requests tables"""

    print("[*] Connecting to Neon PostgreSQL...")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        print("[OK] Connected to database")

        # Create manual_cache table
        print("\n[*] Creating manual_cache table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS manual_cache (
                id SERIAL PRIMARY KEY,

                -- Equipment Identification
                manufacturer VARCHAR(255) NOT NULL,
                model VARCHAR(255) NOT NULL,

                -- Manual Information
                manual_url TEXT NOT NULL,
                pdf_stored BOOLEAN DEFAULT FALSE,
                confidence_score DECIMAL(3,2),
                found_via VARCHAR(50),

                -- Metadata
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP,

                -- Constraints
                UNIQUE(manufacturer, model)
            );
        """)

        print("   [OK] manual_cache table created")

        # Create indexes for manual_cache
        print("   [*] Creating indexes for manual_cache...")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_manual_cache_lookup
                ON manual_cache(manufacturer, model);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_manual_cache_confidence
                ON manual_cache(confidence_score);
        """)
        print("   [OK] Indexes created")

        # Create manual_requests table
        print("\n[*] Creating manual_requests table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS manual_requests (
                id SERIAL PRIMARY KEY,

                -- Equipment Identification
                manufacturer VARCHAR(255) NOT NULL,
                model VARCHAR(255) NOT NULL,
                serial_number VARCHAR(255),
                equipment_type VARCHAR(100),

                -- Requester Information
                requester_telegram_id BIGINT NOT NULL,
                requester_username VARCHAR(255),
                photo_file_id VARCHAR(255),

                -- Search History
                search_attempts JSONB,

                -- Status Tracking
                status VARCHAR(50) DEFAULT 'pending',
                assigned_to VARCHAR(255),
                resolution_notes TEXT,
                manual_url TEXT,

                -- Metadata
                created_at TIMESTAMP DEFAULT NOW(),
                resolved_at TIMESTAMP,
                response_time_hours DECIMAL(5,2)
            );
        """)

        print("   [OK] manual_requests table created")

        # Create indexes for manual_requests
        print("   [*] Creating indexes for manual_requests...")
        try:
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_manual_requests_status
                    ON manual_requests(status);
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_manual_requests_requester
                    ON manual_requests(requester_telegram_id);
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_manual_requests_created
                    ON manual_requests(created_at DESC);
            """)
            print("   [OK] Indexes created")
        except psycopg2.Error as idx_err:
            print(f"   [WARNING] Index creation issue (may already exist): {idx_err}")
            conn.rollback()  # Rollback this transaction
            conn.commit()  # Try to commit what we have

        # Commit changes
        conn.commit()

        # Verify tables exist
        print("\n[*] Verifying tables...")
        cur.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename LIKE 'manual_%'
            ORDER BY tablename;
        """)

        tables = cur.fetchall()

        if len(tables) == 2:
            print("[SUCCESS] Tables verified:")
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print(f"[WARNING] Expected 2 tables, found {len(tables)}")

        # Get table details
        print("\n[*] Table Details:")

        for table_name in ['manual_cache', 'manual_requests']:
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
            """, (table_name,))

            columns = cur.fetchall()
            print(f"\n   {table_name} ({len(columns)} columns):")
            for col in columns[:5]:  # Show first 5 columns
                print(f"      - {col[0]}: {col[1]}")
            if len(columns) > 5:
                print(f"      ... and {len(columns) - 5} more")

        cur.close()
        conn.close()

        print("\n" + "="*60)
        print("[SUCCESS] MANUAL HUNTER DATABASE SETUP COMPLETE")
        print("="*60)
        print("\nNext steps:")
        print("1. Configure DeepSeek credential in n8n")
        print("2. Import Manual Hunter workflow JSON")
        print("3. Test with: Siemens S7-1200 PLC")
        print("\nGuide: C:\\Users\\hharp\\Downloads\\TAB3_MANUAL_HUNTER_DEPLOYMENT.md")

        return True

    except psycopg2.Error as e:
        print(f"\n[ERROR] Database error: {e}")
        return False

    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("MANUAL HUNTER - DATABASE TABLE CREATION")
    print("="*60)
    print()

    success = create_tables()

    if success:
        sys.exit(0)
    else:
        sys.exit(1)
