# RIVET Pro Build Specification
## Claude Code CLI Development Prompt

---

## Mission
Build RIVET Pro from scratch - an AI-powered industrial maintenance assistant that helps field technicians identify equipment and access documentation through photo-based interaction. Start with Telegram, architect for WhatsApp expansion.

---

## The User
**Who:** Industrial maintenance technicians in the field
**Where:** Standing in front of unfamiliar equipment - a drive, PLC, contactor, I/O card
**When:** They've troubleshot a problem down to a component and need the manual NOW
**Pain:** Currently takes multiple Google searches to find the right PDF manual

---

## Core Value Proposition
1. Snap a photo of any equipment nameplate/model tag
2. Bot OCRs it, identifies manufacturer + model
3. Bot finds the manual (from knowledge base OR web search)
4. Bot delivers the PDF
5. (Phase 2) Tech can chat with the manual to find specific info

---

## Architecture Requirements

### Platform Abstraction Layer
```
rivet_pro/
├── core/                      # Platform-agnostic business logic
│   ├── ocr/                   # Multi-provider OCR pipeline
│   │   ├── pipeline.py        # Fallback chain: Groq → Gemini → Claude → GPT-4o
│   │   └── extractors.py      # Nameplate data extraction
│   ├── knowledge/             # Knowledge base operations
│   │   ├── search.py          # Vector search for indexed manuals
│   │   ├── ingest.py          # Manual indexing pipeline
│   │   └── web_search.py      # Agentic web search for unknown manuals
│   ├── matching/              # Equipment identification
│   │   ├── classifier.py      # Manufacturer/model classification
│   │   └── fuzzy.py           # Fuzzy matching for partial reads
│   ├── reasoning/             # LLM-powered intelligence
│   │   ├── orchestrator.py    # Adaptive response generation
│   │   ├── troubleshoot.py    # Troubleshooting logic (Phase 2)
│   │   └── vibe_check.py      # Detect user intent/mood for response style
│   └── models/                # Pydantic models
│       ├── equipment.py       # Equipment, Manufacturer, Model
│       ├── user.py            # User, Subscription, History
│       └── interaction.py     # Message, Response, Feedback
├── adapters/                  # Platform-specific implementations
│   ├── telegram/
│   │   ├── bot.py             # python-telegram-bot v20+ async
│   │   ├── handlers.py        # Message/callback handlers
│   │   ├── keyboards.py       # Inline keyboard builders
│   │   └── media.py           # Photo/document handling
│   └── whatsapp/              # Future: PyWa implementation
│       ├── bot.py
│       ├── handlers.py
│       └── buttons.py
├── infra/
│   ├── database.py            # Neon PostgreSQL (asyncpg)
│   ├── redis.py               # Redis for caching/sessions
│   ├── storage.py             # S3/local for PDF storage
│   └── observability.py       # LangSmith tracing
├── config/
│   └── settings.py            # Pydantic settings from env
└── main.py                    # Application entrypoint
```

### Critical Design Principles

1. **NO SLASH COMMANDS** - The bot is conversational, not CLI-like
   - Use inline button menus for choices
   - Natural language interaction
   - `/start` only for initial registration, hidden from regular use

2. **LLM-Powered Adaptive Responses**
   - The orchestrator LLM reads message + user history
   - Classifies intent AND vibe (rushed vs exploratory)
   - Decides dynamically: buttons vs freeform, guided vs direct
   - Generates response AND UI elements

3. **Every Interaction Trains the System**
   - OCR confidence feedback: "Is this right?" → labeled training data
   - Manual selection from options → improves matching
   - Troubleshooting outcomes → builds diagnostic intelligence
   - Tribal knowledge annotations → expert knowledge capture

4. **Platform Agnostic Core**
   - All business logic in `core/` - no platform imports
   - Adapters are thin translation layers
   - Same logic must work for Telegram today, WhatsApp tomorrow

---

## Conversation Flows

### First Contact
```
User opens bot for first time
↓
Bot: "Hey, I'm RIVET. Send me a photo of any equipment nameplate 
     and I'll find you the manual. Try it now 👇"
     
     [No buttons - just an invitation to send a photo]
```

### Photo → Manual Flow (MVP)
```
User sends photo of nameplate
↓
Bot: [OCR processing indicator]
↓
IF high confidence match:
    Bot: "Got it - Siemens SINAMICS G120C, 2.2kW, 480V.
         Here's the manual:"
         [PDF attachment or link]
         
         [✓ Correct] [✗ Wrong equipment]
         
ELIF multiple possibilities:
    Bot: "I found a few matches. Which one is it?"
    
         [Siemens 6SL3210-1KE15-8UF2]
         [Siemens 6SL3210-1KE15-8AF2]  
         [None of these / Search manually]
         
ELIF low confidence:
    Bot: "The nameplate is hard to read. I can see it's a Siemens drive.
         Can you tell me the voltage - 230V or 480V?"
         
         [230V] [480V] [Let me take another photo]
         
ELIF no match found:
    Bot: "I couldn't find this one in my knowledge base or online.
         Want me to flag it so our team can track it down?"
         
         [Yes, flag it] [I'll find it myself]
```

### Feedback Capture
```
After delivering manual:
    Bot: "Did this manual help?"
    
         [👍 Yes] [👎 No] [💬 Add a note]
         
IF user clicks "Add a note":
    Bot: "What should other techs know about this equipment?"
    
    User types tribal knowledge
    
    Bot: "Got it. I'll remember that for next time. 🧠"
```

### Chat with Manual (Phase 2)
```
After manual delivered:
    User: "what does fault code F0021 mean"
    ↓
    Bot searches indexed manual + tribal knowledge
    ↓
    Bot: "F0021 is an overvoltage fault. The manual says to check:
         • DC link voltage
         • Braking resistor connection
         • Line voltage stability
         
         [From page 247 of the manual]
         
         💡 Tech note: 'On these units, F0021 is usually a loose 
            encoder cable, not actual overvoltage' - added by @mike_tech"
```

---

## Database Schema (Neon PostgreSQL)

```sql
-- Users and subscriptions
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE,
    whatsapp_id VARCHAR(20) UNIQUE,
    name VARCHAR(255),
    company VARCHAR(255),
    subscription_tier VARCHAR(20) DEFAULT 'free', -- free, pro, team
    team_id UUID REFERENCES teams(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ
);

CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255),
    owner_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Equipment knowledge base
CREATE TABLE manufacturers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    aliases TEXT[], -- ["ABB", "Asea Brown Boveri", "Baldor"]
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE equipment_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manufacturer_id UUID REFERENCES manufacturers(id),
    model_number VARCHAR(255) NOT NULL,
    model_aliases TEXT[],
    equipment_type VARCHAR(100), -- drive, plc, contactor, etc
    specifications JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE manuals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_model_id UUID REFERENCES equipment_models(id),
    title VARCHAR(500),
    file_url VARCHAR(1000),
    file_hash VARCHAR(64),
    page_count INT,
    indexed_at TIMESTAMPTZ,
    source VARCHAR(50), -- 'manufacturer', 'web_search', 'user_upload'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vector embeddings for semantic search (using pgvector)
CREATE TABLE manual_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manual_id UUID REFERENCES manuals(id),
    content TEXT,
    page_number INT,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tribal knowledge
CREATE TABLE tech_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_model_id UUID REFERENCES equipment_models(id),
    user_id UUID REFERENCES users(id),
    content TEXT NOT NULL,
    upvotes INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Interaction history (feeds CMMS)
CREATE TABLE interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    equipment_model_id UUID REFERENCES equipment_models(id),
    interaction_type VARCHAR(50), -- 'manual_lookup', 'troubleshoot', 'chat'
    ocr_raw_text TEXT,
    ocr_confidence FLOAT,
    user_confirmed BOOLEAN,
    outcome VARCHAR(50), -- 'resolved', 'escalated', 'abandoned'
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Manual request queue (for unfound manuals)
CREATE TABLE manual_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    ocr_text TEXT,
    manufacturer_guess VARCHAR(255),
    model_guess VARCHAR(255),
    photo_url VARCHAR(1000),
    status VARCHAR(20) DEFAULT 'pending', -- pending, found, unfindable
    resolved_manual_id UUID REFERENCES manuals(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_equipment_models_manufacturer ON equipment_models(manufacturer_id);
CREATE INDEX idx_manuals_equipment ON manuals(equipment_model_id);
CREATE INDEX idx_interactions_user ON interactions(user_id);
CREATE INDEX idx_interactions_equipment ON interactions(equipment_model_id);
CREATE INDEX idx_manual_chunks_embedding ON manual_chunks USING ivfflat (embedding vector_cosine_ops);
```

---

## Subscription Tiers

| Feature | Free | Pro $29/mo | Team $200/mo |
|---------|------|------------|--------------|
| Manual lookups | 10/month | Unlimited | Unlimited |
| PDF delivery | ✓ | ✓ | ✓ |
| Chat with PDF | ✗ | ✓ | ✓ |
| Chat with prints | ✗ | ✓ | ✓ |
| Personal history | 7 days | Forever | Forever |
| Personal CMMS | ✗ | ✓ | ✓ |
| Upload own docs | ✗ | 50/month | Unlimited |
| Tribal knowledge | View only | Add notes | Team-wide |
| PLC IO panel | ✗ | ✗ | ✓ |
| Seats | 1 | 1 | 10 |
| Shared KB | ✗ | ✗ | ✓ |

**Beta Mode:** All features unlocked for all users during testing.

---

## OCR Pipeline

Multi-provider fallback chain for reliability:

```python
class OCRPipeline:
    """
    Attempts OCR in order of cost/speed, falling back on failure.
    Each provider returns: {text, confidence, raw_response}
    """
    
    providers = [
        GroqVisionProvider(),      # Fast, cheap, good enough usually
        GeminiVisionProvider(),    # Better quality fallback
        ClaudeVisionProvider(),    # High quality
        GPT4oVisionProvider(),     # Last resort, expensive
    ]
    
    async def extract(self, image_bytes: bytes) -> OCRResult:
        for provider in self.providers:
            try:
                result = await provider.extract(image_bytes)
                if result.confidence > 0.7:
                    return result
            except ProviderError:
                continue
        
        return OCRResult(text="", confidence=0, error="All providers failed")
```

**Extraction prompt for nameplate analysis:**
```
Analyze this industrial equipment nameplate image. Extract:
- Manufacturer name
- Model number / Part number
- Serial number (if visible)
- Voltage rating
- Power rating (kW/HP)
- Any other specifications visible

Return as structured JSON. If any field is unclear or partially obscured, 
include your best guess with a confidence score.
```

---

## LLM Orchestrator

The brain that makes responses adaptive:

```python
class Orchestrator:
    """
    Analyzes user message + context and generates appropriate response.
    Decides both WHAT to say and HOW to present it (buttons, freeform, etc.)
    """
    
    async def process(
        self, 
        message: str,
        user: User,
        context: ConversationContext,
        ocr_result: Optional[OCRResult] = None
    ) -> Response:
        
        # Build prompt with all context
        prompt = self._build_prompt(message, user, context, ocr_result)
        
        # LLM decides intent, vibe, and response
        llm_response = await self.llm.generate(prompt)
        
        # Parse structured output
        return Response(
            text=llm_response.message,
            buttons=llm_response.suggested_buttons,  # Can be empty
            attachments=llm_response.files,
            follow_up_action=llm_response.next_action
        )
    
    def _build_prompt(self, ...):
        return f"""
You are RIVET, an AI assistant for industrial maintenance technicians.

## Current User
- Name: {user.name}
- Subscription: {user.subscription_tier}
- Recent equipment: {context.recent_equipment}
- Interaction style preference: {context.detected_style}

## Conversation History
{context.recent_messages}

## Current Message
{message}

## OCR Result (if photo was sent)
{ocr_result}

## Your Task
1. Understand what the technician needs
2. Detect their vibe (rushed/need-answer-now vs exploring/learning)
3. Respond appropriately:
   - If they need a quick answer, be direct
   - If they're exploring, offer options
   - If you're uncertain, ask ONE clarifying question
4. Decide if buttons would help or get in the way

Respond with:
- message: Your response text
- buttons: List of button labels (empty if not needed)
- vibe: detected user vibe
- confidence: your confidence in understanding their need
"""
```

---

## Environment Variables

```bash
# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_URL=
TELEGRAM_WEBHOOK_SECRET=

# WhatsApp (Future)
WHATSAPP_PHONE_ID=
WHATSAPP_TOKEN=
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_APP_SECRET=

# Database
DATABASE_URL=postgresql://...@...neon.tech/rivet_pro

# Redis
REDIS_URL=redis://...

# AI Providers (OCR Pipeline)
GROQ_API_KEY=
GOOGLE_API_KEY=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# Orchestrator LLM (pick one as primary)
ORCHESTRATOR_MODEL=claude-3-5-sonnet-20241022
ORCHESTRATOR_PROVIDER=anthropic

# Storage
S3_BUCKET=rivet-pro-manuals
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_ENDPOINT=  # Optional for non-AWS

# Observability
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=rivet-pro

# Feature Flags
BETA_MODE=true  # Unlock all features for all users
```

---

## Implementation Order

### Phase 1: Walking Skeleton (Week 1)
1. [ ] Project structure with all directories
2. [ ] Pydantic settings loading from env
3. [ ] Telegram bot that responds to any message with "I'm alive"
4. [ ] Database connection test
5. [ ] Basic logging setup

### Phase 2: Photo → Text (Week 1-2)
1. [ ] Photo handler receives image
2. [ ] OCR pipeline with Groq (single provider first)
3. [ ] Return extracted text to user
4. [ ] Add fallback providers

### Phase 3: Equipment Matching (Week 2)
1. [ ] Manufacturer classifier
2. [ ] Model number extraction and normalization
3. [ ] Database lookup for known equipment
4. [ ] Fuzzy matching for partial/unclear reads

### Phase 4: Manual Delivery (Week 2-3)
1. [ ] Manual storage and retrieval
2. [ ] PDF delivery via Telegram
3. [ ] Web search fallback for unknown equipment
4. [ ] Manual request queue for unfound items

### Phase 5: Feedback Loop (Week 3)
1. [ ] Inline keyboard for confirmation
2. [ ] "Is this correct?" feedback capture
3. [ ] Tribal knowledge note submission
4. [ ] Interaction logging to database

### Phase 6: Adaptive Intelligence (Week 3-4)
1. [ ] Orchestrator LLM integration
2. [ ] Vibe detection from message patterns
3. [ ] Dynamic button generation
4. [ ] Conversation context tracking

### Phase 7: Chat with Manual (Week 4+)
1. [ ] Manual chunking and embedding
2. [ ] Vector search setup (pgvector)
3. [ ] RAG pipeline for manual Q&A
4. [ ] Tribal knowledge injection into responses

---

## Testing Strategy

```python
# tests/core/test_ocr.py
async def test_ocr_extracts_siemens_nameplate():
    """Test OCR on a known Siemens drive nameplate image."""
    with open("tests/fixtures/siemens_g120c.jpg", "rb") as f:
        result = await ocr_pipeline.extract(f.read())
    
    assert result.confidence > 0.8
    assert "siemens" in result.text.lower()
    assert "6SL3210" in result.text or "G120" in result.text

# tests/core/test_matching.py
async def test_fuzzy_match_partial_model():
    """Test matching with partially obscured model number."""
    result = await matcher.find_equipment(
        manufacturer="Siemens",
        model_fragment="6SL32**-1KE15"
    )
    
    assert len(result.candidates) > 0
    assert result.candidates[0].confidence > 0.7

# tests/adapters/test_telegram.py
async def test_photo_handler_triggers_ocr():
    """Test that photo upload triggers OCR pipeline."""
    # Mock telegram update with photo
    # Assert OCR was called
    # Assert response was sent
```

---

## Commands to Start

```bash
# Create project
mkdir rivet-pro && cd rivet-pro
git init

# Setup Python environment
python -m venv .venv
source .venv/bin/activate

# Install core dependencies
pip install python-telegram-bot[webhooks,job-queue]
pip install anthropic openai google-generativeai groq
pip install asyncpg redis aiohttp
pip install pydantic pydantic-settings
pip install langsmith

# Create structure
mkdir -p rivet_pro/{core/{ocr,knowledge,matching,reasoning,models},adapters/{telegram,whatsapp},infra,config}
touch rivet_pro/__init__.py
touch rivet_pro/main.py

# Copy this spec into the repo
cp RIVET_PRO_BUILD_SPEC.md ./

# Start building
claude "Read RIVET_PRO_BUILD_SPEC.md and implement Phase 1: Walking Skeleton"
```

---

## Success Criteria

**MVP is complete when:**
1. Tech sends photo of nameplate → receives correct manual PDF
2. System handles "I don't know" gracefully with options
3. Feedback buttons work and log to database
4. Works reliably on Telegram

**Production ready when:**
1. 95%+ OCR accuracy on clear nameplates
2. < 10 second response time photo-to-manual
3. Graceful degradation when providers fail
4. Observable via LangSmith
5. Subscription tier enforcement works
6. WhatsApp adapter functional

---

## Notes for Claude Code

- **Start simple, iterate fast** - Get photo → response working first
- **Use python-telegram-bot v20+** - Async/await style, not the old callback style
- **Pydantic everywhere** - All data models, all configs
- **Test with real nameplates** - Grab photos from Google Images of Siemens/ABB/Rockwell nameplates
- **Log everything** - Every OCR result, every match attempt, every user interaction
- **Don't over-engineer** - No microservices, no Kubernetes, just clean Python that runs on a VPS

The goal is a working product that helps real technicians, not a perfect architecture diagram.
