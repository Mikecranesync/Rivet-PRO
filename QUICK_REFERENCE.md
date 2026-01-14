# RIVET Pro - Quick Reference

**One-page guide for developers**

---

## 🌐 URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **VPS** | 72.60.175.144 | Production server |
| **n8n** | http://72.60.175.144:5678 | Workflow automation UI |
| **Telegram Bots** | https://t.me/rivet_local_dev_bot<br>https://t.me/RivetCeo_bot<br>https://t.me/RivetCMMS_bot | User interface |
| **Neon DB** | ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech | Primary PostgreSQL |
| **Supabase DB** | db.mggqgrxwumnnujojndub.supabase.co | Fallback PostgreSQL |

---

## 🔐 Credentials

| Item | Location | Notes |
|------|----------|-------|
| **Main .env** | `/root/Rivet-PRO/.env` | All API keys and database URLs |
| **Ralph .env** | `/root/ralph/config/.env` | Copy of main .env for Ralph |
| **ralph user .env** | `/home/ralph/.env` | For Claude CLI execution |
| **n8n Login** | Stored in .env as N8N credentials | UI access |
| **Telegram Bot Tokens** | .env: `TELEGRAM_BOT_TOKEN`, `ORCHESTRATOR_BOT_TOKEN`, `PUBLIC_TELEGRAM_BOT_TOKEN` | 3 bots |
| **Anthropic API** | .env: `ANTHROPIC_API_KEY` | Claude AI |
| **Database URLs** | .env: `DATABASE_URL`, `NEON_DB_URL`, `SUPABASE_DB_URL` | PostgreSQL connections |

**⚠️ NEVER commit .env files to git!**

---

## 💻 Common Commands

### SSH & Access
```bash
# Connect to VPS
ssh root@72.60.175.144

# Connect as ralph user
ssh root@72.60.175.144
su - ralph
```

### n8n Workflows
```bash
# Check n8n status
curl http://72.60.175.144:5678/healthz

# View n8n logs (if running as service)
journalctl -u n8n -f

# Access n8n UI
# Open browser: http://72.60.175.144:5678
```

### Database
```bash
# Connect to primary database (Neon)
psql "postgresql://neondb_owner:npg_c3UNa4KOlCeL@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require"

# Quick query
psql "<DATABASE_URL>" -c "SELECT * FROM ralph_stories;"

# Run migration
psql "<DATABASE_URL>" -f migrations/010_ralph_system.sql
```

### Ralph System
```bash
# Check Ralph status
/root/ralph/scripts/check_status.sh

# Detect databases
/root/ralph/scripts/detect_databases.sh

# Database status
/root/ralph/scripts/db_manager.sh status

# Run Ralph (3 iterations)
cd /root/ralph && ./scripts/ralph_loop.sh 3

# View Ralph logs
ls -lt /root/ralph/logs/ | head
cat /root/ralph/logs/ORG-001_*.log
```

### Git
```bash
# Check status
cd /root/Rivet-PRO && git status

# View recent commits
git log --oneline -10

# Create commit
git add .
git commit -m "feat: your message"
git push origin feat/branch-name

# Check current branch
git branch
```

### Telegram Bots
```bash
# Test bot connection
curl https://api.telegram.org/bot<BOT_TOKEN>/getMe

# Get recent updates
curl https://api.telegram.org/bot<BOT_TOKEN>/getUpdates

# Send notification
/root/ralph/scripts/notify_telegram.sh "Test message"
```

---

## 📁 Folder Structure

```
/root/Rivet-PRO/                    # Main project directory
├── .env                             # Environment variables (NEVER commit!)
├── .git/                            # Git repository
├── CLAUDE.md                        # Instructions for Claude AI
├── PROJECT_STATUS.md                # This project's status
├── QUICK_REFERENCE.md               # This file
│
├── rivet/                           # Core application code
│   ├── core/                        # Core services (database, logging)
│   │   ├── database_manager.py      # Database connection pooling
│   │   └── trace_logger.py          # Logging infrastructure
│   ├── integrations/                # External service integrations
│   │   └── telegram/                # Telegram bot code
│   │       ├── orchestrator_bot.py  # @RivetCeo_bot
│   │       └── cmms_bot.py          # @RivetCMMS_bot
│   └── services/                    # Business logic
│
├── rivet_pro/                       # RIVET Pro specific code
│   └── migrations/                  # Database migrations
│       └── 010_ralph_system.sql     # Ralph tables schema
│
├── rivet-n8n-workflow/              # n8n workflow definitions
│   ├── rivet_workflow.json          # Main workflow
│   └── *.json                       # Various workflow exports
│
├── docs/                            # Documentation
│   └── N8N_WORKFLOWS.md             # Workflow map
│
└── tests/                           # Test files

/root/ralph/                         # Ralph autonomous system
├── scripts/                         # Bash scripts
│   ├── ralph_loop.sh                # Main orchestration loop
│   ├── run_story.sh                 # Story execution wrapper
│   ├── db_manager.sh                # Database failover manager
│   ├── detect_databases.sh          # Auto-detect databases
│   ├── sync_databases.sh            # Multi-DB sync
│   ├── notify_telegram.sh           # Send Telegram messages
│   └── check_status.sh              # Status monitoring
├── config/                          # Configuration files
│   ├── .env                         # Environment variables (copy of main)
│   ├── databases.conf               # Detected databases
│   └── primary.conf                 # Selected primary database
└── logs/                            # Execution logs
    └── *.log                        # Story execution logs
```

---

## 🚀 Quick Start (New Developer)

### 1. Get Access
```bash
# Request SSH access to VPS
# Get .env file from team lead (NEVER in git!)
```

### 2. First Connection
```bash
# Connect to VPS
ssh root@72.60.175.144

# Navigate to project
cd /root/Rivet-PRO

# Check git status
git status
git log -5

# Verify environment
cat .env | grep -v "KEY\|TOKEN\|PASSWORD"  # Check structure (not secrets!)
```

### 3. Test Everything
```bash
# Test database connection
psql "$DATABASE_URL" -c "SELECT 1;"

# Test n8n
curl http://localhost:5678/healthz

# Test Telegram bot
curl https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe

# Test Ralph
/root/ralph/scripts/check_status.sh
```

### 4. Make First Change
```bash
# Create branch
git checkout -b feature/your-feature

# Make changes
# ... edit files ...

# Test locally
# ... run tests ...

# Commit
git add <files>
git commit -m "feat: describe your change"

# Push
git push origin feature/your-feature
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| **Can't connect to VPS** | Check SSH keys, VPN if required |
| **Database connection fails** | Check .env has correct DATABASE_URL, test with psql |
| **n8n workflows not working** | Check credentials are wired, check execution logs |
| **Telegram bot not responding** | Verify bot token, check webhook setup |
| **Ralph hanging** | Known issue: Claude CLI hangs in automation |
| **Git conflicts** | Pull latest, resolve conflicts, commit |

---

## 📚 Key Documentation

| File | Purpose |
|------|---------|
| `PROJECT_STATUS.md` | Current project state, what works/broken |
| `docs/N8N_WORKFLOWS.md` | Map of all n8n workflows |
| `QUICK_REFERENCE.md` | This file - quick start guide |
| `CLAUDE.md` | Instructions for Claude AI assistant |
| `README.md` | Project overview (TBD) |

---

## 🔧 Development Workflow

1. **Plan**: Create story in ralph_stories table or discuss in team
2. **Branch**: `git checkout -b feature/story-name`
3. **Develop**: Write code, test locally
4. **Test**: Run test suite (command TBD)
5. **Commit**: `git commit -m "feat(STORY-ID): description"`
6. **Push**: `git push origin feature/story-name`
7. **Review**: Create PR, request review
8. **Merge**: After approval, merge to main
9. **Deploy**: Push to production (manual currently)

---

## 📞 Support

- **Project Lead**: (contact TBD)
- **Repository**: (GitHub URL TBD)
- **Slack/Discord**: (channel TBD)
- **Documentation**: `/root/Rivet-PRO/docs/`

---

**Generated**: 2026-01-11 | **One-Page Reference** - Keep it concise!
