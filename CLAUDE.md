# RIVET Pro - Essential Documentation

## Key Reference Documents

**Keep these updated as the system evolves:**

| Document | Purpose | When to Update |
|----------|---------|----------------|
| `docs/CLAUDE_REFERENCE.md` | Technical reference for AI agents - infrastructure, connections, deployment, troubleshooting | When infrastructure, credentials, or architecture changes |
| `docs/USER_MANUAL.md` | User-facing documentation for the Telegram bot | When features are added or modified |

### Quick Start for New Sessions

1. **Read `docs/CLAUDE_REFERENCE.md`** for:
   - VPS connection (72.60.175.144)
   - Database connection strings
   - Deployment commands
   - Troubleshooting guides

2. **Read `docs/USER_MANUAL.md`** to understand:
   - All bot commands and features
   - SME Expert personalities
   - User workflows

---

# RALPH WIGGUM - AUTONOMOUS DEVELOPMENT LOOP

## When to Use Ralph

**Use Ralph for large features that require multiple stories/iterations.**

Ralph is an autonomous coding agent that:
- Reads stories from the `ralph_stories` PostgreSQL table
- Implements one story at a time
- Commits changes with proper messages
- Updates database status
- Loops until all stories are complete

## How to Start Ralph

### Option 1: Run Directly in Claude Code (Recommended)
1. Read `scripts/ralph/prd.json` for current PRD and stories
2. Read `scripts/ralph/prompt.md` for agent instructions
3. Connect to database using `DATABASE_URL` from `.env`
4. Query: `SELECT * FROM ralph_stories WHERE status = 'todo' ORDER BY priority`
5. Implement one story following the prompt instructions
6. Update status in database when complete
7. Repeat until all stories are done

### Option 2: Use Python Script
```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
python scripts/ralph/ralph_local.py --max 5
```

## Ralph File Locations

| File | Purpose |
|------|---------|
| `scripts/ralph/prd.json` | Current PRD with user stories |
| `scripts/ralph/prompt.md` | Agent instructions and quality checks |
| `scripts/ralph/progress.txt` | Append-only progress log |
| `ralph_stories` table | Database story tracking |

## Creating New Ralph Work

1. Write a PRD with user stories
2. Insert stories into `ralph_stories` table:
   ```sql
   INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, priority, status)
   VALUES (1, 'FEATURE-001', 'Title', 'Description', '["criteria1", "criteria2"]'::jsonb, 1, 'todo');
   ```
3. Update `scripts/ralph/prd.json` with the new PRD
4. Start Ralph using one of the methods above

---

# CLAUDE.md - Rivet Pro

## MISSION

Extract Atlas CMMS from Agent Factory into Rivet Pro as a working product. The CMMS already exists — your job is to pull it out clean, wire it up, and make it production-ready.

**Atlas CMMS is the foundation. Telegram bot is the interface. AI learns invisibly from every interaction.**

---

## CURRENT OBJECTIVE: EXTRACT & PRODUCTIZE ATLAS CMMS

Atlas CMMS exists in Agent Factory. Find it, extract it, make it work standalone in Rivet Pro.

### What Already Exists in Agent Factory

Search for these:

```bash
# CMMS Core
grep -rn "cmms\|CMMS\|equipment\|work_order" ~/Agent-Factory/ --include="*.py"
grep -rn "cmms" ~/Agent-Factory/migrations/ --include="*.sql"

# Database Models
grep -rn "class Equipment\|class WorkOrder" ~/Agent-Factory/ --include="*.py"

# Telegram Integration
grep -rn "orchestrator_bot\|telegram" ~/Agent-Factory/agent_factory/integrations/

# Existing Commands
grep -rn "CommandHandler\|/wo\|/equip" ~/Agent-Factory/ --include="*.py"
```

### Known Locations (Verify These)

| Component | Likely Path in Agent Factory |
|-----------|------------------------------|
| CMMS Models | `agent_factory/services/` or `agent_factory/models/` |
| Equipment Table | `migrations/005_cmms_equipment.sql` or similar |
| Work Orders | Look for `work_order` in migrations |
| Telegram Bot | `agent_factory/integrations/telegram/orchestrator_bot.py` |
| Database Manager | `agent_factory/core/` or `agent_factory/services/` |

### Extraction Target

Pull into Rivet Pro:

```
rivet_pro/
├── atlas/                    # Core CMMS
│   ├── models.py            # Equipment, WorkOrder, Technician
│   ├── database.py          # Connection, queries
│   └── services.py          # Business logic
├── bot/                      # Telegram interface
│   ├── bot.py               # Main bot, handlers
│   ├── commands/            # /equip, /wo, /manual handlers
│   └── conversations/       # Multi-step flows (add equipment, create WO)
├── migrations/              # SQL schemas
└── tests/
```

---

## EXTRACTION PROCESS

### Step 1: Audit Agent Factory

```bash
# Find all CMMS-related files
find ~/Agent-Factory -name "*.py" | xargs grep -l "cmms\|equipment\|work_order" 

# Find migrations
ls ~/Agent-Factory/migrations/ | grep -i cmms

# Find the running bot
cat ~/Agent-Factory/agent_factory/integrations/telegram/orchestrator_bot.py | head -100
```

### Step 2: Extract Database Layer

1. Copy relevant migrations to `rivet_pro/migrations/`
2. Extract database connection code
3. Extract model classes (Equipment, WorkOrder, Technician)
4. Verify tables exist in Neon, or run migrations

### Step 3: Extract CMMS Services

1. Find equipment CRUD operations
2. Find work order CRUD operations  
3. Pull into `rivet_pro/atlas/services.py`
4. Simplify — remove unused dependencies

### Step 4: Extract Bot Commands

1. Find existing `/equip`, `/wo` handlers
2. Find photo/OCR handling
3. Pull into `rivet_pro/bot/`
4. Wire to extracted CMMS services

### Step 5: Test End-to-End

1. Run the bot locally
2. `/start` → registers technician
3. `/equip search motor` → finds equipment
4. Send nameplate photo → OCR works
5. `/wo create` → creates work order linked to equipment
6. Verify data in Neon

---

## ATLAS CMMS FEATURES TO EXTRACT

### Must Have (MVP)

- [ ] Equipment registry (CRUD)
- [ ] Work orders with mandatory equipment linking
- [ ] Technician registration
- [ ] Telegram commands: `/start`, `/equip`, `/wo`
- [ ] Nameplate OCR → equipment creation
- [ ] Database persistence (Neon PostgreSQL)

### Already Built (Find & Extract)

- [ ] 4-route orchestrator (confidence-based routing)
- [ ] Knowledge atoms storage
- [ ] Gap detector
- [ ] OCR pipeline (Gemini Vision)
- [ ] Session management

### Wire Later (Phase 2+)

- Self-healing knowledge base
- Research agent
- Learning feedback loop
- Multi-tenant architecture

---

## STRANGLER FIG RULES

1. **Don't rewrite what works.** Extract and adapt.

2. **Cut dependencies aggressively.** If Atlas CMMS imports 15 things from Agent Factory, figure out which 3 it actually needs.

3. **Test after each extraction.** Don't extract 10 files then debug. Extract 1, test, commit, repeat.

4. **Keep Agent Factory running.** It's production. Don't break it. Rivet Pro is the new home.

5. **When in doubt, copy more than less.** You can delete code. You can't delete context you didn't capture.

---

## ENVIRONMENT

```bash
# Required in .env
TELEGRAM_BOT_TOKEN=xxx          # New bot token for Rivet Pro, or same as Agent Factory
NEON_DATABASE_URL=xxx           # Same Neon instance, or new one
GOOGLE_API_KEY=xxx              # For Gemini Vision OCR
```

---

## ACCEPTANCE CRITERIA

Rivet Pro Atlas CMMS is complete when:

- [ ] Bot runs standalone from `rivet_pro/` directory
- [ ] All CMMS data in Neon (equipment, work orders, technicians)
- [ ] `/equip` commands work
- [ ] `/wo` commands work
- [ ] Photo OCR creates equipment
- [ ] No imports from `agent_factory/` — fully extracted
- [ ] Tests pass
- [ ] Can run 24 hours without crashing

---

## START HERE

```bash
# 1. Audit what exists
grep -rn "class Equipment\|class WorkOrder" ~/Agent-Factory/ --include="*.py"

# 2. Find the main bot
cat ~/Agent-Factory/agent_factory/integrations/telegram/orchestrator_bot.py | head -50

# 3. Find CMMS migrations
ls -la ~/Agent-Factory/migrations/ | grep -i cmms

# 4. Start extraction: Database models first
# 5. Then services
# 6. Then bot commands
# 7. Test each piece as you go

# Goal: Working Atlas CMMS in rivet_pro/ with zero agent_factory imports
```

**Extract it. Wire it. Ship it.**

---

# SESSION MEMORY

## CURRENT STATE (Update before clearing context)
- **Last session**: 2026-01-14
- **Active branch**: main
- **Recent work**: Repository cleanup - archived 137 files locally, implemented memory system
- **Next task**: Continue CMMS extraction from Agent Factory

## USER PREFERENCES (Learned from interactions)
- Archive files instead of permanently deleting them
- Commit changes to git for historical reference
- Keep local archive for files containing secrets/API keys
- Use trunk-based development with feature flags
- Prefer automatic reminders to save session context
- Self-approve PRs for solo development

## CODE PATTERNS
- **Feature flags**: Use `FeatureFlagManager` from `rivet_pro/core/feature_flags.py`
- **Bot handlers**: `rivet_pro/adapters/telegram/bot.py`
- **Database**: PostgreSQL via Neon (DATABASE_URL in .env)
- **Ralph stories**: `ralph_stories` table in database
- **Memory storage**: `rivet_pro/rivet/memory/storage.py` (pluggable backends)

## QUICK CONTEXT RESTORATION
If you just started a new session, read `docs/QUICK_CONTEXT.md` for instant context.
For session history, check `docs/SESSION_LOG.md`.
Query MCP memory: `mcp__memory__search_nodes("RIVET")`
