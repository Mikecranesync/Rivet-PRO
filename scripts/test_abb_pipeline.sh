#!/bin/bash
# =============================================================================
# RIVET Pro ABB Pipeline Test
# =============================================================================
# Tests the full pipeline with the ABB ACS580 equipment that started it all.
# This is the golden test case - if this fails, something is broken.
#
# Usage: ./scripts/test_abb_pipeline.sh [n8n_cloud_url]
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🚀 RIVET Pro Pipeline Test"
echo "=========================="
echo ""

# Configuration
N8N_URL="${1:-${N8N_CLOUD_URL:-https://your-instance.app.n8n.cloud}}"
MANUAL_HUNTER_WEBHOOK="$N8N_URL/webhook/rivet-manual-hunter"
PHOTO_BOT_WEBHOOK="$N8N_URL/webhook/rivet-photo-bot-v2"

# Check if URL is configured
if [[ "$N8N_URL" == *"your-instance"* ]]; then
    echo -e "${RED}ERROR: n8n Cloud URL not configured${NC}"
    echo ""
    echo "Set your n8n Cloud URL:"
    echo "  export N8N_CLOUD_URL=https://your-instance.app.n8n.cloud"
    echo "  ./scripts/test_abb_pipeline.sh"
    echo ""
    echo "Or pass it directly:"
    echo "  ./scripts/test_abb_pipeline.sh https://your-instance.app.n8n.cloud"
    exit 1
fi

echo "📋 Test Case: ABB ACS580-01-12A5-4"
echo "   This is the equipment that started RIVET Pro"
echo ""
echo "🔗 Target: $N8N_URL"
echo ""

# Test data - the original ABB equipment
TEST_DATA='{
  "manufacturer": "ABB",
  "model_number": "ACS580-01-12A5-4",
  "product_family": "ACS580",
  "chat_id": 123456789,
  "source": "automated_test"
}'

# =============================================================================
# Test 1: Manual Hunter Direct
# =============================================================================
echo "🔍 Test 1: Manual Hunter Direct Search"
echo "   Endpoint: $MANUAL_HUNTER_WEBHOOK"

START_TIME=$(date +%s%3N)

RESULT=$(curl -s -w "\n%{http_code}" -X POST "$MANUAL_HUNTER_WEBHOOK" \
  -H "Content-Type: application/json" \
  -d "$TEST_DATA" 2>/dev/null || echo "CURL_ERROR")

END_TIME=$(date +%s%3N)
DURATION=$((END_TIME - START_TIME))

# Extract HTTP status code (last line)
HTTP_CODE=$(echo "$RESULT" | tail -n1)
RESPONSE=$(echo "$RESULT" | sed '$d')

if [[ "$RESULT" == "CURL_ERROR" ]]; then
    echo -e "   ${RED}❌ FAILED: Could not connect to webhook${NC}"
    echo "   Make sure the Manual Hunter workflow is deployed and active"
    exit 1
fi

if [[ "$HTTP_CODE" != "200" ]]; then
    echo -e "   ${RED}❌ FAILED: HTTP $HTTP_CODE${NC}"
    echo "   Response: $RESPONSE"
    exit 1
fi

echo -e "   ${GREEN}✓ Response received (${DURATION}ms)${NC}"

# Parse result
FOUND=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('found', d.get('manual_found', False)))" 2>/dev/null || echo "parse_error")
PDF_URL=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('pdf_url', d.get('manual_url', 'not_found')))" 2>/dev/null || echo "parse_error")
TIER=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('search_tier', 'unknown'))" 2>/dev/null || echo "unknown")
CONFIDENCE=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('confidence_score', 0))" 2>/dev/null || echo "0")

echo ""
echo "📊 Results:"
echo "   Manual Found:  $FOUND"
echo "   Search Tier:   $TIER"
echo "   Confidence:    $CONFIDENCE%"
echo "   Response Time: ${DURATION}ms"
echo "   PDF URL:       $PDF_URL"
echo ""

# =============================================================================
# Validation
# =============================================================================
echo "✅ Validation:"

PASSED=true

# Check if manual was found
if [[ "$FOUND" == "True" || "$FOUND" == "true" ]]; then
    echo -e "   ${GREEN}✓ Manual found${NC}"
else
    echo -e "   ${RED}✗ Manual NOT found${NC}"
    PASSED=false
fi

# Check search tier (should be 1 or 2 for ABB)
if [[ "$TIER" == "1" || "$TIER" == "2" ]]; then
    echo -e "   ${GREEN}✓ Search tier acceptable ($TIER)${NC}"
else
    echo -e "   ${YELLOW}⚠ Search tier higher than expected ($TIER)${NC}"
fi

# Check response time (should be under 15 seconds)
if [[ $DURATION -lt 15000 ]]; then
    echo -e "   ${GREEN}✓ Response time acceptable (${DURATION}ms < 15000ms)${NC}"
else
    echo -e "   ${YELLOW}⚠ Response time slow (${DURATION}ms)${NC}"
fi

# Check if PDF URL contains ABB
if [[ "$PDF_URL" == *"abb"* || "$PDF_URL" == *"ABB"* || "$PDF_URL" == *"ACS580"* ]]; then
    echo -e "   ${GREEN}✓ PDF URL looks correct${NC}"
else
    echo -e "   ${YELLOW}⚠ PDF URL may not be ABB-specific${NC}"
fi

# Validate PDF is accessible (if found)
if [[ "$FOUND" == "True" || "$FOUND" == "true" ]] && [[ "$PDF_URL" != "not_found" ]]; then
    PDF_HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$PDF_URL" 2>/dev/null || echo "000")
    if [[ "$PDF_HTTP_CODE" == "200" ]]; then
        echo -e "   ${GREEN}✓ PDF URL is accessible (HTTP 200)${NC}"
    else
        echo -e "   ${YELLOW}⚠ PDF URL returned HTTP $PDF_HTTP_CODE${NC}"
    fi
fi

echo ""

# =============================================================================
# Final Result
# =============================================================================
if [[ "$PASSED" == "true" ]]; then
    echo -e "${GREEN}═══════════════════════════════════════${NC}"
    echo -e "${GREEN}   ✅ ABB PIPELINE TEST PASSED${NC}"
    echo -e "${GREEN}═══════════════════════════════════════${NC}"
    exit 0
else
    echo -e "${RED}═══════════════════════════════════════${NC}"
    echo -e "${RED}   ❌ ABB PIPELINE TEST FAILED${NC}"
    echo -e "${RED}═══════════════════════════════════════${NC}"
    echo ""
    echo "Full response:"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    exit 1
fi
