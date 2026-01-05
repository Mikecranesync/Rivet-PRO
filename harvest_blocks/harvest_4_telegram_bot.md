# HARVEST BLOCK 4: Telegram Bot Integration

**Priority:** HIGH (completes the user interface)
**Duration:** 30 minutes
**Source:** `agent_factory/integrations/telegram/photo_handler.py` (280 lines)

---

## What This Adds

Complete Telegram bot with photo handler. Includes:

1. **Photo download** - Gets highest resolution from Telegram
2. **OCR integration** - Runs `ocr_workflow()` on received photos
3. **Response formatting** - Pretty Markdown messages with equipment data
4. **/start and /help handlers** - User onboarding
5. **Error handling** - Image quality issues, OCR failures

**Why critical:** This is the user interface. Without Telegram bot, users can't interact with the system.

---

## Target File

`rivet/integrations/telegram.py` (NEW FILE - doesn't exist yet)

---

## Complete File Content

Create new file `rivet/integrations/telegram.py`:

```python
"""
Telegram Bot Integration - Photo Handler & Commands

Handles:
- /start - Welcome message
- /help - Usage instructions
- Photo uploads - OCR extraction → equipment data response
"""

import logging
import os
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from rivet.workflows.ocr import ocr_workflow
from rivet.workflows.sme_router import detect_manufacturer
from rivet.models.ocr import OCRResult

logger = logging.getLogger(__name__)


# ============================================================================
# Command Handlers
# ============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    logger.info(f"[Telegram] /start from user {user.id} (@{user.username})")

    welcome_message = f"""👋 **Welcome to Rivet Pro!**

I'm your industrial maintenance AI assistant.

**What I can do:**
📸 Send me a photo of equipment → I'll identify it
❓ Ask me troubleshooting questions → I'll find answers
🔧 Get vendor-specific guidance (Siemens, Rockwell, ABB, etc.)

**Try it:**
1. Send a photo of an equipment nameplate
2. I'll extract manufacturer, model, fault codes
3. Ask me a question about the equipment

Type /help for detailed instructions.
"""

    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    logger.info(f"[Telegram] /help from user {update.effective_user.id}")

    help_message = """**📚 Rivet Pro Help**

**Supported Equipment:**
• Siemens (S7-1200, S7-1500, SINAMICS drives)
• Rockwell/Allen-Bradley (ControlLogix, CompactLogix, PowerFlex)
• ABB (ACS880, IRB robots, AC500 PLCs)
• Schneider (Modicon M340/M580, Altivar drives)
• Mitsubishi (MELSEC iQ-R, FX3U)
• FANUC (CNC, robots)

**How to Use:**
1. **Send Equipment Photo**
   • Take clear photo of nameplate
   • Good lighting, focused on text
   • I'll extract manufacturer, model, fault codes

2. **Ask Questions**
   • "How to reset F0002 fault?"
   • "ControlLogix major fault troubleshooting"
   • "Motor won't start after contactor replacement"

3. **Get Answers**
   • Vendor-specific guidance
   • Safety warnings
   • Step-by-step troubleshooting

**Tips for Best Results:**
✅ Good lighting on nameplate
✅ Focus on text, avoid blur
✅ Include fault codes in photo if visible
❌ Avoid extreme angles
❌ Avoid shadows covering text

Type /start to begin.
"""

    await update.message.reply_text(help_message, parse_mode="Markdown")


# ============================================================================
# Photo Handler
# ============================================================================

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle photo uploads from users.

    Flow:
    1. Download highest resolution photo
    2. Run OCR workflow
    3. Detect manufacturer
    4. Format response with equipment data
    5. Offer to answer questions about equipment
    """
    message = update.message
    user = message.from_user

    logger.info(f"[Telegram] Photo received from user {user.id} (@{user.username})")

    # Get highest resolution photo (last element in list)
    photo = message.photo[-1]

    # Download photo bytes
    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    logger.info(f"[Telegram] Downloaded photo: {len(image_bytes)} bytes")

    # Send "processing" message
    processing_msg = await message.reply_text(
        "📸 Analyzing equipment photo...",
        reply_to_message_id=message.message_id
    )

    try:
        # Run OCR
        ocr_result = await ocr_workflow(bytes(image_bytes))

        logger.info(
            f"[Telegram] OCR complete: {ocr_result.manufacturer} "
            f"{ocr_result.model_number}, confidence={ocr_result.confidence:.0%}"
        )

        # Detect manufacturer
        vendor = detect_manufacturer("", ocr_result)

        # Format response
        response = format_ocr_response(ocr_result, vendor)

        # Update message
        await processing_msg.edit_text(
            response,
            parse_mode="Markdown"
        )

    except ValueError as e:
        # Image quality error
        error_msg = f"❌ **Image Quality Issue**\n\n{str(e)}\n\n"
        error_msg += "**Tips:**\n"
        error_msg += "• Increase lighting (avoid shadows)\n"
        error_msg += "• Hold camera steady (avoid blur)\n"
        error_msg += "• Get closer to nameplate\n"
        error_msg += "• Avoid extreme angles"

        await processing_msg.edit_text(error_msg, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"[Telegram] Photo handler error: {e}")
        await processing_msg.edit_text(
            "❌ **Error Processing Photo**\n\n"
            "Something went wrong. Please try again or contact support.\n\n"
            f"Error: {str(e)[:100]}",
            parse_mode="Markdown"
        )


def format_ocr_response(ocr_result: OCRResult, vendor: Optional[str]) -> str:
    """
    Format OCR result as pretty Telegram message.

    Args:
        ocr_result: Extracted equipment data
        vendor: Detected vendor key ("siemens", "rockwell", etc.)

    Returns:
        Markdown-formatted message string

    Example:
        >>> result = OCRResult(manufacturer="Siemens", model_number="S7-1200", ...)
        >>> format_ocr_response(result, "siemens")
        '✅ **Equipment Detected**\n\n**Manufacturer:** Siemens\n...'
    """
    lines = ["✅ **Equipment Detected**\n"]

    # Basic info
    if ocr_result.manufacturer:
        lines.append(f"**Manufacturer:** {ocr_result.manufacturer}")

    if ocr_result.model_number:
        lines.append(f"**Model:** {ocr_result.model_number}")

    if ocr_result.serial_number:
        lines.append(f"**Serial:** {ocr_result.serial_number}")

    if ocr_result.equipment_type:
        lines.append(f"**Type:** {ocr_result.equipment_type}")

    # Electrical specs (if available)
    specs = []
    if ocr_result.voltage:
        specs.append(ocr_result.voltage)
    if ocr_result.current:
        specs.append(ocr_result.current)
    if ocr_result.horsepower:
        specs.append(ocr_result.horsepower)
    if ocr_result.phase:
        specs.append(ocr_result.phase)

    if specs:
        lines.append(f"**Specs:** {', '.join(specs)}")

    # Fault information (important!)
    if ocr_result.fault_code:
        lines.append(f"\n⚠️ **Fault Code:** `{ocr_result.fault_code}`")

    if ocr_result.error_message:
        lines.append(f"**Error:** {ocr_result.error_message}")

    # Condition assessment
    if ocr_result.condition:
        lines.append(f"\n**Condition:** {ocr_result.condition}")

    if ocr_result.visible_issues:
        lines.append(f"**Issues:** {ocr_result.visible_issues}")

    # Detection confidence
    lines.append(f"\n_Confidence: {ocr_result.confidence:.0%}_")

    # Vendor detection
    if vendor:
        lines.append(f"_Detected vendor: {vendor.title()}_")

    # Call to action
    lines.append("\n💬 **Ask me a question about this equipment!**")
    lines.append("_Example: \"How to troubleshoot this fault?\"_")

    return "\n".join(lines)


# ============================================================================
# Bot Setup & Main
# ============================================================================

def create_bot_application() -> Application:
    """
    Create and configure Telegram bot application.

    Registers all handlers:
    - /start command
    - /help command
    - Photo handler

    Returns:
        Configured Application instance

    Example:
        >>> app = create_bot_application()
        >>> app.run_polling()
    """
    # Get bot token from environment
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in environment")

    # Create application
    app = Application.builder().token(token).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))

    # Register photo handler
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("[Telegram] Bot application configured")
    return app


def main():
    """Run the Telegram bot."""
    logger.info("[Telegram] Starting Rivet Pro bot...")

    # Create and run application
    app = create_bot_application()

    # Run with polling (blocks until stopped)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )

    main()
```

---

## Dependencies

Add python-telegram-bot:

```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
poetry add python-telegram-bot
```

---

## Environment Setup

Add to `.env` file:

```bash
# Telegram Bot Token (get from @BotFather)
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

**How to get bot token:**
1. Message @BotFather on Telegram
2. Send `/newbot`
3. Follow prompts to create bot
4. Copy token and add to `.env`

---

## Validation

```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO

# Test imports
python -c "from rivet.integrations.telegram import create_bot_application; print('✅ Telegram bot OK')"

# Test bot application creation
python -c "
import os
os.environ['TELEGRAM_BOT_TOKEN'] = 'dummy-token-for-test'
from rivet.integrations.telegram import create_bot_application
app = create_bot_application()
print('✅ Bot application created')
"

# Run bot (requires real token in .env)
# python -m rivet.integrations.telegram
```

---

## Testing the Bot

Once deployed:

1. **Find your bot** - Search for bot name in Telegram
2. **Send /start** - Should get welcome message
3. **Send /help** - Should get usage instructions
4. **Send equipment photo** - Should extract data and respond
5. **Ask question** - Should route to appropriate SME

**Expected flow:**
```
User: [sends photo of Siemens S7-1200 nameplate]
Bot: ✅ Equipment Detected
     Manufacturer: Siemens
     Model: S7-1200 CPU 1214C
     Fault Code: F0002
     ...
     💬 Ask me a question about this equipment!

User: "How to reset F0002 fault?"
Bot: [Routes to Siemens SME → returns troubleshooting steps]
```

---

## Integration Notes

1. **Photo handler is async** - Uses `await` for OCR workflow
2. **Error handling** - Catches image quality issues, OCR failures
3. **Response formatting** - Uses Markdown for pretty messages
4. **Highest resolution** - Gets best quality photo from Telegram
5. **User context** - Can track conversation history if needed

---

## Bot Deployment Options

**Option 1: Local Development**
```bash
python -m rivet.integrations.telegram
```

**Option 2: Docker**
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install poetry && poetry install
CMD ["poetry", "run", "python", "-m", "rivet.integrations.telegram"]
```

**Option 3: Cloud Hosting**
- Railway.app (free tier)
- Render.com (free tier)
- Heroku (paid)
- AWS Lambda + API Gateway

---

## Next Steps

After validating bot works:

1. **HARVEST 5** (optional) - Enhanced response formatting with citations/safety
2. **HARVEST 6** (optional) - Print/schematic analyzer
3. **Production deployment** - Choose hosting platform
4. **Monitoring** - Add logging, error tracking (Sentry)

---

## Success Criteria

Bot is complete when:
- ✅ User sends photo → bot extracts equipment data
- ✅ Bot responds within 5 seconds
- ✅ /start and /help commands work
- ✅ Image quality errors handled gracefully
- ✅ OCR confidence shown to user

**This completes the critical path!** Telegram bot can now process equipment photos.
