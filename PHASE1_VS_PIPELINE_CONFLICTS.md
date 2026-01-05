# ⚠️ PHASE 1 vs EXTRACTION PIPELINE - CONFLICT RESOLUTION

**Date:** 2026-01-03
**Resolution:** HYBRID APPROACH - Use Phase 1 infrastructure, integrate harvest patterns/prompts

---

## 🎯 BOTTOM LINE

**Keep Phase 1's skeleton (infrastructure), harvest the meat (patterns, prompts, handlers).**

- ✅ **USE Phase 1:** Multi-provider LLM router, config, observability, file structure
- ✅ **USE Harvest Blocks:** Manufacturer patterns, SME prompts, vendor keywords, Telegram handlers

---

## ⚠️ CONFLICTS IDENTIFIED

### 1. LLM Provider Strategy

| Aspect | Phase 1 (Existing) | Extraction Pipeline | Resolution |
|--------|-------------------|---------------------|------------|
| **Structure** | Multi-provider router (`llm.py`) | Claude-only (`anthropic.py`) | **USE PHASE 1** |
| **Providers** | Groq→Gemini→Claude→GPT-4o-mini→GPT-4o | Gemini only | **USE PHASE 1** |
| **Cost Optimization** | 73% savings via free Groq first | Not mentioned | **USE PHASE 1** |
| **Flexibility** | All providers supported | Single provider | **USE PHASE 1** |

**Decision:** Keep `rivet/integrations/llm.py` multi-provider router. Do NOT create single-purpose `anthropic.py`.

---

### 2. SME Prompts Structure

| Aspect | Phase 1 (Existing) | Extraction Pipeline | Resolution |
|--------|-------------------|---------------------|------------|
| **File Structure** | 7 separate files in `prompts/sme/*.py` | Single `prompts/__init__.py` | **USE PHASE 1** |
| **Vendors** | siemens, rockwell, abb, schneider, mitsubishi, fanuc, generic | Same 7 vendors | **USE PHASE 1** |
| **Organization** | One file per vendor | All in one file | **USE PHASE 1** |

**Decision:** Keep separate files per vendor. Compare harvest prompts with existing and enhance if better.

---

### 3. Configuration System

| Aspect | Phase 1 (Existing) | Extraction Pipeline | Resolution |
|--------|-------------------|---------------------|------------|
| **Config** | Full Pydantic with `TierLimits` | Not specified | **USE PHASE 1** |
| **Tier Support** | Beta, Pro, Team with limits | Not mentioned | **USE PHASE 1** |
| **Settings** | Centralized in `config.py` | Not specified | **USE PHASE 1** |

**Decision:** Keep existing config.py. Use it for all harvest integrations.

---

### 4. Observability

| Aspect | Phase 1 (Existing) | Extraction Pipeline | Resolution |
|--------|-------------------|---------------------|------------|
| **Tracing** | Phoenix + LangSmith | Not mentioned | **USE PHASE 1** |
| **Logging** | Structured with context | Not specified | **USE PHASE 1** |
| **Monitoring** | Full observability stack | Not mentioned | **USE PHASE 1** |

**Decision:** Keep `rivet/observability/tracer.py` and all observability features.

---

### 5. OCR Detection Methods

| Aspect | Phase 1 (Existing) | Extraction Pipeline | Resolution |
|--------|-------------------|---------------------|------------|
| **Manufacturer Detection** | LLM-based (Gemini/Claude) | Regex patterns | **MERGE BOTH** |
| **Model/Serial Extraction** | LLM-based | Vendor-specific regex | **MERGE BOTH** |
| **Approach** | AI-first | Pattern-first | **HYBRID** |

**Decision:**
- ADD harvested regex patterns to `ocr.py` as helper functions
- Use regex FIRST (fast, cheap), LLM as FALLBACK (accurate for edge cases)
- Best of both worlds: speed + accuracy

---

## ✅ WHAT TO HARVEST & INTEGRATE

### Round 1-2: Manufacturer & Model/Serial Patterns
**Status:** Phase 1 has LLM-based detection
**Action:** ADD harvest regex patterns as helpers
**File:** `rivet/workflows/ocr.py`
**Strategy:** Try regex first (fast), fall back to LLM if no match

```python
# NEW in ocr.py
MANUFACTURER_PATTERNS = {
    "siemens": [r"6ES7.*", r"SIMATIC.*", ...],  # from harvest
    "rockwell": [r"1756-.*", r"1769-.*", ...],
    # ... more from harvest
}

def detect_manufacturer_regex(text: str) -> Optional[str]:
    """Fast regex-based detection (from harvest)."""
    # Use harvested patterns

async def detect_manufacturer(text: str) -> Optional[str]:
    """Hybrid detection: regex first, LLM fallback."""
    # Try regex first (fast, free)
    result = detect_manufacturer_regex(text)
    if result:
        return result

    # Fall back to LLM (accurate, costs money)
    return await detect_manufacturer_llm(text)
```

---

### Round 3: OCR Prompts - EXPANDED SCOPE
**Status:** Phase 1 has multi-provider prompts
**Action:** ENHANCE prompts for ALL providers (not just Gemini)
**File:** `rivet/integrations/llm.py`

**CRITICAL:** Harvester needs to find prompts for ALL vision providers:
- ✅ Gemini Vision prompt
- ✅ Claude Vision prompt (Haiku/Sonnet)
- ✅ GPT-4o Vision prompt
- ✅ Groq Vision prompt (if exists)
- ✅ Confidence scoring logic
- ✅ Fallback chain logic

**Integration:** Compare harvested prompts, use best practices across all providers.

---

### Round 4: SME Prompts
**Status:** Phase 1 has all 7 vendor prompts
**Action:** COMPARE and ENHANCE existing files
**Files:** `rivet/prompts/sme/*.py` (7 files)

**Process:**
1. Receive harvest block for each vendor
2. Compare with existing prompt in corresponding file
3. If harvest is better: UPDATE existing file
4. If existing is better: LOG for reference, keep existing
5. MERGE any additional vendor-specific knowledge

---

### Round 5: Vendor Keywords
**Status:** Phase 1 has `VENDOR_PATTERNS` dict
**Action:** MERGE harvest keywords into existing dict
**File:** `rivet/workflows/sme_router.py`

```python
# EXISTING in sme_router.py
VENDOR_PATTERNS = {
    "siemens": ["s7-1200", "tia portal", ...],
    # ... existing keywords
}

# AFTER HARVEST: Merge additional keywords
VENDOR_PATTERNS = {
    "siemens": [
        # Existing keywords
        "s7-1200", "tia portal",
        # NEW from harvest
        "simatic step 7", "profinet io", ...
    ],
}
```

---

### Round 6: Route Logic & Thresholds
**Status:** Phase 1 has full 4-route orchestrator
**Action:** VALIDATE harvest thresholds match existing
**File:** `rivet/workflows/troubleshoot.py`

**Current thresholds:**
- KB confidence: 0.85
- SME confidence: 0.70

**Process:**
1. Receive harvest route logic
2. Compare thresholds with existing
3. If harvest thresholds are production-tested and different: ADJUST
4. If same: VALIDATE and confirm
5. Compare decision tree logic for edge cases

---

### Round 7: Telegram Handlers ⭐ PRIMARY BUILD
**Status:** Phase 1 has template, NO implementation
**Action:** INTEGRATE harvest into template
**File:** `rivet/integrations/telegram.py`

**This is the ONLY major component missing from Phase 1!**

Harvest will provide:
- Proven handler implementations
- Response formatting logic
- Error handling patterns
- User interaction flows

Integration: Replace template TODOs with harvest implementations.

---

### Round 8: Anthropic Integration
**Status:** Phase 1 has full Claude support in `llm.py`
**Action:** SKIP separate anthropic.py (redundant)

**Decision:** llm.py already handles:
- Anthropic SDK integration
- Claude Haiku/Sonnet/Opus support
- Vision API calls
- Error handling
- Cost tracking

**No need for separate file.** If harvest provides better Claude-specific logic, integrate into llm.py.

---

### Round 9: Rate Limiting & Usage Tracking ⭐ NEW
**Status:** Phase 1 has `TierLimits` in config, NO enforcement
**Action:** CREATE new file from harvest
**File:** `rivet/utils/rate_limiter.py` (NEW)

**Expected from harvest:**
- Query counting per user
- Daily reset logic
- Tier enforcement (beta=50/day, pro=1000/day, team=unlimited)
- Rate limit exceeded handling
- Redis/DB integration for persistence

**Integration:** Create new file, wire to Telegram handlers and config.

---

## 🔧 PACKAGE UPDATE: google.generativeai → google.genai

### Issue Identified
Harvester found warning:
```
FutureWarning: All support for `google.generativeai` package has ended.
Please switch to `google.genai` package.
```

### Resolution Applied
✅ **Updated** `pyproject.toml`:
- OLD: `"google-generativeai>=0.3"`
- NEW: `"google-genai>=0.2"`

✅ **Updated** `rivet/integrations/llm.py`:
- OLD: `import google.generativeai as genai`
- NEW: `from google import genai`
- OLD: `genai.GenerativeModel(model_name)`
- NEW: `genai.Client(api_key=api_key)`
- OLD: `model.generate_content_async([...])`
- NEW: `client.aio.models.generate_content(model=model, contents=[...])`

---

## 📋 HARVEST INTEGRATION CHECKLIST

When each harvest block arrives:

- [ ] **Identify** which round it belongs to
- [ ] **Check** conflict resolution table above
- [ ] **Apply** correct strategy (USE PHASE 1 / MERGE / CREATE NEW)
- [ ] **Enhance** existing files, DON'T replace
- [ ] **Validate** imports work
- [ ] **Test** integration
- [ ] **Log** what was integrated

---

## 🎯 SUMMARY

**Phase 1 Infrastructure (KEEP):**
- ✅ Multi-provider LLM router
- ✅ Cost optimization (73% savings)
- ✅ Config system with tier limits
- ✅ Observability (Phoenix + LangSmith)
- ✅ 7 separate SME prompt files
- ✅ 4-route orchestrator
- ✅ File structure

**Harvest Blocks (INTEGRATE):**
- ✅ Production-tested regex patterns
- ✅ Proven SME prompts
- ✅ Vendor detection keywords
- ✅ Working Telegram handlers
- ✅ Rate limiting logic

**Result:** Best of both worlds - robust infrastructure + proven patterns.

---

**Builder Agent Ready:** Awaiting harvest blocks with hybrid integration strategy.
