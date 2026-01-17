-- Migration 001: Ralph - Autonomous Coding Agent Schema
-- Creates tables for story tracking and execution history

-- Projects table (Ralph configurations)
CREATE TABLE IF NOT EXISTS ralph_projects (
    id SERIAL PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    max_iterations INTEGER DEFAULT 50,
    token_budget INTEGER DEFAULT 500000,
    telegram_chat_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Stories table (implementation queue with AI model selection)
CREATE TABLE IF NOT EXISTS ralph_stories (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES ralph_projects(id),
    story_id VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    acceptance_criteria JSONB,
    ai_model VARCHAR(100) DEFAULT 'claude-sonnet-4-20250514',
    status VARCHAR(20) DEFAULT 'todo',
    status_emoji VARCHAR(10) DEFAULT '',
    priority INTEGER DEFAULT 0,
    commit_hash VARCHAR(100),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, story_id),
    CONSTRAINT check_status CHECK (
        status IN ('todo', 'in_progress', 'done', 'failed')
    )
);

-- Iterations table (execution history)
CREATE TABLE IF NOT EXISTS ralph_iterations (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES ralph_projects(id),
    story_id INTEGER REFERENCES ralph_stories(id),
    execution_id INTEGER,
    iteration_number INTEGER,
    status VARCHAR(20),
    commit_hash VARCHAR(100),
    tokens_used INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Executions table (run tracking)
CREATE TABLE IF NOT EXISTS ralph_executions (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES ralph_projects(id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    total_iterations INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    stories_completed INTEGER DEFAULT 0,
    stories_failed INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'running',
    stop_reason VARCHAR(100),
    CONSTRAINT check_exec_status CHECK (
        status IN ('running', 'completed', 'failed')
    )
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_stories_status ON ralph_stories(project_id, status);
CREATE INDEX IF NOT EXISTS idx_stories_priority ON ralph_stories(project_id, priority ASC) WHERE status = 'todo';
CREATE INDEX IF NOT EXISTS idx_iterations_story ON ralph_iterations(story_id);
CREATE INDEX IF NOT EXISTS idx_executions_project ON ralph_executions(project_id, created_at DESC);

-- Default project
INSERT INTO ralph_projects (id, project_name, max_iterations, token_budget)
VALUES (1, 'Default Project', 50, 500000)
ON CONFLICT (id) DO NOTHING;

-- Comments
COMMENT ON TABLE ralph_projects IS 'Ralph project configurations with token budgets';
COMMENT ON TABLE ralph_stories IS 'Story queue with per-story AI model selection';
COMMENT ON TABLE ralph_iterations IS 'Execution history tracking tokens and results';
COMMENT ON TABLE ralph_executions IS 'High-level run metrics and status';
