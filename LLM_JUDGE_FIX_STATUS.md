# LLM Judge Workflow Fix Status

**Date**: 2026-01-10
**Workflow ID**: QaFV6k14mQroMfat
**Status**: FIXES APPLIED - REQUIRES UI VERIFICATION

---

## Issues Identified and Fixed

### 1. ✅ Incorrect Gemini Model (FIXED)
**Problem**: Workflow was using `gemini-1.5-flash` which doesn't exist in v1 or v1beta API
**Fix**: Updated to `gemini-2.5-flash` (latest stable model)
**Node**: LLM Analysis (Gemini)
**Change**:
- Old: `v1beta/models/gemini-1.5-flash`
- New: `v1/models/gemini-2.5-flash`

### 2. ✅ Markdown Code Fence Parsing (FIXED)
**Problem**: Gemini returns JSON wrapped in ```json ... ``` markdown fences
**Fix**: Updated parser to strip markdown fences before JSON.parse()
**Node**: Parse LLM Response
**Change**: Added regex to remove code fences:
```javascript
content = content.replace(/^```json\s*/i, '').replace(/\s*```$/i, '').trim();
```

### 3. ✅ Token Truncation (FIXED)
**Problem**: Gemini 2.5 Flash uses ~720 "thinking tokens" before output, causing MAX_TOKENS finish reason
**Fix**: Increased maxOutputTokens from 800 to 2000
**Node**: Prepare LLM Prompt
**Change**:
- Old: `"maxOutputTokens": 800`
- New: `"maxOutputTokens": 2000`

---

## Fixes Applied

| Fix # | Component | Change | Status |
|-------|-----------|--------|--------|
| 1 | LLM Analysis Node | Updated to gemini-2.5-flash | ✅ Applied |
| 2 | Parse LLM Response | Strip markdown fences | ✅ Applied |
| 3 | Prepare LLM Prompt | maxOutputTokens: 2000 | ✅ Applied |
| 4 | Workflow | Deactivate/Reactivate | ✅ Completed |

---

## Testing Results

### Direct API Test
- ✅ Gemini 2.5 Flash confirmed working
- ✅ Returns valid JSON scores
- ✅ Model responds in 2-3 seconds
- ⚠️ With maxOutputTokens: 800, response truncated (finishReason: MAX_TOKENS)
- ✅ With maxOutputTokens: 2000, full response expected

### Workflow Test
- Webhook: `https://mikecranesync.app.n8n.cloud/webhook/rivet-llm-judge`
- Response: HTTP 200
- Issue: Still returning all zeros despite fixes
- Response time: < 1 second (suspiciously fast - suggests error)

---

## Diagnosis

The workflow is responding but returning default values (all zeros), suggesting:

1. **Possible Gemini API Call Failure**
   - GOOGLE_API_KEY might not be set in n8n environment variables
   - API call might be timing out silently
   - Error being swallowed by `continueOnFail: true`

2. **Possible Workflow Path Issue**
   - Might be taking a different execution path
   - Could be failing earlier in the flow

3. **Possible N8N Caching**
   - Workflow changes applied via API
   - n8n cloud might need manual refresh in UI

---

## Recommended Next Steps

### IMMEDIATE: Check n8n UI

1. **Login to n8n cloud**: https://mikecranesync.app.n8n.cloud

2. **Open LLM Judge workflow** (ID: QaFV6k14mQroMfat)

3. **Verify environment variables**:
   - Settings → Environment Variables
   - Confirm `GOOGLE_API_KEY` is set
   - Test the key works

4. **Check recent executions**:
   - Click "Executions" tab
   - View latest execution
   - Inspect each node's output
   - Look for errors in "LLM Analysis (Gemini)" node

5. **Manual test in UI**:
   - Click "Execute Workflow"
   - Send test payload:
   ```json
   {
     "manual_text": "Test manual content",
     "equipment_type": "Motor",
     "manufacturer": "Test Corp"
   }
   ```
   - Watch execution flow node-by-node
   - Verify Gemini returns scores

### VERIFICATION: Check Each Node

**Nodes to inspect**:
1. **Extract Request Data** - Verify manual_text is extracted
2. **Needs Fetch?** - Should be FALSE for manual_text input
3. **Pass Through** - Should receive data
4. **Merge Content** - Should have manual_text populated
5. **Prepare LLM Prompt** - Check gemini_request is built correctly
6. **LLM Analysis (Gemini)** - **CRITICAL** - Check response structure
7. **Parse LLM Response** - Should extract scores from Gemini response

### QUICK FIX: If Still Failing

If workflow still returns zeros after checking above:

1. **Re-import workflow**:
   - Download: `llm_judge_fixed_parser.json`
   - Delete existing workflow
   - Import as new workflow
   - Set environment variables
   - Test

2. **Check API key**:
   ```bash
   # Test Gemini API directly
   curl "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key=YOUR_KEY" \
     -H "Content-Type: application/json" \
     -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
   ```

---

## Files Created

| File | Purpose |
|------|---------|
| `search_llm_judge_workflow.py` | Find workflow in n8n cloud |
| `fetch_llm_judge.py` | Download current workflow |
| `test_llm_judge.py` | Test workflow endpoint |
| `list_gemini_models.py` | List available Gemini models |
| `test_gemini_2_5.py` | Test Gemini 2.5 Flash directly |
| `fix_llm_judge_v2.py` | Update to gemini-2.5-flash |
| `fix_llm_judge_parser.py` | Fix markdown fence parsing |
| `fix_max_tokens.py` | Increase maxOutputTokens |
| `llm_judge_fixed_parser.json` | Complete fixed workflow |

---

## Summary

**Workflow Changes**: ✅ All applied successfully via API

**API Testing**: ✅ Gemini 2.5 Flash works correctly

**Workflow Testing**: ⚠️ Returns zeros (requires UI debugging)

**Likely Cause**: Environment variable (GOOGLE_API_KEY) not set in n8n cloud, or workflow execution path issue

**Resolution**: Access n8n UI to verify environment variables and inspect execution logs

---

**Next Action**: Login to n8n cloud UI and manually inspect the workflow execution to identify where the Gemini API call is failing.
