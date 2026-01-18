"""
WhatsApp Cloud API Adapter

This module provides integration with Meta's WhatsApp Cloud API for sending
and receiving messages via WhatsApp Business Platform.

Components:
- client: API client for sending messages (text, images) and marking as read
- webhook router: FastAPI router for receiving webhooks (in adapters.web.routers.whatsapp)

Configuration:
    Required environment variables:
    - WHATSAPP_PHONE_NUMBER_ID: Phone Number ID from Meta Developer Portal
    - WHATSAPP_ACCESS_TOKEN: System User access token for API calls
    - WHATSAPP_VERIFY_TOKEN: Custom token for webhook verification
    - WHATSAPP_APP_SECRET: App Secret for webhook signature verification

    Optional:
    - WHATSAPP_BUSINESS_ACCOUNT_ID: WhatsApp Business Account ID

Usage:
    from rivet_pro.adapters.whatsapp import (
        send_whatsapp_text,
        send_whatsapp_image,
        mark_as_read
    )

    # Send a text message
    await send_whatsapp_text("15551234567", "Hello from RIVET!")

    # Send an image
    await send_whatsapp_image("15551234567", "https://example.com/image.jpg", "Caption")

    # Mark message as read (sends blue checkmarks)
    await mark_as_read("wamid.xxx")

See Also:
    - docs/WHATSAPP_SETUP.md for complete setup instructions
    - rivet_pro/adapters/web/routers/whatsapp.py for webhook handling
"""

from rivet_pro.adapters.whatsapp.client import (
    send_whatsapp_text,
    send_whatsapp_image,
    mark_as_read,
)

__all__ = [
    "send_whatsapp_text",
    "send_whatsapp_image",
    "mark_as_read",
]
