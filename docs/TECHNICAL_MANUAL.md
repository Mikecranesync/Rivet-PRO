# RIVET Pro Technical Manual

**Version**: 1.0
**Last Updated**: 2026-01-17
**Audience**: Operators and Developers

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Service Layer API Documentation](#2-service-layer-api-documentation)
3. [Database Schema](#3-database-schema)
4. [Deployment Checklist](#4-deployment-checklist)
5. [Troubleshooting Guide](#5-troubleshooting-guide)
6. [Local Development Setup](#6-local-development-setup)
7. [Monitoring & Alerting](#7-monitoring--alerting)

---

## 1. Architecture Overview

### 1.1 Photo Pipeline Architecture

RIVET Pro uses a three-stage AI pipeline orchestrated by Ralph for photo analysis:

```
                           +------------------+
                           |  Field Technician |
                           |  (Telegram App)   |
                           +--------+---------+
                                    |
                                    | Photo Upload
                                    v
+----------------------------------------------------------------------+
|                        RIVET Pro Telegram Bot                        |
|  rivet_pro/adapters/telegram/bot.py                                  |
+----------------------------------------------------------------------+
                                    |
                                    v
+----------------------------------------------------------------------+
|  STAGE 1: Groq Industrial Screening                                  |
|  +-----------------------------------------------------------------+ |
|  | Model: meta-llama/llama-4-scout-17b-16e-instruct                | |
|  | Cost: ~$0.001/image | Target Latency: <2s                       | |
|  | Purpose: Fast filter - is this industrial equipment?            | |
|  | Threshold: >= 80% confidence to proceed                         | |
|  | Service: rivet_pro/core/services/screening_service.py           | |
|  +-----------------------------------------------------------------+ |
+----------------------------------------------------------------------+
           |                                     |
           | Passes (>=80%)                      | Rejects (<80%)
           v                                     v
+-------------------------------+      +------------------------+
|  Cache Check (SHA256 hash)   |      |  Rejection Message     |
|  Table: photo_analysis_cache |      |  (food, pets, docs...)  |
+-------------------------------+      +------------------------+
           |
           | Cache Miss
           v
+----------------------------------------------------------------------+
|  STAGE 2: DeepSeek Specification Extraction                          |
|  +-----------------------------------------------------------------+ |
|  | Model: deepseek-chat                                            | |
|  | Cost: ~$0.002/image | Target Latency: <3s                       | |
|  | Purpose: Extract manufacturer, model, serial, specs             | |
|  | Service: rivet_pro/core/services/extraction_service.py          | |
|  +-----------------------------------------------------------------+ |
+----------------------------------------------------------------------+
                                    |
                                    v
+----------------------------------------------------------------------+
|  Equipment Matching                                                  |
|  +-----------------------------------------------------------------+ |
|  | Searches: cmms_equipment table by manufacturer + model          | |
|  | Creates: New equipment record if no match found                 | |
|  | Returns: equipment_id, equipment_number, is_new flag            | |
|  | Service: rivet_pro/core/services/equipment_service.py           | |
|  +-----------------------------------------------------------------+ |
+----------------------------------------------------------------------+
                                    |
                                    v
+----------------------------------------------------------------------+
|  STAGE 3: Claude AI Analysis & KB Synthesis                          |
|  +-----------------------------------------------------------------+ |
|  | Model: claude-sonnet-4-20250514                                 | |
|  | Cost: ~$0.01/analysis | Prerequisites: equipment_id + KB atoms  | |
|  | Purpose: Synthesize specs + history + KB into guidance          | |
|  | Output: Solutions, safety warnings, citations                   | |
|  | Service: rivet_pro/core/services/claude_analyzer.py             | |
|  +-----------------------------------------------------------------+ |
+----------------------------------------------------------------------+
                                    |
                                    v
+----------------------------------------------------------------------+
|  Response Formatter                                                  |
|  PhotoPipelineService._format_pipeline_response()                   |
|  Returns: Formatted HTML for Telegram                               |
+----------------------------------------------------------------------+
```

### 1.2 Data Flow Summary

| Stage | Provider | Model | Cost | Latency Target | When Skipped |
|-------|----------|-------|------|----------------|--------------|
| 1 | Groq | llama-4-scout-17b | ~$0.001 | <2s | Never |
| 2 | DeepSeek | deepseek-chat | ~$0.002 | <3s | Groq <80% or cache hit |
| 3 | Anthropic | claude-sonnet-4 | ~$0.01 | <4s | No equipment or no KB |

### 1.3 Ralph Orchestration

Ralph is the autonomous development agent that manages feature implementation:

```
+------------------+     +------------------+     +------------------+
| Ralph Stories    |---->| Claude Code      |---->| Git Commits      |
| (ralph_stories)  |     | Implementation   |     | Status Updates   |
+------------------+     +------------------+     +------------------+
       ^                                                   |
       |                                                   |
       +---------------------------------------------------+
                    Continuous Loop
```

**Ralph workflow:**
1. Query `ralph_stories` table for `status = 'todo'` ordered by priority
2. Mark story `in_progress`
3. Implement feature following acceptance criteria
4. Run tests, commit changes
5. Mark `done` or `failed`
6. Loop to next story

---

## 2. Service Layer API Documentation

### 2.1 PhotoPipelineService

**Location**: `rivet_pro/core/services/photo_pipeline_service.py`

#### `process_photo()`

Main entry point for photo analysis pipeline.

**Signature:**
```python
async def process_photo(
    self,
    image_bytes: bytes,
    user_id: str,
    telegram_user_id: int,
    equipment_id: Optional[UUID] = None,
    trace=None
) -> PhotoPipelineResult
```

**Inputs:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `image_bytes` | `bytes` | Yes | Raw photo bytes from Telegram |
| `user_id` | `str` | Yes | User identifier (e.g., "telegram_123") |
| `telegram_user_id` | `int` | Yes | Telegram user ID for context |
| `equipment_id` | `UUID` | No | Pre-matched equipment UUID |
| `trace` | object | No | Trace object for observability |

**Output:** `PhotoPipelineResult`

```python
@dataclass
class PhotoPipelineResult:
    screening: Optional[ScreeningResult]      # Stage 1 result
    extraction: Optional[ExtractionResult]    # Stage 2 result
    analysis: Optional[AnalysisResult]        # Stage 3 result
    total_cost_usd: float                     # Combined cost
    total_time_ms: int                        # Combined processing time
    formatted_response: str                   # User-friendly HTML
    equipment_id: Optional[UUID]              # Matched/created equipment
    equipment_number: Optional[str]           # Equipment number
    is_new_equipment: bool                    # True if just created
    from_cache: bool                          # True if from cache
    stages: List[PipelineStageResult]         # Stage details
    error: Optional[str]                      # Error message if failed
    rejected: bool                            # True if non-industrial
    rejection_message: Optional[str]          # User-friendly rejection
```

**Error Codes:**
| Code | Description | Recovery |
|------|-------------|----------|
| `SCREENING_FAILED` | Groq API error | Retry with backoff |
| `EXTRACTION_FAILED` | DeepSeek API error | Skip to equipment matching |
| `ANALYSIS_SKIPPED` | No KB context found | Return Stage 2 results |
| `INVALID_IMAGE` | Base64 decode failed | Request new photo |

---

### 2.2 ScreeningService

**Location**: `rivet_pro/core/services/screening_service.py`

#### `screen_industrial_photo()`

First-pass Groq screening to determine if photo is industrial equipment.

**Signature:**
```python
async def screen_industrial_photo(base64_image: str) -> ScreeningResult
```

**Input:** Base64-encoded image (no `data:` prefix)

**Output:** `ScreeningResult`

```python
@dataclass
class ScreeningResult:
    is_industrial: bool          # True if industrial equipment detected
    confidence: float            # 0.0-1.0 confidence score
    category: Optional[str]      # plc, vfd, motor, pump, control_panel, sensor, other
    reason: str                  # Brief explanation
    rejection_message: Optional[str]  # User-friendly rejection (if not industrial)
    passes_threshold: bool       # True if confidence >= 0.80
    processing_time_ms: int      # API call duration
    cost_usd: float              # ~$0.001
    model_used: str              # Model identifier
    error: Optional[str]         # Error message if failed
```

**Categories:**
| Category | Description | Examples |
|----------|-------------|----------|
| `plc` | Programmable Logic Controllers | Siemens S7, Allen-Bradley |
| `vfd` | Variable Frequency Drives | G120C, PowerFlex |
| `motor` | Electric Motors | Baldor, WEG |
| `pump` | Industrial Pumps | Grundfos, Flygt |
| `control_panel` | Control Panels/Switchgear | MCC, enclosures |
| `sensor` | Sensors and Transducers | Proximity, temp |
| `other` | Other industrial equipment | - |

---

### 2.3 ExtractionService

**Location**: `rivet_pro/core/services/extraction_service.py`

#### `extract_component_specs()`

DeepSeek extraction of manufacturer, model, serial, and specs.

**Signature:**
```python
async def extract_component_specs(
    base64_image: str,
    screening: ScreeningResult,
    db=None,
) -> ExtractionResult
```

**Output:** `ExtractionResult`

```python
@dataclass
class ExtractionResult:
    manufacturer: Optional[str]    # Exact manufacturer name
    model_number: Optional[str]    # Exact model/part number
    serial_number: Optional[str]   # Serial number if visible
    specs: Dict[str, Any]          # Technical specifications
    raw_text: str                  # All visible text from nameplate
    confidence: float              # 0.0-1.0 confidence
    processing_time_ms: int        # API call duration
    cost_usd: float                # ~$0.002
    model_used: str                # Model identifier
    from_cache: bool               # True if from cache
    has_model_info: bool           # True if manufacturer or model extracted
    error: Optional[str]           # Error message if failed
```

**Extracted Specifications:**
| Field | Description | Example |
|-------|-------------|---------|
| `voltage` | With unit | "480V", "230V" |
| `current` | With unit | "15A", "2.5A" |
| `horsepower` | With unit | "5HP", "0.5HP" |
| `rpm` | Revolutions per minute | "1750" |
| `phase` | 1 or 3 phase | "3" |
| `frequency` | With unit | "60Hz" |
| `frame` | Frame size | "145T" |
| `enclosure` | NEMA rating | "TEFC" |
| `ip_rating` | IP rating | "IP55" |
| `service_factor` | SF value | "1.15" |
| `efficiency` | Percentage or class | "95%" |
| `insulation_class` | Class letter | "F" |

---

### 2.4 ClaudeAnalyzer

**Location**: `rivet_pro/core/services/claude_analyzer.py`

#### `analyze_with_kb()`

Third-pass Claude analysis with knowledge base synthesis.

**Signature:**
```python
async def analyze_with_kb(
    self,
    equipment_id: UUID,
    specs: Dict[str, Any],
    history: List[Dict[str, Any]],
    kb_context: List[Dict[str, Any]]
) -> AnalysisResult
```

**Output:** `AnalysisResult`

```python
@dataclass
class AnalysisResult:
    analysis: str                          # Synthesized troubleshooting text
    solutions: List[str]                   # Prioritized solutions
    kb_citations: List[Dict[str, str]]     # Source citations with URLs
    recommendations: List[str]             # Actionable next steps
    confidence: float                      # 0.0-1.0 analysis confidence
    safety_warnings: List[str]             # Critical safety considerations
    cost_usd: float                        # ~$0.01
    model: str                             # "claude-sonnet-4-20250514"
```

---

### 2.5 Database Retry Logic

**Location**: `rivet_pro/infra/database.py`

All database operations use exponential backoff retry:

```python
# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [0.1, 0.5, 0.5]  # 100ms, 500ms, 500ms (capped)

# Retryable errors
RETRYABLE_ERRORS = (
    asyncpg.ConnectionDoesNotExistError,
    asyncpg.InterfaceError,
    asyncpg.TooManyConnectionsError,
    asyncpg.CannotConnectNowError,
    OSError,
)
```

**Retry behavior:**
- Attempt 1: Immediate
- Attempt 2: After 100ms
- Attempt 3: After 500ms
- Attempt 4: After 500ms (final)

**Non-retryable errors** (raise immediately):
- Syntax errors
- Unique constraint violations
- Foreign key violations
- Permission errors

---

## 3. Database Schema

### 3.1 Core Tables

#### `photo_analysis_cache`

Caches photo analysis results to avoid re-processing identical images.

```sql
CREATE TABLE photo_analysis_cache (
    id SERIAL PRIMARY KEY,
    photo_hash VARCHAR(64) NOT NULL UNIQUE,    -- SHA256 hash of image bytes
    screening_result JSONB DEFAULT '{}',       -- Groq screening result
    extraction_result JSONB DEFAULT '{}',      -- DeepSeek extraction result
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours'),
    access_count INTEGER NOT NULL DEFAULT 0    -- Cache hit tracking
);

-- Indexes
CREATE INDEX idx_photo_cache_hash ON photo_analysis_cache(photo_hash);
CREATE INDEX idx_photo_cache_expires ON photo_analysis_cache(expires_at);
```

#### `cmms_equipment`

Equipment registry populated by photo OCR.

```sql
CREATE TABLE cmms_equipment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_number VARCHAR(50) UNIQUE NOT NULL,  -- Auto: EQ-2026-000001
    equipment_model_id UUID REFERENCES equipment_models(id),
    manufacturer VARCHAR(255) NOT NULL,
    model_number VARCHAR(255),
    serial_number VARCHAR(255),
    equipment_type VARCHAR(100),
    location VARCHAR(500),
    department VARCHAR(255),
    criticality criticality_level DEFAULT 'medium',  -- low/medium/high/critical
    owned_by_user_id UUID REFERENCES users(id),
    work_order_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX idx_cmms_equipment_manufacturer ON cmms_equipment(manufacturer);
CREATE INDEX idx_cmms_equipment_model ON cmms_equipment(model_number);
CREATE INDEX idx_cmms_equipment_serial ON cmms_equipment(serial_number);
CREATE INDEX idx_cmms_equipment_location ON cmms_equipment(location);
CREATE INDEX idx_cmms_equipment_created ON cmms_equipment(created_at DESC);
CREATE INDEX idx_cmms_equipment_criticality ON cmms_equipment(criticality);
```

#### `knowledge_atoms`

Curated troubleshooting knowledge for AI synthesis.

```sql
CREATE TABLE knowledge_atoms (
    atom_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL,              -- fault, procedure, spec, part, tip, safety
    manufacturer VARCHAR(255),
    model VARCHAR(255),
    equipment_type VARCHAR(100),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    source_url VARCHAR(1000),
    confidence FLOAT NOT NULL DEFAULT 0.5,  -- 0.0-1.0
    human_verified BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,
    embedding vector(1536),                 -- OpenAI embedding for semantic search
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for search
CREATE INDEX idx_knowledge_atoms_type ON knowledge_atoms(type);
CREATE INDEX idx_knowledge_atoms_manufacturer ON knowledge_atoms(manufacturer);
CREATE INDEX idx_knowledge_atoms_confidence ON knowledge_atoms(confidence DESC);
CREATE INDEX idx_knowledge_atoms_embedding ON knowledge_atoms
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### 3.2 Entity Relationship Diagram

```
+------------------+     +------------------+     +------------------+
|      users       |     | cmms_equipment   |     | work_orders      |
+------------------+     +------------------+     +------------------+
| id (PK)          |<----| owned_by_user_id |     | id (PK)          |
| telegram_id      |     | id (PK)          |<----| equipment_id     |
| first_name       |     | equipment_number |     | work_order_number|
| tier             |     | manufacturer     |     | title            |
+------------------+     | model_number     |     | status           |
                         | serial_number    |     | created_by       |
                         +------------------+     +------------------+
                                  |
                                  v
                         +------------------+
                         | knowledge_atoms  |
                         +------------------+
                         | atom_id (PK)     |
                         | manufacturer     |
                         | model            |
                         | content          |
                         | confidence       |
                         +------------------+
```

---

## 4. Deployment Checklist

### 4.1 Required Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from @BotFather | `123456:ABC...` |
| `DATABASE_URL` | Yes | Neon PostgreSQL connection | `postgresql://...` |
| `GROQ_API_KEY` | Yes | Groq API for Stage 1 screening | `gsk_...` |
| `DEEPSEEK_API_KEY` | Yes | DeepSeek API for Stage 2 extraction | `sk-...` |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API for Stage 3 analysis | `sk-ant-...` |
| `JWT_SECRET_KEY` | Yes | JWT signing key (32+ chars) | `your-secret-key` |
| `LANGFUSE_PUBLIC_KEY` | No | Langfuse tracing (optional) | `pk-lf-...` |
| `LANGFUSE_SECRET_KEY` | No | Langfuse tracing (optional) | `sk-lf-...` |
| `SUPABASE_DB_URL` | No | Failover database | `postgresql://...` |

### 4.2 VPS Deployment Commands

```bash
# 1. SSH to VPS
ssh root@72.60.175.144

# 2. Pull latest code
cd /opt/Rivet-PRO
git fetch origin
git checkout main
git pull

# 3. Update environment (if needed)
nano .env

# 4. Restart bot service
systemctl restart rivet-bot

# 5. Verify deployment
systemctl status rivet-bot
journalctl -u rivet-bot -n 50 --no-pager
```

### 4.3 Pre-Deployment Verification

```bash
# Check all required env vars are set
cat .env | grep -E "TELEGRAM_BOT_TOKEN|DATABASE_URL|GROQ_API_KEY|DEEPSEEK_API_KEY|ANTHROPIC_API_KEY"

# Test database connection
PGPASSWORD='...' psql $DATABASE_URL -c "SELECT 1"

# Run migrations (if any pending)
python -c "from rivet_pro.infra.database import db; import asyncio; asyncio.run(db.run_migrations())"

# Run tests
pytest tests/ -v
```

### 4.4 systemd Service Configuration

**File:** `/etc/systemd/system/rivet-bot.service`

```ini
[Unit]
Description=RIVET Pro Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/Rivet-PRO
EnvironmentFile=/opt/Rivet-PRO/.env
ExecStart=/usr/bin/python3 -m rivet_pro.adapters.telegram
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

---

## 5. Troubleshooting Guide

### 5.1 API Timeouts

#### Groq Timeout (Stage 1)

**Symptoms:**
- Photo analysis hangs for >5 seconds
- Logs show: `Screening failed: ReadTimeout`

**Resolution:**
1. Check Groq status: https://status.groq.com
2. Verify API key is valid:
   ```bash
   curl -H "Authorization: Bearer $GROQ_API_KEY" https://api.groq.com/openai/v1/models
   ```
3. If persistent, check rate limits (30 req/min default)

#### DeepSeek Timeout (Stage 2)

**Symptoms:**
- Extraction takes >5 seconds
- Logs show: `Extraction failed: Connection timeout`

**Resolution:**
1. Check DeepSeek API status
2. DeepSeek has 60 req/min limit
3. Verify API key:
   ```bash
   curl -H "Authorization: Bearer $DEEPSEEK_API_KEY" https://api.deepseek.com/v1/models
   ```

#### Claude Timeout (Stage 3)

**Symptoms:**
- Analysis takes >10 seconds
- Logs show: `Claude analysis failed: APITimeoutError`

**Resolution:**
1. Check Anthropic status: https://status.anthropic.com
2. Verify API key and credits
3. Stage 3 failure returns Stage 2 results automatically (graceful degradation)

### 5.2 Cache Invalidation

**When to invalidate:**
- Model accuracy improvements deployed
- Prompt changes in screening/extraction
- Bug fixes in parsing logic

**How to invalidate:**

```sql
-- Clear all cache (nuclear option)
TRUNCATE photo_analysis_cache;

-- Clear expired only (safe, automatic)
SELECT cleanup_expired_cache();

-- Clear specific manufacturer (targeted)
DELETE FROM photo_analysis_cache
WHERE extraction_result->>'manufacturer' ILIKE '%siemens%';
```

**Automatic cleanup:**
- Cache entries expire after 24 hours (TTL)
- `cleanup_expired_cache()` function available for manual triggers

### 5.3 Cost Spikes

**Monitoring thresholds:**
| Metric | Normal | Warning | Critical |
|--------|--------|---------|----------|
| Daily API cost | <$5 | $5-15 | >$15 |
| Groq calls/hour | <100 | 100-200 | >200 |
| Claude calls/hour | <50 | 50-100 | >100 |

**Investigation steps:**

```sql
-- Check recent photo volume
SELECT DATE(created_at), COUNT(*)
FROM photo_analysis_cache
GROUP BY DATE(created_at)
ORDER BY 1 DESC LIMIT 7;

-- Check cache hit rate
SELECT
    COUNT(*) as total,
    SUM(access_count) as total_hits,
    AVG(access_count) as avg_hits_per_image
FROM photo_analysis_cache
WHERE created_at > NOW() - INTERVAL '24 hours';
```

**Cost reduction strategies:**
1. Increase cache TTL beyond 24h for stable photos
2. Lower Groq confidence threshold (currently 80%)
3. Skip Stage 3 more aggressively (only when KB match is strong)

### 5.4 Common Error Messages

| Error | Cause | Fix |
|-------|-------|-----|
| `GROQ_API_KEY not configured` | Missing env var | Add to `.env` |
| `Screening confidence below threshold` | Non-industrial photo | Expected behavior |
| `JSON parse error` | Malformed LLM response | Check prompt, retry |
| `All database providers failed` | DB connection issue | Check Neon status |
| `Equipment matching failed` | DB write error | Check constraints |

---

## 6. Local Development Setup

### 6.1 Quick Start (< 5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/Mikecranesync/Rivet-PRO.git
cd Rivet-PRO

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment template
cp .env.example .env

# 5. Edit .env with your API keys
nano .env

# 6. Run the bot
python -m rivet_pro.adapters.telegram
```

### 6.2 Required API Keys for Development

| Service | How to Get | Cost |
|---------|------------|------|
| Telegram | @BotFather on Telegram | Free |
| Groq | https://console.groq.com | Free tier available |
| DeepSeek | https://platform.deepseek.com | Pay-as-you-go |
| Anthropic | https://console.anthropic.com | Pay-as-you-go |
| Neon | https://console.neon.tech | Free tier (500MB) |

### 6.3 Minimal .env for Development

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token
DATABASE_URL=postgresql://user:pass@host/neondb?sslmode=require
GROQ_API_KEY=gsk_...
DEEPSEEK_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
JWT_SECRET_KEY=dev-secret-key-at-least-32-chars

# Optional (for full features)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

### 6.4 Running Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Specific test file
pytest tests/unit/test_screening_service.py -v

# With coverage
pytest tests/ --cov=rivet_pro --cov-report=html
```

### 6.5 Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Make changes, run tests
pytest tests/ -v

# 3. Commit with conventional format
git commit -m "feat(photo-pipeline): add retry logic"

# 4. Push and create PR
git push origin feature/my-feature
```

---

## 7. Monitoring & Alerting

### 7.1 Key Metrics to Watch

| Metric | Source | Normal Range | Alert Threshold |
|--------|--------|--------------|-----------------|
| End-to-end latency (P95) | Langfuse | <5s | >8s |
| Groq screening latency | Langfuse | <2s | >4s |
| DeepSeek extraction latency | Langfuse | <3s | >5s |
| Cache hit rate | photo_analysis_cache | >20% | <10% |
| Daily API cost | Langfuse | <$5 | >$15 |
| Error rate | journalctl | <1% | >5% |
| Photo rejection rate | Logs | 10-20% | >40% |
| DB connection pool usage | asyncpg | <80% | >90% |

### 7.2 Langfuse Dashboard Setup

1. Create account at https://cloud.langfuse.com
2. Create new project "rivet-pro"
3. Get API keys from Settings > API Keys
4. Add to `.env`:
   ```bash
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_BASE_URL=https://us.cloud.langfuse.com
   ```

**Tracked traces:**
- `industrial_photo_screening` - Stage 1 Groq calls
- `deepseek_component_extraction` - Stage 2 DeepSeek calls
- `claude_kb_analysis` - Stage 3 Claude calls

### 7.3 Log Monitoring

```bash
# Follow bot logs in real-time
journalctl -u rivet-bot -f

# Search for errors
journalctl -u rivet-bot --since "1 hour ago" | grep -i error

# Filter by log level
journalctl -u rivet-bot | grep -E "ERROR|WARNING"

# Export logs for analysis
journalctl -u rivet-bot --since "2026-01-17" -o json > logs.json
```

### 7.4 Database Health Queries

```sql
-- Connection pool status (run on Neon dashboard)
SELECT count(*) as active_connections
FROM pg_stat_activity
WHERE state = 'active';

-- Recent equipment creation rate
SELECT
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as equipment_created
FROM cmms_equipment
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY 1
ORDER BY 1 DESC;

-- Knowledge base health
SELECT
    COUNT(*) as total_atoms,
    COUNT(*) FILTER (WHERE human_verified) as verified,
    AVG(confidence)::numeric(3,2) as avg_confidence,
    SUM(usage_count) as total_usage
FROM knowledge_atoms;

-- Pending knowledge gaps
SELECT
    manufacturer,
    COUNT(*) as gap_count,
    AVG(priority)::numeric(5,2) as avg_priority
FROM knowledge_gaps
WHERE research_status = 'pending'
GROUP BY manufacturer
ORDER BY avg_priority DESC
LIMIT 10;
```

### 7.5 Alerting Configuration

**Telegram alerts** (automatic via bot):
- Database failover events
- High error rates (>5% in 5 minutes)
- Cost threshold exceeded

**Setup admin alerts:**

```python
# In settings.py
telegram_admin_chat_id: int = Field(
    8445149012,  # Replace with your admin Telegram ID
    description="Admin chat ID for alerts"
)
```

### 7.6 Runbook: Common Alerts

#### Alert: Database Failover

**Triggered when:** Primary Neon database fails, system switches to Supabase/CockroachDB

**Actions:**
1. Check Neon status: https://console.neon.tech
2. Review failover alert in admin Telegram
3. Monitor performance on backup database
4. Once Neon recovers, restart bot to reconnect to primary

#### Alert: High Error Rate

**Triggered when:** >5% of requests fail in 5-minute window

**Actions:**
1. Check logs: `journalctl -u rivet-bot -n 100 --no-pager | grep ERROR`
2. Identify failing stage (1/2/3)
3. Check corresponding API provider status
4. If API issue, enable graceful degradation

#### Alert: Cost Spike

**Triggered when:** Daily cost exceeds $15

**Actions:**
1. Check Langfuse dashboard for usage patterns
2. Identify source (specific user, bot spam, etc.)
3. Verify cache is working (check hit rate)
4. Consider rate limiting if abuse detected

---

## Appendix A: File Structure

```
rivet_pro/
├── adapters/
│   ├── telegram/
│   │   ├── __main__.py          # Entry point
│   │   └── bot.py               # Main bot handlers
│   └── llm/
│       └── router.py            # LLM provider routing
├── core/
│   ├── services/
│   │   ├── photo_pipeline_service.py   # Main orchestrator
│   │   ├── screening_service.py        # Stage 1: Groq
│   │   ├── extraction_service.py       # Stage 2: DeepSeek
│   │   ├── claude_analyzer.py          # Stage 3: Claude
│   │   └── equipment_service.py        # Equipment CRUD
│   └── models/
│       ├── screening.py         # ScreeningResult
│       └── extraction.py        # ExtractionResult
├── infra/
│   ├── database.py              # DB connection + retry
│   └── observability.py         # Logging + tracing
├── config/
│   └── settings.py              # Pydantic settings
└── migrations/
    ├── 003_cmms_equipment.sql
    ├── 009_knowledge_atoms.sql
    └── 028_photo_analysis_cache.sql
```

---

*Document generated for RIVET Pro v1.0 - Photo Pipeline Phase 6*
