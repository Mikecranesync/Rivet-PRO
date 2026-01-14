-- RALPH Tables for Supabase
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS ralph_projects (
    id SERIAL PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    max_iterations INTEGER DEFAULT 50,
    token_budget INTEGER DEFAULT 500000,
    telegram_chat_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ralph_stories (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES ralph_projects(id),
    story_id VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    acceptance_criteria JSONB,
    ai_model VARCHAR(100) DEFAULT 'claude-sonnet-4-20250514',
    status VARCHAR(20) DEFAULT 'todo',
    status_emoji VARCHAR(10) DEFAULT '⬜',
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
    ),
    CONSTRAINT check_ai_model CHECK (
        ai_model IN ('claude-sonnet-4-20250514', 'claude-3-5-sonnet-20241022', 'claude-haiku-20250305')
    )
);

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

INSERT INTO ralph_projects (id, project_name, max_iterations, token_budget, telegram_chat_id)
VALUES (1, 'RIVET Pro', 50, 500000, '8445149012')
ON CONFLICT (id) DO NOTHING;

INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, ai_model, priority) VALUES
(1, 'RIVET-001', 'Usage Tracking System', 'Track equipment lookups per user for freemium enforcement.', '["Track each photo upload as one lookup", "Store user_id and timestamp in Neon", "Create get_usage_count function", "Block at 10 free lookups with upgrade message"]'::jsonb, 'claude-sonnet-4-20250514', 1),
(1, 'RIVET-002', 'Stripe Payment Integration', 'Connect Stripe for Pro tier at $29/month.', '["Create Stripe product/price for Pro $29/mo", "Implement checkout session endpoint", "Handle payment success webhook", "Update user subscription status", "Send Telegram confirmation"]'::jsonb, 'claude-sonnet-4-20250514', 2),
(1, 'RIVET-003', 'Free Tier Limit Enforcement', 'Block lookups at 10 and show upgrade prompt.', '["Check usage before processing photo", "Return upgrade message with Stripe link if limit hit", "Allow Pro users unlimited"]'::jsonb, 'claude-sonnet-4-20250514', 3),
(1, 'RIVET-004', 'Shorten System Prompts', 'Cut all prompts by 50% for faster field responses.', '["Audit all RIVET prompts", "Reduce each by 50%", "Remove filler text", "Test quality maintained"]'::jsonb, 'claude-haiku-20250305', 4),
(1, 'RIVET-005', 'Remove n8n Footer', 'Remove n8n branding from Telegram messages.', '["Find where footer is added", "Remove or override it", "Test all message types"]'::jsonb, 'claude-haiku-20250305', 5)
ON CONFLICT (project_id, story_id) DO NOTHING;
