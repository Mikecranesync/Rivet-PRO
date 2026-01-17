-- Ralph Stories: Photo Intelligence Pipeline (Groq -> DeepSeek -> Claude)
-- PRD: RIVET Pro Photo-to-Component Intelligence System
-- Run: psql $DATABASE_URL -f scripts/ralph/insert_photo_pipeline_stories.sql

-- Clear any existing photo pipeline stories (idempotent)
DELETE FROM ralph_stories WHERE story_id LIKE 'PHOTO-%';

-- Insert Photo Pipeline stories
INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, ai_model, priority, status, status_emoji) VALUES

-- Phase 1: Security & Infrastructure
(1, 'PHOTO-SEC-001', 'Secrets Rotation and Fly.io Migration',
'Rotate all exposed secrets from .env and migrate to Fly.io secrets management. Remove .env from git history.',
'["All API keys rotated (Anthropic, OpenAI, Groq, Google, DeepSeek)", "Database passwords changed (Neon, Supabase, CockroachDB)", "Telegram bot tokens rotated (6 tokens)", "GitHub token, Stripe keys, Slack webhook rotated", "Fly.io secrets set for all keys: fly secrets set KEY=value", ".env removed from git history using git filter-branch", "Secrets verification: fly secrets list shows all required keys"]'::jsonb,
'claude-sonnet-4-20250514', 1, 'todo', '⬜'),

(1, 'PHOTO-ORCH-001', 'Ralph Wiggum Orchestrator Base Class',
'Create rivet_pro/core/llm/ralph_orchestrator.py with base orchestration framework for multi-LLM photo pipeline.',
'["RalphOrchestrator class with __init__ accepting db pool and settings", "Abstract methods: screen_photo, extract_specs, analyze_with_kb", "Retry helper with exponential backoff (3 attempts, 100ms base)", "Cost tracking: total_cost_usd property aggregating all LLM calls", "Photo hash computation: SHA256 of image bytes for caching", "Logging with timing for each stage", "Error handling with graceful degradation", "Export from rivet_pro/core/llm/__init__.py"]'::jsonb,
'claude-sonnet-4-20250514', 2, 'todo', '⬜'),

(1, 'PHOTO-GROQ-001', 'Groq Vision Industrial Screening Service',
'Implement Groq-based first-pass screening to determine if photo is industrial equipment.',
'["async screen_industrial_photo(base64_image: str) -> ScreeningResult dataclass", "ScreeningResult: is_industrial bool, confidence float, category str, reason str", "Uses Groq llava-v1.5-7b-4096-preview model for vision", "Confidence threshold: >= 0.80 passes to next stage", "Category detection: plc, vfd, motor, pump, control_panel, sensor, other", "Response time target: < 2 seconds", "Cost tracking: ~$0.001 per image", "Reject non-industrial with helpful message suggesting what to photograph"]'::jsonb,
'claude-sonnet-4-20250514', 3, 'todo', '⬜'),

(1, 'PHOTO-DEEP-001', 'DeepSeek Component Specification Extraction',
'Implement DeepSeek-based second-pass extraction for model numbers, manufacturers, and specs.',
'["async extract_component_specs(base64_image: str, screening: ScreeningResult) -> ExtractionResult", "ExtractionResult: manufacturer, model_number, serial_number, specs dict, raw_text, confidence", "Only called if Groq confidence >= 0.80", "Uses DeepSeek-VL or deepseek-chat with vision", "Photo hash caching: skip extraction if same hash processed within 24h", "Cache storage in photo_analysis_cache table", "Response time target: < 3 seconds", "Cost tracking: ~$0.002 per image", "Handles blurry/partial text with confidence reduction"]'::jsonb,
'claude-sonnet-4-20250514', 4, 'todo', '⬜'),

(1, 'PHOTO-CACHE-001', 'Photo Analysis Cache Table Migration',
'Create database migration for caching photo analysis results by hash.',
'["Migration 028_photo_analysis_cache.sql", "Table: photo_analysis_cache with photo_hash, screening_result JSONB, extraction_result JSONB", "Columns: created_at, expires_at (24h default), access_count", "Index on photo_hash for fast lookup", "Index on expires_at for cleanup", "Function cleanup_expired_cache() for maintenance", "Upsert on duplicate hash"]'::jsonb,
'claude-haiku-20250305', 5, 'todo', '⬜'),

-- Phase 2: Core Pipeline
(1, 'PHOTO-TIMEOUT-001', 'Photo Handler 60-Second Timeout Protection',
'Add asyncio.timeout wrapper to _handle_photo in bot.py to prevent indefinite hangs.',
'["Import asyncio at top of bot.py", "Wrap _handle_photo body in async with asyncio.timeout(60)", "TimeoutError caught and logged with trace.add_step(timeout, error)", "User receives friendly message: Sorry processing took too long", "Alert sent to admin via alerting_service.alert_warning", "Trace saved in finally block regardless of outcome", "Extract main logic to _process_photo_internal helper"]'::jsonb,
'claude-sonnet-4-20250514', 6, 'todo', '⬜'),

(1, 'PHOTO-HIST-001', 'Equipment Maintenance History Retrieval',
'Add get_equipment_maintenance_history method to WorkOrderService for retrieving work order history.',
'["async get_equipment_maintenance_history(equipment_id: UUID, days: int = 90) -> List[Dict]", "Query work_orders WHERE equipment_id = $1 AND created_at >= NOW() - INTERVAL days", "Return: work_order_number, created_at, completed_at, status, title, fault_codes, priority", "Calculate resolution_time_hours from completed_at - created_at", "Handle empty results with empty list (no error)", "Order by created_at DESC", "Add to WorkOrderService class in work_order_service.py"]'::jsonb,
'claude-sonnet-4-20250514', 7, 'todo', '⬜'),

(1, 'PHOTO-HIST-002', 'Technician Work History Retrieval',
'Add get_technician_work_history method to WorkOrderService for technician performance tracking.',
'["async get_technician_work_history(user_id: str, days: int = 90, status_filter: str = None) -> List[Dict]", "Query work_orders with optional status filter", "Return: work_order_number, equipment_number, manufacturer, model_number, status, title, fault_codes", "Include resolution_time_hours calculation", "Handle status_filter as optional parameter", "Order by created_at DESC"]'::jsonb,
'claude-sonnet-4-20250514', 8, 'todo', '⬜'),

(1, 'PHOTO-CLAUDE-001', 'Claude AI Analysis and KB Synthesis',
'Implement Claude-based third-pass for troubleshooting synthesis with KB integration.',
'["async analyze_with_kb(equipment_id, specs, history, kb_context) -> AnalysisResult", "AnalysisResult: analysis str, solutions list, kb_citations list, recommendations list, confidence", "Only called on confirmed/tagged photos with equipment_id", "Uses Claude claude-sonnet-4-20250514 for synthesis", "Combines: component specs + maintenance history + KB atoms", "Formats citations with source URLs from KB atoms", "Includes safety warnings extracted from response", "Fallback: return specs + history without synthesis if Claude fails", "Cost tracking: ~$0.01 per analysis"]'::jsonb,
'claude-sonnet-4-20250514', 9, 'todo', '⬜'),

(1, 'PHOTO-RETRY-001', 'Database Retry Logic with Exponential Backoff',
'Add retry mechanism to Database class execute/fetch methods for transient connection errors.',
'["Add _execute_with_retry helper method to Database class", "Retry on: ConnectionDoesNotExistError, InterfaceError, TooManyConnectionsError, CannotConnectNowError, OSError", "Max 3 retries with exponential backoff: 100ms, 500ms, 500ms (capped)", "Log warning on retry, error after max retries", "Do NOT retry on query errors (PostgresSyntaxError, UniqueViolationError)", "Update execute(), fetch(), fetchrow(), fetchval() to use helper", "Add import asyncio at top"]'::jsonb,
'claude-sonnet-4-20250514', 10, 'todo', '⬜'),

-- Phase 3: Integration
(1, 'PHOTO-FLOW-001', 'Telegram Photo Upload Pipeline Integration',
'Wire Groq -> DeepSeek -> Claude pipeline into _handle_photo handler.',
'["Create PhotoPipelineService orchestrating all three stages", "Stage 1: Groq screening (always runs)", "Stage 2: DeepSeek extraction (if Groq >= 0.80)", "Stage 3: Claude analysis (if equipment matched and KB context found)", "Cache check before DeepSeek based on photo hash", "Track costs at each stage in trace metadata", "Format response with all relevant data", "Handle each stage failure independently"]'::jsonb,
'claude-sonnet-4-20250514', 11, 'todo', '⬜'),

(1, 'PHOTO-RESP-001', 'Photo Response Formatting for Telegram',
'Create format_photo_pipeline_response function for Telegram-optimized output.',
'["Format Groq screening result with confidence emoji", "Format DeepSeek extraction as equipment card", "Format Claude analysis with collapsible sections", "Include safety warnings prominently with warning emoji", "Include KB citations as numbered references", "Include maintenance history summary if exists", "Keep total message under 4096 chars (Telegram limit)", "Use markdown for formatting"]'::jsonb,
'claude-haiku-20250305', 12, 'todo', '⬜'),

-- Phase 4: Testing & Documentation
(1, 'PHOTO-TEST-001', 'Unit Tests for Photo Pipeline Services',
'Create comprehensive unit tests for Groq, DeepSeek, and Claude services.',
'["tests/unit/test_groq_screening.py with mocked Groq API", "tests/unit/test_deepseek_extraction.py with mocked DeepSeek API", "tests/unit/test_claude_analysis.py with mocked Claude API", "tests/unit/test_photo_cache.py for cache hit/miss scenarios", "Test retry logic with simulated transient failures", "Test confidence thresholds and routing logic", "All tests pass with pytest"]'::jsonb,
'claude-haiku-20250305', 13, 'todo', '⬜'),

(1, 'PHOTO-TEST-002', 'Integration Tests for Full Pipeline',
'Create integration tests exercising full photo pipeline end-to-end.',
'["tests/integration/test_photo_pipeline.py with real DB", "Test: industrial photo -> Groq screens -> DeepSeek extracts -> Claude analyzes", "Test: non-industrial photo rejected at Groq stage", "Test: blurry photo gets low confidence", "Test: cache hit skips DeepSeek on duplicate photo", "Test: each stage failure handled gracefully", "Can run with: uv run pytest tests/integration/test_photo_pipeline.py -v"]'::jsonb,
'claude-haiku-20250305', 14, 'todo', '⬜'),

(1, 'PHOTO-DOC-001', 'PRD Document Creation',
'Create docs/PRD_PHOTO_PIPELINE.md with complete product requirements.',
'["Vision statement: Technicians upload photos, get AI analysis", "Core features: 6 numbered items (ingestion through CMMS)", "Success metrics: latency < 5s, Groq accuracy > 95%, cost < $0.01", "Acceptance criteria: 10 functional, 5 performance, 3 reliability", "Out of scope: Google Photos import, predictive maintenance", "Architecture diagram in mermaid format", "Reviewed and approved by stakeholder"]'::jsonb,
'claude-haiku-20250305', 15, 'todo', '⬜'),

(1, 'PHOTO-DOC-002', 'Technical Manual Creation',
'Create docs/TECHNICAL_MANUAL.md for operators and developers.',
'["Architecture diagram: Groq -> DeepSeek -> Claude with Ralph orchestration", "Service layer API docs: inputs, outputs, error codes", "Database schema with indexes", "Deployment checklist: secrets, env vars, fly.io commands", "Troubleshooting guide: API timeouts, cache invalidation, cost spikes", "Local dev setup: run bot + pipeline in < 5 min", "Monitoring & alerting: what to watch, thresholds"]'::jsonb,
'claude-haiku-20250305', 16, 'todo', '⬜'),

(1, 'PHOTO-DOC-003', 'User Manual Creation',
'Create docs/USER_MANUAL.md for field technicians.',
'["Getting started: How to add RIVET to Telegram with screenshots", "Photo tips: What to photograph, angles, lighting", "Reading results: What each section means", "Tagging equipment: How to link photos to CMMS", "Viewing history: How to retrieve work orders", "FAQ: 5 common issues with solutions", "Support contact information"]'::jsonb,
'claude-haiku-20250305', 17, 'todo', '⬜');

-- Verify insertion
SELECT story_id, title, status, ai_model, priority FROM ralph_stories WHERE story_id LIKE 'PHOTO-%' ORDER BY priority;
