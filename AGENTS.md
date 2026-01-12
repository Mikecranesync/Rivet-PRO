# AGENTS.md - Patterns for AI Code Agents

**Purpose:** Document codebase patterns, architecture decisions, and gotchas for AI agents (Ralph, Claude Code, etc.) working on RIVET Pro.

**Last Updated:** 2026-01-12 (Ralph Chore 001 System Audit)

---

## Architecture Overview

RIVET Pro is a **hybrid Python + n8n system**:
- **Python (rivet_pro/):** Telegram bot, FastAPI REST API, business logic
- **n8n:** Photo analysis (Gemini Vision), manual search (3-tier), workflow orchestration
- **Database:** Neon PostgreSQL with multi-provider failover

**Key Principle:** Leverage n8n for complex workflows, Python for business logic and data persistence.

---

## Patterns Discovered (Audit 2026-01-12)

### 1. n8n Webhook Integration Pattern

**When:** n8n workflows need to trigger Python bot actions (save to database, send messages, track usage)

**How:**
1. n8n completes workflow (e.g., Photo Bot V2 analyzes image)
2. n8n makes HTTP POST to Python bot webhook endpoint: `/api/webhook/n8n-photo-callback`
3. Python bot receives JSON payload:
   ```json
   {
     "chat_id": 987654321,
     "equipment": {
       "manufacturer": "Siemens",
       "model": "S7-1200",
       "serial": "6ES7214-1AG40-0XB0"
     },
     "manual_url": "https://support.siemens.com/..."
   }
   ```
4. Python bot executes business logic:
   - Save equipment to `cmms_equipment` table
   - Track lookup in `usage_tracking` table
   - Send final Telegram message to user
5. n8n workflow completes

**Files:**
- Create router: `rivet_pro/adapters/web/routers/webhooks.py`
- Register in: `rivet_pro/adapters/web/main.py`

**Example:**
```python
# webhooks.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class N8nPhotoCallback(BaseModel):
    chat_id: int
    equipment: dict
    manual_url: str

@router.post("/n8n-photo-callback")
async def handle_n8n_photo_callback(payload: N8nPhotoCallback):
    # 1. Save equipment
    equipment_id = await equipment_service.match_or_create_equipment(
        manufacturer=payload.equipment['manufacturer'],
        model=payload.equipment['model'],
        serial=payload.equipment['serial']
    )

    # 2. Track usage
    await usage_service.record_lookup(user_id, 'photo_ocr', equipment_id)

    # 3. Send Telegram message
    await bot.send_message(
        chat_id=payload.chat_id,
        text=f"Equipment: {payload.equipment['manufacturer']} {payload.equipment['model']}\n[Download Manual]({payload.manual_url})"
    )

    return {"ok": True}
```

---

### 2. Equipment-First Architecture

**Principle:** All work orders MUST link to equipment. Equipment is the central entity.

**Database Design:**
- `work_orders.equipment_id` → `cmms_equipment.id` (FK NOT NULL)
- Equipment denormalized into work_orders for query performance (manufacturer, model, serial copied)
- Auto-triggers update equipment stats:
  - `cmms_equipment.work_order_count` incremented on new work order
  - `cmms_equipment.last_work_order_at` timestamp updated
  - `cmms_equipment.last_reported_fault` updated

**Create Work Order Flow:**
1. Match or create equipment first → get `equipment_id`
2. Then create work order with `equipment_id` (mandatory)
3. Database trigger auto-updates equipment stats

**Files:**
- `migrations/004_work_orders.sql` - Trigger: `trg_update_equipment_stats`
- `rivet_pro/core/services/work_order_service.py` - Always requires equipment_id

**Example:**
```python
# WRONG - no equipment
await work_order_service.create_work_order(
    user_id=user_id,
    title="Motor failure"
)  # ❌ Will fail - equipment_id required

# CORRECT - equipment first
equipment_id = await equipment_service.match_or_create_equipment(
    manufacturer="Siemens",
    model="1LA7"
)
await work_order_service.create_work_order(
    user_id=user_id,
    equipment_id=equipment_id,  # ✅ Required
    title="Motor failure"
)
```

---

### 3. Database Failover Strategy

**Primary:** Neon PostgreSQL (serverless, auto-scaling)
**Failover Chain:** Neon → VPS → Supabase → Local SQLite

**When:** Database connection fails or health check fails

**How:**
- `rivet_pro/infra/database.py` (PRIMARY - use this)
  - asyncpg connection pooling (min=2, max=10)
  - Health checks with 60s TTL caching
  - Auto-failover on connection errors
- `rivet/core/database_manager.py` (LEGACY - multi-provider, complex)
  - Supports 6 providers, automatic failover
  - Use for reference, prefer rivet_pro/infra/database.py for new code

**Files:**
- `rivet_pro/infra/database.py` - Modern async interface (use this)
- `rivet_pro/config/settings.py` - DATABASE_URL and failover config

**Environment Variables:**
```bash
DATABASE_PROVIDER=neon
DATABASE_URL=postgresql://user:pass@neon.tech/db
DATABASE_FAILOVER_ENABLED=true
DATABASE_FAILOVER_ORDER=neon,vps,supabase
VPS_KB_HOST=72.60.175.144
SUPABASE_URL=https://xyz.supabase.co
```

---

### 4. Service Layer Pattern

**When:** Implementing business logic (equipment CRUD, work orders, usage tracking)

**Structure:**
```
rivet_pro/core/services/
├── equipment_service.py       # Equipment operations
├── work_order_service.py      # Work order lifecycle
├── usage_service.py           # Usage tracking + limits
├── equipment_taxonomy.py      # Equipment classification
└── ocr_service.py             # Multi-provider OCR
```

**Pattern:**
1. Services are classes with async methods
2. Database instance injected via dependency injection (FastAPI) or passed as parameter
3. Return JSON-serializable dicts (not asyncpg.Record objects)
4. Use type hints with Pydantic models

**Example:**
```python
# equipment_service.py
from rivet_pro.infra.database import Database

class EquipmentService:
    def __init__(self, db: Database):
        self.db = db

    async def match_or_create_equipment(
        self,
        manufacturer: str,
        model: str,
        serial: str | None = None
    ) -> tuple[str, str, bool]:
        """
        Match or create equipment.

        Returns: (equipment_id, equipment_number, is_new)
        """
        # 1. Try to match existing
        existing = await self.db.fetchrow(
            """
            SELECT id, equipment_number FROM cmms_equipment
            WHERE manufacturer ILIKE $1 AND model_number ILIKE $2
            """,
            manufacturer, model
        )

        if existing:
            return (existing['id'], existing['equipment_number'], False)

        # 2. Create new (equipment_number auto-generated by trigger)
        result = await self.db.fetchrow(
            """
            INSERT INTO cmms_equipment (manufacturer, model_number, serial_number)
            VALUES ($1, $2, $3)
            RETURNING id, equipment_number
            """,
            manufacturer, model, serial
        )

        return (result['id'], result['equipment_number'], True)
```

---

### 5. Auto-Numbering Pattern

**When:** Creating equipment or work orders

**How:** Database triggers generate sequential numbers automatically

**Equipment:** `EQ-2025-000001`
- Trigger: `trg_generate_equipment_number`
- Format: `EQ-{YEAR}-{SEQUENCE}`
- Increments per year

**Work Orders:** `WO-2025-000001`
- Trigger: `trg_generate_work_order_number`
- Format: `WO-{YEAR}-{SEQUENCE}`
- Increments per year

**Usage:**
```python
# Just insert - number generated automatically
result = await db.fetchrow(
    """
    INSERT INTO cmms_equipment (manufacturer, model_number)
    VALUES ($1, $2)
    RETURNING id, equipment_number  -- equipment_number already set by trigger
    """,
    "Siemens", "S7-1200"
)
# result['equipment_number'] == 'EQ-2025-000123'
```

**Files:**
- `migrations/003_cmms_equipment.sql` - Equipment trigger
- `migrations/004_work_orders.sql` - Work order trigger

---

### 6. Usage Tracking & Freemium Enforcement

**When:** User performs a billable action (photo lookup, manual search, API call)

**Tables:**
- `users` - Stores `monthly_lookup_count`, `lookup_count_reset_date`, `subscription_tier`
- `subscription_limits` - Defines limits per tier (free: 10/month, pro: unlimited)
- `usage_tracking` - Logs each lookup with timestamp and type

**Flow:**
1. **Before action:** Check if user is within limit
   ```python
   count = await db.fetchval(
       """
       SELECT COUNT(*) FROM usage_tracking
       WHERE user_id = $1 AND lookup_timestamp >= (
           SELECT lookup_count_reset_date FROM users WHERE id = $1
       )
       """,
       user_id
   )

   limit = await db.fetchval(
       """
       SELECT manual_lookups_per_month FROM subscription_limits
       WHERE tier = (SELECT subscription_tier FROM users WHERE id = $1)
       """,
       user_id
   )

   if count >= limit and subscription_tier == 'free':
       raise UsageLimitExceeded("Free tier limit reached. Upgrade to Pro.")
   ```

2. **After action:** Record lookup
   ```python
   await db.execute(
       """
       INSERT INTO usage_tracking (user_id, lookup_type, equipment_id)
       VALUES ($1, $2, $3)
       """,
       user_id, 'photo_ocr', equipment_id
   )
   ```

3. **Monthly reset:** Handled by `users.lookup_count_reset_date` field (set to first day of next month)

**Files:**
- `migrations/011_usage_tracking.sql`
- `rivet_pro/core/services/usage_service.py`
- `rivet_pro/adapters/telegram/bot.py` - Enforce before processing photos

---

## Gotchas

### 1. Three Database Abstractions - Use rivet_pro!

**Problem:** Three different database access layers exist:
1. `rivet_pro/infra/database.py` ← **PRIMARY - use this**
2. `rivet/atlas/database.py` (legacy, backward compat with Agent Factory)
3. `rivet/core/database_manager.py` (multi-provider, complex)

**Solution:** Always use `rivet_pro/infra/database.py` for new code. It's async-first, clean API, proper connection pooling.

```python
# ✅ CORRECT
from rivet_pro.infra.database import Database

db = Database()
await db.connect()
result = await db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)

# ❌ WRONG - don't use rivet/
from rivet.atlas.database import AtlasDatabase  # Legacy!
```

---

### 2. Circular Foreign Keys (teams ↔ users)

**Problem:**
- `users.team_id` → `teams.id`
- `teams.owner_id` → `users.id`

**Solution:** Migration 001 resolves this with careful ALTER FK ordering:
1. Create users table WITHOUT team_id FK
2. Create teams table WITH owner_id FK
3. ALTER users ADD FOREIGN KEY team_id → teams.id

**Action:** Be cautious adding new FKs between these tables. Follow same pattern.

---

### 3. n8n Workflows Not Version-Controlled

**Problem:** n8n workflow JSON files exist in `rivet-pro/n8n-workflows/` but deployment is manual (import via n8n UI).

**Current State:**
- Workflows stored as JSON files in Git
- Deployment: Manual import to n8n UI at 72.60.175.144:5678
- No CI/CD automation

**Action:** Consider n8n API auto-import script for future CI/CD:
```bash
# Example n8n API workflow import
curl -X POST http://72.60.175.144:5678/rest/workflows \
  -H "Content-Type: application/json" \
  -d @rivet_photo_bot_v2_hybrid.json
```

**Files:**
- `rivet-pro/n8n-workflows/*.json` - Workflow definitions
- `rivet-n8n-workflow/*.json` - Additional workflows

---

### 4. Telegram Bot: Polling vs Webhook Mode

**Current:** Bot uses polling mode (development)
**Production:** Should use webhook mode (more efficient)

**Polling Mode:**
```python
# start_bot.py
bot.run_polling()  # ← Current
```

**Webhook Mode:**
```python
# main.py (FastAPI)
@app.post("/api/telegram/webhook")
async def telegram_webhook(update: dict):
    await bot.process_update(update)
```

**Action:** Switch to webhook mode before production launch. Requires HTTPS with valid SSL certificate.

---

## File Locations Quick Reference

### Critical Files for MVP

| File | Purpose |
|------|---------|
| `rivet_pro/adapters/telegram/bot.py` | Telegram bot handlers (INCOMPLETE - only /start) |
| `rivet_pro/core/services/equipment_service.py` | Equipment CRUD + matching |
| `rivet_pro/core/services/usage_service.py` | Usage tracking (enforcement needed) |
| `rivet_pro/infra/database.py` | Database connection (PRIMARY) |
| `rivet_pro/config/settings.py` | Environment config |
| `rivet-pro/n8n-workflows/rivet_photo_bot_v2_hybrid.json` | Photo analysis workflow (ACTIVE) |
| `rivet-n8n-workflow/rivet_workflow.json` | Manual Hunter 3-tier search (ACTIVE) |

### Database Migrations

All migrations in `rivet_pro/migrations/`:
- `001_saas_layer.sql` - Users, teams, subscriptions
- `002_knowledge_base.sql` - Manufacturers, equipment_models, manuals
- `003_cmms_equipment.sql` - Equipment instances + auto-numbering
- `004_work_orders.sql` - Work orders + auto-numbering + equipment stats trigger
- `011_usage_tracking.sql` - Usage tracking table
- `012_stripe_integration.sql` - Stripe webhooks

---

## Testing Patterns

### Unit Tests
```python
# tests/core/test_equipment_service.py
import pytest
from rivet_pro.core.services.equipment_service import EquipmentService

@pytest.mark.asyncio
async def test_match_or_create_equipment(mock_db):
    service = EquipmentService(mock_db)
    equipment_id, number, is_new = await service.match_or_create_equipment(
        manufacturer="Siemens",
        model="S7-1200"
    )
    assert number.startswith("EQ-2025-")
    assert is_new == True
```

### Integration Tests
```python
# tests/adapters/test_telegram_bot.py
import pytest
from rivet_pro.adapters.telegram.bot import TelegramBot

@pytest.mark.asyncio
async def test_photo_handler(mock_update, mock_db):
    bot = TelegramBot(db=mock_db)
    await bot.handle_photo(mock_update, mock_context)
    # Assert equipment created, usage tracked
```

---

## Deployment Checklist

- [ ] Environment variables configured (.env)
- [ ] Database migrations applied (auto-run at startup)
- [ ] n8n workflows imported to VPS n8n instance
- [ ] Telegram webhook configured (webhook mode)
- [ ] HTTPS certificate valid (for webhook mode)
- [ ] Monitoring/logging configured
- [ ] Database backups enabled (Neon auto-backup)

---

**Last Updated:** 2026-01-12
**Next Review:** After RIVET-007 through RIVET-013 implementation
