-- Migration: Manual Matching System with LLM Validation
-- Creates tables for async manual search, validation, and retry logic

-- Equipment Manual Searches - Track async manual search status and results
CREATE TABLE IF NOT EXISTS equipment_manual_searches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_id UUID NOT NULL REFERENCES cmms_equipment(id) ON DELETE CASCADE,
    telegram_chat_id BIGINT NOT NULL,  -- For delayed notification

    -- Search tracking
    search_status VARCHAR(20) DEFAULT 'pending',
    search_started_at TIMESTAMPTZ DEFAULT NOW(),
    search_completed_at TIMESTAMPTZ,

    -- Results (supports multiple manuals)
    manuals_found JSONB,  -- Array of {url, title, confidence, reasoning, manual_type, atom_id}
    best_manual_url TEXT,
    best_manual_confidence FLOAT,
    requires_human_verification BOOLEAN DEFAULT FALSE,

    -- Retry tracking
    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMPTZ,
    next_retry_at TIMESTAMPTZ,
    retry_reason TEXT,

    -- Metadata
    search_duration_ms INTEGER,
    sources_searched TEXT[],
    error_message TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_search_status CHECK (
        search_status IN ('pending', 'searching', 'completed', 'failed', 'no_manual_found',
                          'pending_human_verification', 'retrying')
    )
);

CREATE INDEX IF NOT EXISTS idx_ems_equipment ON equipment_manual_searches(equipment_id);
CREATE INDEX IF NOT EXISTS idx_ems_status ON equipment_manual_searches(search_status);
CREATE INDEX IF NOT EXISTS idx_ems_pending ON equipment_manual_searches(search_status, created_at)
    WHERE search_status = 'pending';
CREATE INDEX IF NOT EXISTS idx_ems_chat ON equipment_manual_searches(telegram_chat_id);
CREATE INDEX IF NOT EXISTS idx_ems_retry ON equipment_manual_searches(next_retry_at)
    WHERE search_status = 'retrying' AND next_retry_at IS NOT NULL;

-- Extend manual_cache table with LLM validation columns
ALTER TABLE manual_cache ADD COLUMN IF NOT EXISTS llm_validated BOOLEAN DEFAULT FALSE;
ALTER TABLE manual_cache ADD COLUMN IF NOT EXISTS llm_confidence FLOAT;
ALTER TABLE manual_cache ADD COLUMN IF NOT EXISTS validation_reasoning TEXT;
ALTER TABLE manual_cache ADD COLUMN IF NOT EXISTS manual_type VARCHAR(50);
ALTER TABLE manual_cache ADD COLUMN IF NOT EXISTS atom_id TEXT REFERENCES knowledge_atoms(atom_id);

CREATE INDEX IF NOT EXISTS idx_manual_cache_validated ON manual_cache(llm_validated) WHERE llm_validated = TRUE;
CREATE INDEX IF NOT EXISTS idx_manual_cache_atom ON manual_cache(atom_id) WHERE atom_id IS NOT NULL;

-- Comments for documentation
COMMENT ON TABLE equipment_manual_searches IS 'Tracks async manual search operations with retry logic and LLM validation';
COMMENT ON COLUMN equipment_manual_searches.manuals_found IS 'JSONB array of all validated manuals with metadata';
COMMENT ON COLUMN equipment_manual_searches.requires_human_verification IS 'True for 0.70-0.85 confidence results needing human verification';
COMMENT ON COLUMN equipment_manual_searches.retry_count IS 'Number of retry attempts (max 5 with exponential backoff)';
COMMENT ON COLUMN manual_cache.llm_validated IS 'True if manual validated by LLM judge (Groq or Claude)';
COMMENT ON COLUMN manual_cache.manual_type IS 'Type: user_manual, service_manual, datasheet, quick_start, unknown';
