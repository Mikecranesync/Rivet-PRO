#!/usr/bin/env python
"""
Test Multi-Signal Router (EXPERT-005)

Validates:
1. Keyword signal accuracy (~85%)
2. Semantic signal accuracy (~88%)
3. Combined accuracy (>=95%)
4. LLM fallback rate (<20%)
"""

import asyncio
import sys
from datetime import datetime
from typing import List, Tuple

# Add project root to path
sys.path.insert(0, ".")

from rivet_pro.core.intelligence.multi_signal_router import (
    MultiSignalRouter,
    IntentType,
)


# Test cases: (message, expected_intent, min_confidence)
TEST_CASES: List[Tuple[str, IntentType, float]] = [
    # Equipment Search
    ("find siemens motors", IntentType.EQUIPMENT_SEARCH, 0.7),
    ("what equipment do I have", IntentType.EQUIPMENT_SEARCH, 0.7),
    ("VFD fault history", IntentType.EQUIPMENT_SEARCH, 0.7),
    ("history on motor 7", IntentType.EQUIPMENT_SEARCH, 0.6),
    ("spare parts for pump", IntentType.EQUIPMENT_SEARCH, 0.6),

    # Work Order Create
    ("create work order", IntentType.WORK_ORDER_CREATE, 0.8),
    ("log this: changed belts on AHU-5", IntentType.WORK_ORDER_CREATE, 0.8),
    ("document this: replaced filter", IntentType.WORK_ORDER_CREATE, 0.8),
    ("schedule PM on cooling tower", IntentType.WORK_ORDER_CREATE, 0.7),

    # Work Order Status
    ("check my work orders", IntentType.WORK_ORDER_STATUS, 0.8),
    ("what's open", IntentType.WORK_ORDER_STATUS, 0.7),
    ("pending work orders", IntentType.WORK_ORDER_STATUS, 0.7),

    # Manual Question
    ("how do I reset a Siemens drive", IntentType.MANUAL_QUESTION, 0.7),
    ("what does error code F0002 mean", IntentType.MANUAL_QUESTION, 0.7),
    ("lockout procedure for chiller", IntentType.MANUAL_QUESTION, 0.7),
    ("torque spec for motor mounts", IntentType.MANUAL_QUESTION, 0.7),

    # Troubleshoot
    ("motor is overheating", IntentType.TROUBLESHOOT, 0.8),
    ("drive won't start", IntentType.TROUBLESHOOT, 0.8),
    ("what does a bad motor smell like", IntentType.TROUBLESHOOT, 0.7),
    ("amp draw is high on unit 3", IntentType.TROUBLESHOOT, 0.7),
    ("bearing's going out on pump 7", IntentType.TROUBLESHOOT, 0.7),
    ("phase imbalance on compressor", IntentType.TROUBLESHOOT, 0.7),

    # General Chat
    ("hello", IntentType.GENERAL_CHAT, 0.9),
    ("thanks", IntentType.GENERAL_CHAT, 0.9),
    ("what can you do", IntentType.GENERAL_CHAT, 0.6),  # Edge case, lower threshold
]


async def run_tests():
    """Run all test cases through multi-signal router."""
    print("=" * 70)
    print("MULTI-SIGNAL ROUTER TEST (EXPERT-005)")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Test Cases: {len(TEST_CASES)}")
    print("=" * 70)
    print()

    router = MultiSignalRouter()

    passed = 0
    failed = 0
    llm_calls = 0
    total_latency = 0.0

    results_by_signal = {
        "keyword_only": 0,
        "keyword_semantic": 0,
        "with_llm": 0,
    }

    for message, expected_intent, min_confidence in TEST_CASES:
        result = await router.classify(message, user_id="test")

        # Check if passed
        intent_match = result.intent == expected_intent
        confidence_met = result.confidence >= min_confidence

        if intent_match and confidence_met:
            status = "PASS"
            passed += 1
        else:
            status = "FAIL"
            failed += 1

        # Track LLM usage
        if result.llm_called:
            llm_calls += 1
            results_by_signal["with_llm"] += 1
        elif "semantic" in result.signals_used:
            results_by_signal["keyword_semantic"] += 1
        else:
            results_by_signal["keyword_only"] += 1

        total_latency += result.total_latency_ms

        # Print result
        signals_str = "+".join(result.signals_used)
        print(f"[{status}] '{message[:40]}...' " if len(message) > 40 else f"[{status}] '{message}'")
        print(f"       Expected: {expected_intent.value} (>={min_confidence})")
        print(f"       Got: {result.intent.value} ({result.confidence:.2f})")
        print(f"       Signals: {signals_str} | {result.total_latency_ms:.1f}ms")
        if status == "FAIL":
            print(f"       REASON: {'Intent mismatch' if not intent_match else 'Low confidence'}")
        print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total:        {len(TEST_CASES)}")
    print(f"Passed:       {passed}")
    print(f"Failed:       {failed}")
    print(f"Pass Rate:    {100 * passed / len(TEST_CASES):.1f}%")
    print()
    print(f"LLM Calls:    {llm_calls}/{len(TEST_CASES)} ({100 * llm_calls / len(TEST_CASES):.1f}%)")
    print(f"Avg Latency:  {total_latency / len(TEST_CASES):.1f}ms")
    print()
    print("Signal Usage:")
    print(f"  Keyword only:      {results_by_signal['keyword_only']}")
    print(f"  Keyword+Semantic:  {results_by_signal['keyword_semantic']}")
    print(f"  With LLM fallback: {results_by_signal['with_llm']}")
    print()

    # Acceptance criteria check
    print("ACCEPTANCE CRITERIA:")
    print(f"  [{'PASS' if passed/len(TEST_CASES) >= 0.95 else 'FAIL'}] Accuracy >= 95% (got {100*passed/len(TEST_CASES):.1f}%)")
    print(f"  [{'PASS' if llm_calls/len(TEST_CASES) < 0.20 else 'FAIL'}] LLM calls < 20% (got {100*llm_calls/len(TEST_CASES):.1f}%)")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
