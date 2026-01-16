-- Ralph Stories: Phase 5 Analytics Dashboard
-- Run: psql $DATABASE_URL -f scripts/ralph/insert_analytics_stories.sql

-- Clear any existing analytics stories (idempotent)
DELETE FROM ralph_stories WHERE story_id LIKE 'ANALYTICS-%';

-- Insert Phase 5 Analytics stories
INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, priority, status) VALUES

(1, 'ANALYTICS-001', 'Daily Usage Statistics Aggregation',
 'Create a background job that aggregates daily usage stats from rivet_usage_log into daily_stats table. Track: total queries, unique users, queries by category (equipment/troubleshooting/manual/sme_chat), average response time.',
 '["Function aggregate_daily_stats() created in rivet_pro/core/services/analytics_service.py", "Queries rivet_usage_log for previous day data", "Inserts aggregated row into daily_stats table", "Handles duplicate runs gracefully (upsert)", "Can be triggered manually or via scheduler"]'::jsonb,
 1, 'todo'),

(1, 'ANALYTICS-002', 'Knowledge Base Health Metrics',
 'Track KB health: total atoms, atoms by manufacturer, coverage gaps (queries with no KB matches), stale atoms (not accessed in 30+ days).',
 '["Function get_kb_health() returns structured health metrics", "Counts atoms by manufacturer from knowledge_atoms table", "Identifies coverage gaps from low-confidence responses", "Tracks atom freshness (last_accessed timestamp)", "Returns actionable insights"]'::jsonb,
 2, 'todo'),

(1, 'ANALYTICS-003', 'SME Chat Analytics',
 'Track SME chat usage: sessions by vendor, average turns per session, confidence distribution, safety warnings triggered.',
 '["Function get_sme_chat_analytics() returns chat metrics", "Queries sme_chat_sessions and sme_chat_messages tables", "Groups by vendor (Siemens, Rockwell, ABB, etc.)", "Calculates avg messages per session", "Tracks confidence level distribution (HIGH/MEDIUM/LOW)"]'::jsonb,
 3, 'todo'),

(1, 'ANALYTICS-004', 'Admin /stats Command',
 'Create /stats command for admin users showing quick stats: today queries, active users, top equipment lookups, KB health summary.',
 '["/stats command added to bot.py", "Only accessible to admin users (telegram_id in admin list)", "Shows: queries today, unique users today, top 5 equipment", "Shows: KB atom count, SME sessions today", "Fast response (<2s) using pre-aggregated data"]'::jsonb,
 4, 'todo'),

(1, 'ANALYTICS-005', 'Weekly Report Generation',
 'Generate weekly report summarizing: usage trends, top queries, knowledge gaps, SME chat patterns. Send to admin via Telegram.',
 '["Function generate_weekly_report() creates formatted report", "Compares this week vs last week (trend arrows)", "Lists top 10 unanswered queries (knowledge gaps)", "Shows SME vendor popularity ranking", "Can be triggered via /report command or scheduler"]'::jsonb,
 5, 'todo'),

(1, 'ANALYTICS-006', 'Response Time Tracking',
 'Add response time tracking to all bot interactions. Store in rivet_usage_log with millisecond precision.',
 '["response_time_ms column added to rivet_usage_log (if not exists)", "All message handlers track start/end time", "Response time logged with each interaction", "Average response time visible in /stats", "Slow queries (>5s) flagged for review"]'::jsonb,
 6, 'todo');

-- Verify insertion
SELECT story_id, title, status FROM ralph_stories WHERE story_id LIKE 'ANALYTICS-%' ORDER BY priority;
