#!/usr/bin/env python3
"""
Automated Telegram Bot Testing Script

Sends test messages to the Rivet CMMS bot and logs responses.
Uses the Telegram Bot API to simulate user interactions.

Usage:
    python scripts/test_bot_automated.py

Requirements:
    - TELEGRAM_BOT_TOKEN in .env
    - TELEGRAM_TEST_CHAT_ID in .env (your personal chat ID with the bot)
"""

import asyncio
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import httpx


@dataclass
class TestCase:
    """A single test case."""
    id: str
    message: str
    expected_intent: str
    expected_contains: list[str]  # Strings that should appear in response
    expected_not_contains: list[str] = None  # Strings that should NOT appear


@dataclass
class TestResult:
    """Result of a single test."""
    test_id: str
    message_sent: str
    response_received: str
    expected_intent: str
    passed: bool
    failure_reason: Optional[str] = None
    response_time_ms: int = 0


# Test cases organized by intent
TEST_CASES = [
    # Equipment Search
    TestCase(
        id="EQUIP_SEARCH_001",
        message="find siemens motors",
        expected_intent="EQUIPMENT_SEARCH",
        expected_contains=["Equipment", "EQ-"],
        expected_not_contains=["Error", "trouble understanding"]
    ),
    TestCase(
        id="EQUIP_SEARCH_002",
        message="what equipment do I have",
        expected_intent="EQUIPMENT_SEARCH",
        expected_contains=["Equipment"],
        expected_not_contains=["Error"]
    ),
    TestCase(
        id="EQUIP_SEARCH_003",
        message="Is there anything about pumps in my CMMS",
        expected_intent="EQUIPMENT_SEARCH",
        expected_contains=["Equipment", "EQ-"],
        expected_not_contains=["trouble understanding"]
    ),
    TestCase(
        id="EQUIP_SEARCH_004",
        message="show me my drives",
        expected_intent="EQUIPMENT_SEARCH",
        expected_contains=["Equipment"],
        expected_not_contains=["Error"]
    ),

    # Manual Questions
    TestCase(
        id="MANUAL_001",
        message="how do I reset a Siemens drive",
        expected_intent="MANUAL_QUESTION",
        expected_contains=["reset", "drive"],  # Should mention the topic
        expected_not_contains=["Error searching equipment"]
    ),
    TestCase(
        id="MANUAL_002",
        message="what does error code F0002 mean",
        expected_intent="MANUAL_QUESTION",
        expected_contains=["error", "F0002"],
        expected_not_contains=["Equipment Results"]
    ),
    TestCase(
        id="MANUAL_003",
        message="calibration procedure for VFD",
        expected_intent="MANUAL_QUESTION",
        expected_contains=["calibration", "VFD"],
        expected_not_contains=["Equipment Results"]
    ),

    # Troubleshooting
    TestCase(
        id="TROUBLE_001",
        message="motor is overheating",
        expected_intent="TROUBLESHOOT",
        expected_contains=["Overheating", "Causes", "Safety"],
        expected_not_contains=["Equipment Results", "Error"]
    ),
    TestCase(
        id="TROUBLE_002",
        message="drive won't start",
        expected_intent="TROUBLESHOOT",
        expected_contains=["start", "drive"],
        expected_not_contains=["Equipment Results"]
    ),
    TestCase(
        id="TROUBLE_003",
        message="getting error on the compressor",
        expected_intent="TROUBLESHOOT",
        expected_contains=["compressor", "error"],
        expected_not_contains=["Equipment Results"]
    ),

    # Work Orders
    TestCase(
        id="WO_CREATE_001",
        message="create a work order",
        expected_intent="WORK_ORDER_CREATE",
        expected_contains=["work order", "create"],
        expected_not_contains=["Equipment Results"]
    ),
    TestCase(
        id="WO_STATUS_001",
        message="show my work orders",
        expected_intent="WORK_ORDER_STATUS",
        expected_contains=["work order"],
        expected_not_contains=["Equipment Results"]
    ),

    # General Chat
    TestCase(
        id="GENERAL_001",
        message="hello",
        expected_intent="GENERAL_CHAT",
        expected_contains=["Hey", "help", "Menu"],
        expected_not_contains=["Error"]
    ),
    TestCase(
        id="GENERAL_002",
        message="thanks",
        expected_intent="GENERAL_CHAT",
        expected_contains=[],  # Just shouldn't error
        expected_not_contains=["Error searching"]
    ),
    TestCase(
        id="GENERAL_003",
        message="what can you do",
        expected_intent="GENERAL_CHAT",
        expected_contains=["help", "Menu", "Equipment"],
        expected_not_contains=["Error"]
    ),
]


class TelegramTestClient:
    """Client for sending test messages to Telegram bot."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.last_update_id = 0

    async def send_message(self, text: str) -> dict:
        """Send a message to the bot."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text
                },
                timeout=30.0
            )
            return response.json()

    async def get_updates(self, offset: int = 0, timeout: int = 30) -> list:
        """Get updates (responses) from the bot."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/getUpdates",
                params={
                    "offset": offset,
                    "timeout": timeout,
                    "allowed_updates": ["message"]
                },
                timeout=timeout + 10
            )
            data = response.json()
            if data.get("ok"):
                return data.get("result", [])
            return []

    async def clear_updates(self):
        """Clear pending updates."""
        updates = await self.get_updates(timeout=1)
        if updates:
            self.last_update_id = updates[-1]["update_id"] + 1

    async def wait_for_response(self, timeout: int = 30) -> Optional[str]:
        """Wait for a response from the bot."""
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            updates = await self.get_updates(offset=self.last_update_id, timeout=5)

            for update in updates:
                self.last_update_id = update["update_id"] + 1

                # Check if this is a message from the bot (not from user)
                message = update.get("message", {})
                if message.get("from", {}).get("is_bot", False):
                    return message.get("text", "")

            await asyncio.sleep(1)

        return None


async def run_test(client: TelegramTestClient, test: TestCase) -> TestResult:
    """Run a single test case."""
    print(f"\n{'='*60}")
    print(f"Test: {test.id}")
    print(f"Message: {test.message}")
    print(f"Expected Intent: {test.expected_intent}")

    # Clear any pending updates
    await client.clear_updates()

    # Send the test message
    start_time = asyncio.get_event_loop().time()
    await client.send_message(test.message)

    # Wait for response
    response = await client.wait_for_response(timeout=45)
    response_time = int((asyncio.get_event_loop().time() - start_time) * 1000)

    if not response:
        return TestResult(
            test_id=test.id,
            message_sent=test.message,
            response_received="<NO RESPONSE>",
            expected_intent=test.expected_intent,
            passed=False,
            failure_reason="No response received within timeout",
            response_time_ms=response_time
        )

    print(f"Response ({response_time}ms): {response[:200]}...")

    # Check expected_contains
    missing = []
    for expected in test.expected_contains:
        if expected.lower() not in response.lower():
            missing.append(expected)

    # Check expected_not_contains
    unwanted = []
    if test.expected_not_contains:
        for not_expected in test.expected_not_contains:
            if not_expected.lower() in response.lower():
                unwanted.append(not_expected)

    # Determine pass/fail
    passed = len(missing) == 0 and len(unwanted) == 0
    failure_reason = None

    if missing:
        failure_reason = f"Missing expected content: {missing}"
    if unwanted:
        fr = f"Contains unwanted content: {unwanted}"
        failure_reason = f"{failure_reason}; {fr}" if failure_reason else fr

    result = TestResult(
        test_id=test.id,
        message_sent=test.message,
        response_received=response,
        expected_intent=test.expected_intent,
        passed=passed,
        failure_reason=failure_reason,
        response_time_ms=response_time
    )

    status = "PASS" if passed else "FAIL"
    print(f"Result: {status}")
    if failure_reason:
        print(f"Reason: {failure_reason}")

    return result


async def main():
    """Run all tests."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_TEST_CHAT_ID")

    if not bot_token:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    if not chat_id:
        print("ERROR: TELEGRAM_TEST_CHAT_ID not set in .env")
        print("To find your chat ID:")
        print("1. Send a message to your bot")
        print("2. Visit: https://api.telegram.org/bot<TOKEN>/getUpdates")
        print("3. Look for 'chat': {'id': <YOUR_CHAT_ID>}")
        sys.exit(1)

    client = TelegramTestClient(bot_token, chat_id)

    print("=" * 60)
    print("RIVET CMMS Bot - Automated Test Suite")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Test Cases: {len(TEST_CASES)}")
    print("=" * 60)

    results = []

    for test in TEST_CASES:
        try:
            result = await run_test(client, test)
            results.append(result)
            # Small delay between tests
            await asyncio.sleep(2)
        except Exception as e:
            print(f"ERROR running test {test.id}: {e}")
            results.append(TestResult(
                test_id=test.id,
                message_sent=test.message,
                response_received=f"ERROR: {e}",
                expected_intent=test.expected_intent,
                passed=False,
                failure_reason=str(e)
            ))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    print(f"Total: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Pass Rate: {passed/len(results)*100:.1f}%")

    if failed > 0:
        print("\nFailed Tests:")
        for r in results:
            if not r.passed:
                print(f"  - {r.test_id}: {r.failure_reason}")

    # Save results to file
    output_file = Path(__file__).parent / "test_results.json"
    with open(output_file, "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    print(f"\nResults saved to: {output_file}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
