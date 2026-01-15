# Back Navigation for Troubleshooting Trees

**Task**: TASK-9.7
**Status**: ✅ Completed
**Author**: Atlas Engineer

## Overview

The navigation history system enables users to navigate backward through troubleshooting decision trees using a "⬅️ Back" button. The system maintains a per-user navigation stack that tracks the path taken through the tree, allowing users to return to previous decision points.

## Features

- ✅ Back button appears on all non-root nodes
- ✅ Returns to exact previous state
- ✅ Navigation stack persists per user session
- ✅ Stack automatically clears on new tree start
- ✅ Works correctly with branching paths
- ✅ Tree isolation (different trees have separate histories)
- ✅ Automatic session cleanup (24-hour timeout by default)
- ✅ Stack depth limits to prevent memory issues
- ✅ Multi-user isolation (concurrent users don't interfere)

## Architecture

### Core Components

```
rivet_pro/troubleshooting/
├── history.py              # NavigationHistory implementation
├── test_history.py         # Comprehensive test suite (32 tests)
└── README_NAVIGATION.md    # This file
```

### Key Classes

#### `NavigationHistory`

Main class managing navigation stacks for all users.

```python
from rivet_pro.troubleshooting import NavigationHistory

history = NavigationHistory(
    max_stack_depth=50,        # Maximum nodes to remember
    session_timeout_hours=24   # Auto-cleanup old sessions
)
```

#### `NavigationSession`

Dataclass representing a single user's navigation session.

```python
@dataclass
class NavigationSession:
    chat_id: int
    tree_id: Optional[int]
    stack: List[str]
    last_accessed: datetime
```

## Usage

### Basic Navigation Flow

```python
from rivet_pro.troubleshooting import get_navigation_history

# Get global instance
history = get_navigation_history()

chat_id = 123456  # User's Telegram chat ID

# User starts at root
history.push(chat_id, node_id="Root", tree_id=1)

# User navigates: Root -> CheckMotor -> CheckTemp
history.push(chat_id, node_id="CheckMotor", tree_id=1)
history.push(chat_id, node_id="CheckTemp", tree_id=1)

# Check if user can go back
if history.can_go_back(chat_id):
    # Show back button
    pass

# User clicks back button
previous_node = history.pop(chat_id)  # Returns "CheckTemp"
# Navigate to previous_node

# Get full navigation path for breadcrumbs
path = history.get_full_path(chat_id)  # ["Root", "CheckMotor"]
```

### Integration with TreeNavigator

```python
from rivet_pro.troubleshooting import get_navigation_history, TreeNavigator

history = get_navigation_history()
navigator = TreeNavigator()

async def handle_navigation(update, context, tree, target_node):
    """Handle forward navigation with history tracking."""
    chat_id = update.effective_chat.id

    # Get current node before navigating
    current_node = navigator.get_current_node(update)

    # Save current position to history
    if current_node:
        history.push(chat_id, current_node, tree_id=tree.id)

    # Navigate to new node
    await navigator.navigate_to(update, context, tree, target_node)

async def handle_back_button(update, context, tree):
    """Handle back button press."""
    chat_id = update.effective_chat.id

    # Pop previous node from history
    previous_node = history.pop(chat_id)

    if previous_node:
        # Navigate back to previous node
        await navigator.navigate_to(update, context, tree, previous_node)
    else:
        # At root, no previous node
        await update.callback_query.answer("Already at the beginning")
```

### Keyboard Integration

```python
from rivet_pro.troubleshooting.keyboard import build_navigation_keyboard
from rivet_pro.troubleshooting import get_navigation_history

history = get_navigation_history()
chat_id = update.effective_chat.id

# Build keyboard with back button
keyboard = build_navigation_keyboard(
    current_node="CheckMotor",
    edges=[
        {"to": "CheckTemp", "label": "Check Temperature"},
        {"to": "CheckVibration", "label": "Check Vibration"}
    ],
    include_back_button=history.can_go_back(chat_id),
    parent_node=history.peek(chat_id)  # Previous node
)
```

## Session Management

### Tree Isolation

Different troubleshooting trees maintain separate navigation histories:

```python
# User starts Tree 1 (Motor troubleshooting)
history.push(chat_id, "Root", tree_id=1)
history.push(chat_id, "CheckMotor", tree_id=1)

# User switches to Tree 2 (Pump troubleshooting)
# History automatically clears
history.push(chat_id, "Root", tree_id=2)

assert history.get_stack_depth(chat_id) == 1  # Only "Root" in stack
```

### Clearing Sessions

```python
# Explicitly clear navigation history
history.clear(chat_id)

# Or let it auto-clear on tree change (handled automatically)
```

### Automatic Cleanup

Old sessions are automatically cleaned up after 24 hours of inactivity:

```python
# Manual cleanup (called periodically by background task)
cleaned_count = history.cleanup_old_sessions()
print(f"Cleaned up {cleaned_count} expired sessions")
```

## Stack Depth Management

The navigation stack has a configurable maximum depth (default: 50 nodes):

```python
history = NavigationHistory(max_stack_depth=50)

# When limit is reached, oldest entries are removed
for i in range(60):
    history.push(chat_id, f"Node{i}")

# Stack maintains only the 50 most recent nodes
assert history.get_stack_depth(chat_id) == 50
```

## Multi-User Support

Each user has an isolated navigation stack:

```python
# User 1 navigates their tree
history.push(111, "Root", tree_id=1)
history.push(111, "CheckMotor", tree_id=1)

# User 2 navigates independently
history.push(222, "Root", tree_id=2)
history.push(222, "CheckPump", tree_id=2)

# No interference between users
assert history.get_current(111) == "CheckMotor"
assert history.get_current(222) == "CheckPump"
```

## Debugging and Monitoring

### Session Information

```python
# Get detailed session info
info = history.get_session_info(chat_id)
print(f"""
Session exists: {info['exists']}
Chat ID: {info['chat_id']}
Tree ID: {info['tree_id']}
Stack depth: {info['stack_depth']}
Stack: {info['stack']}
Can go back: {info['can_go_back']}
Last accessed: {info['last_accessed']}
Age (seconds): {info['age_seconds']}
""")
```

### Global Statistics

```python
# Get overall statistics
stats = history.get_stats()
print(f"""
Total sessions: {stats['total_sessions']}
Total nodes: {stats['total_nodes']}
Average stack depth: {stats['avg_stack_depth']}
Max stack depth: {stats['max_stack_depth']}
""")
```

### All Sessions Overview

```python
# Get info for all active sessions
all_sessions = history.get_all_sessions_info()
for session in all_sessions:
    print(f"Chat {session['chat_id']}: {session['stack_depth']} nodes")
```

## Testing

Comprehensive test suite with 32 tests covering:

- Basic push/pop operations
- Stack depth management
- Tree isolation
- Multi-user isolation
- Session cleanup
- Edge cases (empty stacks, zero depth limit)
- Real-world scenarios (branching, back navigation)

Run tests:

```bash
cd C:/Users/hharp/OneDrive/Desktop/Rivet-PRO
python -m pytest rivet_pro/troubleshooting/test_history.py -v
```

Expected result: **32 passed**

## Performance Considerations

- **Memory**: ~200-500 bytes per node in stack
- **Typical stack depth**: 5-10 nodes per user
- **Max concurrent users**: Limited only by available memory
- **Operation complexity**: O(1) for push, pop, peek
- **Cleanup**: O(n) where n = number of sessions (run periodically)

### Example Memory Usage

```
1,000 users × 10 nodes × 400 bytes = ~4 MB
10,000 users × 10 nodes × 400 bytes = ~40 MB
```

## API Reference

### NavigationHistory

#### Methods

- `push(chat_id, node_id, tree_id=None)` - Add node to history
- `pop(chat_id) -> Optional[str]` - Remove and return last node
- `peek(chat_id) -> Optional[str]` - View last node without removing
- `get_current(chat_id) -> Optional[str]` - Alias for peek()
- `can_go_back(chat_id) -> bool` - Check if back navigation possible
- `get_stack_depth(chat_id) -> int` - Get number of nodes in stack
- `get_full_path(chat_id) -> List[str]` - Get complete navigation path
- `clear(chat_id)` - Clear navigation history for user
- `cleanup_old_sessions() -> int` - Remove expired sessions
- `get_session_info(chat_id) -> Dict` - Get session details
- `get_all_sessions_info() -> List[Dict]` - Get all sessions
- `get_stats() -> Dict` - Get global statistics

#### Configuration

```python
NavigationHistory(
    max_stack_depth=50,        # Max nodes per user (default: 50)
    session_timeout_hours=24   # Auto-cleanup timeout (default: 24)
)
```

### Global Singleton

```python
from rivet_pro.troubleshooting import get_navigation_history

# Get shared instance across application
history = get_navigation_history()
```

## Integration Checklist

To integrate back navigation into your troubleshooting bot:

- [ ] Import NavigationHistory: `from rivet_pro.troubleshooting import get_navigation_history`
- [ ] Get global instance: `history = get_navigation_history()`
- [ ] Push current node before navigating forward
- [ ] Add back button when `history.can_go_back(chat_id)` returns True
- [ ] Handle back button callback by calling `history.pop(chat_id)`
- [ ] Clear history when starting new tree: `history.clear(chat_id)`
- [ ] Set up periodic cleanup task for `history.cleanup_old_sessions()`

## Example Bot Handler

```python
from telegram.ext import CallbackQueryHandler
from rivet_pro.troubleshooting import get_navigation_history

history = get_navigation_history()

async def callback_query_handler(update, context):
    """Handle troubleshooting navigation callbacks."""
    query = update.callback_query
    chat_id = update.effective_chat.id

    # Decode callback data
    data = decode_callback(query.data)

    if data.action == 'back':
        # Handle back navigation
        previous_node = history.pop(chat_id)
        if previous_node:
            await show_node(update, context, previous_node)
        else:
            await query.answer("Already at the beginning")

    elif data.action == 'navigate':
        # Handle forward navigation
        current_node = get_current_node(update)
        history.push(chat_id, current_node, tree_id=data.tree_id)
        await show_node(update, context, data.node_id)

    await query.answer()

# Register handler
application.add_handler(CallbackQueryHandler(callback_query_handler))
```

## Acceptance Criteria Verification

✅ **Back button appears on all non-root nodes**
- Implemented via `include_back_button=history.can_go_back(chat_id)` in keyboard builder

✅ **Returns to exact previous state**
- Stack maintains exact node IDs, navigator restores previous node

✅ **Navigation stack persists per user session**
- Dictionary keyed by chat_id maintains isolation between users

✅ **Stack clears on new tree start**
- Tree ID tracking automatically clears stack on tree change

✅ **Works correctly with branching paths**
- Stack-based design naturally handles branching (tested in test suite)

## Related Documentation

- `callback.py` - Callback data encoding/decoding
- `keyboard.py` - Keyboard generation with back button support
- `navigator.py` - Tree navigation with message editing
- `mermaid_parser.py` - Troubleshooting tree parsing

## License

Part of RIVET Pro - Atlas CMMS
Copyright © 2026
