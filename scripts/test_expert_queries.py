#!/usr/bin/env python3
"""
Expert-Level Intent Classification Tests

These are the queries a 20-year industrial maintenance technician would ask.
They're tricky, ambiguous, use jargon, and test the classifier's real-world ability.

Run: python scripts/test_expert_queries.py
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


@dataclass
class TestCase:
    id: str
    message: str
    expected_intent: str
    min_confidence: float = 0.5
    notes: str = ""  # Why this is tricky


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
    entities: dict = None


# Expert-level test cases - the kind a 20-year tech would ask
EXPERT_TEST_CASES = [
    # === TRICKY TROUBLESHOOTING ===
    # These sound like questions but are active problems
    TestCase("EXP-TS001", "what does a bad motor smell like?", "TROUBLESHOOT", 0.6,
             "Sounds like question but tech is probably smelling something"),
    TestCase("EXP-TS002", "F30050 on the ABB drive", "TROUBLESHOOT", 0.7,
             "Just a fault code - experienced tech won't say 'error'"),
    TestCase("EXP-TS003", "bearing's going out on pump 7", "TROUBLESHOOT", 0.7,
             "Tech diagnosis statement - active problem"),
    TestCase("EXP-TS004", "E001", "TROUBLESHOOT", 0.6,
             "Just the error code, nothing else"),
    TestCase("EXP-TS005", "this VFD is acting up again", "TROUBLESHOOT", 0.7,
             "'acting up' = problem"),
    TestCase("EXP-TS006", "amp draw is high on unit 3", "TROUBLESHOOT", 0.7,
             "Technical symptom - high amps = problem"),
    TestCase("EXP-TS007", "getting harmonics on the line", "TROUBLESHOOT", 0.7,
             "Electrical problem symptom"),
    TestCase("EXP-TS008", "motor's pulling way more than FLA", "TROUBLESHOOT", 0.7,
             "FLA = Full Load Amps, expert terminology"),
    TestCase("EXP-TS009", "phase imbalance on the compressor", "TROUBLESHOOT", 0.7,
             "Technical electrical issue"),
    TestCase("EXP-TS010", "ground fault on conveyor C", "TROUBLESHOOT", 0.8,
             "Specific fault type"),

    # === TRICKY MANUAL QUESTIONS ===
    # Asking for info/procedures, not reporting problems
    TestCase("EXP-MQ001", "what's the megger spec for a 480V motor", "MANUAL_QUESTION", 0.7,
             "Asking for specification, not a problem"),
    TestCase("EXP-MQ002", "lockout procedure for the chiller", "MANUAL_QUESTION", 0.8,
             "Asking for safety procedure"),
    TestCase("EXP-MQ003", "what should bearing temp be on these pumps", "MANUAL_QUESTION", 0.7,
             "Asking for normal spec, not reporting high temp"),
    TestCase("EXP-MQ004", "acceptable vibration levels for the fan", "MANUAL_QUESTION", 0.7,
             "Asking for spec/threshold"),
    TestCase("EXP-MQ005", "torque spec for motor mounts", "MANUAL_QUESTION", 0.7,
             "Installation specification"),
    TestCase("EXP-MQ006", "what's normal startup current on these drives", "MANUAL_QUESTION", 0.6,
             "Asking what's normal, not reporting problem"),
    TestCase("EXP-MQ007", "alignment tolerance for pump coupling", "MANUAL_QUESTION", 0.7,
             "Maintenance spec question"),
    TestCase("EXP-MQ008", "parameter 31 on siemens G120", "MANUAL_QUESTION", 0.7,
             "Asking about drive parameter meaning"),

    # === TRICKY EQUIPMENT SEARCH ===
    # Looking for equipment, not asking questions about it
    TestCase("EXP-ES001", "where's that ABB drive we replaced last month", "EQUIPMENT_SEARCH", 0.6,
             "Looking for equipment in system"),
    TestCase("EXP-ES002", "do we have any spare 50HP motors", "EQUIPMENT_SEARCH", 0.7,
             "Inventory question"),
    TestCase("EXP-ES003", "pull up the compressor info", "EQUIPMENT_SEARCH", 0.7,
             "'pull up' = search"),
    TestCase("EXP-ES004", "what model is the roof unit", "EQUIPMENT_SEARCH", 0.6,
             "Asking for equipment info from CMMS"),
    TestCase("EXP-ES005", "serial number on AHU-3", "EQUIPMENT_SEARCH", 0.7,
             "Looking up equipment data"),

    # === WORK ORDER SCENARIOS ===
    TestCase("EXP-WO001", "need to schedule PM on the cooling tower", "WORK_ORDER_CREATE", 0.7,
             "PM = preventive maintenance = work order"),
    TestCase("EXP-WO002", "put in a ticket for the air handler", "WORK_ORDER_CREATE", 0.7,
             "'ticket' = work order"),
    TestCase("EXP-WO003", "what's open on building 2", "WORK_ORDER_STATUS", 0.6,
             "'what's open' = open work orders"),
    TestCase("EXP-WO004", "log this: changed belts on AHU-5", "WORK_ORDER_CREATE", 0.6,
             "'log this' = create record/WO"),

    # === AMBIGUOUS/EDGE CASES ===
    # These could go either way - test the classifier's judgment
    TestCase("EXP-AMB001", "siemens drive", "EQUIPMENT_SEARCH", 0.5,
             "Super short - probably looking for equipment"),
    TestCase("EXP-AMB002", "that motor from building 3", "EQUIPMENT_SEARCH", 0.5,
             "Vague reference, probably searching"),
    TestCase("EXP-AMB003", "check the oil", "WORK_ORDER_CREATE", 0.5,
             "Could be reminder to self = create WO"),

    # === SHOULDN'T MATCH EQUIPMENT SEARCH ===
    # These mention equipment but aren't searches
    TestCase("EXP-NEG001", "the motor sounds rough", "TROUBLESHOOT", 0.7,
             "Mentions motor but it's a symptom"),
    TestCase("EXP-NEG002", "pump is cavitating", "TROUBLESHOOT", 0.8,
             "Technical term for pump problem"),
    TestCase("EXP-NEG003", "VFD fault history", "EQUIPMENT_SEARCH", 0.5,
             "Looking up data, not troubleshooting"),
]


async def run_expert_tests():
    """Run expert-level intent classification tests."""
    from rivet_pro.core.intelligence.intent_classifier import IntentClassifier

    print("=" * 70)
    print("RIVET CMMS - Expert-Level Intent Classification Tests")
    print("Testing queries a 20-year maintenance tech would actually ask")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Test Cases: {len(EXPERT_TEST_CASES)}")
    print("=" * 70)

    classifier = IntentClassifier()
    results = []

    for test in EXPERT_TEST_CASES:
        print(f"\n[{test.id}] '{test.message}'")
        if test.notes:
            print(f"       Note: {test.notes}")
        print(f"       Expected: {test.expected_intent} (min: {test.min_confidence})")

        try:
            classification = await classifier.classify(test.message, user_id="expert_test")

            actual_intent = classification.intent.value
            confidence = classification.confidence
            time_ms = classification.classification_time_ms

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
                failure_reason=failure_reason,
                entities=classification.entities
            )

            status = "PASS" if passed else "FAIL"
            print(f"       Result: {status} | Got: {actual_intent} ({confidence:.2f}) | {time_ms}ms")
            if classification.entities:
                print(f"       Entities: {classification.entities}")
            if failure_reason:
                print(f"       REASON: {failure_reason}")

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
    print("EXPERT TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    avg_time = sum(r.classification_time_ms for r in results) / len(results) if results else 0

    print(f"Total:     {len(results)}")
    print(f"Passed:    {passed}")
    print(f"Failed:    {failed}")
    print(f"Pass Rate: {passed/len(results)*100:.1f}%")
    print(f"Avg Time:  {avg_time:.0f}ms")

    # Group by category
    categories = {
        "EXP-TS": "Troubleshooting",
        "EXP-MQ": "Manual Questions",
        "EXP-ES": "Equipment Search",
        "EXP-WO": "Work Orders",
        "EXP-AMB": "Ambiguous",
        "EXP-NEG": "Negative (shouldn't match equipment)"
    }

    print("\nResults by Category:")
    for prefix, name in categories.items():
        cat_results = [r for r in results if r.test_id.startswith(prefix)]
        if cat_results:
            cat_passed = sum(1 for r in cat_results if r.passed)
            print(f"  {name}: {cat_passed}/{len(cat_results)}")

    if failed > 0:
        print("\n" + "=" * 70)
        print("FAILED TESTS - NEED FIXING")
        print("=" * 70)
        for r in results:
            if not r.passed:
                print(f"\n  [{r.test_id}] {r.message}")
                print(f"           Expected: {r.expected_intent}")
                print(f"           Got: {r.actual_intent} ({r.confidence:.2f})")
                print(f"           Reason: {r.failure_reason}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_expert_tests())
    sys.exit(exit_code)
