# Resume Prompt - 2026-01-16

Copy and paste this to resume the session:

---

## Context

I'm working on **RIVET Pro**, a Telegram bot for industrial equipment technicians. Read `docs/QUICK_CONTEXT.md` for full context.

## Current Status: Phase 4 SME Chat COMPLETE

**PR**: https://github.com/Mikecranesync/Rivet-PRO/pull/8
**Branch**: `ralph/sme-chat-phase4`
**Status**: User testing PASSED - Ready to merge to main

### What Was Built

Phase 4 adds conversational chat with vendor-specific SME agents:
- **7 SME Personalities**: Hans (Siemens), Mike (Rockwell), Erik (ABB), Pierre (Schneider), Takeshi (Mitsubishi), Ken (Fanuc), Alex (Generic)
- **RAG-Enhanced Responses**: Knowledge base context filtered by manufacturer
- **Confidence-Based Routing**:
  - HIGH (>=0.85): Direct KB answer with SME voice styling
  - MEDIUM (0.70-0.85): Full SME synthesis from RAG context
  - LOW (<0.70): Clarifying questions to gather more info
- **Telegram Commands**: `/chat [vendor]` to start, `/endchat` to close
- **Telegram Menu**: All commands now appear in bot menu button
- **Safety Warning Extraction**: Flags voltage, LOTO, arc flash hazards
- **Multi-Turn Conversation**: Session preserves context across messages

### Key Commits
- `08beec7` - SME-CHAT-001: Database migration
- `f8ceb8e` - SME-CHAT-002: Pydantic models
- `213b99c` - SME-CHAT-003: SME personalities
- `b383c71` - SME-CHAT-004: RAG service
- `f365592` - SME-CHAT-005: Chat service core
- `d8324cb` - SME-CHAT-006: Telegram /chat command
- `fdd77de` - SME-CHAT-007: Message routing
- `2aefbde` - SME-CHAT-008: Confidence routing
- `8910f51` - SME-CHAT-009: Unit tests (38)
- `b119989` - SME-CHAT-010: Integration tests (12)
- `da1416c` - Production bot integration
- `fd896b4` - Fix callback handler bug

### Testing Results
- 50 automated tests passing (38 unit + 12 integration)
- Manual user testing PASSED:
  - [x] `/chat siemens` - Hans personality works
  - [x] Vendor picker shows when no vendor specified
  - [x] Multi-turn conversation preserves context
  - [x] Safety warnings appear for hazardous topics
  - [x] `/endchat` closes session properly

## What's Next

### Merge PR #8 to main
```bash
git checkout main
git pull
git merge ralph/sme-chat-phase4
git push

# Redeploy to VPS (uses systemd now)
ssh root@72.60.175.144 "cd /opt/Rivet-PRO && git checkout main && git pull && systemctl restart rivet-bot"
```

### After Merge
1. **Phase 5: Analytics & Admin** (task-11) - Usage metrics dashboard
2. **Complete Phase 1 Auth** (task-8.1-8.3) - Telegram Login Widget

## VPS Info

Bot runs via systemd service on `72.60.175.144`:
```bash
# Check status
ssh root@72.60.175.144 "systemctl status rivet-bot"

# View logs
ssh root@72.60.175.144 "journalctl -u rivet-bot -n 50 --no-pager"

# Restart
ssh root@72.60.175.144 "systemctl restart rivet-bot"
```

## MCP Memory

Query for context:
- `mcp__memory__search_nodes("SME_Chat_Phase4")`
- `mcp__memory__search_nodes("RIVET")`

## Bugs Fixed During Development

1. **Pydantic use_enum_values=True** - Enum fields stored as strings, not enum objects. Don't call `.value` on them.
2. **asyncpg JSONB** - Requires `json.dumps()` for INSERT with `::jsonb` cast, and parsing (string vs dict) on SELECT.
3. **Callback handler update.message is None** - Use `update.effective_message` for code that handles both commands and inline keyboard callbacks.

---

*Last updated: 2026-01-16 - Testing complete, ready to merge*
