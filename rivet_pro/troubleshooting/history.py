"""
Navigation History Management for Troubleshooting Trees

Maintains per-user navigation stacks to enable back navigation through
troubleshooting decision trees. Supports branching paths, session isolation,
and automatic cleanup.

Features:
- Per-user navigation stack (chat_id based)
- Push/pop operations for tree traversal
- Clear on new tree start
- Session isolation (multiple users, multiple trees)
- Memory-efficient storage with automatic cleanup

Example:
    >>> history = NavigationHistory()
    >>>
    >>> # User navigates: Root -> CheckMotor -> CheckTemp
    >>> history.push(chat_id=123, node_id="Root")
    >>> history.push(chat_id=123, node_id="CheckMotor")
    >>> history.push(chat_id=123, node_id="CheckTemp")
    >>>
    >>> # User clicks back
    >>> prev = history.pop(chat_id=123)  # Returns "CheckMotor"
    >>> prev = history.pop(chat_id=123)  # Returns "Root"
    >>> prev = history.pop(chat_id=123)  # Returns None (at root)
    >>>
    >>> # Start new tree - clears history
    >>> history.clear(chat_id=123)
"""

import logging
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class NavigationSession:
    """
    Navigation session data for a single user/chat.

    Attributes:
        chat_id: Telegram chat ID
        tree_id: Current troubleshooting tree ID
        stack: Navigation history stack (oldest to newest)
        last_accessed: Last access timestamp for cleanup
    """
    chat_id: int
    tree_id: Optional[int] = None
    stack: List[str] = field(default_factory=list)
    last_accessed: datetime = field(default_factory=datetime.utcnow)

    def update_access_time(self):
        """Update last accessed timestamp."""
        self.last_accessed = datetime.utcnow()


class NavigationHistory:
    """
    Manages navigation history for troubleshooting tree traversal.

    Features:
    - Per-chat navigation stacks
    - Automatic session cleanup (configurable timeout)
    - Tree isolation (different trees have separate histories)
    - Stack depth limits to prevent memory issues
    - Debug logging for troubleshooting

    Usage:
        history = NavigationHistory(max_stack_depth=50)

        # User starts at root
        history.push(chat_id=123, node_id="Root", tree_id=1)

        # User navigates forward
        history.push(chat_id=123, node_id="CheckMotor", tree_id=1)
        history.push(chat_id=123, node_id="CheckTemp", tree_id=1)

        # User goes back
        prev_node = history.pop(chat_id=123)  # Returns "CheckTemp"

        # Check where we can go back to
        can_go_back = history.can_go_back(chat_id=123)

        # Get current position
        current = history.get_current(chat_id=123)

        # Start new tree (clears history)
        history.clear(chat_id=123)
    """

    # Default configuration
    DEFAULT_MAX_STACK_DEPTH = 50
    DEFAULT_SESSION_TIMEOUT_HOURS = 24

    def __init__(
        self,
        max_stack_depth: int = DEFAULT_MAX_STACK_DEPTH,
        session_timeout_hours: int = DEFAULT_SESSION_TIMEOUT_HOURS
    ):
        """
        Initialize NavigationHistory manager.

        Args:
            max_stack_depth: Maximum stack depth per session (default: 50)
            session_timeout_hours: Auto-cleanup sessions older than N hours (default: 24)
        """
        self._sessions: Dict[int, NavigationSession] = {}
        self._max_stack_depth = max_stack_depth
        self._session_timeout = timedelta(hours=session_timeout_hours)

        logger.info(
            f"NavigationHistory initialized: "
            f"max_depth={max_stack_depth}, timeout={session_timeout_hours}h"
        )

    def _get_or_create_session(self, chat_id: int) -> NavigationSession:
        """
        Get existing session or create new one.

        Args:
            chat_id: Telegram chat ID

        Returns:
            NavigationSession instance
        """
        if chat_id not in self._sessions:
            self._sessions[chat_id] = NavigationSession(chat_id=chat_id)
            logger.debug(f"Created new navigation session for chat {chat_id}")

        session = self._sessions[chat_id]
        session.update_access_time()
        return session

    def push(self, chat_id: int, node_id: str, tree_id: Optional[int] = None):
        """
        Push a node onto the navigation stack.

        This is called BEFORE navigating forward to record where we came from.

        Args:
            chat_id: Telegram chat ID
            node_id: Node identifier to push
            tree_id: Optional tree ID for tree isolation

        Example:
            # User at Root, clicking to CheckMotor
            history.push(chat_id=123, node_id="Root")  # Save current position
            # Then navigate to CheckMotor
        """
        session = self._get_or_create_session(chat_id)

        # If tree changed, clear old history
        if tree_id is not None and session.tree_id != tree_id:
            logger.info(f"Tree changed for chat {chat_id}: {session.tree_id} -> {tree_id}")
            session.stack.clear()
            session.tree_id = tree_id

        # Enforce stack depth limit
        if len(session.stack) >= self._max_stack_depth and self._max_stack_depth > 0:
            # Remove oldest entry (bottom of stack)
            removed = session.stack.pop(0)
            logger.warning(
                f"Stack depth limit reached for chat {chat_id}. "
                f"Removed oldest node: {removed}"
            )

        # Push node onto stack (only if max_stack_depth allows)
        if self._max_stack_depth > 0:
            session.stack.append(node_id)
            logger.debug(
                f"Pushed node '{node_id}' for chat {chat_id}. "
                f"Stack depth: {len(session.stack)}"
            )
        else:
            logger.debug(
                f"Skipped push for chat {chat_id} - max_stack_depth is 0"
            )

    def pop(self, chat_id: int) -> Optional[str]:
        """
        Pop a node from the navigation stack.

        This is called when the user clicks the Back button.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Previous node ID, or None if stack is empty

        Example:
            # User at CheckTemp, stack is [Root, CheckMotor]
            prev = history.pop(chat_id=123)  # Returns "CheckMotor"
            # Now stack is [Root], navigate to CheckMotor
        """
        if chat_id not in self._sessions:
            logger.debug(f"No session found for chat {chat_id} during pop")
            return None

        session = self._sessions[chat_id]
        session.update_access_time()

        if not session.stack:
            logger.debug(f"Stack empty for chat {chat_id}, cannot pop")
            return None

        # Pop from end (most recent)
        node_id = session.stack.pop()
        logger.debug(
            f"Popped node '{node_id}' for chat {chat_id}. "
            f"Remaining depth: {len(session.stack)}"
        )

        return node_id

    def peek(self, chat_id: int) -> Optional[str]:
        """
        Peek at the top of the stack without removing it.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Top node ID, or None if stack is empty
        """
        if chat_id not in self._sessions:
            return None

        session = self._sessions[chat_id]
        session.update_access_time()

        return session.stack[-1] if session.stack else None

    def get_current(self, chat_id: int) -> Optional[str]:
        """
        Get the current node (top of stack) without popping.

        Alias for peek() with clearer semantic meaning.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Current node ID, or None if stack is empty
        """
        return self.peek(chat_id)

    def can_go_back(self, chat_id: int) -> bool:
        """
        Check if back navigation is possible.

        Args:
            chat_id: Telegram chat ID

        Returns:
            True if stack has at least one node, False otherwise
        """
        if chat_id not in self._sessions:
            return False

        session = self._sessions[chat_id]
        has_history = len(session.stack) > 0

        logger.debug(f"Can go back for chat {chat_id}: {has_history}")
        return has_history

    def get_stack_depth(self, chat_id: int) -> int:
        """
        Get current stack depth for debugging.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Number of nodes in the stack
        """
        if chat_id not in self._sessions:
            return 0

        return len(self._sessions[chat_id].stack)

    def get_full_path(self, chat_id: int) -> List[str]:
        """
        Get the complete navigation path (entire stack).

        Useful for debugging and showing breadcrumb navigation.

        Args:
            chat_id: Telegram chat ID

        Returns:
            List of node IDs from oldest to newest
        """
        if chat_id not in self._sessions:
            return []

        session = self._sessions[chat_id]
        session.update_access_time()

        return session.stack.copy()

    def clear(self, chat_id: int):
        """
        Clear navigation history for a chat session.

        This should be called when:
        - User starts a new troubleshooting tree
        - User explicitly resets navigation
        - Session times out or ends

        Args:
            chat_id: Telegram chat ID
        """
        if chat_id in self._sessions:
            stack_size = len(self._sessions[chat_id].stack)
            del self._sessions[chat_id]
            logger.info(f"Cleared navigation history for chat {chat_id} ({stack_size} nodes)")
        else:
            logger.debug(f"No session to clear for chat {chat_id}")

    def cleanup_old_sessions(self):
        """
        Remove sessions that haven't been accessed within timeout period.

        This should be called periodically to prevent memory leaks from
        abandoned sessions.

        Returns:
            Number of sessions cleaned up
        """
        now = datetime.utcnow()
        expired_chats = []

        for chat_id, session in self._sessions.items():
            age = now - session.last_accessed
            if age > self._session_timeout:
                expired_chats.append(chat_id)

        # Clean up expired sessions
        for chat_id in expired_chats:
            stack_size = len(self._sessions[chat_id].stack)
            del self._sessions[chat_id]
            logger.info(
                f"Cleaned up expired session for chat {chat_id} "
                f"(age: {age.total_seconds() / 3600:.1f}h, stack: {stack_size} nodes)"
            )

        if expired_chats:
            logger.info(f"Cleaned up {len(expired_chats)} expired sessions")

        return len(expired_chats)

    def get_session_info(self, chat_id: int) -> Dict:
        """
        Get session information for debugging.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Dictionary with session details
        """
        if chat_id not in self._sessions:
            return {
                "exists": False,
                "chat_id": chat_id
            }

        session = self._sessions[chat_id]
        age = datetime.utcnow() - session.last_accessed

        return {
            "exists": True,
            "chat_id": chat_id,
            "tree_id": session.tree_id,
            "stack_depth": len(session.stack),
            "stack": session.stack.copy(),
            "can_go_back": len(session.stack) > 0,
            "last_accessed": session.last_accessed.isoformat(),
            "age_seconds": age.total_seconds()
        }

    def get_all_sessions_info(self) -> List[Dict]:
        """
        Get information about all active sessions.

        Useful for monitoring and debugging.

        Returns:
            List of session info dictionaries
        """
        return [
            self.get_session_info(chat_id)
            for chat_id in self._sessions.keys()
        ]

    def get_stats(self) -> Dict:
        """
        Get global statistics about navigation history.

        Returns:
            Dictionary with overall statistics
        """
        total_sessions = len(self._sessions)
        total_nodes = sum(len(s.stack) for s in self._sessions.values())

        if total_sessions > 0:
            avg_stack_depth = total_nodes / total_sessions
            max_stack_depth = max(len(s.stack) for s in self._sessions.values())
            oldest_session = min(s.last_accessed for s in self._sessions.values())
            newest_session = max(s.last_accessed for s in self._sessions.values())
        else:
            avg_stack_depth = 0
            max_stack_depth = 0
            oldest_session = None
            newest_session = None

        return {
            "total_sessions": total_sessions,
            "total_nodes": total_nodes,
            "avg_stack_depth": round(avg_stack_depth, 2),
            "max_stack_depth": max_stack_depth,
            "max_allowed_depth": self._max_stack_depth,
            "session_timeout_hours": self._session_timeout.total_seconds() / 3600,
            "oldest_session": oldest_session.isoformat() if oldest_session else None,
            "newest_session": newest_session.isoformat() if newest_session else None
        }


# Global singleton instance for easy import
_global_history: Optional[NavigationHistory] = None


def get_navigation_history() -> NavigationHistory:
    """
    Get the global NavigationHistory instance (singleton pattern).

    Returns:
        Global NavigationHistory instance

    Example:
        >>> from rivet_pro.troubleshooting.history import get_navigation_history
        >>> history = get_navigation_history()
        >>> history.push(chat_id=123, node_id="Root")
    """
    global _global_history

    if _global_history is None:
        _global_history = NavigationHistory()
        logger.info("Created global NavigationHistory singleton")

    return _global_history


if __name__ == '__main__':
    # Demo and testing
    import time

    print("=== Navigation History Demo ===\n")

    history = NavigationHistory(max_stack_depth=5, session_timeout_hours=1)

    # Simulate user navigation
    chat_id = 123456

    print("1. User starts troubleshooting:")
    history.push(chat_id, "Root", tree_id=1)
    print(f"   Stack: {history.get_full_path(chat_id)}")
    print(f"   Can go back: {history.can_go_back(chat_id)}")

    print("\n2. User navigates: Root -> CheckMotor -> CheckTemp")
    history.push(chat_id, "CheckMotor", tree_id=1)
    history.push(chat_id, "CheckTemp", tree_id=1)
    print(f"   Stack: {history.get_full_path(chat_id)}")
    print(f"   Stack depth: {history.get_stack_depth(chat_id)}")

    print("\n3. User clicks back")
    prev = history.pop(chat_id)
    print(f"   Popped: {prev}")
    print(f"   Stack: {history.get_full_path(chat_id)}")
    print(f"   Current: {history.get_current(chat_id)}")

    print("\n4. User continues navigating")
    history.push(chat_id, "CheckBearings", tree_id=1)
    history.push(chat_id, "CheckLubrication", tree_id=1)
    print(f"   Stack: {history.get_full_path(chat_id)}")

    print("\n5. Test stack depth limit (max 5)")
    history.push(chat_id, "CheckVibration", tree_id=1)
    history.push(chat_id, "CheckAlignment", tree_id=1)  # Should remove oldest
    print(f"   Stack: {history.get_full_path(chat_id)}")
    print(f"   Stack depth: {history.get_stack_depth(chat_id)}")

    print("\n6. User starts new tree")
    history.clear(chat_id)
    print(f"   Stack after clear: {history.get_full_path(chat_id)}")
    print(f"   Can go back: {history.can_go_back(chat_id)}")

    print("\n7. Multiple users")
    history.push(123, "Root", tree_id=1)
    history.push(456, "Root", tree_id=2)
    history.push(123, "Node1", tree_id=1)
    history.push(456, "Node2", tree_id=2)

    print(f"   User 123 stack: {history.get_full_path(123)}")
    print(f"   User 456 stack: {history.get_full_path(456)}")

    print("\n8. Statistics")
    stats = history.get_stats()
    print(f"   Total sessions: {stats['total_sessions']}")
    print(f"   Total nodes: {stats['total_nodes']}")
    print(f"   Avg stack depth: {stats['avg_stack_depth']}")
    print(f"   Max stack depth: {stats['max_stack_depth']}")

    print("\n9. Session info")
    info = history.get_session_info(123)
    print(f"   Chat 123: {info}")

    print("\n=== Demo Complete ===")
