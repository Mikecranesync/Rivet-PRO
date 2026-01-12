"""
Comprehensive tests for Telegram bot handlers.

Tests all command handlers, message handlers, photo processing,
usage limits, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Message, Photo, PhotoSize
from telegram.ext import ContextTypes
from rivet_pro.adapters.telegram.bot import TelegramBot


@pytest.fixture
def bot():
    """Create TelegramBot instance for testing."""
    return TelegramBot()


@pytest.fixture
def mock_update():
    """Create mock Telegram Update object."""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 123456789
    update.effective_user.first_name = "Test"
    update.effective_user.username = "testuser"
    update.message = AsyncMock(spec=Message)
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create mock Telegram Context object."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    return context


@pytest.fixture
def mock_db():
    """Create mock database."""
    db = AsyncMock()
    db.execute_query_async = AsyncMock()
    db.fetchval = AsyncMock()
    db.fetchrow = AsyncMock()
    return db


@pytest.fixture
def mock_usage_service():
    """Create mock usage service."""
    service = AsyncMock()
    service.can_use_service = AsyncMock(return_value=(True, 5, "under_limit"))
    service.record_lookup = AsyncMock()
    return service


@pytest.fixture
def mock_stripe_service():
    """Create mock stripe service."""
    service = AsyncMock()
    service.is_pro_user = AsyncMock(return_value=False)
    service.create_checkout_session = AsyncMock(return_value="https://checkout.stripe.com/test")
    return service


@pytest.fixture
def mock_equipment_service():
    """Create mock equipment service."""
    service = AsyncMock()
    service.match_or_create_equipment = AsyncMock(return_value=("eq-123", "EQ-2026-000001", True))
    return service


# ============================================================================
# /start Command Tests
# ============================================================================

@pytest.mark.asyncio
async def test_start_command_sends_welcome_message(bot, mock_update, mock_context):
    """Test /start command sends welcome message."""
    await bot.start_command(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "RIVET" in call_args
    assert "photo" in call_args.lower()


@pytest.mark.asyncio
async def test_start_command_uses_user_first_name(bot, mock_update, mock_context):
    """Test /start command personalizes greeting."""
    mock_update.effective_user.first_name = "Alice"

    await bot.start_command(mock_update, mock_context)

    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "Alice" in call_args


# ============================================================================
# /equip Command Tests
# ============================================================================

@pytest.mark.asyncio
async def test_equip_list_shows_user_equipment(bot, mock_update, mock_context, mock_db):
    """Test /equip list shows user's equipment."""
    bot.db = mock_db
    mock_db.execute_query_async.return_value = [
        {
            "equipment_number": "EQ-2026-000001",
            "manufacturer": "Siemens",
            "model_number": "G120C",
            "work_order_count": 3
        }
    ]

    await bot.equip_command(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    response = mock_update.message.reply_text.call_args[0][0]
    assert "EQ-2026-000001" in response
    assert "Siemens" in response
    assert "G120C" in response


@pytest.mark.asyncio
async def test_equip_list_empty_shows_helpful_message(bot, mock_update, mock_context, mock_db):
    """Test /equip list with no equipment shows helpful message."""
    bot.db = mock_db
    mock_db.execute_query_async.return_value = []

    await bot.equip_command(mock_update, mock_context)

    response = mock_update.message.reply_text.call_args[0][0]
    assert "No equipment found" in response
    assert "photo" in response.lower()


@pytest.mark.asyncio
async def test_equip_search_finds_matching_equipment(bot, mock_update, mock_context, mock_db):
    """Test /equip search finds matching equipment."""
    bot.db = mock_db
    mock_context.args = ["search", "siemens"]
    mock_db.execute_query_async.return_value = [
        {
            "equipment_number": "EQ-2026-000001",
            "manufacturer": "Siemens",
            "model_number": "G120C",
            "serial_number": "SN12345"
        }
    ]

    await bot.equip_command(mock_update, mock_context)

    response = mock_update.message.reply_text.call_args[0][0]
    assert "siemens" in response.lower()
    assert "EQ-2026-000001" in response


@pytest.mark.asyncio
async def test_equip_search_no_results(bot, mock_update, mock_context, mock_db):
    """Test /equip search with no results."""
    bot.db = mock_db
    mock_context.args = ["search", "nonexistent"]
    mock_db.execute_query_async.return_value = []

    await bot.equip_command(mock_update, mock_context)

    response = mock_update.message.reply_text.call_args[0][0]
    assert "No equipment found" in response


@pytest.mark.asyncio
async def test_equip_view_shows_equipment_details(bot, mock_update, mock_context, mock_db):
    """Test /equip view shows equipment details."""
    bot.db = mock_db
    mock_context.args = ["view", "EQ-2026-000001"]
    mock_db.execute_query_async.return_value = [[{
        "equipment_number": "EQ-2026-000001",
        "manufacturer": "Siemens",
        "model_number": "G120C",
        "serial_number": "SN12345",
        "equipment_type": "VFD",
        "location": "Building A",
        "work_order_count": 3,
        "last_reported_fault": "Overcurrent"
    }]]

    await bot.equip_command(mock_update, mock_context)

    response = mock_update.message.reply_text.call_args[0][0]
    assert "EQ-2026-000001" in response
    assert "Siemens" in response
    assert "Building A" in response


# ============================================================================
# /wo (Work Order) Command Tests
# ============================================================================

@pytest.mark.asyncio
async def test_wo_list_shows_work_orders(bot, mock_update, mock_context):
    """Test /wo list shows user's work orders."""
    mock_work_order_service = AsyncMock()
    mock_work_order_service.list_work_orders_by_user = AsyncMock(return_value=[
        {
            "work_order_number": "WO-2026-000001",
            "title": "Motor repair",
            "status": "open",
            "priority": "high",
            "equipment_number": "EQ-2026-000001"
        }
    ])
    bot.work_order_service = mock_work_order_service

    await bot.wo_command(mock_update, mock_context)

    response = mock_update.message.reply_text.call_args[0][0]
    assert "WO-2026-000001" in response
    assert "Motor repair" in response


@pytest.mark.asyncio
async def test_wo_list_empty_shows_message(bot, mock_update, mock_context):
    """Test /wo list with no work orders."""
    mock_work_order_service = AsyncMock()
    mock_work_order_service.list_work_orders_by_user = AsyncMock(return_value=[])
    bot.work_order_service = mock_work_order_service

    await bot.wo_command(mock_update, mock_context)

    response = mock_update.message.reply_text.call_args[0][0]
    assert "No work orders found" in response


# ============================================================================
# /stats Command Tests
# ============================================================================

@pytest.mark.asyncio
async def test_stats_command_shows_user_statistics(bot, mock_update, mock_context, mock_db):
    """Test /stats command shows equipment and work order stats."""
    bot.db = mock_db
    mock_db.fetchval.return_value = 5  # Equipment count
    mock_db.fetchrow.return_value = {
        "open": 2,
        "in_progress": 1,
        "completed": 7
    }

    await bot.stats_command(mock_update, mock_context)

    response = mock_update.message.reply_text.call_args[0][0]
    assert "Equipment:" in response
    assert "5" in response
    assert "Work Orders:" in response


# ============================================================================
# /upgrade Command Tests
# ============================================================================

@pytest.mark.asyncio
async def test_upgrade_command_creates_checkout_session(bot, mock_update, mock_context, mock_stripe_service):
    """Test /upgrade creates Stripe checkout session."""
    bot.stripe_service = mock_stripe_service

    await bot.upgrade_command(mock_update, mock_context)

    mock_stripe_service.create_checkout_session.assert_called_once_with(mock_update.effective_user.id)
    response = mock_update.message.reply_text.call_args[0][0]
    assert "RIVET Pro" in response
    assert "29" in response  # Price
    assert "checkout.stripe.com" in response


@pytest.mark.asyncio
async def test_upgrade_command_already_pro_user(bot, mock_update, mock_context, mock_stripe_service):
    """Test /upgrade for existing Pro user."""
    mock_stripe_service.is_pro_user.return_value = True
    bot.stripe_service = mock_stripe_service

    await bot.upgrade_command(mock_update, mock_context)

    response = mock_update.message.reply_text.call_args[0][0]
    assert "already a RIVET Pro member" in response
    mock_stripe_service.create_checkout_session.assert_not_called()


# ============================================================================
# Photo Handler Tests
# ============================================================================

@pytest.mark.asyncio
async def test_photo_handler_under_free_limit(bot, mock_update, mock_context, mock_usage_service, mock_equipment_service):
    """Test photo handler processes photo when under free limit."""
    bot.usage_service = mock_usage_service
    bot.equipment_service = mock_equipment_service

    # Mock photo
    mock_photo = AsyncMock()
    mock_photo.get_file = AsyncMock()
    mock_photo.get_file.return_value.download_as_bytearray = AsyncMock(return_value=b"fake_image_data")
    mock_update.message.photo = [mock_photo]

    # Mock OCR result
    mock_ocr_result = MagicMock()
    mock_ocr_result.manufacturer = "Siemens"
    mock_ocr_result.model_number = "G120C"
    mock_ocr_result.serial_number = "SN12345"
    mock_ocr_result.confidence = 0.95
    mock_ocr_result.error = None

    with patch("rivet_pro.adapters.telegram.bot.analyze_image", return_value=mock_ocr_result):
        await bot._handle_photo(mock_update, mock_context)

    # Verify OCR was run
    mock_usage_service.can_use_service.assert_called_once()
    mock_usage_service.record_lookup.assert_called_once()


@pytest.mark.asyncio
async def test_photo_handler_free_limit_reached(bot, mock_update, mock_context, mock_usage_service, mock_stripe_service):
    """Test photo handler blocks when free limit reached."""
    mock_usage_service.can_use_service.return_value = (False, 10, "limit_reached")
    bot.usage_service = mock_usage_service
    bot.stripe_service = mock_stripe_service

    mock_update.message.photo = [AsyncMock()]

    await bot._handle_photo(mock_update, mock_context)

    # Verify upgrade message sent
    response = mock_update.message.reply_text.call_args[0][0]
    assert "Free Limit Reached" in response
    assert "Upgrade to RIVET Pro" in response


@pytest.mark.asyncio
async def test_photo_handler_ocr_error(bot, mock_update, mock_context, mock_usage_service):
    """Test photo handler handles OCR errors gracefully."""
    bot.usage_service = mock_usage_service

    mock_photo = AsyncMock()
    mock_photo.get_file = AsyncMock()
    mock_photo.get_file.return_value.download_as_bytearray = AsyncMock(return_value=b"fake_image_data")
    mock_update.message.photo = [mock_photo]

    # Mock OCR error
    mock_ocr_result = MagicMock()
    mock_ocr_result.error = "Failed to detect text in image"

    mock_msg = AsyncMock()
    mock_update.message.reply_text.return_value = mock_msg

    with patch("rivet_pro.adapters.telegram.bot.analyze_image", return_value=mock_ocr_result):
        await bot._handle_photo(mock_update, mock_context)

    # Verify error message sent
    assert mock_msg.edit_text.called
    error_response = mock_msg.edit_text.call_args[0][0]
    assert "Failed to detect text" in error_response


# ============================================================================
# Text Handler Tests
# ============================================================================

@pytest.mark.asyncio
async def test_text_handler_routes_to_sme(bot, mock_update, mock_context):
    """Test text handler routes questions to SME."""
    mock_update.message.text = "How do I troubleshoot a Siemens VFD?"

    mock_msg = AsyncMock()
    mock_update.message.reply_text.return_value = mock_msg

    with patch("rivet_pro.adapters.telegram.bot.route_to_sme", return_value="SME response here"):
        await bot._handle_text(mock_update, mock_context)

    # Verify SME was called
    assert mock_msg.edit_text.called
    response = mock_msg.edit_text.call_args[0][0]
    assert response == "SME response here"


# ============================================================================
# Error Handler Tests
# ============================================================================

@pytest.mark.asyncio
async def test_error_handler_notifies_user(bot, mock_update, mock_context):
    """Test error handler sends error message to user."""
    mock_context.error = Exception("Test error")

    await bot.error_handler(mock_update, mock_context)

    mock_update.effective_message.reply_text.assert_called_once()
    response = mock_update.effective_message.reply_text.call_args[0][0]
    assert "went wrong" in response.lower()


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_handle_message_routes_photo_correctly(bot, mock_update, mock_context):
    """Test handle_message routes photo to photo handler."""
    mock_update.message.photo = [AsyncMock()]
    mock_update.message.text = None

    with patch.object(bot, '_handle_photo', new=AsyncMock()) as mock_handle_photo:
        await bot.handle_message(mock_update, mock_context)
        mock_handle_photo.assert_called_once()


@pytest.mark.asyncio
async def test_handle_message_routes_text_correctly(bot, mock_update, mock_context):
    """Test handle_message routes text to text handler."""
    mock_update.message.photo = None
    mock_update.message.text = "What is a VFD?"

    with patch.object(bot, '_handle_text', new=AsyncMock()) as mock_handle_text:
        await bot.handle_message(mock_update, mock_context)
        mock_handle_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_message_unknown_type_sends_help(bot, mock_update, mock_context):
    """Test handle_message with unknown message type sends help."""
    mock_update.message.photo = None
    mock_update.message.text = None
    mock_update.message.document = None

    await bot.handle_message(mock_update, mock_context)

    response = mock_update.message.reply_text.call_args[0][0]
    assert "photo" in response.lower()


# ============================================================================
# Build/Initialization Tests
# ============================================================================

def test_build_creates_application(bot):
    """Test build() creates and configures application."""
    with patch("rivet_pro.adapters.telegram.bot.settings") as mock_settings:
        mock_settings.telegram_bot_token = "test_token"

        app = bot.build()

        assert app is not None
        assert bot.application is not None


# ============================================================================
# Edge Cases and Error Conditions
# ============================================================================

@pytest.mark.asyncio
async def test_equip_command_database_error(bot, mock_update, mock_context, mock_db):
    """Test /equip handles database errors gracefully."""
    bot.db = mock_db
    mock_db.execute_query_async.side_effect = Exception("Database connection failed")

    await bot.equip_command(mock_update, mock_context)

    response = mock_update.message.reply_text.call_args[0][0]
    assert "error occurred" in response.lower()


@pytest.mark.asyncio
async def test_stats_command_handles_no_data(bot, mock_update, mock_context, mock_db):
    """Test /stats handles case with no data."""
    bot.db = mock_db
    mock_db.fetchval.return_value = 0
    mock_db.fetchrow.return_value = None

    await bot.stats_command(mock_update, mock_context)

    # Should not crash, should show zeros
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_upgrade_command_stripe_error(bot, mock_update, mock_context, mock_stripe_service):
    """Test /upgrade handles Stripe errors gracefully."""
    mock_stripe_service.is_pro_user.return_value = False
    mock_stripe_service.create_checkout_session.side_effect = Exception("Stripe API error")
    bot.stripe_service = mock_stripe_service

    await bot.upgrade_command(mock_update, mock_context)

    response = mock_update.message.reply_text.call_args[0][0]
    assert "Could not generate upgrade link" in response
