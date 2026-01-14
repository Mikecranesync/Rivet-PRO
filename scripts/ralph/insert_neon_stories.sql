-- Ralph Stories: Neon MCP Integration & DevOps Automation
-- Run this after database is available

-- Clear any existing stories from this batch (idempotent)
DELETE FROM ralph_stories WHERE story_id LIKE 'NEON-%' OR story_id LIKE 'N8N-NEON-%' OR story_id LIKE 'GITHUB-NEON-%';

-- Insert new stories
INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, priority, status) VALUES

(1, 'NEON-MCP-001', 'Setup Neon MCP Server in Claude Code',
'Add Neon MCP server to Claude Code for natural language database management. This enables using Claude to run SQL, manage branches, and perform migrations via natural language.',
'["Run: claude mcp add --transport http neon https://mcp.neon.tech/mcp", "Verify with /mcp in Claude Code shows Neon tools", "Test: List my Neon projects returns project list", "Test: Get tables in neondb returns table list", "Document Neon project ID in CLAUDE.md"]'::jsonb,
1, 'completed'),

(1, 'NEON-MCP-002', 'Add Neon API Key to Environment',
'Get Neon API key for programmatic access and backup auth method. Required for GitHub Actions workflows.',
'["Go to https://console.neon.tech/app/settings/api-keys", "Create new API key named rivet-pro-mcp", "Add to .env: NEON_API_KEY=neon_...", "Add NEON_API_KEY and NEON_PROJECT_ID to GitHub secrets", "Test with curl to Neon API"]'::jsonb,
2, 'todo'),

(1, 'NEON-BRANCH-001', 'GitHub PR Auto-Branching with Neon',
'Automatically create Neon database branches for each PR for isolated testing. Uses neondatabase/create-branch-action.',
'["Create .github/workflows/neon-branch.yml", "Workflow triggers on PR open/reopen/sync", "Creates branch named pr-{number}", "Comments PR with branch info", "Tests run against isolated branch"]'::jsonb,
3, 'completed'),

(1, 'NEON-BRANCH-002', 'PR Branch Cleanup Workflow',
'Auto-delete Neon branches when PRs are merged/closed to prevent orphan branches.',
'["Create .github/workflows/neon-cleanup.yml", "Workflow triggers on PR close", "Deletes branch pr-{number}", "Comments PR confirming cleanup"]'::jsonb,
4, 'completed'),

(1, 'N8N-NEON-001', 'n8n Workflow for Database Monitoring',
'Create n8n workflow to monitor Neon database health and alert on issues via Telegram.',
'["Create n8n workflow with schedule trigger (every 5 min)", "Test Neon connection with SELECT 1", "Send Telegram alert on failure", "Track compute auto-suspend warnings"]'::jsonb,
5, 'todo'),

(1, 'N8N-NEON-002', 'Auto-Wake Neon on Bot Start',
'n8n workflow to wake Neon compute before bot starts, eliminating cold-start connection errors.',
'["Create n8n webhook endpoint", "Bot startup calls webhook before DB connect", "Workflow runs SELECT 1 to wake compute", "Returns 200 when DB ready", "Update run_bot.py to call webhook"]'::jsonb,
6, 'todo'),

(1, 'GITHUB-NEON-001', 'Schema Migration PR Workflow',
'Auto-create Neon preview branch when migrations/*.sql files change for safe migration testing.',
'["Create .github/workflows/neon-migration-preview.yml", "Trigger on changes to rivet_pro/migrations/*.sql", "Create preview branch migration-preview-{number}", "Apply migrations to preview branch", "Comment PR with migration status"]'::jsonb,
7, 'completed'),

(1, 'CODERABBIT-001', 'Enable CodeRabbit for PR Reviews',
'Configure CodeRabbit AI code review on every PR using existing API key.',
'["Create .coderabbit.yaml config file", "Enable auto_review for PRs", "Configure path filters (exclude .md, .json)", "Add path-specific instructions for Python files", "Verify reviews appear on test PR"]'::jsonb,
8, 'completed'),

(1, 'LANGFUSE-NEON-001', 'Track LLM Costs with Langfuse',
'Connect Langfuse to track AI costs per user/query for all LLM calls.',
'["Add Langfuse tracing to OCR service (Gemini calls)", "Add tracing to SME routing (LLM calls)", "Add tracing to manual search (Tavily + LLM)", "Cost per query visible in Langfuse", "User attribution for billing"]'::jsonb,
9, 'todo'),

(1, 'RAILWAY-BACKUP-001', 'Railway as Neon Failover',
'Configure Railway Postgres as automatic failover when Neon is unavailable.',
'["Update rivet_pro/infra/database.py with failover logic", "Try Neon first, then Railway, then Supabase", "Log which provider connected", "Send alert to Telegram on failover", "Test by temporarily blocking Neon"]'::jsonb,
10, 'todo');

-- Verify insertion
SELECT story_id, title, status, priority FROM ralph_stories WHERE story_id LIKE 'NEON-%' OR story_id LIKE 'N8N-%' OR story_id LIKE 'GITHUB-%' OR story_id LIKE 'CODERABBIT-%' OR story_id LIKE 'LANGFUSE-%' OR story_id LIKE 'RAILWAY-%' ORDER BY priority;
