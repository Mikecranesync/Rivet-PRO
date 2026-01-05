# Phase 2: Database Migration - COMPLETE ✅

## Summary

Phase 2 of Rivet Pro has been successfully implemented. The unified database schema merges all three visions (SaaS, Knowledge Base, CMMS) into a single coherent data model with clear layer separation.

## What Was Built

### 6 Migration Files Created

**1. `001_saas_layer.sql` - SaaS & Subscription Management**
- `users` table with Telegram + WhatsApp support
- `teams` table for multi-user subscriptions
- `subscription_limits` table defining free/pro/team tiers
- Auto-reset monthly lookup counters
- Circular foreign key resolution (teams ← users → teams)

**2. `002_knowledge_base.sql` - Equipment Knowledge & Manuals**
- `manufacturers` table with aliases (7 pre-loaded manufacturers)
- `equipment_models` table (canonical knowledge: "What IS a G120C?")
- `manuals` table with file storage, indexing status, source tracking
- `manual_chunks` table with vector embeddings for RAG (pgvector)
- `tech_notes` table for tribal knowledge with upvotes
- Sample manufacturers: Siemens, Rockwell, ABB, Schneider, Mitsubishi, Fanuc, Omron

**3. `003_cmms_equipment.sql` - Equipment Instances (CMMS)**
- `cmms_equipment` table (specific instances: "The G120C in Building A")
- **Critical link:** `equipment_model_id` foreign key to `equipment_models`
- Auto-numbering: EQ-2025-0001 format
- Auto-linking trigger (matches manufacturer + model to equipment_models)
- Criticality levels: low/medium/high/critical
- Work order tracking statistics

**4. `004_work_orders.sql` - Work Order Management**
- `work_orders` table with mandatory equipment linking
- Auto-numbering: WO-2025-0001 format
- Source tracking (telegram_text, telegram_photo, etc.)
- Route tracking (A/B/C/D from 4-route SME orchestrator)
- Priority calculation with confidence scores
- Auto-updates equipment statistics on WO creation

**5. `005_user_machines.sql` - Personal Equipment Library**
- `user_machines` table for user's saved equipment
- Links to CMMS equipment instances
- Nickname-based organization per user
- Photo reference storage (Telegram file_id)

**6. `006_links.sql` - Interaction Tracking & Manual Requests**
- `interactions` table for all user activity tracking
- `manual_requests` table for unfound manual queue
- Foreign key constraints linking all layers
- `schema_health` view for monitoring

### Migration Runner Infrastructure

**Enhanced `rivet_pro/infra/database.py`:**
- `run_migrations()` - Executes all pending migrations in order
- `_create_migrations_table()` - Tracks applied migrations
- `_get_applied_migrations()` - Returns set of completed migrations
- `rollback_migration()` - Marks migration as rolled back
- Idempotent execution (re-running is safe)

**CLI Tool: `run_migrations.py`**
- Simple command-line interface
- Connects to database
- Runs all pending migrations
- Displays schema health check
- Error handling with helpful messages

## Unified Schema Architecture

### Three Layers, One Database

```
┌──────────────────────────────────────────────────────┐
│ SAAS LAYER                                           │
│ • users (with telegram_id/whatsapp_id)               │
│ • teams (multi-user subscriptions)                   │
│ • subscription_limits (tier definitions)             │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│ KNOWLEDGE BASE LAYER                                 │
│ • manufacturers (canonical list)                     │
│ • equipment_models (What IS a G120C?)                │
│ • manuals (PDF storage & metadata)                   │
│ • manual_chunks (vector embeddings for RAG)          │
│ • tech_notes (tribal knowledge)                      │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│ CMMS LAYER                                           │
│ • cmms_equipment (The G120C in Building A)           │
│   ├─→ equipment_model_id (CRITICAL LINK)            │
│ • work_orders (always linked to equipment)           │
│ • user_machines (personal library)                   │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│ TRACKING LAYER                                       │
│ • interactions (all user activity)                   │
│ • manual_requests (unfound manuals queue)            │
└──────────────────────────────────────────────────────┘
```

### Critical Design Decision: equipment_models vs cmms_equipment

**The Link That Unifies All Three Visions:**

```sql
-- Knowledge Base Layer
equipment_models (id, manufacturer_id, model_number)
  → "What IS a Siemens G120C?" (canonical knowledge)

-- CMMS Layer
cmms_equipment (id, equipment_model_id, serial_number, location)
  → "The specific G120C in Building A, serial SR123"
  → equipment_model_id REFERENCES equipment_models(id)
```

**What This Enables:**
1. **Vision 1 (Manual Lookup):** Photo → OCR → Match equipment_model → Deliver manual
2. **Vision 3 (CMMS):** Create cmms_equipment → Auto-link to equipment_model → Manual available
3. **Hybrid Flow:** User creates work order → Equipment instance → Manual lookup via equipment_model_id

### Auto-Linking Intelligence

The schema includes smart triggers:

**1. Auto-Link Equipment Model (003_cmms_equipment.sql:62-82)**
```sql
-- When creating CMMS equipment, automatically link to equipment_model if match found
CREATE TRIGGER auto_link_equipment_model_trigger
```
- If manufacturer + model_number match → sets equipment_model_id
- Happens transparently on INSERT/UPDATE
- Enables instant manual lookup for CMMS equipment

**2. Auto-Update Equipment Stats (004_work_orders.sql:165-191)**
```sql
-- When work order created, update equipment statistics
CREATE TRIGGER work_order_equipment_stats
```
- Increments work_order_count
- Updates last_work_order_at timestamp
- Records last_reported_fault

## How to Use

### 1. Configure Database

Edit `.env`:
```bash
DATABASE_URL=postgresql://user:password@host/rivet_pro?sslmode=require
```

### 2. Run Migrations

```bash
cd rivet_pro
python run_migrations.py
```

Expected output:
```
[RUN] 001_saas_layer.sql
[DONE] 001_saas_layer.sql
[RUN] 002_knowledge_base.sql
[DONE] 002_knowledge_base.sql
[RUN] 003_cmms_equipment.sql
[DONE] 003_cmms_equipment.sql
[RUN] 004_work_orders.sql
[DONE] 004_work_orders.sql
[RUN] 005_user_machines.sql
[DONE] 005_user_machines.sql
[RUN] 006_links.sql
[DONE] 006_links.sql

All migrations complete

Schema Health Check
users                          |          0 rows | 16 kB
teams                          |          0 rows | 16 kB
manufacturers                  |          7 rows | 32 kB
...
```

### 3. Verify Schema

Query the `schema_health` view:
```sql
SELECT * FROM schema_health ORDER BY table_name;
```

### 4. Re-Running is Safe

Migrations are idempotent:
- `schema_migrations` table tracks applied migrations
- Re-running skips already-applied migrations
- Safe to run multiple times

## Schema Statistics

| Table | Purpose | Layer | Critical Links |
|-------|---------|-------|----------------|
| users | User accounts | SaaS | telegram_id, team_id |
| teams | Organizations | SaaS | owner_id → users |
| subscription_limits | Tier features | SaaS | tier (free/pro/team) |
| manufacturers | Vendor list | Knowledge | - |
| equipment_models | Product catalog | Knowledge | manufacturer_id |
| manuals | Documentation | Knowledge | equipment_model_id |
| manual_chunks | RAG search | Knowledge | manual_id, embedding |
| tech_notes | Tribal knowledge | Knowledge | equipment_model_id, user_id |
| cmms_equipment | Equipment instances | CMMS | **equipment_model_id** |
| work_orders | Maintenance tickets | CMMS | equipment_id, user_id |
| user_machines | Personal library | CMMS | user_id |
| interactions | Activity log | Tracking | user_id, equipment_model_id |
| manual_requests | Unfound queue | Tracking | user_id |

**Total Tables:** 13
**Total Enums:** 5 (criticality_level, source_type, route_type, work_order_status, priority_level)
**Total Triggers:** 10 (auto-numbering, timestamps, stats updates, auto-linking)
**Total Indexes:** 50+

## Key Features Enabled

### Subscription Tiers
```sql
SELECT * FROM subscription_limits;

tier  | manual_lookups_per_month | chat_with_pdf | personal_cmms | seats
------|--------------------------|---------------|---------------|-------
free  | 10                       | FALSE         | FALSE         | 1
pro   | -1 (unlimited)           | TRUE          | TRUE          | 1
team  | -1 (unlimited)           | TRUE          | TRUE          | 10
```

### Pre-Loaded Manufacturers
- Siemens (Siemens AG, Siemens Industry)
- Rockwell Automation (Rockwell, Allen-Bradley, AB)
- ABB (Asea Brown Boveri, ABB Inc)
- Schneider Electric (Schneider, Telemecanique, Modicon)
- Mitsubishi Electric (Mitsubishi, MELSEC)
- Fanuc (FANUC Corporation)
- Omron (Omron Corporation)

### Vector Search (pgvector)
- `manual_chunks.embedding` uses vector(1536) for OpenAI embeddings
- IVFFlat index for fast cosine similarity search
- Ready for RAG (Phase 8)

### Equipment Numbering
- Equipment: `EQ-2025-0001`, `EQ-2025-0002`, ...
- Work Orders: `WO-2025-0001`, `WO-2025-0002`, ...
- Auto-increments annually with year prefix

## Success Criteria: MET ✅

- [x] All 6 migrations created
- [x] Unified schema with clear layer separation
- [x] Critical link: cmms_equipment.equipment_model_id → equipment_models.id
- [x] Foreign keys enforce referential integrity
- [x] Auto-linking triggers for intelligent defaults
- [x] Migration runner infrastructure
- [x] CLI tool for easy execution
- [x] Schema health monitoring view
- [x] Idempotent migrations (safe to re-run)

## Next Steps: Phase 3

**Phase 3: Service Extraction (5 days)**

Copy proven code from rivet/:
1. `rivet/workflows/ocr.py` → `rivet_pro/core/services/ocr_service.py` (390 lines, unchanged)
2. `rivet/workflows/sme_router.py` → `rivet_pro/core/services/sme_service.py` (436 lines, unchanged)
3. `rivet/atlas/equipment_matcher.py` → `rivet_pro/core/services/equipment_service.py` (adapt for new schema)
4. `rivet/prompts/sme/*.py` → `rivet_pro/core/prompts/sme/` (7 vendor prompts)

**Command to start Phase 3:**
```bash
# Phase 3 will extract and adapt production-ready services from rivet/
```

## Files Modified

**New Files Created:**
- `rivet_pro/migrations/001_saas_layer.sql` (115 lines)
- `rivet_pro/migrations/002_knowledge_base.sql` (183 lines)
- `rivet_pro/migrations/003_cmms_equipment.sql` (147 lines)
- `rivet_pro/migrations/004_work_orders.sql` (156 lines)
- `rivet_pro/migrations/005_user_machines.sql` (49 lines)
- `rivet_pro/migrations/006_links.sql` (133 lines)
- `rivet_pro/run_migrations.py` (70 lines)

**Files Modified:**
- `rivet_pro/infra/database.py` (+127 lines for migration runner)

**Total LOC Added:** ~980 lines of SQL + Python

---

**Phase 2 Status: COMPLETE ✅**

The unified database schema is ready for service integration.
