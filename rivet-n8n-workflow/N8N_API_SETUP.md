# n8n API Auto-Import Setup Guide

Complete guide for automatically importing the RIVET Pro workflow to n8n using the API.

---

## 📋 Quick Start (3 Steps)

### 1. Start n8n and Get API Key

```bash
# Start n8n (if not running)
n8n start

# Or run in background
n8n start &

# n8n will be available at: http://localhost:5678
```

**Get your API key:**
1. Open n8n in browser: http://localhost:5678
2. Click your profile → **Settings**
3. Navigate to **API** section
4. Click **Generate API Key**
5. Copy the key (format: `n8n_api_XXXXX...`)

### 2. Set Environment Variable

**Windows (PowerShell):**
```powershell
$env:N8N_API_KEY = "n8n_api_YOUR_KEY_HERE"
```

**Linux/Mac (Bash):**
```bash
export N8N_API_KEY="n8n_api_YOUR_KEY_HERE"
```

**Or add to `.env` file:**
```bash
echo "N8N_API_KEY=n8n_api_YOUR_KEY_HERE" >> rivet_pro/.env
```

### 3. Run Import Script

**Option A: PowerShell (Windows)**
```powershell
cd rivet-n8n-workflow
.\import_to_n8n.ps1
```

**Option B: Bash (Linux/Mac/Git Bash)**
```bash
cd rivet-n8n-workflow
chmod +x import_to_n8n.sh
./import_to_n8n.sh
```

**Option C: Python (Advanced)**
```bash
cd rivet-n8n-workflow
pip install requests python-dotenv
python n8n_auto_import.py
```

---

## 🔧 Detailed Setup

### Prerequisites

- [ ] n8n installed and running
- [ ] n8n API key generated
- [ ] `.env` file with API keys (Telegram, Google, Tavily, CMMS)

### API Key Configuration

#### Where to Get Each API Key

| Service | Where to Get | Free Tier | Format |
|---------|--------------|-----------|--------|
| **n8n API** | n8n → Settings → API | Unlimited (self-hosted) | `n8n_api_...` |
| **Telegram Bot** | @BotFather on Telegram | Unlimited | `1234567890:ABC...` |
| **Google Gemini** | [Google AI Studio](https://makersuite.google.com/app/apikey) | 15 req/min | `AIzaSy...` |
| **Tavily Search** | [tavily.com](https://tavily.com) → API Keys | 1000/month | `tvly-...` |
| **Atlas CMMS** | Your CMMS admin panel | Varies | Custom token |

#### Complete .env Configuration

Copy `.env.n8n.template` to `rivet_pro/.env` and fill in:

```bash
# Core API Keys (ALREADY HAVE)
TELEGRAM_BOT_TOKEN=7855741814:AAFHIk0vPmG9ZHACISMl-izzDwdS0bk_nYo
GOOGLE_API_KEY=AIzaSyBOEFzA3fWyS_s92h4Sd7ZaWIctiVXZjlA

# Need to Add
TAVILY_API_KEY=tvly-XXXXXXXX              # Get from tavily.com
ATLAS_CMMS_URL=https://rivet-cmms.com      # Your CMMS URL
ATLAS_CMMS_API_KEY=YOUR_TOKEN              # CMMS API token

# n8n Configuration
N8N_URL=http://localhost:5678
N8N_API_KEY=n8n_api_XXXXXXXX               # From n8n Settings → API
```

---

## 📜 Import Scripts Explained

### PowerShell Script: `import_to_n8n.ps1`

**Features:**
- ✅ Tests n8n connection
- ✅ Validates API key
- ✅ Imports workflow JSON
- ✅ Returns workflow ID and URL
- ✅ Optionally opens browser

**Usage:**
```powershell
# Basic (uses env vars)
.\import_to_n8n.ps1

# Custom n8n URL
.\import_to_n8n.ps1 -N8nUrl "http://192.168.1.100:5678"

# Custom API key
.\import_to_n8n.ps1 -ApiKey "n8n_api_YOUR_KEY"

# Both custom
.\import_to_n8n.ps1 -N8nUrl "http://localhost:5678" -ApiKey "n8n_api_YOUR_KEY"
```

### Bash Script: `import_to_n8n.sh`

**Features:**
- ✅ Same as PowerShell version
- ✅ Color-coded output
- ✅ Error handling

**Usage:**
```bash
# Basic (uses env vars)
./import_to_n8n.sh

# Custom n8n URL
./import_to_n8n.sh http://192.168.1.100:5678

# With API key
./import_to_n8n.sh http://localhost:5678 n8n_api_YOUR_KEY
```

### Python Script: `n8n_auto_import.py`

**Features:**
- ✅ Full credential setup automation
- ✅ Reads .env file
- ✅ Creates credentials via API
- ✅ Updates workflow with credential IDs
- ✅ Most automated option

**Usage:**
```bash
# Install dependencies
pip install requests python-dotenv

# Run with env vars
python n8n_auto_import.py

# Run with arguments
python n8n_auto_import.py --n8n-url http://localhost:5678 --api-key n8n_api_YOUR_KEY
```

**What it does:**
1. Loads API keys from `.env`
2. Creates Telegram Bot credential
3. Creates Tavily API credential
4. Creates Atlas CMMS credential
5. Updates workflow nodes with credential IDs
6. Imports complete workflow
7. Displays variables to set manually

---

## 🔌 n8n API Reference

### Authentication

All n8n API requests require authentication via API key:

```bash
curl -H "X-N8N-API-KEY: your-api-key" http://localhost:5678/api/v1/workflows
```

### Endpoints Used

#### 1. List Workflows
```http
GET /api/v1/workflows
X-N8N-API-KEY: your-key
```

**Response:**
```json
[
  {
    "id": "1",
    "name": "My Workflow",
    "active": false,
    "nodes": [...],
    "connections": {...}
  }
]
```

#### 2. Import/Create Workflow
```http
POST /api/v1/workflows
X-N8N-API-KEY: your-key
Content-Type: application/json

{
  "name": "RIVET Pro - Photo to Manual",
  "nodes": [...],
  "connections": {...}
}
```

**Response:**
```json
{
  "id": "abc123",
  "name": "RIVET Pro - Photo to Manual",
  "active": false,
  "createdAt": "2026-01-05T12:00:00.000Z",
  "updatedAt": "2026-01-05T12:00:00.000Z"
}
```

#### 3. Create Credential
```http
POST /api/v1/credentials
X-N8N-API-KEY: your-key
Content-Type: application/json

{
  "name": "Telegram Bot - RIVET",
  "type": "telegramApi",
  "data": {
    "accessToken": "1234567890:ABC..."
  }
}
```

**Response:**
```json
{
  "id": "cred123",
  "name": "Telegram Bot - RIVET",
  "type": "telegramApi",
  "createdAt": "2026-01-05T12:00:00.000Z"
}
```

#### 4. Get Workflow by ID
```http
GET /api/v1/workflows/{id}
X-N8N-API-KEY: your-key
```

#### 5. Update Workflow
```http
PATCH /api/v1/workflows/{id}
X-N8N-API-KEY: your-key
Content-Type: application/json

{
  "active": true
}
```

#### 6. Activate/Deactivate Workflow
```http
PATCH /api/v1/workflows/{id}
X-N8N-API-KEY: your-key

{
  "active": true  // or false
}
```

---

## 🛠️ Manual Setup (If Scripts Fail)

### Step-by-Step API Import

**1. Test Connection**
```bash
curl -H "X-N8N-API-KEY: your-key" http://localhost:5678/api/v1/workflows
```

**2. Import Workflow**
```bash
curl -X POST \
  -H "X-N8N-API-KEY: your-key" \
  -H "Content-Type: application/json" \
  -d @rivet_workflow.json \
  http://localhost:5678/api/v1/workflows
```

**3. Get Workflow ID from Response**
```json
{
  "id": "abc123",  // <-- This is your workflow ID
  "name": "RIVET Pro - Photo to Manual"
}
```

**4. Open in Browser**
```
http://localhost:5678/workflow/abc123
```

**5. Configure Manually**
- Add credentials
- Set variables
- Activate workflow

---

## 🔒 Security Best Practices

### Protect Your API Keys

**Don't commit .env to git:**
```bash
# Add to .gitignore
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore
echo ".env.n8n" >> .gitignore
```

**Use environment variables in production:**
```bash
# Instead of .env file
export N8N_API_KEY="your-key"
export TAVILY_API_KEY="your-key"
```

**Rotate keys periodically:**
- n8n API key: Regenerate every 90 days
- Telegram bot token: Only if compromised
- Third-party APIs: Follow provider guidelines

---

## 🐛 Troubleshooting

### Error: "Connection refused"

**Problem:** n8n not running

**Solution:**
```bash
# Start n8n
n8n start

# Check if running
curl http://localhost:5678/healthz
```

---

### Error: "401 Unauthorized"

**Problem:** Invalid or missing API key

**Solution:**
1. Regenerate API key in n8n UI
2. Update `N8N_API_KEY` environment variable
3. Retry import

---

### Error: "Workflow already exists"

**Problem:** Workflow with same name exists

**Solution:**
```bash
# Option 1: Delete old workflow via UI

# Option 2: Update existing workflow
curl -X PATCH \
  -H "X-N8N-API-KEY: your-key" \
  -H "Content-Type: application/json" \
  -d @rivet_workflow.json \
  http://localhost:5678/api/v1/workflows/{old-workflow-id}
```

---

### Error: "Credential not found"

**Problem:** Workflow references non-existent credential

**Solution:**
1. Use Python script (auto-creates credentials)
2. Or manually create credentials in n8n UI first
3. Then import workflow

---

### Python Script Error: "Module not found"

**Problem:** Missing dependencies

**Solution:**
```bash
pip install requests python-dotenv
```

---

## 📊 Workflow Variables Setup

After import, set these in n8n UI:

**Settings → Variables → Add Variable**

| Variable | Value (from .env) | Example |
|----------|-------------------|---------|
| `GOOGLE_API_KEY` | Your Gemini API key | `AIzaSyBOEFzA3f...` |
| `ATLAS_CMMS_URL` | Your CMMS base URL | `https://rivet-cmms.com` |

**Screenshot location in n8n:**
```
n8n UI
└── Settings (⚙️)
    └── Variables
        └── + Add Variable
            ├── Key: GOOGLE_API_KEY
            └── Value: AIzaSy...
```

---

## ✅ Post-Import Checklist

After running import script:

- [ ] Workflow appears in n8n workflows list
- [ ] Open workflow in browser
- [ ] Check all nodes loaded (should be 20 nodes)
- [ ] Configure credentials:
  - [ ] Telegram Bot (4 nodes)
  - [ ] Tavily API (2 nodes)
  - [ ] Atlas CMMS (3 nodes)
- [ ] Set variables:
  - [ ] GOOGLE_API_KEY
  - [ ] ATLAS_CMMS_URL
- [ ] Activate workflow (toggle switch)
- [ ] Test with Telegram:
  - [ ] Send text message → Should request photo
  - [ ] Send photo → Should process and respond

---

## 🚀 Advanced: Deploy to VPS

### Install n8n on VPS (72.60.175.144)

```bash
# SSH to VPS
ssh root@72.60.175.144

# Install n8n
npm install -g n8n

# Create systemd service
sudo tee /etc/systemd/system/n8n.service <<EOF
[Unit]
Description=n8n workflow automation
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root
ExecStart=/usr/bin/n8n start
Restart=always
Environment="N8N_PORT=5678"
Environment="N8N_PROTOCOL=http"
Environment="N8N_HOST=72.60.175.144"

[Install]
WantedBy=multi-user.target
EOF

# Start n8n
sudo systemctl daemon-reload
sudo systemctl enable n8n
sudo systemctl start n8n

# Check status
sudo systemctl status n8n
```

### Import to VPS n8n

```bash
# From local machine
./import_to_n8n.sh http://72.60.175.144:5678 your-api-key
```

---

## 📚 Additional Resources

- **n8n API Docs:** https://docs.n8n.io/api/
- **n8n Credentials:** https://docs.n8n.io/credentials/
- **n8n Environment Variables:** https://docs.n8n.io/hosting/configuration/environment-variables/
- **Workflow JSON Format:** https://docs.n8n.io/workflows/

---

**Generated:** 2026-01-05
**Version:** 1.0
**For:** RIVET Pro CMMS n8n Integration
