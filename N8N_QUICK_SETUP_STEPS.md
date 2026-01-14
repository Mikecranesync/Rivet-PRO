# Rivet-PRO n8n Quick Setup Steps

**Date:** 2026-01-06
**n8n Instance:** http://localhost:5678 (RUNNING ✅)

---

## 🚀 Quick Setup (15 Minutes)

### Step 1: Import Workflow (2 min)

1. **Open n8n:** http://localhost:5678
2. Click **"Workflows"** in left sidebar
3. Click **"+ Add workflow"** button (top right)
4. Click **"⋮" menu** (three dots, top right)
5. Select **"Import from File"**
6. Navigate to: `C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\rivet-n8n-workflow\`
7. Select: **`rivet_workflow_clean.json`**
8. Click **"Import"**

✅ You should now see ~20 nodes in the workflow canvas.

---

### Step 2: Configure Telegram Bot Credential (2 min)

1. In workflow canvas, click any **yellow warning** icon on Telegram nodes
2. Click **"Select Credential"** dropdown
3. Click **"+ Create New Credential"**
4. Credential Type: **"Telegram API"**
5. Name: `Rivet CMMS Bot`
6. Access Token: `8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE`
7. Click **"Save"**
8. The Telegram nodes will auto-select this credential

**Telegram nodes that need this credential:**
- "Telegram Photo Received" (trigger)
- "Send Manual Found"
- "Send No Manual Found"
- "Send Error Message"
- "Request Photo"

---

### Step 3: Set Google API Variable (1 min)

1. Click **Settings** (gear icon, bottom left)
2. Navigate to **"Variables"** section
3. Click **"+ Add Variable"**
4. Key: `GOOGLE_API_KEY`
5. Value: `AIzaSyBOEFzA3fWyS_s92h4Sd7ZaWIctiVXZjlA`
6. Click **"Save"**

---

### Step 4: Set Atlas CMMS URL Variable (1 min)

While in **Settings → Variables:**

1. Click **"+ Add Variable"** again
2. Key: `ATLAS_CMMS_URL`
3. Value: `http://localhost:8080/api`
4. Click **"Save"**

---

### Step 5: Start Atlas CMMS Backend (3 min)

Open a new terminal and start your Java backend:

```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
docker-compose up rivet-java
```

**Wait for:** `Started RivetApplication in X seconds`

Test it's running:
```bash
curl http://localhost:8080/api/health
```

Should return:
```json
{
  "status": "UP",
  "service": "Rivet CMMS API",
  "database": "UP"
}
```

---

### Step 6: Get Atlas CMMS JWT Token (2 min)

**Option A: Register new admin user**
```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"admin@example.com\",\"password\":\"admin\",\"name\":\"Admin User\"}"
```

**Option B: Login with existing admin**
```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"admin@example.com\",\"password\":\"admin\"}"
```

**Copy the JWT token** from the response (format: `eyJ...`)

---

### Step 7: Configure Atlas CMMS Credential (2 min)

Back in n8n workflow:

1. Find node: **"Search Atlas CMMS"** or **"Create Asset"**
2. Click the **yellow warning** icon
3. Click **"+ Create New Credential"**
4. Credential Type: **"HTTP Header Auth"**
5. Name: `Atlas CMMS API`
6. Header Name: `Authorization`
7. Header Value: `Bearer YOUR_JWT_TOKEN_HERE` (paste the JWT from Step 6)
8. Click **"Save"**

**Nodes that use this credential:**
- "Search Atlas CMMS"
- "Create Asset"
- "Update Asset"

---

### Step 8: Configure Tavily Search (Optional - 2 min)

**Get Tavily API Key:**
1. Go to https://tavily.com
2. Click "Sign Up" (free tier: 1000 searches/month)
3. Verify email
4. Go to Dashboard → API Keys
5. Copy your API key (format: `tvly-...`)

**You already have one in .env:**
```
TAVILY_API_KEY=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
```

**Add to n8n:**
1. Find node: **"Quick Manual Search"** or **"Deep Manual Search"**
2. Click **+ Create New Credential**
3. Credential Type: **"HTTP Header Auth"**
4. Name: `Tavily Search API`
5. Header Name: `Authorization`
6. Header Value: `Bearer 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`
7. Click **"Save"**

**Nodes that use this:**
- "Quick Manual Search"
- "Deep Manual Search"

---

### Step 9: Activate Workflow (1 min)

1. Click **"Save"** button (top right)
2. Toggle **"Active"** switch to ON (top right)
3. Workflow should turn green

✅ Workflow is now listening for Telegram messages!

---

### Step 10: Test the Workflow (3 min)

**Test 1: Text Message**
1. Open Telegram
2. Find your bot: Search `@YourBotUsername`
3. Send message: `Hello`

**Expected Response:**
```
📸 Please send a photo of the equipment nameplate...
```

**Test 2: Equipment Photo**
1. Send a photo of equipment nameplate (or any equipment photo)
2. Wait 10-15 seconds

**Expected Response:**
```
📋 Equipment Details

Manufacturer: [Detected from OCR]
Model: [Detected from OCR]
Serial: [Detected from OCR]

✅ Asset saved to CMMS
```

**If manual search enabled (Tavily configured):**
```
📥 Manual Found!
[Link to manual]
```

---

## ✅ Setup Complete Checklist

Before testing:

- [ ] Workflow imported in n8n
- [ ] Telegram credential configured (8161680636...)
- [ ] GOOGLE_API_KEY variable set
- [ ] ATLAS_CMMS_URL variable set (http://localhost:8080/api)
- [ ] Atlas CMMS backend running (docker-compose up rivet-java)
- [ ] JWT token obtained (login via API)
- [ ] Atlas CMMS credential configured (Bearer token)
- [ ] Tavily credential configured (optional)
- [ ] Workflow activated (green toggle)
- [ ] Test message sent to bot

---

## 🐛 Troubleshooting

### Workflow won't activate
**Error:** "Credentials required"

**Fix:**
- Check all nodes with yellow warning icons
- Ensure all credentials are assigned
- Click "Test Credentials" to verify they work

---

### Telegram bot not responding
**Error:** No response from bot

**Fix:**
1. Check workflow is Active (green toggle)
2. Go to Executions tab - see if messages are being received
3. Test bot token:
   ```bash
   curl https://api.telegram.org/bot8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE/getMe
   ```

---

### OCR returns error
**Error:** "Google API quota exceeded" or "Invalid API key"

**Fix:**
1. Check GOOGLE_API_KEY variable is set correctly
2. Test API key:
   ```bash
   curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=AIzaSyBOEFzA3fWyS_s92h4Sd7ZaWIctiVXZjlA" \
     -H "Content-Type: application/json" \
     -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
   ```

---

### CMMS API returns 401
**Error:** "Unauthorized"

**Fix:**
1. JWT tokens expire after 24 hours
2. Get new token:
   ```bash
   curl -X POST http://localhost:8080/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@example.com","password":"admin"}'
   ```
3. Update Atlas CMMS credential with new token

---

### CMMS API connection refused
**Error:** "ECONNREFUSED"

**Fix:**
1. Ensure Java backend is running:
   ```bash
   curl http://localhost:8080/api/health
   ```
2. If not running:
   ```bash
   cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
   docker-compose up rivet-java
   ```

---

## 📊 Workflow Performance

| Action | Expected Time |
|--------|--------------|
| Text message response | < 1 second |
| Photo OCR | 3-5 seconds |
| Quick manual search | 5-10 seconds |
| Deep manual search | 15-25 seconds |
| Total photo → manual | 10-30 seconds |

---

## 🎯 What This Workflow Does

```
User sends equipment photo via Telegram
            ↓
Gemini Vision OCR extracts:
  - Manufacturer
  - Model number
  - Serial number
            ↓
Check Atlas CMMS for existing asset
            ↓
If not found: Create new asset
            ↓
Search for equipment manual (Tavily)
            ↓
Send manual link + asset details to user
            ↓
Done!
```

---

## 📚 Additional Resources

- **Full Guide:** `rivet-n8n-workflow/README.md`
- **Credentials Reference:** `N8N_CREDENTIALS_GUIDE.md`
- **Node Configuration:** `rivet-n8n-workflow/rivet_node_configs.md`
- **Workflow Diagram:** `rivet-n8n-workflow/rivet_workflow_diagram.md`

---

## 🆘 Need Help?

1. Check workflow execution logs: n8n → Executions tab
2. View node output: Click node → "Show Execution Data"
3. Test individual nodes: Click node → "Test step"
4. Check Docker logs: `docker-compose logs rivet-java`

---

**Your API Keys Quick Reference:**

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE

# Google Gemini
GOOGLE_API_KEY=AIzaSyBOEFzA3fWyS_s92h4Sd7ZaWIctiVXZjlA

# Tavily Search
TAVILY_API_KEY=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

# Atlas CMMS
ATLAS_API_URL=http://localhost:8080/api
ATLAS_ADMIN_EMAIL=admin@example.com
ATLAS_ADMIN_PASSWORD=admin

# n8n
N8N_URL=http://localhost:5678
N8N_API_KEY=eyJhbGci... (already configured)
```

---

**Ready to go! 🎉**

Start at Step 1 and work through each step. The whole setup takes about 15 minutes.
