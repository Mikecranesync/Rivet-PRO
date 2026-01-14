"""
Telegram bot adapter for Rivet Pro.
Handles all Telegram-specific interaction logic.
"""

from typing import Optional
from uuid import UUID
from datetime import time as datetime_time
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from rivet_pro.config.settings import settings
from rivet_pro.infra.observability import get_logger
from rivet_pro.infra.database import Database
from rivet_pro.core.services.equipment_service import EquipmentService
from rivet_pro.core.services.work_order_service import WorkOrderService
from rivet_pro.core.services.usage_service import UsageService, FREE_TIER_LIMIT
from rivet_pro.core.services.stripe_service import StripeService
from rivet_pro.core.services.manual_service import ManualService
from rivet_pro.core.services.feedback_service import FeedbackService
from rivet_pro.core.services.alerting_service import AlertingService
from rivet_pro.core.services.kb_analytics_service import KnowledgeBaseAnalytics
from rivet_pro.core.utils import format_equipment_response

logger = get_logger(__name__)


class TelegramBot:
    """
    Telegram bot adapter.
    Manages bot lifecycle and message routing.
    """

    def __init__(self):
        self.application: Application = None
        self.db = Database()
        self.equipment_service = None  # Initialized after db connects
        self.work_order_service = None  # Initialized after db connects
        self.usage_service = None  # Initialized after db connects
        self.stripe_service = None  # Initialized after db connects
        self.manual_service = None  # Initialized after db connects
        self.feedback_service = None  # Initialized after db connects
        self.kb_analytics_service = None  # Initialized after db connects

        # Initialize alerting service for Ralph notifications (RALPH-BOT-3)
        self.alerting_service = AlertingService(
            bot_token=settings.telegram_bot_token,
            ralph_chat_id="8445149012"  # Ralph's Telegram chat ID
        )

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /start command.
        This is the only slash command - used for initial registration.
        Creates user in database if not exists (idempotent).
        """
        user = update.effective_user
        logger.info(f"User started bot | user_id={user.id} | username={user.username}")

        # Create or get user in database (idempotent - won't error on duplicate)
        try:
            from datetime import datetime, timedelta

            result = await self.db.fetchrow(
                """
                INSERT INTO users (telegram_id, full_name, username, subscription_tier, subscription_status, created_at)
                VALUES ($1, $2, $3, 'free', 'active', NOW())
                ON CONFLICT (telegram_id) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    username = EXCLUDED.username,
                    last_active = NOW()
                RETURNING id, subscription_tier, created_at
                """,
                user.id,
                user.full_name or user.first_name,
                user.username
            )

            if result:
                # Check if user was just created (within last 5 seconds)
                is_new = result['created_at'].replace(tzinfo=None) > (
                    datetime.utcnow() - timedelta(seconds=5)
                )
                if is_new:
                    logger.info(f"User created | telegram_id={user.id} | tier=free")
                else:
                    logger.info(f"User exists | telegram_id={user.id} | tier={result['subscription_tier']}")

        except Exception as e:
            logger.error(f"Failed to create/get user | telegram_id={user.id} | error={e}")

        welcome_message = (
            f"👋 Hey {user.first_name}, I'm RIVET.\n\n"
            "Send me a photo of any equipment nameplate and I'll find you the manual. "
            "Try it now 👇"
        )

        await update.message.reply_text(welcome_message)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle all incoming messages (text, photos, etc.).
        This is the main entry point for user interaction.
        """
        user = update.effective_user
        message = update.message

        # Log the interaction
        content_type = "text"
        if message.photo:
            content_type = "photo"
        elif message.document:
            content_type = "document"

        logger.info(
            f"Received message | user_id={user.id} | type={content_type} | "
            f"text={'...' if message.text and len(message.text) > 50 else message.text}"
        )

        # Route based on message type
        try:
            if message.photo:
                await self._handle_photo(update, context)
            elif message.text:
                await self._handle_text(update, context)
            else:
                await update.message.reply_text(
                    "I can help with photos of equipment nameplates or questions about equipment. "
                    "Try sending me a photo!"
                )
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

            # Send critical alert to Ralph (RALPH-BOT-3)
            await self.alerting_service.alert_critical(
                error=e,
                context={
                    "service": "TelegramBot.handle_message",
                    "content_type": content_type,
                    "user_id": str(user.id),
                    "message_text": message.text[:100] if message.text else None
                },
                user_id=str(user.id),
                service="TelegramBot"
            )

            await update.message.reply_text(
                "⚠️ Something went wrong processing your request. Please try again."
            )

    async def _handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle photo messages with OCR analysis and streaming responses.
        """
        from rivet_pro.core.services import analyze_image

        user_id = str(update.effective_user.id)
        telegram_user_id = update.effective_user.id

        # Check usage limits before processing
        allowed, count, reason = await self.usage_service.can_use_service(telegram_user_id)
        
        if not allowed:
            # Generate Stripe checkout link inline for better conversion
            try:
                checkout_url = await self.stripe_service.create_checkout_session(telegram_user_id)
                upgrade_cta = f'👉 <a href="{checkout_url}">Subscribe now</a>'
            except Exception as e:
                logger.warning(f"Could not generate checkout URL: {e}")
                upgrade_cta = "Reply /upgrade to get started!"
            
            await update.message.reply_text(
                f"⚠️ <b>Free Limit Reached</b>\n\n"
                f"You've used all {FREE_TIER_LIMIT} free equipment lookups.\n\n"
                f"🚀 <b>Upgrade to RIVET Pro</b> for:\n"
                f"• Unlimited equipment lookups\n"
                f"• PDF manual chat\n"
                f"• Work order management\n"
                f"• Priority support\n\n"
                f"💰 <b>Just $29/month</b>\n\n"
                f"{upgrade_cta}",
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            return

        # Send initial message with streaming
        msg = await update.message.reply_text("🔍 Analyzing nameplate...")

        try:
            # Download photo (get highest resolution)
            photo = await update.message.photo[-1].get_file()
            photo_bytes = await photo.download_as_bytearray()

            logger.info(f"Downloaded photo | user_id={user_id} | size={len(photo_bytes)} bytes")

            # Update message: OCR in progress
            await msg.edit_text("🔍 Analyzing nameplate...\n⏳ Reading text from image...")

            # Run OCR analysis
            result = await analyze_image(
                image_bytes=photo_bytes,
                user_id=user_id
            )

            # Handle OCR errors
            if hasattr(result, 'error') and result.error:
                await msg.edit_text(
                    f"❌ {result.error}\n\n"
                    "Try taking a clearer photo with good lighting and focus on the nameplate."
                )
                return

            # Create or match equipment in CMMS
            equipment_id = None
            equipment_number = None
            is_new = False

            try:
                equipment_id, equipment_number, is_new = await self.equipment_service.match_or_create_equipment(
                    manufacturer=result.manufacturer,
                    model_number=result.model_number,
                    serial_number=result.serial_number,
                    equipment_type=getattr(result, 'equipment_type', None),
                    location=None,  # Can be added later via conversation
                    user_id=f"telegram_{user_id}"
                )
                logger.info(
                    f"Equipment {'created' if is_new else 'matched'} | "
                    f"equipment_number={equipment_number} | user_id={user_id}"
                )
            except Exception as e:
                logger.error(f"Failed to create/match equipment: {e}", exc_info=True)
                # Continue anyway - OCR succeeded even if CMMS failed

            # Update message: Searching for manual
            await msg.edit_text(
                "🔍 Analyzing nameplate...\n"
                "⏳ Reading text from image...\n"
                "📖 Searching for manual..."
            )

            # KB-003: Search knowledge base first, then external if needed
            manual_result = None
            kb_result = None
            if result.manufacturer and result.model_number:
                try:
                    # Step 1: Check knowledge base
                    kb_result = await self._search_knowledge_base(
                        manufacturer=result.manufacturer,
                        model=result.model_number,
                        equipment_type=getattr(result, 'equipment_type', None)
                    )

                    if kb_result:
                        confidence = kb_result.get('confidence', 0.0)

                        # High confidence (≥0.85): Use KB result, skip external search
                        if confidence >= 0.85:
                            manual_result = kb_result
                            logger.info(
                                f"KB hit (high confidence) | user_id={user_id} | "
                                f"confidence={confidence:.2f} | Skipping external search"
                            )

                            # Increment usage_count for this atom
                            await self.db.pool.execute(
                                "UPDATE knowledge_atoms SET usage_count = usage_count + 1 WHERE atom_id = $1",
                                kb_result['atom_id']
                            )

                        # Medium confidence (0.40-0.85): Use KB but also trigger external search
                        elif confidence >= 0.40:
                            manual_result = kb_result
                            logger.info(
                                f"KB hit (medium confidence) | user_id={user_id} | "
                                f"confidence={confidence:.2f} | Also trying external search"
                            )

                            # Increment usage_count
                            await self.db.pool.execute(
                                "UPDATE knowledge_atoms SET usage_count = usage_count + 1 WHERE atom_id = $1",
                                kb_result['atom_id']
                            )

                            # Try external search as backup
                            try:
                                external_result = await self.manual_service.search_manual(
                                    manufacturer=result.manufacturer,
                                    model=result.model_number,
                                    timeout=15
                                )
                                # If external finds different/better result, use it
                                if external_result and external_result.get('url') != kb_result.get('url'):
                                    logger.info(
                                        f"External search found different manual | "
                                        f"kb_url={kb_result.get('url')} | "
                                        f"external_url={external_result.get('url')}"
                                    )
                                    # Use external result but keep KB as fallback
                                    manual_result = external_result
                            except Exception as e:
                                logger.error(f"External search failed (using KB result): {e}")
                                # Keep using KB result

                        # Low confidence (<0.40): Fall through to external search
                        else:
                            logger.info(
                                f"KB hit (low confidence) | user_id={user_id} | "
                                f"confidence={confidence:.2f} | Using external search"
                            )
                            kb_result = None  # Ignore low confidence result

                    # Step 2: If no KB result or low confidence, use external search
                    if not manual_result:
                        manual_result = await self.manual_service.search_manual(
                            manufacturer=result.manufacturer,
                            model=result.model_number,
                            timeout=15
                        )

                    if manual_result:
                        logger.info(
                            f"Manual found | user_id={user_id} | "
                            f"url={manual_result.get('url')} | "
                            f"cached={manual_result.get('cached', False)}"
                        )
                    else:
                        logger.info(f"Manual not found | user_id={user_id}")

                except Exception as e:
                    logger.error(f"Manual search failed: {e}", exc_info=True)
                    # Continue without manual if search fails

            # Create knowledge atom if manual was found (CRITICAL-KB-001, KB-002)
            if manual_result and result.manufacturer and result.model_number:
                try:
                    # Create interaction record first (KB-001)
                    interaction_id = None
                    try:
                        interaction_id = await self.db.fetchval(
                            """
                            INSERT INTO interactions (
                                user_id, interaction_type, outcome, created_at
                            )
                            VALUES (
                                (SELECT id FROM users WHERE telegram_id = $1),
                                'manual_lookup', 'manual_delivered', NOW()
                            )
                            RETURNING id
                            """,
                            str(update.effective_user.id)
                        )
                        logger.info(f"Created interaction {interaction_id} for manual lookup")
                    except Exception as e:
                        logger.warning(f"Failed to create interaction: {e}")
                        # Continue anyway - don't break user experience

                    # Create atom with interaction link
                    await self._create_manual_atom(
                        manufacturer=result.manufacturer,
                        model=result.model_number,
                        equipment_type=getattr(result, 'equipment_type', None),
                        manual_url=manual_result.get('url'),
                        confidence=min(result.confidence, 0.95),  # Cap at 0.95
                        source_id=str(user_id),
                        interaction_id=interaction_id  # Pass interaction_id for linking
                    )
                except Exception as e:
                    logger.error(f"Failed to create knowledge atom: {e}", exc_info=True)
                    # Don't fail the user interaction if atom creation fails

            # Format equipment response with manual link
            equipment_data = {
                'manufacturer': result.manufacturer,
                'model': result.model_number or 'Unknown',
                'serial': result.serial_number,
                'confidence': result.confidence
            }

            # Add error code if detected
            if hasattr(result, 'error_code') and result.error_code:
                equipment_data['error_code'] = result.error_code

            response = format_equipment_response(equipment_data, manual_result)

            # Add equipment number if created/matched
            if equipment_number:
                status = "🆕 Created" if is_new else "✓ Matched"
                response += f"\n\n<b>Equipment ID:</b> {equipment_number} ({status})"

            # Add component type if detected
            if hasattr(result, 'component_type') and result.component_type:
                response += f"\n<b>Type:</b> {result.component_type}"

            # Record this lookup for usage tracking
            await self.usage_service.record_lookup(
                telegram_user_id=telegram_user_id,
                equipment_id=equipment_id,
                lookup_type="photo_ocr"
            )
            
            # Show remaining lookups for free users
            if reason == 'under_limit':
                remaining = FREE_TIER_LIMIT - count - 1
                if remaining > 0:
                    response += f"\n\n📊 _{remaining} free lookups remaining_"
                else:
                    response += f"\n\n📊 _This was your last free lookup!_"

            await msg.edit_text(response, parse_mode="Markdown")

            logger.info(
                f"OCR complete | user_id={user_id} | "
                f"manufacturer={result.manufacturer} | "
                f"model={result.model_number} | "
                f"confidence={result.confidence:.2%}"
            )

        except Exception as e:
            logger.error(f"Error in photo handler: {e}", exc_info=True)
            await msg.edit_text(
                "❌ Failed to analyze photo. Please try again with a clearer image."
            )

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle text messages with SME routing.
        """
        from rivet_pro.core.services import route_to_sme

        user_id = str(update.effective_user.id)
        user_message = update.message.text

        # Send initial message
        msg = await update.message.reply_text("🤔 Analyzing your question...")

        try:
            # Route to appropriate SME
            await msg.edit_text("🤔 Analyzing your question...\n⏳ Consulting expert...")

            response = await route_to_sme(
                user_message=user_message,
                user_id=user_id
            )

            # Format response
            await msg.edit_text(response)

            logger.info(
                f"SME routing complete | user_id={user_id} | "
                f"question_length={len(user_message)}"
            )

        except Exception as e:
            logger.error(f"Error in text handler: {e}", exc_info=True)
            await msg.edit_text(
                "❌ I had trouble understanding your question. "
                "Try asking about a specific equipment model or issue."
            )

    async def equip_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /equip command.

        Usage:
          /equip list - List your equipment
          /equip search <query> - Search equipment
          /equip view <equipment_number> - View equipment details
        """
        user_id = f"telegram_{update.effective_user.id}"
        args = context.args or []

        try:
            if not args or args[0] == "list":
                # List equipment
                equipment_list = await self.db.execute_query_async(
                    """
                    SELECT
                        equipment_number,
                        manufacturer,
                        model_number,
                        work_order_count
                    FROM cmms_equipment
                    WHERE owned_by_user_id = $1
                    ORDER BY created_at DESC
                    LIMIT 10
                    """,
                    (user_id,)
                )

                if not equipment_list:
                    await update.message.reply_text(
                        "📦 *Your Equipment*\n\n"
                        "No equipment found. Send me a photo of a nameplate to get started!",
                        parse_mode="Markdown"
                    )
                    return

                response = "📦 *Your Equipment* (most recent 10)\n\n"
                for eq in equipment_list:
                    wo_count = eq['work_order_count']
                    response += f"• `{eq['equipment_number']}` - {eq['manufacturer']} {eq['model_number'] or ''}\n"
                    response += f"  └─ {wo_count} work order{'s' if wo_count != 1 else ''}\n"

                response += "\n💡 Use `/equip view <number>` to see details"
                await update.message.reply_text(response, parse_mode="Markdown")

            elif args[0] == "search":
                if len(args) < 2:
                    await update.message.reply_text(
                        "Usage: `/equip search <query>`\nExample: `/equip search siemens`",
                        parse_mode="Markdown"
                    )
                    return

                query = " ".join(args[1:])
                results = await self.db.execute_query_async(
                    """
                    SELECT
                        equipment_number,
                        manufacturer,
                        model_number,
                        serial_number
                    FROM cmms_equipment
                    WHERE owned_by_user_id = $1
                      AND (
                          manufacturer ILIKE $2
                          OR model_number ILIKE $2
                          OR serial_number ILIKE $2
                      )
                    LIMIT 10
                    """,
                    (user_id, f"%{query}%")
                )

                if not results:
                    await update.message.reply_text(f"🔍 No equipment found matching: *{query}*", parse_mode="Markdown")
                    return

                response = f"🔍 *Search Results for: {query}*\n\n"
                for eq in results:
                    response += f"• `{eq['equipment_number']}` - {eq['manufacturer']} {eq['model_number'] or ''}\n"

                await update.message.reply_text(response, parse_mode="Markdown")

            elif args[0] == "view":
                if len(args) < 2:
                    await update.message.reply_text(
                        "Usage: `/equip view <equipment_number>`\nExample: `/equip view EQ-2026-000001`",
                        parse_mode="Markdown"
                    )
                    return

                equipment_number = args[1]
                equipment = await self.db.execute_query_async(
                    """
                    SELECT *
                    FROM cmms_equipment
                    WHERE owned_by_user_id = $1 AND equipment_number = $2
                    """,
                    (user_id, equipment_number),
                    fetch_mode="one"
                )

                if not equipment:
                    await update.message.reply_text(f"❌ Equipment `{equipment_number}` not found", parse_mode="Markdown")
                    return

                eq = equipment[0]
                response = f"📦 *Equipment Details*\n\n"
                response += f"*Number:* `{eq['equipment_number']}`\n"
                response += f"*Manufacturer:* {eq['manufacturer']}\n"
                response += f"*Model:* {eq['model_number'] or 'N/A'}\n"
                response += f"*Serial:* {eq['serial_number'] or 'N/A'}\n"
                response += f"*Type:* {eq['equipment_type'] or 'N/A'}\n"
                response += f"*Location:* {eq['location'] or 'Not specified'}\n"
                response += f"*Work Orders:* {eq['work_order_count']}\n"
                response += f"*Last Fault:* {eq['last_reported_fault'] or 'None'}\n"

                await update.message.reply_text(response, parse_mode="Markdown")

            else:
                await update.message.reply_text(
                    "📦 *Equipment Commands*\n\n"
                    "`/equip list` - List your equipment\n"
                    "`/equip search <query>` - Search equipment\n"
                    "`/equip view <number>` - View details",
                    parse_mode="Markdown"
                )

        except Exception as e:
            logger.error(f"Error in /equip command: {e}", exc_info=True)
            await update.message.reply_text("❌ An error occurred. Please try again.")

    async def wo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /wo command.

        Usage:
          /wo list - List your work orders
          /wo view <work_order_number> - View work order details
        """
        user_id = f"telegram_{update.effective_user.id}"
        args = context.args or []

        try:
            if not args or args[0] == "list":
                # List work orders
                work_orders = await self.work_order_service.list_work_orders_by_user(
                    user_id=user_id,
                    limit=10
                )

                if not work_orders:
                    await update.message.reply_text(
                        "🔧 *Your Work Orders*\n\n"
                        "No work orders found.",
                        parse_mode="Markdown"
                    )
                    return

                response = "🔧 *Your Work Orders* (most recent 10)\n\n"
                for wo in work_orders:
                    status_emoji = {
                        "open": "🟢",
                        "in_progress": "🟡",
                        "completed": "✅",
                        "cancelled": "🔴"
                    }.get(wo['status'], "⚪")

                    priority_emoji = {
                        "low": "🔵",
                        "medium": "🟡",
                        "high": "🟠",
                        "critical": "🔴"
                    }.get(wo['priority'], "⚪")

                    response += f"{status_emoji} `{wo['work_order_number']}` {priority_emoji}\n"
                    response += f"  {wo['title']}\n"
                    response += f"  └─ Equipment: `{wo['equipment_number']}`\n"

                response += "\n💡 Use `/wo view <number>` to see details"
                await update.message.reply_text(response, parse_mode="Markdown")

            elif args[0] == "view":
                if len(args) < 2:
                    await update.message.reply_text(
                        "Usage: `/wo view <work_order_number>`\nExample: `/wo view WO-2026-000001`",
                        parse_mode="Markdown"
                    )
                    return

                work_order_number = args[1]
                work_order = await self.db.execute_query_async(
                    """
                    SELECT *
                    FROM work_orders
                    WHERE user_id = $1 AND work_order_number = $2
                    """,
                    (user_id, work_order_number),
                    fetch_mode="one"
                )

                if not work_order:
                    await update.message.reply_text(f"❌ Work order `{work_order_number}` not found", parse_mode="Markdown")
                    return

                wo = work_order[0]
                status_emoji = {
                    "open": "🟢",
                    "in_progress": "🟡",
                    "completed": "✅",
                    "cancelled": "🔴"
                }.get(wo['status'], "⚪")

                response = f"🔧 *Work Order Details*\n\n"
                response += f"*Number:* `{wo['work_order_number']}`\n"
                response += f"*Status:* {status_emoji} {wo['status'].title()}\n"
                response += f"*Priority:* {wo['priority'].title()}\n"
                response += f"*Equipment:* `{wo['equipment_number']}`\n"
                response += f"*Title:* {wo['title']}\n"
                response += f"*Description:*\n{wo['description']}\n"

                if wo.get('fault_codes'):
                    response += f"*Fault Codes:* {', '.join(wo['fault_codes'])}\n"

                response += f"*Created:* {wo['created_at'].strftime('%Y-%m-%d %H:%M')}\n"

                await update.message.reply_text(response, parse_mode="Markdown")

            else:
                await update.message.reply_text(
                    "🔧 *Work Order Commands*\n\n"
                    "`/wo list` - List your work orders\n"
                    "`/wo view <number>` - View details",
                    parse_mode="Markdown"
                )

        except Exception as e:
            logger.error(f"Error in /wo command: {e}", exc_info=True)
            await update.message.reply_text("❌ An error occurred. Please try again.")

    async def manual_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /manual command - Instant equipment manual retrieval (MANUAL-003).

        Usage:
          /manual <equipment_number> - Get validated manual for equipment
        Example:
          /manual EQ-2025-0142
        """
        args = context.args or []

        try:
            if not args:
                await update.message.reply_text(
                    "📘 *Manual Lookup*\n\n"
                    "Usage: `/manual <equipment_number>`\n"
                    "Example: `/manual EQ-2025-0142`\n\n"
                    "Get instant access to AI-validated equipment manuals.",
                    parse_mode="Markdown"
                )
                return

            equipment_number = args[0].upper()

            # Look up equipment
            equipment = await self.db.fetchrow("""
                SELECT id, manufacturer, model_number, equipment_type
                FROM cmms_equipment
                WHERE equipment_number = $1
            """, equipment_number)

            if not equipment:
                await update.message.reply_text(
                    f"❌ Equipment `{equipment_number}` not found.\n"
                    "Try `/equip search <query>` to find equipment.",
                    parse_mode="Markdown"
                )
                return

            # Check manual_cache for validated manual
            cached_manual = await self.db.fetchrow("""
                SELECT manual_url, manual_title, llm_confidence, manual_type, llm_validated
                FROM manual_cache
                WHERE LOWER(manufacturer) = LOWER($1)
                    AND LOWER(model) = LOWER($2)
                    AND llm_validated = TRUE
            """, equipment['manufacturer'], equipment['model_number'])

            if cached_manual:
                confidence = cached_manual['llm_confidence']
                confidence_icon = "✅" if confidence >= 0.90 else "⚠️"

                response = f"""📘 *Manual: {equipment['manufacturer']} {equipment['model_number']}*

*Title:* {cached_manual['manual_title']}
*Type:* {cached_manual['manual_type'].replace('_', ' ').title()}
*URL:* {cached_manual['manual_url']}

*Confidence:* {confidence_icon} {confidence:.0%} (AI-validated)"""

                await update.message.reply_text(response, parse_mode="Markdown")

                # Track access
                await self.db.execute("""
                    UPDATE manual_cache
                    SET access_count = access_count + 1, last_accessed = NOW()
                    WHERE LOWER(manufacturer) = LOWER($1)
                        AND LOWER(model) = LOWER($2)
                """, equipment['manufacturer'], equipment['model_number'])

            else:
                # Check if search is in progress
                search = await self.db.fetchrow("""
                    SELECT search_status FROM equipment_manual_searches
                    WHERE equipment_id = $1
                    ORDER BY created_at DESC
                    LIMIT 1
                """, equipment['id'])

                if search and search['search_status'] == 'searching':
                    await update.message.reply_text(
                        f"🔍 Manual search in progress for `{equipment_number}`...\n"
                        "You'll receive a notification when found (usually <60s).",
                        parse_mode="Markdown"
                    )
                elif search and search['search_status'] == 'no_manual_found':
                    await update.message.reply_text(
                        f"❌ Manual not found for {equipment['manufacturer']} {equipment['model_number']}.\n"
                        "We searched multiple sources but couldn't locate a validated manual.",
                        parse_mode="Markdown"
                    )
                else:
                    await update.message.reply_text(
                        f"❌ No manual available for `{equipment_number}`.\n"
                        "Try sending a photo to trigger automatic manual search.",
                        parse_mode="Markdown"
                    )

        except Exception as e:
            logger.error(f"Error in /manual command: {e}", exc_info=True)
            await update.message.reply_text("❌ An error occurred. Please try again.")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /stats command.
        Show user statistics.
        """
        user_id = f"telegram_{update.effective_user.id}"

        try:
            # Get equipment count
            equipment_count = await self.db.fetchval(
                "SELECT COUNT(*) FROM cmms_equipment WHERE owned_by_user_id = $1",
                user_id
            )

            # Get work order stats
            wo_stats = await self.db.fetchrow(
                """
                SELECT
                    COUNT(*) FILTER (WHERE status = 'open') as open,
                    COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed
                FROM work_orders
                WHERE user_id = $1
                """,
                user_id
            )

            response = f"📊 *Your CMMS Stats*\n\n"
            response += f"📦 *Equipment:* {equipment_count or 0}\n\n"
            response += f"🔧 *Work Orders:*\n"
            response += f"  └─ 🟢 Open: {wo_stats['open'] if wo_stats else 0}\n"
            response += f"  └─ 🟡 In Progress: {wo_stats['in_progress'] if wo_stats else 0}\n"
            response += f"  └─ ✅ Completed: {wo_stats['completed'] if wo_stats else 0}\n"

            await update.message.reply_text(response, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in /stats command: {e}", exc_info=True)
            await update.message.reply_text("❌ An error occurred. Please try again.")

    async def kb_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /kb_stats command - Display knowledge base statistics.
        Admin-only command for monitoring KB growth and effectiveness.
        """
        user = update.effective_user
        telegram_user_id = str(user.id)

        # Admin check - only allow authorized users
        admin_list = [settings.telegram_admin_chat_id]  # Add more admins as needed
        if telegram_user_id not in admin_list:
            await update.message.reply_text(
                "🔒 This command is admin-only.\n\n"
                "Contact the system administrator for access."
            )
            logger.warning(f"Unauthorized /kb_stats attempt | user_id={user.id}")
            return

        logger.info(f"/kb_stats command | user_id={user.id}")

        try:
            # Fetch KB statistics
            stats = await self.kb_analytics_service.get_learning_stats()
            hit_rate = await self.kb_analytics_service.get_kb_hit_rate()
            response_times = await self.kb_analytics_service.get_response_time_comparison()
            atoms_today = await self.kb_analytics_service.get_atoms_created_today()
            pending_gaps = await self.kb_analytics_service.get_pending_gaps_count()

            # Format the message
            message = "📊 *Knowledge Base Statistics*\n\n"

            # Overview
            message += f"📚 *Total Atoms:* {stats['total_atoms']}\n"
            message += f"✨ *Created Today:* {atoms_today}\n"
            message += f"✓ *Verified:* {stats['verified_atoms']}\n"
            message += f"📈 *Avg Confidence:* {stats['avg_confidence']:.1%}\n\n"

            # Performance
            message += f"🎯 *KB Hit Rate:* {hit_rate:.1f}%\n"
            message += f"⚡ *KB Response Time:* {response_times['kb_avg_ms']:.0f}ms\n"
            message += f"🔍 *External Search Time:* {response_times['external_avg_ms']:.0f}ms\n"
            message += f"🚀 *Speed Improvement:* {response_times['speedup_factor']:.1f}x faster\n\n"

            # Atoms by source
            if stats['atoms_by_source']:
                message += "📦 *Atoms by Source:*\n"
                for source, count in sorted(stats['atoms_by_source'].items(), key=lambda x: x[1], reverse=True):
                    message += f"  • {source}: {count}\n"
                message += "\n"

            # Knowledge gaps
            message += f"🔴 *Pending Gaps:* {pending_gaps}\n"
            message += f"✅ *Resolved Gaps:* {stats['gaps_resolved']}\n\n"

            # Top atoms
            if stats['most_used_atoms']:
                message += "🏆 *Top 5 Most Used Atoms:*\n"
                for i, atom in enumerate(stats['most_used_atoms'], 1):
                    message += (
                        f"{i}. {atom['manufacturer']} {atom['model']} "
                        f"({atom['usage_count']} uses, {atom['confidence']:.1%} confidence)\n"
                    )

            await update.message.reply_text(message, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in /kb_stats command: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Failed to retrieve KB statistics. Please try again later."
            )

    async def _send_daily_kb_report(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Send daily KB health report to Ralph at scheduled time (KB-009).
        This is a JobQueue callback, not a command handler.
        """
        logger.info("Sending daily KB health report to Ralph")

        try:
            # Generate the health report
            report = await self.kb_analytics_service.generate_daily_health_report()

            # Send to Ralph's chat ID
            await context.bot.send_message(
                chat_id=self.alerting_service.ralph_chat_id,
                text=report,
                parse_mode="Markdown"
            )

            logger.info("Daily KB health report sent successfully")

        except Exception as e:
            logger.error(f"Failed to send daily KB health report: {e}", exc_info=True)
            # Try to alert Ralph about the failure
            try:
                await context.bot.send_message(
                    chat_id=self.alerting_service.ralph_chat_id,
                    text=f"❌ *Daily KB Report Failed*\n\nError: {str(e)[:200]}",
                    parse_mode="Markdown"
                )
            except:
                pass  # Don't cascade errors

    async def upgrade_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /upgrade command.
        Generate Stripe checkout link for Pro subscription.
        """
        telegram_user_id = update.effective_user.id

        try:
            is_pro = await self.stripe_service.is_pro_user(telegram_user_id)
            
            if is_pro:
                await update.message.reply_text(
                    "✅ <b>You're already a RIVET Pro member!</b>\n\n"
                    "You have unlimited equipment lookups and all Pro features.",
                    parse_mode="HTML"
                )
                return

            checkout_url = await self.stripe_service.create_checkout_session(telegram_user_id)

            await update.message.reply_text(
                "🚀 <b>Upgrade to RIVET Pro</b>\n\n"
                "Get unlimited equipment lookups and more:\n"
                "• ✅ Unlimited equipment lookups\n"
                "• 📚 PDF manual chat\n"
                "• 🔧 Work order management\n"
                "• ⚡ Priority support\n\n"
                f"💰 <b>$29/month</b>\n\n"
                f"👉 <a href=\"{checkout_url}\">Click here to subscribe</a>",
                parse_mode="HTML",
                disable_web_page_preview=True
            )

            logger.info(f"Sent upgrade link | telegram_id={telegram_user_id}")

        except Exception as e:
            logger.error(f"Error in /upgrade command: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Could not generate upgrade link. Please try again later."
            )

    async def _search_knowledge_base(
        self,
        manufacturer: str,
        model: str,
        equipment_type: Optional[str] = None
    ) -> Optional[dict]:
        """
        Search knowledge base for manual before calling external search.

        KB-003: Check knowledge atoms for manufacturer/model match.
        Returns atom with highest confidence if found.

        Args:
            manufacturer: Equipment manufacturer
            model: Equipment model number
            equipment_type: Optional equipment type

        Returns:
            Dict with 'url', 'confidence', 'atom_id' if found, None otherwise
        """
        try:
            # Query knowledge_atoms for SPEC type with manufacturer/model match
            query = """
                SELECT
                    atom_id,
                    source_url,
                    confidence,
                    usage_count,
                    title,
                    content
                FROM knowledge_atoms
                WHERE type = 'spec'
                  AND LOWER(manufacturer) = LOWER($1)
                  AND LOWER(model) = LOWER($2)
                  AND source_url IS NOT NULL
                ORDER BY confidence DESC, usage_count DESC
                LIMIT 1
            """

            row = await self.db.pool.fetchrow(query, manufacturer, model)

            if not row:
                logger.info(
                    f"KB miss | manufacturer={manufacturer} | model={model} | "
                    f"Falling back to external search"
                )
                return None

            result = {
                'atom_id': row['atom_id'],
                'url': row['source_url'],
                'confidence': float(row['confidence']),
                'usage_count': row['usage_count'],
                'title': row['title'],
                'cached': True  # Mark as KB hit for logging
            }

            logger.info(
                f"KB hit | manufacturer={manufacturer} | model={model} | "
                f"confidence={result['confidence']:.2f} | "
                f"usage_count={result['usage_count']}"
            )

            return result

        except Exception as e:
            logger.error(f"KB search failed | error={e}", exc_info=True)
            return None

    async def _create_manual_atom(
        self,
        manufacturer: str,
        model: str,
        equipment_type: Optional[str],
        manual_url: str,
        confidence: float,
        source_id: str,
        interaction_id: Optional[UUID] = None
    ) -> Optional[str]:
        """
        Create knowledge atom after manual is found.

        Implements CRITICAL-KB-001 and KB-002: System should learn from
        every successful manual lookup to improve future responses.

        Args:
            manufacturer: Equipment manufacturer
            model: Equipment model
            equipment_type: Type of equipment (motor, PLC, etc.)
            manual_url: URL to equipment manual
            confidence: Confidence score (capped at 0.95)
            source_id: User ID who triggered the lookup
        """
        try:
            # Build atom content
            content = f"Equipment Manual: {manufacturer} {model}\n\n"
            content += f"Manual URL: {manual_url}\n"
            if equipment_type:
                content += f"Equipment Type: {equipment_type}\n"
            content += f"\nGenerated from user interaction - verified by successful manual retrieval."

            # Generate keywords for search
            keywords = [
                manufacturer.lower(),
                model.lower(),
                'manual',
                'spec'
            ]
            if equipment_type:
                keywords.append(equipment_type.lower())

            # Check if atom already exists
            existing = await self.db.fetchval(
                """
                SELECT id FROM knowledge_atoms
                WHERE manufacturer = $1
                  AND model = $2
                  AND atom_type = 'SPEC'
                LIMIT 1
                """,
                manufacturer,
                model
            )

            if existing:
                # Update usage count
                await self.db.execute(
                    "UPDATE knowledge_atoms SET usage_count = usage_count + 1, last_used_at = NOW() WHERE id = $1",
                    existing
                )
                logger.info(f"Atom already exists, updated usage | atom_id={existing}")

                # Link interaction to existing atom
                if interaction_id:
                    await self.db.execute(
                        """
                        UPDATE interactions
                        SET atom_id = $1, atom_created = FALSE
                        WHERE id = $2
                        """,
                        existing,
                        interaction_id
                    )
                    logger.info(f"Linked interaction {interaction_id} to existing atom {existing}")

                return existing

            # Create new knowledge atom
            atom_id = await self.db.fetchval(
                """
                INSERT INTO knowledge_atoms (
                    id,
                    atom_type,
                    manufacturer,
                    model,
                    equipment_type,
                    content,
                    keywords,
                    confidence,
                    human_verified,
                    source_type,
                    source_id,
                    created_at,
                    usage_count,
                    last_used_at
                )
                VALUES (
                    gen_random_uuid(),
                    'SPEC',
                    $1, $2, $3, $4, $5,
                    $6,  -- confidence
                    false,  -- Not human-verified yet
                    'user_interaction',
                    $7,
                    NOW(),
                    1,  -- Start at 1 since it was just used
                    NOW()  -- last_used_at
                )
                RETURNING id
                """,
                manufacturer,
                model,
                equipment_type,
                content,
                keywords,
                confidence,
                source_id
            )

            logger.info(
                f"Knowledge atom created | atom_id={atom_id} | "
                f"manufacturer={manufacturer} | model={model} | "
                f"type=SPEC | source=user_interaction"
            )

            # Link interaction to newly created atom
            if interaction_id:
                await self.db.execute(
                    """
                    UPDATE interactions
                    SET atom_id = $1, atom_created = TRUE
                    WHERE id = $2
                    """,
                    atom_id,
                    interaction_id
                )
                logger.info(f"Linked interaction {interaction_id} to new atom {atom_id}")

            return atom_id

        except Exception as e:
            logger.error(
                f"Failed to create manual atom | manufacturer={manufacturer} | "
                f"model={model} | error={e}",
                exc_info=True
            )
            # Don't raise - atom creation failure shouldn't break user experience
            return None

    async def handle_message_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Route messages - detect feedback replies vs normal messages.

        If user replies to bot's message → treat as feedback
        Otherwise → normal message handling
        """
        message = update.message

        # Check if this is a reply to the bot's own message
        if message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id:
            await self._handle_feedback_reply(update, context)
        else:
            await self.handle_message(update, context)  # Existing handler

    async def _handle_feedback_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Process user feedback on bot's previous response.
        User replied to bot message with issue description.
        """
        user = update.effective_user
        feedback_text = update.message.text
        original_message = update.message.reply_to_message.text

        logger.info(
            f"Feedback received | user_id={user.id} | "
            f"feedback='{feedback_text[:50]}...'"
        )

        try:
            # Extract context from original bot message
            context_data = self.feedback_service.extract_context(original_message)

            # Classify feedback type
            feedback_type = self.feedback_service.classify_feedback(feedback_text, context_data)

            # Get user from database
            user_record = await self.db.fetchrow(
                "SELECT id FROM users WHERE telegram_user_id = $1",
                str(user.id)
            )

            if not user_record:
                await update.message.reply_text(
                    "❌ User not found. Please use /start first."
                )
                return

            user_id = user_record['id']

            # Send acknowledgment
            await update.message.reply_text(
                "🔍 <b>Analyzing your feedback...</b>\n\n"
                "I'll generate a fix proposal and send it to you for approval shortly.",
                parse_mode="HTML"
            )

            # Create feedback interaction and trigger workflow
            interaction_id = await self.feedback_service.create_feedback(
                user_id=user_id,
                feedback_text=feedback_text,
                feedback_type=feedback_type,
                context_data=context_data,
                telegram_user_id=str(user.id)
            )

            logger.info(
                f"Feedback stored | interaction_id={interaction_id} | "
                f"type={feedback_type} | user_id={user.id}"
            )

        except ValueError as e:
            # Rate limit or validation error
            await update.message.reply_text(
                f"⚠️ {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error handling feedback: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Failed to process feedback. Please try again."
            )

    async def handle_proposal_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle user approval/rejection of fix proposals.
        Called when user clicks 👍 or 👎 button.
        """
        query = update.callback_query
        user = update.effective_user

        await query.answer()  # Acknowledge button click

        try:
            # Parse callback data: "approve_fix:FEEDBACK-001" or "reject_fix:FEEDBACK-001"
            action, story_id = query.data.split(':', 1)

            logger.info(
                f"Proposal callback | action={action} | "
                f"story_id={story_id} | user_id={user.id}"
            )

            if action == 'approve_fix':
                # Approve the fix
                success = await self.feedback_service.approve_proposal(
                    story_id=story_id,
                    telegram_user_id=str(user.id)
                )

                if success:
                    # Edit message to show approval
                    await query.edit_message_text(
                        query.message.text + "\n\n"
                        "✅ <b>APPROVED</b>\n"
                        "⚙️ Implementing fix now... "
                        "I'll send you real-time updates as I work on it.",
                        parse_mode="HTML"
                    )

                    logger.info(f"Proposal approved | story_id={story_id} | by={user.id}")
                else:
                    await query.edit_message_text(
                        query.message.text + "\n\n"
                        "❌ <b>Failed to approve proposal.</b> Please try again.",
                        parse_mode="HTML"
                    )

            elif action == 'reject_fix':
                # Reject the fix
                success = await self.feedback_service.reject_proposal(
                    story_id=story_id,
                    telegram_user_id=str(user.id),
                    rejection_reason="User rejected via Telegram"
                )

                if success:
                    # Edit message to show rejection
                    await query.edit_message_text(
                        query.message.text + "\n\n"
                        "❌ <b>REJECTED</b>\n"
                        "Thanks for the feedback! I won't implement this fix.",
                        parse_mode="HTML"
                    )

                    logger.info(f"Proposal rejected | story_id={story_id} | by={user.id}")
                else:
                    await query.edit_message_text(
                        query.message.text + "\n\n"
                        "❌ <b>Failed to reject proposal.</b> Please try again.",
                        parse_mode="HTML"
                    )

        except Exception as e:
            logger.error(f"Error handling proposal callback: {e}", exc_info=True)
            await query.edit_message_text(
                query.message.text + "\n\n"
                "❌ <b>Error processing your response.</b> Please try again.",
                parse_mode="HTML"
            )

    async def manual_verification_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle user verification of inconclusive manual matches (MANUAL-002).
        Called when user clicks ✅ or ❌ button on manual verification request.
        """
        query = update.callback_query
        await query.answer()

        try:
            # Parse callback data: "verify_yes:equipment_id" or "verify_no:equipment_id"
            action, equipment_id_str = query.data.split(':', 1)
            equipment_id = UUID(equipment_id_str)

            logger.info(
                f"Manual verification callback | action={action} | "
                f"equipment_id={equipment_id}"
            )

            if action == 'verify_yes':
                # User confirmed manual is correct
                await self.db.execute("""
                    UPDATE equipment_manual_searches
                    SET requires_human_verification = FALSE,
                        best_manual_confidence = 0.95,
                        search_status = 'completed',
                        updated_at = NOW()
                    WHERE equipment_id = $1
                """, equipment_id)

                # TODO: In MANUAL-003, trigger SPEC atom creation here

                await query.edit_message_text(
                    "✅ Thank you! Manual verified and added to knowledge base.\n"
                    "This equipment is now available for all future users."
                )

                logger.info(f"Manual verified by user | equipment_id={equipment_id}")

            elif action == 'verify_no':
                # User rejected manual - schedule retry
                from rivet_pro.core.services.manual_matcher_service import ManualMatcherService
                manual_matcher = ManualMatcherService(self.db)

                await manual_matcher._schedule_retry(
                    equipment_id=equipment_id,
                    retry_reason='human_rejected',
                    current_retry_count=0
                )

                await query.edit_message_text(
                    "❌ Got it. We'll keep searching for a better manual.\n"
                    "I'll notify you when we find a more accurate match."
                )

                logger.info(f"Manual rejected by user | equipment_id={equipment_id}")

        except Exception as e:
            logger.error(f"Error handling manual verification: {e}", exc_info=True)
            await query.edit_message_text(
                "❌ Error processing your response. Please try again or contact support."
            )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle errors in the bot.
        """
        logger.error(f"Update {update} caused error: {context.error}")

        # Try to notify the user if possible
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Something went wrong. Our team has been notified."
            )

    def build(self) -> Application:
        """
        Build and configure the Telegram application.

        Returns:
            Configured Application instance
        """
        logger.info("Building Telegram bot application")

        # Create application
        self.application = (
            Application.builder()
            .token(settings.telegram_bot_token)
            .build()
        )

        # Register command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("equip", self.equip_command))
        self.application.add_handler(CommandHandler("wo", self.wo_command))
        self.application.add_handler(CommandHandler("manual", self.manual_command))  # MANUAL-003
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("kb_stats", self.kb_stats_command))
        self.application.add_handler(CommandHandler("upgrade", self.upgrade_command))

        # Register callback handler for inline keyboard buttons (approve/reject)
        # IMPORTANT: Must be registered BEFORE message handler
        self.application.add_handler(
            CallbackQueryHandler(
                self.handle_proposal_callback,
                pattern=r'^(approve_fix|reject_fix):'
            )
        )

        # Register callback handler for manual verification (MANUAL-002)
        self.application.add_handler(
            CallbackQueryHandler(
                self.manual_verification_callback,
                pattern=r'^verify_(yes|no):'
            )
        )

        # Register message handler (for non-command messages)
        # Now routes through handle_message_reply to detect feedback
        self.application.add_handler(
            MessageHandler(
                filters.ALL & ~filters.COMMAND,
                self.handle_message_reply  # Changed from handle_message
            )
        )

        # Register error handler
        self.application.add_error_handler(self.error_handler)

        logger.info("Telegram bot application built successfully")

        return self.application

    async def start(self) -> None:
        """
        Start the bot using either polling (development) or webhook (production).
        Mode is controlled by settings.telegram_bot_mode.
        """
        if self.application is None:
            self.build()

        # Connect to database
        await self.db.connect()
        self.equipment_service = EquipmentService(self.db)
        self.work_order_service = WorkOrderService(self.db)
        self.usage_service = UsageService(self.db)
        self.stripe_service = StripeService(self.db)
        self.manual_service = ManualService(self.db)
        self.feedback_service = FeedbackService(self.db.pool)
        self.kb_analytics_service = KnowledgeBaseAnalytics(self.db.pool)
        logger.info("Database and services initialized")

        # Initialize the application
        await self.application.initialize()
        await self.application.start()

        # Schedule daily KB health report at 9 AM EST (KB-009)
        est = pytz.timezone('America/New_York')
        report_time = datetime_time(hour=9, minute=0, tzinfo=est)

        self.application.job_queue.run_daily(
            callback=self._send_daily_kb_report,
            time=report_time,
            name='kb_daily_health_report'
        )
        logger.info("Scheduled daily KB health report at 9:00 AM EST")

        # Start bot based on configured mode
        if settings.telegram_bot_mode == "webhook":
            # Webhook mode (production with HTTPS)
            if not settings.telegram_webhook_url:
                logger.error("Webhook mode requires TELEGRAM_WEBHOOK_URL to be set")
                raise ValueError("TELEGRAM_WEBHOOK_URL must be set when using webhook mode")

            logger.info(f"Starting Telegram bot in webhook mode | url={settings.telegram_webhook_url}")

            # Start webhook
            await self.application.updater.start_webhook(
                listen="0.0.0.0",  # Listen on all interfaces
                port=settings.telegram_webhook_port,
                url_path="telegram-webhook",  # Path component of webhook URL
                webhook_url=settings.telegram_webhook_url,
                secret_token=settings.telegram_webhook_secret,  # Optional security token
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )

            logger.info(
                f"✅ Telegram bot is running in webhook mode | "
                f"port={settings.telegram_webhook_port} | "
                f"url={settings.telegram_webhook_url}"
            )

        else:
            # Polling mode (development/default)
            logger.info("Starting Telegram bot in polling mode...")

            # Start polling
            await self.application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )

            logger.info("✅ Telegram bot is running and polling for updates")

    async def stop(self) -> None:
        """
        Stop the bot gracefully.
        """
        if self.application is None:
            return

        logger.info("Stopping Telegram bot...")

        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()

        # Disconnect database
        if self.db:
            await self.db.disconnect()

        logger.info("Telegram bot stopped")


# Singleton bot instance
telegram_bot = TelegramBot()
