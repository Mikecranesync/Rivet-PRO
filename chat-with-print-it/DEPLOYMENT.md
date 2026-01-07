# Chat with Print - Deployment Guide

Complete step-by-step deployment instructions for production.

## Overview

**Infrastructure:**
- VPS: 72.60.175.144
- n8n: http://72.60.175.144:5678
- Database: Neon PostgreSQL (managed)
- Telegram: Bot API
- Payments: Stripe

**Deployment time:** ~5-6 hours for complete production setup

---

## Phase 1: Infrastructure Setup (~2 hours)

### 1.1 Create Telegram Bot

Follow: `scripts/setup_telegram_bot.md`

**Deliverables:**
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET`

### 1.2 Configure Stripe

Follow: `scripts/setup_stripe.md`

**Deliverables:**
- `STRIPE_SECRET_KEY`
- `STRIPE_PRICE_ID`
- `STRIPE_CHECKOUT_URL`
- `STRIPE_WEBHOOK_SECRET`

### 1.3 Setup Slack

Follow: `scripts/setup_slack.md`

**Deliverables:**
- `SLACK_WEBHOOK_URL`

### 1.4 Get Claude API Key

1. Go to https://console.anthropic.com
2. Navigate to API Keys
3. Create new key for "Chat with Print"
4. Save as: `ANTHROPIC_API_KEY`

### 1.5 Get Database URL

**Option A: Use existing Neon database**
```bash
# Copy from existing .env or Neon dashboard
DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/dbname?sslmode=require
```

**Option B: Create new Neon database**
1. Go to https://neon.tech
2. Create new project: "Chat with Print"
3. Create database: `chatwithprint`
4. Copy connection string
5. Ensure `?sslmode=require` is appended

---

## Phase 2: Database Deployment (~5 minutes)

### 2.1 Set Environment Variable

```bash
export DATABASE_URL="postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/dbname?sslmode=require"
```

### 2.2 Run Deployment Script

```bash
cd chat-with-print-it
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

**Expected output:**
```
✅ Prerequisites OK
✅ Database schema deployed
✅ Table 'users' exists
✅ Table 'lookups' exists
✅ Table 'payments' exists
✅ Table 'daily_stats' exists
✅ 6 indexes created
✅ Function 'update_daily_stats' exists
✅ Database deployment complete!
```

### 2.3 Verify Tables

```bash
psql "$DATABASE_URL" -c "\dt"
```

Should show: `users`, `lookups`, `payments`, `daily_stats`

---

## Phase 3: n8n Configuration (~30 minutes)

### 3.1 Access n8n UI

Open browser: http://72.60.175.144:5678

### 3.2 Configure n8n Environment Variables

**Settings → Variables → Add Variable**

Add these variables:

| Variable Name | Value | Example |
|---------------|-------|---------|
| `ANTHROPIC_API_KEY` | Your Claude API key | `sk-ant-api03-xxx...` |
| `SLACK_WEBHOOK_URL` | Slack webhook URL | `https://hooks.slack.com/services/...` |
| `STRIPE_CHECKOUT_URL` | Stripe payment link | `https://buy.stripe.com/...` |
| `APP_URL` | Your app URL | `https://rivetpro.com` (or IP) |
| `N8N_URL` | n8n base URL | `http://72.60.175.144:5678` |

**⚠️ Important:** Click "Save" after adding each variable.

### 3.3 Import Workflows

For each workflow:

1. **Workflow 1: Core Bot**
   - Click "+ Add Workflow"
   - Click "..." menu (top right) → "Import from File"
   - Select `n8n-workflows/workflow_core_bot.json`
   - Click "Import"
   - Rename if needed: "Chat with Print - Core Bot"
   - **Save** (Ctrl+S or Save button)

2. **Workflow 2: Stripe Webhook**
   - Repeat above with `workflow_stripe_webhook.json`
   - Name: "Chat with Print - Stripe Webhook"
   - **Save**

3. **Workflow 3: Daily Summary**
   - Repeat above with `workflow_daily_summary.json`
   - Name: "Chat with Print - Daily Summary"
   - **Save**

### 3.4 Configure Credentials

**After importing, configure credentials for each workflow:**

#### For "Core Bot" workflow:

1. Open the workflow
2. Find "Telegram Trigger" node
3. Click on "Telegram Bot" credential dropdown
4. Select "Create New Credential"
5. Enter:
   - **Access Token:** `TELEGRAM_BOT_TOKEN` (from Phase 1.1)
6. Click "Save"
7. Find "PostgreSQL" nodes
8. Click on credential dropdown → "Create New Credential"
9. Enter connection details from `DATABASE_URL`:
   - **Host:** `ep-xxx.us-east-2.aws.neon.tech`
   - **Database:** `dbname`
   - **User:** `user`
   - **Password:** `pass`
   - **Port:** `5432`
   - **SSL:** `require` (enable)
10. Click "Save"
11. **Save workflow** (Ctrl+S)

#### For "Stripe Webhook" workflow:

1. Open the workflow
2. Configure PostgreSQL credential (same as above)
3. **Save workflow**

#### For "Daily Summary" workflow:

1. Open the workflow
2. Configure PostgreSQL credential (same as above)
3. **Save workflow**

### 3.5 Activate Workflows

For each workflow:

1. Open the workflow
2. Click "Inactive" toggle (top right)
3. Should change to "Active" (green)
4. Verify in workflows list - all 3 should show "Active"

---

## Phase 4: External Integrations (~10 minutes)

### 4.1 Set Telegram Webhook

```bash
export TELEGRAM_BOT_TOKEN="your_token_here"
export TELEGRAM_WEBHOOK_SECRET="your_secret_here"
export N8N_URL="http://72.60.175.144:5678"

chmod +x scripts/set_telegram_webhook.sh
./scripts/set_telegram_webhook.sh
```

**Expected output:**
```
✅ Webhook set successfully!
✅ No pending updates
```

**Verify:**
```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo" | jq '.'
```

Should show:
- `url`: `http://72.60.175.144:5678/webhook/telegram-trigger`
- `pending_update_count`: `0`

### 4.2 Set Stripe Webhook

**In Stripe Dashboard:**

1. Go to Developers → Webhooks
2. Click "+ Add endpoint"
3. **Endpoint URL:** `http://72.60.175.144:5678/webhook/stripe-webhook`
4. **Events to send:**
   - `checkout.session.completed`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
5. Click "Add endpoint"
6. Click "Reveal" signing secret
7. Verify it matches `STRIPE_WEBHOOK_SECRET` from Phase 1.2

---

## Phase 5: Testing (~1 hour)

### 5.1 Run Test Checklist

Follow: `scripts/test_checklist.md`

**Critical tests must pass:**
- ✅ Bot registration
- ✅ Photo analysis
- ✅ Free tier limit
- ✅ Command handlers
- ✅ Payment flow (test mode)
- ✅ Error handling
- ✅ Performance (<30s)

### 5.2 Check n8n Executions

1. Open n8n UI
2. Click "Executions" (left sidebar)
3. Verify all test executions show "Success" (green)
4. If any failures, click to see error details and fix

### 5.3 Check Database

```sql
-- Verify test data created
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM lookups;
SELECT COUNT(*) FROM payments WHERE status = 'complete';

-- Check latest user
SELECT * FROM users ORDER BY created_at DESC LIMIT 1;
```

---

## Phase 6: Go-Live Preparation (~30 minutes)

### 6.1 Security Checklist

- [ ] All API keys in n8n Variables (not hardcoded in workflows)
- [ ] Database uses SSL (`?sslmode=require` in DATABASE_URL)
- [ ] Stripe webhook signature verification enabled (check workflow)
- [ ] Telegram webhook secret configured
- [ ] No sensitive data in n8n execution logs
- [ ] `.env` files added to `.gitignore`

### 6.2 Performance Checklist

- [ ] Database indexes created (run `deploy.sh` if skipped)
- [ ] Claude API timeout set to 30s (check in workflow)
- [ ] n8n execution mode: "Regular" (Settings → Executions)
- [ ] Photo download timeout set (check Telegram Trigger node)

### 6.3 Monitoring Checklist

- [ ] Slack webhook working (test with `curl`)
- [ ] #chat-with-print-alerts channel created
- [ ] Daily summary scheduled for midnight UTC
- [ ] Error notifications enabled in all workflows

### 6.4 Backup & Recovery

- [ ] Neon automated backups enabled (check Neon dashboard)
- [ ] Workflows exported and committed to git:
   ```bash
   git add n8n-workflows/*.json
   git commit -m "Add production n8n workflows"
   git push origin feature/chat-with-print-it
   ```
- [ ] Environment variables documented in `.env.production`
- [ ] Test recovery: Can you restore from Neon backup?

---

## Phase 7: Launch 🚀

### 7.1 Final Health Check

```bash
./scripts/healthcheck.sh
```

All checks should pass (green).

### 7.2 Enable Production Mode

**For Stripe:**
1. Go to Stripe Dashboard
2. Toggle from "Test mode" to "Live mode"
3. Re-create Product, Price, and Webhook in live mode
4. Update `STRIPE_PRICE_ID`, `STRIPE_CHECKOUT_URL`, `STRIPE_WEBHOOK_SECRET` in n8n Variables
5. Update `STRIPE_SECRET_KEY` to live key

**For Telegram:**
- Already in production (no test mode)

### 7.3 Announce Launch

1. Test bot one more time with personal account
2. Share bot link: `https://t.me/your_bot_username`
3. Monitor Slack for first real users
4. Watch n8n executions for errors

---

## Troubleshooting

### Telegram webhook not working

**Symptom:** Bot doesn't respond to messages

**Fix:**
1. Check webhook status:
   ```bash
   curl "https://api.telegram.org/bot$TOKEN/getWebhookInfo"
   ```
2. If `pending_update_count` > 0, delete and reset:
   ```bash
   curl -X POST "https://api.telegram.org/bot$TOKEN/deleteWebhook?drop_pending_updates=true"
   ./scripts/set_telegram_webhook.sh
   ```
3. Check n8n "Telegram Trigger" node credentials

### n8n workflow execution fails

**Symptom:** Red "Failed" in executions list

**Fix:**
1. Click on failed execution
2. See which node failed (red icon)
3. Common issues:
   - **Database:** Check `DATABASE_URL` is correct
   - **Telegram:** Check bot token is valid
   - **Claude API:** Check `ANTHROPIC_API_KEY` is valid
   - **Variables:** Check all n8n Variables are set

### Stripe webhook not firing

**Symptom:** Payments complete but users not upgraded

**Fix:**
1. Check Stripe Dashboard → Developers → Webhooks
2. Click on your endpoint
3. Check "Recent events" - should show attempts
4. If failures, check signature verification in n8n workflow
5. Verify `STRIPE_WEBHOOK_SECRET` matches in both places

### Database connection errors

**Symptom:** "Connection refused" or "Authentication failed"

**Fix:**
1. Verify `DATABASE_URL` format:
   ```
   postgresql://user:pass@host:5432/db?sslmode=require
   ```
2. Check Neon dashboard - database is running
3. Test connection:
   ```bash
   psql "$DATABASE_URL" -c "SELECT 1;"
   ```
4. If still failing, regenerate Neon password and update `DATABASE_URL`

---

## Rollback Procedure

If critical issues occur post-launch:

### 1. Stop incoming traffic

```bash
# Disable Telegram webhook
curl -X POST "https://api.telegram.org/bot$TOKEN/deleteWebhook"
```

### 2. Deactivate n8n workflows

1. Open each workflow in n8n UI
2. Click "Active" toggle to disable
3. Verify "Inactive" (grey)

### 3. Investigate

1. Check n8n execution logs
2. Check Slack alerts
3. Query database for errors:
   ```sql
   SELECT * FROM lookups WHERE success = FALSE ORDER BY created_at DESC LIMIT 10;
   ```

### 4. Fix and re-test

1. Fix the issue
2. Re-run `scripts/test_checklist.md`
3. Verify all tests pass

### 5. Re-enable

```bash
# Re-enable Telegram webhook
./scripts/set_telegram_webhook.sh

# Reactivate n8n workflows (via UI)
```

---

## Post-Launch Monitoring

**First 24 hours:**
- Check Slack every 4 hours
- Review n8n executions hourly
- Monitor database performance

**Ongoing:**
- Daily: Review Slack summary
- Weekly: Check Stripe revenue vs database payments
- Monthly: Database cleanup (archive old lookups if needed)

---

## Support

For issues:
1. Check this guide's Troubleshooting section
2. Review `RUNBOOK.md` for operational procedures
3. Check n8n execution logs for error details
4. Review Neon database logs (if available)

**Monitoring:**
- Slack: #chat-with-print-alerts
- n8n: http://72.60.175.144:5678
- Database: Neon dashboard

---

**Deployment complete! 🎉**

Your Chat with Print bot is now live and ready to help technicians analyze electrical panels.
