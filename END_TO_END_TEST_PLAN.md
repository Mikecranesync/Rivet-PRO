# RIVET End-to-End Test Plan

**Objective:** Verify real data flows through the entire RIVET system correctly

**Date:** 2026-01-10
**Status:** Step 1 Complete ✓

---

## System Configuration Discovered

### Active Telegram Bots (3)
1. **@rivet_local_dev_bot** (ID: 8161680636) - Connected to Photo Bot v2 workflow
2. **@RivetCeo_bot** (ID: 7910254197) - Orchestrator bot
3. **@RivetCMMS_bot** (ID: 7855741814) - Public CMMS bot

### Active n8n Workflows (6)
1. URL Validator (Test & Production)
2. Manual Hunter
3. Photo Bot v2
4. LLM Judge
5. Test Runner

---

## STEP 1: VERIFY TELEGRAM BOT CONNECTION ✓

**Status:** COMPLETE

**Results:**
- ✓ 3 Telegram bots active and responding
- ✓ Photo Bot v2 uses @rivet_local_dev_bot (ID: 8161680636)
- ✓ Workflow is webhook-based (not polling)

**Bot Details:**
- **Username:** @rivet_local_dev_bot
- **ID:** 8161680636
- **Token:** TELEGRAM_BOT_TOKEN in .env
- **Workflow:** Photo Bot v2 (b-dRUZ6PrwkhlyRuQi7QS)
- **Telegram Link:** https://t.me/rivet_local_dev_bot

**Architecture:**
- Photo Bot v2 workflow uses WEBHOOK trigger (not Telegram Trigger)
- This means there might be a local bot running that forwards to the webhook
- Or the Telegram webhook needs to be set up to point to n8n

**Next Action Required:**
Check if local bot is running or if Telegram webhook is configured

---

## STEP 2: VERIFY BOT IS RECEIVING MESSAGES (NEXT)

**Goal:** Confirm the Telegram bot can receive and process messages

**Test:**
1. Send `/start` to @rivet_local_dev_bot
2. Check if bot responds
3. Verify message reaches n8n workflow

**Expected Result:**
- Bot should respond with help text or confirmation
- n8n execution log should show new execution

**If bot doesn't respond:**
- Check if local bot process is running
- Check Telegram webhook configuration
- Verify n8n webhook endpoint is accessible

---

## STEP 3: TEST PHOTO PROCESSING (AFTER STEP 2)

**Goal:** Send real nameplate photo and verify OCR works

**Test Data:**
- Prepare motor nameplate photo (JPG/PNG)
- Should contain: Motor name, model, specs

**Test Process:**
1. Send photo to @rivet_local_dev_bot
2. Bot should acknowledge "Analyzing photo..."
3. OCR should extract equipment data
4. Bot should return extracted information

**Verification:**
- Check n8n Photo Bot v2 execution logs
- Verify Anthropic Claude API called for OCR
- Confirm extracted data is correct

---

## STEP 4: TEST MANUAL HUNTER INTEGRATION

**Goal:** Verify equipment manual search works

**Test Process:**
1. Trigger Manual Hunter with equipment data from Step 3
2. Workflow should search for manual online
3. URLs should be validated
4. Manual should be cached/stored

**Verification:**
- Manual Hunter execution successful
- URL Validator called and returned valid URLs
- Database has manual entry

---

## STEP 5: VERIFY DATABASE PERSISTENCE

**Goal:** Confirm data is saved to Neon PostgreSQL

**Check:**
- Equipment table has new entry
- Work order can be created
- Manual URLs are stored
- OCR data is cached

**Query Database:**
```sql
SELECT * FROM equipment ORDER BY created_at DESC LIMIT 5;
SELECT * FROM work_orders ORDER BY created_at DESC LIMIT 5;
SELECT * FROM manuals ORDER BY created_at DESC LIMIT 5;
```

---

## STEP 6: COMPLETE END-TO-END TEST

**Full Flow:**
1. User sends nameplate photo to Telegram bot
2. Photo Bot v2 receives photo
3. OCR extracts equipment data (Anthropic Claude)
4. Equipment saved to database
5. Manual Hunter searches for equipment manual
6. URLs validated by URL Validator
7. Manual URLs saved to database
8. Quality judged by LLM Judge
9. Response sent back to user via Telegram

**Success Criteria:**
- ✓ Photo processed and data extracted
- ✓ Equipment created in database
- ✓ Manual found and URLs validated
- ✓ User receives complete response
- ✓ All data persisted in database
- ✓ No errors in workflow executions

---

## Current Status: STEP 1 COMPLETE

**What We Know:**
- 3 Telegram bots are active and API-reachable
- 6 n8n workflows are active with 90% success rate
- Photo Bot v2 workflow uses webhook architecture
- All webhook endpoints responding correctly

**What We Need to Verify:**
- Is a local bot process running to forward messages?
- Or is Telegram webhook configured to hit n8n directly?
- Can the bot actually receive and respond to messages?

**Next Command:**
We need to check if there's a local Python bot running that acts as a bridge between Telegram and the n8n workflows.

---

## Files Created:
- `verify_telegram_bot.py` - Bot connection verification
- `test_core_workflows.py` - Workflow health testing
- `check_workflow_errors.py` - Error analysis
- `get_all_workflow_statuses.py` - Status reporting
- `WORKFLOW_TEST_REPORT.md` - Test results
- `END_TO_END_TEST_PLAN.md` - This file
