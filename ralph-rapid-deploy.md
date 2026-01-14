# RALPH RAPID DEPLOY
## Copy-Paste Everything Below - Build in 1 Hour

---

# PHASE 1: DATABASE (10 minutes)

Open Neon SQL Editor and run these in order:

## 1A: Schema

```sql
-- RUN THIS FIRST
CREATE TABLE IF NOT EXISTS ralph_projects (
  id SERIAL PRIMARY KEY,
  project_name VARCHAR(255) NOT NULL,
  max_iterations INTEGER DEFAULT 50,
  token_budget INTEGER DEFAULT 500000,
  telegram_chat_id VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ralph_stories (
  id SERIAL PRIMARY KEY,
  project_id INTEGER REFERENCES ralph_projects(id),
  story_id VARCHAR(50) NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  acceptance_criteria JSONB,
  status VARCHAR(20) DEFAULT 'todo',
  status_emoji VARCHAR(10) DEFAULT '⬜',
  priority INTEGER DEFAULT 0,
  commit_hash VARCHAR(100),
  error_message TEXT,
  retry_count INTEGER DEFAULT 0,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(project_id, story_id)
);

CREATE TABLE IF NOT EXISTS ralph_iterations (
  id SERIAL PRIMARY KEY,
  project_id INTEGER,
  story_id INTEGER,
  execution_id INTEGER,
  iteration_number INTEGER,
  status VARCHAR(20),
  commit_hash VARCHAR(100),
  tokens_used INTEGER,
  error_message TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ralph_executions (
  id SERIAL PRIMARY KEY,
  project_id INTEGER,
  started_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP,
  total_iterations INTEGER DEFAULT 0,
  total_tokens INTEGER DEFAULT 0,
  stories_completed INTEGER DEFAULT 0,
  stories_failed INTEGER DEFAULT 0,
  status VARCHAR(20) DEFAULT 'running',
  stop_reason VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_stories_status ON ralph_stories(project_id, status);
```

## 1B: Project + Stories

```sql
-- REPLACE 'YOUR_CHAT_ID' with your actual Telegram chat ID
INSERT INTO ralph_projects (project_name, max_iterations, token_budget, telegram_chat_id)
VALUES ('RIVET Pro', 50, 500000, 'YOUR_CHAT_ID');

-- RIVET Pro Stories - Phase 1 MVP
INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, priority, status, status_emoji) VALUES
(1, 'RIVET-001', 'Usage Tracking System', 
'Track equipment lookups per user for freemium enforcement.',
'["Track each photo upload as one lookup", "Store user_id and timestamp in Neon", "Create get_usage_count function", "Block at 10 free lookups with upgrade message"]'::jsonb,
1, 'todo', '⬜'),

(1, 'RIVET-002', 'Stripe Payment Integration', 
'Connect Stripe for Pro tier at $29/month.',
'["Create Stripe product/price for Pro $29/mo", "Implement checkout session endpoint", "Handle payment success webhook", "Update user subscription status", "Send Telegram confirmation"]'::jsonb,
2, 'todo', '⬜'),

(1, 'RIVET-003', 'Free Tier Limit Enforcement',
'Block lookups at 10 and show upgrade prompt.',
'["Check usage before processing photo", "Return upgrade message with Stripe link if limit hit", "Allow Pro users unlimited"]'::jsonb,
3, 'todo', '⬜'),

(1, 'RIVET-004', 'Shorten System Prompts',
'Cut all prompts by 50% for faster field responses.',
'["Audit all RIVET prompts", "Reduce each by 50%", "Remove filler text", "Test quality maintained"]'::jsonb,
4, 'todo', '⬜'),

(1, 'RIVET-005', 'Remove n8n Footer',
'Remove n8n branding from Telegram messages.',
'["Find where footer is added", "Remove or override it", "Test all message types"]'::jsonb,
5, 'todo', '⬜');

-- Verify
SELECT story_id, title, status_emoji || ' ' || status as status FROM ralph_stories;
```

---

# PHASE 2: WORKER WORKFLOW (20 minutes)

Create new workflow in n8n: "Ralph - Implement Single Story"

## Node 1: Execute Workflow Trigger
- Just add it, no config needed
- This receives data from main loop

## Node 2: Code - Validate & Start Timer
Name: `Validate Input`
```javascript
const input = $input.first().json;

if (!input.story_id || !input.prompt_text) {
  return [{
    json: {
      success: false,
      error_message: 'Missing story_id or prompt_text',
      story_id: input.story_id || 0,
      story_code: input.story_code || 'UNKNOWN',
      tokens_used: 0,
      iteration: input.iteration || 0,
      execution_id: input.execution_id || 0
    }
  }];
}

return [{
  json: {
    ...input,
    start_time: Date.now(),
    valid: true
  }
}];
```

## Node 3: IF - Check Valid
- Condition: `{{ $json.valid }}` equals `true`
- TRUE → Claude API
- FALSE → Return (end node)

## Node 4: HTTP Request - Claude API
Name: `Call Claude`
- Method: POST
- URL: `https://api.anthropic.com/v1/messages`
- Authentication: Header Auth
- Header Name: `x-api-key`
- Header Value: Your Anthropic API key (or use credential)
- Add Header: `anthropic-version` = `2023-06-01`
- Add Header: `content-type` = `application/json`
- Body (JSON):
```json
{
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 16000,
  "messages": [{"role": "user", "content": "{{ $json.prompt_text }}"}]
}
```
- Timeout: 180000
- **On Error: Continue** (important!)

## Node 5: Code - Parse Response
Name: `Parse Claude Response`
```javascript
const response = $input.first().json;
const input = $('Validate Input').first().json;
const duration = Math.round((Date.now() - input.start_time) / 1000);

// API error
if (response.error || !response.content) {
  return [{
    json: {
      success: false,
      story_id: input.story_id,
      story_code: input.story_code,
      error_message: response.error?.message || 'No response',
      commit_hash: null,
      tokens_used: 0,
      duration_seconds: duration,
      iteration: input.iteration,
      execution_id: input.execution_id
    }
  }];
}

const content = response.content[0]?.text || '';
const tokens = (response.usage?.input_tokens || 0) + (response.usage?.output_tokens || 0);

// Parse JSON from response
let result;
try {
  const match = content.match(/```json\s*([\s\S]*?)\s*```/) || 
                content.match(/(\{[\s\S]*"success"[\s\S]*\})/);
  result = JSON.parse(match[1] || match[0]);
} catch (e) {
  result = {
    success: false,
    error_message: 'Could not parse response',
    notes: content.substring(0, 500)
  };
}

return [{
  json: {
    success: result.success === true,
    story_id: input.story_id,
    story_code: input.story_code,
    commit_hash: result.commit_hash || null,
    error_message: result.error_message || null,
    files_changed: result.files_changed || [],
    notes: result.notes || '',
    tokens_used: tokens,
    duration_seconds: duration,
    iteration: input.iteration,
    execution_id: input.execution_id
  }
}];
```

## Node 6: Return node (or just end)
Connect Parse Response to the end

## Wire It:
```
Trigger → Validate → IF (true) → Claude API → Parse Response → End
                      ↓ (false)
                      End
```

**SAVE & ACTIVATE**

---

# PHASE 3: MAIN LOOP (30 minutes)

Create new workflow: "Ralph - Main Loop"

## Node 1: Webhook
- Path: `ralph-main-loop`
- Method: POST
- Response: Immediately

## Node 2: Telegram - Start
Name: `Send Start`
- Credential: Select your Telegram credential
- Chat ID: `{{ $json.body.chat_id || 'YOUR_DEFAULT_CHAT_ID' }}`
- Text:
```
🚀 RALPH STARTING
Project: RIVET Pro
Time: {{ $now }}
```
- Parse Mode: Markdown

## Node 3: Postgres - Create Execution
Name: `Create Execution`
- Operation: Execute Query
- Query:
```sql
INSERT INTO ralph_executions (project_id, status)
VALUES (1, 'running')
RETURNING id
```

## Node 4: Postgres - Get Next Story
Name: `Get Next Story`
- Operation: Execute Query
- Query:
```sql
SELECT * FROM ralph_stories 
WHERE project_id = 1 
AND status = 'todo' 
AND retry_count < 3
ORDER BY priority ASC 
LIMIT 1
```

## Node 5: Code - Check Stories
Name: `Check Stories Remain`
```javascript
const rows = $input.first().json;
const story = Array.isArray(rows) ? rows[0] : rows;
const execution = $('Create Execution').first().json;
const execId = Array.isArray(execution) ? execution[0].id : execution.id;

if (!story || !story.id) {
  return [{
    json: {
      continue_loop: false,
      reason: 'All stories completed!',
      execution_id: execId
    }
  }];
}

return [{
  json: {
    continue_loop: true,
    story: story,
    iteration: 1,
    execution_id: execId
  }
}];
```

## Node 6: IF - Continue?
Name: `Should Continue`
- Condition: `{{ $json.continue_loop }}` equals `true`
- TRUE → Build Prompt
- FALSE → Send Summary

## Node 7: Postgres - Mark In Progress
Name: `Mark In Progress`
- Operation: Execute Query
- Query:
```sql
UPDATE ralph_stories 
SET status = 'in_progress', status_emoji = '🟡', started_at = NOW()
WHERE id = {{ $json.story.id }}
```

## Node 8: Code - Build Prompt
Name: `Build Prompt`
```javascript
const story = $json.story;
const iteration = $json.iteration;

const prompt = `
# IMPLEMENT THIS STORY

## ${story.story_id}: ${story.title}

${story.description}

## Acceptance Criteria
${JSON.parse(JSON.stringify(story.acceptance_criteria)).map((c, i) => (i+1) + '. ' + c).join('\n')}

## RIVET Pro Context
- n8n workflows on VPS 72.60.175.144:5678
- Neon PostgreSQL database
- Telegram bot @rivet_local_dev_bot
- Gemini 2.5 Flash for vision, Claude for text
- Keep code SIMPLE, field techs need FAST responses

## Instructions
1. Implement completely
2. Keep it simple - CRAWL before RUN
3. Commit: "feat(${story.story_id}): ${story.title}"

Return ONLY JSON:
\`\`\`json
{
  "success": true,
  "commit_hash": "abc123",
  "files_changed": ["file1.js"],
  "notes": "What was done"
}
\`\`\`

Or if blocked:
\`\`\`json
{
  "success": false,
  "error_message": "What went wrong"
}
\`\`\`
`;

return [{
  json: {
    prompt_text: prompt,
    story_id: story.id,
    story_code: story.story_id,
    story_title: story.title,
    iteration: iteration,
    execution_id: $json.execution_id
  }
}];
```

## Node 9: Telegram - Story Start
Name: `Send Story Start`
- Chat ID: YOUR_CHAT_ID
- Text:
```
🟡 Starting: {{ $json.story_code }}
{{ $json.story_title }}
```

## Node 10: Execute Workflow - Call Worker
Name: `Call Worker`
- Workflow: Select "Ralph - Implement Single Story"
- Mode: Wait for completion
- Input data from: Current node input

## Node 11: Code - Process Result
Name: `Process Result`
```javascript
const r = $input.first().json;

const newStatus = r.success ? 'done' : 'failed';
const emoji = r.success ? '✅' : '🔴';

return [{
  json: {
    ...r,
    new_status: newStatus,
    status_emoji: emoji
  }
}];
```

## Node 12: Postgres - Update Story
Name: `Update Story Status`
- Operation: Execute Query
- Query:
```sql
UPDATE ralph_stories SET 
  status = '{{ $json.new_status }}',
  status_emoji = '{{ $json.status_emoji }}',
  commit_hash = {{ $json.commit_hash ? "'" + $json.commit_hash + "'" : 'NULL' }},
  error_message = {{ $json.error_message ? "'" + $json.error_message.replace(/'/g, "''") + "'" : 'NULL' }},
  completed_at = CASE WHEN '{{ $json.new_status }}' = 'done' THEN NOW() ELSE NULL END,
  retry_count = CASE WHEN '{{ $json.new_status }}' = 'failed' THEN retry_count + 1 ELSE retry_count END
WHERE id = {{ $json.story_id }}
```

## Node 13: Postgres - Update Execution
Name: `Update Execution`
- Query:
```sql
UPDATE ralph_executions SET
  total_iterations = total_iterations + 1,
  total_tokens = total_tokens + {{ $json.tokens_used || 0 }},
  stories_completed = stories_completed + {{ $json.success ? 1 : 0 }},
  stories_failed = stories_failed + {{ $json.success ? 0 : 1 }}
WHERE id = {{ $json.execution_id }}
```

## Node 14: Telegram - Result
Name: `Send Result`
- Text:
```
{{ $json.status_emoji }} {{ $json.new_status.toUpperCase() }}: {{ $json.story_code }}
{{ $json.commit_hash ? 'Commit: ' + $json.commit_hash.substring(0,8) : '' }}
{{ $json.error_message ? '⚠️ ' + $json.error_message.substring(0,200) : '' }}
```

## Node 15: Postgres - Check More Stories
Name: `Check More`
- Query:
```sql
SELECT COUNT(*) as remaining FROM ralph_stories 
WHERE project_id = 1 AND status = 'todo' AND retry_count < 3
```

## Node 16: Code - Should Loop
Name: `Should Loop`
```javascript
const result = $input.first().json;
const remaining = Array.isArray(result) ? result[0].remaining : result.remaining;

return [{
  json: {
    has_more: parseInt(remaining) > 0,
    execution_id: $('Process Result').first().json.execution_id
  }
}];
```

## Node 17: IF - Loop Back?
Name: `Loop Back?`
- Condition: `{{ $json.has_more }}` equals `true`
- TRUE → **CONNECT BACK TO "Get Next Story" (Node 4)** ← THE LOOP
- FALSE → Send Summary

## Node 18: Telegram - Summary
Name: `Send Summary`
- Text:
```
🏁 RALPH COMPLETE

Check database for results:
SELECT story_id, status_emoji, status FROM ralph_stories;
```

## Node 19: Postgres - Finalize
Name: `Finalize Execution`
- Query:
```sql
UPDATE ralph_executions SET 
  status = 'completed',
  completed_at = NOW()
WHERE id = {{ $json.execution_id }}
```

---

## WIRE THE MAIN LOOP:

```
Webhook → Send Start → Create Execution → Get Next Story → Check Stories
                                                              ↓
                                          ┌─── (false) ───→ Send Summary → Finalize
                                          ↓
                                    (true) Should Continue
                                          ↓
Mark In Progress → Build Prompt → Send Story Start → Call Worker → Process Result
                                                                        ↓
Update Story → Update Execution → Send Result → Check More → Should Loop
                                                                  ↓
                                              ┌──── (false) → Send Summary → Finalize
                                              ↓
                                        (true) LOOP BACK TO "Get Next Story"
```

**THE CRITICAL CONNECTION:**
Node 17 (Loop Back?) TRUE output → Node 4 (Get Next Story)

**SAVE & ACTIVATE**

---

# PHASE 4: TEST IT (5 minutes)

## Get your Telegram chat ID if you don't have it:
Message your bot, then:
```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/getUpdates"
```
Look for `"chat":{"id":XXXXXXXX`

## Update the project:
```sql
UPDATE ralph_projects SET telegram_chat_id = 'YOUR_CHAT_ID' WHERE id = 1;
```

## Trigger Ralph:
```bash
curl -X POST "http://72.60.175.144:5678/webhook/ralph-main-loop" \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1}'
```

## Or from n8n:
Click "Test Workflow" on Ralph - Main Loop

---

# WATCH TELEGRAM

You should see:
1. 🚀 RALPH STARTING
2. 🟡 Starting: RIVET-001
3. ✅ DONE or 🔴 FAILED
4. Repeat for each story
5. 🏁 RALPH COMPLETE

---

# TROUBLESHOOTING

## "No stories found"
```sql
SELECT * FROM ralph_stories WHERE status = 'todo';
```

## "Telegram not sending"
- Check credential is selected in each Telegram node
- Verify chat_id is a string (some need quotes)

## "Claude API error"
- Check API key in HTTP Request node
- Look at execution log for details

## "Loop not working"
- Verify Node 17 TRUE connects to Node 4
- Check the connection in n8n UI

## Reset and retry:
```sql
UPDATE ralph_stories SET status = 'todo', status_emoji = '⬜', 
  retry_count = 0, error_message = NULL, commit_hash = NULL,
  started_at = NULL, completed_at = NULL
WHERE project_id = 1;

DELETE FROM ralph_iterations WHERE project_id = 1;
DELETE FROM ralph_executions WHERE project_id = 1;
```

---

# TOTAL TIME: ~1 HOUR

- Phase 1 (SQL): 10 min
- Phase 2 (Worker): 20 min
- Phase 3 (Main Loop): 30 min
- Phase 4 (Test): 5 min

🚀 SHIP IT
