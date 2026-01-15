# RIVET Pro - Quick Context

> Read this file at the start of any new session for instant context restoration.

## What This Is

**Atlas CMMS** extracted from Agent Factory into a standalone product.
- Telegram bot interface for equipment technicians
- PostgreSQL database on Neon
- AI-powered equipment identification via photo OCR

## Current State (2026-01-15 Evening)

| Item | Status |
|------|--------|
| Branch | `main` (clean, production-ready) |
| Phase 1: Foundation | Partial (3/12 - Auth incomplete) |
| Phase 2: Troubleshooting | **COMPLETE** (9/9) |
| Phase 3: Pipeline Agents | **COMPLETE** (8/8) |
| AUTO-KB System | **COMPLETE** - All 11 stories done |
| Latest commit | `13ff139` - Phase 3 Pipeline infrastructure |

## Key Commands

```bash
# Run the bot
python -m rivet_pro.adapters.telegram.bot

# Run tests
pytest tests/

# Start Ralph (autonomous development)
python scripts/ralph/ralph_local.py --max 5

# Query Ralph stories
psql $DATABASE_URL -c "SELECT story_id, title, status FROM ralph_stories ORDER BY priority"
```

## Key Files

| Purpose | File |
|---------|------|
| Bot main | `rivet_pro/adapters/telegram/bot.py` |
| Feature flags | `rivet_pro/config/feature_flags.json` |
| Flag manager | `rivet_pro/core/feature_flags.py` |
| Memory storage | `rivet_pro/rivet/memory/storage.py` |
| Ralph runner | `scripts/ralph/ralph_local.py` |
| Branching guide | `docs/BRANCHING_GUIDE.md` |
| **Enrichment worker** | `rivet_pro/workers/enrichment_worker.py` |
| **Manual download** | `rivet_pro/core/services/manual_download_manager.py` |
| **Semantic search** | `rivet_pro/core/services/semantic_search_service.py` |
| **Query patterns** | `rivet_pro/core/services/query_pattern_analyzer.py` |
| **Catalog scraper** | `rivet_pro/core/services/catalog_scraper.py` |
| **Dashboard API** | `rivet_pro/adapters/web/routers/enrichment.py` |

## Recent Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-14 | Archive folder kept local | Contains API keys/secrets |
| 2026-01-14 | Trunk-based development | Protected main branch with PR workflow |
| 2026-01-14 | Feature flags for experiments | Safe rollout of new features |
| 2026-01-14 | MCP memory for context | Survives context window clears |

## What's Next

1. **Phase 4: Analytics & Admin** (task-11) - Usage metrics dashboard
2. **Complete Phase 1 Auth** (task-8.1-8.3) - Telegram Login Widget, HMAC verification
3. **Integration Testing** - Verify Phase 3 pipeline components end-to-end
4. Continue CMMS extraction from Agent Factory
5. Implement remaining bot commands (`/equip`, `/wo`)

## Phase 3 Pipeline Files (NEW)

| Purpose | File |
|---------|------|
| Pipeline API | `rivet_pro/adapters/web/routers/pipeline.py` |
| State machine | `rivet_pro/core/services/workflow_state_machine.py` |
| LLM failover | `rivet_pro/core/services/llm_manager.py` |
| Telegram queue | `rivet_pro/core/services/resilient_telegram_manager.py` |
| Agent routing | `rivet_pro/core/services/agent_executor.py` |
| Backlog worker | `rivet_pro/workers/backlog_generator.py` |
| DB migration | `rivet_pro/migrations/024_workflow_history.sql` |

## AUTO-KB System Summary

The autonomous KB enrichment system is complete:
- **Worker**: Background process polls enrichment_queue every 30s
- **Download**: Concurrent downloads with checksums, retry logic
- **Text extraction**: PyPDF2 extracts text from PDFs
- **Embeddings**: OpenAI or sentence-transformers for semantic search
- **Priority scoring**: QueryPatternAnalyzer adjusts priorities based on user queries
- **Catalog scraping**: Discovers manuals from manufacturer portals
- **Dashboard**: Admin API at `/api/admin/enrichment/*`

Query MCP memory for details: `mcp__memory__search_nodes("AUTO-KB")`

## Memory System

- **MCP Memory**: Query with `mcp__memory__search_nodes("RIVET")` or `mcp__memory__search_nodes("AUTO-KB")`
- **Session log**: `docs/SESSION_LOG.md`
- **Full context**: `CLAUDE.md`
