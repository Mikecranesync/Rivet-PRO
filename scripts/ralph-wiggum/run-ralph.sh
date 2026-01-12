#!/bin/bash
# Wrapper for Ralph Wiggum with cost controls and defaults
# Usage: ./run-ralph.sh "task description" "completion promise" [max_iterations] [timeout]

set -e

TASK="${1:-}"
PROMISE="${2:-COMPLETE}"
MAX_ITER="${3:-10}"
TIMEOUT="${4:-1800}"

if [ -z "$TASK" ]; then
  echo "Usage: ./run-ralph.sh \"task description\" \"completion promise\" [max_iterations] [timeout]"
  echo ""
  echo "Examples:"
  echo "  ./run-ralph.sh \"Add /ping command to bot\" \"command works\" 5"
  echo "  ./run-ralph.sh \"Create user service\" \"tests pass\" 10 3600"
  echo ""
  echo "Arguments:"
  echo "  task             - Detailed task description (required)"
  echo "  promise          - Completion criteria (default: 'COMPLETE')"
  echo "  max_iterations   - Max iterations (default: 10)"
  echo "  timeout          - Timeout in seconds (default: 1800 = 30 min)"
  echo ""
  exit 1
fi

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║              Ralph Wiggum - Autonomous Development            ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Task: $TASK"
echo "Promise: $PROMISE"
echo "Max Iterations: $MAX_ITER"
echo "Timeout: ${TIMEOUT}s ($(( TIMEOUT / 60 )) minutes)"
echo "Model: claude-3-5-sonnet"
echo "Temperature: 0.7"
echo ""
echo "Starting in 3 seconds... (Ctrl+C to cancel)"
sleep 3

# Run Ralph with all configured parameters
/ralph-loop "$TASK" \
  --completion-promise "$PROMISE" \
  --max-iterations "$MAX_ITER" \
  --timeout "$TIMEOUT" \
  --model claude-3-5-sonnet \
  --temperature 0.7

EXIT_CODE=$?

echo ""
echo "═══════════════════════════════════════════════════════════════"
if [ $EXIT_CODE -eq 0 ]; then
  echo "✓ Ralph completed successfully!"
else
  echo "⚠ Ralph exited with code $EXIT_CODE"
fi
echo "═══════════════════════════════════════════════════════════════"

exit $EXIT_CODE
