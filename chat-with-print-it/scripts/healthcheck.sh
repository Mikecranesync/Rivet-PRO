#!/bin/bash

# Chat with Print - System Health Check
# Monitors all critical components

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
N8N_URL="${N8N_URL:-http://localhost:5678}"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
DATABASE_URL="${DATABASE_URL:-}"

# Track failures
FAILURES=0

echo "======================================="
echo "  Chat with Print - Health Check"
echo "======================================="
echo ""

# Check 1: n8n Service
echo -n "n8n Service: "
N8N_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "${N8N_URL}/healthz" 2>/dev/null)
if [ "$N8N_HEALTH" = "200" ]; then
    echo -e "${GREEN}✅ Running${NC}"
else
    echo -e "${RED}❌ Down (HTTP $N8N_HEALTH)${NC}"
    ((FAILURES++))
fi

# Check 2: Database Connection
echo -n "Database: "
if [ -n "$DATABASE_URL" ]; then
    DB_CHECK=$(psql "$DATABASE_URL" -c "SELECT 1;" 2>&1)
    if echo "$DB_CHECK" | grep -q "1 row"; then
        echo -e "${GREEN}✅ Connected${NC}"
    else
        echo -e "${RED}❌ Connection failed${NC}"
        ((FAILURES++))
    fi
else
    echo -e "${YELLOW}⚠️  DATABASE_URL not set${NC}"
fi

# Check 3: Telegram Webhook
echo -n "Telegram Webhook: "
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
    WEBHOOK_INFO=$(curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo")
    WEBHOOK_URL=$(echo "$WEBHOOK_INFO" | grep -o '"url":"[^"]*"' | cut -d'"' -f4)
    PENDING=$(echo "$WEBHOOK_INFO" | grep -o '"pending_update_count":[0-9]*' | grep -o '[0-9]*')

    if [ -n "$WEBHOOK_URL" ]; then
        echo -e "${GREEN}✅ Active${NC}"
        echo "   URL: $WEBHOOK_URL"
        if [ "$PENDING" != "0" ]; then
            echo -e "   ${YELLOW}⚠️  Pending updates: $PENDING${NC}"
        fi
    else
        echo -e "${RED}❌ Not configured${NC}"
        ((FAILURES++))
    fi
else
    echo -e "${YELLOW}⚠️  TELEGRAM_BOT_TOKEN not set${NC}"
fi

# Check 4: n8n Workflows
echo -n "n8n Workflows: "
# This requires n8n API credentials - skip if not configured
if [ -n "$N8N_API_KEY" ]; then
    WORKFLOWS=$(curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" "${N8N_URL}/api/v1/workflows" 2>/dev/null)
    ACTIVE_COUNT=$(echo "$WORKFLOWS" | grep -o '"active":true' | wc -l)
    TOTAL_COUNT=$(echo "$WORKFLOWS" | grep -o '"id":' | wc -l)

    if [ "$ACTIVE_COUNT" -ge 3 ]; then
        echo -e "${GREEN}✅ $ACTIVE_COUNT/$TOTAL_COUNT active${NC}"
    else
        echo -e "${YELLOW}⚠️  Only $ACTIVE_COUNT/$TOTAL_COUNT active (expected 3)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  N8N_API_KEY not set (skip check)${NC}"
fi

# Check 5: Disk Space
echo -n "Disk Space: "
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    echo -e "${GREEN}✅ ${DISK_USAGE}% used${NC}"
elif [ "$DISK_USAGE" -lt 90 ]; then
    echo -e "${YELLOW}⚠️  ${DISK_USAGE}% used${NC}"
else
    echo -e "${RED}❌ ${DISK_USAGE}% used (critical)${NC}"
    ((FAILURES++))
fi

# Check 6: Memory Usage
echo -n "Memory Usage: "
if command -v free >/dev/null 2>&1; then
    MEM_USAGE=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
    if [ "$MEM_USAGE" -lt 80 ]; then
        echo -e "${GREEN}✅ ${MEM_USAGE}% used${NC}"
    elif [ "$MEM_USAGE" -lt 90 ]; then
        echo -e "${YELLOW}⚠️  ${MEM_USAGE}% used${NC}"
    else
        echo -e "${RED}❌ ${MEM_USAGE}% used (critical)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  'free' command not available${NC}"
fi

# Summary
echo ""
echo "======================================="
if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}Overall Status: ✅ HEALTHY${NC}"
    exit 0
else
    echo -e "${RED}Overall Status: ❌ $FAILURES FAILURES${NC}"
    exit 1
fi
