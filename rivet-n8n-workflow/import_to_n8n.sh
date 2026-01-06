#!/bin/bash
# RIVET Pro - Quick n8n Workflow Import Script
# Usage: ./import_to_n8n.sh [n8n-url] [api-key]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
N8N_URL="${1:-${N8N_URL:-http://localhost:5678}}"
N8N_API_KEY="${2:-${N8N_API_KEY}}"
WORKFLOW_FILE="rivet_workflow.json"

# Banner
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}RIVET Pro - n8n Workflow Import${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check API key
if [ -z "$N8N_API_KEY" ]; then
    echo -e "${RED}❌ Error: N8N_API_KEY not set${NC}"
    echo ""
    echo "Options:"
    echo "  1. Set env var: export N8N_API_KEY=your-key"
    echo "  2. Pass as argument: ./import_to_n8n.sh http://localhost:5678 your-key"
    echo ""
    echo "To get your API key:"
    echo "  n8n → Settings → API → Generate API Key"
    exit 1
fi

# Check if workflow file exists
if [ ! -f "$WORKFLOW_FILE" ]; then
    echo -e "${RED}❌ Error: Workflow file not found: $WORKFLOW_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Found workflow file: $WORKFLOW_FILE${NC}"
echo -e "${BLUE}📡 n8n URL: $N8N_URL${NC}\n"

# Test connection
echo "Testing n8n connection..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "X-N8N-API-KEY: $N8N_API_KEY" \
    "$N8N_URL/api/v1/workflows")

if [ "$HTTP_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ Connected to n8n${NC}\n"
elif [ "$HTTP_STATUS" = "401" ]; then
    echo -e "${RED}❌ Authentication failed. Check your API key.${NC}"
    exit 1
else
    echo -e "${RED}❌ Connection failed (HTTP $HTTP_STATUS)${NC}"
    echo "Make sure n8n is running: n8n start"
    exit 1
fi

# Import workflow
echo "📤 Importing workflow..."
RESPONSE=$(curl -s -X POST \
    -H "X-N8N-API-KEY: $N8N_API_KEY" \
    -H "Content-Type: application/json" \
    -d @"$WORKFLOW_FILE" \
    "$N8N_URL/api/v1/workflows")

# Check if import was successful
if echo "$RESPONSE" | grep -q '"id"'; then
    WORKFLOW_ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
    WORKFLOW_NAME=$(echo "$RESPONSE" | grep -o '"name":"[^"]*' | head -1 | cut -d'"' -f4)

    echo -e "\n${GREEN}✅ Workflow imported successfully!${NC}"
    echo -e "${BLUE}   ID: $WORKFLOW_ID${NC}"
    echo -e "${BLUE}   Name: $WORKFLOW_NAME${NC}"
    echo -e "${BLUE}   URL: $N8N_URL/workflow/$WORKFLOW_ID${NC}\n"

    echo -e "${YELLOW}📋 Next Steps:${NC}"
    echo "   1. Open workflow: $N8N_URL/workflow/$WORKFLOW_ID"
    echo "   2. Configure credentials:"
    echo "      - Telegram Bot (token from .env)"
    echo "      - Tavily API (get from tavily.com)"
    echo "      - Atlas CMMS API (from admin panel)"
    echo "   3. Set variables in n8n:"
    echo "      - GOOGLE_API_KEY (from .env)"
    echo "      - ATLAS_CMMS_URL (your CMMS instance)"
    echo "   4. Activate workflow"
    echo "   5. Test with Telegram bot"
else
    echo -e "\n${RED}❌ Import failed${NC}"
    echo "Response: $RESPONSE"
    exit 1
fi
