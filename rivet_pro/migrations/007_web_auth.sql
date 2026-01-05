-- 007_web_auth.sql
-- Add web authentication fields to users table

-- Add password_hash column for web login
ALTER TABLE users
ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);

-- Add email verification status
ALTER TABLE users
ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;

-- Add last login tracking
ALTER TABLE users
ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;

-- Create unique index on email for web login
-- Only create if it doesn't already exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE indexname = 'idx_users_email_unique'
    ) THEN
        CREATE UNIQUE INDEX idx_users_email_unique
        ON users(email) WHERE email IS NOT NULL;
    END IF;
END
$$;

-- Add comment to track migration purpose
COMMENT ON COLUMN users.password_hash IS 'Bcrypt hashed password for web authentication';
COMMENT ON COLUMN users.email_verified IS 'Whether user has verified their email address';
COMMENT ON COLUMN users.last_login_at IS 'Timestamp of last successful login (web or Telegram)';
