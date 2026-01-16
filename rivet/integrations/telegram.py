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
from rivet.workflows.print_analyzer import PrintAnalyzer
from rivet.models.ocr import OCRResult
from rivet.workflows.troubleshoot import TroubleshootResult
from rivet.integrations.atlas import AtlasClient, AtlasNotFoundError, AtlasValidationError

# SME Chat imports
from rivet.services.sme_chat_service import SMEChatService
from rivet.models.sme_chat import SMEVendor, get_sme_name, get_sme_title
from rivet.prompts.sme.personalities import get_personality

logger = logging.getLogger(__name__)

# Global SME chat service instance (initialized lazily)
_sme_chat_service: Optional[SMEChatService] = None


def get_sme_chat_service() -> SMEChatService:
    """Get or create the SME chat service singleton."""
    global _sme_chat_service
    if _sme_chat_service is None:
        _sme_chat_service = SMEChatService()
    return _sme_chat_service


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
📸 **Photo Analysis** - Send me photos and I'll help with:
   • Equipment nameplates (manufacturer, model, serial, fault codes)
   • Schematics & diagrams (ladder logic, wiring, P&ID)
   • Technical drawings analysis

💬 **Troubleshooting** - Ask me questions about:
   • Siemens, Rockwell, ABB, Schneider, Mitsubishi, Fanuc
   • PLC programming
   • VFD configuration
   • Equipment diagnostics

**Get started:**
1. Send a photo of equipment nameplate OR schematic (add caption for diagrams)
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
   Send photos for equipment or schematic analysis:

   **Equipment Nameplates:**
   • Just send the photo
   • I'll extract manufacturer, model, serial, fault codes

   **Schematics/Diagrams:**
   • Add caption with keywords: "schematic", "diagram", "wiring", "ladder"
   • I'll analyze the technical drawing and identify components

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
   ✓ For schematics: add caption like "ladder logic diagram"
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
# SME CHAT HANDLERS
# ============================================================================


# Valid vendor choices for /chat command
VENDOR_CHOICES = {
    "siemens": SMEVendor.SIEMENS,
    "rockwell": SMEVendor.ROCKWELL,
    "allen-bradley": SMEVendor.ROCKWELL,  # Alias
    "ab": SMEVendor.ROCKWELL,  # Alias
    "abb": SMEVendor.ABB,
    "schneider": SMEVendor.SCHNEIDER,
    "mitsubishi": SMEVendor.MITSUBISHI,
    "fanuc": SMEVendor.FANUC,
    "generic": SMEVendor.GENERIC,
}


async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /chat command - Start SME chat session.

    Usage:
    - /chat [vendor] - Start chat with specific vendor SME
    - /chat - Show vendor picker if no vendor specified

    Vendors: siemens, rockwell, abb, schneider, mitsubishi, fanuc, generic
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    args = context.args

    logger.info(f"[SME Chat] /chat command from user {user_id}, args: {args}")

    # Check if already in active chat session
    if context.user_data.get('sme_chat_active'):
        session_id = context.user_data.get('sme_session_id')
        sme_name = context.user_data.get('sme_name', 'Expert')
        await update.message.reply_text(
            f"You're already chatting with **{sme_name}**.\n\n"
            f"Use `/endchat` to end this session first, or just keep chatting!",
            parse_mode="Markdown"
        )
        return

    # Determine vendor
    vendor_str = None
    if args:
        vendor_str = args[0].lower()
        if vendor_str not in VENDOR_CHOICES:
            await update.message.reply_text(
                f"Unknown vendor: `{args[0]}`\n\n"
                f"**Available SME specialists:**\n"
                f"• `siemens` - Hans (German precision)\n"
                f"• `rockwell` - Mike (American practical)\n"
                f"• `abb` - Erik (Safety-focused)\n"
                f"• `schneider` - Pierre (French elegance)\n"
                f"• `mitsubishi` - Takeshi (Japanese detail)\n"
                f"• `fanuc` - Ken (CNC expert)\n"
                f"• `generic` - Alex (Versatile)\n\n"
                f"Example: `/chat siemens`",
                parse_mode="Markdown"
            )
            return

    # If no vendor specified, check for recent equipment context or show picker
    if not vendor_str:
        # Check for equipment context from recent OCR
        pending_equipment = context.user_data.get('pending_equipment')
        if pending_equipment and pending_equipment.get('manufacturer'):
            manufacturer = pending_equipment['manufacturer'].lower()
            # Try to match manufacturer to vendor
            for key, vendor in VENDOR_CHOICES.items():
                if key in manufacturer.lower():
                    vendor_str = key
                    break

        # Still no vendor? Show picker
        if not vendor_str:
            keyboard = [
                [
                    InlineKeyboardButton("🇩🇪 Siemens (Hans)", callback_data="sme_vendor_siemens"),
                    InlineKeyboardButton("🇺🇸 Rockwell (Mike)", callback_data="sme_vendor_rockwell"),
                ],
                [
                    InlineKeyboardButton("🇨🇭 ABB (Erik)", callback_data="sme_vendor_abb"),
                    InlineKeyboardButton("🇫🇷 Schneider (Pierre)", callback_data="sme_vendor_schneider"),
                ],
                [
                    InlineKeyboardButton("🇯🇵 Mitsubishi (Takeshi)", callback_data="sme_vendor_mitsubishi"),
                    InlineKeyboardButton("⚙️ FANUC (Ken)", callback_data="sme_vendor_fanuc"),
                ],
                [
                    InlineKeyboardButton("🔧 General (Alex)", callback_data="sme_vendor_generic"),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "**Start SME Chat Session**\n\n"
                "Choose your specialist based on your equipment:\n",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            return

    # Start the chat session
    await start_sme_session(update, context, vendor_str)


async def start_sme_session(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    vendor_str: str,
    from_callback: bool = False
) -> None:
    """
    Start an SME chat session for the given vendor.

    Args:
        update: Telegram update
        context: Bot context
        vendor_str: Vendor key (siemens, rockwell, etc.)
        from_callback: True if called from callback handler
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Get equipment context if available
    equipment_context = None
    pending_equipment = context.user_data.get('pending_equipment')
    if pending_equipment:
        equipment_context = {
            "model": pending_equipment.get('model'),
            "serial": pending_equipment.get('serial'),
            "recent_faults": [pending_equipment.get('fault')] if pending_equipment.get('fault') else None,
        }

    # Send typing indicator
    if from_callback:
        await update.callback_query.message.chat.send_action(action="typing")
    else:
        await update.message.chat.send_action(action="typing")

    try:
        # Start session via SMEChatService
        sme_service = get_sme_chat_service()
        session = await sme_service.start_session(
            telegram_chat_id=chat_id,
            sme_vendor=vendor_str,
            equipment_context=equipment_context
        )

        # Get personality for greeting
        personality = get_personality(vendor_str)

        # Store session info in user_data
        context.user_data['sme_chat_active'] = True
        context.user_data['sme_session_id'] = str(session.session_id)
        context.user_data['sme_vendor'] = vendor_str
        context.user_data['sme_name'] = personality.name

        # Build greeting message
        greeting = f"**{personality.name}** - {get_sme_title(VENDOR_CHOICES[vendor_str])}\n\n"
        greeting += f"_{personality.tagline}_\n\n"
        greeting += f"{personality.voice.greeting}\n\n"
        greeting += "💬 **Chat mode active** - Just type your questions!\n"
        greeting += "_Type `/endchat` when you're done._"

        if from_callback:
            await update.callback_query.edit_message_text(greeting, parse_mode="Markdown")
        else:
            await update.message.reply_text(greeting, parse_mode="Markdown")

        logger.info(
            f"[SME Chat] Session started: {session.session_id}, "
            f"vendor={vendor_str}, user={user_id}"
        )

    except Exception as e:
        logger.error(f"[SME Chat] Failed to start session: {e}", exc_info=True)
        error_msg = "Sorry, I couldn't start the chat session. Please try again."
        if from_callback:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)


async def endchat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /endchat command - Close active SME chat session.
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    logger.info(f"[SME Chat] /endchat command from user {user_id}")

    # Check if in active chat session
    if not context.user_data.get('sme_chat_active'):
        await update.message.reply_text(
            "You don't have an active chat session.\n\n"
            "Use `/chat` to start one!",
            parse_mode="Markdown"
        )
        return

    # Get session info
    session_id_str = context.user_data.get('sme_session_id')
    sme_name = context.user_data.get('sme_name', 'Expert')

    try:
        # Close session in database
        if session_id_str:
            from uuid import UUID
            sme_service = get_sme_chat_service()
            await sme_service.close_session(UUID(session_id_str))

        # Clear user_data
        context.user_data.pop('sme_chat_active', None)
        context.user_data.pop('sme_session_id', None)
        context.user_data.pop('sme_vendor', None)
        context.user_data.pop('sme_name', None)

        # Get closing phrase from personality
        vendor = context.user_data.get('sme_vendor', 'generic')
        personality = get_personality(vendor)
        closing = personality.voice.closing_phrases[0] if personality.voice.closing_phrases else "Thank you for chatting!"

        await update.message.reply_text(
            f"**Chat session ended** with {sme_name}.\n\n"
            f"_{closing}_\n\n"
            f"Use `/chat` anytime to start a new session!",
            parse_mode="Markdown"
        )

        logger.info(f"[SME Chat] Session closed: {session_id_str}, user={user_id}")

    except Exception as e:
        logger.error(f"[SME Chat] Error closing session: {e}", exc_info=True)
        # Clear user_data anyway
        context.user_data.pop('sme_chat_active', None)
        context.user_data.pop('sme_session_id', None)
        context.user_data.pop('sme_vendor', None)
        context.user_data.pop('sme_name', None)

        await update.message.reply_text(
            "Chat session ended.\n\n"
            "Use `/chat` to start a new session!",
            parse_mode="Markdown"
        )


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
                results = await client.search_equipment(user_id=str(user_id), query=query, limit=10)

            if not results:
                await update.message.reply_text(f"No equipment found for '{query}'")
                return

            # Format results
            lines = ["**Equipment Search Results**\n"]
            for equipment in results[:10]:
                manufacturer = equipment.get("manufacturer", "Unknown")
                model = equipment.get("model_number", "Unknown")
                equipment_id = equipment.get("id")
                equipment_number = equipment.get("equipment_number", "N/A")
                lines.append(f"• **{equipment_number}** ({manufacturer} {model})")
                lines.append(f"  ID: `{equipment_id}`")

            lines.append(f"\nType `/equip view <id>` to see details")
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

        elif action == 'view':
            if len(args) < 2:
                await update.message.reply_text("Usage: `/equip view <id>`", parse_mode="Markdown")
                return

            equipment_id_str = args[1]
            await update.message.chat.send_action(action="typing")

            from uuid import UUID
            async with AtlasClient() as client:
                equipment = await client.get_equipment(UUID(equipment_id_str))

            # Format details
            lines = ["**Equipment Details**\n"]
            lines.append(f"**ID**: `{equipment['id']}`")
            lines.append(f"**Equipment Number**: {equipment.get('equipment_number', 'N/A')}")
            if equipment.get('manufacturer'):
                lines.append(f"**Manufacturer**: {equipment['manufacturer']}")
            if equipment.get('model_number'):
                lines.append(f"**Model**: {equipment['model_number']}")
            if equipment.get('serial_number'):
                lines.append(f"**Serial**: {equipment['serial_number']}")
            if equipment.get('equipment_type'):
                lines.append(f"**Type**: {equipment['equipment_type']}")
            if equipment.get('location'):
                lines.append(f"**Location**: {equipment['location']}")

            lines.append(f"\nCreate work order: `/wo create {equipment['id']}`")
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

    # SME vendor selection callbacks
    if query.data.startswith("sme_vendor_"):
        vendor_str = query.data.replace("sme_vendor_", "")
        await start_sme_session(update, context, vendor_str, from_callback=True)
        return

    if query.data == "create_equip":
        ocr_data = context.user_data.get('pending_equipment')
        if not ocr_data:
            await query.edit_message_text("Equipment data expired. Please send photo again.")
            return

        # Create equipment in Atlas
        try:
            user_id = query.from_user.id
            async with AtlasClient() as client:
                equipment = await client.create_equipment(
                    user_id=str(user_id),
                    manufacturer=ocr_data.get('manufacturer') or 'Unknown',
                    model_number=ocr_data.get('model'),
                    serial_number=ocr_data.get('serial'),
                    equipment_type=ocr_data.get('type'),
                    photo_file_id=context.user_data.get('photo_file_id')
                )

            context.user_data.pop('pending_equipment', None)
            context.user_data.pop('photo_file_id', None)

            await query.edit_message_text(
                f"✅ Equipment created in Atlas!\n\n"
                f"**Equipment Number**: {equipment.get('equipment_number')}\n"
                f"**ID**: `{equipment['id']}`\n"
                f"**Manufacturer**: {equipment.get('manufacturer', 'N/A')}\n"
                f"**Model**: {equipment.get('model_number', 'N/A')}\n"
                f"**Serial**: {equipment.get('serial_number', 'N/A')}\n\n"
                f"Create work order: `/wo create {equipment['id']}`",
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Equipment creation from OCR error: {e}", exc_info=True)
            context.user_data.pop('pending_equipment', None)
            context.user_data.pop('photo_file_id', None)
            await query.edit_message_text(f"❌ Error creating equipment: {str(e)}")

    elif query.data == "skip_equip":
        context.user_data.pop('pending_equipment', None)
        await query.edit_message_text("Equipment creation skipped.")


# ============================================================================
# PHOTO HANDLER - OCR WORKFLOW & PRINT ANALYZER
# ============================================================================


def is_schematic_photo(caption: Optional[str]) -> bool:
    """
    Detect if photo is a technical schematic/diagram based on caption.

    Keywords: schematic, diagram, wiring, ladder, print, drawing, blueprint, P&ID
    """
    if not caption:
        return False

    caption_lower = caption.lower()
    schematic_keywords = [
        "schematic", "diagram", "wiring", "ladder", "print",
        "drawing", "blueprint", "p&id", "electrical", "circuit",
        "panel", "layout", "dwg"
    ]

    return any(keyword in caption_lower for keyword in schematic_keywords)


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle photo messages - Equipment OCR OR Schematic analysis.

    Flow:
    1. Download photo from Telegram
    2. Check caption for schematic keywords
    3a. If schematic: Route to PrintAnalyzer
    3b. If equipment: Route to OCR workflow
    4. Format and send results

    Schematic detection keywords:
    - schematic, diagram, wiring, ladder, print, drawing, blueprint, P&ID
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    caption = update.message.caption

    logger.info(f"Photo received from user {user_id} (@{username}), caption: {caption}")

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

        # Route based on caption keywords
        if is_schematic_photo(caption):
            # SCHEMATIC ANALYSIS
            logger.info(f"Routing to PrintAnalyzer (schematic detected)")
            analyzer = PrintAnalyzer()
            analysis = await analyzer.analyze(bytes(photo_bytes), caption=caption)

            # Format and send schematic analysis
            response = format_schematic_response(analysis, caption)
            await update.message.reply_text(response, parse_mode="Markdown")

            logger.info(
                f"Schematic analysis sent to user {user_id}",
                extra={"user_id": user_id, "caption": caption},
            )
            return

        # EQUIPMENT OCR (default)
        logger.info(f"Routing to OCR workflow (equipment nameplate)")
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
            context.user_data['photo_file_id'] = photo.file_id

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


def format_schematic_response(analysis: str, caption: Optional[str] = None) -> str:
    """
    Format schematic analysis result for Telegram display.

    Args:
        analysis: PrintAnalyzer analysis text
        caption: Optional user caption

    Returns:
        Formatted Telegram message with schematic analysis
    """
    lines = ["📐 **Schematic Analysis**\n"]

    if caption:
        lines.append(f"_User context: {caption}_\n")

    # Add the analysis (already formatted by PrintAnalyzer)
    lines.append(analysis)

    # Add footer
    lines.append("\n" + "─" * 30)
    lines.append("\n💡 **Need more details?**")
    lines.append("Ask a question about this schematic:")
    lines.append("• _\"What voltage is at terminal X1?\"_")
    lines.append("• _\"Where should I check for motor overload?\"_")
    lines.append("• _\"What does component M1 control?\"_")

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
    application.add_handler(CommandHandler("chat", chat_handler))  # SME Chat
    application.add_handler(CommandHandler("endchat", endchat_handler))  # SME Chat

    # Register message handlers
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Register callback handlers (inline buttons)
    application.add_handler(CallbackQueryHandler(callback_handler))

    # Register error handler
    application.add_error_handler(error_handler)

    # Register bot commands with Telegram
    from telegram import BotCommand

    async def post_init(app: Application) -> None:
        """Register commands with Telegram after bot starts."""
        await app.bot.set_my_commands([
            BotCommand("start", "Get started with Rivet"),
            BotCommand("help", "Show available commands"),
            BotCommand("chat", "Start SME chat session"),
            BotCommand("endchat", "End active chat session"),
            BotCommand("status", "Check bot status"),
            BotCommand("tier", "View subscription tier info"),
            BotCommand("equip", "Equipment management (search, create, view)"),
            BotCommand("wo", "Work order management (create, list, view)"),
        ])
        logger.info("Bot commands registered with Telegram")

    application.post_init = post_init

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
