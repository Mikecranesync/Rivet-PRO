#!/bin/bash
# Run Claude Code CLI on a single story
# Usage: ./run_story.sh "STORY_ID" "STORY_TITLE" "DESCRIPTION" "CRITERIA"

set -e

# Load config
if [ -f /root/ralph/config/.env ]; then
  source /root/ralph/config/.env
export ANTHROPIC_API_KEY
fi

STORY_ID="$1"
STORY_TITLE="$2"
DESCRIPTION="$3"
CRITERIA="$4"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/root/ralph/logs/${STORY_ID}_${TIMESTAMP}.log"

# Default project path
PROJECT_PATH="${PROJECT_PATH:-/root/rivet-pro}"

cd "$PROJECT_PATH"

# Build the prompt
PROMPT="You are implementing a feature for RIVET Pro, an AI-powered maintenance assistant for field technicians.

## Story: ${STORY_ID}
## Title: ${STORY_TITLE}

## Description
${DESCRIPTION}

## Acceptance Criteria
${CRITERIA}

## Context
- This is an n8n-based system on VPS 72.60.175.144:5678
- Database is PostgreSQL (auto-detected, with fallbacks)
- Telegram bot for user interface
- Keep code SIMPLE - field techs need FAST responses
- Use existing patterns in the codebase
- DO NOT over-engineer or refactor unrelated code

## Instructions
1. Implement this feature completely
2. Test that it works
3. Commit with message: feat(${STORY_ID}): ${STORY_TITLE}

When done, output a JSON summary:
{
  \"success\": true,
  \"commit_hash\": \"the-commit-hash\",
  \"files_changed\": [\"list\", \"of\", \"files\"],
  \"notes\": \"Brief description of what was implemented\"
}

If blocked:
{
  \"success\": false,
  \"error_message\": \"What went wrong\",
  \"notes\": \"What needs to happen to unblock\"
}"

echo "Starting implementation of ${STORY_ID} at $(date)" | tee "$LOG_FILE"

# Write prompt to temp file to avoid quoting issues
PROMPT_FILE="/tmp/ralph_prompt_${STORY_ID}_${TIMESTAMP}.txt"
echo "$PROMPT" > "$PROMPT_FILE"
chmod 644 "$PROMPT_FILE"

# Execute Claude Code as ralph user (non-root) with dangerously-skip-permissions
# This is required because Claude Code CLI won't bypass permissions when running as root
OUTPUT=$(su - ralph -c "cd '$PROJECT_PATH' && source /home/ralph/.env && export ANTHROPIC_API_KEY && cat '$PROMPT_FILE' | claude --print --dangerously-skip-permissions 2>&1") || true

# Clean up temp file
rm -f "$PROMPT_FILE"

echo "$OUTPUT" >> "$LOG_FILE"

# Try to extract JSON result from output
RESULT=$(echo "$OUTPUT" | grep -o '{.*}' | tail -1) || RESULT='{"success": false, "error_message": "Could not parse output"}'

echo "$RESULT"
