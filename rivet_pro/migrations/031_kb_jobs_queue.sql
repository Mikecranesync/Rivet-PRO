-- Migration 031: KB Jobs Queue Tables
-- Created: 2026-01-18
-- Purpose: Support 24/7 KB ingestion worker and gap-driven research

-- ============================================================================
-- Table: kb_ingest_jobs
-- Purpose: Track URLs queued for KB ingestion (mirrors Redis queue for persistence)
-- ============================================================================
CREATE TABLE IF NOT EXISTS kb_ingest_jobs (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    source_type VARCHAR(50) DEFAULT 'web',  -- pdf, youtube, web
    priority INTEGER DEFAULT 50,  -- 0-100, higher = more urgent
    status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, completed, failed

    -- Processing metadata
    worker_id VARCHAR(100),  -- Which worker claimed this job
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Results
    atoms_created INTEGER DEFAULT 0,
    atoms_failed INTEGER DEFAULT 0,
    error_message TEXT,

    -- Tracking
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Deduplication
    url_hash VARCHAR(64) UNIQUE  -- SHA256 hash of URL
);

-- Indexes for efficient queue operations
CREATE INDEX IF NOT EXISTS idx_kb_jobs_status ON kb_ingest_jobs(status);
CREATE INDEX IF NOT EXISTS idx_kb_jobs_priority ON kb_ingest_jobs(priority DESC, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_kb_jobs_worker ON kb_ingest_jobs(worker_id) WHERE status = 'processing';

-- ============================================================================
-- Table: gap_requests
-- Purpose: Track knowledge gaps detected from user queries
-- ============================================================================
CREATE TABLE IF NOT EXISTS gap_requests (
    id SERIAL PRIMARY KEY,

    -- Gap identification
    query_text TEXT NOT NULL,
    equipment_detected VARCHAR(255),  -- e.g., "siemens:plc"
    vendor VARCHAR(100),
    equipment_type VARCHAR(100),

    -- Priority and status
    priority_score INTEGER DEFAULT 50,  -- 0-100, computed from weakness type
    weakness_type VARCHAR(50),  -- zero_atoms, thin_coverage, low_relevance

    -- Ingestion tracking
    ingestion_completed BOOLEAN DEFAULT FALSE,
    source_urls TEXT[],  -- URLs queued for ingestion
    atoms_created INTEGER DEFAULT 0,

    -- Context
    atoms_found INTEGER DEFAULT 0,
    confidence FLOAT DEFAULT 0.0,
    context JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

-- Indexes for gap processing
CREATE INDEX IF NOT EXISTS idx_gap_requests_pending ON gap_requests(priority_score DESC)
    WHERE ingestion_completed = FALSE;
CREATE INDEX IF NOT EXISTS idx_gap_requests_equipment ON gap_requests(vendor, equipment_type);

-- ============================================================================
-- Table: source_fingerprints
-- Purpose: Deduplicate already-processed sources
-- ============================================================================
CREATE TABLE IF NOT EXISTS source_fingerprints (
    id SERIAL PRIMARY KEY,
    fingerprint VARCHAR(64) UNIQUE NOT NULL,  -- SHA256 hash of URL
    url TEXT NOT NULL,
    source_type VARCHAR(50),
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fingerprints_hash ON source_fingerprints(fingerprint);

-- ============================================================================
-- Table: kb_worker_heartbeats
-- Purpose: Track 24/7 worker health
-- ============================================================================
CREATE TABLE IF NOT EXISTS kb_worker_heartbeats (
    id SERIAL PRIMARY KEY,
    worker_id VARCHAR(100) NOT NULL,
    worker_type VARCHAR(50) NOT NULL,  -- ingestion, scheduler, enrichment

    -- Health metrics
    status VARCHAR(50) DEFAULT 'running',  -- running, idle, error, shutdown
    jobs_processed INTEGER DEFAULT 0,
    jobs_failed INTEGER DEFAULT 0,
    queue_depth INTEGER DEFAULT 0,

    -- Timestamps
    started_at TIMESTAMPTZ NOT NULL,
    last_heartbeat TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(worker_id, worker_type)
);

CREATE INDEX IF NOT EXISTS idx_worker_heartbeats_type ON kb_worker_heartbeats(worker_type, last_heartbeat DESC);

-- ============================================================================
-- Function: Update timestamp trigger
-- ============================================================================
CREATE OR REPLACE FUNCTION update_kb_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers
DROP TRIGGER IF EXISTS kb_ingest_jobs_timestamp ON kb_ingest_jobs;
CREATE TRIGGER kb_ingest_jobs_timestamp
    BEFORE UPDATE ON kb_ingest_jobs
    FOR EACH ROW EXECUTE FUNCTION update_kb_timestamp();

DROP TRIGGER IF EXISTS gap_requests_timestamp ON gap_requests;
CREATE TRIGGER gap_requests_timestamp
    BEFORE UPDATE ON gap_requests
    FOR EACH ROW EXECUTE FUNCTION update_kb_timestamp();

-- ============================================================================
-- Seed data: Initial manufacturer URLs for maintenance KB
-- ============================================================================
-- This would be populated by the URL scheduler worker
