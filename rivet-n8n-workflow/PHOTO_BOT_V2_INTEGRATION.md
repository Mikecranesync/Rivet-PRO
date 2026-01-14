# Photo Bot V2 ↔ Manual Hunter Integration Guide

**Integration Method**: Webhook Call
**Photo Bot V2 Workflow ID**: 7LMKcMmldZsu1l6g
**Manual Hunter Workflow**: RIVET Pro - Photo to Manual
**Integration Point**: After Gemini Vision analysis completes

---

## Overview

This guide explains how to integrate **Photo Bot V2** (Telegram photo analysis bot) with **Manual Hunter** (equipment manual finder) so that when a user sends an equipment photo, the bot:

1. Analyzes the photo with Gemini Vision ✅ (existing)
2. Extracts manufacturer + model ✅ (existing)
3. **Calls Manual Hunter** to find the manual (NEW)
4. **Sends manual link** to user (NEW)

---

## Architecture

### Current Photo Bot V2 Flow

```
User sends photo → Telegram Webhook
                    ↓
              Download Photo
                    ↓
           Gemini Vision Analysis
                    ↓
             Format Response
                    ↓
         Telegram Send Analysis
                    ↓
                  [END]
```

### Enhanced Flow with Manual Hunter

```
User sends photo → Telegram Webhook
                    ↓
              Download Photo
                    ↓
           Gemini Vision Analysis
                    ↓
             Extract Manufacturer/Model ← NEW
                    ↓
        Call Manual Hunter Webhook ← NEW
                    ↓
         Parse Manual Hunter Response ← NEW
                    ↓
         Telegram Send Analysis + Manual ← ENHANCED
                    ↓
                  [END]
```

---

## Prerequisites

1. **Photo Bot V2 workflow** is imported and activated
   - Workflow ID: 7LMKcMmldZsu1l6g
   - URL: http://72.60.175.144:5678/workflow/7LMKcMmldZsu1l6g
2. **Manual Hunter workflow** is imported and activated
   - Webhook URL: http://72.60.175.144:5678/webhook-test/rivet-manual-hunter
3. **Gemini credential** is configured in Photo Bot V2 (currently pending)

---

## Step 1: Open Photo Bot V2 Workflow

1. Go to n8n: http://72.60.175.144:5678
2. Click **"Workflows"** in sidebar
3. Find workflow **"RIVET Photo Bot v2"** (ID: 7LMKcMmldZsu1l6g)
4. Click to open in editor

You should see 10 nodes:
- Webhook Trigger
- Extract Data (Code)
- Has Photo? (IF)
- Telegram Download File
- **Gemini Vision Analysis** (HTTP Request)
- **Format Response** (Code)
- Telegram Send Analysis
- Telegram Send Help
- Respond to Webhook (×2)

---

## Step 2: Add "Extract Equipment Info" Code Node

**Purpose**: Extract manufacturer and model from Gemini's analysis for Manual Hunter

**Location**: After **"Format Response"** node, before **"Telegram Send Analysis"**

### Add the Node

1. Click **"+"** button after **"Format Response"** node
2. Search for **"Code"**
3. Click **"Code"** node
4. Name it: **"Extract Equipment Info"**

### Configure the Node

**Mode**: Run Once for Each Item

**JavaScript Code**:
```javascript
// Extract manufacturer and model from Gemini analysis
const geminiResponse = $input.item.json;
const analysisText = geminiResponse.formatted_analysis || geminiResponse.analysis || '';

// Try to extract manufacturer and model from analysis text
let manufacturer = 'Unknown';
let model = 'Unknown';

// Pattern 1: "Manufacturer: XXX"
const mfgMatch = analysisText.match(/Manufacturer[:\s]+([A-Za-z0-9\s&.-]+)/i);
if (mfgMatch) {
  manufacturer = mfgMatch[1].trim();
}

// Pattern 2: "Model: XXX" or "Model Number: XXX"
const modelMatch = analysisText.match(/Model(?:\s+Number)?[:\s]+([A-Za-z0-9\s\/-]+)/i);
if (modelMatch) {
  model = modelMatch[1].trim();
}

// Pattern 3: First line often contains "Brand Model"
const firstLine = analysisText.split('\n')[0];
const parts = firstLine.split(/\s+/);
if (parts.length >= 2 && manufacturer === 'Unknown') {
  manufacturer = parts[0];
  model = parts.slice(1).join(' ');
}

// Get chat_id from original webhook
const chatId = $('Extract Data').item.json.chat_id;

return {
  json: {
    ...geminiResponse,
    manufacturer: manufacturer,
    model: model,
    chat_id: chatId,
    original_analysis: analysisText
  }
};
```

**What it does**:
- Parses Gemini's analysis text
- Extracts manufacturer and model using regex patterns
- Passes data to next node

### Connect the Node

1. Disconnect **"Format Response"** → **"Telegram Send Analysis"**
2. Connect **"Format Response"** → **"Extract Equipment Info"**
3. Connect **"Extract Equipment Info"** → (new node below)

---

## Step 3: Add "Call Manual Hunter" HTTP Request Node

**Purpose**: Send manufacturer + model to Manual Hunter workflow

**Location**: After **"Extract Equipment Info"**

### Add the Node

1. Click **"+"** after **"Extract Equipment Info"**
2. Search for **"HTTP Request"**
3. Click **"HTTP Request"**
4. Name it: **"Call Manual Hunter"**

### Configure the Node

**Method**: POST

**URL**:
```
http://72.60.175.144:5678/webhook-test/rivet-manual-hunter
```

**Authentication**: None (internal webhook)

**Send Body**: Yes

**Body Content Type**: JSON

**JSON Body**:
```json
={
  "message": {
    "chat": {
      "id": {{ $json.chat_id }}
    },
    "photo": [
      {
        "file_id": "from_photo_bot_v2"
      }
    ],
    "from": {
      "id": {{ $json.chat_id }},
      "first_name": "PhotoBot"
    }
  },
  "manufacturer": "{{ $json.manufacturer }}",
  "model": "{{ $json.model }}"
}
```

**Options**:
- **Timeout**: 60000 (60 seconds) - allows all 3 search tiers to execute
- **Ignore SSL Issues**: False

**What it does**:
- Calls Manual Hunter webhook
- Sends manufacturer + model in Telegram update format
- Waits up to 60 seconds for response (all 3 tiers can complete)

### Connect the Node

1. Connect **"Extract Equipment Info"** → **"Call Manual Hunter"**
2. Connect **"Call Manual Hunter"** → (new node below)

---

## Step 4: Add "Parse Manual Result" Code Node

**Purpose**: Extract manual URL from Manual Hunter response

**Location**: After **"Call Manual Hunter"**

### Add the Node

1. Click **"+"** after **"Call Manual Hunter"**
2. Search for **"Code"**
3. Click **"Code"**
4. Name it: **"Parse Manual Result"**

### Configure the Node

**Mode**: Run Once for Each Item

**JavaScript Code**:
```javascript
// Parse Manual Hunter response
const response = $input.item.json;

// Manual Hunter returns Telegram message sent to user
// We need to extract the manual URL from the response

let manualFound = false;
let manualUrl = null;
let searchTier = 'none';
let message = response.message || '';

// Check if manual was found (look for "Manual Found" or PDF link)
if (message.includes('Manual Found') || message.includes('Download Manual')) {
  manualFound = true;

  // Extract URL from markdown link: [Download Manual](URL)
  const urlMatch = message.match(/\[Download Manual\]\(([^)]+)\)/);
  if (urlMatch) {
    manualUrl = urlMatch[1];
  }

  // Determine which tier found it
  if (message.includes('(AI Search)')) {
    searchTier = 'groq';
  } else if (message.includes('(Deep Search)')) {
    searchTier = 'tavily_deep';
  } else {
    searchTier = 'tavily_quick';
  }
}

// Get previous node data
const equipmentInfo = $('Extract Equipment Info').item.json;

return {
  json: {
    manual_found: manualFound,
    manual_url: manualUrl,
    search_tier: searchTier,
    manufacturer: equipmentInfo.manufacturer,
    model: equipmentInfo.model,
    chat_id: equipmentInfo.chat_id,
    original_analysis: equipmentInfo.original_analysis,
    manual_hunter_response: message
  }
};
```

**What it does**:
- Parses Manual Hunter's Telegram response
- Extracts PDF URL if found
- Determines which search tier succeeded
- Passes combined data to next node

### Connect the Node

1. Connect **"Call Manual Hunter"** → **"Parse Manual Result"**
2. Connect **"Parse Manual Result"** → **"Send Combined Result"** (new node below)

---

## Step 5: Modify "Telegram Send Analysis" Node

**Purpose**: Send both Gemini analysis AND manual link (if found)

### Update Existing Node

1. Click on **"Telegram Send Analysis"** node
2. **Rename it** to: **"Send Combined Result"**
3. Update the **Message Text**:

**New Message Text**:
```
=📸 Equipment Analysis:

{{ $('Extract Equipment Info').item.json.original_analysis }}

---

{{ $json.manual_found ?
  '📋 **Manual Found!**\n\n📥 [Download PDF Manual](' + $json.manual_url + ')\n\n_Found via ' + ($json.search_tier === 'groq' ? 'AI search (Tier 3)' : $json.search_tier === 'tavily_deep' ? 'deep search (Tier 2)' : 'quick search (Tier 1)') + '_'
  :
  '⚠️ Manual not available. Check manufacturer support site or contact support.'
}}
```

**Parse Mode**: Markdown (ensure this is selected)

**What it does**:
- Shows Gemini's equipment analysis
- If manual found: Shows download link with search tier info
- If not found: Shows helpful message

### Connect the Node

1. Connect **"Parse Manual Result"** → **"Send Combined Result"**
2. Connect **"Send Combined Result"** → **"Respond to Webhook"**

---

## Step 6: Update Connections

**Old flow**:
```
Format Response → Telegram Send Analysis → Respond to Webhook
```

**New flow**:
```
Format Response → Extract Equipment Info → Call Manual Hunter → Parse Manual Result → Send Combined Result → Respond to Webhook
```

**Ensure**:
- ✅ All new nodes are connected in sequence
- ✅ "Send Combined Result" connects to "Respond to Webhook"
- ✅ No broken connections (red lines)

---

## Step 7: Save and Activate

1. Click **"Save"** (Ctrl+S)
2. Ensure workflow is **"Active"** (toggle top-right)
3. Verify no errors in nodes

---

## Step 8: Test the Integration

### Test 1: Send Equipment Photo

1. Open Telegram
2. Message your Photo Bot V2: @rivet_local_dev_bot
3. Send a clear photo of equipment nameplate (e.g., Siemens PLC)
4. Wait 10-30 seconds

**Expected response**:
```
📸 Equipment Analysis:

This is a Siemens S7-1200 Programmable Logic Controller (PLC).
The model number is CPU 1214C.
Serial number: 6ES7214-1AG40-0XB0.
No visible errors or faults.

---

📋 Manual Found!

📥 [Download PDF Manual](https://support.siemens.com/cs/document/...)

Found via quick search (Tier 1)
```

### Test 2: Send Rare Equipment Photo

1. Send photo of uncommon/discontinued equipment
2. Wait 30-40 seconds (all 3 tiers may execute)

**Expected response**:
```
📸 Equipment Analysis:

[Gemini's analysis...]

---

📋 Manual Found!

📥 [Download PDF Manual](https://...)

Found via AI search (Tier 3)
```

### Test 3: Monitor Execution

1. Go to n8n: **Workflows** → **RIVET Photo Bot v2** → **Executions**
2. Click on latest execution
3. Verify:
   - ✅ All nodes executed successfully (green)
   - ✅ "Call Manual Hunter" node shows HTTP 200 response
   - ✅ "Parse Manual Result" extracted URL correctly
   - ✅ User received combined message

### Test 4: Check Manual Hunter Execution

1. Go to **Workflows** → **RIVET Pro - Photo to Manual** → **Executions**
2. Verify:
   - ✅ Workflow was triggered by Photo Bot V2
   - ✅ Search tiers executed (Quick → Deep → Groq if needed)
   - ✅ Manual found or "Not Found" message sent

---

## Troubleshooting

### Issue: Manual Hunter webhook returns 404

**Cause**: Manual Hunter workflow not activated or wrong webhook URL

**Fix**:
1. Go to **Workflows** → **RIVET Pro - Photo to Manual**
2. Ensure workflow is **Active**
3. Open **"Telegram Photo Received"** node
4. Copy the **Webhook URL** from "Webhook URLs" section
5. Update Photo Bot V2's **"Call Manual Hunter"** node with correct URL

### Issue: Timeout error after 60 seconds

**Cause**: All 3 search tiers executing (rare equipment)

**Fix**:
- Increase timeout in **"Call Manual Hunter"** node:
  - **Options** → **Timeout** → `90000` (90 seconds)
- Or handle timeout gracefully:
  ```javascript
  // In "Parse Manual Result" node
  if ($input.item.json.error && $input.item.json.error.includes('timeout')) {
    return {
      json: {
        manual_found: false,
        manual_url: null,
        timeout: true,
        message: 'Manual search timed out. Please try again.'
      }
    };
  }
  ```

### Issue: Manual URL not extracted

**Cause**: Manual Hunter response format changed

**Debug**:
1. Check **"Parse Manual Result"** node output
2. Look at `manual_hunter_response` field
3. Update regex in **"Parse Manual Result"** if needed:
   ```javascript
   // Try multiple patterns
   const urlMatch = message.match(/\[Download Manual\]\(([^)]+)\)/) ||
                    message.match(/https?:\/\/[^\s\)]+\.pdf/i);
   ```

### Issue: Manufacturer/Model not extracted from Gemini analysis

**Cause**: Gemini's response format varies

**Fix**:
1. Check **"Extract Equipment Info"** node output
2. If manufacturer/model are "Unknown", update extraction logic:
   ```javascript
   // Add more patterns
   const patterns = [
     /Manufacturer[:\s]+([A-Za-z0-9\s&.-]+)/i,
     /Brand[:\s]+([A-Za-z0-9\s&.-]+)/i,
     /Make[:\s]+([A-Za-z0-9\s&.-]+)/i
   ];

   for (const pattern of patterns) {
     const match = analysisText.match(pattern);
     if (match) {
       manufacturer = match[1].trim();
       break;
     }
   }
   ```

### Issue: Manual Hunter called even for non-equipment photos

**Solution**: Add confidence check before calling Manual Hunter

1. Add **IF node** after **"Extract Equipment Info"**:
   - **Name**: "Is Equipment?"
   - **Condition**: `{{ $json.manufacturer !== 'Unknown' && $json.model !== 'Unknown' }}`
   - **TRUE** → Call Manual Hunter
   - **FALSE** → Skip to Send Combined Result

---

## Optional Enhancements

### Enhancement 1: Add "Find Manual" Button

Instead of automatically calling Manual Hunter, add an inline button:

1. Update **"Send Combined Result"** node:
   ```json
   {
     "chatId": "={{ $json.chat_id }}",
     "text": "={{ $json.original_analysis }}",
     "additionalFields": {
       "reply_markup": {
         "inline_keyboard": [
           [
             {
               "text": "📋 Find Manual",
               "callback_data": "find_manual"
             }
           ]
         ]
       }
     }
   }
   ```

2. Add **Telegram Trigger** for callback queries:
   - **Updates**: `callback_query`
   - When user clicks "Find Manual" → Call Manual Hunter

### Enhancement 2: Cache Manual Results

Add database caching to avoid re-searching for same equipment:

1. Before calling Manual Hunter, check cache:
   ```sql
   SELECT manual_url FROM manuals
   WHERE manufacturer = '{{ $json.manufacturer }}'
   AND model = '{{ $json.model }}'
   ```

2. If cached → Use cached URL
3. If not cached → Call Manual Hunter → Save result to cache

### Enhancement 3: Manual Request Queue

If manual not found, save to human review queue:

1. After Manual Hunter returns "Not Found"
2. Save request to database:
   ```sql
   INSERT INTO manual_requests (manufacturer, model, chat_id, photo_url)
   VALUES ('{{ $json.manufacturer }}', '{{ $json.model }}', {{ $json.chat_id }}, '{{ $json.photo_url }}')
   ```

3. Notify admin channel:
   ```
   New manual request:
   Equipment: Siemens S7-1200
   Requested by: User #123456789
   [Approve] [Reject]
   ```

---

## Webhook Payload Reference

### Photo Bot V2 → Manual Hunter

**Method**: POST
**URL**: `http://72.60.175.144:5678/webhook-test/rivet-manual-hunter`

**Payload**:
```json
{
  "message": {
    "chat": {
      "id": 123456789
    },
    "photo": [
      {
        "file_id": "from_photo_bot_v2"
      }
    ],
    "from": {
      "id": 123456789,
      "first_name": "PhotoBot"
    }
  },
  "manufacturer": "Siemens",
  "model": "S7-1200"
}
```

### Manual Hunter → Photo Bot V2

**Response** (if manual found):
```json
{
  "ok": true,
  "message": "📋 **Manual Found!**\n\n**Equipment:** Siemens S7-1200\n**Serial:** 6ES7214\n\n📥 [Download Manual](https://support.siemens.com/...)\n\n✅ _Asset saved to CMMS_"
}
```

**Response** (if not found):
```json
{
  "ok": true,
  "message": "⚠️ **Manual Not Found**\n\n**Equipment:** Siemens S7-1200\n**Serial:** 6ES7214\n\nI couldn't find a PDF manual automatically..."
}
```

---

## Node Summary

**New nodes added to Photo Bot V2** (4 total):

| Node | Type | Purpose |
|------|------|---------|
| Extract Equipment Info | Code | Parse Gemini analysis for manufacturer/model |
| Call Manual Hunter | HTTP Request | Webhook call to Manual Hunter |
| Parse Manual Result | Code | Extract PDF URL from Manual Hunter response |
| Send Combined Result | Telegram | Send analysis + manual link |

**Total nodes in enhanced Photo Bot V2**: 14 (10 original + 4 new)

---

## Testing Checklist

- [ ] Photo Bot V2 workflow activated
- [ ] Manual Hunter workflow activated
- [ ] All 4 new nodes added
- [ ] Connections updated correctly
- [ ] Test 1: Common equipment → Tier 1 manual found
- [ ] Test 2: Uncommon equipment → Tier 2 or 3 manual found
- [ ] Test 3: Rare equipment → All tiers execute
- [ ] Test 4: Execution logs show successful integration
- [ ] Test 5: User receives combined analysis + manual

---

## Next Steps

1. ✅ Complete this integration
2. 📋 Run full test suite (see testing plan in project plan file)
3. 🚀 Deploy to production with HTTPS webhook
4. 📊 Monitor usage and optimize search tiers
5. 💾 Add caching for repeated manual requests

---

## Support

**Photo Bot V2**: http://72.60.175.144:5678/workflow/7LMKcMmldZsu1l6g
**Manual Hunter**: http://72.60.175.144:5678/workflow/[WORKFLOW_ID]
**Setup Guide**: `MANUAL_HUNTER_SETUP.md`
**Technical Spec**: `GROQ_SEARCH_IMPLEMENTATION.md`

**Last Updated**: 2026-01-09
