# User Feedback Loop - Testing Guide

## Quick Start Testing (No Paid APIs Required)

This guide shows how to test the feedback loop system using free/local alternatives where possible.

---

## Prerequisites

✅ **Required**:
- Telegram account
- Access to Rivet Pro bot
- SSH access to VPS (72.60.175.144)
- Database access (Neon PostgreSQL)

⚠️ **Optional** (for full functionality):
- Groq API (free tier: 30 requests/min)
- Anthropic API (or use Groq fallback)

---

## Test Scenario 1: Manual 404 Feedback (Complete Flow)

### Setup Phase

**1. Deploy the code to VPS:**

```bash
# From local machine
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO

# Commit and push
git add .
git commit -m "feat(FEEDBACK-LOOP): user feedback loop implementation"
git push origin ralph/mvp-phase1

# SSH to VPS
ssh root@72.60.175.144

# Pull changes
cd Rivet-PRO
git pull origin ralph/mvp-phase1

# Check current bot status
ps aux | grep python | grep -i bot
```

**2. Apply database migration:**

```bash
# On VPS
cd Rivet-PRO

# Connect to Neon database
psql $DATABASE_URL

# Paste migration SQL
\i rivet_pro/migrations/014_feedback_loop.sql

# Verify tables updated
\d interactions
\d ralph_stories

# Check new columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'interactions'
  AND column_name IN ('story_id', 'feedback_text', 'context_data');

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'ralph_stories'
  AND column_name IN ('feedback_interaction_id', 'approval_status', 'proposal_text');

# Exit psql
\q
```

**3. Update environment variables:**

```bash
# On VPS
cd Rivet-PRO
nano .env

# Add these lines (update URLs to your n8n instance):
N8N_FEEDBACK_WEBHOOK_URL=https://your-n8n-instance.app.n8n.cloud/webhook/user-feedback
RALPH_MAIN_LOOP_URL=https://your-n8n-instance.app.n8n.cloud/webhook/ralph-main-loop
FEEDBACK_MAX_PER_HOUR=5
FEEDBACK_APPROVAL_TIMEOUT_HOURS=24

# Save and exit (Ctrl+X, Y, Enter)
```

**4. Import n8n workflows:**

Go to n8n dashboard:
1. Click "Workflows" → "Import from File"
2. Upload `rivet-n8n-workflow/user_feedback_loop.json`
3. Configure credentials:
   - PostgreSQL: Use existing Neon connection
   - Telegram Bot: Use existing bot credentials
   - Anthropic API: Add your API key (or skip for now)
4. Activate workflow
5. Copy webhook URL: `https://your-n8n.app.n8n.cloud/webhook/user-feedback`

Repeat for Ralph main loop:
1. Upload `rivet-n8n-workflow/ralph_main_loop_enhanced.json`
2. Configure same credentials
3. Activate workflow
4. Copy webhook URL: `https://your-n8n.app.n8n.cloud/webhook/ralph-main-loop`

**5. Restart bot with new code:**

```bash
# On VPS
cd Rivet-PRO

# Stop existing bot
pkill -f "orchestrator_bot" || pkill -f "rivet_pro"

# Start new bot
nohup python3 -m rivet_pro.main > logs/bot.log 2>&1 &

# Verify bot started
ps aux | grep python | grep -i rivet

# Check logs
tail -f logs/bot.log
# Press Ctrl+C to stop watching
```

---

### Testing Phase

**Step 1: Trigger Initial Interaction**

```
1. Open Telegram
2. Find your Rivet Pro bot
3. Send /start (if first time)
4. Send a photo of equipment nameplate
   - OR send text: "Find manual for Siemens G120"
5. Wait for bot response with manual link
```

**Expected Result**:
```
📖 User Manual
Siemens G120 Manual
https://example.com/siemens-g120.pdf

💡 Bookmark this for offline access.

Equipment ID: EQ-2026-000123 (✓ Matched)
```

**Step 2: Send Feedback (Reply to Bot Message)**

```
1. Click "Reply" on bot's message (IMPORTANT: must be a reply!)
2. Type: "404 error when I click the link"
3. Send
```

**Expected Result**:
```
🔍 Analyzing your feedback...

I'll generate a fix proposal and send it to you for approval shortly.
```

**Step 3: Verify Feedback Captured**

```bash
# On VPS, check database
psql $DATABASE_URL -c "
SELECT
  id,
  feedback_text,
  feedback_type,
  approval_status,
  context_data->>'manual_url' as manual_url
FROM interactions
WHERE interaction_type = 'feedback'
ORDER BY created_at DESC
LIMIT 1;
"
```

**Expected Output**:
```
                  id                  |      feedback_text       | feedback_type | approval_status |           manual_url
--------------------------------------+--------------------------+---------------+-----------------+--------------------------------
 abc12345-6789-...                    | 404 error when I cli...  | manual_404    | pending         | https://example.com/siemens...
```

**Step 4: Wait for Fix Proposal (~30-60 seconds)**

n8n workflow executes:
1. Validates input ✓
2. Gets user from database ✓
3. Generates story ID (e.g., FEEDBACK-404-20260112153045) ✓
4. Calls Claude/Groq for analysis ✓
5. Creates Ralph story (status=pending_approval) ✓
6. Sends Telegram message with buttons ✓

**Expected Telegram Message**:
```
🔧 Fix Proposal (FEEDBACK-404-20260112153045)

Issue:
The manual URL validation passed but the link returns 404,
indicating the PDF file was moved or deleted after validation.

Proposed Solution:
1. Add HTTP HEAD request check before returning URL to user
2. If 404, mark URL as stale in cache and re-search
3. Update manual_service.py to verify URL accessibility

Files to Change:
• rivet_pro/core/services/manual_service.py

Effort: 🟡 medium

Acceptance Criteria:
1. Manual URLs return 200 status before being sent to user
2. Stale URLs trigger automatic re-search
3. Cache is invalidated for 404 URLs

Review the proposal and approve to begin implementation.

[👍 Approve Fix] [👎 Reject]
```

**Step 5: Verify Story Created**

```bash
# Check Ralph story
psql $DATABASE_URL -c "
SELECT
  story_id,
  title,
  approval_status,
  status,
  feedback_type
FROM ralph_stories
WHERE feedback_type IS NOT NULL
ORDER BY created_at DESC
LIMIT 1;
"
```

**Expected Output**:
```
         story_id          |       title        | approval_status |  status  | feedback_type
---------------------------+--------------------+-----------------+----------+---------------
 FEEDBACK-404-20260112...  | Fix: manual_404    | pending_approval| todo     | manual_404
```

**Step 6: Approve Fix (Click 👍)**

```
1. In Telegram, click "👍 Approve Fix" button
```

**Expected Result**:
```
[Previous proposal message text...]

✅ APPROVED
⚙️ Implementing fix now... I'll send you real-time updates as I work on it.
```

**Step 7: Verify Approval Stored**

```bash
# Check approval
psql $DATABASE_URL -c "
SELECT
  rs.story_id,
  rs.approval_status,
  rs.approved_by_telegram_id,
  rs.status,
  i.approval_status as interaction_status
FROM ralph_stories rs
JOIN interactions i ON rs.feedback_interaction_id = i.id
WHERE rs.feedback_type IS NOT NULL
ORDER BY rs.created_at DESC
LIMIT 1;
"
```

**Expected Output**:
```
         story_id          | approval_status | approved_by_telegram_id | status | interaction_status
---------------------------+-----------------+-------------------------+--------+--------------------
 FEEDBACK-404-20260112...  | approved        | 123456789               | todo   | approved
```

**Step 8: Wait for Ralph Execution (2-5 minutes)**

Ralph main loop executes:
1. Receives webhook with execution_mode='single_story' ✓
2. Queries for story by story_id ✓
3. Marks story as 'in_progress' ✓
4. Builds Claude prompt ✓
5. Calls Claude API ✓
6. Implements fix ✓
7. Commits to git ✓
8. Updates story status to 'done' ✓

**Expected Telegram Updates**:
```
▶️ STARTING: FEEDBACK-404-20260112153045
Fix: manual_404

Mode: single_story
```

Then after completion:
```
✅ COMPLETED: FEEDBACK-404-20260112153045
Fix: manual_404

Commit: a1b2c3d4
Files changed: 1

Mode: single_story
```

**Step 9: Verify Fix Applied**

```bash
# Check story completion
psql $DATABASE_URL -c "
SELECT
  story_id,
  status,
  commit_hash,
  completed_at
FROM ralph_stories
WHERE feedback_type IS NOT NULL
ORDER BY created_at DESC
LIMIT 1;
"
```

**Expected Output**:
```
         story_id          | status |  commit_hash  |      completed_at
---------------------------+--------+---------------+-------------------------
 FEEDBACK-404-20260112...  | done   | a1b2c3d4e5f6  | 2026-01-12 15:35:22
```

```bash
# Check git log
cd Rivet-PRO
git log -1 --oneline

# Should show:
# a1b2c3d feat(FEEDBACK-404-20260112153045): Fix: manual_404
```

**Step 10: Verify Fix Works**

```
1. In Telegram, send same equipment photo again
   - OR send text: "Find manual for Siemens G120"
2. Click the manual link
3. Verify PDF loads (no 404)
```

**Expected Result**:
```
✅ Manual link works!
✅ No 404 error
✅ PDF downloads/displays correctly
```

---

## Test Scenario 2: Reject Proposal

**Step 1-5: Same as Scenario 1** (up to receiving proposal)

**Step 6: Reject Fix (Click 👎)**

```
1. In Telegram, click "👎 Reject" button
```

**Expected Result**:
```
[Previous proposal message text...]

❌ REJECTED
Thanks for the feedback! I won't implement this fix.
```

**Verify rejection stored:**

```bash
psql $DATABASE_URL -c "
SELECT
  story_id,
  approval_status,
  status
FROM ralph_stories
WHERE feedback_type IS NOT NULL
ORDER BY created_at DESC
LIMIT 1;
"
```

**Expected Output**:
```
         story_id          | approval_status | status
---------------------------+-----------------+--------
 FEEDBACK-404-20260112...  | rejected        | todo
```

**Result**: ✅ No Ralph execution, story stays in 'todo' with 'rejected' approval status

---

## Test Scenario 3: Multiple Feedback Messages (Rate Limiting)

**Test rate limiting:**

```
1. Send feedback message 1: "Link not working"
2. Send feedback message 2: "Wrong manual"
3. Send feedback message 3: "OCR failed"
4. Send feedback message 4: "Slow response"
5. Send feedback message 5: "Still broken"
6. Send feedback message 6: "Need help" ← Should be rate limited
```

**Expected Result for message 6**:
```
⚠️ Rate limit exceeded. Maximum 5 feedback messages per hour.
```

**Verify rate limit:**

```bash
psql $DATABASE_URL -c "
SELECT
  COUNT(*) as feedback_count,
  user_id
FROM interactions
WHERE interaction_type = 'feedback'
  AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY user_id;
"
```

**Expected Output**:
```
 feedback_count |              user_id
----------------+------------------------------------
              5 | abc12345-6789-0123-4567-89abcdef...
```

---

## Test Scenario 4: Expired Approval

**Test approval timeout (24 hours):**

```bash
# Manually set feedback to 25 hours ago
psql $DATABASE_URL -c "
UPDATE interactions
SET created_at = NOW() - INTERVAL '25 hours'
WHERE interaction_type = 'feedback'
  AND approval_status = 'pending'
LIMIT 1;
"

# Run expiration function
psql $DATABASE_URL -c "SELECT expire_pending_approvals();"
```

**Expected Output**:
```
 expire_pending_approvals
--------------------------
                        1
```

**Verify expiration:**

```bash
psql $DATABASE_URL -c "
SELECT
  story_id,
  approval_status,
  created_at
FROM ralph_stories
WHERE approval_status = 'expired';
"
```

---

## Test Scenario 5: Wrong Equipment Feedback

**Test different feedback type:**

```
1. Send photo to bot → Get equipment info
2. Reply: "This is the wrong equipment, it's actually a different model"
```

**Expected**:
- Feedback classified as `wrong_equipment`
- Proposal focuses on OCR accuracy improvement
- Different acceptance criteria than manual_404

---

## Monitoring During Tests

**Terminal 1 - Watch bot logs:**
```bash
ssh root@72.60.175.144
cd Rivet-PRO
tail -f logs/bot.log | grep -E "(Feedback|Proposal|Approval)"
```

**Terminal 2 - Watch database:**
```bash
# Run this in a loop
while true; do
  psql $DATABASE_URL -c "
  SELECT
    i.created_at,
    i.feedback_text,
    i.approval_status as i_approval,
    rs.story_id,
    rs.approval_status as rs_approval,
    rs.status
  FROM interactions i
  LEFT JOIN ralph_stories rs ON i.story_id = rs.story_id
  WHERE i.interaction_type = 'feedback'
  ORDER BY i.created_at DESC
  LIMIT 5;
  "
  sleep 5
done
```

**Terminal 3 - Watch n8n executions:**
```
1. Open n8n dashboard
2. Go to "Executions" tab
3. Filter by workflow: "User Feedback Loop"
4. Watch executions appear in real-time
```

---

## Troubleshooting

### Issue: Feedback not captured

**Debug:**
```bash
# Check if reply detection works
tail -f logs/bot.log | grep "Feedback received"

# If nothing appears, check if message was actually a reply
# Must click "Reply" on bot's message, not send new message
```

### Issue: No proposal received

**Debug:**
```bash
# Check n8n execution
# Go to n8n dashboard → Executions → User Feedback Loop
# Check for errors

# Check Claude API key
ssh root@72.60.175.144
cd Rivet-PRO
cat .env | grep ANTHROPIC_API_KEY

# If no key, Groq fallback should work
cat .env | grep GROQ_API_KEY
```

### Issue: Approval doesn't trigger Ralph

**Debug:**
```bash
# Check if approval was stored
psql $DATABASE_URL -c "
SELECT * FROM ralph_stories
WHERE story_id = 'FEEDBACK-XXX-XXXX'
  AND approval_status = 'approved';
"

# Check if Ralph webhook was called
# Go to n8n dashboard → Executions → Ralph Main Loop (Enhanced)
# Look for execution with execution_mode='single_story'

# If no execution, check webhook URL
ssh root@72.60.175.144
cd Rivet-PRO
cat .env | grep RALPH_MAIN_LOOP_URL
```

### Issue: Ralph execution fails

**Debug:**
```bash
# Check story error message
psql $DATABASE_URL -c "
SELECT
  story_id,
  status,
  error_message,
  retry_count
FROM ralph_stories
WHERE story_id = 'FEEDBACK-XXX-XXXX';
"

# Check Claude API quota
# Go to Anthropic dashboard → Usage

# Check git permissions
ssh root@72.60.175.144
cd Rivet-PRO
git status
git log -1
```

---

## Success Criteria

✅ **User can report issues**:
- Reply to bot message
- Feedback stored in database
- Acknowledgment received

✅ **Proposal generated**:
- Received within 60 seconds
- Contains 👍/👎 buttons
- Stored in ralph_stories

✅ **Approval workflow**:
- 👍 triggers Ralph execution
- 👎 rejects proposal
- Status updates in database

✅ **Ralph execution**:
- Story status changes: todo → in_progress → done
- Git commit created
- User notified of completion

✅ **Fix verification**:
- Original issue resolved
- User can verify fix works
- No new issues introduced

---

## Free Alternatives for Testing (No Paid APIs)

### Option 1: Mock n8n Workflows

Create simplified workflows without Claude API:

**Mock Feedback Workflow**:
```json
{
  "nodes": [
    {"name": "Webhook", "type": "webhook"},
    {"name": "Generate Mock Proposal", "type": "code",
     "jsCode": "return {json: {analysis: 'Mock fix', proposed_fix: 'Add validation', files_to_change: ['file.py']}}"},
    {"name": "Create Story", "type": "postgres"},
    {"name": "Send to Telegram", "type": "telegram"}
  ]
}
```

### Option 2: Test Locally (Without VPS)

```bash
# Run bot locally
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
python -m rivet_pro.main

# Use local n8n instance
docker run -it --rm --name n8n -p 5678:5678 n8nio/n8n

# Use SQLite instead of Neon
# (requires code modification)
```

### Option 3: Manual Testing (No Automation)

```bash
# Step 1: Create feedback manually
psql $DATABASE_URL -c "
INSERT INTO interactions (
  id, user_id, interaction_type, feedback_text, context_data
) VALUES (
  gen_random_uuid(),
  (SELECT id FROM users LIMIT 1),
  'feedback',
  'Test feedback',
  '{\"manual_url\": \"https://example.com/test.pdf\"}'::jsonb
);
"

# Step 2: Create story manually
psql $DATABASE_URL -c "
INSERT INTO ralph_stories (
  story_id, project_id, title, description,
  status, approval_status, feedback_type
) VALUES (
  'FEEDBACK-TEST-001',
  1,
  'Test fix',
  'Manual test',
  'todo',
  'approved',
  'manual_404'
);
"

# Step 3: Link them
psql $DATABASE_URL -c "
UPDATE interactions
SET story_id = 'FEEDBACK-TEST-001'
WHERE interaction_type = 'feedback'
ORDER BY created_at DESC
LIMIT 1;
"

# Step 4: Verify
psql $DATABASE_URL -c "
SELECT * FROM pending_feedback_proposals;
"
```

---

## Quick Test Checklist

```
□ Migration applied (014_feedback_loop.sql)
□ n8n workflows imported and active
□ Environment variables updated
□ Bot restarted with new code
□ Send photo to bot → Get manual
□ Reply to bot → "404 error"
□ Receive acknowledgment
□ Receive proposal with buttons (wait ~30s)
□ Click 👍 Approve
□ Receive "✅ APPROVED" message
□ Receive Ralph start notification
□ Receive Ralph completion notification (wait 2-5 min)
□ Verify git commit exists
□ Test original scenario → Issue fixed
```

---

**Time to Complete Full Test**: ~10 minutes per scenario

**Total Test Time**: ~30-45 minutes for all scenarios
