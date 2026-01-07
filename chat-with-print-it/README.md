# Chat with Print-it 📸⚡

AI-powered electrical panel analysis via Telegram. Send a photo, get expert troubleshooting guidance in seconds.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Telegram   │────▶│    n8n      │────▶│   Claude    │
│    Bot      │◀────│  Workflows  │◀────│   Vision    │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              ┌──────────┐  ┌──────────┐
              │ Neon DB  │  │  Stripe  │
              │PostgreSQL│  │ Payments │
              └──────────┘  └──────────┘
```

## Features

- 📸 **Photo Analysis**: Send any electrical panel photo for instant AI analysis
- 🔍 **Component ID**: Identifies system type, components, and designations  
- ⚠️ **Issue Detection**: Spots visible problems and wear
- 📋 **Troubleshooting**: Top 3 things to check first
- 💳 **Freemium Model**: 10 free lookups, then $29/month Pro
- 📊 **Usage Tracking**: Full audit trail of all lookups
- 🔔 **Monitoring**: Slack notifications for users, payments, errors

## Quick Start

### 1. Setup Database

```bash
psql $DATABASE_URL -f database/schema.sql
```

### 2. Configure n8n Variables

In n8n Settings > Variables, add:
- `ANTHROPIC_API_KEY`
- `SLACK_WEBHOOK_URL`
- `STRIPE_CHECKOUT_URL`

### 3. Import Workflows

Import these JSON files via n8n UI:
- `n8n-workflows/workflow_core_bot.json`
- `n8n-workflows/workflow_stripe_webhook.json`
- `n8n-workflows/workflow_daily_summary.json`

### 4. Configure Credentials

After import, configure:
- Telegram Bot API credentials
- PostgreSQL (Neon) connection

### 5. Setup Webhooks

**Telegram:**
```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook?url=$N8N_URL/webhook/telegram-trigger"
```

**Stripe:**
Add webhook endpoint in Stripe Dashboard pointing to:
`$N8N_URL/webhook/stripe-webhook`

## File Structure

```
chat-with-print-it/
├── n8n-workflows/
│   ├── workflow_core_bot.json      # Main Telegram bot
│   ├── workflow_stripe_webhook.json # Payment handling
│   └── workflow_daily_summary.json  # Daily stats
├── database/
│   └── schema.sql                   # PostgreSQL schema
├── landing-page/
│   └── index.html                   # Marketing page
├── scripts/
│   └── deploy.sh                    # Deployment script
├── .env.example                     # Environment template
├── CLAUDE_CODE_PROMPT.md           # CLI prompt for Claude Code
└── README.md                        # This file
```

## Workflows Overview

### Core Bot (`workflow_core_bot.json`)
- Telegram webhook trigger
- Message routing (photo/command/text)
- User upsert and limit checking
- Claude Vision API for analysis
- Response formatting
- Usage logging

### Stripe Webhook (`workflow_stripe_webhook.json`)
- Signature verification
- Checkout completion → Pro activation
- Subscription cancellation handling
- Payment failure notifications

### Daily Summary (`workflow_daily_summary.json`)
- Scheduled midnight execution
- Aggregates daily metrics
- Slack reporting
- Stats persistence

## Environment Variables

See `.env.example` for all required variables.

## Support

Built by Mike for field technicians. Questions? Open an issue or reach out on Telegram.
