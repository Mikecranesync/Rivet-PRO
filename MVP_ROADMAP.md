# RIVET Pro MVP Roadmap

**Created:** 2026-01-12
**Target Launch:** 2 weeks from audit completion
**Philosophy:** CRAWL first. Ship something that works.

---

## Vision

Field techs photograph equipment → instant identification + troubleshooting guidance.

**One Sentence:** "Shazam for industrial equipment"

---

## MVP Scope

### IN SCOPE (Must Ship)
1. ✅ Photo Bot V2 receives photos (n8n webhook)
2. ✅ Gemini Vision analyzes photo
3. ✅ Manual Hunter searches web (Tavily Tier 1-2, Groq Tier 3)
4. ❌ Python bot integrated with n8n webhooks
5. ❌ Equipment auto-created in database
6. ❌ Usage tracking enforced (10 lookups/month free)
7. ✅ Database schema complete

### OUT OF SCOPE (Deferred)
- Stripe payment integration (honor system first)
- PDF manual retrieval (n8n Manual Hunter works, polish later)
- Detailed troubleshooting steps (4-route exists but complex)
- CMMS integration beyond equipment creation
- Team/organization features
- Web dashboard (REST API exists, UI deferred)
- Mobile app

---

## Sprint Plan

### Sprint 1: n8n Integration (Week 1)
**Goal:** Photo in → Equipment saved → Answer out

| Story | Title | Priority | Effort | Status |
|-------|-------|----------|--------|--------|
| RIVET-007 | Integrate n8n Photo Bot V2 with Python Bot | P0 | Medium | ⬜ TODO |
| RIVET-010 | Usage Tracking Enforcement | P0 | Medium | ⬜ TODO |

### Sprint 2: Telegram Commands (Week 1-2)
**Goal:** Equipment search + work order creation

| Story | Title | Priority | Effort | Status |
|-------|-------|----------|--------|--------|
| RIVET-008 | Implement /equip search Command | P0 | Small | ⬜ TODO |
| RIVET-009 | Implement /wo create Command (Optional) | P1 | Medium | ⬜ TODO |

### Sprint 3: Polish & Deploy (Week 2)
**Goal:** Handle edge cases, improve UX, deploy to VPS

| Story | Title | Priority | Effort | Status |
|-------|-------|----------|--------|--------|
| RIVET-011 | Error Handling & User Messages | P1 | Small | ⬜ TODO |
| RIVET-012 | Database Migration Automation | P1 | Small | ⬜ TODO |
| RIVET-013 | Setup Documentation | P1 | Small | ⬜ TODO |

---

## Success Criteria

### Technical
- [ ] Bot responds in < 10 seconds
- [ ] Equipment ID accuracy > 80%
- [ ] Manual found rate > 80% (3-tier search)
- [ ] Zero crashes in 24hr test
- [ ] Handles 100 requests/day

### User
- [ ] 5 real techs give positive feedback
- [ ] Setup takes < 5 minutes
- [ ] No training needed to use

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Gemini API rate limits | Medium | High | Implement backoff, use Groq fallback |
| Poor equipment recognition | Medium | High | Improve prompts, feedback loop |
| n8n VPS downtime | Low | High | Monitor uptime, manual fallback |
| Database connection failures | Low | High | Failover: Neon → VPS → Supabase → SQLite |

---

## Launch Checklist

### Before Public Launch
- [ ] All Sprint 1-3 stories complete
- [ ] Tested with 20+ real equipment photos
- [ ] Error messages are helpful
- [ ] README has setup instructions
- [ ] Bot description configured in BotFather
- [ ] Monitoring/alerting in place

### Launch Day
- [ ] Announce in 1-2 maintenance forums
- [ ] Monitor error rates
- [ ] Be available for quick fixes

---

## Post-MVP Roadmap (WALK → RUN)

### WALK Phase (Month 2)
- Stripe integration
- PDF manual retrieval polish
- Basic analytics dashboard
- Work order Telegram commands

### RUN Phase (Month 3+)
- Team features
- CMMS integrations
- Mobile app
- PLC panel recognition
- 4-route troubleshooting

---

## Timeline

**Week 1:**
- Day 1-2: RIVET-007 + RIVET-010
- Day 3-4: RIVET-008 + RIVET-011
- Day 5: RIVET-012 + RIVET-013

**Week 2:**
- Day 1-2: RIVET-009 (optional)
- Day 3: Integration testing
- Day 4: VPS deployment
- Day 5: User testing

**Launch:** End of Week 2

---

**Ralph Execution:** 12-16 hours | Cost: $0.50-1.00
**Next Action:** Queue stories in @fix_plan.md
