# 🔄 RIVET EXTRACTION PIPELINE

## The Setup

```
TERMINAL 1                              TERMINAL 2
┌─────────────────────────┐            ┌─────────────────────────┐
│  HARVESTER AGENT        │            │  BUILDER AGENT          │
│  ~/Agent Factory/       │            │  ~/rivet-pro/           │
│                         │            │                         │
│  "Find OCR patterns"    │ ────────▶  │  "Here's the extract"   │
│  "Extract SME prompts"  │   paste    │  "Structure it right"   │
│  "Get route thresholds" │            │  "Make production-ready"│
└─────────────────────────┘            └─────────────────────────┘
```

---

# 🔍 HARVESTER AGENT PROMPT

Run this in Claude Code CLI inside `~/Agent Factory/`:

```
=== RIVET HARVESTER - EXTRACTION AGENT ===

ROLE:
You are the Harvester. You operate in the OLD Agent Factory codebase.
Your job: Find working code, extract it cleanly, output for the Builder.

WORKFLOW:
1. I tell you what to extract
2. You find it in the codebase
3. You clean it up (remove broken deps, simplify)
4. You output a clean "HARVEST BLOCK" I can paste to the Builder

HARVEST BLOCK FORMAT:
```
=== HARVEST: [Component Name] ===
SOURCE: [file path and lines]
WHAT: [brief description]

```python
[clean, standalone code]
```

NOTES FOR BUILDER:
- [any integration notes]
- [dependencies needed]
- [gotchas]
=== END HARVEST ===
```

RULES:
- Only extract code that WORKS
- Remove all broken imports/dependencies
- Simplify classes to functions where possible
- Keep the exact patterns/prompts that work
- Document where it came from

FIRST TASK - EXPLORE:
Show me the codebase structure so we know what we're working with:

```bash
find . -type f -name "*.py" -path "*/agent_factory/*" | head -50
ls -la agent_factory/
ls -la agent_factory/integrations/telegram/ 2>/dev/null
ls -la agent_factory/core/ 2>/dev/null
ls -la agent_factory/rivet_pro/ 2>/dev/null
```

Then I'll tell you what to harvest first.
```

---

# 🏗️ BUILDER AGENT PROMPT

Run this in Claude Code CLI inside `~/rivet-pro/` (create it first):

```
=== RIVET BUILDER - PRODUCTION ASSEMBLY ===

ROLE:
You are the Builder. You operate in the NEW rivet-pro repository.
Your job: Receive harvest blocks from the Harvester, structure them production-ready.

THE PRODUCT:
Rivet Pro - Industrial maintenance AI assistant
- Telegram bot
- Photo → Equipment detection (OCR)
- Question → 4-route troubleshooting
- Stripe payments + user onboarding

TARGET STRUCTURE:
```
rivet-pro/
├── pyproject.toml
├── rivet/
│   ├── __init__.py
│   ├── config.py              # All settings
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── ocr.py             # Photo → Equipment
│   │   └── troubleshoot.py    # Query → Answer (4-route)
│   ├── prompts/
│   │   └── __init__.py        # SME prompts
│   └── integrations/
│       ├── __init__.py
│       ├── telegram.py        # Bot (single file)
│       ├── anthropic.py       # Claude API
│       └── stripe.py          # Payments
└── tests/
```

WORKFLOW:
1. Harvester sends me a HARVEST BLOCK
2. I determine where it goes in the structure
3. I integrate it properly (imports, types, error handling)
4. I make it production-ready (logging, validation, tests)

PRODUCTION-READY MEANS:
- Type hints on all functions
- Proper error handling
- Logging with context
- No hardcoded values (use config)
- Dataclasses for structured data
- Async where appropriate

FIRST TASK - SETUP:
Create the repository structure:

```bash
# If repo doesn't exist
mkdir -p ~/rivet-pro
cd ~/rivet-pro
git init

# Create structure
mkdir -p rivet/{workflows,prompts,integrations,utils}
mkdir -p tests scripts
touch rivet/__init__.py
touch rivet/workflows/__init__.py
touch rivet/prompts/__init__.py
touch rivet/integrations/__init__.py

# Create pyproject.toml
```

Then create rivet/config.py with all the env vars needed.
Wait for harvest blocks from the Harvester.
```

---

# 📋 EXTRACTION SEQUENCE

## Round 1: Manufacturer Patterns

**Tell Harvester:**
```
HARVEST REQUEST: Manufacturer detection patterns

Find:
- All regex patterns for detecting equipment manufacturers
- Siemens, Rockwell, ABB, Schneider, Mitsubishi, Yaskawa, Danfoss, etc.
- The detection function

Look in:
- agent_factory/integrations/telegram/ocr/
- agent_factory/routers/
- Any file with "manufacturer" or "vendor" 

Output as HARVEST BLOCK.
```

**Give Builder the harvest block, then tell it:**
```
INTEGRATE: Manufacturer patterns

Put this in rivet/workflows/ocr.py
- Create Equipment dataclass
- Create detect_manufacturer(text) -> Optional[str]
- Make patterns a constant dict
- Add type hints
```

---

## Round 2: Model/Serial Extraction

**Tell Harvester:**
```
HARVEST REQUEST: Model and serial number extraction

Find:
- Regex patterns for extracting model numbers
- Regex patterns for extracting serial numbers
- Patterns for specific vendors (6ES7 for Siemens, 1756- for Rockwell, etc.)

Look in:
- Same OCR files
- Any file with "model" or "serial" patterns

Output as HARVEST BLOCK.
```

**Give Builder:**
```
INTEGRATE: Model/serial extraction

Add to rivet/workflows/ocr.py
- extract_model_number(text) -> Optional[str]
- extract_serial_number(text) -> Optional[str]
- Add vendor-specific patterns
```

---

## Round 3: OCR Prompt

**Tell Harvester:**
```
HARVEST REQUEST: Gemini Vision OCR prompt

Find:
- The exact prompt used for extracting text from equipment photos
- The Gemini API call structure
- Any image preprocessing

Look in:
- agent_factory/integrations/telegram/ocr/
- Files with "gemini" or "vision"

Output as HARVEST BLOCK.
```

**Give Builder:**
```
INTEGRATE: OCR prompt and Gemini call

Add to rivet/workflows/ocr.py
- extract_text_from_image(bytes) -> str
- Use the exact prompt that works
- Handle errors properly
```

---

## Round 4: SME Prompts

**Tell Harvester:**
```
HARVEST REQUEST: All SME prompts

Find:
- Siemens expert prompt
- Rockwell expert prompt  
- ABB expert prompt
- Schneider expert prompt
- Any other vendor prompts
- General troubleshooting prompt

Look in:
- agent_factory/rivet_pro/agents/
- Files with "prompt" or "system"

Output each prompt as separate HARVEST BLOCK.
```

**Give Builder:**
```
INTEGRATE: SME prompts

Put all prompts in rivet/prompts/__init__.py
- One constant per vendor: SIEMENS_PROMPT, ROCKWELL_PROMPT, etc.
- GENERAL_PROMPT for fallback
- get_sme_prompt(vendor) function
- List all supported vendors
```

---

## Round 5: Vendor Keywords

**Tell Harvester:**
```
HARVEST REQUEST: Vendor detection keywords

Find:
- Keywords that identify Siemens questions (simatic, s7, tia portal...)
- Keywords for Rockwell (controllogix, allen bradley, rslogix...)
- Keywords for all other vendors
- The detection function

Look in:
- agent_factory/routers/vendor_detector.py
- Orchestrator files
- Any file with vendor keyword lists

Output as HARVEST BLOCK.
```

**Give Builder:**
```
INTEGRATE: Vendor keywords

Put in rivet/workflows/troubleshoot.py
- VENDOR_KEYWORDS dict
- detect_vendor(query) -> Optional[str]
```

---

## Round 6: Route Logic

**Tell Harvester:**
```
HARVEST REQUEST: 4-route decision logic

Find:
- Confidence thresholds (when to use KB vs SME vs research)
- The decision tree/flow
- How routes A, B, C, D are determined

Look in:
- agent_factory/core/orchestrator.py
- Any file with "route" logic

Output as HARVEST BLOCK with exact thresholds.
```

**Give Builder:**
```
INTEGRATE: Route logic

Complete rivet/workflows/troubleshoot.py
- Route enum (A, B, C, D)
- Answer dataclass
- troubleshoot_workflow(query) -> Answer
- Use exact thresholds from harvest
```

---

## Round 7: Telegram Handlers

**Tell Harvester:**
```
HARVEST REQUEST: Telegram bot handlers

Find:
- /start handler
- /help handler
- Photo handler (calls OCR)
- Message handler (calls troubleshoot)
- Response formatting
- How the bot is configured

Look in:
- agent_factory/integrations/telegram/
- bot.py or handlers.py

Output as HARVEST BLOCK.
```

**Give Builder:**
```
INTEGRATE: Telegram bot

Create rivet/integrations/telegram.py (single file)
- All handlers
- Response formatting
- Bot setup function
- Wire to workflows
```

---

## Round 8: Anthropic Integration

**Tell Harvester:**
```
HARVEST REQUEST: Claude API calls

Find:
- How Claude is called
- Model used
- Max tokens
- Error handling

Look in:
- Any file with "anthropic" or "claude"

Output as HARVEST BLOCK.
```

**Give Builder:**
```
INTEGRATE: Claude API

Create rivet/integrations/anthropic.py
- call_claude(system, user) -> str
- Proper error handling
- Use config for API key
```

---

# 🔁 The Loop

```
1. You tell Harvester what to find
2. Harvester searches, extracts, outputs HARVEST BLOCK
3. You copy HARVEST BLOCK to Builder
4. Builder integrates it production-ready
5. Repeat for next component
```

## After All Rounds

Tell Builder:
```
FINALIZE:
1. Create tests for OCR detection
2. Create tests for vendor detection
3. Create run script
4. Verify all imports work
5. Test with: python -m rivet.integrations.telegram
```

---

# ⚡ Quick Commands

**Harvester - Find files:**
```bash
grep -r "PATTERN" agent_factory/ --include="*.py" -l
```

**Harvester - Show code:**
```bash
cat FILE | head -100
```

**Builder - Test imports:**
```bash
python -c "from rivet.workflows.ocr import ocr_workflow; print('OK')"
```

**Builder - Run bot:**
```bash
python -m rivet.integrations.telegram
```
