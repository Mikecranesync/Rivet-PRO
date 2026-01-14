-- Migration 013: Manual Cache Table
-- Description: Cache equipment manuals to reduce API calls and speed up repeat lookups
-- Author: Ralph
-- Date: 2026-01-12

-- Create manual cache table
CREATE TABLE IF NOT EXISTS manual_cache (
    id SERIAL PRIMARY KEY,
    manufacturer VARCHAR(255) NOT NULL,
    model VARCHAR(255) NOT NULL,
    manual_url TEXT,
    manual_title VARCHAR(500),
    source VARCHAR(100) DEFAULT 'tavily',
    verified BOOLEAN DEFAULT FALSE,
    found_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    access_count INTEGER DEFAULT 1,
    UNIQUE(manufacturer, model)
);

-- Create index for fast case-insensitive lookups
CREATE INDEX IF NOT EXISTS idx_manual_cache_lookup
ON manual_cache(LOWER(manufacturer), LOWER(model));

-- Add comment to table
COMMENT ON TABLE manual_cache IS 'Caches equipment manual URLs to reduce external API calls';

-- Add comments to columns
COMMENT ON COLUMN manual_cache.manufacturer IS 'Equipment manufacturer (case-insensitive for lookup)';
COMMENT ON COLUMN manual_cache.model IS 'Equipment model number (case-insensitive for lookup)';
COMMENT ON COLUMN manual_cache.manual_url IS 'URL to PDF manual (NULL if not found)';
COMMENT ON COLUMN manual_cache.manual_title IS 'Human-readable manual title';
COMMENT ON COLUMN manual_cache.source IS 'Where manual was found (tavily, vendor site, etc)';
COMMENT ON COLUMN manual_cache.verified IS 'Whether URL has been verified to work';
COMMENT ON COLUMN manual_cache.found_at IS 'When manual was first cached';
COMMENT ON COLUMN manual_cache.last_accessed IS 'Last time manual was requested';
COMMENT ON COLUMN manual_cache.access_count IS 'Number of times this manual has been accessed';
