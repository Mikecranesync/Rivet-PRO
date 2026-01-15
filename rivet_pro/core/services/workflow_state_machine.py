"""
WorkflowStateMachine - State machine for tracking pipeline execution states.

Provides state transition validation and history tracking for all pipeline workflows.
States: CREATED, IN_PROGRESS, PENDING_APPROVAL, APPROVED, REJECTED, COMPLETED, FAILED
"""

import os
import psycopg2
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from dotenv import load_dotenv

load_dotenv()


class WorkflowState(Enum):
    """Valid workflow states"""
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# Define valid state transitions
VALID_TRANSITIONS: Dict[WorkflowState, List[WorkflowState]] = {
    WorkflowState.CREATED: [WorkflowState.IN_PROGRESS, WorkflowState.FAILED],
    WorkflowState.IN_PROGRESS: [WorkflowState.PENDING_APPROVAL, WorkflowState.COMPLETED, WorkflowState.FAILED],
    WorkflowState.PENDING_APPROVAL: [WorkflowState.APPROVED, WorkflowState.REJECTED, WorkflowState.FAILED],
    WorkflowState.APPROVED: [WorkflowState.IN_PROGRESS, WorkflowState.COMPLETED, WorkflowState.FAILED],
    WorkflowState.REJECTED: [WorkflowState.COMPLETED, WorkflowState.FAILED],
    WorkflowState.COMPLETED: [],  # Terminal state
    WorkflowState.FAILED: [WorkflowState.CREATED],  # Can retry
}


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted"""
    pass


class WorkflowStateMachine:
    """
    State machine for tracking pipeline execution states.

    Usage:
        machine = WorkflowStateMachine()

        # Create a new workflow
        workflow_id = machine.create("sme_agent", "work_order_123", {"user_id": "456"})

        # Transition to new state
        machine.transition(workflow_id, WorkflowState.IN_PROGRESS, {"step": "siemens_agent"})

        # Get current state
        state = machine.get_current_state(workflow_id)

        # Get history
        history = machine.get_history(workflow_id)
    """

    def __init__(self, database_url: Optional[str] = None):
        """Initialize with database connection"""
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL not found in environment")

    def _get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.database_url)

    def create(
        self,
        workflow_type: str,
        entity_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Create a new workflow in CREATED state.

        Args:
            workflow_type: Type of workflow (e.g., 'sme_agent', 'photo_processing')
            entity_id: ID of the entity being processed (e.g., work order ID)
            metadata: Optional metadata to store with the workflow

        Returns:
            The ID of the newly created workflow record
        """
        import json

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO pipeline_execution_history
                    (workflow_type, entity_id, current_state, transition_data)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (
                    workflow_type,
                    entity_id,
                    WorkflowState.CREATED.value,
                    json.dumps(metadata) if metadata else None
                ))
                workflow_id = cur.fetchone()[0]
                conn.commit()
                return workflow_id
        finally:
            conn.close()

    def transition(
        self,
        workflow_id: int,
        new_state: WorkflowState,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Transition workflow to a new state.

        Args:
            workflow_id: ID of the workflow
            new_state: The new state to transition to
            metadata: Optional metadata to store with this transition

        Returns:
            True if transition successful

        Raises:
            InvalidTransitionError: If the transition is not valid
        """
        import json

        # Get current state
        current = self.get_current_state(workflow_id)
        if current is None:
            raise InvalidTransitionError(f"Workflow {workflow_id} not found")

        current_state = WorkflowState(current["current_state"])

        # Validate transition
        if new_state not in VALID_TRANSITIONS.get(current_state, []):
            raise InvalidTransitionError(
                f"Cannot transition from {current_state.value} to {new_state.value}"
            )

        # Merge existing metadata with new metadata
        existing_data = current.get("transition_data") or {}
        if metadata:
            existing_data.update(metadata)
        existing_data["last_transition"] = datetime.utcnow().isoformat()
        existing_data["transition_from"] = current_state.value

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE pipeline_execution_history
                    SET previous_state = current_state,
                        current_state = %s,
                        transition_data = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (
                    new_state.value,
                    json.dumps(existing_data),
                    workflow_id
                ))
                conn.commit()
                return True
        finally:
            conn.close()

    def get_current_state(self, workflow_id: int) -> Optional[Dict[str, Any]]:
        """
        Get current state of a workflow.

        Args:
            workflow_id: ID of the workflow

        Returns:
            Dictionary with workflow data or None if not found
        """
        import json

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, workflow_type, entity_id, current_state,
                           previous_state, transition_data, created_at, updated_at
                    FROM pipeline_execution_history
                    WHERE id = %s
                """, (workflow_id,))
                row = cur.fetchone()

                if not row:
                    return None

                return {
                    "id": row[0],
                    "workflow_type": row[1],
                    "entity_id": row[2],
                    "current_state": row[3],
                    "previous_state": row[4],
                    "transition_data": row[5] if isinstance(row[5], dict) else (json.loads(row[5]) if row[5] else {}),
                    "created_at": row[6],
                    "updated_at": row[7]
                }
        finally:
            conn.close()

    def get_history(
        self,
        entity_id: str,
        workflow_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get workflow history for an entity.

        Args:
            entity_id: ID of the entity
            workflow_type: Optional filter by workflow type
            limit: Maximum number of records to return

        Returns:
            List of workflow history records
        """
        import json

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                if workflow_type:
                    cur.execute("""
                        SELECT id, workflow_type, entity_id, current_state,
                               previous_state, transition_data, created_at, updated_at
                        FROM pipeline_execution_history
                        WHERE entity_id = %s AND workflow_type = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (entity_id, workflow_type, limit))
                else:
                    cur.execute("""
                        SELECT id, workflow_type, entity_id, current_state,
                               previous_state, transition_data, created_at, updated_at
                        FROM pipeline_execution_history
                        WHERE entity_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (entity_id, limit))

                rows = cur.fetchall()
                return [
                    {
                        "id": row[0],
                        "workflow_type": row[1],
                        "entity_id": row[2],
                        "current_state": row[3],
                        "previous_state": row[4],
                        "transition_data": row[5] if isinstance(row[5], dict) else (json.loads(row[5]) if row[5] else {}),
                        "created_at": row[6],
                        "updated_at": row[7]
                    }
                    for row in rows
                ]
        finally:
            conn.close()

    def get_active_workflows(
        self,
        workflow_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all workflows that are not in terminal states (COMPLETED, FAILED).

        Args:
            workflow_type: Optional filter by workflow type

        Returns:
            List of active workflow records
        """
        import json

        terminal_states = [WorkflowState.COMPLETED.value, WorkflowState.FAILED.value]

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                if workflow_type:
                    cur.execute("""
                        SELECT id, workflow_type, entity_id, current_state,
                               previous_state, transition_data, created_at, updated_at
                        FROM pipeline_execution_history
                        WHERE workflow_type = %s
                          AND current_state NOT IN %s
                        ORDER BY created_at DESC
                    """, (workflow_type, tuple(terminal_states)))
                else:
                    cur.execute("""
                        SELECT id, workflow_type, entity_id, current_state,
                               previous_state, transition_data, created_at, updated_at
                        FROM pipeline_execution_history
                        WHERE current_state NOT IN %s
                        ORDER BY created_at DESC
                    """, (tuple(terminal_states),))

                rows = cur.fetchall()
                return [
                    {
                        "id": row[0],
                        "workflow_type": row[1],
                        "entity_id": row[2],
                        "current_state": row[3],
                        "previous_state": row[4],
                        "transition_data": row[5] if isinstance(row[5], dict) else (json.loads(row[5]) if row[5] else {}),
                        "created_at": row[6],
                        "updated_at": row[7]
                    }
                    for row in rows
                ]
        finally:
            conn.close()


# Convenience function for quick access
def get_state_machine() -> WorkflowStateMachine:
    """Get a WorkflowStateMachine instance"""
    return WorkflowStateMachine()
