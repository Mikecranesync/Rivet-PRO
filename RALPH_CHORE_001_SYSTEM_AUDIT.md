# RALPH CHORE 001: RIVET Pro System Status Audit

You are auditing the RIVET Pro codebase to create a comprehensive status report. This report will drive the next phase of Ralph-automated development.

This is Ralph's first real production task. Be thorough but practical.

---

## CONTEXT

**Project:** RIVET Pro - AI-powered maintenance assistant for field technicians
**Goal:** Techs photograph equipment → instant identification + troubleshooting guidance
**Philosophy:** CRAWL→WALK→RUN. Ship simple, iterate fast.

**Known Infrastructure:**
- VPS: 72.60.175.144:5678 (n8n)
- Telegram Bot: @rivet_local_dev_bot
- Photo Bot Workflow: 7LMKcMmldZsu1l6g (Gemini 2.5 Flash)
- Database: Neon PostgreSQL (with fallback support planned)

**Business Model:**
- Free: 10 lookups
- Pro: $29/month (unlimited + PDF chat)
- Team: $200/month (shared KB + PLC panels)

**Ralph Status:** ✅ Working (frankbria/ralph-claude-code validated with RIVET-006)

**Recent Win:** RIVET-006 (API Version Endpoint) completed in 1 iteration with 93.75% success rate.

---

## TASK 1: Deep Codebase Scan

Examine EVERY file in the project. No assumptions. For each component, determine:
- Does it exist?
- Is it complete or stubbed?
- Does it actually work?
- What's missing?

### 1.1 Project Structure
Scan and document:
- [ ] Root directory layout
- [ ] Entry points (main.py, app.py, __init__.py)
- [ ] Package structure
- [ ] Import relationships

### 1.2 API Layer
Find and assess:
- [ ] FastAPI/Flask app initialization
- [ ] Router registration
- [ ] All endpoint definitions
- [ ] Request/response models
- [ ] Authentication/authorization
- [ ] Error handling

### 1.3 Telegram Integration
Look for:
- [ ] Bot initialization
- [ ] Webhook handlers
- [ ] Message handlers (text, photo, commands)
- [ ] Callback handlers
- [ ] Response formatting
- [ ] n8n webhook integration

### 1.4 AI/Vision Pipeline
Find:
- [ ] Gemini API integration
- [ ] Claude API integration
- [ ] Photo processing logic
- [ ] OCR/text extraction
- [ ] Equipment identification logic
- [ ] Response generation

### 1.5 Database Layer
Locate:
- [ ] Connection configuration
- [ ] Models/schemas
- [ ] Migration files
- [ ] Query functions
- [ ] Connection pooling

### 1.6 Business Logic
Search for:
- [ ] Usage tracking implementation
- [ ] Free tier limit logic
- [ ] User management
- [ ] Subscription handling
- [ ] Rate limiting

### 1.7 Configuration
Find:
- [ ] Environment variable usage
- [ ] Config files
- [ ] Secrets management
- [ ] Feature flags

### 1.8 n8n Workflows
Document:
- [ ] Photo Bot v2 (7LMKcMmldZsu1l6g) - what does it do?
- [ ] Any other workflow IDs found
- [ ] Webhook URLs referenced
- [ ] Workflow dependencies

### 1.9 Tests & Quality
Look for:
- [ ] Test files
- [ ] Test coverage
- [ ] Linting configuration
- [ ] Type hints usage

### 1.10 Documentation
Check:
- [ ] README.md completeness
- [ ] AGENTS.md (for Ralph)
- [ ] PROMPT.md (for Ralph)
- [ ] API docs
- [ ] Setup instructions

---

## TASK 2: Create STATUS_REPORT.md

Create `STATUS_REPORT.md` in the project root:

```markdown
# RIVET Pro - System Status Report

**Generated:** [DATE]
**Audited by:** Claude Code CLI (Ralph Chore 001)
**Project Version:** [from git or package.json]
**Last Commit:** [hash and message]

---

## Executive Summary

[2-3 sentences max: Overall health, what works, biggest blocker to MVP]

**MVP Readiness Score:** X/10

---

## MVP Definition

### What MVP Must Do
A Telegram bot where field techs send equipment photos and receive identification + basic troubleshooting.

### MVP Critical Path
1. ✅/❌ Telegram bot receives photos
2. ✅/❌ AI analyzes photo (Gemini)
3. ✅/❌ Equipment identified
4. ✅/❌ Response sent to user
5. ✅/❌ Usage tracked per user
6. ✅/❌ Free tier limited to 10 lookups

### Explicitly NOT in MVP
- Stripe payments (honor system first)
- PDF manual chat
- CMMS integration
- Web dashboard
- Team features

---

## Component Status

### ✅ WORKING (Verified Functional)

| Component | File(s) | Evidence |
|-----------|---------|----------|
| [name] | [path] | [how verified] |

### 🟡 EXISTS BUT INCOMPLETE

| Component | File(s) | What's Missing | Effort |
|-----------|---------|----------------|--------|
| [name] | [path] | [gap] | S/M/L |

### 🔴 MISSING (Must Build)

| Component | Why Needed | Priority | Effort |
|-----------|------------|----------|--------|
| [name] | [reason] | P0/P1/P2 | S/M/L |

### ⚪ DEFERRED (Not MVP)

| Component | Reason to Defer |
|-----------|-----------------|
| [name] | [reason] |

---

## File Tree Analysis

```
[Include actual tree output with annotations]
```

### Key Files Identified

| File | Purpose | Status |
|------|---------|--------|
| [path] | [what it does] | ✅/🟡/🔴 |

---

## n8n Workflow Analysis

### Photo Bot v2 (7LMKcMmldZsu1l6g)

- **Status:** [Working/Broken/Unknown]
- **Trigger:** [Type and URL]
- **Purpose:** [What it does]
- **Nodes:** [Count and key nodes]
- **Dependencies:** [External services called]
- **Issues Found:** [Any problems]

### Other Workflows Found

| Workflow ID | Name | Purpose | Status |
|-------------|------|---------|--------|
| [id] | [name] | [purpose] | [status] |

---

## Database Analysis

### Connection Status
- **Provider:** [Neon/Supabase/Local]
- **Connected:** ✅/❌
- **Connection String Location:** [where defined]

### Tables Found

| Table | Columns | Row Count | Purpose |
|-------|---------|-----------|---------|
| [name] | [count] | [count] | [purpose] |

### Tables Needed for MVP

| Table | Purpose | Schema Suggestion |
|-------|---------|-------------------|
| users | Track users | id, telegram_id, created_at |
| usage | Track lookups | id, user_id, timestamp, equipment_id |

---

## Environment Configuration

### Variables Found in Code

| Variable | Used In | Required | Has Default |
|----------|---------|----------|-------------|
| TELEGRAM_BOT_TOKEN | [file] | Yes | No |
| ANTHROPIC_API_KEY | [file] | Yes | No |
| GEMINI_API_KEY | [file] | Yes | No |
| DATABASE_URL | [file] | Yes | No |
| [others] | | | |

### Config Files

| File | Exists | Complete | Notes |
|------|--------|----------|-------|
| .env | ✅/❌ | ✅/❌ | [notes] |
| .env.example | ✅/❌ | ✅/❌ | [notes] |
| config.py | ✅/❌ | ✅/❌ | [notes] |

---

## Code Quality

### Patterns Observed
- [ ] Async/await usage: [Yes/No/Partial]
- [ ] Type hints: [Yes/No/Partial]
- [ ] Docstrings: [Yes/No/Partial]
- [ ] Error handling: [Yes/No/Partial]
- [ ] Logging: [Yes/No/Partial]

### Technical Debt

| Issue | Location | Impact | Fix Effort |
|-------|----------|--------|------------|
| [issue] | [file] | High/Med/Low | S/M/L |

### Strengths
- [What's done well]

---

## Gap Analysis

### Critical Blockers (Must Fix for MVP)

1. **[Blocker]**
   - Current: [state]
   - Needed: [state]
   - Fix: [how]

2. **[Blocker]**
   - Current: [state]
   - Needed: [state]
   - Fix: [how]

### MVP Launch Checklist

- [ ] Bot responds to /start command
- [ ] Bot accepts and acknowledges photo messages
- [ ] Photos sent to Gemini for analysis
- [ ] Equipment identification returned
- [ ] User sees helpful response in Telegram
- [ ] Usage count incremented in database
- [ ] User blocked after 10 free lookups
- [ ] Error messages are user-friendly
- [ ] No crashes on edge cases (no photo, wrong format, etc.)

---

## Recommendations

### Do Immediately (Today)
1. [Action]
2. [Action]

### Do This Week
1. [Action]
2. [Action]
3. [Action]

### Do Before Launch
1. [Action]
2. [Action]

### Do After MVP (WALK Phase)
1. [Action]
2. [Action]

---

## Appendix: All Files Scanned

[List every file examined with line count]
```

---

## TASK 3: Create MVP_ROADMAP.md

Create `MVP_ROADMAP.md`:

```markdown
# RIVET Pro MVP Roadmap

**Created:** [DATE]
**Target Launch:** [DATE + 2 weeks or realistic estimate]
**Philosophy:** CRAWL first. Ship something that works.

---

## Vision

Field techs photograph equipment → instant identification + troubleshooting guidance.

**One Sentence:** "Shazam for industrial equipment"

---

## MVP Scope

### IN SCOPE (Must Ship)
1. Telegram bot receives photos ✅/❌
2. AI identifies equipment from photo ✅/❌
3. Bot responds with equipment name + basic info ✅/❌
4. Usage tracked per Telegram user ✅/❌
5. Free tier enforced (10 lookups) ✅/❌

### OUT OF SCOPE (Deferred)
- Stripe payment integration
- PDF manual retrieval
- Detailed troubleshooting steps
- CMMS integration
- Team/organization features
- Web dashboard
- Mobile app

---

## Sprint Plan

### Sprint 1: Core Pipeline
**Goal:** Photo in → Answer out

| Story | Title | Status |
|-------|-------|--------|
| RIVET-007 | [from audit] | ⬜ TODO |
| RIVET-008 | [from audit] | ⬜ TODO |
| RIVET-009 | [from audit] | ⬜ TODO |

### Sprint 2: Usage & Limits
**Goal:** Track usage, enforce free tier

| Story | Title | Status |
|-------|-------|--------|
| RIVET-010 | [from audit] | ⬜ TODO |
| RIVET-011 | [from audit] | ⬜ TODO |

### Sprint 3: Polish
**Goal:** Handle edge cases, improve UX

| Story | Title | Status |
|-------|-------|--------|
| RIVET-012 | [from audit] | ⬜ TODO |
| RIVET-013 | [from audit] | ⬜ TODO |

---

## Success Criteria

### Technical
- [ ] Bot responds in < 10 seconds
- [ ] Equipment ID accuracy > 80%
- [ ] Zero crashes in 24hr test
- [ ] Handles 100 requests/day

### User
- [ ] 5 real techs give positive feedback
- [ ] Setup takes < 5 minutes
- [ ] No training needed to use

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Gemini API rate limits | Medium | High | Implement backoff |
| Poor equipment recognition | Medium | High | Improve prompts, add feedback loop |
| [other risks] | | | |

---

## Launch Checklist

### Before Public Launch
- [ ] All Sprint 1-3 stories complete
- [ ] Tested with 20+ real equipment photos
- [ ] Error messages are helpful
- [ ] README has setup instructions
- [ ] Bot description configured in BotFather
- [ ] Monitoring/alerting in place
- [ ] Backup database configured

### Launch Day
- [ ] Announce in 1-2 maintenance forums
- [ ] Monitor error rates
- [ ] Be available for quick fixes

---

## Post-MVP Roadmap (WALK → RUN)

### WALK Phase (Month 2)
- Stripe integration for Pro tier
- PDF manual retrieval
- Basic analytics dashboard

### RUN Phase (Month 3+)
- Team features
- CMMS integrations
- Mobile app consideration
- PLC panel recognition
```

---

## TASK 4: Update @fix_plan.md with Next Stories

Based on your audit findings, update `scripts/ralph-claude-code/@fix_plan.md`:

```markdown
# RIVET Pro - Ralph Task Queue

**Updated:** [DATE]
**Sprint:** MVP Core Pipeline
**Source:** Ralph Chore 001 System Audit

---

## How This Works
Ralph reads this file top-to-bottom. First incomplete story gets implemented.
Mark stories complete by changing ⬜ to ✅.

---

## Active Sprint

### RIVET-007: [Title based on #1 gap from audit]
**Priority:** P0 - MVP Blocker
**Complexity:** [Simple/Medium]
**Status:** ⬜ TODO

**Description:**
[Clear description of what to build based on audit findings]

**Acceptance Criteria:**
- [ ] [Specific, testable criterion]
- [ ] [Specific, testable criterion]
- [ ] [Specific, testable criterion]
- [ ] Code follows existing patterns (see AGENTS.md)
- [ ] No linting errors
- [ ] Committed with message: `feat(RIVET-007): [title]`

**Files to Create/Modify:**
- `[filepath]` - [what to do]

**Implementation Notes:**
- [Helpful context from audit]
- [Pattern to follow]
- [Gotcha to avoid]

---

### RIVET-008: [Title based on #2 gap]
**Priority:** P0 - MVP Blocker
**Complexity:** [Simple/Medium]
**Status:** ⬜ TODO

**Description:**
[What to build]

**Acceptance Criteria:**
- [ ] [Criterion]
- [ ] [Criterion]
- [ ] Committed with message: `feat(RIVET-008): [title]`

**Files to Create/Modify:**
- `[filepath]` - [what]

---

### RIVET-009: [Title based on #3 gap]
**Priority:** P1 - Important
**Complexity:** [Simple/Medium]
**Status:** ⬜ TODO

**Description:**
[What to build]

**Acceptance Criteria:**
- [ ] [Criterion]
- [ ] [Criterion]
- [ ] Committed with message: `feat(RIVET-009): [title]`

---

### RIVET-010: [Title]
**Priority:** P1
**Status:** ⬜ TODO

[Continue pattern...]

---

### RIVET-011: [Title]
**Priority:** P1
**Status:** ⬜ TODO

[Continue pattern...]

---

## Completed Stories

### ✅ RIVET-006: Add API Version Endpoint
**Completed:** 2026-01-11
**Commit:** fce57e2
**Result:** Production-quality code in 1 iteration

---

## Backlog (Post-MVP)

### RIVET-020: Stripe Payment Integration
**Priority:** P2 - Post-MVP
**Status:** ⬜ BACKLOG

### RIVET-021: PDF Manual Chat
**Priority:** P2 - Post-MVP
**Status:** ⬜ BACKLOG
```

---

## TASK 5: Update AGENTS.md with Audit Learnings

Append to `AGENTS.md` any patterns or gotchas discovered during the audit:

```markdown
## Patterns Discovered (Audit 2026-01-11)

### [Pattern Name]
- [Description]
- [Where it's used]
- [How to follow it]

## Gotchas Found

### [Gotcha]
- [What the problem is]
- [How to avoid it]
```

---

## TASK 6: Commit Everything

```bash
git add STATUS_REPORT.md MVP_ROADMAP.md scripts/ralph-claude-code/@fix_plan.md AGENTS.md
git commit -m "docs(CHORE-001): system audit and MVP roadmap

- Complete codebase audit
- MVP readiness assessment
- Queued RIVET-007 through RIVET-011 for Ralph
- Updated AGENTS.md with discovered patterns"
git push
```

---

## OUTPUT

When complete, output this summary:

```
═══════════════════════════════════════════════════════════════
RALPH CHORE 001 COMPLETE: System Audit
═══════════════════════════════════════════════════════════════

FILES CREATED:
  ✅ STATUS_REPORT.md ([X] lines)
  ✅ MVP_ROADMAP.md ([X] lines)
  ✅ @fix_plan.md updated with [X] new stories

AUDIT FINDINGS:
  MVP Readiness: [X]/10
  Components Working: [X]
  Components Incomplete: [X]
  Components Missing: [X]

CRITICAL GAPS IDENTIFIED:
  1. [Gap #1 - becomes RIVET-007]
  2. [Gap #2 - becomes RIVET-008]
  3. [Gap #3 - becomes RIVET-009]

STORIES QUEUED FOR RALPH:
  ⬜ RIVET-007: [title]
  ⬜ RIVET-008: [title]
  ⬜ RIVET-009: [title]
  ⬜ RIVET-010: [title]
  ⬜ RIVET-011: [title]

COMMITS:
  [hash] docs(CHORE-001): system audit and MVP roadmap

═══════════════════════════════════════════════════════════════
NEXT STEP: Run Ralph to implement the queued stories
═══════════════════════════════════════════════════════════════

cd [project-directory]
ralph --max-iterations 30

Ralph will implement RIVET-007 through RIVET-011 autonomously.
Estimated time: 1-2 hours
Estimated cost: ~$0.15-0.30

READY FOR RALPH 🚀
```

---

## CONSTRAINTS

- Be BRUTALLY honest. If something is broken, say broken.
- If you can't verify something works, mark it UNKNOWN not WORKING.
- Keep stories SMALL - one feature, one file, one purpose.
- Prioritize ruthlessly - MVP means MINIMUM.
- Don't over-engineer the audit - we need to ship, not document forever.
- Every story must have testable acceptance criteria.
- Maximum 5-6 stories for first Ralph run. Don't overwhelm.
