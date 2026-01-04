"""
RIVET Pro - Telegram Bot Integration

Main bot handlers for photo OCR and text troubleshooting.
Single-file implementation connecting Telegram to RIVET workflows.

Handlers:
- /start: User onboarding
- /help: Commands and usage info
- Photo: OCR workflow (equipment detection)
- Text: Troubleshooting workflow (4-route system)
"""

import logging
from typing import Optional
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from rivet.config import config, TierLimits
from rivet.workflows.ocr import analyze_image
from rivet.workflows.troubleshoot import troubleshoot
from rivet.models.ocr import OCRResult
from rivet.workflows.troubleshoot import TroubleshootResult
from rivet.integrations.atlas import AtlasClient, AtlasNotFoundError, AtlasValidationError

logger = logging.getLogger(__name__)


# ============================================================================
# COMMAND HANDLERS
# ============================================================================


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start command - User onboarding + Atlas CMMS registration.

    TODO: Integrate harvest block from Harvester (Round 7)
    - Onboarding message
    - Tier detection/setup
    - Welcome flow
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or f"user{user_id}"
    first_name = update.effective_user.first_name or ""
    last_name = update.effective_user.last_name or ""

    logger.info(f"New user started bot: {user_id} (@{username})")

    # Register user in Atlas CMMS
    try:
        async with AtlasClient() as client:
            await client.create_user({
                "email": f"{username}@telegram.local",
                "firstName": first_name or username,
                "lastName": last_name,
                "password": str(user_id),
                "role": "TECHNICIAN"
            })
            logger.info(f"Registered user {username} in Atlas CMMS")
    except AtlasValidationError:
        # User likely already exists
        logger.info(f"User {username} already exists in Atlas CMMS")
    except Exception as e:
        # Don't block onboarding if Atlas registration fails
        logger.warning(f"Atlas registration failed for {username}: {e}")

    welcome_message = f"""
👋 **Welcome to RIVET Pro**, {username}!

I'm your industrial maintenance AI assistant.

**What I can do:**
📸 **Photo Analysis** - Send me equipment photos and I'll identify:
   • Manufacturer & model
   • Serial numbers
   • Fault codes
   • Technical specs

💬 **Troubleshooting** - Ask me questions about:
   • Siemens, Rockwell, ABB, Schneider, Mitsubishi, Fanuc
   • PLC programming
   • VFD configuration
   • Equipment diagnostics

**Get started:**
1. Send a photo of equipment nameplate
2. Or ask a troubleshooting question

Type /help for more commands.
"""

    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /help command - Show available commands.

    TODO: Integrate harvest block from Harvester (Round 7)
    - Command list
    - Usage examples
    - Tier limits display
    """
    user_id = update.effective_user.id

    help_message = """
**RIVET Pro - Commands**

📸 **Photo Analysis**
   Send a clear photo of equipment nameplate or display.
   I'll extract manufacturer, model, serial, fault codes.

💬 **Ask Questions**
   Just type your question:
   • "Why is my S7-1200 showing error F0502?"
   • "How to configure Rockwell ControlLogix IP address?"
   • "ABB ACS880 parameter reset procedure"

**Commands:**
   /start - Start the bot
   /help - Show this help message
   /status - Check your usage stats
   /tier - View subscription tier info

**Tips:**
   ✓ Clear, well-lit photos work best
   ✓ Include manufacturer name in questions for better accuracy
   ✓ Mention fault codes if you see them

**Support:** Contact @rivet_support for help
"""

    await update.message.reply_text(help_message, parse_mode="Markdown")


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /status command - Show user usage statistics.

    TODO: Implement usage tracking integration
    - Query database for user stats
    - Show queries used today
    - Show tier limits
    """
    user_id = update.effective_user.id

    # TODO: Query actual usage from database
    # For now, show placeholder
    status_message = """
**Your RIVET Pro Status**

📊 **Tier:** Beta (Free Trial)
📈 **Usage Today:** 0 / 50 queries
⏰ **Trial Days Remaining:** 7 days

Type /tier to upgrade to Pro for unlimited queries.
"""

    await update.message.reply_text(status_message, parse_mode="Markdown")


async def tier_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /tier command - Show tier information and upgrade options.

    TODO: Integrate Stripe payment flow
    """
    user_id = update.effective_user.id

    tier_message = """
**RIVET Pro - Subscription Tiers**

🆓 **Beta (Free Trial)**
   • 50 queries/day
   • 7-day trial
   • All features included
   • $0/month

⭐ **Pro**
   • 1,000 queries/day
   • Priority support
   • Unlimited equipment library
   • $29/month

👥 **Team**
   • Unlimited queries
   • 10 user licenses
   • Admin dashboard
   • API access
   • $200/month

To upgrade, visit: https://rivet.pro/subscribe
"""

    await update.message.reply_text(tier_message, parse_mode="Markdown")


# ============================================================================
# ATLAS CMMS HANDLERS - Equipment & Work Orders
# ============================================================================


async def equip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /equip command - Equipment management via Atlas CMMS."""
    user_id = update.effective_user.id
    args = context.args

    if not args or args[0] == 'help':
        help_text = """
**Equipment Management Commands**

🔍 `/equip search <query>` - Search equipment
📋 `/equip view <id>` - View equipment details
➕ `/equip create` - Create new equipment

**Examples:**
• `/equip search motor`
• `/equip view 123`
• `/equip create`
"""
        await update.message.reply_text(help_text, parse_mode="Markdown")
        return

    action = args[0]

    try:
        if action == 'search':
            query = ' '.join(args[1:])
            if not query:
                await update.message.reply_text("Usage: `/equip search <query>`", parse_mode="Markdown")
                return

            await update.message.chat.send_action(action="typing")

            async with AtlasClient() as client:
                results = await client.search_assets(query, limit=10)

            if not results:
                await update.message.reply_text(f"No equipment found for '{query}'")
                return

            # Format results
            lines = ["**Equipment Search Results**\n"]
            for asset in results[:10]:
                name = asset.get("name", "Unnamed")
                manufacturer = asset.get("manufacturer", "Unknown")
                model = asset.get("model", "Unknown")
                asset_id = asset.get("id")
                lines.append(f"• **{name}** ({manufacturer} {model})")
                lines.append(f"  ID: `{asset_id}`")

            lines.append(f"\nType `/equip view <id>` to see details")
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

        elif action == 'view':
            if len(args) < 2:
                await update.message.reply_text("Usage: `/equip view <id>`", parse_mode="Markdown")
                return

            asset_id = args[1]
            await update.message.chat.send_action(action="typing")

            async with AtlasClient() as client:
                asset = await client.get_asset(asset_id)

            # Format details
            lines = ["**Equipment Details**\n"]
            lines.append(f"**ID**: `{asset['id']}`")
            lines.append(f"**Name**: {asset.get('name', 'N/A')}")
            if asset.get('manufacturer'):
                lines.append(f"**Manufacturer**: {asset['manufacturer']}")
            if asset.get('model'):
                lines.append(f"**Model**: {asset['model']}")
            if asset.get('serialNumber'):
                lines.append(f"**Serial**: {asset['serialNumber']}")
            if asset.get('category'):
                lines.append(f"**Type**: {asset['category']}")

            lines.append(f"\nCreate work order: `/wo create {asset['id']}`")
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

        elif action == 'create':
            # Start conversation flow
            context.user_data['equip_create_state'] = 'awaiting_name'
            await update.message.reply_text(
                "Let's create new equipment.\n\n"
                "What's the equipment name? (e.g., 'VFD Line 3' or 'Motor Pump 2')"
            )

        else:
            await update.message.reply_text(f"Unknown action: {action}\n\nType `/equip help` for usage.", parse_mode="Markdown")

    except AtlasNotFoundError:
        await update.message.reply_text(f"❌ Equipment not found")
    except Exception as e:
        logger.error(f"Equipment handler error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def wo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /wo command - Work order management via Atlas CMMS."""
    user_id = update.effective_user.id
    args = context.args

    if not args or args[0] == 'help':
        help_text = """
**Work Order Commands**

➕ `/wo create <equipment_id>` - Create work order
📋 `/wo list [status]` - List work orders
👁️ `/wo view <id>` - View work order details
✅ `/wo complete <id>` - Mark complete

**Examples:**
• `/wo create 123`
• `/wo list open`
• `/wo view 456`
• `/wo complete 456`
"""
        await update.message.reply_text(help_text, parse_mode="Markdown")
        return

    action = args[0]

    try:
        if action == 'create':
            if len(args) < 2:
                await update.message.reply_text("Usage: `/wo create <equipment_id>`", parse_mode="Markdown")
                return

            equipment_id = args[1]
            await update.message.chat.send_action(action="typing")

            # Verify equipment exists
            async with AtlasClient() as client:
                asset = await client.get_asset(equipment_id)

            # Start conversation flow
            context.user_data['wo_create_state'] = 'awaiting_issue'
            context.user_data['wo_equipment_id'] = equipment_id
            context.user_data['wo_equipment_name'] = asset.get('name', 'Unknown')

            await update.message.reply_text(
                f"Creating work order for: **{asset.get('name')}**\n\n"
                f"What's the issue or task?",
                parse_mode="Markdown"
            )

        elif action == 'list':
            status = args[1].upper() if len(args) > 1 else None
            await update.message.chat.send_action(action="typing")

            async with AtlasClient() as client:
                result = await client.list_work_orders(status=status, page=0, limit=20)

            wos = result.get('content', [])

            if not wos:
                await update.message.reply_text("No work orders found")
                return

            # Format list
            lines = ["**Work Orders**\n"]
            status_emoji = {"PENDING": "⏳", "IN_PROGRESS": "🔧", "COMPLETED": "✓", "CANCELLED": "❌"}

            for wo in wos[:20]:
                title = wo.get('title', 'Untitled')
                wo_status = wo.get('status', 'UNKNOWN')
                priority = wo.get('priority', 'MEDIUM')
                wo_id = wo.get('id')
                emoji = status_emoji.get(wo_status, "•")
                lines.append(f"{emoji} **{title}** - {priority}")
                lines.append(f"  ID: `{wo_id}` | Status: {wo_status}")

            lines.append(f"\nType `/wo view <id>` for details")
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

        elif action == 'view':
            if len(args) < 2:
                await update.message.reply_text("Usage: `/wo view <id>`", parse_mode="Markdown")
                return

            wo_id = args[1]
            await update.message.chat.send_action(action="typing")

            async with AtlasClient() as client:
                wo = await client.get_work_order(wo_id)

            # Format details
            lines = ["**Work Order Details**\n"]
            lines.append(f"**ID**: `{wo['id']}`")
            lines.append(f"**Title**: {wo.get('title', 'N/A')}")
            if wo.get('description'):
                lines.append(f"**Description**: {wo['description']}")
            lines.append(f"**Status**: {wo.get('status', 'UNKNOWN')}")
            lines.append(f"**Priority**: {wo.get('priority', 'MEDIUM')}")
            if wo.get('assetId'):
                lines.append(f"**Equipment ID**: {wo['assetId']}")

            if wo.get('status') != 'COMPLETED':
                lines.append(f"\nComplete: `/wo complete {wo['id']}`")

            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

        elif action == 'complete':
            if len(args) < 2:
                await update.message.reply_text("Usage: `/wo complete <id>`", parse_mode="Markdown")
                return

            wo_id = args[1]
            await update.message.chat.send_action(action="typing")

            async with AtlasClient() as client:
                await client.complete_work_order(wo_id)

            await update.message.reply_text(
                f"✅ Work order `{wo_id}` marked complete!",
                parse_mode="Markdown"
            )

        else:
            await update.message.reply_text(f"Unknown action: {action}\n\nType `/wo help` for usage.", parse_mode="Markdown")

    except AtlasNotFoundError:
        await update.message.reply_text("❌ Work order or equipment not found")
    except Exception as e:
        logger.error(f"Work order handler error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def handle_equipment_creation_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle multi-step equipment creation conversation."""
    state = context.user_data['equip_create_state']

    if state == 'awaiting_name':
        context.user_data['equip_name'] = text
        context.user_data['equip_create_state'] = 'awaiting_manufacturer'
        await update.message.reply_text("Manufacturer? (or type 'skip')")

    elif state == 'awaiting_manufacturer':
        context.user_data['equip_manufacturer'] = None if text.lower() == 'skip' else text
        context.user_data['equip_create_state'] = 'awaiting_model'
        await update.message.reply_text("Model number? (or type 'skip')")

    elif state == 'awaiting_model':
        context.user_data['equip_model'] = None if text.lower() == 'skip' else text
        context.user_data['equip_create_state'] = 'awaiting_serial'
        await update.message.reply_text("Serial number? (or type 'skip')")

    elif state == 'awaiting_serial':
        context.user_data['equip_serial'] = None if text.lower() == 'skip' else text

        # Create equipment in Atlas
        await update.message.chat.send_action(action="typing")

        try:
            async with AtlasClient() as client:
                asset = await client.create_asset({
                    "name": context.user_data['equip_name'],
                    "manufacturer": context.user_data.get('equip_manufacturer'),
                    "model": context.user_data.get('equip_model'),
                    "serialNumber": context.user_data.get('equip_serial')
                })

            # Clear conversation state
            context.user_data.clear()

            await update.message.reply_text(
                f"✅ Equipment created!\n\n"
                f"**ID**: `{asset['id']}`\n"
                f"**Name**: {asset['name']}\n\n"
                f"Create work order: `/wo create {asset['id']}`",
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Equipment creation error: {e}", exc_info=True)
            context.user_data.clear()
            await update.message.reply_text(f"❌ Error creating equipment: {str(e)}")


async def handle_wo_creation_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle multi-step work order creation conversation."""
    state = context.user_data['wo_create_state']

    if state == 'awaiting_issue':
        context.user_data['wo_description'] = text
        context.user_data['wo_create_state'] = 'awaiting_priority'
        await update.message.reply_text(
            "Priority?\n\n"
            "1 = LOW\n"
            "2 = MEDIUM\n"
            "3 = HIGH\n"
            "4 = CRITICAL"
        )

    elif state == 'awaiting_priority':
        priority_map = {'1': 'LOW', '2': 'MEDIUM', '3': 'HIGH', '4': 'CRITICAL'}
        priority = priority_map.get(text, 'MEDIUM')

        # Create work order
        await update.message.chat.send_action(action="typing")

        try:
            async with AtlasClient() as client:
                wo = await client.create_work_order({
                    "title": context.user_data['wo_description'][:100],
                    "description": context.user_data['wo_description'],
                    "priority": priority,
                    "assetId": context.user_data['wo_equipment_id'],
                    "status": "PENDING"
                })

            # Clear conversation state
            equipment_name = context.user_data['wo_equipment_name']
            context.user_data.clear()

            await update.message.reply_text(
                f"✅ Work order created!\n\n"
                f"**ID**: `{wo['id']}`\n"
                f"**Equipment**: {equipment_name}\n"
                f"**Priority**: {priority}\n"
                f"**Status**: PENDING\n\n"
                f"View: `/wo view {wo['id']}`",
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Work order creation error: {e}", exc_info=True)
            context.user_data.clear()
            await update.message.reply_text(f"❌ Error creating work order: {str(e)}")


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks."""
    query = update.callback_query
    await query.answer()

    if query.data == "create_equip":
        ocr_data = context.user_data.get('pending_equipment')
        if not ocr_data:
            await query.edit_message_text("Equipment data expired. Please send photo again.")
            return

        # Create asset in Atlas
        try:
            async with AtlasClient() as client:
                asset = await client.create_asset({
                    "name": f"{ocr_data.get('manufacturer', 'Unknown')} {ocr_data.get('model', '')}".strip(),
                    "manufacturer": ocr_data.get('manufacturer'),
                    "model": ocr_data.get('model'),
                    "serialNumber": ocr_data.get('serial'),
                    "category": ocr_data.get('type'),
                    "description": f"Voltage: {ocr_data.get('voltage', 'N/A')}, Current: {ocr_data.get('current', 'N/A')}"
                })

            context.user_data.pop('pending_equipment', None)

            await query.edit_message_text(
                f"✅ Equipment created in Atlas!\n\n"
                f"**ID**: `{asset['id']}`\n"
                f"**Name**: {asset.get('name')}\n"
                f"**Manufacturer**: {asset.get('manufacturer', 'N/A')}\n"
                f"**Model**: {asset.get('model', 'N/A')}\n\n"
                f"Create work order: `/wo create {asset['id']}`",
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Equipment creation from OCR error: {e}", exc_info=True)
            context.user_data.pop('pending_equipment', None)
            await query.edit_message_text(f"❌ Error creating equipment: {str(e)}")

    elif query.data == "skip_equip":
        context.user_data.pop('pending_equipment', None)
        await query.edit_message_text("Equipment creation skipped.")


# ============================================================================
# PHOTO HANDLER - OCR WORKFLOW
# ============================================================================


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle photo messages - Equipment OCR analysis.

    Flow:
    1. Download photo from Telegram
    2. Validate image quality
    3. Call analyze_image()
    4. Format and send results

    TODO: Integrate harvest block from Harvester (Round 7)
    - Photo download logic
    - Response formatting
    - Error handling
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"

    logger.info(f"Photo received from user {user_id} (@{username})")

    # Send typing indicator
    await update.message.chat.send_action(action="typing")

    try:
        # Download photo (get highest resolution)
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()

        logger.info(
            f"Photo downloaded: {len(photo_bytes)} bytes",
            extra={"user_id": user_id, "file_id": photo.file_id},
        )

        # Call OCR workflow
        result: OCRResult = await analyze_image(
            image_bytes=bytes(photo_bytes),
            user_id=str(user_id),
            skip_quality_check=False,
            min_confidence=0.5,  # Lowered from implicit 0.7
        )

        # Format response
        response = format_ocr_response(result)

        # Add "Create Equipment?" button if OCR successful
        if result.manufacturer or result.model_number:
            # Store OCR data for callback
            context.user_data['pending_equipment'] = {
                "manufacturer": result.manufacturer,
                "model": result.model_number,
                "serial": result.serial_number,
                "type": result.equipment_type,
                "voltage": result.voltage,
                "current": result.current
            }

            # Add inline keyboard
            keyboard = [[
                InlineKeyboardButton("✓ Create Equipment", callback_data="create_equip"),
                InlineKeyboardButton("✗ Skip", callback_data="skip_equip")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(response, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            # No manufacturer/model found, send without buttons
            await update.message.reply_text(response, parse_mode="Markdown")

        logger.info(
            f"OCR result sent to user {user_id}",
            extra={
                "user_id": user_id,
                "manufacturer": result.manufacturer,
                "model": result.model_number,
                "confidence": result.confidence,
                "cost_usd": result.cost_usd,
            },
        )

    except Exception as e:
        logger.error(
            f"Photo processing failed for user {user_id}: {e}",
            exc_info=True,
            extra={"user_id": user_id},
        )

        error_message = """
❌ **Error Processing Photo**

I couldn't analyze this photo. Please try:
• Taking a clearer photo
• Better lighting
• Getting closer to the nameplate
• Ensuring text is readable

If the problem persists, contact support: @rivet_support
"""
        await update.message.reply_text(error_message, parse_mode="Markdown")


# ============================================================================
# MESSAGE HANDLER - TROUBLESHOOTING WORKFLOW
# ============================================================================


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle text messages - Conversation flows OR troubleshooting queries.

    Flow:
    1. Check if user is in active conversation flow (equipment/WO creation)
    2. If yes, route to appropriate handler
    3. If no, call troubleshoot() workflow
    4. Format response by route (KB/SME/Research/General)
    5. Send answer with metadata

    TODO: Integrate harvest block from Harvester (Round 7)
    - Query preprocessing
    - Response formatting by route
    - Safety warning display
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    text = update.message.text

    # Check for active conversation flows first
    if 'equip_create_state' in context.user_data:
        await handle_equipment_creation_flow(update, context, text)
        return

    if 'wo_create_state' in context.user_data:
        await handle_wo_creation_flow(update, context, text)
        return

    # Default: troubleshooting workflow
    query = text

    logger.info(
        f"Query received from user {user_id}: {query[:100]}...",
        extra={"user_id": user_id},
    )

    # Send typing indicator
    await update.message.chat.send_action(action="typing")

    try:
        # Call troubleshooting workflow
        result: TroubleshootResult = await troubleshoot(
            query=query,
            user_id=str(user_id),
        )

        # Format response
        response = format_troubleshoot_response(result)

        # Send result
        await update.message.reply_text(response, parse_mode="Markdown")

        logger.info(
            f"Troubleshoot result sent to user {user_id}",
            extra={
                "user_id": user_id,
                "route": result.route,
                "confidence": result.confidence,
                "manufacturer": result.manufacturer,
                "cost_usd": result.cost_usd,
            },
        )

    except Exception as e:
        logger.error(
            f"Query processing failed for user {user_id}: {e}",
            exc_info=True,
            extra={"user_id": user_id},
        )

        error_message = """
❌ **Error Processing Query**

I encountered an error processing your question.
Please try rephrasing or contact support: @rivet_support
"""
        await update.message.reply_text(error_message, parse_mode="Markdown")


# ============================================================================
# RESPONSE FORMATTING
# ============================================================================


def format_ocr_response(result: OCRResult) -> str:
    """
    Format OCR result for Telegram display.

    TODO: Integrate harvest block from Harvester (Round 7)
    - Improve formatting
    - Add emoji indicators
    - Include confidence visualization
    """
    lines = ["📸 **Equipment Detected**\n"]

    if result.manufacturer:
        lines.append(f"🏭 **Manufacturer:** {result.manufacturer}")

    if result.model_number:
        lines.append(f"🔢 **Model:** {result.model_number}")

    if result.serial_number:
        lines.append(f"#️⃣ **Serial:** {result.serial_number}")

    if result.fault_code:
        lines.append(f"⚠️ **Fault Code:** {result.fault_code}")

    if result.rated_voltage:
        lines.append(f"⚡ **Voltage:** {result.rated_voltage}")

    if result.rated_current:
        lines.append(f"🔌 **Current:** {result.rated_current}")

    if result.equipment_type:
        lines.append(f"⚙️ **Type:** {result.equipment_type}")

    # Metadata
    lines.append(f"\n📊 **Confidence:** {result.confidence:.0%}")
    lines.append(f"🤖 **Provider:** {result.provider}")

    if result.raw_text:
        lines.append(f"\n📝 **Extracted Text:**\n```\n{result.raw_text[:200]}...\n```")

    return "\n".join(lines)


def format_troubleshoot_response(result: TroubleshootResult) -> str:
    """
    Format troubleshooting result for Telegram display.

    TODO: Integrate harvest block from Harvester (Round 7)
    - Route-specific formatting
    - Safety warning display
    - Source citations
    """
    lines = []

    # Route indicator
    route_emoji = {
        "kb": "📚",
        "sme": "👨‍🔧",
        "research": "🔬",
        "general": "🤖",
    }
    emoji = route_emoji.get(result.route, "💬")

    lines.append(f"{emoji} **Answer** (via {result.route.upper()} route)\n")

    # Main answer
    lines.append(result.answer)

    # Safety warnings
    if result.safety_warnings:
        lines.append("\n⚠️ **Safety Warnings:**")
        for warning in result.safety_warnings:
            lines.append(f"• {warning}")

    # Metadata
    lines.append(f"\n📊 **Confidence:** {result.confidence:.0%}")

    if result.manufacturer:
        lines.append(f"🏭 **Manufacturer:** {result.manufacturer}")

    if result.sme_vendor:
        lines.append(f"👨‍🔧 **SME:** {result.sme_vendor.title()} Expert")

    # Sources
    if result.sources:
        lines.append("\n📖 **Sources:**")
        for source in result.sources[:3]:  # Limit to 3
            lines.append(f"• {source}")

    return "\n".join(lines)


# ============================================================================
# ERROR HANDLER
# ============================================================================


async def error_handler(update: Optional[Update], context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle errors in the bot.

    TODO: Integrate harvest block from Harvester (Round 7)
    - Error classification
    - User-friendly error messages
    - Admin notifications for critical errors
    """
    logger.error(f"Update {update} caused error: {context.error}", exc_info=context.error)

    if update and update.effective_message:
        error_message = """
❌ **Oops! Something went wrong.**

Our team has been notified. Please try again in a moment.

If the issue persists, contact support: @rivet_support
"""
        await update.effective_message.reply_text(error_message, parse_mode="Markdown")


# ============================================================================
# BOT SETUP
# ============================================================================


def setup_bot() -> Application:
    """
    Configure and return the Telegram bot application.

    TODO: Integrate harvest block from Harvester (Round 7)
    - Bot configuration
    - Handler registration
    - Middleware setup
    """
    # Create application
    application = Application.builder().token(config.telegram_bot_token).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("status", status_handler))
    application.add_handler(CommandHandler("tier", tier_handler))
    application.add_handler(CommandHandler("equip", equip_handler))  # Atlas CMMS
    application.add_handler(CommandHandler("wo", wo_handler))  # Atlas CMMS

    # Register message handlers
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Register callback handlers (inline buttons)
    application.add_handler(CallbackQueryHandler(callback_handler))

    # Register error handler
    application.add_error_handler(error_handler)

    logger.info("Telegram bot configured successfully")

    return application


# ============================================================================
# MAIN
# ============================================================================


def main():
    """
    Main entry point for Telegram bot.

    Run with: python -m rivet.integrations.telegram
    """
    # Configure logging
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    # Log configuration status
    config.log_status()

    # Validate telegram token
    if not config.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set in environment!")
        return

    # Setup and run bot
    logger.info("Starting RIVET Pro Telegram bot...")
    application = setup_bot()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
