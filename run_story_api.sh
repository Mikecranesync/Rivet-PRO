#!/bin/bash
# Run story implementation using Anthropic API directly
# Usage: ./run_story.sh "STORY_ID" "STORY_TITLE" "DESCRIPTION" "CRITERIA"

set -e

# Load config
if [ -f /root/ralph/config/.env ]; then
  source /root/ralph/config/.env
fi

STORY_ID="$1"
STORY_TITLE="$2"
DESCRIPTION="$3"
CRITERIA="$4"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/root/ralph/logs/${STORY_ID}_${TIMESTAMP}.log"

# Default project path
PROJECT_PATH="${PROJECT_PATH:-/root/rivet-pro}"

echo "Starting implementation of ${STORY_ID} at $(date)" | tee "$LOG_FILE"

# Build the prompt for Claude
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
- Project directory: ${PROJECT_PATH}
- Keep code SIMPLE - field techs need FAST responses
- Use existing patterns in the codebase
- DO NOT over-engineer or refactor unrelated code

## Instructions
1. Analyze the existing codebase structure
2. Implement this feature completely
3. Ensure all code follows existing patterns
4. Create or modify files as needed
5. After implementation, describe what you did

Output a detailed summary in this EXACT format:
SUCCESS: [true or false]
FILES_CHANGED: [comma-separated list of file paths]
DESCRIPTION: [what was implemented]
NOTES: [any important details or blockers]"

# Call Anthropic API using Messages API
API_RESPONSE=$(curl -s -X POST "https://api.anthropic.com/v1/messages" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${ANTHROPIC_API_KEY}" \
  -H "anthropic-version: 2023-06-01" \
  -d "{
    \"model\": \"claude-sonnet-4-20250514\",
    \"max_tokens\": 4096,
    \"messages\": [{
      \"role\": \"user\",
      \"content\": $(echo "$PROMPT" | jq -Rs .)
    }]
  }" 2>&1)

# Log the API response
echo "$API_RESPONSE" >> "$LOG_FILE"

# Extract Claude's response text
CLAUDE_TEXT=$(echo "$API_RESPONSE" | jq -r '.content[0].text // .error.message // "No response"')

echo "Claude Response:" >> "$LOG_FILE"
echo "$CLAUDE_TEXT" >> "$LOG_FILE"

# Parse the response to extract structured data
if echo "$CLAUDE_TEXT" | grep -q "SUCCESS: true"; then
  SUCCESS=true
  FILES=$(echo "$CLAUDE_TEXT" | grep "FILES_CHANGED:" | sed 's/FILES_CHANGED: //' | tr -d ' ')
  DESC=$(echo "$CLAUDE_TEXT" | grep "DESCRIPTION:" | sed 's/DESCRIPTION: //')
  NOTES=$(echo "$CLAUDE_TEXT" | grep "NOTES:" | sed 's/NOTES: //')

  # Note: Since we're using the API directly, we can't actually implement the code
  # This would need to be enhanced to actually create/modify files based on Claude's instructions
  # For now, we'll return a placeholder response

  echo "{\"success\": true, \"commit_hash\": \"manual\", \"files_changed\": [\"$FILES\"], \"notes\": \"$DESC - $NOTES (NOTE: Using API - actual file changes need manual implementation)\"}"
else
  ERROR=$(echo "$CLAUDE_TEXT" | grep "NOTES:" | sed 's/NOTES: //' || echo "$CLAUDE_TEXT")
  echo "{\"success\": false, \"error_message\": \"$ERROR\"}"
fi
