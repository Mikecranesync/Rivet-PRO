# Issue #1: Manual Hunter Workflow Stops at Cache Check

**Workflow:** TEST - RIVET - Manual Hunter (ID: HQgppQgX9H2yyQdN)
**Severity:** CRITICAL
**Status:** FAILED
**Discovered:** 2026-01-10 (E2E Testing)

## Problem Description

The Manual Hunter workflow stops execution after checking the cache and does not proceed to Tier 1 search when no cached result is found. This prevents the workflow from finding any equipment manuals.

## Expected Behavior

When a manual search request is received:
1. Extract manufacturer/model from request ✅
2. Check cache for existing manual ✅
3. **If cache miss:** Proceed to Tier 1: Tavily Search ❌ **FAILS HERE**
4. Evaluate results with Groq LLM
5. Validate URL quality
6. If Tier 1 fails, escalate to Tier 2: Serper Search
7. If all tiers fail, add to human queue

## Actual Behavior

Workflow execution stops after "Check Cache" node with empty results. Flow does not continue to search tiers.

## Reproduction

### Test Input
```json
{
  "make": "Caterpillar",
  "model": "D9T",
  "type": "bulldozer",
  "chat_id": 123456789
}
```

### Execution Trace (Execution ID: 6467)

```
Manual Hunter Webhook → SUCCESS (received data)
  ↓
Extract Webhook Data → SUCCESS (but manufacturer="", model_number="")
  ↓
Check Cache → SUCCESS (returned empty array [])
  ↓
[EXECUTION ENDS] ← Should continue to "Cache Hit?" and Tier 1
```

## Root Cause Analysis

### Issue 1: Data Extraction
The "Extract Webhook Data" node expects fields from Photo Bot V2 integration:
```javascript
const body = $input.item.json.body;
return {
  json: {
    manufacturer: body.manufacturer || '',  // ← Empty when direct test
    model_number: body.model_number || '',  // ← Empty when direct test
    product_family: body.product_family || null,
    // ...
  }
};
```

When testing directly, the payload structure is different:
```json
{
  "make": "Caterpillar",      // ← Not "manufacturer"
  "model": "D9T",             // ← Not "model_number"
  "type": "bulldozer"
}
```

### Issue 2: Cache SQL Query
With empty manufacturer/model:
```sql
SELECT * FROM manual_hunter_cache
WHERE LOWER(manufacturer) = LOWER('')  -- Empty string
  AND (
    LOWER(model_number) = LOWER('')    -- Empty string
    OR (...)
  )
```

This query returns `[]` (no results), which is correct, but...

### Issue 3: Missing Flow Connection
The "Check Cache" node returns empty array `[]`. In n8n:
- Empty array means "no items to process"
- Downstream nodes don't execute when input is empty
- This is WHY the workflow stops!

The "Cache Hit?" node never receives data to evaluate because the empty result from "Check Cache" doesn't flow.

### Issue 4: Cache Hit Logic
Even if data flowed, the "Cache Hit?" node checks:
```javascript
{
  "conditions": {
    "conditions": [
      {
        "id": "cache-exists",
        "leftValue": "={{ $json.id }}",  // ← undefined for empty cache
        "operator": { "type": "any", "operation": "exists" }
      }
    ]
  }
}
```

With no cached data, `$json.id` is undefined, should route to "false" branch (Tier 1), but node never executes.

## Impact

**Critical Business Impact:**
- Manual Hunter cannot find any manuals
- Users receive no response when uploading nameplate photos
- Photo Bot V2 integration broken
- All manual search requests dead-end at cache check

**Affected Components:**
- Manual Hunter workflow (main search orchestration)
- Photo Bot V2 (depends on Manual Hunter)
- Telegram bot user experience

## Proposed Solution

### Fix 1: Normalize Input Data
Update "Extract Webhook Data" to handle both direct testing AND Photo Bot V2:

```javascript
const body = $input.item.json.body || $input.item.json;

return {
  json: {
    chat_id: body.chat_id,
    original_message_id: body.original_message_id,
    // Support both field name conventions
    manufacturer: body.manufacturer || body.make || '',
    model_number: body.model_number || body.model || '',
    product_family: body.product_family || body.type || null,
    full_ocr_text: body.full_ocr_text || '',
    timestamp: new Date().toISOString()
  }
};
```

### Fix 2: Ensure Cache Flow with Empty Results
Add a "No Op" transform after "Check Cache" that always returns an item:

```javascript
// Always return data, even if cache is empty
const cacheResult = $input.all();

if (cacheResult.length === 0) {
  // No cache hit - return empty cache marker
  return {
    json: {
      cache_hit: false,
      cached_data: null
    }
  };
} else {
  // Cache hit - return the data
  return {
    json: {
      cache_hit: true,
      cached_data: cacheResult[0].json
    }
  };
}
```

### Fix 3: Update Cache Hit Logic
Simplify "Cache Hit?" to check the new field:

```javascript
{
  "conditions": {
    "conditions": [
      {
        "leftValue": "={{ $json.cache_hit }}",
        "operator": { "type": "boolean", "operation": "true" }
      }
    ]
  }
}
```

### Fix 4: Add Validation
Add input validation before cache check:

```javascript
// Validate required fields
if (!manufacturer || manufacturer.trim() === '') {
  return {
    json: {
      error: 'Manufacturer is required',
      should_queue: true
    }
  };
}

if (!model_number || model_number.trim() === '') {
  return {
    json: {
      error: 'Model number is required',
      should_queue: true
    }
  };
}
```

## Testing Plan

### Test Cases

1. **Cache Hit (existing manual)**
   ```json
   {
     "manufacturer": "Caterpillar",
     "model_number": "D9T"
   }
   ```
   Expected: Return cached manual instantly

2. **Cache Miss → Tier 1 Success**
   ```json
   {
     "manufacturer": "NewEquipCo",
     "model_number": "XYZ-123"
   }
   ```
   Expected: Tier 1 search finds manual, validates, caches, returns

3. **Cache Miss → Tier 2 Success**
   ```json
   {
     "manufacturer": "ObscureBrand",
     "model_number": "ABC-999"
   }
   ```
   Expected: Tier 1 fails, escalates to Tier 2, finds manual

4. **All Tiers Fail → Human Queue**
   ```json
   {
     "manufacturer": "NoManuals",
     "model_number": "DNE-000"
   }
   ```
   Expected: Add to human queue, notify user

5. **Photo Bot V2 Integration**
   - Upload nameplate photo via Telegram
   - Verify OCR extraction
   - Verify Manual Hunter receives correct data format
   - Verify end-to-end manual retrieval

### Success Criteria

- [ ] Cache miss flows to Tier 1 search
- [ ] Tier 1 search executes Tavily + Groq + URL validation
- [ ] Tier 2 search executes when Tier 1 fails
- [ ] Human queue receives requests when all tiers fail
- [ ] Photo Bot V2 integration works end-to-end
- [ ] All 5 test cases pass

## Files to Modify

1. `n8n/workflows/test/rivet_manual_hunter_active.json`
   - Update "Extract Webhook Data" node
   - Add cache flow normalization
   - Update "Cache Hit?" logic
   - Add input validation

## Additional Notes

This bug was discovered during automated E2E testing. The workflow was likely designed to work with Photo Bot V2's specific payload structure and never tested standalone.

**Workaround:** None - workflow is completely broken for manual searches.

**Timeline:** Fix ASAP - blocking manual search functionality.
