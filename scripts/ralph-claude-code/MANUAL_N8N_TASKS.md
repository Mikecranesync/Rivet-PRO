# Manual n8n UI Configuration Tasks

**These tasks require you to log into the n8n web interface and configure credentials. Ralph cannot do these - they're UI-only.**

---

## Prerequisites

- Access to VPS: 72.60.175.144
- n8n running on port 5678
- Browser (Chrome/Firefox recommended)

---

## RIVET-007: Verify n8n Photo Bot v2 Gemini Credential

**Time Required:** 10-15 minutes
**Priority:** P0 - MVP Blocker

### Step 1: Log into n8n

1. Open your web browser
2. Navigate to: `http://72.60.175.144:5678`
3. You should see the n8n login screen
4. Enter your n8n credentials and click "Sign in"

### Step 2: Find the Photo Bot v2 Workflow

1. Once logged in, you'll see the n8n dashboard
2. Look for the left sidebar with "Workflows" menu
3. Click on "Workflows" to see the list of all workflows
4. Find the workflow named **"Photo Bot v2"** or **"RIVET Photo Bot v2"**
   - The workflow ID is: `7LMKcMmldZsu1l6g`
5. Click on the workflow name to open it

### Step 3: Locate the Gemini Vision Node

1. You'll see a canvas with connected nodes (boxes)
2. Look for a node labeled **"Gemini Vision"** or **"Google Gemini"** or **"AI Vision"**
3. Click on that node to select it
4. The node should have a gear icon or settings panel on the right

### Step 4: Check the Credential

1. Inside the node settings (right panel), look for a field called **"Credential"** or **"API Credential"**
2. You should see a dropdown with one of these states:
   - ✅ **Green checkmark** with a credential name (e.g., "Google Gemini API") - GOOD!
   - ⚠️ **Red warning** or "Select credential" - BAD, needs setup
   - ❌ **Missing credential** or blank - BAD, needs setup

### Step 5A: If Credential Exists (Green Checkmark)

1. Click the **"Test"** button at the bottom of the node settings
2. You should see "Success" or a sample response
3. ✅ **Done!** Mark RIVET-007 as complete

### Step 5B: If Credential is Missing (Red Warning)

You need to create a new credential:

1. Click the dropdown that says "Select credential"
2. Click **"+ Create New Credential"**
3. You'll see a credential creation form

**Fill in the form:**

- **Credential Type:** Google Gemini API (or Google AI)
- **Name:** Give it a name like "Gemini Production"
- **API Key:** You need to get this from your environment

**To find your Gemini API Key:**

Option 1 - Check .env file on VPS:
```bash
ssh root@72.60.175.144
cat /root/Rivet-PRO/.env | grep GEMINI_API_KEY
```

Option 2 - Check your local .env:
```bash
# On Windows
type C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\.env | findstr GEMINI_API_KEY
```

4. Copy the API key value (after `GEMINI_API_KEY=`)
5. Paste it into the "API Key" field in n8n
6. Click **"Create"** to save the credential
7. The node should now show the green checkmark

### Step 6: Test the Workflow

1. Click the **"Execute Workflow"** button (top right, looks like a play button ▶️)
2. If you see a prompt "Workflow needs manual trigger", click **"Execute Workflow"** again
3. Watch the nodes light up as they execute
4. The workflow should complete without errors
5. Check the output - you should see equipment identification data

### Step 7: Verify Success

✅ **Success criteria:**
- No red error messages
- Gemini Vision node completed successfully
- Output contains equipment data (name, manufacturer, model)

❌ **If you see errors:**
- Double-check the API key is correct
- Make sure the credential is selected on the node
- Try clicking "Save" at the top right
- Try executing the workflow again

---

## RIVET-009: Wire Ralph Workflow Database Credentials

**Time Required:** 15-20 minutes
**Priority:** P1 - Important for Autonomous Development

### Step 1: Log into n8n (Same as Before)

1. Open browser to `http://72.60.175.144:5678`
2. Sign in with your credentials

### Step 2: Find the Ralph Main Loop Workflow

1. Click "Workflows" in the left sidebar
2. Find the workflow named **"Ralph Main Loop"** or **"Ralph Workflow"**
3. Click to open it

### Step 3: Identify Postgres Nodes Without Credentials

1. Look at the workflow canvas
2. Find all **purple/blue database icon nodes** labeled "Postgres"
3. You should see approximately 7 of them
4. Click on each one and check if it has a credential configured
5. If you see a **red warning icon** or "Select credential", it needs setup

### Step 4: Create Neon PostgreSQL Credential (If Needed)

**First, check if a Neon credential already exists:**

1. Click on any Postgres node
2. Look at the "Credential" dropdown
3. If you see "Neon PostgreSQL" or similar, use that existing one
4. If not, create a new one:

**To create new Neon credential:**

1. Click the credential dropdown
2. Click **"+ Create New Credential"**
3. Select **"Postgres"** as the credential type
4. Name it: **"Neon PostgreSQL - Ralph"**

**You need the Neon connection details:**

Option 1 - From .env file on VPS:
```bash
ssh root@72.60.175.144
cat /root/Rivet-PRO/.env | grep NEON_DATABASE_URL
```

Option 2 - From your local .env:
```bash
type C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\.env | findstr NEON_DATABASE_URL
```

**The NEON_DATABASE_URL looks like:**
```
postgresql://username:password@hostname.neon.tech/database?sslmode=require
```

**Parse the connection string and fill in n8n fields:**

- **Host:** The part after `@` and before `/` (e.g., `ep-cool-name-123456.us-east-2.aws.neon.tech`)
- **Port:** `5432` (default PostgreSQL port)
- **Database:** The part after the last `/` and before `?` (e.g., `neondb`)
- **User:** The part between `//` and `:` (before the password)
- **Password:** The part between `:` and `@` (after username)
- **SSL:** Toggle ON (or select "require")

**Example parsing:**
```
postgresql://myuser:mypass123@ep-cool-name.neon.tech/mydb?sslmode=require

Host:     ep-cool-name.neon.tech
Port:     5432
Database: mydb
User:     myuser
Password: mypass123
SSL:      ON/require
```

5. Fill in all fields
6. Click **"Create"** to save the credential

### Step 5: Wire Credential to All 7 Postgres Nodes

Now you need to apply this credential to each Postgres node:

1. Click on **Postgres Node #1**
2. Find the "Credential" dropdown in the settings panel
3. Select your newly created **"Neon PostgreSQL - Ralph"** credential
4. You should see a green checkmark appear
5. **Repeat for all 7 Postgres nodes:**
   - Node 1: (whatever it's named, e.g., "Get Stories")
   - Node 2: (e.g., "Update Progress")
   - Node 3: (e.g., "Insert Result")
   - Node 4: ...continue for all 7
6. Make sure each one shows the green checkmark

### Step 6: Save the Workflow

1. Click the **"Save"** button at the top right
2. You should see "Workflow saved" confirmation

### Step 7: Test the Workflow

1. Click the **"Execute Workflow"** button (▶️ at top right)
2. Watch the nodes execute
3. Check that all Postgres nodes complete successfully (green checkmarks)
4. Check for any red error messages

### Step 8: Verify Database Connection

✅ **Success criteria:**
- All 7 Postgres nodes have credentials configured
- Workflow executes without database connection errors
- No "password authentication failed" errors
- No "connection timeout" errors

❌ **Common issues and fixes:**

**Issue: "password authentication failed"**
- Double-check the username and password from NEON_DATABASE_URL
- Make sure there are no extra spaces in the credential fields

**Issue: "connection timeout"**
- Verify the host is correct (should end in .neon.tech)
- Check that SSL is enabled

**Issue: "database does not exist"**
- Verify the database name matches NEON_DATABASE_URL

**Issue: "could not connect to server"**
- Check VPS has internet access
- Verify Neon database is not paused (check Neon dashboard)

---

## Completion Checklist

When you're done with both tasks, verify:

### RIVET-007 ✅
- [ ] Logged into n8n successfully
- [ ] Found Photo Bot v2 workflow
- [ ] Gemini Vision node has valid credential
- [ ] Workflow executes without errors
- [ ] Output shows equipment identification

### RIVET-009 ✅
- [ ] Logged into n8n successfully
- [ ] Found Ralph Main Loop workflow
- [ ] Identified all 7 Postgres nodes
- [ ] Created Neon PostgreSQL credential
- [ ] Applied credential to all 7 nodes
- [ ] Workflow executes without database errors
- [ ] Can read from and write to database

---

## Need Help?

If you get stuck:

1. **Check n8n logs:**
   ```bash
   ssh root@72.60.175.144
   docker logs n8n-container
   ```

2. **Verify n8n is running:**
   ```bash
   ssh root@72.60.175.144
   docker ps | grep n8n
   ```

3. **Restart n8n if needed:**
   ```bash
   ssh root@72.60.175.144
   docker restart n8n-container
   ```

4. **Check Neon database status:**
   - Log into Neon dashboard
   - Verify database is not paused
   - Check connection string is correct

---

**Once both manual tasks are complete, Ralph can continue with the automated code tasks (RIVET-008, 010, 011).**
