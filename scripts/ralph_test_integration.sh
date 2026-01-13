#!/bin/bash
# Ralph Test Integration - Run tests after story completion
# This script is called by Ralph after each story is implemented

set -e

STORY_ID="$1"
COMMIT_HASH="$2"
SUCCESS="$3"

echo "═══════════════════════════════════════════════════════"
echo "  Ralph Test Integration"
echo "═══════════════════════════════════════════════════════"
echo "Story: $STORY_ID"
echo "Commit: $COMMIT_HASH"
echo "Implementation Status: $SUCCESS"
echo ""

# Only run tests if story implementation succeeded
if [ "$SUCCESS" != "true" ]; then
  echo "⚠️  Skipping tests - implementation failed"
  exit 0
fi

# Change to project directory
cd /root/Rivet-PRO

# Activate virtual environment if exists
if [ -d ".venv" ]; then
  source .venv/bin/activate
elif [ -d "venv" ]; then
  source venv/bin/activate
fi

# Run test harness
echo "▶ Running automated tests..."
python3 tests/ralph/ralph_test_harness.py "$STORY_ID" "$COMMIT_HASH" || true

# Check test results from database
echo ""
echo "▶ Fetching test results from database..."

TEST_STATUS=$(psql "$DATABASE_URL" -t -c "SELECT test_status FROM ralph_stories WHERE story_id = '$STORY_ID' LIMIT 1" | xargs)

if [ "$TEST_STATUS" = "passed" ]; then
  echo "✅ All tests PASSED"

  # Send Telegram notification
  if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_ADMIN_CHAT_ID" ]; then
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
      -d "chat_id=$TELEGRAM_ADMIN_CHAT_ID" \
      -d "text=✅ *Tests PASSED*: \`$STORY_ID\`%0ACommit: \`${COMMIT_HASH:0:8}\`%0AAll automated tests passed successfully." \
      -d "parse_mode=Markdown" > /dev/null
  fi

  exit 0

elif [ "$TEST_STATUS" = "failed" ]; then
  echo "❌ Tests FAILED"

  # Send Telegram notification with details
  if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_ADMIN_CHAT_ID" ]; then
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
      -d "chat_id=$TELEGRAM_ADMIN_CHAT_ID" \
      -d "text=❌ *Tests FAILED*: \`$STORY_ID\`%0ACommit: \`${COMMIT_HASH:0:8}\`%0ACheck logs for details: /root/ralph/logs/" \
      -d "parse_mode=Markdown" > /dev/null
  fi

  exit 1

else
  echo "⚠️  Test status unknown"
  exit 0
fi
