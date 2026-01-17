-- YCB Database Schema
-- Run this in Supabase SQL Editor to create required tables

-- Agent Status Tracking
CREATE TABLE IF NOT EXISTS ycb_agent_status (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'idle',
    last_heartbeat TIMESTAMPTZ DEFAULT NOW(),
    current_task TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ycb_agent_status_name ON ycb_agent_status(agent_name);
CREATE INDEX IF NOT EXISTS idx_ycb_agent_status_status ON ycb_agent_status(status);

-- Agent Logs
CREATE TABLE IF NOT EXISTS ycb_agent_logs (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    extra_data JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ycb_logs_agent ON ycb_agent_logs(agent_name);
CREATE INDEX IF NOT EXISTS idx_ycb_logs_level ON ycb_agent_logs(level);
CREATE INDEX IF NOT EXISTS idx_ycb_logs_timestamp ON ycb_agent_logs(timestamp DESC);

-- Video Scripts
CREATE TABLE IF NOT EXISTS ycb_scripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    script_type VARCHAR(50) DEFAULT 'tutorial',
    target_duration INTEGER,
    target_audience TEXT,
    sections JSONB DEFAULT '[]',
    keywords TEXT[] DEFAULT '{}',
    topics TEXT[] DEFAULT '{}',
    production_notes TEXT,
    research_sources TEXT[] DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'concept',
    version INTEGER DEFAULT 1,
    generated_by VARCHAR(100),
    generation_params JSONB,
    readability_score NUMERIC(5,2),
    engagement_score NUMERIC(5,2),
    approved_by VARCHAR(100),
    approval_notes TEXT,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ycb_scripts_status ON ycb_scripts(status);
CREATE INDEX IF NOT EXISTS idx_ycb_scripts_type ON ycb_scripts(script_type);

-- Video Pipeline (production tracking)
CREATE TABLE IF NOT EXISTS ycb_video_pipeline (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(500) NOT NULL,
    script_id UUID REFERENCES ycb_scripts(id),
    status VARCHAR(50) DEFAULT 'pending',
    script_generated BOOLEAN DEFAULT FALSE,
    voice_generated BOOLEAN DEFAULT FALSE,
    video_rendered BOOLEAN DEFAULT FALSE,
    thumbnail_generated BOOLEAN DEFAULT FALSE,
    uploaded BOOLEAN DEFAULT FALSE,
    youtube_video_id VARCHAR(50),
    youtube_url TEXT,
    quality_score INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ycb_pipeline_status ON ycb_video_pipeline(status);
CREATE INDEX IF NOT EXISTS idx_ycb_pipeline_created ON ycb_video_pipeline(created_at DESC);

-- Upload Jobs
CREATE TABLE IF NOT EXISTS ycb_upload_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID,
    platform VARCHAR(50) DEFAULT 'youtube',
    video_file_path TEXT NOT NULL,
    thumbnail_file_path TEXT,
    title VARCHAR(200),
    description TEXT,
    tags TEXT[],
    privacy_status VARCHAR(50) DEFAULT 'private',
    scheduled_publish_time TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'pending',
    progress_percent NUMERIC(5,2) DEFAULT 0,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    platform_video_id VARCHAR(100),
    platform_response JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ycb_uploads_status ON ycb_upload_jobs(status);
CREATE INDEX IF NOT EXISTS idx_ycb_uploads_platform ON ycb_upload_jobs(platform);

-- API Quota Tracking
CREATE TABLE IF NOT EXISTS ycb_api_quota (
    id SERIAL PRIMARY KEY,
    service VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    units_used INTEGER DEFAULT 0,
    units_limit INTEGER,
    UNIQUE(service, date)
);

CREATE INDEX IF NOT EXISTS idx_ycb_quota_service_date ON ycb_api_quota(service, date);

-- Enable RLS (Row Level Security) - optional for production
-- ALTER TABLE ycb_agent_status ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE ycb_agent_logs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE ycb_scripts ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE ycb_video_pipeline ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE ycb_upload_jobs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE ycb_api_quota ENABLE ROW LEVEL SECURITY;

-- Create update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables with updated_at
DROP TRIGGER IF EXISTS update_ycb_agent_status_updated_at ON ycb_agent_status;
CREATE TRIGGER update_ycb_agent_status_updated_at
    BEFORE UPDATE ON ycb_agent_status
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS update_ycb_scripts_updated_at ON ycb_scripts;
CREATE TRIGGER update_ycb_scripts_updated_at
    BEFORE UPDATE ON ycb_scripts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS update_ycb_pipeline_updated_at ON ycb_video_pipeline;
CREATE TRIGGER update_ycb_pipeline_updated_at
    BEFORE UPDATE ON ycb_video_pipeline
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Insert default quota limits
INSERT INTO ycb_api_quota (service, date, units_used, units_limit)
VALUES
    ('youtube', CURRENT_DATE, 0, 10000),
    ('openai', CURRENT_DATE, 0, 1000000),
    ('elevenlabs', CURRENT_DATE, 0, 100000)
ON CONFLICT (service, date) DO NOTHING;

-- Verify tables created
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name LIKE 'ycb_%'
ORDER BY table_name;
