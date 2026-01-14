# RIVET Pro MVP - Quick Setup Guide

**Get from zero to production in 30 minutes.**

---

## ✅ What You Have Now

All the files needed for a production-ready Telegram bot MVP:

```
rivet-pro/
├── n8n-workflows/               ← Import these to n8n
│   ├── workflow_production_complete.json
│   ├── workflow_stripe_checkout.json
│   ├── workflow_stripe_webhook.json
│   └── workflow_daily_summary.json
├── database/
│   └── schema.sql               ← Run this on Neon
├── landing-page/
│   └── index.html               ← Deploy this to VPS/Vercel
├── scripts/
│   ├── deploy.sh                ← Automated deployment helper
│   └── backup.sh                ← Database backup script
├── .env.example                 ← Copy to .env and fill in
├── README_MVP.md                ← Full documentation
└── SETUP_GUIDE.md               ← You are here
```

---

## 🚀 30-Minute Setup

### Step 1: Environment Setup (5 min)

```bash
# 1. Copy environment file
cd rivet-pro
cp .env.example .env

# 2. Edit with your values
nano .env

# Required values:
# - TELEGRAM_BOT_TOKEN (from @BotFather)
# - ANTHROPIC_API_KEY (from console.anthropic.com)
# - DATABASE_URL (your Neon connection string)
# - STRIPE_SECRET_KEY (from dashboard.stripe.com)
# - STRIPE_PRICE_ID (create $29/month product first)
# - STRIPE_WEBHOOK_SECRET (from webhook setup)
# - SLACK_WEBHOOK_URL (optional but recommended)
```

### Step 2: Database Setup (5 min)

```bash
# Connect to your Neon database
psql "YOUR_NEON_CONNECTION_STRING"

# Run schema
\i database/schema.sql

# Verify tables created
\dt
# Should show: users, lookups, subscriptions, command_logs

# Exit
\q
```

### Step 3: Telegram Bot Setup (3 min)

```bash
# 1. Create bot with @BotFather
# Open Telegram → search @BotFather → send /newbot → follow prompts

# 2. Set webhook (replace <TOKEN> with your bot token)
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "http://72.60.175.144:5678/webhook/telegram-webhook"}'

# 3. Verify
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

### Step 4: Stripe Setup (5 min)

```bash
# Go to: https://dashboard.stripe.com/products

# 1. Click "+ Add product"
# 2. Name: "RIVET Pro"
# 3. Price: $29
# 4. Billing period: Monthly
# 5. Click "Save product"
# 6. Copy the Price ID (starts with price_xxx) to .env

# Set up webhook:
# Go to: https://dashboard.stripe.com/webhooks
# 1. Click "+ Add endpoint"
# 2. Endpoint URL: http://72.60.175.144:5678/webhook/stripe/webhook
# 3. Select events:
#    - checkout.session.completed
#    - customer.subscription.deleted
#    - invoice.payment_failed
# 4. Click "Add endpoint"
# 5. Copy Signing secret (whsec_xxx) to .env
```

### Step 5: Import n8n Workflows (10 min)

```bash
# Go to: http://72.60.175.144:5678

# For each workflow JSON file in n8n-workflows/:

# 1. Click "Workflows" in left sidebar
# 2. Click "+ Add workflow" dropdown → "Import from file"
# 3. Select the JSON file
# 4. Configure credentials (one-time setup per credential type):

#    PostgreSQL Credential:
#    - Name: "Neon PostgreSQL"
#    - Host: Extract from DATABASE_URL
#    - Database: rivetpro (or your DB name)
#    - User: Extract from DATABASE_URL
#    - Password: Extract from DATABASE_URL
#    - SSL: true

#    HTTP Header Auth (Telegram):
#    - Name: "Telegram Bot Auth"
#    - Header Name: Authorization
#    - Header Value: Bearer <YOUR_TELEGRAM_BOT_TOKEN>

#    HTTP Header Auth (Anthropic):
#    - Name: "Anthropic API Auth"
#    - Header Name: x-api-key
#    - Header Value: <YOUR_ANTHROPIC_API_KEY>

#    HTTP Header Auth (Stripe):
#    - Name: "Stripe API Auth"
#    - Header Name: Authorization
#    - Header Value: Bearer <YOUR_STRIPE_SECRET_KEY>

# 5. Click "Activate" toggle (top right) for each workflow
```

### Step 6: Test It! (2 min)

```bash
# 1. Open Telegram
# 2. Find your bot (@your_bot_username)
# 3. Send: /start
#    Expected: Welcome message

# 4. Send a photo of any electrical panel
#    Expected: "⚡ Analyzing..." then full analysis

# 5. Send: /status
#    Expected: "9 of 10 free lookups remaining"

# 6. Send 10 more photos to test limit
#    Expected: After 10th, "Limit reached. /upgrade"
```

---

## 🌐 Deploy Landing Page (Optional)

### Option A: Deploy to VPS

```bash
# 1. Update bot username in HTML
sed -i 's/YOUR_BOT_USERNAME/your_actual_bot_username/g' landing-page/index.html

# 2. Copy to VPS
scp landing-page/index.html root@72.60.175.144:/var/www/rivetpro.com/index.html

# 3. Configure nginx (create /etc/nginx/sites-available/rivetpro.com):
server {
    listen 80;
    server_name rivetpro.com www.rivetpro.com;
    root /var/www/rivetpro.com;
    index index.html;
}

# 4. Enable site
ln -s /etc/nginx/sites-available/rivetpro.com /etc/nginx/sites-enabled/
systemctl reload nginx
```

### Option B: Deploy to Vercel (Faster)

```bash
# 1. Install Vercel CLI
npm i -g vercel

# 2. Update bot username
sed -i 's/YOUR_BOT_USERNAME/your_actual_bot_username/g' landing-page/index.html

# 3. Deploy
cd landing-page
vercel --prod

# Done! Your landing page is live in seconds
```

---

## 📊 Verify Everything Works

### Database Check

```sql
-- Connect to database
psql "YOUR_NEON_CONNECTION_STRING"

-- Check users table
SELECT * FROM users;

-- Check lookups table
SELECT * FROM lookups ORDER BY created_at DESC LIMIT 5;

-- Check helper functions
SELECT * FROM can_user_lookup(YOUR_TELEGRAM_ID);
```

### n8n Workflow Check

```bash
# Go to: http://72.60.175.144:5678/workflows

# Verify all 4 workflows are:
# ✅ Imported
# ✅ Active (green toggle)
# ✅ No errors (check execution logs)
```

### Stripe Check

```bash
# Test Stripe API
curl https://api.stripe.com/v1/products \
  -u "$STRIPE_SECRET_KEY:" | jq .

# Go to: https://dashboard.stripe.com/webhooks
# Verify webhook is active and receiving events
```

---

## 🔧 Common Issues

**"Bot doesn't respond"**
- Check webhook: `curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"`
- Verify n8n workflow is active
- Check n8n execution logs for errors

**"Claude API error 401"**
- Verify ANTHROPIC_API_KEY in .env
- Test: `curl https://api.anthropic.com/v1/messages -H "x-api-key: $ANTHROPIC_API_KEY" ...`

**"Database connection failed"**
- Check Neon project is not paused
- Verify DATABASE_URL includes `?sslmode=require`
- Test: `psql "$DATABASE_URL" -c "SELECT 1;"`

**"Stripe webhook not working"**
- Go to Stripe dashboard → Webhooks
- Click your webhook → "Send test webhook"
- Check n8n execution logs

---

## 📈 Next Steps

### Week 1: Launch
- [ ] Get first 10 users
- [ ] Monitor for errors
- [ ] Collect feedback
- [ ] Iterate on prompt quality

### Week 2: Improve
- [ ] Set up automated backups (`scripts/backup.sh`)
- [ ] Add error monitoring (Sentry)
- [ ] Write privacy policy & terms
- [ ] Optimize response time

### Week 3+: Grow
- [ ] SEO for landing page
- [ ] Content marketing (Reddit, LinkedIn)
- [ ] Add referral program
- [ ] Pro user case studies

---

## 💰 Pricing Reminder

- **Free:** 10 analyses
- **Pro:** $29/month unlimited

**Economics:**
- Cost per analysis: ~$0.005 (Claude API)
- Pro user profit: ~$28.75/month
- Break-even: 1 Pro subscriber

---

## 📞 Need Help?

**Documentation:**
- Full docs: `README_MVP.md`
- n8n community: https://community.n8n.io
- Stripe docs: https://docs.stripe.com
- Claude API: https://docs.anthropic.com

**Quick references:**
- Database schema: `database/schema.sql`
- Environment vars: `.env.example`
- Workflows: `n8n-workflows/`

---

**You're ready to ship! 🚀**

Test everything, fix any issues, then launch.

Remember: Perfect is the enemy of shipped. Get it working, get users, iterate based on real feedback.

Good luck!
