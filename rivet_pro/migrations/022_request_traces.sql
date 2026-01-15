-- Migration 022: Request Traces
-- End-to-end tracing for all Telegram bot requests
-- Enables debugging, analytics, and visibility into message flow

CREATE TABLE IF NOT EXISTS request_traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id TEXT NOT NULL UNIQUE,
    telegram_id BIGINT NOT NULL,
    username TEXT,
    request_type TEXT NOT NULL,  -- 'photo', 'text', 'command'
    steps JSONB NOT NULL DEFAULT '[]'::jsonb,  -- Array of step objects
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,  -- outcome, duration, cost
    outcome TEXT,  -- 'success', 'error', 'partial', 'manual_not_found'
    total_duration_ms INT,
    llm_cost_usd DECIMAL(10,6) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_traces_telegram_id ON request_traces(telegram_id);
CREATE INDEX IF NOT EXISTS idx_traces_created_at ON request_traces(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_traces_outcome ON request_traces(outcome);
CREATE INDEX IF NOT EXISTS idx_traces_request_type ON request_traces(request_type);

-- Index for querying steps by name (for debugging specific step failures)
CREATE INDEX IF NOT EXISTS idx_traces_steps ON request_traces USING GIN (steps);

-- Comment for documentation
COMMENT ON TABLE request_traces IS 'End-to-end request traces for debugging and analytics. Each row = one user request from receipt to response.';
COMMENT ON COLUMN request_traces.trace_id IS 'Unique trace ID (tr_xxxxxxxxxxxx format)';
COMMENT ON COLUMN request_traces.steps IS 'Array of {step, name, timestamp, duration_ms, status, data} objects';
COMMENT ON COLUMN request_traces.summary IS 'Final stats: total_duration_ms, outcome, llm_cost_usd, steps_completed, steps_failed';
