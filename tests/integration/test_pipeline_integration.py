"""
Integration tests for Phase 3 Pipeline components.

Tests:
- PipelineIntegration facade
- WorkflowStateMachine state transitions
- AgentExecutor with vendor routing
- End-to-end message processing
"""

import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Skip if database not available
pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set"
)


class TestWorkflowStateMachine:
    """Test WorkflowStateMachine state transitions."""

    def test_create_workflow(self):
        """Should create workflow in CREATED state."""
        from rivet_pro.core.services.workflow_state_machine import (
            WorkflowStateMachine,
            WorkflowState
        )

        sm = WorkflowStateMachine()
        workflow_id = sm.create(
            workflow_type="test_workflow",
            entity_id="test_entity_123",
            metadata={"test": True}
        )

        assert workflow_id is not None
        assert workflow_id > 0

        # Verify state
        state = sm.get_current_state(workflow_id)
        assert state["current_state"] == WorkflowState.CREATED.value
        assert state["workflow_type"] == "test_workflow"

    def test_valid_transition(self):
        """Should allow valid state transitions."""
        from rivet_pro.core.services.workflow_state_machine import (
            WorkflowStateMachine,
            WorkflowState
        )

        sm = WorkflowStateMachine()
        workflow_id = sm.create(
            workflow_type="test_workflow",
            entity_id="test_entity_456"
        )

        # CREATED -> IN_PROGRESS (valid)
        result = sm.transition(workflow_id, WorkflowState.IN_PROGRESS)
        assert result is True

        state = sm.get_current_state(workflow_id)
        assert state["current_state"] == WorkflowState.IN_PROGRESS.value
        assert state["previous_state"] == WorkflowState.CREATED.value

    def test_invalid_transition(self):
        """Should reject invalid state transitions."""
        from rivet_pro.core.services.workflow_state_machine import (
            WorkflowStateMachine,
            WorkflowState,
            InvalidTransitionError
        )

        sm = WorkflowStateMachine()
        workflow_id = sm.create(
            workflow_type="test_workflow",
            entity_id="test_entity_789"
        )

        # CREATED -> COMPLETED (invalid - must go through IN_PROGRESS)
        with pytest.raises(InvalidTransitionError):
            sm.transition(workflow_id, WorkflowState.COMPLETED)

    def test_full_lifecycle(self):
        """Should complete full workflow lifecycle."""
        from rivet_pro.core.services.workflow_state_machine import (
            WorkflowStateMachine,
            WorkflowState
        )

        sm = WorkflowStateMachine()
        workflow_id = sm.create(
            workflow_type="sme_query",
            entity_id="user_test"
        )

        # CREATED -> IN_PROGRESS -> COMPLETED
        sm.transition(workflow_id, WorkflowState.IN_PROGRESS)
        sm.transition(workflow_id, WorkflowState.COMPLETED, metadata={"confidence": 0.85})

        state = sm.get_current_state(workflow_id)
        assert state["current_state"] == WorkflowState.COMPLETED.value


class TestAgentExecutor:
    """Test AgentExecutor vendor routing."""

    def test_route_vendor_siemens(self):
        """Should detect Siemens from query."""
        from rivet_pro.core.services.agent_executor import AgentExecutor, VendorType

        executor = AgentExecutor()
        vendor = executor.route_vendor("How do I reset a Siemens S7-1200 fault?")

        assert vendor == VendorType.SIEMENS

    def test_route_vendor_rockwell(self):
        """Should detect Rockwell from query."""
        from rivet_pro.core.services.agent_executor import AgentExecutor, VendorType

        executor = AgentExecutor()
        vendor = executor.route_vendor("ControlLogix 1756-L73 not communicating")

        assert vendor == VendorType.ROCKWELL

    def test_route_vendor_safety(self):
        """Should detect safety topic from query."""
        from rivet_pro.core.services.agent_executor import AgentExecutor, VendorType

        executor = AgentExecutor()
        vendor = executor.route_vendor("E-stop wiring for safety interlock SIL2")

        assert vendor == VendorType.SAFETY

    def test_route_vendor_generic(self):
        """Should default to generic for unknown queries."""
        from rivet_pro.core.services.agent_executor import AgentExecutor, VendorType

        executor = AgentExecutor()
        vendor = executor.route_vendor("Motor not starting")

        assert vendor == VendorType.GENERIC


class TestPipelineIntegration:
    """Test PipelineIntegration facade."""

    @pytest.mark.asyncio
    async def test_process_text_message_creates_pipeline(self):
        """Text message should create and complete pipeline execution."""
        from rivet_pro.core.services.pipeline_integration import PipelineIntegration

        # Mock the agent executor to avoid actual LLM calls
        with patch('rivet_pro.core.services.agent_executor.AgentExecutor') as MockExecutor:
            mock_executor = MockExecutor.return_value
            mock_executor.route_vendor.return_value = Mock(value="siemens")

            # Mock the execute method
            mock_response = Mock()
            mock_response.answer = "Test answer"
            mock_response.confidence = 0.85
            mock_response.vendor = "siemens"
            mock_response.metadata = {"provider": "mock"}
            mock_executor.execute = AsyncMock(return_value=mock_response)

            pipeline = PipelineIntegration(agent_executor=mock_executor)
            result = await pipeline.process_text_message(
                user_id="test_123",
                query="How do I reset a Siemens drive fault?"
            )

            assert result.pipeline_id is not None
            assert result.confidence == 0.85
            assert result.vendor == "siemens"
            assert result.answer == "Test answer"

    @pytest.mark.asyncio
    async def test_process_text_message_tracks_state(self):
        """Pipeline should track state transitions in database."""
        from rivet_pro.core.services.pipeline_integration import PipelineIntegration
        from rivet_pro.core.services.workflow_state_machine import (
            WorkflowStateMachine,
            WorkflowState
        )

        # Mock the agent executor
        with patch('rivet_pro.core.services.agent_executor.AgentExecutor') as MockExecutor:
            mock_executor = MockExecutor.return_value
            mock_executor.route_vendor.return_value = Mock(value="generic")

            mock_response = Mock()
            mock_response.answer = "Generic answer"
            mock_response.confidence = 0.7
            mock_response.vendor = "generic"
            mock_response.metadata = {}
            mock_executor.execute = AsyncMock(return_value=mock_response)

            # Use real state machine
            state_machine = WorkflowStateMachine()
            pipeline = PipelineIntegration(
                state_machine=state_machine,
                agent_executor=mock_executor
            )

            result = await pipeline.process_text_message(
                user_id="test_456",
                query="Motor not starting"
            )

            # Verify final state
            state = state_machine.get_current_state(result.pipeline_id)
            assert state["current_state"] == WorkflowState.COMPLETED.value

    def test_get_stats(self):
        """Should return pipeline statistics."""
        from rivet_pro.core.services.pipeline_integration import PipelineIntegration

        pipeline = PipelineIntegration()
        stats = pipeline.get_stats()

        assert "active_workflows" in stats
        assert "workflow_types" in stats
        assert "states" in stats
        assert "timestamp" in stats


class TestLLMManager:
    """Test MultiProviderLLMManager failover."""

    def test_cache_key_generation(self):
        """Cache key should be consistent for same prompt."""
        from rivet_pro.core.services.llm_manager import CacheProvider

        cache = CacheProvider()
        key1 = cache._get_cache_key("Test prompt")
        key2 = cache._get_cache_key("Test prompt")
        key3 = cache._get_cache_key("Different prompt")

        assert key1 == key2
        assert key1 != key3
        assert len(key1) == 64  # SHA-256 hex digest

    def test_provider_availability(self):
        """Should check provider availability based on API keys."""
        from rivet_pro.core.services.llm_manager import ClaudeProvider, GPT4Provider

        claude = ClaudeProvider()
        gpt4 = GPT4Provider()

        # These tests depend on environment variables
        # Just verify the method exists and returns bool
        assert isinstance(claude.is_available(), bool)
        assert isinstance(gpt4.is_available(), bool)


class TestEndToEnd:
    """End-to-end integration tests (require full environment)."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_siemens_query_full_pipeline(self):
        """Full pipeline test with Siemens query."""
        from rivet_pro.core.services.pipeline_integration import get_pipeline

        pipeline = get_pipeline()
        result = await pipeline.process_text_message(
            user_id="e2e_test_user",
            query="What does fault F0002 mean on Siemens SINAMICS G120?"
        )

        assert result.pipeline_id is not None
        assert result.vendor == "siemens"
        assert result.confidence > 0
        assert len(result.answer) > 50  # Should have substantial response
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_generic_query_full_pipeline(self):
        """Full pipeline test with generic query."""
        from rivet_pro.core.services.pipeline_integration import get_pipeline

        pipeline = get_pipeline()
        result = await pipeline.process_text_message(
            user_id="e2e_test_user",
            query="Motor overheating after 10 minutes"
        )

        assert result.pipeline_id is not None
        assert result.vendor == "generic"
        assert result.confidence > 0
        assert len(result.answer) > 50
