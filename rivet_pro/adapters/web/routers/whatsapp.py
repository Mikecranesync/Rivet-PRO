"""
WhatsApp Cloud API Webhook Router

Handles incoming webhooks from Meta's WhatsApp Cloud API:
- GET: Webhook verification (hub.mode, hub.verify_token, hub.challenge)
- POST: Incoming messages with HMAC-SHA256 signature verification

Required Configuration:
- WHATSAPP_VERIFY_TOKEN: Custom token for webhook URL verification
- WHATSAPP_APP_SECRET: App Secret for signature verification

Usage:
    Router is mounted at /whatsapp in the main FastAPI app.
    Configure webhook URL in Meta Developer Portal as: https://yourdomain.com/whatsapp
"""

import hashlib
import hmac
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse

from rivet_pro.config.settings import settings
from rivet_pro.infra.observability import get_logger
from rivet_pro.adapters.whatsapp.client import mark_as_read

logger = get_logger(__name__)

router = APIRouter()


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify HMAC-SHA256 signature from WhatsApp webhook.

    This is a pure function for easy testing.

    Args:
        payload: Raw request body bytes
        signature: X-Hub-Signature-256 header value (format: "sha256=<hash>")
        secret: App Secret from Meta Developer Portal

    Returns:
        bool: True if signature is valid, False otherwise

    Example:
        is_valid = verify_webhook_signature(
            b'{"entry":[...]}',
            "sha256=abc123...",
            "my_app_secret"
        )
    """
    if not signature or not signature.startswith("sha256="):
        return False

    expected_signature = signature[7:]  # Remove "sha256=" prefix

    computed_hash = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed_hash, expected_signature)


@router.get("")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge")
) -> PlainTextResponse:
    """
    Handle Meta webhook verification request.

    Meta sends a GET request with:
    - hub.mode: Should be "subscribe"
    - hub.verify_token: Must match our WHATSAPP_VERIFY_TOKEN
    - hub.challenge: Echo back to confirm verification

    Returns:
        200 with challenge if valid
        403 if token doesn't match
    """
    logger.info(f"WhatsApp webhook verification | mode={hub_mode}")

    if not settings.whatsapp_verify_token:
        logger.warning("WhatsApp verify token not configured")
        raise HTTPException(status_code=403, detail="Webhook not configured")

    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        logger.info("WhatsApp webhook verified successfully")
        return PlainTextResponse(content=hub_challenge or "", status_code=200)

    logger.warning(f"WhatsApp webhook verification failed | mode={hub_mode} | token_match={hub_verify_token == settings.whatsapp_verify_token}")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("")
async def receive_webhook(request: Request):
    """
    Handle incoming WhatsApp messages.

    Validates HMAC-SHA256 signature and processes:
    - Text messages
    - Image messages

    Returns:
        200 on success (required by Meta to acknowledge receipt)
        401 if signature verification fails
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature if app secret is configured
    if settings.whatsapp_app_secret:
        signature = request.headers.get("X-Hub-Signature-256", "")

        if not verify_webhook_signature(body, signature, settings.whatsapp_app_secret):
            logger.warning("WhatsApp webhook signature verification failed")
            raise HTTPException(status_code=401, detail="Invalid signature")
    else:
        logger.warning("WhatsApp app secret not configured - skipping signature verification")

    # Parse JSON payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse WhatsApp webhook payload | error={e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Process webhook entries
    entries = payload.get("entry", [])

    for entry in entries:
        changes = entry.get("changes", [])

        for change in changes:
            value = change.get("value", {})
            messages = value.get("messages", [])

            for message in messages:
                await process_message(message, value)

    # Always return 200 to acknowledge receipt
    return {"status": "ok"}


async def process_message(message: dict, value: dict):
    """
    Process a single incoming WhatsApp message.

    Handles text and image message types.
    Logs message details without exposing sensitive content.

    Args:
        message: Message object from webhook payload
        value: Parent value object containing metadata
    """
    message_id = message.get("id", "unknown")
    from_number = message.get("from", "unknown")
    message_type = message.get("type", "unknown")
    timestamp = message.get("timestamp", "unknown")

    # Get sender profile info if available
    contacts = value.get("contacts", [])
    sender_name = contacts[0].get("profile", {}).get("name", "Unknown") if contacts else "Unknown"

    logger.info(
        f"WhatsApp message received | "
        f"type={message_type} | "
        f"from={from_number[:6]}*** | "
        f"sender={sender_name} | "
        f"message_id={message_id[:20]}..."
    )

    # Mark message as read (send blue checkmarks)
    await mark_as_read(message_id)

    if message_type == "text":
        text_body = message.get("text", {}).get("body", "")
        logger.info(f"WhatsApp text message | from={from_number[:6]}*** | length={len(text_body)}")

        # TODO: Route to conversation handler
        # This is where you'd integrate with your business logic
        # Example: await handle_text_message(from_number, text_body, message_id)

    elif message_type == "image":
        image = message.get("image", {})
        image_id = image.get("id", "unknown")
        caption = image.get("caption", "")
        mime_type = image.get("mime_type", "unknown")

        logger.info(
            f"WhatsApp image message | "
            f"from={from_number[:6]}*** | "
            f"mime={mime_type} | "
            f"has_caption={bool(caption)}"
        )

        # TODO: Route to image handler
        # This is where you'd download the image and process it
        # Example: await handle_image_message(from_number, image_id, caption, message_id)

    elif message_type == "audio":
        audio = message.get("audio", {})
        audio_id = audio.get("id", "unknown")
        mime_type = audio.get("mime_type", "unknown")

        logger.info(
            f"WhatsApp audio message | "
            f"from={from_number[:6]}*** | "
            f"mime={mime_type}"
        )

        # TODO: Route to audio handler (voice messages)

    elif message_type == "document":
        document = message.get("document", {})
        doc_id = document.get("id", "unknown")
        filename = document.get("filename", "unknown")
        mime_type = document.get("mime_type", "unknown")

        logger.info(
            f"WhatsApp document message | "
            f"from={from_number[:6]}*** | "
            f"filename={filename} | "
            f"mime={mime_type}"
        )

        # TODO: Route to document handler

    else:
        logger.info(f"WhatsApp unsupported message type | type={message_type} | from={from_number[:6]}***")
