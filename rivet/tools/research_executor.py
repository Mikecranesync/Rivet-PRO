"""
ResearchExecutorTool - Long-running autonomous research agent for Agent Factory
Delegates complex research tasks to OpenHands for manufacturer lookups,
documentation compilation, and knowledge gap filling.

Usage:
    from rivet.tools.research_executor import ResearchExecutorTool

    tool = ResearchExecutorTool(llm_provider="ollama")  # or "anthropic", "openai"
    result = await tool.execute(ResearchTask(
        objective="Research Lenze VFD fault codes",
        manufacturer="Lenze",
        equipment_type="VFD",
        specific_queries=["fault code F0001", "parameter settings"]
    ))
"""

import asyncio
import json
import logging
import os
import tempfile
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration & Enums
# ============================================================================

class LLMProvider(str, Enum):
    """Supported LLM providers for research tasks"""
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"


class ResearchStatus(str, Enum):
    """Status of a research task"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ResearchPriority(str, Enum):
    """Priority levels for research tasks"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# Pydantic Models
# ============================================================================

class ResearchTask(BaseModel):
    """Input model for research requests"""
    objective: str = Field(..., description="Primary research objective")
    manufacturer: Optional[str] = Field(None, description="Target manufacturer name")
    equipment_type: Optional[str] = Field(None, description="Equipment category (VFD, PLC, Motor, etc)")
    model_number: Optional[str] = Field(None, description="Specific model if known")
    specific_queries: List[str] = Field(default_factory=list, description="Specific questions to answer")
    context: Optional[str] = Field(None, description="Additional context from conversation")
    priority: ResearchPriority = Field(default=ResearchPriority.MEDIUM)
    timeout_minutes: int = Field(default=30, ge=5, le=120)
    max_sources: int = Field(default=10, ge=1, le=50)

    class Config:
        use_enum_values = True


class ResearchSource(BaseModel):
    """A source discovered during research"""
    url: str
    title: str
    source_type: str = Field(..., description="pdf, webpage, manual, forum, datasheet")
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    extracted_content: Optional[str] = None
    citation_key: str = Field(..., description="Citation key like [^1]")
    accessed_at: datetime = Field(default_factory=datetime.utcnow)


class ExtractedFaultCode(BaseModel):
    """Structured fault code extracted from research"""
    code: str
    description: str
    possible_causes: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    severity: Optional[str] = None
    source_citation: str


class ExtractedParameter(BaseModel):
    """Equipment parameter extracted from research"""
    parameter_id: str
    name: str
    description: str
    default_value: Optional[str] = None
    valid_range: Optional[str] = None
    unit: Optional[str] = None
    source_citation: str


class ResearchResult(BaseModel):
    """Output model for completed research"""
    task_id: str
    status: ResearchStatus
    objective: str

    # Core findings
    summary: str = Field(..., description="Executive summary of findings")
    detailed_findings: str = Field(..., description="Full research output with citations")

    # Structured extractions
    fault_codes: List[ExtractedFaultCode] = Field(default_factory=list)
    parameters: List[ExtractedParameter] = Field(default_factory=list)
    troubleshooting_steps: List[str] = Field(default_factory=list)

    # Sources and citations
    sources: List[ResearchSource] = Field(default_factory=list)
    citations_markdown: str = Field(default="", description="Formatted citation block")

    # Metadata
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    llm_provider: str
    total_tokens_used: Optional[int] = None
    estimated_cost_usd: Optional[float] = None

    # For knowledge base integration
    suggested_atom_title: Optional[str] = None
    suggested_atom_content: Optional[str] = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)

    class Config:
        use_enum_values = True


class ResearchExecutorConfig(BaseModel):
    """Configuration for the research executor"""
    default_provider: LLMProvider = LLMProvider.OLLAMA
    ollama_model: str = "deepseek-coder:6.7b"
    ollama_base_url: str = "http://localhost:11434"
    anthropic_model: str = "claude-sonnet-4-20250514"
    openai_model: str = "gpt-4o"
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    # Execution settings
    max_concurrent_tasks: int = 3
    default_timeout_minutes: int = 30
    workspace_base_path: str = "/tmp/research_workspaces"

    # Research behavior
    enable_web_browsing: bool = True
    enable_pdf_extraction: bool = True
    enable_code_execution: bool = True
    max_browser_pages: int = 20

    class Config:
        use_enum_values = True


# ============================================================================
# Research Executor Tool
# ============================================================================

class ResearchExecutorTool:
    """
    Long-running autonomous research agent using OpenHands SDK.

    Designed for Agent Factory integration - delegates complex research tasks
    that require web browsing, document analysis, and multi-step reasoning.

    Example use cases:
    - Research unknown equipment manufacturers
    - Compile fault code documentation
    - Fill knowledge base gaps
    - Generate technical summaries from multiple sources
    """

    name = "research_executor"
    description = """Autonomous research agent for complex, multi-step research tasks.
    Use when you need to:
    - Research unknown manufacturers or equipment
    - Compile documentation from multiple sources
    - Extract structured data (fault codes, parameters) from technical docs
    - Fill knowledge gaps that require web research

    NOT for: Simple lookups, single-page fetches, or tasks under 5 minutes."""

    def __init__(
        self,
        config: Optional[ResearchExecutorConfig] = None,
        llm_provider: Optional[str] = None,
    ):
        self.config = config or ResearchExecutorConfig()

        # Override provider if specified
        if llm_provider:
            self.config.default_provider = LLMProvider(llm_provider)

        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._results_cache: Dict[str, ResearchResult] = {}

        # Ensure workspace exists
        Path(self.config.workspace_base_path).mkdir(parents=True, exist_ok=True)

        logger.info(f"ResearchExecutorTool initialized with provider: {self.config.default_provider}")

    def _get_llm_config(self, provider: Optional[LLMProvider] = None) -> Dict[str, Any]:
        """Get LLM configuration for OpenHands"""
        provider = provider or self.config.default_provider

        if provider == LLMProvider.OLLAMA:
            return {
                "model": f"ollama/{self.config.ollama_model}",
                "base_url": self.config.ollama_base_url,
                "api_key": "ollama",  # Ollama doesn't need a real key
            }
        elif provider == LLMProvider.ANTHROPIC:
            return {
                "model": f"anthropic/{self.config.anthropic_model}",
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
            }
        elif provider == LLMProvider.OPENAI:
            return {
                "model": f"openai/{self.config.openai_model}",
                "api_key": os.getenv("OPENAI_API_KEY"),
            }
        elif provider == LLMProvider.DEEPSEEK:
            return {
                "model": self.config.deepseek_model,
                "base_url": self.config.deepseek_base_url,
                "api_key": os.getenv("DEEPSEEK_API_KEY"),
            }
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _build_research_prompt(self, task: ResearchTask) -> str:
        """Build the research prompt for OpenHands agent"""

        prompt_parts = [
            "# Research Task",
            "",
            f"**Objective:** {task.objective}",
            "",
        ]

        if task.manufacturer:
            prompt_parts.append(f"**Manufacturer:** {task.manufacturer}")
        if task.equipment_type:
            prompt_parts.append(f"**Equipment Type:** {task.equipment_type}")
        if task.model_number:
            prompt_parts.append(f"**Model:** {task.model_number}")

        if task.specific_queries:
            prompt_parts.extend([
                "",
                "## Specific Questions to Answer",
                "",
            ])
            for i, query in enumerate(task.specific_queries, 1):
                prompt_parts.append(f"{i}. {query}")

        if task.context:
            prompt_parts.extend([
                "",
                "## Additional Context",
                "",
                task.context,
            ])

        prompt_parts.extend([
            "",
            "## Research Instructions",
            "",
            "1. **Search Strategy**: Start with official manufacturer documentation, then technical forums, then general sources.",
            "2. **Source Priority**: Prefer official manuals > datasheets > application notes > forums > general web",
            "3. **Citation Format**: Use footnote citations [^1], [^2], etc. for EVERY factual claim",
            "4. **Extract Structure**: When you find fault codes or parameters, extract them in structured format",
            "5. **Quality Check**: Verify information across multiple sources when possible",
            "",
            "## Required Output Format",
            "",
            "Provide your findings as JSON with this structure:",
            "```json",
            "{",
            '  "summary": "Executive summary (2-3 sentences)",',
            '  "detailed_findings": "Full findings with [^N] citations",',
            '  "fault_codes": [{"code": "F001", "description": "...", "possible_causes": [...], "recommended_actions": [...], "source_citation": "[^1]"}],',
            '  "parameters": [{"parameter_id": "P001", "name": "...", "description": "...", "source_citation": "[^2]"}],',
            '  "troubleshooting_steps": ["Step 1...", "Step 2..."],',
            '  "sources": [{"url": "https://...", "title": "...", "source_type": "manual|datasheet|forum|webpage", "citation_key": "[^1]"}],',
            '  "suggested_atom_title": "Title for knowledge base entry",',
            '  "suggested_atom_content": "Formatted content for knowledge atom with citations",',
            '  "confidence_score": 0.85',
            "}",
            "```",
            "",
            f"**Time Budget:** {task.timeout_minutes} minutes",
            f"**Max Sources:** {task.max_sources}",
        ])

        return "\n".join(prompt_parts)

    async def execute(
        self,
        task: Union[ResearchTask, Dict[str, Any], str],
        provider: Optional[LLMProvider] = None,
    ) -> ResearchResult:
        """
        Execute a research task asynchronously.

        Args:
            task: ResearchTask, dict, or simple string objective
            provider: Override the default LLM provider

        Returns:
            ResearchResult with findings, sources, and structured extractions
        """
        # Normalize input
        if isinstance(task, str):
            task = ResearchTask(objective=task)
        elif isinstance(task, dict):
            task = ResearchTask(**task)

        task_id = f"research_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{id(task)}"
        started_at = datetime.utcnow()

        logger.info(f"Starting research task {task_id}: {task.objective[:100]}...")

        try:
            # Build the research prompt
            prompt = self._build_research_prompt(task)

            # Get LLM config
            llm_config = self._get_llm_config(provider)

            # Execute via OpenHands SDK
            result_data = await self._execute_openhands(
                task_id=task_id,
                prompt=prompt,
                llm_config=llm_config,
                timeout_minutes=task.timeout_minutes,
            )

            completed_at = datetime.utcnow()
            duration = (completed_at - started_at).total_seconds()

            # Parse and structure the result
            result = self._parse_research_output(
                task_id=task_id,
                task=task,
                raw_output=result_data,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                llm_provider=str(provider or self.config.default_provider),
            )

            # Cache result
            self._results_cache[task_id] = result

            logger.info(f"Research task {task_id} completed in {duration:.1f}s with {len(result.sources)} sources")

            return result

        except asyncio.TimeoutError:
            logger.error(f"Research task {task_id} timed out after {task.timeout_minutes} minutes")
            return ResearchResult(
                task_id=task_id,
                status=ResearchStatus.TIMEOUT,
                objective=task.objective,
                summary=f"Research timed out after {task.timeout_minutes} minutes",
                detailed_findings="",
                started_at=started_at,
                completed_at=datetime.utcnow(),
                llm_provider=str(provider or self.config.default_provider),
            )

        except Exception as e:
            logger.exception(f"Research task {task_id} failed: {e}")
            return ResearchResult(
                task_id=task_id,
                status=ResearchStatus.FAILED,
                objective=task.objective,
                summary=f"Research failed: {str(e)}",
                detailed_findings="",
                started_at=started_at,
                completed_at=datetime.utcnow(),
                llm_provider=str(provider or self.config.default_provider),
            )

    async def _execute_openhands(
        self,
        task_id: str,
        prompt: str,
        llm_config: Dict[str, Any],
        timeout_minutes: int,
    ) -> Dict[str, Any]:
        """
        Execute research via OpenHands SDK.

        This is the integration point - replace with actual OpenHands SDK calls.
        """
        try:
            # Try to import OpenHands SDK
            from openhands.sdk import LLM, Agent, Conversation, Tool
            from openhands.tools.browser import BrowserTool
            from openhands.tools.terminal import TerminalTool
            from openhands.tools.file_editor import FileEditorTool

            # Create workspace for this task
            workspace = Path(self.config.workspace_base_path) / task_id
            workspace.mkdir(parents=True, exist_ok=True)

            # Initialize LLM
            llm = LLM(
                model=llm_config["model"],
                api_key=llm_config.get("api_key"),
                base_url=llm_config.get("base_url"),
            )

            # Configure tools
            tools = [Tool(name=TerminalTool.name)]

            if self.config.enable_web_browsing:
                tools.append(Tool(name=BrowserTool.name))

            tools.append(Tool(name=FileEditorTool.name))

            # Create agent
            agent = Agent(llm=llm, tools=tools)

            # Create conversation and execute
            conversation = Conversation(
                agent=agent,
                workspace=str(workspace),
            )

            # Execute with timeout
            result = await asyncio.wait_for(
                conversation.send(prompt),
                timeout=timeout_minutes * 60
            )

            # Parse JSON from response
            return self._extract_json_from_response(result.content)

        except ImportError:
            # OpenHands SDK not installed - use fallback
            logger.warning("OpenHands SDK not installed, using fallback research method")
            return await self._fallback_research(prompt, llm_config, timeout_minutes)

    async def _fallback_research(
        self,
        prompt: str,
        llm_config: Dict[str, Any],
        timeout_minutes: int,
    ) -> Dict[str, Any]:
        """
        Fallback research method when OpenHands SDK is not available.
        Uses direct LLM calls with web search tool.
        """
        try:
            # Try LangChain for fallback
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_community.tools import DuckDuckGoSearchRun

            # Determine which LLM to use
            model = llm_config["model"]

            if "ollama" in model:
                from langchain_ollama import ChatOllama
                llm = ChatOllama(
                    model=model.replace("ollama/", ""),
                    base_url=llm_config.get("base_url", "http://localhost:11434"),
                )
            elif "anthropic" in model:
                from langchain_anthropic import ChatAnthropic
                llm = ChatAnthropic(
                    model=model.replace("anthropic/", ""),
                    api_key=llm_config["api_key"],
                )
            elif "openai" in model:
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(
                    model=model.replace("openai/", ""),
                    api_key=llm_config["api_key"],
                )
            else:
                # Default to OpenAI-compatible
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(
                    model=model,
                    base_url=llm_config.get("base_url"),
                    api_key=llm_config.get("api_key", "not-needed"),
                )

            # Initialize search tool
            search = DuckDuckGoSearchRun()

            # Build system prompt for research
            system_prompt = """You are an expert industrial equipment researcher.
Your task is to research technical documentation and compile accurate, well-cited information.

When researching:
1. Use the search tool to find relevant sources
2. Prioritize official manufacturer documentation
3. Extract structured information (fault codes, parameters)
4. Cite every factual claim with [^N] notation
5. Return results as valid JSON

Always verify information across multiple sources when possible."""

            # Execute research in steps
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt),
            ]

            # Get initial response
            response = await llm.ainvoke(messages)

            # Try to extract JSON
            return self._extract_json_from_response(response.content)

        except Exception as e:
            logger.error(f"Fallback research failed: {e}")
            # Return minimal result
            return {
                "summary": f"Research could not be completed: {str(e)}",
                "detailed_findings": "",
                "fault_codes": [],
                "parameters": [],
                "troubleshooting_steps": [],
                "sources": [],
                "confidence_score": 0.0,
            }

    def _extract_json_from_response(self, content: str) -> Dict[str, Any]:
        """Extract JSON from LLM response, handling markdown code blocks"""
        import re

        # Try to find JSON in code blocks first
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to parse the whole content as JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in content
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Return content as summary if no JSON found
        return {
            "summary": content[:500] if len(content) > 500 else content,
            "detailed_findings": content,
            "fault_codes": [],
            "parameters": [],
            "troubleshooting_steps": [],
            "sources": [],
            "confidence_score": 0.3,
        }

    def _parse_research_output(
        self,
        task_id: str,
        task: ResearchTask,
        raw_output: Dict[str, Any],
        started_at: datetime,
        completed_at: datetime,
        duration_seconds: float,
        llm_provider: str,
    ) -> ResearchResult:
        """Parse raw research output into structured ResearchResult"""

        # Parse fault codes
        fault_codes = []
        for fc in raw_output.get("fault_codes", []):
            try:
                fault_codes.append(ExtractedFaultCode(
                    code=fc.get("code", ""),
                    description=fc.get("description", ""),
                    possible_causes=fc.get("possible_causes", []),
                    recommended_actions=fc.get("recommended_actions", []),
                    severity=fc.get("severity"),
                    source_citation=fc.get("source_citation", ""),
                ))
            except Exception as e:
                logger.warning(f"Failed to parse fault code: {e}")

        # Parse parameters
        parameters = []
        for param in raw_output.get("parameters", []):
            try:
                parameters.append(ExtractedParameter(
                    parameter_id=param.get("parameter_id", ""),
                    name=param.get("name", ""),
                    description=param.get("description", ""),
                    default_value=param.get("default_value"),
                    valid_range=param.get("valid_range"),
                    unit=param.get("unit"),
                    source_citation=param.get("source_citation", ""),
                ))
            except Exception as e:
                logger.warning(f"Failed to parse parameter: {e}")

        # Parse sources
        sources = []
        for i, src in enumerate(raw_output.get("sources", []), 1):
            try:
                sources.append(ResearchSource(
                    url=src.get("url", ""),
                    title=src.get("title", f"Source {i}"),
                    source_type=src.get("source_type", "webpage"),
                    relevance_score=src.get("relevance_score", 0.5),
                    extracted_content=src.get("extracted_content"),
                    citation_key=src.get("citation_key", f"[^{i}]"),
                ))
            except Exception as e:
                logger.warning(f"Failed to parse source: {e}")

        # Build citations markdown
        citations_md = "\n\n## Sources\n\n"
        for src in sources:
            citations_md += f"{src.citation_key}: [{src.title}]({src.url})\n"

        return ResearchResult(
            task_id=task_id,
            status=ResearchStatus.COMPLETED,
            objective=task.objective,
            summary=raw_output.get("summary", "Research completed"),
            detailed_findings=raw_output.get("detailed_findings", ""),
            fault_codes=fault_codes,
            parameters=parameters,
            troubleshooting_steps=raw_output.get("troubleshooting_steps", []),
            sources=sources,
            citations_markdown=citations_md,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            llm_provider=llm_provider,
            suggested_atom_title=raw_output.get("suggested_atom_title"),
            suggested_atom_content=raw_output.get("suggested_atom_content"),
            confidence_score=raw_output.get("confidence_score", 0.5),
        )

    # ========================================================================
    # Convenience methods for common research patterns
    # ========================================================================

    async def research_manufacturer(
        self,
        manufacturer: str,
        equipment_type: str,
        specific_model: Optional[str] = None,
    ) -> ResearchResult:
        """Research a specific manufacturer's equipment"""
        task = ResearchTask(
            objective=f"Research {manufacturer} {equipment_type} documentation and fault codes",
            manufacturer=manufacturer,
            equipment_type=equipment_type,
            model_number=specific_model,
            specific_queries=[
                f"Official {manufacturer} documentation and manuals",
                "Common fault codes and error messages",
                "Troubleshooting procedures",
                "Parameter settings and configuration",
            ],
            priority=ResearchPriority.HIGH,
        )
        return await self.execute(task)

    async def research_fault_code(
        self,
        manufacturer: str,
        equipment_type: str,
        fault_code: str,
    ) -> ResearchResult:
        """Research a specific fault code"""
        task = ResearchTask(
            objective=f"Research {manufacturer} {equipment_type} fault code {fault_code}",
            manufacturer=manufacturer,
            equipment_type=equipment_type,
            specific_queries=[
                f"What does fault code {fault_code} mean?",
                f"What causes {fault_code}?",
                f"How to fix {fault_code}?",
                f"Related fault codes",
            ],
            priority=ResearchPriority.CRITICAL,
            timeout_minutes=15,  # Shorter timeout for specific lookups
        )
        return await self.execute(task)

    async def fill_knowledge_gap(
        self,
        gap_description: str,
        context: Optional[str] = None,
    ) -> ResearchResult:
        """Fill a detected knowledge gap"""
        task = ResearchTask(
            objective=f"Fill knowledge gap: {gap_description}",
            context=context,
            specific_queries=[
                "Find authoritative sources on this topic",
                "Extract key technical information",
                "Compile into structured knowledge atom format",
            ],
            priority=ResearchPriority.MEDIUM,
        )
        return await self.execute(task)


# ============================================================================
# LangChain Tool Wrapper (for Agent Factory integration)
# ============================================================================

def create_langchain_tool(config: Optional[ResearchExecutorConfig] = None):
    """Create a LangChain-compatible tool wrapper"""
    from langchain_core.tools import StructuredTool

    executor = ResearchExecutorTool(config=config)

    async def _research_wrapper(
        objective: str,
        manufacturer: Optional[str] = None,
        equipment_type: Optional[str] = None,
        specific_queries: Optional[List[str]] = None,
    ) -> str:
        """Execute autonomous research task"""
        task = ResearchTask(
            objective=objective,
            manufacturer=manufacturer,
            equipment_type=equipment_type,
            specific_queries=specific_queries or [],
        )
        result = await executor.execute(task)

        # Return formatted result for agent consumption
        return f"""## Research Results

**Status:** {result.status}
**Confidence:** {result.confidence_score:.0%}

### Summary
{result.summary}

### Findings
{result.detailed_findings}

### Fault Codes Found
{chr(10).join(f'- **{fc.code}**: {fc.description}' for fc in result.fault_codes) or 'None extracted'}

### Sources
{result.citations_markdown}
"""

    return StructuredTool.from_function(
        coroutine=_research_wrapper,
        name="research_executor",
        description=ResearchExecutorTool.description,
    )


# ============================================================================
# CLI for testing
# ============================================================================

if __name__ == "__main__":
    import sys

    async def main():
        # Example usage
        executor = ResearchExecutorTool(llm_provider="ollama")

        if len(sys.argv) > 1:
            objective = " ".join(sys.argv[1:])
        else:
            objective = "Research Siemens S7-1200 PLC common fault codes and troubleshooting"

        print(f"Researching: {objective}\n")

        result = await executor.execute(ResearchTask(
            objective=objective,
            timeout_minutes=15,
        ))

        print(f"Status: {result.status}")
        print(f"Duration: {result.duration_seconds:.1f}s")
        print(f"Confidence: {result.confidence_score:.0%}")
        print(f"\nSummary:\n{result.summary}")
        print(f"\nSources: {len(result.sources)}")
        for src in result.sources:
            print(f"  {src.citation_key} {src.title}")

        if result.fault_codes:
            print(f"\nFault Codes: {len(result.fault_codes)}")
            for fc in result.fault_codes[:5]:
                print(f"  - {fc.code}: {fc.description[:80]}...")

    asyncio.run(main())
