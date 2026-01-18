#!/usr/bin/env python3
"""
Direct Bot Testing Script - Tests intent classification and routing internally.

This script tests the bot's intelligence layer directly without going through Telegram,
allowing faster iteration and debugging.

Usage:
    python scripts/test_bot_direct.py
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


@dataclass
class TestCase:
    id: str
    message: str
    expected_intent: str
    min_confidence: float = 0.5


@dataclass
class TestResult:
    test_id: str
    message: str
    expected_intent: str
    actual_intent: str
    confidence: float
    passed: bool
    classification_time_ms: int
    failure_reason: Optional[str] = None


TEST_CASES = [
    # Equipment Search
    TestCase("ES001", "find siemens motors", "EQUIPMENT_SEARCH", 0.7),
    TestCase("ES002", "what equipment do I have", "EQUIPMENT_SEARCH", 0.7),
    TestCase("ES003", "Is there anything about Stardust Racers in my CMMS", "EQUIPMENT_SEARCH", 0.6),
    TestCase("ES004", "show me my drives", "EQUIPMENT_SEARCH", 0.7),
    TestCase("ES005", "search for pumps", "EQUIPMENT_SEARCH", 0.7),
    TestCase("ES006", "list my gear", "EQUIPMENT_SEARCH", 0.6),

    # Work Orders
    TestCase("WO001", "create a work order", "WORK_ORDER_CREATE", 0.8),
    TestCase("WO002", "I need to report an issue with pump 3", "WORK_ORDER_CREATE", 0.6),
    TestCase("WO003", "show my work orders", "WORK_ORDER_STATUS", 0.8),
    TestCase("WO004", "what's pending", "WORK_ORDER_STATUS", 0.6),
    TestCase("WO005", "check my WOs", "WORK_ORDER_STATUS", 0.7),

    # Manual Questions
    TestCase("MQ001", "how do I reset a Siemens drive", "MANUAL_QUESTION", 0.7),
    TestCase("MQ002", "what does error code F0002 mean", "MANUAL_QUESTION", 0.7),
    TestCase("MQ003", "calibration procedure for VFD", "MANUAL_QUESTION", 0.7),
    TestCase("MQ004", "wiring diagram for motor starter", "MANUAL_QUESTION", 0.6),
    TestCase("MQ005", "instructions for setup", "MANUAL_QUESTION", 0.6),

    # Troubleshooting
    TestCase("TS001", "motor is overheating", "TROUBLESHOOT", 0.8),
    TestCase("TS002", "drive won't start", "TROUBLESHOOT", 0.8),
    TestCase("TS003", "getting error on the compressor", "TROUBLESHOOT", 0.7),
    TestCase("TS004", "pump making strange noise", "TROUBLESHOOT", 0.7),
    TestCase("TS005", "motor tripped again", "TROUBLESHOOT", 0.7),

    # General Chat
    TestCase("GC001", "hello", "GENERAL_CHAT", 0.9),
    TestCase("GC002", "thanks", "GENERAL_CHAT", 0.9),
    TestCase("GC003", "what can you do", "GENERAL_CHAT", 0.7),
    TestCase("GC004", "help", "GENERAL_CHAT", 0.9),
    TestCase("GC005", "good morning", "GENERAL_CHAT", 0.9),
]


async def run_tests():
    """Run all intent classification tests."""
    # Import here to ensure env is loaded
    from rivet_pro.core.intelligence.intent_classifier import IntentClassifier

    print("=" * 70)
    print("RIVET CMMS - Intent Classification Test Suite")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Test Cases: {len(TEST_CASES)}")
    print("=" * 70)

    classifier = IntentClassifier()
    results = []

    for test in TEST_CASES:
        print(f"\n[{test.id}] Testing: '{test.message}'")
        print(f"       Expected: {test.expected_intent} (min confidence: {test.min_confidence})")

        try:
            classification = await classifier.classify(test.message, user_id="test_user")

            actual_intent = classification.intent.value
            confidence = classification.confidence
            time_ms = classification.classification_time_ms

            # Check if passed
            intent_match = actual_intent == test.expected_intent
            confidence_ok = confidence >= test.min_confidence
            passed = intent_match and confidence_ok

            failure_reason = None
            if not intent_match:
                failure_reason = f"Intent mismatch: got {actual_intent}"
            elif not confidence_ok:
                failure_reason = f"Low confidence: {confidence:.2f} < {test.min_confidence}"

            result = TestResult(
                test_id=test.id,
                message=test.message,
                expected_intent=test.expected_intent,
                actual_intent=actual_intent,
                confidence=confidence,
                passed=passed,
                classification_time_ms=time_ms,
                failure_reason=failure_reason
            )

            status = "PASS" if passed else "FAIL"
            print(f"       Result: {status} | Actual: {actual_intent} ({confidence:.2f}) | {time_ms}ms")
            if failure_reason:
                print(f"       Reason: {failure_reason}")

            if classification.entities:
                print(f"       Entities: {classification.entities}")

        except Exception as e:
            result = TestResult(
                test_id=test.id,
                message=test.message,
                expected_intent=test.expected_intent,
                actual_intent="ERROR",
                confidence=0.0,
                passed=False,
                classification_time_ms=0,
                failure_reason=str(e)
            )
            print(f"       ERROR: {e}")

        results.append(result)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    avg_time = sum(r.classification_time_ms for r in results) / len(results)

    print(f"Total:     {len(results)}")
    print(f"Passed:    {passed}")
    print(f"Failed:    {failed}")
    print(f"Pass Rate: {passed/len(results)*100:.1f}%")
    print(f"Avg Time:  {avg_time:.0f}ms")

    # Group by intent
    print("\nResults by Intent:")
    intents = set(t.expected_intent for t in TEST_CASES)
    for intent in sorted(intents):
        intent_results = [r for r in results if r.expected_intent == intent]
        intent_passed = sum(1 for r in intent_results if r.passed)
        print(f"  {intent}: {intent_passed}/{len(intent_results)}")

    if failed > 0:
        print("\nFailed Tests:")
        for r in results:
            if not r.passed:
                print(f"  [{r.test_id}] {r.message}")
                print(f"           Expected: {r.expected_intent}, Got: {r.actual_intent} ({r.confidence:.2f})")
                print(f"           Reason: {r.failure_reason}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_tests())
    sys.exit(exit_code)
