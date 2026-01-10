# Photo Bot V2 → Manual Hunter Integration Guide

## Overview
This guide shows you how to integrate the Manual Hunter workflow with your existing Photo Bot V2 (workflow ID: `7LMKcMmldZsu1l6g`) in n8n cloud.

## Integration Summary

**What we're adding**:
1. "Searching for manual..." message after OCR analysis
2. HTTP webhook call to trigger Manual Hunter
3. Pass equipment data to Manual Hunter
4. Manual Hunter sends Telegram response directly (no callback needed)

**Where to add**:
- After Gemini OCR analysis node
- Before workflow termination
- Position: Between OCR results and end of workflow

---

## Prerequisites

- [ ] Manual Hunter workflow imported and activated
- [ ] All API credentials configured (see `MANUAL_HUNTER_SETUP.md`)
- [ ] Database tables created (`manual_hunter_tables.sql`)
- [ ] Admin access to Photo Bot V2 workflow in n8n cloud

---

## Step-by-Step Integration

### Step 1: Open Photo Bot V2 Workflow

1. Log into your n8n cloud instance
2. Go to **Workflows** tab
3. Find: **RIVET Pro - Photo Bot V2** (ID: `7LMKcMmldZsu1l6g`)
4. Click to open workflow editor

### Step 2: Locate the Insertion Point

**Find the node** that sends the OCR analysis results to the user. This is typically:
- Node name: `Send OCR Results` or `Send Equipment Info`
- Node type: Telegram (Send Message)
- Position: After Gemini OCR / Vision analysis

**Visual Reference**:
```
Telegram Trigger (Photo)
  ↓
Get Photo File
  ↓
Gemini Vision Analysis
  ↓
Parse OCR Results
  ↓
Send OCR Results  ← WE INSERT AFTER THIS NODE
  ↓
[Workflow ends]
```

### Step 3: Add "Searching Manual" Message Node

**Insert a new Telegram node**:

1. Click the **+** button after "Send OCR Results" node
2. Search for: **Telegram**
3. Select: **Telegram**
4. Configure the node:

**Node Configuration**:
```yaml
Node Name: Send Searching Manual
Type: n8n-nodes-base.telegram
Credential: Telegram Bot (if4EOJbvMirfWqCC)

Parameters:
  Resource: message
  Operation: sendMessage

  Chat ID: ={{ $('Telegram Trigger (Photo)').item.json.message.chat.id }}

  Text: |
    ✅ Equipment identified!

    I'm now searching for your user manual...

    This may take 10-30 seconds depending on availability.

  Additional Fields:
    Parse Mode: Markdown
    Reply to Message ID: ={{ $('Telegram Trigger (Photo)').item.json.message.message_id }}
```

**Position**: Place this node directly after "Send OCR Results"

### Step 4: Add Manual Hunter Trigger Node

**Insert HTTP Request node**:

1. Click the **+** button after "Send Searching Manual" node
2. Search for: **HTTP Request**
3. Select: **HTTP Request**
4. Configure the node:

**Node Configuration**:
```yaml
Node Name: Trigger Manual Hunter
Type: n8n-nodes-base.httpRequest

Parameters:
  Method: POST

  URL:
    Production: https://[your-n8n-instance].app.n8n.cloud/webhook/rivet-manual-hunter
    OR
    Test: http://72.60.175.144:5678/webhook/rivet-manual-hunter

  Authentication: None

  Send Body: true
  Body Content Type: application/json

  Body (JSON):
    ={{ JSON.stringify({
      chat_id: $('Telegram Trigger (Photo)').item.json.message.chat.id,
      original_message_id: $('Telegram Trigger (Photo)').item.json.message.message_id,
      manufacturer: $('Parse OCR Results').item.json.manufacturer,
      model_number: $('Parse OCR Results').item.json.model_number,
      product_family: $('Parse OCR Results').item.json.product_family,
      full_ocr_text: $('Parse OCR Results').item.json.full_text
    }) }}

  Options:
    Timeout: 90000  (90 seconds - allows for all 3 tiers)
    Ignore Response Code: false
```

**Important Notes**:
- Replace `[your-n8n-instance]` with your actual n8n cloud instance URL
- Adjust node name references if your Photo Bot V2 uses different names:
  - `Telegram Trigger (Photo)` → Your trigger node name
  - `Parse OCR Results` → Your OCR parsing node name

**Position**: Place this node directly after "Send Searching Manual"

### Step 5: Update Workflow Connections

**Before Integration**:
```
Send OCR Results → [End]
```

**After Integration**:
```
Send OCR Results → Send Searching Manual → Trigger Manual Hunter → [End]
```

**How to connect**:
1. Delete the old connection from "Send OCR Results" to workflow end
2. Drag connection from "Send OCR Results" → "Send Searching Manual"
3. Drag connection from "Send Searching Manual" → "Trigger Manual Hunter"
4. "Trigger Manual Hunter" terminates (no output needed)

### Step 6: Handle Node Name Variations

**If your Photo Bot V2 uses different node names**, update references:

| Reference in Guide | Your Actual Node Name | Update In |
|--------------------|----------------------|-----------|
| `Telegram Trigger (Photo)` | `Webhook Trigger` or `Photo Trigger` | Both new nodes |
| `Parse OCR Results` | `Extract Equipment Data` or `Gemini Output` | HTTP Request body |
| `Send OCR Results` | `Send Identification` or `Reply to User` | Connection point |

**To find node names**:
1. Click on any node in Photo Bot V2
2. Look at the top of the node panel for the node name
3. Update expressions accordingly

### Step 7: Save and Test

1. Click **Save** (top right) to save workflow changes
2. **Activate** Photo Bot V2 if not already active
3. Test the integration (see Testing section below)

---

## Testing the Integration

### Test Scenario 1: End-to-End Photo Upload

1. **Send test photo** to Telegram bot:
   - Take a photo of equipment nameplate
   - OR use test image with visible manufacturer/model

2. **Expected flow**:
   ```
   User sends photo
     ↓
   Bot: "Processing your image..."
     ↓
   Bot: "Equipment identified: [Manufacturer] [Model]"
     ↓
   Bot: "I'm now searching for your user manual..."
     ↓
   (10-30 seconds pass - Manual Hunter runs)
     ↓
   Bot: "✅ Found your manual! [Download link]"
     OR
   Bot: "⚠️ Manual not found... queued for sourcing"
   ```

3. **Verify**:
   - All messages received in correct order
   - Download link works (opens PDF)
   - Manual matches equipment

### Test Scenario 2: Cache Hit (Repeat Lookup)

1. Send the **same equipment photo again**
2. **Expected**: Instant manual return from cache (<1 second)
3. **Message should say**: "💾 Cached result - instant retrieval!"

### Test Scenario 3: Manual Not Found

1. Send photo of obscure/rare equipment
2. **Expected**: Manual Hunter tries all 3 tiers, then queues
3. **Message should say**: "⚠️ Manual not found... queued for sourcing"

---

## Troubleshooting

### Issue: "Send Searching Manual" node fails

**Symptom**: Error about Telegram credential
**Solution**:
- Verify credential ID is `if4EOJbvMirfWqCC`
- Check credential name is exactly `Telegram Bot`
- Re-select credential in node config

### Issue: "Trigger Manual Hunter" times out

**Symptom**: HTTP request timeout after 90 seconds
**Possible Causes**:
1. Manual Hunter workflow not activated
2. Webhook URL incorrect
3. All 3 search tiers failed + Perplexity taking too long

**Solution**:
- Check Manual Hunter workflow is **Active** in n8n
- Verify webhook URL matches: `/webhook/rivet-manual-hunter`
- Check Manual Hunter execution logs for errors
- Consider reducing Perplexity timeout if installed

### Issue: No manual response received

**Symptom**: "Searching..." message sent, but no follow-up
**Debugging**:
1. Check Manual Hunter workflow execution logs
2. Look for failed API calls (Tavily, Groq, etc.)
3. Verify all credentials configured correctly
4. Check database connection (cache queries may fail)

**Common Fixes**:
- Configure missing API credentials
- Check API rate limits not exceeded
- Verify Neon PostgreSQL tables exist
- Check Telegram credential in Manual Hunter

### Issue: Wrong equipment data passed

**Symptom**: Manual Hunter searches for wrong manufacturer/model
**Solution**:
- Verify OCR parsing node extracts correct fields
- Check field names match:
  - `manufacturer` (not `mfr` or `brand`)
  - `model_number` (not `model` or `part_number`)
  - `product_family` (optional)
  - `full_text` or `full_ocr_text`
- Update HTTP Request body field names if needed

### Issue: Duplicate messages

**Symptom**: User receives multiple manual responses
**Solution**:
- Check Manual Hunter workflow not duplicated/activated twice
- Verify Photo Bot V2 only calls webhook once
- Check for race conditions in Telegram trigger

---

## Advanced Configuration

### Custom Timeout Adjustment

If your equipment requires longer search times:

**In "Trigger Manual Hunter" node**:
```yaml
Options:
  Timeout: 120000  # 2 minutes (default: 90000)
```

### Conditional Manual Search

Only search for manuals if OCR confidence is high:

**Add If node before "Send Searching Manual"**:
```yaml
Conditions:
  - Field: ={{ $('Parse OCR Results').item.json.confidence }}
  - Operator: Greater Than or Equal
  - Value: 0.80  # 80% confidence threshold
```

### Multi-Instance Support

If running multiple n8n instances:

**Update webhook URL to include instance identifier**:
```
Production: https://prod-n8n.app.n8n.cloud/webhook/rivet-manual-hunter
Staging: https://staging-n8n.app.n8n.cloud/webhook/rivet-manual-hunter
```

---

## Performance Metrics

### Expected Response Times

| Tier | Success Rate | Avg Response Time |
|------|--------------|-------------------|
| Cache Hit | 60%* | <1 second |
| Tier 1 (Tavily+Groq) | 80% | 5-10 seconds |
| Tier 2 (Serper+DeepSeek) | 15% | 15-20 seconds |
| Tier 3 (Perplexity) | 4% | 25-30 seconds |
| Human Queue | 1% | 3-5 seconds (to queue) |

*After initial lookups, cache hit rate increases over time

### Monitoring Recommendations

**Track in your analytics**:
- Manual search requests/day
- Cache hit rate
- Tier distribution (how often each tier is used)
- Average response time per tier
- Human queue size

**Set alerts for**:
- Cache hit rate < 50% (indicates caching issues)
- Tier 3 usage > 10% (API costs spiking)
- Human queue > 50 pending requests

---

## Photo Bot V2 Node Reference

**Expected node structure in Photo Bot V2**:

```yaml
# Your existing nodes (don't modify)
1. Telegram Trigger (Photo)
2. Get Photo File
3. Call Gemini Vision API
4. Parse OCR Results
5. Send OCR Results

# New nodes (add these)
6. Send Searching Manual       ← NEW
7. Trigger Manual Hunter        ← NEW

# Connection Flow
Telegram Trigger → Get Photo File → Gemini API → Parse OCR → Send OCR Results
                                                                  ↓
                                                        Send Searching Manual
                                                                  ↓
                                                        Trigger Manual Hunter
                                                                  ↓
                                                                [End]
```

---

## Rollback Instructions

If you need to remove Manual Hunter integration:

1. Open Photo Bot V2 workflow
2. Delete nodes:
   - "Send Searching Manual"
   - "Trigger Manual Hunter"
3. Reconnect "Send OCR Results" → workflow end
4. Save workflow
5. Manual Hunter workflow can remain active (harmless if not triggered)

---

## Next Steps

After successful integration:

1. ✅ Test with 5-10 different equipment photos
2. ✅ Monitor cache hit rate over first week
3. ✅ Review Manual Hunter execution logs for errors
4. ✅ Adjust confidence thresholds if needed
5. ✅ Train users on expected response times
6. ✅ Set up monitoring/alerts for queue size

---

## Integration Checklist

```
✅ Pre-Integration:
  ├─ Manual Hunter workflow imported ⬜
  ├─ API credentials configured ⬜
  ├─ Database tables created ⬜
  └─ Webhook URL identified ⬜

✅ Integration Steps:
  ├─ Opened Photo Bot V2 workflow ⬜
  ├─ Found insertion point after OCR ⬜
  ├─ Added "Send Searching Manual" node ⬜
  ├─ Added "Trigger Manual Hunter" node ⬜
  ├─ Connected nodes correctly ⬜
  └─ Saved workflow ⬜

✅ Testing:
  ├─ End-to-end photo upload test ⬜
  ├─ Cache hit test (repeat lookup) ⬜
  ├─ Verified manual download works ⬜
  └─ Tested obscure equipment (queue) ⬜

✅ Monitoring:
  ├─ Execution logs reviewed ⬜
  ├─ Performance metrics tracked ⬜
  └─ Alerts configured ⬜
```

---

**Document Version**: 1.0
**Last Updated**: 2026-01-09
**Photo Bot V2 Workflow ID**: `7LMKcMmldZsu1l6g`
**Manual Hunter Webhook**: `/webhook/rivet-manual-hunter`
