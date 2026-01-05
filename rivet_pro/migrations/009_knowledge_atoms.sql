-- Migration 009: Knowledge Atoms & Gap Detection (Self-Healing KB)
-- Vision: rivet_pro_skill_ai_routing.md - 4-route AI orchestrator
-- Dependencies: 002_knowledge_base.sql (pgvector extension, manufacturers table)

-- Knowledge atoms table (structured troubleshooting knowledge)
-- Difference from manual_chunks: Atoms are curated, atomic pieces of knowledge
-- (e.g., "F0021 fault means X", "Procedure to calibrate Y"), not raw manual text
CREATE TABLE knowledge_atoms (
    atom_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Categorization
    type VARCHAR(50) NOT NULL,  -- fault, procedure, spec, part, tip, safety
    manufacturer VARCHAR(255),  -- Optional: specific manufacturer
    model VARCHAR(255),         -- Optional: specific model
    equipment_type VARCHAR(100), -- Optional: drive, plc, sensor, etc.

    -- Content
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    source_url VARCHAR(1000),   -- Where this knowledge came from

    -- Quality metrics
    confidence FLOAT NOT NULL DEFAULT 0.5,  -- 0.0-1.0 how verified is this
    human_verified BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,  -- How many times this atom was returned

    -- Vector search
    embedding vector(1536),  -- OpenAI text-embedding-3-small dimension

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_verified TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_atom_type CHECK (
        type IN ('fault', 'procedure', 'spec', 'part', 'tip', 'safety')
    ),
    CONSTRAINT check_confidence CHECK (
        confidence >= 0.0 AND confidence <= 1.0
    )
);

-- Knowledge gaps table (self-healing KB tracking)
-- Tracks queries where KB confidence was low → triggers research
CREATE TABLE knowledge_gaps (
    gap_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Query context
    query TEXT NOT NULL,
    manufacturer VARCHAR(255),
    model VARCHAR(255),
    confidence_score FLOAT NOT NULL,  -- What confidence did we have?

    -- Gap tracking
    occurrence_count INTEGER DEFAULT 1,  -- How many times seen
    priority FLOAT NOT NULL,  -- Auto-calculated: count × confidence_gap × vendor_boost

    -- Research status
    research_status VARCHAR(50) DEFAULT 'pending',
    resolved_atom_id UUID REFERENCES knowledge_atoms(atom_id) ON DELETE SET NULL,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,

    CONSTRAINT check_research_status CHECK (
        research_status IN ('pending', 'in_progress', 'completed', 'failed')
    ),
    CONSTRAINT check_confidence_score CHECK (
        confidence_score >= 0.0 AND confidence_score <= 1.0
    )
);

-- Indexes for performance
CREATE INDEX idx_knowledge_atoms_type ON knowledge_atoms(type);
CREATE INDEX idx_knowledge_atoms_manufacturer ON knowledge_atoms(manufacturer);
CREATE INDEX idx_knowledge_atoms_model ON knowledge_atoms(model);
CREATE INDEX idx_knowledge_atoms_equipment_type ON knowledge_atoms(equipment_type);
CREATE INDEX idx_knowledge_atoms_confidence ON knowledge_atoms(confidence DESC);
CREATE INDEX idx_knowledge_atoms_verified ON knowledge_atoms(human_verified);
CREATE INDEX idx_knowledge_atoms_usage ON knowledge_atoms(usage_count DESC);

-- Vector similarity search index (IVFFlat for pgvector)
-- Note: Similar to manual_chunks, but separate index for curated knowledge
CREATE INDEX idx_knowledge_atoms_embedding ON knowledge_atoms
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX idx_knowledge_gaps_status ON knowledge_gaps(research_status);
CREATE INDEX idx_knowledge_gaps_priority ON knowledge_gaps(priority DESC);
CREATE INDEX idx_knowledge_gaps_manufacturer ON knowledge_gaps(manufacturer);
CREATE INDEX idx_knowledge_gaps_created ON knowledge_gaps(created_at);
CREATE INDEX idx_knowledge_gaps_unresolved ON knowledge_gaps(research_status, priority DESC)
    WHERE research_status IN ('pending', 'in_progress');

-- Unique constraint to prevent duplicate gaps
CREATE UNIQUE INDEX idx_knowledge_gaps_unique_pending ON knowledge_gaps(
    query,
    COALESCE(manufacturer, ''),
    COALESCE(model, '')
)
WHERE research_status = 'pending';

-- Auto-update last_verified timestamp for atoms
CREATE OR REPLACE FUNCTION update_atom_last_verified()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.human_verified = TRUE AND OLD.human_verified = FALSE THEN
        NEW.last_verified = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_atom_verified
    BEFORE UPDATE ON knowledge_atoms
    FOR EACH ROW
    EXECUTE FUNCTION update_atom_last_verified();

-- Function to calculate gap priority
-- priority = occurrence_count × (1 - confidence) × vendor_boost
-- vendor_boost = 1.5 for Siemens/Rockwell, 1.0 otherwise
CREATE OR REPLACE FUNCTION calculate_gap_priority(
    p_occurrence_count INTEGER,
    p_confidence_score FLOAT,
    p_manufacturer VARCHAR
)
RETURNS FLOAT AS $$
DECLARE
    vendor_boost FLOAT := 1.0;
    confidence_gap FLOAT;
BEGIN
    -- Boost priority for major vendors
    IF p_manufacturer IN ('Siemens', 'Rockwell', 'Rockwell Automation', 'Allen-Bradley') THEN
        vendor_boost := 1.5;
    END IF;

    -- Confidence gap: how much we don't know (inverted)
    confidence_gap := 1.0 - COALESCE(p_confidence_score, 0.0);

    -- Final priority calculation
    RETURN p_occurrence_count * confidence_gap * vendor_boost;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-calculate priority on insert/update
CREATE OR REPLACE FUNCTION update_gap_priority()
RETURNS TRIGGER AS $$
BEGIN
    NEW.priority := calculate_gap_priority(
        NEW.occurrence_count,
        NEW.confidence_score,
        NEW.manufacturer
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_calculate_gap_priority
    BEFORE INSERT OR UPDATE ON knowledge_gaps
    FOR EACH ROW
    EXECUTE FUNCTION update_gap_priority();

-- Comments
COMMENT ON TABLE knowledge_atoms IS 'Curated troubleshooting knowledge atoms for 4-route AI orchestrator';
COMMENT ON TABLE knowledge_gaps IS 'Self-healing KB: tracks low-confidence queries to trigger research';

COMMENT ON COLUMN knowledge_atoms.type IS 'fault=error codes, procedure=how-to, spec=technical specs, part=component info, tip=best practices, safety=warnings';
COMMENT ON COLUMN knowledge_atoms.confidence IS 'How verified is this knowledge? 0.0=unverified, 1.0=manufacturer-confirmed';
COMMENT ON COLUMN knowledge_atoms.usage_count IS 'How many times this atom was returned to users (popularity metric)';
COMMENT ON COLUMN knowledge_atoms.embedding IS 'Vector embedding for semantic search (1536 dimensions for OpenAI text-embedding-3-small)';

COMMENT ON COLUMN knowledge_gaps.priority IS 'Auto-calculated: occurrence_count × (1-confidence) × vendor_boost (higher = more urgent to research)';
COMMENT ON COLUMN knowledge_gaps.occurrence_count IS 'How many times this gap was encountered (increment on duplicate queries)';
COMMENT ON COLUMN knowledge_gaps.resolved_atom_id IS 'Links to the knowledge_atom created to fill this gap (when research completes)';

-- Sample seed data: Common Siemens fault codes
INSERT INTO knowledge_atoms (type, manufacturer, model, title, content, source_url, confidence, human_verified, embedding) VALUES
    (
        'fault',
        'Siemens',
        'G120C',
        'F0002 - Overvoltage Fault',
        'F0002 indicates DC bus overvoltage on Siemens G120C drive. Common causes: (1) Regen energy from decelerating motor not dissipated, (2) Input voltage spike, (3) Faulty braking resistor. Solutions: Check ramp-down time (p1121), verify braking resistor connection, check input voltage stability.',
        'https://support.industry.siemens.com/cs/document/67854244',
        0.95,
        TRUE,
        NULL  -- Will be populated by embedding service
    ),
    (
        'fault',
        'Siemens',
        'G120C',
        'F0001 - Overcurrent Fault',
        'F0001 indicates overcurrent detection. Causes: (1) Motor overload, (2) Short circuit in motor cable, (3) Incorrect motor parameters. Troubleshooting: Check motor load, inspect cables for damage, verify p0304 (rated motor voltage) and p0305 (rated motor current) match nameplate.',
        'https://support.industry.siemens.com/cs/document/67854244',
        0.95,
        TRUE,
        NULL
    ),
    (
        'procedure',
        'Siemens',
        'G120C',
        'Basic Parameter Setup for G120C',
        'Quick commissioning procedure: (1) Set p0010=1 (quick commissioning), (2) Enter motor nameplate: p0304 (voltage), p0305 (current), p0307 (power), p0308 (cos phi), p0309 (efficiency), p0310 (frequency), p0311 (speed). (3) Set p1080 (min frequency), p1082 (max frequency). (4) Run motor identification p1910=1 if required. (5) Set p0010=0 to lock parameters.',
        'https://support.industry.siemens.com/cs/document/109746530',
        0.90,
        TRUE,
        NULL
    );

-- Note: Embeddings will be generated by embedding_service.py and updated via UPDATE queries
