# Ralph Wiggum - Quick Start

## 60 Second Setup

### 1. Install Plugin (Local)
```bash
/plugin install ralph-loop@claude-plugins-official
```

### 2. Verify
```bash
/plugin list
```

### 3. Test
```bash
/ralph-loop "Create test.txt with 'Hello Ralph'" --completion-promise "file created" --max-iterations 2
```

### 4. Check Result
```powershell
type test.txt
```

**✅ You're done! Ralph is installed and working.**

---

## First Real Task

```bash
cd scripts/ralph-wiggum
./run-ralph.sh "Add /ping command to Telegram bot" "command works" 5
```

Ralph will:
- Read the bot code
- Add the /ping command
- Test it
- Report completion

---

## What Next?

**Learn by Example:**
- Read `examples.md` for common Rivet Pro tasks
- Start with simple tasks (3-5 iterations)
- Gradually increase complexity

**Plan Features:**
- Use `prd_template.md` for complex features
- Define clear completion criteria
- Estimate iterations needed

**Compare Systems:**
- Read `COMPARISON.md` to understand custom vs official
- Try both systems in parallel
- Decide which fits your workflow

**Full Installation:**
- See `INSTALLATION_GUIDE.md` for VPS setup
- Learn all cost control options
- Troubleshooting tips

---

## Cost Control

**Always set limits:**
```bash
--max-iterations 10      # Required!
--timeout 1800           # 30 minutes
```

**Start conservative:**
- Simple tasks: 5 iterations
- Medium tasks: 10 iterations
- Complex tasks: 20 iterations

---

## Commands

**Direct:**
```bash
/ralph-loop "task" --completion-promise "done" --max-iterations 5
```

**Using Wrapper (Easier):**
```bash
./run-ralph.sh "task" "done" 5
```

---

## Files Created

All configuration is in `scripts/ralph-wiggum/`:

- **QUICKSTART.md** (this file) - 60-second setup
- **README.md** - Overview and basics
- **INSTALLATION_GUIDE.md** - Full local + VPS setup
- **examples.md** - Rivet Pro task examples
- **prd_template.md** - Feature planning template
- **COMPARISON.md** - Custom vs official plugin
- **run-ralph.sh** - Cost control wrapper script

---

## Quick Tips

✅ **Be specific:** "Add /ping command to rivet_pro/bot/commands.py"
✅ **Test requirements:** "Test manually with Telegram"
✅ **Clear success:** "tests pass and command works"
❌ **Too vague:** "Make the bot better"
❌ **No limits:** Never skip --max-iterations
❌ **Too strict:** "Absolutely perfect with zero bugs"

---

## Your Systems

You now have **two Ralph systems**:

**Custom (`scripts/ralph/`):**
- Structured PRD workflow
- 3 completed stories
- 2 pending (RIVET-004, RIVET-005)
- Use for: Finishing current PRD

**Official (`scripts/ralph-wiggum/`):**
- Command-line based
- Just installed
- Testing phase
- Use for: New tasks, experimentation

**Both work!** Use whichever fits the task.

---

## Support

- **Examples:** `examples.md`
- **Full guide:** `INSTALLATION_GUIDE.md`
- **Comparison:** `COMPARISON.md`
- **Official docs:** https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum

**Ready to code autonomously! 🚀**
