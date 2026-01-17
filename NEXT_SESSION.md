# Next Session: Ralph Test Implementation

## 🎯 Mission
Install frankbria/ralph-claude-code and run a comprehensive test with RIVET-006 (health check endpoint).

## 📍 Current Status
- ✅ Migration complete (13 files, 2,024 lines)
- ✅ Smoke tested (all components working)
- ✅ PR #7 created and ready
- ⏳ frankbria NOT yet installed
- ⏳ Test story NOT yet run

## 🚀 Quick Start (30-60 minutes)

### Option 1: Use Quick Reference
```bash
cd /c/Users/hharp/OneDrive/Desktop/Rivet-PRO
cat .claude/prompts/ralph-test-quick.md
# Follow the 5 quick steps
```

### Option 2: Full Guided Session
```bash
cd /c/Users/hharp/OneDrive/Desktop/Rivet-PRO
cat .claude/prompts/ralph-test-session.md
# Follow the comprehensive 5-phase guide
```

### Option 3: Tell Claude
```
Read .claude/prompts/ralph-test-session.md and execute the test plan.
Install frankbria, add RIVET-006 story, run Ralph, and verify results.
Create RALPH_TEST_REPORT.md with findings.
```

## 📋 Test Story Overview

**RIVET-006: Health Check Endpoint**
- **Type**: Real feature (production monitoring)
- **Scope**: Create 1 file, modify 1 file
- **Complexity**: Simple (health check pattern)
- **Verification**: curl test returns JSON
- **Time**: Should complete in 1-3 Ralph iterations

**Why this test?**
- Small enough to complete quickly
- Real code change (not hello-world)
- Highly verifiable (HTTP endpoint)
- Uses database (tests pattern knowledge)
- Safe (no impact on existing features)
- Valuable (actually needed for prod)

## 🎓 What This Tests

### Ralph Components
1. **PROMPT.md** - Agent understands RIVET Pro context
2. **AGENTS.md** - Agent uses discovered patterns
3. **@fix_plan.md** - Agent parses markdown tasks
4. **config.sh** - Platform detection works
5. **notify.py** - Telegram notifications sent
6. **ralph-wrapper.sh** - Orchestration works
7. **Git integration** - Commits created correctly

### Code Quality
1. Syntax valid
2. Imports work
3. Follows existing patterns
4. Has type hints
5. Has docstrings
6. Error handling

### Workflow
1. Task selection
2. Implementation
3. Testing
4. Committing
5. Status reporting
6. EXIT_SIGNAL detection

## ✅ Success Criteria

All must be TRUE:
- [ ] frankbria installed (`ralph --version` works)
- [ ] Story completes in ≤10 iterations
- [ ] `rivet_pro/adapters/web/routers/health.py` created
- [ ] `rivet_pro/adapters/web/main.py` modified
- [ ] Git commit created with format `feat(RIVET-006): ...`
- [ ] `@fix_plan.md` updated (RIVET-006 checkbox marked)
- [ ] `curl http://localhost:8000/health` returns 200
- [ ] Response JSON has correct structure
- [ ] No syntax errors
- [ ] EXIT_SIGNAL: true detected

## 📊 Expected Output

### Terminal
```
================================================
Ralph Configuration
================================================
Platform:     windows
Python:       python (3.11.x)
...
Running Ralph (max 10 calls)...

[Iteration 1]
Reading @fix_plan.md...
Found task: RIVET-006
Creating health.py...
Modifying main.py...
Testing endpoint...
Committing changes...

---RALPH_STATUS---
STATUS: COMPLETE
EXIT_SIGNAL: true
---
```

### Files Created
```
rivet_pro/adapters/web/routers/health.py  (~50 lines)
```

### Files Modified
```
rivet_pro/adapters/web/main.py  (+2 lines: import + include router)
scripts/ralph-claude-code/@fix_plan.md  (checkbox marked)
```

### Git
```
feat(RIVET-006): add health check endpoint

- Create health router with GET /health endpoint
- Check database connectivity
- Return JSON status and timestamp
- Register router in main.py
```

## 🐛 Common Issues

### Installation
```bash
# If ralph not found after install
source ~/.bashrc
which ralph
```

### Execution
```bash
# If Ralph won't start
cd scripts/ralph-claude-code
ls -la PROMPT.md @fix_plan.md  # Verify files exist
```

### Verification
```bash
# If endpoint doesn't respond
python -m rivet_pro.adapters.web.main &  # Start server first
sleep 3
curl http://localhost:8000/health
```

## 📝 Deliverables

After test completes, you should have:

1. **RALPH_TEST_REPORT.md** - Test results
2. **Working endpoint** - Health check responding
3. **Git commits** - In ralph/frankbria-migration branch
4. **Updated PR #7** - With test results comment
5. **Learnings** - What worked, what didn't

## 🔄 Next Steps After Test

### If Test PASSES ✅
1. Push commits to GitHub
2. Update PR #7 with test results
3. Merge PR #7 to main
4. Install frankbria on VPS (72.60.175.144)
5. Create RIVET-007, RIVET-008 for real development
6. Start using Ralph for production feature work

### If Test FAILS ❌
1. Capture errors in RALPH_TEST_REPORT.md
2. Identify root cause (installation? story? PROMPT?)
3. Fix the issue
4. Re-run test
5. Update prompts/documentation based on learnings

## 📚 Reference Files

- `.claude/prompts/ralph-test-session.md` - Full guide (700+ lines)
- `.claude/prompts/ralph-test-quick.md` - Quick reference
- `scripts/ralph-claude-code/PROMPT.md` - Agent instructions
- `scripts/ralph-claude-code/AGENTS.md` - Codebase patterns
- `scripts/ralph-archive/2026-01-11-amp-ralph/README.md` - Migration history
- `.claude/plans/magical-yawning-wind.md` - Migration plan

## 🎬 Start Command

```bash
# Copy and paste this into Claude:
Read .claude/prompts/ralph-test-session.md and execute Phase 1-5.
Install frankbria, create RIVET-006 story, run Ralph, verify results,
and create RALPH_TEST_REPORT.md. Report findings.
```

---

**Ready to prove Ralph works! 🚀**

**Estimated Time**: 30-60 minutes
**Difficulty**: Medium (new tool, clear instructions)
**Impact**: High (validates entire migration)

Good luck! 🍀
