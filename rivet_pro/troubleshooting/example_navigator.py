"""
Example integration of TreeNavigator with RIVET Pro Telegram bot

This example demonstrates how to use TreeNavigator with a troubleshooting tree
for equipment diagnostics with in-place message editing.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from rivet_pro.troubleshooting import TreeNavigator, encode_callback, decode_callback


class SimpleEquipmentTree:
    """
    Simplified troubleshooting tree for demonstration.

    In production, load from database or TroubleshootingTree class.
    """

    def __init__(self):
        self.nodes = {
            "start": {
                "text": "🔧 <b>Equipment Troubleshooting</b>\n\nWhat seems to be the problem?",
                "children": ["not_starting", "overheating", "strange_noise"]
            },
            "not_starting": {
                "text": "⚡ <b>Equipment Won't Start</b>\n\nLet's check the basics first.",
                "children": ["check_power", "check_fuel"]
            },
            "overheating": {
                "text": "🌡️ <b>Equipment Overheating</b>\n\nOverheating can be dangerous.",
                "children": ["check_coolant", "check_airflow"]
            },
            "strange_noise": {
                "text": "🔊 <b>Strange Noises</b>\n\nWhat kind of noise?",
                "children": ["grinding_noise", "squealing_noise"]
            },
            "check_power": {
                "text": "🔌 <b>Power Check</b>\n\nIs the equipment connected to power?",
                "children": ["power_yes", "power_no"]
            },
            "power_yes": {
                "text": "✅ Power OK. Let's check fuel next.",
                "children": ["check_fuel"]
            },
            "power_no": {
                "text": "⚠️ <b>No Power</b>\n\n<b>Solution:</b>\n• Connect equipment to power\n• Check circuit breaker\n• Verify power cable",
                "children": []
            },
            "check_fuel": {
                "text": "⛽ <b>Fuel Check</b>\n\nIs there fuel in the tank?",
                "children": ["fuel_yes", "fuel_no"]
            },
            "fuel_yes": {
                "text": "❌ <b>Issue Not Resolved</b>\n\nContact maintenance for inspection.",
                "children": []
            },
            "fuel_no": {
                "text": "⚠️ <b>No Fuel</b>\n\n<b>Solution:</b>\n• Refuel the equipment\n• Check for fuel leaks",
                "children": []
            },
            "check_coolant": {
                "text": "💧 <b>Coolant Check</b>\n\nIs the coolant level adequate?",
                "children": ["coolant_ok", "coolant_low"]
            },
            "coolant_ok": {
                "text": "✅ Coolant OK. Let's check airflow.",
                "children": ["check_airflow"]
            },
            "coolant_low": {
                "text": "⚠️ <b>Low Coolant</b>\n\n<b>Solution:</b>\n• Add coolant\n• Check for leaks\n\nIMPORTANT: Let equipment cool first!",
                "children": []
            },
            "check_airflow": {
                "text": "🌬️ <b>Airflow Check</b>\n\nAre cooling vents clear?",
                "children": ["airflow_ok", "airflow_blocked"]
            },
            "airflow_ok": {
                "text": "❌ <b>Issue Persists</b>\n\nContact maintenance.",
                "children": []
            },
            "airflow_blocked": {
                "text": "⚠️ <b>Blocked Airflow</b>\n\n<b>Solution:</b>\n• Clean cooling vents\n• Remove debris",
                "children": []
            },
            "grinding_noise": {
                "text": "⚠️ <b>Grinding Noise</b>\n\nWARNING: Stop equipment immediately!\n\nContact maintenance urgently.",
                "children": []
            },
            "squealing_noise": {
                "text": "⚠️ <b>Squealing Noise</b>\n\n<b>Likely Causes:</b>\n• Belt slippage\n• Worn bearings\n\nContact maintenance.",
                "children": []
            }
        }

    def get_node(self, node_id):
        """Get node data by ID."""
        return self.nodes.get(node_id)

    def render_node(self, node_id):
        """Render node as formatted text."""
        node = self.nodes.get(node_id)
        if not node:
            return f"❌ Node '{node_id}' not found"
        return node["text"]

    def get_node_keyboard(self, node_id):
        """Generate inline keyboard for node."""
        node = self.nodes.get(node_id)
        if not node:
            return None

        buttons = []

        # Add child buttons
        if node["children"]:
            for child_id in node["children"]:
                child = self.nodes.get(child_id)
                if child:
                    # Extract title from text
                    title = child["text"].split("\n")[0].split("<b>")[-1].split("</b>")[0].strip()

                    if child_id.endswith("_yes"):
                        buttons.append([
                            InlineKeyboardButton("✅ Yes", callback_data=encode_callback("nav", child_id))
                        ])
                    elif child_id.endswith("_no"):
                        buttons.append([
                            InlineKeyboardButton("❌ No", callback_data=encode_callback("nav", child_id))
                        ])
                    else:
                        buttons.append([
                            InlineKeyboardButton(title[:40], callback_data=encode_callback("nav", child_id))
                        ])

        # Add back/cancel buttons for non-root nodes
        if node_id != "start":
            buttons.append([
                InlineKeyboardButton("🏠 Start Over", callback_data=encode_callback("nav", "start")),
                InlineKeyboardButton("❌ Cancel", callback_data=encode_callback("cancel", ""))
            ])

        return InlineKeyboardMarkup(buttons) if buttons else None


# Initialize tree and navigator (single instances for the bot)
tree = SimpleEquipmentTree()
navigator = TreeNavigator()


async def troubleshoot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Start troubleshooting session.

    Usage: /troubleshoot

    This sends the initial message which will be edited during navigation.
    """
    await navigator.show_node(update, context, tree, "start")


async def handle_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle navigation button callbacks.

    This is where the magic happens - navigator edits the message in-place
    instead of sending new messages.
    """
    query = update.callback_query
    await query.answer()

    # Decode callback
    callback_type, data = decode_callback(query.data)

    if callback_type == "nav":
        # Navigate to node - THIS EDITS THE MESSAGE IN-PLACE
        node_id = data
        await navigator.navigate_to(update, context, tree, node_id)

    elif callback_type == "cancel":
        # Cancel troubleshooting
        await query.edit_message_text(
            "❌ <b>Troubleshooting Cancelled</b>\n\n"
            "Use /troubleshoot to start again.",
            parse_mode="HTML"
        )
        navigator.clear_session(update)


async def end_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    End troubleshooting session.

    Usage: /end
    """
    navigator.clear_session(update)
    await update.message.reply_text(
        "✅ Troubleshooting session ended.\n\n"
        "Use /troubleshoot to start again."
    )


async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show debug info about current session.

    Usage: /debug
    """
    info = navigator.get_session_info(update)

    debug_text = (
        "🔍 <b>Debug Info</b>\n\n"
        f"Session Key: <code>{info['session_key']}</code>\n"
        f"Tracked Message ID: <code>{info['tracked_message_id']}</code>\n"
        f"Current Node: <code>{info['current_node']}</code>\n"
        f"Total Active Sessions: <code>{info['total_sessions']}</code>"
    )

    await update.message.reply_text(debug_text, parse_mode="HTML")


def main():
    """
    Run the example bot.

    Set TELEGRAM_BOT_TOKEN environment variable before running.
    """
    import os

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not set")
        print("Usage: export TELEGRAM_BOT_TOKEN='your_token_here'")
        return

    # Build application
    app = Application.builder().token(token).build()

    # Add handlers
    app.add_handler(CommandHandler("troubleshoot", troubleshoot_command))
    app.add_handler(CommandHandler("end", end_command))
    app.add_handler(CommandHandler("debug", debug_command))
    app.add_handler(CallbackQueryHandler(handle_navigation))

    # Run bot
    print("🤖 TreeNavigator Example Bot Started")
    print("\nAvailable commands:")
    print("  /troubleshoot - Start troubleshooting")
    print("  /end - End session")
    print("  /debug - Show session debug info")
    print("\nPress Ctrl+C to stop\n")

    app.run_polling()


if __name__ == "__main__":
    main()
