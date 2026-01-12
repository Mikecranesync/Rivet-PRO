# n8n Manual Hunter Integration Guide

**Date:** 2026-01-12
**Author:** Ralph
**Purpose:** Wire Manual Hunter workflow into Rivet Pro bot for automatic manual delivery

---

## Overview

This guide explains how to connect the n8n **Manual Hunter** workflow to the Rivet Pro Telegram bot so that equipment photos automatically return PDF manual links.

**What we're connecting:**
- **Rivet Pro Bot** → Sends manufacturer + model to n8n
- **n8n Manual Hunter** → Searches for manual PDF using Tavily API
- **Response** → Manual URL sent back to bot → Displayed to user

---

## Prerequisites

Before starting, ensure you have:

1. **n8n instance running** (local or cloud)
2. **Tavily API key** (for web search) - [Get one free at tavily.com](https://tavily.com)
3. **Manual Hunter workflow imported** to n8n
4. **Rivet Pro bot deployed** on VPS

---

## Step 1: Import Manual Hunter Workflow to n8n

### Option A: Find Existing Workflow

If Manual Hunter already exists in your n8n instance:

1. Open n8n interface: `http://localhost:5678` or your n8n URL
2. Search workflows for "Manual Hunter"
3. Note the webhook URL (should look like `/webhook/manual-hunter`)
4. Skip to Step 2

### Option B: Create New Manual Hunter Workflow

If starting from scratch:

1. In n8n, click **"New Workflow"**
2. Name it: `Manual Hunter - Rivet Pro`
3. Add nodes as described below

---

## Step 2: Manual Hunter Workflow Structure

The workflow should have these nodes:

```
Webhook (Trigger)
    ↓
Tavily Search (HTTP Request)
    ↓
Parse Results (Code/Function)
    ↓
Respond to Webhook
```

### Node Configuration

#### 1. Webhook Node (Trigger)

- **Type:** Webhook
- **HTTP Method:** POST
- **Path:** `manual-hunter`
- **Response Mode:** "Respond When Last Node Finishes"

**Expected Input:**
```json
{
  "manufacturer": "Siemens",
  "model": "G120 VFD",
  "query": "Siemens G120 VFD manual PDF"
}
```

#### 2. Tavily Search Node

- **Type:** HTTP Request
- **Method:** POST
- **URL:** `https://api.tavily.com/search`
- **Authentication:** None (API key in body)

**Headers:**
```json
{
  "Content-Type": "application/json"
}
```

**Body:**
```json
{
  "api_key": "{{ $credentials.tavilyApi.apiKey }}",
  "query": "{{ $json.query }} filetype:pdf",
  "search_depth": "advanced",
  "max_results": 5,
  "include_domains": [
    "manualslib.com",
    "siemens.com",
    "abb.com",
    "rockwellautomation.com",
    "schneider-electric.com"
  ]
}
```

#### 3. Parse Results Node (Code)

- **Type:** Code (JavaScript)
- **Mode:** Run Once for All Items

**Code:**
```javascript
// Extract first PDF result from Tavily response
const results = items[0].json.results || [];

for (const result of results) {
  // Check if URL ends with .pdf or contains "manual"
  const url = result.url;
  const isPDF = url.toLowerCase().endsWith('.pdf') ||
                url.toLowerCase().includes('manual');

  if (isPDF) {
    return [{
      json: {
        found: true,
        url: url,
        title: result.title || 'Equipment Manual',
        source: 'tavily'
      }
    }];
  }
}

// No manual found
return [{
  json: {
    found: false,
    url: null,
    title: null,
    source: 'tavily'
  }
}];
```

#### 4. Respond to Webhook

- **Type:** Respond to Webhook
- **Response Body:** `{{ $json }}`

Expected response format:
```json
{
  "found": true,
  "url": "https://example.com/manual.pdf",
  "title": "Siemens G120 Operating Instructions",
  "source": "tavily"
}
```

---

## Step 3: Configure Tavily Credentials in n8n

1. In n8n, go to **Settings** → **Credentials**
2. Click **"Add Credential"**
3. Search for "HTTP" or create **"API Key"** credential
4. Name it: `Tavily API`
5. Add your Tavily API key
6. Save

---

## Step 4: Test Manual Hunter Workflow

### Test from n8n UI

1. Open Manual Hunter workflow
2. Click **"Execute Workflow"** (or use "Test Workflow" button)
3. Manually trigger with test data:
   ```json
   {
     "manufacturer": "Siemens",
     "model": "G120",
     "query": "Siemens G120 manual PDF"
   }
   ```
4. Verify response contains:
   - `found: true`
   - `url: <valid PDF URL>`

### Test from Command Line

```bash
curl -X POST http://localhost:5678/webhook/manual-hunter \
  -H "Content-Type: application/json" \
  -d '{
    "manufacturer": "Siemens",
    "model": "G120",
    "query": "Siemens G120 manual PDF"
  }'
```

**Expected Response:**
```json
{
  "found": true,
  "url": "https://support.industry.siemens.com/...",
  "title": "Siemens SINAMICS G120 Operating Instructions",
  "source": "tavily"
}
```

---

## Step 5: Update Rivet Pro Configuration

On your VPS where Rivet Pro is deployed:

1. SSH into VPS:
   ```bash
   ssh root@72.60.175.144
   ```

2. Edit `.env` file:
   ```bash
   cd /opt/Rivet-PRO/rivet_pro
   nano .env
   ```

3. Add Manual Hunter webhook URL:
   ```bash
   # If n8n is on the same server
   N8N_MANUAL_HUNTER_URL=http://localhost:5678/webhook/manual-hunter

   # If n8n is on a different server or cloud
   N8N_MANUAL_HUNTER_URL=https://your-n8n-instance.com/webhook/manual-hunter
   ```

4. Save and exit: `Ctrl+X`, then `Y`, then `Enter`

---

## Step 6: Run Database Migration

The manual cache table needs to be created:

```bash
cd /opt/Rivet-PRO
python rivet_pro/run_migrations.py
```

**Expected output:**
```
Running migration: 013_manual_cache.sql
✓ Migration 013 applied successfully
```

---

## Step 7: Restart Rivet Pro Bot

```bash
systemctl restart rivet-bot
systemctl status rivet-bot
```

**Check logs:**
```bash
journalctl -u rivet-bot -f --no-pager
```

Look for:
```
INFO | Database and services initialized
INFO | Manual service initialized
```

---

## Step 8: End-to-End Test

### Test the Full Flow

1. Open Telegram and find your bot: `@RivetCMMS_bot`
2. Send `/start` if not already started
3. Send a photo of equipment nameplate (or use a test image)
4. Bot should respond with:
   ```
   📋 Equipment Identified

   Manufacturer: Siemens
   Model: G120 VFD

   📖 User Manual
   [Siemens G120 Operating Instructions](https://...)

   💡 Bookmark this for offline access.
   ```

### If Manual Found:
- ✅ Verify link is clickable
- ✅ Verify link opens a PDF
- ✅ Check bot logs: `Manual found | cached=false`
- ✅ Send same photo again: `Manual found | cached=true` (instant)

### If Manual NOT Found:
```
📋 Equipment Identified

Manufacturer: UnknownBrand
Model: XYZ-500

📖 Manual Not Found

Try searching: UnknownBrand XYZ-500 manual PDF

_Send a clearer photo if the ID looks wrong._
```

---

## Troubleshooting

### Issue: "Manual search failed"

**Check 1: n8n webhook URL is correct**
```bash
# From VPS
curl http://localhost:5678/webhook/manual-hunter

# Should NOT return 404
```

**Check 2: n8n workflow is active**
- Open n8n UI
- Manual Hunter workflow should show "Active" status
- If inactive, click "Activate" button

**Check 3: Tavily API key is valid**
- Test directly: https://tavily.com/dashboard
- Check n8n credential is saved correctly

### Issue: "Connection timeout"

**Cause:** n8n is not responding within 15 seconds

**Solution:**
- Increase timeout in bot code (currently 15s)
- Optimize Tavily search (reduce `max_results`)
- Check n8n server resources

### Issue: "Manual URL is broken"

**Cause:** Tavily returned a link that's not a direct PDF

**Solution:**
- Update Parse Results node to validate URLs
- Add fallback domains in Tavily `include_domains`
- Consider caching verified URLs only

---

## Performance Expectations

| Metric | Target | Notes |
|--------|--------|-------|
| Cache hit response | < 500ms | Direct database lookup |
| Cache miss (new search) | 5-15s | Tavily API + caching |
| Cache hit rate (after 1 week) | > 60% | Depends on equipment variety |
| Manual found rate | ~70% | Common industrial equipment |

---

## Monitoring

### Check Cache Statistics

Run this SQL query in your database:

```sql
SELECT
    COUNT(*) as total_cached,
    COUNT(*) FILTER (WHERE manual_url IS NOT NULL) as manuals_found,
    SUM(access_count) as total_accesses,
    AVG(access_count) as avg_accesses_per_manual
FROM manual_cache;
```

### Check Recent Manual Searches

```sql
SELECT
    manufacturer,
    model,
    manual_url IS NOT NULL as found,
    access_count,
    found_at
FROM manual_cache
ORDER BY found_at DESC
LIMIT 20;
```

---

## Next Steps

After successful integration:

1. **Monitor for 1 week**
   - Track cache hit rate
   - Verify manual URLs are working
   - Check user feedback

2. **Tune Tavily search**
   - Add more trusted domains
   - Adjust search parameters
   - Filter out broken links

3. **Add manual verification**
   - Allow users to report broken links
   - Implement URL verification service
   - Update `verified` flag in cache

---

## Support

If you encounter issues:

1. Check bot logs: `journalctl -u rivet-bot -f`
2. Check n8n execution logs (in n8n UI → Executions)
3. Verify database connection: `psql <DATABASE_URL>`
4. Test Manual Hunter directly with curl (see Step 4)

---

## Summary

✅ **What We Did:**
- Connected Rivet Pro bot to n8n Manual Hunter webhook
- Integrated manual search into photo processing flow
- Added database caching for fast repeat lookups
- Formatted beautiful responses with clickable manual links

✅ **What Happens Now:**
- User sends photo → Bot identifies equipment
- Bot searches for manual (n8n + Tavily)
- Manual URL delivered in < 15 seconds
- Future lookups instant (cache hit)

🚀 **Result:** "Shazam for Equipment" is complete!
