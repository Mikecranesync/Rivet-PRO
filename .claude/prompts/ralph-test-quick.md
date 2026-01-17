# Ralph Test - Quick Reference

## Context
Ralph migration complete. PR #7 ready. Need to install frankbria and run test.

## Quick Start Commands

```bash
# 1. Install frankbria (10 min)
cd /c/temp
git clone https://github.com/frankbria/ralph-claude-code.git
cd ralph-claude-code && ./install.sh
ralph --version  # Verify

# 2. Add test story to @fix_plan.md (5 min)
cd /c/Users/hharp/OneDrive/Desktop/Rivet-PRO/scripts/ralph-claude-code
# Edit @fix_plan.md - add RIVET-006 (health check endpoint)

# 3. Run Ralph (10 min)
./ralph-wrapper.sh 10 "RIVET-006"

# 4. Verify (5 min)
ls rivet_pro/adapters/web/routers/health.py
git log --oneline -1
curl http://localhost:8000/health

# 5. Report (10 min)
# Create RALPH_TEST_REPORT.md with results
git push origin ralph/frankbria-migration
# Update PR #7 with test results
```

## Test Story: RIVET-006

**Goal**: Add `/health` endpoint for production monitoring

**Files**:
- Create: `rivet_pro/adapters/web/routers/health.py`
- Modify: `rivet_pro/adapters/web/main.py`

**Test**:
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","database":"connected","timestamp":"..."}
```

## Success = All True
- [ ] Ralph installed
- [ ] Story completes in ≤10 iterations
- [ ] health.py created with valid code
- [ ] main.py modified to register router
- [ ] Git commit created
- [ ] @fix_plan.md updated (checkbox marked)
- [ ] curl test returns 200
- [ ] No syntax errors

## If Problems
```bash
# Check logs
cat logs/ralph-*.log | tail -50

# Check Ralph status
cat scripts/ralph-claude-code/.response_analysis

# Manual syntax check
python -m py_compile rivet_pro/adapters/web/routers/health.py
```

## Full Details
See `ralph-test-session.md` for complete instructions.
