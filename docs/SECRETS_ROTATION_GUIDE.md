# RIVET Pro - Secrets Rotation Guide

**Created:** January 17, 2026
**Story:** PHOTO-SEC-001
**Status:** CRITICAL - Secrets were exposed in git history

---

## Overview

This guide documents all secrets that need rotation after exposure in git history.

## Exposed Secrets Inventory

### AI/LLM API Keys (5 Keys)

| Service | Key Prefix | Dashboard URL | Priority |
|---------|------------|---------------|----------|
| Anthropic | `sk-ant-api03-...` | https://console.anthropic.com/settings/keys | HIGH |
| OpenAI | `sk-proj-...` | https://platform.openai.com/api-keys | HIGH |
| Groq | `gsk_...` | https://console.groq.com/keys | HIGH |
| Google AI | `AIzaSy...` | https://console.cloud.google.com/apis/credentials | HIGH |
| DeepSeek | `sk-...` | https://platform.deepseek.com/api-keys | MEDIUM |

### Database Credentials (4 Services)

| Service | Connection Info | Dashboard URL | Priority |
|---------|----------------|---------------|----------|
| Neon | `ep-purple-hall-ahimeyn0` | https://console.neon.tech | HIGH |
| Supabase | `mggqgrxwumnnujojndub` | https://supabase.com/dashboard | HIGH |
| VPS PostgreSQL | `72.60.175.144` | SSH to VPS | MEDIUM |
| CockroachDB | Placeholder only | N/A | LOW |

### Telegram Bot Tokens (6 Bots)

| Bot Name | Username | Dashboard | Priority |
|----------|----------|-----------|----------|
| Rivet CMMS | @RivetCMMS_bot | https://t.me/BotFather | HIGH |
| Rivet CEO | @RivetCeo_bot | https://t.me/BotFather | HIGH |
| Test Bot | @testbotrivet_bot | https://t.me/BotFather | LOW |
| Agent Factory | @AgentFactoryRemote_bot | https://t.me/BotFather | MEDIUM |
| Chat With Print | @chatwithprint_bot | https://t.me/BotFather | LOW |
| Glen | @Seedofchucky_bot | https://t.me/BotFather | LOW |

### Platform API Keys

| Service | Key Type | Dashboard URL | Priority |
|---------|----------|---------------|----------|
| GitHub | `ghp_...` | https://github.com/settings/tokens | HIGH |
| Stripe | `sk_test_...` | https://dashboard.stripe.com/apikeys | HIGH |
| Slack | Bot Token + Secrets | https://api.slack.com/apps | MEDIUM |
| N8N Cloud | JWT Token | https://n8n.io/cloud | MEDIUM |
| Neon API | `napi_...` | https://console.neon.tech/app/settings/api-keys | HIGH |

### Observability & Search APIs

| Service | Key Prefix | Dashboard URL | Priority |
|---------|------------|---------------|----------|
| LangFuse | `sk-lf-...` | https://cloud.langfuse.com | MEDIUM |
| LangSmith | `lsv2_pt_...` | https://smith.langchain.com/settings | MEDIUM |
| Brave Search | `BSA...` | https://brave.com/search/api/ | LOW |
| Tavily | `tvly-...` | https://tavily.com | LOW |
| Serper | (32 char) | https://serper.dev | LOW |
| Firecrawl | `fc-...` | https://firecrawl.dev | LOW |

### Hosting Platforms

| Service | Key Type | Dashboard URL | Priority |
|---------|----------|---------------|----------|
| Hostinger | API Token | https://hpanel.hostinger.com | LOW |
| Render | `rnd_...` | https://dashboard.render.com | LOW |
| Railway | UUID | https://railway.app/account | LOW |

### Misc Keys

| Service | Dashboard URL | Priority |
|---------|---------------|----------|
| CodeRabbit | https://coderabbit.ai/settings | LOW |
| Miro | https://miro.com/app/settings | LOW |
| Manus | N/A | LOW |

---

## Rotation Procedure

### Step 1: AI/LLM Keys (Do First)

```bash
# 1. Anthropic (most critical - Claude access)
# Go to: https://console.anthropic.com/settings/keys
# - Delete old key: sk-ant-api03-lTwI...
# - Create new key
# - Update .env with new value

# 2. OpenAI
# Go to: https://platform.openai.com/api-keys
# - Revoke old key
# - Create new key
# - Update .env

# 3. Groq
# Go to: https://console.groq.com/keys
# - Delete old key
# - Create new key
# - Update .env

# 4. Google AI
# Go to: https://console.cloud.google.com/apis/credentials
# - Delete old key
# - Create new key
# - Update .env

# 5. DeepSeek
# Go to: https://platform.deepseek.com/api-keys
# - Rotate key
# - Update .env
```

### Step 2: Database Credentials

```bash
# 1. Neon PostgreSQL
# Go to: https://console.neon.tech
# - Project: ep-purple-hall-ahimeyn0
# - Reset role password for neondb_owner
# - Update DATABASE_URL, NEON_DB_URL in .env

# 2. Supabase
# Go to: https://supabase.com/dashboard/project/mggqgrxwumnnujojndub/settings/database
# - Reset database password
# - Update SUPABASE_DB_URL, SUPABASE_DB_PASSWORD in .env

# 3. VPS PostgreSQL
ssh root@72.60.175.144
sudo -u postgres psql
ALTER USER rivet WITH PASSWORD 'new_secure_password_here';
\q
# Update VPS_KB_PASSWORD in .env
```

### Step 3: Telegram Bot Tokens

```bash
# For each bot, message @BotFather:
# 1. /mybots
# 2. Select the bot
# 3. API Token → Revoke current token
# 4. Copy new token to .env

# Bots to rotate (in order of priority):
# - @RivetCMMS_bot (TELEGRAM_BOT_TOKEN)
# - @RivetCeo_bot (ORCHESTRATOR_BOT_TOKEN)
# - @AgentFactoryRemote_bot (AGENT_FACTORY_BOT_TOKEN)
# - Others as needed
```

### Step 4: Platform Tokens

```bash
# GitHub Personal Access Token
# Go to: https://github.com/settings/tokens
# - Delete the existing token (find it in your .env file)
# - Create new fine-grained token with minimal scopes
# - Update GITHUB_TOKEN in .env

# Stripe (if using)
# Go to: https://dashboard.stripe.com/apikeys
# - Roll keys
# - Update STRIPE_SECRET_KEY

# Slack
# Go to: https://api.slack.com/apps
# - Regenerate Bot Token
# - Regenerate Signing Secret
# - Update all SLACK_* vars

# Neon API Key
# Go to: https://console.neon.tech/app/settings/api-keys
# - Delete old key
# - Create new key
# - Update NEON_API_KEY
```

---

## Removing .env from Git History

**WARNING:** This rewrites history. Coordinate with team before running.

### Option 1: git filter-repo (Recommended)

```bash
# Install git filter-repo
pip install git-filter-repo

# Backup first
git clone --mirror https://github.com/Mikecranesync/Rivet-PRO.git backup-repo

# Remove .env files from all history
cd Rivet-PRO
git filter-repo --path .env --invert-paths
git filter-repo --path rivet_pro/.env --invert-paths
git filter-repo --path archive/ --invert-paths

# Force push (DANGER: rewrites history)
git push origin --force --all
git push origin --force --tags
```

### Option 2: BFG Repo-Cleaner

```bash
# Download BFG
# https://rtyley.github.io/bfg-repo-cleaner/

# Clone a fresh mirror
git clone --mirror https://github.com/Mikecranesync/Rivet-PRO.git

# Remove .env files
java -jar bfg.jar --delete-files .env Rivet-PRO.git

# Clean and push
cd Rivet-PRO.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force
```

---

## Fly.io Secrets Management

Once secrets are rotated, set them in Fly.io:

```bash
# Install Fly CLI (if not installed)
# Windows: iwr https://fly.io/install.ps1 -useb | iex
# macOS/Linux: curl -L https://fly.io/install.sh | sh

# Login to Fly.io
fly auth login

# Set all secrets (from rotated .env)
fly secrets set \
  TELEGRAM_BOT_TOKEN="new_token_here" \
  DATABASE_URL="postgresql://..." \
  ANTHROPIC_API_KEY="sk-ant-..." \
  OPENAI_API_KEY="sk-proj-..." \
  GROQ_API_KEY="gsk_..." \
  GOOGLE_API_KEY="AIzaSy..." \
  # ... add all required keys

# Verify secrets are set
fly secrets list
```

---

## VPS Secrets Update

For the current VPS deployment:

```bash
# SSH to VPS
ssh root@72.60.175.144

# Edit .env
nano /opt/Rivet-PRO/.env

# Restart service
systemctl restart rivet-bot

# Verify running
systemctl status rivet-bot
journalctl -u rivet-bot -n 20
```

---

## Post-Rotation Verification Checklist

- [ ] All AI/LLM keys rotated and tested
- [ ] Database connections working with new passwords
- [ ] Telegram bots responding with new tokens
- [ ] GitHub token working for repo access
- [ ] .env removed from git history
- [ ] New .env NOT committed to git
- [ ] VPS .env updated
- [ ] Fly.io secrets set (if deploying there)
- [ ] All services tested end-to-end

---

## Security Best Practices Going Forward

1. **Never commit .env files** - Already in .gitignore
2. **Use .env.example** - Template without real values
3. **Rotate keys quarterly** - Set calendar reminder
4. **Use scoped tokens** - Minimal permissions needed
5. **Monitor for leaks** - Enable GitHub secret scanning
6. **Document in 1Password/Vault** - Not in git

---

## Emergency Contacts

If keys are compromised:
- Anthropic: support@anthropic.com
- OpenAI: abuse@openai.com
- Telegram: @BotSupport
- GitHub: security@github.com
