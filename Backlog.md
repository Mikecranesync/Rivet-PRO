# RIVET Pro Backlog

> Auto-generated: 2026-01-15 | Updated: Phase 2 Complete

## Summary

| Status | Count |
|--------|-------|
| Done | 29 |
| To Do | 55 |
| **Total** | **84** |

## Ralph Stories: 75/75 DONE (100%)

All Ralph stories complete! No pending stories in database.

---

## Backlog Tasks by Phase

### DONE - PART 1: Stability Foundation
- [x] task-1: Stability Foundation (epic)
- [x] task-1.1: Create stabilize-rivet.sh script
- [x] task-1.2: Enable GitHub branch protection
- [x] task-1.3: Add startup endpoint validation

### DONE - AUTO-KB: Autonomous Knowledge Base (12 tasks)
- [x] task-13 through task-24: All AUTO-KB stories complete

### PARTIAL - PART 2: Database Failover
- [x] task-2.4: Add /health endpoint
- [ ] task-2: Database Failover (epic) - **Already implemented via Railway**
- [ ] task-2.1: Create Turso database (skip - using Railway instead)
- [ ] task-2.2: Sync Neon data to Turso
- [ ] task-2.3: Implement MultiDatabaseManager
- [ ] task-2.5: Test failover end-to-end

### PARTIAL - PHASE 1: Foundation (task-8)
- [x] task-8.4: User record created/updated on login
- [x] task-8.5: JWT session token with 7-day expiry
- [x] task-8.6: Telegram ID as universal FK
- [ ] task-8.1: Telegram Login Widget renders on login page
- [ ] task-8.2: Backend verifies HMAC-SHA-256 hash
- [ ] task-8.3: Auth data older than 24 hours rejected
- [ ] task-8.7: Schema deploys to Neon PostgreSQL
- [ ] task-8.8: Branch creation via API < 2 seconds
- [ ] task-8.9: Preview branches auto-expire 7 days
- [ ] task-8.10: RLS policies enforce org isolation
- [ ] task-8.11: Pooled connections handle 1000 users
- [ ] task-8.12: Tree traversal queries < 50ms

### DONE - PHASE 2: Troubleshooting Core (task-9) ✅
- [x] task-9.1: Mermaid diagrams parse to nodes/edges (`mermaid_parser.py`)
- [x] task-9.2: Inline keyboard max 8 buttons per row (`keyboard.py`)
- [x] task-9.3: callback_data within 64-byte limit (`callback.py`)
- [x] task-9.4: Messages edit in-place, no new messages (`navigator.py`)
- [x] task-9.5: Images/media display with captions (`media_display.py`)
- [x] task-9.6: Safety warnings in blockquote format (`formatting.py`)
- [x] task-9.7: Back navigation returns to previous step (`history.py`)
- [x] task-9.8: Claude fallback for unknown equipment (`fallback.py`)
- [x] task-9.9: Save this guide creates tree draft (`drafts.py`)

### TODO - PHASE 3: Pipeline Agents (task-10)
- [ ] task-10.1 through task-10.8: Pipeline orchestration

### TODO - PHASE 4: Analytics & Admin (task-11)
- [ ] task-11.1 through task-11.6: Usage analytics

### TODO - PHASE 5: Polish & Scale (task-12)
- [ ] task-12.1 through task-12.5: Diagram exports

---

## Next Steps (Recommended Priority)

### 1. Start PHASE 3: Pipeline Agents (task-10)
Phase 2 complete! Begin pipeline orchestration for multi-agent workflows.

### 2. Complete PHASE 1 Foundation (task-8)
**Remaining auth tasks:**
- task-8.1: Telegram Login Widget (frontend)
- task-8.2: HMAC-SHA-256 verification (backend)
- task-8.3: 24-hour auth expiry check

**Database tasks (mostly done via Neon):**
- task-8.7: Already deployed to Neon
- task-8.8-8.12: Performance/security optimizations

### 3. Mark Completed Items
Several task-2 subtasks are already implemented:
- Database failover exists (Neon → Railway → Supabase)
- /health endpoint done
- Consider marking task-2 epic as Done

---

## DevOps Status (All DONE)

| Component | Status |
|-----------|--------|
| Neon MCP Server | Configured |
| Neon API Key | In .env + GitHub secrets |
| GitHub PR Branching | Workflows ready |
| n8n Health Monitor | Workflow exists (needs credentials) |
| n8n Auto-Wake | Webhook exists (needs activation) |
| Langfuse Tracing | Implemented |
| Database Failover | Neon → Railway → Supabase |
| CodeRabbit | Configured |

---

## Phase 2 Completion Details (2026-01-15)

All 9 troubleshooting core modules implemented in `rivet_pro/troubleshooting/`:

| Module | Purpose | Lines |
|--------|---------|-------|
| `mermaid_parser.py` | Parse Mermaid flowchart to tree structure | ~150 |
| `keyboard.py` | Build Telegram inline keyboards | ~100 |
| `callback.py` | Compress callback_data under 64 bytes | ~80 |
| `navigator.py` | In-place message editing during navigation | ~120 |
| `media_display.py` | Display images with captions | ~90 |
| `formatting.py` | Safety warning blockquote formatting | ~60 |
| `history.py` | Back navigation stack per user | ~70 |
| `fallback.py` | Claude API fallback for unknown equipment | ~130 |
| `drafts.py` | Save Claude guides as tree drafts | ~140 |

**Also created:**
- Database migration: `023_troubleshooting_tree_drafts.sql`
- Tests: `test_formatting.py`, `test_navigator.py`, `test_drafts.py`, `test_history.py`
- Examples: `example_integration.py`, `example_navigator.py`
