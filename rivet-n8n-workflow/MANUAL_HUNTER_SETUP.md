# Manual Hunter Workflow - Setup Guide

**Workflow Name**: RIVET Pro - Photo to Manual
**Nodes**: 24 (3-tier search architecture)
**n8n Version**: 1.117.3+
**Status**: Enhanced with Groq AI Tier 3

---

## Overview

This workflow implements a 3-tier cascading search system to find equipment manuals:

1. **Tier 1: Tavily Quick Search** (5 results, 2-5 seconds)
2. **Tier 2: Tavily Deep Search** (10 results, manufacturer-specific, 10-20 seconds)
3. **Tier 3: Groq AI Search** (LLM-powered web synthesis, 5-15 seconds)

Each tier only executes if the previous tier fails to find a manual.

---

## Prerequisites

### Required API Keys

You'll need to obtain the following API keys before importing the workflow:

| Service | Purpose | Tier | Cost | Rate Limit |
|---------|---------|------|------|------------|
| **Telegram Bot API** | Receive photos, send results | All | FREE | None |
| **Google Gemini** | OCR for nameplates | Pre-search | FREE tier available | 60 req/min |
| **Tavily Search** | Web search (Tiers 1 & 2) | 1-2 | $1/1000 searches | 100 req/min |
| **Groq** | LLM web search (Tier 3) | 3 | FREE | 30 req/min |
| **Atlas CMMS** (optional) | Equipment database | Post-OCR | N/A | N/A |

---

## Step 1: Obtain API Keys

### 1.1 Telegram Bot API

1. Open Telegram and message [@BotFather](https://t.me/botfather)
2. Send `/newbot`
3. Follow prompts to name your bot (e.g., "RIVET Manual Hunter")
4. Copy the API token (format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)
5. **Save this token** - you'll need it for n8n credentials

**Test your bot**:
```bash
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"
```

### 1.2 Google Gemini API

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with Google account
3. Click "Get API Key" → "Create API key in new project"
4. Copy the key (format: `AIzaSy...`)
5. **Save this key** - you'll need it for n8n

**Test your key**:
```bash
curl -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=<YOUR_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"contents": [{"parts": [{"text": "test"}]}]}'
```

**Expected response**: JSON with `candidates` array

### 1.3 Tavily Search API

1. Go to [Tavily](https://tavily.com/)
2. Sign up for free account
3. Go to dashboard → API Keys
4. Copy your API key (format: `tvly-...`)
5. **Save this key** - you'll need it for n8n

**Pricing**:
- Free tier: 1,000 searches/month
- Pro: $1 per 1,000 searches

**Test your key**:
```bash
curl -X POST "https://api.tavily.com/search" \
  -H "Authorization: Bearer <YOUR_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "search_depth": "basic", "max_results": 5}'
```

**Expected response**: JSON with `results` array

### 1.4 Groq API (FREE)

1. Go to [Groq Console](https://console.groq.com/)
2. Sign up with GitHub/Google
3. Go to API Keys → Create API Key
4. Copy the key (format: `gsk_...`)
5. **Save this key** - you'll need it for n8n

**Pricing**: **100% FREE** (rate-limited)
**Rate Limit**: 30 requests/minute, 14,400 requests/day

**Test your key**:
```bash
curl -X POST "https://api.groq.com/openai/v1/chat/completions" \
  -H "Authorization: Bearer <YOUR_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.3-70b-versatile",
    "messages": [{"role": "user", "content": "test"}],
    "temperature": 0.3,
    "max_tokens": 100
  }'
```

**Expected response**: JSON with `choices` array

---

## Step 2: Import Workflow to n8n

### 2.1 Access n8n Instance

Open your n8n instance:
```
http://72.60.175.144:5678
```

Login with your credentials.

### 2.2 Import Workflow

1. Click **"Workflows"** in sidebar
2. Click **"Add workflow"** dropdown → **"Import from file"**
3. Select file: `rivet-n8n-workflow/rivet_workflow.json`
4. Click **"Import"**

You should see 24 nodes arranged in the canvas.

### 2.3 Verify Import

Check that all nodes are present:
- ✅ 1 Telegram Trigger
- ✅ 5 Telegram Send nodes
- ✅ 6 HTTP Request nodes (Gemini, CMMS, Tavily x2, Groq)
- ✅ 4 IF nodes (Has Photo, Confidence, PDF Found x2, Groq Found)
- ✅ 2 Code nodes (Parse OCR, Parse Groq)
- ✅ 6 other nodes

**If any nodes are red/missing**: The import was incomplete. Try re-importing or manually fix missing nodes.

---

## Step 3: Configure Credentials

### 3.1 Telegram Bot API Credential

1. In n8n, click **"Credentials"** in sidebar → **"Add Credential"**
2. Search for **"Telegram API"**
3. Click **"Telegram API"**
4. Fill in:
   - **Credential Name**: `Telegram Bot - Manual Hunter`
   - **Access Token**: Paste your bot token from Step 1.1
5. Click **"Save"**

**Apply to nodes**:
1. Go back to workflow editor
2. Click on **"Telegram Photo Received"** node
3. Under **"Credentials"**, select **"Telegram Bot - Manual Hunter"**
4. Repeat for all 5 Telegram nodes:
   - Telegram Photo Received
   - Request Photo
   - Get Telegram File
   - Ask for Clarification
   - Send PDF Link
   - Send Deep Search Result
   - Send Groq Result
   - Send Not Found
5. **Save workflow** (Ctrl+S)

### 3.2 Google Gemini API Credential

**Option A: Use HTTP Query Auth** (Recommended)

1. Click **"Credentials"** → **"Add Credential"** → **"HTTP Query Auth"**
2. Fill in:
   - **Credential Name**: `Google Gemini API`
   - **Name**: `key`
   - **Value**: Paste your Gemini API key from Step 1.2
3. Click **"Save"**

**Apply to node**:
1. Click on **"Gemini Vision OCR"** node
2. Under **"Authentication"**, select **"Generic Credential Type"**
3. Under **"Generic Auth Type"**, select **"HTTP Query Auth"**
4. Under **"Credential for HTTP Query Auth"**, select **"Google Gemini API"**
5. **Save workflow**

**Option B: Use Workflow Variable** (Alternative)

1. Click workflow **"Settings"** (gear icon)
2. Add variable:
   - **Name**: `GOOGLE_API_KEY`
   - **Value**: Paste your Gemini API key
3. The **"Gemini Vision OCR"** node already references this: `={{ $vars.GOOGLE_API_KEY }}`
4. **Save workflow**

### 3.3 Tavily Search API Credential

1. Click **"Credentials"** → **"Add Credential"** → **"HTTP Header Auth"**
2. Fill in:
   - **Credential Name**: `Tavily Search API`
   - **Name**: `Authorization`
   - **Value**: `Bearer YOUR_TAVILY_KEY` (replace YOUR_TAVILY_KEY)
3. Click **"Save"**

**Apply to nodes**:
1. Click on **"Quick Manual Search"** node
2. Under **"Authentication"**, select **"Generic Credential Type"**
3. Under **"Generic Auth Type"**, select **"HTTP Header Auth"**
4. Under **"Credential for HTTP Header Auth"**, select **"Tavily Search API"**
5. Repeat for **"Deep Search - Manufacturer Site"** node
6. **Save workflow**

### 3.4 Groq API Credential

1. Click **"Credentials"** → **"Add Credential"** → **"HTTP Header Auth"**
2. Fill in:
   - **Credential Name**: `Groq API`
   - **Name**: `Authorization`
   - **Value**: `Bearer YOUR_GROQ_KEY` (replace YOUR_GROQ_KEY with key from Step 1.4)
3. Click **"Save"**

**Apply to node**:
1. Click on **"Groq Web Search"** node
2. Under **"Authentication"**, select **"Generic Credential Type"**
3. Under **"Generic Auth Type"**, select **"HTTP Header Auth"**
4. Under **"Credential for HTTP Header Auth"**, select **"Groq API"**
5. **Save workflow**

### 3.5 Atlas CMMS Credential (Optional)

**If you have Atlas CMMS running**:

1. Add workflow variable for CMMS URL:
   - **Settings** → **Variables**
   - **Name**: `ATLAS_CMMS_URL`
   - **Value**: `http://your-cmms-url:port` (e.g., `http://localhost:8000`)
2. Create HTTP Header Auth credential:
   - **Name**: `Atlas CMMS Auth`
   - **Header**: `Authorization`
   - **Value**: `Bearer YOUR_CMMS_TOKEN`
3. Apply to nodes:
   - Search Atlas CMMS
   - Create Asset
   - Update Asset

**If you don't have Atlas CMMS**:
- You can skip CMMS integration for now
- Manual search will still work
- Equipment won't be saved to database

---

## Step 4: Activate Workflow

1. In workflow editor, toggle **"Active"** switch (top-right)
2. Status should change to **"Active"**
3. Check **"Webhook URLs"** in **"Telegram Photo Received"** node
4. You should see a webhook URL like: `http://72.60.175.144:5678/webhook-test/rivet-manual-hunter`

---

## Step 5: Register Telegram Webhook

### 5.1 Set Webhook

Run this command (replace `<YOUR_BOT_TOKEN>` and `<WEBHOOK_URL>`):

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://72.60.175.144:5678/webhook-test/rivet-manual-hunter"
  }'
```

**Expected response**:
```json
{
  "ok": true,
  "result": true,
  "description": "Webhook was set"
}
```

**Note**: Telegram requires HTTPS for production webhooks. For testing, use:
- **ngrok** to create HTTPS tunnel: `ngrok http 5678`
- **Polling mode** with the `test_bot_polling.py` script (see Testing section)

### 5.2 Verify Webhook

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

**Expected response**:
```json
{
  "ok": true,
  "result": {
    "url": "http://72.60.175.144:5678/webhook-test/rivet-manual-hunter",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

---

## Step 6: Test the Workflow

### Quick Test (No Photo)

1. Open Telegram
2. Search for your bot (username from Step 1.1)
3. Send message: `hello`

**Expected response**:
```
📸 Please send a photo of the equipment nameplate, panel, or error display.

I'll:
• Extract the manufacturer and model
• Find the manual for you
• Save it to your CMMS
```

### Full Test (With Photo)

1. Take a clear photo of equipment nameplate (e.g., Siemens PLC)
2. Send photo to bot

**Expected workflow**:
1. Bot receives photo
2. Gemini OCR extracts manufacturer + model
3. **Tier 1**: Tavily quick search (5 results, 2-5 sec)
   - If PDF found → Send manual link ✅
   - If not found → Continue to Tier 2
4. **Tier 2**: Tavily deep search (manufacturer site, 10-20 sec)
   - If PDF found → Send manual link ✅
   - If not found → Continue to Tier 3
5. **Tier 3**: Groq AI search (LLM synthesis, 5-15 sec)
   - If PDF found → Send manual link ✅
   - If not found → Send "Manual Not Found" message

**Expected response (if manual found)**:
```
📋 Manual Found!

Equipment: Siemens S7-1200
Serial: 6ES7214-1AG40-0XB0

📥 [Download Manual](https://support.siemens.com/...)

✅ Asset saved to CMMS
```

### Monitor Executions

1. Go to n8n: **Workflows** → **RIVET Pro - Photo to Manual** → **Executions**
2. Click on latest execution
3. Verify:
   - All nodes executed successfully (green)
   - No red (failed) nodes
   - Data flows through correctly

---

## Troubleshooting

### Issue: Bot doesn't respond to photos

**Check**:
1. Workflow is **Active** (toggle on)
2. Webhook is registered: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`
3. Telegram credential is configured in all 8 Telegram nodes
4. Firewall allows incoming connections to n8n (port 5678)

**Debug**:
```bash
# Check n8n logs
docker logs <n8n-container-id>

# Or if running directly:
tail -f ~/.n8n/logs/n8n.log
```

### Issue: OCR fails (Gemini node red)

**Common causes**:
1. **Invalid API key**: Check Gemini credential
2. **API quota exceeded**: Check [Google AI Studio](https://aistudio.google.com/app/apikey) quota
3. **Binary data not passed**: Ensure "Download Photo" node returns `responseFormat: file`

**Test Gemini API directly**:
```bash
curl -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=<KEY>" \
  -d '{"contents": [{"parts": [{"text": "test"}]}]}'
```

### Issue: Tavily search fails (401 Unauthorized)

**Fix**:
1. Check Tavily credential is configured
2. Verify API key format: `Bearer tvly-...`
3. Test API key directly (see Step 1.3)

### Issue: Groq search fails (401 Unauthorized)

**Fix**:
1. Check Groq credential is configured
2. Verify API key format: `Bearer gsk_...`
3. Check rate limit: 30 req/min (wait 2 minutes and retry)
4. Test API key directly (see Step 1.4)

### Issue: "Manual Not Found" for common equipment

**Possible causes**:
1. OCR extracted wrong manufacturer/model (check execution logs)
2. All 3 search tiers failed
3. Tavily/Groq API issues

**Debug**:
1. Check **"Parse OCR Response"** node output:
   - Is manufacturer correct?
   - Is model number correct?
   - Is confidence >= 70%?
2. Check **"Quick Manual Search"** node output:
   - Did Tavily return results?
   - Check `results` array
3. Check **"Parse Groq Response"** node output:
   - Did Groq return a PDF URL?
   - Check `pdf_url` field

### Issue: Workflow slow (> 60 seconds)

**Check**:
1. How many tiers executed?
   - Tier 1: 2-5 sec
   - Tier 1 + 2: 15-25 sec
   - All 3 tiers: 25-40 sec
2. Tavily API latency (check `search_depth: "advanced"` for Tier 2)
3. Groq API latency (free tier can be slower during high usage)

**Optimize**:
- Reduce Tavily `max_results` (currently 5 for Tier 1, 10 for Tier 2)
- Use Gemini `gemini-1.5-flash` instead of Pro (faster OCR)

---

## Cost Estimates

### Per Manual Search

| Scenario | APIs Used | Cost |
|----------|-----------|------|
| **Tier 1 success** | Gemini + Tavily Quick | $0.001 |
| **Tier 2 success** | Gemini + Tavily Quick + Tavily Deep | $0.002 |
| **Tier 3 success** | Gemini + Tavily x2 + Groq | $0.002 (Groq FREE) |
| **Not found** | All tiers | $0.002 |

### Monthly Estimates (100 searches/month)

- **Gemini Vision**: FREE (within 60 req/min limit)
- **Tavily**: $0.20 (100 searches × 2 avg tiers × $0.001)
- **Groq**: FREE
- **Total**: **~$0.20/month** for 100 manual searches

**Groq is completely free**, so Tier 3 adds zero cost!

---

## Rate Limits

| Service | Limit | Handling |
|---------|-------|----------|
| Gemini | 60 req/min | n8n auto-queues |
| Tavily | 100 req/min | n8n auto-retries |
| Groq | 30 req/min | Add 2-second delay between calls |
| Telegram | None | No limit |

---

## Next Steps

1. ✅ Import workflow
2. ✅ Configure 4 credentials (Telegram, Gemini, Tavily, Groq)
3. ✅ Activate workflow
4. ✅ Register webhook
5. ✅ Test with equipment photo
6. 📋 Integrate with Photo Bot V2 (see `PHOTO_BOT_V2_INTEGRATION.md`)
7. 🧪 Run full test suite (see `End-to-End Testing Plan` in plan file)

---

## Support

**Workflow File**: `rivet-n8n-workflow/rivet_workflow.json`
**Integration Guide**: `PHOTO_BOT_V2_INTEGRATION.md`
**Technical Spec**: `GROQ_SEARCH_IMPLEMENTATION.md`
**n8n Instance**: http://72.60.175.144:5678

**Workflow Stats**:
- 24 nodes total
- 3-tier search cascade
- 8 Telegram nodes
- 6 HTTP Request nodes
- 4 IF conditional nodes
- 2 Code nodes

**Last Updated**: 2026-01-09
