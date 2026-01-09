# AGENT 1: N8N WORKFLOW LOGIC

**Priority:** #1 - All logic MUST be codified in n8n workflows before anything else

---

## YOUR MISSION

Codeify ALL testing and debugging logic into n8n workflows. These workflows are the source of truth - they persist even if Claude forgets everything.

**Every piece of logic MUST exist as an n8n workflow before we integrate with Claude.**

---

## INFRASTRUCTURE

```
n8n Cloud: [ASK MIKE FOR URL]
n8n API Key: [ASK MIKE]
Database: Neon PostgreSQL  
Telegram Bot: @rivet_local_dev_bot (token: 8161680636)
```

---

## WORKFLOWS TO BUILD

### 1. RIVET Test Orchestrator
**Purpose:** Execute any workflow and capture full execution data
**Trigger:** MCP Server Trigger at `/mcp/rivet-test-orchestrator`

```
[MCP Server Trigger] 
    ↓
[Parse Request] - Extract workflowId, testData, testMode
    ↓
[Execute Workflow] - Run the target workflow
    ↓
[Get Execution Details] - Fetch full execution data from n8n API
    ↓
[Format Results] - Structure for Claude consumption:
    - Each node's input/output
    - Errors with stack traces
    - Timing per node
    - Overall success/failure
    ↓
[Log to Database] - Insert into test_executions table
    ↓
[Return Results] - Respond to MCP client
```

**Key Code Node (Format Results):**
```javascript
const execution = $input.first().json;
const runData = execution.data?.resultData?.runData || {};

const results = {
  success: execution.finished,
  workflowId: execution.workflowId,
  executionId: execution.id,
  duration: new Date(execution.stoppedAt) - new Date(execution.startedAt),
  nodes: Object.entries(runData).map(([name, runs]) => ({
    name,
    success: !runs[0]?.error,
    output: runs[0]?.data?.main?.[0] || null,
    error: runs[0]?.error?.message || null,
    executionTime: runs[0]?.executionTime
  })),
  errors: Object.entries(runData)
    .filter(([_, runs]) => runs[0]?.error)
    .map(([name, runs]) => ({
      node: name,
      message: runs[0].error.message,
      stack: runs[0].error.stack
    }))
};

return [{ json: results }];
```

---

### 2. RIVET Node Tester
**Purpose:** Test a single node configuration in isolation
**Trigger:** MCP Server Trigger at `/mcp/rivet-node-tester`

```
[MCP Server Trigger]
    ↓
[Parse Node Config] - nodeType, config, testInput
    ↓
[Build Temp Workflow] - Create minimal workflow with just this node
    ↓
[Create via API] - POST to n8n API /workflows
    ↓
[Execute] - Trigger the temp workflow
    ↓
[Get Results] - Fetch execution data
    ↓
[Delete Temp Workflow] - Cleanup
    ↓
[Return Results]
```

---

### 3. RIVET Error Analyzer
**Purpose:** AI-powered error analysis and fix suggestions
**Trigger:** MCP Server Trigger at `/mcp/rivet-error-analyzer`

```
[MCP Server Trigger]
    ↓
[Get Execution] - Fetch failed execution details
    ↓
[Extract Errors] - Parse error messages and context
    ↓
[Check KB] - Query error_patterns table for known fixes
    ↓
[IF Known Fix]
    │
    ├── [Return Cached Fix]
    │
    └── [AI Analysis] - Use Gemini/Groq to analyze
            ↓
        [Cache New Fix] - Store in error_patterns
            ↓
        [Return Analysis]
```

---

## DATABASE SCHEMA

Create these tables in Neon:

```sql
-- Test execution history
CREATE TABLE IF NOT EXISTS test_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id VARCHAR(255) NOT NULL,
    workflow_name VARCHAR(500),
    execution_id VARCHAR(255),
    success BOOLEAN,
    duration_ms INTEGER,
    node_count INTEGER,
    error_count INTEGER,
    test_input JSONB,
    results_json JSONB,
    triggered_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Error knowledge base
CREATE TABLE IF NOT EXISTS error_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type VARCHAR(255),
    error_pattern TEXT,
    error_hash VARCHAR(64),
    root_cause TEXT,
    fix_description TEXT,
    fix_code JSONB,
    times_seen INTEGER DEFAULT 1,
    times_fixed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_test_executions_workflow 
    ON test_executions(workflow_id);
CREATE INDEX IF NOT EXISTS idx_error_patterns_hash 
    ON error_patterns(error_hash);
```

---

## OUTPUT FILES

Save workflows to:
```
n8n/workflows/testing/
├── test_orchestrator.json
├── node_tester.json
├── error_analyzer.json
└── README.md
```

---

## COMPLETION SIGNAL

When done, create `AGENT1_COMPLETE.md` with:
- Workflow IDs deployed to n8n Cloud
- MCP endpoint URLs
- Database tables created
- Test results showing they work

---

## CONSTRAINTS

1. **n8n workflows FIRST** - No Python/JS unless it's inside a Code node
2. **Use native n8n nodes** where possible
3. **All workflows must have error handling**
4. **Log everything to database**
5. **MCP Server Trigger on all workflows** for Claude integration

---

## START HERE

1. Ask Mike for n8n Cloud URL and API key
2. Create database tables
3. Build Test Orchestrator first (it's the foundation)
4. Test with ABB fixture from `fixtures/abb_test_case.py`
5. Deploy and verify MCP endpoint works
