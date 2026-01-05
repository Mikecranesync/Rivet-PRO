-- Migration 006: Interaction History & Manual Requests (Final Links)
-- Vision: RIVET_PRO_BUILD_SPEC.md - Track interactions and manual requests
-- Dependencies: All previous migrations (users, equipment_models, work_orders, etc.)

-- Interaction history (feeds analytics and CMMS)
CREATE TABLE interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    equipment_model_id UUID REFERENCES equipment_models(id) ON DELETE SET NULL,
    work_order_id UUID REFERENCES work_orders(id) ON DELETE SET NULL,

    -- Interaction type
    interaction_type VARCHAR(50) NOT NULL,  -- 'manual_lookup', 'troubleshoot', 'chat', 'equipment_create', 'wo_create'

    -- OCR data (if photo was sent)
    ocr_raw_text TEXT,
    ocr_confidence FLOAT,
    user_confirmed BOOLEAN,

    -- Outcome tracking
    outcome VARCHAR(50),  -- 'resolved', 'escalated', 'abandoned', 'manual_delivered', 'manual_not_found'
    notes TEXT,

    -- Performance metrics
    response_time_seconds FLOAT,
    llm_cost_usd FLOAT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_interaction_type CHECK (
        interaction_type IN (
            'manual_lookup',
            'troubleshoot',
            'chat_with_manual',
            'equipment_create',
            'wo_create',
            'feedback',
            'tribal_knowledge'
        )
    ),
    CONSTRAINT check_outcome CHECK (
        outcome IN (
            'resolved',
            'escalated',
            'abandoned',
            'manual_delivered',
            'manual_not_found',
            'equipment_created',
            'wo_created'
        )
    )
);

-- Manual request queue (for unfound manuals)
CREATE TABLE manual_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- OCR data from photo
    ocr_text TEXT,
    manufacturer_guess VARCHAR(255),
    model_guess VARCHAR(255),
    photo_url VARCHAR(1000),  -- S3 or Telegram file_id

    -- Request status
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'found', 'unfindable', 'duplicate'
    resolved_manual_id UUID REFERENCES manuals(id) ON DELETE SET NULL,
    resolved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    resolved_at TIMESTAMPTZ,

    -- Admin notes
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_request_status CHECK (
        status IN ('pending', 'found', 'unfindable', 'duplicate')
    )
);

-- Indexes for interactions
CREATE INDEX idx_interactions_user ON interactions(user_id);
CREATE INDEX idx_interactions_equipment_model ON interactions(equipment_model_id);
CREATE INDEX idx_interactions_work_order ON interactions(work_order_id);
CREATE INDEX idx_interactions_type ON interactions(interaction_type);
CREATE INDEX idx_interactions_outcome ON interactions(outcome);
CREATE INDEX idx_interactions_created ON interactions(created_at DESC);

-- Indexes for manual requests
CREATE INDEX idx_manual_requests_user ON manual_requests(user_id);
CREATE INDEX idx_manual_requests_status ON manual_requests(status);
CREATE INDEX idx_manual_requests_created ON manual_requests(created_at DESC);

-- Auto-update manual_requests timestamp
CREATE TRIGGER manual_requests_updated_at
    BEFORE UPDATE ON manual_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE interactions IS 'Interaction history for all user activities (manual lookup, troubleshooting, CMMS)';
COMMENT ON TABLE manual_requests IS 'Queue of unfound manual requests for admin follow-up';
COMMENT ON COLUMN interactions.interaction_type IS 'Type of interaction (manual_lookup, troubleshoot, chat, etc.)';
COMMENT ON COLUMN interactions.outcome IS 'Result of the interaction (resolved, escalated, etc.)';
COMMENT ON COLUMN interactions.ocr_confidence IS 'OCR confidence score (0.0-1.0) if photo was sent';
COMMENT ON COLUMN manual_requests.status IS 'Request status (pending, found, unfindable, duplicate)';

-- Additional foreign key constraints for user_machines → cmms_equipment link
-- (This allows users to link their personal machine library to CMMS equipment instances)
ALTER TABLE cmms_equipment
    ADD CONSTRAINT fk_cmms_equipment_machine
    FOREIGN KEY (machine_id) REFERENCES user_machines(id) ON DELETE SET NULL;

-- Link work_orders to user_machines
ALTER TABLE work_orders
    ADD CONSTRAINT fk_work_orders_machine
    FOREIGN KEY (machine_id) REFERENCES user_machines(id) ON DELETE SET NULL;

-- Final validation view: Shows the complete unified schema
CREATE OR REPLACE VIEW schema_health AS
SELECT
    'users' AS table_name,
    COUNT(*) AS row_count,
    pg_size_pretty(pg_total_relation_size('users')) AS table_size
FROM users
UNION ALL
SELECT 'teams', COUNT(*), pg_size_pretty(pg_total_relation_size('teams')) FROM teams
UNION ALL
SELECT 'manufacturers', COUNT(*), pg_size_pretty(pg_total_relation_size('manufacturers')) FROM manufacturers
UNION ALL
SELECT 'equipment_models', COUNT(*), pg_size_pretty(pg_total_relation_size('equipment_models')) FROM equipment_models
UNION ALL
SELECT 'manuals', COUNT(*), pg_size_pretty(pg_total_relation_size('manuals')) FROM manuals
UNION ALL
SELECT 'manual_chunks', COUNT(*), pg_size_pretty(pg_total_relation_size('manual_chunks')) FROM manual_chunks
UNION ALL
SELECT 'tech_notes', COUNT(*), pg_size_pretty(pg_total_relation_size('tech_notes')) FROM tech_notes
UNION ALL
SELECT 'cmms_equipment', COUNT(*), pg_size_pretty(pg_total_relation_size('cmms_equipment')) FROM cmms_equipment
UNION ALL
SELECT 'work_orders', COUNT(*), pg_size_pretty(pg_total_relation_size('work_orders')) FROM work_orders
UNION ALL
SELECT 'user_machines', COUNT(*), pg_size_pretty(pg_total_relation_size('user_machines')) FROM user_machines
UNION ALL
SELECT 'interactions', COUNT(*), pg_size_pretty(pg_total_relation_size('interactions')) FROM interactions
UNION ALL
SELECT 'manual_requests', COUNT(*), pg_size_pretty(pg_total_relation_size('manual_requests')) FROM manual_requests
ORDER BY table_name;

COMMENT ON VIEW schema_health IS 'Health check view showing all tables with row counts and sizes';
