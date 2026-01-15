# Safety Warning Formatting Module

**Task**: TASK-9.6
**Purpose**: Format safety warnings using Telegram blockquote style for visual distinction in troubleshooting trees.

## Overview

This module provides HTML-formatted safety warnings that stand out visually in Telegram messages. Safety nodes in troubleshooting trees are automatically formatted as blockquotes with warning emojis.

## Features

- ✅ Automatic safety node detection (by type, emoji, or keywords)
- ✅ HTML blockquote formatting with warning emojis
- ✅ Multi-line warning support
- ✅ Expandable blockquote option for long warnings
- ✅ HTML escaping for security
- ✅ Telegram HTML parse mode compatible
- ✅ Works in both text and caption contexts

## Quick Start

```python
from rivet_pro.troubleshooting.formatting import format_node_text

# Regular node - returns plain text
node = {"label": "Check motor", "type": "action"}
text = format_node_text(node)
# Returns: "Check motor"

# Safety node - returns formatted blockquote
safety_node = {"label": "HIGH VOLTAGE - Do not touch", "type": "safety"}
text = format_node_text(safety_node)
# Returns: '<blockquote>⚠️ <b>WARNING</b>\n\nHIGH VOLTAGE - Do not touch</blockquote>'
```

## Usage

### Basic Safety Warning

```python
from rivet_pro.troubleshooting.formatting import format_safety_warning

warning = format_safety_warning("Lockout/tagout required before maintenance")
# Returns formatted blockquote
```

### Tree Node Formatting

```python
from rivet_pro.troubleshooting.formatting import format_node_text

nodes = [
    {"label": "Motor won't start", "type": "problem"},
    {"label": "⚠️ LOCKOUT/TAGOUT REQUIRED", "type": "safety"},
    {"label": "Check power supply", "type": "diagnostic"},
]

formatted_nodes = [format_node_text(node) for node in nodes]
# Safety nodes automatically formatted as blockquotes
```

### Photo Captions with Warnings

```python
from rivet_pro.troubleshooting.formatting import SafetyFormatter

caption = "Motor nameplate photo"
warnings = [
    "HIGH VOLTAGE",
    "Lockout/tagout required"
]

formatted_caption = SafetyFormatter.format_caption_with_safety(
    caption,
    warnings,
    expandable=True
)
# Caption with embedded safety warnings
```

### Expandable Warnings

For long safety procedures:

```python
long_warning = """
Step 1: Verify power is OFF
Step 2: Apply lockout device
Step 3: Test for voltage
Step 4: Ground conductors
"""

formatted = format_safety_warning(long_warning, expandable=True)
# Uses <blockquote expandable> for collapsible display
```

## Safety Node Detection

Nodes are identified as safety warnings if they have:

1. **Explicit type**: `type` in `["safety", "warning", "danger", "caution"]`
2. **Warning emoji**: Contains `⚠️`, `🚨`, or `⚡`
3. **Warning keywords**: "warning", "danger", "hazard", "voltage", "electrical", etc.

```python
from rivet_pro.troubleshooting.formatting import is_safety_node

is_safety_node({"label": "Check filter", "type": "action"})
# Returns: False

is_safety_node({"label": "HIGH VOLTAGE", "type": "safety"})
# Returns: True

is_safety_node({"label": "⚠️ Wear PPE"})
# Returns: True (detected by emoji)

is_safety_node({"label": "Check for electrical hazards"})
# Returns: True (detected by keyword)
```

## Safety Emoji Levels

The formatter selects appropriate emojis based on danger level:

| Level | Emoji | Triggers |
|-------|-------|----------|
| Danger (High) | 🚨 | `type="danger"`, "voltage", "electrical" |
| Caution | ⚡ | `type="caution"`, "moving", "sharp" |
| Warning (Default) | ⚠️ | All other safety nodes |

```python
from rivet_pro.troubleshooting.formatting import SafetyFormatter

# Danger level
node = {"label": "HIGH VOLTAGE", "type": "danger"}
emoji = SafetyFormatter.get_safety_emoji(node)
# Returns: "🚨"

# Caution level
node = {"label": "Moving parts present", "type": "caution"}
emoji = SafetyFormatter.get_safety_emoji(node)
# Returns: "⚡"

# Default warning
node = {"label": "Wear PPE", "type": "safety"}
emoji = SafetyFormatter.get_safety_emoji(node)
# Returns: "⚠️"
```

## HTML Escaping

All user content is automatically HTML-escaped to prevent injection attacks:

```python
from rivet_pro.troubleshooting.formatting import format_node_text

node = {"label": "<script>alert('xss')</script>", "type": "action"}
formatted = format_node_text(node)
# Returns: "&lt;script&gt;alert('xss')&lt;/script&gt;"
```

To disable escaping (for pre-sanitized HTML):

```python
formatted = format_node_text(node, escape=False)
```

## Telegram Integration

### Sending Formatted Messages

```python
from telegram import Bot
from rivet_pro.troubleshooting.formatting import format_node_text

bot = Bot(token="YOUR_TOKEN")

node = {"label": "⚠️ HIGH VOLTAGE", "type": "safety"}
formatted = format_node_text(node)

await bot.send_message(
    chat_id=user_id,
    text=formatted,
    parse_mode="HTML"  # Required for blockquote formatting
)
```

### Photo Captions

```python
from rivet_pro.troubleshooting.formatting import SafetyFormatter

caption = "Equipment inspection photo"
warnings = ["Lockout/tagout required", "Moving parts present"]

formatted_caption = SafetyFormatter.format_caption_with_safety(
    caption,
    warnings,
    expandable=True  # Recommended for photo captions
)

await bot.send_photo(
    chat_id=user_id,
    photo=photo_file,
    caption=formatted_caption,
    parse_mode="HTML"
)
```

## API Reference

### Functions

#### `format_node_text(node, escape=True, expandable=False)`
Format a tree node's text with appropriate safety styling.

**Parameters:**
- `node` (dict): Tree node with `label` and optional `type`
- `escape` (bool): Apply HTML escaping (default: True)
- `expandable` (bool): Use expandable blockquote for safety warnings

**Returns:** Formatted text string

---

#### `format_safety_warning(text, node=None, expandable=False)`
Format text as a safety warning blockquote.

**Parameters:**
- `text` (str): Warning text to format
- `node` (dict, optional): Node context for emoji selection
- `expandable` (bool): Use expandable blockquote

**Returns:** HTML-formatted safety warning

---

#### `is_safety_node(node)`
Check if a node represents a safety warning.

**Parameters:**
- `node` (dict): Tree node dictionary

**Returns:** True if node is a safety warning

---

### Class: SafetyFormatter

#### `SafetyFormatter.format_caption_with_safety(caption, safety_warnings, expandable=True)`
Format a photo/video caption with embedded safety warnings.

**Parameters:**
- `caption` (str): Main caption text
- `safety_warnings` (list[str]): List of safety warning texts
- `expandable` (bool): Use expandable blockquotes (default: True)

**Returns:** HTML-formatted caption with warnings

## Examples

### Troubleshooting Tree Integration

```python
from rivet_pro.troubleshooting.formatting import format_node_text

def render_troubleshooting_step(node):
    """Render a single troubleshooting step with safety formatting."""
    formatted_text = format_node_text(node)

    if is_safety_node(node):
        # Safety nodes already formatted as blockquotes
        return formatted_text
    else:
        # Add regular formatting
        return f"• {formatted_text}"

# Example tree
tree = [
    {"label": "Motor overheating", "type": "problem"},
    {"label": "⚠️ Allow motor to cool before touching", "type": "safety"},
    {"label": "Check for blocked ventilation", "type": "diagnostic"},
    {"label": "🚨 HIGH VOLTAGE - Use insulated tools", "type": "danger"},
    {"label": "Clean air intake", "type": "solution"},
]

rendered = "\n\n".join(render_troubleshooting_step(node) for node in tree)
```

### Multi-Step Safety Procedure

```python
safety_procedure = """
LOCKOUT/TAGOUT PROCEDURE:

1. Notify all affected personnel
2. Shut down equipment using normal procedures
3. Isolate energy sources (electrical, pneumatic, hydraulic)
4. Apply lockout devices
5. Release stored energy
6. Verify zero energy state with test equipment
"""

formatted = format_safety_warning(
    safety_procedure,
    node={"type": "danger"},
    expandable=True
)

# Send as Telegram message
await bot.send_message(
    chat_id=user_id,
    text=formatted,
    parse_mode="HTML"
)
```

### Conditional Safety Warnings

```python
def get_equipment_warnings(equipment_type: str) -> list[str]:
    """Get safety warnings based on equipment type."""
    warnings = {
        "motor": [
            "HIGH VOLTAGE - Lockout/tagout required",
            "Moving parts - Keep hands clear",
            "Hot surfaces - Allow cooling before maintenance"
        ],
        "pump": [
            "Pressurized system - Release pressure before opening",
            "Hot fluids - Wear protective equipment",
            "Rotating components - Ensure complete stop"
        ],
        "conveyor": [
            "Pinch points - Use lockout during maintenance",
            "Moving parts - Emergency stop accessible",
            "Trip hazards - Clear work area"
        ]
    }
    return warnings.get(equipment_type, [])

# Format equipment-specific warnings
equipment = "motor"
warnings = get_equipment_warnings(equipment)

for warning in warnings:
    formatted = format_safety_warning(warning)
    await bot.send_message(chat_id=user_id, text=formatted, parse_mode="HTML")
```

## Testing

Run the comprehensive test suite:

```bash
pytest rivet_pro/troubleshooting/test_formatting.py -v
```

Tests cover:
- Safety node detection (by type, emoji, keywords)
- HTML escaping and injection prevention
- Blockquote formatting (standard and expandable)
- Multi-line warnings
- Caption integration
- Telegram HTML compatibility
- Edge cases (Unicode, long text, special characters)

## Best Practices

1. **Always use HTML parse mode** when sending formatted warnings via Telegram
2. **Use expandable blockquotes** for photo captions to save space
3. **Test with actual equipment** to ensure warnings are appropriate
4. **Keep warnings concise** but comprehensive
5. **Layer warnings** by severity (danger first, cautions after)
6. **Include actionable steps** in safety warnings when possible
7. **Escape user input** to prevent HTML injection (enabled by default)

## Security Considerations

- All user input is HTML-escaped by default
- Safe for displaying user-generated content
- Prevents XSS via malicious node labels
- Compatible with Telegram's strict HTML parser

## Telegram HTML Limitations

Telegram supports a limited set of HTML tags:
- `<b>`, `<strong>` - Bold
- `<i>`, `<em>` - Italic
- `<u>`, `<ins>` - Underline
- `<s>`, `<strike>`, `<del>` - Strikethrough
- `<code>` - Inline code
- `<pre>` - Code block
- `<a href="">` - Links
- `<blockquote>` - Blockquote (used for safety warnings)
- `<blockquote expandable>` - Collapsible blockquote

This formatter only uses `<blockquote>` and `<b>` to ensure compatibility.

## Related Modules

- `rivet_pro.adapters.telegram.bot` - Bot handlers using this formatter
- `rivet_pro.troubleshooting.tree` - Tree structure that nodes come from
- `rivet_pro.atlas.equipment` - Equipment data with safety warnings

## Support

For issues or questions:
1. Check test cases in `test_formatting.py` for usage examples
2. Review this documentation
3. Consult Telegram Bot API docs for HTML parse mode details

---

**Author**: Atlas Engineer
**Task**: TASK-9.6
**Version**: 1.0.0
**Last Updated**: 2026-01-15
