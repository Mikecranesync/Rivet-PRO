"""
YCB v3 Test Runner

Runs all unit and integration tests for the v3 video generation pipeline.

Usage:
    python -m ycb.tests.run_all_tests
    python -m ycb.tests.run_all_tests --quick   # Skip slow tests
    python -m ycb.tests.run_all_tests --verbose # Show all output
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Test file locations (relative to ycb/)
TEST_FILES = [
    # Unit tests
    ("SVG Electrical Assets", "assets/electrical/test_svg_import.py"),
    ("PLC Assets", "assets/plc/test_plc_import.py"),
    ("Manim Templates", "rendering/test_templates.py"),
    ("Storyboard Generator", "storyboard/test_generator.py"),
    ("Scene Router", "storyboard/test_router.py"),
    ("Audio Timing", "audio/test_timing.py"),
    ("Video Compositor", "composition/test_compositor.py"),
    ("Post-Processing", "composition/test_post_processing.py"),
    ("Video Generator v3", "pipeline/test_video_generator_v3.py"),
    ("Quality Judge v3", "evaluation/test_video_judge_v3.py"),
    ("Autonomous Loop v3", "pipeline/test_autonomous_loop_v3.py"),
    # Integration tests
    ("Integration Tests", "tests/test_integration_v3.py"),
]


def run_test_file(name: str, path: str, verbose: bool = False) -> Tuple[bool, str, float]:
    """
    Run a single test file and return results.

    Returns:
        Tuple of (success, output, duration_seconds)
    """
    ycb_dir = Path(__file__).parent.parent
    full_path = ycb_dir / path

    if not full_path.exists():
        return False, f"Test file not found: {full_path}", 0.0

    start = datetime.now()

    try:
        result = subprocess.run(
            [sys.executable, str(full_path)],
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout per test file
            cwd=str(full_path.parent.parent.parent),  # Run from project root
        )

        duration = (datetime.now() - start).total_seconds()
        output = result.stdout + result.stderr

        success = result.returncode == 0

        if verbose:
            print(output)

        return success, output, duration

    except subprocess.TimeoutExpired:
        return False, "Test timed out after 120 seconds", 120.0
    except Exception as e:
        return False, f"Error running test: {e}", 0.0


def extract_test_counts(output: str) -> Tuple[int, int]:
    """Extract passed/total counts from test output."""
    import re

    # Look for "Total: X/Y passed"
    match = re.search(r"Total:\s*(\d+)/(\d+)\s*passed", output)
    if match:
        return int(match.group(1)), int(match.group(2))

    # Look for "X/Y tests passed"
    match = re.search(r"(\d+)/(\d+)\s*tests?\s*passed", output, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))

    return 0, 0


def main():
    parser = argparse.ArgumentParser(description="Run YCB v3 tests")
    parser.add_argument("--quick", action="store_true", help="Skip slow tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all output")
    parser.add_argument("--filter", type=str, help="Only run tests matching filter")
    args = parser.parse_args()

    print("=" * 70)
    print("YCB v3 - Test Suite Runner")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    results: Dict[str, Tuple[bool, int, int, float]] = {}
    total_tests = 0
    total_passed = 0
    total_duration = 0.0

    for name, path in TEST_FILES:
        # Apply filter
        if args.filter and args.filter.lower() not in name.lower():
            continue

        print(f"Running: {name}...", end=" ", flush=True)

        success, output, duration = run_test_file(name, path, args.verbose)
        passed, total = extract_test_counts(output)

        total_tests += total
        total_passed += passed
        total_duration += duration

        results[name] = (success, passed, total, duration)

        if success:
            print(f"PASS ({passed}/{total}) [{duration:.1f}s]")
        else:
            print(f"FAIL ({passed}/{total}) [{duration:.1f}s]")
            if not args.verbose:
                # Show failure summary
                lines = output.strip().split("\n")
                for line in lines[-10:]:  # Last 10 lines
                    if "error" in line.lower() or "fail" in line.lower():
                        print(f"    {line}")

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    files_passed = sum(1 for r in results.values() if r[0])
    files_total = len(results)

    print(f"\nTest Files: {files_passed}/{files_total} passed")
    print(f"Total Tests: {total_passed}/{total_tests} passed")
    print(f"Total Time: {total_duration:.1f}s")

    print("\nBy Component:")
    for name, (success, passed, total, duration) in results.items():
        status = "PASS" if success else "FAIL"
        print(f"  [{status}] {name}: {passed}/{total} tests ({duration:.1f}s)")

    # Exit code
    all_passed = all(r[0] for r in results.values())

    if all_passed:
        print(f"\n{'='*70}")
        print("ALL TESTS PASSED!")
        print(f"{'='*70}")
    else:
        print(f"\n{'='*70}")
        print("SOME TESTS FAILED")
        print(f"{'='*70}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
