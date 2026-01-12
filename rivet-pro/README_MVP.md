# RIVET Pro MVP - n8n Implementation

**Production-ready Telegram bot for instant AI-powered electrical panel analysis.**

Ship in hours using n8n workflows, Neon PostgreSQL, Claude Vision API, and Stripe.

---

## 🎯 What You're Building

A Telegram bot that:
1. **Receives photos** of electrical panels from technicians
2. **Analyzes them instantly** using Claude Vision AI
3. **Returns expert guidance** in 15-20 seconds
4. **Monetizes with subscriptions** ($29/month for unlimited)

**Business Model:**
- Free: 10 analyses
- Pro: Unlimited analyses for $29/month

---

## 📦 What's In This Directory

```
rivet-pro/
├── n8n-workflows/
│   ├── workflow_production_complete.json       # Main bot (photo analysis + commands)
│   ├── workflow_stripe_checkout.json           # Generate Stripe checkout links
│   ├── workflow_stripe_webhook.json            # Handle subscription events
│   └── workflow_daily_summary.json             # Daily metrics to Slack
├── database/
│   └── schema.sql                               # PostgreSQL schema with all tables
├── landing-page/
│   └── index.html                               # Marketing site (Tailwind CSS)
├── scripts/
│   └── (deployment scripts)
├── .env.example                                 # All environment variables needed
└── README_MVP.md                                # This file
```

---

## 🚀 Quick Start (30 Minutes)

### Prerequisites

You need:
- ✅ VPS with n8n running (you have: 72.60.175.144:5678)
- ✅ Neon PostgreSQL database
- ✅ Telegram bot token (from @BotFather)
- ✅ Claude API key (console.anthropic.com)
- ✅ Stripe account (for payments)
- ⚠️ Slack webhook (optional, for monitoring)

### Step 1: Database Setup

```bash
# 1. Get your Neon connection string
# Example: postgresql://user:pass@ep-xyz.aws.neon.tech/rivetpro

# 2. Run schema
psql "YOUR_NEON_CONNECTION_STRING" -f rivet-pro/database/schema.sql

# 3. Verify tables created
psql "YOUR_NEON_CONNECTION_STRING" -c "\dt"
# Should show: users, lookups, subscriptions, command_logs
```

### Step 2: Environment Variables

```bash
# Copy example
cp rivet-pro/.env.example rivet-pro/.env

# Edit with real values
nano rivet-pro/.env
```

**Required values:**
```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxx
DATABASE_URL=postgresql://user:password@ep-xyz.aws.neon.tech/rivetpro
STRIPE_SECRET_KEY=sk_test_51xxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxx
STRIPE_PRICE_ID=price_xxxxxxxxxx
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx
APP_URL=https://rivetpro.com
N8N_URL=http://72.60.175.144:5678
```

### Step 3: Telegram Bot Configuration

```bash
# 1. Create bot with @BotFather
# Send to @BotFather: /newbot
# Follow prompts, save your token

# 2. Set webhook
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "http://72.60.175.144:5678/webhook/telegram-webhook"}'

# 3. Verify
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

### Step 4: Stripe Setup

```bash
# 1. Go to https://dashboard.stripe.com/products
# 2. Create product: "RIVET Pro" at $29/month recurring
# 3. Copy the Price ID (price_xxxxx)
# 4. Go to https://dashboard.stripe.com/webhooks
# 5. Add endpoint: http://72.60.175.144:5678/webhook/stripe/webhook
# 6. Select events:
#    - checkout.session.completed
#    - customer.subscription.deleted
#    - invoice.payment_failed
# 7. Copy Webhook Signing Secret (whsec_xxxxx)
```

### Step 5: Import Workflows to n8n

**Option A: Via UI (recommended)**
1. Go to http://72.60.175.144:5678
2. Click **Workflows** → **Import from File**
3. Import all 4 JSON files from `rivet-pro/n8n-workflows/`
4. For each workflow, configure credentials:
   - **PostgreSQL**: Your Neon connection
   - **Telegram Bot Auth** (HTTP Header): `Authorization: Bearer <BOT_TOKEN>`
   - **Anthropic API** (HTTP Header): `x-api-key: <ANTHROPIC_KEY>`
   - **Stripe** (HTTP Header): `Authorization: Bearer <STRIPE_KEY>`

**Option B: Via CLI**
```bash
n8n import:workflow --input=rivet-pro/n8n-workflows/workflow_production_complete.json
# Repeat for all 4 workflows
```

### Step 6: Activate Workflows

In n8n:
1. Open each workflow
2. Click **Activate** toggle (top right)
3. Workflows should turn green

### Step 7: Test

```bash
# 1. Open Telegram, find your bot
# 2. Send: /start
# Expected: Welcome message with instructions

# 3. Send a photo of any electrical panel
# Expected: "⚡ Analyzing..." then full analysis

# 4. Send: /status
# Expected: "9 of 10 free lookups remaining"

# 5. Test limit: Send 10 more photos
# Expected: "🚫 Free limit reached. Upgrade..."
```

### Step 8: Deploy Landing Page

```bash
# Update bot username
sed -i 's/YOUR_BOT_USERNAME/your_actual_bot_username/g' \
  rivet-pro/landing-page/index.html

# Deploy to VPS
scp rivet-pro/landing-page/index.html \
  root@72.60.175.144:/var/www/rivetpro.com/index.html

# Or use Vercel, Netlify, Cloudflare Pages
```

---

## 📊 How It Works

### Main Workflow Flow

```
User sends photo to Telegram bot
  ↓
Telegram Webhook → n8n
  ↓
Extract message data (chat_id, user_id, photo_file_id)
  ↓
Upsert user in PostgreSQL (create if new, update if exists)
  ↓
Route by message type (Switch node):
  ├─ Photo detected
  │   ↓
  │   Check user limits (can_user_lookup function)
  │   ↓
  │   If allowed:
  │     → Send "Analyzing..." message
  │     → Download photo from Telegram
  │     → Send to Claude Vision API with expert prompt
  │     → Format response with lookup count
  │     → Send analysis to user
  │     → Increment lookup counter
  │     → Log to lookups table
  │   If limit reached:
  │     → Send "Upgrade to Pro" message
  │
  ├─ /start command → Send welcome message
  ├─ /help command → Send help text
  ├─ /status command → Query user data, show stats
  ├─ /upgrade command → Send upgrade info
  └─ Other text → Send "Please send a photo"
```

### Stripe Flow

**Checkout creation:**
```
User sends /upgrade
  ↓
(Future: Call webhook to create checkout link)
  ↓
Check if user has Stripe customer_id
  ↓
If no: Create Stripe customer → Save to DB
  ↓
Create Stripe Checkout Session (mode=subscription)
  ↓
Return checkout URL to user
```

**Webhook handling:**
```
Stripe sends event to webhook
  ↓
Verify signature (prevents spoofing)
  ↓
Route by event type:
  ├─ checkout.session.completed
  │   → Set user is_pro=true
  │   → Create subscription record
  │   → Send "Welcome to Pro!" via Telegram
  │
  ├─ customer.subscription.deleted
  │   → Set user is_pro=false
  │   → Update subscription status
  │   → Send cancellation notice
  │
  └─ invoice.payment_failed
      → Send payment failure notice via Telegram
```

---

## 🧪 Testing Checklist

**Bot functionality:**
- [ ] /start shows welcome message
- [ ] Photo triggers analysis in <30s
- [ ] Analysis is relevant and accurate
- [ ] /status shows correct count
- [ ] /help shows all commands
- [ ] Random text prompts for photo
- [ ] 11th photo (free user) hits limit

**Database:**
- [ ] New users created on first message
- [ ] Lookup count increments correctly
- [ ] All analyses logged to `lookups` table
- [ ] Commands logged to `command_logs` table

**Stripe:**
- [ ] Checkout link generated
- [ ] Successful payment activates Pro
- [ ] User receives Telegram confirmation
- [ ] Cancellation deactivates Pro
- [ ] Failed payment sends notification

**Monitoring:**
- [ ] Daily summary arrives in Slack at 9 AM
- [ ] Metrics are accurate
- [ ] Error notifications work

---

## 💰 Economics

**Costs per month:**
- VPS (n8n): $5-10
- Neon PostgreSQL: Free (up to 0.5GB)
- Claude API (per analysis): ~$0.005
- Stripe fees: 2.9% + $0.30 per transaction

**Revenue per Pro user:**
- Subscription: $29/month
- Estimated usage: 50 analyses/month
- Claude cost: $0.25/month
- **Net profit: ~$28 per Pro user**

**Break-even: 1 Pro subscriber**

**Scale:**
- 10 Pro users = $280/month profit
- 100 Pro users = $2,800/month profit
- 1,000 Pro users = $28,000/month profit

---

## 🛠️ Troubleshooting

**Bot doesn't respond:**
```bash
# Check webhook
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# Reset webhook
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=http://72.60.175.144:5678/webhook/telegram-webhook"
```

**Claude API errors:**
```bash
# Test API key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-20250514","max_tokens":100,"messages":[{"role":"user","content":"test"}]}'
```

**Database connection fails:**
```bash
# Test connection
psql "$DATABASE_URL" -c "SELECT 1;"

# Check Neon project is not paused
# Verify connection string includes ?sslmode=require
```

**n8n workflow errors:**
1. Check execution logs in n8n UI
2. Verify all credentials are configured
3. Test nodes individually using "Test step"
4. Check environment variables are loaded

---

## 📈 Analytics & Monitoring

**Key metrics (tracked automatically):**
- New users (daily/total)
- Analyses performed (volume, success rate)
- Average processing time
- Free → Pro conversion rate
- MRR (Monthly Recurring Revenue)
- Churn rate

**Useful database queries:**

```sql
-- Top users by activity
SELECT telegram_username, lookup_count, is_pro, created_at
FROM users
ORDER BY lookup_count DESC
LIMIT 10;

-- Daily analysis volume
SELECT DATE(created_at) as date, COUNT(*) as analyses
FROM lookups
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Conversion rate
SELECT
  COUNT(*) FILTER (WHERE is_pro = false) as free_users,
  COUNT(*) FILTER (WHERE is_pro = true) as pro_users,
  ROUND(100.0 * COUNT(*) FILTER (WHERE is_pro = true) / COUNT(*), 2) as conversion_pct
FROM users;

-- Average processing time
SELECT AVG(processing_time_ms) / 1000 as avg_seconds
FROM lookups
WHERE success = true AND created_at >= NOW() - INTERVAL '7 days';
```

---

## 🚢 Pre-Launch Checklist

- [ ] Switch `STRIPE_SECRET_KEY` to live key (sk_live_xxx)
- [ ] Update `APP_URL` to actual domain
- [ ] Replace `YOUR_BOT_USERNAME` in landing page
- [ ] Set up SSL certificate for domain
- [ ] Configure DNS (A record → VPS IP)
- [ ] Test full user journey (free → 10 analyses → upgrade → pro)
- [ ] Write privacy policy & terms of service
- [ ] Set up database backups (Neon auto-backups)
- [ ] Configure error monitoring (optional: Sentry)
- [ ] Test on mobile devices (Telegram is primarily mobile)

---

## 🎨 Customization

**Change analysis prompt:**

In workflow `workflow_production_complete.json`, find the **Claude Vision Analysis** node and update the prompt text:

```javascript
"You are an expert [YOUR SPECIALTY]. Analyze this [YOUR SUBJECT]..."
```

**Add new commands:**

1. In **Route Message Type** (Switch node), add new case
2. Create new "Build Message" node with your response
3. Wire to **Merge Command Responses**
4. Activate workflow

**Multi-language support:**

In message building Code nodes:
```javascript
const lang = $runData.nodes['Upsert User'][0].data.main[0][0].json.language_code || 'en';
const messages = {
  en: "Welcome!",
  es: "¡Bienvenido!",
  fr: "Bienvenue!"
};
return { text: messages[lang] };
```

---

## 📞 Support

**Setup issues:**
- Check n8n execution logs
- Verify all environment variables
- Test workflows individually
- Join n8n community forum

**Business questions:**
- Review Stripe dashboard
- Check Slack daily summaries
- Query PostgreSQL directly

---

## 🚀 Roadmap

**Week 1-2 (MVP Launch):**
- ✅ Core bot with photo analysis
- ✅ User tracking and limits
- ✅ Stripe subscriptions
- ✅ Landing page
- ⬜ First 10 users

**Week 3-4 (Iterate):**
- ⬜ Improve prompt based on user feedback
- ⬜ Add /stats command for admin
- ⬜ Set up error monitoring
- ⬜ Optimize processing speed

**Month 2 (Features):**
- ⬜ IEC→ANSI conversion
- ⬜ PDF manual OCR
- ⬜ Equipment database
- ⬜ Documentation generation

**Month 3+ (Scale):**
- ⬜ Referral program
- ⬜ Team accounts
- ⬜ API for integrations
- ⬜ White-label offering

---

**Built with:**
- n8n (workflow automation)
- Claude Sonnet 4 (AI vision)
- Neon PostgreSQL (database)
- Stripe (payments)
- Telegram Bot API (interface)

**Ship it. Learn. Iterate.**
