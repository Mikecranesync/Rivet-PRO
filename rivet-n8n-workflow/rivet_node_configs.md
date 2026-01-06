# RIVET Pro - Node Configuration Guide

## After Import Checklist

After importing `rivet_workflow.json` into n8n, you'll need to configure credentials and variables.

### 1. Credentials to Configure

| Credential Name | Type | Purpose | Where to Get |
|-----------------|------|---------|--------------|
| Telegram Bot | Telegram API | Receive photos, send responses | @BotFather on Telegram → `/newbot` → copy token |
| Google API (Gemini) | HTTP Query Auth | OCR via Gemini Vision | [Google AI Studio](https://makersuite.google.com/app/apikey) → Create API Key |
| Tavily API | HTTP Header Auth | Web search for manuals | [tavily.com](https://tavily.com) → Sign up → API Keys |
| Atlas CMMS | HTTP Header Auth | Equipment database | Your Atlas instance admin panel |

---

## 2. Setting Up Credentials in n8n

### Telegram Bot Credential

1. **Create the Bot:**
   - Open Telegram, search for `@BotFather`
   - Send `/newbot`
   - Follow prompts to name your bot
   - Copy the bot token (format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

2. **Add to n8n:**
   - n8n → Credentials → + New Credential
   - Search "Telegram"
   - Select "Telegram API"
   - Paste your bot token
   - Test connection
   - Save as "Telegram Bot"

### Google Gemini API Credential

1. **Get API Key:**
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Sign in with Google account
   - Click "Create API Key"
   - Copy the key (format: `AIzaSy...`)

2. **Add to n8n:**
   - Instead of creating a credential, we'll use a **variable**
   - Go to Settings → Variables
   - Add variable: `GOOGLE_API_KEY` = `your-api-key-here`

### Tavily API Credential

1. **Get API Key:**
   - Visit [tavily.com](https://tavily.com)
   - Sign up for free tier (1000 searches/month)
   - Navigate to API Keys section
   - Copy API key (format: `tvly-...`)

2. **Add to n8n:**
   - n8n → Credentials → + New Credential
   - Select "HTTP Header Auth"
   - Name: "Tavily API"
   - Header Name: `Authorization`
   - Header Value: `Bearer YOUR_TAVILY_KEY`
   - Save

### Atlas CMMS API Credential

1. **Get API Token:**
   - From your Atlas CMMS admin panel
   - Generate API token or use JWT from login
   - Copy token

2. **Add to n8n:**
   - n8n → Credentials → + New Credential
   - Select "HTTP Header Auth"
   - Name: "Atlas CMMS API"
   - Header Name: `Authorization`
   - Header Value: `Bearer YOUR_ATLAS_TOKEN`
   - Save

---

## 3. Variables to Set

Go to **Settings → Variables** in n8n and add:

| Variable Name | Value | Purpose |
|---------------|-------|---------|
| `ATLAS_CMMS_URL` | `https://your-atlas-instance.com` | Base URL for CMMS API |
| `GOOGLE_API_KEY` | `AIzaSy...` | Google Gemini API key |

**Example:**
```
ATLAS_CMMS_URL = https://rivet-cmms.com
GOOGLE_API_KEY = AIzaSyABC123XYZ789example
```

---

## 4. Node-by-Node Configuration

### Node: Telegram Photo Received (Trigger)

**Purpose:** Listens for incoming Telegram messages

**Setup:**
1. Double-click the node
2. Click "Credential to connect with"
3. Select your "Telegram Bot" credential
4. Updates: Keep `message` selected
5. No additional filters needed (we check for photo in next node)
6. Save

**Test:**
- Send any message to your bot
- Node should trigger and show execution in n8n

---

### Node: Has Photo? (IF Node)

**Purpose:** Checks if message contains a photo

**Configuration (Already Set):**
- Condition: `{{ $json.message.photo }}` exists
- Output 1 (True): Photo present → proceed to Get File
- Output 2 (False): No photo → Request Photo

**No changes needed** - works out of the box

---

### Node: Get Telegram File

**Purpose:** Gets file metadata from Telegram API

**Setup:**
1. Select your "Telegram Bot" credential
2. Operation: `getFile`
3. File ID: `={{ $json.message.photo.slice(-1)[0].file_id }}`

**How it works:**
- Telegram sends photo in multiple sizes
- `slice(-1)[0]` gets the highest resolution photo
- Returns file path for download

---

### Node: Download Photo

**Purpose:** Downloads the photo binary from Telegram servers

**Configuration (Already Set):**
- Method: GET
- URL: Constructs Telegram file URL dynamically
- Response: File format (binary)

**Important:**
- Uses `{{ $credentials.telegramApi.accessToken }}` - automatic
- Photo stored in `$binary.data` for next node

---

### Node: Gemini Vision OCR

**Purpose:** Extracts equipment data from photo using AI vision

**Setup:**
1. **NO credential needed** - uses variable `GOOGLE_API_KEY`
2. Verify JSON body is correct (already configured)

**Prompt Explanation:**
```
Extract from this equipment photo:
- manufacturer
- model number
- serial number
- any error codes or fault displays

Return ONLY valid JSON with these exact keys:
{
  "manufacturer": "Siemens",
  "model": "S7-1200",
  "serial": "6ES7214",
  "errors": null,
  "confidence": 95
}
```

**Parameters:**
- Model: `gemini-1.5-flash` (fastest, cheapest)
- Image: Base64 encoded from `$binary.data`
- API Key: Passed as query parameter

**Expected Response:**
```json
{
  "candidates": [{
    "content": {
      "parts": [{
        "text": "{\"manufacturer\":\"Siemens\",\"model\":\"S7-1200\",\"serial\":\"6ES7214\",\"errors\":null,\"confidence\":95}"
      }]
    }
  }]
}
```

---

### Node: Parse OCR Response (Code)

**Purpose:** Extracts clean JSON from Gemini's response

**Code Explanation:**

```javascript
// 1. Get Gemini's text response
const text = response.candidates?.[0]?.content?.parts?.[0]?.text || '';

// 2. Try to parse JSON (handles markdown code blocks)
const jsonMatch = text.match(/\{[\s\S]*\}/);
extracted = JSON.parse(jsonMatch[0]);

// 3. Fallback: regex extraction if JSON parsing fails
extracted = {
  manufacturer: text.match(/manufacturer[:\s]+([\w\s&.-]+)/i)?.[1]?.trim() || 'Unknown',
  model: text.match(/model[:\s]+([\w\s\-\/]+)/i)?.[1]?.trim() || 'Unknown',
  ...
};

// 4. Add chat_id for later responses
const chatId = $('Telegram Photo Received').item.json.message.chat.id;

return {
  json: { ...extracted, chat_id: chatId }
};
```

**No configuration needed** - works automatically

**Output Example:**
```json
{
  "manufacturer": "Siemens",
  "model": "SIMATIC S7-1200",
  "serial": "6ES7 214-1AG40-0XB0",
  "errors": null,
  "confidence": 92,
  "chat_id": 123456789,
  "raw_text": "..."
}
```

---

### Node: Confidence >= 70%? (IF Node)

**Purpose:** Quality gate for OCR accuracy

**Configuration (Already Set):**
- Condition: `{{ $json.confidence }}` >= 70
- True path: Proceed to CMMS
- False path: Ask user for clarification

**Rationale:**
- < 70%: OCR too uncertain, ask for better photo
- >= 70%: Confident enough to create/update asset

---

### Node: Search Atlas CMMS

**Purpose:** Check if equipment already exists in database

**Setup:**
1. Select "Atlas CMMS API" credential
2. Verify URL: `={{ $vars.ATLAS_CMMS_URL }}/api/equipment`
3. Method: GET
4. Query parameters:
   - `manufacturer` = `={{ $json.manufacturer }}`
   - `model` = `={{ $json.model }}`

**Important:**
- Endpoint must return array: `{ "data": [{ equipment objects }] }`
- If your CMMS API structure differs, adjust the path

**Expected Response:**
```json
{
  "data": [
    {
      "id": "uuid-123",
      "manufacturer": "Siemens",
      "model_number": "SIMATIC S7-1200",
      "serial_number": "...",
      "last_seen": "2026-01-05T10:00:00Z"
    }
  ]
}
```

---

### Node: Asset Exists? (IF Node)

**Purpose:** Determine if we update or create

**Configuration (Already Set):**
- Condition: `{{ $json.data && $json.data.length > 0 }}` = true
- True: Asset exists → Update
- False: New asset → Create

---

### Node: Update Asset

**Purpose:** Update existing asset's last_seen timestamp

**Setup:**
1. Select "Atlas CMMS API" credential
2. Method: PATCH
3. URL: `={{ $vars.ATLAS_CMMS_URL }}/api/equipment/{{ $json.data[0].id }}`
4. Body:
```json
{
  "last_seen": "{{ new Date().toISOString() }}",
  "serial_number": "{{ $('Parse OCR Response').item.json.serial }}"
}
```

**Purpose:**
- Updates timestamp to track when equipment was last seen
- Updates serial if it changed (useful for swapped equipment)

---

### Node: Create Asset

**Purpose:** Create new equipment record in CMMS

**Setup:**
1. Select "Atlas CMMS API" credential
2. Method: POST
3. URL: `={{ $vars.ATLAS_CMMS_URL }}/api/equipment`
4. Body:
```json
{
  "manufacturer": "{{ $('Parse OCR Response').item.json.manufacturer }}",
  "model_number": "{{ $('Parse OCR Response').item.json.model }}",
  "serial_number": "{{ $('Parse OCR Response').item.json.serial }}",
  "created_via": "telegram_bot",
  "status": "operational"
}
```

**Important:**
- Adjust field names to match your CMMS schema
- Common variations: `model` vs `model_number`, `serial` vs `serial_number`
- `created_via` helps track source of asset

---

### Node: Quick Manual Search

**Purpose:** Fast search for equipment manual

**Setup:**
1. Select "Tavily API" credential
2. Method: POST
3. URL: `https://api.tavily.com/search`
4. Body:
```json
{
  "query": "{{ manufacturer }} {{ model }} user manual PDF filetype:pdf",
  "search_depth": "basic",
  "include_answer": false,
  "max_results": 5
}
```

**Search Depth:**
- `basic`: Fast, checks top results (2-5 seconds)
- `advanced`: Thorough, crawls multiple pages (10-20 seconds)

**Expected Response:**
```json
{
  "results": [
    {
      "title": "SIMATIC S7-1200 Manual",
      "url": "https://.../manual.pdf",
      "content": "User manual for..."
    }
  ]
}
```

---

### Node: PDF Found? (IF Node)

**Purpose:** Check if quick search found a manual

**Configuration (Already Set):**
- Checks if any result URL contains `.pdf` or `manual`
- True: Send link immediately
- False: Try deep search

**Logic:**
```javascript
$json.results.filter(r =>
  r.url &&
  (r.url.toLowerCase().includes('.pdf') ||
   r.url.toLowerCase().includes('manual'))
).length > 0
```

---

### Node: Deep Search - Manufacturer Site

**Purpose:** Targeted search on manufacturer's website

**Setup:**
1. Select "Tavily API" credential
2. Method: POST
3. Search depth: `advanced`
4. Query: `site:manufacturer.com model manual PDF`

**Dynamic Site Construction:**
```javascript
// Converts "Siemens AG" → "siemensag.com"
$('Parse OCR Response').item.json.manufacturer
  .toLowerCase()
  .replace(/\s/g, '')
  .replace(/[^a-z0-9]/g, '')
```

**Examples:**
- "Siemens" → `site:siemens.com`
- "Allen-Bradley" → `site:allenbradley.com`
- "Schneider Electric" → `site:schneiderelectric.com`

---

### Nodes: Send Telegram Responses

All response nodes use same credential: "Telegram Bot"

**Send PDF Link:**
- Markdown format with download link
- Shows manufacturer, model, serial
- Confirms CMMS save

**Send Deep Search Result:**
- Same format, indicates it was deep search
- Might not be direct PDF link (manual page)

**Send Not Found:**
- Provides manual search suggestions
- Shows Google search link
- Confirms CMMS saved asset anyway

**Ask for Clarification:**
- Shows partial OCR data
- Requests better photo or manual entry
- Includes confidence score

---

## 5. Testing Sequence

### Step 1: Test Telegram Trigger

1. Open n8n workflow
2. Click "Execute Workflow" or enable auto-execution
3. Send any message to your Telegram bot
4. Verify: Node fires and shows in execution log

**Expected:** Trigger activates, shows message JSON

---

### Step 2: Test with Text Message (No Photo)

1. Send text message to bot: "Hello"
2. Should execute: Trigger → Has Photo? (False) → Request Photo

**Expected Response:**
```
📸 Please send a photo of the equipment nameplate, panel, or error display.

I'll:
• Extract the manufacturer and model
• Find the manual for you
• Save it to your CMMS
```

---

### Step 3: Test with Equipment Photo

1. Find equipment nameplate photo (or use test image)
2. Send to Telegram bot
3. Watch execution flow in n8n

**Should Execute:**
1. Trigger (Photo received)
2. Has Photo? (True)
3. Get File → Download → Gemini OCR
4. Parse OCR
5. If confidence >= 70%:
   - Search CMMS → Create/Update
   - Quick Search → PDF Found? → Send Result

**Expected Response (Success):**
```
📋 Manual Found!

Equipment: Siemens SIMATIC S7-1200
Serial: 6ES7 214-1AG40-0XB0

📥 Download Manual

✅ Asset saved to CMMS
```

---

### Step 4: Test with Blurry Photo

1. Send intentionally blurry/unclear photo
2. Should trigger low confidence path

**Expected Response:**
```
🔍 I couldn't read the equipment info clearly (45% confidence).

I found:
• Manufacturer: unclear
• Model: unclear
• Serial: unclear

Could you:
1. Take a clearer photo of the nameplate
2. Or type the info: Manufacturer - Model Number
```

---

### Step 5: Verify CMMS Integration

1. After successful photo processing
2. Check Atlas CMMS directly
3. Verify asset was created/updated

**Verify:**
- Equipment record exists
- Manufacturer/model/serial correct
- `created_via` = "telegram_bot"
- `last_seen` timestamp recent

---

## 6. Troubleshooting

### Issue: Telegram Trigger Not Firing

**Check:**
- Bot token correct in credential
- Workflow is "Active" (toggle in top-right)
- Telegram bot not blocked by user
- n8n has internet access

**Fix:**
- Re-create Telegram credential
- Test bot token: `curl https://api.telegram.org/bot<TOKEN>/getMe`

---

### Issue: Gemini OCR Returns Error

**Check:**
- `GOOGLE_API_KEY` variable set correctly
- API key has Gemini API enabled
- Image size < 20MB
- Billing enabled on Google Cloud (if free tier exhausted)

**Fix:**
- Re-generate API key
- Enable "Generative Language API" in Google Cloud Console
- Use smaller image (n8n might timeout on huge files)

---

### Issue: CMMS API Returns 401 Unauthorized

**Check:**
- `ATLAS_CMMS_URL` variable correct
- "Atlas CMMS API" credential has valid token
- Token not expired

**Fix:**
- Re-generate CMMS API token
- Update credential in n8n
- Check CMMS API endpoint (try curl manually)

---

### Issue: Tavily Search Returns No Results

**Check:**
- Tavily API key valid
- Search quota not exceeded (1000/month on free tier)
- Manufacturer/model extracted correctly

**Fix:**
- Upgrade Tavily plan if quota exceeded
- Manually test search: `curl -X POST https://api.tavily.com/search -H "Authorization: Bearer KEY" -d '{"query":"Siemens S7-1200 manual"}'`
- Adjust search query in node if needed

---

### Issue: Parse OCR Response Returns "Unknown"

**Check:**
- Gemini response structure changed
- Photo quality too poor
- Equipment nameplate not in English

**Fix:**
- Update regex patterns in Code node
- Improve prompt in Gemini OCR node
- Add language detection logic

---

### Issue: Workflow Takes Too Long

**Optimization:**
- Reduce Tavily `max_results` from 10 to 5
- Skip deep search for common equipment
- Cache manual URLs in separate database

---

## 7. Advanced Configuration

### Add Logging

Insert HTTP Request node after each major step:

```json
{
  "method": "POST",
  "url": "{{ $vars.LOGGING_WEBHOOK }}",
  "body": {
    "step": "ocr_complete",
    "data": "{{ $json }}",
    "timestamp": "{{ new Date().toISOString() }}"
  }
}
```

### Add Error Notifications

Use n8n error workflow to notify admin on failures:

1. Settings → Error Workflow
2. Create workflow: Error Trigger → Telegram Send (to admin)

### Parallel Search

Instead of Quick → Deep sequential:
- Run Quick and Deep searches in parallel
- Use Merge node to combine results
- Return first successful result

### Manual Caching

Add database node after successful manual find:
- Store: manufacturer, model → manual_url
- Check cache before Tavily search
- Reduce API calls, faster responses

---

## 8. Production Checklist

Before going live:

- [ ] All credentials configured
- [ ] Variables set correctly
- [ ] Tested with 10+ different photos
- [ ] Verified CMMS integration working
- [ ] Tested low confidence path
- [ ] Tested manual not found path
- [ ] Error workflow configured
- [ ] Rate limits understood (Tavily, Gemini)
- [ ] Bot commands documented for users
- [ ] Monitoring/logging enabled

---

**Configuration Complete!** 🎉

Your RIVET Pro workflow is now ready for production use.

**Next Steps:**
1. Test with real equipment photos from your facility
2. Monitor first 100 executions for errors
3. Adjust confidence threshold if needed (current: 70%)
4. Add more response variations based on user feedback

---

**Support:**
- n8n Docs: https://docs.n8n.io
- Gemini API: https://ai.google.dev/docs
- Tavily API: https://docs.tavily.com
- Telegram Bot API: https://core.telegram.org/bots/api
