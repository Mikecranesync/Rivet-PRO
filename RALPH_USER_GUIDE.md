# Ralph: Your AI Developer - User Guide

**Date:** 2026-01-12

---

## What Is Ralph? (Explain It Like I'm 5)

Imagine you have a todo list of features you want built for your app. Ralph is like having a junior developer who:
- Never sleeps
- Works 24/7
- Costs $0.04/hour (vs $50-150/hour for a human)
- Reads your todo list and builds each feature automatically
- Tells you in Telegram when each task is done

**Instead of:**
```
You: "Hey developer, can you add user authentication?"
Developer: "Sure, I'll start tomorrow, should take 2-3 days"
[3 days later...]
Developer: "It's done, check the code"
You: "Great! Now can you add payment processing?"
[Repeat...]
```

**With Ralph:**
```
You: Write todo list in database
Ralph: [silently builds everything overnight]
[You wake up]
Ralph: "✅ Done. Here are the 5 features you asked for."
```

---

## The User Experience (Step by Step)

### Step 1: You Write Your Wishlist

You add features to a database table (think of it like a Google Sheet). Each feature is a "story."

**Example:**
```
Story ID: RIVET-001
Title: Add usage tracking
What it does: Count how many times each user analyzes a photo
Why: So we can limit free users to 10 analyses

Story ID: RIVET-002
Title: Add Stripe payments
What it does: Let users pay $29/month for unlimited
Why: Make money

Story ID: RIVET-003
Title: Block free users at limit
What it does: Show "upgrade to Pro" after 10 free analyses
Why: Convert free users to paid
```

That's it. You just describe WHAT you want, not HOW to build it.

---

### Step 2: You Tell Ralph To Start

Three ways:

**Option A: Click a button in n8n**
- Open n8n in your browser
- Click "Execute Workflow"
- Done

**Option B: Send a webhook**
```bash
curl "https://your-n8n.com/webhook/ralph-main-loop"
```

**Option C: Schedule it**
- Set Ralph to run automatically every night at 2 AM
- Wake up to new features every morning

---

### Step 3: Ralph Works (You Watch)

Ralph sends you Telegram messages as it works:

```
[2:00 AM]
🚀 RALPH STARTING
Project: RIVET Pro

[2:01 AM]
🟡 STARTING: RIVET-001
Title: Add usage tracking
Model: Claude Sonnet 4
Priority: 1

[2:04 AM]
✅ DONE: RIVET-001
Commit: a1b2c3d
Files changed: 3
Tokens used: 12,345
Duration: 3m 15s

[2:04 AM]
🟡 STARTING: RIVET-002
Title: Add Stripe payments
Model: Claude Sonnet 4
Priority: 2

[2:09 AM]
✅ DONE: RIVET-002
Commit: e4f5g6h
Files changed: 5
Tokens used: 18,902
Duration: 5m 22s

[continuing for all stories...]

[2:25 AM]
🏁 RALPH COMPLETE
✅ Stories completed: 5
❌ Stories failed: 0
💰 Cost: $0.34
⏱️ Duration: 25 minutes
```

You can check Telegram anytime to see progress. It's like getting real-time status updates from a developer working overnight.

---

### Step 4: Ralph Is Done (You Check The Code)

When Ralph finishes:

1. **Code is committed to git**
   - Each story gets its own commit
   - Clear commit messages like "RIVET-001: Add usage tracking"

2. **You review the changes**
   ```bash
   git log
   git diff HEAD~5..HEAD  # See last 5 commits
   ```

3. **Test the features**
   - Ralph wrote the code, but you should test it
   - Make sure it works as expected

4. **Deploy if good**
   ```bash
   git push
   # Your deployment pipeline handles the rest
   ```

5. **OR: Give feedback if not quite right**
   - Add a new story: "RIVET-001-FIX: Adjust usage tracking to reset monthly"
   - Run Ralph again

---

## Real-World Example: Friday Evening → Monday Morning

### Friday 5 PM (You)

You're heading out for the weekend. You have 10 features you want built for your RIVET Pro app.

You spend 30 minutes writing them as stories in the database:

```sql
RIVET-001: Usage tracking
RIVET-002: Stripe payments
RIVET-003: Free tier limits
RIVET-004: Shorten AI prompts
RIVET-005: Remove n8n branding
RIVET-006: Add user dashboard
RIVET-007: Email notifications
RIVET-008: Export usage data
RIVET-009: Admin panel
RIVET-010: Dark mode
```

You trigger Ralph, then leave for the weekend.

---

### Friday 5:30 PM → Monday 8 AM (Ralph)

Ralph works all weekend:
- Reads each story
- Understands what you want
- Reads your existing codebase
- Writes the code
- Tests it (if you configured tests)
- Commits to git
- Moves to next story

**Total time:** 2-3 hours of actual work (spread across 60 hours)
**Your time:** 30 minutes (writing stories)
**Cost:** ~$3.40 (10 stories × $0.34)

---

### Monday 8 AM (You)

You check Telegram:

```
🏁 RALPH COMPLETE
✅ Stories completed: 10
❌ Stories failed: 0
💰 Cost: $3.42
⏱️ Total: 2h 47m
```

You check git:

```bash
$ git log --oneline
a1b2c3d RIVET-010: Add dark mode toggle
e4f5g6h RIVET-009: Create admin panel
...
z9y8x7w RIVET-001: Add usage tracking
```

You pull the code, test it, and deploy.

**You just got 10 features built for $3.42 and 30 minutes of your time.**

A human developer would have charged $5,000-15,000 and taken 2-4 weeks.

---

## What Ralph Is Great At

✅ **Repetitive CRUD operations**
- "Add a new database table for X"
- "Create REST API endpoints for Y"

✅ **Following patterns**
- "Do the same thing we did for equipment, but for work orders"

✅ **Refactoring**
- "Make all these prompts shorter"
- "Update all API calls to use the new auth header"

✅ **Documentation**
- "Add JSDoc comments to all functions"
- "Generate API documentation"

✅ **Integration work**
- "Connect Stripe for payments"
- "Add Twilio SMS notifications"

✅ **Boilerplate**
- "Create a new microservice following our template"
- "Add tests for all API endpoints"

---

## What Ralph Struggles With

❌ **Brand new architecture decisions**
- "Should we use microservices or monolith?"
- "Which database should we choose?"

❌ **Creative/UX work**
- "Design a beautiful landing page"
- "Make the user flow feel magical"

❌ **Performance optimization**
- "This query is slow, make it faster"
- Ralph will try, but might not find the best solution

❌ **Debugging complex issues**
- "Users report random crashes on iOS 14.3"
- Ralph can make attempts, but needs human guidance

❌ **Security audits**
- "Find all security vulnerabilities"
- Ralph can implement fixes, but needs you to find issues first

**Rule of thumb:** Ralph is great at **implementing** solutions you've already decided on. Not great at **deciding** what the solution should be.

---

## How Much Does It Cost?

### Token Costs (Claude API)

| Task Type | Model | Tokens | Cost |
|-----------|-------|--------|------|
| Simple feature (RIVET-005) | Haiku | ~5,000 | $0.01 |
| Medium feature (RIVET-001) | Sonnet 4 | ~15,000 | $0.10 |
| Complex feature (RIVET-002) | Sonnet 4 | ~25,000 | $0.17 |

### Real Examples

**10 features (mixed complexity):**
- 2 complex (Stripe, Auth) = $0.34
- 5 medium (CRUD, APIs) = $0.50
- 3 simple (UI tweaks, docs) = $0.03
- **Total: $0.87**

**50 features (full app):**
- **Total: ~$15-25**

**For comparison:**
- Human developer: $5,000-25,000
- Your time saved: 100-200 hours
- **Ralph ROI: 200-1000x**

---

## How Fast Is Ralph?

### Per Feature

| Complexity | Time | Human Equivalent |
|------------|------|------------------|
| Simple (UI tweak) | 30s - 2min | 30min - 1hr |
| Medium (CRUD) | 2-5min | 2-4hrs |
| Complex (Integration) | 5-15min | 4-8hrs |

### Full Runs

**5 features (MVP):**
- Ralph: 15-25 minutes
- Human: 1-2 days

**20 features (Full product):**
- Ralph: 1-2 hours
- Human: 1-2 weeks

**100 features (Enterprise app):**
- Ralph: 8-10 hours
- Human: 2-3 months

**The magic:** Ralph works at 3 AM. You sleep, Ralph codes. You wake up to new features.

---

## Safety: Can Ralph Break Things?

### Built-in Safety Features

✅ **Git commits**
- Every change is committed
- Easy to revert: `git revert HEAD`

✅ **Status tracking**
- Database tracks every story
- You can see what succeeded vs failed

✅ **Error handling**
- If a story fails, Ralph retries (up to 3 times)
- Failures don't stop the whole run

✅ **Telegram notifications**
- You're notified immediately if something fails
- Can intervene if needed

✅ **Human review**
- Ralph commits, but YOU decide when to deploy
- Review code before it goes to production

### Best Practices

1. **Start small**
   - Run Ralph on 1-2 simple stories first
   - Verify quality before scaling up

2. **Review commits**
   - Use `git diff` to see what changed
   - Read the code, don't blindly deploy

3. **Test before deploy**
   - Ralph wrote it, you test it
   - Have a staging environment

4. **Use branches**
   - Ralph works on `feature/ralph-batch-1` branch
   - You merge to `main` after review

5. **Set token budgets**
   - Configure max tokens per run
   - Prevents runaway costs

---

## Typical Workflows

### Workflow 1: Weekly Feature Batch

**Monday:**
- Product team writes 10 new stories
- Prioritize them (1-10)

**Tuesday 2 AM:**
- Ralph runs automatically (scheduled)
- Implements all 10 stories
- Takes 1-2 hours

**Tuesday 9 AM:**
- Dev team reviews commits
- Fixes any issues
- Merges to main

**Tuesday 5 PM:**
- Deploy to production
- 10 new features live

**Repeat every week.**

---

### Workflow 2: On-Demand Development

**Situation:** Customer requests emergency feature

**2:00 PM:**
- You write the story
- Priority: 1 (urgent)

**2:05 PM:**
- Trigger Ralph via webhook
- Ralph starts immediately

**2:15 PM:**
- Ralph finishes
- You receive Telegram notification

**2:20 PM:**
- You review code
- Looks good

**2:25 PM:**
- Deploy to production
- Customer has their feature in 25 minutes

---

### Workflow 3: Overnight Magic

**Before bed (11 PM):**
- Write 5-10 stories
- Trigger Ralph

**While you sleep:**
- Ralph works all night
- Implements everything

**Morning (7 AM):**
- Wake up to completion message
- Review over coffee
- Deploy before standup

**Standup (9 AM):**
- "I shipped 8 features this morning"
- Team thinks you're a wizard

---

## Advanced: Teaching Ralph Your Style

Ralph learns from your codebase:

### Style Guide Example

Create `.ralph/style-guide.md`:

```markdown
# RIVET Pro Coding Style

## File Structure
- Models in `rivet_pro/core/models/`
- API routes in `rivet_pro/adapters/web/routes/`
- Tests in `tests/unit/` or `tests/integration/`

## Naming
- Classes: PascalCase (UsageTracker)
- Functions: snake_case (get_usage_count)
- Constants: UPPER_SNAKE (MAX_FREE_LOOKUPS)

## Database
- Use Neon PostgreSQL connection string from .env
- All queries use sqlalchemy ORM
- No raw SQL except in migrations

## Testing
- Every new function needs a test
- Tests use pytest
- Mock external APIs

## Commit Messages
- Format: "RIVET-XXX: Brief description"
- Example: "RIVET-001: Add usage tracking to user model"
```

Ralph will read this file and follow your style automatically.

---

## Monitoring Ralph

### Real-Time (Telegram)
- Get messages as each story completes
- See errors immediately
- Know when full run finishes

### Database Queries

**Check current status:**
```sql
SELECT story_id, status, status_emoji
FROM ralph_stories
WHERE project_id = 1
ORDER BY priority;
```

**See what's running:**
```sql
SELECT *
FROM ralph_executions
WHERE status = 'running'
ORDER BY started_at DESC
LIMIT 1;
```

**Track costs:**
```sql
SELECT
  SUM(total_tokens) as total_tokens,
  ROUND(SUM(total_tokens) * 0.000005, 2) as estimated_cost
FROM ralph_executions
WHERE created_at >= NOW() - INTERVAL '30 days';
```

### n8n Dashboard
- Open n8n web UI
- See execution history
- View logs for each run
- Manually trigger if needed

---

## Common Questions

### Q: Does Ralph replace developers?
**A:** No. Ralph is like a junior developer who needs guidance. You still need humans to:
- Decide what to build
- Design architecture
- Review code quality
- Debug complex issues
- Make business decisions

Ralph is a **productivity multiplier**, not a replacement.

---

### Q: What if Ralph writes bad code?
**A:** You review it before deploying. Ralph commits to git, you decide when it goes live. If code is bad:
1. Revert the commit
2. Add clarification to the story
3. Run Ralph again

---

### Q: Can Ralph work on any codebase?
**A:** Yes, but works best on:
- Well-structured codebases
- Clear conventions
- Good documentation
- Existing patterns to follow

Messy legacy codebases need cleanup first.

---

### Q: What if Ralph gets stuck?
**A:** Ralph retries failed stories up to 3 times. If still failing:
1. Check error message in database
2. Fix underlying issue (e.g., missing dependency)
3. Reset story to 'todo'
4. Run Ralph again

---

### Q: How do I stop Ralph mid-run?
**A:** Two ways:
1. **Deactivate workflow** in n8n (stops after current story)
2. **Update database:** `UPDATE ralph_executions SET status = 'stopped' WHERE id = X`

Ralph will finish current story, then stop.

---

### Q: Can multiple Ralphs run at once?
**A:** Not recommended. Stories could conflict. Better to:
- Run one Ralph per project
- Use priority to control order
- Queue up stories, let Ralph process sequentially

---

## Getting Started Checklist

Ready to use Ralph? Follow these steps:

- [ ] **VPS Access**
  - n8n running on http://72.60.175.144:5678
  - You can log in and see workflows

- [ ] **Database Setup**
  - PostgreSQL accessible (Neon or Supabase)
  - 4 Ralph tables created (run migration SQL)

- [ ] **Telegram Bot**
  - Bot token configured
  - Your chat ID set up
  - Can receive test messages

- [ ] **n8n Workflows**
  - "Ralph - Main Loop" imported and active
  - "Ralph - Worker" imported and active
  - Credentials configured

- [ ] **Claude Code CLI**
  - Installed on VPS
  - API key configured
  - Can run basic commands

- [ ] **First Story**
  - Write one simple story in database
  - Trigger Ralph
  - Verify it completes successfully

- [ ] **Git Repository**
  - Clean working directory
  - Can commit changes
  - Branches set up if using feature branches

---

## Your First Ralph Run (Quick Start)

### 1. Add A Simple Story

```sql
INSERT INTO ralph_stories (
  project_id, story_id, title, description,
  acceptance_criteria, ai_model, priority
) VALUES (
  1,
  'TEST-001',
  'Add health check endpoint',
  'Create a simple /health endpoint that returns {"status": "ok"}',
  '["Create /health route", "Return JSON with status ok", "Add test for endpoint"]'::jsonb,
  'claude-haiku-20250305',
  1
);
```

This is a simple story Ralph can definitely handle.

---

### 2. Trigger Ralph

```bash
curl "http://72.60.175.144:5678/webhook/ralph-main-loop"
```

---

### 3. Watch Telegram

You should receive:
```
🚀 RALPH STARTING
🟡 STARTING: TEST-001
✅ DONE: TEST-001
🏁 RALPH COMPLETE
```

---

### 4. Check The Code

```bash
cd /opt/Rivet-PRO
git log -1
git show HEAD
```

You should see:
- New file: `rivet_pro/adapters/web/routes/health.py`
- Test file: `tests/unit/test_health.py`
- Clean commit message

---

### 5. Test It

```bash
python -m pytest tests/unit/test_health.py
curl http://localhost:8000/health
```

Should return:
```json
{"status": "ok"}
```

---

### 6. Celebrate! 🎉

You just had an AI autonomously:
- Read your requirements
- Wrote production code
- Added tests
- Committed to git
- All in < 2 minutes

---

## Summary: Why Ralph?

**Before Ralph:**
- Write spec → Wait for developer → Review code → Deploy
- Takes days/weeks
- Costs $50-150/hour
- Limited by human availability

**With Ralph:**
- Write spec → Ralph builds it → Review code → Deploy
- Takes minutes/hours
- Costs $0.04/hour
- Works 24/7

**The Revolution:**
- You describe WHAT you want
- Ralph figures out HOW
- You review and deploy
- Repeat infinitely

**Result:** You ship 10-100x faster at 1/1000th the cost.

---

## Next Steps

1. ✅ Read this guide (you just did!)
2. ⬜ Access n8n at http://72.60.175.144:5678
3. ⬜ Import Ralph workflows (or they're already there)
4. ⬜ Run the "First Ralph Run" tutorial above
5. ⬜ Add 5-10 real stories for your project
6. ⬜ Let Ralph build your product overnight
7. ⬜ Wake up to new features
8. ⬜ Repeat forever

**Welcome to the future of software development.** 🚀

---

**Questions?** Re-read sections above or ask me to explain anything in more detail!
