"""
Unit tests for Atlas CMMS client integration.

Run with: pytest tests/test_atlas_client.py
"""

import pytest
from rivet.integrations.atlas import AtlasClient, AtlasConfig, AtlasNotFoundError, AtlasValidationError


class TestAtlasConfig:
    """Test Atlas configuration."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = AtlasConfig()
        assert config.atlas_base_url == "http://localhost:8080/api"
        assert config.atlas_timeout == 30.0
        assert config.atlas_max_retries == 3
        assert config.atlas_enabled is True

    def test_config_validation(self):
        """Test configuration validation."""
        config = AtlasConfig()
        errors = config.validate_config()
        # Should have no errors with defaults
        assert isinstance(errors, list)


@pytest.mark.asyncio
class TestAtlasClient:
    """Test Atlas CMMS client (requires Atlas server running)."""

    async def test_client_context_manager(self):
        """Test client can be used as async context manager."""
        async with AtlasClient() as client:
            assert client is not None

    @pytest.mark.skip(reason="Requires Atlas server running")
    async def test_health_check(self):
        """Test Atlas API health check."""
        async with AtlasClient() as client:
            health = await client.health_check()
            assert health["status"] == "UP"

    @pytest.mark.skip(reason="Requires Atlas server running")
    async def test_create_asset(self):
        """Test asset creation."""
        async with AtlasClient() as client:
            asset = await client.create_asset({
                "name": "Test Motor",
                "manufacturer": "Siemens",
                "model": "1LA7096-4AA12",
                "serialNumber": "TEST-001"
            })
            assert asset["id"] is not None
            assert asset["manufacturer"] == "Siemens"

    @pytest.mark.skip(reason="Requires Atlas server running")
    async def test_search_assets(self):
        """Test asset search."""
        async with AtlasClient() as client:
            results = await client.search_assets("motor", limit=10)
            assert isinstance(results, list)

    @pytest.mark.skip(reason="Requires Atlas server running")
    async def test_create_work_order(self):
        """Test work order creation with equipment."""
        async with AtlasClient() as client:
            # Create asset first
            asset = await client.create_asset({"name": "Test VFD"})

            # Create work order
            wo = await client.create_work_order({
                "title": "Fix VFD fault F005",
                "description": "VFD displaying fault code F005",
                "priority": "HIGH",
                "assetId": asset["id"]
            })

            assert wo["id"] is not None
            assert wo["priority"] == "HIGH"
            assert wo["assetId"] == asset["id"]

    @pytest.mark.skip(reason="Requires Atlas server running")
    async def test_list_work_orders(self):
        """Test work order listing."""
        async with AtlasClient() as client:
            result = await client.list_work_orders(status="PENDING", page=0, limit=20)
            assert "content" in result
            assert isinstance(result["content"], list)


@pytest.mark.asyncio
class TestEquipmentTaxonomy:
    """Test equipment taxonomy integration."""

    def test_taxonomy_import(self):
        """Test taxonomy can be imported."""
        from rivet.atlas.equipment_taxonomy import identify_component, extract_fault_code

        # Test basic functionality
        component = identify_component("Siemens S7-1200")
        assert component is not None
        assert "manufacturer" in component

    def test_fault_code_extraction(self):
        """Test fault code extraction."""
        from rivet.atlas.equipment_taxonomy import extract_fault_code

        text = "Device showing error F0502"
        fault = extract_fault_code(text)
        assert fault is not None
        assert "F0502" in fault or "0502" in fault
