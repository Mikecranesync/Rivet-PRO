-- Migration 024: Pipeline Execution History
-- Create pipeline_execution_history table to track pipeline execution states
-- Tracks state transitions for all workflows with flexible metadata storage

CREATE TABLE IF NOT EXISTS pipeline_execution_history (
    id SERIAL PRIMARY KEY,

    -- Workflow identification
    workflow_type VARCHAR(255) NOT NULL,  -- e.g. 'manual_hunter', 'llm_judge', 'photo_processing'
    entity_id VARCHAR(255) NOT NULL,      -- e.g. work order ID, execution ID, etc.

    -- State tracking
    current_state VARCHAR(255) NOT NULL,  -- e.g. 'CREATED', 'IN_PROGRESS', 'PENDING_APPROVAL', 'COMPLETED', 'FAILED'
    previous_state VARCHAR(255),          -- previous state for tracking transitions

    -- Flexible metadata
    transition_data JSONB,                -- additional context: user_id, error_details, etc.

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_pipeline_exec_hist_type ON pipeline_execution_history(workflow_type);
CREATE INDEX IF NOT EXISTS idx_pipeline_exec_hist_entity ON pipeline_execution_history(entity_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_exec_hist_state ON pipeline_execution_history(current_state);
CREATE INDEX IF NOT EXISTS idx_pipeline_exec_hist_created ON pipeline_execution_history(created_at DESC);

-- Composite index for common queries (workflow + entity)
CREATE INDEX IF NOT EXISTS idx_pipeline_exec_hist_type_entity ON pipeline_execution_history(workflow_type, entity_id);

-- Composite index for active state queries (workflow + state)
CREATE INDEX IF NOT EXISTS idx_pipeline_exec_hist_type_state ON pipeline_execution_history(workflow_type, current_state);

-- GIN index for JSONB queries on transition_data
CREATE INDEX IF NOT EXISTS idx_pipeline_exec_hist_data ON pipeline_execution_history USING GIN (transition_data);

-- Create updated_at trigger function if not exists
CREATE OR REPLACE FUNCTION update_pipeline_execution_history_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for automatic updated_at timestamp
DROP TRIGGER IF EXISTS pipeline_execution_history_updated_at ON pipeline_execution_history;
CREATE TRIGGER pipeline_execution_history_updated_at
    BEFORE UPDATE ON pipeline_execution_history
    FOR EACH ROW
    EXECUTE FUNCTION update_pipeline_execution_history_updated_at();

-- Comments for documentation
COMMENT ON TABLE pipeline_execution_history IS 'Tracks execution states and transitions for all pipeline workflows';
COMMENT ON COLUMN pipeline_execution_history.workflow_type IS 'Type of workflow: sme_agent, photo_processing, etc.';
COMMENT ON COLUMN pipeline_execution_history.entity_id IS 'Unique identifier for the entity being processed (work order ID, execution ID, etc.)';
COMMENT ON COLUMN pipeline_execution_history.current_state IS 'Current state: CREATED, IN_PROGRESS, PENDING_APPROVAL, APPROVED, REJECTED, COMPLETED, FAILED';
COMMENT ON COLUMN pipeline_execution_history.previous_state IS 'Previous state for tracking transitions';
COMMENT ON COLUMN pipeline_execution_history.transition_data IS 'JSONB field for flexible metadata: user_id, error_details, step_data, etc.';