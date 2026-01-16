"""
User Feedback Service - Business Logic Layer

Handles user feedback collection, fix proposal workflows, and approval management.
Clean API that bot handlers can use without direct database manipulation.
"""

import json
import httpx
import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime

from rivet_pro.config.settings import settings

logger = logging.getLogger(__name__)


class FeedbackService:
    """Handle user feedback and fix proposal workflows."""

    def __init__(self, db_pool):
        """
        Initialize feedback service.

        Args:
            db_pool: asyncpg connection pool
        """
        self.db = db_pool
        self.feedback_webhook_url = settings.n8n_feedback_webhook_url
        self.ralph_webhook_url = settings.ralph_main_loop_url
        self.max_per_hour = settings.feedback_max_per_hour
        self.approval_timeout_hours = settings.feedback_approval_timeout_hours

    async def create_feedback(
        self,
        user_id: UUID,
        feedback_text: str,
        feedback_type: str,
        context_data: Dict[str, Any],
        telegram_user_id: str
    ) -> UUID:
        """
        Store feedback interaction in database.

        Args:
            user_id: User's UUID from users table
            feedback_text: User's description of the issue
            feedback_type: Type of feedback (manual_404, wrong_equipment, etc.)
            context_data: Extracted context (equipment_id, manual_url, etc.)
            telegram_user_id: User's Telegram ID

        Returns:
            UUID of created interaction
        """
        try:
            # Check rate limit
            if not await self._check_rate_limit(user_id):
                logger.warning(f"Rate limit exceeded | user_id={user_id}")
                raise ValueError("Rate limit exceeded. Maximum 5 feedback messages per hour.")

            # Insert feedback interaction
            row = await self.db.fetchrow(
                """
                INSERT INTO interactions (
                    id, user_id, interaction_type, feedback_text,
                    context_data, approval_status, outcome, created_at
                )
                VALUES (
                    gen_random_uuid(), $1, 'feedback', $2,
                    $3::jsonb, 'pending', 'awaiting_proposal', NOW()
                )
                RETURNING id
                """,
                user_id, feedback_text, json.dumps(context_data)
            )

            interaction_id = row['id']

            logger.info(
                f"Feedback created | interaction_id={interaction_id} | "
                f"user_id={user_id} | type={feedback_type}"
            )

            # Trigger n8n feedback workflow
            await self._trigger_feedback_workflow(
                interaction_id=interaction_id,
                telegram_user_id=telegram_user_id,
                feedback_text=feedback_text,
                feedback_type=feedback_type,
                context_data=context_data
            )

            return interaction_id

        except Exception as e:
            logger.error(f"Failed to create feedback | error={e}")
            raise

    async def _check_rate_limit(self, user_id: UUID) -> bool:
        """
        Check if user has exceeded feedback rate limit.

        Args:
            user_id: User's UUID

        Returns:
            True if within limit, False if exceeded
        """
        row = await self.db.fetchrow(
            """
            SELECT COUNT(*) as count
            FROM interactions
            WHERE user_id = $1
              AND interaction_type = 'feedback'
              AND created_at > NOW() - INTERVAL '1 hour'
            """,
            user_id
        )

        count = row['count'] if row else 0
        return count < self.max_per_hour

    async def _trigger_feedback_workflow(
        self,
        interaction_id: UUID,
        telegram_user_id: str,
        feedback_text: str,
        feedback_type: str,
        context_data: Dict[str, Any]
    ):
        """
        Trigger n8n feedback workflow via webhook.

        Args:
            interaction_id: UUID of feedback interaction
            telegram_user_id: User's Telegram ID
            feedback_text: User's feedback message
            feedback_type: Type of feedback
            context_data: Extracted context
        """
        try:
            payload = {
                'interaction_id': str(interaction_id),
                'telegram_user_id': telegram_user_id,
                'feedback_text': feedback_text,
                'feedback_type': feedback_type,
                'context': context_data
            }

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    self.feedback_webhook_url,
                    json=payload
                )

                if response.status_code == 200:
                    logger.info(f"Feedback workflow triggered | interaction_id={interaction_id}")
                else:
                    logger.error(
                        f"Feedback workflow failed | status={response.status_code} | "
                        f"response={response.text}"
                    )

        except Exception as e:
            logger.error(f"Failed to trigger feedback workflow | error={e}")

    async def get_pending_proposals(self, telegram_user_id: str) -> List[Dict[str, Any]]:
        """
        Get pending fix proposals for a user.

        Args:
            telegram_user_id: User's Telegram ID

        Returns:
            List of pending proposals
        """
        rows = await self.db.fetch(
            """
            SELECT
                i.id AS interaction_id,
                i.feedback_text,
                i.context_data,
                i.created_at,
                rs.story_id,
                rs.title,
                rs.proposal_text,
                rs.priority,
                EXTRACT(EPOCH FROM (NOW() - i.created_at))/3600 AS hours_pending
            FROM interactions i
            JOIN ralph_stories rs ON i.story_id = rs.story_id
            JOIN users u ON i.user_id = u.id
            WHERE u.telegram_user_id = $1
              AND i.approval_status = 'pending'
              AND rs.approval_status = 'pending_approval'
            ORDER BY i.created_at ASC
            """,
            telegram_user_id
        )

        return [dict(row) for row in rows]

    async def approve_proposal(
        self,
        story_id: str,
        telegram_user_id: str
    ) -> bool:
        """
        Approve fix proposal and trigger Ralph execution.

        Args:
            story_id: Ralph story ID (e.g., 'FEEDBACK-001')
            telegram_user_id: User's Telegram ID who approved

        Returns:
            True if approved successfully
        """
        try:
            # Update ralph_stories
            await self.db.execute(
                """
                UPDATE ralph_stories
                SET approval_status = 'approved',
                    approved_by_telegram_id = $1,
                    approved_at = NOW(),
                    status = 'todo'
                WHERE story_id = $2
                  AND approval_status = 'pending_approval'
                """,
                telegram_user_id, story_id
            )

            # Update linked interaction
            await self.db.execute(
                """
                UPDATE interactions
                SET approval_status = 'approved',
                    approved_at = NOW(),
                    outcome = 'proposal_approved'
                WHERE story_id = $1
                  AND approval_status = 'pending'
                """,
                story_id
            )

            logger.info(f"Proposal approved | story_id={story_id} | by={telegram_user_id}")

            # Trigger Ralph execution
            await self._trigger_ralph_execution(story_id, telegram_user_id)

            return True

        except Exception as e:
            logger.error(f"Failed to approve proposal | story_id={story_id} | error={e}")
            return False

    async def reject_proposal(
        self,
        story_id: str,
        telegram_user_id: str,
        rejection_reason: Optional[str] = None
    ) -> bool:
        """
        Reject fix proposal.

        Args:
            story_id: Ralph story ID
            telegram_user_id: User's Telegram ID who rejected
            rejection_reason: Optional reason for rejection

        Returns:
            True if rejected successfully
        """
        try:
            # Update ralph_stories
            await self.db.execute(
                """
                UPDATE ralph_stories
                SET approval_status = 'rejected',
                    approved_by_telegram_id = $1,
                    approved_at = NOW()
                WHERE story_id = $2
                  AND approval_status = 'pending_approval'
                """,
                telegram_user_id, story_id
            )

            # Update linked interaction
            outcome = f"proposal_rejected: {rejection_reason}" if rejection_reason else "proposal_rejected"
            await self.db.execute(
                """
                UPDATE interactions
                SET approval_status = 'rejected',
                    approved_at = NOW(),
                    outcome = $3
                WHERE story_id = $1
                  AND approval_status = 'pending'
                """,
                story_id, telegram_user_id, outcome
            )

            logger.info(f"Proposal rejected | story_id={story_id} | by={telegram_user_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to reject proposal | story_id={story_id} | error={e}")
            return False

    async def _trigger_ralph_execution(
        self,
        story_id: str,
        triggered_by: str
    ):
        """
        Trigger Ralph to execute approved story.

        Args:
            story_id: Ralph story ID
            triggered_by: User who triggered execution
        """
        try:
            payload = {
                'execution_mode': 'single_story',
                'story_id': story_id,
                'triggered_by': triggered_by
            }

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    self.ralph_webhook_url,
                    json=payload
                )

                if response.status_code == 200:
                    logger.info(f"Ralph execution triggered | story_id={story_id}")
                else:
                    logger.error(
                        f"Ralph execution failed | status={response.status_code} | "
                        f"response={response.text}"
                    )

        except Exception as e:
            logger.error(f"Failed to trigger Ralph execution | error={e}")

    async def get_story_status(self, story_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a Ralph story.

        Args:
            story_id: Ralph story ID

        Returns:
            Story details or None if not found
        """
        row = await self.db.fetchrow(
            """
            SELECT
                story_id,
                title,
                description,
                status,
                commit_hash,
                error_message,
                updated_at
            FROM ralph_stories
            WHERE story_id = $1
            """,
            story_id
        )

        return dict(row) if row else None

    async def expire_old_proposals(self) -> int:
        """
        Expire pending proposals older than timeout threshold.

        Returns:
            Number of proposals expired
        """
        try:
            # Call database function
            row = await self.db.fetchrow("SELECT expire_pending_approvals() as count")
            count = row['count'] if row else 0

            if count > 0:
                logger.info(f"Expired {count} old proposals")

            return count

        except Exception as e:
            logger.error(f"Failed to expire proposals | error={e}")
            return 0

    def classify_feedback(self, feedback_text: str, context: Dict[str, Any]) -> str:
        """
        Classify feedback type based on text and context.

        Args:
            feedback_text: User's feedback message
            context: Extracted context

        Returns:
            Feedback type classification
        """
        text_lower = feedback_text.lower()

        # Check for specific patterns
        if '404' in text_lower or 'not found' in text_lower:
            return 'manual_404'
        elif 'wrong manual' in text_lower or 'incorrect manual' in text_lower:
            return 'wrong_manual'
        elif 'wrong equipment' in text_lower or 'not my equipment' in text_lower:
            return 'wrong_equipment'
        elif 'ocr' in text_lower or "can't read" in text_lower:
            return 'ocr_failure'
        elif 'unclear' in text_lower or "don't understand" in text_lower:
            return 'unclear_answer'
        elif 'slow' in text_lower or 'performance' in text_lower:
            return 'performance_issue'
        elif 'feature' in text_lower or 'add' in text_lower:
            return 'feature_request'
        else:
            return 'general_bug'

    def extract_context(self, message_text: str) -> Dict[str, Any]:
        """
        Extract context (equipment_id, manual_url) from bot's message using regex.

        Args:
            message_text: Bot's original message text

        Returns:
            Dict with extracted context
        """
        import re

        context = {}

        # Equipment number: EQ-2026-000001
        equip_match = re.search(r'EQ-\d{4}-\d{6}', message_text)
        if equip_match:
            context['equipment_number'] = equip_match.group(0)

        # Manual URL
        url_match = re.search(r'https?://[^\s\)]+\.pdf', message_text)
        if url_match:
            context['manual_url'] = url_match.group(0)

        # Manufacturer (after "Manufacturer: ")
        mfr_match = re.search(r'Manufacturer:\s*([^\n]+)', message_text)
        if mfr_match:
            context['manufacturer'] = mfr_match.group(1).strip()

        # Model (after "Model: ")
        model_match = re.search(r'Model:\s*([^\n]+)', message_text)
        if model_match:
            context['model'] = model_match.group(1).strip()

        return context

    async def create_atom_from_feedback(
        self,
        story_id: str,
        interaction_id: UUID
    ) -> Optional[UUID]:
        """
        Create knowledge atom from approved Ralph fix.

        Called after Ralph story is completed and deployed. Converts
        user feedback + fix details into a validated knowledge atom.

        Args:
            story_id: Ralph story ID (e.g., 'FEEDBACK-001')
            interaction_id: UUID of feedback interaction

        Returns:
            UUID of created knowledge atom, or None if failed
        """
        try:
            # Get story details
            story = await self.db.fetchrow(
                """
                SELECT
                    story_id,
                    title,
                    description,
                    acceptance_criteria,
                    feedback_type,
                    commit_hash
                FROM ralph_stories
                WHERE story_id = $1
                """,
                story_id
            )

            if not story:
                logger.warning(f"Story not found | story_id={story_id}")
                return None

            # Get interaction details
            interaction = await self.db.fetchrow(
                """
                SELECT
                    feedback_text,
                    context_data,
                    created_at
                FROM interactions
                WHERE id = $1
                """,
                interaction_id
            )

            if not interaction:
                logger.warning(f"Interaction not found | interaction_id={interaction_id}")
                return None

            # Extract equipment details from context
            context_data = interaction['context_data'] or {}
            manufacturer = context_data.get('manufacturer')
            model = context_data.get('model')
            equipment_type = context_data.get('equipment_type')

            if not manufacturer or not model:
                logger.warning(
                    f"Missing manufacturer/model | story_id={story_id} | context={context_data}"
                )
                return None

            # Map feedback_type to AtomType
            feedback_type = story['feedback_type'] or 'general_bug'
            atom_type_map = {
                'manual_404': 'SPEC',
                'wrong_manual': 'SPEC',
                'wrong_equipment': 'TIP',
                'ocr_failure': 'TIP',
                'unclear_answer': 'PROCEDURE',
                'general_bug': 'PROCEDURE',
                'performance_issue': 'TIP',
                'feature_request': 'PROCEDURE'
            }
            atom_type = atom_type_map.get(feedback_type, 'PROCEDURE')

            # Build atom content
            content = f"**Issue:** {interaction['feedback_text']}\n\n"
            content += f"**Fix:** {story['description']}\n\n"

            if story['acceptance_criteria']:
                try:
                    criteria = json.loads(story['acceptance_criteria']) if isinstance(
                        story['acceptance_criteria'], str
                    ) else story['acceptance_criteria']
                    if isinstance(criteria, list):
                        content += "**Validation:**\n"
                        for criterion in criteria:
                            content += f"- {criterion}\n"
                except (json.JSONDecodeError, TypeError, KeyError) as parse_error:
                    logger.debug(f"Could not parse acceptance_criteria for story {story.get('id', 'unknown')}: {parse_error}")

            content += f"\n**Commit:** {story['commit_hash']}"

            # Generate keywords
            keywords = [
                manufacturer.lower(),
                model.lower(),
                feedback_type,
                atom_type.lower()
            ]
            if equipment_type:
                keywords.append(equipment_type.lower())

            # Create knowledge atom
            atom_id = await self.db.fetchval(
                """
                INSERT INTO knowledge_atoms (
                    id,
                    atom_type,
                    manufacturer,
                    model,
                    equipment_type,
                    content,
                    keywords,
                    confidence,
                    human_verified,
                    source_type,
                    source_id,
                    created_at,
                    usage_count,
                    last_used_at,
                    source_interaction_id
                )
                VALUES (
                    gen_random_uuid(),
                    $1, $2, $3, $4, $5, $6,
                    0.85,  -- High confidence (human-verified)
                    true,  -- Human verified
                    'feedback',
                    $7,    -- source_id (interaction_id as string)
                    NOW(),
                    0,     -- usage_count
                    NOW(), -- last_used_at
                    $8     -- source_interaction_id
                )
                RETURNING id
                """,
                atom_type,
                manufacturer,
                model,
                equipment_type,
                content,
                keywords,
                str(interaction_id),
                interaction_id  # Add interaction_id for source_interaction_id
            )

            logger.info(
                f"Atom created from feedback | atom_id={atom_id} | "
                f"story_id={story_id} | type={atom_type}"
            )

            # Link interaction back to created atom (KB-001)
            await self.db.execute(
                """
                UPDATE interactions
                SET atom_id = $1, atom_created = TRUE
                WHERE id = $2
                """,
                atom_id,
                interaction_id
            )

            logger.info(
                f"Bidirectional link established | "
                f"interaction={interaction_id} <-> atom={atom_id}"
            )

            return atom_id

        except Exception as e:
            logger.error(
                f"Failed to create atom from feedback | story_id={story_id} | "
                f"interaction_id={interaction_id} | error={e}",
                exc_info=True
            )
            return None
