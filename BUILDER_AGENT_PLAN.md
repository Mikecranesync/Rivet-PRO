# 🏗️ RIVET BUILDER AGENT - INTEGRATION PLAN

**Role:** Builder Agent operating in rivet-pro repository
**Mission:** Receive harvest blocks from Harvester Agent and integrate them production-ready
**Status:** Repository ~70% complete, awaiting harvest blocks for validation/enhancement
**Date:** 2026-01-03
**Strategy:** HYBRID APPROACH - Phase 1 infrastructure + Harvest block patterns/prompts

---

## 🚨 CRITICAL: HYBRID APPROACH DECISION

### ⚠️ Conflicts Resolved

**PHASE 1 WINS FOR INFRASTRUCTURE:**
- ✅ **Multi-provider LLM router** (`rivet/integrations/llm.py`) - NOT Claude-only
- ✅ **Cost optimization** (Groq→Gemini→Claude→GPT-4o-mini→GPT-4o)
- ✅ **Config system** (Pydantic with tier limits)
- ✅ **Observability** (Phoenix + LangSmith tracing)
- ✅ **File structure** (7 separate SME files, not one __init__.py)

**HARVEST BLOCKS WIN FOR CONTENT:**
- ✅ **Manufacturer regex patterns** (production-tested)
- ✅ **SME prompts** (proven in production)
- ✅ **Vendor keywords** (real detection logic)
- ✅ **Telegram handlers** (working bot code)
- ✅ **Rate limiting logic** (NEW Round 9)

### 🎯 Integration Strategy UPDATE

**DO NOT replace Phase 1 files. ENHANCE them with harvest blocks:**

| Harvest | Phase 1 File | Action |
|---------|-------------|--------|
| Manufacturer patterns | `rivet/workflows/ocr.py` | ADD regex patterns as helpers |
| Model/serial extraction | `rivet/workflows/ocr.py` | MERGE vendor-specific patterns |
| OCR prompts | `rivet/integrations/llm.py` | ENHANCE prompts for ALL providers |
| SME prompts | `rivet/prompts/sme/*.py` | COMPARE and UPDATE existing files |
| Vendor keywords | `rivet/workflows/sme_router.py` | MERGE into VENDOR_PATTERNS |
| Route logic | `rivet/workflows/troubleshoot.py` | VALIDATE thresholds |
| Telegram handlers | `rivet/integrations/telegram.py` | INTEGRATE into template |
| Rate limiting | **NEW FILE**: `rivet/utils/rate_limiter.py` | CREATE from harvest |

---

## 📊 CURRENT STATE ASSESSMENT

### ✅ Phase 1: OCR Workflow (COMPLETE)
- **File:** `rivet/workflows/ocr.py` (296 lines)
- **Status:** Production-ready with 5-provider LLM router
- **Features:**
  - Image quality validation
  - Manufacturer detection
  - Model/serial extraction
  - Fault code parsing
  - 73% cost optimization (Groq → Gemini → Claude → GPT-4o-mini → GPT-4o)
- **Tests:** 13 test cases in `tests/test_ocr.py`

### ✅ Phase 2: 4-Route Orchestrator (BUILT)
- **File:** `rivet/workflows/troubleshoot.py` (370 lines)
- **Status:** Fully implemented
- **Routes:**
  - Route A: KB Search (confidence >= 0.85)
  - Route B: Vendor SME Dispatch (manufacturer-specific)
  - Route C: Research Trigger (async KB gap filling)
  - Route D: General Claude Fallback

### ✅ SME Router & Prompts (BUILT)
- **File:** `rivet/workflows/sme_router.py` (313 lines)
- **Prompts:** `rivet/prompts/sme/` (7 vendor SMEs)
  - siemens.py (181 lines)
  - rockwell.py (186 lines)
  - abb.py (181 lines)
  - schneider.py (189 lines)
  - mitsubishi.py (190 lines)
  - fanuc.py (192 lines)
  - generic.py (211 lines)
- **Vendor detection:** Keyword-based pattern matching

### ✅ Supporting Workflows (BUILT)
- `rivet/workflows/kb_search.py` - Knowledge base search
- `rivet/workflows/research.py` - Async research triggers
- `rivet/workflows/general.py` - General Claude fallback

### ✅ Infrastructure (BUILT)
- `rivet/config.py` - Centralized settings with Pydantic
- `rivet/integrations/llm.py` - Multi-provider LLM router
- `rivet/observability/tracer.py` - Phoenix + LangSmith tracing
- `pyproject.toml` - Dependencies configured (includes telegram, stripe)

### ❌ MISSING COMPONENTS

**Priority 1: Telegram Bot Integration**
- `rivet/integrations/telegram.py` - Main bot handlers
  - /start handler (onboarding)
  - /help handler
  - Photo handler → calls ocr_workflow()
  - Message handler → calls troubleshoot()
  - Response formatting
  - Error handling

**Priority 2: Stripe Payment Integration**
- `rivet/integrations/stripe.py`
  - Subscription management
  - Webhook handlers
  - Usage tracking

**Priority 3: Anthropic Integration** (Optional)
- `rivet/integrations/anthropic.py` - Standalone Claude wrapper
- NOTE: `llm.py` already handles Claude API, this may be redundant

---

## 🔄 HARVEST BLOCK RECEPTION WORKFLOW

### Format Expected from Harvester:
```
=== HARVEST: [Component Name] ===
SOURCE: [file path and lines]
WHAT: [brief description]

```python
[clean, standalone code]
```

NOTES FOR BUILDER:
- [integration notes]
- [dependencies needed]
- [gotchas]
=== END HARVEST ===
```

### My Integration Process:
1. **RECEIVE** harvest block via copy-paste from user
2. **ANALYZE** where it fits in existing structure
3. **DECIDE** integration strategy:
   - **VALIDATE:** Compare with existing implementation
   - **ENHANCE:** Add missing patterns/logic to existing files
   - **CREATE:** Build new file if component missing
   - **SKIP:** Already implemented, log for reference
4. **INTEGRATE** with production standards:
   - Type hints on all functions
   - Proper error handling
   - Logging with context
   - Config-based settings (no hardcoded values)
   - Dataclasses for structured data
   - Async where appropriate
5. **TEST** integration works with existing code
6. **DOCUMENT** what was integrated and any deviations

---

## 📋 EXTRACTION SEQUENCE MAPPING

### Round 1: Manufacturer Patterns → ocr.py
**Expected Harvest:** Regex patterns for manufacturers (Siemens, Rockwell, ABB, etc.)

**Current State:** `rivet/workflows/ocr.py` already has:
```python
def detect_manufacturer(text: str) -> Optional[str]:
    # Uses LLM-based detection, not regex patterns
```

**Integration Strategy:**
- **COMPARE** harvest patterns with current LLM-based approach
- **DECIDE** if regex patterns should:
  - Replace LLM detection (faster, cheaper)
  - Supplement LLM detection (hybrid approach)
  - Be logged as reference only
- **IF REPLACING:** Refactor `detect_manufacturer()` to use regex first, LLM fallback
- **VALIDATE** accuracy matches or exceeds current approach

**Target Location:** `rivet/workflows/ocr.py:detect_manufacturer()`

---

### Round 2: Model/Serial Extraction → ocr.py
**Expected Harvest:** Regex patterns for model numbers and serial numbers

**Current State:** `rivet/workflows/ocr.py` already extracts via LLM

**Integration Strategy:**
- **ADD** regex patterns as constants at top of file
- **ENHANCE** extraction logic with vendor-specific patterns (6ES7 for Siemens, 1756- for Rockwell)
- **CREATE** `extract_model_number()` and `extract_serial_number()` helper functions if not present
- **KEEP** existing LLM extraction as fallback

**Target Location:** `rivet/workflows/ocr.py`

---

### Round 3: OCR Prompt → ocr.py
**Expected Harvest:** Gemini Vision OCR prompt

**Current State:** `rivet/workflows/ocr.py` uses multi-provider LLM router with structured prompts

**Integration Strategy:**
- **COMPARE** harvested Gemini prompt with current implementation
- **EXTRACT** any superior prompt engineering techniques
- **ENHANCE** existing prompts if harvest version is better
- **PRESERVE** multi-provider approach (don't hardcode to Gemini only)

**Target Location:** `rivet/workflows/ocr.py:ocr_workflow()`

---

### Round 4: SME Prompts → prompts/sme/
**Expected Harvest:** 7+ vendor SME prompts (Siemens, Rockwell, ABB, Schneider, Mitsubishi, Fanuc, Generic)

**Current State:** ALL 7 SME prompts ALREADY EXIST in `rivet/prompts/sme/*.py`
- siemens.py (181 lines)
- rockwell.py (186 lines)
- abb.py (181 lines)
- schneider.py (189 lines)
- mitsubishi.py (190 lines)
- fanuc.py (192 lines)
- generic.py (211 lines)

**Integration Strategy:**
- **COMPARE** harvested prompts with existing implementations
- **VALIDATE** harvested prompts are production-tested
- **ENHANCE** existing prompts if harvest version superior
- **MERGE** any additional vendor-specific knowledge
- **DOCUMENT** differences for review

**Target Location:** `rivet/prompts/sme/*.py` (ENHANCEMENT ONLY)

---

### Round 5: Vendor Keywords → sme_router.py
**Expected Harvest:** Keyword lists for vendor detection

**Current State:** `rivet/workflows/sme_router.py` has `VENDOR_PATTERNS` dict with keywords

**Integration Strategy:**
- **COMPARE** harvested keywords with existing `VENDOR_PATTERNS`
- **MERGE** any missing keywords into existing patterns
- **VALIDATE** detection accuracy improves
- **TEST** against known equipment queries

**Target Location:** `rivet/workflows/sme_router.py:VENDOR_PATTERNS`

---

### Round 6: Route Logic → troubleshoot.py
**Expected Harvest:** 4-route decision logic with confidence thresholds

**Current State:** `rivet/workflows/troubleshoot.py` FULLY IMPLEMENTED
- Default thresholds: KB=0.85, SME=0.70
- Complete decision tree logic

**Integration Strategy:**
- **VALIDATE** harvested thresholds match production-tested values
- **COMPARE** decision logic for any edge cases
- **ADJUST** thresholds if harvest provides better calibration
- **TEST** routing accuracy after any changes

**Target Location:** `rivet/workflows/troubleshoot.py:troubleshoot()`

---

### Round 7: Telegram Handlers → integrations/telegram.py
**Expected Harvest:** Bot handlers, response formatting, bot configuration

**Current State:** ❌ **FILE DOES NOT EXIST** - This is the PRIMARY BUILD TASK

**Integration Strategy:**
- **CREATE** `rivet/integrations/telegram.py` from scratch
- **STRUCTURE** as single-file bot implementation:
  ```python
  # Handlers
  async def start_handler(update, context)
  async def help_handler(update, context)
  async def photo_handler(update, context)  # → ocr_workflow()
  async def message_handler(update, context)  # → troubleshoot()

  # Response formatting
  def format_ocr_response(result: OCRResult) -> str
  def format_troubleshoot_response(result: TroubleshootResult) -> str

  # Bot setup
  async def setup_bot() -> Application
  def main()
  ```
- **WIRE** to existing workflows:
  - Photo → `rivet.workflows.ocr.ocr_workflow()`
  - Text → `rivet.workflows.troubleshoot.troubleshoot()`
- **ADD** production features:
  - Error handling with user-friendly messages
  - Logging with user_id context
  - Rate limiting (use config.TierLimits)
  - Admin commands
  - Typing indicators
- **USE** config for bot token: `config.telegram_bot_token`

**Target Location:** `rivet/integrations/telegram.py` (CREATE NEW)

**Dependencies:**
- python-telegram-bot (already in pyproject.toml)
- Import from existing workflows

---

### Round 8: Anthropic Integration → integrations/anthropic.py
**Expected Harvest:** Claude API call structure

**Current State:** `rivet/integrations/llm.py` ALREADY HANDLES CLAUDE
- Uses Anthropic SDK
- Proper error handling
- Multi-model support

**Integration Strategy:**
- **DECISION POINT:** Do we need separate anthropic.py?
  - **OPTION A:** Skip, use existing llm.py (RECOMMENDED)
  - **OPTION B:** Create standalone wrapper for direct Claude calls
- **IF CREATING:**
  - Extract Claude-specific logic from llm.py
  - Create `call_claude(system, user) -> str` wrapper
  - Use for non-OCR Claude calls
- **VALIDATE** no duplication with existing llm.py

**Target Location:** `rivet/integrations/anthropic.py` (OPTIONAL)

---

### Round 9: Rate Limiting & Usage Tracking → utils/rate_limiter.py
**Expected Harvest:** Query counting, rate limiting, tier enforcement

**Current State:** ❌ **NOT IMPLEMENTED** - Config has TierLimits but no enforcement

**Integration Strategy:**
- **CREATE** `rivet/utils/rate_limiter.py` from harvest block
- **STRUCTURE:**
  ```python
  class RateLimiter:
      async def check_limit(user_id: str, tier: str) -> bool
      async def increment_usage(user_id: str)
      async def get_usage_stats(user_id: str) -> Dict
      async def reset_daily_counts()
  ```
- **INTEGRATE** with:
  - Telegram handlers (check before processing)
  - Database or Redis for persistence
  - Config.TierLimits for limit values
- **FEATURES:**
  - Per-user query counting
  - Daily reset logic
  - Tier enforcement (beta=50/day, pro=1000/day, team=unlimited)
  - Usage statistics API
  - Rate limit exceeded messages

**Target Location:** `rivet/utils/rate_limiter.py` (CREATE NEW)

**Dependencies:**
- Redis or database for counter storage
- Config.TierLimits for tier definitions
- Async support for non-blocking checks

---

## 🎯 PRODUCTION-READY STANDARDS

Every harvest integration MUST meet these standards:

### 1. Type Hints
```python
async def troubleshoot(
    query: str,
    ocr_result: Optional[OCRResult] = None,
    user_id: Optional[str] = None,
) -> TroubleshootResult:
```

### 2. Error Handling
```python
try:
    result = await call_api()
except APIError as e:
    logger.error(f"API call failed: {e}", extra={"user_id": user_id})
    raise
```

### 3. Logging with Context
```python
logger.info(
    "OCR completed",
    extra={
        "user_id": user_id,
        "manufacturer": result.manufacturer,
        "processing_time_ms": result.processing_time_ms,
    }
)
```

### 4. Config-Based Settings
```python
# ❌ BAD
api_key = "sk-1234..."

# ✅ GOOD
from rivet.config import config
api_key = config.anthropic_api_key
```

### 5. Dataclasses for Structured Data
```python
from dataclasses import dataclass

@dataclass
class TroubleshootResult:
    answer: str
    route: str
    confidence: float
    # ... more fields
```

### 6. Async Where Appropriate
```python
# API calls, I/O operations
async def call_llm(prompt: str) -> str:
    async with session.post(...) as response:
        return await response.json()
```

---

## ✅ TESTING STRATEGY

After each harvest integration:

### 1. Import Validation
```bash
python -c "from rivet.workflows.ocr import detect_manufacturer; print('OK')"
```

### 2. Unit Tests
- Create/update tests in `tests/test_*.py`
- Mock external APIs
- Test error paths

### 3. Integration Tests
- Test workflow end-to-end
- Verify harvest logic matches existing behavior
- Check performance (no regressions)

### 4. Manual Testing
```bash
# Test telegram bot
python -m rivet.integrations.telegram
```

---

## 📝 HARVEST RECEPTION LOG

As harvest blocks arrive, I'll log them here:

### Round 1: Manufacturer Patterns
- **Status:** PENDING
- **Expected:** Regex patterns for vendors
- **Action:** TBD

### Round 2: Model/Serial Extraction
- **Status:** PENDING
- **Expected:** Vendor-specific patterns
- **Action:** TBD

### Round 3: OCR Prompt (ALL PROVIDERS)
- **Status:** PENDING
- **Expected:** Multi-provider vision prompts (Gemini, Claude, OpenAI, Groq)
- **Action:** Enhance llm.py prompts for all providers, not just Gemini

### Round 4: SME Prompts
- **Status:** PENDING
- **Expected:** 7 vendor prompts
- **Action:** Compare with existing, enhance if better

### Round 5: Vendor Keywords
- **Status:** PENDING
- **Expected:** Detection keywords
- **Action:** Merge into VENDOR_PATTERNS

### Round 6: Route Logic
- **Status:** PENDING
- **Expected:** Confidence thresholds
- **Action:** Validate against existing

### Round 7: Telegram Handlers ⭐ PRIMARY BUILD
- **Status:** PENDING
- **Expected:** Complete bot implementation
- **Action:** CREATE rivet/integrations/telegram.py

### Round 8: Anthropic Integration
- **Status:** PENDING
- **Expected:** Claude API wrapper
- **Action:** Evaluate if needed (llm.py exists)

### Round 9: Rate Limiting ⭐ NEW
- **Status:** PENDING
- **Expected:** Usage tracking, rate limiting, tier enforcement
- **Action:** CREATE rivet/utils/rate_limiter.py

---

## 🚀 FINALIZATION CHECKLIST

After all harvest rounds complete:

- [ ] All imports resolve correctly
- [ ] No circular dependencies
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] All tests pass
- [ ] Telegram bot runs: `python -m rivet.integrations.telegram`
- [ ] Integration tests with real APIs (using test tokens)
- [ ] Load testing (simulate 100 concurrent users)
- [ ] Cost analysis (verify LLM router saves money)
- [ ] Documentation updated (README.md, SYSTEM_MAP.md)
- [ ] Git commit: "Phase 2 complete: Telegram integration + harvest blocks"

---

## 💡 BUILDER AGENT READY STATE

**I am now ready to receive harvest blocks.**

**When Harvester sends a harvest block:**
1. User pastes harvest block into conversation
2. I identify which round it corresponds to
3. I execute the integration strategy for that round
4. I report what was integrated and any issues
5. I wait for next harvest block

**Key principle:** Enhance existing code where possible, create new code only when necessary.

**Current priority:** Round 7 (Telegram Handlers) - This is the only major missing component.

---

**END BUILDER AGENT PLAN**
