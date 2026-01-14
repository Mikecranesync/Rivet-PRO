# RIVET Pro - n8n Workflow Map

**Generated**: 2026-01-11
**n8n Instance**: http://72.60.175.144:5678
**Total Workflows**: 39 (15 active, 24 inactive)
**Overall Success Rate**: 90%

---

## Core Production Workflows

### 1. Photo Bot v2
- **ID**: `b-dRUZ6PrwkhlyRuQi7QS` (also referenced as `7LMKcMmldZsu1l6g`)
- **Status**: ✅ Active
- **Trigger**: Webhook (from local bot)
- **Purpose**: Equipment nameplate OCR and data extraction
- **Flow**:
  1. Receives photo from Telegram (@rivet_local_dev_bot)
  2. Sends to Gemini Vision API for OCR
  3. Extracts equipment data (name, model, specs)
  4. Stores in database
  5. Returns extracted info to user
- **Dependencies**: Anthropic Claude API, Gemini Vision API
- **Notes**: Main entry point for equipment registration

### 2. Manual Hunter
- **ID**: TBD (referenced in test workflows)
- **Status**: ✅ Active
- **Trigger**: Webhook or workflow call
- **Purpose**: Search for equipment manuals online
- **Flow**:
  1. Receives equipment data (model, manufacturer)
  2. Searches web for PDF manuals
  3. Calls URL Validator to verify links
  4. Stores manual URLs in database
  5. Returns manual links to requester
- **Dependencies**: URL Validator, Database
- **Calls**: URL Validator workflow

### 3. URL Validator (Test)
- **ID**: TBD
- **Status**: ✅ Active
- **Trigger**: Webhook or workflow call
- **Purpose**: Validate equipment manual URLs are accessible
- **Flow**:
  1. Receives URL to validate
  2. Makes HTTP request with timeout
  3. Checks response status (200 OK, PDF content-type)
  4. Returns validity status
- **Success Rate**: High
- **Notes**: Test environment version

### 4. URL Validator (Production)
- **ID**: TBD
- **Status**: ✅ Active
- **Trigger**: Webhook or workflow call
- **Purpose**: Production URL validation
- **Flow**: Same as test version
- **Notes**: Production-grade error handling

### 5. LLM Judge
- **ID**: TBD
- **Status**: ✅ Active
- **Trigger**: Workflow call
- **Purpose**: Quality assessment of AI responses
- **Flow**:
  1. Receives AI-generated response
  2. Evaluates against quality criteria
  3. Provides score/feedback
  4. Logs result to database
- **Dependencies**: LLM API (Claude or similar)

### 6. Test Runner
- **ID**: TBD
- **Status**: ✅ Active
- **Trigger**: Manual or scheduled
- **Purpose**: Automated workflow testing
- **Flow**:
  1. Executes test cases against workflows
  2. Validates responses
  3. Reports results
- **Notes**: Part of CI/CD validation

---

## Ralph Autonomous System Workflows

### 7. Ralph Main Loop
- **ID**: `HIwpqfAegFSotLqs`
- **Status**: ⚠️ Created, needs credential wiring
- **Trigger**: Manual (will be webhook)
- **Purpose**: Orchestrate autonomous story implementation
- **Flow**:
  1. Query database for todo stories
  2. Execute story via SSH to VPS
  3. Monitor execution
  4. Update status in database
  5. Send Telegram notifications
- **Required Changes**:
  - Wire Supabase credentials to 7 Postgres nodes
  - Change Manual Trigger → Webhook Trigger
  - Activate workflow
- **Notes**: Hybrid approach - calls bash scripts on VPS

---

## Telegram Bot Workflows

### 8. Orchestrator Bot Workflow
- **ID**: TBD
- **Status**: ✅ Active
- **Trigger**: Telegram updates (@RivetCeo_bot)
- **Purpose**: 4-route confidence-based message routing
- **Routes**:
  1. High confidence → direct response
  2. Medium confidence → verify with user
  3. Low confidence → escalate to human
  4. Equipment related → route to CMMS
- **Bot ID**: 7910254197

### 9. CMMS Public Bot Workflow
- **ID**: TBD
- **Status**: ✅ Active
- **Trigger**: Telegram updates (@RivetCMMS_bot)
- **Purpose**: Public-facing work order and equipment management
- **Features**:
  - Equipment search
  - Work order creation
  - Manual lookup
- **Bot ID**: 7855741814

### 10. Photo Bot Workflow
- **ID**: TBD (related to @rivet_local_dev_bot)
- **Status**: ✅ Active
- **Trigger**: Telegram updates (ID: 8161680636)
- **Purpose**: Receive nameplate photos and trigger OCR
- **Calls**: Photo Bot v2 workflow
- **Notes**: Webhook-based architecture

---

## Utility & Helper Workflows

### 11-15. Additional Active Workflows
- **Count**: 5 more active workflows (15 total)
- **Status**: ✅ Active
- **Success Rate**: Contributing to 90% overall
- **Details**: TBD (require workflow inspection)

---

## Inactive Workflows (24 total)

These workflows exist but are not currently active:
- May be deprecated versions
- Could be test/development workflows
- Some might be templates or experiments

**Action Required**: Audit inactive workflows
- Determine if needed
- Archive or delete unnecessary ones
- Document remaining ones

---

## Workflow Dependencies Graph

```
User (Telegram)
    ↓
Photo Bot (Telegram Trigger)
    ↓
Photo Bot v2 Workflow (7LMKcMmldZsu1l6g)
    ├─→ Gemini Vision API (OCR)
    ├─→ Equipment Database (store)
    └─→ Manual Hunter Workflow
            ├─→ Web Search
            ├─→ URL Validator Workflow
            │     └─→ HTTP Request
            └─→ Manual Database (store)
                  ↓
            LLM Judge (quality check)
                  ↓
            Response to User
```

---

## Workflow Call Relationships

**Caller → Callee**:
- Photo Bot v2 → Manual Hunter
- Manual Hunter → URL Validator
- Manual Hunter → LLM Judge (optional)
- Ralph Main Loop → VPS bash scripts (external)

**No Known Callers** (entry points):
- Orchestrator Bot (Telegram triggered)
- CMMS Public Bot (Telegram triggered)
- Test Runner (manual/scheduled)

---

## Workflow Configuration

### Common Settings
- **Timezone**: UTC
- **Execution Mode**: Main (not manual)
- **Error Workflow**: None configured
- **Retry Policy**: Varies by workflow

### Credentials Used
- **PostgreSQL**: Supabase, Neon
- **Telegram**: 3 bot tokens
- **APIs**: Anthropic, Google Gemini, Groq, OpenAI
- **HTTP**: Various API keys

### Environment Variables
Most workflows reference:
- `DATABASE_URL`
- `TELEGRAM_BOT_TOKEN`
- `ANTHROPIC_API_KEY`
- `GOOGLE_API_KEY`

---

## Monitoring & Health

### Success Rates (Active Workflows)
- **Overall**: 90% success
- **Photo Bot v2**: High success (OCR works well)
- **Manual Hunter**: Good (depends on search quality)
- **URL Validator**: Very high (simple HTTP check)
- **LLM Judge**: Varies (depends on AI response)

### Common Failure Modes
1. **API Timeouts**: External services slow/down
2. **Database Connection**: Temporary connection loss
3. **Invalid Data**: Malformed input from Telegram
4. **Rate Limiting**: Hitting API limits

### Monitoring Tools
- n8n execution log (built-in)
- PostgreSQL logs
- Telegram bot status (@BotFather)
- VPS system logs

---

## Deployment & Access

### n8n Access
- **URL**: http://72.60.175.144:5678
- **Auth**: Username/password (in .env)
- **API**: Available for programmatic access

### Workflow Export/Import
- **Format**: JSON
- **Location**: `/root/Rivet-PRO/rivet-n8n-workflow/`
- **Files**:
  - `rivet_workflow.json` (main)
  - `rivet_workflow_clean.json`
  - `rivet_workflow_minimal.json`
  - Various test/backup versions

### Backup Strategy
- Git-tracked workflow JSON files
- Manual exports before major changes
- Database backups include workflow metadata

---

## Development Workflow

### Adding a New Workflow
1. Create in n8n UI
2. Test with manual trigger
3. Wire credentials
4. Export JSON
5. Commit to git
6. Activate
7. Document here

### Modifying Existing Workflow
1. Deactivate in n8n
2. Make changes
3. Test with manual execution
4. Export updated JSON
5. Commit to git
6. Reactivate
7. Update documentation

### Testing Workflows
1. Use Test Runner workflow (automated)
2. Manual execution with sample data
3. Check execution logs
4. Verify database state
5. Test Telegram responses

---

## Next Steps

### Documentation Needed
- [ ] Complete workflow IDs for all 15 active workflows
- [ ] Document the 9 unknown active workflows
- [ ] List all 24 inactive workflows
- [ ] Create detailed flow diagrams
- [ ] Document webhook endpoints

### Improvements
- [ ] Set up centralized error handling workflow
- [ ] Implement retry policies consistently
- [ ] Add monitoring/alerting for failures
- [ ] Create workflow templates for common patterns
- [ ] Audit and clean up inactive workflows

### Testing
- [ ] Create comprehensive test suite
- [ ] Document test data/scenarios
- [ ] Automate workflow testing
- [ ] Set up staging environment

---

## Glossary

**Webhook**: HTTP endpoint that triggers workflow
**Node**: Single step in workflow (HTTP Request, Database Query, etc.)
**Execution**: Single run of a workflow
**Trigger**: Entry point for workflow (Webhook, Schedule, Manual)
**Connection**: Line between nodes showing data flow

---

**Last Updated**: 2026-01-11
**Maintained By**: Development Team
**Next Audit**: TBD (after workflow inspection)
