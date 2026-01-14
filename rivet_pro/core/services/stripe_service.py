"""
Stripe Payment Service for Rivet Pro.
Handles checkout sessions, webhooks, and subscription management.
"""

import stripe
from typing import Optional, Tuple
from rivet_pro.config.settings import settings
from rivet_pro.infra.observability import get_logger
from rivet_pro.infra.database import Database

logger = get_logger(__name__)

RIVET_PRO_MONTHLY_PRICE = 2900  # $29.00 in cents


class StripeService:
    """Handles Stripe payment integration."""

    def __init__(self, db: Database):
        self.db = db
        if settings.stripe_api_key:
            stripe.api_key = settings.stripe_api_key
        else:
            logger.warning("Stripe API key not configured")

    async def get_or_create_customer(
        self,
        telegram_user_id: int,
        email: Optional[str] = None,
        name: Optional[str] = None
    ) -> Tuple[str, bool]:
        """
        Get existing Stripe customer or create new one.
        Returns (customer_id, is_new).
        """
        row = await self.db.fetchrow(
            "SELECT stripe_customer_id FROM users WHERE telegram_id = $1",
            telegram_user_id
        )

        if row and row['stripe_customer_id']:
            return row['stripe_customer_id'], False

        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata={"telegram_user_id": str(telegram_user_id)}
        )

        await self.db.execute(
            """
            UPDATE users 
            SET stripe_customer_id = $1 
            WHERE telegram_id = $2
            """,
            customer.id, telegram_user_id
        )

        logger.info(f"Created Stripe customer | telegram_id={telegram_user_id} | customer_id={customer.id}")
        return customer.id, True

    async def create_checkout_session(
        self,
        telegram_user_id: int,
        success_url: str = "https://rivet-cmms.com/payment/success",
        cancel_url: str = "https://rivet-cmms.com/payment/cancel"
    ) -> str:
        """
        Create a Stripe Checkout session for Pro subscription.
        Returns the checkout URL.
        """
        customer_id, _ = await self.get_or_create_customer(telegram_user_id)

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": settings.stripe_price_id,
                "quantity": 1,
            }] if settings.stripe_price_id else [{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "RIVET Pro",
                        "description": "Unlimited equipment lookups, PDF chat, work order management",
                    },
                    "unit_amount": RIVET_PRO_MONTHLY_PRICE,
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            }],
            mode="subscription",
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={"telegram_user_id": str(telegram_user_id)},
        )

        logger.info(f"Created checkout session | telegram_id={telegram_user_id} | session_id={session.id}")
        return session.url

    async def handle_webhook_event(self, payload: bytes, sig_header: str) -> dict:
        """
        Handle Stripe webhook events.
        Returns event processing result.
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {e}")
            raise ValueError("Invalid signature")

        event_type = event["type"]
        data = event["data"]["object"]

        logger.info(f"Processing Stripe webhook | type={event_type}")

        if event_type == "checkout.session.completed":
            await self._handle_checkout_completed(data)
        elif event_type == "customer.subscription.updated":
            await self._handle_subscription_updated(data)
        elif event_type == "customer.subscription.deleted":
            await self._handle_subscription_deleted(data)
        elif event_type == "invoice.payment_failed":
            await self._handle_payment_failed(data)

        return {"status": "processed", "type": event_type}

    async def _handle_checkout_completed(self, session: dict) -> None:
        """Handle successful checkout - activate Pro subscription."""
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")
        telegram_user_id = session.get("metadata", {}).get("telegram_user_id")

        await self.db.execute(
            """
            UPDATE users 
            SET subscription_status = 'active',
                subscription_tier = 'pro',
                stripe_subscription_id = $1,
                subscription_started_at = NOW()
            WHERE stripe_customer_id = $2 OR telegram_id = $3
            """,
            subscription_id, customer_id, int(telegram_user_id) if telegram_user_id else None
        )

        logger.info(f"Subscription activated | customer_id={customer_id} | subscription_id={subscription_id}")

    async def _handle_subscription_updated(self, subscription: dict) -> None:
        """Handle subscription status changes."""
        customer_id = subscription.get("customer")
        status = subscription.get("status")

        status_mapping = {
            "active": "active",
            "past_due": "past_due",
            "canceled": "canceled",
            "unpaid": "past_due",
        }
        db_status = status_mapping.get(status, "free")

        await self.db.execute(
            """
            UPDATE users 
            SET subscription_status = $1
            WHERE stripe_customer_id = $2
            """,
            db_status, customer_id
        )

        logger.info(f"Subscription updated | customer_id={customer_id} | status={db_status}")

    async def _handle_subscription_deleted(self, subscription: dict) -> None:
        """Handle subscription cancellation."""
        customer_id = subscription.get("customer")

        await self.db.execute(
            """
            UPDATE users 
            SET subscription_status = 'canceled',
                subscription_tier = 'free',
                subscription_ends_at = NOW()
            WHERE stripe_customer_id = $1
            """,
            customer_id
        )

        logger.info(f"Subscription canceled | customer_id={customer_id}")

    async def _handle_payment_failed(self, invoice: dict) -> None:
        """Handle failed payment."""
        customer_id = invoice.get("customer")

        await self.db.execute(
            """
            UPDATE users 
            SET subscription_status = 'past_due'
            WHERE stripe_customer_id = $1
            """,
            customer_id
        )

        logger.warning(f"Payment failed | customer_id={customer_id}")

    async def get_subscription_status(self, telegram_user_id: int) -> str:
        """Get current subscription status for a user."""
        row = await self.db.fetchrow(
            "SELECT subscription_status FROM users WHERE telegram_id = $1",
            telegram_user_id
        )
        return row['subscription_status'] if row else 'free'

    async def is_pro_user(self, telegram_user_id: int) -> bool:
        """Check if user has active Pro subscription."""
        status = await self.get_subscription_status(telegram_user_id)
        return status == 'active'


async def send_telegram_confirmation(telegram_user_id: int, bot) -> None:
    """Send payment confirmation message via Telegram."""
    try:
        await bot.send_message(
            chat_id=telegram_user_id,
            text=(
                "🎉 <b>Welcome to RIVET Pro!</b>\n\n"
                "Your subscription is now active. You have:\n"
                "• ✅ Unlimited equipment lookups\n"
                "• 📚 PDF manual chat\n"
                "• 🔧 Work order management\n"
                "• ⚡ Priority support\n\n"
                "Send a photo to get started!"
            ),
            parse_mode="HTML"
        )
        logger.info(f"Sent payment confirmation | telegram_id={telegram_user_id}")
    except Exception as e:
        logger.error(f"Failed to send confirmation: {e}")
