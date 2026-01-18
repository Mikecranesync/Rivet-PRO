# ATLAS CMMS Login Investigation Guide

**Target System:** Atlas CMMS Web UI at http://72.60.175.144:3000 (Java API at :8080)
**Purpose:** Systematically diagnose authentication/login failures
**Created:** January 18, 2026

---

## Overview

This guide walks through 7 investigation phases to identify why users cannot log in to Atlas CMMS. Each phase builds on the previous, narrowing down the root cause.

**Common symptoms:**
- Login form submits but nothing happens
- "Invalid credentials" error for correct password
- Page refreshes but user isn't logged in
- CORS errors in browser console
- Network errors when submitting login

---

## Phase 1: Environment Variables

### What to Check

Environment variables control authentication behavior. Missing or misconfigured values cause silent failures.

### Required Variables

```bash
# Authentication
JWT_SECRET=your-secret-key-at-least-32-characters
JWT_EXPIRATION=86400

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname
# OR
MONGO_URI=mongodb://user:pass@host:27017/dbname

# CORS
CORS_ORIGIN=https://cmms.rivet.com
# OR
ALLOWED_ORIGINS=https://cmms.rivet.com,http://localhost:3000

# Frontend
REACT_APP_API_URL=https://api.cmms.rivet.com
# OR
NEXT_PUBLIC_API_URL=https://api.cmms.rivet.com
```

### How to Check

**On VPS/Server:**
```bash
# View all environment variables in .env
cat .env | grep -v "^#" | grep -v "^$"

# Check if JWT_SECRET is set and long enough
grep "JWT_SECRET" .env | wc -c
# Should be > 40 characters (key=value + 32+ char secret)

# Check database URL format
grep "DATABASE\|MONGO" .env
```

**In Docker:**
```bash
# Check variables inside container
docker exec <backend-container> env | grep -i "jwt\|database\|mongo\|cors"
```

### Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| JWT_SECRET missing | Login succeeds but token invalid | Add 32+ char secret to .env |
| JWT_SECRET too short | Token verification fails randomly | Use longer secret |
| Wrong DATABASE_URL | "Cannot connect to database" | Verify connection string |
| CORS_ORIGIN mismatch | Browser blocks requests | Match frontend URL exactly |

---

## Phase 2: Docker Configuration

### What to Check

Docker-compose misconfiguration causes services to fail silently or not communicate.

### Required Configuration

```yaml
# docker-compose.yml
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://backend:5000
    depends_on:
      - backend
    networks:
      - app-network

  backend:
    build: ./backend
    ports:
      - "5000:5000"
    environment:
      - JWT_SECRET=${JWT_SECRET}
      - DATABASE_URL=${DATABASE_URL}
      - CORS_ORIGIN=http://localhost:3000
    depends_on:
      - database
    networks:
      - app-network

  database:
    image: mongo:6  # or postgres:14
    ports:
      - "27017:27017"
    volumes:
      - db-data:/data/db
    networks:
      - app-network

networks:
  app-network:
    driver: bridge

volumes:
  db-data:
```

### How to Check

```bash
# Validate docker-compose syntax
docker-compose config

# Check service definitions
docker-compose config --services

# Check network configuration
docker network ls
docker network inspect <network-name>
```

### Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| Missing network | Services can't communicate | Add shared network to all services |
| Wrong depends_on | Backend starts before DB ready | Add proper dependency chain |
| Port conflicts | Container won't start | Change host port mapping |
| Missing env_file | Variables not loaded | Add `env_file: .env` to service |

---

## Phase 3: Docker Container Status

### What to Check

Containers must be running and healthy for authentication to work.

### How to Check

```bash
# List all containers (running and stopped)
docker ps -a

# Check container health
docker inspect --format='{{.State.Health.Status}}' <container>

# View container logs
docker logs <container> --tail 100

# Check resource usage
docker stats --no-stream

# Check if container is restarting
docker events --filter 'event=restart' --since 5m
```

### Expected Output

```
CONTAINER ID   IMAGE          STATUS                    PORTS                    NAMES
abc123         atlas/front    Up 2 hours (healthy)      0.0.0.0:3000->3000/tcp   atlas-frontend
def456         atlas/back     Up 2 hours (healthy)      0.0.0.0:5000->5000/tcp   atlas-backend
ghi789         mongo:6        Up 2 hours                0.0.0.0:27017->27017/tcp atlas-db
```

### Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| Container exited | STATUS shows "Exited" | Check logs: `docker logs <container>` |
| Container restarting | STATUS shows "Restarting" | Fix crash cause, check memory limits |
| Unhealthy status | Healthcheck failing | Review healthcheck command/endpoint |
| Port not mapped | Cannot access from host | Add port mapping to docker-compose |

---

## Phase 4: Network Connectivity

### What to Check

Services must be able to reach each other over the Docker network.

### How to Check

**From host machine:**
```bash
# Test frontend
curl -I http://localhost:3000

# Test backend health
curl http://localhost:5000/api/health

# Test login endpoint (expect 401 or validation error)
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"wrong"}'
```

**From inside container:**
```bash
# Enter backend container
docker exec -it <backend-container> sh

# Test database connectivity
nc -zv database 27017  # MongoDB
nc -zv database 5432   # PostgreSQL

# Test from frontend container
docker exec -it <frontend-container> sh
nc -zv backend 5000
```

**DNS resolution inside Docker:**
```bash
docker exec <backend-container> nslookup database
docker exec <frontend-container> nslookup backend
```

### Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| DNS not resolving | "Unknown host" error | Services on different networks |
| Connection refused | Port not listening | Service not started or wrong port |
| Timeout | Network isolation | Check firewall rules |
| Wrong hostname | Frontend uses localhost | Use service name in Docker |

---

## Phase 5: Database Connectivity

### What to Check

Authentication requires database access to verify credentials.

### MongoDB Checks

```bash
# Test MongoDB connection
docker exec <mongo-container> mongosh --eval "db.adminCommand('ping')"

# Check if users collection exists
docker exec <mongo-container> mongosh atlas-cmms --eval "db.users.countDocuments()"

# Check if admin user exists
docker exec <mongo-container> mongosh atlas-cmms --eval \
  "db.users.findOne({email: 'admin@example.com'})"
```

### PostgreSQL Checks

```bash
# Test PostgreSQL connection
docker exec <postgres-container> pg_isready

# Check users table
docker exec <postgres-container> psql -U postgres -d atlas-cmms -c \
  "SELECT id, email FROM users LIMIT 5;"

# Check if admin user exists
docker exec <postgres-container> psql -U postgres -d atlas-cmms -c \
  "SELECT email, created_at FROM users WHERE email = 'admin@example.com';"
```

### Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| No users in DB | All logins fail | Run seed script or create user |
| Wrong database name | Tables not found | Check DATABASE_URL path |
| Auth required | Connection refused | Add credentials to connection string |
| Password hash mismatch | bcrypt version issue | Recreate user with same bcrypt version |

---

## Phase 6: Application Logs

### What to Check

Application logs reveal authentication errors that aren't visible to users.

### How to Check

```bash
# Backend logs - last 100 lines
docker logs <backend-container> --tail 100

# Backend logs - follow in real-time
docker logs <backend-container> -f

# Filter for auth-related errors
docker logs <backend-container> 2>&1 | grep -i "auth\|jwt\|token\|login\|password"

# Filter for errors only
docker logs <backend-container> 2>&1 | grep -i "error\|exception\|fail"
```

### Error Patterns to Look For

```
# JWT errors
"JsonWebTokenError: invalid signature"
"TokenExpiredError: jwt expired"
"Error: secretOrPrivateKey must have a value"

# Database errors
"MongoError: Authentication failed"
"Error: connect ECONNREFUSED"
"SequelizeConnectionError"

# CORS errors (from frontend/browser)
"Access to XMLHttpRequest blocked by CORS policy"
"No 'Access-Control-Allow-Origin' header"

# Password/Auth errors
"Invalid password"
"User not found"
"bcrypt: Invalid salt version"
```

### Common Issues

| Issue | Log Message | Fix |
|-------|-------------|-----|
| JWT secret missing | "secretOrPrivateKey must have a value" | Set JWT_SECRET in .env |
| Token expired | "jwt expired" | Increase JWT_EXPIRATION |
| Invalid token | "invalid signature" | JWT_SECRET changed, users must re-login |
| DB auth failed | "Authentication failed" | Fix database credentials |

---

## Phase 7: CORS Configuration

### What to Check

CORS blocks browser requests if misconfigured. Backend works with curl but fails in browser.

### How to Check

```bash
# Test CORS preflight (OPTIONS request)
curl -I -X OPTIONS http://localhost:5000/api/auth/login \
  -H "Origin: https://cmms.rivet.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type"
```

### Expected Headers

```
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://cmms.rivet.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Allow-Credentials: true
```

### Backend CORS Setup (Node.js/Express)

```javascript
const cors = require('cors');

// Option 1: Simple (allows all origins - NOT for production)
app.use(cors());

// Option 2: Specific origin (RECOMMENDED)
app.use(cors({
  origin: process.env.CORS_ORIGIN || 'https://cmms.rivet.com',
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

// Option 3: Multiple origins
app.use(cors({
  origin: ['https://cmms.rivet.com', 'http://localhost:3000'],
  credentials: true
}));
```

### Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| No CORS headers | "blocked by CORS policy" | Add cors middleware |
| Wrong origin | "not allowed by CORS" | Match frontend URL exactly |
| Missing credentials | Cookies not sent | Add `credentials: true` |
| Preflight fails | OPTIONS returns 404 | Handle OPTIONS requests |

---

## Quick Reference: Error → Phase Mapping

| Error Message | Check Phase |
|---------------|-------------|
| "CORS policy" | Phase 7: CORS |
| "Invalid credentials" | Phase 5: Database |
| "Cannot connect" | Phase 4: Network |
| "jwt malformed" | Phase 1: Environment |
| "Container exited" | Phase 3: Docker Status |
| "Service unavailable" | Phase 3: Docker Status |
| "Network Error" | Phase 4: Network |
| "Unauthorized" | Phase 6: Logs |

---

## Diagnostic Workflow

```
START
  │
  ▼
┌─────────────────┐
│ Run diagnostic  │
│ script          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     YES    ┌─────────────────┐
│ Containers      │───────────>│ Fix Docker      │
│ running?        │            │ (Phase 3)       │
└────────┬────────┘            └─────────────────┘
         │ NO
         ▼
┌─────────────────┐     YES    ┌─────────────────┐
│ Network         │───────────>│ Fix Network     │
│ errors?         │            │ (Phase 4)       │
└────────┬────────┘            └─────────────────┘
         │ NO
         ▼
┌─────────────────┐     YES    ┌─────────────────┐
│ Database        │───────────>│ Fix Database    │
│ errors?         │            │ (Phase 5)       │
└────────┬────────┘            └─────────────────┘
         │ NO
         ▼
┌─────────────────┐     YES    ┌─────────────────┐
│ CORS errors in  │───────────>│ Fix CORS        │
│ browser?        │            │ (Phase 7)       │
└────────┬────────┘            └─────────────────┘
         │ NO
         ▼
┌─────────────────┐     YES    ┌─────────────────┐
│ JWT errors in   │───────────>│ Fix JWT/Env     │
│ logs?           │            │ (Phase 1)       │
└────────┬────────┘            └─────────────────┘
         │ NO
         ▼
┌─────────────────┐
│ Check browser   │
│ console for     │
│ client-side     │
│ errors          │
└─────────────────┘
```

---

## Next Steps

After identifying the root cause:

1. **Apply fix:** See `atlas_cmms_auth_fixes.md` for code solutions
2. **Test:** Run diagnostic script again
3. **Verify:** Test login in browser
4. **Commit:** Use `GITHUB_PR_TEMPLATE.md` for your fix

---

*Document created for RIVET Pro / Atlas CMMS Integration*
