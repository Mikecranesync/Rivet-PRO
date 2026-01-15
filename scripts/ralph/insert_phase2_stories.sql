-- Phase 2: Troubleshooting Core (task-9) Stories
-- Run: psql $DATABASE_URL -f scripts/ralph/insert_phase2_stories.sql

-- Clear any existing Phase 2 stories (idempotent)
DELETE FROM ralph_stories WHERE story_id LIKE 'TASK-9.%';

-- Insert Phase 2 stories
INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, priority, status) VALUES

(1, 'TASK-9.1', 'Mermaid Diagram Parser',
'Create a parser that converts Mermaid flowchart syntax into a navigable tree structure of nodes and edges. The parser should handle flowchart TD/LR syntax with decision nodes (diamonds), action nodes (rectangles), and connections with labels.',
'["Mermaid flowchart syntax parses to Python dict with nodes and edges", "Supports TD and LR orientations", "Handles decision nodes (rhombus) and action nodes (rectangle)", "Edge labels preserved for button text", "Unit tests cover basic flowchart, branching, and edge cases"]'::jsonb,
1, 'todo'),

(1, 'TASK-9.2', 'Telegram Inline Keyboard Builder',
'Build a keyboard builder that creates Telegram InlineKeyboardMarkup from parsed tree nodes. Must respect Telegram limits: max 8 buttons per row, max 100 buttons total.',
'["Creates InlineKeyboardMarkup from tree node children", "Max 8 buttons per row enforced", "Buttons arranged logically (2-4 per row typical)", "Empty state handled gracefully", "Integration with python-telegram-bot library"]'::jsonb,
2, 'todo'),

(1, 'TASK-9.3', 'Callback Data Compression',
'Implement callback_data encoding that fits within Telegram 64-byte limit. Use short codes or hashing for node references.',
'["callback_data always under 64 bytes", "Node IDs encoded/decoded reliably", "Supports tree depth up to 10 levels", "Collision-free encoding scheme", "Fast encode/decode (< 1ms)"]'::jsonb,
3, 'todo'),

(1, 'TASK-9.4', 'In-Place Message Editing',
'Implement message editing so navigation updates the same message instead of sending new ones. Handle edit failures gracefully.',
'["Navigation edits message in-place via edit_message_text", "No new messages sent during tree traversal", "Edit failures fall back to new message with old message deletion", "Message history stays clean", "Works with both text and media messages"]'::jsonb,
4, 'todo'),

(1, 'TASK-9.5', 'Media Display with Captions',
'Support displaying images and media at tree nodes with captions. Handle cases where media is optional.',
'["Images display with node text as caption", "Supports JPEG and PNG formats", "Media URL or file_id reference supported", "Graceful fallback if media unavailable", "Caption respects Telegram 1024 char limit"]'::jsonb,
5, 'todo'),

(1, 'TASK-9.6', 'Safety Warning Formatting',
'Format safety warnings using Telegram blockquote style. Safety nodes should be visually distinct.',
'["Safety warnings use blockquote format (> prefix)", "Warning emoji prefix for visibility", "Supports multi-line warnings", "Works in both text and caption contexts", "HTML parse mode compatible"]'::jsonb,
6, 'todo'),

(1, 'TASK-9.7', 'Back Navigation',
'Implement back button that returns to previous step in the troubleshooting tree. Maintain navigation stack.',
'["Back button appears on all non-root nodes", "Returns to exact previous state", "Navigation stack persists per user session", "Stack clears on new tree start", "Works correctly with branching paths"]'::jsonb,
7, 'todo'),

(1, 'TASK-9.8', 'Claude Fallback for Unknown Equipment',
'When equipment has no troubleshooting tree, fall back to Claude API for dynamic guidance generation.',
'["Detects missing tree for equipment type", "Calls Claude API with equipment context", "Generates step-by-step troubleshooting", "Response formatted for Telegram display", "Offers to save generated guide as tree draft"]'::jsonb,
8, 'todo'),

(1, 'TASK-9.9', 'Save Guide as Tree Draft',
'Allow users to save Claude-generated guides as draft troubleshooting trees for admin review.',
'["Save this guide button on Claude responses", "Creates draft tree in database", "Stores original query context", "Admin can review and approve drafts", "Approved drafts become permanent trees"]'::jsonb,
9, 'todo');

-- Verify insertion
SELECT story_id, title, status FROM ralph_stories WHERE story_id LIKE 'TASK-9.%' ORDER BY priority;
