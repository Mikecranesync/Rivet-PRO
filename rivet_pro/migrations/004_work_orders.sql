-- Migration 004: Work Orders Table (Adapted from rivet/atlas)
-- Vision: CLAUDE.md - Work orders linked to equipment for CMMS
-- Dependencies: 001_saas_layer.sql (users), 003_cmms_equipment.sql (cmms_equipment)

-- Create enums for work order tracking
CREATE TYPE source_type AS ENUM (
    'telegram_text',
    'telegram_voice',
    'telegram_photo',
    'telegram_print_qa',
    'telegram_manual_gap',
    'whatsapp_text',
    'whatsapp_voice',
    'whatsapp_photo'
);

CREATE TYPE route_type AS ENUM ('A', 'B', 'C', 'D');

CREATE TYPE work_order_status AS ENUM (
    'open',          -- Just created
    'in_progress',   -- Technician working on it
    'completed',     -- Fixed
    'cancelled'      -- No longer relevant
);

CREATE TYPE priority_level AS ENUM ('low', 'medium', 'high', 'critical');

-- Create work order sequence for auto-numbering
CREATE SEQUENCE work_order_seq START 1;

-- Function to generate work order numbers (WO-2025-0001)
CREATE OR REPLACE FUNCTION generate_work_order_number()
RETURNS VARCHAR(50) AS $$
DECLARE
    year_prefix VARCHAR(4);
    seq_num INTEGER;
    padded_num VARCHAR(6);
BEGIN
    year_prefix := TO_CHAR(NOW(), 'YYYY');
    seq_num := nextval('work_order_seq');
    padded_num := LPAD(seq_num::TEXT, 6, '0');
    RETURN 'WO-' || year_prefix || '-' || padded_num;
END;
$$ LANGUAGE plpgsql;

-- Create work orders table
CREATE TABLE work_orders (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_order_number VARCHAR(50) UNIQUE NOT NULL,

    -- User & Source (UUID now, not TEXT)
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    telegram_username VARCHAR(255),
    created_by_agent VARCHAR(100),  -- siemens_agent, rockwell_agent, etc.
    source source_type NOT NULL,

    -- Equipment (LINKED TO CMMS_EQUIPMENT - REQUIRED for equipment-first architecture)
    equipment_id UUID NOT NULL REFERENCES cmms_equipment(id) ON DELETE CASCADE,
    equipment_number VARCHAR(50),  -- Denormalized for quick reference

    -- Equipment Details (denormalized for query performance)
    manufacturer VARCHAR(255),
    model_number VARCHAR(255),
    serial_number VARCHAR(255),
    equipment_type VARCHAR(100),
    machine_id UUID,  -- Link to user_machines table
    location VARCHAR(500),

    -- Issue Details
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    fault_codes TEXT[],
    symptoms TEXT[],

    -- Response Metadata
    answer_text TEXT,
    confidence_score FLOAT,
    route_taken route_type,
    suggested_actions TEXT[],
    safety_warnings TEXT[],
    cited_kb_atoms TEXT[],
    manual_links TEXT[],

    -- Status & Priority
    status work_order_status DEFAULT 'open',
    priority priority_level DEFAULT 'medium',

    -- Audit Trail
    trace_id UUID,
    conversation_id UUID,
    research_triggered BOOLEAN DEFAULT FALSE,
    enrichment_triggered BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Trigger function to auto-set work order number
CREATE OR REPLACE FUNCTION set_work_order_number_trigger()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.work_order_number IS NULL THEN
        NEW.work_order_number := generate_work_order_number();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-set work order number on insert
CREATE TRIGGER set_work_order_number
    BEFORE INSERT ON work_orders
    FOR EACH ROW
    EXECUTE FUNCTION set_work_order_number_trigger();

-- Create indexes for performance
CREATE INDEX idx_work_orders_user ON work_orders(user_id);
CREATE INDEX idx_work_orders_equipment ON work_orders(equipment_id);
CREATE INDEX idx_work_orders_machine ON work_orders(machine_id);
CREATE INDEX idx_work_orders_status ON work_orders(status);
CREATE INDEX idx_work_orders_priority ON work_orders(priority);
CREATE INDEX idx_work_orders_created ON work_orders(created_at DESC);
CREATE INDEX idx_work_orders_trace ON work_orders(trace_id);
CREATE INDEX idx_work_orders_conversation ON work_orders(conversation_id);
CREATE INDEX idx_work_orders_source ON work_orders(source);
CREATE INDEX idx_work_orders_route ON work_orders(route_taken);

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_work_order_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER work_order_updated_at
    BEFORE UPDATE ON work_orders
    FOR EACH ROW
    EXECUTE FUNCTION update_work_order_timestamp();

-- Auto-update equipment statistics when work order created
CREATE OR REPLACE FUNCTION update_equipment_on_work_order()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.equipment_id IS NOT NULL THEN
        UPDATE cmms_equipment
        SET
            work_order_count = work_order_count + 1,
            last_work_order_at = NOW(),
            last_reported_fault = COALESCE(
                CASE
                    WHEN array_length(NEW.fault_codes, 1) > 0 THEN NEW.fault_codes[1]
                    ELSE last_reported_fault
                END,
                last_reported_fault
            ),
            updated_at = NOW()
        WHERE id = NEW.equipment_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER work_order_equipment_stats
    AFTER INSERT ON work_orders
    FOR EACH ROW
    EXECUTE FUNCTION update_equipment_on_work_order();

-- Comments for documentation
COMMENT ON TABLE work_orders IS 'Work orders created from Telegram/WhatsApp interactions. Always linked to equipment (equipment-first architecture).';
COMMENT ON COLUMN work_orders.work_order_number IS 'Auto-generated unique identifier (WO-2025-0001)';
COMMENT ON COLUMN work_orders.equipment_id IS 'Link to cmms_equipment table (canonical equipment record)';
COMMENT ON COLUMN work_orders.equipment_number IS 'Denormalized equipment number for quick reference without JOIN';
COMMENT ON COLUMN work_orders.user_id IS 'User who created work order (UUID reference to users table)';
COMMENT ON COLUMN work_orders.conversation_id IS 'Links multi-turn conversations (used for updating existing work orders)';
COMMENT ON COLUMN work_orders.trace_id IS 'Links to RequestTrace for audit trail';
COMMENT ON COLUMN work_orders.route_taken IS 'RIVET orchestrator route (A=KB, B=SME, C=Research, D=Clarification)';
COMMENT ON COLUMN work_orders.confidence_score IS 'AI confidence score (0.0-1.0) used for priority calculation';
