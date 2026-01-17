"""
Ralph Telegram Alerting Service

Sends critical error alerts to Ralph via Telegram for immediate failure visibility.
Part of RALPH-BOT-3: Superior error handling and observability.

Features:
- Immediate Telegram notifications (<10s)
- Error deduplication (max 1 per type per 5 minutes)
- Solution hints for common errors
- Stack trace inclusion
- Impact metrics (users affected)
"""

import logging
import traceback
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict
import httpx

logger = logging.getLogger(__name__)


class AlertingService:
    """
    Service for sending critical error alerts to Ralph via Telegram.

    Prevents alert spam while ensuring Ralph knows about problems immediately.
    """

    def __init__(self, bot_token: str, ralph_chat_id: str):
        """
        Initialize alerting service.

        Args:
            bot_token: Telegram bot token
            ralph_chat_id: Admin/Ralph's Telegram chat ID (from settings.telegram_admin_chat_id)
        """
        self.bot_token = bot_token
        self.ralph_chat_id = ralph_chat_id
        self.telegram_api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        # Error deduplication: {error_type: last_sent_time}
        self._alert_history: Dict[str, datetime] = {}
        self._dedup_window_minutes = 5

        logger.info(f"AlertingService initialized for Ralph (chat {ralph_chat_id})")

    def _get_solution_hint(self, error: Exception, context: Dict[str, Any]) -> str:
        """
        Generate solution hint based on error type and context.

        Args:
            error: The exception that occurred
            context: Additional context about the error

        Returns:
            Solution hint string
        """
        error_str = str(error)
        error_type = type(error).__name__

        # Database errors
        if "database" in error_str.lower() or "connection" in error_str.lower():
            return (
                "💡 Solution: Check database connection\n"
                "- Verify Neon database is accessible\n"
                "- Check DATABASE_URL in .env\n"
                "- Verify pool connections not exhausted"
            )

        # OpenAI quota errors
        if "insufficient_quota" in error_str or "quota" in error_str.lower():
            return (
                "💡 Solution: OpenAI quota exceeded\n"
                "- Add funds at https://platform.openai.com/account/billing\n"
                "- OR disable KB features temporarily\n"
                "- OR wait for quota reset (monthly)"
            )

        # Gemini API key errors
        if "403" in error_str and "PERMISSION_DENIED" in error_str:
            return (
                "💡 Solution: Gemini API key blocked/leaked\n"
                "- Generate new API key at https://aistudio.google.com/apikey\n"
                "- Update GOOGLE_API_KEY in .env\n"
                "- Groq fallback should handle this automatically"
            )

        # OCR failures
        if "ocr" in context.get("service", "").lower() or "vision" in error_str.lower():
            return (
                "💡 Solution: OCR provider failure\n"
                "- Check if all vision providers are down\n"
                "- Verify API keys (Groq, Gemini, OpenAI, Claude)\n"
                "- Check provider status pages"
            )

        # Telegram API errors
        if "telegram" in error_str.lower():
            return (
                "💡 Solution: Telegram API issue\n"
                "- Verify bot token is valid\n"
                "- Check Telegram API status\n"
                "- Verify network connectivity"
            )

        # Generic fallback
        return (
            "💡 Solution: Manual investigation required\n"
            f"- Error type: {error_type}\n"
            "- Check logs for full context\n"
            "- Review recent code changes"
        )

    def _should_send_alert(self, error_type: str) -> bool:
        """
        Check if we should send an alert based on deduplication window.

        Args:
            error_type: Type of error (for deduplication)

        Returns:
            True if alert should be sent, False if recently sent
        """
        now = datetime.utcnow()

        if error_type in self._alert_history:
            last_sent = self._alert_history[error_type]
            time_since_last = now - last_sent

            if time_since_last < timedelta(minutes=self._dedup_window_minutes):
                # Too soon, skip
                logger.debug(
                    f"Alert deduped: {error_type} sent {time_since_last.seconds}s ago"
                )
                return False

        # Update history
        self._alert_history[error_type] = now
        return True

    async def alert_critical(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        service: Optional[str] = None
    ) -> bool:
        """
        Send critical error alert to Ralph via Telegram.

        Args:
            error: The exception that occurred
            context: Additional context about the error
            user_id: User ID if applicable
            service: Service name (e.g., "PhotoService", "EquipmentService")

        Returns:
            True if alert was sent successfully, False otherwise
        """
        error_type = type(error).__name__
        error_msg = str(error)

        # Check deduplication
        if not self._should_send_alert(error_type):
            return False

        # Build context dict
        ctx = context or {}
        ctx["service"] = service or ctx.get("service", "Unknown")
        ctx["user_id"] = user_id or ctx.get("user_id", "Unknown")

        # Get stack trace
        stack_trace = "".join(traceback.format_exception(
            type(error), error, error.__traceback__
        ))

        # Truncate stack trace if too long
        if len(stack_trace) > 1000:
            stack_trace = stack_trace[:1000] + "\n...(truncated)"

        # Get solution hint
        solution_hint = self._get_solution_hint(error, ctx)

        # Build alert message
        alert_message = (
            f"🚨 <b>CRITICAL ERROR</b>\n\n"
            f"<b>Service:</b> {ctx['service']}\n"
            f"<b>Error:</b> {error_type}\n"
            f"<b>Message:</b> {error_msg}\n"
            f"<b>User:</b> {ctx['user_id']}\n"
            f"<b>Time:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
            f"<b>Stack Trace:</b>\n"
            f"<pre>{stack_trace}</pre>\n\n"
            f"{solution_hint}"
        )

        # Send via Telegram API
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.telegram_api_url,
                    json={
                        "chat_id": self.ralph_chat_id,
                        "text": alert_message,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True
                    }
                )

                if response.status_code == 200:
                    logger.info(
                        f"Alert sent to Ralph | error_type={error_type} | "
                        f"service={ctx['service']}"
                    )
                    return True
                else:
                    logger.error(
                        f"Failed to send alert to Ralph: {response.status_code} "
                        f"{response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error sending alert to Ralph: {e}", exc_info=True)
            return False

    async def alert_warning(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        service: Optional[str] = None
    ) -> bool:
        """
        Send warning alert to Ralph via Telegram.
        Used for non-critical issues like timeouts that need attention.

        Args:
            message: Warning message
            context: Additional context about the warning
            user_id: User ID if applicable
            service: Service name

        Returns:
            True if alert was sent successfully, False otherwise
        """
        warning_key = f"warning:{service}:{message[:50]}"

        # Check deduplication
        if not self._should_send_alert(warning_key):
            return False

        # Build context dict
        ctx = context or {}
        ctx["service"] = service or ctx.get("service", "Unknown")
        ctx["user_id"] = user_id or ctx.get("user_id", "Unknown")

        # Build alert message
        alert_message = (
            f"⚠️ <b>WARNING</b>\n\n"
            f"<b>Service:</b> {ctx['service']}\n"
            f"<b>Message:</b> {message}\n"
            f"<b>User:</b> {ctx['user_id']}\n"
            f"<b>Time:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        )

        # Add context details if provided
        if context:
            context_items = [f"  • {k}: {v}" for k, v in context.items()
                          if k not in ('service', 'user_id')]
            if context_items:
                alert_message += f"\n<b>Context:</b>\n" + "\n".join(context_items)

        # Send via Telegram API
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.telegram_api_url,
                    json={
                        "chat_id": self.ralph_chat_id,
                        "text": alert_message,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True
                    }
                )

                if response.status_code == 200:
                    logger.info(
                        f"Warning alert sent to Ralph | message={message[:50]} | "
                        f"service={ctx['service']}"
                    )
                    return True
                else:
                    logger.error(
                        f"Failed to send warning to Ralph: {response.status_code} "
                        f"{response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error sending warning to Ralph: {e}", exc_info=True)
            return False

    async def alert_degraded_service(
        self,
        service: str,
        reason: str,
        impact: str
    ) -> bool:
        """
        Send degraded service alert (non-critical).

        Args:
            service: Service name
            reason: Reason for degradation
            impact: User impact description

        Returns:
            True if alert sent successfully
        """
        alert_message = (
            f"🟡 <b>SERVICE DEGRADED</b>\n\n"
            f"<b>Service:</b> {service}\n"
            f"<b>Reason:</b> {reason}\n"
            f"<b>Impact:</b> {impact}\n"
            f"<b>Time:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
            "Service still operational but with reduced functionality."
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.telegram_api_url,
                    json={
                        "chat_id": self.ralph_chat_id,
                        "text": alert_message,
                        "parse_mode": "HTML"
                    }
                )
                return response.status_code == 200

        except Exception as e:
            logger.error(f"Error sending degraded service alert: {e}")
            return False
