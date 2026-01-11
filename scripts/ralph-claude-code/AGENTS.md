# RIVET Pro - Agent Knowledge Base

## Project Overview

RIVET Pro is an AI-powered equipment identification system for field technicians. Core flow: Technician photographs equipment → OCR extraction → Equipment matching → Manual/troubleshooting delivery.

**Target Users**: Field maintenance technicians who need FAST, RELIABLE equipment identification and troubleshooting guidance.

**Business Model**:
- Free tier: 10 equipment lookups
- Pro tier: $29/month unlimited lookups + PDF chat + CMMS features
- Team tier: $200/month with shared knowledge base + PLC panel analysis

---

## Architecture

**Orchestration**: n8n workflows for deterministic paths + Python services for business logic

**AI Models**:
- Vision: Gemini 2.5 Flash (equipment photo OCR)
- Text: Claude Sonnet (troubleshooting, chat)

**Interface**: Telegram bot (@rivet_local_dev_bot)

**Database**: PostgreSQL via Supabase (db.mggqgrxwumnnujojndub.supabase.co)
- Connection pooling with asyncpg
- Min 2, Max 10 connections

---

## Key Files & Locations

### Core Services
- `rivet_pro/core/services/usage_service.py` - Freemium lookup tracking
- `rivet_pro/core/services/stripe_service.py` - Payment and subscription management
- `rivet_pro/core/services/__init__.py` - Service exports

### Database
- `rivet_pro/infra/database.py` - Database connection and query execution
- `rivet_pro/migrations/*.sql` - Schema migrations (run in order)

### Telegram Bot
- `rivet_pro/adapters/telegram/bot.py` - Main bot, command handlers, photo processing
- `rivet_pro/adapters/telegram/` - Telegram adapter layer

### Configuration
- `rivet_pro/config/settings.py` - Pydantic settings (loads from .env)
- `.env` - Environment variables (NOT in git)

### API
- `rivet_pro/adapters/web/routers/stripe.py` - Stripe webhook endpoint
- `rivet_pro/adapters/web/main.py` - FastAPI app setup

---

## Discovered Patterns

These patterns were discovered during RIVET-001, RIVET-002, RIVET-003 implementation. Future agents should follow these conventions.

### 1. Database Patterns

#### Always Use IF NOT EXISTS
**Rule**: All CREATE TABLE, CREATE INDEX, ALTER TABLE must be idempotent.

**Why**: Migrations may run multiple times. Avoid errors.

**Examples**:
```sql
-- Table creation
CREATE TABLE IF NOT EXISTS usage_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ...
);

-- Index creation
CREATE INDEX IF NOT EXISTS idx_usage_telegram_user
ON usage_tracking(telegram_user_id);

-- Column addition
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='users' AND column_name='subscription_status'
    ) THEN
        ALTER TABLE users ADD COLUMN subscription_status VARCHAR(20);
    END IF;
END $$;
```

#### asyncpg Positional Parameters
**Rule**: Use `$1, $2, $3` NOT named parameters.

**Why**: asyncpg doesn't support named params like `:user_id`.

**Examples**:
```python
# Correct
result = await db.fetch(
    "SELECT * FROM users WHERE telegram_user_id = $1",
    telegram_user_id
)

# Incorrect (will fail)
result = await db.fetch(
    "SELECT * FROM users WHERE telegram_user_id = :user_id",
    user_id=telegram_user_id
)
```

#### Services Receive Database Instance
**Rule**: Services are initialized with shared `Database` instance.

**Why**: Centralized connection pool management.

**Pattern**:
```python
class UsageService:
    def __init__(self, db: Database):
        self.db = db

    async def get_usage_count(self, telegram_user_id: int) -> int:
        result = await self.db.fetchval(
            "SELECT COUNT(*) FROM usage_tracking WHERE telegram_user_id = $1",
            telegram_user_id
        )
        return result or 0
```

**Initialization** (in bot.py):
```python
async def start():
    db = Database()
    await db.connect()

    # Services AFTER db.connect()
    usage_service = UsageService(db)
    stripe_service = StripeService(db)
```

#### DO $$ Blocks for Constraints
**Rule**: Use procedural blocks for conditional constraint creation.

**Why**: IF NOT EXISTS doesn't work directly with constraints.

**Example**:
```sql
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_subscription_status'
    ) THEN
        ALTER TABLE users ADD CONSTRAINT chk_subscription_status
        CHECK (subscription_status IN ('free', 'active', 'canceled', 'past_due'));
    END IF;
END $$;
```

---

### 2. Bot Development Patterns

#### Services Initialize AFTER db.connect()
**Rule**: Never create services before database connection is established.

**Why**: Services may query database during __init__.

**Correct Order**:
```python
async def start():
    # 1. Create database
    db = Database()

    # 2. Connect to database
    await db.connect()

    # 3. NOW create services
    usage_service = UsageService(db)
    stripe_service = StripeService(db)

    # 4. Create bot with services
    bot = TelegramBot(usage_service, stripe_service)

    # 5. Start bot
    await bot.start()
```

#### Telegram User ID is Integer
**Rule**: Access user ID via `update.effective_user.id` (returns int).

**Why**: Common mistake is to treat as string. Database expects integer.

**Correct**:
```python
async def _handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user_id = update.effective_user.id  # int

    # Use directly in queries
    allowed, count, reason = await self.usage_service.can_use_service(telegram_user_id)
```

#### HTML Parse Mode for Special Characters
**Rule**: Use `parse_mode='HTML'` for messages with special chars (<, >, &).

**Why**: Telegram escaping errors if characters aren't HTML-encoded.

**Example**:
```python
await update.message.reply_text(
    "<b>Upgrade Required</b>\n\nYou've used <code>10/10</code> free lookups.",
    parse_mode='HTML'
)
```

#### Try/Except for External Services
**Rule**: Wrap Stripe/API calls in try/except with fallback UX.

**Why**: External services can fail. Provide graceful degradation.

**Pattern**:
```python
try:
    checkout_url = await self.stripe_service.create_checkout_session(telegram_user_id)
    await update.message.reply_text(
        f"<a href='{checkout_url}'>Subscribe now</a>",
        parse_mode='HTML'
    )
except Exception as e:
    logger.error(f"Stripe checkout failed: {e}")
    await update.message.reply_text(
        "Upgrade required. Use /upgrade command for details."
    )
```

---

### 3. Python Conventions

#### PYTHONPATH for Import Testing
**Rule**: Use `PYTHONPATH=.` when testing imports from workspace root.

**Why**: Python needs workspace root in path to resolve `rivet_pro.*` imports.

**Usage**:
```bash
# From workspace root
PYTHONPATH=. python -c "from rivet_pro.core.services import UsageService; print('OK')"
```

#### Pydantic Settings with Optional API Keys
**Rule**: Use `Optional[str]` for API keys that may not be configured initially.

**Why**: Development may not have all keys. App should start with warnings, not errors.

**Pattern**:
```python
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Required
    telegram_bot_token: str = Field(..., description="Required token")

    # Optional (may not be set in dev)
    stripe_api_key: Optional[str] = Field(None, description="Stripe secret key")
    stripe_webhook_secret: Optional[str] = Field(None, description="Webhook secret")
```

**Service Handling**:
```python
def __init__(self, db: Database):
    self.db = db

    if not settings.stripe_api_key:
        logger.warning("Stripe API key not configured - payment features disabled")
        self.stripe = None
    else:
        self.stripe = stripe
        self.stripe.api_key = settings.stripe_api_key
```

#### Module Execution from Root
**Rule**: Run modules as `python -m rivet_pro.bot`, NOT `python rivet_pro/bot.py`.

**Why**: Correct import resolution for internal packages.

**Correct**:
```bash
cd /path/to/Rivet-PRO
python -m rivet_pro.adapters.telegram.bot
```

**Incorrect** (import errors):
```bash
cd /path/to/Rivet-PRO/rivet_pro/adapters/telegram
python bot.py  # Will fail with "No module named 'rivet_pro'"
```

---

### 4. Testing Patterns

#### Manual Telegram Testing is REQUIRED
**Rule**: For ANY bot behavior change, test with live Telegram bot.

**Why**: Mocks don't catch real-world issues (rate limits, message formatting, user flow).

**Process**:
```bash
# 1. Start bot locally
cd rivet_pro && python -m bot.bot

# 2. Open Telegram, find @rivet_local_dev_bot

# 3. Test the feature
# - Send /start
# - Upload equipment photo
# - Check responses are FAST and CORRECT
# - Verify error handling

# 4. Stop bot
# Ctrl+C in terminal
```

**Checklist**:
- [ ] Bot starts without errors
- [ ] Commands respond correctly
- [ ] Photo processing works
- [ ] Error messages are clear
- [ ] Responses are FAST (< 3 seconds for field techs)

#### Syntax Check Before Commit
**Rule**: Always run `python -m py_compile` before committing.

**Why**: Catch syntax errors early.

**Command**:
```bash
python -m py_compile rivet_pro/**/*.py
```

If any file fails, fix it before committing.

---

## Migration History

### 011_usage_tracking.sql (RIVET-001)
**Purpose**: Track equipment lookups per user for freemium enforcement.

**Tables**:
- `usage_tracking` - Records each lookup with timestamp

**Indexes**:
- `idx_usage_telegram_user` - Fast lookup by Telegram user
- `idx_usage_timestamp` - Time-based queries

**Pattern**: First use of IF NOT EXISTS for idempotency.

### 012_stripe_integration.sql (RIVET-002)
**Purpose**: Add Stripe subscription tracking to users table.

**Columns Added**:
- `subscription_status` - Enum: free, active, canceled, past_due
- `stripe_customer_id` - Stripe customer reference
- `stripe_subscription_id` - Stripe subscription reference
- `subscription_started_at` - Timestamp
- `subscription_ends_at` - Timestamp

**Constraint**: `chk_subscription_status` - Only valid statuses allowed

**Pattern**: First use of DO $$ block for conditional constraints.

### UsageService (RIVET-001)
**Purpose**: Business logic for freemium enforcement.

**Key Methods**:
- `get_usage_count(telegram_user_id)` - Total lookups
- `record_lookup(telegram_user_id, equipment_id, lookup_type)` - Record and return count
- `check_limit(telegram_user_id)` - Returns (can_proceed, count)
- `can_use_service(telegram_user_id)` - Combined check with Pro bypass

**FREE_TIER_LIMIT**: 10 lookups

**Pattern**: Service receives Database instance, all methods are async.

### StripeService (RIVET-002)
**Purpose**: Payment and subscription management.

**Key Methods**:
- `create_checkout_session(telegram_user_id, success_url, cancel_url)` - Generate checkout URL
- `handle_webhook_event(payload, sig_header)` - Process Stripe webhooks
- `get_subscription_status(telegram_user_id)` - Check current status
- `is_pro_user(telegram_user_id)` - Boolean Pro check

**Webhook Events Handled**:
- `checkout.session.completed` - Activate Pro subscription
- `customer.subscription.updated` - Update subscription status
- `customer.subscription.deleted` - Cancel subscription
- `invoice.payment_failed` - Mark as past_due

**Pattern**: Webhook signature verification with raw payload bytes is critical for security.

### Bot Integration (RIVET-003)
**Purpose**: Enforce freemium limits with upgrade prompt.

**Changes in `_handle_photo()`**:
1. Check `can_use_service()` BEFORE photo processing
2. If limit reached and free user, generate Stripe checkout link inline
3. Fallback to /upgrade command if Stripe fails
4. Record lookup AFTER successful OCR
5. Show remaining lookups to free users

**UX Pattern**: Minimize friction - provide direct checkout link, not just error message.

---

## Gotchas & Lessons Learned

### Database
- **Forgot IF NOT EXISTS**: Migration failed on re-run → Always use it
- **Named parameters**: asyncpg doesn't support → Use $1, $2
- **Service before db.connect()**: Query failed → Init services AFTER connect
- **Constraint without DO block**: SQL error → Use procedural block

### Bot
- **Telegram user ID as string**: Type error → It's an integer
- **Special chars in message**: Parse error → Use HTML parse_mode
- **Stripe checkout in error path**: Failed silently → Wrap in try/except
- **Services as globals**: Import cycle → Pass as constructor params

### Testing
- **Mocked Telegram responses**: Missed real formatting issues → Always test live
- **Import from subdir**: Module not found → Run with python -m from root

---

## Future Agent Guidance

### When Adding New Service
1. Create in `rivet_pro/core/services/<name>_service.py`
2. Accept `Database` in `__init__(self, db: Database)`
3. Make all methods `async def`
4. Export from `rivet_pro/core/services/__init__.py`
5. Initialize in bot.py AFTER `db.connect()`
6. Add to `TelegramBot.__init__()` params
7. Write tests with mocked Database

### When Adding Migration
1. Name: `0XX_<feature_name>.sql` (increment number)
2. Start with `-- Migration 0XX: <description>`
3. Use `IF NOT EXISTS` for all CREATE statements
4. Use `DO $$` blocks for conditional constraints
5. Test locally first: `psql -f migrations/0XX_*.sql`
6. Verify idempotency (run twice, no errors)

### When Modifying Bot
1. Read existing handler patterns first
2. Maintain HTML parse_mode for consistency
3. Test with live Telegram bot ALWAYS
4. Ensure responses are FAST (field tech requirement)
5. Add error handling with clear user messages

### When Using External APIs
1. Wrap in try/except
2. Provide fallback UX
3. Log errors for debugging
4. Use Optional[str] for API keys in settings
5. Check if key exists before initializing client

---

## Emergency Contacts

**Database**: Supabase (db.mggqgrxwumnnujojndub.supabase.co)
- Check connection: `psql $DATABASE_URL -c "SELECT 1;"`

**Telegram Bot**: @rivet_local_dev_bot
- Bot token in .env as TELEGRAM_BOT_TOKEN
- Admin chat ID: 8445149012

**Stripe**:
- API keys in .env (STRIPE_API_KEY, STRIPE_WEBHOOK_SECRET)
- Price ID for Pro tier in STRIPE_PRICE_ID

**n8n Workflows**: 72.60.175.144:5678
- Photo Bot workflow: 7LMKcMmldZsu1l6g
- Credentials: if4EOJbvMirfWqCC (Telegram)

---

## Quick Reference Commands

```bash
# Run bot locally
cd rivet_pro && python -m bot.bot

# Check syntax
python -m py_compile rivet_pro/**/*.py

# Test imports
PYTHONPATH=. python -c "from rivet_pro.core.services import UsageService"

# Database query
psql $DATABASE_URL -c "SELECT COUNT(*) FROM usage_tracking;"

# View recent logs
tail -f logs/rivet-pro.log

# Git recent commits
git log --oneline -10 --graph

# Search codebase
grep -r "pattern" rivet_pro/
```
