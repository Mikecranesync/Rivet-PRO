-- Add validation columns to manual_hunter_cache
-- Run this on Neon database

ALTER TABLE manual_hunter_cache
ADD COLUMN IF NOT EXISTS validation_score INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS validation_content_type TEXT,
ADD COLUMN IF NOT EXISTS validated_at TIMESTAMP DEFAULT NOW();

-- Verify columns were added
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'manual_hunter_cache'
AND column_name IN ('validation_score', 'validation_content_type', 'validated_at');
