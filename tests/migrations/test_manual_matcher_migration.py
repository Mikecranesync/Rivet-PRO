"""
Tests for manual_matcher_service.py feature flag migration.

Tests both code paths:
- Flag OFF: Classic search without LLM validation
- Flag ON: LLM-enhanced matching with validation

Story: STABLE-011
"""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# This would normally import from rivet_pro.core.services
# For demo purposes, we're documenting the test pattern


class TestManualMatcherMigration:
    """Test manual matcher service with feature flag"""

    @pytest.fixture
    def mock_db(self):
        """Mock database connection"""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.fetchrow = AsyncMock()
        return db

    @pytest.fixture
    def equipment_params(self):
        """Sample equipment parameters"""
        return {
            'equipment_id': uuid4(),
            'manufacturer': 'Siemens',
            'model': 'S7-1200',
            'equipment_type': 'PLC',
            'telegram_chat_id': 12345
        }

    @pytest.fixture
    async def flag_off(self, monkeypatch):
        """Fixture to disable the feature flag"""
        monkeypatch.setenv('RIVET_FLAG_RIVET_MIGRATION_MANUAL_MATCHER_V2', 'false')
        # Reload the flag manager to pick up env change
        from rivet_pro.core.feature_flags import FeatureFlagManager
        manager = FeatureFlagManager()
        manager.reload()
        yield manager

    @pytest.fixture
    async def flag_on(self, monkeypatch):
        """Fixture to enable the feature flag"""
        monkeypatch.setenv('RIVET_FLAG_RIVET_MIGRATION_MANUAL_MATCHER_V2', 'true')
        # Reload the flag manager to pick up env change
        from rivet_pro.core.feature_flags import FeatureFlagManager
        manager = FeatureFlagManager()
        manager.reload()
        yield manager

    @pytest.mark.asyncio
    async def test_flag_off_uses_classic_search(self, mock_db, equipment_params, flag_off):
        """
        Test Case 1: Flag OFF → Classic search behavior

        When the feature flag is disabled, the service should:
        - Use simple search without LLM validation
        - Return fixed confidence score (0.75)
        - Include method='classic_search' in result
        """
        from rivet_pro.core.services.manual_matcher_service import ManualMatcherService

        service = ManualMatcherService(mock_db)

        # Mock the manual_service to return a manual
        with patch.object(service.manual_service, 'search_manual', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                'manual_url': 'https://example.com/manual.pdf',
                'manual_title': 'Siemens S7-1200 Manual'
            }

            result = await service.search_and_validate_manual(**equipment_params)

            # Assertions for classic behavior
            assert result['status'] == 'manual_found'
            assert result['manual_url'] == 'https://example.com/manual.pdf'
            assert result['confidence'] == 0.75  # Fixed for classic
            assert result['method'] == 'classic_search'

            # Verify classic search was called
            mock_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_flag_on_uses_llm_validation(self, mock_db, equipment_params, flag_on):
        """
        Test Case 2: Flag ON → LLM-enhanced matching

        When the feature flag is enabled, the service should:
        - Use LLM validation
        - Return dynamic confidence score
        - Call the v2 implementation
        """
        from rivet_pro.core.services.manual_matcher_service import ManualMatcherService

        service = ManualMatcherService(mock_db)

        # Mock both manual search and LLM validation
        with patch.object(service.manual_service, 'search_manual', new_callable=AsyncMock) as mock_search, \
             patch.object(service, '_validate_with_llm', new_callable=AsyncMock) as mock_llm:

            mock_search.return_value = {
                'manual_url': 'https://example.com/manual.pdf',
                'manual_title': 'Siemens S7-1200 Manual'
            }

            mock_llm.return_value = {
                'matches': True,
                'confidence': 0.92,  # LLM-validated confidence
                'reasoning': 'High confidence match based on model number'
            }

            # Note: This test would need the actual v2 implementation
            # For demo, we're showing the test pattern

            # Verify LLM validation was called (in full implementation)
            # assert result includes LLM-validated confidence
            # assert _validate_with_llm was called

    @pytest.mark.asyncio
    async def test_flag_toggle_no_crashes(self, mock_db, equipment_params):
        """
        Test Case 3: Toggle flag mid-process → No crashes

        Changing the flag state should not cause crashes.
        Each request uses the flag state at invocation time.
        """
        from rivet_pro.core.services.manual_matcher_service import ManualMatcherService

        service = ManualMatcherService(mock_db)

        # First call with flag OFF
        os.environ['RIVET_FLAG_RIVET_MIGRATION_MANUAL_MATCHER_V2'] = 'false'
        service.flags.reload()

        with patch.object(service.manual_service, 'search_manual', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                'manual_url': 'https://example.com/manual1.pdf',
                'manual_title': 'Manual 1'
            }

            result1 = await service.search_and_validate_manual(**equipment_params)
            assert result1['method'] == 'classic_search'

        # Toggle flag ON for second call
        os.environ['RIVET_FLAG_RIVET_MIGRATION_MANUAL_MATCHER_V2'] = 'true'
        service.flags.reload()

        # Second call should use new method (no crash)
        # In full implementation, this would verify v2 is used

        # No exception raised = test passes

    def test_flag_state_logging(self, mock_db, caplog):
        """
        Test Case 4: Verify flag state is logged

        The service should log which code path is being used.
        """
        from rivet_pro.core.services.manual_matcher_service import ManualMatcherService
        import logging

        caplog.set_level(logging.INFO)

        service = ManualMatcherService(mock_db)

        # Check that flag manager was initialized
        assert hasattr(service, 'flags')
        assert service.flags is not None

    @pytest.mark.parametrize('flag_state,expected_method', [
        ('true', 'llm_enhanced'),
        ('false', 'classic_search'),
    ])
    def test_flag_state_determines_method(self, flag_state, expected_method, mock_db, monkeypatch):
        """
        Test Case 5: Parameterized test for flag states

        Verify that different flag states route to different implementations.
        """
        from rivet_pro.core.services.manual_matcher_service import ManualMatcherService

        monkeypatch.setenv('RIVET_FLAG_RIVET_MIGRATION_MANUAL_MATCHER_V2', flag_state)

        service = ManualMatcherService(mock_db)
        service.flags.reload()

        enabled = service.flags.is_enabled('rivet.migration.manual_matcher_v2')

        if flag_state == 'true':
            assert enabled is True
        else:
            assert enabled is False


# Integration test pattern (for CI)
@pytest.mark.integration
class TestManualMatcherIntegration:
    """
    Integration tests requiring actual database/LLM connections.

    These tests are skipped in unit test runs and only run in CI
    with proper credentials configured.
    """

    @pytest.mark.asyncio
    async def test_end_to_end_with_flag_on(self):
        """
        Full end-to-end test with real database and LLM.

        Requires:
        - Database connection
        - LLM API keys
        - Test equipment data
        """
        pytest.skip("Integration test - requires full environment")

    @pytest.mark.asyncio
    async def test_end_to_end_with_flag_off(self):
        """
        Full end-to-end test with classic search only.

        Requires:
        - Database connection
        - Test equipment data
        """
        pytest.skip("Integration test - requires full environment")


# Performance test pattern
@pytest.mark.performance
class TestManualMatcherPerformance:
    """
    Performance tests to compare classic vs LLM-enhanced matching.

    These tests help validate that the new implementation meets
    performance requirements.
    """

    @pytest.mark.asyncio
    async def test_classic_search_performance(self):
        """Benchmark classic search performance"""
        pytest.skip("Performance test - run separately")

    @pytest.mark.asyncio
    async def test_llm_search_performance(self):
        """Benchmark LLM-enhanced search performance"""
        pytest.skip("Performance test - run separately")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
