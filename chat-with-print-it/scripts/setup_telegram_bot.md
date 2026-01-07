# Telegram Bot Setup Guide

## Create Your Bot

1. **Open Telegram** and search for `@BotFather`

2. **Start a chat** with BotFather and send:
   ```
   /newbot
   ```

3. **Choose a name** for your bot:
   ```
   Chat with Print
   ```
   (or any display name you prefer)

4. **Choose a username** (must end in "bot"):
   ```
   chatwithprint_bot
   ```
   (or your preferred unique username)

5. **Save the bot token**
   - BotFather will send you a token like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
   - **CRITICAL:** Save this immediately - you'll need it for `TELEGRAM_BOT_TOKEN`

## Configure Bot Settings

1. **Set bot description** (shown in chat header):
   ```
   /setdescription
   ```
   Then select your bot and send:
   ```
   AI-powered electrical panel analysis. Send a photo of any electrical panel to identify components, detect issues, and get expert troubleshooting guidance in seconds.
   ```

2. **Set about text** (shown in bot profile):
   ```
   /setabouttext
   ```
   Then select your bot and send:
   ```
   Chat with Print analyzes electrical panel photos using AI to help technicians identify equipment and troubleshoot faster. 10 free analyses, then $29/month Pro.
   ```

3. **Set bot commands** (shows in menu):
   ```
   /setcommands
   ```
   Then select your bot and send:
   ```
   start - Start using the bot
   help - Show help and usage instructions
   status - Check your usage and subscription status
   upgrade - Upgrade to Pro for unlimited analyses
   ```

4. **Disable group privacy** (optional, if you want bot to work in groups):
   ```
   /setprivacy
   ```
   Select your bot, then choose "Disable"

## Generate Webhook Secret

On your local machine or VPS, run:

```bash
openssl rand -hex 32
```

Save this output as `TELEGRAM_WEBHOOK_SECRET`

## Environment Variables to Save

After completing the steps above, you should have:

```bash
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_WEBHOOK_SECRET=<output from openssl command>
```

**SECURITY:** Never commit these to git. Store in n8n Variables or environment files.

## Test Your Bot

Before continuing:

1. Search for your bot in Telegram (by username)
2. Send `/start`
3. You should see: "Please use @username" (bot not configured yet - this is expected)

Bot creation is complete! Continue to Phase 2 to configure n8n workflows.
