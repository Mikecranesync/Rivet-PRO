"""
Unit tests for troubleshooting tree drafts module.

Tests save_draft, list_drafts, approve_draft, reject_draft functionality.
"""

import pytest
import asyncio
from datetime import datetime
from rivet_pro.troubleshooting.drafts import (
    save_draft,
    get_draft,
    list_drafts,
    approve_draft,
    reject_draft,
    delete_draft,
    get_draft_stats,
    DraftStatus,
)


@pytest.fixture
async def sample_draft_data():
    """Sample draft data for testing"""
    return {
        "equipment_type": "Siemens S7-1200 PLC",
        "problem": "Communication fault",
        "steps": [
            "Step 1: Check physical cable connections",
            "Step 2: Verify IP address configuration",
            "Step 3: Test with PING command",
            "Step 4: Check firewall settings",
            "Step 5: Verify PLC is in RUN mode"
        ],
        "user_id": 123456789,
        "original_query": "My PLC won't communicate with the HMI"
    }


@pytest.fixture
async def created_draft(sample_draft_data):
    """Create a draft for testing and clean up after"""
    draft_id = await save_draft(**sample_draft_data)
    yield draft_id
    # Cleanup - ignore errors since draft may already be deleted by test
    try:
        await delete_draft(draft_id)
    except Exception as cleanup_error:
        # Expected if test already deleted the draft
        pass  # Cleanup failures are acceptable in test fixtures


class TestSaveDraft:
    """Tests for save_draft function"""

    @pytest.mark.asyncio
    async def test_save_draft_success(self, sample_draft_data):
        """Test successful draft creation"""
        draft_id = await save_draft(**sample_draft_data)

        assert isinstance(draft_id, int)
        assert draft_id > 0

        # Cleanup
        await delete_draft(draft_id)

    @pytest.mark.asyncio
    async def test_save_draft_with_minimal_data(self):
        """Test draft creation with minimal required data"""
        draft_id = await save_draft(
            equipment_type="Test Equipment",
            problem="Test Problem",
            steps=["Step 1"],
            user_id=123456789
        )

        assert isinstance(draft_id, int)
        assert draft_id > 0

        # Cleanup
        await delete_draft(draft_id)

    @pytest.mark.asyncio
    async def test_save_draft_validation_errors(self):
        """Test validation errors for invalid inputs"""

        # Missing equipment_type
        with pytest.raises(ValueError, match="equipment_type, problem, and steps are required"):
            await save_draft(
                equipment_type="",
                problem="Problem",
                steps=["Step 1"],
                user_id=123
            )

        # Empty steps list
        with pytest.raises(ValueError, match="steps must be a non-empty list"):
            await save_draft(
                equipment_type="Equipment",
                problem="Problem",
                steps=[],
                user_id=123
            )

        # Steps not a list
        with pytest.raises(ValueError, match="steps must be a non-empty list"):
            await save_draft(
                equipment_type="Equipment",
                problem="Problem",
                steps="Not a list",
                user_id=123
            )


class TestGetDraft:
    """Tests for get_draft function"""

    @pytest.mark.asyncio
    async def test_get_draft_success(self, created_draft, sample_draft_data):
        """Test retrieving a draft by ID"""
        draft = await get_draft(created_draft)

        assert draft is not None
        assert draft["id"] == created_draft
        assert draft["equipment_type"] == sample_draft_data["equipment_type"]
        assert draft["problem"] == sample_draft_data["problem"]
        assert draft["generated_steps"] == sample_draft_data["steps"]
        assert draft["user_id"] == sample_draft_data["user_id"]
        assert draft["status"] == DraftStatus.DRAFT
        assert isinstance(draft["created_at"], datetime)

    @pytest.mark.asyncio
    async def test_get_draft_not_found(self):
        """Test retrieving non-existent draft"""
        draft = await get_draft(999999)
        assert draft is None


class TestListDrafts:
    """Tests for list_drafts function"""

    @pytest.mark.asyncio
    async def test_list_drafts_no_filter(self, created_draft):
        """Test listing all drafts"""
        drafts = await list_drafts()

        assert isinstance(drafts, list)
        assert len(drafts) > 0

        # Check structure
        draft = drafts[0]
        assert "id" in draft
        assert "equipment_type" in draft
        assert "problem" in draft
        assert "status" in draft
        assert "step_count" in draft

    @pytest.mark.asyncio
    async def test_list_drafts_by_status(self, created_draft):
        """Test filtering drafts by status"""
        drafts = await list_drafts(status=DraftStatus.DRAFT)

        assert isinstance(drafts, list)
        assert all(d["status"] == DraftStatus.DRAFT for d in drafts)

    @pytest.mark.asyncio
    async def test_list_drafts_by_user(self, created_draft, sample_draft_data):
        """Test filtering drafts by user"""
        drafts = await list_drafts(user_id=sample_draft_data["user_id"])

        assert isinstance(drafts, list)
        assert all(d["user_id"] == sample_draft_data["user_id"] for d in drafts)

    @pytest.mark.asyncio
    async def test_list_drafts_pagination(self, created_draft):
        """Test pagination parameters"""
        # Get first 5
        drafts_page1 = await list_drafts(limit=5, offset=0)
        assert len(drafts_page1) <= 5

        # Get next 5
        drafts_page2 = await list_drafts(limit=5, offset=5)
        assert len(drafts_page2) <= 5

        # Should be different (if more than 5 drafts exist)
        if len(drafts_page1) == 5 and len(drafts_page2) > 0:
            assert drafts_page1[0]["id"] != drafts_page2[0]["id"]


class TestApproveDraft:
    """Tests for approve_draft function"""

    @pytest.mark.asyncio
    async def test_approve_draft_success(self, created_draft):
        """Test successful draft approval"""
        admin_id = 987654321

        tree_id = await approve_draft(created_draft, approved_by=admin_id)

        assert isinstance(tree_id, int)
        assert tree_id > 0

        # Verify draft status updated
        draft = await get_draft(created_draft)
        assert draft["status"] == DraftStatus.APPROVED
        assert draft["approved_by"] == admin_id
        assert draft["tree_id"] == tree_id
        assert draft["approved_at"] is not None

    @pytest.mark.asyncio
    async def test_approve_draft_not_found(self):
        """Test approving non-existent draft"""
        tree_id = await approve_draft(999999, approved_by=123)
        assert tree_id is None

    @pytest.mark.asyncio
    async def test_approve_draft_already_approved(self, created_draft):
        """Test approving already approved draft"""
        # Approve first time
        await approve_draft(created_draft, approved_by=123)

        # Try to approve again
        with pytest.raises(ValueError, match="already approved"):
            await approve_draft(created_draft, approved_by=456)


class TestRejectDraft:
    """Tests for reject_draft function"""

    @pytest.mark.asyncio
    async def test_reject_draft_success(self, created_draft):
        """Test successful draft rejection"""
        admin_id = 987654321
        reason = "Steps are too generic, need more detail"

        success = await reject_draft(
            created_draft,
            rejected_by=admin_id,
            reason=reason
        )

        assert success is True

        # Verify draft status updated
        draft = await get_draft(created_draft)
        assert draft["status"] == DraftStatus.REJECTED
        assert draft["approved_by"] == admin_id  # Using approved_by for rejected_by
        assert draft["rejection_reason"] == reason
        assert draft["approved_at"] is not None

    @pytest.mark.asyncio
    async def test_reject_draft_not_found(self):
        """Test rejecting non-existent draft"""
        success = await reject_draft(999999, rejected_by=123, reason="Test")
        assert success is False

    @pytest.mark.asyncio
    async def test_reject_draft_already_rejected(self, created_draft):
        """Test rejecting already rejected draft"""
        # Reject first time
        await reject_draft(created_draft, rejected_by=123, reason="First")

        # Try to reject again
        with pytest.raises(ValueError, match="already rejected"):
            await reject_draft(created_draft, rejected_by=456, reason="Second")


class TestDeleteDraft:
    """Tests for delete_draft function"""

    @pytest.mark.asyncio
    async def test_delete_draft_success(self, created_draft):
        """Test successful draft deletion"""
        success = await delete_draft(created_draft)
        assert success is True

        # Verify draft is gone
        draft = await get_draft(created_draft)
        assert draft is None

    @pytest.mark.asyncio
    async def test_delete_draft_not_found(self):
        """Test deleting non-existent draft"""
        success = await delete_draft(999999)
        assert success is False


class TestGetDraftStats:
    """Tests for get_draft_stats function"""

    @pytest.mark.asyncio
    async def test_get_draft_stats(self, created_draft):
        """Test getting draft statistics"""
        stats = await get_draft_stats()

        assert isinstance(stats, dict)
        assert "total" in stats
        assert DraftStatus.DRAFT in stats
        assert DraftStatus.APPROVED in stats
        assert DraftStatus.REJECTED in stats

        assert isinstance(stats["total"], int)
        assert stats["total"] >= 1  # At least our test draft

        # Sum of status counts should equal total
        status_sum = (
            stats[DraftStatus.DRAFT] +
            stats[DraftStatus.APPROVED] +
            stats[DraftStatus.REJECTED]
        )
        assert status_sum == stats["total"]


class TestDraftToTreeConversion:
    """Tests for draft to tree conversion logic"""

    @pytest.mark.asyncio
    async def test_approved_draft_creates_valid_tree(self, created_draft):
        """Test that approved draft creates a valid tree structure"""
        admin_id = 123456789

        # Approve draft
        tree_id = await approve_draft(created_draft, approved_by=admin_id)
        assert tree_id is not None

        # Get the created tree (would need tree service to verify)
        # For now, just verify the draft was properly updated
        draft = await get_draft(created_draft)
        assert draft["tree_id"] == tree_id
        assert draft["status"] == DraftStatus.APPROVED


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_draft_with_special_characters(self):
        """Test draft with special characters in content"""
        draft_id = await save_draft(
            equipment_type="Motor (3-phase, 480V)",
            problem="Fault #42: Overload & Temperature",
            steps=[
                "Check wire gauge (AWG 12-16)",
                "Test @ 50% load",
                "Verify temp < 80°C"
            ],
            user_id=123456789
        )

        assert draft_id > 0

        # Verify retrieval
        draft = await get_draft(draft_id)
        assert draft is not None
        assert "°C" in draft["generated_steps"][2]

        # Cleanup
        await delete_draft(draft_id)

    @pytest.mark.asyncio
    async def test_draft_with_long_content(self):
        """Test draft with very long content"""
        long_steps = [f"Step {i}: This is a very detailed step with lots of information about troubleshooting." * 10
                      for i in range(1, 51)]  # 50 long steps

        draft_id = await save_draft(
            equipment_type="Complex Equipment",
            problem="Complex Problem",
            steps=long_steps,
            user_id=123456789
        )

        assert draft_id > 0

        # Verify retrieval
        draft = await get_draft(draft_id)
        assert draft is not None
        assert len(draft["generated_steps"]) == 50

        # Cleanup
        await delete_draft(draft_id)

    @pytest.mark.asyncio
    async def test_concurrent_draft_operations(self, sample_draft_data):
        """Test concurrent draft creation"""
        # Create multiple drafts concurrently
        tasks = [
            save_draft(**{**sample_draft_data, "user_id": 100 + i})
            for i in range(5)
        ]

        draft_ids = await asyncio.gather(*tasks)

        assert len(draft_ids) == 5
        assert all(isinstance(id, int) for id in draft_ids)
        assert len(set(draft_ids)) == 5  # All unique

        # Cleanup
        for draft_id in draft_ids:
            await delete_draft(draft_id)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
