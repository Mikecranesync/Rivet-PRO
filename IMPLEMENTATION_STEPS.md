# RIVET Manual Hunter - Implementation Steps

## 🎉 Development Complete!

All deliverables have been created, committed, and pushed to GitHub.

**Branch**: `feature/manual-hunter-workflow`
**Commit**: `7d20ad01`
**PR URL**: https://github.com/Mikecranesync/Agent-Factory/pull/new/feature/manual-hunter-workflow

---

## 📦 Deliverables Summary

### Completed Files (6 total)

| File | Purpose | Lines | Status |
|------|---------|-------|--------|
| `n8n/workflows/test/rivet_manual_hunter.json` | Complete 22-node workflow | 547 | ✅ |
| `database/schema/manual_hunter_tables.sql` | PostgreSQL schema with test data | 614 | ✅ |
| `n8n/workflows/test/MANUAL_HUNTER_SETUP.md` | API credentials setup guide | 589 | ✅ |
| `n8n/workflows/test/PHOTO_BOT_V2_INTEGRATION_GUIDE.md` | Integration instructions | 562 | ✅ |
| `n8n/workflows/test/manual_hunter_test_payload.json` | Test payloads & scenarios | 101 | ✅ |
| `DELIVERABLES.md` | Complete documentation | 200 | ✅ |

**Total**: 2,513 lines of code and documentation

---

## 🚀 Next Steps to Implementation

### Phase 1: Database Setup (5 minutes)

1. **Connect to Neon PostgreSQL**:
   ```bash
   # Using Neon SQL Editor or pgAdmin
   ```

2. **Run schema file**:
   ```sql
   -- Copy/paste contents from:
   database/schema/manual_hunter_tables.sql
   ```

3. **Verify tables created**:
   ```sql
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'public'
   AND table_name IN ('manuals', 'manual_requests');
   ```

   **Expected output**:
   ```
   table_name
   --------------
   manuals
   manual_requests
   ```

✅ **Checkpoint**: Database tables exist

---

### Phase 2: API Credentials Setup (15-30 minutes)

Follow the comprehensive guide: `n8n/workflows/test/MANUAL_HUNTER_SETUP.md`

#### Quick Registration Links:

1. **Tavily API** (Free - Required)
   - Register: https://tavily.com
   - Get API key from dashboard
   - Format: `tvly-xxxxx`
   - Cost: FREE (1,000 searches/month)

2. **Groq API** (Free - Required)
   - Register: https://console.groq.com
   - Get API key from dashboard
   - Format: `gsk_xxxxx`
   - Cost: FREE (30 req/min)

3. **Serper API** (Paid - Required)
   - Register: https://serper.dev
   - Add credits: $50 package (2,500 searches)
   - Get API key from dashboard
   - Cost: ~$3/month for 1,000 searches

4. **DeepSeek API** (Paid - Required)
   - Register: https://platform.deepseek.com
   - Add credits: $5 minimum
   - Get API key from dashboard
   - Cost: ~$0.20/month for 1,000 evaluations

5. **Perplexity API** (Paid - Optional)
   - Register: https://www.perplexity.ai/settings/api
   - Requires Pro subscription: $20/month
   - API: $5 per 1,000 requests
   - Cost: ~$0.20/month for 40 searches
   - **Can skip initially** - workflow works without Tier 3

#### Create Credentials in n8n:

For each API above, create an **HTTP Header Auth** credential in n8n:

```yaml
# Tavily
Name: Tavily API
Header Name: X-API-Key
Header Value: tvly-xxxxx

# Groq
Name: Groq API
Header Name: Authorization
Header Value: Bearer gsk-xxxxx

# Serper
Name: Serper API
Header Name: X-API-KEY
Header Value: xxxxx

# DeepSeek
Name: DeepSeek API
Header Name: Authorization
Header Value: Bearer sk-xxxxx

# Perplexity (optional)
Name: Perplexity API
Header Name: Authorization
Header Value: Bearer pplx-xxxxx
```

✅ **Checkpoint**: All API credentials created and tested

---

### Phase 3: Import Manual Hunter Workflow (5 minutes)

1. **Open n8n cloud**:
   - Go to your n8n instance
   - Navigate to **Workflows** tab

2. **Import workflow**:
   - Click **Import from File**
   - Select: `n8n/workflows/test/rivet_manual_hunter.json`
   - Click **Import**

3. **Assign credentials**:
   - n8n will prompt for missing credentials
   - Assign each credential you created in Phase 2:
     - Telegram Bot → `Telegram Bot` (existing)
     - Neon RIVET → `Neon RIVET` (existing)
     - Tavily API → `Tavily API`
     - Groq API → `Groq API`
     - Serper API → `Serper API`
     - DeepSeek API → `DeepSeek API`
     - Perplexity API → `Perplexity API` (or skip)

4. **Activate workflow**:
   - Toggle switch to **Active**
   - Webhook URL will be generated

5. **Note webhook URL**:
   ```
   https://[your-instance].app.n8n.cloud/webhook/rivet-manual-hunter
   ```

✅ **Checkpoint**: Manual Hunter workflow active and webhook URL copied

---

### Phase 4: Test Manual Hunter (10 minutes)

Use the test payloads from: `n8n/workflows/test/manual_hunter_test_payload.json`

#### Test 1: Basic Functionality

```bash
curl -X POST https://[your-n8n].app.n8n.cloud/webhook/rivet-manual-hunter \
  -H 'Content-Type: application/json' \
  -d '{
    "chat_id": 123456789,
    "original_message_id": 987654321,
    "manufacturer": "ABB",
    "model_number": "ACS580-01-12A5-4",
    "product_family": "ACS580",
    "full_ocr_text": "ABB DRIVES ACS580-01-12A5-4 Variable Frequency Drive"
  }'
```

**Expected**:
- Manual Hunter workflow executes
- Check n8n execution logs: Should show Tier 1 success
- Check Neon database: Manual should be cached

#### Test 2: Cache Hit

Run the **same curl command again**

**Expected**:
- Instant response (<1 second)
- Execution logs show cache hit path
- Database query returns existing manual

#### Test 3: Telegram Integration

**Important**: For Telegram messages to work, you need to:
1. Update `chat_id` to a **real Telegram chat ID**
2. Ensure your Telegram bot has access to that chat

To get a real chat ID:
```bash
# Send any message to your bot, then check:
curl https://api.telegram.org/bot8161680636:YOUR_BOT_TOKEN/getUpdates
```

Use the `chat.id` from the response.

✅ **Checkpoint**: Manual Hunter finds and caches manuals successfully

---

### Phase 5: Integrate with Photo Bot V2 (15 minutes)

Follow the detailed guide: `n8n/workflows/test/PHOTO_BOT_V2_INTEGRATION_GUIDE.md`

#### Quick Integration Steps:

1. **Open Photo Bot V2**:
   - Workflow ID: `7LMKcMmldZsu1l6g`
   - In n8n cloud

2. **Find insertion point**:
   - Locate node: "Send OCR Results" (or similar)
   - This is where OCR analysis results are sent to user

3. **Add "Send Searching Manual" node**:
   ```yaml
   Type: Telegram
   Chat ID: ={{ $('Telegram Trigger (Photo)').item.json.message.chat.id }}
   Text: "✅ Equipment identified!\n\nI'm now searching for your user manual..."
   Reply to Message ID: ={{ $('Telegram Trigger (Photo)').item.json.message.message_id }}
   ```

4. **Add "Trigger Manual Hunter" node**:
   ```yaml
   Type: HTTP Request
   Method: POST
   URL: https://[your-n8n].app.n8n.cloud/webhook/rivet-manual-hunter
   Body: JSON with manufacturer, model, OCR data
   ```

5. **Update connections**:
   ```
   Send OCR Results → Send Searching Manual → Trigger Manual Hunter → [End]
   ```

6. **Save Photo Bot V2**

7. **Test end-to-end**:
   - Send equipment photo to Telegram bot
   - Verify all messages received:
     1. "Processing your image..."
     2. "Equipment identified: [details]"
     3. "I'm now searching for your user manual..."
     4. "✅ Found your manual! [link]"

✅ **Checkpoint**: Photo Bot V2 triggers Manual Hunter automatically

---

### Phase 6: Monitor & Optimize (Ongoing)

#### Week 1: Initial Monitoring

**Track these metrics**:
- Total manual searches
- Cache hit rate (target: >60% after week 1)
- Tier distribution:
  - Tier 1 (free): Should be ~80%
  - Tier 2 (cheap): Should be ~15%
  - Tier 3 (expensive): Should be ~4%
  - Human queue: Should be ~1%
- API costs (target: <$5/month for 1,000 searches)

**Where to check**:
- n8n execution logs (workflow history)
- Neon database queries:
  ```sql
  -- Cache hit rate
  SELECT COUNT(*) as cache_hits FROM manuals WHERE search_count > 1;

  -- Tier distribution
  SELECT search_tier, COUNT(*) FROM manuals GROUP BY search_tier;

  -- Human queue size
  SELECT COUNT(*) FROM manual_requests WHERE status = 'pending';
  ```

#### Month 1: Cost Optimization

**If costs are high**:
1. **Increase Tier 1 confidence threshold**:
   - Edit "Tier 1 Success?" node
   - Change from `>= 75` to `>= 80`
   - More searches escalate, but higher accuracy

2. **Skip Perplexity initially**:
   - Deactivate Tier 3 nodes
   - Route directly to human queue after Tier 2 fails
   - Save ~$0.20/month

3. **Monitor manufacturer patterns**:
   - Check which manufacturers fail most often
   - Manually source those manuals
   - Add to cache proactively

#### Ongoing: Queue Management

**Human queue requires manual processing**:

1. **Check queue weekly**:
   ```sql
   SELECT * FROM manual_requests
   WHERE status = 'pending'
   ORDER BY requested_at ASC
   LIMIT 10;
   ```

2. **For each pending request**:
   - Manually search for manual
   - If found:
     ```sql
     INSERT INTO manuals (manufacturer, model_number, pdf_url, search_tier, confidence_score)
     VALUES ('...', '...', 'https://...', 'manual', 100);

     UPDATE manual_requests
     SET status = 'found', resolved_at = NOW(), manual_id = [id]
     WHERE id = [request_id];
     ```
   - If not found:
     ```sql
     UPDATE manual_requests
     SET status = 'unavailable', resolved_at = NOW(), notes = 'Manual does not exist'
     WHERE id = [request_id];
     ```

3. **Notify users** (optional):
   - Build admin workflow to send Telegram notifications
   - When manual sourced, message user: "Your manual for [equipment] is now available!"

✅ **Checkpoint**: Monitoring established, costs optimized

---

## 📊 Success Metrics

### Immediate (After Phase 5)
- [ ] Database tables exist in Neon
- [ ] All API credentials configured
- [ ] Manual Hunter workflow active
- [ ] Test curl returns manual successfully
- [ ] Cache hit works (instant response)
- [ ] Photo Bot V2 triggers Manual Hunter
- [ ] End-to-end photo → manual works

### Week 1
- [ ] 50+ manual searches processed
- [ ] Cache hit rate >40%
- [ ] Tier 1 success rate >70%
- [ ] Zero workflow errors
- [ ] Human queue <10 requests

### Month 1
- [ ] 500+ manual searches processed
- [ ] Cache hit rate >60%
- [ ] Average response time <15 seconds
- [ ] API costs <$5/month
- [ ] Human queue resolved weekly
- [ ] User satisfaction: Manual found >95% (includes queue)

---

## 🆘 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Database connection error | Verify Neon credential active, tables exist |
| "Credential not found" | Check credential names match exactly (case-sensitive) |
| API timeout | Check API keys valid, not rate limited |
| No Telegram messages | Verify bot token, chat ID is real/accessible |
| Tier escalation too aggressive | Adjust confidence thresholds in If nodes |
| High API costs | Review tier distribution, increase Tier 1 threshold |
| Large human queue | Process queue weekly, add common manuals to cache |

### Get Help

1. **Check execution logs**:
   - n8n → Workflow → Execution tab
   - Look for red error indicators
   - Click to see detailed error messages

2. **Test individual nodes**:
   - Click "Test Workflow" in n8n
   - Select specific node to test
   - Verify output data structure

3. **Review documentation**:
   - `MANUAL_HUNTER_SETUP.md` - Credential issues
   - `PHOTO_BOT_V2_INTEGRATION_GUIDE.md` - Integration errors
   - `DELIVERABLES.md` - Architecture reference

---

## 🎯 Implementation Timeline

| Phase | Time | Status |
|-------|------|--------|
| Database Setup | 5 min | ⬜ Not Started |
| API Credentials | 15-30 min | ⬜ Not Started |
| Import Workflow | 5 min | ⬜ Not Started |
| Test Manual Hunter | 10 min | ⬜ Not Started |
| Integrate Photo Bot V2 | 15 min | ⬜ Not Started |
| Monitor & Optimize | Ongoing | ⬜ Not Started |
| **TOTAL SETUP TIME** | **~60 minutes** | |

---

## 📁 File Locations

All files in branch: `feature/manual-hunter-workflow`

```
rivet-test-manual-hunter/
├── n8n/workflows/test/
│   ├── rivet_manual_hunter.json              ← Import into n8n
│   ├── manual_hunter_test_payload.json       ← Test with curl
│   ├── MANUAL_HUNTER_SETUP.md                ← API credentials guide
│   └── PHOTO_BOT_V2_INTEGRATION_GUIDE.md     ← Integration steps
├── database/schema/
│   └── manual_hunter_tables.sql              ← Run in Neon SQL editor
├── DELIVERABLES.md                            ← Technical documentation
└── IMPLEMENTATION_STEPS.md                    ← This file
```

---

## 🔗 Quick Links

- **GitHub PR**: https://github.com/Mikecranesync/Agent-Factory/pull/new/feature/manual-hunter-workflow
- **Tavily API**: https://tavily.com
- **Groq API**: https://console.groq.com
- **Serper API**: https://serper.dev
- **DeepSeek API**: https://platform.deepseek.com
- **Perplexity API**: https://www.perplexity.ai/settings/api
- **n8n Docs**: https://docs.n8n.io

---

## 🎉 You're Ready!

Follow the phases above sequentially. Each phase builds on the previous one.

**Estimated total setup time**: ~60 minutes (excluding API account registration wait times)

**Expected result**: Fully automated equipment manual search system that:
- Finds manuals in 10-30 seconds
- Caches results for instant repeat lookups
- Costs ~$3/month for 1,000 searches
- Integrates seamlessly with Photo Bot V2

Good luck! 🚀

---

**Document Version**: 1.0
**Created**: 2026-01-09
**Branch**: `feature/manual-hunter-workflow`
**Commit**: `7d20ad01`
