# Quick Start - Your Manual Tasks

**Ralph is running in background. You do these 2 tasks while Ralph works.**

---

## Get Your Credentials First

```bash
# Get Gemini API Key
type C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\.env | findstr GEMINI_API_KEY

# Get Neon Database URL
type C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\.env | findstr NEON_DATABASE_URL
```

**Copy these values - you'll need them!**

---

## Task 1: RIVET-007 (10 minutes)

### What: Verify Gemini credential in n8n Photo Bot v2

1. Open browser → `http://72.60.175.144:5678`
2. Sign into n8n
3. Open "Photo Bot v2" workflow
4. Click "Gemini Vision" node
5. Check credential dropdown
   - ✅ If green checkmark → you're done!
   - ❌ If red warning → create new credential:
     - Click "+ Create New Credential"
     - Name: "Gemini Production"
     - Paste your GEMINI_API_KEY from above
     - Click "Create"
6. Click "Execute Workflow" button to test
7. Verify no errors

**Done? ✅ Move to Task 2**

---

## Task 2: RIVET-009 (15 minutes)

### What: Wire database credentials to Ralph workflow

1. Still in n8n (from Task 1)
2. Open "Ralph Main Loop" workflow
3. Create Neon credential (one time):
   - Click any purple Postgres node
   - Credential dropdown → "+ Create New Credential"
   - Name: "Neon PostgreSQL - Ralph"
   - Parse your NEON_DATABASE_URL:
     ```
     postgresql://USER:PASS@HOST/DB?ssl=...

     Host: [the part after @ and before /]
     Port: 5432
     Database: [the part after / and before ?]
     User: [before the : after //]
     Password: [after : and before @]
     SSL: Toggle ON
     ```
   - Click "Create"
4. Apply to all 7 Postgres nodes:
   - Click each Postgres node (find all 7)
   - Select "Neon PostgreSQL - Ralph" from dropdown
   - See green checkmark on each
5. Click "Save" (top right)
6. Click "Execute Workflow" to test
7. Verify no database errors

**Done? ✅ Both tasks complete!**

---

## Check Ralph's Progress

```bash
# See what Ralph is doing
type C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\scripts\ralph-claude-code\status.json
```

Look for:
- `"status": "running"` - Ralph is still working
- `"status": "completed"` - Ralph is done!

---

## When Ralph Finishes

You'll see new files:
- `tests/test_bot_handlers.py` - Bot tests
- `DEPLOYMENT.md` - Deployment guide
- Changes to `rivet_pro/adapters/telegram/bot.py` - Webhook mode

Review and commit:
```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
git status
git add .
git commit -m "feat: Complete RIVET-007 through RIVET-011"
git push origin ralph/mvp-phase1
```

---

## Need Help?

**Full instructions:** See `MANUAL_N8N_TASKS.md`

**Parse NEON_DATABASE_URL example:**
```
postgresql://myuser:abc123@ep-cool-name.us-east-2.aws.neon.tech/neondb?sslmode=require

Host:     ep-cool-name.us-east-2.aws.neon.tech
Port:     5432
Database: neondb
User:     myuser
Password: abc123
SSL:      ON
```

**If n8n isn't accessible:**
```bash
ssh root@72.60.175.144
docker ps | grep n8n
docker restart n8n  # if needed
```

---

**Total time: ~30 minutes for both manual tasks**
**Ralph time: ~1-2 hours for 3 automated tasks**

**Do them in parallel and you're done in ~1-2 hours total! 🚀**
