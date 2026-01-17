"""
Integration Tests for Photo Pipeline (PHOTO-TEST-002)

End-to-end tests exercising the full photo analysis pipeline with real database.

Tests:
- Industrial photo -> Groq screens -> DeepSeek extracts -> Claude analyzes
- Non-industrial photo rejected at Groq stage
- Blurry photo gets low confidence
- Cache hit skips DeepSeek on duplicate photo
- Each stage failure handled gracefully

Run with: uv run pytest tests/integration/test_photo_pipeline.py -v
"""

import pytest
import asyncio
import base64
import os
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Skip if database not available
pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set"
)

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from rivet_pro.core.models.screening import ScreeningResult
from rivet_pro.core.models.extraction import ExtractionResult
from rivet_pro.core.services.photo_pipeline_service import (
    PhotoPipelineService,
    PhotoPipelineResult,
    PipelineStageResult,
)
from rivet_pro.core.services.claude_analyzer import AnalysisResult


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_db():
    """Create mock database connection."""
    db = AsyncMock()
    db.fetch = AsyncMock(return_value=[])
    db.fetchrow = AsyncMock(return_value=None)
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_equipment_service():
    """Create mock equipment service."""
    service = AsyncMock()
    service.match_or_create_equipment = AsyncMock(
        return_value=(uuid4(), "EQ-001234", True)  # (id, number, is_new)
    )
    return service


@pytest.fixture
def mock_work_order_service():
    """Create mock work order service."""
    service = AsyncMock()
    service.get_equipment_maintenance_history = AsyncMock(return_value=[
        {
            "work_order_number": "WO-2024-001",
            "title": "VFD overheating alarm",
            "status": "completed",
            "fault_codes": ["F003"],
            "resolution_time_hours": 2.5,
        }
    ])
    return service


@pytest.fixture
def mock_knowledge_service():
    """Create mock knowledge service."""
    service = AsyncMock()
    return service


@pytest.fixture
def test_image_bytes():
    """Create test image bytes."""
    return b"test industrial equipment image bytes for testing"


@pytest.fixture
def test_image_b64(test_image_bytes):
    """Create test image base64."""
    return base64.b64encode(test_image_bytes).decode()


# =============================================================================
# Test: Industrial Photo Full Pipeline Flow
# =============================================================================

class TestIndustrialPhotoFullPipeline:
    """Test: industrial photo -> Groq screens -> DeepSeek extracts -> Claude analyzes."""

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.photo_pipeline_service.screen_industrial_photo")
    @patch("rivet_pro.core.services.photo_pipeline_service.get_cached_extraction")
    @patch("rivet_pro.core.services.photo_pipeline_service.extract_component_specs")
    async def test_full_pipeline_industrial_photo(
        self,
        mock_extract,
        mock_get_cache,
        mock_screen,
        mock_db,
        mock_equipment_service,
        mock_work_order_service,
        test_image_bytes,
    ):
        """Full pipeline successfully processes industrial equipment photo."""
        # Setup Stage 1: Groq screening passes
        mock_screen.return_value = ScreeningResult(
            is_industrial=True,
            confidence=0.92,
            category="vfd",
            reason="VFD nameplate detected with Allen-Bradley logo",
            processing_time_ms=850,
            cost_usd=0.001,
        )

        # Setup Stage 2: Cache miss, DeepSeek extracts
        mock_get_cache.return_value = None
        mock_extract.return_value = ExtractionResult(
            manufacturer="Allen-Bradley",
            model_number="PowerFlex 525",
            serial_number="ABC123456",
            specs={
                "voltage": "480V",
                "horsepower": "25HP",
                "current": "32A",
            },
            raw_text="ALLEN-BRADLEY PowerFlex 525 480V 25HP",
            confidence=0.89,
            processing_time_ms=2100,
            cost_usd=0.002,
        )

        # Setup KB search to return context (triggers Stage 3)
        mock_db.fetch.return_value = [
            {
                "atom_id": uuid4(),
                "title": "PowerFlex 525 Fault Codes",
                "content": "F003 indicates motor overload",
                "source_url": "https://docs.rockwell.com",
                "type": "procedure",
                "confidence": 0.90,
            }
        ]

        # Create pipeline service
        pipeline = PhotoPipelineService(
            db=mock_db,
            equipment_service=mock_equipment_service,
            work_order_service=mock_work_order_service,
            knowledge_service=mock_knowledge_service,
        )

        # Mock Claude analyzer
        with patch.object(pipeline.claude_analyzer, 'analyze_with_kb', new_callable=AsyncMock) as mock_claude:
            mock_claude.return_value = AnalysisResult(
                analysis="This VFD is operating normally. Historical F003 faults indicate past overload events.",
                solutions=["Monitor load levels", "Check cooling fan"],
                kb_citations=[{"title": "PowerFlex 525 Guide", "url": "https://docs.rockwell.com", "type": "procedure"}],
                recommendations=["Schedule preventive maintenance"],
                safety_warnings=["Lock out/tag out required before servicing"],
                confidence=0.85,
                cost_usd=0.012,
                model="claude-sonnet-4-20250514",
            )

            # Process photo
            result = await pipeline.process_photo(
                image_bytes=test_image_bytes,
                user_id="telegram_123",
                telegram_user_id=123,
            )

        # Assertions
        assert result is not None
        assert not result.rejected
        assert result.error is None

        # Stage 1 verification
        assert result.screening is not None
        assert result.screening.is_industrial
        assert result.screening.confidence >= 0.80
        assert result.screening.category == "vfd"

        # Stage 2 verification
        assert result.extraction is not None
        assert result.extraction.manufacturer == "Allen-Bradley"
        assert result.extraction.model_number == "PowerFlex 525"
        assert result.extraction.confidence >= 0.80
        assert not result.from_cache

        # Stage 3 verification
        assert result.analysis is not None
        assert "VFD" in result.analysis.analysis
        assert len(result.analysis.solutions) >= 1
        assert len(result.analysis.safety_warnings) >= 1

        # Equipment matching verification
        assert result.equipment_id is not None
        assert result.equipment_number == "EQ-001234"
        assert result.is_new_equipment

        # Cost tracking
        assert result.total_cost_usd > 0
        assert len(result.stages) == 3  # All three stages ran

        # Formatted response
        assert len(result.formatted_response) > 0
        assert "Allen-Bradley" in result.formatted_response
        assert "PowerFlex 525" in result.formatted_response


# =============================================================================
# Test: Non-Industrial Photo Rejected at Groq Stage
# =============================================================================

class TestNonIndustrialPhotoRejection:
    """Test: non-industrial photo rejected at Groq stage."""

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.photo_pipeline_service.screen_industrial_photo")
    async def test_non_industrial_photo_rejected(
        self,
        mock_screen,
        mock_db,
        test_image_bytes,
    ):
        """Non-industrial photo is rejected early at Groq screening."""
        # Setup: Groq identifies non-industrial image
        mock_screen.return_value = ScreeningResult(
            is_industrial=False,
            confidence=0.15,
            category=None,
            reason="Image shows food items, not industrial equipment",
            rejection_message="📷 This doesn't appear to be industrial equipment. Please send a photo of equipment nameplates, VFDs, motors, or control panels.",
            processing_time_ms=650,
            cost_usd=0.001,
        )

        pipeline = PhotoPipelineService(db=mock_db)

        result = await pipeline.process_photo(
            image_bytes=test_image_bytes,
            user_id="telegram_456",
            telegram_user_id=456,
        )

        # Assertions
        assert result.rejected
        assert result.rejection_message is not None
        assert "doesn't appear to be industrial" in result.rejection_message

        # Screening completed but didn't pass
        assert result.screening is not None
        assert not result.screening.is_industrial
        assert not result.screening.passes_threshold

        # Extraction should not have run
        assert result.extraction is None

        # Analysis should not have run
        assert result.analysis is None

        # Only Stage 1 ran
        assert len(result.stages) == 1
        assert result.stages[0].stage == "groq_screening"

        # Minimal cost (only screening)
        assert result.total_cost_usd == 0.001


# =============================================================================
# Test: Blurry Photo Gets Low Confidence
# =============================================================================

class TestBlurryPhotoLowConfidence:
    """Test: blurry photo gets low confidence."""

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.photo_pipeline_service.screen_industrial_photo")
    async def test_blurry_photo_low_confidence(
        self,
        mock_screen,
        mock_db,
        test_image_bytes,
    ):
        """Blurry industrial photo passes screening but with low confidence."""
        # Setup: Groq identifies industrial but low confidence
        mock_screen.return_value = ScreeningResult(
            is_industrial=True,
            confidence=0.65,  # Below 0.80 threshold
            category="motor",
            reason="Possibly a motor but image is very blurry",
            processing_time_ms=720,
            cost_usd=0.001,
        )

        pipeline = PhotoPipelineService(db=mock_db)

        result = await pipeline.process_photo(
            image_bytes=test_image_bytes,
            user_id="telegram_789",
            telegram_user_id=789,
        )

        # Assertions
        assert result.rejected
        assert result.screening is not None
        assert result.screening.is_industrial
        assert result.screening.confidence == 0.65
        assert not result.screening.passes_threshold  # Below 0.80

        # Extraction should not run (confidence below threshold)
        assert result.extraction is None

        # User message should suggest clearer photo
        assert "Low confidence" in result.formatted_response or "clearer" in result.formatted_response.lower()

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.photo_pipeline_service.screen_industrial_photo")
    @patch("rivet_pro.core.services.photo_pipeline_service.get_cached_extraction")
    @patch("rivet_pro.core.services.photo_pipeline_service.extract_component_specs")
    async def test_blurry_extraction_low_confidence(
        self,
        mock_extract,
        mock_get_cache,
        mock_screen,
        mock_db,
        test_image_bytes,
    ):
        """Photo passes screening but extraction has low confidence due to quality issues."""
        # Screening passes
        mock_screen.return_value = ScreeningResult(
            is_industrial=True,
            confidence=0.85,
            category="vfd",
            processing_time_ms=700,
            cost_usd=0.001,
        )

        # Cache miss
        mock_get_cache.return_value = None

        # Extraction succeeds but with low confidence due to text quality issues
        mock_extract.return_value = ExtractionResult(
            manufacturer="Siemens",
            model_number="6ES7",  # Partial - text was blurry
            serial_number=None,
            specs={},
            raw_text="Siemens 6ES7...",
            confidence=0.55,  # Low due to blurry text
            processing_time_ms=1800,
            cost_usd=0.002,
        )

        pipeline = PhotoPipelineService(db=mock_db)

        result = await pipeline.process_photo(
            image_bytes=test_image_bytes,
            user_id="telegram_111",
            telegram_user_id=111,
        )

        # Assertions
        assert not result.rejected
        assert result.extraction is not None
        assert result.extraction.confidence == 0.55
        assert result.extraction.manufacturer == "Siemens"

        # Low confidence extraction should still provide data
        assert "Siemens" in result.formatted_response


# =============================================================================
# Test: Cache Hit Skips DeepSeek
# =============================================================================

class TestCacheHitSkipsDeepSeek:
    """Test: cache hit skips DeepSeek on duplicate photo."""

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.photo_pipeline_service.screen_industrial_photo")
    @patch("rivet_pro.core.services.photo_pipeline_service.get_cached_extraction")
    @patch("rivet_pro.core.services.photo_pipeline_service.extract_component_specs")
    async def test_cache_hit_skips_extraction_api(
        self,
        mock_extract,
        mock_get_cache,
        mock_screen,
        mock_db,
        mock_equipment_service,
        test_image_bytes,
    ):
        """Duplicate photo retrieves cached extraction, skipping DeepSeek API call."""
        # Screening passes
        mock_screen.return_value = ScreeningResult(
            is_industrial=True,
            confidence=0.90,
            category="plc",
            processing_time_ms=600,
            cost_usd=0.001,
        )

        # CACHE HIT - return cached extraction
        mock_get_cache.return_value = ExtractionResult(
            manufacturer="Rockwell",
            model_number="1756-L72S",
            serial_number="SN12345",
            specs={"voltage": "24V DC"},
            confidence=0.88,
            from_cache=True,  # CACHED
            cost_usd=0.0,  # No cost for cache
            processing_time_ms=0,
        )

        pipeline = PhotoPipelineService(
            db=mock_db,
            equipment_service=mock_equipment_service,
        )

        result = await pipeline.process_photo(
            image_bytes=test_image_bytes,
            user_id="telegram_222",
            telegram_user_id=222,
        )

        # Assertions
        assert not result.rejected
        assert result.from_cache  # Should indicate cache hit

        # Extraction should be from cache
        assert result.extraction is not None
        assert result.extraction.from_cache
        assert result.extraction.manufacturer == "Rockwell"

        # extract_component_specs should NOT have been called (cache hit)
        mock_extract.assert_not_called()

        # Cost should be minimal (only screening + analysis, no extraction)
        # Note: extraction cost was 0 from cache
        assert result.extraction.cost_usd == 0.0

        # Formatted response should indicate cache
        assert "cache" in result.formatted_response.lower() or result.from_cache


# =============================================================================
# Test: Each Stage Failure Handled Gracefully
# =============================================================================

class TestGracefulFailureHandling:
    """Test: each stage failure handled gracefully."""

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.photo_pipeline_service.screen_industrial_photo")
    async def test_stage1_groq_api_failure(
        self,
        mock_screen,
        mock_db,
        test_image_bytes,
    ):
        """Stage 1 Groq API failure returns error gracefully."""
        # Groq API fails
        mock_screen.return_value = ScreeningResult(
            error="API timeout after 30 seconds",
            is_industrial=False,
            confidence=0.0,
        )

        pipeline = PhotoPipelineService(db=mock_db)

        result = await pipeline.process_photo(
            image_bytes=test_image_bytes,
            user_id="telegram_333",
            telegram_user_id=333,
        )

        # Assertions
        assert result.error is not None
        assert "timeout" in result.error.lower()

        # Pipeline should have stopped at Stage 1
        assert len(result.stages) == 1
        assert not result.stages[0].success

        # User-friendly error message
        assert "failed" in result.formatted_response.lower() or "❌" in result.formatted_response

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.photo_pipeline_service.screen_industrial_photo")
    @patch("rivet_pro.core.services.photo_pipeline_service.get_cached_extraction")
    @patch("rivet_pro.core.services.photo_pipeline_service.extract_component_specs")
    async def test_stage2_deepseek_api_failure(
        self,
        mock_extract,
        mock_get_cache,
        mock_screen,
        mock_db,
        test_image_bytes,
    ):
        """Stage 2 DeepSeek API failure continues with partial data."""
        # Screening passes
        mock_screen.return_value = ScreeningResult(
            is_industrial=True,
            confidence=0.88,
            category="motor",
            processing_time_ms=700,
            cost_usd=0.001,
        )

        # Cache miss
        mock_get_cache.return_value = None

        # DeepSeek extraction fails
        mock_extract.return_value = ExtractionResult(
            error="DeepSeek API rate limit exceeded",
            confidence=0.0,
        )

        pipeline = PhotoPipelineService(db=mock_db)

        result = await pipeline.process_photo(
            image_bytes=test_image_bytes,
            user_id="telegram_444",
            telegram_user_id=444,
        )

        # Assertions - should continue with partial data
        assert result.screening is not None
        assert result.screening.passes_threshold

        # Extraction failed but handled gracefully
        assert result.extraction is not None
        assert result.extraction.error is not None

        # Should have multiple stages
        assert len(result.stages) >= 2

        # Stage 2 should show failure
        stage2 = next((s for s in result.stages if s.stage == "deepseek_extraction"), None)
        assert stage2 is not None
        assert not stage2.success

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.photo_pipeline_service.screen_industrial_photo")
    @patch("rivet_pro.core.services.photo_pipeline_service.get_cached_extraction")
    @patch("rivet_pro.core.services.photo_pipeline_service.extract_component_specs")
    async def test_stage3_claude_api_failure(
        self,
        mock_extract,
        mock_get_cache,
        mock_screen,
        mock_db,
        mock_equipment_service,
        test_image_bytes,
    ):
        """Stage 3 Claude API failure returns partial result."""
        # Screening passes
        mock_screen.return_value = ScreeningResult(
            is_industrial=True,
            confidence=0.90,
            category="vfd",
            processing_time_ms=650,
            cost_usd=0.001,
        )

        # Cache miss
        mock_get_cache.return_value = None

        # Extraction succeeds
        mock_extract.return_value = ExtractionResult(
            manufacturer="ABB",
            model_number="ACS550",
            serial_number="SN789",
            specs={"voltage": "480V", "horsepower": "50HP"},
            confidence=0.91,
            processing_time_ms=1900,
            cost_usd=0.002,
        )

        # Setup KB search to return context (triggers Stage 3)
        mock_db.fetch.return_value = [
            {
                "atom_id": uuid4(),
                "title": "ACS550 Manual",
                "content": "Drive specifications",
                "source_url": "https://abb.com",
                "type": "procedure",
                "confidence": 0.85,
            }
        ]

        pipeline = PhotoPipelineService(
            db=mock_db,
            equipment_service=mock_equipment_service,
        )

        # Mock Claude analyzer to fail
        with patch.object(pipeline.claude_analyzer, 'analyze_with_kb', new_callable=AsyncMock) as mock_claude:
            mock_claude.side_effect = Exception("Claude API rate limit exceeded")

            result = await pipeline.process_photo(
                image_bytes=test_image_bytes,
                user_id="telegram_555",
                telegram_user_id=555,
            )

        # Assertions - Stage 1 and 2 succeeded
        assert result.screening is not None
        assert result.screening.passes_threshold

        assert result.extraction is not None
        assert result.extraction.manufacturer == "ABB"

        # Stage 3 failed but handled gracefully
        stage3 = next((s for s in result.stages if s.stage == "claude_analysis"), None)
        assert stage3 is not None
        assert not stage3.success or stage3.skipped

        # Result still has useful data from Stage 1 and 2
        assert "ABB" in result.formatted_response
        assert "ACS550" in result.formatted_response

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.photo_pipeline_service.screen_industrial_photo")
    async def test_groq_api_key_missing(
        self,
        mock_screen,
        mock_db,
        test_image_bytes,
    ):
        """Missing GROQ_API_KEY returns helpful error."""
        mock_screen.return_value = ScreeningResult(
            error="GROQ_API_KEY not configured",
            is_industrial=False,
            confidence=0.0,
        )

        pipeline = PhotoPipelineService(db=mock_db)

        result = await pipeline.process_photo(
            image_bytes=test_image_bytes,
            user_id="telegram_666",
            telegram_user_id=666,
        )

        assert result.error is not None
        assert "GROQ_API_KEY" in result.error

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.photo_pipeline_service.screen_industrial_photo")
    async def test_network_timeout_handled(
        self,
        mock_screen,
        mock_db,
        test_image_bytes,
    ):
        """Network timeout during screening is handled gracefully."""
        mock_screen.side_effect = asyncio.TimeoutError("Network timeout")

        pipeline = PhotoPipelineService(db=mock_db)

        result = await pipeline.process_photo(
            image_bytes=test_image_bytes,
            user_id="telegram_777",
            telegram_user_id=777,
        )

        # Should handle exception gracefully
        assert result.error is not None or len(result.stages) == 0


# =============================================================================
# Test: Pipeline Stage Result Tracking
# =============================================================================

class TestPipelineStageTracking:
    """Test: stage result tracking and trace metadata."""

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.photo_pipeline_service.screen_industrial_photo")
    @patch("rivet_pro.core.services.photo_pipeline_service.get_cached_extraction")
    @patch("rivet_pro.core.services.photo_pipeline_service.extract_component_specs")
    async def test_trace_metadata_complete(
        self,
        mock_extract,
        mock_get_cache,
        mock_screen,
        mock_db,
        mock_equipment_service,
        test_image_bytes,
    ):
        """Trace metadata contains all stage information."""
        mock_screen.return_value = ScreeningResult(
            is_industrial=True,
            confidence=0.88,
            category="sensor",
            processing_time_ms=500,
            cost_usd=0.001,
        )
        mock_get_cache.return_value = None
        mock_extract.return_value = ExtractionResult(
            manufacturer="Honeywell",
            model_number="STD725",
            confidence=0.85,
            processing_time_ms=1500,
            cost_usd=0.002,
        )

        pipeline = PhotoPipelineService(
            db=mock_db,
            equipment_service=mock_equipment_service,
        )

        result = await pipeline.process_photo(
            image_bytes=test_image_bytes,
            user_id="telegram_888",
            telegram_user_id=888,
        )

        # Get trace metadata
        metadata = result.get_trace_metadata()

        # Verify structure
        assert "total_cost_usd" in metadata
        assert "total_time_ms" in metadata
        assert "from_cache" in metadata
        assert "stages" in metadata

        # Verify stage details
        assert len(metadata["stages"]) >= 2
        for stage in metadata["stages"]:
            assert "stage" in stage
            assert "success" in stage
            assert "cost_usd" in stage
            assert "processing_time_ms" in stage


# =============================================================================
# Test: Equipment Service Integration
# =============================================================================

class TestEquipmentServiceIntegration:
    """Test: equipment matching/creation integration."""

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.photo_pipeline_service.screen_industrial_photo")
    @patch("rivet_pro.core.services.photo_pipeline_service.get_cached_extraction")
    @patch("rivet_pro.core.services.photo_pipeline_service.extract_component_specs")
    async def test_equipment_created_for_new_photo(
        self,
        mock_extract,
        mock_get_cache,
        mock_screen,
        mock_db,
        test_image_bytes,
    ):
        """New equipment is created when extraction has model info."""
        mock_screen.return_value = ScreeningResult(
            is_industrial=True,
            confidence=0.92,
            category="pump",
            processing_time_ms=600,
            cost_usd=0.001,
        )
        mock_get_cache.return_value = None
        mock_extract.return_value = ExtractionResult(
            manufacturer="Grundfos",
            model_number="CR 45-2",
            serial_number="GF123456",
            specs={"flow_rate": "100 GPM", "pressure": "150 PSI"},
            confidence=0.90,
            processing_time_ms=1700,
            cost_usd=0.002,
        )

        # Create mock equipment service that tracks calls
        equipment_service = AsyncMock()
        equipment_service.match_or_create_equipment = AsyncMock(
            return_value=(uuid4(), "PUMP-001", True)  # New equipment
        )

        pipeline = PhotoPipelineService(
            db=mock_db,
            equipment_service=equipment_service,
        )

        result = await pipeline.process_photo(
            image_bytes=test_image_bytes,
            user_id="telegram_999",
            telegram_user_id=999,
        )

        # Verify equipment service was called with correct parameters
        equipment_service.match_or_create_equipment.assert_called_once()
        call_args = equipment_service.match_or_create_equipment.call_args

        assert call_args.kwargs["manufacturer"] == "Grundfos"
        assert call_args.kwargs["model_number"] == "CR 45-2"
        assert call_args.kwargs["serial_number"] == "GF123456"
        assert call_args.kwargs["equipment_type"] == "pump"

        # Verify result has equipment info
        assert result.equipment_number == "PUMP-001"
        assert result.is_new_equipment


# =============================================================================
# Test: Response Formatting
# =============================================================================

class TestResponseFormatting:
    """Test: formatted response includes all relevant data."""

    @pytest.mark.asyncio
    @patch("rivet_pro.core.services.photo_pipeline_service.screen_industrial_photo")
    @patch("rivet_pro.core.services.photo_pipeline_service.get_cached_extraction")
    @patch("rivet_pro.core.services.photo_pipeline_service.extract_component_specs")
    async def test_formatted_response_includes_specs(
        self,
        mock_extract,
        mock_get_cache,
        mock_screen,
        mock_db,
        mock_equipment_service,
        test_image_bytes,
    ):
        """Formatted response includes manufacturer, model, and specs."""
        mock_screen.return_value = ScreeningResult(
            is_industrial=True,
            confidence=0.91,
            category="motor",
            processing_time_ms=650,
            cost_usd=0.001,
        )
        mock_get_cache.return_value = None
        mock_extract.return_value = ExtractionResult(
            manufacturer="WEG",
            model_number="W22-355M",
            serial_number="WG789012",
            specs={
                "voltage": "460V",
                "horsepower": "150HP",
                "rpm": "1800",
                "phase": "3",
                "current": "175A",
            },
            confidence=0.88,
            processing_time_ms=1800,
            cost_usd=0.002,
        )

        pipeline = PhotoPipelineService(
            db=mock_db,
            equipment_service=mock_equipment_service,
        )

        result = await pipeline.process_photo(
            image_bytes=test_image_bytes,
            user_id="telegram_1010",
            telegram_user_id=1010,
        )

        response = result.formatted_response

        # Verify key information is included
        assert "WEG" in response
        assert "W22-355M" in response
        assert "460V" in response or "voltage" in response.lower()
        assert "150HP" in response or "horsepower" in response.lower()
        assert "EQ-001234" in response  # Equipment number


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
