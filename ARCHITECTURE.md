# Rivet-PRO Architecture Documentation

## System Overview

Rivet-PRO is a CMMS (Computerized Maintenance Management System) with Telegram bot integration, providing equipment tracking, work order management, and AI-powered troubleshooting through a conversational interface.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACES                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  📱 Telegram Bot          🌐 Web UI          🔧 n8n          │
│  (Port: Polling)      (Port: 3001)      (Port: 5678)        │
│                                                               │
└──────────────┬───────────────┬────────────────┬─────────────┘
               │               │                │
               │               │                │
               ▼               ▼                ▼
┌──────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                           │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  🤖 Telegram Bot          🖥️  CMMS Backend                   │
│  (bot_launcher.py)        (Spring Boot)                       │
│  - Photo OCR              - REST API                          │
│  - Command handlers       - Business logic                    │
│  - Equipment queries      - JWT auth                          │
│  - Work order CRUD        - File uploads                      │
│  Port: N/A                Port: 8081                          │
│                                                                │
└────────────────┬───────────────────────┬──────────────────────┘
                 │                       │
                 │                       │
                 ▼                       ▼
┌──────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                 │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  🗄️  PostgreSQL           📦 MinIO Storage                   │
│  (Database)               (S3-compatible)                     │
│  - Equipment registry     - Equipment photos                  │
│  - Work orders            - Manual PDFs                       │
│  - Users/auth             - Attachments                       │
│  - Knowledge base         - Backups                           │
│  Port: 5435               Ports: 9000, 9001                   │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

---

## Infrastructure Components

### 1. Grashjs CMMS (Core System)

**Location:** `C:\Users\hharp\OneDrive\Desktop\grashjs-cmms\`

**Docker Containers:**

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| atlas_db | postgres:16-alpine | 5435:5432 | PostgreSQL database |
| atlas-cmms-backend | intelloop/atlas-cmms-backend | 8081:8080 | Spring Boot API |
| atlas-cmms-frontend | intelloop/atlas-cmms-frontend | 3001:3000 | React web UI |
| atlas_minio | minio/minio | 9000-9001 | Object storage |

**Key Services:**

**PostgreSQL (atlas_db)**
- Database: `atlas`
- User: `rivet_admin`
- Password: `rivet_secure_password_2026`
- Tables: 100+ (Equipment, WorkOrder, User, Part, Location, etc.)
- Migrations: Managed by Liquibase (173+ changesets)

**CMMS Backend (atlas-cmms-backend)**
- Framework: Spring Boot 2.6.7 + Java 8
- API: REST (OpenAPI/Swagger)
- Auth: JWT tokens
- Health: `/actuator/health`
- Features:
  - Multi-tenant support
  - RBAC (Role-based access control)
  - File uploads (via MinIO)
  - Custom fields
  - Preventive maintenance scheduling
  - Parts inventory
  - Vendor management

**CMMS Frontend (atlas-cmms-frontend)**
- Framework: React 18 + TypeScript
- UI Library: Material-UI
- Features:
  - Asset management
  - Work order tracking
  - Calendar/scheduling
  - Analytics/reports
  - User management

**MinIO (atlas_minio)**
- Bucket: `atlas-bucket`
- User: `minio`
- Password: `minio_secure_password_2026`
- Console: http://localhost:9001
- Stores: Photos, PDFs, attachments

---

### 2. Telegram Bot

**Location:** `C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\`

**Main Files:**
- `bot_launcher.py` - Startup script with validation
- `cmms_bot.py` - Bot implementation
- `integrations/grashjs_client.py` - CMMS API client (~500 lines)

**Bot Configuration:**
```python
BOT_TOKEN = "7855741814:AAFHIk0vPmG9ZHACISMl-izzDwdS0bk_nYo"
ADMIN_TELEGRAM_ID = 8445149012
CMMS_EMAIL = "mike@cranesync.com"
CMMS_PASSWORD = "Bo1ws2er@12"
CMMS_API_URL = "http://localhost:8081"
```

**Bot Commands:**
- `/start` - Show main menu
- `/help` - Help message
- `/status` - CMMS connection status

**Bot Features (via inline buttons):**
- 📦 View Assets - List all equipment
- 🔧 Work Orders - List work orders
- ➕ Create Asset - Link to web UI
- ➕ Create WO - Create work order
- 📊 CMMS Status - Connection diagnostics

**API Integration:**
Bot → `grashjs_client.py` → CMMS API (HTTP/JSON)

All CRUD operations use the GrashjsClient wrapper class:
```python
from grashjs_client import GrashjsClient

cmms = GrashjsClient('http://localhost:8081')
cmms.login(email, password)
assets = cmms.get_assets()
wo = cmms.create_work_order(title, description, priority)
```

---

### 3. n8n Orchestration

**Port:** 5678 (http://localhost:5678)

**Workflows:**

**Rivet-PRO Startup Orchestrator** (17 nodes)
- Manual trigger
- Docker health check
- CMMS container management
- API health polling (30 attempts × 5s = 2.5min max)
- Login validation
- Bot process management
- Telegram notifications (success/failure)

**Node Types Used:**
- Manual Trigger - User-initiated
- Code Node (JavaScript) - Variable init, message formatting
- Execute Command - Docker commands, bot startup
- HTTP Request - Health checks, CMMS login, Telegram API
- IF Node - Conditional branching (success/error paths)
- Wait Node - Delays for service initialization

**Credentials Required:**
- N8N_API_KEY (in .env)
- Telegram bot token (in workflow variables)
- CMMS credentials (in workflow variables)

---

## Dependency Graph

```
Startup Sequence (Critical Path):

1. Docker Desktop
   └─> Running and responsive

2. PostgreSQL (atlas_db)
   └─> Health check: pg_isready
   └─> Database 'atlas' initialized
   └─> Liquibase migrations complete

3. MinIO (atlas_minio)
   └─> Health check: HTTP 200 on /minio/health/live
   └─> Bucket 'atlas-bucket' created

4. CMMS Backend (atlas-cmms-backend)
   └─> Depends on: PostgreSQL, MinIO
   └─> Health check: /actuator/health → {"status":"UP"}
   └─> Ready when: HTTP 200 or 403

5. CMMS Frontend (atlas-cmms-frontend)
   └─> Depends on: CMMS Backend
   └─> Health check: HTTP 200 on port 3001

6. Telegram Bot
   └─> Depends on: CMMS Backend (must respond)
   └─> Auth: Must login with valid credentials
   └─> Telegram API: Must connect successfully
   └─> Ready when: Polling starts, sends /getMe successfully
```

**Total startup time:** 30-60 seconds (from containers down to bot ready)

---

## Port Allocation

| Port | Service | Protocol | Purpose | Required |
|------|---------|----------|---------|----------|
| 3001 | CMMS Frontend | HTTP | Web UI | ✅ Yes |
| 5435 | PostgreSQL | TCP | Database | ✅ Yes |
| 5678 | n8n | HTTP | Workflow automation | ⚠️ Optional |
| 8081 | CMMS Backend | HTTP | REST API | ✅ Yes |
| 9000 | MinIO API | HTTP | Object storage | ✅ Yes |
| 9001 | MinIO Console | HTTP | Storage UI | ⚠️ Optional |

**Port Conflicts:**
If any port is already in use, Docker won't start the container. Check with:
```bash
netstat -ano | findstr :8081
```

---

## Data Flow

### Telegram Message → Equipment Lookup

```
1. User sends message in Telegram
   └─> Telegram API delivers to bot via polling

2. Bot receives update
   └─> Parses command/button callback
   └─> Routes to appropriate handler

3. Handler calls CMMS API
   └─> GrashjsClient.get_assets(search=query)
   └─> HTTP GET /api/assets?search=query

4. CMMS Backend processes request
   └─> Queries PostgreSQL
   └─> Applies filters, pagination
   └─> Returns JSON response

5. Bot formats response
   └─> Creates message with inline buttons
   └─> Sends via Telegram API

6. User sees formatted asset list
```

### Work Order Creation Flow

```
1. User clicks "Create WO" button
   └─> Callback query to bot

2. Bot creates work order
   └─> GrashjsClient.create_work_order(title, description, priority)
   └─> HTTP POST /api/work-orders
   └─> Body: {"title": "...", "description": "...", "priority": "MEDIUM"}

3. CMMS Backend creates WO
   └─> INSERT INTO work_order (...)
   └─> Returns work order JSON with ID

4. Bot sends confirmation
   └─> Message: "Work order #123 created!"
   └─> Button: "View in Web UI" → http://localhost:3001/app/work-orders/123

5. User can view in either:
   - Telegram (summary)
   - Web UI (full details)
```

---

## Database Schema

### Key Tables

**equipment (Assets)**
```sql
id              BIGSERIAL PRIMARY KEY
name            VARCHAR(255) NOT NULL
description     TEXT
model           VARCHAR(255)
serial_number   VARCHAR(255)
barcode         VARCHAR(255)
qr_code         VARCHAR(255)
category_id     BIGINT REFERENCES categories(id)
location_id     BIGINT REFERENCES locations(id)
assigned_to_id  BIGINT REFERENCES users(id)
warranty_date   DATE
acquisition_cost DECIMAL
status          VARCHAR(50)  -- OPERATIONAL, DOWN, MAINTENANCE, etc.
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

**work_order**
```sql
id               BIGSERIAL PRIMARY KEY
title            VARCHAR(255) NOT NULL
description      TEXT
priority         VARCHAR(50)  -- LOW, MEDIUM, HIGH, CRITICAL
status           VARCHAR(50)  -- OPEN, IN_PROGRESS, ON_HOLD, COMPLETE
asset_id         BIGINT REFERENCES equipment(id)
assigned_to_id   BIGINT REFERENCES users(id)
location_id      BIGINT REFERENCES locations(id)
category_id      BIGINT REFERENCES categories(id)
due_date         TIMESTAMP
completed_on     TIMESTAMP
estimated_duration INTEGER  -- minutes
actual_duration  INTEGER  -- minutes
created_at       TIMESTAMP
updated_at       TIMESTAMP
```

**users (Authentication)**
```sql
id              BIGSERIAL PRIMARY KEY
email           VARCHAR(255) UNIQUE NOT NULL
first_name      VARCHAR(255)
last_name       VARCHAR(255)
phone           VARCHAR(255)
role            VARCHAR(50)  -- ADMIN, LIMITED_ADMIN, TECHNICIAN, etc.
rate            DECIMAL
org_id          BIGINT REFERENCES organizations(id)
enabled         BOOLEAN DEFAULT TRUE
created_at      TIMESTAMP
```

**Total tables:** 100+ (includes parts, inventory, vendors, customers, files, custom fields, notifications, etc.)

---

## Health Check Endpoints

### CMMS Backend
```bash
GET http://localhost:8081/actuator/health

Response (healthy):
{
  "status": "UP"
}

Response (starting/unhealthy):
HTTP 503 or no response
```

### PostgreSQL
```bash
docker exec atlas_db pg_isready -U rivet_admin -d atlas

Response (healthy):
/var/run/postgresql:5432 - accepting connections
```

### MinIO
```bash
GET http://localhost:9000/minio/health/live

Response (healthy):
HTTP 200 OK
```

### Telegram Bot
```bash
GET https://api.telegram.org/bot{TOKEN}/getMe

Response (healthy):
{
  "ok": true,
  "result": {
    "id": 7855741814,
    "is_bot": true,
    "first_name": "Rivet CMMS Bot",
    ...
  }
}
```

---

## Credentials & Secrets

### Storage Locations

1. **Main .env file:**
   - Location: `C:\Users\hharp\OneDrive\Desktop\Rivet-PRO\.env`
   - Contains: All API keys, tokens, database URLs
   - **NOT** committed to git (in .gitignore)

2. **CMMS .env file:**
   - Location: `C:\Users\hharp\OneDrive\Desktop\grashjs-cmms\.env`
   - Contains: CMMS-specific config (DB, MinIO, JWT secret)

3. **Bot configuration:**
   - Hardcoded in: `cmms_bot.py`, `bot_launcher.py`
   - Source: Read from main .env or hardcoded

### Credential Reference

| Credential | Value | Where Used |
|------------|-------|------------|
| CMMS Email | mike@cranesync.com | Bot login, n8n workflow |
| CMMS Password | Bo1ws2er@12 | Bot login, n8n workflow |
| Telegram Bot Token | 7855741814:AAGF... | Bot, n8n workflow |
| Telegram Admin Chat ID | 8445149012 | n8n notifications |
| PostgreSQL User | rivet_admin | CMMS backend, direct DB access |
| PostgreSQL Password | rivet_secure_password_2026 | CMMS backend |
| MinIO User | minio | CMMS backend |
| MinIO Password | minio_secure_password_2026 | CMMS backend, MinIO console |
| JWT Secret | rivet_pro_jwt_secret... | CMMS backend (token signing) |

---

## Security Considerations

### Current Setup (Development)

⚠️ **Not production-ready** - Current configuration is for local development only.

**Issues:**
- Default/weak passwords (change these!)
- Credentials hardcoded in scripts
- No HTTPS/SSL
- No firewall rules
- JWT secret should be regenerated
- MinIO uses default credentials
- No rate limiting
- No input validation in bot

### Production Recommendations

1. **Change all passwords** to strong, random values
2. **Use environment variables** for all secrets (no hardcoding)
3. **Enable HTTPS** with Let's Encrypt
4. **Set up firewall** rules (only expose 443, block others)
5. **Regenerate JWT secret** with strong random value
6. **Enable CORS** properly (restrict origins)
7. **Add rate limiting** on API endpoints
8. **Implement input validation** in bot commands
9. **Set up backups** (automated PostgreSQL dumps)
10. **Enable audit logging** for all CRUD operations
11. **Use Docker secrets** instead of .env for sensitive data
12. **Implement API key rotation** policy

---

## Deployment Options

### Option 1: Local Development (Current)

**Pros:**
- Easy to debug
- Fast iteration
- No internet required (except Telegram API)

**Cons:**
- Must keep PC running
- Not accessible remotely
- No automatic restart on failure

**Use for:** Development, testing, demos

---

### Option 2: VPS Deployment (Recommended for Production)

**Target:** 72.60.175.144

**Pros:**
- 24/7 availability
- Accessible anywhere
- Automatic restart (systemd)
- Better for team use

**Cons:**
- Requires server setup
- Need to manage security
- Monthly hosting cost

**Deployment Steps:**

1. **Upload CMMS:**
   ```bash
   scp -r grashjs-cmms/ root@72.60.175.144:/opt/
   ```

2. **Upload Bot:**
   ```bash
   scp -r Rivet-PRO/ root@72.60.175.144:/opt/
   ```

3. **SSH and setup:**
   ```bash
   ssh root@72.60.175.144
   cd /opt/grashjs-cmms
   docker-compose up -d

   cd /opt/Rivet-PRO
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Create systemd service:**
   ```bash
   sudo nano /etc/systemd/system/rivet-bot.service
   ```

   ```ini
   [Unit]
   Description=Rivet-PRO Telegram Bot
   After=network.target docker.service
   Requires=docker.service

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/opt/Rivet-PRO
   ExecStart=/opt/Rivet-PRO/venv/bin/python bot_launcher.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

5. **Enable and start:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable rivet-bot
   sudo systemctl start rivet-bot
   sudo systemctl status rivet-bot
   ```

6. **Configure nginx** (reverse proxy for web UI):
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:3001;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }

       location /api {
           proxy_pass http://localhost:8081;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

7. **Enable HTTPS** with Let's Encrypt:
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

---

## Monitoring & Logging

### Docker Logs
```bash
# All containers
cd C:\Users\hharp\OneDrive\Desktop\grashjs-cmms
docker-compose logs -f

# Specific service
docker-compose logs -f atlas-cmms-backend

# Last 100 lines
docker-compose logs --tail=100 atlas-cmms-backend
```

### Bot Logs
The bot outputs all logs to stdout. When running via START_RIVET.bat, you see them in the terminal window.

For production (systemd):
```bash
sudo journalctl -u rivet-bot -f
```

### Database Queries
```bash
docker exec -it atlas_db psql -U rivet_admin -d atlas

# Example queries
SELECT COUNT(*) FROM work_order WHERE status = 'OPEN';
SELECT name, model, status FROM equipment LIMIT 10;
```

### Health Monitoring
```bash
# Check all services
curl http://localhost:8081/actuator/health
curl http://localhost:3001
curl http://localhost:9000/minio/health/live
curl https://api.telegram.org/bot{TOKEN}/getMe
```

---

## Backup & Recovery

### Database Backup
```bash
# Dump database
docker exec atlas_db pg_dump -U rivet_admin atlas > backup_$(date +%Y%m%d).sql

# Restore database
docker exec -i atlas_db psql -U rivet_admin atlas < backup_20260106.sql
```

### MinIO Backup
```bash
# Using mc (MinIO client)
mc alias set local http://localhost:9000 minio minio_secure_password_2026
mc mirror local/atlas-bucket ./minio-backup/
```

### Full System Backup
```bash
# Backup everything
cd C:\Users\hharp\OneDrive\Desktop\grashjs-cmms
docker-compose down
tar -czf rivet-backup-$(date +%Y%m%d).tar.gz \
    grashjs-cmms/ \
    Rivet-PRO/ \
    --exclude='node_modules' \
    --exclude='venv' \
    --exclude='__pycache__'
docker-compose up -d
```

---

## Performance Tuning

### PostgreSQL
```sql
-- Increase shared_buffers (in postgresql.conf)
shared_buffers = 256MB

-- Increase work_mem
work_mem = 16MB

-- Create indexes
CREATE INDEX idx_work_order_status ON work_order(status);
CREATE INDEX idx_equipment_name ON equipment(name);
CREATE INDEX idx_work_order_asset ON work_order(asset_id);
```

### Docker Resource Limits
```yaml
# In docker-compose.yml
services:
  atlas-cmms-backend:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
```

### Bot Performance
- Use connection pooling for CMMS API calls
- Cache frequently accessed data (assets list, etc.)
- Implement request throttling (max 30 req/sec to Telegram API)

---

## Future Enhancements

1. **OCR Integration**
   - Photo → Gemini Vision → Equipment data extraction
   - Auto-create equipment from nameplate photos

2. **Knowledge Base**
   - Store manuals, troubleshooting guides
   - AI-powered search and recommendations

3. **Advanced Analytics**
   - Equipment uptime tracking
   - Work order completion metrics
   - Cost analysis

4. **Mobile App**
   - Native iOS/Android app
   - Offline mode
   - Push notifications

5. **Multi-tenancy**
   - Support multiple organizations
   - Role-based access control
   - Data isolation

6. **Integrations**
   - SAP/ERP integration
   - IoT sensor data
   - Third-party parts catalogs

---

## Glossary

- **CMMS:** Computerized Maintenance Management System
- **WO:** Work Order
- **PM:** Preventive Maintenance
- **Asset:** Equipment, machinery, or facility being maintained
- **JWT:** JSON Web Token (authentication)
- **MinIO:** S3-compatible object storage
- **n8n:** Workflow automation tool
- **Polling:** Bot checks Telegram API for new messages (vs webhook)
- **Webhook:** Telegram pushes new messages to bot URL
- **OCR:** Optical Character Recognition (reading text from images)

---

## Version History

- **v1.0.0** (2026-01-06) - Initial one-click startup implementation
  - Desktop launcher (START_RIVET.bat)
  - Bot credentials configured (mike@cranesync.com)
  - n8n orchestration workflow
  - Complete documentation

---

For operational guide, see [STARTUP_GUIDE.md](./STARTUP_GUIDE.md)
