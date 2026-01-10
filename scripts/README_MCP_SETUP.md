# MCP Setup Scripts - README

## Overview

Two PowerShell scripts for configuring n8n MCP integration with Claude Code.

| Script | Purpose | Use When |
|--------|---------|----------|
| **setup_mcp_dual.ps1** | Configure **both** MCP methods | Recommended for full functionality |
| **setup_mcp.ps1** | Configure **n8n-mcp package only** | Simple setup, single method |

---

## Quick Start

### Recommended: Dual Setup

```powershell
# Configure both n8n-native and n8n-mcp
.\scripts\setup_mcp_dual.ps1

# Choose option 3: Both
# Restart Claude Code CLI
```

### Simple: Package Only

```powershell
# Configure n8n-mcp package (13 tools)
.\scripts\setup_mcp.ps1

# Restart Claude Code CLI
```

---

## Script Details

### setup_mcp_dual.ps1 ⭐ RECOMMENDED

**What it does**:
- Lets you choose: Native MCP, n8n-mcp package, or both
- Prompts for appropriate tokens based on choice
- Configures one or both MCP servers
- Creates/updates `~/.config/claude-code/mcp.json`

**Options**:
1. **n8n Native MCP** - Direct workflow triggers (requires MCP Server Token)
2. **n8n-mcp Package** - 13 MCP tools (requires API Key)
3. **Both** - Full functionality (requires both tokens)

**Tokens Needed**:
- **MCP Server Token**: Settings → API → MCP Server → Create Token
- **API Key**: Settings → API → Generate Key

**Usage**:
```powershell
.\scripts\setup_mcp_dual.ps1

# Example interaction:
# Choose method: 3 (Both)
# n8n URL: https://mikecranesync.app.n8n.cloud
# MCP Server Token: eyJ...(mcp-server-api)
# API Key: eyJ...(public-api)
# Test connection: y
```

**Output**:
```json
{
  "mcpServers": {
    "n8n-native": {
      "command": "npx",
      "args": ["-y", "supergateway", ...]
    },
    "n8n-mcp": {
      "command": "npx",
      "args": ["-y", "n8n-mcp"],
      "env": {...}
    }
  }
}
```

---

### setup_mcp.ps1

**What it does**:
- Configures n8n-mcp package only (simpler setup)
- Prompts for n8n URL and API Key
- Creates/updates `~/.config/claude-code/mcp.json`

**Tokens Needed**:
- **API Key**: Settings → API → Generate Key

**Usage**:
```powershell
.\scripts\setup_mcp.ps1

# Example interaction:
# n8n URL: https://mikecranesync.app.n8n.cloud
# API Key: eyJ...(public-api)
# Test connection: y
```

**Output**:
```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "npx",
      "args": ["-y", "n8n-mcp"],
      "env": {
        "N8N_API_URL": "...",
        "N8N_API_KEY": "..."
      }
    }
  }
}
```

---

## Token Guide

### How to Get MCP Server Token

```
1. Open n8n: https://your-instance.app.n8n.cloud
2. Click Settings (⚙️)
3. Go to: API
4. Scroll to: "MCP Server" section
5. Click: "Create MCP Server Token"
6. Copy token (starts with eyJ...)
```

**Token Details**:
- JWT with `aud: "mcp-server-api"`
- Used by: `supergateway` to connect to `/mcp-server/http`
- Purpose: Direct MCP protocol support

### How to Get API Key

```
1. Open n8n: https://your-instance.app.n8n.cloud
2. Click Settings (⚙️)
3. Go to: API
4. Scroll to: "API Keys" section
5. Click: "Generate API Key"
6. Copy key (starts with eyJ...)
```

**Token Details**:
- JWT with `aud: "public-api"`
- Used by: `n8n-mcp` package to call `/api/v1/*`
- Purpose: REST API access for workflow CRUD

---

## Comparison Table

| Feature | setup_mcp_dual.ps1 | setup_mcp.ps1 |
|---------|-------------------|---------------|
| **Methods** | Choose 1 or 2 methods | n8n-mcp only |
| **n8n Native** | ✅ Optional | ❌ No |
| **n8n-mcp Package** | ✅ Optional | ✅ Yes |
| **Tokens** | 1 or 2 tokens | 1 token (API Key) |
| **Complexity** | Medium | Simple |
| **Flexibility** | High | Low |
| **Use Case** | Full functionality | Quick setup |

---

## After Setup

### 1. Restart Claude Code CLI

**CRITICAL**: You **must** restart Claude Code after running setup!

```powershell
# Close terminal completely
# Reopen terminal
# Start Claude Code again
```

### 2. Verify Setup

**Test n8n-native** (if configured):
```
Ask Claude: "What MCP servers are available?"
# Should show: n8n-native
```

**Test n8n-mcp** (if configured):
```
Ask Claude: "List my n8n workflows"
# Should show all workflows
```

### 3. Use with RIVET Tests

```bash
# Python test client (independent of MCP)
python scripts/test_client.py validate-url "https://example.com"

# Claude via MCP (after Agent 1 deploys workflows)
Ask Claude: "Run the URL validator workflow"
```

---

## Troubleshooting

### Script won't run

**Error**: "cannot be loaded because running scripts is disabled"

**Solution**:
```powershell
# Set execution policy (run as Administrator)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run script again
.\scripts\setup_mcp_dual.ps1
```

### "Config not found" after restart

**Cause**: Config in wrong location

**Solution**:
```powershell
# Check config exists
ls $env:USERPROFILE\.config\claude-code\mcp.json

# If missing, run setup again
.\scripts\setup_mcp_dual.ps1
```

### Claude doesn't see MCP servers

**Checklist**:
- [ ] Ran setup script
- [ ] **Restarted Claude Code CLI** (most common!)
- [ ] Config file exists (`~/.config/claude-code/mcp.json`)
- [ ] JSON is valid (no syntax errors)

**Verify**:
```powershell
# Validate JSON
Get-Content $env:USERPROFILE\.config\claude-code\mcp.json | ConvertFrom-Json

# Should not error
```

### Wrong token type

**Error**: "Unauthorized" or "Invalid token"

**Cause**: Mixed up MCP Server Token and API Key

**Solution**:
- n8n-native needs: **MCP Server Token** (aud: mcp-server-api)
- n8n-mcp needs: **API Key** (aud: public-api)

Check token audience:
```bash
# Decode JWT (first part)
echo "eyJ..." | base64 -d | jq .aud
```

---

## Migration Scenarios

### From Manual Config → Script

```powershell
# Backup your manual config
cp $env:USERPROFILE\.config\claude-code\mcp.json mcp.json.manual_backup

# Run setup (will auto-backup again)
.\scripts\setup_mcp_dual.ps1

# Old config saved to: mcp.json.backup.YYYYMMDD_HHMMSS
```

### From Single Method → Dual Method

```powershell
# Run dual setup
.\scripts\setup_mcp_dual.ps1

# Choose option 3: Both
# Enter both tokens
# Restart Claude Code
```

### From Dual → Single Method

```powershell
# Edit .mcp.json manually, or
# Run setup_mcp.ps1 to overwrite with single method
.\scripts\setup_mcp.ps1
```

---

## Related Files

- **Main Documentation**: `docs/CLAUDE_TESTING_PROTOCOL.md`
- **Dual MCP Guide**: `docs/MCP_DUAL_SETUP_GUIDE.md`
- **Test Client**: `scripts/test_client.py`
- **MCP Config**: `~/.config/claude-code/mcp.json`

---

## Support

**Issues**: https://github.com/anthropics/claude-code/issues
**n8n Docs**: https://docs.n8n.io

---

**Last Updated**: 2026-01-09
