# Ralph MVP System - Complete Walkthrough

**Date:** 2026-01-12
**Purpose:** Step-by-step explanation of Ralph's autonomous development system

---

## What Is Ralph?

**Ralph is an autonomous software development agent** built on n8n that implements user stories automatically by:
1. Reading stories from a PostgreSQL database
2. Calling the Claude Code CLI to implement each story
3. Managing iterations, retries, and error handling
4. Sending progress updates to Telegram
5. Looping through a backlog until all stories are complete

**Think of Ralph as:** A tireless junior developer who works 24/7, reading your backlog and implementing features one by one.

---

## The Big Picture

```
┌─────────────────────────────────────────────────────────────┐
│                     RALPH SYSTEM OVERVIEW                    │
└─────────────────────────────────────────────────────────────┘

User defines stories in database
         │
         ▼
   ┌──────────────┐
   │   Trigger    │ ← Webhook/Manual/Schedule
   │   (n8n)      │
   └──────┬───────┘
          │
          ▼
   ┌─────────────────┐
   │ Main Loop       │ ← Workflow: "Ralph - Main Loop"
   │ Workflow (n8n)  │   - Creates execution record
   └────────┬────────┘   - Fetches next story
            │            - Checks if stories remain
            │
            ▼
      ┌─────────────────┐
      │ Should Continue?│
      └───┬─────────┬───┘
          │ YES     │ NO
          │         └──────→ Send completion message
          │
          ▼
   ┌────────────────────┐
   │ Mark In Progress   │ ← Update story status to 'in_progress'
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐
   │ Send Telegram:     │ ← Notify: "🟡 STARTING: RIVET-001"
   │ "Starting Story"   │   "Model: claude-sonnet-4-20250514"
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐
   │ Call Worker        │ ← HTTP POST to worker workflow
   │ Workflow           │   Passes story_id, model, description
   └─────────┬──────────┘
             │
             ▼
   ┌─────────────────────────────────────────┐
   │       WORKER WORKFLOW                    │
   │   (Separate workflow, runs in parallel) │
   ├─────────────────────────────────────────┤
   │  1. Receive story data                  │
   │  2. Build Claude Code CLI command       │
   │  3. Execute: claude-code implement      │
   │  4. Parse output (commit hash, tokens)  │
   │  5. Return result to Main Loop          │
   └────────────────┬────────────────────────┘
                    │
                    ▼
         ┌─────────────────┐
         │ Update Story    │ ← Mark 'done' or 'failed'
         │ (PostgreSQL)    │   Store commit hash, tokens, error
         └──────┬──────────┘
                │
                ▼
         ┌─────────────────┐
         │ Send Telegram:  │ ← "✅ DONE: RIVET-001"
         │ "Story Complete"│   "Commit: abc123, Tokens: 12,345"
         └──────┬──────────┘
                │
                ▼
         ┌─────────────────┐
         │ Check More      │ ← Query: More stories with status='todo'?
         │ Stories?        │
         └──┬──────────┬───┘
            │ YES      │ NO
            │          │
            │          ▼
            │    ┌────────────────┐
            │    │ Finalize       │
            │    │ Execution      │
            │    └───────┬────────┘
            │            │
            │            ▼
            │    ┌────────────────┐
            │    │ Send Telegram: │
            │    │ "COMPLETE"     │
            │    └────────────────┘
            │
            └──────→ LOOP BACK TO "Get Next Story"

```

---

## Step-by-Step System Flow

### Phase 1: System Initialization

#### Step 1.1: Trigger Event
**What happens:**
- A webhook is called: `https://n8n-cloud.com/webhook/ralph-main-loop`
- OR a manual trigger button is clicked in n8n
- OR a scheduled cron job fires

**Why:** Ralph needs to know when to start working

**n8n Node:** Webhook node (ID: 1)

---

#### Step 1.2: Send Start Notification
**What happens:**
- Ralph sends a Telegram message:
  ```
  🚀 RALPH STARTING
  Project: RIVET Pro
  ```

**Why:** Let humans know Ralph is awake and working

**n8n Node:** Telegram node "Send Start" (ID: 2)
- **Chat ID:** 8445149012 (your Telegram user ID)

---

#### Step 1.3: Create Execution Record
**What happens:**
- Ralph inserts a row into `ralph_executions` table:
  ```sql
  INSERT INTO ralph_executions (project_id, status)
  VALUES (1, 'running')
  RETURNING id;
  ```
- Gets back execution ID (e.g., `execution_id = 42`)

**Why:** Track this run in the database - how many stories completed, tokens used, when started

**n8n Node:** Postgres "Create Execution" (ID: 3)
- **Database:** Neon PostgreSQL or Supabase
- **Table:** `ralph_executions`

**Database Schema:**
```sql
CREATE TABLE ralph_executions (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES ralph_projects(id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    total_iterations INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    stories_completed INTEGER DEFAULT 0,
    stories_failed INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'running'
);
```

---

### Phase 2: Story Processing Loop

#### Step 2.1: Get Next Story
**What happens:**
- Ralph queries the database for the next story to implement:
  ```sql
  SELECT * FROM ralph_stories
  WHERE project_id = 1
    AND status = 'todo'
    AND retry_count < 3
  ORDER BY priority ASC
  LIMIT 1;
  ```

**Returns something like:**
```json
{
  "id": 123,
  "story_id": "RIVET-001",
  "title": "Usage Tracking System",
  "description": "Track equipment lookups per user for freemium enforcement.",
  "acceptance_criteria": [
    "Track each photo upload as one lookup",
    "Store user_id and timestamp in Neon",
    "Create get_usage_count function",
    "Block at 10 free lookups with upgrade message"
  ],
  "ai_model": "claude-sonnet-4-20250514",
  "status": "todo",
  "priority": 1
}
```

**Why:** Ralph needs to know WHAT to build next

**n8n Node:** Postgres "Get Next Story" (ID: 4)

**Database Schema:**
```sql
CREATE TABLE ralph_stories (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES ralph_projects(id),
    story_id VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    acceptance_criteria JSONB,
    ai_model VARCHAR(100) DEFAULT 'claude-sonnet-4-20250514',
    status VARCHAR(20) DEFAULT 'todo',  -- 'todo', 'in_progress', 'done', 'failed'
    status_emoji VARCHAR(10) DEFAULT '⬜',
    priority INTEGER DEFAULT 0,
    commit_hash VARCHAR(100),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    UNIQUE(project_id, story_id)
);
```

---

#### Step 2.2: Check If Stories Remain
**What happens:**
- Ralph runs JavaScript code to check if a story was found:
  ```javascript
  const story = $input.first().json;
  const execution_id = $('Create Execution').first().json.id;

  if (!story || !story.id) {
    return [{
      json: {
        continue_loop: false,
        reason: 'All stories completed!',
        execution_id: execution_id
      }
    }];
  }

  return [{
    json: {
      continue_loop: true,
      story: story,
      execution_id: execution_id
    }
  }];
  ```

**Returns:**
- If stories exist: `{ continue_loop: true, story: {...} }`
- If no stories: `{ continue_loop: false, reason: 'All stories completed!' }`

**Why:** Ralph needs to know if there's more work or if it's time to stop

**n8n Node:** Code node "Check Stories Remain" (ID: 5)

---

#### Step 2.3: Should Continue?
**What happens:**
- Ralph uses an IF node to check `continue_loop` value
- **TRUE branch:** Continue to implement story
- **FALSE branch:** Jump to finalization (send completion message)

**Why:** Branching logic - either keep working or wrap up

**n8n Node:** IF node "Should Continue" (ID: 6)

---

#### Step 2.4: Mark Story In Progress
**What happens:**
- Ralph updates the story in the database:
  ```sql
  UPDATE ralph_stories
  SET status = 'in_progress',
      status_emoji = '🟡',
      started_at = NOW()
  WHERE id = 123;
  ```

**Why:** Track that this story is being worked on right now (prevents double-processing)

**n8n Node:** Postgres "Mark In Progress" (ID: 7)

---

#### Step 2.5: Send "Starting Story" Notification
**What happens:**
- Ralph sends Telegram message:
  ```
  🟡 STARTING: RIVET-001
  Title: Usage Tracking System
  Model: claude-sonnet-4-20250514
  Priority: 1
  ```

**Why:** Let humans monitor progress in real-time

**n8n Node:** Telegram "Send Starting" (ID: 8)

---

#### Step 2.6: Call Worker Workflow
**What happens:**
- Ralph makes an HTTP POST request to the **Worker Workflow**:
  ```http
  POST https://n8n-cloud.com/webhook/ralph-worker
  Content-Type: application/json

  {
    "story_id": "RIVET-001",
    "title": "Usage Tracking System",
    "description": "Track equipment lookups per user...",
    "acceptance_criteria": ["Track each photo...", "Store user_id..."],
    "ai_model": "claude-sonnet-4-20250514",
    "execution_id": 42
  }
  ```

- Worker workflow does the heavy lifting (see Phase 3 below)
- Returns result:
  ```json
  {
    "success": true,
    "commit_hash": "abc123def456",
    "tokens_used": 12345,
    "duration_seconds": 180
  }
  ```

**Why:** Separation of concerns - Main Loop orchestrates, Worker executes

**n8n Node:** HTTP Request "Call Worker" (ID: 9)

---

### Phase 3: Worker Workflow (The Implementation Engine)

**Separate Workflow:** "Ralph - Implement Single Story"
**Workflow ID:** ovTlTYSu97mWj-yc0J_yi (already exists and active)

This workflow receives the story data and actually implements it using Claude Code CLI.

#### Step 3.1: Receive Webhook
**What happens:**
- Worker receives the POST request from Main Loop
- Extracts story data from request body

**n8n Node:** Webhook "Receive Story"

---

#### Step 3.2: Build Claude Code Command
**What happens:**
- Worker constructs a command like:
  ```bash
  claude-code implement \
    --story-id "RIVET-001" \
    --title "Usage Tracking System" \
    --description "Track equipment lookups per user for freemium enforcement." \
    --acceptance-criteria '["Track each photo...", "Store user_id..."]' \
    --model "claude-sonnet-4-20250514" \
    --max-tokens 50000 \
    --output-format json \
    --auto-commit
  ```

**Why:** Claude Code CLI needs structured input to know what to build

**n8n Node:** Code "Build Command"

---

#### Step 3.3: Execute Claude Code CLI
**What happens:**
- Worker runs the command on the VPS:
  ```bash
  cd /opt/Rivet-PRO
  ./venv/bin/claude-code implement [args]
  ```

- Claude Code CLI:
  1. Reads the codebase
  2. Plans the implementation
  3. Writes code files
  4. Runs tests (if configured)
  5. Commits changes to git
  6. Outputs JSON with results

**Example Output:**
```json
{
  "status": "success",
  "story_id": "RIVET-001",
  "commit_hash": "abc123def456",
  "tokens_used": 12345,
  "files_modified": [
    "rivet_pro/core/usage_tracker.py",
    "rivet_pro/adapters/telegram/bot.py"
  ],
  "tests_passed": true,
  "duration_seconds": 180
}
```

**Why:** This is where the actual code gets written

**n8n Node:** Execute Command "Run Claude Code"

---

#### Step 3.4: Parse Output
**What happens:**
- Worker parses the JSON output from Claude Code
- Extracts key fields: commit_hash, tokens_used, success status
- Handles errors if Claude Code failed

**n8n Node:** Code "Parse Result"

---

#### Step 3.5: Return to Main Loop
**What happens:**
- Worker sends HTTP 200 response back to Main Loop with result data

**Why:** Main Loop needs to know if story succeeded or failed

**n8n Node:** Respond to Webhook

---

### Phase 4: Story Completion

#### Step 4.1: Update Story Status
**What happens:**
- Ralph updates the database based on worker result:

**If success:**
```sql
UPDATE ralph_stories
SET status = 'done',
    status_emoji = '✅',
    commit_hash = 'abc123def456',
    completed_at = NOW()
WHERE id = 123;
```

**If failure:**
```sql
UPDATE ralph_stories
SET status = 'failed',
    status_emoji = '❌',
    error_message = 'Claude Code CLI timed out',
    retry_count = retry_count + 1
WHERE id = 123;
```

**Why:** Track which stories are complete vs need retry

**n8n Node:** Postgres "Update Story" (ID: 10)

---

#### Step 4.2: Update Execution Stats
**What happens:**
- Ralph increments counters in `ralph_executions`:
  ```sql
  UPDATE ralph_executions
  SET total_iterations = total_iterations + 1,
      total_tokens = total_tokens + 12345,
      stories_completed = stories_completed + 1
  WHERE id = 42;
  ```

**Why:** Track overall progress for this run

**n8n Node:** Postgres "Update Execution" (ID: 11)

---

#### Step 4.3: Send Story Complete Notification
**What happens:**
- Ralph sends Telegram message:

**If success:**
```
✅ DONE: RIVET-001
Title: Usage Tracking System
Commit: abc123def456
Tokens: 12,345
Duration: 3m 0s
```

**If failure:**
```
❌ FAILED: RIVET-001
Title: Usage Tracking System
Error: Claude Code CLI timed out
Retry: 1 of 3
```

**Why:** Real-time progress updates for humans

**n8n Node:** Telegram "Send Complete" (ID: 12)

---

#### Step 4.4: Check For More Stories
**What happens:**
- Ralph queries database again:
  ```sql
  SELECT COUNT(*) as remaining
  FROM ralph_stories
  WHERE project_id = 1
    AND status = 'todo'
    AND retry_count < 3;
  ```

**Returns:**
- `{ remaining: 4 }` → More work to do
- `{ remaining: 0 }` → All done

**Why:** Decide whether to loop or finish

**n8n Node:** Postgres "Check More Stories" (ID: 13)

---

#### Step 4.5: Loop Decision
**What happens:**
- IF node checks `remaining > 0`
  - **TRUE:** Jump back to Step 2.1 (Get Next Story) ← **THE LOOP**
  - **FALSE:** Continue to finalization

**Why:** This is what makes Ralph autonomous - it keeps going until all stories are done

**n8n Node:** IF "Should Loop" (ID: 14)

**The Magic:** Node 14 has an outgoing connection that wires back to Node 4 (Get Next Story), creating a continuous loop.

---

### Phase 5: Finalization

#### Step 5.1: Finalize Execution Record
**What happens:**
- Ralph closes out the execution:
  ```sql
  UPDATE ralph_executions
  SET status = 'completed',
      completed_at = NOW(),
      stop_reason = 'All stories completed'
  WHERE id = 42;
  ```

**n8n Node:** Postgres "Finalize Execution" (ID: 15)

---

#### Step 5.2: Build Summary Report
**What happens:**
- Ralph queries final stats:
  ```sql
  SELECT
    stories_completed,
    stories_failed,
    total_tokens,
    total_iterations,
    completed_at - started_at as duration
  FROM ralph_executions
  WHERE id = 42;
  ```

- Formats a summary message

**n8n Node:** Code "Build Summary" (ID: 16)

---

#### Step 5.3: Send Completion Notification
**What happens:**
- Ralph sends final Telegram message:
  ```
  🏁 RALPH COMPLETE
  ✅ Stories completed: 5
  ❌ Stories failed: 0
  🔢 Total tokens: 67,890
  ⏱️ Duration: 15m 30s
  💰 Estimated cost: $0.34
  ```

**Why:** Let humans know Ralph is done and see the summary

**n8n Node:** Telegram "Send Complete" (ID: 17)

---

## The Database Schema Deep Dive

Ralph uses 4 PostgreSQL tables:

### Table 1: ralph_projects
**Purpose:** High-level project configuration

```sql
CREATE TABLE ralph_projects (
    id SERIAL PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    max_iterations INTEGER DEFAULT 50,
    token_budget INTEGER DEFAULT 500000,
    telegram_chat_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Example Data:**
```sql
INSERT INTO ralph_projects VALUES
(1, 'RIVET Pro', 50, 500000, '8445149012');
```

**Fields Explained:**
- `max_iterations`: Stop after this many stories (safety limit)
- `token_budget`: Stop if total tokens exceed this (cost control)
- `telegram_chat_id`: Where to send notifications

---

### Table 2: ralph_stories
**Purpose:** The backlog - what needs to be built

```sql
CREATE TABLE ralph_stories (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES ralph_projects(id),
    story_id VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    acceptance_criteria JSONB,
    ai_model VARCHAR(100) DEFAULT 'claude-sonnet-4-20250514',
    status VARCHAR(20) DEFAULT 'todo',
    status_emoji VARCHAR(10) DEFAULT '⬜',
    priority INTEGER DEFAULT 0,
    commit_hash VARCHAR(100),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, story_id)
);
```

**Example Data:**
```sql
INSERT INTO ralph_stories VALUES
(1, 1, 'RIVET-001', 'Usage Tracking System',
 'Track equipment lookups per user for freemium enforcement.',
 '["Track each photo upload", "Store user_id in Neon"]'::jsonb,
 'claude-sonnet-4-20250514', 'todo', '⬜', 1,
 NULL, NULL, 0, NULL, NULL, NOW());
```

**Status Flow:**
```
⬜ todo → 🟡 in_progress → ✅ done
                         ↘ ❌ failed → (retry_count++)
```

**Fields Explained:**
- `acceptance_criteria`: JSON array of requirements (becomes part of Claude prompt)
- `ai_model`: Which Claude model to use (Sonnet 4, Haiku, etc.)
- `priority`: Lower number = higher priority (processed first)
- `retry_count`: Failed stories get retried up to 3 times

---

### Table 3: ralph_executions
**Purpose:** Track each run of Ralph

```sql
CREATE TABLE ralph_executions (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES ralph_projects(id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    total_iterations INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    stories_completed INTEGER DEFAULT 0,
    stories_failed INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'running',
    stop_reason VARCHAR(100)
);
```

**Example Data After Completion:**
```sql
SELECT * FROM ralph_executions WHERE id = 42;

id  | 42
started_at | 2026-01-12 08:00:00
completed_at | 2026-01-12 08:15:30
total_iterations | 5
total_tokens | 67890
stories_completed | 5
stories_failed | 0
status | 'completed'
stop_reason | 'All stories completed'
```

**Use Case:** Track costs, performance over time

---

### Table 4: ralph_iterations
**Purpose:** Detailed log of each implementation attempt

```sql
CREATE TABLE ralph_iterations (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES ralph_projects(id),
    story_id INTEGER REFERENCES ralph_stories(id),
    execution_id INTEGER REFERENCES ralph_executions(id),
    iteration_number INTEGER,
    status VARCHAR(20),
    commit_hash VARCHAR(100),
    tokens_used INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Example Data:**
```sql
INSERT INTO ralph_iterations VALUES
(1, 1, 123, 42, 1, 'success', 'abc123', 12345, NULL, NOW());
```

**Use Case:**
- Debug failures (what error happened?)
- Track token usage per story
- Audit trail of code changes

---

## The MVP Stories (What Ralph Builds)

Ralph's initial backlog has 5 stories for RIVET Pro:

### Story 1: RIVET-001 - Usage Tracking System
**Priority:** 1 (highest)
**Model:** Sonnet 4 (most capable)

**What it does:**
- Tracks each photo analysis as 1 "lookup"
- Stores count per user in PostgreSQL
- Creates `get_usage_count(user_id)` function
- Blocks users at 10 free lookups

**Why:** Enable freemium model (free tier + paid tier)

---

### Story 2: RIVET-002 - Stripe Payment Integration
**Priority:** 2
**Model:** Sonnet 4

**What it does:**
- Creates Stripe product: "RIVET Pro" at $29/month
- Implements `/upgrade` command in Telegram bot
- Generates Stripe Checkout session URLs
- Handles payment webhooks
- Updates `user.is_pro = true` on successful payment

**Why:** Monetization - actually collect money

---

### Story 3: RIVET-003 - Free Tier Limit Enforcement
**Priority:** 3
**Model:** Sonnet 4

**What it does:**
- Before processing photo, check `get_usage_count(user_id)`
- If >= 10 and not Pro:
  - Return "🚫 Free limit reached. Upgrade to Pro: [link]"
  - Don't process the photo
- If Pro or < 10:
  - Process photo normally

**Why:** Actually enforce the limits (Stories 1 + 2 make this possible)

---

### Story 4: RIVET-004 - Shorten System Prompts
**Priority:** 4
**Model:** Haiku (fast, cheap for refactoring)

**What it does:**
- Audit all AI prompts in the codebase
- Cut each prompt by ~50% (remove filler, consolidate)
- Test that quality is maintained

**Why:** Faster responses, lower costs, better UX

---

### Story 5: RIVET-005 - Remove n8n Footer
**Priority:** 5
**Model:** Haiku

**What it does:**
- Find where "Powered by n8n" footer is added to Telegram messages
- Remove or override it
- Test all message types (photo analysis, commands, errors)

**Why:** Professional appearance (users shouldn't see internal tech)

---

## Cost Analysis

### Per Story
**Sonnet 4 (RIVET-001, 002, 003):**
- ~15,000 tokens input (codebase context)
- ~5,000 tokens output (generated code)
- **Cost:** ~$0.10 per story
- **Time:** 2-3 minutes

**Haiku (RIVET-004, 005):**
- ~8,000 tokens input
- ~2,000 tokens output
- **Cost:** ~$0.01 per story
- **Time:** 30-60 seconds

### Full Run (5 stories)
- **Total tokens:** ~67,000
- **Total cost:** ~$0.34
- **Total time:** ~15 minutes
- **Human time saved:** ~8 hours (if done manually)

**ROI:** $0.34 for 8 hours of work = **$0.04/hour** vs $50-150/hour for a human developer

---

## How To Use Ralph

### Setup (One Time)

1. **Create Database Tables:**
   ```sql
   psql "YOUR_DATABASE_URL" -f setup_ralph_supabase.sql
   ```

2. **Configure n8n Credentials:**
   - Add PostgreSQL credential pointing to your database
   - Add Telegram bot token
   - Assign credentials to all nodes

3. **Activate Workflows:**
   - Activate "Ralph - Main Loop"
   - Activate "Ralph - Implement Single Story" (worker)

4. **Add Stories:**
   ```sql
   INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, priority)
   VALUES (1, 'CUSTOM-001', 'Your Feature', 'Description', '["Criteria 1", "Criteria 2"]'::jsonb, 10);
   ```

### Run Ralph

**Option 1: Manual Trigger**
- Open n8n workflow
- Click "Execute Workflow" button

**Option 2: Webhook**
```bash
curl "https://your-n8n-instance.com/webhook/ralph-main-loop"
```

**Option 3: Schedule (Cron)**
- Add Schedule Trigger node
- Set to run: Daily at 2 AM, or every 6 hours, etc.

### Monitor Progress

**Telegram:**
- You'll receive messages in real-time as stories are processed

**Database:**
```sql
-- Check story status
SELECT story_id, status, status_emoji, commit_hash
FROM ralph_stories
ORDER BY priority;

-- Check current execution
SELECT * FROM ralph_executions
WHERE status = 'running'
ORDER BY started_at DESC
LIMIT 1;

-- See total progress
SELECT
  COUNT(*) FILTER (WHERE status = 'done') as done,
  COUNT(*) FILTER (WHERE status = 'todo') as todo,
  COUNT(*) FILTER (WHERE status = 'failed') as failed
FROM ralph_stories
WHERE project_id = 1;
```

---

## Troubleshooting

### Ralph Not Starting
**Symptom:** No Telegram message after triggering
**Causes:**
1. Workflow not activated (toggle ON in n8n)
2. Wrong Telegram chat ID
3. Database connection failed

**Fix:**
```bash
# Test database
psql "YOUR_DATABASE_URL" -c "SELECT 1;"

# Test Telegram
curl "https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id=8445149012&text=test"

# Check n8n logs
docker logs n8n-container -f
```

---

### Stories Not Processing
**Symptom:** Ralph starts but doesn't process stories
**Causes:**
1. No stories with `status = 'todo'`
2. Stories have `retry_count >= 3`
3. Claude Code CLI not installed on VPS

**Fix:**
```sql
-- Reset stories
UPDATE ralph_stories
SET status = 'todo', retry_count = 0
WHERE project_id = 1;

-- Check for stories
SELECT * FROM ralph_stories WHERE status = 'todo';
```

---

### Worker Workflow Fails
**Symptom:** Story marked 'failed' with error
**Causes:**
1. Claude Code CLI command syntax error
2. Insufficient permissions on VPS
3. Git repository not clean (uncommitted changes)

**Fix:**
```bash
# Test Claude Code manually
ssh root@72.60.175.144
cd /opt/Rivet-PRO
./venv/bin/claude-code --version

# Clean git
git status
git add .
git commit -m "Prep for Ralph"
```

---

### Loop Never Stops
**Symptom:** Ralph processes same story repeatedly
**Causes:**
1. Story update query failing (story stays 'todo')
2. Loop condition logic error

**Fix:**
- Check `ralph_stories` table directly
- Manually update story to 'done'
- Review n8n execution logs for SQL errors

---

## Advanced: Adding Your Own Stories

### Story Template

```sql
INSERT INTO ralph_stories (
    project_id,
    story_id,
    title,
    description,
    acceptance_criteria,
    ai_model,
    priority
) VALUES (
    1,  -- Project ID (RIVET Pro = 1)
    'CUSTOM-042',  -- Unique ID
    'Add User Authentication',  -- Short title
    'Implement JWT-based authentication for API endpoints. Users should login with email/password and receive a token valid for 7 days.',  -- Detailed description
    '[
        "Create /api/login endpoint that accepts email + password",
        "Generate JWT token on successful auth",
        "Token expires after 7 days",
        "Add middleware to verify token on protected routes",
        "Return 401 if token invalid or expired"
    ]'::jsonb,  -- Acceptance criteria (becomes part of Claude prompt)
    'claude-sonnet-4-20250514',  -- Model (use Sonnet 4 for complex, Haiku for simple)
    100  -- Priority (lower = sooner)
);
```

### Choosing The Right Model

| Model | Best For | Cost | Speed |
|-------|----------|------|-------|
| Sonnet 4 | Complex features, new systems, critical code | $$$ | Slow |
| Sonnet 3.5 | Medium complexity, refactoring | $$ | Medium |
| Haiku | Simple tasks, docs, prompts, UI tweaks | $ | Fast |

**Rule of thumb:**
- New feature with DB changes → Sonnet 4
- Refactoring existing code → Sonnet 3.5
- Docs, prompts, simple UI → Haiku

---

## The Vision: Self-Improving System

Ralph's ultimate goal is to **build itself**. Eventually Ralph will:

1. **Read user feedback** from Telegram/database
2. **Generate its own stories** based on feedback
3. **Prioritize stories** by impact
4. **Implement stories** autonomously
5. **Test in production**
6. **Roll back** if errors detected
7. **Repeat**

This creates a **flywheel**:
```
More users → More feedback → Better product → More users
```

With Ralph, the "Better product" step happens **automatically, 24/7**.

---

## Summary: The Ralph Loop in One Paragraph

Ralph is triggered → creates an execution record → fetches the highest-priority 'todo' story → marks it 'in_progress' → calls the worker workflow which runs Claude Code CLI to implement the story → worker returns commit hash and tokens → Ralph marks story 'done' → checks if more stories exist → if yes, loops back to fetch next story → if no, finalizes execution and sends completion message → Ralph sleeps until triggered again.

**The Magic:** The loop is self-contained in n8n. No external schedulers, no complex orchestration. Just a workflow that calls itself until the backlog is empty.

---

## Next Steps

1. ✅ VPS stabilized (you just did this!)
2. ⬜ Access n8n at http://72.60.175.144:5678
3. ⬜ Import Ralph workflows (or create following docs)
4. ⬜ Configure database credentials
5. ⬜ Test with one simple story
6. ⬜ Watch Ralph work its magic

---

**Questions?** Ask me anything about Ralph - I'll explain any part in more detail!
