# Rivet Pro - Resume Context

**Last Updated:** 2026-01-05
**Session:** Production CMMS Web API + Telegram Bot Commands Implementation
**Status:** Ready for VPS Deployment (Phase 8)

---

## 🎯 Project Overview

**Rivet Pro** is a production-ready CMMS (Computerized Maintenance Management System) with:
- Equipment-first architecture with fuzzy matching
- Multi-provider OCR for equipment nameplate analysis
- Telegram bot interface with commands
- RESTful Web API with JWT authentication
- PostgreSQL database (Neon hosted)

---

## ✅ What's Complete

### Phase 1-6: Production Web API (FastAPI)

**Core Infrastructure:**
- ✅ FastAPI application with async lifespan (`rivet_pro/adapters/web/main.py`)
- ✅ JWT authentication with bcrypt password hashing
- ✅ CORS middleware configured
- ✅ Database connection pooling via asyncpg
- ✅ Auto-generated API docs at `/docs` and `/redoc`

**5 Complete API Routers:**

1. **Authentication** (`/api/auth`)
   - POST `/register` - Email/password registration
   - POST `/login` - OAuth2 password flow
   - GET `/me` - Current user info (protected)
   - POST `/link-telegram` - Link Telegram to web account

2. **Equipment** (`/api/equipment`)
   - GET `/` - List with pagination/filters
   - GET `/{id}` - Get details
   - POST `/` - Create/match (fuzzy matching)
   - PUT `/{id}` - Update location/status
   - GET `/search/fuzzy` - Fuzzy search

3. **Work Orders** (`/api/work-orders`)
   - GET `/` - List with status filter
   - GET `/{id}` - Get details
   - POST `/` - Create (equipment-first)
   - PUT `/{id}` - Update status/notes
   - GET `/equipment/{id}/work-orders` - List by equipment

4. **Statistics** (`/api/stats`)
   - GET `/overview` - Dashboard stats
   - GET `/equipment-health` - Health scores
   - GET `/work-order-trends` - Time-series (30 days)
   - GET `/summary` - Quick user summary

5. **Upload** (`/api/upload`)
   - POST `/nameplate` - Photo OCR + auto-equipment creation

**Services:**
- ✅ `EquipmentService` - Equipment matching, CRUD (rivet_pro/core/services/equipment_service.py)
- ✅ `WorkOrderService` - Work order management (ported from rivet/atlas)
- ✅ `OCRService` - Multi-provider OCR (Gemini→Groq→Claude→OpenAI)
- ✅ `SMEService` - Manufacturer-specific troubleshooting

**Database:**
- ✅ 7 migrations complete
- ✅ Migration 007: Web auth fields (password_hash, email_verified, last_login_at)
- ✅ Unique email index created
- ✅ Equipment-first architecture maintained

### Phase 7: Telegram Bot Commands

**Commands Implemented:**

1. **`/equip`** - Equipment management
   - `/equip list` - List equipment (most recent 10)
   - `/equip search <query>` - Fuzzy search
   - `/equip view <number>` - Full details

2. **`/wo`** - Work order management
   - `/wo list` - List work orders (most recent 10)
   - `/wo view <number>` - Full details

3. **`/stats`** - Dashboard overview
   - Equipment count
   - Work order breakdown by status

**Features:**
- ✅ Status emojis (🟢 open, 🟡 in progress, ✅ completed, 🔴 cancelled)
- ✅ Priority indicators (🔵 low, 🟡 medium, 🟠 high, 🔴 critical)
- ✅ Work order counts per equipment
- ✅ Error handling with user-friendly messages
- ✅ WorkOrderService initialized in bot startup

**Existing Bot Features:**
- ✅ `/start` - User registration
- ✅ Photo upload → OCR → Equipment creation
- ✅ Text messages → SME routing

---

## 📂 Key File Locations

### Web API
```
rivet_pro/adapters/web/
├── main.py                    # FastAPI app (107 lines)
├── dependencies.py            # Auth helpers, JWT (172 lines)
└── routers/
    ├── auth.py               # Authentication (217 lines)
    ├── equipment.py          # Equipment CRUD (282 lines)
    ├── work_orders.py        # Work orders (242 lines)
    ├── stats.py              # Dashboard stats (230 lines)
    └── upload.py             # Photo OCR upload (157 lines)
```

### Services
```
rivet_pro/core/services/
├── equipment_service.py       # Equipment matching & CRUD (453 lines)
├── work_order_service.py      # Work order management (309 lines)
├── ocr_service.py             # Multi-provider OCR
└── sme_service.py             # Manufacturer troubleshooting
```

### Telegram Bot
```
rivet_pro/adapters/telegram/
└── bot.py                     # Bot with commands (540+ lines)
```

### Database
```
rivet_pro/migrations/
├── 001_saas_layer.sql
├── 002_knowledge_base.sql
├── 003_cmms_equipment.sql
├── 004_work_orders.sql
├── 005_user_machines.sql
├── 006_links.sql
└── 007_web_auth.sql           # NEW: Web authentication
```

### Configuration
```
rivet_pro/config/
└── settings.py                # Pydantic settings with JWT config
```

---

## 🔧 Technical Details

### Database Schema

**Users Table:**
```sql
- id (UUID, PK)
- email (TEXT, UNIQUE)
- full_name (TEXT)
- role (TEXT)
- telegram_user_id (TEXT)
- password_hash (VARCHAR(255))  -- NEW in migration 007
- email_verified (BOOLEAN)       -- NEW in migration 007
- last_login_at (TIMESTAMPTZ)    -- NEW in migration 007
- created_at (TIMESTAMPTZ)
```

**Equipment Table (cmms_equipment):**
```sql
- id (UUID, PK)
- equipment_number (TEXT, UNIQUE) -- EQ-2026-000001
- manufacturer (TEXT)
- model_number (TEXT)
- serial_number (TEXT)
- equipment_type (TEXT)
- location (TEXT)
- work_order_count (INTEGER, DEFAULT 0)
- last_reported_fault (TEXT)
- owned_by_user_id (TEXT, FK)
- created_at/updated_at (TIMESTAMPTZ)
```

**Work Orders Table:**
```sql
- id (UUID, PK)
- work_order_number (TEXT, UNIQUE) -- WO-2026-000001
- equipment_id (UUID, FK)
- equipment_number (TEXT, denormalized)
- user_id (TEXT, FK)
- title (TEXT)
- description (TEXT)
- status (TEXT) -- open, in_progress, completed, cancelled
- priority (TEXT) -- low, medium, high, critical
- fault_codes (TEXT[])
- symptoms (TEXT[])
- source (TEXT) -- web, telegram, api
- created_at/updated_at/completed_at (TIMESTAMPTZ)
```

### Environment Variables Required

```bash
# Database
DATABASE_URL=postgresql://...neon.tech/...

# Telegram
TELEGRAM_BOT_TOKEN=...

# AI Providers
GROQ_API_KEY=...
GOOGLE_API_KEY=...          # For Gemini
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...

# Web API (NEW)
JWT_SECRET_KEY=...          # REQUIRED - Generate with: python -c "import secrets; print(secrets.token_hex(32))"
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,https://rivet-cmms.com

# Observability
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### Dependencies Installed

**Web API (NEW):**
- fastapi>=0.110.0
- uvicorn[standard]>=0.27.0
- python-jose[cryptography]>=3.3.0
- passlib[bcrypt]>=1.7.4
- python-multipart>=0.0.9

**Existing:**
- python-telegram-bot[webhooks,job-queue]>=20.0
- asyncpg>=0.29.0
- anthropic>=0.40.0
- openai>=1.0.0
- google-generativeai>=0.3.0
- groq>=0.4.0

---

## 🚀 VPS Deployment Info

**VPS:** 72.60.175.144
**Location:** `/opt/Rivet-PRO`
**Current Services:**
- `rivet-bot.service` - Telegram bot (running)

**Services to Add:**
- `rivet-api.service` - Web API on port 8000 (pending)

---

## 📋 Next Steps - Phase 8: Deployment

### Pending Tasks

1. **Install Dependencies on VPS**
   ```bash
   ssh root@72.60.175.144
   cd /opt/Rivet-PRO
   git pull origin main
   source rivet_pro/venv/bin/activate
   pip install fastapi uvicorn python-jose passlib python-multipart
   ```

2. **Generate and Set JWT_SECRET_KEY**
   ```bash
   python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(32))"
   # Add output to /opt/Rivet-PRO/.env
   ```

3. **Run Migration 007**
   ```bash
   python3 -c "
   import asyncio
   from rivet_pro.infra.database import db
   async def run():
       await db.connect()
       await db.run_migrations()
       await db.disconnect()
   asyncio.run(run())
   "
   ```

4. **Create systemd Service for Web API**
   - File: `/etc/systemd/system/rivet-api.service`
   - ExecStart: `uvicorn rivet_pro.adapters.web.main:app --host 0.0.0.0 --port 8000`

5. **Start Services**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable rivet-api
   sudo systemctl start rivet-api
   sudo systemctl restart rivet-bot
   ```

6. **Verify**
   - API health: `curl http://localhost:8000/health`
   - API docs: `http://72.60.175.144:8000/docs`
   - Telegram commands: `/stats`, `/equip list`, `/wo list`

---

## 🔍 Testing Checklist

### API Testing (Local)
```bash
# Start API
cd rivet_pro
uvicorn rivet_pro.adapters.web.main:app --reload --port 8000

# Visit http://localhost:8000/docs

# Register user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=test123"

# List equipment (with JWT token)
curl http://localhost:8000/api/equipment \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Telegram Bot Testing
```
/start              # Should show welcome message
/stats              # Should show equipment & work order counts
/equip list         # Should list equipment (10 most recent)
/wo list            # Should list work orders (10 most recent)
[Send photo]        # Should run OCR and create equipment
```

---

## 📊 Current System State

**Git Status:**
- Main branch: `main`
- Last commit: `7683941` - "Add Telegram bot commands for CMMS management"
- Changes pushed to GitHub: ✅

**Database:**
- Connection: Neon PostgreSQL (async via asyncpg)
- Migrations: 1-6 applied on VPS, 7 pending deployment
- Equipment records: 10+ existing (from prior testing)

**Services Running on VPS:**
- Telegram Bot: ✅ Running (polling mode)
- Web API: ❌ Not deployed yet

**Known Working Features:**
- ✅ Photo OCR → Equipment creation
- ✅ Equipment fuzzy matching (85% similarity threshold)
- ✅ Text messages → SME routing
- ✅ Equipment service CRUD operations
- ✅ Multi-provider LLM fallback chain

---

## 🐛 Known Issues / Notes

1. **JWT_SECRET_KEY** - Must be generated and added to .env before API will start
2. **Migration 007** - Must be run before web authentication will work
3. **Port 8000** - Ensure firewall allows access if testing remotely
4. **Bot Commands** - Require WorkOrderService initialization (already implemented)
5. **CORS** - Currently allows localhost:3000, localhost:5173, rivet-cmms.com

---

## 📚 Architecture Notes

**Equipment-First Philosophy:**
- Work orders MUST link to equipment
- Fuzzy matching prevents duplicate equipment entries
- Equipment created automatically from OCR results
- 3-step matching: exact serial → fuzzy (manufacturer+model 85%) → create new

**Multi-Provider OCR Chain:**
1. Gemini 2.5 Flash ($0.075 per 1M tokens) - CHEAPEST
2. Groq Llama 4 Scout ($0.11 per 1M) - FASTEST
3. OpenAI GPT-4o-mini ($0.15 per 1M)
4. Claude Haiku ($0.25 per 1M)
5. Groq Llama 4 Maverick ($0.50 per 1M) - Better vision
6. Gemini 2.5 Pro ($1.25 per 1M)
7. OpenAI GPT-4o ($5.00 per 1M) - MOST EXPENSIVE

**API Design:**
- RESTful with resource-based routing
- JWT tokens expire after 24 hours
- OAuth2 password flow for compatibility
- User ownership enforced (users only see their own data)

---

## 🎯 Success Metrics

**Phase 1-7 Completion:**
- ✅ 13 new files created (1,600+ lines of production code)
- ✅ 5 complete API routers with 20+ endpoints
- ✅ 3 Telegram bot commands
- ✅ 1 database migration
- ✅ JWT authentication system
- ✅ WorkOrderService ported and integrated
- ✅ All code committed and pushed

**Phase 8 Pending:**
- [ ] VPS deployment
- [ ] Production testing
- [ ] Both services running simultaneously
- [ ] Web UI login working

---

## 🔗 Related Documentation

- Plan file: `~/.claude/plans/reflective-popping-wand.md`
- API docs (after deployment): `http://72.60.175.144:8000/docs`
- GitHub repo: `https://github.com/Mikecranesync/Rivet-PRO`

---

## 💡 Quick Resume Commands

```bash
# Resume development
cd /c/Users/hharp/OneDrive/Desktop/Rivet-PRO

# Check status
git status
git log --oneline -5

# Start local API testing
cd rivet_pro
uvicorn rivet_pro.adapters.web.main:app --reload --port 8000

# Deploy to VPS
ssh root@72.60.175.144
cd /opt/Rivet-PRO
git pull origin main
# ... follow deployment steps above
```

---

**End of Resume Context**
