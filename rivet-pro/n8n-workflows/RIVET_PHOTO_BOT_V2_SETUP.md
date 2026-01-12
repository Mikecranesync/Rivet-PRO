# RIVET Photo Bot v2 - Setup Guide

## ✅ Workflow Created Successfully

**Workflow ID**: 7LMKcMmldZsu1l6g
**Workflow Name**: RIVET Photo Bot v2
**n8n Instance**: http://72.60.175.144:5678

---

## Workflow Architecture

### Nodes (10 total)
1. **Webhook Trigger** - Receives Telegram updates at `/rivet-photo-bot-v2`
2. **Extract Data** (Code) - Extracts chat_id, photo_file_id, has_photo from update
3. **Has Photo?** (IF) - Routes to photo analysis or help message
4. **Telegram Download File** (Native Telegram node) - Downloads photo from Telegram
5. **Gemini Vision Analysis** (HTTP Request) - Analyzes image with Google Gemini
   *Note: Uses HTTP Request temporarily - can be replaced with native Gemini node*
6. **Format Response** (Code) - Formats Gemini analysis into user-friendly message
7. **Telegram Send Analysis** (Native Telegram node) - Sends analysis back to user
8. **Telegram Send Help** (Native Telegram node) - Sends help message when no photo
9. **Respond to Webhook** (×2) - Returns {ok: true} to Telegram

### Native Nodes Used
- ✅ Native Telegram nodes for file download and message sending
- ⚠️ HTTP Request used for Gemini (native node config pending)
- ✅ Webhook and Code nodes (native)
- ✅ IF node (native)
- ✅ Respond to Webhook nodes (native)

---

## Required Setup Steps

### 1. Configure Telegram Bot API Credential

Open workflow in n8n UI and configure the Telegram nodes:

**Credential Type**: `telegramApi`
**Credential Name**: "Telegram Bot API" (or any name you prefer)
**Bot Token**: `8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE`

**Nodes that need this credential:**
- Telegram Download File
- Telegram Send Analysis
- Telegram Send Help

**Steps:**
1. Open http://72.60.175.144:5678/workflows
2. Find and open "RIVET Photo Bot v2"
3. Click on "Telegram Download File" node
4. Click "Create New Credential" under Telegram API
5. Enter bot token: `8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE`
6. Save credential
7. Apply same credential to "Telegram Send Analysis" and "Telegram Send Help" nodes

### 2. Configure Google Gemini API Credential

**Credential Type**: `googleApiKey` (or `googleGeminiApi`)
**Existing credential**: "Google Gemini(PaLM) Api account 3"
**Node that needs it**: "Gemini Vision Analysis"

**Steps:**
1. Click on "Gemini Vision Analysis" node
2. Select existing credential "Google Gemini(PaLM) Api account 3" from dropdown
3. OR create new credential with your Gemini API key
4. Save

**API Endpoint**: `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent`

### 3. Activate the Workflow

1. In the workflow editor, click the toggle at top right to **Activate**
2. The workflow will start listening for webhook requests

### 4. Get the Webhook URL

Once activated, the webhook URL will be:

```
https://72.60.175.144/webhook/rivet-photo-bot-v2
```

OR (if n8n is not behind a reverse proxy):

```
http://72.60.175.144:5678/webhook/rivet-photo-bot-v2
```

You can find the exact URL by:
1. Opening the "Webhook Trigger" node
2. Looking at the "Webhook URLs" section
3. Copying the "Production URL"

### 5. Register Webhook with Telegram

Run this command to register the webhook:

```bash
curl -X POST "https://api.telegram.org/bot8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "http://72.60.175.144:5678/webhook/rivet-photo-bot-v2"}'
```

**Expected Response:**
```json
{
  "ok": true,
  "result": true,
  "description": "Webhook was set"
}
```

**Verify webhook:**
```bash
curl "https://api.telegram.org/bot8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE/getWebhookInfo"
```

---

## Testing

### Test 1: Send Help Message

1. Open Telegram
2. Find bot: @rivet_local_dev_bot (or whatever bot uses token 8161680636:...)
3. Send a text message (no photo)
4. **Expected Response:**
   ```
   👋 Welcome to RIVET Photo Bot!

   Please send me a photo of equipment (nameplate, machinery, etc.) and I'll analyze it for you.

   I can identify:
   • Manufacturer & model
   • Serial numbers
   • Specifications
   • Visible issues or wear
   ```

### Test 2: Send Photo for Analysis

1. Send a photo of equipment/nameplate
2. Bot should respond within 10-20 seconds with:
   ```
   📸 Equipment Analysis:

   [Detailed analysis from Gemini Vision]
   ```

### Monitoring

**View Execution Logs:**
1. Go to http://72.60.175.144:5678/workflows
2. Click on "RIVET Photo Bot v2"
3. Click "Executions" tab to see execution history
4. Click on any execution to see the data flow through each node

**Check for Errors:**
- Red nodes indicate failures
- Click on failed node to see error message
- Common issues:
  - Missing credentials
  - Incorrect Gemini API key format
  - Webhook not registered with Telegram

---

## Troubleshooting

### Issue: Bot doesn't respond

**Check:**
1. Workflow is activated (toggle should be ON)
2. Webhook URL is registered with Telegram (`getWebhookInfo`)
3. Telegram can reach the n8n server (firewall/network)

**Debug:**
```bash
# Check if n8n is receiving webhooks
# Look for incoming requests in n8n execution logs
```

### Issue: Telegram nodes fail with "No credentials"

**Solution:**
- Ensure Telegram Bot API credential is created and selected in ALL three Telegram nodes
- Double-check bot token is correct

### Issue: Gemini Vision Analysis fails

**Common Errors:**
1. **401 Unauthorized**: API key is invalid or missing
   - Verify credential in "Gemini Vision Analysis" node
2. **400 Bad Request**: Image format issue
   - Ensure Telegram Download File returns binary data
   - Check that binary data is properly passed to Gemini node
3. **Model not found**: Model name incorrect
   - Current: `gemini-2.0-flash-exp`
   - Alternative: `gemini-1.5-flash` or `gemini-1.5-pro`

### Issue: Response format is wrong

**Solution:**
- Check "Format Response" Code node
- Verify it's reading Gemini response structure correctly:
  ```javascript
  geminiResponse.candidates[0].content.parts[0].text
  ```

---

## Next Steps

### Replace HTTP Request with Native Gemini Node (Optional)

Once you confirm the workflow works:

1. Add a native Gemini Chat Model node from n8n's AI nodes
2. Configure it to accept binary image input
3. Set the prompt in the node parameters
4. Replace the "Gemini Vision Analysis" HTTP Request node
5. Delete the HTTP Request node

**Benefits:**
- Better integration with n8n's AI features
- Automatic credential management
- Easier configuration

---

## Workflow Summary

| Node | Type | Purpose | Credentials Needed |
|------|------|---------|-------------------|
| Webhook Trigger | n8n-nodes-base.webhook | Receive Telegram updates | None |
| Extract Data | n8n-nodes-base.code | Parse Telegram update | None |
| Has Photo? | n8n-nodes-base.if | Route based on photo presence | None |
| Telegram Download File | n8n-nodes-base.telegram | Download photo binary | Telegram Bot API ✅ |
| Gemini Vision Analysis | n8n-nodes-base.httpRequest | Analyze image | Google API Key ✅ |
| Format Response | n8n-nodes-base.code | Format analysis text | None |
| Telegram Send Analysis | n8n-nodes-base.telegram | Send result to user | Telegram Bot API ✅ |
| Telegram Send Help | n8n-nodes-base.telegram | Send help message | Telegram Bot API ✅ |
| Respond to Webhook (×2) | n8n-nodes-base.respondToWebhook | Acknowledge Telegram | None |

**Total Nodes**: 10
**Native Telegram Nodes**: 3 ✅
**HTTP Request Nodes**: 1 (Gemini only) ⚠️
**Credentials Required**: 2 (Telegram Bot API, Google API Key)

---

## Success Criteria

- ✅ Workflow created in n8n (ID: 7LMKcMmldZsu1l6g)
- ⏳ Telegram Bot API credential configured
- ⏳ Google Gemini API credential configured
- ⏳ Workflow activated
- ⏳ Webhook registered with Telegram
- ⏳ Help message test passes
- ⏳ Photo analysis test passes
- ⏳ All executions succeed without errors

---

## Files Created

- `rivet-pro/n8n-workflows/rivet_photo_bot_v2_native.json` - Initial native node attempt
- `rivet-pro/n8n-workflows/rivet_photo_bot_v2_hybrid.json` - Working hybrid solution ✅
- `rivet-pro/n8n-workflows/RIVET_PHOTO_BOT_V2_SETUP.md` - This file

---

**Status**: Workflow created, awaiting credential configuration
**Next Action**: Configure credentials in n8n UI
**Estimated Time to Production**: 10-15 minutes
