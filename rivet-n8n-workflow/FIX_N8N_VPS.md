# Fix n8n on VPS & Import Workflow

## Current Issue

n8n Docker container is crash-looping due to permissions:
```
Error: EACCES: permission denied, open '/home/node/.n8n/config'
```

## Quick Fix (Option 1: Restart with Proper Permissions)

```bash
# SSH to VPS
ssh root@72.60.175.144

# Stop and remove the broken container
docker stop n8n
docker rm n8n

# Create n8n data directory with proper permissions
mkdir -p /root/.n8n
chmod -R 777 /root/.n8n

# Run n8n with proper volume mapping
docker run -d \
  --name n8n \
  --restart unless-stopped \
  -p 5678:5678 \
  -e N8N_PORT=5678 \
  -e N8N_PROTOCOL=http \
  -e N8N_HOST=0.0.0.0 \
  -e WEBHOOK_URL=http://72.60.175.144:5678/ \
  -e N8N_BASIC_AUTH_ACTIVE=false \
  -e GENERIC_TIMEZONE=America/New_York \
  -v /root/.n8n:/home/node/.n8n \
  n8nio/n8n

# Wait for startup (30 seconds)
sleep 30

# Verify it's running
docker logs n8n | tail -20
curl -s http://localhost:5678/ | head -5
```

## Alternative Fix (Option 2: Use Existing Setup Script)

```bash
ssh root@72.60.175.144

# Stop Docker container
docker stop n8n && docker rm n8n

# Install n8n via npm instead (more stable for production)
npm install -g n8n

# Run the setup script from the repo
cd /opt/Rivet-PRO/rivet-n8n-workflow
bash setup_n8n_vps.sh

# This will:
# - Create systemd service
# - Start n8n on port 5678
# - Configure auto-restart
```

## Access n8n

Once fixed, access n8n at:
- **Direct IP:** http://72.60.175.144:5678
- **Subdomain (if DNS configured):** http://n8n.maintpc.com

## Initial Setup (First Time)

1. Open http://72.60.175.144:5678
2. Create owner account (username, email, password)
3. Skip setup wizard (we'll import the workflow)

## Generate API Key

1. Click your profile icon (top-right)
2. Go to **Settings**
3. Click **API** in left sidebar
4. Click **Generate API Key**
5. Copy the key (format: `n8n_api_XXXXXXXX...`)

## Import the Workflow

### Option A: Using Auto-Import Script (Recommended)

```bash
# From your local machine

# 1. Set environment variables
export N8N_URL="http://72.60.175.144:5678"
export N8N_API_KEY="n8n_api_YOUR_KEY_HERE"  # from previous step

# 2. Run import script
cd rivet-n8n-workflow
python n8n_auto_import.py

# This will:
# - Create all credentials (Telegram, Tavily, Atlas CMMS)
# - Import workflow with nodes configured
# - Display what variables to set manually
```

### Option B: Manual Import via Web UI

1. Open http://72.60.175.144:5678
2. Click **Workflows** (left sidebar)
3. Click **Import from File**
4. Select `rivet_workflow.json`
5. Click **Import**
6. Configure credentials manually (see README.md)

## Configure Credentials & Variables

After import, you need to set up:

### Credentials (via n8n UI)

**Telegram Bot:**
- Credential type: Telegram API
- Access Token: `7855741814:AAFHIk0vPmG9ZHACISMl-izzDwdS0bk_nYo`

**Google Gemini:**
- Set as variable (see below), not credential

**Tavily Search:**
- Credential type: HTTP Header Auth
- Header: `Authorization`
- Value: `Bearer tvly-YOUR_KEY` (get from tavily.com)

**Atlas CMMS:**
- Credential type: HTTP Header Auth
- Header: `Authorization`
- Value: `Bearer YOUR_ATLAS_TOKEN`

### Variables (Settings → Variables)

| Variable | Value |
|----------|-------|
| `GOOGLE_API_KEY` | `AIzaSyBOEFzA3fWyS_s92h4Sd7ZaWIctiVXZjlA` |
| `ATLAS_CMMS_URL` | Your CMMS URL (e.g., `https://rivet-cmms.com`) |

## Test the Workflow

1. **Activate:** Toggle the workflow to "Active" (top-right)
2. **Send Message:** Open Telegram and message your bot
3. **Send Photo:** Send an equipment nameplate photo
4. **Verify:** Should respond with manual link within 10-15 seconds

## Troubleshooting

### n8n Still Not Starting

Check Docker logs:
```bash
ssh root@72.60.175.144 "docker logs n8n"
```

### Can't Access Web UI

Check if port is open:
```bash
# From local machine
curl http://72.60.175.144:5678/
```

If timeout, check firewall:
```bash
ssh root@72.60.175.144
ufw status
ufw allow 5678/tcp
```

### API Import Fails

Test API manually:
```bash
curl -H "X-N8N-API-KEY: your-key" http://72.60.175.144:5678/api/v1/workflows
```

Should return JSON array of workflows.

## Running n8n Locally (for Development)

If you want to test the workflow locally before deploying to VPS:

```bash
# Install n8n locally
npm install -g n8n

# Start n8n
n8n start

# Access at: http://localhost:5678

# Import workflow via UI or script
cd rivet-n8n-workflow
python n8n_auto_import.py --n8n-url http://localhost:5678
```

## Production Checklist

- [ ] n8n running and accessible at http://72.60.175.144:5678
- [ ] Owner account created
- [ ] API key generated
- [ ] Workflow imported (20 nodes visible)
- [ ] All 4 credentials configured
- [ ] All 2 variables set
- [ ] Workflow activated
- [ ] Test message sent to Telegram bot
- [ ] Test photo processed successfully
- [ ] Equipment saved to CMMS verified

## Next Steps

1. Fix the Docker permission issue using Option 1 or 2 above
2. Generate n8n API key
3. Import workflow using Python script
4. Configure credentials
5. Test end-to-end with Telegram bot

---

**VPS Details:**
- IP: 72.60.175.144
- n8n Port: 5678
- n8n URL: http://72.60.175.144:5678
- Container: Docker (n8nio/n8n:latest)
- Reverse Proxy: Caddy (already configured)
