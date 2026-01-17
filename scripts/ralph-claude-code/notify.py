#!/usr/bin/env python3
"""
Send Telegram notifications for Ralph events.

Usage:
    python notify.py <event> [story_id] [details]

Events:
    start    - Ralph execution started
    complete - Story completed successfully
    blocked  - Story blocked, cannot proceed
    error    - Error encountered
    progress - Progress update

Examples:
    python notify.py start "" "Testing Ralph system"
    python notify.py complete "RIVET-006" "Redis caching implemented"
    python notify.py blocked "RIVET-007" "Missing API credentials"
    python notify.py error "RIVET-008" "Database connection failed"
"""

import asyncio
import os
import sys
from datetime import datetime


async def send_telegram(message: str):
    """Send message via Telegram Bot API."""
    try:
        import aiohttp
    except ImportError:
        print("ERROR: aiohttp not installed. Install with: pip install aiohttp")
        return

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_ADMIN_CHAT_ID', '8445149012')  # Default admin

    if not token:
        print("WARNING: TELEGRAM_BOT_TOKEN not set, skipping notification")
        print("Set in .env file: TELEGRAM_BOT_TOKEN=your_token_here")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    print(f"✓ Notification sent successfully")
                else:
                    error_text = await resp.text()
                    print(f"✗ Telegram API error (status {resp.status}): {error_text}")
    except Exception as e:
        print(f"✗ Failed to send notification: {e}")


def format_message(event: str, story_id: str = "", details: str = ""):
    """Format notification message with emojis and styling."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Event-specific emoji and title
    event_config = {
        'start': {'emoji': '🚀', 'title': 'RALPH STARTING'},
        'complete': {'emoji': '✅', 'title': 'STORY COMPLETE'},
        'blocked': {'emoji': '🚫', 'title': 'STORY BLOCKED'},
        'error': {'emoji': '❌', 'title': 'ERROR ENCOUNTERED'},
        'progress': {'emoji': '⚙️', 'title': 'PROGRESS UPDATE'}
    }

    config = event_config.get(event, {'emoji': '📌', 'title': 'RALPH UPDATE'})
    emoji = config['emoji']
    title = config['title']

    # Build message
    msg = f"{emoji} <b>{title}</b>\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"

    if story_id:
        msg += f"<b>Story:</b> <code>{story_id}</code>\n"

    if details:
        # Ensure details don't contain HTML that breaks formatting
        safe_details = details.replace('<', '&lt;').replace('>', '&gt;')
        msg += f"\n{safe_details}\n"

    msg += f"\n<i>{timestamp}</i>\n"
    msg += f"━━━━━━━━━━━━━━━━━━"

    return msg


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: notify.py <event> [story_id] [details]")
        print("\nEvents: start, complete, blocked, error, progress")
        print("\nExamples:")
        print('  notify.py start "" "Testing Ralph"')
        print('  notify.py complete "RIVET-006" "Feature complete"')
        print('  notify.py blocked "RIVET-007" "Missing credentials"')
        sys.exit(1)

    event = sys.argv[1]
    story_id = sys.argv[2] if len(sys.argv) > 2 else ""
    details = sys.argv[3] if len(sys.argv) > 3 else ""

    # Validate event
    valid_events = ['start', 'complete', 'blocked', 'error', 'progress']
    if event not in valid_events:
        print(f"ERROR: Invalid event '{event}'. Must be one of: {', '.join(valid_events)}")
        sys.exit(1)

    # Format and send
    message = format_message(event, story_id, details)

    print(f"\nSending notification:")
    print(f"Event: {event}")
    if story_id:
        print(f"Story: {story_id}")
    if details:
        print(f"Details: {details[:50]}..." if len(details) > 50 else f"Details: {details}")
    print()

    # Send asynchronously
    asyncio.run(send_telegram(message))


if __name__ == '__main__':
    main()
