# Atlas CMMS Testing Guide

## Overview

Atlas CMMS is RIVET Pro's custom-built Computerized Maintenance Management System. It provides equipment tracking, manual lookup, work order management, and AI-powered troubleshooting through a Telegram bot interface.

**Bot:** @rivet_pro_bot (or your configured bot)
**Primary Interface:** Telegram

---

## Testing Requirements

### Prerequisites
- [ ] Telegram account
- [ ] Access to the RIVET Pro bot
- [ ] Sample equipment nameplate photos (or use test images)
- [ ] Admin access (telegram_id: 8445149012) for admin commands

### Test Environment
- **VPS:** 72.60.175.144
- **Database:** Neon PostgreSQL
- **Branch:** main

---

## Feature Test Matrix

| Feature | Command | Priority | Status |
|---------|---------|----------|--------|
| User Registration | `/start` | P0 | [ ] |
| Equipment OCR | Send photo | P0 | [ ] |
| Equipment Search | `/equip search <term>` | P0 | [ ] |
| Manual Lookup | `/manual <equipment>` | P1 | [ ] |
| Equipment Library | `/library` | P1 | [ ] |
| Work Orders | `/wo` | P1 | [ ] |
| SME Chat | `/chat <vendor>` | P1 | [ ] |
| Troubleshooting | Send problem description | P1 | [ ] |
| User Stats | `/stats` | P2 | [ ] |
| Help | `/help` | P2 | [ ] |
| Admin Stats | `/adminstats` | P2 | [ ] |
| Weekly Report | `/report` | P2 | [ ] |

---

## Step-by-Step User Test Plan

### Test 1: User Registration (P0)
**Purpose:** Verify new users are registered in the system

**Steps:**
1. Open Telegram and find @rivet_pro_bot
2. Send `/start`
3. Expected: Welcome message with user's name

**Pass Criteria:**
- [ ] Bot responds with personalized greeting
- [ ] User appears in database (check `/stats`)

---

### Test 2: Equipment OCR from Nameplate Photo (P0)
**Purpose:** Verify OCR can extract equipment info from photos

**Steps:**
1. Take a photo of any equipment nameplate (motor, pump, HVAC unit, etc.)
   - Should show: Manufacturer, Model Number, Serial Number
2. Send the photo to the bot
3. Wait for processing (typing indicator shows)

**Pass Criteria:**
- [ ] Bot identifies manufacturer
- [ ] Bot extracts model number
- [ ] Bot extracts serial number (if visible)
- [ ] Equipment ID is created (e.g., "EQ-2026-000044")
- [ ] Manual search is triggered automatically

**Test Photos to Try:**
- Siemens VFD/motor nameplate
- Allen-Bradley PLC
- ABB drive
- Maytag/Whirlpool appliance
- Any industrial equipment with visible nameplate

---

### Test 3: Equipment Search (P0)
**Purpose:** Verify equipment can be searched by text

**Steps:**
1. Send `/equip search motor`
2. Send `/equip search siemens`
3. Send `/equip search MDB949` (partial model)

**Pass Criteria:**
- [ ] Returns matching equipment from database
- [ ] Shows manufacturer, model, equipment ID
- [ ] "No results" message if nothing matches

---

### Test 4: Manual Lookup (P1)
**Purpose:** Verify manual search finds relevant documentation

**Steps:**
1. Send `/manual siemens 6SE7021`
2. Or after OCR, respond "Yes" to "Is this the correct manual?"

**Pass Criteria:**
- [ ] Bot searches for manual
- [ ] Returns PDF link or ManualsLib URL
- [ ] Confidence percentage shown
- [ ] Human-in-the-loop validation prompt appears

---

### Test 5: Equipment Library (P1)
**Purpose:** View all equipment you've added

**Steps:**
1. Send `/library`

**Pass Criteria:**
- [ ] Lists equipment you've created
- [ ] Shows manufacturer, model, date added
- [ ] Pagination if many items

---

### Test 6: Work Order Management (P1)
**Purpose:** Create and manage work orders

**Steps:**
1. Send `/wo` to see work order menu
2. Send `/wo create` to start new work order
3. Follow prompts to link equipment and describe issue

**Pass Criteria:**
- [ ] Work order menu displays options
- [ ] Can create new work order
- [ ] Work order links to equipment
- [ ] Work order ID generated

---

### Test 7: SME Chat Session (P1)
**Purpose:** Test AI-powered vendor expert chat

**Steps:**
1. Send `/chat siemens` (or rockwell, abb, schneider, etc.)
2. Bot greets you as the vendor SME (e.g., "Hans" for Siemens)
3. Ask a technical question: "How do I reset fault code F001 on a 6SE7021 drive?"
4. Continue conversation with follow-up questions
5. Send `/endchat` to close session

**Pass Criteria:**
- [ ] SME personality greeting appears
- [ ] Responses have vendor-specific voice
- [ ] Confidence level shown (HIGH/MEDIUM/LOW)
- [ ] Safety warnings appear for dangerous operations
- [ ] Sources cited from knowledge base
- [ ] Session ends cleanly with `/endchat`

**Vendors to Test:**
- `siemens` - Hans (German engineering precision)
- `rockwell` - Mike (Allen-Bradley expert)
- `abb` - Erik (Scandinavian efficiency)
- `schneider` - Pierre (Modicon/Telemecanique)
- `fanuc` - Kenji (CNC specialist)
- `mitsubishi` - Yuki (PLC expert)
- `generic` - Alex (general automation)

---

### Test 8: Troubleshooting Flow (P1)
**Purpose:** Test problem description and troubleshooting guidance

**Steps:**
1. Send a problem description (not a command):
   "My Siemens drive is showing fault F001 and won't start"
2. Bot should route to troubleshooting or SME chat

**Pass Criteria:**
- [ ] Bot understands it's a troubleshooting request
- [ ] Provides relevant guidance
- [ ] May offer to start SME chat session

---

### Test 9: User Stats (P2)
**Purpose:** View personal usage statistics

**Steps:**
1. Send `/stats`

**Pass Criteria:**
- [ ] Shows queries made
- [ ] Shows equipment added
- [ ] Shows usage tier (Free/Pro)

---

### Test 10: Help Command (P2)
**Purpose:** Verify help information is useful

**Steps:**
1. Send `/help`

**Pass Criteria:**
- [ ] Lists available commands
- [ ] Brief description of each
- [ ] Easy to understand

---

### Test 11: Admin Stats (P2) - Admin Only
**Purpose:** View system-wide analytics

**Steps:**
1. Send `/adminstats` (must be admin)

**Pass Criteria:**
- [ ] Shows today's queries
- [ ] Shows unique users
- [ ] Shows SME chat sessions
- [ ] Shows KB atom count
- [ ] Shows performance metrics

---

### Test 12: Weekly Report (P2) - Admin Only
**Purpose:** Generate weekly analytics report

**Steps:**
1. Send `/report` (must be admin)

**Pass Criteria:**
- [ ] Shows usage trends with arrows
- [ ] Compares to previous week
- [ ] Lists knowledge gaps
- [ ] Shows SME vendor popularity

---

## Bug Reporting Template

When you find an issue, document it with:

```
**Bug Title:** [Brief description]

**Steps to Reproduce:**
1.
2.
3.

**Expected Result:**


**Actual Result:**


**Screenshot:** [Attach if applicable]

**Telegram Message ID:** [If applicable]

**Severity:** Critical / High / Medium / Low
```

---

## Test Data Cleanup

After testing, you may want to clean up test data:

```sql
-- View your equipment
SELECT * FROM equipment_models WHERE created_at > NOW() - INTERVAL '1 day';

-- View your interactions
SELECT * FROM interactions WHERE telegram_id = YOUR_ID ORDER BY created_at DESC LIMIT 10;
```

---

## Known Limitations

1. **OCR Accuracy:** Works best with clear, well-lit nameplate photos
2. **Manual Search:** May not find manuals for obscure equipment
3. **SME Chat:** Requires OpenAI API key on server
4. **Rate Limits:** Free tier has daily query limits

---

## Contact

For issues during testing, the bot will log errors. Check VPS logs:
```bash
ssh root@72.60.175.144 "journalctl -u rivet-bot -f"
```
