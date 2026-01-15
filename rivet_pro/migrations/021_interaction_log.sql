-- Migration: 021_interaction_log.sql
-- Purpose: Store interaction log for memory backup redundancy
-- Created: 2026-01-15

-- Interaction log table for backup
CREATE TABLE IF NOT EXISTS interaction_log (
    id SERIAL PRIMARY KEY,
    project VARCHAR(100) NOT NULL DEFAULT 'RIVET-Pro',
    session_date DATE NOT NULL,
    session_time TIME NOT NULL,
    session_id VARCHAR(255),
    user_prompt TEXT NOT NULL,
    outcome TEXT,
    key_decisions TEXT,
    files_created TEXT[],
    files_modified TEXT[],
    commits TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for efficient querying
CREATE INDEX IF NOT EXISTS idx_interaction_log_project ON interaction_log(project);
CREATE INDEX IF NOT EXISTS idx_interaction_log_session_date ON interaction_log(session_date DESC);
CREATE INDEX IF NOT EXISTS idx_interaction_log_created_at ON interaction_log(created_at DESC);

-- Knowledge graph backup table
CREATE TABLE IF NOT EXISTS knowledge_graph_backup (
    id SERIAL PRIMARY KEY,
    project VARCHAR(100) NOT NULL DEFAULT 'RIVET-Pro',
    entity_name VARCHAR(255) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    observations JSONB DEFAULT '[]'::jsonb,
    relations JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(project, entity_name)
);

-- Index for knowledge graph queries
CREATE INDEX IF NOT EXISTS idx_kg_backup_project ON knowledge_graph_backup(project);
CREATE INDEX IF NOT EXISTS idx_kg_backup_entity_type ON knowledge_graph_backup(entity_type);

-- Comment for documentation
COMMENT ON TABLE interaction_log IS 'Backup of Claude Code interaction history for context restoration';
COMMENT ON TABLE knowledge_graph_backup IS 'Backup of MCP memory graph entities and relations';
