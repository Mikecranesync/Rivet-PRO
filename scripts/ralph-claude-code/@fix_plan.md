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

### ❌ RIVET-006: API Version Endpoint

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

## Summary

- **Total Stories**: 3 completed, 2 discarded
- **Completed**: 3 ✅ (RIVET-001, RIVET-002, RIVET-003)
- **Discarded**: 2 ❌ (RIVET-004, RIVET-005)
- **Pending**: 0

**Next**: Add RIVET-006 or later stories as needed
