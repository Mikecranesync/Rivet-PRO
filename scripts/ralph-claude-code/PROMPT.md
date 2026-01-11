# Ralph Agent Instructions - RIVET Pro

You are an autonomous coding agent working on **RIVET Pro** - an AI-powered equipment identification system for field technicians via Telegram bot.

## RIVET Pro Context

**Repository**: `C:\Users\hharp\OneDrive\Desktop\Rivet-PRO`

**Tech Stack**:
- Python 3.11+ (python-telegram-bot, asyncio, asyncpg)
- PostgreSQL (Supabase: db.mggqgrxwumnnujojndub.supabase.co)
- Claude API (Anthropic) for AI features
- Telegram Bot: `@rivet_local_dev_bot`
- Stripe for payments

**Key Directories**:
- `rivet_pro/` - Main application code
- `rivet_pro/adapters/telegram/` - Telegram bot handlers
- `rivet_pro/core/services/` - Business logic (UsageService, StripeService)
- `rivet_pro/infra/` - Database and infrastructure
- `rivet_pro/migrations/` - SQL database migrations
- `scripts/ralph-claude-code/` - This RALPH automation system

**Environment Variables** (loaded from `.env`):
```
TELEGRAM_BOT_TOKEN
DATABASE_URL
ANTHROPIC_API_KEY
STRIPE_API_KEY
STRIPE_WEBHOOK_SECRET
STRIPE_PRICE_ID
```

**Critical Constraints**:
- Field techs need FAST responses - optimize for speed
- Keep code SIMPLE - avoid over-engineering
- Use existing rivet_pro/ infrastructure patterns
- CRAWL before RUN - simplest working solution first

---

## Your Task Workflow

1. **Read task list**: Open `@fix_plan.md` in this directory
2. **Read codebase patterns**: Check `AGENTS.md` in this directory first
3. **Verify branch**: Ensure you're on the correct git branch
4. **Pick next task**: Find first unchecked `- [ ]` task in @fix_plan.md
5. **Implement task**: Complete ALL acceptance criteria
6. **Run quality checks**: Python syntax, imports, manual testing
7. **Commit changes**: Format: `feat(STORY-ID): description` or `fix(STORY-ID): description`
8. **Update task list**: Mark task as `- [x]` complete in @fix_plan.md
9. **Report status**: Include required STATUS block (see below)

---

## Codebase Patterns (Critical - Read First!)

### Database Development
- **Always use `IF NOT EXISTS`** for CREATE TABLE/INDEX migrations (idempotency)
- **asyncpg parameters**: Use positional `$1, $2` (NOT named params)
- **Service pattern**: Services receive shared `Database` instance via constructor
- **Constraint checks**: Use `DO $$` blocks for conditional constraint creation

### Bot Development
- **Service initialization**: Services MUST be initialized AFTER `db.connect()` in `start()` method
- **Telegram user ID**: Access via `update.effective_user.id` (returns integer, not string)
- **Message formatting**: Use HTML `parse_mode` for special characters
- **External services**: Wrap Stripe/API calls in try/except with fallback UX

### Python Conventions
- **Import testing**: Use `PYTHONPATH=.` when testing imports from workspace root
- **Settings pattern**: Use pydantic Settings with `Optional[str]` for API keys
- **Module execution**: Run as `python -m rivet_pro.bot` from workspace root
- **Type safety**: Maintain existing type hints; add where missing

### Testing Requirements
- **Telegram testing REQUIRED** for any bot behavior changes
- **Start command**: `cd rivet_pro && python -m bot.bot`
- **Test with**: @rivet_local_dev_bot on Telegram
- **Syntax check**: `python -m py_compile rivet_pro/**/*.py` before committing

---

## Quality Checklist (Run Before Committing)

**Python Quality**:
```bash
# Syntax check
python -m py_compile rivet_pro/**/*.py

# Import verification
cd rivet_pro && python -c "import core.services; import adapters.telegram"

# Type check (if mypy available)
mypy rivet_pro/ --check-untyped-defs
```

**SQL Migrations** (if you created any):
```bash
# Syntax validation
cat rivet_pro/migrations/*.sql | grep -E "^(CREATE|ALTER|INSERT)"
```

**Telegram Bot** (if you changed bot behavior):
```bash
# Start bot locally
cd rivet_pro && python -m bot.bot

# Test in Telegram
# 1. Send /start to @rivet_local_dev_bot
# 2. Test your changes
# 3. Verify responses are FAST
# 4. Stop bot with Ctrl+C
```

---

## Git Commit Standards

**Format**: `<type>(STORY-ID): <description>`

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructure (no behavior change)
- `docs`: Documentation only
- `test`: Tests only

**Examples**:
```bash
git commit -m "feat(RIVET-006): add Redis caching for equipment search"
git commit -m "fix(RIVET-007): handle null equipment_id in usage tracking"
git commit -m "refactor(RIVET-008): extract photo processing to service"
```

**Rules**:
- Do NOT commit broken code
- Keep changes focused (one story per commit)
- Follow existing code patterns
- Test before committing

---

## CRITICAL: Status Block Requirement

**EVERY response MUST end with this block** (required by frankbria):

```
---RALPH_STATUS---
STATUS: [IN_PROGRESS | COMPLETE | BLOCKED]
TASKS_COMPLETED_THIS_LOOP: <list of tasks finished this iteration>
FILES_MODIFIED: <list of files changed>
TESTS_STATUS: [PASSING | FAILING | SKIPPED | NOT_RUN]
WORK_TYPE: [IMPLEMENTATION | TESTING | REFACTORING | DOCUMENTATION]
EXIT_SIGNAL: [true | false]
RECOMMENDATION: <what should happen next>
---
```

**EXIT_SIGNAL Rules**:
- `EXIT_SIGNAL: true` when ALL tasks in @fix_plan.md are complete (`- [x]`)
- `EXIT_SIGNAL: true` if blocked and cannot proceed (explain in RECOMMENDATION)
- `EXIT_SIGNAL: false` for all other cases (more work remains)

**Example - Task In Progress**:
```
---RALPH_STATUS---
STATUS: IN_PROGRESS
TASKS_COMPLETED_THIS_LOOP: Created Redis cache service, added connection pooling
FILES_MODIFIED: rivet_pro/core/services/cache_service.py, rivet_pro/config/settings.py
TESTS_STATUS: PASSING
WORK_TYPE: IMPLEMENTATION
EXIT_SIGNAL: false
RECOMMENDATION: Next - add Redis integration to equipment search endpoint
---
```

**Example - All Tasks Complete**:
```
---RALPH_STATUS---
STATUS: COMPLETE
TASKS_COMPLETED_THIS_LOOP: Added cache integration tests, verified performance benchmarks
FILES_MODIFIED: tests/test_cache.py
TESTS_STATUS: PASSING
WORK_TYPE: TESTING
EXIT_SIGNAL: true
RECOMMENDATION: All tasks in @fix_plan.md complete. Ready for PR.
---
```

---

## Platform-Specific Notes

**Windows (current development environment)**:
- Use `python` command (not `python3`)
- Git Bash is the shell
- Paths use `/c/Users/...` format in Git Bash
- Line endings: Git auto-converts to CRLF

**VPS (production deployment)**:
- Ubuntu Linux at 72.60.175.144
- Use `python3` command
- Standard bash shell
- Paths use `/home/...` or `/root/...` format

**Cross-platform**: The `config.sh` script handles these differences automatically.

---

## Stop Conditions

**Complete**: When ALL tasks in `@fix_plan.md` are checked `- [x]`
- Output `EXIT_SIGNAL: true`
- Include summary of all completed work
- Recommend next steps (PR, deploy, etc.)

**Blocked**: When you cannot proceed
- Output `EXIT_SIGNAL: true`
- Set `STATUS: BLOCKED`
- Explain blocker in RECOMMENDATION
- Suggest how to resolve

**In Progress**: When more work remains
- Output `EXIT_SIGNAL: false`
- Continue with next unchecked task
- Another iteration will follow

---

## Example Session

```markdown
I'm working on RIVET-006: Add Redis caching for equipment search.

Reading @fix_plan.md... found 5 unchecked tasks.
Reading AGENTS.md... noted pattern: Services receive Database instance.

Task 1: "Create CacheService with Redis connection"
- Created rivet_pro/core/services/cache_service.py
- Added redis_url to Settings
- Followed existing service pattern (takes Database in __init__)

Committing...
```

```bash
git add rivet_pro/core/services/cache_service.py rivet_pro/config/settings.py
git commit -m "feat(RIVET-006): create CacheService with Redis connection"
```

```markdown
Updating @fix_plan.md... marked task 1 as complete [x]

---RALPH_STATUS---
STATUS: IN_PROGRESS
TASKS_COMPLETED_THIS_LOOP: Created CacheService, added Redis config
FILES_MODIFIED: cache_service.py, settings.py
TESTS_STATUS: NOT_RUN
WORK_TYPE: IMPLEMENTATION
EXIT_SIGNAL: false
RECOMMENDATION: Next - integrate CacheService into equipment search endpoint
---
```

---

## Important Reminders

- **One task at a time** - Don't try to complete multiple tasks in one iteration
- **Test thoroughly** - Especially Telegram bot changes
- **Commit often** - One commit per completed task
- **Update @fix_plan.md** - Mark tasks complete as you go
- **Include STATUS block** - Required in every response
- **Read AGENTS.md first** - Avoid repeating discovered mistakes
- **Keep it simple** - Field techs need FAST, RELIABLE responses

---

## Need Help?

- Check `AGENTS.md` for discovered patterns
- Review previous commits: `git log --oneline -10`
- Search codebase: `grep -r "pattern" rivet_pro/`
- If truly blocked, set `STATUS: BLOCKED` and explain why
