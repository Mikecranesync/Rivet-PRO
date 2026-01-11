# Fix Plan: RIVET Pro

**Branch**: `ralph/mvp-phase1`
**Description**: Phase 1 MVP - Usage tracking, Stripe payment, freemium limits, and optimizations

---

## Completed Stories (Reference)

_These stories were implemented with the previous Ralph system (Amp-based). They are complete and should NOT be re-implemented._

### ✅ RIVET-001: Usage Tracking System
Completed - Files: `011_usage_tracking.sql`, `usage_service.py`

### ✅ RIVET-002: Stripe Payment Integration
Completed - Files: `012_stripe_integration.sql`, `stripe_service.py`, stripe router

### ✅ RIVET-003: Free Tier Limit Enforcement
Completed - Files: Modified `bot.py` photo handler

---

## Discarded Stories (Not Migrated)

_These stories were started but not completed with Amp-based Ralph. They have been discarded and will not be implemented in frankbria system._

### ❌ RIVET-004: Shorten System Prompts
**Status**: Discarded (not migrated)

### ❌ RIVET-005: Remove n8n Footer
**Status**: Discarded (not migrated)

---

## Current Tasks

### ✅ RIVET-006: API Version Endpoint

Add a `/api/version` endpoint that returns API version, environment, and build information for production monitoring and debugging.

**Acceptance Criteria**:
- [ ] Create `rivet_pro/adapters/web/routers/version.py` with APIRouter
- [ ] Implement `GET /version` endpoint that returns JSON
- [ ] Return version info: `{"version": "1.0.0", "environment": "production/development", "api_name": "rivet-pro-api", "python_version": "3.11.x"}`
- [ ] Add module docstring explaining endpoint purpose
- [ ] Add function docstring for the endpoint
- [ ] Use async def for the endpoint function
- [ ] Register version router in `rivet_pro/adapters/web/main.py` with prefix `/api`
- [ ] Add type hints (use `dict` for return type)
- [ ] Test manually: `curl http://localhost:8000/api/version` returns 200
- [ ] Commit with message: `feat(RIVET-006): add API version endpoint`

**Implementation Notes**:
- Follow existing router pattern (see `routers/stripe.py` for example)
- Use async/await consistently
- Import `APIRouter` from `fastapi`
- Get settings from `rivet_pro.config.settings`
- Keep response format simple and standard
- No authentication required (public version info)
- No database access needed (static info only)

**Testing**:
```bash
# Start API server
cd /c/Users/hharp/OneDrive/Desktop/Rivet-PRO
cd rivet_pro && python -m adapters.web.main &
sleep 3

# Test endpoint
curl http://localhost:8000/api/version

# Expected response:
# {"version":"1.0.0","environment":"development","api_name":"rivet-pro-api","python_version":"3.11.x"}

# Stop server
pkill -f "python -m adapters.web.main"
```

---

## Active Sprint - MVP Launch

### RIVET-007: Verify n8n Photo Bot v2 Gemini Credential

**Priority:** P0 - MVP Blocker
**Complexity:** Simple
**Status:** ⬜ TODO

**Description:**
Verify that the n8n Photo Bot v2 workflow (ID: 7LMKcMmldZsu1l6g) has a valid Gemini API credential configured. Without this, photo OCR will fail in production. Log into n8n UI, check the Gemini Vision node credential, and test workflow execution.

**Acceptance Criteria:**
- [ ] Log into n8n at http://72.60.175.144:5678
- [ ] Open Photo Bot v2 workflow (7LMKcMmldZsu1l6g)
- [ ] Verify Gemini API credential is configured on Vision node
- [ ] Execute workflow manually with test photo
- [ ] Confirm workflow returns equipment identification
- [ ] No credential-related errors in execution logs
- [ ] Document credential name and configuration in n8n

**Implementation Notes:**
- This is n8n UI configuration, not code changes
- If credential is missing, create new Google credential in n8n
- Use API key from GEMINI_API_KEY environment variable
- Test with a sample equipment photo (motor nameplate)
- Verify response includes equipment name, manufacturer, model

---

### RIVET-008: Configure Production HTTPS Webhook

**Priority:** P0 - MVP Blocker
**Complexity:** Medium
**Status:** ⬜ TODO

**Description:**
Configure HTTPS webhook for Telegram bot production deployment. Currently using polling mode (development only). Telegram requires HTTPS for production webhooks. Choose between ngrok (fast MVP) or proper SSL certificate (production-ready).

**Acceptance Criteria:**
- [ ] Choose webhook approach (ngrok or Let's Encrypt SSL)
- [ ] Configure HTTPS endpoint on VPS (72.60.175.144)
- [ ] Update `rivet_pro/adapters/telegram/bot.py` to use webhook mode
- [ ] Change `application.run_polling()` to `application.run_webhook()`
- [ ] Set webhook URL with Telegram API
- [ ] Test bot receives messages via webhook
- [ ] Verify photo uploads trigger n8n workflow
- [ ] Commit changes with message: `feat(RIVET-008): configure production HTTPS webhook`

**Files to Create/Modify:**
- `rivet_pro/adapters/telegram/bot.py` - Change from polling to webhook mode
- Optionally: nginx configuration for reverse proxy

**Implementation Notes:**
- For MVP: Use ngrok for quick HTTPS tunnel
- For production: Configure domain + Let's Encrypt SSL
- Webhook URL format: `https://your-domain.com/telegram-webhook`
- Test webhook with curl before registering with Telegram
- Keep polling mode as fallback option in code

---

### RIVET-009: Wire Ralph Workflow Database Credentials

**Priority:** P1 - Important for Autonomous Development
**Complexity:** Simple
**Status:** ⬜ TODO

**Description:**
Wire Neon PostgreSQL credentials to the 7 Postgres nodes in the Ralph Main Loop workflow. This enables Ralph to autonomously read stories from @fix_plan table and write progress updates. Currently the workflow exists but database credentials are not configured.

**Acceptance Criteria:**
- [ ] Log into n8n at http://72.60.175.144:5678
- [ ] Open Ralph Main Loop workflow
- [ ] Identify all 7 Postgres nodes without credentials
- [ ] Create Neon PostgreSQL credential in n8n (if not exists)
- [ ] Use NEON_DATABASE_URL from environment
- [ ] Wire credential to all 7 Postgres nodes
- [ ] Execute workflow manually to test
- [ ] Verify workflow can read from database
- [ ] Verify workflow can write progress updates
- [ ] No database connection errors in logs

**Implementation Notes:**
- This is n8n UI configuration, not code changes
- Credential format: PostgreSQL connection string
- Host: from NEON_DATABASE_URL
- Port: usually 5432
- Database: from NEON_DATABASE_URL
- User/Password: from NEON_DATABASE_URL
- Test each Postgres node individually

---

### RIVET-010: Add Comprehensive Bot Handler Tests

**Priority:** P1 - Quality Assurance
**Complexity:** Medium
**Status:** ⬜ TODO

**Description:**
Create comprehensive pytest suite for Telegram bot handlers. Test all commands (/start, /equip, /wo, /stats, /upgrade), photo handling, usage enforcement, and edge cases. Ensure free tier limits work correctly and error handling is robust.

**Acceptance Criteria:**
- [ ] Create `tests/test_bot_handlers.py` with 15+ tests
- [ ] Update `tests/conftest.py` with Telegram bot fixtures
- [ ] Test /start command (user registration)
- [ ] Test /equip command (equipment search)
- [ ] Test /wo command (work order creation)
- [ ] Test /stats command (usage statistics)
- [ ] Test /upgrade command (Stripe checkout)
- [ ] Test photo handler (OCR workflow trigger)
- [ ] Test usage limit enforcement (11th photo blocked)
- [ ] Test edge cases (invalid photo, timeout, DB errors)
- [ ] Mock external dependencies (Telegram API, n8n, DB)
- [ ] All tests pass with pytest
- [ ] Code coverage > 80% for bot.py
- [ ] Commit with message: `test(RIVET-010): add comprehensive bot handler tests`

**Files to Create/Modify:**
- `tests/test_bot_handlers.py` - New test suite
- `tests/conftest.py` - Add bot fixtures and mocks

**Implementation Notes:**
- Use pytest-asyncio for async test support
- Mock telegram.Update and telegram.Bot objects
- Mock n8n webhook responses
- Mock database queries with pytest-asyncpg
- Follow existing test patterns in tests/test_ocr.py
- Test both success and failure cases

---

### RIVET-011: Create Production Deployment Documentation

**Priority:** P1 - Operational Readiness
**Complexity:** Simple
**Status:** ⬜ TODO

**Description:**
Create comprehensive DEPLOYMENT.md guide for production VPS deployment. Include prerequisites, setup steps, n8n configuration, service management, and troubleshooting. Enable new developers to deploy from scratch in under 2 hours.

**Acceptance Criteria:**
- [ ] Create `DEPLOYMENT.md` in project root
- [ ] Document VPS requirements (Ubuntu, 2GB RAM, 20GB disk)
- [ ] List required accounts (Neon, Telegram, Gemini, Stripe)
- [ ] Provide initial setup steps (clone, dependencies, .env)
- [ ] Document database migration process
- [ ] Explain n8n installation and workflow import
- [ ] List all n8n credentials to configure
- [ ] Provide systemd service configurations for bot and API
- [ ] Document HTTPS webhook setup (refer to RIVET-008)
- [ ] Include nginx reverse proxy configuration
- [ ] Add monitoring and log file locations
- [ ] Provide common troubleshooting steps
- [ ] Create `.env.example` with all required variables
- [ ] Commit with message: `docs(RIVET-011): create production deployment guide`

**Files to Create/Modify:**
- `DEPLOYMENT.md` - New deployment guide
- `.env.example` - Environment variable template

**Implementation Notes:**
- Use clear section headers and numbered steps
- Include example commands for each step
- Reference existing documentation where appropriate
- Test deployment guide on fresh VPS if possible
- Link to STATUS_REPORT.md and MVP_ROADMAP.md
- Include "Common Issues" section with solutions

---

## Summary

- **Total Stories**: 9 total (4 completed, 2 discarded, 5 active)
- **Completed**: 4 ✅ (RIVET-001, RIVET-002, RIVET-003, RIVET-006)
- **Discarded**: 2 ❌ (RIVET-004, RIVET-005)
- **Active Sprint**: 5 ⬜ (RIVET-007, RIVET-008, RIVET-009, RIVET-010, RIVET-011)

**Next**: Run Ralph to autonomously implement RIVET-007 through RIVET-011
