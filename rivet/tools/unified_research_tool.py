"""
UnifiedResearchTool - Multi-Backend Research with Smart Routing

Combines all research backends with intelligent routing and automatic fallback:
- ResearchExecutorTool (OpenHands/LangChain - free with Ollama)
- ManusResearchTool (Commercial API - reliable, $0.50-2.00/task)
- OpenManusResearchTool (Self-hosted - $0-0.50/task)

Features:
- Auto-selects best backend based on task complexity, priority, and cost
- Automatic fallback chain if primary backend fails
- Cost tracking and budget management
- Same interface as all other research tools

Usage:
    from rivet.tools.unified_research_tool import UnifiedResearchTool

    # Auto-select best backend
    tool = UnifiedResearchTool(backend="auto")
    result = await tool.execute(task)

    # Force specific backend
    tool = UnifiedResearchTool(backend="manus_api")
    result = await tool.execute(task)

    # Custom backend preferences
    tool = UnifiedResearchTool(
        backend="auto",
        prefer_free=True,  # Prefer free backends when possible
        cost_threshold_usd=0.50,  # Switch to paid if free > threshold
    )
"""

import asyncio
import logging
import os
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

# Import research task/result models
try:
    from rivet.tools.research_executor import (
        ResearchTask,
        ResearchResult,
        ResearchStatus,
        ResearchPriority,
    )
except ImportError:
    # Fallback if research_executor not available
    from pydantic import Field as PydanticField

    class ResearchTask(BaseModel):
        objective: str
        manufacturer: Optional[str] = None
        equipment_type: Optional[str] = None
        model_number: Optional[str] = None
        specific_queries: List[str] = PydanticField(default_factory=list)
        context: Optional[str] = None
        priority: str = "medium"
        timeout_minutes: int = 30
        max_sources: int = 10

    class ResearchResult(BaseModel):
        task_id: str
        status: str
        objective: str
        summary: str
        detailed_findings: str
        fault_codes: List[Dict] = PydanticField(default_factory=list)
        parameters: List[Dict] = PydanticField(default_factory=list)
        troubleshooting_steps: List[str] = PydanticField(default_factory=list)
        sources: List[Dict] = PydanticField(default_factory=list)
        citations_markdown: str = ""
        started_at: datetime
        completed_at: Optional[datetime] = None
        duration_seconds: Optional[float] = None
        llm_provider: str
        total_tokens_used: Optional[int] = None
        estimated_cost_usd: Optional[float] = None
        suggested_atom_title: Optional[str] = None
        suggested_atom_content: Optional[str] = None
        confidence_score: float = 0.0

logger = logging.getLogger(__name__)


class BackendType(str, Enum):
    """Available research backends"""
    AUTO = "auto"
    RESEARCH_EXECUTOR = "research_executor"
    MANUS_API = "manus_api"
    OPENMANUS = "openmanus"


class BackendPreference(BaseModel):
    """Backend selection preferences"""
    backend: BackendType = BackendType.AUTO
    prefer_free: bool = False
    cost_threshold_usd: float = 0.50
    enable_fallback: bool = True
    max_retries: int = 3


class UnifiedResearchTool:
    """
    Unified research tool with multiple backend support and smart routing.

    Backends (in priority order):
    1. ResearchExecutorTool - Free (Ollama) or cheap (DeepSeek ~$0.03)
    2. OpenManusResearchTool - Free (Ollama) or moderate (Claude ~$0.30)
    3. ManusResearchTool - Premium (Manus API ~$1.50)

    Smart Routing Logic:
    - Simple tasks (single lookup) → ResearchExecutor (free)
    - Moderate tasks (research) → ResearchExecutor or OpenManus
    - Complex tasks (multi-source report) → Manus API (most reliable)
    - Critical priority → Manus API (guaranteed SLA)

    Automatic Fallback:
    Primary → Fallback 1 → Fallback 2 → Error

    Cost Tracking:
    Tracks total spend across all backends with budget limits.
    """

    name = "unified_research"
    description = """Unified research tool with multiple backend options.
    Automatically selects the best backend based on task requirements.
    Supports free (Ollama), moderate (Claude), and premium (Manus API) options.
    """

    def __init__(
        self,
        backend: Union[BackendType, str] = BackendType.AUTO,
        prefer_free: bool = False,
        cost_threshold_usd: float = 0.50,
        enable_fallback: bool = True,
        max_retries: int = 3,
        manus_api_key: Optional[str] = None,
    ):
        """
        Initialize unified research tool.

        Args:
            backend: Backend selection ("auto", "research_executor", "manus_api", "openmanus")
            prefer_free: Prefer free backends when possible
            cost_threshold_usd: Switch to paid backend if free exceeds this cost
            enable_fallback: Enable automatic fallback on errors
            max_retries: Max retry attempts per backend
            manus_api_key: Manus API key (optional, reads from env if not provided)
        """
        if isinstance(backend, str):
            backend = BackendType(backend)

        self.preferences = BackendPreference(
            backend=backend,
            prefer_free=prefer_free,
            cost_threshold_usd=cost_threshold_usd,
            enable_fallback=enable_fallback,
            max_retries=max_retries,
        )

        self._backends = {}
        self._backend_order = []
        self._total_cost_usd = 0.0

        # Initialize available backends
        self._initialize_backends(manus_api_key)

        logger.info(
            f"UnifiedResearchTool initialized with {len(self._backends)} backends: "
            f"{list(self._backends.keys())}"
        )

    def _initialize_backends(self, manus_api_key: Optional[str] = None):
        """Initialize all available research backends"""

        # 1. ResearchExecutorTool (always available - free with Ollama)
        try:
            from rivet.tools.research_executor import ResearchExecutorTool

            self._backends["research_executor"] = ResearchExecutorTool()
            self._backend_order.append("research_executor")
            logger.info("ResearchExecutorTool loaded")
        except ImportError as e:
            logger.warning(f"ResearchExecutorTool not available: {e}")

        # 2. ManusResearchTool (requires API key)
        manus_key = manus_api_key or os.getenv("MANUS_API_KEY")
        if manus_key:
            try:
                from rivet.tools.manus_research_tool import ManusResearchTool

                self._backends["manus_api"] = ManusResearchTool(api_key=manus_key)
                self._backend_order.append("manus_api")
                logger.info("ManusResearchTool loaded")
            except ImportError as e:
                logger.warning(f"ManusResearchTool not available: {e}")
        else:
            logger.info("Manus API key not found - ManusResearchTool disabled")

        # 3. OpenManusResearchTool (self-hosted - auto-installs)
        try:
            from rivet.tools.openmanus_research_tool import OpenManusResearchTool

            self._backends["openmanus"] = OpenManusResearchTool()
            self._backend_order.append("openmanus")
            logger.info("OpenManusResearchTool loaded")
        except ImportError as e:
            logger.warning(f"OpenManusResearchTool not available: {e}")

        if not self._backends:
            raise RuntimeError(
                "No research backends available. Install at least one backend."
            )

    async def execute(
        self,
        task: Union[ResearchTask, Dict[str, Any], str],
    ) -> ResearchResult:
        """
        Execute research task with auto-selected or specified backend.

        Args:
            task: ResearchTask, dict, or string objective

        Returns:
            ResearchResult from the selected backend
        """
        # Normalize input to ResearchTask
        if isinstance(task, str):
            task = ResearchTask(objective=task)
        elif isinstance(task, dict):
            task = ResearchTask(**task)

        # Select backend
        backend_name = self._select_backend(task)

        logger.info(
            f"Executing research with backend: {backend_name} "
            f"(objective: {task.objective[:50]}...)"
        )

        # Execute with fallback
        if self.preferences.enable_fallback:
            return await self._execute_with_fallback(task, preferred_backend=backend_name)
        else:
            return await self._execute_single(task, backend_name)

    def _select_backend(self, task: ResearchTask) -> str:
        """
        Select best backend based on task characteristics.

        Routing logic:
        - CRITICAL priority → Manus API (most reliable)
        - Long timeout (>30min) → Manus API (complex research)
        - prefer_free=True → ResearchExecutor or OpenManus
        - Default → First available backend
        """
        # Manual backend selection
        if self.preferences.backend != BackendType.AUTO:
            backend_name = self.preferences.backend.value
            if backend_name in self._backends:
                return backend_name
            else:
                logger.warning(
                    f"Requested backend '{backend_name}' not available, "
                    f"falling back to auto-selection"
                )

        # Auto-selection logic
        priority = getattr(task, "priority", "medium")
        timeout = getattr(task, "timeout_minutes", 30)

        # Critical priority → Manus API (best reliability)
        if priority == "critical" or priority == "high":
            if "manus_api" in self._backends:
                logger.debug("Critical priority → Manus API")
                return "manus_api"

        # Long research → Manus API (handles complex workflows best)
        if timeout > 30:
            if "manus_api" in self._backends:
                logger.debug("Long timeout → Manus API")
                return "manus_api"

        # prefer_free → Use free backend
        if self.preferences.prefer_free:
            if "research_executor" in self._backends:
                logger.debug("Prefer free → ResearchExecutor")
                return "research_executor"
            elif "openmanus" in self._backends:
                logger.debug("Prefer free → OpenManus")
                return "openmanus"

        # Default: First available backend
        default = self._backend_order[0]
        logger.debug(f"Default selection → {default}")
        return default

    async def _execute_single(
        self,
        task: ResearchTask,
        backend_name: str,
    ) -> ResearchResult:
        """Execute task with single backend (no fallback)"""
        backend = self._backends[backend_name]

        try:
            result = await backend.execute(task)

            # Track cost
            if result.estimated_cost_usd:
                self._total_cost_usd += result.estimated_cost_usd

            logger.info(
                f"Research completed via {backend_name}: "
                f"status={result.status}, "
                f"cost=${result.estimated_cost_usd:.4f}"
            )

            return result

        except Exception as e:
            logger.exception(f"Error executing task with {backend_name}: {e}")
            raise

    async def _execute_with_fallback(
        self,
        task: ResearchTask,
        preferred_backend: str,
    ) -> ResearchResult:
        """
        Execute task with automatic fallback on errors.

        Fallback chain:
        1. Preferred backend
        2. Other available backends (in order)
        3. Raise error if all fail
        """
        # Build fallback chain (preferred first, then others)
        fallback_chain = [preferred_backend]
        for backend in self._backend_order:
            if backend not in fallback_chain:
                fallback_chain.append(backend)

        last_error = None

        for i, backend_name in enumerate(fallback_chain):
            try:
                logger.info(
                    f"Attempting backend {i+1}/{len(fallback_chain)}: {backend_name}"
                )

                result = await self._execute_single(task, backend_name)

                # Success!
                if i > 0:
                    logger.info(
                        f"Fallback successful: {backend_name} succeeded after "
                        f"{i} failed attempts"
                    )

                return result

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Backend {backend_name} failed: {e}. "
                    f"Trying next backend..."
                )

                # Continue to next backend
                continue

        # All backends failed
        logger.error(
            f"All {len(fallback_chain)} backends failed. Last error: {last_error}"
        )
        raise RuntimeError(
            f"All research backends failed. Last error: {last_error}"
        )

    # ========================================================================
    # Convenience Methods
    # ========================================================================

    async def research_manufacturer(
        self,
        manufacturer: str,
        equipment_type: str,
        timeout_minutes: int = 30,
    ) -> ResearchResult:
        """Convenience method for manufacturer research"""
        task = ResearchTask(
            objective=f"Research {manufacturer} {equipment_type} products and documentation",
            manufacturer=manufacturer,
            equipment_type=equipment_type,
            specific_queries=[
                f"What {equipment_type} products does {manufacturer} make?",
                "What are common fault codes and their meanings?",
                "Where can I find official documentation?",
            ],
            timeout_minutes=timeout_minutes,
        )

        return await self.execute(task)

    async def research_fault_code(
        self,
        manufacturer: str,
        equipment_type: str,
        fault_code: str,
        model_number: Optional[str] = None,
        timeout_minutes: int = 20,
    ) -> ResearchResult:
        """Convenience method for fault code research"""
        objective = f"Research {manufacturer} {equipment_type} fault code {fault_code}"
        if model_number:
            objective += f" (model {model_number})"

        task = ResearchTask(
            objective=objective,
            manufacturer=manufacturer,
            equipment_type=equipment_type,
            model_number=model_number,
            specific_queries=[
                f"What does fault code {fault_code} mean?",
                "What are the possible causes?",
                "What are the recommended troubleshooting steps?",
            ],
            timeout_minutes=timeout_minutes,
        )

        return await self.execute(task)

    async def fill_knowledge_gap(
        self,
        gap_description: str,
        context: Optional[str] = None,
        timeout_minutes: int = 30,
        priority: str = "high",
    ) -> ResearchResult:
        """Convenience method for knowledge gap filling"""
        task = ResearchTask(
            objective=f"Fill knowledge gap: {gap_description}",
            context=context,
            timeout_minutes=timeout_minutes,
            priority=priority,
        )

        return await self.execute(task)

    # ========================================================================
    # Status & Statistics
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get current status and statistics"""
        return {
            "available_backends": list(self._backends.keys()),
            "backend_order": self._backend_order,
            "preferences": {
                "backend": self.preferences.backend.value,
                "prefer_free": self.preferences.prefer_free,
                "cost_threshold_usd": self.preferences.cost_threshold_usd,
                "enable_fallback": self.preferences.enable_fallback,
            },
            "total_cost_usd": self._total_cost_usd,
        }

    def reset_cost_tracking(self):
        """Reset total cost counter"""
        self._total_cost_usd = 0.0

    # ========================================================================
    # LangChain Integration
    # ========================================================================

    def as_langchain_tool(self):
        """
        Wrap this tool as a LangChain tool.

        Returns:
            LangChain Tool instance
        """
        try:
            from langchain.tools import Tool

            def research_wrapper(objective: str) -> str:
                """Execute research and return summary"""
                result = asyncio.run(self.execute(objective))
                return result.summary

            return Tool(
                name=self.name,
                description=self.description,
                func=research_wrapper,
            )
        except ImportError:
            logger.warning("LangChain not installed - as_langchain_tool() unavailable")
            return None


# ============================================================================
# Standalone Functions
# ============================================================================

def create_langchain_tool(
    backend: Union[BackendType, str] = BackendType.AUTO,
    prefer_free: bool = False,
    manus_api_key: Optional[str] = None,
):
    """
    Create LangChain tool for unified research.

    Args:
        backend: Backend selection
        prefer_free: Prefer free backends
        manus_api_key: Manus API key (optional)

    Returns:
        LangChain Tool instance
    """
    tool = UnifiedResearchTool(
        backend=backend,
        prefer_free=prefer_free,
        manus_api_key=manus_api_key,
    )
    return tool.as_langchain_tool()


# ============================================================================
# CLI Support
# ============================================================================

if __name__ == "__main__":
    import sys

    async def main():
        if len(sys.argv) < 2:
            print("Usage: python unified_research_tool.py <objective> [backend]")
            print("\nExamples:")
            print('  python unified_research_tool.py "Research Siemens S7-1200"')
            print('  python unified_research_tool.py "Research Lenze VFD" manus_api')
            print('  python unified_research_tool.py "Research ABB fault codes" openmanus')
            sys.exit(1)

        objective = sys.argv[1]
        backend = sys.argv[2] if len(sys.argv) > 2 else "auto"

        print(f"Starting unified research: {objective}")
        print(f"Backend: {backend}")
        print("-" * 80)

        tool = UnifiedResearchTool(backend=backend)

        # Show available backends
        status = tool.get_status()
        print(f"\nAvailable backends: {', '.join(status['available_backends'])}")
        print(f"Fallback order: {' → '.join(status['backend_order'])}\n")

        result = await tool.execute(objective)

        print("\n=== RESEARCH RESULT ===\n")
        print(f"Backend used: {result.llm_provider}")
        print(f"Status: {result.status}")
        print(f"Duration: {result.duration_seconds:.1f}s")
        print(f"Estimated Cost: ${result.estimated_cost_usd:.4f}")
        print(f"\n{result.summary}\n")
        print(f"Confidence: {result.confidence_score:.0%}")
        print(f"Sources: {len(result.sources)}")
        print(f"Fault Codes: {len(result.fault_codes)}")

        print(f"\nTotal session cost: ${tool._total_cost_usd:.4f}")
        print("=" * 80)

    asyncio.run(main())
