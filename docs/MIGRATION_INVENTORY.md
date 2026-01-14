# RIVET Pro Module Migration Inventory

## Overview

This document catalogs all major modules in RIVET Pro, their stability rating, and migration priorities for implementing feature flag patterns.

Last updated: 2026-01-14

## Module Categories

- **Core**: Always-on critical functionality
- **Migrations**: Candidates for feature flag gating
- **Experiments**: Risky or experimental features

## Service Modules Inventory

### Core Services (Always On)

#### equipment_service.py
- **Stability**: Stable
- **Last Major Change**: 2026-01-05
- **Dependencies**: Database, equipment_taxonomy
- **Test Coverage**: Unknown
- **Purpose**: Equipment CRUD operations and lookup
- **Migration Priority**: Low (core functionality)
- **Notes**: Fundamental to CMMS operation, should remain always-on

#### work_order_service.py
- **Stability**: Stable
- **Last Major Change**: 2026-01-05
- **Dependencies**: Database, equipment_service
- **Test Coverage**: Unknown
- **Purpose**: Work order management
- **Migration Priority**: Low (core functionality)
- **Notes**: Critical workflow component

#### equipment_taxonomy.py
- **Stability**: Stable
- **Last Major Change**: 2026-01-05
- **Dependencies**: None
- **Test Coverage**: Unknown
- **Purpose**: Equipment classification and categorization
- **Migration Priority**: Low (reference data)
- **Notes**: Static taxonomy definitions

#### sme_service.py
- **Stability**: Stable
- **Last Major Change**: 2026-01-05
- **Dependencies**: Database
- **Test Coverage**: Unknown
- **Purpose**: Subject matter expert routing
- **Migration Priority**: Medium
- **Notes**: Could benefit from experimental improvements

### Migration Candidates (Need Feature Flags)

#### manual_matcher_service.py ⭐ MIGRATED
- **Stability**: Experimental → Stable
- **Last Major Change**: 2026-01-14 (migrated with flag!)
- **Dependencies**: LLM providers, database
- **Test Coverage**: In progress (STABLE-011)
- **Purpose**: Match equipment to manuals using LLM validation
- **Migration Status**: ✅ **MIGRATED** with feature flag
- **Current Behavior**:
  - Flag OFF: Classic search without LLM validation
  - Flag ON: LLM-enhanced matching with multi-source search
- **Flag**: `rivet.migration.manual_matcher_v2`
- **Rollout Status**:
  - Dev: ✅ ON
  - Stage: ✅ ON
  - Prod: ❌ OFF (gradual rollout planned)
- **Notes**: Successfully migrated! Demonstrates v1 → v2 migration pattern

#### ocr_service.py
- **Stability**: Stable → Experimental
- **Last Major Change**: 2026-01-13
- **Dependencies**: Gemini Vision API, file storage
- **Test Coverage**: Unknown
- **Purpose**: Extract text from nameplate photos
- **Migration Priority**: HIGH
- **Current Behavior**: Uses Gemini Vision for OCR
- **Migration Goal**:
  - Experiment with new OCR engines
  - A/B test different vision models
  - Flag: `rivet.experiment.new_ocr`
- **Notes**: Good candidate for experimental flag gating

#### photo_service.py
- **Stability**: Stable
- **Last Major Change**: 2026-01-13
- **Dependencies**: File storage, OCR service, Telegram
- **Test Coverage**: Unknown
- **Purpose**: Handle photo uploads and processing
- **Migration Priority**: MEDIUM
- **Current Behavior**: Orchestrates photo → OCR → equipment workflow
- **Migration Goal**: Could experiment with different processing pipelines
- **Notes**: Recently modified, might benefit from migration pattern

### Experimental Services

#### feedback_service.py
- **Stability**: Experimental
- **Last Major Change**: 2026-01-13 (new!)
- **Dependencies**: Database, Telegram
- **Test Coverage**: Unknown
- **Purpose**: Collect and process user feedback
- **Migration Priority**: LOW (already new)
- **Notes**: Newly added, could use kill switch flag

#### kb_analytics_service.py
- **Stability**: Experimental
- **Last Major Change**: 2026-01-13 (new!)
- **Dependencies**: Database
- **Test Coverage**: Unknown
- **Purpose**: Knowledge base analytics and insights
- **Migration Priority**: LOW (already new)
- **Notes**: New feature, good candidate for experiment flag

#### stripe_service.py
- **Stability**: Stable
- **Last Major Change**: 2026-01-13
- **Dependencies**: Stripe API, database
- **Test Coverage**: Unknown
- **Purpose**: Payment processing and subscription management
- **Migration Priority**: LOW (financial critical)
- **Notes**: Payment systems should not use experimental flags

#### usage_service.py
- **Stability**: Stable
- **Last Major Change**: 2026-01-13
- **Dependencies**: Database
- **Test Coverage**: Unknown
- **Purpose**: Track feature usage and user activity
- **Migration Priority**: LOW
- **Notes**: Analytics service, stable implementation

#### alerting_service.py
- **Stability**: Stable
- **Last Major Change**: 2026-01-13
- **Dependencies**: Telegram, Slack
- **Test Coverage**: Unknown
- **Purpose**: Send alerts and notifications
- **Migration Priority**: LOW
- **Notes**: Critical communication path, should remain stable

#### manual_service.py
- **Stability**: Stable
- **Last Major Change**: 2026-01-13
- **Dependencies**: Database, file storage
- **Test Coverage**: Unknown
- **Purpose**: Equipment manual management and storage
- **Migration Priority**: MEDIUM
- **Notes**: Could experiment with different storage strategies

## Migration Priority Order

### Phase 1: Demo Migration (STABLE-010)
1. **manual_matcher_service.py** ⭐
   - Create flag: `rivet.migration.manual_matcher_v2`
   - Wrap entry points with flag checks
   - Keep old matching logic intact
   - Demonstrate migration pattern

### Phase 2: High-Value Migrations (Future)
2. **ocr_service.py**
   - Flag: `rivet.experiment.new_ocr`
   - Test alternative OCR engines

3. **photo_service.py**
   - Flag: `rivet.experiment.photo_pipeline_v2`
   - Experiment with processing optimizations

### Phase 3: Low-Priority Migrations (Future)
4. **manual_service.py**
   - Flag: `rivet.experiment.manual_storage_v2`
   - Test different storage backends

5. **sme_service.py**
   - Flag: `rivet.experiment.smart_routing`
   - Experiment with AI-powered routing

## Demo Migration Candidate: manual_matcher_service.py

### Why This Module?

✅ **Perfect for demo** because:
- Recently implemented (2026-01-13)
- Contains both old and new logic paths
- Has clear v1 → v2 migration story
- Uses LLM features (good flag candidate)
- Self-contained service module
- Non-critical (can safely experiment)

### Current Behavior

The `manual_matcher_service.py` provides:
- Manual-to-equipment matching
- LLM-powered validation
- Confidence scoring
- Match result ranking

### Migration Plan

1. **Create flag**: `rivet.migration.manual_matcher_v2`
2. **Wrap entry point**:
   ```python
   from rivet_pro.core.feature_flags import FeatureFlagManager

   flags = FeatureFlagManager()

   def match_manual_to_equipment(equipment, manual):
       if flags.is_enabled('rivet.migration.manual_matcher_v2'):
           # New: LLM-enhanced matching
           return llm_enhanced_match(equipment, manual)
       else:
           # Old: Classic keyword matching
           return classic_keyword_match(equipment, manual)
   ```

3. **Test both paths**:
   - Flag OFF: Classic matching works
   - Flag ON: LLM matching works
   - Toggle mid-operation: No crashes

4. **Gradual rollout**:
   - Week 1: Dev/Stage only
   - Week 2: Beta users
   - Week 3: 100% rollout
   - Week 4: Remove flag and old code

### Expected Benefits

- ✅ Demonstrates migration pattern for team
- ✅ Enables A/B testing of matching algorithms
- ✅ Provides quick rollback if issues arise
- ✅ Shows proper flag lifecycle management
- ✅ Creates tests for flagged code paths

## Notes

- Modules marked with ⭐ are top migration priorities
- Recently modified modules (2026-01-13) show active development
- Core modules should generally avoid experimental flags
- Financial/payment modules (stripe_service) should not use experiment flags
- Communication modules (alerting_service) should remain stable

## Next Steps

1. ✅ Complete this inventory (STABLE-009)
2. ⏭️ Implement demo migration for manual_matcher_service (STABLE-010)
3. ⏭️ Add tests for both flag states (STABLE-011)
4. 📅 Future: Migrate other high-priority modules

## Related Documentation

- [Feature Flag Lifecycle](./FEATURE_FLAGS.md)
- [Flag Cleanup Checklist](./FLAG_CLEANUP_CHECKLIST.md)
- [Branching Guide](./BRANCHING_GUIDE.md)
