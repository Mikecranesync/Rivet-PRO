-- Migration 015: Knowledge Base Integration
-- Links interactions with knowledge atoms for autonomous learning
-- Part of KB Self-Learning System (KB-001)

BEGIN;

-- Link interactions to knowledge atoms
ALTER TABLE interactions
ADD COLUMN IF NOT EXISTS atom_id TEXT REFERENCES knowledge_atoms(atom_id);

ALTER TABLE interactions
ADD COLUMN IF NOT EXISTS atom_created BOOLEAN DEFAULT FALSE;

-- Track which atoms came from which interactions
ALTER TABLE knowledge_atoms
ADD COLUMN IF NOT EXISTS source_interaction_id UUID REFERENCES interactions(id);

ALTER TABLE knowledge_atoms
ADD COLUMN IF NOT EXISTS created_by VARCHAR(20) DEFAULT 'system';

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_interactions_atom
ON interactions(atom_id) WHERE atom_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_knowledge_atoms_source
ON knowledge_atoms(source_interaction_id) WHERE source_interaction_id IS NOT NULL;

-- Add comments
COMMENT ON COLUMN interactions.atom_id IS 'Knowledge atom created from this interaction';
COMMENT ON COLUMN interactions.atom_created IS 'Whether an atom was successfully created';
COMMENT ON COLUMN knowledge_atoms.source_interaction_id IS 'Interaction that generated this atom';
COMMENT ON COLUMN knowledge_atoms.created_by IS 'Source: system, feedback, or research';

COMMIT;

-- Verify schema changes
SELECT
    'interactions' as table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'interactions'
AND column_name IN ('atom_id', 'atom_created')
UNION ALL
SELECT
    'knowledge_atoms' as table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'knowledge_atoms'
AND column_name IN ('source_interaction_id', 'created_by');
