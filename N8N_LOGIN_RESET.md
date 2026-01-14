# ✅ N8N LOGIN RESET - SETUP REQUIRED

**Date**: 2026-01-12
**Action**: Reset n8n user database to allow fresh setup
**Status**: Ready for initial owner setup

---

## What Happened

The n8n instance had an existing user (mike@cranesync.com) with an unknown password. I reset the user management to allow you to set it up fresh.

---

## Access n8n Now

**Via SSH Tunnel**: http://localhost:8080
(Keep your PowerShell terminal with SSH connection open)

---

## You'll See: Owner Setup Screen

n8n will now show an initial setup wizard. Fill in:

### Owner Account Setup
- **Email**: mike@cranesync.com (or any email you prefer)
- **First Name**: Michael (or your name)
- **Last Name**: Harper (or your name)
- **Password**: Choose a secure password

### After Setup
- Click through any onboarding/welcome screens
- You'll land on the n8n workflows page
- Proceed with workflow import

---

## Import Feature 1 Workflow

Once you're in:

1. **Click "Workflows"** (left sidebar)
2. **Click "Import from File"** (top right)
3. **Select file**:
   ```
   C:\Users\hharp\OneDrive\Desktop\Rivet-PRO-feature1\rivet-pro\n8n-workflows\rivet_photo_bot_feature1.json
   ```
4. **Click "Import"**

---

## Configure Credentials (After Import)

The workflow needs 3 credentials:

### 1. Telegram Bot API
- **Type**: Telegram
- **Name**: "Telegram Bot API" (or any name)
- **Access Token**: `7910254197:AAGeEqMI_rvJExOsZVrTLc_0fb26CQKqlHQ`

### 2. Anthropic API Key
- **Type**: HTTP Header Auth
- **Name**: "Anthropic API Key"
- **Header Name**: `x-api-key`
- **Header Value**: Get from your .env file (ANTHROPIC_API_KEY)

### 3. Neon PostgreSQL
- **Type**: Postgres
- **Name**: "neon-ralph" (or any name)
- **Connection Details**: From your .env DATABASE_URL:
  ```
  Host: ep-purple-hall-a8meyn0-pooler.us-east-1.aws.neon.tech
  Port: 5432
  Database: neondb
  User: neondb_owner
  Password: (from DATABASE_URL)
  SSL: Enable
  ```

---

## Activate Workflow

After configuring credentials:
1. Click **"Active"** toggle (top-right)
2. Should turn green
3. Workflow is now live!

---

## Test Feature 1

1. Open Telegram
2. Find bot: @RalphOrchestratorBot
3. Send a photo of equipment
4. Wait for response (< 10 seconds)

Expected response:
```
📸 Equipment logged!

I think this is **[Manufacturer] [Model]**.

🔍 I'm looking for your manual now...

📋 Equipment: `EQ-2026-000001`
📊 Confidence: 85%
```

---

## Important Notes

### Keep SSH Tunnel Open
- Don't close the PowerShell terminal
- If you close it, reconnect with: `ssh -L 8080:localhost:5678 root@72.60.175.144`
- Then access: http://localhost:8080

### Save Your Password
- You're creating a new owner account
- Save the password you choose
- This is your n8n admin account

### Existing Workflows Safe
- All existing workflows are still there
- Only the user account was reset
- Your data and configurations are intact

---

**Status**: Ready for setup - Go to http://localhost:8080 now!
