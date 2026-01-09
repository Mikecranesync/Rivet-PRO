#!/usr/bin/env python3
"""
Create Manual Hunter database tables in Neon PostgreSQL
Drops existing tables if they exist to ensure clean schema
Run: python create_manual_hunter_tables_v2.py
"""

import os
import sys
from pathlib import Path

try:
    import psycopg2
except ImportError:
    print("[*] Installing psycopg2...")
    os.system("pip install psycopg2-binary")
    import psycopg2

# Database connection from .env
DATABASE_URL = "postgresql://neondb_owner:npg_c3UNa4KOlCeL@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require"

def create_tables():
    """Create manual_cache and manual_requests tables"""

    print("[*] Connecting to Neon PostgreSQL...")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        print("[OK] Connected to database\n")

        # Check for existing tables
        print("[*] Checking for existing Manual Hunter tables...")
        cur.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename IN ('manual_cache', 'manual_requests');
        """)
        existing = [row[0] for row in cur.fetchall()]

        if existing:
            print(f"[WARNING] Found existing tables: {', '.join(existing)}")
            print("[*] Dropping existing tables to ensure clean schema...")

            cur.execute("DROP TABLE IF EXISTS manual_requests CASCADE;")
            cur.execute("DROP TABLE IF EXISTS manual_cache CASCADE;")
            conn.commit()
            print("[OK] Existing tables dropped\n")
        else:
            print("[OK] No existing tables found\n")

        # Create manual_cache table
        print("[*] Creating manual_cache table...")
        cur.execute("""
            CREATE TABLE manual_cache (
                id SERIAL PRIMARY KEY,
                manufacturer VARCHAR(255) NOT NULL,
                model VARCHAR(255) NOT NULL,
                manual_url TEXT NOT NULL,
                pdf_stored BOOLEAN DEFAULT FALSE,
                confidence_score DECIMAL(3,2),
                found_via VARCHAR(50),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP,
                UNIQUE(manufacturer, model)
            );
        """)
        print("   [OK] manual_cache table created")

        # Create indexes for manual_cache
        print("   [*] Creating indexes...")
        cur.execute("""
            CREATE INDEX idx_manual_cache_lookup
                ON manual_cache(manufacturer, model);
        """)
        cur.execute("""
            CREATE INDEX idx_manual_cache_confidence
                ON manual_cache(confidence_score);
        """)
        print("   [OK] Indexes created\n")

        # Create manual_requests table
        print("[*] Creating manual_requests table...")
        cur.execute("""
            CREATE TABLE manual_requests (
                id SERIAL PRIMARY KEY,
                manufacturer VARCHAR(255) NOT NULL,
                model VARCHAR(255) NOT NULL,
                serial_number VARCHAR(255),
                equipment_type VARCHAR(100),
                requester_telegram_id BIGINT NOT NULL,
                requester_username VARCHAR(255),
                photo_file_id VARCHAR(255),
                search_attempts JSONB,
                status VARCHAR(50) DEFAULT 'pending',
                assigned_to VARCHAR(255),
                resolution_notes TEXT,
                manual_url TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                resolved_at TIMESTAMP,
                response_time_hours DECIMAL(5,2)
            );
        """)
        print("   [OK] manual_requests table created")

        # Create indexes for manual_requests
        print("   [*] Creating indexes...")
        cur.execute("""
            CREATE INDEX idx_manual_requests_status
                ON manual_requests(status);
        """)
        cur.execute("""
            CREATE INDEX idx_manual_requests_requester
                ON manual_requests(requester_telegram_id);
        """)
        cur.execute("""
            CREATE INDEX idx_manual_requests_created
                ON manual_requests(created_at DESC);
        """)
        print("   [OK] Indexes created\n")

        # Commit all changes
        conn.commit()

        # Verify tables
        print("[*] Verifying tables...")
        cur.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename LIKE 'manual_%'
            ORDER BY tablename;
        """)

        tables = cur.fetchall()
        print(f"[OK] Found {len(tables)} tables:")
        for table in tables:
            print(f"   - {table[0]}")

        # Show column counts
        print("\n[*] Table schemas:")
        for table_name in ['manual_cache', 'manual_requests']:
            cur.execute("""
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_name = %s;
            """, (table_name,))
            col_count = cur.fetchone()[0]
            print(f"   - {table_name}: {col_count} columns")

        cur.close()
        conn.close()

        print("\n" + "="*60)
        print("[SUCCESS] MANUAL HUNTER DATABASE SETUP COMPLETE")
        print("="*60)
        print("\nTables created:")
        print("  - manual_cache (equipment manual cache)")
        print("  - manual_requests (human queue for failed searches)")
        print("\nNext steps:")
        print("  1. Configure DeepSeek credential in n8n")
        print("  2. Import Manual Hunter workflow JSON")
        print("  3. Test with: Siemens S7-1200 PLC")
        print("\nGuide: C:\\Users\\hharp\\Downloads\\TAB3_MANUAL_HUNTER_DEPLOYMENT.md")

        return True

    except psycopg2.Error as e:
        print(f"\n[ERROR] Database error: {e}")
        if conn:
            conn.rollback()
        return False

    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("MANUAL HUNTER - DATABASE TABLE CREATION (V2)")
    print("="*60)
    print()

    success = create_tables()

    if success:
        sys.exit(0)
    else:
        sys.exit(1)
