# START HERE - Quick Deployment Guide

## Step 1: Get Your Credentials (Start Now!)

Open these in separate browser tabs and collect your credentials:

### 1a. Create Telegram Bot (5 minutes)
1. Open Telegram, search for `@BotFather`
2. Send: `/newbot`
3. Name: `Chat with Print` (or your choice)
4. Username: `chatwithprint_bot` (must end in "bot")
5. **Copy the token** - save it as `TELEGRAM_BOT_TOKEN`
6. Generate webhook secret:
   ```bash
   openssl rand -hex 32
   ```
   Save this as `TELEGRAM_WEBHOOK_SECRET`

### 1b. Get Claude API Key (2 minutes)
1. Go to: https://console.anthropic.com
2. Click "API Keys" → "Create Key"
3. Name: "Chat with Print"
4. **Copy the key** - save it as `ANTHROPIC_API_KEY`

### 1c. Get Database URL (2 minutes)
**Do you already have a Neon database?**
- **Yes:** Copy your existing `DATABASE_URL` from `.env` or Neon dashboard
- **No:** Go to https://neon.tech → Create project → Copy connection string

Make sure it ends with `?sslmode=require`

### 1d. Setup Stripe (10 minutes)
1. Go to: https://dashboard.stripe.com
2. **Toggle to TEST MODE** (top right - we'll test first, then go live)
3. Create Product:
   - Products → "+ Add product"
   - Name: "Chat with Print Pro"
   - Price: $29/month
   - **Copy Price ID** (starts with `price_`)
4. Create Payment Link:
   - More → Payment links → "+ New"
   - Select your product
   - **Copy the URL** (starts with `https://buy.stripe.com/`)
5. Get API Key:
   - Developers → API Keys
   - **Copy "Secret key"** (starts with `sk_test_` for test mode)

**DON'T CREATE WEBHOOK YET** - we'll do that after n8n is configured

### 1e. Setup Slack (5 minutes)
1. Go to your Slack workspace (or create one at https://slack.com)
2. Create channel: `#chat-with-print-alerts`
3. Add Incoming Webhook:
   - Click workspace name → Settings & admin → Manage apps
   - Search "Incoming Webhooks" → Add to Slack
   - Choose `#chat-with-print-alerts`
   - **Copy Webhook URL**

---

## Step 2: Deploy Database (5 minutes)

```bash
# Navigate to project
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO-chat-with-print\chat-with-print-it

# Set database URL (paste your actual URL)
export DATABASE_URL="postgresql://user:pass@host/db?sslmode=require"

# Run deployment
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

**Expected output:** All green checkmarks for tables, indexes, and functions

---

## Step 3: Configure n8n (20 minutes)

### 3a. Add Environment Variables

1. Open: http://72.60.175.144:5678
2. Go to: Settings → Variables
3. Click "+ Add Variable" for each:

| Variable Name | Value |
|---------------|-------|
| `ANTHROPIC_API_KEY` | Your Claude API key from Step 1b |
| `SLACK_WEBHOOK_URL` | Your Slack webhook from Step 1e |
| `STRIPE_CHECKOUT_URL` | Your payment link from Step 1d |
| `APP_URL` | `http://72.60.175.144` (or your domain) |
| `N8N_URL` | `http://72.60.175.144:5678` |

### 3b. Import Workflows

For each workflow:

1. Click "+ Add Workflow" (top left)
2. Click "..." menu → "Import from File"
3. Navigate to: `C:\Users\hharp\OneDrive\Desktop\Rivet-PRO-chat-with-print\chat-with-print-it\n8n-workflows\`
4. Import these 3 files:
   - `workflow_core_bot.json`
   - `workflow_stripe_webhook.json`
   - `workflow_daily_summary.json`

### 3c. Configure Credentials

**For "Chat with Print - Core Bot" workflow:**

1. Open the workflow
2. Click "Telegram Trigger" node
3. Under Credential, click "Create New"
4. Enter your `TELEGRAM_BOT_TOKEN` from Step 1a
5. Save

6. Click any "PostgreSQL" node
7. Under Credential, click "Create New"
8. Enter your database details from `DATABASE_URL`:
   - Host: `ep-xxxxx.us-east-2.aws.neon.tech`
   - Database: `dbname`
   - User: `user`
   - Password: `password`
   - Port: `5432`
   - SSL: Enable/Require
9. Save
10. **Save workflow** (Ctrl+S)

**For "Stripe Webhook" workflow:**
1. Open workflow
2. Click PostgreSQL node → Use same credential as above
3. Save workflow

**For "Daily Summary" workflow:**
1. Open workflow
2. Click PostgreSQL node → Use same credential as above
3. Save workflow

### 3d. Activate All Workflows

1. Open each workflow
2. Click "Inactive" toggle → Should turn to "Active" (green)
3. Verify all 3 are active

---

## Step 4: Set Webhooks (5 minutes)

### 4a. Telegram Webhook

```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO-chat-with-print\chat-with-print-it

# Set your credentials
export TELEGRAM_BOT_TOKEN="your_token_from_step_1a"
export TELEGRAM_WEBHOOK_SECRET="your_secret_from_step_1a"
export N8N_URL="http://72.60.175.144:5678"

# Run script
chmod +x scripts/set_telegram_webhook.sh
./scripts/set_telegram_webhook.sh
```

**Expected:** ✅ Webhook set successfully!

### 4b. Stripe Webhook

1. Go to: https://dashboard.stripe.com/test/webhooks
2. Click "+ Add endpoint"
3. Endpoint URL: `http://72.60.175.144:5678/webhook/stripe-webhook`
4. Events to send:
   - `checkout.session.completed`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
5. Click "Add endpoint"
6. Click "Reveal" on Signing Secret
7. **Copy the secret** (starts with `whsec_`)

**Save this as `STRIPE_WEBHOOK_SECRET`** - you'll need it if webhook fails

---

## Step 5: TEST! (30 minutes)

### Quick Smoke Test (5 minutes)

1. **Open Telegram**, search for your bot by username
2. **Send:** `/start`
3. **Expected:** Welcome message

4. **Take a photo** of any electrical panel (or find one online)
5. **Send the photo** to your bot
6. **Expected:**
   - "Analyzing..." message
   - Within 30 seconds: Detailed analysis response

7. **Check Slack:** You should see:
   - New user notification
   - (Optionally) lookup notification

**✅ If this works, your bot is LIVE!**

### Full Test Suite

Follow the complete checklist:
```bash
cat scripts/test_checklist.md
```

Run through all 10 tests to verify:
- ✅ User registration
- ✅ Photo analysis
- ✅ Free tier limit (10 lookups)
- ✅ Commands (/help, /status, /upgrade)
- ✅ Payment flow (use test card: 4242 4242 4242 4242)
- ✅ Error handling
- ✅ Performance (<30s)

---

## Step 6: Go Live (When Ready)

**After all tests pass:**

1. **Switch Stripe to Live Mode:**
   - Dashboard → Toggle to "Live mode"
   - Re-create Product, Price, Payment Link in live mode
   - Update n8n Variables with live Stripe keys (`sk_live_xxx`)
   - Re-create webhook in live mode

2. **Share your bot:**
   - Link: `https://t.me/your_bot_username`

3. **Monitor:**
   - Slack: #chat-with-print-alerts
   - n8n: http://72.60.175.144:5678 (Executions tab)

---

## Quick Reference

| Resource | Location |
|----------|----------|
| **n8n Dashboard** | http://72.60.175.144:5678 |
| **Health Check** | `./scripts/healthcheck.sh` |
| **Full Deployment Guide** | `DEPLOYMENT.md` |
| **Operations Manual** | `RUNBOOK.md` |
| **Test Checklist** | `scripts/test_checklist.md` |

---

## Troubleshooting

**Bot not responding?**
```bash
./scripts/healthcheck.sh
```

**Need help?**
1. Check `DEPLOYMENT.md` Troubleshooting section
2. Check n8n Executions for errors
3. Check Slack alerts

---

## Estimated Time

- **Steps 1-4:** ~45 minutes (credential setup + deployment)
- **Step 5:** ~30 minutes (testing)
- **Total:** ~1.5 hours to fully deployed and tested bot

**You can skip Stripe setup initially and test just photo analysis (Steps 1a-1e, 2, 3, 4a, 5)**

---

🚀 **Ready? Start with Step 1a - Create your Telegram bot now!**
