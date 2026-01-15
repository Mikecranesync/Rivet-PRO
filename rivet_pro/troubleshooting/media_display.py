"""
Media Display Module for Troubleshooting Trees

Handles displaying images and media at tree nodes with captions.
Supports JPEG, PNG formats with URL or file_id references.
Gracefully handles media unavailability with text-only fallback.
Respects Telegram's 1024 character caption limit.
"""

from typing import Optional, Dict, Any, Union
from telegram import Update, InputMediaPhoto
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)

# Telegram limits
TELEGRAM_CAPTION_LIMIT = 1024
CAPTION_TRUNCATE_SUFFIX = "..."


class MediaDisplayError(Exception):
    """Raised when media display operations fail."""
    pass


def truncate_caption(text: str, max_length: int = TELEGRAM_CAPTION_LIMIT) -> str:
    """
    Truncate caption text to fit within Telegram's character limit.

    Args:
        text: The caption text to truncate
        max_length: Maximum allowed length (default: 1024 chars)

    Returns:
        Truncated text with "..." suffix if needed

    Example:
        >>> truncate_caption("A" * 1100)
        "AAA...AAA..."  # (1024 chars total)
    """
    if len(text) <= max_length:
        return text

    # Reserve space for truncation suffix
    suffix_len = len(CAPTION_TRUNCATE_SUFFIX)
    truncated_len = max_length - suffix_len

    # Truncate and add suffix
    truncated = text[:truncated_len] + CAPTION_TRUNCATE_SUFFIX

    logger.debug(
        f"Caption truncated | original_length={len(text)} | "
        f"truncated_length={len(truncated)}"
    )

    return truncated


def validate_media_node(node: Dict[str, Any]) -> bool:
    """
    Validate that a node has properly formatted media configuration.

    Args:
        node: Tree node dictionary

    Returns:
        True if node has valid media, False otherwise

    Example node with media:
        {
            "id": "CheckBearing",
            "label": "Inspect the bearing for wear marks",
            "type": "action",
            "media": {
                "type": "photo",
                "url": "https://example.com/bearing-diagram.jpg"
            }
        }
    """
    if not isinstance(node, dict):
        logger.warning("Node is not a dictionary")
        return False

    media = node.get("media")
    if not media:
        return False

    if not isinstance(media, dict):
        logger.warning(f"Media is not a dictionary | node_id={node.get('id')}")
        return False

    media_type = media.get("type")
    if media_type != "photo":
        logger.warning(
            f"Unsupported media type | node_id={node.get('id')} | "
            f"type={media_type}"
        )
        return False

    # Must have either URL or file_id
    has_url = bool(media.get("url"))
    has_file_id = bool(media.get("file_id"))

    if not (has_url or has_file_id):
        logger.warning(
            f"Media missing url or file_id | node_id={node.get('id')}"
        )
        return False

    return True


def get_media_reference(media: Dict[str, Any]) -> tuple[str, Union[str, None]]:
    """
    Extract media reference (URL or file_id) from media config.

    Args:
        media: Media configuration dictionary

    Returns:
        Tuple of (reference_type, reference_value)
        reference_type is either "url" or "file_id"

    Example:
        >>> get_media_reference({"url": "https://example.com/img.jpg"})
        ("url", "https://example.com/img.jpg")

        >>> get_media_reference({"file_id": "AgACAgIAAxkBAAI..."})
        ("file_id", "AgACAgIAAxkBAAI...")
    """
    url = media.get("url")
    if url:
        return ("url", url)

    file_id = media.get("file_id")
    if file_id:
        return ("file_id", file_id)

    return (None, None)


def format_caption_with_fallback(label: str, media_available: bool = True) -> str:
    """
    Format caption text with optional unavailability notice.

    Args:
        label: The node label text to use as caption
        media_available: Whether media loaded successfully

    Returns:
        Formatted caption with [Image unavailable] prefix if needed

    Example:
        >>> format_caption_with_fallback("Check bearing", False)
        "[Image unavailable]\n\nCheck bearing"
    """
    caption = label

    if not media_available:
        unavailable_prefix = "[Image unavailable]\n\n"
        caption = unavailable_prefix + caption

    # Truncate if needed
    caption = truncate_caption(caption)

    return caption


async def send_node_with_media(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    node: Dict[str, Any],
    reply_markup: Any = None,
) -> Optional[int]:
    """
    Send a tree node with media (photo) and caption.
    Falls back to text-only if media fails to load.

    Args:
        update: Telegram update object
        context: Telegram context
        node: Tree node with optional media field
        reply_markup: Optional inline keyboard markup

    Returns:
        Message ID of sent message, or None if failed

    Raises:
        MediaDisplayError: If both media and text-only fallback fail
    """
    node_id = node.get("id", "unknown")
    label = node.get("label", "")

    # Check if node has media
    has_media = validate_media_node(node)

    if not has_media:
        # No media - send as regular text message
        try:
            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=label,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            logger.info(
                f"Sent text-only node | node_id={node_id} | "
                f"message_id={message.message_id}"
            )
            return message.message_id

        except TelegramError as e:
            logger.error(f"Failed to send text message | node_id={node_id} | error={e}")
            raise MediaDisplayError(f"Failed to send text message: {e}")

    # Has media - attempt to send with photo
    media = node["media"]
    ref_type, ref_value = get_media_reference(media)

    if not ref_value:
        logger.error(f"Invalid media reference | node_id={node_id}")
        # Fall back to text-only
        return await send_text_only_fallback(
            update, context, label, reply_markup, node_id
        )

    try:
        caption = format_caption_with_fallback(label, media_available=True)

        logger.info(
            f"Sending photo node | node_id={node_id} | ref_type={ref_type} | "
            f"caption_length={len(caption)}"
        )

        # Send photo with caption
        if ref_type == "url":
            message = await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=ref_value,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        elif ref_type == "file_id":
            message = await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=ref_value,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            raise ValueError(f"Unknown reference type: {ref_type}")

        logger.info(
            f"Sent photo node | node_id={node_id} | message_id={message.message_id}"
        )
        return message.message_id

    except TelegramError as e:
        logger.warning(
            f"Failed to send photo, falling back to text | node_id={node_id} | "
            f"error={e}"
        )
        # Graceful fallback to text-only with unavailable notice
        return await send_text_only_fallback(
            update, context, label, reply_markup, node_id
        )


async def send_text_only_fallback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    label: str,
    reply_markup: Any,
    node_id: str
) -> int:
    """
    Send text-only fallback when media fails.

    Args:
        update: Telegram update
        context: Telegram context
        label: Node label text
        reply_markup: Inline keyboard
        node_id: Node identifier for logging

    Returns:
        Message ID

    Raises:
        MediaDisplayError: If text fallback also fails
    """
    try:
        caption = format_caption_with_fallback(label, media_available=False)

        message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=caption,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        logger.info(
            f"Sent text-only fallback | node_id={node_id} | "
            f"message_id={message.message_id}"
        )
        return message.message_id

    except TelegramError as e:
        logger.error(
            f"Text-only fallback failed | node_id={node_id} | error={e}"
        )
        raise MediaDisplayError(f"Both media and text fallback failed: {e}")


async def update_node_with_media(
    query: Any,
    node: Dict[str, Any],
    reply_markup: Any = None,
) -> bool:
    """
    Update existing message with new node content.
    Handles transition between text-only and media messages.

    Args:
        query: CallbackQuery from inline button press
        node: New tree node to display
        reply_markup: Optional inline keyboard markup

    Returns:
        True if update succeeded, False otherwise

    Note:
        If transitioning from text to media (or vice versa),
        deletes old message and sends new one, as Telegram
        doesn't support edit_message_media for transitions.
    """
    node_id = node.get("id", "unknown")
    label = node.get("label", "")
    has_media = validate_media_node(node)

    try:
        # Get current message info
        current_message = query.message
        has_photo = bool(current_message.photo)

        # Case 1: Text to text (simple edit)
        if not has_media and not has_photo:
            await query.edit_message_text(
                text=label,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            logger.info(f"Updated text node | node_id={node_id}")
            return True

        # Case 2: Photo to photo with same format (edit media)
        if has_media and has_photo:
            media = node["media"]
            ref_type, ref_value = get_media_reference(media)

            if ref_value:
                caption = format_caption_with_fallback(label, media_available=True)

                try:
                    await query.edit_message_media(
                        media=InputMediaPhoto(
                            media=ref_value,
                            caption=caption,
                            parse_mode="Markdown"
                        ),
                        reply_markup=reply_markup
                    )
                    logger.info(f"Updated photo node | node_id={node_id}")
                    return True

                except TelegramError as e:
                    logger.warning(
                        f"Failed to edit media, falling back to delete+send | "
                        f"node_id={node_id} | error={e}"
                    )
                    # Fall through to delete+send approach

        # Case 3: Transition between text/media formats
        # Delete old message and send new one
        logger.info(
            f"Transitioning message format | node_id={node_id} | "
            f"old_has_photo={has_photo} | new_has_media={has_media}"
        )

        try:
            await query.delete_message()
        except TelegramError as e:
            logger.warning(f"Failed to delete old message | error={e}")

        # Send new message through Update constructed from query
        from telegram import Update as TelegramUpdate
        update = TelegramUpdate(update_id=0, message=current_message)

        await send_node_with_media(
            update,
            query.get_bot(),  # Get bot context from query
            node,
            reply_markup
        )

        logger.info(f"Transitioned message format | node_id={node_id}")
        return True

    except TelegramError as e:
        logger.error(
            f"Failed to update node | node_id={node_id} | error={e}"
        )
        return False


# Export public API
__all__ = [
    "MediaDisplayError",
    "truncate_caption",
    "validate_media_node",
    "format_caption_with_fallback",
    "send_node_with_media",
    "update_node_with_media",
]
