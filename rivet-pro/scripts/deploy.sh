#!/bin/bash
#############################################################
# RIVET Pro MVP - Deployment Script
#
# This script helps deploy the n8n workflows and landing
# page to your production environment.
#
# Usage: ./deploy.sh [options]
# Options:
#   --db-only      Only set up database
#   --workflows    Only import workflows
#   --landing      Only deploy landing page
#############################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration (update these)
VPS_HOST="${VPS_HOST:-72.60.175.144}"
VPS_USER="${VPS_USER:-root}"
N8N_URL="${N8N_URL:-http://72.60.175.144:5678}"

echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   RIVET Pro MVP - Deployment        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""

# Check if .env exists
if [ ! -f "../.env" ]; then
    echo -e "${RED}✗ .env file not found${NC}"
    echo "  Please copy .env.example to .env and fill in values"
    exit 1
fi

# Load environment variables
source ../.env

#############################################################
# Database Setup
#############################################################
setup_database() {
    echo -e "${YELLOW}📊 Setting up database...${NC}"

    if [ -z "$DATABASE_URL" ]; then
        echo -e "${RED}✗ DATABASE_URL not set in .env${NC}"
        exit 1
    fi

    echo "  → Running schema.sql..."
    psql "$DATABASE_URL" -f ../database/schema.sql

    echo "  → Verifying tables..."
    psql "$DATABASE_URL" -c "\dt" | grep -E "(users|lookups|subscriptions|command_logs)"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Database setup complete${NC}"
    else
        echo -e "${RED}✗ Database setup failed${NC}"
        exit 1
    fi
}

#############################################################
# Telegram Bot Configuration
#############################################################
setup_telegram() {
    echo -e "${YELLOW}🤖 Configuring Telegram bot...${NC}"

    if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
        echo -e "${RED}✗ TELEGRAM_BOT_TOKEN not set in .env${NC}"
        exit 1
    fi

    # Set webhook
    WEBHOOK_URL="$N8N_URL/webhook/telegram-webhook"
    echo "  → Setting webhook to: $WEBHOOK_URL"

    RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
        -H "Content-Type: application/json" \
        -d "{\"url\": \"$WEBHOOK_URL\"}")

    if echo "$RESPONSE" | grep -q '"ok":true'; then
        echo -e "${GREEN}✓ Telegram webhook configured${NC}"
    else
        echo -e "${RED}✗ Failed to set webhook${NC}"
        echo "$RESPONSE"
        exit 1
    fi

    # Verify webhook
    echo "  → Verifying webhook..."
    curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo" | jq '.'
}

#############################################################
# n8n Workflow Import
#############################################################
import_workflows() {
    echo -e "${YELLOW}⚙️  Importing n8n workflows...${NC}"

    # Note: This requires manual import via n8n UI or CLI
    echo "  → Workflow files are in: rivet-pro/n8n-workflows/"
    echo "  → Manual steps:"
    echo "    1. Go to $N8N_URL"
    echo "    2. Click Workflows → Import from File"
    echo "    3. Import each .json file"
    echo "    4. Configure credentials for each workflow"
    echo "    5. Activate workflows"
    echo ""
    echo -e "${YELLOW}  ⚠️  Workflows must be imported manually via n8n UI${NC}"
}

#############################################################
# Landing Page Deployment
#############################################################
deploy_landing_page() {
    echo -e "${YELLOW}🌐 Deploying landing page...${NC}"

    # Update bot username in HTML
    echo "  → Enter your Telegram bot username (without @):"
    read BOT_USERNAME

    if [ -z "$BOT_USERNAME" ]; then
        echo -e "${RED}✗ Bot username is required${NC}"
        exit 1
    fi

    # Create temp file with updated username
    TEMP_HTML=$(mktemp)
    sed "s/YOUR_BOT_USERNAME/$BOT_USERNAME/g" ../landing-page/index.html > "$TEMP_HTML"

    # Deploy to VPS
    echo "  → Deploying to VPS..."
    ssh "${VPS_USER}@${VPS_HOST}" "mkdir -p /var/www/rivetpro.com"
    scp "$TEMP_HTML" "${VPS_USER}@${VPS_HOST}:/var/www/rivetpro.com/index.html"

    # Clean up
    rm "$TEMP_HTML"

    echo -e "${GREEN}✓ Landing page deployed${NC}"
    echo "  → Configure nginx to serve /var/www/rivetpro.com"
}

#############################################################
# Stripe Setup Verification
#############################################################
verify_stripe() {
    echo -e "${YELLOW}💳 Verifying Stripe configuration...${NC}"

    if [ -z "$STRIPE_SECRET_KEY" ]; then
        echo -e "${RED}✗ STRIPE_SECRET_KEY not set${NC}"
        exit 1
    fi

    echo "  → Testing Stripe API..."
    RESPONSE=$(curl -s "https://api.stripe.com/v1/products?limit=1" \
        -u "$STRIPE_SECRET_KEY:")

    if echo "$RESPONSE" | grep -q '"object":"list"'; then
        echo -e "${GREEN}✓ Stripe API key valid${NC}"
    else
        echo -e "${RED}✗ Stripe API key invalid${NC}"
        echo "$RESPONSE"
        exit 1
    fi

    echo ""
    echo "  Manual steps required:"
    echo "  1. Create product 'RIVET Pro' at $29/month"
    echo "  2. Copy Price ID to .env (STRIPE_PRICE_ID)"
    echo "  3. Set up webhook endpoint:"
    echo "     URL: $N8N_URL/webhook/stripe/webhook"
    echo "     Events: checkout.session.completed, customer.subscription.deleted, invoice.payment_failed"
    echo "  4. Copy Webhook Signing Secret to .env (STRIPE_WEBHOOK_SECRET)"
}

#############################################################
# Main Deployment Flow
#############################################################

# Parse arguments
DB_ONLY=false
WORKFLOWS_ONLY=false
LANDING_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --db-only)
            DB_ONLY=true
            shift
            ;;
        --workflows)
            WORKFLOWS_ONLY=true
            shift
            ;;
        --landing)
            LANDING_ONLY=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./deploy.sh [--db-only|--workflows|--landing]"
            exit 1
            ;;
    esac
done

# Run appropriate steps
if [ "$DB_ONLY" = true ]; then
    setup_database
elif [ "$WORKFLOWS_ONLY" = true ]; then
    import_workflows
elif [ "$LANDING_ONLY" = true ]; then
    deploy_landing_page
else
    # Full deployment
    echo "Starting full deployment..."
    echo ""

    setup_database
    echo ""

    setup_telegram
    echo ""

    verify_stripe
    echo ""

    import_workflows
    echo ""

    deploy_landing_page
    echo ""
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Deployment Complete! 🎉           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
echo "Next steps:"
echo "  1. Import workflows manually in n8n UI"
echo "  2. Configure Stripe product and webhook"
echo "  3. Set up nginx for landing page"
echo "  4. Test bot in Telegram"
echo ""
echo "Documentation: See README_MVP.md"
