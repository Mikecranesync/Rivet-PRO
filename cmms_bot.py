#!/usr/bin/env python3
"""
Rivet-PRO CMMS Telegram Bot
Connects to Grashjs CMMS running at localhost:8081
"""
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import logging

# Add integrations to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'integrations'))
from grashjs_client import GrashjsClient

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration from .env
BOT_TOKEN = "7855741814:AAFHIk0vPmG9ZHACISMl-izzDwdS0bk_nYo"
ADMIN_TELEGRAM_ID = 8445149012
CMMS_API_URL = "http://localhost:8081"
CMMS_EMAIL = "mike@cranesync.com"
CMMS_PASSWORD = "Bo1ws2er@12"

# Global CMMS client
cmms = None


def get_main_menu():
    """Create the main menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("📦 View Assets", callback_data="view_assets"),
            InlineKeyboardButton("🔧 Work Orders", callback_data="view_workorders"),
        ],
        [
            InlineKeyboardButton("➕ Create Asset", callback_data="create_asset"),
            InlineKeyboardButton("➕ Create WO", callback_data="create_wo"),
        ],
        [
            InlineKeyboardButton("📊 CMMS Status", callback_data="cmms_status"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - show main menu"""
    global cmms

    user = update.effective_user
    logger.info(f"User {user.id} ({user.first_name}) started the bot")

    # Try to login to CMMS
    try:
        if cmms is None:
            logger.info("Connecting to CMMS...")
            cmms = GrashjsClient(CMMS_API_URL)
            cmms.login(CMMS_EMAIL, CMMS_PASSWORD)
            logger.info("✅ Connected to CMMS")

        message = (
            f"👋 Welcome to Rivet-PRO CMMS, {user.first_name}!\n\n"
            f"🌐 CMMS: {CMMS_API_URL}\n"
            f"📧 User: {CMMS_EMAIL}\n"
            f"🔐 Status: ✅ Connected\n\n"
            f"What would you like to do?"
        )

        await update.message.reply_text(
            message,
            reply_markup=get_main_menu()
        )

    except Exception as e:
        logger.error(f"Failed to connect to CMMS: {e}")
        await update.message.reply_text(
            f"❌ Failed to connect to CMMS\n\n"
            f"Error: {str(e)}\n\n"
            f"Make sure the CMMS is running at {CMMS_API_URL}"
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses"""
    query = update.callback_query
    await query.answer()

    action = query.data

    if action == "view_assets":
        await view_assets(query)
    elif action == "view_workorders":
        await view_workorders(query)
    elif action == "create_asset":
        await create_asset_prompt(query)
    elif action == "create_wo":
        await create_wo_prompt(query)
    elif action == "cmms_status":
        await cmms_status(query)
    elif action == "back_to_menu":
        await query.edit_message_text(
            "What would you like to do?",
            reply_markup=get_main_menu()
        )


async def view_assets(query):
    """Show all assets from CMMS"""
    global cmms

    try:
        logger.info("Fetching assets from CMMS...")
        result = cmms.get_assets()

        if not result or 'content' not in result:
            await query.edit_message_text(
                "📦 No assets found in CMMS\n\n"
                "Create one using the web UI or the bot!",
                reply_markup=get_main_menu()
            )
            return

        assets = result['content']
        total = result.get('totalElements', len(assets))

        if not assets:
            await query.edit_message_text(
                "📦 No assets found in CMMS\n\n"
                "Create one using the web UI or the bot!",
                reply_markup=get_main_menu()
            )
            return

        message = f"📦 Assets in CMMS ({total} total)\n\n"

        for asset in assets[:10]:  # Show first 10
            name = asset.get('name', 'Unnamed')
            asset_id = asset.get('id', 'N/A')
            model = asset.get('model', 'N/A')
            serial = asset.get('serialNumber', 'N/A')

            message += f"▫️ {name}\n"
            message += f"   ID: {asset_id} | Model: {model}\n"
            if serial != 'N/A':
                message += f"   S/N: {serial}\n"
            message += "\n"

        if total > 10:
            message += f"\n... and {total - 10} more"

        keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="back_to_menu")]]
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Error fetching assets: {e}")
        await query.edit_message_text(
            f"❌ Error fetching assets: {str(e)}",
            reply_markup=get_main_menu()
        )


async def view_workorders(query):
    """Show work orders from CMMS"""
    global cmms

    try:
        logger.info("Fetching work orders from CMMS...")
        result = cmms.get_work_orders()

        if not result or 'content' not in result:
            await query.edit_message_text(
                "🔧 No work orders found\n\n"
                "Create one to get started!",
                reply_markup=get_main_menu()
            )
            return

        work_orders = result['content']
        total = result.get('totalElements', len(work_orders))

        if not work_orders:
            await query.edit_message_text(
                "🔧 No work orders found\n\n"
                "Create one to get started!",
                reply_markup=get_main_menu()
            )
            return

        message = f"🔧 Work Orders ({total} total)\n\n"

        for wo in work_orders[:10]:
            title = wo.get('title', 'Untitled')
            wo_id = wo.get('id', 'N/A')
            status = wo.get('status', 'N/A')
            priority = wo.get('priority', 'N/A')

            # Status emoji
            status_emoji = {
                'OPEN': '🟢',
                'IN_PROGRESS': '🟡',
                'ON_HOLD': '🟠',
                'COMPLETE': '✅',
            }.get(status, '⚪')

            message += f"{status_emoji} {title}\n"
            message += f"   ID: {wo_id} | Status: {status} | Priority: {priority}\n\n"

        if total > 10:
            message += f"\n... and {total - 10} more"

        keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="back_to_menu")]]
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Error fetching work orders: {e}")
        await query.edit_message_text(
            f"❌ Error fetching work orders: {str(e)}",
            reply_markup=get_main_menu()
        )


async def create_asset_prompt(query):
    """Prompt user to create an asset"""
    message = (
        "➕ Create New Asset\n\n"
        "To create a new asset, go to:\n"
        f"🌐 {CMMS_API_URL.replace('8081', '3001')}\n\n"
        "Or use the /createasset command (coming soon!)"
    )

    keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="back_to_menu")]]
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def create_wo_prompt(query):
    """Create a quick test work order"""
    global cmms

    try:
        logger.info("Creating test work order...")

        wo = cmms.create_work_order(
            title="Test WO from Telegram",
            description="Created via Telegram bot",
            priority="MEDIUM"
        )

        wo_id = wo.get('id', 'N/A')

        message = (
            "✅ Work Order Created!\n\n"
            f"📋 Title: Test WO from Telegram\n"
            f"🆔 ID: {wo_id}\n"
            f"📊 Priority: MEDIUM\n\n"
            f"View it at:\n"
            f"🌐 {CMMS_API_URL.replace('8081', '3001')}/app/work-orders/{wo_id}"
        )

        keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="back_to_menu")]]
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Error creating work order: {e}")
        await query.edit_message_text(
            f"❌ Error creating work order: {str(e)}",
            reply_markup=get_main_menu()
        )


async def cmms_status(query):
    """Show CMMS connection status"""
    global cmms

    try:
        # Try to get current user to verify connection
        user_info = cmms.get_current_user()

        message = (
            "📊 CMMS Status\n\n"
            f"🌐 API: {CMMS_API_URL}\n"
            f"✅ Connected: Yes\n"
            f"👤 User: {user_info.get('email', 'N/A')}\n"
            f"🏢 Organization: {user_info.get('organizationName', 'N/A')}\n"
        )

    except Exception as e:
        message = (
            "📊 CMMS Status\n\n"
            f"🌐 API: {CMMS_API_URL}\n"
            f"❌ Connected: No\n"
            f"⚠️ Error: {str(e)}\n"
        )

    keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="back_to_menu")]]
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message"""
    message = (
        "🤖 Rivet-PRO CMMS Bot Help\n\n"
        "📱 Commands:\n"
        "/start - Main menu\n"
        "/help - This help message\n"
        "/status - CMMS connection status\n\n"
        "🌐 Web UI:\n"
        f"{CMMS_API_URL.replace('8081', '3001')}\n\n"
        "💡 Use the menu buttons for quick access!"
    )

    await update.message.reply_text(message)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show CMMS status via command"""
    global cmms

    try:
        user_info = cmms.get_current_user()

        message = (
            "📊 CMMS Status\n\n"
            f"🌐 API: {CMMS_API_URL}\n"
            f"✅ Connected: Yes\n"
            f"👤 User: {user_info.get('email', 'N/A')}\n"
            f"🏢 Organization: {user_info.get('organizationName', 'N/A')}\n"
        )

    except Exception as e:
        message = (
            "📊 CMMS Status\n\n"
            f"🌐 API: {CMMS_API_URL}\n"
            f"❌ Connected: No\n"
            f"⚠️ Error: {str(e)}\n"
        )

    await update.message.reply_text(message)


def main():
    """Start the bot"""
    global cmms

    print("=" * 50)
    print("RIVET-PRO CMMS TELEGRAM BOT")
    print("=" * 50)
    print(f"CMMS API: {CMMS_API_URL}")
    print(f"Login: {CMMS_EMAIL}")
    print(f"Bot Token: {BOT_TOKEN[:20]}...")
    print("=" * 50)

    # Initialize CMMS connection
    try:
        print("\nConnecting to CMMS...")
        cmms = GrashjsClient(CMMS_API_URL)
        cmms.login(CMMS_EMAIL, CMMS_PASSWORD)
        print(">> Connected to CMMS successfully!")

        # Get user info
        user_info = cmms.get_current_user()
        print(f">> Logged in as: {user_info.get('email')}")
        print(f">> Organization: {user_info.get('organizationName', 'N/A')}")

    except Exception as e:
        print(f"WARNING: Could not connect to CMMS: {e}")
        print("WARNING: Bot will start anyway, but CMMS features won't work")
        print("WARNING: Make sure CMMS is running at http://localhost:8081")

    print("\nStarting Telegram bot...")

    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Start the bot
    print(">> Bot is running!")
    print(">> Open Telegram and send /start to your bot")
    print("\nPress Ctrl+C to stop\n")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
