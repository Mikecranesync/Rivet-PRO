# RIVET Pro - Quick Context

> Read this file at the start of any new session for instant context restoration.

## What This Is

**Atlas CMMS** extracted from Agent Factory into a standalone product.
- Telegram bot interface for equipment technicians
- PostgreSQL database on Neon
- AI-powered equipment identification via photo OCR

## Current State (2026-01-14)

| Item | Status |
|------|--------|
| Branch | `main` (clean, production-ready) |
| Feature flags | Stable/experimental split done (STABLE-001 to STABLE-013) |
| Repository | Cleaned up - 137 files archived locally |
| Memory system | Implemented - MCP memory + file-based |

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

## Recent Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-14 | Archive folder kept local | Contains API keys/secrets |
| 2026-01-14 | Trunk-based development | Protected main branch with PR workflow |
| 2026-01-14 | Feature flags for experiments | Safe rollout of new features |
| 2026-01-14 | MCP memory for context | Survives context window clears |

## What's Next

1. Continue CMMS extraction from Agent Factory
2. Implement remaining bot commands (`/equip`, `/wo`)
3. Wire up OCR pipeline for nameplate photos

## Memory System

- **MCP Memory**: Query with `mcp__memory__search_nodes("RIVET")`
- **Session log**: `docs/SESSION_LOG.md`
- **Full context**: `CLAUDE.md`
