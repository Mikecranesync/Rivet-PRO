-- Migration 014: User Feedback Loop System
-- Purpose: Enable users to report issues via Telegram, trigger Ralph fixes with approval workflow
-- Created: 2026-01-12

-- ============================================================================
-- PART 1: Extend Interactions Table for Feedback
-- ============================================================================

-- Add feedback-related columns to interactions
ALTER TABLE interactions
ADD COLUMN story_id VARCHAR(50),
ADD COLUMN approval_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN approved_at TIMESTAMPTZ,
ADD COLUMN feedback_text TEXT,
ADD COLUMN context_data JSONB;

-- Add foreign key to ralph_stories (will be created if doesn't exist)
ALTER TABLE interactions
ADD CONSTRAINT fk_interactions_story
FOREIGN KEY (story_id) REFERENCES ralph_stories(story_id)
ON DELETE SET NULL;

-- Update interaction type constraint to include new feedback types
ALTER TABLE interactions DROP CONSTRAINT IF EXISTS check_interaction_type;
ALTER TABLE interactions ADD CONSTRAINT check_interaction_type CHECK (
    interaction_type IN (
        'manual_lookup',
        'troubleshoot',
        'chat_with_manual',
        'equipment_create',
        'wo_create',
        'feedback',
        'tribal_knowledge',
        'fix_proposal',
        'fix_approved',
        'fix_rejected'
    )
);

-- Performance index for feedback queries
CREATE INDEX idx_interactions_feedback
ON interactions(user_id, created_at DESC)
WHERE interaction_type = 'feedback';

-- Index for pending approvals
CREATE INDEX idx_interactions_pending_approval
ON interactions(approval_status, created_at DESC)
WHERE approval_status = 'pending';

-- ============================================================================
-- PART 2: Extend Ralph Stories Table for Approval Workflow
-- ============================================================================

-- Add approval workflow columns to ralph_stories
ALTER TABLE ralph_stories
ADD COLUMN feedback_interaction_id UUID,
ADD COLUMN approval_status VARCHAR(20) DEFAULT 'auto_approved',
ADD COLUMN proposal_text TEXT,
ADD COLUMN approved_by_telegram_id VARCHAR(100),
ADD COLUMN approved_at TIMESTAMPTZ,
ADD COLUMN feedback_type VARCHAR(50);

-- Add foreign key back to interactions (bidirectional linking)
ALTER TABLE ralph_stories
ADD CONSTRAINT fk_ralph_stories_interaction
FOREIGN KEY (feedback_interaction_id) REFERENCES interactions(id)
ON DELETE SET NULL;

-- Performance index for approval queries
CREATE INDEX idx_ralph_stories_approval
ON ralph_stories(approval_status, created_at DESC)
WHERE approval_status IN ('pending_approval', 'approved');

-- Index for feedback-triggered stories
CREATE INDEX idx_ralph_stories_feedback
ON ralph_stories(feedback_type, created_at DESC)
WHERE feedback_type IS NOT NULL;

-- ============================================================================
-- PART 3: Add Check Constraints for Data Integrity
-- ============================================================================

-- Ensure approval_status is valid
ALTER TABLE interactions ADD CONSTRAINT check_approval_status CHECK (
    approval_status IN ('pending', 'approved', 'rejected', 'expired', 'auto_approved')
);

-- Ensure ralph_stories approval_status is valid
ALTER TABLE ralph_stories ADD CONSTRAINT check_ralph_approval_status CHECK (
    approval_status IN ('auto_approved', 'pending_approval', 'approved', 'rejected', 'expired')
);

-- Ensure feedback_type is valid
ALTER TABLE ralph_stories ADD CONSTRAINT check_feedback_type CHECK (
    feedback_type IS NULL OR feedback_type IN (
        'manual_404',
        'wrong_manual',
        'wrong_equipment',
        'ocr_failure',
        'unclear_answer',
        'performance_issue',
        'general_bug',
        'feature_request'
    )
);

-- ============================================================================
-- PART 4: Functions for Common Operations
-- ============================================================================

-- Function to automatically expire pending approvals after timeout
CREATE OR REPLACE FUNCTION expire_pending_approvals()
RETURNS INTEGER AS $$
DECLARE
    expired_count INTEGER;
BEGIN
    -- Get timeout from environment (default 24 hours)
    WITH expired AS (
        UPDATE interactions
        SET approval_status = 'expired'
        WHERE approval_status = 'pending'
          AND created_at < NOW() - INTERVAL '24 hours'
        RETURNING id
    )
    SELECT COUNT(*) INTO expired_count FROM expired;

    -- Also expire corresponding Ralph stories
    UPDATE ralph_stories
    SET approval_status = 'expired'
    WHERE approval_status = 'pending_approval'
      AND created_at < NOW() - INTERVAL '24 hours';

    RETURN expired_count;
END;
$$ LANGUAGE plpgsql;

-- Function to link interaction and story bidirectionally
CREATE OR REPLACE FUNCTION link_feedback_and_story(
    p_interaction_id UUID,
    p_story_id VARCHAR(50)
)
RETURNS VOID AS $$
BEGIN
    -- Update interaction with story_id
    UPDATE interactions
    SET story_id = p_story_id
    WHERE id = p_interaction_id;

    -- Update story with interaction_id
    UPDATE ralph_stories
    SET feedback_interaction_id = p_interaction_id
    WHERE story_id = p_story_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PART 5: Views for Monitoring
-- ============================================================================

-- View: Pending feedback awaiting user approval
CREATE OR REPLACE VIEW pending_feedback_proposals AS
SELECT
    i.id AS interaction_id,
    i.user_id,
    i.feedback_text,
    i.context_data,
    i.created_at AS feedback_created_at,
    rs.story_id,
    rs.title AS proposal_title,
    rs.proposal_text,
    rs.priority,
    EXTRACT(EPOCH FROM (NOW() - i.created_at))/3600 AS hours_pending
FROM interactions i
JOIN ralph_stories rs ON i.story_id = rs.story_id
WHERE i.approval_status = 'pending'
  AND rs.approval_status = 'pending_approval'
ORDER BY i.created_at ASC;

-- View: Approved stories ready for execution
CREATE OR REPLACE VIEW approved_feedback_stories AS
SELECT
    rs.story_id,
    rs.title,
    rs.description,
    rs.feedback_type,
    rs.priority,
    rs.approved_by_telegram_id,
    rs.approved_at,
    i.feedback_text,
    i.context_data,
    u.telegram_user_id,
    u.username
FROM ralph_stories rs
JOIN interactions i ON rs.feedback_interaction_id = i.id
JOIN users u ON i.user_id = u.id
WHERE rs.approval_status = 'approved'
  AND rs.status = 'todo'
ORDER BY rs.priority ASC, rs.approved_at ASC;

-- View: Feedback statistics
CREATE OR REPLACE VIEW feedback_statistics AS
SELECT
    feedback_type,
    approval_status,
    COUNT(*) AS count,
    AVG(EXTRACT(EPOCH FROM (approved_at - created_at))/60) AS avg_approval_time_minutes
FROM ralph_stories
WHERE feedback_type IS NOT NULL
GROUP BY feedback_type, approval_status;

-- ============================================================================
-- PART 6: Sample Data for Testing
-- ============================================================================

-- Insert test feedback interaction (commented out - uncomment for testing)
/*
INSERT INTO interactions (
    id,
    user_id,
    interaction_type,
    feedback_text,
    context_data,
    approval_status,
    outcome
) VALUES (
    gen_random_uuid(),
    (SELECT id FROM users LIMIT 1),
    'feedback',
    'Manual link returns 404 error',
    '{"equipment_number": "EQ-2026-000001", "manufacturer": "Siemens", "model": "G120", "manual_url": "https://example.com/manual.pdf"}',
    'pending',
    'awaiting_proposal'
);
*/

-- ============================================================================
-- PART 7: Grants (adjust based on your user roles)
-- ============================================================================

-- Grant permissions to application user (adjust username as needed)
-- GRANT SELECT, INSERT, UPDATE ON interactions TO rivet_app;
-- GRANT SELECT, INSERT, UPDATE ON ralph_stories TO rivet_app;
-- GRANT EXECUTE ON FUNCTION expire_pending_approvals() TO rivet_app;
-- GRANT EXECUTE ON FUNCTION link_feedback_and_story(UUID, VARCHAR) TO rivet_app;

-- ============================================================================
-- Migration Complete
-- ============================================================================

COMMENT ON COLUMN interactions.story_id IS 'Links feedback to the Ralph story created to address it';
COMMENT ON COLUMN interactions.approval_status IS 'Status of user approval for proposed fix (pending/approved/rejected/expired)';
COMMENT ON COLUMN interactions.feedback_text IS 'User-provided description of the issue';
COMMENT ON COLUMN interactions.context_data IS 'JSONB context extracted from bot message (equipment_id, manual_url, etc.)';

COMMENT ON COLUMN ralph_stories.feedback_interaction_id IS 'Links story back to the feedback interaction that triggered it';
COMMENT ON COLUMN ralph_stories.approval_status IS 'Approval workflow status (auto_approved/pending_approval/approved/rejected)';
COMMENT ON COLUMN ralph_stories.proposal_text IS 'Human-readable fix proposal sent to user for approval';
COMMENT ON COLUMN ralph_stories.approved_by_telegram_id IS 'Telegram user ID who approved the fix';
COMMENT ON COLUMN ralph_stories.feedback_type IS 'Category of feedback (manual_404, wrong_equipment, etc.)';
