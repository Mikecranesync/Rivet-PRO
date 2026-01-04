-- ═══════════════════════════════════════════════════════════════════════════
-- Personal Machine Library - User's Saved Equipment
-- Part of Atlas CMMS extraction from Agent Factory
-- ═══════════════════════════════════════════════════════════════════════════

-- User Machines: Personal equipment library for quick troubleshooting context
CREATE TABLE IF NOT EXISTS user_machines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,  -- Telegram user_id (string)

    -- Machine identification
    nickname VARCHAR(255) NOT NULL,  -- User's name for the machine (e.g., "Motor A")
    manufacturer VARCHAR(255),
    model_number VARCHAR(255),
    serial_number VARCHAR(255),

    -- Location and context
    location VARCHAR(255),
    notes TEXT,

    -- Photo reference
    photo_file_id VARCHAR(500),  -- Telegram file_id for saved photo

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_query_at TIMESTAMP,

    -- Ensure unique nickname per user
    UNIQUE(user_id, nickname)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_user_machines_user_id ON user_machines(user_id);
CREATE INDEX IF NOT EXISTS idx_user_machines_manufacturer ON user_machines(manufacturer);
CREATE INDEX IF NOT EXISTS idx_user_machines_model ON user_machines(model_number);
CREATE INDEX IF NOT EXISTS idx_user_machines_created ON user_machines(created_at DESC);

-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_user_machine_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_machines_updated_at
    BEFORE UPDATE ON user_machines
    FOR EACH ROW
    EXECUTE FUNCTION update_user_machine_timestamp();

-- Query tracking: Update last_query_at when machine is used for troubleshooting
-- This is updated by the application layer, not via trigger
