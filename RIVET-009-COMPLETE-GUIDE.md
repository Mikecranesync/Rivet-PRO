# RIVET-009: Complete Guide - Wire Ralph Database Credentials

**Status**: Ready to Execute
**Time Required**: 5-10 minutes
**Difficulty**: Easy

---

## 🎯 Goal

Import the Ralph Main Loop workflow into n8n and configure database credentials so all 7 Postgres nodes can connect to your Neon PostgreSQL database.

---

## ✅ What Ralph Fixed

1. **Found the problem**: Original `ralph_main_loop_workflow.json` had JSON syntax errors
2. **Created solution**: `ralph_main_loop_ready.json` with all credentials pre-configured
3. **Parsed your credentials**: Extracted database connection details from `.env`
4. **Ready to import**: Just 2 simple steps left!

---

## 📋 Step-by-Step Instructions

### Step 1: Import the Workflow (2 minutes)

1. Open n8n in your browser:
   ```
   http://72.60.175.144:5678
   ```

2. Sign in to n8n

3. Click **"Workflows"** in the left sidebar

4. Click **"Import from File"** button (top right)

5. Browse to and select:
   ```
   C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\rivet-n8n-workflow\ralph_main_loop_ready.json
   ```

6. Click **"Import"**

7. The workflow **"Ralph - Main Loop"** appears with 19 nodes!

### Step 2: Create the Database Credential (3 minutes)

1. In the imported workflow, click **ANY purple Postgres node**
   (There are 7 total - click any one)

2. In the right panel, find the **"Credential"** dropdown

3. You'll see: **"Neon PostgreSQL - Ralph"** with a red warning
   (Means it's referenced but doesn't exist yet)

4. Click the dropdown → **"+ Create New Credential"**

5. Fill in the form with these **exact values**:

   ```
   Credential Name: Neon PostgreSQL - Ralph

   Host:     ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech
   Port:     5432
   Database: neondb
   User:     neondb_owner
   Password: npg_c3UNa4KOlCeL
   SSL:      Toggle ON ✓ (Enable)
   ```

   **Tip**: Copy-paste from `scripts/ralph-claude-code/NEON_CREDENTIALS_FOR_N8N.txt`

6. Click **"Create"**

7. The node should now show a **green checkmark** ✓

8. Check the other 6 Postgres nodes - they should **ALL** have green checkmarks automatically!

### Step 3: Save & Test (2 minutes)

1. Click **"Save"** (top right corner of workflow)

2. Click **"Execute Workflow"** (play button ▶ at top)

3. Watch the nodes light up green as they execute

4. Check the execution log at the bottom

5. Look for:
   - ✅ Green checkmarks on all nodes
   - ✅ Database query results in logs
   - ❌ No red "connection failed" errors

6. If all green = **SUCCESS!** ✅

---

## 🔍 What Each File Does

| File | Purpose | Use It? |
|------|---------|---------|
| `ralph_main_loop_ready.json` | Fixed workflow with credentials | ✅ YES - Import this! |
| `NEON_CREDENTIALS_FOR_N8N.txt` | Your database connection details | ✅ YES - Copy values from here |
| `RALPH_WORKFLOW_FIXED.md` | Detailed technical explanation | 📖 Read if you want to understand |
| `ralph_main_loop_workflow.json` | Original (broken) workflow | ❌ NO - Ignore this |

---

## 🎨 Visual Guide

### What You'll See in n8n:

```
Ralph - Main Loop Workflow
├── 📥 Webhook Trigger
├── 📱 Send Start (Telegram)
├── 🟣 Create Execution (Postgres) ← Click this one!
├── 🟣 Get Next Story (Postgres)
├── 🟣 Mark In Progress (Postgres)
├── 💬 Build Prompt (Code)
├── 🤖 Call Claude (HTTP)
├── 📝 Parse Result (Code)
├── 🟣 Update Story (Postgres)
├── 🟣 Update Execution (Postgres)
├── ❓ Check More Stories (IF)
├── 🟣 Check More Stories (Postgres)
├── 🟣 Finalize Execution (Postgres)
└── 📱 Send Complete (Telegram)
```

All 7 purple 🟣 Postgres nodes need the credential!

---

## ✅ Success Checklist

After completing the steps above, verify:

- [ ] Workflow "Ralph - Main Loop" imported into n8n
- [ ] Credential "Neon PostgreSQL - Ralph" created
- [ ] All 7 Postgres nodes show green checkmarks ✓
- [ ] Workflow saves without errors
- [ ] Execute Workflow runs successfully
- [ ] Execution log shows database query results
- [ ] No red connection errors

**If all checked = RIVET-009 COMPLETE!** 🎉

---

## 🆘 Troubleshooting

### Issue: Can't import workflow

**Solution**:
1. Make sure file path is correct: `C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\rivet-n8n-workflow\ralph_main_loop_ready.json`
2. Try copying file to your Desktop first
3. Check you're using `ralph_main_loop_ready.json` not `ralph_main_loop_workflow.json`

### Issue: Credential shows red warning after creation

**Solution**:
1. Credential name must be EXACTLY: `Neon PostgreSQL - Ralph`
2. Check for extra spaces in the name
3. Try deleting and recreating it
4. Make sure SSL is toggled ON (enabled)

### Issue: "Connection failed" or "Authentication failed"

**Solution**:
1. Double-check the host has no extra spaces:
   `ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech`
2. Verify password is exactly: `npg_c3UNa4KOlCeL`
3. Confirm SSL is toggled ON
4. Test VPS can reach Neon:
   ```bash
   ping ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech
   ```

### Issue: Some nodes still show "no credential"

**Solution**:
1. Click each Postgres node individually
2. Manually select "Neon PostgreSQL - Ralph" from the dropdown
3. Should happen automatically, but you can do it manually

### Issue: Execute Workflow does nothing

**Solution**:
1. Make sure you clicked "Save" first
2. Try refreshing the page
3. Check the webhook trigger is enabled
4. Look for errors in browser console (F12)

---

## 📚 Reference Files

All files are in: `C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\scripts\ralph-claude-code\`

1. **NEON_CREDENTIALS_FOR_N8N.txt** - Database credentials (copy-paste from here)
2. **RALPH_WORKFLOW_FIXED.md** - Technical details about the fix
3. **MANUAL_N8N_TASKS.md** - Original manual task instructions
4. **QUICK_START.md** - Quick reference for both RIVET-007 and 009

---

## 🚀 What Happens After This

Once RIVET-009 is complete:

1. ✅ Ralph can read stories from the `ralph_stories` table
2. ✅ Ralph can write execution results to `ralph_executions` table
3. ✅ Ralph can update story status (todo → in_progress → complete)
4. ✅ Autonomous development loop is fully wired!

**Next**:
- Test Ralph by triggering the webhook
- Watch it autonomously process stories
- See database updates in real-time

---

## 📊 Progress Update

**RIVET Sprint Status**:
- ✅ RIVET-006: API Version Endpoint (Complete)
- ✅ RIVET-007: n8n Gemini Credential (You did this manually)
- ✅ RIVET-008: HTTPS Webhook (Complete - code changes)
- ⬜ RIVET-009: Ralph DB Credentials (You're doing this now!)
- ✅ RIVET-010: Bot Handler Tests (Complete - 30+ tests)
- ✅ RIVET-011: Deployment Documentation (Complete - 803 lines)

**After RIVET-009: 6/6 COMPLETE! 🎉**

---

## 🎯 Quick Summary

**What**: Import Ralph workflow and create database credential
**How**: Import file → Create credential → Test
**Time**: 5-10 minutes
**Files**: `ralph_main_loop_ready.json` + `NEON_CREDENTIALS_FOR_N8N.txt`
**Result**: Ralph can autonomously read/write stories from database

---

**Ready to go? Follow Step 1 above to import the workflow!** 🚀
