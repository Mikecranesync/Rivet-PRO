# RIVET Pro: Vision & Architecture Guide

## What This Document Is

This is the north star for RIVET Pro development. Read this before starting any work session to understand where we're going and why. The product evolves in phases, but every decision should move toward the end-state vision described here.

---

## The One-Liner

RIVET Pro is a read-only diagnostic brain for industrial maintenance teams, delivered through the messaging apps they already use.

---

## Core Philosophy

### Crawl → Walk → Run

We ship simple things that work before building complex things that might not. Each phase must prove itself with paying customers before we advance.

### Harvest, Don't Rewrite

The existing Agent Factory codebase contains battle-tested components. Extract and refine what works rather than rebuilding from scratch.

### Every Interaction Trains the System

This is not a static tool. Every photo analyzed, every manual requested, every troubleshooting conversation makes RIVET smarter. The knowledge base grows automatically.

### Read-Only Is a Feature, Not a Limitation

When we add PLC connectivity, it will be strictly read-only. This is a deliberate design choice that eliminates customer fear and liability concerns. RIVET is a stethoscope, not a scalpel.

---

## Platform Strategy

### Why Telegram and WhatsApp

- Zero onboarding friction. Users already have these apps.
- No app store approvals or update cycles.
- No push notification infrastructure to build.
- User identity comes free.
- WhatsApp penetration in Latin America is near-universal.

### Platform-Agnostic Core

The AI logic lives in one place. Messaging platforms are just adapters.

```
Telegram Adapter (~150 lines)
    ↓
┌─────────────────────────────┐
│      RIVET Core Engine      │
│  - OCR Pipeline             │
│  - KB Lookup                │
│  - SME Routing              │
│  - LangGraph Workflows      │
│  - PLC Gateway (future)     │
└─────────────────────────────┘
    ↑
WhatsApp Adapter (~200 lines)
```

Adapters are dumb translators. All intelligence stays in the core.

---

## Latency Strategy

Telegram and WhatsApp add inherent latency. We cannot compete with native app response times. Instead, we optimize perception of speed.

### Streaming Message Updates

Send immediate acknowledgment, then edit the message as the response generates:

1. User sends photo
2. Instantly reply: "🔍 Analyzing nameplate..."
3. Update: "Found: Allen-Bradley PowerFlex 525..."
4. Update: "Loading manual and troubleshooting info..."
5. Final: Complete response with manual link

User sees activity immediately instead of staring at nothing.

### Fast Models for Fast Tasks

- Groq for intent detection and routing (10x faster than Claude/GPT)
- Expensive models only for OCR and complex reasoning
- Parallel processing where possible (OCR + KB search simultaneously)
- Pre-warmed LLM connections to avoid cold start latency

### Realistic Latency Targets

| Scenario | Target |
|----------|--------|
| Text question, KB hit | 1.5-2s |
| Photo OCR + KB lookup | 3-4s |
| Complex troubleshooting | 5-7s |

These are acceptable for async maintenance work. We're not building a voice assistant.

---

## The Product Phases

### Phase 1: Manual Lookup (NOW)

The MVP that proves the market exists.

**User Flow:**
1. Tech sends photo of equipment nameplate
2. OCR extracts manufacturer, model, serial
3. KB returns relevant manual/documentation
4. AI provides contextual troubleshooting guidance

**Success Metrics:**
- Users get correct manual >90% of time
- Response time <5 seconds for photo queries
- Paying customers on Pro tier

**What We're Building:**
- Multi-provider OCR pipeline (Groq → Gemini → Claude → GPT-4o)
- Equipment matching and normalization
- Knowledge base with manufacturer documentation
- Telegram bot with streaming message updates
- Subscription management (Free/Pro/Team tiers)

### Phase 2: Self-Learning Knowledge Base

The system that gets smarter automatically.

**How It Works:**
- Every interaction is logged and analyzed
- Gaps in knowledge base are detected automatically
- Research orchestrator fills gaps with documentation
- Thumbs up/down feedback trains response quality
- Popular equipment gets priority KB expansion

**Success Metrics:**
- KB coverage increases month over month
- Repeat queries decrease (problems solved first time)
- User satisfaction scores improve

### Phase 3: PLC Gateway & Live Diagnostics (FUTURE)

The unlock that changes the value proposition entirely.

**What It Does:**
- Connects to customer PLCs via OPC UA / Modbus / EtherNet-IP
- Records tag values, fault codes, I/O states continuously
- AI analyzes traces to identify patterns and predict failures
- When fault occurs, AI correlates with historical data

**Critical Design Constraint: READ-ONLY**

```
┌─────────────────────────────────────────────────────┐
│              RIVET PLC Gateway                       │
│                                                      │
│   ┌─────────────┐      READ ONLY      ┌──────────┐  │
│   │   PLC       │ ───────────────────▶│ Recorder │  │
│   │             │   • Tag values      │          │  │
│   │             │   • Fault codes     │ • Trends │  │
│   │             │   • I/O states      │ • Alerts │  │
│   └─────────────┘   • Timestamps      │ • History│  │
│         ▲                             └────┬─────┘  │
│         │                                  │        │
│    NO WRITE ✗                              ▼        │
│    EVER                            ┌────────────┐   │
│                                    │ AI Engine  │   │
│                                    └────────────┘   │
└─────────────────────────────────────────────────────┘
```

**Why Read-Only Matters:**
- Eliminates "what if it shuts down my line?" objection
- No cybersecurity attack surface for control
- IT approval becomes trivial
- Insurance/liability is non-issue
- Worst case: bad advice that human ignores

**Trace Recording Strategy:**
- Poll tags at 1-5 second intervals (sufficient for maintenance diagnostics)
- Rolling buffer keeps last hour locally
- Ship data on interesting events (faults, anomalies)
- Segment and compress for efficient transmission
- Queue and retry if connectivity drops

**Example Interaction:**
```
Tech: "Why did Drive 7 fault?"

RIVET: "Drive 7 hit overcurrent fault F070 at 14:23:07. 

Looking at the trace, motor load spiked from 78% to 147% 
over 3 seconds before the fault triggered. 

This pattern typically indicates mechanical binding. 
Check for:
- Jammed roller on conveyor
- Belt tension issue  
- Bearing failure on motor shaft

Here's the PowerFlex 525 troubleshooting guide for F070..."
```

This is expertise on demand, not automation.

---

## Market Focus

### Why Latin America First

1. **WhatsApp is default** - No adoption friction
2. **Maintenance is manual** - No enterprise software to compete with
3. **Equipment is old and diverse** - Tons of legacy drives needing manuals
4. **Word of mouth is powerful** - Tight manufacturing communities
5. **Dollar pricing is premium** - $29/mo signals quality, still affordable

### Target Industries

- Textile and apparel manufacturing (47,000+ facilities in Colombia alone)
- Food and beverage processing
- General manufacturing SMEs
- Any facility with 5-200 employees and maintenance staff

### Market Size

| Segment | Facilities |
|---------|------------|
| Colombia textile | ~47,000 |
| Mexico textile | ~35,000 |
| Brazil textile | ~30,000 |
| Peru textile | ~15,000 |
| **Total textile LATAM** | **~130,000** |
| **All manufacturing SMEs LATAM** | **~20 million** |

### Revenue Projections

| Year | Pro ($29/mo) | Team ($200/mo) | ARR |
|------|--------------|----------------|-----|
| 1 | 120 | 15 | $78K |
| 2 | 500 | 80 | $366K |
| 3 | 2,000 | 400 | $1.65M |

Conservative estimates. PLC gateway could accelerate significantly.

---

## Subscription Tiers

### Beta (Free)
- 10 equipment lookups per month
- Basic OCR and manual retrieval
- Community knowledge base access

### Pro ($29/month)
- Unlimited lookups
- Chat with PDF (ask questions about manuals)
- Priority OCR processing
- CMMS integration (future)

### Team ($200/month)
- Everything in Pro
- Shared knowledge base across team
- PLC Gateway connectivity (when available)
- Custom equipment profiles
- Admin dashboard and analytics

---

## Technical Architecture

### Current Stack
- Python backend with LangGraph workflows
- Multi-provider LLM support (Groq, Gemini, Claude, OpenAI)
- Neon PostgreSQL database
- Redis for caching and queues
- VPS at 72.60.175.144
- LangSmith + Phoenix for observability
- Slack integration for monitoring

### OCR Pipeline (Cost-Optimized)
```
Photo → Groq (fast/cheap)
           ↓ confidence < 80%
        Gemini (better quality)
           ↓ confidence < 80%
        Claude (high accuracy)
           ↓ confidence < 80%
        GPT-4o (last resort)
```

### Key Principles
- Fail gracefully with clear error messages
- Log everything for debugging and training
- Tenant isolation for multi-customer support
- Idempotent operations where possible

---

## What Success Looks Like

### 6 Months
- 100+ paying customers on Pro/Team
- Knowledge base covers top 50 equipment manufacturers
- Telegram bot stable in production
- WhatsApp adapter launched

### 12 Months
- 500+ paying customers
- Self-learning KB filling gaps automatically
- $300K+ ARR
- Ready for seed funding conversations

### 24 Months
- PLC Gateway in beta with select customers
- Live diagnostics proving value
- $1M+ ARR or significant funding raised
- Expansion beyond textiles into broader manufacturing

---

## Reminders for Every Work Session

1. **Ship working code.** Perfect is the enemy of done.

2. **The user is a maintenance technician** on a factory floor with greasy hands and a phone. Keep it simple.

3. **Telegram/WhatsApp are the product.** Don't get distracted by native app dreams.

4. **Manual lookup must work perfectly** before we add complexity.

5. **PLC Gateway is the vision, not the MVP.** It comes after we prove the basic product.

6. **Read-only is non-negotiable** for any equipment connectivity.

7. **Every feature should make money** or directly support something that does.

8. **Latin America first.** That's where we prove the model.

---

## Questions to Ask Before Building Anything

- Does this help a technician get back to work faster?
- Does this work over WhatsApp with a bad connection?
- Does this get us closer to paying customers?
- Is this the simplest version that could work?
- Can we ship this in days, not weeks?

If the answer to any of these is "no," reconsider.
