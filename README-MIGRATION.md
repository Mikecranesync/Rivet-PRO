# Rivet-PRO Java/Spring Boot Migration

## Overview

This is a **Strangler Fig Pattern** migration from Python/FastAPI to Java/Spring Boot, following the Grashjs CMMS architecture specifications.

**Current Status**: Phase 1 Foundation Complete

### Architecture

- **Java Spring Boot 2.6.7** - New backend (port 8080)
- **Python FastAPI** - Legacy backend (port 8000)
- **Nginx** - Routes `/api/` to Java, `/api/v1/` to Python
- **PostgreSQL** - Shared database (Neon or local)
- **MinIO** - Object storage
- **Docker Compose** - Orchestrates all services

### Parallel System Design

```
┌──────────┐
│  Client  │
└────┬─────┘
     │
     v
┌────────────┐
│   Nginx    │ Port 80
│  (Router)  │
└─────┬──────┘
      │
      ├─────────────┐
      │             │
      v             v
┌──────────┐  ┌───────────┐
│  Java    │  │  Python   │
│  Spring  │  │  FastAPI  │
│  Boot    │  │           │
│ Port 8080│  │ Port 8000 │
└────┬─────┘  └─────┬─────┘
     │              │
     └──────┬───────┘
            v
    ┌──────────────┐
    │  PostgreSQL  │
    │   (Shared)   │
    └──────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Java 8+ (for local development)
- Maven 3.8+
- Git

### 1. Clone and Setup

```bash
cd /c/Users/hharp/OneDrive/Desktop/Rivet-PRO

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env  # or vim, code, etc.
```

### 2. Start All Services

```bash
# Build and start all containers
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

### 3. Verify Services

**Java API Health:**
```bash
curl http://localhost:8080/api/health
```

Expected response:
```json
{
  "status": "UP",
  "service": "Rivet CMMS API",
  "version": "1.0.0",
  "database": "UP",
  "databaseProductName": "PostgreSQL"
}
```

**Python API** (if still running):
```bash
curl http://localhost:8000/health
```

**Nginx Routing:**
```bash
# Routes to Java
curl http://localhost/api/health

# Routes to Python
curl http://localhost/api/v1/health
```

### 4. Access Swagger API Docs

Open in browser:
- **Java Swagger UI**: http://localhost:8080/swagger-ui.html
- **Direct API docs**: http://localhost:8080/v2/api-docs

## Database Migrations

The Java application uses **Liquibase** for database migrations.

### Baseline Strategy

The first changeset (`001-baseline-python-schema.xml`) mirrors all existing Python migrations (001-009). It uses `preConditions` to skip if tables already exist, ensuring:

- ✅ No data loss
- ✅ Existing schema recognized
- ✅ Future migrations apply cleanly

### Run Migrations

Migrations run automatically on application startup. To run manually:

```bash
# Inside Java container
docker exec -it rivet-java mvn liquibase:update

# Or locally
cd rivet-java
mvn liquibase:update
```

### Rollback (if needed)

```bash
# Rollback last N changesets
docker exec -it rivet-java mvn liquibase:rollback -Dliquibase.rollbackCount=5
```

## API Endpoints

### Authentication (Java - `/api/auth`)

```bash
# Register new user
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "name": "John Doe"
  }'

# Login
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'

# Telegram authentication (for bot)
curl -X POST http://localhost:8080/api/auth/telegram \
  -H "Content-Type: application/json" \
  -d '{
    "telegramUserId": 123456789,
    "username": "johndoe"
  }'
```

### Assets (Java - `/api/assets`)

```bash
# Get JWT token first (from login response)
TOKEN="your_jwt_token_here"

# Create asset
curl -X POST http://localhost:8080/api/assets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "manufacturer": "Siemens",
    "modelNumber": "G120C",
    "serialNumber": "12345",
    "location": "Building A",
    "criticality": "HIGH"
  }'

# Search assets
curl "http://localhost:8080/api/assets/search?q=Siemens" \
  -H "Authorization: Bearer $TOKEN"

# Match or create (fuzzy matching)
curl -X POST "http://localhost:8080/api/assets/match-or-create?manufacturer=Siemens&modelNumber=G120C&serialNumber=12345" \
  -H "Authorization: Bearer $TOKEN"
```

### Work Orders (Java - `/api/work-orders`)

```bash
# Create work order
curl -X POST http://localhost:8080/api/work-orders \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "equipmentId": "uuid-of-equipment",
    "title": "Motor overheating",
    "description": "Motor running hot, needs inspection",
    "priority": "HIGH",
    "faultCodes": ["F001", "F002"]
  }'

# Get work orders by status
curl "http://localhost:8080/api/work-orders/status/OPEN" \
  -H "Authorization: Bearer $TOKEN"

# Update work order status
curl -X PATCH "http://localhost:8080/api/work-orders/{id}/status?status=IN_PROGRESS" \
  -H "Authorization: Bearer $TOKEN"
```

## Development

### Local Java Development (without Docker)

```bash
cd rivet-java

# Build
mvn clean package

# Run locally (requires PostgreSQL)
export DATABASE_URL="postgresql://localhost:5432/rivet"
export DB_USER="postgres"
export DB_PASSWORD="postgres"
export JWT_SECRET_KEY="your_secret_key_here"

java -jar target/rivet-cmms-1.0.0-SNAPSHOT.jar
```

### Rebuild After Code Changes

```bash
# Rebuild Java container only
docker-compose build rivet-java
docker-compose up -d rivet-java

# Or rebuild all
docker-compose up --build
```

## Telegram Bot Integration

The Python Telegram bot can be updated to call the Java API:

**Before** (calls Python services directly):
```python
from rivet_pro.core.services.equipment_service import EquipmentService
asset = equipment_service.create(...)
```

**After** (calls Java REST API):
```python
import httpx

async def create_equipment_from_ocr(ocr_result, telegram_user_id):
    # Get JWT token
    token = await authenticate_telegram_user(telegram_user_id)

    # Call Java API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://rivet-java:8080/api/assets",
            json={
                "manufacturer": ocr_result.manufacturer,
                "modelNumber": ocr_result.model,
                "serialNumber": ocr_result.serial
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
```

## Rollback Strategy

If issues arise at any point:

### 1. Nginx Rollback (instant)

Edit `nginx/nginx.conf` to route all traffic to Python:

```nginx
location /api/ {
    proxy_pass http://python_backend;  # Change from java_backend
}
```

Reload:
```bash
docker-compose restart nginx
```

### 2. Database Rollback

```bash
# Rollback last 10 changesets
docker exec -it rivet-java mvn liquibase:rollback -Dliquibase.rollbackCount=10
```

### 3. Full Rollback

```bash
# Stop Java services
docker-compose stop rivet-java nginx

# Restart Python only
docker-compose up -d rivet-python
```

## Production Deployment (VPS)

### 1. Copy Files to VPS

```bash
scp -r rivet-java docker-compose.yml nginx .env root@72.60.175.144:/opt/rivet-pro/
```

### 2. Deploy on VPS

```bash
ssh root@72.60.175.144

cd /opt/rivet-pro

# Pull latest code
git pull origin main

# Update environment
nano .env

# Build and start
docker-compose up -d --build

# Check logs
docker-compose logs -f rivet-java
```

### 3. Monitor

```bash
# Check service health
curl http://localhost/api/health

# Check logs
docker-compose logs -f

# Check specific service
docker-compose logs -f rivet-java
```

## Troubleshooting

### Java Service Won't Start

```bash
# Check logs
docker-compose logs rivet-java

# Common issues:
# 1. Database connection - verify DATABASE_URL in .env
# 2. Liquibase migration failed - check migration logs
# 3. Port conflict - ensure 8080 is available
```

### Database Connection Issues

```bash
# Test PostgreSQL connectivity
docker exec -it rivet-postgres psql -U postgres -d rivet

# Verify tables exist
\dt

# Check Liquibase changesets
SELECT * FROM databasechangelog ORDER BY dateexecuted DESC LIMIT 10;
```

### Nginx Routing Issues

```bash
# Test backends directly
curl http://localhost:8080/api/health  # Java
curl http://localhost:8000/health      # Python

# Check Nginx logs
docker-compose logs nginx

# Verify nginx config
docker exec -it rivet-nginx nginx -t
```

## Next Steps (Roadmap)

### Phase 2: Preventive Maintenance (Weeks 3-4)
- [ ] Quartz scheduler configuration
- [ ] PreventiveMaintenance entity
- [ ] PM schedules auto-generate work orders
- [ ] Meter-based triggers

### Phase 3: Parts & Inventory (Weeks 5-6)
- [ ] Parts entity and repository
- [ ] Inventory tracking
- [ ] Purchase order management
- [ ] Parts consumption in work orders

### Phase 4: Telegram Bot Migration (Weeks 7-8)
- [ ] Update Python bot to call Java API
- [ ] Implement Telegram auth endpoint
- [ ] Test OCR → Java workflow

### Phase 5: React Frontend (Weeks 9-10)
- [ ] Clone/adapt Grashjs React UI
- [ ] Connect to Java API
- [ ] Dual interface: Web + Telegram

### Phase 6: Complete Migration (Weeks 11-12)
- [ ] Implement all 59+ Grashjs controllers
- [ ] Deprecate Python backend
- [ ] Production deployment

## Resources

- **Grashjs Repository**: https://github.com/Grashjs/cmms
- **Spring Boot Docs**: https://docs.spring.io/spring-boot/docs/2.6.7/reference/html/
- **Liquibase Docs**: https://docs.liquibase.com/
- **Migration Plan**: See `.claude/plans/jiggly-brewing-nest.md`

## Support

For issues or questions:
1. Check `docker-compose logs -f`
2. Review Swagger UI at http://localhost:8080/swagger-ui.html
3. Consult migration plan in `.claude/plans/`
