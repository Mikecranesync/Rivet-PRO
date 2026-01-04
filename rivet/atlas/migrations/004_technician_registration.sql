-- Migration 004: Create Technicians Table
-- Date: 2025-01-04
-- Description: Technician registration and activity tracking for Telegram users

-- Create table for technician users (if not exists)
CREATE TABLE IF NOT EXISTS technicians (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_user_id TEXT UNIQUE NOT NULL,  -- Telegram user ID (unique identifier)

    -- Profile
    username VARCHAR(255),                   -- Telegram @username (optional)
    first_name VARCHAR(255),                 -- Telegram first name
    last_name VARCHAR(255),                  -- Telegram last name

    -- Professional Details
    specialization VARCHAR(255),             -- e.g., "Electrical", "Mechanical", "Automation"
    organization VARCHAR(255),               -- Company or facility name

    -- Status
    is_active BOOLEAN DEFAULT TRUE,          -- Can login and create work orders

    -- Activity Tracking
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ DEFAULT NOW(),

    -- Statistics (denormalized for performance)
    work_order_count INTEGER DEFAULT 0,      -- Total work orders created
    equipment_count INTEGER DEFAULT 0        -- Total equipment registered
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_technicians_telegram_id ON technicians(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_technicians_active ON technicians(is_active);
CREATE INDEX IF NOT EXISTS idx_technicians_organization ON technicians(organization);
CREATE INDEX IF NOT EXISTS idx_technicians_last_activity ON technicians(last_activity_at DESC);

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_technician_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS technician_updated_at ON technicians;
CREATE TRIGGER technician_updated_at
BEFORE UPDATE ON technicians
FOR EACH ROW
EXECUTE FUNCTION update_technician_timestamp();

-- Comments for documentation
COMMENT ON TABLE technicians IS 'Technician users who interact via Telegram bot. Tracks registration, activity, and statistics.';
COMMENT ON COLUMN technicians.telegram_user_id IS 'Telegram user ID (numeric string from Telegram API) - primary identifier';
COMMENT ON COLUMN technicians.username IS 'Telegram @username (may change, not used as primary key)';
COMMENT ON COLUMN technicians.work_order_count IS 'Cached count of work orders created by this technician';
COMMENT ON COLUMN technicians.equipment_count IS 'Cached count of equipment registered by this technician';
COMMENT ON COLUMN technicians.last_activity_at IS 'Last time technician interacted with bot (any command)';
