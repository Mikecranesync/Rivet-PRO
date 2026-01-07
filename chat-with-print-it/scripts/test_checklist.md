# Chat with Print - Test Checklist

Use this checklist to verify your deployment before going live.

## Prerequisites

- [ ] Database schema deployed
- [ ] All three n8n workflows imported and active
- [ ] Telegram webhook configured
- [ ] Environment variables set in n8n

## Test 1: Bot Registration

**Goal:** Verify new user registration works

1. [ ] Open Telegram and search for your bot (by username)
2. [ ] Send `/start` command
3. [ ] **Expected:** Welcome message with instructions
4. [ ] **Verify in database:**
   ```sql
   SELECT * FROM users ORDER BY created_at DESC LIMIT 1;
   ```
   - `telegram_id` matches your ID
   - `is_pro` is FALSE
   - `lookup_count` is 0
5. [ ] **Verify in Slack:** New user notification in #chat-with-print-alerts

**Status:** ⬜ Pass / ⬜ Fail

---

## Test 2: Photo Analysis (First Lookup)

**Goal:** Verify Claude Vision analysis works

1. [ ] Send a photo of an electrical panel to the bot
2. [ ] **Expected:** "Analyzing your electrical panel..." message appears
3. [ ] **Expected:** Within 30 seconds, receive detailed analysis with:
   - System type identification
   - Component list
   - Visible issues (if any)
   - Top 3 troubleshooting steps
4. [ ] **Verify in database:**
   ```sql
   SELECT * FROM lookups ORDER BY created_at DESC LIMIT 1;
   SELECT lookup_count FROM users WHERE telegram_id = YOUR_ID;
   ```
   - Lookup logged with analysis_text
   - `success` is TRUE
   - User's `lookup_count` is 1

**Status:** ⬜ Pass / ⬜ Fail

---

## Test 3: Free Tier Limit

**Goal:** Verify 10-lookup limit enforced

1. [ ] Send 9 more photos (for a total of 10)
2. [ ] **Expected:** All 10 analyses work normally
3. [ ] **Verify lookup_count:** Should be 10
4. [ ] Send an 11th photo
5. [ ] **Expected:** Upgrade prompt message instead of analysis:
   ```
   🔒 You've reached your 10 free analyses!

   Upgrade to Pro for unlimited analyses: [Stripe link]
   ```
6. [ ] **Verify in database:** No 11th lookup logged
7. [ ] **Verify in n8n:** Check executions show limit block triggered

**Status:** ⬜ Pass / ⬜ Fail

---

## Test 4: Command Handlers

**Goal:** Verify all bot commands work

### `/help` Command
1. [ ] Send `/help`
2. [ ] **Expected:** Help text with usage instructions

### `/status` Command
1. [ ] Send `/status`
2. [ ] **Expected:** Message showing:
   - Current plan (Free/Pro)
   - Lookups used this month
   - Lookups remaining (if free tier)

### `/upgrade` Command
1. [ ] Send `/upgrade`
2. [ ] **Expected:** Message with Stripe checkout link

**Status:** ⬜ Pass / ⬜ Fail

---

## Test 5: Payment Flow (Stripe)

**Goal:** Verify Pro upgrade works end-to-end

**⚠️ USE TEST MODE for this test**

1. [ ] Click upgrade link from `/upgrade` command
2. [ ] **Expected:** Stripe checkout page loads
3. [ ] Fill in test card details:
   - Card: `4242 4242 4242 4242`
   - Exp: Any future date
   - CVC: Any 3 digits
   - Email: Your test email
4. [ ] Complete checkout
5. [ ] **Expected:** Success page (or redirect if configured)
6. [ ] **Verify in Stripe Dashboard:**
   - Payment shows as "succeeded"
   - Webhook event fired: `checkout.session.completed`
7. [ ] **Verify in database:**
   ```sql
   SELECT is_pro, pro_expires_at, stripe_customer_id FROM users WHERE telegram_id = YOUR_ID;
   SELECT * FROM payments ORDER BY created_at DESC LIMIT 1;
   ```
   - `is_pro` is TRUE
   - `pro_expires_at` is set (30 days from now)
   - `stripe_customer_id` populated
   - Payment logged in `payments` table
8. [ ] **Verify in Slack:** "New Pro subscriber" notification
9. [ ] **Test unlimited access:** Send 11th photo
10. [ ] **Expected:** Analysis works (no limit for Pro users)

**Status:** ⬜ Pass / ⬜ Fail

---

## Test 6: Daily Summary Workflow

**Goal:** Verify stats aggregation and Slack reporting

**Option A: Wait for midnight UTC**
1. [ ] Wait for scheduled execution (midnight)
2. [ ] Check Slack at 12:01 AM UTC
3. [ ] **Expected:** Daily summary message with stats

**Option B: Manual trigger**
1. [ ] Open n8n UI
2. [ ] Find "Chat with Print - Daily Summary" workflow
3. [ ] Click "Execute Workflow" button
4. [ ] **Expected:** Execution succeeds
5. [ ] **Verify in Slack:** Summary message appears with:
   - New users today
   - Total lookups today
   - New Pro subscriptions
   - Revenue
6. [ ] **Verify in database:**
   ```sql
   SELECT * FROM daily_stats ORDER BY date DESC LIMIT 1;
   ```
   - Stats match actual counts

**Status:** ⬜ Pass / ⬜ Fail

---

## Test 7: Error Handling

**Goal:** Verify graceful error handling

### Test 7a: Invalid Photo
1. [ ] Send a text file (not an image) to the bot
2. [ ] **Expected:** Error message instead of crash
3. [ ] **Verify:** Bot still responds to next valid photo

### Test 7b: Very Large Photo
1. [ ] Send a very large image (10MB+)
2. [ ] **Expected:** Either processes or gives file size error
3. [ ] **Verify:** No n8n execution crash

### Test 7c: Non-Electrical Photo
1. [ ] Send a photo of something else (dog, landscape, etc.)
2. [ ] **Expected:** Analysis attempts, possibly returns "This doesn't appear to be an electrical panel"
3. [ ] **Verify:** Counts toward lookup limit (as expected)

**Status:** ⬜ Pass / ⬜ Fail

---

## Test 8: Performance

**Goal:** Verify response times

1. [ ] Send a photo
2. [ ] **Time from send to analysis:** Should be < 30 seconds
3. [ ] Check n8n execution time in workflow history
4. [ ] **Verify:** Claude API call completed in reasonable time

**Status:** ⬜ Pass / ⬜ Fail

---

## Test 9: Security

**Goal:** Verify security measures

1. [ ] **Telegram webhook secret:** Check n8n logs - no unauthorized webhook calls
2. [ ] **Stripe webhook signature:** Try sending fake webhook (should be rejected)
3. [ ] **Database:** Verify SSL connection (check for `?sslmode=require` in DATABASE_URL)
4. [ ] **API keys:** Verify not exposed in n8n workflow JSON or logs

**Status:** ⬜ Pass / ⬜ Fail

---

## Test 10: System Health

**Goal:** Verify monitoring and health checks

1. [ ] Run: `./scripts/healthcheck.sh`
2. [ ] **Expected:** All checks pass (green)
3. [ ] **Verify n8n uptime:** Should be running continuously
4. [ ] **Verify database connection:** Stable and fast

**Status:** ⬜ Pass / ⬜ Fail

---

## Summary

- **Total tests:** 10
- **Tests passed:** ___
- **Tests failed:** ___

## Go/No-Go Decision

- [ ] All critical tests passed (1-5, 7, 8)
- [ ] No active errors in n8n execution log
- [ ] Health check passes
- [ ] Monitoring (Slack) working

**Deployment status:** ⬜ READY FOR PRODUCTION / ⬜ NEEDS FIXES

## Post-Launch Monitoring

After going live, monitor for 24 hours:

- [ ] Check Slack alerts every 4 hours
- [ ] Review n8n executions for errors
- [ ] Monitor database performance
- [ ] Track first real user signups
- [ ] Verify payment flows with real transactions (test mode first!)

## Rollback Plan

If critical issues occur:

1. Deactivate Telegram webhook: `curl -X POST "https://api.telegram.org/bot$TOKEN/deleteWebhook"`
2. Deactivate n8n workflows
3. Investigate and fix
4. Re-test this checklist
5. Re-enable when ready

**Contact:** [Your support channel/email]
