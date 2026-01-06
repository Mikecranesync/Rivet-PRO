-- Migration 008: Complete Web Authentication Support
-- Fixes schema mismatch between auth code expectations and database reality
-- Allows BOTH Telegram/WhatsApp users AND web email/password users

-- 1. Rename 'name' to 'full_name' (align with auth code)
ALTER TABLE users RENAME COLUMN name TO full_name;

-- 2. Add 'role' column for RBAC (required by auth code)
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user';

-- 3. password_hash and email_verified should already exist from migration 007
-- But add IF NOT EXISTS for safety
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;

-- 4. Remove platform_id constraint (allows web users without telegram_id/whatsapp_id)
ALTER TABLE users DROP CONSTRAINT IF EXISTS check_platform_id;

-- 5. Create unique index on email (only for non-NULL emails)
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique
ON users(email) WHERE email IS NOT NULL;

-- 6. Add helpful comments
COMMENT ON COLUMN users.full_name IS 'User full name (from email registration or platform profile)';
COMMENT ON COLUMN users.role IS 'User role: user, admin, moderator (default: user)';
COMMENT ON COLUMN users.password_hash IS 'Bcrypt hashed password (NULL for platform-only users)';
COMMENT ON COLUMN users.email_verified IS 'Email verification status (platform users auto-verified)';

-- 7. Update existing n8n user to have role
UPDATE users
SET role = 'user', email_verified = TRUE
WHERE email = 'n8n@rivet-cmms.com';
