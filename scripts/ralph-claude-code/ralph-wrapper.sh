#!/bin/bash
# Ralph wrapper with Telegram notifications and logging
#
# Usage:
#   ./ralph-wrapper.sh [max_calls] [story_id]
#
# Arguments:
#   max_calls - Maximum Ralph iterations (default: 50)
#   story_id  - Story ID for notifications (default: UNKNOWN)
#
# Examples:
#   ./ralph-wrapper.sh 10 "RIVET-006"
#   ./ralph-wrapper.sh 50
#   ./ralph-wrapper.sh

set -e  # Exit on error
set -u  # Exit on undefined variable

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load platform configuration
source "$SCRIPT_DIR/config.sh"

# Parse arguments
MAX_CALLS="${1:-50}"
STORY_ID="${2:-UNKNOWN}"

# Create logs directory
LOG_DIR="$WORKSPACE_ROOT/logs"
mkdir -p "$LOG_DIR"

# Log file with timestamp
LOG_FILE="$LOG_DIR/ralph-$(date +%Y%m%d-%H%M%S).log"

# Notification helper
notify() {
    local event="$1"
    local story="$2"
    local details="$3"

    echo "[$(date +%H:%M:%S)] Notification: $event - $story" | tee -a "$LOG_FILE"
    $PYTHON_CMD "$SCRIPT_DIR/notify.py" "$event" "$story" "$details" 2>&1 | tee -a "$LOG_FILE"
}

# Trap errors
trap 'notify "error" "$STORY_ID" "Script terminated unexpectedly"; exit 1' ERR

# Start notification
notify "start" "$STORY_ID" "Project: RIVET Pro\nMax iterations: $MAX_CALLS"

# Navigate to Ralph directory
cd "$SCRIPT_DIR" || {
    echo "ERROR: Cannot access $SCRIPT_DIR"
    notify "error" "$STORY_ID" "Cannot access Ralph directory"
    exit 1
}

# Verify Ralph is installed
if ! command -v ralph &> /dev/null; then
    echo "ERROR: ralph command not found"
    echo "Install frankbria/ralph-claude-code first:"
    echo "  git clone https://github.com/frankbria/ralph-claude-code.git /tmp/ralph"
    echo "  cd /tmp/ralph && ./install.sh"
    notify "error" "$STORY_ID" "ralph command not installed"
    exit 1
fi

# Verify required files exist
if [ ! -f "PROMPT.md" ]; then
    echo "ERROR: PROMPT.md not found in $SCRIPT_DIR"
    notify "error" "$STORY_ID" "PROMPT.md missing"
    exit 1
fi

if [ ! -f "@fix_plan.md" ]; then
    echo "ERROR: @fix_plan.md not found in $SCRIPT_DIR"
    echo "Create it first or convert from prd.json:"
    echo "  python convert-prd.py ../ralph/prd.json --output @fix_plan.md"
    notify "error" "$STORY_ID" "@fix_plan.md missing"
    exit 1
fi

# Display configuration
echo "================================================" | tee -a "$LOG_FILE"
echo "Starting Ralph" | tee -a "$LOG_FILE"
echo "================================================" | tee -a "$LOG_FILE"
echo "Story ID:     $STORY_ID" | tee -a "$LOG_FILE"
echo "Max Calls:    $MAX_CALLS" | tee -a "$LOG_FILE"
echo "Log File:     $LOG_FILE" | tee -a "$LOG_FILE"
echo "Working Dir:  $SCRIPT_DIR" | tee -a "$LOG_FILE"
echo "================================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Run Ralph
echo "Running Ralph (max $MAX_CALLS iterations)..." | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Ralph command with optional monitor flag
RALPH_CMD="ralph --calls $MAX_CALLS $RALPH_MONITOR"

echo "Command: $RALPH_CMD" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Execute Ralph, capturing output
if $RALPH_CMD 2>&1 | tee -a "$LOG_FILE"; then
    RALPH_EXIT_CODE=0
else
    RALPH_EXIT_CODE=$?
fi

echo "" | tee -a "$LOG_FILE"
echo "================================================" | tee -a "$LOG_FILE"
echo "Ralph Finished (exit code: $RALPH_EXIT_CODE)" | tee -a "$LOG_FILE"
echo "================================================" | tee -a "$LOG_FILE"

# Check exit status and send appropriate notification
if [ $RALPH_EXIT_CODE -eq 0 ]; then
    # Check for EXIT_SIGNAL in .response_analysis (if frankbria creates it)
    if [ -f ".response_analysis" ]; then
        if grep -q "EXIT_SIGNAL.*true" ".response_analysis" 2>/dev/null; then
            echo "✓ EXIT_SIGNAL detected - all tasks complete" | tee -a "$LOG_FILE"
            notify "complete" "$STORY_ID" "All tasks completed successfully\nLog: $LOG_FILE"
        else
            echo "↻ EXIT_SIGNAL not detected - more iterations needed" | tee -a "$LOG_FILE"
            notify "progress" "$STORY_ID" "Iteration complete, continuing...\nLog: $LOG_FILE"
        fi
    else
        # No .response_analysis file - assume complete
        echo "✓ Process complete (no response analysis file)" | tee -a "$LOG_FILE"
        notify "complete" "$STORY_ID" "Process complete\nLog: $LOG_FILE"
    fi
else
    # Non-zero exit code
    echo "✗ Ralph exited with error code $RALPH_EXIT_CODE" | tee -a "$LOG_FILE"
    notify "error" "$STORY_ID" "Exit code: $RALPH_EXIT_CODE\nCheck log: $LOG_FILE"
    exit $RALPH_EXIT_CODE
fi

echo "" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
