"""
Adaptive Command Service for Always-On Intelligent Assistant

Learns user command preferences and dynamically updates the slash command menu.
Commands used more frequently appear higher in the menu.

Usage:
    service = AdaptiveCommandService(db)
    await service.record_usage(user_id, IntentType.EQUIPMENT_SEARCH)
    commands = await service.get_user_commands(user_id)
"""

import logging
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

from rivet_pro.core.intelligence.intent_classifier import IntentType

logger = logging.getLogger(__name__)


@dataclass
class UserCommand:
    """A command for the user's personalized menu."""
    intent_type: str
    slash_command: str
    display_name: str
    description: str
    usage_count: int = 0
    is_pinned: bool = False
    is_hidden: bool = False
    priority: int = 50


@dataclass
class IntentMapping:
    """Mapping from intent to slash command."""
    intent_type: str
    slash_command: str
    display_name: str
    description: str
    example_phrases: List[str]
    priority: int


class AdaptiveCommandService:
    """
    Service for learning and adapting user command preferences.

    Features:
    - Track which intents each user uses most
    - Generate personalized slash command menus
    - Allow pinning/hiding commands
    - Reset to default on /reset
    """

    # Default command menu (when no user preferences exist)
    DEFAULT_COMMANDS: List[UserCommand] = [
        UserCommand(
            intent_type="EQUIPMENT_SEARCH",
            slash_command="/equip search",
            display_name="Search Equipment",
            description="Find equipment by name or model",
            priority=10
        ),
        UserCommand(
            intent_type="WORK_ORDER_CREATE",
            slash_command="/wo create",
            display_name="Create Work Order",
            description="Create a new work order",
            priority=30
        ),
        UserCommand(
            intent_type="MANUAL_QUESTION",
            slash_command="/ask",
            display_name="Ask Manual",
            description="Questions about manuals",
            priority=50
        ),
        UserCommand(
            intent_type="TROUBLESHOOT",
            slash_command="/help",
            display_name="Troubleshoot",
            description="Get help with equipment issues",
            priority=60
        ),
        UserCommand(
            intent_type="WORK_ORDER_STATUS",
            slash_command="/wo list",
            display_name="Work Orders",
            description="View work order status",
            priority=40
        ),
    ]

    def __init__(self, db):
        """
        Initialize service.

        Args:
            db: Database instance with execute/execute_query_async methods
        """
        self.db = db
        logger.info("AdaptiveCommandService initialized")

    async def record_usage(self, user_id: str, intent: IntentType) -> None:
        """
        Record that a user triggered an intent.

        Increments usage count or creates new preference record.

        Args:
            user_id: User identifier (telegram_id as string)
            intent: The intent that was triggered
        """
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid user_id for recording: {user_id}")
            return

        intent_type = intent.value if isinstance(intent, IntentType) else str(intent)

        try:
            # Upsert: increment if exists, create if not
            await self.db.execute(
                """
                INSERT INTO user_command_preferences (user_id, intent_type, usage_count, last_used_at, first_used_at)
                VALUES ($1, $2, 1, NOW(), NOW())
                ON CONFLICT (user_id, intent_type) DO UPDATE SET
                    usage_count = user_command_preferences.usage_count + 1,
                    last_used_at = NOW(),
                    updated_at = NOW()
                """,
                user_id_int,
                intent_type
            )

            logger.debug(f"Recorded usage | user={user_id} | intent={intent_type}")

        except Exception as e:
            logger.error(f"Failed to record usage: {e}")
            # Don't raise - usage tracking is non-critical

    async def get_user_commands(
        self,
        user_id: str,
        limit: int = 7
    ) -> List[UserCommand]:
        """
        Get personalized command list for user.

        Returns commands sorted by:
        1. Pinned commands first
        2. Then by usage_count (most used first)
        3. Then by default priority

        Args:
            user_id: User identifier
            limit: Maximum commands to return

        Returns:
            List of UserCommand sorted by preference
        """
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid user_id: {user_id}")
            return self.DEFAULT_COMMANDS[:limit]

        try:
            # Get user preferences joined with mappings
            rows = await self.db.execute_query_async(
                """
                SELECT
                    COALESCE(p.intent_type, m.intent_type) as intent_type,
                    m.slash_command,
                    m.display_name,
                    m.description,
                    COALESCE(p.usage_count, 0) as usage_count,
                    COALESCE(p.is_pinned, FALSE) as is_pinned,
                    COALESCE(p.is_hidden, FALSE) as is_hidden,
                    m.priority as default_priority
                FROM intent_command_mapping m
                LEFT JOIN user_command_preferences p
                    ON m.intent_type = p.intent_type AND p.user_id = $1
                WHERE m.is_active = TRUE
                  AND COALESCE(p.is_hidden, FALSE) = FALSE
                ORDER BY
                    COALESCE(p.is_pinned, FALSE) DESC,
                    COALESCE(p.usage_count, 0) DESC,
                    m.priority ASC
                LIMIT $2
                """,
                (user_id_int, limit)
            )

            if not rows:
                logger.debug(f"No preferences found for user {user_id}, using defaults")
                return self.DEFAULT_COMMANDS[:limit]

            commands = [
                UserCommand(
                    intent_type=row['intent_type'],
                    slash_command=row['slash_command'],
                    display_name=row['display_name'],
                    description=row['description'],
                    usage_count=row['usage_count'],
                    is_pinned=row['is_pinned'],
                    is_hidden=row['is_hidden'],
                    priority=row['default_priority']
                )
                for row in rows
            ]

            return commands

        except Exception as e:
            logger.error(f"Failed to get user commands: {e}")
            return self.DEFAULT_COMMANDS[:limit]

    async def reset_to_default(self, user_id: str) -> bool:
        """
        Reset user's command preferences to default.

        Args:
            user_id: User identifier

        Returns:
            True if reset successful
        """
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            return False

        try:
            await self.db.execute(
                "DELETE FROM user_command_preferences WHERE user_id = $1",
                user_id_int
            )

            logger.info(f"Reset adaptive commands | user={user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to reset preferences: {e}")
            return False

    async def pin_command(self, user_id: str, intent_type: str) -> bool:
        """
        Pin a command to always appear at top of user's menu.

        Args:
            user_id: User identifier
            intent_type: Intent to pin

        Returns:
            True if successful
        """
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            return False

        try:
            await self.db.execute(
                """
                INSERT INTO user_command_preferences (user_id, intent_type, is_pinned)
                VALUES ($1, $2, TRUE)
                ON CONFLICT (user_id, intent_type) DO UPDATE SET
                    is_pinned = TRUE,
                    updated_at = NOW()
                """,
                user_id_int,
                intent_type
            )
            return True

        except Exception as e:
            logger.error(f"Failed to pin command: {e}")
            return False

    async def unpin_command(self, user_id: str, intent_type: str) -> bool:
        """Unpin a command."""
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            return False

        try:
            await self.db.execute(
                """
                UPDATE user_command_preferences
                SET is_pinned = FALSE, updated_at = NOW()
                WHERE user_id = $1 AND intent_type = $2
                """,
                user_id_int,
                intent_type
            )
            return True

        except Exception as e:
            logger.error(f"Failed to unpin command: {e}")
            return False

    async def hide_command(self, user_id: str, intent_type: str) -> bool:
        """
        Hide a command from user's menu.

        Args:
            user_id: User identifier
            intent_type: Intent to hide

        Returns:
            True if successful
        """
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            return False

        try:
            await self.db.execute(
                """
                INSERT INTO user_command_preferences (user_id, intent_type, is_hidden)
                VALUES ($1, $2, TRUE)
                ON CONFLICT (user_id, intent_type) DO UPDATE SET
                    is_hidden = TRUE,
                    updated_at = NOW()
                """,
                user_id_int,
                intent_type
            )
            return True

        except Exception as e:
            logger.error(f"Failed to hide command: {e}")
            return False

    async def unhide_command(self, user_id: str, intent_type: str) -> bool:
        """Unhide a command."""
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            return False

        try:
            await self.db.execute(
                """
                UPDATE user_command_preferences
                SET is_hidden = FALSE, updated_at = NOW()
                WHERE user_id = $1 AND intent_type = $2
                """,
                user_id_int,
                intent_type
            )
            return True

        except Exception as e:
            logger.error(f"Failed to unhide command: {e}")
            return False

    async def log_classification(
        self,
        user_id: str,
        message: str,
        intent: IntentType,
        confidence: float,
        entities: dict,
        classification_time_ms: int,
        model_used: str
    ) -> None:
        """
        Log an intent classification for ML improvement.

        Args:
            user_id: User identifier
            message: Original message
            intent: Classified intent
            confidence: Classification confidence
            entities: Extracted entities
            classification_time_ms: Time taken
            model_used: Model that did classification
        """
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            return

        try:
            import json
            await self.db.execute(
                """
                INSERT INTO intent_classification_log
                    (user_id, message_text, classified_intent, confidence, entities,
                     classification_time_ms, model_used)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                user_id_int,
                message[:1000],  # Truncate long messages
                intent.value if isinstance(intent, IntentType) else str(intent),
                confidence,
                json.dumps(entities) if entities else '{}',
                classification_time_ms,
                model_used
            )
        except Exception as e:
            logger.debug(f"Failed to log classification: {e}")
            # Non-critical, don't raise

    async def record_feedback(
        self,
        user_id: str,
        was_correct: bool,
        corrected_intent: Optional[str] = None
    ) -> None:
        """
        Record user feedback on the last classification.

        Args:
            user_id: User identifier
            was_correct: Whether classification was correct
            corrected_intent: If wrong, what was the correct intent
        """
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            return

        try:
            await self.db.execute(
                """
                UPDATE intent_classification_log
                SET was_correct = $2, corrected_intent = $3
                WHERE id = (
                    SELECT id FROM intent_classification_log
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                    LIMIT 1
                )
                """,
                user_id_int,
                was_correct,
                corrected_intent
            )
        except Exception as e:
            logger.debug(f"Failed to record feedback: {e}")

    def get_slash_command_for_intent(self, intent: IntentType) -> str:
        """
        Get the slash command string for an intent.

        Used for fallback suggestions when confidence is low.
        """
        mapping = {
            IntentType.EQUIPMENT_SEARCH: "/equip search",
            IntentType.EQUIPMENT_ADD: "/equip add",
            IntentType.WORK_ORDER_CREATE: "/wo create",
            IntentType.WORK_ORDER_STATUS: "/wo list",
            IntentType.MANUAL_QUESTION: "/ask",
            IntentType.TROUBLESHOOT: "/help",
            IntentType.GENERAL_CHAT: "/menu",
        }
        return mapping.get(intent, "/menu")


__all__ = [
    "AdaptiveCommandService",
    "UserCommand",
]
