# RIVET Pro - Claude/AI Agent Technical Reference

**Purpose:** Complete technical reference for any AI agent to understand and operate the RIVET Pro system.

**Last Updated:** January 16, 2026 (Dual-Write Sync Added)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Infrastructure & Connections](#2-infrastructure--connections)
3. [Database Architecture](#3-database-architecture)
4. [Codebase Structure](#4-codebase-structure)
5. [Deployment & Operations](#5-deployment--operations)
6. [API Keys & Services](#6-api-keys--services)
7. [Common Operations](#7-common-operations)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Project Overview

### What is RIVET Pro?

RIVET Pro Atlas CMMS is a **Telegram-based Computerized Maintenance Management System** with AI-powered features:
- **Equipment Registry** via photo OCR
- **Manual Lookup** with self-healing knowledge base
- **Work Order Management**
- **SME Expert Chat** (vendor-specific AI personas)

### Key Paths

| Location | Path |
|----------|------|
| **Local Project** | `C:\Users\hharp\OneDrive\Desktop\Rivet-PRO` |
| **VPS Project** | `/opt/Rivet-PRO` |
| **Environment File** | `.env` (both local and VPS) |
| **Bot Entry Point** | `rivet_pro/adapters/telegram/__main__.py` |

### GitHub Repository

```
Repository: https://github.com/Mikecranesync/Rivet-PRO.git
Main Branch: main
Current Branch: troubleshoot/atlas-cmms-testing
```

---

## 2. Infrastructure & Connections

### 2.1 VPS Server

| Property | Value |
|----------|-------|
| **IP Address** | `72.60.175.144` |
| **SSH Access** | `ssh root@72.60.175.144` |
| **OS** | Ubuntu (systemd) |
| **Project Path** | `/opt/Rivet-PRO` |

**SSH Quick Commands:**
```bash
# Connect to VPS
ssh root@72.60.175.144

# Check bot status
ssh root@72.60.175.144 "systemctl status rivet-bot"

# View bot logs
ssh root@72.60.175.144 "journalctl -u rivet-bot -n 50 --no-pager"

# Restart bot
ssh root@72.60.175.144 "systemctl restart rivet-bot"

# Deploy latest code
ssh root@72.60.175.144 "cd /opt/Rivet-PRO && git pull && systemctl restart rivet-bot"
```

### 2.2 Systemd Service

**Service File:** `/etc/systemd/system/rivet-bot.service`

```ini
[Unit]
Description=RIVET Pro Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/Rivet-PRO
EnvironmentFile=/opt/Rivet-PRO/.env
ExecStart=/usr/bin/python3 -m rivet_pro.adapters.telegram
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Service Commands:**
```bash
systemctl start rivet-bot
systemctl stop rivet-bot
systemctl restart rivet-bot
systemctl status rivet-bot
journalctl -u rivet-bot -f  # Follow logs
```

### 2.3 Docker Containers on VPS

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `atlas-frontend` | `intelloop/atlas-cmms-frontend:latest` | 3000 | Atlas CMMS Web UI |
| `atlas-cmms` | `atlas-cmms-backend:neon` | 8080 | Atlas CMMS API (Java) |
| `infra_postgres_1` | `pgvector/pgvector:pg16` | 5432 | Local PostgreSQL |
| `infra_redis_1` | `redis:7` | 6379 | Redis cache |
| `infra_ollama_1` | `ollama/ollama:latest` | 11434 | Local LLM (stopped) |

**Atlas CMMS Web UI Access:**
- **URL:** http://72.60.175.144:3000
- **Login:** admin@example.com / admin
- **Assets:** Navigate to Assets to see equipment synced from Telegram bot

**Docker Commands:**
```bash
docker ps -a                    # List all containers
docker logs atlas-cmms -f       # Follow Atlas CMMS logs
docker restart atlas-cmms       # Restart container
docker exec -it atlas-cmms sh   # Shell into container
```

---

## 3. Database Architecture

### 3.1 Primary Database: Neon PostgreSQL

**IMPORTANT: Dual-Database Architecture**

RIVET Pro uses TWO databases on the same Neon project:

| Database | Purpose | Connection Variable |
|----------|---------|---------------------|
| `neondb` | RIVET Pro bot (equipment, users, work orders) | `DATABASE_URL` |
| `atlas_cmms` | Atlas CMMS web UI (asset table) | `ATLAS_DATABASE_URL` |

**Dual-Write Sync:** Equipment created via Telegram is automatically written to BOTH databases, making it visible in both the bot AND the Atlas CMMS web UI.

**Connection Strings:**
```bash
# RIVET Pro Bot Database
DATABASE_URL=postgresql://neondb_owner:npg_c3UNa4KOlCeL@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require

# Atlas CMMS Web UI Database
ATLAS_DATABASE_URL=postgresql://neondb_owner:npg_c3UNa4KOlCeL@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/atlas_cmms?sslmode=require
```

**Quick Query from VPS:**
```bash
# Query neondb (bot data)
ssh root@72.60.175.144 "PGPASSWORD='npg_c3UNa4KOlCeL' psql 'postgresql://neondb_owner@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require' -c \"YOUR_QUERY\""

# Query atlas_cmms (web UI data)
ssh root@72.60.175.144 "PGPASSWORD='npg_c3UNa4KOlCeL' psql 'postgresql://neondb_owner@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/atlas_cmms?sslmode=require' -c \"YOUR_QUERY\""
```

**Neon Console:** https://console.neon.tech
- Project ID: `ep-purple-hall-ahimeyn0`
- API Key: `napi_hgqhaj45dryk5t509877pkgkkywszz2hatvvbwvdlg4vp5we6m3l19qs50l08ggf`

### 3.2 Dual-Write Sync (Equipment → Atlas CMMS)

When equipment is created via Telegram photo OCR, it's written to:
1. `neondb.cmms_equipment` (primary)
2. `atlas_cmms.asset` (synced for web UI visibility)

**Field Mapping:**

| RIVET Pro (cmms_equipment) | Atlas CMMS (asset) | Example |
|---|---|---|
| manufacturer + model_number | name | "Siemens G120C" |
| model_number | model | "G120C" |
| serial_number | serial_number | "SR123456" |
| location (from photo caption) | area | "Stardust Racers" |
| equipment_number | bar_code | "EQ-2026-000044" |
| - | company_id | 46 (hardcoded) |

**Implementation:** `rivet_pro/core/services/equipment_service.py` → `_sync_to_atlas_cmms()`

**Verify Sync:**
```sql
-- Check neondb
SELECT equipment_number, location FROM cmms_equipment ORDER BY created_at DESC LIMIT 5;

-- Check atlas_cmms (should match)
SELECT bar_code, area FROM asset WHERE bar_code LIKE 'EQ-%' ORDER BY id DESC LIMIT 5;
```

### 3.3 Key Tables

**neondb (RIVET Pro Bot):**

| Table | Purpose |
|-------|---------|
| `users` | Telegram user accounts |
| `cmms_equipment` | Equipment registry (photo OCR results) |
| `equipment_models` | Equipment model library |
| `work_orders` | Work order tracking |
| `knowledge_atoms` | Self-healing KB entries |
| `interactions` | User interaction logging |
| `sme_chat_sessions` | SME chat conversations |
| `sme_chat_messages` | Individual chat messages |
| `ralph_stories` | Ralph autonomous dev stories |
| `rivet_usage_log` | Usage analytics |
| `enrichment_queue` | Background enrichment jobs |

**atlas_cmms (Web UI):**

| Table | Purpose |
|-------|---------|
| `asset` | Equipment (synced from cmms_equipment) |
| `work_order` | Work orders (Atlas native) |
| `company` | Company (id=46 for RIVET) |
| `own_user` | Web UI users |

### 3.4 Common Queries

**Check recent equipment:**
```sql
SELECT equipment_number, manufacturer, model_number, location, created_at
FROM cmms_equipment
ORDER BY created_at DESC
LIMIT 10;
```

**Check user stats:**
```sql
SELECT u.telegram_id, u.first_name,
       COUNT(DISTINCT e.id) as equipment_count,
       COUNT(DISTINCT w.id) as work_order_count
FROM users u
LEFT JOIN cmms_equipment e ON e.created_by = CONCAT('telegram_', u.telegram_id::text)
LEFT JOIN work_orders w ON w.created_by = CONCAT('telegram_', u.telegram_id::text)
GROUP BY u.id, u.telegram_id, u.first_name;
```

**Check knowledge base health:**
```sql
SELECT
    COUNT(*) as total_atoms,
    COUNT(*) FILTER (WHERE verified = true) as verified,
    AVG(confidence) as avg_confidence,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as created_today
FROM knowledge_atoms;
```

**Check Ralph stories:**
```sql
SELECT story_id, title, status, priority
FROM ralph_stories
WHERE project_id = 1
ORDER BY priority;
```

### 3.5 Failover Databases

| Provider | Connection | Status |
|----------|------------|--------|
| **Neon** (Primary) | `DATABASE_URL` | Active |
| **Supabase** (Backup) | `SUPABASE_DB_URL` | Available |
| **VPS Local** | `72.60.175.144:5432` | Available |

---

## 4. Codebase Structure

### 4.1 Directory Layout

```
rivet_pro/
├── adapters/
│   ├── telegram/
│   │   ├── __main__.py      # Entry point
│   │   └── bot.py           # Main bot (3000+ lines)
│   ├── llm/
│   │   └── router.py        # LLM provider routing
│   └── web/
│       └── routers/         # FastAPI endpoints
├── core/
│   ├── services/
│   │   ├── equipment_service.py
│   │   ├── manual_service.py
│   │   ├── ocr_service.py
│   │   ├── sme_service.py
│   │   ├── work_order_service.py
│   │   └── usage_service.py
│   ├── prompts/sme/         # SME personality prompts
│   │   ├── siemens.py       # Hans
│   │   ├── rockwell.py      # Mike
│   │   ├── abb.py           # Erik
│   │   ├── schneider.py     # Pierre
│   │   ├── fanuc.py         # Kenji
│   │   ├── mitsubishi.py    # Yuki
│   │   └── generic.py       # Alex
│   └── models/
├── infra/
│   ├── database.py          # Database connection
│   └── tracer.py            # Request tracing
├── workers/
│   └── enrichment_worker.py # Background jobs
└── config/
    └── settings.py

rivet/                        # SME Chat module (Phase 4)
├── services/
│   ├── sme_chat_service.py
│   ├── sme_rag_service.py
│   └── embedding_service.py
└── atlas/
    └── database.py
```

### 4.2 Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `rivet_pro/adapters/telegram/bot.py` | Main Telegram bot | ~3000 |
| `rivet_pro/core/services/ocr_service.py` | Photo OCR pipeline | ~400 |
| `rivet_pro/core/services/equipment_service.py` | Equipment CRUD | ~400 |
| `rivet_pro/adapters/llm/router.py` | LLM failover routing | ~400 |
| `rivet/services/sme_chat_service.py` | SME Chat logic | ~300 |

### 4.3 Entry Points

**Run Telegram Bot:**
```bash
# From project root
python -m rivet_pro.adapters.telegram

# Or
python rivet_pro/start_bot.py
```

**Run Web API:**
```bash
uvicorn rivet_pro.adapters.web.main:app --reload
```

---

## 5. Deployment & Operations

### 5.1 Deploy to VPS

**Full Deploy:**
```bash
# From local machine
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
git add . && git commit -m "Your message" && git push

# On VPS
ssh root@72.60.175.144 "cd /opt/Rivet-PRO && git pull origin troubleshoot/atlas-cmms-testing && systemctl restart rivet-bot"
```

**Quick Deploy Script:**
```bash
ssh root@72.60.175.144 "cd /opt/Rivet-PRO && git fetch origin && git checkout troubleshoot/atlas-cmms-testing && git pull && systemctl restart rivet-bot && sleep 2 && systemctl status rivet-bot --no-pager"
```

### 5.2 Verify Deployment

```bash
# Check service status
ssh root@72.60.175.144 "systemctl status rivet-bot --no-pager"

# Check recent logs
ssh root@72.60.175.144 "journalctl -u rivet-bot -n 30 --no-pager"

# Test database connection
ssh root@72.60.175.144 "PGPASSWORD='npg_c3UNa4KOlCeL' psql 'postgresql://neondb_owner@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require' -c 'SELECT 1'"
```

### 5.3 Git Branches

| Branch | Purpose |
|--------|---------|
| `main` | Production |
| `troubleshoot/atlas-cmms-testing` | Current working branch |
| `ralph/sme-chat-phase4` | SME Chat feature |
| `ralph/mvp-phase1` | MVP features |

---

## 6. API Keys & Services

### 6.1 LLM Providers (Priority Order for OCR)

| Provider | Model | Status | Notes |
|----------|-------|--------|-------|
| **Groq** | llama-4-maverick-17b | ✅ Active | Primary for OCR |
| **DeepSeek** | deepseek-chat | ✅ Active | Backup |
| **Gemini** | gemini-2.5-pro | ⚠️ Permission issues | Needs API key fix |
| **OpenAI** | gpt-4o | ⚠️ Quota exceeded | Check billing |
| **Anthropic** | claude-3 | ⚠️ Invalid key on VPS | Update key |

**LLM Router Priority:** The `router.py` tries providers in order until one succeeds.

### 6.2 Telegram Bots

| Bot | Token Variable | Purpose |
|-----|----------------|---------|
| **@RivetCMMS_bot** | `TELEGRAM_BOT_TOKEN` | Production CMMS bot |
| **@RivetCeo_bot** | `ORCHESTRATOR_BOT_TOKEN` | Admin/orchestrator |
| **@testbotrivet_bot** | `TELEGRAM_TEST_BOT_TOKEN` | Local dev testing |

**Admin Telegram ID:** `8445149012`

### 6.3 External Services

| Service | Purpose | Console |
|---------|---------|---------|
| **Neon** | Primary database | https://console.neon.tech |
| **Supabase** | Backup database | https://app.supabase.com |
| **Stripe** | Payments | https://dashboard.stripe.com |
| **Langfuse** | LLM observability | https://us.cloud.langfuse.com |
| **LangSmith** | Tracing | https://smith.langchain.com |

### 6.4 Manual Search APIs

| API | Purpose | Key Variable |
|-----|---------|--------------|
| **Brave Search** | Web search | `BRAVE_SEARCH_API_KEY` |
| **Serper** | Google search | `SERPER_API_KEY` |
| **Tavily** | AI search | `TAVILY_API_KEY` |
| **Firecrawl** | Web scraping | `FIRECRAWL_API_KEY` |

---

## 7. Common Operations

### 7.1 Photo Caption → Location Tagging

When a user sends a photo with a caption, the caption becomes the equipment's `location`:

```python
# In bot.py _handle_photo()
photo_caption = update.message.caption.strip() if update.message.caption else None

# Passed to equipment service
equipment_id, equipment_number, is_new = await self.equipment_service.match_or_create_equipment(
    manufacturer=result.manufacturer,
    model_number=result.model_number,
    serial_number=result.serial_number,
    equipment_type=getattr(result, 'equipment_type', None),
    location=photo_caption,  # Caption becomes location
    user_id=f"telegram_{user_id}"
)
```

**Verify:**
```sql
SELECT equipment_number, location FROM cmms_equipment WHERE location IS NOT NULL ORDER BY created_at DESC LIMIT 5;
```

### 7.2 SME Chat Flow

**Start Session:**
1. User sends `/chat siemens`
2. `_handle_chat_command()` in bot.py
3. Creates session in `sme_chat_sessions` table
4. Loads personality from `rivet_pro/core/prompts/sme/siemens.py`
5. Returns greeting as "Hans"

**Message Routing:**
1. User sends message
2. `_handle_sme_chat_callback()` checks for active session
3. Routes to `sme_chat_service.process_message()`
4. RAG retrieves context from knowledge base
5. LLM generates response with confidence level

**End Session:**
1. User sends `/endchat`
2. Session marked as closed
3. Goodbye message sent

### 7.3 Ralph Autonomous Development

**Start Ralph:**
```bash
# Read current PRD
cat scripts/ralph/prd.json

# Check pending stories
ssh root@72.60.175.144 "PGPASSWORD='npg_c3UNa4KOlCeL' psql 'postgresql://neondb_owner@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require' -c \"SELECT story_id, title, status FROM ralph_stories WHERE status = 'todo' ORDER BY priority\""
```

**Story Workflow:**
1. Mark story `in_progress`
2. Implement according to acceptance criteria
3. Run tests
4. Commit with `feat(STORY-ID): Title`
5. Mark `done` or `failed`
6. Loop to next story

---

## 8. Troubleshooting

### 8.1 Bot Not Responding

```bash
# Check if running
ssh root@72.60.175.144 "systemctl status rivet-bot"

# Check logs for errors
ssh root@72.60.175.144 "journalctl -u rivet-bot -n 100 --no-pager | grep -i error"

# Restart
ssh root@72.60.175.144 "systemctl restart rivet-bot"
```

### 8.2 Database Connection Issues

```bash
# Test Neon connection
ssh root@72.60.175.144 "PGPASSWORD='npg_c3UNa4KOlCeL' psql 'postgresql://neondb_owner@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require' -c 'SELECT NOW()'"

# If Neon is sleeping, it auto-wakes on connection
# Check Neon console: https://console.neon.tech
```

### 8.3 OCR Failures

**Check which LLM providers are working:**
```bash
ssh root@72.60.175.144 "journalctl -u rivet-bot -n 200 --no-pager | grep -E 'Trying|failed|success'"
```

**Common issues:**
- Groq: Usually works
- OpenAI: Quota exceeded → Check billing
- Gemini: Permission denied → Check API key
- Anthropic: Invalid key → Update on VPS

### 8.4 Atlas CMMS Docker Issues

```bash
# Check container status
ssh root@72.60.175.144 "docker ps -a | grep atlas"

# View logs
ssh root@72.60.175.144 "docker logs atlas-cmms --tail 100"

# Restart
ssh root@72.60.175.144 "docker restart atlas-cmms"
```

### 8.5 Quick Health Check

```bash
# All-in-one health check
ssh root@72.60.175.144 "
echo '=== Bot Status ==='
systemctl is-active rivet-bot

echo '=== Database ==='
PGPASSWORD='npg_c3UNa4KOlCeL' psql 'postgresql://neondb_owner@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require' -c 'SELECT COUNT(*) FROM users' 2>/dev/null | tail -2

echo '=== Docker ==='
docker ps --format 'table {{.Names}}\t{{.Status}}' | head -5

echo '=== Recent Errors ==='
journalctl -u rivet-bot -n 20 --no-pager 2>/dev/null | grep -i error | tail -3
"
```

---

## Quick Reference Card

### SSH to VPS
```bash
ssh root@72.60.175.144
```

### Deploy Code
```bash
ssh root@72.60.175.144 "cd /opt/Rivet-PRO && git pull && systemctl restart rivet-bot"
```

### Check Logs
```bash
ssh root@72.60.175.144 "journalctl -u rivet-bot -f"
```

### Query Database
```bash
ssh root@72.60.175.144 "PGPASSWORD='npg_c3UNa4KOlCeL' psql 'postgresql://neondb_owner@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require' -c \"YOUR_QUERY\""
```

### Restart Bot
```bash
ssh root@72.60.175.144 "systemctl restart rivet-bot"
```

---

*This document enables any AI agent to fully operate the RIVET Pro system.*
