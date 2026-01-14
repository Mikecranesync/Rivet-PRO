-- Migration 012: Stripe Payment Integration
-- Adds subscription_status and stripe_customer_id to users table

-- Add Stripe-related columns to users table
ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(20) DEFAULT 'free',
    ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255) UNIQUE,
    ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS subscription_started_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS subscription_ends_at TIMESTAMPTZ;

-- Add check constraint for subscription_status
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.check_constraints 
        WHERE constraint_name = 'check_subscription_status'
    ) THEN
        ALTER TABLE users ADD CONSTRAINT check_subscription_status CHECK (
            subscription_status IN ('free', 'active', 'canceled', 'past_due')
        );
    END IF;
END $$;

-- Create index for Stripe customer lookup
CREATE INDEX IF NOT EXISTS idx_users_stripe_customer_id ON users(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_users_subscription_status ON users(subscription_status);

-- Comments
COMMENT ON COLUMN users.subscription_status IS 'Current subscription status: free, active, canceled, past_due';
COMMENT ON COLUMN users.stripe_customer_id IS 'Stripe customer ID for billing';
COMMENT ON COLUMN users.stripe_subscription_id IS 'Stripe subscription ID';
