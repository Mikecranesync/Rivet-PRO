# Import Fixed Workflow to n8n Cloud

## Quick Start

1. Download `rivet_llm_judge_fixed.json` from this directory
2. Go to n8n Cloud → Workflows
3. Click "Import from File"
4. Select the fixed workflow JSON
5. Configure Google API credential
6. Test & activate

---

## Step-by-Step Instructions

### Step 1: Prepare the Workflow File

The fixed workflow is ready at:
```
n8n/workflows/test/rivet_llm_judge_fixed.json
```

**Important:** Before importing, you need to update the credential ID.

Open `rivet_llm_judge_fixed.json` and find line ~170:
```json
"credentials": {
  "googleApi": {
    "id": "YOUR_CREDENTIAL_ID",
    "name": "Google API (Gemini)"
  }
}
```

You have 2 options:
- **Option A:** Leave it as is, then select the credential in n8n UI after import
- **Option B:** Replace `"YOUR_CREDENTIAL_ID"` with your actual credential ID from n8n Cloud

---

### Step 2: Import to n8n Cloud

1. **Login to n8n Cloud**
   - Go to your n8n instance
   - Navigate to "Workflows" section

2. **Import the Workflow**
   - Click the "..." menu or "Add workflow" button
   - Select "Import from File" or "Import from JSON"
   - Upload `rivet_llm_judge_fixed.json`
   - Click "Import"

3. **Verify Import**
   - The workflow should appear named "RIVET LLM Judge (Fixed)"
   - You should see 13 nodes total
   - Check that all nodes are connected (no disconnected nodes)

---

### Step 3: Configure Google API Credential

The "LLM Analysis (Gemini)" node needs your Google API credential.

#### If You Already Have a Google API Credential:

1. Click on the "LLM Analysis (Gemini)" node
2. In the credential dropdown, select your existing "Google API" or "Google Gemini" credential
3. Click "Save"

#### If You Need to Create a Credential:

1. Click on the "LLM Analysis (Gemini)" node
2. In the credential field, click "Create New"
3. Enter:
   - **Credential Name:** "Google API (Gemini)" or similar
   - **API Key:** Your Google API key (from Google AI Studio)
4. Click "Create"
5. The credential should now be selected

**Where to Get a Google API Key:**
1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key
4. Paste into n8n credential field

---

### Step 4: Test the Workflow

1. **Open Workflow Editor**
   - Click on the workflow to open it
   - You should see all nodes laid out

2. **Test Individual Nodes**

   **Test "Extract Prompt Text":**
   - Click on the node
   - Click "Test step"
   - Verify output has: `prompt`, `temperature`, `maxTokens`

   **Test "LLM Analysis (Gemini)":**
   - Click on the node
   - Click "Test step"
   - Should call Gemini API
   - Output should be JSON with `text` field containing evaluation

   **Test "Format Gemini Response":**
   - Click on the node
   - Click "Test step"
   - Output should have `candidates[0].content.parts[0].text`

3. **Test Full Workflow**

   Click "Test workflow" and use test data:
   ```json
   {
     "manual_text": "AC Motor Model XYZ-500\n\nSpecifications:\n- Voltage: 480V\n- HP: 50\n- RPM: 1750\n\nInstallation:\n1. Mount motor securely\n2. Connect power leads\n3. Ground properly\n\nTroubleshooting:\n- Vibration: Check alignment\n- Overheating: Check ventilation",
     "equipment_type": "Motor",
     "manufacturer": "Test Corp"
   }
   ```

   **Expected Response:**
   ```json
   {
     "quality_score": 7.2,
     "criteria": {
       "completeness": 6,
       "technical_accuracy": 8,
       "clarity": 7,
       "troubleshooting_usefulness": 7,
       "metadata_quality": 8
     },
     "feedback": "Brief manual with basic specs...",
     "llm_model_used": "gemini-1.5-flash",
     "error": null,
     "url": ""
   }
   ```

---

### Step 5: Webhook Configuration

1. **Get Webhook URL**
   - Click on "Webhook Trigger" node
   - Copy the Production webhook URL
   - It should look like: `https://your-instance.app.n8n.cloud/webhook/rivet-llm-judge`

2. **Test Webhook with cURL**
   ```bash
   curl -X POST "https://your-instance.app.n8n.cloud/webhook/rivet-llm-judge" \
     -H "Content-Type: application/json" \
     -d '{
       "manual_text": "Test manual content here...",
       "equipment_type": "Motor",
       "manufacturer": "Test Manufacturer"
     }'
   ```

3. **Verify Response**
   - Should return JSON with quality_score and criteria
   - Check n8n execution logs for details

---

### Step 6: Activate the Workflow

1. **Final Check**
   - All nodes configured ✓
   - Test executions passed ✓
   - Webhook responds correctly ✓

2. **Activate**
   - Toggle the "Active" switch in top-right
   - Workflow is now live

3. **Monitor**
   - Go to "Executions" tab
   - Watch for successful webhook calls
   - Check for any errors

---

## Troubleshooting

### Issue: "LLM Analysis (Gemini)" node not found

**Solution:** Your n8n Cloud might not have the native Gemini node.

Try this alternative:
1. Use "Google Gemini Chat Model" node (LangChain version)
2. Or use "HTTP Request" with credential-based authentication (not env var)

### Issue: Gemini response format different than expected

**Solution:** Update "Format Gemini Response" code node.

The native Gemini node might return:
- `text` field
- `output` field
- `response` field
- `content` field

Check the actual output and update line 12 in "Format Gemini Response":
```javascript
const responseText = geminiOutput.text || geminiOutput.output || geminiOutput.response || geminiOutput.content || JSON.stringify(geminiOutput);
```

### Issue: Credential doesn't work

**Solution:** Verify API key permissions.

1. Go to Google AI Studio
2. Check that your API key has Gemini API access enabled
3. Try the key in a test API call:
   ```bash
   curl "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key=YOUR_KEY" \
     -H "Content-Type: application/json" \
     -d '{"contents":[{"parts":[{"text":"test"}]}]}'
   ```

### Issue: Workflow errors on execution

**Solution:** Check execution logs.

1. Go to "Executions" in n8n
2. Click on failed execution
3. See which node failed
4. Check the error message
5. Verify node configuration

---

## Node Configuration Reference

### Extract Prompt Text (Code)
```javascript
const data = $input.item.json;
const prompt = data.gemini_request.contents[0].parts[0].text;
const temperature = data.gemini_request.generationConfig.temperature || 0.1;
const maxTokens = data.gemini_request.generationConfig.maxOutputTokens || 800;

return {
  json: {
    prompt,
    temperature,
    maxTokens,
    url: data.url,
    equipment_type: data.equipment_type,
    manufacturer: data.manufacturer
  }
};
```

### LLM Analysis (Gemini) - Native Node
- **Credential:** Google API
- **Model:** gemini-1.5-flash
- **Prompt:** `={{ $json.prompt }}`
- **Temperature:** `={{ $json.temperature }}`
- **Max Tokens:** `={{ $json.maxTokens }}`
- **Continue on Fail:** Enabled

### Format Gemini Response (Code)
```javascript
const geminiOutput = $input.item.json;
const extractedData = $('Extract Prompt Text').item.json;

const responseText = geminiOutput.text || geminiOutput.output || geminiOutput.response || geminiOutput.content || JSON.stringify(geminiOutput);

const formattedResponse = {
  candidates: [{
    content: {
      parts: [{
        text: responseText
      }]
    }
  }],
  url: extractedData.url,
  equipment_type: extractedData.equipment_type,
  manufacturer: extractedData.manufacturer
};

return { json: formattedResponse };
```

---

## Verify Success

✅ Workflow imports without errors
✅ All 13 nodes visible and connected
✅ Google API credential configured
✅ Test execution completes successfully
✅ Webhook returns quality scores
✅ No errors in execution logs
✅ Workflow activated

**You're done!** The RIVET LLM Judge is now running with native Gemini integration.

---

## Next Steps

1. **Update any integrations** that call this webhook
2. **Monitor quality scores** in production
3. **Archive old workflow** (rivet_llm_judge.json)
4. **Document** the webhook URL for your team

---

## Support

If you encounter issues:
1. Check execution logs in n8n Cloud
2. Verify Google API key has Gemini access
3. Test nodes individually to isolate the issue
4. Check that all connections are correct

**Workflow Files:**
- Fixed: `n8n/workflows/test/rivet_llm_judge_fixed.json`
- Original: `n8n/workflows/test/rivet_llm_judge.json` (backup)
- Changes: `n8n/workflows/test/WORKFLOW_CHANGES.md`
