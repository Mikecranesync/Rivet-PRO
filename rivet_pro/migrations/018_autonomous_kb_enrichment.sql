-- Migration: Autonomous KB Enrichment System
-- Description: Create tables for autonomous knowledge base enrichment
-- Author: AUTO-KB-001
-- Date: 2026-01-14

-- Enable pgvector extension for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- 1. ENRICHMENT QUEUE TABLE
-- ============================================================================
-- Priority-based work queue for autonomous enrichment
CREATE TABLE IF NOT EXISTS enrichment_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manufacturer VARCHAR(255) NOT NULL,
    model_pattern VARCHAR(255) NOT NULL,  -- e.g., "S7-*", "2080*"
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),  -- 1-10, higher = more urgent
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    user_query_count INTEGER DEFAULT 1,  -- How many users searched this
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    worker_id VARCHAR(100),
    family_size INTEGER,  -- How many models found in family
    manuals_indexed INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_enrichment_priority
    ON enrichment_queue(priority DESC, created_at ASC)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_enrichment_status
    ON enrichment_queue(status, manufacturer);

CREATE INDEX IF NOT EXISTS idx_enrichment_manufacturer
    ON enrichment_queue(manufacturer, model_pattern);

COMMENT ON TABLE enrichment_queue IS 'Work queue for autonomous KB enrichment jobs';
COMMENT ON COLUMN enrichment_queue.priority IS 'Job priority: 1=lowest, 10=highest urgency';
COMMENT ON COLUMN enrichment_queue.user_query_count IS 'Number of user queries that triggered this family';

-- ============================================================================
-- 2. PRODUCT FAMILIES TABLE
-- ============================================================================
-- Track discovered product families (e.g., "S7 Series", "2080 Micro")
CREATE TABLE IF NOT EXISTS product_families (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manufacturer VARCHAR(255) NOT NULL,
    family_name VARCHAR(255) NOT NULL,  -- e.g., "S7 Series", "2080 Micro"
    family_pattern VARCHAR(255),  -- e.g., "S7-*", "2080*"
    discovered_at TIMESTAMPTZ DEFAULT NOW(),
    member_count INTEGER DEFAULT 0,  -- Total models in family
    indexed_count INTEGER DEFAULT 0,  -- Models indexed so far
    last_enriched_at TIMESTAMPTZ,
    is_complete BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}'::jsonb,  -- Additional family info
    UNIQUE(manufacturer, family_name)
);

CREATE INDEX IF NOT EXISTS idx_product_families_manufacturer
    ON product_families(manufacturer);

CREATE INDEX IF NOT EXISTS idx_product_families_complete
    ON product_families(is_complete, last_enriched_at);

COMMENT ON TABLE product_families IS 'Discovered product families for bulk enrichment';
COMMENT ON COLUMN product_families.indexed_count IS 'Number of family members with manuals indexed';

-- ============================================================================
-- 3. MANUAL FILES TABLE
-- ============================================================================
-- Local manual storage metadata with vector embeddings
CREATE TABLE IF NOT EXISTS manual_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manual_cache_id INTEGER REFERENCES manual_cache(id) ON DELETE SET NULL,
    file_path TEXT NOT NULL,  -- Local path or S3 key
    file_size_bytes BIGINT,
    mime_type VARCHAR(100) DEFAULT 'application/pdf',
    download_status VARCHAR(20) DEFAULT 'pending' CHECK (download_status IN ('pending', 'downloading', 'completed', 'failed')),
    downloaded_at TIMESTAMPTZ,
    text_extracted BOOLEAN DEFAULT FALSE,
    text_content TEXT,  -- Extracted text for search
    embedding_vector VECTOR(1536),  -- For semantic search (OpenAI ada-002 dimension)
    checksum VARCHAR(64),  -- SHA256 of file
    storage_location VARCHAR(20) DEFAULT 'local' CHECK (storage_location IN ('local', 's3', 'both')),
    s3_key TEXT,
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_manual_files_path
    ON manual_files(file_path);

CREATE INDEX IF NOT EXISTS idx_manual_files_status
    ON manual_files(download_status);

CREATE INDEX IF NOT EXISTS idx_manual_files_cache
    ON manual_files(manual_cache_id);

-- Vector similarity search index (IVFFlat for performance)
CREATE INDEX IF NOT EXISTS idx_manual_files_embedding
    ON manual_files USING ivfflat (embedding_vector vector_cosine_ops)
    WITH (lists = 100);

COMMENT ON TABLE manual_files IS 'Local storage metadata for downloaded manuals';
COMMENT ON COLUMN manual_files.embedding_vector IS 'Vector embedding for semantic search';
COMMENT ON COLUMN manual_files.checksum IS 'SHA256 checksum for file integrity verification';

-- ============================================================================
-- 4. ENRICHMENT STATS TABLE
-- ============================================================================
-- Worker health monitoring and analytics
CREATE TABLE IF NOT EXISTS enrichment_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stat_type VARCHAR(50) NOT NULL CHECK (stat_type IN ('daily_summary', 'worker_heartbeat', 'error_log', 'performance_metric')),
    worker_id VARCHAR(100),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metrics JSONB DEFAULT '{}'::jsonb,  -- Flexible stats storage
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_enrichment_stats_type
    ON enrichment_stats(stat_type, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_enrichment_stats_worker
    ON enrichment_stats(worker_id, timestamp DESC);

COMMENT ON TABLE enrichment_stats IS 'Worker health monitoring and enrichment analytics';
COMMENT ON COLUMN enrichment_stats.stat_type IS 'Type: daily_summary, worker_heartbeat, error_log, performance_metric';

-- ============================================================================
-- 5. SCHEMA UPDATES TO EXISTING TABLES
-- ============================================================================

-- Update knowledge_atoms table
ALTER TABLE knowledge_atoms
ADD COLUMN IF NOT EXISTS product_family_id UUID REFERENCES product_families(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS manual_file_id UUID REFERENCES manual_files(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS enrichment_source VARCHAR(50) DEFAULT 'reactive'
    CHECK (enrichment_source IN ('reactive', 'proactive_family', 'proactive_priority')),
ADD COLUMN IF NOT EXISTS indexed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_knowledge_atoms_family
    ON knowledge_atoms(product_family_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_atoms_enrichment_source
    ON knowledge_atoms(enrichment_source);

COMMENT ON COLUMN knowledge_atoms.enrichment_source IS 'How atom was created: reactive (user query), proactive_family (family discovery), proactive_priority (priority enrichment)';

-- Update manual_cache table
ALTER TABLE manual_cache
ADD COLUMN IF NOT EXISTS product_family_id UUID REFERENCES product_families(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS local_file_available BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS download_priority INTEGER DEFAULT 5 CHECK (download_priority >= 1 AND download_priority <= 10);

CREATE INDEX IF NOT EXISTS idx_manual_cache_family
    ON manual_cache(product_family_id);

CREATE INDEX IF NOT EXISTS idx_manual_cache_local_available
    ON manual_cache(local_file_available);

COMMENT ON COLUMN manual_cache.local_file_available IS 'Whether manual is downloaded and available locally';
COMMENT ON COLUMN manual_cache.download_priority IS 'Priority for downloading this manual (1-10)';

-- ============================================================================
-- 6. UTILITY FUNCTIONS
-- ============================================================================

-- Function to update manual_cache.local_file_available when file is downloaded
CREATE OR REPLACE FUNCTION update_local_file_availability()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.download_status = 'completed' AND NEW.manual_cache_id IS NOT NULL THEN
        UPDATE manual_cache
        SET local_file_available = TRUE
        WHERE id = NEW.manual_cache_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER manual_file_download_complete
AFTER INSERT OR UPDATE ON manual_files
FOR EACH ROW
WHEN (NEW.download_status = 'completed')
EXECUTE FUNCTION update_local_file_availability();

-- Function to update product_families.indexed_count
CREATE OR REPLACE FUNCTION update_family_indexed_count()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.product_family_id IS NOT NULL THEN
        UPDATE product_families
        SET indexed_count = (
            SELECT COUNT(DISTINCT id)
            FROM knowledge_atoms
            WHERE product_family_id = NEW.product_family_id
        ),
        last_enriched_at = NOW()
        WHERE id = NEW.product_family_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER knowledge_atom_family_update
AFTER INSERT OR UPDATE ON knowledge_atoms
FOR EACH ROW
WHEN (NEW.product_family_id IS NOT NULL)
EXECUTE FUNCTION update_family_indexed_count();

-- ============================================================================
-- 7. INITIAL DATA
-- ============================================================================

-- Insert initial worker heartbeat
INSERT INTO enrichment_stats (stat_type, worker_id, metrics)
VALUES ('worker_heartbeat', 'bootstrap', '{"status": "system_initialized", "version": "1.0.0"}'::jsonb);

COMMENT ON SCHEMA public IS 'Autonomous KB Enrichment System - Migration 018';

-- Migration complete
