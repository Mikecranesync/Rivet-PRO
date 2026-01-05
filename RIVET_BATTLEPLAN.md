# RIVET PRO: HYBRID BATTLE PLAN
## Revenue + Demo in Parallel — The Path to Dollars

**Read this first. Every session. No exceptions.**

---

## The Strategy in One Paragraph

We run two parallel tracks for six weeks. Track One ships a production Telegram bot that real technicians pay for. Track Two builds a demo rig with Factory IO and PLC integration for an investor video. They share the same AI core but serve different purposes. Track One proves the market exists. Track Two shows where we're going. Together, they tell the story investors want to hear: "We have customers AND a vision."

---

## The Golden Rules

### 1. Revenue Comes First
If you have to choose between a production feature and a demo feature, ship the production feature. Paying customers > impressive demos.

### 2. Read-Only for Production, Write-OK for Demo Rig
Any code that touches real customer equipment is READ-ONLY. No exceptions. The demo rig with YOUR PLC can have write capabilities for the video, but that code never ships to customers.

### 3. Every Interaction Trains the System
Log everything. Every photo, every query, every manual lookup. This data is gold for the investor pitch AND for making the product better.

### 4. Ship Working Code Daily
No week-long development cycles. Something should be deployable every single day. Small commits, fast iterations.

### 5. The User is a Technician with Greasy Hands
Every feature must work on a phone, in a factory, over spotty WhatsApp. If it requires a desktop or good wifi, it's wrong.

---

## Timeline Overview

```
Week 1-2: TRACK ONE — Ship the Telegram Bot (Revenue)
Week 1-2: TRACK TWO — Factory IO + PLC Demo Rig (Parallel)
Week 3-4: TRACK ONE — WhatsApp Adapter + Paying Customers
Week 3-4: TRACK TWO — Claude Diagnostic Engine Integration
Week 5-6: TRACK ONE — Self-Learning KB + Subscription Enforcement
Week 5-6: TRACK TWO — Shoot the Demo Video
```

---

# TRACK ONE: PRODUCTION (Revenue-Generating)

This is the product that makes money. Prioritize this always.

## Week 1-2: Core Telegram Bot

### What We're Building
A Telegram bot that maintenance technicians use to:
1. Send a photo of equipment nameplate
2. Get back the correct manual/documentation
3. Ask follow-up troubleshooting questions

### User Flow
```
Tech sends photo
    ↓
Bot immediately replies: "🔍 Analyzing nameplate..."
    ↓
OCR extracts: Manufacturer, Model, Serial
    ↓
Bot updates message: "Found: Allen-Bradley PowerFlex 525"
    ↓
KB lookup finds manual
    ↓
Bot updates: "Here's the manual and common troubleshooting steps..."
    ↓
Tech can ask follow-up questions in natural language
```

### Streaming Message Updates (Critical for UX)
Users must see activity immediately. Never leave them staring at nothing.

```python
# Pseudocode for streaming updates
async def handle_photo(update):
    msg = await bot.send_message("🔍 Analyzing nameplate...")
    
    # OCR happens
    result = await ocr_pipeline(photo)
    await bot.edit_message(msg, f"Found: {result.manufacturer} {result.model}...")
    
    # KB lookup happens
    manual = await kb_lookup(result)
    await bot.edit_message(msg, f"Found: {result.manufacturer} {result.model}\n\n📖 Loading manual...")
    
    # Final response
    response = await generate_response(result, manual)
    await bot.edit_message(msg, response)
```

### OCR Pipeline (Cost-Optimized)
```
Photo
  ↓
Groq Vision (fast, cheap) ──→ confidence ≥ 80%? → Use result
  ↓ no
Gemini Flash (better) ──→ confidence ≥ 80%? → Use result
  ↓ no
Claude Sonnet (accurate) ──→ confidence ≥ 80%? → Use result
  ↓ no
GPT-4o (last resort) → Use result regardless
```

### Success Criteria Week 2
- [ ] Bot deployed and responding to photos
- [ ] OCR pipeline working with fallback providers
- [ ] Streaming message updates feel snappy
- [ ] 10+ real technicians testing (friends, contacts, anyone)
- [ ] Basic analytics: queries per day, OCR success rate

### Files to Create
```
rivet-pro/
├── src/
│   ├── bot/
│   │   ├── telegram_adapter.py      # Webhook handler
│   │   ├── message_streamer.py      # Edit messages as response builds
│   │   └── handlers.py              # Photo, text, command handlers
│   ├── ocr/
│   │   ├── pipeline.py              # Multi-provider OCR with fallback
│   │   ├── providers/
│   │   │   ├── groq.py
│   │   │   ├── gemini.py
│   │   │   ├── claude.py
│   │   │   └── openai.py
│   │   └── normalizer.py            # Standardize manufacturer names
│   ├── knowledge/
│   │   ├── kb_lookup.py             # Find manuals by equipment
│   │   └── manual_store.py          # Where manuals live
│   └── config.py                    # All settings, API keys, etc.
├── tests/
│   ├── test_ocr_pipeline.py
│   └── test_telegram_flow.py
└── requirements.txt
```

---

## Week 3-4: WhatsApp + First Paying Customers

### What We're Adding
- WhatsApp Business API adapter (same core, different transport)
- Subscription management (Free tier limits, Pro tier unlock)
- User onboarding flow
- Basic CMMS data integration (optional, if time permits)

### WhatsApp Adapter
Same pattern as Telegram, just different API:

```python
# The core doesn't change
async def process_message(message: UnifiedMessage) -> Response:
    # This is platform-agnostic
    ...

# Only the adapters differ
class TelegramAdapter:
    async def receive(self, update) -> UnifiedMessage: ...
    async def send(self, response: Response): ...

class WhatsAppAdapter:
    async def receive(self, webhook) -> UnifiedMessage: ...
    async def send(self, response: Response): ...
```

### Subscription Tiers

| Tier | Price | Limits |
|------|-------|--------|
| Beta (Free) | $0 | 10 lookups/month |
| Pro | $29/month | Unlimited lookups, chat-with-PDF |
| Team | $200/month | Everything + PLC Gateway (future) |

### Subscription Enforcement
```python
async def check_usage(user_id: str) -> bool:
    user = await get_user(user_id)
    if user.tier == "free" and user.monthly_lookups >= 10:
        await send_upgrade_prompt(user_id)
        return False
    return True
```

### Onboarding Flow
First message from new user:
```
Welcome to RIVET Pro! 🔧

I help maintenance technicians find manuals and troubleshoot equipment faster.

Send me a photo of any equipment nameplate and I'll identify it and find the documentation.

You're on the free tier (10 lookups/month). 
Upgrade to Pro for unlimited access: [link]

What equipment do you need help with today?
```

### Success Criteria Week 4
- [ ] WhatsApp adapter deployed and working
- [ ] Subscription system enforcing limits
- [ ] Stripe/payment integration for Pro tier
- [ ] 50+ users across Telegram and WhatsApp
- [ ] 5-10 paying Pro customers
- [ ] User feedback collected (what do they actually need?)

### Files to Add
```
rivet-pro/
├── src/
│   ├── bot/
│   │   ├── whatsapp_adapter.py      # NEW
│   │   ├── unified_message.py       # NEW - platform-agnostic message format
│   │   └── onboarding.py            # NEW
│   ├── billing/
│   │   ├── subscription.py          # Tier management
│   │   ├── stripe_integration.py    # Payment processing
│   │   └── usage_tracker.py         # Count lookups per user
│   └── database/
│       ├── models.py                # User, Subscription, Usage models
│       └── migrations/              # Schema changes
```

---

## Week 5-6: Self-Learning KB + Production Hardening

### What We're Adding
- Knowledge base that fills its own gaps
- Confidence tracking (how sure are we about each answer?)
- Production monitoring and alerting
- Preparing for scale

### Self-Learning Knowledge Base

When the system can't find a manual:
```
1. Log the gap (manufacturer, model, what user asked)
2. Queue a research task
3. Research agent searches web for documentation
4. Human reviews and approves (or AI auto-approves if confidence high)
5. KB updated, next user gets the answer
```

```python
async def handle_kb_miss(equipment: Equipment, user_query: str):
    # Log the gap
    await log_kb_gap(equipment, user_query)
    
    # Tell user we're learning
    await send_message(
        "I don't have documentation for this equipment yet, "
        "but I'm researching it now. I'll know next time!"
    )
    
    # Queue background research
    await research_queue.add(ResearchTask(
        equipment=equipment,
        priority=calculate_priority(equipment),  # Popular = higher priority
    ))
```

### Confidence Tracking
Every answer includes a confidence score:
```python
class DiagnosticResponse:
    answer: str
    confidence: float  # 0.0 to 1.0
    sources: list[str]
    precedent_count: int  # How many similar cases we've seen
```

Confidence formula:
```
base_confidence = model_confidence * source_quality
historical_boost = min(0.3, log10(precedent_count + 1) * 0.15)
final_confidence = base_confidence + historical_boost
```

Display to user:
- "I'm 95% confident this is the issue (seen 47 similar cases)"
- "I'm 60% confident - this is a new pattern for me"

### Production Hardening
- Health check endpoints
- Error alerting to Slack
- Request logging for debugging
- Rate limiting per user
- Graceful degradation (if OCR fails, ask user to type model number)

### Success Criteria Week 6
- [ ] KB gap detection and auto-research working
- [ ] Confidence scores displayed to users
- [ ] 100+ total users
- [ ] 15-20 paying customers
- [ ] Zero unhandled crashes in 48 hours
- [ ] Monitoring dashboard showing key metrics

---

# TRACK TWO: DEMO RIG (Investor Video)

This runs in parallel with Track One. It's for the pitch, not for customers.

## Week 1-2: Factory IO + PLC Foundation

### What We're Building
A demo environment on YOUR hardware that shows:
- Real PLC running conveyor logic
- Factory IO visualizing the process
- AI reading PLC state and diagnosing faults

### Hardware Setup
```
┌─────────────────┐      Ethernet      ┌─────────────────┐
│  Allen-Bradley  │◄──────────────────►│  Your Computer  │
│  Micro820 PLC   │                    │                 │
│  (or Siemens)   │                    │  - Python App   │
└─────────────────┘                    │  - Factory IO   │
                                       │  - Claude API   │
                                       └─────────────────┘
```

### Conveyor Logic (Ladder)
Simple 3-stage process for demo purposes:

**Stage 1 - FEED:**
- Start button pressed → Motor 1 runs
- Part detector triggers after 5 seconds

**Stage 2 - PROCESS:**
- Part arrives → Motor 2 runs
- Pressure must be ≥ 80 bar
- Process time: 8 seconds

**Stage 3 - EJECT:**
- Timer expires → Pneumatic fires for 1 second
- Counter increments

**Fault Conditions (for demo):**
- Pressure drop below 80 bar → Fault 001
- Door open → Fault 002
- Temperature > 60°C → Fault 003

### I/O Mapping
```
INPUTS:
I:0/0 - Start Button
I:0/1 - Stop Button
I:0/2 - Part Detect Stage 1
I:0/3 - Part Detect Stage 2
I:0/4 - Part Detect Stage 3
I:0/5 - Door Safety Switch
AI:0  - Pressure Transducer (0-100 bar)
AI:1  - Temperature Sensor (0-100°C)

OUTPUTS:
O:0/0 - Motor 1 (Feed)
O:0/1 - Motor 2 (Process)
O:0/2 - Motor 3 (Eject belt)
O:0/3 - Pneumatic Eject Solenoid
O:0/4 - Fault Light (Red)
O:0/5 - Status Light (Green)
```

### Factory IO Integration
Connection via OPC UA or Modbus TCP:

```python
class FactoryIOBridge:
    async def sync_plc_to_sim(self, plc_state: PLCState):
        """Send real PLC outputs to Factory IO inputs"""
        await self.factory_io.write("Motor1", plc_state.motor1_run)
        await self.factory_io.write("Motor2", plc_state.motor2_run)
        await self.factory_io.write("Pressure", plc_state.pressure)
        
    async def sync_sim_to_plc(self, sim_state: SimState):
        """Send Factory IO outputs to real PLC inputs (for testing)"""
        # Only used in simulation mode, not production
        await self.plc.write("PartDetect1", sim_state.part_at_stage1)
```

### Demo Rig vs Production: THE WALL

```
┌─────────────────────────────────────────────────────────────┐
│                      DEMO RIG ONLY                          │
│                                                             │
│   ┌─────────┐     ┌─────────────┐     ┌─────────────────┐  │
│   │ Your    │◄───►│ Factory IO  │◄───►│ PLC Write       │  │
│   │ PLC     │     │ Simulation  │     │ Commands OK     │  │
│   └─────────┘     └─────────────┘     └─────────────────┘  │
│                                                             │
│   This code NEVER ships to customers                        │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ SHARED: AI Core, OCR, KB
                           │
┌─────────────────────────────────────────────────────────────┐
│                      PRODUCTION                             │
│                                                             │
│   ┌─────────┐     READ      ┌─────────────────────────────┐│
│   │Customer │────ONLY──────►│ PLC Gateway (Trace Recorder)││
│   │ PLC     │               │ NO WRITE COMMANDS EVER      ││
│   └─────────┘               └─────────────────────────────┘│
│                                                             │
│   This is what customers get                                │
└─────────────────────────────────────────────────────────────┘
```

### Success Criteria Week 2 (Demo Rig)
- [ ] PLC running conveyor logic
- [ ] Factory IO visualizing belt movement
- [ ] Python reading PLC state every 100ms
- [ ] Can manually inject faults (drop pressure, open door)
- [ ] Fault state visible in both PLC and simulation

### Files for Demo Rig
```
rivet-demo/                          # SEPARATE from production!
├── plc/
│   ├── conveyor_logic.L5X          # Ladder logic export
│   ├── io_mapping.json             # Tag addresses
│   └── fault_codes.json            # What each fault means
├── factory_io/
│   ├── conveyor_scene.factoryio    # Simulation scene file
│   └── tag_mapping.json            # Factory IO ↔ PLC mapping
├── src/
│   ├── plc_interface.py            # Read/write to PLC
│   ├── factory_io_bridge.py        # Sync simulation
│   ├── fault_injector.py           # Trigger faults for demo
│   └── state_recorder.py           # Log PLC state over time
└── README.md                        # How to set up demo rig
```

---

## Week 3-4: Claude Diagnostic Engine

### What We're Building
Claude analyzes PLC state + maintenance history and explains what's wrong.

### Input to Claude
```json
{
  "timestamp": "2026-01-15T14:23:07Z",
  "plc_state": {
    "motor1_run": true,
    "motor2_run": false,
    "pressure_bar": 62,
    "temperature_c": 58,
    "fault_code": "001",
    "door_safe": true,
    "parts_processed": 47
  },
  "fault_history": [
    {"time": "14:20", "code": "001", "pressure": 65},
    {"time": "14:15", "code": "001", "pressure": 68}
  ],
  "maintenance_history": {
    "last_seal_replacement": "21 days ago",
    "valve_model": "Moog servo X123",
    "similar_faults_past_60_days": 3
  },
  "operator_question": "Why does my conveyor keep faulting?"
}
```

### Claude System Prompt
```
You are RIVET, an expert industrial maintenance AI. You diagnose equipment failures by analyzing PLC data, maintenance history, and fault patterns.

Your responses follow this structure:

## DIAGNOSIS
[One-sentence summary of what's wrong]

## CONFIDENCE
[Percentage] - [Brief explanation of why]

## ROOT CAUSE ANALYSIS
- [Evidence point 1]
- [Evidence point 2]
- [Evidence point 3]

## RECOMMENDED ACTIONS
1. [Action] - [Risk level] - [Time estimate]
2. [Action] - [Risk level] - [Time estimate]
3. [Action] - [Risk level] - [Time estimate]

## FOR THE TECHNICIAN
[Plain-language explanation a floor technician would understand]

Always:
- Reference specific data points from the PLC state
- Note patterns in fault history
- Consider maintenance history context
- Rank recommendations by safety and likelihood of success
- Speak like an experienced maintenance supervisor, not a manual
```

### Simulation Validation Loop (Demo Only)
Before recommending an action, simulate it:

```python
async def validate_action_in_simulation(action: ProposedAction, current_state: PLCState):
    """Run proposed action in Factory IO before recommending to user"""
    
    # Save current state
    snapshot = await factory_io.save_state()
    
    # Apply proposed action
    await factory_io.apply_action(action)
    
    # Run simulation for 60 seconds
    result = await factory_io.simulate(duration_seconds=60)
    
    # Check if it worked
    validation = ValidationResult(
        success=result.fault_cleared,
        final_pressure=result.pressure,
        side_effects=result.detect_side_effects(),
        recovery_time=result.time_to_normal,
    )
    
    # Restore original state
    await factory_io.restore_state(snapshot)
    
    return validation
```

### Success Criteria Week 4 (Demo Rig)
- [ ] Claude receiving PLC state and returning diagnoses
- [ ] Diagnoses include confidence scores
- [ ] Simulation validation working (propose → simulate → confirm)
- [ ] Can demonstrate fault injection → diagnosis → fix recommendation

---

## Week 5-6: Demo Video Production

### The 90-Second Video Structure

**0:00-0:15 — The Problem (Hook)**
- Shot: Technician looking frustrated at faulted machine
- Voiceover: "When equipment fails, technicians waste hours hunting for manuals and guessing at fixes."

**0:15-0:35 — Magic Moment 1: Voice Query**
- Shot: Tech speaks into phone via Telegram voice message
- "Hey RIVET, why does my conveyor keep faulting on pressure?"
- Show response appearing with streaming updates

**0:35-0:55 — Magic Moment 2: AI Diagnosis**
- Shot: Close-up of phone showing Claude's diagnosis
- Highlight: Confidence score, root cause, recommended action
- Voiceover: "RIVET analyzed the PLC data, maintenance history, and found the pattern."

**0:55-1:10 — Magic Moment 3: Simulation**
- Shot: Factory IO screen showing simulation running
- Voiceover: "Before recommending a fix, RIVET simulates it to make sure it's safe."
- Show: Pressure recovering in simulation

**1:10-1:20 — Magic Moment 4: Real Execution (Demo Rig Only)**
- Shot: Real PLC lights, motor running
- Voiceover: "With technician approval, RIVET can execute the fix on real equipment."
- Show: Status light goes from red to green

**1:20-1:30 — Magic Moment 5: Traction**
- Shot: Dashboard showing metrics
- Text overlay: "127 technicians • 340 faults diagnosed • 94% accuracy"
- Voiceover: "And it's already being used in factories across Latin America."

**1:30-1:35 — The Ask**
- Shot: Logo + contact info
- Voiceover: "RIVET. The maintenance AI that learns your equipment."

### Shot List
```
□ Wide shot: Factory floor / workshop with equipment
□ Close-up: Technician's hands on phone
□ Screen recording: Telegram conversation with RIVET
□ Screen recording: Factory IO simulation running
□ Close-up: Real PLC with status lights
□ Close-up: Motor starting/stopping
□ Dashboard: Metrics screen (can be mocked up)
□ Logo animation: Simple RIVET logo reveal
```

### Equipment Needed
- Phone with Telegram (for voice demo)
- Tripod or stable surface
- Lapel mic (phone mic is usually too quiet)
- Ring light or good natural lighting
- Your PLC demo rig running
- Factory IO on a monitor visible in shot
- Second monitor showing Telegram conversation (optional)

### Success Criteria Week 6 (Demo)
- [ ] All 5 magic moments captured on video
- [ ] Video edited to exactly 90 seconds
- [ ] Text overlays for clarity
- [ ] Background music (royalty-free)
- [ ] Exported for Twitter/LinkedIn (square or 16:9)
- [ ] Ready to send to investors

---

# INTEGRATION: Where Both Tracks Connect

The demo rig and production system share core components:

```
┌────────────────────────────────────────────────────────────────┐
│                        SHARED CORE                              │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ OCR Pipeline│  │ Claude API  │  │ Knowledge Base          │ │
│  │ (all provs) │  │ (diagnosis) │  │ (manuals, fault history)│ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ LangGraph Workflows (routing, orchestration)            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────┬──────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐
│   PRODUCTION    │ │   DEMO RIG      │ │   FUTURE: Customer      │
│                 │ │                 │ │   PLC Gateway           │
│ Telegram Bot    │ │ Factory IO      │ │                         │
│ WhatsApp Bot    │ │ Real PLC        │ │ READ-ONLY traces        │
│ Manual Lookup   │ │ Write Commands  │ │ Live diagnostics        │
│ Subscriptions   │ │ Simulation Val  │ │ No write ever           │
└─────────────────┘ └─────────────────┘ └─────────────────────────┘
     SHIPS NOW         FOR VIDEO            AFTER FUNDING
```

---

# DAILY WORKFLOW FOR CLAUDE CODE CLI

## Starting a Session

1. **Read this document first.** Every time.

2. **Check which track you're working on:**
   - Production (rivet-pro/) → Revenue features
   - Demo (rivet-demo/) → Video features

3. **Check the current week's success criteria.** What's not done?

4. **Pick ONE thing to ship today.** Not three things. One thing.

5. **Ship it.** Commit, deploy, verify it works.

## Ending a Session

1. **Update progress in a CHANGELOG or TODO.**

2. **Note any blockers for next session.**

3. **Commit everything.** No uncommitted work overnight.

---

# METRICS TO TRACK

## Production Metrics (What Investors Care About)
- Daily active users
- Lookups per day
- OCR success rate
- Paying customers
- Monthly recurring revenue
- User retention (do they come back?)

## Demo Metrics (What the Video Shows)
- Faults diagnosed (cumulative)
- Diagnosis accuracy (% correct)
- Response time (seconds)
- Simulation validation success rate

## Technical Metrics (What Keeps Us Alive)
- API error rate
- P95 response latency
- LLM cost per query
- Uptime percentage

---

# WHAT SUCCESS LOOKS LIKE

## End of Week 6

**Production:**
- 100+ users across Telegram/WhatsApp
- 15-25 paying Pro customers
- $500-750 MRR (small but real)
- Self-learning KB operational
- Zero major outages

**Demo:**
- 90-second video complete
- All 5 magic moments captured
- PLC + Factory IO integration proven
- Ready to send to investors

**Together:**
- Pitch deck with real traction numbers
- Working demo video showing the vision
- Clear roadmap: "Here's what we've built, here's where we're going, here's the money we need to get there"

---

# APPENDIX: Key Technical Decisions

## LLM Provider Strategy
- **Groq**: Intent detection, fast routing, cheap text generation
- **Gemini Flash**: Secondary OCR, general queries
- **Claude Sonnet**: Complex diagnosis, high-stakes decisions
- **GPT-4o**: Fallback OCR, edge cases

## Database
- **Neon PostgreSQL**: Users, subscriptions, equipment, audit logs
- **Redis**: Session state, rate limiting, caching
- **Vector DB (future)**: Semantic search over manuals

## Hosting
- **VPS (72.60.175.144)**: Current backend
- **Cloudflare**: CDN, DDoS protection (if needed)
- **Stripe**: Payments

## Observability
- **LangSmith**: LLM call tracing
- **Phoenix**: Additional tracing
- **Slack**: Alerts and monitoring

---

# FINAL REMINDER

The goal is not to build impressive technology.

The goal is to get maintenance technicians to pay us money every month because we save them time and frustration.

Everything else is in service of that.

Now go build.
