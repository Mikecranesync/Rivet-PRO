# RALPH Setup - Complete! ✅

## What Was Done

### ✅ 1. Deleted Old Workflow
- Removed old "Ralph - Main Loop" (ID: KdDrxp9tkCUvDUTmM8Jp1)
- Old workflow used Neon with connection issues

### ✅ 2. Created New Workflow
- **Workflow ID**: HIwpqfAegFSotLqs
- **Name**: Ralph - Main Loop
- **Nodes**: All 19 nodes created with proper connections
- **Loop**: Loop-back connection wired (Node 17 → Node 4)
- **Location**: https://mikecranesync.app.n8n.cloud/workflow/HIwpqfAegFSotLqs

### ✅ 3. Migration Ready
- Migration SQL file ready: `setup_ralph_supabase.sql`
- Includes 4 tables + 5 stories
- Run in Supabase SQL Editor: https://supabase.com/dashboard/project/mggqgrxwumnnujojndub

---

## 🔧 FINAL STEPS (Do This Now)

### STEP 1: Run Migration in Supabase

1. Go to https://supabase.com/dashboard/project/mggqgrxwumnnujojndub
2. Click **SQL Editor** (left sidebar)
3. Click **New Query**
4. Copy and paste this SQL:

```sql
-- RALPH Tables for Supabase
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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_stories_status ON ralph_stories(project_id, status);
CREATE INDEX IF NOT EXISTS idx_stories_priority ON ralph_stories(project_id, priority ASC) WHERE status = 'todo';
CREATE INDEX IF NOT EXISTS idx_iterations_story ON ralph_iterations(story_id);
CREATE INDEX IF NOT EXISTS idx_executions_project ON ralph_executions(project_id, created_at DESC);

INSERT INTO ralph_projects (id, project_name, max_iterations, token_budget, telegram_chat_id)
VALUES (1, 'RIVET Pro', 50, 500000, '8445149012')
ON CONFLICT (id) DO NOTHING;

INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, ai_model, priority) VALUES
(1, 'RIVET-001', 'Usage Tracking System', 'Track equipment lookups per user for freemium enforcement.', '["Track each photo upload as one lookup", "Store user_id and timestamp in Neon", "Create get_usage_count function", "Block at 10 free lookups with upgrade message"]'::jsonb, 'claude-sonnet-4-20250514', 1),
(1, 'RIVET-002', 'Stripe Payment Integration', 'Connect Stripe for Pro tier at $29/month.', '["Create Stripe product/price for Pro $29/mo", "Implement checkout session endpoint", "Handle payment success webhook", "Update user subscription status", "Send Telegram confirmation"]'::jsonb, 'claude-sonnet-4-20250514', 2),
(1, 'RIVET-003', 'Free Tier Limit Enforcement', 'Block lookups at 10 and show upgrade prompt.', '["Check usage before processing photo", "Return upgrade message with Stripe link if limit hit", "Allow Pro users unlimited"]'::jsonb, 'claude-sonnet-4-20250514', 3),
(1, 'RIVET-004', 'Shorten System Prompts', 'Cut all prompts by 50% for faster field responses.', '["Audit all RIVET prompts", "Reduce each by 50%", "Remove filler text", "Test quality maintained"]'::jsonb, 'claude-haiku-20250305', 4),
(1, 'RIVET-005', 'Remove n8n Footer', 'Remove n8n branding from Telegram messages.', '["Find where footer is added", "Remove or override it", "Test all message types"]'::jsonb, 'claude-haiku-20250305', 5)
ON CONFLICT (project_id, story_id) DO NOTHING;
```

5. Click **Run** (or press Ctrl+Enter)
6. Verify success with: `SELECT story_id, ai_model, status FROM ralph_stories ORDER BY priority;`

---

### STEP 2: Create Supabase Credential in n8n

1. Go to https://mikecranesync.app.n8n.cloud
2. Click **Settings** (left sidebar)
3. Click **Credentials**
4. Click **Add Credential**
5. Search for and select **"Postgres"**
6. Fill in these EXACT values:
   - **Name**: `Supabase - RALPH`
   - **Host**: `db.mggqgrxwumnnujojndub.supabase.co`
   - **Database**: `postgres`
   - **User**: `postgres.mggqgrxwumnnujojndub`
   - **Password**: `$!hLQDYB#uW23DJ`
   - **Port**: `5432`
   - **SSL Mode**: `require` (enable SSL)
7. Click **Test Connection** → must show SUCCESS ✅
8. Click **Save**

---

### STEP 3: Assign Credential to 7 Postgres Nodes

1. Go to the workflow: https://mikecranesync.app.n8n.cloud/workflow/HIwpqfAegFSotLqs
2. For EACH of these 7 nodes, click the node and assign the credential:

| Node Name | What to do |
|-----------|------------|
| **Create Execution** | Click node → Credential dropdown → Select "Supabase - RALPH" |
| **Get Next Story** | Click node → Credential dropdown → Select "Supabase - RALPH" |
| **Mark In Progress** | Click node → Credential dropdown → Select "Supabase - RALPH" |
| **Update Story** | Click node → Credential dropdown → Select "Supabase - RALPH" |
| **Update Execution** | Click node → Credential dropdown → Select "Supabase - RALPH" |
| **Check More Stories** | Click node → Credential dropdown → Select "Supabase - RALPH" |
| **Finalize Execution** | Click node → Credential dropdown → Select "Supabase - RALPH" |

**All 7 MUST use "Supabase - RALPH"!**

---

### STEP 4: Activate Workflow

1. In the workflow editor, toggle **Active** switch to ON (top-right)
2. Wait for confirmation message

---

### STEP 5: Test RALPH

**Trigger the workflow**:
```bash
curl "https://mikecranesync.app.n8n.cloud/webhook/ralph-main-loop"
```

**Expected Telegram messages** (to chat 8445149012):
1. 🚀 "RALPH STARTING"
2. 🟡 "STARTING: RIVET-001" (Model: Sonnet 4)
3. ✅ "DONE: RIVET-001" (commit hash + tokens)
4. Loop continues for RIVET-002, 003, 004, 005
5. 🏁 "RALPH COMPLETE"

---

## Verification Checklist

- [ ] Migration run in Supabase (5 stories visible)
- [ ] "Supabase - RALPH" credential created and tested
- [ ] All 7 Postgres nodes assigned the credential
- [ ] Workflow activated (toggle ON)
- [ ] Webhook triggered successfully
- [ ] Telegram messages received
- [ ] Stories processed (check Supabase:  `SELECT * FROM ralph_stories;`)

---

## Troubleshooting

**"No credential selected" error**:
- Make sure all 7 Postgres nodes have "Supabase - RALPH" assigned

**"relation ralph_executions does not exist"**:
- Run the migration SQL in Supabase first

**"Connection failed"**:
- Verify credential test succeeded
- Check SSL is enabled
- Verify host is `db.mggqgrxwumnnujojndub.supabase.co`

**"No stories found"**:
- Run in Supabase: `SELECT * FROM ralph_stories;`
- If empty, re-run the INSERT statements

---

## Quick Commands

**Reset stories to todo**:
```sql
UPDATE ralph_stories
SET status = 'todo', status_emoji = '⬜', retry_count = 0
WHERE project_id = 1;
```

**Check status**:
```sql
SELECT story_id, status, status_emoji, ai_model
FROM ralph_stories
ORDER BY priority;
```

**Trigger RALPH**:
```bash
curl "https://mikecranesync.app.n8n.cloud/webhook/ralph-main-loop"
```

---

## Files Created

| File | Purpose |
|------|---------|
| `setup_ralph_supabase.sql` | Migration SQL (complete) |
| `ralph_main_loop_supabase.json` | Workflow source (for reference) |
| `RALPH_REBUILD_GUIDE.md` | Manual build guide (if needed) |
| `RALPH_SETUP_COMPLETE.md` | This file - completion summary |

---

## Architecture Summary

**Worker Workflow** (already exists):
- ID: `ovTlTYSu97mWj-yc0J_yi`
- Name: "Ralph - Implement Single Story"
- Status: Active ✅

**Main Loop Workflow** (just created):
- ID: `HIwpqfAegFSotLqs`
- Name: "Ralph - Main Loop"
- Nodes: 19 (all configured)
- Loop: Wired (Node 17 → Node 4)
- Status: Inactive (waiting for credentials)

**Database**:
- Platform: Supabase PostgreSQL
- Host: `db.mggqgrxwumnnujojndub.supabase.co`
- Tables: 4 (projects, stories, iterations, executions)
- Stories: 5 (RIVET-001 through RIVET-005)

**Cost**: ~$0.28 per full run (33,500 tokens)

---

🎯 **Next Action**: Complete Steps 1-4 above, then trigger RALPH!
