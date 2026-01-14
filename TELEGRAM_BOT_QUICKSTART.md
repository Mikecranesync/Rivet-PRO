# 🤖 Telegram Bot Testing - Quick Start

## Prerequisites Checklist

- ✅ Grashjs CMMS is running (http://localhost:8081)
- ✅ You have created an account in the CMMS web UI
- ✅ You have created at least one asset in CMMS
- ✅ Python dependencies installed (python-telegram-bot, requests)
- ⚠️ You need a Telegram Bot Token

---

## Step 1: Get Your Telegram Bot Token

If you don't have a bot yet:

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Follow the prompts:
   - Name: `Rivet-PRO CMMS Bot` (or any name you like)
   - Username: `rivetpro_cmms_bot` (must end with `_bot`)
4. Copy the token that BotFather gives you (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

---

## Step 2: Test API Connection (Optional but Recommended)

First, verify the CMMS API connection works:

### Option A: Interactive Test

```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
python test_cmms_connection.py
```

You'll be prompted for:
- Your CMMS email (from when you registered at http://localhost:3001)
- Your CMMS password

The script will:
- ✅ Login to CMMS
- ✅ Retrieve and display your assets
- ✅ Optionally create a test asset via API
- ✅ Optionally create a test work order

### Option B: Quick Python Test

```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
python
```

Then run:

```python
from integrations.grashjs_client import GrashjsClient

# Initialize client
cmms = GrashjsClient("http://localhost:8081")

# Login (use YOUR credentials)
cmms.login("your@email.com", "yourpassword")

# Get assets
result = cmms.get_assets()
assets = result.get('content', [])

# Print assets
for asset in assets:
    print(f"✓ {asset['name']} (ID: {asset['id']})")
```

---

## Step 3: Run the Telegram Bot

### Option A: Using the Setup Script (Recommended)

```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
setup_telegram_test.bat
```

This will:
1. Check if CMMS is running
2. Ask for your bot token
3. Ask for your CMMS credentials
4. Run the API test
5. Start the Telegram bot

### Option B: Manual Setup

Set environment variables:

```bash
# Set your Telegram bot token
set TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Set CMMS credentials
set CMMS_EMAIL=your@email.com
set CMMS_PASSWORD=yourpassword
```

Run the bot:

```bash
python test_telegram_bot.py
```

### Option C: Edit the Script Directly

Open `test_telegram_bot.py` and change these lines:

```python
# Line 18-20 - Update with your credentials
CMMS_EMAIL = "your@email.com"  # Change this
CMMS_PASSWORD = "yourpassword"  # Change this
```

Then run:

```bash
set TELEGRAM_BOT_TOKEN=your_token_here
python test_telegram_bot.py
```

---

## Step 4: Test in Telegram

Once the bot is running, you'll see:

```
✅ Logged into CMMS successfully
🤖 Starting Telegram bot...
✅ Bot is running!
📱 Open Telegram and send /start to your bot
```

### In Telegram:

1. Find your bot (search for the username you created)
2. Send `/start`

You should see a menu with buttons:
- 📦 View Assets
- 🔧 Work Orders
- ➕ Create WO
- ℹ️ Help

### Available Commands:

- `/start` - Show main menu
- `/assets` - List all assets from CMMS
- `/wo` - List open work orders
- `/createwo` - Create a test work order

---

## Testing Checklist

Once the bot is running, test these features:

### Test 1: View Assets
1. Send `/assets` or click "📦 View Assets"
2. You should see the asset you created in CMMS
3. Verify the details match (name, serial number, etc.)

### Test 2: Create Work Order
1. Send `/createwo` or click "➕ Create WO"
2. Bot should create a work order linked to your asset
3. Check the web UI to confirm: http://localhost:3001/app/work-orders

### Test 3: View Work Orders
1. Send `/wo` or click "🔧 Work Orders"
2. You should see the work order you just created

### Test 4: Verify in Web UI
1. Open http://localhost:3001
2. Go to "Work Orders"
3. You should see the work order created via Telegram!

---

## Troubleshooting

### Bot won't start

**Error: `TELEGRAM_BOT_TOKEN not set`**
- Solution: Set the environment variable:
  ```bash
  set TELEGRAM_BOT_TOKEN=your_token_here
  ```

**Error: `Failed to login to CMMS`**
- Check CMMS is running: `docker-compose ps`
- Verify credentials are correct
- Make sure you've created an account at http://localhost:3001

### Bot starts but doesn't respond

- Make sure you're messaging the correct bot
- Check the bot username matches what BotFather gave you
- Look at the console output for errors

### "No assets found"

- Create an asset in the web UI first: http://localhost:3001
- Go to Assets → + New Asset
- Fill in at least the name field

### API connection errors

- Check CMMS is running:
  ```bash
  curl http://localhost:8081
  ```
  Should return a 403 (that's good - means it's up)

- Check Docker containers:
  ```bash
  docker ps | findstr atlas
  ```
  You should see:
  - atlas-cmms-backend
  - atlas-cmms-frontend
  - atlas_db
  - atlas_minio

---

## What to Expect

When everything works correctly:

1. **Bot starts** → Logs into CMMS successfully
2. **You send `/start`** → Bot responds with menu
3. **You click "View Assets"** → Bot retrieves and displays your asset
4. **You click "Create WO"** → Bot creates work order in CMMS
5. **Check web UI** → Work order appears in CMMS

This proves the integration is working end-to-end:
```
Telegram → Bot → Python Client → Grashjs API → Database
```

---

## Next Steps After Testing

Once you confirm the integration works:

1. **Integrate into your main bot** (`rivet_pro/bot/`)
   - Copy the patterns from `test_telegram_bot.py`
   - Add CMMS commands to your existing bot

2. **Customize the commands**
   - Add more specific work order types
   - Implement asset search
   - Add PM schedule creation
   - Create custom workflows

3. **Deploy to production**
   - Move to your production server
   - Update CMMS_URL to production URL
   - Set environment variables securely

---

## Example: Full Test Run

```bash
# Terminal
C:\> cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO

C:\...\Rivet-PRO> set TELEGRAM_BOT_TOKEN=1234567890:ABC...
C:\...\Rivet-PRO> set CMMS_EMAIL=admin@rivetpro.com
C:\...\Rivet-PRO> set CMMS_PASSWORD=mypassword

C:\...\Rivet-PRO> python test_telegram_bot.py

🔐 Logging into CMMS...
   URL: http://localhost:8081
   Email: admin@rivetpro.com
✅ Logged into CMMS successfully

🤖 Starting Telegram bot...
✅ Bot is running!
📱 Open Telegram and send /start to your bot

⏸  Press Ctrl+C to stop
```

```
# In Telegram
You: /start

Bot: 👋 Welcome to Rivet-PRO CMMS!
     🌐 CMMS: http://localhost:8081
     📧 User: admin@rivetpro.com
     🔐 Status: ✅ Connected

     [📦 View Assets] [🔧 Work Orders]
     [➕ Create WO]   [ℹ️ Help]

You: /assets

Bot: 📦 Assets in CMMS (1 total)

     Motor #101
     ├ ID: 1
     ├ S/N: MTR-001
     ├ Model: XYZ-500
     ├ Mfr: ACME Corp
     └ Status: OPERATIONAL

You: /createwo

Bot: ✅ Work Order Created!

     ID: #1
     Title: Test WO from Telegram Bot
     Asset: Motor #101
     Priority: MEDIUM
     Status: OPEN

     View it at:
     http://localhost:3001/app/work-orders/1
```

---

## Success! 🎉

If you got this far, your Telegram bot is successfully integrated with Grashjs CMMS!

You can now:
- ✅ View assets from Telegram
- ✅ Create work orders from Telegram
- ✅ List work orders from Telegram
- ✅ All data syncs with the web UI

**The integration is complete and working!**
