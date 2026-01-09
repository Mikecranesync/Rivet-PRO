# AGENT 2: MCP INTEGRATION

**Dependencies:** Wait for Agent 1's workflow endpoints

---

## YOUR MISSION

Configure MCP so Claude Code CLI can directly call the test workflows that Agent 1 builds.

---

## WHAT YOU'RE BUILDING

### 1. MCP Configuration File

```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "npx",
      "args": ["n8n-mcp"],
      "env": {
        "MCP_MODE": "stdio",
        "LOG_LEVEL": "error",
        "DISABLE_CONSOLE_OUTPUT": "true",
        "N8N_API_URL": "https://[N8N_CLOUD_URL]",
        "N8N_API_KEY": "[API_KEY]"
      }
    },
    "rivet-test-orchestrator": {
      "command": "npx",
      "args": ["mcp-remote", "https://[N8N_CLOUD_URL]/mcp/rivet-test-orchestrator"],
      "env": {
        "MCP_AUTH_TOKEN": "[BEARER_TOKEN]"
      }
    },
    "rivet-node-tester": {
      "command": "npx", 
      "args": ["mcp-remote", "https://[N8N_CLOUD_URL]/mcp/rivet-node-tester"],
      "env": {
        "MCP_AUTH_TOKEN": "[BEARER_TOKEN]"
      }
    },
    "rivet-error-analyzer": {
      "command": "npx",
      "args": ["mcp-remote", "https://[N8N_CLOUD_URL]/mcp/rivet-error-analyzer"],
      "env": {
        "MCP_AUTH_TOKEN": "[BEARER_TOKEN]"
      }
    }
  }
}
```

---

### 2. Claude System Instructions

Create `docs/CLAUDE_TESTING_INSTRUCTIONS.md`:

```markdown
## RIVET LIVE TESTING CAPABILITIES

You have access to live testing tools. Use them - don't ask Mike to test manually.

### Available Tools

**rivet-test-orchestrator**
- Execute any workflow and see full results
- Input: { workflowId, testData, testMode }
- Output: All node outputs, errors, timing

**rivet-node-tester**  
- Test single node in isolation
- Input: { nodeType, config, testInput }
- Output: Node output, errors, execution time

**rivet-error-analyzer**
- Get AI-powered fix suggestions
- Input: { executionId }
- Output: Root cause, fix, validation steps

### Testing Protocol

1. **After creating/updating workflow:**
   ```
   rivet-test-orchestrator({
     workflowId: "xxx",
     testData: { manufacturer: "ABB", model_number: "ACS580-01-12A5-4" },
     testMode: "full"
   })
   ```

2. **If errors occur:**
   ```
   rivet-error-analyzer({ executionId: "xxx" })
   ```

3. **Apply fixes and re-test automatically**

4. **For new nodes, test in isolation first:**
   ```
   rivet-node-tester({
     nodeType: "n8n-nodes-base.httpRequest",
     config: { method: "POST", url: "..." },
     testInput: { data: "test" }
   })
   ```

### NEVER Ask User to Test Manually

You have the tools. Use them.

Only ask when:
- You need credentials or API keys
- There's a decision about business logic
- You've exhausted automated troubleshooting
```

---

### 3. Setup Script

```bash
#!/bin/bash
# scripts/setup_mcp.sh

echo "Installing mcp-remote..."
npm install -g mcp-remote

echo ""
echo "MCP Configuration:"
echo "=================="
echo ""
echo "Copy to: ~/.config/claude-code/mcp.json (Linux/Mac)"
echo "     or: %USERPROFILE%\.config\claude-code\mcp.json (Windows)"
echo ""
echo "Then restart Claude Code CLI"
```

---

### 4. Validation Script

```javascript
// scripts/validate_mcp.js
const servers = [
  'rivet-test-orchestrator',
  'rivet-node-tester',
  'rivet-error-analyzer'
];

const N8N_URL = process.env.N8N_CLOUD_URL;
const AUTH_TOKEN = process.env.MCP_AUTH_TOKEN;

servers.forEach(async (server) => {
  try {
    const response = await fetch(`${N8N_URL}/mcp/${server}`, {
      headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` }
    });
    console.log(`✅ ${server}: ${response.status}`);
  } catch (e) {
    console.log(`❌ ${server}: ${e.message}`);
  }
});
```

---

## OUTPUT FILES

```
config/
└── mcp.json                    # MCP configuration

docs/
└── CLAUDE_TESTING_INSTRUCTIONS.md

scripts/
├── setup_mcp.sh
└── validate_mcp.js
```

---

## COMPLETION SIGNAL

Create `AGENT2_COMPLETE.md` with:
- MCP config file path
- Endpoint URLs verified
- Claude instructions documented

---

## COORDINATION

1. Check for `AGENT1_COMPLETE.md` first
2. Get endpoint URLs from Agent 1's output
3. Update MCP config with real URLs
4. Test that Claude can call the tools
