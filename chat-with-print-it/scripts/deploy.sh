#!/bin/bash

# Chat with Print - Complete Deployment Script
# Automates database setup and verification

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}  Chat with Print - Deployment${NC}"
echo -e "${BLUE}=======================================${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}=== Checking Prerequisites ===${NC}"

if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}ERROR: DATABASE_URL not set${NC}"
    echo "Set it with: export DATABASE_URL=postgresql://..."
    exit 1
fi

if ! command -v psql &> /dev/null; then
    echo -e "${RED}ERROR: psql not found${NC}"
    echo "Install PostgreSQL client"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites OK${NC}"
echo ""

# Deploy database schema
echo -e "${YELLOW}=== Deploying Database Schema ===${NC}"
SCHEMA_FILE="${PROJECT_ROOT}/database/schema.sql"

if [ ! -f "$SCHEMA_FILE" ]; then
    echo -e "${RED}ERROR: Schema file not found at $SCHEMA_FILE${NC}"
    exit 1
fi

echo "Running schema.sql..."
if psql "$DATABASE_URL" -f "$SCHEMA_FILE"; then
    echo -e "${GREEN}✅ Database schema deployed${NC}"
else
    echo -e "${RED}❌ Database deployment failed${NC}"
    exit 1
fi

# Verify tables
echo ""
echo -e "${YELLOW}=== Verifying Tables ===${NC}"
TABLES=$(psql "$DATABASE_URL" -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public';" | tr -d ' ')
EXPECTED_TABLES=("users" "lookups" "payments" "daily_stats")

for table in "${EXPECTED_TABLES[@]}"; do
    if echo "$TABLES" | grep -q "^$table$"; then
        echo -e "${GREEN}✅ Table '$table' exists${NC}"
    else
        echo -e "${RED}❌ Table '$table' missing${NC}"
        exit 1
    fi
done

# Verify indexes
echo ""
echo -e "${YELLOW}=== Verifying Indexes ===${NC}"
INDEX_COUNT=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM pg_indexes WHERE schemaname='public';" | tr -d ' ')
if [ "$INDEX_COUNT" -ge 6 ]; then
    echo -e "${GREEN}✅ $INDEX_COUNT indexes created${NC}"
else
    echo -e "${YELLOW}⚠️  Only $INDEX_COUNT indexes found (expected 6+)${NC}"
fi

# Verify function
echo ""
echo -e "${YELLOW}=== Verifying Database Functions ===${NC}"
FUNCTION_EXISTS=$(psql "$DATABASE_URL" -t -c "SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname='update_daily_stats');" | tr -d ' ')
if [ "$FUNCTION_EXISTS" = "t" ]; then
    echo -e "${GREEN}✅ Function 'update_daily_stats' exists${NC}"
else
    echo -e "${RED}❌ Function 'update_daily_stats' missing${NC}"
    exit 1
fi

# Summary
echo ""
echo -e "${BLUE}=======================================${NC}"
echo -e "${GREEN}✅ Database deployment complete!${NC}"
echo -e "${BLUE}=======================================${NC}"
echo ""
echo "Next steps:"
echo "1. Configure n8n environment variables (Settings > Variables)"
echo "2. Import workflows from n8n-workflows/ directory"
echo "3. Configure workflow credentials (Telegram, PostgreSQL)"
echo "4. Run: ./scripts/set_telegram_webhook.sh"
echo "5. Activate workflows in n8n UI"
echo "6. Test with: ./scripts/test_checklist.md"
echo ""
echo "For full instructions, see: DEPLOYMENT.md"
