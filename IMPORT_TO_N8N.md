# How to Import Rivet Startup Orchestrator to n8n

## ✅ Your n8n MCP is Now Configured!

I've configured your Claude Desktop to connect to n8n with these settings:

```json
{
  "n8n": {
    "command": "npx -y n8n-mcp",
    "env": {
      "N8N_API_URL": "http://localhost:5678",
      "N8N_API_KEY": "eyJhbGci..."
    }
  }
}
```

**To activate:** Restart Claude Desktop app

---

## Import the Workflow (Manual Method)

Since the API import has validation issues, use the n8n web UI instead:

### Step 1: Access n8n
```
http://localhost:5678
```

### Step 2: Create New Workflow
1. Click "+ Add workflow" (top left)
2. Name it: "Rivet-PRO Startup Orchestrator"

### Step 3: Add Nodes Manually

#### Node 1: Manual Trigger
- Type: Manual Trigger
- Position: Start

#### Node 2: Execute Command - Check Docker
- Type: Execute Command
- Command: `docker info`
- Continue on fail: Yes

#### Node 3: IF - Docker OK?
- Type: IF
- Condition: `{{ $json.exitCode }} equals 0`

#### Node 4: HTTP Request - Check CMMS
- Type: HTTP Request
- Method: GET
- URL: `http://localhost:8081/actuator/health`
- Continue on fail: Yes

#### Node 5: IF - CMMS Running?
- Type: IF
- Condition: `{{ $json.statusCode }} equals 403 OR {{ $json.statusCode }} equals 200`

#### Node 6: Execute Command - Start CMMS
- Type: Execute Command
- Command: `cd C:\Users\hharp\OneDrive\Desktop\grashjs-cmms && docker-compose up -d`
- Only runs if CMMS not running

#### Node 7: Wait - Give CMMS time
- Type: Wait
- Amount: 30 seconds

#### Node 8: HTTP Request - Login to CMMS
- Type: HTTP Request
- Method: POST
- URL: `http://localhost:8081/auth/login`
- Body (JSON):
```json
{
  "email": "mike@cranesync.com",
  "password": "Bo1ws2er@12"
}
```

#### Node 9: Execute Command - Start Bot
- Type: Execute Command
- Command: `cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO && start /B python bot_launcher.py`

#### Node 10: Telegram - Send Success Notification
- Type: HTTP Request
- Method: POST
- URL: `https://api.telegram.org/bot8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE/sendMessage`
- Body (JSON):
```json
{
  "chat_id": "8445149012",
  "text": "✅ Rivet-PRO Started!"
}
```

### Step 4: Connect the Nodes
```
Manual Trigger → Check Docker → Docker OK?
                                     ↓ True
                                Check CMMS → CMMS Running?
                                                 ↓ False
                                            Start CMMS → Wait → Login → Start Bot → Notify
                                                 ↓ True
                                            Login → Start Bot → Notify
```

### Step 5: Test It!
Click "Execute Workflow" and watch it run!

---

## Or Use n8n MCP from Claude Code

Since MCP is now configured, you can ask me to:

```
Create an n8n workflow that starts Rivet-PRO
```

And I'll use the n8n MCP tools to create it automatically!

---

## Current Status

✅ **n8n Running**: http://localhost:5678
✅ **API Key Configured**: In .env and MCP
✅ **MCP Server Added**: In Claude Desktop config
✅ **Credentials**: mike@cranesync.com / Bo1ws2er@12

⏳ **Next**: Restart Claude Desktop to activate n8n MCP
⏳ **Then**: Create workflow via MCP or manual import
