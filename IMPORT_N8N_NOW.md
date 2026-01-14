# Import Rivet n8n Workflow NOW

**Status:** Java backend building (skip CMMS for now)
**Action:** Import and test OCR workflow

---

## ✅ Step 1: Import Workflow (2 min)

1. **Go to:** http://localhost:5678
2. **Click:** Workflows → + Add workflow
3. **Click:** ⋮ menu (top right) → Import from File
4. **Select:** `C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\rivet-n8n-workflow\rivet_workflow_clean.json`
5. **Click:** Import

---

## ✅ Step 2: Add Telegram Credential (2 min)

1. **Click any Telegram node** (has yellow warning)
2. **Click:** "Select Credential" dropdown
3. **Click:** "+ Create New Credential"
4. **Type:** "Telegram API"
5. **Name:** `Rivet CMMS Bot`
6. **Access Token:** `8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE`
7. **Click:** Save

✅ All Telegram nodes will auto-use this credential

---

## ✅ Step 3: Set Google API Variable (1 min)

1. **Click:** Settings (gear icon, bottom left)
2. **Navigate to:** Variables section
3. **Click:** + Add Variable
4. **Key:** `GOOGLE_API_KEY`
5. **Value:** `AIzaSyBOEFzA3fWyS_s92h4Sd7ZaWIctiVXZjlA`
6. **Click:** Save

---

## ✅ Step 4: Set Tavily API Credential (2 min)

1. **Find node:** "Quick Manual Search" or "Deep Manual Search"
2. **Click:** yellow warning icon
3. **Click:** "+ Create New Credential"
4. **Type:** "HTTP Header Auth"
5. **Name:** `Tavily Search API`
6. **Header Name:** `Authorization`
7. **Header Value:** `Bearer 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`
8. **Click:** Save

---

## ✅ Step 5: Disable CMMS Nodes (Temporary - 1 min)

Since Java backend is still building, disable these nodes:

1. **Find nodes:**
   - "Search Atlas CMMS"
   - "Create Asset"
   - "Update Asset"

2. **For each node:**
   - Right-click → Disable
   - OR click node → toggle "Enabled" off

This lets you test OCR without CMMS.

---

## ✅ Step 6: Activate Workflow (30 sec)

1. **Click:** Save button (top right)
2. **Toggle:** Active switch to ON (should turn green)

✅ Workflow is now listening!

---

## ✅ Step 7: Test with Telegram (2 min)

### Test 1: Text Message
1. Open Telegram
2. Search for your bot: `@` + bot username
3. Send: `Hello`

**Expected:** Bot asks for a photo

### Test 2: Equipment Photo
1. Send any equipment photo (nameplate, label, etc.)
2. Wait 5-10 seconds

**Expected:**
```
📋 Equipment Details

Manufacturer: [Extracted from photo]
Model: [Extracted from photo]
Serial: [Extracted from photo]

Confidence: XX%
```

If confidence > 70%, OCR is working! ✅

---

## 🎯 What's Working Now

✅ Telegram bot integration
✅ Photo OCR (Gemini Vision)
✅ Manual search (Tavily - optional)
⏳ CMMS integration (pending Java backend)

---

## 🔧 Add CMMS Later

Once Java backend is ready:

1. Get JWT token:
   ```bash
   curl -X POST http://localhost:8080/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@example.com","password":"admin"}'
   ```

2. Create Atlas CMMS credential:
   - Type: HTTP Header Auth
   - Header: `Authorization`
   - Value: `Bearer YOUR_JWT_TOKEN`

3. Re-enable CMMS nodes
4. Set `ATLAS_CMMS_URL` variable: `http://localhost:8080/api`

---

## ✅ Quick Checklist

- [ ] Workflow imported
- [ ] Telegram credential added
- [ ] GOOGLE_API_KEY variable set
- [ ] Tavily credential added (optional)
- [ ] CMMS nodes disabled (temporary)
- [ ] Workflow activated
- [ ] Test message sent
- [ ] Photo OCR working

---

**Start here:** http://localhost:5678

**Need help?** Each step takes < 2 minutes. You'll be testing in 10 minutes!
