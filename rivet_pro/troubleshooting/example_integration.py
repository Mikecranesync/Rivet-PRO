"""
Example integration of troubleshooting tree drafts with Telegram bot.

This shows how to integrate the draft system into your bot handlers.
"""

import asyncio
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from rivet_pro.troubleshooting.commands import (
    save_guide_command,
    list_drafts_command,
    view_draft_command,
    approve_draft_command,
    reject_draft_command,
    handle_approve_callback,
    handle_reject_callback,
    handle_draft_steps,
)
from rivet_pro.infra.database import db
from rivet_pro.config.settings import settings


async def setup_draft_handlers(application: Application) -> None:
    """
    Add draft-related handlers to the bot application.

    Args:
        application: python-telegram-bot Application instance
    """

    # User commands
    application.add_handler(CommandHandler("save_guide", save_guide_command))

    # Admin commands
    application.add_handler(CommandHandler("drafts", list_drafts_command))
    application.add_handler(CommandHandler("view_draft", view_draft_command))
    application.add_handler(CommandHandler("approve_draft", approve_draft_command))
    application.add_handler(CommandHandler("reject_draft", reject_draft_command))

    # Callback handlers for inline buttons
    application.add_handler(CallbackQueryHandler(
        handle_approve_callback,
        pattern=r"^approve_draft_\d+$"
    ))
    application.add_handler(CallbackQueryHandler(
        handle_reject_callback,
        pattern=r"^reject_draft_\d+$"
    ))

    # Message handler for draft steps (user replies to save_guide prompt)
    # This should be added with lower priority to avoid interfering with other handlers
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_draft_steps
    ))


async def example_programmatic_usage():
    """
    Example of using the drafts module programmatically.

    This shows how to use the drafts API directly in your code
    without going through Telegram commands.
    """
    from rivet_pro.troubleshooting.drafts import (
        save_draft,
        list_drafts,
        get_draft,
        approve_draft,
        reject_draft,
        get_draft_stats,
        DraftStatus,
    )

    # Connect to database
    await db.connect()

    try:
        # Example 1: Save a draft
        print("Example 1: Saving a draft...")
        draft_id = await save_draft(
            equipment_type="Siemens S7-1200 PLC",
            problem="Communication fault with HMI",
            steps=[
                "Check Ethernet cable connection between PLC and HMI",
                "Verify IP address settings on both devices",
                "Test network connectivity with PING",
                "Check firewall settings on PC/HMI",
                "Verify PLC is in RUN mode",
                "Check for firmware compatibility issues",
            ],
            user_id=123456789,
            original_query="My HMI can't connect to the PLC"
        )
        print(f"Draft saved with ID: {draft_id}")

        # Example 2: List pending drafts
        print("\nExample 2: Listing pending drafts...")
        pending_drafts = await list_drafts(status=DraftStatus.DRAFT)
        print(f"Found {len(pending_drafts)} pending drafts")
        for draft in pending_drafts[:3]:  # Show first 3
            print(f"  - ID {draft['id']}: {draft['equipment_type']} - {draft['problem']}")

        # Example 3: Get draft details
        print(f"\nExample 3: Getting details for draft {draft_id}...")
        draft = await get_draft(draft_id)
        if draft:
            print(f"Equipment: {draft['equipment_type']}")
            print(f"Problem: {draft['problem']}")
            print(f"Steps: {len(draft['generated_steps'])}")
            print(f"Created by: {draft['creator_name']}")

        # Example 4: Approve draft
        print(f"\nExample 4: Approving draft {draft_id}...")
        tree_id = await approve_draft(draft_id, approved_by=987654321)
        if tree_id:
            print(f"Draft approved! Created tree ID: {tree_id}")

        # Example 5: Get statistics
        print("\nExample 5: Getting draft statistics...")
        stats = await get_draft_stats()
        print(f"Total drafts: {stats['total']}")
        print(f"Pending: {stats[DraftStatus.DRAFT]}")
        print(f"Approved: {stats[DraftStatus.APPROVED]}")
        print(f"Rejected: {stats[DraftStatus.REJECTED]}")

        # Example 6: List user's drafts
        print("\nExample 6: Listing drafts by user...")
        user_drafts = await list_drafts(user_id=123456789)
        print(f"User 123456789 has {len(user_drafts)} drafts")

    finally:
        # Disconnect from database
        await db.disconnect()


async def example_with_claude_integration():
    """
    Example showing how to integrate with Claude-generated guides.

    This demonstrates the complete workflow:
    1. User asks Claude for help
    2. Claude generates troubleshooting steps
    3. User saves the guide as a draft
    4. Admin reviews and approves
    5. Tree becomes available for reuse
    """
    from rivet_pro.troubleshooting.drafts import save_draft
    from rivet_pro.troubleshooting.fallback import generate_troubleshooting_guide

    # Connect to database
    await db.connect()

    try:
        # Step 1: User asks for help (simulated)
        equipment = "ABB ACS880 VFD"
        problem = "Frequent overcurrent faults"

        print(f"User asks: Help with {equipment} - {problem}")

        # Step 2: Generate guide using Claude
        print("\nGenerating troubleshooting guide with Claude...")
        guide = await generate_troubleshooting_guide(
            equipment_type=equipment,
            problem=problem,
            context={"user_id": 123456789}
        )

        print(f"Generated guide with {len(guide.steps)} steps")

        # Step 3: User saves as draft (via "Save this guide" button)
        print("\nUser clicks 'Save this guide' button...")
        draft_id = await save_draft(
            equipment_type=equipment,
            problem=problem,
            steps=[step.action for step in guide.steps],
            user_id=123456789,
            original_query=f"Help with {equipment} - {problem}"
        )

        print(f"Draft saved! ID: {draft_id}")
        print("Admin will review this draft and approve/reject it.")

        # Step 4-5: Admin reviews and approves (handled separately)
        # See approve_draft() and reject_draft() functions

    finally:
        await db.disconnect()


if __name__ == "__main__":
    """
    Run examples.

    Usage:
        python -m rivet_pro.troubleshooting.example_integration
    """
    print("=" * 60)
    print("Troubleshooting Tree Drafts - Integration Examples")
    print("=" * 60)

    # Run programmatic usage example
    print("\n--- PROGRAMMATIC USAGE EXAMPLE ---\n")
    asyncio.run(example_programmatic_usage())

    # Uncomment to run Claude integration example:
    # print("\n--- CLAUDE INTEGRATION EXAMPLE ---\n")
    # asyncio.run(example_with_claude_integration())

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)
