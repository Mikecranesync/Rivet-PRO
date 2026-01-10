# Issue #2: LLM Judge Returns Default Values (All Zeros)

**Workflow:** RIVET LLM Judge (ID: QaFV6k14mQroMfat)
**Severity:** CRITICAL
**Status:** FAILED
**Discovered:** 2026-01-10 (E2E Testing)

## Problem Description

The LLM Judge workflow returns default/fallback values (all zeros) instead of actual quality analysis from Gemini LLM. This renders the workflow useless for assessing manual quality.

## Expected Behavior

When manual content is submitted for quality analysis:
1. Extract user query and manual content ✅
2. Optionally fetch manual from URL ✅
3. Prepare LLM prompt with content ✅
4. Send to Gemini 2.5 Flash for analysis ✅
5. **Parse JSON response with quality scores** ❌ **RETURNS ZEROS**
6. Return structured quality assessment ✅ (but with wrong data)

## Actual Behavior

Workflow executes successfully through all nodes, but "Parse LLM Response" returns fallback values instead of actual LLM analysis.

## Reproduction

### Test Input
```json
{
  "user_query": "How do I change the oil on a Caterpillar D9T?",
  "manual_content": "Caterpillar D9T Maintenance Manual. Oil change procedure: 1. Warm up engine for 5 minutes. 2. Locate oil drain plug under engine. 3. Remove drain plug and drain oil. 4. Replace oil filter. 5. Add new oil (45 quarts 15W-40). 6. Check oil level."
}
```

### Expected Output
```json
{
  "quality_score": 75,
  "criteria": {
    "completeness": 8,
    "technical_accuracy": 8,
    "clarity": 9,
    "troubleshooting_usefulness": 6,
    "metadata_quality": 5
  },
  "feedback": "Manual provides clear step-by-step oil change procedure. Includes specific oil capacity (45 quarts) and viscosity grade (15W-40). Missing: torque specs for drain plug, oil filter part number, disposal recommendations.",
  "llm_model_used": "gemini-2.5-flash"
}
```

### Actual Output
```json
{
  "quality_score": 0,
  "criteria": {
    "completeness": 0,
    "technical_accuracy": 0,
    "clarity": 0,
    "troubleshooting_usefulness": 0,
    "metadata_quality": 0
  },
  "feedback": "No feedback provided",
  "llm_model_used": "gemini-2.5-flash",
  "error": null,
  "url": ""
}
```

## Root Cause Analysis

### Execution Trace (Execution ID: 6468)

```
Webhook Trigger → SUCCESS
  ↓
Extract Request Data → SUCCESS (took 1453ms - suspicious delay)
  ↓
Needs Fetch? → false branch (manual_content provided)
  ↓
Pass Through → SUCCESS
  ↓
Merge Content → SUCCESS
  ↓
Prepare LLM Prompt → SUCCESS
  ↓
LLM Analysis (Gemini) → SUCCESS (took 1ms - TOO FAST!)
  ↓
Parse LLM Response → SUCCESS (returned zeros)
  ↓
Respond to Webhook → ERROR (but response sent successfully)
```

### Red Flags

1. **LLM Analysis took 1ms** - This is impossibly fast for a Gemini API call
2. **Extract Request Data took 1453ms** - Unusually long for simple data extraction
3. **Parse LLM Response returned fallback values** - Indicates parsing failure

### Hypothesis 1: LLM API Call Failed Silently

The "LLM Analysis (Gemini)" node may have:
- Failed to connect to Gemini API
- Received empty/error response
- Returned malformed JSON
- Hit timeout/rate limit

Because the node has `continueOnFail: true` (implied by successful execution), it passed an error object to the parser, which couldn't extract quality scores.

### Hypothesis 2: Parser Logic Bug

The "Parse LLM Response" node code likely has a try-catch that returns zeros on any error:

```javascript
try {
  const response = $input.item.json;
  const content = response.choices?.[0]?.message?.content || '{}';
  const parsed = JSON.parse(content);

  return {
    json: {
      quality_score: parsed.quality_score,
      criteria: parsed.criteria,
      feedback: parsed.feedback,
      // ...
    }
  };
} catch (error) {
  // FALLBACK - returns zeros
  return {
    json: {
      quality_score: 0,
      criteria: { /* all zeros */ },
      feedback: "No feedback provided",
      error: error.message  // ← But error is null in output!
    }
  };
}
```

The fact that `error: null` suggests the catch block isn't even executing - the LLM response structure just doesn't match what the parser expects.

### Hypothesis 3: Gemini Response Format Mismatch

Gemini 2.5 Flash may return a different response structure than expected. Common variations:

**Expected structure:**
```javascript
{
  choices: [
    {
      message: {
        content: '{"quality_score": 75, "criteria": {...}, ...}'
      }
    }
  ]
}
```

**Actual Gemini structure (REST API):**
```javascript
{
  candidates: [  // ← Not "choices"!
    {
      content: {
        parts: [  // ← Not "message.content"!
          {
            text: '{"quality_score": 75, ...}'
          }
        ]
      }
    }
  ]
}
```

## Impact

**Critical Business Impact:**
- Cannot assess manual quality
- Test Runner always fails (depends on LLM Judge)
- No way to validate manual search results
- Manual Hunter Tier 1/2 might pass invalid URLs

**Affected Workflows:**
- RIVET LLM Judge (primary failure)
- RIVET Test Runner (cascading failure)
- RIVET Manual Hunter (if quality checking enabled)

## Proposed Solutions

### Solution 1: Add Debug Logging

First, capture the raw LLM response to understand the actual structure:

```javascript
// In "Parse LLM Response" node
const rawResponse = $input.item.json;

// Log to workflow execution data
console.log('RAW GEMINI RESPONSE:', JSON.stringify(rawResponse, null, 2));

// Try multiple parsing strategies
let qualityData = null;

// Strategy 1: OpenAI-style (choices)
try {
  const content = rawResponse.choices?.[0]?.message?.content;
  if (content) {
    qualityData = JSON.parse(content);
  }
} catch (e) {
  console.log('Strategy 1 failed:', e.message);
}

// Strategy 2: Gemini-style (candidates)
if (!qualityData) {
  try {
    const text = rawResponse.candidates?.[0]?.content?.parts?.[0]?.text;
    if (text) {
      qualityData = JSON.parse(text);
    }
  } catch (e) {
    console.log('Strategy 2 failed:', e.message);
  }
}

// Strategy 3: Direct JSON (if response is already parsed)
if (!qualityData) {
  try {
    if (rawResponse.quality_score !== undefined) {
      qualityData = rawResponse;
    }
  } catch (e) {
    console.log('Strategy 3 failed:', e.message);
  }
}

// Return data or fallback
if (qualityData) {
  return { json: qualityData };
} else {
  console.error('ALL PARSING STRATEGIES FAILED', rawResponse);
  return {
    json: {
      quality_score: 0,
      // ... fallback ...
      error: 'Failed to parse LLM response',
      _raw_response: rawResponse  // Include for debugging
    }
  };
}
```

### Solution 2: Fix Gemini API Call

Verify the "LLM Analysis (Gemini)" node configuration:

1. **Check HTTP Request Setup:**
   - URL: `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=API_KEY`
   - Method: POST
   - Body format: Correct for Gemini REST API

2. **Correct Gemini Request Body:**
```json
{
  "contents": [
    {
      "parts": [
        {
          "text": "{{ $json.prompt }}"
        }
      ]
    }
  ],
  "generationConfig": {
    "temperature": 0.3,
    "topK": 40,
    "topP": 0.95,
    "maxOutputTokens": 2048,
    "responseMimeType": "application/json"
  }
}
```

### Solution 3: Use n8n Gemini Node

Instead of manual HTTP Request, use the native `@n8n/n8n-nodes-langchain.googleGemini` node which handles:
- Correct API format automatically
- Response parsing
- Error handling
- Retries

Replace "LLM Analysis (Gemini)" HTTP Request node with:
- Node Type: "Chat Google Gemini"
- Model: "gemini-2.5-flash"
- Response format: JSON
- Output parsing: Automatic

### Solution 4: Add Response Validation

Before parsing, validate the LLM response structure:

```javascript
function validateGeminiResponse(response) {
  // Check if response exists
  if (!response) {
    return { valid: false, error: 'Empty response' };
  }

  // Check Gemini structure
  if (response.candidates && Array.isArray(response.candidates)) {
    const candidate = response.candidates[0];
    if (candidate?.content?.parts?.[0]?.text) {
      return { valid: true, content: candidate.content.parts[0].text };
    }
  }

  // Check OpenAI structure
  if (response.choices && Array.isArray(response.choices)) {
    const choice = response.choices[0];
    if (choice?.message?.content) {
      return { valid: true, content: choice.message.content };
    }
  }

  return { valid: false, error: 'Unknown response format', raw: response };
}
```

## Testing Plan

### Test Cases

1. **Valid Manual Content**
   ```json
   {
     "user_query": "How to change oil?",
     "manual_content": "Oil change procedure: 1. Warm engine. 2. Drain oil. 3. Replace filter. 4. Add new oil."
   }
   ```
   Expected: Quality scores 7-9, detailed feedback

2. **Incomplete Manual**
   ```json
   {
     "user_query": "How to replace transmission?",
     "manual_content": "See dealer for transmission service."
   }
   ```
   Expected: Low completeness score (2-3), feedback about missing details

3. **Invalid/Gibberish Content**
   ```json
   {
     "user_query": "How to fix hydraulics?",
     "manual_content": "asdfkjalsdkfj aksdjf alskdjf"
   }
   ```
   Expected: Low scores across the board, feedback about unintelligible content

4. **URL Fetch Test**
   ```json
   {
     "user_query": "Maintenance schedule?",
     "url": "https://example.com/manual.pdf"
   }
   ```
   Expected: Fetch PDF, extract text, analyze quality

5. **Error Handling**
   - Test with invalid Gemini API key
   - Test with rate-limited API
   - Test with malformed prompt
   Expected: Graceful error messages, not silent zeros

### Success Criteria

- [ ] LLM returns actual analysis (not zeros)
- [ ] Quality scores reflect manual content accurately
- [ ] Feedback is detailed and actionable
- [ ] All test cases return non-zero scores (except where appropriate)
- [ ] Test Runner passes when using LLM Judge
- [ ] Raw LLM response visible in execution logs for debugging

## Files to Modify

1. `n8n/workflows/test/rivet_llm_judge.json`
   - Update "LLM Analysis (Gemini)" node (possibly replace with native node)
   - Rewrite "Parse LLM Response" with multiple parsing strategies
   - Add response validation
   - Add debug logging

## Additional Notes

This is a **blocking issue** for Test Runner and potentially for Manual Hunter quality validation. Without working LLM analysis, we cannot assess whether found manuals are actually useful.

**Priority:** Fix immediately after Manual Hunter cache flow issue.

**Workaround:** Temporarily disable quality checking in Test Runner, accept all URL Validator results above threshold.
