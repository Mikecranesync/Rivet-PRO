"""
Pipeline Router - API endpoints for pipeline orchestration.

POST /pipeline/start - Create new pipeline execution
PUT /pipeline/{id}/stage - Update pipeline stage
GET /pipeline/{id} - Get pipeline status
GET /pipeline - List active pipelines
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

from rivet_pro.core.services.workflow_state_machine import (
    WorkflowStateMachine,
    WorkflowState,
    InvalidTransitionError,
    get_state_machine
)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


# Request/Response Models

class PipelineStartRequest(BaseModel):
    """Request to start a new pipeline"""
    workflow_type: str = Field(..., description="Type of workflow (e.g., 'sme_agent', 'photo_processing')")
    entity_id: str = Field(..., description="ID of the entity being processed")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class PipelineStartResponse(BaseModel):
    """Response from starting a pipeline"""
    pipeline_id: int
    workflow_type: str
    entity_id: str
    current_state: str
    created_at: str


class StageUpdateRequest(BaseModel):
    """Request to update pipeline stage"""
    new_state: str = Field(..., description="New state to transition to")
    stage_results: Optional[Dict[str, Any]] = Field(default=None, description="Results from the completed stage")
    error_message: Optional[str] = Field(default=None, description="Error message if stage failed")


class StageUpdateResponse(BaseModel):
    """Response from stage update"""
    pipeline_id: int
    previous_state: str
    current_state: str
    updated_at: str


class PipelineStatusResponse(BaseModel):
    """Pipeline status response"""
    id: int
    workflow_type: str
    entity_id: str
    current_state: str
    previous_state: Optional[str]
    transition_data: Dict[str, Any]
    created_at: str
    updated_at: str


# Valid workflow types
VALID_WORKFLOW_TYPES = [
    "sme_agent",
    "photo_processing",
    "work_order",
    "equipment_lookup",
    "manual_hunter",
    "research_pipeline"
]


# Endpoints

@router.post("/start", response_model=PipelineStartResponse)
async def start_pipeline(request: PipelineStartRequest):
    """
    Start a new pipeline execution.

    Creates a new workflow in CREATED state and returns the pipeline ID.
    """
    # Validate workflow type
    if request.workflow_type not in VALID_WORKFLOW_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid workflow_type. Must be one of: {VALID_WORKFLOW_TYPES}"
        )

    try:
        machine = get_state_machine()
        pipeline_id = machine.create(
            workflow_type=request.workflow_type,
            entity_id=request.entity_id,
            metadata=request.metadata
        )

        # Get the created workflow
        workflow = machine.get_current_state(pipeline_id)

        return PipelineStartResponse(
            pipeline_id=pipeline_id,
            workflow_type=workflow["workflow_type"],
            entity_id=workflow["entity_id"],
            current_state=workflow["current_state"],
            created_at=workflow["created_at"].isoformat()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{pipeline_id}/stage", response_model=StageUpdateResponse)
async def update_pipeline_stage(pipeline_id: int, request: StageUpdateRequest):
    """
    Update pipeline to a new stage.

    Validates the transition and persists stage results.
    """
    try:
        # Parse the new state
        try:
            new_state = WorkflowState(request.new_state)
        except ValueError:
            valid_states = [s.value for s in WorkflowState]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid state. Must be one of: {valid_states}"
            )

        machine = get_state_machine()

        # Get current state
        current = machine.get_current_state(pipeline_id)
        if not current:
            raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_id} not found")

        previous_state = current["current_state"]

        # Build metadata for transition
        metadata = {}
        if request.stage_results:
            metadata["stage_results"] = request.stage_results
        if request.error_message:
            metadata["error_message"] = request.error_message

        # Perform transition
        machine.transition(pipeline_id, new_state, metadata)

        return StageUpdateResponse(
            pipeline_id=pipeline_id,
            previous_state=previous_state,
            current_state=new_state.value,
            updated_at=datetime.utcnow().isoformat()
        )

    except InvalidTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pipeline_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(pipeline_id: int):
    """Get the current status of a pipeline."""
    try:
        machine = get_state_machine()
        workflow = machine.get_current_state(pipeline_id)

        if not workflow:
            raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_id} not found")

        return PipelineStatusResponse(
            id=workflow["id"],
            workflow_type=workflow["workflow_type"],
            entity_id=workflow["entity_id"],
            current_state=workflow["current_state"],
            previous_state=workflow.get("previous_state"),
            transition_data=workflow.get("transition_data", {}),
            created_at=workflow["created_at"].isoformat(),
            updated_at=workflow["updated_at"].isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[PipelineStatusResponse])
async def list_active_pipelines(
    workflow_type: Optional[str] = None,
    limit: int = 50
):
    """List all active (non-terminal) pipelines."""
    try:
        machine = get_state_machine()
        workflows = machine.get_active_workflows(workflow_type)

        return [
            PipelineStatusResponse(
                id=w["id"],
                workflow_type=w["workflow_type"],
                entity_id=w["entity_id"],
                current_state=w["current_state"],
                previous_state=w.get("previous_state"),
                transition_data=w.get("transition_data", {}),
                created_at=w["created_at"].isoformat(),
                updated_at=w["updated_at"].isoformat()
            )
            for w in workflows[:limit]
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{entity_id}", response_model=List[PipelineStatusResponse])
async def get_pipeline_history(
    entity_id: str,
    workflow_type: Optional[str] = None,
    limit: int = 50
):
    """Get pipeline execution history for an entity."""
    try:
        machine = get_state_machine()
        history = machine.get_history(entity_id, workflow_type, limit)

        return [
            PipelineStatusResponse(
                id=w["id"],
                workflow_type=w["workflow_type"],
                entity_id=w["entity_id"],
                current_state=w["current_state"],
                previous_state=w.get("previous_state"),
                transition_data=w.get("transition_data", {}),
                created_at=w["created_at"].isoformat(),
                updated_at=w["updated_at"].isoformat()
            )
            for w in history
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
