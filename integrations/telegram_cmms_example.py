"""
Telegram Bot Integration Example for Grashjs CMMS
Shows how to integrate CMMS functionality into your Telegram bot
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler
)
from grashjs_client import GrashjsClient
import os
from typing import Dict, Any

# Conversation states
AWAITING_ASSET_NAME, AWAITING_WO_TITLE, AWAITING_WO_DESCRIPTION = range(3)

# Initialize CMMS client
cmms = GrashjsClient(os.getenv("GRASHJS_API_URL", "http://localhost:8081"))

# Store user sessions (in production, use a database)
user_sessions: Dict[int, Dict[str, Any]] = {}


def get_user_session(user_id: int) -> Dict[str, Any]:
    """Get or create user session"""
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "authenticated": False,
            "token": None,
            "temp_data": {}
        }
    return user_sessions[user_id]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - show main menu"""
    user = update.effective_user
    session = get_user_session(user.id)

    if not session["authenticated"]:
        await update.message.reply_text(
            f"👋 Welcome to Rivet-PRO CMMS, {user.first_name}!\n\n"
            "Please login first using:\n"
            "/login <email> <password>\n\n"
            "Or register a new account with:\n"
            "/register"
        )
        return

    keyboard = [
        [
            InlineKeyboardButton("📦 Assets", callback_data="menu_assets"),
            InlineKeyboardButton("🔧 Work Orders", callback_data="menu_workorders"),
        ],
        [
            InlineKeyboardButton("📅 Preventive Maintenance", callback_data="menu_pm"),
            InlineKeyboardButton("🔩 Parts", callback_data="menu_parts"),
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="menu_help"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🏭 *Rivet-PRO CMMS Dashboard*\n\n"
        "What would you like to do?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Login command"""
    if len(context.args) != 2:
        await update.message.reply_text(
            "Usage: /login <email> <password>\n"
            "Example: /login admin@rivetpro.com mypassword"
        )
        return

    email, password = context.args
    user_id = update.effective_user.id

    try:
        token = cmms.login(email, password)
        session = get_user_session(user_id)
        session["authenticated"] = True
        session["token"] = token

        user_info = cmms.get_current_user()

        await update.message.reply_text(
            f"✅ Logged in successfully!\n\n"
            f"User: {user_info.get('firstName')} {user_info.get('lastName')}\n"
            f"Company: {user_info.get('company', {}).get('name', 'N/A')}\n\n"
            "Use /start to access the main menu."
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Login failed: {str(e)}\n\n"
            "Please check your credentials and try again."
        )


async def search_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search for assets"""
    query = update.message.text if update.message else None
    user_id = update.effective_user.id
    session = get_user_session(user_id)

    if not session["authenticated"]:
        await update.message.reply_text("Please /login first")
        return

    search_query = " ".join(context.args) if context.args else None

    try:
        result = cmms.get_assets(search=search_query, size=5)
        assets = result.get("content", [])

        if not assets:
            await update.message.reply_text("No assets found.")
            return

        message = "📦 *Assets:*\n\n"
        for asset in assets:
            message += (
                f"*{asset.get('name')}*\n"
                f"ID: {asset.get('id')}\n"
                f"Serial: {asset.get('serialNumber', 'N/A')}\n"
                f"Status: {asset.get('status', 'N/A')}\n"
                f"Description: {asset.get('description', 'N/A')}\n\n"
            )

        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def create_asset_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start asset creation flow"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)

    if not session["authenticated"]:
        await update.message.reply_text("Please /login first")
        return ConversationHandler.END

    await update.message.reply_text(
        "🆕 *Create New Asset*\n\n"
        "Please enter the asset name:",
        parse_mode="Markdown"
    )
    return AWAITING_ASSET_NAME


async def create_asset_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle asset name input"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)

    asset_name = update.message.text
    session["temp_data"]["asset_name"] = asset_name

    await update.message.reply_text(
        f"Asset name: *{asset_name}*\n\n"
        "Now send me the asset description (or /skip):",
        parse_mode="Markdown"
    )
    return AWAITING_WO_DESCRIPTION


async def create_asset_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finish asset creation"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)

    description = update.message.text if update.message.text != "/skip" else None
    asset_name = session["temp_data"].get("asset_name")

    try:
        asset = cmms.create_asset(
            name=asset_name,
            description=description
        )

        await update.message.reply_text(
            f"✅ *Asset Created!*\n\n"
            f"Name: {asset.get('name')}\n"
            f"ID: {asset.get('id')}\n"
            f"Description: {asset.get('description', 'N/A')}",
            parse_mode="Markdown"
        )

        session["temp_data"] = {}
        return ConversationHandler.END

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        return ConversationHandler.END


async def create_work_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a work order"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)

    if not session["authenticated"]:
        await update.message.reply_text("Please /login first")
        return

    if len(context.args) < 1:
        await update.message.reply_text(
            "Usage: /wo <title> [description]\n"
            "Example: /wo \"Fix motor\" Motor making noise"
        )
        return

    title = context.args[0]
    description = " ".join(context.args[1:]) if len(context.args) > 1 else None

    try:
        wo = cmms.create_work_order(
            title=title,
            description=description,
            priority="MEDIUM"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Complete", callback_data=f"wo_complete_{wo.get('id')}"),
                InlineKeyboardButton("📋 Details", callback_data=f"wo_details_{wo.get('id')}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ *Work Order Created!*\n\n"
            f"ID: #{wo.get('id')}\n"
            f"Title: {wo.get('title')}\n"
            f"Status: {wo.get('status')}\n"
            f"Priority: {wo.get('priority')}",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def list_work_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List open work orders"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)

    if not session["authenticated"]:
        await update.message.reply_text("Please /login first")
        return

    try:
        result = cmms.get_work_orders(status="OPEN", size=10)
        work_orders = result.get("content", [])

        if not work_orders:
            await update.message.reply_text("No open work orders.")
            return

        message = "🔧 *Open Work Orders:*\n\n"
        for wo in work_orders:
            message += (
                f"*#{wo.get('id')} - {wo.get('title')}*\n"
                f"Priority: {wo.get('priority')}\n"
                f"Status: {wo.get('status')}\n"
                f"Due: {wo.get('dueDate', 'Not set')}\n\n"
            )

        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    session = get_user_session(user_id)

    if not session["authenticated"]:
        await query.edit_message_text("Please /login first")
        return

    data = query.data

    if data == "menu_assets":
        await query.edit_message_text(
            "📦 *Assets Menu*\n\n"
            "/assets - List all assets\n"
            "/asset <search> - Search assets\n"
            "/newasset - Create new asset",
            parse_mode="Markdown"
        )

    elif data == "menu_workorders":
        await query.edit_message_text(
            "🔧 *Work Orders Menu*\n\n"
            "/workorders - List open work orders\n"
            "/wo <title> - Create new work order\n"
            "/closewo <id> - Complete work order",
            parse_mode="Markdown"
        )

    elif data == "menu_pm":
        await query.edit_message_text(
            "📅 *Preventive Maintenance Menu*\n\n"
            "/pmlist - List PM schedules\n"
            "/newpm - Create PM schedule",
            parse_mode="Markdown"
        )

    elif data == "menu_parts":
        await query.edit_message_text(
            "🔩 *Parts & Inventory Menu*\n\n"
            "/parts - List all parts\n"
            "/part <search> - Search parts\n"
            "/newpart - Add new part",
            parse_mode="Markdown"
        )

    elif data.startswith("wo_complete_"):
        wo_id = int(data.split("_")[2])
        try:
            wo = cmms.complete_work_order(wo_id, feedback="Completed via Telegram bot")
            await query.edit_message_text(
                f"✅ Work Order #{wo_id} completed successfully!"
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")

    elif data.startswith("wo_details_"):
        wo_id = int(data.split("_")[2])
        try:
            wo = cmms.get_work_order(wo_id)
            details = (
                f"🔧 *Work Order #{wo.get('id')}*\n\n"
                f"Title: {wo.get('title')}\n"
                f"Description: {wo.get('description', 'N/A')}\n"
                f"Status: {wo.get('status')}\n"
                f"Priority: {wo.get('priority')}\n"
                f"Created: {wo.get('createdAt', 'N/A')}"
            )
            await query.edit_message_text(details, parse_mode="Markdown")
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")


def main():
    """Start the bot"""
    # Get bot token from environment
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set")
        return

    # Build application
    app = ApplicationBuilder().token(bot_token).build()

    # Conversation handler for asset creation
    asset_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("newasset", create_asset_start)],
        states={
            AWAITING_ASSET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_asset_name)],
            AWAITING_WO_DESCRIPTION: [MessageHandler(filters.TEXT, create_asset_finish)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("assets", search_assets))
    app.add_handler(CommandHandler("asset", search_assets))
    app.add_handler(CommandHandler("workorders", list_work_orders))
    app.add_handler(CommandHandler("wo", create_work_order))
    app.add_handler(asset_conv_handler)
    app.add_handler(CallbackQueryHandler(button_callback))

    # Start bot
    print("🤖 Rivet-PRO CMMS Telegram Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
