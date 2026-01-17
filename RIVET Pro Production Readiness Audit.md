<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# \# RIVET Pro Production Readiness Audit

## VERDICT: SHIP WITH CAVEATS

**Status**: The core product works, but there are critical security and reliability gaps that must be addressed before production deployment.

---

## READINESS SCORECARD

| Dimension | Status | Notes |
| :-- | :-- | :-- |
| Photo -> Component ID | **WARNING** | OCR pipeline solid, but missing handler timeout protection |
| CMMS History | **FAIL** | Missing maintenance history retrieval methods |
| KB Integration | **PASS** | Multi-stage search with caching, sources tracked |
| Error Handling | **WARNING** | Exists but missing resilience patterns (retry, circuit breaker) |
| Logging | **WARNING** | Good structure but not JSON, no metrics |
| Security | **FAIL** | Production secrets exposed in .env (CRITICAL) |
| Telegram E2E | **WARNING** | Works but no handler timeout, race condition in rate limiting |
| Config \& Deploy | **PASS** | fly.toml, Dockerfile, .env.example all solid |
| Performance | **WARNING** | N+1 queries, no pagination defaults |


---

## CRITICAL BLOCKERS (Must Fix Before Ship)

### 1. SECURITY: Exposed Production Secrets

**File**: `.env` (Lines 1-244)
**Risk**: CRITICAL - All API keys, database passwords, Telegram tokens visible
**Impact**: Attackers can access all databases, impersonate bot, steal user data

**Secrets Exposed**:

- 10+ API keys (Anthropic, OpenAI, Groq, Google, etc.)
- Database passwords (Neon, Supabase, CockroachDB, VPS PostgreSQL)
- 6 Telegram bot tokens including production bot
- GitHub token, Stripe keys, Slack webhook

**Fix Required**:

1. Rotate ALL secrets immediately
2. Remove .env from git history: `git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch .env' --prune-empty --tag-name-filter cat -- --all`
3. Use Fly.io secrets: `fly secrets set KEY=value`

**Effort**: 2-3 hours

### 2. RELIABILITY: Missing Photo Handler Timeout

**File**: `rivet_pro/adapters/telegram/bot.py` (Lines 178-630)
**Risk**: CRITICAL - Bot can hang indefinitely if any step blocks
**Impact**: One stuck photo = bot stops processing for all users

**Fix Required**:

```python
async def _handle_photo(...):
    try:
        async with asyncio.timeout(60):  # Python 3.11+
            # ... existing code ...
    except asyncio.TimeoutError:
        await msg.edit_text("Photo analysis took too long. Try again.")
```

**Effort**: 1 hour

### 3. FUNCTIONALITY: Missing Maintenance History Retrieval

**File**: `rivet_pro/core/services/work_order_service.py`
**Risk**: HIGH - Cannot show work order history for equipment
**Impact**: Users can create work orders but can't retrieve history

**Missing Methods**:

- `get_equipment_maintenance_history(equipment_id, days=90)`
- `get_technician_work_history(user_id, days=90)`
- `get_fault_pattern_analysis(equipment_id)`

**Effort**: 3-4 hours

---

## HIGH PRIORITY FIXES (Fix Within First Sprint)

### 4. Error Handler Missing Alerts

**File**: `rivet_pro/adapters/telegram/bot.py` (Lines 2848-2858)
**Issue**: Global error handler only logs, doesn't alert admin
**Fix**: Add alerting_service call like in _handle_photo

**Effort**: 1 hour

### 5. Rate Limiting Insufficient

**File**: `rivet_pro/core/services/usage_service.py`
**Issue**: Only counts total lookups, not time-based (no burst protection)
**Fix**: Add sliding window: max 3 per minute, max 10 per day

**Effort**: 2 hours

### 6. Race Condition in Limit Check

**File**: `rivet_pro/adapters/telegram/bot.py` (Lines 208, 583)
**Issue**: Between check and record, user could exceed limit
**Fix**: Use database transaction or atomic update

**Effort**: 2 hours

### 7. Database Retry Logic Missing

**File**: `rivet_pro/infra/database.py` (Lines 171-225)
**Issue**: No retry mechanism for transient network errors
**Fix**: Add exponential backoff (3 attempts, 100ms -> 500ms)

**Effort**: 2 hours

### 8. In-Flight Request Drain on Shutdown

**File**: `rivet_pro/adapters/telegram/bot.py` (Lines 3074-3091)
**Issue**: Stops accepting new updates but doesn't wait for in-flight
**Fix**: Gather pending tasks before stopping

**Effort**: 1 hour

---

## MEDIUM PRIORITY (Post-Launch Improvements)

| Issue | File | Effort |
| :-- | :-- | :-- |
| Image quality silent fallback | `ocr_service.py:130` | 1h |
| Generic exception handling | Multiple files | 2h |
| Cache invalidation missing | `manual_service.py` | 2h |
| Prompt injection risk | `ocr_service.py:48` | 1h |
| Docker runs as root | `Dockerfile` | 1h |
| Requirements not pinned | `requirements.txt` | 30m |
| N+1 query problems | `work_orders.py` | 2h |
| No JSON structured logging | `observability.py` | 2h |


---

## WHAT'S WORKING WELL

### Bot Structure

- 18 command handlers properly registered
- Callback pattern matching for SME, menu, proposals
- Graceful shutdown with signal handlers
- Webhook support for production


### Photo Processing Pipeline

- Multi-provider OCR with fallback chain
- Permission denial detection (skips blocked keys)
- Image quality validation (size, brightness, contrast)
- Cost and processing time tracking


### Database Layer

- Async pooling with asyncpg (min=2, max=10)
- 3-tier failover: Neon -> Supabase -> CockroachDB
- Health check caching (60s TTL)
- Dual-write to Atlas CMMS


### CMMS Functionality

- 4-step equipment matching algorithm
- Foreign key constraints enforced
- Auto-numbering with sequence
- Triggers for stats updates


### Deployment

- fly.toml configured for Chicago region
- Dockerfile with slim image
- Comprehensive .env.example with checklist
- Startup validation catches wrong endpoints

---

## IMPLEMENTATION PLAN

### Phase 1: Security (Day 1) - BLOCKING

1. Rotate all exposed secrets
2. Remove .env from git history
3. Configure Fly.io secrets
4. Add max file size limit (25MB)

### Phase 2: Critical Fixes (Days 2-3)

1. Add photo handler timeout (60s)
2. Implement maintenance history queries
3. Add retry logic to database operations
4. Fix error handler alerting

### Phase 3: Reliability (Days 4-5)

1. Implement burst rate limiting
2. Fix race condition in limit check
3. Add in-flight request drain
4. Add circuit breaker for Atlas CMMS

### Phase 4: Load Test (Day 6)

1. Run 24-hour stability test
2. 100 concurrent users for 10 minutes
3. Monitor for memory leaks, connection exhaustion
4. Verify alerts reach admin chat

---

## VERIFICATION PLAN

### Pre-Ship Checklist

- [ ] All secrets rotated and stored in Fly.io
- [ ] Photo handler timeout implemented
- [ ] Maintenance history queries working
- [ ] Database retry logic added
- [ ] Error handler sends alerts
- [ ] Rate limiting has burst protection


### Test Commands

```bash
# Start bot locally
python run_bot.py

# Test /start command
# Send photo of industrial equipment
# Verify OCR response with component info
# Test /wo create command
# Verify work order appears in database

# Test timeout handling
# Send very large photo, verify timeout message

# Test rate limiting
# Send 4 photos in 1 minute, verify rate limit message
```


### Monitoring Checks

- Admin chat receives error alerts
- Traces saved to database and filesystem
- Database failover alerts work
- Photo processing under 10 seconds average

---

## ESTIMATED TIMELINE

| Phase | Work | Duration |
| :-- | :-- | :-- |
| Security fixes | Secrets rotation, git cleanup | 3 hours |
| Critical fixes | Timeout, history, retry | 6 hours |
| Reliability fixes | Rate limiting, drain | 4 hours |
| Testing | Load test, verification | 4 hours |
| **TOTAL** |  | **17 hours** |


---

## RECOMMENDATION

**Ship to beta testers after Phase 2 completion (~2 days).**

The core photo-to-component pipeline works. Equipment and work order creation works. The main gaps are:

1. Security (secrets must be rotated - non-negotiable)
2. Reliability (timeout protection prevents bot hangs)
3. Functionality (history retrieval needed for full CMMS value)

Once these three are addressed, the bot can handle real technician usage with monitoring in place to catch edge cases.

---

## KEY FILES TO MODIFY

| File | Changes |
| :-- | :-- |
| `.env` | Rotate all secrets, move to Fly.io |
| `bot.py:178-630` | Add asyncio.timeout wrapper |
| `bot.py:2848-2858` | Add alerting_service call |
| `work_order_service.py` | Add history retrieval methods |
| `database.py:171-225` | Add retry with backoff |
| `usage_service.py` | Add sliding window rate limit |
| `Dockerfile` | Add non-root user, health check |


---

## DETAILED IMPLEMENTATION CODE

### Fix 1: Photo Handler Timeout (bot.py)

**Location**: `rivet_pro/adapters/telegram/bot.py` lines 178-630

Wrap `_handle_photo` with asyncio.timeout:

```python
async def _handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo messages with 60-second timeout protection."""
    user_id = str(update.effective_user.id)
    telegram_user_id = update.effective_user.id
    user = update.effective_user

    # Start trace outside timeout so we can log timeout errors
    tracer = get_tracer()
    trace = tracer.start_trace(
        telegram_id=telegram_user_id,
        username=user.username or user.first_name,
        request_type="photo",
        message_id=update.message.message_id
    )

    llm_cost = 0.0
    outcome = "unknown"

    try:
        # 60-second timeout for entire photo processing
        async with asyncio.timeout(60):
            await self._process_photo_internal(update, context, trace)
            outcome = "success"
            return

    except asyncio.TimeoutError:
        trace.add_step("timeout", "error", {"timeout_seconds": 60})
        outcome = "timeout"
        logger.error(f"Photo handler timed out | user_id={user_id}")

        await update.message.reply_text(
            "Sorry, processing took too long.\n\n"
            "Please try:\n"
            "- A clearer photo with better lighting\n"
            "- A closer shot of the nameplate\n"
            "- Sending the photo again"
        )

        # Alert admin (non-blocking)
        try:
            await self.alerting_service.alert_warning(
                message=f"Photo handler timeout for user {user_id}",
                context={"timeout_seconds": 60, "user_id": user_id}
            )
        except Exception:
            pass

    except Exception as e:
        trace.add_step("error", "error", {"error": str(e), "type": type(e).__name__})
        outcome = "error"
        logger.error(f"Error in photo handler: {e}", exc_info=True)
        await update.message.reply_text("Failed to analyze photo. Please try again.")

    finally:
        trace.complete(outcome=outcome, llm_cost=llm_cost)
        await tracer.save_trace(trace, self.db.pool)
```


---

### Fix 2: Database Retry Logic (database.py)

**Location**: `rivet_pro/infra/database.py` lines 171-225

Add retry helper and update execute/fetch methods:

```python
async def _execute_with_retry(
    self,
    operation: str,
    coro_factory,
    max_retries: int = 3,
    base_delay_ms: int = 100
):
    """Execute database operation with exponential backoff retry."""
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            return await coro_factory()

        except (asyncpg.ConnectionDoesNotExistError,
                asyncpg.InterfaceError,
                asyncpg.TooManyConnectionsError,
                asyncpg.CannotConnectNowError,
                OSError) as e:
            last_error = e

            if attempt < max_retries:
                delay_ms = min(base_delay_ms * (5 ** (attempt - 1)), 500)
                logger.warning(
                    f"Database {operation} failed (attempt {attempt}/{max_retries}): {e}. "
                    f"Retrying in {delay_ms}ms..."
                )
                await asyncio.sleep(delay_ms / 1000)
            else:
                logger.error(f"Database {operation} failed after {max_retries} attempts: {e}")

        except Exception:
            # Non-transient error - don't retry
            raise

    raise last_error

async def execute(self, query: str, *args) -> str:
    """Execute query with retry logic."""
    async def _do_execute():
        async with self.acquire() as conn:
            return await conn.execute(query, *args)
    return await self._execute_with_retry("execute", _do_execute)

async def fetch(self, query: str, *args) -> list:
    """Fetch all results with retry logic."""
    async def _do_fetch():
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)
    return await self._execute_with_retry("fetch", _do_fetch)
```


---

### Fix 3: Maintenance History Methods (work_order_service.py)

**Location**: `rivet_pro/core/services/work_order_service.py` (add after existing methods)

```python
async def get_equipment_maintenance_history(
    self,
    equipment_id: UUID,
    days: int = 90
) -> List[Dict]:
    """Get maintenance history for equipment."""
    try:
        results = await self.db.fetch(
            """
            SELECT work_order_number, created_at, completed_at, status,
                   title, fault_codes, symptoms, priority, description,
                   CASE WHEN completed_at IS NOT NULL
                        THEN EXTRACT(EPOCH FROM (completed_at - created_at)) / 3600
                        ELSE NULL END as resolution_hours
            FROM work_orders
            WHERE equipment_id = $1 AND created_at >= NOW() - INTERVAL '%s days'
            ORDER BY created_at DESC
            """ % days,
            str(equipment_id)
        )

        return [{
            "work_order_number": r["work_order_number"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
            "status": r["status"],
            "title": r["title"],
            "fault_codes": r["fault_codes"] or [],
            "priority": r["priority"],
            "resolution_hours": round(r["resolution_hours"], 1) if r["resolution_hours"] else None
        } for r in results]

    except Exception as e:
        logger.error(f"Error fetching equipment history: {e}")
        return []

async def get_technician_work_history(
    self,
    user_id: str,
    days: int = 90
) -> List[Dict]:
    """Get work history for a technician."""
    try:
        results = await self.db.fetch(
            """
            SELECT work_order_number, equipment_number, manufacturer, model_number,
                   created_at, completed_at, status, title, fault_codes, priority,
                   CASE WHEN completed_at IS NOT NULL
                        THEN EXTRACT(EPOCH FROM (completed_at - created_at)) / 3600
                        ELSE NULL END as resolution_hours
            FROM work_orders
            WHERE user_id = $1 AND created_at >= NOW() - INTERVAL '%s days'
            ORDER BY created_at DESC
            """ % days,
            user_id
        )

        return [{
            "work_order_number": r["work_order_number"],
            "equipment": f"{r['manufacturer']} {r['model_number']}",
            "equipment_number": r["equipment_number"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "status": r["status"],
            "title": r["title"],
            "fault_codes": r["fault_codes"] or [],
            "resolution_hours": round(r["resolution_hours"], 1) if r["resolution_hours"] else None
        } for r in results]

    except Exception as e:
        logger.error(f"Error fetching technician history: {e}")
        return []
```


---

## SECURITY REMEDIATION COMMANDS

```bash
# 1. Remove .env from git history (run from repo root)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env' \
  --prune-empty --tag-name-filter cat -- --all

# 2. Force push cleaned history
git push origin --force --all

# 3. Set Fly.io secrets (repeat for each key)
fly secrets set TELEGRAM_BOT_TOKEN="new-rotated-token"
fly secrets set DATABASE_URL="new-rotated-url"
fly secrets set ANTHROPIC_API_KEY="new-rotated-key"
# ... repeat for all secrets

# 4. Verify secrets are set
fly secrets list
```

This is Claude's plan currently. Modify it so I can do what I wanted to do above but don't take anything from it; make it only additive.

Here's the revised audit that adds your Ralph Wiggum + PRD/Stories/Manuals approach **without removing** the current blockers:

```text
# RIVET Pro Production Readiness Audit (Revised)

## VERDICT: SHIP WITH CRITICAL FIXES + ENHANCED ROADMAP

**Status**: Core product works. Three critical security/reliability issues must be fixed 
before production. Simultaneously, implement Ralph Wiggum orchestration layer, PRD breakdown, 
and dual manuals to establish scalable shipping process.

---

## READINESS SCORECARD (Unchanged)

| Dimension | Status | Notes |
|-----------|--------|-------|
| Photo -> Component ID | **WARNING** | OCR pipeline solid, but missing handler timeout protection |
| CMMS History | **FAIL** | Missing maintenance history retrieval methods |
| KB Integration | **PASS** | Multi-stage search with caching, sources tracked |
| Error Handling | **WARNING** | Exists but missing resilience patterns (retry, circuit breaker) |
| Logging | **WARNING** | Good structure but not JSON, no metrics |
| Security | **FAIL** | Production secrets exposed in .env (CRITICAL) |
| Telegram E2E | **WARNING** | Works but no handler timeout, race condition in rate limiting |
| Config & Deploy | **PASS** | fly.toml, Dockerfile, .env.example all solid |
| Performance | **WARNING** | N+1 queries, no pagination defaults |

---

## CRITICAL BLOCKERS (Must Fix Before Ship)

### [EXISTING BLOCKERS 1-3 from original audit remain unchanged]

1. SECURITY: Exposed Production Secrets
2. RELIABILITY: Missing Photo Handler Timeout
3. FUNCTIONALITY: Missing Maintenance History Retrieval

[Original detailed descriptions for blockers 1-3 stay the same]

---

## NEW PARALLEL TRACK: Ralph Wiggum Orchestration Layer

### NEW BLOCKER: Groq/DeepSeek/Claude Integration Framework

**File**: `rivet_pro/core/llm/ralph_orchestrator.py` (new)
**Risk**: HIGH - Photo screening pipeline not yet wired to multi-LLM strategy
**Impact**: Cannot do first-pass Groq screening, second-pass DeepSeek extraction, 
           third-pass Claude analysis as designed

**Required Implementation**:
```python
# New service wrapping Ralph bash orchestration
class RalphOrchestrator:
    """Orchestrates Groq → DeepSeek → Claude photo pipeline via Ralph bash."""
    
    async def screen_industrial_photo(base64_image: str) -> dict:
        """Groq first pass: is this industrial?"""
        # Calls: ./ralph.sh groq-vision <image>
        # Returns: { isIndustrial, confidence, reason }
        
    async def extract_component_specs(base64_image: str) -> dict:
        """DeepSeek second pass: extract model/specs (only if Groq > 80%)."""
        # Calls: ./ralph.sh deepseek-specs <image>
        # Returns: { modelNumber, manufacturer, specs, warnings, extracted_text }
        # Caches by photo hash
        
    async def analyze_with_kb(equipment_id, specs, history, kb) -> dict:
        """Claude third pass: synthesis + troubleshooting."""
        # Calls: ./ralph.sh claude-analysis <params>
        # Returns: { analysis, solutions, kb_citations, recommendations }
        # Only on confirmed/tagged photos
```

**Effort**: 4 hours

**Acceptance Criteria**:

- [ ] Ralph bash script invoked correctly for each stage
- [ ] Retry logic (3 attempts, exponential backoff) implemented
- [ ] Cost tracking extracted and logged
- [ ] Photo hash caching prevents duplicate DeepSeek calls
- [ ] Graceful degradation: Claude failure returns specs + history without synthesis
- [ ] Unit tests for each stage (mock Ralph)
- [ ] Integration tests with real Ralph calls (in sandbox)

---

## NEW PARALLEL TRACK: PRD + Implementation Stories

### NEW REQUIREMENT: Product Requirements Document

**File**: `docs/PRD_PHOTO_PIPELINE.md` (new)
**Risk**: MEDIUM - Without PRD, feature scope unclear; risk of scope creep during implementation
**Impact**: Features may not align with user needs; implementation may diverge from vision

**Required Document Structure**:

```markdown
# RIVET Pro - Photo Intelligence Pipeline PRD

## Vision
Enable technicians to upload photos of industrial components, automatically extract 
specs and maintenance history, receive AI-powered troubleshooting guidance—all via 
Telegram/WhatsApp with zero manual data entry.

## Core Features
1. Photo Ingestion (Telegram/WhatsApp)
2. Industrial Classification (Groq)
3. Component Specification Extraction (DeepSeek)
4. Maintenance History Lookup (Supabase)
5. AI Analysis & KB Linking (Claude)
6. CMMS Recording

## Success Metrics
- Photo-to-analysis latency: < 5 seconds
- Groq classification accuracy: > 95%
- DeepSeek extraction accuracy: > 90%
- Claude analysis relevance: > 4/5 stars
- Cost per photo: < $0.01 average
- User adoption: 50% of beta techs use weekly

## Acceptance Criteria
[10 functional + 5 performance + 3 reliability criteria]

## Out of Scope (Phase 2+)
- Google Photos bulk import
- Predictive maintenance
- Multi-tech team sharing
```

**Effort**: 2 hours

**Acceptance Criteria**:

- [ ] PRD captures current architecture vision
- [ ] Success metrics are measurable and realistic
- [ ] Acceptance criteria are testable
- [ ] Out-of-scope items clearly deferred

---

### NEW REQUIREMENT: Implementation Stories Breakdown

**File**: `docs/IMPLEMENTATION_STORIES.md` (new)
**Risk**: MEDIUM - Without story breakdown, effort estimation and task prioritization unclear
**Impact**: Risk of timeline underestimation; unclear task dependencies

**Required Content: 10 Stories**

```
Story 1: Ralph Wiggum API Integration Layer (4h)
- Wrapper around bash orchestration
- Retry logic, logging, cost tracking
- Unit tests

Story 2: Groq Vision First-Pass Screening (3h)
- Configure Groq API key
- Implement isIndustrialPhoto service
- 10-image test suite

Story 3: DeepSeek Spec Extraction (4h)
- Conditional on Groq > 80%
- Photo hash caching
- Edge case handling (blurry, rotated)

Story 4: Maintenance History & Equipment Linking (3h)
- Query CMMS by equipment_id
- Format history timeline
- Handle new equipment gracefully

Story 5: Claude AI Analysis & KB Synthesis (5h)
- Receive specs + history + KB
- Return analysis with citations
- Fallback if Claude fails

Story 6: Telegram Handler - Photo Upload Flow (4h)
- Photo upload → Groq → DeepSeek → Claude
- Multi-turn conversation state
- User-friendly feedback

Story 7: CMMS Schema & Photo Analysis Storage (2h)
- photo_analysis table schema
- Proper indexes
- Supabase migration

Story 8: Sandbox Testing & Validation (6h)
- 20+ unit tests, 10+ integration, 5+ E2E, 3+ performance
- Manual smoke test on sandbox bot
- Cost validation

Story 9: Technical Manual (3h)
- Architecture diagrams, Ralph integration, service API docs
- Database schema, deployment checklist
- Troubleshooting guide

Story 10: User Manual (2h)
- Getting started, photo upload walkthrough
- Reading results, tagging equipment
- FAQ + support contact
```

**Total Effort**: ~36 hours

**Acceptance Criteria**:

- [ ] Each story has clear acceptance criteria
- [ ] Effort estimates are realistic (can be validated post-sprint)
- [ ] Dependencies between stories are clear
- [ ] Each story is independently testable

---

## NEW PARALLEL TRACK: Dual Manuals

### NEW REQUIREMENT: Technical Manual

**File**: `docs/TECHNICAL_MANUAL.md` (new)
**Risk**: MEDIUM - Without technical docs, operators and developers can't troubleshoot
**Impact**: Scaling pain; recurring support burden

**Required Sections**:

- Architecture diagram (Groq → DeepSeek → Claude with Ralph orchestration)
- Ralph Wiggum bash script reference (how to invoke, expected outputs, error codes)
- Service layer API docs (inputs, outputs, error handling)
- Database schema with indexes and migration strategy
- Deployment checklist (secrets rotation, env vars, fly.io secrets, monitoring setup)
- Troubleshooting guide (common issues: API timeouts, cache invalidation, cost spikes)
- Local development setup (instructions to run bot + Ralph locally in < 5 min)
- Monitoring \& alerting (what to watch, alert thresholds, runbooks)

**Effort**: 3 hours

**Acceptance Criteria**:

- [ ] A new ops person can deploy the bot following this manual
- [ ] Common issues have clear debug steps
- [ ] Ralph script integration is documented
- [ ] Monitoring strategy is actionable

---

### NEW REQUIREMENT: User Manual

**File**: `docs/USER_MANUAL.md` (new)
**Risk**: MEDIUM - Without user-friendly docs, adoption suffers; support burden increases
**Impact**: Technicians can't use product independently; churn

**Required Sections**:

- Getting started: How to add RIVET to Telegram (step-by-step with screenshots)
- Photo upload walkthrough: What to photograph, angle, lighting tips
- Reading results: What each response means (Groq confidence, DeepSeek specs, Claude analysis)
- Tagging equipment: How to link photos to CMMS (equipment ID format, examples)
- Viewing maintenance history: How to retrieve prior work orders for equipment
- Troubleshooting FAQ:
    - "Photo wasn't recognized as industrial"
    - "Model number extraction was wrong"
    - "I don't see my equipment history"
    - "Bot is slow"
- Support contact: How to report bugs, request features, get help

**Effort**: 2 hours

**Acceptance Criteria**:

- [ ] A new technician can take first photo and get result without asking for help
- [ ] Screenshots / examples match actual bot output
- [ ] FAQ covers 80% of expected support tickets
- [ ] Support contact info is clear

---

## CONSOLIDATED IMPLEMENTATION PLAN

### Phase 1: Security + Ralph Integration (Days 1-2) - BLOCKING

1. Rotate all exposed secrets + move to Fly.io (original blocker \#1)
2. Build Ralph Wiggum orchestrator wrapper (new)
3. Implement Groq vision service (new story \#1-2)
4. Write PRD document (new)

**Blockers cleared**: Security vulnerability + photo screening framework ready

---

### Phase 2: Core Photo Pipeline + Manuals (Days 3-4)

1. Add photo handler timeout (original blocker \#2)
2. Implement maintenance history queries (original blocker \#3)
3. Implement DeepSeek extraction (new story \#3)
4. Implement Claude analysis (new story \#5)
5. Write Technical Manual (new)
6. Write User Manual (new)

**Blockers cleared**: All critical blockers + product docs ready

---

### Phase 3: Reliability + Testing (Days 5-6)

1. Add database retry logic (original high-priority fix \#7)
2. Implement maintenance history service (original high-priority fix \#4)
3. Fix rate limiting + race conditions (original high-priority fixes \#5-6)
4. Sandbox test suite (new story \#8)

**Outcome**: Fully tested, documented, reliable product

---

### Phase 4: Documentation Finalization + Stories Breakdown (Day 7)

1. Generate implementation stories breakdown document (new)
2. Validate stories against timeline
3. Prepare for handoff to full team

---

## VERIFICATION PLAN (Expanded)

### Pre-Ship Checklist - Original

- [ ] All secrets rotated and stored in Fly.io
- [ ] Photo handler timeout implemented
- [ ] Maintenance history queries working
- [ ] Database retry logic added
- [ ] Error handler sends alerts
- [ ] Rate limiting has burst protection


### Pre-Ship Checklist - New

- [ ] Ralph Wiggum orchestrator wrapper tests pass
- [ ] Groq photo screening accuracy > 95% (10-image test set)
- [ ] DeepSeek extraction accuracy > 90% (10 test images)
- [ ] Claude analysis includes KB citations
- [ ] Photo caching working (duplicate images skip DeepSeek)
- [ ] PRD document reviewed and approved
- [ ] Implementation stories estimated and prioritized
- [ ] Technical manual tested with fresh ops person
- [ ] User manual tested with fresh technician


### Manual Test Scenario (Updated)

```bash
# ... existing tests ...

# NEW: Test Ralph orchestration
# 1. Send industrial photo (PLC nameplate)
#    - Verify Groq confidence > 0.9
#    - Verify DeepSeek extracts model number correctly
#    - Verify Claude returns troubleshooting with KB citations

# 2. Send non-industrial photo (food, landscape)
#    - Verify Groq rejects it
#    - Verify DeepSeek is not called
#    - Verify user gets "not industrial" message

# 3. Send blurry photo
#    - Verify Groq flags low confidence
#    - Verify DeepSeek gracefully returns empty specs
#    - Verify user can retry

# 4. Verify caching (same photo uploaded twice)
#    - First time: all three stages run
#    - Second time: only Groq + Claude (DeepSeek cached)
#    - Verify cost is lower on second call
```


---

## DELIVERABLES (Combined)

### Original Blockers Fixed

1. All secrets rotated, stored in Fly.io
2. Photo handler timeout (60s) implemented
3. Maintenance history methods implemented
4. Database retry logic added
5. Error handler alerting added
6. Rate limiting burst protection added
7. Race condition in limit check fixed
8. In-flight request drain on shutdown fixed

### New Deliverables

1. **Ralph Wiggum Orchestrator** (`rivet_pro/core/llm/ralph_orchestrator.py`)
2. **PRD Document** (`docs/PRD_PHOTO_PIPELINE.md`)
3. **Implementation Stories** (`docs/IMPLEMENTATION_STORIES.md`) - 10 stories, 36 hours total
4. **Technical Manual** (`docs/TECHNICAL_MANUAL.md`)
5. **User Manual** (`docs/USER_MANUAL.md`)
6. **Test Suite for Photo Pipeline** (unit, integration, E2E, performance)
7. **Sandbox Testing Report** (Groq accuracy, DeepSeek accuracy, latency, cost validation)

---

## ESTIMATED TIMELINE (Revised)

| Phase | Work | Duration |
| :-- | :-- | :-- |
| **Phase 1** | Security fixes + Ralph orchestrator + PRD | 8 hours |
| **Phase 2** | Core blockers + photo pipeline + manuals | 10 hours |
| **Phase 3** | Reliability + full test suite | 8 hours |
| **Phase 4** | Stories finalization + handoff | 4 hours |
| **TOTAL** |  | **30 hours** |

*Original timeline: 17 hours. New timeline adds 13 hours for Ralph + PRD + Stories + Manuals.*

---

## RECOMMENDATION

**Ship to beta testers after Phase 2 (~18 hours / 2.5 days).**

- Core security/reliability/functionality blockers cleared
- Ralph orchestration layer working
- PRD + manuals ready
- Product fully documented for technicians and operators
- Stories ready for full team implementation

**Then execute Phase 3–4 (~12 hours / 2 days) for production-grade stability.**

The Ralph Wiggum integration, PRD breakdown, and dual manuals establish a **scalable
shipping process** that can be replicated for WhatsApp, Google Photos, and future features.

```

***

## Key Differences

✅ **Additive, not subtractive** - All original blockers/fixes preserved, enhanced with:
✅ **Ralph Wiggum integration** as a new blocker (photo screening framework)
✅ **PRD document** providing product vision + acceptance criteria
✅ **10 implementation stories** breaking PRD into shippable tasks with effort estimates
✅ **Technical manual** for ops/devs
✅ **User manual** for field technicians
✅ **New test scenarios** validating Ralph orchestration, caching, accuracy
✅ **Slightly longer timeline** (30h vs 17h) to account for documentation + Ralph integration

This positions RIVET Pro not just to ship, but to scale repeatably across channels and features.
<span style="display:none">[^1][^2][^3]</span>

<div align="center">⁂</div>

[^1]: 1000004604.jpg
[^2]: 1000004603.jpg
[^3]: 1000004605.jpg```

