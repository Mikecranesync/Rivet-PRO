# RIVET Pro - Production Deployment Guide

**Target Deployment**: Ubuntu VPS (72.60.175.144)
**Estimated Time**: 2 hours for fresh deployment
**Prerequisites**: Root or sudo access to VPS

---

## Table of Contents

1. [VPS Requirements](#vps-requirements)
2. [Required Accounts](#required-accounts)
3. [Initial VPS Setup](#initial-vps-setup)
4. [Database Setup](#database-setup)
5. [Application Deployment](#application-deployment)
6. [n8n Setup](#n8n-setup)
7. [HTTPS Webhook Configuration](#https-webhook-configuration)
8. [Systemd Services](#systemd-services)
9. [Monitoring & Logs](#monitoring--logs)
10. [Common Issues](#common-issues)

---

## VPS Requirements

**Minimum Specifications**:
- **OS**: Ubuntu 22.04 LTS or newer
- **RAM**: 2GB minimum (4GB recommended)
- **Disk**: 20GB SSD
- **Network**: Static IP address
- **Ports**: 80 (HTTP), 443 (HTTPS), 5678 (n8n), 8443 (Telegram webhook)

**Software Requirements**:
- Python 3.11+
- PostgreSQL client (psycopg2)
- Git
- Nginx (reverse proxy)
- Certbot (Let's Encrypt SSL)
- Node.js 18+ (for n8n)

---

## Required Accounts

Before starting deployment, ensure you have:

### 1. Neon Database (PostgreSQL)
- Sign up: https://neon.tech
- Create a new project
- Copy the connection string (DATABASE_URL)

### 2. Telegram Bot
- Contact @BotFather on Telegram
- Create new bot with `/newbot` command
- Copy the bot token (TELEGRAM_BOT_TOKEN)

### 3. Google Gemini API
- Go to: https://ai.google.dev
- Create API key for Gemini Vision
- Copy API key (GOOGLE_API_KEY)

### 4. Stripe Payment Processing
- Sign up: https://stripe.com
- Get API keys from Dashboard
- Create a monthly subscription product ($29/month)
- Copy: STRIPE_API_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_ID

### 5. Anthropic Claude API
- Sign up: https://console.anthropic.com
- Create API key
- Copy key (ANTHROPIC_API_KEY)

---

## Initial VPS Setup

### 1. Connect to VPS

```bash
ssh root@72.60.175.144
# Or use your VPS IP address
```

### 2. Update System

```bash
apt update && apt upgrade -y
```

### 3. Install System Dependencies

```bash
# Install Python 3.11
apt install -y python3.11 python3.11-venv python3-pip

# Install PostgreSQL client
apt install -y libpq-dev

# Install Git
apt install -y git

# Install Nginx
apt install -y nginx

# Install Certbot for SSL
apt install -y certbot python3-certbot-nginx

# Install Node.js 18 (for n8n)
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs
```

### 4. Create Application User

```bash
# Create rivet user (non-root for security)
useradd -m -s /bin/bash rivet
usermod -aG sudo rivet
su - rivet
```

---

## Database Setup

### 1. Configure Neon Database

From your local machine with psql installed:

```bash
# Connect to Neon database
psql "postgresql://[neon-connection-string]"

# Run migrations
\i rivet_pro/migrations/001_initial_schema.sql
\i rivet_pro/migrations/002_equipment_tables.sql
\i rivet_pro/migrations/003_work_orders.sql
\i rivet_pro/migrations/011_usage_tracking.sql
\i rivet_pro/migrations/012_stripe_integration.sql
```

Or from VPS after cloning repo:

```bash
cd /home/rivet/Rivet-PRO
export DATABASE_URL="postgresql://[your-neon-connection-string]"
python3 rivet_pro/migrations/run_migrations.py
```

### 2. Verify Database Schema

```sql
-- List all tables
\dt

-- Expected tables:
-- cmms_equipment
-- work_orders
-- technicians
-- usage_tracking
-- stripe_subscriptions
```

---

## Application Deployment

### 1. Clone Repository

```bash
cd /home/rivet
git clone https://github.com/your-org/Rivet-PRO.git
cd Rivet-PRO
git checkout main  # Or production branch
```

### 2. Create Python Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create `.env` file in project root:

```bash
cp .env.example .env
nano .env
```

Fill in all required variables (see `.env.example` for reference):

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_BOT_MODE=webhook
TELEGRAM_WEBHOOK_URL=https://your-domain.com/telegram-webhook
TELEGRAM_WEBHOOK_SECRET=random_secret_string_here

# Database
DATABASE_URL=postgresql://user:pass@host/db

# AI APIs
GOOGLE_API_KEY=your_gemini_key
ANTHROPIC_API_KEY=your_claude_key

# Stripe
STRIPE_API_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...

# Application
JWT_SECRET_KEY=random_secret_key_here
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### 5. Test Application

```bash
# Test bot (polling mode first)
cd rivet_pro
python -m adapters.telegram.bot

# Test API
python -m adapters.web.main
```

Press Ctrl+C to stop after verifying no errors.

---

## n8n Setup

### 1. Install n8n

```bash
npm install -g n8n
```

### 2. Configure n8n

Create n8n data directory:

```bash
mkdir -p /home/rivet/.n8n
```

Set n8n environment variables in `.env`:

```env
N8N_PORT=5678
N8N_HOST=0.0.0.0
N8N_PROTOCOL=https
N8N_EDITOR_BASE_URL=https://your-domain.com:5678
WEBHOOK_URL=https://your-domain.com
```

### 3. Start n8n (first time)

```bash
n8n start
```

Access n8n at: http://72.60.175.144:5678

### 4. Import Workflows

1. **Photo Bot v2 Workflow**:
   - Login to n8n UI
   - Go to Workflows → Import from File
   - Import: `rivet-n8n-workflow/photo_bot_v2.json`
   - Workflow ID: 7LMKcMmldZsu1l6g

2. **Ralph Main Loop Workflow** (optional):
   - Import: `rivet-n8n-workflow/ralph_main_loop.json`

### 5. Configure n8n Credentials

For each workflow, configure these credentials:

**Gemini API Credential**:
- Name: "Google Gemini"
- Type: Google API
- API Key: [Your GOOGLE_API_KEY]

**Neon PostgreSQL Credential**:
- Name: "Neon Database"
- Type: PostgreSQL
- Host: [From DATABASE_URL]
- Port: 5432
- Database: [From DATABASE_URL]
- User: [From DATABASE_URL]
- Password: [From DATABASE_URL]
- SSL: Require

**Telegram Credential** (if using n8n Telegram nodes):
- Name: "RIVET Bot"
- Type: Telegram API
- Access Token: [Your TELEGRAM_BOT_TOKEN]

### 6. Test Workflows

1. Open Photo Bot v2 workflow
2. Click "Execute Workflow" button
3. Upload test image (motor nameplate photo)
4. Verify execution succeeds and returns equipment identification
5. Check execution logs for errors

---

## HTTPS Webhook Configuration

Choose one approach:

### Option A: ngrok (Quick MVP - Development)

```bash
# Install ngrok
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar -xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/

# Start ngrok tunnel
ngrok http 8443

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Update .env:
TELEGRAM_WEBHOOK_URL=https://abc123.ngrok.io/telegram-webhook
```

**Pros**: Fast setup (5 minutes)
**Cons**: URL changes on restart, not for production

### Option B: Let's Encrypt SSL (Production-Ready)

#### 1. Configure DNS

Point your domain to VPS IP:

```
A record: rivet-cmms.com → 72.60.175.144
```

Wait for DNS propagation (5-30 minutes).

#### 2. Configure Nginx

Create nginx configuration:

```bash
sudo nano /etc/nginx/sites-available/rivet-pro
```

```nginx
# Telegram Webhook Server
server {
    listen 80;
    server_name rivet-cmms.com;

    location /telegram-webhook {
        proxy_pass http://127.0.0.1:8443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # n8n workflows
    location /webhook/ {
        proxy_pass http://127.0.0.1:5678;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/rivet-pro /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 3. Install SSL Certificate

```bash
sudo certbot --nginx -d rivet-cmms.com
# Follow prompts, choose redirect HTTP to HTTPS
```

Certbot will automatically update nginx config to use HTTPS.

#### 4. Update Environment

Update `.env`:

```env
TELEGRAM_BOT_MODE=webhook
TELEGRAM_WEBHOOK_URL=https://rivet-cmms.com/telegram-webhook
```

#### 5. Test Webhook

```bash
# Test nginx is forwarding
curl https://rivet-cmms.com/telegram-webhook

# Expected: Connection to bot webhook endpoint
```

---

## Systemd Services

Create systemd service files for automatic startup and restart.

### 1. Telegram Bot Service

```bash
sudo nano /etc/systemd/system/rivet-bot.service
```

```ini
[Unit]
Description=RIVET Telegram Bot
After=network.target

[Service]
Type=simple
User=rivet
WorkingDirectory=/home/rivet/Rivet-PRO
Environment="PATH=/home/rivet/Rivet-PRO/venv/bin"
ExecStart=/home/rivet/Rivet-PRO/venv/bin/python -m rivet_pro.adapters.telegram.bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. Web API Service

```bash
sudo nano /etc/systemd/system/rivet-api.service
```

```ini
[Unit]
Description=RIVET Web API
After=network.target

[Service]
Type=simple
User=rivet
WorkingDirectory=/home/rivet/Rivet-PRO
Environment="PATH=/home/rivet/Rivet-PRO/venv/bin"
ExecStart=/home/rivet/Rivet-PRO/venv/bin/uvicorn rivet_pro.adapters.web.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3. n8n Service

```bash
sudo nano /etc/systemd/system/n8n.service
```

```ini
[Unit]
Description=n8n Workflow Automation
After=network.target

[Service]
Type=simple
User=rivet
Environment="N8N_PORT=5678"
Environment="N8N_PROTOCOL=https"
Environment="WEBHOOK_URL=https://rivet-cmms.com"
ExecStart=/usr/bin/n8n start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 4. Enable and Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services (start on boot)
sudo systemctl enable rivet-bot
sudo systemctl enable rivet-api
sudo systemctl enable n8n

# Start services
sudo systemctl start rivet-bot
sudo systemctl start rivet-api
sudo systemctl start n8n

# Check status
sudo systemctl status rivet-bot
sudo systemctl status rivet-api
sudo systemctl status n8n
```

---

## Monitoring & Logs

### Service Logs

```bash
# View bot logs
sudo journalctl -u rivet-bot -f

# View API logs
sudo journalctl -u rivet-api -f

# View n8n logs
sudo journalctl -u n8n -f

# View last 100 lines
sudo journalctl -u rivet-bot -n 100
```

### Application Logs

Logs are written to:

```
/home/rivet/Rivet-PRO/logs/
  ├── bot.log       # Telegram bot logs
  ├── api.log       # Web API logs
  └── errors.log    # Error logs
```

View logs:

```bash
tail -f /home/rivet/Rivet-PRO/logs/bot.log
tail -f /home/rivet/Rivet-PRO/logs/api.log
```

### Monitoring Checklist

Daily checks:

```bash
# 1. Check service status
sudo systemctl status rivet-bot rivet-api n8n

# 2. Check disk space
df -h

# 3. Check memory usage
free -m

# 4. Check recent errors
sudo journalctl -p err -n 50

# 5. Test bot
# Send a message to your bot on Telegram

# 6. Test API
curl https://rivet-cmms.com/api/version
```

### Health Check Endpoint

Monitor API health:

```bash
curl https://rivet-cmms.com/health
```

Expected response:

```json
{
  "status": "healthy",
  "service": "rivet-pro-api",
  "version": "1.0.0",
  "environment": "production",
  "database": {
    "healthy": true
  }
}
```

---

## Common Issues

### Issue 1: Bot Not Receiving Messages (Webhook Mode)

**Symptoms**: Bot doesn't respond to messages, no errors in logs

**Diagnosis**:

```bash
# Check if webhook is set
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo

# Check nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

**Solutions**:

1. Verify `TELEGRAM_WEBHOOK_URL` is correct in `.env`
2. Check nginx is forwarding to port 8443
3. Verify SSL certificate is valid
4. Try deleting and re-setting webhook:

```bash
# Delete webhook
curl https://api.telegram.org/bot<TOKEN>/deleteWebhook

# Restart bot service
sudo systemctl restart rivet-bot
```

### Issue 2: Database Connection Errors

**Symptoms**: `asyncpg.exceptions.ConnectionFailureError`

**Solutions**:

1. Verify `DATABASE_URL` is correct
2. Check Neon database is not suspended (free tier timeout)
3. Verify firewall allows outbound PostgreSQL connections
4. Test connection manually:

```bash
psql "$DATABASE_URL"
```

### Issue 3: OCR Not Working

**Symptoms**: Photo uploads fail with "Failed to analyze photo"

**Solutions**:

1. Verify `GOOGLE_API_KEY` is set correctly
2. Check Gemini API quota/billing
3. Check n8n Photo Bot v2 workflow is active
4. Test n8n workflow manually (upload test image)
5. Check n8n logs:

```bash
sudo journalctl -u n8n -n 100
```

### Issue 4: Stripe Webhook Errors

**Symptoms**: Payments succeed but subscription not activated

**Solutions**:

1. Verify `STRIPE_WEBHOOK_SECRET` matches Stripe dashboard
2. Check webhook endpoint is reachable:

```bash
curl -X POST https://rivet-cmms.com/api/stripe/webhook \
  -H "Content-Type: application/json" \
  -d '{}'
```

3. Check Stripe dashboard → Webhooks → Endpoint details → Recent deliveries
4. Verify webhook URL in Stripe is `https://rivet-cmms.com/api/stripe/webhook`

### Issue 5: High Memory Usage

**Symptoms**: VPS running out of memory, services crashing

**Solutions**:

1. Check memory usage:

```bash
free -m
ps aux --sort=-%mem | head -20
```

2. Adjust database pool size in `settings.py`:

```python
database_pool_max_size: int = Field(5)  # Reduce from 10
```

3. Restart services to free memory:

```bash
sudo systemctl restart rivet-bot rivet-api n8n
```

4. Consider upgrading VPS to 4GB RAM

### Issue 6: Services Not Starting on Boot

**Symptoms**: After reboot, bot/API not running

**Solutions**:

```bash
# Check if services are enabled
sudo systemctl is-enabled rivet-bot rivet-api n8n

# Enable if not enabled
sudo systemctl enable rivet-bot
sudo systemctl enable rivet-api
sudo systemctl enable n8n

# Check boot logs
sudo journalctl -b -p err
```

### Issue 7: SSL Certificate Expired

**Symptoms**: Webhook errors, HTTPS not working

**Solutions**:

```bash
# Check certificate expiry
sudo certbot certificates

# Renew certificate
sudo certbot renew

# Test auto-renewal
sudo certbot renew --dry-run

# Reload nginx
sudo systemctl reload nginx
```

---

## Security Best Practices

1. **Use non-root user**: Deploy as `rivet` user, not `root`
2. **Keep secrets secure**: Never commit `.env` to git
3. **Use strong JWT secret**: Generate with `openssl rand -hex 32`
4. **Enable firewall**: Use `ufw` to restrict ports
5. **Regular updates**: Run `apt update && apt upgrade` weekly
6. **Monitor logs**: Check for suspicious activity daily
7. **Backup database**: Export Neon database weekly
8. **Use HTTPS everywhere**: Never use HTTP in production

---

## Deployment Checklist

Before going live, verify:

- [ ] All services running: `sudo systemctl status rivet-bot rivet-api n8n`
- [ ] Database migrations applied
- [ ] n8n workflows imported and credentials configured
- [ ] SSL certificate valid and auto-renewal enabled
- [ ] Webhook URL set and tested
- [ ] Bot responds to messages on Telegram
- [ ] Photo OCR working (upload test image)
- [ ] Stripe webhooks receiving events
- [ ] Health check endpoint returns 200
- [ ] Logs are being written correctly
- [ ] Services restart on failure (test by killing process)
- [ ] Services start on boot (test by rebooting VPS)

---

## Getting Help

- **Documentation**: See `README.md`, `STATUS_REPORT.md`, `MVP_ROADMAP.md`
- **Logs**: Check `/home/rivet/Rivet-PRO/logs/` and `journalctl`
- **Database**: Query Neon console for data issues
- **n8n**: Check workflow execution logs in n8n UI
- **Telegram**: Use @BotFather to verify bot settings

---

**Last Updated**: 2026-01-11
**Version**: 1.0.0
**For**: RIVET Pro MVP Launch
