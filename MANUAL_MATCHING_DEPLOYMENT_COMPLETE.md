# Manual Matching Deployment Complete ✅

**Date**: 2026-01-13
**Branch**: `ralph/manual-delivery`
**Commits**: `ed42af1`, `5c4fc34`, `6af32cb`

---

## ✅ Deployment Steps Completed

### 1. ✅ Database Migration Applied

**Migration**: `rivet_pro/migrations/017_manual_matching.sql`

**Applied to production database with verification**:
- ✅ `equipment_manual_searches` table created
- ✅ `manual_cache` extended with 4 new columns:
  - `llm_validated` (boolean)
  - `llm_confidence` (double precision)
  - `manual_type` (character varying)
  - `atom_id` (text) - Fixed to match knowledge_atoms schema

**Indexes created**:
- ✅ `idx_ems_equipment` - Equipment lookup
- ✅ `idx_ems_status` - Status filtering
- ✅ `idx_ems_pending` - Pending search queries
- ✅ `idx_ems_chat` - Telegram chat lookup
- ✅ `idx_ems_retry` - Retry scheduling
- ✅ `idx_manual_cache_validated` - Validated manual lookup
- ✅ `idx_manual_cache_atom` - Atom reference lookup

**Fix Applied**: Changed `atom_id` from UUID to TEXT to match existing `knowledge_atoms.atom_id` type

### 2. ✅ Dependencies Installed

**PyPDF2**: Version 3.0.1 installed and verified

**All imports successful**:
- ✅ `ManualMatcherService` imports without errors
- ✅ `ManualGapFiller` imports without errors
- ✅ All service dependencies resolved

### 3. ✅ Configuration Verified

**Environment variables confirmed**:
- ✅ `ANTHROPIC_API_KEY` - For Claude Sonnet 4.5 fallback
- ✅ `GROQ_API_KEY` - For primary LLM validation
- ✅ `GOOGLE_API_KEY` - For Gemini Vision OCR
- ✅ `TELEGRAM_BOT_TOKEN` - For bot notifications
- ✅ `DATABASE_URL` - Connected to Neon PostgreSQL

**Code integration verified**:
- ✅ PhotoService has `_trigger_manual_search()` method
- ✅ PhotoService integrated with ManualMatcherService
- ✅ Telegram bot has `/manual` command handler
- ✅ Telegram bot has verification callback handler

---

## 🚀 Ready to Test

The system is now fully deployed and ready for end-to-end testing.

### How to Start the Bot

```bash
cd /opt/Rivet-PRO  # or your deployment directory
python -m rivet_pro.adapters.telegram
```

**Or if using systemd**:
```bash
sudo systemctl restart rivet-bot
```

---

## 🧪 Testing Scenarios

### Scenario 1: New Equipment Photo with Manual Search

**Test**: Send equipment photo → Verify async manual search

1. Send equipment photo via Telegram (e.g., Allen Bradley 2080-LC20)
2. **Expected**: Bot responds in <3 seconds with equipment details
3. Check database:
   ```sql
   SELECT * FROM equipment_manual_searches
   WHERE search_status IN ('pending', 'searching')
   ORDER BY created_at DESC LIMIT 1;
   ```
4. **Expected**: Record created with `search_status='pending'` or `'searching'`
5. Wait 45-60 seconds
6. **Expected**: Bot sends "📘 Manual Found!" notification with confidence
7. Check database:
   ```sql
   SELECT search_status, best_manual_url, best_manual_confidence, manuals_found
   FROM equipment_manual_searches
   ORDER BY created_at DESC LIMIT 1;
   ```
8. **Expected**:
   - `search_status='completed'`
   - `best_manual_url` populated
   - `best_manual_confidence >= 0.85`
   - `manuals_found` JSONB array with manual details

### Scenario 2: Instant Manual Retrieval

**Test**: Use `/manual` command for instant lookup

1. Run `/manual EQ-2025-0142` (use actual equipment number from scenario 1)
2. **Expected**: Response in <1 second with:
   - Manual URL
   - Manual title
   - Confidence indicator (✅ for ≥0.90, ⚠️ for 0.80-0.89)
   - Manual type (user_manual, service_manual, etc.)
3. Check database:
   ```sql
   SELECT access_count, last_accessed
   FROM manual_cache
   WHERE llm_validated = TRUE
   ORDER BY last_accessed DESC LIMIT 1;
   ```
4. **Expected**: `access_count` incremented, `last_accessed` updated

### Scenario 3: Inconclusive Manual (Human Verification)

**Test**: Manual with 0.70-0.85 confidence triggers human verification

1. Trigger search for equipment with medium-confidence manual (may need specific equipment)
2. **Expected**: Bot sends message with inline keyboard:
   ```
   📘 Possible Manual Found (78% confidence)

   [Title of manual]
   URL: [manual URL]

   Is this the correct manual for your equipment?
   [✅ Yes, it's correct] [❌ No, keep searching]
   ```
3. Click "✅ Yes, it's correct"
4. **Expected**: Message updates to "✅ Thank you! Manual verified..."
5. Check database:
   ```sql
   SELECT best_manual_confidence, requires_human_verification, search_status
   FROM equipment_manual_searches
   WHERE requires_human_verification = FALSE
       AND best_manual_confidence >= 0.90
   ORDER BY updated_at DESC LIMIT 1;
   ```
6. **Expected**: Confidence updated to 0.95, SPEC atom created

### Scenario 4: Failed Search with Retry

**Test**: Equipment without manual triggers retry logic

1. Send photo of obscure/uncommon equipment
2. **Expected**: Immediate response with equipment identified
3. Wait 60 seconds
4. Check database:
   ```sql
   SELECT search_status, retry_count, next_retry_at, retry_reason
   FROM equipment_manual_searches
   WHERE search_status = 'retrying'
   ORDER BY created_at DESC LIMIT 1;
   ```
5. **Expected**:
   - `search_status='retrying'`
   - `retry_count=1`
   - `next_retry_at` ≈ 1 hour from now
   - `retry_reason` populated

### Scenario 5: Background Gap Filler

**Test**: Manual gap filler processes high-priority equipment

1. Run gap filler manually:
   ```bash
   python scripts/run_manual_gap_filler.py
   ```
2. **Expected output**:
   ```
   ✅ Processed 10 equipment
   📘 Found X manuals
   ✅ Validated Y manuals
   🔍 Resolved Z knowledge gaps
   ```
3. Check database:
   ```sql
   -- Check manuals found by gap filler
   SELECT equipment_id, best_manual_url, best_manual_confidence
   FROM equipment_manual_searches
   WHERE telegram_chat_id = 0  -- Background job indicator
       AND search_status = 'completed'
       AND created_at > NOW() - INTERVAL '10 minutes';

   -- Check resolved gaps
   SELECT COUNT(*)
   FROM knowledge_gaps
   WHERE research_status = 'completed'
       AND resolved_atom_id IS NOT NULL
       AND updated_at > NOW() - INTERVAL '10 minutes';
   ```
4. **Expected**: High-priority equipment have validated manuals

---

## 📊 Monitoring Queries

### Check Search Status Distribution
```sql
SELECT search_status, COUNT(*) as count
FROM equipment_manual_searches
GROUP BY search_status
ORDER BY count DESC;
```

### Check Validation Success Rate
```sql
SELECT
    COUNT(*) FILTER (WHERE llm_validated = TRUE)::float /
    NULLIF(COUNT(*), 0) * 100 as validation_rate_pct,
    AVG(llm_confidence) FILTER (WHERE llm_validated = TRUE) as avg_confidence
FROM manual_cache
WHERE llm_confidence IS NOT NULL;
```

### Check KB Coverage
```sql
SELECT
    COUNT(DISTINCT e.id)::float /
    (SELECT COUNT(*) FROM cmms_equipment) * 100 as coverage_pct
FROM cmms_equipment e
JOIN manual_cache mc
    ON LOWER(e.manufacturer) = LOWER(mc.manufacturer)
    AND LOWER(e.model_number) = LOWER(mc.model)
WHERE mc.llm_validated = TRUE;
```

### Check Recent Manual Searches
```sql
SELECT
    e.equipment_number,
    e.manufacturer,
    e.model_number,
    ems.search_status,
    ems.best_manual_confidence,
    ems.search_duration_ms,
    ems.created_at
FROM equipment_manual_searches ems
JOIN cmms_equipment e ON e.id = ems.equipment_id
ORDER BY ems.created_at DESC
LIMIT 10;
```

### Check Retry Queue
```sql
SELECT
    e.equipment_number,
    ems.retry_count,
    ems.next_retry_at,
    ems.retry_reason
FROM equipment_manual_searches ems
JOIN cmms_equipment e ON e.id = ems.equipment_id
WHERE ems.search_status = 'retrying'
    AND ems.next_retry_at > NOW()
ORDER BY ems.next_retry_at ASC;
```

---

## 🔧 Optional: Setup Cron Job

For automated background gap filling:

```bash
crontab -e

# Add this line (runs daily at 2 AM):
0 2 * * * cd /opt/Rivet-PRO && /opt/Rivet-PRO/venv/bin/python scripts/run_manual_gap_filler.py >> /var/log/rivet/gap_filler.log 2>&1
```

---

## 📝 Deployment Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Migration 017 | ✅ Applied | atom_id type fixed to TEXT |
| PyPDF2 3.0.1 | ✅ Installed | PDF parsing ready |
| ManualMatcherService | ✅ Deployed | 24KB, 600+ lines |
| ManualGapFiller | ✅ Deployed | 10KB, 300+ lines |
| PhotoService Integration | ✅ Complete | Async trigger added |
| /manual Command | ✅ Registered | Instant retrieval |
| Callback Handler | ✅ Registered | Human verification |
| Database Schema | ✅ Verified | All tables and columns exist |
| Environment | ✅ Configured | All API keys present |

---

## 🎯 Success Metrics (Track Over 30 Days)

| Metric | Target | Query |
|--------|--------|-------|
| **Coverage** | 70% of equipment have manuals | See monitoring query above |
| **Accuracy** | 80%+ LLM validation accuracy | `AVG(llm_confidence) >= 0.80` |
| **Speed** | 95% searches complete <60s | `COUNT(*) FILTER (WHERE search_duration_ms < 60000)` |
| **KB Growth** | 450+ SPEC atoms (15/day) | `COUNT(*) FROM knowledge_atoms WHERE source_type='manual_matcher'` |
| **Reusability** | 40% KB hit rate | Track `/manual` command usage vs searches |
| **User Satisfaction** | <5% manual search failures | `COUNT(*) FILTER (WHERE status='failed')` |

---

## 🐛 Troubleshooting

### Issue: No manual notification received

**Check**:
```sql
SELECT * FROM equipment_manual_searches
WHERE telegram_chat_id = [YOUR_CHAT_ID]
ORDER BY created_at DESC LIMIT 1;
```

**Solutions**:
- If `search_status='failed'`: Check `error_message` column
- If `search_status='searching'` for >2 minutes: May be stuck, check bot logs
- If `search_status='no_manual_found'`: Equipment manual not available online

### Issue: Import errors when starting bot

**Solution**:
```bash
pip install PyPDF2>=3.0.0
python -c "from rivet_pro.core.services.manual_matcher_service import ManualMatcherService"
```

### Issue: Migration conflicts

**Check existing columns**:
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'manual_cache';
```

If columns already exist, migration will skip them (uses `ADD COLUMN IF NOT EXISTS`).

---

## 📚 Documentation Files

- `MANUAL_MATCHING_IMPLEMENTATION_COMPLETE.md` - Full implementation details
- `MANUAL_MATCHING_DEPLOYMENT_COMPLETE.md` - This file
- `scripts/apply_migration.py` - Migration helper script
- `scripts/verify_manual_matching_setup.py` - Setup verification
- `scripts/run_manual_gap_filler.py` - Gap filler CLI

---

## ✨ What's Next

1. **Test all 5 scenarios** above to verify system works end-to-end
2. **Monitor performance** using the monitoring queries
3. **Review logs** for any errors during first 24 hours
4. **Adjust confidence thresholds** if needed (currently 0.70/0.85)
5. **Setup cron job** for automated gap filling
6. **Track success metrics** over 30 days

---

**Deployment completed successfully at**: 2026-01-13 18:23 PST

**Ready for production testing!** 🚀
