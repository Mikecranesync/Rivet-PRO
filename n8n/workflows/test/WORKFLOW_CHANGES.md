# RIVET LLM Judge Workflow - Fix Summary

## Problem
The HTTP Request node to Gemini API was failing because n8n Cloud blocks `{{ $env.GOOGLE_API_KEY }}`.

## Solution
Replaced 1 broken HTTP Request node with 3 new nodes that use n8n's native credential system.

---

## Visual Flow Comparison

### BEFORE (Broken)
```
Prepare LLM Prompt
       ↓
[LLM Analysis (Gemini)]  ← HTTP Request ❌ FAILS
       ↓                    (blocks $env.GOOGLE_API_KEY)
Parse LLM Response
```

### AFTER (Fixed)
```
Prepare LLM Prompt
       ↓
[Extract Prompt Text]     ← NEW: Code node
       ↓                     (extracts prompt + config)
[LLM Analysis (Gemini)]   ← REPLACED: Native Gemini node ✅
       ↓                     (uses n8n credentials)
[Format Gemini Response]  ← NEW: Code node
       ↓                     (formats to expected structure)
Parse LLM Response
```

---

## What Changed

### ❌ REMOVED
- **Node:** LLM Analysis (Gemini) - HTTP Request
- **Reason:** n8n Cloud blocks `$env.GOOGLE_API_KEY`

### ✅ ADDED

#### 1. Extract Prompt Text (Code Node)
**Purpose:** Extract prompt and config from `gemini_request` object

**Input:**
```json
{
  "gemini_request": {
    "contents": [{"parts": [{"text": "..."}]}],
    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 800}
  }
}
```

**Output:**
```json
{
  "prompt": "Full prompt text...",
  "temperature": 0.1,
  "maxTokens": 800,
  "url": "...",
  "equipment_type": "...",
  "manufacturer": "..."
}
```

---

#### 2. LLM Analysis (Gemini) - Native Node
**Purpose:** Call Gemini API using n8n credential system

**Configuration:**
- Type: `n8n-nodes-base.googleGemini`
- Credential: Your existing Google API credential
- Model: `gemini-1.5-flash`
- Prompt: `{{ $json.prompt }}`
- Temperature: `{{ $json.temperature }}` (0.1)
- Max Tokens: `{{ $json.maxTokens }}` (800)
- Continue on Fail: `true`

**Input:**
```json
{
  "prompt": "Full evaluation prompt...",
  "temperature": 0.1,
  "maxTokens": 800
}
```

**Output:**
```json
{
  "text": "{\"completeness\": 8, \"technical_accuracy\": 9, ...}",
  // (exact field name may vary - check during testing)
}
```

---

#### 3. Format Gemini Response (Code Node)
**Purpose:** Transform native node output to match expected API response format

**Input:**
```json
{
  "text": "{\"completeness\": 8, ...}"
}
```

**Output:**
```json
{
  "candidates": [{
    "content": {
      "parts": [{"text": "{\"completeness\": 8, ...}"}]
    }
  }],
  "url": "...",
  "equipment_type": "...",
  "manufacturer": "..."
}
```

This format matches what "Parse LLM Response" expects from the Gemini API.

---

## Connection Changes

### Old Connections
```
Prepare LLM Prompt → LLM Analysis (Gemini) → Parse LLM Response
```

### New Connections
```
Prepare LLM Prompt
    → Extract Prompt Text
    → LLM Analysis (Gemini)
    → Format Gemini Response
    → Parse LLM Response
```

---

## Files

- **Original:** `n8n/workflows/test/rivet_llm_judge.json`
- **Fixed:** `n8n/workflows/test/rivet_llm_judge_fixed.json`
- **Import:** Use the fixed version in n8n Cloud

---

## Next Steps

1. **Import the fixed workflow** to n8n Cloud (see IMPORT_INSTRUCTIONS.md)
2. **Configure credential** in the "LLM Analysis (Gemini)" node
3. **Test the workflow** with a sample manual
4. **Activate** if tests pass
5. **Delete** or archive the old broken workflow

---

## Benefits

✅ Works on n8n Cloud (no env var needed)
✅ Uses n8n's secure credential system
✅ Same model (gemini-1.5-flash)
✅ Same temperature/tokens config
✅ Same error handling behavior
✅ Compatible with existing downstream nodes

---

## Rollback

If the new workflow fails, you can:
1. Re-import the original `rivet_llm_judge.json`
2. Consider self-hosting n8n where env vars work
3. Use HTTP Request with credential-based API key (different approach)
