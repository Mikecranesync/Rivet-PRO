-- Chat with Print-it Database Schema
-- PostgreSQL (Neon)

-- Users table
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
    last_lookup_at TIMESTAMP
);

-- Lookups audit table
CREATE TABLE IF NOT EXISTS lookups (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    telegram_id BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    image_hash VARCHAR(64),
    analysis_text TEXT,
    processing_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

-- Payments tracking
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    telegram_id BIGINT,
    stripe_session_id VARCHAR(255) UNIQUE,
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    amount_cents INTEGER,
    currency VARCHAR(10) DEFAULT 'usd',
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Daily stats for reporting
CREATE TABLE IF NOT EXISTS daily_stats (
    id SERIAL PRIMARY KEY,
    date DATE UNIQUE NOT NULL,
    new_users INTEGER DEFAULT 0,
    total_lookups INTEGER DEFAULT 0,
    new_pro_subscriptions INTEGER DEFAULT 0,
    revenue_cents INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_lookups_user_id ON lookups(user_id);
CREATE INDEX IF NOT EXISTS idx_lookups_created_at ON lookups(created_at);
CREATE INDEX IF NOT EXISTS idx_lookups_telegram_id ON lookups(telegram_id);
CREATE INDEX IF NOT EXISTS idx_payments_telegram_id ON payments(telegram_id);
CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date);

-- Function to update daily stats
CREATE OR REPLACE FUNCTION update_daily_stats()
RETURNS void AS $$
BEGIN
    INSERT INTO daily_stats (date, new_users, total_lookups, new_pro_subscriptions, revenue_cents)
    SELECT 
        CURRENT_DATE,
        (SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURRENT_DATE),
        (SELECT COUNT(*) FROM lookups WHERE DATE(created_at) = CURRENT_DATE),
        (SELECT COUNT(*) FROM payments WHERE DATE(created_at) = CURRENT_DATE AND status = 'complete'),
        (SELECT COALESCE(SUM(amount_cents), 0) FROM payments WHERE DATE(created_at) = CURRENT_DATE AND status = 'complete')
    ON CONFLICT (date) DO UPDATE SET
        new_users = EXCLUDED.new_users,
        total_lookups = EXCLUDED.total_lookups,
        new_pro_subscriptions = EXCLUDED.new_pro_subscriptions,
        revenue_cents = EXCLUDED.revenue_cents;
END;
$$ LANGUAGE plpgsql;
