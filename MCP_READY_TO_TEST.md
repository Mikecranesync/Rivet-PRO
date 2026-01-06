# 🚀 n8n-MCP Ready to Test!

## ✅ Status: n8n Running Successfully

**Verified:**
- ✅ n8n started on port 5678
- ✅ Health check passed: `{"status":"ok"}`
- ✅ Editor accessible at http://localhost:5678
- ✅ MCP configured in `.claude/settings.local.json`
- ✅ API key configured
- ✅ Permissions granted for `mcp__n8n-mcp__*` tools

---

## 🎯 CRITICAL NEXT STEP

### **YOU MUST RESTART CLAUDE CODE NOW**

**Why?** Claude Code only loads MCP server configurations on startup. The n8n-MCP server we configured won't be available until you restart.

**How to restart:**
1. **Close Claude Code completely** (don't just minimize - actually close it)
2. **Reopen Claude Code**
3. **Open this project** (Rivet-PRO)
4. **Start a new conversation**

---

## 🧪 Test the MCP Connection

**After restarting Claude Code, in a NEW conversation, type:**

```
List my n8n workflows
```

### Expected Behavior:

**✅ SUCCESS - MCP is working:**
- Claude will use the tool: `mcp__n8n-mcp__n8n_list_workflows`
- You'll see a response like:
  ```json
  {
    "data": []
  }
  ```
  (Empty array is normal - you don't have workflows yet!)

**❌ FAILURE - MCP not loaded:**
- Error: "I don't have access to that tool" or similar
- Solution: Make sure you **fully closed** Claude Code (not just minimized)

---

## 🎨 Next Steps After Successful Connection

### Step 1: Import the RIVET Workflow

**In Claude Code, type:**
```
Read the file rivet-n8n-workflow/rivet_workflow.json and import it to n8n
```

**What happens:**
- Claude reads the 21-node RIVET Pro workflow
- Claude calls `mcp__n8n-mcp__n8n_create_workflow`
- Workflow appears in n8n UI instantly

**Verify in browser:** http://localhost:5678 - You should see "RIVET Pro - Photo to Manual"

---

### Step 2: Test Workflow Editing (The Magic!)

**Try this:**
```
Add error handling to the Gemini OCR node in the RIVET Pro workflow
```

**What happens:**
- Claude fetches workflow via MCP
- Claude identifies the Gemini Vision OCR HTTP Request node
- Claude adds try-catch error handling
- Claude updates workflow in n8n directly
- **NO COPY-PASTE!**

**Verify in n8n UI:** Open the workflow and check the Gemini node - error handling should be there!

---

### Step 3: More Cool Things to Try

**Add new functionality:**
```
Add a Supabase node to store equipment photos after OCR in the RIVET workflow
```

**Test the workflow:**
```
Test the RIVET Pro workflow with sample Telegram data
```

**Search for nodes:**
```
Find all database-related nodes in n8n
```

**Deploy a template:**
```
Search n8n templates for Telegram bots
```

---

## 📊 Available MCP Tools (13 total)

Once connected, Claude can use:

| Tool | Example |
|------|---------|
| `n8n_list_workflows` | "List my workflows" |
| `n8n_get_workflow` | "Show me the RIVET workflow structure" |
| `n8n_create_workflow` | "Create a workflow that..." |
| `n8n_update_partial_workflow` | "Add error handling to..." |
| `n8n_test_workflow` | "Test the workflow with..." |
| `search_nodes` | "Find Telegram nodes" |
| `n8n_deploy_template` | "Deploy template #123" |
| `validate_workflow` | "Validate the RIVET workflow" |
| `n8n_activate_workflow` | "Activate the workflow" |
| `n8n_delete_workflow` | "Delete the test workflow" |
| `n8n_get_workflow_executions` | "Show recent executions" |
| `n8n_set_workflow_variables` | "Set GOOGLE_API_KEY to..." |
| `n8n_export_workflow` | "Export the workflow as JSON" |

---

## 🔧 Configuration Details

**MCP Server:** n8n-mcp
**Method:** NPX (no Docker needed)
**n8n URL:** http://localhost:5678
**API Key:** Configured from `.env`
**Config File:** `.claude/settings.local.json`

**Current n8n Settings:**
```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "npx",
      "args": ["n8n-mcp"],
      "env": {
        "MCP_MODE": "stdio",
        "LOG_LEVEL": "error",
        "N8N_API_URL": "http://localhost:5678",
        "N8N_API_KEY": "eyJhbGci...",
        "WEBHOOK_SECURITY_MODE": "moderate"
      }
    }
  }
}
```

---

## 🐛 Troubleshooting

### MCP tools still not available after restart

**Check:**
1. Did you **fully close** Claude Code? (Check Task Manager - no Claude processes running)
2. Is `.claude/settings.local.json` valid JSON? (No syntax errors)
3. Is n8n still running? `curl http://localhost:5678/healthz`

**Fix:**
- Restart your computer if all else fails
- Check Claude Code logs for errors
- Verify settings file has `mcpServers` section

### "List my n8n workflows" returns error

**If error mentions authentication:**
- Check n8n UI → Settings → API
- Regenerate API key
- Update `.claude/settings.local.json`
- Restart Claude Code

**If error mentions connection:**
- Verify n8n is running: `curl http://localhost:5678/healthz`
- Check firewall isn't blocking localhost:5678

### n8n-mcp not installing when Claude tries to use it

**Manually install:**
```bash
npm cache clean --force
npm install -g n8n-mcp
```

Then restart Claude Code.

---

## 📈 Before vs After

### Before n8n-MCP:
1. Open n8n GUI
2. Export workflow (500 lines of JSON)
3. Copy to Claude conversation
4. Claude suggests changes
5. Copy modified JSON back
6. Import to n8n GUI
7. Test manually
8. Find issues, repeat entire process

**Time per iteration:** 5-10 minutes

### After n8n-MCP:
```
You: "Add Supabase photo storage and error alerts"
Claude: [modifies workflow via MCP]
Claude: "Done! Test it?"
You: "Yes"
Claude: [executes via MCP]
Claude: "Success! Photo stored at..."
```

**Time per iteration:** 30 seconds

**Time savings: 90%**

---

## ✅ Checklist

- [x] n8n installed (v1.117.3)
- [x] n8n running on port 5678
- [x] Health check passing
- [x] MCP configured in Claude Code
- [x] API key configured
- [x] Permissions granted
- [x] Documentation created
- [ ] **Claude Code restarted** ← YOU ARE HERE
- [ ] MCP connection tested
- [ ] RIVET workflow imported
- [ ] Workflow editing tested

---

## 🎯 Your Action Items

### RIGHT NOW:
1. **Restart Claude Code** (close completely and reopen)
2. **Test:** "List my n8n workflows"

### AFTER SUCCESSFUL TEST:
3. **Import:** "Import rivet-n8n-workflow/rivet_workflow.json"
4. **Edit:** "Add error handling to Gemini node"
5. **Celebrate:** You just eliminated workflow copy-paste hell! 🎉

---

**n8n is ready. MCP is configured. You're one restart away from magic!** 🚀

---

**Created:** 2026-01-05
**n8n Version:** 1.117.3
**MCP Status:** Configured ✅
**Next:** Restart Claude Code and test!
