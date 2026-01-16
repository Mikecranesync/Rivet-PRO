-- Migration 025: Manual Feedback Tables
-- Description: Track human-in-the-loop validation of manual URLs
-- Author: Claude
-- Date: 2026-01-15

-- Add validated_by_user column to manual_cache if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'manual_cache' AND column_name = 'validated_by_user'
    ) THEN
        ALTER TABLE manual_cache ADD COLUMN validated_by_user BOOLEAN DEFAULT FALSE;
    END IF;

    -- Also add url column alias if needed (some code uses 'url' instead of 'manual_url')
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'manual_cache' AND column_name = 'url'
    ) THEN
        ALTER TABLE manual_cache ADD COLUMN url TEXT;
    END IF;

    -- Add confidence column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'manual_cache' AND column_name = 'confidence'
    ) THEN
        ALTER TABLE manual_cache ADD COLUMN confidence FLOAT DEFAULT 0.0;
    END IF;

    -- Add updated_at column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'manual_cache' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE manual_cache ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE;
    END IF;

    -- Add created_at column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'manual_cache' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE manual_cache ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
    END IF;
END $$;

-- Create manual_feedback table to track user validation responses
CREATE TABLE IF NOT EXISTS manual_feedback (
    id SERIAL PRIMARY KEY,
    manufacturer VARCHAR(255) NOT NULL,
    model VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    telegram_user_id VARCHAR(50),
    feedback_note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for analytics on rejection patterns
CREATE INDEX IF NOT EXISTS idx_manual_feedback_url
ON manual_feedback(url);

CREATE INDEX IF NOT EXISTS idx_manual_feedback_equipment
ON manual_feedback(LOWER(manufacturer), LOWER(model));

-- Comments
COMMENT ON TABLE manual_feedback IS 'Tracks human-in-the-loop validation of manual URLs';
COMMENT ON COLUMN manual_feedback.is_correct IS 'TRUE if user confirmed URL is correct, FALSE if rejected';
COMMENT ON COLUMN manual_feedback.telegram_user_id IS 'User who provided feedback (for rate limiting if needed)';
