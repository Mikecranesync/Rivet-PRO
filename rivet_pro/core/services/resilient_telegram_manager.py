"""
ResilientTelegramManager - Telegram message queue with retry logic.

Features:
- Asyncio queue for messages
- Retry with exponential backoff (max 5 attempts)
- Dead letter queue for failed messages
- Rate limiting (30 msg/sec)
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class MessageStatus(Enum):
    PENDING = "PENDING"
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


@dataclass
class QueuedMessage:
    """Represents a message in the queue"""
    chat_id: int
    text: str
    message_id: str = field(default_factory=lambda: f"msg_{datetime.utcnow().timestamp()}")
    status: MessageStatus = MessageStatus.PENDING
    attempts: int = 0
    max_attempts: int = 5
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_attempt_at: Optional[datetime] = None
    error_message: Optional[str] = None
    reply_markup: Optional[Dict[str, Any]] = None
    parse_mode: Optional[str] = "HTML"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "chat_id": self.chat_id,
            "text": self.text[:100] + "..." if len(self.text) > 100 else self.text,
            "status": self.status.value,
            "attempts": self.attempts,
            "created_at": self.created_at.isoformat(),
            "last_attempt_at": self.last_attempt_at.isoformat() if self.last_attempt_at else None,
            "error_message": self.error_message
        }


class ResilientTelegramManager:
    """
    Telegram message manager with queue, retry logic, and rate limiting.

    Usage:
        manager = ResilientTelegramManager(bot_token="xxx")
        await manager.start()

        # Queue a message (non-blocking)
        await manager.send_message(chat_id=123, text="Hello!")

        # Wait for queue to drain
        await manager.wait_for_drain()

        # Stop the manager
        await manager.stop()
    """

    def __init__(
        self,
        bot_token: Optional[str] = None,
        max_retries: int = 5,
        rate_limit: float = 30.0,  # messages per second
        queue_size: int = 1000
    ):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.max_retries = max_retries
        self.rate_limit = rate_limit
        self.min_interval = 1.0 / rate_limit  # seconds between messages
        self.queue_size = queue_size

        # Queues
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self._dead_letter_queue: deque = deque(maxlen=100)

        # State
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._last_send_time = 0.0
        self._stats = {
            "sent": 0,
            "failed": 0,
            "retried": 0,
            "dead_letter": 0
        }

        # Bot instance (lazy loaded)
        self._bot = None

    @property
    def bot(self):
        """Lazy load telegram bot"""
        if self._bot is None:
            from telegram import Bot
            self._bot = Bot(token=self.bot_token)
        return self._bot

    async def start(self):
        """Start the message processing worker"""
        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._process_queue())
        logger.info("ResilientTelegramManager started")

    async def stop(self, drain: bool = True):
        """Stop the message processing worker"""
        if not self._running:
            return

        if drain:
            await self.wait_for_drain()

        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        logger.info("ResilientTelegramManager stopped")

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None,
        parse_mode: str = "HTML",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Queue a message for sending.

        Args:
            chat_id: Telegram chat ID
            text: Message text
            reply_markup: Optional inline keyboard markup
            parse_mode: Message parse mode (HTML, Markdown, MarkdownV2)
            metadata: Optional metadata for tracking

        Returns:
            Message ID for tracking
        """
        message = QueuedMessage(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            metadata=metadata or {}
        )

        try:
            self._message_queue.put_nowait(message)
            logger.debug(f"Message queued: {message.message_id}")
            return message.message_id
        except asyncio.QueueFull:
            logger.error("Message queue full, dropping message")
            raise RuntimeError("Message queue is full")

    async def send_to_admin(self, text: str, **kwargs) -> str:
        """Send message to admin chat"""
        try:
            from rivet_pro.config.settings import settings
            admin_chat_id = settings.telegram_admin_chat_id
        except ImportError:
            admin_chat_id = int(os.getenv("TELEGRAM_ADMIN_CHAT_ID", "8445149012"))
        return await self.send_message(chat_id=admin_chat_id, text=text, **kwargs)

    async def _process_queue(self):
        """Worker that processes the message queue"""
        while self._running:
            try:
                # Wait for a message
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0
                )

                # Rate limiting
                await self._apply_rate_limit()

                # Send the message
                await self._send_with_retry(message)

                self._message_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue processing error: {e}")

    async def _apply_rate_limit(self):
        """Apply rate limiting between messages"""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_send_time
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self._last_send_time = asyncio.get_event_loop().time()

    async def _send_with_retry(self, message: QueuedMessage):
        """Send message with exponential backoff retry"""
        while message.attempts < message.max_attempts:
            message.attempts += 1
            message.last_attempt_at = datetime.utcnow()
            message.status = MessageStatus.SENDING

            try:
                # Build kwargs for send_message
                kwargs = {
                    "chat_id": message.chat_id,
                    "text": message.text,
                    "parse_mode": message.parse_mode
                }
                if message.reply_markup:
                    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
                    # Convert dict to InlineKeyboardMarkup if needed
                    if isinstance(message.reply_markup, dict):
                        keyboard = []
                        for row in message.reply_markup.get("inline_keyboard", []):
                            keyboard.append([
                                InlineKeyboardButton(
                                    text=btn.get("text", ""),
                                    callback_data=btn.get("callback_data")
                                )
                                for btn in row
                            ])
                        kwargs["reply_markup"] = InlineKeyboardMarkup(keyboard)
                    else:
                        kwargs["reply_markup"] = message.reply_markup

                # Send via bot
                await self.bot.send_message(**kwargs)

                message.status = MessageStatus.SENT
                self._stats["sent"] += 1
                logger.info(f"Message sent: {message.message_id} to {message.chat_id}")
                return

            except Exception as e:
                message.error_message = str(e)
                logger.warning(
                    f"Send failed (attempt {message.attempts}/{message.max_attempts}): {e}"
                )

                if message.attempts < message.max_attempts:
                    # Exponential backoff: 1s, 2s, 4s, 8s, 16s
                    delay = 2 ** (message.attempts - 1)
                    self._stats["retried"] += 1
                    await asyncio.sleep(delay)

        # Max retries exceeded - move to dead letter queue
        message.status = MessageStatus.DEAD_LETTER
        self._dead_letter_queue.append(message)
        self._stats["failed"] += 1
        self._stats["dead_letter"] += 1
        logger.error(f"Message moved to dead letter queue: {message.message_id}")

    async def wait_for_drain(self, timeout: float = 30.0):
        """Wait for all queued messages to be processed"""
        try:
            await asyncio.wait_for(
                self._message_queue.join(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Queue drain timed out after {timeout}s")

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            **self._stats,
            "queue_size": self._message_queue.qsize(),
            "dead_letter_count": len(self._dead_letter_queue),
            "running": self._running
        }

    def get_dead_letter_queue(self) -> List[Dict[str, Any]]:
        """Get messages from dead letter queue"""
        return [msg.to_dict() for msg in self._dead_letter_queue]

    def clear_dead_letter_queue(self):
        """Clear the dead letter queue"""
        self._dead_letter_queue.clear()


# Global instance for convenience
_manager_instance: Optional[ResilientTelegramManager] = None


def get_telegram_manager() -> ResilientTelegramManager:
    """Get or create the global ResilientTelegramManager instance"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ResilientTelegramManager()
    return _manager_instance


async def send_admin_notification(text: str, **kwargs) -> str:
    """Convenience function to send notification to admin"""
    manager = get_telegram_manager()
    if not manager._running:
        await manager.start()
    return await manager.send_to_admin(text, **kwargs)
