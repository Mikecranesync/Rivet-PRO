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
| Branch | `ralph/sme-chat-phase4` (testing complete, ready to merge) |
| Phase 1: Foundation | Partial (3/12 - Auth incomplete) |
| Phase 2: Troubleshooting | **COMPLETE** (9/9) |
| Phase 3: Pipeline Agents | **COMPLETE** (8/8) |
| AUTO-KB System | **COMPLETE** - All 11 stories done |
| Search Transparency | **COMPLETE** - Human-in-the-loop validation |
| **Phase 4: SME Chat** | **TESTED & WORKING** - Ready to merge |
| Latest commit | `fd896b4` - SME Chat production integration complete |

### Phase 4: SME Chat (TESTED)
- **Branch**: `ralph/sme-chat-phase4`
- **PR**: https://github.com/Mikecranesync/Rivet-PRO/pull/8
- **Status**: User testing passed, ready to merge to main
- **Features**: 7 SME personalities, RAG-enhanced responses, confidence-based routing
- **Commands**: `/chat [vendor]` to start, `/endchat` to close
- **Telegram menu**: All commands now appear in bot menu button

### Key Files Added
| File | Purpose |
|------|---------|
| `rivet/models/sme_chat.py` | Pydantic models for sessions/messages |
| `rivet/prompts/sme/personalities.py` | 7 SME personalities (Hans, Mike, Erik, etc.) |
| `rivet/services/sme_rag_service.py` | RAG context retrieval |
| `rivet/services/sme_chat_service.py` | Core chat orchestration |
| `rivet_pro/adapters/telegram/bot.py` | /chat, /endchat commands integrated |
| `tests/unit/test_sme_*.py` | 38 unit tests |
| `tests/integration/test_sme_chat_flow.py` | 12 integration tests |

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

## VPS Deployment

```bash
# Bot runs via systemd service
ssh root@72.60.175.144 "systemctl restart rivet-bot"

# Check status
ssh root@72.60.175.144 "systemctl status rivet-bot"

# Check logs
ssh root@72.60.175.144 "journalctl -u rivet-bot -n 50 --no-pager"

# Deploy new code
ssh root@72.60.175.144 "cd /opt/Rivet-PRO && git pull && systemctl restart rivet-bot"
```

## What's Next

1. **Merge PR #8** - SME Chat testing passed, merge to main
2. **Phase 5: Analytics & Admin** (task-11) - Usage metrics dashboard
3. **Complete Phase 1 Auth** (task-8.1-8.3) - Telegram Login Widget
4. Continue CMMS extraction from Agent Factory

## Memory System

- **MCP Memory**: Query with `mcp__memory__search_nodes("SME_Chat_Phase4")` or `mcp__memory__search_nodes("RIVET")`
- **Session log**: `docs/SESSION_LOG.md`
- **Full context**: `CLAUDE.md`
