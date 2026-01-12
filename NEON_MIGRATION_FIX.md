# Neon Migration Fix - How to Run RALPH Migration

## Problem
Neon SQL Editor was adding `EXPLAIN` to the query, causing syntax errors with `CREATE TABLE`.

## ✅ Solution Applied
The migration file has been fixed with:
- ✅ `CREATE TABLE IF NOT EXISTS` (prevents re-run errors)
- ✅ `CREATE INDEX IF NOT EXISTS` (idempotent)
- ✅ `ON CONFLICT DO NOTHING` (handles duplicate inserts)

## 🚀 How to Run in Neon (3 Methods)

### Method 1: Run Entire File (Recommended)

1. Open Neon Console: https://console.neon.tech/
2. Select your database: `neondb`
3. Click **SQL Editor** in sidebar
4. **IMPORTANT**: Look for an "Explain" toggle/button - **DISABLE IT** if present
5. Copy the entire contents of `rivet_pro/migrations/010_ralph_system.sql`
6. Paste into SQL Editor
7. Click **Run** or press `Ctrl+Enter`

### Method 2: Run in Chunks (If Method 1 Fails)

If you still get errors, run these chunks separately:

**Chunk 1 - Create Tables:**
```sql
CREATE TABLE IF NOT EXISTS ralph_projects (
    id SERIAL PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    max_iterations INTEGER DEFAULT 50,
    token_budget INTEGER DEFAULT 500000,
    telegram_chat_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ralph_stories (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES ralph_projects(id),
    story_id VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    acceptance_criteria JSONB,
    ai_model VARCHAR(100) DEFAULT 'claude-sonnet-4-20250514',
    status VARCHAR(20) DEFAULT 'todo',
    status_emoji VARCHAR(10) DEFAULT '⬜',
    priority INTEGER DEFAULT 0,
    commit_hash VARCHAR(100),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, story_id),
    CONSTRAINT check_status CHECK (
        status IN ('todo', 'in_progress', 'done', 'failed')
    ),
    CONSTRAINT check_ai_model CHECK (
        ai_model IN ('claude-sonnet-4-20250514', 'claude-3-5-sonnet-20241022', 'claude-haiku-20250305')
    )
);

CREATE TABLE IF NOT EXISTS ralph_iterations (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES ralph_projects(id),
    story_id INTEGER REFERENCES ralph_stories(id),
    execution_id INTEGER,
    iteration_number INTEGER,
    status VARCHAR(20),
    commit_hash VARCHAR(100),
    tokens_used INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ralph_executions (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES ralph_projects(id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    total_iterations INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    stories_completed INTEGER DEFAULT 0,
    stories_failed INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'running',
    stop_reason VARCHAR(100),
    CONSTRAINT check_exec_status CHECK (
        status IN ('running', 'completed', 'failed')
    )
);
```

**Chunk 2 - Create Indexes:**
```sql
CREATE INDEX IF NOT EXISTS idx_stories_status ON ralph_stories(project_id, status);
CREATE INDEX IF NOT EXISTS idx_stories_priority ON ralph_stories(project_id, priority ASC) WHERE status = 'todo';
CREATE INDEX IF NOT EXISTS idx_iterations_story ON ralph_iterations(story_id);
CREATE INDEX IF NOT EXISTS idx_executions_project ON ralph_executions(project_id, created_at DESC);
```

**Chunk 3 - Insert Project:**
```sql
INSERT INTO ralph_projects (id, project_name, max_iterations, token_budget, telegram_chat_id)
VALUES (1, 'RIVET Pro', 50, 500000, '8445149012')
ON CONFLICT (id) DO NOTHING;
```

**Chunk 4 - Insert Stories:**
```sql
INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, ai_model, priority, status, status_emoji) VALUES
(1, 'RIVET-001', 'Usage Tracking System',
'Track equipment lookups per user for freemium enforcement.',
'["Track each photo upload as one lookup", "Store user_id and timestamp in Neon", "Create get_usage_count function", "Block at 10 free lookups with upgrade message"]'::jsonb,
'claude-sonnet-4-20250514', 1, 'todo', '⬜'),

(1, 'RIVET-002', 'Stripe Payment Integration',
'Connect Stripe for Pro tier at $29/month.',
'["Create Stripe product/price for Pro $29/mo", "Implement checkout session endpoint", "Handle payment success webhook", "Update user subscription status", "Send Telegram confirmation"]'::jsonb,
'claude-sonnet-4-20250514', 2, 'todo', '⬜'),

(1, 'RIVET-003', 'Free Tier Limit Enforcement',
'Block lookups at 10 and show upgrade prompt.',
'["Check usage before processing photo", "Return upgrade message with Stripe link if limit hit", "Allow Pro users unlimited"]'::jsonb,
'claude-sonnet-4-20250514', 3, 'todo', '⬜'),

(1, 'RIVET-004', 'Shorten System Prompts',
'Cut all prompts by 50% for faster field responses.',
'["Audit all RIVET prompts", "Reduce each by 50%", "Remove filler text", "Test quality maintained"]'::jsonb,
'claude-haiku-20250305', 4, 'todo', '⬜'),

(1, 'RIVET-005', 'Remove n8n Footer',
'Remove n8n branding from Telegram messages.',
'["Find where footer is added", "Remove or override it", "Test all message types"]'::jsonb,
'claude-haiku-20250305', 5, 'todo', '⬜')
ON CONFLICT (project_id, story_id) DO NOTHING;
```

### Method 3: Use psql Command Line

If you have `psql` installed:

```bash
# Set connection string
$env:DATABASE_URL="postgresql://neondb_owner:npg_c3UNa4KOlCeL@ep-purple-hall-ahimeyn0-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

# Run migration
psql $env:DATABASE_URL -f rivet_pro/migrations/010_ralph_system.sql
```

## ✅ Verification

After running, verify success:

```sql
-- Check tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_name LIKE 'ralph_%'
ORDER BY table_name;
```

**Expected Output:**
```
ralph_executions
ralph_iterations
ralph_projects
ralph_stories
```

```sql
-- Check stories were inserted
SELECT story_id, ai_model, status, priority
FROM ralph_stories
ORDER BY priority;
```

**Expected Output:**
```
RIVET-001 | claude-sonnet-4-20250514 | todo | 1
RIVET-002 | claude-sonnet-4-20250514 | todo | 2
RIVET-003 | claude-sonnet-4-20250514 | todo | 3
RIVET-004 | claude-haiku-20250305    | todo | 4
RIVET-005 | claude-haiku-20250305    | todo | 5
```

## 🎯 Next Steps

Once verified, continue with RALPH deployment:
1. ✅ Database migration complete
2. ⏳ Configure n8n credentials (see RALPH_DEPLOYMENT_GUIDE.md Step 2)
3. ⏳ Import workflows
4. ⏳ Test RALPH

---

**Migration file location:** `rivet_pro/migrations/010_ralph_system.sql`
**Full guide:** `RALPH_DEPLOYMENT_GUIDE.md`
