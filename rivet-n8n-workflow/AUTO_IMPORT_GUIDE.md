# 🚀 RIVET Pro n8n - Auto-Import Quick Start

**Complete automation package for importing RIVET Pro workflow to n8n**

---

## ⚡ Super Quick Start (3 Commands)

```powershell
# 1. Start n8n (if not running)
n8n start

# 2. Set API key (get from n8n Settings → API)
$env:N8N_API_KEY = "n8n_api_YOUR_KEY_HERE"

# 3. Import workflow
cd rivet-n8n-workflow
.\import_to_n8n.ps1
```

**Done!** Workflow imported to n8n. Open the URL shown in output.

---

## 📦 What's Included

### Auto-Import Scripts (3 Options)

| Script | Platform | Features | Best For |
|--------|----------|----------|----------|
| **`import_to_n8n.ps1`** | Windows PowerShell | ✅ One-click import<br>✅ Opens browser<br>✅ Color output | **Windows users** |
| **`import_to_n8n.sh`** | Linux/Mac/Bash | ✅ Cross-platform<br>✅ Color output<br>✅ Error handling | **Linux/Mac users** |
| **`n8n_auto_import.py`** | Python 3.7+ | ✅ Full automation<br>✅ Auto-creates credentials<br>✅ Updates workflow | **Advanced users** |

### Configuration Files

| File | Purpose |
|------|---------|
| `.env.n8n.template` | Template showing required API keys |
| `N8N_API_SETUP.md` | Complete API setup documentation |
| `AUTO_IMPORT_GUIDE.md` | This file - quick reference |

### Workflow Files (Original Package)

| File | Purpose |
|------|---------|
| `rivet_workflow.json` | The workflow to import |
| `README.md` | Full setup guide |
| `rivet_node_configs.md` | Node configuration details |
| `rivet_workflow_diagram.md` | Architecture flowchart |

---

## 🎯 Choose Your Method

### Method 1: PowerShell (Recommended for Windows)

```powershell
# Navigate to workflow directory
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\rivet-n8n-workflow

# Set n8n API key
$env:N8N_API_KEY = "n8n_api_YOUR_KEY_FROM_N8N_UI"

# Import
.\import_to_n8n.ps1

# Optional: Custom n8n URL
.\import_to_n8n.ps1 -N8nUrl "http://192.168.1.100:5678"
```

**Output:**
```
✅ Connected to n8n
📤 Importing workflow...
✅ Workflow imported successfully!
   ID: abc123
   URL: http://localhost:5678/workflow/abc123

📋 Next Steps:
   1. Configure credentials...
```

---

### Method 2: Bash (Linux/Mac/Git Bash)

```bash
# Navigate to workflow directory
cd ~/rivet-n8n-workflow

# Set n8n API key
export N8N_API_KEY="n8n_api_YOUR_KEY_FROM_N8N_UI"

# Make executable (first time only)
chmod +x import_to_n8n.sh

# Import
./import_to_n8n.sh

# Optional: Custom n8n URL and API key as arguments
./import_to_n8n.sh http://localhost:5678 n8n_api_YOUR_KEY
```

---

### Method 3: Python (Most Automated)

**Prerequisites:**
```bash
pip install requests python-dotenv
```

**Usage:**
```bash
# Navigate to workflow directory
cd rivet-n8n-workflow

# Make sure .env file exists with API keys
# (Copy from ../rivet_pro/.env or use .env.n8n.template)

# Import
python n8n_auto_import.py

# Or with custom settings
python n8n_auto_import.py \
  --n8n-url http://localhost:5678 \
  --api-key n8n_api_YOUR_KEY
```

**What Python script does differently:**
1. ✅ Reads API keys from `.env` automatically
2. ✅ Creates Telegram Bot credential
3. ✅ Creates Tavily API credential (if key exists)
4. ✅ Creates Atlas CMMS credential (if key exists)
5. ✅ Updates workflow nodes with credential IDs
6. ✅ Imports complete, ready-to-use workflow

---

## 📋 Prerequisites Checklist

Before running any import script:

### 1. n8n Running
```bash
# Check if n8n is running
curl http://localhost:5678/healthz

# If not running, start it
n8n start
```

### 2. n8n API Key
1. Open n8n: http://localhost:5678
2. Click profile icon → **Settings**
3. Navigate to **API** tab
4. Click **Generate API Key**
5. Copy key (format: `n8n_api_XXXXX...`)

### 3. API Keys in .env

**Already have from your .env:**
- ✅ `TELEGRAM_BOT_TOKEN` = `7855741814:AAFHIk0vPmG9ZHACISMl-izzDwdS0bk_nYo`
- ✅ `GOOGLE_API_KEY` = `AIzaSyBOEFzA3fWyS_s92h4Sd7ZaWIctiVXZjlA`

**Need to add:**
- ⚠️ `TAVILY_API_KEY` - Get from [tavily.com](https://tavily.com)
- ⚠️ `ATLAS_CMMS_API_KEY` - Get from Atlas admin panel
- ⚠️ `ATLAS_CMMS_URL` - Your CMMS URL (e.g., `https://rivet-cmms.com`)

**See:** `.env.n8n.template` for complete example

---

## 🔑 Getting Missing API Keys

### Tavily Search API

1. Visit: https://tavily.com
2. Sign up (free tier: 1000 searches/month)
3. Navigate to API Keys
4. Copy API key (format: `tvly-XXXXX...`)
5. Add to `.env`:
   ```bash
   TAVILY_API_KEY=tvly-YOUR_KEY_HERE
   ```

### Atlas CMMS API

1. Log into your Atlas CMMS admin panel
2. Navigate to **API** or **Settings** → **API Tokens**
3. Click **Generate New Token**
4. Copy token
5. Add to `.env`:
   ```bash
   ATLAS_CMMS_URL=https://rivet-cmms.com
   ATLAS_CMMS_API_KEY=YOUR_TOKEN_HERE
   ```

---

## ✅ After Import - Next Steps

### 1. Open Workflow in n8n

The import script will show you the URL:
```
http://localhost:5678/workflow/abc123
```

### 2. Configure Remaining Items

**A. Set Variables** (n8n UI → Settings → Variables)
- `GOOGLE_API_KEY` = `AIzaSyBOEFzA3fWyS_s92h4Sd7ZaWIctiVXZjlA`
- `ATLAS_CMMS_URL` = `https://rivet-cmms.com`

**B. Verify Credentials** (if using Python script)
- Telegram Bot - Should be auto-configured
- Tavily API - Should be auto-configured
- Atlas CMMS - Should be auto-configured

**C. Manual Credential Setup** (if using PowerShell/Bash)
1. Open each node with yellow warning icon
2. Click "Select Credential"
3. Click "+ Create New"
4. Enter details from `.env`
5. Save

### 3. Activate Workflow

1. Click **Active** toggle in top-right (turns green)
2. Workflow now listening for Telegram messages

### 4. Test

Send message to your Telegram bot:
- Text: "Hello" → Should request photo
- Photo: Equipment nameplate → Should extract data and find manual

---

## 🐛 Troubleshooting

### Error: "Cannot connect to n8n"

**Problem:** n8n not running

**Fix:**
```bash
# Start n8n
n8n start

# Check status
curl http://localhost:5678/healthz
```

---

### Error: "401 Unauthorized"

**Problem:** Invalid API key

**Fix:**
1. Go to n8n → Settings → API
2. Delete old API key
3. Generate new API key
4. Update `N8N_API_KEY` environment variable
5. Re-run import script

---

### Error: "Workflow already exists"

**Problem:** You already imported this workflow

**Options:**

**A. Delete old workflow:**
1. n8n → Workflows
2. Find "RIVET Pro - Photo to Manual"
3. Click ⋮ → Delete
4. Re-run import

**B. Rename in JSON:**
```bash
# Edit rivet_workflow.json, change:
"name": "RIVET Pro - Photo to Manual v2"
```

---

### Script hangs or times out

**Problem:** Network/firewall blocking n8n

**Fix:**
```bash
# Check if n8n is accessible
curl -v http://localhost:5678/api/v1/workflows \
  -H "X-N8N-API-KEY: your-key"

# If blocked, check firewall
# Windows: Windows Defender Firewall
# Linux: sudo ufw status
```

---

## 📊 Comparison: Manual vs Auto-Import

| Task | Manual (UI) | PowerShell/Bash | Python Script |
|------|-------------|-----------------|---------------|
| **Import workflow** | 5 clicks | 1 command | 1 command |
| **Create credentials** | 5 min per credential | Manual after import | **Automatic** |
| **Set variables** | Manual | Manual | Shows what to set |
| **Total time** | ~20 minutes | ~10 minutes | **~5 minutes** |
| **Error-prone** | Medium | Low | **Very Low** |

**Recommendation:**
- **Windows users:** Use PowerShell script, then configure manually
- **Advanced users:** Use Python script for full automation
- **Linux/Mac:** Use Bash script

---

## 🔒 Security Notes

### Protect Your API Keys

**Never commit .env to git:**
```bash
# Verify .gitignore includes
cat .gitignore | grep .env

# If not, add it
echo ".env*" >> .gitignore
```

**Use environment variables in production:**
```bash
# Don't hardcode keys in scripts
# Use environment variables instead
export N8N_API_KEY="your-key"
```

**Rotate keys regularly:**
- n8n API key: Every 90 days
- Third-party APIs: Follow provider recommendations

---

## 📚 Full Documentation

For complete details, see:

- **`N8N_API_SETUP.md`** - Complete n8n API documentation
- **`README.md`** - Full workflow setup guide
- **`rivet_node_configs.md`** - Node configuration details
- **`.env.n8n.template`** - Required environment variables

---

## 🎉 Success!

After import, you should see:

```
✅ Workflow: RIVET Pro - Photo to Manual
✅ Nodes: 20
✅ Status: Imported
✅ URL: http://localhost:5678/workflow/abc123
```

**Your RIVET Pro workflow is now in n8n and ready to use!**

---

**Questions?** See `N8N_API_SETUP.md` for troubleshooting.

**Generated:** 2026-01-05
**Version:** 1.0
