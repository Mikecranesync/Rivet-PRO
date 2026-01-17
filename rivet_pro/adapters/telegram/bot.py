"""
Telegram bot adapter for Rivet Pro.
Handles all Telegram-specific interaction logic.
"""

from typing import Optional
from uuid import UUID
from datetime import time as datetime_time
import asyncio
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# SME Chat imports
from rivet.services.sme_chat_service import SMEChatService
from rivet.services.sme_rag_service import SMERagService
from rivet.prompts.sme.personalities import get_personality, SME_PERSONALITIES
from rivet.models.sme_chat import SMEVendor, ConfidenceLevel
from rivet.atlas.database import AtlasDatabase
from rivet_pro.config.settings import settings
from rivet_pro.infra.observability import get_logger
from rivet_pro.infra.database import Database, atlas_db
from rivet_pro.core.services.equipment_service import EquipmentService
from rivet_pro.core.services.work_order_service import WorkOrderService
from rivet_pro.core.services.usage_service import UsageService, FREE_TIER_LIMIT
from rivet_pro.core.services.stripe_service import StripeService
from rivet_pro.core.services.manual_service import ManualService
from rivet_pro.core.services.feedback_service import FeedbackService
from rivet_pro.core.services.alerting_service import AlertingService
from rivet_pro.core.services.kb_analytics_service import KnowledgeBaseAnalytics
from rivet_pro.core.services.enrichment_queue_service import EnrichmentQueueService
from rivet_pro.core.services.analytics_service import AnalyticsService
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
        self.enrichment_queue_service = None  # Initialized after db connects (AUTO-KB-004)
        self.analytics_service = None  # Initialized after db connects (Phase 5 Analytics)

        # SME Chat service (Phase 4)
        self.atlas_db = None  # AtlasDatabase for SME chat
        self.sme_chat_service = None  # Initialized after db connects

        # Track pending manual validations (human-in-the-loop)
        # Maps user_id -> {url, manufacturer, model, timestamp}
        self._pending_validations: dict = {}

        # Initialize alerting service for Ralph notifications (RALPH-BOT-3)
        self.alerting_service = AlertingService(
            bot_token=settings.telegram_bot_token,
            ralph_chat_id=str(settings.telegram_admin_chat_id)  # From config
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
        Includes end-to-end tracing for debugging and observability.
        Wrapped with 60-second timeout protection (PHOTO-TIMEOUT-001).
        """
        from rivet_pro.infra.tracer import get_tracer

        user_id = str(update.effective_user.id)
        telegram_user_id = update.effective_user.id
        user = update.effective_user

        # Start trace for this request
        tracer = get_tracer()
        trace = tracer.start_trace(
            telegram_id=telegram_user_id,
            username=user.username or user.first_name,
            request_type="photo",
            message_id=update.message.message_id
        )
        trace.add_step("message_received", "success", {
            "message_id": update.message.message_id,
            "chat_id": update.effective_chat.id
        })

        llm_cost = 0.0
        outcome = "unknown"

        try:
            # 60-second timeout protection (PHOTO-TIMEOUT-001)
            async with asyncio.timeout(60):
                outcome, llm_cost = await self._process_photo_internal(
                    update, context, trace, user_id, telegram_user_id, user
                )

        except asyncio.TimeoutError:
            # Log timeout in trace
            trace.add_step("timeout", "error", {
                "timeout_seconds": 60,
                "message": "Photo processing exceeded 60 second limit"
            })
            outcome = "timeout"
            logger.error(f"Photo processing timeout | user_id={user_id} | timeout=60s")

            # Send friendly message to user
            try:
                await update.message.reply_text(
                    "⏱️ Sorry, processing took too long. Please try again with a clearer photo."
                )
            except Exception as reply_error:
                logger.error(f"Failed to send timeout message: {reply_error}")

            # Alert admin via alerting_service (PHOTO-TIMEOUT-001)
            await self.alerting_service.alert_warning(
                message="Photo processing timeout (60s exceeded)",
                context={
                    "service": "TelegramBot._handle_photo",
                    "user_id": user_id,
                    "telegram_user_id": telegram_user_id,
                    "username": user.username or user.first_name,
                    "message_id": update.message.message_id,
                    "timeout_seconds": 60
                },
                user_id=user_id,
                service="TelegramBot"
            )

        except Exception as e:
            trace.add_step("error", "error", {"error": str(e), "type": type(e).__name__})
            outcome = "error"
            logger.error(f"Error in photo handler: {e}", exc_info=True)
            try:
                await update.message.reply_text(
                    "❌ Failed to analyze photo. Please try again with a clearer image."
                )
            except Exception as reply_error:
                logger.error(f"Failed to send error message: {reply_error}")

        finally:
            # Always save trace regardless of outcome
            trace.complete(outcome=outcome, llm_cost=llm_cost)
            await tracer.save_trace(trace, self.db.pool)

    async def _process_photo_internal(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        trace,
        user_id: str,
        telegram_user_id: int,
        user
    ) -> tuple[str, float]:
        """
        Internal photo processing logic extracted for timeout protection.
        Returns (outcome, llm_cost) tuple.
        """
        from rivet_pro.core.services import analyze_image

        llm_cost = 0.0
        outcome = "unknown"

        try:
            # Check usage limits before processing
            allowed, count, reason = await self.usage_service.can_use_service(telegram_user_id)
            trace.add_step("usage_check", "success", {
                "allowed": allowed,
                "used": count,
                "limit": FREE_TIER_LIMIT,
                "reason": reason
            })

            if not allowed:
                trace.add_step("rate_limited", "skipped", {"reason": "free_limit_reached"})
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
                outcome = "rate_limited"
                return outcome, llm_cost

            # Send initial message with streaming
            msg = await update.message.reply_text("🔍 Analyzing nameplate...")

            # Download photo (get highest resolution)
            photo = await update.message.photo[-1].get_file()
            photo_bytes = await photo.download_as_bytearray()

            # Extract caption for location tagging (user can tag equipment via photo caption)
            photo_caption = update.message.caption.strip() if update.message.caption else None
            if photo_caption:
                logger.info(f"Photo caption provided | user_id={user_id} | caption='{photo_caption}'")

            trace.add_step("photo_download", "success", {
                "size_bytes": len(photo_bytes),
                "size_kb": round(len(photo_bytes) / 1024, 1)
            })

            logger.info(f"Downloaded photo | user_id={user_id} | size={len(photo_bytes)} bytes")

            # Update message: OCR in progress
            await msg.edit_text("🔍 Analyzing nameplate...\n⏳ Reading text from image...")

            # Run OCR analysis
            result = await analyze_image(
                image_bytes=photo_bytes,
                user_id=user_id
            )

            # Track LLM cost from OCR
            if hasattr(result, 'cost_usd') and result.cost_usd:
                llm_cost += result.cost_usd

            trace.add_step("ocr_analysis", "success", {
                "provider": getattr(result, 'provider', 'unknown'),
                "model": getattr(result, 'model_used', 'unknown'),
                "cost_usd": getattr(result, 'cost_usd', 0),
                "confidence": getattr(result, 'confidence', 0),
                "manufacturer": result.manufacturer,
                "model_number": result.model_number,
                "serial_number": result.serial_number,
                "equipment_type": getattr(result, 'equipment_type', None)
            })

            # Handle OCR errors
            if hasattr(result, 'error') and result.error:
                trace.add_step("ocr_error", "error", {"error": result.error})
                await msg.edit_text(
                    f"❌ {result.error}\n\n"
                    "Try taking a clearer photo with good lighting and focus on the nameplate."
                )
                outcome = "ocr_error"
                trace.complete(outcome=outcome, llm_cost=llm_cost)
                await tracer.save_trace(trace, self.db.pool)
                return

            # Log interaction for EVERY equipment lookup (CRITICAL-LOGGING-001)
            interaction_id = None
            try:
                interaction_id = await self.db.fetchval(
                    """
                    INSERT INTO interactions (
                        user_id, interaction_type, ocr_confidence, outcome, created_at
                    )
                    VALUES (
                        (SELECT id FROM users WHERE telegram_id = $1),
                        'equipment_lookup',
                        $2,
                        'ocr_complete',
                        NOW()
                    )
                    RETURNING id
                    """,
                    user_id,  # Pass as integer, not string
                    result.confidence if hasattr(result, 'confidence') else None
                )
                logger.info(f"Logged interaction | interaction_id={interaction_id} | user_id={user_id}")
            except Exception as e:
                logger.warning(f"Failed to log interaction: {e}")
                # Continue anyway - don't break user experience

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
                    location=photo_caption,  # From photo caption (e.g., "Stardust Racers")
                    user_id=f"telegram_{user_id}"
                )
                trace.add_step("equipment_match", "success", {
                    "action": "created" if is_new else "matched",
                    "equipment_id": str(equipment_id) if equipment_id else None,
                    "equipment_number": equipment_number,
                    "is_new": is_new
                })
                logger.info(
                    f"Equipment {'created' if is_new else 'matched'} | "
                    f"equipment_number={equipment_number} | user_id={user_id}"
                )

                # Update interaction with equipment_id (CRITICAL-LOGGING-001)
                if interaction_id and equipment_id:
                    try:
                        await self.db.execute(
                            """
                            UPDATE interactions
                            SET equipment_model_id = $1, outcome = 'equipment_matched'
                            WHERE id = $2
                            """,
                            equipment_id,
                            interaction_id
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update interaction with equipment: {e}")

            except Exception as e:
                trace.add_step("equipment_match", "error", {"error": str(e)})
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
            search_report = None  # For search transparency
            helpful_response = None  # LLM-generated tip when not found
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
                        trace.add_step("kb_search", "success", {
                            "hit": True,
                            "confidence": confidence,
                            "atom_id": kb_result.get('atom_id'),
                            "confidence_tier": "high" if confidence >= 0.85 else ("medium" if confidence >= 0.40 else "low")
                        })

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
                                external_result, _ = await self.manual_service.search_manual(
                                    manufacturer=result.manufacturer,
                                    model=result.model_number,
                                    timeout=15,
                                    collect_report=False  # Don't need report for backup search
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
                    search_report = None
                    if not manual_result:
                        if not kb_result:
                            trace.add_step("kb_search", "miss", {"hit": False})
                        manual_result, search_report = await self.manual_service.search_manual(
                            manufacturer=result.manufacturer,
                            model=result.model_number,
                            timeout=15,
                            collect_report=True  # Collect transparency report
                        )
                        trace.add_step("external_manual_search",
                            "success" if manual_result else "miss", {
                            "found": bool(manual_result),
                            "url": manual_result.get('url') if manual_result else None,
                            "cached": manual_result.get('cached', False) if manual_result else None,
                            "search_report": search_report.to_dict() if search_report else None
                        })

                    # Generate helpful response if not found
                    helpful_response = None
                    if manual_result:
                        logger.info(
                            f"Manual found | user_id={user_id} | "
                            f"url={manual_result.get('url')} | "
                            f"cached={manual_result.get('cached', False)}"
                        )
                    else:
                        logger.info(f"Manual not found | user_id={user_id}")
                        # Generate helpful response using LLM
                        if search_report:
                            try:
                                helpful_response = await self.manual_service.generate_helpful_response(
                                    manufacturer=result.manufacturer,
                                    model=result.model_number,
                                    search_report=search_report
                                )
                                logger.info(f"Generated helpful response for {result.manufacturer} {result.model_number}")
                            except Exception as e:
                                logger.error(f"Failed to generate helpful response: {e}")

                except Exception as e:
                    trace.add_step("manual_search", "error", {"error": str(e)})
                    logger.error(f"Manual search failed: {e}", exc_info=True)
                    # Continue without manual if search fails

            # Create knowledge atom if manual was found (CRITICAL-KB-001, KB-002)
            if manual_result and result.manufacturer and result.model_number:
                try:
                    # Update existing interaction with manual_delivered outcome (CRITICAL-LOGGING-001)
                    if interaction_id:
                        try:
                            await self.db.execute(
                                """
                                UPDATE interactions
                                SET outcome = 'manual_delivered'
                                WHERE id = $1
                                """,
                                interaction_id
                            )
                            logger.info(f"Updated interaction {interaction_id} with manual_delivered")
                        except Exception as e:
                            logger.warning(f"Failed to update interaction outcome: {e}")

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
                'confidence': result.confidence,
                'image_issues': getattr(result, 'image_issues', [])
            }

            # Add error code if detected
            if hasattr(result, 'error_code') and result.error_code:
                equipment_data['error_code'] = result.error_code

            response = format_equipment_response(
                equipment_data,
                manual_result,
                search_report=search_report,
                helpful_response=helpful_response
            )

            # Store pending validation if showing human-in-the-loop prompt
            if search_report and search_report.best_candidate and search_report.best_candidate.confidence >= 0.5:
                import time
                self._pending_validations[str(user_id)] = {
                    'url': search_report.best_candidate.url,
                    'title': search_report.best_candidate.title,
                    'manufacturer': result.manufacturer,
                    'model': result.model_number,
                    'timestamp': time.time()
                }
                logger.info(
                    f"Stored pending validation | user_id={user_id} | "
                    f"mfr={result.manufacturer} | model={result.model_number}"
                )

            # Add equipment number if created/matched
            if equipment_number:
                status = "🆕 Created" if is_new else "✓ Matched"
                response += f"\n\n<b>Equipment ID:</b> {equipment_number} ({status})"

            # Add location if provided via photo caption
            if photo_caption:
                response += f"\n<b>Location:</b> {photo_caption}"

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
                    response += f"\n\n📊 <i>{remaining} free lookups remaining</i>"
                else:
                    response += f"\n\n📊 <i>This was your last free lookup!</i>"

            await msg.edit_text(response, parse_mode="HTML")
            trace.add_step("response_sent", "success", {
                "response_length": len(response),
                "manual_found": bool(manual_result),
                "equipment_created": is_new
            })

            # Determine final outcome
            if manual_result:
                outcome = "success_with_manual"
            elif equipment_number:
                outcome = "success_no_manual"
            else:
                outcome = "partial_success"

            logger.info(
                f"OCR complete | user_id={user_id} | "
                f"manufacturer={result.manufacturer} | "
                f"model={result.model_number} | "
                f"confidence={result.confidence:.2%}"
            )

            return outcome, llm_cost

        except Exception as e:
            trace.add_step("error", "error", {"error": str(e), "type": type(e).__name__})
            outcome = "error"
            logger.error(f"Error in photo handler: {e}", exc_info=True)
            try:
                await msg.edit_text(
                    "❌ Failed to analyze photo. Please try again with a clearer image."
                )
            except Exception:
                pass  # Message may not exist yet if error was early
            return outcome, llm_cost

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle text messages with Pipeline Integration.

        Uses Phase 3 pipeline components:
        - WorkflowStateMachine for state tracking
        - AgentExecutor with vendor routing
        - SME service with LLMRouter failover
        """
        from rivet_pro.core.services.pipeline_integration import get_pipeline

        user_id = str(update.effective_user.id)
        user_message = update.message.text

        # Send initial message
        msg = await update.message.reply_text("Analyzing your question...")

        try:
            # Route through pipeline (tracks state, uses AgentExecutor with failover)
            await msg.edit_text("Analyzing your question...\nConsulting expert...")

            pipeline = get_pipeline()
            result = await pipeline.process_text_message(
                user_id=user_id,
                query=user_message
            )

            # Format response with metadata
            response_text = result.answer
            if result.confidence < 0.5:
                response_text += "\n\n_Note: Low confidence response. Consider asking a more specific question._"

            await msg.edit_text(response_text, parse_mode="Markdown")

            logger.info(
                f"Pipeline complete | user_id={user_id} | "
                f"pipeline_id={result.pipeline_id} | "
                f"vendor={result.vendor} | "
                f"confidence={result.confidence:.2f} | "
                f"time={result.execution_time_ms:.0f}ms"
            )

        except Exception as e:
            logger.error(f"Error in text handler: {e}", exc_info=True)
            await msg.edit_text(
                "I had trouble understanding your question. "
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
        telegram_id = str(update.effective_user.id)
        user_id = f"telegram_{telegram_id}"
        args = context.args or []

        try:
            if not args or args[0] == "list":
                # List equipment (match both user_id formats for backward compatibility)
                equipment_list = await self.db.execute_query_async(
                    """
                    SELECT
                        equipment_number,
                        manufacturer,
                        model_number,
                        work_order_count
                    FROM cmms_equipment
                    WHERE owned_by_user_id IN ($1, $2)
                       OR first_reported_by IN ($1, $2)
                    ORDER BY created_at DESC
                    LIMIT 10
                    """,
                    (user_id, telegram_id)
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
                    WHERE (owned_by_user_id IN ($1, $2) OR first_reported_by IN ($1, $2))
                      AND (
                          manufacturer ILIKE $3
                          OR model_number ILIKE $3
                          OR serial_number ILIKE $3
                      )
                    LIMIT 10
                    """,
                    (user_id, telegram_id, f"%{query}%")
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
                    WHERE (owned_by_user_id IN ($1, $2) OR first_reported_by IN ($1, $2))
                      AND equipment_number = $3
                    """,
                    (user_id, telegram_id, equipment_number),
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
          /wo create <equipment_number> <description> - Create new work order
        """
        user_id = f"telegram_{update.effective_user.id}"
        args = context.args or []

        try:
            if args and args[0] == "create":
                await self._wo_create(update, context, user_id, args[1:])
                return
            elif not args or args[0] == "list":
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

    async def tier_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /tier command.
        Show current subscription tier and usage.
        """
        telegram_user_id = update.effective_user.id

        try:
            # Get usage info
            allowed, count, reason = await self.usage_service.can_use_service(telegram_user_id)

            # Determine tier
            if reason == "subscribed":
                tier = "Pro"
                tier_emoji = "⭐"
                limit_text = "Unlimited"
            else:
                tier = "Free"
                tier_emoji = "🆓"
                limit_text = f"{count}/{FREE_TIER_LIMIT}"

            response = f"{tier_emoji} *Your Subscription*\n\n"
            response += f"*Tier:* {tier}\n"
            response += f"*Lookups Used:* {limit_text}\n"

            if tier == "Free":
                remaining = max(0, FREE_TIER_LIMIT - count)
                response += f"*Remaining:* {remaining}\n\n"
                response += "💡 `/upgrade` to get unlimited lookups!"

            await update.message.reply_text(response, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in /tier command: {e}", exc_info=True)
            await update.message.reply_text("❌ An error occurred. Please try again.")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /status command.
        Show bot and system status.
        """
        try:
            # Check database
            db_ok = await self.db.health_check()

            # Get recent activity
            telegram_id = str(update.effective_user.id)
            user_id = f"telegram_{telegram_id}"

            equipment_count = await self.db.fetchval(
                "SELECT COUNT(*) FROM cmms_equipment WHERE owned_by_user_id IN ($1, $2)",
                user_id, telegram_id
            ) or 0

            # Check knowledge base
            kb_count = await self.db.fetchval(
                "SELECT COUNT(*) FROM knowledge_atoms WHERE is_active = true"
            ) or 0

            response = "🤖 *RIVET Status*\n\n"
            response += f"*Database:* {'✅ Connected' if db_ok else '❌ Error'}\n"
            response += f"*Your Equipment:* {equipment_count}\n"
            response += f"*Knowledge Base:* {kb_count:,} atoms\n"
            response += f"*Bot Version:* 1.0.0\n"

            await update.message.reply_text(response, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in /status command: {e}", exc_info=True)
            await update.message.reply_text("An error occurred. Please try again.")

    async def pipeline_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /pipeline command.
        Show pipeline execution statistics and active workflows.
        """
        try:
            from rivet_pro.core.services.pipeline_integration import get_pipeline
            from rivet_pro.core.services.workflow_state_machine import get_state_machine

            pipeline = get_pipeline()
            state_machine = get_state_machine()

            # Get stats
            stats = pipeline.get_stats()
            active_workflows = state_machine.get_active_workflows()

            # Get recent history
            recent_count = 0
            try:
                result = await self.db.fetchval(
                    """
                    SELECT COUNT(*) FROM pipeline_execution_history
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                    """
                )
                recent_count = result or 0
            except Exception:
                pass  # Table might not exist yet

            response = "*Pipeline Status*\n\n"
            response += f"*Active Workflows:* {stats['active_workflows']}\n"
            response += f"*Last 24h Executions:* {recent_count}\n\n"

            if active_workflows:
                response += "*Active Workflows:*\n"
                for wf in active_workflows[:5]:  # Limit to 5
                    wf_type = wf.get('workflow_type', 'unknown')
                    state = wf.get('current_state', 'unknown')
                    response += f"  - {wf_type}: {state}\n"
            else:
                response += "_No active workflows_\n"

            # Show state distribution if any
            if stats.get('states'):
                response += "\n*States:*\n"
                for state, count in stats['states'].items():
                    response += f"  - {state}: {count}\n"

            await update.message.reply_text(response, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in /pipeline command: {e}", exc_info=True)
            await update.message.reply_text("Pipeline status unavailable. Database may be initializing.")

    async def kb_worker_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /kb_worker_status command - Display enrichment worker status (AUTO-KB-005).
        Admin-only command for monitoring worker health.
        """
        user = update.effective_user
        telegram_user_id = str(user.id)

        # Admin check - only allow authorized users
        admin_list = [settings.telegram_admin_chat_id]
        if telegram_user_id not in admin_list:
            await update.message.reply_text(
                "This command is admin-only.\n\n"
                "Contact the system administrator for access."
            )
            logger.warning(f"Unauthorized /kb_worker_status attempt | user_id={user.id}")
            return

        logger.info(f"/kb_worker_status command | user_id={user.id}")

        try:
            # Fetch worker status
            status = await self.enrichment_queue_service.worker_status()

            # Format the response
            if status.get('error'):
                await update.message.reply_text(
                    f"*Worker Status Error*\n\n{status['error']}",
                    parse_mode="Markdown"
                )
                return

            is_running = status.get('is_running', False)
            status_emoji = "🟢" if is_running else "🔴"
            status_text = "Running" if is_running else "Stopped"

            message = f"*Enrichment Worker Status*\n\n"
            message += f"{status_emoji} *Status:* {status_text}\n"

            if status.get('worker_id'):
                message += f"*Worker ID:* `{status['worker_id']}`\n"

            if status.get('last_heartbeat'):
                message += f"*Last Heartbeat:* {status['last_heartbeat']}\n"

            message += f"*Jobs Today:* {status.get('jobs_processed_today', 0)}\n"
            message += f"*Queue Depth:* {status.get('queue_depth', 0)}\n"

            if status.get('current_job'):
                job = status['current_job']
                message += f"\n*Current Job:*\n"
                message += f"  `{job['manufacturer']} {job['model_pattern']}`\n"
                message += f"  Started: {job['started_at']}\n"

            # Add alert if worker is down
            if not is_running:
                message += "\n*Worker appears to be down!*\n"
                message += "Run `/restart_worker` to restart."

            await update.message.reply_text(message, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in /kb_worker_status command: {e}", exc_info=True)
            await update.message.reply_text(
                "Failed to retrieve worker status. Please try again later."
            )

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
            except Exception as alert_error:
                logger.warning(f"Failed to send KB report failure alert: {alert_error}")

    async def adminstats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /adminstats command - Display admin analytics dashboard.
        Admin-only command for monitoring system-wide usage (Phase 5 ANALYTICS-004).
        """
        user = update.effective_user
        telegram_user_id = user.id

        # Admin check - only allow authorized users
        admin_list = [settings.telegram_admin_chat_id]
        if telegram_user_id not in admin_list:
            await update.message.reply_text(
                "🔒 This command is admin-only.\n\n"
                "Contact the system administrator for access."
            )
            logger.warning(f"Unauthorized /adminstats attempt | user_id={user.id}")
            return

        logger.info(f"/adminstats command | user_id={user.id}")

        try:
            # Use AnalyticsService to get formatted stats
            message = await self.analytics_service.format_stats_message()
            await update.message.reply_text(message, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in /adminstats command: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Failed to retrieve admin stats. Please try again later."
            )

    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /report command - Generate weekly analytics report.
        Admin-only command for comprehensive usage report (Phase 5 ANALYTICS-005).
        """
        user = update.effective_user
        telegram_user_id = user.id

        # Admin check - only allow authorized users
        admin_list = [settings.telegram_admin_chat_id]
        if telegram_user_id not in admin_list:
            await update.message.reply_text(
                "🔒 This command is admin-only.\n\n"
                "Contact the system administrator for access."
            )
            logger.warning(f"Unauthorized /report attempt | user_id={user.id}")
            return

        logger.info(f"/report command | user_id={user.id}")

        await update.message.reply_text("📊 Generating weekly report...")

        try:
            # Generate the weekly report
            report = await self.analytics_service.generate_weekly_report()
            await update.message.reply_text(report, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in /report command: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Failed to generate weekly report. Please try again later."
            )

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

                # AUTO-KB-004: Trigger enrichment job on KB miss
                if self.enrichment_queue_service and manufacturer and model:
                    try:
                        await self.enrichment_queue_service.add_to_queue(
                            manufacturer=manufacturer,
                            model_pattern=model,
                            priority=5,  # Default priority
                            user_query_count=1,
                            metadata={'trigger': 'user_search', 'equipment_type': equipment_type}
                        )
                        logger.info(
                            f"Enrichment job queued | manufacturer={manufacturer} | "
                            f"model={model} | trigger=kb_miss"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to queue enrichment job: {e}")
                        # Don't fail user request if enrichment queue fails

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

        Priority:
        1. SME Chat mode - if active, route to SME handler
        2. Reply to bot message → treat as feedback
        3. Pending validation yes/no → treat as validation response
        4. Otherwise → normal message handling
        """
        import time
        start_time = time.perf_counter()

        message = update.message
        user_id = str(update.effective_user.id)

        # Check for SME Chat mode first (Phase 4)
        if context.user_data.get('sme_chat_active') and message.text:
            handled = await self.handle_sme_chat_message(update, context)
            if handled:
                await self._log_response_time(update.effective_user.id, 'sme_chat', start_time)
                return

        # Check if this is a reply to the bot's own message
        if message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id:
            await self._handle_feedback_reply(update, context)
            await self._log_response_time(update.effective_user.id, 'feedback', start_time)
            return

        # Check if user has a pending validation and this looks like yes/no
        if message.text and user_id in self._pending_validations:
            import time
            pending = self._pending_validations[user_id]
            text_lower = message.text.strip().lower()

            # Only process if within 5 minutes and looks like yes/no
            is_yes_no = text_lower in ('yes', 'y', 'yep', 'yeah', 'correct', 'right', 'si', 'oui',
                                       'no', 'n', 'nope', 'nah', 'wrong', 'incorrect')
            is_recent = (time.time() - pending.get('timestamp', 0)) < 300  # 5 minutes

            if is_yes_no and is_recent:
                await self._handle_pending_validation(update, context, text_lower, pending)
                del self._pending_validations[user_id]
                await self._log_response_time(update.effective_user.id, 'validation', start_time)
                return

        # Default: normal message handling
        await self.handle_message(update, context)
        await self._log_response_time(update.effective_user.id, 'message', start_time)

    async def _log_response_time(self, telegram_user_id: int, action_type: str, start_time: float) -> None:
        """
        Log response time to rivet_usage_log for analytics (ANALYTICS-006).

        Args:
            telegram_user_id: Telegram user ID
            action_type: Type of action (message, sme_chat, validation, etc.)
            start_time: Start time from time.perf_counter()
        """
        import time
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Flag slow queries (>5s)
        if latency_ms > 5000:
            logger.warning(f"Slow response | user={telegram_user_id} | action={action_type} | latency={latency_ms}ms")

        try:
            await self.db.execute(
                """
                INSERT INTO rivet_usage_log (telegram_id, action_type, latency_ms, success, created_at)
                VALUES ($1, $2, $3, true, NOW())
                """,
                telegram_user_id,
                action_type,
                latency_ms
            )
        except Exception as e:
            logger.debug(f"Failed to log response time: {e}")
            # Don't break user experience for logging failures

    async def _handle_feedback_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Process user feedback on bot's previous response.
        User replied to bot message with issue description.
        Also handles Yes/No replies for manual validation (human-in-the-loop).
        """
        user = update.effective_user
        feedback_text = update.message.text.strip().lower()
        original_message = update.message.reply_to_message.text or ""

        logger.info(
            f"Feedback received | user_id={user.id} | "
            f"feedback='{feedback_text[:50]}...'"
        )

        # Check if this is a manual validation response (Yes/No)
        if "Is this the correct manual?" in original_message or "Possible Manual Found" in original_message:
            await self._handle_manual_validation_reply(update, context, feedback_text, original_message)
            return

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

    async def _handle_pending_validation(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        reply_text: str,
        pending: dict
    ) -> None:
        """
        Handle Yes/No for pending manual validation (human-in-the-loop).
        Called when user types yes/no without explicit reply, but has a pending validation.
        """
        user = update.effective_user
        is_yes = reply_text in ('yes', 'y', 'yep', 'yeah', 'correct', 'right', 'si', 'oui')

        url = pending.get('url', '')
        manufacturer = pending.get('manufacturer', 'Unknown')
        model = pending.get('model', 'Unknown')

        logger.info(
            f"Pending validation response | user={user.id} | "
            f"validated={'yes' if is_yes else 'no'} | "
            f"mfr={manufacturer} | model={model} | url={url[:60]}..."
        )

        if is_yes:
            # Store validated URL in cache for future searches
            try:
                await self.db.execute(
                    """
                    INSERT INTO manual_cache (manufacturer, model, url, source, confidence, validated_by_user, created_at)
                    VALUES ($1, $2, $3, 'user_validated', 1.0, TRUE, NOW())
                    ON CONFLICT (manufacturer, model) DO UPDATE SET
                        url = EXCLUDED.url,
                        source = 'user_validated',
                        confidence = 1.0,
                        validated_by_user = TRUE,
                        updated_at = NOW()
                    """,
                    manufacturer, model, url
                )

                await update.message.reply_text(
                    "✅ <b>Thanks for confirming!</b>\n\n"
                    "I've saved this manual for future reference. "
                    "Next time someone asks about this equipment, I'll provide this link directly.",
                    parse_mode="HTML"
                )

                logger.info(f"Manual URL validated and cached | {manufacturer} {model} | url={url[:60]}")

            except Exception as e:
                logger.error(f"Failed to cache validated URL: {e}", exc_info=True)
                await update.message.reply_text(
                    "✅ Thanks for the feedback! (Note: Had trouble saving for future use)"
                )

        else:
            # User said No - log the rejection for learning
            try:
                await self.db.execute(
                    """
                    INSERT INTO manual_feedback (manufacturer, model, url, is_correct, telegram_user_id, created_at)
                    VALUES ($1, $2, $3, FALSE, $4, NOW())
                    """,
                    manufacturer, model, url, str(user.id)
                )

                await update.message.reply_text(
                    "👍 <b>Thanks for the feedback!</b>\n\n"
                    "I won't suggest this URL again for this equipment. "
                    "Your feedback helps improve future searches.",
                    parse_mode="HTML"
                )

                logger.info(f"Manual URL rejected by user | {manufacturer} {model} | url={url[:60]}")

            except Exception as e:
                logger.error(f"Failed to store feedback: {e}", exc_info=True)
                await update.message.reply_text(
                    "👍 Thanks for the feedback!"
                )

    async def _handle_manual_validation_reply(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        reply_text: str,
        original_message: str
    ) -> None:
        """
        Handle user Yes/No reply for manual URL validation (human-in-the-loop).

        If user says Yes: Store URL as validated, cache for future searches
        If user says No: Log as rejected, don't cache
        """
        import re
        user = update.effective_user

        # Parse Yes/No response
        is_yes = reply_text in ('yes', 'y', 'yep', 'yeah', 'correct', 'right', 'si', 'oui')
        is_no = reply_text in ('no', 'n', 'nope', 'nah', 'wrong', 'incorrect')

        if not is_yes and not is_no:
            await update.message.reply_text(
                "🤔 Please reply <b>Yes</b> or <b>No</b> to confirm if the manual is correct.",
                parse_mode="HTML"
            )
            return

        # Extract URL from original message (look for the code block with URL)
        url_match = re.search(r'<code>(https?://[^<]+)</code>', original_message)
        if not url_match:
            # Try plain URL pattern
            url_match = re.search(r'(https?://\S+\.pdf\S*)', original_message)

        if not url_match:
            logger.warning(f"Could not extract URL from original message for validation")
            await update.message.reply_text(
                "❌ Could not find the URL to validate. Please try searching again."
            )
            return

        url = url_match.group(1).strip()

        # Extract manufacturer/model from original message
        mfr_match = re.search(r'Manufacturer:\s*([^\n]+)', original_message)
        model_match = re.search(r'Model:\s*([^\n]+)', original_message)

        manufacturer = mfr_match.group(1).strip() if mfr_match else "Unknown"
        model = model_match.group(1).strip() if model_match else "Unknown"

        logger.info(
            f"Manual validation | user={user.id} | "
            f"validated={'yes' if is_yes else 'no'} | "
            f"mfr={manufacturer} | model={model} | url={url[:60]}..."
        )

        if is_yes:
            # Store validated URL in cache for future searches
            try:
                await self.db.execute(
                    """
                    INSERT INTO manual_cache (manufacturer, model, url, source, confidence, validated_by_user, created_at)
                    VALUES ($1, $2, $3, 'user_validated', 1.0, TRUE, NOW())
                    ON CONFLICT (manufacturer, model) DO UPDATE SET
                        url = EXCLUDED.url,
                        source = 'user_validated',
                        confidence = 1.0,
                        validated_by_user = TRUE,
                        updated_at = NOW()
                    """,
                    manufacturer, model, url
                )

                await update.message.reply_text(
                    "✅ <b>Thanks for confirming!</b>\n\n"
                    "I've saved this manual for future reference. "
                    "Next time someone asks about this equipment, I'll provide this link directly.",
                    parse_mode="HTML"
                )

                logger.info(f"Manual URL validated and cached | {manufacturer} {model} | url={url[:60]}")

            except Exception as e:
                logger.error(f"Failed to cache validated URL: {e}", exc_info=True)
                await update.message.reply_text(
                    "✅ Thanks for the feedback! (Note: Had trouble saving for future use)"
                )

        else:
            # User said No - log the rejection
            try:
                await self.db.execute(
                    """
                    INSERT INTO manual_feedback (manufacturer, model, url, is_correct, telegram_user_id, created_at)
                    VALUES ($1, $2, $3, FALSE, $4, NOW())
                    """,
                    manufacturer, model, url, str(user.id)
                )
            except Exception as e:
                # Table might not exist - that's ok
                logger.debug(f"Could not log manual rejection: {e}")

            await update.message.reply_text(
                "👍 <b>Thanks for letting me know!</b>\n\n"
                "I won't suggest this link again. "
                f"Try searching: <code>{manufacturer} {model} manual PDF</code>",
                parse_mode="HTML"
            )

            logger.info(f"Manual URL rejected by user | {manufacturer} {model} | url={url[:60]}")

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

    async def handle_pipeline_approval_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle pipeline approval/decline/request changes callbacks (PIPE-010).
        Called when user clicks Approve, Decline, or Request Changes button.
        """
        query = update.callback_query
        await query.answer()

        try:
            # Parse callback data: "pipeline_approve:123" or "pipeline_decline:123" or "pipeline_changes:123"
            action_part, pipeline_id_str = query.data.split(':', 1)
            action = action_part.replace('pipeline_', '')
            pipeline_id = int(pipeline_id_str)

            user = update.effective_user
            approver_id = str(user.id)
            approver_name = user.full_name

            logger.info(
                f"Pipeline approval callback | action={action} | "
                f"pipeline_id={pipeline_id} | approver={approver_name}"
            )

            # Get state machine
            from rivet_pro.core.services.workflow_state_machine import (
                get_state_machine, WorkflowState, InvalidTransitionError
            )
            from datetime import datetime

            machine = get_state_machine()
            current = machine.get_current_state(pipeline_id)

            if not current:
                await query.edit_message_text(
                    f"❌ Pipeline #{pipeline_id} not found."
                )
                return

            # Build metadata
            metadata = {
                "approver_telegram_id": approver_id,
                "approver_name": approver_name,
                "approved_at": datetime.utcnow().isoformat(),
                "action": action
            }

            if action == 'approve':
                # Transition to APPROVED state
                try:
                    machine.transition(pipeline_id, WorkflowState.APPROVED, metadata)
                    await query.edit_message_text(
                        f"✅ <b>Pipeline Approved</b>\n\n"
                        f"Pipeline #{pipeline_id} has been approved by {approver_name}.\n"
                        f"The pipeline will now continue execution.",
                        parse_mode="HTML"
                    )
                    logger.info(f"Pipeline {pipeline_id} approved by {approver_name}")
                except InvalidTransitionError as e:
                    await query.edit_message_text(f"❌ Cannot approve: {e}")

            elif action == 'decline':
                # Transition to REJECTED state
                try:
                    machine.transition(pipeline_id, WorkflowState.REJECTED, metadata)
                    await query.edit_message_text(
                        f"❌ <b>Pipeline Declined</b>\n\n"
                        f"Pipeline #{pipeline_id} has been declined by {approver_name}.\n"
                        f"The pipeline has been stopped.",
                        parse_mode="HTML"
                    )
                    logger.info(f"Pipeline {pipeline_id} declined by {approver_name}")
                except InvalidTransitionError as e:
                    await query.edit_message_text(f"❌ Cannot decline: {e}")

            elif action == 'changes':
                # Keep in PENDING_APPROVAL but note that changes were requested
                metadata["changes_requested"] = True
                machine.transition(pipeline_id, WorkflowState.PENDING_APPROVAL, metadata)
                await query.edit_message_text(
                    f"📝 <b>Changes Requested</b>\n\n"
                    f"Pipeline #{pipeline_id} - {approver_name} has requested changes.\n"
                    f"Please reply to this message with your requested changes.",
                    parse_mode="HTML"
                )
                logger.info(f"Pipeline {pipeline_id} - changes requested by {approver_name}")

        except ValueError as e:
            logger.error(f"Error parsing pipeline callback data: {e}")
            await query.edit_message_text(
                "❌ Error parsing request. Please try again."
            )
        except Exception as e:
            logger.error(f"Error handling pipeline approval: {e}", exc_info=True)
            await query.edit_message_text(
                "❌ Error processing your response. Please try again or contact support."
            )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /help command.
        Show all available commands and usage.
        """
        help_text = """📚 *RIVET Bot Commands*

*Equipment Management*
• `/equip list` - List your equipment
• `/equip search <query>` - Search equipment
• `/equip view <number>` - View equipment details

*Work Orders*
• `/wo list` - List your work orders
• `/wo view <number>` - View work order details
• `/wo create <equip> <desc>` - Create work order

*Manuals & Information*
• `/manual <equipment_number>` - Get equipment manual
• `/library` - Browse machine library

*Account & Stats*
• `/stats` - View your CMMS statistics
• `/upgrade` - Upgrade to Pro

*Session*
• `/menu` - Show interactive menu
• `/reset` - Clear current session
• `/done` - Exit troubleshooting mode
• `/help` - Show this help message

*Quick Start*
Send a 📷 photo of any equipment nameplate and I'll identify it and find the manual!"""

        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /menu command.
        Show interactive menu with inline buttons.
        """
        keyboard = [
            [
                InlineKeyboardButton("📦 Equipment", callback_data="menu_equip"),
                InlineKeyboardButton("🔧 Work Orders", callback_data="menu_wo"),
            ],
            [
                InlineKeyboardButton("📘 Manual Lookup", callback_data="menu_manual"),
                InlineKeyboardButton("📚 Library", callback_data="menu_library"),
            ],
            [
                InlineKeyboardButton("📊 Stats", callback_data="menu_stats"),
                InlineKeyboardButton("❓ Help", callback_data="menu_help"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🤖 *RIVET Main Menu*\n\nWhat would you like to do?",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    async def library_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /library command.
        Browse the machine library.

        Usage:
          /library - Show library categories
          /library search <query> - Search library
        """
        args = context.args or []

        try:
            if args and args[0] == "search":
                if len(args) < 2:
                    await update.message.reply_text(
                        "Usage: `/library search <query>`\nExample: `/library search siemens motor`",
                        parse_mode="Markdown"
                    )
                    return

                query = " ".join(args[1:])

                # Search machine_library table
                results = await self.db.fetch(
                    """
                    SELECT manufacturer, model, equipment_type, manual_url
                    FROM machine_library
                    WHERE manufacturer ILIKE $1
                       OR model ILIKE $1
                       OR equipment_type ILIKE $1
                    LIMIT 10
                    """,
                    f"%{query}%"
                )

                if not results:
                    await update.message.reply_text(
                        f"🔍 No results found for: *{query}*\n\n"
                        "Try a different search term or send a photo of the equipment nameplate.",
                        parse_mode="Markdown"
                    )
                    return

                response = f"📚 *Library Search: {query}*\n\n"
                for r in results:
                    has_manual = "📘" if r['manual_url'] else "❌"
                    response += f"{has_manual} {r['manufacturer']} {r['model']}\n"
                    response += f"  └─ Type: {r['equipment_type'] or 'Unknown'}\n"

                await update.message.reply_text(response, parse_mode="Markdown")

            else:
                # Show library overview
                stats = await self.db.fetchrow(
                    """
                    SELECT
                        COUNT(*) as total,
                        COUNT(DISTINCT manufacturer) as manufacturers,
                        COUNT(DISTINCT equipment_type) as types,
                        COUNT(*) FILTER (WHERE manual_url IS NOT NULL) as with_manuals
                    FROM machine_library
                    """
                )

                response = """📚 *Machine Library*

*Statistics*
• Total entries: {total}
• Manufacturers: {manufacturers}
• Equipment types: {types}
• With manuals: {with_manuals}

*Commands*
• `/library search <query>` - Search library

💡 Send a photo to auto-lookup equipment!""".format(
                    total=stats['total'] if stats else 0,
                    manufacturers=stats['manufacturers'] if stats else 0,
                    types=stats['types'] if stats else 0,
                    with_manuals=stats['with_manuals'] if stats else 0
                )

                await update.message.reply_text(response, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in /library command: {e}", exc_info=True)
            await update.message.reply_text("❌ An error occurred. Please try again.")

    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /reset command.
        Clear current session/context.
        """
        user_id = str(update.effective_user.id)

        # Clear any user data stored in context
        context.user_data.clear()

        await update.message.reply_text(
            "🔄 *Session Reset*\n\n"
            "Your session has been cleared. Ready for a fresh start!\n\n"
            "Send a photo or type a question to begin.",
            parse_mode="Markdown"
        )

        logger.info(f"Session reset | user_id={user_id}")

    async def done_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /done command.
        Exit troubleshooting mode and return to normal operation.
        """
        user_id = str(update.effective_user.id)

        # Clear troubleshooting state if any
        if 'troubleshooting' in context.user_data:
            del context.user_data['troubleshooting']

        await update.message.reply_text(
            "✅ *Troubleshooting Complete*\n\n"
            "Exited troubleshooting mode. What would you like to do next?\n\n"
            "• Send a photo for equipment lookup\n"
            "• Use `/help` for available commands",
            parse_mode="Markdown"
        )

        logger.info(f"Exited troubleshooting | user_id={user_id}")

    # ==================== SME CHAT COMMANDS (Phase 4) ====================

    async def chat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /chat command - Start SME chat session.

        Usage:
        - /chat [vendor] - Start chat with specific vendor SME
        - /chat - Show vendor picker if no vendor specified
        """
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        args = context.args

        logger.info(f"[SME Chat] /chat command | user_id={user_id} | args={args}")

        # Check if SME chat service is available
        if not self.sme_chat_service:
            await update.message.reply_text(
                "⚠️ SME Chat is currently unavailable. Please try again later.",
                parse_mode="Markdown"
            )
            return

        # Check if already in a chat session
        if context.user_data.get('sme_chat_active'):
            vendor = context.user_data.get('sme_vendor', 'unknown')
            sme_name = context.user_data.get('sme_name', 'SME')
            await update.message.reply_text(
                f"💬 You're already chatting with *{sme_name}*!\n\n"
                f"Use `/endchat` to end this session first, or just keep chatting!",
                parse_mode="Markdown"
            )
            return

        # Valid vendor choices
        VENDOR_ALIASES = {
            "siemens": "siemens",
            "rockwell": "rockwell",
            "allen-bradley": "rockwell",
            "ab": "rockwell",
            "abb": "abb",
            "schneider": "schneider",
            "mitsubishi": "mitsubishi",
            "melsec": "mitsubishi",
            "fanuc": "fanuc",
            "generic": "generic",
        }

        vendor = None

        # Check if vendor was specified
        if args:
            vendor_input = args[0].lower()
            vendor = VENDOR_ALIASES.get(vendor_input)
            if not vendor:
                await update.message.reply_text(
                    f"❓ Unknown vendor: `{args[0]}`\n\n"
                    f"Supported vendors: siemens, rockwell (or allen-bradley/ab), abb, schneider, mitsubishi, fanuc, generic\n\n"
                    f"Example: `/chat siemens`",
                    parse_mode="Markdown"
                )
                return

        # If no vendor specified, show picker
        if not vendor:
            keyboard = [
                [
                    InlineKeyboardButton("🇩🇪 Siemens", callback_data="sme_vendor_siemens"),
                    InlineKeyboardButton("🇺🇸 Rockwell", callback_data="sme_vendor_rockwell"),
                ],
                [
                    InlineKeyboardButton("🇨🇭 ABB", callback_data="sme_vendor_abb"),
                    InlineKeyboardButton("🇫🇷 Schneider", callback_data="sme_vendor_schneider"),
                ],
                [
                    InlineKeyboardButton("🇯🇵 Mitsubishi", callback_data="sme_vendor_mitsubishi"),
                    InlineKeyboardButton("🇯🇵 Fanuc", callback_data="sme_vendor_fanuc"),
                ],
                [
                    InlineKeyboardButton("🌐 Generic", callback_data="sme_vendor_generic"),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "🎯 *Choose Your SME Expert*\n\n"
                "Select a vendor-specific expert to chat with:",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            return

        # Start the session
        await self._start_sme_session(update, context, vendor, chat_id)

    async def _start_sme_session(self, update: Update, context: ContextTypes.DEFAULT_TYPE, vendor: str, chat_id: int) -> None:
        """Start an SME chat session with the specified vendor."""
        # Get the message object - works for both commands and callbacks
        message = update.effective_message

        try:
            # Get personality info
            personality = get_personality(vendor)
            sme_name = personality.name

            # Get equipment context if available (from recent photo lookup)
            equipment_context = None
            if context.user_data.get('pending_equipment'):
                eq = context.user_data['pending_equipment']
                equipment_context = {
                    "manufacturer": eq.get("manufacturer"),
                    "model": eq.get("model"),
                    "serial_number": eq.get("serial_number"),
                }

            # Start session in database
            session = await self.sme_chat_service.start_session(
                telegram_chat_id=chat_id,
                sme_vendor=vendor,
                equipment_context=equipment_context,
            )

            # Store session info in user_data
            context.user_data['sme_session_id'] = str(session.session_id)
            context.user_data['sme_chat_active'] = True
            context.user_data['sme_vendor'] = vendor
            context.user_data['sme_name'] = sme_name
            context.user_data['sme_error_count'] = 0

            # Build greeting
            greeting = f"👋 *{sme_name}* is ready to help!\n\n"
            greeting += f"_{personality.tagline}_\n\n"
            if equipment_context:
                greeting += f"📋 I see you're working with a *{equipment_context.get('manufacturer', '')} {equipment_context.get('model', '')}*.\n\n"
            greeting += "Ask me anything about troubleshooting, configuration, or technical details.\n\n"
            greeting += "_Type `/endchat` when you're done._"

            await message.reply_text(greeting, parse_mode="Markdown")
            logger.info(f"[SME Chat] Session started | user_id={update.effective_user.id} | vendor={vendor} | session_id={session.session_id}")

        except Exception as e:
            logger.error(f"[SME Chat] Failed to start session | error={e}")
            await message.reply_text(
                "❌ Failed to start chat session. Please try again.",
                parse_mode="Markdown"
            )

    async def endchat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /endchat command - Close active SME chat session.
        """
        user_id = update.effective_user.id
        logger.info(f"[SME Chat] /endchat command | user_id={user_id}")

        # Check if in a chat session
        if not context.user_data.get('sme_chat_active'):
            await update.message.reply_text(
                "ℹ️ You don't have an active chat session.\n\n"
                "Use `/chat` to start one!",
                parse_mode="Markdown"
            )
            return

        session_id = context.user_data.get('sme_session_id')
        sme_name = context.user_data.get('sme_name', 'SME')

        try:
            # Close session in database
            if session_id and self.sme_chat_service:
                await self.sme_chat_service.close_session(session_id)

            # Clear user_data
            context.user_data.pop('sme_session_id', None)
            context.user_data.pop('sme_chat_active', None)
            context.user_data.pop('sme_vendor', None)
            context.user_data.pop('sme_name', None)
            context.user_data.pop('sme_error_count', None)

            await update.message.reply_text(
                f"👋 *Chat with {sme_name} ended.*\n\n"
                f"Thanks for chatting! Use `/chat` anytime to start a new session!",
                parse_mode="Markdown"
            )
            logger.info(f"[SME Chat] Session closed | user_id={user_id} | session_id={session_id}")

        except Exception as e:
            logger.error(f"[SME Chat] Failed to close session | error={e}")
            # Clear local state anyway
            context.user_data.pop('sme_session_id', None)
            context.user_data.pop('sme_chat_active', None)
            context.user_data.pop('sme_vendor', None)
            context.user_data.pop('sme_name', None)
            await update.message.reply_text(
                "✅ Chat session ended.\n\n"
                "Use `/chat` to start a new session!",
                parse_mode="Markdown"
            )

    async def sme_vendor_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle SME vendor selection callback."""
        query = update.callback_query
        await query.answer()

        # Extract vendor from callback_data (e.g., "sme_vendor_siemens" -> "siemens")
        vendor = query.data.replace("sme_vendor_", "")
        chat_id = update.effective_chat.id

        await self._start_sme_session(update, context, vendor, chat_id)

    async def handle_sme_chat_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Handle a message in SME chat mode.

        Returns True if message was handled, False if should fall through to normal handling.
        """
        if not context.user_data.get('sme_chat_active'):
            return False

        if not self.sme_chat_service:
            await update.message.reply_text(
                "⚠️ SME Chat service is unavailable. Session ended.\n"
                "Use `/chat` to try starting a new session.",
                parse_mode="Markdown"
            )
            context.user_data.pop('sme_chat_active', None)
            return True

        session_id = context.user_data.get('sme_session_id')
        sme_name = context.user_data.get('sme_name', 'SME')
        sme_vendor = context.user_data.get('sme_vendor', 'generic')
        user_message = update.message.text

        # Show typing indicator
        await update.message.chat.send_action("typing")

        try:
            # Get response from SME chat service
            response = await self.sme_chat_service.chat(
                session_id=session_id,
                user_message=user_message,
            )

            # Format response
            formatted = self._format_sme_chat_response(response, sme_name)
            await update.message.reply_text(formatted, parse_mode="Markdown")

            # Reset error count on success
            context.user_data['sme_error_count'] = 0

            logger.info(f"[SME Chat] Response sent | session_id={session_id} | confidence={response.confidence_level}")
            return True

        except Exception as e:
            logger.error(f"[SME Chat] Error processing message | error={e}")

            # Track consecutive errors
            error_count = context.user_data.get('sme_error_count', 0) + 1
            context.user_data['sme_error_count'] = error_count

            if error_count >= 3:
                await update.message.reply_text(
                    f"⚠️ *{sme_name} is having trouble responding.*\n\n"
                    f"This might be a temporary issue. You can:\n"
                    f"1. Type `/endchat` to end this session\n"
                    f"2. Start fresh with `/chat {sme_vendor}`\n\n"
                    f"_Error: {str(e)[:100]}_",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    f"⚠️ *{sme_name}* had trouble processing that.\n\n"
                    f"_Please rephrase your question, or type `/endchat` to end the session._",
                    parse_mode="Markdown"
                )
            return True

    def _format_sme_chat_response(self, response, sme_name: str) -> str:
        """Format SME chat response for Telegram."""
        lines = []

        # SME name badge with confidence indicator
        if response.confidence_level == ConfidenceLevel.HIGH:
            conf_emoji = "🟢"
        elif response.confidence_level == ConfidenceLevel.MEDIUM:
            conf_emoji = "🟡"
        else:
            conf_emoji = "🟠"

        lines.append(f"{conf_emoji} *{sme_name}*\n")

        # Main response
        lines.append(response.response)

        # Safety warnings
        if response.safety_warnings:
            lines.append("\n\n⚠️ *SAFETY WARNINGS:*")
            for warning in response.safety_warnings:
                lines.append(f"• {warning}")

        # Sources (limit to 3)
        if response.sources:
            lines.append("\n\n📚 *Sources:*")
            for source in response.sources[:3]:
                # Truncate long source strings
                if len(source) > 60:
                    source = source[:57] + "..."
                lines.append(f"• {source}")

        # Footer
        lines.append(f"\n_💬 Chatting with {sme_name} | /endchat to end_")

        return "\n".join(lines)

    # ==================== END SME CHAT COMMANDS ====================

    async def menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle menu button callbacks.
        """
        query = update.callback_query
        await query.answer()

        action = query.data

        if action == "menu_equip":
            await query.edit_message_text(
                "📦 *Equipment Commands*\n\n"
                "`/equip list` - List your equipment\n"
                "`/equip search <query>` - Search equipment\n"
                "`/equip view <number>` - View details",
                parse_mode="Markdown"
            )
        elif action == "menu_wo":
            await query.edit_message_text(
                "🔧 *Work Order Commands*\n\n"
                "`/wo list` - List your work orders\n"
                "`/wo view <number>` - View details\n"
                "`/wo create <equip> <desc>` - Create new",
                parse_mode="Markdown"
            )
        elif action == "menu_manual":
            await query.edit_message_text(
                "📘 *Manual Lookup*\n\n"
                "Usage: `/manual <equipment_number>`\n"
                "Example: `/manual EQ-2025-0142`\n\n"
                "Or simply send a 📷 photo of the nameplate!",
                parse_mode="Markdown"
            )
        elif action == "menu_library":
            await query.edit_message_text(
                "📚 *Machine Library*\n\n"
                "`/library` - View library stats\n"
                "`/library search <query>` - Search library",
                parse_mode="Markdown"
            )
        elif action == "menu_stats":
            await query.edit_message_text(
                "📊 Use `/stats` command to see your statistics.",
                parse_mode="Markdown"
            )
        elif action == "menu_help":
            await query.edit_message_text(
                "❓ Use `/help` command to see all available commands.",
                parse_mode="Markdown"
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
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("menu", self.menu_command))
        self.application.add_handler(CommandHandler("equip", self.equip_command))
        self.application.add_handler(CommandHandler("wo", self.wo_command))
        self.application.add_handler(CommandHandler("manual", self.manual_command))
        self.application.add_handler(CommandHandler("library", self.library_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("tier", self.tier_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("pipeline", self.pipeline_command))  # Phase 3 Pipeline
        self.application.add_handler(CommandHandler("kb_stats", self.kb_stats_command))
        self.application.add_handler(CommandHandler("kb_worker_status", self.kb_worker_status_command))  # AUTO-KB-005
        self.application.add_handler(CommandHandler("adminstats", self.adminstats_command))  # Phase 5 Analytics
        self.application.add_handler(CommandHandler("report", self.report_command))  # Phase 5 Weekly Report
        self.application.add_handler(CommandHandler("upgrade", self.upgrade_command))
        self.application.add_handler(CommandHandler("reset", self.reset_command))
        self.application.add_handler(CommandHandler("done", self.done_command))

        # SME Chat commands (Phase 4)
        self.application.add_handler(CommandHandler("chat", self.chat_command))
        self.application.add_handler(CommandHandler("endchat", self.endchat_command))

        # Register callback handler for SME vendor selection
        self.application.add_handler(
            CallbackQueryHandler(
                self.sme_vendor_callback,
                pattern=r'^sme_vendor_'
            )
        )

        # Register callback handler for menu buttons
        self.application.add_handler(
            CallbackQueryHandler(
                self.menu_callback,
                pattern=r'^menu_'
            )
        )

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

        # Register callback handler for pipeline approval (PIPE-010)
        self.application.add_handler(
            CallbackQueryHandler(
                self.handle_pipeline_approval_callback,
                pattern=r'^pipeline_(approve|decline|changes):'
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

        # Connect to Atlas CMMS database for dual-write sync
        try:
            await atlas_db.connect()
            logger.info("Atlas CMMS database connected for equipment sync")
        except Exception as e:
            logger.warning(f"Atlas CMMS database connection failed (non-blocking): {e}")

        self.equipment_service = EquipmentService(self.db)
        self.work_order_service = WorkOrderService(self.db)
        self.usage_service = UsageService(self.db)
        self.stripe_service = StripeService(self.db)
        self.manual_service = ManualService(self.db)
        self.feedback_service = FeedbackService(self.db.pool)
        self.kb_analytics_service = KnowledgeBaseAnalytics(self.db.pool)
        self.enrichment_queue_service = EnrichmentQueueService(self.db.pool)  # AUTO-KB-004
        self.analytics_service = AnalyticsService(self.db)  # Phase 5 Analytics

        # Initialize SME Chat service (Phase 4)
        try:
            self.atlas_db = AtlasDatabase()
            await self.atlas_db.connect()
            self.sme_chat_service = SMEChatService(db=self.atlas_db)
            logger.info("SME Chat service initialized")
        except Exception as e:
            logger.warning(f"SME Chat service initialization failed: {e}")
            self.sme_chat_service = None

        logger.info("Database and services initialized")

        # Initialize the application
        await self.application.initialize()
        await self.application.start()

        # Set bot commands menu
        commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("help", "Show help"),
            BotCommand("menu", "Show main menu"),
            BotCommand("chat", "Start SME chat session"),
            BotCommand("endchat", "End SME chat session"),
            BotCommand("manual", "Search for equipment manual"),
            BotCommand("equip", "Equipment lookup"),
            BotCommand("wo", "Work order management"),
            BotCommand("library", "Browse your equipment library"),
            BotCommand("stats", "View your stats"),
            BotCommand("done", "Exit troubleshooting mode"),
        ]
        try:
            await self.application.bot.set_my_commands(commands)
            logger.info("Bot menu commands set successfully")
        except Exception as e:
            logger.warning(f"Failed to set bot commands: {e}")

        # Schedule daily KB health report at 9 AM EST (KB-009)
        # Only if job_queue is available (requires pip install "python-telegram-bot[job-queue]")
        if self.application.job_queue is not None:
            est = pytz.timezone('America/New_York')
            report_time = datetime_time(hour=9, minute=0, tzinfo=est)

            self.application.job_queue.run_daily(
                callback=self._send_daily_kb_report,
                time=report_time,
                name='kb_daily_health_report'
            )
            logger.info("Scheduled daily KB health report at 9:00 AM EST")
        else:
            logger.warning("JobQueue not available - daily KB health reports disabled. Install with: pip install 'python-telegram-bot[job-queue]'")

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

            logger.info("Telegram bot is running and polling for updates")

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
