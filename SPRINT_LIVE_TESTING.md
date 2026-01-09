# SPRINT: RIVET Live Testing Infrastructure

**Started:** 2026-01-09
**Goal:** Claude can test workflows and see results without manual intervention
**Priority:** n8n workflow logic FIRST (persists), then Claude integration

---

## THE PROBLEM WE'RE SOLVING

**BEFORE (painful):**
```
You take photo → Import workflow → Click test → Check each node → Report to Claude → Repeat
```

**AFTER (automated):**
```
Claude builds workflow → Auto-tests with ABB fixture → Sees all results → Fixes itself → You approve
```

---

## 3-AGENT SPRINT ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT 1: N8N WORKFLOWS                        │
│                    (Priority #1 - Logic Persists)                │
│                                                                  │
│  Builds:                                                         │
│  • Test Orchestrator - Execute any workflow, capture results     │
│  • Node Tester - Test single node in isolation                   │
│  • Execution Monitor - Watch progress in real-time               │
│  • Error Analyzer - AI-powered fix suggestions                   │
│                                                                  │
│  Output: n8n workflow JSON files + database schema               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT 2: MCP INTEGRATION                      │
│                    (Connects Claude to n8n)                      │
│                                                                  │
│  Builds:                                                         │
│  • MCP config for Claude Code CLI                                │
│  • System instructions for testing protocol                      │
│  • Setup scripts and validation tools                            │
│                                                                  │
│  Output: mcp.json + CLAUDE_INSTRUCTIONS.md                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT 3: DEBUG HARNESS                        │
│                    (Test Fixtures & Utilities)                   │
│                                                                  │
│  Builds:                                                         │
│  • ABB test fixtures (already done! ✅)                          │
│  • Debug CLI tool                                                │
│  • Telegram debug console workflow                               │
│  • Performance benchmarks                                        │
│  • Test report generator                                         │
│                                                                  │
│  Output: fixtures/ + scripts/ + debug tools                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## WORKTREE SETUP

```bash
# Navigate to your repo
cd C:\Users\hharp\Documents\GitHub\Rivet-PRO

# Create 3 worktrees for parallel development
git worktree add ../rivet-agent1-workflows feature/live-testing-workflows
git worktree add ../rivet-agent2-mcp feature/mcp-test-integration  
git worktree add ../rivet-agent3-harness feature/debug-harness

# Verify
git worktree list
```

---

## AGENT STATUS

| Agent | Branch | Focus | Status |
|-------|--------|-------|--------|
| 1 | feature/live-testing-workflows | n8n Workflows | 🟡 Ready to start |
| 2 | feature/mcp-test-integration | MCP Config | 🟡 Waiting on Agent 1 |
| 3 | feature/debug-harness | Debug Tools | ✅ Fixtures done |

---

## QUICK TEST (Right Now)

```bash
# Set your n8n Cloud URL
export N8N_CLOUD_URL="https://your-instance.app.n8n.cloud"

# Run the ABB test
./scripts/test_abb_pipeline.sh
```

Or PowerShell:
```powershell
$env:N8N_CLOUD_URL = "https://your-instance.app.n8n.cloud"
.\scripts\test_abb_pipeline.ps1
```

---

## THE ABB TEST CASE

The ABB ACS580 VFD that started RIVET Pro is now codified in `fixtures/abb_test_case.py`.

**This is the golden test case.** If it fails, something is broken.

```python
from fixtures import get_abb_test_payload, validate_result

# Get the test data
payload = get_abb_test_payload()
# {'manufacturer': 'ABB', 'model_number': 'ACS580-01-12A5-4', ...}

# After calling Manual Hunter, validate results
result = validate_result(response, ORIGINAL_ABB_TEST["expected"])
if result["passed"]:
    print("✅ ABB test passed!")
```

---

## WHAT'S NEEDED FROM YOU (MIKE)

1. **n8n Cloud URL** - What's your instance URL?
2. **n8n Cloud API Key** - For Claude to manage workflows
3. **Run the test script** to verify current state

---

## MERGE ORDER

1. Agent 3 fixtures → main (already merged!)
2. Agent 1 workflows → main
3. Agent 2 MCP config → main

---

## FILES CREATED IN THIS SPRINT

```
fixtures/
├── __init__.py              # Package exports
└── abb_test_case.py         # ABB ACS580 golden test case

scripts/
├── test_abb_pipeline.sh     # Bash test script
└── test_abb_pipeline.ps1    # PowerShell test script

SPRINT_LIVE_TESTING.md       # This file
```

---

## NEXT STEPS

1. ✅ Create ABB test fixture (DONE)
2. ✅ Create test scripts (DONE)
3. ⬜ Get n8n Cloud URL from Mike
4. ⬜ Run test to verify Manual Hunter status
5. ⬜ Agent 1: Build Test Orchestrator workflow
6. ⬜ Agent 2: Configure MCP for Claude
7. ⬜ Agent 3: Build debug CLI and Telegram console
