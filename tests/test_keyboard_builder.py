"""
Unit tests for Telegram Inline Keyboard Builder.

Tests keyboard creation, layout strategies, and Telegram limits enforcement.
"""

import pytest
from unittest.mock import Mock, patch

from rivet_pro.troubleshooting.keyboard import (
    build_navigation_keyboard,
    build_confirmation_keyboard,
    build_paginated_keyboard,
    KeyboardLayoutStrategy,
    _calculate_optimal_layout,
    _chunk_buttons,
    MAX_BUTTONS_PER_ROW,
    MAX_TOTAL_BUTTONS
)


class TestOptimalLayoutCalculation:
    """Test the optimal layout calculation logic."""

    def test_1_to_2_buttons_single_column(self):
        """1-2 buttons should be arranged in single column."""
        assert _calculate_optimal_layout(1) == 1
        assert _calculate_optimal_layout(2) == 1

    def test_3_to_4_buttons_double_column(self):
        """3-4 buttons should be arranged in 2 columns."""
        assert _calculate_optimal_layout(3) == 2
        assert _calculate_optimal_layout(4) == 2

    def test_5_to_9_buttons_triple_column(self):
        """5-9 buttons should be arranged in 3 columns."""
        assert _calculate_optimal_layout(5) == 3
        assert _calculate_optimal_layout(6) == 3
        assert _calculate_optimal_layout(9) == 3

    def test_10_plus_buttons_quad_column(self):
        """10+ buttons should be arranged in 4 columns."""
        assert _calculate_optimal_layout(10) == 4
        assert _calculate_optimal_layout(20) == 4
        assert _calculate_optimal_layout(50) == 4


class TestButtonChunking:
    """Test button chunking into rows."""

    def test_chunk_respects_telegram_limit(self):
        """Chunking should enforce max 8 buttons per row."""
        from telegram import InlineKeyboardButton

        # Create 20 dummy buttons
        buttons = [
            InlineKeyboardButton(f"Button {i}", callback_data=f"cb_{i}")
            for i in range(20)
        ]

        # Try to chunk with 10 per row (should be capped at 8)
        rows = _chunk_buttons(buttons, buttons_per_row=10)

        # Verify no row exceeds 8 buttons
        for row in rows:
            assert len(row) <= MAX_BUTTONS_PER_ROW

        # Should have 3 rows: 8, 8, 4
        assert len(rows) == 3
        assert len(rows[0]) == 8
        assert len(rows[1]) == 8
        assert len(rows[2]) == 4

    def test_chunk_evenly_distributed(self):
        """Buttons should be evenly distributed across rows."""
        from telegram import InlineKeyboardButton

        buttons = [
            InlineKeyboardButton(f"Btn {i}", callback_data=f"cb_{i}")
            for i in range(9)
        ]

        rows = _chunk_buttons(buttons, buttons_per_row=3)

        assert len(rows) == 3
        assert all(len(row) == 3 for row in rows)


class TestNavigationKeyboard:
    """Test build_navigation_keyboard function."""

    def test_empty_edges_returns_no_options_keyboard(self):
        """Empty edges should return 'No options' keyboard."""
        keyboard = build_navigation_keyboard(current_node="A", edges=[])

        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 1
        assert "No options" in keyboard.inline_keyboard[0][0].text

    def test_simple_two_button_keyboard(self):
        """Basic two-button keyboard (Yes/No)."""
        edges = [
            {"to": "C", "label": "Yes"},
            {"to": "D", "label": "No"}
        ]

        keyboard = build_navigation_keyboard(current_node="B", edges=edges, tree_id=1)

        # Should have 2 buttons in separate rows (AUTO layout with 2 buttons)
        assert len(keyboard.inline_keyboard) == 2
        assert keyboard.inline_keyboard[0][0].text == "Yes"
        assert keyboard.inline_keyboard[1][0].text == "No"

    def test_auto_layout_with_three_buttons(self):
        """AUTO layout with 3 buttons should use 2 per row."""
        edges = [
            {"to": "motor", "label": "Check motor"},
            {"to": "bearing", "label": "Check bearing"},
            {"to": "electrical", "label": "Check electrical"}
        ]

        keyboard = build_navigation_keyboard(
            current_node="root",
            edges=edges,
            layout=KeyboardLayoutStrategy.AUTO
        )

        # 3 buttons with AUTO should be 2 per row: [2, 1]
        assert len(keyboard.inline_keyboard) == 2
        assert len(keyboard.inline_keyboard[0]) == 2  # First row: 2 buttons
        assert len(keyboard.inline_keyboard[1]) == 1  # Second row: 1 button

    def test_single_column_layout(self):
        """SINGLE_COLUMN layout should have 1 button per row."""
        edges = [
            {"to": "opt1", "label": "Option 1"},
            {"to": "opt2", "label": "Option 2"},
            {"to": "opt3", "label": "Option 3"}
        ]

        keyboard = build_navigation_keyboard(
            current_node="menu",
            edges=edges,
            layout=KeyboardLayoutStrategy.SINGLE_COLUMN
        )

        assert len(keyboard.inline_keyboard) == 3
        assert all(len(row) == 1 for row in keyboard.inline_keyboard)

    def test_double_column_layout(self):
        """DOUBLE_COLUMN layout should have 2 buttons per row."""
        edges = [
            {"to": f"opt{i}", "label": f"Option {i}"}
            for i in range(1, 6)
        ]

        keyboard = build_navigation_keyboard(
            current_node="menu",
            edges=edges,
            layout=KeyboardLayoutStrategy.DOUBLE_COLUMN
        )

        # 5 buttons: [2, 2, 1]
        assert len(keyboard.inline_keyboard) == 3
        assert len(keyboard.inline_keyboard[0]) == 2
        assert len(keyboard.inline_keyboard[1]) == 2
        assert len(keyboard.inline_keyboard[2]) == 1

    def test_back_button_appended(self):
        """Back button should be added when requested."""
        edges = [
            {"to": "C", "label": "Option C"}
        ]

        keyboard = build_navigation_keyboard(
            current_node="B",
            edges=edges,
            include_back_button=True,
            parent_node="A"
        )

        # Should have 2 buttons total (1 edge + back)
        buttons_count = sum(len(row) for row in keyboard.inline_keyboard)
        assert buttons_count == 2

        # Find back button
        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        back_button = next(btn for btn in all_buttons if "Back" in btn.text)
        assert back_button is not None

    def test_fallback_to_node_id_if_no_label(self):
        """Should use node ID as label if label is missing."""
        edges = [
            {"to": "node_xyz"}  # No label provided
        ]

        keyboard = build_navigation_keyboard(current_node="A", edges=edges, tree_id=1)

        button = keyboard.inline_keyboard[0][0]
        assert button.text == "node_xyz"

    def test_too_many_buttons_raises_error(self):
        """Should raise ValueError if exceeding 100 button limit."""
        edges = [
            {"to": f"node{i}", "label": f"Button {i}"}
            for i in range(MAX_TOTAL_BUTTONS + 1)
        ]

        with pytest.raises(ValueError, match="Telegram limit"):
            build_navigation_keyboard(current_node="root", edges=edges, tree_id=1)

    def test_callback_data_includes_navigation_info(self):
        """Callback data should contain action and node information."""
        edges = [{"to": "target_node", "label": "Go"}]

        keyboard = build_navigation_keyboard(current_node="source", edges=edges, tree_id=1)

        button = keyboard.inline_keyboard[0][0]
        callback_data = button.callback_data

        # Should contain encoded navigation data
        assert "nav" in callback_data or "target_node" in callback_data


class TestConfirmationKeyboard:
    """Test build_confirmation_keyboard function."""

    def test_default_confirm_cancel_keyboard(self):
        """Should create keyboard with confirm and cancel buttons."""
        keyboard = build_confirmation_keyboard(
            confirm_callback="confirm_action",
            cancel_callback="cancel_action"
        )

        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 2

        confirm_btn, cancel_btn = keyboard.inline_keyboard[0]
        assert "Confirm" in confirm_btn.text
        assert "Cancel" in cancel_btn.text
        assert confirm_btn.callback_data == "confirm_action"
        assert cancel_btn.callback_data == "cancel_action"

    def test_custom_button_text(self):
        """Should accept custom button text."""
        keyboard = build_confirmation_keyboard(
            confirm_callback="yes",
            cancel_callback="no",
            confirm_text="👍 Yes",
            cancel_text="👎 No"
        )

        confirm_btn, cancel_btn = keyboard.inline_keyboard[0]
        assert confirm_btn.text == "👍 Yes"
        assert cancel_btn.text == "👎 No"


class TestPaginatedKeyboard:
    """Test build_paginated_keyboard function."""

    def test_single_page_no_pagination_controls(self):
        """Single page should not have pagination buttons."""
        items = [
            {"id": "item1", "label": "Item 1"},
            {"id": "item2", "label": "Item 2"}
        ]

        keyboard = build_paginated_keyboard(
            items=items,
            page=0,
            items_per_page=5,
            callback_prefix="select"
        )

        # Should have items but no pagination row
        total_buttons = sum(len(row) for row in keyboard.inline_keyboard)
        assert total_buttons == 2  # Just the 2 items

    def test_multiple_pages_with_pagination_controls(self):
        """Multiple pages should include pagination buttons."""
        items = [
            {"id": f"item{i}", "label": f"Item {i}"}
            for i in range(15)
        ]

        keyboard = build_paginated_keyboard(
            items=items,
            page=0,
            items_per_page=5,
            callback_prefix="select"
        )

        # Should have 5 items + pagination row
        assert len(keyboard.inline_keyboard) >= 2

        # Last row should be pagination
        pagination_row = keyboard.inline_keyboard[-1]
        pagination_text = " ".join(btn.text for btn in pagination_row)

        assert "Next" in pagination_text or "Prev" in pagination_text or "📄" in pagination_text

    def test_page_zero_no_prev_button(self):
        """First page should not have Previous button."""
        items = [{"id": f"i{i}", "label": f"Item {i}"} for i in range(20)]

        keyboard = build_paginated_keyboard(
            items=items, page=0, items_per_page=5, callback_prefix="sel"
        )

        pagination_row = keyboard.inline_keyboard[-1]
        pagination_text = " ".join(btn.text for btn in pagination_row)

        assert "Prev" not in pagination_text
        assert "Next" in pagination_text

    def test_last_page_no_next_button(self):
        """Last page should not have Next button."""
        items = [{"id": f"i{i}", "label": f"Item {i}"} for i in range(15)]

        # Page 2 (0-indexed) is the last page with 5 items per page
        keyboard = build_paginated_keyboard(
            items=items, page=2, items_per_page=5, callback_prefix="sel"
        )

        pagination_row = keyboard.inline_keyboard[-1]
        pagination_text = " ".join(btn.text for btn in pagination_row)

        assert "Next" not in pagination_text
        assert "Prev" in pagination_text

    def test_middle_page_has_both_buttons(self):
        """Middle page should have both Previous and Next."""
        items = [{"id": f"i{i}", "label": f"Item {i}"} for i in range(20)]

        keyboard = build_paginated_keyboard(
            items=items, page=1, items_per_page=5, callback_prefix="sel"
        )

        pagination_row = keyboard.inline_keyboard[-1]
        pagination_text = " ".join(btn.text for btn in pagination_row)

        assert "Prev" in pagination_text
        assert "Next" in pagination_text


class TestTelegramLimitsEnforcement:
    """Test that Telegram limits are strictly enforced."""

    def test_max_8_buttons_per_row_enforced(self):
        """No row should ever exceed 8 buttons."""
        # Try to create keyboard with 12 buttons in quad layout
        edges = [
            {"to": f"node{i}", "label": f"Btn {i}"}
            for i in range(12)
        ]

        keyboard = build_navigation_keyboard(
            current_node="root",
            edges=edges,
            layout=KeyboardLayoutStrategy.QUAD_COLUMN
        )

        for row in keyboard.inline_keyboard:
            assert len(row) <= MAX_BUTTONS_PER_ROW

    def test_max_100_buttons_total_enforced(self):
        """Should raise error if total buttons exceed 100."""
        edges = [{"to": f"n{i}", "label": f"B{i}"} for i in range(101)]

        with pytest.raises(ValueError):
            build_navigation_keyboard(current_node="root", edges=edges, tree_id=1)

    def test_callback_data_truncation_on_overflow(self):
        """Long callback data should be truncated to fit 64 bytes."""
        # Create edge with very long node IDs and labels
        edges = [
            {
                "to": "x" * 100,  # Very long node ID
                "label": "y" * 100  # Very long label
            }
        ]

        keyboard = build_navigation_keyboard(current_node="z" * 100, edges=edges, tree_id=1)

        button = keyboard.inline_keyboard[0][0]
        callback_bytes = len(button.callback_data.encode('utf-8'))

        # Should be within Telegram's 64-byte limit
        assert callback_bytes <= 64


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
