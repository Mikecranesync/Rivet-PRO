# RALPH Main Loop - Rebuild with Supabase Nodes

## Step 1: Delete Old Workflow

1. Go to https://mikecranesync.app.n8n.cloud
2. Find "Ralph - Main Loop" in workflows list
3. Click the **⋮** (three dots) menu
4. Click **Delete**
5. Confirm deletion

---

## Step 2: Create New Workflow

1. Click **+ New Workflow** button
2. Name it: **"Ralph - Main Loop"**
3. Save the empty workflow

---

## Step 3: Add Nodes (Build in Order)

### NODE 1: Webhook Trigger

1. Click **+** → Search "Webhook"
2. Select **Webhook** trigger
3. Configure:
   - **HTTP Method**: GET
   - **Path**: `ralph-main-loop`
   - **Respond**: Immediately
4. Save node

---

### NODE 2: Telegram - Send Start

1. Click **+** → Search "Telegram"
2. Select **Telegram** node
3. Configure:
   - **Credential**: Select "Telegram - RALPH" (or create if needed)
   - **Resource**: Message
   - **Operation**: Send Message
   - **Chat ID**: `8445149012`
   - **Text**:
```
🚀 RALPH STARTING
Project: RIVET Pro
Time: {{ $now.format('yyyy-MM-dd HH:mm:ss') }}
```
4. Connect from Webhook node
5. Save node

---

### NODE 3: Supabase - Create Execution ⭐

1. Click **+** → Search "Supabase"
2. Select **Supabase** node (NOT Postgres!)
3. Name it: **"Create Execution"**
4. Configure:
   - **Credential**: Select "Supabase - RALPH"
   - **Operation**: Execute SQL
   - **Query**:
```sql
INSERT INTO ralph_executions (project_id, status)
VALUES (1, 'running')
RETURNING id
```
5. Connect from "Send Start" node
6. Save node

---

### NODE 4: Supabase - Get Next Story ⭐ (LOOP TARGET)

1. Click **+** → Search "Supabase"
2. Select **Supabase** node
3. Name it: **"Get Next Story"**
4. Configure:
   - **Credential**: Select "Supabase - RALPH"
   - **Operation**: Execute SQL
   - **Query**:
```sql
SELECT * FROM ralph_stories
WHERE project_id = 1
AND status = 'todo'
AND retry_count < 3
ORDER BY priority ASC
LIMIT 1
```
5. Connect from "Create Execution" node
6. Save node

---

### NODE 5: Code - Check Stories Remain

1. Click **+** → Search "Code"
2. Select **Code** node
3. Name it: **"Check Stories Remain"**
4. Configure:
   - **Mode**: Run Once for All Items
   - **JavaScript Code**:
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
5. Connect from "Get Next Story" node
6. Save node

---

### NODE 6: IF - Should Continue

1. Click **+** → Search "IF"
2. Select **IF** node
3. Name it: **"Should Continue"**
4. Configure:
   - **Condition**: Data of an expression
   - **Value 1**: `{{ $json.continue_loop }}`
   - **Operation**: Equal
   - **Value 2**: `true`
5. Connect from "Check Stories Remain" node
6. Save node

---

### NODE 7: Supabase - Mark In Progress ⭐

1. Click **+** → Search "Supabase"
2. Select **Supabase** node
3. Name it: **"Mark In Progress"**
4. Configure:
   - **Credential**: Select "Supabase - RALPH"
   - **Operation**: Execute SQL
   - **Query**:
```sql
UPDATE ralph_stories
SET status = 'in_progress', status_emoji = '🟡', started_at = NOW()
WHERE id = {{ $json.story.id }}
```
5. Connect from "Should Continue" **TRUE** output
6. Save node

---

### NODE 8: Code - Build Prompt

1. Click **+** → Search "Code"
2. Select **Code** node
3. Name it: **"Build Prompt"**
4. **JavaScript Code**:
```javascript
const story = $json.story;
const iteration = $json.iteration;

const criteriaList = story.acceptance_criteria.map((c, i) => (i+1) + '. ' + c).join('\n');

const prompt = `# IMPLEMENT THIS STORY

## ${story.story_id}: ${story.title}

${story.description}

## Acceptance Criteria
${criteriaList}

## RIVET Pro Context
- Repository: C:\\Users\\hharp\\OneDrive\\Desktop\\Rivet-PRO
- Branch: feat/github-actions-claude-integration
- n8n Cloud: mikecranesync.app.n8n.cloud:5678
- Supabase PostgreSQL database (db.mggqgrxwumnnujojndub.supabase.co)
- Telegram bot: 8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE
- Keep code SIMPLE - field techs need FAST responses

## Instructions
1. Implement completely using existing rivet_pro/ infrastructure
2. Keep it simple - CRAWL before RUN
3. Commit: "feat(${story.story_id}): ${story.title}"

Return ONLY JSON:
\`\`\`json
{
  "success": true,
  "commit_hash": "abc123",
  "files_changed": ["file1.py"],
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
    ai_model: story.ai_model,
    iteration: iteration,
    execution_id: $json.execution_id
  }
}];
```
5. Connect from "Mark In Progress" node
6. Save node

---

### NODE 9: Telegram - Story Start

1. Click **+** → Search "Telegram"
2. Select **Telegram** node
3. Name it: **"Story Start"**
4. Configure:
   - **Credential**: Select "Telegram - RALPH"
   - **Resource**: Message
   - **Operation**: Send Message
   - **Chat ID**: `8445149012`
   - **Text**:
```
🟡 STARTING: {{ $json.story_code }}
{{ $json.story_title }}
Model: {{ $json.ai_model.includes('sonnet-4') ? '🧠 Sonnet 4' : '⚡ Haiku' }}
```
5. Connect from "Build Prompt" node
6. Save node

---

### NODE 10: Execute Workflow - Call Worker

1. Click **+** → Search "Execute Workflow"
2. Select **Execute Workflow** node
3. Name it: **"Call Worker"**
4. Configure:
   - **Source**: Database
   - **Workflow**: Select "Ralph - Implement Single Story" (ID: ovTlTYSu97mWj-yc0J_yi)
   - **Wait for Completion**: Yes
5. Connect from "Story Start" node
6. Save node

---

### NODE 11: Code - Process Result

1. Click **+** → Search "Code"
2. Select **Code** node
3. Name it: **"Process Result"**
4. **JavaScript Code**:
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
5. Connect from "Call Worker" node
6. Save node

---

### NODE 12: Supabase - Update Story ⭐

1. Click **+** → Search "Supabase"
2. Select **Supabase** node
3. Name it: **"Update Story"**
4. Configure:
   - **Credential**: Select "Supabase - RALPH"
   - **Operation**: Execute SQL
   - **Query**:
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
5. Connect from "Process Result" node
6. Save node

---

### NODE 13: Supabase - Update Execution ⭐

1. Click **+** → Search "Supabase"
2. Select **Supabase** node
3. Name it: **"Update Execution"**
4. Configure:
   - **Credential**: Select "Supabase - RALPH"
   - **Operation**: Execute SQL
   - **Query**:
```sql
UPDATE ralph_executions SET
  total_iterations = total_iterations + 1,
  total_tokens = total_tokens + {{ $json.tokens_used || 0 }},
  stories_completed = stories_completed + {{ $json.success ? 1 : 0 }},
  stories_failed = stories_failed + {{ $json.success ? 0 : 1 }}
WHERE id = {{ $json.execution_id }}
```
5. Connect from "Update Story" node
6. Save node

---

### NODE 14: Telegram - Send Result

1. Click **+** → Search "Telegram"
2. Select **Telegram** node
3. Name it: **"Send Result"**
4. Configure:
   - **Credential**: Select "Telegram - RALPH"
   - **Resource**: Message
   - **Operation**: Send Message
   - **Chat ID**: `8445149012`
   - **Text**:
```
{{ $json.status_emoji }} {{ $json.new_status.toUpperCase() }}: {{ $json.story_code }}
{{ $json.commit_hash ? 'Commit: ' + $json.commit_hash.substring(0,8) : '' }}
{{ $json.error_message ? '⚠️ ' + $json.error_message.substring(0,200) : '' }}
Tokens: {{ $json.tokens_used || 0 }}
```
5. Connect from "Update Execution" node
6. Save node

---

### NODE 15: Supabase - Check More Stories ⭐

1. Click **+** → Search "Supabase"
2. Select **Supabase** node
3. Name it: **"Check More Stories"**
4. Configure:
   - **Credential**: Select "Supabase - RALPH"
   - **Operation**: Execute SQL
   - **Query**:
```sql
SELECT COUNT(*) as remaining FROM ralph_stories
WHERE project_id = 1 AND status = 'todo' AND retry_count < 3
```
5. Connect from "Send Result" node
6. Save node

---

### NODE 16: Code - Should Loop

1. Click **+** → Search "Code"
2. Select **Code** node
3. Name it: **"Should Loop"**
4. **JavaScript Code**:
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
5. Connect from "Check More Stories" node
6. Save node

---

### NODE 17: IF - Loop Back? 🔁 CRITICAL

1. Click **+** → Search "IF"
2. Select **IF** node
3. Name it: **"Loop Back?"**
4. Configure:
   - **Condition**: Data of an expression
   - **Value 1**: `{{ $json.has_more }}`
   - **Operation**: Equal
   - **Value 2**: `true`
5. Connect from "Should Loop" node
6. **TRUE output**: DO NOT CONNECT YET (we'll loop back in Step 4)
7. **FALSE output**: Continue to next node
8. Save node

---

### NODE 18: Telegram - Send Summary

1. Click **+** → Search "Telegram"
2. Select **Telegram** node
3. Name it: **"Send Summary"**
4. Configure:
   - **Credential**: Select "Telegram - RALPH"
   - **Resource**: Message
   - **Operation**: Send Message
   - **Chat ID**: `8445149012`
   - **Text**:
```
🏁 RALPH COMPLETE

Check results:
SELECT story_id, status_emoji, status, commit_hash
FROM ralph_stories
ORDER BY priority;
```
5. Connect from "Loop Back?" **FALSE** output
6. Also connect from "Should Continue" **FALSE** output (this handles "no stories found" case)
7. Save node

---

### NODE 19: Supabase - Finalize Execution ⭐

1. Click **+** → Search "Supabase"
2. Select **Supabase** node
3. Name it: **"Finalize Execution"**
4. Configure:
   - **Credential**: Select "Supabase - RALPH"
   - **Operation**: Execute SQL
   - **Query**:
```sql
UPDATE ralph_executions SET
  status = 'completed',
  completed_at = NOW()
WHERE id = {{ $json.execution_id }}
```
5. Connect from "Send Summary" node
6. Save node

---

## Step 4: Wire the Loop-Back Connection 🔁

**CRITICAL**: This creates the loop that processes all stories!

1. Find **Node 17 (Loop Back? IF)**
2. Drag from its **TRUE** output
3. Connect it back to **Node 4 (Get Next Story)**

This creates the visual loop-back that processes stories sequentially.

---

## Step 5: Activate Workflow

1. Click **Active** toggle in top-right (switch to ON)
2. Workflow should now be active and ready

---

## Step 6: Test the Workflow

**Method 1 - Webhook Trigger**:
```bash
curl "https://mikecranesync.app.n8n.cloud/webhook/ralph-main-loop"
```

**Method 2 - Manual Test**:
1. In n8n, click **Test Workflow** button
2. Click **Execute** on the Webhook node
3. Watch execution flow in real-time

---

## Verification Checklist

- [ ] All 19 nodes created
- [ ] 7 Supabase nodes (⭐) using "Supabase - RALPH" credential
- [ ] Loop-back connection wired (Node 17 TRUE → Node 4)
- [ ] Workflow activated
- [ ] Telegram messages arrive in chat 8445149012
- [ ] Database updates visible in Supabase

---

## 7 Supabase Nodes to Double-Check

| # | Node Name | Type | Credential |
|---|-----------|------|------------|
| 3 | Create Execution | Supabase | Supabase - RALPH |
| 4 | Get Next Story | Supabase | Supabase - RALPH |
| 7 | Mark In Progress | Supabase | Supabase - RALPH |
| 12 | Update Story | Supabase | Supabase - RALPH |
| 13 | Update Execution | Supabase | Supabase - RALPH |
| 15 | Check More Stories | Supabase | Supabase - RALPH |
| 19 | Finalize Execution | Supabase | Supabase - RALPH |

All must be **Supabase** nodes (NOT Postgres)!

---

## Troubleshooting

**"Can't find Supabase node"**:
- Make sure you're searching for "Supabase" exactly
- If it doesn't appear, your n8n version might not have it - try "Postgres" but it may not work as reliably

**"Connection failed"**:
- Verify Supabase credential is correct
- Test connection in Settings → Credentials → Supabase - RALPH

**"Loop not working"**:
- Verify visual connection from Node 17 TRUE → Node 4
- Check n8n execution log for errors

**"Stories not found"**:
- Run this in Supabase SQL Editor:
```sql
SELECT story_id, status FROM ralph_stories ORDER BY priority;
```
- If empty, re-run the migration

---

Ready to build! Start with Step 1 and work through sequentially.
