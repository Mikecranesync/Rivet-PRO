# RIVET Pro - Agent Development Guide

**Purpose:** Document codebase patterns, conventions, and gotchas for autonomous agents (Ralph) and human developers.

**Last Updated:** 2026-01-11 (Ralph Chore 001 System Audit)

---

## Codebase Architecture

### Clean Architecture Layers

```
rivet_pro/
├── adapters/          # External integrations (Telegram, Web API, LLM)
├── core/              # Business logic (services, models, prompts)
├── infra/             # Infrastructure (database, observability)
└── config/            # Configuration (settings, environment)
```

**Key Principle:** Dependencies flow inward. Core never imports from adapters. Adapters can import from core.

---

## Patterns Discovered (Audit 2026-01-11)

### Pattern 1: Multi-Provider OCR with Cost Optimization

**Location:** `rivet_pro/core/services/ocr_service.py`

**Description:**
Chain multiple OCR providers from cheapest/fastest to most expensive/accurate. Try each provider in sequence until one succeeds.

**Provider Chain:**
1. **Groq** (fastest, cheapest) - Try first
2. **Gemini 2.5 Flash** (good balance) - Primary fallback
3. **Claude 3.5 Sonnet** (high accuracy) - Secondary fallback
4. **GPT-4o** (most expensive) - Final fallback

**Implementation Pattern:**
```python
async def analyze_photo(photo_bytes: bytes) -> OCRResult:
    providers = [
        ('groq', analyze_with_groq),
        ('gemini', analyze_with_gemini),
        ('claude', analyze_with_claude),
        ('gpt4o', analyze_with_gpt4o)
    ]

    for provider_name, provider_func in providers:
        try:
            result = await provider_func(photo_bytes)
            if result.confidence > THRESHOLD:
                logger.info(f"OCR success with {provider_name}")
                return result
        except Exception as e:
            logger.warning(f"{provider_name} failed: {e}")
            continue

    raise OCRError("All providers failed")
```

**When to Use:**
- Any multi-provider integration where cost/latency matters
- LLM routing, image analysis, translation services
- Want automatic failover without manual intervention

**Benefits:**
- Cost optimization (tries cheap options first)
- High availability (automatic failover)
- Performance optimization (faster providers first)
- Easy to add/remove providers

---

### Pattern 2: Usage Enforcement with Check-Before-Record

**Location:** `rivet_pro/core/services/usage_service.py`, `rivet_pro/adapters/telegram/bot.py`

**Description:**
Check usage limits BEFORE performing expensive operations. Record usage AFTER successful completion. Never charge users for failed operations.

**Implementation Pattern:**
```python
# In bot handler
async def handle_photo(update: Update):
    user_id = update.effective_user.id

    # Check BEFORE processing
    can_use, current_count, reason = await usage_service.can_use_service(user_id)

    if not can_use:
        await update.message.reply_text(
            f"❌ Limit reached ({current_count}/10 free lookups). "
            f"Upgrade to Pro for unlimited: /upgrade"
        )
        return

    # Perform expensive operation
    try:
        result = await ocr_service.analyze_photo(photo_bytes)

        # Record AFTER success
        await usage_service.record_lookup(
            user_id=user_id,
            equipment_id=result.equipment_id,
            lookup_type='photo_ocr'
        )

        await update.message.reply_text(f"✅ {result.equipment_name}")
    except Exception as e:
        # Don't record usage on failure
        logger.error(f"OCR failed: {e}")
        await update.message.reply_text("❌ Analysis failed. Try again.")
```

**Key Points:**
- Check limits synchronously before async operations
- Return early if limit exceeded (fail fast)
- Only increment usage counter after successful operation
- Never charge users for errors/failures

**When to Use:**
- API rate limiting
- Freemium tier enforcement
- Credit-based systems
- Any usage-based billing

---

### Pattern 3: Stripe Webhook with Signature Verification

**Location:** `rivet_pro/core/services/stripe_service.py`, `rivet_pro/adapters/web/routers/stripe.py`

**Description:**
Always verify Stripe webhook signatures before processing events. This prevents webhook spoofing and ensures events are authentic.

**Implementation Pattern:**
```python
from fastapi import Request, HTTPException
import stripe

async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    # Verify signature FIRST
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.stripe_webhook_secret
        )
    except ValueError:
        # Invalid payload
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Process verified event
    event_type = event['type']

    if event_type == 'checkout.session.completed':
        await handle_checkout_completed(event)
    elif event_type == 'customer.subscription.updated':
        await handle_subscription_updated(event)
    # ... handle other event types

    return {"status": "success"}
```

**Critical Security Points:**
- ALWAYS verify signature before any processing
- Use constant-time comparison (Stripe SDK does this)
- Return 400 for invalid signatures (not 200)
- Log signature verification failures
- Store webhook secret securely in environment variables

**When to Use:**
- All Stripe webhook endpoints
- Any webhook requiring cryptographic verification
- Payment processing integrations

---

### Pattern 4: Equipment Fuzzy Matching with Taxonomy

**Location:** `rivet_pro/core/services/equipment_service.py`, `rivet_pro/core/services/equipment_taxonomy.py`

**Description:**
Use 3-step fuzzy matching algorithm to find equipment even with typos, abbreviations, or variations in manufacturer/model names.

**Matching Algorithm:**
1. **Exact Match:** Try exact name/model/manufacturer match first
2. **Fuzzy Match:** Use Levenshtein distance for typo tolerance
3. **Taxonomy Match:** Fall back to equipment category/type matching

**Implementation Pattern:**
```python
async def find_equipment(
    name: str = None,
    manufacturer: str = None,
    model: str = None
) -> List[Equipment]:

    # Step 1: Exact match
    exact = await db.fetch("""
        SELECT * FROM equipment
        WHERE name = $1 OR (manufacturer = $2 AND model = $3)
    """, name, manufacturer, model)

    if exact:
        return exact

    # Step 2: Fuzzy match with similarity threshold
    fuzzy = await db.fetch("""
        SELECT *, similarity(name, $1) as score
        FROM equipment
        WHERE similarity(name, $1) > 0.6
        ORDER BY score DESC
        LIMIT 10
    """, name)

    if fuzzy:
        return fuzzy

    # Step 3: Taxonomy category match
    category = await taxonomy_service.classify(name)
    taxonomy_match = await db.fetch("""
        SELECT * FROM equipment
        WHERE category = $1
        LIMIT 10
    """, category)

    return taxonomy_match or []
```

**When to Use:**
- User input with potential typos
- Product catalogs with variations
- Any fuzzy search requirement
- Equipment/part number matching

**Benefits:**
- Typo-tolerant search
- Works with partial information
- Falls back gracefully
- Returns best matches first

---

### Pattern 5: AsyncPG Connection Pool with Lifespan Management

**Location:** `rivet_pro/infra/database.py`, `rivet_pro/adapters/web/main.py`

**Description:**
Initialize database connection pool in FastAPI lifespan event, not at module import time. This ensures proper resource management and graceful shutdown.

**Implementation Pattern:**
```python
# database.py
import asyncpg

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        """Create connection pool."""
        self.pool = await asyncpg.create_pool(
            dsn=settings.neon_database_url,
            min_size=2,
            max_size=10,
            command_timeout=60
        )

    async def disconnect(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()

    async def fetch(self, query, *args):
        """Execute query and fetch results."""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

# Singleton instance
db = Database()

# main.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db.connect()
    logger.info("Database connected")

    yield

    # Shutdown
    await db.disconnect()
    logger.info("Database disconnected")

app = FastAPI(lifespan=lifespan)
```

**Why This Pattern:**
- Proper async resource management
- Graceful startup/shutdown
- Connection pool reuse
- No dangling connections

**When to Use:**
- Any async database connection
- Redis/cache connections
- External API clients with connection pools

---

### Pattern 6: SME Prompt Routing

**Location:** `rivet_pro/core/services/sme_service.py`, `rivet_pro/core/prompts/sme/*.py`

**Description:**
Route LLM prompts to manufacturer-specific subject matter expert (SME) prompts for better accuracy on specialized equipment.

**Implementation Pattern:**
```python
# sme_service.py
from rivet_pro.core.prompts.sme import siemens, rockwell, abb, generic

MANUFACTURER_SME_MAP = {
    'siemens': siemens.PROMPT,
    'rockwell': rockwell.PROMPT,
    'allen-bradley': rockwell.PROMPT,  # Alias
    'abb': abb.PROMPT,
    'schneider': schneider.PROMPT,
    'mitsubishi': mitsubishi.PROMPT,
    'fanuc': fanuc.PROMPT,
}

def get_sme_prompt(manufacturer: str) -> str:
    """Get manufacturer-specific SME prompt."""
    manufacturer_lower = manufacturer.lower()

    # Try exact match
    if manufacturer_lower in MANUFACTURER_SME_MAP:
        return MANUFACTURER_SME_MAP[manufacturer_lower]

    # Try partial match
    for key, prompt in MANUFACTURER_SME_MAP.items():
        if key in manufacturer_lower or manufacturer_lower in key:
            return prompt

    # Fall back to generic
    return generic.PROMPT
```

**SME Prompt Structure:**
```python
# siemens.py
PROMPT = """
You are a Siemens industrial automation expert with deep knowledge of:
- SIMATIC PLCs (S7-1200, S7-1500, S7-300, S7-400)
- SINAMICS drives (G120, S120, V90)
- HMI systems (Comfort Panels, Mobile Panels)
- Industrial communication (PROFINET, PROFIBUS)

When analyzing Siemens equipment photos:
1. Identify product line (SIMATIC, SINAMICS, SITOP, etc.)
2. Extract article number (MLFB) from nameplate
3. Provide TIA Portal configuration tips
4. Reference relevant Siemens documentation

Common troubleshooting steps for Siemens equipment:
...
"""
```

**When to Use:**
- Domain-specific expertise needed
- Multiple product lines/manufacturers
- Specialized technical documentation
- Industry-specific terminology

**Benefits:**
- Higher accuracy for specialized domains
- Contextual troubleshooting advice
- Manufacturer-specific part numbers
- Better extraction from nameplates

---

## Gotchas Found

### Gotcha 1: Telegram Polling vs Webhooks

**Problem:**
Telegram bot has two modes: polling (for development) and webhooks (for production). Polling mode doesn't work in production because it requires constant connection. Webhooks require HTTPS.

**Symptoms:**
- Bot works locally but not on VPS
- "Connection timeout" errors in production
- Telegram says "webhook set" but bot doesn't respond

**Solution:**
```python
# Development (polling)
if settings.environment == 'development':
    application.run_polling()
else:
    # Production (webhook)
    application.run_webhook(
        listen='0.0.0.0',
        port=8443,
        url_path='telegram-webhook',
        webhook_url=f'https://your-domain.com/telegram-webhook'
    )
```

**Prevention:**
- Use environment variable to switch modes
- Always test webhook mode before production deploy
- Configure HTTPS FIRST, then set webhook
- Use ngrok for quick HTTPS testing

---

### Gotcha 2: AsyncPG Pool Initialization

**Problem:**
If you create AsyncPG connection pool at module import time, it will fail because event loop doesn't exist yet.

**Symptoms:**
- "RuntimeError: no running event loop"
- "coroutine was never awaited"
- Import-time errors with async code

**Wrong:**
```python
# database.py - WRONG
import asyncpg

# This runs at import time, before event loop exists
pool = asyncpg.create_pool(...)  # ❌ FAILS
```

**Right:**
```python
# database.py - CORRECT
import asyncpg

class Database:
    def __init__(self):
        self.pool = None  # Just None initially

    async def connect(self):
        # Create pool when connect() is called (in lifespan)
        self.pool = await asyncpg.create_pool(...)  # ✅ WORKS

db = Database()

# main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()  # Called when event loop exists
    yield
    await db.disconnect()
```

**Prevention:**
- Never call async functions at import time
- Use lifespan events for async initialization
- Initialize async resources lazily

---

### Gotcha 3: n8n Credentials Not Version Controlled

**Problem:**
n8n credentials (API keys, database passwords) are stored in n8n's internal database, NOT in workflow JSON files. When you export/import workflows, credentials are NOT included.

**Symptoms:**
- Imported workflow shows "Credential not set"
- Workflow fails with "No credentials found"
- Fresh n8n instance has no credentials

**Solution:**
1. Export workflows from n8n (gets workflow structure)
2. Manually recreate credentials in new n8n instance
3. Wire credentials to nodes in imported workflows
4. Test each workflow after credential wiring

**Prevention:**
- Document all required credentials in setup guide
- Keep credential names consistent across environments
- Create setup checklist for n8n deployment
- Test workflows after import

**Credential Documentation Pattern:**
```markdown
## Required n8n Credentials

### Gemini API
- Type: Google API Key
- Name: "Gemini Production"
- Key Source: GEMINI_API_KEY environment variable
- Used In: Photo Bot v2, LLM Judge

### Neon PostgreSQL
- Type: Postgres
- Name: "Neon Production"
- Connection String: NEON_DATABASE_URL environment variable
- Used In: Ralph Main Loop, CMMS Bot
```

---

### Gotcha 4: Stripe Webhook Secret Different Per Environment

**Problem:**
Stripe webhook signing secrets are different for test mode vs production mode. Using wrong secret causes signature verification to fail.

**Symptoms:**
- Webhooks work in Stripe test mode but fail in production
- "Invalid signature" errors
- Payments succeed but database doesn't update

**Solution:**
```python
# settings.py
class Settings(BaseSettings):
    # Different secrets for test vs production
    stripe_api_key: str
    stripe_webhook_secret: str

    # Load from environment
    # Test: whsec_test_xxx
    # Production: whsec_xxx
```

**Prevention:**
- Use separate environment variables for test/prod
- Test webhook signature verification before going live
- Use Stripe CLI for local webhook testing
- Document which secret goes in which environment

---

### Gotcha 5: Telegram Photo Download Expiry

**Problem:**
Telegram photo file_ids expire after a certain time (usually 24 hours). If you try to download a photo using an old file_id, it will fail.

**Symptoms:**
- Photos work immediately but fail later
- "File not found" errors for old photos
- Download timeouts for photos sent hours ago

**Solution:**
```python
async def handle_photo(update: Update):
    # Get photo immediately
    photo = update.message.photo[-1]  # Highest resolution

    # Download photo bytes NOW (don't store file_id)
    photo_file = await photo.get_file()
    photo_bytes = await photo_file.download_as_bytearray()

    # Process immediately or store bytes (not file_id)
    result = await ocr_service.analyze_photo(photo_bytes)

    # If you need to store the photo, save bytes to S3/blob storage
    # NOT the file_id
```

**Prevention:**
- Download and process photos immediately
- If storing photos, save bytes to blob storage (S3, Azure Blob)
- Never store just the file_id for later use
- Set up workflow to process within photo's validity window

---

## Development Workflow

### Adding a New Feature

1. **Read Existing Code First**
   - Find similar feature in codebase
   - Follow existing patterns
   - Check services for reusable logic

2. **Update Models (if needed)**
   - Add Pydantic models in `core/models/`
   - Add database tables via migration in `migrations/`

3. **Implement Business Logic**
   - Add service in `core/services/`
   - Use async/await consistently
   - Add error handling with logging

4. **Add API Endpoint (if needed)**
   - Create router in `adapters/web/routers/`
   - Register router in `adapters/web/main.py`
   - Add authentication if needed

5. **Add Bot Command (if needed)**
   - Add handler in `adapters/telegram/bot.py`
   - Register command with CommandHandler
   - Update bot description in BotFather

6. **Write Tests**
   - Create test file in `tests/`
   - Mock external dependencies
   - Test success and failure cases

7. **Update Documentation**
   - Update README if user-facing
   - Update this AGENTS.md if pattern discovered
   - Add comments for complex logic

---

## Testing Guidelines

### Unit Tests

**Location:** `tests/`

**Pattern:**
```python
import pytest
from rivet_pro.core.services.equipment_service import find_equipment

@pytest.mark.asyncio
async def test_find_equipment_exact_match(mock_db):
    """Test exact equipment name match."""
    # Arrange
    mock_db.set_return_value([
        {'id': 1, 'name': 'Siemens Motor', 'manufacturer': 'Siemens'}
    ])

    # Act
    results = await find_equipment(name='Siemens Motor')

    # Assert
    assert len(results) == 1
    assert results[0]['name'] == 'Siemens Motor'

@pytest.mark.asyncio
async def test_find_equipment_fuzzy_match(mock_db):
    """Test fuzzy matching with typo."""
    # Should find 'Siemens Motor' even with typo 'Seimens Motor'
    results = await find_equipment(name='Seimens Motor')
    assert len(results) > 0
```

**Key Points:**
- Use `pytest.mark.asyncio` for async tests
- Mock database with fixtures
- Test both success and failure cases
- Use descriptive test names

---

## Configuration Management

### Environment Variables

**Location:** `rivet_pro/config/settings.py`

**Pattern:**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Required (no defaults)
    telegram_bot_token: str
    neon_database_url: str

    # Optional (with defaults)
    environment: str = "development"
    log_level: str = "INFO"

    # Nested config
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

settings = Settings()
```

**Loading Priority:**
1. Environment variables (highest)
2. .env file
3. Default values
4. Error if required var missing

---

## Database Migrations

### Creating a New Migration

**Location:** `migrations/`

**Naming:** `{number}_{description}.sql`

**Pattern:**
```sql
-- migrations/013_feature_name.sql

-- Create new table
CREATE TABLE IF NOT EXISTS new_feature (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Add index
CREATE INDEX idx_new_feature_user_id ON new_feature(user_id);

-- Add new column to existing table
ALTER TABLE users ADD COLUMN IF NOT EXISTS new_field TEXT;

-- Migration is idempotent (safe to run multiple times)
```

**Key Points:**
- Use `IF NOT EXISTS` / `IF NOT EXISTS` for idempotency
- Add indexes for foreign keys
- Include rollback instructions in comments
- Test migration on development database first

---

## Logging Best Practices

### Structured Logging

**Location:** `rivet_pro/infra/observability.py`

**Pattern:**
```python
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)

# Good logging
logger.info("OCR analysis started", extra={
    'user_id': user_id,
    'provider': 'gemini',
    'photo_size': len(photo_bytes)
})

# Log errors with context
try:
    result = await rivet_service.analyze(photo)
except Exception as e:
    logger.error(
        "OCR failed",
        extra={'user_id': user_id, 'error': str(e)},
        exc_info=True
    )
    raise

# Don't log sensitive data
logger.info("User login", extra={'user_id': user_id})  # ✅ Good
logger.info("User login", extra={'password': password})  # ❌ Bad
```

---

## Code Style

### Async/Await Consistency

**Always use async/await:**
- Database queries
- HTTP requests
- File I/O
- Telegram bot handlers

**Example:**
```python
# Good
async def create_equipment(data: dict) -> Equipment:
    async with db.pool.acquire() as conn:
        result = await conn.fetchrow(
            "INSERT INTO equipment (...) VALUES (...) RETURNING *",
            *data.values()
        )
    return Equipment(**result)

# Bad
def create_equipment(data: dict) -> Equipment:
    # Blocking database call
    result = blocking_db_query(...)
    return Equipment(**result)
```

### Type Hints

**Use type hints for:**
- Function parameters
- Return types
- Class attributes

**Example:**
```python
from typing import List, Optional, Dict, Any

async def find_equipment(
    name: Optional[str] = None,
    manufacturer: Optional[str] = None
) -> List[Dict[str, Any]]:
    ...
```

---

## Security Checklist

### Before Deploying to Production

- [ ] All API keys in environment variables (not hardcoded)
- [ ] Stripe webhook signature verification enabled
- [ ] Database uses connection pool (not hardcoded credentials)
- [ ] HTTPS enabled for webhooks
- [ ] JWT secret is random and secure
- [ ] SQL injection prevented (use parameterized queries)
- [ ] User input validated (Pydantic models)
- [ ] Rate limiting implemented for expensive operations
- [ ] Logging doesn't include sensitive data
- [ ] Error messages don't reveal system details

---

**End of AGENTS.md**

*This guide will evolve as new patterns and gotchas are discovered.*
*Always update this file when you find something worth documenting.*
