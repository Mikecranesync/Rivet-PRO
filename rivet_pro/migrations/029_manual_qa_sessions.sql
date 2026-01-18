-- Migration 029: Manual QA Sessions
-- Supports the PDF Manual Q&A system with conversation persistence
-- Vision: pdf_manual_qa_system.md - Hybrid inference Q&A system

-- Q&A Sessions table
-- Tracks user sessions for multi-turn conversations with PDF manuals
CREATE TABLE manual_qa_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manual_id UUID REFERENCES manuals(id) ON DELETE SET NULL,
    user_id INTEGER,  -- Telegram chat ID or web user ID

    -- Session metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,

    -- Statistics
    message_count INTEGER DEFAULT 0,
    total_cost_usd FLOAT DEFAULT 0.0,
    avg_confidence FLOAT DEFAULT 0.0,

    -- Session state
    status VARCHAR(20) DEFAULT 'active',

    CONSTRAINT check_session_status CHECK (
        status IN ('active', 'ended', 'expired')
    )
);

-- Q&A Messages table
-- Stores individual messages within a session
CREATE TABLE manual_qa_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES manual_qa_sessions(session_id) ON DELETE CASCADE,

    -- Message content
    role VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,

    -- Response metadata (for assistant messages)
    citations JSONB,  -- [{"page": 12, "section": "3.2", "text": "..."}]
    confidence FLOAT,
    cost_usd FLOAT,
    model_used VARCHAR(100),
    from_vision BOOLEAN DEFAULT FALSE,

    -- RAG context (for debugging/improvement)
    rag_chunks_used INTEGER DEFAULT 0,
    rag_top_similarity FLOAT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_message_role CHECK (
        role IN ('user', 'assistant', 'system')
    )
);

-- Manual Q&A Analytics
-- Aggregated statistics for improving the system
CREATE TABLE manual_qa_analytics (
    id SERIAL PRIMARY KEY,
    manual_id UUID REFERENCES manuals(id) ON DELETE CASCADE,

    -- Query patterns
    query_text TEXT NOT NULL,
    query_embedding vector(1536),  -- For finding similar queries

    -- Response quality
    response_confidence FLOAT,
    sources_found INTEGER,
    user_helpful_vote BOOLEAN,  -- NULL = no vote, TRUE = helpful, FALSE = not helpful

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Dedupe similar queries (within same manual)
    query_hash VARCHAR(64)  -- SHA256 of normalized query
);

-- Indexes for performance

-- Sessions
CREATE INDEX idx_manual_qa_sessions_manual ON manual_qa_sessions(manual_id);
CREATE INDEX idx_manual_qa_sessions_user ON manual_qa_sessions(user_id);
CREATE INDEX idx_manual_qa_sessions_status ON manual_qa_sessions(status);
CREATE INDEX idx_manual_qa_sessions_created ON manual_qa_sessions(created_at);

-- Messages
CREATE INDEX idx_manual_qa_messages_session ON manual_qa_messages(session_id);
CREATE INDEX idx_manual_qa_messages_created ON manual_qa_messages(created_at);
CREATE INDEX idx_manual_qa_messages_role ON manual_qa_messages(role);

-- Analytics
CREATE INDEX idx_manual_qa_analytics_manual ON manual_qa_analytics(manual_id);
CREATE INDEX idx_manual_qa_analytics_created ON manual_qa_analytics(created_at);
CREATE INDEX idx_manual_qa_analytics_hash ON manual_qa_analytics(query_hash);

-- Vector similarity index for finding similar queries
CREATE INDEX idx_manual_qa_analytics_embedding ON manual_qa_analytics
    USING ivfflat (query_embedding vector_cosine_ops)
    WITH (lists = 50);

-- Trigger to update session last_message_at
CREATE OR REPLACE FUNCTION update_session_last_message()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE manual_qa_sessions
    SET last_message_at = NOW(),
        message_count = message_count + 1
    WHERE session_id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_session_last_message
    AFTER INSERT ON manual_qa_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_session_last_message();

-- Function to expire old sessions (call periodically)
CREATE OR REPLACE FUNCTION expire_old_manual_qa_sessions(older_than_hours INTEGER DEFAULT 24)
RETURNS INTEGER AS $$
DECLARE
    expired_count INTEGER;
BEGIN
    UPDATE manual_qa_sessions
    SET status = 'expired',
        ended_at = NOW()
    WHERE status = 'active'
      AND last_message_at < NOW() - (older_than_hours || ' hours')::INTERVAL;

    GET DIAGNOSTICS expired_count = ROW_COUNT;
    RETURN expired_count;
END;
$$ LANGUAGE plpgsql;

-- Comments
COMMENT ON TABLE manual_qa_sessions IS 'PDF Manual Q&A conversation sessions';
COMMENT ON TABLE manual_qa_messages IS 'Individual messages within Q&A sessions';
COMMENT ON TABLE manual_qa_analytics IS 'Query analytics for improving Q&A system';

COMMENT ON COLUMN manual_qa_sessions.manual_id IS 'Specific manual being queried (NULL = all manuals)';
COMMENT ON COLUMN manual_qa_sessions.user_id IS 'Telegram chat ID or web user identifier';
COMMENT ON COLUMN manual_qa_messages.citations IS 'JSON array of page/section citations';
COMMENT ON COLUMN manual_qa_messages.from_vision IS 'TRUE if answer came from image/vision pipeline';
COMMENT ON COLUMN manual_qa_analytics.query_hash IS 'SHA256 hash for deduplicating similar queries';
