"""
Unit tests for media display module.

Tests caption truncation, media validation, fallback handling,
and graceful degradation when media is unavailable.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram.error import TelegramError

from rivet_pro.troubleshooting.media_display import (
    truncate_caption,
    validate_media_node,
    get_media_reference,
    format_caption_with_fallback,
    send_node_with_media,
    update_node_with_media,
    MediaDisplayError,
    TELEGRAM_CAPTION_LIMIT,
)


class TestCaptionTruncation:
    """Test caption text truncation to fit Telegram limits."""

    def test_short_caption_unchanged(self):
        """Short captions should pass through unchanged."""
        text = "Check the bearing for wear"
        result = truncate_caption(text)
        assert result == text

    def test_exact_limit_unchanged(self):
        """Caption exactly at limit should be unchanged."""
        text = "A" * TELEGRAM_CAPTION_LIMIT
        result = truncate_caption(text)
        assert result == text
        assert len(result) == TELEGRAM_CAPTION_LIMIT

    def test_over_limit_truncated(self):
        """Long captions should be truncated with suffix."""
        text = "A" * (TELEGRAM_CAPTION_LIMIT + 100)
        result = truncate_caption(text)

        assert len(result) == TELEGRAM_CAPTION_LIMIT
        assert result.endswith("...")

    def test_truncation_respects_suffix(self):
        """Truncation should account for suffix length."""
        text = "B" * 1100
        result = truncate_caption(text, max_length=100)

        assert len(result) == 100
        assert result.endswith("...")
        # Content + suffix = max_length
        assert result == ("B" * 97) + "..."

    def test_empty_caption(self):
        """Empty caption should remain empty."""
        result = truncate_caption("")
        assert result == ""


class TestMediaNodeValidation:
    """Test validation of tree nodes with media configuration."""

    def test_valid_node_with_url(self):
        """Node with valid photo URL should validate."""
        node = {
            "id": "CheckBearing",
            "label": "Inspect bearing",
            "type": "action",
            "media": {
                "type": "photo",
                "url": "https://example.com/bearing.jpg"
            }
        }
        assert validate_media_node(node) is True

    def test_valid_node_with_file_id(self):
        """Node with valid file_id should validate."""
        node = {
            "id": "CheckBearing",
            "label": "Inspect bearing",
            "media": {
                "type": "photo",
                "file_id": "AgACAgIAAxkBAAIBCD..."
            }
        }
        assert validate_media_node(node) is True

    def test_node_without_media(self):
        """Node without media field should be invalid."""
        node = {
            "id": "TextOnly",
            "label": "Text-only step"
        }
        assert validate_media_node(node) is False

    def test_node_with_wrong_media_type(self):
        """Node with non-photo media type should be invalid."""
        node = {
            "id": "VideoNode",
            "media": {
                "type": "video",
                "url": "https://example.com/video.mp4"
            }
        }
        assert validate_media_node(node) is False

    def test_node_with_missing_reference(self):
        """Node with media but no url/file_id should be invalid."""
        node = {
            "id": "BadMedia",
            "media": {
                "type": "photo"
                # Missing url or file_id
            }
        }
        assert validate_media_node(node) is False

    def test_node_with_invalid_structure(self):
        """Node with malformed media should be invalid."""
        node = {
            "id": "BadStructure",
            "media": "not_a_dict"
        }
        assert validate_media_node(node) is False

    def test_non_dict_node(self):
        """Non-dictionary node should be invalid."""
        assert validate_media_node(None) is False
        assert validate_media_node("string") is False
        assert validate_media_node([]) is False


class TestMediaReference:
    """Test extraction of media references from config."""

    def test_extract_url_reference(self):
        """Should extract URL reference type."""
        media = {
            "type": "photo",
            "url": "https://example.com/image.jpg"
        }
        ref_type, ref_value = get_media_reference(media)

        assert ref_type == "url"
        assert ref_value == "https://example.com/image.jpg"

    def test_extract_file_id_reference(self):
        """Should extract file_id reference type."""
        media = {
            "type": "photo",
            "file_id": "AgACAgIAAxkBAAI..."
        }
        ref_type, ref_value = get_media_reference(media)

        assert ref_type == "file_id"
        assert ref_value == "AgACAgIAAxkBAAI..."

    def test_url_takes_precedence(self):
        """URL should take precedence if both present."""
        media = {
            "type": "photo",
            "url": "https://example.com/image.jpg",
            "file_id": "AgACAgIAAxkBAAI..."
        }
        ref_type, ref_value = get_media_reference(media)

        assert ref_type == "url"
        assert ref_value == "https://example.com/image.jpg"

    def test_missing_references(self):
        """Should return None if no references present."""
        media = {"type": "photo"}
        ref_type, ref_value = get_media_reference(media)

        assert ref_type is None
        assert ref_value is None


class TestCaptionFormatting:
    """Test caption formatting with availability notices."""

    def test_caption_with_available_media(self):
        """Caption for available media should be unchanged."""
        label = "Check bearing for wear marks"
        result = format_caption_with_fallback(label, media_available=True)

        assert result == label
        assert "[Image unavailable]" not in result

    def test_caption_with_unavailable_media(self):
        """Caption for unavailable media should have prefix."""
        label = "Check bearing for wear marks"
        result = format_caption_with_fallback(label, media_available=False)

        assert result.startswith("[Image unavailable]")
        assert label in result

    def test_unavailable_caption_truncation(self):
        """Long unavailable captions should truncate properly."""
        label = "A" * 1100
        result = format_caption_with_fallback(label, media_available=False)

        assert len(result) == TELEGRAM_CAPTION_LIMIT
        assert result.startswith("[Image unavailable]")
        assert result.endswith("...")


@pytest.mark.asyncio
class TestSendNodeWithMedia:
    """Test sending tree nodes with media to Telegram."""

    async def test_send_text_only_node(self):
        """Should send text-only node without media."""
        node = {
            "id": "TextNode",
            "label": "Check the motor bearings"
        }

        update = MagicMock()
        update.effective_chat.id = 12345

        context = MagicMock()
        context.bot.send_message = AsyncMock(return_value=MagicMock(message_id=999))

        message_id = await send_node_with_media(update, context, node)

        assert message_id == 999
        context.bot.send_message.assert_called_once()
        call_kwargs = context.bot.send_message.call_args.kwargs
        assert call_kwargs["text"] == "Check the motor bearings"
        assert call_kwargs["chat_id"] == 12345

    async def test_send_node_with_photo_url(self):
        """Should send photo node with URL reference."""
        node = {
            "id": "PhotoNode",
            "label": "Bearing diagram",
            "media": {
                "type": "photo",
                "url": "https://example.com/bearing.jpg"
            }
        }

        update = MagicMock()
        update.effective_chat.id = 12345

        context = MagicMock()
        context.bot.send_photo = AsyncMock(return_value=MagicMock(message_id=888))

        message_id = await send_node_with_media(update, context, node)

        assert message_id == 888
        context.bot.send_photo.assert_called_once()
        call_kwargs = context.bot.send_photo.call_args.kwargs
        assert call_kwargs["photo"] == "https://example.com/bearing.jpg"
        assert call_kwargs["caption"] == "Bearing diagram"

    async def test_send_node_with_photo_file_id(self):
        """Should send photo node with file_id reference."""
        node = {
            "id": "PhotoNode",
            "label": "Saved bearing photo",
            "media": {
                "type": "photo",
                "file_id": "AgACAgIAAxkBAAI..."
            }
        }

        update = MagicMock()
        update.effective_chat.id = 12345

        context = MagicMock()
        context.bot.send_photo = AsyncMock(return_value=MagicMock(message_id=777))

        message_id = await send_node_with_media(update, context, node)

        assert message_id == 777
        context.bot.send_photo.assert_called_once()
        call_kwargs = context.bot.send_photo.call_args.kwargs
        assert call_kwargs["photo"] == "AgACAgIAAxkBAAI..."

    async def test_photo_failure_falls_back_to_text(self):
        """Should fall back to text if photo send fails."""
        node = {
            "id": "FailNode",
            "label": "Image that will fail",
            "media": {
                "type": "photo",
                "url": "https://broken.com/404.jpg"
            }
        }

        update = MagicMock()
        update.effective_chat.id = 12345

        context = MagicMock()
        context.bot.send_photo = AsyncMock(side_effect=TelegramError("Photo not found"))
        context.bot.send_message = AsyncMock(return_value=MagicMock(message_id=666))

        message_id = await send_node_with_media(update, context, node)

        # Should have tried photo first, then text fallback
        assert message_id == 666
        context.bot.send_photo.assert_called_once()
        context.bot.send_message.assert_called_once()

        # Fallback message should have unavailable notice
        call_kwargs = context.bot.send_message.call_args.kwargs
        assert "[Image unavailable]" in call_kwargs["text"]

    async def test_both_photo_and_text_fail(self):
        """Should raise MediaDisplayError if all methods fail."""
        node = {
            "id": "TotalFail",
            "label": "Everything fails",
            "media": {
                "type": "photo",
                "url": "https://broken.com/404.jpg"
            }
        }

        update = MagicMock()
        update.effective_chat.id = 12345

        context = MagicMock()
        context.bot.send_photo = AsyncMock(side_effect=TelegramError("Photo failed"))
        context.bot.send_message = AsyncMock(side_effect=TelegramError("Text failed"))

        with pytest.raises(MediaDisplayError):
            await send_node_with_media(update, context, node)

    async def test_caption_truncation_applied(self):
        """Should truncate long captions automatically."""
        long_label = "A" * 1100

        node = {
            "id": "LongCaption",
            "label": long_label,
            "media": {
                "type": "photo",
                "url": "https://example.com/img.jpg"
            }
        }

        update = MagicMock()
        update.effective_chat.id = 12345

        context = MagicMock()
        context.bot.send_photo = AsyncMock(return_value=MagicMock(message_id=555))

        await send_node_with_media(update, context, node)

        call_kwargs = context.bot.send_photo.call_args.kwargs
        caption = call_kwargs["caption"]

        assert len(caption) == TELEGRAM_CAPTION_LIMIT
        assert caption.endswith("...")


@pytest.mark.asyncio
class TestUpdateNodeWithMedia:
    """Test updating existing messages with new node content."""

    async def test_update_text_to_text(self):
        """Should use edit_message_text for text-to-text updates."""
        node = {
            "id": "UpdatedText",
            "label": "Updated instruction"
        }

        query = MagicMock()
        query.message.photo = None  # No photo in current message
        query.edit_message_text = AsyncMock()

        result = await update_node_with_media(query, node)

        assert result is True
        query.edit_message_text.assert_called_once()
        call_kwargs = query.edit_message_text.call_args.kwargs
        assert call_kwargs["text"] == "Updated instruction"

    async def test_update_photo_to_photo(self):
        """Should use edit_message_media for photo-to-photo updates."""
        node = {
            "id": "UpdatedPhoto",
            "label": "Updated diagram",
            "media": {
                "type": "photo",
                "url": "https://example.com/new-diagram.jpg"
            }
        }

        query = MagicMock()
        query.message.photo = [MagicMock()]  # Has photo
        query.edit_message_media = AsyncMock()

        result = await update_node_with_media(query, node)

        assert result is True
        query.edit_message_media.assert_called_once()

    async def test_update_handles_edit_failure(self):
        """Should handle edit failures gracefully."""
        node = {
            "id": "FailUpdate",
            "label": "This will fail"
        }

        query = MagicMock()
        query.message.photo = None
        query.edit_message_text = AsyncMock(side_effect=TelegramError("Edit failed"))

        result = await update_node_with_media(query, node)

        assert result is False


class TestExportedAPI:
    """Test that all expected functions are exported."""

    def test_public_api_exported(self):
        """Verify all public functions are in __all__."""
        from rivet_pro.troubleshooting import media_display

        expected_exports = [
            "MediaDisplayError",
            "truncate_caption",
            "validate_media_node",
            "format_caption_with_fallback",
            "send_node_with_media",
            "update_node_with_media",
        ]

        for export in expected_exports:
            assert export in media_display.__all__
            assert hasattr(media_display, export)
