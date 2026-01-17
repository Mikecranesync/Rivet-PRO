# Resume Prompt - 2026-01-17

Copy and paste this to resume the session:

---

## Context

I'm working on **RIVET Pro**, a Telegram bot for industrial equipment technicians. Read `docs/QUICK_CONTEXT.md` for full context.

## Current Status: Cloud Migration - Phase 1 (Fly.io Deployment)

**Branch**: `troubleshoot/atlas-cmms-testing`
**Plan File**: `.claude/plans/eager-knitting-creek.md`

### What's Done

1. Created comprehensive cloud migration plan
2. Updated `fly.toml` with health checks, auto-restart, rolling deploy strategy
3. Modified `run_bot.py` to include aiohttp health server on port 8080
4. Updated `Dockerfile` with EXPOSE 8080 and HEALTHCHECK
5. Created `deploy/fly-deploy.ps1` PowerShell script with all secrets

### What's Pending - DEPLOYMENT

User needs to run the deployment script to set Fly.io secrets and deploy:

```powershell
# Install Fly CLI if needed
iwr https://fly.io/install.ps1 -useb | iex

# Restart PowerShell, then:
fly auth login
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
.\deploy\fly-deploy.ps1
```

### After Deployment Succeeds

Verify with:
```bash
fly status -a rivet-cmms-bot
fly logs -a rivet-cmms-bot
curl https://rivet-cmms-bot.fly.dev/health
```

## Cloud Migration Phases

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Telegram Bot to Fly.io | **Scripts ready, awaiting deploy** |
| Phase 2 | Atlas CMMS to Railway (public URL) | Pending |
| Phase 3 | Better Uptime monitoring + alerts | Pending |
| Phase 4 | Supabase failover logic | Pending |

## Key Files Modified This Session

| File | Changes |
|------|---------|
| `fly.toml` | Health checks, VM config, restart policy |
| `run_bot.py` | Added aiohttp health server |
| `Dockerfile` | Added EXPOSE 8080, HEALTHCHECK |
| `deploy/fly-deploy.ps1` | Deployment script with all secrets |
| `deploy/fly-secrets.sh` | Template for bash (placeholder values) |

## Infrastructure Overview

| Component | Current Location | Target |
|-----------|------------------|--------|
| Telegram Bot | VPS systemd (72.60.175.144) | Fly.io (rivet-cmms-bot) |
| Atlas CMMS | VPS Docker | Railway (pending) |
| Primary DB | Neon PostgreSQL | Neon (keep) |
| Failover DB | Supabase | Supabase (add failover code) |

## Technical Reference

- **VPS:** 72.60.175.144
- **Neon Project:** ep-purple-hall-ahimeyn0
- **Fly.io App:** rivet-cmms-bot
- **Region:** ord (Chicago)
- **n8n Cloud:** mikecranesync.app.n8n.cloud

## MCP Memory

Query for context:
- `mcp__memory__search_nodes("CloudMigrationPlan")`
- `mcp__memory__search_nodes("FlyioDeployment")`
- `mcp__memory__search_nodes("HealthCheckServer")`

## Previously Completed

- **Photo Pipeline**: 17 PHOTO-* stories complete, PR #12 merged
- **SME Chat Phase 4**: Conversational chat with vendor SME agents
- **DualWriteSync**: Atlas CMMS sync working

---

*Last updated: 2026-01-17 - Fly.io deployment scripts ready, awaiting user to run*
