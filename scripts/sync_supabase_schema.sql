-- Supabase Failover Schema Sync
-- Run this on Supabase to enable CMMS failover functionality
-- Generated: 2026-01-15

-- Drop existing objects if they exist (safe for re-runs)
DROP TABLE IF EXISTS work_orders CASCADE;
DROP TABLE IF EXISTS cmms_equipment CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS interactions CASCADE;
DROP TABLE IF EXISTS manual_cache CASCADE;
DROP SEQUENCE IF EXISTS equipment_seq;
DROP SEQUENCE IF EXISTS work_order_seq;
DROP TYPE IF EXISTS criticality_level CASCADE;
DROP TYPE IF EXISTS source_type CASCADE;
DROP TYPE IF EXISTS route_type CASCADE;
DROP TYPE IF EXISTS work_order_status CASCADE;
DROP TYPE IF EXISTS priority_level CASCADE;
DROP TYPE IF EXISTS feedback_type CASCADE;

-- Create enums
CREATE TYPE criticality_level AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE source_type AS ENUM (
    'telegram_text', 'telegram_voice', 'telegram_photo',
    'telegram_print_qa', 'telegram_manual_gap',
    'whatsapp_text', 'whatsapp_voice', 'whatsapp_photo'
);
CREATE TYPE route_type AS ENUM ('A', 'B', 'C', 'D');
CREATE TYPE work_order_status AS ENUM ('open', 'in_progress', 'completed', 'cancelled');
CREATE TYPE priority_level AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE feedback_type AS ENUM ('positive', 'negative', 'none');

-- Create sequences
CREATE SEQUENCE equipment_seq START 1;
CREATE SEQUENCE work_order_seq START 1;

-- Users table (minimal for failover)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE,
    full_name VARCHAR(255),
    username VARCHAR(255),
    subscription_tier VARCHAR(50) DEFAULT 'free',
    subscription_status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_active TIMESTAMPTZ DEFAULT NOW()
);

-- CMMS Equipment table (TEXT user IDs for compatibility)
CREATE TABLE cmms_equipment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_number VARCHAR(50) UNIQUE NOT NULL,
    equipment_model_id UUID,
    manufacturer VARCHAR(255) NOT NULL,
    model_number VARCHAR(255),
    serial_number VARCHAR(255),
    equipment_type VARCHAR(100),
    location VARCHAR(500),
    department VARCHAR(255),
    criticality criticality_level DEFAULT 'medium',
    owned_by_user_id TEXT,  -- TEXT for telegram_xxx format
    first_reported_by TEXT, -- TEXT for telegram_xxx format
    machine_id UUID,
    description TEXT,
    photo_file_id VARCHAR(500),
    installation_date DATE,
    last_maintenance_date DATE,
    work_order_count INTEGER DEFAULT 0,
    total_downtime_hours FLOAT DEFAULT 0.0,
    last_reported_fault VARCHAR(100),
    last_work_order_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Work Orders table (TEXT user IDs for compatibility)
CREATE TABLE work_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_order_number VARCHAR(50) UNIQUE NOT NULL,
    user_id TEXT NOT NULL,  -- TEXT for telegram_xxx format
    telegram_username VARCHAR(255),
    created_by_agent VARCHAR(100),
    source source_type NOT NULL,
    equipment_id UUID REFERENCES cmms_equipment(id) ON DELETE CASCADE,
    equipment_number VARCHAR(50),
    manufacturer VARCHAR(255),
    model_number VARCHAR(255),
    serial_number VARCHAR(255),
    equipment_type VARCHAR(100),
    machine_id UUID,
    location VARCHAR(500),
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    fault_codes TEXT[],
    symptoms TEXT[],
    answer_text TEXT,
    confidence_score FLOAT,
    route_taken route_type,
    suggested_actions TEXT[],
    safety_warnings TEXT[],
    cited_kb_atoms TEXT[],
    manual_links TEXT[],
    status work_order_status DEFAULT 'open',
    priority priority_level DEFAULT 'medium',
    trace_id UUID,
    conversation_id UUID,
    research_triggered BOOLEAN DEFAULT FALSE,
    enrichment_triggered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    feedback_at TIMESTAMPTZ,
    user_feedback feedback_type DEFAULT 'none'
);

-- Interactions table (for tracking user actions)
CREATE TABLE interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    equipment_model_id UUID,
    work_order_id UUID,
    interaction_type VARCHAR(50) NOT NULL,
    ocr_raw_text TEXT,
    ocr_confidence FLOAT,
    user_confirmed BOOLEAN,
    outcome VARCHAR(100),
    notes TEXT,
    response_time_seconds FLOAT,
    llm_cost_usd FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    story_id VARCHAR(50),
    approval_status VARCHAR(50) DEFAULT 'pending',
    approved_at TIMESTAMPTZ,
    feedback_text TEXT,
    context_data JSONB,
    atom_id TEXT,
    atom_created BOOLEAN DEFAULT FALSE
);

-- Manual Cache table
CREATE TABLE manual_cache (
    id SERIAL PRIMARY KEY,
    manufacturer VARCHAR(255) NOT NULL,
    model VARCHAR(255) NOT NULL,
    manual_url TEXT NOT NULL,
    pdf_stored BOOLEAN DEFAULT FALSE,
    confidence_score NUMERIC,
    found_via VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMPTZ,
    manual_title VARCHAR(500),
    source VARCHAR(100) DEFAULT 'tavily',
    verified BOOLEAN DEFAULT FALSE,
    found_at TIMESTAMPTZ DEFAULT NOW(),
    llm_validated BOOLEAN DEFAULT FALSE,
    llm_confidence FLOAT,
    validation_reasoning TEXT,
    manual_type VARCHAR(100),
    atom_id TEXT,
    product_family_id UUID,
    local_file_available BOOLEAN DEFAULT FALSE,
    download_priority INTEGER DEFAULT 5
);

-- Create indexes
CREATE INDEX idx_cmms_equipment_manufacturer ON cmms_equipment(manufacturer);
CREATE INDEX idx_cmms_equipment_model ON cmms_equipment(model_number);
CREATE INDEX idx_cmms_equipment_serial ON cmms_equipment(serial_number);
CREATE INDEX idx_cmms_equipment_user ON cmms_equipment(owned_by_user_id);
CREATE INDEX idx_cmms_equipment_created ON cmms_equipment(created_at DESC);

CREATE INDEX idx_work_orders_user ON work_orders(user_id);
CREATE INDEX idx_work_orders_equipment ON work_orders(equipment_id);
CREATE INDEX idx_work_orders_status ON work_orders(status);
CREATE INDEX idx_work_orders_created ON work_orders(created_at DESC);

CREATE INDEX idx_users_telegram ON users(telegram_id);

CREATE INDEX idx_manual_cache_lookup ON manual_cache(LOWER(manufacturer), LOWER(model));

-- Functions for auto-numbering
CREATE OR REPLACE FUNCTION generate_equipment_number()
RETURNS VARCHAR(50) AS $$
DECLARE
    year_prefix VARCHAR(4);
    seq_num INTEGER;
BEGIN
    year_prefix := TO_CHAR(NOW(), 'YYYY');
    seq_num := nextval('equipment_seq');
    RETURN 'EQ-' || year_prefix || '-' || LPAD(seq_num::TEXT, 6, '0');
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION generate_work_order_number()
RETURNS VARCHAR(50) AS $$
DECLARE
    year_prefix VARCHAR(4);
    seq_num INTEGER;
BEGIN
    year_prefix := TO_CHAR(NOW(), 'YYYY');
    seq_num := nextval('work_order_seq');
    RETURN 'WO-' || year_prefix || '-' || LPAD(seq_num::TEXT, 6, '0');
END;
$$ LANGUAGE plpgsql;

-- Auto-set equipment number trigger
CREATE OR REPLACE FUNCTION set_equipment_number_trigger()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.equipment_number IS NULL THEN
        NEW.equipment_number := generate_equipment_number();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_equipment_number
    BEFORE INSERT ON cmms_equipment
    FOR EACH ROW
    EXECUTE FUNCTION set_equipment_number_trigger();

-- Auto-set work order number trigger
CREATE OR REPLACE FUNCTION set_work_order_number_trigger()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.work_order_number IS NULL THEN
        NEW.work_order_number := generate_work_order_number();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_work_order_number
    BEFORE INSERT ON work_orders
    FOR EACH ROW
    EXECUTE FUNCTION set_work_order_number_trigger();

-- Comments
COMMENT ON TABLE cmms_equipment IS 'CMMS equipment for failover (synced from Neon)';
COMMENT ON TABLE work_orders IS 'Work orders for failover (synced from Neon)';
COMMENT ON TABLE users IS 'Users table for failover (synced from Neon)';

-- NOTE: Run the Python sync script after this to copy data from Neon
