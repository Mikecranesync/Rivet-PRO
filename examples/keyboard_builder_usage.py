"""
Telegram Inline Keyboard Builder Usage Examples

Demonstrates how to build interactive keyboards for RIVET Pro troubleshooting flows.
"""

from rivet_pro.troubleshooting.keyboard import (
    build_navigation_keyboard,
    build_confirmation_keyboard,
    build_paginated_keyboard,
    KeyboardLayoutStrategy
)


def example_simple_yes_no():
    """Basic Yes/No decision keyboard."""
    print("=== Example 1: Simple Yes/No Keyboard ===\n")

    edges = [
        {"to": "check_voltage", "label": "✅ Yes, it powers on"},
        {"to": "check_power_supply", "label": "❌ No, it's dead"}
    ]

    keyboard = build_navigation_keyboard(
        current_node="does_it_power_on",
        edges=edges,
        tree_id=1
    )

    print(f"Buttons: {len(keyboard.inline_keyboard)} rows")
    for i, row in enumerate(keyboard.inline_keyboard):
        print(f"  Row {i + 1}: {[btn.text for btn in row]}")
    print()


def example_multiple_options():
    """Multiple troubleshooting options."""
    print("=== Example 2: Multiple Options (AUTO Layout) ===\n")

    edges = [
        {"to": "motor_overheating", "label": "🔥 Motor is hot"},
        {"to": "unusual_noise", "label": "🔊 Strange noise"},
        {"to": "vibration", "label": "📳 Excessive vibration"},
        {"to": "low_speed", "label": "🐌 Running slow"},
        {"to": "no_start", "label": "❌ Won't start"}
    ]

    keyboard = build_navigation_keyboard(
        current_node="what_is_the_issue",
        edges=edges,
        tree_id=1,
        layout=KeyboardLayoutStrategy.AUTO  # Intelligently arranges buttons
    )

    print(f"Buttons arranged in {len(keyboard.inline_keyboard)} rows:")
    for i, row in enumerate(keyboard.inline_keyboard):
        print(f"  Row {i + 1}: {[btn.text for btn in row]}")
    print()


def example_with_back_button():
    """Navigation with back button."""
    print("=== Example 3: Navigation with Back Button ===\n")

    edges = [
        {"to": "check_thermal_sensor", "label": "Check temperature sensor"},
        {"to": "verify_cooling_fan", "label": "Verify cooling fan"}
    ]

    keyboard = build_navigation_keyboard(
        current_node="motor_overheating",
        edges=edges,
        tree_id=1,
        include_back_button=True,
        parent_node="what_is_the_issue"
    )

    print(f"Total buttons: {sum(len(row) for row in keyboard.inline_keyboard)}")
    for i, row in enumerate(keyboard.inline_keyboard):
        print(f"  Row {i + 1}: {[btn.text for btn in row]}")
    print()


def example_layout_strategies():
    """Different layout strategies."""
    print("=== Example 4: Layout Strategies ===\n")

    edges = [
        {"to": f"option_{i}", "label": f"Option {i}"}
        for i in range(1, 7)
    ]

    layouts = [
        (KeyboardLayoutStrategy.SINGLE_COLUMN, "Single Column"),
        (KeyboardLayoutStrategy.DOUBLE_COLUMN, "Double Column"),
        (KeyboardLayoutStrategy.TRIPLE_COLUMN, "Triple Column"),
        (KeyboardLayoutStrategy.QUAD_COLUMN, "Quad Column"),
    ]

    for strategy, name in layouts:
        keyboard = build_navigation_keyboard(
            current_node="menu",
            edges=edges,
            tree_id=1,
            layout=strategy
        )
        print(f"{name}: {len(keyboard.inline_keyboard)} rows")
        for i, row in enumerate(keyboard.inline_keyboard):
            print(f"  Row {i + 1}: {len(row)} buttons")
        print()


def example_confirmation():
    """Confirmation dialogs."""
    print("=== Example 5: Confirmation Keyboard ===\n")

    keyboard = build_confirmation_keyboard(
        confirm_callback="confirm:shutdown:motor_123",
        cancel_callback="cancel:shutdown",
        confirm_text="🛑 Yes, shut it down",
        cancel_text="↩️ Cancel"
    )

    print("Confirmation buttons:")
    for btn in keyboard.inline_keyboard[0]:
        print(f"  - {btn.text} → {btn.callback_data}")
    print()


def example_paginated_list():
    """Paginated equipment list."""
    print("=== Example 6: Paginated List ===\n")

    # Simulate 15 equipment items
    items = [
        {"id": f"pump_{i}", "label": f"Pump {i} - Building {chr(65 + i % 5)}"}
        for i in range(1, 16)
    ]

    # Page 0 (first page)
    keyboard = build_paginated_keyboard(
        items=items,
        page=0,
        items_per_page=5,
        callback_prefix="select_equipment",
        tree_id=1
    )

    print(f"Page 1: {len(keyboard.inline_keyboard)} rows total")
    print("Equipment items:")
    for row in keyboard.inline_keyboard[:-1]:  # All but pagination row
        for btn in row:
            print(f"  - {btn.text}")

    print("Pagination controls:")
    pagination_row = keyboard.inline_keyboard[-1]
    print(f"  {[btn.text for btn in pagination_row]}")
    print()


def example_with_emojis():
    """Using emojis for visual clarity."""
    print("=== Example 7: Emojis for Visual Hierarchy ===\n")

    edges = [
        {"to": "critical_failure", "label": "🚨 CRITICAL: Immediate shutdown required"},
        {"to": "investigate_warning", "label": "⚠️ WARNING: Investigate soon"},
        {"to": "routine_check", "label": "ℹ️ INFO: Routine check recommended"},
        {"to": "all_clear", "label": "✅ All systems normal"}
    ]

    keyboard = build_navigation_keyboard(
        current_node="system_status",
        edges=edges,
        tree_id=1,
        layout=KeyboardLayoutStrategy.SINGLE_COLUMN  # Stack vertically for hierarchy
    )

    print("Status options (single column for clarity):")
    for row in keyboard.inline_keyboard:
        print(f"  {row[0].text}")
    print()


def example_telegram_limits():
    """Demonstrating Telegram limits enforcement."""
    print("=== Example 8: Telegram Limits Enforcement ===\n")

    # Create many options
    edges = [
        {"to": f"sensor_{i}", "label": f"Sensor {i}"}
        for i in range(1, 21)
    ]

    keyboard = build_navigation_keyboard(
        current_node="select_sensor",
        edges=edges,
        tree_id=1,
        layout=KeyboardLayoutStrategy.QUAD_COLUMN
    )

    print(f"20 buttons arranged in {len(keyboard.inline_keyboard)} rows")
    print(f"Max buttons per row: {max(len(row) for row in keyboard.inline_keyboard)}")
    print(f"All rows respect 8-button limit: {all(len(row) <= 8 for row in keyboard.inline_keyboard)}")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("TELEGRAM INLINE KEYBOARD BUILDER - USAGE EXAMPLES")
    print("=" * 60)
    print()

    example_simple_yes_no()
    example_multiple_options()
    example_with_back_button()
    example_layout_strategies()
    example_confirmation()
    example_paginated_list()
    example_with_emojis()
    example_telegram_limits()

    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
