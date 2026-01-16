-- Migration 027: Node Callback Mappings for Persistent Storage
-- DEBT-002: Replace in-memory callback storage with PostgreSQL
-- This ensures Telegram inline button callbacks survive bot restarts

-- Create the node_callback_mappings table
CREATE TABLE IF NOT EXISTS node_callback_mappings (
    id SERIAL PRIMARY KEY,
    -- Composite key: tree_id + node_hash
    tree_id INTEGER NOT NULL,
    node_hash VARCHAR(8) NOT NULL,  -- 4 hex chars, allow some buffer
    -- Original node identifier
    node_id TEXT NOT NULL,
    -- Timestamps for TTL management
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours'),
    -- Prevent duplicate mappings
    UNIQUE(tree_id, node_hash)
);

-- Index for fast lookup by tree_id + node_hash (primary query pattern)
CREATE INDEX IF NOT EXISTS idx_callback_mappings_lookup
ON node_callback_mappings(tree_id, node_hash);

-- Index for cleanup of expired mappings
CREATE INDEX IF NOT EXISTS idx_callback_mappings_expires
ON node_callback_mappings(expires_at);

-- Function to clean up expired mappings (called periodically or on insert)
CREATE OR REPLACE FUNCTION cleanup_expired_callback_mappings()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM node_callback_mappings
    WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Upsert function for storing mappings (handles collisions gracefully)
CREATE OR REPLACE FUNCTION upsert_node_callback_mapping(
    p_tree_id INTEGER,
    p_node_hash VARCHAR(8),
    p_node_id TEXT
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO node_callback_mappings (tree_id, node_hash, node_id, created_at, expires_at)
    VALUES (p_tree_id, p_node_hash, p_node_id, NOW(), NOW() + INTERVAL '24 hours')
    ON CONFLICT (tree_id, node_hash)
    DO UPDATE SET
        node_id = EXCLUDED.node_id,
        created_at = NOW(),
        expires_at = NOW() + INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust role name as needed)
-- GRANT ALL ON node_callback_mappings TO your_app_role;
-- GRANT EXECUTE ON FUNCTION cleanup_expired_callback_mappings() TO your_app_role;
-- GRANT EXECUTE ON FUNCTION upsert_node_callback_mapping(INTEGER, VARCHAR, TEXT) TO your_app_role;

-- Verify
SELECT 'Migration 027_node_callback_mappings.sql applied successfully' AS status;
