# CHAT WITH PRINT-IT - CLAUDE CODE CLI PROMPT

Copy everything below the line and paste into Claude Code CLI.

---

## CRITICAL: ADD TO CLAUDE SETTINGS

**Before running any commands, add this to your Claude Code settings:**

```json
{
  "dangerouslySkipPermissions": true
}
```

This allows autonomous execution without confirmation prompts.

---

## CONTEXT

I'm Mike, an industrial maintenance technician with 20+ years experience. I'm building RIVET Pro - an AI-powered maintenance assistant that helps field technicians identify equipment from photos and get instant troubleshooting guidance.

**My infrastructure:**
- VPS: 72.60.175.144
- Database: Neon PostgreSQL (I'll provide connection string)
- Redis: Running on VPS
- n8n: Running on VPS at port 5678
- Primary LLM: Claude API (I have API key)

**My timeline:** 
- Need a sellable MVP ASAP
- Must be production-ready for real users

**My philosophy:**
- CRAWL → WALK → RUN (basic first, solidify, then add complexity)
- Ship simple, iterate fast
- Partial service always better than complete failure
- Every interaction trains the system
- n8n workflows are THE source of truth - JSON files that AI can't accidentally break

---

## WHAT'S ALREADY BUILT

The following n8n workflow JSON files exist in `/chat-with-print-it/n8n-workflows/`:

1. **workflow_core_bot.json** - Main Telegram bot with:
   - Photo detection and routing
   - Claude Vision API integration for panel analysis
   - User tracking with PostgreSQL
   - Free tier limits (10 lookups)
   - Command handlers (/start, /help, /status, /upgrade)
   - Slack notifications for new users and errors
   - Error handling that never fails silently

2. **workflow_stripe_webhook.json** - Payment handling:
   - Webhook signature verification
   - checkout.session.completed → activate Pro
   - customer.subscription.deleted → deactivate Pro  
   - invoice.payment_failed → notify user
   - Slack notifications for new Pro subscribers

3. **workflow_daily_summary.json** - Monitoring:
   - Scheduled daily at midnight
   - Aggregates: new users, lookups, Pro subscribers, revenue
   - Sends summary to Slack
   - Saves to daily_stats table

**Database schema exists in** `/chat-with-print-it/database/schema.sql`

**Landing page exists in** `/chat-with-print-it/landing-page/index.html`

---

## YOUR TASK

Help me deploy and test this system. Specific tasks:

### 1. VERIFY WORKFLOWS
- Check that all workflow JSON files are valid and importable
- Verify node connections are correct
- Check for any missing credentials placeholders

### 2. DEPLOYMENT
- Run the database schema on Neon
- Import workflows to n8n via API or manual instructions
- Setup Telegram webhook
- Configure Stripe webhook endpoint

### 3. TESTING
- Test the Telegram bot end-to-end
- Verify user creation and lookup counting
- Test command handlers
- Verify Slack notifications work

### 4. ENHANCEMENTS (if time)
- Add conversation memory for multi-turn troubleshooting
- Improve response formatting
- Add more detailed error messages

---

## ENVIRONMENT VARIABLES NEEDED

```bash
# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=

# Claude API  
ANTHROPIC_API_KEY=

# Neon PostgreSQL
DATABASE_URL=

# Stripe
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_ID=
STRIPE_CHECKOUT_URL=

# Slack
SLACK_WEBHOOK_URL=

# App
APP_URL=https://rivetpro.com
N8N_URL=http://72.60.175.144:5678
```

---

## CONSTRAINTS

1. All n8n workflows must be valid JSON that can be imported directly
2. Every workflow must have error handling - no silent failures
3. All database queries must use parameterized queries (no SQL injection)
4. Response times under 30 seconds for analysis
5. Mobile-friendly landing page
6. NEVER modify the workflow JSON files without explicit permission

---

## START NOW

Begin by verifying the workflow files exist and are valid JSON, then give me step-by-step deployment instructions.
