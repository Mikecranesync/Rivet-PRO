# Ralph Wiggum Plugin - Complete Installation Guide

This guide walks you through installing the official Ralph Wiggum plugin on both your local Windows machine and your VPS.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Phase 1: Install Locally (Windows)](#phase-1-install-locally-windows)
3. [Phase 2: Install on VPS](#phase-2-install-on-vps)
4. [Phase 3: Testing](#phase-3-testing)
5. [Phase 4: Integration](#phase-4-integration)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Local Windows Machine
- ✅ Claude Code CLI installed (you have this)
- ✅ Git repository (Rivet-PRO)
- ✅ Internet connection
- ✅ Terminal/PowerShell access

### VPS (72.60.175.144)
- ✅ SSH access (configured in `.claude/settings.local.json`)
- ⚠️ Claude Code CLI (we'll install if needed)
- ✅ Rivet-PRO repository
- ✅ Root/sudo access

---

## Phase 1: Install Locally (Windows)

### Step 1.1: Open Claude Code CLI

1. Open your terminal (PowerShell or Command Prompt)
2. Navigate to Rivet-PRO directory:
   ```powershell
   cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
   ```
3. Ensure you're in a Claude Code session

### Step 1.2: Install Ralph Wiggum Plugin

Run this command in Claude Code:
```bash
/plugin install ralph-loop@claude-plugins-official
```

**Expected Output:**
```
Installing ralph-loop@claude-plugins-official...
✓ Plugin installed successfully
```

**Possible Issues:**
- **Error: "plugin not found"** → Check spelling, ensure `@claude-plugins-official`
- **Error: "permission denied"** → Run as administrator
- **Error: "network error"** → Check internet connection

### Step 1.3: Verify Installation

```bash
/plugin list
```

**Expected Output:**
You should see `ralph-loop` in the list:
```
Installed plugins:
- ralph-loop@claude-plugins-official
- [other plugins if any]
```

### Step 1.4: Simple Hello World Test

Test that Ralph works:
```bash
/ralph-loop "Create a file called test_ralph.txt with the text 'Ralph Wiggum works!'" --completion-promise "file created" --max-iterations 2
```

**What Ralph will do:**
1. Create the file
2. Write the text
3. Verify file exists
4. Report completion

**Verify:**
```powershell
type test_ralph.txt
```

Should output: `Ralph Wiggum works!`

### Step 1.5: Rivet Pro Context Test

Test Ralph with actual Rivet Pro code:
```bash
/ralph-loop "Read rivet_pro/config/settings.py and list all environment variables in a file called env_vars.md" --completion-promise "list complete" --max-iterations 3
```

**What Ralph will do:**
1. Read `rivet_pro/config/settings.py`
2. Extract environment variable names
3. Create `env_vars.md` with the list
4. Report completion

**Verify:**
```powershell
type env_vars.md
```

Should show a markdown list of all env vars.

### ✅ Local Installation Complete!

If both tests passed, Ralph is working on your local machine.

---

## Phase 2: Install on VPS

### Step 2.1: Connect to VPS

From your local machine (you can use Claude Code's Bash tool):
```bash
ssh root@72.60.175.144
```

**Note:** Your SSH credentials are already configured in `.claude/settings.local.json`, so this should work without password prompt.

### Step 2.2: Verify Claude Code on VPS

Once connected to VPS, check if Claude Code is installed:
```bash
which claude
```

**If Claude Code is installed:**
```
/usr/local/bin/claude
```
→ Skip to Step 2.4

**If Claude Code is NOT installed:**
```
[no output or "claude not found"]
```
→ Continue to Step 2.3

### Step 2.3: Install Claude Code on VPS (if needed)

Run the official installer:
```bash
curl -fsSL https://claude.ai/install.sh | sh
```

**Follow prompts:**
1. Accept the license
2. Choose installation directory (default: /usr/local/bin)
3. Wait for installation to complete

**Verify installation:**
```bash
claude --version
```

Should show version number.

### Step 2.4: Navigate to Rivet-PRO Directory

```bash
cd ~/Rivet-PRO
pwd  # Should show: /root/Rivet-PRO (or wherever it's located)
ls   # Verify you see rivet_pro/, scripts/, etc.
```

**If Rivet-PRO doesn't exist on VPS:**
```bash
git clone [your-repo-url] ~/Rivet-PRO
cd ~/Rivet-PRO
```

### Step 2.5: Start Claude Code Session (on VPS)

```bash
claude
```

This starts an interactive Claude Code session on the VPS.

### Step 2.6: Install Ralph Plugin on VPS

In the Claude Code session on VPS:
```bash
/plugin install ralph-loop@claude-plugins-official
```

**Expected Output:**
```
Installing ralph-loop@claude-plugins-official...
✓ Plugin installed successfully
```

### Step 2.7: Verify Installation on VPS

```bash
/plugin list
```

Should show `ralph-loop@claude-plugins-official`.

### Step 2.8: Test Ralph on VPS

Simple test to confirm it works:
```bash
/ralph-loop "Create a test file at /tmp/ralph_vps_test.txt with content 'Ralph works on VPS!'" --completion-promise "file created" --max-iterations 2
```

**Verify (in VPS shell):**
```bash
cat /tmp/ralph_vps_test.txt
```

Should output: `Ralph works on VPS!`

### Step 2.9: Test Ralph with Rivet Pro on VPS

```bash
/ralph-loop "Count the number of Python files in rivet_pro/ and save to /tmp/python_file_count.txt" --completion-promise "count saved" --max-iterations 3
```

**Verify:**
```bash
cat /tmp/python_file_count.txt
```

Should show the count of .py files.

### ✅ VPS Installation Complete!

Ralph is now working on both your local machine and VPS.

---

## Phase 3: Testing

### Test 3.1: Factorial Function (Local)

```bash
/ralph-loop "Create a Python file test_factorial.py with a recursive factorial function and test it with factorial(5) == 120. Print the result." --completion-promise "test passes" --max-iterations 5
```

**What to check:**
- [ ] `test_factorial.py` created
- [ ] Function works correctly
- [ ] Test passes
- [ ] Output shows `120`

### Test 3.2: Add Telegram Command (Local)

```bash
/ralph-loop "In rivet_pro/bot/, find where commands are defined and describe the pattern in command_pattern.md" --completion-promise "pattern documented" --max-iterations 3
```

**What to check:**
- [ ] `command_pattern.md` created
- [ ] Describes how commands work
- [ ] Lists example command handlers

### Test 3.3: Cost Control Test (Local)

Test that max-iterations works:
```bash
/ralph-loop "Count to 1000 and save each number to count.txt, one per line" --completion-promise "counted to 1000" --max-iterations 2
```

**Expected:**
- Ralph will run for 2 iterations
- Will NOT complete (not enough iterations)
- Will stop gracefully after 2 iterations

This confirms cost control is working.

### Test 3.4: Database Test (VPS)

**Only if you want to test database access:**
```bash
/ralph-loop "Connect to Supabase using credentials in .env and query users table to count total users. Save to /tmp/user_count.txt" --completion-promise "count saved" --max-iterations 5
```

**What to check:**
- [ ] Connects to database
- [ ] Query executes
- [ ] Count saved to file

⚠️ **Warning:** This accesses production database. Only run if comfortable.

---

## Phase 4: Integration

### Option A: Keep Both Systems (Recommended)

You now have both systems available:

**Custom System (`scripts/ralph/`):**
- Use for structured PRD work (RIVET-004, RIVET-005)
- Has all your custom features
- Proven track record

**Official Plugin (`scripts/ralph-wiggum/`):**
- Use for ad-hoc tasks
- Use for quick bug fixes
- Use for testing new features

**No changes needed** - they coexist peacefully.

### Option B: Start Migration

If you prefer the official plugin:

1. **Finish current PRD** with custom system:
   ```bash
   cd scripts/ralph
   ./ralph.sh 10
   ```

2. **Test thoroughly** with official plugin:
   - Run 5-10 different tasks
   - Document any issues
   - Compare quality

3. **Decide** based on results:
   - Update `COMPARISON.md` with findings
   - Make informed decision

---

## Phase 5: Using Ralph Wiggum

### Quick Tasks

```bash
# Direct command
/ralph-loop "task" --completion-promise "done" --max-iterations 5

# Using wrapper (easier)
cd scripts/ralph-wiggum
./run-ralph.sh "task" "done" 5
```

### Medium Tasks

```bash
./run-ralph.sh "Create service and migration" "tests pass" 10 1800
```

### Complex Features

1. **Plan first:** Use `prd_template.md`
2. **Run Ralph:**
   ```bash
   ./run-ralph.sh "detailed task from PRD" "completion criteria" 20 3600
   ```
3. **Review results**
4. **Document learnings**

---

## Troubleshooting

### Issue: "Command /ralph-loop not found"

**Solution:**
- Plugin not installed correctly
- Run: `/plugin install ralph-loop@claude-plugins-official`
- Verify: `/plugin list`

### Issue: Ralph runs but doesn't complete

**Possible causes:**
1. **Completion promise too strict**
   - Make it more general: "done" instead of "all tests pass"
2. **Not enough iterations**
   - Increase --max-iterations
3. **Task too complex**
   - Break into smaller tasks

### Issue: Ralph makes mistakes

**Solutions:**
- **More detail in task description:** "In rivet_pro/bot/handlers.py, find _handle_photo function and..."
- **Reference existing patterns:** "Follow the pattern in usage_service.py"
- **Be specific about testing:** "Test with a sample photo upload and verify response"

### Issue: Can't install on VPS

**Possible causes:**
1. **Claude Code not installed**
   - Install: `curl -fsSL https://claude.ai/install.sh | sh`
2. **Permission issues**
   - Run as root: `sudo claude`
3. **Network issues**
   - Check internet connection
   - Check firewall rules

### Issue: Costs too high

**Solutions:**
1. **Lower max-iterations:** Start with 5, increase if needed
2. **Add timeout:** `--timeout 600` (10 minutes)
3. **Use haiku for simple tasks:** `--model claude-3-haiku` (cheaper)
4. **Break tasks smaller:** Multiple small tasks cost less than one huge task

---

## Success Checklist

### Local Installation
- [ ] Plugin installed (`/plugin list` shows it)
- [ ] Hello world test passed
- [ ] Rivet Pro context test passed
- [ ] Can run Ralph commands
- [ ] Wrapper script works

### VPS Installation
- [ ] SSH connection works
- [ ] Claude Code installed
- [ ] Plugin installed
- [ ] VPS test passed
- [ ] Can run Ralph on VPS

### Integration
- [ ] Both systems coexist
- [ ] Understand when to use each
- [ ] Documentation complete
- [ ] Team knows how to use

---

## Quick Commands Reference

### Local

**Install:**
```bash
/plugin install ralph-loop@claude-plugins-official
```

**Verify:**
```bash
/plugin list
```

**Simple task:**
```bash
/ralph-loop "task" --completion-promise "done" --max-iterations 5
```

**Using wrapper:**
```bash
cd scripts/ralph-wiggum
./run-ralph.sh "task" "done" 5
```

### VPS

**Connect:**
```bash
ssh root@72.60.175.144
```

**Navigate:**
```bash
cd ~/Rivet-PRO
```

**Start Claude:**
```bash
claude
```

**Install plugin:**
```bash
/plugin install ralph-loop@claude-plugins-official
```

**Run task:**
```bash
/ralph-loop "task" --completion-promise "done" --max-iterations 5
```

---

## Next Steps

After installation:

1. **Read examples.md** - See common Rivet Pro tasks
2. **Try simple task** - Get comfortable with syntax
3. **Test with real feature** - Add a small feature
4. **Document findings** - Update COMPARISON.md
5. **Decide on approach** - Migrate, parallel, or stay custom

---

## Support

**Official Resources:**
- GitHub: https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum
- Docs: https://github.com/anthropics/claude-code/blob/main/plugins/README.md
- Blog: https://paddo.dev/blog/ralph-wiggum-autonomous-loops/

**Local Resources:**
- README: `scripts/ralph-wiggum/README.md`
- Examples: `scripts/ralph-wiggum/examples.md`
- PRD Template: `scripts/ralph-wiggum/prd_template.md`
- Comparison: `scripts/ralph-wiggum/COMPARISON.md`

**Getting Help:**
- Check troubleshooting section above
- Review examples for similar tasks
- Start with simpler task to build confidence

---

**Installation complete! You're ready to use Ralph Wiggum for autonomous development on Rivet Pro.**
