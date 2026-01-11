"""
Stripe webhook router for payment events.
"""

from fastapi import APIRouter, Request, HTTPException, Header
from rivet_pro.core.services import StripeService
from rivet_pro.infra.database import db
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature")
):
    """
    Handle Stripe webhook events.
    
    Stripe will POST events like:
    - checkout.session.completed (user subscribed)
    - customer.subscription.updated (status change)
    - customer.subscription.deleted (canceled)
    - invoice.payment_failed (payment failed)
    """
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")

    payload = await request.body()
    stripe_service = StripeService(db)

    try:
        result = await stripe_service.handle_webhook_event(payload, stripe_signature)
        return result
    except ValueError as e:
        logger.error(f"Stripe webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected webhook error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error")


@router.get("/checkout-url/{telegram_user_id}")
async def get_checkout_url(telegram_user_id: int):
    """
    Generate a Stripe Checkout URL for a user.
    Used by the Telegram bot to provide upgrade links.
    """
    stripe_service = StripeService(db)

    try:
        url = await stripe_service.create_checkout_session(telegram_user_id)
        return {"checkout_url": url}
    except Exception as e:
        logger.error(f"Failed to create checkout session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create checkout session")
