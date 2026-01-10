# RIVET Testing Protocol

**Version**: 1.0.0
**Last Updated**: 2026-01-09
**Purpose**: Complete guide for testing RIVET n8n workflows

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    RIVET Test Infrastructure                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ALL TEST LOGIC LIVES IN N8N WORKFLOWS                     │
│  Python/Claude are THIN CLIENTS that just call webhooks    │
│                                                             │
│  ┌──────────────┐         ┌──────────────┐                │
│  │   Agent 1    │────────▶│  n8n Cloud   │                │
│  │ (Builds      │         │  (Test       │                │
│  │  workflows)  │         │   workflows) │                │
│  └──────────────┘         └───────┬──────┘                │
│                                    │                        │
│  ┌──────────────┐         ┌───────▼──────┐                │
│  │   Agent 2    │────────▶│  Test Client │                │
│  │ (This guide) │         │  (calls      │                │
│  │              │         │   webhooks)  │                │
│  └──────────────┘         └──────────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key Principle**: Workflows persist across sessions. Tests can be triggered anytime.

---

## Quick Start (2 minutes)

### Choose Your Method

| Method | When to Use | Setup Time |
|--------|-------------|------------|
| **Python Test Client** | Automated testing, CI/CD, local development, need JSON output | 1 minute |
| **n8n-MCP Tools** | Claude integration, workflow management, interactive testing | 2 minutes |

**Choose Python Client if**:
- Running tests in scripts or CI/CD
- Need structured JSON output
- Want simple CLI interface
- Testing locally without Claude

**Choose n8n-MCP if**:
- Claude needs to trigger tests
- Managing workflows programmatically
- Need to deploy/update workflows
- Want Claude to analyze results

---

## Dual MCP Approach (Recommended)

**RIVET now supports TWO MCP integration methods** - you can use both simultaneously!

### Method Comparison

| Feature | n8n Native MCP | n8n-mcp Package |
|---------|----------------|-----------------|
| **Package** | `supergateway` | `n8n-mcp` |
| **Connection** | n8n's built-in `/mcp-server/http` | Third-party npm package |
| **Token Type** | MCP Server Token (`mcp-server-api` audience) | API Key (`public-api` audience) |
| **Setup** | Settings → API → Create MCP Server Token | Settings → API → Generate API Key |
| **Use Case** | Direct workflow triggers, Claude integration | Workflow CRUD, management tools |
| **Tools** | Native MCP protocol support | 13 specialized MCP tools |
| **Best For** | Triggering test workflows | Managing/creating workflows |

### How to Get Both Tokens

#### 1. MCP Server Token (for Native MCP)
```
1. Open n8n: https://mikecranesync.app.n8n.cloud
2. Go to: Settings → API
3. Find section: "MCP Server"
4. Click: "Create MCP Server Token"
5. Copy token (starts with eyJ...)
```

**Token Details**:
- Audience: `mcp-server-api`
- Used by: `supergateway` to connect to `/mcp-server/http`
- Purpose: Direct MCP protocol support

#### 2. API Key (for n8n-mcp Package)
```
1. Open n8n: https://mikecranesync.app.n8n.cloud
2. Go to: Settings → API
3. Click: "Generate API Key"
4. Copy key (starts with eyJ...)
```

**Token Details**:
- Audience: `public-api`
- Used by: `n8n-mcp` package to call `/api/v1/*`
- Purpose: Workflow management via REST API

### Configuration Example

Your `.mcp.json` should have **both servers**:

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
        "DISABLE_CONSOLE_OUTPUT": "true",
        "N8N_API_URL": "https://mikecranesync.app.n8n.cloud/api/v1",
        "N8N_API_KEY": "<API_KEY>",
        "WEBHOOK_SECURITY_MODE": "moderate"
      }
    }
  }
}
```

### Setup Script (Dual Method)

Use the enhanced setup script to configure both:

```powershell
# Run dual-method setup
.\scripts\setup_mcp_dual.ps1

# Choose option 3: Both (recommended)
# Enter n8n URL
# Enter MCP Server Token
# Enter API Key
# Restart Claude Code CLI
```

### When to Use Each

**Use n8n-native for**:
```
Claude: "Run the URL validator workflow with https://example.com"
Claude: "Trigger the test runner"
Claude: "Execute the LLM judge workflow"
```

**Use n8n-mcp for**:
```
Claude: "List all n8n workflows"
Claude: "Show me the URL validator workflow code"
Claude: "Update the test runner workflow to add logging"
Claude: "Create a new workflow from template"
```

**Both work together**:
```
User: "Show me all workflows, then run the URL validator"

Claude:
<uses n8n-mcp to list workflows>
"You have 5 workflows: ..."

<uses n8n-native to execute URL validator>
"✓ URL Validation: PASS - Score: 8.5/10"
```

### Verification

After setup, verify both servers:

```
# Restart Claude Code CLI first!

# Test n8n-native
Ask Claude: "Trigger a test workflow"

# Test n8n-mcp
Ask Claude: "List my n8n workflows"

# Both should work without errors
```

---

## Method 1: Python Test Client

### Installation

```bash
# Install dependencies
pip install click requests python-dotenv

# Verify installation
python scripts/test_client.py --version
```

### Configuration

Add to `.env`:

```bash
# N8N Test Client (Agent 2)
N8N_WEBHOOK_BASE_URL=https://mikecranesync.app.n8n.cloud
N8N_WEBHOOK_TIMEOUT=30
```

**Environment Variables**:
- `N8N_WEBHOOK_BASE_URL` - Your n8n cloud instance URL (no trailing slash)
- `N8N_WEBHOOK_TIMEOUT` - Request timeout in seconds (default: 30)

### CLI Usage

#### Validate URL

Check if a URL is accessible and valid (format, status code, file type):

```bash
# Basic URL validation
python scripts/test_client.py validate-url "https://example.com/manual.pdf"

# With equipment context
python scripts/test_client.py validate-url "https://example.com/manual.pdf" \
  --equipment-type "motor" \
  --manufacturer "siemens"

# JSON output (for programmatic use)
python scripts/test_client.py validate-url "https://example.com/manual.pdf" --json-output
```

**Example Output**:
```
============================================================
Test Result: PASS
============================================================
Test Type:    rivet-url-validator
Duration:     1234.56ms

Payload:
{
  "url": "https://example.com/manual.pdf",
  "context": {
    "equipment_type": "motor",
    "manufacturer": "siemens"
  }
}

Response:
{
  "success": true,
  "score": 8.5,
  "is_reachable": true,
  "status_code": 200,
  "is_pdf": true,
  "file_size_mb": 2.3,
  "issues": []
}
============================================================
```

#### Judge Manual Quality

Score a manual using LLM (relevance, completeness, clarity):

```bash
# Create test payload
cat > manual_test.json << 'EOF'
{
  "url": "https://example.com/siemens-s7-1200.pdf",
  "content": "Siemens S7-1200 PLC Programming Manual...",
  "equipment_type": "plc",
  "manufacturer": "siemens"
}
EOF

# Run LLM judge
python scripts/test_client.py judge-manual manual_test.json

# JSON output
python scripts/test_client.py judge-manual manual_test.json --json-output
```

**Example Output**:
```
============================================================
Test Result: PASS
============================================================
Test Type:    rivet-llm-judge
Duration:     5678.90ms

Response:
{
  "success": true,
  "quality_score": 9.2,
  "completeness": 8.8,
  "clarity": 9.5,
  "relevance": 9.0,
  "issues": [],
  "recommendation": "High quality manual, suitable for Manual Hunter"
}
============================================================
```

#### Run Generic Test

Execute end-to-end or integration tests:

```bash
# Create test case
cat > e2e_test.json << 'EOF'
{
  "test_case": "abb_acs580",
  "equipment": {
    "manufacturer": "ABB",
    "model": "ACS580",
    "type": "vfd"
  }
}
EOF

# Run test
python scripts/test_client.py run-test e2e e2e_test.json

# JSON output
python scripts/test_client.py run-test e2e e2e_test.json --json-output
```

### Programmatic Usage

Import and use in Python scripts:

```python
from scripts.test_client import validate_url, judge_manual, run_test, TestResult

# Validate URL
result = validate_url("https://example.com/manual.pdf")
if result.success:
    print(f"Score: {result.response['score']}/10")
    print(f"Duration: {result.duration_ms:.2f}ms")
else:
    print(f"Failed: {result.error}")

# Judge manual quality
manual_data = {
    "url": "https://example.com/manual.pdf",
    "content": "Manual content...",
    "equipment_type": "motor"
}
result = judge_manual(manual_data)
print(f"Quality: {result.response.get('quality_score', 'N/A')}/10")

# Run test with custom payload
result = run_test("e2e", {"test_case": "abb_acs580"})
if result.success:
    print("Test passed!")
else:
    print(f"Test failed: {result.error}")
```

### Error Handling

```python
from scripts.test_client import WebhookError, ValidationError

try:
    result = validate_url("not-a-url")
except ValidationError as e:
    print(f"Input error: {e}")
except WebhookError as e:
    print(f"Network error: {e}")
```

**Exit Codes**:
- `0` - Test passed
- `1` - Test failed or error occurred

---

## Method 2: n8n-MCP Tools

Two MCP integration options available (see "Dual MCP Approach" above for comparison).

### Setup Option A: Both Methods (Recommended)

```powershell
# Configure both n8n-native and n8n-mcp
.\scripts\setup_mcp_dual.ps1

# Choose option 3: Both
# Enter n8n URL: https://mikecranesync.app.n8n.cloud
# Enter MCP Server Token (from Settings → API → MCP Server)
# Enter API Key (from Settings → API → Generate Key)

# Restart Claude Code CLI
```

### Setup Option B: n8n-mcp Package Only

```powershell
# Configure only n8n-mcp package (13 tools)
.\scripts\setup_mcp.ps1

# Enter n8n URL: https://mikecranesync.app.n8n.cloud
# Enter API key: eyJ... (from Settings → API → Generate Key)

# Restart Claude Code CLI
```

**What the setup scripts do**:
1. Prompt for n8n URL and token(s)
2. Create/update `~/.config/claude-code/mcp.json`
3. Back up existing config (if exists)
4. Validate connection (optional)

**Config Location**:
- Windows: `C:\Users\<user>\.config\claude-code\mcp.json`
- Mac/Linux: `~/.config/claude-code/mcp.json`

### Available MCP Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `n8n_list_workflows` | List all workflows | "List my n8n workflows" |
| `n8n_get_workflow` | Get workflow details | "Show me the URL validator workflow" |
| `n8n_test_workflow` | Execute workflow | "Run the URL validator with..." |
| `n8n_get_workflow_executions` | View execution history | "Show recent test runs" |
| `n8n_activate_workflow` | Toggle workflow on/off | "Activate the test runner workflow" |
| `n8n_create_workflow` | Create new workflow | (Used by Agent 1) |
| `n8n_update_partial_workflow` | Edit workflow | (Used by Agent 1) |
| `n8n_delete_workflow` | Delete workflow | "Delete the old test workflow" |
| `validate_workflow` | Validate before deploy | "Check if this workflow is valid" |
| `search_nodes` | Find n8n nodes | "Find Webhook nodes" |
| `search_templates` | Find templates | "Search for HTTP request templates" |
| `n8n_deploy_template` | Deploy from template | "Deploy manual validator template" |
| `n8n_set_workflow_variables` | Configure variables | "Set API key variable" |

### Usage with Claude

#### List Workflows

```
User: "List my n8n workflows"

Claude: I'll list your n8n workflows.

<uses mcp__n8n-mcp__n8n_list_workflows>

You have 5 workflows:
1. RIVET-URL-Validator (active)
2. RIVET-LLM-Judge (active)
3. RIVET-Test-Runner (active)
4. RIVET-Photo-OCR (active)
5. RIVET-Manual-Hunter (active)
```

#### Execute Test Workflow

```
User: "Test this URL: https://example.com/manual.pdf"

Claude: I'll validate that URL using the RIVET URL validator workflow.

<uses mcp__n8n-mcp__n8n_test_workflow>

✓ URL Validation: PASS
- URL: https://example.com/manual.pdf
- Score: 8.5/10
- Reachable: ✓
- Format: PDF (2.3MB)
- Status: 200 OK

The manual looks good for Manual Hunter ingestion.
```

#### View Execution History

```
User: "Show me recent test runs"

Claude: I'll check the recent workflow executions.

<uses mcp__n8n-mcp__n8n_get_workflow_executions>

Recent Test Runs (last 10):
1. URL Validator - 2 minutes ago - ✓ Success
2. LLM Judge - 15 minutes ago - ✓ Success
3. Test Runner - 1 hour ago - ✗ Failed
4. URL Validator - 2 hours ago - ✓ Success
...
```

### Best Practices for Claude

When using MCP tools with Claude:

1. **Always show results to user**
   - Don't just execute silently
   - Format results clearly
   - Explain what the test checks

2. **Explain test purpose**
   - What does this test validate?
   - Why is this important?
   - What does the score mean?

3. **Suggest next steps**
   - If test passes: "Ready for production"
   - If test fails: "Try fixing X, then retest"
   - If unclear: "Need more context about Y"

4. **Use JSON for parsing**
   - When programmatic analysis needed
   - When integrating with other tools
   - When storing results

---

## Test Workflows Reference

### Overview Table

| Workflow | Webhook | Purpose | Input | Output | Avg Time |
|----------|---------|---------|-------|--------|----------|
| **RIVET-URL-Validator** | `/webhook/rivet-url-validator` | Validate URL accessibility and format | `{url, context?}` | `{success, score, issues}` | 1-3s |
| **RIVET-LLM-Judge** | `/webhook/rivet-llm-judge` | Score manual quality with LLM | `{url?, content?, equipment_type}` | `{quality_score, completeness}` | 5-10s |
| **RIVET-Test-Runner** | `/webhook/rivet-test-runner` | Generic test executor | `{test_type, payload}` | `{success, results}` | 10-30s |

---

### RIVET-URL-Validator

**Purpose**: Check if a URL is accessible, valid format, correct file type

**Webhook**: `POST https://mikecranesync.app.n8n.cloud/webhook/rivet-url-validator`

**Input Schema**:
```json
{
  "url": "string (required)",
  "context": {
    "equipment_type": "string (optional)",
    "manufacturer": "string (optional)"
  }
}
```

**Output Schema**:
```json
{
  "success": true,
  "score": 8.5,
  "is_reachable": true,
  "status_code": 200,
  "is_pdf": true,
  "file_size_mb": 2.3,
  "content_type": "application/pdf",
  "issues": []
}
```

**Example Payloads**:

Valid PDF:
```json
{
  "url": "https://example.com/siemens-s7-1200.pdf",
  "context": {
    "equipment_type": "plc",
    "manufacturer": "siemens"
  }
}
```

Invalid URL:
```json
{
  "url": "https://404-not-found.com/manual.pdf"
}
```

**Test Cases**:
- ✅ Valid PDF URL (200 OK)
- ✅ Valid HTML documentation page
- ❌ 404 Not Found
- ❌ 403 Forbidden
- ❌ Timeout (>10s)
- ❌ Invalid SSL certificate
- ❌ Wrong file type (expected PDF, got HTML)

**Expected Response Times**:
- Fast (local): 100-500ms
- Normal: 500-2000ms
- Slow: 2000-5000ms
- Timeout: >5000ms (fail)

---

### RIVET-LLM-Judge

**Purpose**: Score manual quality using LLM (relevance, completeness, clarity)

**Webhook**: `POST https://mikecranesync.app.n8n.cloud/webhook/rivet-llm-judge`

**Input Schema**:
```json
{
  "url": "string (optional)",
  "content": "string (optional)",
  "equipment_type": "string (required)",
  "manufacturer": "string (optional)",
  "model": "string (optional)"
}
```

**Note**: Either `url` or `content` must be provided (or both)

**Output Schema**:
```json
{
  "success": true,
  "quality_score": 9.2,
  "completeness": 8.8,
  "clarity": 9.5,
  "relevance": 9.0,
  "technical_accuracy": 8.9,
  "issues": [
    "Missing electrical specifications",
    "Diagrams are low resolution"
  ],
  "strengths": [
    "Clear installation instructions",
    "Comprehensive troubleshooting section"
  ],
  "recommendation": "High quality manual, suitable for Manual Hunter",
  "verdict": "PASS"
}
```

**Scoring Rubric**:
- **9-10**: Excellent - Complete, clear, accurate
- **7-8**: Good - Minor issues, usable
- **5-6**: Fair - Missing some info, needs review
- **3-4**: Poor - Incomplete or unclear
- **1-2**: Very Poor - Major issues, not usable

**Example Payloads**:

Full manual with URL:
```json
{
  "url": "https://example.com/siemens-s7-1200.pdf",
  "equipment_type": "plc",
  "manufacturer": "siemens",
  "model": "S7-1200"
}
```

Content snippet:
```json
{
  "content": "Siemens S7-1200 PLC Programming Manual\n\nTable of Contents:\n1. Installation\n2. Wiring\n3. Programming\n4. Troubleshooting\n...",
  "equipment_type": "plc",
  "manufacturer": "siemens"
}
```

**Test Cases**:
- ✅ Complete OEM manual (score >8)
- ✅ Quick start guide (score 6-7)
- ❌ Wrong equipment type (score <3)
- ❌ Generic documentation (score <5)
- ❌ Corrupted/unreadable file (error)

**Expected Response Times**:
- Fast (cached): 2-4s
- Normal: 5-10s
- Slow (large manual): 10-20s
- Timeout: >30s (fail)

---

### RIVET-Test-Runner

**Purpose**: Generic test executor for end-to-end, integration, and stress tests

**Webhook**: `POST https://mikecranesync.app.n8n.cloud/webhook/rivet-test-runner`

**Input Schema**:
```json
{
  "test_type": "string (required)",
  "payload": {
    "test_case": "string (optional)",
    "equipment": {
      "manufacturer": "string",
      "model": "string",
      "type": "string"
    },
    "options": {
      "skip_ocr": false,
      "mock_manual_search": false,
      "verbose": false
    }
  }
}
```

**Test Types**:
- `e2e` - Full Photo → OCR → CMMS → Manual flow
- `integration` - Test workflow integration points
- `stress` - Load testing (multiple concurrent requests)
- `manual_hunter` - Manual search accuracy (quick → deep)
- `ocr_accuracy` - OCR quality testing

**Output Schema**:
```json
{
  "success": true,
  "test_type": "e2e",
  "test_case": "abb_acs580",
  "results": {
    "ocr_score": 9.1,
    "cmms_found": true,
    "manual_found": true,
    "manual_score": 8.7,
    "total_time_ms": 12340
  },
  "steps": [
    {"step": "OCR", "status": "PASS", "duration_ms": 2300},
    {"step": "CMMS Search", "status": "PASS", "duration_ms": 450},
    {"step": "Manual Search", "status": "PASS", "duration_ms": 9590}
  ],
  "verdict": "PASS",
  "issues": []
}
```

**Example Payloads**:

End-to-End Test (ABB ACS580 VFD):
```json
{
  "test_type": "e2e",
  "payload": {
    "test_case": "abb_acs580",
    "equipment": {
      "manufacturer": "ABB",
      "model": "ACS580",
      "type": "vfd"
    }
  }
}
```

Manual Hunter Accuracy Test:
```json
{
  "test_type": "manual_hunter",
  "payload": {
    "test_case": "common_equipment",
    "options": {
      "verbose": true
    }
  }
}
```

Stress Test:
```json
{
  "test_type": "stress",
  "payload": {
    "concurrent_requests": 10,
    "duration_minutes": 5
  }
}
```

**Test Cases Included**:
1. `abb_acs580` - ABB VFD (common, should pass)
2. `siemens_s7_1200` - Siemens PLC (common, should pass)
3. `obscure_motor` - Rare equipment (tests deep search)
4. `invalid_nameplate` - Bad OCR input (should fail gracefully)
5. `timeout_test` - Slow external service (tests timeout handling)

**Expected Response Times**:
- E2E Test: 10-30s
- Integration Test: 5-15s
- Stress Test: 5-10 minutes
- Manual Hunter: 2-25s (depending on tier)

---

## Claude Integration

### How Claude Triggers Tests

**Two Methods**:

1. **Direct MCP** (Preferred)
   - Uses `mcp__n8n-mcp__*` tools
   - Direct workflow execution
   - View execution history
   - Manage workflows

2. **Via Python Client**
   - Uses `Bash` tool to run `python scripts/test_client.py`
   - Gets structured JSON output
   - Can parse and analyze results
   - Easier error handling

### Example Conversations

#### Example 1: URL Validation

```
User: "Test this URL: https://example.com/manual.pdf"

Claude: I'll validate that URL using the RIVET URL validator.

<uses mcp__n8n-mcp__n8n_test_workflow with URL validator workflow ID>

✓ URL Validation: PASS
- URL: https://example.com/manual.pdf
- Score: 8.5/10
- Reachable: ✓
- Format: PDF (2.3MB)
- Status: 200 OK

The manual looks good for Manual Hunter ingestion. Would you like me to:
1. Score the manual quality with LLM judge?
2. Run a full end-to-end test?
3. Add this to the manual database?
```

#### Example 2: Manual Quality Scoring

```
User: "Score this manual: https://example.com/siemens-plc.pdf (Siemens S7-1200 PLC)"

Claude: I'll score that manual using the RIVET LLM judge.

<uses Python client or MCP tool>

📊 Manual Quality Score: 9.2/10

Breakdown:
- Completeness: 8.8/10
- Clarity: 9.5/10
- Relevance: 9.0/10
- Technical Accuracy: 8.9/10

✅ Strengths:
- Clear installation instructions
- Comprehensive troubleshooting section
- Good wiring diagrams

⚠️ Minor Issues:
- Missing electrical specifications
- Diagrams are low resolution

Recommendation: High quality manual, suitable for Manual Hunter

This is an excellent manual. Would you like me to add it to the database?
```

#### Example 3: End-to-End Test

```
User: "Run a full test for ABB ACS580 VFD"

Claude: I'll run a complete end-to-end test for the ABB ACS580.

<uses test runner workflow>

🧪 E2E Test Results: ABB ACS580

Overall: ✅ PASS

Steps:
1. ✅ OCR Extraction (2.3s) - Score: 9.1/10
   - Manufacturer: ABB ✓
   - Model: ACS580 ✓
   - Type: VFD ✓

2. ✅ CMMS Search (0.5s)
   - Found in database ✓

3. ✅ Manual Search (9.6s)
   - Quick search: Found PDF ✓
   - Score: 8.7/10 ✓

Total Time: 12.3s
Verdict: PASS

All systems working correctly for ABB ACS580. The Manual Hunter successfully:
- Extracted nameplate data with 91% confidence
- Found equipment in CMMS
- Retrieved high-quality manual (8.7/10)

Ready for production use!
```

### Best Practices

When Claude triggers tests:

1. **Always show results to user**
   ```
   ❌ Bad: "Test completed successfully"
   ✅ Good: "✅ Test PASS - Score: 8.5/10, Duration: 2.3s"
   ```

2. **Explain what was tested**
   ```
   ❌ Bad: "URL validator returned success"
   ✅ Good: "Validated URL accessibility (200 OK), format (PDF), size (2.3MB)"
   ```

3. **Suggest next steps**
   ```
   ✅ "Test passed! Would you like me to:
      1. Run LLM judge to score quality?
      2. Add to manual database?
      3. Run full end-to-end test?"
   ```

4. **Handle failures gracefully**
   ```
   ❌ Bad: "Test failed"
   ✅ Good: "⚠️ URL validation failed (404 Not Found). Possible fixes:
      - Check if URL is correct
      - Try alternative search
      - Manual might be behind paywall"
   ```

5. **Use emojis sparingly**
   - ✅ Status indicators (✓, ✗, ⚠️)
   - 📊 Metrics/scores
   - 🧪 Test results
   - ❌ Don't overuse or use decorative emojis

---

## Troubleshooting

### Error: "Connection timeout"

**Symptom**: Request takes >30s and fails

**Causes**:
- Webhook is processing large file
- External API is slow
- n8n instance is overloaded

**Solutions**:
```bash
# Increase timeout in .env
N8N_WEBHOOK_TIMEOUT=60

# Or set for single test
python scripts/test_client.py validate-url "..." --timeout 60
```

### Error: "Webhook not found (404)"

**Symptom**: `404 Not Found` when calling webhook

**Causes**:
- Test workflow not deployed in n8n
- Wrong webhook URL
- Workflow is deactivated

**Solutions**:
1. Check n8n instance:
   ```
   Claude: "List my n8n workflows"
   ```
2. Verify webhook exists:
   - Open n8n: https://mikecranesync.app.n8n.cloud
   - Find workflow: RIVET-URL-Validator
   - Check webhook path: /webhook/rivet-url-validator
3. Activate workflow:
   ```
   Claude: "Activate the URL validator workflow"
   ```

### Error: "Invalid API key"

**Symptom**: `401 Unauthorized` or `403 Forbidden`

**Causes**:
- API key expired
- Wrong API key
- API key not activated

**Solutions**:
1. Regenerate API key in n8n:
   - Settings → API → Generate New Key
2. Update `.mcp.json`:
   ```powershell
   .\scripts\setup_mcp.ps1
   ```
3. Restart Claude Code CLI

### Error: "N8N_WEBHOOK_BASE_URL not set"

**Symptom**: Python client fails immediately

**Causes**:
- Missing environment variable
- Wrong .env file location

**Solutions**:
```bash
# Check .env exists
ls -la .env

# Verify variable is set
cat .env | grep N8N_WEBHOOK_BASE_URL

# Add if missing
echo "N8N_WEBHOOK_BASE_URL=https://mikecranesync.app.n8n.cloud" >> .env

# Reload environment
source .env  # (Linux/Mac)
```

### Error: "Test failed but no error message"

**Symptom**: `success: false` but no details

**Causes**:
- Workflow returned unexpected format
- Workflow threw exception but didn't log
- Network issue mid-request

**Solutions**:
1. Check n8n execution history:
   ```
   Claude: "Show recent test runs for URL validator"
   ```
2. Enable verbose mode (if supported):
   ```json
   {
     "url": "...",
     "options": {
       "verbose": true
     }
   }
   ```
3. Check n8n logs manually

### Error: "JSON decode error"

**Symptom**: `Invalid JSON in manual_test.json`

**Causes**:
- Malformed JSON file
- Wrong file encoding
- Missing quotes/commas

**Solutions**:
```bash
# Validate JSON
python -m json.tool manual_test.json

# Fix formatting
cat manual_test.json | jq '.' > manual_test_fixed.json
```

### Slow Response Times

**Symptom**: Tests take longer than expected

**Benchmarks**:
| Test Type | Expected | Acceptable | Too Slow |
|-----------|----------|------------|----------|
| URL Validator | 1-3s | 3-5s | >5s |
| LLM Judge | 5-10s | 10-20s | >20s |
| Test Runner (E2E) | 10-30s | 30-60s | >60s |

**Solutions**:
1. Check n8n instance health (cloud status)
2. Verify external APIs are responding (Tavily, Gemini)
3. Check network latency (ping n8n instance)
4. Consider upgrading n8n plan (rate limits)

---

## Advanced Usage

### Batch Testing

Test multiple URLs from CSV:

```bash
# Create CSV
cat > urls.csv << 'EOF'
url,equipment_type,manufacturer
https://example.com/manual1.pdf,motor,siemens
https://example.com/manual2.pdf,plc,abb
https://example.com/manual3.pdf,vfd,schneider
EOF

# Batch test (bash script)
while IFS=, read -r url type mfg; do
  echo "Testing: $url"
  python scripts/test_client.py validate-url "$url" \
    --equipment-type "$type" \
    --manufacturer "$mfg" \
    --json-output >> results.jsonl
done < urls.csv

# Analyze results
cat results.jsonl | jq '.response.score' | awk '{sum+=$1} END {print sum/NR}'
```

### CI/CD Integration

GitHub Actions example:

```yaml
name: RIVET Manual Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run URL validator tests
        env:
          N8N_WEBHOOK_BASE_URL: ${{ secrets.N8N_WEBHOOK_BASE_URL }}
        run: |
          python scripts/test_client.py validate-url "https://example.com/manual.pdf" --json-output > result.json
          cat result.json | jq '.success' | grep -q true
```

### Custom Test Workflows

Create your own test workflows in n8n:

1. Use Webhook trigger node
2. Add test logic (HTTP requests, code nodes, etc)
3. Return structured JSON:
   ```json
   {
     "success": true/false,
     "score": 0-10,
     "details": {...}
   }
   ```
4. Call from Python client:
   ```python
   result = _call_webhook("/webhook/my-custom-test", payload)
   ```

---

## FAQ

**Q: Can I run tests without n8n?**
A: No. All test logic lives in n8n workflows. The Python client is just a thin wrapper.

**Q: How do I add a new test workflow?**
A: Agent 1 creates workflows in n8n. Agent 2 (this client) just calls them. Contact Agent 1 or use n8n-MCP tools.

**Q: Can I test locally?**
A: Yes, but you need a local n8n instance. Update `.env`:
```bash
N8N_WEBHOOK_BASE_URL=http://localhost:5678
```

**Q: What's the difference between MCP and Python client?**
A: MCP integrates with Claude for interactive use. Python client is for automation/scripts.

**Q: How do I debug a failed test?**
A: Check n8n execution history (via MCP or n8n UI). Look for error messages, check logs.

**Q: Can I modify test workflows?**
A: Yes, via n8n-MCP tools:
```
Claude: "Update the URL validator workflow to check file size"
```

**Q: Are tests persistent?**
A: Yes, workflows persist in n8n. Tests can be triggered anytime.

**Q: What happens if n8n is down?**
A: Tests will fail with connection error. Check n8n cloud status.

---

## Next Steps

1. **Run your first test**:
   ```bash
   python scripts/test_client.py validate-url "https://google.com"
   ```

2. **Integrate with Claude**:
   ```
   Ask Claude: "List my n8n workflows"
   ```

3. **Create test cases**:
   ```bash
   mkdir tests/fixtures
   # Add JSON test payloads
   ```

4. **Add to CI/CD**:
   - Create GitHub Actions workflow
   - Run tests on every commit
   - Block merges if tests fail

5. **Monitor tests**:
   - Set up alerting (webhook failures)
   - Track success rates
   - Monitor response times

---

## Support

**Issues**: https://github.com/anthropics/claude-code/issues
**Documentation**: This file
**n8n Docs**: https://docs.n8n.io

**Version History**:
- 1.0.0 (2026-01-09): Initial release
