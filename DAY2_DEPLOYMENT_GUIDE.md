# Day 2: VPS Deployment Guide

## ✅ Pre-Deployment Checklist

**Completed:**
- ✅ Bot wired to OCR and SME services
- ✅ .env file created with Agent Factory configuration
- ✅ Requirements.txt ready
- ✅ Test script created

**Before deploying:**
1. Test locally
2. Verify all imports work
3. Push code to GitHub (if not already)
4. SSH access to VPS confirmed

---

## Step 1: Test Locally First

**IMPORTANT:** Always test locally before deploying to VPS.

```bash
cd rivet_pro/

# Install dependencies
pip install -r requirements.txt

# Test imports and configuration
python test_imports.py

# If all tests pass, start bot
python start_bot.py
```

**Expected output:**
```
============================================================
RIVET PRO - Import & Configuration Test
============================================================

Testing imports...
✅ Core services imported successfully
✅ Settings loaded (bot token: ********************_nYo)
✅ Observability/logging working
✅ Telegram bot imported successfully

✅ All critical imports successful!

Testing environment variables...
  ✅ telegram_bot_token: ********************_nYo
  ✅ database_url: ********************neondb
  ✅ groq_api_key: ********************2D
  ✅ google_api_key: ********************jlA

✅ All required environment variables set!

🚀 Ready for deployment!
```

**Test the bot:**
1. Open Telegram
2. Search for your bot: @RivetCMMSBot
3. Send `/start` - should get welcome message
4. Send a photo of equipment nameplate - should get OCR results
5. Send text like "Siemens G120C fault F0001" - should get expert response

**If local testing works, proceed to VPS deployment.**

---

## Step 2: Push Code to GitHub

```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO

# Check status
git status

# Add all new files
git add rivet_pro/adapters/telegram/bot.py
git add rivet_pro/adapters/telegram/__main__.py
git add rivet_pro/start_bot.py
git add rivet_pro/test_imports.py
git add DAY1_COMPLETE.md
git add DAY2_DEPLOYMENT_GUIDE.md

# Commit
git commit -m "$(cat <<'EOF'
Day 1 Complete: Wire OCR & SME services to Telegram bot

- Wire photo handler to OCR service with streaming UX
- Wire text handler to SME routing
- Create bot runner scripts (__main__.py, start_bot.py)
- Extract .env configuration from Agent Factory
- Add import test script for pre-deployment validation

Bot now supports:
- Photo → OCR (nameplate identification)
- Text → SME expert routing
- Message streaming (progressive updates)
- Error handling

Ready for VPS deployment (Day 2).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"

# Push to GitHub
git push origin main
```

---

## Step 3: Deploy to VPS (72.60.175.144)

### 3.1 Connect to VPS

```bash
ssh root@72.60.175.144
```

### 3.2 Clone or Pull Repository

**If first deployment:**
```bash
cd /opt/
git clone https://github.com/YOUR_USERNAME/Rivet-PRO.git
cd Rivet-PRO/rivet_pro
```

**If updating existing deployment:**
```bash
cd /opt/Rivet-PRO
git pull origin main
cd rivet_pro
```

### 3.3 Create .env File on VPS

**Option A: Copy from local machine (recommended)**
```bash
# On your local Windows machine
scp C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\rivet_pro\.env root@72.60.175.144:/opt/Rivet-PRO/rivet_pro/
```

**Option B: Create manually on VPS**
```bash
nano /opt/Rivet-PRO/rivet_pro/.env
# Paste the contents from local .env file
# Press Ctrl+X, then Y, then Enter to save
```

### 3.4 Set Up Python Virtual Environment

```bash
cd /opt/Rivet-PRO/rivet_pro

# Create virtual environment
python3.11 -m venv venv

# Activate
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

**Expected time:** 2-3 minutes

### 3.5 Run Database Migrations

```bash
python run_migrations.py
```

**Expected output:**
```
Running migrations...
✅ 001_initial_schema.sql
✅ 002_equipment_models.sql
✅ 003_cmms_equipment.sql
✅ 004_work_orders.sql
✅ 005_interactions.sql
✅ 006_subscription_limits.sql
All migrations complete!
```

### 3.6 Test Bot on VPS

```bash
# Test imports
python test_imports.py

# If tests pass, run bot
python start_bot.py
```

**Test in Telegram:**
- Send /start
- Send a photo
- Send a question

**If everything works, press Ctrl+C to stop the bot.**

---

## Step 4: Set Up Systemd Service (24/7 Operation)

### 4.1 Create Service File

```bash
sudo nano /etc/systemd/system/rivet-bot.service
```

**Paste this configuration:**
```ini
[Unit]
Description=RIVET Pro Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/Rivet-PRO/rivet_pro
Environment="PATH=/opt/Rivet-PRO/rivet_pro/venv/bin"
ExecStart=/opt/Rivet-PRO/rivet_pro/venv/bin/python start_bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Save:** Press Ctrl+X, then Y, then Enter

### 4.2 Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable rivet-bot

# Start service
sudo systemctl start rivet-bot

# Check status
sudo systemctl status rivet-bot
```

**Expected output:**
```
● rivet-bot.service - RIVET Pro Telegram Bot
     Loaded: loaded (/etc/systemd/system/rivet-bot.service; enabled; vendor preset: enabled)
     Active: active (running) since Sun 2026-01-05 03:00:00 UTC; 5s ago
   Main PID: 12345 (python)
      Tasks: 3 (limit: 2345)
     Memory: 45.2M
        CPU: 1.234s
     CGroup: /system.slice/rivet-bot.service
             └─12345 /opt/Rivet-PRO/rivet_pro/venv/bin/python start_bot.py

Jan 05 03:00:00 vps systemd[1]: Started RIVET Pro Telegram Bot.
Jan 05 03:00:01 vps python[12345]: ============================================================
Jan 05 03:00:01 vps python[12345]: 🤖 Starting RIVET Pro Telegram Bot
Jan 05 03:00:01 vps python[12345]: ============================================================
Jan 05 03:00:02 vps python[12345]: ✅ Bot is now running. Press Ctrl+C to stop.
```

---

## Step 5: Monitor and Manage Bot

### View Logs (Real-time)

```bash
sudo journalctl -u rivet-bot -f
```

**Expected output:**
```
Jan 05 03:00:02 vps python[12345]: INFO:rivet_pro.adapters.telegram.bot:Starting Telegram bot with polling...
Jan 05 03:00:03 vps python[12345]: INFO:rivet_pro.adapters.telegram.bot:✅ Telegram bot is running and polling for updates
Jan 05 03:15:23 vps python[12345]: INFO:rivet_pro.adapters.telegram.bot:User started bot | user_id=8445149012 | username=kai_
Jan 05 03:15:45 vps python[12345]: INFO:rivet_pro.adapters.telegram.bot:Received message | user_id=8445149012 | type=photo
Jan 05 03:15:46 vps python[12345]: INFO:rivet_pro.adapters.telegram.bot:Downloaded photo | user_id=8445149012 | size=234567 bytes
Jan 05 03:15:48 vps python[12345]: INFO:rivet_pro.adapters.telegram.bot:OCR complete | manufacturer=Siemens | model=G120C | confidence=0.94
```

### Common Commands

```bash
# Stop bot
sudo systemctl stop rivet-bot

# Start bot
sudo systemctl start rivet-bot

# Restart bot (after code changes)
sudo systemctl restart rivet-bot

# Check status
sudo systemctl status rivet-bot

# View logs (last 100 lines)
sudo journalctl -u rivet-bot -n 100

# View logs (real-time)
sudo journalctl -u rivet-bot -f

# Disable service (won't start on boot)
sudo systemctl disable rivet-bot
```

---

## Step 6: Update Bot After Code Changes

**Workflow when you make changes locally:**

```bash
# 1. On local machine: Push changes
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
git add .
git commit -m "Your changes"
git push origin main

# 2. On VPS: Pull and restart
ssh root@72.60.175.144
cd /opt/Rivet-PRO
git pull origin main
cd rivet_pro
source venv/bin/activate
pip install -r requirements.txt  # If dependencies changed
sudo systemctl restart rivet-bot

# 3. Check logs
sudo journalctl -u rivet-bot -f
```

---

## Troubleshooting

### Bot not responding

```bash
# Check if service is running
sudo systemctl status rivet-bot

# If not running, check logs for errors
sudo journalctl -u rivet-bot -n 50

# Common issues:
# - Wrong bot token → Check .env file
# - Missing dependencies → Run: pip install -r requirements.txt
# - Import errors → Run: python test_imports.py
```

### Database connection errors

```bash
# Test database connection
python -c "
from rivet_pro.infra.database import get_db
db = get_db()
print('✅ Database connected')
"

# If fails, check:
# - DATABASE_URL in .env is correct
# - Neon database is accessible
# - Network connection works
```

### OCR not working

```bash
# Check API keys
python -c "
from rivet_pro.config.settings import settings
print(f'Groq: {settings.groq_api_key[:20]}...')
print(f'Google: {settings.google_api_key[:20]}...')
"

# Test OCR directly
python -c "
from rivet_pro.core.services import analyze_image
# Test with sample image
"
```

### High memory usage

```bash
# Check memory
free -h

# Restart bot to clear memory
sudo systemctl restart rivet-bot
```

---

## Success Criteria - Day 2 Complete

- ✅ Bot deployed to VPS (72.60.175.144)
- ✅ Systemd service running
- ✅ Bot responds 24/7
- ✅ OCR working on photos
- ✅ SME routing working on text
- ✅ Logs accessible via journalctl
- ✅ Can restart/update easily

**When all checkboxes are checked, Day 2 is complete!**

---

## Next Steps (Day 3)

**Goal:** Get 5 real users testing

1. **Share bot with users:**
   - Personal contacts (maintenance technicians)
   - LinkedIn outreach
   - Reddit posts (r/PLC, r/electricians)

2. **Outreach message:**
   ```
   I built a maintenance AI that identifies equipment from photos and finds manuals.

   Want to try it? Just send a photo of any nameplate to:
   https://t.me/RivetCMMSBot

   Free beta (10 lookups/month).

   Let me know what you think!
   ```

3. **Collect feedback:**
   - Did it identify correctly?
   - How fast was response?
   - What's missing?
   - Would they pay $29/month?

**Target:** 5 users send photos, 3+ say "this is useful"

---

## Quick Reference

| Task | Command |
|------|---------|
| Connect to VPS | `ssh root@72.60.175.144` |
| View logs | `sudo journalctl -u rivet-bot -f` |
| Restart bot | `sudo systemctl restart rivet-bot` |
| Check status | `sudo systemctl status rivet-bot` |
| Pull updates | `cd /opt/Rivet-PRO && git pull` |
| Update & restart | `git pull && sudo systemctl restart rivet-bot` |

---

**Ready to deploy! 🚀**
