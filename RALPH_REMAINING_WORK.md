# Ralph Remaining Work - Complete Status

**Date**: 2026-01-13
**Branch**: ralph/manual-delivery
**Status**: KB stories complete, other stories pending

---

## ✅ COMPLETED - KB Self-Learning System (5 stories)

### Recently Completed (2026-01-13)
- ✅ **KB-007**: Knowledge Base Analytics Service - COMPLETE
- ✅ **KB-008**: /kb_stats Admin Command - COMPLETE
- ✅ **KB-006**: Create Atoms from Approved Ralph Fixes - COMPLETE
- ✅ **CRITICAL-KB-001**: Auto-create atoms from OCR - COMPLETE
- ✅ **KB-002**: Create SPEC atoms after manual search - COMPLETE

**Implementation Details**:
- ~1,200 lines of code added
- 6 commits created
- All tests passing locally
- Ready for VPS deployment

---

## ⬜ PENDING - KB Self-Learning System (3 stories)

### KB-001: Add atom_id column to interactions table
**Priority**: P10 (High)
**Status**: ⬜ TODO
**Complexity**: Simple database migration

**Description**: Database schema changes to link interactions with knowledge atoms.

**Required Changes**:
- Add `atom_id` UUID column to `interactions` table (FK to knowledge_atoms)
- Add `atom_created` BOOLEAN flag to interactions
- Add `source_interaction_id` to knowledge_atoms table
- Add `created_by` VARCHAR(20) to knowledge_atoms
- Create indexes for performance

**Why Needed**: Foundation for tracking which interactions create which atoms.

---

### KB-003: Search KB before external search
**Priority**: P9 (High)
**Status**: ⬜ TODO
**Complexity**: Medium integration

**Description**: Check knowledge base BEFORE calling external Tavily search.

**Implementation**:
- Add `_search_knowledge_base()` method in bot.py
- Call BEFORE `manual_service.search_manual()`
- Use semantic search with OpenAI embeddings
- Confidence thresholds:
  - ≥0.85: Use KB result, skip external search
  - 0.40-0.85: Show KB + trigger external search
  - <0.40: Normal external search
- Increment usage_count when KB atom used

**Impact**: Reduce latency from 3+ seconds to <500ms for KB hits.

---

### KB-004: Create equipment atom after OCR
**Priority**: P8 (Medium)
**Status**: ⬜ TODO
**Complexity**: Medium integration

**Description**: Create EQUIPMENT atom after successful OCR extraction.

**Implementation**:
- After OCR identifies equipment (manufacturer, model)
- Create atom with type=EQUIPMENT
- Include: manufacturer, model, equipment_type, confidence
- Store in knowledge_atoms table
- Future queries can benefit from OCR learnings

---

### KB-005: Detect gaps on low-confidence responses
**Priority**: P7 (Medium)
**Status**: ⬜ TODO
**Complexity**: Simple analytics

**Description**: Track knowledge gaps when confidence is low.

**Implementation**:
- When KB search returns confidence <0.40
- Insert row into knowledge_gaps table
- Track: manufacturer, model, equipment_type, gap_reason
- Ralph can later research these gaps

---

## ⬜ PENDING - RALPH Process Optimization (6 stories)

### RALPH-P1: Role-Based Command Filtering
**Priority**: P1
**Status**: ⬜ TODO
**Complexity**: Medium
**Impact**: 40% token reduction

**Description**: Filter Telegram commands by user subscription tier.

**Implementation**:
- Create `@role_required` decorator in bot.py
- Free users: /start, /equip, /wo only
- Pro users: + /stats, /manual
- Admin users: + /admin commands
- Show upgrade message for blocked commands

---

### RALPH-P2: Progressive Disclosure for /equip search
**Priority**: P1
**Status**: ⬜ TODO
**Complexity**: Simple
**Impact**: 60% token reduction

**Description**: Return summaries first, full details on request.

**Implementation**:
- `/equip search motor` → max 10 results (ID | mfg | model)
- `/equip detail EQ-2025-001` → full equipment details
- Search < 500 tokens, Detail < 2000 tokens

---

### RALPH-P3: Bundle Photo Workflow
**Priority**: P0 (Critical)
**Status**: ⬜ TODO
**Complexity**: Medium
**Impact**: 50% token reduction, 70% latency reduction

**Description**: Combine Bot→n8n→Python into single `process_photo()` function.

**Implementation**:
- Create `photo_service.py` with `process_photo()`
- Combines: OCR, equipment match, DB save, usage tracking
- Returns: {equipment_id, manual_url, message}
- Eliminate n8n webhook callback
- Direct integration reduces round trips

---

### RALPH-P4: Context-Rich Error Messages
**Priority**: P1
**Status**: ⬜ TODO
**Complexity**: Simple

**Description**: All errors include 2-3 action suggestions.

**Format**: "⚠️ [Problem]. Try: 1) [Action], 2) [Action], 3) [Action]"

---

### RALPH-P5: Response Template with Next Actions
**Priority**: P1
**Status**: ⬜ TODO
**Complexity**: Simple

**Description**: All responses include "What's next?" section.

**Implementation**:
- Create `format_with_actions()` helper
- All success messages include suggested next actions
- Reduce user confusion, improve engagement

---

### RALPH-P6: Token Usage Dashboard
**Priority**: P2
**Status**: ⬜ TODO
**Complexity**: Medium

**Description**: `/admin stats` shows token usage per command/user/time.

**Implementation**:
- Add `token_count` column to usage_tracking table
- Track tokens per command execution
- Admin dashboard with: total, avg, top users
- Admin-only access

---

## ⬜ PENDING - RIVET MVP Stories (Multiple)

### RIVET-007: n8n Gemini Credential Verification
**Priority**: P0 - MVP Blocker
**Status**: 🔧 MANUAL TASK
**Complexity**: Simple (n8n UI)

**Description**: Verify n8n Photo Bot v2 has valid Gemini API credential.

**Manual Steps**:
1. Log into n8n at http://72.60.175.144:5678
2. Open Photo Bot v2 workflow (7LMKcMmldZsu1l6g)
3. Check Gemini Vision node credential
4. Test workflow with sample photo
5. Verify no credential errors

---

### RIVET-009: Ralph Workflow Database Credentials
**Priority**: P1
**Status**: 🔧 MANUAL TASK
**Complexity**: Simple (n8n UI)

**Description**: Wire Neon PostgreSQL credentials to Ralph Main Loop workflow.

**Manual Steps**:
1. Log into n8n at http://72.60.175.144:5678
2. Open Ralph Main Loop workflow
3. Create Neon PostgreSQL credential (if not exists)
4. Wire credential to all 7 Postgres nodes
5. Test workflow execution

---

### Other RIVET Stories
- Multiple RIVET-001 through RIVET-013 stories in @fix_plan.md
- Some completed (RIVET-006, RIVET-008, RIVET-010, RIVET-011)
- Some manual tasks (RIVET-007, RIVET-009)
- Some discarded (RIVET-004, RIVET-005)

**See**: `scripts/ralph-claude-code/@fix_plan.md` for complete list

---

## 🔄 RALPH BOT Stories (Completed)

### RALPH-BOT-1, RALPH-BOT-2, RALPH-BOT-3
**Status**: ✅ COMPLETE (commit d9e019d)
**Description**: Superior bot error handling and reliability

These were completed in previous Ralph runs.

---

## 📊 Summary

### By Category

| Category | Total | Complete | Pending | Manual |
|----------|-------|----------|---------|--------|
| KB Self-Learning | 8 | 5 | 3 | 0 |
| CRITICAL-KB | 1 | 1 | 0 | 0 |
| RALPH Process | 6 | 0 | 6 | 0 |
| RALPH Bot | 3 | 3 | 0 | 0 |
| RIVET MVP | 11+ | 7 | 2 | 2 |
| **TOTAL** | **29+** | **16** | **11** | **2** |

### By Priority

| Priority | Stories | Description |
|----------|---------|-------------|
| P0 (Critical) | 3 | RALPH-P3, RIVET-007, RIVET-009 |
| P1 (High) | 7 | KB-001, RALPH-P1-P5, RIVET-009 |
| P2 (Medium) | 2 | KB-003-005, RALPH-P6 |

---

## 🚀 Recommended Execution Order

### Phase 1: Deploy KB Features (Immediate)
1. Deploy completed KB features to VPS (KB-007, KB-008, KB-006, CRITICAL-KB-001, KB-002)
2. Test `/kb_stats` command in production
3. Verify atoms are being created

### Phase 2: Complete KB Foundation (Next)
1. **KB-001**: Database schema updates (1-2 hours)
2. **KB-003**: Search KB before external (2-3 hours)
3. **KB-004**: Create equipment atoms (1-2 hours)
4. **KB-005**: Gap detection (1 hour)

**Estimated**: 5-8 hours total

### Phase 3: Manual n8n Tasks
1. **RIVET-007**: Verify Gemini credential (15 mins)
2. **RIVET-009**: Wire Ralph database credentials (30 mins)

**Estimated**: 45 minutes total

### Phase 4: Process Optimization
1. **RALPH-P3**: Bundle photo workflow (4 hours) ⭐ Biggest impact
2. **RALPH-P2**: Progressive disclosure (2 hours)
3. **RALPH-P4**: Error messages (1 hour)
4. **RALPH-P5**: Next actions (1 hour)
5. **RALPH-P1**: Role filtering (3 hours)
6. **RALPH-P6**: Token dashboard (2 hours)

**Estimated**: 13 hours total

---

## 💡 Key Insights

### High-Impact, Low-Effort
- **KB-003**: Search KB first (2-3 hours, massive latency improvement)
- **RALPH-P4**: Context-rich errors (1 hour, better UX)
- **RALPH-P5**: Next actions (1 hour, better engagement)

### Critical Path to Production
1. Deploy current KB features ✅
2. Complete KB-001 (database foundation)
3. Complete KB-003 (use the KB!)
4. Complete RALPH-P3 (bundle workflow)
5. Manual n8n tasks

This gets the self-learning KB working end-to-end in production.

### Token/Latency Wins
- **RALPH-P3**: 50% token ↓, 70% latency ↓
- **RALPH-P2**: 60% token ↓
- **RALPH-P1**: 40% token ↓
- **KB-003**: 3s → 500ms latency for KB hits

**Combined**: Could achieve 60-70% token reduction, 75% latency reduction.

---

## 🎯 Next Steps for Ralph

### Immediate (Today)
1. Deploy KB-007, KB-008, KB-006, CRITICAL-KB-001, KB-002 to VPS
2. Test in production Telegram bot
3. Verify `/kb_stats` command works

### Short Term (This Week)
1. Implement KB-001 (database schema)
2. Implement KB-003 (search KB first)
3. Complete manual n8n tasks (RIVET-007, RIVET-009)

### Medium Term (Next Week)
1. Implement RALPH-P3 (bundle photo workflow)
2. Implement KB-004, KB-005 (equipment atoms, gap detection)
3. Implement RALPH-P2, P4, P5 (UX improvements)

### Long Term (Future)
1. RALPH-P1, P6 (role filtering, token dashboard)
2. Research agent to fill knowledge gaps
3. Additional RIVET stories as needed

---

**Last Updated**: 2026-01-13
**Ralph Status**: Ready for next iteration
**Deployment**: KB features awaiting VPS deployment
