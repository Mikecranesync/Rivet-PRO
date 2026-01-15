"""
Troubleshooting Tree Drafts Service

Allows users to save Claude-generated guides as draft troubleshooting trees.
Admins can review, approve, or reject drafts.
"""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from rivet_pro.infra.database import db
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)


class DraftStatus:
    """Draft status constants"""
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


async def save_draft(
    equipment_type: str,
    problem: str,
    steps: List[str],
    user_id: int,
    original_query: Optional[str] = None
) -> int:
    """
    Save a Claude-generated guide as a draft troubleshooting tree.

    Args:
        equipment_type: Type of equipment (e.g., "Siemens S7-1200 PLC")
        problem: Problem description (e.g., "Communication fault")
        steps: List of troubleshooting steps from Claude
        user_id: Telegram user ID who saved the draft
        original_query: Original user query/conversation context

    Returns:
        Draft ID

    Example:
        draft_id = await save_draft(
            equipment_type="Siemens S7-1200 PLC",
            problem="Communication fault",
            steps=["Step 1: Check cable", "Step 2: Verify IP"],
            user_id=123456789,
            original_query="My PLC won't communicate"
        )
    """
    try:
        # Validate inputs
        if not equipment_type or not problem or not steps:
            raise ValueError("equipment_type, problem, and steps are required")

        if not isinstance(steps, list) or len(steps) == 0:
            raise ValueError("steps must be a non-empty list")

        # Convert steps to JSON
        steps_json = json.dumps(steps)

        # Insert draft
        query = """
            INSERT INTO troubleshooting_tree_drafts
                (equipment_type, problem, generated_steps, user_id, original_query, status)
            VALUES ($1, $2, $3::jsonb, $4, $5, $6)
            RETURNING id
        """

        result = await db.fetchval(
            query,
            equipment_type,
            problem,
            steps_json,
            user_id,
            original_query,
            DraftStatus.DRAFT
        )

        logger.info(
            f"Draft saved successfully | "
            f"Draft ID: {result} | "
            f"Equipment: {equipment_type} | "
            f"User: {user_id}"
        )

        return result

    except Exception as e:
        logger.error(f"Failed to save draft | Error: {e}")
        raise


async def get_draft(draft_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a specific draft by ID.

    Args:
        draft_id: Draft ID

    Returns:
        Draft details as dict, or None if not found
    """
    try:
        query = """
            SELECT
                d.id,
                d.equipment_type,
                d.problem,
                d.generated_steps,
                d.original_query,
                d.user_id,
                d.status,
                d.approved_by,
                d.approved_at,
                d.rejection_reason,
                d.tree_id,
                d.created_at,
                d.updated_at,
                t1.name as creator_name,
                t2.name as approver_name
            FROM troubleshooting_tree_drafts d
            LEFT JOIN technicians t1 ON d.user_id = t1.telegram_id
            LEFT JOIN technicians t2 ON d.approved_by = t2.telegram_id
            WHERE d.id = $1
        """

        result = await db.fetchrow(query, draft_id)

        if not result:
            return None

        return {
            "id": result["id"],
            "equipment_type": result["equipment_type"],
            "problem": result["problem"],
            "generated_steps": result["generated_steps"],
            "original_query": result["original_query"],
            "user_id": result["user_id"],
            "creator_name": result["creator_name"],
            "status": result["status"],
            "approved_by": result["approved_by"],
            "approver_name": result["approver_name"],
            "approved_at": result["approved_at"],
            "rejection_reason": result["rejection_reason"],
            "tree_id": result["tree_id"],
            "created_at": result["created_at"],
            "updated_at": result["updated_at"],
        }

    except Exception as e:
        logger.error(f"Failed to get draft | Draft ID: {draft_id} | Error: {e}")
        raise


async def list_drafts(
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    List drafts with optional filtering.

    Args:
        status: Filter by status (draft, approved, rejected)
        user_id: Filter by user who created the draft
        limit: Maximum number of results (default: 50)
        offset: Pagination offset (default: 0)

    Returns:
        List of draft summaries

    Example:
        # Get pending drafts
        drafts = await list_drafts(status="draft")

        # Get user's drafts
        user_drafts = await list_drafts(user_id=123456789)
    """
    try:
        # Build query with filters
        conditions = []
        params = []
        param_count = 1

        if status:
            conditions.append(f"d.status = ${param_count}")
            params.append(status)
            param_count += 1

        if user_id:
            conditions.append(f"d.user_id = ${param_count}")
            params.append(user_id)
            param_count += 1

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
            SELECT
                d.id,
                d.equipment_type,
                d.problem,
                d.status,
                d.user_id,
                d.created_at,
                d.updated_at,
                t.name as creator_name,
                jsonb_array_length(d.generated_steps) as step_count
            FROM troubleshooting_tree_drafts d
            LEFT JOIN technicians t ON d.user_id = t.telegram_id
            {where_clause}
            ORDER BY d.created_at DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """

        params.extend([limit, offset])

        results = await db.fetch(query, *params)

        drafts = []
        for row in results:
            drafts.append({
                "id": row["id"],
                "equipment_type": row["equipment_type"],
                "problem": row["problem"],
                "status": row["status"],
                "user_id": row["user_id"],
                "creator_name": row["creator_name"],
                "step_count": row["step_count"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            })

        logger.info(f"Listed drafts | Status: {status} | Count: {len(drafts)}")

        return drafts

    except Exception as e:
        logger.error(f"Failed to list drafts | Error: {e}")
        raise


async def approve_draft(draft_id: int, approved_by: int) -> Optional[int]:
    """
    Approve a draft and convert it to a troubleshooting tree.

    Args:
        draft_id: Draft ID to approve
        approved_by: Telegram user ID of approver (admin)

    Returns:
        Tree ID of created troubleshooting tree, or None if draft not found

    Example:
        tree_id = await approve_draft(draft_id=42, approved_by=123456789)
        if tree_id:
            print(f"Draft approved! Tree ID: {tree_id}")
    """
    try:
        # Get the draft
        draft = await get_draft(draft_id)
        if not draft:
            logger.warning(f"Draft not found | Draft ID: {draft_id}")
            return None

        if draft["status"] != DraftStatus.DRAFT:
            raise ValueError(f"Draft already {draft['status']}")

        # Create troubleshooting tree from draft
        tree_data = _convert_draft_to_tree(draft)

        # Insert tree
        tree_query = """
            INSERT INTO troubleshooting_trees
                (equipment_type, problem, tree_data, created_by)
            VALUES ($1, $2, $3::jsonb, $4)
            ON CONFLICT (equipment_type, problem)
            DO UPDATE SET
                tree_data = EXCLUDED.tree_data,
                updated_at = NOW(),
                usage_count = troubleshooting_trees.usage_count
            RETURNING id
        """

        tree_id = await db.fetchval(
            tree_query,
            draft["equipment_type"],
            draft["problem"],
            json.dumps(tree_data),
            approved_by
        )

        # Update draft status
        update_query = """
            UPDATE troubleshooting_tree_drafts
            SET
                status = $1,
                approved_by = $2,
                approved_at = NOW(),
                tree_id = $3
            WHERE id = $4
        """

        await db.execute(
            update_query,
            DraftStatus.APPROVED,
            approved_by,
            tree_id,
            draft_id
        )

        logger.info(
            f"Draft approved successfully | "
            f"Draft ID: {draft_id} | "
            f"Tree ID: {tree_id} | "
            f"Approved by: {approved_by}"
        )

        return tree_id

    except Exception as e:
        logger.error(f"Failed to approve draft | Draft ID: {draft_id} | Error: {e}")
        raise


async def reject_draft(draft_id: int, rejected_by: int, reason: str) -> bool:
    """
    Reject a draft with a reason.

    Args:
        draft_id: Draft ID to reject
        rejected_by: Telegram user ID of reviewer (admin)
        reason: Rejection reason

    Returns:
        True if successful, False if draft not found

    Example:
        success = await reject_draft(
            draft_id=42,
            rejected_by=123456789,
            reason="Steps are too generic, need more detail"
        )
    """
    try:
        # Check if draft exists
        draft = await get_draft(draft_id)
        if not draft:
            logger.warning(f"Draft not found | Draft ID: {draft_id}")
            return False

        if draft["status"] != DraftStatus.DRAFT:
            raise ValueError(f"Draft already {draft['status']}")

        # Update draft status
        query = """
            UPDATE troubleshooting_tree_drafts
            SET
                status = $1,
                approved_by = $2,
                approved_at = NOW(),
                rejection_reason = $3
            WHERE id = $4
        """

        await db.execute(
            query,
            DraftStatus.REJECTED,
            rejected_by,
            reason,
            draft_id
        )

        logger.info(
            f"Draft rejected | "
            f"Draft ID: {draft_id} | "
            f"Rejected by: {rejected_by} | "
            f"Reason: {reason}"
        )

        return True

    except Exception as e:
        logger.error(f"Failed to reject draft | Draft ID: {draft_id} | Error: {e}")
        raise


async def delete_draft(draft_id: int) -> bool:
    """
    Delete a draft (hard delete).

    Args:
        draft_id: Draft ID to delete

    Returns:
        True if deleted, False if not found
    """
    try:
        query = "DELETE FROM troubleshooting_tree_drafts WHERE id = $1"
        result = await db.execute(query, draft_id)

        deleted = "DELETE 1" in result
        if deleted:
            logger.info(f"Draft deleted | Draft ID: {draft_id}")
        else:
            logger.warning(f"Draft not found for deletion | Draft ID: {draft_id}")

        return deleted

    except Exception as e:
        logger.error(f"Failed to delete draft | Draft ID: {draft_id} | Error: {e}")
        raise


def _convert_draft_to_tree(draft: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a draft's generated steps into a troubleshooting tree structure.

    Args:
        draft: Draft dictionary with generated_steps

    Returns:
        Tree data structure compatible with troubleshooting_trees.tree_data
    """
    steps = draft["generated_steps"]

    # Create a simple linear tree structure from steps
    # Each step becomes a node with a "next" action
    nodes = []

    for i, step in enumerate(steps):
        node_id = f"step_{i + 1}"

        node = {
            "id": node_id,
            "type": "action",
            "content": step,
            "actions": []
        }

        # Add "next" action for all but the last step
        if i < len(steps) - 1:
            node["actions"].append({
                "label": "Next",
                "next": f"step_{i + 2}"
            })
        else:
            # Last step - mark as complete
            node["actions"].append({
                "label": "Complete",
                "next": None
            })

        nodes.append(node)

    return {
        "version": "1.0",
        "root": "step_1",
        "nodes": nodes,
        "metadata": {
            "source": "claude_draft",
            "draft_id": draft["id"],
            "created_from_query": draft["original_query"],
        }
    }


async def get_draft_stats() -> Dict[str, int]:
    """
    Get statistics about drafts.

    Returns:
        Dictionary with draft counts by status
    """
    try:
        query = """
            SELECT
                status,
                COUNT(*) as count
            FROM troubleshooting_tree_drafts
            GROUP BY status
        """

        results = await db.fetch(query)

        stats = {
            "total": 0,
            DraftStatus.DRAFT: 0,
            DraftStatus.APPROVED: 0,
            DraftStatus.REJECTED: 0,
        }

        for row in results:
            stats[row["status"]] = row["count"]
            stats["total"] += row["count"]

        return stats

    except Exception as e:
        logger.error(f"Failed to get draft stats | Error: {e}")
        raise
