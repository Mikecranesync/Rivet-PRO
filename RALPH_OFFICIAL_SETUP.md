# Official RALPH Setup - Complete

## ✅ Setup Complete

### 1. Repository Forked
- **Original**: snarktank/ralph
- **Fork**: Mikecranesync/ralph
- **Cloned**: `ralph-temp/` directory

### 2. Scripts Installed
All RALPH files copied to `scripts/ralph/`:
- `ralph.sh` - Main bash loop (Windows-compatible fix applied)
- `prompt.md` - Customized for RIVET Pro
- `prd.json` - 5 RIVET stories configured
- `prd.json.example` - Reference

### 3. PRD Created with 5 Stories

**Branch**: `ralph/mvp-phase1`

| Story ID | Title | Priority | AI Model |
|----------|-------|----------|----------|
| RIVET-001 | Usage Tracking System | 1 | Sonnet 4 |
| RIVET-002 | Stripe Payment Integration | 2 | Sonnet 4 |
| RIVET-003 | Free Tier Limit Enforcement | 3 | Sonnet 4 |
| RIVET-004 | Shorten System Prompts | 4 | Haiku |
| RIVET-005 | Remove n8n Footer | 5 | Haiku |

### 4. Amp CLI Installed
- **Version**: 0.0.1768075257-g6dc6d4
- **Location**: `/c/Users/hharp/.amp/bin/amp.exe`
- **Status**: Authenticated ✅

### 5. prompt.md Customized for RIVET Pro

Added project-specific context:
- Repository path: `C:\Users\hharp\OneDrive\Desktop\Rivet-PRO`
- Tech stack: Python, Supabase, Telegram, Claude API
- Database credentials from .env
- Telegram bot token and chat ID
- Python quality checks (syntax, imports, migrations)
- Telegram bot testing requirements

---

## ⚠️ Blocker: Amp Credits Required

RALPH is configured and ready, but **Amp requires credits** to run.

**Error**: `Error: Insufficient credit balance.`

### Add Credits

1. Go to [ampcode.com/settings](https://ampcode.com/settings)
2. Navigate to billing/credits section
3. Add credits to your account
4. Return and run RALPH

---

## 🚀 Running RALPH (Once Credits Added)

```bash
cd "C:\Users\hharp\OneDrive\Desktop\Rivet-PRO"
./scripts/ralph/ralph.sh 10
```

### What RALPH Will Do

**Iteration 1**:
1. Read `scripts/ralph/prd.json`
2. Create branch `ralph/mvp-phase1`
3. Pick RIVET-001 (Usage Tracking System)
4. Implement the story using Claude via Amp
5. Run quality checks (Python syntax, imports)
6. Test with Telegram bot locally
7. Commit: `feat: RIVET-001 - Usage Tracking System`
8. Update prd.json → `"passes": true`
9. Append to `scripts/ralph/progress.txt`

**Iterations 2-5**: Repeat for RIVET-002, 003, 004, 005

**Completion**: When all stories have `passes: true`, RALPH outputs `<promise>COMPLETE</promise>` and exits.

---

## 📊 Progress Monitoring

### Check Current Status
```bash
# See which stories are done
cat scripts/ralph/prd.json | grep -A 2 '"id"'

# View progress log
cat scripts/ralph/progress.txt

# Check git commits
git log --oneline -10

# Check current branch
git branch --show-current
```

### Progress Files
- `scripts/ralph/prd.json` - Updated after each story
- `scripts/ralph/progress.txt` - Learnings from each iteration
- `scripts/ralph/.last-branch` - Tracks current branch
- `scripts/ralph/archive/` - Previous runs

---

## 🔧 Architecture

### Official RALPH vs Custom n8n Approach

**Official RALPH (Now Using)**:
- ✅ Bash script loop spawning fresh Amp instances
- ✅ State in prd.json + progress.txt + git history
- ✅ Each iteration = clean context window
- ✅ Battle-tested, official implementation
- ✅ Direct Claude API access via Amp
- ⚠️ Requires Amp credits

**Custom n8n Approach (Previously Built)**:
- n8n workflows with 19 nodes
- Supabase database tracking
- Webhook triggers
- Telegram notifications via n8n
- Database issues blocked progress

**Files Available**:
- `setup_ralph_supabase.sql` - Migration (can still use for reference)
- `ralph_main_loop_supabase.json` - n8n workflow (archived)
- `RALPH_SETUP_COMPLETE.md` - n8n setup guide (archived)

---

## 💰 Cost Estimate

**Per Full Run** (all 5 stories):
- RIVET-001, 002, 003 (Sonnet 4): ~30,000 tokens
- RIVET-004, 005 (Haiku): ~3,500 tokens
- **Total**: ~33,500 tokens
- **Estimated Cost**: $0.28 per run

Plus Amp credits (check ampcode.com pricing).

---

## 🎯 Next Steps

1. **Add Amp credits** at ampcode.com/settings
2. **Run RALPH**: `./scripts/ralph/ralph.sh 10`
3. **Monitor progress** via git commits and progress.txt
4. **Review code** after each story completes
5. **Test features** implemented by RALPH
6. **Iterate** if changes needed (update prd.json and re-run)

---

## Files Created

| File | Purpose |
|------|---------|
| `scripts/ralph/ralph.sh` | Main RALPH loop (Windows-compatible) |
| `scripts/ralph/prompt.md` | Agent instructions (RIVET Pro customized) |
| `scripts/ralph/prd.json` | 5 RIVET stories queue |
| `scripts/ralph/prd.json.example` | Format reference |
| `RALPH_OFFICIAL_SETUP.md` | This file - setup summary |

---

## Troubleshooting

**"Insufficient credit balance"**:
- Add credits at ampcode.com/settings

**"jq: command not found"**:
- Install jq: `choco install jq` (Windows) or `brew install jq` (macOS)

**"Permission denied" on ralph.sh**:
- Run: `chmod +x scripts/ralph/ralph.sh`

**Branch issues**:
- Manually create: `git checkout -b ralph/mvp-phase1`

**Quality checks failing**:
- Fix issues manually and re-run RALPH
- RALPH will skip completed stories (passes: true)

---

Ready to run once Amp credits are added!
