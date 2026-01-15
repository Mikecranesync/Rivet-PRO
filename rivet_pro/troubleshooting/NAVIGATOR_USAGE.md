# TreeNavigator Usage Guide

## Overview

`TreeNavigator` manages in-place message editing for troubleshooting tree navigation in Telegram bots. It provides seamless navigation through decision trees by editing messages instead of sending new ones, keeping chat history clean.

## Features

✅ **In-Place Editing** - Updates existing messages instead of sending new ones
✅ **Graceful Fallback** - Automatically handles edit failures by deleting and resending
✅ **Session Isolation** - Tracks message IDs per user/chat independently
✅ **Clean History** - No message spam during tree traversal
✅ **Error Resilient** - Handles BadRequest, TelegramError, and missing messages

## Basic Usage

### 1. Initialize Navigator

```python
from rivet_pro.troubleshooting import TreeNavigator

# Create a navigator instance (usually one per bot)
navigator = TreeNavigator()
```

### 2. Show Initial Node

```python
from telegram import Update
from telegram.ext import ContextTypes

async def start_troubleshooting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tree = load_troubleshooting_tree()  # Your tree implementation

    # First interaction - sends new message
    await navigator.show_node(
        update=update,
        context=context,
        tree=tree,
        node_id="root"
    )
```

### 3. Navigate Between Nodes

```python
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Extract node_id from callback data
    node_id = extract_node_id(query.data)

    tree = load_troubleshooting_tree()

    # Navigation - edits existing message
    await navigator.navigate_to(
        update=update,
        context=context,
        tree=tree,
        node_id=node_id
    )
```

## Advanced Usage

### Force New Message

Sometimes you want to send a new message instead of editing:

```python
# Force sending a new message (e.g., for important updates)
await navigator.show_node(
    update=update,
    context=context,
    tree=tree,
    node_id="warning",
    force_new=True
)
```

### Session Management

Clear session when ending troubleshooting:

```python
async def end_troubleshooting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Clear tracked messages and nodes
    navigator.clear_session(update)

    await update.message.reply_text("Troubleshooting session ended.")
```

### Debug Session Info

Get current session information:

```python
async def debug_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = navigator.get_session_info(update)

    print(f"Session Key: {info['session_key']}")
    print(f"Tracked Message ID: {info['tracked_message_id']}")
    print(f"Current Node: {info['current_node']}")
    print(f"Total Active Sessions: {info['total_sessions']}")
```

## Integration with TroubleshootingTree

The navigator expects your tree to implement these methods:

```python
class TroubleshootingTree:
    def get_node(self, node_id: str) -> Optional[Dict]:
        """Return node data or None if not found."""
        pass

    def render_node(self, node_id: str) -> str:
        """Return formatted text for the node."""
        pass

    def get_node_keyboard(self, node_id: str) -> InlineKeyboardMarkup:
        """Return keyboard markup for node navigation."""
        pass
```

## Complete Bot Example

```python
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from rivet_pro.troubleshooting import TreeNavigator, encode_callback

# Initialize navigator
navigator = TreeNavigator()

# Your tree implementation
class SimpleTree:
    def __init__(self):
        self.nodes = {
            "root": {
                "text": "Equipment not starting?",
                "children": ["check_power", "check_fuel"]
            },
            "check_power": {
                "text": "Is power connected?",
                "children": ["power_yes", "power_no"]
            },
            "check_fuel": {
                "text": "Is there fuel?",
                "children": ["fuel_yes", "fuel_no"]
            },
            "power_yes": {"text": "Power OK. Check fuel next.", "children": []},
            "power_no": {"text": "Connect power and try again.", "children": []},
            "fuel_yes": {"text": "Fuel OK. Contact support.", "children": []},
            "fuel_no": {"text": "Refuel and try again.", "children": []}
        }

    def get_node(self, node_id):
        return self.nodes.get(node_id)

    def render_node(self, node_id):
        node = self.nodes[node_id]
        return f"<b>Troubleshooting</b>\n\n{node['text']}"

    def get_node_keyboard(self, node_id):
        node = self.nodes[node_id]

        if not node["children"]:
            # Leaf node - just back button
            return InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Start Over", callback_data=encode_callback("nav", "root"))
            ]])

        # Navigation buttons
        buttons = []
        for child_id in node["children"]:
            child = self.nodes[child_id]
            buttons.append([
                InlineKeyboardButton(
                    child["text"][:30],  # Truncate long text
                    callback_data=encode_callback("nav", child_id)
                )
            ])

        return InlineKeyboardMarkup(buttons)

tree = SimpleTree()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start troubleshooting."""
    await navigator.show_node(update, context, tree, "root")

async def handle_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle navigation button clicks."""
    query = update.callback_query
    await query.answer()

    # Decode callback data
    from rivet_pro.troubleshooting import decode_callback
    callback_type, node_id = decode_callback(query.data)

    if callback_type == "nav":
        # Navigate to node
        await navigator.navigate_to(update, context, tree, node_id)

async def end_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """End troubleshooting session."""
    navigator.clear_session(update)
    await update.message.reply_text("Troubleshooting ended. Use /start to begin again.")

# Build application
app = Application.builder().token("YOUR_BOT_TOKEN").build()

app.add_handler(CommandHandler("start", start_command))
app.add_handler(CommandHandler("end", end_command))
app.add_handler(CallbackQueryHandler(handle_navigation, pattern="^nav:"))

# Run bot
app.run_polling()
```

## Error Handling

The navigator handles errors gracefully:

### Edit Failures

When `edit_message_text` fails (message too old, deleted, etc.):
1. Attempts to delete the old message
2. Sends a new message
3. Tracks the new message ID
4. Continues normally

### Delete Failures

If deleting the old message fails:
- Logs a warning
- Continues with sending new message
- User may see duplicate messages briefly (unavoidable)

### Telegram Errors

Network errors, rate limits, etc.:
- Falls back to delete+send strategy
- Logs errors for monitoring
- Keeps navigation functional

## Best Practices

### 1. Single Navigator Instance

Create one navigator per bot, not per handler:

```python
# ✅ Good - single instance
navigator = TreeNavigator()

# ❌ Bad - creates new instance each time
async def handler(update, context):
    navigator = TreeNavigator()  # Lost tracking!
```

### 2. Clear Sessions on Exit

Always clear sessions when done:

```python
async def cancel_handler(update, context):
    navigator.clear_session(update)
    await update.message.reply_text("Cancelled.")
```

### 3. Use force_new for Important Messages

Use `force_new=True` for critical updates:

```python
# Critical warning - don't edit existing message
await navigator.show_node(
    update, context, tree, "emergency_stop",
    force_new=True
)
```

### 4. Monitor Session Count

Track active sessions for debugging:

```python
# Periodically check session count
info = navigator.get_session_info(update)
if info['total_sessions'] > 1000:
    logger.warning(f"High session count: {info['total_sessions']}")
```

## Testing

Run the comprehensive test suite:

```bash
cd C:/Users/hharp/OneDrive/Desktop/Rivet-PRO
pytest rivet_pro/troubleshooting/test_navigator.py -v
```

Tests cover:
- Initial message sending
- In-place editing
- Edit failure fallback
- Session isolation
- Multiple navigations
- Error handling
- Force new messages

## Troubleshooting

### Navigator not editing messages

**Symptom:** New messages sent instead of editing

**Causes:**
- Creating new navigator instance per handler
- Message too old (>48 hours)
- Bot restarted (lost in-memory tracking)

**Solutions:**
- Use single navigator instance
- Clear sessions on bot restart
- Use force_new for old sessions

### Multiple messages in chat

**Symptom:** Duplicate messages during navigation

**Causes:**
- Edit failure and delete failure together
- Very old messages can't be deleted

**Solutions:**
- Normal behavior for old messages
- Clear sessions regularly
- Acceptable edge case

### Session memory leak

**Symptom:** Growing memory usage

**Causes:**
- Sessions not cleared after completion
- Abandoned sessions

**Solutions:**
- Call `clear_session()` on end
- Implement session timeout
- Periodic cleanup of old sessions

## Implementation Notes

### Message ID Tracking

The navigator tracks message IDs in-memory:
- Stored in dict: `{(chat_id, user_id): message_id}`
- Lost on bot restart (acceptable - falls back to new message)
- Consider Redis for persistent tracking in production

### Thread Safety

Current implementation is NOT thread-safe. For multi-threaded bots:
- Use locks around _message_map access
- Or use thread-safe collections
- Or implement per-thread instances

### Scalability

For high-traffic bots:
- Implement session expiry (TTL)
- Use external storage (Redis)
- Monitor memory usage
- Consider stateless approach with callback data

## API Reference

See docstrings in `navigator.py` for complete API documentation.
