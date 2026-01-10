# n8n MCP Dual Setup - Quick Reference

**Last Updated**: 2026-01-09

## TL;DR

RIVET supports **TWO** n8n MCP integration methods. Use both for full functionality!

```powershell
# Run dual setup (recommended)
.\scripts\setup_mcp_dual.ps1

# Choose option 3: Both
# Restart Claude Code CLI
```

---

## The Two Methods

### 1. n8n Native MCP (n8n-native)

**What**: n8n's built-in MCP server
**Package**: `supergateway`
**Token**: MCP Server Token (from Settings → API → MCP Server)
**Endpoint**: `https://your-instance.app.n8n.cloud/mcp-server/http`

**Best For**:
- ✅ Triggering test workflows
- ✅ Direct Claude integration
- ✅ Running workflows with parameters
- ✅ Official n8n support

**Claude Usage**:
```
"Run the URL validator workflow"
"Trigger the test runner with this payload"
"Execute the LLM judge"
```

### 2. n8n-mcp Package (n8n-mcp)

**What**: Third-party npm package with 13 MCP tools
**Package**: `n8n-mcp`
**Token**: API Key (from Settings → API → Generate Key)
**Endpoint**: `https://your-instance.app.n8n.cloud/api/v1/*`

**Best For**:
- ✅ Listing workflows
- ✅ Creating/updating workflows
- ✅ Managing workflow CRUD
- ✅ Viewing execution history

**Claude Usage**:
```
"List all my n8n workflows"
"Show me the URL validator workflow"
"Update the test runner to add logging"
"Create a new workflow"
```

---

## Token Comparison

| Aspect | MCP Server Token | API Key |
|--------|------------------|---------|
| **Location** | Settings → API → MCP Server | Settings → API → Generate Key |
| **Action** | Create MCP Server Token | Generate API Key |
| **JWT Audience** | `mcp-server-api` | `public-api` |
| **Used By** | supergateway | n8n-mcp package |
| **Purpose** | Direct MCP protocol | REST API access |
| **Example** | `eyJ...mcp-server-api...` | `eyJ...public-api...` |

**IMPORTANT**: These are **different tokens**! Don't mix them up.

---

## Configuration Files

### .mcp.json (Both Methods)

```json
{
  "mcpServers": {
    "n8n-native": {
      "command": "npx",
      "args": [
        "-y",
        "supergateway",
        "--streamableHttp",
        "https://mikecranesync.app.n8n.cloud/mcp-server/http",
        "--header",
        "authorization:Bearer <MCP_SERVER_TOKEN>"
      ]
    },
    "n8n-mcp": {
      "command": "npx",
      "args": ["-y", "n8n-mcp"],
      "env": {
        "MCP_MODE": "stdio",
        "LOG_LEVEL": "error",
        "N8N_API_URL": "https://mikecranesync.app.n8n.cloud/api/v1",
        "N8N_API_KEY": "<API_KEY>"
      }
    }
  }
}
```

**Location**:
- Windows: `C:\Users\<user>\.config\claude-code\mcp.json`
- Mac/Linux: `~/.config/claude-code/mcp.json`

---

## Setup Scripts

### setup_mcp_dual.ps1 (Recommended)

Configures **both** methods with clear prompts.

```powershell
.\scripts\setup_mcp_dual.ps1

# Choose:
# 1 - n8n Native only
# 2 - n8n-mcp Package only
# 3 - Both (recommended)
```

**Features**:
- ✅ Choose one or both methods
- ✅ Automatic backup of existing config
- ✅ Input validation (URL, JWT format)
- ✅ Optional connection test
- ✅ Cross-platform (Windows/Mac/Linux)

### setup_mcp.ps1 (Original)

Configures **n8n-mcp package only**.

```powershell
.\scripts\setup_mcp.ps1

# Prompts for:
# - n8n URL
# - API Key (public-api)
```

**Use this if**:
- You only want the n8n-mcp package
- You don't need native MCP triggers
- You want simpler setup

---

## When to Use Which

| Scenario | Use Method | Claude Command |
|----------|------------|----------------|
| Trigger URL validator test | n8n-native | "Run URL validator with https://..." |
| List all workflows | n8n-mcp | "List my n8n workflows" |
| Execute test runner | n8n-native | "Execute test runner for ABB ACS580" |
| Show workflow code | n8n-mcp | "Show me the URL validator workflow" |
| Run LLM judge | n8n-native | "Judge this manual quality: ..." |
| Create new workflow | n8n-mcp | "Create a new test workflow" |
| Check execution history | n8n-mcp | "Show recent test runs" |
| Update workflow | n8n-mcp | "Add logging to test runner" |

**Pro Tip**: Use both! Native for triggers, package for management.

---

## Troubleshooting

### Error: "MCP server not found"

**Cause**: Claude Code not restarted after setup

**Solution**:
```
1. Close Claude Code CLI completely
2. Reopen terminal
3. Start Claude Code again
4. Try command again
```

### Error: "Invalid token" (n8n-native)

**Cause**: Using API Key instead of MCP Server Token

**Solution**:
```
1. Go to n8n: Settings → API
2. Find "MCP Server" section (NOT "API Keys")
3. Click "Create MCP Server Token"
4. Run setup again with correct token
```

### Error: "Unauthorized" (n8n-mcp)

**Cause**: Using MCP Server Token instead of API Key

**Solution**:
```
1. Go to n8n: Settings → API
2. Find "API Keys" section (NOT "MCP Server")
3. Click "Generate API Key"
4. Run setup again with correct key
```

### Both Methods Not Working

**Checklist**:
- [ ] Ran setup script (`setup_mcp_dual.ps1`)
- [ ] **Restarted Claude Code CLI** (most common issue!)
- [ ] Tokens are correct (check JWT audience)
- [ ] n8n instance URL is correct
- [ ] `.mcp.json` exists in config directory
- [ ] `.mcp.json` is valid JSON

**Verify Config**:
```powershell
# Check if config exists
ls ~/.config/claude-code/mcp.json  # Mac/Linux
dir $env:USERPROFILE\.config\claude-code\mcp.json  # Windows

# Validate JSON
Get-Content ~/.config/claude-code/mcp.json | ConvertFrom-Json
```

---

## Testing Your Setup

After setup and restart:

### Test n8n-native

```
Ask Claude: "What MCP servers are available?"
# Should show: n8n-native

Ask Claude: "Trigger a test workflow"
# Should work if workflows exist
```

### Test n8n-mcp

```
Ask Claude: "List my n8n workflows"
# Should show all workflows

Ask Claude: "How many workflows do I have?"
# Should count and respond
```

### Test Both Together

```
User: "List my workflows, then run the URL validator"

Claude:
<uses n8n-mcp to list>
"You have 5 workflows: ..."

<uses n8n-native to execute>
"✓ URL Validation: PASS"
```

---

## Migration Guide

### From n8n-mcp Only → Both Methods

```powershell
# Backup current config
cp ~/.config/claude-code/mcp.json ~/.config/claude-code/mcp.json.backup

# Run dual setup
.\scripts\setup_mcp_dual.ps1

# Choose option 3: Both
# Enter MCP Server Token (new)
# Enter existing API Key (same as before)

# Restart Claude Code CLI
```

### From Manual Config → Scripted Setup

```powershell
# Your existing .mcp.json will be backed up automatically
.\scripts\setup_mcp_dual.ps1

# Follow prompts
# Old config saved to: mcp.json.backup.YYYYMMDD_HHMMSS
```

---

## FAQ

**Q: Do I need both methods?**
A: Recommended! Native for triggers, package for management. But each works standalone.

**Q: Can I use local n8n?**
A: Yes! Use `http://localhost:5678` as the URL. Local n8n doesn't support MCP Server tokens, so use n8n-mcp package only.

**Q: Which token is which?**
A:
- MCP Server Token: JWT with `aud: "mcp-server-api"` (for n8n-native)
- API Key: JWT with `aud: "public-api"` (for n8n-mcp)

**Q: Can I have different n8n instances?**
A: No, both methods must use the same instance. But you can switch by re-running setup.

**Q: What if I already have .mcp.json?**
A: Scripts automatically back it up before overwriting (timestamped backup).

**Q: Do I need to restart Claude Code?**
A: **YES!** Always restart after changing `.mcp.json`. Most common issue.

---

## Quick Commands Reference

```powershell
# Setup both methods (recommended)
.\scripts\setup_mcp_dual.ps1

# Setup n8n-mcp only
.\scripts\setup_mcp.ps1

# Backup current config
cp ~/.config/claude-code/mcp.json ~/.config/claude-code/mcp.json.manual_backup

# Validate config
Get-Content ~/.config/claude-code/mcp.json | ConvertFrom-Json

# Check if Claude sees MCP servers (after restart)
# Ask Claude: "What MCP servers are connected?"
```

---

## Related Documentation

- **Full Testing Protocol**: [CLAUDE_TESTING_PROTOCOL.md](./CLAUDE_TESTING_PROTOCOL.md)
- **Python Test Client**: [CLAUDE_TESTING_PROTOCOL.md](./CLAUDE_TESTING_PROTOCOL.md#method-1-python-test-client)
- **n8n Documentation**: https://docs.n8n.io/hosting/configuration/mcp-server/

---

## Version History

- **1.0.0** (2026-01-09): Initial dual MCP setup guide
