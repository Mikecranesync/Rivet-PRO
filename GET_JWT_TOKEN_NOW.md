# Get Your Atlas CMMS JWT Token NOW

**Quick reference:** 2026-01-06

---

## 🔑 Your Login Credentials

```
Email:    admin@example.com
Password: admin
API URL:  http://localhost:8080/api
```

---

## 🚀 Get JWT Token (2 Steps)

### Step 1: Start Backend (if not running)

```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO

# Start backend + database
docker-compose up -d rivet-java postgres

# Wait 30 seconds for startup...
```

### Step 2: Get JWT Token

**Copy and run this command:**

```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin"}'
```

**If login fails (user doesn't exist), register first:**

```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin","name":"Admin User"}'
```

**Response will look like:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkFkbWluIFVzZXIiLCJpYXQiOjE1MTYyMzkwMjJ9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
  "user": {
    "id": "abc123",
    "email": "admin@example.com",
    "name": "Admin User"
  }
}
```

**→ COPY THE TOKEN VALUE** (the long string starting with `eyJ...`)

---

## 📝 Add Token to n8n

### Method 1: Create New Credential

1. Open n8n: **http://localhost:5678**
2. Click: **Credentials** → **+ Create New Credential**
3. Search: **"HTTP Header Auth"**
4. Fill in:
   - **Name:** `Atlas CMMS API`
   - **Header Name:** `Authorization`
   - **Header Value:** `Bearer YOUR_TOKEN_HERE`

     ↓ Paste your token after "Bearer " like this:

     `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

5. Click: **Save**

### Method 2: Use Automated Script

```bash
# Set your token as environment variable
export ATLAS_JWT_TOKEN="your_token_here"

# Run this to auto-create credential:
curl -X POST http://localhost:5678/api/v1/credentials \
  -H "X-N8N-API-KEY: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMTVjYWY5Ny04YjU4LTQwZDEtOGQwZi02Y2I0NzA0NDIwMjUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY3Njk5NTQxLCJleHAiOjE3NzAyNjc2MDB9.u1YVLEVetchYP2FcmUjfQSqNldb24gYbeSEArRT07lM" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Atlas CMMS API",
    "type": "httpHeaderAuth",
    "data": {
      "name": "Authorization",
      "value": "Bearer '"$ATLAS_JWT_TOKEN"'"
    }
  }'
```

---

## 🔧 Troubleshooting

### "Connection refused" error
Backend not running. Start it:
```bash
docker-compose up -d rivet-java postgres
# Wait 30 seconds
curl http://localhost:8080/api/health
```

### "401 Unauthorized" error
Wrong credentials. Double-check:
- Email: `admin@example.com`
- Password: `admin`

### No response / Empty response
Backend still starting. Wait 30 more seconds and try again.

### Backend won't start
Check logs:
```bash
docker-compose logs rivet-java
```

Common issues:
- Port 8080 already in use → Change port in docker-compose.yml
- Database connection failed → Ensure postgres is running
- Build errors → Check Dockerfile syntax

---

## ✅ Quick Verification

**Test your JWT token works:**

```bash
# Replace YOUR_TOKEN with actual token
curl http://localhost:8080/api/assets \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected:** List of assets (or empty array `[]` if no assets yet)

**If 401 error:** Token invalid or expired, get new one

---

## 🎯 What the Token is For

Your JWT token lets n8n workflow:
- ✅ Search for existing equipment in Atlas CMMS
- ✅ Create new assets when equipment detected via OCR
- ✅ Update asset details and maintenance records
- ✅ Link work orders to equipment

**Without token:** OCR still works, but equipment won't be saved to CMMS

---

## ⏰ Token Expiration

**JWT tokens expire after 24 hours.**

When expired:
1. Run login command again
2. Get new token
3. Update n8n credential with new token

**Tip:** Set up a daily cron job to refresh the token automatically.

---

**Need help?** See `ATLAS_CMMS_CREDENTIALS.md` for complete documentation.
