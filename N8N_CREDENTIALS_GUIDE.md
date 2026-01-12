# Rivet-PRO n8n Credentials Quick Reference

**Generated:** 2026-01-06
**For:** n8n Workflow Setup
**n8n Instance:** http://localhost:5678

---

## ✅ Credentials You Already Have

### 1. Telegram Bot Token
```
Bot Token: 8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE
Status: ✅ Ready to use
Source: @BotFather on Telegram
```

**How to add in n8n:**
1. n8n → Credentials → "+ Create New Credential"
2. Search: "Telegram"
3. Select: "Telegram API"
4. Name: `Rivet CMMS Bot`
5. Access Token: `8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE`
6. Save

---

### 2. Google Gemini API (OCR)
```
API Key: AIzaSyBOEFzA3fWyS_s92h4Sd7ZaWIctiVXZjlA
Status: ✅ Ready to use
Purpose: Equipment nameplate OCR
```

**How to add in n8n:**
1. n8n → Settings → Variables → "+ Add Variable"
2. Key: `GOOGLE_API_KEY`
3. Value: `AIzaSyBOEFzA3fWyS_s92h4Sd7ZaWIctiVXZjlA`
4. Save

---

### 3. Atlas CMMS API
```
Base URL: http://localhost:8080/api
Admin Email: admin@example.com
Status: ⚠️ Need to generate API token
```

**How to generate API token:**
1. Start your Rivet Java backend: `docker-compose up rivet-java`
2. Register admin user or login:
   ```bash
   curl -X POST http://localhost:8080/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@example.com","password":"your_password"}'
   ```
3. Copy the JWT token from response
4. Use this as your ATLAS_CMMS_API_KEY

**How to add in n8n:**
1. n8n → Credentials → "+ Create New Credential"
2. Search: "HTTP Header Auth"
3. Name: `Atlas CMMS API`
4. Header Name: `Authorization`
5. Header Value: `Bearer YOUR_JWT_TOKEN_HERE`
6. Save

---

## ⏳ Credentials You Need to Get

### 4. Tavily Search API (Optional but Recommended)
```
Website: https://tavily.com
Status: ❌ Not configured
Free Tier: 1,000 searches/month
Purpose: Equipment manual search
```

**How to get:**
1. Go to https://tavily.com
2. Click "Sign Up" (free)
3. Verify email
4. Go to Dashboard → API Keys
5. Copy your API key (format: `tvly-XXXXX`)

**How to add in n8n:**
1. n8n → Credentials → "+ Create New Credential"
2. Search: "HTTP Header Auth"
3. Name: `Tavily Search API`
4. Header Name: `Authorization`
5. Header Value: `Bearer tvly-YOUR_KEY_HERE`
6. Save

---

### 5. n8n API Key (for automated import)
```
Instance: http://localhost:5678
Status: ❌ Need to generate
Purpose: Workflow import automation
```

**How to get:**
1. Open n8n: http://localhost:5678
2. Click your profile icon (top right)
3. Go to: **Settings**
4. Navigate to: **API** section
5. Click: **"Generate new API key"**
6. Copy key (format: `n8n_api_XXXXXXXXXXXXX`)
7. Save somewhere safe!

**How to use:**
```bash
# Add to environment
export N8N_API_KEY="n8n_api_YOUR_KEY_HERE"

# Or add to .env file
echo "N8N_API_KEY=n8n_api_YOUR_KEY_HERE" >> .env
```

---

## 📊 Complete Environment Variables

Add these to your `.env` file:

```bash
# ===== Already Configured =====
TELEGRAM_BOT_TOKEN=8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE
GOOGLE_API_KEY=AIzaSyBOEFzA3fWyS_s92h4Sd7ZaWIctiVXZjlA

# ===== Need to Add =====
# Get from https://tavily.com
TAVILY_API_KEY=tvly-XXXXXXXXXXXXXXXXXXXXX

# Get from n8n → Settings → API
N8N_API_KEY=n8n_api_XXXXXXXXXXXXXXXXXXXXX

# Get from Atlas CMMS login
ATLAS_CMMS_URL=http://localhost:8080/api
ATLAS_CMMS_API_KEY=YOUR_JWT_TOKEN_HERE

# ===== n8n Configuration =====
N8N_URL=http://localhost:5678
```

---

## 🔑 n8n Variables to Set

After importing workflow, set these in n8n UI:

**Settings → Variables → Add Variable:**

| Variable Name | Value | Source |
|---------------|-------|--------|
| `GOOGLE_API_KEY` | `AIzaSyBOEFzA3fWyS_s92h4Sd7ZaWIctiVXZjlA` | Already configured |
| `ATLAS_CMMS_URL` | `http://localhost:8080/api` | Your local Java backend |

---

## ✅ Setup Checklist

Before importing workflow:

- [ ] n8n running at http://localhost:5678
- [ ] Telegram bot token ready: `8161680636:...`
- [ ] Google API key ready: `AIzaSyBOEFzA3f...`
- [ ] Generate n8n API key (Settings → API)
- [ ] Sign up for Tavily API (optional): https://tavily.com
- [ ] Start Atlas CMMS backend: `docker-compose up rivet-java`
- [ ] Get Atlas CMMS JWT token (login via API)

After importing workflow:

- [ ] Add Telegram credential in n8n
- [ ] Add Atlas CMMS credential in n8n
- [ ] Add Tavily credential in n8n (optional)
- [ ] Set GOOGLE_API_KEY variable
- [ ] Set ATLAS_CMMS_URL variable
- [ ] Activate workflow
- [ ] Test with Telegram photo

---

## 🚀 Quick Test Commands

### Test Telegram Bot
```bash
curl https://api.telegram.org/bot8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE/getMe
```

### Test Atlas CMMS
```bash
# Health check
curl http://localhost:8080/api/health

# Login (get JWT token)
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'
```

### Test Google Gemini API
```bash
curl -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=AIzaSyBOEFzA3fWyS_s92h4Sd7ZaWIctiVXZjlA" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
```

### Test n8n
```bash
curl http://localhost:5678/healthz
```

---

## 🛠️ Troubleshooting

### Telegram Bot Not Responding
- Verify bot token with: `/getMe` endpoint
- Check bot is not already connected to another webhook
- Ensure n8n workflow is activated

### Google API Quota Exceeded
- Check usage: https://console.cloud.google.com/apis/dashboard
- Enable billing if on free tier
- Limit: 15 requests/minute on free tier

### Atlas CMMS 401 Unauthorized
- JWT tokens expire after 24 hours
- Re-login to get new token
- Update credential in n8n

### Tavily No Results
- Check API quota (1000/month free)
- Verify equipment manufacturer/model is common
- Try manual search to confirm manual exists online

---

## 📝 Next Steps

1. **Generate n8n API key** → http://localhost:5678 → Settings → API
2. **Get Tavily API key** → https://tavily.com (optional, 5 min signup)
3. **Run import script** → `python n8n_auto_import.py`
4. **Configure credentials** → Follow prompts
5. **Test workflow** → Send equipment photo to Telegram bot

---

**🎯 Your Setup Status**

| Component | Status |
|-----------|--------|
| n8n Instance | ✅ Running |
| Telegram Bot | ✅ Token ready |
| Google Gemini | ✅ API key ready |
| Atlas CMMS | ⏳ Backend running? |
| Tavily Search | ❌ Need signup |
| n8n API Key | ❌ Need to generate |

---

**Need help?** Re-read:
- `rivet-n8n-workflow/README.md` - Full setup guide
- `rivet-n8n-workflow/N8N_API_SETUP.md` - API automation guide
- `rivet-n8n-workflow/rivet_node_configs.md` - Node-by-node config

**Quick links:**
- n8n UI: http://localhost:5678
- Tavily Signup: https://tavily.com
- Google AI Studio: https://makersuite.google.com/app/apikey
- Atlas CMMS: http://localhost:8080/swagger-ui.html
