# Slack Monitoring Setup Guide

## Create Slack Workspace (If Needed)

If you don't have a Slack workspace:

1. Go to https://slack.com/create
2. Enter your email
3. Follow the setup wizard
4. Choose a workspace name (e.g., "Chat with Print Operations")

## Create Alert Channel

1. **Open Slack** and click on workspace name (top left)

2. **Create channel:**
   - Click `+` next to "Channels"
   - Channel name: `chat-with-print-alerts`
   - Description: `Automated alerts for Chat with Print bot - new users, errors, payments`
   - Make it **private** if you want (recommended)
   - Click `Create`

## Setup Incoming Webhook

### 1. Add Webhook App

1. **Navigate to App Directory:**
   - Click workspace name → Settings & administration → Manage apps
   - Or visit: https://YOUR-WORKSPACE.slack.com/apps

2. **Search for "Incoming Webhooks"**
   - Click on "Incoming Webhooks"
   - Click `Add to Slack`

3. **Choose channel:**
   - Select `#chat-with-print-alerts`
   - Click `Add Incoming WebHooks integration`

### 2. Configure Webhook

1. **Customize details (optional):**
   - **Descriptive Label:** `Chat with Print Bot Alerts`
   - **Customize Name:** `Chat with Print Bot`
   - **Customize Icon:** Upload a bot/alert icon (optional)

2. **Copy the Webhook URL:**
   ```
   https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
   ```

3. **Save as:**
   ```bash
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
   ```

4. **Click** `Save Settings`

## Test the Webhook

Run this command to verify the webhook works:

```bash
curl -X POST -H 'Content-type: application/json' \
--data '{"text":"🤖 Chat with Print monitoring is online!"}' \
YOUR_WEBHOOK_URL
```

You should see a message appear in `#chat-with-print-alerts`

## Alert Types

Your bot will send Slack notifications for:

- ✅ **New Users:** When someone sends `/start`
- 📸 **Photo Lookups:** Optional real-time lookup tracking
- 💳 **New Pro Subscribers:** When payment completes
- ❌ **Errors:** Critical failures (DB connection, API errors, etc.)
- 📊 **Daily Summary:** Midnight report with stats

## Customize Notifications (Optional)

In your Slack channel:

1. Click channel name → `Integrations`
2. Click on "Incoming Webhook"
3. Adjust notification settings:
   - Mute channel except for @mentions (reduces noise)
   - Set custom keywords for important alerts

## Environment Variable

After completing this guide, you should have:

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
```

**SECURITY:** Never commit this to git. Store in n8n Variables.

## Verify Setup

1. Test message sent successfully
2. Channel receiving notifications
3. Webhook URL saved securely

Setup complete! Continue to Phase 2 to configure n8n workflows.
