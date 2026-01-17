"""
PhotoPipelineService - Telegram Photo Upload Pipeline Integration (PHOTO-FLOW-001)

Orchestrates the three-stage photo analysis pipeline:
1. Stage 1: Groq screening (always runs) - fast, cheap industrial detection
2. Stage 2: DeepSeek extraction (if Groq >= 0.80) - detailed spec extraction
3. Stage 3: Claude analysis (if equipment matched and KB context) - AI synthesis

Features:
- Cache check before DeepSeek based on photo hash
- Track costs at each stage in trace metadata
- Format response with all relevant data
- Handle each stage failure independently
"""

import base64
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

from rivet_pro.infra.observability import get_logger
from rivet_pro.core.models.screening import ScreeningResult
from rivet_pro.core.models.extraction import ExtractionResult
from rivet_pro.core.services.screening_service import screen_industrial_photo
from rivet_pro.core.services.extraction_service import (
    extract_component_specs,
    compute_photo_hash,
    get_cached_extraction,
)
from rivet_pro.core.services.claude_analyzer import (
    ClaudeAnalyzer,
    AnalysisResult,
    get_claude_analyzer,
)

logger = get_logger(__name__)


@dataclass
class PipelineStageResult:
    """Result from a single pipeline stage."""
    stage: str
    success: bool
    skipped: bool = False
    skip_reason: Optional[str] = None
    cost_usd: float = 0.0
    processing_time_ms: int = 0
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PhotoPipelineResult:
    """
    Complete result from the photo analysis pipeline.

    Contains results from all three stages plus formatted response.

    Attributes:
        screening: Stage 1 Groq screening result
        extraction: Stage 2 DeepSeek extraction result (if screening passed)
        analysis: Stage 3 Claude analysis result (if equipment matched)
        total_cost_usd: Combined cost of all stages
        total_time_ms: Combined processing time
        formatted_response: User-friendly HTML response
        equipment_id: Matched/created equipment UUID (if any)
        equipment_number: Equipment number (if any)
        is_new_equipment: True if equipment was just created
        from_cache: True if extraction came from cache
        stages: List of stage results for trace metadata
    """
    # Stage results
    screening: Optional[ScreeningResult] = None
    extraction: Optional[ExtractionResult] = None
    analysis: Optional[AnalysisResult] = None

    # Aggregate metrics
    total_cost_usd: float = 0.0
    total_time_ms: int = 0

    # Response
    formatted_response: str = ""

    # Equipment info
    equipment_id: Optional[UUID] = None
    equipment_number: Optional[str] = None
    is_new_equipment: bool = False

    # Cache info
    from_cache: bool = False

    # Stage details for tracing
    stages: List[PipelineStageResult] = field(default_factory=list)

    # Error handling
    error: Optional[str] = None
    rejected: bool = False
    rejection_message: Optional[str] = None

    def get_trace_metadata(self) -> Dict[str, Any]:
        """Get metadata for trace logging."""
        return {
            "total_cost_usd": self.total_cost_usd,
            "total_time_ms": self.total_time_ms,
            "from_cache": self.from_cache,
            "rejected": self.rejected,
            "stages": [
                {
                    "stage": s.stage,
                    "success": s.success,
                    "skipped": s.skipped,
                    "skip_reason": s.skip_reason,
                    "cost_usd": s.cost_usd,
                    "processing_time_ms": s.processing_time_ms,
                    "error": s.error,
                }
                for s in self.stages
            ],
            "equipment_id": str(self.equipment_id) if self.equipment_id else None,
            "equipment_number": self.equipment_number,
            "is_new_equipment": self.is_new_equipment,
        }


class PhotoPipelineService:
    """
    Orchestrates the three-stage photo analysis pipeline.

    Stage 1: Groq Screening (always runs)
    - Fast, cheap (~$0.001) industrial equipment detection
    - Filters out non-industrial photos early
    - Confidence >= 0.80 passes to Stage 2

    Stage 2: DeepSeek Extraction (if Groq >= 0.80)
    - Cache check first based on photo hash
    - Detailed spec extraction (~$0.002)
    - Returns manufacturer, model, serial, specs

    Stage 3: Claude Analysis (if equipment matched and KB context)
    - Only for confirmed equipment with KB atoms
    - Synthesizes specs + history + KB into guidance (~$0.01)
    - Provides troubleshooting solutions with citations
    """

    def __init__(self, db, equipment_service=None, work_order_service=None, knowledge_service=None):
        """
        Initialize pipeline service.

        Args:
            db: Database connection
            equipment_service: Optional EquipmentService for matching
            work_order_service: Optional WorkOrderService for history
            knowledge_service: Optional KnowledgeService for KB search
        """
        self.db = db
        self.equipment_service = equipment_service
        self.work_order_service = work_order_service
        self.knowledge_service = knowledge_service
        self.claude_analyzer = get_claude_analyzer()

    async def process_photo(
        self,
        image_bytes: bytes,
        user_id: str,
        telegram_user_id: int,
        equipment_id: Optional[UUID] = None,
        trace=None
    ) -> PhotoPipelineResult:
        """
        Process photo through the three-stage pipeline.

        Args:
            image_bytes: Raw photo bytes
            user_id: User ID string (e.g., "telegram_123")
            telegram_user_id: Telegram user ID for context
            equipment_id: Optional pre-matched equipment UUID
            trace: Optional trace object for observability

        Returns:
            PhotoPipelineResult with all stage results and formatted response
        """
        result = PhotoPipelineResult()
        start_time = datetime.utcnow()

        # Encode image to base64 for API calls
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        photo_hash = compute_photo_hash(image_bytes)

        logger.info(f"Pipeline starting | user={user_id} | hash={photo_hash[:12]}...")

        # ========================================
        # STAGE 1: Groq Screening (always runs)
        # ========================================
        stage1_result = await self._run_stage_1_screening(base64_image, trace)
        result.stages.append(stage1_result)
        result.total_cost_usd += stage1_result.cost_usd
        result.total_time_ms += stage1_result.processing_time_ms

        if not stage1_result.success:
            result.error = stage1_result.error
            result.formatted_response = self._format_error_response(stage1_result.error)
            return result

        result.screening = stage1_result.data.get('screening')

        # Check if photo was rejected (not industrial)
        if not result.screening.passes_threshold:
            result.rejected = True
            result.rejection_message = result.screening.get_user_message()
            result.formatted_response = result.rejection_message

            logger.info(
                f"Photo rejected | user={user_id} | "
                f"industrial={result.screening.is_industrial} | "
                f"confidence={result.screening.confidence:.0%}"
            )
            return result

        # ========================================
        # STAGE 2: DeepSeek Extraction (if Groq >= 0.80)
        # ========================================
        stage2_result = await self._run_stage_2_extraction(
            base64_image, photo_hash, result.screening, trace
        )
        result.stages.append(stage2_result)
        result.total_cost_usd += stage2_result.cost_usd
        result.total_time_ms += stage2_result.processing_time_ms

        if stage2_result.skipped:
            # Shouldn't happen since we checked passes_threshold above
            result.formatted_response = stage2_result.skip_reason or "Extraction skipped"
            return result

        if not stage2_result.success:
            # Continue with partial data if extraction failed
            logger.warning(f"Extraction failed, continuing with screening data: {stage2_result.error}")
            result.extraction = ExtractionResult(
                manufacturer=None,
                model_number=None,
                error=stage2_result.error
            )
        else:
            result.extraction = stage2_result.data.get('extraction')
            result.from_cache = result.extraction.from_cache if result.extraction else False

        # ========================================
        # Equipment Matching (between Stage 2 and 3)
        # ========================================
        if result.extraction and result.extraction.has_model_info and self.equipment_service:
            try:
                eq_id, eq_num, is_new = await self.equipment_service.match_or_create_equipment(
                    manufacturer=result.extraction.manufacturer,
                    model_number=result.extraction.model_number,
                    serial_number=result.extraction.serial_number,
                    equipment_type=result.screening.category,
                    location=None,
                    user_id=user_id
                )
                result.equipment_id = eq_id
                result.equipment_number = eq_num
                result.is_new_equipment = is_new
                equipment_id = eq_id  # Use for stage 3

                logger.info(
                    f"Equipment {'created' if is_new else 'matched'} | "
                    f"equipment_number={eq_num} | user={user_id}"
                )

                if trace:
                    trace.add_step("equipment_match", "success", {
                        "action": "created" if is_new else "matched",
                        "equipment_id": str(eq_id) if eq_id else None,
                        "equipment_number": eq_num,
                        "is_new": is_new
                    })

            except Exception as e:
                logger.error(f"Equipment matching failed: {e}", exc_info=True)
                if trace:
                    trace.add_step("equipment_match", "error", {"error": str(e)})

        # ========================================
        # STAGE 3: Claude Analysis (if equipment matched and KB context found)
        # ========================================
        stage3_result = await self._run_stage_3_analysis(
            equipment_id,
            result.extraction,
            telegram_user_id,
            trace
        )
        result.stages.append(stage3_result)
        result.total_cost_usd += stage3_result.cost_usd
        result.total_time_ms += stage3_result.processing_time_ms

        if stage3_result.success and not stage3_result.skipped:
            result.analysis = stage3_result.data.get('analysis')

        # ========================================
        # Format Final Response
        # ========================================
        result.formatted_response = self._format_pipeline_response(result)
        result.total_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        logger.info(
            f"Pipeline complete | user={user_id} | "
            f"cost=${result.total_cost_usd:.4f} | time={result.total_time_ms}ms | "
            f"equipment={result.equipment_number}"
        )

        return result

    async def _run_stage_1_screening(
        self,
        base64_image: str,
        trace=None
    ) -> PipelineStageResult:
        """
        Run Stage 1: Groq industrial photo screening.

        Always runs first to filter non-industrial photos cheaply.
        """
        stage_result = PipelineStageResult(stage="groq_screening", success=False)

        try:
            screening = await screen_industrial_photo(base64_image)

            stage_result.success = screening.is_successful
            stage_result.cost_usd = screening.cost_usd
            stage_result.processing_time_ms = screening.processing_time_ms
            stage_result.data = {'screening': screening}

            if screening.error:
                stage_result.error = screening.error

            if trace:
                trace.add_step("stage1_groq_screening",
                    "success" if stage_result.success else "error", {
                    "is_industrial": screening.is_industrial,
                    "confidence": screening.confidence,
                    "category": screening.category,
                    "passes_threshold": screening.passes_threshold,
                    "cost_usd": screening.cost_usd,
                    "processing_time_ms": screening.processing_time_ms,
                    "error": screening.error
                })

            logger.info(
                f"Stage 1 complete | industrial={screening.is_industrial} | "
                f"confidence={screening.confidence:.0%} | category={screening.category} | "
                f"cost=${screening.cost_usd:.4f} | time={screening.processing_time_ms}ms"
            )

        except Exception as e:
            stage_result.error = str(e)
            logger.error(f"Stage 1 screening failed: {e}", exc_info=True)
            if trace:
                trace.add_step("stage1_groq_screening", "error", {"error": str(e)})

        return stage_result

    async def _run_stage_2_extraction(
        self,
        base64_image: str,
        photo_hash: str,
        screening: ScreeningResult,
        trace=None
    ) -> PipelineStageResult:
        """
        Run Stage 2: DeepSeek component specification extraction.

        Only runs if Stage 1 confidence >= 0.80.
        Checks cache first based on photo hash.
        """
        stage_result = PipelineStageResult(stage="deepseek_extraction", success=False)

        # Check if screening passed
        if not screening.passes_threshold:
            stage_result.skipped = True
            stage_result.skip_reason = f"Screening confidence {screening.confidence:.0%} below 80% threshold"
            if trace:
                trace.add_step("stage2_deepseek_extraction", "skipped", {
                    "reason": stage_result.skip_reason
                })
            return stage_result

        try:
            # Check cache first
            if self.db:
                cached = await get_cached_extraction(self.db, photo_hash)
                if cached:
                    stage_result.success = True
                    stage_result.cost_usd = 0.0  # No cost for cache hit
                    stage_result.processing_time_ms = 0
                    stage_result.data = {'extraction': cached}

                    logger.info(f"Stage 2 cache HIT | hash={photo_hash[:12]}...")

                    if trace:
                        trace.add_step("stage2_deepseek_extraction", "cache_hit", {
                            "from_cache": True,
                            "manufacturer": cached.manufacturer,
                            "model_number": cached.model_number,
                            "confidence": cached.confidence
                        })

                    return stage_result

            # Run extraction
            extraction = await extract_component_specs(
                base64_image,
                screening,
                db=self.db
            )

            stage_result.success = extraction.is_successful
            stage_result.cost_usd = extraction.cost_usd
            stage_result.processing_time_ms = extraction.processing_time_ms
            stage_result.data = {'extraction': extraction}

            if extraction.error:
                stage_result.error = extraction.error

            if trace:
                trace.add_step("stage2_deepseek_extraction",
                    "success" if stage_result.success else "error", {
                    "manufacturer": extraction.manufacturer,
                    "model_number": extraction.model_number,
                    "serial_number": extraction.serial_number,
                    "confidence": extraction.confidence,
                    "cost_usd": extraction.cost_usd,
                    "processing_time_ms": extraction.processing_time_ms,
                    "from_cache": extraction.from_cache,
                    "error": extraction.error
                })

            logger.info(
                f"Stage 2 complete | manufacturer={extraction.manufacturer} | "
                f"model={extraction.model_number} | confidence={extraction.confidence:.0%} | "
                f"cost=${extraction.cost_usd:.4f} | time={extraction.processing_time_ms}ms"
            )

        except Exception as e:
            stage_result.error = str(e)
            logger.error(f"Stage 2 extraction failed: {e}", exc_info=True)
            if trace:
                trace.add_step("stage2_deepseek_extraction", "error", {"error": str(e)})

        return stage_result

    async def _run_stage_3_analysis(
        self,
        equipment_id: Optional[UUID],
        extraction: Optional[ExtractionResult],
        telegram_user_id: int,
        trace=None
    ) -> PipelineStageResult:
        """
        Run Stage 3: Claude AI analysis and KB synthesis.

        Only runs if:
        - Equipment was matched/created (equipment_id exists)
        - KB context is found for the equipment
        """
        stage_result = PipelineStageResult(stage="claude_analysis", success=False)

        # Check if we have equipment to analyze
        if not equipment_id:
            stage_result.skipped = True
            stage_result.skip_reason = "No equipment matched/created"
            if trace:
                trace.add_step("stage3_claude_analysis", "skipped", {
                    "reason": stage_result.skip_reason
                })
            return stage_result

        try:
            # Get maintenance history
            history = []
            if self.work_order_service:
                try:
                    history = await self.work_order_service.get_equipment_maintenance_history(
                        equipment_id=equipment_id,
                        days=90
                    )
                except Exception as e:
                    logger.warning(f"Failed to get maintenance history: {e}")

            # Get KB context
            kb_context = []
            if self.knowledge_service and extraction:
                try:
                    # Search KB for relevant atoms
                    query = f"{extraction.manufacturer or ''} {extraction.model_number or ''}"
                    kb_context = await self._search_kb_for_equipment(
                        manufacturer=extraction.manufacturer,
                        model_number=extraction.model_number
                    )
                except Exception as e:
                    logger.warning(f"Failed to search KB: {e}")

            # Skip if no KB context found
            if not kb_context:
                stage_result.skipped = True
                stage_result.skip_reason = "No KB context found for equipment"
                if trace:
                    trace.add_step("stage3_claude_analysis", "skipped", {
                        "reason": stage_result.skip_reason,
                        "equipment_id": str(equipment_id)
                    })
                return stage_result

            # Build specs dict from extraction
            specs = {}
            if extraction:
                specs = {
                    "manufacturer": extraction.manufacturer,
                    "model_number": extraction.model_number,
                    "serial_number": extraction.serial_number,
                    **(extraction.specs or {})
                }

            # Run Claude analysis
            analysis = await self.claude_analyzer.analyze_with_kb(
                equipment_id=equipment_id,
                specs=specs,
                history=history,
                kb_context=kb_context
            )

            stage_result.success = True
            stage_result.cost_usd = analysis.cost_usd
            stage_result.data = {'analysis': analysis}

            if trace:
                trace.add_step("stage3_claude_analysis", "success", {
                    "equipment_id": str(equipment_id),
                    "history_count": len(history),
                    "kb_context_count": len(kb_context),
                    "confidence": analysis.confidence,
                    "cost_usd": analysis.cost_usd,
                    "solutions_count": len(analysis.solutions),
                    "safety_warnings_count": len(analysis.safety_warnings)
                })

            logger.info(
                f"Stage 3 complete | equipment_id={equipment_id} | "
                f"history={len(history)} | kb_atoms={len(kb_context)} | "
                f"cost=${analysis.cost_usd:.4f}"
            )

        except Exception as e:
            stage_result.error = str(e)
            logger.error(f"Stage 3 analysis failed: {e}", exc_info=True)
            if trace:
                trace.add_step("stage3_claude_analysis", "error", {"error": str(e)})

        return stage_result

    async def _search_kb_for_equipment(
        self,
        manufacturer: Optional[str],
        model_number: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Search knowledge base for relevant atoms.

        Returns list of KB atom dicts for Claude analysis context.
        """
        if not self.db or not manufacturer:
            return []

        try:
            # Simple query for atoms matching manufacturer/model
            results = await self.db.fetch(
                """
                SELECT atom_id, title, content, source_url, type, confidence
                FROM knowledge_atoms
                WHERE (
                    LOWER(manufacturer) = LOWER($1)
                    OR LOWER(content) LIKE LOWER($2)
                )
                AND confidence >= 0.5
                ORDER BY confidence DESC, usage_count DESC
                LIMIT 5
                """,
                manufacturer,
                f"%{model_number}%" if model_number else "%"
            )

            return [dict(r) for r in results] if results else []

        except Exception as e:
            logger.error(f"KB search failed: {e}")
            return []

    def _format_pipeline_response(self, result: PhotoPipelineResult) -> str:
        """
        Format the complete pipeline result into user-friendly HTML response.

        Includes all relevant data from all stages.
        """
        parts = []

        # Header with screening category
        category = result.screening.category if result.screening else "equipment"
        confidence_emoji = "✅" if (result.extraction and result.extraction.confidence >= 0.85) else "⚠️"

        parts.append(f"{confidence_emoji} <b>Equipment Identified</b> ({category})")
        parts.append("")

        # Extraction details
        if result.extraction and result.extraction.has_model_info:
            if result.extraction.manufacturer:
                parts.append(f"<b>Manufacturer:</b> {result.extraction.manufacturer}")
            if result.extraction.model_number:
                parts.append(f"<b>Model:</b> {result.extraction.model_number}")
            if result.extraction.serial_number:
                parts.append(f"<b>Serial:</b> {result.extraction.serial_number}")
            parts.append(f"<b>Confidence:</b> {result.extraction.confidence:.0%}")

            # Key specs
            if result.extraction.specs:
                spec_parts = []
                for key in ["voltage", "current", "horsepower", "rpm", "phase"]:
                    if key in result.extraction.specs and result.extraction.specs[key]:
                        spec_parts.append(f"{key.title()}: {result.extraction.specs[key]}")
                if spec_parts:
                    parts.append("")
                    parts.append("<b>Specifications:</b>")
                    for sp in spec_parts:
                        parts.append(f"• {sp}")

        # Equipment info
        if result.equipment_number:
            status = "🆕 Created" if result.is_new_equipment else "✓ Matched"
            parts.append("")
            parts.append(f"<b>Equipment ID:</b> {result.equipment_number} ({status})")

        # Claude analysis (if available)
        if result.analysis and result.analysis.analysis:
            parts.append("")
            parts.append("━━━━━━━━━━━━━━━━━━━━")
            parts.append("🤖 <b>AI Analysis</b>")
            parts.append("")

            # Truncate analysis if too long
            analysis_text = result.analysis.analysis
            if len(analysis_text) > 500:
                analysis_text = analysis_text[:500] + "..."
            parts.append(analysis_text)

            # Solutions
            if result.analysis.solutions:
                parts.append("")
                parts.append("<b>Recommended Solutions:</b>")
                for i, solution in enumerate(result.analysis.solutions[:3], 1):
                    parts.append(f"{i}. {solution}")

            # Safety warnings
            if result.analysis.safety_warnings:
                parts.append("")
                parts.append("⚠️ <b>Safety Warnings:</b>")
                for warning in result.analysis.safety_warnings[:2]:
                    parts.append(f"• {warning}")

            # Citations
            if result.analysis.kb_citations:
                parts.append("")
                parts.append("📚 <b>Sources:</b>")
                for citation in result.analysis.kb_citations[:3]:
                    if citation.get('url'):
                        parts.append(f"• <a href=\"{citation['url']}\">{citation.get('title', 'Source')}</a>")
                    else:
                        parts.append(f"• {citation.get('title', 'Knowledge Base')}")

        # Cache indicator
        if result.from_cache:
            parts.append("")
            parts.append("<i>📦 Results from cache (instant response)</i>")

        # Cost tracking (for debugging, can be removed in prod)
        # parts.append("")
        # parts.append(f"<i>Cost: ${result.total_cost_usd:.4f} | Time: {result.total_time_ms}ms</i>")

        return "\n".join(parts)

    def _format_error_response(self, error: str) -> str:
        """Format error message for user."""
        return (
            f"❌ <b>Analysis Failed</b>\n\n"
            f"{error}\n\n"
            "Please try again with a clearer photo."
        )


# Module-level singleton
_pipeline_service: Optional[PhotoPipelineService] = None


def get_photo_pipeline_service(
    db=None,
    equipment_service=None,
    work_order_service=None,
    knowledge_service=None
) -> PhotoPipelineService:
    """Get or create the PhotoPipelineService singleton."""
    global _pipeline_service
    if _pipeline_service is None:
        _pipeline_service = PhotoPipelineService(
            db=db,
            equipment_service=equipment_service,
            work_order_service=work_order_service,
            knowledge_service=knowledge_service
        )
    return _pipeline_service
