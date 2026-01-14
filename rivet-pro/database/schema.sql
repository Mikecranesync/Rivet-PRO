-- RIVET Pro Database Schema
-- PostgreSQL on Neon
-- Created: 2026-01-07

-- ============================================
-- USERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    telegram_username VARCHAR(255),
    first_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    is_pro BOOLEAN DEFAULT FALSE,
    pro_expires_at TIMESTAMP,
    stripe_customer_id VARCHAR(255),
    lookup_count INTEGER DEFAULT 0,
    last_lookup_at TIMESTAMP,

    -- Metadata
    last_updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_is_pro ON users(is_pro);
CREATE INDEX IF NOT EXISTS idx_users_stripe_customer_id ON users(stripe_customer_id);

-- ============================================
-- LOOKUPS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS lookups (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    telegram_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),

    -- Photo & Analysis Data
    image_hash VARCHAR(64),
    photo_file_id VARCHAR(255),
    analysis_text TEXT,

    -- Performance Tracking
    processing_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,

    -- Metadata
    model_used VARCHAR(100) DEFAULT 'claude-sonnet-4-20250514',
    tokens_used INTEGER
);

-- Indexes for analytics
CREATE INDEX IF NOT EXISTS idx_lookups_user_id ON lookups(user_id);
CREATE INDEX IF NOT EXISTS idx_lookups_telegram_id ON lookups(telegram_id);
CREATE INDEX IF NOT EXISTS idx_lookups_created_at ON lookups(created_at);
CREATE INDEX IF NOT EXISTS idx_lookups_success ON lookups(success);

-- ============================================
-- SUBSCRIPTIONS TABLE (for Stripe tracking)
-- ============================================
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    stripe_subscription_id VARCHAR(255) UNIQUE,
    stripe_customer_id VARCHAR(255),
    status VARCHAR(50), -- active, canceled, past_due, etc.
    plan_id VARCHAR(255),
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_subscription_id ON subscriptions(stripe_subscription_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);

-- ============================================
-- COMMANDS LOG (for analytics)
-- ============================================
CREATE TABLE IF NOT EXISTS command_logs (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    command VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_command_logs_telegram_id ON command_logs(telegram_id);
CREATE INDEX IF NOT EXISTS idx_command_logs_created_at ON command_logs(created_at);

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to upsert user and return full user record
CREATE OR REPLACE FUNCTION upsert_user(
    p_telegram_id BIGINT,
    p_telegram_username VARCHAR(255),
    p_first_name VARCHAR(255)
)
RETURNS TABLE (
    id INTEGER,
    telegram_id BIGINT,
    telegram_username VARCHAR(255),
    first_name VARCHAR(255),
    is_pro BOOLEAN,
    lookup_count INTEGER,
    pro_expires_at TIMESTAMP
) AS $$
BEGIN
    INSERT INTO users (telegram_id, telegram_username, first_name)
    VALUES (p_telegram_id, p_telegram_username, p_first_name)
    ON CONFLICT (telegram_id)
    DO UPDATE SET
        telegram_username = EXCLUDED.telegram_username,
        first_name = EXCLUDED.first_name,
        last_updated_at = NOW();

    RETURN QUERY
    SELECT u.id, u.telegram_id, u.telegram_username, u.first_name,
           u.is_pro, u.lookup_count, u.pro_expires_at
    FROM users u
    WHERE u.telegram_id = p_telegram_id;
END;
$$ LANGUAGE plpgsql;

-- Function to check if user can perform lookup
CREATE OR REPLACE FUNCTION can_user_lookup(p_telegram_id BIGINT)
RETURNS TABLE (
    allowed BOOLEAN,
    is_pro BOOLEAN,
    lookups_remaining INTEGER,
    message TEXT
) AS $$
DECLARE
    v_user RECORD;
BEGIN
    SELECT * INTO v_user FROM users WHERE telegram_id = p_telegram_id;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, FALSE, 0, 'User not found. Please /start first.'::TEXT;
        RETURN;
    END IF;

    -- Pro users always allowed
    IF v_user.is_pro AND (v_user.pro_expires_at IS NULL OR v_user.pro_expires_at > NOW()) THEN
        RETURN QUERY SELECT TRUE, TRUE, -1, 'Pro user - unlimited'::TEXT;
        RETURN;
    END IF;

    -- Free users check limit
    IF v_user.lookup_count >= 10 THEN
        RETURN QUERY SELECT FALSE, FALSE, 0, 'Free limit reached. Use /upgrade for unlimited access.'::TEXT;
        RETURN;
    END IF;

    RETURN QUERY SELECT TRUE, FALSE, (10 - v_user.lookup_count), 'Lookup allowed'::TEXT;
END;
$$ LANGUAGE plpgsql;

-- Function to increment lookup counter
CREATE OR REPLACE FUNCTION increment_lookup_counter(p_telegram_id BIGINT)
RETURNS VOID AS $$
BEGIN
    UPDATE users
    SET lookup_count = lookup_count + 1,
        last_lookup_at = NOW()
    WHERE telegram_id = p_telegram_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- ANALYTICS VIEWS
-- ============================================

-- Daily stats view
CREATE OR REPLACE VIEW daily_stats AS
SELECT
    DATE(created_at) as date,
    COUNT(DISTINCT telegram_id) as unique_users,
    COUNT(*) as total_lookups,
    COUNT(*) FILTER (WHERE success = true) as successful_lookups,
    COUNT(*) FILTER (WHERE success = false) as failed_lookups,
    AVG(processing_time_ms) as avg_processing_time_ms
FROM lookups
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- User activity summary
CREATE OR REPLACE VIEW user_activity AS
SELECT
    u.telegram_id,
    u.telegram_username,
    u.first_name,
    u.is_pro,
    u.lookup_count,
    u.created_at as joined_at,
    u.last_lookup_at,
    COUNT(l.id) as total_analyses,
    MAX(l.created_at) as last_analysis_at
FROM users u
LEFT JOIN lookups l ON u.id = l.user_id
GROUP BY u.id, u.telegram_id, u.telegram_username, u.first_name,
         u.is_pro, u.lookup_count, u.created_at, u.last_lookup_at
ORDER BY u.created_at DESC;

-- ============================================
-- SEED DATA (optional - for testing)
-- ============================================

-- Uncomment to create a test user
-- INSERT INTO users (telegram_id, telegram_username, first_name, is_pro)
-- VALUES (123456789, 'testuser', 'Test User', false)
-- ON CONFLICT (telegram_id) DO NOTHING;
