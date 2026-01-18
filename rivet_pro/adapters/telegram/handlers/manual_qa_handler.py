"""
Manual Q&A Telegram Handler

Telegram bot commands and handlers for PDF Manual Q&A functionality.
Integrates with the existing TelegramBot class.

Commands:
- /manualqa [query] - Start Q&A session or ask a question
- /manualqa_end - End current Q&A session
- /manualqa_stats - Show session statistics

Usage:
    Import and register handlers with the bot:

    from rivet_pro.adapters.telegram.handlers.manual_qa_handler import ManualQAHandler

    # In TelegramBot.__init__():
    self.manual_qa_handler = ManualQAHandler(db_pool, self)

    # In setup_handlers():
    self.manual_qa_handler.register_handlers(self.application)
"""

import logging
from typing import Optional, Dict, Any
from uuid import UUID

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

import asyncpg

from rivet_pro.core.services.manual_qa_service import ManualQAService
from rivet_pro.core.services.manual_conversation_service import ManualConversationService

logger = logging.getLogger(__name__)


# Conversation states
AWAITING_QUESTION = 1
AWAITING_MANUAL_SELECTION = 2


class ManualQAHandler:
    """
    Telegram handler for Manual Q&A functionality.

    Manages:
    - Q&A sessions per user
    - Question routing to ManualQAService
    - Session persistence via ManualConversationService
    """

    # User data keys
    SESSION_ID_KEY = "manual_qa_session_id"
    MANUAL_ID_KEY = "manual_qa_manual_id"
    IN_QA_MODE_KEY = "in_manual_qa_mode"

    def __init__(self, db_pool: asyncpg.Pool, bot=None):
        """
        Initialize handler.

        Args:
            db_pool: Database connection pool
            bot: Optional TelegramBot instance for shared state
        """
        self.db_pool = db_pool
        self.bot = bot
        self.qa_service = ManualQAService(db_pool)
        self.conversation_service = ManualConversationService(db_pool)

        logger.info("ManualQAHandler initialized")

    def register_handlers(self, application: Application) -> None:
        """
        Register command handlers with the Telegram application.

        Args:
            application: Telegram Application instance
        """
        # Main Q&A command
        application.add_handler(
            CommandHandler("manualqa", self.manualqa_command)
        )

        # End session command
        application.add_handler(
            CommandHandler("manualqa_end", self.end_session_command)
        )

        # Stats command
        application.add_handler(
            CommandHandler("manualqa_stats", self.stats_command)
        )

        logger.info("ManualQAHandler handlers registered")

    async def manualqa_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /manualqa command.

        Usage:
            /manualqa - Show help and start session
            /manualqa <question> - Ask a question directly
            /manualqa manual:<uuid> - Start session with specific manual
        """
        user = update.effective_user
        args = context.args or []

        # Check if user has an active session
        session_id = context.user_data.get(self.SESSION_ID_KEY)
        manual_id = context.user_data.get(self.MANUAL_ID_KEY)

        if not args:
            # Show help
            help_text = (
                "📘 *PDF Manual Q&A*\n\n"
                "Ask questions about your equipment manuals!\n\n"
                "*Usage:*\n"
                "`/manualqa <your question>`\n"
                "`/manualqa manual:<id> <question>` - specific manual\n\n"
                "*Examples:*\n"
                "• `/manualqa How do I reset to factory settings?`\n"
                "• `/manualqa What are the safety warnings?`\n"
                "• `/manualqa What causes F0002 fault?`\n\n"
                "*Other Commands:*\n"
                "• `/manualqa_end` - End current session\n"
                "• `/manualqa_stats` - View session stats\n\n"
            )

            if session_id:
                help_text += f"_Active session: {str(session_id)[:8]}..._"
            else:
                help_text += "_No active session. Ask a question to start!_"

            await update.message.reply_text(help_text, parse_mode="Markdown")
            return

        # Parse arguments
        query_parts = []
        target_manual_id = manual_id  # Use existing session manual if any

        for arg in args:
            if arg.startswith("manual:"):
                try:
                    target_manual_id = UUID(arg[7:])
                except ValueError:
                    await update.message.reply_text(
                        "❌ Invalid manual ID format.\n"
                        "Use: `/manualqa manual:uuid-here question`",
                        parse_mode="Markdown"
                    )
                    return
            else:
                query_parts.append(arg)

        if not query_parts:
            await update.message.reply_text(
                "Please provide a question.\n"
                "Example: `/manualqa How do I calibrate?`",
                parse_mode="Markdown"
            )
            return

        query = " ".join(query_parts)

        # Show typing indicator
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )

        try:
            # Create or reuse session
            if not session_id:
                session_id = await self.conversation_service.create_session(
                    manual_id=target_manual_id,
                    user_id=user.id
                )
                context.user_data[self.SESSION_ID_KEY] = session_id
                context.user_data[self.MANUAL_ID_KEY] = target_manual_id

                logger.info(
                    f"Started manual QA session | user={user.id} | session={session_id}"
                )

            # Ask the question
            response = await self.qa_service.ask(
                query=query,
                manual_id=target_manual_id,
                session_id=session_id,
                user_id=user.id
            )

            # Persist messages
            await self.conversation_service.add_message(
                session_id=session_id,
                role="user",
                content=query
            )
            await self.conversation_service.add_message(
                session_id=session_id,
                role="assistant",
                content=response.answer,
                citations=[
                    {"page": c.page, "section": c.section}
                    for c in response.citations
                ],
                confidence=response.confidence,
                cost_usd=response.cost_usd,
                model_used=response.model_used,
                rag_chunks_used=response.sources_used
            )

            # Log analytics
            await self.conversation_service.log_query_analytics(
                manual_id=target_manual_id,
                query_text=query,
                response_confidence=response.confidence,
                sources_found=response.sources_used
            )

            # Format response
            confidence_emoji = self._get_confidence_emoji(response.confidence)
            answer_text = f"{response.answer}"

            # Add metadata footer
            footer = (
                f"\n\n---\n"
                f"{confidence_emoji} Confidence: {response.confidence:.0%} | "
                f"Sources: {response.sources_used}\n"
                f"_Model: {response.model_used} | Cost: ${response.cost_usd:.4f}_"
            )

            full_response = answer_text + footer

            # Telegram message limit is 4096 chars
            if len(full_response) > 4000:
                # Send in chunks
                await update.message.reply_text(
                    answer_text[:3900] + "...",
                    parse_mode="Markdown"
                )
                await update.message.reply_text(
                    f"_(continued)_\n{footer}",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    full_response,
                    parse_mode="Markdown"
                )

            logger.info(
                f"Manual QA response | user={user.id} | "
                f"confidence={response.confidence:.2f} | cost=${response.cost_usd:.4f}"
            )

        except Exception as e:
            logger.error(f"Manual QA error | user={user.id} | error={e}")
            await update.message.reply_text(
                f"❌ An error occurred: {str(e)[:200]}\n"
                "Please try again or rephrase your question.",
                parse_mode="Markdown"
            )

    async def end_session_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /manualqa_end command - end current Q&A session."""
        user = update.effective_user
        session_id = context.user_data.get(self.SESSION_ID_KEY)

        if not session_id:
            await update.message.reply_text(
                "No active Q&A session to end.\n"
                "Start one with `/manualqa <question>`",
                parse_mode="Markdown"
            )
            return

        try:
            # End session in database
            await self.conversation_service.end_session(session_id)

            # Get final stats
            session = await self.conversation_service.get_session(session_id)

            # Clear user data
            context.user_data.pop(self.SESSION_ID_KEY, None)
            context.user_data.pop(self.MANUAL_ID_KEY, None)
            context.user_data.pop(self.IN_QA_MODE_KEY, None)

            stats_text = (
                "✅ *Q&A Session Ended*\n\n"
                f"Messages: {session.message_count if session else 0}\n"
                f"Total Cost: ${session.total_cost_usd:.4f if session else 0}\n"
                f"Avg Confidence: {session.avg_confidence:.0% if session else 0}\n\n"
                "Start a new session with `/manualqa <question>`"
            )

            await update.message.reply_text(stats_text, parse_mode="Markdown")

            logger.info(
                f"Ended manual QA session | user={user.id} | session={session_id}"
            )

        except Exception as e:
            logger.error(f"End session error | user={user.id} | error={e}")
            await update.message.reply_text(
                f"❌ Error ending session: {str(e)[:100]}",
                parse_mode="Markdown"
            )

    async def stats_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /manualqa_stats command - show session statistics."""
        user = update.effective_user
        session_id = context.user_data.get(self.SESSION_ID_KEY)

        try:
            if session_id:
                # Get current session stats
                session = await self.conversation_service.get_session(session_id)

                if session:
                    stats_text = (
                        "📊 *Current Q&A Session*\n\n"
                        f"Session ID: `{str(session_id)[:8]}...`\n"
                        f"Messages: {session.message_count}\n"
                        f"Total Cost: ${session.total_cost_usd:.4f}\n"
                        f"Avg Confidence: {session.avg_confidence:.0%}\n"
                        f"Status: {session.status}\n"
                    )
                else:
                    stats_text = "Session not found in database."
            else:
                stats_text = (
                    "No active Q&A session.\n"
                    "Start one with `/manualqa <question>`"
                )

            # Get user's session history
            sessions = await self.conversation_service.get_user_sessions(
                user_id=user.id,
                limit=5
            )

            if sessions:
                stats_text += "\n\n*Recent Sessions:*\n"
                for s in sessions:
                    stats_text += (
                        f"• {str(s.session_id)[:8]}... | "
                        f"{s.message_count} msgs | "
                        f"${s.total_cost_usd:.3f} | "
                        f"{s.status}\n"
                    )

            await update.message.reply_text(stats_text, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Stats error | user={user.id} | error={e}")
            await update.message.reply_text(
                f"❌ Error fetching stats: {str(e)[:100]}",
                parse_mode="Markdown"
            )

    def _get_confidence_emoji(self, confidence: float) -> str:
        """Get emoji indicator for confidence level."""
        if confidence >= 0.8:
            return "✅"
        elif confidence >= 0.6:
            return "⚠️"
        else:
            return "❓"


# ===== Utility Functions =====

def create_manual_qa_handler(db_pool: asyncpg.Pool) -> ManualQAHandler:
    """
    Factory function to create ManualQAHandler.

    Args:
        db_pool: Database connection pool

    Returns:
        ManualQAHandler instance
    """
    return ManualQAHandler(db_pool)


__all__ = [
    "ManualQAHandler",
    "create_manual_qa_handler",
]
