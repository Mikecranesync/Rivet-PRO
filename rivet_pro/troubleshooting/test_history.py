"""
Unit tests for NavigationHistory module.

Tests all aspects of back navigation functionality for troubleshooting trees.
"""

import pytest
from datetime import datetime, timedelta
from rivet_pro.troubleshooting.history import (
    NavigationHistory,
    NavigationSession,
    get_navigation_history
)


class TestNavigationSession:
    """Test NavigationSession dataclass."""

    def test_session_creation(self):
        """Test creating a navigation session."""
        session = NavigationSession(chat_id=123)

        assert session.chat_id == 123
        assert session.tree_id is None
        assert session.stack == []
        assert isinstance(session.last_accessed, datetime)

    def test_session_with_tree(self):
        """Test creating session with tree ID."""
        session = NavigationSession(chat_id=123, tree_id=42)

        assert session.chat_id == 123
        assert session.tree_id == 42

    def test_update_access_time(self):
        """Test access time updates."""
        session = NavigationSession(chat_id=123)
        original_time = session.last_accessed

        # Wait a bit and update
        import time
        time.sleep(0.01)
        session.update_access_time()

        assert session.last_accessed > original_time


class TestNavigationHistory:
    """Test NavigationHistory functionality."""

    def test_initialization(self):
        """Test NavigationHistory initialization."""
        history = NavigationHistory(max_stack_depth=10, session_timeout_hours=2)

        assert history._max_stack_depth == 10
        assert history._session_timeout == timedelta(hours=2)
        assert len(history._sessions) == 0

    def test_push_single_node(self):
        """Test pushing a single node."""
        history = NavigationHistory()
        chat_id = 123

        history.push(chat_id, "Root")

        assert history.get_stack_depth(chat_id) == 1
        assert history.get_current(chat_id) == "Root"
        assert history.can_go_back(chat_id) is True

    def test_push_multiple_nodes(self):
        """Test pushing multiple nodes."""
        history = NavigationHistory()
        chat_id = 123

        history.push(chat_id, "Root")
        history.push(chat_id, "CheckMotor")
        history.push(chat_id, "CheckTemp")

        assert history.get_stack_depth(chat_id) == 3
        assert history.get_current(chat_id) == "CheckTemp"
        assert history.get_full_path(chat_id) == ["Root", "CheckMotor", "CheckTemp"]

    def test_pop_single_node(self):
        """Test popping a single node."""
        history = NavigationHistory()
        chat_id = 123

        history.push(chat_id, "Root")
        history.push(chat_id, "CheckMotor")

        popped = history.pop(chat_id)

        assert popped == "CheckMotor"
        assert history.get_stack_depth(chat_id) == 1
        assert history.get_current(chat_id) == "Root"

    def test_pop_multiple_nodes(self):
        """Test popping multiple nodes."""
        history = NavigationHistory()
        chat_id = 123

        history.push(chat_id, "A")
        history.push(chat_id, "B")
        history.push(chat_id, "C")

        assert history.pop(chat_id) == "C"
        assert history.pop(chat_id) == "B"
        assert history.pop(chat_id) == "A"
        assert history.pop(chat_id) is None  # Empty stack

    def test_pop_empty_stack(self):
        """Test popping from empty stack."""
        history = NavigationHistory()
        chat_id = 123

        popped = history.pop(chat_id)

        assert popped is None
        assert history.get_stack_depth(chat_id) == 0
        assert history.can_go_back(chat_id) is False

    def test_peek_does_not_modify(self):
        """Test that peek doesn't modify the stack."""
        history = NavigationHistory()
        chat_id = 123

        history.push(chat_id, "Root")
        history.push(chat_id, "CheckMotor")

        current = history.peek(chat_id)
        assert current == "CheckMotor"
        assert history.get_stack_depth(chat_id) == 2  # Stack unchanged

    def test_can_go_back(self):
        """Test can_go_back logic."""
        history = NavigationHistory()
        chat_id = 123

        # Empty stack - can't go back
        assert history.can_go_back(chat_id) is False

        # With nodes - can go back
        history.push(chat_id, "Root")
        assert history.can_go_back(chat_id) is True

        # Clear stack - can't go back
        history.clear(chat_id)
        assert history.can_go_back(chat_id) is False

    def test_clear_session(self):
        """Test clearing a session."""
        history = NavigationHistory()
        chat_id = 123

        history.push(chat_id, "Root")
        history.push(chat_id, "CheckMotor")

        assert history.get_stack_depth(chat_id) == 2

        history.clear(chat_id)

        assert history.get_stack_depth(chat_id) == 0
        assert history.can_go_back(chat_id) is False
        assert chat_id not in history._sessions

    def test_tree_isolation(self):
        """Test that different trees have separate histories."""
        history = NavigationHistory()
        chat_id = 123

        # Start with tree 1
        history.push(chat_id, "Root", tree_id=1)
        history.push(chat_id, "Node1", tree_id=1)

        assert history.get_stack_depth(chat_id) == 2

        # Switch to tree 2 - should clear history
        history.push(chat_id, "Root2", tree_id=2)

        assert history.get_stack_depth(chat_id) == 1
        assert history.get_current(chat_id) == "Root2"

    def test_max_stack_depth_enforcement(self):
        """Test that stack depth limit is enforced."""
        history = NavigationHistory(max_stack_depth=3)
        chat_id = 123

        # Push 5 nodes (limit is 3)
        history.push(chat_id, "A")
        history.push(chat_id, "B")
        history.push(chat_id, "C")
        history.push(chat_id, "D")  # Should remove "A"
        history.push(chat_id, "E")  # Should remove "B"

        assert history.get_stack_depth(chat_id) == 3
        assert history.get_full_path(chat_id) == ["C", "D", "E"]

    def test_multiple_users_isolation(self):
        """Test that multiple users have isolated stacks."""
        history = NavigationHistory()
        chat1 = 111
        chat2 = 222

        # User 1 navigates
        history.push(chat1, "Root1")
        history.push(chat1, "Node1")

        # User 2 navigates
        history.push(chat2, "Root2")
        history.push(chat2, "Node2")
        history.push(chat2, "Node3")

        # Check isolation
        assert history.get_stack_depth(chat1) == 2
        assert history.get_stack_depth(chat2) == 3
        assert history.get_current(chat1) == "Node1"
        assert history.get_current(chat2) == "Node3"

    def test_get_full_path(self):
        """Test getting complete navigation path."""
        history = NavigationHistory()
        chat_id = 123

        history.push(chat_id, "Root")
        history.push(chat_id, "CheckMotor")
        history.push(chat_id, "CheckTemp")

        path = history.get_full_path(chat_id)

        assert path == ["Root", "CheckMotor", "CheckTemp"]
        assert isinstance(path, list)  # Should be a copy

    def test_get_session_info(self):
        """Test getting session information."""
        history = NavigationHistory()
        chat_id = 123

        # Non-existent session
        info = history.get_session_info(chat_id)
        assert info["exists"] is False

        # Existing session
        history.push(chat_id, "Root", tree_id=42)
        info = history.get_session_info(chat_id)

        assert info["exists"] is True
        assert info["chat_id"] == 123
        assert info["tree_id"] == 42
        assert info["stack_depth"] == 1
        assert info["can_go_back"] is True
        assert "last_accessed" in info
        assert "age_seconds" in info

    def test_get_stats(self):
        """Test getting global statistics."""
        history = NavigationHistory()

        # Empty stats
        stats = history.get_stats()
        assert stats["total_sessions"] == 0
        assert stats["total_nodes"] == 0

        # With data
        history.push(111, "A")
        history.push(111, "B")
        history.push(222, "C")

        stats = history.get_stats()
        assert stats["total_sessions"] == 2
        assert stats["total_nodes"] == 3
        assert stats["avg_stack_depth"] == 1.5
        assert stats["max_stack_depth"] == 2

    def test_cleanup_old_sessions(self):
        """Test automatic session cleanup."""
        # Use very short timeout for testing
        history = NavigationHistory(session_timeout_hours=0.001)  # ~3.6 seconds
        chat_id = 123

        history.push(chat_id, "Root")
        assert chat_id in history._sessions

        # Manually set old access time
        history._sessions[chat_id].last_accessed = datetime.utcnow() - timedelta(hours=1)

        # Run cleanup
        cleaned = history.cleanup_old_sessions()

        assert cleaned == 1
        assert chat_id not in history._sessions

    def test_get_all_sessions_info(self):
        """Test getting info for all sessions."""
        history = NavigationHistory()

        history.push(111, "A")
        history.push(222, "B")
        history.push(333, "C")

        all_info = history.get_all_sessions_info()

        assert len(all_info) == 3
        assert all(info["exists"] for info in all_info)
        chat_ids = [info["chat_id"] for info in all_info]
        assert set(chat_ids) == {111, 222, 333}


class TestGlobalSingleton:
    """Test global singleton pattern."""

    def test_get_navigation_history_singleton(self):
        """Test that get_navigation_history returns same instance."""
        history1 = get_navigation_history()
        history2 = get_navigation_history()

        assert history1 is history2  # Same object

    def test_singleton_persists_data(self):
        """Test that singleton persists data between calls."""
        history1 = get_navigation_history()
        history1.push(999, "TestNode")

        history2 = get_navigation_history()
        assert history2.get_current(999) == "TestNode"


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_pop_nonexistent_session(self):
        """Test popping from non-existent session."""
        history = NavigationHistory()
        result = history.pop(999)

        assert result is None

    def test_peek_nonexistent_session(self):
        """Test peeking at non-existent session."""
        history = NavigationHistory()
        result = history.peek(999)

        assert result is None

    def test_clear_nonexistent_session(self):
        """Test clearing non-existent session (should not error)."""
        history = NavigationHistory()
        history.clear(999)  # Should not raise

    def test_can_go_back_nonexistent_session(self):
        """Test can_go_back for non-existent session."""
        history = NavigationHistory()
        result = history.can_go_back(999)

        assert result is False

    def test_zero_max_stack_depth(self):
        """Test with zero max stack depth."""
        history = NavigationHistory(max_stack_depth=0)
        chat_id = 123

        # Should immediately evict on push
        history.push(chat_id, "A")
        # Stack is always empty due to limit
        assert history.get_stack_depth(chat_id) == 0

    def test_push_none_tree_id(self):
        """Test pushing with None tree ID."""
        history = NavigationHistory()
        chat_id = 123

        history.push(chat_id, "Root", tree_id=None)
        history.push(chat_id, "Node", tree_id=None)

        assert history.get_stack_depth(chat_id) == 2


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_linear_navigation_with_back(self):
        """Test typical linear navigation with back button."""
        history = NavigationHistory()
        chat_id = 123

        # User path: Root -> A -> B -> C
        history.push(chat_id, "Root")
        history.push(chat_id, "A")
        history.push(chat_id, "B")
        history.push(chat_id, "C")

        # User clicks back twice: C -> B -> A
        assert history.pop(chat_id) == "C"
        assert history.pop(chat_id) == "B"
        assert history.get_current(chat_id) == "A"

        # User navigates forward again
        history.push(chat_id, "D")
        assert history.get_full_path(chat_id) == ["Root", "A", "D"]

    def test_branching_navigation(self):
        """Test navigation through branching tree."""
        history = NavigationHistory()
        chat_id = 123

        # Root -> Left -> Left_A
        history.push(chat_id, "Root")
        history.push(chat_id, "Left")
        history.push(chat_id, "Left_A")

        # Back to Left
        history.pop(chat_id)

        # Take different branch: Left -> Left_B
        history.push(chat_id, "Left_B")

        assert history.get_full_path(chat_id) == ["Root", "Left", "Left_B"]

    def test_session_restart(self):
        """Test restarting session mid-troubleshooting."""
        history = NavigationHistory()
        chat_id = 123

        # User navigates deep
        history.push(chat_id, "Root")
        history.push(chat_id, "A")
        history.push(chat_id, "B")

        # User decides to start over
        history.clear(chat_id)

        # New session
        history.push(chat_id, "Root")

        assert history.get_stack_depth(chat_id) == 1
        assert history.get_current(chat_id) == "Root"

    def test_multiple_concurrent_users(self):
        """Test multiple users navigating simultaneously."""
        history = NavigationHistory()

        # User 1: Equipment A troubleshooting
        history.push(111, "Root", tree_id=1)
        history.push(111, "CheckMotor", tree_id=1)

        # User 2: Equipment B troubleshooting
        history.push(222, "Root", tree_id=2)
        history.push(222, "CheckPump", tree_id=2)

        # User 3: Equipment A troubleshooting (same tree as user 1)
        history.push(333, "Root", tree_id=1)
        history.push(333, "CheckElectrical", tree_id=1)

        # Verify isolation
        assert history.get_current(111) == "CheckMotor"
        assert history.get_current(222) == "CheckPump"
        assert history.get_current(333) == "CheckElectrical"

        # User 1 goes back
        history.pop(111)
        assert history.get_current(111) == "Root"

        # Other users unaffected
        assert history.get_current(222) == "CheckPump"
        assert history.get_current(333) == "CheckElectrical"


if __name__ == '__main__':
    # Run tests with pytest if available, otherwise run basic tests
    try:
        import pytest
        pytest.main([__file__, '-v'])
    except ImportError:
        print("pytest not available, running basic tests...")

        # Run a few key tests manually
        test_nav = TestNavigationHistory()
        test_nav.test_initialization()
        print("✓ Initialization test passed")

        test_nav.test_push_multiple_nodes()
        print("✓ Push multiple nodes test passed")

        test_nav.test_pop_multiple_nodes()
        print("✓ Pop multiple nodes test passed")

        test_nav.test_tree_isolation()
        print("✓ Tree isolation test passed")

        test_nav.test_multiple_users_isolation()
        print("✓ Multiple users isolation test passed")

        print("\nAll basic tests passed!")
