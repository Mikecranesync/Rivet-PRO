# User Feedback Loop - Implementation Complete

## Overview

The user feedback loop system has been fully implemented. Users can now report issues via Telegram by replying to the bot's messages, which triggers an automated workflow where Ralph (the AI engineer) analyzes the issue, proposes a fix, waits for user approval, and then implements the fix with real-time progress updates.

**Status**: ✅ **Implementation Complete** - Ready for deployment and testing

---

## System Flow

```
USER (Telegram)
    ↓ Reply "not working" to bot message
TELEGRAM BOT
    ↓ Extract context + classify feedback type
    ↓ Store in interactions table
    ↓ POST to n8n webhook
N8N FEEDBACK WORKFLOW
    ↓ Validate input + Get user
    ↓ Generate story ID (FEEDBACK-404-20260112...)
    ↓ Call Claude for fix proposal
    ↓ Create ralph_story (status=pending_approval)
    ↓ Link to interaction bidirectionally
    ↓ Format Telegram message with 👍/👎 buttons
TELEGRAM BOT
    ↓ Send proposal to user
USER
    ↓ Click 👍 Approve
TELEGRAM BOT
    ↓ Update status to 'approved'
    ↓ POST to Ralph main loop (single_story mode)
RALPH MAIN LOOP
    ↓ Get approved story by story_id
    ↓ Call Claude to implement fix
    ↓ Commit changes to git
    ↓ Update status to 'done'
TELEGRAM BOT
    ↓ "✅ Fix deployed! Commit: abc123"
USER
    ↓ Try again → Issue resolved!
```

---

## Implementation Summary

### Phase 1: Database Schema ✅

**File**: `rivet_pro/migrations/014_feedback_loop.sql`

**What was added**:

**interactions table** (extended):
- `story_id` VARCHAR(50) - Links to ralph_stories.story_id
- `approval_status` VARCHAR(20) - pending/approved/rejected/expired
- `approved_at` TIMESTAMPTZ - When user approved
- `feedback_text` TEXT - User's issue description
- `context_data` JSONB - Extracted context (equipment_id, manual_url, etc.)

**ralph_stories table** (extended):
- `feedback_interaction_id` UUID - Links back to interactions.id
- `approval_status` VARCHAR(20) - auto_approved/pending_approval/approved/rejected
- `proposal_text` TEXT - Human-readable fix proposal
- `approved_by_telegram_id` VARCHAR(100) - Who approved
- `approved_at` TIMESTAMPTZ - When approved
- `feedback_type` VARCHAR(50) - manual_404, wrong_equipment, etc.

**Indexes added**:
- `idx_interactions_feedback` - Fast feedback queries
- `idx_ralph_stories_approval` - Fast approval queries

**Functions added**:
- `expire_pending_approvals()` - Auto-expire after 24 hours
- `link_feedback_and_story()` - Bidirectional linking helper

**Views added**:
- `pending_feedback_proposals` - Monitor pending approvals
- `approved_feedback_stories` - Queue of approved fixes
- `feedback_statistics` - Analytics

---

### Phase 2: FeedbackService (Business Logic) ✅

**File**: `rivet_pro/core/services/feedback_service.py`

**Key Methods**:

1. **`create_feedback()`**
   - Stores feedback in database
   - Checks rate limit (5 per hour)
   - Triggers n8n workflow via webhook
   - Returns interaction_id

2. **`approve_proposal()`**
   - Updates status to 'approved'
   - Links interaction and story
   - Triggers Ralph execution
   - Returns success/failure

3. **`reject_proposal()`**
   - Updates status to 'rejected'
   - Logs rejection reason
   - No Ralph execution

4. **`classify_feedback()`**
   - Detects feedback type from text
   - manual_404, wrong_manual, ocr_failure, etc.

5. **`extract_context()`**
   - Uses regex to extract data from bot message
   - Equipment number, manual URL, manufacturer, model

---

### Phase 3: Telegram Bot Handlers ✅

**File**: `rivet_pro/adapters/telegram/bot.py`

**Changes Made**:

1. **Imports added**:
   - `InlineKeyboardButton`, `InlineKeyboardMarkup`
   - `CallbackQueryHandler`
   - `FeedbackService`

2. **New Methods**:

   **`handle_message_reply()`** - Message router
   - Detects if message is reply to bot
   - Routes to feedback handler or normal handler

   **`_handle_feedback_reply()`** - Feedback processor
   - Extracts context from original message
   - Classifies feedback type
   - Stores in database via FeedbackService
   - Sends acknowledgment to user

   **`handle_proposal_callback()`** - Button click handler
   - Parses callback_data (approve_fix:STORY_ID)
   - Calls FeedbackService approve/reject
   - Edits message to show status

3. **Handler Registration** (in `build()` method):
   - CallbackQueryHandler registered BEFORE message handler
   - MessageHandler now routes through `handle_message_reply`

4. **Service Initialization** (in `start()` method):
   - `self.feedback_service = FeedbackService(self.db.pool)`

---

### Phase 4: n8n Feedback Workflow ✅

**File**: `rivet-n8n-workflow/user_feedback_loop.json`

**13-Node Workflow**:

1. **Webhook** - `/webhook/user-feedback` receives POST
2. **Validate Input** - Check required fields
3. **Get User** - Fetch from database
4. **Generate Story ID** - `FEEDBACK-{type}-{timestamp}`
5. **Build Claude Prompt** - Context + analysis instructions
6. **Call Claude API** - Generate fix proposal
7. **Parse Response** - Extract JSON from Claude
8. **Create Ralph Story** - INSERT with status='pending_approval'
9. **Link to Interaction** - UPDATE interactions.story_id
10. **Format Message** - Build Telegram message with buttons
11. **Send Proposal** - Telegram with inline keyboard 👍/👎
12. **Respond Success** - Return to webhook caller

**Webhook Payload**:
```json
{
  "interaction_id": "uuid",
  "telegram_user_id": "123456789",
  "feedback_text": "404 error on manual link",
  "feedback_type": "manual_404",
  "context": {
    "equipment_number": "EQ-2026-000001",
    "manufacturer": "Siemens",
    "model": "G120",
    "manual_url": "https://..."
  }
}
```

**Telegram Button Format**:
```json
{
  "inline_keyboard": [
    [
      {
        "text": "👍 Approve Fix",
        "callback_data": "approve_fix:FEEDBACK-001"
      },
      {
        "text": "👎 Reject",
        "callback_data": "reject_fix:FEEDBACK-001"
      }
    ]
  ]
}
```

---

### Phase 5: Ralph Main Loop Enhancement ✅

**File**: `rivet-n8n-workflow/ralph_main_loop_enhanced.json`

**Key Changes**:

1. **Check Execution Mode** (new node after webhook):
   - Parses `execution_mode` from request body
   - Defaults to 'full_queue' if not specified
   - Extracts `story_id` for single-story mode

2. **Conditional Story Query**:
   - **Single-story mode**: `SELECT * FROM ralph_stories WHERE story_id = '...'`
   - **Full queue mode**: `SELECT * ... WHERE status = 'todo' ... ORDER BY priority`

3. **Mode-aware execution**:
   - Single-story: Execute one story, then exit
   - Full queue: Loop through all pending stories

4. **Approval Status Filter** (queue mode):
   - Only processes stories with `approval_status = 'approved'` OR `'auto_approved'`
   - Skips stories pending user approval

**API Request Format**:
```json
{
  "execution_mode": "single_story",
  "story_id": "FEEDBACK-404-20260112",
  "triggered_by": "telegram_user_12345"
}
```

---

### Phase 6: Configuration ✅

**File**: `rivet_pro/config/settings.py`

**New Settings**:
```python
n8n_feedback_webhook_url: str = Field(
    "http://localhost:5678/webhook/user-feedback",
    description="n8n webhook URL for user feedback loop"
)

ralph_main_loop_url: str = Field(
    "http://localhost:5678/webhook/ralph-main-loop",
    description="Ralph main loop webhook for story execution"
)

feedback_max_per_hour: int = Field(
    5,
    description="Maximum feedback messages per user per hour"
)

feedback_approval_timeout_hours: int = Field(
    24,
    description="Hours before pending approvals expire"
)
```

**Environment Variables** (add to `.env`):
```bash
N8N_FEEDBACK_WEBHOOK_URL=http://localhost:5678/webhook/user-feedback
RALPH_MAIN_LOOP_URL=http://localhost:5678/webhook/ralph-main-loop
FEEDBACK_MAX_PER_HOUR=5
FEEDBACK_APPROVAL_TIMEOUT_HOURS=24
```

---

## Deployment Checklist

### 1. Database Migration

```bash
# Connect to Neon database
psql $DATABASE_URL

# Apply migration
\i rivet_pro/migrations/014_feedback_loop.sql

# Verify tables updated
\d interactions
\d ralph_stories

# Test functions
SELECT expire_pending_approvals();
```

### 2. Import n8n Workflows

**n8n Cloud UI**:
1. Go to n8n dashboard
2. Click "Import from File"
3. Upload `user_feedback_loop.json` → Activate
4. Upload `ralph_main_loop_enhanced.json` → Activate (or replace existing)
5. Configure credentials:
   - Telegram Bot API
   - Anthropic API (Claude)
   - PostgreSQL (Neon)
6. Test webhooks:
   - Test URL: `https://your-n8n.app.n8n.cloud/webhook/user-feedback`
   - Test URL: `https://your-n8n.app.n8n.cloud/webhook/ralph-main-loop`

### 3. Update .env on VPS

```bash
# SSH to VPS
ssh root@72.60.175.144

# Edit .env
cd Rivet-PRO
nano .env

# Add these lines:
N8N_FEEDBACK_WEBHOOK_URL=https://your-n8n.app.n8n.cloud/webhook/user-feedback
RALPH_MAIN_LOOP_URL=https://your-n8n.app.n8n.cloud/webhook/ralph-main-loop
FEEDBACK_MAX_PER_HOUR=5
FEEDBACK_APPROVAL_TIMEOUT_HOURS=24

# Save and exit (Ctrl+X, Y, Enter)
```

### 4. Deploy Bot Code to VPS

```bash
# From local machine
git add .
git commit -m "feat(FEEDBACK-LOOP): complete user feedback loop implementation"
git push origin ralph/mvp-phase1

# SSH to VPS
ssh root@72.60.175.144

# Pull changes
cd Rivet-PRO
git pull

# Restart bot
systemctl restart rivet-bots
# OR
pkill -f "orchestrator_bot" && python3 rivet_pro/main.py &

# Check logs
tail -f logs/rivet_pro.log
```

### 5. Verify Deployment

**Test Sequence**:
1. Send photo to bot → Get manual link
2. Reply to bot message with "404 error"
3. Check feedback stored: `SELECT * FROM interactions WHERE interaction_type = 'feedback' ORDER BY created_at DESC LIMIT 1;`
4. Wait for proposal (should arrive in ~30 seconds)
5. Click 👍 Approve
6. Check Ralph execution: `SELECT * FROM ralph_stories WHERE feedback_type IS NOT NULL;`
7. Wait for completion notification
8. Verify fix applied

---

## Testing Guide

### Unit Test (Without Database)

```bash
# Create test script
cat > test_feedback_classifier.py << 'EOF'
from rivet_pro.core.services.feedback_service import FeedbackService

# Mock database
class MockDB:
    pass

service = FeedbackService(MockDB())

# Test feedback classification
tests = [
    ("404 error", "manual_404"),
    ("wrong manual", "wrong_manual"),
    ("can't read nameplate", "ocr_failure"),
    ("slow performance", "performance_issue"),
    ("unclear answer", "unclear_answer"),
]

for text, expected in tests:
    result = service.classify_feedback(text, {})
    print(f"✓ {text[:20]:20} → {result:20} {'✓' if result == expected else '✗'}")
EOF

python test_feedback_classifier.py
```

### Integration Test (With Database)

```bash
# Create test script
cat > test_feedback_flow.py << 'EOF'
import asyncio
import httpx
from rivet_pro.infra.database import Database
from rivet_pro.core.services.feedback_service import FeedbackService

async def test_feedback():
    db = Database()
    await db.connect()

    service = FeedbackService(db.pool)

    # Get test user
    user = await db.fetchrow("SELECT id FROM users LIMIT 1")

    if not user:
        print("❌ No users found. Run bot first.")
        return

    # Create feedback
    print("Creating feedback...")
    interaction_id = await service.create_feedback(
        user_id=user['id'],
        feedback_text="Test feedback: Manual link returns 404",
        feedback_type="manual_404",
        context_data={
            "equipment_number": "EQ-2026-000001",
            "manual_url": "https://example.com/test.pdf"
        },
        telegram_user_id="123456789"
    )

    print(f"✅ Feedback created: {interaction_id}")

    # Check interaction
    interaction = await db.fetchrow(
        "SELECT * FROM interactions WHERE id = $1",
        interaction_id
    )
    print(f"✅ Interaction: {interaction['interaction_type']} | {interaction['approval_status']}")

    await db.disconnect()

asyncio.run(test_feedback())
EOF

python test_feedback_flow.py
```

### End-to-End Test

```bash
# Manual test via Telegram
1. Send photo to bot: @YourRivetBot
2. Wait for OCR result with manual link
3. Reply to bot's message: "404 error"
4. Bot should respond: "🔍 Analyzing your feedback..."
5. Wait ~30 seconds for proposal
6. Should receive proposal with 👍/👎 buttons
7. Click 👍 Approve
8. Bot should respond: "✅ APPROVED - Implementing fix now..."
9. Wait for completion (varies based on fix complexity)
10. Should receive: "✅ Fix deployed! Commit: abc123"
11. Send same photo again → Verify fix worked
```

---

## Monitoring & Observability

### Database Queries

**Pending proposals**:
```sql
SELECT * FROM pending_feedback_proposals;
```

**Approved stories**:
```sql
SELECT * FROM approved_feedback_stories;
```

**Feedback statistics**:
```sql
SELECT * FROM feedback_statistics;
```

**Recent feedback**:
```sql
SELECT
  i.created_at,
  i.feedback_text,
  i.approval_status,
  rs.story_id,
  rs.status as story_status
FROM interactions i
LEFT JOIN ralph_stories rs ON i.story_id = rs.story_id
WHERE i.interaction_type = 'feedback'
ORDER BY i.created_at DESC
LIMIT 10;
```

### Success Metrics

Track these KPIs:
- **Feedback capture rate**: % of users who report issues
- **Proposal quality**: % of proposals approved by users
- **Fix success rate**: % of approved fixes that work on retry
- **Time to resolution**: Average minutes from feedback to deployment
- **User satisfaction**: % who verify fix works

### Alerting

Set up alerts for:
- Feedback approval rate < 50% (proposals too risky)
- Fix success rate < 80% (implementation quality issue)
- Pending approvals > 10 (backlog growing)
- Rate limit violations > 5/day (potential abuse)

---

## Architecture Decisions

### 1. Bidirectional Foreign Keys

**Decision**: Both `interactions.story_id` and `ralph_stories.feedback_interaction_id`

**Rationale**:
- Full traceability in both directions
- No need for junction table
- Fast queries from either starting point

### 2. Approval Status in Both Tables

**Decision**: Separate `approval_status` columns in both tables

**Rationale**:
- Interaction tracks user's approval decision
- Story tracks Ralph's execution eligibility
- Allows different lifecycles

### 3. JSONB for Context Storage

**Decision**: `context_data JSONB` instead of fixed columns

**Rationale**:
- Flexible schema (different feedback types need different context)
- Can add new context fields without migration
- Fast indexing with GIN indexes (future)

### 4. Single-Story Execution Mode

**Decision**: Add mode parameter instead of separate workflow

**Rationale**:
- Reuses existing Ralph infrastructure
- No workflow duplication
- Easy to maintain

### 5. Human-in-the-Loop Approval

**Decision**: Require 👍 click before Ralph executes

**Rationale**:
- Safety: prevent unwanted auto-fixes
- Trust building: user sees proposed changes first
- Learning opportunity: track which proposals users prefer

---

## Known Limitations

1. **No Rollback**: If fix breaks something, requires manual revert
2. **Single Approval**: No multi-user approval workflow
3. **No A/B Testing**: Can't test fix on subset before full rollout
4. **Rate Limiting**: Simple per-hour limit, not intelligent throttling
5. **Context Extraction**: Regex-based, may miss edge cases

---

## Future Enhancements

### Phase 2 (Next)

1. **Automatic Categorization**: ML to classify feedback severity
2. **Batch Fixes**: Group similar issues into one story
3. **Learning Loop**: Track which fixes work best
4. **Analytics Dashboard**: Visualize feedback trends

### Phase 3 (Later)

1. **A/B Testing**: Test fix on subset before full rollout
2. **Rollback Mechanism**: Auto-revert if fix causes new issues
3. **Multi-user Approval**: Require N approvals for critical fixes
4. **Smart Rate Limiting**: Reputation-based throttling
5. **Visual Context**: Screenshot comparison before/after fix

---

## Troubleshooting

### Feedback not captured

**Check**:
1. User replied to bot's message (not new message)
2. FeedbackService initialized in bot
3. Webhook URL correct in settings
4. n8n workflow active

**Debug**:
```bash
# Check bot logs
tail -f logs/rivet_pro.log | grep "Feedback received"

# Check database
SELECT * FROM interactions WHERE interaction_type = 'feedback' ORDER BY created_at DESC LIMIT 5;
```

### Proposal not received

**Check**:
1. n8n workflow executed successfully
2. Claude API key valid
3. Telegram bot can send messages
4. Story created in database

**Debug**:
```bash
# Check n8n execution log
# Check ralph_stories table
SELECT * FROM ralph_stories WHERE feedback_type IS NOT NULL ORDER BY created_at DESC LIMIT 5;
```

### Fix not executed after approval

**Check**:
1. Ralph main loop webhook called
2. Story status changed to 'approved'
3. Ralph main loop workflow active
4. Claude API key valid

**Debug**:
```sql
-- Check approval status
SELECT story_id, approval_status, status, error_message
FROM ralph_stories
WHERE feedback_type IS NOT NULL
ORDER BY created_at DESC
LIMIT 5;

-- Check executions
SELECT * FROM ralph_executions ORDER BY created_at DESC LIMIT 5;
```

---

## Summary

✅ **Database schema** extended with feedback columns and indexes
✅ **FeedbackService** business logic layer created
✅ **Telegram bot** handlers added for feedback capture and approval
✅ **n8n feedback workflow** created (13 nodes)
✅ **Ralph main loop** enhanced with single-story mode
✅ **Configuration** updated with new settings

**Next Steps**:
1. Apply database migration
2. Import n8n workflows
3. Deploy bot code to VPS
4. Run end-to-end test
5. Monitor for 24 hours

**Implementation Date**: 2026-01-12
**Status**: ✅ Ready for Deployment
