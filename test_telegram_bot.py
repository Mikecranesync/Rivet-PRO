"""
Simple Telegram Bot for Testing CMMS Integration
Run this to test the Telegram <-> CMMS connection
"""

import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler
)
from integrations.grashjs_client import GrashjsClient

# CMMS credentials - CHANGE THESE to match your account!
CMMS_EMAIL = os.getenv("CMMS_EMAIL", "admin@rivetpro.com")
CMMS_PASSWORD = os.getenv("CMMS_PASSWORD", "password")
CMMS_URL = os.getenv("CMMS_URL", "http://localhost:8081")

# Initialize CMMS client
cmms = GrashjsClient(CMMS_URL)
cmms_logged_in = False


def login_to_cmms():
    """Login to CMMS"""
    global cmms_logged_in
    try:
        cmms.login(CMMS_EMAIL, CMMS_PASSWORD)
        cmms_logged_in = True
        print("✅ Logged into CMMS successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to login to CMMS: {e}")
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user = update.effective_user

    keyboard = [
        [
            InlineKeyboardButton("📦 View Assets", callback_data="assets"),
            InlineKeyboardButton("🔧 Work Orders", callback_data="workorders"),
        ],
        [
            InlineKeyboardButton("➕ Create WO", callback_data="create_wo"),
            InlineKeyboardButton("ℹ️ Help", callback_data="help"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"👋 Welcome to Rivet-PRO CMMS, {user.first_name}!\n\n"
        f"🌐 CMMS: {CMMS_URL}\n"
        f"📧 User: {CMMS_EMAIL}\n"
        f"🔐 Status: {'✅ Connected' if cmms_logged_in else '❌ Not connected'}\n\n"
        "What would you like to do?",
        reply_markup=reply_markup
    )


async def assets_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all assets"""
    if not cmms_logged_in:
        await update.message.reply_text("❌ Not logged into CMMS. Please restart the bot.")
        return

    try:
        # Get assets
        result = cmms.get_assets(size=10)
        assets = result.get('content', [])
        total = result.get('totalElements', 0)

        if not assets:
            await update.message.reply_text(
                "📦 No assets found in CMMS.\n\n"
                "Create an asset in the web UI first:\n"
                "http://localhost:3001"
            )
            return

        message = f"📦 *Assets in CMMS* ({total} total)\n\n"

        for asset in assets:
            message += f"*{asset.get('name')}*\n"
            message += f"├ ID: {asset.get('id')}\n"

            if asset.get('serialNumber'):
                message += f"├ S/N: {asset.get('serialNumber')}\n"

            if asset.get('model'):
                message += f"├ Model: {asset.get('model')}\n"

            if asset.get('manufacturer'):
                message += f"├ Mfr: {asset.get('manufacturer')}\n"

            message += f"└ Status: {asset.get('status', 'N/A')}\n\n"

        await update.message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching assets: {str(e)}")


async def workorders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List work orders"""
    if not cmms_logged_in:
        await update.message.reply_text("❌ Not logged into CMMS. Please restart the bot.")
        return

    try:
        result = cmms.get_work_orders(status="OPEN", size=10)
        work_orders = result.get('content', [])
        total = result.get('totalElements', 0)

        if not work_orders:
            await update.message.reply_text(
                "🔧 No open work orders found.\n\n"
                "Create a work order with /createwo"
            )
            return

        message = f"🔧 *Open Work Orders* ({total} total)\n\n"

        for wo in work_orders:
            message += f"*#{wo.get('id')} - {wo.get('title')}*\n"
            message += f"├ Priority: {wo.get('priority', 'N/A')}\n"
            message += f"├ Status: {wo.get('status')}\n"

            if wo.get('asset'):
                message += f"├ Asset: {wo.get('asset', {}).get('name', 'N/A')}\n"

            if wo.get('dueDate'):
                message += f"└ Due: {wo.get('dueDate')}\n"
            else:
                message += f"└ No due date\n"

            message += "\n"

        await update.message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching work orders: {str(e)}")


async def create_wo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a test work order"""
    if not cmms_logged_in:
        await update.message.reply_text("❌ Not logged into CMMS. Please restart the bot.")
        return

    try:
        # Get the first asset
        result = cmms.get_assets(size=1)
        assets = result.get('content', [])

        if not assets:
            await update.message.reply_text(
                "❌ No assets found. Create an asset first at:\n"
                "http://localhost:3001"
            )
            return

        asset = assets[0]

        # Create work order
        wo = cmms.create_work_order(
            title=f"Test WO from Telegram Bot",
            description=f"Created by {update.effective_user.first_name} via Telegram",
            asset_id=asset.get('id'),
            priority="MEDIUM"
        )

        await update.message.reply_text(
            f"✅ *Work Order Created!*\n\n"
            f"ID: #{wo.get('id')}\n"
            f"Title: {wo.get('title')}\n"
            f"Asset: {asset.get('name')}\n"
            f"Priority: {wo.get('priority')}\n"
            f"Status: {wo.get('status')}\n\n"
            f"View it at:\n"
            f"http://localhost:3001/app/work-orders/{wo.get('id')}",
            parse_mode='Markdown'
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error creating work order: {str(e)}")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses"""
    query = update.callback_query
    await query.answer()

    if query.data == "assets":
        # Call assets command
        update.message = query.message
        await assets_command(update, context)

    elif query.data == "workorders":
        # Call work orders command
        update.message = query.message
        await workorders_command(update, context)

    elif query.data == "create_wo":
        # Call create WO command
        update.message = query.message
        await create_wo(update, context)

    elif query.data == "help":
        await query.edit_message_text(
            "🤖 *Rivet-PRO CMMS Bot*\n\n"
            "*Available Commands:*\n"
            "/start - Show main menu\n"
            "/assets - List all assets\n"
            "/wo - List work orders\n"
            "/createwo - Create test work order\n\n"
            "*CMMS Web UI:*\n"
            "http://localhost:3001",
            parse_mode='Markdown'
        )


def main():
    """Start the bot"""
    # Check for bot token
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not bot_token:
        print("❌ Error: TELEGRAM_BOT_TOKEN not set!")
        print("\nSet it with:")
        print('  set TELEGRAM_BOT_TOKEN=your_token_here')
        print("\nOr run:")
        print('  python test_telegram_bot.py')
        sys.exit(1)

    # Login to CMMS
    print("🔐 Logging into CMMS...")
    print(f"   URL: {CMMS_URL}")
    print(f"   Email: {CMMS_EMAIL}")

    if not login_to_cmms():
        print("\n❌ Failed to login to CMMS!")
        print("\nMake sure:")
        print("1. CMMS is running: docker-compose ps")
        print("2. You've created an account at: http://localhost:3001")
        print("3. Update CMMS_EMAIL and CMMS_PASSWORD in this script")
        print("\nOr set environment variables:")
        print("  set CMMS_EMAIL=your@email.com")
        print("  set CMMS_PASSWORD=yourpassword")
        sys.exit(1)

    # Build bot
    print(f"\n🤖 Starting Telegram bot...")
    app = ApplicationBuilder().token(bot_token).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("assets", assets_command))
    app.add_handler(CommandHandler("wo", workorders_command))
    app.add_handler(CommandHandler("createwo", create_wo))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Start
    print("✅ Bot is running!")
    print("📱 Open Telegram and send /start to your bot")
    print("\n⏸  Press Ctrl+C to stop\n")

    app.run_polling()


if __name__ == "__main__":
    main()
