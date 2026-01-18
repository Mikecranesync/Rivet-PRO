-- Migration 030: Adaptive Command System for Always-On Intelligent Assistant
-- Tracks user command preferences for dynamic menu personalization
-- Enables the bot to learn which commands each user prefers

-- =============================================================================
-- USER COMMAND PREFERENCES
-- =============================================================================
-- Track per-user command usage for adaptive menu ordering
CREATE TABLE IF NOT EXISTS user_command_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL,  -- telegram_id

    -- Intent tracking
    intent_type VARCHAR(50) NOT NULL,  -- EQUIPMENT_SEARCH, MANUAL_QUESTION, etc.
    usage_count INTEGER DEFAULT 1,
    last_used_at TIMESTAMPTZ DEFAULT NOW(),

    -- User customization
    is_pinned BOOLEAN DEFAULT FALSE,  -- User manually pinned this command
    is_hidden BOOLEAN DEFAULT FALSE,  -- User manually hid this command
    custom_alias VARCHAR(100),         -- User's custom name for command (future)

    -- Tracking
    first_used_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(user_id, intent_type)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_user_cmd_prefs_user_id
    ON user_command_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_user_cmd_prefs_usage
    ON user_command_preferences(user_id, usage_count DESC);
CREATE INDEX IF NOT EXISTS idx_user_cmd_prefs_recent
    ON user_command_preferences(user_id, last_used_at DESC);

-- =============================================================================
-- INTENT COMMAND MAPPING
-- =============================================================================
-- Default intent -> slash command mapping for fallback routing
CREATE TABLE IF NOT EXISTS intent_command_mapping (
    intent_type VARCHAR(50) PRIMARY KEY,
    slash_command VARCHAR(50) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    example_phrases TEXT[],  -- Array of example natural language phrases
    priority INTEGER DEFAULT 50,  -- Default display order (lower = higher priority)
    is_active BOOLEAN DEFAULT TRUE
);

-- Insert default mappings
INSERT INTO intent_command_mapping (intent_type, slash_command, display_name, description, example_phrases, priority) VALUES
('EQUIPMENT_SEARCH', '/equip search', 'Search Equipment', 'Find equipment by name, manufacturer, or model',
    ARRAY['find siemens', 'what motors do I have', 'show equipment', 'list drives'], 10),
('EQUIPMENT_ADD', '/equip add', 'Add Equipment', 'Register new equipment from nameplate',
    ARRAY['add motor', 'register this', 'new equipment'], 20),
('WORK_ORDER_CREATE', '/wo create', 'Create Work Order', 'Create a new maintenance work order',
    ARRAY['create WO', 'new work order', 'report issue', 'maintenance request'], 30),
('WORK_ORDER_STATUS', '/wo list', 'Work Orders', 'View your work order status and history',
    ARRAY['my work orders', 'WO status', 'open WOs', 'check work order'], 40),
('MANUAL_QUESTION', '/ask', 'Ask Manual', 'Questions about equipment manuals and procedures',
    ARRAY['how do I', 'what does error mean', 'procedure for', 'calibration steps'], 50),
('TROUBLESHOOT', '/help', 'Troubleshoot', 'Get expert help with equipment issues',
    ARRAY['motor overheating', 'won''t start', 'error code', 'fault diagnosis'], 60),
('GENERAL_CHAT', '/menu', 'Menu', 'Show main menu and available commands',
    ARRAY['hello', 'help', 'what can you do', 'options'], 100)
ON CONFLICT (intent_type) DO UPDATE SET
    slash_command = EXCLUDED.slash_command,
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    example_phrases = EXCLUDED.example_phrases,
    priority = EXCLUDED.priority;

-- =============================================================================
-- INTENT CLASSIFICATION LOG
-- =============================================================================
-- Log classifications for ML improvement and debugging
CREATE TABLE IF NOT EXISTS intent_classification_log (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    message_text TEXT NOT NULL,

    -- Classification results
    classified_intent VARCHAR(50),
    confidence FLOAT,
    entities JSONB,  -- {manufacturer, model, fault_code, equipment_number}

    -- Feedback for learning
    was_correct BOOLEAN,  -- NULL = not confirmed, TRUE = correct, FALSE = user corrected
    corrected_intent VARCHAR(50),  -- If user selected different action

    -- Metadata
    classification_time_ms INTEGER,  -- How long classification took
    model_used VARCHAR(100),  -- e.g., 'groq/llama-3.3-70b-versatile'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_intent_log_user
    ON intent_classification_log(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_intent_log_intent
    ON intent_classification_log(classified_intent, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_intent_log_feedback
    ON intent_classification_log(was_correct) WHERE was_correct IS NOT NULL;

-- =============================================================================
-- COMMENTS
-- =============================================================================
COMMENT ON TABLE user_command_preferences IS 'Tracks per-user command usage for adaptive menu personalization';
COMMENT ON TABLE intent_command_mapping IS 'Maps intents to slash commands for fallback routing and menu display';
COMMENT ON TABLE intent_classification_log IS 'Logs intent classifications for ML improvement and debugging';

COMMENT ON COLUMN user_command_preferences.is_pinned IS 'User manually pinned this command to always show at top';
COMMENT ON COLUMN user_command_preferences.is_hidden IS 'User manually hid this command from their menu';
COMMENT ON COLUMN intent_command_mapping.priority IS 'Default display order - lower number = higher priority';
COMMENT ON COLUMN intent_classification_log.was_correct IS 'User feedback: NULL=no feedback, TRUE=correct, FALSE=wrong intent';
