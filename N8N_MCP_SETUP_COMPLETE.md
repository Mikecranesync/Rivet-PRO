# n8n + Claude Integration - Setup Complete

**Status**: ✅ Fully Configured
**Date**: 2026-01-07

---

## What Was Installed

### 1. n8n-mcp Server (MCP Server)
- **Method**: npx (on-demand)
- **Location**: Configured in Claude Desktop
- **Purpose**: Gives Claude deep knowledge of 545+ n8n nodes and 2,709 workflow templates

### 2. n8n-skills (7 Skills)
- **Location**: `C:\Users\hharp\.claude\skills\`
- **Skills Installed**:
  1. `n8n-expression-syntax` - Writing {{}} expressions, $json/$node variables
  2. `n8n-mcp-tools-expert` - Searching nodes, validating, accessing templates
  3. `n8n-workflow-patterns` - Creating workflows, connecting nodes
  4. `n8n-validation-expert` - Validation fails, debugging workflow errors
  5. `n8n-node-configuration` - Configuring nodes, understanding dependencies
  6. `n8n-code-javascript` - Writing JS in Code nodes, $helpers usage
  7. `n8n-code-python` - Writing Python in Code nodes

---

## Configuration

### Claude Desktop Config
**File**: `C:\Users\hharp\AppData\Roaming\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "npx",
      "args": ["-y", "n8n-mcp"],
      "env": {
        "N8N_API_URL": "http://localhost:5678",
        "N8N_API_KEY": "eyJhbGc...",
        "MCP_MODE": "stdio",
        "LOG_LEVEL": "error",
        "DISABLE_CONSOLE_OUTPUT": "true",
        "WEBHOOK_SECURITY_MODE": "moderate"
      }
    }
  }
}
```

### n8n Instance
- **URL**: http://localhost:5678
- **Status**: Running
- **API Key**: Configured in `.env` and Claude Desktop

### Claude Code CLI Config
**Files Created**:
1. **`.mcp.json`** (project root) - MCP server configuration
2. **`.claude/settings.local.json`** - Permissions and auto-enable

**Project `.mcp.json`**:
```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "npx",
      "args": ["-y", "n8n-mcp"],
      "env": {
        "N8N_API_URL": "http://localhost:5678",
        "N8N_API_KEY": "...",
        "MCP_MODE": "stdio",
        "LOG_LEVEL": "error",
        "DISABLE_CONSOLE_OUTPUT": "true",
        "WEBHOOK_SECURITY_MODE": "moderate"
      }
    }
  }
}
```

**Settings**: `enableAllProjectMcpServers: true` + `mcp__n8n-mcp__*` permission

---

## Available MCP Tools (20 Total)

### Core Tools (7)
| Tool | Purpose |
|------|---------|
| `tools_documentation` | Get docs for any MCP tool (START HERE!) |
| `search_nodes` | Full-text search across 545+ nodes |
| `get_node` | Get node info, docs, properties, versions |
| `validate_node` | Validate node configurations |
| `validate_workflow` | Complete workflow validation |
| `search_templates` | Search 2,709 workflow templates |
| `get_template` | Get complete workflow JSON |

### n8n Management Tools (13)
| Tool | Purpose |
|------|---------|
| `n8n_create_workflow` | Create new workflows |
| `n8n_get_workflow` | Retrieve workflows |
| `n8n_update_full_workflow` | Full workflow replacement |
| `n8n_update_partial_workflow` | Diff-based updates |
| `n8n_delete_workflow` | Delete workflows |
| `n8n_list_workflows` | List with filtering |
| `n8n_validate_workflow` | Validate by ID |
| `n8n_autofix_workflow` | Auto-fix common errors |
| `n8n_workflow_versions` | Version history/rollback |
| `n8n_deploy_template` | Deploy from n8n.io |
| `n8n_test_workflow` | Test/trigger execution |
| `n8n_executions` | Manage execution history |
| `n8n_health_check` | Check n8n connectivity |

---

## What Works Where

### ✅ Claude Desktop
- **Status**: Configured, needs restart
- **n8n-mcp server**: 20 MCP tools
- **n8n skills**: 7 skills
- **Activation**: Restart Claude Desktop

### ✅ Claude Code CLI
- **Status**: Configured, needs new session
- **n8n-mcp server**: 20 MCP tools
- **n8n skills**: 7 skills
- **Activation**: Start new Claude Code session in this directory

---

## How to Use

### Restart Claude Desktop (Required!)
For the changes to take effect:
1. Close Claude Desktop completely
2. Reopen Claude Desktop
3. The n8n-mcp server will start automatically on first use

### Start New Claude Code Session (Required!)
For Claude Code CLI:
1. Exit this session (Ctrl+C or type `exit`)
2. Start a new session: `claude code` in this directory
3. The n8n-mcp server will load automatically from `.mcp.json`

### Test the Integration
Try these commands in Claude Desktop or Claude Code:

```
"Search for telegram nodes and show me webhook templates"
```

Claude should automatically:
1. Use `search_nodes` to find Telegram-related nodes
2. Use `search_templates` to find webhook workflow templates
3. Present you with relevant options

### Workflow Development Process

```
1. Template Discovery (FIRST!)
   └→ "Find me a template for [use case]"

2. Node Discovery (if no template)
   └→ "What nodes can I use for [task]?"

3. Configuration Phase
   └→ "Configure this [node type] to do [action]"

4. Validation Phase
   └→ "Validate my workflow configuration"

5. Building Phase
   └→ "Create a workflow that does [task]"

6. Deployment & Testing
   └→ "Deploy and test the workflow"
```

---

## RIVET Pro Integration Points

This setup is perfect for your RIVET Pro architecture:

### Current Use Cases
1. **Photo OCR → Equipment Matching**
   - Telegram webhook receives photo
   - n8n triggers Gemini Vision OCR
   - Matches equipment in database
   - Returns to Telegram bot

2. **Work Order Creation Flow**
   - Multi-step conversation handler
   - Equipment lookup and validation
   - Create work order with mandatory equipment link
   - Store in Neon PostgreSQL

3. **Manual Retrieval System**
   - Equipment search by keyword
   - Fuzzy matching for part numbers
   - Return manual PDFs or links
   - Track usage for knowledge base

### Template-First Approach
- Search 2,709 proven workflow patterns
- Deploy with one command
- Claude validates before production
- JSON as source of truth (AI can't accidentally modify)

---

## Troubleshooting

### Skills Not Loading
```bash
# Verify skills are in place
ls -la /c/Users/hharp/.claude/skills/ | grep n8n

# Should show 7 n8n-* directories
```

### MCP Server Not Connecting
```bash
# Check n8n is running
curl http://localhost:5678

# Verify API key in .env
grep N8N_API_KEY .env

# Check Claude Desktop config
cat "$APPDATA/Claude/claude_desktop_config.json"
```

### n8n API Key Expired
```bash
# Generate new API key in n8n:
# 1. Open http://localhost:5678
# 2. Settings → API
# 3. Create new API key
# 4. Update .env and Claude Desktop config
```

---

## Next Steps

### For Atlas CMMS Integration
1. ✅ n8n-mcp configured - can now build workflows with Claude
2. 📝 Create Telegram → OCR → Equipment workflow
3. 📝 Create Work Order creation workflow
4. 📝 Create Manual retrieval workflow
5. 📝 Deploy to production n8n instance

### Quick Workflow Creation
```
"Create a workflow that:
1. Receives a Telegram message with a photo
2. Sends it to Gemini Vision for OCR
3. Extracts equipment details (model, serial, manufacturer)
4. Searches our PostgreSQL database for matching equipment
5. If found, returns equipment manual link
6. If not found, creates a new equipment entry
7. Sends results back to Telegram"
```

Claude will now:
- Search for relevant template
- Configure all nodes
- Validate the workflow
- Create it in n8n
- Test it

---

## Resources

- **n8n-mcp GitHub**: https://github.com/czlonkowski/n8n-mcp
- **n8n-skills GitHub**: https://github.com/czlonkowski/n8n-skills
- **n8n-mcp Hosted**: https://dashboard.n8n-mcp.com (100 free calls/day)
- **n8n-skills Website**: https://www.n8n-skills.com
- **Your n8n Instance**: http://localhost:5678

---

## Summary

You now have:
- ✅ n8n-mcp server configured in Claude Desktop
- ✅ 7 n8n skills installed
- ✅ 20 MCP tools available for workflow automation
- ✅ Full knowledge of 545+ n8n nodes
- ✅ Access to 2,709 workflow templates
- ✅ Direct n8n API integration

**Next action**: Restart Claude Desktop and try: "Show me telegram webhook templates"
