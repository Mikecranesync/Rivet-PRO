"""
Telegram bot commands for troubleshooting tree draft management.

Provides commands for users and admins to interact with drafts:
- /save_guide - Save current Claude response as draft
- /drafts - Admin command to list drafts
- /approve_draft <id> - Admin command to approve draft
- /reject_draft <id> <reason> - Admin command to reject draft
"""

from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from rivet_pro.troubleshooting.drafts import (
    save_draft,
    list_drafts,
    approve_draft,
    reject_draft,
    get_draft,
    get_draft_stats,
    DraftStatus
)
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)

# Admin user IDs from config
try:
    from rivet_pro.config.settings import settings
    ADMIN_USER_IDS = [settings.telegram_admin_chat_id]
except ImportError:
    import os
    ADMIN_USER_IDS = [int(os.getenv("TELEGRAM_ADMIN_CHAT_ID", "8445149012"))]


def is_admin(user_id: int) -> bool:
    """Check if user is an admin"""
    return user_id in ADMIN_USER_IDS


async def save_guide_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command: /save_guide
    Save the current conversation/guide as a troubleshooting tree draft.

    Usage:
        /save_guide <equipment_type> | <problem>
        Example: /save_guide Siemens S7-1200 PLC | Communication fault
    """
    user_id = update.effective_user.id

    try:
        # Parse command arguments
        if not context.args or len(context.args) < 3:
            await update.message.reply_text(
                "❌ Invalid format.\n\n"
                "Usage: `/save_guide <equipment_type> | <problem>`\n\n"
                "Example:\n"
                "`/save_guide Siemens S7-1200 PLC | Communication fault`",
                parse_mode="Markdown"
            )
            return

        # Join args and split by pipe
        full_text = " ".join(context.args)
        parts = [p.strip() for p in full_text.split("|")]

        if len(parts) != 2:
            await update.message.reply_text(
                "❌ Invalid format. Use pipe (|) to separate equipment type and problem.\n\n"
                "Example:\n"
                "`/save_guide Siemens S7-1200 PLC | Communication fault`",
                parse_mode="Markdown"
            )
            return

        equipment_type, problem = parts

        # Get recent messages from context (last Claude response)
        # In a real implementation, you'd track the Claude conversation
        # For now, we'll ask the user to provide steps
        await update.message.reply_text(
            f"📝 Creating draft for:\n"
            f"Equipment: {equipment_type}\n"
            f"Problem: {problem}\n\n"
            f"Please reply with the troubleshooting steps (one per line):"
        )

        # Store context for next message
        context.user_data["pending_draft"] = {
            "equipment_type": equipment_type,
            "problem": problem,
        }

    except Exception as e:
        logger.error(f"Error in save_guide_command | User: {user_id} | Error: {e}")
        await update.message.reply_text(
            "❌ Error saving guide. Please try again or contact support."
        )


async def handle_draft_steps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle user's reply with troubleshooting steps for pending draft.
    This is called when user replies to save_guide prompt.
    """
    user_id = update.effective_user.id

    try:
        # Check if user has pending draft
        pending = context.user_data.get("pending_draft")
        if not pending:
            return  # Not a draft steps reply

        # Parse steps from message (one per line)
        steps = [s.strip() for s in update.message.text.split("\n") if s.strip()]

        if not steps:
            await update.message.reply_text(
                "❌ No steps provided. Please enter at least one step."
            )
            return

        # Save draft
        draft_id = await save_draft(
            equipment_type=pending["equipment_type"],
            problem=pending["problem"],
            steps=steps,
            user_id=user_id,
            original_query=f"Equipment: {pending['equipment_type']} | Problem: {pending['problem']}"
        )

        # Clear pending draft
        del context.user_data["pending_draft"]

        # Send confirmation
        await update.message.reply_text(
            f"✅ Draft saved successfully!\n\n"
            f"📋 Draft ID: {draft_id}\n"
            f"🔧 Equipment: {pending['equipment_type']}\n"
            f"⚠️ Problem: {pending['problem']}\n"
            f"📝 Steps: {len(steps)}\n\n"
            f"An admin will review your draft soon."
        )

        logger.info(f"Draft saved via command | Draft ID: {draft_id} | User: {user_id}")

    except Exception as e:
        logger.error(f"Error handling draft steps | User: {user_id} | Error: {e}")
        await update.message.reply_text(
            "❌ Error saving draft. Please try again or contact support."
        )


async def list_drafts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command: /drafts [status]
    List troubleshooting tree drafts (admin only).

    Usage:
        /drafts         - List all pending drafts
        /drafts draft   - List pending drafts
        /drafts approved - List approved drafts
        /drafts rejected - List rejected drafts
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ This command is for admins only.")
        return

    try:
        # Parse status filter
        status = context.args[0] if context.args else DraftStatus.DRAFT

        # Validate status
        if status not in [DraftStatus.DRAFT, DraftStatus.APPROVED, DraftStatus.REJECTED]:
            await update.message.reply_text(
                f"❌ Invalid status. Use: draft, approved, or rejected"
            )
            return

        # Get drafts
        drafts = await list_drafts(status=status, limit=20)

        if not drafts:
            await update.message.reply_text(
                f"📋 No {status} drafts found."
            )
            return

        # Get stats
        stats = await get_draft_stats()

        # Format response
        status_emoji = {
            DraftStatus.DRAFT: "⏳",
            DraftStatus.APPROVED: "✅",
            DraftStatus.REJECTED: "❌"
        }

        response = f"{status_emoji[status]} *{status.upper()} DRAFTS* ({len(drafts)})\n\n"
        response += f"📊 Total: {stats['total']} | ⏳ Pending: {stats[DraftStatus.DRAFT]} | "
        response += f"✅ Approved: {stats[DraftStatus.APPROVED]} | ❌ Rejected: {stats[DraftStatus.REJECTED]}\n\n"

        for draft in drafts[:10]:  # Show first 10
            response += f"🆔 *ID {draft['id']}*\n"
            response += f"🔧 {draft['equipment_type']}\n"
            response += f"⚠️ {draft['problem']}\n"
            response += f"📝 Steps: {draft['step_count']}\n"
            response += f"👤 By: {draft['creator_name'] or 'Unknown'}\n"
            response += f"📅 {draft['created_at'].strftime('%Y-%m-%d %H:%M')}\n\n"

        if len(drafts) > 10:
            response += f"... and {len(drafts) - 10} more\n"

        await update.message.reply_text(response, parse_mode="Markdown")

        logger.info(f"Listed drafts | User: {user_id} | Status: {status} | Count: {len(drafts)}")

    except Exception as e:
        logger.error(f"Error listing drafts | User: {user_id} | Error: {e}")
        await update.message.reply_text(
            "❌ Error listing drafts. Please try again."
        )


async def view_draft_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command: /view_draft <id>
    View detailed draft information (admin only).

    Usage:
        /view_draft 42
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ This command is for admins only.")
        return

    try:
        # Parse draft ID
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text(
                "❌ Usage: `/view_draft <id>`\n"
                "Example: `/view_draft 42`",
                parse_mode="Markdown"
            )
            return

        draft_id = int(context.args[0])

        # Get draft
        draft = await get_draft(draft_id)

        if not draft:
            await update.message.reply_text(f"❌ Draft {draft_id} not found.")
            return

        # Format response
        status_emoji = {
            DraftStatus.DRAFT: "⏳",
            DraftStatus.APPROVED: "✅",
            DraftStatus.REJECTED: "❌"
        }

        response = f"📋 *DRAFT {draft['id']}* {status_emoji[draft['status']]}\n\n"
        response += f"🔧 *Equipment:* {draft['equipment_type']}\n"
        response += f"⚠️ *Problem:* {draft['problem']}\n"
        response += f"👤 *Created by:* {draft['creator_name'] or 'Unknown'}\n"
        response += f"📅 *Created:* {draft['created_at'].strftime('%Y-%m-%d %H:%M')}\n\n"

        if draft['original_query']:
            response += f"💬 *Original Query:*\n{draft['original_query']}\n\n"

        response += f"📝 *Troubleshooting Steps:*\n"
        for i, step in enumerate(draft['generated_steps'], 1):
            response += f"{i}. {step}\n"

        if draft['status'] == DraftStatus.APPROVED:
            response += f"\n✅ *Approved by:* {draft['approver_name']}\n"
            response += f"🌳 *Tree ID:* {draft['tree_id']}\n"
        elif draft['status'] == DraftStatus.REJECTED:
            response += f"\n❌ *Rejected by:* {draft['approver_name']}\n"
            response += f"📝 *Reason:* {draft['rejection_reason']}\n"

        # Add action buttons for pending drafts
        if draft['status'] == DraftStatus.DRAFT:
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_draft_{draft_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_draft_{draft_id}"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(response, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            await update.message.reply_text(response, parse_mode="Markdown")

        logger.info(f"Viewed draft | Draft ID: {draft_id} | User: {user_id}")

    except Exception as e:
        logger.error(f"Error viewing draft | User: {user_id} | Error: {e}")
        await update.message.reply_text(
            "❌ Error viewing draft. Please try again."
        )


async def approve_draft_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command: /approve_draft <id>
    Approve a draft and convert to troubleshooting tree (admin only).

    Usage:
        /approve_draft 42
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ This command is for admins only.")
        return

    try:
        # Parse draft ID
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text(
                "❌ Usage: `/approve_draft <id>`\n"
                "Example: `/approve_draft 42`",
                parse_mode="Markdown"
            )
            return

        draft_id = int(context.args[0])

        # Approve draft
        tree_id = await approve_draft(draft_id, approved_by=user_id)

        if not tree_id:
            await update.message.reply_text(
                f"❌ Failed to approve draft {draft_id}. Draft may not exist or already processed."
            )
            return

        await update.message.reply_text(
            f"✅ *Draft Approved!*\n\n"
            f"📋 Draft ID: {draft_id}\n"
            f"🌳 Tree ID: {tree_id}\n\n"
            f"The troubleshooting tree is now available for use.",
            parse_mode="Markdown"
        )

        logger.info(f"Draft approved | Draft ID: {draft_id} | Tree ID: {tree_id} | User: {user_id}")

    except ValueError as e:
        await update.message.reply_text(f"❌ {str(e)}")
    except Exception as e:
        logger.error(f"Error approving draft | User: {user_id} | Error: {e}")
        await update.message.reply_text(
            "❌ Error approving draft. Please try again."
        )


async def reject_draft_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command: /reject_draft <id> <reason>
    Reject a draft with a reason (admin only).

    Usage:
        /reject_draft 42 Steps are too generic
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ This command is for admins only.")
        return

    try:
        # Parse draft ID and reason
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "❌ Usage: `/reject_draft <id> <reason>`\n"
                "Example: `/reject_draft 42 Steps are too generic`",
                parse_mode="Markdown"
            )
            return

        draft_id = int(context.args[0])
        reason = " ".join(context.args[1:])

        # Reject draft
        success = await reject_draft(draft_id, rejected_by=user_id, reason=reason)

        if not success:
            await update.message.reply_text(
                f"❌ Failed to reject draft {draft_id}. Draft may not exist or already processed."
            )
            return

        await update.message.reply_text(
            f"❌ *Draft Rejected*\n\n"
            f"📋 Draft ID: {draft_id}\n"
            f"📝 Reason: {reason}\n\n"
            f"The creator will be notified.",
            parse_mode="Markdown"
        )

        logger.info(f"Draft rejected | Draft ID: {draft_id} | User: {user_id} | Reason: {reason}")

    except ValueError as e:
        await update.message.reply_text(f"❌ {str(e)}")
    except Exception as e:
        logger.error(f"Error rejecting draft | User: {user_id} | Error: {e}")
        await update.message.reply_text(
            "❌ Error rejecting draft. Please try again."
        )


# Callback query handlers for inline buttons
async def handle_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle approve button click from inline keyboard"""
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("❌ Admin only", show_alert=True)
        return

    try:
        # Parse draft ID from callback data
        draft_id = int(query.data.split("_")[-1])

        # Approve draft
        tree_id = await approve_draft(draft_id, approved_by=user_id)

        if not tree_id:
            await query.answer("❌ Failed to approve draft", show_alert=True)
            return

        # Update message
        await query.edit_message_text(
            f"✅ *Draft {draft_id} Approved!*\n\n"
            f"🌳 Tree ID: {tree_id}",
            parse_mode="Markdown"
        )

        await query.answer("✅ Draft approved!", show_alert=False)

        logger.info(f"Draft approved via callback | Draft ID: {draft_id} | User: {user_id}")

    except Exception as e:
        logger.error(f"Error in approve callback | User: {user_id} | Error: {e}")
        await query.answer("❌ Error approving draft", show_alert=True)


async def handle_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle reject button click from inline keyboard"""
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("❌ Admin only", show_alert=True)
        return

    # Prompt for rejection reason
    draft_id = int(query.data.split("_")[-1])

    await query.answer()
    await query.message.reply_text(
        f"📝 Please provide a rejection reason for draft {draft_id}:\n\n"
        f"Use: `/reject_draft {draft_id} <reason>`",
        parse_mode="Markdown"
    )
