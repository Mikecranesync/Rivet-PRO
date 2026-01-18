"""
WhatsApp Cloud API Client

Provides functions for sending messages via WhatsApp Cloud API.
Uses Meta's Cloud API (graph.facebook.com) for message delivery.

Required Configuration:
- WHATSAPP_PHONE_NUMBER_ID: Phone Number ID from Meta Developer Portal
- WHATSAPP_ACCESS_TOKEN: System User access token for API calls

Usage:
    from rivet_pro.adapters.whatsapp.client import send_whatsapp_text, send_whatsapp_image

    await send_whatsapp_text(to_whatsapp_id="1234567890", body="Hello!")
    await send_whatsapp_image(to_whatsapp_id="1234567890", image_url="https://...", caption="Equipment photo")
"""

import httpx
from typing import Optional

from rivet_pro.config.settings import settings
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)

# WhatsApp Cloud API base URL
WHATSAPP_API_BASE = "https://graph.facebook.com/v18.0"


async def send_whatsapp_text(to_whatsapp_id: str, body: str) -> bool:
    """
    Send a text message via WhatsApp Cloud API.

    Args:
        to_whatsapp_id: Recipient's WhatsApp ID (phone number without + or spaces)
        body: Message text content

    Returns:
        bool: True if message was sent successfully, False otherwise

    Example:
        await send_whatsapp_text("15551234567", "Hello from RIVET!")
    """
    if not settings.whatsapp_phone_number_id or not settings.whatsapp_access_token:
        logger.warning("WhatsApp adapter not configured - message not sent")
        return False

    url = f"{WHATSAPP_API_BASE}/{settings.whatsapp_phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_whatsapp_id,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": body
        }
    }

    logger.info(f"Sending WhatsApp text | to={to_whatsapp_id} | body_length={len(body)}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)

            if response.status_code == 200:
                data = response.json()
                message_id = data.get("messages", [{}])[0].get("id", "unknown")
                logger.info(f"WhatsApp text sent | to={to_whatsapp_id} | message_id={message_id}")
                return True
            else:
                logger.error(
                    f"WhatsApp send failed | to={to_whatsapp_id} | "
                    f"status={response.status_code} | error={response.text}"
                )
                return False

    except Exception as e:
        logger.error(f"WhatsApp send error | to={to_whatsapp_id} | error={e}", exc_info=True)
        return False


async def send_whatsapp_image(
    to_whatsapp_id: str,
    image_url: str,
    caption: Optional[str] = None
) -> bool:
    """
    Send an image message via WhatsApp Cloud API.

    Args:
        to_whatsapp_id: Recipient's WhatsApp ID (phone number without + or spaces)
        image_url: Public URL to the image (must be HTTPS and accessible)
        caption: Optional caption text for the image

    Returns:
        bool: True if message was sent successfully, False otherwise

    Example:
        await send_whatsapp_image("15551234567", "https://example.com/photo.jpg", "Motor nameplate")
    """
    if not settings.whatsapp_phone_number_id or not settings.whatsapp_access_token:
        logger.warning("WhatsApp adapter not configured - image not sent")
        return False

    url = f"{WHATSAPP_API_BASE}/{settings.whatsapp_phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json"
    }

    image_obj = {"link": image_url}
    if caption:
        image_obj["caption"] = caption

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_whatsapp_id,
        "type": "image",
        "image": image_obj
    }

    logger.info(f"Sending WhatsApp image | to={to_whatsapp_id} | has_caption={caption is not None}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)

            if response.status_code == 200:
                data = response.json()
                message_id = data.get("messages", [{}])[0].get("id", "unknown")
                logger.info(f"WhatsApp image sent | to={to_whatsapp_id} | message_id={message_id}")
                return True
            else:
                logger.error(
                    f"WhatsApp image send failed | to={to_whatsapp_id} | "
                    f"status={response.status_code} | error={response.text}"
                )
                return False

    except Exception as e:
        logger.error(f"WhatsApp image send error | to={to_whatsapp_id} | error={e}", exc_info=True)
        return False


async def mark_as_read(message_id: str) -> bool:
    """
    Mark a received message as read in WhatsApp.

    This sends a read receipt to the sender, showing blue checkmarks.
    Should be called after processing an incoming message.

    Args:
        message_id: WhatsApp message ID (from webhook payload)

    Returns:
        bool: True if marked successfully, False otherwise

    Example:
        await mark_as_read("wamid.HBgLMTU1NTEyMzQ1NjcVAgARGBI3QjY4...")
    """
    if not settings.whatsapp_phone_number_id or not settings.whatsapp_access_token:
        logger.warning("WhatsApp adapter not configured - cannot mark as read")
        return False

    url = f"{WHATSAPP_API_BASE}/{settings.whatsapp_phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id
    }

    logger.info(f"Marking WhatsApp message as read | message_id={message_id[:20]}...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)

            if response.status_code == 200:
                logger.debug(f"WhatsApp message marked as read | message_id={message_id[:20]}...")
                return True
            else:
                logger.warning(
                    f"WhatsApp mark read failed | message_id={message_id[:20]}... | "
                    f"status={response.status_code}"
                )
                return False

    except Exception as e:
        logger.warning(f"WhatsApp mark read error | error={e}")
        return False
