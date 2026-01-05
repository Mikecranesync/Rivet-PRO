-- Migration 001: SaaS Layer (Users, Teams, Subscriptions)
-- Vision: RIVET_PRO_BUILD_SPEC.md - SaaS with subscription tiers
-- Dependencies: None (foundation layer)

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Teams table (organizations)
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    owner_id UUID,  -- Will reference users.id (added in constraint below)
    subscription_tier VARCHAR(20) NOT NULL DEFAULT 'free',
    max_seats INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_subscription_tier CHECK (
        subscription_tier IN ('free', 'pro', 'team')
    )
);

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Platform identifiers (support Telegram + WhatsApp)
    telegram_id BIGINT UNIQUE,
    whatsapp_id VARCHAR(20) UNIQUE,

    -- User profile
    name VARCHAR(255),
    email VARCHAR(255),
    company VARCHAR(255),

    -- Subscription
    subscription_tier VARCHAR(20) DEFAULT 'free',
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,

    -- Usage tracking
    monthly_lookup_count INTEGER DEFAULT 0,
    lookup_count_reset_date DATE DEFAULT CURRENT_DATE,

    -- Activity
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_subscription_tier CHECK (
        subscription_tier IN ('free', 'pro', 'team')
    ),
    CONSTRAINT check_platform_id CHECK (
        telegram_id IS NOT NULL OR whatsapp_id IS NOT NULL
    )
);

-- Add foreign key for team owner (circular reference resolved)
ALTER TABLE teams
    ADD CONSTRAINT fk_team_owner
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE;

-- Subscription usage limits
CREATE TABLE subscription_limits (
    tier VARCHAR(20) PRIMARY KEY,
    manual_lookups_per_month INTEGER,
    chat_with_pdf BOOLEAN DEFAULT FALSE,
    chat_with_prints BOOLEAN DEFAULT FALSE,
    personal_cmms BOOLEAN DEFAULT FALSE,
    upload_docs_per_month INTEGER DEFAULT 0,
    tribal_knowledge_write BOOLEAN DEFAULT FALSE,
    plc_io_panel BOOLEAN DEFAULT FALSE,
    seats INTEGER DEFAULT 1,

    CONSTRAINT check_tier CHECK (tier IN ('free', 'pro', 'team'))
);

-- Insert subscription tier definitions
INSERT INTO subscription_limits (
    tier,
    manual_lookups_per_month,
    chat_with_pdf,
    chat_with_prints,
    personal_cmms,
    upload_docs_per_month,
    tribal_knowledge_write,
    plc_io_panel,
    seats
) VALUES
    ('free', 10, FALSE, FALSE, FALSE, 0, FALSE, FALSE, 1),
    ('pro', -1, TRUE, TRUE, TRUE, 50, TRUE, FALSE, 1),  -- -1 = unlimited
    ('team', -1, TRUE, TRUE, TRUE, -1, TRUE, TRUE, 10);

-- Indexes for performance
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_whatsapp_id ON users(whatsapp_id);
CREATE INDEX idx_users_team_id ON users(team_id);
CREATE INDEX idx_users_subscription_tier ON users(subscription_tier);
CREATE INDEX idx_users_last_active ON users(last_active_at);

-- Auto-update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_teams_updated_at
    BEFORE UPDATE ON teams
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE users IS 'User accounts for Rivet Pro SaaS platform';
COMMENT ON TABLE teams IS 'Team/organization accounts for multi-user subscriptions';
COMMENT ON TABLE subscription_limits IS 'Feature limits for each subscription tier';
COMMENT ON COLUMN users.telegram_id IS 'Telegram user ID (unique)';
COMMENT ON COLUMN users.whatsapp_id IS 'WhatsApp phone number (unique)';
COMMENT ON COLUMN users.monthly_lookup_count IS 'Reset monthly for free tier limit enforcement';
COMMENT ON COLUMN subscription_limits.manual_lookups_per_month IS 'Manual lookup limit (-1 = unlimited)';
