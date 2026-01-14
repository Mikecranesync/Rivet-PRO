"""
Usage tracking service for freemium enforcement.
Tracks equipment lookups per user and enforces limits.
"""

from typing import Optional
from uuid import UUID
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)

FREE_TIER_LIMIT = 10


class UsageService:
    """Tracks and enforces usage limits for freemium model."""

    def __init__(self, db):
        self.db = db

    async def get_usage_count(self, telegram_user_id: int) -> int:
        """
        Get total lookup count for a Telegram user.
        
        Args:
            telegram_user_id: Telegram user ID
            
        Returns:
            Total number of lookups for this user
        """
        count = await self.db.fetchval(
            "SELECT COUNT(*) FROM usage_tracking WHERE telegram_user_id = $1",
            telegram_user_id
        )
        return count or 0

    async def record_lookup(
        self,
        telegram_user_id: int,
        equipment_id: Optional[UUID] = None,
        lookup_type: str = "photo_ocr"
    ) -> int:
        """
        Record a lookup and return new usage count.
        
        Args:
            telegram_user_id: Telegram user ID
            equipment_id: Optional equipment ID if one was matched/created
            lookup_type: Type of lookup (photo_ocr, manual_search, api_call)
            
        Returns:
            Updated usage count after this lookup
        """
        await self.db.execute(
            """
            INSERT INTO usage_tracking (telegram_user_id, equipment_id, lookup_type)
            VALUES ($1, $2, $3)
            """,
            telegram_user_id,
            equipment_id,
            lookup_type
        )
        
        new_count = await self.get_usage_count(telegram_user_id)
        logger.info(f"Recorded lookup | user={telegram_user_id} | count={new_count}")
        return new_count

    async def check_limit(self, telegram_user_id: int) -> tuple[bool, int]:
        """
        Check if user has exceeded free tier limit.
        
        Args:
            telegram_user_id: Telegram user ID
            
        Returns:
            Tuple of (can_proceed, current_count)
            - can_proceed: True if under limit (count < 10)
            - current_count: Current usage count
        """
        count = await self.get_usage_count(telegram_user_id)
        can_proceed = count < FREE_TIER_LIMIT
        return can_proceed, count

    async def is_pro_user(self, telegram_user_id: int) -> bool:
        """
        Check if user has Pro subscription.
        
        Args:
            telegram_user_id: Telegram user ID
            
        Returns:
            True if user has active Pro subscription
        """
        user = await self.db.fetchrow(
            "SELECT subscription_tier FROM users WHERE telegram_id = $1",
            telegram_user_id
        )
        if user and user.get('subscription_tier') in ('pro', 'team'):
            return True
        return False

    async def can_use_service(self, telegram_user_id: int) -> tuple[bool, int, str]:
        """
        Full check: can this user make a lookup?
        
        Args:
            telegram_user_id: Telegram user ID
            
        Returns:
            Tuple of (allowed, current_count, reason)
            - allowed: True if user can proceed
            - current_count: Current usage count
            - reason: 'pro', 'under_limit', or 'limit_exceeded'
        """
        if await self.is_pro_user(telegram_user_id):
            count = await self.get_usage_count(telegram_user_id)
            return True, count, 'pro'
        
        can_proceed, count = await self.check_limit(telegram_user_id)
        if can_proceed:
            return True, count, 'under_limit'
        
        return False, count, 'limit_exceeded'
