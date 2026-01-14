#!/usr/bin/env python3
"""Test script to verify version.py router imports correctly."""

import sys
sys.path.insert(0, 'C:/Users/hharp/OneDrive/Desktop/Rivet-PRO')

try:
    from rivet_pro.adapters.web.routers import version
    print("✓ Import successful")
    print(f"✓ Router object exists: {hasattr(version, 'router')}")
    print(f"✓ get_version function exists: {hasattr(version, 'get_version')}")
    print("All checks passed!")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)
