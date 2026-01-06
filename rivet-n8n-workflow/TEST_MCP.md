# n8n-MCP Testing Guide

## Prerequisites

### 1. Install n8n-mcp (if using NPX method)

```bash
npm install -g n8n-mcp
```

### 2. Start n8n Instance

**Option A: Local Development**
```bash
# If installed globally
n8n start

# Or via npx
npx n8n
```

**Option B: VPS Instance**
```bash
# SSH to VPS
ssh root@72.60.175.144

# Start n8n service
systemctl start n8n

# Or start Docker container
docker start n8n
```

**Verify n8n is running:**
```bash
# Local
curl http://localhost:5678/healthz

# VPS
curl http://72.60.175.144:5678/healthz
```

Expected response: `{"status":"ok"}`

---

## MCP Configuration Status

✅ **n8n-MCP server configured** in `.claude/settings.local.json`
✅ **Permissions granted** for `mcp__n8n-mcp__*` tools
✅ **API key configured** from `.env` file

**Current Configuration:**
- **Method:** NPX (recommended)
- **n8n URL:** http://localhost:5678
- **MCP Mode:** stdio
- **Log Level:** error

---

## Testing MCP Connection

### Test 1: List Workflows

**In Claude Code conversation:**
```
User: "List my n8n workflows"
```

**Expected Claude Action:**
- Calls: `mcp__n8n-mcp__n8n_list_workflows`
- Returns: JSON array of workflows (or empty array if none exist)

**If this fails:**
1. Check n8n is running: `curl http://localhost:5678/healthz`
2. Restart Claude Code to load new MCP configuration
3. Check API key is valid in n8n UI → Settings → API

---

### Test 2: Search Nodes

**In Claude Code conversation:**
```
User: "Find Telegram nodes in n8n"
```

**Expected Claude Action:**
- Calls: `mcp__n8n-mcp__search_nodes`
- Returns: List of Telegram-related nodes (Telegram, Telegram Trigger, etc.)

---

### Test 3: Get Workflow (if workflows exist)

**In Claude Code conversation:**
```
User: "Show me the RIVET Pro workflow structure"
```

**Expected Claude Action:**
- Calls: `mcp__n8n-mcp__n8n_get_workflow`
- Returns: Workflow JSON with nodes and connections

---

## Importing the RIVET Workflow via MCP

### Option 1: Direct Import via Claude (Recommended)

**In Claude Code conversation:**
```
User: "Read the workflow from rivet-n8n-workflow/rivet_workflow.json and import it to n8n"
```

**Expected Claude Actions:**
1. Reads: `rivet-n8n-workflow/rivet_workflow.json`
2. Calls: `mcp__n8n-mcp__n8n_create_workflow` with workflow data
3. Returns: Workflow ID and success confirmation

### Option 2: Python Auto-Import (Fallback)

**If MCP import fails:**
```bash
cd rivet-n8n-workflow

python n8n_auto_import.py \
  --n8n-url http://localhost:5678 \
  --api-key eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyY2Y1ZDM0MC1hMWM3LTRiYzYtYTQwMy02MjljZDFlZjc0MzMiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY3NjI5ODYzfQ.V0n_f1G1Hb4_pFoedIKC5NWS5Kdh3oRaouRR7ck_fSg
```

---

## Example MCP Workflow Editing

### Add Error Handling to a Node

**Conversation:**
```
User: "Add try-catch error handling to the Gemini OCR node in the RIVET Pro workflow"
```

**Expected Flow:**
1. Claude calls `n8n_get_workflow` to fetch current workflow
2. Claude identifies the Gemini OCR HTTP Request node
3. Claude calls `n8n_update_partial_workflow` with error handling added
4. Workflow updated in n8n

### Add New Node to Workflow

**Conversation:**
```
User: "Add a Supabase node after OCR to store equipment photos in my RIVET workflow"
```

**Expected Flow:**
1. Claude calls `search_nodes` to find Supabase node
2. Claude calls `n8n_get_workflow` to understand current structure
3. Claude calls `n8n_update_partial_workflow` to insert Supabase node
4. Node added with proper connections

### Test Workflow Execution

**Conversation:**
```
User: "Test the RIVET Pro workflow with this sample data: {photo_url: 'https://example.com/motor.jpg'}"
```

**Expected Flow:**
1. Claude calls `n8n_test_workflow` with test data
2. Workflow executes (OCR → Search → Response)
3. Claude returns execution result and equipment data

---

## Troubleshooting

### Issue: MCP tools not appearing

**Diagnosis:** Claude Code hasn't loaded new configuration

**Solution:**
1. Restart Claude Code completely (close and reopen)
2. Verify `.claude/settings.local.json` has `mcpServers` section
3. Check for JSON syntax errors in config file

### Issue: "n8n-mcp command not found"

**Diagnosis:** n8n-mcp not installed globally

**Solution:**
```bash
npm install -g n8n-mcp

# Verify installation
npx n8n-mcp --version
```

### Issue: "Connection refused"

**Diagnosis:** n8n is not running or wrong URL

**Solution:**
```bash
# Check if n8n is running
curl http://localhost:5678/healthz

# If not running, start it
n8n start

# If VPS, update .claude/settings.local.json:
# Change N8N_API_URL to "http://72.60.175.144:5678"
```

### Issue: "Authentication failed"

**Diagnosis:** Wrong or expired API key

**Solution:**
1. Open n8n UI: http://localhost:5678
2. Go to Settings → API
3. Generate new API key
4. Update `.claude/settings.local.json` with new key
5. Restart Claude Code

### Issue: Docker networking error (if using Docker method)

**Diagnosis:** Docker can't reach localhost

**Solution:**
Change N8N_API_URL in `.claude/settings.local.json`:
```json
"N8N_API_URL": "http://host.docker.internal:5678"
```

---

## MCP Tools Available

Once connected, Claude has access to these n8n-MCP tools:

| Tool | Purpose | Example Usage |
|------|---------|---------------|
| `n8n_list_workflows` | List all workflows | "Show me all my workflows" |
| `n8n_get_workflow` | Get workflow details | "Show me the RIVET workflow" |
| `n8n_create_workflow` | Create new workflow | "Create a workflow for..." |
| `n8n_update_partial_workflow` | Edit workflow | "Add error handling to..." |
| `n8n_test_workflow` | Test workflow | "Test this workflow with..." |
| `search_nodes` | Find n8n nodes | "Find Telegram nodes" |
| `n8n_deploy_template` | Deploy template | "Deploy n8n.io template #123" |
| `validate_workflow` | Validate workflow | "Check if workflow is valid" |

---

## Success Indicators

✅ **MCP Connected Successfully:**
- Claude can list workflows without errors
- Claude can read workflow structure
- No "tool not found" errors

✅ **n8n Running:**
- `/healthz` endpoint returns `{"status":"ok"}`
- n8n UI accessible at http://localhost:5678

✅ **API Authentication Working:**
- No "401 Unauthorized" errors
- Claude can create/update workflows

✅ **Ready for Production:**
- Can edit workflows without copy-paste
- Can test workflows via Claude
- Workflow changes persist in n8n

---

## Next Steps After Successful Connection

1. **Import RIVET Workflow:**
   - "Read rivet-n8n-workflow/rivet_workflow.json and import it"

2. **Configure Workflow Variables:**
   - "Set GOOGLE_API_KEY to AIzaSyBOEFzA3fWyS_s92h4Sd7ZaWIctiVXZjlA"
   - "Set ATLAS_CMMS_URL to http://72.60.175.144:8000"

3. **Test Workflow:**
   - "Test the RIVET workflow with a sample photo URL"

4. **Customize Workflow:**
   - "Add equipment type filtering for Siemens and Rockwell only"
   - "Add error notifications to Telegram when OCR fails"

5. **Deploy to VPS:**
   - "Export this workflow and import it to 72.60.175.144:5678"

---

## Quick Reference Commands

```bash
# Start n8n locally
n8n start

# Check n8n health
curl http://localhost:5678/healthz

# Test MCP connection (via Claude)
"List my n8n workflows"

# Import RIVET workflow (via Claude)
"Read rivet-n8n-workflow/rivet_workflow.json and import it to n8n"

# Restart Claude Code (Windows)
# Close Claude Code completely and reopen

# View n8n logs
tail -f ~/.n8n/logs/n8n.log

# Check npx n8n-mcp works
npx n8n-mcp --help
```

---

## Configuration Files Reference

| File | Purpose | Location |
|------|---------|----------|
| `.claude/settings.local.json` | MCP server config | `C:\Users\hharp\.claude\settings.local.json` |
| `rivet_workflow.json` | RIVET workflow | `rivet-n8n-workflow/rivet_workflow.json` |
| `.env` | n8n API key | Project root |
| `n8n_auto_import.py` | Fallback import script | `rivet-n8n-workflow/` |

---

**Status:** n8n-MCP configured and ready to test once n8n is running!
