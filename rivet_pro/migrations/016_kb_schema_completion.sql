-- Migration 016: KB Schema Completion
-- Adds columns referenced in code but missing from schema
-- Part of KB-001: Database Schema Updates

BEGIN;

-- First verify which columns actually exist and add missing ones
DO $$
BEGIN
    -- Add last_used_at if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'knowledge_atoms' AND column_name = 'last_used_at'
    ) THEN
        ALTER TABLE knowledge_atoms ADD COLUMN last_used_at TIMESTAMPTZ;
        UPDATE knowledge_atoms SET last_used_at = created_at WHERE last_used_at IS NULL;
        RAISE NOTICE 'Added last_used_at column to knowledge_atoms';
    ELSE
        RAISE NOTICE 'Column last_used_at already exists';
    END IF;

    -- Add source_type if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'knowledge_atoms' AND column_name = 'source_type'
    ) THEN
        ALTER TABLE knowledge_atoms ADD COLUMN source_type VARCHAR(50);
        UPDATE knowledge_atoms SET source_type = 'system' WHERE source_type IS NULL;
        RAISE NOTICE 'Added source_type column to knowledge_atoms';
    ELSE
        RAISE NOTICE 'Column source_type already exists';
    END IF;

    -- Add source_id if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'knowledge_atoms' AND column_name = 'source_id'
    ) THEN
        ALTER TABLE knowledge_atoms ADD COLUMN source_id TEXT;
        RAISE NOTICE 'Added source_id column to knowledge_atoms';
    ELSE
        RAISE NOTICE 'Column source_id already exists';
    END IF;
END $$;

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_knowledge_atoms_source_type
ON knowledge_atoms(source_type) WHERE source_type IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_knowledge_atoms_last_used
ON knowledge_atoms(last_used_at DESC NULLS LAST);

-- Add helpful comments
COMMENT ON COLUMN knowledge_atoms.last_used_at IS 'When atom was last returned to user (for usage tracking)';
COMMENT ON COLUMN knowledge_atoms.source_type IS 'Origin: user_interaction, feedback, research, system';
COMMENT ON COLUMN knowledge_atoms.source_id IS 'User ID or system identifier that created this atom';

COMMIT;

-- Verification query - show newly added columns
SELECT
    'knowledge_atoms' as table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'knowledge_atoms'
AND column_name IN ('last_used_at', 'source_type', 'source_id', 'source_interaction_id', 'created_by')
ORDER BY column_name;
