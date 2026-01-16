"""
PipelineIntegration - Facade connecting all Phase 3 pipeline components.

Integrates:
- WorkflowStateMachine (state tracking)
- MultiProviderLLMManager (LLM failover)
- ResilientTelegramManager (message queue)
- AgentExecutor (SME routing)

Usage:
    from rivet_pro.core.services.pipeline_integration import get_pipeline

    pipeline = get_pipeline()
    result = await pipeline.process_text_message(
        user_id="123",
        query="How do I reset a Siemens drive fault?"
    )
    print(result["answer"])
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from rivet_pro.core.services.workflow_state_machine import (
    WorkflowStateMachine,
    WorkflowState,
    get_state_machine,
    InvalidTransitionError
)
from rivet_pro.core.services.llm_manager import (
    MultiProviderLLMManager,
    get_llm_manager
)
from rivet_pro.core.services.agent_executor import (
    AgentExecutor,
    VendorType,
    get_agent_executor
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result from pipeline processing"""
    answer: str
    confidence: float
    vendor: str
    pipeline_id: int
    provider_used: str
    execution_time_ms: float
    cached: bool = False
    metadata: Dict[str, Any] = None


class PipelineIntegration:
    """
    Facade connecting all Phase 3 pipeline components.

    Orchestrates the flow:
    1. Create pipeline execution (CREATED state)
    2. Transition to IN_PROGRESS
    3. Route to vendor SME via AgentExecutor
    4. AgentExecutor uses LLMManager for failover
    5. Transition to COMPLETED
    6. Return structured result
    """

    def __init__(
        self,
        state_machine: Optional[WorkflowStateMachine] = None,
        llm_manager: Optional[MultiProviderLLMManager] = None,
        agent_executor: Optional[AgentExecutor] = None
    ):
        """
        Initialize with optional dependency injection for testing.

        Args:
            state_machine: WorkflowStateMachine instance (or creates new)
            llm_manager: MultiProviderLLMManager instance (or creates new)
            agent_executor: AgentExecutor instance (or creates new)
        """
        self.state_machine = state_machine or get_state_machine()
        self.llm_manager = llm_manager or get_llm_manager()
        self.agent_executor = agent_executor or get_agent_executor()

        logger.info("PipelineIntegration initialized with all Phase 3 components")

    async def process_text_message(
        self,
        user_id: str,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> PipelineResult:
        """
        Process a text message through the full pipeline.

        Flow:
        1. Create pipeline execution record
        2. Detect vendor from query
        3. Execute via AgentExecutor (uses LLMManager internally)
        4. Track state transitions
        5. Return structured result

        Args:
            user_id: Telegram user ID
            query: User's question text
            context: Optional additional context (e.g., equipment data)

        Returns:
            PipelineResult with answer, confidence, vendor, etc.
        """
        start_time = datetime.utcnow()
        pipeline_id = None

        try:
            # Step 1: Create pipeline execution (CREATED state)
            pipeline_id = self.state_machine.create(
                workflow_type="sme_query",
                entity_id=f"user_{user_id}",
                metadata={
                    "query": query[:200],  # Truncate for storage
                    "timestamp": start_time.isoformat()
                }
            )
            logger.info(f"Pipeline {pipeline_id} created for user {user_id}")

            # Step 2: Transition to IN_PROGRESS
            self.state_machine.transition(
                pipeline_id,
                WorkflowState.IN_PROGRESS,
                metadata={"step": "routing"}
            )

            # Step 3: Route to vendor
            vendor = self.agent_executor.route_vendor(query, context)
            logger.info(f"Pipeline {pipeline_id} routing to vendor: {vendor.value}")

            # Step 4: Execute via AgentExecutor
            response = await self.agent_executor.execute(
                query=query,
                vendor=vendor,
                entity_id=f"user_{user_id}",
                context=context,
                pipeline_id=pipeline_id
            )

            # Step 5: Transition to COMPLETED
            execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.state_machine.transition(
                pipeline_id,
                WorkflowState.COMPLETED,
                metadata={
                    "confidence": response.confidence,
                    "vendor": response.vendor,
                    "execution_time_ms": execution_time_ms
                }
            )

            logger.info(
                f"Pipeline {pipeline_id} completed: "
                f"vendor={response.vendor}, confidence={response.confidence:.2f}, "
                f"time={execution_time_ms:.0f}ms"
            )

            return PipelineResult(
                answer=response.answer,
                confidence=response.confidence,
                vendor=response.vendor,
                pipeline_id=pipeline_id,
                provider_used=response.metadata.get("provider", "unknown"),
                execution_time_ms=execution_time_ms,
                cached=response.metadata.get("cached", False),
                metadata=response.metadata
            )

        except Exception as e:
            logger.error(f"Pipeline {pipeline_id} failed: {e}", exc_info=True)

            # Transition to FAILED if pipeline was created
            if pipeline_id:
                try:
                    self.state_machine.transition(
                        pipeline_id,
                        WorkflowState.FAILED,
                        metadata={"error": str(e)}
                    )
                except InvalidTransitionError:
                    # Already in terminal state, ignore
                    pass

            raise

    async def process_photo(
        self,
        user_id: str,
        photo_data: bytes,
        caption: Optional[str] = None
    ) -> PipelineResult:
        """
        Process a photo through the pipeline (OCR + equipment matching).

        This is a placeholder for future implementation.
        Currently, photo processing uses the existing bot handler.

        Args:
            user_id: Telegram user ID
            photo_data: Raw photo bytes
            caption: Optional caption with the photo

        Returns:
            PipelineResult with OCR results and equipment match
        """
        # TODO: Integrate with existing photo handler
        # For now, delegate to existing implementation
        raise NotImplementedError(
            "Photo processing via pipeline not yet implemented. "
            "Use TelegramBot._handle_photo() directly."
        )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get pipeline statistics for /pipeline command.

        Returns:
            Dict with active workflows, LLM stats, etc.
        """
        active_workflows = self.state_machine.get_active_workflows()

        return {
            "active_workflows": len(active_workflows),
            "workflow_types": self._count_by_type(active_workflows),
            "states": self._count_by_state(active_workflows),
            "timestamp": datetime.utcnow().isoformat()
        }

    def _count_by_type(self, workflows: list) -> Dict[str, int]:
        """Count workflows by type"""
        counts = {}
        for wf in workflows:
            wf_type = wf.get("workflow_type", "unknown")
            counts[wf_type] = counts.get(wf_type, 0) + 1
        return counts

    def _count_by_state(self, workflows: list) -> Dict[str, int]:
        """Count workflows by state"""
        counts = {}
        for wf in workflows:
            state = wf.get("current_state", "unknown")
            counts[state] = counts.get(state, 0) + 1
        return counts


# Global instance (singleton pattern)
_pipeline_instance: Optional[PipelineIntegration] = None


def get_pipeline() -> PipelineIntegration:
    """Get or create the global PipelineIntegration instance"""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = PipelineIntegration()
    return _pipeline_instance


def reset_pipeline():
    """Reset the global pipeline instance (for testing)"""
    global _pipeline_instance
    _pipeline_instance = None
