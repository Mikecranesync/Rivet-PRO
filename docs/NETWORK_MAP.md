# RIVET Pro Network Infrastructure Map

**Generated:** 2026-01-18
**Last Updated:** 2026-01-18

---

## Telegram Bot Status

| Location | Service | Status | Token |
|----------|---------|--------|-------|
| **Fly.io** | rivet-pro app | RUNNING (PRIMARY) | `7855741814:AAF...` |
| **VPS** | rivet-bot.service | STOPPED (disabled) | `7855741814:AAF...` |

**Fly.io is now the primary Telegram bot host.**

---

## VPS Server (72.60.175.144)

### Systemd Services

| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| `rivet-bot.service` | - | STOPPED (disabled) | Telegram bot - moved to Fly.io |
| `rivet-api.service` | 8000 (internal) | Running | FastAPI Web API |
| `docker.service` | - | Running | Container runtime |

### Docker Containers

| Container | Port | Status | Purpose |
|-----------|------|--------|---------|
| `atlas-frontend` | 3000 (internal) | Up | Atlas CMMS Web UI |
| `atlas-cmms` | 8080 (internal) | Unhealthy | Atlas CMMS Java API |
| `infra_postgres_1` | 5432 (public) | Healthy | Local PostgreSQL + pgvector |
| `infra_redis_1` | 6379 (public) | Healthy | Redis cache |
| `n8n` | 5678 | Created (not running) | n8n (local, unused) |
| `infra_ollama_1` | 11434 | Stopped | Local LLM (unused) |
| `fast-rivet-worker` | - | Stopped | Background worker |

### Exposed Ports (Public Internet)

| Port | Protocol | Service | Security |
|------|----------|---------|----------|
| 22 | SSH | Remote access | OK |
| 80 | HTTP | Caddy reverse proxy | OK |
| 443 | HTTPS | Caddy reverse proxy | OK |
| 5432 | PostgreSQL | Local DB | EXPOSED |
| 5678 | HTTP | n8n (local) | EXPOSED |
| 6379 | Redis | Cache | EXPOSED |

### Internal-Only Ports

| Port | Service |
|------|---------|
| 3000 | Atlas CMMS Frontend |
| 8000 | Rivet Web API |
| 8080 | Atlas CMMS Java API |

---

## Fly.io (rivet-pro.fly.dev)

| Property | Value |
|----------|-------|
| **App Name** | `rivet-pro` |
| **Region** | `iad` (Virginia) |
| **URL** | https://rivet-pro.fly.dev |
| **Health** | https://rivet-pro.fly.dev/health |
| **Status** | 1 machine running, 1 stopped |
| **Mode** | Telegram polling |

### Machines

| ID | Version | State | Health |
|----|---------|-------|--------|
| `2860d43c65e318` | 9 | started | passing |
| `6e827001b60178` | 9 | stopped | warning |

### Fly.io Secrets Configured

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ADMIN_CHAT_ID`
- `DATABASE_URL`
- `ATLAS_DATABASE_URL`
- `JWT_SECRET_KEY`
- `GROQ_API_KEY`
- `DEEPSEEK_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `GOOGLE_API_KEY`
- `N8N_WEBHOOK_BASE_URL`
- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_BASE_URL`
- `TAVILY_API_KEY`
- `BRAVE_SEARCH_API_KEY`
- `SERPER_API_KEY`
- `FIRECRAWL_API_KEY`

---

## Databases

### Primary: Neon PostgreSQL (Cloud)

| Database | Purpose | Environment Variable |
|----------|---------|---------------------|
| `neondb` | RIVET Pro bot data | `DATABASE_URL` |
| `atlas_cmms` | Atlas CMMS Web UI sync | `ATLAS_DATABASE_URL` |

| Property | Value |
|----------|-------|
| **Project ID** | `ep-purple-hall-ahimeyn0` |
| **Region** | `us-east-1` |
| **Console** | https://console.neon.tech |
| **Status** | Online |

### Backup: Local PostgreSQL (VPS)

| Property | Value |
|----------|-------|
| **Host** | 72.60.175.144:5432 |
| **Container** | `infra_postgres_1` |
| **Status** | Healthy |
| **Purpose** | Failover / local dev |

### Backup: Supabase (Cloud)

| Property | Value |
|----------|-------|
| **Project** | `mggqgrxwumnnujojndub` |
| **Region** | `us-east-1` |
| **Status** | Available (not primary) |

---

## n8n Workflow Automation

| Instance | URL | Status |
|----------|-----|--------|
| **n8n Cloud** (Primary) | https://mikecranesync.app.n8n.cloud | Healthy |
| **n8n VPS** (Unused) | http://72.60.175.144:5678 | Container created, not running |

---

## Telegram Bots

| Bot | Username | Token Prefix | Used By |
|-----|----------|--------------|---------|
| **RIVET CMMS** (Primary) | @RivetCMMS_bot | `7855741814` | VPS + Fly.io (DUPLICATE!) |
| **Rivet CEO** | @RivetCeo_bot | `7910254197` | Orchestrator (unused) |
| **Test Bot** | @testbotrivet_bot | `8519329029` | Local dev testing |

---

## Connection Diagram

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                    INTERNET                             │
                    └─────────────────────────────────────────────────────────┘
                           │                    │                    │
                           ▼                    ▼                    ▼
                    ┌─────────────┐     ┌─────────────┐      ┌─────────────┐
                    │   TELEGRAM  │     │  n8n CLOUD  │      │    NEON     │
                    │   SERVERS   │     │mikecranesync│      │  POSTGRES   │
                    └──────┬──────┘     └──────┬──────┘      └──────┬──────┘
                           │                   │                    │
              ┌────────────┴────────────┐      │         ┌─────────┴─────────┐
              │                         │      │         │                   │
              ▼                         ▼      │         ▼                   ▼
    ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
    │   FLY.IO        │       │    VPS          │       │   neondb        │
    │  rivet-pro      │       │ 72.60.175.144   │       │   atlas_cmms    │
    │  (iad region)   │       │                 │       │                 │
    │                 │       │                 │       │                 │
    │ ┌─────────────┐ │       │ ┌─────────────┐ │       └─────────────────┘
    │ │ Telegram Bot│◄┼───────┼─┤ Telegram Bot│ │               │
    │ │ (polling)   │ │ DUPE! │ │ (polling)   │ │               │
    │ └──────┬──────┘ │       │ └──────┬──────┘ │               │
    │        │        │       │        │        │               │
    │        ▼        │       │        ▼        │               │
    │   ┌─────────┐   │       │  ┌──────────┐   │               │
    │   │ Health  │   │       │  │ Web API  │   │               │
    │   │ :8080   │   │       │  │ :8000    │   │               │
    │   └─────────┘   │       │  └──────────┘   │               │
    └────────┬────────┘       │        │        │               │
             │                │        ▼        │               │
             │                │  ┌──────────────┤               │
             │                │  │ Atlas CMMS   │               │
             │                │  │ Frontend     │               │
             │                │  │ :3000        │               │
             │                │  │ Java API     │               │
             │                │  │ :8080        │               │
             │                │  └──────┬───────┤               │
             │                │         │       │               │
             │                │         ▼       │               │
             │                │  ┌──────────────┤               │
             │                │  │   Docker     │               │
             │                │  │  - Postgres  │               │
             │                │  │  - Redis     │               │
             │                │  └──────────────┘               │
             │                │                                 │
             └────────────────┴─────────────────────────────────┘
                           All connect to Neon
```

---

## Summary Table

| Component | Location | Status | Notes |
|-----------|----------|--------|-------|
| **Telegram Bot** | Fly.io | Running | PRIMARY - @RivetCMMS_bot |
| **Telegram Bot** | VPS | Stopped | Disabled - moved to Fly.io |
| **Web API** | VPS:8000 | Running | FastAPI |
| **Atlas CMMS UI** | VPS:3000 | Running | React frontend |
| **Atlas CMMS API** | VPS:8080 | Running* | Java backend (*health check returns 403 but app works) |
| **PostgreSQL** | Neon Cloud | Online | Primary database |
| **PostgreSQL** | VPS:5432 | Healthy | Backup/local (user: rivet) |
| **Redis** | VPS:6379 | Healthy | Cache |
| **n8n** | Cloud | Healthy | Workflow automation |
| **Ollama** | VPS | Stopped | Local LLM (unused) |

---

## Completed Actions (2026-01-18)

### 1. Duplicate Bot Resolved
- VPS bot stopped and disabled
- Fly.io is now PRIMARY

### 2. Security: Exposed Ports Closed
UFW rules added to block:
- 5432 (PostgreSQL)
- 5678 (n8n)
- 6379 (Redis)

### 3. Atlas CMMS Status
- Container is running fine
- Health check shows "unhealthy" because endpoint returns 403 (requires auth)
- This is a false positive - app is working

### 4. Health Check Script Created
```bash
bash /opt/Rivet-PRO/scripts/health-check.sh
```

## Remaining Optional Actions

### Scale Fly.io to 1 Machine (Cost Savings)

```bash
flyctl scale count 1 --app rivet-pro
```

### Re-enable VPS Bot (if Fly.io fails)

```bash
ssh root@72.60.175.144 "systemctl enable rivet-bot && systemctl start rivet-bot"
```

---

## Access Quick Reference

### SSH to VPS
```bash
ssh root@72.60.175.144
```

### Fly.io Commands
```bash
flyctl status --app rivet-pro
flyctl logs --app rivet-pro --no-tail
flyctl ssh console --app rivet-pro
```

### Database Queries
```bash
# Neon (from VPS)
PGPASSWORD='npg_c3UNa4KOlCeL' psql 'postgresql://neondb_owner@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require'

# Local PostgreSQL (VPS)
docker exec -it infra_postgres_1 psql -U postgres
```

### Service Management (VPS)
```bash
systemctl status rivet-bot
systemctl restart rivet-bot
journalctl -u rivet-bot -f
```

---

## External Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Neon Console | https://console.neon.tech | Database management |
| Fly.io Dashboard | https://fly.io/apps/rivet-pro | App management |
| n8n Cloud | https://mikecranesync.app.n8n.cloud | Workflow automation |
| Langfuse | https://us.cloud.langfuse.com | LLM observability |
| Atlas CMMS UI | http://72.60.175.144:3000 | Web interface (via VPS) |
| GitHub Repo | https://github.com/Mikecranesync/Rivet-PRO | Source code |
