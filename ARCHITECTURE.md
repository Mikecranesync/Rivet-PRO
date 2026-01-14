# RIVET Pro - Complete Architecture Documentation

> **Last Updated:** 2026-01-14
> **Primary Database:** Neon PostgreSQL (ep-purple-hall-ahimeyn0)
> **Backup Database:** Supabase (mggqgrxwumnnujojndub)

---

## Quick Reference

| Resource | Value |
|----------|-------|
| **Neon Project** | ep-purple-hall-ahimeyn0 |
| **Neon Host** | ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech |
| **Supabase Project** | mggqgrxwumnnujojndub |
| **Supabase URL** | https://mggqgrxwumnnujojndub.supabase.co |
| **Telegram Bot** | @RivetProBot (8161680636) |
| **Admin Chat ID** | 8445149012 |
| **Repository** | C:\Users\hharp\OneDrive\Desktop\Rivet-PRO |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACES                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   [Telegram Bot]          [FastAPI Web]           [n8n Workflows]       │
│   Polling/Webhook         REST API :8000          Automation :5678      │
│   - Photo OCR             - Equipment CRUD        - Manual Hunter       │
│   - /equip, /wo, /manual  - Work Orders           - KB Enrichment       │
│   - Natural language      - Auth (JWT)            - Feedback Loop       │
│                           - Swagger docs          - Ralph Execution     │
│                                                                          │
└────────────────┬──────────────────┬─────────────────┬───────────────────┘
                 │                  │                 │
                 ▼                  ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER (rivet_pro/)                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │    ADAPTERS     │  │      CORE       │  │     INFRA       │         │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤         │
│  │ telegram/       │  │ services/       │  │ database.py     │         │
│  │  └─ bot.py      │  │  ├─ equipment   │  │  (asyncpg pool) │         │
│  │ web/            │  │  ├─ work_order  │  │ observability   │         │
│  │  ├─ main.py     │  │  ├─ ocr         │  │  (logging)      │         │
│  │  └─ routers/    │  │  ├─ manual      │  └─────────────────┘         │
│  │ llm/            │  │  ├─ stripe      │                               │
│  │  └─ router.py   │  │  ├─ usage       │  ┌─────────────────┐         │
│  │    (multi-LLM)  │  │  ├─ feedback    │  │     CONFIG      │         │
│  └─────────────────┘  │  ├─ kb_analytics│  ├─────────────────┤         │
│                       │  ├─ alerting    │  │ settings.py     │         │
│                       │  └─ 8 more...   │  │ feature_flags   │         │
│                       └─────────────────┘  └─────────────────┘         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────┐  │
│  │   NEON PostgreSQL (PRIMARY)     │  │   SUPABASE (BACKUP/LEGACY)  │  │
│  │   ep-purple-hall-ahimeyn0       │  │   mggqgrxwumnnujojndub      │  │
│  ├─────────────────────────────────┤  ├─────────────────────────────┤  │
│  │ 120 tables                      │  │ knowledge_atoms: 1,985 rows │  │
│  │ - users (3)                     │  │ (Legacy KB data)            │  │
│  │ - cmms_equipment (38)           │  │                             │  │
│  │ - work_orders (40)              │  │ REST API: Working           │  │
│  │ - knowledge_atoms (26)          │  │ Direct DB: DNS issues       │  │
│  │ - ralph_stories (56)            │  │                             │  │
│  │ - manufacturers (11)            │  │                             │  │
│  │ - + 114 more tables             │  │                             │  │
│  └─────────────────────────────────┘  └─────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Database Connections

### Primary: Neon PostgreSQL

```
Host: ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech
Database: neondb
User: neondb_owner
Password: npg_c3UNa4KOlCeL
SSL: require

Connection String:
postgresql://neondb_owner:npg_c3UNa4KOlCeL@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require
```

### Backup: Supabase

```
Project URL: https://mggqgrxwumnnujojndub.supabase.co
DB Host: db.mggqgrxwumnnujojndub.supabase.co
Database: postgres
User: postgres
Password: $!hLQDYB#uW23DJ
Service Role Key: sb_secret_x67ttLFGhQY_KsNmBB-fMQ_WC5Ab_tP

Note: Direct PostgreSQL connection has DNS resolution issues.
Use Supabase REST API instead for backup operations.
```

### Important: Two Neon Projects Exist

| Neon Project | Endpoint | Status |
|--------------|----------|--------|
| **ep-purple-hall-ahimeyn0** | Primary, 120 tables | **USE THIS** |
| ep-lingering-salad-ahbmzx98 | Empty, 4 tables | Ignore |

---

## Database Schema Overview

### Table Categories (120 total)

#### CMMS Core (5 tables)
| Table | Rows | Purpose |
|-------|------|---------|
| `cmms_equipment` | 38 | Equipment registry (manufacturer, model, serial, location) |
| `work_orders` | 40 | Work order tracking with equipment linking |
| `technicians` | 0 | Technician profiles |
| `machines` | 4 | Machine instances |
| `user_machines` | 0 | User-owned equipment |

#### Knowledge Base (11 tables)
| Table | Rows | Purpose |
|-------|------|---------|
| `knowledge_atoms` | 26 | AI-generated knowledge units |
| `knowledge_gaps` | 0 | Identified knowledge gaps |
| `manual_cache` | 3 | Cached manual lookups |
| `manuals` | 10 | Manual metadata |
| `equipment_manuals` | 2 | Equipment-manual links |
| `manufacturers` | 11 | Manufacturer registry |
| `equipment_models` | 5 | Canonical equipment models |
| `product_families` | 0 | Product family groupings |
| `tech_notes` | 0 | Technical notes |
| `manual_chunks` | 0 | Chunked manual content |
| `manual_files` | 0 | Manual file storage |

#### Users & Authentication (8 tables)
| Table | Rows | Purpose |
|-------|------|---------|
| `users` | 3 | Primary user table (telegram_id, subscription) |
| `rivet_users` | 1 | Legacy user table |
| `user` | 1 | n8n user table |
| `teams` | 0 | Team/organization groupings |
| `admin_users` | 1 | Admin accounts |
| `user_api_keys` | 0 | API key storage |
| `role` | 13 | Role definitions |
| `scope` | 169 | Permission scopes |

#### Interactions & Chat (6 tables)
| Table | Rows | Purpose |
|-------|------|---------|
| `interactions` | 6 | User interaction logging |
| `chat_hub_messages` | 0 | Chat message history |
| `chat_hub_sessions` | 0 | Chat sessions |
| `print_chat_history` | 4 | Print-related chats |
| `prints` | 2 | Print jobs |
| `rivet_print_sessions` | 0 | Print sessions |

#### Manual Hunter System (5 tables)
| Table | Rows | Purpose |
|-------|------|---------|
| `manual_hunter_cache` | 0 | Manual search cache |
| `manual_hunter_queue` | 0 | Pending manual searches |
| `manual_requests` | 0 | User manual requests |
| `manual_gaps` | 2 | Missing manuals |
| `equipment_manual_searches` | 0 | Search history |

#### KB Enrichment Pipeline (4 tables)
| Table | Rows | Purpose |
|-------|------|---------|
| `enrichment_queue` | 0 | Pending enrichment tasks |
| `enrichment_stats` | 2 | Enrichment metrics |
| `gap_requests` | 58 | Knowledge gap requests |
| `human_review_queue` | 0 | Items needing review |

#### Usage & Billing (6 tables)
| Table | Rows | Purpose |
|-------|------|---------|
| `usage_events` | 0 | Usage event log |
| `usage_tracking` | 14 | Usage metrics |
| `rivet_usage_log` | 0 | Legacy usage log |
| `subscription_limits` | 3 | Tier limits |
| `tier_limits` | 3 | Feature limits by tier |
| `rivet_stripe_events` | 0 | Stripe webhook events |

#### Ralph Autonomous System (4 tables)
| Table | Rows | Purpose |
|-------|------|---------|
| `ralph_stories` | 56 | User stories for autonomous dev |
| `ralph_projects` | 1 | Project definitions |
| `ralph_executions` | 0 | Execution history |
| `ralph_iterations` | 0 | Iteration tracking |

#### n8n Workflow Tables (5 tables)
| Table | Rows | Purpose |
|-------|------|---------|
| `workflow_entity` | 0 | Workflow definitions |
| `workflow_history` | 0 | Workflow version history |
| `execution_entity` | 0 | Execution records |
| `execution_data` | 0 | Execution payloads |
| `credentials_entity` | 1 | Stored credentials |

---

## Key Table Schemas

### users
```sql
id                    UUID PRIMARY KEY
telegram_id           BIGINT
whatsapp_id           VARCHAR
full_name             VARCHAR
email                 VARCHAR
company               VARCHAR
subscription_tier     VARCHAR  -- 'free', 'pro', 'team'
team_id               UUID REFERENCES teams(id)
monthly_lookup_count  INTEGER
lookup_count_reset_date DATE
created_at            TIMESTAMPTZ
last_active_at        TIMESTAMPTZ
-- + 10 more columns
```

### cmms_equipment
```sql
id                    UUID PRIMARY KEY
equipment_number      VARCHAR NOT NULL  -- 'EQ-2026-000001'
manufacturer          VARCHAR NOT NULL
model_number          VARCHAR
serial_number         VARCHAR
equipment_type        VARCHAR
location              VARCHAR
department            VARCHAR
criticality           ENUM ('low', 'medium', 'high', 'critical')
owned_by_user_id      TEXT
machine_id            UUID
description           TEXT
work_order_count      INTEGER DEFAULT 0
last_reported_fault   TEXT
created_at            TIMESTAMPTZ
-- + 9 more columns
```

### work_orders
```sql
id                    UUID PRIMARY KEY
work_order_number     VARCHAR NOT NULL  -- 'WO-2026-000001'
user_id               TEXT NOT NULL
telegram_username     VARCHAR
created_by_agent      VARCHAR
source                ENUM NOT NULL
equipment_id          UUID NOT NULL REFERENCES cmms_equipment(id)
equipment_number      VARCHAR
manufacturer          VARCHAR
model_number          VARCHAR
title                 VARCHAR NOT NULL
description           TEXT
status                VARCHAR  -- 'open', 'in_progress', 'completed', 'cancelled'
priority              VARCHAR  -- 'low', 'medium', 'high', 'critical'
fault_codes           JSONB
created_at            TIMESTAMPTZ
-- + 20 more columns
```

### knowledge_atoms
```sql
id                    UUID PRIMARY KEY
atom_id               TEXT NOT NULL
atom_type             TEXT NOT NULL  -- 'concept', 'procedure', 'specification'
title                 TEXT NOT NULL
summary               TEXT NOT NULL
content               TEXT NOT NULL
manufacturer          TEXT NOT NULL
product_family        TEXT
product_version       TEXT
difficulty            TEXT NOT NULL
prerequisites         ARRAY
related_atoms         ARRAY
source_document       TEXT
source_pages          ARRAY
source_url            TEXT
citations             JSONB
quality_score         FLOAT
safety_level          TEXT
safety_notes          TEXT
keywords              ARRAY
embedding             VECTOR
created_at            TIMESTAMPTZ
last_validated_at     TIMESTAMPTZ
-- + 20 more columns
```

### ralph_stories
```sql
id                    SERIAL PRIMARY KEY
project_id            INTEGER
story_id              VARCHAR NOT NULL  -- 'FEATURE-001'
title                 VARCHAR NOT NULL
description           TEXT
acceptance_criteria   JSONB
status                VARCHAR  -- 'todo', 'in_progress', 'done', 'blocked'
status_emoji          VARCHAR
priority              INTEGER
commit_hash           VARCHAR
error_message         TEXT
retry_count           INTEGER DEFAULT 0
created_at            TIMESTAMPTZ
updated_at            TIMESTAMPTZ
-- + 8 more columns
```

---

## Directory Structure

```
Rivet-PRO/
├── rivet_pro/                      # Main application
│   ├── adapters/                   # External integrations
│   │   ├── telegram/
│   │   │   └── bot.py              # TelegramBot class (1900 lines)
│   │   ├── web/
│   │   │   ├── main.py             # FastAPI app
│   │   │   └── routers/            # API endpoints
│   │   │       ├── auth.py
│   │   │       ├── equipment.py
│   │   │       ├── work_orders.py
│   │   │       ├── stats.py
│   │   │       ├── stripe.py
│   │   │       └── upload.py
│   │   └── llm/
│   │       └── router.py           # Multi-provider LLM routing
│   │
│   ├── core/                       # Business logic
│   │   ├── services/               # 17 service classes
│   │   │   ├── equipment_service.py
│   │   │   ├── work_order_service.py
│   │   │   ├── ocr_service.py
│   │   │   ├── manual_service.py
│   │   │   ├── manual_matcher_service.py
│   │   │   ├── sme_service.py
│   │   │   ├── feedback_service.py
│   │   │   ├── stripe_service.py
│   │   │   ├── usage_service.py
│   │   │   ├── alerting_service.py
│   │   │   ├── kb_analytics_service.py
│   │   │   ├── enrichment_queue_service.py
│   │   │   ├── product_family_discoverer.py
│   │   │   └── equipment_taxonomy.py
│   │   ├── models/
│   │   │   └── ocr.py
│   │   ├── prompts/
│   │   │   └── sme/                # Manufacturer-specific prompts
│   │   │       ├── siemens.py
│   │   │       ├── abb.py
│   │   │       ├── fanuc.py
│   │   │       ├── rockwell.py
│   │   │       ├── schneider.py
│   │   │       ├── mitsubishi.py
│   │   │       └── generic.py
│   │   ├── utils/
│   │   └── feature_flags.py
│   │
│   ├── config/
│   │   ├── settings.py             # Pydantic BaseSettings
│   │   └── feature_flags.json
│   │
│   ├── infra/
│   │   ├── database.py             # asyncpg connection pool
│   │   └── observability.py        # Logging setup
│   │
│   ├── migrations/                 # SQL migration files (18)
│   │   ├── 001_saas_layer.sql
│   │   ├── 002_knowledge_base.sql
│   │   ├── 003_cmms_equipment.sql
│   │   ├── 004_work_orders.sql
│   │   └── ... (14 more)
│   │
│   ├── workers/
│   │   └── manual_gap_filler.py
│   │
│   ├── main.py                     # RivetProApplication
│   ├── start_bot.py                # Bot launcher
│   └── run_migrations.py
│
├── scripts/
│   └── ralph/                      # Ralph autonomous system
│       ├── prompt.md               # Agent instructions
│       ├── prd.json                # Product requirements
│       ├── progress.txt            # Execution log
│       └── ralph_local.py          # Python runner
│
├── n8n/workflows/                  # n8n workflow exports
│
├── docs/
│   ├── QUICK_CONTEXT.md
│   ├── SESSION_LOG.md
│   └── BRANCHING_GUIDE.md
│
├── .github/workflows/              # CI/CD
│   ├── neon-branch.yml
│   ├── neon-cleanup.yml
│   └── neon-migration-preview.yml
│
├── .env                            # Environment variables
├── .env.example
├── CLAUDE.md                       # Claude Code instructions
├── ARCHITECTURE.md                 # This file
├── docker-compose.yml
├── pyproject.toml
└── requirements.txt
```

---

## Service Layer (17 Services)

| Service | File | Purpose | Key Methods |
|---------|------|---------|-------------|
| **EquipmentService** | equipment_service.py | Equipment CRUD & matching | `match_or_create_equipment()`, `search_equipment()` |
| **WorkOrderService** | work_order_service.py | Work order lifecycle | `create_work_order()`, `update_status()` |
| **OCRService** | ocr_service.py | Multi-provider vision OCR | `extract_from_image()` |
| **ManualService** | manual_service.py | Manual lookup | `search_manual()` |
| **ManualMatcherService** | manual_matcher_service.py | Fuzzy manual matching | `find_best_match()` |
| **SMEService** | sme_service.py | Manufacturer-specific AI | `get_sme_response()` |
| **FeedbackService** | feedback_service.py | User feedback collection | `create_feedback()`, `approve_proposal()` |
| **StripeService** | stripe_service.py | Payment processing | `create_checkout_session()`, `is_pro_user()` |
| **UsageService** | usage_service.py | Usage tracking & limits | `can_use_service()`, `record_lookup()` |
| **AlertingService** | alerting_service.py | Telegram notifications | `alert_critical()` |
| **KBAnalyticsService** | kb_analytics_service.py | KB metrics & reporting | `get_learning_stats()`, `generate_daily_health_report()` |
| **EnrichmentQueueService** | enrichment_queue_service.py | KB enrichment pipeline | `enqueue_enrichment()` |
| **ProductFamilyDiscoverer** | product_family_discoverer.py | Equipment family grouping | `discover_family()` |
| **EquipmentTaxonomy** | equipment_taxonomy.py | Component classification | `identify_component()` |
| **PhotoService** | photo_service.py | Photo handling | `upload_photo()` |

---

## LLM Provider Chain

Cost-optimized routing (cheapest first):

| Priority | Provider | Model | Cost/1K tokens |
|----------|----------|-------|----------------|
| 1 | Groq | Llama 4 Scout | $0.00011 |
| 2 | Google | Gemini 2.5 Flash | $0.000075 |
| 3 | OpenAI | GPT-4o-mini | $0.00015 |
| 4 | Anthropic | Claude 3 Haiku | $0.00025 |
| 5 | OpenAI | GPT-4o | $0.005 |

Configuration in `rivet_pro/adapters/llm/router.py`

---

## Telegram Bot Commands

| Command | Handler | Description |
|---------|---------|-------------|
| `/start` | `start_command` | User registration, welcome message |
| `/help` | `help_command` | Show all commands |
| `/menu` | `menu_command` | Interactive menu buttons |
| `/equip list` | `equip_command` | List user's equipment |
| `/equip search <q>` | `equip_command` | Search equipment |
| `/equip view <num>` | `equip_command` | View equipment details |
| `/wo list` | `wo_command` | List work orders |
| `/wo view <num>` | `wo_command` | View work order details |
| `/wo create` | `wo_command` | Create work order |
| `/manual <equip>` | `manual_command` | Get equipment manual |
| `/library` | `library_command` | Browse machine library |
| `/stats` | `stats_command` | User CMMS statistics |
| `/kb_stats` | `kb_stats_command` | KB statistics (admin) |
| `/upgrade` | `upgrade_command` | Stripe checkout link |
| `/reset` | `reset_command` | Clear session |
| `/done` | `done_command` | Exit troubleshooting |

**Photo Handler:** Send any photo to trigger OCR analysis and equipment matching.

---

## Data Flow Diagrams

### Photo OCR Flow
```
User sends photo
    │
    ▼
TelegramBot._handle_photo()
    │
    ├─► UsageService.can_use_service() → Check free tier limit
    │
    ├─► Download photo bytes
    │
    ├─► OCRService.extract_from_image() → Multi-provider LLM
    │       │
    │       └─► Returns: manufacturer, model, serial, confidence
    │
    ├─► EquipmentService.match_or_create_equipment()
    │       │
    │       └─► Returns: equipment_id, equipment_number, is_new
    │
    ├─► ManualService.search_manual() or KB search
    │       │
    │       └─► Returns: manual_url, confidence
    │
    ├─► Create knowledge_atom (if manual found)
    │
    ├─► Log interaction
    │
    └─► Send formatted response to user
```

### Work Order Creation Flow
```
User: /wo create EQ-2026-000001 "Motor overheating"
    │
    ▼
TelegramBot.wo_command()
    │
    ├─► Parse equipment_number and description
    │
    ├─► EquipmentService.get_equipment_by_number()
    │       │
    │       └─► Validates equipment exists
    │
    ├─► WorkOrderService.create_work_order()
    │       │
    │       ├─► Generate work_order_number (WO-2026-XXXXXX)
    │       ├─► INSERT INTO work_orders
    │       └─► UPDATE cmms_equipment.work_order_count
    │
    └─► Send confirmation with WO number
```

---

## Environment Variables

```bash
# Database (PRIMARY - use this!)
DATABASE_URL=postgresql://neondb_owner:npg_c3UNa4KOlCeL@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require
DATABASE_PROVIDER=neon
DATABASE_FAILOVER_ENABLED=true
DATABASE_FAILOVER_ORDER=neon,vps,supabase

# Supabase (BACKUP)
SUPABASE_URL=https://mggqgrxwumnnujojndub.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sb_secret_x67ttLFGhQY_KsNmBB-fMQ_WC5Ab_tP
SUPABASE_DB_HOST=db.mggqgrxwumnnujojndub.supabase.co
SUPABASE_DB_PASSWORD=$!hLQDYB#uW23DJ

# Telegram
TELEGRAM_BOT_TOKEN=8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE
TELEGRAM_BOT_MODE=polling  # or 'webhook'
TELEGRAM_ADMIN_CHAT_ID=8445149012

# AI Providers
GROQ_API_KEY=xxx
GOOGLE_API_KEY=xxx
ANTHROPIC_API_KEY=xxx
OPENAI_API_KEY=xxx

# Stripe
STRIPE_API_KEY=xxx
STRIPE_WEBHOOK_SECRET=xxx

# n8n Webhooks
N8N_WEBHOOK_URL=xxx
N8N_MANUAL_HUNTER_URL=xxx
N8N_FEEDBACK_WEBHOOK_URL=xxx
RALPH_MAIN_LOOP_URL=xxx

# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
```

---

## Current Data Summary

| Metric | Count |
|--------|-------|
| **Users** | 3 |
| **Equipment** | 38 |
| **Work Orders** | 40 |
| **KB Atoms (Neon)** | 26 |
| **KB Atoms (Supabase)** | 1,985 |
| **Cached Manuals** | 3 |
| **Manufacturers** | 11 |
| **Ralph Stories** | 56 |
| **Gap Requests** | 58 |
| **Total Tables** | 120 |

---

## Design Patterns

| Pattern | Implementation |
|---------|----------------|
| **Adapter** | `adapters/` folder isolates external integrations |
| **Service Layer** | Business logic in `core/services/` |
| **Repository** | Services encapsulate database queries |
| **Singleton** | FeatureFlagManager, Database pool |
| **Dependency Injection** | FastAPI `Depends()` |
| **Provider Chain** | LLM router tries providers in cost order |
| **Feature Flags** | Safe rollouts via JSON config |
| **Async/Await** | All I/O operations |
| **Trigger-Based** | Database triggers for auto-numbering |

---

## Startup Commands

```bash
# Run the Telegram bot
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
python run_bot.py

# Or using module
python -m rivet_pro.adapters.telegram.bot

# Run FastAPI web server
uvicorn rivet_pro.adapters.web.main:app --reload --port 8000

# Run Ralph autonomous agent
python scripts/ralph/ralph_local.py --max 5

# Run migrations
python rivet_pro/run_migrations.py

# Test database connection
python -c "
import asyncio
import asyncpg
async def test():
    conn = await asyncpg.connect('postgresql://neondb_owner:npg_c3UNa4KOlCeL@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require')
    print(await conn.fetchval('SELECT NOW()'))
    await conn.close()
asyncio.run(test())
"
```

---

## Troubleshooting

### Database Connection Issues

1. **Wrong Neon endpoint**: Use `ep-purple-hall-ahimeyn0`, NOT `ep-lingering-salad`
2. **Neon sleeping**: Wake at https://console.neon.tech
3. **Supabase DNS**: Use REST API instead of direct PostgreSQL

### Bot Issues

1. **Bot not responding**: Check `TELEGRAM_BOT_TOKEN` in `.env`
2. **Database errors**: Verify `DATABASE_URL` points to correct Neon
3. **Free tier limit**: Check `usage_tracking` table

### Common Queries

```sql
-- Check user subscription
SELECT telegram_id, subscription_tier, monthly_lookup_count
FROM users WHERE telegram_id = 8445149012;

-- List recent work orders
SELECT work_order_number, title, status, created_at
FROM work_orders ORDER BY created_at DESC LIMIT 10;

-- Check Ralph stories
SELECT story_id, title, status FROM ralph_stories
WHERE status != 'done' ORDER BY priority;

-- KB atom count by type
SELECT atom_type, COUNT(*) FROM knowledge_atoms GROUP BY atom_type;
```

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-14 | 2.0.0 | Complete rewrite, documented Neon as primary DB |
| 2026-01-14 | 1.5.0 | Repository cleanup, memory system |
| 2026-01-13 | 1.4.0 | Telegram bot commands expanded |
| 2026-01-12 | 1.3.0 | KB analytics, feedback loop |
| 2026-01-10 | 1.2.0 | Stripe integration |
| 2026-01-08 | 1.1.0 | Work order system |
| 2026-01-06 | 1.0.0 | Initial CMMS extraction |

---

## Related Documentation

- [CLAUDE.md](./CLAUDE.md) - Claude Code instructions
- [docs/QUICK_CONTEXT.md](./docs/QUICK_CONTEXT.md) - Session restoration
- [docs/SESSION_LOG.md](./docs/SESSION_LOG.md) - Work history
- [docs/BRANCHING_GUIDE.md](./docs/BRANCHING_GUIDE.md) - Git workflow
- [scripts/ralph/prompt.md](./scripts/ralph/prompt.md) - Ralph agent instructions
