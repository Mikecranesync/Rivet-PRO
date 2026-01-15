-- AUTO-KB-011: Query Pattern Tracking
-- Tracks user queries for intelligent enrichment prioritization

-- Query patterns table
CREATE TABLE IF NOT EXISTS query_patterns (
    id SERIAL PRIMARY KEY,
    manufacturer VARCHAR(255) NOT NULL,
    model VARCHAR(255),
    product_family VARCHAR(255),
    user_id VARCHAR(255),  -- Telegram user ID or session ID
    queried_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_query_patterns_manufacturer
    ON query_patterns(LOWER(manufacturer));

CREATE INDEX IF NOT EXISTS idx_query_patterns_queried_at
    ON query_patterns(queried_at DESC);

CREATE INDEX IF NOT EXISTS idx_query_patterns_manufacturer_time
    ON query_patterns(LOWER(manufacturer), queried_at DESC);

CREATE INDEX IF NOT EXISTS idx_query_patterns_family
    ON query_patterns(LOWER(product_family)) WHERE product_family IS NOT NULL;

-- Add S3 backup columns to manual_files (AUTO-KB-010)
ALTER TABLE manual_files
    ADD COLUMN IF NOT EXISTS s3_key VARCHAR(500),
    ADD COLUMN IF NOT EXISTS s3_uploaded_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_manual_files_s3
    ON manual_files(s3_key) WHERE s3_key IS NOT NULL;

-- Add access tracking to manual_files (AUTO-KB-009)
ALTER TABLE manual_files
    ADD COLUMN IF NOT EXISTS last_accessed_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS access_count INTEGER DEFAULT 0;

-- Comments
COMMENT ON TABLE query_patterns IS 'Tracks user query patterns for intelligent enrichment prioritization (AUTO-KB-011)';
COMMENT ON COLUMN query_patterns.manufacturer IS 'Equipment manufacturer from query';
COMMENT ON COLUMN query_patterns.model IS 'Specific model if queried';
COMMENT ON COLUMN query_patterns.product_family IS 'Product family if identified';
COMMENT ON COLUMN query_patterns.user_id IS 'User identifier for unique user tracking';
