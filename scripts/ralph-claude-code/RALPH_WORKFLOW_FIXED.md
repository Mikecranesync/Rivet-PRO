# ✅ RALPH WORKFLOW FIXED & READY

**Issue**: Original `ralph_main_loop_workflow.json` had JSON syntax errors
**Solution**: Created `ralph_main_loop_ready.json` with proper credentials

---

## What Was Fixed

1. ✅ **Found the problem**: `ralph_main_loop_workflow.json` had malformed JSON
2. ✅ **Used clean version**: `ralph_main_loop_simple.json` (valid JSON)
3. ✅ **Added credentials**: All 7 Postgres nodes now reference "Neon PostgreSQL - Ralph"
4. ✅ **Created**: `ralph_main_loop_ready.json` - Ready to import!

---

## Quick Import & Setup (5 minutes)

### Step 1: Import the Fixed Workflow

1. Open n8n: `http://72.60.175.144:5678`

2. Go to: **Workflows** (left sidebar)

3. Click: **Import from File** (top right)

4. Select file:
   ```
   C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\rivet-n8n-workflow\ralph_main_loop_ready.json
   ```

5. Click: **Import**

6. The workflow "Ralph - Main Loop" will appear!

### Step 2: Create the Neon Credential (ONE TIME)

1. In the imported workflow, click **ANY purple Postgres node**

2. In right panel, find **"Credential"** dropdown

3. It will show: "Neon PostgreSQL - Ralph" with a **red warning icon**
   (This means the credential is referenced but doesn't exist yet)

4. Click the dropdown → **"+ Create New Credential"**

5. Fill in (from NEON_CREDENTIALS_FOR_N8N.txt):
   ```
   Name:     Neon PostgreSQL - Ralph
   Host:     ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech
   Port:     5432
   Database: neondb
   User:     neondb_owner
   Password: npg_c3UNa4KOlCeL
   SSL:      Toggle ON ✓
   ```

6. Click: **"Create"**

7. You should see a **green checkmark** ✓ on the node!

8. Check the other 6 Postgres nodes - they should **ALL** have green checkmarks!
   (They automatically link to the same credential)

### Step 3: Save & Test

1. Click **"Save"** (top right corner)

2. Click **"Execute Workflow"** (play button ▶)

3. Watch the nodes light up as they execute

4. Check execution log (bottom panel) - should see database queries

5. No red errors = **SUCCESS!** ✅

---

## What the Workflow Does

The Ralph Main Loop workflow implements the autonomous development loop:

1. **Create Execution** - Start a new Ralph execution session
2. **Get Next Story** - Fetch next TODO story from database
3. **Mark In Progress** - Update story status to "in_progress"
4. **Build Prompt** - Create Claude Code prompt from story
5. **Call Claude** - Execute Claude Code with the prompt
6. **Parse Result** - Extract success/failure from response
7. **Update Story** - Mark story complete or failed
8. **Update Execution** - Record execution results
9. **Check More Stories** - Loop if more stories remain
10. **Finalize Execution** - Close execution session

All 7 Postgres nodes connect to your Neon database to read stories and write results.

---

## Verification Checklist

After import and credential creation:

- [ ] Workflow imported successfully
- [ ] All 7 Postgres nodes show green checkmarks ✓
- [ ] Workflow saves without errors
- [ ] Execute Workflow runs without database errors
- [ ] Execution log shows database query results

---

## Troubleshooting

**Workflow won't import:**
- Make sure you're using `ralph_main_loop_ready.json`
- Check file exists in `rivet-n8n-workflow/` directory
- Try copying file to desktop first, then import

**Credential shows red warning after creation:**
- The credential name must EXACTLY match: "Neon PostgreSQL - Ralph"
- Try deleting and recreating with exact name
- Check for extra spaces in the name

**Database connection fails:**
- Verify SSL is toggled ON (enabled)
- Double-check host is correct (no extra spaces)
- Test connection: ping ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech
- Check VPS can reach internet

**Nodes still show "no credential":**
- Click each node individually
- Manually select "Neon PostgreSQL - Ralph" from dropdown
- This should happen automatically, but you can do it manually if needed

---

## File Locations

**Fixed Workflow (USE THIS):**
```
C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\rivet-n8n-workflow\ralph_main_loop_ready.json
```

**Credentials Reference:**
```
C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\scripts\ralph-claude-code\NEON_CREDENTIALS_FOR_N8N.txt
```

**Broken Workflow (DON'T USE):**
```
C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\rivet-n8n-workflow\ralph_main_loop_workflow.json
```
(Has JSON syntax errors - ignore this one)

---

## What's Already Configured

✅ All 7 Postgres nodes have credential references
✅ Workflow structure is correct
✅ Node connections are wired
✅ Telegram notifications configured
✅ Claude Code integration ready

❌ Just need to create the actual credential in n8n UI (one-time setup)

---

## After RIVET-009 is Complete

Once the workflow is imported and credential is created:

1. ✅ RIVET-007: n8n Photo Bot v2 Gemini credential configured
2. ✅ RIVET-009: Ralph workflow database credentials wired
3. Ready to test autonomous development!

**Test Ralph:**
```
POST http://72.60.175.144:5678/webhook/ralph-main-loop
```

Or trigger from Telegram:
- Send message to Ralph bot
- Workflow executes automatically
- Stories get processed

---

## Summary

**Problem**: Original workflow had JSON errors
**Solution**: Created clean version with credentials pre-configured
**Result**: Import → Create credential → Done!

**Time**: 5 minutes total
**Difficulty**: Easy (just import and fill in 6 fields)

---

**Ready? Import ralph_main_loop_ready.json and create the credential!** 🚀
