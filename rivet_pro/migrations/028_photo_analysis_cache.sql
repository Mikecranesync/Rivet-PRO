-- Migration 028: Photo Analysis Cache
-- PHOTO-DEEP-001: Cache for DeepSeek extraction results
-- Prevents re-processing same images within 24h window

-- Create photo_analysis_cache table
CREATE TABLE IF NOT EXISTS photo_analysis_cache (
    id SERIAL PRIMARY KEY,

    -- Image identification (SHA256 hash of image bytes)
    photo_hash VARCHAR(64) NOT NULL UNIQUE,

    -- Extraction results
    manufacturer VARCHAR(255),
    model_number VARCHAR(255),
    serial_number VARCHAR(255),
    specs JSONB DEFAULT '{}',
    raw_text TEXT,
    confidence REAL NOT NULL DEFAULT 0.0,

    -- Processing metadata
    model_used VARCHAR(100) NOT NULL,
    processing_time_ms INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0.0,

    -- Timestamps for TTL management
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours'),

    -- Track cache hits for analytics
    hit_count INTEGER NOT NULL DEFAULT 0,
    last_hit_at TIMESTAMPTZ
);

-- Index for fast lookup by photo_hash (primary query pattern)
CREATE INDEX IF NOT EXISTS idx_photo_cache_hash
ON photo_analysis_cache(photo_hash);

-- Index for cleanup of expired entries
CREATE INDEX IF NOT EXISTS idx_photo_cache_expires
ON photo_analysis_cache(expires_at);

-- Function to clean up expired cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_photo_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM photo_analysis_cache
    WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get or record cache hit
CREATE OR REPLACE FUNCTION get_photo_cache_and_hit(p_photo_hash VARCHAR(64))
RETURNS TABLE (
    manufacturer VARCHAR(255),
    model_number VARCHAR(255),
    serial_number VARCHAR(255),
    specs JSONB,
    raw_text TEXT,
    confidence REAL,
    model_used VARCHAR(100),
    was_cached BOOLEAN
) AS $$
DECLARE
    v_record RECORD;
BEGIN
    -- Try to find existing non-expired entry
    SELECT pc.manufacturer, pc.model_number, pc.serial_number,
           pc.specs, pc.raw_text, pc.confidence, pc.model_used
    INTO v_record
    FROM photo_analysis_cache pc
    WHERE pc.photo_hash = p_photo_hash
      AND pc.expires_at > NOW();

    IF FOUND THEN
        -- Update hit count
        UPDATE photo_analysis_cache
        SET hit_count = hit_count + 1,
            last_hit_at = NOW()
        WHERE photo_hash = p_photo_hash;

        -- Return cached result
        RETURN QUERY SELECT
            v_record.manufacturer,
            v_record.model_number,
            v_record.serial_number,
            v_record.specs,
            v_record.raw_text,
            v_record.confidence,
            v_record.model_used,
            TRUE::BOOLEAN;
    ELSE
        -- Return empty with was_cached = false
        RETURN QUERY SELECT
            NULL::VARCHAR(255),
            NULL::VARCHAR(255),
            NULL::VARCHAR(255),
            NULL::JSONB,
            NULL::TEXT,
            NULL::REAL,
            NULL::VARCHAR(100),
            FALSE::BOOLEAN;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Verify
SELECT 'Migration 028_photo_analysis_cache.sql applied successfully' AS status;
