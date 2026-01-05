-- Migration 003: CMMS Equipment Table (Adapted from rivet/atlas)
-- Vision: CLAUDE.md - Equipment asset tracking for CMMS work orders
-- Dependencies: 001_saas_layer.sql (users), 002_knowledge_base.sql (equipment_models)

-- Create enum for equipment criticality
CREATE TYPE criticality_level AS ENUM ('low', 'medium', 'high', 'critical');

-- Create equipment sequence for auto-numbering
CREATE SEQUENCE equipment_seq START 1;

-- Function to generate equipment numbers (EQ-2025-0001)
CREATE OR REPLACE FUNCTION generate_equipment_number()
RETURNS VARCHAR(50) AS $$
DECLARE
    year_prefix VARCHAR(4);
    seq_num INTEGER;
    padded_num VARCHAR(6);
BEGIN
    year_prefix := TO_CHAR(NOW(), 'YYYY');
    seq_num := nextval('equipment_seq');
    padded_num := LPAD(seq_num::TEXT, 6, '0');
    RETURN 'EQ-' || year_prefix || '-' || padded_num;
END;
$$ LANGUAGE plpgsql;

-- Create CMMS equipment table
CREATE TABLE cmms_equipment (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_number VARCHAR(50) UNIQUE NOT NULL,

    -- CRITICAL LINK: Connect to knowledge base
    equipment_model_id UUID REFERENCES equipment_models(id) ON DELETE SET NULL,

    -- Equipment Details (from OCR or manual entry)
    manufacturer VARCHAR(255) NOT NULL,
    model_number VARCHAR(255),
    serial_number VARCHAR(255),
    equipment_type VARCHAR(100),

    -- Location & Context
    location VARCHAR(500),
    department VARCHAR(255),
    criticality criticality_level DEFAULT 'medium',

    -- Ownership (UUID now, not TEXT)
    owned_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    machine_id UUID,  -- Link to user_machines table

    -- Metadata
    description TEXT,
    photo_file_id VARCHAR(500),  -- Telegram file ID
    installation_date DATE,
    last_maintenance_date DATE,

    -- Stats (updated automatically by triggers)
    work_order_count INTEGER DEFAULT 0,
    total_downtime_hours FLOAT DEFAULT 0.0,
    last_reported_fault VARCHAR(100),
    last_work_order_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    first_reported_by UUID REFERENCES users(id) ON DELETE SET NULL
);

-- Trigger function to auto-set equipment number
CREATE OR REPLACE FUNCTION set_equipment_number_trigger()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.equipment_number IS NULL THEN
        NEW.equipment_number := generate_equipment_number();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-set equipment number on insert
CREATE TRIGGER set_equipment_number
    BEFORE INSERT ON cmms_equipment
    FOR EACH ROW
    EXECUTE FUNCTION set_equipment_number_trigger();

-- Auto-link equipment_model_id if manufacturer + model match
CREATE OR REPLACE FUNCTION auto_link_equipment_model()
RETURNS TRIGGER AS $$
DECLARE
    matching_model_id UUID;
BEGIN
    -- If equipment_model_id is NULL, try to find a match
    IF NEW.equipment_model_id IS NULL AND NEW.manufacturer IS NOT NULL AND NEW.model_number IS NOT NULL THEN
        SELECT em.id INTO matching_model_id
        FROM equipment_models em
        JOIN manufacturers m ON m.id = em.manufacturer_id
        WHERE m.name = NEW.manufacturer
          AND em.model_number = NEW.model_number
        LIMIT 1;

        IF matching_model_id IS NOT NULL THEN
            NEW.equipment_model_id := matching_model_id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-link equipment model on insert/update
CREATE TRIGGER auto_link_equipment_model_trigger
    BEFORE INSERT OR UPDATE ON cmms_equipment
    FOR EACH ROW
    EXECUTE FUNCTION auto_link_equipment_model();

-- Create indexes for performance
CREATE INDEX idx_cmms_equipment_manufacturer ON cmms_equipment(manufacturer);
CREATE INDEX idx_cmms_equipment_model ON cmms_equipment(model_number);
CREATE INDEX idx_cmms_equipment_serial ON cmms_equipment(serial_number);
CREATE INDEX idx_cmms_equipment_user ON cmms_equipment(owned_by_user_id);
CREATE INDEX idx_cmms_equipment_machine ON cmms_equipment(machine_id);
CREATE INDEX idx_cmms_equipment_location ON cmms_equipment(location);
CREATE INDEX idx_cmms_equipment_created ON cmms_equipment(created_at DESC);
CREATE INDEX idx_cmms_equipment_model_id ON cmms_equipment(equipment_model_id);
CREATE INDEX idx_cmms_equipment_criticality ON cmms_equipment(criticality);

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_cmms_equipment_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER cmms_equipment_updated_at
    BEFORE UPDATE ON cmms_equipment
    FOR EACH ROW
    EXECUTE FUNCTION update_cmms_equipment_timestamp();

-- Comments for documentation
COMMENT ON TABLE cmms_equipment IS 'Equipment instances for CMMS (The G120C in Building A). Links to equipment_models for manual lookup.';
COMMENT ON COLUMN cmms_equipment.equipment_number IS 'Auto-generated unique identifier (EQ-2025-0001)';
COMMENT ON COLUMN cmms_equipment.equipment_model_id IS 'Link to equipment_models (knowledge base) for manual lookup';
COMMENT ON COLUMN cmms_equipment.manufacturer IS 'Manufacturer name (denormalized for search)';
COMMENT ON COLUMN cmms_equipment.model_number IS 'Model number (denormalized for search)';
COMMENT ON COLUMN cmms_equipment.machine_id IS 'Optional link to user machine library (user_machines table)';
COMMENT ON COLUMN cmms_equipment.work_order_count IS 'Total work orders for this equipment (auto-updated)';
COMMENT ON COLUMN cmms_equipment.criticality IS 'Equipment criticality for prioritization (low/medium/high/critical)';
COMMENT ON COLUMN cmms_equipment.owned_by_user_id IS 'User who owns this equipment (UUID reference to users table)';
