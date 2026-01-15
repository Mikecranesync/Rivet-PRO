"""
Unit tests for TreeNavigator - In-place message editing
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from telegram import Update, Message, Chat, User, InlineKeyboardMarkup
from telegram.error import BadRequest, TelegramError

from rivet_pro.troubleshooting.navigator import TreeNavigator


class MockTree:
    """Mock TroubleshootingTree for testing."""

    def __init__(self):
        self.nodes = {
            "A": {"text": "Node A content", "children": ["B", "C"]},
            "B": {"text": "Node B content", "children": []},
            "C": {"text": "Node C content", "children": ["D"]},
            "D": {"text": "Node D content", "children": []}
        }

    def get_node(self, node_id):
        return self.nodes.get(node_id)

    def render_node(self, node_id):
        node = self.nodes.get(node_id)
        if not node:
            return None
        return f"<b>{node_id}</b>: {node['text']}"

    def get_node_keyboard(self, node_id):
        # Return a mock keyboard
        return InlineKeyboardMarkup([[]])


@pytest.fixture
def navigator():
    """Create a fresh TreeNavigator instance."""
    return TreeNavigator()


@pytest.fixture
def mock_tree():
    """Create a mock troubleshooting tree."""
    return MockTree()


@pytest.fixture
def mock_update():
    """Create a mock Telegram update."""
    update = Mock(spec=Update)
    update.effective_chat = Mock(spec=Chat)
    update.effective_chat.id = 12345
    update.effective_user = Mock(spec=User)
    update.effective_user.id = 67890
    return update


@pytest.fixture
def mock_context():
    """Create a mock bot context."""
    context = Mock()
    context.bot = AsyncMock()
    return context


@pytest.mark.asyncio
async def test_show_node_sends_new_message_first_time(
    navigator, mock_update, mock_context, mock_tree
):
    """Test that show_node sends a new message on first call."""
    # Mock send_message to return a message
    mock_message = Mock(spec=Message)
    mock_message.message_id = 111
    mock_message.chat_id = 12345
    mock_context.bot.send_message.return_value = mock_message

    # Show node A
    result = await navigator.show_node(mock_update, mock_context, mock_tree, "A")

    # Should send new message
    mock_context.bot.send_message.assert_called_once()
    assert result.message_id == 111

    # Should track the message
    tracked_id = navigator._get_tracked_message_id(mock_update)
    assert tracked_id == 111

    # Should track current node
    assert navigator.get_current_node(mock_update) == "A"


@pytest.mark.asyncio
async def test_navigate_to_edits_existing_message(
    navigator, mock_update, mock_context, mock_tree
):
    """Test that navigate_to edits the existing message."""
    # Setup: First message sent
    mock_message = Mock(spec=Message)
    mock_message.message_id = 111
    mock_message.chat_id = 12345
    mock_context.bot.send_message.return_value = mock_message

    await navigator.show_node(mock_update, mock_context, mock_tree, "A")

    # Reset mock to check second call
    mock_context.bot.reset_mock()
    mock_context.bot.edit_message_text.return_value = True

    # Navigate to node B
    result = await navigator.navigate_to(mock_update, mock_context, mock_tree, "B")

    # Should edit existing message, not send new
    mock_context.bot.edit_message_text.assert_called_once()
    mock_context.bot.send_message.assert_not_called()

    # Should still track same message ID
    tracked_id = navigator._get_tracked_message_id(mock_update)
    assert tracked_id == 111

    # Should update current node
    assert navigator.get_current_node(mock_update) == "B"


@pytest.mark.asyncio
async def test_edit_failure_fallback_to_delete_and_send(
    navigator, mock_update, mock_context, mock_tree
):
    """Test that edit failure triggers delete+send fallback."""
    # Setup: First message sent
    mock_message = Mock(spec=Message)
    mock_message.message_id = 111
    mock_message.chat_id = 12345
    mock_context.bot.send_message.return_value = mock_message

    await navigator.show_node(mock_update, mock_context, mock_tree, "A")

    # Reset and setup for edit failure
    mock_context.bot.reset_mock()
    mock_context.bot.edit_message_text.side_effect = BadRequest("Message can't be edited")

    # New message after fallback
    new_message = Mock(spec=Message)
    new_message.message_id = 222
    new_message.chat_id = 12345
    mock_context.bot.send_message.return_value = new_message

    # Navigate to node B
    result = await navigator.navigate_to(mock_update, mock_context, mock_tree, "B")

    # Should attempt edit
    mock_context.bot.edit_message_text.assert_called_once()

    # Should delete old message
    mock_context.bot.delete_message.assert_called_once_with(
        chat_id=12345,
        message_id=111
    )

    # Should send new message
    mock_context.bot.send_message.assert_called_once()
    assert result.message_id == 222

    # Should track new message ID
    tracked_id = navigator._get_tracked_message_id(mock_update)
    assert tracked_id == 222


@pytest.mark.asyncio
async def test_force_new_message(navigator, mock_update, mock_context, mock_tree):
    """Test force_new parameter sends new message instead of editing."""
    # Setup: First message
    mock_message = Mock(spec=Message)
    mock_message.message_id = 111
    mock_message.chat_id = 12345
    mock_context.bot.send_message.return_value = mock_message

    await navigator.show_node(mock_update, mock_context, mock_tree, "A")

    # Reset and setup for forced new message
    mock_context.bot.reset_mock()
    new_message = Mock(spec=Message)
    new_message.message_id = 222
    new_message.chat_id = 12345
    mock_context.bot.send_message.return_value = new_message

    # Show node B with force_new=True
    result = await navigator.show_node(
        mock_update, mock_context, mock_tree, "B", force_new=True
    )

    # Should NOT attempt edit
    mock_context.bot.edit_message_text.assert_not_called()

    # Should send new message
    mock_context.bot.send_message.assert_called_once()
    assert result.message_id == 222

    # Should track new message
    tracked_id = navigator._get_tracked_message_id(mock_update)
    assert tracked_id == 222


@pytest.mark.asyncio
async def test_invalid_node_raises_error(navigator, mock_update, mock_context, mock_tree):
    """Test that showing invalid node raises ValueError."""
    with pytest.raises(ValueError, match="Node 'INVALID' not found"):
        await navigator.show_node(mock_update, mock_context, mock_tree, "INVALID")


@pytest.mark.asyncio
async def test_session_isolation(navigator, mock_context, mock_tree):
    """Test that different sessions are tracked independently."""
    # Create two different updates (different users)
    update1 = Mock(spec=Update)
    update1.effective_chat = Mock(spec=Chat)
    update1.effective_chat.id = 11111
    update1.effective_user = Mock(spec=User)
    update1.effective_user.id = 11111

    update2 = Mock(spec=Update)
    update2.effective_chat = Mock(spec=Chat)
    update2.effective_chat.id = 22222
    update2.effective_user = Mock(spec=User)
    update2.effective_user.id = 22222

    # Mock messages
    msg1 = Mock(spec=Message)
    msg1.message_id = 111
    msg1.chat_id = 11111

    msg2 = Mock(spec=Message)
    msg2.message_id = 222
    msg2.chat_id = 22222

    mock_context.bot.send_message.side_effect = [msg1, msg2]

    # Show nodes for both sessions
    await navigator.show_node(update1, mock_context, mock_tree, "A")
    await navigator.show_node(update2, mock_context, mock_tree, "B")

    # Each session should track its own message
    assert navigator._get_tracked_message_id(update1) == 111
    assert navigator._get_tracked_message_id(update2) == 222

    # Each session should track its own node
    assert navigator.get_current_node(update1) == "A"
    assert navigator.get_current_node(update2) == "B"


def test_clear_session(navigator, mock_update, mock_context, mock_tree):
    """Test that clear_session removes tracking data."""
    # Track some data
    session_key = navigator._get_session_key(mock_update)
    navigator._message_map[session_key] = 123
    navigator._current_node[session_key] = "A"

    # Clear session
    navigator.clear_session(mock_update)

    # Data should be removed
    assert navigator._get_tracked_message_id(mock_update) is None
    assert navigator.get_current_node(mock_update) is None


def test_get_session_info(navigator, mock_update):
    """Test that get_session_info returns correct data."""
    # Setup session data
    session_key = navigator._get_session_key(mock_update)
    navigator._message_map[session_key] = 123
    navigator._current_node[session_key] = "A"

    # Get info
    info = navigator.get_session_info(mock_update)

    assert info["session_key"] == (12345, 67890)
    assert info["tracked_message_id"] == 123
    assert info["current_node"] == "A"
    assert info["total_sessions"] == 1


@pytest.mark.asyncio
async def test_delete_message_failure_is_graceful(
    navigator, mock_update, mock_context, mock_tree
):
    """Test that delete_message failure doesn't crash the system."""
    # Setup: First message
    mock_message = Mock(spec=Message)
    mock_message.message_id = 111
    mock_message.chat_id = 12345
    mock_context.bot.send_message.return_value = mock_message

    await navigator.show_node(mock_update, mock_context, mock_tree, "A")

    # Setup for edit failure and delete failure
    mock_context.bot.reset_mock()
    mock_context.bot.edit_message_text.side_effect = BadRequest("Can't edit")
    mock_context.bot.delete_message.side_effect = TelegramError("Can't delete")

    # New message
    new_message = Mock(spec=Message)
    new_message.message_id = 222
    new_message.chat_id = 12345
    mock_context.bot.send_message.return_value = new_message

    # Should not crash despite delete failure
    result = await navigator.navigate_to(mock_update, mock_context, mock_tree, "B")

    # Should still send new message
    assert result.message_id == 222


@pytest.mark.asyncio
async def test_telegram_error_during_edit_triggers_fallback(
    navigator, mock_update, mock_context, mock_tree
):
    """Test that general TelegramError during edit triggers fallback."""
    # Setup: First message
    mock_message = Mock(spec=Message)
    mock_message.message_id = 111
    mock_message.chat_id = 12345
    mock_context.bot.send_message.return_value = mock_message

    await navigator.show_node(mock_update, mock_context, mock_tree, "A")

    # Setup for generic TelegramError
    mock_context.bot.reset_mock()
    mock_context.bot.edit_message_text.side_effect = TelegramError("Network error")

    # New message
    new_message = Mock(spec=Message)
    new_message.message_id = 222
    new_message.chat_id = 12345
    mock_context.bot.send_message.return_value = new_message

    # Navigate
    result = await navigator.navigate_to(mock_update, mock_context, mock_tree, "B")

    # Should fallback to delete+send
    mock_context.bot.delete_message.assert_called_once()
    mock_context.bot.send_message.assert_called_once()
    assert result.message_id == 222


def test_session_key_generation(navigator):
    """Test that session keys are generated correctly."""
    update = Mock(spec=Update)
    update.effective_chat = Mock(spec=Chat)
    update.effective_chat.id = 12345
    update.effective_user = Mock(spec=User)
    update.effective_user.id = 67890

    session_key = navigator._get_session_key(update)
    assert session_key == (12345, 67890)


@pytest.mark.asyncio
async def test_multiple_navigations_use_same_message(
    navigator, mock_update, mock_context, mock_tree
):
    """Test that multiple navigations keep editing the same message."""
    # First message
    mock_message = Mock(spec=Message)
    mock_message.message_id = 111
    mock_message.chat_id = 12345
    mock_context.bot.send_message.return_value = mock_message

    await navigator.show_node(mock_update, mock_context, mock_tree, "A")
    original_message_id = navigator._get_tracked_message_id(mock_update)

    # Multiple navigations
    mock_context.bot.reset_mock()
    mock_context.bot.edit_message_text.return_value = True

    await navigator.navigate_to(mock_update, mock_context, mock_tree, "B")
    await navigator.navigate_to(mock_update, mock_context, mock_tree, "C")
    await navigator.navigate_to(mock_update, mock_context, mock_tree, "D")

    # Should all edit the same message
    assert mock_context.bot.edit_message_text.call_count == 3
    assert navigator._get_tracked_message_id(mock_update) == original_message_id
