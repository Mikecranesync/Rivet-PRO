# Atlas CMMS Credentials & Access

**Updated:** 2026-01-06

---

## 🔑 Your Atlas CMMS Credentials

### Login Credentials
```
Email:    admin@example.com
Password: admin
```

### API Endpoint
```
Base URL: http://localhost:8080/api
```

### Database Connection
```
Database URL: postgresql://neondb_owner:npg_c3UNa4KOlCeL@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require
```

---

## 🚀 How to Start Atlas CMMS Backend

### Option 1: Docker Compose (Recommended)

```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO

# Start Java backend + Database
docker-compose up -d rivet-java postgres

# Wait for startup (about 30-60 seconds)
# Check if ready:
curl http://localhost:8080/api/health
```

**Expected response:**
```json
{
  "status": "UP",
  "service": "Rivet CMMS API",
  "version": "1.0.0",
  "database": "UP"
}
```

### Option 2: Start All Services

```bash
# Start entire stack
docker-compose up -d

# Services started:
# - postgres (Database)
# - rivet-java (Atlas CMMS API)
# - rivet-python (Legacy Python API)
# - nginx (Reverse proxy)
# - redis (Cache)
# - minio (File storage)
```

---

## 🎫 Get JWT Token for n8n

Once backend is running, get your JWT token:

### Method 1: Login (if user exists)
```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin"}'
```

### Method 2: Register new user (if needed)
```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin","name":"Admin User"}'
```

**Response format:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "...",
    "email": "admin@example.com",
    "name": "Admin User"
  }
}
```

**Copy the `token` value** - This is your JWT token for n8n!

---

## 📝 Add JWT Token to n8n

### Step 1: Copy Your JWT Token
From the API response above, copy the entire token (starts with `eyJ...`)

### Step 2: Create n8n Credential

1. Open n8n: http://localhost:5678
2. Go to: **Credentials** → **+ Create New Credential**
3. Search: **"HTTP Header Auth"**
4. Fill in:
   - **Name:** `Atlas CMMS API`
   - **Header Name:** `Authorization`
   - **Header Value:** `Bearer YOUR_JWT_TOKEN_HERE`
     (Paste the token after "Bearer ")
5. Click **Save**

### Step 3: Assign to Workflow Nodes

In your imported workflow, assign this credential to:
- "Search Atlas CMMS" node
- "Create Asset" node
- "Update Asset" node

---

## 🧪 Test Atlas CMMS API

### Test 1: Health Check
```bash
curl http://localhost:8080/api/health
```

### Test 2: List Assets (with JWT)
```bash
# Replace YOUR_TOKEN with actual JWT token
curl http://localhost:8080/api/assets \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test 3: Create Asset (with JWT)
```bash
curl -X POST http://localhost:8080/api/assets \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "manufacturer": "Siemens",
    "modelNumber": "SIMATIC S7-1200",
    "serialNumber": "6ES7214-1AG40-0XB0"
  }'
```

---

## 🔧 Troubleshooting

### Backend won't start
```bash
# Check Docker logs
docker-compose logs rivet-java

# Common issues:
# 1. Port 8080 already in use
# 2. Database connection failed
# 3. Build errors (check Dockerfile)
```

### Can't login / Register fails
```bash
# Check database connection
docker-compose logs postgres

# Reset database (WARNING: deletes data)
docker-compose down -v
docker-compose up -d postgres
# Wait 10 seconds
docker-compose up -d rivet-java
```

### JWT Token expired
```bash
# JWT tokens expire after 24 hours
# Just login again to get new token:
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin"}'

# Update n8n credential with new token
```

### Port 8080 already in use
```bash
# Find what's using port 8080
netstat -ano | findstr :8080

# Or change port in docker-compose.yml:
# ports:
#   - "8081:8080"  # Change first port
```

---

## 📊 API Endpoints Reference

### Authentication
- POST `/api/auth/register` - Create account
- POST `/api/auth/login` - Get JWT token
- POST `/api/auth/telegram` - Telegram bot auth
- GET `/api/auth/me` - Current user info (requires JWT)

### Assets (Equipment)
- GET `/api/assets` - List all assets
- GET `/api/assets/{id}` - Get specific asset
- POST `/api/assets` - Create new asset
- PUT `/api/assets/{id}` - Update asset
- DELETE `/api/assets/{id}` - Delete asset
- GET `/api/assets/search?q=` - Search assets
- POST `/api/assets/match-or-create` - Fuzzy match or create

### Work Orders
- GET `/api/work-orders` - List work orders
- GET `/api/work-orders/{id}` - Get specific WO
- POST `/api/work-orders` - Create work order
- PATCH `/api/work-orders/{id}/status` - Update status
- GET `/api/work-orders/stats` - Dashboard stats

### Health
- GET `/api/health` - Service health check

---

## 🌐 Web Access

### Swagger UI (API Documentation)
- URL: http://localhost:8080/swagger-ui.html
- Test all endpoints interactively
- See request/response examples

### Database Admin (if pgAdmin running)
- URL: http://localhost:5050
- Email: admin@example.com
- Password: admin

---

## 🔐 Security Notes

### Production Deployment
For production, change these:

1. **Strong password:**
   ```
   ATLAS_ADMIN_PASSWORD=your_secure_password_here
   ```

2. **Secure JWT secret:**
   ```
   JWT_SECRET_KEY=generate_long_random_string_here
   ```

3. **Database credentials:**
   Use production Neon database with strong password

4. **CORS origins:**
   ```
   CORS_ALLOWED_ORIGINS=https://yourdomain.com
   ```

### Current Setup (Development)
⚠️ These are development credentials:
- Default password: `admin`
- Open CORS: `localhost`
- HTTP (not HTTPS)

**DO NOT use in production!**

---

## 📱 Telegram Bot Integration

Your bot token is already configured:
```
TELEGRAM_BOT_TOKEN=8161680636:AAGF8eyldKWGF2I0qVSWXxveonRy02GH_nE
```

Users can authenticate via Telegram:
```bash
POST /api/auth/telegram
{
  "telegramUserId": "123456789"
}
```

This auto-creates users and returns JWT token.

---

## ✅ Quick Start Checklist

- [ ] Start backend: `docker-compose up -d rivet-java postgres`
- [ ] Check health: `curl http://localhost:8080/api/health`
- [ ] Get JWT token: Login via API
- [ ] Add JWT to n8n: Create "HTTP Header Auth" credential
- [ ] Test API: Create test asset
- [ ] Configure workflow: Assign credential to CMMS nodes

---

**Need the JWT token now?**

Run this:
```bash
# Start backend
docker-compose up -d rivet-java postgres

# Wait 30 seconds, then:
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin"}'

# Copy the "token" from response!
```
