# Resume Prompt - 2026-01-16

Copy and paste this to resume the session:

---

## Context

I'm working on **RIVET Pro**, a Telegram bot for industrial equipment technicians. Read `docs/QUICK_CONTEXT.md` for full context.

## What Was Just Completed

### Search Transparency & Human-in-the-Loop Validation

When manual search fails but finds potential URLs:
1. **Transparency Report** - Shows search stages and rejected URLs with reasons
2. **Human-in-the-Loop** - If candidate ≥50% confidence, asks "Is this correct?"
3. **Feedback Learning** - User Yes/No cached for future searches

**Key files modified:**
- `rivet_pro/core/models/search_report.py` - Added `best_candidate` property
- `rivet_pro/core/services/manual_service.py` - Reordered LLM cascade: Groq → DeepSeek → Claude
- `rivet_pro/core/utils/response_formatter.py` - Human-in-loop prompt UI
- `rivet_pro/adapters/telegram/bot.py` - `_handle_manual_validation_reply()` handler
- `rivet_pro/migrations/025_manual_feedback.sql` - User feedback table
- `rivet_pro/core/utils/encoding.py` - Windows UTF-8 console fix

**LLM Cascade (speed/cost optimized):**
1. Groq (free, fastest)
2. DeepSeek (cheap)
3. Claude (expensive, last resort)

**Test Results:** 5/10 equipment items found direct PDF manuals

### Windows Encoding Fix

Created `rivet_pro/core/utils/encoding.py` to fix emoji display on Windows console (cp1252 → UTF-8).

## Bot Status

Running on VPS at `72.60.175.144`. Check with:
```bash
ssh root@72.60.175.144 "ps aux | grep telegram | grep -v grep"
ssh root@72.60.175.144 "tail -30 /tmp/bot.log"
```

## What's Next

1. **Test human-in-the-loop** - Send photo to @testbotrivet_bot of obscure equipment, verify it shows "Is this correct?" prompt, reply Yes/No
2. **Verify feedback storage** - Check `manual_cache` and `manual_feedback` tables after user replies
3. **Push latest commits** - `git push origin main` then redeploy to VPS

## MCP Memory

Query for context:
- `mcp__memory__search_nodes("SearchTransparency")`
- `mcp__memory__search_nodes("HumanInTheLoop")`
- `mcp__memory__search_nodes("LLMCascade")`

---
