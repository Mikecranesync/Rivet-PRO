-- Migration 002: Knowledge Base Layer (Manufacturers, Equipment Models, Manuals)
-- Vision: RIVET_PRO_BUILD_SPEC.md - Manual lookup and knowledge base
-- Dependencies: 001_saas_layer.sql (users table for tech_notes)

-- Enable pgvector for embeddings (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- Manufacturers table (canonical)
CREATE TABLE manufacturers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    aliases TEXT[],  -- ["ABB", "Asea Brown Boveri", "Baldor"]
    website VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Equipment models table (canonical knowledge: "What IS a Siemens G120C?")
CREATE TABLE equipment_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manufacturer_id UUID REFERENCES manufacturers(id) ON DELETE CASCADE,
    model_number VARCHAR(255) NOT NULL,
    model_aliases TEXT[],  -- Alternative model numbers
    equipment_type VARCHAR(100),  -- drive, plc, contactor, hmi, sensor, etc.
    specifications JSONB,  -- Flexible specs (voltage, power, i/o count, etc.)

    -- Extracted from OCR/manuals
    voltage_rating VARCHAR(50),
    power_rating VARCHAR(50),
    current_rating VARCHAR(50),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(manufacturer_id, model_number)
);

-- Manuals table (PDFs and documentation)
CREATE TABLE manuals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_model_id UUID REFERENCES equipment_models(id) ON DELETE CASCADE,

    title VARCHAR(500) NOT NULL,
    file_url VARCHAR(1000),  -- S3 or local path
    file_hash VARCHAR(64),  -- SHA-256 for deduplication
    file_size_bytes BIGINT,
    page_count INTEGER,

    -- Manual metadata
    manual_type VARCHAR(50) DEFAULT 'user_manual',  -- user_manual, service_manual, quick_start, datasheet
    language VARCHAR(10) DEFAULT 'en',
    version VARCHAR(50),
    published_date DATE,

    -- Source tracking
    source VARCHAR(50) NOT NULL,  -- 'manufacturer', 'web_search', 'user_upload'
    source_url VARCHAR(1000),  -- Original download URL

    -- Indexing status
    indexed_at TIMESTAMPTZ,
    embedding_model VARCHAR(100),  -- e.g., 'text-embedding-3-small'

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_manual_type CHECK (
        manual_type IN ('user_manual', 'service_manual', 'quick_start', 'datasheet', 'schematic', 'parts_list')
    ),
    CONSTRAINT check_source CHECK (
        source IN ('manufacturer', 'web_search', 'user_upload')
    )
);

-- Manual chunks (for RAG / vector search)
CREATE TABLE manual_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manual_id UUID REFERENCES manuals(id) ON DELETE CASCADE,

    content TEXT NOT NULL,
    page_number INTEGER,
    chunk_index INTEGER,  -- Order within the manual
    embedding vector(1536),  -- OpenAI text-embedding-3-small dimension

    -- Metadata extracted from chunk
    section_title TEXT,
    keywords TEXT[],

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(manual_id, chunk_index)
);

-- Tribal knowledge (user-contributed tips)
CREATE TABLE tech_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_model_id UUID REFERENCES equipment_models(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,

    content TEXT NOT NULL,
    note_type VARCHAR(50) DEFAULT 'tip',  -- tip, warning, workaround, faq
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,

    -- Moderation
    is_approved BOOLEAN DEFAULT FALSE,
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_note_type CHECK (
        note_type IN ('tip', 'warning', 'workaround', 'faq', 'common_issue')
    )
);

-- Indexes for performance
CREATE INDEX idx_equipment_models_manufacturer ON equipment_models(manufacturer_id);
CREATE INDEX idx_equipment_models_type ON equipment_models(equipment_type);
CREATE INDEX idx_equipment_models_model_number ON equipment_models(model_number);

CREATE INDEX idx_manuals_equipment_model ON manuals(equipment_model_id);
CREATE INDEX idx_manuals_source ON manuals(source);
CREATE INDEX idx_manuals_indexed ON manuals(indexed_at);

CREATE INDEX idx_manual_chunks_manual ON manual_chunks(manual_id);
CREATE INDEX idx_manual_chunks_page ON manual_chunks(page_number);

-- Vector similarity search index (IVFFlat for pgvector)
CREATE INDEX idx_manual_chunks_embedding ON manual_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX idx_tech_notes_equipment ON tech_notes(equipment_model_id);
CREATE INDEX idx_tech_notes_user ON tech_notes(user_id);
CREATE INDEX idx_tech_notes_approved ON tech_notes(is_approved);

-- Auto-update timestamps
CREATE TRIGGER update_manufacturers_updated_at
    BEFORE UPDATE ON manufacturers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_equipment_models_updated_at
    BEFORE UPDATE ON equipment_models
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_manuals_updated_at
    BEFORE UPDATE ON manuals
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tech_notes_updated_at
    BEFORE UPDATE ON tech_notes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE manufacturers IS 'Canonical list of equipment manufacturers';
COMMENT ON TABLE equipment_models IS 'Equipment model definitions (What IS a G120C?) - knowledge layer';
COMMENT ON TABLE manuals IS 'PDF manuals and documentation linked to equipment models';
COMMENT ON TABLE manual_chunks IS 'Chunked manual content with embeddings for RAG search';
COMMENT ON TABLE tech_notes IS 'User-contributed tribal knowledge and tips';

COMMENT ON COLUMN equipment_models.specifications IS 'Flexible JSONB for model-specific specs (voltage, power, I/O count, etc.)';
COMMENT ON COLUMN manuals.file_hash IS 'SHA-256 hash for deduplication of uploaded manuals';
COMMENT ON COLUMN manual_chunks.embedding IS 'Vector embedding for semantic search (1536 dimensions for OpenAI)';
COMMENT ON COLUMN tech_notes.upvotes IS 'Community voting for helpful tips';

-- Sample data for common manufacturers
INSERT INTO manufacturers (name, aliases, website) VALUES
    ('Siemens', ARRAY['Siemens AG', 'Siemens Industry'], 'https://siemens.com'),
    ('Rockwell Automation', ARRAY['Rockwell', 'Allen-Bradley', 'AB'], 'https://rockwellautomation.com'),
    ('ABB', ARRAY['Asea Brown Boveri', 'ABB Inc'], 'https://abb.com'),
    ('Schneider Electric', ARRAY['Schneider', 'Telemecanique', 'Modicon'], 'https://se.com'),
    ('Mitsubishi Electric', ARRAY['Mitsubishi', 'MELSEC'], 'https://mitsubishielectric.com'),
    ('Fanuc', ARRAY['FANUC Corporation'], 'https://fanuc.com'),
    ('Omron', ARRAY['Omron Corporation'], 'https://omron.com')
ON CONFLICT (name) DO NOTHING;
