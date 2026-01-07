#!/bin/bash

# Telegram Webhook Configuration Script
# Sets the webhook URL for Chat with Print bot

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if environment variables are set
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo -e "${RED}ERROR: TELEGRAM_BOT_TOKEN not set${NC}"
    echo "Set it with: export TELEGRAM_BOT_TOKEN=your_token_here"
    exit 1
fi

if [ -z "$TELEGRAM_WEBHOOK_SECRET" ]; then
    echo -e "${RED}ERROR: TELEGRAM_WEBHOOK_SECRET not set${NC}"
    echo "Generate one with: openssl rand -hex 32"
    echo "Then set it with: export TELEGRAM_WEBHOOK_SECRET=your_secret_here"
    exit 1
fi

# Default n8n URL (can be overridden)
N8N_URL="${N8N_URL:-http://72.60.175.144:5678}"
WEBHOOK_PATH="/webhook/telegram-trigger"
FULL_WEBHOOK_URL="${N8N_URL}${WEBHOOK_PATH}"

echo -e "${YELLOW}=== Setting Telegram Webhook ===${NC}"
echo "Bot Token: ${TELEGRAM_BOT_TOKEN:0:10}..."
echo "Webhook URL: $FULL_WEBHOOK_URL"
echo "Secret: ${TELEGRAM_WEBHOOK_SECRET:0:10}..."
echo ""

# Set the webhook
RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"${FULL_WEBHOOK_URL}\",
    \"secret_token\": \"${TELEGRAM_WEBHOOK_SECRET}\",
    \"allowed_updates\": [\"message\"],
    \"drop_pending_updates\": true
  }")

# Parse response
SUCCESS=$(echo "$RESPONSE" | grep -o '"ok":true' || echo "")

if [ -n "$SUCCESS" ]; then
    echo -e "${GREEN}✅ Webhook set successfully!${NC}"
    echo ""
else
    echo -e "${RED}❌ Failed to set webhook${NC}"
    echo "Response: $RESPONSE"
    exit 1
fi

# Verify webhook info
echo -e "${YELLOW}=== Verifying Webhook ===${NC}"
INFO=$(curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo")
echo "$INFO" | jq '.' 2>/dev/null || echo "$INFO"

# Check for pending updates
PENDING=$(echo "$INFO" | grep -o '"pending_update_count":[0-9]*' | grep -o '[0-9]*')

if [ "$PENDING" = "0" ]; then
    echo -e "${GREEN}✅ No pending updates${NC}"
else
    echo -e "${YELLOW}⚠️  Pending updates: $PENDING (will be processed)${NC}"
fi

echo ""
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo "Your bot is now listening at: $FULL_WEBHOOK_URL"
echo ""
echo "Next steps:"
echo "1. Open Telegram and search for your bot"
echo "2. Send /start to test"
echo "3. Check n8n executions at ${N8N_URL}"
