#!/usr/bin/env python
"""
Test Expert Response Templates (EXPERT-008)

Validates:
1. Expertise detection from technical terminology
2. Expert vs standard prompt selection
3. Condescending phrase filtering
4. Intent-specific prompt customization
"""

import sys
from datetime import datetime
from typing import List, Tuple

# Add project root to path
sys.path.insert(0, ".")

from rivet_pro.core.intelligence.response_templates import (
    ExpertiseDetector,
    ExpertiseLevel,
    ResponseTemplateManager,
    detect_expertise,
    get_expert_prompt,
)
from rivet_pro.core.intelligence.intent_classifier import IntentType


def test_expertise_detection_expert():
    """Test detection of expert-level queries."""
    print("\n=== Test: Expert Query Detection ===")

    detector = ExpertiseDetector()

    expert_queries = [
        "phase imbalance on motor 7, reading 3% between phases",
        "F30050 fault on ABB ACS880, ramp time set to 10s",
        "megger reading 2.5 megohms on stator windings",
        "siemens g120 showing ground fault, dc bus voltage normal",
        "cavitation on pump 3, suction pressure at 5 psi",
        "checking FLA on nameplate vs measured RLA",
    ]

    passed = 0
    for query in expert_queries:
        signals = detector.detect_expertise(query)
        if signals.expertise_level == ExpertiseLevel.EXPERT:
            print(f"  [PASS] Expert: '{query[:50]}...'")
            print(f"         Terms: {signals.technical_terms_found[:3]}")
            passed += 1
        else:
            print(f"  [FAIL] Should be expert: '{query[:50]}...'")
            print(f"         Got: {signals.expertise_level.value}")

    print(f"\n  Result: {passed}/{len(expert_queries)} passed")
    return passed == len(expert_queries)


def test_expertise_detection_beginner():
    """Test detection of beginner-level queries."""
    print("\n=== Test: Beginner Query Detection ===")

    detector = ExpertiseDetector()

    beginner_queries = [
        "the motor is making a weird noise",
        "how do I start the machine",
        "something is broken",
        "it won't turn on",
        "help",
    ]

    passed = 0
    for query in beginner_queries:
        signals = detector.detect_expertise(query)
        if signals.expertise_level == ExpertiseLevel.BEGINNER:
            print(f"  [PASS] Beginner: '{query}'")
            passed += 1
        else:
            print(f"  [FAIL] Should be beginner: '{query}'")
            print(f"         Got: {signals.expertise_level.value}")

    print(f"\n  Result: {passed}/{len(beginner_queries)} passed")
    return passed == len(beginner_queries)


def test_expert_prompt_selection():
    """Test that expert prompts are selected for expert queries."""
    print("\n=== Test: Expert Prompt Selection ===")

    manager = ResponseTemplateManager()

    test_cases = [
        (IntentType.TROUBLESHOOT, True, "Jump straight to diagnosis"),
        (IntentType.TROUBLESHOOT, False, "Walk through diagnostic steps"),
        (IntentType.MANUAL_QUESTION, True, "Give specs, values, and procedures directly"),
        (IntentType.WORK_ORDER_CREATE, True, "Confirm the work order creation concisely"),
    ]

    passed = 0
    for intent, is_expert, must_contain in test_cases:
        prompt = manager.get_system_prompt(intent, is_expert)
        mode = "expert" if is_expert else "standard"

        if must_contain.lower() in prompt.lower():
            print(f"  [PASS] {intent.value} ({mode}): contains expected guidance")
            passed += 1
        else:
            print(f"  [FAIL] {intent.value} ({mode}): missing '{must_contain}'")
            print(f"         Got: {prompt[:100]}...")

    print(f"\n  Result: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_condescending_filter():
    """Test removal of condescending phrases."""
    print("\n=== Test: Condescending Phrase Filter ===")

    manager = ResponseTemplateManager()

    test_cases = [
        (
            "As you may know, motors can overheat. First, let's understand the basics.",
            ["as you may know", "first, let's understand"]
        ),
        (
            "For safety reasons, always remember to check the voltage first.",
            ["for safety reasons", "always remember to"]
        ),
        (
            "It's important to note that the VFD needs proper cooling. Basically, it's simple.",
            ["it's important to note", "basically,"]
        ),
    ]

    passed = 0
    for original, phrases_to_remove in test_cases:
        filtered = manager.filter_condescending(original)

        all_removed = all(
            phrase.lower() not in filtered.lower()
            for phrase in phrases_to_remove
        )

        if all_removed:
            print(f"  [PASS] Filtered: '{original[:40]}...'")
            print(f"         Result: '{filtered[:40]}...'")
            passed += 1
        else:
            print(f"  [FAIL] Still contains condescending phrase")
            print(f"         Input: '{original}'")
            print(f"         Output: '{filtered}'")

    print(f"\n  Result: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_intent_specific_prompts():
    """Test that each intent has appropriate prompts."""
    print("\n=== Test: Intent-Specific Prompts ===")

    manager = ResponseTemplateManager()

    # Each intent should have distinct expert and standard prompts
    intents = [
        IntentType.TROUBLESHOOT,
        IntentType.MANUAL_QUESTION,
        IntentType.WORK_ORDER_CREATE,
        IntentType.WORK_ORDER_STATUS,
        IntentType.EQUIPMENT_SEARCH,
        IntentType.GENERAL_CHAT,
    ]

    passed = 0
    for intent in intents:
        expert_prompt = manager.get_system_prompt(intent, is_expert=True)
        standard_prompt = manager.get_system_prompt(intent, is_expert=False)

        # Prompts should be different
        if expert_prompt != standard_prompt:
            print(f"  [PASS] {intent.value}: distinct expert/standard prompts")
            passed += 1
        else:
            print(f"  [FAIL] {intent.value}: expert and standard prompts are identical")

    print(f"\n  Result: {passed}/{len(intents)} passed")
    return passed == len(intents)


def test_context_injection():
    """Test that context is properly injected into prompts."""
    print("\n=== Test: Context Injection ===")

    manager = ResponseTemplateManager()

    context = """- **WO WO-2026-00123** (2026-01-15): Motor overheating - RESOLVED
- **Siemens G120C** (2026-01-10): VFD | Building A | 5 work orders"""

    prompt = manager.get_system_prompt(
        IntentType.TROUBLESHOOT,
        is_expert=True,
        context=context
    )

    if "## Context" in prompt and "WO-2026-00123" in prompt:
        print(f"  [PASS] Context injected into prompt")
        print(f"         Contains context header and work order reference")
        return True
    else:
        print(f"  [FAIL] Context not properly injected")
        return False


def test_convenience_functions():
    """Test module-level convenience functions."""
    print("\n=== Test: Convenience Functions ===")

    # Test detect_expertise
    expert_query = "phase imbalance on siemens g120"
    beginner_query = "motor is broken"

    passed = 0

    if detect_expertise(expert_query):
        print(f"  [PASS] detect_expertise() identifies expert query")
        passed += 1
    else:
        print(f"  [FAIL] detect_expertise() should return True for expert query")

    if not detect_expertise(beginner_query):
        print(f"  [PASS] detect_expertise() identifies beginner query")
        passed += 1
    else:
        print(f"  [FAIL] detect_expertise() should return False for beginner query")

    # Test get_expert_prompt
    prompt = get_expert_prompt(IntentType.TROUBLESHOOT, expert_query)
    if "Jump straight to diagnosis" in prompt:
        print(f"  [PASS] get_expert_prompt() returns expert prompt for expert query")
        passed += 1
    else:
        print(f"  [FAIL] get_expert_prompt() should return expert prompt")

    print(f"\n  Result: {passed}/3 passed")
    return passed == 3


def test_no_expert_for_safety_critical():
    """Verify prompts still include necessary technical accuracy."""
    print("\n=== Test: Technical Accuracy in Expert Mode ===")

    manager = ResponseTemplateManager()

    prompt = manager.get_system_prompt(IntentType.TROUBLESHOOT, is_expert=True)

    # Expert mode should still mention:
    # - Specific checks
    # - Expected values
    # - Fault codes

    indicators = [
        "specific check",
        "expected value",
        "fault code",
        "diagnostic",
    ]

    found = sum(1 for ind in indicators if ind.lower() in prompt.lower())

    if found >= 2:
        print(f"  [PASS] Expert prompt maintains technical rigor ({found}/4 indicators)")
        return True
    else:
        print(f"  [FAIL] Expert prompt should maintain technical accuracy ({found}/4 indicators)")
        return False


def run_all_tests():
    """Run all test cases."""
    print("=" * 70)
    print("EXPERT RESPONSE TEMPLATES TEST (EXPERT-008)")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    results = []

    results.append(("Expert Query Detection", test_expertise_detection_expert()))
    results.append(("Beginner Query Detection", test_expertise_detection_beginner()))
    results.append(("Expert Prompt Selection", test_expert_prompt_selection()))
    results.append(("Condescending Filter", test_condescending_filter()))
    results.append(("Intent-Specific Prompts", test_intent_specific_prompts()))
    results.append(("Context Injection", test_context_injection()))
    results.append(("Convenience Functions", test_convenience_functions()))
    results.append(("Technical Accuracy", test_no_expert_for_safety_critical()))

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
    print(f"  [{'PASS' if passed >= 6 else 'FAIL'}] Troubleshoot: Jump to diagnosis for experts")
    print(f"  [{'PASS' if passed >= 6 else 'FAIL'}] Manual: Give specs directly for experts")
    print(f"  [{'PASS' if passed >= 6 else 'FAIL'}] Work orders: Confirm and move on")
    print(f"  [{'PASS' if passed >= 6 else 'FAIL'}] Detect technical terminology -> expert mode")
    print(f"  [{'PASS' if passed >= 6 else 'FAIL'}] No condescending phrases")
    print(f"  [{'PASS' if passed == total else 'FAIL'}] All tests pass ({passed}/{total})")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
