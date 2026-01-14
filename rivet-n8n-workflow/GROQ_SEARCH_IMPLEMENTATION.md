# Groq Web Search Implementation - Technical Specification

**Component**: Manual Hunter Tier 3 Search
**Model**: llama-3.3-70b-versatile
**API**: Groq OpenAI-Compatible Chat Completions
**Cost**: FREE (rate-limited)
**Purpose**: LLM-powered web synthesis for finding equipment manuals when Tavily searches fail

---

## Architecture Overview

### 3-Tier Search Cascade

```
┌─────────────────────────────────────────────────────────┐
│                    Manual Hunter                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Tier 1: Tavily Quick Search                           │
│  ├─ 5 results, basic depth                             │
│  ├─ Query: "{mfg} {model} user manual PDF filetype:pdf"│
│  └─ Latency: 2-5 seconds                               │
│                    ↓ (no PDF found)                     │
│                                                         │
│  Tier 2: Tavily Deep Search                            │
│  ├─ 10 results, advanced depth                         │
│  ├─ Query: "site:{mfg}.com {model} manual PDF download"│
│  └─ Latency: 10-20 seconds                             │
│                    ↓ (no PDF found)                     │
│                                                         │
│  Tier 3: Groq AI Search ← THIS SPEC                    │
│  ├─ llama-3.3-70b-versatile                            │
│  ├─ Web search synthesis                               │
│  ├─ Returns: PDF URL, support URL, confidence          │
│  └─ Latency: 5-15 seconds                              │
│                    ↓                                    │
│                                                         │
│  Result: PDF link or "Not Found"                       │
└─────────────────────────────────────────────────────────┘
```

### Why Groq for Tier 3?

**Advantages**:
- ✅ **FREE**: No cost for API usage (vs $1/1000 for Tavily)
- ✅ **Intelligent**: LLM can synthesize search results and reason about URLs
- ✅ **Fallback**: Handles cases where keyword search fails (misspellings, aliases, discontinued models)
- ✅ **Fast**: 70B parameter model with excellent inference speed
- ✅ **Flexible**: Can handle natural language variations

**Limitations**:
- ⚠️ Rate limited: 30 req/min, 14,400 req/day
- ⚠️ Not a search engine: Relies on training data + reasoning, not live web crawling
- ⚠️ May hallucinate URLs: Must validate responses

---

## API Configuration

### Endpoint

```
POST https://api.groq.com/openai/v1/chat/completions
```

### Authentication

**Method**: HTTP Header Auth
**Header**: `Authorization: Bearer <API_KEY>`

**Credential in n8n**:
```json
{
  "name": "Groq API",
  "type": "httpHeaderAuth",
  "data": {
    "name": "Authorization",
    "value": "Bearer gsk_..."
  }
}
```

### Request Body

```json
{
  "model": "llama-3.3-70b-versatile",
  "messages": [
    {
      "role": "system",
      "content": "You are a technical manual search expert. Your task is to find official PDF manuals for equipment. Return results as JSON only."
    },
    {
      "role": "user",
      "content": "Find the official PDF manual for this equipment:\n\nManufacturer: Siemens\nModel: S7-1200\n\nSearch the web and return ONLY a JSON object with these fields:\n{\n  \"pdf_url\": \"direct PDF download URL or null\",\n  \"support_url\": \"manufacturer support page URL or null\",\n  \"confidence\": 0-100,\n  \"notes\": \"brief explanation\"\n}\n\nIf you find multiple sources, return the most official/reliable one."
    }
  ],
  "temperature": 0.3,
  "max_tokens": 500
}
```

### Request Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `model` | `llama-3.3-70b-versatile` | 70B param model optimized for reasoning |
| `temperature` | `0.3` | Low temperature for deterministic, factual output |
| `max_tokens` | `500` | Sufficient for JSON response with URLs + notes |

**Why llama-3.3-70b-versatile?**
- ✅ Best balance of speed vs capability
- ✅ Strong instruction following
- ✅ Good at structured output (JSON)
- ✅ Free tier availability

**Alternatives** (if needed):
- `mixtral-8x7b-32768` - Faster, less capable
- `llama3-70b-8192` - Similar but older version
- `llama-3.1-70b-versatile` - Newer, may have better web knowledge

---

## Prompt Engineering

### System Prompt

```
You are a technical manual search expert. Your task is to find official PDF manuals for equipment. Return results as JSON only.
```

**Design principles**:
- **Role definition**: Establishes expertise domain
- **Task clarity**: "find official PDF manuals"
- **Output format**: "JSON only" prevents markdown formatting

### User Prompt Template

```
Find the official PDF manual for this equipment:

Manufacturer: {{ manufacturer }}
Model: {{ model }}

Search the web and return ONLY a JSON object with these fields:
{
  "pdf_url": "direct PDF download URL or null",
  "support_url": "manufacturer support page URL or null",
  "confidence": 0-100,
  "notes": "brief explanation"
}

If you find multiple sources, return the most official/reliable one.
```

**Design principles**:
- **Structured input**: Clear manufacturer + model separation
- **JSON schema**: Explicit field definitions with types
- **Null handling**: Instructs model to use `null` for missing data
- **Confidence scoring**: Allows downstream filtering
- **Source selection**: "most official/reliable" prioritizes manufacturer sites

### Example Prompts

**Example 1: Common equipment**
```
Manufacturer: Siemens
Model: S7-1200
```

**Expected output**:
```json
{
  "pdf_url": "https://support.industry.siemens.com/.../s71200_manual.pdf",
  "support_url": "https://support.industry.siemens.com/cs/document/109742530",
  "confidence": 95,
  "notes": "Official Siemens S7-1200 system manual from manufacturer support site"
}
```

**Example 2: Discontinued equipment**
```
Manufacturer: Allen-Bradley
Model: MicroLogix 1100
```

**Expected output**:
```json
{
  "pdf_url": "https://literature.rockwellautomation.com/.../1763-um001_-en-p.pdf",
  "support_url": "https://www.rockwellautomation.com/en-us/support.html",
  "confidence": 85,
  "notes": "Allen-Bradley (now Rockwell Automation) MicroLogix 1100 manual from legacy literature library"
}
```

**Example 3: Manual not found**
```
Manufacturer: CustomCorp
Model: XYZ-9000
```

**Expected output**:
```json
{
  "pdf_url": null,
  "support_url": null,
  "confidence": 0,
  "notes": "No official manual found for CustomCorp XYZ-9000. May be proprietary or custom equipment."
}
```

---

## Response Parsing

### Successful Response Structure

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1704067200,
  "model": "llama-3.3-70b-versatile",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "{\n  \"pdf_url\": \"https://...\",\n  \"support_url\": \"https://...\",\n  \"confidence\": 95,\n  \"notes\": \"...\"\n}"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 100,
    "total_tokens": 250
  }
}
```

### Parsing Logic (n8n Code Node)

```javascript
// Parse Groq LLM response and extract manual URL
const response = $input.item.json;
const content = response.choices?.[0]?.message?.content || '';

// Try to parse JSON from response
let result = {
  pdf_url: null,
  support_url: null,
  confidence: 0,
  notes: 'No manual found'
};

try {
  // Find JSON in response (handles markdown code blocks)
  const jsonMatch = content.match(/\{[\s\S]*\}/);
  if (jsonMatch) {
    result = JSON.parse(jsonMatch[0]);
  }
} catch (e) {
  // Fallback: extract URLs with regex if JSON parsing fails
  const pdfMatch = content.match(/https?:\/\/[^\s]+\.pdf/i);
  const urlMatch = content.match(/https?:\/\/[^\s"'<>]+/i);

  result = {
    pdf_url: pdfMatch?.[0] || null,
    support_url: urlMatch?.[0] || null,
    confidence: pdfMatch ? 70 : urlMatch ? 50 : 0,
    notes: content.substring(0, 200)
  };
}

// Ensure confidence is a number
if (typeof result.confidence === 'string') {
  result.confidence = parseInt(result.confidence, 10) || 0;
}

return {
  json: {
    ...result,
    raw_response: content,
    manufacturer: $('Parse OCR Response').item.json.manufacturer,
    model: $('Parse OCR Response').item.json.model,
    chat_id: $('Parse OCR Response').item.json.chat_id
  }
};
```

**Key features**:
- ✅ **JSON extraction with regex**: Handles markdown code blocks (`\`\`\`json...`)
- ✅ **Fallback URL extraction**: If JSON parse fails, extracts URLs directly
- ✅ **Type coercion**: Ensures `confidence` is integer
- ✅ **Error tolerance**: Never throws, always returns valid structure
- ✅ **Context preservation**: Includes manufacturer, model, chat_id from upstream

### Edge Cases

**Case 1: Model returns markdown-wrapped JSON**
```
Here's the manual information:

```json
{
  "pdf_url": "https://...",
  ...
}
```
```

**Handling**: Regex `\{[\s\S]*\}` matches JSON block, ignoring surrounding text

**Case 2: Model returns text instead of JSON**
```
I found the manual at https://example.com/manual.pdf
The support page is https://example.com/support
```

**Handling**: Fallback regex extracts PDF URL, assigns 70% confidence

**Case 3: Model hallucinates invalid URL**
```json
{
  "pdf_url": "https://non-existent-domain.com/fake-manual.pdf",
  "confidence": 95
}
```

**Handling**: URL validation should be added:
```javascript
// Validate URL before trusting it
if (result.pdf_url) {
  try {
    new URL(result.pdf_url);
    // Optionally: HEAD request to check if URL is reachable
  } catch (e) {
    result.pdf_url = null;
    result.confidence = 0;
    result.notes += ' (invalid URL detected)';
  }
}
```

---

## Error Handling

### Rate Limit Error (429)

**Response**:
```json
{
  "error": {
    "message": "Rate limit reached. Please try again later.",
    "type": "rate_limit_error",
    "code": "rate_limit_exceeded"
  }
}
```

**Handling**:
```javascript
if (response.error?.code === 'rate_limit_exceeded') {
  return {
    json: {
      manual_found: false,
      rate_limited: true,
      retry_after: 60, // Wait 60 seconds
      message: 'Manual search temporarily unavailable. Please try again in 1 minute.'
    }
  };
}
```

**Prevention**:
- Track request count in workflow (e.g., static data counter)
- Add 2-second delay between Groq calls
- Queue requests during high usage

### Authentication Error (401)

**Response**:
```json
{
  "error": {
    "message": "Invalid API key",
    "type": "authentication_error",
    "code": "invalid_api_key"
  }
}
```

**Handling**:
- Log error to n8n execution
- Return "Manual not found" to user (don't expose API error)
- Alert admin via separate notification

### Timeout Error

**Scenario**: Groq API doesn't respond within timeout (default: 30 seconds)

**Handling**:
```javascript
if (error.code === 'ETIMEDOUT' || error.code === 'ECONNABORTED') {
  return {
    json: {
      manual_found: false,
      timeout: true,
      message: 'Manual search timed out. Please try again.'
    }
  };
}
```

**Configuration**:
- Set timeout to 30 seconds in HTTP Request node
- Groq usually responds in 5-15 seconds
- If timeout occurs frequently, check Groq status page

---

## Performance Characteristics

### Latency

**Typical latency**: 5-15 seconds

**Breakdown**:
- Network round-trip: 100-500ms
- Token generation (500 tokens @ 70B): 3-10 seconds
- JSON parsing: < 10ms

**Factors affecting latency**:
- ✅ Model load: llama-3.3-70b is fast for 70B model
- ❌ Groq infrastructure load: Shared free tier
- ❌ Geographic distance: Groq servers in US
- ✅ Token count: 500 tokens is moderate

### Throughput

**Rate limits**:
- **Free tier**: 30 requests/minute, 14,400 requests/day
- **Token limit**: 6,000 tokens/minute (input + output)

**Optimization**:
- Reduce `max_tokens` if possible (500 is sufficient)
- Cache results to avoid re-searching same equipment
- Batch requests if multiple manual lookups needed

### Cost

**Pricing**: **FREE** (as of 2024)

**Comparison to Tavily**:
- Tavily: $1 per 1,000 searches ($0.001 per search)
- Groq: $0 per 1,000 searches
- **Savings**: $1 per 1,000 Tier 3 searches

**Total Manual Hunter cost** (per 1,000 searches):
- Tier 1 (Tavily Quick): $1
- Tier 2 (Tavily Deep): $1
- Tier 3 (Groq): $0
- **Total**: ~$2 (vs $3 if Tier 3 was also Tavily)

---

## Security Considerations

### API Key Protection

**n8n credential storage**:
- ✅ Credentials encrypted at rest in n8n database
- ✅ Never logged in execution history
- ✅ HTTP Header Auth prevents accidental exposure

**Best practices**:
- Rotate Groq API key quarterly
- Use separate API key per environment (dev, prod)
- Monitor Groq dashboard for unauthorized usage

### URL Validation

**Risk**: Groq may return malicious URLs (XSS, phishing, malware)

**Mitigation**:
1. **Whitelist domains**: Only allow known manufacturer domains
   ```javascript
   const trustedDomains = [
     'siemens.com', 'rockwellautomation.com', 'abbcomau.com',
     'schneider-electric.com', 'emerson.com', 'ge.com'
   ];

   const url = new URL(result.pdf_url);
   const isTrusted = trustedDomains.some(domain =>
     url.hostname.endsWith(domain)
   );

   if (!isTrusted) {
     result.confidence = Math.min(result.confidence, 50); // Lower confidence
     result.notes += ' (third-party source)';
   }
   ```

2. **HEAD request validation**: Check if URL is reachable and returns PDF
   ```javascript
   const headResponse = await fetch(result.pdf_url, { method: 'HEAD' });
   if (headResponse.headers.get('content-type') !== 'application/pdf') {
     result.pdf_url = null;
     result.confidence = 0;
   }
   ```

3. **User warning**: If URL is not from manufacturer domain, warn user
   ```
   ⚠️ Manual found from third-party source. Verify before downloading.
   ```

### Data Privacy

**PII handling**:
- ✅ No user PII sent to Groq (only manufacturer + model)
- ✅ Chat IDs not included in Groq request
- ✅ Equipment serial numbers filtered out before Groq call

**Compliance**:
- Groq API: GDPR-compliant, SOC 2 Type II
- Data retention: Groq doesn't store API requests

---

## Monitoring & Logging

### Key Metrics

**Track in n8n execution data**:
```javascript
return {
  json: {
    ...result,
    // Metrics
    groq_latency_ms: Date.now() - startTime,
    groq_tokens_used: response.usage?.total_tokens,
    groq_model: response.model,
    search_successful: result.pdf_url !== null,
    confidence_score: result.confidence
  }
};
```

### Success Rate

**Formula**:
```
Groq Success Rate = (Tier 3 manuals found) / (Tier 3 searches executed)
```

**Expected**: 40-60% (Groq finds manuals that Tavily missed)

### Confidence Distribution

**Track confidence scores**:
- `90-100`: High confidence (manufacturer site)
- `70-89`: Medium confidence (verified third-party)
- `50-69`: Low confidence (unverified third-party)
- `0-49`: Very low confidence (uncertain/hallucinated)

**Use for quality control**: If avg confidence < 60%, review prompt

### Error Tracking

**Track error types**:
```javascript
{
  error_type: 'rate_limit' | 'auth' | 'timeout' | 'parse_error' | 'invalid_url',
  error_count: 1,
  timestamp: new Date().toISOString()
}
```

**Alert triggers**:
- Rate limit errors > 5 in 1 hour → Alert admin
- Auth errors > 0 → Immediate alert (API key issue)
- Parse errors > 10% → Review prompt engineering

---

## Testing & Validation

### Unit Tests

**Test 1: Common equipment (high confidence)**
```
Input:
  Manufacturer: Siemens
  Model: S7-1200

Expected Output:
  pdf_url: https://support.industry.siemens.com/...
  confidence: >= 80
  support_url: not null
```

**Test 2: Uncommon equipment (medium confidence)**
```
Input:
  Manufacturer: Mitsubishi
  Model: FX3U-64MR

Expected Output:
  pdf_url: https://... (may be third-party)
  confidence: 50-80
  support_url: may be null
```

**Test 3: Non-existent equipment (no results)**
```
Input:
  Manufacturer: FakeCompany
  Model: NonExistentModel-XYZ

Expected Output:
  pdf_url: null
  confidence: 0
  notes: "No official manual found"
```

**Test 4: Typo resilience**
```
Input:
  Manufacturer: "Simens" (typo)
  Model: S7-1200

Expected Output:
  Model should correct to "Siemens"
  pdf_url: not null (Groq infers correction)
  notes: Should mention "Siemens" (corrected)
```

### Integration Tests

**Test 5: Tier 1 & 2 fail → Tier 3 succeeds**
```
Scenario: Discontinued equipment (not indexed in Tavily)
Equipment: Allen-Bradley MicroLogix 1100
Expected: Groq finds manual from Rockwell Automation legacy site
```

**Test 6: All tiers fail gracefully**
```
Scenario: Proprietary equipment
Equipment: CustomCorp InternalDevice-001
Expected: "Manual Not Found" message after Tier 3
```

### Load Testing

**Test 7: Rate limit handling**
```
Send 31 requests in 1 minute
Expected:
  - Requests 1-30: Succeed
  - Request 31: Rate limit error
  - Wait 60 seconds, request 32: Succeed
```

---

## Optimization Recommendations

### 1. Prompt Optimization

**Current prompt**: Generic for all equipment

**Improvement**: Customize prompt based on manufacturer
```javascript
// Add manufacturer-specific hints
const manufacturerHints = {
  'Siemens': 'Check support.industry.siemens.com',
  'Allen-Bradley': 'Now owned by Rockwell Automation, check literature.rockwellautomation.com',
  'Schneider Electric': 'Check download.schneider-electric.com'
};

const hint = manufacturerHints[manufacturer] || '';
const prompt = `Find the official PDF manual for this equipment:

Manufacturer: ${manufacturer}
Model: ${model}

${hint}

Return JSON...`;
```

### 2. Caching Strategy

**Cache Tier 3 results** to reduce API calls:

```sql
-- Before calling Groq
SELECT manual_url, confidence FROM groq_search_cache
WHERE manufacturer = ? AND model = ?
AND created_at > NOW() - INTERVAL '30 days';

-- If cached, use cached result
-- If not cached, call Groq and store:

INSERT INTO groq_search_cache (manufacturer, model, manual_url, confidence, created_at)
VALUES (?, ?, ?, ?, NOW());
```

**Cache invalidation**: 30 days (manuals rarely change)

### 3. Parallel Execution

**Current**: Sequential (Tier 1 → Tier 2 → Tier 3)

**Improvement**: Parallel with timeout
```javascript
// Execute all 3 tiers in parallel
const [tier1, tier2, tier3] = await Promise.all([
  tavilyQuick(query),
  tavilyDeep(query),
  groqSearch(query)
]);

// Return first successful result
return tier1.found ? tier1 :
       tier2.found ? tier2 :
       tier3.found ? tier3 :
       null;
```

**Trade-off**: Higher API costs but 3x faster

### 4. Confidence-Based Routing

**Current**: Always execute next tier if previous fails

**Improvement**: Skip tiers based on confidence
```javascript
// If Tier 1 finds manual with confidence < 70%, try Tier 2
// If Tier 2 finds manual with confidence < 50%, try Tier 3 (Groq)

if (tier1.confidence < 70) {
  tier2Result = await tavilyDeep(query);
  if (tier2.confidence < 50) {
    tier3Result = await groqSearch(query);
  }
}
```

---

## Future Enhancements

### 1. Multi-Model Ensemble

Use multiple LLMs and vote:
```
Groq (llama-3.3-70b) → Result A
OpenAI (gpt-4-turbo) → Result B
Anthropic (claude-3-haiku) → Result C

If 2/3 agree on URL → High confidence (95%)
If 1/3 different → Medium confidence (70%)
```

### 2. URL Verification Pipeline

```
Groq returns URL → HEAD request → PDF validation → Extract metadata → Verify manufacturer match → Return validated URL
```

### 3. Learning from Corrections

Store user feedback:
```sql
CREATE TABLE groq_feedback (
  search_query TEXT,
  groq_url TEXT,
  user_correction TEXT, -- Actual manual URL provided by user
  helpful BOOLEAN,
  created_at TIMESTAMP
);
```

Use feedback to fine-tune prompts or build training dataset.

### 4. Hybrid Search

Combine Groq with vector search:
```
User equipment → Vector embedding → Find similar equipment in database → Use cached manual
If not in cache → Groq search
```

---

## Summary

### Node Configuration

**Node Name**: Groq Web Search
**Type**: n8n-nodes-base.httpRequest
**Position**: After "Deep Search Found PDF?" (FALSE path)

**Settings**:
- **Method**: POST
- **URL**: `https://api.groq.com/openai/v1/chat/completions`
- **Authentication**: HTTP Header Auth (Bearer token)
- **Body**: JSON with llama-3.3-70b-versatile model
- **Timeout**: 30 seconds

### Success Criteria

- ✅ Tier 3 executed when Tiers 1 & 2 fail
- ✅ Groq returns structured JSON response
- ✅ PDF URL extracted successfully
- ✅ Confidence score >= 50 for valid results
- ✅ Latency < 15 seconds
- ✅ No rate limit errors under normal usage
- ✅ Integration with Photo Bot V2 works end-to-end

### Key Metrics

- **Target Success Rate**: 40-60% (of searches that reach Tier 3)
- **Average Latency**: 5-15 seconds
- **Cost**: $0 (FREE)
- **Confidence**: 70-95% for manufacturer sites, 50-70% for third-party

---

**Last Updated**: 2026-01-09
**Workflow File**: `rivet-n8n-workflow/rivet_workflow.json`
**Setup Guide**: `MANUAL_HUNTER_SETUP.md`
**Integration Guide**: `PHOTO_BOT_V2_INTEGRATION.md`
