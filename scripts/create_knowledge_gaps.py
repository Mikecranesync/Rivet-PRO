"""
Create knowledge_gaps table (missing from migration).
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()


async def create_gaps_table():
    """Create knowledge_gaps table."""
    db_url = os.getenv("NEON_DB_URL")

    print("[*] Connecting to Neon database...")
    conn = await asyncpg.connect(db_url)
    print("[OK] Connected\n")

    # Create knowledge_gaps table SQL
    gaps_sql = """
    -- Knowledge gaps table (self-healing KB tracking)
    CREATE TABLE IF NOT EXISTS knowledge_gaps (
        gap_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

        -- Query context
        query TEXT NOT NULL,
        manufacturer VARCHAR(255),
        model VARCHAR(255),
        confidence_score FLOAT NOT NULL,

        -- Gap tracking
        occurrence_count INTEGER DEFAULT 1,
        priority FLOAT NOT NULL,

        -- Research status
        research_status VARCHAR(50) DEFAULT 'pending',
        resolved_atom_id TEXT,  -- References knowledge_atoms.atom_id (TEXT type in existing table)

        -- Timestamps
        created_at TIMESTAMPTZ DEFAULT NOW(),
        resolved_at TIMESTAMPTZ,

        CONSTRAINT check_research_status CHECK (
            research_status IN ('pending', 'in_progress', 'completed', 'failed')
        ),
        CONSTRAINT check_confidence_score CHECK (
            confidence_score >= 0.0 AND confidence_score <= 1.0
        )
    );

    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_knowledge_gaps_status ON knowledge_gaps(research_status);
    CREATE INDEX IF NOT EXISTS idx_knowledge_gaps_priority ON knowledge_gaps(priority DESC);
    CREATE INDEX IF NOT EXISTS idx_knowledge_gaps_manufacturer ON knowledge_gaps(manufacturer);
    CREATE INDEX IF NOT EXISTS idx_knowledge_gaps_created ON knowledge_gaps(created_at);
    CREATE INDEX IF NOT EXISTS idx_knowledge_gaps_unresolved ON knowledge_gaps(research_status, priority DESC)
        WHERE research_status IN ('pending', 'in_progress');

    -- Unique constraint to prevent duplicate gaps
    CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_gaps_unique_pending ON knowledge_gaps(
        query,
        COALESCE(manufacturer, ''),
        COALESCE(model, '')
    )
    WHERE research_status = 'pending';

    -- Function to calculate gap priority
    CREATE OR REPLACE FUNCTION calculate_gap_priority(
        p_occurrence_count INTEGER,
        p_confidence_score FLOAT,
        p_manufacturer VARCHAR
    )
    RETURNS FLOAT AS $$
    DECLARE
        vendor_boost FLOAT := 1.0;
        confidence_gap FLOAT;
    BEGIN
        -- Boost priority for major vendors
        IF p_manufacturer IN ('Siemens', 'Rockwell', 'Rockwell Automation', 'Allen-Bradley') THEN
            vendor_boost := 1.5;
        END IF;

        -- Confidence gap: how much we don't know (inverted)
        confidence_gap := 1.0 - COALESCE(p_confidence_score, 0.0);

        -- Final priority calculation
        RETURN p_occurrence_count * confidence_gap * vendor_boost;
    END;
    $$ LANGUAGE plpgsql;

    -- Trigger to auto-calculate priority on insert/update
    CREATE OR REPLACE FUNCTION update_gap_priority()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.priority := calculate_gap_priority(
            NEW.occurrence_count,
            NEW.confidence_score,
            NEW.manufacturer
        );
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS trigger_calculate_gap_priority ON knowledge_gaps;
    CREATE TRIGGER trigger_calculate_gap_priority
        BEFORE INSERT OR UPDATE ON knowledge_gaps
        FOR EACH ROW
        EXECUTE FUNCTION update_gap_priority();

    -- Comments
    COMMENT ON TABLE knowledge_gaps IS 'Self-healing KB: tracks low-confidence queries to trigger research';
    COMMENT ON COLUMN knowledge_gaps.priority IS 'Auto-calculated: occurrence_count × (1-confidence) × vendor_boost (higher = more urgent to research)';
    """

    print("[*] Creating knowledge_gaps table and related objects...")

    try:
        await conn.execute(gaps_sql)
        print("[OK] knowledge_gaps table created successfully!")

        # Verify
        count = await conn.fetchval("SELECT COUNT(*) FROM knowledge_gaps")
        print(f"[OK] Verified: knowledge_gaps table exists ({count} rows)")

    except Exception as e:
        print(f"[ERROR] Failed to create table: {e}")

    await conn.close()
    print("\n[SUCCESS] Knowledge gaps table ready!")


if __name__ == "__main__":
    asyncio.run(create_gaps_table())
