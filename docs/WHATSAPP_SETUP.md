# WhatsApp Cloud API Setup Guide

This guide explains how to configure WhatsApp Cloud API integration for RIVET Pro.

## Prerequisites

1. **Meta Developer Account**: https://developers.facebook.com/
2. **Meta Business Account**: Required for WhatsApp Business API
3. **Verified Business**: Your business must be verified by Meta
4. **HTTPS Endpoint**: Webhooks require a publicly accessible HTTPS URL

## Step 1: Create a Meta App

1. Go to https://developers.facebook.com/apps/
2. Click "Create App"
3. Select "Business" as the app type
4. Enter app name (e.g., "RIVET Pro WhatsApp")
5. Select your Business Account
6. Click "Create App"

## Step 2: Add WhatsApp Product

1. In your app dashboard, click "Add Product"
2. Find "WhatsApp" and click "Set Up"
3. Accept the terms of service

## Step 3: Get Your Credentials

From the WhatsApp section of your app dashboard, note the following:

### Phone Number ID
- Navigate to: WhatsApp > Getting Started
- Find "Phone number ID" (NOT the phone number itself)
- This is a numeric ID like `123456789012345`

### WhatsApp Business Account ID
- In the same section, find "WhatsApp Business Account ID"
- Another numeric ID like `987654321098765`

### Access Token
1. Navigate to: WhatsApp > Getting Started
2. Click "Generate" to create a temporary access token
3. For production, create a System User:
   - Go to Business Settings > Users > System Users
   - Create a new System User with "Admin" role
   - Assign the WhatsApp app with "Full Control"
   - Generate a token with these permissions:
     - `whatsapp_business_management`
     - `whatsapp_business_messaging`

### App Secret
1. Navigate to: Settings > Basic
2. Click "Show" next to App Secret
3. Copy the value (keep this secure!)

### Verify Token
- This is a custom string YOU create
- Choose something secure and random
- Example: Generate with `openssl rand -hex 32`

## Step 4: Configure Environment Variables

Add to your `.env` file:

```bash
# WhatsApp Cloud API Configuration
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_BUSINESS_ACCOUNT_ID=987654321098765
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxxxxxxxxxxx
WHATSAPP_VERIFY_TOKEN=your_random_verify_token_here
WHATSAPP_APP_SECRET=abcdef123456789
```

## Step 5: Configure Webhook URL

1. In your Meta App dashboard, go to: WhatsApp > Configuration
2. Click "Edit" next to Webhook URL
3. Enter your webhook URL:
   - Format: `https://yourdomain.com/whatsapp`
   - For local development with ngrok: `https://abc123.ngrok.io/whatsapp`
4. Enter your Verify Token (the one you created)
5. Click "Verify and Save"

### Subscribe to Webhook Events

After verification, subscribe to these webhook fields:
- `messages` - Incoming messages

## Step 6: Test the Integration

### Test Webhook Verification
```bash
curl "https://yourdomain.com/whatsapp?hub.mode=subscribe&hub.verify_token=YOUR_VERIFY_TOKEN&hub.challenge=test123"
# Should return: test123
```

### Test Sending a Message
```python
from rivet_pro.adapters.whatsapp import send_whatsapp_text

# Send to a test number (must be registered in your test numbers)
await send_whatsapp_text("15551234567", "Hello from RIVET Pro!")
```

### Test Receiving Messages
1. Add your phone number to "Test Numbers" in the Meta dashboard
2. Send a message to your WhatsApp Business number
3. Check logs for incoming webhook data

## Development with ngrok

For local development, use ngrok to expose your local server:

```bash
# Install ngrok (if not installed)
brew install ngrok  # macOS
# or download from https://ngrok.com/

# Start your local server
uvicorn rivet_pro.adapters.web.main:app --reload --port 8000

# In another terminal, expose port 8000
ngrok http 8000
```

Use the ngrok HTTPS URL as your webhook URL in the Meta dashboard.

## Webhook Payload Examples

### Text Message
```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
    "changes": [{
      "value": {
        "messaging_product": "whatsapp",
        "metadata": {
          "display_phone_number": "15551234567",
          "phone_number_id": "PHONE_NUMBER_ID"
        },
        "contacts": [{
          "profile": {"name": "John Doe"},
          "wa_id": "15559876543"
        }],
        "messages": [{
          "id": "wamid.xxx",
          "from": "15559876543",
          "timestamp": "1234567890",
          "type": "text",
          "text": {"body": "Hello!"}
        }]
      },
      "field": "messages"
    }]
  }]
}
```

### Image Message
```json
{
  "entry": [{
    "changes": [{
      "value": {
        "messages": [{
          "id": "wamid.xxx",
          "from": "15559876543",
          "timestamp": "1234567890",
          "type": "image",
          "image": {
            "id": "IMAGE_ID",
            "mime_type": "image/jpeg",
            "sha256": "xxx",
            "caption": "Equipment nameplate"
          }
        }]
      }
    }]
  }]
}
```

## Troubleshooting

### Webhook Verification Fails
1. Check that `WHATSAPP_VERIFY_TOKEN` matches exactly
2. Ensure your endpoint is accessible via HTTPS
3. Check server logs for errors

### Messages Not Received
1. Verify webhook subscription is active
2. Check that you subscribed to `messages` field
3. Ensure the sending number is in test numbers (for test apps)

### Signature Verification Fails
1. Verify `WHATSAPP_APP_SECRET` is correct
2. Check that you're reading the raw request body (not parsed JSON)
3. The signature header is `X-Hub-Signature-256`

### Rate Limits
- Test apps: Limited to messages with registered test numbers
- Production: Subject to WhatsApp Business API rate limits
- See: https://developers.facebook.com/docs/whatsapp/api/rate-limits

## Security Best Practices

1. **Always verify webhook signatures** in production
2. **Use environment variables** for all credentials
3. **Never log access tokens** or app secrets
4. **Rotate tokens** periodically
5. **Restrict test numbers** during development

## Reference Links

- [WhatsApp Cloud API Documentation](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Webhook Setup Guide](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/components)
- [Message Types Reference](https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages)
- [Error Codes](https://developers.facebook.com/docs/whatsapp/cloud-api/support/error-codes)
