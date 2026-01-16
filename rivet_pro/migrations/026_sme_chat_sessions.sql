-- Migration 026: SME Chat Sessions
-- Phase 4: SME Chat with LLM Interaction
-- Tracks conversational sessions with SME agents (Hans, Mike, Erik, etc.)

-- SME Chat Sessions table
-- Tracks active conversations between users and vendor-specific SME agents
CREATE TABLE IF NOT EXISTS sme_chat_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- User identification
    telegram_chat_id BIGINT NOT NULL,

    -- SME configuration
    sme_vendor VARCHAR(50) NOT NULL,  -- siemens, rockwell, abb, schneider, mitsubishi, fanuc, generic

    -- Session state
    status VARCHAR(20) NOT NULL DEFAULT 'active',

    -- Context from equipment/troubleshooting workflow
    equipment_context JSONB,  -- model, serial, recent_faults, etc.

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,

    CONSTRAINT check_sme_vendor CHECK (
        sme_vendor IN ('siemens', 'rockwell', 'abb', 'schneider', 'mitsubishi', 'fanuc', 'generic')
    ),
    CONSTRAINT check_session_status CHECK (
        status IN ('active', 'closed', 'timeout')
    )
);

-- SME Chat Messages table
-- Stores conversation history for context and analytics
CREATE TABLE IF NOT EXISTS sme_chat_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Session reference
    session_id UUID NOT NULL REFERENCES sme_chat_sessions(session_id) ON DELETE CASCADE,

    -- Message content
    role VARCHAR(20) NOT NULL,  -- system, user, assistant
    content TEXT NOT NULL,

    -- Response metadata (for assistant messages)
    confidence FLOAT,  -- RAG confidence score 0.0-1.0
    rag_atoms_used UUID[],  -- Array of knowledge_atom IDs used in response
    cost_usd FLOAT,  -- LLM cost for this message

    -- Extracted information
    safety_warnings TEXT[],  -- Safety warnings extracted from response
    sources TEXT[],  -- Source citations from RAG

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT check_message_role CHECK (
        role IN ('system', 'user', 'assistant')
    ),
    CONSTRAINT check_confidence CHECK (
        confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)
    )
);

-- Indexes for session lookups
CREATE INDEX IF NOT EXISTS idx_sme_sessions_telegram_chat ON sme_chat_sessions(telegram_chat_id);
CREATE INDEX IF NOT EXISTS idx_sme_sessions_status ON sme_chat_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sme_sessions_vendor ON sme_chat_sessions(sme_vendor);
CREATE INDEX IF NOT EXISTS idx_sme_sessions_active ON sme_chat_sessions(telegram_chat_id, status)
    WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_sme_sessions_last_message ON sme_chat_sessions(last_message_at DESC);

-- Indexes for message queries
CREATE INDEX IF NOT EXISTS idx_sme_messages_session ON sme_chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_sme_messages_created ON sme_chat_messages(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sme_messages_role ON sme_chat_messages(session_id, role);

-- Auto-update last_message_at trigger
CREATE OR REPLACE FUNCTION update_session_last_message()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE sme_chat_sessions
    SET last_message_at = NOW()
    WHERE session_id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_session_last_message
    AFTER INSERT ON sme_chat_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_session_last_message();

-- Function to close inactive sessions (30-minute timeout)
CREATE OR REPLACE FUNCTION close_inactive_sme_sessions(timeout_minutes INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    closed_count INTEGER;
BEGIN
    WITH updated AS (
        UPDATE sme_chat_sessions
        SET status = 'timeout', closed_at = NOW()
        WHERE status = 'active'
          AND last_message_at < NOW() - (timeout_minutes || ' minutes')::INTERVAL
        RETURNING session_id
    )
    SELECT COUNT(*) INTO closed_count FROM updated;

    RETURN closed_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get active session for a Telegram chat
CREATE OR REPLACE FUNCTION get_active_sme_session(p_telegram_chat_id BIGINT)
RETURNS TABLE(
    session_id UUID,
    sme_vendor VARCHAR,
    equipment_context JSONB,
    created_at TIMESTAMPTZ,
    last_message_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.session_id,
        s.sme_vendor,
        s.equipment_context,
        s.created_at,
        s.last_message_at
    FROM sme_chat_sessions s
    WHERE s.telegram_chat_id = p_telegram_chat_id
      AND s.status = 'active'
    ORDER BY s.created_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to get conversation history for a session
CREATE OR REPLACE FUNCTION get_sme_conversation_history(
    p_session_id UUID,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE(
    role VARCHAR,
    content TEXT,
    confidence FLOAT,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.role,
        m.content,
        m.confidence,
        m.created_at
    FROM sme_chat_messages m
    WHERE m.session_id = p_session_id
    ORDER BY m.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Comments
COMMENT ON TABLE sme_chat_sessions IS 'Multi-turn chat sessions with vendor-specific SME agents (Hans, Mike, Erik, etc.)';
COMMENT ON TABLE sme_chat_messages IS 'Conversation history for SME chat sessions with RAG metadata';

COMMENT ON COLUMN sme_chat_sessions.sme_vendor IS 'Vendor SME personality: siemens=Hans, rockwell=Mike, abb=Erik, schneider=Pierre, mitsubishi=Takeshi, fanuc=Ken';
COMMENT ON COLUMN sme_chat_sessions.equipment_context IS 'JSON with model, serial, recent_faults from equipment workflow';
COMMENT ON COLUMN sme_chat_sessions.status IS 'active=in conversation, closed=user ended, timeout=30min inactivity';

COMMENT ON COLUMN sme_chat_messages.rag_atoms_used IS 'UUID array of knowledge_atoms referenced in response';
COMMENT ON COLUMN sme_chat_messages.confidence IS 'RAG confidence: >=0.85 direct KB, 0.70-0.85 synthesis, <0.70 clarify';
COMMENT ON COLUMN sme_chat_messages.safety_warnings IS 'Safety warnings extracted from response (high voltage, lockout, etc.)';

COMMENT ON FUNCTION close_inactive_sme_sessions IS 'Closes sessions inactive for specified minutes (default 30). Call periodically via cron.';
COMMENT ON FUNCTION get_active_sme_session IS 'Returns the current active SME session for a Telegram chat, if any.';
COMMENT ON FUNCTION get_sme_conversation_history IS 'Returns recent messages for a session, newest first.';
