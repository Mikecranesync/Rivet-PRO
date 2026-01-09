# RIVET Manual Hunter - API Credentials Setup Guide

## Overview
This guide walks you through setting up all required API credentials for the Manual Hunter workflow in n8n.

## Prerequisites
- Active n8n cloud account or self-hosted instance
- Admin access to create credentials
- Credit card for paid APIs (Serper, Perplexity)

---

## Credential Setup Checklist

- [ ] Telegram Bot API (Existing - Verify)
- [ ] Neon PostgreSQL (Existing - Add Tables)
- [ ] Tavily API (Free Tier)
- [ ] Groq API (Free Tier)
- [ ] Serper API (Paid)
- [ ] DeepSeek API (Cheap)
- [ ] Perplexity API (Paid - Optional)

---

## 1. Telegram Bot API (Already Configured)

**Status**: ✅ Existing credential

**Credential Details**:
- **ID**: `if4EOJbvMirfWqCC`
- **Name**: `Telegram Bot`
- **Bot Token**: `8161680636:*` (already configured)

**Verification**:
1. Open n8n → **Credentials** tab
2. Search for "Telegram Bot"
3. Verify credential ID matches `if4EOJbvMirfWqCC`
4. **DO NOT** modify this credential

---

## 2. Neon PostgreSQL (Add Tables)

**Status**: ✅ Existing credential, ⚠️ Need to add tables

**Credential Details**:
- **Name**: `Neon RIVET`
- **Type**: PostgreSQL
- **Connection**: Already configured

**Setup Steps**:
1. Connect to your Neon database using SQL editor
2. Run the schema file: `database/schema/manual_hunter_tables.sql`
3. Verify tables created:
   ```sql
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'public'
   AND table_name IN ('manuals', 'manual_requests');
   ```

**Expected Output**:
```
table_name
--------------
manuals
manual_requests
```

---

## 3. Tavily API (Free Tier - Tier 1 Search)

**Purpose**: Web search for equipment manuals (Tier 1)
**Cost**: FREE - 1,000 searches/month
**Success Rate**: ~80% of manual searches

### Step 1: Create Account
1. Visit: https://tavily.com
2. Click **Sign Up** (top right)
3. Use email or Google OAuth
4. Verify your email

### Step 2: Get API Key
1. After login, go to **Dashboard**
2. Click **API Keys** in sidebar
3. Click **Create New API Key**
4. Copy the API key (format: `tvly-xxxxx`)
5. **Save it securely** - shown only once

### Step 3: Configure in n8n
1. Open n8n → **Credentials** tab
2. Click **+ Add Credential**
3. Search for: **HTTP Header Auth**
4. Configure:
   - **Name**: `Tavily API`
   - **Header Name**: `X-API-Key`
   - **Header Value**: `tvly-xxxxx` (paste your key)
5. Click **Save**

### Step 4: Test Connection
```bash
curl -X POST https://api.tavily.com/search \
  -H "X-API-Key: YOUR_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ABB ACS580 manual PDF",
    "max_results": 5
  }'
```

**Expected Response**: JSON with search results

---

## 4. Groq API (Free Tier - Tier 1 Evaluation)

**Purpose**: LLM evaluation of search results (Tier 1)
**Cost**: FREE - 30 requests/minute, generous monthly limits
**Model**: Llama 3.1 70B Versatile

### Step 1: Create Account
1. Visit: https://console.groq.com
2. Click **Sign Up**
3. Use email or GitHub OAuth
4. Verify email if required

### Step 2: Get API Key
1. After login, go to **API Keys** section
2. Click **Create API Key**
3. Name it: `RIVET Manual Hunter`
4. Copy the key (format: `gsk_xxxxx`)
5. **Save securely** - shown only once

### Step 3: Configure in n8n
1. Open n8n → **Credentials** tab
2. Click **+ Add Credential**
3. Search for: **HTTP Header Auth**
4. Configure:
   - **Name**: `Groq API`
   - **Header Name**: `Authorization`
   - **Header Value**: `Bearer gsk_xxxxx` (paste your key with "Bearer " prefix)
5. Click **Save**

### Step 4: Test Connection
```bash
curl -X POST https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.1-70b-versatile",
    "messages": [{"role": "user", "content": "Hello!"}],
    "temperature": 0.3
  }'
```

**Expected Response**: JSON with chat completion

---

## 5. Serper API (Paid - Tier 2 Search)

**Purpose**: Google search API for edge cases (Tier 2)
**Cost**: $50 for 2,500 searches (~$0.02 per search)
**Success Rate**: ~15% additional coverage when Tier 1 fails

### Step 1: Create Account
1. Visit: https://serper.dev
2. Click **Get Started** or **Sign Up**
3. Use email or Google OAuth
4. Verify email

### Step 2: Add Credits
1. Go to **Billing** section
2. Click **Add Credits**
3. Purchase credits:
   - **Recommended**: $50 package (2,500 searches)
   - **Minimum**: $20 package (1,000 searches)
4. Complete payment

### Step 3: Get API Key
1. Go to **API Keys** section
2. Copy your API key (shown on dashboard)
3. Format: `xxxxx` (alphanumeric string)

### Step 4: Configure in n8n
1. Open n8n → **Credentials** tab
2. Click **+ Add Credential**
3. Search for: **HTTP Header Auth**
4. Configure:
   - **Name**: `Serper API`
   - **Header Name**: `X-API-KEY`
   - **Header Value**: `xxxxx` (paste your key)
5. Click **Save**

### Step 5: Test Connection
```bash
curl -X POST https://google.serper.dev/search \
  -H "X-API-KEY: YOUR_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "ABB ACS580 manual PDF",
    "num": 10
  }'
```

**Expected Response**: JSON with Google search results

---

## 6. DeepSeek API (Cheap - Tier 2 Evaluation)

**Purpose**: Advanced reasoning for partial matches (Tier 2)
**Cost**: $0.14 per 1M input tokens (~$0.0001 per evaluation)
**Model**: DeepSeek Chat

### Step 1: Create Account
1. Visit: https://platform.deepseek.com
2. Click **Sign Up** (may need to click "English" for language)
3. Use email registration
4. Verify email

### Step 2: Add Credits
1. Go to **Billing** or **Account**
2. Add minimum credits (~$5 will last months)
3. Payment methods: Credit card or crypto

### Step 3: Get API Key
1. Go to **API Keys** section
2. Click **Create API Key**
3. Name it: `RIVET Manual Hunter`
4. Copy the key (format: `sk-xxxxx`)
5. **Save securely**

### Step 4: Configure in n8n
1. Open n8n → **Credentials** tab
2. Click **+ Add Credential**
3. Search for: **HTTP Header Auth**
4. Configure:
   - **Name**: `DeepSeek API`
   - **Header Name**: `Authorization`
   - **Header Value**: `Bearer sk-xxxxx` (paste with "Bearer " prefix)
5. Click **Save**

### Step 5: Test Connection
```bash
curl -X POST https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Test"}]
  }'
```

**Expected Response**: JSON with chat completion

---

## 7. Perplexity API (Paid - Tier 3 Research)

**Purpose**: Deep web research for rare equipment (Tier 3)
**Cost**: $5 per 1,000 requests (~$0.005 per search)
**Success Rate**: ~4% additional coverage (rare equipment)
**Status**: ⚠️ Optional - can skip Tier 3 initially

### Step 1: Create Account
1. Visit: https://www.perplexity.ai/settings/api
2. Sign up for Perplexity Pro (required for API access)
3. Cost: $20/month subscription

### Step 2: Enable API Access
1. Go to **Settings** → **API**
2. Enable API access (may require separate payment)
3. Pricing: $5 per 1,000 requests

### Step 3: Get API Key
1. In API settings, click **Generate API Key**
2. Name it: `RIVET Manual Hunter`
3. Copy key (format: `pplx-xxxxx`)
4. **Save securely**

### Step 4: Configure in n8n
1. Open n8n → **Credentials** tab
2. Click **+ Add Credential**
3. Search for: **HTTP Header Auth**
4. Configure:
   - **Name**: `Perplexity API`
   - **Header Name**: `Authorization`
   - **Header Value**: `Bearer pplx-xxxxx` (paste with "Bearer " prefix)
5. Click **Save**

### Step 5: Test Connection
```bash
curl -X POST https://api.perplexity.ai/chat/completions \
  -H "Authorization: Bearer YOUR_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.1-sonar-large-128k-online",
    "messages": [{"role": "user", "content": "Test"}]
  }'
```

**Expected Response**: JSON with research results

---

## Cost Summary

| Service | Type | Monthly Cost | Purpose |
|---------|------|--------------|---------|
| Tavily | Free | $0 | Tier 1 search (80% success) |
| Groq | Free | $0 | Tier 1 evaluation |
| Serper | Paid | ~$3* | Tier 2 search (15% escalation) |
| DeepSeek | Paid | ~$0.20* | Tier 2 evaluation |
| Perplexity | Paid | ~$0.20* | Tier 3 research (4% escalation) |
| Neon PostgreSQL | Existing | $0** | Database caching |
| Telegram | Existing | $0 | User messaging |
| **TOTAL** | | **~$3.40/month*** | For 1,000 manual searches |

*Assumes 1,000 manual searches/month with tier distribution
**Assuming existing Neon free tier or paid plan

### Cost Optimization Tips
- **80% of searches use free Tier 1** → Most users pay nothing
- **Aggressive caching** → Repeat lookups cost $0
- **Skip Perplexity initially** → Save $0.20+/month
- **Monitor usage** → Adjust tier confidence thresholds if costs spike

---

## Verification Checklist

After setting up all credentials, verify in n8n:

```
✅ Credentials Created:
  ├─ Telegram Bot (if4EOJbvMirfWqCC) ✅ Existing
  ├─ Neon RIVET ✅ Existing + Tables Added
  ├─ Tavily API ⬜ Created
  ├─ Groq API ⬜ Created
  ├─ Serper API ⬜ Created
  ├─ DeepSeek API ⬜ Created
  └─ Perplexity API ⬜ Created (Optional)

✅ Database Tables:
  ├─ manuals ⬜ Created
  └─ manual_requests ⬜ Created

✅ Workflow Import:
  └─ rivet_manual_hunter.json ⬜ Imported & Activated
```

---

## Troubleshooting

### "Credential not found" error
- Verify credential names match exactly (case-sensitive)
- Check credential IDs in workflow JSON
- Re-import workflow after creating credentials

### "Authorization failed" errors
- Verify API key copied correctly (no extra spaces)
- Check "Bearer " prefix for OAuth APIs (Groq, DeepSeek, Perplexity)
- Test API keys using cURL commands above

### "Insufficient credits" errors
- Add credits to paid services (Serper, DeepSeek, Perplexity)
- Check account balance in service dashboards
- Monitor usage to avoid rate limits

### Database connection errors
- Verify Neon connection string is active
- Check database tables were created successfully
- Run schema file again if tables missing

---

## Next Steps

After completing credential setup:

1. ✅ Import workflow: `rivet_manual_hunter.json`
2. ✅ Assign credentials to nodes
3. ✅ Activate workflow
4. ✅ Test with sample payload
5. ✅ Integrate with Photo Bot V2
6. ✅ Monitor performance and costs

See `PHOTO_BOT_V2_INTEGRATION_GUIDE.md` for integration steps.

---

**Document Version**: 1.0
**Last Updated**: 2026-01-09
**Support**: Check n8n execution logs for credential errors
