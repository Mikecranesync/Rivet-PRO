-- Migration 011: Usage Tracking for Freemium Enforcement
-- Tracks equipment lookups per user for billing/limits
-- Dependencies: 001_saas_layer.sql (users table)

-- Usage tracking table
CREATE TABLE IF NOT EXISTS usage_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    telegram_user_id BIGINT NOT NULL,
    lookup_timestamp TIMESTAMPTZ DEFAULT NOW(),
    equipment_id UUID,
    lookup_type VARCHAR(50) DEFAULT 'photo_ocr',
    
    CONSTRAINT check_lookup_type CHECK (
        lookup_type IN ('photo_ocr', 'manual_search', 'api_call')
    )
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_usage_tracking_telegram_user ON usage_tracking(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_usage_tracking_timestamp ON usage_tracking(lookup_timestamp);
CREATE INDEX IF NOT EXISTS idx_usage_tracking_user_id ON usage_tracking(user_id);

-- Comments
COMMENT ON TABLE usage_tracking IS 'Granular tracking of user lookups for freemium billing';
COMMENT ON COLUMN usage_tracking.telegram_user_id IS 'Telegram user ID for quick lookup without JOIN';
COMMENT ON COLUMN usage_tracking.lookup_type IS 'Type of lookup: photo_ocr, manual_search, api_call';
