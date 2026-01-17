# RALPH Deployment Guide
## Autonomous Story Implementation System - Quick Start

🎯 **Goal**: Deploy RALPH in under 1 hour to automatically implement 5 RIVET stories.

📋 **Status**: Migration file created ✅ | Workflow JSONs created ✅ | Deployment steps below ⏳

---

## ✅ COMPLETED

1. **Migration File Created**: `rivet_pro/migrations/010_ralph_system.sql`
2. **Worker Workflow JSON**: `rivet-n8n-workflow/ralph_worker_workflow.json`
3. **Main Loop Workflow JSON**: `rivet-n8n-workflow/ralph_main_loop_workflow.json`

---

## 🚀 DEPLOYMENT STEPS

### STEP 1: Apply Database Migration (5 minutes)

#### 1.1 Open Neon Console
1. Go to https://console.neon.tech/
2. Login with your account
3. Select project: `ep-purple-hall-ahimeyn0-pooler`
4. Select database: `neondb`

#### 1.2 Run Migration
1. Click "SQL Editor" in left sidebar
2. Open file: `rivet_pro/migrations/010_ralph_system.sql`
3. Copy entire contents
4. Paste into SQL Editor
5. Click "Run" button

#### 1.3 Verify Tables Created
Run this query:
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_name LIKE 'ralph_%';
```

**Expected Output**: 4 tables
- `ralph_projects`
- `ralph_stories`
- `ralph_executions`
- `ralph_iterations`

#### 1.4 Verify Stories Seeded
```sql
SELECT story_id, ai_model, status, priority
FROM ralph_stories
ORDER BY priority;
```

**Expected Output**: 5 stories
| story_id | ai_model | status | priority |
|----------|----------|--------|----------|
| RIVET-001 | claude-sonnet-4-20250514 | todo | 1 |
| RIVET-002 | claude-sonnet-4-20250514 | todo | 2 |
| RIVET-003 | claude-sonnet-4-20250514 | todo | 3 |
| RIVET-004 | claude-haiku-20250305 | todo | 4 |
| RIVET-005 | claude-haiku-20250305 | todo | 5 |

---

### STEP 2: Configure n8n Credentials (5 minutes)

#### 2.1 Open n8n Cloud
1. Go to https://mikecranesync.app.n8n.cloud
2. Login with your account

#### 2.2 Configure Anthropic API Credential
1. Click Settings (gear icon) → Credentials
2. Click "+ Add Credential"
3. Search for "Anthropic"
4. Fill in:
   - **Credential Name**: `Anthropic - RALPH`
   - **API Key**: `sk-ant-api03-lTwIq3...` (from your `.env` file)
5. Click "Save"

#### 2.3 Configure Postgres Credential
1. Click "+ Add Credential" again
2. Search for "Postgres"
3. Fill in:
   - **Credential Name**: `Neon - RALPH`
   - **Host**: `ep-purple-hall-ahimeyn0-pooler.us-east-1.aws.neon.tech`
   - **Database**: `neondb`
   - **User**: `neondb_owner`
   - **Password**: `npg_c3UNa4KOlCeL` (from your connection string)
   - **Port**: `5432`
   - **SSL**: Enable (check the box)
4. Click "Test Connection" (should succeed)
5. Click "Save"

#### 2.4 Configure Telegram Credential
1. Click "+ Add Credential" again
2. Search for "Telegram"
3. Fill in:
   - **Credential Name**: `Telegram - RALPH`
   - **Access Token**: `8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE`
4. Click "Save"

---

### STEP 3: Import Worker Workflow (10 minutes)

#### 3.1 Import Workflow
1. In n8n, click "Workflows" in sidebar
2. Click "+ Add Workflow" → "Import from File"
3. Select file: `rivet-n8n-workflow/ralph_worker_workflow.json`
4. Click "Import"

#### 3.2 Configure Credentials in Workflow
1. Open the imported workflow "Ralph - Implement Single Story"
2. Click on node "Call Claude" (HTTP Request node)
3. Under "Authentication", select credential: `Anthropic - RALPH`
4. Click "Save" (top-right corner)

#### 3.3 Activate Workflow
1. Toggle switch in top-right to "Active"
2. Status should show green "Active"

---

### STEP 4: Import Main Loop Workflow (15 minutes)

#### 4.1 Import Workflow
1. Click "+ Add Workflow" → "Import from File"
2. Select file: `rivet-n8n-workflow/ralph_main_loop_workflow.json`
3. Click "Import"

#### 4.2 Configure Credentials in Nodes
Open the imported workflow "Ralph - Main Loop" and configure:

**PostgreSQL Nodes** (7 nodes total):
- `Create Execution`
- `Get Next Story`
- `Mark In Progress`
- `Update Story`
- `Update Execution`
- `Check More Stories`
- `Finalize Execution`

For each:
1. Click the node
2. Under "Credential to connect with", select: `Neon - RALPH`

**Telegram Nodes** (4 nodes total):
- `Send Start`
- `Story Start`
- `Send Result`
- `Send Summary`

For each:
1. Click the node
2. Under "Credential to connect with", select: `Telegram - RALPH`

**Execute Workflow Node**:
1. Click node "Call Worker"
2. Under "Workflow", select: `Ralph - Implement Single Story`
3. Ensure "Wait for completion" is checked

#### 4.3 Verify Loop-Back Connection (CRITICAL!)
1. Look at node "Loop Back?" (IF node)
2. Follow the TRUE branch (left/top output)
3. It should connect to node "Get Next Story"
4. This creates the loop that processes all stories

**If connection is missing**:
1. Click the TRUE output dot on "Loop Back?" node
2. Drag to "Get Next Story" node
3. Drop to create connection

#### 4.4 Save and Activate
1. Click "Save" (top-right)
2. Toggle to "Active"

---

### STEP 5: Test RALPH (5 minutes)

#### 5.1 Manual Test via n8n UI
1. Open workflow "Ralph - Main Loop"
2. Click "Test Workflow" button (top-right)
3. Watch execution in real-time
4. Check Telegram for messages (chat ID 8445149012)

**Expected Telegram Flow**:
```
🚀 RALPH STARTING
Project: RIVET Pro
Time: 2026-01-10 12:00:00

🟡 STARTING: RIVET-001
Usage Tracking System
Model: 🧠 Sonnet 4

[... Claude implements the story ...]

✅ DONE: RIVET-001
Commit: abc123de
Tokens: 12500

🟡 STARTING: RIVET-002
[... continues for all 5 stories ...]

🏁 RALPH COMPLETE
```

#### 5.2 Test via Webhook (Programmatic Trigger)
```bash
curl -X POST "https://mikecranesync.app.n8n.cloud/webhook/ralph-main-loop" \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1}'
```

**OR** using PowerShell:
```powershell
Invoke-WebRequest -Uri "https://mikecranesync.app.n8n.cloud/webhook/ralph-main-loop" `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"project_id": 1}'
```

#### 5.3 Verify Database Results
After completion, check:
```sql
-- Story status
SELECT story_id, status_emoji, status, commit_hash, tokens_used
FROM ralph_stories
ORDER BY priority;

-- Execution summary
SELECT
  total_iterations,
  total_tokens,
  stories_completed,
  stories_failed,
  completed_at - started_at as duration
FROM ralph_executions
ORDER BY id DESC
LIMIT 1;
```

---

## 🔧 TROUBLESHOOTING

### Problem: "No stories found"
**Solution**: Reset stories to 'todo' status
```sql
UPDATE ralph_stories
SET status = 'todo', status_emoji = '⬜', retry_count = 0
WHERE project_id = 1;
```

### Problem: "Credential not found in workflow"
**Solution**: Re-select credentials in each node
1. Open workflow
2. Click each node with credential
3. Re-select credential from dropdown
4. Save workflow

### Problem: "Loop not working - only processes 1 story"
**Solution**: Check loop-back connection
1. Open "Ralph - Main Loop" workflow
2. Click node "Loop Back?" (IF node)
3. Verify TRUE output connects to "Get Next Story"
4. If missing, manually create connection

### Problem: "Telegram messages not sending"
**Solution**: Verify chat ID and credential
1. Check Telegram nodes have credential selected
2. Verify chat ID is `8445149012` (string, not number)
3. Test credential with simple message

### Problem: "Wrong AI model used"
**Solution**: Check database and prompt building
```sql
-- Verify models in database
SELECT story_id, ai_model FROM ralph_stories;

-- Should show:
-- RIVET-001: claude-sonnet-4-20250514
-- RIVET-002: claude-sonnet-4-20250514
-- RIVET-003: claude-sonnet-4-20250514
-- RIVET-004: claude-haiku-20250305
-- RIVET-005: claude-haiku-20250305
```

### Problem: "Parse error in Claude response"
**Solution**: Check Claude response format
1. Open execution log in n8n
2. Click "Parse Claude Response" node
3. View input data - check `response.content[0].text`
4. Ensure JSON is wrapped in ```json ... ``` code fence

---

## 📊 EXPECTED COSTS

**Per Full Run** (5 stories):
- Token usage: ~33,500 tokens
- Cost: ~$0.28
- Time: ~15-30 minutes (depending on story complexity)

**Token Breakdown**:
- RIVET-001 (Sonnet 4): ~10,000 tokens (~$0.09)
- RIVET-002 (Sonnet 4): ~12,000 tokens (~$0.11)
- RIVET-003 (Sonnet 4): ~8,000 tokens (~$0.07)
- RIVET-004 (Haiku): ~2,000 tokens (~$0.005)
- RIVET-005 (Haiku): ~1,500 tokens (~$0.004)

**Savings**: 60% vs all-Sonnet-4 approach

---

## ✅ SUCCESS CRITERIA

After deployment, you should have:
- ✅ 4 database tables (ralph_projects, ralph_stories, ralph_iterations, ralph_executions)
- ✅ 5 stories with mixed AI models (3 Sonnet 4, 2 Haiku)
- ✅ 2 active workflows in n8n Cloud
- ✅ 3 configured credentials (Anthropic, Postgres, Telegram)
- ✅ Working webhook endpoint
- ✅ Telegram notifications to chat 8445149012
- ✅ Loop processes all 5 stories sequentially
- ✅ Database populated with results

---

## 🔄 RESET EVERYTHING (If Needed)

To start fresh:

```sql
-- Reset stories to initial state
UPDATE ralph_stories SET
  status = 'todo',
  status_emoji = '⬜',
  retry_count = 0,
  error_message = NULL,
  commit_hash = NULL,
  started_at = NULL,
  completed_at = NULL
WHERE project_id = 1;

-- Clear execution history
DELETE FROM ralph_iterations WHERE project_id = 1;
DELETE FROM ralph_executions WHERE project_id = 1;
```

---

## 📝 NEXT STEPS

After successful deployment:

1. **Monitor First Run**: Watch Telegram for progress updates
2. **Review Commits**: Check git history for Claude's implementations
3. **Test Features**: Verify implemented features work (usage tracking, Stripe, etc.)
4. **Add More Stories**: Insert new stories into `ralph_stories` table
5. **Tune Models**: Adjust `ai_model` column based on results
6. **Scale Up**: Increase `token_budget` or `max_iterations` as needed

---

## 🎯 QUICK REFERENCE

**Migration File**: `rivet_pro/migrations/010_ralph_system.sql`
**Worker Workflow**: `rivet-n8n-workflow/ralph_worker_workflow.json`
**Main Loop Workflow**: `rivet-n8n-workflow/ralph_main_loop_workflow.json`

**Neon Console**: https://console.neon.tech/
**n8n Cloud**: https://mikecranesync.app.n8n.cloud
**Webhook URL**: `https://mikecranesync.app.n8n.cloud/webhook/ralph-main-loop`
**Telegram Chat ID**: `8445149012`

**Database**: `neondb` on `ep-purple-hall-ahimeyn0-pooler.us-east-1.aws.neon.tech`
**Bot Token**: `8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE`

---

**Ready to deploy! Follow the steps above in order. Total time: ~40 minutes.** 🚀
