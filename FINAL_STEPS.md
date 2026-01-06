# Final Steps to Activate n8n-MCP Integration

## 🎯 What You Need to Do Right Now

### Step 1: Start n8n in the CMD Window

**In the CMD window that just opened, type:**
```bash
npx n8n
```

**Press Enter**

**Wait for this message:**
```
n8n ready on http://localhost:5678
Editor is now accessible via:
http://localhost:5678/
```

This usually takes 30-60 seconds on first run.

---

### Step 2: Verify n8n is Running

**Open a new terminal/PowerShell and run:**
```bash
curl http://localhost:5678/healthz
```

**Expected response:**
```json
{"status":"ok"}
```

Or just open your browser: http://localhost:5678

---

### Step 3: Restart Claude Code

**CRITICAL:** You must restart Claude Code for it to load the new MCP configuration.

1. Close Claude Code completely
2. Reopen Claude Code
3. Open this project (Rivet-PRO)

---

### Step 4: Test the MCP Connection

**In a new Claude Code conversation, type:**
```
List my n8n workflows
```

**What should happen:**
- Claude will use the `mcp__n8n-mcp__n8n_list_workflows` tool
- You'll see a list of workflows (probably empty at first)
- No errors about "tool not found"

**If this works, MCP is connected! 🎉**

---

### Step 5: Import the RIVET Workflow

**In Claude Code, type:**
```
Read the file rivet-n8n-workflow/rivet_workflow.json and import it to n8n
```

**What should happen:**
- Claude reads the workflow JSON
- Claude uses `mcp__n8n-mcp__n8n_create_workflow` to import it
- Workflow appears in n8n UI with 21 nodes

---

### Step 6: Test Workflow Editing (The Magic Part!)

**Now try this:**
```
Add error handling to the Gemini OCR node in the RIVET Pro workflow
```

**What should happen:**
- Claude fetches the workflow via MCP
- Claude identifies the Gemini OCR HTTP Request node
- Claude modifies the node to add try-catch error handling
- Claude updates the workflow in n8n directly
- **NO COPY-PASTE REQUIRED!**

You can verify the changes in the n8n UI at http://localhost:5678

---

## What's Already Done ✅

| Task | Status |
|------|--------|
| n8n installed | ✅ v1.117.3 |
| MCP configured in Claude Code | ✅ `.claude/settings.local.json` |
| MCP permissions granted | ✅ `mcp__n8n-mcp__*` |
| n8n API key configured | ✅ From `.env` file |
| Documentation created | ✅ 3 guide files |
| Git committed and pushed | ✅ Commit 4735f2c |
| CMD window opened | ✅ Waiting for you to type `npx n8n` |

---

## Troubleshooting

### n8n takes forever to start

**First run can take 1-2 minutes.** You'll see:
```
Initializing n8n process...
Setting up database...
Loading workflows...
```

Just wait - it's setting up the database for the first time.

### "command not found: npx"

**Install Node.js/npm:**
- Download from: https://nodejs.org/
- Restart terminal after install
- Verify: `node --version`

### Port 5678 already in use

**Find what's using it:**
```bash
netstat -ano | findstr :5678
```

**Kill that process:**
```bash
taskkill /F /PID <PID_NUMBER>
```

Then start n8n again.

### n8n-mcp installation failed earlier

**Don't worry!** The MCP configuration uses `npx n8n-mcp` which will auto-install it when Claude Code tries to use it.

If you want to pre-install:
```bash
npm cache clean --force
npm install -g n8n-mcp
```

### MCP tools don't appear after restart

1. Check `.claude/settings.local.json` has the `mcpServers` section
2. Make sure you **fully closed** Claude Code (not just minimized)
3. Check for JSON syntax errors in settings file
4. Try restarting your computer if all else fails

---

## Alternative: Use VPS Instead

If local n8n is being difficult, use the VPS:

### 1. SSH to VPS and start n8n:
```bash
ssh root@72.60.175.144
systemctl start n8n
# or
docker start n8n
```

### 2. Update MCP config:
Edit `.claude/settings.local.json`:
```json
{
  "mcpServers": {
    "n8n-mcp": {
      "env": {
        "N8N_API_URL": "http://72.60.175.144:5678"
      }
    }
  }
}
```

### 3. Restart Claude Code and test

---

## Success Indicators

### ✅ n8n Running:
- Browser shows n8n UI at http://localhost:5678
- `curl http://localhost:5678/healthz` returns `{"status":"ok"}`

### ✅ MCP Connected:
- "List my n8n workflows" works in Claude Code
- No "tool not found" errors
- Claude shows workflow data (or empty array)

### ✅ Ready for Production:
- Can import RIVET workflow via Claude
- Can edit workflows by talking to Claude
- Changes appear in n8n UI instantly
- No copy-paste required!

---

## What You'll Be Able to Do

### Before (Current Pain):
1. Open n8n GUI → Export JSON → Copy 500 lines
2. Paste to Claude → Claude edits → Copy 500 lines back
3. Import to n8n → Test → Find bug → Repeat

### After (With MCP):
```
You: "Add Supabase storage for photos and error notifications"
Claude: [reads workflow → adds nodes → updates n8n]
Claude: "Done! Added Supabase node and Telegram error alerts. Test it?"
You: "Yes"
Claude: [executes workflow]
Claude: "Success! Photo stored at https://..."
```

**80% faster workflow editing. Zero copy-paste errors. Instant testing.**

---

## Quick Reference

```bash
# Start n8n
npx n8n

# Check if running
curl http://localhost:5678/healthz

# Open n8n UI
# Browser: http://localhost:5678

# Restart Claude Code
# (Close completely and reopen)

# Test MCP connection
# In Claude: "List my n8n workflows"

# Import RIVET workflow
# In Claude: "Import rivet-n8n-workflow/rivet_workflow.json"

# Edit workflow
# In Claude: "Add error handling to Gemini node"
```

---

**You're literally one command away from eliminating workflow editing hell:**

**Type in the CMD window:** `npx n8n`

Then restart Claude Code and say: **"List my n8n workflows"**

🚀 That's it!
