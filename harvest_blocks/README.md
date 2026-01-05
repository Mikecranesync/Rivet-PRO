# HARVEST BLOCKS - Rivet Pro Phase 2 Completion

**Extraction Date:** 2026-01-03
**Source:** Agent Factory codebase (10,088 LOC production-ready code)
**Purpose:** Complete Telegram bot integration by extracting missing components

---

## Overview

These HARVEST BLOCKS contain production-ready code extracted from Agent Factory to complete Rivet Pro Phase 2. Each block is a self-contained module ready for integration.

**Current State:**
- ✅ Phase 2 routing logic complete (14 files, ~3,500 LOC)
- ❌ Missing: LLM text generation, OCR pipeline, Telegram integration
- ❌ Blocked: All SME agents can't run without text generation support

**Critical Path (2 hours to working bot):**
1. **HARVEST 1** - LLM Router text generation (30 min) - CRITICAL BLOCKER
2. **HARVEST 2** - Manufacturer patterns (15 min)
3. **HARVEST 3** - OCR pipeline (45 min)
4. **HARVEST 4** - Telegram bot (30 min)

**Optional Enhancements (30 min):**
5. **HARVEST 5** - Response synthesizer (citations, safety warnings)
6. **HARVEST 6** - Print analyzer (schematic analysis)

---

## Integration Sequence

### Phase 1: Unblock SME Agents (HARVEST 1)

**File:** `rivet/integrations/llm.py`
**Action:** Add text generation support
**Why critical:** All SME agents are blocked without this
**Instructions:** See `harvest_1_llm_router.md`

### Phase 2: Enhance Routing (HARVEST 2)

**File:** `rivet/workflows/sme_router.py`
**Action:** Add comprehensive manufacturer patterns
**Why important:** Better vendor detection = better SME routing
**Instructions:** See `harvest_2_manufacturer_patterns.md`

### Phase 3: Enable Photo Analysis (HARVEST 3)

**File:** `rivet/workflows/ocr.py` (NEW FILE)
**Action:** Create dual-provider OCR pipeline
**Why critical:** Telegram bot needs to process equipment photos
**Instructions:** See `harvest_3_ocr_pipeline.md`
**Dependencies:** Requires Pillow (`poetry add pillow`)

### Phase 4: Complete Telegram Integration (HARVEST 4)

**File:** `rivet/integrations/telegram.py` (NEW FILE)
**Action:** Create Telegram bot with photo handler
**Why critical:** This is the user interface
**Instructions:** See `harvest_4_telegram_bot.md`
**Dependencies:** Requires python-telegram-bot (`poetry add python-telegram-bot`)

### Phase 5: Enhance Response Quality (HARVEST 5 - OPTIONAL)

**Files:** All SME files (`rivet/prompts/sme/*.py`, `rivet/workflows/general.py`)
**Action:** Add citations, safety warnings, confidence badges
**Why nice-to-have:** Better UX, more professional responses
**Instructions:** See `harvest_5_response_synthesizer.md`

### Phase 6: Add Schematic Analysis (HARVEST 6 - OPTIONAL)

**File:** `rivet/workflows/print_analyzer.py` (NEW FILE)
**Action:** Create technical print/schematic analyzer
**Why nice-to-have:** Advanced feature for analyzing wiring diagrams
**Instructions:** See `harvest_6_print_analyzer.md`

---

## Validation Commands

After each phase:

```bash
# Phase 1: LLM Router
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
python -c "from rivet.integrations.llm import LLMRouter, ModelCapability, LLMResponse; print('✅ LLM Router OK')"

# Phase 2: Manufacturer Patterns
python -c "from rivet.workflows.sme_router import detect_manufacturer; print('✅ Vendor:', detect_manufacturer('Siemens S7-1200', None))"

# Phase 3: OCR Pipeline
python -c "from rivet.workflows.ocr import ocr_workflow; print('✅ OCR Pipeline OK')"

# Phase 4: Telegram Bot
python -c "from rivet.integrations.telegram import handle_photo; print('✅ Telegram Bot OK')"

# End-to-end test (send photo to bot)
# Should respond with equipment data + offer troubleshooting help
```

---

## Success Criteria

**Telegram bot is complete when:**
- ✅ User sends equipment photo → bot extracts manufacturer, model, fault code
- ✅ User asks question → bot routes to correct vendor SME
- ✅ Bot responds with troubleshooting guidance + safety warnings
- ✅ Confidence badges show (High/Medium/Low)
- ✅ Research triggered for low-confidence responses

**Expected timeline:** 2-2.5 hours for full implementation

---

## Notes for Claude Instance

**Read these files in order:**
1. `harvest_1_llm_router.md` - Start here, it unblocks everything else
2. `harvest_2_manufacturer_patterns.md`
3. `harvest_3_ocr_pipeline.md`
4. `harvest_4_telegram_bot.md`
5. `harvest_5_response_synthesizer.md` (optional)
6. `harvest_6_print_analyzer.md` (optional)

**Each file contains:**
- What to extract
- Where it goes (target file)
- Integration notes
- Complete code ready to copy/paste

**Pattern:**
- Read HARVEST file
- Follow integration instructions
- Test with validation command
- Move to next HARVEST

**If you get stuck:**
- All source code is in Agent Factory repo
- Files are production-tested (10,088 LOC)
- Each component works standalone
