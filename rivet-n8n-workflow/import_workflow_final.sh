#!/bin/bash
# Final step: Import RIVET Pro workflow to n8n
# Usage: ./import_workflow_final.sh YOUR_N8N_API_KEY

API_KEY="$1"
N8N_URL="http://localhost:5678"
WORKFLOW_FILE="/opt/Rivet-PRO/rivet_workflow.json"

if [ -z "$API_KEY" ]; then
    echo "❌ Error: API key required"
    echo ""
    echo "Usage: $0 YOUR_API_KEY"
    echo ""
    echo "Get your API key:"
    echo "  1. Open http://72.60.175.144:5678"
    echo "  2. Settings → API → Generate API Key"
    echo "  3. Run: $0 n8n_api_YOUR_KEY"
    exit 1
fi

echo "🚀 Importing RIVET Pro workflow..."
echo ""

# Import workflow
RESPONSE=$(curl -s -X POST \
    -H "X-N8N-API-KEY: $API_KEY" \
    -H "Content-Type: application/json" \
    -d @"$WORKFLOW_FILE" \
    "$N8N_URL/api/v1/workflows")

# Check result
if echo "$RESPONSE" | grep -q '"id"'; then
    WORKFLOW_ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
    echo "✅ Workflow imported successfully!"
    echo ""
    echo "Workflow ID: $WORKFLOW_ID"
    echo "URL: http://72.60.175.144:5678/workflow/$WORKFLOW_ID"
    echo ""
    echo "📋 Next Steps:"
    echo "  1. Open: http://72.60.175.144:5678/workflow/$WORKFLOW_ID"
    echo "  2. Configure credentials (Telegram, Tavily, CMMS)"
    echo "  3. Set variables (GOOGLE_API_KEY, ATLAS_CMMS_URL)"
    echo "  4. Activate workflow"
    echo ""
else
    echo "❌ Import failed"
    echo "Response: $RESPONSE"
    exit 1
fi
