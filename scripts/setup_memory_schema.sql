-- Memory atoms table for session storage
-- Supports PostgreSQL with JSONB for flexible content storage

CREATE TABLE IF NOT EXISTS session_memories (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    memory_type TEXT NOT NULL,
    content JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_session_memories_session_id ON session_memories(session_id);
CREATE INDEX IF NOT EXISTS idx_session_memories_user_id ON session_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_session_memories_memory_type ON session_memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_session_memories_created_at ON session_memories(created_at);

-- Composite index for common query pattern
CREATE INDEX IF NOT EXISTS idx_session_memories_session_type ON session_memories(session_id, memory_type);
