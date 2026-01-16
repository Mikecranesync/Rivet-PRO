# -*- coding: utf-8 -*-
"""
Windows Console Encoding Fix

Windows uses cp1252 by default which can't display emojis.
Import this module early in any script that prints Unicode.

Usage:
    from rivet_pro.core.utils.encoding import fix_windows_encoding
    fix_windows_encoding()

Or just import at top of script:
    import rivet_pro.core.utils.encoding  # Auto-fixes on import
"""

import sys
import io


def fix_windows_encoding():
    """
    Fix Windows console encoding to support Unicode/emoji output.

    Safe to call multiple times - only applies fix once.
    No-op on non-Windows platforms.
    """
    if sys.platform != 'win32':
        return

    # Check if already wrapped
    if hasattr(sys.stdout, '_wrapped_for_unicode'):
        return

    try:
        # Wrap stdout/stderr with UTF-8 encoding
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer,
            encoding='utf-8',
            errors='replace',
            line_buffering=True
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer,
            encoding='utf-8',
            errors='replace',
            line_buffering=True
        )

        # Mark as wrapped to avoid double-wrapping
        sys.stdout._wrapped_for_unicode = True
        sys.stderr._wrapped_for_unicode = True

    except Exception:
        # If wrapping fails, silently continue with default encoding
        pass


# Auto-fix on import
fix_windows_encoding()
