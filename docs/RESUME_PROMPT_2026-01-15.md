# Session Resume Prompt - 2026-01-15

## Quick Context Restoration

Copy this to start a new session:

```
Read the memory graph for RIVET project status, then continue Phase 3 verification or move to next phase.

Key files to read for context:
- docs/RESUME_PROMPT_2026-01-15.md (this file)
- backlog/Backlog.md (current task status)
- scripts/ralph/ralph_api.py (Ralph Wiggum autonomous agent)
```

---

## Project Status Summary

### Completed Phases

| Phase | Status | Tasks Done |
|-------|--------|------------|
| Phase 1: Foundation | Partial | 3/12 (Auth incomplete) |
| Phase 2: Troubleshooting | **COMPLETE** | 9/9 |
| Phase 3: Pipeline Agents | **COMPLETE** | 8/8 |

### Phase 3 Deliverables (Just Completed)

All 12 PIPE-* stories implemented:

| Story | File Created | Purpose |
|-------|--------------|---------|
| PIPE-001 | `rivet_pro/migrations/024_workflow_history.sql` | Pipeline state table |
| PIPE-002 | `rivet_pro/core/services/workflow_state_machine.py` | State machine class |
| PIPE-003 | `rivet_pro/core/services/llm_manager.py` | Claude→GPT-4→Cache failover |
| PIPE-004 | `rivet_pro/core/services/resilient_telegram_manager.py` | Message queue |
| PIPE-005-009 | `rivet_pro/adapters/web/routers/pipeline.py` | REST API endpoints |
| PIPE-007 | `rivet_pro/core/services/agent_executor.py` | SME agent routing |
| PIPE-010 | `rivet_pro/adapters/telegram/bot.py` (modified) | Approval buttons |
| PIPE-012 | `rivet_pro/workers/backlog_generator.py` | Auto-generate backlog |

### Git Status

- **Branch**: main
- **Latest Commits**:
  - `fb5b78e` - feat(phase3): Implement Pipeline Agents infrastructure
  - `13ff139` - docs(backlog): Mark Phase 3 Pipeline tasks as Done
- **Pushed**: Yes, to origin/main

---

## Ralph Wiggum Process

The autonomous development agent is at `scripts/ralph/ralph_api.py`.

### How to Use Ralph

1. **Insert stories into database**:
```sql
INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, priority, status)
VALUES (1, 'PREFIX-001', 'Title', 'Description', '["AC1", "AC2"]', 1, 'todo');
```

2. **Run Ralph**:
```bash
python scripts/ralph/ralph_api.py --prefix PREFIX --max 10 --model claude-sonnet-4-20250514
```

3. **Monitor progress**: Ralph logs to console and updates `ralph_stories.status` in database

### Recent Issue Fixed

Windows encoding error with emoji characters was fixed by adding to ralph_api.py:
```python
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
```

---

## Next Recommended Tasks

### Option 1: Phase 4 Analytics (task-11)
- Usage metrics dashboard
- Admin interface
- 6 subtasks

### Option 2: Complete Phase 1 Auth (task-8.1-8.3)
- Telegram Login Widget
- HMAC-SHA-256 verification
- 24-hour auth expiry

### Option 3: Integration Testing
- Verify Phase 3 components work end-to-end
- Test pipeline orchestration
- Test LLM failover chain

---

## Database Connection

```bash
# Neon PostgreSQL
DATABASE_URL from .env file
Project: ep-purple-hall-ahimeyn0

# Key tables
- ralph_stories (Ralph work items)
- pipeline_execution_history (Phase 3 state machine)
- users, equipment, work_orders (CMMS core)
```

---

## Architecture Overview

```
rivet_pro/
├── adapters/
│   ├── telegram/bot.py         # Telegram interface
│   └── web/routers/
│       └── pipeline.py         # REST API (NEW)
├── core/services/
│   ├── workflow_state_machine.py  # State machine (NEW)
│   ├── llm_manager.py             # LLM failover (NEW)
│   ├── resilient_telegram_manager.py  # Message queue (NEW)
│   └── agent_executor.py          # SME routing (NEW)
├── workers/
│   └── backlog_generator.py       # Auto-backlog (NEW)
└── migrations/
    └── 024_workflow_history.sql   # Pipeline table (NEW)
```

---

## Memory Graph Entities

Query these for context:
- `RIVET-Pro` - Main project entity
- `Phase3-PipelineAgents` - Phase 3 details
- `PipelineOrchestrator` - Pipeline REST API
- `MultiProviderLLMManager` - LLM failover
- `ResilientTelegramManager` - Message queue
- `AgentExecutor` - SME routing
- `BacklogGenerator` - Auto-backlog worker

---

## Session End State

- All Phase 3 tasks marked Done in backlog
- All 12 PIPE-* stories marked done in ralph_stories
- Code committed and pushed to GitHub
- Memory graph updated with new entities
- This resume prompt created

**Ready for**: Phase 4, Auth completion, or integration testing
