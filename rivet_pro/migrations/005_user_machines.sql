-- Migration 005: User Machines - Personal Equipment Library (Adapted from rivet/atlas)
-- Vision: CLAUDE.md - Personal machine library for quick troubleshooting context
-- Dependencies: 001_saas_layer.sql (users)

-- User Machines: Personal equipment library for quick troubleshooting context
CREATE TABLE user_machines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,  -- UUID now, not TEXT

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
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_query_at TIMESTAMPTZ,

    -- Ensure unique nickname per user
    UNIQUE(user_id, nickname)
);

-- Indexes for fast lookups
CREATE INDEX idx_user_machines_user_id ON user_machines(user_id);
CREATE INDEX idx_user_machines_manufacturer ON user_machines(manufacturer);
CREATE INDEX idx_user_machines_model ON user_machines(model_number);
CREATE INDEX idx_user_machines_created ON user_machines(created_at DESC);

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

-- Comments for documentation
COMMENT ON TABLE user_machines IS 'Personal equipment library for users to save frequently-accessed machines';
COMMENT ON COLUMN user_machines.nickname IS 'User-defined name for the machine (e.g., "Motor A", "Main Drive")';
COMMENT ON COLUMN user_machines.photo_file_id IS 'Telegram file ID for the saved nameplate photo';
COMMENT ON COLUMN user_machines.last_query_at IS 'Last time this machine was used for troubleshooting (updated by app)';
