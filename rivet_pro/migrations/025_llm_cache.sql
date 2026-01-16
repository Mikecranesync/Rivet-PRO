-- Migration 025: LLM Cache Table
-- Stores cached LLM responses for failover and cost reduction
-- Part of Phase 3 Pipeline Integration

CREATE TABLE IF NOT EXISTS llm_cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(64) UNIQUE NOT NULL,
    prompt_hash VARCHAR(64) NOT NULL,
    response TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Index for fast cache lookups by key
CREATE INDEX IF NOT EXISTS idx_llm_cache_key ON llm_cache(cache_key);

-- Index for TTL cleanup queries (oldest first)
CREATE INDEX IF NOT EXISTS idx_llm_cache_created ON llm_cache(created_at DESC);

-- Comment explaining purpose
COMMENT ON TABLE llm_cache IS 'Cached LLM responses for Claude->GPT-4->Cache failover chain';
COMMENT ON COLUMN llm_cache.cache_key IS 'SHA-256 hash of prompt for deduplication';
COMMENT ON COLUMN llm_cache.metadata IS 'JSON with provider, tokens, cost, timestamp';
