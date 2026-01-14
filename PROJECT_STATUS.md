# RIVET Pro - Project Status Snapshot

**Generated**: 2026-01-11
**Purpose**: Comprehensive snapshot of current project state

---

## What Works

### ✅ Core Infrastructure
- **VPS Deployment** (72.60.175.144)
  - n8n running on port 5678
  - PostgreSQL databases connected (Neon primary)
  - SSH access configured
  - Git repository active

- **Database Layer**
  - Neon PostgreSQL (primary): Connected and operational
  - Supabase PostgreSQL: Available as fallback
  - Multi-database failover configuration
  - Ralph system schema (migrations/010_ralph_system.sql)

### ✅ Telegram Bots (3 Active)
1. **@rivet_local_dev_bot** (ID: 8161680636)
   - Connected to Photo Bot v2 workflow
   - Webhook-based architecture
   - OCR for equipment nameplates

2. **@RivetCeo_bot** (ID: 7910254197)
   - Orchestrator bot
   - 4-route confidence-based routing

3. **@RivetCMMS_bot** (ID: 7855741814)
   - Public CMMS interface
   - Work order management

### ✅ n8n Workflows (15 Active, 24 Inactive)
- **Success Rate**: 90% across active workflows
- **Photo Bot v2** (7LMKcMmldZsu1l6g): Equipment photo OCR
- **Manual Hunter**: Equipment manual search
- **URL Validator** (Test & Production): Validates manual URLs
- **LLM Judge**: Quality assessment
- **Test Runner**: Automated testing

### ✅ Ralph Autonomous System (Partially Complete)
- Directory structure: `/root/ralph/`
- 7 bash scripts implemented:
  - `ralph_loop.sh` - main orchestration
  - `run_story.sh` - story execution
  - `db_manager.sh` - database failover
  - `detect_databases.sh` - auto-detection
  - `sync_databases.sh` - multi-DB sync
  - `notify_telegram.sh` - notifications
  - `check_status.sh` - monitoring
- Database schema initialized
- Multi-database detection working
- Story tracking in PostgreSQL

---

## What Is Broken or Incomplete

### ⚠️ Ralph Story Execution (CRITICAL)
**Status**: Claude Code CLI hangs in automation
**Impact**: Cannot execute stories autonomously
**Root Cause**: CLI requires interactive permissions even with `--dangerously-skip-permissions`
**Workaround Attempted**: Running as non-root `ralph` user - still hangs
**Next Steps**:
- Consider switching to Anthropic Messages API
- Implement `expect` script for interactive prompts
- Or use Claude CLI only for planning, manual implementation

### ⚠️ Telegram Notifications
**Status**: Not configured in Ralph
**Issue**: `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` need to be set in `/root/ralph/config/.env`
**Impact**: No real-time progress updates from Ralph
**Fix**: Add credentials and test with `notify_telegram.sh`

### ⚠️ n8n Workflow Credentials
**Status**: Some workflows need credential wiring
**Affected**: Main loop workflow (HIwpqfAegFSotLqs)
**Fix**: Wire Supabase credentials to 7 Postgres nodes

### ⚠️ Missing Documentation
**Status**: Before this file, no comprehensive status docs
**Impact**: New developers can't quickly understand project
**Fix**: This file + N8N_WORKFLOWS.md + QUICK_REFERENCE.md

### ⚠️ Test Coverage
**Status**: Unknown - no clear test suite
**Files**: Some test files exist (`tests/`, `test_*.py`)
**Issue**: Not clear which tests run, which pass
**Next Step**: Document test strategy, run test suite

---

## Key Files

### 1. `/root/Rivet-PRO/rivet/core/database_manager.py`
**What**: Database connection pooling and query execution
**Importance**: Core data layer, used by all services
**Status**: Functional

### 2. `/root/Rivet-PRO/rivet_pro/migrations/010_ralph_system.sql`
**What**: Ralph autonomous system schema
**Tables**: ralph_projects, ralph_stories, ralph_iterations, ralph_executions
**Status**: Applied to Neon database

### 3. `/root/ralph/scripts/ralph_loop.sh`
**What**: Main orchestration loop for autonomous story execution
**Status**: Implemented, but blocked by Claude CLI issue

### 4. `/root/ralph/scripts/db_manager.sh`
**What**: Database failover and multi-DB replication
**Functions**: load_primary(), test_db(), db_query(), db_execute(), db_status()
**Status**: Working

### 5. `/root/Rivet-PRO/.env`
**What**: Environment configuration with API keys and database URLs
**Critical Variables**: ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, DATABASE_URL
**Status**: Configured, copied to `/root/ralph/config/.env`

### 6. `/root/Rivet-PRO/rivet/integrations/telegram/`
**What**: Telegram bot implementations
**Files**: orchestrator_bot.py, cmms_bot.py
**Status**: Bots operational

### 7. `/root/Rivet-PRO/rivet-n8n-workflow/rivet_workflow.json`
**What**: Main n8n workflow definition
**Size**: Complex multi-node workflow
**Status**: Modified recently (git shows uncommitted changes)

### 8. `/root/Rivet-PRO/rivet/core/trace_logger.py`
**What**: Logging and debugging infrastructure
**Status**: Functional

### 9. `/root/Rivet-PRO/upload_ralph_scripts.py`
**What**: Python script to upload bash scripts to VPS
**Purpose**: Deployment automation for Ralph
**Status**: Used successfully

### 10. `/root/Rivet-PRO/CLAUDE.md`
**What**: Project instructions for Claude (this AI assistant)
**Contains**: Mission, extraction guidance, strangler fig rules
**Status**: Active, referenced during development

---

## Tech Stack

### Languages
- **Python** (primary): Backend services, bots, scripts
- **JavaScript/Node.js**: n8n workflow logic, custom code nodes
- **Bash**: Deployment and orchestration scripts (Ralph system)
- **SQL**: PostgreSQL queries and migrations

### Frameworks & Tools
- **n8n** (v0.x): Workflow automation platform
- **Telegram Bot API**: User interface layer
- **PostgreSQL**: Primary database (Neon, Supabase)
- **Anthropic Claude API**: AI/LLM integration
- **Claude Code CLI**: Development assistant (attempting automation)

### APIs & Services
- **Anthropic Claude** (Sonnet 4.5): Code generation, analysis
- **Google Gemini** (2.5): Vision OCR for equipment nameplates
- **Telegram**: Bot interface for technicians
- **Neon Database**: Serverless PostgreSQL
- **Supabase**: PostgreSQL + realtime features

### Infrastructure
- **VPS**: 72.60.175.144 (production)
- **Git**: Version control (GitHub)
- **SSH**: Remote access and deployment
- **Docker**: (mentioned but not actively used)

### Development Tools
- **Claude Code CLI**: AI pair programming
- **psql**: PostgreSQL client
- **curl**: API testing, HTTP requests
- **jq**: JSON parsing in bash
- **dos2unix**: Line ending conversion (Windows/Linux)

---

## Next Steps

### 🔴 Priority 1: Fix Ralph Story Execution
**Why**: Blocks autonomous development
**Options**:
1. Debug Claude CLI hanging issue
2. Switch to Anthropic Messages API with manual file operations
3. Use hybrid approach: Claude plans, human implements

**Action**: Test Claude CLI with minimal prompt in isolated directory
**Owner**: Development team
**Timeline**: Critical - resolve before using Ralph

### 🟡 Priority 2: Complete End-to-End Test
**Why**: Validate entire RIVET system works with real data
**Test Flow**:
1. User sends nameplate photo to @rivet_local_dev_bot
2. Photo Bot v2 → OCR extracts equipment data
3. Equipment saved to database
4. Manual Hunter → searches for manual
5. URL Validator → validates URLs
6. Response sent back to user

**Action**: Document test procedure, run with real photo
**Owner**: QA/Testing
**Timeline**: After Priority 1

### 🟢 Priority 3: Documentation & Onboarding
**Why**: Project is complex, need quick-start for new contributors
**Deliverables**:
- ✅ PROJECT_STATUS.md (this file)
- ⬜ N8N_WORKFLOWS.md (workflow map)
- ⬜ QUICK_REFERENCE.md (one-page guide)
- ⬜ TESTING.md (how to run tests)
- ⬜ DEPLOYMENT.md (how to deploy)

**Action**: Complete remaining documentation files
**Owner**: Development team
**Timeline**: This week

---

## Additional Notes

### Git Status
- **Current branch**: feat/github-actions-claude-integration
- **Main branch**: main
- **Uncommitted changes**: rivet-n8n-workflow/rivet_workflow.json (modified)
- **Recent commits**:
  - GitHub Actions integration
  - n8n startup guides
  - n8n-MCP configuration
  - Deployment fixes

### Known Issues Log
1. Claude CLI hangs in automation (RIVET-TEST-001, ORG-001)
2. Telegram notifications not configured in Ralph
3. n8n workflow credentials need wiring
4. Large number of untracked files (temp files, logs)

### Success Metrics
- 3 Telegram bots: ✅ All operational
- 15 n8n workflows: ✅ 90% success rate
- Database connections: ✅ Primary (Neon) + fallbacks
- Ralph infrastructure: ✅ 80% complete (execution blocked)

---

**Last Updated**: 2026-01-11
**Next Review**: When Ralph execution issue resolved
