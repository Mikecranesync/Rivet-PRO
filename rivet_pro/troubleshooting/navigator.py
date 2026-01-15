"""
TreeNavigator - In-place message editing for troubleshooting tree navigation

Handles message editing with graceful fallback for edit failures.
Maintains clean message history during tree traversal.
"""

import logging
from typing import Dict, Optional, Any
from telegram import Update, Message, InlineKeyboardMarkup
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class TreeNavigator:
    """
    Manages in-place message editing for troubleshooting tree navigation.

    Features:
    - Tracks message IDs per chat/user session
    - Attempts edit_message_text for updates
    - Falls back to delete+send on edit failures
    - Handles both text and media messages
    - Maintains clean message history

    Usage:
        navigator = TreeNavigator()

        # First interaction - sends new message
        msg = await navigator.show_node(update, context, tree, node_id="A")

        # Navigation - edits same message
        await navigator.navigate_to(update, context, tree, node_id="B")
    """

    def __init__(self):
        """Initialize the TreeNavigator with session tracking."""
        # Track message IDs: {(chat_id, user_id): message_id}
        self._message_map: Dict[tuple, int] = {}

        # Track current node: {(chat_id, user_id): node_id}
        self._current_node: Dict[tuple, str] = {}

        logger.info("TreeNavigator initialized")

    def _get_session_key(self, update: Update) -> tuple:
        """
        Generate session key from update.

        Args:
            update: Telegram update object

        Returns:
            Tuple of (chat_id, user_id)
        """
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        return (chat_id, user_id)

    def _get_tracked_message_id(self, update: Update) -> Optional[int]:
        """
        Get the tracked message ID for this session.

        Args:
            update: Telegram update object

        Returns:
            Message ID if tracked, None otherwise
        """
        session_key = self._get_session_key(update)
        return self._message_map.get(session_key)

    def _track_message(self, update: Update, message_id: int):
        """
        Track a message ID for this session.

        Args:
            update: Telegram update object
            message_id: Message ID to track
        """
        session_key = self._get_session_key(update)
        self._message_map[session_key] = message_id
        logger.debug(f"Tracking message {message_id} for session {session_key}")

    def _set_current_node(self, update: Update, node_id: str):
        """
        Set the current node for this session.

        Args:
            update: Telegram update object
            node_id: Node ID to track
        """
        session_key = self._get_session_key(update)
        self._current_node[session_key] = node_id
        logger.debug(f"Current node for session {session_key}: {node_id}")

    def get_current_node(self, update: Update) -> Optional[str]:
        """
        Get the current node ID for this session.

        Args:
            update: Telegram update object

        Returns:
            Current node ID if tracked, None otherwise
        """
        session_key = self._get_session_key(update)
        return self._current_node.get(session_key)

    async def _try_edit_message(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        parse_mode: str = "HTML"
    ) -> bool:
        """
        Attempt to edit an existing message.

        Args:
            context: Bot context
            chat_id: Chat ID
            message_id: Message ID to edit
            text: New text content
            reply_markup: Optional keyboard markup
            parse_mode: Message parse mode (default: HTML)

        Returns:
            True if edit succeeded, False if it failed
        """
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            logger.debug(f"Successfully edited message {message_id}")
            return True

        except BadRequest as e:
            # Common reasons for edit failure:
            # - Message is too old
            # - Message content is identical
            # - Message was deleted
            # - Message is a media message
            logger.warning(f"Failed to edit message {message_id}: {e}")
            return False

        except TelegramError as e:
            logger.error(f"Telegram error editing message {message_id}: {e}")
            return False

    async def _delete_message(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: int,
        message_id: int
    ) -> bool:
        """
        Attempt to delete a message.

        Args:
            context: Bot context
            chat_id: Chat ID
            message_id: Message ID to delete

        Returns:
            True if deletion succeeded, False otherwise
        """
        try:
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=message_id
            )
            logger.debug(f"Successfully deleted message {message_id}")
            return True

        except TelegramError as e:
            logger.warning(f"Failed to delete message {message_id}: {e}")
            return False

    async def _send_new_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        parse_mode: str = "HTML"
    ) -> Message:
        """
        Send a new message.

        Args:
            update: Telegram update object
            context: Bot context
            text: Message text
            reply_markup: Optional keyboard markup
            parse_mode: Message parse mode (default: HTML)

        Returns:
            Sent message object
        """
        message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        logger.debug(f"Sent new message {message.message_id}")
        return message

    async def show_node(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        tree: Any,  # TroubleshootingTree object
        node_id: str,
        force_new: bool = False
    ) -> Message:
        """
        Show a tree node, editing existing message if possible.

        Args:
            update: Telegram update object
            context: Bot context
            tree: TroubleshootingTree instance
            node_id: Node ID to display
            force_new: Force sending new message instead of editing

        Returns:
            The message object (edited or newly sent)

        Raises:
            ValueError: If node_id doesn't exist in tree
        """
        # Get node data from tree
        node = tree.get_node(node_id)
        if not node:
            raise ValueError(f"Node '{node_id}' not found in tree")

        # Render the node content
        text = tree.render_node(node_id)
        reply_markup = tree.get_node_keyboard(node_id)

        chat_id = update.effective_chat.id
        tracked_message_id = self._get_tracked_message_id(update)

        # Try to edit existing message if we have one and not forcing new
        if tracked_message_id and not force_new:
            edit_success = await self._try_edit_message(
                context=context,
                chat_id=chat_id,
                message_id=tracked_message_id,
                text=text,
                reply_markup=reply_markup
            )

            if edit_success:
                # Edit succeeded, update current node and return
                self._set_current_node(update, node_id)
                # Return a pseudo-message object for consistency
                class EditedMessage:
                    def __init__(self, msg_id, chat_id):
                        self.message_id = msg_id
                        self.chat_id = chat_id

                return EditedMessage(tracked_message_id, chat_id)

            # Edit failed, try to delete old message before sending new
            logger.info(f"Edit failed for message {tracked_message_id}, falling back to delete+send")
            await self._delete_message(context, chat_id, tracked_message_id)

        # Send new message (either no tracked message, force_new, or edit failed)
        message = await self._send_new_message(
            update=update,
            context=context,
            text=text,
            reply_markup=reply_markup
        )

        # Track the new message
        self._track_message(update, message.message_id)
        self._set_current_node(update, node_id)

        return message

    async def navigate_to(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        tree: Any,
        node_id: str
    ) -> Message:
        """
        Navigate to a new node, editing the current message.

        This is a convenience wrapper around show_node for navigation.

        Args:
            update: Telegram update object
            context: Bot context
            tree: TroubleshootingTree instance
            node_id: Node ID to navigate to

        Returns:
            The message object (edited or newly sent)
        """
        return await self.show_node(update, context, tree, node_id, force_new=False)

    def clear_session(self, update: Update):
        """
        Clear tracking data for a session.

        Useful when ending a troubleshooting session or resetting.

        Args:
            update: Telegram update object
        """
        session_key = self._get_session_key(update)

        if session_key in self._message_map:
            del self._message_map[session_key]
            logger.debug(f"Cleared message tracking for session {session_key}")

        if session_key in self._current_node:
            del self._current_node[session_key]
            logger.debug(f"Cleared node tracking for session {session_key}")

    def get_session_info(self, update: Update) -> Dict[str, Any]:
        """
        Get current session information for debugging.

        Args:
            update: Telegram update object

        Returns:
            Dictionary with session info
        """
        session_key = self._get_session_key(update)

        return {
            "session_key": session_key,
            "tracked_message_id": self._message_map.get(session_key),
            "current_node": self._current_node.get(session_key),
            "total_sessions": len(self._message_map)
        }
