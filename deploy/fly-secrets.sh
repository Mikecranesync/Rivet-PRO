#!/bin/bash
# Fly.io Secrets Setup for RIVET Pro Telegram Bot
# Run this ONCE before first deployment
#
# Usage:
#   1. Install Fly CLI: curl -L https://fly.io/install.sh | sh
#   2. Login: fly auth login
#   3. Copy your secrets from .env file
#   4. Run this script: bash deploy/fly-secrets.sh

echo "Setting Fly.io secrets for rivet-cmms-bot..."
echo ""
echo "IMPORTANT: Replace <YOUR_*> placeholders with actual values from your .env file"
echo ""

# ===== REQUIRED SECRETS =====
# Copy these values from your .env file

# Telegram Bot
fly secrets set TELEGRAM_BOT_TOKEN="<YOUR_TELEGRAM_BOT_TOKEN>"
fly secrets set TELEGRAM_ADMIN_CHAT_ID="<YOUR_ADMIN_CHAT_ID>"

# Primary Database (Neon)
fly secrets set DATABASE_URL="<YOUR_NEON_DATABASE_URL>"

# Atlas CMMS Database (for dual-write sync)
fly secrets set ATLAS_DATABASE_URL="<YOUR_ATLAS_DATABASE_URL>"

# LLM APIs (Photo Pipeline)
fly secrets set GROQ_API_KEY="<YOUR_GROQ_API_KEY>"
fly secrets set DEEPSEEK_API_KEY="<YOUR_DEEPSEEK_API_KEY>"
fly secrets set ANTHROPIC_API_KEY="<YOUR_ANTHROPIC_API_KEY>"
fly secrets set GOOGLE_API_KEY="<YOUR_GOOGLE_API_KEY>"
fly secrets set OPENAI_API_KEY="<YOUR_OPENAI_API_KEY>"

# n8n Webhooks
fly secrets set N8N_WEBHOOK_BASE_URL="<YOUR_N8N_WEBHOOK_BASE_URL>"

# ===== OPTIONAL SECRETS (uncomment if needed) =====

# Supabase Failover
# fly secrets set SUPABASE_DB_URL="<YOUR_SUPABASE_DB_URL>"

# Observability
# fly secrets set LANGFUSE_PUBLIC_KEY="<YOUR_LANGFUSE_PUBLIC_KEY>"
# fly secrets set LANGFUSE_SECRET_KEY="<YOUR_LANGFUSE_SECRET_KEY>"
# fly secrets set LANGFUSE_BASE_URL="https://us.cloud.langfuse.com"

# Search APIs
# fly secrets set TAVILY_API_KEY="<YOUR_TAVILY_API_KEY>"
# fly secrets set BRAVE_SEARCH_API_KEY="<YOUR_BRAVE_SEARCH_API_KEY>"

# Slack Alerts
# fly secrets set SLACK_WEBHOOK_URL="<YOUR_SLACK_WEBHOOK_URL>"

echo ""
echo "Done! Verify secrets with: fly secrets list"
echo ""
echo "Next steps:"
echo "  1. Deploy: fly deploy"
echo "  2. Check status: fly status"
echo "  3. View logs: fly logs"
