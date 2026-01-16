-- Phase 4: SME Chat with LLM Interaction Stories
-- Run: psql $DATABASE_URL -f scripts/ralph/insert_sme_chat_stories.sql

-- Clear any existing SME Chat stories (idempotent)
DELETE FROM ralph_stories WHERE story_id LIKE 'SME-CHAT-%';

-- Insert SME Chat stories (uses Sonnet 4 for complex architectural work)
INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, ai_model, priority, status, status_emoji) VALUES

(1, 'SME-CHAT-001', 'Database Migration for Chat Sessions',
'Create migration 026_sme_chat_sessions.sql with tables for sme_chat_sessions and sme_chat_messages. Include auto-update triggers and session timeout functions.',
'["sme_chat_sessions table with telegram_chat_id, sme_vendor, status, equipment_context JSONB", "sme_chat_messages table with session_id FK, role, content, confidence, rag_atoms_used UUID array", "Auto-update last_message_at trigger on message insert", "close_inactive_sessions() function for 30-min timeout", "Indexes on telegram_chat_id, session status, and message timestamps"]'::jsonb,
'claude-sonnet-4-20250514', 1, 'todo', '⬜'),

(1, 'SME-CHAT-002', 'Pydantic Models for SME Chat',
'Create rivet/models/sme_chat.py with Pydantic models for chat sessions, messages, and responses.',
'["SMEChatSession model with session_id, telegram_chat_id, sme_vendor, status, equipment_context", "SMEChatMessage model with message_id, session_id, role, content, confidence, rag_atoms_used", "SMEChatResponse model with response, confidence, sources list, safety_warnings list, cost_usd", "All models have proper type hints and validation", "Export from rivet/models/__init__.py"]'::jsonb,
'claude-sonnet-4-20250514', 2, 'todo', '⬜'),

(1, 'SME-CHAT-003', 'SME Personalities Configuration',
'Create rivet/prompts/sme/personalities.py with distinct voice/personality for 6 vendor SMEs plus generic.',
'["SME_PERSONALITIES dict with siemens, rockwell, abb, schneider, mitsubishi, fanuc, generic keys", "Each personality has name, tagline, voice dict (style, greeting, thinking_phrases, closing_phrases)", "Each personality has expertise_areas list and response_format preferences", "Each personality has system_prompt_additions for LLM prompt injection", "Siemens=Hans German precision, Rockwell=Mike American practical, ABB=Erik safety-focused, etc."]'::jsonb,
'claude-sonnet-4-20250514', 3, 'todo', '⬜'),

(1, 'SME-CHAT-004', 'RAG Service for SME Context',
'Create rivet/services/sme_rag_service.py that retrieves relevant knowledge atoms filtered by manufacturer.',
'["SMERagService class with get_relevant_context async method", "Accepts query, manufacturer, conversation_history, equipment_context, limit params", "Builds enhanced query from conversation context for better embedding", "Uses existing EmbeddingService for query embedding generation", "Uses existing KnowledgeService.vector_search with manufacturer filter", "Returns tuple of (atoms_list, formatted_context_string)", "Formats atoms as structured context for LLM prompt"]'::jsonb,
'claude-sonnet-4-20250514', 4, 'todo', '⬜'),

(1, 'SME-CHAT-005', 'SME Chat Service Core',
'Create rivet/services/sme_chat_service.py that orchestrates chat sessions with personality, RAG, and LLM.',
'["SMEChatService class with start_session, chat, close_session methods", "start_session creates DB session, adds system message with personality", "chat method: load session, get history, RAG context, build prompt, generate LLM response", "Prompt combines personality voice + RAG context + conversation history + equipment context", "Extract safety warnings from response text", "Calculate confidence based on RAG hit quality", "Store assistant message with rag_atoms_used metadata", "Uses existing LLMRouter.generate with ModelCapability.MODERATE"]'::jsonb,
'claude-sonnet-4-20250514', 5, 'todo', '⬜'),

(1, 'SME-CHAT-006', 'Telegram /chat Command Handler',
'Add /chat and /endchat command handlers to rivet/integrations/telegram.py for starting SME chat sessions.',
'["/chat [vendor] command starts SME session - vendor optional, auto-detects from recent equipment", "/endchat command closes active session and clears user_data", "Show vendor picker if no vendor specified and no recent equipment", "Store sme_session_id and sme_chat_active in context.user_data", "Send SME greeting with personality name and tagline", "Register both commands in setup_bot() with CommandHandler"]'::jsonb,
'claude-sonnet-4-20250514', 6, 'todo', '⬜'),

(1, 'SME-CHAT-007', 'Telegram Message Routing for Chat Mode',
'Update message_handler in telegram.py to route messages to SME chat when session is active.',
'["Check context.user_data.get(sme_chat_active) at start of message_handler", "If active, call handle_sme_chat_message instead of troubleshoot workflow", "handle_sme_chat_message loads session, calls SMEChatService.chat, formats response", "Response includes SME name badge, answer, safety warnings, sources, confidence indicator", "Typing indicator shown while processing", "Error handling with suggestion to /endchat if persistent failures"]'::jsonb,
'claude-sonnet-4-20250514', 7, 'todo', '⬜'),

(1, 'SME-CHAT-008', 'Confidence-Based Routing in Orchestrator',
'Implement confidence-based routing: high (>0.85) direct KB, medium (0.7-0.85) SME synthesis, low (<0.7) clarifying questions.',
'["route_chat_query function calculates RAG confidence from top result similarity", "High confidence (>=0.85): format_direct_kb_answer with SME voice styling", "Medium confidence (0.70-0.85): generate_sme_synthesis from RAG context", "Low confidence (<0.70): generate_clarifying_questions to ask user for more info", "Confidence calculation: (top_similarity * 0.6) + (avg_top3_similarity * 0.4)", "Integrate with SMEChatService.chat flow"]'::jsonb,
'claude-sonnet-4-20250514', 8, 'todo', '⬜'),

(1, 'SME-CHAT-009', 'Unit Tests for SME Chat',
'Create comprehensive unit tests for SME chat service and personalities.',
'["tests/unit/test_sme_chat_service.py with mocked DB and LLM", "Test start_session creates session and adds system message", "Test chat returns properly formatted response with all fields", "Test close_session updates status", "tests/unit/test_sme_personalities.py verifies all 7 personalities load", "Test personality prompt generation includes voice elements", "All tests pass with pytest"]'::jsonb,
'claude-haiku-20250305', 9, 'todo', '⬜'),

(1, 'SME-CHAT-010', 'Integration Test for Full Chat Flow',
'Create integration test that exercises the full SME chat flow from Telegram to response.',
'["tests/integration/test_sme_chat_flow.py with real DB connection", "Test: /chat siemens -> ask question -> verify Hans personality in response", "Test: multi-turn conversation preserves context", "Test: RAG atoms are retrieved and formatted in context", "Test: safety warnings extracted correctly", "Test: session closes on /endchat", "Can run with: uv run pytest tests/integration/test_sme_chat_flow.py -v"]'::jsonb,
'claude-haiku-20250305', 10, 'todo', '⬜');

-- Verify insertion
SELECT story_id, title, status, ai_model FROM ralph_stories WHERE story_id LIKE 'SME-CHAT-%' ORDER BY priority;
