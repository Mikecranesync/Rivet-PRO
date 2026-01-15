# RIVET Pro - Quick Context

> Read this file at the start of any new session for instant context restoration.

## What This Is

**Atlas CMMS** extracted from Agent Factory into a standalone product.
- Telegram bot interface for equipment technicians
- PostgreSQL database on Neon
- AI-powered equipment identification via photo OCR

## Current State (2026-01-15)

| Item | Status |
|------|--------|
| Branch | `main` (clean, production-ready) |
| Feature flags | Stable/experimental split done (STABLE-001 to STABLE-013) |
| Repository | Cleaned up - 137 files archived locally |
| Memory system | Implemented - MCP memory + file-based |
| AUTO-KB System | **COMPLETE** - All 11 stories done (AUTO-KB-003 to AUTO-KB-013) |
| Backlog.md tasks | task-13 to task-24 (all Done) |

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

1. **Run migrations** - Apply 019_query_patterns.sql and 020_catalog_scraper.sql to Neon
2. **Test enrichment worker** - Run `python -m rivet_pro.workers.enrichment_worker`
3. **Deploy worker** - Set up systemd service on Linux server
4. Continue CMMS extraction from Agent Factory
5. Implement remaining bot commands (`/equip`, `/wo`)
6. Wire up OCR pipeline for nameplate photos

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
