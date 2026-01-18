-- Shop Floor Expert Stories
-- Insert into ralph_stories table for Ralph autonomous development
-- Run: psql $DATABASE_URL -f scripts/ralph/insert_expert_stories.sql

-- Clear any existing EXPERT stories (idempotent)
DELETE FROM ralph_stories WHERE story_id LIKE 'EXPERT-%';

-- Insert new stories
INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, priority, status) VALUES
(1, 'EXPERT-001', 'Intent Fix: Symptom Questions',
 'Add symptom word override to quick classifier so questions like "what does a bad motor smell like?" route to TROUBLESHOOT',
 '["symptom + bad/failing → TROUBLESHOOT (0.85+)", "what does a failing bearing sound like → TROUBLESHOOT", "basic tests still 100%"]',
 1, 'todo'),

(1, 'EXPERT-002', 'Intent Fix: Logging Patterns',
 'Add logging patterns (log this, log it, document this, record this) to quick classifier for WORK_ORDER_CREATE',
 '["log this: X → WORK_ORDER_CREATE (0.90+)", "document this: X → WORK_ORDER_CREATE", "record this: X → WORK_ORDER_CREATE", "basic tests still 100%"]',
 2, 'todo'),

(1, 'EXPERT-003', 'Intent Fix: History Lookup',
 'Add history patterns (fault history, history on, records for) to quick classifier for EQUIPMENT_SEARCH',
 '["VFD fault history → EQUIPMENT_SEARCH (0.85+)", "history on motor 7 → EQUIPMENT_SEARCH", "fault records for compressor → EQUIPMENT_SEARCH", "basic tests still 100%"]',
 3, 'todo'),

(1, 'EXPERT-004', 'Streaming Responses',
 'Implement streaming responses so text appears word-by-word in Telegram instead of waiting for full response',
 '["first token <200ms", "progressive message updates every ~500ms", "graceful fallback if streaming fails", "works for TROUBLESHOOT, MANUAL_QUESTION, GENERAL_CHAT"]',
 4, 'todo'),

(1, 'EXPERT-005', 'Multi-Signal Router',
 'Replace single classifier with 3-signal voting: keyword (40%) + semantic (35%) + LLM fallback (25%)',
 '["keyword signal: 0ms, 85% accuracy", "semantic signal: 10ms, 88% accuracy", "LLM only when confidence <0.75", "expert tests ≥95%", "LLM called for <20% of queries"]',
 5, 'todo'),

(1, 'EXPERT-006', 'Context Retrieval',
 'Search equipment history before generating responses, inject relevant past cases into prompt',
 '["top 3 relevant cases injected into prompt", "responses reference history when applicable", "no awkward empty results messages", "works for TROUBLESHOOT and EQUIPMENT_SEARCH"]',
 6, 'todo'),

(1, 'EXPERT-007', 'Voice-First Optimization',
 'Clean up speech-to-text artifacts: filler words, abbreviation normalization, incomplete sentences',
 '["strip uh/um/like/you know", "vee eff dee → VFD", "ay ach you → AHU", "handle motor... pump 3... not working", "preserve megger/FLA/phase imbalance"]',
 7, 'todo'),

(1, 'EXPERT-008', 'Expert Response Templates',
 'Update system prompts to respect technician expertise - direct answers, no condescending explanations',
 '["troubleshoot: jump to diagnosis", "manual: specs directly no preamble", "detect technical terms → expert mode", "no As you may know or For safety phrases"]',
 8, 'todo');

-- Verify insertion
SELECT story_id, title, status FROM ralph_stories WHERE story_id LIKE 'EXPERT-%' ORDER BY priority;
