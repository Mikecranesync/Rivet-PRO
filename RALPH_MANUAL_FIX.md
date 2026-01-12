# RALPH Manual Fix Guide

## Problem
The workflow is stopping after "Create Execution" node completes successfully.

## Root Cause
Either:
1. **Credential mismatch** - Some nodes using different Postgres credentials
2. **Query issues** - The "Get Next Story" query isn't finding stories
3. **Connection issue** - Database connection from n8n isn't reaching the right database

---

## 🔧 MANUAL FIX - Do These Steps in n8n UI

### Step 1: Test the Database Connection

1. Open "Ralph - Main Loop" workflow
2. Click the **"Get Next Story"** node (Postgres node)
3. Click **"Test step"** or **"Execute node"** button
4. Does it return data?
   - **YES** → Problem is elsewhere, go to Step 3
   - **NO/ERROR** → Go to Step 2

### Step 2: Fix the Postgres Credential

1. Go to **Settings → Credentials**
2. Click **"Neon - RALPH"** to edit
3. **Verify these EXACT settings**:
   ```
   Host: ep-purple-hall-ahimeyn0-pooler.us-east-1.aws.neon.tech
   Database: neondb
   User: neondb_owner
   Password: npg_c3UNa4KOlCeL
   Port: 5432
   SSL: ✅ ENABLED
   ```
4. Click **"Test Connection"** - MUST show SUCCESS
5. Click **Save**

### Step 3: Apply Credential to ALL Postgres Nodes

In the "Ralph - Main Loop" workflow, click EACH of these nodes and verify "Credential to connect with" is **"Neon - RALPH"**:

- [ ] Create Execution
- [ ] Get Next Story
- [ ] Mark In Progress
- [ ] Update Story
- [ ] Update Execution
- [ ] Check More Stories
- [ ] Finalize Execution

**Change ANY that are different to "Neon - RALPH"**

### Step 4: Test Individual Nodes

1. Click **"Get Next Story"** node
2. Click **"Test step"** button
3. **Expected output**: JSON with story data like:
   ```json
   {
     "id": 1,
     "project_id": 1,
     "story_id": "RIVET-001",
     "title": "Usage Tracking System",
     "status": "todo",
     "ai_model": "claude-sonnet-4-20250514"
   }
   ```

If you see this, the database connection works!

### Step 5: Check Stories in Database

Run this in **Neon SQL Editor**:

```sql
SELECT story_id, status, priority, ai_model
FROM ralph_stories
WHERE project_id = 1 AND status = 'todo'
ORDER BY priority
LIMIT 1;
```

**Expected**: Should return RIVET-001 with status 'todo'

If NO results → Run this to reset:
```sql
UPDATE ralph_stories
SET status = 'todo',
    retry_count = 0,
    started_at = NULL,
    completed_at = NULL
WHERE project_id = 1;
```

### Step 6: Simplify the "Get Next Story" Query

If still not working, edit the "Get Next Story" node:

**Change query FROM**:
```sql
SELECT * FROM ralph_stories WHERE project_id = 1 AND status = 'todo' AND retry_count < 3 ORDER BY priority ASC LIMIT 1
```

**TO** (simplified):
```sql
SELECT * FROM ralph_stories WHERE status = 'todo' ORDER BY priority LIMIT 1
```

This removes the retry_count check in case that's causing issues.

### Step 7: Enable Continue on Fail

For EVERY Postgres node:
1. Click the node
2. Go to **Settings** tab (gear icon)
3. Under **"On Error"**, select: **"Continue"**
4. This prevents the workflow from stopping on errors

---

## 🚀 After Fixes - Trigger Test

Once you've done Steps 1-7, trigger again:

```bash
curl "https://mikecranesync.app.n8n.cloud/webhook/ralph-main-loop"
```

---

## 🔍 Debug Output

If still failing, check the execution log:
1. Go to Executions
2. Click the failed execution
3. Click each node to see input/output
4. **Look at "Get Next Story" node output** - what does it say?

---

## 🎯 Expected Success Flow

When working correctly, you should see:
1. ✅ Webhook triggers
2. ✅ Send Start (Telegram message sent)
3. ✅ Create Execution (returns execution ID)
4. ✅ Get Next Story (returns RIVET-001 data)
5. ✅ Check Stories Remain (continue_loop = true)
6. ✅ Should Continue (routes to Mark In Progress)
7. ✅ Mark In Progress (updates story status)
8. ✅ Build Prompt (creates Claude prompt)
9. ✅ Story Start (Telegram message)
10. ✅ Call Worker (executes Claude)
... continues

---

**Start with Step 3 - verify ALL 7 Postgres nodes use "Neon - RALPH" credential!**
