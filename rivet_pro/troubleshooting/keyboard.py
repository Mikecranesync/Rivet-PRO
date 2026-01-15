"""
Telegram Inline Keyboard Builder for RIVET Pro Troubleshooting.

Creates InlineKeyboardMarkup objects from parsed Mermaid tree nodes,
respecting Telegram's limits:
- Max 8 buttons per row
- Max 100 buttons total
- Callback data max 64 bytes

Example:
    >>> from rivet_pro.troubleshooting.keyboard import build_navigation_keyboard
    >>> edges = [
    ...     {"to": "C", "label": "Check voltage"},
    ...     {"to": "D", "label": "Check connections"}
    ... ]
    >>> keyboard = build_navigation_keyboard("B", edges)
    >>> # Returns InlineKeyboardMarkup with 2 buttons
"""

from typing import List, Dict, Optional, Any
from enum import Enum
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .callback import encode_callback


class KeyboardLayoutStrategy(Enum):
    """Layout strategies for arranging buttons in rows."""

    AUTO = "auto"  # Intelligently choose based on button count
    SINGLE_COLUMN = "single_column"  # One button per row
    DOUBLE_COLUMN = "double_column"  # Two buttons per row
    TRIPLE_COLUMN = "triple_column"  # Three buttons per row
    QUAD_COLUMN = "quad_column"  # Four buttons per row
    GRID = "grid"  # Balance buttons across rows


# Telegram limits
MAX_BUTTONS_PER_ROW = 8
MAX_TOTAL_BUTTONS = 100
MAX_CALLBACK_DATA_BYTES = 64


def _calculate_optimal_layout(button_count: int) -> int:
    """
    Calculate optimal buttons per row based on total button count.

    Args:
        button_count: Total number of buttons

    Returns:
        Optimal number of buttons per row

    Logic:
        1-2 buttons: 1 per row (vertical stack)
        3-4 buttons: 2 per row
        5-9 buttons: 3 per row
        10-16 buttons: 4 per row
        17+ buttons: 4 per row (with potential overflow to new rows)
    """
    if button_count <= 2:
        return 1
    elif button_count <= 4:
        return 2
    elif button_count <= 9:
        return 3
    else:
        return 4


def _chunk_buttons(
    buttons: List[InlineKeyboardButton],
    buttons_per_row: int
) -> List[List[InlineKeyboardButton]]:
    """
    Split buttons into rows, respecting max buttons per row limit.

    Args:
        buttons: List of InlineKeyboardButton objects
        buttons_per_row: Desired number of buttons per row

    Returns:
        List of button rows
    """
    # Enforce Telegram limit
    buttons_per_row = min(buttons_per_row, MAX_BUTTONS_PER_ROW)

    rows = []
    for i in range(0, len(buttons), buttons_per_row):
        row = buttons[i:i + buttons_per_row]
        rows.append(row)

    return rows


def build_navigation_keyboard(
    current_node: str,
    edges: List[Dict[str, Any]],
    tree_id: int = 1,
    layout: KeyboardLayoutStrategy = KeyboardLayoutStrategy.AUTO,
    include_back_button: bool = False,
    parent_node: Optional[str] = None
) -> InlineKeyboardMarkup:
    """
    Build Telegram InlineKeyboardMarkup from troubleshooting tree edges.

    Args:
        current_node: Current node ID in the tree
        edges: List of edge dictionaries with "to" and "label" keys
            Example: [{"to": "C", "label": "Yes"}, {"to": "D", "label": "No"}]
        tree_id: Troubleshooting tree identifier (default: 1)
        layout: Button arrangement strategy (default: AUTO)
        include_back_button: Whether to add a back navigation button
        parent_node: Parent node ID for back navigation

    Returns:
        InlineKeyboardMarkup ready for Telegram bot

    Raises:
        ValueError: If edges exceed Telegram's 100 button limit

    Example:
        >>> edges = [
        ...     {"to": "motor_check", "label": "✅ Check motor"},
        ...     {"to": "bearing_check", "label": "🔧 Check bearings"},
        ...     {"to": "electrical", "label": "⚡ Check electrical"}
        ... ]
        >>> keyboard = build_navigation_keyboard("root", edges, tree_id=1)
    """
    # Validate button count
    button_count = len(edges)
    if include_back_button:
        button_count += 1

    if button_count == 0:
        # Empty state: Return keyboard with just a "No options" message
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ No options available", callback_data="none")]
        ])

    if button_count > MAX_TOTAL_BUTTONS:
        raise ValueError(
            f"Cannot create keyboard with {button_count} buttons. "
            f"Telegram limit is {MAX_TOTAL_BUTTONS} buttons."
        )

    # Build buttons from edges
    buttons = []
    for edge in edges:
        target_node = edge.get("to")
        label = edge.get("label", target_node)  # Fallback to node ID if no label

        if not target_node:
            continue

        # Encode callback data
        callback_data = encode_callback(
            action="nav",
            node=target_node,
            from_node=current_node
        )

        # Validate callback data size
        if len(callback_data.encode('utf-8')) > MAX_CALLBACK_DATA_BYTES:
            # Truncate label if callback data too long
            label = label[:20] + "..."
            callback_data = encode_callback(
                action="nav",
                node=target_node[:10],  # Truncate node ID too
                from_node=current_node[:10]
            )

        buttons.append(InlineKeyboardButton(label, callback_data=callback_data))

    # Add back button if requested
    if include_back_button and parent_node:
        back_callback = encode_callback(
            action="back",
            node=parent_node,
            from_node=current_node
        )
        buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=back_callback))

    # Determine layout strategy
    if layout == KeyboardLayoutStrategy.AUTO:
        buttons_per_row = _calculate_optimal_layout(len(buttons))
    elif layout == KeyboardLayoutStrategy.SINGLE_COLUMN:
        buttons_per_row = 1
    elif layout == KeyboardLayoutStrategy.DOUBLE_COLUMN:
        buttons_per_row = 2
    elif layout == KeyboardLayoutStrategy.TRIPLE_COLUMN:
        buttons_per_row = 3
    elif layout == KeyboardLayoutStrategy.QUAD_COLUMN:
        buttons_per_row = 4
    elif layout == KeyboardLayoutStrategy.GRID:
        # For grid, calculate square-ish layout
        import math
        buttons_per_row = min(4, math.ceil(math.sqrt(len(buttons))))
    else:
        buttons_per_row = 2  # Safe default

    # Arrange buttons into rows
    button_rows = _chunk_buttons(buttons, buttons_per_row)

    return InlineKeyboardMarkup(button_rows)


def build_confirmation_keyboard(
    confirm_callback: str,
    cancel_callback: str,
    confirm_text: str = "✅ Confirm",
    cancel_text: str = "❌ Cancel"
) -> InlineKeyboardMarkup:
    """
    Build a simple confirmation keyboard with confirm/cancel buttons.

    Args:
        confirm_callback: Callback data for confirm button
        cancel_callback: Callback data for cancel button
        confirm_text: Text for confirm button (default: "✅ Confirm")
        cancel_text: Text for cancel button (default: "❌ Cancel")

    Returns:
        InlineKeyboardMarkup with two buttons in one row

    Example:
        >>> keyboard = build_confirmation_keyboard(
        ...     confirm_callback="confirm:delete:123",
        ...     cancel_callback="cancel:delete"
        ... )
    """
    keyboard = [
        [
            InlineKeyboardButton(confirm_text, callback_data=confirm_callback),
            InlineKeyboardButton(cancel_text, callback_data=cancel_callback)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_paginated_keyboard(
    items: List[Dict[str, str]],
    page: int,
    items_per_page: int,
    callback_prefix: str,
    layout: KeyboardLayoutStrategy = KeyboardLayoutStrategy.AUTO
) -> InlineKeyboardMarkup:
    """
    Build paginated keyboard for long lists.

    Args:
        items: List of items, each with "id" and "label" keys
        page: Current page number (0-indexed)
        items_per_page: Number of items to show per page
        callback_prefix: Prefix for callback data (e.g., "select_equip")
        layout: Button arrangement strategy

    Returns:
        InlineKeyboardMarkup with items and pagination controls

    Example:
        >>> items = [
        ...     {"id": "pump1", "label": "Pump A"},
        ...     {"id": "pump2", "label": "Pump B"},
        ...     # ... more items
        ... ]
        >>> keyboard = build_paginated_keyboard(
        ...     items, page=0, items_per_page=5, callback_prefix="select"
        ... )
    """
    # Calculate pagination
    start = page * items_per_page
    end = start + items_per_page
    page_items = items[start:end]
    total_pages = (len(items) + items_per_page - 1) // items_per_page

    # Build item buttons
    edges = [
        {"to": item["id"], "label": item["label"]}
        for item in page_items
    ]

    # Create main keyboard
    keyboard_markup = build_navigation_keyboard(
        current_node=f"page_{page}",
        edges=edges,
        layout=layout
    )

    # Add pagination controls if multiple pages
    if total_pages > 1:
        pagination_row = []

        # Previous button
        if page > 0:
            prev_callback = encode_callback(
                action="page",
                node=str(page - 1),
                prefix=callback_prefix
            )
            pagination_row.append(
                InlineKeyboardButton("◀️ Prev", callback_data=prev_callback)
            )

        # Page indicator
        pagination_row.append(
            InlineKeyboardButton(
                f"📄 {page + 1}/{total_pages}",
                callback_data="page_info"
            )
        )

        # Next button
        if page < total_pages - 1:
            next_callback = encode_callback(
                action="page",
                node=str(page + 1),
                prefix=callback_prefix
            )
            pagination_row.append(
                InlineKeyboardButton("Next ▶️", callback_data=next_callback)
            )

        # Add pagination row to keyboard
        keyboard_markup.inline_keyboard.append(pagination_row)

    return keyboard_markup
