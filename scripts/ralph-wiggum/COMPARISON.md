# Custom scripts/ralph/ vs Official Ralph Wiggum Plugin

## Executive Summary

This document compares the existing custom Ralph system (`scripts/ralph/`) with the official Anthropic Ralph Wiggum plugin to help decide the best path forward.

**Current Status (as of 2026-01-11):**
- Custom system has completed 3 of 5 stories in Phase 1 MVP
- 2 stories remaining (RIVET-004: Shorten prompts, RIVET-005: Remove n8n footer)
- Custom system is working and stable

---

## Custom System (scripts/ralph/)

### Overview
- **Tool:** Uses `amp` CLI
- **Script:** `ralph.sh` (bash loop, max 10 iterations)
- **PRD:** `prd.json` (JSON format with user stories)
- **Instructions:** `prompt.md` (detailed agent instructions)
- **Progress:** `progress.txt` (manual progress logging)

### Pros
✅ **Already Working** - 3 completed stories, proven track record
✅ **Customized Workflow** - Tailored for Rivet Pro patterns
✅ **Archive System** - Auto-archives when branch changes
✅ **Progress Tracking** - progress.txt documents learnings
✅ **Quality Checks** - Built-in Python syntax, import, migration checks
✅ **Telegram Testing** - Mandatory bot testing before commit
✅ **Git Integration** - Automatic commits with structured messages
✅ **Codebase Patterns** - Accumulates knowledge in progress.txt
✅ **PRD Structure** - Clear user story format with acceptance criteria
✅ **AGENTS.md Integration** - Updates local documentation

### Cons
❌ **Not Official** - Custom implementation, no official support
❌ **Manual Iteration** - Fixed 10 iteration limit, runs in loop
❌ **No Cost Controls** - Relies on iteration limit only
❌ **Limited to amp CLI** - Tied to specific tool
❌ **Custom Maintenance** - Need to maintain the tooling ourselves
❌ **No Timeout Protection** - Could run indefinitely if amp hangs

### Current Progress

| Story | Status | Notes |
|-------|--------|-------|
| RIVET-001: Usage Tracking | ✅ Complete | Migration, service, bot integration |
| RIVET-002: Stripe Payment | ✅ Complete | Checkout, webhooks, /upgrade command |
| RIVET-003: Free Tier Limits | ✅ Complete | Limit enforcement, inline checkout |
| RIVET-004: Shorten Prompts | ❌ Pending | 50% reduction target |
| RIVET-005: Remove n8n Footer | ❌ Pending | Clean messaging |

---

## Official Plugin (ralph-wiggum)

### Overview
- **Tool:** Claude Code plugin system
- **Command:** `/ralph-loop`
- **Installation:** `/plugin install ralph-loop@claude-plugins-official`
- **Repository:** https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum

### Pros
✅ **Official Support** - Built and maintained by Anthropic
✅ **Built-in Cost Controls** - `--max-iterations` and `--timeout` flags
✅ **Claude Code Integration** - Native integration with Claude Code
✅ **Community Support** - Active development and community
✅ **Better Error Handling** - Robust error handling built-in
✅ **Model Selection** - Choose specific Claude models
✅ **Temperature Control** - Fine-tune creativity vs consistency
✅ **No Loop Management** - Runs autonomously until completion
✅ **Completion Promise** - Clear success criteria

### Cons
❌ **New Workflow** - Need to learn and adapt
❌ **No Progress Tracking** - Need to implement our own
❌ **No Archive System** - Need to build if wanted
❌ **No PRD Format** - Freeform task description
❌ **No Quality Checks** - Need to add Rivet Pro specific checks
❌ **No Git Integration** - Doesn't auto-commit (need to add)
❌ **Different Syntax** - Command-line args vs config files
❌ **Learning Curve** - Team needs to learn new approach

---

## Feature Comparison

| Feature | Custom Ralph | Official Plugin | Winner |
|---------|-------------|----------------|--------|
| **Official Support** | ❌ None | ✅ Anthropic | **Official** |
| **Cost Controls** | ⚠️ Manual (iteration limit) | ✅ Built-in (--max-iterations, --timeout) | **Official** |
| **Progress Tracking** | ✅ progress.txt with learnings | ⚠️ DIY | **Custom** |
| **Branch Archiving** | ✅ Auto-archives on branch change | ⚠️ DIY | **Custom** |
| **Quality Checks** | ✅ Python syntax, imports, migrations | ⚠️ DIY | **Custom** |
| **Git Integration** | ✅ Auto-commits with structured messages | ⚠️ DIY | **Custom** |
| **PRD Structure** | ✅ JSON with user stories | ⚠️ Freeform | **Custom** |
| **Telegram Testing** | ✅ Mandatory before commit | ⚠️ DIY | **Custom** |
| **Codebase Patterns** | ✅ Accumulated in progress.txt | ⚠️ DIY | **Custom** |
| **Integration** | ✅ amp CLI | ✅ Claude Code | **Tie** |
| **Learning Curve** | ✅ Already know | ⚠️ New syntax | **Custom** |
| **Error Handling** | ⚠️ Basic | ✅ Robust | **Official** |
| **Model Selection** | ⚠️ Default only | ✅ Choose any model | **Official** |
| **Temperature** | ⚠️ Not configurable | ✅ Configurable | **Official** |
| **Documentation** | ✅ Detailed in prompt.md | ✅ Official docs | **Tie** |

**Score:** Custom 8, Official 4, Tie 2

---

## Decision Matrix

### Option 1: Migrate to Official (Long-term Recommendation)

**When:**
- After completing existing PRD (RIVET-004, RIVET-005)
- After testing official plugin with simple tasks
- After confirming it meets our needs

**How:**
1. Finish remaining 2 stories with custom system
2. Test official plugin with simple Rivet Pro tasks
3. Port useful features:
   - Progress tracking → add to wrapper script
   - Quality checks → add to wrapper script
   - Git integration → add commit hooks
4. Archive `scripts/ralph/` → `scripts/ralph-archive/`
5. Move future development to official plugin

**Pros:**
- Official support and updates
- Better cost controls
- Community improvements
- Future-proof

**Cons:**
- Migration effort
- Need to rebuild features
- Team learning curve

**Estimated Effort:** 2-3 days

---

### Option 2: Keep Both (Recommended for Testing)

**When:**
- During evaluation period (now)
- Testing official plugin capabilities
- Completing existing PRD

**How:**
```
scripts/
├── ralph/              # Custom (for existing PRD)
│   ├── prd.json
│   ├── prompt.md
│   ├── ralph.sh
│   └── progress.txt
└── ralph-wiggum/       # Official (for new tasks & testing)
    ├── README.md
    ├── examples.md
    ├── prd_template.md
    ├── run-ralph.sh
    └── COMPARISON.md
```

**Use Cases:**
- **Custom:** Finish RIVET-004 and RIVET-005 (known, structured PRD)
- **Official:** Quick ad-hoc tasks, bug fixes, simple features

**Pros:**
- No disruption to existing work
- Test official plugin without commitment
- Keep proven system operational
- Best of both worlds

**Cons:**
- Maintain two systems
- Potential confusion
- More complexity

**Estimated Effort:** 0 days (already implemented)

---

### Option 3: Stay Custom

**When:**
- Official plugin doesn't meet needs after testing
- Custom system has unique features we can't replicate
- Team prefers current workflow

**How:**
1. Test official plugin thoroughly
2. Document gaps/issues
3. Decide custom system is better fit
4. Continue using scripts/ralph/
5. Enhance custom system as needed

**Pros:**
- No migration
- Keep all existing features
- Proven track record

**Cons:**
- No official support
- Maintenance burden
- Miss out on improvements

**Estimated Effort:** 0 days

---

## Test Plan

Before making a decision, test the official plugin:

### 1. Simple Task Test
```bash
/ralph-loop "Create a Python function that calculates factorial" \
  --completion-promise "test passes" \
  --max-iterations 5
```

**Evaluate:**
- Does it complete successfully?
- How many iterations did it take?
- Quality of generated code?

### 2. Rivet Pro Task Test
```bash
/ralph-loop "Add /ping command to Telegram bot that replies 'Pong!'" \
  --completion-promise "command works" \
  --max-iterations 5
```

**Evaluate:**
- Does it understand Rivet Pro structure?
- Does it follow our patterns?
- Does it test properly?

### 3. Complex Task Test
```bash
/ralph-loop "Create database migration and service for user preferences" \
  --completion-promise "migration and service complete" \
  --max-iterations 15
```

**Evaluate:**
- Can it handle multi-step features?
- Does it create quality migrations?
- Does it follow our conventions?

### 4. Cost & Time Analysis
- Track total iterations used
- Track total time taken
- Estimate API costs
- Compare with custom system

---

## Recommendations

### Immediate (Next 1-2 weeks)
1. **✅ Install official plugin** (local + VPS)
2. **✅ Run simple tests** (hello world, factorial)
3. **✅ Test with Rivet Pro** (add /ping command)
4. **✅ Document findings** (update this file)
5. **⏳ Complete RIVET-004 and RIVET-005** with custom system

### Short-term (Next 1 month)
1. **Use both systems in parallel**
   - Custom: Structured PRD work
   - Official: Ad-hoc tasks, quick fixes
2. **Build missing features for official plugin**
   - Progress tracking in wrapper
   - Quality checks in wrapper
   - Git commit hooks
3. **Evaluate which works better** for team

### Long-term (Next 3 months)
1. **Decide on migration** or staying custom
2. If migrating:
   - Port all features
   - Archive custom system
   - Update team documentation
3. If staying:
   - Enhance custom system
   - Add missing features
   - Document decision

---

## Success Criteria for Official Plugin

The official plugin should be adopted if it:

✅ Completes tasks with similar quality to custom system
✅ Costs are reasonable (within 2x of custom system)
✅ Can be extended with our required features (progress, quality checks)
✅ Team finds it easier to use
✅ Provides better long-term maintainability
✅ Official support adds value

If **all criteria met** → Migrate
If **some criteria met** → Keep both
If **few criteria met** → Stay custom

---

## Notes

### Current Situation (2026-01-11)
- Custom system: **Working well**, 3/5 stories complete
- Official plugin: **Not yet tested**
- Decision: **Postponed until after testing**

### Next Review Date
**2026-01-25** (2 weeks from now)

After testing, update this document with:
- Test results
- Performance comparison
- Cost analysis
- Final recommendation

---

## Quick Reference

**Custom System Command:**
```bash
cd scripts/ralph
./ralph.sh 10  # max 10 iterations
```

**Official Plugin Command:**
```bash
cd scripts/ralph-wiggum
./run-ralph.sh "task" "promise" 10
```

**Both Installed:**
```
scripts/
├── ralph/              # Custom (proven)
└── ralph-wiggum/       # Official (testing)
```

Use whichever fits the task best during evaluation period.
