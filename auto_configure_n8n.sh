#!/bin/bash
# Auto-configure n8n workflow with all credentials

set -e

N8N_URL="http://localhost:5678"
N8N_API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMTVjYWY5Ny04YjU4LTQwZDEtOGQwZi02Y2I0NzA0NDIwMjUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY3Njk5NTQxLCJleHAiOjE3NzAyNjc2MDB9.u1YVLEVetchYP2FcmUjfQSqNldb24gYbeSEArRT07lM"

TELEGRAM_TOKEN="8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE"
GOOGLE_API_KEY="AIzaSyBOEFzA3fWyS_s92h4Sd7ZaWIctiVXZjlA"
TAVILY_API_KEY="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"
ATLAS_CMMS_URL="http://localhost:8080/api"

echo "🚀 Auto-configuring n8n workflow..."
echo

# Step 1: Create Telegram credential
echo "1️⃣ Creating Telegram Bot credential..."
TELEGRAM_CRED=$(curl -s -X POST "${N8N_URL}/api/v1/credentials" \
  -H "X-N8N-API-KEY: ${N8N_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Rivet CMMS Bot",
    "type": "telegramApi",
    "data": {
      "accessToken": "'${TELEGRAM_TOKEN}'"
    }
  }')

TELEGRAM_CRED_ID=$(echo $TELEGRAM_CRED | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
if [ ! -z "$TELEGRAM_CRED_ID" ]; then
  echo "✅ Telegram credential created: ${TELEGRAM_CRED_ID}"
else
  echo "ℹ️  Telegram credential might already exist (checking...)"
  # List existing credentials
  EXISTING_CREDS=$(curl -s -X GET "${N8N_URL}/api/v1/credentials" \
    -H "X-N8N-API-KEY: ${N8N_API_KEY}")
  TELEGRAM_CRED_ID=$(echo $EXISTING_CREDS | grep -o '"id":"[^"]*","name":"Rivet CMMS Bot"' | cut -d'"' -f4 | head -1)
  if [ ! -z "$TELEGRAM_CRED_ID" ]; then
    echo "✅ Found existing Telegram credential: ${TELEGRAM_CRED_ID}"
  fi
fi
echo

# Step 2: Create Tavily credential
echo "2️⃣ Creating Tavily Search API credential..."
TAVILY_CRED=$(curl -s -X POST "${N8N_URL}/api/v1/credentials" \
  -H "X-N8N-API-KEY: ${N8N_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tavily Search API",
    "type": "httpHeaderAuth",
    "data": {
      "name": "Authorization",
      "value": "Bearer '${TAVILY_API_KEY}'"
    }
  }')

TAVILY_CRED_ID=$(echo $TAVILY_CRED | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
if [ ! -z "$TAVILY_CRED_ID" ]; then
  echo "✅ Tavily credential created: ${TAVILY_CRED_ID}"
else
  echo "ℹ️  Tavily credential might already exist"
fi
echo

# Step 3: Test backend and get JWT
echo "3️⃣ Testing Atlas CMMS backend..."
HEALTH_CHECK=$(curl -s http://localhost:8080/api/health || echo "")
if echo "$HEALTH_CHECK" | grep -q "UP"; then
  echo "✅ Atlas CMMS backend is running"

  echo "4️⃣ Getting JWT token..."
  # Try login
  JWT_RESPONSE=$(curl -s -X POST http://localhost:8080/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@example.com","password":"admin"}')

  JWT_TOKEN=$(echo $JWT_RESPONSE | grep -o '"token":"[^"]*' | cut -d'"' -f4)

  if [ -z "$JWT_TOKEN" ]; then
    echo "ℹ️  Login failed, trying registration..."
    REG_RESPONSE=$(curl -s -X POST http://localhost:8080/api/auth/register \
      -H "Content-Type: application/json" \
      -d '{"email":"admin@example.com","password":"admin","name":"Admin User"}')

    JWT_TOKEN=$(echo $REG_RESPONSE | grep -o '"token":"[^"]*' | cut -d'"' -f4)
  fi

  if [ ! -z "$JWT_TOKEN" ]; then
    echo "✅ Got JWT token: ${JWT_TOKEN:0:20}..."

    # Create Atlas CMMS credential
    echo "5️⃣ Creating Atlas CMMS credential..."
    ATLAS_CRED=$(curl -s -X POST "${N8N_URL}/api/v1/credentials" \
      -H "X-N8N-API-KEY: ${N8N_API_KEY}" \
      -H "Content-Type: application/json" \
      -d '{
        "name": "Atlas CMMS API",
        "type": "httpHeaderAuth",
        "data": {
          "name": "Authorization",
          "value": "Bearer '${JWT_TOKEN}'"
        }
      }')

    ATLAS_CRED_ID=$(echo $ATLAS_CRED | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
    if [ ! -z "$ATLAS_CRED_ID" ]; then
      echo "✅ Atlas CMMS credential created: ${ATLAS_CRED_ID}"
    fi
  else
    echo "⚠️  Could not get JWT token. Skip CMMS integration for now."
  fi
else
  echo "⚠️  Atlas CMMS backend not ready yet. Skip CMMS integration."
  echo "   You can run: docker-compose up -d rivet-java"
fi
echo

# Step 6: Import workflow
echo "6️⃣ Importing workflow..."
cd rivet-n8n-workflow

# Use a minimal workflow format that n8n API accepts
WORKFLOW_IMPORT=$(curl -s -X POST "${N8N_URL}/api/v1/workflows/import" \
  -H "X-N8N-API-KEY: ${N8N_API_KEY}" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@rivet_workflow_clean.json" || echo "")

if [ -z "$WORKFLOW_IMPORT" ]; then
  echo "ℹ️  API import failed, please import manually through UI"
  echo "   File: rivet-n8n-workflow/rivet_workflow_clean.json"
else
  WORKFLOW_ID=$(echo $WORKFLOW_IMPORT | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
  if [ ! -z "$WORKFLOW_ID" ]; then
    echo "✅ Workflow imported: ${WORKFLOW_ID}"
    echo "   URL: ${N8N_URL}/workflow/${WORKFLOW_ID}"
  fi
fi
cd ..
echo

# Summary
echo "📋 Configuration Summary"
echo "========================"
echo "Telegram Bot:      ${TELEGRAM_CRED_ID:-'Manual setup needed'}"
echo "Tavily Search:     ${TAVILY_CRED_ID:-'Manual setup needed'}"
echo "Atlas CMMS:        ${ATLAS_CRED_ID:-'Backend not ready'}"
echo "Google API Key:    Set in n8n UI → Settings → Variables"
echo "Atlas CMMS URL:    Set in n8n UI → Settings → Variables"
echo
echo "🎯 Next Steps:"
echo "1. Open n8n: ${N8N_URL}"
echo "2. If workflow not imported, manually import: rivet-n8n-workflow/rivet_workflow_clean.json"
echo "3. Set variables in Settings → Variables:"
echo "   - GOOGLE_API_KEY=${GOOGLE_API_KEY}"
echo "   - ATLAS_CMMS_URL=${ATLAS_CMMS_URL}"
echo "4. Activate workflow"
echo "5. Test with Telegram bot"
echo
echo "✅ Auto-configuration complete!"
