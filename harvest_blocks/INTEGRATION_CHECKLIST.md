# INTEGRATION CHECKLIST - Rivet Pro Phase 2 Completion

**Location:** `C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\harvest_blocks\`
**Created:** 2026-01-03
**Total HARVEST BLOCKS:** 6 (4 critical, 2 optional)

---

## Quick Start

Open the Rivet-PRO project in Claude Code and tell it:

```
Read the harvest_blocks folder and implement HARVEST BLOCK 1 first.
After that works, proceed through HARVEST 2, 3, and 4 in order.
```

---

## Critical Path (2 hours → Working Telegram Bot)

### ☐ HARVEST 1: LLM Router Text Generation (30 min)
**Status:** NOT STARTED
**File:** `harvest_1_llm_router.md`
**Target:** `rivet/integrations/llm.py`
**Why critical:** Unblocks all SME agents

**Checklist:**
- [ ] Read `harvest_1_llm_router.md`
- [ ] Add `from enum import Enum` to imports
- [ ] Add `ModelCapability` enum
- [ ] Add `LLMResponse` dataclass
- [ ] Add `TEXT_GENERATION_MODELS` registry
- [ ] Add `generate()` method to `LLMRouter` class
- [ ] Test with validation command
- [ ] Verify all 7 SME files can import `ModelCapability`

**Test Command:**
```bash
python -c "from rivet.integrations.llm import LLMRouter, ModelCapability, LLMResponse; print('✅ LLM Router OK')"
```

---

### ☐ HARVEST 2: Manufacturer Detection Patterns (15 min)
**Status:** NOT STARTED
**File:** `harvest_2_manufacturer_patterns.md`
**Target:** `rivet/workflows/sme_router.py`
**Why important:** Improves vendor detection accuracy 70% → 95%

**Checklist:**
- [ ] Read `harvest_2_manufacturer_patterns.md`
- [ ] Replace `VENDOR_PATTERNS` dictionary with comprehensive version
- [ ] Replace `normalize_manufacturer()` function
- [ ] Enhance `detect_manufacturer_from_query()` with part number detection
- [ ] Test with validation commands

**Test Command:**
```bash
python -c "from rivet.workflows.sme_router import detect_manufacturer; print('✅ Siemens:', detect_manufacturer('Siemens S7-1200', None))"
```

---

### ☐ HARVEST 3: OCR Pipeline (45 min)
**Status:** NOT STARTED
**File:** `harvest_3_ocr_pipeline.md`
**Target:** `rivet/workflows/ocr.py` (NEW FILE)
**Why critical:** Enables Telegram bot to process photos

**Checklist:**
- [ ] Read `harvest_3_ocr_pipeline.md`
- [ ] Install Pillow: `poetry add pillow`
- [ ] Create `rivet/workflows/ocr.py` with complete file content
- [ ] Create `rivet/models/ocr.py` with `OCRResult` dataclass (if doesn't exist)
- [ ] Test imports
- [ ] Test with real equipment photo (optional)

**Test Command:**
```bash
python -c "from rivet.workflows.ocr import ocr_workflow, validate_image_quality; print('✅ OCR Pipeline OK')"
```

---

### ☐ HARVEST 4: Telegram Bot Integration (30 min)
**Status:** NOT STARTED
**File:** `harvest_4_telegram_bot.md`
**Target:** `rivet/integrations/telegram.py` (NEW FILE)
**Why critical:** This is the user interface

**Checklist:**
- [ ] Read `harvest_4_telegram_bot.md`
- [ ] Install python-telegram-bot: `poetry add python-telegram-bot`
- [ ] Create `rivet/integrations/telegram.py` with complete file content
- [ ] Add `TELEGRAM_BOT_TOKEN` to `.env` file
- [ ] Test imports
- [ ] Run bot: `python -m rivet.integrations.telegram`
- [ ] Send test photo to bot

**Test Command:**
```bash
python -c "from rivet.integrations.telegram import create_bot_application; print('✅ Telegram Bot OK')"
```

---

## Optional Enhancements (30 min)

### ☐ HARVEST 5: Response Synthesizer (20 min)
**Status:** NOT STARTED
**File:** `harvest_5_response_synthesizer.md`
**Target:** `rivet/utils/response_formatter.py` (NEW FILE) + all SME files
**Why nice-to-have:** Professional UX with badges, citations, safety warnings

**Checklist:**
- [ ] Read `harvest_5_response_synthesizer.md`
- [ ] Create `rivet/utils/response_formatter.py`
- [ ] Create `rivet/utils/__init__.py`
- [ ] Update all 8 SME files to use `synthesize_response()`
- [ ] Test formatting

**Test Command:**
```bash
python -c "from rivet.utils.response_formatter import synthesize_response; print('✅ Formatter OK')"
```

---

### ☐ HARVEST 6: Print Analyzer (30 min)
**Status:** NOT STARTED
**File:** `harvest_6_print_analyzer.md`
**Target:** `rivet/workflows/print_analyzer.py` (NEW FILE)
**Why nice-to-have:** Advanced feature for schematic analysis

**Checklist:**
- [ ] Read `harvest_6_print_analyzer.md`
- [ ] Create `rivet/workflows/print_analyzer.py`
- [ ] Integrate with `telegram.py` photo handler (schematic detection)
- [ ] Test with sample schematic

**Test Command:**
```bash
python -c "from rivet.workflows.print_analyzer import PrintAnalyzer; print('✅ Print Analyzer OK')"
```

---

## Integration Order

**DO THIS IN ORDER:**

1. ✅ **Read README.md first** - Understand the overall strategy
2. 🔴 **HARVEST 1** - CRITICAL BLOCKER - Do this first!
3. 🟡 **HARVEST 2** - Quick win, improves accuracy
4. 🔴 **HARVEST 3** - CRITICAL - OCR pipeline
5. 🔴 **HARVEST 4** - CRITICAL - Telegram bot
6. 🟢 **Test end-to-end** - Send photo to bot, verify it works
7. ⚪ **HARVEST 5** (optional) - Response formatting
8. ⚪ **HARVEST 6** (optional) - Print analyzer

**Never skip HARVEST 1!** Everything else depends on it.

---

## Success Criteria

### Phase 2 Complete When:

**Functional Requirements:**
- ✅ User sends equipment photo to Telegram bot
- ✅ Bot extracts manufacturer, model, fault code
- ✅ Bot responds within 5 seconds
- ✅ User asks question about equipment
- ✅ Bot routes to correct vendor SME (Siemens, Rockwell, etc.)
- ✅ Bot returns troubleshooting guidance
- ✅ Safety warnings displayed

**Technical Requirements:**
- ✅ LLM router supports text generation (ModelCapability, generate())
- ✅ OCR pipeline works with dual providers (GPT-4o → Gemini)
- ✅ Manufacturer detection 95%+ accurate
- ✅ All 7 vendor SME prompts working
- ✅ Tests pass (`test_troubleshoot.py`, `test_routing.py`)

**User Experience:**
- ✅ /start command shows welcome message
- ✅ /help command shows instructions
- ✅ Image quality errors handled gracefully
- ✅ Response time < 5 seconds per photo

---

## Validation Commands (Run After All Integration)

```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO

# 1. Imports
python -c "from rivet.integrations.llm import ModelCapability, LLMResponse; print('✅ LLM OK')"
python -c "from rivet.workflows.sme_router import detect_manufacturer; print('✅ Router OK')"
python -c "from rivet.workflows.ocr import ocr_workflow; print('✅ OCR OK')"
python -c "from rivet.integrations.telegram import create_bot_application; print('✅ Bot OK')"

# 2. Vendor detection
python -c "from rivet.workflows.sme_router import detect_manufacturer; print(detect_manufacturer('Siemens S7-1200', None))"

# 3. Run tests
poetry run pytest tests/test_troubleshoot.py -v
poetry run pytest tests/test_routing.py -v

# 4. Start bot (requires TELEGRAM_BOT_TOKEN in .env)
python -m rivet.integrations.telegram
```

---

## Environment Variables Needed

Add to `.env`:

```bash
# LLM Providers (at least one required)
GROQ_API_KEY=your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

**How to get tokens:**
- Groq: https://console.groq.com/
- Gemini: https://ai.google.dev/
- Anthropic: https://console.anthropic.com/
- OpenAI: https://platform.openai.com/
- Telegram: Message @BotFather on Telegram

---

## Dependencies to Install

```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO

# HARVEST 3 - OCR
poetry add pillow

# HARVEST 4 - Telegram
poetry add python-telegram-bot

# Verify all dependencies
poetry install
```

---

## Timeline Estimate

| Phase | Duration | Cumulative |
|-------|----------|------------|
| HARVEST 1 | 30 min | 30 min |
| HARVEST 2 | 15 min | 45 min |
| HARVEST 3 | 45 min | 1h 30min |
| HARVEST 4 | 30 min | 2h 00min |
| **Testing** | 15 min | **2h 15min** |
| HARVEST 5 (opt) | 20 min | 2h 35min |
| HARVEST 6 (opt) | 30 min | 3h 05min |

**Critical path: 2 hours** (HARVEST 1-4 + testing)
**Full feature set: 3 hours** (all HARVEST blocks)

---

## Troubleshooting

### Import Error: Cannot import ModelCapability
**Cause:** HARVEST 1 not completed
**Fix:** Complete HARVEST 1 first, it unblocks everything else

### OCR fails with "Pillow not found"
**Cause:** Pillow not installed
**Fix:** `poetry add pillow`

### Telegram bot won't start
**Cause:** Missing TELEGRAM_BOT_TOKEN
**Fix:** Add token to `.env` file

### Low manufacturer detection accuracy
**Cause:** HARVEST 2 not integrated
**Fix:** Replace VENDOR_PATTERNS with comprehensive version

---

## Next Steps After Completion

1. **Deploy bot** - Railway.app, Render.com, or AWS
2. **Add monitoring** - Sentry for error tracking
3. **Add analytics** - Track usage, popular vendors
4. **Phase 3** - Knowledge base integration (kb_search.py)
5. **Documentation** - Update README.md with Phase 2 details

---

## Questions?

Each HARVEST BLOCK file contains:
- Complete code ready to copy/paste
- Integration instructions
- Validation commands
- Dependencies needed
- Notes and gotchas

**Start with HARVEST 1 and work through in order!**
