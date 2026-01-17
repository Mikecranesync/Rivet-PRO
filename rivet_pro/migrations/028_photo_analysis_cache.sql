-- Migration 028: Photo Analysis Cache
-- PHOTO-CACHE-001: Cache for photo analysis results (screening + extraction)
-- Prevents re-processing same images within 24h window

-- Drop existing table if schema changed (dev only - remove in prod)
DROP TABLE IF EXISTS photo_analysis_cache CASCADE;

-- Create photo_analysis_cache table
CREATE TABLE IF NOT EXISTS photo_analysis_cache (
    id SERIAL PRIMARY KEY,

    -- Image identification (SHA256 hash of image bytes)
    photo_hash VARCHAR(64) NOT NULL UNIQUE,

    -- Screening result (Groq fast-check: is_industrial, confidence, etc)
    screening_result JSONB DEFAULT '{}',

    -- Extraction result (DeepSeek full extraction: manufacturer, model, specs, etc)
    extraction_result JSONB DEFAULT '{}',

    -- Timestamps for TTL management
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours'),

    -- Track cache hits for analytics
    access_count INTEGER NOT NULL DEFAULT 0
);

-- Index for fast lookup by photo_hash (primary query pattern)
CREATE INDEX IF NOT EXISTS idx_photo_cache_hash
ON photo_analysis_cache(photo_hash);

-- Index for cleanup of expired entries
CREATE INDEX IF NOT EXISTS idx_photo_cache_expires
ON photo_analysis_cache(expires_at);

-- Function to clean up expired cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
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

-- Upsert function for duplicate hash handling
CREATE OR REPLACE FUNCTION upsert_photo_cache(
    p_photo_hash VARCHAR(64),
    p_screening_result JSONB DEFAULT '{}',
    p_extraction_result JSONB DEFAULT '{}'
)
RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
BEGIN
    INSERT INTO photo_analysis_cache (photo_hash, screening_result, extraction_result)
    VALUES (p_photo_hash, p_screening_result, p_extraction_result)
    ON CONFLICT (photo_hash)
    DO UPDATE SET
        screening_result = COALESCE(NULLIF(p_screening_result::text, '{}')::jsonb, photo_analysis_cache.screening_result),
        extraction_result = COALESCE(NULLIF(p_extraction_result::text, '{}')::jsonb, photo_analysis_cache.extraction_result),
        expires_at = NOW() + INTERVAL '24 hours',
        access_count = photo_analysis_cache.access_count + 1
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get cache entry and increment access count
CREATE OR REPLACE FUNCTION get_photo_cache(p_photo_hash VARCHAR(64))
RETURNS TABLE (
    screening_result JSONB,
    extraction_result JSONB,
    access_count INTEGER,
    was_cached BOOLEAN
) AS $$
DECLARE
    v_record RECORD;
BEGIN
    -- Try to find existing non-expired entry
    SELECT pc.screening_result, pc.extraction_result, pc.access_count
    INTO v_record
    FROM photo_analysis_cache pc
    WHERE pc.photo_hash = p_photo_hash
      AND pc.expires_at > NOW();

    IF FOUND THEN
        -- Update access count
        UPDATE photo_analysis_cache
        SET access_count = photo_analysis_cache.access_count + 1
        WHERE photo_hash = p_photo_hash;

        -- Return cached result
        RETURN QUERY SELECT
            v_record.screening_result,
            v_record.extraction_result,
            v_record.access_count + 1,
            TRUE::BOOLEAN;
    ELSE
        -- Return empty with was_cached = false
        RETURN QUERY SELECT
            NULL::JSONB,
            NULL::JSONB,
            0::INTEGER,
            FALSE::BOOLEAN;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Verify
SELECT 'Migration 028_photo_analysis_cache.sql applied successfully' AS status;
