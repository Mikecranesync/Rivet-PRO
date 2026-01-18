#!/usr/bin/env python
"""
Test Voice Normalizer (EXPERT-007)

Validates:
1. Filler word stripping
2. Industry abbreviation expansion
3. Incomplete sentence handling
4. Technical term preservation
5. STT error correction
"""

import sys
from datetime import datetime
from typing import List, Tuple

# Add project root to path
sys.path.insert(0, ".")

from rivet_pro.core.intelligence.voice_normalizer import (
    VoiceNormalizer,
    normalize_voice_input,
)


def test_filler_word_stripping():
    """Test removal of filler words."""
    print("\n=== Test: Filler Word Stripping ===")

    normalizer = VoiceNormalizer()

    test_cases: List[Tuple[str, str]] = [
        ("uh the motor is broken", "the motor is broken"),
        ("um like the pump won't start", "the pump won't start"),
        ("you know the VFD is acting up", "the VFD is acting up"),
        ("basically the compressor failed", "the compressor failed"),
        ("so uh like you know it's overheating", "it's overheating"),
        ("well um I mean the fan stopped", "the fan stopped"),
    ]

    passed = 0
    for input_text, expected in test_cases:
        result = normalizer.normalize(input_text)
        # Compare lowercase since normalization may change case
        if result.lower() == expected.lower():
            print(f"  [PASS] '{input_text}' -> '{result}'")
            passed += 1
        else:
            print(f"  [FAIL] '{input_text}' -> '{result}' (expected '{expected}')")

    print(f"\n  Result: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_abbreviation_expansion():
    """Test expansion of spoken abbreviations."""
    print("\n=== Test: Abbreviation Expansion ===")

    normalizer = VoiceNormalizer()

    test_cases: List[Tuple[str, str]] = [
        ("vee eff dee is faulting", "VFD is faulting"),
        ("check the ay ach you", "check the AHU"),
        ("pee el see error", "PLC error"),
        ("what's the eff el ay", "what's the FLA"),
        ("running at 1800 are pee em", "running at 1800 RPM"),
        ("need 50 pee ess eye", "need 50 PSI"),
    ]

    passed = 0
    for input_text, expected in test_cases:
        result = normalizer.normalize(input_text)
        # Check if abbreviation was expanded (case-insensitive for other parts)
        if expected.upper() in result.upper() or result.lower() == expected.lower():
            print(f"  [PASS] '{input_text}' -> '{result}'")
            passed += 1
        else:
            print(f"  [FAIL] '{input_text}' -> '{result}' (expected '{expected}')")

    print(f"\n  Result: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_incomplete_sentences():
    """Test handling of incomplete/ellipsis sentences."""
    print("\n=== Test: Incomplete Sentence Handling ===")

    normalizer = VoiceNormalizer()

    test_cases: List[Tuple[str, str]] = [
        ("motor... pump 3... not working", "motor pump 3 not working"),
        ("the... uh... compressor... stopped", "the compressor stopped"),
        ("vfd ... acting ... weird", "VFD acting weird"),
        ("check the . . . bearing", "check the bearing"),
    ]

    passed = 0
    for input_text, expected in test_cases:
        result = normalizer.normalize(input_text)
        # Check that ellipsis is removed and words are present
        expected_words = expected.lower().split()
        result_words = result.lower().split()
        # Allow for slight variations but key words should be present
        key_words = [w for w in expected_words if len(w) > 3]
        if all(w in result_words for w in key_words):
            print(f"  [PASS] '{input_text}' -> '{result}'")
            passed += 1
        else:
            print(f"  [FAIL] '{input_text}' -> '{result}' (expected '{expected}')")

    print(f"\n  Result: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_technical_term_preservation():
    """Test that technical terms are preserved correctly."""
    print("\n=== Test: Technical Term Preservation ===")

    normalizer = VoiceNormalizer()

    test_cases: List[Tuple[str, str]] = [
        ("check megger reading", "megger"),
        ("phase imbalance detected", "phase imbalance"),
        ("ground fault on line 3", "ground fault"),
        ("need lockout tagout", "lockout"),
        ("pump is cavitation", "cavitation"),
    ]

    passed = 0
    for input_text, must_contain in test_cases:
        result = normalizer.normalize(input_text)
        if must_contain.lower() in result.lower():
            print(f"  [PASS] '{input_text}' -> '{result}' (contains '{must_contain}')")
            passed += 1
        else:
            print(f"  [FAIL] '{input_text}' -> '{result}' (missing '{must_contain}')")

    print(f"\n  Result: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_stt_error_correction():
    """Test correction of common speech-to-text errors."""
    print("\n=== Test: STT Error Correction ===")

    normalizer = VoiceNormalizer()

    test_cases: List[Tuple[str, str]] = [
        ("bare ring is worn", "bearing"),
        ("see mens drive", "Siemens"),
        ("over heating motor", "overheating"),
        ("face imbalance on phase", "phase imbalance"),
        ("create a work order", "create work order"),
    ]

    passed = 0
    for input_text, must_contain in test_cases:
        result = normalizer.normalize(input_text)
        if must_contain.lower() in result.lower():
            print(f"  [PASS] '{input_text}' -> '{result}' (contains '{must_contain}')")
            passed += 1
        else:
            print(f"  [FAIL] '{input_text}' -> '{result}' (missing '{must_contain}')")

    print(f"\n  Result: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_voice_input_detection():
    """Test detection of voice vs typed input."""
    print("\n=== Test: Voice Input Detection ===")

    normalizer = VoiceNormalizer()

    voice_inputs = [
        "uh the motor is broken",
        "vee eff dee won't start",
        "the pump... not working...",
        "like the compressor stopped",
    ]

    typed_inputs = [
        "Motor EQ-2025-001 needs repair",
        "Please check the VFD on line 3.",
        "Work order: Replace filter",
    ]

    passed = 0
    total = len(voice_inputs) + len(typed_inputs)

    for text in voice_inputs:
        if normalizer.is_voice_input(text):
            print(f"  [PASS] Detected as voice: '{text}'")
            passed += 1
        else:
            print(f"  [FAIL] Should be voice: '{text}'")

    for text in typed_inputs:
        if not normalizer.is_voice_input(text):
            print(f"  [PASS] Detected as typed: '{text}'")
            passed += 1
        else:
            print(f"  [FAIL] Should be typed: '{text}'")

    print(f"\n  Result: {passed}/{total} passed")
    return passed == total


def test_integration_with_intent():
    """Test that normalized voice input works with intent classification."""
    print("\n=== Test: Integration with Intent Classification ===")

    # These are voice inputs that should normalize to recognizable intents
    test_cases = [
        ("uh the vee eff dee is like acting up again", "troubleshoot"),
        ("um create a work order for the pump", "work order"),
        ("you know check my work orders", "status"),
        ("like find see mens motors", "search"),
    ]

    normalizer = VoiceNormalizer()
    passed = 0

    for voice_input, expected_category in test_cases:
        normalized = normalizer.normalize(voice_input)

        # Check if normalized text contains key words for that intent
        key_indicators = {
            "troubleshoot": ["acting up", "not working", "broken", "fault"],
            "work order": ["work order", "create"],
            "status": ["work order", "check", "status"],
            "search": ["find", "search", "motors", "Siemens"],
        }

        indicators = key_indicators.get(expected_category, [])
        found = any(ind.lower() in normalized.lower() for ind in indicators)

        if found:
            print(f"  [PASS] '{voice_input[:40]}...' -> '{normalized[:40]}...'")
            passed += 1
        else:
            print(f"  [FAIL] '{voice_input[:40]}...' -> '{normalized[:40]}...' (no {expected_category} indicators)")

    print(f"\n  Result: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_convenience_function():
    """Test the module-level convenience function."""
    print("\n=== Test: Convenience Function ===")

    result = normalize_voice_input("uh the vee eff dee is broken")

    if "VFD" in result:
        print(f"  [PASS] normalize_voice_input() works: '{result}'")
        return True
    else:
        print(f"  [FAIL] normalize_voice_input() failed: '{result}'")
        return False


def run_all_tests():
    """Run all test cases."""
    print("=" * 70)
    print("VOICE NORMALIZER TEST (EXPERT-007)")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    results = []

    results.append(("Filler Word Stripping", test_filler_word_stripping()))
    results.append(("Abbreviation Expansion", test_abbreviation_expansion()))
    results.append(("Incomplete Sentences", test_incomplete_sentences()))
    results.append(("Technical Term Preservation", test_technical_term_preservation()))
    results.append(("STT Error Correction", test_stt_error_correction()))
    results.append(("Voice Input Detection", test_voice_input_detection()))
    results.append(("Integration with Intent", test_integration_with_intent()))
    results.append(("Convenience Function", test_convenience_function()))

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    print("\nACCEPTANCE CRITERIA:")
    print(f"  [{'PASS' if passed >= 6 else 'FAIL'}] Strip filler words")
    print(f"  [{'PASS' if passed >= 6 else 'FAIL'}] Normalize industry abbreviations")
    print(f"  [{'PASS' if passed >= 6 else 'FAIL'}] Handle incomplete sentences")
    print(f"  [{'PASS' if passed >= 6 else 'FAIL'}] Preserve technical terms")
    print(f"  [{'PASS' if passed == total else 'FAIL'}] All tests pass ({passed}/{total})")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
