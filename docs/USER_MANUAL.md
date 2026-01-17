# RIVET Pro Atlas CMMS
## User Manual

**Version 1.0** | January 2026

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Getting Started](#2-getting-started)
3. [Equipment Management](#3-equipment-management)
4. [Manual & Documentation Lookup](#4-manual--documentation-lookup)
5. [Work Order Management](#5-work-order-management)
6. [SME Expert Chat](#6-sme-expert-chat)
7. [Account Management](#7-account-management)
8. [Administrator Features](#8-administrator-features)
9. [Tips & Best Practices](#9-tips--best-practices)
10. [Quick Reference](#10-quick-reference)
11. [Atlas CMMS Web Interface](#11-atlas-cmms-web-interface)

---

## 1. Introduction

### What is RIVET Pro Atlas CMMS?

RIVET Pro Atlas CMMS is a **mobile-first Computerized Maintenance Management System** designed for maintenance technicians, engineers, and facility managers. Unlike traditional web-based CMMS platforms, RIVET Pro operates entirely through **Telegram**, putting powerful maintenance tools in your pocket.

### Why Telegram?

- **Instant Access** - No apps to download, no logins to remember
- **Works Everywhere** - Any device with Telegram (phone, tablet, desktop)
- **Offline Photos** - Take photos offline, send when connected
- **Push Notifications** - Real-time alerts for work orders and updates
- **Natural Conversation** - Ask questions like you're texting a colleague

### What Can You Do?

| Feature | Description |
|---------|-------------|
| **Equipment Registry** | Snap a photo of any nameplate, and AI automatically extracts manufacturer, model, and serial number |
| **Manual Lookup** | Instantly find service manuals for your equipment |
| **Work Orders** | Create, track, and complete work orders linked to equipment |
| **SME Expert Chat** | Chat with AI-powered vendor specialists (Siemens, Rockwell, ABB, etc.) |
| **Knowledge Base** | System learns from every interaction, getting smarter over time |

---

## 2. Getting Started

### Prerequisites

- A Telegram account (free at [telegram.org](https://telegram.org))
- Access to the RIVET Pro bot

### Finding the Bot

1. Open Telegram
2. Search for **@RivetCMMS_bot**
3. Tap **Start** or send `/start`

### First-Time Registration

When you first message the bot, you'll be automatically registered:

```
/start
```

**Response:**
```
Welcome to RIVET Pro Atlas CMMS!

I'm your AI-powered maintenance assistant. Here's what I can help with:

📸 Send a photo of any equipment nameplate
🔍 Search for service manuals
📋 Create and manage work orders
💬 Chat with vendor SME experts

Send /help to see all available commands.
```

### Checking Your Account

**View your stats:**
```
/stats
```

Shows:
- Total equipment count
- Work orders (open, in progress, completed)

**Check your subscription tier:**
```
/tier
```

Shows:
- Current tier (Free or Pro)
- Lookups used / remaining
- Upgrade options

---

## 3. Equipment Management

### 3.1 Adding Equipment via Photo

The fastest way to add equipment is by sending a **nameplate photo**.

#### Step 1: Take a Clear Photo

Photograph the equipment nameplate showing:
- Manufacturer name
- Model number
- Serial number (if visible)

**Tips for best results:**
- Good lighting (avoid glare)
- Hold camera steady
- Fill the frame with the nameplate
- Ensure text is readable

#### Step 2: Send with Location Tag (Optional)

Add a **caption** to your photo to tag the equipment's location:

```
[Photo of nameplate]
Caption: Stardust Racers
```

The caption becomes the equipment's **location** in the database, making it easy to find later.

**Example locations:**
- `Stardust Racers` (machine name)
- `Building 3, Line 2` (physical location)
- `Compressor Room` (area)

#### Step 3: Review Results

The bot will respond with:

```
🏭 Equipment Detected

Manufacturer: Siemens
Model: 6SE7021-0EA61
Serial: XB1234567
Confidence: 87%

📖 Manual Found!
Siemens MICROMASTER 420 Operating Instructions
[View Manual]

Equipment ID: EQ-2026-000044 (🆕 Created)
Location: Stardust Racers

Is this the correct manual? Reply Yes or No
```

#### Step 4: Validate the Manual

Reply **Yes** or **No** to confirm if the manual is correct:
- **Yes** → Manual is saved to knowledge base with high confidence
- **No** → Manual is rejected, system searches for alternatives

This **human-in-the-loop** validation helps the system learn and improve.

---

### 3.2 Searching Equipment

Find equipment already in your database:

```
/equip search <query>
```

**Examples:**
```
/equip search siemens
/equip search motor
/equip search MDB949
/equip search Stardust
```

**Response:**
```
🔍 Search Results for "siemens"

1. EQ-2026-000012
   Siemens | 6SE7021-0EA61
   📍 Stardust Racers

2. EQ-2026-000008
   Siemens | 1LA7096-4AA10
   📍 Building 3

3. EQ-2026-000003
   Siemens | 3RV2011-1JA10
   📍 MCC Panel 4

Found 3 results
```

---

### 3.3 Viewing Equipment Details

Get full details on a specific piece of equipment:

```
/equip view <equipment_number>
```

**Example:**
```
/equip view EQ-2026-000044
```

**Response:**
```
🔧 Equipment Details

ID: EQ-2026-000044
Manufacturer: Siemens
Model: 6SE7021-0EA61
Serial: XB1234567
Type: VFD
Location: Stardust Racers

📋 Work Orders: 2
Last Fault: F001 (Overcurrent)

Created: Jan 16, 2026
```

---

### 3.4 Equipment Library

Browse all equipment in the system:

```
/library
```

**Response:**
```
📚 Equipment Library

Total Entries: 156
Manufacturers: 23
Equipment Types: 12
With Manuals: 89 (57%)

Use /library search <query> to find specific equipment
```

**Search the library:**
```
/library search siemens drive
```

---

### 3.5 Listing Your Equipment

View your most recent equipment:

```
/equip list
```

Shows the 10 most recently added equipment with IDs, manufacturers, and models.

---

## 4. Manual & Documentation Lookup

### 4.1 How Manual Search Works

When you send an equipment photo or request a manual, RIVET Pro:

1. **Checks the Knowledge Base** - Looks for previously validated manuals
2. **Searches External Sources** - If not found, searches ManualsLib, manufacturer sites, etc.
3. **Ranks by Confidence** - Returns the best match with confidence percentage
4. **Asks for Validation** - You confirm if it's correct (human-in-the-loop)

### 4.2 Direct Manual Lookup

Request a manual for specific equipment:

```
/manual <equipment_number>
```

**Example:**
```
/manual EQ-2026-000044
```

Or search by manufacturer and model:

```
/manual siemens 6SE7021
```

**Response:**
```
📖 Manual Found

Siemens MICROMASTER 420/430/440
Operating Instructions

Type: Operating Manual
Source: ManualsLib
Confidence: 92%

[📄 View Manual]

Is this the correct manual? Reply Yes or No
```

### 4.3 What If No Manual Is Found?

If no manual is found:
- The system logs this as a **knowledge gap**
- Background workers search for the manual
- Future requests may find it
- Try alternative search terms

**Helpful tips when manual not found:**
- Try the exact model number from the nameplate
- Include the product line name (e.g., "MICROMASTER" not just "MM420")
- Check for typos in model numbers

---

## 5. Work Order Management

### 5.1 Listing Work Orders

View all your work orders:

```
/wo list
```

**Response:**
```
📋 Work Orders

🟢 WO-2026-000015 | Open
   Motor bearing replacement
   Equipment: EQ-2026-000044

🟡 WO-2026-000012 | In Progress
   VFD fault diagnosis
   Equipment: EQ-2026-000008

✅ WO-2026-000010 | Completed
   PM - Monthly inspection
   Equipment: EQ-2026-000003

Showing 3 of 15 work orders
```

**Status Legend:**
| Icon | Status |
|------|--------|
| 🟢 | Open |
| 🟡 | In Progress |
| ✅ | Completed |
| 🔴 | Cancelled |

**Priority Legend:**
| Icon | Priority |
|------|----------|
| 🔵 | Low |
| 🟡 | Medium |
| 🟠 | High |
| 🔴 | Critical |

---

### 5.2 Creating a Work Order

Create a new work order linked to equipment:

```
/wo create <equipment_number> <description>
```

**Example:**
```
/wo create EQ-2026-000044 Motor making grinding noise at high speed
```

**Response:**
```
✅ Work Order Created

WO-2026-000016
Equipment: EQ-2026-000044 (Siemens 6SE7021)
Description: Motor making grinding noise at high speed
Status: 🟢 Open
Priority: 🟡 Medium

Use /wo view WO-2026-000016 to see details
```

---

### 5.3 Viewing Work Order Details

Get full details on a work order:

```
/wo view <work_order_number>
```

**Example:**
```
/wo view WO-2026-000016
```

**Response:**
```
📋 Work Order Details

Number: WO-2026-000016
Status: 🟢 Open
Priority: 🟡 Medium

Equipment: EQ-2026-000044
Siemens 6SE7021-0EA61
📍 Stardust Racers

Title: Motor making grinding noise at high speed

Description:
Motor making grinding noise at high speed. Noticed during
production run. Possible bearing failure.

Fault Codes: None recorded

Created: Jan 16, 2026 3:45 PM
```

---

## 6. SME Expert Chat

### 6.1 What is SME Chat?

SME (Subject Matter Expert) Chat connects you with **AI-powered vendor specialists**. Each expert has deep knowledge of their vendor's equipment and speaks with a unique personality.

### 6.2 Available Experts

| Vendor | Expert | Specialty | Personality |
|--------|--------|-----------|-------------|
| Siemens | **Hans** | Drives, PLCs, Motors | German engineering precision |
| Rockwell | **Mike** | Allen-Bradley PLCs, Drives | American practicality |
| ABB | **Erik** | Drives, Robotics | Scandinavian efficiency |
| Schneider | **Pierre** | Modicon, Telemecanique | French electrical expertise |
| FANUC | **Kenji** | CNC, Robotics | Japanese precision |
| Mitsubishi | **Yuki** | PLCs, Servo systems | Technical excellence |
| Generic | **Alex** | General automation | Versatile problem-solver |

### 6.3 Starting a Chat Session

```
/chat <vendor>
```

**Examples:**
```
/chat siemens
/chat rockwell
/chat abb
```

**Vendor Aliases:**
- `rockwell`, `allen-bradley`, `ab` → Rockwell
- `melsec` → Mitsubishi

**Response:**
```
🇩🇪 Guten Tag! I'm Hans, your Siemens specialist.

I have extensive knowledge of Siemens drives, PLCs, and
automation systems. I see you recently looked up a
6SE7021 MICROMASTER drive.

How can I help you today?

(Send /endchat when you're done)
```

### 6.4 Asking Questions

Simply type your question as a normal message:

```
How do I reset fault code F001 on my MICROMASTER drive?
```

**Response:**
```
🟢 HIGH CONFIDENCE

Fault F001 on the MICROMASTER 420 indicates an overcurrent
condition. Here's how to reset it:

1. First, identify the cause - check for:
   • Motor short circuit
   • Ground fault
   • Excessive load

2. Clear the fault:
   • Press the UP and DOWN buttons simultaneously
   • Or cycle power to the drive
   • Or send reset command via fieldbus

3. If fault persists after reset:
   • Check motor cables for damage
   • Verify motor rating matches drive
   • Check for mechanical binding

⚠️ SAFETY WARNING: Ensure motor is isolated before
inspecting cables or connections.

📚 Sources:
• MICROMASTER 420 Operating Instructions, Ch. 8
• Siemens Fault Code Reference
```

### 6.5 Understanding Confidence Levels

Each response shows a confidence indicator:

| Indicator | Meaning |
|-----------|---------|
| 🟢 **HIGH** | Strong knowledge base match, reliable answer |
| 🟡 **MEDIUM** | Good match but verify with documentation |
| 🟠 **LOW** | Limited information, use caution |

### 6.6 Safety Warnings

When discussing potentially dangerous operations, you'll see:

```
⚠️ SAFETY WARNING: [Warning message]
```

**Always follow proper lockout/tagout procedures!**

### 6.7 Ending a Chat Session

When you're done:

```
/endchat
```

**Response:**
```
Auf Wiedersehen! Session ended.

Your conversation has been saved. Start a new session
anytime with /chat siemens.

Need help with a different vendor? Try /chat
```

---

## 7. Account Management

### 7.1 Free vs Pro Tier

| Feature | Free | Pro |
|---------|------|-----|
| Equipment Lookups | 10/day | Unlimited |
| Manual Search | ✅ | ✅ |
| Work Orders | Limited | Unlimited |
| SME Chat | ✅ | ✅ |
| PDF Manual Chat | ❌ | ✅ |
| Priority Support | ❌ | ✅ |
| **Price** | Free | $29/month |

### 7.2 Checking Your Tier

```
/tier
```

**Free Tier Response:**
```
📊 Your Subscription

Tier: 🆓 Free
Lookups Today: 7 / 10
Remaining: 3

Upgrade to Pro for unlimited lookups!
/upgrade
```

**Pro Tier Response:**
```
📊 Your Subscription

Tier: ⭐ Pro
Lookups: Unlimited
Status: Active

Thank you for your subscription!
```

### 7.3 Upgrading to Pro

```
/upgrade
```

**Response:**
```
⭐ Upgrade to RIVET Pro

Get unlimited access to:
• Unlimited equipment lookups
• PDF manual chat
• Work order management
• Priority support

💰 Just $29/month

[🔗 Subscribe Now]
```

Click the link to complete payment via Stripe.

---

## 8. Administrator Features

*These commands are only available to designated administrators.*

### 8.1 Knowledge Base Statistics

```
/kb_stats
```

Shows:
- Total atoms in knowledge base
- Atoms created today
- Verified atoms count
- Average confidence score
- KB hit rate percentage
- Response time comparisons
- Top 5 most-used atoms

### 8.2 Worker Status

```
/kb_worker_status
```

Shows:
- Worker status (Running/Stopped)
- Last heartbeat
- Jobs processed today
- Queue depth
- Current job details

### 8.3 Admin Dashboard

```
/adminstats
```

Shows:
- Today's query count
- Unique users today
- SME chat sessions
- System health indicators

### 8.4 Weekly Report

```
/report
```

Generates a comprehensive weekly report with:
- Usage trends (with ↑↓→ indicators)
- Week-over-week comparison
- Knowledge gaps identified
- SME vendor popularity

---

## 9. Tips & Best Practices

### 9.1 Taking Great Nameplate Photos

**DO:**
- ✅ Use good lighting (natural light works best)
- ✅ Hold camera steady (brace against something)
- ✅ Fill the frame with the nameplate
- ✅ Ensure all text is readable
- ✅ Clean dusty nameplates first

**DON'T:**
- ❌ Take photos at an angle (causes distortion)
- ❌ Use flash directly (causes glare)
- ❌ Crop out important information
- ❌ Take blurry photos

### 9.2 Location Tagging Best Practices

Use consistent location tags for easy searching:

| Good | Bad |
|------|-----|
| `Building 3, Line 2` | `bldg3` |
| `Stardust Racers` | `that machine` |
| `Compressor Room A` | `comp rm` |
| `MCC-4, Bucket 12` | `electrical` |

### 9.3 When to Use SME Chat

**Use SME Chat for:**
- Troubleshooting fault codes
- Understanding error messages
- Parameter configuration questions
- Best practices for maintenance
- Comparing product options

**Use Manual Lookup for:**
- Wiring diagrams
- Torque specifications
- Replacement part numbers
- Installation procedures

### 9.4 Getting the Most from Free Tier

- **Batch your lookups** - Do multiple equipment additions in one session
- **Use search first** - Check if equipment already exists before adding
- **Validate manuals** - Confirmed manuals don't count against your limit
- **Use SME Chat** - Chat sessions are unlimited

---

## 10. Quick Reference

### 10.1 All Commands

| Command | Description |
|---------|-------------|
| `/start` | Register and start the bot |
| `/help` | Show all commands |
| `/menu` | Interactive command menu |
| `/equip list` | List your equipment |
| `/equip search <query>` | Search equipment |
| `/equip view <id>` | View equipment details |
| `/library` | Browse equipment library |
| `/library search <query>` | Search library |
| `/manual <equipment>` | Look up manual |
| `/wo list` | List work orders |
| `/wo view <id>` | View work order |
| `/wo create <equip> <desc>` | Create work order |
| `/chat <vendor>` | Start SME chat |
| `/endchat` | End SME chat session |
| `/stats` | View your statistics |
| `/tier` | Check subscription tier |
| `/upgrade` | Upgrade to Pro |
| `/status` | System health check |
| `/reset` | Clear session state |

### 10.2 SME Vendor Codes

| Code | Vendor | Expert |
|------|--------|--------|
| `siemens` | Siemens | Hans |
| `rockwell` | Rockwell Automation | Mike |
| `allen-bradley` | Allen-Bradley | Mike |
| `ab` | Allen-Bradley | Mike |
| `abb` | ABB | Erik |
| `schneider` | Schneider Electric | Pierre |
| `fanuc` | FANUC | Kenji |
| `mitsubishi` | Mitsubishi Electric | Yuki |
| `melsec` | Mitsubishi MELSEC | Yuki |
| `generic` | General | Alex |

### 10.3 Status Indicators

**Work Order Status:**
- 🟢 Open
- 🟡 In Progress
- ✅ Completed
- 🔴 Cancelled

**Priority:**
- 🔵 Low
- 🟡 Medium
- 🟠 High
- 🔴 Critical

**Confidence:**
- 🟢 HIGH - Reliable
- 🟡 MEDIUM - Verify
- 🟠 LOW - Use caution

---

## 11. Atlas CMMS Web Interface

In addition to the Telegram bot, you can view and manage equipment through the **Atlas CMMS web interface**.

### 11.1 Accessing the Web UI

**URL:** http://72.60.175.144:3000

**Login Credentials:**
- Email: `admin@example.com`
- Password: `admin`

### 11.2 What's Synced?

Equipment you add via Telegram photo is automatically synced to the web interface:

| Telegram | Web UI |
|----------|--------|
| Equipment Number | Bar Code |
| Manufacturer + Model | Name |
| Model Number | Model |
| Serial Number | Serial Number |
| Photo Caption | Area |

**Example:** If you send a photo with caption "Stardust Racers", that equipment will appear in the web Assets list with "Stardust Racers" as the Area.

### 11.3 Web UI Features

The Atlas CMMS web interface provides:

- **Asset Browser** - View all equipment in a searchable grid
- **Asset Details** - See full specifications, history, and linked work orders
- **Work Order Management** - Create and manage work orders visually
- **Reports** - Generate maintenance reports and analytics
- **User Management** - Add team members and assign roles

### 11.4 Mobile vs Web

| Task | Best Tool |
|------|-----------|
| Quick equipment capture | Telegram (photo) |
| Equipment search while working | Telegram |
| SME expert chat | Telegram |
| Detailed asset browsing | Web UI |
| Work order reports | Web UI |
| Team management | Web UI |

**Tip:** Use Telegram for field work and quick captures, use the web UI for office-based management and reporting.

---

## Support

For issues or feedback:
- Check system status: `/status`
- View help: `/help`
- Admin contact: [Your admin contact]

---

*RIVET Pro Atlas CMMS - Maintenance Made Mobile*

**Bot:** @RivetCMMS_bot
