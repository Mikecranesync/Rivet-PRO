# Feature Flag Lifecycle Guide

## Overview

Feature flags enable safe, gradual rollouts of new features and migrations in RIVET Pro. This guide covers the complete lifecycle from flag creation to removal.

## When to Use Feature Flags

### Use flags for:

✅ **Migrations** - Moving from old to new implementations
```python
if flags.is_enabled('rivet.migration.new_ocr_v2'):
    use_new_ocr()  # New implementation
else:
    use_old_ocr()  # Keep old working
```

✅ **Experiments** - Testing new features that might need quick rollback
```python
if flags.is_enabled('rivet.experiment.ai_suggestions'):
    show_ai_suggestions()
```

✅ **Gradual Rollouts** - Deploying to small user groups first
```python
if flags.is_enabled('rivet.rollout.new_ui'):
    load_new_ui()
else:
    load_classic_ui()
```

✅ **Kill Switches** - Emergency off switches for problematic features
```python
if not flags.is_enabled('rivet.kill_switch.expensive_feature'):
    run_expensive_operation()
```

### Don't use flags for:

❌ **Bug fixes** - Fix the bug directly, don't hide it behind a flag
❌ **Simple refactors** - If refactored code breaks, fix it
❌ **Configuration changes** - Use `.env` variables instead
❌ **Documentation updates** - These can't break production

## Flag Lifecycle

```
Create → Test → Rollout → Monitor → Remove
  ↓       ↓        ↓         ↓        ↓
 30min   1 day   1 week   2 weeks  2 weeks
                                      ↓
                        Total: ~30 days
```

### Phase 1: Create (30 minutes)

1. **Define the flag** in `rivet_pro/config/feature_flags.json`:

```json
{
  "rivet.migration.new_matcher": {
    "description": "Enable improved manual matching with LLM validation",
    "default_enabled": false,
    "category": "migration",
    "environments": {
      "dev": true,
      "stage": true,
      "prod": false
    },
    "created_date": "2026-01-14",
    "owner": "mike"
  }
}
```

2. **Wrap your code** with flag checks:

```python
from rivet_pro.core.feature_flags import FeatureFlagManager

flags = FeatureFlagManager()

if flags.is_enabled('rivet.migration.new_matcher'):
    # New code path
    result = improved_manual_match(equipment, manual)
else:
    # Old code path (keep working!)
    result = original_manual_match(equipment, manual)
```

3. **Add tests** for both code paths:

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.fixture
async def flag_off(monkeypatch):
    """Fixture to disable feature flag"""
    monkeypatch.setenv('RIVET_FLAG_RIVET_MIGRATION_NEW_MATCHER', 'false')
    from rivet_pro.core.feature_flags import FeatureFlagManager
    manager = FeatureFlagManager()
    manager.reload()
    yield manager

@pytest.fixture
async def flag_on(monkeypatch):
    """Fixture to enable feature flag"""
    monkeypatch.setenv('RIVET_FLAG_RIVET_MIGRATION_NEW_MATCHER', 'true')
    from rivet_pro.core.feature_flags import FeatureFlagManager
    manager = FeatureFlagManager()
    manager.reload()
    yield manager

@pytest.mark.asyncio
async def test_new_matcher_enabled(flag_on):
    """Test with flag ON → new behavior"""
    result = await match_equipment()
    assert result.uses_llm_validation
    assert result.method == 'llm_enhanced'

@pytest.mark.asyncio
async def test_old_matcher_fallback(flag_off):
    """Test with flag OFF → old behavior"""
    result = await match_equipment()
    assert result.uses_classic_matching
    assert result.method == 'classic_search'

@pytest.mark.asyncio
async def test_flag_toggle_no_crashes():
    """Test toggling flag mid-operation"""
    # First call with flag OFF
    os.environ['RIVET_FLAG_RIVET_MIGRATION_NEW_MATCHER'] = 'false'
    result1 = await match_equipment()
    assert result1.method == 'classic_search'

    # Toggle to ON
    os.environ['RIVET_FLAG_RIVET_MIGRATION_NEW_MATCHER'] = 'true'
    result2 = await match_equipment()
    # Should work without crashes
```

See `tests/migrations/test_manual_matcher_migration.py` for a complete example.

4. **Document in PR** using the PR template flag section

### Phase 2: Test (1 day)

1. **Enable in dev/stage** environments:

```json
{
  "environments": {
    "dev": true,
    "stage": true,
    "prod": false
  }
}
```

2. **Manual testing**:
   - Test with flag ON - new behavior works
   - Test with flag OFF - old behavior still works
   - Test toggling mid-operation - no crashes

3. **Monitor logs** for flag usage:
```
[DEBUG] Flag 'rivet.migration.new_matcher' from config: true
```

### Phase 3: Rollout (1 week)

Gradual rollout to production:

**Day 1-2: Beta users**
```bash
# Enable for specific user via env override on their instance
RIVET_FLAG_RIVET_MIGRATION_NEW_MATCHER=true
```

**Day 3-5: 50% rollout**
```json
{
  "environments": {
    "prod": true  // But monitor closely
  }
}
```

**Day 6-7: 100% rollout**
```json
{
  "default_enabled": true,
  "environments": {
    "dev": true,
    "stage": true,
    "prod": true
  }
}
```

### Phase 4: Monitor (2 weeks)

After full rollout, monitor for issues:

1. **Check error rates** - No increase in errors related to the change
2. **Watch performance** - New code performs as expected
3. **Gather feedback** - Users report no issues
4. **Verify logs** - Flag is being used correctly

If issues arise:
```json
{
  "default_enabled": false  // Quick rollback!
}
```

### Phase 5: Remove (2 weeks)

After 30 days of stable full rollout, clean up the flag:

1. **Remove old code path**:
```python
# Before (with flag):
if flags.is_enabled('rivet.migration.new_matcher'):
    result = improved_manual_match(equipment, manual)
else:
    result = original_manual_match(equipment, manual)  # DELETE THIS

# After (flag removed):
result = improved_manual_match(equipment, manual)
```

2. **Remove flag definition** from `feature_flags.json`

3. **Remove env override** from `.env.example`

4. **Update tests** - Remove flag toggle tests, keep behavior tests

5. **Document in PR**: `cleanup: Remove new_matcher flag after full rollout`

**Detailed cleanup guide**: See [FLAG_CLEANUP_CHECKLIST.md](./FLAG_CLEANUP_CHECKLIST.md) for step-by-step removal instructions.

## Flag Naming Convention

Format: `rivet.<category>.<feature_name>`

### Categories

| Category | Purpose | Example |
|----------|---------|---------|
| `migration` | Moving from old to new code | `rivet.migration.new_ocr_v2` |
| `experiment` | Testing new features | `rivet.experiment.ai_chat` |
| `rollout` | Gradual user rollouts | `rivet.rollout.premium_ui` |
| `kill_switch` | Emergency off switches | `rivet.kill_switch.heavy_compute` |

### Naming Tips

- Use lowercase with underscores: `new_feature_name`
- Be specific: `improved_ocr` not just `ocr`
- Include version if multiple migrations: `manual_matcher_v2`
- Keep it short but descriptive

## Flag Lifespan Goal

**Target: Remove within 30 days of full rollout**

Why?
- **Avoid flag debt** - Too many flags make code hard to understand
- **Keep it simple** - Less conditional logic = fewer bugs
- **Stay focused** - Old code paths waste mental energy

If a flag has been at 100% for 30+ days:
1. Schedule removal
2. Create cleanup PR
3. Delete old code path
4. Remove flag definition

## Example: Real Flag Lifecycle

### Manual Matching Migration (RIVET Pro)

**Week 1: Create**
- Created `rivet.migration.manual_matcher_v2`
- Wrapped new LLM validation code
- Tested both paths
- PR merged with flag OFF by default

**Week 2: Test**
- Enabled in dev/stage
- Manual testing completed
- All acceptance criteria met
- Ready for prod rollout

**Week 3: Rollout**
- Day 1-2: Beta user (mike@example.com) only
- Day 3-4: 10% of users
- Day 5-6: 50% of users
- Day 7: 100% of users

**Week 4-5: Monitor**
- No errors reported
- Performance improved 2x
- User feedback positive
- Flag stable

**Week 6: Remove**
- Deleted old matching code
- Removed flag from config
- Updated tests
- Clean codebase!

## Tools

### Check flag status
```bash
python scripts/feature_flags/toggle_flag.py --list
```

### Toggle a flag
```bash
python scripts/feature_flags/toggle_flag.py \
  --flag-name rivet.migration.new_ocr \
  --enable \
  --env dev
```

### Validate config
```bash
python scripts/feature_flags/toggle_flag.py --validate
```

## Troubleshooting

### Flag not working in production

1. Check env override:
```bash
echo $RIVET_FLAG_RIVET_MIGRATION_NEW_MATCHER
```

2. Verify config:
```bash
cat rivet_pro/config/feature_flags.json | grep new_matcher
```

3. Check logs:
```bash
grep "Flag 'rivet.migration.new_matcher'" /var/log/rivet_pro.log
```

### Flag causing issues

**Quick rollback**:
```json
{
  "default_enabled": false  // Turn it off immediately
}
```

Or via env:
```bash
export RIVET_FLAG_RIVET_MIGRATION_NEW_MATCHER=false
systemctl restart rivet-bot
```

## Best Practices

1. **Start with flag OFF** - Safe default, enable gradually
2. **Keep both paths** - Don't delete old code until fully rolled out
3. **Test both states** - Flag on AND flag off must work
4. **Document in PR** - Use PR template flag section
5. **Remove promptly** - Don't accumulate flag debt
6. **Use env overrides** - Quick fixes without code changes
7. **Monitor closely** - Watch for issues during rollout
8. **Clean up fast** - 30 day removal target

## Related Documentation

- [Branching Guide](./BRANCHING_GUIDE.md) - How to work with feature branches
- [Flag Cleanup Checklist](./FLAG_CLEANUP_CHECKLIST.md) - Step-by-step flag removal
- [PR Template](../.github/pull_request_template.md) - How to document flag changes

## Questions?

- **"Should I use a flag for this?"** - See "When to Use Feature Flags" above
- **"How do I remove a flag?"** - See [FLAG_CLEANUP_CHECKLIST.md](./FLAG_CLEANUP_CHECKLIST.md)
- **"Flag not working?"** - See "Troubleshooting" section
- **"Other questions?"** - Open a discussion issue
