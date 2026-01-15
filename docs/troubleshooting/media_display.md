# Media Display with Captions

Support for displaying images and media at troubleshooting tree nodes with captions.

## Overview

The media display module enables visual troubleshooting guides by allowing tree nodes to include photos, diagrams, and other images alongside text instructions. Images display with the node text as a caption, with automatic fallback to text-only if media is unavailable.

## Features

- **Image Support**: JPEG and PNG formats
- **Flexible References**: URL or Telegram file_id
- **Caption Management**: Automatic truncation to Telegram's 1024 character limit
- **Graceful Fallback**: Text-only display if media unavailable
- **Update Support**: Handles transitions between text and media messages

## Tree Node Format

### Node with Media

```python
{
    "id": "CheckBearing",
    "label": "Inspect the bearing for wear marks. Look for:\n- Pitting\n- Discoloration\n- Cracks",
    "type": "action",
    "media": {
        "type": "photo",
        "url": "https://example.com/bearing-diagram.jpg"
    },
    "children": ["BearingGood", "BearingBad"]
}
```

### Node with Telegram file_id

```python
{
    "id": "WiringDiagram",
    "label": "Follow the wiring diagram for proper connections",
    "media": {
        "type": "photo",
        "file_id": "AgACAgIAAxkBAAI..."  # Previously uploaded to Telegram
    }
}
```

### Node without Media (text-only)

```python
{
    "id": "TextStep",
    "label": "Power down the equipment using the main disconnect",
    "type": "action"
}
```

## API Reference

### send_node_with_media()

Send a tree node to Telegram with optional media.

```python
from rivet_pro.troubleshooting import send_node_with_media

async def show_troubleshooting_step(update, context, node, keyboard):
    message_id = await send_node_with_media(
        update=update,
        context=context,
        node=node,
        reply_markup=keyboard
    )
```

**Behavior:**
- If node has valid media → sends photo with caption
- If media unavailable → sends text with "[Image unavailable]" prefix
- If no media field → sends regular text message

### update_node_with_media()

Update existing message with new node content.

```python
from rivet_pro.troubleshooting import update_node_with_media

async def navigate_to_node(query, new_node, keyboard):
    success = await update_node_with_media(
        query=query,
        node=new_node,
        reply_markup=keyboard
    )
```

**Behavior:**
- Text → text: Uses `edit_message_text()`
- Photo → photo: Uses `edit_message_media()`
- Text ↔ photo: Deletes old message, sends new one (Telegram limitation)

### truncate_caption()

Truncate caption to fit Telegram's 1024 character limit.

```python
from rivet_pro.troubleshooting import truncate_caption

long_text = "..." * 1000
truncated = truncate_caption(long_text)
# Result: 1024 characters ending with "..."
```

### validate_media_node()

Check if a node has valid media configuration.

```python
from rivet_pro.troubleshooting import validate_media_node

if validate_media_node(node):
    # Node has media and it's properly formatted
    pass
```

**Valid media requires:**
- `media` field is a dict
- `media["type"]` equals "photo"
- Either `media["url"]` or `media["file_id"]` present

### format_caption_with_fallback()

Format caption with unavailability notice if needed.

```python
from rivet_pro.troubleshooting import format_caption_with_fallback

# Media available
caption = format_caption_with_fallback("Check the motor", media_available=True)
# Result: "Check the motor"

# Media unavailable
caption = format_caption_with_fallback("Check the motor", media_available=False)
# Result: "[Image unavailable]\n\nCheck the motor"
```

## Usage Examples

### Example 1: Basic Photo Node

```python
from telegram import Update
from telegram.ext import ContextTypes
from rivet_pro.troubleshooting import send_node_with_media

async def show_bearing_inspection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    node = {
        "id": "InspectBearing",
        "label": "Check bearing for wear:\n• Pitting\n• Discoloration\n• Rough rotation",
        "media": {
            "type": "photo",
            "url": "https://maintenance-guides.com/bearing-inspection.jpg"
        }
    }

    await send_node_with_media(update, context, node)
```

### Example 2: Navigation with Media Updates

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from rivet_pro.troubleshooting import update_node_with_media

async def handle_navigation(query, next_node_id):
    # Load next node from tree
    next_node = get_node_by_id(next_node_id)

    # Build keyboard
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Done", callback_data="done")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back")]
    ])

    # Update message with new node (handles media automatically)
    await update_node_with_media(query, next_node, keyboard)
```

### Example 3: Dynamic Media from Database

```python
async def show_equipment_photo(update, context, equipment_id):
    # Get equipment with photo from database
    equipment = await db.fetchrow(
        "SELECT name, photo_url FROM equipment WHERE id = $1",
        equipment_id
    )

    node = {
        "id": f"equip_{equipment_id}",
        "label": f"Equipment: {equipment['name']}",
        "media": {
            "type": "photo",
            "url": equipment['photo_url']
        } if equipment['photo_url'] else None
    }

    await send_node_with_media(update, context, node)
```

### Example 4: Error Handling

```python
from rivet_pro.troubleshooting import (
    send_node_with_media,
    MediaDisplayError
)

async def safe_node_display(update, context, node):
    try:
        message_id = await send_node_with_media(update, context, node)
        logger.info(f"Displayed node {node['id']} | message_id={message_id}")
    except MediaDisplayError as e:
        logger.error(f"Failed to display node: {e}")
        # Fallback: send simple text message
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ Error displaying troubleshooting step. Please try again."
        )
```

## Telegram Limits

### Caption Length
- **Maximum**: 1024 characters
- **Auto-truncation**: Captions longer than 1024 chars are truncated with "..." suffix
- **Recommendation**: Keep captions under 800 characters for readability

### Photo Formats
- **Supported**: JPEG, PNG
- **Max file size**: 10 MB (Telegram limit)
- **Recommendations**:
  - Use compressed images (< 500 KB)
  - Dimensions: 800-1200px width optimal
  - Consider Telegram file_id for frequently used images (saves bandwidth)

### Message Updates
- **Text → Text**: Direct edit (fast)
- **Photo → Photo**: Media edit (fast)
- **Text ↔ Photo**: Delete + send (slight delay)

## Best Practices

### 1. Use Descriptive Captions

```python
# ❌ Bad: Too brief
{
    "label": "Check bearing"
}

# ✅ Good: Clear instructions
{
    "label": "Inspect motor bearing:\n1. Check for roughness\n2. Look for wear patterns\n3. Verify lubrication"
}
```

### 2. Optimize Image URLs

```python
# ❌ Bad: Unreliable external URL
{
    "media": {
        "url": "https://random-site.com/image.jpg"
    }
}

# ✅ Good: Self-hosted or Telegram file_id
{
    "media": {
        "url": "https://cdn.yourcompany.com/guides/bearing-inspection.jpg"
    }
}
```

### 3. Handle Missing Media Gracefully

```python
from rivet_pro.troubleshooting import validate_media_node

# Check before assuming media exists
if validate_media_node(node):
    logger.info(f"Node {node['id']} has media")
else:
    logger.info(f"Node {node['id']} is text-only")
```

### 4. Cache Telegram file_ids

```python
# First time: Upload and save file_id
async def upload_and_cache(photo_url, node_id):
    message = await bot.send_photo(
        chat_id=ADMIN_CHAT,
        photo=photo_url
    )

    file_id = message.photo[-1].file_id

    # Save for reuse
    await db.execute(
        "UPDATE nodes SET media_file_id = $1 WHERE id = $2",
        file_id, node_id
    )

    return file_id

# Subsequent uses: Use file_id (faster, no bandwidth)
node["media"]["file_id"] = cached_file_id
```

### 5. Monitor Media Availability

```python
from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)

# Log media failures for monitoring
async def display_with_monitoring(update, context, node):
    try:
        await send_node_with_media(update, context, node)
    except Exception as e:
        if validate_media_node(node):
            logger.warning(
                f"Media failed to load | node_id={node['id']} | "
                f"url={node['media'].get('url')} | error={e}"
            )
        raise
```

## Error Handling

### MediaDisplayError

Raised when both media and text fallback fail.

```python
from rivet_pro.troubleshooting import MediaDisplayError

try:
    await send_node_with_media(update, context, node)
except MediaDisplayError as e:
    # Catastrophic failure - notify user and log
    logger.error(f"Total display failure: {e}")
    await notify_admin(f"Media display broken: {e}")
```

**Common causes:**
- Invalid chat_id
- Bot blocked by user
- Network connectivity issues
- Telegram API downtime

### Graceful Degradation

The module automatically handles these scenarios:

1. **Invalid media URL** → Text-only with "[Image unavailable]"
2. **Telegram file_id expired** → Text-only with "[Image unavailable]"
3. **Network timeout** → Text-only with "[Image unavailable]"
4. **Unsupported format** → Ignored, treated as text-only node

## Integration with Tree Navigator

```python
# In tree_navigator.py (future implementation)

from rivet_pro.troubleshooting import (
    send_node_with_media,
    update_node_with_media
)

class TreeNavigator:
    async def show_node(self, update, context, node_id):
        """Display a tree node with media support."""
        node = self.get_node(node_id)
        keyboard = self.build_keyboard(node)

        # Automatically handles media if present
        await send_node_with_media(update, context, node, keyboard)

    async def navigate_to(self, query, node_id):
        """Navigate to a new node, updating message."""
        node = self.get_node(node_id)
        keyboard = self.build_keyboard(node)

        # Handles text↔media transitions automatically
        await update_node_with_media(query, node, keyboard)
```

## Testing

Run the test suite:

```bash
pytest tests/unit/test_media_display.py -v
```

**Test coverage:**
- Caption truncation (5 tests)
- Media node validation (7 tests)
- Media reference extraction (4 tests)
- Caption formatting (3 tests)
- Sending nodes with media (6 tests)
- Updating nodes with media (3 tests)
- API exports (1 test)

**Total: 29 tests**

## Future Enhancements

- [ ] Video support (short clips)
- [ ] Multiple images per node (gallery/carousel)
- [ ] Image compression before upload
- [ ] Automatic file_id caching service
- [ ] Analytics on media load success rates

## Related Documentation

- [Troubleshooting Trees](./troubleshooting_trees.md)
- [Tree Navigation](./tree_navigation.md)
- [Callback Data Encoding](./callback_encoding.md)
- [Safety Warnings](./safety_warnings.md)

---

**Module**: `rivet_pro/troubleshooting/media_display.py`
**Tests**: `tests/unit/test_media_display.py`
**Task**: TASK-9.5 (AC-TS-5)
