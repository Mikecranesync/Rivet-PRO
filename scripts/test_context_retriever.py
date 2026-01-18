#!/usr/bin/env python
"""
Test Context Retriever (EXPERT-006)

Validates:
1. Equipment term extraction
2. Symptom keyword extraction
3. Fault code pattern matching
4. Context formatting for LLM injection
5. Appropriate filtering by intent type
"""

import asyncio
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

# Add project root to path
sys.path.insert(0, ".")

from rivet_pro.core.intelligence.context_retriever import (
    ContextRetriever,
    ContextMatch,
    RetrievedContext,
)
from rivet_pro.core.intelligence.intent_classifier import IntentType


class MockDatabase:
    """Mock database for testing without real DB connection."""

    def __init__(self, work_orders=None, equipment=None):
        self.work_orders = work_orders or []
        self.equipment = equipment or []

    async def execute_query_async(self, query, params, fetch_mode=None):
        """Mock query execution based on query type."""
        if "work_orders" in query.lower():
            return self.work_orders
        elif "cmms_equipment" in query.lower():
            return self.equipment
        return []


def test_equipment_term_extraction():
    """Test extraction of equipment keywords."""
    print("\n=== Test: Equipment Term Extraction ===")

    db = MockDatabase()
    retriever = ContextRetriever(db)

    test_cases = [
        ("motor is overheating", ["motor"]),
        ("VFD won't start", ["vfd"]),
        ("check the pump and compressor", ["pump", "compressor"]),
        ("hello", []),
        ("fan making noise on ahu-5", ["fan", "ahu"]),
    ]

    passed = 0
    for message, expected in test_cases:
        result = retriever._extract_equipment_terms(message)
        if set(result) == set(expected):
            print(f"  [PASS] '{message}' -> {result}")
            passed += 1
        else:
            print(f"  [FAIL] '{message}' -> {result} (expected {expected})")

    print(f"\n  Result: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_symptom_extraction():
    """Test extraction of symptom keywords."""
    print("\n=== Test: Symptom Keyword Extraction ===")

    db = MockDatabase()
    retriever = ContextRetriever(db)

    test_cases = [
        ("motor is overheating", ["overheating"]),
        ("weird noise from pump", ["noise"]),
        ("fault code showing", ["fault"]),
        ("won't start and making smoke", ["won't start", "smoke"]),
        ("equipment list", []),
    ]

    passed = 0
    for message, expected in test_cases:
        result = retriever._extract_symptoms(message)
        if set(result) == set(expected):
            print(f"  [PASS] '{message}' -> {result}")
            passed += 1
        else:
            print(f"  [FAIL] '{message}' -> {result} (expected {expected})")

    print(f"\n  Result: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_fault_code_extraction():
    """Test extraction of fault codes."""
    print("\n=== Test: Fault Code Extraction ===")

    db = MockDatabase()
    retriever = ContextRetriever(db)

    test_cases = [
        ("F0002 on the drive", ["F0002"]),
        ("error code E-001", ["E-001"]),
        ("showing F30050 and F30051", ["F30050", "F30051"]),
        ("no fault codes here", []),
        ("A12 is too short", []),  # 2 digits minimum
        ("FAULT_123 appeared", ["FAULT_123"]),
    ]

    passed = 0
    for message, expected in test_cases:
        result = retriever._extract_fault_codes(message)
        # Compare uppercase
        result_upper = [r.upper() for r in result]
        expected_upper = [e.upper() for e in expected]
        if set(result_upper) == set(expected_upper):
            print(f"  [PASS] '{message}' -> {result}")
            passed += 1
        else:
            print(f"  [FAIL] '{message}' -> {result} (expected {expected})")

    print(f"\n  Result: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_context_formatting():
    """Test formatting of context for LLM injection."""
    print("\n=== Test: Context Formatting ===")

    db = MockDatabase()
    retriever = ContextRetriever(db)

    matches = [
        ContextMatch(
            source='work_order',
            relevance_score=0.85,
            title='WO WO-2026-00123 (Siemens G120C)',
            summary='Motor overheating - RESOLVED',
            equipment_number='EQ-2026-00001',
            created_at='2026-01-15',
            status='completed'
        ),
        ContextMatch(
            source='equipment',
            relevance_score=0.60,
            title='Siemens G120C',
            summary='VFD | Building A | 5 work orders',
            equipment_number='EQ-2026-00001',
            created_at='2026-01-10',
        ),
    ]

    formatted = retriever._format_context_for_prompt(matches)

    print(f"  Formatted output:\n{formatted}\n")

    # Check structure
    passed = True
    if "WO-2026-00123" not in formatted:
        print("  [FAIL] Work order number not in output")
        passed = False
    if "RESOLVED" not in formatted:
        print("  [FAIL] Status not in output")
        passed = False
    if "Siemens G120C" not in formatted:
        print("  [FAIL] Equipment name not in output")
        passed = False
    if passed:
        print("  [PASS] Formatting includes all expected elements")

    return passed


async def test_intent_filtering():
    """Test that context is only retrieved for relevant intents."""
    print("\n=== Test: Intent Filtering ===")

    db = MockDatabase()
    retriever = ContextRetriever(db)

    # Should NOT retrieve for general chat
    result = await retriever.get_relevant_context(
        message="hello",
        intent=IntentType.GENERAL_CHAT,
        user_id="test"
    )
    if not result.has_relevant_history and len(result.matches) == 0:
        print("  [PASS] GENERAL_CHAT returns empty context")
    else:
        print("  [FAIL] GENERAL_CHAT should not retrieve context")
        return False

    # Should NOT retrieve for work order create
    result = await retriever.get_relevant_context(
        message="create work order",
        intent=IntentType.WORK_ORDER_CREATE,
        user_id="test"
    )
    if not result.has_relevant_history:
        print("  [PASS] WORK_ORDER_CREATE returns empty context")
    else:
        print("  [FAIL] WORK_ORDER_CREATE should not retrieve context")
        return False

    # SHOULD retrieve for troubleshoot (even if no results)
    db_with_data = MockDatabase(
        work_orders=[{
            'work_order_number': 'WO-2026-00001',
            'equipment_number': 'EQ-2026-00001',
            'title': 'Motor overheating issue',
            'description': 'Motor running hot',
            'status': 'completed',
            'fault_codes': ['F0002'],
            'created_at': '2026-01-15',
            'manufacturer': 'Siemens',
            'model_number': 'G120C'
        }]
    )
    retriever_with_data = ContextRetriever(db_with_data)

    result = await retriever_with_data.get_relevant_context(
        message="motor is overheating",
        intent=IntentType.TROUBLESHOOT,
        user_id="test"
    )
    if len(result.matches) > 0:
        print(f"  [PASS] TROUBLESHOOT retrieves context ({len(result.matches)} matches)")
    else:
        print("  [FAIL] TROUBLESHOOT should retrieve context when available")
        return False

    return True


async def test_relevance_scoring():
    """Test relevance scoring of matches."""
    print("\n=== Test: Relevance Scoring ===")

    db = MockDatabase()
    retriever = ContextRetriever(db)

    # High relevance: matching fault code + symptom
    record_high = {
        'title': 'Motor overheating',
        'description': 'Unit running hot',
        'fault_codes': ['F0002']
    }
    score_high = retriever._score_relevance(
        record_high,
        equipment_terms=['motor'],
        symptoms=['overheating'],
        fault_codes=['F0002']
    )

    # Low relevance: no matches
    record_low = {
        'title': 'Replaced filter',
        'description': 'Routine maintenance',
        'fault_codes': []
    }
    score_low = retriever._score_relevance(
        record_low,
        equipment_terms=['motor'],
        symptoms=['overheating'],
        fault_codes=['F0002']
    )

    print(f"  High relevance score: {score_high:.2f}")
    print(f"  Low relevance score: {score_low:.2f}")

    if score_high > score_low:
        print("  [PASS] High relevance record scores higher")
        return True
    else:
        print("  [FAIL] Scoring not working correctly")
        return False


async def test_system_prompt_injection():
    """Test system prompt injection format."""
    print("\n=== Test: System Prompt Injection ===")

    context = RetrievedContext(
        matches=[
            ContextMatch(
                source='work_order',
                relevance_score=0.85,
                title='WO WO-2026-00123',
                summary='Motor overheating - RESOLVED',
                created_at='2026-01-15',
            )
        ],
        formatted_context="- **WO WO-2026-00123** (2026-01-15): Motor overheating - RESOLVED",
        has_relevant_history=True
    )

    injection = context.to_system_prompt_injection()

    print(f"  Injection:\n{injection}\n")

    if "## Relevant Equipment History" in injection:
        print("  [PASS] Injection has correct header")
    else:
        print("  [FAIL] Missing header in injection")
        return False

    # Empty context should return empty string
    empty_context = RetrievedContext()
    empty_injection = empty_context.to_system_prompt_injection()

    if empty_injection == "":
        print("  [PASS] Empty context returns empty injection")
    else:
        print("  [FAIL] Empty context should return empty string")
        return False

    return True


async def run_all_tests():
    """Run all test cases."""
    print("=" * 70)
    print("CONTEXT RETRIEVER TEST (EXPERT-006)")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    results = []

    # Sync tests
    results.append(("Equipment Term Extraction", test_equipment_term_extraction()))
    results.append(("Symptom Extraction", test_symptom_extraction()))
    results.append(("Fault Code Extraction", test_fault_code_extraction()))
    results.append(("Context Formatting", test_context_formatting()))

    # Async tests
    results.append(("Intent Filtering", await test_intent_filtering()))
    results.append(("Relevance Scoring", await test_relevance_scoring()))
    results.append(("System Prompt Injection", await test_system_prompt_injection()))

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
    print(f"  [{'PASS' if passed == total else 'FAIL'}] All unit tests pass")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
