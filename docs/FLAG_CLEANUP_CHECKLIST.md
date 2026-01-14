# Feature Flag Cleanup Checklist

## Overview

This checklist guides you through safely removing a feature flag after it has been fully rolled out and proven stable in production. Following this process ensures clean code and prevents regressions.

**When to use this**: After a feature flag has been enabled in all environments for 30+ days with no issues.

## Pre-Cleanup Verification

Before removing any flag, verify these conditions are met:

### ✅ Step 1: Verify Full Rollout Duration
- [ ] Flag has been enabled in all environments for **30+ days**
- [ ] Check flag creation date in `rivet_pro/config/feature_flags.json`
- [ ] Calculate: `today - created_date >= 30 days`
- [ ] Review `scripts/feature_flags/flag_changes.log` for rollout history

**How to check**:
```bash
# View flag configuration
python scripts/feature_flags/toggle_flag.py --list | grep your-flag-name

# Check change log
cat scripts/feature_flags/flag_changes.log | grep your-flag-name
```

### ✅ Step 2: Monitor for Errors
- [ ] No errors related to the flagged feature in the last 30 days
- [ ] Check application logs for warnings or exceptions
- [ ] Review error tracking service (if configured)
- [ ] Verify no support tickets related to the feature

**How to check**:
```bash
# Search logs for errors related to the feature
grep -i "error.*your-feature" /var/log/rivet_pro.log | grep -v "test"

# Check recent errors (last 30 days)
find /var/log -name "rivet_pro*.log" -mtime -30 -exec grep -i "error.*your-feature" {} \;
```

### ✅ Step 3: Confirm Flag State
- [ ] Flag `default_enabled` is `true` in config
- [ ] All environments (dev, stage, prod) have flag ON
- [ ] No environment overrides in `.env` forcing flag OFF

**How to check**:
```bash
# Validate flag configuration
python scripts/feature_flags/toggle_flag.py --validate

# Check specific flag state
python scripts/feature_flags/toggle_flag.py --list | grep your-flag-name
```

## Cleanup Steps

Once pre-verification is complete, follow these steps:

### Step 3: Remove Old Code Path
- [ ] Identify all locations where the old code path exists
- [ ] Delete the old implementation (dead code)
- [ ] Keep only the new code path

**Example**:
```python
# BEFORE (with flag):
if flags.is_enabled('rivet.migration.new_matcher'):
    result = improved_match(equipment, manual)  # Keep this
else:
    result = old_match(equipment, manual)  # DELETE THIS

# AFTER (flag removed):
result = improved_match(equipment, manual)
```

**How to do it**:
```bash
# Find all references to the flag
grep -rn "rivet.migration.new_matcher" rivet_pro/

# Edit each file and remove:
# 1. The flag check (if/else)
# 2. The old code path (else branch)
# 3. Any old helper functions only used by old path
```

### Step 4: Remove Flag Check
- [ ] Find all `if flags.is_enabled('flag-name')` checks
- [ ] Replace `if/else` with just the new code path
- [ ] Remove any imports of FeatureFlagManager if no longer needed

**Example**:
```python
# BEFORE:
from rivet_pro.core.feature_flags import FeatureFlagManager

flags = FeatureFlagManager()

if flags.is_enabled('rivet.migration.new_matcher'):
    return new_implementation()
else:
    return old_implementation()

# AFTER:
# Remove FeatureFlagManager import if not used elsewhere
return new_implementation()
```

### Step 5: Remove Flag Definition
- [ ] Open `rivet_pro/config/feature_flags.json`
- [ ] Delete the entire flag entry
- [ ] Ensure JSON is still valid (no trailing commas)
- [ ] Validate with `python scripts/feature_flags/toggle_flag.py --validate`

**Example**:
```json
// BEFORE:
{
  "rivet.migration.new_matcher": {
    "description": "...",
    "default_enabled": true,
    ...
  },  // DELETE THIS ENTIRE BLOCK
  "rivet.experiment.other_flag": {
    ...
  }
}

// AFTER:
{
  "rivet.experiment.other_flag": {
    ...
  }
}
```

### Step 6: Remove Environment Overrides
- [ ] Open `.env.example`
- [ ] Remove or comment out the flag override example
- [ ] Check production `.env` files and remove overrides
- [ ] Verify no `.env.local` or `.env.production` has the flag

**Example**:
```bash
# BEFORE:
# RIVET_FLAG_RIVET_MIGRATION_NEW_MATCHER=true  # DELETE THIS LINE

# AFTER:
# (line removed)
```

**How to check**:
```bash
# Find all .env files with the flag
grep -r "RIVET_FLAG_YOUR_FLAG" . --include=".env*"
```

### Step 7: Update Tests
- [ ] Remove flag toggle tests (e.g., `test_flag_on`, `test_flag_off`)
- [ ] Keep behavior tests for the new implementation
- [ ] Remove fixtures for flag state setup
- [ ] Update test documentation

**Example**:
```python
# BEFORE:
@pytest.fixture
async def flag_on(monkeypatch):
    # DELETE THIS FIXTURE
    ...

async def test_new_matcher_enabled(flag_on):
    # DELETE THIS TEST
    ...

async def test_old_matcher_fallback(flag_off):
    # DELETE THIS TEST
    ...

async def test_matcher_behavior():
    # KEEP THIS - tests actual behavior
    ...

# AFTER:
async def test_matcher_behavior():
    # Tests the (now only) implementation
    ...
```

### Step 8: Document in Pull Request
- [ ] Create PR with descriptive title: `cleanup: Remove flag X after full rollout`
- [ ] Fill out PR template
- [ ] In description, note:
  - Flag name removed
  - Rollout duration (e.g., "enabled for 45 days")
  - Verification performed (logs checked, no errors)
  - Files changed
- [ ] Link to original flag creation PR (if available)

**Example PR description**:
```markdown
## Cleanup: Remove `rivet.migration.new_matcher` flag

### Summary
Removing feature flag after successful full rollout and 45 days of stable production use.

### Verification
- ✅ Enabled in all environments since 2026-01-14
- ✅ No errors in logs for 45 days
- ✅ No user-reported issues
- ✅ All automated tests passing

### Changes
- Removed old matching code path
- Deleted flag definition from `feature_flags.json`
- Removed flag override from `.env.example`
- Updated tests to remove flag toggle scenarios

### Rollout History
1. 2026-01-14: Created flag, OFF by default
2. 2026-01-21: Enabled in dev/stage
3. 2026-02-01: Enabled in prod (beta users)
4. 2026-02-07: Enabled in prod (100%)
5. 2026-03-01: Cleanup (this PR)

Closes #123 (original feature PR)
```

## Post-Cleanup Verification

After merging the cleanup PR:

### ✅ Verify Deployment
- [ ] Changes deployed to all environments
- [ ] Application starts without errors
- [ ] No warnings about missing flag definition
- [ ] Feature still works correctly (behavior unchanged)

### ✅ Update Documentation
- [ ] Add flag removal to `docs/FEATURE_FLAGS.md` (if you added it there as an example)
- [ ] Update any READMEs that mentioned the flag
- [ ] Add entry to change log with flag removal

### ✅ Monitor Post-Cleanup
- [ ] Monitor logs for 24 hours after deployment
- [ ] Check error rates haven't increased
- [ ] Verify feature usage metrics are stable
- [ ] Be ready to revert if issues arise

## Troubleshooting

### Issue: Tests failing after flag removal

**Solution**:
1. Check if any tests still reference the flag
2. Look for tests that expect both code paths
3. Update tests to only test the new (single) implementation

### Issue: Application crashes after cleanup

**Solution**:
1. Check logs for the specific error
2. Look for references to the removed flag
3. Possible causes:
   - Forgot to remove a flag check somewhere
   - Old code path was still being used unexpectedly
   - Tests weren't comprehensive enough
4. **Quick fix**: Re-add flag definition temporarily
5. **Proper fix**: Find and remove all flag references

### Issue: Feature behaves differently

**Solution**:
1. Verify old code path was actually dead code
2. Check if old path had edge case handling not in new path
3. Compare old and new implementations side-by-side
4. If needed, revert cleanup and re-evaluate

## Quick Reference

**Cleanup command sequence**:
```bash
# 1. Verify flag state
python scripts/feature_flags/toggle_flag.py --list | grep your-flag

# 2. Find all references
grep -rn "your-flag-name" rivet_pro/

# 3. Remove old code paths (manual editing)

# 4. Remove flag definition from feature_flags.json

# 5. Validate config
python scripts/feature_flags/toggle_flag.py --validate

# 6. Run tests
pytest tests/

# 7. Commit
git add -A
git commit -m "cleanup: Remove your-flag after full rollout"
```

## Related Documentation

- [Feature Flag Lifecycle](./FEATURE_FLAGS.md) - Full flag lifecycle guide
- [Branching Guide](./BRANCHING_GUIDE.md) - How to create cleanup PR
- [Migration Inventory](./MIGRATION_INVENTORY.md) - Update after cleanup

## Notes

- **Be patient**: Wait the full 30 days before cleanup
- **Be thorough**: Check every file for flag references
- **Be safe**: Keep tests for the actual feature behavior
- **Be documented**: Clear PR description helps future developers
- **Be monitoring**: Watch logs closely after cleanup deployment

**Remember**: A clean codebase is a maintainable codebase. Don't let flag debt accumulate!
