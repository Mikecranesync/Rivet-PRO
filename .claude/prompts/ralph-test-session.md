# Ralph Migration - Test Implementation Session

## Context: What Was Done Previously

### Migration Completed ✅
1. **Created customization files** in `scripts/ralph-claude-code/`:
   - PROMPT.md - Agent instructions with RIVET Pro patterns
   - AGENTS.md - Discovered codebase patterns (database, bot, Python)
   - @fix_plan.md - Markdown task list (RIVET-001/002/003 complete, RIVET-004/005 discarded)
   - config.sh - Platform detection (Windows/Linux)
   - notify.py - Telegram notifications
   - convert-prd.py - JSON→markdown PRD converter
   - ralph-wrapper.sh - Orchestration script

2. **Archived old system** in `scripts/ralph-archive/2026-01-11-amp-ralph/`
   - All Amp-based Ralph files preserved
   - Comprehensive README for rollback

3. **Created Git artifacts**:
   - Branch: `ralph/frankbria-migration`
   - GitHub Issue #6: https://github.com/Mikecranesync/Rivet-PRO/issues/6
   - Pull Request #7: https://github.com/Mikecranesync/Rivet-PRO/pull/7
   - Commits: 54873fa (initial), 0c3c8b4 (Windows fix)

4. **Smoke tested** - All components working ✅

### Current State
- PR #7 is open and ready for review
- frankbria/ralph-claude-code NOT yet installed (pending)
- No test stories run yet
- Ready for end-to-end testing

---

## Your Mission: Create & Execute Comprehensive Ralph Test

### Objective
Install frankbria/ralph-claude-code and run a **small but real** implementation test that:
1. Tests all Ralph components (PROMPT, AGENTS, notifications, git)
2. Makes actual changes to RIVET Pro codebase
3. Has highly verifiable success criteria
4. Can complete in 1-3 Ralph iterations (~5-10 minutes)

---

## Phase 1: Install frankbria (Windows)

### Step 1: Check Prerequisites
```bash
# Verify Claude Code CLI installed
claude --version
# Should show version (e.g., 0.x.x)

# Verify Git Bash
bash --version
# Should show 4.0+ for frankbria compatibility

# Verify Python
python --version
# Should show 3.11+
```

### Step 2: Install frankbria
```bash
# Clone to temp location
cd /c/temp
git clone https://github.com/frankbria/ralph-claude-code.git
cd ralph-claude-code

# Run installer
./install.sh

# Verify installation
which ralph
ralph --version
```

**Expected**: `ralph` command available globally

### Step 3: Verify Environment
```bash
cd /c/Users/hharp/OneDrive/Desktop/Rivet-PRO/scripts/ralph-claude-code

# Test platform detection
source config.sh

# Should output:
# Platform: windows
# Python: python (3.11.x)
# Workspace: /c/Users/hharp/OneDrive/Desktop/Rivet-PRO
```

---

## Phase 2: Create Test Story (RIVET-006)

### Story Design Principles
- **Small**: Single file creation or modification
- **Real**: Actual codebase change, not hello-world
- **Verifiable**: Clear pass/fail criteria
- **Safe**: Won't break existing functionality
- **Valuable**: Actually useful for RIVET Pro

### Recommended Test Story: Health Check Endpoint

**Why this story?**
- ✅ Real feature (production monitoring needs this)
- ✅ Small scope (one new file, one route registration)
- ✅ Highly verifiable (curl test)
- ✅ Tests database connection (using existing patterns)
- ✅ Tests documentation skills (docstrings, comments)
- ✅ Safe (no impact on existing features)

### Step 1: Add Story to @fix_plan.md

Edit `scripts/ralph-claude-code/@fix_plan.md` and add:

```markdown
## Current Tasks

_Complete these tasks in order of priority._

### ❌ RIVET-006: Health Check Endpoint

Add a health check endpoint for production monitoring. The endpoint should verify database connectivity and return system status.

**Acceptance Criteria**:
- [ ] Create `rivet_pro/adapters/web/routers/health.py`
- [ ] Implement `GET /health` endpoint that returns JSON
- [ ] Check database connection using `db.fetchval("SELECT 1")`
- [ ] Return status: `{"status": "healthy", "database": "connected", "timestamp": "ISO8601"}`
- [ ] Return 503 if database check fails with `{"status": "unhealthy", "database": "disconnected"}`
- [ ] Register health router in `rivet_pro/adapters/web/main.py`
- [ ] Add docstring explaining endpoint purpose
- [ ] Test manually: `curl http://localhost:8000/health` returns 200
- [ ] Commit with message: `feat(RIVET-006): add health check endpoint`
- [ ] No changes to existing files except main.py router registration

**Implementation Notes**:
- Follow existing router pattern (see `routers/stripe.py` for example)
- Use async/await consistently
- Use existing Database instance from app state
- Keep response format simple and standard
- No authentication required (public health check)

**Testing**:
```bash
# Start API server
cd rivet_pro && python -m adapters.web.main

# Test endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","database":"connected","timestamp":"2026-01-11T..."}
```

---
```

### Step 2: Verify Story is Ready
```bash
cd scripts/ralph-claude-code
cat @fix_plan.md | grep "RIVET-006" -A 20
```

Should show the complete story with all acceptance criteria.

---

## Phase 3: Run Ralph Test

### Step 1: Create Logs Directory
```bash
cd /c/Users/hharp/OneDrive/Desktop/Rivet-PRO
mkdir -p logs
```

### Step 2: Run Ralph Wrapper
```bash
cd scripts/ralph-claude-code

# Run with max 10 iterations (should complete in 1-3)
./ralph-wrapper.sh 10 "RIVET-006"
```

**What to watch for**:
1. Platform detection output
2. Ralph starting message
3. Iteration progress
4. File creation messages
5. Git commit messages
6. Completion/exit signal

### Step 3: Monitor Output
Ralph should:
1. Read PROMPT.md and AGENTS.md
2. Parse @fix_plan.md
3. Find RIVET-006 (first unchecked task)
4. Create `rivet_pro/adapters/web/routers/health.py`
5. Modify `rivet_pro/adapters/web/main.py`
6. Test the endpoint
7. Commit changes
8. Mark task complete in @fix_plan.md
9. Output EXIT_SIGNAL: true

---

## Phase 4: Verify Results

### Verification Checklist

#### 1. File Creation ✓
```bash
# Check health.py exists
ls -la rivet_pro/adapters/web/routers/health.py

# Check content
cat rivet_pro/adapters/web/routers/health.py | head -30
```

**Expected**:
- File exists
- Has proper imports (FastAPI, APIRouter)
- Has GET /health endpoint
- Has database check logic
- Has docstrings

#### 2. Router Registration ✓
```bash
# Check main.py modified
git diff main -- rivet_pro/adapters/web/main.py
```

**Expected**:
- Import health router
- Include health router with prefix

#### 3. Git Commit ✓
```bash
# Check recent commits
git log --oneline -3

# Check commit details
git show HEAD
```

**Expected**:
- Commit message: `feat(RIVET-006): add health check endpoint`
- Files changed: health.py (new), main.py (modified)
- No unexpected changes

#### 4. Task Marked Complete ✓
```bash
# Check @fix_plan.md updated
cat scripts/ralph-claude-code/@fix_plan.md | grep "RIVET-006" -A 2
```

**Expected**: `### ✅ RIVET-006: Health Check Endpoint`

#### 5. Manual Endpoint Test ✓
```bash
# Start server
cd rivet_pro
python -m adapters.web.main &
SERVER_PID=$!
sleep 3

# Test health endpoint
curl http://localhost:8000/health

# Stop server
kill $SERVER_PID
```

**Expected**:
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-01-11T21:45:00Z"
}
```

#### 6. Code Quality ✓
```bash
# Syntax check
python -m py_compile rivet_pro/adapters/web/routers/health.py

# Import check
PYTHONPATH=. python -c "from rivet_pro.adapters.web.routers.health import router; print('OK')"
```

**Expected**: No errors

#### 7. Telegram Notification ✓
- Check Telegram for completion notification
- Should show "✅ STORY COMPLETE - RIVET-006"

---

## Phase 5: Analysis & Report

### Success Criteria
All of these must be TRUE:
- [ ] frankbria installed successfully
- [ ] Ralph wrapper executed without errors
- [ ] health.py file created with correct implementation
- [ ] main.py modified to register health router
- [ ] Git commit created with proper message format
- [ ] @fix_plan.md updated (RIVET-006 marked complete)
- [ ] Manual curl test returned 200 with correct JSON
- [ ] No syntax errors in generated code
- [ ] Code follows existing patterns (async, type hints, docstrings)
- [ ] Completed in ≤10 iterations

### Create Test Report

Create `RALPH_TEST_REPORT.md`:

```markdown
# Ralph Test Report - RIVET-006

**Date**: [Current Date]
**Story**: RIVET-006 - Health Check Endpoint
**Iterations**: [X] / 10
**Duration**: [X] minutes
**Status**: [PASS/FAIL]

## Results

### Installation ✓
- frankbria version: [version]
- Platform detected: windows
- Python command: python

### Execution ✓
- Iterations used: [X]
- Files created: 1 (health.py)
- Files modified: 1 (main.py)
- Commits created: 1
- Exit signal detected: [yes/no]

### Code Quality ✓
- Syntax valid: [yes/no]
- Imports work: [yes/no]
- Follows patterns: [yes/no]
- Has docstrings: [yes/no]
- Type hints: [yes/no]

### Functionality ✓
- Endpoint responds: [yes/no]
- Status code: [200/other]
- JSON valid: [yes/no]
- Database check works: [yes/no]

### Git Integration ✓
- Commit message format: [correct/incorrect]
- Files staged correctly: [yes/no]
- No unexpected changes: [yes/no]

### Documentation ✓
- @fix_plan.md updated: [yes/no]
- Task marked complete: [yes/no]

## Issues Found
[List any issues or unexpected behavior]

## Recommendations
[Suggestions for improvement]

## Conclusion
[Overall assessment - ready for production use?]
```

---

## Alternative Test Stories (if RIVET-006 fails or you want more tests)

### RIVET-007: Version Endpoint
```markdown
### ❌ RIVET-007: Version Info Endpoint

Add `/version` endpoint that returns API version and build info.

**Acceptance Criteria**:
- [ ] Create `rivet_pro/adapters/web/routers/version.py`
- [ ] Return `{"version": "1.0.0", "name": "RIVET Pro API", "build": "git-hash"}`
- [ ] No database dependency (static info)
- [ ] Test with curl
- [ ] Commit as `feat(RIVET-007): add version endpoint`
```

### RIVET-008: Settings Validation Endpoint
```markdown
### ❌ RIVET-008: Settings Validation

Add `/admin/settings/validate` endpoint to check required env vars.

**Acceptance Criteria**:
- [ ] Create `rivet_pro/adapters/web/routers/admin.py`
- [ ] Check presence of TELEGRAM_BOT_TOKEN, DATABASE_URL, ANTHROPIC_API_KEY
- [ ] Return `{"valid": true/false, "missing": [list]}`
- [ ] Test with curl
- [ ] Commit as `feat(RIVET-008): add settings validation endpoint`
```

### RIVET-009: Usage Stats Utility
```markdown
### ❌ RIVET-009: Usage Stats Helper Function

Add utility function to get usage statistics summary.

**Acceptance Criteria**:
- [ ] Create `rivet_pro/core/utils/stats.py`
- [ ] Implement `async def get_usage_summary() -> dict`
- [ ] Return total lookups, active users, pro users count
- [ ] Use UsageService for data
- [ ] Add docstring and type hints
- [ ] Test with simple script
- [ ] Commit as `feat(RIVET-009): add usage stats utility`
```

---

## Debugging Guide

### If Ralph Fails to Start
```bash
# Check ralph is installed
which ralph

# Check workspace is accessible
cd /c/Users/hharp/OneDrive/Desktop/Rivet-PRO

# Check PROMPT.md exists
ls scripts/ralph-claude-code/PROMPT.md

# Check @fix_plan.md exists
ls scripts/ralph-claude-code/@fix_plan.md
```

### If Ralph Doesn't Complete Story
```bash
# Check iteration logs
cat logs/ralph-*.log | tail -100

# Check for errors
cat logs/ralph-*.log | grep -i error

# Check response analysis
cat scripts/ralph-claude-code/.response_analysis
```

### If Code Doesn't Work
```bash
# Check syntax
python -m py_compile rivet_pro/adapters/web/routers/health.py

# Check imports
PYTHONPATH=. python -c "from rivet_pro.adapters.web.routers import health"

# Check database connection
PYTHONPATH=. python -c "import asyncio; from rivet_pro.infra.database import Database; asyncio.run(Database().connect())"
```

### If Git Commit Missing
```bash
# Check git status
git status

# Check recent commits
git log --oneline -5

# Check branch
git branch --show-current
```

---

## Expected Timeline

**Optimistic** (everything works first try):
- Installation: 10 minutes
- Story creation: 5 minutes
- Ralph execution: 5-10 minutes
- Verification: 10 minutes
- Total: ~30-35 minutes

**Realistic** (some troubleshooting):
- Installation: 15 minutes
- Story creation: 5 minutes
- Ralph execution: 10-15 minutes
- Verification: 15 minutes
- Debugging: 15-20 minutes
- Total: ~60-70 minutes

**Worst Case** (multiple retries):
- Installation issues: 30 minutes
- Story tweaking: 10 minutes
- Ralph execution (multiple attempts): 30 minutes
- Verification & debugging: 30 minutes
- Total: ~100 minutes

---

## Success Indicators

You'll know Ralph is working correctly when:
1. ✅ `ralph` command runs without errors
2. ✅ Platform detection shows correct values
3. ✅ Ralph iterates (shows progress in logs)
4. ✅ New file created with valid Python code
5. ✅ Existing file modified correctly
6. ✅ Git commit created automatically
7. ✅ @fix_plan.md updated (checkbox marked)
8. ✅ EXIT_SIGNAL: true appears in logs
9. ✅ Telegram notification received (if configured)
10. ✅ Manual test of feature works

---

## After Successful Test

### 1. Push to GitHub
```bash
git push origin ralph/frankbria-migration
```

### 2. Update PR #7
Add comment to PR with test results:
```
Test execution completed successfully!

**Test Story**: RIVET-006 - Health Check Endpoint
**Result**: PASS ✅
**Iterations**: [X] / 10
**Files**: health.py (created), main.py (modified)
**Commit**: [commit-hash]

All acceptance criteria met. Ralph is production-ready.

See `RALPH_TEST_REPORT.md` for details.
```

### 3. Merge PR
If test passed, merge PR #7 to main.

### 4. Plan Next Stories
Create RIVET-007, RIVET-008, etc. in @fix_plan.md for real feature development.

---

## Questions to Answer in Report

1. **Did frankbria install smoothly on Windows?**
   - Any errors or warnings?
   - Installation time?

2. **Did config.sh detect platform correctly?**
   - Correct PLATFORM value?
   - Correct PYTHON_CMD?
   - Workspace path correct?

3. **Did Ralph understand the story?**
   - Correct files created?
   - Followed acceptance criteria?
   - Used codebase patterns from AGENTS.md?

4. **Was code quality good?**
   - Proper async/await?
   - Type hints?
   - Docstrings?
   - Error handling?

5. **Did git integration work?**
   - Commit created?
   - Message format correct?
   - Files staged properly?

6. **How many iterations did it take?**
   - First try? (ideal)
   - 2-3 tries? (acceptable)
   - 5+ tries? (needs PROMPT.md improvement)

7. **Did Telegram notifications work?**
   - Start notification?
   - Complete notification?
   - Correct story ID in message?

8. **What would you improve?**
   - PROMPT.md clarity?
   - AGENTS.md patterns?
   - Story acceptance criteria?
   - ralph-wrapper.sh features?

---

## Final Checklist

Before ending session:
- [ ] frankbria installed and verified
- [ ] Test story (RIVET-006) created in @fix_plan.md
- [ ] Ralph wrapper executed
- [ ] Story completed (or debugging notes captured)
- [ ] Manual verification performed
- [ ] RALPH_TEST_REPORT.md created
- [ ] Results pushed to GitHub
- [ ] PR #7 updated with test results
- [ ] Next steps identified

---

## TL;DR - Quick Start

```bash
# 1. Install frankbria
cd /c/temp && git clone https://github.com/frankbria/ralph-claude-code.git
cd ralph-claude-code && ./install.sh

# 2. Add RIVET-006 story to @fix_plan.md (health check endpoint)

# 3. Run Ralph
cd /c/Users/hharp/OneDrive/Desktop/Rivet-PRO/scripts/ralph-claude-code
./ralph-wrapper.sh 10 "RIVET-006"

# 4. Verify
curl http://localhost:8000/health

# 5. Report results in RALPH_TEST_REPORT.md
```

**Good luck! This is the moment of truth for the migration.** 🚀
