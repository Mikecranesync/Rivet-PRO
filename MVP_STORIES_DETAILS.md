# RIVET-PRO MVP Stories - Ready For Implementation

**Status:** All stories loaded and ready
**Total Stories:** 5
**Estimated Time:** 2-3 hours to implement all
**Estimated Cost:** $0.30-0.50 (if using AI directly)

---

## Story 1: RIVET-001 - Usage Tracking System 🔢

**Priority:** 1 (HIGHEST)
**AI Model:** Claude Sonnet 4 (most capable)
**Status:** ⬜ TODO

### Description
Track equipment lookups per user for freemium enforcement.

### What This Does
Implements the foundation of your freemium business model by counting how many times each user uses the photo analysis feature.

### Acceptance Criteria
1. ✅ Track each photo upload as one lookup
2. ✅ Store user_id and timestamp in Neon
3. ✅ Create get_usage_count function
4. ✅ Block at 10 free lookups with upgrade message

### Technical Implementation Plan
- **Database Changes:**
  - Add `lookups` table or `user_lookups` counter column
  - Track: user_id, timestamp, photo_id, analysis_result_id

- **Backend:**
  - Create `UsageTracker` class or module
  - Implement `increment_lookup_count(user_id)` function
  - Implement `get_usage_count(user_id)` function
  - Implement `can_user_lookup(user_id)` function (returns true if < 10)

- **Integration Points:**
  - Hook into photo analysis workflow
  - Before processing: check `can_user_lookup()`
  - After successful analysis: call `increment_lookup_count()`
  - If blocked: return upgrade message

### Files Likely To Change
- `rivet_pro/core/usage_tracker.py` (NEW)
- `rivet_pro/migrations/011_usage_tracking.sql` (NEW)
- `rivet_pro/adapters/telegram/bot.py` (MODIFY - add checks)
- `rivet_pro/adapters/web/routes/analysis.py` (MODIFY - add checks)

### Testing
- New user starts with 0 lookups
- Counter increments after photo analysis
- User blocked at 10 lookups
- Upgrade message shown correctly

---

## Story 2: RIVET-002 - Stripe Payment Integration 💳

**Priority:** 2
**AI Model:** Claude Sonnet 4
**Status:** ⬜ TODO
**Depends On:** RIVET-001 (usage tracking)

### Description
Connect Stripe for Pro tier at $29/month.

### What This Does
Implements the payment system so users can upgrade from free to Pro tier.

### Acceptance Criteria
1. ✅ Create Stripe product/price for Pro $29/mo
2. ✅ Implement checkout session endpoint
3. ✅ Handle payment success webhook
4. ✅ Update user subscription status
5. ✅ Send Telegram confirmation

### Technical Implementation Plan
- **Stripe Setup (Manual):**
  - Create product in Stripe Dashboard: "RIVET Pro"
  - Create recurring price: $29/month
  - Get price_id (e.g., `price_abc123`)
  - Set up webhook endpoint in Stripe Dashboard

- **Backend:**
  - Add `stripe` Python library to requirements
  - Create `StripeService` class
  - Implement `/api/stripe/checkout` endpoint
  - Implement `/api/stripe/webhook` endpoint
  - Add `is_pro` flag to users table

- **Telegram Integration:**
  - Add `/upgrade` command
  - Generate Stripe checkout link
  - Send link to user
  - Handle webhook events (payment success)
  - Send confirmation message

### Files Likely To Change
- `requirements.txt` (ADD stripe library)
- `rivet_pro/core/stripe_service.py` (NEW)
- `rivet_pro/migrations/012_user_subscriptions.sql` (NEW)
- `rivet_pro/adapters/web/routes/stripe.py` (NEW)
- `rivet_pro/adapters/telegram/bot.py` (ADD /upgrade command)
- `.env` (ADD Stripe keys)

### Environment Variables Needed
```env
STRIPE_SECRET_KEY=sk_test_xxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxx
STRIPE_PRICE_ID=price_xxxx
```

### Testing
- `/upgrade` command generates valid checkout link
- Payment success updates user to Pro
- Telegram confirmation sent
- Webhook signature validation works

---

## Story 3: RIVET-003 - Free Tier Limit Enforcement 🚫

**Priority:** 3
**AI Model:** Claude Sonnet 4
**Status:** ⬜ TODO
**Depends On:** RIVET-001, RIVET-002

### Description
Block lookups at 10 and show upgrade prompt.

### What This Does
Enforces the free tier limits and converts free users to paid by showing upgrade CTA at the right moment.

### Acceptance Criteria
1. ✅ Check usage before processing photo
2. ✅ Return upgrade message with Stripe link if limit hit
3. ✅ Allow Pro users unlimited

### Technical Implementation Plan
- **Photo Analysis Flow:**
  ```python
  def handle_photo(user_id, photo):
      usage = get_usage_count(user_id)
      is_pro = check_if_pro(user_id)

      if usage >= 10 and not is_pro:
          return upgrade_message_with_link()

      result = analyze_photo(photo)
      increment_lookup_count(user_id)
      return result
  ```

- **Upgrade Message Template:**
  ```
  🚫 Free Limit Reached (10/10)

  You've used all your free analyses!

  Upgrade to RIVET Pro for:
  ✅ Unlimited photo analyses
  ✅ Priority processing
  ✅ Advanced AI features

  Only $29/month

  [Upgrade Now] → [Stripe link]
  ```

### Files Likely To Change
- `rivet_pro/adapters/telegram/bot.py` (MODIFY photo handler)
- `rivet_pro/adapters/telegram/messages.py` (ADD upgrade message)
- `rivet_pro/core/usage_tracker.py` (USE functions from RIVET-001)

### Testing
- Free user with 9 lookups → analysis works
- Free user with 10 lookups → blocked with upgrade message
- Pro user with 100 lookups → analysis works
- Upgrade link is valid

---

## Story 4: RIVET-004 - Shorten System Prompts ✂️

**Priority:** 4
**AI Model:** Claude Haiku (cheaper, good for refactoring)
**Status:** ⬜ TODO

### Description
Cut all prompts by 50% for faster field responses.

### What This Does
Reduces AI costs and response time by making prompts more concise without losing quality.

### Acceptance Criteria
1. ✅ Audit all RIVET prompts
2. ✅ Reduce each by 50%
3. ✅ Remove filler text
4. ✅ Test quality maintained

### Technical Implementation Plan
- **Audit Phase:**
  - Find all AI prompts in codebase
  - Document current token counts
  - Identify redundant/filler text

- **Refactor Phase:**
  - Remove unnecessary context
  - Use bullet points instead of paragraphs
  - Remove examples if obvious
  - Keep only essential instructions

- **Example Before:**
  ```
  You are an expert electrical engineer with 20 years of experience
  analyzing industrial equipment. When you receive a photo of an
  electrical panel, you should carefully examine all visible components
  including breakers, contactors, and wiring. Please provide a detailed
  analysis covering the following aspects: equipment identification,
  condition assessment, safety concerns, and maintenance recommendations.
  ```

- **Example After:**
  ```
  Analyze this electrical panel photo:
  - Identify components (breakers, contactors, wiring)
  - Assess condition and safety
  - Provide maintenance recommendations
  ```

### Files Likely To Change
- `rivet_pro/core/prompts.py` (REFACTOR all prompts)
- `rivet_pro/adapters/ai/claude_client.py` (UPDATE prompt templates)
- Any files with AI prompt strings

### Testing
- Before/after token counts (should be ~50% reduction)
- Quality check: Test with same photos, compare results
- Response time improvement

---

## Story 5: RIVET-005 - Remove n8n Footer 🧹

**Priority:** 5 (LOWEST)
**AI Model:** Claude Haiku
**Status:** ⬜ TODO

### Description
Remove n8n branding from Telegram messages.

### What This Does
Makes the bot look professional by removing the "Powered by n8n" footer that appears on messages.

### Acceptance Criteria
1. ✅ Find where footer is added
2. ✅ Remove or override it
3. ✅ Test all message types

### Technical Implementation Plan
- **Investigation:**
  - Check Telegram message sending code
  - Look for n8n webhook nodes
  - Find where footer text is appended

- **Fix Options:**
  - **Option A:** Strip footer in bot code before sending
  - **Option B:** Override n8n Telegram node settings
  - **Option C:** Use custom HTTP requests instead of n8n Telegram node

- **Implementation:**
  ```python
  def clean_message(text):
      # Remove n8n footer
      footer_patterns = [
          "Powered by n8n",
          "Made with n8n",
          "Built with n8n"
      ]
      for pattern in footer_patterns:
          text = text.replace(pattern, "")
      return text.strip()
  ```

### Files Likely To Change
- `rivet_pro/adapters/telegram/bot.py` (MODIFY message sender)
- n8n workflow JSON files (MODIFY Telegram nodes)

### Testing
- Send all message types (welcome, analysis, error, upgrade)
- Verify no n8n branding appears
- Check message formatting is clean

---

## Implementation Order & Dependencies

```
RIVET-001 (Usage Tracking)
    ↓
RIVET-002 (Stripe Payments)
    ↓
RIVET-003 (Free Tier Enforcement) ← Uses RIVET-001 + RIVET-002
    ↓
RIVET-004 (Shorten Prompts) ← Independent
    ↓
RIVET-005 (Remove Footer) ← Independent
```

**Critical Path:** RIVET-001 → RIVET-002 → RIVET-003

**Can Be Done Anytime:** RIVET-004, RIVET-005

---

## Cost & Time Estimates

### Development Time
| Story | Complexity | Time Estimate |
|-------|-----------|---------------|
| RIVET-001 | Medium | 30-45 min |
| RIVET-002 | High | 45-60 min |
| RIVET-003 | Low | 15-20 min |
| RIVET-004 | Low | 20-30 min |
| RIVET-005 | Low | 10-15 min |
| **TOTAL** | | **2-3 hours** |

### AI Costs (If Using Claude API)
| Story | Model | Tokens | Cost |
|-------|-------|--------|------|
| RIVET-001 | Sonnet 4 | ~15,000 | $0.10 |
| RIVET-002 | Sonnet 4 | ~20,000 | $0.13 |
| RIVET-003 | Sonnet 4 | ~10,000 | $0.07 |
| RIVET-004 | Haiku | ~5,000 | $0.01 |
| RIVET-005 | Haiku | ~3,000 | $0.01 |
| **TOTAL** | | **~53,000** | **$0.32** |

---

## Business Impact

### Before MVP (Current State)
- Users can analyze photos
- No limits = no monetization
- No tracking = no data
- n8n branding = looks unprofessional
- Slow/expensive prompts

### After MVP (With These 5 Stories)
- ✅ Freemium model: 10 free, then $29/month
- ✅ Payment processing: Can collect money
- ✅ Usage tracking: Know your metrics
- ✅ Professional branding: No n8n footer
- ✅ Optimized prompts: 50% faster, 50% cheaper

**Revenue Potential:**
- 100 users → 10 convert to Pro (10%) = $290/month
- 1,000 users → 100 convert to Pro = $2,900/month
- 10,000 users → 1,000 convert to Pro = $29,000/month

**ROI:** Spend 3 hours + $0.32 → Enable $290-29,000/month revenue

---

## Next Steps

**Option 1: I Implement All 5 Stories Now** ⚡
- Start with RIVET-001
- Move through them sequentially
- Each story takes 10-60 minutes
- Total time: 2-3 hours
- You get: Complete MVP, ready to monetize

**Option 2: Review & Modify Stories First** ✏️
- Change priorities
- Add/remove acceptance criteria
- Adjust descriptions
- Then I implement

**Option 3: Cherry-Pick Stories** 🍒
- "Just do RIVET-001 and RIVET-002" (monetization core)
- Skip the others for now

---

**What would you like to do?**
1. Start implementing all 5 stories?
2. Modify any stories first?
3. Implement only specific stories?
