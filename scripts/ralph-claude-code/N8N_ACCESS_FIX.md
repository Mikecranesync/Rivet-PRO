# n8n Access Issue - Quick Fix

**Problem**: http://72.60.175.144:5678 is not accessible
**Root Cause**: n8n is running but not listening on port 5678
**Status**: Service is running but not binding to the port correctly

---

## 🚀 Quick Solution: Use SSH Tunnel

Instead of accessing n8n directly at http://72.60.175.144:5678, we'll create an SSH tunnel to access it through localhost.

### Option 1: SSH Tunnel (RECOMMENDED - Works Now!)

1. **Open Command Prompt or PowerShell**

2. **Create SSH tunnel**:
   ```bash
   ssh -L 5678:localhost:5678 root@72.60.175.144
   ```

3. **Keep that terminal open** (don't close it!)

4. **Open your browser** and go to:
   ```
   http://localhost:5678
   ```

5. **n8n should now load!** ✅

### How It Works

The SSH tunnel forwards port 5678 from the VPS to your local machine's port 5678, bypassing any network/firewall issues.

---

## Option 2: Fix n8n on VPS (Longer Fix)

If you want to fix n8n permanently:

### Step 1: Reinstall n8n Service

```bash
ssh root@72.60.175.144

# Stop current service
systemctl stop n8n

# Remove old service file
rm /etc/systemd/system/n8n.service

# Create new service file with better configuration
cat > /etc/systemd/system/n8n.service << 'EOF'
[Unit]
Description=n8n workflow automation
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root
ExecStart=/usr/bin/node /usr/bin/n8n start
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment="N8N_PORT=5678"
Environment="N8N_PROTOCOL=http"
Environment="N8N_HOST=0.0.0.0"
Environment="N8N_LISTEN_ADDRESS=0.0.0.0"
Environment="N8N_BASIC_AUTH_ACTIVE=false"
Environment="EXECUTIONS_DATA_SAVE_ON_SUCCESS=all"
Environment="EXECUTIONS_DATA_SAVE_ON_ERROR=all"
Environment="GENERIC_TIMEZONE=America/New_York"
Environment="N8N_SECURE_COOKIE=false"

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable and start n8n
systemctl enable n8n
systemctl start n8n

# Wait and test
sleep 10
curl http://localhost:5678

# If that works, test from outside
exit
```

Then test: `http://72.60.175.144:5678`

---

## Option 3: Run n8n via Docker (Most Reliable)

```bash
ssh root@72.60.175.144

# Stop systemd service
systemctl stop n8n
systemctl disable n8n

# Run n8n in Docker
docker run -d \
  --name n8n \
  --restart always \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n

# Check it's running
docker ps | grep n8n

# Test
curl http://localhost:5678
```

Then test: `http://72.60.175.144:5678`

---

## ✅ Immediate Action (Use This Now!)

**For RIVET-009, use Option 1 (SSH Tunnel):**

```bash
# In Command Prompt / PowerShell:
ssh -L 5678:localhost:5678 root@72.60.175.144
```

**Then open browser to**: `http://localhost:5678`

You can now:
1. Import Ralph workflow
2. Create Neon credential
3. Complete RIVET-009

**Keep the SSH terminal open while working in n8n!**

---

## Why This Happened

Possible causes:
1. n8n configuration file has different port
2. n8n is binding to 127.0.0.1 instead of 0.0.0.0
3. Environment variables not being read correctly
4. n8n process is stuck in initialization

The SSH tunnel bypasses all of these issues.

---

## After RIVET-009

Once you finish configuring n8n via the SSH tunnel, you can:
1. Leave it as-is (always use SSH tunnel)
2. Fix the VPS configuration using Option 2 or 3 above
3. Use nginx reverse proxy (more advanced)

**For now, just use the SSH tunnel - it works!**

---

**Next Steps**:
1. Open Command Prompt
2. Run: `ssh -L 5678:localhost:5678 root@72.60.175.144`
3. Open browser: `http://localhost:5678`
4. Follow RIVET-009-COMPLETE-GUIDE.md to import workflow
5. Done!
