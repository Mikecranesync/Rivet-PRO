"""
AgentExecutor - Routes requests to appropriate SME agents with retry logic.

Features:
- Routes to Siemens, Rockwell, Safety, or Generic agent based on vendor
- Logs each agent call
- Tracks state via WorkflowStateMachine
- Returns structured response with confidence score
- Retry with exponential backoff (5 attempts)
- Error notifications to admin on final failure
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class VendorType(Enum):
    """Supported equipment vendors"""
    SIEMENS = "siemens"
    ROCKWELL = "rockwell"
    SAFETY = "safety"
    GENERIC = "generic"


@dataclass
class AgentRequest:
    """Request to an SME agent"""
    query: str
    vendor: VendorType
    entity_id: str
    context: Optional[Dict[str, Any]] = None
    pipeline_id: Optional[int] = None


@dataclass
class AgentResponse:
    """Response from an SME agent"""
    answer: str
    confidence: float  # 0.0 to 1.0
    vendor: str
    citations: list
    suggested_actions: list
    warnings: list
    metadata: Dict[str, Any]
    execution_time_ms: float


class AgentExecutor:
    """
    Executes SME agent requests with routing, retry logic, and error handling.

    Usage:
        executor = AgentExecutor()

        # Execute an agent request
        response = await executor.execute(
            query="How do I reset a Siemens SINAMICS drive fault?",
            vendor=VendorType.SIEMENS,
            entity_id="work_order_123"
        )

        print(f"Answer: {response.answer}")
        print(f"Confidence: {response.confidence}")
    """

    def __init__(
        self,
        max_retries: int = 5,
        admin_chat_id: Optional[int] = None
    ):
        self.max_retries = max_retries
        self.admin_chat_id = admin_chat_id or int(os.getenv("ADMIN_CHAT_ID", "8445149012"))

        # Agent implementations (lazy loaded)
        self._agents: Dict[VendorType, Any] = {}

    def _get_agent(self, vendor: VendorType):
        """Get or create agent instance for vendor"""
        if vendor not in self._agents:
            # Import agents lazily to avoid circular imports
            if vendor == VendorType.SIEMENS:
                try:
                    from rivet_pro.agents.siemens_agent import SiemensAgent
                    self._agents[vendor] = SiemensAgent()
                except ImportError:
                    logger.warning("SiemensAgent not available, using generic")
                    self._agents[vendor] = self._create_generic_agent("siemens")

            elif vendor == VendorType.ROCKWELL:
                try:
                    from rivet_pro.agents.rockwell_agent import RockwellAgent
                    self._agents[vendor] = RockwellAgent()
                except ImportError:
                    logger.warning("RockwellAgent not available, using generic")
                    self._agents[vendor] = self._create_generic_agent("rockwell")

            elif vendor == VendorType.SAFETY:
                try:
                    from rivet_pro.agents.safety_agent import SafetyAgent
                    self._agents[vendor] = SafetyAgent()
                except ImportError:
                    logger.warning("SafetyAgent not available, using generic")
                    self._agents[vendor] = self._create_generic_agent("safety")

            else:
                self._agents[vendor] = self._create_generic_agent("generic")

        return self._agents[vendor]

    def _create_generic_agent(self, specialty: str):
        """Create a generic agent wrapper"""
        from rivet_pro.core.services.llm_manager import get_llm_manager

        class GenericAgentWrapper:
            def __init__(self, specialty: str):
                self.specialty = specialty
                self.llm = get_llm_manager()

            async def handle(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
                prompt = f"""You are an industrial automation expert specializing in {self.specialty}.

Answer the following question:
{query}

Provide:
1. A clear, concise answer
2. Any safety warnings
3. Suggested next steps

Format your response as a helpful guide for a field technician."""

                response, metadata = self.llm.generate(prompt, max_tokens=1000)

                return {
                    "answer": response,
                    "confidence": 0.7,
                    "citations": [],
                    "suggested_actions": [],
                    "warnings": [],
                    "metadata": metadata
                }

        return GenericAgentWrapper(specialty)

    async def execute(
        self,
        query: str,
        vendor: VendorType,
        entity_id: str,
        context: Optional[Dict[str, Any]] = None,
        pipeline_id: Optional[int] = None
    ) -> AgentResponse:
        """
        Execute an agent request with retry logic.

        Args:
            query: The question or task for the agent
            vendor: The vendor type (determines which agent to use)
            entity_id: ID of the entity being processed
            context: Optional context dict
            pipeline_id: Optional pipeline ID for state tracking

        Returns:
            AgentResponse with answer, confidence, and metadata
        """
        request = AgentRequest(
            query=query,
            vendor=vendor,
            entity_id=entity_id,
            context=context,
            pipeline_id=pipeline_id
        )

        return await self._execute_with_retry(request)

    async def _execute_with_retry(self, request: AgentRequest) -> AgentResponse:
        """Execute with exponential backoff retry"""
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"Agent execution attempt {attempt}/{self.max_retries} "
                    f"for {request.vendor.value} (entity: {request.entity_id})"
                )

                start_time = datetime.utcnow()

                # Get the appropriate agent
                agent = self._get_agent(request.vendor)

                # Execute the agent
                result = await self._call_agent(agent, request)

                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                # Log successful execution
                logger.info(
                    f"Agent {request.vendor.value} completed in {execution_time:.0f}ms "
                    f"with confidence {result.get('confidence', 0):.2f}"
                )

                return AgentResponse(
                    answer=result.get("answer", ""),
                    confidence=result.get("confidence", 0.5),
                    vendor=request.vendor.value,
                    citations=result.get("citations", []),
                    suggested_actions=result.get("suggested_actions", []),
                    warnings=result.get("warnings", []),
                    metadata={
                        "attempt": attempt,
                        "entity_id": request.entity_id,
                        "pipeline_id": request.pipeline_id,
                        **result.get("metadata", {})
                    },
                    execution_time_ms=execution_time
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Agent execution failed (attempt {attempt}/{self.max_retries}): {e}"
                )

                if attempt < self.max_retries:
                    # Exponential backoff: 1s, 2s, 4s, 8s, 16s
                    delay = 2 ** (attempt - 1)
                    logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)

        # All retries exhausted - send error notification
        await self._send_error_notification(request, last_error)

        raise RuntimeError(
            f"Agent execution failed after {self.max_retries} attempts: {last_error}"
        )

    async def _call_agent(
        self,
        agent: Any,
        request: AgentRequest
    ) -> Dict[str, Any]:
        """Call the agent's handle method"""
        # Handle both sync and async agents
        if asyncio.iscoroutinefunction(agent.handle):
            result = await agent.handle(request.query, request.context or {})
        else:
            # Run sync agent in executor to not block
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: agent.handle(request.query, request.context or {})
            )

        return result

    async def _send_error_notification(
        self,
        request: AgentRequest,
        error_message: str
    ):
        """Send error notification to admin via Telegram"""
        try:
            from rivet_pro.core.services.resilient_telegram_manager import send_admin_notification

            message = (
                f"<b>Pipeline Error</b>\n\n"
                f"<b>Pipeline ID:</b> {request.pipeline_id or 'N/A'}\n"
                f"<b>Entity:</b> {request.entity_id}\n"
                f"<b>Vendor:</b> {request.vendor.value}\n"
                f"<b>Error:</b> {error_message}\n"
                f"<b>Time:</b> {datetime.utcnow().isoformat()}\n\n"
                f"All {self.max_retries} retry attempts exhausted."
            )

            await send_admin_notification(message)
            logger.info("Error notification sent to admin")

        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")

    def route_vendor(self, query: str, context: Optional[Dict[str, Any]] = None) -> VendorType:
        """
        Determine the appropriate vendor based on query content.

        Args:
            query: The user's query
            context: Optional context with vendor hints

        Returns:
            VendorType to route to
        """
        query_lower = query.lower()

        # Check context for explicit vendor
        if context and context.get("vendor"):
            vendor_str = context["vendor"].lower()
            if "siemens" in vendor_str:
                return VendorType.SIEMENS
            elif "rockwell" in vendor_str or "allen" in vendor_str or "bradley" in vendor_str:
                return VendorType.ROCKWELL
            elif "safety" in vendor_str:
                return VendorType.SAFETY

        # Check query for vendor keywords
        siemens_keywords = ["siemens", "simatic", "sinamics", "profinet", "tia portal", "s7"]
        rockwell_keywords = ["rockwell", "allen-bradley", "allen bradley", "controllogix", "compactlogix", "powerflex", "studio 5000"]
        safety_keywords = ["safety", "e-stop", "estop", "light curtain", "interlock", "sil ", "sil1", "sil2", "sil3"]

        for kw in siemens_keywords:
            if kw in query_lower:
                return VendorType.SIEMENS

        for kw in rockwell_keywords:
            if kw in query_lower:
                return VendorType.ROCKWELL

        for kw in safety_keywords:
            if kw in query_lower:
                return VendorType.SAFETY

        # Default to generic
        return VendorType.GENERIC


# Convenience function
def get_agent_executor() -> AgentExecutor:
    """Get an AgentExecutor instance"""
    return AgentExecutor()
