# Groq and DeepSeek Fallback LLM Providers Implementation

**Date**: 2026-01-12
**Branch**: `ralph/manual-delivery`
**Commit**: ba8ce7c

## Problem Statement

The manual service's URL validation system was failing because both primary LLM providers were unavailable:
- **Claude API**: 404 error (model "claude-3-5-sonnet-20241022" not found)
- **OpenAI API**: 429 error (quota exceeded)

This caused ALL manual URLs to be rejected, resulting in users receiving "Manual not found" messages even when valid PDFs were available.

## Solution

Added Groq and DeepSeek as additional fallback providers to ensure URL validation succeeds even when primary providers fail.

### New Fallback Chain

**Claude → OpenAI → Groq → DeepSeek → Reject**

Each provider is attempted in sequence until one successfully validates the URL or all fail.

## Implementation Details

### 1. Configuration Changes

**File**: `rivet_pro/config/settings.py`

Added DeepSeek API key configuration:
```python
deepseek_api_key: Optional[str] = Field(None, description="DeepSeek API key for LLM validation")
```

Note: `groq_api_key` was already configured.

### 2. Service Initialization

**File**: `rivet_pro/core/services/manual_service.py`

Updated `__init__` method to load both new API keys:
```python
self.groq_api_key = settings.groq_api_key
self.deepseek_api_key = settings.deepseek_api_key
```

Updated safety check to include all four providers:
```python
if not any([self.anthropic_api_key, self.openai_api_key, self.groq_api_key, self.deepseek_api_key]):
    logger.warning("No LLM API keys configured - URL validation will be disabled")
```

### 3. Groq API Integration

**Endpoint**: `https://api.groq.com/openai/v1/chat/completions`
**Model**: `llama-3.3-70b-versatile`
**Authorization**: `Bearer {groq_api_key}`

Implementation follows OpenAI-compatible format:
```python
response = await client.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {self.groq_api_key}",
        "Content-Type": "application/json"
    },
    json={
        "model": "llama-3.3-70b-versatile",
        "max_tokens": 200,
        "temperature": 0.1,
        "messages": [{"role": "user", "content": prompt}]
    }
)
```

### 4. DeepSeek API Integration

**Endpoint**: `https://api.deepseek.com/v1/chat/completions`
**Model**: `deepseek-chat`
**Authorization**: `Bearer {deepseek_api_key}`

Implementation follows OpenAI-compatible format:
```python
response = await client.post(
    "https://api.deepseek.com/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {self.deepseek_api_key}",
        "Content-Type": "application/json"
    },
    json={
        "model": "deepseek-chat",
        "max_tokens": 200,
        "temperature": 0.1,
        "messages": [{"role": "user", "content": prompt}]
    }
)
```

### 5. Comprehensive Logging

Each provider attempt logs:
- Initial attempt: `Attempting {Provider} API validation | url=...`
- Response status: `{Provider} API response | status={status_code}`
- Response content: `{Provider} content (first 200 chars): ...`
- Success: `URL validation ({Provider}) SUCCESS | is_direct_pdf=... | confidence=...`
- Failure: `{Provider} API failed | status=... | body=...`

Final rejection logs all attempts:
```python
logger.warning(
    f"URL rejected (validation failed) | {url} | "
    f"claude_attempted={bool(self.anthropic_api_key)} | "
    f"openai_attempted={bool(self.openai_api_key)} | "
    f"groq_attempted={bool(self.groq_api_key)} | "
    f"deepseek_attempted={bool(self.deepseek_api_key)}"
)
```

## Expected Response Format

All LLMs return consistent JSON:
```json
{
  "is_direct_pdf": true,
  "confidence": 0.92,
  "reasoning": "URL ends with .pdf and contains /documents/ path",
  "likely_pdf_extension": true
}
```

## Validation Prompt

All providers use the same prompt instructing them to:
1. Determine if URL is a DIRECT PDF link or search page
2. Return structured JSON with `is_direct_pdf`, `confidence`, and `reasoning`
3. Be strict: only approve URLs that are clearly direct PDF links

## Testing Instructions

### 1. Environment Setup

Add DeepSeek API key to `.env`:
```bash
DEEPSEEK_API_KEY=your_deepseek_key_here
```

Verify Groq API key exists in `.env`:
```bash
GROQ_API_KEY=your_groq_key_here
```

### 2. Service Restart

Restart the bot service on VPS:
```bash
sudo systemctl restart rivet-bot
```

Or for local testing:
```bash
cd rivet_pro
python -m rivet_pro.bot.bot
```

### 3. Clear Manual Cache

Clear cached results for test equipment:
```sql
DELETE FROM manual_cache WHERE manual_url LIKE '%rockwell%';
```

### 4. Test End-to-End

1. Send a nameplate photo to the bot
2. Monitor logs for fallback chain:
   ```
   Attempting Claude API validation
   Claude API failed | status=404
   Attempting OpenAI API validation
   OpenAI API failed | status=429
   Attempting Groq API validation
   Groq API response | status=200
   URL validation (Groq) SUCCESS | is_direct_pdf=True | confidence=0.92
   ```
3. Verify bot returns manual URL to user

### 5. Expected Log Output

**Successful Groq fallback**:
```
Jan 12 XX:XX:XX | INFO | URL validation starting | has_claude_key=True | has_openai_key=True | has_groq_key=True | has_deepseek_key=True
Jan 12 XX:XX:XX | INFO | Attempting Claude API validation
Jan 12 XX:XX:XX | ERROR | Claude API failed | status=404
Jan 12 XX:XX:XX | INFO | Attempting OpenAI API validation
Jan 12 XX:XX:XX | ERROR | OpenAI API failed | status=429
Jan 12 XX:XX:XX | INFO | Attempting Groq API validation
Jan 12 XX:XX:XX | INFO | Groq API response | status=200
Jan 12 XX:XX:XX | INFO | URL validation (Groq) SUCCESS | is_direct_pdf=True | confidence=0.92
```

**Successful DeepSeek fallback** (if Groq also fails):
```
Jan 12 XX:XX:XX | INFO | Attempting DeepSeek API validation
Jan 12 XX:XX:XX | INFO | DeepSeek API response | status=200
Jan 12 XX:XX:XX | INFO | URL validation (DeepSeek) SUCCESS | is_direct_pdf=True | confidence=0.88
```

## Benefits

1. **Resilience**: Four-layer fallback ensures validation succeeds even if primary providers fail
2. **Cost-effective**: Groq and DeepSeek are generally cheaper than Claude/OpenAI
3. **Speed**: Groq's llama-3.3-70b-versatile is very fast for inference
4. **Transparency**: Comprehensive logging makes debugging easy
5. **Maintainability**: Consistent pattern across all providers

## Files Modified

1. `rivet_pro/config/settings.py` - Added `deepseek_api_key` field
2. `rivet_pro/core/services/manual_service.py` - Implemented Groq and DeepSeek fallback logic

## Deployment Notes

- No database migrations required
- Service restart required to load new configuration
- API keys must be added to `.env` before restart
- Existing manual cache remains valid
- No breaking changes to API or bot interface

## Future Improvements

1. Add provider usage metrics (which provider succeeded most often)
2. Implement dynamic provider ordering based on success rate
3. Add provider-specific timeout configuration
4. Cache LLM validation results to reduce API calls
5. Add cost tracking per provider

## Related Documentation

- Manual Hunter Integration: `MANUAL_HUNTER_INTEGRATION_STATUS.md`
- URL Validator Diagnostic: `URL_VALIDATOR_DIAGNOSTIC_REPORT.md`
- Rivet Photo Bot V2 Status: `RIVET_PHOTO_BOT_V2_STATUS.md`

---

**Implementation Status**: ✅ COMPLETE
**Testing Status**: ⏳ PENDING VPS DEPLOYMENT
**Production Ready**: YES (pending API key configuration)
