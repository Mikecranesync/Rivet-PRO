# Amp-based Ralph System (Archived)

**Archived**: 2026-01-11
**Reason**: Migrated to frankbria/ralph-claude-code for improved reliability and cross-platform support

---

## What This Was

Custom Ralph Wiggum implementation using Amp CLI with bash loop orchestration. This system autonomously implemented user stories by running Amp in a loop until completion.

**Repository**: https://github.com/snarktank/ralph (original concept)
**Our Implementation**: Custom for RIVET Pro with Amp CLI integration

---

## Completed Work

This Ralph system successfully completed 3 major stories:

### ✅ RIVET-001: Usage Tracking System
**Commit**: a68febc (partial), fully merged on ralph/mvp-phase1
**Files Created**:
- `rivet_pro/migrations/011_usage_tracking.sql` - Database schema
- `rivet_pro/core/services/usage_service.py` - Business logic

**Features**:
- Tracks equipment lookups per user
- Enforces 10 free lookups limit
- Integrates with Telegram bot photo handler

### ✅ RIVET-002: Stripe Payment Integration
**Commit**: 71480de
**Files Created**:
- `rivet_pro/migrations/012_stripe_integration.sql` - Subscription columns
- `rivet_pro/core/services/stripe_service.py` - Payment handling
- `rivet_pro/adapters/web/routers/stripe.py` - Webhook endpoint

**Features**:
- $29/month Pro tier checkout
- Stripe webhook handling (subscription events)
- Telegram notification on successful payment

### ✅ RIVET-003: Free Tier Limit Enforcement
**Commit**: 0935dd8
**Files Modified**:
- `rivet_pro/adapters/telegram/bot.py` - Photo handler with usage checks

**Features**:
- Blocks lookups at 10 for free users
- Shows inline Stripe checkout link
- Pro users get unlimited lookups

---

## Uncompleted Work

These stories were started but not completed:

### ❌ RIVET-004: Shorten System Prompts
**Status**: Not started (passes: false)
**Goal**: Reduce all RIVET prompts by 50% for faster field responses

### ❌ RIVET-005: Remove n8n Footer
**Status**: Not started (passes: false)
**Goal**: Remove n8n branding from Telegram bot messages

**Decision**: These stories were not migrated to frankbria system. May be implemented later as RIVET-006+.

---

## Key Files

- `prd.json` - Product requirements with 5 stories (3 complete, 2 incomplete)
- `prompt.md` - Instructions for Amp agent iterations
- `progress.txt` - Learnings log with discovered codebase patterns
- `ralph.sh` - Bash loop that spawned fresh Amp instances
- `prd.json.example` - Template for creating new PRDs

---

## Discovered Codebase Patterns

This Ralph system discovered important patterns that are now documented in the new `scripts/ralph-claude-code/AGENTS.md`:

**Database Patterns**:
- Always use `IF NOT EXISTS` for idempotency
- asyncpg uses positional `$1` parameters (not named)
- Services receive shared Database instance

**Bot Development**:
- Services initialize AFTER `db.connect()`
- Telegram user ID is integer via `update.effective_user.id`
- Use HTML parse_mode for special characters

**Python Conventions**:
- Use `PYTHONPATH=.` for import testing
- Pydantic Settings with `Optional[str]` for API keys
- Run modules as `python -m rivet_pro.bot`

---

## How to Restore

If frankbria migration fails and you need to restore this system:

```bash
# From workspace root
cd /path/to/Rivet-PRO

# Copy archive back to active location
cp -r scripts/ralph-archive/2026-01-11-amp-ralph/* scripts/ralph/

# Verify files restored
ls scripts/ralph/

# Run Ralph
cd scripts/ralph
./ralph.sh 10
```

**Prerequisites for restoration**:
- Amp CLI installed and configured
- Git bash (Windows) or bash (Linux)
- ANTHROPIC_API_KEY in environment

**Run command**:
```bash
./ralph.sh <max_iterations>
```

---

## Why We Migrated

**Reasons for switching to frankbria/ralph-claude-code**:

1. **Better Windows support**: frankbria handles Windows Git Bash edge cases
2. **Built-in rate limiting**: Prevents API quota exhaustion
3. **Circuit breaker**: Automatic failure detection and recovery
4. **Session management**: 24-hour session expiry prevents runaway costs
5. **Structured progress**: JSON response analysis instead of text parsing
6. **Established patterns**: Benefit from frankbria community learnings
7. **Active maintenance**: frankbria is actively maintained vs. our custom solution

---

## Migration Details

See `scripts/ralph-claude-code/` for new system:
- PROMPT.md - RIVET Pro agent instructions
- AGENTS.md - Migrated codebase patterns
- @fix_plan.md - Markdown task list (converted from prd.json)
- config.sh - Platform detection
- notify.py - Telegram notifications
- convert-prd.py - JSON→markdown converter
- ralph-wrapper.sh - Orchestration script

---

## Historical Context

**Created**: January 10, 2026
**Last Run**: Before January 11, 2026
**Total Stories Completed**: 3/5 (60%)
**Total Amp Iterations**: ~15-20 (estimated)

---

## Contact

For questions about this archived system or the migration:
- Check GitHub issue: https://github.com/Mikecranesync/Rivet-PRO/issues/6
- Review migration PR (will be created after frankbria setup)

**DO NOT use this system for new work**. Use `scripts/ralph-claude-code/` instead.
