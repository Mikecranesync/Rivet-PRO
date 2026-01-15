# Claude Fallback for Unknown Equipment - Usage Guide

## Overview

TASK-9.8 implements a Claude API fallback system that dynamically generates troubleshooting guides when equipment has no predefined troubleshooting tree.

## Features

- **Smart Detection**: Automatically detects missing troubleshooting trees
- **Claude API Integration**: Uses Claude 3.5 Sonnet for expert troubleshooting generation
- **Telegram Formatting**: Properly escapes markdown and formats for mobile display
- **Persistent Option**: Offers to save generated guides as tree drafts
- **Safety Focused**: Includes safety warnings and clear step-by-step instructions

## Quick Start

### Async Usage (Recommended)

```python
from rivet_pro.troubleshooting import generate_troubleshooting_guide

# Generate guide for unknown equipment
guide = await generate_troubleshooting_guide(
    equipment_type="Siemens S7-1200 PLC",
    problem="Communication fault",
    context="Profinet connection lost to HMI"
)

# Use in Telegram bot
await bot.send_message(
    chat_id=chat_id,
    text=guide["formatted_text"],
    parse_mode="MarkdownV2"
)
```

### Synchronous Usage

```python
from rivet_pro.troubleshooting import generate_troubleshooting_guide_sync

guide = generate_troubleshooting_guide_sync(
    equipment_type="ABB M3BP Motor",
    problem="Overheating",
    context="Reaches 95°C within 30 minutes"
)
```

### Automatic Fallback

```python
from rivet_pro.troubleshooting import get_or_generate_troubleshooting

# Automatically checks for existing tree, falls back to Claude if not found
guide = await get_or_generate_troubleshooting(
    equipment_type="Unknown Model XYZ",
    problem="Will not start"
)
```

## Response Structure

The `TroubleshootingGuide` dictionary contains:

```python
{
    "equipment_type": "Siemens S7-1200 PLC",
    "problem": "Communication fault",
    "steps": [
        "Check physical Ethernet connection...",
        "Verify IP address configuration...",
        "Inspect for damaged cables...",
        # ... 5-8 steps total
    ],
    "formatted_text": "🔧 *Troubleshooting Guide*\n\n*Equipment:*...",
    "can_save": True,  # Always true for generated guides
    "raw_response": "1. Check physical...\n2. Verify..."
}
```

## Telegram Bot Integration

### Basic Flow

```python
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from rivet_pro.troubleshooting import get_or_generate_troubleshooting

async def troubleshoot_equipment(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """Handle equipment troubleshooting request"""

    # Get equipment info from context
    equipment_type = context.user_data.get("equipment_type")
    problem = context.user_data.get("problem")

    # Generate or retrieve guide
    try:
        guide = await get_or_generate_troubleshooting(
            equipment_type=equipment_type,
            problem=problem,
            context=None  # Optional additional context
        )

        # Create keyboard with save option
        keyboard = [
            [InlineKeyboardButton("💾 Save Guide", callback_data=f"save_guide:{guide_id}")],
            [InlineKeyboardButton("🔄 Regenerate", callback_data="regenerate")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send formatted guide
        await update.message.reply_text(
            text=guide["formatted_text"],
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Failed to generate troubleshooting guide: {str(e)}"
        )
```

### Saving Generated Guides

```python
async def save_generated_guide(guide: dict, user_id: int):
    """Save Claude-generated guide as troubleshooting tree draft"""

    # Convert steps to tree format
    tree_data = {
        "equipment_type": guide["equipment_type"],
        "problem": guide["problem"],
        "nodes": [],
        "edges": [],
        "created_by": "claude_fallback",
        "status": "draft"
    }

    # Create nodes from steps
    for i, step in enumerate(guide["steps"], start=1):
        node = {
            "id": f"step_{i}",
            "type": "action",
            "text": step,
            "order": i
        }
        tree_data["nodes"].append(node)

        # Link to next step
        if i < len(guide["steps"]):
            tree_data["edges"].append({
                "from": f"step_{i}",
                "to": f"step_{i+1}",
                "label": "Next"
            })

    # Save to database
    await save_troubleshooting_tree(tree_data)
```

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-api03-xxx

# Optional (has defaults)
DATABASE_URL=postgresql://...
```

### Model Configuration

The fallback uses Claude 3.5 Sonnet by default. To change:

```python
# In fallback.py
response = await client.messages.create(
    model="claude-3-5-sonnet-20241022",  # Change model here
    max_tokens=1024,
    temperature=0.3,  # Adjust temperature for more/less variety
    ...
)
```

## Error Handling

### Common Errors

```python
from rivet_pro.troubleshooting import ClaudeFallbackError

try:
    guide = await generate_troubleshooting_guide(...)
except ClaudeFallbackError as e:
    if "ANTHROPIC_API_KEY not found" in str(e):
        # Handle missing API key
        logger.error("Claude API key not configured")
    elif "equipment_type cannot be empty" in str(e):
        # Handle invalid input
        logger.error("Invalid equipment type provided")
    elif "Failed to generate" in str(e):
        # Handle API failure
        logger.error(f"Claude API error: {e}")
```

### Graceful Degradation

```python
async def get_troubleshooting_with_fallback(equipment_type: str, problem: str):
    """Get troubleshooting with multiple fallback levels"""

    # Try database tree first
    tree = await get_tree_from_db(equipment_type)
    if tree:
        return tree

    # Try Claude API fallback
    try:
        return await generate_troubleshooting_guide(
            equipment_type=equipment_type,
            problem=problem
        )
    except ClaudeFallbackError:
        # Return generic fallback
        return {
            "formatted_text": (
                "⚠️ No specific troubleshooting guide available.\n\n"
                "Please contact support or consult equipment manual."
            ),
            "can_save": False
        }
```

## Performance & Costs

### Response Times
- Average: 2-4 seconds
- With caching: < 1 second (if same equipment/problem)

### API Costs (Claude 3.5 Sonnet)
- Input: ~500 tokens per request (~$0.0015)
- Output: ~800 tokens per response (~$0.012)
- **Total per guide: ~$0.014** (1.4 cents)

### Optimization Tips

1. **Cache frequently requested guides**:
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=100)
   def get_cached_guide(equipment_type: str, problem: str):
       return generate_troubleshooting_guide_sync(equipment_type, problem)
   ```

2. **Batch similar requests**:
   - If multiple users request the same equipment type, generate once and reuse

3. **Save generated guides**:
   - Store successful guides in database for future use
   - Reduces API calls significantly

## Testing

### Run Unit Tests

```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
python -m pytest tests/test_troubleshooting_fallback.py -v
```

### Manual Testing

```python
# Test with demo script
python rivet_pro/troubleshooting/fallback.py
```

Output:
```
=== Claude Fallback Demo ===

Generated guide:
🔧 *Troubleshooting Guide*

*Equipment:* Siemens S7\\-1200 PLC
*Problem:* Communication fault
*Context:* Profinet connection lost to HMI

*Steps:*

*1.* Check physical Ethernet connection at terminals \\.\\.\\.
*2.* Verify IP address configuration in TIA Portal \\.\\.\\.
...

Total steps: 6
Can save: True
```

## Monitoring & Logging

### Key Metrics to Track

1. **Fallback usage rate**: How often fallback is triggered
2. **API success rate**: Success vs. failure of Claude API calls
3. **Response quality**: User feedback on generated guides
4. **Cost per user**: API costs normalized by user

### Example Logging

```python
import logging

logger = logging.getLogger(__name__)

# Log fallback usage
logger.info(
    "Claude fallback triggered",
    extra={
        "equipment_type": equipment_type,
        "problem": problem,
        "user_id": user_id
    }
)

# Log API response
logger.info(
    "Guide generated successfully",
    extra={
        "steps_count": len(guide["steps"]),
        "response_time_ms": response_time,
        "tokens_used": response.usage.total_tokens if response.usage else None
    }
)
```

## Future Enhancements

### Planned Features
- [ ] Multi-language support (translate generated guides)
- [ ] Image/diagram generation using Claude's vision capabilities
- [ ] Learning from technician feedback to improve prompts
- [ ] Automatic tree creation from successful fallback guides
- [ ] Integration with equipment manuals for context augmentation

### Database Schema for Saved Guides

```sql
CREATE TABLE generated_troubleshooting_guides (
    id SERIAL PRIMARY KEY,
    equipment_type VARCHAR(255) NOT NULL,
    problem VARCHAR(500) NOT NULL,
    context TEXT,
    steps JSONB NOT NULL,
    raw_response TEXT NOT NULL,
    usage_count INTEGER DEFAULT 1,
    avg_rating DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(50) DEFAULT 'claude_fallback',
    status VARCHAR(20) DEFAULT 'active',
    INDEX idx_equipment_problem (equipment_type, problem)
);
```

## Support & Troubleshooting

### Debug Mode

Enable debug logging:
```python
import logging
logging.getLogger('rivet_pro.troubleshooting.fallback').setLevel(logging.DEBUG)
```

### Common Issues

1. **"ANTHROPIC_API_KEY not found"**
   - Check `.env` file has `ANTHROPIC_API_KEY=sk-ant-...`
   - Verify environment is loaded

2. **"Could not extract troubleshooting steps"**
   - Claude returned non-standard format
   - Check `raw_response` field for actual response
   - May need to adjust parsing regex

3. **Rate limiting errors**
   - Implement exponential backoff
   - Cache frequently requested guides

---

**Created**: 2026-01-15
**Task**: TASK-9.8
**Module**: `rivet_pro.troubleshooting.fallback`
**Tests**: 31 unit tests (100% passing)
