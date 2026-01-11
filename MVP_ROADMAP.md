# RIVET Pro MVP Roadmap

**Created:** 2026-01-11
**Target Launch:** 2026-01-25 (2 weeks)
**Philosophy:** CRAWL first. Ship something that works.
**Current Status:** 8/10 MVP Ready - Core features complete, deployment gaps remain

---

## Vision

Field techs photograph equipment → instant identification + troubleshooting guidance.

**One Sentence:** "Shazam for industrial equipment"

---

## MVP Scope

### IN SCOPE (Must Ship)

1. ✅ Telegram bot receives photos
2. ✅ AI identifies equipment from photo (Gemini 2.5 Flash)
3. ✅ Bot responds with equipment name + basic info
4. ✅ Usage tracked per Telegram user (RIVET-001)
5. ✅ Free tier enforced (10 lookups/month) (RIVET-003)

**ALL CORE FEATURES IMPLEMENTED**

### BONUS (Already Built, Will Ship)

- ✅ Stripe payment integration (RIVET-002) - Pro tier checkout + webhooks
- ✅ Equipment CMMS - Full equipment registry with fuzzy matching
- ✅ Work Orders - Complete work order lifecycle management
- ✅ Web API - FastAPI with 7 routers for future dashboard
- ✅ Multi-provider OCR - Cost-optimized Groq → Gemini → Claude → GPT-4o chain

### OUT OF SCOPE (Deferred to WALK Phase)

- PDF manual retrieval polish (Manual Hunter works, needs UI)
- Team/organization features (tables exist, activation deferred)
- WhatsApp integration (scaffolded, not active)
- Mobile native app
- Advanced analytics dashboard
- CMMS integrations (ServiceNow, SAP, etc.)
- PLC panel recognition

---

## Sprint Plan

### Sprint 1: Production Infrastructure (Jan 11-14)

**Goal:** Fix deployment blockers, verify production readiness

| Story | Title | Status | Complexity | Priority |
|-------|-------|--------|------------|----------|
| RIVET-007 | Verify n8n Photo Bot v2 Gemini Credential | ⬜ TODO | Simple | P0 |
| RIVET-008 | Configure Production HTTPS Webhook | ⬜ TODO | Medium | P0 |
| RIVET-009 | Wire Ralph Workflow Database Credentials | ⬜ TODO | Simple | P1 |

**Deliverable:** Bot works in production with HTTPS webhook, n8n workflows fully operational

---

### Sprint 2: Quality & Documentation (Jan 15-18)

**Goal:** Test coverage, deployment docs, production confidence

| Story | Title | Status | Complexity | Priority |
|-------|-------|--------|------------|----------|
| RIVET-010 | Add Comprehensive Bot Handler Tests | ⬜ TODO | Medium | P1 |
| RIVET-011 | Create Production Deployment Documentation | ⬜ TODO | Simple | P1 |

**Deliverable:** Test suite covers critical paths, anyone can deploy to production

---

### Sprint 3: Launch Readiness (Jan 19-25)

**Goal:** Final polish, monitoring, launch prep

| Task | Description | Owner | Status |
|------|-------------|-------|--------|
| Load Testing | 100 requests/day test | Developer | ⬜ |
| Error Monitoring | Configure alerts for failures | Developer | ⬜ |
| Database Backup | Automated Neon backups + restore test | Developer | ⬜ |
| User Feedback | Add /feedback command to bot | Developer | ⬜ |
| Launch Announcement | Draft announcement for maintenance forums | Product | ⬜ |
| BotFather Configuration | Update bot description, commands, profile pic | Developer | ⬜ |

**Deliverable:** Production-ready bot with monitoring, backups, and launch plan

---

## Story Details

### RIVET-007: Verify n8n Photo Bot v2 Gemini Credential

**Priority:** P0 - MVP Blocker
**Complexity:** Simple (10-15 minutes)
**Why Critical:** Without working Gemini credential, photo OCR fails

**Tasks:**
1. Log into n8n at http://72.60.175.144:5678
2. Open Photo Bot v2 workflow (ID: 7LMKcMmldZsu1l6g)
3. Check Gemini API credential configuration
4. Test workflow execution with sample photo
5. If broken: Create new Gemini credential, wire to workflow nodes
6. Re-test workflow end-to-end

**Success Criteria:**
- Photo Bot v2 executes successfully
- Gemini Vision node returns equipment identification
- No credential-related errors in workflow logs

---

### RIVET-008: Configure Production HTTPS Webhook

**Priority:** P0 - MVP Blocker
**Complexity:** Medium (30-45 minutes)
**Why Critical:** Telegram requires HTTPS for production webhooks (polling mode is dev-only)

**Options:**

**Option A: ngrok (Fastest)**
- Install ngrok on VPS
- Create persistent HTTPS tunnel
- Update bot.py to use webhook mode
- Register webhook with Telegram

**Option B: Proper SSL (Production-Ready)**
- Configure domain DNS to point to VPS (72.60.175.144)
- Install Let's Encrypt SSL certificate
- Configure nginx reverse proxy
- Update bot.py to use webhook mode
- Register webhook with Telegram

**Tasks:**
1. Choose approach (recommend Option A for MVP, Option B for production)
2. Configure HTTPS endpoint
3. Update `rivet_pro/adapters/telegram/bot.py`:
   - Change from `application.run_polling()` to `application.run_webhook()`
   - Set webhook URL
4. Test webhook receives Telegram updates
5. Verify photo upload works via webhook

**Success Criteria:**
- Bot responds to messages via HTTPS webhook
- Photo uploads trigger workflow correctly
- No polling mode fallback needed

---

### RIVET-009: Wire Ralph Workflow Database Credentials

**Priority:** P1 - Important for Autonomous Development
**Complexity:** Simple (10-15 minutes)
**Why Important:** Enables Ralph to autonomously implement future stories

**Tasks:**
1. Log into n8n at http://72.60.175.144:5678
2. Open Ralph Main Loop workflow
3. Identify 7 Postgres nodes without credentials
4. Create Neon PostgreSQL credential in n8n if not exists
5. Wire credential to all 7 Postgres nodes
6. Test workflow execution (manual trigger)
7. Verify database reads/writes work

**Success Criteria:**
- All 7 Postgres nodes have valid credentials
- Ralph workflow can read from @fix_plan table
- Ralph workflow can write progress updates
- No database connection errors

---

### RIVET-010: Add Comprehensive Bot Handler Tests

**Priority:** P1 - Quality Assurance
**Complexity:** Medium (1-2 hours)
**Why Important:** Prevents regressions, enables confident iteration

**Files to Create/Modify:**
- `tests/test_bot_handlers.py` - New comprehensive test suite
- `tests/conftest.py` - Add Telegram bot fixtures

**Test Coverage Needed:**

1. **Command Tests**
   - `/start` command registers new user
   - `/equip search motor` returns equipment results
   - `/wo create` initiates work order flow
   - `/stats` returns usage statistics
   - `/upgrade` returns Stripe checkout link

2. **Photo Handler Tests**
   - Photo upload triggers OCR workflow
   - Equipment identified correctly
   - Response formatted properly
   - Usage count incremented
   - Free tier limit enforced (11th photo blocked)

3. **Edge Cases**
   - Non-photo message handling
   - Invalid photo format
   - n8n webhook timeout
   - Database connection failure
   - API key missing/invalid

**Success Criteria:**
- pytest suite with 15+ tests
- All critical paths covered
- Mocked external dependencies (Telegram API, n8n, database)
- Tests pass in CI/CD
- 80%+ code coverage for bot.py

---

### RIVET-011: Create Production Deployment Documentation

**Priority:** P1 - Operational Readiness
**Complexity:** Simple (30-45 minutes)
**Why Important:** Enables reproducible deployments, onboarding new developers

**File to Create:**
- `DEPLOYMENT.md` - Comprehensive production deployment guide

**Sections Needed:**

1. **Prerequisites**
   - VPS requirements (Ubuntu 22.04+, 2GB RAM, 20GB disk)
   - Required accounts (Neon, Telegram, Gemini, Stripe)
   - SSH access setup

2. **Initial Setup**
   - Clone repository
   - Install dependencies (Python 3.11+, poetry, postgresql-client)
   - Configure environment variables (.env setup)
   - Database migration execution

3. **n8n Configuration**
   - Install n8n on VPS
   - Import workflows from `rivet-n8n-workflow/`
   - Configure credentials (Gemini, Claude, Postgres)
   - Test each workflow

4. **Bot Deployment**
   - Configure systemd service for bot
   - Start bot service
   - Configure HTTPS webhook (see RIVET-008)
   - Verify bot responds to /start

5. **Web API Deployment**
   - Configure systemd service for FastAPI
   - Set up nginx reverse proxy
   - Enable SSL certificate
   - Test API endpoints

6. **Monitoring & Maintenance**
   - Log file locations
   - How to restart services
   - Database backup strategy
   - Common troubleshooting steps

**Success Criteria:**
- New developer can deploy from scratch in < 2 hours
- All environment variables documented
- Service management commands clear
- Troubleshooting section covers common issues

---

## Success Criteria

### Technical

- [x] Bot responds in < 10 seconds (currently ~3-5 seconds via n8n)
- [🟡] Equipment ID accuracy > 80% (needs production data to verify)
- [⬜] Zero crashes in 24hr test (needs load testing)
- [x] Handles 100 requests/day (Neon free tier supports this)

### User

- [⬜] 5 real techs give positive feedback (post-launch)
- [x] Setup takes < 5 minutes (send photo → get answer)
- [x] No training needed to use (intuitive Telegram UX)

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Gemini API rate limits | Medium | High | Multi-provider fallback already implemented (Groq → Gemini → Claude → GPT-4o) |
| Poor equipment recognition | Medium | High | Equipment taxonomy with 500+ categories, continuous prompt tuning |
| n8n workflow failures | Low | High | Implement workflow monitoring, alerts on failures |
| Database connection issues | Low | Medium | AsyncPG connection pool with retry logic |
| Stripe webhook signature verification fails | Low | High | Already implemented correctly, test thoroughly |
| Free tier abuse | Medium | Medium | Usage tracking with IP-based rate limiting if needed |
| VPS downtime | Low | High | Configure automated monitoring (UptimeRobot), have VPS backup plan |

---

## Launch Checklist

### Before Public Launch

- [⬜] All Sprint 1-3 stories complete (RIVET-007 through RIVET-011)
- [⬜] Tested with 20+ real equipment photos from different manufacturers
- [x] Error messages are helpful and user-friendly
- [x] README has setup instructions
- [⬜] Bot description configured in BotFather
- [⬜] Monitoring/alerting in place (error tracking, uptime monitoring)
- [⬜] Database backup configured (Neon automated backups enabled)
- [⬜] Load tested (100 requests/day for 24 hours)
- [x] Stripe integration tested (checkout flow, webhooks)
- [⬜] .env.example created for new developers

### Launch Day

- [⬜] Announce in 1-2 maintenance forums (r/PLC, r/IndustrialMaintenance)
- [⬜] Monitor error rates closely (first 24 hours)
- [⬜] Be available for quick fixes (on-call for launch day)
- [⬜] Have rollback plan ready (revert to polling mode if webhook fails)
- [⬜] Collect initial user feedback via /feedback command

### Week 1 Post-Launch

- [⬜] Analyze usage patterns (popular equipment, response times)
- [⬜] Fix any critical bugs discovered
- [⬜] Collect feedback from first 10 users
- [⬜] Iterate on equipment identification prompts based on real data
- [⬜] Plan WALK phase features based on user requests

---

## Post-MVP Roadmap (WALK → RUN)

### WALK Phase (Month 2 - Feb 2026)

**Goal:** Enhance core features, improve accuracy

| Feature | Description | Priority | Effort |
|---------|-------------|----------|--------|
| Enhanced Equipment Taxonomy | Expand to 1000+ categories based on usage | P1 | M |
| Manual Hunter UI Polish | Better manual search results presentation | P1 | M |
| Advanced Analytics | Usage patterns, popular equipment, response time metrics | P2 | L |
| Feedback Loop | Auto-improve prompts based on user corrections | P1 | L |
| Equipment Photo Gallery | Show example photos for each equipment type | P2 | M |
| Multilingual Support | Spanish equipment names and responses | P2 | M |

### RUN Phase (Month 3+ - Mar 2026)

**Goal:** Scale, multi-channel, enterprise features

| Feature | Description | Priority | Effort |
|---------|-------------|----------|--------|
| Team Features Activation | Organizations, shared knowledge, admin roles | P1 | L |
| WhatsApp Integration | Multi-channel support via WhatsApp Business | P1 | M |
| CMMS Integrations | ServiceNow, SAP PM, Maximo connectors | P1 | XL |
| Mobile App | Native iOS/Android app for better UX | P2 | XL |
| PLC Panel Recognition | Specialized OCR for control panels | P2 | L |
| Offline Mode | Download manuals for offline access | P2 | M |
| Voice Commands | "Hey RIVET, identify this motor" | P3 | L |

---

## Timeline

```
Week 1 (Jan 11-14): Sprint 1 - Production Infrastructure
├── Day 1-2: RIVET-007 (n8n credentials) + RIVET-008 (HTTPS webhook)
└── Day 3-4: RIVET-009 (Ralph credentials) + testing

Week 2 (Jan 15-18): Sprint 2 - Quality & Documentation
├── Day 1-2: RIVET-010 (bot tests)
└── Day 3-4: RIVET-011 (deployment docs) + refinement

Week 3 (Jan 19-25): Sprint 3 - Launch Readiness
├── Day 1-2: Load testing, monitoring setup
├── Day 3-4: Final polish, launch prep
└── Day 5: LAUNCH 🚀
```

**Total Development Time:** 2 weeks
**Ralph Implementation Time:** ~1-2 hours (RIVET-007-011 autonomous)
**Manual Work:** Load testing, deployment, launch activities

---

## Cost Estimate

### MVP Development
- Ralph autonomous implementation (RIVET-007-011): ~$0.20-0.40
- Manual testing and deployment: $0 (developer time)
- **Total Dev Cost:** < $1

### Monthly Operating Costs (MVP)
- Neon PostgreSQL (Free tier): $0
- VPS (DigitalOcean 2GB): ~$12/month
- n8n (self-hosted): $0
- Gemini API (100 lookups/day): ~$3/month
- Stripe fees (2.9% + 30¢): Variable based on revenue
- Domain + SSL (Let's Encrypt): ~$15/year
- **Total Monthly:** ~$15-20

### Revenue Projections (Month 1)
- 50 free users × $0 = $0
- 5 Pro users × $29 = $145
- Stripe fees (5 × ~$1.15) = -$5.75
- **Net Revenue:** ~$140/month
- **Profit:** ~$120/month (after $20 operating costs)

**Break-even:** 2 paying users

---

## Metrics to Track

### Product Metrics
- Daily active users (DAU)
- Photos processed per day
- Equipment identification accuracy
- Average response time
- Free → Pro conversion rate
- User retention (week-over-week)

### Technical Metrics
- API uptime %
- Workflow execution success rate
- Database query performance
- Error rate by error type
- n8n workflow execution times

### Business Metrics
- Monthly recurring revenue (MRR)
- Churn rate
- Customer acquisition cost (CAC)
- Lifetime value (LTV)
- Net promoter score (NPS)

---

## Definition of Done

**MVP is "done" when:**
- [⬜] RIVET-007 through RIVET-011 complete
- [⬜] Bot runs in production for 48 hours without crashes
- [⬜] 10 real equipment photos correctly identified
- [⬜] Free tier limits enforced correctly
- [⬜] Stripe payment flow tested end-to-end
- [⬜] Deployment documentation allows new deploy in < 2 hours
- [⬜] Load tested at 100 requests/day
- [⬜] Monitoring and alerts configured
- [⬜] Launch announcement drafted

**Ready to WALK when:**
- 50+ active users
- Equipment ID accuracy > 85%
- At least 10 Pro subscribers
- User feedback collected and analyzed
- Technical debt from MVP addressed

---

**End of MVP Roadmap**

*Target Launch: January 25, 2026*
*Current Progress: 8/10 MVP Ready*
*Remaining Work: 5 stories (RIVET-007-011) + load testing + launch prep*
*Estimated Time to Launch: 2 weeks*
