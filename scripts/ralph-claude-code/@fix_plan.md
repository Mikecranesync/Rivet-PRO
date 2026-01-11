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

_No active tasks. Ready for new stories starting at RIVET-006._

**To add new stories:**
1. Edit this file to add new story sections
2. Use format:
   ```
   ### ❌ RIVET-XXX: Story Title

   Story description here.

   **Acceptance Criteria**:
   - [ ] Criterion 1
   - [ ] Criterion 2
   ```
3. Run ralph-wrapper.sh to start implementation

---

## Summary

- **Total Stories**: 3 completed, 2 discarded
- **Completed**: 3 ✅ (RIVET-001, RIVET-002, RIVET-003)
- **Discarded**: 2 ❌ (RIVET-004, RIVET-005)
- **Pending**: 0

**Next**: Add RIVET-006 or later stories as needed
