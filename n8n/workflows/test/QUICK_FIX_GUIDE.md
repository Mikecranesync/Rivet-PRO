# Quick Fix Guide - RIVET LLM Judge Gemini Node

## TL;DR

Replace broken HTTP Request → Gemini with 3 native nodes:
1. Extract Prompt Text (Code)
2. LLM Analysis (Gemini) - Native
3. Format Gemini Response (Code)

---

## 5-Minute Fix

### 1. Import Fixed Workflow
```bash
# File location:
n8n/workflows/test/rivet_llm_judge_fixed.json
```

- Go to n8n Cloud → Import from File
- Upload `rivet_llm_judge_fixed.json`
- Workflow name: "RIVET LLM Judge (Fixed)"

### 2. Configure Credential

Click "LLM Analysis (Gemini)" node → Select Google API credential

**Need a credential?**
- n8n: Create New Credential → Google API
- API Key: Get from https://aistudio.google.com/app/apikey

### 3. Test

Click "Test workflow" → Paste this:
```json
{
  "manual_text": "Motor specs: 480V, 50HP, 1750RPM",
  "equipment_type": "Motor"
}
```

Expected output:
```json
{
  "quality_score": 6.8,
  "criteria": {...},
  "llm_model_used": "gemini-1.5-flash"
}
```

### 4. Activate

Toggle "Active" → Done!

---

## Node Details

### Node 1: Extract Prompt Text
**Type:** Code
**Input:** `$json.gemini_request`
**Output:** `{ prompt, temperature, maxTokens }`

### Node 2: LLM Analysis (Gemini)
**Type:** Google Gemini (native)
**Config:**
- Model: gemini-1.5-flash
- Prompt: `{{ $json.prompt }}`
- Temp: `{{ $json.temperature }}` (0.1)
- Max: `{{ $json.maxTokens }}` (800)

### Node 3: Format Gemini Response
**Type:** Code
**Input:** Gemini output
**Output:** `{ candidates[0].content.parts[0].text }`

---

## What Changed

### Before (Broken)
```
HTTP Request → Gemini API
❌ Fails: "access to env vars denied"
```

### After (Fixed)
```
Extract → Native Gemini Node → Format
✅ Works: Uses n8n credential system
```

---

## Files Created

1. **rivet_llm_judge_fixed.json** - Import this
2. **IMPORT_INSTRUCTIONS.md** - Full guide
3. **WORKFLOW_CHANGES.md** - Detailed changes
4. **QUICK_FIX_GUIDE.md** - This file

---

## Troubleshooting

**Error: "Credential not found"**
→ Click node → Select your Google API credential

**Error: "Model not available"**
→ Verify API key has Gemini access at https://aistudio.google.com

**Response format wrong**
→ Check "Format Gemini Response" code - update field names

**Node not found: googleGemini**
→ Your n8n might not have it - try LangChain Gemini node

---

## Verify Success

- [ ] Workflow imported (13 nodes)
- [ ] Credential configured
- [ ] Test execution passes
- [ ] Returns quality scores
- [ ] Workflow activated

**Done!** ✅

---

## Contact

Issues? Check:
1. n8n execution logs
2. Google API key validity
3. Node connections
4. Full docs: IMPORT_INSTRUCTIONS.md
