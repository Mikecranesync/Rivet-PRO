-- Migration 005: CMMS Equipment Table
-- Date: 2025-12-28
-- Description: Equipment asset tracking for CMMS work order integration

-- Create enum for equipment criticality
CREATE TYPE CriticalityLevel AS ENUM ('low', 'medium', 'high', 'critical');

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

-- Create equipment table
CREATE TABLE cmms_equipment (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_number VARCHAR(50) UNIQUE NOT NULL,

    -- Equipment Details
    manufacturer VARCHAR(255) NOT NULL,
    model_number VARCHAR(255),
    serial_number VARCHAR(255),
    equipment_type VARCHAR(100),

    -- Location & Context
    location VARCHAR(500),
    department VARCHAR(255),
    criticality CriticalityLevel DEFAULT 'medium',

    -- Ownership
    owned_by_user_id TEXT,
    machine_id UUID,  -- Link to user_machines table

    -- Metadata
    description TEXT,
    photo_file_id VARCHAR(500),
    installation_date DATE,
    last_maintenance_date DATE,

    -- Stats (updated automatically)
    work_order_count INTEGER DEFAULT 0,
    total_downtime_hours FLOAT DEFAULT 0.0,
    last_reported_fault VARCHAR(100),
    last_work_order_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    first_reported_by TEXT
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

-- Trigger to auto-set equipment number
CREATE TRIGGER set_equipment_number
BEFORE INSERT ON cmms_equipment
FOR EACH ROW
EXECUTE FUNCTION set_equipment_number_trigger();

-- Create indexes for performance
CREATE INDEX idx_equipment_manufacturer ON cmms_equipment(manufacturer);
CREATE INDEX idx_equipment_model ON cmms_equipment(model_number);
CREATE INDEX idx_equipment_serial ON cmms_equipment(serial_number);
CREATE INDEX idx_equipment_user ON cmms_equipment(owned_by_user_id);
CREATE INDEX idx_equipment_machine ON cmms_equipment(machine_id);
CREATE INDEX idx_equipment_location ON cmms_equipment(location);
CREATE INDEX idx_equipment_created ON cmms_equipment(created_at DESC);

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_equipment_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER equipment_updated_at
BEFORE UPDATE ON cmms_equipment
FOR EACH ROW
EXECUTE FUNCTION update_equipment_timestamp();

-- Comments for documentation
COMMENT ON TABLE cmms_equipment IS 'Equipment assets for CMMS work order tracking. Equipment-first architecture ensures work orders always link to canonical equipment records.';
COMMENT ON COLUMN cmms_equipment.equipment_number IS 'Auto-generated unique identifier (EQ-2025-0001)';
COMMENT ON COLUMN cmms_equipment.machine_id IS 'Optional link to user''s machine library (user_machines table)';
COMMENT ON COLUMN cmms_equipment.work_order_count IS 'Total number of work orders for this equipment (auto-updated)';
COMMENT ON COLUMN cmms_equipment.criticality IS 'Equipment criticality level for prioritization (low/medium/high/critical)';
