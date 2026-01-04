"""
RIVET Pro - Stripe Payment Integration

Handles subscription management, webhooks, and usage tracking.

Features:
- Subscription creation and management
- Webhook event processing
- Usage-based billing
- Tier enforcement
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

try:
    import stripe
except ImportError:
    stripe = None
    logging.warning("Stripe not installed. Payment features disabled.")

from rivet.config import config, TierLimits

logger = logging.getLogger(__name__)


# ============================================================================
# STRIPE INITIALIZATION
# ============================================================================


def init_stripe() -> bool:
    """
    Initialize Stripe with API key from config.

    Returns:
        True if initialized successfully, False otherwise
    """
    if not stripe:
        logger.error("Stripe library not installed")
        return False

    if not config.stripe_secret_key:
        logger.warning("STRIPE_SECRET_KEY not set, payment features disabled")
        return False

    stripe.api_key = config.stripe_secret_key
    logger.info("Stripe initialized successfully")
    return True


# ============================================================================
# SUBSCRIPTION MANAGEMENT
# ============================================================================


async def create_subscription(
    user_id: str,
    email: str,
    tier: str = "pro",
) -> Optional[Dict[str, Any]]:
    """
    Create a new subscription for a user.

    Args:
        user_id: Internal user ID
        email: User email address
        tier: Subscription tier (pro or team)

    Returns:
        Subscription data or None if failed

    TODO: Integrate harvest block from Harvester (Round 8?)
    - Customer creation
    - Subscription setup
    - Payment method collection
    """
    if not init_stripe():
        return None

    try:
        # Get price ID from config
        price_id = (
            config.stripe_price_pro if tier == "pro" else config.stripe_price_team
        )

        if not price_id:
            logger.error(f"Price ID not configured for tier: {tier}")
            return None

        # Create or retrieve customer
        customer = stripe.Customer.create(
            email=email,
            metadata={"user_id": user_id, "tier": tier},
        )

        # Create subscription
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{"price": price_id}],
            payment_behavior="default_incomplete",
            payment_settings={"save_default_payment_method": "on_subscription"},
            expand=["latest_invoice.payment_intent"],
        )

        logger.info(
            f"Subscription created for user {user_id}",
            extra={
                "user_id": user_id,
                "tier": tier,
                "subscription_id": subscription.id,
            },
        )

        return {
            "subscription_id": subscription.id,
            "customer_id": customer.id,
            "client_secret": subscription.latest_invoice.payment_intent.client_secret,
        }

    except Exception as e:
        logger.error(f"Failed to create subscription: {e}", exc_info=True)
        return None


async def cancel_subscription(subscription_id: str) -> bool:
    """
    Cancel a subscription.

    Args:
        subscription_id: Stripe subscription ID

    Returns:
        True if cancelled successfully
    """
    if not init_stripe():
        return False

    try:
        stripe.Subscription.delete(subscription_id)
        logger.info(f"Subscription cancelled: {subscription_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to cancel subscription: {e}", exc_info=True)
        return False


async def get_subscription_status(subscription_id: str) -> Optional[str]:
    """
    Get current subscription status.

    Args:
        subscription_id: Stripe subscription ID

    Returns:
        Status string (active, past_due, canceled, etc.) or None
    """
    if not init_stripe():
        return None

    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        return subscription.status
    except Exception as e:
        logger.error(f"Failed to retrieve subscription: {e}", exc_info=True)
        return None


# ============================================================================
# WEBHOOK HANDLING
# ============================================================================


async def handle_webhook(
    payload: bytes,
    signature: str,
) -> Optional[Dict[str, Any]]:
    """
    Process Stripe webhook events.

    Args:
        payload: Raw webhook payload
        signature: Stripe signature header

    Returns:
        Event data or None if verification failed

    TODO: Integrate harvest block from Harvester (Round 8?)
    - Webhook verification
    - Event routing
    - Database updates
    """
    if not init_stripe():
        return None

    if not config.stripe_webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        return None

    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, signature, config.stripe_webhook_secret
        )

        logger.info(f"Webhook received: {event['type']}")

        # Route event to handler
        event_type = event["type"]
        event_data = event["data"]["object"]

        if event_type == "customer.subscription.created":
            await handle_subscription_created(event_data)
        elif event_type == "customer.subscription.updated":
            await handle_subscription_updated(event_data)
        elif event_type == "customer.subscription.deleted":
            await handle_subscription_deleted(event_data)
        elif event_type == "invoice.payment_succeeded":
            await handle_payment_succeeded(event_data)
        elif event_type == "invoice.payment_failed":
            await handle_payment_failed(event_data)
        else:
            logger.info(f"Unhandled webhook event: {event_type}")

        return event

    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Webhook signature verification failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}", exc_info=True)
        return None


# ============================================================================
# WEBHOOK EVENT HANDLERS
# ============================================================================


async def handle_subscription_created(subscription: Dict[str, Any]) -> None:
    """Handle subscription.created event."""
    user_id = subscription["metadata"].get("user_id")
    logger.info(f"Subscription created for user {user_id}")

    # TODO: Update user tier in database
    # TODO: Send welcome email
    # TODO: Grant access to features


async def handle_subscription_updated(subscription: Dict[str, Any]) -> None:
    """Handle subscription.updated event."""
    user_id = subscription["metadata"].get("user_id")
    status = subscription.get("status")

    logger.info(f"Subscription updated for user {user_id}: {status}")

    # TODO: Update user status in database
    # TODO: Handle tier changes
    # TODO: Send notification if needed


async def handle_subscription_deleted(subscription: Dict[str, Any]) -> None:
    """Handle subscription.deleted event."""
    user_id = subscription["metadata"].get("user_id")
    logger.info(f"Subscription deleted for user {user_id}")

    # TODO: Downgrade user to free tier
    # TODO: Send cancellation confirmation
    # TODO: Archive user data if needed


async def handle_payment_succeeded(invoice: Dict[str, Any]) -> None:
    """Handle invoice.payment_succeeded event."""
    subscription_id = invoice.get("subscription")
    amount = invoice.get("amount_paid")

    logger.info(f"Payment succeeded for subscription {subscription_id}: ${amount/100}")

    # TODO: Record payment in database
    # TODO: Send receipt
    # TODO: Update usage limits


async def handle_payment_failed(invoice: Dict[str, Any]) -> None:
    """Handle invoice.payment_failed event."""
    subscription_id = invoice.get("subscription")

    logger.warning(f"Payment failed for subscription {subscription_id}")

    # TODO: Send payment failure notification
    # TODO: Retry payment
    # TODO: Suspend account if repeated failures


# ============================================================================
# USAGE TRACKING
# ============================================================================


async def check_usage_limits(user_id: str, tier: str) -> Dict[str, Any]:
    """
    Check if user is within usage limits for their tier.

    Args:
        user_id: User ID
        tier: Subscription tier

    Returns:
        Usage status with limits and current usage

    TODO: Integrate with database
    - Query actual usage from DB
    - Check against tier limits
    - Return detailed status
    """
    limits = TierLimits.get(tier)

    # TODO: Query actual usage from database
    # Placeholder for now
    usage_today = 0

    daily_limit = limits.get("queries_per_day", 50)
    within_limit = daily_limit == -1 or usage_today < daily_limit

    return {
        "tier": tier,
        "usage_today": usage_today,
        "daily_limit": daily_limit,
        "within_limit": within_limit,
        "remaining": daily_limit - usage_today if daily_limit != -1 else -1,
    }


async def increment_usage(user_id: str, query_type: str = "query") -> bool:
    """
    Increment usage counter for user.

    Args:
        user_id: User ID
        query_type: Type of query (ocr, troubleshoot, etc.)

    Returns:
        True if incremented successfully
    """
    # TODO: Implement database increment
    # TODO: Track by query type
    # TODO: Handle daily reset

    logger.info(f"Usage increment: {user_id} - {query_type}")
    return True


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def get_tier_limits(tier: str) -> Dict[str, Any]:
    """
    Get usage limits for a subscription tier.

    Args:
        tier: Tier name (beta, pro, team)

    Returns:
        Dictionary with tier limits
    """
    return TierLimits.get(tier)


def calculate_prorated_amount(
    current_tier: str,
    new_tier: str,
    days_remaining: int,
) -> float:
    """
    Calculate prorated amount for tier change.

    Args:
        current_tier: Current subscription tier
        new_tier: New subscription tier
        days_remaining: Days remaining in billing period

    Returns:
        Prorated amount in USD
    """
    current_price = TierLimits.get(current_tier)["price"]
    new_price = TierLimits.get(new_tier)["price"]

    # Simple proration calculation
    daily_diff = (new_price - current_price) / 30
    prorated = daily_diff * days_remaining

    return max(0, prorated)


# ============================================================================
# TESTING HELPERS
# ============================================================================


def create_test_price(tier: str) -> Optional[str]:
    """
    Create a test price in Stripe (for development).

    Args:
        tier: Tier to create price for

    Returns:
        Price ID or None
    """
    if not init_stripe():
        return None

    try:
        limits = TierLimits.get(tier)
        price = stripe.Price.create(
            unit_amount=limits["price"] * 100,  # Convert to cents
            currency="usd",
            recurring={"interval": "month"},
            product_data={
                "name": f"RIVET Pro - {tier.title()}",
            },
        )
        logger.info(f"Test price created: {price.id}")
        return price.id
    except Exception as e:
        logger.error(f"Failed to create test price: {e}", exc_info=True)
        return None
