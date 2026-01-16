# RIVET Pro - Quick Context

> Read this file at the start of any new session for instant context restoration.

## What This Is

**Atlas CMMS** extracted from Agent Factory into a standalone product.
- Telegram bot interface for equipment technicians
- PostgreSQL database on Neon
- AI-powered equipment identification via photo OCR

## Current State (2026-01-16)

| Item | Status |
|------|--------|
| Branch | `main` (clean, production-ready) |
| Phase 1: Foundation | Partial (3/12 - Auth incomplete) |
| Phase 2: Troubleshooting | **COMPLETE** (9/9) |
| Phase 3: Pipeline Agents | **COMPLETE** (8/8) |
| AUTO-KB System | **COMPLETE** - All 11 stories done |
| Search Transparency | **COMPLETE** - Human-in-the-loop validation |
| Latest commit | `7e93be9` - Windows UTF-8 encoding fix |

## Key Commands

```bash
# Run the bot
python -m rivet_pro.adapters.telegram

# Run tests
pytest tests/

# Test search transparency
python scripts/test_search_transparency.py --python-only --limit 3

# Start Ralph (autonomous development)
python scripts/ralph/ralph_local.py --max 5

# Query Ralph stories
psql $DATABASE_URL -c "SELECT story_id, title, status FROM ralph_stories ORDER BY priority"
```

## Key Files

| Purpose | File |
|---------|------|
| Bot main | `rivet_pro/adapters/telegram/bot.py` |
| Manual service | `rivet_pro/core/services/manual_service.py` |
| Search report model | `rivet_pro/core/models/search_report.py` |
| Response formatter | `rivet_pro/core/utils/response_formatter.py` |
| Windows encoding fix | `rivet_pro/core/utils/encoding.py` |
| Feature flags | `rivet_pro/config/feature_flags.json` |
| Flag manager | `rivet_pro/core/feature_flags.py` |
| Test script | `scripts/test_search_transparency.py` |

## Search Transparency Feature (NEW)

When manual search fails, the bot now:
1. **Shows transparency report**: What was searched and why each URL was rejected
2. **Human-in-the-loop**: If candidate URL has ≥50% confidence, asks user "Is this correct?"
3. **Learns from feedback**: User's Yes/No response cached for future searches

### LLM Cascade (optimized for speed/cost)
1. **Groq** (llama-3.3-70b-versatile) - Free, fastest
2. **DeepSeek** (deepseek-chat) - Cheap fallback
3. **Claude** (claude-sonnet-4-20250514) - Expensive, best quality

### Key Changes
- `SearchReport.best_candidate` - Returns highest confidence rejected URL
- `_handle_manual_validation_reply()` - Handles Yes/No responses
- Migration `025_manual_feedback.sql` - Tracks user validations

## Recent Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-16 | 50% threshold for human-in-loop | Cast wider net to gather feedback |
| 2026-01-16 | Groq → DeepSeek → Claude order | Speed/cost optimization |
| 2026-01-16 | Windows UTF-8 encoding fix | cp1252 can't display emojis |
| 2026-01-14 | Archive folder kept local | Contains API keys/secrets |
| 2026-01-14 | Trunk-based development | Protected main branch with PR workflow |

## What's Next

1. **Test human-in-the-loop** - Send photos to @testbotrivet_bot, reply Yes/No
2. **Phase 4: Analytics & Admin** (task-11) - Usage metrics dashboard
3. **Complete Phase 1 Auth** (task-8.1-8.3) - Telegram Login Widget
4. Continue CMMS extraction from Agent Factory
5. Implement remaining bot commands (`/equip`, `/wo`)

## VPS Deployment

```bash
# Deploy to VPS
ssh root@72.60.175.144 "cd /opt/Rivet-PRO && git pull && pkill -f 'python.*telegram'; nohup python3 -m rivet_pro.adapters.telegram > /tmp/bot.log 2>&1 &"

# Check logs
ssh root@72.60.175.144 "tail -50 /tmp/bot.log"
```

## Memory System

- **MCP Memory**: Query with `mcp__memory__search_nodes("SearchTransparency")` or `mcp__memory__search_nodes("HumanInTheLoop")`
- **Session log**: `docs/SESSION_LOG.md`
- **Full context**: `CLAUDE.md`
