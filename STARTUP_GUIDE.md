# Rivet-PRO One-Click Startup Guide

## Quick Start (10 seconds)

**Just double-click this file on your Desktop:**

```
START_RIVET.bat
```

That's it! The script will:
1. ✓ Check Docker is running
2. ✓ Start CMMS containers if needed
3. ✓ Wait for CMMS to be healthy
4. ✓ Test login with your account (mike@cranesync.com)
5. ✓ Start the Telegram bot
6. ✓ Show you the success message

**Then open Telegram and send `/start` to your bot!**

---

## What Happens When You Click START_RIVET.bat?

### Step 1: Docker Check
```
[1/5] Checking Docker...
[OK] Docker is running
```

The script verifies Docker Desktop is running. If not, you'll see an error asking you to start Docker first.

### Step 2: CMMS Container Check
```
[2/5] Checking CMMS containers...
[INFO] CMMS containers not running, starting them...
[OK] CMMS containers started
```

The script checks if your Grashjs CMMS containers are running. If not, it automatically starts them with:
```bash
docker-compose up -d
```

### Step 3: Health Check Wait
```
[3/5] Waiting for CMMS API to be ready...
Attempt 1/30: CMMS API not ready yet (HTTP 000), waiting 5 seconds...
Attempt 2/30: CMMS API not ready yet (HTTP 000), waiting 5 seconds...
...
[OK] CMMS API is responding (HTTP 403)
```

The script polls the CMMS API every 5 seconds (max 30 attempts = 2.5 minutes) until it responds.

Success = HTTP 200 or 403 (both mean the API is alive)

### Step 4: Login Test
```
[4/5] Testing CMMS login for mike@cranesync.com...
[OK] Login successful
```

The script tests your credentials with the CMMS to make sure everything is configured correctly.

### Step 5: Bot Start
```
[5/5] Starting Telegram bot...

================================================
  BOT IS STARTING
================================================

CMMS: http://localhost:8081
User: mike@cranesync.com
Bot Token: 7855741814:AAFHIk0vP...

Open Telegram and send /start to your bot!

Press Ctrl+C to stop the bot
================================================
```

The bot starts and begins polling Telegram for messages. Leave this window open!

---

## Troubleshooting

### "Docker is not running!"

**Problem:** Docker Desktop is not started.

**Solution:**
1. Start Docker Desktop from Start Menu
2. Wait for Docker to fully start (icon in system tray)
3. Run START_RIVET.bat again

### "Failed to start CMMS containers!"

**Problem:** docker-compose failed to start containers.

**Solution:**
1. Open PowerShell and run:
   ```bash
   cd C:\Users\hharp\OneDrive\Desktop\grashjs-cmms
   docker-compose down
   docker-compose up -d
   ```
2. Check for errors in the output
3. If you see port conflicts, stop other services using ports 8081, 3001, 5435, 9000

### "CMMS API did not respond after 2.5 minutes"

**Problem:** CMMS backend is not starting properly.

**Solution:**
1. Check container logs:
   ```bash
   cd C:\Users\hharp\OneDrive\Desktop\grashjs-cmms
   docker-compose logs atlas-cmms-backend
   ```
2. Look for errors in the logs
3. Common issues:
   - Database connection failed → Check PostgreSQL container is running
   - MinIO connection failed → Check MinIO container is running
   - Port conflict → Stop other services using port 8081

### "Could not login to CMMS"

**Problem:** Credentials are incorrect or account doesn't exist.

**Solution:**
1. Go to http://localhost:3001
2. Try logging in manually with mike@cranesync.com / Bo1ws2er@12
3. If login fails, check if:
   - Account email is correct
   - Password is correct
   - Account was created successfully

### Bot starts but doesn't respond in Telegram

**Problem:** Bot credentials are wrong or bot is not registered.

**Solution:**
1. Check bot token in .env file
2. Test bot token with:
   ```bash
   curl https://api.telegram.org/bot7855741814:AAFHIk0vPmG9ZHACISMl-izzDwdS0bk_nYo/getMe
   ```
3. Should return bot information
4. Make sure you're messaging the correct bot in Telegram

---

## Manual Startup (If Automatic Fails)

### 1. Start CMMS Manually
```bash
cd C:\Users\hharp\OneDrive\Desktop\grashjs-cmms
docker-compose up -d
```

Wait 30 seconds, then check:
```bash
curl http://localhost:8081/actuator/health
```

Should see: `{"status":"UP"}`

### 2. Check CMMS Login
```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
python -c "import sys; sys.path.insert(0, 'integrations'); from grashjs_client import GrashjsClient; c = GrashjsClient('http://localhost:8081'); c.login('mike@cranesync.com', 'Bo1ws2er@12'); print('Login OK')"
```

### 3. Start Bot Manually
```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
python bot_launcher.py
```

---

## Using n8n Orchestration

### What is n8n Orchestration?

n8n is a workflow automation tool. The Rivet-PRO includes an n8n workflow that can orchestrate the entire startup process with:
- Automatic Docker checks
- CMMS container management
- Health monitoring
- Login validation
- Bot startup
- Telegram notifications on success/failure

### Setup n8n Workflow

1. **Start n8n** (if not already running):
   ```bash
   npx n8n
   ```
   Or if installed globally:
   ```bash
   n8n start
   ```

2. **Import the workflow:**
   ```bash
   cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
   python setup_n8n_orchestrator.py
   ```

   This will:
   - Check n8n is running
   - Get or prompt for N8N_API_KEY
   - Import the workflow
   - Activate it
   - Show you the workflow URL

3. **Access the workflow:**
   - Open http://localhost:5678
   - Find "Rivet-PRO Startup Orchestrator"
   - Click to open it

### Using the n8n Workflow

1. Open http://localhost:5678
2. Go to "Rivet-PRO Startup Orchestrator"
3. Click "Execute Workflow" button
4. Watch the nodes turn green as each step completes
5. You'll receive a Telegram notification when done!

### n8n Workflow Stages

**Stage 1: Initialization**
- Sets up variables (CMMS URL, paths, credentials)
- Checks Docker is running

**Stage 2: Start CMMS**
- Checks if CMMS is already running
- Starts containers if needed
- Waits for health check to pass

**Stage 3: Validate Login**
- Tests login with mike@cranesync.com
- Gets user info from CMMS
- Fails if credentials are wrong

**Stage 4: Start Bot**
- Starts Telegram bot in background
- Waits 5 seconds for initialization

**Stage 5: Notify**
- Sends success message to Telegram
- Or sends error message if anything failed

---

## Port Reference

| Service | Port | URL |
|---------|------|-----|
| CMMS API | 8081 | http://localhost:8081 |
| CMMS Frontend | 3001 | http://localhost:3001 |
| PostgreSQL | 5435 | localhost:5435 |
| MinIO API | 9000 | http://localhost:9000 |
| MinIO Console | 9001 | http://localhost:9001 |
| n8n | 5678 | http://localhost:5678 |

---

## Credentials

### CMMS Access
- **Web UI:** http://localhost:3001
- **Email:** mike@cranesync.com
- **Password:** Bo1ws2er@12

### Telegram Bot
- **Token:** 7855741814:AAFHIk0vPmG9ZHACISMl-izzDwdS0bk_nYo
- **Your Chat ID:** 8445149012

### Database
- **Host:** localhost:5435
- **Database:** atlas
- **User:** rivet_admin
- **Password:** rivet_secure_password_2026

---

## Testing Checklist

After starting Rivet-PRO, verify everything works:

- [ ] Double-click START_RIVET.bat
- [ ] All 5 steps complete successfully
- [ ] Bot window shows "BOT IS STARTING"
- [ ] Open Telegram app
- [ ] Find your bot in chat list
- [ ] Send `/start` to bot
- [ ] Bot responds with welcome message and menu buttons
- [ ] Click "View Assets" → See your assets
- [ ] Click "Create WO" → Creates a work order
- [ ] Go to http://localhost:3001/app/work-orders
- [ ] Verify work order appears in web UI

**If all checks pass: ✅ Rivet-PRO is fully operational!**

---

## Stopping Rivet-PRO

### Stop the Bot
Press `Ctrl+C` in the bot window

### Stop CMMS Containers
```bash
cd C:\Users\hharp\OneDrive\Desktop\grashjs-cmms
docker-compose down
```

### Stop Everything (Including Docker)
```bash
cd C:\Users\hharp\OneDrive\Desktop\grashjs-cmms
docker-compose down
# Then stop Docker Desktop from system tray
```

---

## Next Steps

Once you have Rivet-PRO running locally, you can:

1. **Deploy to VPS** (72.60.175.144)
   - Run 24/7 without your PC
   - Accessible from anywhere
   - Automatic startup on server boot

2. **Add More Bot Commands**
   - Equipment search by photo OCR
   - Manual upload
   - Work order tracking
   - Custom reports

3. **Set Up Monitoring**
   - n8n workflow for hourly health checks
   - Automatic restart on failure
   - Alert notifications

4. **Backup Your Data**
   - PostgreSQL backup scripts
   - Asset export
   - Work order history

---

## Help & Support

**Check logs:**
```bash
cd C:\Users\hharp\OneDrive\Desktop\grashjs-cmms
docker-compose logs -f atlas-cmms-backend
```

**Restart CMMS:**
```bash
cd C:\Users\hharp\OneDrive\Desktop\grashjs-cmms
docker-compose restart
```

**Full reset:**
```bash
cd C:\Users\hharp\OneDrive\Desktop\grashjs-cmms
docker-compose down -v  # WARNING: Deletes all data!
docker-compose up -d
```

**Check bot logs:**
The bot window shows all logs in real-time. Look for errors there.

---

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for complete system architecture documentation.
