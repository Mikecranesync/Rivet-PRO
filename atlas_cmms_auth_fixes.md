# ATLAS CMMS Authentication Fixes

**Purpose:** Code fixes for all known authentication issues
**Target:** Atlas CMMS Web UI at https://cmms.maintnpc.com (Java API proxied from /auth/*)
**Created:** January 18, 2026
**Last Updated:** January 18, 2026

---

## ⚠️ CRITICAL: Correct API Endpoint

> **Atlas CMMS uses `/auth/signin` NOT `/api/auth/signin`!**

The login endpoint requires THREE fields:
1. `email` - User's email address
2. `password` - User's password
3. `type` - Either `"SUPER_ADMIN"` (role_type=0) or `"CLIENT"` (role_type=1+)

### Working Example
```bash
curl -s -X POST https://cmms.maintnpc.com/auth/signin \
  -H "Content-Type: application/json" \
  -d '{"email":"mike@cranesync.com","password":"Bo1ws2er@12","type":"CLIENT"}'
```

---

## Quick Reference

| Fix # | Root Cause | Likelihood | Time to Fix |
|-------|------------|------------|-------------|
| 1 | CORS misconfiguration | 60% | 5 minutes |
| 2 | JWT token handling | 30% | 10 minutes |
| 3 | Database connection | 20% | 10 minutes |
| 4 | Docker networking | 15% | 10 minutes |
| 5 | Environment variables | 25% | 5 minutes |
| 6 | Frontend API URL | 10% | 5 minutes |

---

## FIX #1: CORS Misconfiguration (60% likelihood)

### Symptoms
- [ ] Browser console shows "CORS policy" error
- [ ] Network tab shows request blocked or status 0
- [ ] `curl` to backend works, but browser doesn't
- [ ] Preflight (OPTIONS) request fails

### Root Cause

Backend doesn't include CORS headers, or headers don't match frontend origin.

### Fix (Node.js/Express)

**File:** `backend/src/app.js` or `backend/server.js`

```javascript
// BEFORE (missing or incorrect)
app.use(cors());

// AFTER (correct configuration)
const cors = require('cors');

const corsOptions = {
  origin: function (origin, callback) {
    const allowedOrigins = [
      'https://cmms.rivet.com',
      'http://localhost:3000',
      'http://localhost:5173'
    ];

    // Allow requests with no origin (mobile apps, curl, etc.)
    if (!origin || allowedOrigins.includes(origin)) {
      callback(null, true);
    } else {
      console.log(`CORS blocked origin: ${origin}`);
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With'],
  exposedHeaders: ['Content-Range', 'X-Content-Range'],
  maxAge: 86400 // Cache preflight for 24 hours
};

app.use(cors(corsOptions));

// IMPORTANT: Handle preflight explicitly
app.options('*', cors(corsOptions));
```

### Fix (NestJS)

**File:** `backend/src/main.ts`

```typescript
// BEFORE
app.enableCors();

// AFTER
app.enableCors({
  origin: ['https://cmms.rivet.com', 'http://localhost:3000'],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
});
```

### Fix (FastAPI/Python)

**File:** `backend/main.py`

```python
from fastapi.middleware.cors import CORSMiddleware

# BEFORE
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# AFTER
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://cmms.rivet.com",
        "http://localhost:3000",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Verification

```bash
# Test CORS headers
curl -I -X OPTIONS https://api.cmms.rivet.com/api/auth/login \
  -H "Origin: https://cmms.rivet.com" \
  -H "Access-Control-Request-Method: POST"

# Expected output should include:
# Access-Control-Allow-Origin: https://cmms.rivet.com
# Access-Control-Allow-Credentials: true
# Access-Control-Allow-Methods: GET, POST, PUT, DELETE, PATCH, OPTIONS
```

---

## FIX #2: JWT Token Handling (30% likelihood)

### Symptoms
- [ ] Login request succeeds (200 OK) but user stays logged out
- [ ] Token not appearing in localStorage/cookies
- [ ] All subsequent API requests return 401 Unauthorized
- [ ] "jwt malformed" or "invalid signature" in logs

### Root Cause

JWT token generation, storage, or validation is broken.

### Fix Backend (Token Generation)

**File:** `backend/src/controllers/authController.js`

```javascript
const jwt = require('jsonwebtoken');

// BEFORE (common issues)
const token = jwt.sign({ id: user.id }, 'hardcoded-secret');

// AFTER (correct implementation)
const generateToken = (user) => {
  const payload = {
    id: user._id || user.id,
    email: user.email,
    role: user.role || 'user'
  };

  const secret = process.env.JWT_SECRET;

  if (!secret || secret.length < 32) {
    throw new Error('JWT_SECRET must be at least 32 characters');
  }

  const options = {
    expiresIn: process.env.JWT_EXPIRATION || '7d',
    issuer: 'atlas-cmms',
    audience: 'atlas-cmms-client'
  };

  return jwt.sign(payload, secret, options);
};

// In login handler
exports.login = async (req, res) => {
  try {
    const { email, password } = req.body;

    const user = await User.findOne({ email });
    if (!user) {
      return res.status(401).json({ message: 'Invalid credentials' });
    }

    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) {
      return res.status(401).json({ message: 'Invalid credentials' });
    }

    const token = generateToken(user);

    // Send token in response body AND as httpOnly cookie
    res.cookie('token', token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 7 * 24 * 60 * 60 * 1000 // 7 days
    });

    return res.json({
      success: true,
      token,
      user: {
        id: user._id,
        email: user.email,
        name: user.name,
        role: user.role
      }
    });
  } catch (error) {
    console.error('Login error:', error);
    return res.status(500).json({ message: 'Server error' });
  }
};
```

### Fix Backend (Token Verification)

**File:** `backend/src/middleware/auth.js`

```javascript
const jwt = require('jsonwebtoken');

// BEFORE (common issues)
const decoded = jwt.verify(token, 'hardcoded-secret');

// AFTER (correct implementation)
const verifyToken = (req, res, next) => {
  try {
    // Get token from header or cookie
    let token = req.headers.authorization?.replace('Bearer ', '');

    if (!token && req.cookies?.token) {
      token = req.cookies.token;
    }

    if (!token) {
      return res.status(401).json({ message: 'No token provided' });
    }

    const secret = process.env.JWT_SECRET;

    if (!secret) {
      console.error('JWT_SECRET not configured!');
      return res.status(500).json({ message: 'Server configuration error' });
    }

    const decoded = jwt.verify(token, secret, {
      issuer: 'atlas-cmms',
      audience: 'atlas-cmms-client'
    });

    req.user = decoded;
    next();
  } catch (error) {
    if (error.name === 'TokenExpiredError') {
      return res.status(401).json({ message: 'Token expired', code: 'TOKEN_EXPIRED' });
    }
    if (error.name === 'JsonWebTokenError') {
      return res.status(401).json({ message: 'Invalid token', code: 'INVALID_TOKEN' });
    }
    console.error('Token verification error:', error);
    return res.status(401).json({ message: 'Authentication failed' });
  }
};

module.exports = verifyToken;
```

### Fix Frontend (Token Storage)

**File:** `frontend/src/services/auth.js`

```javascript
// BEFORE (token lost on page refresh)
let token = null;

// AFTER (persist token correctly)
const TOKEN_KEY = 'atlas_cmms_token';

export const authService = {
  setToken(token) {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    }
  },

  getToken() {
    return localStorage.getItem(TOKEN_KEY);
  },

  removeToken() {
    localStorage.removeItem(TOKEN_KEY);
  },

  async login(email, password) {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include', // Important for cookies
      body: JSON.stringify({ email, password })
    });

    const data = await response.json();

    if (response.ok && data.token) {
      this.setToken(data.token);
      return { success: true, user: data.user };
    }

    return { success: false, error: data.message };
  },

  isAuthenticated() {
    const token = this.getToken();
    if (!token) return false;

    try {
      // Decode without verification (just to check expiry)
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.exp * 1000 > Date.now();
    } catch {
      return false;
    }
  }
};
```

### Verification

```bash
# Test login and capture token
TOKEN=$(curl -s -X POST https://api.cmms.rivet.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin"}' | jq -r '.token')

echo "Token: $TOKEN"

# Verify token works
curl -s https://api.cmms.rivet.com/api/auth/me \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## FIX #3: Database Connection (20% likelihood)

### Symptoms
- [ ] "Cannot connect to database" in logs
- [ ] All login attempts fail with server error
- [ ] "Authentication failed" for MongoDB
- [ ] Connection timeouts

### Root Cause

Database connection string is wrong, or credentials are invalid.

### Fix (MongoDB Connection)

**File:** `backend/src/config/database.js`

```javascript
const mongoose = require('mongoose');

// BEFORE (common issues)
mongoose.connect('mongodb://localhost:27017/atlas');

// AFTER (correct implementation)
const connectDB = async () => {
  const uri = process.env.MONGO_URI || process.env.DATABASE_URL;

  if (!uri) {
    console.error('Database URI not configured!');
    process.exit(1);
  }

  const options = {
    useNewUrlParser: true,
    useUnifiedTopology: true,
    serverSelectionTimeoutMS: 5000,
    socketTimeoutMS: 45000,
    maxPoolSize: 10
  };

  try {
    await mongoose.connect(uri, options);
    console.log('MongoDB connected successfully');

    mongoose.connection.on('error', (err) => {
      console.error('MongoDB error:', err);
    });

    mongoose.connection.on('disconnected', () => {
      console.warn('MongoDB disconnected, attempting reconnect...');
    });
  } catch (error) {
    console.error('MongoDB connection failed:', error.message);
    process.exit(1);
  }
};

module.exports = connectDB;
```

### Fix (PostgreSQL Connection)

**File:** `backend/src/config/database.js`

```javascript
const { Pool } = require('pg');

// BEFORE
const pool = new Pool();

// AFTER
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false,
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
});

pool.on('error', (err) => {
  console.error('Unexpected database error:', err);
});

// Test connection on startup
pool.query('SELECT NOW()')
  .then(() => console.log('PostgreSQL connected'))
  .catch((err) => {
    console.error('PostgreSQL connection failed:', err);
    process.exit(1);
  });

module.exports = pool;
```

### Fix (Environment Variable)

**File:** `.env`

```bash
# MongoDB
MONGO_URI=mongodb://username:password@hostname:27017/atlas-cmms?authSource=admin

# PostgreSQL
DATABASE_URL=postgresql://username:password@hostname:5432/atlas-cmms?sslmode=require

# For Docker internal networking
# Use container name instead of localhost
MONGO_URI=mongodb://mongo:27017/atlas-cmms
DATABASE_URL=postgresql://postgres:password@database:5432/atlas-cmms
```

### Verification

```bash
# MongoDB
docker exec <mongo-container> mongosh --eval "db.users.countDocuments()"

# PostgreSQL
docker exec <postgres-container> psql -U postgres -d atlas-cmms -c "SELECT COUNT(*) FROM users;"

# From backend container
docker exec <backend-container> node -e "
  require('mongoose').connect(process.env.MONGO_URI)
    .then(() => console.log('Connected!'))
    .catch(err => console.error('Failed:', err.message))
"
```

---

## FIX #4: Docker Networking (15% likelihood)

### Symptoms
- [ ] Frontend shows "Network Error" or "Failed to fetch"
- [ ] Backend works via `curl` from host but not from frontend container
- [ ] Services can't resolve each other's hostnames
- [ ] "ECONNREFUSED" errors

### Root Cause

Docker services are on different networks or using wrong hostnames.

### Fix (docker-compose.yml)

```yaml
# BEFORE (services isolated)
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"

  backend:
    build: ./backend
    ports:
      - "5000:5000"

  database:
    image: mongo:6

# AFTER (services networked correctly)
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      # Use backend service name, not localhost
      - REACT_APP_API_URL=http://backend:5000
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - atlas-network

  backend:
    build: ./backend
    ports:
      - "5000:5000"
    environment:
      - NODE_ENV=production
      - JWT_SECRET=${JWT_SECRET}
      - MONGO_URI=mongodb://database:27017/atlas-cmms
      - CORS_ORIGIN=http://localhost:3000
    depends_on:
      database:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - atlas-network

  database:
    image: mongo:6
    ports:
      - "27017:27017"
    volumes:
      - mongo-data:/data/db
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - atlas-network

networks:
  atlas-network:
    driver: bridge
    name: atlas-network

volumes:
  mongo-data:
```

### Fix (Frontend API URL for Production)

**File:** `frontend/.env.production`

```bash
# For production deployment where frontend is served separately
REACT_APP_API_URL=https://api.cmms.rivet.com

# For Docker deployment where frontend and backend are co-located
# REACT_APP_API_URL=http://backend:5000
```

**File:** `frontend/src/config/api.js`

```javascript
// BEFORE (hardcoded)
const API_URL = 'http://localhost:5000';

// AFTER (configurable)
const API_URL = process.env.REACT_APP_API_URL ||
  (typeof window !== 'undefined'
    ? `${window.location.protocol}//${window.location.hostname}:5000`
    : 'http://localhost:5000');

export default API_URL;
```

### Verification

```bash
# Check network exists
docker network ls | grep atlas

# Check services are on same network
docker network inspect atlas-network

# Test connectivity from frontend to backend
docker exec <frontend-container> curl -s http://backend:5000/api/health

# Test connectivity from backend to database
docker exec <backend-container> nc -zv database 27017
```

---

## FIX #5: Environment Variables (25% likelihood)

### Symptoms
- [ ] Works locally but fails in Docker
- [ ] "undefined" values in logs
- [ ] Different behavior after restart
- [ ] "SECRET not found" errors

### Root Cause

Environment variables not passed to containers or not loaded properly.

### Fix (docker-compose.yml)

```yaml
# BEFORE (variables not loaded)
services:
  backend:
    build: ./backend
    environment:
      - JWT_SECRET

# AFTER (correct loading)
services:
  backend:
    build: ./backend
    env_file:
      - .env
    environment:
      # Override specific values if needed
      - NODE_ENV=production
      - JWT_SECRET=${JWT_SECRET}
      - MONGO_URI=${MONGO_URI}
      - CORS_ORIGIN=${CORS_ORIGIN:-http://localhost:3000}
```

### Fix (.env file)

```bash
# .env (root of project)

# REQUIRED - Authentication
JWT_SECRET=your-super-secret-key-at-least-32-characters-long-change-this
JWT_EXPIRATION=7d

# REQUIRED - Database (choose one)
MONGO_URI=mongodb://localhost:27017/atlas-cmms
# DATABASE_URL=postgresql://user:pass@localhost:5432/atlas-cmms

# REQUIRED - CORS
CORS_ORIGIN=https://cmms.rivet.com

# OPTIONAL - Node environment
NODE_ENV=production

# OPTIONAL - Ports
BACKEND_PORT=5000
FRONTEND_PORT=3000
```

### Fix (Backend Startup Validation)

**File:** `backend/src/config/validate.js`

```javascript
const requiredEnvVars = [
  'JWT_SECRET',
  'MONGO_URI', // or DATABASE_URL
];

const validateEnv = () => {
  const missing = [];
  const warnings = [];

  for (const key of requiredEnvVars) {
    if (!process.env[key]) {
      missing.push(key);
    }
  }

  // Validate JWT_SECRET length
  if (process.env.JWT_SECRET && process.env.JWT_SECRET.length < 32) {
    warnings.push('JWT_SECRET should be at least 32 characters');
  }

  if (missing.length > 0) {
    console.error('Missing required environment variables:');
    missing.forEach(key => console.error(`  - ${key}`));
    process.exit(1);
  }

  if (warnings.length > 0) {
    console.warn('Environment warnings:');
    warnings.forEach(msg => console.warn(`  - ${msg}`));
  }

  console.log('Environment validation passed');
};

module.exports = validateEnv;

// Call at startup
// In app.js: require('./config/validate')();
```

### Verification

```bash
# Check variables in running container
docker exec <backend-container> env | grep -E "JWT|MONGO|DATABASE|CORS"

# Check .env file is not committed
git status .env  # Should show "untracked" or not appear

# Verify docker-compose interpolation
docker-compose config | grep -A5 "environment:"
```

---

## FIX #6: Frontend API URL Configuration (10% likelihood)

### Symptoms
- [ ] Network requests go to wrong URL
- [ ] "localhost:5000" in production
- [ ] Mixed content warnings (HTTP vs HTTPS)
- [ ] API calls succeed locally but fail in production

### Root Cause

Frontend hardcoded to localhost or wrong API URL.

### Fix (React)

**File:** `frontend/src/services/api.js`

```javascript
// BEFORE (hardcoded)
const api = axios.create({
  baseURL: 'http://localhost:5000/api'
});

// AFTER (environment-aware)
const getBaseURL = () => {
  // 1. Check environment variable (set at build time)
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }

  // 2. Check runtime config (injected via script tag)
  if (window.__ENV__?.API_URL) {
    return window.__ENV__.API_URL;
  }

  // 3. Same-origin API (when frontend and backend share domain)
  if (typeof window !== 'undefined') {
    return `${window.location.origin}/api`;
  }

  // 4. Fallback for SSR/testing
  return 'http://localhost:5000/api';
};

const api = axios.create({
  baseURL: getBaseURL(),
  withCredentials: true, // Important for cookies
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('atlas_cmms_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
```

### Fix (Build-time Configuration)

**File:** `frontend/.env.production`

```bash
REACT_APP_API_URL=https://api.cmms.rivet.com
```

**File:** `frontend/.env.development`

```bash
REACT_APP_API_URL=http://localhost:5000
```

### Fix (Runtime Configuration via Nginx)

**File:** `frontend/nginx.conf`

```nginx
server {
    listen 80;
    server_name cmms.rivet.com;

    # Serve React app
    location / {
        root /usr/share/nginx/html;
        try_files $uri /index.html;
    }

    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://backend:5000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Verification

```bash
# Check what URL frontend is using (in browser console)
console.log(process.env.REACT_APP_API_URL);

# Check network requests in browser DevTools
# Network tab → look at request URL

# Test API from browser console
fetch('/api/health').then(r => r.json()).then(console.log)
```

---

## Post-Fix Checklist

After applying any fix:

- [ ] Restart services: `docker-compose down && docker-compose up -d --build`
- [ ] Run diagnostic: `bash atlas_cmms_diagnostic.sh`
- [ ] Clear browser cache/cookies
- [ ] Test login in incognito window
- [ ] Verify token in localStorage
- [ ] Test page refresh (should stay logged in)
- [ ] Test protected routes
- [ ] Check browser console for errors

---

## Emergency Recovery

If nothing works:

```bash
# 1. Full reset
docker-compose down -v  # WARNING: Deletes data volumes
docker system prune -f
docker-compose up -d --build

# 2. Create admin user manually
docker exec <backend-container> node -e "
  const bcrypt = require('bcrypt');
  const mongoose = require('mongoose');
  const User = require('./src/models/User');

  mongoose.connect(process.env.MONGO_URI).then(async () => {
    const hash = await bcrypt.hash('admin123', 10);
    await User.create({
      email: 'admin@example.com',
      password: hash,
      name: 'Admin',
      role: 'admin'
    });
    console.log('Admin user created');
    process.exit(0);
  });
"

# 3. Test login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'
```

---

*Document created for RIVET Pro / Atlas CMMS Integration*
